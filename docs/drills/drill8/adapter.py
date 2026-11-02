"""Tonight's adapter: Ghost Hold'em kit (K/README.md section 5).

Native state `s`: attributes hand_no, street (0-3), hole (int,int), board (ints), stack, owe, min_raise (chips put
in NOW for the smallest raise; 0 = cannot raise; == stack when all-in is the only raise), pot (ALL chips incl. this
street's bets and the Haunt), haunt, sb, bb, button (relative), stacks[8], bets[8] (this street), status (str8:
A in hand, X all-in, F folded, - out), log (full action log, relative seats). Seat 0 is always us.
Reply: one int, the chips put in now (n < owe fold/check, owe <= n < min_raise call, n >= min_raise raise).
Cards are already ours: rank*4 + suit, 2=0 .. A=12, c d h s = 0..3.
"""
from __future__ import annotations

from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked

_KIND = {"f": ActionKind.FOLD, "k": ActionKind.CHECK, "c": ActionKind.CALL, "r": ActionKind.RAISE}


def card(native_card: Any) -> int:
    return int(native_card)


def history(log: Any) -> list[tuple[int, Action]]:
    """s.log -> [(seat, Action)]; raises as raise-TO totals for the street; blind posts skipped."""
    out: list[tuple[int, Action]] = []
    street = [0] * 8
    for tok in str(log or "").split():
        try:
            if tok == "/":
                street = [0] * 8
                continue
            seat = int(tok[0])
            code = tok[1]
            n = int(tok[2:].rstrip("!")) if len(tok) > 2 else 0
            if code in ("s", "b"):
                street[seat] += n
                continue
            kind = _KIND.get(code)
            if kind is None:
                continue
            if kind is ActionKind.RAISE:
                street[seat] += n
                out.append((seat, Action(kind, street[seat])))
            elif kind is ActionKind.CALL:
                street[seat] += n
                out.append((seat, Action(kind, 0)))
            else:
                out.append((seat, Action(kind, 0)))
        except Exception:  # noqa: BLE001 - a malformed token costs one history line
            continue
    return out


class TonightAdapter(Adapter):
    """Ghost Hold'em kit: attribute state, relative seats (we are 0), int reply = chips put in now."""

    history_source = "log"

    def to_observation(self, s: Any) -> Observation:
        stacks = [int(x) for x in s.stacks]
        bets = [int(x) for x in s.bets]
        status = str(s.status)
        owe = int(s.owe)
        mr = int(s.min_raise)
        legal = ["fold", "call"] if owe > 0 else ["check"]
        if mr > 0:
            legal.append("raise")
            lo, hi = mr + bets[0], int(s.stack) + bets[0]
        else:
            lo = hi = None
        return make_observation(
            hole=[card(c) for c in s.hole], board=[card(c) for c in s.board], street=int(s.street), seat=0,
            button=int(s.button), stacks=stacks, bets=bets, in_hand=[ch in "AX" for ch in status],
            pot=int(s.pot) - sum(bets), to_call=owe, min_raise=lo, max_raise=hi, legal=legal,
            hand_no=int(s.hand_no), blinds=(int(s.sb), int(s.bb)), history=history(s.log),
        )

    def from_action(self, action: Action, obs: Observation, s: Any) -> Any:
        owe = int(s.owe)
        if action.kind is ActionKind.RAISE:
            mr = int(s.min_raise)
            if mr <= 0:
                return owe
            n = int(action.amount) - int(s.bets[0])
            return max(mr, min(n, int(s.stack)))
        if action.kind is ActionKind.CALL:
            return owe
        return 0  # fold, or check when owe == 0

    def native_safe(self, s: Any) -> Any:
        return 0  # the dealer reads 0 as check when free, else fold


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    return maybe_checked(TonightAdapter(bot, rules))
