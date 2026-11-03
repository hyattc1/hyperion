"""Gate seat for a PROCESS kit (the bot is its own process on JSON lines: drill 10's kit H): copy to
`submission/gate_seat.py`, fill the TODOs, and run `python tools/gate.py dist/submission.zip --kit submission/gate_seat.py
--entry bot.py --tables 100 --rules rules_tonight.json`.

`PROCESS = True` tells tools/gate_host.py not to import the entry in its own process: this seat LAUNCHES it, as the kit
does (`python -u <entry>`, the package directory as the working directory, the kit's fixed environment), and plays the
real stdin loop through a pipe: the reader, the reply-first order, the hand ends skipped while a message waits, the
unbuffered writes. An in-process seat calls the entry's methods and never tests any of that (drill 10's gate seat).
The gate's timed `call` is the round trip, write to read, as the kit's clock runs on the engine's side.

Each gate table is one bot process (the gate imports a package once per table): `start` launches it and sends the
kit's hello and table start; `native` builds the kit's decision request from the gate's dealer state (kit H's act
message: players in position order, raise-by bounds, the per-street log with raise-by amounts and no blinds);
`parse` turns the reply into (kind, raise-to total); `end` sends the kit's hand end and reads its reply (outside the
timed call: the kit times it too, but a slow hand end shows in the next decision's round trip, as on the kit, since
the bot is still busy when the next request arrives); `close` sends the table end and closes stdin. The defaults are
kit H's protocol, matching hyperion/drills/process_entry_template.py; the drill 10 player's in-process seat
(docs/drills/drill10/gate_seat.py) has the same translation.
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import sys

PROCESS = True  # tools/gate_host.py: launch the entry from here, never import it in-process

READY_S = 60.0  # the import on a loaded box (the kit's own hello budget is checked by tools/pack.py --import-budget)
REPLY_S = 5.0  # a reply slower than this: the bot is stuck; the seat raises and the gate counts the error
KIT_ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1",
           "LANG": "C.UTF-8"}  # TODO 0  the kit's launcher's environment (kit H: engine/botproc.py), exactly


def by_street(rows, posts=(), upto=None):
    """The gate's tagged rows [seat, kind, total, street, put] -> one list per street of (seat, kind, to, put), `to`
    the seat's chips in on that street after the action (posts counted, not listed). As gate_seat_template.by_street."""
    streets = [[]]
    have: dict = {}
    for seat, kind, chips in posts or ():
        if kind != "ante":
            have[int(seat)] = have.get(int(seat), 0) + int(chips)
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
    HAND_BASE = 1  # TODO 1  the kit's first hand number (ours is 0)

    def __init__(self, module, kit):
        self.entry = module.__file__  # gate_host passes the entry's path (PROCESS): the file the kit would run
        self.pkg = os.path.dirname(self.entry)
        self.kit = kit
        self.proc = None
        self.buf = b""
        self.next_id = 0
        self.handles: list = []
        self.n, self.me, self.bb = 8, 0, 20
        self.start_stacks: dict = {}
        self.hand_start: dict = {}
        self.hand_no = None
        # launched and greeted here, so the gate's import time is the bot's: launch to the hello's reply (kit H: 2 s)
        self.you = "me"  # TODO 2  our handle, the same for the whole process (kit H: in hello and every act)
        self._launch()
        self._ask({"t": "hello", "proto": 1, "you": self.you, "seats": 8, "stack": 2000}, READY_S)

    # ---------------------------------------------------------------- the pipe
    def _launch(self) -> None:
        self.proc = subprocess.Popen([sys.executable, "-u", self.entry], cwd=self.pkg, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, stderr=sys.stderr, bufsize=0, close_fds=True,
                                     env=dict(KIT_ENV))
        self.in_fd, self.out_fd = self.proc.stdin.fileno(), self.proc.stdout.fileno()

    def _ask(self, msg: dict, timeout: float = REPLY_S) -> dict:
        """Write one request (with a fresh id), read lines until the reply that echoes it."""
        mid = self.next_id
        self.next_id += 1
        msg = dict(msg, id=mid)
        data = (json.dumps(msg, separators=(",", ":")) + "\n").encode()
        view = memoryview(data)
        while view:
            view = view[os.write(self.in_fd, view):]
        while True:
            i = self.buf.find(b"\n")
            while i >= 0:
                line, self.buf = self.buf[:i], self.buf[i + 1:]
                try:
                    obj = json.loads(line)
                except ValueError:
                    obj = None  # not a reply (the kit ignores it): keep reading
                if isinstance(obj, dict) and obj.get("id") == mid:
                    return obj
                i = self.buf.find(b"\n")
            r, _, _ = select.select([self.out_fd], [], [], timeout)
            if not r:
                raise TimeoutError(f"no reply to {msg.get('t')} within {timeout:g} s")
            chunk = os.read(self.out_fd, 65536)
            if not chunk:
                raise EOFError("the bot process closed stdout")
            self.buf += chunk

    # ---------------------------------------------------------------- lifecycle
    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n, self.me = n, seat
        self.handles = ["p%d" % i for i in range(n)]  # the kit's handles, clockwise (kit H: short opaque strings)
        self.handles[seat] = self.you
        self.start_stacks = {h: stack for h in self.handles}
        self.hand_start, self.hand_no = {}, None
        self._ask({"t": "table", "table": 1, "seats": self.handles, "button": self.handles[0], "stack": stack,
                   "max_hands": 200})

    def close(self) -> None:
        if self.proc is None:
            return
        try:
            self._ask({"t": "over", "table": 1, "hands": 0, "results": []})
        except Exception:  # noqa: BLE001
            pass
        try:
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self.proc.kill()
        self.proc = None

    # ---------------------------------------------------------------- a decision
    def _log(self, rows, posts, upto, bb) -> str:
        """TODO 3  the kit's log (kit H: streets split by "/", "<handle>:f|k|c|r<raise-by>", no blinds)."""
        out = []
        for s, street in enumerate(by_street(rows, posts, upto)):
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

    def native(self, st: dict) -> dict:
        """TODO 4  the kit's decision request for the gate's dealer state (kit H's act message). Untimed."""
        n = len(st["stacks"])
        stacks, bets, inh = st["stacks"], st["bets"], st["in_hand"]
        total = [0] * n
        for seat, _kind, chips in st.get("posts") or ():
            total[int(seat)] += int(chips)
        for row in st.get("history") or ():
            if len(row) > 4:
                total[int(row[0])] += int(row[4])
        alive = [i for i in range(n) if stacks[i] > 0 or inh[i] or total[i] > 0]
        b = int(st["button"])
        order = sorted(alive, key=lambda i: (i - b - 1) % n)  # small blind first ... the button last
        if len(alive) == 2:
            order = sorted(alive, key=lambda i: (i - b) % n)  # heads-up: the button is the small blind, first
        players = [{"h": self.handles[i], "stack": int(stacks[i]), "bet": int(bets[i]), "total": int(total[i]),
                    "state": ("allin" if stacks[i] == 0 else "live") if inh[i] else "folded"} for i in order]
        seat = int(st["seat"])
        top = int(bets[seat]) + int(st["to_call"])
        min_r = max_r = 0
        if "raise" in st["legal"]:
            min_r, max_r = int(st["min_raise"]) - top, int(st["max_raise"]) - top
        self.bb = int(st["blinds"][1])
        hand = int(st["hand_no"]) + self.HAND_BASE
        if hand != self.hand_no:
            self.hand_no = hand
            self.hand_start = {p["h"]: p["stack"] + p["total"] for p in players}
        return {"t": "act", "table": 1, "hand": hand, "sb": int(st["blinds"][0]), "bb": self.bb,
                "you": self.handles[seat], "button": self.handles[b], "cards": list(st["hole"]),
                "board": list(st["board"]), "pot": int(st["pot"]) + sum(int(x) for x in bets),
                "to_call": int(st["to_call"]), "min_r": min_r, "max_r": max_r, "players": players,
                "log": self._log(st.get("history"), st.get("posts"), int(st["street"]), self.bb)}

    def call(self, native: dict):
        """The timed call: the round trip through the pipe, as the kit's engine-side clock."""
        return self._ask(native).get("a")

    def parse(self, reply, st: dict):
        """TODO 5  the kit's answer -> (kind, raise-to total); anything else raises (the gate counts it illegal)."""
        if not isinstance(reply, str):
            raise ValueError(f"reply {reply!r} is not a string")
        to_call = int(st["to_call"])
        mine = int(st["bets"][int(st["seat"])])
        if reply == "f":
            return ("fold", 0) if to_call > 0 else ("check", 0)
        if reply == "c" or (reply[:1] == "r" and reply[1:].isdigit() and "raise" not in st["legal"]):
            return ("call", mine + to_call) if to_call > 0 else ("check", 0)
        if reply[:1] == "r" and reply[1:].isdigit() and int(reply[1:]) > 0:
            top = mine + to_call
            by = min(max(int(reply[1:]), int(st["min_raise"]) - top), int(st["max_raise"]) - top)
            return "raise", top + by
        raise ValueError(f"bad reply {reply!r}")

    # ---------------------------------------------------------------- the hand end
    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        """TODO 6  the kit's hand end from the gate's result (kit H's end: the board, the whole log, the hands shown,
        everyone's chips after the hand, who went out), sent and its reply read."""
        r = result or {}
        hand = hand_no + self.HAND_BASE
        before = dict(self.start_stacks)
        if self.hand_no == hand and self.hand_start:
            before.update(self.hand_start)
        deltas = list(r.get("deltas") or [0] * self.n)
        stacks, out = {}, []
        for i, h in enumerate(self.handles):
            b0 = before.get(h, 0)
            a = b0 + int(deltas[i]) if i < len(deltas) else b0
            if b0 > 0 or a > 0:
                stacks[h] = a
            if b0 > 0 and a == 0:
                out.append(h)
        self.start_stacks = {h: stacks.get(h, 0) for h in self.handles}
        # the log's preflop raise-by counts from the full big blind: this hand's, from its post when we never decided
        bb = max([self.bb] + [int(c) for _s, k, c in (r.get("posts") or ()) if k == "bb"])
        shown = {self.handles[int(k)]: list(v) for k, v in (r.get("showdown") or {}).items()}
        self._ask({"t": "end", "table": 1, "hand": hand, "board": list(r.get("board") or ()),
                   "log": self._log(r.get("history"), r.get("posts"), None, bb), "shown": shown, "best": {},
                   "won": {}, "stacks": stacks, "out": out})
