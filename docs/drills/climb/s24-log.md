# S24: exploiter 5 wired in; the over-folding it found (running log)

Branch climb/s24-overfold, worktree goal/wt_s24, from main 6138ef0 (batch 8 is F). Scratch goal/s24/. Diagnostics on seeds
18000-18999 only; screen on 10000-10199 with `--aim exploit`, every stage, runout term; identity against goal/idchk39.md. Held-out
seeds 20000-59999, judge seeds 60000+ and 70000+, and the judge bots (out_*, elite5, rival4, rival5, adapt2) are not used. Workers
at most 3, nice 5.

**Where I am / next:** the rule is fixed below and committed (3d5dab6); identity passed (14 of 14); the screen is running at 3d5dab6 (goal/s24/run.sh; ends with goal/s24/RUN_DONE; goal/s24/screen.md, screen.json; re-running run.sh resumes from its cache). Then the suite, then the report.

## Part 1: exploiter 5 wired in

- Frozen copy `hyperion/sim/field/exploiter5.py` (md5 f4121d39, origin header + archive bytes), archive docs/drills/exploiter5/
  (notebook, brief, arena, bot). `Exploiter5Bot`, registry `exploiter5`; fields exploit5 (six night seats), exploit5_hu,
  exploit5_3; climb_accept's exploit stage gains the three cells, appended after exploit4_3 in the list (each cell's file is named by
  its field, so no earlier cell moves). Weighted score's adapter family: six bots, a sixth each (family weight and range unchanged).
- Clock: the bot reads perf_counter twice in act(), and the branch on it is `pass`, so play does not depend on it: no fixed clock.
  No random import. Two model-mode runs replay exactly (test). At import it does gc.freeze and raises the collector's threshold
  process-wide; the adapter puts the threshold back (here the collector is everyone's). Its env hooks (BOT_DEBUG, BOT_LOG) stay unset.
- Its arena against batch 8, before any fix (its notebook): 8-max 4.68-4.92 vs F 5.85-5.96; three-handed 2.01 vs 2.36; heads-up
  (2/1) 1.47-1.50 vs 1.51-1.54, level. F wins; that is the baseline to keep.

## Part 2: the diagnosis so far (seeds 18000-18199 at most; goal/s24/diag.py, ana.py, tab2.py, pre.py)

"F folds" is F's answer to the first bet of a street in a heads-up pot, "air" the bettor's tier 0-1, "folded W" what F's folded hands
win against the bettor's actual cards checked down (it overstates a flop call, which meets more bets), "ev" those folds called, in pots.

| seats | alive | flop: folds / air / W vs price / ev | turn | river |
|---|---|---|---|---|
| exploiter 5 | 2 | 0.87 / 0.40 / 0.38 vs 0.33 / +0.074 | 0.67 / 0.15 / +0.028 | 0.64 / 0.10 / -0.104 |
| exploiter 5 | 3 | 0.85 / 0.24 / 0.28 vs 0.31 / -0.003 | 0.82 / 0.07 / -0.048 | 0.74 / 0.07 / -0.160 |
| exploiter 5 | 6+ | 0.83 / 0.19 / 0.30 vs 0.32 / +0.054 | 0.71 / 0.02 / -0.052 | 0.77 / 0.10 / -0.189 |
| night seats | 2 | 0.78 / 0.22 / 0.21 vs 0.27 / -0.072 | 0.75 / 0.09 / -0.133 | 0.70 / 0.14 / -0.136 |
| night seats | 3 | 0.77 / 0.28 / 0.26 vs 0.26 / -0.021 | 0.77 / 0.09 / -0.083 | 0.72 / 0.11 / -0.115 |
| night seats | 6+ | 0.70 / 0.29 / 0.28 vs 0.27 / +0.012 | 0.71 / 0.11 / -0.074 | 0.63 / 0.12 / -0.066 |
| elite, elite_b, mirror | 6+ | 0.59-0.64 / 0.35-0.42 / 0.29-0.32 vs 0.25-0.27 / -0.001 to +0.036 | -0.056 to -0.015 | -0.113 to -0.052 |

- The probes' 98% turn fold is real against a bot that barrels air, but the bots that play for points do not: exploiter 5's own turn
  bets hold 2-15% air, so F's turn folds lose nothing against it. Its river bets are value (F's calls there are the leak, if any).
- The flop is where it shows, and heads-up: exploiter 5's pot-size c-bet with F out of position after calling: F folds 90% (n=3206),
  air 0.55, folded W 0.48 vs 0.33, ev +0.238. At three alive the same size holds air 0.59-0.69 (F folds 90-100%, n=490), but the bot
  sizes value 0.6-0.7 there (air 0.00, ev -0.09 to -0.13), so the seat's frequency does not separate them. At 6+ it is 47 spots.
- In the ordinary and strong rooms F's folds are right or level on every street at every table size. Those are the folds the fix must keep.

### The preflop leaks, measured in points (seeds 18200-18499 short-handed, 18200-18279 at 8-max; goal/s24/diag2.py, shove2.py, grid2.py)

- **Chips mislead here, as the brief warned.** F's folds to shoves look +2 to +16 bb per folded hand in chips against wide shovers at
  every table size. Priced in points with the base core's own ICM values and the shover's actual cards, calling every fold loses in
  nearly every cell at every table size: heads-up -0.03 to -0.14 a hand against exploiters 1, 2, 4, 5 and adapt1 (+0.07 against
  exploiter 3), three alive -0.08 to -0.30, 4-5 alive -0.17 to -0.31, 6+ alive -0.27 to -0.49. F's call-off range is about right as a
  blanket; the shove-defence numbers in exploiter 5's notebook (15-39% called) are not a blanket leak.
- **What does lose: one spot, at every table size.** F opens, a seat with about 10 bb re-shoves, F has about 35 bb and folds. F's width for
  that seat is its 3-bet read (w 0.12 on average); the seat's own rate of all-ins per chance at that depth is about 0.27, and F's folded
  hands win 0.48 at the price. A per-seat read of that rate flips 90-220 folds per 640 tables at 8-max and is worth points in every room.
- The big blind's fold to an open (47-53% at every table size, opponent or not) comes from a hard cap in the core (top half of hands);
  `r3.bb_defend` played on diagnostics: exploit_hu -0.128 ± 0.125 DOWN, nothing up (it costs, as in S2 and S11). Left alone.
- Folds to 3-bets: F's open faces a non-all-in 3-bet at 0.73 fold heads-up, 0.60 three-handed, 0.89-0.93 at 4+ alive against exploiter 5,
  the same as against night seats (0.71 / 0.85 / 0.90-0.93). No seat evidence there tells a bluff; left alone.
- A big check-raise of F's flop bet (goal/s24/xr.py): F folds 0.66-0.83 at every table size, and it should: the raiser holds air 0-7% everywhere
  (exploiter 5: 0.04-0.05; rooms 0.01-0.03), F's folded hands win 0.04-0.22 at a price of 0.25-0.34. The one exception is exploiter 2
  three-handed (air 0.62, ev +0.153, n=263). Left alone.

### How much of each leak exists, by table size (the question the brief asked)

| leak (probes' number) | heads-up | three alive | 4-5 alive | 6+ alive |
|---|---|---|---|---|
| flop big bet (61-100% folds) | **real against exploiter 5's pot c-bet: ev +0.238, air 0.55**; night seats -0.072 | exploiter 5 -0.003 (its pot size air 0.6, its 0.6-0.7 size air 0: frequency cannot split them); night -0.021 | exploiter 5 +0.058; night -0.044 | exploiter 5 +0.054 (47 pot-size spots); night +0.012; elite rooms -0.001 to +0.036, all folded W about the price before later bets |
| turn after calling (98%) | exploiter 5 +0.028, air 0.15; night -0.133 | -0.048; -0.083 | -0.051; -0.113 | -0.052; -0.074; rooms -0.056 to -0.015 |
| river (calls 78-95%) | -0.104 | -0.160 | | -0.189: value bets, no leak |
| big blind vs an open (45%) | 47-49% vs exploiter 5, r3.bb_defend costs when played | 50-51% | 53-55% | 49-52%: the same at every size, not seat-specific |
| vs 3-bet (80% to value only) | 0.73; night 0.71 | 0.60; 0.85 | 0.93; 0.93 | 0.89; 0.90: right against value, no read tells it |
| vs shoves as a blanket (15-39% called) | calling the folds costs -0.03 to -0.14 points a hand | -0.08 to -0.30 | -0.17 to -0.31 | -0.27 to -0.49 |
| a seat re-shoving short over F's open | small | small | **real in every room** | **real in every room** |
| c-bet check-raised (67-76%) | right (raiser air 0.05) | right | right | right |

So the postflop family is a heads-up leak against a seat that bets nearly every flop, and turn folds only cost after F starts calling the
flop. At full tables F's postflop folds are right. The leak that reaches 8-max is preflop and is narrower than the notebook's.

## The rule (fixed from the diagnosis on 18000-18999, before any screen; off by default; docs/drills/climb/s24-candidate.json)

**1. The shove read, `r3.sr_*` (hyperion/hybrid/core3.py; sr_scan).** Per seat: its chances (first action of a hand, no all-in before it, chips at
the hand's start at most `sr_depth` 15 bb) and its all-ins among them (a raise to at least 85% of those chips, rival 3's own count). Facing an
all-in of at most 15 bb, from one bettor (no other caller in), on a plain hold'em table with no straddle, the width of its range is at least (all-ins +
0.15 x 6) / (chances + 6), this hand's action counted, with no read before 3 chances. **Calls only**: the width only widens, and the core's own ICM
price still decides (ev_call > ev_fold + call_margin). Why width: F's width after its own open is the 3-bet read (r3 x 0.9), which says nothing about a
short stack that shoves a quarter of its hands; the seat's own frequency does.

Offline, points-valued (goal/s24/shove2.py, grid2.py, grid3.py; 18200-18499 short-handed, 18200-18279 and 18200-18239 at 8-max): each folded hand that the
read flips, valued with the core's fold / win / lose ICM points and the actual cards of the shover and of any seat that actually called behind. Points
per table, 95%, flips in brackets:

| exploit5 | exploit4 | exploit2 | exploit3 | exploit | adapt | night | night_hard | realistic | top | elite | elite_b | mirror | mirror_b | elite_night |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| +0.028 ± 0.014 (191) | +0.032 ± 0.014 (161) | +0.031 ± 0.021 (76) | +0.033 ± 0.018 (81) | +0.011 ± 0.012 (56) | +0.016 ± 0.015 (63) | +0.013 ± 0.007 (169) | +0.018 ± 0.010 (104) | +0.005 ± 0.005 (161) | +0.013 ± 0.009 (69) | +0.030 ± 0.010 (219) | +0.022 ± 0.010 (207) | +0.016 ± 0.020 (108) | +0.014 ± 0.015 (89) | +0.013 ± 0.009 (72) |

Heads-up and three-handed cells -0.001 to +0.017. 71% of the flips are F's own open re-shoved: shover about 10 bb, F about 35 bb, F's width 0.12 against the read's
0.27, F's folded hands win 0.48. The gain holds on odd and even tables separately and from prior 0.1 to 0.25, minimum 2 to 5, x0.8 to x1.25; depth 25 or 30 keeps
about half of it, so 15 is a real choice of depth and not a peak of the prior. Faster or wider settings find a little more and were not taken.

Played on diagnostics (100 seeds x 8, 18500-18599; goal/s24/q3.out): exploit3 +0.082 ± 0.076 UP, exploit5 +0.026 ± 0.083, night +0.010 ± 0.033, mirror_b +0.006 ±
0.048, exploit4 -0.020 ± 0.071, realistic -0.023 ± 0.027, elite_b -0.024 ± 0.058, elite -0.028 ± 0.052, exploit2 -0.045 ± 0.078: nothing beyond noise down, mean about
zero. Online the read flips as the offline replay said (goal/s24/chk.py on 480 tables each: night 113 flips, exploit5 119, elite 121), worth +0.0115, +0.0088 and +0.0128 a table in
first-order points. That is lower than the offline numbers on exploit5 and elite, and it is the honest size: **about +0.01 a table**, which 200-seed cells will read as level.

**2. The c-bettor read, `hero.postflop.cbr_*` (hyperion/strategy/postflop.py).** Facing the bet of the last aggressor of the earlier streets heads-up (nothing of F's in), on the flop or the
turn, with **two alive**, on a hold'em table, from a seat with at least 4 such chances whose smoothed rate (Profiler.aggr_bet_rate, flop and turn pooled, prior 0.6 worth 6) is above 0.8: F's
equity moves from the tier's proxy toward WIDE_EQUITY and its call margin toward 0.03, by the weight (r - 0.8) / 0.15, at most 1. Calls only: no raise, no bluff (S11's `cbet_from` also raises and
bluffs; it fired on exploiter 1 and elite2). It reads frequency alone because exploiter 5's pot-size bet is that bot's habit and because a real bluff-free bot does not c-bet 80%+ of flops and barrel.

Played on diagnostics, 200 seeds, 18500-18699 (goal/s24/q2.out): exploit5_hu +0.083 ± 0.060 UP; every other heads-up and three-handed cell -0.025 to +0.007, level. Flop only (`cbr_streets` 1): exploit5_hu
-0.015 ± 0.055: a flop call that folds to the next barrel pays and gets nothing, so the read must hold on the turn. From 0.75 (full 0.9): +0.022 ± 0.101, exploit_hu -0.045, so 0.8 stays; `cbet_from` 0.7 had taken exploit_hu
-0.128 ± 0.125 DOWN. At three alive it does not apply (exploiter 5's rate there, 0.54, is an ordinary seat's).

Not done, on the evidence: no change to the big blind's defence, the 3-bet defence, the turn or river outside the read, or check-raises (the table above).

## Identity

The branch with the new dials off (3d5dab6; SHIP_DIALS = batch 8) against batch 8's F (goal/idchk39/post): `climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, chunk by chunk (goal/s24/idcmp.py): **14 of 14 identical**, night 5.928, night_hard 5.735, realistic 6.265, top 5.047, matching goal/idchk39.md row for row. Exploiter 5's wiring is in that tree, so it moved none of those cells.
