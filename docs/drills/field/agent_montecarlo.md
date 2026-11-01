# build_log: team "No Limit" (f2_montecarlo)

Persona: three CS students, pure Monte Carlo hand equity vs the opponents still in the hand, compared with
pot odds, pure Python, as fast as possible. Followed as briefed: no hand charts, no solver tables, no bluff
logic, no ICM. Bot is `rival_bot.py` (class `Bot(Agent)`), frozen at minute ~46 (md5 in FROZEN.md5).

## What it is
- Evaluator: table-driven 7-card eval. Non-flush hands = one dict lookup keyed by a base-5 rank-count sum
  (49,205 entries built at import); flush/straight-flush via a 13-bit suit mask table. Checked against a
  brute-force best-of-21 reference (0 ordering mismatches in 10,000 pairs). About 0.3 us per eval.
- Postflop: MC loop (`_sim`), partial Fisher-Yates dealing, stop as soon as one opponent beats us, perf_counter
  budget of 0.18 ms per decision, early stop when the estimate is 2.5 standard errors from every decision
  threshold. Opponents who raised or bet get a narrowed range by rejection sampling (top ~50% or top ~20% of
  two-card combos by heads-up equity). Equity is compared with pot odds plus a margin
  (0.06 + 0.06 * bet/pot); value-bet when strength (equity above fair share) >= 0.30; raise when >= 0.62.
- Preflop: also equity. Table of equity vs 1..7 random hands for the 169 classes (1,000 trials per class,
  simulated at import) plus two range-narrowed tables (opponent 0 drawn from top 35% / top 12%, 450 trials)
  used when facing a raise. Open when the hand is in the top X% (X from 17% to 60% depending on how many
  opponents are left, wider when short-stacked), 3-bet top ~7%, call when equity > pot odds + small margin.
  Short stacks (<= ~12 bb) shove instead of sizing.
- Safety: act() is wrapped in try/except with a legal fallback, output is clamped to legal actions and the
  raise range, hostile/None fields are tolerated (fuzz clean). `gc.disable()`, warm-up run at import.
- Import: about 1.4-2.7 s depending on machine load. RSS about 15 MB.

## Minute marks
- m0-15: evaluator, MC sim, preflop table, pot-odds decisions, own mini engine (`sim.py`) with Tag/Station/
  Maniac/Random opponents. First version had 0.55 ms budget and many timeouts under load; added early stop and
  cut budget to 0.25 ms. Range narrowing for aggressive opponents (self-play: +1.0 pt vs no narrowing).
  `snap_m15.py`.
- m15-30: range-narrowed preflop tables for facing raises (+0.4 in duels), robust history parsing, no
  pointless raises when everyone else is all-in, per-seat aggression tracking added, parameter sweeps in
  duels vs older versions of itself; call margin raised 0.02/0.04 -> 0.06/0.06 (+0.3 to +0.4, three seeds).
  `snap_m30.py`.
- m30-45: more sweeps (bet/raise thresholds, open ranges, all-in survival margin: all within noise, not
  adopted). Budget 0.6 ms vs 0.25 ms vs 0.15 ms showed no measurable difference, so budget cut to 0.18 ms.
  Per-seat style tracking lost about 0.4 pt in maniac-heavy mixes, switched off (`_STYLE_ON = False`, code
  left in). `snap_m45.py` = final file. Team stopped there (done by minute ~46; no edits after).

## Timing (honest)
The machine was heavily shared during this run (load average 11 rising to 51 on 8 cores), so wall-clock tails
are mostly scheduler noise. The kit's `_control.py` (a fixed 20 us busy loop) shows max 8.4 ms and mean 48 us
in the same conditions, and 58 of 10,000 calls over 0.7 ms.
- harness.py (wall): mean 111-134 us, median 65-70 us, p99 0.5-3.3 ms (noise), max 4-9 ms in the final runs.
  Earlier, lighter-load runs of the same code: mean 80-105 us, p99 260-490 us, max 0.4-1.6 ms.
- cpu_time.py (thread CPU time, same obs): mean 82 us, median 66 us, p99 299 us, p99.9 811 us, max 4.1 ms,
  8 of 10,000 over 1 ms.
- Own engine, 1000-table runs: about 0.1-0.5% of decisions went over 1 ms (and would auto-fold) under load,
  including preflop table lookups that do almost no work, so these are not a code path. Expect rare timeouts
  on a busy grader; on a quiet box the budget (0.18 ms + setup) leaves a wide margin.

## Results in own engine (weak/medium opponents, not the real field)
Avg points per table (10/7/5/4/3/2/1/0, cap ranked by stack): about 6.8-7.7 against mixes of Tag/Station/Maniac/
Random bots (a copy of each of a few simple bots), 4.5-5.1 against 7 Tag bots (equal skill = 4.0). In duels
(4 copies vs 4 copies of its own earlier versions) the final version beats the first by about 0.6 pt.

## Known weaknesses
- No ICM and no position model. The only position sense is "how many opponents are still in the hand".
- Equity vs random or crudely narrowed ranges, not real ranges. Overcalls versus strong players, undervalues
  draws (no implied odds), ignores reverse implied odds.
- Never bluffs, never slow-plays, bet sizes are only 0.5 or 0.75 pot, so a tight solver reads it easily.
- All-in opponents are treated like any other opponent (no side-pot arithmetic).
- MC noise of about +/-4% on 100-200 trials near thresholds; preflop tables have about +/-1.5% error.
- Per-table opponent memory exists but is switched off; it did not help against its own sim opponents.
- Variance: shoves a lot with short stacks, so results are high variance (many 1st and many 6th-8th).
- Timeouts under load are auto-folds; a timeout with a premium hand is costly.

## With more time
Real ICM at the cap and on the bubble, a proper preflop 3-bet/4-bet range model, weighted opponent ranges
from betting lines, bluffs and check-raises, draw implied odds, vectorised equity (precomputed flop textures),
a calibrated per-decision CPU budget measured on the grader, and a test against a real solver-like opponent
instead of our hand-written Tag/Station/Maniac bots.
