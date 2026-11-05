"""Generate docs/packet/CONTRACTS.md from the code, so the API card the agent reads on the night
cannot go stale. `python tools/apicard.py` rewrites it; `python tools/apicard.py --check` exits 1 if
the committed file differs (a test calls this)."""
from __future__ import annotations

import dataclasses
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion import ship  # noqa: E402
from hyperion.core import types as T  # noqa: E402
from hyperion.drills.adapter import Adapter  # noqa: E402
from hyperion.hybrid.bot import HybridConfig  # noqa: E402
from hyperion.hybrid.dials import Rival3Knobs  # noqa: E402
from hyperion.strategy.exploit import ShippedExploitParams  # noqa: E402
from hyperion.strategy.hero import Config  # noqa: E402

OUT = ROOT / "docs" / "packet" / "CONTRACTS.md"

COMMANDS = [
    ("Run tests (the day)", "python -m pytest -q"),
    ("The night's tests: adapter, conformance, pack, switch and templates (about a minute at load 18)",
     "python -m pytest -q -p no:cacheprovider -m night"),
    ("The ship bot (see the switch) vs realistic field, strict 1 ms", "python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship"),
    ("Same, duplicate-dealt (seating luck cancels)", "python -m hyperion.sim --tables 40 --rotate --seed 11 --mode strict --field realistic@ship"),
    ("A window's recipe, measured (prompt 06: paired against the bot we ship, the night field, tonight's rules)", "python tools/climb_accept.py --stages window --base '<kept>' --cand '<kept>+passive' --rules submission/rules_tonight.json --workers 4"),
    ("A recipe or dials in a sim run (same seed without it is the before)", "python -m hyperion.sim --tables 300 --seed 11 --mode model --field realistic@ship --dials passive"),
    ("Keep dials in the switch / print it", "python -m hyperion.ship --set survival+passive   |   python -m hyperion.ship"),
    ("Hero instead (the base until 2026-11-01)", "python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic   (and --bot hero on pack, gate, latency)"),
    ("Pack the upload (records the bot; --bot cheap at Stage 2)", "python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py submission/rules_tonight.json"),
    ("Check the zip plays as the source does, decision for decision (the freeze; about 90 s at 3 workers)", "python tools/zip_parity.py dist/submission.zip"),
    ("Gate the zip against the same bot in-sim", "python tools/gate.py dist/submission.zip --kit a|b|c|d --tables 100 --rules rules_tonight.json"),
    ("Decision latency of the ship bot", "python tools/latency.py --n 2000 --rules rules_tonight.json"),
    ("Regenerate every table for a variant", "python tools/gen_tables.py --rules rules_tonight.json --out tables/"),
    ("List variant presets / write a rules JSON", "python -m hyperion.drills.variants --list   |   --rules NAME --out rules_NAME.json"),
    ("Timed drill against a fake kit", "python -m hyperion.drills.run --variant NAME --kit a|b|c|d --seed 1"),
    ("The rebuilt action log: precision and recall on sim tables / what it wins back",
     "python -m hyperion.drills.infer_eval --check 20 --fields realistic --bots ship   |   "
     "--fields realistic --bots hero --cases nolog,infer,full --seeds 50 --rotate"),
]


def _fields(cls) -> list[tuple[str, str, str]]:
    out = []
    for f in dataclasses.fields(cls):
        if f.default is not dataclasses.MISSING:
            d = repr(f.default)
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[attr-defined]
            d = "(factory)"
        else:
            d = "required"
        ann = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type))
        out.append((f.name, ann, d))
    return out


def _table(rows, header=("field", "type", "default")) -> str:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    last = len(header) - 1
    for r in rows:
        lines.append("| " + " | ".join(f"`{c}`" if i < last else str(c) for i, c in enumerate(r)) + " |")
    return "\n".join(lines)


def _config_rows(cfg_cls, prefix="") -> list[tuple[str, str, str]]:
    rows = []
    for f in dataclasses.fields(cfg_cls):
        if dataclasses.is_dataclass(f.type if not isinstance(f.type, str) else None):
            rows += _config_rows(f.type, prefix + f.name + ".")
            continue
        if f.default_factory is not dataclasses.MISSING and dataclasses.is_dataclass(f.default_factory):  # type: ignore
            rows += _config_rows(f.default_factory, prefix + f.name + ".")  # type: ignore
            continue
        d = repr(f.default) if f.default is not dataclasses.MISSING else "(factory)"
        if len(d) > 60:
            d = d[:57] + "..."
        rows.append((prefix + f.name, d))
    return rows


def _methods(cls) -> list[str]:
    out = []
    for name, fn in inspect.getmembers(cls, inspect.isfunction):
        if name.startswith("_") and name != "__init__":
            continue
        try:
            sig = str(inspect.signature(fn))
        except (TypeError, ValueError):
            sig = "(...)"
        doc = (inspect.getdoc(fn) or "").split("\n")[0]
        out.append(f"- `{name}{sig}`" + (f": {doc}" if doc else ""))
    return out


def render() -> str:
    parts = ["# CONTRACTS: the API card", "",
             "Generated by `python tools/apicard.py` from the code. Do not edit by hand.", "",
             "Cards are ints `rank*4 + suit`, rank 0 = deuce ... 12 = ace, suits c d h s = 0..3. "
             "`parse_cards('Ah Kd')` and `cards_str(...)` convert. Strategy never sees a kit; one `Adapter` "
             "subclass translates both ways. `Action.raise_to(amount)` is a raise-TO total for this street, "
             "never an increment. `obs.pot` excludes this street's bets; `obs.total_pot` includes them. "
             "`obs.position()` is 0 for first to act postflop, n-1 for the button; `obs.stack_bb` is my stack in big blinds.", ""]
    parts += ["## Observation (what strategy sees, one per decision)", "", _table(_fields(T.Observation)), ""]
    parts += ["## Action", "", _table(_fields(T.Action)),
              "", "Kinds: " + ", ".join(k.value for k in T.ActionKind) + ". `action.clamp(obs)` returns a legal "
              "version (raise clamped to [min_raise, max_raise], else call, else check, else fold).", ""]
    parts += ["## Rules (the variant, passed to everything)", "", _table(_fields(T.Rules)), ""]
    parts += ["## Bot protocol", "", "`new_table(rules, seat, n_players)` · `act(obs) -> Action` · `hand_end(result: HandResult)`", ""]
    parts += ["## Adapter (the only code written on the night)", ""] + _methods(Adapter) + ["",
              "Reference adapters for four fake kits live in `hyperion/drills/adapter.py` and `hyperion/drills/fakekits/*/RUBRIC.md` "
              "lists the gotchas each one covers.", "",
              "`history_source` says what the kit shows of the betting: `\"log\"` (its full action log, passed as `history`), "
              "`\"partial\"` (some actions, merged), `\"bets\"` (none). For the last two `decide` rebuilds the hand's log from "
              "the states (`hyperion/drills/infer_history.py`: each seat's in-hand flag, stack and bet between our decisions, "
              "replayed through the betting order; every entry happened; a state it cannot settle ends the log for the hand). "
              "`hand_end` adds our last reply and the folds after it that the kit's `deltas` / `final_stacks` / `showdown` "
              "settle; with only our chip change it holds the hand end for the next hand's first state "
              "(`defer_hand_end`, `hold_all`). The sim seat that sees what such a kit gives is `InferSeat(bot)`.", ""]
    parts += ["## The ship bot (`hyperion/ship.py`, the switch)", "",
              f"`SHIP = {ship.SHIP!r}`, "
              f"`DIALS = {ship.DIALS!r}`. The submission entry builds it with "
              "`hyperion.ship.make_bot()`; `tools/pack.py` records the bot and dials it packed in the package's copy "
              "of that file and `tools/gate.py` pairs the zip against the same bot in-sim; `tools/latency.py` and "
              "`python -m hyperion.sim --field <field>@ship` measure it. Every tool takes `--bot NAME` and "
              "`--dials JSON`; `--bot hero` restores Hero, `--bot cheap` is Stage 2's Hero.cheap(). Names: "
              + ", ".join(f"`{n}`" for n in ship.BUILDERS) + ".", "",
              "hybrid3_x (and the composite's base) is rival 3's decision core plus the exploit layer behind Hero's "
              "shell (adapter, Rules, rank "
              "remap, variant decisions, SafeBot). The core makes about 97% of plain hold'em decisions; Hero plays "
              "the 14 tables the core cannot represent (short deck, lowball, wild cards, hi/lo, two boards, "
              "must-use, three or more hole cards, fixed limit, bounties, exposed cards) and the straddle preflop. "
              "So Hero's Config keys move hybrid3_x only there: on hybrid3_x they are written `hero.<key>`, and a "
              "bare Hero key is an error.", "",
              "The composite (`hyperion/compose/`, the ship bot since the decisions entry \"Composite bot\") plays that "
              "base preflop and Hero postflop and when it faces a raise short (under 20 bb effective, four or more "
              "players), with the layer in front of both; with no dials it is the measured composite "
              "(`hyperion.compose.bot.SHIP_DIALS`: the route, `exploit.bet_min_fold` 0.4, `hero.postflop.call_margin` "
              "0.2). Its dials: `route` (\"section=donor,...\"), `r3.<name>` for the base's core, `exploit.<field>`, "
              "`hero.<key>` (the hero member and the base's fallback Hero, as on hybrid3_x), `cheap`, `light`.", ""]
    parts += ["## Recipes (the night's dials by name: `--dials survival`, stacked `survival+passive`)", "",
              "Each resolves for the bot the switch names: on the composite its own (the core's preflop dials, the "
              "exploit layer's keys and Hero's as `hero.<key>`: rival 3's core plays only preflop there and one layer "
              "sits in front, so the core's postflop dials and Hero's `exploit.*` keys would reach nothing); on "
              "hybrid3_x and hybrid3 the core's dials plus Hero's as `hero.<key>`; on Hero its Config keys. "
              "`slow_box` (the governor) is in the composite's defaults; it gives the fallbacks theirs.", "",
              _table([(n, repr(ship.COMPOSITE_RECIPES[n]), repr(ship.CORE_RECIPES[n]), repr(ship.HERO_RECIPES[n]))
                      for n in ship.HERO_RECIPES], ("recipe", "composite (ships)", "hybrid3_x, hybrid3", "Hero")), ""]
    parts += ["## Dials of rival 3's core bots (one flat dict: `--dials '{\"r3.open_scale\": 1.2}'`)", "",
              "Rival 3's core, `r3.<name>` (defaults are rival 3 as built, bit for bit):", "",
              _table([("r3." + f.name, repr(f.default), f.metadata.get("doc", ""))
                      for f in dataclasses.fields(Rival3Knobs)], ("key", "default", "meaning")), "",
              "The exploit layer, `exploit.<name>`; hybrid3_x carries Hero's params (below; `{\"exploit\": null}` turns "
              "the layer off):", "",
              _table([("exploit." + n, d) for n, d in _config_rows(ShippedExploitParams)], ("key", "hybrid3_x")), "",
              "The shell, flat keys (hybrid3_x sets `core` 'rival3' and `exploit` 'hero'; `cheap: true` = every "
              "decision Hero's cheap path, the timeout dial):", "",
              _table([(n, d) for n, d in _config_rows(HybridConfig)
                      if n.split(".")[0] not in ("hero", "r3", "seed", "core", "exploit")], ("key", "default")), "",
              "The fallback Hero: `hero.<key>` for any key in the next table.", ""]
    parts += ["## Config keys (Hero: the dials of `--bot hero`, `hero.<key>` on hybrid3_x; `hero.config_from_dict({'a.b': v})`)", "",
              _table(_config_rows(Config), ("key", "default")), ""]
    parts += ["## Commands", ""] + [f"- {what}: `{cmd}`" for what, cmd in COMMANDS] + [""]
    parts += ["## Entry points", "",
              "- `hyperion.ship.make_bot(name=None, dials=None)` -> the bot we ship (SHIP with DIALS; what the entry builds). `make_bot('cheap')` = `Hero.cheap()`.",
              "- `hyperion.strategy.hero.make_bot(config=None)` -> Hero (SafeBot-wrapped). `Hero.cheap()` -> the 15-minute fallback.",
              "- `hyperion.strategy.tables.load(tables_dir)` -> preflop tables; `hyperion.strategy.pushfold.load_pushfold(tables)`.",
              "- `hyperion.core.eval.evaluate(cards)` -> int strength, higher is better, 5 to 8 cards.",
              "- `hyperion.core.icm.icm_equity(stacks, payouts)` -> expected points per seat (never call in act()).", ""]
    return "\n".join(parts)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    text = render()
    if "--check" in argv:
        if not OUT.exists() or OUT.read_text() != text:
            print("CONTRACTS.md is stale; run python tools/apicard.py", file=sys.stderr)
            return 1
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)
    print(f"wrote {OUT} ({len(text)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
