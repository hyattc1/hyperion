"""Trailing Stop kit: v (namedtuple, amounts floats in bb of the level, cards bit masks, players clockwise from the small
blind with the eliminated missing, tags per table) <-> Observation (chips, fixed seats = index in table.tags)."""
from __future__ import annotations

import os
from typing import Any

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked

STREET_BOARD = (0, 3, 4, 5)
# kit bit = 13*suit + rank-2 -> ours rank*4 + suit
_CARD = tuple((i % 13) * 4 + i // 13 for i in range(52))


def cards(mask: int) -> tuple:
    out = []
    while mask:
        low = mask & -mask
        out.append(_CARD[low.bit_length() - 1])
        mask ^= low
    return tuple(out)


def history(log: str, bb: int, seat_of: dict) -> list:
    """The kit's log -> [(seat, Action)]: blinds dropped, R's raise-by turned into a raise-to total for the street."""
    out = []
    price = bb  # a short blind still sets the full price
    for tok in log.split():
        if tok == "/":
            price = 0
            continue
        try:
            verb = tok[2]
            if verb == "S" or verb == "B":
                continue
            seat = seat_of[tok[:2]]
            if verb == "F":
                out.append((seat, Action.fold()))
            elif verb == "K":
                out.append((seat, Action.check()))
            elif verb == "C":
                out.append((seat, Action.call()))
            elif verb == "R":
                price += int(float(tok[3:].rstrip("!")) * bb + 0.5)
                out.append((seat, Action.raise_to(price)))
        except (KeyError, IndexError, ValueError):
            continue
    return out


def _read_mode() -> str:
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "stop_patch.txt")) as f:
            return f.read().strip()
    except OSError:
        return ""


STOP_MODE = _read_mode()  # "" off; "A" past the stop, shove; letters add: B rooms always, L rooms under LOW_BB, X the same at a crossing only, D crossing call priced as the stack, R raises cut to the room
_FC = frozenset((ActionKind.FOLD, ActionKind.CALL))
LOW_BB = 6


class StopBot:
    """The twist in front of the bot, as one function of the observation (obs.extras["floors"]). Past the stop a fold is
    the end and the chips behind are worth nothing if we lose: all of them go in, the bot not asked. "B": the bot sees
    each seat's room (stack minus stop) as its stack, a depth it can lose; a call or raise past our room is a bet of
    everything and is played as one."""

    def __init__(self, bot: Any, mode: str):
        self.bot = bot
        self.mode = mode

    def __getattr__(self, name):
        return getattr(self.bot, name)

    def new_table(self, rules, seat, n):
        return self.bot.new_table(rules, seat, n)

    def hand_end(self, result):
        return self.bot.hand_end(result)

    def act(self, obs: Observation) -> Action:
        floors = obs.extras.get("floors")
        if floors is None:
            return self.bot.act(obs)
        me = obs.seat
        room = obs.stacks[me] - floors[me]
        if room < 0:
            if ActionKind.RAISE in obs.legal:
                return Action.raise_to(obs.max_raise)
            return Action.call() if obs.to_call > 0 else Action.check()
        mode = self.mode
        if "B" in mode or (room < LOW_BB * obs.blinds[1] and ("L" in mode or ("X" in mode and obs.to_call > room))):
            return self._lens(obs, floors, me, room)
        if "D" in mode and obs.to_call > room:
            return self._whole(obs, me)
        a = self.bot.act(obs)
        if "R" in mode and a.kind is ActionKind.RAISE and a.amount - obs.bets[me] > room and a.amount < obs.max_raise:
            cut = obs.bets[me] + room  # the most we can lose and still be here; under a legal raise, all of it
            return Action.raise_to(cut if cut >= obs.min_raise else obs.max_raise)
        return a

    def _whole(self, obs: Observation, me: int) -> Action:
        stack = obs.stacks[me]
        seen = Observation(obs.hole, obs.board, obs.street, me, obs.button, obs.stacks, obs.bets, obs.in_hand, obs.pot,
                           stack, 0, 0, _FC, obs.hand_no, obs.blinds, obs.history, obs.extras)
        a = self.bot.act(seen)
        if a.kind is ActionKind.CALL or a.kind is ActionKind.RAISE:
            return Action.raise_to(obs.max_raise) if ActionKind.RAISE in obs.legal else Action.call()
        return Action.fold()

    def _lens(self, obs: Observation, floors, me: int, room: int) -> Action:
        stacks = [s - f if s >= f else s for s, f in zip(obs.stacks, floors)]
        seen = room if room > 0 else 1
        stacks[me] = seen
        to_call = obs.to_call if obs.to_call < seen else seen
        left = seen - to_call
        real_raise = ActionKind.RAISE in obs.legal
        base = obs.bets[me] + to_call
        if left > 0 and real_raise:
            legal = obs.legal
            hi = base + left
            lo = obs.min_raise if obs.min_raise < hi else hi
        else:
            legal = _FC if to_call > 0 else obs.legal - {ActionKind.RAISE}
            hi = lo = 0
        seen_obs = Observation(obs.hole, obs.board, obs.street, me, obs.button, stacks, obs.bets, obs.in_hand, obs.pot,
                               to_call, lo, hi, legal, obs.hand_no, obs.blinds, obs.history, obs.extras)
        a = self.bot.act(seen_obs)
        k = a.kind
        if k is ActionKind.RAISE:
            if a.amount >= hi or a.amount - obs.bets[me] > room:  # past the room: everything
                return Action.raise_to(obs.max_raise) if real_raise else Action.call()
            return a
        if k is ActionKind.CALL and obs.to_call > room:  # the call crosses the stop: a bet of everything
            return Action.raise_to(obs.max_raise) if real_raise else a
        return a


class _NoInference:
    """The kit gives the full log: nothing to rebuild, so none of the rebuild's work on the 1 ms clock (about 10% of it)."""

    def new_table(self, rules) -> None:
        pass

    def acted(self, action) -> None:
        pass


class TonightAdapter(Adapter):
    history_source = "log"

    def __init__(self, bot: Any, rules: Rules | None = None):
        super().__init__(bot, rules)
        if "F" in STOP_MODE:
            self.inference = _NoInference()
            self.with_history = self._with_log
            self._end = self._end_log
        self.seat_of: dict = {}
        self.tags: tuple = ()
        self.n = 8
        self.start_stack: dict = {}

    def sit(self, tags, me) -> None:
        self.tags = tuple(tags)
        self.seat_of = {t: i for i, t in enumerate(self.tags)}
        self.n = len(self.tags)
        self.start_stack = {t: 2000 for t in self.tags}
        self.start(self.seat_of[me], self.n, self.rules)

    def _with_log(self, obs: Observation) -> Observation:
        return obs

    def _end_log(self, hand_no, delta, n_players, history, deltas, final_stacks, showdown, board) -> None:
        self.bot.hand_end(HandResult(hand_no=hand_no, deltas=list(deltas), showdown=dict(showdown or {}),
                                     board=tuple(board or ()), history=list(history or ())))

    def to_observation(self, v: Any) -> Observation:
        bb = v.bb
        n = self.n
        seat_of = self.seat_of
        stacks, bets, in_hand = [0] * n, [0] * n, [False] * n
        floors, peaks = [0] * n, [0] * n
        start = self.start_stack
        for p in v.players:
            s = seat_of[p.tag]
            st = int(p.stack * bb + 0.5)
            stacks[s] = st
            bets[s] = int(p.bet * bb + 0.5)
            in_hand[s] = p.state != "F"
            floors[s] = int(p.floor * bb + 0.5)
            peaks[s] = int(p.peak * bb + 0.5)
            start[p.tag] = st + int(p.in_pot * bb + 0.5)
        me = seat_of[v.players[v.me].tag]
        to_call = int(v.owe * bb + 0.5)
        lo = hi = None
        legal = ["fold", "call"] if to_call > 0 else ["check"]
        if v.max_raise > 0.0:
            base = bets[me] + to_call
            lo = base + int(v.min_raise * bb + 0.5)
            hi = base + int(v.max_raise * bb + 0.5)
            legal.append("raise")
        lvl = self.rules.blind_levels[v.level - 1]
        return make_observation(
            hole=cards(v.hole), board=cards(v.board), street=v.street, seat=me,
            button=seat_of[v.players[v.button].tag], stacks=stacks, bets=bets, in_hand=in_hand,
            pot=int(v.pot * bb + 0.5) - sum(bets), to_call=to_call, min_raise=lo, max_raise=hi, legal=legal,
            hand_no=v.hand - 1, blinds=(lvl[0], lvl[1]), history=history(v.log, bb, seat_of),
            extras={"floors": floors, "peaks": peaks})

    def from_action(self, action: Action, obs: Observation, native: Any) -> Any:
        k = action.kind
        if k is ActionKind.RAISE:
            if action.amount >= obs.max_raise:
                return "r1000000"
            x = (action.amount - obs.bets[obs.seat] - obs.to_call) / native.bb
            return f"r{x:.6f}" if x > 0 else "c"
        if k is ActionKind.FOLD and obs.to_call > 0:
            return "f"
        return "c"

    def native_safe(self, native: Any) -> Any:
        try:
            if native.owe <= 0:
                return "c"
            you = native.players[native.me]
            return "c" if you.stack < you.floor else "f"  # past the stop a fold is the end of the table
        except Exception:  # noqa: BLE001
            return "f"

    def recap(self, r: Any) -> None:
        """One finished hand -> Adapter.hand_end. The kit's `net` leaves out what an eliminated seat forfeits: charged
        here, so the deltas sum to 0."""
        bb = r.bb
        seat_of = self.seat_of
        start = self.start_stack
        deltas = [0] * self.n
        for tag, net in r.net:
            s = seat_of[tag]
            d = int(net * bb + (0.5 if net >= 0 else -0.5))
            if tag in r.out:
                d = -start.get(tag, -d)
            deltas[s] = d
            start[tag] = start.get(tag, 0) + d
        showdown = {seat_of[t]: cards(m) for t, m in r.shown}
        self.hand_end(r.hand - 1, deltas[self.seat], self.n, history=history(r.log, bb, seat_of), deltas=deltas,
                      showdown=showdown, board=cards(r.board))


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    return maybe_checked(TonightAdapter(StopBot(bot, STOP_MODE) if STOP_MODE else bot, rules))
