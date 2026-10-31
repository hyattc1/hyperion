#!/usr/bin/env python
"""Regenerate every table under tables/ from a Rules object. Stdlib + multiprocessing only.

    python tools/gen_tables.py --rules default --samples 20000 --out tables/
    python tools/gen_tables.py --rules variant.json --variant-check     # time budget per table
    python tools/gen_tables.py --rules default --skip-matrix --out /tmp/t

Outputs (see tables/README.md): preflop_equity.json, preflop_rank.json, hu_matrix.json,
flop_strength.json, hole_classes.json (only when hole_cards != 2), meta.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from multiprocessing import Pool, cpu_count
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion import tablegen as tg  # noqa: E402
from hyperion.core.types import Rules  # noqa: E402

MAX_OPP = 7


def load_rules(spec: str) -> Rules:
    if spec == "default":
        return Rules()
    with open(spec) as f:
        return tg.rules_from_dict(json.load(f))


def _dump(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
        f.write("\n")


def _matrix_samples(samples: int) -> int:
    return max(20, samples // 20)


def gen_preflop(pool: Pool, classes: dict, samples: int, seed: int, out: Path) -> tuple[dict, dict]:
    per_job = max(50, int(samples * 169 / max(169, len(classes))))
    jobs = [(label, n, per_job, seed * 7919 + i) for i, (label, n) in
            enumerate((c, n) for c in classes for n in range(1, MAX_OPP + 1))]
    equity = {c: [0.0] * MAX_OPP for c in classes}
    for label, n_opp, eq in pool.imap_unordered(tg.preflop_job, jobs, chunksize=4):
        equity[label][n_opp - 1] = round(eq, 4)
    rank = tg.rank_percentiles(equity, classes)
    _dump(out / "preflop_equity.json", equity)
    _dump(out / "preflop_rank.json", rank)
    return equity, rank


def gen_matrix(pool: Pool, classes: dict, samples: int, seed: int, out: Path) -> None:
    labels = list(classes)
    n = len(labels)
    jobs = [(i, j, samples, seed * 104729 + i * n + j) for i in range(n) for j in range(i, n)]
    m = [[0.0] * n for _ in range(n)]
    for i, j, eq in pool.imap_unordered(tg.matrix_job, jobs, chunksize=64):
        m[i][j] = 0.5 if i == j else round(eq, 3)
        m[j][i] = round(1.0 - m[i][j], 3)
    _dump(out / "hu_matrix.json", {"classes": labels, "equity": m})


def gen_flops(pool: Pool, rules: Rules, seed: int, out: Path, flops_per_bucket: int, max_holdings: int) -> dict:
    flops = tg.canonical_flops(tg.live_deck(rules))
    if flops_per_bucket:
        kept: dict[str, list] = {}
        for rep, w in flops:
            lst = kept.setdefault(tg.texture_key(rep), [])
            if len(lst) < flops_per_bucket:
                lst.append((rep, w))
        flops = [x for lst in kept.values() for x in lst]
    jobs = [(rep, w, max_holdings, seed * 31 + i) for i, (rep, w) in enumerate(flops)]
    merged = tg.merge_flops(pool.imap_unordered(tg.flop_job, jobs, chunksize=8))
    examples: dict[str, str] = {}
    for rep, _ in flops:
        examples.setdefault(tg.texture_key(rep), tg.flop_example(rep))
    for key, b in merged.items():
        b["example"] = examples[key]
    doc = {
        "scheme": {
            "key": "pair-suits-connect-high",
            "pair": ["unpaired", "paired", "trips"],
            "suits": ["rainbow", "twotone", "mono"],
            "connect": "span of distinct ranks: connected <=2, gapped <=4, dry >4, none for trips",
            "high": "displayed rank of the top card",
            "hs": "hand strength = share of opposing holdings beaten on the flop (ties half), vs one opponent",
            "function": "hyperion.tablegen.texture_key(flop)",
        },
        "buckets": merged,
    }
    _dump(out / "flop_strength.json", doc)
    return doc


def run(rules: Rules, samples: int, out: Path, seed: int, workers: int, skip_matrix: bool,
        flops_per_bucket: int = 0, max_holdings: int = 2000, quiet: bool = False) -> dict[str, float]:
    """Generate every table into out; returns seconds per table."""
    t_all = time.perf_counter()
    classes = tg.class_table(rules)
    times: dict[str, float] = {}
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else print

    with Pool(workers, initializer=tg._init_worker, initargs=(tg.rules_to_dict(rules), classes)) as pool:
        t = time.perf_counter()
        gen_preflop(pool, classes, samples, seed, out)
        times["preflop_equity+rank"] = time.perf_counter() - t
        log(f"preflop_equity.json + preflop_rank.json  {len(classes)} classes  {times['preflop_equity+rank']:.1f}s")

        if rules.hole_cards != 2:
            _dump(out / "hole_classes.json", tg.hole_classes_doc(rules, classes))
            log(f"hole_classes.json  scheme best2+tags, {len(classes)} classes (hu_matrix skipped: not 2-card)")
        elif skip_matrix:
            log("hu_matrix.json  skipped")
        else:
            t = time.perf_counter()
            gen_matrix(pool, classes, _matrix_samples(samples), seed, out)
            times["hu_matrix"] = time.perf_counter() - t
            log(f"hu_matrix.json  {len(classes)}x{len(classes)} @ {_matrix_samples(samples)} samples  {times['hu_matrix']:.1f}s")

        t = time.perf_counter()
        doc = gen_flops(pool, rules, seed, out, flops_per_bucket, max_holdings)
        times["flop_strength"] = time.perf_counter() - t
        log(f"flop_strength.json  {len(doc['buckets'])} textures  {times['flop_strength']:.1f}s")

    times["total"] = time.perf_counter() - t_all
    meta = {
        "rules": tg.rules_to_dict(rules),
        "samples": samples,
        "matrix_samples": None if (skip_matrix or rules.hole_cards != 2) else _matrix_samples(samples),
        "seed": seed,
        "workers": workers,
        "seconds": {k: round(v, 1) for k, v in times.items()},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python": sys.version.split()[0],
    }
    _dump(out / "meta.json", meta)
    log(f"total {times['total']:.1f}s -> {out}")
    return times


def variant_check(rules: Rules, samples: int, seed: int, workers: int, skip_matrix: bool) -> None:
    """Run every table at 1/20 of the samples and project the full-run budget."""
    scale = 20
    with tempfile.TemporaryDirectory() as tmp:
        times = run(rules, max(50, samples // scale), Path(tmp), seed, workers, skip_matrix, quiet=True)
    print(f"variant check: hole_cards={rules.hole_cards} deck={len(tg.live_deck(rules))} workers={workers}")
    print(f"  measured at samples={max(50, samples // scale)}; projected at samples={samples}:")
    total = 0.0
    for name, secs in times.items():
        if name == "total":
            continue
        proj = secs * (1 if name == "flop_strength" else scale)
        total += proj
        print(f"  {name:22s} {secs:7.1f}s measured  ~{proj:7.1f}s projected")
    print(f"  {'total':22s} {times['total']:7.1f}s measured  ~{total:7.1f}s projected"
          f"  ({'OK' if total < 300 else 'OVER'} the 5-minute budget)")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--rules", default="default", help="'default' or a JSON file with Rules fields")
    p.add_argument("--samples", type=int, default=20000, help="Monte Carlo samples per class per opponent count")
    p.add_argument("--out", default=str(ROOT / "tables"))
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--workers", type=int, default=max(1, cpu_count() - 1))
    p.add_argument("--skip-matrix", action="store_true", help="skip the 169x169 heads-up matrix")
    p.add_argument("--flops-per-bucket", type=int, default=0, help="cap canonical flops per texture (0 = all)")
    p.add_argument("--max-holdings", type=int, default=2000, help="sample holdings per flop above this count")
    p.add_argument("--variant-check", action="store_true", help="time each table at reduced samples and project")
    a = p.parse_args(argv)
    rules = load_rules(a.rules)
    if a.variant_check:
        variant_check(rules, a.samples, a.seed, a.workers, a.skip_matrix)
        return 0
    run(rules, a.samples, Path(a.out), a.seed, a.workers, a.skip_matrix, a.flops_per_bucket, a.max_holdings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
