#!/usr/bin/env python
"""The honest variant board: F against the generic variant-aware field on every catalog entry, beside the twist-blind
`realistic` field on the same deals.

    .venv/bin/python tools/aware_board.py --set screen --workers 2                    (every catalog entry, 200 x 8)
    .venv/bin/python tools/aware_board.py --set 10000:10100 --variants bounty,short_deck
    .venv/bin/python tools/aware_board.py --variants submission/tonight.py:variant --fields generic_aware

Per entry and field: F's points (the shipped composite, or --spec), its rank among the field's bots, and its margin
over the best other bot (paired per seed: F minus that bot, 95% interval), and on the generic field also over the best
of the three generic bots (gen_mc, gen_tag, gen_pushfold; hyperion/sim/generic.py). `shrink` is F's margin over the
best opponent on realistic minus the same on generic_aware: how much of F's lead disappears once the twist-reading
seats read it. Also every generic bot's exceptions, illegal actions and engine-measured p50 / p99.

Model mode at fixed speed, eight rotations per seed (tools/swap.py's setup_process), so it replays exactly. Results are
cached per (spec, code version, field, variant, seed chunk) under --out, as tools/climb_accept.py does; every bot's
per-seed points are kept (climb_accept keeps only the candidate's).
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location("climb_accept_tool", os.path.join(_HERE, "climb_accept.py"))
CA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CA)
SW = CA.SW

GENERIC = ("gen_mc", "gen_tag", "gen_pushfold")
CHUNK = 25


def _job(args):
    key, spec, field, variant, off, n = args
    SW.setup_process("model")
    from hyperion.compose import bot as CB
    from hyperion.drills import variants as V
    from hyperion.sim import bestiary as B
    from hyperion.sim.runner import run_tournament

    CB.COUNTS.clear()
    nm = SW._spec_bot("board", spec)
    v = V.get(variant, seed=SW.SEED) if variant else None
    t0 = time.time()
    rep = run_tournament(B.field_names(f"{field}@{nm}"), n, seed=SW.SEED, rotate=True, mode="model",
                         hero_config=B.HERO_CONFIG, table_offset=off, variant=v)
    bots = {}
    for name, b in rep.bots.items():
        st = b.stats
        bots["F" if name == nm else name] = {
            "samples": b.samples, "exc": st.exceptions + st.safe_err, "ill": st.illegal, "tmo": st.over_budget,
            "calls": st.calls, "p50": st.percentile_us(0.5), "p99": st.percentile_us(0.99), "max_us": st.max_ns / 1000}
    return key, (field, variant, off), {"bots": bots, "secs": time.time() - t0, "load": os.getloadavg()[0]}


def cell_path(out: str, key: str, field: str, variant, off: int) -> str:
    return os.path.join(out, key, f"{field}.{CA._variant_tag(variant)}.{off}.json")


def run(out: str, keys: dict, spec: dict, cells: list, lo: int, hi: int, workers: int) -> None:
    jobs = []
    for field, variant in cells:
        for off in range(lo, hi, CHUNK):
            if not os.path.exists(cell_path(out, keys[field], field, variant, off)):
                jobs.append((keys[field], spec, field, variant, off, min(CHUNK, hi - off)))
    if not jobs:
        return
    for key in set(keys.values()):
        os.makedirs(os.path.join(out, key), exist_ok=True)
        with open(os.path.join(out, key, "spec.json"), "w") as fh:
            json.dump(spec, fh)
    done = 0
    with Pool(workers, maxtasksperchild=2) as p:
        for k, (field, variant, off), res in p.imap_unordered(_job, jobs):
            path = cell_path(out, k, field, variant, off)
            with open(path + ".tmp", "w") as fh:
                json.dump(res, fh)
            os.replace(path + ".tmp", path)
            done += 1
            print(f"[{time.strftime('%H:%M:%S')}] {done}/{len(jobs)} {field} {variant} {off} "
                  f"{res['secs']:.0f}s load {res['load']:.1f}", flush=True)


def gather(out: str, key: str, field: str, variant, lo: int, hi: int) -> dict:
    agg: dict = {}
    for off in range(lo, hi, CHUNK):
        with open(cell_path(out, key, field, variant, off)) as fh:
            r = json.load(fh)
        for name, b in r["bots"].items():
            a = agg.setdefault(name, {"samples": [], "exc": 0, "ill": 0, "tmo": 0, "calls": 0, "p50": 0.0, "p99": 0.0,
                                      "max_us": 0.0})
            a["samples"] += b["samples"]
            for k in ("exc", "ill", "tmo", "calls"):
                a[k] += b[k]
            for k in ("p50", "p99", "max_us"):
                a[k] = max(a[k], b[k])
    for a in agg.values():
        a["mean"] = sum(a["samples"]) / len(a["samples"])
    return agg


def margin(agg: dict, among) -> tuple:
    """F minus the best of `among` (by mean): (bot, mean diff, 95% half-width of the paired per-seed difference)."""
    best = max((n for n in among if n in agg), key=lambda n: agg[n]["mean"])
    d = [f - b for f, b in zip(agg["F"]["samples"], agg[best]["samples"])]
    m = sum(d) / len(d)
    v = sum((x - m) ** 2 for x in d) / (len(d) - 1) if len(d) > 1 else 0.0
    return best, m, 1.96 * math.sqrt(v / len(d))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--set", default="screen", help="screen (10000-10199) or lo:hi; never held-out seeds here")
    p.add_argument("--variants", default="all", help="catalog entries (comma-separated), file specs, or all")
    p.add_argument("--fields", default="generic_aware,realistic")
    p.add_argument("--spec", default="", help="the bot in Hero's seat: a climb_accept spec ('' = F as shipped)")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--out", default=os.path.join(ROOT, "scratch", "aware_board"))
    p.add_argument("--json", default=None)
    p.add_argument("--field-set", action="append", default=[], metavar="FIELD=SET",
                   help="play FIELD on its own seed set (lo:hi), e.g. the twist-blind field on fewer seeds")
    p.add_argument("--field-version", action="append", default=[], metavar="FIELD=TAG",
                   help="key FIELD's cells by TAG instead of the code version: a field whose bots and the spec are the "
                        "same at two commits (realistic before and after an opponent-only change) is played once")
    a = p.parse_args(argv)
    from hyperion.drills import variants as V

    lo, hi = CA.seed_range(a.set)
    if lo >= 20000:
        raise SystemExit("held-out seeds (20000+) are not for the board; use screen seeds")
    spec = CA.resolve(CA.load_spec(a.spec))
    version = CA.code_version()
    variants = V.catalog_names() if a.variants == "all" else a.variants.split(",")
    fields = a.fields.split(",")
    tags = dict(fv.split("=", 1) for fv in a.field_version)
    seeds = {f: CA.seed_range(r) for f, r in (fs.split("=", 1) for fs in a.field_set)}
    keys = {f: CA.spec_key(spec, tags.get(f, version)) for f in fields}
    t0 = time.time()
    if "generic_aware" in fields:
        from hyperion.sim import generic as GEN

        for v in variants:
            t1 = time.time()
            path, _ = GEN.prepare(v, workers=a.workers)
            if time.time() - t1 > 1:
                print(f"generic table for {v}: {os.path.relpath(path, ROOT)} ({time.time() - t1:.1f} s)", flush=True)
    for f in fields:
        f_lo, f_hi = seeds.get(f, (lo, hi))
        run(a.out, keys, spec, [(f, v) for v in variants], f_lo, f_hi, a.workers)
    rows = []
    for v in variants:
        row = {"variant": v}
        diffs = {}
        for f in fields:
            agg = gather(a.out, keys[f], f, v, *seeds.get(f, (lo, hi)))
            ranked = sorted(agg, key=lambda n: -agg[n]["mean"])
            others = [n for n in agg if n != "F"]
            best, m, h = margin(agg, others)
            row[f] = {"F": agg["F"]["mean"], "rank": ranked.index("F") + 1, "n_bots": len(agg), "best": best,
                      "margin": m, "ci": h, "n": len(agg["F"]["samples"]),
                      "bots": {n: {k: agg[n][k] for k in ("mean", "exc", "ill", "tmo", "calls", "p50", "p99", "max_us")}
                               for n in agg}}
            diffs[f] = [x - y for x, y in zip(agg["F"]["samples"], agg[best]["samples"])]
            if f == "generic_aware":
                gb, gm, gh = margin(agg, [n for n in GENERIC if n in agg])
                row[f].update({"best_gen": gb, "gen_margin": gm, "gen_ci": gh})
        if "generic_aware" in diffs and "realistic" in diffs:
            # the shrink on the seeds both fields played: F's margin over its best opponent, realistic minus generic
            d = [r - g for r, g in zip(diffs["realistic"], diffs["generic_aware"])]
            m = sum(d) / len(d)
            h = 1.96 * math.sqrt(sum((x - m) ** 2 for x in d) / (len(d) - 1) / len(d)) if len(d) > 1 else 0.0
            row["shrink"] = {"mean": m, "ci": h, "n": len(d)}
        rows.append(row)
    print(f"# aware_board: set {a.set} ({lo}-{hi - 1}) x 8 rotations, code {version}, spec {json.dumps(spec)[:80]}, "
          f"{(time.time() - t0) / 60:.1f} min\n")
    if "generic_aware" in fields and "realistic" in fields:
        print("| variant | F generic | rank | margin over best generic bot | margin over best opponent | "
              "F realistic | rank | margin over best opponent | shrink (paired seeds) |")
        print("|---|---|---|---|---|---|---|---|---|")
        for r in sorted(rows, key=lambda r: -r["shrink"]["mean"]):
            g, z, k = r["generic_aware"], r["realistic"], r["shrink"]
            print(f"| {r['variant']} | {g['F']:.3f} | {g['rank']} | {g['gen_margin']:+.3f} ± {g['gen_ci']:.3f} "
                  f"({g['best_gen']}) | {g['margin']:+.3f} ± {g['ci']:.3f} ({g['best']}) | {z['F']:.3f} | "
                  f"{z['rank']} | {z['margin']:+.3f} ± {z['ci']:.3f} ({z['best']}) | {k['mean']:+.3f} ± {k['ci']:.3f} "
                  f"(n {k['n']}) |")
    else:
        for f in fields:
            print(f"\n## {f}\n\n| variant | F | rank | margin over best opponent |\n|---|---|---|---|")
            for r in rows:
                g = r[f]
                print(f"| {r['variant']} | {g['F']:.3f} | {g['rank']}/{g['n_bots']} | {g['margin']:+.3f} ± "
                      f"{g['ci']:.3f} ({g['best']}) |")
    if "generic_aware" in fields:
        print("\n| variant | " + " | ".join(f"{b} pts / exc / ill / p50 / p99 us" for b in GENERIC) + " |")
        print("|---|" + "---|" * len(GENERIC))
        for r in rows:
            cells = []
            for b in GENERIC:
                x = r["generic_aware"]["bots"].get(b)
                cells.append("-" if x is None else f"{x['mean']:.2f} / {x['exc']} / {x['ill']} / {x['p50']:.0f} / "
                                                   f"{x['p99']:.0f}")
            print(f"| {r['variant']} | " + " | ".join(cells) + " |")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"set": a.set, "seeds": [lo, hi], "version": version, "spec": spec, "rows": rows}, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
