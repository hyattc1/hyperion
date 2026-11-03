"""Gate seat for tonight's Tranche Hold'em kit (module-level start/table/act/done in bot.py, relative seats, log string,
act returns chips added now). tools/gate.py --kit submission/gate_seat.py --entry bot.py. Only `call` is timed."""
from __future__ import annotations

from types import SimpleNamespace

from hyperion.drills.gate_seat_template import by_street

CODE = {"sb": "s", "bb": "b", "fold": "f", "check": "k", "call": "c", "raise": "r"}


def kit_log(rows, posts, me: int, n: int, upto: int | None = None) -> str:
    out = []
    for street in by_street(rows, posts, upto):
        toks = []
        for seat, kind, _to, put in street:
            c = CODE.get(kind)
            if c is not None:
                toks.append(f"{(seat - me) % n}{c}{put if c in 'sbcr' else ''}")
        out.append(" ".join(toks))
    return "/".join(out)


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit = module, kit
        self.me, self.n = 0, 8

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.me, self.n = int(seat), int(n)
        f = getattr(self.mod, "start", None)
        if f is not None and not getattr(self, "_started", False):
            f(SimpleNamespace(data_dir=".", limits_ms={"start": 3000, "table": 50, "act": 1, "done": 1}, seats=n,
                              starting_stack=stack, blinds=None, hands_per_level=25, max_hands=200, points=None,
                              tables=None))
            self._started = True
        f = getattr(self.mod, "table", None)
        if f is not None:
            f(SimpleNamespace(table=0, seats=n, stacks=tuple([stack] * n), button=0, blinds=None,
                              hands_per_level=25, max_hands=200, points=None))

    def _rel(self, xs):
        n, me = self.n, self.me
        return tuple(xs[(me + r) % n] for r in range(n))

    def native(self, st: dict):
        n, me = self.n, self.me
        street = int(st["street"])
        stacks = [int(x) for x in st["stacks"]]
        bets = [int(x) for x in st["bets"]]
        inh = list(st["in_hand"])
        seats = "".join(("p" if stacks[s] > 0 else "a") if inh[s] else ("f" if stacks[s] > 0 else "x")
                        for s in range(n))
        paid = []
        for s in range(n):
            p = [0, 0, 0, 0]
            p[street] = bets[s]
            paid.append(tuple(p))
        tr = [0, 0, 0, 0]
        tr[street] = sum(bets)
        if street > 0:
            tr[0] += int(st["pot"])
        legal = st["legal"]
        mr = int(st["min_raise"]) - bets[me] if "raise" in legal and st.get("min_raise") is not None else 0
        hand_no = int(st["hand_no"])
        sb, bb = int(st["blinds"][0]), int(st["blinds"][1])
        rel_seats = "".join(seats[(me + r) % n] for r in range(n))
        return SimpleNamespace(
            hole=tuple(st["hole"]), board=tuple(st["board"]), street=street, to_call=int(st["to_call"]),
            min_raise=max(0, mr), stack=stacks[me], stacks=self._rel(stacks), seats=rel_seats,
            paid=self._rel(paid), tranches=tuple(tr), button=(int(st["button"]) - me) % n, sb=sb, bb=bb,
            hand=hand_no + 1, level=hand_no // 25 + 1,
            log=kit_log(st.get("history") or (), st.get("posts") or (), me, n, street))

    def call(self, native):
        return self.mod.act(native)

    def parse(self, reply, st: dict):
        if type(reply) is not int:
            raise ValueError(f"not an int: {reply!r}")
        me = self.me
        to_call = int(st["to_call"])
        my_bet = int(st["bets"][me])
        stack = int(st["stacks"][me])
        legal = st["legal"]
        mr = int(st["min_raise"]) - my_bet if "raise" in legal and st.get("min_raise") is not None else 0
        if reply < to_call:
            return ("fold", 0) if to_call > 0 else ("check", 0)
        if mr <= 0 or reply < mr:
            return ("call", my_bet + to_call) if to_call > 0 else ("check", 0)
        return "raise", my_bet + min(reply, stack)

    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        r = result or {}
        n, me = self.n, self.me
        deltas = [int(x) for x in (r.get("deltas") or [0] * n)]
        sd = {int(s): tuple(h) for s, h in (r.get("showdown") or {}).items()}
        shown = [None] * n
        for s, h in sd.items():
            shown[s] = h
        f = getattr(self.mod, "done", None)
        if f is None:
            return
        f(SimpleNamespace(hand=hand_no + 1, board=tuple(r.get("board") or ()), shown=self._rel(shown),
                          paid=tuple([(0, 0, 0, 0)] * n), awards=((0,) * n,) * 4, won=self._rel(deltas),
                          stacks=None, log=kit_log(r.get("history") or (), r.get("posts") or (), me, n)))
