"""Tonight's adapter: Solo Hold'em kit (JSON lines over stdin/stdout, one process per session).

Native state = the kit's `act` message dict plus the table's seat map (handles clockwise, from `table`).
Cards are already ours (4*rank+suit, deuce 0, c d h s). pot includes this street's bets. min_r / max_r and the
reply's N are RAISE-BY (over the bet to match): total = my bet + to_call + N. Full log -> history_source "log".
"""
from __future__ import annotations

from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked

_KIND = {"f": ActionKind.FOLD, "k": ActionKind.CHECK, "c": ActionKind.CALL}


def card(native_card: Any) -> int:
    return int(native_card)


def history(log: str, idx: dict, bb: int) -> list[tuple[int, Action]]:
    """'h:f h:r40 h:c/h:k ...' -> [(seat, Action)] with raise-TO totals per street. Unreadable entries skipped."""
    out: list[tuple[int, Action]] = []
    if not log:
        return out
    for street, part in enumerate(log.split("/")):
        top = bb if street == 0 else 0
        for tok in part.split():
            try:
                h, _, a = tok.rpartition(":")
                seat = idx[h]
                if a and a[0] == "r":
                    top += int(a[1:])
                    out.append((seat, Action(ActionKind.RAISE, top)))
                else:
                    kind = _KIND.get(a)
                    if kind is not None:
                        out.append((seat, Action(kind, 0)))
            except Exception:  # noqa: BLE001
                continue
    return out


class TonightAdapter(Adapter):
    """Solo kit: act dict {cards, board, pot (incl. street), to_call, min_r/max_r raise-by, players in position
    order, log}. Replies "f" / "c" / "r<N>" (N raise-by)."""

    history_source = "log"

    def __init__(self, bot, rules=None):
        super().__init__(bot, rules)
        self.idx: dict = {}
        self.n = 8

    def set_table(self, seats: list) -> None:
        self.idx = {h: i for i, h in enumerate(seats)}
        self.n = len(seats)

    def to_observation(self, m: Any) -> Observation:
        idx, n = self.idx, self.n
        stacks, bets, in_hand = [0] * n, [0] * n, [False] * n
        for p in m["players"]:
            i = idx[p["h"]]
            stacks[i] = int(p["stack"])
            bets[i] = int(p["bet"])
            in_hand[i] = p["state"] != "folded"
        seat = idx[m["you"]]
        board = [int(c) for c in m["board"]]
        to_call = min(int(m["to_call"]), stacks[seat])  # the kit's to_call is not capped by my stack
        legal = ["fold", "call"] if to_call > 0 else ["check"]
        lo = hi = None
        max_r = int(m.get("max_r") or 0)
        if max_r > 0:
            legal.append("raise")
            base = bets[seat] + int(m["to_call"])
            lo = base + int(m.get("min_r") or 0)
            hi = base + max_r
        bb = int(m["bb"])
        return make_observation(
            hole=[int(c) for c in m["cards"]], board=board, street={0: 0, 3: 1, 4: 2, 5: 3}[len(board)],
            seat=seat, button=idx[m["button"]], stacks=stacks, bets=bets, in_hand=in_hand,
            pot=int(m["pot"]) - sum(bets), to_call=to_call, min_raise=lo, max_raise=hi, legal=legal,
            hand_no=int(m["hand"]), blinds=(int(m["sb"]), bb), history=history(m.get("log", ""), idx, bb),
        )

    def from_action(self, a: Action, obs: Observation, m: Any) -> str:
        if a.kind is ActionKind.RAISE and int(m.get("max_r") or 0) > 0:
            n = int(a.amount) - obs.bets[obs.seat] - int(m["to_call"])
            return "r%d" % max(int(m.get("min_r") or 1), n, 1)
        if a.kind is ActionKind.CALL or a.kind is ActionKind.CHECK or a.kind is ActionKind.RAISE:
            return "c"
        return "f" if obs.to_call > 0 else "c"

    def native_safe(self, m: Any) -> str:
        try:
            return "c" if int(m["to_call"]) == 0 else "f"
        except Exception:  # noqa: BLE001
            return "f"  # a fold with nothing to call is a check (kit README 2)


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    return maybe_checked(TonightAdapter(bot, rules))
