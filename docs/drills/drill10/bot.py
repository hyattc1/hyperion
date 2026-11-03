"""Solo Hold'em entry: JSON lines on stdin/stdout (kit README 4). One process plays the whole session.

Everything is imported, built and warmed before the hello reply. `act` is decided then answered; `end` and `over`
are answered FIRST and processed after (their 1 ms clock stops at our reply); `table` is processed then answered
(50 ms budget). Any failure answers the kit's check-else-fold. Logs only to stderr.
"""
from __future__ import annotations

import gc
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOTS = (_HERE,) if os.path.isdir(os.path.join(_HERE, "hyperion")) else (os.path.dirname(_HERE), _HERE)
for _p in _ROOTS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

if os.path.exists(os.path.join(_HERE, "check.on")):  # local only: the kit sim strips the environment
    os.environ["HYPERION_CHECK"] = "1"

_OUT = sys.stdout
_ERR = {"n": 0}


def _say(obj) -> None:
    _OUT.write(json.dumps(obj, separators=(",", ":")) + "\n")
    _OUT.flush()


def _log(msg: str) -> None:
    try:
        sys.stderr.write(msg + "\n")
    except Exception:  # noqa: BLE001
        pass


AD = None
RULES = None
HAND_END = "defer"
try:
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.drills.adapter import pin_package, repin_package
    from hyperion.drills.conformance import warmed
    from hyperion.tablegen import rules_from_dict

    from adapter import history, make_adapter

    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            RULES = rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        RULES = Rules()
    _bot = ship.make_bot()
    # `end` is answered before it is processed. HAND_END "defer": the bot's hand end runs only its light part there
    # and the ICM curve waits for the Hero that decides next (the composite has two Heros; eager computes both)
    if HAND_END == "defer":
        try:
            _bot.defer_hand_end(True)
        except Exception:  # noqa: BLE001
            pass
    AD = make_adapter(_bot, RULES)
except Exception as e:  # noqa: BLE001 - no bot: the loop still answers check-else-fold
    _log("entry: build failed: %r" % (e,))
    AD = None


class Session:
    def __init__(self, ad):
        self.ad = ad
        self.you = None
        self.seats: list = []
        self.start_stacks: dict = {}
        self.hand_start: dict = {}
        self.hand_no = None
        self.active = False

    def table(self, m) -> None:
        self.seats = list(m.get("seats") or [])
        st = int(m.get("stack") or 2000)
        self.start_stacks = {h: st for h in self.seats}
        self.hand_start = {}
        self.hand_no = None
        self.active = True
        if self.ad is None:
            return
        self.ad.set_table(self.seats)
        me = self.you if self.you in self.seats else (self.seats[0] if self.seats else None)
        self.ad.start(self.seats.index(me) if me in self.seats else 0, len(self.seats), RULES)

    def act(self, m) -> str:
        if self.ad is None or not self.active:
            return "c" if int(m.get("to_call") or 0) == 0 else "f"
        h = m.get("hand")
        if h != self.hand_no:
            self.hand_no = h
            self.hand_start = {p["h"]: int(p["stack"]) + int(p["total"]) for p in m["players"]}
        return self.ad.decide(m)

    def end(self, m) -> None:
        if self.ad is None or not self.active:
            return
        idx = self.ad.idx
        n = len(self.seats)
        hand = int(m["hand"])
        before = dict(self.start_stacks)
        if self.hand_no == hand and self.hand_start:
            before.update(self.hand_start)
        after = {h: int(v) for h, v in (m.get("stacks") or {}).items()}
        final = [0] * n
        deltas = [0] * n
        for h, i in idx.items():
            a = after.get(h, 0 if h in (m.get("out") or ()) else before.get(h, 0))
            final[i] = a
            deltas[i] = a - before.get(h, 0)
        self.start_stacks = {h: final[i] for h, i in idx.items()}
        me = idx.get(self.you, 0)
        shown = {idx[h]: tuple(int(c) for c in cs) for h, cs in (m.get("shown") or {}).items() if h in idx}
        self.ad.hand_end(hand, deltas[me], n, history=history(m.get("log", ""), idx, int(self.bb(hand))),
                         deltas=deltas, showdown=shown, board=tuple(int(c) for c in (m.get("board") or ())))

    @staticmethod
    def bb(hand: int) -> int:
        try:
            lv = min(len(RULES.blind_levels) - 1, (int(hand) - 1) // int(RULES.hands_per_level))
            return int(RULES.blind_levels[lv][1])
        except Exception:  # noqa: BLE001
            return 20


def _warm(sess: Session) -> None:
    """Made-up kit states, so the translation and decision paths ran once before the clock starts."""
    seats = ["w%d" % i for i in range(8)]
    sess.you = "w3"
    sess.table({"seats": seats, "stack": 2000, "button": "w0"})
    pl = [{"h": seats[(1 + k) % 8], "stack": 2000, "bet": 0, "total": 0, "state": "live"} for k in range(8)]
    pl[0].update(stack=1990, bet=10, total=10)
    pl[1].update(stack=1980, bet=20, total=20)
    pre = {"t": "act", "table": 1, "hand": 1, "sb": 10, "bb": 20, "you": "w3", "button": "w0", "cards": [48, 49],
           "board": [], "pot": 30, "to_call": 20, "min_r": 20, "max_r": 1980, "players": pl, "log": ""}
    for cards in ([48, 49], [0, 21], [50, 46]):
        pre["cards"] = cards
        sess.act(dict(pre))
    pl2 = [dict(p, bet=0) for p in pl]
    for p in pl2:
        p["state"] = "folded"
    for k in (1, 2):
        pl2[k].update(state="live", stack=1940, total=60)
    pl2[0].update(stack=1990, total=10)
    flop = {"t": "act", "table": 1, "hand": 1, "sb": 10, "bb": 20, "you": "w3", "button": "w0", "cards": [48, 49],
            "board": [8, 22, 37], "pot": 130, "to_call": 0, "min_r": 20, "max_r": 1940, "players": pl2,
            "log": "w3:r40 w4:f w5:f w6:f w7:f w0:f w1:f w2:c/w2:k"}
    sess.act(flop)
    sess.end({"t": "end", "table": 1, "hand": 1, "board": [8, 22, 37, 40, 5],
              "log": "w3:r40 w4:f w5:f w6:f w7:f w0:f w1:f w2:c/w2:k w3:r40 w2:f",
              "shown": {}, "best": {}, "won": {"w3": 170}, "stacks": {"w3": 2070, "w2": 1940, "w1": 1990},
              "out": []})
    sess.active = False


SESS = Session(AD)
if AD is not None:
    try:
        _warm(SESS)
        warmed(AD)
        pin_package(*_ROOTS)
    except Exception as e:  # noqa: BLE001
        _log("entry: warm-up failed: %r" % (e,))
    SESS.you = None
gc.collect()
try:
    gc.freeze()
except Exception:  # noqa: BLE001
    pass
gc.disable()


_NOEND = os.path.exists(os.path.join(_HERE, "noend.on"))  # local experiment only
_TIMING = os.path.exists(os.path.join(_HERE, "timing.on"))  # local only: per-message timings to stderr at exit


class _Lines:
    """stdin as lines from the raw fd, so `waiting()` sees a message the engine has already sent."""

    def __init__(self, fd: int = 0):
        import select
        self.fd, self.buf, self.sel = fd, b"", select.select

    def readline(self) -> str:
        while True:
            i = self.buf.find(b"\n")
            if i >= 0:
                line, self.buf = self.buf[:i + 1], self.buf[i + 1:]
                return line.decode("utf-8", "replace")
            chunk = os.read(self.fd, 65536)
            if not chunk:
                line, self.buf = self.buf, b""
                return line.decode("utf-8", "replace")
            self.buf += chunk

    def waiting(self) -> bool:
        if b"\n" in self.buf:
            return True
        try:
            return bool(self.sel([self.fd], [], [], 0)[0])
        except Exception:  # noqa: BLE001
            return False


_SKIPPED = {"n": 0}


def main() -> None:
    sess = SESS
    try:
        _in = _Lines(sys.stdin.fileno())
        rd, waiting = _in.readline, _in.waiting
    except Exception:  # noqa: BLE001
        rd, waiting = sys.stdin.readline, (lambda: False)
    if _TIMING:
        import time as _t
        pc, cpu = _t.perf_counter_ns, _t.process_time_ns
        rows = []
    while True:
        line = rd()
        if _TIMING:
            t_in, c_in = pc(), cpu()
            if rows:
                rows[-1].append(t_in)
        if not line:
            break
        line = line.strip()
        if not line:
            continue
        mid = None
        try:
            m = json.loads(line)
            mid = m.get("id")
            t = m.get("t")
        except Exception:  # noqa: BLE001
            _ERR["n"] += 1
            continue
        if t == "act":
            try:
                a = sess.act(m)
                if not isinstance(a, str) or not (a in ("f", "c") or (a[:1] == "r" and a[1:].isdigit())):
                    raise ValueError(a)
            except Exception:  # noqa: BLE001
                _ERR["n"] += 1
                try:
                    a = "c" if int(m.get("to_call") or 0) == 0 else "f"
                except Exception:  # noqa: BLE001
                    a = "f"
            _say({"id": mid, "a": a})
        elif t == "end":
            _say({"id": mid})
            try:
                # the bot's hand end only when the engine is not already waiting on us: a message in the pipe is on
                # its clock (the next act is self-contained; a skipped hand end costs the profiler one hand)
                if _NOEND or waiting():
                    _SKIPPED["n"] += 1
                else:
                    sess.end(m)
            except Exception:  # noqa: BLE001
                _ERR["n"] += 1
        elif t == "table":
            try:
                sess.table(m)
            except Exception:  # noqa: BLE001
                _ERR["n"] += 1
            _say({"id": mid})
        elif t == "hello":
            sess.you = m.get("you")
            _say({"id": mid})
        elif t == "over":
            _say({"id": mid})
            sess.active = False
            gc.collect()
        else:
            _say({"id": mid})
        if _TIMING:
            rows.append([t, t_in, c_in, pc(), cpu()])
    if _TIMING:
        import collections
        agg = collections.defaultdict(list)
        for r in rows:
            if len(r) == 6:
                agg[r[0]].append(((r[3] - r[1]) / 1e3, (r[4] - r[2]) / 1e3, (r[5] - r[3]) / 1e3))
        for k, v in agg.items():
            w = sorted(x[0] for x in v); c = sorted(x[1] for x in v); g = sorted(x[2] for x in v)
            q = lambda a, f: a[min(len(a) - 1, int(f * len(a)))]
            _log("timing %s n=%d wall p50 %.0f p90 %.0f p99 %.0f | cpu p50 %.0f p90 %.0f p99 %.0f | idle-after p10 %.0f p50 %.0f"
                 % (k, len(v), q(w, .5), q(w, .9), q(w, .99), q(c, .5), q(c, .9), q(c, .99), q(g, .1), q(g, .5)))
    if os.environ.get("HYPERION_CHECK") == "1":
        _log("entry: swallowed errors %d, hand ends skipped (message waiting) %d" % (_ERR["n"], _SKIPPED["n"]))


if __name__ == "__main__":
    if os.path.exists(os.path.join(_HERE, "profile.on")):  # local only
        import cProfile, pstats, io
        _pr = cProfile.Profile(); _pr.enable(); main(); _pr.disable()
        _s = io.StringIO(); pstats.Stats(_pr, stream=_s).sort_stats("tottime").print_stats(25); _log(_s.getvalue())
        _s = io.StringIO(); pstats.Stats(_pr, stream=_s).sort_stats("cumtime").print_stats(30); _log(_s.getvalue())
    else:
        main()
