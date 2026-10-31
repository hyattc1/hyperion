"""Offline equity generation. Never called on the decision path: results go into tables/.

Two products:
  - preflop_equity(cls, n_opp): win+tie/2 share of a 169-class hand vs n_opp random hands, all-in to showdown.
  - hand_strength(hole, board): fraction of random opponent holdings we beat (ties half) on this board,
    which is the classic HS; squared/averaged over runouts gives E[HS^2] for draws.
Both are parameterized by Rules (hole-card count, rank order) so a variant regenerates everything.
"""
from __future__ import annotations

import random
from itertools import combinations
from typing import Sequence

from .cards import class_combos, deck_for, remap, is_identity_order
from .eval import evaluate
from .types import Rules


def _canon(cards: Sequence[int], rules: Rules) -> tuple[int, ...]:
    return tuple(cards) if is_identity_order(rules) else remap(cards, rules)


def showdown_share(hero: Sequence[int], villains: Sequence[Sequence[int]], board: Sequence[int]) -> float:
    """Hero's share of one pot at showdown: 1 win, 0 loss, 1/k for a k-way tie."""
    h = evaluate(tuple(hero) + tuple(board))
    best_v = 0
    for v in villains:
        s = evaluate(tuple(v) + tuple(board))
        if s > best_v:
            best_v = s
    if h > best_v:
        return 1.0
    if h < best_v:
        return 0.0
    ties = 1 + sum(1 for v in villains if evaluate(tuple(v) + tuple(board)) == h)
    return 1.0 / ties


def monte_carlo_equity(
    hole: Sequence[int],
    board: Sequence[int],
    n_opp: int,
    samples: int,
    rules: Rules = Rules(),
    seed: int | None = None,
) -> float:
    """Equity of hole on board vs n_opp random hands, run out to a full board. Displayed cards in."""
    rng = random.Random(seed)
    hole_c = _canon(hole, rules)
    board_c = _canon(board, rules)
    dead = set(hole_c) | set(board_c)
    stub = [c for c in deck_for(rules) if c not in dead]
    need_board = rules.board_sizes[-1] - len(board_c)
    k = rules.hole_cards
    total = 0.0
    for _ in range(samples):
        rng.shuffle(stub)
        i = 0
        villains = []
        for _ in range(n_opp):
            villains.append(stub[i : i + k])
            i += k
        full_board = board_c + tuple(stub[i : i + need_board])
        total += showdown_share(hole_c, villains, full_board)
    return total / samples


def preflop_equity(cls: str, n_opp: int, samples: int, rules: Rules = Rules(), seed: int | None = None) -> float:
    """Average equity of a 169-class vs n_opp random hands (standard 2-card rules only)."""
    rng = random.Random(seed)
    combos = class_combos(cls)
    per = max(1, samples // len(combos))
    total = 0.0
    for combo in combos:
        total += monte_carlo_equity(combo, (), n_opp, per, rules, seed=rng.randrange(1 << 30))
    return total / len(combos)


def hand_strength(hole: Sequence[int], board: Sequence[int], rules: Rules = Rules()) -> float:
    """Exact HS vs one random opponent holding on this board (no runout). Board must be 3..5 cards."""
    hole_c = _canon(hole, rules)
    board_c = _canon(board, rules)
    dead = set(hole_c) | set(board_c)
    stub = [c for c in deck_for(rules) if c not in dead]
    mine = evaluate(hole_c + board_c)
    ahead = tied = total = 0
    for v in combinations(stub, rules.hole_cards):
        s = evaluate(tuple(v) + board_c)
        if mine > s:
            ahead += 1
        elif mine == s:
            tied += 1
        total += 1
    return (ahead + 0.5 * tied) / total


def hand_strength_mc(
    hole: Sequence[int], board: Sequence[int], samples: int, rules: Rules = Rules(), seed: int | None = None
) -> float:
    """Sampled HS, for when exact enumeration is too slow (e.g. 3+ hole cards)."""
    rng = random.Random(seed)
    hole_c = _canon(hole, rules)
    board_c = _canon(board, rules)
    dead = set(hole_c) | set(board_c)
    stub = [c for c in deck_for(rules) if c not in dead]
    mine = evaluate(hole_c + board_c)
    k = rules.hole_cards
    acc = 0.0
    for _ in range(samples):
        v = rng.sample(stub, k)
        s = evaluate(tuple(v) + board_c)
        acc += 1.0 if mine > s else 0.5 if mine == s else 0.0
    return acc / samples
