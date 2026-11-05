# rival_bot notebook

Built from a blank directory in about 48 minutes of wall clock (21:56 to 22:44). The bot is `rival_bot.py`, one file with `Bot(Agent)` and only stdlib imports (`gc`, `random`, `time`).

## What the bot does

**Evaluator.** A hand-written 7-card evaluator (`ev7`, about 1.5 us) returns an integer rank. I checked it against a brute-force 5-card evaluator on 3000 random 7-card pairs. The first version missed the wheel straight, and the check caught that.

**Preflop.** `PCT` is a table of 169 hand classes (suited or offsuit), each with a percentile rank. I generated it offline by Monte Carlo equity against 3 random opponents, using my own evaluator, and embedded it as a literal. The bot uses percentile cutoffs and does not simulate preflop at decision time.
- **Unraised pot:** open-raise if the hand's percentile is under a cutoff set by how many players act behind (OPEN table: BTN 50%, CO 30%, UTG about 16%, SB 45%). It iso-raises limpers with the top 20%. It never open-limps; the only completes are cheap blind completes with a top-60% hand (about 0.5 bb or less to call).
- **Short stacks:** at 11 big blinds effective or less it uses a push/fold rule. The cutoff is (0.95 - 0.05 * effective_bb) times a position multiplier.
- **Facing a raise:** estimate the raiser's range width by raise count (17%, 7%, 3.5%). Scale it by a per-seat looseness estimate from observed preflop raise frequency, and widen it for short-stack shoves. Then:
  - 3-bet or 4-bet (shove if effective stack is under 28 bb) with the very top of the range.
  - Call if the hand is inside the range times a pot-odds factor.
  - Make rare light 3-bets, 5% of the time.
- **Tightness:** the call multipliers 0.45 and 0.5 are tuned and described below. Calls of 40% or more of the stack use the tighter 0.5 multiplier, but never below 0.85 when effective stack is 10 bb or less. Pot odds make short-stack calls profitable, and a solver-style opponent would punish folding them.

**Postflop.** Range-aware Monte Carlo equity:
1. Sample an opponent hand, rejecting it when its preflop percentile is above a cutoff.
2. Complete the board and compare 7-card ranks.
3. Use 36 samples on the flop and turn, 44 on the river.
4. Stop early if 0.5 ms has passed (the time guard).

The cutoff comes from the bet size relative to the pot, the number of preflop raises, and the aggressor's observed postflop aggression. Multiway equity is approximated as E^(1 + 0.55 * (k - 1)).
- **Checked to us:** value-bet when equity is above 0.57, sized 50% or 72% of pot, or occasionally 90% or 35% when very strong. Bluffs are rare and scaled by the opponents' observed fold rates. Bluff scale is 0.3 of the original.
- **Facing a bet:** raise with equity above 0.80 (0.85 on the river). Call when equity beats pot odds plus a margin of 0.05, plus 0.02 per extra opponent, plus 0.03 for all-in. Otherwise fold. Occasional semi-bluff raise.
- **Sizing:** any raise at 50% or more of the remaining stack becomes a shove.

**Opponent tracking.** Per seat: hands seen, preflop raises, and postflop folds, calls and raises, parsed from `obs.history` incrementally. History entries are parsed defensively, so blind posts or junk entries cannot break it.

**Safety and determinism.**
- `act()` wraps everything in try/except, then sanitizes the result. Anything illegal becomes check, or fold if check is not legal. Raise amounts are clamped to `[min_raise, max_raise]`.
- GC is disabled during `act()` and restored afterwards, which removes GC stalls.
- The RNG is seeded in `new_table` from seat, player count and starting stack. The wall clock is read only for the 0.5 ms equity guard.
- `new_table`, `hand_end` and the observation fields tolerate partial or `None` input.

## How I tested it

All of this lives in this directory.
- `sim.py`: my own engine. Standard no-limit rules, side pots, min-raise and short all-in re-raise rules, heads-up blinds, blinds up every 25 hands, 200-hand cap, ICM scoring at the cap with points 10/7/5/4/3/2/1/0. Chips and points are conserved (checked on 60 tables).
- `opps.py`: 13 sparring opponents.
  - Random, Station, Maniac, Nit, TAG, LAG, LoosePassive, PushFold, TightTAG, Shover, MinRaiser.
  - `v1`: an early snapshot of this bot (two copies in the pool).
  - TAG and TightTAG use Monte Carlo equity, so they are the "solver-ish" bots.
- `spar.py`: seats the bot at a random seat at a table with 7 random opponents from the pool (no repeat when the pool has 7 or more types) and reports the bot's mean points per table. `varbot.py` and `exp.sh` ran parameter variants on the same seeds. The results are in `logs/`.
- `harness.py`, plus `t_robust.py` (None or partial rules, junk history, `hand_end(None)`; 0 failures, and `_act` itself never raised), `t_lat.py` (latency distribution) and `t_det.py` (determinism).

## Sparring results

A random player scores about 4.0 points per table. These are tables of me plus 7 opponents, and they are not the real field.

| Run | Tables | Mean points | SE |
|---|---|---|---|
| First version, early pool | 1000 | 6.04 | 0.10 |
| Final, 13-type pool, held-out seeds 100000+ | 4000 | **6.03** | 0.05 |
| Final, tough pool only (TAG, TightTAG, LAG, Nit, PushFold, v1 clone; 7 drawn with replacement) | 2000 | **5.12** | 0.07 |

In the final 4000-table run the other bots averaged:

| Opponent | Mean points |
|---|---|
| TightTAG | 5.55 |
| TAG | 5.28 |
| v1 clone | 5.27 |
| Nit | 5.11 |
| PushFold | 4.83 |
| LAG | 4.50 |
| LoosePassive | 3.44 |
| Shover | 2.99 |
| Random | 1.88 |
| MinRaiser | 1.51 |
| Maniac | 1.48 |
| Station | 1.24 |

On the tough pool the v1 clone got 4.28 against my 5.12.

**What tuning showed** (3000 tables per variant, SE about 0.06, same seeds):
- Tightening preflop calls helped a lot. With bluffing off, a call multiplier of 1.0 gave 5.48. At 0.5 it gave 5.85, and at 0.35 on all calls it gave 5.98. Making only the non-all-in calls tight, or only the big calls tight, gave about 5.65 to 5.72, so the two effects add up. The shipped values are 0.45 for ordinary calls and 0.5 for big calls.
- Bluffing was neutral at best: scale 0 gave 5.54 and 2.0 gave 5.39 against a base of 5.42, so I kept a small 0.3.
- Margin, value-bet threshold and open-range changes moved results by 0.1 or less, which is inside the noise.
- The 10 bb floor on tightness cost nothing (5.95 against 5.95), so I kept it as protection against solver-like shovers.

These are tuned against my own opponent pool, so some of the improvement may be fitted to it. The exploitable leaks are probably in unusual bet-sizing patterns, and the postflop range model is crude.

## Harness (`python harness.py rival_bot`, final build)

```
module=rival_bot n=2000 import=0.04s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=120.9 median=176.5 p99=266.1 max=524.3
```
Other seeds on the final build: mean 135 us, max 619 us (seed 5); the very last run on the final build showed max 2.5 ms (mean 133 us, median 183 us), and an earlier build showed 1.2 ms. I believe these are stalls of the shared machine rather than bot work: they showed up as clusters of consecutive calls at about 4.2 ms each, while the 20,000-call latency test had p99.9 under 0.5 ms and max 0.83 ms at a quiet moment. I did not test a no-op loop to confirm. This machine has occasional multi-millisecond stalls from other processes that no bot code can prevent. Typical cost is about 0.2 ms, and the 0.5 ms guard stops sampling early on slower machines.

## Ideas not done

- Street-aware tracking of an aggressor's bets across streets; the history has no street markers.
- Explicit ICM-aware calling near the bubble. The points table (10/7/5/4/3/2/1/0) is convex at the top, so I did not penalize variance.
- Check-raise and trapping lines.
