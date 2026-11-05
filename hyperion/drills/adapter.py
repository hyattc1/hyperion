"""Adapter pattern: kit-native state -> Observation, our Action -> kit-native action.

Strategy code never sees a kit. On event night you write one Adapter subclass for the real kit
(pattern below, worked examples for the three fake kits) and the bot behind it stays untouched.
Nothing here imports a fake kit; the reference adapters are pure translation.
"""
from __future__ import annotations

import os
import sys
from time import perf_counter
from typing import Any, Callable, Iterable

from hyperion.core.types import Action, ActionKind, Bot, HandResult, Observation, Rules, parse_card
from hyperion.strategy.safe import SafeBot
from hyperion.strategy.tables import quick_start

KIND_BY_NAME = {"fold": ActionKind.FOLD, "check": ActionKind.CHECK, "call": ActionKind.CALL, "raise": ActionKind.RAISE}
# the other words kits use for the four (legal_kinds); "all in" is a raise unless the call already takes every chip
KIND_WORDS = {**KIND_BY_NAME, "bet": ActionKind.RAISE, "raise_to": ActionKind.RAISE, "raiseto": ActionKind.RAISE,
              "f": ActionKind.FOLD, "k": ActionKind.CHECK, "x": ActionKind.CHECK, "r": ActionKind.RAISE,
              "b": ActionKind.RAISE}
ALL_IN_WORDS = {"allin", "all_in", "all-in", "all in", "shove", "jam", "push"}
# a check when nothing is owed, else a call ("c" as the ACPC protocol uses it)
CHECK_OR_CALL_WORDS = {"check/call", "check_call", "checkcall", "call/check", "check_or_call", "checkorcall", "c"}
_NAME_KEYS = ("type", "action", "kind", "name", "move", "act", "id")

# Kit loaders unload a bot's own modules so two bots can each ship a utils.py: kit F's (drill 8) deletes every module a
# bot imported from its folder from sys.modules once Agent() returns and takes the folder off sys.path; kit G's (drill 9)
# does it as soon as the entry module has run, BEFORE Agent() is built. Each import inside a function then fails with
# "No module named 'hyperion'" (Hero's twin tables at table start, the latency governor, ...), and the callers that
# swallow errors play on misconfigured. So the entry builds and warms its bot at module import and calls
# pin_package(<its folder>) there (hyperion/drills/entry_template.py); the Adapter pins again when it is built, and every
# call (start, decide, hand_end) puts this copy's modules back, and the pinned folders back on sys.path, when a loader
# took them away. A submodule not imported yet still loads through the pinned package's __path__; the folders on
# sys.path are for the entry's own top-level modules (adapter.py, a variant file).
_PKG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # this copy's hyperion/
_PINNED: dict = {}
_KEEP: list = []  # folders pin_package was asked to keep on sys.path


def pin_package(*keep: str) -> None:
    """Remember the modules of this copy of the package imported so far, and keep the folders `keep` on sys.path
    (the entry's own folder and the package root: pin_package(_HERE, ...) at the entry's import)."""
    pre = _PKG_DIR + os.sep
    for k, m in list(sys.modules.items()):
        if (k == "hyperion" or k.startswith("hyperion.")) and m is not None:
            f = getattr(m, "__file__", None)
            if f and os.path.abspath(f).startswith(pre):
                _PINNED.setdefault(k, m)
    for d in keep:
        d = os.path.abspath(d)
        if d not in _KEEP:
            _KEEP.append(d)
    _keep_on_path()


def _keep_on_path() -> None:
    for d in _KEEP:
        if d not in sys.path:
            sys.path.append(d)  # last: it never shadows another bot's or the kit's modules


def repin_package() -> None:
    """Put this copy's modules back into sys.modules when a loader took them out (or another copy took the name), and
    the kept folders back on sys.path."""
    if _PINNED and sys.modules.get("hyperion") is not _PINNED.get("hyperion"):
        sys.modules.update(_PINNED)
    if _KEEP:
        _keep_on_path()


class Adapter:
    """Base class. Subclasses implement the three translation hooks; decide() does the rest safely.

    One object may play many tables. The kit's table-start hook calls start() (the bot's new_table); a kit with none
    gets it from decide(), lazily on the first decision and again whenever the hand number goes back (a new table).

    `history_source` says where obs.history comes from, and conformance holds the adapter to it:
      "log"      the kit's action log, the whole hand so far, so within a hand every decision's history extends the
                 last one. It is used as it is.
      "partial"  the kit shows some actions (this street only, the last few, ...): the rebuilt log below, extended
                 by the kit's entries where they agree with it.
      "bets"     the kit has no log (make_observation's raises-from-bets stand-in is dropped).
    For "partial" and "bets", decide() rebuilds the hand's log from the states the kit shows
    (hyperion/drills/infer_history.py: each seat's in-hand flag, stack and bet between our decisions; every entry
    true, a gap ends it). For every source, hand_end() adds our last reply and, when the kit shows how the hand
    ended (every seat's chips or deltas, the hands at showdown), the folds after it.

    The whole timed call (G1). decide() is what the kit times, so it reads the clock on its first line and sends the
    whole call to the bot's SafeBot on its way out (hyperion/strategy/safe.py report_call): the governor sees the
    translation, the inference and a held hand end, not `act` alone. There is nothing to wire: a subclass writes the three
    hooks and calls nothing else. An entry whose method does work before decide() passes its own first clock read,
    decide(native, t0) (the templates do). Do not override decide(); if you must, call self._safe.report_call(seconds).
    tools/gate.py fails a package whose decisions do not report.
    """

    history_source = "log"

    def __init__(self, bot: Bot, rules: Rules | None = None):
        from hyperion.drills.infer_history import HistoryInference

        pin_package()
        self.bot = bot
        self.rules = rules or Rules()
        self.seat = 0
        self.started = False
        self.inference = HistoryInference(self.rules)
        self._last_hist: list = []
        self._last_hand = None
        self._pending = None  # a hand end waiting for the next hand's first state (defer_hand_end)
        self._hand_seen = None  # the last decision's hand number, to see a new table the kit did not announce
        self.tables_seen = 0  # new tables found that way (a kit with one bot object for many tables and no hook)
        self.seat_fixes = 0  # tables whose hook named a seat the observations did not (decide() restarted the bot)
        self.fallbacks = 0  # decisions that went to native_safe (the translation or the bot raised)
        self._seat_check = False
        # G1: the whole timed call goes to the bot's SafeBot (hyperion/strategy/safe.py), so its governor sees what the kit
        # times. Nothing to wire in an entry: this constructor does it, decide() reports it. `t0` on decide() moves
        # the clock's start back to the first line of an entry's own method
        safe = bot if isinstance(bot, SafeBot) else getattr(bot, "safe", None)
        self._safe = safe if isinstance(safe, SafeBot) else None
        self._whole = self._safe.expect_reports() if self._safe is not None else False
        if self._whole:
            fn = getattr(bot, "defer_hand_end", None)  # the curve and the dials wait for the member that reads them
            if fn is not None:
                fn(True)
        self._budget = self._safe.end_budget if self._whole else 0.0  # the hand end's budget (hand_end): 0 = no budget
        self._e_call = self._e_end = 0.0  # what a decision costs without a hand end, and a hand end: running means
        self._n_call = 0
        self._floored = False
        self._tail_skips = 0
        self._end_now = 0.0  # the hand end inside the decision in play
        self.tails_lost = self.tails_forced = self.ends_dropped = 0

    # -- translation hooks ------------------------------------------------------------
    def to_observation(self, native: Any) -> Observation:
        raise NotImplementedError

    def from_action(self, action: Action, obs: Observation, native: Any) -> Any:
        raise NotImplementedError

    def native_safe(self, native: Any) -> Any:
        """The kit's own check-if-possible-else-fold, used when translation itself blows up."""
        raise NotImplementedError

    # -- lifecycle ---------------------------------------------------------------------
    def start(self, seat: int, n_players: int, rules: Rules | None = None) -> None:
        repin_package()
        if rules is not None:
            self.rules = rules
        self.seat = seat
        self.n_players = n_players
        self.started = True
        self._pending = None
        self._hand_seen = None
        self._e_call = self._e_end = 0.0  # a warm-up's cold calls and the last table say nothing about this one's
        self._n_call = 0
        self._floored = False
        self._tail_skips = 0
        self._seat_check = True  # the first decision's seat wins over the hook's (a 1-based or relative label)
        self.inference.new_table(self.rules)
        try:
            self.bot.new_table(self.rules, seat, n_players)
        except Exception:  # noqa: BLE001 - never let a bot bug reach the kit
            pass

    def with_history(self, obs: Observation) -> Observation:
        """obs with the history the bot reads: the kit's log, or the one rebuilt from the states (history_source).

        The inference runs on every decision, so its walk is in step for the hand end whatever the source; on a log
        kit it only watches."""
        kit = [] if (obs.extras and obs.extras.get("history_from_bets")) else obs.history
        if self.history_source == "log" and kit:
            if not self.log_at_end or self.conformance is not None:
                self.inference.history(obs)
            out = obs
        else:
            out = self.inference.observe(obs, kit if self.history_source == "partial" else None)
        self._last_hist, self._last_hand = out.history, obs.hand_no
        return out

    conformance = None  # set by hyperion/drills/conformance.py's checked()

    def decide(self, native: Any, t0: float | None = None) -> Any:
        """The kit's timed call, and its report: `t0` the kit's call as the entry's first line read the clock (default:
        now), and the whole call goes to the bot's SafeBot on every way out."""
        if t0 is None:
            t0 = perf_counter()
        reply = self._decide(native)
        safe = self._safe
        if safe is not None:
            dt = perf_counter() - t0
            safe.report_call(dt)
            if self._budget:
                self._note_call(dt)
        return reply

    # The budget-aware hand end (G1, hand_end). A decision's cost and a hand end's, on this box's clock this table. A sample is
    # clipped at 1 ms: one stall of the scheduler says nothing about the box, and these means must never move on a normal one
    def _note_call(self, dt: float) -> None:
        dt -= self._end_now  # the hand end has its own mean
        self._end_now = 0.0
        x = dt if dt < 0.001 else 0.001
        self._n_call += 1
        e = self._e_call = x if self._n_call == 1 else self._e_call + (x - self._e_call) / 16.0
        if self._n_call >= 16:
            # a box this slow plays the first rung of the governor's ladder from now on, without waiting for a cluster of
            # overruns: no shadows, a quarter of a decision for little play (the composite's module doc). A loaded 1x box's
            # mean is under 0.2 ms; coming back is lower than going down, as the rung itself takes a quarter off the mean
            if not self._floored:
                if e > FLOOR_ON_S:
                    self._floored = True
                    self._safe.set_floor(1)
            elif e < FLOOR_OFF_S:
                self._floored = False
                self._safe.set_floor(0)

    def _note_end(self, dt: float) -> None:
        x = dt if dt < 0.001 else 0.001
        self._e_end = x if self._e_end == 0.0 else self._e_end + (x - self._e_end) / 8.0

    def short_of_time(self) -> bool:
        """A typical decision with a hand end inside it would pass the budget: most of those calls would time out on their
        own, reads or no reads. Needs a table's worth of calls: never on a cold start. The line is that high because the reads
        are worth more than the timeouts they cost. Kit B at 3x against batch 8: every tail kept +0.01 ± 0.18 points a table,
        one hand in two without its tail -0.24 ± 0.18 (400 tables each), seven in eight -0.48 ± 0.33 (150 tables), while
        timeouts fell about as far in the first two (docs/drills/climb/g1-log.md)."""
        return bool(self._budget) and self._n_call >= 16 and self._e_call + self._e_end > self._budget

    def _decide(self, native: Any) -> Any:
        global _STAND_IN
        repin_package()
        try:
            if self.conformance is None:  # with_history replaces the stand-in; the conformance report reads it
                _STAND_IN = False
            try:
                obs = self.to_observation(native)
            finally:
                _STAND_IN = True
            # A table start here runs inside the kit's timed decision: quick_start() lets it read and build nothing
            # (hyperion/strategy/tables.py), so what the import-time warm-up loaded is used and the rest is plain.
            if not self.started:
                with quick_start():
                    self.start(obs.seat, obs.n_players)
            elif self._hand_seen is not None and obs.hand_no < self._hand_seen:
                # the hand number went back: a new table, and the kit called no table-start hook (one bot object for
                # the tournament or the night, kit D's handle_new_round only). The bot's new_table, as a fresh one
                # would get (Adapter.start itself: a subclass's start may reset kit state this decision just read).
                with quick_start():
                    Adapter.start(self, obs.seat, obs.n_players)
                self.tables_seen += 1
            elif self._seat_check and obs.seat != self.seat:
                # the hook named our seat differently from the observations (numbered from 1, or by id): the bot's
                # table state follows the seat it is asked to act in
                with quick_start():
                    Adapter.start(self, obs.seat, obs.n_players)
                self.seat_fixes += 1
            self._seat_check = False
            self._hand_seen = obs.hand_no
            if self._pending is not None:
                if self._budget:
                    t = perf_counter()
                    self._deliver(obs)
                    self._end_now = perf_counter() - t
                    self._note_end(self._end_now)
                else:
                    self._deliver(obs)
            try:
                obs = self.with_history(obs)
            except Exception:  # noqa: BLE001 - the bot still decides, on the history make_observation would give
                if not obs.history:
                    obs.history = history_from_bets(obs.street, obs.button, obs.stacks, obs.bets, obs.blinds[1])
            action = self.bot.act(obs).clamp(obs)
            self.inference.acted(action)
            return self.from_action(action, obs, native)
        except Exception:  # noqa: BLE001
            self.fallbacks += 1
            return self.native_safe(native)

    def hand_end(self, hand_no: int, delta: int, n_players: int | None = None, history=None, deltas=None,
                 final_stacks=None, showdown=None, board=()) -> None:
        """The hand is over; pass whatever the kit's hand-end signal has.

        `history` the kit's [(seat, Action)] for the hand; `deltas` every seat's chip change (or `final_stacks`,
        every seat's chips after it); `showdown` {seat: hole cards} for every hand still in at showdown ({} when
        there was none; leave it None when the kit does not say). Without a history the rebuilt one goes to the bot:
        the hand's log up to our last decision, our reply, and the folds after it that the deltas and showdown
        settle. When the signal has none of deltas, final_stacks or showdown (`defer_hand_end`) and some seat had to
        act after our reply owing chips, the bot's hand end waits for the next hand's first state, whose stacks give
        every seat's chips after this hand: it is delivered at the top of that decision (50-200 us of the bot's own
        hand end inside it; `defer_hand_end = False` keeps it at the kit's hand end, untimed, without those
        folds). Rival 3's core (hybrid3_x, the composite) replays the hand's history here, as
        the simulator gives it.

        Budget-aware (G1; the dial `hand_end_ms`, the bot's SafeBot.end_budget). On a slow box that hand end is what breaks
        the timed call it lands in. While a typical decision with it would pass the budget (`short_of_time`), it runs
        here, at the kit's hand end, without those folds; one hand in `tail_every` still waits for its tail, so the reads
        of folds are thinned, never cut off, and `tails_lost` and `tails_forced` count them. On a normal box the means never
        reach it and nothing changes, in any decision."""
        repin_package()
        try:
            if self._pending is not None:  # two hand ends with no decision between them (a walk in our big blind)
                self._deliver(None)
            if (deltas is None and final_stacks is None and showdown is None and self.defer_hand_end
                    and self.inference.hand_no == hand_no and (self.hold_all or self.inference.tail_open())):
                if not self.short_of_time():
                    self._tail_skips = 0
                    self._pending = (hand_no, delta, n_players, history, board)
                    return
                # the budget (G1): held, this hand end would run inside the next timed call, and that call would be the
                # one to time out. It runs here instead, with what the kit says; the folds after our last reply and the
                # other seats' chips stay unknown for this hand. The bound: one hand in `tail_every` still waits for its tail,
                # whatever the budget, so the reads of folds keep coming; tools/gate.py prints both counts
                self._tail_skips += 1
                if self._tail_skips >= self.tail_every:
                    self._tail_skips = 0
                    self.tails_forced += 1
                    self._life("forced")
                    self._pending = (hand_no, delta, n_players, history, board)
                    return
                self.tails_lost += 1
                self._life("tail_lost")
            t = perf_counter()
            self._end(hand_no, delta, n_players, history, deltas, final_stacks, showdown, board)
            if self._whole and not self.hand_end_timed:
                fn = getattr(self.bot, "idle", None)  # this call is on no clock: the curve and the dials, now
                if fn is not None:
                    fn()
            if self._budget:
                t = perf_counter() - t
                self._note_end(t)
                if self.hand_end_stored:
                    self._end_now += t
        except Exception:  # noqa: BLE001
            pass

    defer_hand_end = True
    hold_all = False  # hold every hand end we acted in: every seat's chip change for the bot's stacks (Hero's ICM
    #                  curve), at the cost of the bot's hand end inside the next decision on every hand
    hand_end_timed = False  # the kit times its hand-end callback (the entry templates set it from HAND_END: "eager" is False)
    hand_end_stored = False  # an entry calls hand_end inside the next decision (entry_template.py "store", the closure template)
    log_at_end = False  # a "log" kit whose hand end carries the whole log: the inference has nothing to watch for (closure template)
    tail_every = 2  # short of time: one hand end in this many still waits for the next state, for its tail (hand_end)

    def _life(self, key: str) -> None:
        safe = self._safe
        if safe is not None:
            safe.life[key] += 1

    def drop_hand_end(self, n: int = 1) -> None:
        """An entry's stored hand end, not delivered for the budget (entry_template.py "store", the closure template's recap)."""
        self.ends_dropped += n
        safe = self._safe
        if safe is not None:
            safe.life["dropped"] += n

    def _deliver(self, obs: Observation | None) -> None:
        """The waiting hand end, settled by `obs` when it is the next hand's first state."""
        from hyperion.drills.infer_history import chips_after_hand

        hand_no, delta, n_players, history, board = self._pending
        self._pending = None
        after = deltas = None
        if obs is not None and obs.hand_no == hand_no + 1 and self.inference.hand_no == hand_no:
            after = chips_after_hand(obs, self.rules)
            start = self.inference.start_stacks() if after is not None else None
            if start is not None and len(start) == len(after):
                deltas = [f - b for f, b in zip(after, start)]
            else:
                after = None
        self._end(hand_no, delta, n_players, history, deltas, after, None, board)

    def _end(self, hand_no, delta, n_players, history, deltas, final_stacks, showdown, board) -> None:
        try:
            n = n_players or getattr(self, "n_players", 0) or max(1, self.seat + 1)
            kit = list(history or [])
            if kit and self.history_source == "log":  # the kit's whole log is the answer: nothing to rebuild on the clock
                hist = kit
                inf = self.inference
                inf.live = inf.paused = False
                inf.sent = None
            else:
                shown = None if showdown is None else dict(showdown)
                hist = self.inference.hand_end(final_stacks=final_stacks, deltas=deltas, shown=shown, hand_no=hand_no)
                if self.history_source != "bets":  # (with no log, what the last decision saw starts this: the same walk)
                    seen = self._last_hist if self._last_hand == hand_no else []
                    hist = self.inference.merge(hist, list(seen))
                if kit:
                    hist = self.inference.merge(hist, kit)
            if deltas is None:
                deltas = [0] * n
                deltas[self.seat] = delta
            self.bot.hand_end(HandResult(hand_no=hand_no, deltas=list(deltas), showdown=dict(showdown or {}),
                                         board=tuple(board or ()), history=hist))
        except Exception:  # noqa: BLE001
            pass
        self._last_hist, self._last_hand = [], None


def history_from_bets(street: int, button: int, stacks, bets, big_blind: int) -> list[tuple[int, Action]]:
    """This street's raises, rebuilt from the bets when the kit gives no action history.

    Hero reads who raised (Spot.n_raises, Spot.raiser, the opener and shove reads) from obs.history only; an
    empty history makes every raised pot look unopened, which cost Hero 2.5 points a table in drill 6 (5.9 to
    3.3 on the realistic field). One RAISE per distinct bet level above the street's base (the big blind
    preflop, 0 after), credited to the first seat in acting order at that level; a short all-in below the
    top level is a call, not a raise. Earlier streets' raises and the exact count of re-raises are lost."""
    n = len(bets)
    base = big_blind if street == 0 else 0
    top = max(bets) if n else 0
    if top <= base:  # nobody above the base: no raise to credit (most decisions, and this runs inside the timed call)
        return []
    first = 3 if street == 0 else 1  # UTG preflop, the first seat left of the button after
    order = sorted(range(n), key=lambda x: (x - button - first) % n)
    out: list[tuple[int, Action]] = []
    for level in sorted({b for b in bets if b > base}):
        seats = [x for x in order if bets[x] == level]
        if level < top and all(stacks[x] == 0 for x in seats):
            continue
        out.append((seats[0], Action(ActionKind.RAISE, int(level))))
    return out


class NoLogSeat:
    """A bot fed what a kit with no action log gives it through an adapter that infers nothing: each decision's history
    is this street's raises rebuilt from the bets (make_observation's rule, flagged in extras), and each hand end
    carries only its own chip change. What the reference adapters gave before the inference
    (hyperion/drills/infer_history.py InferSeat is the seat with it); tools/gate.py --kit-log bets seats the in-sim
    baseline this way, for a package whose adapter predates the inference."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.seat = 0
        self.n = 0

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.seat, self.n = seat, n_players
        self.bot.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        import dataclasses

        hist = history_from_bets(obs.street, obs.button, obs.stacks, obs.bets, obs.blinds[1])
        return self.bot.act(dataclasses.replace(obs, history=hist, extras={**obs.extras, "history_from_bets": True}))

    def hand_end(self, result: HandResult) -> None:
        deltas = [0] * len(result.deltas)
        if 0 <= self.seat < len(deltas):
            deltas[self.seat] = result.deltas[self.seat]
        self.bot.hand_end(HandResult(hand_no=result.hand_no, deltas=deltas, showdown={}, board=(), history=[]))

    def variant_decide(self, prompt: dict):
        return self.bot.variant_decide(prompt)


def history_rows(history, discards: dict | None = None, at: int | None = None, tags=None) -> list[list]:
    """obs.history -> the fake dealer's rows [seat, kind, total] (total only for a raise). `discards`
    {seat: card}, in toss order, go in as [seat, "discard", card] at history index `at` (the flop's first
    action), as the dealer logs them; without `at` they go last. `tags` [(street, put)], one per history entry (the
    gate's seat files get them: tools/gate.py GateTable.history_tags), makes each row [seat, kind, total, street, put]:
    the street the action was on and the chips it put in; a discard row is on the flop and puts in 0."""
    if tags is None:
        rows = [[int(s), a.kind.value, int(a.amount) if a.kind is ActionKind.RAISE else 0] for s, a in history]
    else:
        rows = [[int(s), a.kind.value, int(a.amount) if a.kind is ActionKind.RAISE else 0, int(st), int(put)]
                for (s, a), (st, put) in zip(history, tags)]
    if discards:
        pos = len(rows) if at is None else min(at, len(rows))
        extra = [] if tags is None else [1, 0]
        rows[pos:pos] = [[int(s), "discard", int(c), *extra] for s, c in discards.items()]
    return rows


def dealer_state(obs: Observation, discards_at: int | None = None, tags=None, posts=None) -> dict:
    """The fake kits' dealer state (hyperion/drills/fakekits/_table.py) for an Observation: the inverse of
    make_observation, history and face-up discards included. Lists and ints only, so
    tools/gate.py can send it to another process (json turns the int keys of `discards` into strings;
    tools/gate_host.py turns them back). `kit.to_state(...)` and its peers accept it as it is. A seat file's state
    (tools/gate.py, kind seat) also has each history row's street and chips (`tags`, history_rows) and the hand's
    forced bets, `posts` [[seat, "ante" | "sb" | "bb" | "straddle", chips]], so it can build a kit's own log."""
    discards = (obs.extras or {}).get("discards") or {}
    st = {
        "hole": list(obs.hole), "board": list(obs.board), "street": obs.street, "seat": obs.seat,
        "button": obs.button, "stacks": list(obs.stacks), "bets": list(obs.bets), "in_hand": list(obs.in_hand),
        "pot": obs.pot, "to_call": obs.to_call, "min_raise": obs.min_raise, "max_raise": obs.max_raise,
        "legal": sorted(k.value for k in obs.legal), "hand_no": obs.hand_no, "blinds": list(obs.blinds),
        "history": history_rows(obs.history, discards, discards_at, tags),
        "discards": {int(s): int(c) for s, c in discards.items()},
    }
    if posts is not None:
        st["posts"] = [list(p) for p in posts]
    return st


def _legal_word(item) -> str:
    """One entry of a kit's legal list -> its lowercase word: a string, an ActionKind, a dict with a type/action/kind/name
    key, or an object with such an attribute (an enum member's name, a class such as CheckAction)."""
    if isinstance(item, ActionKind):
        return item.value
    if isinstance(item, str):
        return item.strip().lower()
    if isinstance(item, dict):
        for k in _NAME_KEYS:
            v = item.get(k)
            if isinstance(v, str):
                return v.strip().lower()
        raise KeyError(f"legal action {item!r} has none of the keys {_NAME_KEYS}")
    for k in ("name", "value", "kind", "type", "action"):
        v = getattr(item, k, None)
        if isinstance(v, str):
            return v.strip().lower()
    name = getattr(item, "__name__", None) or type(item).__name__
    name = name.lower()
    return name[:-6] if name.endswith("action") and len(name) > 6 else name


_LEGAL_NAMES: dict = {}  # a kit's list of our names -> the frozenset (legal_kinds; no state, the answer depends on the words)


def legal_kinds(legal, to_call: int, my_stack: int) -> frozenset:
    """A kit's legal actions -> frozenset[ActionKind]. Takes our names in any case, the usual other words (bet, the
    one-letter F/K/X/C/R/B, check/call, all-in), a comma or space separated string, dicts ({"type": "raise", ...}),
    ActionKinds and objects (CheckAction). An "all in" is a call when the call already takes every chip, else a raise
    (the raise bounds then end at the all-in). Raises KeyError on a word it does not know: say what the kit means."""
    try:  # the usual case, our names in any case: a list of a dozen shapes, cached (this runs inside the timed call)
        if not isinstance(legal, str):
            key = tuple(legal)
            got = _LEGAL_NAMES.get(key)
            if got is None:
                got = frozenset(KIND_BY_NAME[k.lower()] for k in key)
                if len(_LEGAL_NAMES) < 256:
                    _LEGAL_NAMES[key] = got
            return got
    except (KeyError, AttributeError, TypeError):
        pass
    if isinstance(legal, str):
        t = legal.strip()
        if t.lower() in CHECK_OR_CALL_WORDS:
            legal = [t]
        elif any(sep in t for sep in ",|;"):
            legal = [x for x in t.replace("|", ",").replace(";", ",").split(",") if x.strip()]
        else:
            legal = t.split()
    out = set()
    for item in legal:
        w = _legal_word(item)
        k = KIND_WORDS.get(w)
        if k is None:
            if w in ALL_IN_WORDS or w.replace(" ", "").replace("-", "").replace("_", "") == "allin":
                k = ActionKind.CALL if to_call >= my_stack else ActionKind.RAISE
            elif w in CHECK_OR_CALL_WORDS:
                k = ActionKind.CHECK if to_call <= 0 else ActionKind.CALL
            else:
                raise KeyError(f"legal action {item!r}: not one of {sorted(KIND_WORDS)} or an all-in word; map it in "
                               f"the adapter (TODO 5)")
        out.add(k)
    return frozenset(out)


def raise_bounds(min_raise, max_raise, stacks, bets, seat: int, big_blind: int, raise_legal: bool) -> tuple:
    """(min raise-to, max raise-to, what was fixed) from what the kit gave. Missing (None) bounds are derived: the max is
    my stack plus my bet (no-limit), the min the top bet plus the last raise's increment (the big blind at least,
    from this street's bets: a little high when a short all-in raised, never low). Swapped bounds are put in order; an
    all-in below a full raise (the kit's min above everything I have) leaves one raise, the all-in."""
    fixed = []
    if not raise_legal:
        return int(min_raise or 0), int(max_raise or 0), fixed
    n = len(bets)
    me_ok = 0 <= seat < n and len(stacks) == n
    cap = (stacks[seat] + bets[seat]) if me_ok else None
    cur = max(bets) if n else 0
    if min_raise is not None and max_raise is not None and cur < min_raise <= max_raise and (cap is None or
                                                                                            max_raise <= cap):
        return int(min_raise), int(max_raise), fixed  # a clean kit
    lo = None if min_raise is None else int(min_raise)
    hi = None if max_raise is None else int(max_raise)
    if hi is None or (hi <= 0 and cap is not None):
        if cap is None:
            raise ValueError("max_raise missing and no stack to derive it from")
        hi = cap
        fixed.append("max_raise_derived")
    if lo is None or lo <= 0:
        below = max((b for b in bets if b < cur), default=0)
        lo = cur + max(int(big_blind), cur - below)
        fixed.append("min_raise_derived")
    if lo > hi and (cap is None or hi != cap):
        lo, hi = hi, lo
        fixed.append("raise_bounds_swapped")
    if cap is not None and cur < cap < hi and lo <= cap:  # a max above everything I have (an "unlimited" max)
        hi = cap
        fixed.append("max_raise_capped")
    if lo > hi:
        lo = hi
        fixed.append("all_in_below_min_raise")
    return lo, hi, fixed


def drop_blind_posts(history, big_blind: int, street: int = 0) -> tuple[list, int]:
    """A log that starts with the forced bets as raises (a kit that logs "post 10", "post 20", or antes, as bets): those
    leading RAISEs to the big blind or less are dropped (a real raise preflop goes above the big blind). After the
    flop only when the first is below the big blind (a small blind or an ante: a log of this street alone can start
    with a min bet of exactly the big blind). Returns the history and how many were dropped. Hero reads raises from
    history: two posts read as a raise and a re-raise."""
    if not history:
        return history, 0
    a0 = history[0][1]
    if a0.kind is not ActionKind.RAISE or a0.amount > big_blind or (street > 0 and a0.amount >= big_blind):
        return history, 0
    i = 0
    for _, a in history:
        if a.kind is ActionKind.RAISE and a.amount <= big_blind:
            i += 1
        else:
            break
    return (history[i:], i) if i else (history, 0)


FLOOR_ON_S, FLOOR_OFF_S = 0.0003, 0.00019  # a decision's mean, without a hand end, that holds the ladder's first rung (_note_call)
_STAND_IN = True  # False while Adapter.decide translates for a kit with no log: the rebuilt log replaces the stand-in


def make_observation(*, hole, board, street, seat, button, stacks, bets, in_hand, pot, to_call=None, min_raise=None,
                     max_raise=None, legal: Iterable, hand_no, blinds, history=None, extras=None) -> Observation:
    """Assemble an Observation from already-translated pieces. `legal`: our names fold / check / call / raise, or the
    kit's own words, dicts or objects (legal_kinds). Raise bounds are raise-to totals; missing ones (None) are derived,
    swapped or impossible ones put right (raise_bounds); to_call None is max(bets) - my bet, capped by my stack.
    A history that starts with the blinds posted as raises loses those entries (drop_blind_posts).
    No `history` (or an empty one) while somebody has bet above the blind: raises are rebuilt from the bets, and
    `extras["history_from_bets"]` says so (the shipped bot's core then reads no history: a replay of raises alone
    would book every raiser as a seat that raises every hand). What was put right is listed in
    `extras["kit_fixes"]` (conformance counts it), absent when nothing was. `extras`: the twist's own entries, as the
    variant hooks would put them (cards an opponent is known to hold: {"known": {seat: cards}}, our own cards
    included when he holds them too; face-up cards: {"exposed": {seat: card}}; hyperion/strategy/known.py)."""
    stacks, bets, seat = list(stacks), list(bets), int(seat)
    me_ok = 0 <= seat < len(stacks) and len(bets) == len(stacks)
    my_stack = stacks[seat] if me_ok else 0
    if to_call is None:
        to_call = max(0, min(max(bets) - bets[seat], my_stack)) if me_ok else 0
    to_call = int(to_call)
    kinds = legal_kinds(legal, to_call, my_stack)
    lo, hi, fixed = raise_bounds(min_raise, max_raise, stacks, bets, seat, int(blinds[1]), ActionKind.RAISE in kinds)
    hist = list(history or [])
    extras = dict(extras) if extras else {}
    if hist:
        hist, dropped = drop_blind_posts(hist, int(blinds[1]), int(street))
        if dropped:
            fixed.append("blind_posts_dropped")
    if not hist:
        if _STAND_IN:
            hist = history_from_bets(int(street), int(button), stacks, bets, int(blinds[1]))
        extras["history_from_bets"] = True
    if fixed:
        extras["kit_fixes"] = tuple(fixed)
    return Observation(
        hole=tuple(hole), board=tuple(board), street=int(street), seat=seat, button=int(button),
        stacks=stacks, bets=bets, in_hand=list(in_hand), pot=int(pot), to_call=to_call,
        min_raise=lo, max_raise=hi, legal=kinds, hand_no=int(hand_no),
        blinds=(int(blinds[0]), int(blinds[1])), history=hist, extras=extras,
    )


# ------------------------------------------------------------------ kit A: class-based, strings

_A_STREETS = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}


def _a_card(s: str) -> int:
    return parse_card(s.replace("10", "T"))


def _a_history(log) -> list[tuple[int, Action]]:
    """kit A action_log [(index, "FOLD" | "CHECK" | "CALL" | "RAISE:120" | "DISCARD:Ah")] -> obs.history.
    Discards are not betting actions and are skipped; anything unreadable is skipped, never raised."""
    out: list[tuple[int, Action]] = []
    for item in log or ():
        try:
            seat, text = item
            word, _, amount = str(text).partition(":")
            kind = KIND_BY_NAME.get(word.lower())
            if kind is None:
                continue
            out.append((int(seat), Action(kind, int(amount) if kind is ActionKind.RAISE else 0)))
        except Exception:  # noqa: BLE001 - a malformed entry costs one history line, not the decision
            continue
    return out


class KitAAdapter(Adapter):
    """state attributes: hand, community, street, my_index, dealer_index, players[].stack/.bet/.folded,
    pot_size (includes current bets), current_bet, my_bet, legal_moves, min_raise, max_raise (totals)."""

    def to_observation(self, s: Any) -> Observation:
        stacks = [p.stack for p in s.players]
        bets = [p.bet for p in s.players]
        return make_observation(
            hole=[_a_card(c) for c in s.hand], board=[_a_card(c) for c in s.community],
            street=_A_STREETS[s.street], seat=s.my_index, button=s.dealer_index,
            stacks=stacks, bets=bets, in_hand=[not p.folded for p in s.players],
            pot=s.pot_size - sum(bets), to_call=min(s.current_bet - s.my_bet, s.my_stack),
            min_raise=s.min_raise, max_raise=s.max_raise, legal=s.legal_moves,
            hand_no=s.hand_number, blinds=(s.small_blind, s.big_blind),
            history=_a_history(getattr(s, "action_log", None)),
        )

    def from_action(self, a: Action, obs: Observation, s: Any) -> str:
        if a.kind is ActionKind.RAISE:
            return f"RAISE:{a.amount}"
        return a.kind.value.upper()

    def native_safe(self, s: Any) -> str:
        return "CHECK" if "CHECK" in getattr(s, "legal_moves", ()) else "FOLD"


class KitAAgent:
    """Drop-in `Agent` for kit A around any of our bots. Duck-types kit_a.kit.Agent."""

    def __init__(self, bot: Bot | None = None):
        self.adapter = KitAAdapter(bot or _default_bot())

    def new_game(self, my_index: int, n_players: int, starting_stack: int) -> None:
        self.adapter.start(my_index, n_players)

    def act(self, state: Any) -> str:
        return self.adapter.decide(state)

    def hand_over(self, hand_number: int, chip_change: int) -> None:
        self.adapter.hand_end(hand_number, chip_change)


# ------------------------------------------------------------------ kit B: dict in, dict out, increments

_B_SUIT = {"C": 0, "D": 1, "H": 2, "S": 3, "c": 0, "d": 1, "h": 2, "s": 3}


def _b_card(d: dict) -> int:
    return (int(d["rank"]) - 2) * 4 + _B_SUIT[d["suit"]]


_B_STREETS = {0: 0, 3: 1, 4: 2, 5: 3}


class KitBAdapter(Adapter):
    """observation dict: hand.cards[{rank,suit}], table.{board,pot,button,players[{seat,chips,committed,
    active}]}, you.{seat,to_call,min_raise_by,max_raise_by}, actions, street = board count."""

    history_source = "bets"  # the kit has no action log

    def to_observation(self, o: dict) -> Observation:
        players = sorted(o["table"]["players"], key=lambda p: p["seat"])
        bets = [p["committed"] for p in players]
        current = max(bets)
        return make_observation(
            hole=[_b_card(c) for c in o["hand"]["cards"]], board=[_b_card(c) for c in o["table"]["board"]],
            street=_B_STREETS[int(o["street"])], seat=o["you"]["seat"], button=o["table"]["button"],
            stacks=[p["chips"] for p in players], bets=bets, in_hand=[bool(p["active"]) for p in players],
            pot=o["table"]["pot"], to_call=o["you"]["to_call"],
            min_raise=current + o["you"]["min_raise_by"], max_raise=current + o["you"]["max_raise_by"],
            legal=o["actions"], hand_no=o["hand_id"], blinds=(o["blinds"]["sb"], o["blinds"]["bb"]),
        )

    def from_action(self, a: Action, obs: Observation, o: dict) -> dict:
        if a.kind is ActionKind.RAISE:
            return {"action": "raise", "by": a.amount - max(obs.bets)}
        return {"action": a.kind.value}

    def native_safe(self, o: Any) -> dict:
        try:
            return {"action": "check" if "check" in o["actions"] else "fold"}
        except Exception:  # noqa: BLE001
            return {"action": "fold"}


def make_kit_b_module(bot: Bot | None = None) -> tuple[Callable, Callable, Callable]:
    """(decide, on_table_start, on_hand_end) closures to expose at module level in a kit B submission."""
    adapter = KitBAdapter(bot or _default_bot())

    def decide(observation: dict) -> dict:
        return adapter.decide(observation)

    def on_table_start(info: dict) -> None:
        adapter.start(info["seat"], info["players"])

    def on_hand_end(info: dict) -> None:
        adapter.hand_end(info["hand_id"], info["delta"])

    return decide, on_table_start, on_hand_end


# ------------------------------------------------------------------ kit C: line protocol

class KitCAdapter(Adapter):
    """Decision line clauses: H D S K B C E I O L V T (see kit_c/kit.py). Replies F/K/C/R<total>."""

    history_source = "bets"  # the kit has no action log

    @staticmethod
    def clauses(line: str) -> dict[str, str]:
        return {tok[0]: tok[1:] for tok in line.split() if tok}

    def to_observation(self, line: str) -> Observation:
        c = self.clauses(line)
        stacks = [int(x) for x in c["C"].split(",")]
        bets = [int(x) for x in c["E"].split(",")]
        seat = self.seat
        legal, lo, hi = [], 0, 0
        for tok in c["L"].split(","):
            if tok == "F":
                legal.append("fold")
            elif tok == "K":
                legal.append("check")
            elif tok == "C":
                legal.append("call")
            elif tok.startswith("R"):
                legal.append("raise")
                lo, hi = (int(x) for x in tok[1:].split("-"))
        sb, bb = (int(x) for x in c["V"].split("/"))
        return make_observation(
            hole=[parse_card(x) for x in c["K"].split(",")],
            board=[] if c["B"] == "-" else [parse_card(x) for x in c["B"].split(",")],
            street=int(c["S"]), seat=seat, button=int(c["D"]), stacks=stacks, bets=bets,
            in_hand=[ch == "1" for ch in c["I"]], pot=int(c["O"]),
            to_call=min(max(bets) - bets[seat], stacks[seat]), min_raise=lo, max_raise=hi,
            legal=legal, hand_no=int(c["H"]), blinds=(sb, bb),
        )

    def from_action(self, a: Action, obs: Observation, line: str) -> str:
        if a.kind is ActionKind.RAISE:
            return f"R{a.amount}"
        return {"fold": "F", "check": "K", "call": "C"}[a.kind.value]

    def native_safe(self, line: str) -> str:
        try:
            return "K" if "K" in self.clauses(line)["L"].split(",") else "F"
        except Exception:  # noqa: BLE001
            return "F"

    def serve(self, inp=None, out=None) -> None:
        """Run the stdin/stdout loop until Q or EOF. The T line gets OK; L lines get an action."""
        inp = inp or sys.stdin
        out = out or sys.stdout
        for line in inp:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Q"):
                break
            c = self.clauses(line)
            if line.startswith("T") and "P" in c:
                self.start(int(c["P"]), int(c["T"]))
                out.write("OK\n")
                out.flush()
            elif "X" in c and "W" in c:
                self.hand_end(int(c["X"]), int(c["W"]))
            elif "L" in c:
                out.write(self.decide(line) + "\n")
                out.flush()


def _default_bot() -> Bot:
    """The bot hyperion/ship.py ships (`ship.make_bot()`: SHIP with its DIALS, which a package records), else the
    cheap stand-in. HYPERION_DRILL_BOT=cheap forces the stand-in (adapter tests measure translation, not the bot)."""
    if os.environ.get("HYPERION_DRILL_BOT") == "cheap":
        from hyperion.drills.cheapbot import CheapBot

        return CheapBot()
    try:
        from hyperion.ship import make_bot  # type: ignore

        return make_bot()
    except Exception:  # noqa: BLE001 - not there yet, or broken: the drill must still run
        from hyperion.drills.cheapbot import CheapBot

        return CheapBot()


# ------------------------------------------------------------------ kit D: MIT-style Bot, namedtuple states

_D_STREETS = {0: 0, 3: 1, 4: 2, 5: 3}
_D_KIND_BY_CLASS = {"FoldAction": "fold", "CallAction": "call", "CheckAction": "check", "RaiseAction": "raise"}
_D_CLASS_BY_KIND = {v: k for k, v in _D_KIND_BY_CLASS.items()}


def _d_round_total(round_state: Any) -> int:
    """Chips at the table at round start: walk previous_state to the root, where pips are just the blinds."""
    rs = round_state
    while getattr(rs, "previous_state", None) is not None:
        rs = rs.previous_state
    return sum(rs.stacks) + sum(rs.pips)


class KitDAdapter(Adapter):
    """native = (game_state, round_state, active). RoundState fields: button, street (0/3/4/5), pips, stacks,
    hands (card strings, ours filled), board, acting, in_hand, blinds, last_raise, previous_state;
    legal_actions() is a set of action classes (no FoldAction when a check is free); raise_bounds() are
    raise-to totals. Replies are instances of the classes found in the legal set, so no kit import."""

    history_source = "bets"  # previous_state holds the hand, but this adapter does not walk it: the inference does

    def __init__(self, bot: Bot, rules: Rules | None = None):
        super().__init__(bot, rules)
        self.round_total: int | None = None
        self._classes: dict[str, Any] = {}

    def new_round(self, game_state: Any, round_state: Any, active: int) -> None:
        self.round_total = sum(round_state.stacks) + sum(round_state.pips)
        if not self.started:
            self.start(active, len(round_state.stacks))

    def to_observation(self, native: Any) -> Observation:
        game_state, rs, seat = native
        stacks, pips = list(rs.stacks), list(rs.pips)
        self._classes = {cls.__name__: cls for cls in rs.legal_actions()}
        legal = [_D_KIND_BY_CLASS[name] for name in self._classes]
        lo, hi = rs.raise_bounds() if "raise" in legal else (0, 0)
        total = self.round_total if self.round_total is not None else _d_round_total(rs)
        return make_observation(
            hole=[parse_card(c) for c in rs.hands[seat]], board=[parse_card(c) for c in rs.board],
            street=_D_STREETS[int(rs.street)], seat=seat, button=rs.button, stacks=stacks, bets=pips,
            in_hand=list(rs.in_hand), pot=max(0, total - sum(stacks) - sum(pips)),
            to_call=min(max(pips) - pips[seat], stacks[seat]), min_raise=lo, max_raise=hi, legal=legal,
            hand_no=int(game_state.round_num) - 1, blinds=rs.blinds,
        )

    def from_action(self, a: Action, obs: Observation, native: Any) -> Any:
        classes = self._classes
        if a.kind is ActionKind.RAISE:
            return classes["RaiseAction"](a.amount)
        cls = classes.get(_D_CLASS_BY_KIND[a.kind.value]) or classes.get("CheckAction") or classes.get("FoldAction")
        return cls()

    def native_safe(self, native: Any) -> Any:
        try:
            classes = {cls.__name__: cls for cls in native[1].legal_actions()}
        except Exception:  # noqa: BLE001 - native is not even a state; use the classes seen last time
            classes = self._classes
        cls = classes.get("CheckAction") or classes.get("FoldAction")
        return cls() if cls is not None else None

    def round_over(self, game_state: Any, terminal_state: Any, active: int) -> None:
        """Every seat's delta and the hands shown at showdown: the inference settles the folds after our last reply."""
        try:
            last = terminal_state.previous_state
            shown = {s: tuple(parse_card(c) for c in h) for s, h in enumerate(last.hands) if h and s != active}
            deltas = list(terminal_state.deltas)
            self.hand_end(int(game_state.round_num) - 1, deltas[active], len(deltas), deltas=deltas, showdown=shown,
                          board=tuple(parse_card(c) for c in last.board))
        except Exception:  # noqa: BLE001
            pass


class KitDBot:
    """Drop-in MIT-style Bot around any of our bots. Duck-types kit_d.kit.Bot (three hooks)."""

    def __init__(self, bot: Bot | None = None):
        self.adapter = KitDAdapter(bot or _default_bot())

    def handle_new_round(self, game_state: Any, round_state: Any, active: int) -> None:
        self.adapter.new_round(game_state, round_state, active)

    def get_action(self, game_state: Any, round_state: Any, active: int) -> Any:
        return self.adapter.decide((game_state, round_state, active))

    def handle_round_over(self, game_state: Any, terminal_state: Any, active: int) -> None:
        self.adapter.round_over(game_state, terminal_state, active)


# ------------------------------------------------------------------ kit S: one quirk per shape (R3)

class KitSAdapter(Adapter):
    """Fake kit S (hyperion/drills/fakekits/kit_s): one dict per decision, its quirk named in native["rules"] as a rule
    sheet names it. Written the way the template asks: cards through parse_card (any format), legal moves and the raise
    bounds as the kit gives them (make_observation puts them right), seats through the rule sheet's numbering, amounts
    through its convention both ways."""

    LOG = {"full": "log", "own": "partial", "last3": "partial", "none": "bets"}

    def __init__(self, bot: Bot, rules: Rules | None = None):
        super().__init__(bot, rules)
        self.amounts, self.base, self.raise_word = "to", 0, "raise"

    def to_observation(self, o: dict) -> Observation:
        r = o.get("rules") or {}
        self.amounts = r.get("amounts", "to")
        self.base = base = int(r.get("seat_base", 0))
        self.history_source = self.LOG.get(r.get("log", "full"), "partial")
        players = sorted(o["players"], key=lambda p: p["seat"])
        bets = [int(p["bet"]) for p in players]
        seat = int(o["me"]) - base
        legal = o["legal"]
        words = [_legal_word(x) for x in (legal.replace("|", ",").split(",") if isinstance(legal, str) else legal)]
        self.raise_word = next((w for w in words if w in ("raise", "bet", "all-in", "allin", "all_in")), "raise")
        lo, hi = o.get("min"), o.get("max")
        if lo is not None:
            lo, hi = self.to_total(lo, bets, seat), self.to_total(hi, bets, seat)
        hist = [] if "log" not in o else [
            (int(e["seat"]) - base, Action(KIND_WORDS[str(e["act"]).lower()], int(e.get("to", 0) or 0)))
            for e in o["log"] if str(e["act"]).lower() in KIND_WORDS]
        return make_observation(
            hole=[parse_card(c) for c in o["hole"]], board=[parse_card(c) for c in o["board"]],
            street=_B_STREETS[len(o["board"])], seat=seat, button=int(o["button"]) - base,
            stacks=[p["stack"] for p in players], bets=bets, in_hand=[bool(p["in"]) for p in players],
            pot=o["pot"], to_call=o.get("to_call"), min_raise=lo, max_raise=hi, legal=legal, hand_no=o["hand"],
            blinds=o["blinds"], history=hist,
        )

    def to_total(self, amount: int, bets, seat: int) -> int:
        if self.amounts == "by":
            return int(amount) + max(bets)
        if self.amounts == "put_in":
            return int(amount) + bets[seat]
        return int(amount)

    def from_action(self, a: Action, obs: Observation, o: dict) -> dict:
        if a.kind is ActionKind.RAISE:
            amt = a.amount - (max(obs.bets) if self.amounts == "by" else obs.bets[obs.seat] if self.amounts == "put_in"
                              else 0)
            return {"act": self.raise_word, "amount": int(amt)}
        return {"act": a.kind.value, "amount": 0}

    def native_safe(self, o: Any) -> dict:
        try:
            legal = o["legal"]
            words = [_legal_word(x) for x in (legal.split(",") if isinstance(legal, str) else legal)]
            return {"act": "check" if "check" in words else "fold", "amount": 0}
        except Exception:  # noqa: BLE001
            return {"act": "fold", "amount": 0}


class KitSAgent:
    """Kit S's `Agent`: new_table(info) at each table start (`hook=False`: never called, one object for every table),
    act(native) -> reply, hand_over(hand_no, delta)."""

    def __init__(self, bot: Bot | None = None, hook: bool = True):
        self.adapter = KitSAdapter(bot or _default_bot())
        self.hook = hook

    def new_table(self, info: dict) -> None:
        if self.hook:
            self.adapter.start(int(info["seat"]), int(info["players"]))  # the kit's label: decide() checks it

    def act(self, native: dict) -> dict:
        return self.adapter.decide(native)

    def hand_over(self, hand_no: int, delta: int) -> None:
        self.adapter.hand_end(hand_no, delta)
