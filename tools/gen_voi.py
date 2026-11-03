#!/usr/bin/env python
"""The twist decisions' option values (tables/voi.json): what a two-card hand is worth by Hero's read, for the
decisions Hero prices as value of information (hyperion.strategy.hero.HeroCore.variant_decide with Config.voi on).

    .venv/bin/python tools/gen_voi.py --workers 1

Cells are keyed as tools/gen_auction.py keys them: Hero's read (hyperion.strategy.postflop.Postflop.read: the made-hand
tier 0..8 and the draw outs, bucketed 0 / 1-4 / 5-8 / 9+) and the opponents still in (1, 2, 3, 4+). The Monte Carlo
deals random cards and runs the hand to the river; a cell's value is my mean share of the pot (ties split):

  flop<N>   two cards on the flop against opponents dealt N cards who each kept their best two by the flop (the made
            hand with the flop, then a pair, suited, the higher ranks: hyperion.drills.variants.default_keep's rule);
            everyone's discards are dead. N = 2 is plain hold'em, 3 the toss (toss_or_holdem), 5 deal 5 keep 2. My own
            N - 2 discards are dead too, and the read that keys the cell has them as dead cards.
  turn      two cards on the turn against random two-card hands: one card to come (swap_one_turn's swap).
  buy       the bonus card on the flop, every opponent holding three (the hook's default is to buy): "e3" my share
            holding a third card, "e2" without it.

Stdlib + multiprocessing only; about two minutes on one worker at the default samples.
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
FLOP_N = (2, 3, 5)


def outs_bucket(outs: int) -> int:
    return 0 if outs <= 0 else 1 if outs <= 4 else 2 if outs <= 8 else 3


def _share(me: int, others: list[int]) -> float:
    best = max(others) if others else -1
    if me > best:
        return 1.0
    if me < best:
        return 0.0
    return 1.0 / (1 + sum(1 for s in others if s == me))


def best_two(cards: tuple, flop: tuple) -> tuple:
    """The two an opponent keeps: the best made hand with the flop, ties to a pair, suited, the higher ranks."""
    best, key = None, None
    n = len(cards)
    for i in range(n):
        a = cards[i]
        for j in range(i + 1, n):
            b = cards[j]
            k = (evaluate((a, b) + flop), (a >> 2) == (b >> 2), (a & 3) == (b & 3), max(a >> 2, b >> 2),
                 min(a >> 2, b >> 2))
            if key is None or k > key:
                best, key = (a, b), k
    return best


def job(args):
    kind, n_dealt, k, samples, seed = args
    warm(8)
    rng = random.Random(seed)
    read = Postflop.read
    deck = list(range(52))
    acc: dict[str, list[float]] = {}
    for _ in range(samples):
        if kind == "flop":
            need = n_dealt + 3 + n_dealt * k + 2
            cards = rng.sample(deck, need)
            mine_all = tuple(cards[:n_dealt])
            hole, own_dead = mine_all[:2], mine_all[2:]
            flop = tuple(cards[n_dealt:n_dealt + 3])
            off = n_dealt + 3
            opps = []
            for i in range(k):
                dealt = tuple(cards[off + n_dealt * i:off + n_dealt * (i + 1)])
                opps.append(dealt if n_dealt == 2 else best_two(dealt, flop))
            board = flop + tuple(cards[off + n_dealt * k:off + n_dealt * k + 2])
            tier, outs, _ = read(hole, flop, own_dead)
            e = _share(evaluate(hole + board), [evaluate(o + board) for o in opps])
            vals = (e,)
        elif kind == "turn":
            cards = rng.sample(deck, 2 + 4 + 2 * k + 1)
            hole, turn = tuple(cards[:2]), tuple(cards[2:6])
            opps = [tuple(cards[6 + 2 * i:8 + 2 * i]) for i in range(k)]
            board = turn + (cards[6 + 2 * k],)
            tier, outs, _ = read(hole, turn)
            vals = (_share(evaluate(hole + board), [evaluate(o + board) for o in opps]),)
        else:  # buy
            cards = rng.sample(deck, 3 + 3 + 3 * k + 2)
            hole, extra, flop = tuple(cards[:2]), cards[2], tuple(cards[3:6])
            opps = [tuple(cards[6 + 3 * i:9 + 3 * i]) for i in range(k)]
            board = flop + tuple(cards[6 + 3 * k:8 + 3 * k])
            tier, outs, _ = read(hole, flop)
            others = [evaluate(o + board) for o in opps]
            vals = (_share(evaluate(hole + (extra,) + board), others), _share(evaluate(hole + board), others))
        key = f"{tier},{outs_bucket(outs)}"
        a = acc.get(key)
        if a is None:
            a = acc[key] = [0] + [0.0] * len(vals)
        a[0] += 1
        for i, v in enumerate(vals):
            a[i + 1] += v
    return kind, n_dealt, k, acc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--samples", type=int, default=240_000, help="per table and opponent count")
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--out", default=str(ROOT / "tables" / "voi.json"))
    a = p.parse_args(argv)
    t0 = time.perf_counter()
    chunks = 4
    specs = [("flop", n) for n in FLOP_N] + [("turn", 2), ("buy", 2)]
    jobs = [(kind, n, k, a.samples // chunks, a.seed * 7919 + i * 997 + k * 13 + c)
            for i, (kind, n) in enumerate(specs) for k in OPP for c in range(chunks)]
    merged: dict = {}
    with Pool(a.workers) as pool:
        for kind, n, k, acc in pool.imap_unordered(job, jobs):
            m = merged.setdefault((kind, n, k), {})
            for key, v in acc.items():
                t = m.setdefault(key, [0] + [0.0] * (len(v) - 1))
                for i in range(len(v)):
                    t[i] += v[i]
    out: dict = {}
    for (kind, n, k), cells in sorted(merged.items()):
        name = f"flop{n}" if kind == "flop" else kind
        tab = out.setdefault(name, {})
        cols = ("e3", "e2") if kind == "buy" else ("e",)
        tab[str(k)] = {key: {"n": int(v[0]), **{c: round(v[i + 1] / v[0], 4) for i, c in enumerate(cols)}}
                       for key, v in sorted(cells.items())}
    doc = {"what": "twist decisions' option values: my pot share by Hero's read (tier,outs bucket) and opponents "
                   "(1..4+); flop<N>: opponents kept their best two of N by the flop; turn: one card to come; buy: the "
                   "bonus card against opponents holding three",
           "outs_buckets": "0: 0, 1: 1-4, 2: 5-8, 3: 9+", "samples": a.samples, "seed": a.seed,
           "generator": "tools/gen_voi.py", "seconds": round(time.perf_counter() - t0, 1), "tables": out}
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"{a.out}: {sum(len(c) for t in out.values() for c in t.values())} cells in {doc['seconds']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
