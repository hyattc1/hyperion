"""Fake starter kit B: function-based. Your module defines decide(observation: dict) -> dict.

observation (JSON-serializable):
  {
    "hand_id": 17,
    "street": 0 | 3 | 4 | 5,                      # number of board cards, MIT style
    "blinds": {"sb": 10, "bb": 20},
    "hand": {"cards": [{"rank": 14, "suit": "H"}, {"rank": 10, "suit": "D"}]},   # rank 2..14
    "table": {
      "board": [ {rank, suit}, ... ],
      "pot": 60,                                   # chips from previous streets only
      "button": 3,
      "players": [ {"seat": 0, "chips": 1980, "committed": 20, "active": true}, ... ]
    },
    "you": {"seat": 0, "to_call": 20, "min_raise_by": 20, "max_raise_by": 1960},
    "actions": ["fold", "call", "raise"]
  }
return: {"action": "fold" | "check" | "call"} or {"action": "raise", "by": <increment above the
current highest bet>}. "by" is NOT a raise-to total: raise-to = max(committed) + by.
Optional: on_table_start(info: dict) and on_hand_end(info: dict) in the same module.
"""
from __future__ import annotations

SUITS = "CDHS"


def card_obj(c: int) -> dict:
    return {"rank": (c >> 2) + 2, "suit": SUITS[c & 3]}


def to_observation(st: dict) -> dict:
    n = len(st["stacks"])
    current = max(st["bets"])
    return {
        "hand_id": st["hand_no"],
        "street": len(st["board"]),
        "blinds": {"sb": st["blinds"][0], "bb": st["blinds"][1]},
        "hand": {"cards": [card_obj(c) for c in st["hole"]]},
        "table": {
            "board": [card_obj(c) for c in st["board"]],
            "pot": st["pot"],
            "button": st["button"],
            "players": [
                {"seat": i, "chips": st["stacks"][i], "committed": st["bets"][i], "active": st["in_hand"][i]}
                for i in range(n)
            ],
        },
        "you": {
            "seat": st["seat"],
            "to_call": st["to_call"],
            "min_raise_by": st["min_raise"] - current,
            "max_raise_by": st["max_raise"] - current,
        },
        "actions": [k for k in ("fold", "check", "call", "raise") if k in st["legal"]],
    }


def parse_decision(d: dict, st: dict) -> tuple[str, int]:
    """Kit-native decision -> (kind, raise-to total). Raises on garbage."""
    if not isinstance(d, dict) or "action" not in d:
        raise ValueError(f"decision must be a dict with 'action', got {d!r}")
    kind = str(d["action"]).lower()
    if kind == "raise":
        return "raise", max(st["bets"]) + int(d["by"])
    if kind in ("fold", "check", "call"):
        return kind, 0
    raise ValueError(f"bad action {kind!r}")
