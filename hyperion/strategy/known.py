"""Known cards: cards an opponent is known to hold, including cards we hold too, priced as theirs (V-h).

Where they come from (Observation.extras; displayed cards, seats as the observation numbers them):
  extras["exposed"]  {seat: card}: face-up cards everyone sees (the catalog's exposed_card)
  extras["known"]    {seat: cards}: the cards this seat is known to hold, from where we sit. A card may be ours too: a
                     card two players share (Chain Hold'em's links) is in both hands. When one dict serves every seat
                     (our simulator's extras), it is keyed by the viewer first: {viewer: {seat: cards}}.
Our own seat is never an opponent; a seat may appear in both keys (the cards are joined).

What a known card means for us, against one opponent o who is known to hold K:
  shared   K & our hole: in both hands, so it cannot separate us; against o it plays as a board card
  exposed  K - our hole: in o's hand, out of the deck (draw outs), and his hand is built around it
  mine     our hole - K: the cards that separate us from o
`parse` reads the extras; `split` cuts one opponent's cards that way; `equity` prices our hand heads-up against o
before the flop from a prepared table (tables/known_<shape>.json: our equity against a random completion of o's hand,
the shared cards in both, five board cards to come, best five of everything, ties split), keyed by the suit-invariant
`key`. Hero turns that equity into a hand class (Config.known_cards); the postflop read moves shared cards to the
board (Postflop.act's `shared`).

Tables (stdlib, offline; never on the decision path):
    python -m hyperion.strategy.known --build 1,2,0,1 --samples 6000 --workers 2   (Chain heads-up: 1 private card,
        2 shared links, nothing exposed, 1 unknown card of his)
    python -m hyperion.strategy.known --build 2,1,0,2   (Chain against one neighbour)
    python -m hyperion.strategy.known --build 2,0,1,1   (exposed_card heads-up: our 2 against his face-up card + 1)
Shape = (our separating cards, shared cards, his exposed cards, his unknown cards). A shape with no file prices
nothing (the class stays the dealt one).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from bisect import bisect_left
from itertools import combinations

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLES_DIR = os.path.join(_ROOT, "tables")
_ALPHA = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLM"  # group * 13 + rank -> one character (three groups)
_TABLES: dict = {}  # shape -> {key: equity} or None (no file), per process


def _cards(v, out: list) -> None:
    if isinstance(v, bool):
        return
    if isinstance(v, int):
        if 0 <= v < 52:
            out.append(v)
    elif isinstance(v, (list, tuple, set, frozenset)):
        for x in v:
            _cards(x, out)


def _seat(s):
    if isinstance(s, int):
        return s
    try:
        return int(s)
    except (TypeError, ValueError):
        return None


def parse(extras: dict, me: int, rank_order=None) -> dict:
    """{seat: tuple of canonical cards} each other seat is known to hold (module doc); {} when nothing is known.
    `rank_order`: the table's rank permutation (cards remapped as Hero remaps its own), None for identity."""
    out: dict = {}
    ex = extras.get("exposed")
    if ex and isinstance(ex, dict):
        for s, c in ex.items():
            s = _seat(s)
            if s is None or s == me:
                continue
            got: list = []
            _cards(c, got)
            if got:
                out.setdefault(s, []).extend(got)
    kn = extras.get("known")
    if kn and isinstance(kn, dict):
        mine = kn.get(me, kn.get(str(me)))
        flat = kn
        if isinstance(mine, dict):
            flat = mine
        elif any(isinstance(v, dict) for v in kn.values()):
            flat = {}  # keyed by viewer, and nothing for us
        for s, c in flat.items():
            s = _seat(s)
            if s is None or s == me:
                continue
            got = []
            _cards(c, got)
            if got:
                out.setdefault(s, []).extend(got)
    res = {}
    for s, cs in out.items():
        if rank_order is not None:
            cs = [rank_order[c >> 2] * 4 + (c & 3) for c in cs]
        res[s] = tuple(sorted(set(cs)))
    return res


def split(hole, cards) -> tuple[tuple, tuple, tuple]:
    """(mine, shared, exposed) for an opponent known to hold `cards` (module doc)."""
    k = set(cards)
    mine = tuple(c for c in hole if c not in k)
    shared = tuple(c for c in hole if c in k)
    exposed = tuple(c for c in cards if c not in shared)
    return mine, shared, exposed


def key(mine, shared, exposed) -> str:
    """Suit-invariant key: per suit, the sorted (group, rank) characters of its cards; the suits' strings sorted.
    Two hands get one key exactly when a suit permutation maps one onto the other."""
    per = ["", "", "", ""]
    a = _ALPHA
    for c in mine:
        per[c & 3] += a[c >> 2]
    for c in shared:
        per[c & 3] += a[13 + (c >> 2)]
    for c in exposed:
        per[c & 3] += a[26 + (c >> 2)]
    return ".".join(sorted("".join(sorted(x)) for x in per if x))


def shape_name(shape) -> str:
    m, s, x, u = shape
    return f"known_m{m}s{s}x{x}u{u}.json"


def table(shape, tables_dir: str = TABLES_DIR):
    """The prepared {key: equity} for a shape, or None (no file); read once per process."""
    shape = tuple(int(v) for v in shape)
    t = _TABLES.get((shape, tables_dir), False)
    if t is False:
        t = None
        path = os.path.join(tables_dir, shape_name(shape))
        try:
            with open(path) as fh:
                doc = json.load(fh)
            if tuple(doc.get("shape") or ()) == shape:
                t = {k: float(v) for k, v in (doc.get("equity") or {}).items()}
        except (OSError, ValueError, TypeError):
            t = None
        _TABLES[(shape, tables_dir)] = t
    return t


SHAPES = ((1, 2, 0, 1), (2, 1, 0, 2), (2, 0, 1, 1))  # the prepared shapes (module doc)


def preload(hole_cards: int, tables_dir: str = TABLES_DIR) -> None:
    """Read the prepared shapes a game with this many hole cards can ask for (at a table start: never in a decision)."""
    for shape in SHAPES:
        if shape[0] + shape[1] == hole_cards:
            table(shape, tables_dir)


def equity(mine, shared, exposed, unknown: int, tables_dir: str = TABLES_DIR):
    """Our heads-up preflop equity against an opponent holding `shared` + `exposed` + `unknown` random cards, or None
    when the shape has no prepared table (or the key is missing: a deck the table was not built for)."""
    t = table((len(mine), len(shared), len(exposed), unknown), tables_dir)
    if t is None:
        return None
    return t.get(key(mine, shared, exposed))


def ladder(t, pre):
    """(equities ascending, their classes): every class of the table set `t` by its heads-up equity in the preflop
    module `pre` (whose dicts the decisions read), for `class_at`. None when the set lists no classes (a label view)."""
    classes = tuple(getattr(t, "classes", ()) or ())
    if not classes and isinstance(getattr(pre, "rank", None), dict):
        classes = tuple(pre.rank)
    cc = getattr(t, "combo_count", None) or {}
    pts = []
    for c in classes:
        if cc and cc.get(c, 1) == 0:
            continue  # a class this deck cannot deal
        try:
            pts.append((float(pre.equity[c][0]), c))
        except (KeyError, TypeError, IndexError, ValueError):
            continue
    if len(pts) < 10:
        return None
    pts.sort()
    return [e for e, _ in pts], [c for _, c in pts]


def class_at(lad, e: float) -> str:
    """The class whose heads-up equity is nearest `e`."""
    eqs, cls = lad
    i = bisect_left(eqs, e)
    if i <= 0:
        return cls[0]
    if i >= len(eqs):
        return cls[-1]
    return cls[i] if eqs[i] - e < e - eqs[i - 1] else cls[i - 1]


# ------------------------------------------------------------------ the tables (offline)

def representatives(shape) -> dict:
    """{key: (mine, shared, exposed)}: one hand per suit-isomorphism class of the shape."""
    m, s, x, _ = shape
    deck = range(52)
    out: dict = {}
    for mine in combinations(deck, m):
        rest = [c for c in deck if c not in mine]
        for shared in combinations(rest, s):
            rest2 = [c for c in rest if c not in shared]
            for exposed in combinations(rest2, x):
                k = key(mine, shared, exposed)
                if k not in out:
                    out[k] = (mine, shared, exposed)
    return out


def _mc(args) -> tuple[str, float]:
    k, (mine, shared, exposed), unknown, board_n, samples, seed = args
    from ..core.eval import evaluate, warm

    warm(8)
    rng = random.Random(seed)
    known = set(mine) | set(shared) | set(exposed)
    stub = [c for c in range(52) if c not in known]
    me0 = tuple(mine) + tuple(shared)
    op0 = tuple(shared) + tuple(exposed)
    take = unknown + board_n
    acc = 0.0
    sample = rng.sample
    for _ in range(samples):
        pick = sample(stub, take)
        b = tuple(pick[unknown:])
        a = evaluate(me0 + b)
        o = evaluate(op0 + tuple(pick[:unknown]) + b)
        acc += 1.0 if a > o else 0.5 if a == o else 0.0
    return k, acc / samples


def build(shape, samples: int = 6000, seed: int = 2026, workers: int = 1, tables_dir: str = TABLES_DIR,
          board_n: int = 5) -> str:
    shape = tuple(int(v) for v in shape)
    reps = representatives(shape)
    keys = sorted(reps)
    jobs = [(k, reps[k], shape[3], board_n, samples, seed * 100003 + i) for i, k in enumerate(keys)]
    t0 = time.time()
    if workers > 1:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            res = pool.map(_mc, jobs, chunksize=16)
    else:
        res = [_mc(j) for j in jobs]
    eq = {k: round(e, 4) for k, e in res}
    doc = {"shape": list(shape), "what": "heads-up preflop equity: (our separating cards, shared cards, his exposed "
                                        "cards, his unknown cards); best five of hole + board, ties split",
           "board": board_n, "samples": samples, "seed": seed, "keys": len(eq), "seconds": round(time.time() - t0, 1),
           "equity": eq}
    path = os.path.join(tables_dir, shape_name(shape))
    with open(path, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"), sort_keys=True)
        fh.write("\n")
    return path


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.strategy.known", description=__doc__.split("\n\n")[0])
    p.add_argument("--build", required=True, metavar="M,S,X,U", help="the shape to prepare (module doc)")
    p.add_argument("--samples", type=int, default=6000)
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--workers", type=int, default=1)
    p.add_argument("--out", default=TABLES_DIR)
    a = p.parse_args(argv)
    shape = tuple(int(v) for v in a.build.split(","))
    if len(shape) != 4:
        raise SystemExit("--build takes four numbers: M,S,X,U")
    print(build(shape, a.samples, a.seed, a.workers, a.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
