"""The composite bot: a base bot plus, per section of the game, the member bot whose decision is used there.

hyperion/compose/sections.py partitions every decision into twelve sections; bot.py routes each one. Running log:
docs/drills/compose-log.md.
"""
from .sections import SECTIONS, section, section_name

__all__ = ["SECTIONS", "section", "section_name"]
