"""Gate seat for the Chain Hold'em kit (in-process, class Agent, decide(s) -> token). Builds the kit's state object
from the gate's dealer dict (absolute seats -> offsets from us), and turns the token back into (kind, raise-to total)
by the kit's own sizing rule. The log is one street with raise increments chosen so the adapter's parser recovers
the dealer's raise-to totals exactly (the kit sim exercises the real per-street log)."""
from __future__ import annotations

PCT = {"R33": 33, "R50": 50, "R75": 75, "R100": 100, "R150": 150, "R250": 250}


def _log(rows, me, n):
    put, out = {}, []
    for row in rows or ():
        seat, kind, total = int(row[0]), str(row[1]), int(row[2])
        off = (seat - me) % n
        if kind == "fold":
            out.append(f"{off}f")
        elif kind == "check":
            out.append(f"{off}k")
        elif kind == "call":
            out.append(f"{off}c0")
        elif kind == "raise":
            add = total - put.get(off, 0)
            put[off] = total
            out.append(f"{off}r{add}")
    return ",".join(out)


class _S:
    def cost(self, token):
        if token == "F":
            return 0
        if token == "C":
            return self.to_call
        if token == "A":
            return self.stacks[0]
        pct = PCT[token]
        inc = max((self.pot + self.to_call) * pct // 100, self.min_raise_by)
        return min(self.to_call + inc, self.stacks[0])


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit, self.agent = module, kit, None
        self.me, self.n = 0, 8

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.me, self.n = seat, n
        self.agent = self.mod.Agent()
        info = _S()
        info.table, info.button, info.stacks = 0, 0, (stack,) * 8
        info.levels = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
        info.hands_per_level, info.max_hands = 25, 200
        info.points = (50, 32, 21, 14, 9, 5, 2, 0)
        info.menu = tuple(PCT)
        info.decision_ms, info.callback_ms, info.table_setup_ms = 1.0, 1.0, 20.0
        self.agent.begin_table(info)

    def _off(self, xs):
        n, me = self.n, self.me
        return tuple(xs[(me + i) % n] for i in range(n))

    def native(self, st: dict):
        n = self.n
        s = _S()
        hole = list(st["hole"])
        s.card, s.left, s.right = hole[0], hole[1], hole[2]
        s.hand = int(st["hand_no"]) + 1
        s.street = int(st["street"])
        s.board = tuple(st["board"])
        s.stacks = self._off(st["stacks"])
        s.bets = self._off(st["bets"])
        s.in_pot = s.bets
        ih = self._off(st["in_hand"])
        s.status = "".join(("A" if s.stacks[i] > 0 else "L") if ih[i] else ("F" if s.stacks[i] > 0 else "O")
                           for i in range(n))
        dealt = [i for i in range(n) if s.status[i] != "O"]
        s.left_nb = next((i for i in range(1, n) if s.status[i] != "O"), 0)
        s.right_nb = next((i for i in range(n - 1, 0, -1) if s.status[i] != "O"), 0)
        s.pot = int(st["pot"]) + sum(s.bets)
        s.to_call = int(st["to_call"])
        sb, bb = st["blinds"]
        s.sb, s.bb = int(sb), int(bb)
        mr = st.get("min_raise")
        s.min_raise_by = max(int(mr) - max(s.bets), s.bb) if mr else s.bb
        s.can_raise = "raise" in st["legal"]
        s.button = (int(st["button"]) - self.me) % n
        s.level = 1
        s.hands_left = 200 - s.hand
        s.log = _log(st.get("history"), self.me, n)
        s._dealt = dealt
        return s

    def call(self, native):
        return self.agent.decide(native)

    def parse(self, reply, st: dict):
        legal = st["legal"]
        to_call = int(st["to_call"])
        if reply == "F":
            return ("fold", 0) if to_call > 0 else ("check", 0)
        if reply == "C" or (reply in PCT or reply == "A") and "raise" not in legal:
            return ("call", 0) if to_call > 0 else ("check", 0)
        if reply == "A":
            return "raise", int(st["max_raise"])
        if reply in PCT:
            s = self.native(st)
            total = int(st["bets"][self.me]) + s.cost(reply)
            return "raise", min(max(total, int(st["min_raise"])), int(st["max_raise"]))
        raise ValueError(f"bad token {reply!r}")

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        r = _S()
        n = self.n
        result = result or {}
        r.hand = hand_no + 1
        r.board = tuple(result.get("board") or ())
        r.log = _log(result.get("history"), self.me, n)
        shown = {int(k): tuple(v) for k, v in (result.get("showdown") or {}).items()}
        r.shown = tuple(shown.get((self.me + i) % n) for i in range(n))
        d = result.get("deltas") or [0] * n
        r.won = self._off(d)
        r.stacks = (0,) * n
        r.place, r.points, r.table_over = 0, None, False
        self.agent.hand_over(r)
