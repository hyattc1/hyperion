"""The night-like opponent field: other agents' one-hour builds, kept unchanged, and the weighted pool they sit in.

- `agent_*`: the persona bots, each built in one hour by an agent playing one kind of student team against the
  red-team brief and kit (docs/drills/field/agent_*.md are the builders' logs), played through the bestiary's
  PersonaBot;
- `trackb3`, `trackb5`: drills 3 and 5's Track B bots (one-hour from-scratch builds under our spec, on fake kits A
  and B), each a frozen copy of docs/drills/field/<name>_bot.py below an origin header, played through the bestiary's
  TrackBKitABot / TrackBKitBBot adapters.
- `night.py`: the pools (`night`, `night_hard`, ...) and the seat that draws its bot from the table seed.

Nothing in the bot modules imports the rest of hyperion; the adapters translate our Observation to the kit each was
built against, and the engine enforces the budget on adapter and bot together.
"""

import gc
import importlib
import sys
import types


class Obs:
    """The brief's kit.Obs (the observation shape every red-team and persona bot was built against)."""

    __slots__ = ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot", "to_call",
                 "min_raise", "max_raise", "legal", "hand_no", "blinds", "history")

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))


class Agent:
    """The brief's kit.Agent."""

    def new_table(self, rules, seat, n_players):
        pass

    def act(self, obs):
        raise NotImplementedError

    def hand_end(self, result):
        pass


def load(name: str):
    """Import hyperion.sim.field.<name>, as the tournament would run it, but inside our one process:
    - a bot that does `from kit import Agent` with no fallback gets the brief's kit (the two classes above) as a module
      named `kit`, present only while it imports;
    - a bot that switches the garbage collector off at import (gc.disable(), process-wide; agent_montecarlo does) has
      it switched back on: in the tournament each bot has its process to itself, here the collector is everyone's."""
    full = f"{__name__}.{name}"
    mod = sys.modules.get(full)
    if mod is not None:
        return mod
    shim = None
    if "kit" not in sys.modules:
        shim = types.ModuleType("kit")
        shim.Agent, shim.Obs = Agent, Obs
        sys.modules["kit"] = shim
    gc_on = gc.isenabled()
    try:
        return importlib.import_module(full)
    finally:
        if shim is not None and sys.modules.get("kit") is shim:
            del sys.modules["kit"]
        if gc_on and not gc.isenabled():
            gc.enable()
