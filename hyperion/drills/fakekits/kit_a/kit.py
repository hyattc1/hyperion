"""Fake starter kit A: class-based. Subclass Agent and implement act(state) -> Action.

Action is a plain string: "FOLD", "CHECK", "CALL" or "RAISE:<total chips this street>".
Cards are strings like "Ah", "10d" (ten is written as 10, not T).
"""
from __future__ import annotations

from dataclasses import dataclass, field

Action = str
STREETS = ("preflop", "flop", "turn", "river")
_RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
_SUITS = "cdhs"


def card_name(c: int) -> str:
    return _RANKS[c >> 2] + _SUITS[c & 3]


@dataclass
class PlayerInfo:
    name: str
    stack: int  # chips behind
    bet: int  # chips put in this street
    folded: bool
    all_in: bool


@dataclass
class GameState:
    hand: list[str]  # your hole cards
    community: list[str]  # board cards
    street: str  # "preflop" | "flop" | "turn" | "river"
    my_index: int  # index into players
    dealer_index: int
    players: list[PlayerInfo]
    my_stack: int  # chips behind
    pot_size: int  # everything in the middle INCLUDING this street's bets
    current_bet: int  # highest bet this street (you must match it to stay in)
    my_bet: int  # what you have put in this street
    legal_moves: list[str]  # subset of ["FOLD", "CHECK", "CALL", "RAISE"]
    min_raise: int  # smallest legal RAISE total
    max_raise: int  # largest legal RAISE total (all-in)
    hand_number: int
    small_blind: int
    big_blind: int
    action_log: list[tuple[int, str]] = field(default_factory=list)  # (player index, "CALL"/"RAISE:120"/...)


class Agent:
    """Implement act. new_game is called once per table with your index and the number of players."""

    def new_game(self, my_index: int, n_players: int, starting_stack: int) -> None:
        pass

    def act(self, state: GameState) -> Action:
        raise NotImplementedError

    def hand_over(self, hand_number: int, chip_change: int) -> None:
        pass


def to_state(st: dict) -> GameState:
    """Internal dealer state -> kit-native GameState."""
    n = len(st["stacks"])
    players = [
        PlayerInfo(name=f"player{i}", stack=st["stacks"][i], bet=st["bets"][i], folded=not st["in_hand"][i],
                   all_in=st["in_hand"][i] and st["stacks"][i] == 0)
        for i in range(n)
    ]
    legal = [m for m in ("FOLD", "CHECK", "CALL", "RAISE") if m.lower() in st["legal"]]
    log = [(s, k.upper() if k != "raise" else f"RAISE:{t}") for s, k, t in st["history"]]
    return GameState(
        hand=[card_name(c) for c in st["hole"]],
        community=[card_name(c) for c in st["board"]],
        street=STREETS[st["street"]],
        my_index=st["seat"],
        dealer_index=st["button"],
        players=players,
        my_stack=st["stacks"][st["seat"]],
        pot_size=st["pot"] + sum(st["bets"]),
        current_bet=max(st["bets"]),
        my_bet=st["bets"][st["seat"]],
        legal_moves=legal,
        min_raise=st["min_raise"],
        max_raise=st["max_raise"],
        hand_number=st["hand_no"],
        small_blind=st["blinds"][0],
        big_blind=st["blinds"][1],
        action_log=log,
    )


def parse_action(a: Action) -> tuple[str, int]:
    """Kit-native action string -> (kind, total). Raises ValueError on garbage."""
    if not isinstance(a, str):
        raise ValueError(f"action must be a str, got {type(a).__name__}")
    a = a.strip().upper()
    if a in ("FOLD", "CHECK", "CALL"):
        return a.lower(), 0
    if a.startswith("RAISE:") and a[6:].isdigit():
        return "raise", int(a[6:])
    raise ValueError(f"bad action {a!r}")
