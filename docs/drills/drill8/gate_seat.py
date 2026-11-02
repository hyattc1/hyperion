"""Gate seat for the Ghost Hold'em kit: the fake dealer dict -> the kit's `s` (relative seats, chips-put-in-now ints).

The log is rebuilt from the dealer's history rows WITHOUT street markers: raise tokens carry (total - this seat's
running sum since the hand began), calls carry 0, so the adapter's parser (which only resets its sums on "/")
recovers every raise-to total. The real kit's "/" path is covered by the kit simulator's conformance run.
"""
from types import SimpleNamespace


def _rot(xs, seat, n):
    return [xs[(seat + j) % n] for j in range(n)]


def _log(rows, seat, n, blinds, button, stacks0=None):
    acc = [0] * n
    toks = []
    for row in rows:
        s, kind, total = int(row[0]), str(row[1]), int(row[2])
        rs = (s - seat) % n
        if kind == "raise":
            toks.append("%dr%d" % (rs, total - acc[rs]))
            acc[rs] = total
        elif kind == "call":
            toks.append("%dc0" % rs)
        elif kind == "check":
            toks.append("%dk" % rs)
        elif kind == "fold":
            toks.append("%df" % rs)
    return " ".join(toks)


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit, self.agent = module, kit, None

    def start(self, seat, n, stack, blinds):
        self.seat, self.n = seat, n
        if self.agent is None:
            self.agent = self.mod.Agent()
        t = SimpleNamespace(table_id="g", ids=tuple("p%d" % i for i in range(n)), stack=stack,
                            blinds=((blinds[0], blinds[1]),), level_hands=25, max_hands=200,
                            points=(16, 11, 8, 6, 4, 2, 1, 0),
                            limits_ns={"act": 1000000, "hand_over": 1000000, "new_table": 50000000})
        if hasattr(self.agent, "new_table"):
            self.agent.new_table(t)

    def native(self, st):
        seat, n = int(st["seat"]), len(st["stacks"])
        stacks, bets, inh = list(st["stacks"]), list(st["bets"]), list(st["in_hand"])
        my_bet, my_stack = bets[seat], stacks[seat]
        legal = set(st["legal"])
        owe = int(st["to_call"])
        if "raise" in legal and st.get("min_raise") is not None:
            mr = min(int(st["min_raise"]) - my_bet, my_stack)
        else:
            mr = 0
        status = "".join("A" if (inh[i] and stacks[i] > 0) else "X" if inh[i] else ("-" if stacks[i] == 0 else "F")
                         for i in range(n))
        sb, bb = st["blinds"]
        return SimpleNamespace(
            hand_no=int(st["hand_no"]), street=int(st["street"]), hole=tuple(st["hole"]), board=tuple(st["board"]),
            stack=my_stack, owe=owe, min_raise=mr, pot=int(st["pot"]) + sum(bets), haunt=0, sb=int(sb), bb=int(bb),
            button=(int(st["button"]) - seat) % n, stacks=tuple(_rot(stacks, seat, n)), bets=tuple(_rot(bets, seat, n)),
            status=_rotstr(status, seat, n), log=_log(st.get("history") or (), seat, n, (sb, bb), st["button"]))

    def call(self, native):
        return self.agent.act(native)

    def parse(self, reply, st):
        seat = int(st["seat"])
        my_bet, my_stack = st["bets"][seat], st["stacks"][seat]
        owe = int(st["to_call"])
        legal = set(st["legal"])
        mr = min(int(st["min_raise"]) - my_bet, my_stack) if ("raise" in legal and st.get("min_raise") is not None) else 0
        if isinstance(reply, bool) or not isinstance(reply, (int, float)):
            return ("check" if owe == 0 else "fold", 0)
        n = int(reply)
        if n < owe:
            return ("check" if owe == 0 else "fold", 0)
        if mr == 0 or n < mr:
            return ("check" if owe == 0 else "call", 0)
        return ("raise", min(n, my_stack) + my_bet)

    def end(self, hand_no, delta, result):
        if not hasattr(self.agent, "hand_over"):
            return
        seat, n = self.seat, self.n
        res = result or {}
        deltas = list(res.get("deltas") or [0] * n)
        if len(deltas) == n:
            deltas = _rot(deltas, seat, n)
        else:
            deltas = [delta] + [0] * (n - 1)
        shown = {(int(k) - seat) % n: tuple(v) for k, v in (res.get("showdown") or {}).items()}
        r = SimpleNamespace(hand_no=hand_no, board=tuple(res.get("board") or ()), shown=shown, ghost=None, pots=[],
                            haunted=0, delta=tuple(deltas), stacks=(), log=_log(res.get("history") or (), seat, n,
                                                                                 None, 0),
                            busted=(), place=0, table_over=False, places=None)
        self.agent.hand_over(r)


def _rotstr(s, seat, n):
    return "".join(s[(seat + j) % n] for j in range(n))
