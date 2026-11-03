#!/usr/bin/env python
"""Regenerate every table under tables/ from a Rules object. Stdlib + multiprocessing only.

    python tools/gen_tables.py --rules default --samples 20000 --out tables/
    python tools/gen_tables.py --rules variant.json --variant-check     # time budget per table
    python tools/gen_tables.py --rules default --skip-matrix --out /tmp/t
    python tools/gen_tables.py --rules rules_tonight.json --preset loaded --out tables/variants/<name>/ --workers 3
    python tools/gen_tables.py --rules rules_tonight.json --preset loaded --out tables/variants/<name>/ --resume

Outputs (see tables/README.md): preflop_equity.json, preflop_rank.json, hu_matrix.json,
flop_strength.json, hole_classes.json (only when hole_cards != 2), meta.json.

`--preset loaded` (drill 10: the defaults on a box at load 22-28 projected far past 20 minutes for a must-use showdown,
and the night restarted by hand): 3,000 samples a class and opponent count, 50 a heads-up class pair, 2 flops a texture
with 300 holdings each; the accuracy it buys is printed before the run (a 95% interval, the worst case p = 0.5) and
recorded in meta.json. Drill 10's Solo Hold'em set under it: about 5 minutes on 3 workers at load 22-25, and the bot it
fed played the night's patch (+0.93 +- 0.40 against twist-aware bots, docs/drills/prompt-drill-10.md H6). Explicit
--samples / --matrix-samples / --flops-per-bucket / --max-holdings win over the preset.

Progress goes to stdout unbuffered (a line at every tenth of a stage, with its rate and an ETA), so a backgrounded run
redirected to a file shows where it is. `--resume` keeps the stages a stopped run finished in --out (meta.json lists
them as it goes; for a run from before that, the files themselves), for the same card rules, and runs the rest: the
matrix, the push/fold re-solve and the flops after a preflop that finished. Stop a run by its PID (`kill <pid>`; start
it as `... > gen.log 2>&1 & echo $! > gen.pid`), never `pkill -f`: the pattern matches the shell that runs it (drill 10
killed its own shell twice).
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


MATRIX_SAMPLES = 5000  # per class pair; 1,000 (the old samples // 20) left 1.6% noise per cell, which the 2026-10-31 HRC
# cross-check saw as low suited junk pushed at 5-10 bb. 5,000 is ~0.7% and ~50 s on 7 workers.


PRESETS = {
    # a loaded box (load over the core count): drill 10's restart, the numbers its Solo set was built with
    "loaded": {"samples": 3000, "matrix_samples": 50, "flops_per_bucket": 2, "max_holdings": 300},
}


def accuracy(samples: int, m_samples: int | None, n_classes: int) -> dict:
    """The 95% half-widths the sample counts buy, worst case (an equity of 0.5): a preflop cell (one class against one
    to seven opponents, `samples` scaled to the class count as gen_preflop does), a heads-up matrix cell, and an
    equity against a 20% range read from the matrix (push/fold reads ranges; ~34 classes, independent cells)."""
    per_job = max(50, int(samples * 169 / max(169, n_classes)))
    out = {"preflop_cell": round(1.96 * 0.5 / per_job ** 0.5, 4)}
    if m_samples:
        cell = 1.96 * 0.5 / m_samples ** 0.5
        out["matrix_cell"] = round(cell, 4)
        out["matrix_range20"] = round(cell / 34 ** 0.5, 4)
    return out


def _say(*a) -> None:
    print(*a, flush=True)


def _progress(stage: str, done: int, total: int, t0: float, step: list) -> None:
    """One line at every tenth of a stage: done/total, the rate and an ETA."""
    if total <= 0 or done * 10 < step[0] * total:
        return
    while done * 10 >= step[0] * total:
        step[0] += 1
    dt = time.perf_counter() - t0
    eta = dt * (total - done) / done if done else 0.0
    _say(f"  {stage}: {done}/{total} jobs ({100 * done // total}%)  {dt:.0f}s  eta {eta:.0f}s")


def _matrix_samples(samples: int, matrix_samples: int | None = None) -> int:
    if matrix_samples is not None:
        return max(20, matrix_samples)
    return max(20, min(MATRIX_SAMPLES, samples // 4)) if samples < MATRIX_SAMPLES * 4 else MATRIX_SAMPLES


def gen_preflop(pool: Pool, classes: dict, samples: int, seed: int, out: Path, progress: bool = False) -> tuple[dict, dict]:
    per_job = max(50, int(samples * 169 / max(169, len(classes))))
    jobs = [(label, n, per_job, seed * 7919 + i) for i, (label, n) in
            enumerate((c, n) for c in classes for n in range(1, MAX_OPP + 1))]
    equity = {c: [0.0] * MAX_OPP for c in classes}
    t0, step = time.perf_counter(), [1]
    for k, (label, n_opp, eq) in enumerate(pool.imap_unordered(tg.preflop_job, jobs, chunksize=4), 1):
        equity[label][n_opp - 1] = round(eq, 4)
        if progress:
            _progress("preflop", k, len(jobs), t0, step)
    rank = tg.rank_percentiles(equity, classes)
    _dump(out / "preflop_equity.json", equity)
    _dump(out / "preflop_rank.json", rank)
    return equity, rank


def gen_matrix(pool: Pool, classes: dict, samples: int, seed: int, out: Path, progress: bool = False) -> None:
    labels = list(classes)
    n = len(labels)
    jobs = [(i, j, samples, seed * 104729 + i * n + j) for i in range(n) for j in range(i, n)]
    m = [[0.0] * n for _ in range(n)]
    t0, step = time.perf_counter(), [1]
    for k, (i, j, eq) in enumerate(pool.imap_unordered(tg.matrix_job, jobs, chunksize=64), 1):
        m[i][j] = 0.5 if i == j else round(eq, 3)
        m[j][i] = round(1.0 - m[i][j], 3)
        if progress:
            _progress("hu_matrix", k, len(jobs), t0, step)
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


STAGE_FILES = {"preflop": ("preflop_equity.json", "preflop_rank.json"), "hu_matrix": ("hu_matrix.json",),
               "pushfold": ("pushfold_hu.json",), "flops": ("flop_strength.json",)}


def finished_stages(out: Path, rules: Rules) -> tuple[list[str], dict]:
    """The stages a stopped run left finished in `out` for these card rules, and its partial meta (empty when there
    is none, or it was for other card rules: then nothing is kept). meta.json's `done` when the run recorded it, else
    the files (a run from before `done` existed)."""
    try:
        meta = json.loads((out / "meta.json").read_text())
    except (OSError, ValueError):
        return [], {}
    from hyperion.strategy.tables import _card_rules

    if _card_rules(meta.get("rules") or {}) != _card_rules(tg.rules_to_dict(rules)):
        return [], {}
    if "done" in meta:
        done = list(meta["done"])
    else:
        done = [st for st, files in STAGE_FILES.items() if all((out / f).exists() for f in files)]
    return [st for st in done if all((out / f).exists() for f in STAGE_FILES[st])], meta


def run(rules: Rules, samples: int, out: Path, seed: int, workers: int, skip_matrix: bool,
        flops_per_bucket: int = 0, max_holdings: int = 2000, quiet: bool = False,
        matrix_samples: int | None = None, resume: bool = False, preset: str | None = None) -> dict[str, float]:
    """Generate every table into out; returns seconds per table. `resume`: keep the stages a stopped run finished
    (finished_stages) and run the rest; a matrix run again re-solves push/fold too."""
    t_all = time.perf_counter()
    m_samples = _matrix_samples(samples, matrix_samples)
    classes = tg.class_table(rules)
    times: dict[str, float] = {}
    out.mkdir(parents=True, exist_ok=True)
    log = (lambda *a: None) if quiet else _say
    kept, old = finished_stages(out, rules) if resume else ([], {})
    if resume:
        log(f"resume: kept {', '.join(kept) or 'nothing'} from {out}")
    done: list[str] = list(kept)
    used = dict(old.get("used") or {})  # each stage's samples, as run (a resumed set mixes runs)
    if "preflop" in kept and "preflop" not in used:
        used["preflop"] = old.get("samples")
    if "hu_matrix" in kept and "hu_matrix" not in used:
        used["hu_matrix"] = old.get("matrix_samples")
    two_card = rules.hole_cards == 2
    acc = accuracy(samples, None if (skip_matrix or not two_card) else m_samples, len(classes))
    log(f"accuracy (95%, worst case): preflop cell +-{acc['preflop_cell']:.3f}"
        + (f", heads-up matrix cell +-{acc['matrix_cell']:.3f} (+-{acc['matrix_range20']:.3f} against a 20% range)"
           if "matrix_cell" in acc else "") + (f"  [preset {preset}]" if preset else ""))

    def mark(stage: str, n=None) -> None:
        done.append(stage)
        if n is not None:
            used[stage] = n
        _dump(out / "meta.json", {"rules": tg.rules_to_dict(rules), "samples": samples, "seed": seed, "partial": True,
                                  "done": done, "used": used})

    # the rules go down first so anything that reads the half-written set (the push/fold solve below, a
    # drill's T+30 check) knows which class scheme the files declare; the full meta.json replaces it at the end
    _dump(out / "meta.json", {"rules": tg.rules_to_dict(rules), "samples": samples, "seed": seed, "partial": True,
                              "done": done, "used": used})
    with Pool(workers, initializer=tg._init_worker, initargs=(tg.rules_to_dict(rules), classes)) as pool:
        if "preflop" not in kept:
            t = time.perf_counter()
            gen_preflop(pool, classes, samples, seed, out, progress=not quiet)
            times["preflop_equity+rank"] = time.perf_counter() - t
            mark("preflop", samples)
            log(f"preflop_equity.json + preflop_rank.json  {len(classes)} classes  {times['preflop_equity+rank']:.1f}s")

        if rules.hole_cards != 2:
            _dump(out / "hole_classes.json", tg.hole_classes_doc(rules, classes))
            log(f"hole_classes.json  scheme best2+tags, {len(classes)} classes (hu_matrix skipped: not 2-card)")
        elif skip_matrix:
            log("hu_matrix.json  skipped")
        else:
            redo_pf = "hu_matrix" not in kept
            if redo_pf:
                t = time.perf_counter()
                gen_matrix(pool, classes, m_samples, seed, out, progress=not quiet)
                times["hu_matrix"] = time.perf_counter() - t
                mark("hu_matrix", m_samples)
                log(f"hu_matrix.json  {len(classes)}x{len(classes)} @ {m_samples} samples  {times['hu_matrix']:.1f}s")
            if redo_pf or "pushfold" not in kept:
                # the push/fold solution depends on the matrix; rebuild it now so no stale cache survives
                t = time.perf_counter()
                stale = out / "pushfold_hu.json"
                if stale.exists():
                    stale.unlink()
                from hyperion.strategy import tables as _tables
                from hyperion.strategy.pushfold import build_pushfold_tables
                _tables._CACHE.clear()
                t_loaded = _tables.load(str(out), need_hu=True, strict=True)  # the set just written, never a fallback
                sol = build_pushfold_tables(t_loaded, str(out))
                times["pushfold_hu"] = time.perf_counter() - t
                mark("pushfold")
                worst = max(v[1] for v in sol["converged"].values())
                log(f"pushfold_hu.json  re-solved from the new matrix over {sol['n_classes']} classes  "
                    f"{times['pushfold_hu']:.1f}s  (worst best-response gain {worst:.2e} bb)")

        if "flops" not in kept:
            t = time.perf_counter()
            doc = gen_flops(pool, rules, seed, out, flops_per_bucket, max_holdings)
            times["flop_strength"] = time.perf_counter() - t
            mark("flops", [flops_per_bucket, max_holdings])
            log(f"flop_strength.json  {len(doc['buckets'])} textures  {times['flop_strength']:.1f}s")

    times["total"] = time.perf_counter() - t_all
    pre_n = used.get("preflop", samples)
    mat_n = None if (skip_matrix or rules.hole_cards != 2) else used.get("hu_matrix", m_samples)
    meta = {
        "rules": tg.rules_to_dict(rules),
        "samples": pre_n,
        "matrix_samples": mat_n,
        "seed": seed,
        "workers": workers,
        "seconds": {k: round(v, 1) for k, v in times.items()},
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python": sys.version.split()[0],
        "accuracy_95": accuracy(pre_n or samples, mat_n, len(classes)),
    }
    if preset:
        meta["preset"] = preset
    if kept:
        meta["resumed"] = {"kept": kept, "used": used}
    _dump(out / "meta.json", meta)
    log(f"total {times['total']:.1f}s -> {out}")
    return times


def variant_check(rules: Rules, samples: int, seed: int, workers: int, skip_matrix: bool,
                  matrix_samples: int | None = None) -> None:
    """Run every table at 1/20 of the samples and project the full-run budget."""
    scale = 20
    with tempfile.TemporaryDirectory() as tmp:
        times = run(rules, max(50, samples // scale), Path(tmp), seed, workers, skip_matrix, quiet=True,
                    matrix_samples=max(20, _matrix_samples(samples, matrix_samples) // scale))
    print(f"variant check: hole_cards={rules.hole_cards} deck={len(tg.live_deck(rules))} workers={workers}")
    print(f"  measured at samples={max(50, samples // scale)}; projected at samples={samples}:")
    total = 0.0
    for name, secs in times.items():
        if name == "total":
            continue
        proj = secs * (1 if name in ("flop_strength", "pushfold_hu") else scale)
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
    p.add_argument("--matrix-samples", type=int, default=None,
                   help=f"Monte Carlo samples per heads-up class pair (default {MATRIX_SAMPLES}, or samples/4 below that)")
    p.add_argument("--flops-per-bucket", type=int, default=0, help="cap canonical flops per texture (0 = all)")
    p.add_argument("--max-holdings", type=int, default=2000, help="sample holdings per flop above this count")
    p.add_argument("--variant-check", action="store_true", help="time each table at reduced samples and project")
    p.add_argument("--preset", choices=sorted(PRESETS), default=None,
                   help="`loaded`: a box over one load per core (module doc: fewer samples, the accuracy printed)")
    p.add_argument("--resume", action="store_true", help="keep the stages a stopped run finished in --out (same card "
                   "rules) and run the rest")
    a = p.parse_args(argv)
    if a.preset:
        given = {x.split("=")[0] for x in (argv if argv is not None else sys.argv[1:]) if x.startswith("--")}
        for k, v in PRESETS[a.preset].items():
            if "--" + k.replace("_", "-") not in given:
                setattr(a, k, v)
    rules = load_rules(a.rules)
    if a.variant_check:
        variant_check(rules, a.samples, a.seed, a.workers, a.skip_matrix, a.matrix_samples)
        return 0
    run(rules, a.samples, Path(a.out), a.seed, a.workers, a.skip_matrix, a.flops_per_bucket, a.max_holdings,
        matrix_samples=a.matrix_samples, resume=a.resume, preset=a.preset)
    return 0


if __name__ == "__main__":
    sys.exit(main())
