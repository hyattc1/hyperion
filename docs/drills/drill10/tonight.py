"""Tonight's twist as a variant file: Solo Hold'em, exactly one hole card and four board cards at showdown.
Pure Rules (must_use_hole=1); the identity hooks' score_hand already evaluates must-use through the engine."""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks


def variant() -> Variant:
    rules = Rules(must_use_hole=1,
                  blind_levels=((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500)),
                  payouts=(13, 8, 5, 3, 2, 1, 0, -2), extras={"variant": "solo"})
    return Variant(name="solo", summary="Solo Hold'em: best five of exactly one hole card and four board cards.",
                   rules=rules, breaks="evaluator rule and every equity table", checklist=("tables/variants/solo",),
                   hooks_factory=VariantHooks, needs_engine=False, axis="ranking")
