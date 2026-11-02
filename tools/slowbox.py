#!/usr/bin/env python
"""Slow-box harness (backlog R1): play a bot as it would play on a k-times slower machine, or on a noisy shared host.

    .venv/bin/python tools/slowbox.py run --specs SPECS.json --field night --seeds 10000:10200 --k 2 --out DIR
                                          [--payouts lin|brief|th] [--scope seat|all] [--workers 2] [--tag T]
                                          [--clock cpu|wall] [--noise RATE,MEAN_US] [--trace-us 250] [--det]
                                          [--contend N --duty-ms ON,OFF --cpus 6,7 --clock wall]
    .venv/bin/python tools/slowbox.py table DIR/a.json DIR/b.json ... [--ref DIR/ref.json]
    .venv/bin/python tools/slowbox.py trace DIR/a.json [--by section,member,street,...]

SPECS.json is {name: {"bot": "composite" | "hybrid3_x" | "hero" | any hyperion/ship.py BUILDERS name, "dials": {...}}}
(a bare name, e.g. "composite", is that bot with no dials). Each spec is built with hyperion.ship.make_bot(bot, dials,
seed): the shipped settings (SafeBot panic, soft deadlines, the composite's late_us), not the model-mode ones, unless
--det. The candidate sits in Hero's seat of `<field>@<bot>` with the seats, seeds and duplicate deals of run_tournament
and tools/swap.py (SEED 7, table seed 7 * 1000003 + t, bot seed table_seed * 64 + rotation * 8 + seat), so every run
here pairs seed for seed with any other run here and with a swap.py `paired` run on the same seeds.

**The dilated clock (`--k`).** `install(k, basis)` replaces time.perf_counter, perf_counter_ns, monotonic and
monotonic_ns with clocks that read k times the elapsed time from the moment of install, and rebinds every module global
in an imported `hyperion.*` module that holds one of them (the `from time import perf_counter` bindings, made at import,
in sim/engine.py, strategy/safe.py, compose/bot.py, hybrid/bot.py, hybrid/core3.py, hybrid/core.py), so the order of
imports does not matter. Every interval then reads k times its length: the engine's 1 ms check, SafeBot's 0.5 ms soft
deadline and its panic count, the hybrids' 350 us soft deadline, the composite's late_us, and the wall-clock samplers
of opponents that read `time.perf_counter` at call time. That is what a box whose CPU is uniformly k times slower
shows: the same code, every decision k times as long, every deadline in real seconds.
`--clock cpu` (the default) counts this thread's CPU time (CLOCK_THREAD_CPUTIME_ID, ~0.1 us a read, ns resolution):
a *quiet* k-times slower box, immune to whatever else this host runs (other agents' jobs preempting us show up in the
wall clock, not in our CPU time; cache and hyperthread contention still do). `--clock wall` dilates real elapsed time,
preemptions included (k-fold: overstated). What neither models: memory-bound work may slow less than CPU-bound work on
a real box, and a clock read costs ~0.2 us here against ~0.03 us for the builtin (about 10 reads a decision, so a bias
of ~2 us x k in the box's time, under 1% of the budget).
`--noise RATE,MEAN_US` adds virtual preemptions on top: a Poisson process of RATE pauses per second of the box's time,
each an exponential pause of mean MEAN_US, seeded per table (a shared host's noise without busy processes, so it is
reproducible and does not depend on this host's load).

**Scope.** `--scope seat` (the default): the engine runs in mode "model" (no seat is folded on the wall clock; the
bestiary's cost-model bots are folded by their modelled cost; the wall-clock opponents play at their fixed speed) and
the candidate sits behind `SlowSeat`, which reports its own dilated time as `last_cost_ns`, so the engine folds or
checks it over 1 ms exactly as strict mode would. Opponents then play exactly as in a model-mode run whatever k is, so
a change in points between two k is the candidate's own timing cost, and a --det run pairs exactly with swap.py's
model-mode `paired`. `--scope all`: the engine is strict for every seat on the dilated clock, opponents slowed too
(the whole room on the slow box; their own timeouts move as well).

**Contention (`--contend N`).** A noisy shared host: each worker is pinned to one core of `--cpus` with N busy
processes pinned to the same core, each alternating busy and sleeping phases of exponential length with the means in
`--duty-ms ON,OFF` (default 5,5: each busy process wants half the core; OFF 0: always busy). Real CPU contention on
the real clock (k = 1 unless --k says otherwise): our decisions are preempted mid-call by the scheduler, the cost no
bot code can avoid by being cheap. Needs `--clock wall` (preemption is not CPU time). Busy processes are killed when
the run ends.

**Records.** Per (table seed, rotation): points, place, timeouts (the engine's over-budget count for the seat), calls,
SafeBot overruns, whether and when (hand, call) the table entered panic, the slowest call, and the deepest degradation
level reached when the bot exposes one (`degrade_level` on its SafeBot). Per job: the seat's latency histogram as the
box sees it (dilated us), load average at start and end. `--trace-us X`: every decision that used more than X us of
CPU time (real, undilated) is
recorded with its section, the member and route counters it moved, street, players in the hand and alive, whether it
was the hand's first decision, garbage collections during it, and panic state; `trace` aggregates them.

`table` prints points ± 95%, the paired difference against --ref (default: the first file) on the seeds both hold,
timeouts per table, tables with a timeout, tables that entered panic, p50 / p99 / max as the box sees them, and load.
"""
from __future__ import annotations

import argparse
import gc
import json
import math
import os
import random
import subprocess
import sys
import time
from collections import Counter
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ---------------------------------------------------------------------------------------------- the dilated clock
CLOCKS = ("perf_counter", "perf_counter_ns", "monotonic", "monotonic_ns")
_REAL = {name: getattr(time, name) for name in CLOCKS}
_STATE: dict = {"k": 1.0, "basis": "wall", "noise": None, "fns": dict(_REAL)}
# virtual preemptions (--noise): a Poisson process on the box's clock; reseed_noise() restarts it per table
_NOISE: dict = {"rng": random.Random(0), "next": float("inf"), "off": 0.0, "rate": 0.0, "mean": 0.0, "pauses": 0}


def real_ns() -> int:
    """The real perf_counter_ns, whatever is installed."""
    return _REAL["perf_counter_ns"]()


def factor() -> float:
    return _STATE["k"]


def _dilated(k: float, basis: str, current: dict, noise) -> dict:
    """Clocks reading k x the elapsed `basis` time ("cpu": this thread's CPU time; "wall": real elapsed time), plus the
    virtual pauses when `noise` is on, continuing from what `current` reads now (no jump)."""
    src = time.thread_time_ns if basis == "cpu" else _REAL["perf_counter_ns"]
    s0 = src()
    p0, pn0 = current["perf_counter"](), current["perf_counter_ns"]()
    m0, mn0 = current["monotonic"](), current["monotonic_ns"]()
    if noise is None:
        def perf_counter() -> float:
            return p0 + (src() - s0) * k * 1e-9

        def perf_counter_ns() -> int:
            return pn0 + int((src() - s0) * k)

        def monotonic() -> float:
            return m0 + (src() - s0) * k * 1e-9

        def monotonic_ns() -> int:
            return mn0 + int((src() - s0) * k)
    else:
        st = _NOISE
        st["rate"], st["mean"] = noise  # pauses per box ns, mean pause in ns

        def elapsed() -> float:
            e = (src() - s0) * k
            if e >= st["next"]:
                rng = st["rng"]
                while e >= st["next"]:
                    st["off"] += rng.expovariate(1.0 / st["mean"])
                    st["pauses"] += 1
                    st["next"] += rng.expovariate(st["rate"])
            st["now"] = e
            return e + st["off"]

        def perf_counter() -> float:
            return p0 + elapsed() * 1e-9

        def perf_counter_ns() -> int:
            return pn0 + int(elapsed())

        def monotonic() -> float:
            return m0 + elapsed() * 1e-9

        def monotonic_ns() -> int:
            return mn0 + int(elapsed())
    return {"perf_counter": perf_counter, "perf_counter_ns": perf_counter_ns, "monotonic": monotonic,
            "monotonic_ns": monotonic_ns}


def reseed_noise(seed) -> None:
    """Restart the virtual pauses from `seed` (one stream per table, so a table's pauses do not depend on the job)."""
    st = _NOISE
    if _STATE["noise"] is None:
        return
    st["rng"] = random.Random(seed)
    time.perf_counter_ns()  # sets st["now"]
    st["next"] = st.get("now", 0.0) + st["rng"].expovariate(st["rate"])


def install(k: float, basis: str = "wall", noise=None) -> None:
    """Make every clock read k x the elapsed `basis` time (module doc), plus virtual pauses when `noise` is
    (pauses per box second, mean pause in us). k = 1 with basis "wall" and no noise puts the real clocks back."""
    k = float(k)
    if not k > 0:
        raise ValueError(f"k must be positive, got {k}")
    if basis not in ("wall", "cpu"):
        raise ValueError(f"basis must be wall or cpu, got {basis!r}")
    nz = None
    if noise:
        rate_s, mean_us = noise
        nz = (float(rate_s) * 1e-9, float(mean_us) * 1e3) if rate_s > 0 else None
    old = _STATE["fns"]
    real = k == 1.0 and basis == "wall" and nz is None
    new = dict(_REAL) if real else _dilated(k, basis, old, nz)
    for name in CLOCKS:
        setattr(time, name, new[name])
    swap = {id(old[c]): new[c] for c in CLOCKS}
    swap.update({id(_REAL[c]): new[c] for c in CLOCKS})
    known = (*old.values(), *_REAL.values())
    for modname, mod in list(sys.modules.items()):
        if mod is None or not (modname == "hyperion" or modname.startswith("hyperion.")):
            continue
        d = getattr(mod, "__dict__", None)
        if not d:
            continue
        for key, val in list(d.items()):
            if callable(val) and id(val) in swap and any(val is f for f in known):
                d[key] = swap[id(val)]
    _STATE.update(k=k, basis=basis, noise=nz, fns=new)
    if nz is not None:
        _NOISE["off"] = 0.0
        _NOISE["pauses"] = 0
        reseed_noise(0)


def uninstall() -> None:
    install(1.0, "wall", None)


# ---------------------------------------------------------------------------------------------- contention
_BUSY = r"""
import os, random, sys, time
cpu, on, off, seed = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
os.sched_setaffinity(0, {cpu})
rng = random.Random(seed)
pc = time.perf_counter
while True:
    end = pc() + rng.expovariate(1.0 / on) / 1000.0
    while pc() < end:
        pass
    if off > 0:
        time.sleep(rng.expovariate(1.0 / off) / 1000.0)
"""


def start_busy(cpus, n: int, on_ms: float, off_ms: float, seed: int = 1) -> list:
    """n busy processes pinned to each core of `cpus` (module doc). Returns the Popen handles."""
    procs = []
    for c in cpus:
        for i in range(n):
            procs.append(subprocess.Popen([sys.executable, "-c", _BUSY, str(c), str(on_ms), str(off_ms),
                                           str(seed * 1000 + c * 10 + i)]))
    return procs


def stop_busy(procs) -> None:
    for p in procs:
        try:
            p.kill()
        except Exception:  # noqa: BLE001
            pass
    for p in procs:
        try:
            p.wait(timeout=5)
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------------------------- the seat
_GC = {"n": 0, "gen2": 0, "ns": 0, "_t": 0}


def _gc_cb(phase, info):
    if phase == "start":
        _GC["_t"] = real_ns()
    else:
        _GC["n"] += 1
        if info.get("generation") == 2:
            _GC["gen2"] += 1
        _GC["ns"] += real_ns() - _GC["_t"]


def _counts_of(bot):
    """The route / section counters of a composite, hybrid or Hero, or None."""
    core = getattr(bot, "core", None)
    c = getattr(core, "counts", None)
    return c if isinstance(c, Counter) else None


TRACE_KEYS = ("section", "street", "first", "n_in", "alive")


def _keys(obs, first: bool) -> tuple:
    from hyperion.compose.sections import SECTIONS, section

    n_in = sum(1 for x in obs.in_hand if x)
    alive = sum(1 for s in range(len(obs.stacks)) if obs.stacks[s] + obs.bets[s] > 0 or obs.in_hand[s])
    return SECTIONS[section(obs)], obs.street, first, n_in, alive


class SlowSeat:
    """The candidate in mode "model": times its own act() on the (dilated) clock and reports that as `last_cost_ns`, so
    the engine's timeout model folds or checks it over 1 ms exactly as strict mode would (module doc, Scope). Tracks
    SafeBot's panic and, with trace_us, records decisions slower than that many real us."""

    free = False  # --free: never timed out (the seat as in a model-mode run)
    defer = False  # --defer: each hand_end runs at the top of the next act(), inside the timed call (module doc)

    def __init__(self, bot, trace_us: float | None = None, payouts: str = "lin"):
        self.impl = bot
        self.safe = getattr(bot, "safe", None)
        self.last_cost_ns = None
        self.trace_us = trace_us
        self.payouts = payouts
        self.traces: list = []
        self.base: Counter = Counter()  # with trace_us: every decision by TRACE_KEYS, the rates' denominators
        self.reset()

    def reset(self):
        self._pending = None
        self.calls = 0
        self.panic_hand = -1
        self.panic_call = -1
        self.panic_calls = 0  # calls played in panic (with a governor's recovery panic can end)
        self.lvl = [0] * 8  # calls played at each governor level (index = SafeBot.degrade_level after the call)
        self.level_max = 0
        self.worst_ns = 0
        self.hand = -1

    def new_table(self, rules, seat, n_players):
        self.reset()
        self._pending = None
        self.impl.new_table(rules, seat, n_players)

    def act(self, obs):
        tr = self.trace_us is not None
        if tr:
            counts = _counts_of(self.impl)
            before = dict(counts) if counts is not None else None
            g0n, g02, g0ns = _GC["n"], _GC["gen2"], _GC["ns"]
            r0, c0 = real_ns(), time.thread_time_ns()
        pcn = time.perf_counter_ns
        t0 = pcn()
        try:
            if self._pending is not None:  # the adapter's deferred hand end, inside the kit's timer
                r, self._pending = self._pending, None
                self.impl.hand_end(r)
            return self.impl.act(obs)
        finally:
            dt = pcn() - t0
            self.last_cost_ns = None if self.free else dt
            self.calls += 1
            if dt > self.worst_ns:
                self.worst_ns = dt
            safe = self.safe
            if safe is not None:
                pm = getattr(safe, "panic_mode", False)
                if pm:
                    self.panic_calls += 1
                    if self.panic_hand < 0:
                        self.panic_hand, self.panic_call = obs.hand_no, self.calls
                lv = getattr(safe, "degrade_level", 0) or 0
                self.lvl[lv if lv < 8 else 7] += 1
                if lv > self.level_max:
                    self.level_max = lv
            first = obs.hand_no != self.hand
            self.hand = obs.hand_no
            if tr:
                cpu_us = (time.thread_time_ns() - c0) / 1000.0
                self.base["|".join(str(v) for v in _keys(obs, first))] += 1
                if cpu_us > self.trace_us:
                    self._trace(obs, cpu_us, (real_ns() - r0) / 1000.0, dt, first, before, g0n, g02, g0ns)

    def _trace(self, obs, cpu_us, wall_us, dt, first, before, g0n, g02, g0ns):
        from hyperion.compose.sections import SECTIONS, section

        counts = _counts_of(self.impl)
        moved = []
        if counts is not None and before is not None:
            moved = sorted(k for k, v in counts.items() if v != before.get(k, 0))
        n_in = sum(1 for x in obs.in_hand if x)
        alive = sum(1 for s in range(len(obs.stacks)) if obs.stacks[s] + obs.bets[s] > 0 or obs.in_hand[s])
        core = getattr(self.impl, "core", None)
        self.traces.append({
            "us": round(cpu_us, 1), "wall_us": round(wall_us, 1), "box_us": round(dt / 1000.0, 1), "hand": obs.hand_no, "call": self.calls,
            "street": obs.street, "n_in": n_in, "alive": alive, "first": first, "to_call": obs.to_call > 0,
            "allin_faced": any(obs.in_hand[s] and obs.stacks[s] == 0 for s in range(len(obs.stacks)) if s != obs.seat),
            "section": SECTIONS[section(obs)], "moved": moved, "gc": _GC["n"] - g0n, "gc2": _GC["gen2"] - g02,
            "gc_us": round((_GC["ns"] - g0ns) / 1000.0, 1), "panic": bool(getattr(self.safe, "panic_mode", False)),
            "path": getattr(core, "last_path", "") or "", "payouts": self.payouts,
        })

    def hand_end(self, result):
        if self.defer:
            self._pending = result
            return
        self.impl.hand_end(result)

    def variant_decide(self, prompt):
        return self.impl.variant_decide(prompt)


# ---------------------------------------------------------------------------------------------- the runs
SEED = 7
PAYOUTS = {"lin": None, "brief": (10, 7, 5, 4, 3, 2, 1, 0), "th": (50, 25, 12, 6, 3, 2, 1, 1)}
PLACEHOLDER = "slowbox_seat"
# --det: the deterministic settings tools/swap.py's model mode plays (panic, soft deadlines and late_us off)
DET = {
    "composite": {"panic_after": 10 ** 9, "late_us": 1e9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9},
    "hybrid3_x": {"panic_after": 10 ** 9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9},
    "hybrid3": {"panic_after": 10 ** 9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9},
    "hero": {"panic_after": 10 ** 9},
}


def _register_placeholder():
    from hyperion.sim import bestiary as B

    if PLACEHOLDER not in B.REGISTRY:
        class SlowboxSeat(B._Base):
            """Placeholder for the seat tools/slowbox.py fills with its candidate (seating only)."""

        B.REGISTRY[PLACEHOLDER] = SlowboxSeat


def seating(field: str, t: int):
    """run_tournament's seating for table t of `<field>@<candidate>`: (table seed, names by seat, candidate's seat)."""
    from hyperion.sim.bestiary import field_names

    _register_placeholder()
    names = [nm.strip().lower() for nm in field_names(f"{field}@{PLACEHOLDER}") if nm.strip()]
    table_seed = SEED * 1_000_003 + t
    rng = random.Random(table_seed)
    seats = list(names[:8])
    while len(seats) < 8:
        seats.append(rng.choice(names))
    rng.shuffle(seats)
    return table_seed, seats, seats.index(PLACEHOLDER)


def spec_of(spec) -> tuple[str, dict]:
    if isinstance(spec, str):
        return spec, {}
    return spec["bot"], dict(spec.get("dials", {}))


def build(spec, seed: int, det: bool = False):
    from hyperion import ship

    name, dials = spec_of(spec)
    if det:
        dials = {**DET.get(name, {}), **dials}
    return ship.make_bot(name, dials, seed)


def play(spec, field: str, t: int, rot: int, rules, scope: str = "seat", trace_us=None, det: bool = False,
         payouts: str = "lin", seat_cls=None):
    """One rotation of table t with the candidate in Hero's seat: (record, the seat's BotStats, traces, base counts)."""
    from hyperion.sim.bestiary import make_bot
    from hyperion.sim.engine import BotStats, play_table

    table_seed, seats, me = seating(field, t)
    reseed_noise(table_seed * 64 + rot)
    bots = []
    for s, nm in enumerate(seats):
        sd = table_seed * 64 + rot * 8 + s
        bots.append((seat_cls or SlowSeat)(build(spec, sd, det), trace_us, payouts) if s == me else make_bot(nm, seed=sd))
    stats = [BotStats(nm) for nm in seats]
    mode = "model" if scope == "seat" else "strict"
    res = play_table(bots, rules, seed=table_seed, rotation=rot, mode=mode, stats=stats)
    seat = bots[me]
    st = stats[me]
    safe = seat.safe
    rec = {"t": t, "rot": rot, "pts": res.points[me], "place": res.places[me], "tmo": st.over_budget,
           "calls": st.calls + st.first_calls, "over": int(getattr(safe, "overruns", 0) or 0) if safe is not None else 0,
           "panic": seat.panic_hand >= 0, "panic_hand": seat.panic_hand, "panic_call": seat.panic_call,
           "level": seat.level_max, "worst_us": round(seat.worst_ns / 1000.0, 1), "hands": res.hands,
           "panic_calls": seat.panic_calls, "lvl": seat.lvl,
           "changes": int(getattr(safe, "level_changes", 0) or 0) if safe is not None else 0}
    return rec, st, seat.traces, seat.base


def _init_worker(k: float, cpus, basis: str = "wall", noise=None):
    if cpus:
        ident = getattr(__import__("multiprocessing").current_process(), "_identity", (1,))
        i = (ident[0] - 1) % len(cpus) if ident else 0
        os.sched_setaffinity(0, {cpus[i]})
    gc.callbacks.append(_gc_cb)
    install(k, basis, noise)


def _job(args):
    spec_name, spec, field, ts, payouts, scope, trace_us, det, free, defer = args
    SlowSeat.free = bool(free)
    SlowSeat.defer = bool(defer)
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B

    B.HYBRID_CONFIG = None  # the shipped settings for every hybrid / Hero the bestiary builds (none sit in night)
    B.HERO_CONFIG = None
    rules = Rules(payouts=PAYOUTS[payouts]) if PAYOUTS[payouts] else Rules()
    l0 = os.getloadavg()[0]
    w0 = time.time()
    recs, traces = [], []
    base: Counter = Counter()
    hist = None
    for t in ts:
        for rot in range(8):
            rec, st, tr, bc = play(spec, field, t, rot, rules, scope, trace_us, det, payouts)
            base.update(bc)
            recs.append(rec)
            for x in tr:
                x["t"], x["rot"] = t, rot
            traces.extend(tr)
            if hist is None:
                hist = list(st.hist)
            else:
                h = st.hist
                for i in range(len(hist)):
                    hist[i] += h[i]
    return spec_name, ts[0], {"recs": recs, "hist": hist, "traces": traces, "base": dict(base),
                              "load": [l0, os.getloadavg()[0]],
                              "secs": time.time() - w0, "pid": os.getpid()}


def parse_seeds(s: str) -> list:
    lo, hi = (int(x) for x in s.split(":"))
    return list(range(lo, hi))


def cmd_run(a) -> list:
    specs = load_specs(a.specs)
    seeds = parse_seeds(a.seeds)
    cpus = [int(x) for x in a.cpus.split(",")] if a.cpus else []
    if a.contend and not cpus:
        raise SystemExit("--contend needs --cpus (one core per worker)")
    if a.contend and len(cpus) < a.workers:
        raise SystemExit("--contend: give one core per worker in --cpus")
    on, off = (float(x) for x in a.duty_ms.split(","))
    if a.contend and a.clock != "wall":
        raise SystemExit("--contend needs --clock wall (a preemption is wall time, not CPU time)")
    if a.scope == "all" and a.clock != "wall":
        raise SystemExit("--scope all needs --clock wall (opponents that sleep are timed out on the wall clock)")
    noise = tuple(float(x) for x in a.noise.split(",")) if a.noise else None
    os.makedirs(a.out, exist_ok=True)
    chunks = [seeds[i:i + a.chunk] for i in range(0, len(seeds), a.chunk)]
    # interleaved (chunk by chunk, every spec), so the specs of one run share the host's load as it varies
    jobs = [(nm, spec, a.field, ch, a.payouts, a.scope, a.trace_us, a.det, a.free, a.defer) for ch in chunks
            for nm, spec in specs.items()]
    busy = start_busy(cpus[:a.workers], a.contend, on, off) if a.contend else []
    res: dict = {nm: {} for nm in specs}
    t0 = time.time()
    try:
        with Pool(a.workers, initializer=_init_worker,
                  initargs=(a.k, cpus if a.contend or a.pin else [], a.clock, noise)) as p:
            for nm, off0, o in p.imap_unordered(_job, jobs):
                res[nm][str(off0)] = o
                if a.verbose:
                    print(f"{nm} {off0} {o['secs']:.0f}s load {o['load'][0]:.1f}", file=sys.stderr, flush=True)
    finally:
        stop_busy(busy)
    paths = []
    for nm in specs:
        path = os.path.join(a.out, f"slow.{a.field}.{a.payouts}.{a.scope}.k{a.k:g}.{a.clock}"
                                   f"{'.n' + a.noise.replace(',', '-') if a.noise else ''}"
                                   f"{'.c' + str(a.contend) + 'x' + a.duty_ms.replace(',', '-') if a.contend else ''}"
                                   f"{'.det' if a.det else ''}{'.free' if a.free else ''}{'.defer' if a.defer else ''}.{a.seeds.replace(':', '-')}.{a.tag}.{nm}.json")
        out = {"spec": nm, "def": specs[nm], "field": a.field, "seeds": a.seeds, "payouts": a.payouts, "scope": a.scope,
               "k": a.k, "free": a.free, "defer": a.defer, "clock": a.clock, "noise": a.noise, "contend": a.contend, "duty_ms": a.duty_ms if a.contend else "", "cpus": cpus, "det": a.det,
               "res": res[nm], "secs": time.time() - t0, "argv": sys.argv[1:]}
        with open(path + ".tmp", "w") as fh:
            json.dump(out, fh)
        os.replace(path + ".tmp", path)
        paths.append(path)
    print(table(paths))
    return paths


def load_specs(spec: str) -> dict:
    text = spec.strip()
    if text.startswith("{"):
        return json.loads(text)
    if os.path.isfile(text):
        with open(text) as fh:
            return json.load(fh)
    return {nm: nm for nm in text.split(",") if nm}


# ---------------------------------------------------------------------------------------------- quiet costs
class QuietSeat(SlowSeat):
    """--det replays: each call's CPU time (thread clock, real) in order, its features on the first pass, and cProfile
    around the calls named in `prof_calls` (a set of call indices) when given."""

    def __init__(self, bot, trace_us=None, payouts="lin"):
        super().__init__(bot, None, payouts)
        self.cpu: list = []
        self.he: list = []  # hand_end CPU ns, in order
        self.feat: list | None = None
        self.prof_calls = None
        self.profiler = None

    def act(self, obs):
        i = len(self.cpu)
        pr = self.profiler if self.prof_calls is not None and i in self.prof_calls else None
        feat = self.feat
        if feat is not None:
            counts = _counts_of(self.impl)
            before = dict(counts) if counts is not None else None
        c0 = time.thread_time_ns()
        if pr is not None:
            pr.enable()
        try:
            return self.impl.act(obs)
        finally:
            if pr is not None:
                pr.disable()
            self.cpu.append(time.thread_time_ns() - c0)
            if feat is not None:
                first = obs.hand_no != self.hand
                counts = _counts_of(self.impl)
                moved = sorted(k for k, v in counts.items() if v != before.get(k, 0)) if counts is not None else []
                sec, street, _, n_in, alive = _keys(obs, first)
                core = getattr(self.impl, "core", None)
                feat.append((sec, street, first, n_in, alive, obs.to_call > 0, ",".join(moved),
                             getattr(core, "last_path", "") or "", obs.hand_no))
            self.hand = obs.hand_no

    def hand_end(self, result):
        c0 = time.thread_time_ns()
        try:
            self.impl.hand_end(result)
        finally:
            self.he.append(time.thread_time_ns() - c0)


def _job_quiet(args):
    spec_name, spec, field, ts, payouts, reps, prof_us = args
    import cProfile
    import pstats
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B

    B.HYBRID_CONFIG = None
    B.HERO_CONFIG = None
    rules = Rules(payouts=PAYOUTS[payouts]) if PAYOUTS[payouts] else Rules()
    l0 = os.getloadavg()[0]
    out, mism = [], 0
    prof = cProfile.Profile() if prof_us else None
    for t in ts:
        for rot in range(8):
            best = None
            feat = None
            pts = None
            for r in range(reps):
                holder: dict = {}

                def mk(bot, trace_us=None, pay="lin", _h=holder, _r=r):
                    q = QuietSeat(bot, None, pay)
                    if _r == 0:
                        q.feat = []
                    _h["seat"] = q
                    return q

                rec, st, _, _ = play(spec, field, t, rot, rules, det=True, payouts=payouts, seat_cls=mk)
                q = holder["seat"]
                if r == 0:
                    feat, best, pts, he = q.feat, list(q.cpu), rec["pts"], list(q.he)
                elif len(q.cpu) != len(best) or rec["pts"] != pts or len(q.he) != len(he):
                    mism += 1
                else:
                    best = [min(x, y) for x, y in zip(best, q.cpu)]
                    he = [min(x, y) for x, y in zip(he, q.he)]
            if prof is not None:
                slow = {i for i, c in enumerate(best) if c > prof_us * 1000}
                if slow:
                    def mkp(bot, trace_us=None, pay="lin", _s=slow):
                        q = QuietSeat(bot, None, pay)
                        q.prof_calls, q.profiler = _s, prof
                        return q

                    play(spec, field, t, rot, rules, det=True, payouts=payouts, seat_cls=mkp)
            out.append({"t": t, "rot": rot, "pts": pts, "cpu": best, "feat": feat, "he": he})
    pstat = None
    if prof is not None:
        import io

        buf = io.StringIO()
        try:
            pstats.Stats(prof, stream=buf).sort_stats("cumulative").print_stats(40)
        except TypeError:  # no calls profiled
            pass
        pstat = buf.getvalue()
    return spec_name, ts[0], {"tables": out, "mismatch": mism, "load": [l0, os.getloadavg()[0]], "prof": pstat}


def cmd_quiet(a) -> list:
    specs = load_specs(a.specs)
    seeds = parse_seeds(a.seeds)
    os.makedirs(a.out, exist_ok=True)
    chunks = [seeds[i:i + a.chunk] for i in range(0, len(seeds), a.chunk)]
    jobs = [(nm, spec, a.field, ch, a.payouts, a.reps, a.profile_us) for ch in chunks for nm, spec in specs.items()]
    res: dict = {nm: {} for nm in specs}
    with Pool(a.workers, initializer=_init_worker, initargs=(1.0, [], "wall", None)) as p:
        for nm, off0, o in p.imap_unordered(_job_quiet, jobs):
            res[nm][str(off0)] = o
    paths = []
    for nm in specs:
        path = os.path.join(a.out, f"quiet.{a.field}.{a.payouts}.{a.seeds.replace(':', '-')}.{a.tag}.{nm}.json")
        with open(path + ".tmp", "w") as fh:
            json.dump({"spec": nm, "def": specs[nm], "field": a.field, "seeds": a.seeds, "payouts": a.payouts,
                       "reps": a.reps, "res": res[nm]}, fh)
        os.replace(path + ".tmp", path)
        paths.append(path)
        print(quiet_report(path))
    return paths


def _he_line(tabs) -> str:
    he = sorted(c for x in tabs for c in x.get("he", []))
    if not he:
        return "  hand_end: not recorded"
    n = len(he)
    return (f"  hand_end (the adapter delivers it inside the next decision when the kit's signal has no chip deltas): "
            f"p50 {he[n // 2] / 1000:.0f}  p99 {he[min(n - 1, int(.99 * n))] / 1000:.0f}  max {he[-1] / 1000:.0f} us")


def safebot_replay(costs_ns, k: float, deadline_ms: float = 0.5, panic_after: int = 5, panic_rate: float = 0.02):
    """SafeBot's panic rule on one table's quiet costs at speed k (play after panic ignored): (overruns, timeouts,
    the call that would start panic or -1)."""
    over = tmo = 0
    pcall = -1
    dl = deadline_ms * 1e6
    for i, c in enumerate(costs_ns, 1):
        box = c * k
        if box > 1e6:
            tmo += 1
        if box > dl:
            over += 1
            if pcall < 0 and over >= panic_after and over >= panic_rate * i:
                pcall = i
    return over, tmo, pcall


def quiet_report(path: str, ks=(1.0, 1.5, 2.0, 3.0), by="section,street,n_in,alive,first,moved,path") -> str:
    d = load(path)
    tabs = [x for off in sorted(d["res"], key=int) for x in d["res"][off]["tables"]]
    mism = sum(off["mismatch"] for off in d["res"].values())
    loads = [x for off in d["res"].values() for x in off["load"]]
    allc = [c for x in tabs for c in x["cpu"]]
    n = len(allc)
    srt = sorted(allc)

    def q(p):
        return srt[min(n - 1, int(p * n))] / 1000.0 if n else 0.0

    out = [f"{d['spec']} quiet costs (min of {d['reps']} det replays, CPU us), {d['field']} {d['payouts']} seeds "
           f"{d['seeds']} x 8: {len(tabs)} tables, {n} decisions, {mism} replay mismatches, load "
           f"{min(loads):.1f}-{max(loads):.1f}",
           f"  p50 {q(.5):.0f}  p90 {q(.9):.0f}  p99 {q(.99):.0f}  p99.9 {q(.999):.0f}  max {srt[-1] / 1000 if n else 0:.0f}",
           _he_line(tabs),
           "", "| k | decisions over the 0.5 ms soft deadline | over 1 ms (timeouts) | tables that would panic | "
           "mean call of panic |", "|---|---|---|---|---|"]
    for k in ks:
        ov = tm = pn = 0
        pc = []
        for x in tabs:
            o, t_, p_ = safebot_replay(x["cpu"], k)
            ov += o
            tm += t_
            if p_ > 0:
                pn += 1
                pc.append(p_)
        out.append(f"| {k:g} | {ov} ({100 * ov / max(1, n):.2f}%, {ov / max(1, len(tabs)):.2f}/table) | {tm} "
                   f"({100 * tm / max(1, n):.3f}%, {tm / max(1, len(tabs)):.2f}/table) | {pn} of {len(tabs)} | "
                   f"{sum(pc) / len(pc) if pc else 0:.0f} |")
    names = ("section", "street", "n_in", "alive", "first", "to_call", "moved", "path", "hand")
    for thr in (167, 250, 333):
        out.append(f"\n  decisions over {thr} us (the soft deadline at k = {500 / thr:.1f}), by key "
                   f"(count, share of them, rate within the key):")
        for key in by.split(","):
            j = names.index(key)
            den: Counter = Counter()
            num: Counter = Counter()
            for x in tabs:
                for c, f in zip(x["cpu"], x["feat"]):
                    v = f[j]
                    if key == "moved":
                        v = ",".join(m for m in str(v).split(",") if m and m.split(":")[0] not in SECTION_NAMES) or "-"
                    den[v] += 1
                    if c > thr * 1000:
                        num[v] += 1
            tot = sum(num.values())
            out.append(f"    by {key}: " + "; ".join(f"{v} {c} ({100 * c / max(1, tot):.0f}%, {100 * c / den[v]:.1f}%)"
                                                  for v, c in num.most_common(10)))
    profs = [off.get("prof") for off in d["res"].values() if off.get("prof")]
    if profs:
        out.append("\n  cProfile of the slow decisions (first job's):\n" + profs[0])
    return "\n".join(out)


# ---------------------------------------------------------------------------------------------- reports
def ci(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    v = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, 1.96 * math.sqrt(v / n)


def load(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def recs_of(d) -> list:
    return [r for off in sorted(d["res"], key=int) for r in d["res"][off]["recs"]]


def per_seed(recs) -> dict:
    by: dict = {}
    for r in recs:
        by.setdefault(r["t"], []).append(r["pts"])
    return {t: sum(v) / len(v) for t, v in by.items()}


def pct(hist, q: float) -> float:
    total = sum(hist)
    if not total:
        return 0.0
    need = q * total
    acc = 0
    for i, c in enumerate(hist):
        acc += c
        if acc >= need:
            return float(i)
    return float(len(hist) - 1)


def label(d) -> str:
    s = f"{d['spec']} k={d['k']:g}"
    if d.get("clock", "wall") != "cpu":
        s += f" ({d.get('clock', 'wall')} clock)"
    if d.get("noise"):
        s += f" noise {d['noise']}"
    if d.get("contend"):
        s += f" contend {d['contend']}x({d['duty_ms']})"
    if d.get("scope", "seat") != "seat":
        s += f" scope={d['scope']}"
    if d.get("det"):
        s += " det"
    if d.get("free"):
        s += " free"
    if d.get("defer"):
        s += " defer"
    return s


def summary(d) -> dict:
    recs = recs_of(d)
    hist = None
    loads = []
    for off in d["res"].values():
        h = off["hist"]
        hist = list(h) if hist is None else [a + b for a, b in zip(hist, h)]
        loads.extend(off["load"])
    n = len(recs)
    m, h = ci(list(per_seed(recs).values()))
    worst = max((r["worst_us"] for r in recs), default=0.0)
    calls = sum(r["calls"] for r in recs)
    pc = sum(r.get("panic_calls", 0) for r in recs)
    lv = [sum(r.get("lvl", [0] * 8)[i] for r in recs) for i in range(8)]
    return {"n": n, "pts": m, "ci": h, "tmo": sum(r["tmo"] for r in recs) / max(1, n),
            "panic_share": pc / max(1, calls), "lvl_share": [x / max(1, calls) for x in lv],
            "has_lvl": any("lvl" in r for r in recs),
            "changes": sum(r.get("changes", 0) for r in recs) / max(1, n),
            "tmo_tables": sum(1 for r in recs if r["tmo"]), "panic": sum(1 for r in recs if r["panic"]),
            "level": Counter(r.get("level", 0) for r in recs), "calls": sum(r["calls"] for r in recs),
            "tmo_all": sum(r["tmo"] for r in recs), "p50": pct(hist or [0], 0.5), "p99": pct(hist or [0], 0.99),
            "max": worst, "load": (min(loads), max(loads)) if loads else (0, 0)}


def table(paths, ref: str | None = None) -> str:
    ds = [load(p) for p in paths]
    rd = load(ref) if ref else ds[0]
    rs = per_seed(recs_of(rd))
    out = [f"{ds[0]['field']} ({ds[0]['payouts']}), seeds {ds[0]['seeds']} x 8; paired against {label(rd)}", "",
           "| run | points ± 95% | - ref (paired) | timeouts / table | tables with a timeout | panic tables | "
           "calls in panic / below level 0 | p50 / p99 / max us (box) | load |", "|---|---|---|---|---|---|---|---|---|"]
    for d in ds:
        s = summary(d)
        ps = per_seed(recs_of(d))
        common = sorted(set(ps) & set(rs))
        if d is rd or (ref is None and d is ds[0]):
            dd = "-"
        else:
            dm, dh = ci([ps[t] - rs[t] for t in common])
            dd = f"{dm:+.3f} ± {dh:.3f}" + (" **" if abs(dm) > dh else "")
        lv = {k: v for k, v in s["level"].items() if k}
        lvs = (" (levels " + ", ".join(f"{k}: {v}" for k, v in sorted(lv.items())) + ")") if lv else ""
        below = 1.0 - s["lvl_share"][0]
        out.append(f"| {label(d)} | {s['pts']:.3f} ± {s['ci']:.3f} | {dd} | {s['tmo']:.3f} ({s['tmo_all']} of "
                   f"{s['calls']}) | {s['tmo_tables']} of {s['n']} | {s['panic']} of {s['n']}{lvs} | "
                   + (f"{100 * s['panic_share']:.1f}% / {100 * below:.1f}% | " if s["has_lvl"] else "- | ")
                   + f"{s['p50']:.0f} / {s['p99']:.0f} / {s['max']:.0f} | {s['load'][0]:.1f}-{s['load'][1]:.1f} |")
    return "\n".join(out)


def traces_of(d) -> list:
    return [x for off in sorted(d["res"], key=int) for x in d["res"][off].get("traces", [])]


def trace_report(path: str, by: str, top: int = 15) -> str:
    """Slow decisions by each key: count, share of the slow ones, mean CPU us, and the rate (slow / all decisions with
    that value, from the base counts) for the keys the base counts hold."""
    d = load(path)
    xs = traces_of(d)
    s = summary(d)
    base: Counter = Counter()
    for off in d["res"].values():
        base.update(off.get("base", {}))
    out = [f"{label(d)}: {len(xs)} decisions over the trace threshold of {s['calls']} "
           f"({100 * len(xs) / max(1, s['calls']):.2f}%)"]
    keys = [k.strip() for k in by.split(",") if k.strip()]

    def key_of(x, k):
        if k == "member":
            m = [c for c in x["moved"] if ":" in c and c.split(":")[0] in SECTION_NAMES]
            return m[0].split(":", 1)[1] if m else "?"
        if k == "moved":
            return ",".join(c for c in x["moved"] if not (":" in c and c.split(":")[0] in SECTION_NAMES)) or "-"
        if k == "us":
            u = x["us"]
            return "<400" if u < 400 else "<700" if u < 700 else "<1000" if u < 1000 else ">=1000"
        if k == "gc":
            return "gc2" if x["gc2"] else "gc" if x["gc"] else "-"
        return x.get(k)

    for k in keys:
        c = Counter(str(key_of(x, k)) for x in xs)
        tot: Counter = Counter()
        for x in xs:
            tot[str(key_of(x, k))] += x["us"]
        den: Counter = Counter()
        if k in TRACE_KEYS:
            i = TRACE_KEYS.index(k)
            for bk, n in base.items():
                den[bk.split("|")[i]] += n
        out.append(f"  by {k}:")
        for v, n in c.most_common(top):
            rate = f"  rate {100 * n / den[v]:5.2f}% of {den[v]}" if den.get(v) else ""
            out.append(f"    {str(v):<40} {n:>6} {100 * n / max(1, len(xs)):5.1f}%  mean {tot[v] / n:6.0f} us{rate}")
    return "\n".join(out)


try:
    from hyperion.compose.sections import SECTIONS as SECTION_NAMES  # noqa: E402
except Exception:  # noqa: BLE001
    SECTION_NAMES = ()


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--specs", required=True, help="JSON file or inline {name: {bot, dials}}, or bot names a,b")
    r.add_argument("--field", default="night")
    r.add_argument("--seeds", default="10000:10200")
    r.add_argument("--payouts", default="lin", choices=sorted(PAYOUTS))
    r.add_argument("--k", type=float, default=1.0, help="the box is k times slower (dilated clock)")
    r.add_argument("--scope", default="seat", choices=("seat", "all"))
    r.add_argument("--clock", default="cpu", choices=("cpu", "wall"),
                   help="what the dilated clock counts: this thread's CPU time (a quiet slow box) or real time")
    r.add_argument("--noise", default="", help="virtual pauses: RATE_PER_S,MEAN_US on the box's clock")
    r.add_argument("--contend", type=int, default=0, help="busy processes per worker core (noisy host)")
    r.add_argument("--duty-ms", default="5,5", help="busy processes' mean busy and sleep phases, ms")
    r.add_argument("--cpus", default="", help="cores to pin workers to (one per worker), e.g. 6,7")
    r.add_argument("--pin", action="store_true", help="pin workers to --cpus without busy processes")
    r.add_argument("--workers", type=int, default=2)
    r.add_argument("--chunk", type=int, default=10)
    r.add_argument("--trace-us", type=float, default=None, help="record decisions slower than this many real us")
    r.add_argument("--det", action="store_true", help="the model-mode settings (panic, soft deadlines off)")
    r.add_argument("--free", action="store_true", help="the seat is never timed out (with --det: model mode exactly)")
    r.add_argument("--defer", action="store_true", help="every hand_end inside the next act (the adapter's deferral)")
    r.add_argument("--out", required=True)
    r.add_argument("--tag", default="run")
    r.add_argument("-v", "--verbose", action="store_true")
    t = sub.add_parser("table")
    t.add_argument("paths", nargs="+")
    t.add_argument("--ref", default=None)
    qq = sub.add_parser("quiet")
    qq.add_argument("--specs", required=True)
    qq.add_argument("--field", default="night")
    qq.add_argument("--seeds", default="10000:10050")
    qq.add_argument("--payouts", default="lin", choices=sorted(PAYOUTS))
    qq.add_argument("--reps", type=int, default=3)
    qq.add_argument("--profile-us", type=float, default=0.0, help="cProfile the decisions whose quiet cost is over this")
    qq.add_argument("--workers", type=int, default=2)
    qq.add_argument("--chunk", type=int, default=5)
    qq.add_argument("--out", required=True)
    qq.add_argument("--tag", default="run")
    qr = sub.add_parser("qreport")
    qr.add_argument("path")
    tr = sub.add_parser("trace")
    tr.add_argument("path")
    tr.add_argument("--by", default="section,member,moved,street,n_in,alive,first,gc,us,path")
    a = p.parse_args(argv)
    if a.cmd == "run":
        cmd_run(a)
    elif a.cmd == "table":
        print(table(a.paths, a.ref))
    elif a.cmd == "quiet":
        cmd_quiet(a)
    elif a.cmd == "qreport":
        print(quiet_report(a.path))
    else:
        print(trace_report(a.path, a.by))


if __name__ == "__main__":
    main()
