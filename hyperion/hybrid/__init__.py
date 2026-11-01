"""The hybrids: a red-team rival's decision core behind Hero's shell.

The core (`HybridConfig.core`) decides plain hold'em: rival 3's ("rival3", core3.py, the shipped base `hybrid3_x`)
or rival 2's ("rival2", core.py). Hero supplies everything around it: the Bot protocol, Rules, the rank remap,
variant decisions (discards, swaps, buying a card), the SafeBot guard, and every decision the core cannot represent.
Each core is imported on first use (bot.CORES), so a hybrid3 package never loads rival 2's module. Which bot ships is
named once, in hyperion/ship.py.

    from hyperion.hybrid import make_bot
    bot = make_bot(overrides={"core": "rival3", "exploit": "hero"})   # hybrid3_x
    bot.core.counts                        # decisions by route: core, hero:<reason>, exploit:<spot>

Simulator names: `hybrid`, `hybrid_x`, `hybrid3`, `hybrid3_x` (hyperion.sim.bestiary).
"""
from .bot import COUNTS, Hybrid, HybridConfig, HybridCore, hybrid_config, make_bot

__all__ = ["COUNTS", "Hybrid", "HybridConfig", "HybridCore", "hybrid_config", "make_bot"]
