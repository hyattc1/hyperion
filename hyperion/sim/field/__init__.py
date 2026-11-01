"""The night-like opponent field: other agents' one-hour builds, kept unchanged, and the weighted pool they sit in.

- `trackb3`, `trackb5`: drills 3 and 5's Track B bots (one-hour from-scratch builds under our spec, on fake kits A
  and B), each a frozen copy of docs/drills/field/<name>_bot.py below an origin header, played through the bestiary's
  TrackBKitABot / TrackBKitBBot adapters.
- `night.py`: the pools (`night`, `night_hard`, ...) and the seat that draws its bot from the table seed.

Nothing in the bot modules imports the rest of hyperion; the adapters translate our Observation to the kit each was
built against, and the engine enforces the budget on adapter and bot together.
"""
