"""Tonight's adapter: River of Blood kit (event-driven `Player`, no state snapshot).

The kit sends events (take_seat, start_hand, see_cards, see_action, see_showdown, end_hand) and asks
`choose(request)` with only the legal options. `submission/player.py` tracks the hand from the events and hands
this adapter a snapshot dict (`native`) at each decision. Amounts are street totals (raise-to), cards "Ah"/"Td".

River of Blood: streets are board lengths 0/3/4/5 then 6, 7, ... while the last card is red. Our engine has
4 streets. On a run street (board > 5) the bot sees a river: street 3, a 5-card sub-board chosen so that our
best hand from hole + sub-board equals our best hand from hole + the whole board (ties: the strongest board),
pot = every chip before this street, bets = this street, history = the whole hand's log (run streets' actions
follow the river's).
"""
from __future__ import annotations

from itertools import combinations
from typing import Any

from hyperion.core.eval import evaluate
from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_card  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation  # noqa: F401
from hyperion.drills.conformance import maybe_checked

_CARD = {r + s: i * 4 + j for i, r in enumerate("23456789TJQKA") for j, s in enumerate("cdhs")}
_KINDS = {"fold": ActionKind.FOLD, "check": ActionKind.CHECK, "call": ActionKind.CALL, "raise": ActionKind.RAISE}
STREET_BY_BOARD = {0: 0, 3: 1, 4: 2, 5: 3}
RUN_POOL = 9  # board cards searched on a run street (C(9,5) = 126 sub-boards, about 110 us)


def card(native_card: Any) -> int:
    return _CARD[str(native_card)]


def history(log) -> list[tuple[int, Action]]:
    """[(seat, street, move, amount)] -> [(seat, Action)], raise as the raise-TO street total."""
    out: list[tuple[int, Action]] = []
    for item in log or ():
        try:
            seat, _street, move, amount = item
            kind = _KINDS.get(move)
            if kind is None:
                continue
            out.append((int(seat), Action(kind, int(amount) if kind is ActionKind.RAISE else 0)))
        except Exception:  # noqa: BLE001
            continue
    return out


def river_view(hole: list[int], board: list[int]) -> list[int]:
    """A 5-card sub-board (in board order) on which our best hand is the same as on the whole board."""
    pool = board if len(board) <= RUN_POOL else board[:0] + board[-RUN_POOL:]
    best_key, best = None, None
    for sub in combinations(pool, 5):
        sl = list(sub)
        key = (evaluate(hole + sl), evaluate(sl))
        if best_key is None or key > best_key:
            best_key, best = key, sl
    return best


def bot_log(log, street: int) -> list:
    """The log the bot sees: the whole hand, run streets included (a kit log only grows: conformance
    history_prefix). Minute 9 version kept only the current run street; it broke history_prefix, reverted."""
    return log


class TonightAdapter(Adapter):
    """River of Blood kit: snapshot dict built by player.py from the events; options list exact legal moves."""

    history_source = "log"

    def to_observation(self, n: Any) -> Observation:
        seats = n["n"]
        street_k = n["street"]
        kboard = [card(c) for c in n["board"]]
        hole = [card(c) for c in n["hole"]]
        if street_k > 5:
            board = river_view(hole, kboard)
            street = 3
        else:
            board = kboard
            street = STREET_BY_BOARD[street_k]
        stacks = [int(n["stacks"].get(s, 0)) for s in range(seats)]
        bets = [int(n["bets"].get(s, 0)) for s in range(seats)]
        in_hand = [s in n["in_hand"] for s in range(seats)]
        opts = n["options"]
        legal = [o for o in ("fold", "check", "call", "raise") if o in opts]
        to_call = int(opts["call"]["cost"]) if "call" in opts else 0
        if "raise" in opts:
            mn, mx = int(opts["raise"]["min"]), int(opts["raise"]["max"])
        else:
            mn = mx = 0
        pot = int(n["pot"]) - sum(bets)
        return make_observation(
            hole=hole, board=board, street=street, seat=n["seat"], button=n["button"],
            stacks=stacks, bets=bets, in_hand=in_hand, pot=pot, to_call=to_call,
            min_raise=mn, max_raise=mx, legal=legal, hand_no=int(n["hand"]) - 1,
            blinds=(int(n["sb"]), int(n["bb"])), history=history(bot_log(n["log"], street_k)),
        )

    def from_action(self, a: Action, obs: Observation, n: Any) -> Any:
        opts = n["options"]
        k = a.kind.value
        if k == "raise" and "raise" in opts:
            r = opts["raise"]
            amt = int(a.amount)
            if amt < int(r["min"]):
                amt = int(r["min"])
            if amt > int(r["max"]):
                amt = int(r["max"])
            return {"move": "raise", "amount": amt}
        if k in opts and k != "raise":
            return {"move": k}
        return self.native_safe(n)

    def native_safe(self, n: Any) -> Any:
        try:
            opts = n["options"]
            if "check" in opts:
                return {"move": "check"}
            return {"move": "fold"}
        except Exception:  # noqa: BLE001
            return {"move": "fold"}


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    """What the entry point calls. HYPERION_CHECK=1 turns the conformance report on; nothing else changes."""
    return maybe_checked(TonightAdapter(bot, rules))
