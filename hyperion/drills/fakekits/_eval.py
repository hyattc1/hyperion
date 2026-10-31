"""The fake kits' own cards and showdown evaluator. Standard library only, no hyperion import.

A drill copies a kit verbatim into a blank directory (drill 3 could not: `_table.py` pulled in
`hyperion.core`, and copying that would have handed a Track B agent the real evaluator). This is
brute force over the 5-card subsets, which is plenty for a dealer that evaluates a handful of hands
per showdown, and it orders hands exactly as `hyperion.core.eval` does (its `_classify` tuple, so
the split-pot and winner decisions in `_table._showdown` are unchanged).
"""
from __future__ import annotations

from itertools import combinations

RANKS = "23456789TJQKA"
SUITS = "cdhs"
FULL_DECK: tuple[int, ...] = tuple(range(52))  # rank * 4 + suit, rank 0 = deuce, 12 = ace
_STRAIGHT_MASKS = frozenset(0b11111 << i for i in range(9))
_WHEEL = 0b1000000001111
_PATTERN_CATEGORY = {(3, 1, 1): 3, (2, 2, 1): 2, (2, 1, 1, 1): 1}


def card_str(c: int) -> str:
    return RANKS[c >> 2] + SUITS[c & 3]


def classify5(five) -> tuple:
    """(category, tiebreaks...) for exactly five cards; a larger tuple is a stronger hand.
    Category: 0 high card, 1 pair, 2 two pair, 3 trips, 4 straight, 5 flush, 6 full house, 7 quads,
    8 straight flush. Same tuple as hyperion.core.eval._classify."""
    flush = len({c & 3 for c in five}) == 1
    counts: dict[int, int] = {}
    mask = 0
    for c in five:
        r = c >> 2
        counts[r] = counts.get(r, 0) + 1
        mask |= 1 << r
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    pattern = tuple(n for _, n in groups)
    kick = tuple(r for r, _ in groups)
    straight_top = -1
    if len(counts) == 5:
        if mask == _WHEEL:
            straight_top = 3  # five-high
        elif mask in _STRAIGHT_MASKS:
            straight_top = kick[0]
    if flush and straight_top >= 0:
        return (8, straight_top)
    if pattern == (4, 1):
        return (7,) + kick
    if pattern == (3, 2):
        return (6,) + kick
    if flush:
        return (5,) + kick
    if straight_top >= 0:
        return (4, straight_top)
    return (_PATTERN_CATEGORY.get(pattern, 0),) + kick


def evaluate(cards) -> tuple:
    """Best five-card hand among `cards` (five or more) as a comparable tuple. Equal tuples split."""
    return max(classify5(five) for five in combinations(cards, 5))
