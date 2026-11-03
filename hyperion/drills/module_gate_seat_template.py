"""Gate seat for a MODULE-FUNCTION kit (the bot is plain module-level functions, one module for a session: drill 11's
kit I): copy to `submission/gate_seat.py`, fill the TODOs, and run `python tools/gate.py dist/submission.zip --kit
submission/gate_seat.py --entry bot.py --tables 100 --rules rules_tonight.json`.

`load_entry(path)` makes tools/gate_host.py load the entry the way the kit's loader does: the package folder on sys.path
for the import only, then off it, and every module from the folder dropped from sys.modules (kit I's handout, section
7). A lazy import in the package then fails here as on the kit; a seat built on gate_host.KitA leaves the folder on
sys.path and never finds it (drill 11's did). Standard library only, so nothing of ours is loaded before the entry.

The kit's Overtime (a BaseException its timer raises inside our code at each limit) is raised here too, with
signal.setitimer at LIMITS_MS: in act() the call ends as the kit's check-or-fold (0; the gate counts it late), in done()
it is counted, in table() the table is sat out (every decision 0, no done()), in start() the session. An Overtime the
bot catches and runs on past (a bare `except:`, `except BaseException:`) is raised to the gate as an error: GATE FAIL.
The counts come back as the gate's `seat counts` note.

Each gate table is one fresh process (the gate imports a package once per table): `start` calls start(session) the
first time and table(info) every table; `native` builds kit I's `v` from the gate's dealer state (seats relative to us,
chips per street, the log in the kit's own shape: the blinds posted, chips added, `!` on an all-in, "/" between streets);
`parse` turns the int into (kind, raise-to total); `end` builds kit I's `h` (`won` = chips collected, each seat's net
change plus what it paid; `u` for chips nobody matched at the end of a street) and calls done(h). The defaults are kit
I's, matching hyperion/drills/module_entry_template.py.
"""
from __future__ import annotations

import importlib.util
import os
import signal
import sys
from types import SimpleNamespace

MODULE_NAME = "bot"  # TODO 0  the name the kit's loader imports the entry under
LIMITS_MS = {"start": 3000, "table": 50, "act": 1, "done": 1}  # TODO 1  the kit's limits; 0 = no Overtime for it
SAFE = 0  # the kit's answer for a cut or sat-out decision (kit I: 0, check or fold)
HAND_BASE = 1  # TODO 2  the kit's first hand number (ours is 0)
HANDS_PER_LEVEL = 25
SCHEDULE = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))  # kit I's
POINTS = (16, 10, 6, 3, 1, 0, -1, -3)  # TODO 3  the kit's session and table fields (kit I's here)
STREETS = 4  # kit I's paid[s] and awards have one entry per street (its tranches)


class Overtime(BaseException):
    """What kit I's timer raises inside the bot at a limit: `except Exception` does not stop it."""


def load_entry(path: str):
    """The kit's loader (TODO 4 if the kit's differs): the entry imported with its folder first on sys.path, then the
    folder off sys.path (every copy of it: gate_host put it there too) and every module loaded from it out of
    sys.modules. The entry module itself is kept by the caller only."""
    folder = os.path.realpath(os.path.dirname(os.path.abspath(path)))
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = [p for p in sys.path if os.path.realpath(p or ".") != folder]
        pre = folder + os.sep
        for name, m in list(sys.modules.items()):
            f = getattr(m, "__file__", None)
            if f and os.path.realpath(f).startswith(pre):
                del sys.modules[name]
    return mod


def by_street(rows, posts=(), upto=None):
    """The gate's tagged rows [seat, kind, total, street, put] and posts [seat, kind, chips] -> one list per street of
    (seat, kind, put), the posts first on street 0 (at least `upto` + 1 lists). As gate_seat_template.by_street."""
    streets = [[(int(s), str(k), int(c)) for s, k, c in posts or ()]]
    for row in rows or ():
        seat, kind, street, put = int(row[0]), str(row[1]), int(row[3]), int(row[4])
        while len(streets) <= street:
            streets.append([])
        streets[street].append((seat, kind, put))
    while upto is not None and len(streets) <= upto:
        streets.append([])
    return streets


CODE = {"sb": "s", "bb": "b", "fold": "f", "check": "k", "call": "c", "raise": "r"}  # TODO 5  the kit's log codes


class Seat:
    def __init__(self, module, kit):
        self.mod, self.kit = module, kit
        self.n, self.me = 8, 0
        self.started = False
        self.out_session = False
        self.out_table = False
        self.stacks: list = []
        self.hole, self.hole_hand = None, None
        self.counts = {"act_overtime": 0, "done_overtime": 0, "table_sat_out": 0, "start_overtime": 0}
        self._armed = self._fired = False
        signal.signal(signal.SIGALRM, self._alarm)

    @property
    def gate_counts(self) -> dict:  # tools/gate_host.py sends them with the table's close; the gate sums them
        return {k: v for k, v in self.counts.items() if v}

    # ---------------------------------------------------------------- the kit's clock
    def _alarm(self, signum, frame) -> None:
        if self._armed:
            self._fired = True
            raise Overtime()

    def _timed(self, which: str, fn, arg):
        """(cut, the call's result): fn(arg) under the kit's limit for `which`, an Overtime raised inside it at the
        limit. A call that caught the Overtime and returned is the bot's error, raised here."""
        ms = LIMITS_MS.get(which) or 0
        if not ms:
            return False, fn(arg)
        self._fired = False
        try:
            self._armed = True
            signal.setitimer(signal.ITIMER_REAL, ms / 1000.0)
            try:
                out = fn(arg)
            finally:
                self._armed = False
                signal.setitimer(signal.ITIMER_REAL, 0)
        except Overtime:
            return True, None
        if self._fired:
            raise RuntimeError(f"{which}() caught the kit's Overtime and ran on (a bare except or except "
                               f"BaseException in the entry or the package)")
        return False, out

    # ---------------------------------------------------------------- lifecycle
    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n, self.me = int(n), int(seat)
        self.stacks = [int(stack)] * self.n
        self.out_table = False
        sched = tuple(tuple(b) for b in SCHEDULE)
        if not self.started:
            self.started = True
            f = getattr(self.mod, "start", None)
            if f is not None:
                cut, _ = self._timed("start", f, SimpleNamespace(
                    data_dir=os.path.dirname(os.path.abspath(self.mod.__file__)), limits_ms=dict(LIMITS_MS),
                    seats=self.n, starting_stack=int(stack), blinds=sched, hands_per_level=HANDS_PER_LEVEL,
                    max_hands=200, points=POINTS, tables=None))
                if cut:
                    self.counts["start_overtime"] += 1
                    self.out_session = True
        f = getattr(self.mod, "table", None)
        if f is not None and not self.out_session:
            cut, _ = self._timed("table", f, SimpleNamespace(
                table=0, seats=self.n, stacks=tuple(self.stacks), button=0, blinds=sched,
                hands_per_level=HANDS_PER_LEVEL, max_hands=200, points=POINTS))
            if cut:
                self.counts["table_sat_out"] += 1
                self.out_table = True

    def _rel(self, xs):
        return tuple(xs[(self.me + r) % self.n] for r in range(self.n))

    # ---------------------------------------------------------------- the kit's state
    def _paid(self, streets) -> list:
        """paid[s][k]: the chips seat s put in on street k (posts and actions)."""
        paid = [[0] * STREETS for _ in range(self.n)]
        for k, street in enumerate(streets):
            for seat, _kind, put in street:
                paid[seat][min(k, STREETS - 1)] += put
        return paid

    def _log(self, streets, start, paid=None) -> str:
        """The kit's log (TODO 5: kit I's shape), seats relative to us, replayed from the chips each seat had at the
        hand's start (`!` when an action leaves it none). With `paid` (the hand end), the top bet's part nobody matched
        at a street's end goes back (`u`) and comes off paid."""
        n = self.n
        left = [int(x) for x in start]
        parts = []
        for k, street in enumerate(streets):
            toks = []
            for seat, kind, put in street:
                c = CODE.get(kind)
                if c is None:  # an ante: dead money, paid but not logged by kit I
                    continue
                left[seat] -= put
                toks.append(f"{(seat - self.me) % n}{c}{put if c in 'sbcr' else ''}{'!' if left[seat] == 0 else ''}")
            if paid is not None:
                kk = min(k, STREETS - 1)
                got = sorted(((paid[s][kk], s) for s in range(n)), reverse=True)
                if got[0][0] > got[1][0]:
                    back, s = got[0][0] - got[1][0], got[0][1]
                    paid[s][kk] -= back
                    toks.append(f"{(s - self.me) % n}u{back}")
            parts.append(" ".join(toks))
        return "/".join(parts)

    def native(self, st: dict):
        n, me = self.n, self.me
        street = int(st["street"])
        stacks = [int(x) for x in st["stacks"]]
        bets = [int(x) for x in st["bets"]]
        inh = list(st["in_hand"])
        streets = by_street(st.get("history") or (), st.get("posts") or (), street)
        paid = self._paid(streets)
        log = self._log(streets, [stacks[s] + sum(paid[s]) for s in range(n)])
        seats = "".join(("p" if stacks[s] > 0 else "a") if inh[s] else
                        ("f" if stacks[s] > 0 or sum(paid[s]) > 0 else "x") for s in range(n))
        to_call = int(st["to_call"])
        mr = 0
        if "raise" in st["legal"] and st.get("min_raise") is not None:
            mr = min(int(st["min_raise"]) - bets[me], stacks[me])
        hand = int(st["hand_no"])
        self.hole, self.hole_hand = tuple(int(c) for c in st["hole"]), hand  # kit I shows us ours at the hand end
        sb, bb = int(st["blinds"][0]), int(st["blinds"][1])
        rel_paid = self._rel([tuple(p) for p in paid])
        return SimpleNamespace(
            hole=self.hole, board=tuple(int(c) for c in st["board"]), street=street, to_call=to_call,
            min_raise=max(0, mr), stack=stacks[me], stacks=self._rel(stacks), seats="".join(self._rel(seats)),
            paid=rel_paid, tranches=tuple(sum(p[k] for p in paid) for k in range(STREETS)),
            button=(int(st["button"]) - me) % n, sb=sb, bb=bb, hand=hand + HAND_BASE,
            level=min(hand // HANDS_PER_LEVEL, len(SCHEDULE) - 1) + 1, log=log)

    def call(self, native):
        if self.out_session or self.out_table:
            return SAFE
        cut, out = self._timed("act", self.mod.act, native)
        if cut:
            self.counts["act_overtime"] += 1
            return SAFE
        return out

    def parse(self, reply, st: dict):
        """TODO 6  the kit's answer -> (kind, raise-to total): kit I's int, the chips to put in now. Anything but an int
        raises (the gate counts it illegal; the kit would play it as 0 and count an error)."""
        if type(reply) is not int:
            raise ValueError(f"not an int: {reply!r}")
        me = int(st["seat"])
        to_call, my_bet, stack = int(st["to_call"]), int(st["bets"][me]), int(st["stacks"][me])
        mr = 0
        if "raise" in st["legal"] and st.get("min_raise") is not None:
            mr = min(int(st["min_raise"]) - my_bet, stack)
        if reply < to_call:
            return ("fold", 0) if to_call > 0 else ("check", 0)
        if mr <= 0 or reply < mr:
            return ("call", my_bet + to_call) if to_call > 0 else ("check", 0)
        return "raise", my_bet + min(reply, stack)

    # ---------------------------------------------------------------- the hand end
    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        """TODO 7  the kit's hand end from the gate's result. Kit I's `won` is chips collected: each seat's net change
        plus what it paid (a kit whose `won` is the net change: the deltas as they are)."""
        r = result or {}
        n, me = self.n, self.me
        deltas = [int(x) for x in (r.get("deltas") or [0] * n)]
        before = list(self.stacks) if self.stacks else [0] * n
        dealt = before[me] > 0
        after = [before[s] + deltas[s] for s in range(n)]
        self.stacks = after
        if not dealt or self.out_session or self.out_table:
            return
        f = getattr(self.mod, "done", None)
        if f is None:
            return
        streets = by_street(r.get("history") or (), r.get("posts") or ())
        paid = self._paid(streets)
        log = self._log(streets, before, paid)  # paid less the uncalled chips from here on
        won = [deltas[s] + sum(paid[s]) for s in range(n)]
        last = min(len(streets), STREETS) - 1
        awards = [[0] * n for _ in range(STREETS)]
        for s in range(n):
            awards[last][s] = won[s]  # our engine has one pot: everything a seat took shows in the last street's
        shown = [None] * n
        for s, h in (r.get("showdown") or {}).items():
            shown[int(s)] = tuple(int(c) for c in h)
        if shown[me] is None and self.hole_hand == hand_no and self.hole is not None:
            shown[me] = self.hole  # kit I always shows us our own
        cut, _ = self._timed("done", f, SimpleNamespace(
            hand=hand_no + HAND_BASE, board=tuple(int(c) for c in (r.get("board") or ())), shown=self._rel(shown),
            paid=self._rel([tuple(p) for p in paid]), awards=tuple(self._rel(a) for a in awards), won=self._rel(won),
            stacks=self._rel(after), log=log))
        if cut:
            self.counts["done_overtime"] += 1
