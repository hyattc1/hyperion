#!/usr/bin/env python
"""Section swap matrix for the composite bot (hyperion/compose): for each (section, donor), the paired change in points
when that one section of the base route is played by the donor, on the same duplicate deals.

    .venv/bin/python tools/swap.py base  --field realistic --seeds 0:200 --out DIR [--route R0] [--donors hero,r2x,...]
    .venv/bin/python tools/swap.py cells --field realistic --seeds 0:200 --out DIR [--cells all | pre_hu:hero,...]
    .venv/bin/python tools/swap.py joint --field realistic --seeds 0:200 --out DIR --route "pre_hu=hero,post_mw=r2x"
    .venv/bin/python tools/swap.py report --field realistic --seeds 0:200 --out DIR

**Exact shortcut.** Everything here is deterministic (model mode, panic and soft deadlines off, rival 2's sampler at a
fixed sample count; below). The base run plays the base route with every member shadowing every decision, and records
for each (table seed, rotation) which (section, donor) cells ever disagree with the action taken in that section. A
rotation where a donor agrees with the base at every decision of its section follows the base's trajectory exactly
(members never interact, and agreeing actions leave the same table), so its points are the base's; only the
disagreeing rotations are replayed. The same holds for any set of swaps (the union of their disagreeing rotations),
which is how `joint` measures a combined route against its base. `--full` replays every rotation (the check).

**Determinism.** Mode "model", SafeBot panic off, the hybrids' soft deadline off and the composite's `late_us` off, as
the final comparison ran. Rival 2's sampler reads the wall clock (it stops at 260 us, ~110 samples heads-up here, with a
hard stop at 520 us): in these runs every rival 2 opponent draws a fixed `R2_SAMPLES` (110) and the rival 2 core member
a fixed 32 (its `mc_max`), so fields with rival 2 replay exactly. Its import-time equity tables stop at 1500 boards or
2.4 s: its clock is held still while it imports, so every process builds all 1500. The night persona
`agent_montecarlo` samples on the wall clock too: here its clock advances AGENT_MC_STEP_US per read; `agent_pushfold`
skips its heaviest jam EV after 260 us on the wall clock: here it never runs late. That is a fixed-speed rival 2 (`--as-built` keeps the wall clock).

The sample is one table seed (its eight rotations averaged), paired with the base on the same seed.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
# tools/ is not a package: a tool named like a stdlib module (tools/profile.py) must not shadow it (cProfile imports
# `profile`, and the runner imports cProfile)
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
sys.path.insert(0, ROOT)

from hyperion.compose import bot as CB  # noqa: E402
from hyperion.compose.sections import SECTIONS, parse_route  # noqa: E402

DONORS = ("hero", "hybrid3", "r2x", "rival1", "rival3")  # the screen's donors (the brief's list); `base` is the base
HYBRID_CONFIG = {"panic_after": 10 ** 9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9}
HERO_CONFIG = {"panic_after": 10 ** 9}
R2_SAMPLES = 110
AGENT_MC_STEP_US = 3.5  # agent_montecarlo's clock advances this much per read (the field agent's fixed-speed setting)
RIVAL5_STEP_US = 4.0  # rival 5's (the second judge's), likewise
SEED = 7
CAND = "compose_cand"
PAYOUTS = {"lin": None, "brief": (10, 7, 5, 4, 3, 2, 1, 0), "th": (50, 25, 12, 6, 3, 2, 1, 1)}


# --------------------------------------------------------------------------------------------- deterministic setup
def setup_process(mode: str = "model", as_built: bool = False) -> None:
    """Model mode: panic, soft deadlines and `late_us` off. `as_built`: rival 2 (opponent and core) keeps its wall-clock
    sampler. Strict mode: everything as shipped."""
    from hyperion.sim import bestiary as B

    if mode == "strict":
        B.HYBRID_CONFIG = None
        B.HERO_CONFIG = None
        return
    B.HYBRID_CONFIG = dict(HYBRID_CONFIG)
    B.HERO_CONFIG = dict(HERO_CONFIG)
    if as_built:
        for k in ("mc_budget_us", "mc_hard_us"):
            B.HYBRID_CONFIG.pop(k)
        return
    if hasattr(B, "AgentMonteCarloBot"):  # the night persona whose sampler runs on the wall clock: fixed speed
        B.AgentMonteCarloBot.STEP_US = AGENT_MC_STEP_US
    if hasattr(B, "Rival5Bot"):  # the second judge: its postflop sampler stops at 130 us on the wall clock
        B.Rival5Bot.STEP_US = RIVAL5_STEP_US
    if "agent_pushfold" in B.REGISTRY:  # its 260 us wall-clock guard before the heaviest jam EV: never late here
        from hyperion.sim.field import load as _load_field

        _pf = _load_field("agent_pushfold").Bot
        if not getattr(_pf, "_swap_fixed", False):
            _pf._el = lambda self: 0.0
            _pf._swap_fixed = True
    if "hyperion.sim.rivals.rival2" in sys.modules or os.environ.get("SWAP_R2", "1") == "1":
        if "hyperion.sim.rivals.rival2" not in sys.modules:
            # its import-time equity tables stop at 1500 boards or after 2.4 s: hold its clock still while it imports,
            # so every process builds all 1500 (what a quiet host does) whatever the load
            real = time.perf_counter
            time.perf_counter = lambda: 0.0
            try:
                from hyperion.sim.rivals import rival2  # noqa: F401
            finally:
                time.perf_counter = real
        from hyperion.sim.rivals import rival2 as R2

        R2.Bot.MC_BUDGET_US = 1e9
        R2.Bot.MC_MAX = R2_SAMPLES
        if not getattr(R2.Bot, "_swap_fixed", False):  # its postflop call also passes a hard stop at t0 + 520 us
            wall = R2.Bot.equity_mc

            def equity_mc(self, hole, board, cuts, deadline, fits=None, hard=None):
                return wall(self, hole, board, cuts, deadline, fits, deadline + 1.0)

            R2.Bot.equity_mc = equity_mc
            R2.Bot._swap_fixed = True
        # its import-time equity tables stop at 1500 boards or 2.4 s, whichever comes first: on a host slow enough for
        # the clock to bind, processes differ, so say so
        if R2.MC_N != R2.MC_BOARDS:
            print(f"warning: rival 2's import-time tables stopped at {R2.MC_N} of {R2.MC_BOARDS} boards in this "
                  "process: fields with rival 2 do not replay exactly", file=sys.stderr)


def route_str(route: dict) -> str:
    return ",".join(f"{k}={v}" for k, v in sorted(route.items(), key=lambda kv: SECTIONS.index(kv[0])))


def seating(field: str, t: int, seed: int = SEED):
    """run_tournament's seating for table t: (table seed, names by seat)."""
    from hyperion.sim.bestiary import field_names

    names = [nm.strip().lower() for nm in field_names(field) if nm.strip()]
    table_seed = seed * 1_000_003 + t
    rng = random.Random(table_seed)
    seats = list(names[:8])
    while len(seats) < 8:
        seats.append(rng.choice(names))
    rng.shuffle(seats)
    return table_seed, seats


def play(field: str, cand: str, t: int, rot: int, rules=None, mode: str = "model"):
    """One rotation of table t with `cand` in Hero's seat, exactly as run_tournament plays it: (points, its BotStats)."""
    from hyperion.core.types import Rules
    from hyperion.sim.bestiary import make_bot
    from hyperion.sim.engine import BotStats, play_table

    table_seed, seats = seating(f"{field}@{cand}", t)
    bots = [make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seats)]
    stats = [BotStats(nm) for nm in seats]
    res = play_table(bots, rules or Rules(), seed=table_seed, rotation=rot, mode=mode, stats=stats)
    s = seats.index(cand)
    return res.points[s], stats[s], bots[s]


# --------------------------------------------------------------------------------------------- the recorder
class Recorder:
    """The tap: per rotation, the cells (section index, donor index) whose donor's action differs from the one taken in
    that section at least once, the variants (dial changes) that would change at least one decision, and decision /
    disagreement counts."""

    def __init__(self, donors, variants=()):
        self.donors = list(donors)
        self.variants = list(variants)  # (kind, parent member, variant member, layer params)
        self.reset()

    def reset(self):
        self.cells: set = set()
        self.vflags: set = set()
        self.dec = [0] * len(SECTIONS)
        self.dis = {}

    def bind(self, core):
        idx = {n: i for i, n in enumerate(core.names)}
        self.spec = [(idx[CB.DONORS[d][0]], CB.DONORS[d][1]) for d in self.donors]
        self.vspec = [(kind, idx.get(parent, -1), idx.get(vm, -1), lp) for kind, parent, vm, lp in self.variants]
        core.tap = self

    def __call__(self, core, obs, sec, mi, own, taken, props, ex):
        self.dec[sec] += 1
        tk = taken.clamp(obs)
        for di, (m, layer) in enumerate(self.spec):
            if not core.plain and core.plain_only[m]:
                continue  # the composite would play the base here
            p = props[m]
            if p is None:
                a = None
            else:
                a = p
                if layer and ex is not None:
                    try:
                        b = ex.override(obs, p)
                    except Exception:  # noqa: BLE001
                        b = None
                    if b is not None:
                        a = b
            if a is None or a.clamp(obs) != tk:
                self.cells.add((sec, di))
                k = (sec, di)
                self.dis[k] = self.dis.get(k, 0) + 1
        layer_on = core.route[sec][1] or core.panic
        for vi, (kind, pm, vm, lp) in enumerate(self.vspec):
            if vi in self.vflags:
                continue
            if kind == "full":
                self.vflags.add(vi)
                continue
            m_eff = vm if (kind == "member" and mi == pm) else mi
            p = props[m_eff] if m_eff >= 0 else None
            a = p
            if p is not None and layer_on and ex is not None:
                saved = ex.p
                try:
                    if kind == "layer":
                        ex.p = lp
                    b = ex.override(obs, p)
                except Exception:  # noqa: BLE001
                    b = None
                finally:
                    ex.p = saved
                if b is not None:
                    a = b
            if a is None or a.clamp(obs) != tk:
                self.vflags.add(vi)


# exploit params the layer's reads accumulate with: a change to these is not a read-time swap
_LAYER_STATE = ("decay", "recover_cut", "recover_keep")


def classify_variant(dials: dict, delta: dict):
    """How the base run can tell where a dial change would change a decision: ("member", parent, base_overrides,
    hero_member) for a copy of one member, ("layer", ExploitParams) for the layer's read-time params, else ("full",)
    (every rotation replayed)."""
    heads = {k.partition(".")[0] for k in delta}
    if heads <= {"r3", "base"}:
        _, kw = CB.parse_dials({"route": "", **delta})
        return ("member", "base", kw["base_overrides"], {})
    if heads == {"hero"}:
        _, kw = CB.parse_dials({"route": "", **delta})
        return ("member", "hero", {}, kw["hero_member"])
    if heads == {"exploit"} and not any(k.partition(".")[2] in _LAYER_STATE for k in delta) \
            and dials.get("exploit", "hero") is not None:
        _, kw = CB.parse_dials({**dials, **delta})
        return ("layer", kw["exploit"])
    return ("full",)


_REG: dict = {}


def _register(dials: dict, shadow: tuple = (), name: str = CAND):
    key = (json.dumps(dials, sort_keys=True), tuple(shadow), name)
    if _REG.get(name) != key:
        CB.register(name, dials=dict(dials), shadow=tuple(shadow))
        _REG[name] = key


def _job_base(args):
    field, dials, donors, variants, keys, pay = args
    setup_process()
    from hyperion.core.types import Rules

    rules = Rules(payouts=PAYOUTS[pay]) if PAYOUTS[pay] else None
    vspecs = []
    for name, delta in variants:
        c = classify_variant(dials, delta)
        if c[0] == "member":
            vspecs.append(("member", c[1], CB.variant_member(c[1], c[2], c[3]), None))
        elif c[0] == "layer":
            vspecs.append(("layer", None, None, c[1]))
        else:
            vspecs.append(("full", None, None, None))
    shadow = list(dict.fromkeys(CB.DONORS[d][0] for d in donors))
    shadow += [vm for kind, _, vm, _ in vspecs if kind == "member"]
    _register(dials, tuple(shadow))
    rec = Recorder(donors, vspecs)
    out = []
    t0 = time.time()
    from hyperion.sim import bestiary as B

    cls = B.REGISTRY[CAND]

    class Tapped(cls):
        def __init__(self, seed=None):
            super().__init__(seed)
            rec.bind(self.impl.core)

    B.REGISTRY[CAND + "_t"] = Tapped
    for t, rot in keys:
        rec.reset()
        pts, st, b = play(field, CAND + "_t", t, rot, rules)
        out.append((t, rot, pts, sorted(rec.cells), rec.dec, {f"{s}.{d}": v for (s, d), v in rec.dis.items()},
                    dict(b.impl.core.counts), st.over_budget, st.exceptions, sorted(rec.vflags)))
    return out, time.time() - t0, os.getloadavg()[0]


def _job_play(args):
    field, dials, keys, pay, tag = args
    setup_process()
    from hyperion.core.types import Rules

    rules = Rules(payouts=PAYOUTS[pay]) if PAYOUTS[pay] else None
    _register(dials)
    out = []
    t0 = time.time()
    for t, rot in keys:
        pts, st, b = play(field, CAND, t, rot, rules)
        out.append((t, rot, pts, dict(b.impl.core.counts), st.over_budget, st.exceptions))
    return tag, out, time.time() - t0, os.getloadavg()[0]


# --------------------------------------------------------------------------------------------- files
def load_dials(a) -> dict:
    """The composite measured as the base: --dials (JSON, inline or a file) with --route on top."""
    d = {}
    if getattr(a, "dials", None):
        d = json.load(open(a.dials)) if os.path.exists(a.dials) else json.loads(a.dials)
    if a.route:
        d["route"] = a.route
    d["route"] = route_str(parse_route(d.get("route", "")))
    return d


def stage_dir(out: str, field: str, seeds: str, pay: str, dials: dict) -> str:
    r = (route_str(parse_route(dials.get("route", ""))) or "base").replace("=", "~").replace(",", "+")
    rest = {k: v for k, v in dials.items() if k != "route"}
    if rest:
        import hashlib

        r += "~" + hashlib.sha1(json.dumps(rest, sort_keys=True).encode()).hexdigest()[:8]
    d = os.path.join(out, f"{field}.{pay}.{seeds.replace(':', '-')}", r)
    os.makedirs(d, exist_ok=True)
    return d


def parse_seeds(s: str):
    lo, hi = (int(x) for x in s.split(":"))
    return range(lo, hi)


def load_base(d: str):
    with open(os.path.join(d, "base.json")) as fh:
        return json.load(fh)


def chunks(keys, n):
    for i in range(0, len(keys), n):
        yield keys[i:i + n]


# --------------------------------------------------------------------------------------------- commands
def load_variants(a) -> dict:
    if not getattr(a, "variants", None):
        return {}
    return json.load(open(a.variants)) if os.path.exists(a.variants) else json.loads(a.variants)


def cmd_base(a):
    dials = load_dials(a)
    donors = [d.strip() for d in a.donors.split(",") if d.strip()]
    variants = load_variants(a)
    d = stage_dir(a.out, a.field, a.seeds, a.payouts, dials)
    path = os.path.join(d, "base.json")
    if os.path.exists(path) and not a.force:
        print("exists", path)
        return
    keys = [(t, r) for t in parse_seeds(a.seeds) for r in range(8)]
    jobs = [(a.field, dials, donors, list(variants.items()), k, a.payouts) for k in chunks(keys, a.chunk)]
    rows = []
    t0 = time.time()
    loads = []
    with Pool(a.workers) as p:
        for out, secs, ld in p.imap_unordered(_job_base, jobs):
            rows += out
            loads.append(ld)
    rows.sort(key=lambda r: (r[0], r[1]))
    res = {"field": a.field, "seeds": a.seeds, "payouts": a.payouts, "route": parse_route(dials["route"]),
           "dials": dials, "donors": donors, "variants": variants,
           "kinds": {n: classify_variant(dials, v)[0] for n, v in variants.items()},
           "sections": list(SECTIONS), "rows": rows, "secs": time.time() - t0, "load": [min(loads), max(loads)],
           "when": time.strftime("%H:%M")}
    with open(path + ".tmp", "w") as fh:
        json.dump(res, fh)
    os.replace(path + ".tmp", path)
    print(f"base {a.field} {dials}: {len(rows)} rotations in {res['secs']:.0f}s, load {res['load']}")


def per_seed(rows_pts: dict, seeds):
    """{(t, rot): pts} -> per-seed means in seed order."""
    return [sum(rows_pts[(t, r)] for r in range(8)) / 8 for t in seeds]


def ci(xs):
    n = len(xs)
    m = sum(xs) / n
    v = sum((x - m) ** 2 for x in xs) / (n - 1) if n > 1 else 0.0
    return m, 1.96 * math.sqrt(v / n)


def _base_dials(base) -> dict:
    return base.get("dials") or {"route": route_str(base["route"])}


def _run_replays(a, todo):
    """todo: [(tag, path, need, dials)] -> replays every needed rotation under its dials and writes each file."""
    jobs = []
    for tag, path, need, dials in todo:
        for k in chunks(sorted(need), a.chunk):
            jobs.append((a.field, dials, k, a.payouts, tag))
    jobs.sort(key=lambda j: -len(j[2]))  # longest first; the cells' chunks interleave so load falls evenly
    got = {tag: {} for tag, _, _, _ in todo}
    t0 = time.time()
    if jobs:
        with Pool(a.workers) as p:
            for tag, out, secs, ld in p.imap_unordered(_job_play, jobs):
                for t, rot, pts, counts, tmo, exc in out:
                    got[tag][(t, rot)] = (pts, counts, tmo, exc)
    for tag, path, need, dials in todo:
        g = got[tag]
        res = {"cell": tag, "dials": dials, "replayed": len(need), "rows": [[t, r, *v] for (t, r), v in sorted(g.items())],
               "secs": time.time() - t0}
        with open(path, "w") as fh:
            json.dump(res, fh)
    return time.time() - t0


def cmd_cells(a):
    dials = load_dials(a)
    route = parse_route(dials["route"])
    d = stage_dir(a.out, a.field, a.seeds, a.payouts, dials)
    base = load_base(d)
    donors = base["donors"]
    variants = base.get("variants", {})
    vnames = list(variants)
    if a.cells == "all":
        cells = [(s, di) for s in range(len(SECTIONS)) for di in range(len(donors))] + [("var", n) for n in vnames]
    else:
        cells = []
        for c in a.cells.split(","):
            sname, dn = c.split(":", 1)
            cells.append(("var", dn) if sname == "var" else (SECTIONS.index(sname), donors.index(dn)))
    rows = {(r[0], r[1]): r for r in base["rows"]}
    todo = []
    for s, di in cells:
        if s == "var":
            name = f"var.{di}"
            vi = vnames.index(di)
            need = [k for k, r in rows.items() if a.full or (len(r) > 9 and vi in r[9])]
            ndials = {**dials, **variants[di]}
        else:
            if SECTIONS[s] in route and route[SECTIONS[s]] == donors[di]:
                continue
            name = f"{SECTIONS[s]}.{donors[di]}"
            need = [k for k, r in rows.items() if a.full or [s, di] in r[3]]
            ndials = {**dials, "route": route_str({**route, SECTIONS[s]: donors[di]})}
        path = os.path.join(d, f"cell.{name}.json")
        if os.path.exists(path) and not a.force:
            continue
        todo.append((name, path, need, ndials))
    secs = _run_replays(a, todo)
    print(f"cells {a.field}: {len(todo)} cells, {sum(len(n) for _, _, n, _ in todo)} rotations replayed, {secs:.0f}s")


def cmd_joint(a):
    """A changed composite (--to-route / --to-dials) against the base run's: replay the union of its cells' and
    variants' disagreeing rotations (every rotation when a change was not recorded)."""
    dials = load_dials(a)
    d = stage_dir(a.out, a.field, a.seeds, a.payouts, dials)
    base = load_base(d)
    donors = base["donors"]
    variants = base.get("variants", {})
    route = parse_route(dials["route"])
    new = dict(dials)
    extra = json.loads(a.to_dials) if a.to_dials else {}
    new.update(extra)
    to_route = parse_route(a.to_route) if a.to_route else route
    new["route"] = route_str(to_route)
    add = {k: v for k, v in to_route.items() if route.get(k) != v}
    full = a.full or any(route.get(k) and k not in to_route for k in route)  # a section put back on the base
    cells = []
    for k, v in add.items():
        if v not in donors:
            full = True
        else:
            cells.append([SECTIONS.index(k), donors.index(v)])
    vis = []
    for k, v in extra.items():
        hit = [n for n, delta in variants.items() if delta == {k: v}]
        if not hit:
            full = True
        else:
            vis.append(list(variants).index(hit[0]))
    need = sorted((r[0], r[1]) for r in base["rows"]
                  if full or any(c in r[3] for c in cells) or (len(r) > 9 and any(v in r[9] for v in vis)))
    tag = "joint." + hashlib_tag(new)
    path = os.path.join(d, f"{tag}.json")
    secs = _run_replays(a, [(tag, path, need, new)])
    with open(path) as fh:
        res = json.load(fh)
    m, h = delta(base, res, parse_seeds(a.seeds))
    print(f"joint {a.field} {new} vs {dials}: {m:+.3f} ± {h:.3f} ({len(need)} of {len(base['rows'])} rotations replayed, "
          f"{secs:.0f}s)")


def hashlib_tag(dials: dict) -> str:
    import hashlib

    return hashlib.sha1(json.dumps(dials, sort_keys=True).encode()).hexdigest()[:10]


def delta(base, cell, seeds):
    bp = {(r[0], r[1]): r[2] for r in base["rows"]}
    cp = dict(bp)
    for r in cell["rows"]:
        cp[(r[0], r[1])] = r[2]
    b = per_seed(bp, seeds)
    c = per_seed(cp, seeds)
    return ci([x - y for x, y in zip(c, b)])


def cmd_report(a):
    dials = load_dials(a)
    route = parse_route(dials["route"])
    d = stage_dir(a.out, a.field, a.seeds, a.payouts, dials)
    base = load_base(d)
    donors = base["donors"]
    seeds = parse_seeds(a.seeds)
    bp = {(r[0], r[1]): r[2] for r in base["rows"]}
    bm, bh = ci(per_seed(bp, seeds))
    dec = [0] * len(SECTIONS)
    dis: dict = {}
    for r in base["rows"]:
        for i, v in enumerate(r[4]):
            dec[i] += v
        for k, v in r[5].items():
            dis[k] = dis.get(k, 0) + v
    tot = sum(dec)
    res = {"field": a.field, "seeds": a.seeds, "dials": dials, "base_route": route, "base_pts": [bm, bh], "cells": {},
           "variants": {}}
    print(f"## {a.field} ({a.seeds}, {a.payouts}), base {dials if dials != {'route': ''} else 'hybrid3_x'}: "
          f"{bm:.3f} ± {bh:.3f}")
    for s, sname in enumerate(SECTIONS):
        rows = []
        for di, dn in enumerate(donors):
            p = os.path.join(d, f"cell.{sname}.{dn}.json")
            if not os.path.exists(p):
                continue
            with open(p) as fh:
                cell = json.load(fh)
            m, h = delta(base, cell, seeds)
            n_dis = dis.get(f"{s}.{di}", 0)
            rows.append((m, h, dn, cell["replayed"], n_dis))
            res["cells"][f"{sname}.{dn}"] = {"d": m, "ci": h, "replayed": cell["replayed"], "disagree": n_dis,
                                            "decisions": dec[s]}
        if not rows:
            continue
        rows.sort(key=lambda x: -x[0])
        print(f"\n{sname} ({100 * dec[s] / max(1, tot):.1f}% of decisions)")
        for i, (m, h, dn, rep, nd) in enumerate(rows, 1):
            flag = " **" if m - h > 0 else (" (worse)" if m + h < 0 else "")
            print(f"  {i}. {dn}: {m:+.3f} ± {h:.3f}{flag}  [differs on {100 * nd / max(1, dec[s]):.1f}% of its decisions, "
                  f"{rep} rotations replayed]")
    vrows = []
    for n, delta_d in base.get("variants", {}).items():
        p = os.path.join(d, f"cell.var.{n}.json")
        if not os.path.exists(p):
            continue
        with open(p) as fh:
            cell = json.load(fh)
        m, h = delta(base, cell, seeds)
        vrows.append((m, h, n, delta_d, cell["replayed"]))
        res["variants"][n] = {"d": m, "ci": h, "dials": delta_d, "replayed": cell["replayed"]}
    if vrows:
        print("\ndial changes")
        for i, (m, h, n, dd, rep) in enumerate(sorted(vrows, key=lambda x: -x[0]), 1):
            flag = " **" if m - h > 0 else (" (worse)" if m + h < 0 else "")
            print(f"  {i}. {n} {dd}: {m:+.3f} ± {h:.3f}{flag}  [{rep} rotations replayed]")
    with open(os.path.join(d, "report.json"), "w") as fh:
        json.dump(res, fh, indent=1)


# --------------------------------------------------------------------------------------------- full paired runs
def _spec_bot(name: str, spec: dict) -> str:
    """The simulator name for a spec: a registered bot ({"bot": "hybrid3_x"}) or a composite (route and dials)."""
    if "bot" in spec:
        return spec["bot"]
    nm = "cmp_" + name
    if "dials" in spec:
        CB.register(nm, dials=dict(spec["dials"]))
        return nm
    CB.register(nm, spec.get("route", ""), exploit=spec.get("exploit", "hero"),
                base_overrides=dict(spec.get("base_overrides", {})), hero_overrides=dict(spec.get("hero_overrides", {})))
    return nm


def _job_paired(args):
    field, name, spec, off, n, pay, mode, as_built = args
    setup_process(mode, as_built)
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.runner import run_tournament

    rules = Rules(payouts=PAYOUTS[pay]) if PAYOUTS[pay] else None
    CB.COUNTS.clear()
    nm = _spec_bot(name, spec)
    l0 = os.getloadavg()[0]
    t0 = time.time()
    rep = run_tournament(B.field_names(f"{field}@{nm}"), n, seed=SEED, rotate=True, mode=mode, rules=rules,
                         hero_config=B.HERO_CONFIG, table_offset=off)
    b = rep.bots[nm]
    st = b.stats
    return name, off, {"samples": b.samples, "places": b.places, "seats": b.seats, "busts": b.busts,
                       "hist": st.hist, "calls": st.calls, "tmo": st.over_budget, "exc": st.exceptions,
                       "ill": st.illegal, "counts": dict(CB.COUNTS), "load": [l0, os.getloadavg()[0]],
                       "secs": time.time() - t0, "tables": rep.tables}


def cmd_paired(a):
    with open(a.specs) as fh:
        specs = json.load(fh)
    names = list(specs)
    lo, hi = (int(x) for x in a.seeds.split(":"))
    path = os.path.join(a.out, f"paired.{a.field}.{a.payouts}.{a.mode}.{lo}-{hi}.{a.tag}.json")
    os.makedirs(a.out, exist_ok=True)
    done = {}
    if os.path.exists(path) and not a.force:
        with open(path) as fh:
            done = json.load(fh)["res"]
    jobs = [(a.field, nm, specs[nm], off, min(a.chunk, hi - off), a.payouts, a.mode, a.as_built)
            for off in range(lo, hi, a.chunk) for nm in names if str(off) not in done.get(nm, {})]
    res = {nm: dict(done.get(nm, {})) for nm in names}
    t0 = time.time()
    if jobs:
        with Pool(a.workers) as p:
            for nm, off, o in p.imap_unordered(_job_paired, jobs):
                res[nm][str(off)] = o
    with open(path + ".tmp", "w") as fh:
        json.dump({"field": a.field, "seeds": a.seeds, "payouts": a.payouts, "mode": a.mode, "specs": specs,
                   "as_built": a.as_built, "res": res, "secs": time.time() - t0}, fh)
    os.replace(path + ".tmp", path)
    print(paired_table(path))


def _flat(r, key="samples"):
    return [x for off in sorted(r, key=int) for x in r[off][key]]


def paired_table(path: str) -> str:
    from hyperion.sim.engine import BotStats

    with open(path) as fh:
        d = json.load(fh)
    names = list(d["specs"])
    ref = names[0]
    rx = _flat(d["res"][ref])
    loads = [x for nm in names for off in d["res"][nm] for x in d["res"][nm][off]["load"]]
    out = [f"{d['field']} ({d['payouts']}, {d['mode']}{', as built' if d['as_built'] else ''}), seeds {d['seeds']} x 8, "
           f"load {min(loads):.0f}-{max(loads):.0f}; paired against {ref}", "",
           "| # | candidate | points ± 95% | - " + ref + " (paired) | p50 / p99 us | timeouts | exc / ill |",
           "|---|---|---|---|---|---|---|"]
    rows = []
    for nm in names:
        r = d["res"][nm]
        xs = _flat(r)
        m, h = ci(xs)
        dm, dh = ci([x - y for x, y in zip(xs, rx)]) if nm != ref else (0.0, 0.0)
        st = BotStats(nm)
        st.hist = [sum(r[off]["hist"][i] for off in r) for i in range(len(next(iter(r.values()))["hist"]))]
        st.calls = sum(r[off]["calls"] for off in r)
        tmo = sum(r[off]["tmo"] for off in r)
        exc = sum(r[off]["exc"] for off in r)
        ill = sum(r[off]["ill"] for off in r)
        rows.append((m, nm, h, dm, dh, st.percentile_us(0.5), st.percentile_us(0.99), tmo, st.calls, exc, ill))
    for i, (m, nm, h, dm, dh, p50, p99, tmo, calls, exc, ill) in enumerate(sorted(rows, key=lambda x: -x[0]), 1):
        dd = "-" if nm == ref else f"{dm:+.3f} ± {dh:.3f}" + (" **" if abs(dm) > dh else "")
        out.append(f"| {i} | {nm} | {m:.3f} ± {h:.3f} | {dd} | {p50:.0f} / {p99:.0f} | {tmo} ({100 * tmo / max(1, calls):.3f}%) "
                   f"| {exc} / {ill} |")
    return "\n".join(out)


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=("base", "cells", "joint", "report", "paired", "table"))
    p.add_argument("--field", required=True)
    p.add_argument("--seeds", default="0:200")
    p.add_argument("--payouts", default="lin", choices=sorted(PAYOUTS))
    p.add_argument("--route", default="", help="the base composite's route (on top of --dials)")
    p.add_argument("--dials", default="", help="the base composite's dials, JSON inline or a file (route, r3.*, ...)")
    p.add_argument("--variants", default="", help="base: dial changes to record, JSON {name: {dial: value}}")
    p.add_argument("--to-route", default="", help="joint: the route measured against the base's")
    p.add_argument("--to-dials", default="", help="joint: dials changed on top of the base's (JSON)")
    p.add_argument("--donors", default=",".join(DONORS))
    p.add_argument("--cells", default="all")
    p.add_argument("--out", required=True)
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--chunk", type=int, default=16)
    p.add_argument("--full", action="store_true", help="replay every rotation (checks the shortcut)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--specs", help="paired: JSON file {name: {bot | route, exploit, base_overrides, hero_overrides}}; "
                                   "the first is the reference")
    p.add_argument("--tag", default="run", help="paired: names the output file")
    p.add_argument("--mode", default="model", choices=("model", "strict"))
    p.add_argument("--as-built", action="store_true", help="paired: rival 2 keeps its wall-clock sampler")
    a = p.parse_args(argv)
    if a.cmd == "table":
        print(paired_table(a.specs))
        return
    {"base": cmd_base, "cells": cmd_cells, "joint": cmd_joint, "report": cmd_report, "paired": cmd_paired}[a.cmd](a)


if __name__ == "__main__":
    main()
