# hyperion

A millisecond poker bot and training ground for Sequoia's **No Limit: A Bot Building Tournament**
(pokerbot.sequoiacap.com). Python, stdlib only on the decision path, built to never time out.
Named for the tallest living redwood.

Why it exists, what the rules force, and what wins: `docs/research/Sequoia poker bot competition prep.md`.
Build contract: `docs/specs/2026-10-31-hyperion-design.md`. Event-night checklist: `docs/night-of.md`.
Calls made along the way: `docs/decisions.md`.

## Layout

| Path | What |
|---|---|
| `hyperion/core/` | cards, 5-to-8-card evaluator (one dict lookup, a few µs), equity generators, exact ICM |
| `hyperion/strategy/` | SafeBot wrapper, opponent profiler, preflop charts, push/fold with ICM gate, postflop rules, `Hero` |
| `hyperion/sim/` | 8-max SNG engine per the official rules, bestiary of likely opponents, runner with CIs and latency stats |
| `hyperion/drills/` | three fake starter kits, adapter pattern, variant presets (MIT twists), timed 60-minute drill |
| `tools/gen_tables.py` | regenerates every table from a `Rules` JSON in under a minute |
| `tables/` | generated JSON: preflop equity vs 1..7, 169x169 heads-up matrix, push/fold, flop textures |

## Run

```
uv venv .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
.venv/bin/python -m hyperion.sim --tables 1000 --seed 7 --mode strict --bots hero,tag,nit,naive,station,maniac,random,allin
.venv/bin/python -m hyperion.drills.run --variant permuted_ranks --kit b --seed 1
```

## State as of 2026-10-31

- 194 tests pass. Hero: 0 exceptions, 0 illegal actions, p50 12 µs, p99 137 µs per decision in the engine.
- 1,000 strict-mode tables: hero 6.45 ± 0.10 points, tight-aggressive chart bot 6.44 ± 0.08, nit 6.22. Hero wins
  42% of tables but busts in 52%. It is not yet clearly better than a tight chart bot; tuning is in progress.
- Payout structure, blind schedule and Agent interface are placeholders until the kit is released.

## What it does not do

Full-game CFR, neural nets, real-time search. Ruled out by the millisecond and the secret variant.
Boards above eight total cards (MIT's discards-join-the-board rule), a real auction (the catalog's
`bonus_card` posts a fixed price), private per-seat extras (bounties are public in the sim). The engine
plays the rest of the catalog: `python -m hyperion.drills.variants --list` names 23 entries across hand
ranking, information, payoff and betting, with Rules JSON for the generator and `--variant NAME` in the sim
(`docs/decisions.md`, "Variant catalog baseline", says where Hero is weak on each).
