"""Tonight's adapter: the skeleton to copy to `submission/adapter.py` at minute 5.

Fill the TODOs in order. They are the gotchas in the order they have bitten (PLAYBOOK Stage 2, the kit
RUBRICs); each names the Observation field it feeds and the one-line test to run before moving on.
Until the bodies are written this module imports and instantiates and does nothing else. Reference
adapters for four fake kits: `hyperion/drills/adapter.py`. If one of them fits the kit, subclass it
instead of filling this in. The bot behind it is `hyperion.ship.make_bot()` (the ship bot the switch names;
`tools/pack.py --bot cheap` makes the same entry play Hero.cheap() at Stage 2).

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


def history(native: Any) -> list[tuple[int, Action]]:
    """TODO 7b: the kit's action log -> [(seat, Action)] (e.g. kit A's "RAISE:120" -> Action(RAISE, 120)); a
    malformed entry is skipped, never raised. Return [] when the kit has no log (and set history_source)."""
    return []


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

# TODO 7b HISTORY -> obs.history = [(seat, Action)] for the whole hand so far, in order. Hero, the exploit layer and
#   rival 3's core read who folded, called, checked and raised from it: drill 6's adapters passed none and the
#   uploaded bot lost 2.5 points a table; a kit with no log cost 0.6-0.9 more until the inference. Which kit is it?
#   - A full log (every action this hand): map each entry to (their seat as our seat, Action(kind, raise-TO total)),
#     pass history=history(native) to make_observation, skip entries that are not bets (blind posts, discards,
#     card swaps). history_source = "log".
#   - Some actions (this street only, the last few, a per-player last action turned into entries): pass them the
#     same way and set history_source = "partial": Adapter.decide merges them into the log it rebuilds.
#   - No log (kits B, C, D): leave history out and set history_source = "bets". Adapter.decide rebuilds the hand's
#     log from the states (hyperion/drills/infer_history.py: each seat's in_hand, stack and bet between our
#     decisions, replayed through the betting order; every entry true, a state it cannot explain ends the log for
#     the hand). It needs TODO 2-7 right: pot without this street's bets, folded seats out of in_hand, stacks
#     behind, the button the kit's dealer.
#   Test: HYPERION_CHECK=1 reports 0 history_raise, history_prefix and history_infer violations and no
#   history_gap finding ("N of M hands stopped at a gap" near 0); tools/gate.py on the zip PASSes.

# TODO 8  PER-TABLE INIT -> Adapter.start(seat, n_players, rules) -> bot.new_table. Call it from the kit's
#   table-start hook if one exists (outside the 1 ms budget); otherwise Adapter.decide calls it lazily on
#   the first decision, so everything heavy (tables, evaluator warm-up) must happen at import instead.
#   Test: python tools/pack.py ... prints the import time (budget 5 s); kit sim first decision under 1 ms.
#   HAND END -> Adapter.hand_end(hand_no, my_delta, n_players, history=..., deltas=..., showdown=..., board=...):
#   pass what the kit's hand-end signal carries: the hand's actions (history() above), every seat's chip change
#   (deltas=, or final_stacks=), the hands at showdown (showdown={seat: cards}, {} when none; only if the kit
#   shows every hand still in). The bot's hand end then holds the folds after our last decision (rival 3's core
#   reads them). If the signal has only my_delta, Adapter holds the hand end until the next hand's first state,
#   whose stacks settle them (defer_hand_end); nothing to write.

# TODO 9  native_safe -> what the kit gets when translation itself blows up: ITS check if legal, else ITS
#   fold, built from the raw native state and never raising, even on garbage.
#   Test: adapter.native_safe(None) and adapter.decide(None) both return the kit's fold without raising.


class TonightAdapter(Adapter):
    """Kit <name>: <one line on the native state and action format, from the rule sheet>."""

    history_source = "log"  # TODO 7b: "log" (the kit's full log), "partial" (some actions), "bets" (none: inferred)

    def to_observation(self, native: Any) -> Observation:
        # TODO 2-7b, in that order; return make_observation(hole=..., board=..., street=..., seat=..., button=...,
        #   stacks=..., bets=..., in_hand=..., pot=..., to_call=..., min_raise=..., max_raise=..., legal=[...],
        #   hand_no=..., blinds=(sb, bb), history=history(native))
        raise NotImplementedError("TODO 2-7b: kit state -> Observation")

    def from_action(self, action: Action, obs: Observation, native: Any) -> Any:
        # TODO 4-5: action.kind.value is "fold" | "check" | "call" | "raise"; action.amount is a raise-TO total.
        raise NotImplementedError("TODO 4-5: Action -> kit action")

    def native_safe(self, native: Any) -> Any:
        # TODO 9
        raise NotImplementedError("TODO 9: the kit's check-else-fold")


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    """What the entry point calls. HYPERION_CHECK=1 turns the conformance report on; nothing else changes."""
    return maybe_checked(TonightAdapter(bot, rules))
