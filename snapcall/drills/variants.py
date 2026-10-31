"""Variant presets: past MIT twists and plausible new ones, as Rules + hooks + a regeneration checklist.

Each preset answers three questions: what Rules/extras describe it, what breaks in our tables and
strategy, and what to rerun or retune. Where the twist needs the engine's cooperation it is a
`VariantHooks` object whose methods the sim calls at fixed points. Signatures (the contract with
the sim builder; defaults are identity so an unwired hook is harmless):

  on_deal(holes, deck, rng) -> holes
      after hole cards are dealt, before preflop betting. holes: list[tuple[int,...]] per seat
      (empty tuple for seats not in the hand); deck: list[int] of undealt cards the hook may pop
      from; rng: random.Random owned by the table.
  on_street(street, board, holes, deck, rng, ask=None) -> (board, holes)
      when the engine advances to `street` (1 = flop, ...), after that street's board cards are
      dealt and before betting. May change board and holes (swap, discard, second board).
      ask(seat, prompt: dict) -> object is an optional callback the engine supplies to let a bot
      make a variant decision (e.g. which card to discard); hooks must work when ask is None.
  score_hand(hole, board, rules) -> int
      replaces evaluate_displayed at showdown. Higher wins. Default: evaluate_displayed(hole+board).
  on_payout(deltas, holes, board, hand_no, rules, rng) -> deltas
      optional; adjusts the chip deltas of a finished hand (bounties). Must keep sum(deltas) == 0
      unless rules.extras says the house adds chips.

Cards everywhere are *displayed* ints (what the bot sees); rank_order maps them to strength.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, Sequence

from snapcall.core.cards import remap
from snapcall.core.eval import category, evaluate, evaluate_displayed
from snapcall.core.types import Observation, Rules

Holes = list  # list[tuple[int, ...]] per seat


class VariantHooks:
    """Identity hooks. Subclass and override what the twist needs."""

    def on_deal(self, holes: Holes, deck: list[int], rng: random.Random) -> Holes:
        return holes

    def on_street(self, street: int, board: tuple[int, ...], holes: Holes, deck: list[int],
                  rng: random.Random, ask: Callable | None = None) -> tuple[tuple[int, ...], Holes]:
        return board, holes

    def score_hand(self, hole: Sequence[int], board: Sequence[int], rules: Rules) -> int:
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

    def rules_json(self) -> dict:
        from snapcall.tablegen import rules_to_dict

        return rules_to_dict(self.rules)


# ------------------------------------------------------------------------------- presets

def permuted_ranks(seed: int = 0) -> Variant:
    """MIT 2020: ranks are secretly permuted. We model the *known* permutation; inferring it is strategy."""
    perm = list(range(13))
    random.Random(seed).shuffle(perm)
    rules = Rules(rank_order=tuple(perm), extras={"variant": "permuted_ranks", "seed": seed})
    return Variant(
        name="permuted_ranks",
        summary=f"Rank strength order permuted (seed {seed}); evaluator unchanged via Rules.rank_order.",
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
    )


class TossHooks(VariantHooks):
    """3 hole cards; after the flop each player discards one hole card face up (OOP first).

    8-max adaptation: the discard is public information (self.discards, which the engine should put
    in obs.extras['discards']) but not a community card, so showdown is 2 hole + 5 board. MIT's
    heads-up original added discards to the board; see docs/decisions.md.
    """

    def __init__(self) -> None:
        self.discards: dict[int, int] = {}

    def on_deal(self, holes, deck, rng):
        self.discards = {}
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        if street != 1:
            return board, holes
        new_holes = list(holes)
        for seat in range(len(holes)):  # the engine passes holes ordered so OOP seats come first
            h = holes[seat]
            if len(h) != 3:
                continue
            idx = None
            if ask is not None:
                try:
                    idx = int(ask(seat, {"decision": "discard", "hole": h, "board": board}))
                except Exception:  # noqa: BLE001
                    idx = None
            if idx is None or not 0 <= idx < 3:
                idx = default_discard(h)
            self.discards[seat] = h[idx]
            new_holes[seat] = h[:idx] + h[idx + 1:]
        return board, new_holes


def default_discard(hole: Sequence[int]) -> int:
    """Index of the card to toss: keep the pair if any, else the suited pair, else the two highest."""
    def keep_score(i: int, j: int) -> float:
        a, b = hole[i], hole[j]
        return (100 if a >> 2 == b >> 2 else 0) + (3 if a & 3 == b & 3 else 0) + (a >> 2) + (b >> 2)

    best = max(((i, j) for i in range(len(hole)) for j in range(i + 1, len(hole))), key=lambda ij: keep_score(*ij))
    return next(k for k in range(len(hole)) if k not in best)


def toss_or_holdem() -> Variant:
    """MIT 2026: 3 hole cards, 2-card flop, face-up discard, then turn and river (6 board cards)."""
    rules = Rules(hole_cards=3, extras={"variant": "toss_or_holdem", "discard_street": 1,
                                        "discard_face_up": True, "keep": 2})
    return Variant(
        name="toss_or_holdem",
        summary="Three hole cards; after the flop each player discards one face-up (dead, not community); "
                "showdown is the kept 2 + 5 board. MIT 2026 heads-up put discards on the board.",
        rules=rules,
        breaks=(
            "The 169-class notion breaks: gen_tables switches to the best2+tags scheme (hole_classes.json) "
            "and skips hu_matrix. extras['keep']=2 makes the generator score the best 2 of 3 at showdown, "
            "a perfect-hindsight discard, so equities are an upper bound: an ordering, not a price. The "
            "discard is a new decision Observation does not model (engine passes obs.extras['decision']="
            "'discard'), and opponents' discards are dead cards hero should remove from any HS estimate. "
            "If Sequoia keeps MIT's rule that discards join the board, board_sizes become (0, 2, 2+n, 3+n, "
            "4+n) and the evaluator needs a best-5-of-many path; nothing here is ready for that."
        ),
        checklist=(
            "python tools/gen_tables.py --rules variant.json --out tables/  (writes hole_classes.json)",
            "Hero: look up preflop_rank by snapcall.tablegen.hole_label(hole, rules) instead of hole_class.",
            "Hero: implement discard(hole, board) = keep the two cards with the best flop_strength category; "
            "default to tossing the lowest unpaired, unsuited card.",
            "Hero: after the discard, treat opponents' face-up cards as dead cards in any HS estimate.",
            "Sim: wire TossHooks.on_street at street 1 with ask= each bot's discard choice.",
        ),
        hooks=TossHooks(),
        needs_engine=True,
        tables_to_rerun=("preflop_equity", "preflop_rank", "flop_strength"),
    )


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


def swap_holdem() -> Variant:
    rules = Rules(extras={"variant": "swap_holdem", "swap_p_flop": 0.1, "swap_p_turn": 0.05})
    return Variant(
        name="swap_holdem",
        summary="On the flop each hole card is replaced with probability 0.1, on the turn 0.05 (MIT 2022).",
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
            "Sim: wire SwapHooks.on_street at streets 1 and 2.",
        ),
        hooks=SwapHooks(),
        needs_engine=True,
    )


class BountyHooks(VariantHooks):
    """MIT 2025: a private bounty rank per player, re-drawn every N hands; hitting it scales winnings."""

    def __init__(self, ratio: float = 1.5, constant: int = 10, rounds_per_bounty: int = 25):
        self.ratio, self.constant, self.rounds = ratio, constant, rounds_per_bounty
        self.bounties: dict[int, int] = {}

    def on_payout(self, deltas, holes, board, hand_no, rules, rng):
        if hand_no % self.rounds == 0 or not self.bounties:
            self.bounties = {s: rng.randrange(13) for s in range(len(deltas))}
        out = list(deltas)
        board_ranks = {c >> 2 for c in board}
        for s, d in enumerate(deltas):
            if d <= 0 or not holes[s]:
                continue
            hit = self.bounties[s] in board_ranks or any((c >> 2) == self.bounties[s] for c in holes[s])
            if hit:
                out[s] = int(d * self.ratio) + self.constant  # the engine decides who funds the extra
        return out


def bounty() -> Variant:
    rules = Rules(extras={"variant": "bounty", "bounty_ratio": 1.5, "bounty_constant": 10,
                          "rounds_per_bounty": 25, "bounty_rank": None})
    return Variant(
        name="bounty",
        summary="Each player has a private bounty rank, redrawn every 25 hands; a winner holding or seeing "
                "their rank on the board gets 1.5x winnings + 10 (MIT 2025).",
        rules=rules,
        breaks=(
            "No table changes: card strength is untouched. What changes is the value of a hand containing "
            "the bounty rank (and of boards showing it), so preflop thresholds should loosen for hands with "
            "the bounty rank by roughly the bounty multiplier on the pot share, and continuation bets on "
            "bounty boards are worth more. In an 8-max SNG the ICM layer matters more than the bounty; keep "
            "the bounty bonus as a small additive term in the preflop score, not a rewrite. Where the extra "
            "chips come from (house or loser) changes whether chip conservation holds in the sim."
        ),
        checklist=(
            "No regeneration. Read the bounty rank from obs.extras['bounty_rank'] (adapter must fill it).",
            "Hero: add +1 'rank point' to preflop score for hands containing the bounty rank; widen call "
            "thresholds by the multiplier only when the pot is small relative to stacks.",
            "Sim: wire BountyHooks.on_payout; decide whether the bonus is house-funded (default) or taken "
            "from the loser, and set rules.extras['bounty_funding'] accordingly.",
        ),
        hooks=BountyHooks(),
        needs_engine=True,
    )


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


def short_deck() -> Variant:
    rules = Rules(extras={"variant": "short_deck", "removed_ranks": [0, 1, 2, 3],
                          "category_order": "flush_over_full_house", "low_straight": "A6789"})
    return Variant(
        name="short_deck",
        summary="Deuces through fives removed (36 cards); flush beats full house; A-6-7-8-9 is a straight.",
        rules=rules,
        breaks=(
            "Rules has no field for removed ranks, so this lives in extras['removed_ranks']; gen_tables "
            "honours it (classes with removed ranks vanish, equities shift up for pairs and down for "
            "suited connectors), but the evaluator still orders flush below full house and misses A6789, so "
            "every table is slightly wrong at the top of the distribution until score_hand is the showdown "
            "judge in the sim and in any HS computation hero does. Flop textures change meaning: "
            "'connected' is almost every flop. Strategy: pairs and sets are stronger, flushes rarer and "
            "stronger, straight draws much more live (16 outs instead of 8 for an open-ender)."
        ),
        checklist=(
            "python tools/gen_tables.py --rules variant.json --out tables/  (deck is 36 cards)",
            "Sim and hero: use ShortDeckHooks.score_hand for every showdown and HS estimate.",
            "Hero: drop charts for removed classes; raise the value of pocket pairs and of any flush; "
            "treat a flush draw as ~1.3x and an open-ender as ~1.6x their hold'em equity.",
        ),
        hooks=ShortDeckHooks(),
        needs_engine=True,
        tables_to_rerun=("preflop_equity", "preflop_rank", "hu_matrix", "flop_strength"),
    )


class TwoBoardsHooks(VariantHooks):
    """Two boards dealt in parallel; the pot is split in half, each half awarded by its own board.

    `board` (the engine's) stays board 1. The hook deals and keeps board 2 per hand; the engine
    exposes both via boards(board) in obs.extras['boards'] and settles with score_boards.
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

    def score_hand(self, hole, board, rules):
        """Board 1 only, so an engine that has not wired score_boards still terminates."""
        return evaluate_displayed(tuple(hole) + tuple(board), rules)


def two_boards() -> Variant:
    rules = Rules(extras={"variant": "two_boards", "n_boards": 2, "pot_split": "half_per_board"})
    return Variant(
        name="two_boards",
        summary="Two independent boards; half the pot goes to the best hand on each (MIT 2021 had three).",
        rules=rules,
        breaks=(
            "Observation.board holds one board, so the second must travel in obs.extras['boards'] and the "
            "adapter has to build it; any hero code that evaluates obs.board alone sees half the picture. "
            "Preflop tables stay valid as an ordering but equity is less volatile (two boards average out), "
            "so all-in thresholds should move toward the mean: shove less wide, call wider. flop_strength "
            "applies per board; a hand that is strong on one board and dead on the other is worth about "
            "half the pot, which is a new 'scoop or split' dimension the postflop rules must size for."
        ),
        checklist=(
            "No regeneration. Adapter: put every board in obs.extras['boards'] and the first in obs.board.",
            "Hero: compute HS per board, value = mean; bet big only when strong on both (scoop).",
            "Sim: wire TwoBoardsHooks.on_deal/on_street; settle with score_boards, half the pot per board; "
            "put hooks.boards(board) in obs.extras['boards'].",
        ),
        hooks=TwoBoardsHooks(),
        needs_engine=True,
    )


def pot_limit_max_raise(obs: Observation) -> int:
    """Largest legal raise-to total under pot-limit: call, then raise by the pot after the call."""
    current = max(obs.bets)
    pot_after_call = obs.pot + sum(obs.bets) + obs.to_call
    return min(obs.max_raise, current + pot_after_call)


def pot_limit() -> Variant:
    rules = Rules(extras={"variant": "pot_limit", "betting": "pot_limit", "max_raise_fn": "pot_limit_max_raise"})
    return Variant(
        name="pot_limit",
        summary="Pot-limit betting: a raise may not exceed the pot after calling (no-limit otherwise).",
        rules=rules,
        breaks=(
            "No table changes. The strategy's shove logic breaks: with blinds 10/20 and 2000 stacks you "
            "cannot get all-in preflop in one move, so push/fold charts do not apply until stacks are "
            "under about 3 pots; raise sizes must be clamped by pot_limit_max_raise(obs) or the kit will "
            "reject them (and a rejected action is a fold). Multi-street planning matters more: value "
            "hands bet pot on every street to get stacks in by the river."
        ),
        checklist=(
            "No regeneration.",
            "Adapter: if the kit does not report the cap, set obs.max_raise = pot_limit_max_raise(obs).",
            "Hero: disable the preflop shove branch when max_raise < stack; use pot-sized raises.",
            "Sim: compute max_raise with pot_limit_max_raise when rules.extras['betting'] == 'pot_limit'.",
        ),
        needs_engine=True,
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


def get(name: str, seed: int = 0) -> Variant:
    if name == "permuted_ranks":
        return permuted_ranks(seed)
    return PRESETS[name]()


def names() -> list[str]:
    return list(PRESETS)


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
    showdown_hole = r.extras.get("keep", r.hole_cards)
    if showdown_hole + r.board_sizes[-1] > 8:
        problems.append("evaluator handles at most 8 cards")
    if r.n_suits not in (1, 2, 3, 4):
        problems.append("n_suits")
    if v.hooks is not None and not isinstance(v.hooks, VariantHooks):
        problems.append("hooks must subclass VariantHooks")
    if v.needs_engine and v.hooks is None and r.extras.get("betting") != "pot_limit":
        problems.append("needs_engine without hooks or a documented engine rule")
    return problems
