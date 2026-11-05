"""Gate seat for the Trailing Stop kit: the gate's dealer state -> the kit's View, loaded as engine/loader.py loads it."""
from __future__ import annotations

import importlib.util
import os
import sys
from collections import namedtuple

View = namedtuple("View", "hand level bb next_level_in street hole board pot owe min_raise max_raise me button players log recap")
Player = namedtuple("Player", "tag stack peak floor bet in_pot state")
Recap = namedtuple("Recap", "hand bb log board shown net out dividend")
TableInfo = namedtuple("TableInfo", "me tags start_chips blinds hands_per_level hand_cap stop_fraction points decision_limit_ms setup_limit_ms seed")
SCHEDULE = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
POINTS = (14, 9, 6, 4, 3, 2, 1, 0)
TAGS = ("qx", "mv", "tk", "ab", "cd", "ef", "gh", "ij")


def load_entry(path: str):
    folder = os.path.realpath(os.path.dirname(os.path.abspath(path)))
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location("_tsh_bot_0", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["_tsh_bot_0"] = mod
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = [p for p in sys.path if os.path.realpath(p or ".") != folder]
        pre = folder + os.sep
        for name, m in list(sys.modules.items()):
            f = getattr(m, "__file__", None)
            if f and os.path.realpath(f).startswith(pre):
                del sys.modules[name]
    return mod


def mask(cards) -> int:
    m = 0
    for c in cards:
        m |= 1 << (13 * (int(c) % 4) + int(c) // 4)
    return m


def stop_of(peak: int) -> int:
    return -(-peak * 3 // 5)


def g(x: float) -> str:
    return "%g" % x


class Seat:
    def __init__(self, module, kit):
        self.mod = module
        self.decide = None
        self.pending = []

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n, self.me = int(n), int(seat)
        self.stacks = [int(stack)] * self.n
        self.peaks = [int(stack)] * self.n
        self.floors = [stop_of(int(stack))] * self.n
        self.pending = []
        self.decide = self.mod.sit_down(TableInfo(TAGS[self.me], TAGS[:self.n], int(stack), SCHEDULE, 25, 200, 0.6, POINTS,
                                                  1.0, 25.0, 12345))

    def _log(self, rows, posts, bb, upto=None) -> str:
        toks, street, price = [], 0, bb
        for s, kind, chips in posts or ():
            if kind in ("sb", "bb"):
                toks.append(f"{TAGS[int(s)]}{'S' if kind == 'sb' else 'B'}{g(int(chips) / bb)}")
        for row in rows or ():
            seat, kind, total, st, put = int(row[0]), str(row[1]), int(row[2]), int(row[3]), int(row[4])
            while street < st:
                toks.append("/")
                street += 1
                price = 0
            t = TAGS[seat]
            if kind == "fold":
                toks.append(t + "F")
            elif kind == "check":
                toks.append(t + "K")
            elif kind == "call":
                toks.append(f"{t}C{g(put / bb)}")
            elif kind == "raise":
                toks.append(f"{t}R{g((total - price) / bb)}")
                price = total
        while upto is not None and street < upto:
            toks.append("/")
            street += 1
        return " ".join(toks)

    def native(self, st: dict):
        n, me = self.n, self.me
        stacks = [int(x) for x in st["stacks"]]
        bets = [int(x) for x in st["bets"]]
        inh = list(st["in_hand"])
        bb = int(st["blinds"][1])
        street = int(st["street"])
        paid = [0] * n
        for s, kind, chips in st.get("posts") or ():
            paid[int(s)] += int(chips)
        for row in st.get("history") or ():
            paid[int(row[0])] += int(row[4])
        live = [s for s in range(n) if self.stacks[s] > 0]
        btn = int(st["button"])
        i = live.index(btn) if btn in live else 0
        m = len(live)
        order = [live[(i + k) % m] for k in range(m)] if m == 2 else [live[(i + 1 + k) % m] for k in range(m)]
        players = tuple(Player(TAGS[s], stacks[s] / bb, self.peaks[s] / bb, self.floors[s] / bb, bets[s] / bb, paid[s] / bb,
                               "F" if not inh[s] else ("A" if stacks[s] == 0 else "L")) for s in order)
        to_call = int(st["to_call"])
        lo = hi = 0.0
        if "raise" in st["legal"] and st.get("max_raise") is not None:
            base = bets[me] + to_call
            lo = (int(st["min_raise"]) - base) / bb
            hi = (int(st["max_raise"]) - base) / bb
        hand = int(st["hand_no"])
        recap, self.pending = tuple(self.pending), []
        return View(hand + 1, min(hand // 25, 7) + 1, bb, 25 - hand % 25, street, mask(st["hole"]), mask(st["board"]),
                    (int(st["pot"]) + sum(bets)) / bb, to_call / bb, lo, hi, order.index(me), order.index(btn) if btn in order else 0,
                    players, self._log(st.get("history"), st.get("posts"), bb, street), recap)

    def call(self, native):
        return self.decide(native)

    def parse(self, reply, st: dict):
        me = int(st["seat"])
        to_call, my_bet = int(st["to_call"]), int(st["bets"][me])
        bb = int(st["blinds"][1])
        if reply == "f":
            return "fold", 0
        if reply == "c":
            return ("call", my_bet + to_call) if to_call > 0 else ("check", 0)
        if type(reply) is str and reply[:1] == "r":
            x = float(reply[1:])
            if not (x > 0.0 and x != float("inf")):
                raise ValueError(reply)
            if "raise" not in st["legal"]:
                return ("call", my_bet + to_call) if to_call > 0 else ("check", 0)
            total = my_bet + to_call + int(min(x, 1e9) * bb + 0.5)
            return "raise", max(int(st["min_raise"]), min(int(st["max_raise"]), total))
        raise ValueError(repr(reply))

    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        r = result or {}
        n = self.n
        deltas = [int(x) for x in (r.get("deltas") or [0] * n)]
        before = list(self.stacks)
        bb = SCHEDULE[min(int(hand_no) // 25, 7)][1]
        after = [before[s] + deltas[s] for s in range(n)]
        self.stacks = after
        for s in range(n):
            if after[s] > self.peaks[s]:
                self.peaks[s] = after[s]
                self.floors[s] = stop_of(after[s])
        if before[self.me] <= 0:
            return
        shown = tuple((TAGS[int(s)], mask(h)) for s, h in (r.get("showdown") or {}).items())
        net = tuple((TAGS[s], deltas[s] / bb) for s in range(n) if before[s] > 0)
        out = tuple(TAGS[s] for s in range(n) if before[s] > 0 and after[s] <= 0)
        self.pending.append(Recap(int(hand_no) + 1, bb, self._log(r.get("history"), r.get("posts"), bb), mask(r.get("board") or ()),
                                  shown, net, out, 0.0))
