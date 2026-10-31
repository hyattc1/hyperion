#!/usr/bin/env python
"""Generate tables for every catalog variant whose card rules differ from default hold'em.

    python tools/gen_catalog.py                      # tables/variants/NAME/ for each, plus manifest.json
    python tools/gen_catalog.py --only permuted_ranks,toss_or_holdem,bounty
    python tools/gen_catalog.py --dry-run            # print the plan and the sample counts, write nothing

Reduced samples so the whole catalog generates in well under 15 minutes on 7 workers (see the
manifest for measured times). Entries whose card rules match the default (bounty, pot_limit, ...)
share tables/ and are listed in the manifest as "default". Entries the generator cannot model
(lowball, wild_deuces, hi_lo: the generator has no score hook) are listed as "unsupported" with
the reason. The 169x169 heads-up matrix is only generated for 2-card entries; for 3- and 4-card
entries gen_tables writes hole_classes.json instead and the manifest says so.

Per-entry sample counts (preflop samples per class per opponent count; the matrix uses 1/20):
  2 hole cards          4000   (default tables use 20000)
  3 hole cards          1500   (676 best2+tags classes)
  4 hole cards (Omaha)   300   (about 1700 classes, 60 evaluations per showdown)
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from multiprocessing import cpu_count
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from hyperion.drills import variants as V  # noqa: E402
from hyperion.tablegen import live_deck, rules_to_dict  # noqa: E402
import gen_tables  # noqa: E402

OUT_ROOT = ROOT / "tables" / "variants"

SAMPLES = {2: 4000, 3: 1500, 4: 300}
FLOPS_PER_BUCKET = {2: 0, 3: 3, 4: 2}  # 0 = every canonical flop
MAX_HOLDINGS = {2: 2000, 3: 1500, 4: 800}


def plan_for(v: V.Variant) -> dict:
    """What the generator will do for one entry and why."""
    r = v.rules
    if not v.card_rules_differ():
        return {"status": "default", "reason": "card rules match default hold'em; use tables/"}
    if v.tables == "unsupported":
        return {"status": "unsupported", "reason": v.tables_note or "generator cannot model the showdown"}
    if v.tables == "default":
        return {"status": "default", "reason": v.tables_note or "default tables are a fine approximation"}
    k = r.hole_cards
    plan = {
        "status": "generate",
        "samples": SAMPLES[k],
        "matrix": k == 2,
        "matrix_note": None if k == 2 else "hu_matrix skipped: the 169x169 matrix is a 2-card object; hole_classes.json instead",
        "flops_per_bucket": FLOPS_PER_BUCKET[k],
        "max_holdings": MAX_HOLDINGS[k],
        "deck": len(live_deck(r)),
        "approximate": v.tables == "approximate",
        "note": v.tables_note,
    }
    return plan


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(OUT_ROOT))
    p.add_argument("--workers", type=int, default=max(1, cpu_count() - 1))
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--only", default=None, help="comma-separated entry names (default: every entry)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    out_root = Path(a.out)
    only = set(a.only.split(",")) if a.only else None
    manifest = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "workers": a.workers,
        "seed": a.seed,
        "command": "python tools/gen_catalog.py" + (f" --only {a.only}" if a.only else ""),
        "entries": {},
    }
    t_all = time.perf_counter()
    for v in V.catalog(seed=0):
        plan = plan_for(v)
        entry = {"axis": v.axis, "plan": plan}
        if plan["status"] != "generate" or (only and v.name not in only):
            if plan["status"] == "generate":
                entry["plan"] = dict(plan, status="skipped", reason="not in --only; run gen_catalog.py --only " + v.name)
            manifest["entries"][v.name] = entry
            print(f"{v.name:<26} {entry['plan']['status']:<12} {entry['plan'].get('reason', '')}")
            continue
        out = out_root / v.name
        print(f"{v.name:<26} generate -> {out}  samples={plan['samples']} matrix={plan['matrix']}"
              f" deck={plan['deck']} flops/bucket={plan['flops_per_bucket'] or 'all'}")
        if a.dry_run:
            manifest["entries"][v.name] = entry
            continue
        t = time.perf_counter()
        times = gen_tables.run(v.rules, plan["samples"], out, a.seed, a.workers, skip_matrix=not plan["matrix"],
                               flops_per_bucket=plan["flops_per_bucket"], max_holdings=plan["max_holdings"], quiet=True)
        files = sorted(f.name for f in out.iterdir() if f.suffix == ".json")
        size = sum((out / f).stat().st_size for f in files)
        entry.update({
            "seconds": round(time.perf_counter() - t, 1),
            "seconds_by_table": {k: round(s, 1) for k, s in times.items()},
            "files": files,
            "bytes": size,
            "rules": rules_to_dict(v.rules),
        })
        manifest["entries"][v.name] = entry
        print(f"{'':26} done in {entry['seconds']}s, {size / 1024:.0f} KB: {', '.join(files)}")
    manifest["total_seconds"] = round(time.perf_counter() - t_all, 1)
    manifest["total_bytes"] = sum(e.get("bytes", 0) for e in manifest["entries"].values())
    if not a.dry_run:
        out_root.mkdir(parents=True, exist_ok=True)
        (out_root / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(f"total {manifest['total_seconds']}s, {manifest['total_bytes'] / 1024 / 1024:.2f} MB -> {out_root / 'manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
