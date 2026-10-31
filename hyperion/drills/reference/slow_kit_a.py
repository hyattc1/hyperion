"""A kit A submission that is too slow on purpose (drill: watch the auto-fold path)."""
from hyperion.drills.adapter import KitAAgent
from hyperion.drills.cheapbot import SlowBot


class Agent(KitAAgent):
    def __init__(self):
        super().__init__(SlowBot(0.02))
