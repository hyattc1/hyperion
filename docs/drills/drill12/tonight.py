"""Tonight's twist as a file: the trailing stop, for our simulator and the gate (the kit's own sim stays the measure)."""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks

LEVELS = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
POINTS = (14, 9, 6, 4, 3, 2, 1, 0)


def stop_of(peak: int) -> int:
    return -(-peak * 3 // 5)


class StopHooks(VariantHooks):
    def __init__(self) -> None:
        self.peak: list = []

    def _reset(self, n: int, stack: int) -> None:
        self.peak = [stack] * n

    def settle(self, table, hand) -> None:
        stacks = table.stacks
        n = len(stacks)
        if hand.hand_no == 0 or len(self.peak) != n:
            self._reset(n, table.rules.starting_stack)
        floors = [stop_of(p) for p in self.peak]
        start = hand.stacks_start
        alive = [s for s in range(n) if start[s] > 0]
        out = [s for s in alive if stacks[s] < floors[s]]
        if out:
            pool = sum(stacks[s] for s in out)
            for s in out:
                stacks[s] = 0
            left = [s for s in ((hand.button + 1 + k) % n for k in range(n)) if s in alive and s not in out]
            if left:
                d, extra = divmod(pool, len(left))
                for i, s in enumerate(left):
                    stacks[s] += d + (1 if i < extra else 0)
        for s in range(n):
            if stacks[s] > self.peak[s]:
                self.peak[s] = stacks[s]

    def extras(self, hand) -> dict:
        n = len(hand.stacks_start)
        if len(self.peak) != n or hand.hand_no == 0:
            self.peak = [max(hand.stacks_start)] * n if hand.hand_no == 0 else self.peak
        return {"floors": [stop_of(p) if hand.stacks_start[s] > 0 else 0 for s, p in enumerate(self.peak)],
                "peaks": list(self.peak)}


def variant() -> Variant:
    rules = Rules(blind_levels=LEVELS, payouts=POINTS, extras={"full_bb_call": True, "cap_places": "chips"})
    return Variant(name="trailing_stop", summary="Trailing stop: closing a hand under 60% of your peak eliminates you.",
                   rules=rules, breaks="What a chip is worth.", checklist=(), hooks_factory=StopHooks, needs_engine=True,
                   axis="payoff")
