"""Fake kit S: one decision dict whose shape is set by a quirk, for checking an adapter against every kit shape (R3).

Each SHAPE changes one thing a real kit may do differently from the dealer state (hyperion/drills/fakekits/_table.py's
dict, which tools/gate.py sends). The dict names its quirk in `rules`, as a rule sheet would; everything else is the
plain shape:

    {"rules": {"shape": NAME, "amounts": "to" | "by" | "put_in", "seat_base": 0 | 1, "seats": "table" | "me",
               "log": "full" | "own" | "last3" | "none"},
     "hand": hand_no, "button": label, "me": label, "blinds": [sb, bb], "pot": chips of earlier streets,
     "players": [{"seat": label, "stack": chips behind, "bet": this street, "in": bool}] (in seat order),
     "to_call": chips, "min": amount, "max": amount, "legal": [...], "hole": [card], "board": [card],
     "log": [{"seat": label, "act": word, "to": raise-to total (raises only)}]}

Reply {"act": word, "amount": n}: `amount` in the shape's convention (raise-to, by over the top bet, or the chips put
in now). Log amounts are always raise-to totals. No hyperion import (the kits' rule).

`Seat` is the class tools/gate.py's seat files subclass (`SHAPE = NAME`); the entry defines `Agent`
(hyperion.drills.adapter.KitSAgent) with new_table(info), act(native) and hand_over(hand_no, delta).
"""
from __future__ import annotations

RANKS = "23456789TJQKA"
SUITS = "cdhs"
UNICODE = "♣♦♥♠"  # clubs diamonds hearts spades

SHAPES = {
    "base": "the plain shape: raise-to amounts, seats 0..n-1, our names, the full log, cards 'Th'",
    "raise_by": "min / max and the reply's amount are increments over the current top bet",
    "put_in": "min / max and the reply's amount are the chips put in by this action (total - my bet)",
    "log_own": "the log holds only our own actions",
    "log_last3": "the log holds only the last three actions of the hand",
    "log_none": "no log at all",
    "posts": "the log starts with the blinds posted, as bets of 10 and 20",
    "bounds_swapped": "min and max are swapped",
    "bounds_missing": "no min or max: derive them",
    "allin_short": "short of a full raise, min is the full raise (above my stack) and max my all-in",
    "seats_from_1": "seats are numbered 1..n",
    "seats_me": "seats are numbered from us: we are 0, the next seat clockwise 1",
    "cards_ten": "cards '10h', 'Ah'",
    "cards_lower": "cards 'th', 'ah'",
    "cards_unicode": "cards 'T♥', 'A♠'",
    "cards_suit_first": "cards 'hT', 'sA'",
    "legal_upper": "legal moves 'FOLD', 'CALL', 'RAISE'",
    "legal_dicts": "legal moves as dicts {'type': 'raise', 'min': .., 'max': ..}",
    "legal_string": "legal moves one string 'fold,call,raise'",
    "legal_words": "'bet' when nobody has bet this street, and 'all-in' for a raise that is only the all-in; the reply "
                   "must use the same word",
}


def card(c: int, shape: str) -> str:
    r, s = RANKS[c >> 2], SUITS[c & 3]
    if shape == "cards_ten":
        return ("10" if r == "T" else r) + s
    if shape == "cards_lower":
        return r.lower() + s
    if shape == "cards_unicode":
        return r + UNICODE[c & 3]
    if shape == "cards_suit_first":
        return s + r
    return r + s


def _label(s: int, st: dict, shape: str) -> int:
    n = len(st["stacks"])
    if shape == "seats_from_1":
        return s + 1
    if shape == "seats_me":
        return (s - st["seat"]) % n
    return s


def _amount(total: int, st: dict, shape: str) -> int:
    """A raise-to total in the shape's convention."""
    if shape == "raise_by":
        return total - max(st["bets"])
    if shape == "put_in":
        return total - st["bets"][st["seat"]]
    return total


def _total(amount: int, st: dict, shape: str) -> int:
    if shape == "raise_by":
        return amount + max(st["bets"])
    if shape == "put_in":
        return amount + st["bets"][st["seat"]]
    return amount


def _raise_word(st: dict, shape: str) -> str:
    if shape != "legal_words":
        return "raise"
    if st["min_raise"] >= st["max_raise"]:
        return "all-in"
    return "bet" if max(st["bets"]) == 0 else "raise"


def to_native(st: dict, shape: str) -> dict:
    n, me = len(st["stacks"]), st["seat"]
    order = sorted(range(n), key=lambda s: _label(s, st, shape))
    players = [{"seat": _label(s, st, shape), "stack": st["stacks"][s], "bet": st["bets"][s],
                "in": bool(st["in_hand"][s])} for s in order]
    log_kind = {"log_own": "own", "log_last3": "last3", "log_none": "none"}.get(shape, "full")
    rows = [r for r in st.get("history", ()) if r[1] in ("fold", "check", "call", "raise")]
    if log_kind == "own":
        rows = [r for r in rows if r[0] == me]
    elif log_kind == "last3":
        rows = rows[-3:]
    log = [{"seat": _label(s, st, shape), "act": k, **({"to": int(t)} if k == "raise" else {})} for s, k, t in rows]
    if shape == "posts":  # the hand's log starts with the forced bets, on every street
        sb_seat, bb_seat = _blind_seats(st)
        if sb_seat is not None:
            pre = [{"seat": _label(sb_seat, st, shape), "act": "bet", "to": st["blinds"][0]},
                   {"seat": _label(bb_seat, st, shape), "act": "bet", "to": st["blinds"][1]}]
            log = pre + log
    rw = _raise_word(st, shape)
    names = [rw if k == "raise" else k for k in sorted(st["legal"])]
    lo, hi = st["min_raise"], st["max_raise"]
    if shape == "allin_short" and "raise" in st["legal"] and lo >= hi:
        lo = hi + st["blinds"][1]  # the full raise, above what I have
    if shape == "legal_upper":
        legal = [x.upper() for x in names]
    elif shape == "legal_dicts":
        legal = [{"type": x, **({"min": _amount(lo, st, shape), "max": _amount(hi, st, shape)} if x == rw else {})}
                 for x in names]
    elif shape == "legal_string":
        legal = ",".join(names)
    else:
        legal = names
    out = {
        "rules": {"shape": shape, "amounts": {"raise_by": "by", "put_in": "put_in"}.get(shape, "to"),
                  "seat_base": 1 if shape == "seats_from_1" else 0, "seats": "me" if shape == "seats_me" else "table",
                  "log": log_kind},
        "hand": st["hand_no"], "button": _label(st["button"], st, shape), "me": _label(me, st, shape),
        "blinds": list(st["blinds"]), "pot": st["pot"], "players": players, "to_call": st["to_call"],
        "legal": legal, "hole": [card(c, shape) for c in st["hole"]], "board": [card(c, shape) for c in st["board"]],
    }
    if log_kind != "none":
        out["log"] = log
    if "raise" in st["legal"] and shape != "bounds_missing":
        a, b = _amount(lo, st, shape), _amount(hi, st, shape)
        out["min"], out["max"] = (b, a) if shape == "bounds_swapped" else (a, b)
    return out


def _blind_seats(st: dict):
    """The small and big blind seats of the hand (the dealer's rule: the next live seats after the button; heads-up
    the button posts the small blind). Live: chips behind, in the hand, or a bet."""
    n = len(st["stacks"])
    live = [s for s in range(n) if st["stacks"][s] > 0 or st["in_hand"][s] or st["bets"][s] > 0]
    if len(live) < 2:
        return None, None
    after = lambda s: next(x for x in [(s + k) % n for k in range(1, n + 1)] if x in live)  # noqa: E731
    sb = st["button"] if len(live) == 2 else after(st["button"])
    return sb, after(sb)


def parse_reply(reply, st: dict, shape: str) -> tuple[str, int]:
    """The bot's reply -> (kind, raise-to total) for the dealer; anything unreadable raises (an illegal action)."""
    word = str(reply["act"]).lower()
    rw = _raise_word(st, shape)
    if word in ("fold", "check", "call"):
        return word, 0
    if word != rw:
        raise ValueError(f"reply {word!r}: this kit's word for that raise is {rw!r}")
    if rw == "all-in":
        return "raise", st["max_raise"]
    return "raise", _total(int(reply["amount"]), st, shape)


class Seat:
    """tools/gate.py seat: `SHAPE` names the quirk; one Agent per table (the entry's class Agent)."""

    SHAPE = "base"

    def __init__(self, module, kit=None):
        self.mod, self.agent = module, None

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.agent = self.mod.Agent()
        label = {"seats_from_1": seat + 1, "seats_me": 0}.get(self.SHAPE, seat)
        self.agent.new_table({"seat": label, "players": n, "stack": stack, "blinds": list(blinds)})

    def native(self, st: dict):
        return to_native(st, self.SHAPE)

    def call(self, native):
        return self.agent.act(native)

    def parse(self, reply, st: dict):
        return parse_reply(reply, st, self.SHAPE)

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        self.agent.hand_over(hand_no, delta)
