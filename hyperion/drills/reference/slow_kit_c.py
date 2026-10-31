"""A kit C submission that is too slow on purpose."""
import sys

from hyperion.drills.adapter import KitCAdapter
from hyperion.drills.cheapbot import SlowBot

if __name__ == "__main__":
    KitCAdapter(SlowBot(0.02)).serve(sys.stdin, sys.stdout)
