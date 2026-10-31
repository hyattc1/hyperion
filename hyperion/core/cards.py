"""Deck handling. Cards are ints 0..51 = rank*4 + suit (canonical ordering)."""
from __future__ import annotations

import random
from itertools import combinations
from typing import Iterable, Iterator, Sequence

from .types import RANKS, SUITS, Rules

FULL_DECK: tuple[int, ...] = tuple(range(52))


def rank_of(c: int) -> int:
    return c >> 2


def suit_of(c: int) -> int:
    return c & 3


def make_card(rank: int, suit: int) -> int:
    return rank * 4 + suit


def deck_for(rules: Rules) -> tuple[int, ...]:
    """The deck under these rules, in canonical ints (suits may be fewer than 4)."""
    return tuple(make_card(r, s) for r in range(13) for s in range(rules.n_suits))


def remap(cards: Iterable[int], rules: Rules) -> tuple[int, ...]:
    """Map displayed cards to canonical-strength cards under rules.rank_order."""
    ro = rules.rank_order
    return tuple(ro[c >> 2] * 4 + (c & 3) for c in cards)


def is_identity_order(rules: Rules) -> bool:
    return tuple(rules.rank_order) == tuple(range(13))


class Deck:
    """A shuffled deck with deterministic seeding. Deals are O(1) pops from the tail."""

    __slots__ = ("cards", "rng")

    def __init__(self, rules: Rules = Rules(), seed: int | None = None, rng: random.Random | None = None):
        self.rng = rng if rng is not None else random.Random(seed)
        self.cards = list(deck_for(rules))
        self.rng.shuffle(self.cards)

    def deal(self, n: int) -> tuple[int, ...]:
        out = tuple(self.cards[-n:]) if n else ()
        del self.cards[len(self.cards) - n :]
        return out

    def remove(self, cards: Iterable[int]) -> None:
        dead = set(cards)
        self.cards = [c for c in self.cards if c not in dead]

    def __len__(self) -> int:
        return len(self.cards)


def hole_class(hole: Sequence[int]) -> str:
    """169-class label for a 2-card hand: 'AKs', 'AKo', 'TT'. Higher rank first."""
    a, b = sorted(hole, reverse=True)
    ra, rb = RANKS[a >> 2], RANKS[b >> 2]
    if ra == rb:
        return ra + rb
    return ra + rb + ("s" if (a & 3) == (b & 3) else "o")


def all_hole_classes() -> list[str]:
    out = []
    for i in range(12, -1, -1):
        for j in range(i, -1, -1):
            if i == j:
                out.append(RANKS[i] * 2)
            else:
                out.append(RANKS[i] + RANKS[j] + "s")
                out.append(RANKS[i] + RANKS[j] + "o")
    return out


def class_combos(cls: str) -> list[tuple[int, int]]:
    """All specific 2-card combos belonging to a 169-class label."""
    r1, r2 = RANKS.index(cls[0]), RANKS.index(cls[1])
    if r1 == r2:
        return [(make_card(r1, s1), make_card(r1, s2)) for s1, s2 in combinations(range(4), 2)]
    if cls[2] == "s":
        return [(make_card(r1, s), make_card(r2, s)) for s in range(4)]
    return [(make_card(r1, s1), make_card(r2, s2)) for s1 in range(4) for s2 in range(4) if s1 != s2]


def iter_combos(cards: Sequence[int], k: int) -> Iterator[tuple[int, ...]]:
    return combinations(cards, k)


def card_from_str(s: str) -> int:
    return RANKS.index(s[0].upper()) * 4 + SUITS.index(s[1].lower())
