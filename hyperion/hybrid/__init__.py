"""The hybrid candidate: red-team rival 2's decision core behind Hero's shell.

Rival 2 (hyperion/sim/rivals/rival2.py, our own team's drill bot) decides plain hold'em. Hero supplies
everything around it: the Bot protocol, Rules, the rank remap, variant decisions (discards, swaps, buying a
card), the SafeBot guard, and every decision the core cannot represent. It is a candidate measured against
Hero, not a replacement; which bot ships is the owner's decision (docs/decisions.md, "Hybrid candidate").

    from hyperion.hybrid import make_bot
    bot = make_bot(seed=7)                 # Hybrid: SafeBot around HybridCore
    bot.core.counts                        # decisions by route: core, hero:<reason>

Simulator name: `hybrid` (hyperion.sim.bestiary), fields realistic_h, top_h, top2_h, holdout_h.
"""
from .bot import COUNTS, Hybrid, HybridConfig, HybridCore, hybrid_config, make_bot

__all__ = ["COUNTS", "Hybrid", "HybridConfig", "HybridCore", "hybrid_config", "make_bot"]
