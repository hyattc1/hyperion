"""SafeBot: the crash-proof, clamp-everything wrapper around any Bot.

Every error or timeout in the real event is a forced fold, so this layer is worth more than any
strategy inside it. It never raises, never returns an illegal action, and keeps telemetry on how
close the inner bot is to the budget. It cannot interrupt a slow act() (pure Python, one thread),
so the deadline check is after the fact: overruns are counted and after `panic_after` of them the
inner bot is told to switch to its cheapest path via `set_panic(True)` if it has that method.
Panic also needs the overrun *rate* to exceed `panic_rate`, because a preempted process overruns
no matter how cheap its code is and a handful of noisy calls in 200 hands should not degrade play.
"""
from __future__ import annotations

import logging
from time import perf_counter

from ..core.types import Action, ActionKind, Bot, HandResult, Observation, Rules

log = logging.getLogger("snapcall.safe")

_CHECK = Action(ActionKind.CHECK)
_FOLD = Action(ActionKind.FOLD)
_CALL = Action(ActionKind.CALL)


def safe_action(obs: Observation) -> Action:
    """Check if legal, else fold. Shares module-level constants: no allocation."""
    try:
        legal = obs.legal
        if ActionKind.CHECK in legal:
            return _CHECK
        if ActionKind.FOLD in legal:
            return _FOLD
        if ActionKind.CALL in legal:  # degenerate kit: only call offered
            return _CALL
    except Exception:
        pass
    return _FOLD


class SafeBot:
    __slots__ = (
        "inner", "deadline", "panic_after", "panic_rate", "errors", "overruns", "calls", "worst", "panic_mode",
        "_has_panic",
    )

    def __init__(self, inner: Bot, deadline_ms: float = 0.5, panic_after: int = 5, panic_rate: float = 0.02):
        self.inner = inner
        self.deadline = deadline_ms / 1000.0
        self.panic_after = panic_after
        self.panic_rate = panic_rate
        self.errors = 0
        self.overruns = 0
        self.calls = 0
        self.worst = 0.0
        self.panic_mode = False
        self._has_panic = hasattr(inner, "set_panic")

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.errors = 0
        self.overruns = 0
        self.calls = 0
        self.worst = 0.0
        self.panic_mode = False
        try:
            self.inner.new_table(rules, seat, n_players)
        except Exception:
            self.errors += 1
            log.exception("new_table failed")
        if self._has_panic:
            try:
                self.inner.set_panic(False)
            except Exception:
                pass

    def act(self, obs: Observation) -> Action:
        self.calls += 1
        t0 = perf_counter()
        try:
            a = self.inner.act(obs)
        except Exception:
            a = None
            self.errors += 1
            if self.errors <= 3:
                log.exception("act failed; returning safe action")
        dt = perf_counter() - t0
        if dt > self.worst:
            self.worst = dt
        if dt > self.deadline:
            self.overruns += 1
            if not self.panic_mode and self.overruns >= self.panic_after and self.overruns >= self.panic_rate * self.calls:
                self._enter_panic()
        if a is None or a.__class__ is not Action:
            return safe_action(obs)
        try:
            return a.clamp(obs)
        except Exception:
            self.errors += 1
            return safe_action(obs)

    def hand_end(self, result: HandResult) -> None:
        try:
            self.inner.hand_end(result)
        except Exception:
            self.errors += 1
            if self.errors <= 3:
                log.exception("hand_end failed")

    def _enter_panic(self) -> None:
        self.panic_mode = True
        log.warning("panic mode after %d overruns (worst %.3f ms)", self.overruns, self.worst * 1000)
        if self._has_panic:
            try:
                self.inner.set_panic(True)
            except Exception:
                self.errors += 1

    def stats(self) -> dict:
        return {
            "calls": self.calls, "errors": self.errors, "overruns": self.overruns,
            "worst_ms": self.worst * 1000, "panic_mode": self.panic_mode,
        }
