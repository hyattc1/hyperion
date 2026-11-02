#!/usr/bin/env python
"""The auction entry's bid table (tables/auction_bid.json): what a third hole card is worth on the flop.

    .venv/bin/python tools/gen_auction.py --workers 2

For a random flop and two hole cards, bucketed by Hero's flop read (hyperion.strategy.postflop.Postflop.read: the
made-hand tier 0..8 and the draw outs, 0 / 1-4 / 5-8 / 9+) and by the opponents still in (1, 2, 3, 4+), the Monte Carlo
runs the hand to the river twice on the same cards:
  win    I get the third card, every opponent keeps two          -> my share of the pot, e_win
  lose   the first opponent gets the third card, I keep two       -> my share, e_lose
d = e_win - e_lose is what winning the auction instead of losing it is worth, as a share of the pot. Hero's bid is
the price at which winning and losing come out level when the price goes into the pot: d x pot / (1 - d)
(hyperion.strategy.hero.HeroCore._bid). Shares split ties; opponents' cards are random (no range reading).
Stdlib + multiprocessing only; under a minute on two workers at the default 2,000,000 samples per opponent count.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion.core.eval import evaluate, warm  # noqa: E402
from hyperion.strategy.postflop import Postflop  # noqa: E402

OPP = (1, 2, 3, 4)  # 4 stands for four or more
OUTS = (0, 4, 8)  # outs buckets: 0, 1-4, 5-8, 9+


def outs_bucket(outs: int) -> int:
    return 0 if outs <= 0 else 1 if outs <= 4 else 2 if outs <= 8 else 3


def _shares(scores: list[int]) -> list[float]:
    best = max(scores)
    w = [1.0 if s == best else 0.0 for s in scores]
    n = sum(w)
    return [x / n for x in w]


def job(args):
    k, samples, seed = args
    warm(8)
    rng = random.Random(seed)
    read = Postflop.read
    deck = list(range(52))
    acc: dict[str, list[float]] = {}  # "tier,outs" -> [n, sum e_win, sum e_lose, sum e_2]
    need = 2 + 3 + 2 * k + 2 + 2
    for _ in range(samples):
        cards = rng.sample(deck, need)
        hole, flop = tuple(cards[:2]), tuple(cards[2:5])
        opps = [tuple(cards[5 + 2 * i:7 + 2 * i]) for i in range(k)]
        mine3, theirs3 = cards[5 + 2 * k], cards[6 + 2 * k]
        board = flop + tuple(cards[7 + 2 * k:9 + 2 * k])
        tier, outs, _ = read(hole, flop)
        key = f"{tier},{outs_bucket(outs)}"
        me2 = evaluate(hole + board)
        me3 = evaluate(hole + (mine3,) + board)
        others = [evaluate(o + board) for o in opps]
        opp0_3 = evaluate(opps[0] + (theirs3,) + board)
        e_win = _shares([me3] + others)[0]
        e_lose = _shares([me2, opp0_3] + others[1:])[0]
        e_2 = _shares([me2] + others)[0]
        a = acc.get(key)
        if a is None:
            a = acc[key] = [0, 0.0, 0.0, 0.0]
        a[0] += 1
        a[1] += e_win
        a[2] += e_lose
        a[3] += e_2
    return k, acc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--samples", type=int, default=2_000_000, help="per opponent count")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=2024)
    p.add_argument("--out", default=str(ROOT / "tables" / "auction_bid.json"))
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    chunks = 8
    jobs = [(k, a.samples // chunks, a.seed * 1009 + k * 101 + c) for k in OPP for c in range(chunks)]
    merged: dict[int, dict[str, list[float]]] = {k: {} for k in OPP}
    with Pool(a.workers) as pool:
        for k, acc in pool.imap_unordered(job, jobs):
            m = merged[k]
            for key, v in acc.items():
                t = m.setdefault(key, [0, 0.0, 0.0, 0.0])
                for i in range(4):
                    t[i] += v[i]
    table = {}
    for k in OPP:
        cells = {}
        for key, (n, sw, sl, s2) in sorted(merged[k].items()):
            cells[key] = {"n": int(n), "e_win": round(sw / n, 4), "e_lose": round(sl / n, 4), "e_two": round(s2 / n, 4),
                          "d": round((sw - sl) / n, 4)}
        table[str(k)] = cells
    out = {"what": "auction entry: the third card's worth by flop read (tier,outs bucket) and opponents (1..4+)",
           "outs_buckets": "0: 0, 1: 1-4, 2: 5-8, 3: 9+", "samples_per_opp": a.samples, "seed": a.seed,
           "generator": "tools/gen_auction.py", "seconds": round(time.perf_counter() - t0, 1), "d": table}
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    print(f"{a.out}: {sum(len(v) for v in table.values())} cells in {out['seconds']} s")
    for k in OPP:
        ds = [(c["n"], c["d"]) for c in table[str(k)].values()]
        tot = sum(n for n, _ in ds)
        print(f"  {k} opp: mean d {sum(n * d for n, d in ds) / tot:.3f} over {tot} samples")
    return 0


if __name__ == "__main__":
    sys.exit(main())
