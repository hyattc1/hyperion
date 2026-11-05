#!/usr/bin/env python
"""Time the zip's own bot, in the conditions the upload may meet: this box flatters us, so loosen nothing and measure.

    python tools/zip_timing.py dist/submission.zip --label b8_load [--k 3] [--hogs N] [--pin CPU] [--scale 1.0]
                               [--json OUT]

Each table is one fresh `python -I -B` (tools/zip_host.py: the zip's package first on sys.path, PYTHONPATH cleared, a
scratch cwd), as the organisers import a bot once per table, with the bot and dials the zip records and every shipped
setting on (the governor, soft deadlines, late_us): nothing here is model mode's DET. Opponents run in this process on
this repo's simulator in the engine's model mode (fixed speed), so they do not depend on the condition; the bot's table is
the same deal whatever it is, and the same for two zips until their decisions differ. Each call is timed alone inside
the bot's process; over 1 ms is a timeout, and the engine then checks or folds for it as strict mode would (tools/slowbox.py's
SlowSeat). No kit adapter is in the call: tools/gate.py's kit paths time that.

Setup per table: import (`hyperion.ship`), construction (`make_bot`), first table (`new_table`), each on the process's
clock, and `wall`, the launch to the first table's end on the real clock (interpreter start included, no bytecode cache,
as a zip freshly extracted with -B).

Conditions:
  --k K        the slow box as batch 2 measured it (tools/slowbox.py): every clock in the bot's process reads K x its thread's
               CPU time, installed before hyperion is imported. Quiet by construction: preemption does not count, the
               governor and the deadlines see the slow clock. Uniform slowness, not a scheduler's stalls.
  --hogs N     N busy processes for the run, this process's niceness: real load. Yours to count against a shared box's
               worker limit, and killed at the end.
  --pin CPU    the bot's process, and the hogs, on one logical CPU: with 2 hogs a real 3x slowdown of its share, in the
               scheduler's slices (a 4 ms stall lands on a decision, so it reads worse than a uniformly slow CPU).
The factor is measured, not assumed: a fixed pure-Python workload runs at each table's start in the bot's process and its
median time is printed, on the bot's clock and on its thread's CPU clock. Compare `work` across conditions.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import random
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_HERE = str(ROOT / "tools")
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

BUDGET_NS = 1_000_000
SEAT = "zip_timing_seat"
# (field, rules file, tables): the rooms where each route runs. One table per fresh process; rotation = table % players.
CELLS = (("night", None, 30), ("elite", None, 20), ("exploit2_hu", "hu", 30), ("exploit2_3", "three", 30))
SEED_OFFSET = 700
_HOG = "import os\nwhile True:\n    pass\n"


def pct(xs: list, q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0.0


class TimedSeat:
    """The zip's bot behind a pipe; reports each act()'s own time as its cost, so the engine's model mode times it out."""

    host = None
    rec: dict = {}

    def __init__(self, seed=None):
        self.seed = seed
        self.last_cost_ns = None
        self.first = True

    def new_table(self, rules, seat, n_players) -> None:
        if self.host is None:
            return
        w0 = time.perf_counter()
        (build, table, _), _ = self.host.call("table", self.seed, rules, seat, n_players)
        self.rec["start_wall"].append(time.perf_counter() - w0)
        self.rec["build"].append(build)
        self.rec["table"].append(table)
        self.first = True

    def act(self, obs):
        a, ns = self.host.call("act", obs)
        self.last_cost_ns = ns
        self.rec["act"].append(ns)
        self.rec["over"] += ns > BUDGET_NS
        if self.first:
            self.rec["first_act"].append(ns)
            self.first = False
        return a

    def hand_end(self, result) -> None:
        self.rec["end"].append(self.host.call("end", result)[1])

    def variant_decide(self, prompt):
        return self.host.call("variant", prompt)[0]


def summary(rec: dict) -> dict:
    act = sorted(rec["act"])
    end = sorted(rec["end"])
    us = lambda v: round(v / 1000.0, 1)  # noqa: E731
    return {"decisions": len(act), "p50_us": us(pct(act, 0.5)), "p99_us": us(pct(act, 0.99)), "p999_us": us(pct(act, 0.999)),
            "max_us": us(act[-1] if act else 0), "timeouts": rec["over"],
            "timeout_pct": round(100.0 * rec["over"] / max(1, len(act)), 4), "over_800us": sum(1 for x in act if x > 800_000),
            "first_act_p50_us": us(pct(sorted(rec["first_act"]), 0.5)), "first_act_max_us": us(max(rec["first_act"], default=0)),
            "hand_end_p99_us": us(pct(end, 0.99)), "hand_end_max_us": us(end[-1] if end else 0),
            "panic_tables": rec["panic"], "level_tables": rec["level"], "tables": rec["tables"]}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("zip")
    p.add_argument("--label", default="run")
    p.add_argument("--k", type=float, default=1.0)
    p.add_argument("--hogs", type=int, default=0)
    p.add_argument("--pin", type=int, default=None)
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--json")
    a = p.parse_args(argv)

    spec = importlib.util.spec_from_file_location("zip_parity", ROOT / "tools" / "zip_parity.py")
    ZP = importlib.util.module_from_spec(spec)
    sys.modules["zip_parity"] = ZP
    spec.loader.exec_module(ZP)
    SW = ZP.load_tool("swap")

    SW.setup_process("model")
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import BotStats, play_table

    B.REGISTRY[SEAT] = TimedSeat
    extra = ("--k", str(a.k)) if a.k != 1.0 else ()
    hogs = []
    env = ZP.clean_env()
    preexec = None
    if a.pin is not None:
        cpu = a.pin

        def preexec():  # noqa: F811
            os.sched_setaffinity(0, {cpu})
    for _ in range(a.hogs):
        hogs.append(subprocess.Popen([sys.executable, "-I", "-c", _HOG], env=env, preexec_fn=preexec))
    src = Path(a.zip).resolve()
    res: dict = {"label": a.label, "zip": str(src), "k": a.k, "hogs": a.hogs, "pin": a.pin, "cells": {}}
    setup = {"import": [], "build": [], "table": [], "total": [], "wall": []}
    work_clock, work_cpu = [], []
    all_rec = {"act": [], "end": [], "over": 0, "first_act": [], "build": [], "table": [], "panic": 0, "level": 0, "tables": 0}
    loads = []
    t00 = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="zip_timing_") as tmp:
            pkg = Path(tmp) / "package"
            pkg.mkdir()
            with zipfile.ZipFile(src) as zf:
                zf.extractall(pkg)
            cwd = Path(tmp) / "cwd"
            cwd.mkdir()
            static = ZP.probe_zip(pkg, str(cwd))
            bot, dials = static["bot"], static["dials"]
            res["bot"] = bot
            print(f"{a.label}: {src.name} bot {bot}, k {a.k}, hogs {a.hogs}, pin {a.pin}", flush=True)
            for field, rules_name, n in CELLS:
                rules = ZP._rules_of(rules_name) or Rules()
                names = [nm.strip().lower() for nm in B.field_names(f"{field}@{SEAT}") if nm.strip()]
                rec = {"act": [], "end": [], "over": 0, "first_act": [], "build": [], "table": [], "panic": 0, "level": 0,
                       "tables": 0, "start_wall": []}
                TimedSeat.rec = rec
                for t in range(SEED_OFFSET, SEED_OFFSET + max(1, round(n * a.scale))):
                    table_seed = SW.SEED * 1_000_003 + t
                    rng = random.Random(table_seed)
                    seats = list(names[:rules.n_players])
                    while len(seats) < rules.n_players:
                        seats.append(rng.choice(names))
                    rng.shuffle(seats)
                    rot = t % rules.n_players
                    w0 = time.perf_counter()
                    host = ZP.Host(pkg, bot, dials, str(cwd), extra, preexec=preexec)
                    launch = time.perf_counter() - w0  # the real clock to the hello: the interpreter and `import ship`
                    TimedSeat.host = host
                    try:
                        if not Path(host.hello["hyperion"]).resolve().is_relative_to(pkg.resolve()):
                            raise SystemExit(f"FAIL the bot imported {host.hello['hyperion']}, outside the zip")
                        clock, cpu_ns = host.call("work")[0]
                        work_clock.append(clock)
                        work_cpu.append(cpu_ns)
                        bots = [B.make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seats)]
                        stats = [BotStats(nm) for nm in seats]
                        me = seats.index(SEAT)
                        marks = len(rec["table"])
                        play_table(bots, rules, seed=table_seed, rotation=rot, mode="model", stats=stats)
                        if len(rec["table"]) > marks:
                            setup["import"].append(host.hello["import_ns"])
                            setup["build"].append(rec["build"][-1])
                            setup["table"].append(rec["table"][-1])
                            setup["total"].append(host.hello["import_ns"] + rec["build"][-1] + rec["table"][-1])
                            setup["wall"].append(launch + rec["start_wall"][-1])  # real clock, no play, no workload
                        st = host.call("state")[0]
                        rec["panic"] += st["panic"]
                        rec["level"] += st["level"] > 0
                        rec["tables"] += 1
                        if stats[me].exceptions:
                            res.setdefault("errors", []).append(f"{field} table {t}: {stats[me].last_error}")
                        loads.append(os.getloadavg()[0])
                    finally:
                        host.close()
                res["cells"][field] = summary(rec)
                for k in ("act", "end", "first_act", "build", "table"):
                    all_rec[k].extend(rec[k])
                for k in ("over", "panic", "level", "tables"):
                    all_rec[k] += rec[k]
                c = res["cells"][field]
                print(f"  {field:<14} n {c['decisions']:>6}  p50 {c['p50_us']:>7}  p99 {c['p99_us']:>8}  max {c['max_us']:>9}  "
                      f"tmo {c['timeouts']:>4} ({c['timeout_pct']}%)  panic {c['panic_tables']}/{c['tables']}", flush=True)
    finally:
        for h in hogs:
            h.kill()
        for h in hogs:
            h.wait(timeout=5)
    res["all"] = summary(all_rec)
    ms = lambda ns: round(ns / 1e6, 1)  # noqa: E731
    res["setup_ms"] = {}
    for k, v in setup.items():
        v = sorted(v)
        f = (lambda x: round(x * 1000, 1)) if k == "wall" else ms
        res["setup_ms"][k] = {"p50": f(pct(v, 0.5)), "max": f(v[-1] if v else 0), "n": len(v)}
    res["work_clock_ms"] = ms(pct(sorted(work_clock), 0.5))
    res["work_cpu_ms"] = ms(pct(sorted(work_cpu), 0.5))
    res["load"] = [round(min(loads), 1), round(max(loads), 1)] if loads else []
    res["secs"] = round(time.perf_counter() - t00, 1)
    c = res["all"]
    s = res["setup_ms"]
    print(f"  {'all':<14} n {c['decisions']:>6}  p50 {c['p50_us']:>7}  p99 {c['p99_us']:>8}  max {c['max_us']:>9}  "
          f"tmo {c['timeouts']:>4} ({c['timeout_pct']}%)  panic {c['panic_tables']}/{c['tables']}")
    print(f"  setup ms (import + build + first table) p50 {s['total']['p50']} max {s['total']['max']}; import p50 "
          f"{s['import']['p50']}, build {s['build']['p50']}, table {s['table']['p50']}; launch to table wall p50 "
          f"{s['wall']['p50']} max {s['wall']['max']}")
    print(f"  workload {res['work_clock_ms']} ms on the bot's clock, {res['work_cpu_ms']} ms of CPU; load {res['load']}; "
          f"{res['secs']} s")
    for e in res.get("errors", [])[:3]:
        print(f"  ERROR {e}")
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
