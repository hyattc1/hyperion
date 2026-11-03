# S20: a solved three-handed preflop for strong tables (running log)

Branch climb/s20-three, from main b1c9e89 (batch 6 is F). Brief (coordinator, 2026-11-03): F trails the strong builds
three-handed and heads-up preflop at strong tables (S14: F 0.0-0.1 bb a decision there, the strong builds +0.2-0.4; F
min-raises 38-39% and folds 40-42% of those to a re-raise); K18 (elite1's play there) went up at strong tables but down
on exploit_3; S13's own three-handed tables (tables/extra/short_3.json) lose to both exploiters. Build a three-handed
preflop from our own solver that wins at strong tables and does not lose to the exploiters, as a route in the composite,
off by default.

Seeds: screen 10000-10199 (`--set screen`) and diagnostics 11000-11199 only. No judge bot, judge field, held-out set or
judge seed is run, read or tuned on here. Every screen is tools/climb_accept.py with `--runout-term` (addendum 13),
`--workers 2`, `nice -n 10`; F's chunks are computed once in a clean worktree at main b1c9e89 (code bd36043bea) and the
candidates' chunks pin F's cache key to that version (scratch `goal/s20/accept.py`, S13's wrapper), since F plays
identically behind the new dials (identity check below). Host: 8 cores, load 11-14 from other measurements.

Scratch: `goal/s20/` (the diagnostic recorder `d3.py`, the analysis scripts, the accept cache `ca/`).

## Runs (appended as each finishes)

- 13:50 F's base, screen set, stages exploit + elite, runout term (`wt_s20_main`, `--cand '{"dials": {}}' --base
  '{"dials": {}}'`, out `goal/s20/ca`): started.
- 14:05 Step 1 recordings of F on diagnostic seeds 11000-11099 (three-handed exploit cells: exploit_3, exploit2_3,
  exploit3_3, adapt_3 at 10/7/5; elite, mirror, elite_b, mirror_b at 8..1) and 11000-11059 (night): `d3.py` records
  every hand that starts with two or three alive (every decision, every seat's hole class, the deltas): started.
