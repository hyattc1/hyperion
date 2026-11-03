"""Chain Hold'em kit adapter: kit `s` (offsets from me, me = 0; pot includes this street; token actions)
-> Observation; our Action (raise-TO total) -> one of the kit's tokens, priced with s.cost()."""
from __future__ import annotations

from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked

TOKENS = ("R33", "R50", "R75", "R100", "R150", "R250")


def card(c: Any) -> int:
    return int(c)  # kit ints are rank*4 + suit, rank 0 = deuce, suits c d h s: ours exactly


def history(log: str) -> list[tuple[int, Action]]:
    """'5s10,6b20,7f,0r45,...' / per street -> [(offset, Action)]; raises as raise-TO totals; blinds skipped."""
    out: list[tuple[int, Action]] = []
    if not log:
        return out
    for street_txt in str(log).split("/"):
        put: dict = {}
        for tok in street_txt.split(","):
            try:
                if len(tok) < 2:
                    continue
                seat = int(tok[0])
                code = tok[1]
                n = int(tok[2:]) if len(tok) > 2 else 0
                if code in "sb":
                    put[seat] = put.get(seat, 0) + n
                elif code == "f":
                    out.append((seat, Action(ActionKind.FOLD)))
                elif code == "k":
                    out.append((seat, Action(ActionKind.CHECK)))
                elif code == "c":
                    put[seat] = put.get(seat, 0) + n
                    out.append((seat, Action(ActionKind.CALL)))
                elif code == "r":
                    put[seat] = put.get(seat, 0) + n
                    out.append((seat, Action(ActionKind.RAISE, put[seat])))
            except Exception:  # noqa: BLE001
                continue
    return out


class TonightAdapter(Adapter):
    """Chain Hold'em kit: state object s with offsets (me = 0), status string, pot incl. this street, token actions."""

    history_source = "log"

    def to_observation(self, s: Any) -> Observation:
        stacks = [int(x) for x in s.stacks]
        bets = [int(x) for x in s.bets]
        status = str(s.status)
        in_hand = [ch in "AL" for ch in status]
        legal = []
        to_call = int(s.to_call)
        if to_call > 0:
            legal += ["fold", "call"]
        else:
            legal += ["check"]
        my_total = stacks[0] + bets[0]
        lo = hi = None
        if s.can_raise and stacks[0] > to_call:
            legal.append("raise")
            hi = my_total
            lo = min(max(bets) + int(s.min_raise_by), hi)
        board = tuple(card(c) for c in s.board)
        return make_observation(
            hole=(card(s.card), card(s.left), card(s.right)), board=board,
            street=int(s.street), seat=0, button=int(s.button),
            stacks=stacks, bets=bets, in_hand=in_hand, pot=int(s.pot) - sum(bets), to_call=to_call,
            min_raise=lo, max_raise=hi, legal=legal, hand_no=int(s.hand), blinds=(int(s.sb), int(s.bb)),
            history=history(s.log),
        )

    def from_action(self, a: Action, obs: Observation, s: Any) -> str:
        k = a.kind
        if k is ActionKind.FOLD:
            return "F" if int(s.to_call) > 0 else "C"
        if k is ActionKind.CHECK or k is ActionKind.CALL:
            return "C"
        if k is ActionKind.RAISE:
            if not s.can_raise:
                return "C"
            want = int(a.amount) - int(s.bets[0])
            if want >= int(s.stacks[0]):
                return "A"
            best, gap = "R33", None
            for t in TOKENS + ("A",):
                try:
                    c = int(s.cost(t))
                except Exception:  # noqa: BLE001
                    continue
                g = abs(c - want)
                if gap is None or g < gap:
                    best, gap = t, g
            return best
        return "C"

    def native_safe(self, s: Any) -> str:
        return "C" if getattr(s, "to_call", 1) == 0 else "F"


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    return maybe_checked(TonightAdapter(bot, rules))
