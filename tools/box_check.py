#!/usr/bin/env python3
"""Which box is the bot on? One line for the night's run sheet, standard library only, 3 seconds:

    python3 tools/box_check.py

Run it where the bot runs: in the organisers' sandbox if anything lets you (a printed line at the entry's import, the kit's
own runner's log), else it describes only the machine you ran it on, and says nothing about the sandbox.

  speed   a fixed pure-Python workload's CPU time against this repo's box (6.2 ms there; an older Python reads a little slower): the k of
          docs/drills/climb/g1-log.md's tables. CPU time, so a busy machine barely moves it.
  share   this thread's CPU time over the wall clock while it spins, and the stalls: gaps over 1 ms in a loop that never sleeps.

The verdict says what each case means for the bot (G1): the governor reads CPU time, so it steps down on a slow CPU and, by design,
not on a share of one.
"""
from __future__ import annotations

import time

REF_MS = 6.2  # this file's workload (warm, the median of five) on the box the tables were measured on, CPython 3.12, load 6
SLOW = 1.5  # where the governor starts to matter: the first rung holds from about 1.6x
SHARE = 0.85  # CPU over wall under this, spinning, is someone else's time
STALLS_PER_S = 5.0  # gaps over 1 ms a second; a loaded box shows a few


def workload() -> int:
    t = 0
    for i in range(200_000):
        t = (t * 31 + i) & 0xFFFF
    return t


def measure(seconds: float = 2.0) -> dict:
    works = []
    for _ in range(5):
        c0 = time.thread_time()
        workload()
        works.append(time.thread_time() - c0)
    w0, c0 = time.perf_counter(), time.thread_time()
    last, stalls, worst = w0, 0, 0.0
    while True:
        now = time.perf_counter()
        gap = now - last
        last = now
        if gap > 0.001:
            stalls += 1
        if gap > worst:
            worst = gap
        if now - w0 > seconds:
            break
    wall = last - w0
    return {"work_ms": sorted(works)[len(works) // 2] * 1000.0, "share": (time.thread_time() - c0) / wall,
            "stalls_per_s": stalls / wall, "worst_ms": worst * 1000.0}


def verdict(m: dict) -> str:
    k = m["work_ms"] / REF_MS
    if m["share"] < SHARE or m["stalls_per_s"] > STALLS_PER_S:
        return ("CPU SHARE: this process gets a slice of a CPU, in stalls. The governor will not step down (a stall is not slow code) and no bot "
                "code answers a stall: ship as is, no `timeouts` recipe. A bot that sleeps between calls barely notices; one under a runner that "
                "never sleeps loses about 3% of its decisions, whichever bot (docs/drills/climb/b8-timing.md, c2 and c3).")
    if k >= SLOW:
        return (f"SLOW CPU, about {k:.1f}x: the case the governor is for. Ship as is; expect the gate's governor line at `--slow {k:.1f}` to show level 1, "
                f"and read timeouts there (docs/drills/climb/g1-log.md).")
    return "NORMAL: at this speed the governor never fires, and the gate's governor line must read level_max 0."


def main() -> int:
    m = measure()
    print(f"box: workload {m['work_ms']:.1f} ms (about {m['work_ms'] / REF_MS:.1f}x), CPU/wall {m['share']:.2f}, "
          f"{m['stalls_per_s']:.1f} stalls/s, worst {m['worst_ms']:.1f} ms -> {verdict(m)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
