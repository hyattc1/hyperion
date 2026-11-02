"""SafeBot: the crash-proof, clamp-everything wrapper around any Bot.

Every error or timeout in the real event is a forced fold, so this layer is worth more than any
strategy inside it. It never raises, never returns an illegal action, and keeps telemetry on how
close the inner bot is to the budget. It cannot interrupt a slow act() (pure Python, one thread),
so the deadline check is after the fact: overruns are counted and after `panic_after` of them the
inner bot is told to switch to its cheapest path via `set_panic(True)` if it has that method.
Panic also needs the overrun *rate* to exceed `panic_rate`, because a preempted process overruns
no matter how cheap its code is and a handful of noisy calls in 200 hands should not degrade play.

The governor (`Governor`, off by default: today's single cliff above, bit for bit). Backlog R1 (docs/drills/
r1-timing-log.md): on a 2-3x slower or noisy sandbox the cliff sends whole tables to the cheap path for overruns that
were one noisy call apart. Three dials, each independent:
  window   count only the overruns in the last `window` calls (0: since the last level change, with panic_rate);
  ladder   step one level per trigger through the inner bot's `levels` intermediate levels (its `set_level(n)`, n = 1
           .. levels: shed shadows and extras first), and panic (`set_panic(True)`) only past the last one;
  recover  after `recover` calls in a row with no overrun at a level, step back up one level (the box was busy, now
           it is not); each step back up multiplies the calls the next one needs by `backoff`.
`degrade_level` is the level in play (0 = full strength, levels + 1 = panic); `level_max` the deepest this table.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from time import perf_counter

from ..core.types import Action, ActionKind, Bot, HandResult, Observation, Rules

log = logging.getLogger("hyperion.safe")

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


@dataclass(frozen=True)
class Governor:
    """How SafeBot degrades on overruns (module doc). The defaults are the single cliff: Governor() acts as None."""

    window: int = 0  # overruns counted in the last `window` calls; 0 = since the last level change, with panic_rate
    ladder: bool = False  # one level per trigger through the inner bot's levels, panic past the last
    recover: int = 0  # calls in a row without an overrun before stepping back up one level; 0 = never
    backoff: float = 2.0  # each step back up multiplies the calls the next one needs

    @property
    def active(self) -> bool:
        return bool(self.window or self.ladder or self.recover)


def governor(window: int = 0, ladder: bool = False, recover: int = 0, backoff: float = 2.0) -> Governor | None:
    """The Governor these dials name, or None when they are the defaults (the bots' configs call this)."""
    g = Governor(int(window or 0), bool(ladder), int(recover or 0), float(backoff))
    return g if g.active else None


class SafeBot:
    __slots__ = (
        "inner", "deadline", "panic_after", "panic_rate", "errors", "overruns", "calls", "worst", "panic_mode",
        "_has_panic", "gov", "degrade_level", "level_max", "level_changes", "_levels", "_has_level", "_ring",
        "_cnt", "_c0", "_quiet", "_need",
    )

    def __init__(self, inner: Bot, deadline_ms: float = 0.5, panic_after: int = 5, panic_rate: float = 0.02,
                 gov: Governor | None = None):
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
        self.gov = gov if gov is not None and gov.active else None
        self._has_level = hasattr(inner, "set_level")
        self._levels = int(getattr(inner, "levels", 0) or 0) if self._has_level else 0
        self._reset_gov()

    def _reset_gov(self) -> None:
        self.degrade_level = 0
        self.level_max = 0
        self.level_changes = 0
        self._ring: list = []
        self._cnt = 0
        self._c0 = 0
        self._quiet = 0
        self._need = self.gov.recover if self.gov is not None else 0

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.errors = 0
        self.overruns = 0
        self.calls = 0
        self.worst = 0.0
        self.panic_mode = False
        self._reset_gov()
        if self._has_level:
            try:
                self.inner.set_level(0)
            except Exception:
                pass
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
        if self.gov is not None:
            self._govern(dt > self.deadline)
        elif dt > self.deadline:
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

    # ------------------------------------------------------------------ the governor (module doc)
    def _govern(self, over: bool) -> None:
        g = self.gov
        top = (self._levels + 1) if g.ladder else 1
        if over:
            self.overruns += 1
            self._quiet = 0
            if self.degrade_level >= top:
                return
            if g.window:
                ring = self._ring
                ring.append(self.calls)
                lo = self.calls - g.window
                while ring and ring[0] <= lo:
                    ring.pop(0)
                fire = len(ring) >= self.panic_after
            else:
                self._cnt += 1
                fire = self._cnt >= self.panic_after and self._cnt >= self.panic_rate * (self.calls - self._c0)
            if fire:
                self._set_level(self.degrade_level + 1 if g.ladder else top, top)
            return
        if g.recover and self.degrade_level > 0:
            self._quiet += 1
            if self._quiet >= self._need:
                self._need = max(1, int(self._need * g.backoff))
                self._set_level(self.degrade_level - 1, top)

    def _set_level(self, level: int, top: int) -> None:
        level = max(0, min(level, top))
        if level == self.degrade_level:
            return
        was_panic = self.panic_mode
        self.degrade_level = level
        self.level_changes += 1
        if level > self.level_max:
            self.level_max = level
        self._ring = []
        self._cnt = 0
        self._c0 = self.calls
        self._quiet = 0
        if level >= top:
            self._enter_panic()
            return
        if was_panic:
            self.panic_mode = False
            log.warning("panic over after %d quiet calls (level %d)", self._need, level)
            if self._has_panic:
                try:
                    self.inner.set_panic(False)
                except Exception:
                    self.errors += 1
        if self._has_level:
            try:
                self.inner.set_level(level)
            except Exception:
                self.errors += 1

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
            "worst_ms": self.worst * 1000, "panic_mode": self.panic_mode, "level": self.degrade_level,
            "level_max": self.level_max, "level_changes": self.level_changes,
        }
