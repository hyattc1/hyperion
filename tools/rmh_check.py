"""Cross-check tables/pushfold_multi.json's first-in shoves against RangeMyHand's chip-EV push/fold ranges.

    .venv/bin/python tools/rmh_check.py                 # downloads the JSON to ~/.cache/hyperion/rmh
    .venv/bin/python tools/rmh_check.py --file path/to/push-fold-ranges.json
    .venv/bin/python tools/rmh_check.py --depths 2-25 --threshold 0.5 --worst 8 --seats SB,BTN

Data: "RangeMyHand Nash push/fold ranges (www.rangemyhand.com), CC BY 4.0", v0.3.0 (2026-10-12), mirrored
at github.com/hasuwini77/push-fold-ranges (commit c913a16, `push-fold-ranges.json`, 513,798 B). It is
cached outside the repo and never committed. The download is treated as untrusted data: it is parsed as
JSON and every field is type- and range-checked; nothing from it is executed.

Their layout: `hands` (the 169 classes, grid order AA, AKs, ..., A2s, AKo, KK, ...) and `spots[]`, each
{table: "6max" | "9max", seat, playersBehind, stackBB: 1..25, pushFreq: 169 frequencies in `hands`
order}. Their model: chip-EV Nash, unopened shove only, stack = total stack before posting (our S),
1.5 bb dead (the blinds), no antes, fictitious play, 220 iterations.

Seats compared (theirs -> ours): SB (1 behind) -> k=1, BTN (2) -> k=2, CO (3) -> k=3, 6-max UTG (5) ->
k=5, MP (6) -> k=6, and 9-max UTG (8 behind) -> k=7, flagged: our table stops at 7 behind, so their
UTG should be a little tighter than ours. Per depth: how many classes disagree at the threshold (we
shove and their frequency is below it, or the reverse), the mean absolute difference between our 0/1 set
and their frequency over the 169 classes, combo-weighted frequencies (our set, our mixed strategy,
theirs), and the worst classes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion.strategy.multiway import load_multiway  # noqa: E402
from hyperion.strategy.tables import CLASS_INDEX, CLASSES, COMBO_COUNT, TOTAL_COMBOS, load  # noqa: E402

COMMIT = "c913a168742ee39743b4a9c1c0ec645480b533d7"
RMH_URL = f"https://raw.githubusercontent.com/hasuwini77/push-fold-ranges/{COMMIT}/push-fold-ranges.json"
DEFAULT_CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "hyperion" / "rmh"
MAX_BYTES = 8 << 20
ATTRIBUTION = "RangeMyHand Nash push/fold ranges (www.rangemyhand.com), CC BY 4.0"

# (label, their table, their seat, their players behind, our k, note)
SEATS = (
    ("SB", "9max", "SB", 1, 1, ""),
    ("BTN", "9max", "BTN", 2, 2, ""),
    ("CO", "9max", "CO", 3, 3, ""),
    ("UTG6", "6max", "UTG", 5, 5, ""),
    ("MP", "9max", "MP", 6, 6, ""),
    ("UTG", "9max", "UTG", 8, 7, "their 8 behind vs our 7: expect them slightly tighter"),
)


# ---------------------------------------------------------------- parsing (untrusted input)

def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def parse_rmh(text: str) -> dict:
    """RangeMyHand JSON -> {"meta": {...}, "spots": {(table, seat, behind, stack): {class: freq}}}.

    Raises ValueError on anything that is not their layout: the hands must be exactly our 169 class
    names, every spot's pushFreq 169 finite numbers in [0, 1]."""
    try:
        d = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"not JSON: {e}") from None
    if not isinstance(d, dict) or not isinstance(d.get("hands"), list) or not isinstance(d.get("spots"), list):
        raise ValueError("not a RangeMyHand table: expected an object with 'hands' and 'spots' lists")
    hands = d["hands"]
    if len(hands) != len(CLASSES) or not all(isinstance(h, str) for h in hands):
        raise ValueError(f"'hands' must be {len(CLASSES)} class names, got {len(hands)}")
    unknown = [h for h in hands if h not in CLASS_INDEX]
    if unknown or len(set(hands)) != len(hands):
        raise ValueError(f"'hands' does not match the 169 classes (unknown: {unknown[:5]})")
    spots: dict[tuple, dict[str, float]] = {}
    for i, sp in enumerate(d["spots"]):
        if not isinstance(sp, dict):
            raise ValueError(f"spot {i} is not an object")
        table, seat, behind, stack, freq = (sp.get(k) for k in ("table", "seat", "playersBehind", "stackBB", "pushFreq"))
        if not isinstance(table, str) or not isinstance(seat, str) or not _num(behind) or not _num(stack):
            raise ValueError(f"spot {i}: bad table/seat/playersBehind/stackBB")
        if not isinstance(freq, list) or len(freq) != len(hands) or not all(_num(x) and 0.0 <= x <= 1.0 for x in freq):
            raise ValueError(f"spot {i}: pushFreq must be {len(hands)} numbers in [0, 1]")
        key = (table[:16], seat[:16], int(behind), round(float(stack), 2))
        spots[key] = {h: float(x) for h, x in zip(hands, freq)}
    meta = {k: d.get(k) for k in ("name", "version", "generatedAt", "lastVerified", "license", "attribution", "model")
            if isinstance(d.get(k), (str, dict))}
    return {"meta": meta, "spots": spots}


def fetch(url: str = RMH_URL, cache: Path = DEFAULT_CACHE) -> Path:
    """Download once into `cache` (outside the repo); size-capped."""
    cache.mkdir(parents=True, exist_ok=True)
    dest = cache / Path(url).name
    if not dest.exists() or dest.stat().st_size == 0:
        with urllib.request.urlopen(url, timeout=60) as r:
            data = r.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError(f"download larger than {MAX_BYTES} B; refusing")
        tmp = dest.with_suffix(".part")
        tmp.write_bytes(data)
        tmp.replace(dest)
    return dest


# ---------------------------------------------------------------- comparing

def combo_freq(freq_by_class: dict[str, float]) -> float:
    return sum(COMBO_COUNT[i] * float(freq_by_class.get(c, 0.0)) for i, c in enumerate(CLASSES)) / TOTAL_COMBOS


def compare(ours: list[int], theirs: dict[str, float], threshold: float = 0.5, worst: int = 8) -> dict:
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
    diffs.sort(key=lambda d: (-d[0], CLASS_INDEX[d[1]]))
    n = len(diffs)
    return {
        "n": n,
        "disagree": len(we_only) + len(they_only),
        "we_only": we_only,
        "they_only": they_only,
        "mad": sum(d[0] for d in diffs) / n if n else 0.0,
        "freq_ours": sum(COMBO_COUNT[i] * int(ours[i]) for i in range(len(CLASSES))) / TOTAL_COMBOS,
        "freq_theirs": combo_freq(theirs),
        "worst": [(cls, o, t) for _, cls, o, t in diffs[:worst] if abs(o - t) > 0],
    }


def run_check(rmh: dict, mw: dict, depths: list[int], threshold: float = 0.5, worst: int = 8,
              seats=SEATS) -> list[dict]:
    """One record per seat: {"seat", "k", "behind", "note", "rows": [per depth compare + mixed freq]}."""
    out = []
    for label, table, seat, behind, k, note in seats:
        if k > mw["k_max"] or mw["push"][k] is None:
            continue
        rows = []
        for d in depths:
            theirs = rmh["spots"].get((table, seat, behind, float(d)))
            ours = mw["push"][k][d] if d < len(mw["push"][k]) else None
            if theirs is None or ours is None:
                continue
            r = compare(ours, theirs, threshold, worst)
            r["depth"] = d
            r["freq_mixed"] = mw["p_push"][k][d]
            rows.append(r)
        if rows:
            out.append({"seat": label, "table": table, "k": k, "behind": behind, "note": note, "rows": rows})
    return out


def _worst_str(w, k) -> str:
    return " ".join(f"{cls}({o}/{t:.2f})" for cls, o, t in w[:k])


def render(rec: dict, worst: int) -> str:
    lines = [f"### {rec['table']} {rec['seat']} ({rec['behind']} behind) vs our k = {rec['k']}"
             + (f"  [{rec['note']}]" if rec["note"] else ""),
             "",
             "| depth | disagree (we shove / they fold, they shove / we fold) | MAD | freq ours set / mixed / RMH | worst (ours/RMH) |",
             "|---|---|---|---|---|"]
    for r in rec["rows"]:
        lines.append(f"| {r['depth']} | {r['disagree']} ({len(r['we_only'])} / {len(r['they_only'])}) | {r['mad']:.3f} | "
                     f"{r['freq_ours']:.3f} / {r['freq_mixed']:.3f} / {r['freq_theirs']:.3f} | {_worst_str(r['worst'], worst)} |")
    return "\n".join(lines)


def totals(rec: dict) -> dict:
    rows = rec["rows"]
    n = len(rows)
    return {"seat": rec["seat"], "k": rec["k"], "behind": rec["behind"], "depths": n,
            "disagree": sum(r["disagree"] for r in rows), "we_only": sum(len(r["we_only"]) for r in rows),
            "they_only": sum(len(r["they_only"]) for r in rows),
            "mean_mad": sum(r["mad"] for r in rows) / n if n else 0.0,
            "freq": {r["depth"]: (r["freq_mixed"], r["freq_theirs"]) for r in rows}}


def parse_depths(spec: str) -> list[int]:
    out: list[int] = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            out.extend(range(lo, hi + 1))
        elif part:
            out.append(int(part))
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--file", help="local copy of push-fold-ranges.json")
    p.add_argument("--url", default=RMH_URL)
    p.add_argument("--cache", default=str(DEFAULT_CACHE), help="download dir, outside the repo")
    p.add_argument("--depths", default="2-25")
    p.add_argument("--threshold", type=float, default=0.5)
    p.add_argument("--worst", type=int, default=8)
    p.add_argument("--seats", default=",".join(s[0] for s in SEATS), help="labels: " + ",".join(s[0] for s in SEATS))
    p.add_argument("--tables-dir", default=None)
    a = p.parse_args(argv)

    if a.file:
        path = Path(a.file)
    else:
        try:
            path = fetch(a.url, Path(a.cache))
        except Exception as e:  # noqa: BLE001
            print(f"download failed ({e}); pass --file with a local copy of {Path(a.url).name}", file=sys.stderr)
            return 2
    raw = path.read_bytes()
    if len(raw) > MAX_BYTES:
        print(f"{path}: larger than {MAX_BYTES} B; refusing", file=sys.stderr)
        return 2
    try:
        rmh = parse_rmh(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        print(f"{path}: {e}", file=sys.stderr)
        return 2

    tables = load(need_hu=True) if a.tables_dir is None else load(a.tables_dir, need_hu=True)
    mw = load_multiway(tables, a.tables_dir)
    if mw is None:
        print("no usable tables/pushfold_multi.json for this matrix; run tools/gen_multiway.py", file=sys.stderr)
        return 1
    wanted = set(a.seats.split(","))
    seats = [s for s in SEATS if s[0] in wanted]
    results = run_check(rmh, mw, parse_depths(a.depths), a.threshold, a.worst, seats)
    if not results:
        print("no overlapping seats/depths", file=sys.stderr)
        return 1

    meta = rmh["meta"]
    print(f"{ATTRIBUTION}; {meta.get('name', '?')} v{meta.get('version', '?')} ({meta.get('lastVerified', '?')}), "
          f"{path.name} sha256 {hashlib.sha256(raw).hexdigest()[:16]}, {len(rmh['spots'])} spots\n"
          f"vs tables/pushfold_multi.json (matrix {mw['matrix_fp']}), threshold {a.threshold}\n")
    for rec in results:
        print(render(rec, a.worst))
        print()
    print("| seat | behind (RMH / ours) | depths | disagreements (we / they) | per depth | mean MAD | "
          "shove % ours / RMH at 5, 10, 15, 20 bb |")
    print("|---|---|---|---|---|---|---|")
    for rec in results:
        t = totals(rec)
        fr = " ; ".join(f"{d}: {t['freq'][d][0] * 100:.1f} / {t['freq'][d][1] * 100:.1f}" for d in (5, 10, 15, 20)
                        if d in t["freq"])
        print(f"| {t['seat']} | {t['behind']} / {t['k']} | {t['depths']} | {t['disagree']} ({t['we_only']} / {t['they_only']}) | "
              f"{t['disagree'] / t['depths']:.1f} | {t['mean_mad']:.3f} | {fr} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
