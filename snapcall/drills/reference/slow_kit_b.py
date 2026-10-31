"""A kit B submission that is too slow on purpose."""
from snapcall.drills.adapter import make_kit_b_module
from snapcall.drills.cheapbot import SlowBot

decide, on_table_start, on_hand_end = make_kit_b_module(SlowBot(0.02))
