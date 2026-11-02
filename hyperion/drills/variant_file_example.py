"""Tonight's twist as a file: the shape to copy when the night's variant is not in the catalog.

A Variant is Rules plus hooks (hyperion/drills/variants.py documents the contract). Written in a file of its own, every
tool takes it by path, `path/to/file.py:factory`, and registers it by name for the rest of the process:

    .venv/bin/python -m hyperion.sim --field realistic@ship --variant hyperion/drills/variant_file_example.py:variant
    .venv/bin/python -m hyperion.sim.generic --prepare hyperion/drills/variant_file_example.py:variant
    .venv/bin/python tools/climb_accept.py --stages aware --aware generic:hyperion/drills/variant_file_example.py:variant \
        --base '' --cand '' --set screen --workers 2

The generic aware opponents (hyperion/sim/generic.py) read the hooks, so the last command puts F against opponents that
play the twist, with no code written for them. Two rules make that work: name the variant in Rules.extras["variant"]
(the bots find the hooks by it), and when the hooks keep public per-hand state under a name other than the extras key
they publish it as, give them `restore(extras, board)`, the inverse of `extras()` (below: the boards).

The example is MIT 2021's three boards (our catalog has two_boards): the pot is split in three, one share per board.
"""
from __future__ import annotations

from hyperion.core.eval import evaluate_displayed
from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks


class ThreeBoardsHooks(VariantHooks):
    """Three boards dealt in parallel; a third of the pot to the best hand on each. The engine's board is board 1."""

    N = 3

    def __init__(self) -> None:
        self.more: tuple = ((), ())

    def on_deal(self, holes, deck, rng):
        self.more = ((),) * (self.N - 1)
        return holes

    def on_street(self, street, board, holes, deck, rng, ask=None):
        grown = []
        for b in self.more:
            while len(b) < len(board) and deck:
                b = b + (deck.pop(),)
            grown.append(b)
        self.more = tuple(grown)
        return board, holes

    def boards(self, board) -> list:
        return [tuple(board), *self.more]

    def score_splits(self, hole, board, rules):
        return [evaluate_displayed(tuple(hole) + b, rules) for b in self.boards(board)]

    def score_hand(self, hole, board, rules):
        return evaluate_displayed(tuple(hole) + tuple(board), rules)

    def extras(self, hand) -> dict:
        return {"boards": self.boards(hand.board)}

    def restore(self, extras: dict, board) -> None:
        bs = (extras or {}).get("boards") or ()
        self.more = tuple(tuple(b) for b in bs[1:self.N]) if len(bs) >= self.N else ((),) * (self.N - 1)


def variant() -> Variant:
    rules = Rules(extras={"variant": "three_boards", "n_boards": 3, "pot_split": "third_per_board"})
    return Variant(
        name="three_boards",
        summary="Three boards run at once; a third of the pot goes to the best hand on each board.",
        rules=rules,
        breaks="Board 2 and 3 travel in obs.extras['boards']; equity averages over three boards.",
        checklist=("No regeneration.",),
        hooks_factory=ThreeBoardsHooks,
        needs_engine=True,
        axis="information",
    )
