"""Tonight's entry: sit_down(table) -> decide(v). Everything is imported, built and warmed at import (5 s); sit_down
restarts the adapter and bot for a table (25 ms); hand ends arrive as v.recap inside the timed decide."""
from __future__ import annotations

import atexit
import json
import os
import sys
from collections import Counter, namedtuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOTS = (_HERE,) if os.path.isdir(os.path.join(_HERE, "hyperion")) else (os.path.dirname(_HERE), _HERE)
for _p in _ROOTS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hyperion import ship  # noqa: E402
from hyperion.core.types import Rules  # noqa: E402
from hyperion.drills.adapter import pin_package, repin_package  # noqa: E402
from hyperion.drills.conformance import warmed  # noqa: E402
from hyperion.strategy import hero as _hero  # noqa: E402
from hyperion.strategy.tables import quick_start  # noqa: E402
from hyperion.tablegen import rules_from_dict  # noqa: E402

from adapter import make_adapter  # noqa: E402


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules()


# The kit collects between tables on its own time, automatic GC off during one (README 6). Hero's table-start freeze and
# its full collection one table in 16 (20-27 ms in the 25 ms sit_down, measured) only risk the table here.
_hero.table_freeze = lambda: None

RULES = load_rules()
ERRORS: Counter = Counter()
_V = namedtuple("_V", "hand level bb next_level_in street hole board pot owe min_raise max_raise me button players log recap")
_P = namedtuple("_P", "tag stack peak floor bet in_pot state")
_R = namedtuple("_R", "hand bb log board shown net out dividend")
_TAGS = ("aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh")


def build():
    bot = ship.make_bot()
    bot.defer_hand_end(True)
    ad = make_adapter(bot, RULES)
    ad.sit(_TAGS, "aa")
    return ad


def _warm_players(bets, states, inpot):
    return tuple(_P(t, 100.0 - inpot[i], 100.0, 60.0, bets[i], inpot[i], states[i]) for i, t in enumerate(_TAGS))


def warm_up(ad) -> None:
    """One decision per street and one recap through the real path. aa is the button's right... all made up, consistent:
    players clockwise from the small blind, aa first; we act as dd (index 3) UTG+."""
    hole = (1 << (13 * 3 + 12)) | (1 << (13 * 2 + 11))  # As Kh
    board3 = (1 << 10) | (1 << (13 + 5)) | (1 << (26 + 1))
    log0 = "aaS0.5 bbB1 ccF"
    pre = _warm_players((0.5, 1, 0, 0, 0, 0, 0, 0), "LLFLLLLL", (0.5, 1, 0, 0, 0, 0, 0, 0))
    log1 = "aaS0.5 bbB1 ccF ddR2 eeF ffF ggF hhF aaF bbC2 / bbK"
    fl = _warm_players((0, 0, 0, 0, 0, 0, 0, 0), "FLFLFFFF", (0.5, 3, 0, 3, 0, 0, 0, 0))
    try:
        v0 = _V(1, 1, 20, 25, 0, hole, 0, 1.5, 1.0, 1.0, 99.0, 3, 7, pre, log0, ())
        v1 = _V(1, 1, 20, 25, 1, hole, board3, 6.5, 0.0, 1.0, 97.0, 3, 7, fl, log1, ())
        ad.decide(v0)
        ad.decide(v1)
        net = (("aa", -0.5), ("bb", -3.0), ("cc", 0.0), ("dd", 3.5), ("ee", 0.0), ("ff", 0.0), ("gg", 0.0), ("hh", 0.0))
        ad.recap(_R(1, 20, log1 + " ddR2 bbF", board3, (), net, (), 0.0))
        v2 = _V(2, 1, 20, 24, 0, hole, 0, 1.5, 1.0, 1.0, 99.0, 3, 0,
                _warm_players((0.5, 1, 0, 0, 0, 0, 0, 0), "LLLLLLLL", (0.5, 1, 0, 0, 0, 0, 0, 0)), "bbS0.5 ccB1", ())
        ad.decide(v2)
    except Exception:  # noqa: BLE001
        ERRORS["warm_up"] += 1
    ad.sit(_TAGS, "aa")
    warmed(ad)


AD = build()
warm_up(AD)
pin_package(*_ROOTS)


def sit_down(table):
    repin_package()
    ad = AD
    try:
        with quick_start():
            ad.sit(table.tags, table.me)
    except Exception:  # noqa: BLE001
        ERRORS["table_start"] += 1

    def decide(v):
        repin_package()
        try:
            for r in v.recap:
                ad.recap(r)
        except Exception:  # noqa: BLE001
            ERRORS["recap"] += 1
        try:
            return ad.decide(v)
        except Exception:  # noqa: BLE001
            ERRORS["decide"] += 1
            return "c" if v.owe <= 0 else "f"

    return decide


def _report() -> None:
    try:
        sys.stderr.write("entry: swallowed errors " + (", ".join(f"{k} {v}" for k, v in sorted(ERRORS.items())) or "0") + "\n")
    except Exception:  # noqa: BLE001
        pass


if os.environ.get("HYPERION_CHECK") == "1":
    atexit.register(_report)
