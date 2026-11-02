"""Fake event kit (kit_e_style): the protocol, as the organisers' kit module would ship it. Standard library only.

The bot is `class Agent` in `agent.py`, one fresh module and one Agent() per table. It is never sent a state: it
is called once per event and asked for a move with only the legal options, so it keeps the pot, the stacks and the
action log itself. Every call (events included) has 1 ms of wall clock; past 1.05 ms the runner interrupts it (a
BaseException raised inside the call) and counts a timeout. Setup (import + Agent() + on_table) has 1 s per table.

Events (payloads are fresh dicts; seat keys in the chip maps are strings, as JSON would send them):
  on_table({"seat", "players", "stack", "hands", "budget_ms", "setup_ms", "payouts"})
  on_hand({"hand": 1-based, "button", "blinds": [sb, bb], "chips": {"0": chips before posting, ...},
           "posted": [{"seat", "paid", "ante": bool}], "cards": ["Ah", "Td"]})
  on_board({"board": ["Ah", "Td", "2c", ...]})              the whole board so far
  on_action({"seat", "move": "fold" | "check" | "call" | "raise", "to": street total after it, "paid": chips})
                                                            every action, yours included
  on_reveal({"hands": {"3": ["Ks", "Kd"], ...}})           only when two or more hands reach a showdown
  on_result({"hand", "net": {"0": chip change, ...}, "chips": {"0": chips after, ...}})
  decide({"hand", "board_size", "moves": {"fold": {}, "check": {}, "call": {"cost": c},
          "raise": {"min": total, "max": total}}}) -> {"move": "...", "to": street total for a raise}
Cards are rank + suit: "2".."9", "T", "J", "Q", "K", "A" and "c" "d" "h" "s". A raise's `to` is a raise-TO street total
and must be an int inside [min, max]; a move not offered, or garbage, is illegal and played as check-else-fold.
"""
from __future__ import annotations

RANKS = "23456789TJQKA"
SUITS = "cdhs"
EVENTS = ("on_table", "on_hand", "on_board", "on_action", "on_reveal", "on_result")
BUDGET_MS = 1.0
SETUP_MS = 1000.0


def card(c: int) -> str:
    return RANKS[c >> 2] + SUITS[c & 3]


def request(st: dict, hand: int) -> dict:
    """The decide() request for the dealer state `st` (the shared dealer's dict)."""
    moves: dict = {}
    legal = st["legal"]
    if "fold" in legal:
        moves["fold"] = {}
    if "check" in legal:
        moves["check"] = {}
    if "call" in legal:
        moves["call"] = {"cost": int(st["to_call"])}
    if "raise" in legal:
        moves["raise"] = {"min": int(st["min_raise"]), "max": int(st["max_raise"])}
    return {"hand": hand, "board_size": len(st["board"]), "moves": moves}


def parse_reply(reply, st: dict) -> tuple[str, int]:
    """The reply as the dealer's (kind, raise-to total); ValueError when it is not a legal move."""
    if not isinstance(reply, dict) or reply.get("move") not in st["legal"]:
        raise ValueError(f"not a legal move: {reply!r}")
    mv = reply["move"]
    if mv == "raise":
        to = reply.get("to")
        if type(to) is not int or not st["min_raise"] <= to <= st["max_raise"]:
            raise ValueError(f"raise to {to!r} outside [{st['min_raise']}, {st['max_raise']}]")
        return "raise", to
    return mv, 0
