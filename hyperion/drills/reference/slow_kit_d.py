"""A kit D submission that is too slow on purpose."""
from hyperion.drills.adapter import KitDBot
from hyperion.drills.cheapbot import SlowBot
from hyperion.drills.fakekits.kit_d.kit import parse_args, run_bot

if __name__ == "__main__":
    run_bot(KitDBot(SlowBot(0.02)), parse_args())
