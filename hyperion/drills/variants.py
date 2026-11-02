"""Variant catalog: past MIT twists and plausible new ones, as Rules + hooks + what breaks + a Config patch.

Two views of the same objects:
  - the seven drill presets (`names()`, `get()`, `PRESETS`) that `hyperion.drills.run` picks from;
  - the full catalog (`catalog()`, `catalog_names()`), about twenty entries across four axes
    (ranking, information, payoff, betting) so event night picks from a list instead of improvising,
    and `python -m hyperion.sim --variant NAME` can measure Hero on each.

CLI:  python -m hyperion.drills.variants --list
      python -m hyperion.drills.variants --rules NAME [--out rules_NAME.json]   (Rules JSON for gen_tables / sim)
      python -m hyperion.drills.variants --show NAME

Each entry answers: what Rules/extras describe it, whether the engine can play it (`playable`), what breaks
in our tables and strategy, and a Config patch sketch. Where the twist needs the engine's cooperation it is
a `VariantHooks` object the sim calls at fixed points. The contract (defaults are identity so an unwired hook
is harmless; `hyperion.sim.engine.HooksVariant` is the implementation on the engine side):

  on_deal(holes, deck, rng) -> holes
      after hole cards are dealt, before preflop betting. holes: list[tuple[int,...]] per seat
      (empty tuple for seats not in the hand); deck: list[int] of undealt cards the hook may pop
      from; rng: random.Random owned by the table.
  on_street(street, board, holes, deck, rng, ask=None) -> (board, holes)
      when the engine advances to `street` (1 = flop, ...), after that street's board cards are
      dealt and before betting. May change board and holes (swap, discard, second board).
      ask(seat, prompt: dict) -> object is an optional callback the engine supplies to let a bot
      make a variant decision (the bot's `variant_decide(prompt)`); hooks must work when ask is
      None or returns None (use the default decision).
  score_hand(hole, board, rules) -> int
      replaces evaluate_displayed at showdown. Higher wins. Default: evaluate_displayed(hole+board).
  on_payout(deltas, holes, board, hand_no, rules, rng) -> deltas
      optional; adjusts the chip deltas of a finished hand (bounties). Must keep sum(deltas) == 0
      unless rules.extras["bounty_funding"] == "house" (then the house adds chips).
  Optional extensions the engine honours when present:
  score_splits(hole, board, rules) -> list[int | None]
      one score per pot share (two boards, hi/lo). Each pot is split evenly over the columns; a
      column where nobody qualifies (all None) goes to column 0's winners.
  on_bust(busted_seats, deltas, hand_no, rules) -> {seat: bonus points}
      points (not chips) the house adds when players bust (knockout bounties).
  extras(hand) -> dict
      what goes into Observation.extras for the street (discards, boards, exposed cards, bounties).
  charges: dict[seat, chips]
      set by a hook during on_deal/on_street; the engine moves those chips from the stack into the
      pot right after (buying a card) and clears the dict.

Cards everywhere are *displayed* ints (what the bot sees); rank_order maps them to strength.
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import sys
from dataclasses import dataclass, field
from functools import lru_cache
from itertools import combinations
from typing import Callable, Sequence

from hyperion.core.cards import remap
from hyperion.core.eval import MAX_STRENGTH, category, evaluate, evaluate_displayed
from hyperion.core.types import Observation, Rules

Holes = list  # list[tuple[int, ...]] per seat

AXES = ("ranking", "information", "payoff", "betting")


class VariantHooks:
    """Identity hooks. Subclass and override what the twist needs."""

    def on_deal(self, holes: Holes, deck: list[int], rng: random.Random) -> Holes:
        return holes

    def on_street(self, street: int, board: tuple[int, ...], holes: Holes, deck: list[int],
                  rng: random.Random, ask: Callable | None = None) -> tuple[tuple[int, ...], Holes]:
        return board, holes

    def score_hand(self, hole: Sequence[int], board: Sequence[int], rules: Rules) -> int:
        if rules.must_use_hole:
            from hyperion.sim.engine import evaluate_must_use  # the engine owns the 2+3 rule

            return evaluate_must_use(hole, board, rules, rules.must_use_hole)
        return evaluate_displayed(tuple(hole) + tuple(board), rules)

    def on_payout(self, deltas: list[int], holes: Holes, board: tuple[int, ...], hand_no: int,
                  rules: Rules, rng: random.Random) -> list[int]:
        return deltas


@dataclass
class Variant:
    name: str
    summary: str
    rules: Rules
    breaks: str  # one paragraph: what breaks in our tables and strategy
    checklist: tuple[str, ...]  # regeneration / adaptation steps, in order
    hooks: VariantHooks | None = None  # None = pure Rules, no engine support needed
    needs_engine: bool = False
    tables_to_rerun: tuple[str, ...] = ()
    # catalog fields (2026-10-31)
    axis: str = "ranking"
    playable: bool = True  # the engine plays it end to end as written
    playable_note: str = ""  # caveats, or why not
    tables: str = "default"  # default | regenerate | approximate | unsupported (see gen_catalog)
    tables_note: str = ""
    config_patch: dict = field(default_factory=dict)  # sketch of hero Config overrides
    hooks_factory: Callable[[], VariantHooks] | None = None  # fresh hooks per table

    def __post_init__(self) -> None:
        if self.hooks is None and self.hooks_factory is not None:
            self.hooks = self.hooks_factory()

    def rules_json(self) -> dict:
        from hyperion.tablegen import rules_to_dict

        return rules_to_dict(self.rules)

    def new_hooks(self) -> VariantHooks | None:
        """A fresh hooks object (hooks keep per-hand state, so one per table)."""
        if self.hooks_factory is not None:
            return self.hooks_factory()
        return copy.deepcopy(self.hooks) if self.hooks is not None else None

    def card_rules_differ(self) -> bool:
        """True when the deck, the hole/board counts, or the showdown differ from default hold'em."""
        d, r = Rules(), self.rules
        if (r.hole_cards, r.board_sizes, r.rank_order, r.n_suits, r.must_use_hole) != (
                d.hole_cards, d.board_sizes, d.rank_order, d.n_suits, d.must_use_hole):
            return True
        return any(k in r.extras for k in ("removed_ranks", "keep", "wild_rank", "category_order", "lowball", "hi_lo"))


# ------------------------------------------------------------------------------- hooks

class TossHooks(VariantHooks):
    """3 hole cards; after the flop each player discards one hole card face up (OOP first).

    8-max adaptation: the discard is public information (self.discards, which the engine puts in
    obs.extras['discards']) but not a community card, so showdown is 2 hole + 5 board. MIT's
    heads-up original added discards to the board; see docs/decisions.md. `see_flop=False` asks
    for the discard before the flop is shown (the prompt carries an empty board).
    """

    def __init__(self, see_flop: bool = True) -> None:
        self.see_flop = see_flop
        self.discards: dict[int, int] = {}

    def on_deal(self, holes, deck, rng):
        self.discards = {}
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        if street != 1:
            return board, holes
        new_holes = list(holes)
        shown = board if self.see_flop else ()
        for seat in range(len(holes)):  # the engine passes holes ordered so OOP seats come first
            h = holes[seat]
            if len(h) != 3:
                continue
            idx = None
            if ask is not None:
                try:
                    ans = ask(seat, {"decision": "discard", "hole": h, "board": shown})
                    idx = None if ans is None else int(ans)
                except Exception:  # noqa: BLE001
                    idx = None
            if idx is None or not 0 <= idx < 3:
                idx = default_discard(h)
            self.discards[seat] = h[idx]
            new_holes[seat] = h[:idx] + h[idx + 1:]
        return board, new_holes

    def extras(self, hand) -> dict:
        return {"discards": dict(self.discards)}


def default_discard(hole: Sequence[int]) -> int:
    """Index of the card to toss: keep the pair if any, else the suited pair, else the two highest."""
    def keep_score(i: int, j: int) -> float:
        a, b = hole[i], hole[j]
        return (100 if a >> 2 == b >> 2 else 0) + (3 if a & 3 == b & 3 else 0) + (a >> 2) + (b >> 2)

    best = max(((i, j) for i in range(len(hole)) for j in range(i + 1, len(hole))), key=lambda ij: keep_score(*ij))
    return next(k for k in range(len(hole)) if k not in best)


class SwapHooks(VariantHooks):
    """MIT 2022: each hole card is independently replaced from the deck with p_flop on the flop, p_turn on the turn."""

    def __init__(self, p_flop: float = 0.1, p_turn: float = 0.05):
        self.p = {1: p_flop, 2: p_turn}

    def on_street(self, street, board, holes, deck, rng, ask=None):
        p = self.p.get(street, 0.0)
        if p <= 0:
            return board, holes
        new_holes = list(holes)
        for seat, h in enumerate(holes):
            if not h:
                continue
            cards = list(h)
            for i in range(len(cards)):
                if rng.random() < p and deck:
                    cards[i] = deck.pop()
            new_holes[seat] = tuple(cards)
        return board, new_holes


class SwapOneHooks(VariantHooks):
    """At the turn every player still in may replace one hole card with the next deck card (their choice).

    The bot answers {"decision": "swap", "hole", "board"} with the index to replace or -1 to keep.
    Default: swap the lower card when neither hole card pairs the board and the lower card is below a
    ten (displayed rank, which is what a naive bot would do).
    """

    def __init__(self, street: int = 2) -> None:
        self.street = street
        self.swapped: dict[int, bool] = {}

    def on_deal(self, holes, deck, rng):
        self.swapped = {}
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        if street != self.street:
            return board, holes
        new_holes = list(holes)
        for seat, h in enumerate(holes):
            if len(h) < 2 or not deck:
                continue
            idx = None
            if ask is not None:
                try:
                    ans = ask(seat, {"decision": "swap", "hole": h, "board": board})
                    idx = None if ans is None else int(ans)
                except Exception:  # noqa: BLE001
                    idx = None
            if idx is None:
                idx = default_swap(h, board)
            if 0 <= idx < len(h):
                cards = list(h)
                cards[idx] = deck.pop()
                new_holes[seat] = tuple(cards)
                self.swapped[seat] = True
            else:
                self.swapped[seat] = False
        return board, new_holes

    def extras(self, hand) -> dict:
        return {"swapped": dict(self.swapped)}


def default_swap(hole: Sequence[int], board: Sequence[int]) -> int:
    board_ranks = {c >> 2 for c in board}
    if any((c >> 2) in board_ranks for c in hole) or hole[0] >> 2 == hole[1] >> 2:
        return -1
    lo = min(range(len(hole)), key=lambda i: hole[i] >> 2)
    return lo if (hole[lo] >> 2) < 8 else -1


class BountyHooks(VariantHooks):
    """MIT 2025: a bounty rank per player, re-drawn every N hands; hitting it scales winnings.

    Funding: rules.extras['bounty_funding'] 'house' (default: the extra chips appear) or 'losers'
    (the extra is taken pro rata from the hand's losers, so chips are conserved). Bounties are
    public in obs.extras['bounties'] here; MIT kept them private.
    """

    def __init__(self, ratio: float = 1.5, constant: int = 10, rounds_per_bounty: int = 25):
        self.ratio, self.constant, self.rounds = ratio, constant, rounds_per_bounty
        self.bounties: dict[int, int] = {}

    def on_payout(self, deltas, holes, board, hand_no, rules, rng):
        if hand_no % self.rounds == 0 or not self.bounties:
            self.bounties = {s: rng.randrange(13) for s in range(len(deltas))}
        out = list(deltas)
        board_ranks = {c >> 2 for c in board}
        extra_total = 0
        for s, d in enumerate(deltas):
            if d <= 0 or not holes[s]:
                continue
            hit = self.bounties[s] in board_ranks or any((c >> 2) == self.bounties[s] for c in holes[s])
            if hit:
                out[s] = int(d * self.ratio) + self.constant
                extra_total += out[s] - d
        if extra_total and rules.extras.get("bounty_funding", "house") == "losers":
            losers = [s for s, d in enumerate(deltas) if d < 0]
            lost = -sum(deltas[s] for s in losers)
            taken = 0
            for s in losers:
                # the loser cannot pay more than what they still have: the engine clamps stacks at 0
                share = int(extra_total * (-deltas[s]) / lost) if lost else 0
                out[s] -= share
                taken += share
            if taken < extra_total and losers:
                out[losers[0]] -= extra_total - taken
        return out

    def extras(self, hand) -> dict:
        return {"bounties": dict(self.bounties)}


class ShortDeckHooks(VariantHooks):
    """Short deck (6+): ranks 2-5 removed; flush beats full house; A-6-7-8-9 is a straight."""

    ORDER = (0, 1, 2, 3, 4, 6, 5, 7, 8)  # new category rank by standard category index: flush above full house
    LOW_STRAIGHT = frozenset({12, 4, 5, 6, 7})  # canonical A,6,7,8,9

    def score_hand(self, hole, board, rules):
        cards = remap(tuple(hole) + tuple(board), rules)
        s = evaluate(cards)
        cat = category(s)
        # A6789 straight / straight flush that the standard evaluator misses
        if cat < 4 or cat == 5:
            ranks_by_suit: dict[int, set] = {}
            all_ranks = set()
            for c in cards:
                all_ranks.add(c >> 2)
                ranks_by_suit.setdefault(c & 3, set()).add(c >> 2)
            if any(self.LOW_STRAIGHT <= rs for rs in ranks_by_suit.values()):
                return self.ORDER[8] * 10000 + 1  # lowest straight flush
            if cat < 4 and self.LOW_STRAIGHT <= all_ranks:
                return self.ORDER[4] * 10000 + 1  # lowest straight
        return self.ORDER[cat] * 10000 + s


class FlushOverFullHooks(VariantHooks):
    """Category reorder only: a flush beats a full house, everything else as in hold'em."""

    ORDER = (0, 1, 2, 3, 4, 6, 5, 7, 8)

    def score_hand(self, hole, board, rules):
        s = evaluate_displayed(tuple(hole) + tuple(board), rules)
        return self.ORDER[category(s)] * 10000 + s


class LowballHooks(VariantHooks):
    """Reversed rankings: the worst hold'em hand wins (2-7 style: aces high, straights and flushes
    count against you, so 7-5-4-3-2 unsuited is the nuts). Best five of seven for the *lowest* hand."""

    def score_hand(self, hole, board, rules):
        return MAX_STRENGTH + 1 - lowest_five(remap(tuple(hole) + tuple(board), rules))


def lowest_five(cards: Sequence[int]) -> int:
    """Strength of the weakest 5-card hand among the cards (the evaluator gives the strongest)."""
    worst = MAX_STRENGTH + 1
    for five in combinations(cards, 5):
        s = evaluate(five)
        if s < worst:
            worst = s
    return worst


class WildRankHooks(VariantHooks):
    """One displayed rank is wild (deuces by default): each wild stands for any card not already in
    the hand, chosen to make the best hold'em hand. No five of a kind."""

    def __init__(self, rank: int = 0) -> None:
        self.rank = rank

    def score_hand(self, hole, board, rules):
        cards = tuple(hole) + tuple(board)
        return _wild_best(tuple(sorted(cards)), self.rank, rules.rank_order)


@lru_cache(maxsize=65536)
def _wild_best(cards: tuple[int, ...], wild_rank: int, rank_order: tuple[int, ...]) -> int:
    rest = tuple(c for c in cards if (c >> 2) != wild_rank)
    k = len(cards) - len(rest)
    canon = tuple(rank_order[c >> 2] * 4 + (c & 3) for c in rest)
    if k == 0:
        return evaluate(canon)
    present = set(canon)
    pool = [c for c in range(52) if c not in present and (c >> 2) != rank_order[wild_rank]]
    best = 0
    for sub in combinations(pool, k):
        s = evaluate(canon + sub)
        if s > best:
            best = s
    return best


class TwoBoardsHooks(VariantHooks):
    """Two boards dealt in parallel; the pot is split in half, each half awarded by its own board.

    `board` (the engine's) stays board 1. The hook deals and keeps board 2 per hand; the engine
    exposes both via obs.extras['boards'] and settles with score_splits.
    """

    def __init__(self) -> None:
        self.board2: tuple[int, ...] = ()

    def on_deal(self, holes, deck, rng):
        self.board2 = ()
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        while len(self.board2) < len(board) and deck:
            self.board2 = self.board2 + (deck.pop(),)
        return board, holes

    def boards(self, board: tuple[int, ...]) -> list[tuple[int, ...]]:
        return [tuple(board), self.board2]

    def score_boards(self, hole, board, rules) -> list[int]:
        return [evaluate_displayed(tuple(hole) + b, rules) for b in self.boards(board)]

    score_splits = score_boards

    def score_hand(self, hole, board, rules):
        """Board 1 only, so an engine that has not wired score_splits still terminates."""
        return evaluate_displayed(tuple(hole) + tuple(board), rules)

    def extras(self, hand) -> dict:
        return {"boards": self.boards(hand.board)}


class HiLoHooks(VariantHooks):
    """Half the pot to the best high hand, half to the best qualifying low (8-or-better, A-5, ace low,
    straights and flushes ignored). No qualifying low: the high hand scoops."""

    LOW_MAX = 8  # eight-or-better

    def score_splits(self, hole, board, rules) -> list:
        cards = tuple(hole) + tuple(board)
        return [evaluate_displayed(cards, rules), low_score(cards, rules, self.LOW_MAX)]

    def score_hand(self, hole, board, rules):
        return evaluate_displayed(tuple(hole) + tuple(board), rules)


def low_score(cards: Sequence[int], rules: Rules, low_max: int = 8):
    """Higher is a better low; None when no five distinct ranks of `low_max` or less (ace = 1)."""
    vals = set()
    for c in cards:
        r = rules.rank_order[c >> 2]  # canonical: 0 = deuce .. 12 = ace
        v = 1 if r == 12 else r + 2
        if v <= low_max:
            vals.add(v)
    if len(vals) < 5:
        return None
    five = sorted(vals)[:5][::-1]  # highest card first: the most significant
    code = 0
    for v in five:
        code = code * 16 + v
    return -code


class ExposedCardHooks(VariantHooks):
    """Each player's first hole card is dealt face up: everybody sees it in obs.extras['exposed']."""

    def __init__(self) -> None:
        self.exposed: dict[int, int] = {}

    def on_deal(self, holes, deck, rng):
        self.exposed = {s: h[0] for s, h in enumerate(holes) if h}
        return holes

    def extras(self, hand) -> dict:
        return {"exposed": dict(self.exposed)}


class BonusCardHooks(VariantHooks):
    """A fixed-price third hole card on the flop (the auction from MIT 2023, with the auction replaced by
    a posted price so it fits an 8-max engine). The bot answers {"decision": "buy_card", "price"} with
    truthy to buy; the price goes into the pot (dead money). Default: buy."""

    def __init__(self, price_bb: float = 1.0) -> None:
        self.price_bb = price_bb
        self.charges: dict[int, int] = {}
        self.bought: dict[int, bool] = {}
        self.price = 0

    def on_deal(self, holes, deck, rng):
        self.bought = {}
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        if street != 1:
            return board, holes
        new_holes = list(holes)
        price = self.price
        for seat, h in enumerate(holes):
            if not h or not deck:
                continue
            buy = True
            if ask is not None:
                try:
                    ans = ask(seat, {"decision": "buy_card", "price": price, "hole": h, "board": board})
                    buy = True if ans is None else bool(ans)
                except Exception:  # noqa: BLE001
                    buy = True
            self.bought[seat] = buy
            if buy:
                new_holes[seat] = h + (deck.pop(),)
                self.charges[seat] = price
        return board, new_holes

    def extras(self, hand) -> dict:
        self.price = int(round(self.price_bb * hand.blinds[1]))
        return {"bonus_card_price": self.price, "bought": dict(self.bought)}


class KnockoutHooks(VariantHooks):
    """Knockout bounty paid by the house: the player who wins the most chips on a hand where someone
    busts gets `points` per bust, added to their finishing points (ties split the bonus)."""

    def __init__(self, points: float = 1.0) -> None:
        self.points = points

    def on_bust(self, busted: list[int], deltas: list[int], hand_no: int, rules: Rules) -> dict[int, float]:
        top = max(deltas)
        if top <= 0:
            return {}
        winners = [s for s, d in enumerate(deltas) if d == top]
        bonus = self.points * len(busted) / len(winners)
        return {s: bonus for s in winners}


def pot_limit_max_raise(obs: Observation) -> int:
    """Largest legal raise-to total under pot-limit: call, then raise by the pot after the call."""
    current = max(obs.bets)
    pot_after_call = obs.pot + sum(obs.bets) + obs.to_call
    return min(obs.max_raise, current + pot_after_call)


# ------------------------------------------------------------------------------- presets (drills)

def permuted_ranks(seed: int = 0) -> Variant:
    """MIT 2020: ranks are secretly permuted. We model the *known* permutation; inferring it is strategy."""
    perm = list(range(13))
    random.Random(seed).shuffle(perm)
    rules = Rules(rank_order=tuple(perm), extras={"variant": "permuted_ranks", "seed": seed})
    return Variant(
        name="permuted_ranks",
        summary=f"Tonight the ranks are shuffled: the order of 2..A is a secret permutation (seed {seed}); "
                "suits, straights and flushes work as before. Your evaluator is unchanged if you remap "
                "through Rules.rank_order.",
        rules=rules,
        breaks=(
            "Every table keyed by displayed rank is wrong: preflop_equity, preflop_rank, hu_matrix, and the "
            "high-card / connectedness parts of flop_strength. The evaluator is fine because it only sees "
            "canonical cards. If the permutation is secret (as in 2020) the strategy must infer it from "
            "showdowns, which 200 hands of 8-max will not do reliably; play the cheap bot's rank-agnostic "
            "lines (pairs, suitedness, position, stack depth) until the kit or rules state the order."
        ),
        checklist=(
            "Write the permutation into variant.json as rank_order (displayed index -> canonical strength).",
            "python tools/gen_tables.py --rules variant.json --out tables/  (all four tables; ~1 min)",
            "Set hero's preflop charts to read preflop_rank.json, not any hard-coded hand list.",
            "If the order is secret: disable rank-based bluffs, keep pair/suit/stack logic, log showdowns.",
        ),
        tables_to_rerun=("preflop_equity", "preflop_rank", "hu_matrix", "flop_strength"),
        axis="ranking", tables="regenerate",
        tables_note="all four tables under the permutation; labels stay displayed ranks",
        config_patch={"preflop.open_frac_default": 0.09, "postflop.semibluff_freq": 0.3},
    )


def toss_or_holdem() -> Variant:
    """MIT 2026: 3 hole cards, 2-card flop, face-up discard, then turn and river (6 board cards)."""
    rules = Rules(hole_cards=3, extras={"variant": "toss_or_holdem", "discard_street": 1,
                                        "discard_face_up": True, "keep": 2})
    return Variant(
        name="toss_or_holdem",
        summary="Three hole cards. After you see the flop you toss one face up; it is dead, not community. "
                "Showdown is your two kept cards plus the five-card board. (MIT 2026 heads-up put discards "
                "on the board; eight-handed we keep them off it.)",
        rules=rules,
        breaks=(
            "The 169-class notion breaks: gen_tables switches to the best2+tags scheme (hole_classes.json) "
            "and skips hu_matrix. extras['keep']=2 makes the generator score the best 2 of 3 at showdown, "
            "a perfect-hindsight discard, so equities are an upper bound: an ordering, not a price. The "
            "discard is a new decision Observation does not model (the engine asks variant_decide with "
            "{'decision': 'discard'}), and opponents' discards are dead cards (obs.extras['discards']) hero "
            "should remove from any HS estimate. Hero plays 3 hole cards as check/fold preflop and safe "
            "postflop until the preflop module reads hole_label; expect it to finish near the bottom. "
            "If the target format keeps the heads-up rule that discards join the board, board_sizes become "
            "(0, 2, 2+n, 3+n, 4+n) and the evaluator needs a best-5-of-many path; nothing here is ready for that."
        ),
        checklist=(
            "python tools/gen_tables.py --rules variant.json --out tables/  (writes hole_classes.json)",
            "Hero: look up preflop_rank by hyperion.tablegen.hole_label(hole, rules) instead of hole_class.",
            "Hero: implement variant_decide for 'discard' = keep the two cards with the best flop_strength "
            "category; default_discard tosses the lowest unpaired, unsuited card.",
            "Hero: after the discard, treat opponents' face-up cards as dead cards in any HS estimate.",
        ),
        hooks_factory=TossHooks,
        needs_engine=True,
        tables_to_rerun=("preflop_equity", "preflop_rank", "flop_strength"),
        axis="information", tables="regenerate",
        tables_note="best2+tags classes, keep=2 (perfect-hindsight discard, an upper bound); no matrix",
        config_patch={"preflop.open_frac_default": 0.08, "pushfold.threshold_bb": 10.0},
    )


def swap_holdem() -> Variant:
    rules = Rules(extras={"variant": "swap_holdem", "swap_p_flop": 0.1, "swap_p_turn": 0.05})
    return Variant(
        name="swap_holdem",
        summary="On the flop each of your hole cards is replaced from the deck with probability 0.1, on the "
                "turn 0.05. You are told your new cards; nobody else is. (MIT 2022.)",
        rules=rules,
        breaks=(
            "Tables stay valid at the moment they are read: preflop equity is computed assuming cards are "
            "kept, which overstates preflop edges by a small amount (about 10% of the time your hand is "
            "re-rolled on the flop). The strategy breaks more than the tables: hole cards must be re-read "
            "from the observation on every street, never cached per hand, and opponent ranges inferred "
            "preflop decay (a preflop raiser's flop hand is 19% likely to differ). Postflop equity should be "
            "discounted toward random by the swap probability of the streets still to come."
        ),
        checklist=(
            "No table regeneration needed; optionally gen_tables with --samples lowered to buy time elsewhere.",
            "Hero: read obs.hole every call; drop any per-hand cache of hand class.",
            "Hero: multiply postflop HS edge by (1 - p_remaining_swaps) before sizing bets; tighten river "
            "bluff-catching (villain's hand is less correlated with earlier action).",
        ),
        hooks_factory=SwapHooks,
        needs_engine=True,
        axis="information",
        config_patch={"postflop.value_tier": 5, "postflop.semibluff_freq": 0.4},
    )


def bounty() -> Variant:
    rules = Rules(extras={"variant": "bounty", "bounty_ratio": 1.5, "bounty_constant": 10,
                          "rounds_per_bounty": 25, "bounty_funding": "house"})
    return Variant(
        name="bounty",
        summary="Every player has a bounty rank, redrawn every 25 hands. Win a pot while holding that rank or "
                "while it sits on the board and the house pays you 1.5x your winnings plus 10 chips. "
                "(MIT 2025, with the house funding the bonus.)",
        rules=rules,
        breaks=(
            "No table changes: card strength is untouched. What changes is the value of a hand containing "
            "the bounty rank (and of boards showing it), so preflop thresholds should loosen for hands with "
            "the bounty rank by roughly the bounty multiplier on the pot share, and continuation bets on "
            "bounty boards are worth more. In an 8-max SNG the ICM layer matters more than the bounty; keep "
            "the bounty bonus as a small additive term in the preflop score, not a rewrite. House funding "
            "means chips in play grow over the table (ICM at the cap still sums to the payouts)."
        ),
        checklist=(
            "No regeneration. Read your bounty rank from obs.extras['bounties'][seat].",
            "Hero: add +1 'rank point' to preflop score for hands containing the bounty rank; widen call "
            "thresholds by the multiplier only when the pot is small relative to stacks.",
            "Set rules.extras['bounty_funding'] to 'losers' if the organizers take it from the loser.",
        ),
        hooks_factory=BountyHooks,
        needs_engine=True,
        axis="payoff",
        config_patch={"preflop.call_raise_frac": 0.5},
    )


def short_deck() -> Variant:
    rules = Rules(extras={"variant": "short_deck", "removed_ranks": [0, 1, 2, 3],
                          "category_order": "flush_over_full_house", "low_straight": "A6789"})
    return Variant(
        name="short_deck",
        summary="Six-plus hold'em: deuces through fives are out (36 cards). A flush beats a full house and "
                "A-6-7-8-9 is a straight. Everything else is hold'em.",
        rules=rules,
        breaks=(
            "Rules has no field for removed ranks, so this lives in extras['removed_ranks']; the engine and "
            "gen_tables honour it (classes with removed ranks vanish, equities shift up for pairs and down for "
            "suited connectors), but the generator's evaluator still orders flush below full house and misses "
            "A6789, so every table is slightly wrong at the top of the distribution; the sim's showdown uses "
            "ShortDeckHooks.score_hand. Flop textures change meaning: 'connected' is almost every flop. "
            "Strategy: pairs and sets are stronger, flushes rarer and stronger, straight draws much more live "
            "(16 outs instead of 8 for an open-ender)."
        ),
        checklist=(
            "python tools/gen_tables.py --rules variant.json --out tables/  (deck is 36 cards)",
            "Hero: use ShortDeckHooks.score_hand for every HS estimate.",
            "Hero: drop charts for removed classes; raise the value of pocket pairs and of any flush; "
            "treat a flush draw as ~1.3x and an open-ender as ~1.6x their hold'em equity.",
        ),
        hooks_factory=ShortDeckHooks,
        needs_engine=True,
        tables_to_rerun=("preflop_equity", "preflop_rank", "hu_matrix", "flop_strength"),
        axis="ranking", tables="approximate",
        tables_note="36-card deck; generator keeps hold'em category order and misses A6789 (top of the distribution off)",
        config_patch={"postflop.value_tier": 3, "preflop.open_frac_default": 0.14},
    )


def two_boards() -> Variant:
    rules = Rules(extras={"variant": "two_boards", "n_boards": 2, "pot_split": "half_per_board"})
    return Variant(
        name="two_boards",
        summary="Two boards run at once. Half the pot goes to the best hand on the top board, half to the best "
                "hand on the bottom board; scoop both and you take it all. (MIT 2021 had three.)",
        rules=rules,
        breaks=(
            "Observation.board holds board 1; board 2 travels in obs.extras['boards'], which the adapter has "
            "to build from the kit; any hero code that evaluates obs.board alone sees half the picture. "
            "Preflop tables stay valid as an ordering but equity is less volatile (two boards average out), "
            "so all-in thresholds should move toward the mean: shove less wide, call wider. flop_strength "
            "applies per board; a hand that is strong on one board and dead on the other is worth about "
            "half the pot, which is a new 'scoop or split' dimension the postflop rules must size for."
        ),
        checklist=(
            "No regeneration. Adapter: put every board in obs.extras['boards'] and the first in obs.board.",
            "Hero: compute HS per board, value = mean; bet big only when strong on both (scoop).",
        ),
        hooks_factory=TwoBoardsHooks,
        needs_engine=True,
        axis="information",
        config_patch={"pushfold.threshold_bb": 10.0, "preflop.call_raise_frac": 0.55},
    )


def pot_limit() -> Variant:
    rules = Rules(betting="potlimit", extras={"variant": "pot_limit", "max_raise_fn": "pot_limit_max_raise"})
    return Variant(
        name="pot_limit",
        summary="Pot-limit tonight: the most you can raise is the size of the pot after your call. The kit "
                "tells you the cap in max_raise; a raise above it is an illegal action and folds you.",
        rules=rules,
        breaks=(
            "No table changes. The strategy's shove logic breaks: with blinds 10/20 and 2000 stacks you "
            "cannot get all-in preflop in one move, so push/fold charts do not apply until stacks are "
            "under about 3 pots; raise sizes must be clamped by obs.max_raise (SafeBot.clamp does) or the "
            "kit will reject them. Multi-street planning matters more: value hands bet pot on every street "
            "to get stacks in by the river. The engine computes max_raise = current bet + pot after the call."
        ),
        checklist=(
            "No regeneration.",
            "Adapter: if the kit does not report the cap, set obs.max_raise = pot_limit_max_raise(obs).",
            "Hero: disable the preflop shove branch when max_raise < stack; use pot-sized raises.",
        ),
        needs_engine=True,
        axis="betting",
        config_patch={"pushfold.threshold_bb": 6.0},
    )


# ------------------------------------------------------------------------------- catalog-only entries

def three_card_blind_discard() -> Variant:
    rules = Rules(hole_cards=3, extras={"variant": "three_card_blind_discard", "discard_street": 1,
                                        "discard_face_up": True, "keep": 2, "blind_discard": True})
    return Variant(
        name="three_card_blind_discard",
        summary="Three hole cards, and you toss one face up before the flop is shown. Showdown is your two "
                "kept cards and the five-card board.",
        rules=rules,
        breaks=(
            "Same tables as toss_or_holdem (best2+tags, keep=2); the discard decision is simpler, pure preflop "
            "hand selection: keep the pair, else the suited two, else the two highest, which is default_discard. "
            "Hero still has no 3-card preflop path (check/fold)."
        ),
        checklist=("python tools/gen_tables.py --rules variant.json --out tables/",
                   "Hero: preflop by hole_label; variant_decide('discard') = default_discard."),
        hooks_factory=lambda: TossHooks(see_flop=False),
        needs_engine=True,
        tables_to_rerun=("preflop_equity", "preflop_rank", "flop_strength"),
        axis="information", tables="regenerate",
        tables_note="identical generator inputs to toss_or_holdem",
        config_patch={"preflop.open_frac_default": 0.08},
    )


def three_card_keep() -> Variant:
    rules = Rules(hole_cards=3, extras={"variant": "three_card_keep"})
    return Variant(
        name="three_card_keep",
        summary="Three hole cards and you keep all three: best five from your three plus the board.",
        rules=rules,
        breaks=(
            "Tables regenerate under the best2+tags scheme (no matrix). Made hands are much more frequent "
            "(8 cards at the river): top pair is weak, two pair is the new one pair, flushes and straights are "
            "common. Hero's postflop tiers and the push/fold solve assume two cards; Hero plays check/fold "
            "preflop with three cards, so it is a bystander here."
        ),
        checklist=("python tools/gen_tables.py --rules variant.json --out tables/",
                   "Hero: preflop by hole_label; raise every postflop value tier by one category."),
        tables_to_rerun=("preflop_equity", "preflop_rank", "flop_strength"),
        axis="information", tables="regenerate",
        config_patch={"postflop.value_tier": 5},
    )


def omaha_four() -> Variant:
    rules = Rules(hole_cards=4, must_use_hole=2, extras={"variant": "omaha_four"})
    return Variant(
        name="omaha_four",
        summary="Four hole cards; at showdown you must use exactly two of them with exactly three from the "
                "board. Four to a flush in your hand is not a flush.",
        rules=rules,
        breaks=(
            "The engine evaluates must_use_hole=2 exactly (60 five-card evaluations per showdown). gen_tables "
            "honours must_use_hole in its showdown too, with 4-card best2+tags classes (550 labels) "
            "and no matrix; samples per class are thin at catalog budgets. Hero has no 4-card path at all: "
            "preflop falls through to check/fold and postflop to the safe action, so it blinds off. The "
            "bestiary's two-card helpers pick the best two of four, which is wrong but legal."
        ),
        checklist=("python tools/gen_tables.py --rules variant.json --out tables/ --samples 2000",
                   "Hero: preflop by hole_label; postflop strength must use the 2+3 rule (engine.evaluate_must_use)."),
        tables_to_rerun=("preflop_equity", "preflop_rank", "flop_strength"),
        axis="information", tables="regenerate",
        tables_note="4-card classes, must_use_hole=2 showdown; reduced samples",
        config_patch={"postflop.value_tier": 5, "preflop.open_frac_default": 0.10},
    )


def swap_one_turn() -> Variant:
    rules = Rules(extras={"variant": "swap_one_turn", "swap_street": 2, "swap_count": 1})
    return Variant(
        name="swap_one_turn",
        summary="At the turn, before betting, each player may replace one hole card with the next card off "
                "the deck. Everyone sees who swapped, not what.",
        rules=rules,
        breaks=(
            "No table changes. Hero must re-read obs.hole every street (it does) and decide the swap "
            "(variant_decide 'swap'); the default keeps pairs and board pairs and swaps a low unpaired card. "
            "obs.extras['swapped'] says who swapped: a swap is a weakness tell the profiler could use."
        ),
        checklist=("No regeneration.", "Hero: variant_decide('swap') by flop_strength category of the kept pair."),
        hooks_factory=SwapOneHooks,
        needs_engine=True,
        axis="information",
        config_patch={"postflop.value_tier": 4},
    )


def exposed_card() -> Variant:
    rules = Rules(extras={"variant": "exposed_card", "exposed_index": 0})
    return Variant(
        name="exposed_card",
        summary="One of your two hole cards is dealt face up for the table to see; the other stays private.",
        rules=rules,
        breaks=(
            "No table changes. The information is in obs.extras['exposed'] ({seat: card}); nothing in Hero "
            "reads it, so Hero plays as if nobody saw anything and gives away nothing it knows how to use. "
            "The right adaptation is range-narrowing by the exposed card (a visible ace behind you is a "
            "reason not to steal) and card removal in HS estimates."
        ),
        checklist=("No regeneration.", "Hero: remove exposed cards from the deck in any HS estimate; tighten "
                   "steals when a high card is exposed behind."),
        hooks_factory=ExposedCardHooks,
        needs_engine=True,
        axis="information",
        config_patch={},
    )


def bonus_card() -> Variant:
    rules = Rules(extras={"variant": "bonus_card", "price_bb": 1.0, "street": 1})
    return Variant(
        name="bonus_card",
        summary="On the flop anyone still in may buy a third hole card for one big blind, paid into the pot. "
                "(MIT 2023 auctioned the card; here the price is posted so eight players can play it.)",
        rules=rules,
        breaks=(
            "Tables stay default for the two-card game; a buyer has three cards and keeps all three (8 cards at "
            "the river, within the evaluator). Hero's postflop path only handles two hole cards: after buying "
            "it takes the safe action, so the default (buy) hurts Hero until it answers 'buy_card' with False "
            "or learns three-card postflop. Buying is right when the pot is big relative to the price."
        ),
        checklist=("No regeneration.", "Hero: variant_decide('buy_card') = pot >= 8x price; three-card postflop tiers."),
        hooks_factory=BonusCardHooks,
        needs_engine=True,
        axis="information",
        config_patch={},
    )


def lowball() -> Variant:
    rules = Rules(extras={"variant": "lowball", "lowball": "2-7"})
    return Variant(
        name="lowball",
        summary="Reversed rankings: the worst hand wins. Aces are high, straights and flushes count against you, "
                "so 7-5-4-3-2 of mixed suits is the best hand and a royal flush the worst.",
        rules=rules,
        breaks=(
            "Everything about hand strength inverts and the generator cannot express it (it has no score hook), "
            "so every table is wrong and tables/variants has none for it. Hero's charts, push/fold and postflop "
            "tiers all value the wrong hands: expect it to finish last. The cheap adaptation is to invert "
            "preflop_rank (1 - p) and treat made hands as liabilities."
        ),
        checklist=("Hero: invert preflop_rank; postflop: value = no pair, no straight, no flush, low high card.",),
        hooks_factory=LowballHooks,
        needs_engine=True,
        axis="ranking", tables="unsupported",
        tables_note="generator has no score hook; the high-hand tables would be exactly backwards",
        config_patch={"use_profiler": False},
    )


def wild_deuces() -> Variant:
    rules = Rules(extras={"variant": "wild_deuces", "wild_rank": 0})
    return Variant(
        name="wild_deuces",
        summary="Deuces are wild: a 2 stands for any card that makes your best hand. No five of a kind.",
        rules=rules,
        breaks=(
            "The generator does not know wilds, so tables/variants has none: deuces are the worst cards in every "
            "table and the best in the game. Hero treats 22 as a small pair and 2x as trash; any hand with a "
            "deuce should move to the top of the preflop order. Made-hand frequencies rise (trips are common), "
            "so value tiers should move up one category."
        ),
        checklist=("Hero: preflop rank of any hand with a deuce = top 5%; postflop tiers +1 category.",),
        hooks_factory=WildRankHooks,
        needs_engine=True,
        axis="ranking", tables="unsupported",
        tables_note="generator has no wild-card showdown",
        config_patch={"postflop.value_tier": 5},
    )


def flush_over_full_house() -> Variant:
    rules = Rules(extras={"variant": "flush_over_full_house", "category_order": "flush_over_full_house"})
    return Variant(
        name="flush_over_full_house",
        summary="One change to the rankings: a flush beats a full house. Everything else as in hold'em.",
        rules=rules,
        breaks=(
            "Only showdowns between a flush and a full house change (under 1% of showdowns), so the default "
            "tables are a fine approximation and nothing is regenerated. Hero's postflop tier for a full house "
            "on a three-flush board should drop one notch."
        ),
        checklist=("No regeneration.", "Hero: on a 3+ flush board, a full house is one tier lower."),
        hooks_factory=FlushOverFullHooks,
        needs_engine=True,
        axis="ranking", tables="default",
        tables_note="the reorder affects <1% of showdowns; default tables are within noise",
        config_patch={},
    )


def knockout_bounty() -> Variant:
    rules = Rules(extras={"variant": "knockout_bounty", "ko_points": 1.0, "ko_funding": "house"})
    return Variant(
        name="knockout_bounty",
        summary="Knockouts pay: bust a player and the house adds one point to your score for the table, on top "
                "of your finishing points. Bust two on one hand, two points.",
        rules=rules,
        breaks=(
            "No table changes and no chips move; the engine adds points through on_bust (the biggest winner of "
            "the hand collects). The ICM curve Hero builds from Rules.payouts does not see the bonus, so Hero "
            "undervalues calling a short stack's shove by about one payout unit. The patch is a lower ICM "
            "premium against covered short stacks."
        ),
        checklist=("No regeneration.", "Hero: when covering an all-in short stack, add ko_points to the call EV."),
        hooks_factory=KnockoutHooks,
        needs_engine=True,
        axis="payoff",
        config_patch={"preflop.call_raise_frac": 0.5, "pushfold.threshold_bb": 12.0},
    )


def top_heavy() -> Variant:
    rules = Rules(payouts=(50, 25, 12, 6, 3, 2, 1, 1), extras={"variant": "top_heavy"})
    return Variant(
        name="top_heavy",
        summary="Points 50 / 25 / 12 / 6 / 3 / 2 / 1 / 1 by finishing position; ICM on the same table for "
                "survivors at the hand cap. Winning the table is everything.",
        rules=rules,
        breaks=(
            "Nothing in the tables. Hero reads payouts into its ICM curve, so no code changes; drill 2 measured "
            "Hero first under this table (25.8 vs tag 19.9) because it wins outright most often. Patches that "
            "trade bust rate for first places are the lever."
        ),
        checklist=("No regeneration.", "Confirm hero.core.payouts after new_table."),
        axis="payoff",
        config_patch={"preflop.open_frac_default": 0.13, "postflop.semibluff_freq": 0.6},
    )


def hi_lo() -> Variant:
    rules = Rules(extras={"variant": "hi_lo", "hi_lo": "8-or-better", "low": "A-5"})
    return Variant(
        name="hi_lo",
        summary="Split pot: half to the best high hand, half to the best low hand of five different cards eight "
                "or under (ace plays low, straights and flushes do not hurt the low). No qualifying low and the "
                "high hand takes it all.",
        rules=rules,
        breaks=(
            "The generator has no low evaluation, so tables stay default and overvalue high-only hands (KK) "
            "relative to two-way hands (A2s, A3s). Hero plays high only, which is legal and loses the low half "
            "to whoever qualifies. The patch is preflop: promote ace-low suited hands, demote mid pairs."
        ),
        checklist=("No regeneration.", "Hero: preflop bonus for A2-A5 and suited wheel cards; value-bet only two-way hands."),
        hooks_factory=HiLoHooks,
        needs_engine=True,
        axis="payoff", tables="unsupported",
        tables_note="generator scores high only; a two-way equity table does not exist",
        config_patch={"postflop.value_tier": 4},
    )


def antes_from_level_3() -> Variant:
    rules = Rules(ante_per_level=(0, 0, 4, 8, 12, 16, 24, 32), ante_from_level=2,
                  extras={"variant": "antes_from_level_3", "ante_rule": "about 8% of the big blind from level 3"})
    return Variant(
        name="antes_from_level_3",
        summary="From level 3 everyone antes before the deal: 4 at 25/50, 8 at 50/100, 12 at 75/150, 16 at 100/200, "
                "24 at 150/300, 32 at 200/400. Antes go straight into the pot and do not count toward bets.",
        rules=rules,
        breaks=(
            "No table changes. The push/fold solve assumes blinds only, so shoves are worth about 20% more than "
            "the tables say from level 3 (the pot is bigger before anyone acts), and opens should widen by one "
            "position step. Hero's stack_bb ignores the ante; the engine now posts it so the sim can price the "
            "patch drill 2 could not (docs/drills/prompt-drill-2-kitC-payoff.md)."
        ),
        checklist=("No regeneration.", "Hero: pushfold.threshold_bb + 2 and opens one step wider from level 3."),
        axis="betting",
        config_patch={"pushfold.threshold_bb": 14.0, "preflop.open_frac_default": 0.13},
    )


def fixed_raise() -> Variant:
    rules = Rules(betting="fixedlimit", extras={"variant": "fixed_raise", "raise_sizes": "1 bb preflop and flop, 2 bb turn and river"})
    return Variant(
        name="fixed_raise",
        summary="Fixed raise sizes: a raise is exactly one big blind preflop and on the flop, two big blinds on the "
                "turn and river. No cap on the number of raises; a short stack can still go all-in for less.",
        rules=rules,
        breaks=(
            "No table changes. Every bot that sizes its own raises gets clamped to the one legal size (counted "
            "illegal in the sim unless it reads min_raise == max_raise); the kit will reject them. Shoving does "
            "not exist, so push/fold is irrelevant and the game is about showdown frequency: fold less, call "
            "down more, since bets are small relative to the pot."
        ),
        checklist=("No regeneration.", "Hero: raise_to(obs.min_raise) everywhere; call-down threshold one tier lower."),
        axis="betting",
        config_patch={"profiler_calldown_slope": -0.4, "postflop.value_tier": 3},
    )


def fast_schedule() -> Variant:
    rules = Rules(hands_per_level=15, extras={"variant": "fast_schedule"})
    return Variant(
        name="fast_schedule",
        summary="Turbo: blinds rise every 15 hands instead of 25. Level 8 (200/400) arrives at hand 105.",
        rules=rules,
        breaks=(
            "No table changes. Average stacks are shorter sooner, so the push/fold module decides more of the "
            "game and the postflop module less; the 200-hand cap and ICM at the cap matter more because fewer "
            "tables finish. Hero reads the schedule from Rules."
        ),
        checklist=("No regeneration.", "Hero: pushfold.threshold_bb 14; fewer speculative calls."),
        axis="betting",
        config_patch={"pushfold.threshold_bb": 14.0, "preflop.call_raise_frac": 0.3},
    )


def straddle() -> Variant:
    rules = Rules(straddle=2, extras={"variant": "straddle"})
    return Variant(
        name="straddle",
        summary="A live straddle is on: the player after the big blind posts two big blinds before the cards, acts "
                "last preflop, and the minimum raise over it is to four big blinds.",
        rules=rules,
        breaks=(
            "No table changes. Effective blinds double preflop, so stacks are half as deep in blinds as Hero "
            "believes (stack_bb uses blinds[1]); push/fold should key on the straddle. Position logic that counts "
            "players behind is off by one preflop (the straddler acts last). The straddler's 2 bb is dead money "
            "worth stealing."
        ),
        checklist=("No regeneration.", "Hero: treat max(bets) preflop as the big blind for stack depth and sizing."),
        axis="betting",
        config_patch={"pushfold.threshold_bb": 16.0, "preflop.open_frac_default": 0.13},
    )


PRESETS: dict[str, Callable[..., Variant]] = {
    "permuted_ranks": permuted_ranks,
    "toss_or_holdem": toss_or_holdem,
    "swap_holdem": swap_holdem,
    "bounty": bounty,
    "short_deck": short_deck,
    "two_boards": two_boards,
    "pot_limit": pot_limit,
}

CATALOG: dict[str, Callable[..., Variant]] = {
    # ranking
    "permuted_ranks": permuted_ranks,
    "short_deck": short_deck,
    "lowball": lowball,
    "wild_deuces": wild_deuces,
    "flush_over_full_house": flush_over_full_house,
    # information
    "toss_or_holdem": toss_or_holdem,
    "three_card_blind_discard": three_card_blind_discard,
    "three_card_keep": three_card_keep,
    "omaha_four": omaha_four,
    "swap_holdem": swap_holdem,
    "swap_one_turn": swap_one_turn,
    "exposed_card": exposed_card,
    "two_boards": two_boards,
    "bonus_card": bonus_card,
    # payoff
    "bounty": bounty,
    "knockout_bounty": knockout_bounty,
    "top_heavy": top_heavy,
    "hi_lo": hi_lo,
    # betting
    "pot_limit": pot_limit,
    "antes_from_level_3": antes_from_level_3,
    "fixed_raise": fixed_raise,
    "fast_schedule": fast_schedule,
    "straddle": straddle,
}


def get(name: str, seed: int = 0) -> Variant:
    if name == "permuted_ranks":
        return permuted_ranks(seed)
    if name in PRESETS:
        return PRESETS[name]()
    if name in CATALOG:
        return CATALOG[name]()
    from . import variants_unseen  # held out: reachable by name, never in CATALOG / PRESETS (see its docstring)

    if name in variants_unseen.HELD_OUT:
        return variants_unseen.get(name)
    raise KeyError(f"unknown variant {name!r}; known: {', '.join(CATALOG)}; held out: {', '.join(variants_unseen.HELD_OUT)}")


def names() -> list[str]:
    """The drill presets (what `hyperion.drills.run --variant random` picks from)."""
    return list(PRESETS)


def catalog_names() -> list[str]:
    return list(CATALOG)


def catalog(seed: int = 0) -> list[Variant]:
    """Every entry, in axis order."""
    return [get(n, seed) for n in CATALOG]


def validate(v: Variant) -> list[str]:
    """Structural checks a preset must pass; returns a list of problems (empty = valid)."""
    r = v.rules
    problems = []
    if sorted(r.rank_order) != list(range(13)):
        problems.append("rank_order is not a permutation of 0..12")
    if r.hole_cards < 1 or r.hole_cards > 4:
        problems.append("hole_cards out of range")
    if list(r.board_sizes) != sorted(r.board_sizes) or r.board_sizes[0] != 0:
        problems.append("board_sizes must start at 0 and not decrease")
    showdown_hole = r.must_use_hole or r.extras.get("keep", r.hole_cards)
    if showdown_hole + r.board_sizes[-1] > 8 and not r.must_use_hole:
        problems.append("evaluator handles at most 8 cards")
    if r.must_use_hole and not 1 <= r.must_use_hole <= min(4, r.hole_cards):
        problems.append("must_use_hole must be 1..hole_cards")
    if r.n_suits not in (1, 2, 3, 4):
        problems.append("n_suits")
    if r.betting not in ("nolimit", "potlimit", "fixedlimit"):
        problems.append("betting")
    if r.ante < 0 or r.ante_from_level < 0 or any(a < 0 for a in r.ante_per_level) or r.straddle < 0:
        problems.append("negative ante or straddle")
    if v.axis not in AXES:
        problems.append("axis")
    if v.tables not in ("default", "regenerate", "approximate", "unsupported"):
        problems.append("tables")
    if v.hooks is not None and not isinstance(v.hooks, VariantHooks):
        problems.append("hooks must subclass VariantHooks")
    if v.needs_engine and v.hooks is None and r.betting == "nolimit":
        problems.append("needs_engine without hooks or a documented engine rule")
    removed = set(r.extras.get("removed_ranks", ()))
    if (13 - len(removed)) * r.n_suits < r.hole_cards * r.n_players + r.board_sizes[-1] * r.extras.get("n_boards", 1):
        problems.append("deck too small")
    return problems


# ------------------------------------------------------------------------------- CLI

def _list_lines(seed: int = 0) -> list[str]:
    lines = [f"{'name':<26} {'axis':<12} {'playable':<9} {'tables':<12} summary"]
    for v in catalog(seed):
        first = v.summary.split(". ")[0].rstrip(".")
        lines.append(f"{v.name:<26} {v.axis:<12} {('yes' if v.playable else 'no'):<9} {v.tables:<12} {first}")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.drills.variants", description="Variant catalog.")
    p.add_argument("--list", action="store_true", help="list every catalog entry")
    p.add_argument("--rules", metavar="NAME", help="write the entry's Rules as JSON (gen_tables / sim accept it)")
    p.add_argument("--out", default=None, help="output path for --rules (default rules_NAME.json)")
    p.add_argument("--show", metavar="NAME", help="print the entry's summary, what breaks, checklist and Config patch")
    p.add_argument("--seed", type=int, default=0, help="seed for permuted_ranks")
    a = p.parse_args(argv)
    if a.list:
        print("\n".join(_list_lines(a.seed)))
        return 0
    if a.show:
        v = get(a.show, a.seed)
        print(f"{v.name}  [{v.axis}]  playable={'yes' if v.playable else 'no'}  tables={v.tables}")
        print(f"\n{v.summary}\n\nWhat breaks: {v.breaks}\n")
        for c in v.checklist:
            print(f"- {c}")
        print(f"\nConfig patch: {json.dumps(v.config_patch)}")
        if v.playable_note or v.tables_note:
            print(f"\nNotes: {v.playable_note} {v.tables_note}".rstrip())
        return 0
    if a.rules:
        v = get(a.rules, a.seed)
        out = a.out or f"rules_{v.name}.json"
        with open(out, "w") as f:
            json.dump(v.rules_json(), f, indent=1)
            f.write("\n")
        print(out)
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
