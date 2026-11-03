"""Tonight's entry for an EVENT-DRIVEN kit (no state snapshot): copy to `submission/player.py` (the kit's file name)
and fill the TODOs in order. For a kit that sends a state at each decision, use adapter_template.py instead.

The kit calls the bot once per event (table start, hand start, cards, every action, showdown, hand end) and asks for
a move with only the legal options. `hyperion.drills.events.EventTracker` keeps the hand (pot with antes, stacks,
this street's bets, who is in, the action log) and `EventAdapter` decides from it with the ship bot. Your part: one
tracker call per kit event, the card format, and the request / reply format. A worked example for the fake event
kit: hyperion/drills/event_example.py (run it: `python -m hyperion.drills.fakekits.kit_e_style.runner <file>`).

Checks, in order: the kit's simulator with `HYPERION_CHECK=1` (0 violations, 0 exceptions, 0 illegal); the gate with
hyperion/drills/gate_seat_template.py copied to submission/gate_seat.py; tools/pack.py --max-mb <the kit's cap>.

The bot is built and started at module import and the package pinned there (`pin_package`): a kit loader may unload
our modules before it builds the player (drill 9's kit G) or after (drill 8's kit F), and every method that runs bot
code starts with `repin_package()` (hyperion/drills/entry_template.py has the same for a state kit).
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
# inside the package tools/pack.py builds, hyperion/ sits beside this file; run from the repo's submission/, one up
_ROOTS = (_HERE,) if os.path.isdir(os.path.join(_HERE, "hyperion")) else (os.path.dirname(_HERE), _HERE)
for _p in _ROOTS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from hyperion import ship  # noqa: E402
from hyperion.core.types import Action, Observation, Rules, parse_card  # noqa: E402,F401
from hyperion.drills.adapter import pin_package, repin_package  # noqa: E402
from hyperion.drills.conformance import maybe_checked  # noqa: E402
from hyperion.drills.events import EventAdapter  # noqa: E402


def load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            raw = json.load(f)
        for k in ("board_sizes", "rank_order", "payouts", "blind_levels", "ante_per_level"):
            if k in raw:
                raw[k] = tuple(tuple(x) if isinstance(x, list) else x for x in raw[k])
        return Rules(**raw)
    except Exception:  # noqa: BLE001
        return Rules()


RULES = load_rules()
# TODO 0  from the RULE SHEET: does the kit time its hand-end callback (and every event)? Then the bot's hand-end
#   work (ICM curve, dials: 50-300 us) is deferred and done in idle() at the next hand start, in that event's budget.
HAND_END_TIMED = True


# TODO 1  CARDS -> ints, rank * 4 + suit (parse_card("Th") == 34; it also reads "10h", "th", "T\u2665", "hT", (rank,
#   suit) pairs and {"rank", "suit"} dicts). Trap left: ints, whose order is the kit's.
def card(c) -> int:
    return parse_card(c)


def cards(cs) -> list[int]:
    return [card(c) for c in cs]


class TonightAdapter(EventAdapter):
    """Kit <name>: <the request and the reply, one line each, from the rule sheet>."""

    def options(self, req):
        # TODO 2  the request's legal moves -> (our names fold/check/call/raise, to_call or None, min raise-TO,
        #   max raise-TO). A kit giving raise-BY increments: add the current top bet (max(self.t.bets)).
        raise NotImplementedError("TODO 2")

    def request_keys(self, req):
        # TODO 3  (our 0-based hand number, board length) if the request carries them, else (None, None): a mismatch
        #   with the tracker is a missed event and the move is check/fold, never stale cards.
        return None, None

    def from_action(self, a: Action, obs: Observation, req):
        # TODO 4  a.kind.value in fold/check/call/raise, a.amount the raise-TO total -> the kit's reply (an int!)
        raise NotImplementedError("TODO 4")

    def native_safe(self, req):
        # TODO 5  the kit's check if offered, else its fold; never raises, even on garbage
        raise NotImplementedError("TODO 5")


def build() -> TonightAdapter:
    """The ship bot behind the adapter, started for a table: its tables and modules load now, at import."""
    a = maybe_checked(TonightAdapter(ship.make_bot(), RULES))
    if HAND_END_TIMED:
        a.defer_hand_end(True)
    a.start(0, RULES.n_players, RULES)
    return a


_SPARE = [build()]  # the first Player takes this one
pin_package(*_ROOTS)  # here, at import: a loader may unload our modules before it builds the Player


class Player:  # TODO 6  the kit's class name and method names; every method wrapped: nothing raises into the kit
    def __init__(self):
        repin_package()
        self.a = _SPARE.pop() if _SPARE else build()

    def table_start(self, info):  # table start: our seat and the seat count
        repin_package()
        try:
            self.a.start(int(info["seat"]), int(info["players"]), RULES)
        except Exception:  # noqa: BLE001
            pass

    def start_hand(self, info):
        repin_package()
        # TODO 7  hand number in ours (a kit counting from 1: minus 1), button, (sb, bb), every seat's chips BEFORE
        #   the posts ({seat: chips}), our cards; then one post() per ante (ante=True: dead money) and blind. A kit that
        #   gives the chips after posting: pass chips + posts back, or the pot misses the blinds.
        try:
            t = self.a.t
            t.hand_start(int(info["hand"]) - 1, int(info["button"]), info["blinds"],
                         {int(s): int(c) for s, c in info["chips"].items()}, cards(info["cards"]))
            for p in info["posted"]:
                t.post(int(p["seat"]), int(p["paid"]), ante=bool(p.get("ante")))
        except Exception:  # noqa: BLE001
            pass
        if HAND_END_TIMED:
            self.a.idle()

    def board(self, info):  # TODO 8  the WHOLE board so far (a kit sending only the new cards: append them)
        try:
            self.a.t.board(cards(info["board"]))
        except Exception:  # noqa: BLE001
            pass

    def action(self, info):
        # TODO 9  every action, ours included: seat, our kind name, total = street total after it (raise-to),
        #   paid = chips that left the stack; pass what the kit gives (None for the other)
        try:
            self.a.t.action(int(info["seat"]), info["move"], total=int(info["to"]), paid=int(info["paid"]))
        except Exception:  # noqa: BLE001
            pass

    def showdown(self, info):  # TODO 10  {seat: their hole cards}; a kit that never shows: shows_hands = False
        try:
            self.a.t.showdown({int(s): cards(h) for s, h in info["hands"].items()})
        except Exception:  # noqa: BLE001
            pass

    def hand_end(self, info):
        # TODO 11 what the hand end carries: net={seat: chip change} or chips_after={seat: chips}; none: end_hand()
        try:
            self.a.end_hand(net={int(s): int(v) for s, v in info["net"].items()})
        except Exception:  # noqa: BLE001
            pass

    def decide(self, req):
        return self.a.decide(req)
