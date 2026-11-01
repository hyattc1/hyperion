"""The composite bot: a base plus, per section of the game, the member bot whose decision is used there.

hyperion/compose/sections.py partitions every decision into twelve sections; bot.py routes each one to a donor (a member
bot, and whether the exploit layer acts on it there). Running log: docs/drills/compose-log.md.

    from hyperion.compose import make_bot
    bot = make_bot(route="pre_hu=hero")
"""
from .bot import COUNTS, DONORS, MEMBERS, Composite, CompositeCore, ComposeConfig, compose_config, make_bot, register
from .sections import SECTIONS, section, section_name

__all__ = ["COUNTS", "DONORS", "MEMBERS", "Composite", "CompositeCore", "ComposeConfig", "SECTIONS", "compose_config",
           "make_bot", "register", "section", "section_name"]
