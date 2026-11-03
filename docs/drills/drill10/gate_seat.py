"""Gate seat for the Solo Hold'em kit (JSON lines; bot.py's Session does the per-message work).

The gate's dealer state -> the kit's `act` dict (players in position order, raise-by bounds, the per-street log
with raise-by amounts and no blinds), the reply "f"/"c"/"r<N>" -> (kind, raise-to total), the hand end -> the kit's
`end` dict. Only `call` is timed; the end runs outside it, as the kit's reply-first entry does.
"""
from __future__ import annotations

import sys
import os



def _by_street(rows, posts=(), upto=None):
    streets = [[]]
    have = {}
    for seat, kind, chips in posts or ():
        seat, chips = int(seat), int(chips)
        if kind != "ante":
            have[seat] = have.get(seat, 0) + chips
    for row in rows or ():
        seat, kind, street, put = int(row[0]), str(row[1]), int(row[3]), int(row[4])
        while len(streets) <= street:
            streets.append([])
            have = {}
        have[seat] = have.get(seat, 0) + put
        streets[street].append((seat, kind, have[seat], put))
    while upto is not None and len(streets) <= upto:
        streets.append([])
    return streets


_CODE = {"fold": "f", "check": "k", "call": "c"}


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit = module, kit
        self.sess = module.SESS
        self.handles = []
        self.n = 8
        self.me = 0
        self.bb = 20

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n, self.me = n, seat
        self.handles = ["p%d" % i for i in range(n)]
        self.sess.you = self.handles[seat]
        self.sess.table({"t": "table", "seats": self.handles, "stack": stack, "button": self.handles[0],
                         "max_hands": 200})

    def _log(self, rows, posts, upto, bb):
        out = []
        for s, street in enumerate(_by_street(rows, posts, upto)):
            top = bb if s == 0 else 0
            toks = []
            for seat, kind, to, _put in street:
                h = self.handles[seat]
                if kind == "raise":
                    toks.append("%s:r%d" % (h, to - top))
                    top = to
                elif kind in _CODE:
                    toks.append("%s:%s" % (h, _CODE[kind]))
            out.append(" ".join(toks))
        return "/".join(out)

    def native(self, st: dict):
        n = len(st["stacks"])
        stacks, bets, inh = st["stacks"], st["bets"], st["in_hand"]
        total = [0] * n
        for seat, kind, chips in st.get("posts") or ():
            total[int(seat)] += int(chips)
        for row in st.get("history") or ():
            if len(row) > 4:
                total[int(row[0])] += int(row[4])
        alive = [i for i in range(n) if stacks[i] > 0 or inh[i] or total[i] > 0]
        b = int(st["button"])
        order = sorted(alive, key=lambda i: (i - b - 1) % n)  # SB first ... button last
        if len(alive) == 2:
            order = sorted(alive, key=lambda i: (i - b) % n)  # heads-up: the button is the SB, first
        players = []
        for i in order:
            state = ("allin" if stacks[i] == 0 else "live") if inh[i] else "folded"
            players.append({"h": self.handles[i], "stack": int(stacks[i]), "bet": int(bets[i]),
                            "total": int(total[i]), "state": state})
        seat = int(st["seat"])
        top = int(bets[seat]) + int(st["to_call"])
        legal = st["legal"]
        min_r = max_r = 0
        if "raise" in legal:
            min_r, max_r = int(st["min_raise"]) - top, int(st["max_raise"]) - top
        self.bb = int(st["blinds"][1])
        return {"t": "act", "table": 1, "hand": int(st["hand_no"]) + 1, "sb": int(st["blinds"][0]),
                "bb": self.bb, "you": self.handles[seat], "button": self.handles[b], "cards": list(st["hole"]),
                "board": list(st["board"]), "pot": int(st["pot"]) + sum(int(x) for x in bets),
                "to_call": int(st["to_call"]), "min_r": min_r, "max_r": max_r, "players": players,
                "log": self._log(st.get("history"), st.get("posts"), int(st["street"]), self.bb)}

    def call(self, native):
        return self.sess.act(native)

    def parse(self, reply, st: dict):
        if not isinstance(reply, str):
            raise ValueError("reply not a string")
        to_call = int(st["to_call"])
        mine = int(st["bets"][int(st["seat"])])
        if reply == "f":
            return ("fold", 0) if to_call > 0 else ("check", 0)
        if reply == "c":
            return ("call", mine + to_call) if to_call > 0 else ("check", 0)
        if reply[:1] == "r" and reply[1:].isdigit():
            if "raise" not in st["legal"]:
                return ("call", mine + to_call) if to_call > 0 else ("check", 0)
            top = mine + to_call
            n = min(max(int(reply[1:]), int(st["min_raise"]) - top), int(st["max_raise"]) - top)
            return "raise", top + n
        raise ValueError("bad reply %r" % (reply,))

    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        r = result or {}
        s = self.sess
        hand = hand_no + 1
        before = dict(s.start_stacks)
        if s.hand_no == hand and s.hand_start:
            before.update(s.hand_start)
        deltas = list(r.get("deltas") or [0] * self.n)
        stacks = {}
        out = []
        for i, h in enumerate(self.handles):
            b = before.get(h, 0)
            a = b + int(deltas[i]) if i < len(deltas) else b
            if b > 0 or a > 0:
                stacks[h] = a
            if b > 0 and a == 0:
                out.append(h)
        shown = {self.handles[int(k)]: list(v) for k, v in (r.get("showdown") or {}).items()}
        bb = s.bb(hand)
        msg = {"t": "end", "table": 1, "hand": hand, "board": list(r.get("board") or ()),
               "log": self._log(r.get("history"), r.get("posts"), None, bb), "shown": shown, "best": {},
               "won": {}, "stacks": stacks, "out": out}
        s.end(msg)
