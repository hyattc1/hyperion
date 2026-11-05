"""Tonight's entry for a kit whose bot is plain MODULE-LEVEL FUNCTIONS, one module for a whole session (drill 11's kit
I: `start(session)` once, 3 s; `table(info)` every table, 50 ms; `act(v)` every decision, 1 ms, returning one int, the
chips to put in now; `done(h)` every hand, 1 ms). Copy it to `submission/<the kit's entry file>` (kit I: bot.py) beside
`submission/adapter.py` (from adapter_template.py) and fill the TODOs in order. Kit I's shape is the worked default:
seats relative to us (0 = me), no legal list (to_call and min_raise only), cards rank * 4 + suit, a log string, and a
hand end whose `won` is chips collected. A kit that builds a bot object (class Agent): entry_template.py; the bot as its
own process: process_entry_template.py; one call per event: event_player_template.py.

What it does without being asked, each from drill 11:
- NOTHING IMPORTS AFTER IMPORT TIME. Kit I's loader puts the bot folder on sys.path for the import only, then takes it
  off and drops every module from that folder out of sys.modules: an import inside start/table/act/done then fails, or
  loads the module again inside a timed call. So everything is imported, built, started for a table and warmed here,
  at import, and the package is pinned (`pin_package`); every function starts with `repin_package()`, which puts our
  modules and the folder back. submission/adapter.py too: every import at its top, none inside a function.
- One module plays the session (a few hundred tables, module globals kept): table() restarts the adapter and the bot
  for each table (Adapter.start -> bot.new_table), so nothing of the last table's carries into the next.
- THE KIT'S OVERTIME. At each limit a timer raises `Overtime`, a BaseException, inside our code. Nothing here catches
  it: every wrapper is `except Exception`, never a bare `except:` or `except BaseException:` (that would swallow it and
  run on past the limit, and a late return counts as a timeout anyway). Our state stays consistent wherever it lands:
  done() builds the whole translation first and hands it to the bot in one call (the bot's hand end interrupted at any
  line breaks nothing: tests/test_hand_end_interrupt.py), table() runs inside the adapter's start (a cut one sits the
  table out on the kit and the next table() starts clean), and an act() cut at any line leaves the next decision
  clean (tests/test_h7_drill11.py). Keep anything you add that must not be half done short, and after the work.
- The governor sees what the kit times (G1): act() passes its first clock read to Adapter.decide, which reports the whole call to
  the bot's SafeBot; tools/gate.py fails a package whose decisions do not report.
- done() is timed (kit I: 1 ms, an overrun only counted): HAND_END "defer" makes the bot's hand end deferrable
  (`defer_hand_end(True)`: the light part here, the ICM curve and the dials in the next decision's Hero).
- act() always returns one int: the adapter's answer when it is one, else the kit's check-or-fold (0).
- start() checks the session's points, blinds and stack against rules_tonight.json; a difference is counted on the
  error line (a rule sheet that missed the points table plays every all-in at the wrong prices).
- The deltas of every hand end must sum to 0 (no rake): a hand end that does not is counted (`deltas_sum`), which is
  what a `won` read the wrong way round (TODO 3) looks like.
- The warm-up's made-up decisions never reach the HYPERION_CHECK=1 conformance report (`warmed`).

Checks, in order: the kit's simulator with HYPERION_CHECK=1 (0 violations, 0 exceptions; this file's own error line at
exit reads 0); tools/pack.py (`--import-budget` the kit's start budget, both size caps); tools/gate.py with
submission/gate_seat.py from module_gate_seat_template.py (`--kit submission/gate_seat.py --entry bot.py`), which loads
this file as the kit's loader does (the folder off sys.path and our modules out of sys.modules after the import) and
raises the kit's Overtime inside it at the limits.
"""
from __future__ import annotations

import atexit
import json
import os
import sys
from collections import Counter
from time import perf_counter
from types import SimpleNamespace

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

from adapter import history, make_adapter  # noqa: E402  submission/adapter.py: a sibling in the zip, imported now


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules()


RULES = load_rules()
SEATS = RULES.n_players
ERRORS: Counter = Counter()  # what the wrappers swallowed, and the checks above; printed at exit under HYPERION_CHECK=1

# TODO 0  from the RULE SHEET: is the hand-end function timed? Kit I: done() 1 ms, an overrun counted, play unchanged:
#   "defer". Untimed: "eager" (the whole hand end runs in done(), outside every clock).
HAND_END = "defer"

# TODO 1  the kit's answer: kit I takes one int, the chips to put in now (n < to_call folds or checks, to_call <= n <
#   min_raise calls, n >= min_raise > 0 raises; a bool, None or a string is an error there). SAFE is its check-or-fold.
SAFE = 0


def answer_ok(out) -> bool:
    return type(out) is int  # not isinstance: True is an int to Python, an error to kit I


def build():
    """A ship bot behind tonight's adapter, started for a table: every table it reads, and this bot's own modules, are
    loaded and built now (a table start costs 5-70 ms cold), never inside a timed call."""
    bot = ship.make_bot()
    if HAND_END != "eager":
        bot.defer_hand_end(True)
    ad = make_adapter(bot, RULES)
    ad.hand_end_timed = HAND_END != "eager"
    ad.start(0, SEATS, RULES)
    return ad


# TODO 2  WARM-UP: one of the kit's own states per street and one hand end, in the kit's shape (its README's fields), so
#   the adapter's translation and the bot's decision path have run once before the clock starts. Kit I's, made up and
#   consistent (8 seats, we are 0, the button 3, blinds 10/20): preflop facing the big blind after two folds; the flop
#   after our raise to 40 and the big blind's call, checked to us; the hand end after our flop bet of 40 that nobody
#   called (`u`: kit I gives the uncalled chips back at the end of the street).
def _v(hole, board, street, log, to_call, min_raise, paid, seats, button=3, hand=1):
    stacks = tuple(2000 - sum(p) for p in paid)
    return SimpleNamespace(hole=hole, board=board, street=street, to_call=to_call, min_raise=min_raise,
                           stack=stacks[0], stacks=stacks, seats=seats, paid=paid,
                           tranches=tuple(sum(p[k] for p in paid) for k in range(4)), button=button, sb=10, bb=20,
                           hand=hand, level=1, log=log)


def warm_states() -> list:
    z = (0, 0, 0, 0)
    pre = (z, z, z, z, (10, 0, 0, 0), (20, 0, 0, 0), z, z)
    fl = ((40, 0, 0, 0), z, z, z, (10, 0, 0, 0), (40, 0, 0, 0), z, z)
    return [_v((48, 45), (), 0, "4s10 5b20 6f 7f", 20, 40, pre, "ppppppff"),
            _v((48, 45), (12, 30, 7), 1, "4s10 5b20 6f 7f 0r40 1f 2f 3f 4f 5c20/5k", 0, 20, fl, "pffffpff")]


def warm_results() -> list:
    z = (0, 0, 0, 0)
    paid = ((40, 0, 0, 0), z, z, z, (10, 0, 0, 0), (40, 0, 0, 0), z, z)
    return [SimpleNamespace(hand=1, board=(12, 30, 7), shown=((48, 45),) + (None,) * 7, paid=paid,
                            awards=((90, 0, 0, 0, 0, 0, 0, 0),) + ((0,) * 8,) * 3, won=(90, 0, 0, 0, 0, 0, 0, 0),
                            stacks=(2050, 2000, 2000, 2000, 1990, 1960, 2000, 2000),
                            log="4s10 5b20 6f 7f 0r40 1f 2f 3f 4f 5c20/5k 0r40 5f 0u40")]


def hand_end(ad, h) -> None:
    """TODO 3  the kit's hand end -> Adapter.hand_end, with everything it carries (adapter_template TODO 8): the hand's
    actions (history), every seat's chip change (deltas), the hands shown (showdown, {} when none), the board, and the
    hand number the adapter's to_observation passes as hand_no (kit I: `hand` as it is, both places).

    TODO 3a  `won`: chips collected or net change? The README says which; read it, then one of:
      collected (kit I: "chips each seat collected in total (sum(paid[s]) was its cost)"):
          deltas = [int(w) - int(sum(p)) for w, p in zip(h.won, h.paid)]
      net change (drill 9's kit G: each seat's chip change for the hand):
          deltas = [int(w) for w in h.won]
    The wrong one feeds the bot wrong stacks for the rest of the table and nothing raises (drill 11 found
    entry_template.py copying kit G's line onto kit I's collected chips). The deltas sum to 0 when it is right (no
    rake): the check below counts a hand that does not (`deltas_sum` on the error line)."""
    deltas = [int(w) - int(sum(p)) for w, p in zip(h.won, h.paid)]  # collected (kit I)
    if sum(deltas) != 0:
        ERRORS["deltas_sum"] += 1
    log = str(h.log or "")
    # TODO 3b  the hands shown: kit I always shows ours and the others' only at a showdown; ours is a showdown hand
    #   only when another one was shown and we did not fold
    shown = {s: tuple(int(c) for c in x) for s, x in enumerate(h.shown or ()) if x}
    others = {s: c for s, c in shown.items() if s != 0}
    showdown = {}
    if others:
        showdown = dict(others)
        if 0 in shown and not any(t.rstrip("!").startswith("0f") for t in log.replace("/", " ").split()):
            showdown[0] = shown[0]
    ad.hand_end(int(h.hand), deltas[0], SEATS, history=history(log), deltas=deltas, showdown=showdown,
                board=tuple(int(c) for c in h.board))


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
    ERRORS.pop("deltas_sum", None)


AD = build()
warm_up(AD)
pin_package(*_ROOTS)  # here, at import: kit I's loader drops our modules and this folder right after it


def _num(x):
    return [_num(y) for y in x] if isinstance(x, (list, tuple)) else float(x)


def _rules_differ(info) -> list[str]:
    """TODO 4  the session's rules that rules_tonight.json must match, by the kit's field names (kit I's here)."""
    out = []
    for name, want in (("points", RULES.payouts), ("blinds", RULES.blind_levels),
                       ("starting_stack", RULES.starting_stack), ("hands_per_level", RULES.hands_per_level),
                       ("max_hands", RULES.max_hands)):
        got = getattr(info, name, None)
        try:
            if got is not None and _num(got) != _num(want):
                out.append(name)
        except Exception:  # noqa: BLE001
            out.append(name)
    return out


def start(session) -> None:
    """Once per session (kit I: 3 s), before any table: everything is already loaded; check the rules."""
    repin_package()
    try:
        for name in _rules_differ(session):
            ERRORS["rules_" + name] += 1
    except Exception:  # noqa: BLE001
        ERRORS["start"] += 1


def table(info) -> None:
    """TODO 5  every table (kit I: 50 ms): our seat and the seat count (kit I: we are 0, seats relative to us)."""
    repin_package()
    try:
        with quick_start():  # nothing read or built here: what the import loaded is used
            AD.start(0, int(getattr(info, "seats", SEATS) or SEATS), RULES)
    except Exception:  # noqa: BLE001
        ERRORS["table_start"] += 1


def act(v):
    t0 = perf_counter()  # first, always: the kit's clock is running (Adapter.decide reports the whole call to the governor)
    repin_package()
    try:
        out = AD.decide(v, t0)  # Adapter.decide: a translation or bot failure is already the kit's check-or-fold
        if answer_ok(out):
            return out
        ERRORS["bad_answer"] += 1
    except Exception:  # noqa: BLE001
        ERRORS["decide"] += 1
    return SAFE


def done(h) -> None:
    repin_package()
    try:
        hand_end(AD, h)
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
