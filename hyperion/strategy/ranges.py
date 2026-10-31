"""Equity of each hand class against "the top x of hands", for reading an opponent's range from its frequency.

A shover who shoves one hand in fifty holds about the top 2% (AA-QQ, AKs); one who shoves every hand holds a
random hand. `RangeEquity.eq(cls, x)` is the all-in equity of `cls` against the top x of hands ordered by
`tables.rank` (heads-up strength), from the heads-up matrix with card removal, on a fixed grid of x and linear
between grid points. Built once per table set (~25 ms) and shared; a decision costs one interpolation.

Hands that are not one of the 169 classes (3- and 4-card variant labels) are not covered: `eq` returns None and
the caller keeps its older rule.
"""
from __future__ import annotations

from operator import mul

from .pushfold import matrix_fingerprint, removal_weights
from .tables import CLASSES, CLASS_INDEX, Tables

GRID = (0.01, 0.015, 0.02, 0.03, 0.045, 0.06, 0.08, 0.10, 0.13, 0.16, 0.20, 0.25, 0.32, 0.40, 0.50, 0.65, 0.80, 1.0)

_CACHE: dict = {}


class RangeEquity:
    def __init__(self, tables: Tables):
        n = len(CLASSES)
        live = tables.live
        counts = [tables.combo_count.get(c, 0) if (live is None or live[i]) else 0 for i, c in enumerate(CLASSES)]
        total = float(sum(counts)) or 1.0
        order = sorted(range(n), key=lambda i: -tables.rank[CLASSES[i]])
        w = removal_weights(live)
        hu = tables.hu
        we = [[w[i][j] * hu[i][j] for j in range(n)] for i in range(n)]
        self.grid = GRID
        self.table: list[list[float]] = []  # [grid index][class index]
        for x in GRID:
            rng = [0.0] * n
            left = x * total
            for i in order:
                c = counts[i]
                if c <= 0:
                    continue
                if left <= 0:
                    break
                take = c if c <= left else left
                rng[i] = take / c
                left -= take
            row = []
            for i in range(n):
                den = sum(map(mul, w[i], rng))
                row.append(sum(map(mul, we[i], rng)) / den if den > 0 else 0.5)
            self.table.append(row)

    def eq(self, cls: str, x: float):
        """Equity of `cls` vs the top x (0..1] of hands; None for a class outside the 169."""
        i = CLASS_INDEX.get(cls, -1)
        if i < 0:
            return None
        g = self.grid
        t = self.table
        if x <= g[0]:
            return t[0][i]
        if x >= g[-1]:
            return t[-1][i]
        k = 1
        while g[k] < x:
            k += 1
        x0, x1 = g[k - 1], g[k]
        a = (x - x0) / (x1 - x0)
        return t[k - 1][i] + a * (t[k][i] - t[k - 1][i])


def range_equity(tables: Tables) -> RangeEquity:
    key = (tables.dir, matrix_fingerprint(tables.hu), tables.live is None)
    r = _CACHE.get(key)
    if r is None:
        r = _CACHE[key] = RangeEquity(tables)
    return r
