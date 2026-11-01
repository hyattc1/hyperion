"""Tonight's adapter: the skeleton to copy to `submission/adapter.py` at minute 5.

Fill the TODOs in order. They are the gotchas in the order they have bitten (PLAYBOOK Stage 2, the kit
RUBRICs); each names the Observation field it feeds and the one-line test to run before moving on.
Until the bodies are written this module imports and instantiates and does nothing else. Reference
adapters for four fake kits: `hyperion/drills/adapter.py`. If one of them fits the kit, subclass it
instead of filling this in.

While the kit simulator runs, check every decision against the Observation invariants:
    HYPERION_CHECK=1 python -m <kit runner> submission/<entry>.py      # conformance report at exit
"""
from __future__ import annotations

from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_card  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation  # noqa: F401
from hyperion.drills.conformance import maybe_checked

# TODO 1  CARD ENCODING -> obs.hole, obs.board. Ours: int rank*4 + suit with 2=0 ... T=8 ... A=12 and
#   c d h s = 0..3 (`parse_card("Th") == 34`). Theirs: strings ("Th", "10h", "hT"), dicts ({"rank": 10,
#   "suit": "H"}, ace as 14 or 1), ints in SOME order (suit-major is common), or objects. Traps: "10" vs "T",
#   suit case, their int order is not ours.
#   Test: python -c "from submission.adapter import card; assert card(<their Th>) == 34 and card(<their 2c>) == 0"


def card(native_card: Any) -> int:
    raise NotImplementedError("TODO 1: one kit card -> rank*4 + suit")


# TODO 2  STREET -> obs.street (index 0..3), and len(obs.board) must equal (0, 3, 4, 5)[street]. Kits give
#   a name ("flop"), an enum, or the board count (MIT: 0/3/4/5; `street == 3` is the flop, not the river).
#   Test: a flop state from the kit sim -> obs.street == 1 and len(obs.board) == 3 (conformance rule board_len).
STREET_BY_BOARD = {0: 0, 3: 1, 4: 2, 5: 3}

# TODO 3  POT -> obs.pot (previous streets ONLY) and obs.bets (this street, per seat); obs.total_pot adds
#   them. If their pot already includes this street's bets, subtract sum(bets).
#   Test: preflop, blinds posted, no action -> obs.pot == 0 and obs.total_pot == sb + bb (rule chips).

# TODO 4  RAISE -> obs.min_raise, obs.max_raise are raise-TO totals (what my bet becomes); in from_action
#   an Action.raise_to(total) goes back as the kit's total OR increment (`total - max(obs.bets)`). to_call
#   is min(max(bets) - my bet, my stack); compute it if the kit does not give it.
#   Test: unopened preflop, bb 20 -> obs.min_raise == 40 and obs.max_raise == my stack + my bet
#         (rule raise_total); kit sim 50 hands -> 0 illegal.

# TODO 5  LEGAL ACTIONS -> obs.legal, through make_observation(legal=[...]) with our names fold / check /
#   call / raise (it raises KeyError on an unknown name, which is what you want at minute 6). Find the
#   kit's word for check ("check", "CHECK", "K", CheckAction, or "call 0") and whether fold is offered
#   when checking is free.
#   Test: big blind, unopened -> CHECK in obs.legal and CALL not in obs.legal (rule check_vs_call).

# TODO 6  SEATS -> obs.seat, obs.button, and stacks / bets / in_hand indexed by the kit's seat NUMBER,
#   not by list position (sort by their seat field). Button = dealer; obs.position() is n-1 on the button.
#   Test: obs.in_hand[obs.seat] is True and obs.position() == n - 1 when the kit says we are the dealer
#         (rules in_hand_self, seat_changed).

# TODO 7  BLINDS -> obs.blinds = (sb, bb) and obs.hand_no. Blinds live in the state, in the table-start
#   message, or only in the kit's schedule (then compute from hand_no; antes are NOT blinds).
#   Test: obs.blinds == (10, 20) on the first hand and it changes at the kit's first level boundary.

# TODO 8  PER-TABLE INIT -> Adapter.start(seat, n_players, rules) -> bot.new_table. Call it from the kit's
#   table-start hook if one exists (outside the 1 ms budget); otherwise Adapter.decide calls it lazily on
#   the first decision, so everything heavy (tables, evaluator warm-up) must happen at import instead.
#   Test: python tools/pack.py ... prints the import time (budget 5 s); kit sim first decision under 1 ms.

# TODO 7b HISTORY -> obs.history = [(seat, Action)] for the hand so far, from the kit's action log if it has
#   one (pass history=... to make_observation). Hero reads who raised from history alone: drill 6's empty
#   history cost 2.5 points a table. No log at all: leave it out and make_observation rebuilds this
#   street's raises from the bets. Test: after a raise, obs.history has a RAISE by the raiser's seat.

# TODO 9  native_safe -> what the kit gets when translation itself blows up: ITS check if legal, else ITS
#   fold, built from the raw native state and never raising, even on garbage.
#   Test: adapter.native_safe(None) and adapter.decide(None) both return the kit's fold without raising.


class TonightAdapter(Adapter):
    """Kit <name>: <one line on the native state and action format, from the rule sheet>."""

    def to_observation(self, native: Any) -> Observation:
        # TODO 2-7, in that order; return make_observation(hole=..., board=..., street=..., seat=..., button=...,
        #   stacks=..., bets=..., in_hand=..., pot=..., to_call=..., min_raise=..., max_raise=..., legal=[...],
        #   hand_no=..., blinds=(sb, bb), history=[...] (TODO 7b))
        raise NotImplementedError("TODO 2-7: kit state -> Observation")

    def from_action(self, action: Action, obs: Observation, native: Any) -> Any:
        # TODO 4-5: action.kind.value is "fold" | "check" | "call" | "raise"; action.amount is a raise-TO total.
        raise NotImplementedError("TODO 4-5: Action -> kit action")

    def native_safe(self, native: Any) -> Any:
        # TODO 9
        raise NotImplementedError("TODO 9: the kit's check-else-fold")


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    """What the entry point calls. HYPERION_CHECK=1 turns the conformance report on; nothing else changes."""
    return maybe_checked(TonightAdapter(bot, rules))
