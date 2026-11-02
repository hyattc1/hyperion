"""Event-driven kits: the hand rebuilt from per-event callbacks, and an Adapter that decides from it.

Some kits never send a state: they call the bot once per event (a table start, a hand start with the blinds posted
and our cards, new board cards, every action, ours included, a showdown, a hand end) and ask for a decision with
only the legal options (drill 7's kit E). The bot then has to keep the pot, the stacks, this street's bets, who is
still in and the action log itself, and one slip (antes counted as bets, bets not reset on a new street, a missed
event) silently corrupts every later decision. `EventTracker` is that bookkeeping, written once and tested
(tests/test_drills_events.py); tonight's player file maps each kit event to one tracker call
(hyperion/drills/event_player_template.py; a worked example for the fake event kit is
hyperion/drills/event_example.py).

Conventions: cards are ours (ints, rank * 4 + suit: the player converts), seats are the kit's seat numbers 0..n-1,
hand numbers are ours (0-based: a kit counting from 1 passes hand - 1), action kinds are ours (fold, check, call,
raise), and a raise's `total` is the seat's street total after it (raise-to). Every method is O(seats), never
raises on a well-formed event, and leaves the state consistent between events: an interrupted or missed event
shows up as a mismatch `fresh()` reports (the decision then check/folds instead of playing stale cards).
"""
from __future__ import annotations

from typing import Any, Iterable

from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.drills.adapter import KIND_BY_NAME, Adapter, make_observation


class EventTracker:
    """One table's current hand as an event kit reports it, kept as the Observation's fields (module doc)."""

    def __init__(self, rules: Rules | None = None):
        self.rules = rules or Rules()
        self.n = 0
        self.seat = 0
        self.hand_no = -1
        self._new_hand(0, 0, (0, 0), [], ())

    # ------------------------------------------------------------------ events
    def table(self, seat: int, n_players: int, rules: Rules | None = None) -> None:
        """The table start: our seat and the number of seats."""
        if rules is not None:
            self.rules = rules
        self.seat, self.n = int(seat), int(n_players)
        self.hand_no = -1
        self._new_hand(-1, 0, (0, 0), [0] * self.n, ())

    def hand_start(self, hand_no: int, button: int, blinds, chips, hole: Iterable[int], seat: int | None = None) -> None:
        """A new hand: `chips` every seat's chips BEFORE anything is posted (a list by seat, or {seat: chips}; a
        seat missing is out), `hole` our cards. Posts (antes, blinds) follow as post() calls; a kit whose hand start
        gives the chips after posting passes those and no posts (the pot then misses the blinds: prefer before)."""
        if seat is not None:
            self.seat = int(seat)
        if isinstance(chips, dict):
            n = max(self.n, max((int(s) for s in chips), default=-1) + 1)
            row = [0] * n
            for s, c in chips.items():
                row[int(s)] = int(c)
        else:
            row = [int(c) for c in chips]
        if len(row) > self.n:
            self.n = len(row)
        row += [0] * (self.n - len(row))
        self._new_hand(int(hand_no), int(button), blinds, row, tuple(hole))

    def post(self, seat: int, paid: int, ante: bool = False) -> None:
        """A forced bet: an ante (dead money, into the pot, not a bet) or a blind (this street's bet)."""
        s, paid = int(seat), int(paid)
        self.stacks[s] -= paid
        self.pot_all += paid
        if not ante:
            self.bets[s] += paid

    def board(self, cards: Iterable[int]) -> None:
        """The board so far (all of it, not only the new cards). A longer board starts a street: bets go to 0."""
        b = tuple(cards)
        if len(b) > len(self.cards):
            self.bets = [0] * self.n  # first: an event cut short here leaves the old board, which fresh() catches
        self.cards = b

    def action(self, seat: int, kind: str, total: int | None = None, paid: int | None = None) -> None:
        """One action, ours included. `total` the seat's street total after it (raise-to), `paid` the chips that left
        its stack: give what the kit gives, the other is derived (a call's total is the bet it matched, capped by the
        stack; a check or fold pays nothing)."""
        s = int(seat)
        k = KIND_BY_NAME[str(kind).lower()]
        bet = self.bets[s]
        if paid is None:
            if total is not None:
                paid = int(total) - bet
            elif k is ActionKind.CALL:
                paid = min(max(self.bets) - bet, self.stacks[s])
            else:
                paid = 0
        paid = max(0, int(paid))
        if total is None:
            total = bet + paid
        self.stacks[s] -= paid
        self.pot_all += paid
        self.bets[s] = int(total)
        if k is ActionKind.FOLD:
            self.in_hand[s] = False
        self.log.append((s, Action(k, int(total) if k is ActionKind.RAISE else 0)))

    def showdown(self, shown: dict) -> None:
        """{seat: hole cards} of every hand shown."""
        self.shown = {int(s): tuple(h) for s, h in shown.items()}

    # ------------------------------------------------------------------ reading
    @property
    def street(self) -> int:
        """Our street index for the board: the rules' size, else the last street whose size the board reaches (a
        board past the last size, a run of extra cards, reads as the river)."""
        sizes = self.rules.board_sizes
        nb = len(self.cards)
        for i, size in enumerate(sizes):
            if size == nb:
                return i
        last = 0
        for i, size in enumerate(sizes):
            if size <= nb:
                last = i
        return last

    def fresh(self, hand_no: int | None = None, board_len: int | None = None) -> bool:
        """False when the decision cannot trust the state: another hand than the one tracked (a missed hand start),
        a board of another length (a missed or cut cards event), our cards missing, or our seat out of the hand."""
        if hand_no is not None and int(hand_no) != self.hand_no:
            return False
        if board_len is not None and int(board_len) != len(self.cards):
            return False
        if len(self.hole) < 2:
            return False
        return 0 <= self.seat < self.n and self.in_hand[self.seat]

    def observation(self, legal: Iterable[str], to_call: int | None = None, min_raise: int = 0, max_raise: int = 0,
                    board: Iterable[int] | None = None, street: int | None = None) -> Observation:
        """The Observation for our decision: `legal` our kind names; raise bounds as raise-to totals; to_call from
        the bets unless the kit says (a kit may charge the full blind against a short all-in). `board` / `street`
        replace the tracked ones (a view of a longer board)."""
        me = self.seat
        bets = list(self.bets)
        if to_call is None:
            to_call = min(max(bets) - bets[me], self.stacks[me])
        return make_observation(
            hole=self.hole, board=self.cards if board is None else tuple(board),
            street=self.street if street is None else street, seat=me, button=self.button,
            stacks=list(self.stacks), bets=bets, in_hand=list(self.in_hand), pot=self.pot_all - sum(bets),
            to_call=to_call, min_raise=min_raise, max_raise=max_raise, legal=list(legal), hand_no=self.hand_no,
            blinds=self.blinds, history=list(self.log),
        )

    def deltas(self, net: dict | None = None, chips_after: dict | None = None) -> list[int] | None:
        """Every seat's chip change for the hand: the kit's {seat: net}, or {seat: chips after} against the hand's
        start; None when it gives neither."""
        if net is not None:
            out = [0] * self.n
            for s, v in net.items():
                out[int(s)] = int(v)
            return out
        if chips_after is not None:
            out = [0] * self.n
            for s in range(self.n):
                out[s] = int(chips_after.get(s, chips_after.get(str(s), self.start[s]))) - self.start[s]
            return out
        return None

    def load(self, *, hand_no: int, button: int, blinds, hole, board, stacks, bets, in_hand, pot_prev: int,
             history, seat: int | None = None) -> None:
        """Set the whole state from a snapshot (a gate seat replaying the simulator's state, a test): `pot_prev` the
        chips of the previous streets, `history` [(seat, Action)]."""
        if seat is not None:
            self.seat = int(seat)
        self.n = len(stacks)
        if int(hand_no) != self.hand_no:
            self.start = [int(stacks[s]) + int(bets[s]) for s in range(self.n)]
            self.shown = {}
        self.hand_no, self.button, self.blinds = int(hand_no), int(button), (int(blinds[0]), int(blinds[1]))
        self.hole, self.cards = tuple(hole), tuple(board)
        self.stacks, self.bets, self.in_hand = [int(x) for x in stacks], [int(x) for x in bets], [bool(x) for x in in_hand]
        self.pot_all = int(pot_prev) + sum(self.bets)
        self.log = list(history)

    # ------------------------------------------------------------------ internals
    def _new_hand(self, hand_no: int, button: int, blinds, chips: list[int], hole: tuple) -> None:
        self.hand_no, self.button = hand_no, button
        self.blinds = (int(blinds[0]), int(blinds[1]))
        self.hole = hole
        self.cards: tuple = ()
        self.start = list(chips)
        self.stacks = list(chips)
        self.bets = [0] * len(chips)
        self.in_hand = [c > 0 for c in chips]
        self.pot_all = 0  # every chip put in this hand, antes and this street's bets included
        self.log: list[tuple[int, Action]] = []
        self.shown: dict = {}


class EventAdapter(Adapter):
    """An Adapter whose state is an EventTracker (`self.t`) the player file feeds, and whose `native` is the kit's
    decision request. Subclass it and write the three kit hooks: options(request), from_action, native_safe.

    decide(request) is Adapter.decide: the Observation from the tracker and options(), the log as the history, the
    bot's action back through from_action, anything that raises (a stale state included) the kit's check-or-fold."""

    history_source = "log"  # every action arrives as an event

    def __init__(self, bot: Any, rules: Rules | None = None):
        super().__init__(bot, rules)
        self.t = EventTracker(self.rules)

    # -- the kit hooks ------------------------------------------------------------------
    def options(self, request: Any) -> tuple[list[str], int | None, int, int]:
        """(legal kind names, to_call or None, min raise-to, max raise-to) from the kit's request."""
        raise NotImplementedError

    def request_keys(self, request: Any) -> tuple[int | None, int | None]:
        """(hand number in ours, board length) when the kit's request carries them: a mismatch with the tracker means
        a missed event, and the decision check/folds rather than play stale cards. (None, None) checks nothing."""
        return None, None

    shows_hands = True  # the kit reveals the hands at a showdown (an event or the hand end): {} means there was none

    # -- the Adapter hooks --------------------------------------------------------------
    def start(self, seat: int, n_players: int, rules: Rules | None = None) -> None:
        super().start(seat, n_players, rules)
        self.t.table(seat, n_players, self.rules)

    def to_observation(self, request: Any) -> Observation:
        t = self.t
        hand, board_len = self.request_keys(request)
        if not t.fresh(hand, board_len):
            raise LookupError("stale state: an event was missed")  # Adapter.decide answers native_safe
        legal, to_call, lo, hi = self.options(request)
        return t.observation(legal, to_call, lo, hi)

    def end_hand(self, net: dict | None = None, chips_after: dict | None = None, shown: dict | None = None,
                 board: Iterable[int] | None = None) -> None:
        """The kit's hand end, with whatever it carries (every seat's net or chips after, the hands shown)."""
        t = self.t
        if shown is not None:
            t.showdown(shown)
        deltas = t.deltas(net, chips_after)
        me = t.seat
        mine = deltas[me] if deltas is not None and 0 <= me < len(deltas) else 0
        showdown = dict(t.shown) if self.shows_hands else None
        b = tuple(t.cards if board is None else board)
        size = self.rules.board_sizes[-1]
        self.hand_end(t.hand_no, mine, t.n, history=list(t.log), deltas=deltas, showdown=showdown, board=b[:size])

    def defer_hand_end(self, on: bool = True) -> None:
        """For a kit that times its hand-end callback: the bot's pending work waits for idle() (its next event)."""
        fn = getattr(self.bot, "defer_hand_end", None)
        if fn is not None:
            fn(on)

    def idle(self) -> None:
        """Run the bot's pending hand-end work now (call it from an event with time to spare: the next hand start)."""
        fn = getattr(self.bot, "idle", None)
        if fn is not None:
            try:
                fn()
            except Exception:  # noqa: BLE001 - the next decision computes whatever is still pending
                pass
