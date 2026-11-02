"""The event player template filled in for the fake event kit (hyperion/drills/fakekits/kit_e_style): a worked
example of hyperion/drills/event_player_template.py, and the reference the tests run (tests/test_drills_events.py).

    python -m hyperion.drills.fakekits.kit_e_style.runner hyperion/drills/event_example.py

Every kit event is one EventTracker call; decide() is EventAdapter.decide; nothing raises into the kit. The kit times
its hand end (1 ms, interrupted at 1.05 ms), so the bot's hand-end work is deferred to idle() at the next hand start.
"""
from __future__ import annotations

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))  # in a package: the entry's own folder holds hyperion/
for _p in (_HERE if os.path.isdir(os.path.join(_HERE, "hyperion")) else _ROOT,):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hyperion import ship  # noqa: E402
from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_card  # noqa: E402,F401
from hyperion.drills.conformance import maybe_checked  # noqa: E402
from hyperion.drills.events import EventAdapter  # noqa: E402

RULES = Rules()  # tonight: Rules from rules_tonight.json (the template's load_rules)
HAND_END_TIMED = True  # the rule sheet: this kit times on_result like every other event


def card(c: str) -> int:
    return parse_card(c)


def cards(cs) -> list[int]:
    return [parse_card(c) for c in cs]


class KitEStyleAdapter(EventAdapter):
    """decide(request): moves {fold, check, call{cost}, raise{min, max}} (raise-to totals); reply {"move", "to"}."""

    def options(self, req):
        mv = req["moves"]
        legal = [k for k in ("fold", "check", "call", "raise") if k in mv]
        to_call = int(mv["call"]["cost"]) if "call" in mv else 0
        lo, hi = (int(mv["raise"]["min"]), int(mv["raise"]["max"])) if "raise" in mv else (0, 0)
        return legal, to_call, lo, hi

    def request_keys(self, req):
        return int(req["hand"]) - 1, int(req["board_size"])

    def from_action(self, a: Action, obs: Observation, req):
        mv = req["moves"]
        k = a.kind.value
        if k == "raise" and "raise" in mv:
            return {"move": "raise", "to": max(int(mv["raise"]["min"]), min(int(mv["raise"]["max"]), int(a.amount)))}
        if k in mv:
            return {"move": k}
        return self.native_safe(req)

    def native_safe(self, req):
        try:
            return {"move": "check"} if "check" in req["moves"] else {"move": "fold"}
        except Exception:  # noqa: BLE001
            return {"move": "fold"}


class Agent:
    def __init__(self):
        self.a = maybe_checked(KitEStyleAdapter(ship.make_bot(), RULES))
        if HAND_END_TIMED:
            self.a.defer_hand_end(True)

    def on_table(self, info):
        try:
            self.a.start(int(info["seat"]), int(info["players"]), RULES)
        except Exception:  # noqa: BLE001
            pass

    def on_hand(self, info):
        try:
            t = self.a.t
            chips = {int(s): int(c) for s, c in info["chips"].items()}
            t.hand_start(int(info["hand"]) - 1, int(info["button"]), info["blinds"], chips, cards(info["cards"]))
            for p in info["posted"]:
                t.post(int(p["seat"]), int(p["paid"]), ante=bool(p.get("ante")))
        except Exception:  # noqa: BLE001
            pass
        if HAND_END_TIMED:
            self.a.idle()  # the last hand end's deferred work, in this event's own budget

    def on_board(self, info):
        try:
            self.a.t.board(cards(info["board"]))
        except Exception:  # noqa: BLE001
            pass

    def on_action(self, info):
        try:
            self.a.t.action(int(info["seat"]), info["move"], total=int(info["to"]), paid=int(info["paid"]))
        except Exception:  # noqa: BLE001
            pass

    def on_reveal(self, info):
        try:
            self.a.t.showdown({int(s): cards(h) for s, h in info["hands"].items()})
        except Exception:  # noqa: BLE001
            pass

    def on_result(self, info):
        try:
            self.a.end_hand(net={int(s): int(v) for s, v in info["net"].items()})
        except Exception:  # noqa: BLE001
            pass

    def decide(self, req):
        return self.a.decide(req)
