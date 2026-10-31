"""Reference kit D submission: an MIT-style Player that connects to the engine's port."""
from hyperion.drills.adapter import KitDBot as Player
from hyperion.drills.fakekits.kit_d.kit import parse_args, run_bot

if __name__ == "__main__":
    run_bot(Player(), parse_args())
