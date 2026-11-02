#!/usr/bin/env python
"""deal5_keep2's preflop table (tables/variants/deal5_keep2/heads.json): what five hole cards are worth when everyone
keeps two of five on the flop.

    .venv/bin/python tools/gen_keep2.py --workers 2

Hero's tables are keyed by hand class; five cards have no 169 class, so Hero reads them by their head, the Chen-best
two (hyperion.tablegen.hole_label's '<head>+<tags>'). With the default tables that view (the label view) prices a
five-card hand as its best two against random two-card hands: almost every five-card hand looks like a top-30% hand,
and F opened 78% of hands and busted 78% of tables (docs/drills/v-catalog-log.md). This table prices the head among
five-card hands instead. Monte Carlo: k + 1 players (k = 1..7 opponents) are dealt five cards and a board, each keeps
two on the flop with the hook's default keep (hyperion.drills.variants.default_keep: the best made hand on the flop),
and the pot goes to the best two-plus-board; every player's share is credited to its head class. Per head:
  equity[head][k-1]  share of the pot against k opponents (no one folds), shrunk toward the two-card equity plus
                     the mean five-card shift when a head has few samples (`--prior`, in samples)
  rank[head]         combo-weighted percentile among five-card hands by heads-up equity (the 169 definition, over
                     the heads' frequencies as five-card hands)
  freq[head]         how often a five-card hand has this head (sampled)
hyperion.strategy.tables.tables_for reads it (a 'headview': no tag bonuses, no extra tightening). Stdlib only.
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
from hyperion.drills.variants import default_keep  # noqa: E402
from hyperion.tablegen import hole_label  # noqa: E402

MAX_OPP = 7


def job(args):
    k, samples, seed = args
    warm(7)
    rng = random.Random(seed)
    deck = list(range(52))
    acc: dict[str, list[float]] = {}  # head -> [n, sum share]
    need = 5 * (k + 1) + 5
    for _ in range(samples):
        cards = rng.sample(deck, need)
        board = tuple(cards[-5:])
        flop = board[:3]
        scores, heads = [], []
        for p in range(k + 1):
            hole = tuple(cards[5 * p:5 * p + 5])
            i, j = default_keep(hole, flop)
            scores.append(evaluate((hole[i], hole[j]) + board))
            heads.append(hole_label(hole).partition("+")[0])
        best = max(scores)
        winners = sum(1 for s in scores if s == best)
        for h, s in zip(heads, scores):
            a = acc.get(h)
            if a is None:
                a = acc[h] = [0, 0.0]
            a[0] += 1
            a[1] += (1.0 / winners) if s == best else 0.0
    return k, acc


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--samples", type=int, default=200_000, help="deals per opponent count")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--prior", type=float, default=300.0, help="shrinkage weight toward the two-card prior, in samples")
    p.add_argument("--out", default=str(ROOT / "tables" / "variants" / "deal5_keep2" / "heads.json"))
    a = p.parse_args(argv)
    from hyperion.strategy.tables import CLASSES, COMBO_COUNT, load

    base = load(need_hu=False)
    t0 = time.perf_counter()
    chunks = 8
    jobs = [(k, a.samples // chunks, a.seed * 7919 + k * 131 + c) for k in range(1, MAX_OPP + 1) for c in range(chunks)]
    merged: dict[int, dict[str, list[float]]] = {k: {} for k in range(1, MAX_OPP + 1)}
    with Pool(a.workers) as pool:
        for k, acc in pool.imap_unordered(job, jobs):
            m = merged[k]
            for h, (n, s) in acc.items():
                t = m.setdefault(h, [0, 0.0])
                t[0] += n
                t[1] += s
    freq = {c: 0 for c in CLASSES}
    for k in merged:
        for h, (n, _) in merged[k].items():
            freq[h] += n
    equity = {}
    for c in CLASSES:
        equity[c] = [0.0] * MAX_OPP
    for k in range(1, MAX_OPP + 1):
        m = merged[k]
        tot_n = sum(n for n, _ in m.values())
        # the mean shift from the two-card equity, over the sampled hands: the prior for thin heads
        shift = sum(s - n * base.equity[h][k - 1] for h, (n, s) in m.items()) / tot_n
        for c in CLASSES:
            n, s = m.get(c, (0, 0.0))
            prior = min(0.999, max(0.001, base.equity[c][k - 1] + shift))
            equity[c][k - 1] = round((s + a.prior * prior) / (n + a.prior), 4)
    # rank: percentile among five-card hands by heads-up equity, weighted by how often each head occurs
    total = sum(freq.values())
    order = sorted(CLASSES, key=lambda c: equity[c][0])
    rank, below = {}, 0.0
    for c in order:
        w = freq[c] / total if total else COMBO_COUNT[CLASSES.index(c)] / 1326
        rank[c] = round(below + w / 2, 4)
        below += w
    out = {"what": "deal5_keep2 preflop: five-card hands by their Chen-best two (head), everyone keeping two on the flop",
           "keep": "hyperion.drills.variants.default_keep", "samples_per_opp": a.samples, "seed": a.seed,
           "prior": a.prior, "generator": "tools/gen_keep2.py", "seconds": round(time.perf_counter() - t0, 1),
           "equity": equity, "rank": rank, "freq": freq}
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(out, separators=(",", ":")) + "\n")
    top = sorted(CLASSES, key=lambda c: -rank[c])[:8]
    print(f"{a.out}: {out['seconds']} s; most common heads "
          f"{sorted(freq, key=lambda c: -freq[c])[:6]}; top by rank {top}")
    print("  e1 / e7 / rank:", {c: (equity[c][0], equity[c][6], rank[c]) for c in ("AA", "AKs", "KQo", "T9s", "77", "72o")})
    return 0


if __name__ == "__main__":
    sys.exit(main())
