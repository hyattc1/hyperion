"""Shared contracts. Every module speaks these types; nothing imports a kit directly.

Cards are ints 0..51 = rank*4 + suit under the CANONICAL ordering (rank 0 = deuce ... 12 = ace).
A variant that permutes rank strength is handled by Rules.rank_order, which maps a *displayed*
rank index to its canonical strength index. The evaluator only ever sees canonical cards.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, Sequence

RANKS = "23456789TJQKA"
SUITS = "cdhs"


@dataclass(frozen=True)
class Rules:
    """Variant parameters. Defaults are standard no-limit hold'em, 8-max SNG in the target format."""

    hole_cards: int = 2
    board_sizes: tuple[int, ...] = (0, 3, 4, 5)  # cards on board per street index
    rank_order: tuple[int, ...] = tuple(range(13))  # displayed rank -> canonical strength
    n_suits: int = 4
    starting_stack: int = 2000
    small_blind: int = 10
    big_blind: int = 20
    blind_levels: tuple[tuple[int, int], ...] = (
        (10, 20), (15, 30), (25, 50), (50, 100), (75, 150), (100, 200), (150, 300), (200, 400),
    )
    hands_per_level: int = 25
    max_hands: int = 200
    n_players: int = 8
    # points by finishing position, index 0 = winner. Unknown until build; this is a placeholder.
    payouts: tuple[float, ...] = (8, 7, 6, 5, 4, 3, 2, 1)
    # --- betting structure (2026-10-31, variant catalog). Defaults are the standard game. ---
    ante: int = 0  # chips every seated player posts into the pot before the deal, 0 = none
    ante_from_level: int = 0  # antes start at this 0-based blind level (2 = "from level 3")
    ante_per_level: tuple[int, ...] = ()  # optional per-level ante schedule; overrides `ante` when set
    betting: str = "nolimit"  # "nolimit" | "potlimit" | "fixedlimit" (raise = 1 bb pre/flop, 2 bb after)
    straddle: int = 0  # live straddle in big blinds posted by the seat after the big blind (0 = off)
    # --- showdown ---
    must_use_hole: int = 0  # 0 = any combination; 2 = Omaha-style exactly two hole + three board
    # extra hooks for variants; strategy code may read these, core code ignores unknown keys
    extras: dict = field(default_factory=dict, hash=False, compare=False)

    def level_at(self, hand_no: int) -> int:
        return min(hand_no // self.hands_per_level, len(self.blind_levels) - 1)

    def blinds_at(self, hand_no: int) -> tuple[int, int]:
        return self.blind_levels[self.level_at(hand_no)]

    def ante_at(self, hand_no: int) -> int:
        """Chips each player antes on this hand: 0 before ante_from_level, then the schedule or `ante`."""
        level = self.level_at(hand_no)
        if level < self.ante_from_level:
            return 0
        if self.ante_per_level:
            return int(self.ante_per_level[min(level, len(self.ante_per_level) - 1)])
        return int(self.ante)

    def canonical_rank(self, displayed_rank: int) -> int:
        return self.rank_order[displayed_rank]

    @property
    def deck_size(self) -> int:
        return 13 * self.n_suits

    @property
    def streets(self) -> int:
        return len(self.board_sizes)


class Street(int, Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3


class ActionKind(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"  # amount = total bet this street (raise-to), not the increment


@dataclass(frozen=True)
class Action:
    kind: ActionKind
    amount: int = 0

    @staticmethod
    def fold() -> "Action":
        return Action(ActionKind.FOLD)

    @staticmethod
    def check() -> "Action":
        return Action(ActionKind.CHECK)

    @staticmethod
    def call() -> "Action":
        return Action(ActionKind.CALL)

    @staticmethod
    def raise_to(amount: int) -> "Action":
        return Action(ActionKind.RAISE, int(amount))

    def clamp(self, obs: "Observation") -> "Action":
        """Return a legal version of this action for obs, falling back to check then fold."""
        legal = obs.legal
        if self.kind is ActionKind.RAISE:
            if ActionKind.RAISE in legal:
                amt = max(obs.min_raise, min(obs.max_raise, self.amount))
                return Action(ActionKind.RAISE, amt)
            if ActionKind.CALL in legal:
                return Action.call()
        if self.kind in legal:
            return self
        if ActionKind.CHECK in legal:
            return Action.check()
        if ActionKind.CALL in legal and self.kind is ActionKind.CHECK:
            return Action.call()
        return Action.fold()


@dataclass
class Observation:
    """One decision point, kit-agnostic. Seats are 0..n-1, fixed for the table."""

    hole: tuple[int, ...]
    board: tuple[int, ...]
    street: int
    seat: int
    button: int
    stacks: list[int]  # chips behind, per seat, not counting this street's bets
    bets: list[int]  # chips committed this street, per seat
    in_hand: list[bool]
    pot: int  # chips in the middle from previous streets (excludes this street's bets)
    to_call: int
    min_raise: int  # minimum legal raise-to total
    max_raise: int  # all-in raise-to total
    legal: frozenset[ActionKind]
    hand_no: int
    blinds: tuple[int, int]
    history: list[tuple[int, Action]] = field(default_factory=list)  # (seat, action) this hand
    extras: dict = field(default_factory=dict)

    @property
    def n_players(self) -> int:
        return len(self.stacks)

    @property
    def players_left(self) -> int:
        """Seats still alive at the table (have chips behind or committed)."""
        return sum(1 for s, b in zip(self.stacks, self.bets) if s + b > 0)

    @property
    def active(self) -> int:
        return sum(self.in_hand)

    @property
    def total_pot(self) -> int:
        return self.pot + sum(self.bets)

    @property
    def my_stack(self) -> int:
        return self.stacks[self.seat]

    @property
    def big_blind(self) -> int:
        return self.blinds[1]

    @property
    def stack_bb(self) -> float:
        return (self.my_stack + self.bets[self.seat]) / self.blinds[1]

    def position(self, seat: int | None = None) -> int:
        """0 = first to act postflop (left of button) ... n-1 = button."""
        seat = self.seat if seat is None else seat
        return (seat - self.button - 1) % self.n_players

    def seats_after_me(self) -> int:
        """Players still in the hand who act after me postflop (0 = I am last)."""
        me = self.position()
        return sum(1 for s in range(self.n_players) if self.in_hand[s] and self.position(s) > me)


@dataclass
class HandResult:
    hand_no: int
    deltas: list[int]  # chip change per seat
    showdown: dict[int, tuple[int, ...]]  # seat -> revealed hole cards, if shown
    board: tuple[int, ...]
    history: list[tuple[int, Action]]
    # what a variant reports at hand end beyond the above (folded hands shown, a side game's showdown, per-pot
    # winners); empty in standard hold'em, so every bot that ignores it keeps working
    extras: dict = field(default_factory=dict)


class Bot(Protocol):
    def new_table(self, rules: Rules, seat: int, n_players: int) -> None: ...

    def act(self, obs: Observation) -> Action: ...

    def hand_end(self, result: HandResult) -> None: ...


def card_str(c: int) -> str:
    return RANKS[c >> 2] + SUITS[c & 3]


def cards_str(cs: Sequence[int]) -> str:
    return " ".join(card_str(c) for c in cs)


def parse_card(s: str) -> int:
    return RANKS.index(s[0].upper()) * 4 + SUITS.index(s[1].lower())


def parse_cards(s: str) -> tuple[int, ...]:
    s = s.replace(",", " ").split()
    if len(s) == 1 and len(s[0]) % 2 == 0 and len(s[0]) > 2:
        s = [s[0][i : i + 2] for i in range(0, len(s[0]), 2)]
    return tuple(parse_card(x) for x in s)
