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

**The whole timed call** (G1, `whole_call`, off by default; on in the composite's SHIP_DIALS and the `slow_box` recipe). What
a kit times runs from its call to our return: the adapter's translation, the history inference, a hand end delivered at
the top of the decision, then `act`. `act` alone is about half of it, so a governor that times only `act` never sees a
slow box through a kit (batch 8: 12% timeouts at 3x with no level reached, docs/drills/climb/b8-timing.md). With the dial on,
`hyperion.drills.adapter.Adapter` tells this SafeBot that reports are coming (`expect_reports`, at its build) and sends every
decision's whole call to `report_call(seconds)`; the overruns are counted there, on the same deadline and the same
window (the scheduler's stalls apart: report_call), and `act`'s own time counts for nothing. A SafeBot with no adapter in front of it (the simulator, the tests) has no
reports and times `act`, as before. An entry that does not go through Adapter.decide must call `report_call` itself:
tools/gate.py fails a package whose decisions do not report.
"""
from __future__ import annotations

import atexit
import json
import logging
import os
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


_BOTS: list = []  # every SafeBot in this process, kept only for tools/gate.py's report (GATE_GOV_REPORT below)
_REPORT_PATH = os.environ.get("GATE_GOV_REPORT")


class SafeBot:
    __slots__ = (
        "inner", "deadline", "panic_after", "panic_rate", "errors", "overruns", "calls", "worst", "panic_mode",
        "_has_panic", "gov", "degrade_level", "level_max", "level_changes", "_levels", "_has_level", "_ring",
        "_cnt", "_c0", "_quiet", "_need", "whole_on", "_whole", "reports", "life", "lvl_calls", "end_budget", "_floor", "no_panic",
    )

    def __init__(self, inner: Bot, deadline_ms: float = 0.5, panic_after: int = 5, panic_rate: float = 0.02,
                 gov: Governor | None = None, whole_call: bool = False, hand_end_ms: float = 0.0):
        self.inner = inner
        self.whole_on = bool(whole_call)  # the dial: count the whole timed call when an adapter reports it
        # G1: what a kit's held hand end may cost: its Adapter holds it for the next decision only while a typical
        # decision with it stays under this (hyperion/drills/adapter.py Adapter.hand_end); 0 = always. Off with no governor
        # or none that can fire (a model-mode run, panic_after 10^9): it reads the clock
        live = whole_call and gov is not None and gov.active and panic_after < 10 ** 6
        self.end_budget = float(hand_end_ms) / 1000.0 if live else 0.0
        self._whole = False  # ... and one does (expect_reports)
        self.reports = 0  # whole calls reported this table
        self.life = {"acts": 0, "reports": 0, "overruns": 0, "tables": 0, "level_tables": 0, "panic_tables": 0,
                     "level_max": 0, "lvl_calls": {}, "tail_lost": 0, "forced": 0,
                     "dropped": 0}  # every table so far in this process (tools/gate.py's report); the last three, the
        #                             adapter's budget-aware hand end (Adapter.hand_end)
        self.lvl_calls: dict = {}
        self._floor = 0  # the governor does not recover above this level (set_floor)
        self.no_panic = False  # the ladder ends at its last level: the composite's, whose last level is as fast as the cheap path
        if _REPORT_PATH:
            _BOTS.append(self)
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

    def expect_reports(self, on: bool = True) -> bool:
        """An adapter sends the whole timed call (`report_call`). With the dial on, the overruns are counted there and
        `act`'s own time no longer counts; with it off (G1_OFF: batch 8) nothing changes. Returns whether they count."""
        self._whole = bool(on) and self.whole_on
        return self._whole

    def report_call(self, seconds: float, cpu: float | None = None) -> None:
        """One decision's whole timed call: from the kit's call to our return, and (`cpu`) how much of it our thread ran. A
        call the scheduler stalled is late however cheap its code, and stepping down answers nothing: it counts as an overrun
        only when the code itself used most of the line. A normal box under load then never fires, a slow CPU still does."""
        self.reports += 1
        if self._whole:
            if seconds > self.worst:
                self.worst = seconds
            self._count(seconds if cpu is None or cpu > 0.6 * self.deadline else 0.0)

    def set_floor(self, level: int) -> None:
        """An adapter that has measured this box slow for a table's worth of calls (Adapter._note_call): play at level
        `level` or below it, without waiting for a cluster of overruns, and do not recover past it. 0 gives the ladder back."""
        if self.gov is None or not self.gov.ladder or self._levels < 1:
            return
        self._floor = level
        if self.degrade_level < level:
            self._set_level(level, self._top())

    def _bank(self) -> None:
        """This table's counters into the process's (`life`), at the table's end."""
        life = self.life
        life["acts"] += self.calls
        life["reports"] += self.reports
        life["overruns"] += self.overruns
        if self.calls >= 8:  # (not an entry's warm-up, a few made-up decisions)
            life["tables"] += 1
            life["level_tables"] += self.level_max > 0
            life["panic_tables"] += self.panic_mode or (self.gov is not None and self.level_max >= self._top())
        life["level_max"] = max(life["level_max"], self.level_max)
        self._bank_level()
        for k, v in self.lvl_calls.items():
            life["lvl_calls"][k] = life["lvl_calls"].get(k, 0) + v
        self.lvl_calls = {}

    def _bank_level(self) -> None:
        if self.calls > self._c0:
            d = self.degrade_level
            self.lvl_calls[d] = self.lvl_calls.get(d, 0) + self.calls - self._c0
            self._c0 = self.calls

    def _top(self) -> int:
        if self.gov is None or not self.gov.ladder:
            return 1
        return self._levels if self.no_panic and self._levels else self._levels + 1

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
        self._bank()
        self.errors = 0
        self.overruns = 0
        self.calls = 0
        self.reports = 0
        self.worst = 0.0
        self.panic_mode = False
        self._floor = 0
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
        if not self._whole:  # an adapter's report counts this call, the whole of it (report_call)
            dt = perf_counter() - t0
            if dt > self.worst:
                self.worst = dt
            self._count(dt)
        if a is None or a.__class__ is not Action:
            return safe_action(obs)
        try:
            return a.clamp(obs)
        except Exception:
            self.errors += 1
            return safe_action(obs)

    def _count(self, dt: float) -> None:
        if self.gov is not None:
            self._govern(dt > self.deadline)
        elif dt > self.deadline:
            self.overruns += 1
            if not self.panic_mode and self.overruns >= self.panic_after and self.overruns >= self.panic_rate * self.calls:
                self._enter_panic()

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
        top = self._top()
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
        if g.recover and self.degrade_level > self._floor:
            self._quiet += 1
            if self._quiet >= self._need:
                self._need = max(1, int(self._need * g.backoff))
                self._set_level(self.degrade_level - 1, top)

    def _set_level(self, level: int, top: int) -> None:
        level = max(0, min(level, top))
        if level == self.degrade_level:
            return
        self._bank_level()
        was_panic = self.panic_mode
        self.degrade_level = level
        self.level_changes += 1
        if level > self.level_max:
            self.level_max = level
        self._ring = []
        self._cnt = 0
        self._c0 = self.calls  # (_govern's count since the last change, and the calls banked at this level)
        self._quiet = 0
        if level >= top and not (self.no_panic and self._levels):
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
            "level_max": self.level_max, "level_changes": self.level_changes, "reports": self.reports,
            "whole_call": self._whole,
        }

    def life_stats(self) -> dict:
        """Every table so far in this process, the one in play included (tools/gate.py's report)."""
        self._bank()
        life = self.life
        life["whole_on"] = self.whole_on
        life["whole"] = self._whole
        self.calls, self.reports, self.overruns, self.level_max = 0, 0, 0, self.degrade_level
        return life


def report() -> dict:
    """Every SafeBot of this process, summed: decisions, whole calls reported, levels reached."""
    out: dict = {"acts": 0, "reports": 0, "overruns": 0, "tables": 0, "level_tables": 0, "panic_tables": 0, "tail_lost": 0,
                 "forced": 0, "dropped": 0, "level_max": 0, "lvl_calls": {}, "whole_on": False, "whole": False,
                 "bots": len(_BOTS)}
    for b in _BOTS:
        life = b.life_stats()
        for k in ("acts", "reports", "overruns", "tables", "level_tables", "panic_tables", "tail_lost", "forced", "dropped"):
            out[k] += life[k]
        out["level_max"] = max(out["level_max"], life["level_max"])
        out["whole_on"] = out["whole_on"] or life["whole_on"]
        out["whole"] = out["whole"] or life["whole"]
        for k, v in life["lvl_calls"].items():
            out["lvl_calls"][str(k)] = out["lvl_calls"].get(str(k), 0) + v
    return out


def _write_report() -> None:
    try:
        with open(_REPORT_PATH, "w") as fh:
            json.dump(report(), fh)
    except Exception:  # noqa: BLE001 - a report, at exit: never in the way
        pass


if _REPORT_PATH:  # tools/gate.py sets it for a bot in its own process (kits C, D, a process kit); the night's sandbox never
    atexit.register(_write_report)
