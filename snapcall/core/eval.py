"""Pure-Python hand evaluator built for a 1 ms budget.

Strength is an int: higher is better, 1..7462 for 5-card classes. Any n>=5 cards evaluates the best
5-card hand. For n in 5..8, non-flush hands resolve in ONE dict lookup keyed by the product of rank
primes (tables built lazily at import or first use and memoized), and flush hands in one lookup keyed
by the rank bitmask of the suited cards. Typical 7-card evaluate: a few microseconds.

Rank permutation variants: pass a Rules whose rank_order is not identity and call evaluate_displayed,
or remap cards yourself with cards.remap. The tables never change.
"""
from __future__ import annotations

from itertools import combinations, combinations_with_replacement
from typing import Sequence

from .cards import remap, is_identity_order
from .types import Rules

PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
CATEGORY_NAMES = (
    "high card", "pair", "two pair", "trips", "straight", "flush", "full house", "quads", "straight flush",
)
_STRAIGHT_MASKS = [0b11111 << i for i in range(9)] + [0b1000000001111]  # wheel last
_WHEEL = 0b1000000001111


def _classify(ranks: Sequence[int], flush: bool) -> tuple:
    """(category, tiebreak...) for a 5-rank multiset. Larger tuple = stronger."""
    counts = {}
    for r in ranks:
        counts[r] = counts.get(r, 0) + 1
    groups = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    pattern = tuple(c for _, c in groups)
    distinct = len(counts) == 5
    mask = 0
    for r in ranks:
        mask |= 1 << r
    straight_top = -1
    if distinct:
        if mask == _WHEEL:
            straight_top = 3  # five-high
        elif mask in _STRAIGHT_MASKS:
            straight_top = max(ranks)
    kick = tuple(r for r, _ in groups)
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
    if pattern == (3, 1, 1):
        return (3,) + kick
    if pattern == (2, 2, 1):
        return (2,) + kick
    if pattern == (2, 1, 1, 1):
        return (1,) + kick
    return (0,) + kick


def _build_5card_tables() -> tuple[dict[int, int], dict[int, int], list[int]]:
    keys = []
    for combo in combinations_with_replacement(range(13), 5):
        if len(set(combo)) == 1:
            continue
        keys.append((_classify(combo, False), False, combo))
    for combo in combinations(range(13), 5):
        keys.append((_classify(combo, True), True, combo))
    keys.sort(key=lambda k: k[0])
    unsuited: dict[int, int] = {}
    flush: dict[int, int] = {}
    category_of: list[int] = [0] * (len(keys) + 1)
    for strength, (key, is_flush, combo) in enumerate(keys, start=1):
        category_of[strength] = key[0]
        if is_flush:
            m = 0
            for r in combo:
                m |= 1 << r
            flush[m] = strength
        else:
            p = 1
            for r in combo:
                p *= PRIMES[r]
            unsuited[p] = strength
    assert len(keys) == 7462, len(keys)
    return unsuited, flush, category_of


UNSUITED5, FLUSH5, CATEGORY_OF = _build_5card_tables()
MAX_STRENGTH = 7462

_FLUSH_N: dict[int, int] = dict(FLUSH5)  # bitmask with >=5 bits -> best flush strength
_UNSUITED_N: dict[int, dict[int, int]] = {5: UNSUITED5}  # n -> prime product -> best non-flush strength


def _best_flush_for_mask(mask: int) -> int:
    bits = [i for i in range(13) if mask >> i & 1]
    best = 0
    for c in combinations(bits, 5):
        m = 0
        for r in c:
            m |= 1 << r
        s = FLUSH5[m]
        if s > best:
            best = s
    return best


def _ensure_flush_masks() -> None:
    if len(_FLUSH_N) > len(FLUSH5):
        return
    for k in (6, 7, 8):
        for bits in combinations(range(13), k):
            m = 0
            for r in bits:
                m |= 1 << r
            _FLUSH_N[m] = _best_flush_for_mask(m)


_ensure_flush_masks()


def _build_unsuited(n: int) -> dict[int, int]:
    """Prime-product -> best 5-of-n non-flush strength, for every valid n-rank multiset."""
    table: dict[int, int] = {}
    for combo in combinations_with_replacement(range(13), n):
        # at most 4 of a rank
        ok = True
        last, run = -1, 0
        for r in combo:
            if r == last:
                run += 1
                if run > 4:
                    ok = False
                    break
            else:
                last, run = r, 1
        if not ok:
            continue
        p = 1
        for r in combo:
            p *= PRIMES[r]
        best = 0
        for five in set(combinations(combo, 5)):
            q = 1
            for r in five:
                q *= PRIMES[r]
            s = UNSUITED5.get(q)
            if s is not None and s > best:
                best = s
        table[p] = best
    return table


def unsuited_table(n: int) -> dict[int, int]:
    t = _UNSUITED_N.get(n)
    if t is None:
        t = _build_unsuited(n)
        _UNSUITED_N[n] = t
    return t


def warm(max_cards: int = 7) -> None:
    """Build lookup tables for all hand sizes up to max_cards. Call at import in the bot."""
    for n in range(5, max_cards + 1):
        unsuited_table(n)


def evaluate(cards: Sequence[int]) -> int:
    """Best 5-card strength of 5..8 canonical cards. Higher is better."""
    n = len(cards)
    # flush check: count suits
    s0 = s1 = s2 = s3 = 0
    for c in cards:
        s = c & 3
        if s == 0:
            s0 += 1
        elif s == 1:
            s1 += 1
        elif s == 2:
            s2 += 1
        else:
            s3 += 1
    if s0 >= 5 or s1 >= 5 or s2 >= 5 or s3 >= 5:
        suit = 0 if s0 >= 5 else 1 if s1 >= 5 else 2 if s2 >= 5 else 3
        m = 0
        for c in cards:
            if c & 3 == suit:
                m |= 1 << (c >> 2)
        f = _FLUSH_N[m]
        if n < 8:
            return f  # with <=7 cards, 5 suited rules out quads and full houses
        p = 1
        for c in cards:
            p *= PRIMES[c >> 2]
        u = unsuited_table(n)[p]
        return f if f > u else u
    p = 1
    for c in cards:
        p *= PRIMES[c >> 2]
    table = _UNSUITED_N.get(n)
    if table is None:
        table = unsuited_table(n)
    return table[p]


def evaluate_displayed(cards: Sequence[int], rules: Rules) -> int:
    """Evaluate cards shown under a rank-permuting variant."""
    if is_identity_order(rules):
        return evaluate(cards)
    return evaluate(remap(cards, rules))


def category(strength: int) -> int:
    """0 high card .. 8 straight flush."""
    return CATEGORY_OF[strength]


def category_name(strength: int) -> str:
    return CATEGORY_NAMES[CATEGORY_OF[strength]]


def evaluate_slow(cards: Sequence[int]) -> int:
    """Reference: brute force over all 5-card subsets. For tests only."""
    best = 0
    for five in combinations(cards, 5):
        suits = {c & 3 for c in five}
        ranks = [c >> 2 for c in five]
        if len(suits) == 1:
            m = 0
            for r in ranks:
                m |= 1 << r
            s = FLUSH5[m]
        else:
            p = 1
            for r in ranks:
                p *= PRIMES[r]
            s = UNSUITED5[p]
        if s > best:
            best = s
    return best
