"""Tonight's entry for a kit whose bot is ONE MODULE FUNCTION RETURNING A CLOSURE (drill 12's kit J: `sit_down(table)`, 25 ms,
returns the `decide(v)` for that table, 1 ms; no other callback, a finished hand arrives as `v.recap` inside the next timed
decide). Copy it to `submission/<the kit's entry file>` (kit J: bot.py) beside `submission/adapter.py` and fill the TODOs in
order. Kit J's shape is the worked default: tags per table and no seat numbers, amounts in big blinds, cards as a bit mask,
string answers. The adapter it expects is `docs/drills/drill12/adapter.py`'s: `to_observation`, `from_action`, `native_safe`,
module-level `cards(mask)` and `history(log, bb, seat_of)`, and the attributes `seat_of`, `n` and `start_stack` that TODO 4 sets. A kit
with plain module-level functions and a table hook: module_entry_template.py; a bot object: entry_template.py; the bot as
its own process: process_entry_template.py.

What it does without being asked, each from drill 12 unless marked:
- NOTHING IMPORTS AFTER IMPORT TIME (drill 11). Everything is imported, built, started for a table and warmed here, and the
  package is pinned (`pin_package`); sit_down and decide start with `repin_package()`.
- ONE ADAPTER, ONE TABLE AT A TIME. The adapter and the bot behind it hold one table's state, so one process plays one table
  per adapter. TABLES_AT_ONCE (TODO 0) builds that many at import, and sit_down takes the one whose table spoke last longest
  ago. A kit that interleaves more tables than that in one process is not played wrong in silence: the table that lost
  its adapter answers the kit's check-or-fold, `table_overlap` is counted on the error line, and the first one writes a
  line to stderr. A kit's simulator that plays tables in turn never trips it, so read the rule sheet's answer.
- THE HAND END IS ON THE CLOCK. `v.recap` is delivered inside the timed decide, so HAND_END is "defer" (TODO 1) and the bot's
  deferred work lands in the same call: there is no untimed moment to move it to. tools/latency.py's numbers leave this
  out; the gate's and the kit's simulator's do not.
- THE GOVERNOR SEES ALL OF IT (G1). `decide` reads the clock on its first line and passes it to Adapter.decide, which reports
  the whole call, the recap included, to the bot's SafeBot. And the recap minds the budget: when a typical decision with one
  would pass 3/4 of the kit's limit (`short_of_time`), only the chip chain runs and the bot's hand end is dropped, at most
  RECAP_SKIP_MAX in a row, and counted (`dropped` on tools/gate.py's governor line). The bot's reads of that hand stop at our
  last decision in it. On a normal box the means never get there and nothing changes.
- A TABLE START COLLECTS NOTHING: no `gc.collect()` here (a full one is 4-29 ms with our tables, against kit J's 25 ms).
  Hero's table start only freezes (hyperion/strategy/hero.py, the collector block); kits that collect between tables do
  it on their own time. Check it: `python tools/latency.py --table-start --budget-ms <the kit's limit> --copies <our seats>`.
- A timeout or an error is the KIT's check-or-fold, whatever `native_safe` says: under a twist that makes folding fatal, the
  milliseconds are worth whole tables. Nothing here catches BaseException: the kit's hard stop must end the call.
- sit_down checks the first table's points, blinds and stack against rules_tonight.json; a difference is counted on the
  error line (drill 11). A hand end whose deltas do not sum to 0 is counted too (`deltas_sum`): `net` read wrong.
- The warm-up's made-up decisions never reach the HYPERION_CHECK=1 conformance report (`warmed`).

Checks, in order: the kit's simulator with HYPERION_CHECK=1 (0 violations, 0 exceptions; this file's error line at exit
reads 0, and its `setup` column 0); tools/pack.py (`--import-budget` the kit's, both size caps); tools/gate.py with
submission/gate_seat.py from closure_gate_seat_template.py (`--kit submission/gate_seat.py --entry bot.py
--setup-budget-ms <the kit's limit>`, plus `--variant submission/tonight.py:variant` once a function patch is in).
"""
from __future__ import annotations

import atexit
import json
import os
import sys
from collections import Counter, namedtuple
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
from hyperion.strategy.tables import quick_start  # noqa: E402
from hyperion.tablegen import rules_from_dict  # noqa: E402

from adapter import cards, history, make_adapter  # noqa: E402  submission/adapter.py: a sibling in the zip, imported now


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules()


RULES = load_rules()
ERRORS: Counter = Counter()  # what the wrappers swallowed, and the checks above; printed at exit under HYPERION_CHECK=1

# TODO 0  from the RULE SHEET: how many tables does one process run at the same time? Kit J's simulator: one at a time, in
#   turn, each seat its own module copy. Over 1 costs about 15 ms of import per adapter and no timed time.
TABLES_AT_ONCE = 1

# TODO 1  from the RULE SHEET: is the hand end timed? Kit J: inside the next decide, "defer". Untimed: "eager".
HAND_END = "defer"
RECAP_SKIP_MAX = 1  # recaps whose bot hand end is dropped in a row while the budget is short (the next one is delivered)


def safe_answer(v):
    """TODO 2  the kit's check-or-fold, for a table that lost its adapter or a decide that failed (kit J's strings)."""
    return "c" if v.owe <= 0 else "f"


# TODO 3  WARM-UP: one of the kit's own states per street and one hand end, in the kit's shape (its README's fields), so the
#   adapter's translation and the bot's decision path have run once before the clock starts. Kit J's, made up and
#   consistent: players clockwise from the small blind; we are dd (index 3), first to act after a fold; we raise, the big
#   blind calls and checks the flop to us, we bet and it folds; then the next hand's first decision.
_V = namedtuple("_V", "hand level bb next_level_in street hole board pot owe min_raise max_raise me button players log recap")
_P = namedtuple("_P", "tag stack peak floor bet in_pot state")
_R = namedtuple("_R", "hand bb log board shown net out dividend")
_T = namedtuple("_T", "me tags start_chips blinds hands_per_level hand_cap points")
_TAGS = ("aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh")
_WARM_TABLE = _T("dd", _TAGS, None, None, None, None, None)


def _warm_players(bets, states, inpot):
    return tuple(_P(t, 100.0 - inpot[i], 100.0, 60.0, bets[i], inpot[i], states[i]) for i, t in enumerate(_TAGS))


def warm_states() -> list:
    """Whole `v`s, each with the recaps it carries, as the kit delivers them."""
    hole = (1 << (13 * 3 + 12)) | (1 << (13 * 2 + 11))  # As Kh
    board3 = (1 << 10) | (1 << (13 + 5)) | (1 << (26 + 1))
    log1 = "aaS0.5 bbB1 ccF ddR2 eeF ffF ggF hhF aaF bbC2 / bbK"
    pre = _warm_players((0.5, 1, 0, 0, 0, 0, 0, 0), "LLFLLLLL", (0.5, 1, 0, 0, 0, 0, 0, 0))
    flop = _warm_players((0, 0, 0, 0, 0, 0, 0, 0), "FLFLFFFF", (0.5, 3, 0, 3, 0, 0, 0, 0))
    net = (("aa", -0.5), ("bb", -3.0), ("cc", 0.0), ("dd", 3.5), ("ee", 0.0), ("ff", 0.0), ("gg", 0.0), ("hh", 0.0))
    done = _R(1, 20, log1 + " ddR2 bbF", board3, (), net, (), 0.0)
    return [_V(1, 1, 20, 25, 0, hole, 0, 1.5, 1.0, 1.0, 99.0, 3, 7, pre, "aaS0.5 bbB1 ccF", ()),
            _V(1, 1, 20, 25, 1, hole, board3, 6.5, 0.0, 1.0, 97.0, 3, 7, flop, log1, ()),
            _V(2, 1, 20, 24, 0, hole, 0, 1.5, 1.0, 1.0, 99.0, 3, 0,
               _warm_players((0.5, 1, 0, 0, 0, 0, 0, 0), "LLLLLLLL", (0.5, 1, 0, 0, 0, 0, 0, 0)), "bbS0.5 ccB1", (done,))]


def table_start(ad, table) -> None:
    """TODO 4  the kit's table -> the adapter's seats, then Adapter.start (the bot's new_table). Kit J: tags in clockwise
    order, ours is `table.me`, and each table's tags are new. `start_stack` follows every seat's chips at the hand's start
    (the adapter's to_observation keeps it), for hand_end below."""
    tags = tuple(table.tags)
    ad.seat_of = {t: i for i, t in enumerate(tags)}
    ad.n = len(tags)
    ad.start_stack = {t: RULES.starting_stack for t in tags}
    ad.start(ad.seat_of[table.me], ad.n, RULES)


def hand_end(ad, r, deliver: bool = True) -> None:
    """TODO 5  one finished hand -> Adapter.hand_end (with `deliver`; without, the chip chain alone: decide's budget), with everything it carries: the hand's actions (history), every seat's
    chip change (deltas), the hands shown (showdown, {} when none), the board, and the hand number to_observation passes
    as hand_no (kit J counts from 1, ours from 0).

    TODO 5a  `won`: chips collected or net change? The README says which; read it, then one of:
      net change (kit J's `net`, in big blinds): deltas as below;
      collected (drill 11's kit I): deltas = [int(w) - int(sum(p)) for w, p in zip(h.won, h.paid)]
    Does the figure leave anything out? Kit J's leaves out what an eliminated seat forfeits: charged here, so the deltas
    sum to 0 and the bot's stacks stay right. A hand that does not sum to 0 is counted (`deltas_sum` on the error line)."""
    bb = r.bb
    seat_of = ad.seat_of
    start = ad.start_stack
    deltas = [0] * ad.n
    for tag, net in r.net:
        d = int(net * bb + (0.5 if net >= 0 else -0.5))
        if tag in r.out:
            d = -start.get(tag, -d)
        deltas[seat_of[tag]] = d
        start[tag] = start.get(tag, 0) + d
    if sum(deltas) != 0:
        ERRORS["deltas_sum"] += 1
    if not deliver:
        return
    shown = {seat_of[t]: cards(m) for t, m in r.shown}
    ad.hand_end(r.hand - 1, deltas[ad.seat], ad.n, history=history(r.log, bb, seat_of), deltas=deltas, showdown=shown,
                board=cards(r.board))


class _Slot:
    """One adapter and the table it is playing. `owner` is that table's token; `tick` when that table last spoke."""

    __slots__ = ("ad", "owner", "tick", "skipped")

    def __init__(self, ad):
        self.ad, self.owner, self.tick, self.skipped = ad, None, 0, 0


def build() -> _Slot:
    """A ship bot behind tonight's adapter, started for a table: every table it reads, and this bot's own modules, are
    loaded and built now, never inside a timed call."""
    bot = ship.make_bot()
    if HAND_END != "eager":
        bot.defer_hand_end(True)
    ad = make_adapter(bot, RULES)
    ad.hand_end_timed = HAND_END != "eager"
    ad.hand_end_stored = True  # hand_end runs inside the timed decide: it has its own mean (Adapter._note_call)
    ad.log_at_end = True  # the recap carries the hand's whole log (TODO 5): no walk of the states to keep up on the clock
    table_start(ad, _WARM_TABLE)
    return _Slot(ad)


def warm_up(ad) -> None:
    for v in warm_states():
        try:
            for r in v.recap:
                hand_end(ad, r)
            ad.decide(v)
        except Exception:  # noqa: BLE001
            ERRORS["warm_up"] += 1
    try:
        table_start(ad, _WARM_TABLE)  # the kit's first table starts clean
    except Exception:  # noqa: BLE001
        ERRORS["warm_up"] += 1
    warmed(ad)  # the conformance report forgets the made-up hand
    ERRORS.pop("deltas_sum", None)


SLOTS = [build() for _ in range(max(1, TABLES_AT_ONCE))]
for _s in SLOTS:
    warm_up(_s.ad)
pin_package(*_ROOTS)  # here, at import: a kit's loader may drop our modules and this folder right after it
_ticks = 0
_checked_rules = False


def _num(x):
    return [_num(y) for y in x] if isinstance(x, (list, tuple)) else float(x)


def _rules_differ(table) -> list[str]:
    """TODO 6  the table's rules that rules_tonight.json must match, by the kit's field names (kit J's here)."""
    out = []
    for name, want in (("points", RULES.payouts), ("blinds", RULES.blind_levels), ("start_chips", RULES.starting_stack),
                       ("hands_per_level", RULES.hands_per_level), ("hand_cap", RULES.max_hands)):
        got = getattr(table, name, None)
        try:
            if got is not None and _num(got) != _num(want):
                out.append(name)
        except Exception:  # noqa: BLE001
            out.append(name)
    return out


def _overlap() -> None:
    if not ERRORS["table_overlap"]:
        try:
            sys.stderr.write("entry: tables overlap in this process, more than TABLES_AT_ONCE: the table that lost its "
                             "adapter check-folds\n")
        except Exception:  # noqa: BLE001
            pass
    ERRORS["table_overlap"] += 1


def sit_down(table):
    global _ticks, _checked_rules
    repin_package()
    _ticks += 1
    slot = min(SLOTS, key=lambda s: s.tick)  # the adapter whose table spoke last longest ago: with one, the only one
    token = object()
    slot.owner, slot.tick = token, _ticks
    ad = slot.ad
    try:
        if not _checked_rules:
            _checked_rules = True
            for name in _rules_differ(table):
                ERRORS["rules_" + name] += 1
        with quick_start():  # nothing read or built here: what the import loaded is used
            table_start(ad, table)
    except Exception:  # noqa: BLE001
        ERRORS["table_start"] += 1

    def decide(v):
        global _ticks
        t0 = perf_counter()  # first, always: the kit's clock is running (Adapter.decide reports the whole call to the governor)
        repin_package()
        if slot.owner is not token:  # another table took this adapter: its state is not ours
            _overlap()
            return safe_answer(v)
        _ticks += 1
        slot.tick = _ticks
        try:
            for r in v.recap:
                deliver = not ad.short_of_time() or slot.skipped >= RECAP_SKIP_MAX
                slot.skipped = 0 if deliver else slot.skipped + 1
                hand_end(ad, r, deliver)
                if not deliver:
                    ad.drop_hand_end()
        except Exception:  # noqa: BLE001
            ERRORS["hand_end"] += 1
        try:
            return ad.decide(v, t0)  # Adapter.decide: a translation or bot failure is already native_safe's answer
        except Exception:  # noqa: BLE001
            ERRORS["decide"] += 1
            return safe_answer(v)

    return decide


def _report() -> None:
    try:
        sys.stderr.write("entry: swallowed errors " + (", ".join(f"{k} {v}" for k, v in sorted(ERRORS.items()) if v) or "0")
                         + "\n")
    except Exception:  # noqa: BLE001
        pass


if os.environ.get("HYPERION_CHECK") == "1":
    atexit.register(_report)
