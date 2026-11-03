"""Tonight's entry for a kit that runs the bot as ITS OWN PROCESS speaking JSON lines on stdin/stdout (drill 10's kit
H: `python3 -u bot.py`, one JSON object a line in, one reply a line out echoing its id, every message on the engine's
clock). Copy it to `submission/<the kit's entry file>` beside `submission/adapter.py` (from adapter_template.py) and
fill the TODOs in order. A kit that imports a file and builds a bot object: entry_template.py; one call per event with
no state: event_player_template.py. The defaults are kit H's protocol, worked through (docs/drills/drill10/bot.py, the
drill 10 player's entry, is where they come from), and Session expects that player's adapter shape (`set_table(handles)`,
`idx` handle -> seat, `history(log, idx, bb)`: docs/drills/drill10/adapter.py, with which this file runs kit H as is).

What it does without being asked, each from drill 10:
- Everything is imported, built and warmed at import, before the first line is read (kit H: 2 s for `hello` from the
  launch), the package pinned (`pin_package`), the garbage collector frozen and off (a collection is a stall).
- One reply per request, written unbuffered with os.write on a private copy of stdout; fd 1 itself is pointed at
  stderr, so a stray print anywhere in the package never lands in the protocol (kit H ignores it but charges the time).
- Each request is ANSWERED FIRST and the deferred work runs after: a decision is decided, then answered; a hand end or a
  table end is answered at once, then processed. The bot's hand end is deferred (`defer_hand_end(True)`: the light part
  in the hand end, the ICM curve and the profiler's dials in `idle()`), and both run only while no other request is
  already waiting on stdin (`select` on the raw fd, plus what this loop has buffered): a message in the pipe is on the
  engine's clock, so its hand end is skipped and counted (the next decision is self-contained; the bot's reads lose one
  hand), and the pending curve is computed by the decision that needs it. Drill 10, kit H at load 22-28: the composite
  did ~280 us of hand-end work with the next message already waiting; answer first, defer and skip took one seed from
  61% to 33% timeouts and 5.57 to 7.13 points.
- The table start is processed BEFORE its reply (the next decision needs it, and it has its own budget: kit H 50 ms).
- Local checks by MARKER FILE, never by environment: a kit may launch the bot with a fixed environment (kit H passes
  PATH, PYTHONUNBUFFERED, PYTHONDONTWRITEBYTECODE and LANG only), so HYPERION_CHECK=1 never reaches it. `check.on` beside
  this file turns the conformance report and the error line on (both to stderr at exit). Never ship a marker:
  tools/pack.py copies only what --extra names.
- Every kit call is wrapped: nothing raises out of the loop; an answer outside the kit's forms is its check-or-fold.

Checks, in order: the kit's simulator with `check.on` (0 violations, 0 exceptions; the exit line reads 0 errors and
counts the skipped hand ends); tools/pack.py (--import-budget the kit's start budget, both its size caps); tools/gate.py
with submission/gate_seat.py from process_gate_seat_template.py, which launches this file as its own process and plays
the real stdin loop through a pipe (`--kit submission/gate_seat.py --entry bot.py`).
"""
from __future__ import annotations

import gc
import json
import os
import sys
from collections import Counter

# run as the kit's process: the protocol's own copy of stdout first, before any import can print, and fd 1 becomes
# stderr for everything else. Imported (tools/pack.py's import probe prints its timing on stdout): fds left alone
if __name__ == "__main__":
    _OUT_FD = os.dup(1)
    os.dup2(2, 1)
else:
    _OUT_FD = 1

_HERE = os.path.dirname(os.path.abspath(__file__))
# in the package tools/pack.py builds, hyperion/ sits beside this file; run from the repo's submission/, one level up
_ROOTS = (_HERE,) if os.path.isdir(os.path.join(_HERE, "hyperion")) else (os.path.dirname(_HERE), _HERE)
for _p in _ROOTS:
    if _p not in sys.path:
        sys.path.insert(0, _p)

CHECK = os.path.exists(os.path.join(_HERE, "check.on"))  # local only: the kit may strip the environment
if CHECK:
    os.environ["HYPERION_CHECK"] = "1"  # before the adapter is built: maybe_checked reads it

ERRORS: Counter = Counter()  # what the wrappers swallowed; printed at exit with check.on
SKIPPED = Counter()  # hand ends (and idle work) skipped because a message was already waiting

# TODO 0  the protocol, from the kit's README (kit H's, section 4): the id to echo, the type field and the type names,
#   and the reply. `DECIDE` is the only request that needs an action.
ID, TYPE = "id", "t"
HELLO, TABLE, DECIDE, HAND_END, TABLE_END = "hello", "table", "act", "end", "over"


def reply(mid, action: str | None = None) -> dict:
    """The reply line's object: kit H's {"id": n} and {"id": n, "a": "c"}."""
    return {ID: mid} if action is None else {ID: mid, "a": action}


def answer_ok(a) -> bool:
    """TODO 1  the kit's answer forms (kit H: "f", "c", "r<N>" with N a positive integer); anything else is an error
    the kit plays as its default, so the loop sends the check-or-fold instead."""
    return isinstance(a, str) and (a in ("f", "c") or (a[:1] == "r" and a[1:].isdigit() and int(a[1:]) > 0))


def check_or_fold(m) -> str:
    """TODO 1b  the kit's check-else-fold for a decision (kit H: "c" with nothing to call, else "f")."""
    try:
        return "c" if int(m.get("to_call") or 0) == 0 else "f"
    except Exception:  # noqa: BLE001
        return "f"


AD = None
RULES = None
try:
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.drills.adapter import pin_package
    from hyperion.drills.conformance import warmed
    from hyperion.tablegen import rules_from_dict

    from adapter import history, make_adapter  # submission/adapter.py: a sibling in the zip, never submission.

    try:
        with open(os.path.join(_HERE, "rules_tonight.json")) as f:
            RULES = rules_from_dict(json.load(f))
    except Exception:  # noqa: BLE001
        RULES = Rules()
    BOT = ship.make_bot()
    try:
        BOT.defer_hand_end(True)  # the hand end's light part only; idle() does the rest when nothing waits
    except Exception:  # noqa: BLE001
        pass
    AD = make_adapter(BOT, RULES)
except Exception as e:  # noqa: BLE001 - no bot: the loop still answers, check-or-fold
    ERRORS["build"] += 1
    sys.stderr.write(f"entry: build failed: {e!r}\n")
    BOT = None


class Session:
    """TODO 2  the kit's messages -> the adapter (kit H's, worked: handles as seats, stacks from the players list, the
    hand's deltas from the hand end's stacks against each hand's start). One per process; tables come and go."""

    def __init__(self, ad):
        self.ad = ad
        self.you = None
        self.seats: list = []
        self.start_stacks: dict = {}
        self.hand_start: dict = {}
        self.hand_no = None
        self.active = False

    def hello(self, m) -> None:
        self.you = m.get("you")

    def table(self, m) -> None:
        self.seats = list(m.get("seats") or [])
        st = int(m.get("stack") or (RULES.starting_stack if RULES else 2000))
        self.start_stacks = {h: st for h in self.seats}
        self.hand_start, self.hand_no, self.active = {}, None, True
        if self.ad is None:
            return
        self.ad.set_table(self.seats)
        me = self.seats.index(self.you) if self.you in self.seats else 0
        self.ad.start(me, len(self.seats), RULES)

    def act(self, m) -> str:
        if self.ad is None or not self.active:
            return check_or_fold(m)
        h = m.get("hand")
        if h != self.hand_no:  # the hand's first decision: everyone's chips at its start
            self.hand_no = h
            self.hand_start = {p["h"]: int(p["stack"]) + int(p["total"]) for p in m["players"]}
        return self.ad.decide(m)

    def end(self, m, deliver: bool = True) -> None:
        """The hand's chips (always: a few dict entries) and, with `deliver`, the bot's hand end.

        TODO 2a  each seat's chip change: kit H's end carries every seat's chips after the hand, so the deltas are those
        less the chips at the hand's start (below). A kit whose end carries `won` instead: chips collected or net
        change? The README says which: collected (kit I) is `won - paid` (what the seat put in this hand), net change
        (kit G) is `won` as it is. The wrong one feeds the bot wrong stacks in silence; right, they sum to 0."""
        if self.ad is None or not self.active:
            return
        idx = self.ad.idx
        before = dict(self.start_stacks)
        if self.hand_no == m.get("hand") and self.hand_start:
            before.update(self.hand_start)
        after = {h: int(v) for h, v in (m.get("stacks") or {}).items()}
        out = set(m.get("out") or ())
        n = len(self.seats)
        final, deltas = [0] * n, [0] * n
        for h, i in idx.items():
            a = after.get(h, 0 if h in out else before.get(h, 0))
            final[i], deltas[i] = a, a - before.get(h, 0)
        self.start_stacks = {h: final[i] for h, i in idx.items()}
        if not deliver:
            return
        me = idx.get(self.you, 0)
        hand = int(m.get("hand") or 0)
        shown = {idx[h]: tuple(int(c) for c in cs) for h, cs in (m.get("shown") or {}).items() if h in idx}
        self.ad.hand_end(hand, deltas[me], n, history=history(m.get("log", ""), idx, self.bb(hand)), deltas=deltas,
                         showdown=shown, board=tuple(int(c) for c in (m.get("board") or ())))

    def over(self, m) -> None:
        self.active = False

    @staticmethod
    def bb(hand: int) -> int:
        try:
            lv = min(len(RULES.blind_levels) - 1, (int(hand) - 1) // int(RULES.hands_per_level))
            return int(RULES.blind_levels[lv][1])
        except Exception:  # noqa: BLE001
            return 20


def warm_messages() -> list:
    """TODO 3  WARM-UP: one table, one decision per street and one hand end in the kit's own shape (its README's
    examples), so the translation and the decision path have run before the clock starts. Kit H's, made up."""
    seats = ["w%d" % i for i in range(8)]
    pl = [{"h": seats[(1 + k) % 8], "stack": 2000, "bet": 0, "total": 0, "state": "live"} for k in range(8)]
    pl[0].update(stack=1990, bet=10, total=10)
    pl[1].update(stack=1980, bet=20, total=20)
    pre = {"t": "act", "table": 1, "hand": 1, "sb": 10, "bb": 20, "you": "w3", "button": "w0", "cards": [48, 49],
           "board": [], "pot": 30, "to_call": 20, "min_r": 20, "max_r": 1980, "players": pl, "log": ""}
    out = [{"t": "hello", "you": "w3"}, {"t": "table", "seats": seats, "stack": 2000, "button": "w0"}]
    out += [dict(pre, cards=c) for c in ([48, 49], [0, 21], [50, 46])]
    pl2 = [dict(p, bet=0, state="folded") for p in pl]
    for k in (1, 2):
        pl2[k].update(state="live", stack=1940, total=60)
    pl2[0].update(stack=1990, total=10)
    out.append({"t": "act", "table": 1, "hand": 1, "sb": 10, "bb": 20, "you": "w3", "button": "w0", "cards": [48, 49],
                "board": [8, 22, 37], "pot": 130, "to_call": 0, "min_r": 20, "max_r": 1940, "players": pl2,
                "log": "w3:r40 w4:f w5:f w6:f w7:f w0:f w1:f w2:c/w2:k"})
    out.append({"t": "end", "table": 1, "hand": 1, "board": [8, 22, 37, 40, 5],
                "log": "w3:r40 w4:f w5:f w6:f w7:f w0:f w1:f w2:c/w2:k w3:r40 w2:f", "shown": {}, "best": {},
                "won": {"w3": 170}, "stacks": {"w3": 2070, "w2": 1940, "w1": 1990}, "out": []})
    return out


SESS = Session(AD)
if AD is not None:
    try:
        for _m in warm_messages():
            _t = _m.get(TYPE)
            if _t == HELLO:
                SESS.hello(_m)
            elif _t == TABLE:
                SESS.table(_m)
            elif _t == DECIDE:
                SESS.act(_m)
            elif _t == HAND_END:
                SESS.end(_m)
        BOT.idle()
        SESS.active, SESS.you = False, None
        warmed(AD)  # the conformance report forgets the made-up hand
    except Exception as e:  # noqa: BLE001
        ERRORS["warm_up"] += 1
        sys.stderr.write(f"entry: warm-up failed: {e!r}\n")
    try:
        pin_package(*_ROOTS)
    except Exception:  # noqa: BLE001
        ERRORS["pin"] += 1
gc.collect()
try:
    gc.freeze()
except AttributeError:
    pass
gc.disable()


class Lines:
    """Request lines from the raw fd, so `waiting()` sees a message the engine has already sent: a complete line
    already buffered here, or bytes in the pipe (select with no wait)."""

    def __init__(self, fd: int = 0):
        import select

        self.fd, self.buf, self._select = fd, b"", select.select

    def readline(self) -> bytes:
        while True:
            i = self.buf.find(b"\n")
            if i >= 0:
                line, self.buf = self.buf[:i + 1], self.buf[i + 1:]
                return line
            chunk = os.read(self.fd, 65536)
            if not chunk:  # stdin closed: the session is over
                line, self.buf = self.buf, b""
                return line
            self.buf += chunk

    def waiting(self) -> bool:
        if b"\n" in self.buf:
            return True
        try:
            return bool(self._select([self.fd], [], [], 0)[0])
        except Exception:  # noqa: BLE001
            return False


def send(fd: int, obj) -> None:
    """One reply line, unbuffered: os.write until every byte is out."""
    data = (json.dumps(obj, separators=(",", ":")) + "\n").encode()
    view = memoryview(data)
    while view:
        view = view[os.write(fd, view):]


def serve(in_fd: int = 0, out_fd: int | None = None, sess: Session | None = None) -> None:
    """The loop: read a request, answer it, then (only if nothing is waiting) the deferred work. Returns at EOF."""
    out_fd = _OUT_FD if out_fd is None else out_fd
    sess = SESS if sess is None else sess
    lines = Lines(in_fd)
    gc_due = False
    while True:
        raw = lines.readline()
        if not raw:
            return
        try:
            m = json.loads(raw)
            mid, t = m.get(ID), m.get(TYPE)
        except Exception:  # noqa: BLE001 - not a request: nothing to echo
            if raw.strip():
                ERRORS["bad_line"] += 1
            continue
        if t == DECIDE:
            try:
                a = sess.act(m)
                if not answer_ok(a):
                    ERRORS["bad_answer"] += 1
                    a = check_or_fold(m)
            except Exception:  # noqa: BLE001
                ERRORS["decide"] += 1
                a = check_or_fold(m)
            send(out_fd, reply(mid, a))
        elif t == HAND_END:
            send(out_fd, reply(mid))  # answered first: its clock stops here
            try:
                if lines.waiting():  # the next message is already on the engine's clock: the chips only
                    SKIPPED["hand_end"] += 1
                    sess.end(m, deliver=False)
                else:
                    sess.end(m)
                    if BOT is not None:
                        if lines.waiting():
                            SKIPPED["idle"] += 1  # the next decision computes the pending curve itself
                        else:
                            BOT.idle()
            except Exception:  # noqa: BLE001
                ERRORS["hand_end"] += 1
        elif t == TABLE:
            if gc_due:
                gc.collect()  # the last table's garbage, inside this message's own budget
                gc_due = False
            try:
                sess.table(m)
            except Exception:  # noqa: BLE001
                ERRORS["table"] += 1
            send(out_fd, reply(mid))
        elif t == TABLE_END:
            send(out_fd, reply(mid))
            try:
                sess.over(m)
            except Exception:  # noqa: BLE001
                ERRORS["table_end"] += 1
            if lines.waiting():
                gc_due = True
            else:
                gc.collect()
        elif t == HELLO:
            try:
                sess.hello(m)
            except Exception:  # noqa: BLE001
                ERRORS["hello"] += 1
            send(out_fd, reply(mid))
        else:
            send(out_fd, reply(mid))  # a message type this file does not know: echo it, as every message needs


def report() -> None:
    try:
        errs = ", ".join(f"{k} {v}" for k, v in sorted(ERRORS.items())) or "0"
        sk = ", ".join(f"{k} {v}" for k, v in sorted(SKIPPED.items())) or "0"
        sys.stderr.write(f"entry: swallowed errors {errs}; skipped with a message waiting {sk}\n")
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    serve()
    if CHECK:
        report()
