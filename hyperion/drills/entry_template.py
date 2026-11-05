"""Tonight's entry for a kit that imports one file and builds a bot object from it (a class with a decision method and
optional table-start and hand-end callbacks: fake kit A, drill 8's kit F, drill 9's kit G). Copy it to
`submission/<the kit's entry file>` beside `submission/adapter.py` (from adapter_template.py) and fill the TODOs in
order. An event-driven kit (one call per event, no state snapshot): event_player_template.py instead.

What it does without being asked, each from a drill:
- Everything is imported, built, started for a table and warmed at module import, and the package is pinned there
  (`pin_package`). Kit F's loader unloads our modules after Agent() is built (drill 8), kit G's before (drill 9); an
  import inside a later call then fails, and the callers that swallow it play misconfigured. Every method starts with
  `repin_package()`, which puts the modules back and this folder back on sys.path (it survives a sys.path.remove).
- A timed hand-end callback (kits E, F, G: 1 ms, and a late one check/folds our NEXT decision): HAND_END "defer"
  makes the bot's hand end deferrable (`defer_hand_end(True)`): the callback runs only its light part, and the ICM
  curve and the profiler's dials wait for the Hero that decides next (drill 9: the composite's whole hand end ran
  1-5 ms under load and forced 0.3-0.9% of the next decisions). "store" moves even the light part into the next
  decision; measured on kit G it trades the forced check/folds for twice the late decisions (TODO 0).
- The warm-up's made-up decisions never reach the HYPERION_CHECK=1 conformance report (`warmed`).
- One module-level adapter plays ONE TABLE AT A TIME per process. Ask the rule sheet; a kit that interleaves tables in one
  process needs a table per adapter, as closure_entry_template.py's TABLES_AT_ONCE does it.
- Every kit call is wrapped: nothing raises into the kit; an answer outside the kit's set is its check-or-fold.
- The governor sees what the kit times (G1): `decide` reads the clock on its first line and passes it to Adapter.decide, which
  reports the whole call to the bot's SafeBot. A stored hand end (HAND_END "store") that would break the timed call it lands in
  is dropped, at most STORE_SKIP_MAX in a row, and counted (`dropped` on tools/gate.py's governor line).

Checks, in order: the kit's simulator with HYPERION_CHECK=1 (0 violations, 0 exceptions, 0 late hand ends, and this
file's own error line at exit reads 0); tools/pack.py; tools/gate.py with submission/gate_seat.py (class Seat from
tools/gate_host.KitA; hyperion/drills/gate_seat_template.py's `by_street` builds the kit's per-street log).
"""
from __future__ import annotations

import atexit
import json
import os
import sys
from collections import Counter
from time import perf_counter

_HERE = os.path.dirname(os.path.abspath(__file__))
# in the package tools/pack.py builds, hyperion/ sits beside this file; run from the repo's submission/, one level up
_ROOTS = (_HERE,) if os.path.isdir(os.path.join(_HERE, "hyperion")) else (os.path.dirname(_HERE), _HERE)
for _p in _ROOTS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hyperion import ship  # noqa: E402
from hyperion.core.types import Rules  # noqa: E402
from hyperion.drills.adapter import pin_package, repin_package  # noqa: E402
from hyperion.drills.conformance import warmed  # noqa: E402
from hyperion.tablegen import rules_from_dict  # noqa: E402

from adapter import history, make_adapter  # noqa: E402  submission/adapter.py: a sibling in the zip, never submission.


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules()


RULES = load_rules()
SEATS = RULES.n_players
ERRORS: Counter = Counter()  # what the wrappers swallowed; printed at exit under HYPERION_CHECK=1

# TODO 0  from the RULE SHEET: the hand-end callback's clock (prompt 01 asks whether callbacks are timed).
#   "eager"  untimed: the whole hand end runs in the callback, outside every clock.
#   "defer"  timed (kits E, F, G: 1 ms, a late one check/folds our next decision): bot.defer_hand_end(True); the
#            callback runs the light part (the hand's log, the chip chain, rival 3's replay: the composite's 20 us
#            against 105 us whole, p99 64 against 334 us), and the ICM curve and dials (80 us, p99 270) wait for the
#            Hero that decides next, which computes only its own.
#   "store"  the callback only stores the result; the next decision delivers it (a callback budget far below 0.1 ms).
#   Kit G, the same deals at load 7-9 (docs/drills/prompt-drill-9.md, H5): forced check/folds eager 30-234 per 150-200
#   tables, defer 1-33, store 0-3; late decisions eager 15-223, defer 48-206, store 77-452 (the stored hand end puts
#   p50 +90 us and p99 +300 us on the first decision of every hand). Points level within noise.
HAND_END = "defer"
STORE_SKIP_MAX = 1  # "store": stored hand ends dropped in a row while the budget is short (the next one is delivered)

# TODO 1  the kit's answers: the closed set it accepts (kit G's tokens), or None when it takes values (kit F's int
#   chips, kit A's "RAISE:<total>"), and its fold, the answer when even native_safe fails.
ANSWERS: frozenset | None = None
FOLD = None


def build():
    """A ship bot behind tonight's adapter, started for a table: every table it reads, and this bot's own modules, are
    loaded and built now (a table start costs 5-70 ms cold), never inside a timed call."""
    bot = ship.make_bot()
    if HAND_END != "eager":
        bot.defer_hand_end(True)
    ad = make_adapter(bot, RULES)
    ad.hand_end_timed = HAND_END != "eager"
    ad.hand_end_stored = HAND_END == "store"
    ad.start(0, SEATS, RULES)
    return ad


# TODO 2  WARM-UP: one of the kit's own states per street and one hand-end result, in the kit's shape (its README's
#   example, its tests' fixtures; drill 9's _FakeState in docs/drills/drill9/bot.py), so the adapter's translation and
#   the bot's decision path have run once before the kit's clock starts. Empty lists still load every table (build());
#   the first decisions are then a little slower (lazy imports), never wrong.
def warm_states() -> list:
    return []


def warm_results() -> list:
    return []


def warm_up(ad) -> None:
    for s in warm_states():
        try:
            ad.decide(s)
        except Exception:  # noqa: BLE001
            ERRORS["warm_up"] += 1
    for r in warm_results():
        try:
            hand_end(ad, r)
        except Exception:  # noqa: BLE001
            ERRORS["warm_up"] += 1
    try:
        ad.start(0, SEATS, RULES)  # the kit's first table starts clean
    except Exception:  # noqa: BLE001
        ERRORS["warm_up"] += 1
    warmed(ad)  # the conformance report forgets the made-up hand
    ERRORS.pop("deltas_sum", None)  # a made-up hand end need not add up


def hand_end(ad, r) -> None:
    """TODO 3  the kit's hand-end result -> Adapter.hand_end, with everything it carries (adapter_template TODO 8): the
    hand's actions (history), every seat's chip change (deltas, or final_stacks), the hands shown (showdown, {} when
    none; leave it None when the kit does not say), the board. The names below are kit G's (offsets from us).

    TODO 3a  `won`: chips collected or net change? The README says which; read it, then one of:
      net change (drill 9's kit G: each seat's chip change for the hand):
          deltas = [int(w) for w in r.won]
      collected (drill 11's kit I: what each seat took from the pots, sum(paid[s]) its cost):
          deltas = [int(w) - int(sum(p)) for w, p in zip(r.won, r.paid)]
    The wrong one feeds the bot wrong stacks for the rest of the table and nothing raises (drill 11 pasted kit G's line
    onto kit I's collected chips). Right, the deltas sum to 0 (no rake): a hand end that does not is counted
    (`deltas_sum` on the error line)."""
    deltas = [int(x) for x in r.won]  # net change (kit G)
    if sum(deltas) != 0:
        ERRORS["deltas_sum"] += 1
    shown = {i: tuple(x) for i, x in enumerate(r.shown or ()) if x}
    ad.hand_end(int(r.hand), deltas[0], SEATS, history=history(r.log), deltas=deltas, showdown=shown,
                board=tuple(r.board))


def table_over(r) -> bool:
    """TODO 3b  the result ends our table (we busted, or the table finished): nothing stored for it is delivered."""
    return bool(getattr(r, "table_over", False) or getattr(r, "place", 0))


_SPARE = [build()]  # the first Agent takes this one, already warm
warm_up(_SPARE[0])
pin_package(*_ROOTS)  # here, at import: a loader may unload our modules before it builds the Agent (kit G)


class Agent:
    """TODO 4  the kit's class and method names (kit A: new_game / act / hand_over(hand, delta); kit F: new_table / act
    / hand_over(r); kit G: begin_table / decide / hand_over(r)). Every method starts with repin_package()."""

    def __init__(self):
        repin_package()
        self.ad = _SPARE.pop() if _SPARE else build()  # a second Agent in the process builds and starts its own
        self.pending: list = []
        self.skipped = 0

    def begin_table(self, info) -> None:
        """TODO 5  our seat and the seat count from the kit's table start (0 when the kit numbers seats from us)."""
        repin_package()
        self.pending.clear()  # the last table's hand ends: nothing more is played there
        try:
            self.ad.start(0, SEATS, RULES)
        except Exception:  # noqa: BLE001
            ERRORS["table_start"] += 1

    def decide(self, s):
        t0 = perf_counter()  # first, always: the kit's clock is running (Adapter.decide reports the whole call to the governor)
        repin_package()
        if self.pending:
            self._flush()
        try:
            out = self.ad.decide(s, t0)  # Adapter.decide: a translation or bot failure is already the kit's check-or-fold
            if ANSWERS is None or out in ANSWERS:
                return out
            ERRORS["bad_answer"] += 1
        except Exception:  # noqa: BLE001
            ERRORS["decide"] += 1
        try:
            return self.ad.native_safe(s)
        except Exception:  # noqa: BLE001
            return FOLD

    def hand_over(self, r) -> None:
        if HAND_END == "store":
            if table_over(r):
                self.pending.clear()
            else:
                self.pending.append(r)  # nothing else here (TODO 3: copy r's fields if the kit reuses the object)
            return
        repin_package()
        try:
            hand_end(self.ad, r)
        except Exception:  # noqa: BLE001
            ERRORS["hand_end"] += 1

    def _flush(self) -> None:
        """The stored hand ends (HAND_END "store"), in order, before the next decision reads the table. Inside the timed
        call: when a typical decision with one would pass the budget it is dropped instead, at most STORE_SKIP_MAX in a row
        (the bot's reads of that hand stop at our last decision in it; a bot that misses a hand end plays on)."""
        pend, self.pending = self.pending, []
        if self.ad.short_of_time() and self.skipped < STORE_SKIP_MAX:
            self.skipped += 1
            self.ad.drop_hand_end(len(pend))
            return
        self.skipped = 0
        for r in pend:
            try:
                hand_end(self.ad, r)
            except Exception:  # noqa: BLE001
                ERRORS["hand_end"] += 1


def _report() -> None:
    try:
        sys.stderr.write("entry: swallowed errors " + (", ".join(f"{k} {v}" for k, v in sorted(ERRORS.items())) or "0")
                         + "\n")
    except Exception:  # noqa: BLE001
        pass


if os.environ.get("HYPERION_CHECK") == "1":
    atexit.register(_report)
