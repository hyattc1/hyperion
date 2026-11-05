# S24: exploiter 5 wired in; the over-folding it found (running log)

Branch climb/s24-overfold, worktree goal/wt_s24, from main 6138ef0 (batch 8 is F). Scratch goal/s24/. Diagnostics on seeds
18000-18999 only; screen on 10000-10199 with `--aim exploit`, every stage, runout term; identity against goal/idchk39.md. Held-out
seeds 20000-59999, judge seeds 60000+ and 70000+, and the judge bots (out_*, elite5, rival4, rival5, adapt2) are not used. Workers
at most 3, nice 5.

**Where I am / next:** done, not merged (the coordinator's call). Screen **ACCEPT** under `--aim exploit` at 3d5dab6; the gain is the shove read at 8-max, and the heads-up flop read did not show on the screen's seeds. Identity 14 of 14. Candidate docs/drills/climb/s24-candidate.json. Next, if taken: a held-out run on top of what it would ship with (S22's code is not on main yet; it was not screened together with this).

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

Exploiter 5's wiring against the rest of the exploit and elite stages: raw samples of the first chunk (10000-10024) of all 20 existing cells (15 exploit, 5 elite), this tree's base against batch 8's own tree (goal/wt_b8f at c758e56; goal/s24/wcmp.py): **20 of 20 identical**. No existing cell's samples moved.

## The screen: ACCEPT under `--aim exploit`

`climb_accept --base '{"dials": {}}' --cand docs/drills/climb/s24-candidate.json --set 10000:10200 --aim exploit --runout-term --stages confirm,guards,elite,exploit,aware,variants --workers 3` (goal/s24/run.sh, screen.md, screen.json; code 1a20f8df6a = the tree at 3d5dab6, 165 minutes). Corrected deltas (addendum 13), 200 seeds a cell; raw beside where it differs. Exploiters 1 to 5 and adapt1 in.

| stage | cell | F | S24 | S24 - F | | raw | exploiter F / S24 |
|---|---|---|---|---|---|---|---|
| exploit | exploit5 (8-max) | 6.008 | 6.044 | +0.036 ± 0.040 | level | +0.039 ± 0.061 | 4.468 / 4.470 |
| | exploit5_hu | 8.522 | 8.518 | -0.004 ± 0.041 | level | +0.000 ± 0.059 | 8.425 / 8.425 |
| | exploit5_3 | 8.271 | 8.269 | -0.002 ± 0.030 | level | -0.020 ± 0.055 | 7.193 / 7.240 |
| | exploit4 (8-max) | 5.622 | 5.703 | **+0.080 ± 0.054** | **UP** | +0.081 ± 0.068 UP | 5.272 / 5.171 |
| | exploit4_hu / _3 | | | +0.007 ± 0.016 / +0.009 ± 0.022 | level | | |
| | exploit (8-max) / _hu / _3 | | | +0.021 ± 0.033 / +0.019 ± 0.049 / +0.021 ± 0.031 | level | | |
| | exploit2 (8-max) / _hu / _3 | | | +0.001 ± 0.036 / +0.009 ± 0.021 / -0.009 ± 0.021 | level | | |
| | exploit3 (8-max) / _hu / _3 | | | +0.031 ± 0.040 / +0.005 ± 0.019 / +0.004 ± 0.023 | level | | |
| | adapt (8-max) / _hu / _3 | | | +0.006 ± 0.036 / -0.004 ± 0.010 / -0.009 ± 0.033 | level | | |
| confirm | night | 6.015 | 6.040 | **+0.024 ± 0.020** | **UP** | +0.009 ± 0.029 | |
| guards | night_hard | 5.570 | 5.563 | -0.006 ± 0.018 | level | **-0.031 ± 0.030 DOWN** | |
| | realistic | 6.350 | 6.350 | -0.000 ± 0.015 | level | +0.002 ± 0.016 | |
| | top | 5.114 | 5.138 | **+0.025 ± 0.025** | **UP** | +0.034 ± 0.041 | |
| | night @10/7/5/4/3/2/1/0 | 6.311 | 6.326 | +0.014 ± 0.039 | level | +0.019 ± 0.059 | |
| | night @50/25/12/6/3/2/1/1 | 25.112 | 25.121 | +0.009 ± 0.288 | level | -0.035 ± 0.399 | |
| | night, doubling blinds | 5.910 | 5.911 | +0.001 ± 0.018 | level | +0.001 ± 0.030 | |
| elite | elite | 4.886 | 4.916 | **+0.029 ± 0.024** | **UP** | +0.050 ± 0.037 UP | |
| | elite_b | 4.684 | 4.721 | **+0.037 ± 0.025** | **UP** | +0.043 ± 0.040 UP | |
| | mirror | 4.484 | 4.510 | **+0.026 ± 0.026** | **UP** | +0.027 ± 0.038 | |
| | mirror_b | 4.508 | 4.533 | +0.025 ± 0.028 | level | +0.037 ± 0.044 | |
| | elite_night | 5.452 | 5.451 | -0.001 ± 0.018 | level | -0.001 ± 0.026 | |
| variants | 27 catalog entries (realistic) | | | 24 identical chunk by chunk; top_heavy +0.154 ± 0.212, antes_from_level_3 -0.010 ± 0.014, fast_schedule -0.002 ± 0.015 | level | | |
| aware | five aware fields | | | identical | level | | |

0 timeouts and 0 errors in every chunk for both specs. Weighted score (addendum 11, six adapter bots): W +0.0064 ± 0.0060 night points, lower bound **+0.0004**; W-min +0.0049 ± 0.0077, lower bound -0.0028; the cap holds. Families: ordinary +0.0097 ± 0.0216, strong +0.0219 ± 0.0232, adapters +0.0077 ± 0.0158, twist on realistic +0.0002 ± 0.0012, twist aware 0.

**Read these with care.**
- **The heads-up flop read did not show.** exploit5_hu, the cell it was built for, is level. Each read alone on the same seeds, raw (goal/s24/q4.out): c-bettor read exploit5_hu +0.000 ± 0.059, exploit_hu +0.052 ± 0.067, exploit4_hu +0.000, adapt_hu -0.007; shove read exploit5_hu -0.007 ± 0.015, exploit5_3 -0.025 ± 0.050, exploit4_hu +0.015, adapt_hu +0.015. On diagnostics the c-bettor read was +0.083 ± 0.060. So it costs nothing visible, and its gain is unproven: exploiter 5's heads-up flop print is still there in points. Heads-up stays level (8.52 / 8.43), as the arena found it.
- **The gain is the shove read at 8-max, and the screen probably flatters it.** First-order points put it about +0.01 a table (the rule's section), and played on diagnostics the nine 8-max cells averaged about zero. night +0.024 and elite_b +0.037 are above that; expect less on a held-out set.
- **night_hard's raw delta is beyond noise down** (-0.031 ± 0.030); the term's difference accounts for it (-0.024 ± 0.021) and corrected it is level (-0.006 ± 0.018). Corrected deltas decide (addendum 13), but it is the cell to watch.
- **F wins against exploiter 5 as before:** 8-max 6.04 vs 4.47, three-handed 8.27 vs 7.24, heads-up 8.52 vs 8.43 on 10/7. exploit5_3's exploiter moved 7.193 to 7.240 (F level), so the night seat paid for it.
- **Not screened with S22.** The base is batch 8 without S22's river read, whose code is not on main. S22's read and this one act on different streets, but only a run on top of it can say they add. climb/b8-s22 does not merge cleanly with this branch (13 conflict blocks, including hyperion/compose/bot.py); main does (0).
- The exploit stage's p99 column reads up to 4.1 ms for both specs in cells without any new read: those chunks finished in two windows of about ten minutes, one for each spec, on a box shared with other work, with 0 timeouts; model mode replays regardless. Not the bot.

## Timing

`climb_accept --stages timing` (goal/s24/timing.md, tools/latency.py, 20,000 calls at load about 9): act p50 64.0 against 69.2 µs, p99 144.7 against 161.3, max 359 against 515, none over 1 ms, for F and S24. The reads themselves are a counter at hand end and a short scan when a short all-in is faced. One run; under the climb's 200 µs check. Not the zip's proof through a kit's adapter.

## Tests

tests/test_s24_reads.py (12: the shove read's counts, first actions only, no chance behind an all-in, a blind posted as a raise; both reads reach the decisions; shut gates play as F; twist tables play as F; a table replays exactly). tests/test_sim_exploiter.py and tests/test_climb_accept.py gain exploiter 5. docs/packet/CONTRACTS.md regenerated (the apicard test asked).
Full suite at 7a841e1 (`pytest -q -m "not timing"`, goal/s24/suite.out): **1507 passed, 5 skipped, 0 failed**. The first run, at 3d5dab6's tree plus the log, had the one failure of the stale contracts card, fixed by regenerating it. Nothing under hyperion/ or tools/ changed after the screen's 3d5dab6.

## Addendum 17, proposed (not in docs/decisions.md; the coordinator's)

> **The climb: addendum 17 (exploiter 5 joins the exploit stage).** Batch 8 changed F at strong tables and in its three-handed preflop, so a fresh red-team agent played batch 8's ship as a black box through exploiter 3's arena and built exploiter 5 (goal/exploiter5, md5 f4121d395d7e533a128be36f35466353). On its own arena it trails F at 8-max (4.68-4.92 against 5.85-5.96) and three-handed (2.01 against 2.36) and is level heads-up on 2/1 points (1.47-1.50 against 1.51-1.54); its notebook lists heads-up probes of F's folds, whose size at each table size docs/drills/climb/s24-log.md measures.
>
> Fixed before it is measured by a climb_accept run on main: exploiter 5 joins the exploit stage as a tuning opponent, never in a night pool, with cells `exploit5` (8-max, with six night seats), `exploit5_hu` and `exploit5_3` (one night seat), as exploiter 4's; appended, so no earlier cell's seeds, file names or samples move (checked: 20 of 20 chunks of the exploit and elite stages, 14 of 14 of confirm and guards, identical). In the weighted score's adapter family (addendum 11's weights, tools/accept_weights.json) the six adapter bots take a fixed sixth each inside a format (a fifth before): 16.7% of the family, 5.6% in each format, which at the family's base weight of 0.15 is 0.025 of W. The family's weight and range are unchanged. The bot is deterministic: it imports no random and its one clock read cannot change an action, so it needs no fixed speed in model mode; two model-mode runs replay exactly. Its adapter puts back the collector threshold it raises at import. From the first climb_accept run started after its wiring merges; runs already started keep the protocol they started under. S24's screen ran with it from its branch before this addendum, as a tuning run.
