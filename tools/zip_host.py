#!/usr/bin/env python
"""Child side of tools/zip_parity.py and tools/zip_timing.py: one bot, built from one tree, in a process of its own.

    python -I -B tools/zip_host.py <root> <bot> <dials JSON> [--k K] [--spin 1]

Standard library and <root> only, and it never imports this repo unless <root> is this repo: started with -I, PYTHONPATH
cleared and a scratch working directory, <root> first on sys.path, so `import hyperion` resolves to <root>'s package (the
hello reports the file, and the parent checks it). Frames are 4-byte little-endian lengths and pickles, on stdin and on
the saved stdout; the bot's own prints go to stderr. The classes in the frames (Observation, HandResult, Rules, Action)
are the tree's own: hyperion.core.types is in every package.

With --k the clocks read k times this thread's CPU time from the start of the process, before hyperion is imported, so
every binding of perf_counter sees them, and the bot's own deadlines, the governor and the timers here are all on the
slow box's clock: batch 2's method, tools/slowbox.py's install with --clock cpu, written out here because that module
brings this repo's hyperion with it.

With --spin the process spins on its stdin between calls instead of sleeping in the read, as a bot does whose runner plays
every seat in one process: it never sleeps, so the scheduler gives it no sleeper's wake-up priority and a busy CPU preempts it
mid-decision.

Requests: ("table", seed, rules, seat, n) builds a bot and starts its table; ("act", obs); ("end", result);
("variant", prompt); ("state",) the routes it carries, its counters and the table files opened so far; ("work",) times
the fixed workload; ("bye",). Replies are (value, ns), ns the call's own time on this process's clock.
"""
from __future__ import annotations

import json
import os
import pickle
import struct
import sys
import time

# a fixed pure-Python workload: the factor between two conditions is the ratio of its times
def workload() -> int:
    t = 0
    for i in range(200_000):
        t = (t * 31 + i) & 0xFFFF
    return t


def dilate(k: float) -> None:
    src = time.thread_time_ns
    s0, p0, pn0 = src(), time.perf_counter(), time.perf_counter_ns()
    m0, mn0 = time.monotonic(), time.monotonic_ns()
    time.perf_counter = lambda: p0 + (src() - s0) * k * 1e-9
    time.perf_counter_ns = lambda: pn0 + int((src() - s0) * k)
    time.monotonic = lambda: m0 + (src() - s0) * k * 1e-9
    time.monotonic_ns = lambda: mn0 + int((src() - s0) * k)


def main(argv: list[str]) -> int:
    root, name, dials = os.path.abspath(argv[0]), argv[1], json.loads(argv[2])
    opts = dict(zip(argv[3::2], argv[4::2]))
    inp, out = sys.stdin.buffer, os.fdopen(os.dup(1), "wb")
    os.dup2(2, 1)

    def send(obj) -> None:
        data = pickle.dumps(obj, protocol=4)
        out.write(struct.pack("<I", len(data)) + data)
        out.flush()

    def recv():
        head = inp.read(4)
        if len(head) < 4:
            return None
        n = struct.unpack("<I", head)[0]
        return pickle.loads(inp.read(n))

    if opts.get("--spin"):
        os.set_blocking(0, False)
        buf = bytearray()

        def read_exact(n: int) -> bytes:
            while len(buf) < n:
                try:
                    got = os.read(0, 1 << 16)
                except BlockingIOError:
                    continue
                if not got:
                    raise EOFError
                buf.extend(got)
            out_ = bytes(buf[:n])
            del buf[:n]
            return out_

        def recv():  # noqa: F811
            try:
                return pickle.loads(read_exact(struct.unpack("<I", read_exact(4))[0]))
            except EOFError:
                return None

    k = float(opts.get("--k", 1.0))
    if k != 1.0:  # first: every later `from time import perf_counter` binds the slow box's clock
        dilate(k)

    tables = os.path.join(root, "tables") + os.sep
    opened: set = set()

    def hook(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.path.abspath(os.fsdecode(args[0]))
            if p.startswith(tables):
                opened.add(p[len(tables):].replace(os.sep, "/"))

    sys.addaudithook(hook)
    pc = time.perf_counter_ns
    sys.path.insert(0, root)
    t0 = pc()
    from hyperion import ship

    t_import = pc() - t0
    bot = None
    first = True
    hello = {"hyperion": sys.modules["hyperion"].__file__, "ship": ship.SHIP, "ship_dials": ship.DIALS,
             "import_ns": t_import, "k": k}
    send(("hello", hello))
    while True:
        msg = recv()
        if msg is None or msg[0] == "bye":
            return 0
        kind = msg[0]
        if kind == "act":
            t0 = pc()
            a = bot.act(msg[1])
            dt = pc() - t0
            send((a, dt))
        elif kind == "end":
            t0 = pc()
            bot.hand_end(msg[1])
            dt = pc() - t0
            send((None, dt))
        elif kind == "variant":
            t0 = pc()
            a = bot.variant_decide(msg[1])
            dt = pc() - t0
            send((a, dt))
        elif kind == "table":
            _, seed, rules, seat, n = msg
            t0 = pc()
            bot = ship.make_bot(name, dials, seed)
            t1 = pc()
            bot.new_table(rules, seat, n)
            t2 = pc()
            send(((t1 - t0, t2 - t1, first), 0))
            first = False
        elif kind == "state":
            send((state(bot, sorted(opened)), 0))
        elif kind == "work":
            r0 = time.thread_time_ns()
            t0 = pc()
            workload()
            send(((pc() - t0, time.thread_time_ns() - r0), 0))
        else:
            raise SystemExit(f"zip_host: unknown request {kind!r}")


def state(bot, opened: list) -> dict:
    """What fired so far on this bot, by counters: {"strong": n, "hu": n, "3b": n, "short": n}, and the routes it carries:
    a run proves nothing about a route that never fired, so the parent needs both."""
    core = getattr(bot, "core", None)
    counts = dict(getattr(core, "counts", {}) or {})
    out = {"opened": opened, "routes": [], "strong": int(counts.get("strong", 0)), "short": int(counts.get("short", 0)),
           "hu": 0, "3b": 0, "counts": {k: v for k, v in counts.items() if isinstance(v, int)}}
    safe = getattr(bot, "safe", None)
    out["panic"] = bool(getattr(safe, "panic_mode", False))
    out["level"] = int(getattr(safe, "degrade_level", 0) or 0)
    if core is None:
        return out
    if getattr(core, "strong", None) is not None:
        out["routes"].append("strong")
    names = list(getattr(core, "names", ()))
    if "short" in names and getattr(core, "short", None) is not None:
        short = core.members[names.index("short")]
        out["routes"].append("hu")
        out["hu"] = sum(v for k, v in short.counts.items() if k.startswith("hu:"))
        if getattr(short.p, "three2", False):
            out["routes"].append("3b")  # asked for by its dials, whether or not the table loaded
        out["3b"] = sum(v for k, v in short.counts.items() if k.startswith("3b:"))
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
