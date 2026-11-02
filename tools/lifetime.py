#!/usr/bin/env python
"""Instance lifetime (backlog R2): one ship-bot object through thousands of tables, as a kit that builds one bot per
tournament (or one for the night) would use it. Reports memory, per-decision time by block of tables, and whether the
one object plays every table exactly as a fresh object would.

    .venv/bin/python tools/lifetime.py --tables 10000 --every 500 [--field night] [--mode measure|model]
                                       [--fresh-every 50] [--tracemalloc 500] [--out lifetime.jsonl]

Two ways to run it:
- `--mode measure` (default): the bot exactly as the submission builds it (`hyperion.ship.make_bot()`, wall-clock guards
  and the governor on), the engine timing every call and letting it through. For memory and time creep.
- `--mode model`: the deterministic setup the climb measures with (tools/swap.py setup_process: the composite on top of
  SHIP_DIALS, panic and soft deadlines off). With `--fresh-every K`, every K-th table is also played by a fresh object
  built for that table, and the two must score the same: any state the one object carries from earlier tables that
  changes a decision shows up as a mismatch. The random generators are the one thing a fresh object has and an old one
  cannot: after each new_table the old object's generators are set to the fresh object's states (`transplant_rngs`), so
  a mismatch is state, not luck.
At the end the one object and a fresh one both get new_table and their attribute graphs are compared (`state_diff`):
anything but counters and per-decision scratch that differs is state an earlier table left behind.

The bot sits in Hero's seat of the field at rotation t % 8 of table seed t (tools/swap.py's seating); the other seats
are fresh per table, so whatever grows is the bot's (or a module cache it fills). Every `--every` tables one line: RSS
now and peak (MB), tracemalloc's traced MB from table `--tracemalloc` on (its top growth sites at the end), and our
decisions' p50 / p99 / max microseconds in that block, on the wall clock (what a kit's timer sees: on a busy host it
includes preemption, multiples of the 4 ms scheduler tick) and on the thread's CPU clock (the code's own cost), and
the garbage collections that ran inside our act() (by generation, and their milliseconds). Writes one JSON object per block to --out.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import random
import resource
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
sys.path.insert(0, ROOT)


def rss_mb() -> float:
    """Resident set size now, from /proc (Linux); the peak from getrusage elsewhere."""
    try:
        with open("/proc/self/statm") as f:
            return int(f.read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1e6
    except (OSError, ValueError, IndexError):
        return peak_mb()


def peak_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return r / 1e6 if sys.platform == "darwin" else r / 1e3


def rngs(obj, path: str = "", seen: set | None = None, depth: int = 0) -> dict:
    """Every random.Random reachable from obj's attributes, by attribute path (lists and dicts followed)."""
    seen = set() if seen is None else seen
    out: dict = {}
    if depth > 12 or id(obj) in seen or isinstance(obj, (int, float, str, bytes, bool, type(None), type)):
        return out
    seen.add(id(obj))
    if isinstance(obj, random.Random):
        out[path] = obj
        return out
    if isinstance(obj, dict):
        items = list(obj.items())
    elif isinstance(obj, (list, tuple)):
        items = list(enumerate(obj))
    else:
        names = list(getattr(obj, "__dict__", {}) or {})
        for cls in type(obj).__mro__:
            names += [s for s in getattr(cls, "__slots__", ()) if s not in names]
        items = []
        for k in names:
            try:
                items.append((k, getattr(obj, k)))
            except AttributeError:
                pass
    for k, v in items:
        if callable(v) and not isinstance(v, random.Random) and not hasattr(v, "__dict__"):
            continue
        out.update(rngs(v, f"{path}/{k}", seen, depth + 1))
    return out


def transplant_rngs(old, fresh) -> int:
    """Set every generator of `old` to the state of the generator at the same path in `fresh`; returns how many."""
    mine, theirs = rngs(old), rngs(fresh)
    for p, r in theirs.items():
        if p in mine:
            mine[p].setstate(r.getstate())
    return sum(1 for p in theirs if p in mine)


TELEMETRY = {"counts", "fired", "last", "last_path", "_t0", "_states", "_props", "last_section", "calls", "worst",
             "errors", "overruns", "level_changes", "inferred"}  # counters and per-decision scratch: never read to decide


def state_diff(a, b, path: str = "bot", seen: set | None = None, depth: int = 0, out: list | None = None) -> list:
    """Where two bots' attribute graphs differ (generators and TELEMETRY names skipped): after new_table, an old object
    against a fresh one, so whatever an earlier table left behind shows by its attribute path. [(path, old, fresh)]"""
    import math
    import types

    seen = set() if seen is None else seen
    out = [] if out is None else out
    if depth > 10 or len(out) > 200 or id(a) in seen or isinstance(a, random.Random):
        return out
    if isinstance(a, (types.FunctionType, types.MethodType, types.BuiltinFunctionType, type, types.ModuleType)):
        return out
    if isinstance(a, (int, float, str, bool, type(None), bytes, complex)):
        if a != b and not (isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b)):
            out.append((path, repr(a)[:60], repr(b)[:60]))
        return out
    seen.add(id(a))
    if type(a) is not type(b):
        out.append((path, type(a).__name__, type(b).__name__))
    elif isinstance(a, dict):
        if set(map(repr, a)) != set(map(repr, b)):
            out.append((path, f"{len(a)} keys", f"{len(b)} keys"))
        for k in list(a)[:64]:
            if k in b:
                state_diff(a[k], b[k], f"{path}[{k!r}]", seen, depth + 1, out)
    elif isinstance(a, (list, tuple)):
        if len(a) != len(b):
            out.append((path, f"len {len(a)}", f"len {len(b)}"))
        else:
            for i, (x, y) in enumerate(list(zip(a, b))[:64]):
                state_diff(x, y, f"{path}[{i}]", seen, depth + 1, out)
    elif isinstance(a, (set, frozenset)):
        if a != b:
            out.append((path, f"set of {len(a)}", f"set of {len(b)}"))
    else:
        names = list(getattr(a, "__dict__", {}) or {})
        for cls in type(a).__mro__:
            names += [n for n in getattr(cls, "__slots__", ()) if n not in names]
        for k in names:
            if k in TELEMETRY:
                continue
            try:
                x, y = getattr(a, k), getattr(b, k)
            except AttributeError:
                continue
            state_diff(x, y, f"{path}.{k}", seen, depth + 1, out)
    return out


class GcWatch:
    """gc.callbacks: the collections that run while `inside` is set, by generation, and their time."""

    def __init__(self):
        self.inside = False
        self.n = [0, 0, 0]
        self.ns = 0
        self._t = 0

    def __call__(self, phase, info):
        if not self.inside:
            return
        if phase == "start":
            self._t = time.perf_counter_ns()
        else:
            self.n[info.get("generation", 0)] += 1
            self.ns += time.perf_counter_ns() - self._t


class Timed:
    """The seat: the one object (or a fresh one), our act() timed with perf_counter_ns."""

    def __init__(self, bot, on_new_table=None, gcw: GcWatch | None = None):
        self.bot, self.on_new_table, self.ns, self.cpu, self.gcw = bot, on_new_table, [], [], gcw

    def new_table(self, rules, seat, n):
        self.bot.new_table(rules, seat, n)
        if self.on_new_table is not None:
            self.on_new_table(rules, seat, n)

    def act(self, obs):
        g = self.gcw
        if g is not None:
            g.inside = True
        c0, t0 = time.thread_time_ns(), time.perf_counter_ns()
        a = self.bot.act(obs)
        self.ns.append(time.perf_counter_ns() - t0)
        self.cpu.append(time.thread_time_ns() - c0)
        if g is not None:
            g.inside = False
        return a

    def hand_end(self, result):
        self.bot.hand_end(result)

    def variant_decide(self, prompt):
        return self.bot.variant_decide(prompt)


def pct(xs: list, q: float) -> float:
    if not xs:
        return 0.0
    s = sorted(xs)
    return s[min(len(s) - 1, int(q * len(s)))] / 1e3


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables", type=int, default=10000)
    p.add_argument("--every", type=int, default=500)
    p.add_argument("--field", default="night")
    p.add_argument("--mode", choices=("measure", "model"), default="measure")
    p.add_argument("--fresh-every", type=int, default=0, help="model mode: replay every K-th table with a fresh object")
    p.add_argument("--tracemalloc", type=int, default=-1, help="start tracemalloc at this table (-1: off)")
    p.add_argument("--offset", type=int, default=0, help="first table index")
    p.add_argument("--out", help="JSON lines, one per block")
    a = p.parse_args(argv)
    try:
        return _run(a)
    finally:  # leave the process as it was: tests run this in theirs (the runner lists every registered bot)
        from hyperion.sim import bestiary as B

        gc.callbacks[:] = [c for c in gc.callbacks if not isinstance(c, GcWatch)]
        for k in ("lifetime_one", "lifetime_f"):
            B.REGISTRY.pop(k, None)
        B._BY_CLASS.pop("composite_lifetime_f", None)


def _run(a) -> int:

    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table
    import importlib.util

    spec = importlib.util.spec_from_file_location("_swap", os.path.join(ROOT, "tools", "swap.py"))
    swap = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(swap)

    if a.mode == "model":
        swap.setup_process("model")
        from hyperion.compose import bot as CB

        CB.register("lifetime_f", dials={})  # the composite on SHIP_DIALS (ship() adds light shadows; register too)

        def build(seed):
            return B.make_bot("lifetime_f", seed=seed)
    else:
        from hyperion import ship

        def build(seed):
            return ship.make_bot(seed=seed)

    rules = Rules()
    one = build(12345 if a.mode == "model" else None)
    fresh_for = {}

    def transplant(rules_, seat_, n):  # after the one object's new_table on a checked table: a fresh one's generators
        f = fresh_for.pop("bot", None)
        if f is not None:
            transplant_rngs(one, f)

    gcw = GcWatch()
    gc.callbacks.append(gcw)
    seat = Timed(one, transplant, gcw)
    B.REGISTRY["lifetime_one"] = lambda seed=None: seat
    out = open(a.out, "w") if a.out else None  # noqa: SIM115 - closed at the end
    gc.collect()
    rss0 = rss_mb()
    print(f"start  rss {rss0:.1f} MB  mode {a.mode}  field {a.field}  tables {a.tables}", flush=True)
    t_start = time.perf_counter()
    mism, checked, block_ns, block_cpu, tm0 = [], 0, [], [], None
    worst_all = worst_cpu = 0
    for i in range(a.offset, a.offset + a.tables):
        if i == a.tracemalloc:
            import tracemalloc

            tracemalloc.start(1)
            tm0 = tracemalloc.take_snapshot()
        table_seed, names = swap.seating(f"{a.field}@lifetime_one", i)
        rot = i % 8
        me = names.index("lifetime_one")
        seeds = [table_seed * 64 + rot * 8 + s for s in range(len(names))]
        check = a.mode == "model" and a.fresh_every and i % a.fresh_every == 0
        if check:  # the generator states a fresh object would start this table with
            g = build(seeds[me])
            g.new_table(rules, me, len(names))
            fresh_for["bot"] = g
        bots = [seat if s == me else B.make_bot(nm, seed=seeds[s]) for s, nm in enumerate(names)]
        res = play_table(bots, rules, seed=table_seed, rotation=rot, mode=a.mode)
        if check:
            bots2 = [build(seeds[me]) if s == me else B.make_bot(nm, seed=seeds[s]) for s, nm in enumerate(names)]
            res2 = play_table(bots2, rules, seed=table_seed, rotation=rot, mode=a.mode)
            checked += 1
            if (res.points, res.places, res.hands, res.stacks) != (res2.points, res2.places, res2.hands, res2.stacks):
                mism.append(i)
                print(f"MISMATCH table {i}: one object {res.points[me]} ({res.hands} hands), fresh {res2.points[me]} "
                      f"({res2.hands} hands)", flush=True)
        block_ns.extend(seat.ns)
        block_cpu.extend(seat.cpu)
        seat.ns, seat.cpu = [], []
        if (i - a.offset + 1) % a.every == 0 or i == a.offset + a.tables - 1:
            gc.collect()
            row = {"tables": i - a.offset + 1, "rss_mb": round(rss_mb(), 1), "peak_mb": round(peak_mb(), 1),
                   "decisions": len(block_ns), "p50_us": round(pct(block_ns, 0.5), 1),
                   "p99_us": round(pct(block_ns, 0.99), 1), "max_us": round(max(block_ns, default=0) / 1e3, 1),
                   "mean_us": round(sum(block_ns) / max(1, len(block_ns)) / 1e3, 1),
                   "cpu_p50_us": round(pct(block_cpu, 0.5), 1), "cpu_p99_us": round(pct(block_cpu, 0.99), 1),
                   "cpu_max_us": round(max(block_cpu, default=0) / 1e3, 1),
                   "cpu_mean_us": round(sum(block_cpu) / max(1, len(block_cpu)) / 1e3, 1),
                   "gc_in_act": list(gcw.n), "gc_in_act_ms": round(gcw.ns / 1e6, 1),
                   "secs": round(time.perf_counter() - t_start, 1), "checked": checked, "mismatches": len(mism)}
            gcw.n, gcw.ns = [0, 0, 0], 0
            worst_all = max(worst_all, row["max_us"])
            worst_cpu = max(worst_cpu, row["cpu_max_us"])
            if tm0 is not None:
                import tracemalloc

                row["traced_mb"] = round(tracemalloc.get_traced_memory()[0] / 1e6, 2)
            print(json.dumps(row), flush=True)
            if out:
                out.write(json.dumps(row) + "\n")
                out.flush()
            block_ns, block_cpu = [], []
    caches = []
    for modname, fn in (("hyperion.core.icm", "_cached"), ("hyperion.strategy.hero", "_icm_bucketed")):
        f = getattr(sys.modules.get(modname), fn, None)
        if f is not None and hasattr(f, "cache_info"):
            ci = f.cache_info()
            caches.append(f"{modname}.{fn} {ci.currsize}/{ci.maxsize}")
    print("memo caches (bounded; they fill over the first tables):", ", ".join(caches) or "-")
    if tm0 is not None:
        import tracemalloc

        snap = tracemalloc.take_snapshot()
        print("tracemalloc: top growth since table", a.tracemalloc)
        for st in snap.compare_to(tm0, "lineno")[:12]:
            print("  ", st)
    safe = getattr(one, "safe", None) or getattr(getattr(one, "impl", None), "safe", None)
    last = safe.stats() if safe is not None else None
    g = build(12345 if a.mode == "model" else None)  # the one object after every table, against a fresh one
    one.new_table(rules, 3, 8)
    g.new_table(rules, 3, 8)
    diff = state_diff(one, g)
    print(f"state after new_table that differs from a fresh object's: {len(diff)}"
          + "".join(f"\n  {p}: {x} (fresh {y})" for p, x, y in diff[:20]))
    print(f"done   rss {rss_mb():.1f} MB (start {rss0:.1f}), peak {peak_mb():.1f} MB, worst decision {worst_all:.0f} us wall, {worst_cpu:.0f} us CPU, "
          f"fresh checks {checked}, mismatches {len(mism)} {mism[:10]}"
          + (f", last table's SafeBot {last}" if last is not None else ""), flush=True)
    if out:
        out.close()
    return 1 if mism or diff else 0


if __name__ == "__main__":
    sys.exit(main())
