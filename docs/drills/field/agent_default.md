# Build log: f1_default (two CS students, "build the strongest bot you can", no strategy direction)

Frozen: `rival_bot.py`, md5 cd47da88b88071e7e1e7665aea06db41 (see FROZEN.md5). Stopped at about minute 46 of 60.

## What I built
A rule-based tight-aggressive bot. No solver, no precomputed tables, no Monte Carlo (1 ms is too tight in pure Python).
- Own 7-card evaluator (bitmask straight table, checked against brute-force best-of-5 on 3,000 random hands).
- Preflop: Chen-formula hand score. Open-raise thresholds by seats still to act (UTG about 9, button about 5.5, heads-up
  button very wide), 2.5-3x sizing plus 1 BB per limper, 3-bet with JJ+/AK (a bit wider vs loose raisers, plus about 10% suited
  3-bet bluffs vs late-position opens), call by score with adjustments for raise size, raiser position, and being in the big
  blind. 4-bet or jam with QQ+/AK. Push/fold at 10 BB or less effective (threshold grows with stack depth and seats behind).
  Calling a shove uses equity-vs-random (Chen fit) scaled by an estimate of how wide the shover's range is.
- Postflop: classify made hand (top/middle/bottom pair, overpair, two pair, set, straight, flush, boat) and count draw outs
  (flush draw, straight draw, overcards), turn that into an equity number, discount it for multiway pots, bet size relative to
  the pot, board wetness and stack commitment. Value bet at 0.55-0.7 pot, c-bet about 60% heads-up as the preflop raiser,
  semi-bluff draws, a few river bluffs, a stab when checked to in position, pot-odds calls with a margin, raise for value
  with 0.85+ equity.
- Light opponent tracking from `history`: per seat preflop raise rate, VPIP, raises per hand. Used to widen or tighten calls
  against raisers, to call shoves more against loose-aggressive seats, to call lighter vs maniacs, and to stop bluffing seats
  that look like calling stations.
- Safety: `act()` wraps everything in try/except, and `_safe()` repairs any action to a legal one (never folds when check is
  legal, clamps raise amounts, tolerates swapped min/max raise, None fields, list-vs-set legal).

## Timeline
- min 0-4: read brief and kit, first full version of the bot (preflop + postflop + tracking), harness/fuzz clean.
- min 4-10: wrote my own 8-handed SNG engine (side pots, blind schedule, 200-hand cap, ICM scoring at the cap), a pool of 7
  opponent types (random, station, rock, maniac, shover, Monte-Carlo-equity bot, limp-folder), and a bench script.
  Bot scored about 6.0-6.3 points per table vs a 4.5 baseline.
- min 15 (snap_m15): first benchmarked version; BB option raise, limp rules, thresholds.
- min 15-30: heads-up widening, station detection, push/fold ranges, blind-post-robust history parsing, recalibrated the
  preflop equity fit and range factor (helped vs shover-heavy fields).
- min 30 (snap_m30), min 30-45: tried looser opens (-1 Chen point): no measurable difference, kept the tighter ones.
  Min-raise defence tweak. Tested 2-8 player tables for exceptions or repaired actions (none).
- min 45 (snap_m45 = frozen file).

## Local results (my own engine, not the real one; noise is about +-0.15-0.25 points)
Points per table: about 6.0-6.3 vs the mixed pool, 6.2-6.3 vs 4 MC-bot + 3 rocks, 5.6-5.9 vs shovers/maniacs/stations,
about 7.5 vs stations and limp-folders. Won about 37% of tables vs the mixed pool. Against a strong field this is a
decent tight-aggressive bot, not a winner.

Harness: 0 exceptions, 0 illegal actions, 0 folds when check was legal. fuzz.py: 0 exceptions, 0 illegal. About 20 us
median per decision, 55-150 us at p99. The occasional 1-10 ms max is machine noise (the 20 us busy-wait control bot shows
the same spikes on this shared machine), not something the bot does.

## Known weaknesses
- No Monte Carlo or range-vs-range equity; postflop equity is a coarse bucket plus outs heuristic. Over-folds to big river
  bets, under-values backdoor draws, ignores blockers.
- Opponent model is shallow (rates only, partial because `history` is only visible when I act). No fold-to-c-bet, no
  postflop-street split of aggression.
- No ICM or bubble awareness beyond push/fold. Does not adapt strategy near the 200-hand cap.
- No check-raises, no slowplay except 12% on strong hands, bet sizes are few and predictable (a good solver can exploit).
- Preflop ranges are Chen thresholds, not solved charts: 3-bet and call ranges are guesses. Sets and suited connectors under-played.
- Tuning was done against my own guessed opponent pool with noisy A/B tests, so thresholds are principled, not fitted.

## With more time
Build a proper equity engine (precomputed preflop equity tables, fast postflop equity buckets by hand class), replace Chen with
a ranked 169-hand chart per position, add per-street opponent stats (fold to c-bet, check-raise, river aggression), ICM-aware
jam/call thresholds for the last 25 hands and when 4-5 players are alive, self-play tune thresholds with several thousand
tables per variant, and add a deliberate mixed-strategy layer (randomized sizing and checks) so it is harder to exploit.
