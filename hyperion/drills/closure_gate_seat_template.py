"""Gate seat for a CLOSURE kit (one module function returning the decide closure for a table, recaps inside the timed decide:
drill 12's kit J): copy to `submission/gate_seat.py`, fill the TODOs, and run `python tools/gate.py dist/submission.zip --kit
submission/gate_seat.py --entry bot.py --tables 100 --rules rules_tonight.json --setup-budget-ms <the kit's limit>`.

`load_entry(path)` makes tools/gate_host.py load the entry the way the kit's loader does (the folder on sys.path for the
import only, every module from it out of sys.modules after). Standard library only, so nothing of ours is loaded before the
entry. `native` builds the kit's `v` from the gate's dealer state, the recaps of the hands finished since the last decision
inside it, as the kit delivers them; `parse` turns the answer into (kind, raise-to total); `end` queues the recap. The
defaults are kit J's, matching hyperion/drills/closure_entry_template.py.

The kit's clock, as the handout has it (TODO 1): the gate times the call against 1 ms and counts it late. A sit_down over its
limit plays the table on the kit's autopilot (`table_sat_out`). Past the hard stops a BaseException is raised inside the
call with signal.setitimer (`decide_hard_stop`, `sit_down_hard_stop`); an entry that catches it and runs on is raised to the
gate as an error: GATE FAIL. The counts come back as the gate's `seat counts` note.

A TWIST THE ENGINE ONLY PLAYS WITH --variant. The state this seat invents for the twist (kit J: peaks and stops) means
something only when the dealer plays the twist too. tools/gate.py sets GATE_VARIANT in this process's environment to what
`--variant` names, and without it this seat reports no stop for anyone: otherwise a patch in the adapter fires on the seat's
floors with no stop in the engine, shoves at nothing, and the gate's number says nothing (drill 12). So a function patch
needs `--variant`: a hooks file (docs/drills/drill12/tonight.py) or a catalog entry; the gate warns when the adapter carries
a patch and none is given.
"""
from __future__ import annotations

import importlib.util
import os
import signal
import sys
import time
from collections import namedtuple

MODULE_NAME = "_bot_0"  # TODO 0  the name the kit's loader imports the entry under
LIMITS_MS = {"sit_down": 25.0}  # TODO 1  the kit's soft limit on the table start: over it, the table is on autopilot
HARD_MS = {"sit_down": 500, "decide": 50}  # the kit's hard stops; 0 = none
# TODO 2  the kit's table fields, in its field order (the entry reads what it needs by name)
SCHEDULE = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
POINTS = (14, 9, 6, 4, 3, 2, 1, 0)
HANDS_PER_LEVEL = 25
TAGS = ("qx", "mv", "tk", "ab", "cd", "ef", "gh", "ij")  # kit J's are random per table; one fixed set is enough here
View = namedtuple("View", "hand level bb next_level_in street hole board pot owe min_raise max_raise me button players log recap")
Player = namedtuple("Player", "tag stack peak floor bet in_pot state")
Recap = namedtuple("Recap", "hand bb log board shown net out dividend")
TableInfo = namedtuple("TableInfo", "me tags start_chips blinds hands_per_level hand_cap stop_fraction points "
                                    "decision_limit_ms setup_limit_ms seed")


class HardStop(BaseException):
    """What the kit's watchdog raises inside the bot past a hard stop: `except Exception` does not stop it."""


def load_entry(path: str):
    """The kit's loader (TODO 3 if the kit's differs): the folder first on sys.path for the import, then off it, every copy
    (gate_host put it there too), and every module loaded from it out of sys.modules."""
    folder = os.path.realpath(os.path.dirname(os.path.abspath(path)))
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[MODULE_NAME] = mod
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


def mask(cards) -> int:
    """Ours rank * 4 + suit -> kit J's bit mask, bit = 13 * suit + rank - 2 (TODO 4 another kit's encoding)."""
    m = 0
    for c in cards:
        m |= 1 << (13 * (int(c) % 4) + int(c) // 4)
    return m


def stop_of(peak: int) -> int:
    """TODO 5  the twist's public state: kit J's stop, 60% of the peak rounded up."""
    return -(-peak * 3 // 5)


def g(x: float) -> str:
    return "%g" % x


class Seat:
    def __init__(self, module, kit):
        self.mod = module
        self.decide = None
        self.pending: list = []
        self.twist = bool(os.environ.get("GATE_VARIANT"))  # the module doc: the engine plays the twist only with --variant
        self.counts = {"table_sat_out": 0, "decide_hard_stop": 0, "sit_down_hard_stop": 0}
        self._armed = self._fired = False
        signal.signal(signal.SIGALRM, self._alarm)

    @property
    def gate_counts(self) -> dict:  # tools/gate_host.py sends them with the table's close; the gate sums them
        return {k: v for k, v in self.counts.items() if v}

    # ---------------------------------------------------------------- the kit's clock
    def _alarm(self, signum, frame) -> None:
        if self._armed:
            self._fired = True
            raise HardStop()

    def _timed(self, which: str, fn, arg):
        """(cut, the call's result): fn(arg) under the kit's hard stop. A call that caught it and returned is an error."""
        ms = HARD_MS.get(which) or 0
        self._fired = False
        try:
            self._armed = True
            if ms:
                signal.setitimer(signal.ITIMER_REAL, ms / 1000.0)
            try:
                out = fn(arg)
            finally:
                self._armed = False
                signal.setitimer(signal.ITIMER_REAL, 0)
        except HardStop:
            self.counts[which + "_hard_stop"] += 1
            return True, None
        if self._fired:
            raise RuntimeError(f"{which}() caught the kit's hard stop and ran on (a bare except or except BaseException "
                               f"in the entry or the package)")
        return False, out

    # ---------------------------------------------------------------- lifecycle
    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n, self.me = int(n), int(seat)
        self.stacks = [int(stack)] * self.n
        self.peaks = [int(stack)] * self.n
        self.floors = [stop_of(int(stack)) if self.twist else 0] * self.n
        self.pending = []
        info = TableInfo(TAGS[self.me], TAGS[:self.n], int(stack), SCHEDULE, HANDS_PER_LEVEL, 200, 0.6, POINTS, 1.0,
                         LIMITS_MS["sit_down"], 12345)
        t0 = time.perf_counter()
        cut, fn = self._timed("sit_down", self.mod.sit_down, info)
        over = (time.perf_counter() - t0) * 1e3 > LIMITS_MS["sit_down"]
        self.decide = None if cut or over or not callable(fn) else fn  # the kit's autopilot for the whole table
        if self.decide is None:
            self.counts["table_sat_out"] += 1

    # ---------------------------------------------------------------- the kit's state
    def _log(self, rows, posts, bb, upto=None) -> str:
        """The kit's log (TODO 6: kit J's shape): tag, verb, amount; "/" per street; R's amount the raise-by on the price."""
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
        for s, _kind, chips in st.get("posts") or ():
            paid[int(s)] += int(chips)
        for row in st.get("history") or ():
            paid[int(row[0])] += int(row[4])
        live = [s for s in range(n) if self.stacks[s] > 0]
        btn = int(st["button"])
        i = live.index(btn) if btn in live else 0
        m = len(live)
        # clockwise from the small blind; heads-up the button posts it
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
        return View(hand + 1, min(hand // HANDS_PER_LEVEL, len(SCHEDULE) - 1) + 1, bb,
                    HANDS_PER_LEVEL - hand % HANDS_PER_LEVEL, street, mask(st["hole"]), mask(st["board"]),
                    (int(st["pot"]) + sum(bets)) / bb, to_call / bb, lo, hi, order.index(me),
                    order.index(btn) if btn in order else 0, players, self._log(st.get("history"), st.get("posts"), bb, street),
                    recap)

    def call(self, native):
        if self.decide is None:
            return "c" if native.owe <= 0 else "f"  # the kit's autopilot
        cut, out = self._timed("decide", self.decide, native)
        if cut:
            return "c" if native.owe <= 0 else "f"
        return out

    def parse(self, reply, st: dict):
        """TODO 7  the kit's answer -> (kind, raise-to total). Kit J: "f", "c", "r<x>", x big blinds on top of the call,
        clamped to the bounds; anything else raises (the gate counts it illegal; the kit plays it as check or fold)."""
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

    # ---------------------------------------------------------------- the hand end
    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        """TODO 8  the kit's recap from the gate's result. won: chips collected or net change? Kit J's `net` is the net change
        in big blinds (a kit whose `won` is chips collected: each seat's net change plus what it paid). The recap waits for the
        next decide, as the kit delivers it: nothing is timed here."""
        r = result or {}
        n = self.n
        deltas = [int(x) for x in (r.get("deltas") or [0] * n)]
        before = list(self.stacks)
        bb = SCHEDULE[min(int(hand_no) // HANDS_PER_LEVEL, len(SCHEDULE) - 1)][1]
        after = [before[s] + deltas[s] for s in range(n)]
        self.stacks = after
        if self.twist:
            for s in range(n):
                if after[s] > self.peaks[s]:
                    self.peaks[s] = after[s]
                    self.floors[s] = stop_of(after[s])
        if before[self.me] <= 0:
            return
        shown = tuple((TAGS[int(s)], mask(h)) for s, h in (r.get("showdown") or {}).items())
        net = tuple((TAGS[s], deltas[s] / bb) for s in range(n) if before[s] > 0)
        out = tuple(TAGS[s] for s in range(n) if before[s] > 0 and after[s] <= 0)
        self.pending.append(Recap(int(hand_no) + 1, bb, self._log(r.get("history"), r.get("posts"), bb),
                                  mask(r.get("board") or ()), shown, net, out, 0.0))
