# Build log: rival_bot.py (o2_selfplay)

Persona: a solo student driving a coding agent. "Build a decent bot fast, build a local simulator
with a pool of opponents, iterate, keep whatever scores best." I wrote all the code here myself
(stdlib only) and read no files outside D.

Frozen at minute 44.8. md5 `5e739fa4f8f1833d2ea7212a28ef9aef` (FROZEN.md5). snap_m45.py was saved at
minute 44.8 and is byte-identical to the frozen bot.

## What was built
- `evalcore.py`: a fast 5-7 card evaluator (bitmask straights/flushes, about 2 us per 7-card hand). It is inlined in the bot.
- `gen_pre.py`, `gen_rng.py`: offline Monte Carlo over the 169 preflop classes, giving equity vs 1 and
  3 random hands and HU equity vs top-100/50/30/15/7% ranges, plus each class's percentile.
  This is embedded in the bot as a string blob (`table_blob.txt`). Import takes about 0.01 s.
- `engine.py`: an 8-max NLHE sit-and-go engine with 2000 chips, blinds 10/20 rising every 25 hands
  on the brief's assumed schedule, a 200-hand cap, side pots, bust-order places, 10/7/5/4/3/2/1/0
  points, and exact Malmuth-Harville ICM (subset DP) for whoever is alive at the cap.
- `opps.py`: the opponent pool. random-legal, random-caller, calling station, maniac, rock (MC), TAG (MC),
  LAG, push/fold, equity-vs-random bot, limper, and self-play snapshots (v1 = first loose version,
  m15, cur).
- `run.py`: plays N tables with 7 opponents drawn from the pool. Every candidate plays the same seeds,
  the same seat and the same opponents (common random numbers), and the output is mean points and
  the paired difference with its SE.

## Strategy (final)
- Preflop, unopened: at 13 BB effective or less, push/fold. Push if the hand percentile is at most
  10/(effBB*(players_behind+0.5)^0.8). Deeper, open-raise to 2.5 BB with position-dependent top-X%
  ranges (40% SB ... 11% UTG). The bot limps or completes the SB only with cheap, deep, mid-strength hands.
- Preflop vs a raise: the raiser's range width is 2x their observed (smoothed) raise rate. Equity
  comes from the range table. When committed (big raise or eff <= 20 BB), the bot calls or shoves only
  if equity >= pot odds + 0.35, which is very tight for ICM and survival. Deep, it 3-bets the top 3.5%
  (wider vs loose raisers), flats the top 12% and set-mines small pairs.
- Postflop: time-boxed Monte Carlo equity (140 us of wall time) vs every live opponent. Each
  opponent's hand is rejection-sampled from a range set by what they did this hand: raisers get a
  narrow range, callers a medium one. The bot value-bets 0.7 pot at equity >= 0.62 and shoves at low
  SPR. It c-bets 30% of the time HU when it was the preflop aggressor. Facing a bet, it subtracts a
  tightness penalty (up to 0.4) when the bettor is passive, calls if adjusted equity >= pot odds + 0.18,
  and raises at 0.78 or more.
- Safety: every path legalizes the action, with fallbacks to check/fold on exception. GC is paused
  during act().

## Timeline (minutes from T0)
- 0-4: read the brief and wrote the evaluator (1.8 us/eval). Generated the preflop table, then the
  equity-vs-range table.
- 4-8: wrote the engine (ICM, side pots) and bot v1. The harness ran clean, with max about 480 us.
- 8-9: wrote the opponent pool and runner. A first 200-table run gave rival 6.36, tag 5.93, rock 6.69 and eqbot 5.00 from the same seat. The average is 4.0 pts.
- 9-14: tightening sweeps (below). Adopted call_margin .18, tight_pen .4, pre_margin .25 then .35, cbet .3.
  Saved snap_m15 at 14.1 and added v1/m15 self-play bots to the pool.
- 14-20: risk-scaled margins (no gain, kept off) and push width (inconclusive). The diagnostic showed
  that in our pool we rank first (6.77) ahead of m15 (6.42), v1 (5.25), tag/rock (about 5.1),
  random/maniac/station (1.1-1.7).
- 20-30: fold-rate-aware steals, thin value, bet size, open size, 3-bet width and call width were
  all noise or negative, so I kept the base. Built a tough pool (no random/maniac): wider pushing
  (push_c 10) gave +0.33 there and +0.09 in the full pool, so I adopted it. Saved snap_m30 at 29.9.
- 30-37: latency work. The host load average was 3.5-7, and the trivial 20 us control bot itself
  spiked to 0.4-1.4 ms, so the spikes come from the host. I cut the MC budget 250 to 140 us,
  computed the river hand once and paused GC in act(). Harness mean is about 100-120 us, p99 about 200-500 us
  depending on host load.
- 37-44: limp on/off, c-bet 0/.55, commit threshold 13 BB and push_c 11 were all within noise, so
  nothing changed. Final validation, then I froze at 44.8 rather than tweak noise.

## Local test results (paired diffs vs the then-current bot; SE in parentheses; 400 tables unless noted)
- call_margin .03 to .08 + tight_pen .12 to .2: +0.36 (0.14). Adopted.
- call_margin .13 / tight_pen .3: +0.49 (0.13). Adopted. Then .18/.4: +0.21 (0.12). Adopted.
- preflop commit margin .15 to .25: +0.33 (0.14). Adopted. .05: -0.43 (0.14). .35: +0.23 (0.14). Adopted.
- push_c 6: -0.07 / -0.02. push_c 10: +0.08 (0.13), +0.09 (0.13) full pool, +0.33 (0.17) tough pool. Adopted.
  push_c 12: -0.07 (0.12).
- risk-scaled margins: -0.13 (0.11) / +0.05 (0.13). Not adopted.
- open ranges x0.75: -0.19 (0.12). v_bet .55: -0.15 (0.12). bet_frac 1.0: -0.10 (0.13).
  3-bet 6%: -0.18 (0.13). call_pct .06/.2: about 0. fold_adj, thin_adj: about 0 or negative.
- MC budget 170 vs 250 us: +0.22 (0.14). 110 us: -0.16 (0.15). Settled on 140 us.
- Final, full pool: current vs snap_m30 +0.30 (0.135) and vs snap_m15 +0.35 (0.16). Pool without self-copies
  (incl. random/station): current 6.76, m30 6.70, m15 6.70, diffs about -0.06 (0.14), so it is a tie.
- Noise: the per-table SD of points is about 2.7-3.3. At 400 paired tables the SE of a difference is
  about 0.11-0.15, so anything under about 0.25 is noise. Late-session gains are not distinguishable
  from zero. The robust finding is "tight beats loose" in every pool, including the tough one
  (loose preflop/postflop margins: -0.55 (0.20)).
- Caveat: the pool is ours. The real field and blind schedule may differ. The weak-bot share of our pool
  probably rewards tightness more than a field of solvers would.

## Final harness (harness_final.txt)
module=rival_bot n=2000 import=0.01s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=97.2 median=150.6 p99=194.7 max=312.2
