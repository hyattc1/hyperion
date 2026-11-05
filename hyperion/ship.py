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

SHIP = "composite"  # the composite (decisions entry "Composite bot"); hybrid3_x and hero are one word away
DIALS: dict = {}

BUILDERS = {
    "hybrid3_x": "hyperion.ship:hybrid3_x",  # rival 3's core + the exploit layer behind Hero's shell (the base)
    "hybrid3": "hyperion.ship:hybrid3",  # the same without the layer
    "hero": "hyperion.ship:hero",  # Hero alone, default Config: the base until 2026-11-01
    "cheap": "hyperion.ship:cheap",  # Hero.cheap(): Stage 2's bot
    "composite": "hyperion.compose.bot:ship",  # rival 3's core preflop, Hero postflop and short facing a raise (compose)
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


# ---------------------------------------------------------------- the night's dials by name, for whichever bot ships
# The windows (PLAYBOOK section 5, prompt 06) and the timeout fallbacks name a recipe, not keys: `--dials survival`
# on the sim, latency, pack and gate resolves it for the bot SHIP (or --bot) names, so the prompts stay right
# whatever the switch says. On the hybrids a recipe is the core's dials plus Hero's own recipe as `hero.<key>` (the
# tables Hero plays); the composite has its own (COMPOSITE_RECIPES). Join names with "+" to stack them:
# "survival+passive". Checked to move play the stated way: Hero and hybrid3_x in docs/decisions.md ("Ship hybrid3_x as
# the base"), the composite in docs/drills/f1-windows-log.md.
HERO_RECIPES = {
    "survival": {"preflop.patience_deep": 0.3, "postflop.icm_margin": 0.15, "postflop.big_value_tier": 7,
                 "preflop.three_bet_frac": 0.02},
    "passive": {"preflop.open_frac": {"2": 0.66, "3": 0.48}, "postflop.cbet_freq_ip_dry": 0.7},
    "dead_seats": {"exploit.steal_min_fold": 0.5, "profiler_blend_n": 4.0},
    "strong_field": {"preflop.open_frac_mult": 0.9, "profiler_prior_n": 1.0},
    "latency": {"use_profiler": False},
    "timeouts": {"cheap": True},
}
CORE_RECIPES = {  # rival 3's core: hybrid3_x, hybrid3 and the composite's base
    "survival": {"r3.call_margin": 0.03, "r3.call_edge": 0.16, "r3.raise_shift": 0.05, "r3.three_bet_scale": 0.7},
    "passive": {"r3.open_late_scale": 1.3, "r3.bluff_scale": 1.3},
    "dead_seats": {"r3.prior_scale": 0.5},
    "strong_field": {},  # Hero's recipe on the core lost 0.48 +- 0.33 on `top`: the core keeps its own play
    "latency": {"exploit": None},  # the layer's ~6 us
    "timeouts": {"cheap": True},  # every decision Hero's cheap path
}
CORE_BOTS = ("hybrid3_x", "hybrid3", "composite")
# The composite (F) is not hybrid3_x with a route: rival 3's core decides preflop only (Hero plays postflop and short
# facing a raise), and one exploit layer sits in front of every member, whose own layers are off. So on F the core's
# postflop dials (r3.call_edge, r3.raise_shift, r3.bluff_scale) never decide (the same play, seed for seed), a Hero
# `exploit.*` key reaches nothing, and the layer is worth 0.2 points ({"exploit": null}: -0.22 +- 0.09 on night). Its
# recipes: the core's preflop dials, the layer's own keys, Hero's postflop where the stated play is Hero's, and Hero's
# recipe as `hero.<key>` (Hero's postflop, its short re-shoves and the 14 tables it plays whole). Measured on F,
# seeds 10000-10199 x 8, paired, model mode (docs/drills/f1-windows-log.md).
COMPOSITE_RECIPES = {
    # all-in calls 10.9% -> 6.8%, deep 3-bets 5.7% -> 4.0%, 7th-8th finishes 8.1% -> 7.2%; postflop stays Hero's
    # (hero.postflop.call_margin 0.25 on top folds 2 points more there and measured -0.06 +- 0.06 on `strong`)
    "survival": {"r3.call_margin": 0.03, "r3.three_bet_scale": 0.7, "hero.preflop.patience_deep": 0.3,
                 "hero.postflop.icm_margin": 0.15, "hero.postflop.big_value_tier": 7, "hero.preflop.three_bet_frac": 0.02},
    # cutoff and button opens 59.9% -> 63.4%, bets when checked to 54.3% -> 58.1% (the layer bets at a 0.35 fold read)
    "passive": {"r3.open_late_scale": 1.3, "exploit.bet_min_fold": 0.35, "hero.preflop.open_frac": {"2": 0.66, "3": 0.48},
                "hero.postflop.cbet_freq_ip_dry": 0.7},
    # the layer steals at a 0.5 fold read (0.7 shipped) and Hero's reads act sooner: steals 67% -> 75% on `timeouts`
    # (+0.06 +- 0.05). Not r3.prior_scale 0.5 (hybrid3_x's): on F it opened wider at strong tables and lost there
    "dead_seats": {"exploit.steal_min_fold": 0.5, "hero.profiler_blend_n": 4.0},
    # nothing measurable on plain hold'em (-0.004 +- 0.021 on night): Hero's keys reach its postflop reads and the
    # tables it plays whole; the core keeps its own play, as on hybrid3_x
    "strong_field": {"hero.preflop.open_frac_mult": 0.9, "hero.profiler_prior_n": 1.0},
    # no shadow decisions (members not chosen skip the call): about 17 us a call and 30 us at p99, points level; the
    # layer stays (off it saves about 5 us and costs 0.22 points)
    "latency": {"late_us": 0},
    # every decision Hero's cheap path: -1.58 +- 0.14 on night, an emergency. Through kit J's adapter 88 us a decision and
    # p99 230 us, against the ship bot's 255 and 520 and `latency`'s 215 and 490 (docs/drills/climb/h8-log.md)
    "timeouts": {"cheap": True},
}

# A slow or noisy sandbox (backlog R1, docs/drills/r1-timing-log.md). Not a window recipe: it is a property of the box,
# set once when the sandbox's timing is known or suspect, and stacked with any window recipe (`slow_box+survival`).
# SafeBot counts only near-timeouts (0.8 ms, not 0.5), and only when they cluster (5 in 60 calls); each cluster steps
# one level down, and 40 quiet calls step back up (then 80, 160, ...). The composite's levels, in order: no shadows; the
# base's exact-ICM decisions to Hero under top-heavy payouts; every section to Hero; the cheap path last.
# hybrid3_x has one level (lean) before the cheap path, Hero none. The bot alone at k <= 3 never fires it on F; the cliff
# it replaces cost F 2.2 points a table on th at k = 3 (100-point table) and 0.03-0.16 on 8..1. `whole_call` (G1): behind a
# kit's adapter it counts the whole timed call, the adapter's and the deferred hand end's time too, not `act` alone, and
# `hand_end_ms` keeps a kit's held hand end out of that call when a typical decision with it would pass that much of the budget.
SLOW_RECIPES = {
    "slow_box": {
        "composite": {"deadline_ms": 0.8, "panic_window": 60, "panic_ladder": True, "panic_recover": 40,
                      "degrade": "bare,lean,hero", "whole_call": True, "hand_end_ms": 0.75},
        "core": {"deadline_ms": 0.8, "panic_window": 60, "panic_ladder": True, "panic_recover": 40, "whole_call": True,
                 "hand_end_ms": 0.75},
        "hero": {"deadline_ms": 0.8, "panic_window": 60, "panic_recover": 40, "whole_call": True, "hand_end_ms": 0.75},
    },
}


def recipe(names: str, name: str | None = None) -> dict:
    """The dials of the recipes `names` ("survival", "survival+passive") for the bot `name` (default SHIP)."""
    bot = SHIP if name is None else name
    out: dict = {}
    for part in [x.strip() for x in names.split("+") if x.strip()]:
        if part in SLOW_RECIPES:
            r = SLOW_RECIPES[part]
            out.update(r["composite"] if bot == "composite" else r["core"] if bot in CORE_BOTS else r["hero"])
            continue
        if part not in HERO_RECIPES:
            raise KeyError(f"unknown recipe {part!r}; known: {', '.join([*HERO_RECIPES, *SLOW_RECIPES])}")
        if bot in ("hero", "cheap"):
            out.update(HERO_RECIPES[part])
        elif bot == "composite":
            out.update(COMPOSITE_RECIPES[part])
        elif bot in CORE_BOTS:
            out.update(CORE_RECIPES[part])
            if part not in ("latency", "timeouts"):
                out.update({"hero." + k: v for k, v in HERO_RECIPES[part].items()})
        else:
            raise KeyError(f"no recipes for ship bot {bot!r}: add it to CORE_BOTS or give its dials as JSON")
    return out


def parse_dials(spec: str | None, name: str | None = None) -> dict | None:
    """A tool's --dials: a JSON object inline or in a file, or recipe names for the bot `name`; None when not given."""
    import json
    import os

    if spec is None:
        return None
    text = spec.strip()
    if text.startswith("{"):
        val = json.loads(text)
    elif os.path.isfile(text):
        with open(text) as f:
            val = json.load(f)
    else:
        return recipe(text, name)
    if not isinstance(val, dict):
        raise ValueError(f"--dials must be a JSON object or recipe names, got {spec!r}")
    return val


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


def write_record(path, name: str | None = None, dials: dict | None = None) -> None:
    """Set SHIP (`name`) and DIALS (`dials`) in a copy of this file: tools/pack.py in the package it builds, `python -m
    hyperion.ship --set` / `--bot` in the repo's. Only the value given is touched, and only when it changes: the
    line's quoting, its annotation and its comment stay (drill 11: --set rewrote the SHIP line and dropped its
    comment)."""
    import ast
    from pathlib import Path

    path = Path(path)
    text = path.read_text(encoding="utf-8")
    nodes = {nm: node for node, nm in _record_nodes(ast.parse(text))}
    if set(nodes) != {"SHIP", "DIALS"}:
        raise ValueError(f"{path}: no SHIP and DIALS assignments to rewrite")
    starts = [0] + [i + 1 for i, c in enumerate(text) if c == "\n"]  # where each line begins, as ast counts lines
    edits = []
    if name is not None and ast.literal_eval(nodes["SHIP"].value) != name:
        old = ast.get_source_segment(text, nodes["SHIP"].value) or ""
        q = old[:1] if old[:1] in ("'", '"') and old[:1] * 3 != old[:3] else "'"
        edits.append((nodes["SHIP"].value, q + name + q if q not in name and "\\" not in name else repr(name)))
    if dials is not None and ast.literal_eval(nodes["DIALS"].value) != dict(dials):
        edits.append((nodes["DIALS"].value, repr(dict(dials))))

    def at(lineno: int, col: int) -> int:  # an ast (line, utf-8 byte column) -> an index into text
        s = starts[lineno - 1]
        return s + len(text[s:].encode("utf-8")[:col].decode("utf-8", "ignore"))

    for node, src in sorted(edits, key=lambda e: (-e[0].lineno, -e[0].col_offset)):  # last first: offsets stay valid
        a, b = at(node.lineno, node.col_offset), at(node.end_lineno, node.end_col_offset)
        text = text[:a] + src + text[b:]
    if edits:
        path.write_text(text, encoding="utf-8")


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


def main(argv=None, path=None) -> int:
    """python -m hyperion.ship [--set RECIPES|JSON|''] [--bot NAME]: print SHIP and DIALS; --set keeps dials in
    this file (the repo's copy), --bot also switches SHIP."""
    import argparse
    from pathlib import Path

    p = argparse.ArgumentParser(prog="python -m hyperion.ship", description=main.__doc__)
    p.add_argument("--set", dest="dials", help="recipe names (survival+passive), a JSON object, or '' for none")
    p.add_argument("--bot", help="switch SHIP to this BUILDERS name")
    a = p.parse_args(argv)
    path = Path(path or __file__)
    name, dials = read_record(path)
    if a.bot is not None:
        builder(a.bot)
        name = a.bot
    if a.dials is not None:
        dials = parse_dials(a.dials, name) if a.dials.strip() else {}
    if a.bot is not None or a.dials is not None:
        write_record(path, name if a.bot is not None else None, dials if a.dials is not None else None)
    print(f"SHIP = {name!r}\nDIALS = {dials!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
