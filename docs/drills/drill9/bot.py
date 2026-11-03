"""Chain Hold'em entry: class Agent around hyperion.ship.make_bot() behind one adapter. Everything imported and
warmed at module import (the kit's loader unloads our modules and drops our folder from sys.path afterwards)."""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
sys.path.append(_HERE)  # a second entry survives the loader's sys.path.remove, for lazy imports

from hyperion.core.types import Rules  # noqa: E402
from hyperion.drills.adapter import pin_package, repin_package  # noqa: E402
from hyperion.tablegen import rules_from_dict  # noqa: E402
import hyperion.ship  # noqa: E402
from adapter import make_adapter, history  # noqa: E402


def _load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            return rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        return Rules(hole_cards=3)


RULES = _load_rules()


class _FakeState:
    """A kit-shaped state for warming every lazy import and cache at module import."""

    def __init__(self, street=0, hand=1):
        self.hand, self.street = hand, street
        self.card, self.left, self.right = 51, 47, 2
        self.left_nb, self.right_nb = 1, 7
        self.board = (0, 9, 22, 33, 44)[: (0, 3, 4, 5)[street]]
        self.stacks = (2000, 2000, 2000, 2000, 2000, 1990, 1980, 2000) if street == 0 else (1960,) * 8
        self.bets = (0, 0, 0, 0, 0, 10, 20, 0) if street == 0 else (0,) * 8
        self.in_pot = self.bets if street == 0 else (40,) * 8
        self.pot = 30 if street == 0 else 320
        self.to_call = 20 if street == 0 else 0
        self.min_raise_by = 20
        self.can_raise = True
        self.status = "AAAAAAAA"
        self.button = 4
        self.sb, self.bb, self.level, self.hands_left = 10, 20, 1, 200 - hand
        self.log = "5s10,6b20,7f" if street == 0 else "5s10,6b20,7c20,0c20,1c20,2c20,3c20,4c20,5c10,6k" + "/" * street

    def cost(self, token):
        pot_after = self.pot + self.to_call
        pct = {"R33": 33, "R50": 50, "R75": 75, "R100": 100, "R150": 150, "R250": 250}.get(token)
        if token == "F" or token == "C":
            return self.to_call if token == "C" else 0
        if token == "A":
            return self.stacks[0]
        inc = max(pot_after * pct // 100, self.min_raise_by)
        return min(self.to_call + inc, self.stacks[0])


class _FakeResult:
    def __init__(self):
        self.hand, self.board, self.log = 1, (0, 9, 22, 33, 44), "5s10,6b20,7f,0c20,1f,2f,3f,4f,5f,6k/6k,0k/6k,0k/6k,0k"
        self.shown = ((51, 47, 2), None, None, None, None, None, (40, 41, 2), None)
        self.won = (10, 0, 0, 0, 0, -10, 0, 0)
        self.stacks = (2010, 2000, 2000, 2000, 2000, 1990, 2000, 2000)
        self.place, self.points, self.table_over = 0, None, False


def _build():
    bot = hyperion.ship.make_bot()
    ad = make_adapter(bot, RULES)
    return ad


def _hand_end(ad, r) -> None:
    shown = getattr(r, "shown", None) or ()
    showdown = {i: tuple(x) for i, x in enumerate(shown) if x}
    ad.hand_end(int(r.hand), int(r.won[0]), 8, history=history(r.log), deltas=[int(x) for x in r.won],
                showdown=showdown, board=tuple(r.board))


def _warm(ad) -> None:
    try:
        ad.start(0, 8, RULES)
        for st in (0, 1, 2, 3):
            ad.decide(_FakeState(st))
        _hand_end(ad, _FakeResult())
        ad.start(0, 8, RULES)
    except Exception:  # noqa: BLE001
        pass


_warm(_build())
pin_package()


class Agent:
    def __init__(self):
        repin_package()
        self.ad = _build()
        _warm(self.ad)
        pin_package()

    def begin_table(self, info):
        repin_package()
        try:
            self.ad.start(0, 8, RULES)
        except Exception:  # noqa: BLE001
            pass

    def decide(self, s) -> str:
        try:
            out = self.ad.decide(s)
            if out in ("F", "C", "A", "R33", "R50", "R75", "R100", "R150", "R250"):
                return out
        except Exception:  # noqa: BLE001
            pass
        try:
            return "C" if s.to_call == 0 else "F"
        except Exception:  # noqa: BLE001
            return "F"

    def hand_over(self, r):
        try:
            repin_package()
            _hand_end(self.ad, r)
        except Exception:  # noqa: BLE001
            pass
