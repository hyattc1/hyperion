"""River of Blood kit entry: `Player` tracks the hand from the events and asks our ship bot through the adapter.

Built for the kit's sandbox: a fresh copy of this module and a fresh Player() per table; every method under
1 ms; setup (import + Player() + take_seat) under 1 s. Every method is wrapped: nothing raises into the kit.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if os.path.isdir(os.path.join(_HERE, "hyperion")):
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)
else:  # run from the repo's submission/ folder: hyperion lives one level up
    _UP = os.path.dirname(_HERE)
    if _UP not in sys.path:
        sys.path.insert(0, _UP)
    if _HERE not in sys.path:
        sys.path.insert(0, _HERE)

import hyperion.ship  # noqa: E402
from hyperion.core.eval import warm  # noqa: E402
from hyperion.core.types import Rules  # noqa: E402

try:
    from . import adapter as _adapter  # loaded as a package by the kit
except Exception:  # noqa: BLE001
    import adapter as _adapter  # noqa: E402


def _load_rules() -> Rules:
    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            raw = json.load(f)
        for k in ("board_sizes", "rank_order", "payouts", "blind_levels", "ante_per_level"):
            if k in raw:
                raw[k] = tuple(tuple(x) if isinstance(x, list) else x for x in raw[k])
        return Rules(**raw)
    except Exception:  # noqa: BLE001
        return Rules()


RULES = _load_rules()
# Setup budget: import + Player() + take_seat <= 1 s per table. Hero.new_table calls warm(8) (0.62 s: the 8-card
# table for three-card variants). Tonight the bot never sees more than 7 cards (run streets go through the
# adapter's river_view, a 5-card sub-board; hand ends pass board[:5]), so cap the warm-up at 7 cards (0.14 s).
warm(7)
try:
    import hyperion.strategy.hero as _hero_mod

    _hero_mod.warm = lambda max_cards=7: warm(min(int(max_cards), 7))
except Exception:  # noqa: BLE001
    pass


class Player:
    def __init__(self):
        self.seat = 0
        self.n = 8
        self.hand = 1
        self.sb, self.bb, self.button = 10, 20, 0
        self.hole, self.board, self.street = [], [], 0
        self.stacks, self.bets, self.in_hand = {}, {}, set()
        self.pot = 0
        self.log = []
        self.shown = {}
        self.adapter = None
        try:
            self.adapter = _adapter.make_adapter(hyperion.ship.make_bot(), RULES)
        except Exception:  # noqa: BLE001
            self.adapter = None

    # ------------------------------------------------------------------ events
    def take_seat(self, table):
        try:
            self.seat = int(table["seat"])
            seats = list(table.get("seats") or range(8))
            self.n = max(seats) + 1
            if self.adapter is not None:
                self.adapter.start(self.seat, self.n, RULES)
        except Exception:  # noqa: BLE001
            pass

    def start_hand(self, hand):
        try:
            self.hand = int(hand["hand"])
            self.seat = int(hand.get("seat", self.seat))
            self.sb, self.bb, self.button = int(hand["sb"]), int(hand["bb"]), int(hand["button"])
            self.hole = list(hand["hole"])
            self.board = []
            self.street = 0
            self.stacks = {int(s): int(v) for s, v in hand["stacks"].items()}
            self.in_hand = set(int(s) for s in hand["order"])
            self.bets = {s: 0 for s in self.in_hand}
            self.pot = 0
            self.log = []
            self.shown = {}
            for p in hand["posts"]:
                s = int(p["seat"])
                self.stacks[s] = self.stacks.get(s, 0) - int(p["paid"])
                self.pot += int(p["paid"])
                if p["kind"] != "ante":
                    self.bets[s] = self.bets.get(s, 0) + int(p["paid"])
        except Exception:  # noqa: BLE001
            pass

    def see_cards(self, cards):
        try:
            self.bets = {s: 0 for s in self.bets}  # first: an interrupt then leaves the board stale, which choose detects
            self.street = int(cards["street"])
            self.board = list(cards["board"])
        except Exception:  # noqa: BLE001
            pass

    def see_action(self, action):
        try:
            s = int(action["seat"])
            self.stacks[s] = self.stacks.get(s, 0) - int(action["paid"])
            self.pot += int(action["paid"])
            self.bets[s] = int(action["amount"])
            mv = action["move"]
            if mv == "fold":
                self.in_hand.discard(s)
            self.log.append((s, int(action["street"]), mv, int(action["amount"])))
        except Exception:  # noqa: BLE001
            pass

    def see_showdown(self, showdown):
        try:
            self.shown = {int(h["seat"]): list(h["hole"]) for h in showdown["hands"]}
        except Exception:  # noqa: BLE001
            self.shown = {}

    def end_hand(self, result):
        try:
            if self.adapter is None:
                return
            net = {int(s): int(v) for s, v in result.get("net", {}).items()}
            deltas = [net.get(s, 0) for s in range(self.n)]
            card = _adapter.card
            showdown = {s: tuple(card(c) for c in h) for s, h in self.shown.items()}
            board = [card(c) for c in (result.get("board") or self.board)][:5]
            last = self.street
            hist = _adapter.history(_adapter.bot_log(self.log, last))
            self.adapter.hand_end(self.hand - 1, net.get(self.seat, 0), self.n, history=hist, deltas=deltas,
                                  showdown=showdown, board=board)
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ decision
    def choose(self, request):
        opts = {}
        try:
            opts = {o["move"]: o for o in request["options"]}
            if self.adapter is None:
                raise RuntimeError("no adapter")
            street = int(request.get("street", self.street))
            # A missed event (an interrupted callback on a loaded host) leaves stale cards: never play them.
            if int(request.get("hand", self.hand)) != self.hand or len(self.hole) != 2 or street != len(self.board):
                raise RuntimeError("lost track of this hand")
            in_hand = self.in_hand if self.seat in self.in_hand else self.in_hand | {self.seat}
            native = {
                "n": self.n, "seat": self.seat, "button": self.button, "hand": self.hand,
                "sb": self.sb, "bb": self.bb, "street": street,
                "board": self.board, "hole": self.hole, "stacks": self.stacks, "bets": self.bets,
                "in_hand": in_hand, "pot": self.pot, "log": self.log, "options": opts,
            }
            return self.adapter.decide(native)
        except Exception:  # noqa: BLE001
            return {"move": "check"} if "check" in opts else {"move": "fold"}
