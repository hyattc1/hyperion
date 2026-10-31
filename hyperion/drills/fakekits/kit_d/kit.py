"""Fake starter kit D: a socket-skeleton style kit, widened from heads-up to the 8-seat target table.

Written from the documented interface of a public heads-up engine's 2026 python_skeleton (bot.py, states.py,
actions.py, runner.py), not from its code. What a submission sees:

  class Bot                 subclass it and implement
                                handle_new_round(game_state, round_state, active)
                                get_action(game_state, round_state, active) -> an action INSTANCE
                                handle_round_over(game_state, terminal_state, active)
                            `active` is your seat index (0..7), fixed for the whole game.
  GameState                 namedtuple (bankroll, game_clock, round_num); round_num is 1-based.
  RoundState                namedtuple (button, street, pips, stacks, hands, board, acting, in_hand, blinds,
                            last_raise, previous_state) with
                                legal_actions() -> a SET OF ACTION CLASSES, e.g. {FoldAction, CallAction, RaiseAction}
                                raise_bounds()  -> (min_raise_to, max_raise_to), totals for the street
                                proceed(action), proceed_street(board)
                            street is 0, 3, 4 or 5 (cards on the board). pips are chips in front this street.
                            hands has 8 slots; only yours is filled until a showdown. button is the dealer
                            seat; acting is the seat whose turn it is. There is no pot field.
  TerminalState             namedtuple (deltas, previous_state); deltas has 8 entries.
  FoldAction, CallAction, CheckAction, RaiseAction(amount)   namedtuples; amount is a raise-TO total.
  Runner, run_bot, parse_args                                 the socket loop: python player.py <port> [--host H]

Wire protocol (engine -> bot), one line per packet, clauses separated by spaces, first character is the key.
Every packet except Q gets exactly one reply line from the bot:

  T<secs>                 game clock remaining, in seconds, for the WHOLE game (every round trip is charged)
  P<seat>                 your seat
  S<s0,...,s7>            stacks behind after the blinds        (round start only)
  I<p0,...,p7>            pips, chips in front after the blinds (round start only)
  L<sb>,<bb>              the blind level this round
  H<c1,c2>                your hole cards; a card is rank in 23456789TJQKA then suit in cdhs, e.g. As Td
  G<button>               round start, dealer seat: builds a fresh RoundState, calls handle_new_round. Reply K.
  F | C | K | R<total>    one action by whoever is next to act, in order, YOURS INCLUDED; replayed with proceed()
  B<c1,c2,c3[,c4[,c5]]>   the board after a street change; replayed with proceed_street()
  O<seat>:<c1,c2>         a hand shown at showdown
  A<d0,...,d7>            round over, chip change per seat: calls handle_round_over. Reply K.
  Q                       quit

A packet with neither G nor A is a request for your action: reply F, C, K or R<raise-to total>.
A seat with no chips behind and none in front at round start is out of the hand (busted). Unknown keys
must be ignored. Only the reply goes to the socket; print your logs to stderr.
"""
from __future__ import annotations

import argparse
import socket
import sys
from collections import namedtuple

NUM_PLAYERS = 8
NUM_ROUNDS = 200
STARTING_STACK = 2000
SMALL_BLIND = 10
BIG_BLIND = 20
STARTING_GAME_CLOCK = 0.6  # seconds; the engine's T clause is authoritative

FoldAction = namedtuple("FoldAction", [])
CallAction = namedtuple("CallAction", [])
CheckAction = namedtuple("CheckAction", [])
RaiseAction = namedtuple("RaiseAction", ["amount"])

GameState = namedtuple("GameState", ["bankroll", "game_clock", "round_num"])
TerminalState = namedtuple("TerminalState", ["deltas", "previous_state"])


def _next(seat: int, in_hand: list[bool], stacks: list[int] | None) -> int:
    """The next seat after `seat` (cyclic) still in the hand, with chips behind when stacks is given."""
    n = len(in_hand)
    for i in range(1, n + 1):
        s = (seat + i) % n
        if in_hand[s] and (stacks is None or stacks[s] > 0):
            return s
    return seat


class RoundState(namedtuple("_RoundState", ["button", "street", "pips", "stacks", "hands", "board", "acting",
                                            "in_hand", "blinds", "last_raise", "previous_state"])):
    """One point in a round. Immutable: proceed() and proceed_street() return the next state."""

    @classmethod
    def start(cls, button: int, stacks, pips, hands, blinds) -> "RoundState":
        stacks, pips = list(stacks), list(pips)
        in_hand = [s + p > 0 for s, p in zip(stacks, pips)]
        live = [s for s in range(len(stacks)) if in_hand[s]]
        if len(live) == 2:  # dead button: with two left the button posts the small blind and acts first preflop
            bb = next((s for s in live if s != button), live[-1])
        else:
            sb = _next(button, in_hand, None)
            bb = _next(sb, in_hand, None)
        acting = _next(bb, in_hand, stacks)
        return cls(button, 0, pips, stacks, list(hands), [], acting, in_hand, tuple(blinds), int(blinds[1]), None)

    def _continue_cost(self) -> int:
        a = self.acting
        return min(max(self.pips) - self.pips[a], self.stacks[a])

    def legal_actions(self) -> set:
        """The set of action CLASSES the acting seat may use. FoldAction is absent when a check is free."""
        a = self.acting
        cost = self._continue_cost()
        max_to = self.stacks[a] + self.pips[a]
        legal = {CheckAction} if cost == 0 else {FoldAction, CallAction}
        can_bet = sum(1 for s in range(len(self.stacks)) if self.in_hand[s] and self.stacks[s] > 0)
        if max_to > max(self.pips) and (can_bet > 1 or cost == 0):
            legal.add(RaiseAction)
        return legal

    def raise_bounds(self) -> tuple[int, int]:
        """(min_raise_to, max_raise_to): totals for the street, max is your all-in."""
        a = self.acting
        max_to = self.stacks[a] + self.pips[a]
        min_to = min(max_to, max(self.pips) + max(self.last_raise, self.blinds[1]))
        return min_to, max_to

    def proceed(self, action) -> "RoundState":
        """Apply one action by the acting seat and hand the turn to the next seat that can act."""
        a = self.acting
        pips, stacks, in_hand = list(self.pips), list(self.stacks), list(self.in_hand)
        current = max(pips)
        last = self.last_raise
        if isinstance(action, FoldAction):
            in_hand[a] = False
        elif isinstance(action, CallAction):
            amt = min(current - pips[a], stacks[a])
            stacks[a] -= amt
            pips[a] += amt
        elif isinstance(action, RaiseAction):
            amt = max(0, min(int(action.amount) - pips[a], stacks[a]))
            stacks[a] -= amt
            pips[a] += amt
            last = max(last, pips[a] - current)
        return RoundState(self.button, self.street, pips, stacks, self.hands, self.board, _next(a, in_hand, stacks),
                          in_hand, self.blinds, last, self)

    def proceed_street(self, board) -> "RoundState":
        """A new street: pips go to the middle, the first live seat after the button acts."""
        board = list(board)
        return RoundState(self.button, len(board), [0] * len(self.pips), list(self.stacks), self.hands, board,
                          _next(self.button, self.in_hand, self.stacks), list(self.in_hand), self.blinds,
                          int(self.blinds[1]), self)


class Bot:
    """The base class of a submission's Player."""

    def handle_new_round(self, game_state, round_state, active):
        raise NotImplementedError

    def get_action(self, game_state, round_state, active):
        raise NotImplementedError

    def handle_round_over(self, game_state, terminal_state, active):
        raise NotImplementedError


def encode_action(action) -> str:
    if isinstance(action, FoldAction):
        return "F"
    if isinstance(action, CallAction):
        return "C"
    if isinstance(action, CheckAction):
        return "K"
    if isinstance(action, RaiseAction):
        return f"R{int(action.amount)}"
    return "?"  # not an action instance (a class, None, a string): the engine will count it as illegal


def _ints(v: str) -> list[int]:
    return [int(x) for x in v.split(",")] if v else []


class Runner:
    """Rebuilds the game from the engine's clauses and calls the bot's three hooks."""

    def __init__(self, pokerbot, socketfile, outfile=None):
        self.pokerbot = pokerbot
        self.socketfile = socketfile
        self.outfile = outfile or socketfile
        self.game_state = GameState(0, STARTING_GAME_CLOCK, 1)
        self.round_state = None
        self.active = 0
        self._stacks = [STARTING_STACK] * NUM_PLAYERS
        self._pips = [0] * NUM_PLAYERS
        self._blinds = (SMALL_BLIND, BIG_BLIND)
        self._hand: list[str] = []

    def receive(self):
        while True:
            line = self.socketfile.readline()
            if not line:
                return
            yield line.strip().split(" ")

    def send(self, reply: str) -> None:
        self.outfile.write(reply + "\n")
        self.outfile.flush()

    def handle_packet(self, clauses) -> str | None:
        """Process one packet; return the reply line, or None for Q."""
        round_event = False
        for clause in clauses:
            if not clause:
                continue
            key, val = clause[0], clause[1:]
            if key == "T":
                self.game_state = self.game_state._replace(game_clock=float(val))
            elif key == "P":
                self.active = int(val)
            elif key == "S":
                self._stacks = _ints(val)
            elif key == "I":
                self._pips = _ints(val)
            elif key == "L":
                sb, bb = _ints(val)
                self._blinds = (sb, bb)
            elif key == "H":
                self._hand = val.split(",") if val else []
            elif key == "G":
                hands = [[] for _ in self._stacks]
                hands[self.active] = list(self._hand)
                self.round_state = RoundState.start(int(val), self._stacks, self._pips, hands, self._blinds)
                self.pokerbot.handle_new_round(self.game_state, self.round_state, self.active)
                round_event = True
            elif key == "F":
                self.round_state = self.round_state.proceed(FoldAction())
            elif key == "C":
                self.round_state = self.round_state.proceed(CallAction())
            elif key == "K":
                self.round_state = self.round_state.proceed(CheckAction())
            elif key == "R":
                self.round_state = self.round_state.proceed(RaiseAction(int(val)))
            elif key == "B":
                self.round_state = self.round_state.proceed_street(val.split(","))
            elif key == "O":
                seat, cards = val.split(":")
                hands = list(self.round_state.hands)
                hands[int(seat)] = cards.split(",")
                self.round_state = self.round_state._replace(hands=hands)
            elif key == "A":
                deltas = _ints(val)
                terminal = TerminalState(deltas, self.round_state)
                self.game_state = self.game_state._replace(bankroll=self.game_state.bankroll + deltas[self.active])
                self.pokerbot.handle_round_over(self.game_state, terminal, self.active)
                self.game_state = self.game_state._replace(round_num=self.game_state.round_num + 1)
                round_event = True
            elif key == "Q":
                return None
            # anything else: a clause this skeleton does not know; ignored on purpose
        if round_event:
            return "K"  # ack
        assert self.round_state.acting == self.active, "engine asked for an action when it is not our turn"
        return encode_action(self.pokerbot.get_action(self.game_state, self.round_state, self.active))

    def run(self) -> None:
        for clauses in self.receive():
            reply = self.handle_packet(clauses)
            if reply is None:
                return
            self.send(reply)


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="kit D player")
    p.add_argument("port", type=int)
    p.add_argument("--host", default="localhost")
    return p.parse_args(argv)


def run_bot(pokerbot, args) -> None:
    sock = socket.create_connection((args.host, args.port))
    socketfile = sock.makefile("rw")
    try:
        Runner(pokerbot, socketfile).run()
    finally:
        try:
            socketfile.close()
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":  # a bare skeleton run folds everything: python -m ...kit_d.kit <port>
    class _Folder(Bot):
        def handle_new_round(self, *a):
            pass

        def get_action(self, game_state, round_state, active):
            legal = round_state.legal_actions()
            return CheckAction() if CheckAction in legal else FoldAction()

        def handle_round_over(self, *a):
            pass

    run_bot(_Folder(), parse_args())
    sys.exit(0)
