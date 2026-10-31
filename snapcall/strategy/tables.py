"""Load the JSON tables under tables/ into plain dicts, or build defaults when they are missing.

Decision-path code only ever touches the dicts returned by `load()`. The generators here run
offline (tools/gen_tables.py calls them) or as a slow fallback so tests and the hero work on a
cold clone. Formats:

  preflop_equity.json  {cls: [equity vs 1 opp, vs 2, ..., vs 7]}      all 169 classes
  preflop_rank.json    {cls: fraction of combos strictly weaker by heads-up equity, 0..1}
  hu_matrix.json       {"classes": [169 names], "equity": [[e(i vs j)]]}  e[j][i] = 1 - e[i][j]
"""
from __future__ import annotations

import json
import os
import random
from typing import Sequence

from ..core.cards import all_hole_classes, class_combos, deck_for, is_identity_order, remap
from ..core.equity import preflop_equity, showdown_share
from ..core.types import Rules

TABLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tables")
CLASSES: tuple[str, ...] = tuple(all_hole_classes())
CLASS_INDEX: dict[str, int] = {c: i for i, c in enumerate(CLASSES)}
MAX_OPP = 7
TOTAL_COMBOS = 1326


def combos_of(cls: str) -> int:
    return 6 if cls[0] == cls[1] else 4 if cls[2] == "s" else 12


COMBO_COUNT: tuple[int, ...] = tuple(combos_of(c) for c in CLASSES)


def rank_from_equity(equity: dict[str, Sequence[float]]) -> dict[str, float]:
    """Combo-weighted midpoint percentile by heads-up equity (same definition as snapcall.tablegen):
    32o ~ 0.005, AA ~ 0.998. 'Top X of hands' means rank >= 1 - X."""
    order = sorted(CLASSES, key=lambda c: equity[c][0])
    out: dict[str, float] = {}
    below = 0
    for c in order:
        k = combos_of(c)
        out[c] = round((below + 0.5 * k) / TOTAL_COMBOS, 4)
        below += k
    return out


def _equity_row(args) -> tuple[str, list[float]]:
    cls, samples, seed, rules = args
    rng = random.Random(seed)
    return cls, [preflop_equity(cls, n, samples, rules, seed=rng.randrange(1 << 30)) for n in range(1, MAX_OPP + 1)]


def build_default_tables(samples: int = 200, rules: Rules = Rules(), seed: int = 0, workers: int = 1):
    """(equity, rank) dicts from core.equity. `samples` is per class per opponent count."""
    jobs = [(c, samples, seed * 1000 + i, rules) for i, c in enumerate(CLASSES)]
    if workers > 1:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            rows = pool.map(_equity_row, jobs, chunksize=4)
    else:
        rows = [_equity_row(j) for j in jobs]
    equity = {c: row for c, row in rows}
    return equity, rank_from_equity(equity)


def _hu_pair(args) -> tuple[int, int, float]:
    i, j, samples, seed, rules = args
    rng = random.Random(seed)
    ident = is_identity_order(rules)
    a_combos = class_combos(CLASSES[i])
    b_combos = class_combos(CLASSES[j])
    deck = deck_for(rules)
    total = 0.0
    n = 0
    while n < samples:
        a = a_combos[rng.randrange(len(a_combos))]
        b = b_combos[rng.randrange(len(b_combos))]
        if a[0] in b or a[1] in b:
            continue
        dead = (a[0], a[1], b[0], b[1])
        board = []
        while len(board) < rules.board_sizes[-1]:
            c = deck[rng.randrange(len(deck))]
            if c not in dead and c not in board:
                board.append(c)
        if not ident:
            a2, b2, board2 = remap(a, rules), remap(b, rules), remap(board, rules)
        else:
            a2, b2, board2 = a, b, board
        total += showdown_share(a2, (b2,), board2)
        n += 1
    return i, j, total / samples


def build_hu_matrix(samples: int = 300, rules: Rules = Rules(), seed: int = 0, workers: int = 1) -> list[list[float]]:
    """169x169 all-in equity matrix e[i][j] = equity of CLASSES[i] vs CLASSES[j], random boards."""
    n = len(CLASSES)
    jobs = [(i, j, samples, seed * 100003 + i * 169 + j, rules) for i in range(n) for j in range(i + 1, n)]
    if workers > 1:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            res = pool.map(_hu_pair, jobs, chunksize=64)
    else:
        res = [_hu_pair(j) for j in jobs]
    m = [[0.5] * n for _ in range(n)]
    for i, j, e in res:
        m[i][j] = e
        m[j][i] = 1.0 - e
    return m


def write_json(name: str, obj, tables_dir: str = TABLES_DIR) -> str:
    os.makedirs(tables_dir, exist_ok=True)
    path = os.path.join(tables_dir, name)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    return path


def read_json(name: str, tables_dir: str = TABLES_DIR):
    path = os.path.join(tables_dir, name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


class Tables:
    """Plain-dict holder. equity[cls][n-1] = equity vs n opponents; rank[cls] in 0..1."""

    __slots__ = ("equity", "rank", "hu", "source")

    def __init__(self, equity: dict, rank: dict, hu: list[list[float]] | None, source: str):
        self.equity = equity
        self.rank = rank
        self.hu = hu
        self.source = source


_CACHE: dict[str, Tables] = {}


def load(tables_dir: str = TABLES_DIR, fallback_samples: int = 60, need_hu: bool = False) -> Tables:
    """Load tables from disk; build small defaults for anything missing. Cached per directory."""
    key = tables_dir + ("+hu" if need_hu else "")
    t = _CACHE.get(key)
    if t is not None:
        return t
    base = _CACHE.get(tables_dir)
    equity = base.equity if base else read_json("preflop_equity.json", tables_dir)
    rank = base.rank if base else read_json("preflop_rank.json", tables_dir)
    source = "disk"
    if not equity or any(c not in equity for c in CLASSES):
        equity, rank = build_default_tables(fallback_samples)
        source = "built"
    elif not rank or any(c not in rank for c in CLASSES):
        rank = rank_from_equity(equity)
    hu = base.hu if base else None
    if need_hu and hu is None:
        raw = read_json("hu_matrix.json", tables_dir)
        if raw and sorted(raw.get("classes", ())) == sorted(CLASSES) and len(raw.get("equity", ())) == len(CLASSES):
            names = raw["classes"]
            if names == list(CLASSES):
                hu = raw["equity"]
            else:  # another generator's class order: permute into ours
                idx = [names.index(c) for c in CLASSES]
                hu = [[raw["equity"][a][b] for b in idx] for a in idx]
        else:
            hu = build_hu_matrix(40)
            source = "built"
    t = Tables(equity, rank, hu, source)
    _CACHE[key] = t
    if need_hu:
        _CACHE[tables_dir] = t
    return t
