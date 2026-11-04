"""Tonight's entry: Tranche Hold'em kit, module-level start/table/act/done (bot.py at the zip root).

Everything is imported, built, started and warmed at import; the package is pinned there because the kit's loader drops
this folder from sys.path and our modules from sys.modules right after the import. Every call starts with
repin_package(). done() is timed (1 ms): HAND_END "defer".
"""
from __future__ import annotations

import atexit
import json
import os
import sys
from collections import Counter
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
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

from adapter import history, make_adapter  # noqa: E402


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules()


RULES = load_rules()
SEATS = 8
ERRORS: Counter = Counter()
HAND_END = "defer"


def build():
    bot = ship.make_bot()
    if HAND_END != "eager":
        bot.defer_hand_end(True)
    ad = make_adapter(bot, RULES)
    ad.start(0, SEATS, RULES)
    return ad


def _state(hole, board, street, log, to_call, min_raise, paid, button=3, hand=1):
    stacks = tuple(2000 - sum(p) for p in paid)
    tr = tuple(sum(p[k] for p in paid) for k in range(4))
    return SimpleNamespace(hole=hole, board=board, street=street, to_call=to_call, min_raise=min_raise,
                           stack=stacks[0], stacks=stacks, seats="pppppppp", paid=paid, tranches=tr,
                           button=button, sb=10, bb=20, hand=hand, level=1, log=log)


def warm_states() -> list:
    z = (0, 0, 0, 0)
    pre = tuple([z] + [(10, 0, 0, 0) if s == 4 else (20, 0, 0, 0) if s == 5 else z for s in range(1, 8)])
    s0 = _state((48, 45), (), 0, "4s10 5b20 6f 7f", 20, 40, pre)
    fl = tuple([(40, 0, 0, 0), z, z, z, z, (40, 0, 0, 0), z, z])
    s1 = _state((48, 45), (12, 30, 7), 1, "4s10 5b20 6f 7f 0r40 1f 2f 3f 4f 5c20/5k", 0, 20, fl)
    return [s0, s1]


def warm_results() -> list:
    shown = [None] * 8
    shown[0] = (48, 45)
    return [SimpleNamespace(hand=1, board=(12, 30, 7), shown=tuple(shown),
                            paid=tuple([(40, 0, 0, 0)] + [(0, 0, 0, 0)] * 4 + [(40, 0, 0, 0)] + [(0, 0, 0, 0)] * 2),
                            awards=((80, 0, 0, 0, 0, 0, 0, 0), (0,) * 8, (0,) * 8, (0,) * 8),
                            won=(80, 0, 0, 0, 0, 0, 0, 0), stacks=(2040, 2000, 2000, 2000, 2000, 1960, 2000, 2000),
                            log="4s10 5b20 6f 7f 0r40 1f 2f 3f 4f 5c20/5k 0r20 5f")]


def hand_end(ad, r) -> None:
    """done(h) -> Adapter.hand_end: won is chips collected, so the delta is won - paid."""
    won = [int(x) for x in r.won]
    cost = [int(sum(p)) for p in r.paid]
    deltas = [w - c for w, c in zip(won, cost)]
    log = str(r.log or "")
    shown_all = {i: tuple(x) for i, x in enumerate(r.shown or ()) if x}
    others = {i: c for i, c in shown_all.items() if i != 0}
    if others:
        showdown = dict(others)
        folded_me = any(t.rstrip("!").startswith("0f") for t in log.replace("/", " ").split())
        if not folded_me and 0 in shown_all:
            showdown[0] = shown_all[0]
    else:
        showdown = {}
    ad.hand_end(int(r.hand), deltas[0], SEATS, history=history(log), deltas=deltas, showdown=showdown,
                board=tuple(r.board))


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
        ad.start(0, SEATS, RULES)
    except Exception:  # noqa: BLE001
        ERRORS["warm_up"] += 1
    warmed(ad)


AD = build()
warm_up(AD)
pin_package(*_ROOTS)


def start(session) -> None:
    repin_package()


def table(info) -> None:
    repin_package()
    try:
        with quick_start():
            AD.start(0, SEATS, RULES)
    except Exception:  # noqa: BLE001
        ERRORS["table_start"] += 1


def act(v):
    repin_package()
    try:
        out = AD.decide(v)
        if type(out) is int:
            return out
        ERRORS["bad_answer"] += 1
    except Exception:  # noqa: BLE001
        ERRORS["decide"] += 1
    return 0


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
