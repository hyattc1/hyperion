"""Observation builders for the strategy tests: one explicit builder, one tiny preflop/street
applier for scenario tests, and a random generator for latency and robustness runs."""
from __future__ import annotations

import random

from hyperion.core.types import Action, ActionKind, Observation, parse_cards

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


def legal_for(stacks, bets, seat, cur_bet, bb, last_inc=None) -> tuple[frozenset, int, int, int]:
    """(legal, to_call, min_raise, max_raise) the way the sim engine would compute them."""
    to_call = min(cur_bet - bets[seat], stacks[seat])
    max_raise = stacks[seat] + bets[seat]
    inc = last_inc if last_inc else bb
    min_raise = min(max_raise, cur_bet + inc)
    legal = {FOLD}
    if to_call <= 0:
        legal.add(CHECK)
    else:
        legal.add(CALL)
    others_can_respond = any(stacks[s] > 0 for s in range(len(stacks)) if s != seat)
    if max_raise > cur_bet and stacks[seat] > to_call and others_can_respond:
        legal.add(RAISE)
    return frozenset(legal), max(0, to_call), min_raise, max_raise


def make_obs(
    hole="Ah Kh", board="", street=0, seat=0, button=7, stacks=None, bets=None, in_hand=None, pot=0,
    blinds=(10, 20), hand_no=3, history=None, n=8, legal=None, to_call=None, min_raise=None, max_raise=None,
) -> Observation:
    stacks = list(stacks) if stacks is not None else [2000] * n
    n = len(stacks)
    bets = list(bets) if bets is not None else [0] * n
    in_hand = list(in_hand) if in_hand is not None else [stacks[s] + bets[s] > 0 for s in range(n)]
    cur = max(bets) if bets else 0
    lg, tc, mn, mx = legal_for(stacks, bets, seat, cur, blinds[1])
    return Observation(
        hole=parse_cards(hole), board=parse_cards(board) if board else (), street=street, seat=seat, button=button,
        stacks=stacks, bets=bets, in_hand=in_hand, pot=pot, to_call=tc if to_call is None else to_call,
        min_raise=mn if min_raise is None else min_raise, max_raise=mx if max_raise is None else max_raise,
        legal=lg if legal is None else legal, hand_no=hand_no, blinds=blinds, history=list(history or []),
    )


def preflop_obs(hole, seat, button=7, stacks=None, blinds=(10, 20), actions=(), n=8, hand_no=3) -> Observation:
    """Post blinds for the live seats after the button, apply `actions` [(seat, Action)], then build
    the observation for `seat` to act. Stacks are chips before posting."""
    stacks = list(stacks) if stacks is not None else [2000] * n
    n = len(stacks)
    bets = [0] * n
    in_hand = [stacks[s] > 0 for s in range(n)]
    live = [(button + k) % n for k in range(1, n + 1) if stacks[(button + k) % n] > 0]
    if len(live) == 2:
        sb, bb = button, [s for s in live if s != button][0]
    else:
        sb, bb = live[0], live[1]
    for s, amt in ((sb, blinds[0]), (bb, blinds[1])):
        put = min(amt, stacks[s])
        stacks[s] -= put
        bets[s] += put
    cur = blinds[1]
    history = []
    for s, a in actions:
        if a.kind is FOLD:
            in_hand[s] = False
        elif a.kind is CALL:
            put = min(cur - bets[s], stacks[s])
            stacks[s] -= put
            bets[s] += put
        elif a.kind is RAISE:
            put = min(a.amount - bets[s], stacks[s])
            stacks[s] -= put
            bets[s] += put
            cur = max(cur, bets[s])
        history.append((s, a))
    return make_obs(hole=hole, street=0, seat=seat, button=button, stacks=stacks, bets=bets, in_hand=in_hand,
                    pot=0, blinds=blinds, hand_no=hand_no, history=history)


def street_obs(hole, board, seat, button=7, stacks=None, pot=0, in_hand=None, bets=None, blinds=(10, 20),
               history=(), hand_no=3, n=8) -> Observation:
    street = {3: 1, 4: 2, 5: 3}[len(parse_cards(board))]
    return make_obs(hole=hole, board=board, street=street, seat=seat, button=button, stacks=stacks, bets=bets,
                    in_hand=in_hand, pot=pot, blinds=blinds, hand_no=hand_no, history=list(history), n=n)


_BLINDS = ((10, 20), (15, 30), (25, 50), (50, 100), (75, 150), (100, 200), (150, 300), (200, 400))


def random_obs(rng: random.Random, n=8) -> Observation:
    """A self-consistent random decision point: random street, stacks (some busted, some short),
    bets on this street, a plausible pot and a few history entries."""
    deck = list(range(52))
    rng.shuffle(deck)
    street = rng.choice((0, 0, 1, 2, 3))
    hole = tuple(deck[:2])
    board = tuple(deck[2 : 2 + (0, 3, 4, 5)[street]])
    blinds = rng.choice(_BLINDS)
    bb = blinds[1]
    alive = rng.randint(2, n)
    seats = list(range(n))
    rng.shuffle(seats)
    stacks = [0] * n
    for s in seats[:alive]:
        stacks[s] = rng.choice((bb, 3 * bb, 6 * bb, 10 * bb, 15 * bb, 25 * bb, 60 * bb, 120 * bb)) + rng.randint(0, bb)
    seat = seats[0]
    button = rng.choice(seats[:alive])
    in_hand = [stacks[s] > 0 and (s == seat or rng.random() < 0.6) for s in range(n)]
    if sum(in_hand) < 2:
        other = next(s for s in seats[1:alive])
        in_hand[other] = True
    bets = [0] * n
    cur = 0
    if street == 0:
        live = [(button + k) % n for k in range(1, n + 1) if stacks[(button + k) % n] > 0]
        sb, bbs = (button, [s for s in live if s != button][0]) if len(live) == 2 else (live[0], live[1])
        for s, amt in ((sb, blinds[0]), (bbs, bb)):
            put = min(amt, stacks[s])
            stacks[s] -= put
            bets[s] += put
        cur = bb
    history = []
    pot = 0 if street == 0 else rng.choice((2, 3, 5, 8, 12)) * bb
    for s in range(n):
        if in_hand[s] and s != seat and rng.random() < 0.4:
            size = cur + rng.choice((bb, 2 * bb, 3 * bb, 10 * bb))
            put = min(size - bets[s], stacks[s])
            if put > 0:
                stacks[s] -= put
                bets[s] += put
                cur = max(cur, bets[s])
                history.append((s, Action.raise_to(bets[s])))
        elif in_hand[s] and s != seat and rng.random() < 0.3:
            history.append((s, Action.call()))
        elif not in_hand[s] and stacks[s] > 0 and rng.random() < 0.5:
            history.append((s, Action.fold()))
    if street > 0:
        history.insert(0, (seat, Action.raise_to(3 * bb)))
    lg, tc, mn, mx = legal_for(stacks, bets, seat, cur, bb)
    return Observation(
        hole=hole, board=board, street=street, seat=seat, button=button, stacks=stacks, bets=bets, in_hand=in_hand,
        pot=pot, to_call=tc, min_raise=mn, max_raise=mx, legal=lg, hand_no=rng.randint(0, 199), blinds=blinds,
        history=history,
    )
