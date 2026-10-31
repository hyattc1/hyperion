"""Cross-check tables/pushfold_hu.json against HoldemResources' free heads-up Nash push/fold data.

    .venv/bin/python tools/hrc_check.py                      # downloads the zip to ~/.cache/hyperion/hrc
    .venv/bin/python tools/hrc_check.py --zip path/to/holdemresources_hu_equilibrium.zip
    .venv/bin/python tools/hrc_check.py --depths 2-25 --threshold 0.5 --worst 10

HRC's zip holds holdemresources_hu_push.csv and holdemresources_hu_call.csv: a `stack` column (effective
stack in big blinds, 1.00 to 200.00 in 0.05 steps) and one column per 169-class with the push (call)
FREQUENCY 0..1. Our table holds a 0/1 push and call set per integer depth (SB pushes, BB calls, blinds
0.5/1, no antes). For each depth this prints: how many classes disagree at the frequency threshold
(we push and they fold, or they push and we fold), the mean absolute difference between our 0/1 and
their frequency over the 169 classes, both sides' combo-weighted frequencies, and the worst classes.

The files carry no license; they are cached outside the repo and never committed. The reference depth
is HRC's `stack` = our depth S (the whole effective stack, blind included).
"""
from __future__ import annotations

import argparse
import csv
import io
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion.strategy.pushfold import load_pushfold  # noqa: E402
from hyperion.strategy.tables import CLASSES, COMBO_COUNT, TOTAL_COMBOS, load  # noqa: E402

HRC_URL = "https://www.holdemresources.net/hrdata/holdemresources_hu_equilibrium.zip"
PUSH_CSV = "holdemresources_hu_push.csv"
CALL_CSV = "holdemresources_hu_call.csv"
DEFAULT_CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "hyperion" / "hrc"


# ---------------------------------------------------------------- parsing

def parse_hrc_csv(text: str) -> dict[float, dict[str, float]]:
    """HRC layout -> {stack_bb: {class: frequency}}. Header cells are padded (`stack, 22, 32o, ...`)."""
    rows = list(csv.reader(io.StringIO(text)))
    header = [h.strip() for h in rows[0]]
    if not header or header[0].lower() != "stack":
        raise ValueError(f"not an HRC table: header starts with {header[:2]!r}")
    classes = header[1:]
    out: dict[float, dict[str, float]] = {}
    for row in rows[1:]:
        cells = [c.strip() for c in row]
        if len(cells) != len(header) or not cells[0]:
            continue
        stack = round(float(cells[0]), 2)
        out[stack] = {cls: float(v) for cls, v in zip(classes, cells[1:])}
    return out


def fetch_zip(url: str = HRC_URL, cache: Path = DEFAULT_CACHE) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / Path(url).name
    if not dest.exists() or dest.stat().st_size == 0:
        with urllib.request.urlopen(url, timeout=60) as r, open(dest, "wb") as f:
            f.write(r.read())
    return dest


def load_hrc(zip_path: Path) -> tuple[dict[float, dict[str, float]], dict[float, dict[str, float]]]:
    with zipfile.ZipFile(zip_path) as z:
        names = z.namelist()
        push_name = next(n for n in names if n.endswith(PUSH_CSV))
        call_name = next(n for n in names if n.endswith(CALL_CSV))
        return parse_hrc_csv(z.read(push_name).decode()), parse_hrc_csv(z.read(call_name).decode())


# ---------------------------------------------------------------- comparing

def compare(ours: list[int], theirs: dict[str, float], threshold: float = 0.5, worst: int = 10) -> dict:
    """ours: 0/1 per CLASSES; theirs: class -> frequency. Classes missing on their side are skipped."""
    diffs = []
    we_only, they_only = [], []
    for i, cls in enumerate(CLASSES):
        if cls not in theirs:
            continue
        o, t = int(ours[i]), float(theirs[cls])
        diffs.append((abs(o - t), cls, o, t))
        if o == 1 and t < threshold:
            we_only.append(cls)
        elif o == 0 and t >= threshold:
            they_only.append(cls)
    diffs.sort(key=lambda d: (-d[0], d[1]))
    n = len(diffs)
    return {
        "n": n,
        "disagree": len(we_only) + len(they_only),
        "we_only": we_only,
        "they_only": they_only,
        "mad": sum(d[0] for d in diffs) / n if n else 0.0,
        "freq_ours": sum(COMBO_COUNT[i] * int(ours[i]) for i in range(len(CLASSES))) / TOTAL_COMBOS,
        "freq_theirs": sum(COMBO_COUNT[i] * float(theirs.get(c, 0.0)) for i, c in enumerate(CLASSES)) / TOTAL_COMBOS,
        "worst": [(cls, o, t) for _, cls, o, t in diffs[:worst] if abs(o - t) > 0],
    }


def row_for(table: dict[float, dict[str, float]], depth: float) -> dict[str, float] | None:
    key = round(float(depth), 2)
    if key in table:
        return table[key]
    near = [s for s in table if abs(s - key) < 0.026]
    return table[min(near, key=lambda s: abs(s - key))] if near else None


def parse_depths(spec: str) -> list[int]:
    if "-" in spec:
        lo, hi = (int(x) for x in spec.split("-"))
        return list(range(lo, hi + 1))
    return [int(x) for x in spec.split(",")]


def run_check(push_hrc, call_hrc, sol: dict, depths: list[int], threshold: float, worst: int) -> list[dict]:
    out = []
    for d in depths:
        key = str(d)
        if key not in sol["push"]:
            continue
        hp, hc = row_for(push_hrc, d), row_for(call_hrc, d)
        if hp is None or hc is None:
            continue
        out.append({"depth": d, "push": compare(sol["push"][key], hp, threshold, worst),
                    "call": compare(sol["call"][key], hc, threshold, worst)})
    return out


def _worst_str(w, k=10) -> str:
    return " ".join(f"{cls}({o}/{t:.2f})" for cls, o, t in w[:k])


def render(results: list[dict], side: str, worst: int) -> str:
    lines = [f"| depth | {side}: disagree (we {side} / they fold, they {side} / we fold) | MAD | freq ours / HRC | worst (ours/HRC) |",
             "|---|---|---|---|---|"]
    for r in results:
        c = r[side]
        lines.append(f"| {r['depth']} | {c['disagree']} ({len(c['we_only'])} / {len(c['they_only'])}) | {c['mad']:.3f} | "
                     f"{c['freq_ours']:.3f} / {c['freq_theirs']:.3f} | {_worst_str(c['worst'], worst)} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--zip", help="local copy of holdemresources_hu_equilibrium.zip")
    p.add_argument("--url", default=HRC_URL)
    p.add_argument("--cache", default=str(DEFAULT_CACHE), help="download dir, outside the repo")
    p.add_argument("--depths", default="2-25")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--worst", type=int, default=10)
    p.add_argument("--tables-dir", default=None)
    a = p.parse_args(argv)

    if a.zip:
        zip_path = Path(a.zip)
    else:
        try:
            zip_path = fetch_zip(a.url, Path(a.cache))
        except Exception as e:  # noqa: BLE001
            print(f"download failed ({e}); pass --zip with a local copy of {Path(a.url).name}", file=sys.stderr)
            return 2
    push_hrc, call_hrc = load_hrc(zip_path)
    missing = sorted(set(CLASSES) - set(next(iter(push_hrc.values())).keys()))
    if missing:
        print(f"warning: {len(missing)} of our classes are not in the HRC header: {missing[:8]}", file=sys.stderr)

    tables = load(need_hu=True) if a.tables_dir is None else load(a.tables_dir, need_hu=True)
    sol = load_pushfold(tables) if a.tables_dir is None else load_pushfold(tables, a.tables_dir)
    results = run_check(push_hrc, call_hrc, sol, parse_depths(a.depths), a.threshold, a.worst)
    if not results:
        print("no overlapping depths", file=sys.stderr)
        return 1

    print(f"HRC heads-up Nash ({zip_path.name}, {len(push_hrc)} stack rows) vs tables/pushfold_hu.json "
          f"(matrix {sol.get('matrix_fp', '?')}), threshold {a.threshold}\n")
    print(render(results, "push", a.worst))
    print()
    print(render(results, "call", a.worst))
    tot_p = sum(r["push"]["disagree"] for r in results)
    tot_c = sum(r["call"]["disagree"] for r in results)
    print(f"\ntotals over {len(results)} depths: push {tot_p} disagreements ({tot_p / len(results):.1f}/depth), "
          f"call {tot_c} ({tot_c / len(results):.1f}/depth); "
          f"mean MAD push {sum(r['push']['mad'] for r in results) / len(results):.3f}, "
          f"call {sum(r['call']['mad'] for r in results) / len(results):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
