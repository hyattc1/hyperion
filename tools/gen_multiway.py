"""Solve the multiway chip-EV push/fold tables and write tables/pushfold_multi.json.

    .venv/bin/python tools/gen_multiway.py                    # full grid, 7 workers
    .venv/bin/python tools/gen_multiway.py --workers 4 --tol 2e-4
    .venv/bin/python tools/gen_multiway.py --k 1,7 --depths 5-10 --no-reshove --out /tmp/pf.json

(a) first-in shoves with k = 1..7 players behind at S = 2..25 bb and (b) re-shoves over a 2.3 bb open by
the top w of hands with m behind at S = 4..25 (see hyperion/strategy/multiway.py for the model). The file
is keyed to tables/hu_matrix.json by `matrix_fp`; regenerate whenever the matrix changes (load_multiway
returns None on a mismatch and Hero falls back to the heads-up rule).
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion.strategy import multiway as MW  # noqa: E402
from hyperion.strategy.tables import TABLES_DIR, load, write_json  # noqa: E402


def _ints(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            out.extend(range(lo, hi + 1))
        elif part:
            out.append(int(part))
    return out


def _floats(spec: str) -> list[float]:
    return [float(x) for x in spec.split(",") if x]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables-dir", default=TABLES_DIR)
    p.add_argument("--out", default=None, help="output path (default <tables-dir>/pushfold_multi.json)")
    p.add_argument("--no-write", action="store_true")
    p.add_argument("--workers", type=int, default=7)
    p.add_argument("--tol", type=float, default=MW.TOL)
    p.add_argument("--max-iters", type=int, default=MW.MAX_ITERS)
    p.add_argument("--k", default=",".join(map(str, MW.K_GRID)))
    p.add_argument("--depths", default=f"{MW.S_GRID[0]}-{MW.S_GRID[-1]}")
    p.add_argument("--w", default=",".join(map(str, MW.W_GRID)))
    p.add_argument("--m", default=",".join(map(str, MW.M_GRID)))
    p.add_argument("--rs-depths", default=f"{MW.RS_S_GRID[0]}-{MW.RS_S_GRID[-1]}")
    p.add_argument("--no-reshove", action="store_true")
    p.add_argument("--quiet", action="store_true")
    a = p.parse_args(argv)

    tables = load(a.tables_dir, need_hu=True)
    if tables.hu is None:
        print(f"{a.tables_dir}: no heads-up matrix (a 3- or 4-card set?); nothing to solve", file=sys.stderr)
        return 1
    log = None if a.quiet else (lambda s: print(s, flush=True))
    t0 = time.time()
    sol = MW.solve_all(tables, workers=a.workers, k_grid=_ints(a.k), s_grid=_ints(a.depths),
                       w_grid=[] if a.no_reshove else _floats(a.w), m_grid=[] if a.no_reshove else _ints(a.m),
                       rs_s_grid=_ints(a.rs_depths), tol=a.tol, max_iters=a.max_iters, log=log)
    sol["seconds"] = round(time.time() - t0, 1)
    try:
        sol["load_avg_at_end"] = [round(x, 2) for x in os.getloadavg()]
    except OSError:
        pass
    s = sol["summary"]
    print(f"solved {s['solves']} spots in {sol['seconds']} s on {a.workers} workers: worst gain {s['worst_gain']:.3g} bb "
          f"(tol {a.tol:g}), {s['unconverged']} over tol, iterations mean {s['mean_iters']} max {s['max_iters_used']}")
    fi = sol["first_in"]
    print("first-in shove frequency (rows k, columns S):")
    print("  k \\ S " + " ".join(f"{S:>5}" for S in fi["S"]))
    for k, row in zip(fi["k"], fi["p_push"]):
        print(f"  {k:>5} " + " ".join(f"{x:5.3f}" for x in row))
    if not a.no_write:
        if a.out:
            out_dir, name = os.path.dirname(os.path.abspath(a.out)), os.path.basename(a.out)
        else:
            out_dir, name = a.tables_dir, MW.FILE
        path = write_json(name, sol, out_dir)
        print(f"wrote {path} ({os.path.getsize(path):,} B)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
