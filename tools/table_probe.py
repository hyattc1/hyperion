#!/usr/bin/env python
"""Which tables does a recorded bot need, and does this tree hold them? Standard library and the tree under test only.

    python -I -B tools/table_probe.py <root> [--bot NAME] [--dials JSON] [--rules FILE] [--variant NAME]

<root> is the repo or an unpacked package: its `hyperion` and its `tables/`. The bot is the record in <root>'s
hyperion/ship.py unless --bot / --dials say otherwise. Prints one JSON object as its last line:

    hyperion            where `hyperion` resolved from (it must be under <root>)
    bot, dials          the bot it built
    opened              every file under <root>/tables the build and a first table tried to open (a Python audit hook, so
                        no loader can hide from it, including one that catches the failure and carries on)
    declared            the tables DIAL_TABLES names for the bot's effective dials, read later than the build
    specialist_missing  hyperion.strategy.short's record of tables its loader returned None for ({kind: reason})
    lacking             the tables above that <root> does not hold. Empty is the pass.
    lacking_twist       each twist's own preflop table when <root> holds none and no variant is named (--rules or --variant):
                        the bot plays plain hold'em as measured and every twist without it. A zip frozen before batch 8.
                        With a variant named, that variant's table is in `lacking` instead.

tools/pack.py runs it on the repo (what to ship) and on the package (what it lacks: exit 1); tools/gate.py and
tools/zip_parity.py run it on an unpacked zip.

DIAL_TABLES is the declared half, for the tables nothing opens until a twist's table starts or a bot's first use: a build
cannot see those, so a dial that turns one on says so here. Add to it whenever a dial starts reading a new file late. A
table no dial gates (read at a table start whenever the rules name it) is in ALWAYS_TABLES under the bots that read it.
tools/zip_parity.py is the check on this map: it fails on any table the play itself opens that the zip lacks.
"""
from __future__ import annotations

import glob
import json
import os
import sys

# dial -> tables (relative to tables/, `{dial}` is that dial's value) it reads later than the build, when the dial is on
DIAL_TABLES = {
    "hero.voi": ("voi.json",),  # the twist decisions' value of information
    "hero.known_cards": ("known_m1s2x0u1.json", "known_m2s0x1u1.json", "known_m2s1x0u2.json"),  # 2 cards at a plain table's
    #                     start, the others only at a three-card table's (hero.py's _known.preload)
    "hero.twin_preflop": ("generic/*.json",),  # a twist's own preflop table: at that twist's table start, one per variant.
    "hero.twin_multi": ("generic/*.json",),  # With none, generic_doc returns None and Hero plays without it, silently
    "short.three": ("extra/short_3.json",),  # hyperion/strategy/short.py's three-handed tables (at its build today)
    "short.three2": ("extra/short_{short.three2_file}.*",),  # .bin (G1, the loader's first choice) or .json
}
ALWAYS_TABLES = {"composite": ("auction_bid.json",), "hybrid3_x": ("auction_bid.json",), "hybrid3": ("auction_bid.json",),
                 "hero": ("auction_bid.json",), "cheap": ()}  # Hero's bid: at the table start of a game that auctions


def effective_dials(name: str, dials: dict) -> dict:
    """The dials the bot really plays: the composite's are on top of its SHIP_DIALS."""
    if name != "composite":
        return dict(dials)
    from hyperion.compose.bot import SHIP_DIALS

    return {**SHIP_DIALS, **dials}


def declared_tables(name: str, dials: dict, tables: str) -> set:
    """Relative to `tables`. A pattern expands in this tree; one that matches nothing stays itself, so it reads as lacking."""
    eff = effective_dials(name, dials)
    out = set(ALWAYS_TABLES.get(name, ()))
    for dial, files in DIAL_TABLES.items():
        if dial.startswith("short.") and (eff.get("cheap") or not eff.get("short_route", True)):
            continue  # no specialist in this bot (`cheap` means no other member; an empty route builds none)
        if eff.get(dial) or (name in ("hero", "cheap") and dial.startswith("hero.") and eff.get(dial[5:])):
            out.update(f.replace("{short.three2_file}", str(eff.get("short.three2_file", "3b"))) for f in files)
    expanded = set()
    for f in out:
        hits = glob.glob(os.path.join(tables, f)) if "*" in f else ()
        if f.startswith("extra/short_") and hits:  # one form of a solved tree: the one its loader reads first
            hits = [h for h in hits if h.endswith(".bin")] or [h for h in hits if h.endswith(".json")]
        expanded.update(os.path.relpath(h, tables).replace(os.sep, "/") for h in hits)
        if not hits:
            expanded.add(f.replace(".*", ".bin") if f.startswith("extra/short_") else f)
    return expanded


def main(argv: list[str]) -> int:
    root = os.path.abspath(argv[0])
    bot_arg = dials_arg = rules_arg = variant = None
    i = 1
    while i < len(argv):
        if argv[i] == "--bot":
            bot_arg = argv[i + 1]
        elif argv[i] == "--dials":
            dials_arg = json.loads(argv[i + 1])
        elif argv[i] == "--rules":
            rules_arg = argv[i + 1]
        elif argv[i] == "--variant":
            variant = argv[i + 1]
        else:
            raise SystemExit(f"unknown argument {argv[i]!r}")
        i += 2
    tables = os.path.join(root, "tables") + os.sep
    seen: set = set()

    def hook(event, args):
        if event == "open" and args and isinstance(args[0], (str, bytes, os.PathLike)):
            p = os.fsdecode(args[0])
            p = os.path.abspath(p)
            if p.startswith(tables) and p.endswith((".json", ".bin")):
                seen.add(p[len(tables):].replace(os.sep, "/"))

    sys.addaudithook(hook)
    sys.path.insert(0, root)
    out = sys.stdout
    sys.stdout = sys.stderr  # whatever the bot prints stays off the report
    from hyperion import ship
    from hyperion.core.types import Rules

    name = bot_arg or ship.SHIP
    dials = ship.DIALS if dials_arg is None else dials_arg
    bot = ship.make_bot(name, dials, 0)
    rules = Rules()
    if rules_arg:
        from hyperion.tablegen import rules_from_dict

        with open(rules_arg) as fh:
            rules = rules_from_dict(json.load(fh))
    bot.new_table(rules, 0, rules.n_players)
    short = sys.modules.get("hyperion.strategy.short")
    missing: dict = {}
    if short is not None:
        missing.update({k: "loader returned None" for k, v in getattr(short, "_TABLES", {}).items() if v is None})
        missing.update(getattr(short, "MISSING", {}))
    declared = declared_tables(name, dials, tables)
    wanted = seen | declared
    lacking = {t for t in wanted if not os.path.isfile(tables + t)}
    twist = {t for t in lacking if t.startswith("generic/")}
    lacking -= twist
    variant = variant or (rules.extras or {}).get("variant")
    if twist and variant:
        safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(variant))[:40]  # hyperion.strategy.tables
        if not glob.glob(os.path.join(tables, "generic", f"{safe}-*.json")):
            lacking.add(f"generic/{safe}-*.json")
        twist = set()
    report = {"hyperion": sys.modules["hyperion"].__file__, "bot": name, "dials": dials, "opened": sorted(seen),
              "declared": sorted(declared), "specialist_missing": missing, "lacking": sorted(lacking),
              "lacking_twist": sorted(twist)}
    print(json.dumps(report), file=out)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
