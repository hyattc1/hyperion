"""The one place that names the bot we ship.

    SHIP   the bot the submission entry builds (`make_bot()`), tools/pack.py packs, tools/gate.py pairs the zip
           against, tools/latency.py times, and `python -m hyperion.sim --field realistic@ship` seats.
    DIALS  the dials it plays with; {} = the bot as measured. `--dials JSON` on those tools replaces them.

`--bot hero` on any of the tools restores Hero; `--bot cheap` is the Stage 2 bot, Hero.cheap(). tools/pack.py writes
the bot and dials it packed into the package's own copy of this file, so the zip says what it plays and the gate
reads it from there.

The dials are one flat dict whatever the bot (docs/packet/CONTRACTS.md lists every key):
  hero, cheap   Hero's dotted Config keys: {"preflop.open_frac_default": 0.2, "cheap": true}
  hybrid3_x     rival 3's core: `r3.<name>` (hyperion/hybrid/dials.py); the exploit layer: `exploit.<field>`, or
                {"exploit": null} for none; "cheap": true (every decision Hero's cheap path); the fallback Hero:
                `hero.<Config key>`; and any flat HybridConfig field (hyperion/hybrid/bot.py).

Registering another bot as the ship bot is one entry in BUILDERS, its name to "module:function" for a function
(dials: dict, seed: int | None) -> a bot with new_table, act, hand_end and variant_decide, imported only from
hyperion/ (pack vendors hyperion/ and tables/); shipping it is then the one line SHIP = that name (or `--bot <name>`
on pack, gate and latency to try it first). The composite (hyperion/compose/) is registered: SHIP = "composite"
ships it, with its dials (route, r3.*, ...) in DIALS.
"""
from __future__ import annotations

from importlib import import_module

SHIP = "hybrid3_x"
DIALS: dict = {}

BUILDERS = {
    "hybrid3_x": "hyperion.ship:hybrid3_x",  # rival 3's core + the exploit layer behind Hero's shell (the base)
    "hybrid3": "hyperion.ship:hybrid3",  # the same without the layer
    "hero": "hyperion.ship:hero",  # Hero alone, default Config: the base until 2026-11-01
    "cheap": "hyperion.ship:cheap",  # Hero.cheap(): Stage 2's bot
    "composite": "hyperion.compose.bot:ship",  # sections routed to donors (hyperion/compose/); not measured as a ship yet
}


def hybrid3_x(dials: dict, seed: int | None = None):
    from .hybrid import make_bot

    return make_bot(seed=seed, overrides={"core": "rival3", "exploit": "hero", **dials})


def hybrid3(dials: dict, seed: int | None = None):
    from .hybrid import make_bot

    return make_bot(seed=seed, overrides={"core": "rival3", **dials})


def hero(dials: dict, seed: int | None = None):
    from .strategy.hero import Hero, config_from_dict

    return Hero(config_from_dict(dials, seed=seed))


CHEAP = {"cheap": True, "use_profiler": False, "use_icm": False}  # Hero.cheap()'s Config


def cheap(dials: dict, seed: int | None = None):
    return hero({**CHEAP, **dials}, seed)


def builder(name: str):
    """The build function BUILDERS names, imported now."""
    spec = BUILDERS.get(name)
    if spec is None:
        raise KeyError(f"unknown ship bot {name!r}; known: {', '.join(BUILDERS)}")
    if callable(spec):
        return spec
    mod, _, attr = spec.partition(":")
    return getattr(import_module(mod), attr)


def make_bot(name: str | None = None, dials: dict | None = None, seed: int | None = None):
    """The ship bot (or `name`) with DIALS (or `dials`). What the submission entry calls, with no arguments."""
    return builder(SHIP if name is None else name)(dict(DIALS if dials is None else dials), seed)


def describe(name: str | None = None, dials: dict | None = None) -> str:
    return f"{SHIP if name is None else name} dials {DIALS if dials is None else dials}"


class SimSeat:
    """The ship bot as a simulator seat (`ship` in hyperion.sim.bestiary after register_sim)."""

    name: str | None = None
    dials: dict | None = None

    def __init__(self, seed: int | None = None):
        self.impl = make_bot(self.name, self.dials, seed)

    def new_table(self, rules, seat: int, n_players: int) -> None:
        self.impl.new_table(rules, seat, n_players)

    def act(self, obs):
        return self.impl.act(obs)

    def hand_end(self, result) -> None:
        self.impl.hand_end(result)

    def variant_decide(self, prompt: dict):
        return self.impl.variant_decide(prompt)


# ---------------------------------------------------------------- the record in a package's copy of this file

def read_record(path) -> tuple[str, dict]:
    """(SHIP, DIALS) as written in a copy of this file, read without importing it (tools/gate.py on a zip)."""
    import ast
    from pathlib import Path

    found = {}
    for node, name in _record_nodes(ast.parse(Path(path).read_text(encoding="utf-8"))):
        found[name] = ast.literal_eval(node.value)
    if set(found) != {"SHIP", "DIALS"} or not isinstance(found["SHIP"], str) or not isinstance(found["DIALS"], dict):
        raise ValueError(f"{path}: no SHIP = '<name>' and DIALS: dict = {{...}} at the top level")
    return found["SHIP"], found["DIALS"]


def write_record(path, name: str, dials: dict) -> None:
    """Rewrite the SHIP and DIALS lines of a copy of this file (tools/pack.py, in the package it builds)."""
    import ast
    from pathlib import Path

    path = Path(path)
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    new = {"SHIP": f"SHIP = {name!r}\n", "DIALS": f"DIALS: dict = {dict(dials)!r}\n"}
    nodes = sorted(_record_nodes(ast.parse("".join(lines))), key=lambda x: -x[0].lineno)
    if {n for _, n in nodes} != set(new):
        raise ValueError(f"{path}: no SHIP and DIALS assignments to rewrite")
    for node, nm in nodes:  # bottom first, so earlier line numbers stay valid
        lines[node.lineno - 1:node.end_lineno] = [new[nm]]
    path.write_text("".join(lines), encoding="utf-8")


def _record_nodes(tree):
    import ast

    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            nm = node.targets[0].id
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.value is not None:
            nm = node.target.id
        else:
            continue
        if nm in ("SHIP", "DIALS"):
            yield node, nm


def register_sim(dials: dict | None = None, name: str | None = None) -> str:
    """Seat the ship bot as `ship` in the simulator (`--field realistic@ship`), with these dials. Returns describe()."""
    from .sim import bestiary

    seat = type("ShipSeat", (SimSeat,), {"name": name, "dials": None if dials is None else dict(dials),
                                         "__doc__": f"The bot hyperion/ship.py ships: {describe(name, dials)}."})
    bestiary.REGISTRY["ship"] = seat
    return describe(name, dials)
