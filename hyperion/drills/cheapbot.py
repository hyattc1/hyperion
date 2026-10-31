"""The cheap bot: the thing we submit at T+15 before hero exists, and the fallback when hero breaks.

Legal, crash-proof, a few microseconds per decision, and not stupid: raises strong hands, calls
cheap, shoves short. Works for any hole-card count (rank logic only) and any board size up to 8
total cards. No tables, no imports beyond core.
"""
from __future__ import annotations

from hyperion.core.eval import category, evaluate, warm
from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules

warm(7)


class CheapBot:
    def __init__(self) -> None:
        self.rules = Rules()
        self.seat = 0

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.rules = rules
        self.seat = seat

    def hand_end(self, result: HandResult) -> None:
        pass

    def act(self, obs: Observation) -> Action:
        legal = obs.legal
        bb = obs.blinds[1]
        ranks = sorted((c >> 2 for c in obs.hole), reverse=True)
        if obs.street == 0:
            paired = len(set(ranks)) < len(ranks)
            score = (ranks[0] + ranks[1]) / 2 + (6 if paired else 0)
            strong = score >= 11.5 or (paired and ranks[0] >= 5)
            decent = score >= 10 or paired
            short = obs.stack_bb < 10
            if strong and ActionKind.RAISE in legal:
                target = obs.max_raise if short else max(obs.min_raise, 3 * bb + obs.to_call)
                return Action.raise_to(target)
            if decent and obs.to_call <= (3 * bb if not short else obs.my_stack):
                return self._call_or_check(legal)
            return self._check_or_fold(legal)
        cards = obs.hole + obs.board
        if 5 <= len(cards) <= 8:
            cat = category(evaluate(cards))
        else:
            cat = 0
        pot = obs.total_pot
        if cat >= 2 and ActionKind.RAISE in legal:  # two pair or better: bet/raise about the pot
            return Action.raise_to(max(obs.min_raise, min(obs.max_raise, max(obs.bets) + pot)))
        if cat >= 1 and obs.to_call <= max(pot // 2, bb):
            return self._call_or_check(legal)
        if obs.to_call == 0:
            return Action.check()
        return self._check_or_fold(legal)

    @staticmethod
    def _call_or_check(legal) -> Action:
        if ActionKind.CALL in legal:
            return Action.call()
        return Action.check() if ActionKind.CHECK in legal else Action.fold()

    @staticmethod
    def _check_or_fold(legal) -> Action:
        return Action.check() if ActionKind.CHECK in legal else Action.fold()


class SlowBot(CheapBot):
    """For drills: sleeps past the budget on purpose, so a runner's auto-fold path gets exercised."""

    def __init__(self, delay_s: float = 0.02) -> None:
        super().__init__()
        self.delay_s = delay_s

    def act(self, obs: Observation) -> Action:
        import time

        time.sleep(self.delay_s)
        return super().act(obs)
