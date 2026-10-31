# hyperion

A millisecond-budget poker engine, bot sandbox and strategy tables, in pure Python. The decision path is
stdlib only and built to never time out: a 5-to-8-card evaluator that is one dict lookup, exact ICM,
preflop and flop tables regenerated from a `Rules` description of any card variant, a safe wrapper that
answers inside the budget or takes the safe action, and an 8-max sit-and-go simulator with a bestiary of
opponents to measure against. Named for the tallest living redwood.

Build contract: `docs/specs/2026-10-31-hyperion-design.md`. Calls made along the way: `docs/decisions.md`.

## Layout

| Path | What |
|---|---|
| `hyperion/core/` | cards, 5-to-8-card evaluator (one dict lookup, a few µs), equity generators, exact ICM |
| `hyperion/strategy/` | SafeBot wrapper, opponent profiler, preflop charts, push/fold with ICM gate, postflop rules, `Hero` |
| `hyperion/sim/` | 8-max SNG engine (blind schedule, ICM scoring, strict 1 ms enforcement), bestiary of likely opponents, runner with CIs and latency stats |
| `hyperion/drills/` | fake starter kits, adapter pattern, variant catalog, timed 60-minute drill |
| `tools/gen_tables.py` | regenerates every table from a `Rules` JSON in under a minute |
| `tables/` | generated JSON: preflop equity vs 1..7, 169x169 heads-up matrix, push/fold, flop textures |

## Run

```
uv venv .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m hyperion.sim --tables 1000 --seed 7 --mode strict --bots hero,tag,nit,naive,station,maniac,random,allin
.venv/bin/python -m hyperion.drills.run --variant permuted_ranks --kit b --seed 1
```

## What it does not do

Full-game CFR, neural nets, real-time search. Ruled out by the millisecond and the secret variant.
Boards above eight total cards (a discards-join-the-board rule), a real auction (the catalog's
`bonus_card` posts a fixed price), private per-seat extras (bounties are public in the sim). The engine
plays the rest of the catalog: `python -m hyperion.drills.variants --list` names 23 entries across hand
ranking, information, payoff and betting, with Rules JSON for the generator and `--variant NAME` in the sim
(`docs/decisions.md`, "Variant catalog baseline", says where Hero is weak on each).
