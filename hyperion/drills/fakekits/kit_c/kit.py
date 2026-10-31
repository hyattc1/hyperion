"""Fake starter kit C: a line protocol over stdin/stdout, in the spirit of the classic pokerbot engines.

Every message is one line of space-separated clauses; the first character of a clause is its key.
The engine writes to your stdin, you write ONE line to stdout only when the message has an L clause.

  T4 P0 Z2000 V10/20                 table start: players, your seat, stack, blinds
      -> reply  OK                   within 10 s; your imports and warm-up happen before this
  H3 D1 S1 KAs,Td BQh,7d,2c C1980,0,1500,2000 E0,0,20,40 I1011 O60 LF,C,R80-1980 V10/20 T950.2
                                     decision: hand no, dealer seat, street 0..3, your cards,
                                     board (B- when empty), stacks, bets this street, in-hand flags,
                                     pot from previous streets, legal actions, blinds, clock ms left
      -> reply  F | K | C | R<raise-to total>      (fold, check, call, raise)
  X3 W-40                            hand over: hand no, your chip change (no reply)
  Q                                  quit: exit cleanly (no reply)

Only the T line and L lines get a reply. Cards are two characters, rank in 23456789TJQKA and suit
in cdhs. Amounts are raise-to totals.
The clock is a pooled game clock (MIT style): 1 ms per expected decision for the whole table; wall
time of each round trip is subtracted and once it is negative every action is a fold.
"""
from __future__ import annotations

RANKS = "23456789TJQKA"
SUITS = "cdhs"


def card_code(c: int) -> str:
    return RANKS[c >> 2] + SUITS[c & 3]


def encode_decision(st: dict, clock_ms: float) -> str:
    legal = []
    if "fold" in st["legal"]:
        legal.append("F")
    if "check" in st["legal"]:
        legal.append("K")
    if "call" in st["legal"]:
        legal.append("C")
    if "raise" in st["legal"]:
        legal.append(f"R{st['min_raise']}-{st['max_raise']}")
    board = ",".join(card_code(c) for c in st["board"]) or "-"
    return " ".join([
        f"H{st['hand_no']}", f"D{st['button']}", f"S{st['street']}",
        "K" + ",".join(card_code(c) for c in st["hole"]), "B" + board,
        "C" + ",".join(map(str, st["stacks"])), "E" + ",".join(map(str, st["bets"])),
        "I" + "".join("1" if x else "0" for x in st["in_hand"]), f"O{st['pot']}",
        "L" + ",".join(legal), f"V{st['blinds'][0]}/{st['blinds'][1]}", f"T{clock_ms:.1f}",
    ])


def encode_table_start(n_players: int, seat: int, stack: int, blinds: tuple[int, int]) -> str:
    return f"T{n_players} P{seat} Z{stack} V{blinds[0]}/{blinds[1]}"


def encode_hand_end(hand_no: int, delta: int) -> str:
    return f"X{hand_no} W{delta}"


def parse_reply(line: str) -> tuple[str, int]:
    """'F' | 'K' | 'C' | 'R<total>' -> (kind, total). Raises ValueError on garbage."""
    s = line.strip()
    if s == "F":
        return "fold", 0
    if s == "K":
        return "check", 0
    if s == "C":
        return "call", 0
    if s.startswith("R") and s[1:].isdigit():
        return "raise", int(s[1:])
    raise ValueError(f"bad reply {line!r}")
