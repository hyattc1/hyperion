"""Solo Hold'em (drill 10, kit H) as a variant file: a ranking twist, one hole card and four board cards at showdown.

Kit H's rule (docs/drills/drill10/kitH-README.md, section 1): "Your hand is the best five-card poker hand made of
exactly ONE of your two hole cards and exactly FOUR of the five board cards." The usual categories, the wheel, suits
never rank; nobody plays the board, a pocket pair is one card, and a flush needs four board cards of the suit. That is
Rules.must_use_hole = 1, which the engine evaluates exactly (every one-card choice with every four of the board), so the
hooks are the identity's: no engine change, no hook.

What it moves (the night's FIT VERDICT, docs/drills/drill10/NIGHT.md): every equity table (the preflop order turns
over: AA is 55th of 169, TT 149th, 22 last; AKo and A9o first; suited slightly worse than offsuit), so the variant set
is regenerated (tables/variants/solo/, below), and Hero's must-use path, which before H6 checked or folded every flop:
the flop has three board cards and the hand must take four. Hero now reads the flop by what the river can still make of
it (Postflop.read_short, Config `mu_short_board`, H6), the general form of the drill 10 player's `hero.solo_flop`.

tables/variants/solo/ is the drill 10 player's set, generated under load (tools/gen_tables.py's loaded-box numbers, as
its meta.json records): preflop 3,000 samples a class, the heads-up matrix 50 samples a pair, push/fold re-solved from
it, flops 2 per texture with 300 holdings; 284 KB. tables/generic/ holds the generic aware bots' table for these rules
(hyperion/sim/generic.py's prepare; built on first use).

    .venv/bin/python -m hyperion.sim --field realistic@ship --variant hyperion/drills/solo_example.py:variant
    .venv/bin/python -m hyperion.sim.generic --prepare hyperion/drills/solo_example.py:variant
    .venv/bin/python tools/climb_accept.py --stages aware --aware generic:hyperion/drills/solo_example.py:variant \\
        --base '{"dials": {"hero.mu_short_board": false}}' --cand '' --set 10000:10100 --workers 2

Kit H's other rules are Rules, not hooks: its blind schedule (10/20 ... 250/500, 25 hands a level), points
13/8/5/3/2/1/0/-2 (last place loses two), and survivors at the 200-hand cap placed by chip count
(Rules.extras["cap_places"] = "chips"). Differs from kit H, all minor: the first button is seat `rotation` (kit H: a
random seat); busting players who started the hand with exactly the same stack get the seat order (kit H: they share
the places); the bot answers in-process (kit H: its own process on JSON lines, every message on a 1 ms clock; see
hyperion/drills/process_entry_template.py).
"""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks

KIT_H_BLINDS = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
KIT_H_POINTS = (13, 8, 5, 3, 2, 1, 0, -2)


def solo_rules(named: bool = True) -> Rules:
    """Kit H's table rules; `named` adds Rules.extras["variant"] = "solo" (Hero's tables/variants/solo/ and the generic
    bots find the set and the hooks by it)."""
    extras = {"cap_places": "chips"}
    if named:
        extras = {"variant": "solo", **extras}
    return Rules(must_use_hole=1, blind_levels=KIT_H_BLINDS, payouts=KIT_H_POINTS, extras=extras)


def variant() -> Variant:
    return Variant(
        name="solo",
        summary="Solo Hold'em (kit H): the best five-card hand of exactly one hole card and exactly four of the five "
                "board cards. A pocket pair is one card, nobody plays the board, a flush needs four board cards of "
                "the suit.",
        rules=solo_rules(named=True),
        breaks="Every equity table (a pocket pair is one card: AA 55th of 169, 22 last; ace-x offsuit on top), so the "
               "preflop tables, the heads-up matrix and push/fold are regenerated. The flop has no five-card hand "
               "(three board cards, four needed): Hero's must-use path checked or folded every flop until H6's "
               "short-board read. A board pair is everyone's pair; one hole card can pair only one rank.",
        checklist=("tables/variants/solo (committed; python tools/gen_tables.py --rules <these rules> --preset loaded "
                   "--out tables/variants/solo/ to rebuild)",
                   "Hero: Config mu_short_board (on by default) reads the flop by what the river can make"),
        tables_to_rerun=("preflop_equity", "preflop_rank", "hu_matrix", "pushfold_hu", "flop_strength"),
        hooks_factory=VariantHooks,
        needs_engine=False,
        axis="ranking",
        tables="regenerate",
        tables_note="the drill 10 player's loaded-box set: preflop 3,000 samples, matrix 50 a pair, flops 2 a texture",
    )
