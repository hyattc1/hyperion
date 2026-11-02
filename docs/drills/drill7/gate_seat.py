"""Gate seat for tonight's River of Blood kit (event-driven `Player` in player.py, no state snapshot).

Modelled on tools/gate_host.KitA. The gate sends the fake kits' dealer dict at every decision (a full snapshot:
ints for cards, street index 0..3, pot of previous streets, history [[seat, kind, total]]). The kit itself
only sends events; the kit's own simulator already exercises player.py's event bookkeeping (0 exc / 0 illegal).
So `native` writes the snapshot into the Player's tracked fields exactly as its event methods would leave them
(kit-style: street = board length, pot = every chip in the hand incl. this street, stacks behind, this street's
bets, in-hand seats, the log) and returns the kit's `choose` request. `parse` reads the kit reply dict.
The gate's hand end carries only our delta; `end` runs the bot's hand end there (not deferred into the next
timed choose), as the kit's end_hand does. Only `call` is timed.
"""
from __future__ import annotations

_R = "23456789TJQKA"
_S = "cdhs"


def _cs(c: int) -> str:
    return _R[c >> 2] + _S[c & 3]


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit, self.p = module, kit, None
        self.n = 8

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n = n
        self.p = self.mod.Player()
        self.p.take_seat({"seat": seat, "seats": list(range(n)), "starting_stack": stack, "hand_cap": 200,
                          "budget_ms": 1.0, "setup_ms": 1000.0, "blinds": [], "payouts": [], "variant": {}})

    def native(self, st: dict):
        p = self.p
        n = len(st["stacks"])
        bets = {s: int(st["bets"][s]) for s in range(n)}
        p.n = n
        p.seat = int(st["seat"])
        p.button = int(st["button"])
        p.hand = int(st["hand_no"]) + 1
        p.sb, p.bb = int(st["blinds"][0]), int(st["blinds"][1])
        p.hole = [_cs(c) for c in st["hole"]]
        p.board = [_cs(c) for c in st["board"]]
        p.street = len(p.board)
        p.stacks = {s: int(st["stacks"][s]) for s in range(n)}
        p.bets = bets
        p.in_hand = {s for s in range(n) if st["in_hand"][s]}
        p.pot = int(st["pot"]) + sum(bets.values())
        p.log = [(int(h[0]), p.street, str(h[1]), int(h[2])) for h in st.get("history", ())]
        me = p.seat
        to_call = int(st["to_call"])
        legal = st["legal"]
        opts = []
        if "fold" in legal:
            opts.append({"move": "fold"})
        if "check" in legal:
            opts.append({"move": "check"})
        if "call" in legal:
            opts.append({"move": "call", "amount": bets[me] + to_call, "cost": to_call})
        if "raise" in legal:
            opts.append({"move": "raise", "min": int(st["min_raise"]), "max": int(st["max_raise"])})
        a = p.adapter
        if a is not None and getattr(a, "_pending", None) is not None:
            snap = {"n": n, "seat": me, "button": p.button, "hand": p.hand, "sb": p.sb, "bb": p.bb,
                    "street": p.street, "board": p.board, "hole": p.hole, "stacks": p.stacks, "bets": p.bets,
                    "in_hand": p.in_hand, "pot": p.pot, "log": p.log, "options": {o["move"]: o for o in opts}}
            try:
                a._deliver(a.to_observation(snap))
            except Exception:  # noqa: BLE001
                a._pending = None
        return {"hand": p.hand, "street": p.street, "budget_ms": 1.0, "options": opts}

    def call(self, native):
        return self.p.choose(native)

    def parse(self, reply, st: dict):
        mv = reply["move"]
        if mv == "raise":
            amt = reply["amount"]
            if type(amt) is not int:
                raise ValueError("raise amount not an int")
            return "raise", amt
        if mv == "call":
            return "call", int(st["bets"][st["seat"]]) + int(st["to_call"])
        if mv in ("check", "fold"):
            return mv, 0
        raise ValueError(f"unknown move {mv!r}")

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        # The kit's end_hand carries every seat's net, the stacks and the showdown, so in the kit the bot's hand end
        # runs inside end_hand (its own event budget), never inside choose. The gate gives only our delta, so the
        # adapter holds the hand end for the next state (defer_hand_end); `native` delivers it there, untimed, before
        # the timed choose. Minute-15 gate with the default (delivered inside the timed choose): p50 282 us, 2.12%
        # timeouts; minute-18 try with defer off (no other seats' deltas): the bot's stacks went wrong, killed.
        a = self.p.adapter
        if a is not None:
            a.hand_end(hand_no, delta, self.n)
