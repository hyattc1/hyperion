"""Malmuth-Harville ICM: expected tournament points per seat from chip stacks.

The model: the probability a player finishes first is their share of the chips in play; the
probability they finish k-th is summed over every ordering of the k-1 players above them, each
ordering weighted by chip shares among the players not yet placed. Exact by recursion over the
set of unplaced players (2^n states), memoised, so eight players cost a few thousand operations.

Only the top `n_alive` payouts are in play: a busted seat (stack 0) receives 0 here, because its
points were fixed when it busted. The sum of the equities equals the sum of those payouts.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence


def icm_equity(stacks: Sequence[int], payouts: Sequence[float]) -> list[float]:
    """Expected points per seat. Stacks of 0 get 0. Exact for any n; intended for n <= 8."""
    n = len(stacks)
    alive = [i for i in range(n) if stacks[i] > 0]
    k = len(alive)
    if k == 0:
        return [0.0] * n
    pays = [float(p) for p in payouts[:k]] + [0.0] * max(0, k - len(payouts))
    chips = [float(stacks[i]) for i in alive]
    memo: dict[int, list[float]] = {}
    zeros = [0.0] * k

    def ev(mask: int) -> list[float]:
        """Expected points for each unplaced player, given `mask` is the set still unplaced."""
        out = memo.get(mask)
        if out is not None:
            return out
        place = k - bin(mask).count("1")
        if place >= len(pays) or pays[place] == 0.0 and all(p == 0.0 for p in pays[place:]):
            memo[mask] = zeros
            return zeros
        pay = pays[place]
        members = [i for i in range(k) if mask >> i & 1]
        total = 0.0
        for i in members:
            total += chips[i]
        out = [0.0] * k
        if len(members) == 1:
            out[members[0]] = pay
        else:
            for i in members:
                p = chips[i] / total
                out[i] += p * pay
                sub = ev(mask & ~(1 << i))
                for j in members:
                    if j != i:
                        out[j] += p * sub[j]
        memo[mask] = out
        return out

    res = ev((1 << k) - 1)
    eq = [0.0] * n
    for idx, seat in enumerate(alive):
        eq[seat] = res[idx]
    return eq


@lru_cache(maxsize=1 << 16)
def _cached(key: tuple[int, ...], payouts: tuple[float, ...]) -> tuple[float, ...]:
    return tuple(icm_equity(key, payouts))


def icm_cached(stacks: Sequence[int], payouts: Sequence[float], big_blind: int = 1) -> tuple[float, ...]:
    """icm_equity on stacks rounded to the nearest big blind, memoised across calls.

    A live stack never rounds to 0 (it rounds to one blind), so nobody is mistaken for busted.
    Returns a tuple, which is what the cache stores; copy it if you need to mutate.
    """
    bb = big_blind if big_blind > 0 else 1
    key = tuple(0 if s <= 0 else max(1, int(s / bb + 0.5)) for s in stacks)
    return _cached(key, tuple(float(p) for p in payouts))
