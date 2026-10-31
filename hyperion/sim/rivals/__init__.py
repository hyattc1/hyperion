"""Bots built by other teams, kept unchanged and played through adapters in the bestiary.

Each module here is a drop-in of a file written against a kit interface that is not ours (see
docs/drills/redteam/). Nothing in this package imports the rest of hyperion; the bestiary's
RivalBot translates our Observation to the shape each rival expects and its answer back to an
Action, and the engine enforces the budget on the adapter and the rival together.
"""
