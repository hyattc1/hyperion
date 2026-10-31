"""Parameter sweep for the hero: one-at-a-time changes from a base Config, every setting played on the
same duplicate-dealt seed set across several fields, in parallel, with paired deltas against the base.

    .venv/bin/python tools/sweep.py spec.json --tables 100 --seed 7 --workers 8 --out scratch/sweep.json

spec.json:
    {"base": {"preflop.patience_deep": 0.1},                    # dotted hero Config overrides for every run
     "fields": {"base": "hero,tag,nit,naive,station,maniac,random,allin", "weak": "hero,station,..."},
     "sweep": {"preflop.three_bet_frac": [0.03, 0.08], "postflop.value_tier": [5]},   # one lever at a time
     "settings": {"gate30": {"postflop.icm_gate_frac": 0.3, "postflop.icm_margin": 0.1}}}  # named combos

Every (setting, field) plays `--tables` seeds times eight rotations, split into `--chunks` contiguous
slices so the pool stays busy. The sample unit is one table seed (its rotations averaged), the same
seeds for every setting, so the delta against the base is paired: mean of per-seed differences, with
its own 95% interval. "Keep" a lever when its paired delta is positive on every field.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyperion.sim.runner import run_tournament  # noqa: E402


def _job(args):
    setting, field, names, tables, seed, offset, config = args
    rep = run_tournament(names.split(","), tables, seed, rotate=True, mode="strict", hero_config=config,
                         table_offset=offset)
    out = {}
    for nm, b in rep.bots.items():
        out[nm] = {"samples": b.samples, "seats": b.seats, "busts": b.busts, "places": b.places,
                   "tmo": b.stats.over_budget, "exc": b.stats.exceptions, "ill": b.stats.illegal}
    return setting, field, offset, out, rep.hands


def _merge(parts):
    """Chunks of one (setting, field) in offset order -> one dict per bot."""
    merged = {}
    for _, _, _, out, _ in sorted(parts, key=lambda p: p[2]):
        for nm, b in out.items():
            m = merged.setdefault(nm, {"samples": [], "seats": 0, "busts": 0, "places": None, "tmo": 0, "exc": 0, "ill": 0})
            m["samples"] += b["samples"]
            m["seats"] += b["seats"]
            m["busts"] += b["busts"]
            m["places"] = b["places"] if m["places"] is None else [x + y for x, y in zip(m["places"], b["places"])]
            m["tmo"] += b["tmo"]
            m["exc"] += b["exc"]
            m["ill"] += b["ill"]
    return merged


def mean_ci(xs):
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, 1.96 * math.sqrt(var / n)


def settings_from_spec(spec: dict) -> dict[str, dict]:
    base = dict(spec.get("base", {}))
    out = {"base": base}
    for key, values in spec.get("sweep", {}).items():
        for v in values:
            cfg = dict(base)
            cfg[key] = v
            out[f"{key}={json.dumps(v)}"] = cfg
    for name, over in spec.get("settings", {}).items():
        cfg = dict(base)
        cfg.update(over)
        out[name] = cfg
    return out


def format_results(results: dict, fields: dict, settings: dict, rival: str = "tag") -> str:
    lines = []
    base = results["base"]
    head = f"{'setting':<44} {'field':<7} {'hero':>6} {'±':>5} {'bust%':>5} {'tmo':>4} {rival:>6} {'Δhero':>6} {'±':>5} {'Δ(h-' + rival + ')':>8}"
    lines.append(head)
    summary = {}
    for name in settings:
        res = results.get(name)
        if not res:
            continue
        worst = None
        for field in fields:
            r = res.get(field)
            if not r or "hero" not in r:
                continue
            h = r["hero"]
            hm, hc = mean_ci(h["samples"])
            bust = 100 * h["busts"] / h["seats"] if h["seats"] else 0.0
            rv = r.get(rival)
            rm = sum(rv["samples"]) / len(rv["samples"]) if rv and rv["samples"] else float("nan")
            b = base[field]["hero"]["samples"]
            d, dc = mean_ci([x - y for x, y in zip(h["samples"], b)])
            if rv and rival in base[field]:
                br = base[field][rival]["samples"]
                dd, _ = mean_ci([(x - y) - (bx - by) for x, y, bx, by in zip(h["samples"], rv["samples"], b, br)])
            else:
                dd = float("nan")
            lines.append(f"{name[:44]:<44} {field:<7} {hm:>6.3f} {hc:>5.3f} {bust:>5.1f} {h['tmo']:>4} {rm:>6.3f} {d:>+6.3f} {dc:>5.3f} {dd:>+8.3f}")
            worst = d if worst is None else min(worst, d)
        summary[name] = worst
    lines.append("")
    lines.append("worst paired Δhero across fields (positive = helps everywhere):")
    for name, w in sorted(summary.items(), key=lambda kv: -(kv[1] if kv[1] is not None else -9)):
        if w is not None:
            lines.append(f"  {w:+.3f}  {name}")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("spec")
    ap.add_argument("--tables", type=int, default=100, help="table seeds per (setting, field); x8 rotations")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--workers", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--chunks", type=int, default=4, help="slices per (setting, field) for the pool")
    ap.add_argument("--out", default=None, help="write raw results json here")
    ap.add_argument("--rival", default="tag", help="the bot to report the paired hero-minus-rival delta against")
    a = ap.parse_args(argv)
    with open(a.spec) as f:
        spec = json.load(f)
    fields = spec["fields"]
    settings = settings_from_spec(spec)
    jobs = []
    per = max(1, a.tables // a.chunks)
    offsets = list(range(0, a.tables, per))
    for name, cfg in settings.items():
        for field, names in fields.items():
            for off in offsets:
                jobs.append((name, field, names, min(per, a.tables - off), a.seed, off, cfg))
    print(f"{len(settings)} settings x {len(fields)} fields x {len(offsets)} chunks = {len(jobs)} jobs on {a.workers} workers",
          file=sys.stderr)
    t0 = time.perf_counter()
    parts: dict[tuple, list] = {}
    done = 0
    with Pool(a.workers) as pool:
        for part in pool.imap_unordered(_job, jobs):
            parts.setdefault((part[0], part[1]), []).append(part)
            done += 1
            if done % max(1, len(jobs) // 10) == 0:
                print(f"  {done}/{len(jobs)} jobs, {time.perf_counter() - t0:.0f}s", file=sys.stderr)
    results: dict = {}
    for (name, field), ps in parts.items():
        results.setdefault(name, {})[field] = _merge(ps)
    print(format_results(results, fields, settings, a.rival))
    print(f"{time.perf_counter() - t0:.0f}s", file=sys.stderr)
    if a.out:
        with open(a.out, "w") as f:
            json.dump({"spec": spec, "tables": a.tables, "seed": a.seed, "results": results}, f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
