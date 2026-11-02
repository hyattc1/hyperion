"""Pure-Python hand evaluator built for a 1 ms budget.

Strength is an int: higher is better, 1..7462 for 5-card classes. Any n>=5 cards evaluates the best
5-card hand. For n in 5..8, non-flush hands resolve in ONE dict lookup keyed by the product of rank
primes, and flush hands in one lookup keyed by the rank bitmask of the suited cards. Typical 7-card
evaluate: a few microseconds.

Tables: 5 cards and the flush masks at import, 6 and 7 at strategy import (`warm(7)`), and a bot's table start
builds what its Rules need (`warm(max_cards(rules))`: 8 only for three kept hole cards or a bought card). Each
n-card table is grown from the (n-1)-card one (the best five of n cards is the best of the n (n-1)-card subsets'),
so 6, 7 and 8 cost about 3, 20 and 60 ms instead of 0.02, 0.12 and 0.61 s, with the same entries. An evaluate on
6 to 8 cards whose table is not built yet never builds it inside the call (that would be a 1 ms decision spent on
a 60 ms build): it takes the best of its (n-1)-card subsets, exact, and the next `warm()` builds the table. Past
8 cards `evaluate` still builds the table on first use (seconds: river_of_blood's guard in hyperion/drills/variants.py
plays that as a timeout in the sim); `evaluate_many` takes any number of cards without a table (rank counts and suit
masks, about 10 us at 12 cards), which is what a bot reading a board longer than five should call.

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
    """Every 6-, 7- and 8-bit suited mask: the best of the masks one bit smaller (the same as
    _best_flush_for_mask on each, in 3 ms rather than 20)."""
    if len(_FLUSH_N) > len(FLUSH5):
        return
    layer = FLUSH5
    for _ in (6, 7, 8):
        nxt: dict[int, int] = {}
        get = nxt.get
        for m, v in layer.items():
            for r in range(13):
                b = 1 << r
                if not m & b and get(m | b, 0) < v:
                    nxt[m | b] = v
        _FLUSH_N.update(nxt)
        layer = nxt


_ensure_flush_masks()


_P4 = tuple(p ** 4 for p in PRIMES)


def _grow(prev: dict[int, int]) -> dict[int, int]:
    """The (n+1)-rank table from the n-rank one: each multiset's best is the best over the multisets one rank
    smaller, so every entry of `prev` raises each one-rank extension (at most four of a rank) to its value."""
    out: dict[int, int] = {}
    get = out.get
    for p, v in prev.items():
        for r in range(13):
            if p % _P4[r]:
                q = p * PRIMES[r]
                if get(q, 0) < v:
                    out[q] = v
    return out


def _build_unsuited(n: int) -> dict[int, int]:
    """Prime-product -> best 5-of-n non-flush strength, for every valid n-rank multiset (grown from n - 1)."""
    if n <= 5:
        return UNSUITED5
    return _grow(unsuited_table(n - 1))


def _build_unsuited_slow(n: int) -> dict[int, int]:
    """The same table by brute force over each multiset's five-rank subsets (the reference, for tests)."""
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


WANTED: set[int] = set()  # 6..8-card evaluations met before their table was built: the next warm() builds them


def warm(max_cards: int = 7) -> None:
    """Build lookup tables for all hand sizes up to max_cards, and any 6..8 an evaluate has met since. Call it at
    import or at table start, never inside a timed call."""
    top = max(max_cards, max(WANTED, default=0))
    for n in range(5, top + 1):
        unsuited_table(n)
    WANTED.clear()


def max_cards(rules: Rules) -> int:
    """The most cards one of our evaluations holds under `rules` (5 to 8): the hole cards held at each street (all
    of them before a discard street, extras["keep"] from it on, one more from a bought card's street) plus that
    street's board; 5 when the hand must use k hole cards (every evaluation is k + (5 - k) cards); 8 when the board
    can run past its last size (extras["run_until_black"]). A table start warms this many; a count it misses is
    still evaluated exactly, through the (n-1)-card subsets, and built at the next warm()."""
    if rules.must_use_hole:
        return 5
    ex = rules.extras or {}
    sizes = tuple(rules.board_sizes) or (0,)
    hole = int(rules.hole_cards)
    top = 0
    ds = ex.get("discard_street")
    keep = ex.get("keep")
    bought = ex.get("variant") == "bonus_card" or "price_bb" in ex
    buy_street = int(ex.get("street", 1) or 1) if bought else len(sizes)
    for st, board in enumerate(sizes):
        h = hole
        if ds is not None and keep is not None and st >= int(ds):
            h = int(keep)
        if st >= buy_street:
            h += 1
        top = max(top, h + int(board))
    if ex.get("run_until_black"):
        top = 8
    return max(5, min(8, top))


def _from_subsets(cards: Sequence[int], n: int) -> int:
    """Best five of 6..8 cards with no n-card table yet: the best of the (n-1)-card subsets, each exact."""
    WANTED.add(n)
    best = 0
    for i in range(n):
        s = evaluate(cards[:i] + cards[i + 1:])
        if s > best:
            best = s
    return best


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
        table = _UNSUITED_N.get(n)
        if table is None:
            if n <= 8:
                return _from_subsets(tuple(cards), n)
            table = unsuited_table(n)
        p = 1
        for c in cards:
            p *= PRIMES[c >> 2]
        u = table[p]
        return f if f > u else u
    p = 1
    for c in cards:
        p *= PRIMES[c >> 2]
    table = _UNSUITED_N.get(n)
    if table is None:
        if n <= 8:
            return _from_subsets(tuple(cards), n)
        table = unsuited_table(n)
    return table[p]


# ------------------------------------------------------------------ any number of cards, no table

# the ten straights as rank bitmasks, ace-high first, the wheel (A-2-3-4-5) last
_STRAIGHTS_DESC = tuple(0b1111100000000 >> i for i in range(9)) + (0b1000000001111,)


def _mask_ranks(mask: int) -> list[int]:
    return [r for r in range(13) if mask >> r & 1]


def _best_unsuited_ranks(counts: Sequence[int]) -> list[int]:
    """The five ranks of the best non-flush hand in a rank multiset (any size >= 5)."""
    desc = [r for r in range(12, -1, -1) if counts[r]]
    for r in desc:
        if counts[r] >= 4:
            return [r] * 4 + [next(k for k in desc if k != r)]
    trips = [r for r in desc if counts[r] >= 3]
    if trips:
        t = trips[0]
        pair = next((r for r in desc if r != t and counts[r] >= 2), None)
        if pair is not None:
            return [t] * 3 + [pair] * 2
    mask = 0
    for r in desc:
        mask |= 1 << r
    for sm in _STRAIGHTS_DESC:
        if mask & sm == sm:
            return _mask_ranks(sm)
    if trips:
        t = trips[0]
        return [t] * 3 + [r for r in desc if r != t][:2]
    pairs = [r for r in desc if counts[r] >= 2]
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        return [p1, p1, p2, p2, next(r for r in desc if r != p1 and r != p2)]
    if pairs:
        p = pairs[0]
        return [p, p] + [r for r in desc if r != p][:3]
    return desc[:5]


def evaluate_many(cards: Sequence[int]) -> int:
    """Best five-card strength of any number (>= 5) of canonical cards, on the same scale as `evaluate`.

    Up to 8 cards it is `evaluate` itself. Past 8 that evaluator builds a lookup table per hand size (3 s at 9 cards,
    about x3 per extra card, gigabytes by 14), so a board that runs on (river_of_blood: up to 30 board cards) takes
    this direct path instead: the best flush or straight flush per suit from its rank mask, the best non-flush hand
    from the rank counts, each looked up in the five-card tables. Never builds a table; tests compare it with
    evaluate_slow. (Written for the held-out river_of_blood, hyperion/drills/variants_unseen.py; moved here when the
    entry joined the catalog, 2026-11-02.)"""
    n = len(cards)
    if n <= 8:
        return evaluate(cards)
    counts = [0] * 13
    suit_mask = [0, 0, 0, 0]
    suit_n = [0, 0, 0, 0]
    for c in cards:
        r, s = c >> 2, c & 3
        counts[r] += 1
        suit_mask[s] |= 1 << r
        suit_n[s] += 1
    best = 0
    for s in range(4):
        if suit_n[s] >= 5:
            m = suit_mask[s]
            f = 0
            for sm in _STRAIGHTS_DESC:
                if m & sm == sm:
                    f = FLUSH5[sm]
                    break
            if not f:
                top, k = 0, 0
                for r in range(12, -1, -1):
                    if m >> r & 1:
                        top |= 1 << r
                        k += 1
                        if k == 5:
                            break
                f = FLUSH5[top]
            if f > best:
                best = f
    p = 1
    for r in _best_unsuited_ranks(counts):
        p *= PRIMES[r]
    u = UNSUITED5[p]
    return best if best > u else u


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
