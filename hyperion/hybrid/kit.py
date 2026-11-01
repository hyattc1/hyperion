"""What every decision core behind the shell shares: the kit-shaped observation the rivals were built against, its
answer back as an Action, and the soft-deadline signal. No core is imported here, so a package that ships one core
never loads another (rival 2's module runs a Monte Carlo at import: 1.2 s quiet, up to 6 s on a loaded host).
"""
from __future__ import annotations

from ..core.types import Action, Observation

_KIT_ACTIONS = {"fold": Action.fold(), "check": Action.check(), "call": Action.call()}
_KIT_LEGAL: dict = {}  # frozenset[ActionKind] -> set of strings, memoized


class SoftDeadline(Exception):
    """The decision is already late when the core's expensive part would start: answer with Hero's cheap path."""


class KitObs:
    """The observation shape the rivals were built against (red-team brief, kit.py): our fields with `legal` a set of
    strings, `history` a list of (seat, (kind, amount)) and `hand_no` 1-based."""

    __slots__ = ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot",
                 "to_call", "min_raise", "max_raise", "legal", "hand_no", "blinds", "history")


class KitView:
    """Converts our Observation to KitObs. History is converted incrementally (the prefix never changes within a
    hand). `hole` and `board` are passed in already mapped to canonical strength. A history the adapter rebuilt
    from the bets (`obs.extras["history_from_bets"]`: a kit with no action log) is passed as none: it holds the
    street's raises and no folds, calls or checks, and a rival's replay of it books every raiser as a seat that
    raises every hand (rival 3 through fake kit B: -1.23 +- 0.81 against itself in-sim). The core then reads the
    raises from the bets, as it does anyway, and keeps its priors on every seat."""

    __slots__ = ("_hist", "_hist_n", "_hist_hand")

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._hist, self._hist_n, self._hist_hand = [], 0, -1

    def __call__(self, obs: Observation, hole: tuple, board: tuple) -> KitObs:
        k = KitObs()
        k.hole, k.board, k.street, k.seat, k.button = hole, board, obs.street, obs.seat, obs.button
        k.stacks, k.bets, k.in_hand, k.pot = obs.stacks, obs.bets, obs.in_hand, obs.pot
        k.to_call, k.min_raise, k.max_raise = obs.to_call, obs.min_raise, obs.max_raise
        k.hand_no, k.blinds = obs.hand_no + 1, obs.blinds
        legal = _KIT_LEGAL.get(obs.legal)
        if legal is None:
            legal = _KIT_LEGAL[obs.legal] = {kind.value for kind in obs.legal}
        k.legal = legal
        src = () if obs.extras and obs.extras.get("history_from_bets") else obs.history
        n = len(src)
        if obs.hand_no != self._hist_hand or n < self._hist_n:
            self._hist, self._hist_n, self._hist_hand = [], 0, obs.hand_no
        if n > self._hist_n:
            self._hist.extend((s, (a.kind.value, a.amount)) for s, a in src[self._hist_n:])
            self._hist_n = n
        k.history = self._hist
        return k


def from_kit(answer, obs: Observation) -> Action | None:
    """('kind', raise-to total) -> a legal Action; None when the answer is unreadable."""
    try:
        kind, amount = answer
    except (TypeError, ValueError):
        return None
    if kind == "raise":
        try:
            return Action.raise_to(int(amount)).clamp(obs)
        except (TypeError, ValueError):
            return None
    a = _KIT_ACTIONS.get(kind)
    return a.clamp(obs) if a is not None else None
