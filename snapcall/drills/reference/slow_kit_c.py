"""A kit C submission that is too slow on purpose."""
import sys

from snapcall.drills.adapter import KitCAdapter
from snapcall.drills.cheapbot import SlowBot

if __name__ == "__main__":
    KitCAdapter(SlowBot(0.02)).serve(sys.stdin, sys.stdout)
