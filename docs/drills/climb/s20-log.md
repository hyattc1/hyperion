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
- 14:30 Step 1 recordings of F finished for the exploit and strong fields (night still running). Findings below.

## Step 1: where F loses three-handed (diagnostic seeds 11000-11099, F = batch 6)

Tools (scratch `goal/s20/`): `d3.py` records every hand that starts with two or three alive (decisions, hole classes,
deltas) as climb_accept seats each field; `summ.py` books each spot's decision with the hand's net (bb a hand); `a3.py
pairs` / `fit3.py` measure the flop's realization; `depth.py` the effective stacks.

**Strong fields** (elite, mirror, elite_b, mirror_b pooled, 100 seeds x 8 each). Three-handed at these tables is played
at 8-27 bb effective (elite: 669 / 969 / 1,870 / 1,622 / 1,027 / 195 / 25 of F's hands at <8 / 8-12 / 12-18 / 18-27 /
27-40 / 40-60 / 60+ bb). F trails elite1 by about 0.2 bb a hand at every depth from 8 to 27 bb. By spot, action share
(bb a hand of the hands in that action), and the spot's bb a hand:

| spot | F | elite1 | elite2 | rival2 |
|---|---|---|---|---|
| BTN first in: fold / raise / jam | 30% / 65% (-0.2) / 6% (+1.1): **-0.09** | 45% / 29% (+0.6) / 26% (+1.0): **+0.42** | 44% / 36% (+0.3) / 20% (+0.9): +0.31 | 69% / 20% / 11%: +0.14 |
| SB vs the button's open: fold / flat / 3-bet / jam | 77% / 8% / 2% / 12%: -0.10 | 60% / 17% (+1.0) / 2% / 21% (+2.5): +0.44 | 65% / 15% / 2% / 18%: +0.24 | 74% / 2% / 2% / 22%: +0.27 |
| SB first in (button folded): fold / raise / jam | 10% / 64% (-0.1) / 26% (+0.4): -0.01 | 24% / 26% / 49% (+0.5): +0.20 | 27% / 32% / 41%: +0.18 | 44% / 20% / 25% (11% limp): +0.01 |
| BB vs the button's open (SB folded): fold / call / jam | 39% / 19% / 39% (+2.4): **+0.69** | 54% / 17% / 27%: +0.19 | 51% / 22% / 24%: +0.07 | 54% / 19% / 25%: -0.12 |
| BB vs the SB's open | 53% / 25% / 19%: +0.06 | 49% / 20% / 29%: +0.18 | +0.01 | -0.09 |
| our open faces a jam: fold / call | **2,717 times**, 90% / 10%: -1.82 | 651 times, 60% / 40%: -0.71 | 885, 66% / 33%: -0.85 | 596, 90% / 10%: -1.81 |

So at strong tables the loss is F's first-in play: it min-raises 65% of buttons and 64% of small blinds at 8-27 bb,
is re-shoved on four times as often as elite1 (2,717 against 651 times) and folds 90% of those. The elite builds jam
first in (26% and 49%) and raise less. F's big blind (it re-shoves 39% over the button's open, +0.69 bb a hand) is the
strong part; 3-bets short of all in are rare here (elite1 455 jams to 33 sized 3-bets three-handed).

**Exploit fields** (three-handed from the start, 100 bb, so mostly 60+ bb deep):
- exploit_3: F +0.40 bb a hand three-handed, exploiter 1 -0.04. F's batch-4 defence wins the spot that matters:
  facing exploiter 1's small 3-bets (2.0-2.5x, 2,305 times) F 4-bets 65% (+4.0) and folds 26%; as BTN it opens 52% at
  +1.4. Anything new must keep this: exploiter 1's 3-bets are tiny (1,782 under 2.2x, 848 at 2.2-2.6x).
- exploit2_3: F's small blind first in raises 83% (-0.3 bb a hand) against exploiter 2's big blind, which defends 77%
  (+1.15); F's 4-bets over exploiter 2's 2.6-3.1x 3-bets lose (21% of the time, -11.3 bb each); F's BB calls the
  button's open 35% (-1.1).

**3-bet sizes three-handed** (non-all-in, multiple of the open): exploiter 1 2.0-2.6x; exploiter 2 and the elite
builds 2.6-3.1x; F, rival 2, rival 3 and exploiter 3 3.1-3.7x. The new tree's two sizes are 2.3x and 3.3x (geometric
over that span; a size between maps on a log scale).

**Realization at heads-up flops** (two in the hand, chips behind; our seat's share of the flop pot = (net + its chips in
the pot) / pot, against its class-vs-class all-in equity; postflop all-ins before the river scored at their equity,
which narrows little). It depends strongly on the opponent: F out of position against exploiter 1 gives up 0.31 of the
pot beyond equity (the old model says 0.05) and against exploiter 2 0.24; in position F gets -0.07 / -0.10 (model
+0.05); against the exploit fields' pool seat F gets +0.25 in position. Fitted as an offset over the old model's
in-position share E + k E(1-E) + s(b_ip - b_oop), piecewise linear at SPR 2 / 6 / 15 (`fit3.py`), each group's flops
weighted equally (`goal/s20/real_mix.json`; groups: strong = elite, mirror, elite_b, mirror_b; exploit = exploit_3,
exploit2_3, exploit3_3, adapt_3; our seat = F and its copies f_copy):

| offset over the old model (95%) | SPR 2 | SPR 6 | SPR 15 |
|---|---|---|---|
| our seat in position, mix (14,143 flops) | +0.053 ± 0.052 | -0.019 ± 0.055 | **+0.181 ± 0.079** |
| ... exploit group / strong group | +0.166 ± 0.077 / -0.004 ± 0.067 | -0.055 / +0.035 | +0.195 / -0.191 ± 0.426 |
| our seat out of position (its own share), mix (15,300) | -0.024 ± 0.059 | +0.003 ± 0.051 | **-0.117 ± 0.056** |
| ... exploit / strong | +0.004 / -0.037 | -0.046 / +0.023 | -0.116 / +0.149 ± 0.523 |
| two other seats, the IP one's share, mix (16,103) | +0.059 ± 0.046 | -0.012 ± 0.050 | +0.168 ± 0.097 |
| ... exploit / strong | +0.106 / +0.028 | -0.010 / +0.017 | +0.178 / -0.260 ± 0.283 |

At E = 0.5 that is our seat's share - E of +0.07 / +0.03 / +0.24 in position (old model +0.016 / +0.047 / +0.062) and
-0.04 / -0.04 / -0.18 out of position (old -0.016 / -0.047 / -0.062). Read: up to SPR ~6 (every strong-table spot) the
old model is right within noise for us and the field; deep (SPR 15, the exploit fields' 100 bb tables) position is
worth about three times what it assumed, and our out-of-position flops lose more. How much the fit moves across
fields: at SPR 2 our in-position offset is +0.17 against the exploiters' fields and 0.00 at strong tables (0.17 apart,
about two intervals); deep, the strong group has too few flops to say (± 0.4). Three-way flops (1,033, all seats): each
postflop seat's share - its three-way equity is -0.09 / -0.02 / +0.11 (first / middle / last), taken as log weights
-0.29 / -0.07 / +0.28 on the bucket model's odds.

**S13's three-handed tables (C3: tables/extra/short_3.json on pre_3way and pre_allin, no 3-bet deferral), same seeds**
(recorded from the branch at 8061d2a, which plays C3 as S13 left it). Our seat's three-handed bb a hand, C3 against F:
exploit_3 +0.293 against +0.404 (**-0.11**); exploit2_3 +0.242 against +0.136 (+0.11); elite +0.151 against -0.035
(+0.19: as good as elite1's +0.18 and elite2's +0.15 in the same rooms). Where:
- *Against exploiter 1* the loss is the opener facing its tiny 3-bets (1,711 times): C3 folds 34%, calls 44% (-0.5 bb
  each) and 4-bets 10%, so the spot is worth +0.06 a hand; F 4-bets 65% there for +2.07. C3's button also opens 85%
  (+0.41 a hand, F's 52% +0.73) and its small blind limps 35% first in (+0.06, F +1.05). Its blinds are better than
  F's (the SB 3-bets the button's open 41%: +0.77 against +0.06; the BB against the SB's open +0.33 against -0.24).
- *Against exploiter 2* C3's big blind calls the button's open 66% (-1.4 bb each: -0.87 a hand, F -0.56): our
  out-of-position flops lose to it, which the old flop model did not know. Its small blind 3-bets the open 41% (+0.79).
- *At elite* C3 jams first in more (button 19%, SB 40%) and min-raises less (30% / 10%): the button +0.39 a hand (F
  +0.05). Its weak spots there: the SB limps 26% first in (-0.5 bb a limp, no better than folding) and the BB flats
  79% of the button's opens (+0.30 a hand; F's BB re-shoves 39% for +0.69).
So the old tables already fix most of F's strong-table leak; what loses is calling 3-bets and flatting out of position
against the exploiters (realization the old model got wrong) and the equilibrium's answer to exploiter 1's any-two
min-3-bets, which F's own defence beats by 4-betting. The second tree adds 4-bets over small 3-bets, prices our flops
from the fit above, and the gated variant hands preflop back to F against a 3-bettor far above equilibrium.

## F's base on the screen set (code bd36043bea, runout term; corrected means)

- 15:15 base exploit + elite finished (`goal/s20/base1.log`): exploit 5.765, exploit_hu 9.247, exploit_3 8.491,
  exploit2 5.849, exploit2_hu 7.903, exploit2_3 7.321, exploit3 5.447, exploit3_hu 8.339, exploit3_3 7.520, adapt
  5.822, adapt_hu 8.666, adapt_3 7.934; elite 4.856, elite_night 5.440, mirror 4.506, elite_b 4.609, mirror_b 4.501.
- 15:25 Identity check (S14's): `tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages
  confirm,guards --workers 2` on the branch at 9e3af86 (detached worktree `wt_s20_d`, out `goal/s20/idchk`) against
  the coordinator's run of the same command on main b1c9e89 (`goal/idchk27/post`): all 14 chunks' sample lists
  identical (night, night_hard, realistic, top, night at both payout tables, night with doubling blinds). Repeated at
  the end on the final code.

## Step 2: the second tree and its solve

`tools/solve_short.py three2` (block "three-handed, v2 (S20)"): one generic betting-round walk builds the tree, so
every line follows the same rules:
- button: fold / open (2.0 bb to 25 bb effective, 2.25 to 60, 2.5 deeper) / jam (no limp: `limp_btn` off);
- facing an open with nobody in between: fold / flat / 3-bet 2.3x / 3-bet 3.3x / jam (both blinds; the small blind's
  flat makes three-way and heads-up flops);
- behind a flat: fold / call / squeeze 4x / jam;
- the opener facing a 3-bet: fold / call / 4-bet 2.2x / jam; a cold player facing a 3-bet: fold / 4-bet / jam (no
  cold call; the big blind's cold 4-bet over the small blind's 3-bet); facing a 4-bet: the 3-bettor folds / calls /
  jams, anyone else folds / jams;
- the small blind first in: fold / limp / open / jam; the big blind over its limp: check / raise 2.5 or 3 bb / jam;
- a raise to more than 40% of the effective stack (45% for 4-bets) is the jam; once anyone is all in, fold / call.
- Terminals: folds; all-in showdowns (two-way on the 169 x 169 matrix, three-way on 20 buckets as before, side pots
  layered); heads-up flops at the fitted realization; three-way flops by the bucket model's odds tilted by postflop
  seat (the log weights above). ICM at prizes 1 / 0.4 / 0 (10/7/5) as S13.
- *Asymmetric realization*: each configuration is solved three times, once per hero seat (button, small blind, big
  blind). In the solve for hero h, h's flops use our seat's fitted share (in or out of position) and the other two's
  flops the symmetric fit; the table keeps each seat's nodes from its own solve. Every node stores its raise sizes as
  multiples of the bet it faces ("z"), so the bot maps any history generically.
- Size at 40 bb: 76 decision nodes (S13's tree 30); at 12 bb and under, 22.

Solve (14:20-15:40, system python3 with numpy, 2 workers, nice 10): grid 5, 8, 12, 18, 27, 40, 60, 90 bb for each of
the three stacks (512 configurations x 3 hero seats), 400 iterations each, `--real goal/s20/real_mix.json` (the mix
fit, w3 -0.29 / -0.07 / +0.28, shares clipped to [-0.3, 1.3]). Exploitability in the abstract game, milli-prizes a hand
(1st - 3rd = 1000), per hero seat's solve: median 0.038 / 0.041 / 0.038 (button / SB / BB), 90th percentile 0.29 /
0.30 / 0.29, worst 1.59 / 1.63 / 2.37 (90, 90, 27-40: the deepest, least converged; S13's tree: median 0.026, worst
1.65 at 300 iterations). At 60, 60, 60 the exploitability falls 1.35 / 0.58 / 0.43 / 0.33 / 0.25 / 0.19 at 100-600
iterations (S13's is CFR+ with linear averaging, unchanged). Table: tables/extra/short_3b.json, 3.19 MB (compact
form; S13's short_3.json is 1.5 MB), decoded in 0.27 s once per process when `short.three2` is on.

Checks (tests/test_s20_three.py, run with system python3 for the numpy parts): the tree has the new lines; a small
solve converges and every class's probabilities sum to 1; **push/fold sanity**: both trees cut to fold / jam at the
button's and the small blind's first decisions at 8, 8, 8 bb give the same jams and calls within 0.02 (button jam,
SB jam, SB / BB calls of the jams); the default realization coefficients reproduce S13's fixed model exactly.

What the solution plays (combo-weighted frequencies): at 18, 18, 18 the button folds 66% / opens 34% / jams 1%, the
small blind against the open folds 76% / flats 9% / jams 15%, first in folds 32% / limps 16% / opens 38% / jams 14%;
the big blind defends 100% against the button's min-raise (calls 82%, jams 18%: with the small blind's dead half big
blind it gets 3.5 to 1, and the fitted out-of-position share loses only ~0.04 of the pot at SPR 3-4, so even 72o
realizes more than the 22% it needs: the measured shares for weak hands are the open question here); facing a 2.3x
3-bet the opener folds 7-19%, calls 60-77%, jams 16-22%. At 90, 90, 90 the small blind 3-bets 70% of hands against the
button's open (polarized: 72o and T4o 3-bet, K9o folds 60%), never flats it (deep out-of-position flops cost -0.18 of
the pot in the fit).

## Step 4: screens (screen seeds, runout term, --aim strong; deltas corrected, candidate - F)

Candidates (on top of SHIP_DIALS; `goal/s20/cand_*.json`), route `pre_3way=short,pre_allin=short`, `short.three2`:
- **U** (ungated): table 3b (the mix fit), `short.defer_3bet` 1.0 (off);
- **G** (gated): table 3b, `short_strong` true (the strong route's read: our first-in raises re-raised, smoothed,
  at least `strong_rr` 0.2) and `short.defer_3bet` 0.4 (S13's guard: preflop back to F against a seat 3-betting our
  opens at 0.4 or more).

- 16:14 **U, seeds 10000-10099**, stages exploit, elite (`q/010_U100.out`, `r_U100.json`): **REJECT**.

| cell | F | U | U - F | |
|---|---|---|---|---|
| elite | 4.876 | 4.921 | +0.045 ± 0.024 | UP |
| elite_night | 5.389 | 5.387 | -0.002 ± 0.029 | level |
| mirror | 4.534 | 4.549 | +0.015 ± 0.023 | level |
| elite_b | 4.507 | 4.557 | +0.050 ± 0.025 | UP |
| mirror_b | 4.496 | 4.557 | +0.061 ± 0.026 | UP |
| exploit (8-max) | 5.675 | 5.496 | -0.179 ± 0.082 | DOWN (exploiter 1 4.687 -> 4.788) |
| exploit_3 | 8.356 | 7.848 | -0.508 ± 0.237 | DOWN (exploiter 1 7.007 -> 7.407) |
| exploit2 (8-max) | 5.931 | 5.802 | -0.129 ± 0.082 | DOWN (exploiter 2 5.048 -> 5.034: to the pool seats) |
| exploit2_3 | 7.322 | 7.323 | +0.002 ± 0.212 | level |
| exploit3 / exploit3_3 | | | +0.024 ± 0.070 / +0.066 ± 0.234 | level |
| adapt (8-max) | 5.945 | 5.758 | -0.187 ± 0.086 | DOWN (adapt1 5.167 -> 5.191: to the pool seats) |
| adapt_3 | | | +0.036 ± 0.204 | level |
| every heads-up cell | | | 0 | identical (heads-up is not routed) |

Weighted score: W -0.0051 ± 0.0273, W-min -0.0290 ± 0.0404. Read: the equilibrium tables win at strong tables (three
of five cells up, like K18's +0.04) but lose to exploiter 1 (its any-two min-3-bets, which F's 4-bets beat) and, in
the 8-max exploit cells, to the night-pool seats left in the endgame (the points move to them, not to the exploiter:
F's reads take more from weak seats than an equilibrium does, as S13 found heads-up). Ungated is not shippable.
- 16:16 Pessimistic fit for a second table (3c): our seat's flops only against exploiters 1-3 and adapt1 (OPP filter in
  `fit3.py`; 7,979 flops each way). At E = 0.5 our share - E in position -0.008 / -0.108 / +0.146 at SPR 2 / 6 / 15
  (mix +0.069 / +0.028 / +0.243), out of position -0.144 / -0.238 / -0.203 (mix -0.040 / -0.044 / -0.180). Solving
  (`real_ex.json`, same grid and iterations) for a candidate GX = G with table 3c.
- 16:36 **G, seeds 10000-10099**, stages exploit, elite (`q/020_G100.out`, `r_G100.json`, code 4bac2cf): **REJECT**.

| cell | F | G | G - F | |
|---|---|---|---|---|
| elite | 4.876 | 4.904 | +0.028 ± 0.021 | UP |
| elite_night | 5.389 | 5.387 | -0.002 ± 0.019 | level |
| mirror | 4.534 | 4.549 | +0.015 ± 0.020 | level |
| elite_b | 4.507 | 4.540 | +0.032 ± 0.021 | UP |
| mirror_b | 4.496 | 4.536 | +0.040 ± 0.019 | UP |
| exploit (8-max) | 5.675 | 5.512 | -0.163 ± 0.071 | DOWN (exploiter 1 4.687 -> 4.798) |
| exploit_3 | 8.356 | 8.045 | -0.310 ± 0.207 | DOWN (exploiter 1 7.007 -> 7.187) |
| exploit2 (8-max) | 5.931 | 5.882 | -0.049 ± 0.029 | DOWN (exploiter 2 level: the pool seats) |
| exploit2_3 | 7.322 | 7.238 | -0.084 ± 0.112 | level |
| exploit3 (8-max) | 5.341 | 5.401 | +0.060 ± 0.054 | UP |
| exploit3_3 | 7.495 | 7.701 | **+0.206 ± 0.149** | UP (exploiter 3 7.877 -> 7.713) |
| adapt (8-max) | 5.945 | 5.891 | -0.053 ± 0.049 | DOWN |
| adapt_3 | 7.805 | 7.797 | -0.008 ± 0.101 | level |

Weighted: W +0.0008 ± 0.0184, W-min -0.0121 ± 0.0259. The gate halves the 8-max pool losses (exploit2 -0.129 ->
-0.049, adapt -0.187 -> -0.053) and keeps most of the strong-table gain, and the tables now beat exploiter 3 (three-
handed +0.21, 8-max +0.06); but the 3-bet guard does not keep exploiter 1 off (exploit_3 -0.31, exploit -0.16).
- 16:40 Why G loses to exploiter 1 (`d3.py` with G's dials on exploit_3, diagnostic seeds 11000-11059; the recorder
  now marks each decision the specialist made): the tables make 33-47% of our preflop decisions at every stage of the
  table, because the 3-bet guard never fires: exploiter 1 3-bets the tables' opens far less than F's (one table's read
  at hand 43: 1 of 19.5 and 2 of 7.5 opens 3-bet), so the read stays under 0.4. Our seat's three-handed bb a hand,
  G against F on the same seeds: +0.205 against +0.388. The difference is in the answers to exploiter 1's small
  3-bets: G folds 15%, calls 41% (-1.6 bb each) and 4-bets 38% (+0.84 a hand), F folds 25%, calls 7% and 4-bets 65%
  (+1.81); and the small blind first in (G +0.58, F +0.92: F opens 88% and 4-bets the big blind's 3-bets). The mix
  fit prices our calls of 2.3x 3-bets as fine, but against exploiter 1 our flops lose (its column in step 1).
- Two fixes, both principled rather than retuned thresholds, queued as candidates: **keep the defence**
  (`short.three2_keep_defence`, S14's `strong2_keep_defence` for this route: once our own raise this hand has been
  re-raised, F's 3-bet defence plays the rest of the hand's preflop; the tables open and answer opens), and the
  **pessimistic table** (3c, the fit against the exploiters: at 18 bb it folds 33% / calls 32% / jams 35% as the big
  blind against the button's open instead of 0 / 82 / 18%, and calls 2.3x 3-bets 16-52% instead of 51-77%).
  Candidates GK (G + keep the defence), GX (G with table 3c), GXK (both). Also G2 (G with `short.defer` widened to
  every leak archetype F's profiler names: dead, station, maniac, random, nit), running.
- 16:47 **G2** (G + `short.defer` dead,station,maniac,random,nit), seeds 10000-10099, exploit + elite: **REJECT**.
  elite +0.027 ± 0.021 UP, elite_b +0.031 ± 0.021 UP, mirror_b +0.042 ± 0.018 UP, mirror +0.017, elite_night -0.002;
  exploit -0.114 ± 0.063 DOWN, exploit_3 -0.323 ± 0.195 DOWN, exploit2 -0.038 ± 0.027 DOWN, adapt -0.039 ± 0.045,
  exploit3_3 +0.135, the rest level. W +0.0000 ± 0.0172, W-min -0.0133 ± 0.0236. The archetype reads do not separate
  exploiter 1 from the strong builds three-handed; dropped.
- 17:00 **GK** (G + keep the defence), seeds 10000-10099, exploit + elite (`q/024_GK100.out`, code ff07018): **REJECT**
  on two cells. elite +0.027 ± 0.021 UP, elite_b +0.027 ± 0.022 UP, mirror_b +0.034 ± 0.019 UP, mirror +0.002,
  elite_night +0.003; exploit3 +0.057 ± 0.049 UP, exploit3_3 +0.164 ± 0.126 UP; exploit_3 -0.122 ± 0.203 (level; G
  -0.310), exploit2_3 +0.038, adapt -0.029, adapt_3 -0.025 (level); **exploit -0.102 ± 0.064 DOWN** (exploiter 1
  4.687 -> 4.738), **exploit2 -0.047 ± 0.030 DOWN** (exploiter 2 level). W +0.0063 ± 0.0168, W-min -0.0014 ± 0.0229.
  Keeping F's defence fixes most of exploit_3; what is left is the 8-max endgames.
- 17:05 Where GK loses at 8-max exploit (`d3.py`, F and GK on exploit, diagnostic seeds 11000-11079, 640 tables
  each, 364 reach three-handed in both): our seat's three-handed bb a hand with exploiter 1 alive GK -0.108 (1,751
  hands) against F +0.228 (2,119); with two pool seats GK +0.378 against F +0.401. Against exploiter 1 F opens 73% of
  its buttons (+1.0 bb each; exploiter 1's big blind folds 64% to it) where the tables fold 55%, and F's small blind
  opens 84% (+0.70 a hand) where the tables limp 18% and jam 25% (-0.29): F's reads take what exploiter 1 gives, which
  an equilibrium does not.
- 17:10 Surveys at our three-handed preflop decisions (F as shipped, diagnostic seeds 11100-11115, `survey_*.py`):
  per-seat re-raises of our first-in raises do not separate strong builds from the night pool (mirror's strong bots
  median 1, night pool median 1); fold to preflop raises does not separate exploiter 1 (0.70) from the elite builds
  (0.69-0.79). **S13's 3-bet read does**: exploiter 1 median 0.33 [p10 0.27, p90 0.39] at 8-max, 0.36 [0.12, 0.47]
  three-handed; every other bot (elite1, elite2, elite4, rivals 1-3, F's copies, hybrid3_x, agent bots, exploiter 2,
  adapt1, the night pool) has a median of 0.04-0.12 and a p90 of at most 0.23 (adapt1); 0.4 caught exploiter 1 at
  only 5% of its 8-max decisions. So `short.defer_3bet` **0.25** (fixed from this table before any screen: above every
  other bot's p90, below exploiter 1's 8-max p10). Candidate GK25 = GK with 0.25.
- 17:15 **GX** (G with table 3c, the pessimistic fit), partial (exploit3_3 and adapt cells still running): elite
  +0.017, elite_b +0.047 UP, mirror +0.022 UP, mirror_b +0.041 UP, elite_night -0.011; exploit_3 -0.434 ± 0.206 DOWN,
  exploit -0.126 ± 0.071 DOWN. The pessimistic realization alone does not hold exploiter 1.
- 17:19 **GX** final (`q/025_GX100.out`): **REJECT**. elite +0.017, elite_b +0.047 ± 0.023 UP, mirror +0.022 ± 0.016
  UP, mirror_b +0.041 ± 0.023 UP, elite_night -0.011; exploit3 +0.071 ± 0.049 UP; exploit_3 -0.434 ± 0.206, exploit
  -0.126 ± 0.071, adapt -0.056 ± 0.047 DOWN; exploit2 -0.034, exploit2_3 -0.051, exploit3_3 +0.052, adapt_3 +0.002
  level. The pessimistic table moves the strong cells a little (mirror up) but does nothing against exploiter 1 on
  its own; F's defence (GK) is what holds there.
- 17:20 At 8-max exploit2 (diagnostic seeds 11000-11079, F and GK): points 6.074 / 6.065; three-handed with
  exploiter 2 alive GK -0.018 bb a hand against F +0.039 (3,688 / 3,732 hands; the tables play 19% of our preflop
  decisions), with two pool seats +0.410 against +0.388. Small either way on these seeds (the screen's -0.047 ±
  0.030 is near its bound); exploiter 2's 3-bet read (0.08) does not separate it, and its postflop probe read is
  S13c's gate (being changed on climb/s13c-gate), so it is not used here.
- 17:32 **GK25** (G + keep the defence + `short.defer_3bet` 0.25), seeds 10000-10099, exploit + elite
  (`q/026_GK25100.out`, code ff07018): **one cell down**. elite +0.027 ± 0.021 UP, elite_b +0.027 ± 0.022 UP, mirror_b
  +0.034 ± 0.019 UP, mirror +0.002, elite_night +0.003; exploit -0.046 ± 0.054 (GK -0.102), exploit_3 -0.113 ± 0.140,
  exploit3 +0.043, exploit3_3 +0.117, exploit2_3 +0.045, adapt -0.026, adapt_3 -0.023 (all level); **exploit2 -0.052
  ± 0.029 DOWN** (exploiter 2 5.048 -> 5.045: the pool seats). W +0.0070 ± 0.0156, W-min -0.0002 ± 0.0205. The 3-bet
  guard at 0.25 takes exploiter 1 off the tables at 8-max (exploit -0.10 -> -0.05).
- 17:43 **GXK25** (GK25 with table 3c), seeds 10000-10099 (`q/027_GXK100.out`): **two cells down**. elite +0.022 ±
  0.019 UP, elite_b +0.043 ± 0.021 UP, mirror_b +0.036 ± 0.021 UP, mirror +0.016, elite_night -0.003; exploit3 +0.059
  ± 0.046 UP; exploit -0.072 ± 0.061 DOWN, exploit2 -0.052 ± 0.038 DOWN; the rest level. W +0.0079 ± 0.0164, W-min
  -0.0005 ± 0.0224. No better than GK25 on the exploit cells.
- 17:44 Where exploit2's 8-max endgames differ (diagnostic seeds, exploiter 2 alive): the big blind against the
  button's open, GK -0.13 bb a hand (calls 38%, -0.6 each) against F +0.42 (calls 22%, +0.6 each; jams 31%). The big
  blind's wide flats are also the tables' weakest spot at elite (U: calls 79%) and the spot where the realization model
  is least supported (the 100% defence rests on weak hands realizing nearly their equity out of position, a range F
  itself never plays, so the fit has no data there), while F's own big blind was its strongest three-handed spot at
  strong tables (+0.69 bb a hand, step 1). Candidate **GK25R** = GK25 with `short.three2_roles` btn,sb (F plays the
  big blind). Running; F's base confirm + guards (030) moved behind it.
- 17:56 **GK25R** (GK25, the tables on the button and small blind only), seeds 10000-10099, exploit + elite
  (`q/028_GK25R100.out`, code ff07018): **no cell down**.

| cell | F | GK25R | GK25R - F | |
|---|---|---|---|---|
| elite | 4.876 | 4.908 | +0.033 ± 0.020 | UP |
| elite_night | 5.389 | 5.396 | +0.007 ± 0.017 | level |
| mirror | 4.534 | 4.545 | +0.011 ± 0.019 | level |
| elite_b | 4.507 | 4.540 | +0.032 ± 0.021 | UP |
| mirror_b | 4.496 | 4.532 | +0.036 ± 0.018 | UP |
| exploit (8-max) | 5.675 | 5.662 | -0.013 ± 0.053 | level |
| exploit_3 | 8.356 | 8.260 | -0.095 ± 0.135 | level |
| exploit2 (8-max) | 5.931 | 5.903 | -0.029 ± 0.031 | level |
| exploit2_3 | 7.322 | 7.329 | +0.007 ± 0.079 | level |
| exploit3 (8-max) | 5.341 | 5.404 | +0.063 ± 0.049 | UP |
| exploit3_3 | 7.495 | 7.571 | +0.077 ± 0.100 | level |
| adapt (8-max) / adapt_3 | | | +0.009 ± 0.039 / +0.010 ± 0.080 | level |
| every heads-up cell | | | 0 | identical |

  W +0.0123 ± 0.0149, W-min +0.0052 ± 0.0195 (the best of the candidates; G +0.0008, GK25 +0.0070). Chosen as the
  final candidate: the full screen (200 seeds; exploit, elite, confirm, guards, all 26 variants) is next.
- 17:56 Full suite on the branch (`pytest -q -m "not timing"`, wt_s20 at 356d6d7, code ff07018, with the 3b table present, load
  ~15): **1,355 passed, 5 skipped**, 106 deselected, 9:42.
- 18:05 Latency (tools/latency.py --bot composite --hand-end --tables 12 --reps 3, per-call minimum, load ~15; F /
  GK25R, µs): exploit_3 (rules three.json) act p99 78.7 / 90.4, max 114.5 / 121.2, hand_end p99 134.1 / 123.6, first
  decision mean 94.7 / 94.3; elite act p99 119.4 / 113.8, max 200.7 / 167.7, hand_end p99 137.1 / 138.7. A decision is
  a history walk and a string lookup. The member with `short.three2` builds in 0.30 s cold (the table decoded once
  per process; `import hyperion.strategy.short` 0.06 s). Table size: tables/extra/short_3b.json 3.19 MB, 2.43 MB
  zlib-9 (S13's short_3.json 1.5 MB). tools/pack.py copies only tables/*.json, so a ship with `short.three2` on must
  carry the file (move it to tables/ or name it with --extra); with the dial off nothing changes.
- 18:05 What GK25R plays at strong tables (`d3.py`, diagnostic seeds; elite 11000-11099, mirror_b 11000-11059):
  the tables make 20-51% of our three-handed preflop decisions at elite (the strong read opens as the table goes on)
  and 48-57% at mirror_b. Our seat's three-handed bb a hand: elite +0.020 against F's -0.035 on the same seeds (the
  button +0.16 against +0.05: it folds 44% / raises 48% / jams 8% where F raised 65%; our opens faced a jam 440
  times, folding 85%), mirror_b -0.008 against -0.091 (the button +0.12 against -0.13).
- 18:35 **GK25R, screen seeds 10000-10199**: exploit, elite, confirm and guards complete (`q/040_FULL.sh`, cache key
  984b3878e26c; deltas read from the cached chunks' corrected samples, `goal/s20/peek.py`); the run was stopped at the
  variants stage to screen R3 first (below), and its verdict is re-printed from the cache with the variants later.

| stage | cell | GK25R - F (200 seeds) | |
|---|---|---|---|
| elite | elite | +0.026 ± 0.014 | UP |
| | elite_night | +0.011 ± 0.011 | level |
| | mirror | +0.028 ± 0.013 | UP |
| | elite_b | +0.021 ± 0.015 | UP |
| | mirror_b | +0.032 ± 0.013 | UP |
| exploit | exploit / exploit_3 | -0.029 ± 0.034 / -0.073 ± 0.101 | level |
| | exploit2 / exploit2_3 | -0.004 ± 0.022 / +0.011 ± 0.067 | level |
| | exploit3 / exploit3_3 | +0.039 ± 0.030 / +0.068 ± 0.070 | UP / level |
| | adapt / adapt_3 | -0.006 ± 0.027 / -0.030 ± 0.061 | level |
| | every heads-up cell | 0 | identical |
| confirm | night | +0.009 ± 0.011 | level |
| guards | night_hard | -0.003 ± 0.010 | level |
| | realistic | **-0.007 ± 0.005** | **DOWN** |
| | top | +0.002 ± 0.011 | level |
| | night @10/7/5/... / @50/25/12/... / doubling | -0.001 ± 0.022 / +0.094 ± 0.185 / -0.006 ± 0.010 | level |

  Every strong cell but elite_night up, every exploit cell level or up; one guard down by 0.007 (realistic: F's
  reads take more from the realistic field's bots at the tables whose read opens the route). Suspect: the route's
  `pre_allin` (the tables call jams at equilibrium; F's call-off reads shove rates, and the realistic field has
  PushFoldBot-style jammers). **R3** = GK25R with the route `pre_3way=short` only (F answers every all-in): confirm,
  guards at 200 seeds and exploit, elite at 100, running.
- 18:44 **R3** confirm + guards at 200 seeds: night +0.009 ± 0.010, night_hard -0.002, top +0.003, night @10/7/5
  -0.000, @50/25/12 +0.087, **realistic -0.006 ± 0.005 DOWN** (as GK25R). So the all-in answers are not the cause.
- 18:47 The realistic field on diagnostic seeds 11000-11099 (`d3.py`, F and R3): the tables play 2-5% of our
  three-handed preflop decisions there (the strong read rarely opens), 19 of 800 table-rotations play differently,
  and R3 is +0.0022 points on these seeds. The screen's -0.006 comes from the few tables where the read opens. R4 =
  R3 with `short.defer` widened to F's leak archetypes (dead, station, maniac, random, nit): the equilibrium only
  against opponents F has no read on; queued.
- 19:06 **R4** confirm + guards at 200 seeds: **night +0.014 ± 0.009 UP**, night @10/7/5 +0.021 ± 0.021, @50/25/12
  +0.160 ± 0.161, night_hard +0.001 ± 0.008, top +0.004 ± 0.009, doubling -0.007 ± 0.009, **realistic -0.005 ± 0.004
  DOWN** (upper bound -0.001). Per seed (raw): realistic differs from F on 26 of 200 seeds for R4 (33 for GK25R and
  R3), raw sums -0.68 / -1.69 / -1.31 points over the 200 seeds, each differing seed a position or two in one or two
  of its 8 rotations (±0.01-0.25); 16 of R4's 26 are negative (a sign test cannot tell). The cell's interval is narrow
  because 87% of its seeds are identical by construction. A real, small cost at the few realistic tables whose read
  opens the route, or a handful of position swaps: the protocol counts it as down either way.
- 19:16 **R4** exploit + elite at 100 seeds (`q/046_R4.out`): elite +0.033 ± 0.019 UP, elite_b +0.029 ± 0.020 UP,
  mirror_b +0.038 ± 0.017 UP, mirror +0.014, elite_night +0.008; exploit3 +0.058 ± 0.044 UP; exploit -0.026, exploit_3
  -0.086, exploit2 -0.023, exploit2_3 -0.008, exploit3_3 +0.066, adapt +0.006, adapt_3 -0.001 (level). Weighted (all
  stages run so far): W +0.0115 ± 0.0138, W-min +0.0038 ± 0.0180. R3 and GK25R read the same within noise on every
  cell; R4 is the final candidate (night up, realistic the least down, the narrowest gate):
  `{"short_route": "pre_3way=short", "short.three2": true, "short.three2_file": "3b", "short.defer_3bet": 0.25,
  "short_strong": true, "short.three2_keep_defence": true, "short.three2_roles": "btn,sb", "short.defer":
  "dead,station,maniac,random,nit"}`. Its full screen (exploit and elite to 200 seeds, all 26 variants with F's base)
  is queued after the final identity check.
- 19:17 Identity check repeated at ff07018 (the final candidate's code; `goal/s20/idchk2`): 14 of 14 chunks
  identical to main's.
- 19:20 Main moved to e2a20fe (V-j, C3h, H7, S15d merged; SHIP_DIALS unchanged since b1c9e89, checked key by key):
  merged into the branch (8af4fda, `git merge main`, no conflicts; S13c's climb/s13c-gate at f4e7004 also merges
  cleanly onto the branch, checked with a trial merge in a scratch worktree). Full suite on the merged branch: 1,413
  passed, 5 skipped, 2 failed: tests/test_nightof_latency.py's cheap-bot kit round trip (a wall-clock p99 threshold;
  re-run, it fails once and passes once at load 6.5, and passes on main's worktree) and test_sim_adapt's twin test
  (passes alone). Neither touches the specialist (the cheap bot builds no member; adapt1 is an opponent).
  tests/test_s20_three.py: 10 passed under system python3 (numpy), 6 passed + 4 skipped under the venv (no numpy).
- 20:47 **R4 full screen** (screen set 10000-10199, every stage but aware/judges, runout term, --aim strong;
  `q/060_FINAL_R4.out`, `r_FINAL_R4_screen.json`, code ff07018): **REJECT** on three realistic-field cells.

| stage | cell | F | R4 | R4 - F | |
|---|---|---|---|---|---|
| confirm | night | 6.006 | 6.021 | +0.014 ± 0.009 | UP |
| guards | night_hard | 5.470 | 5.471 | +0.001 ± 0.008 | level |
| | realistic | 6.350 | 6.346 | -0.005 ± 0.004 | **DOWN** (raw -0.003 ± 0.005) |
| | top | 5.054 | 5.058 | +0.004 ± 0.009 | level |
| | night @10/7/5/4/3/2/1/0 | 6.243 | 6.264 | +0.021 ± 0.021 | level |
| | night @50/25/12/6/3/2/1/1 | 24.719 | 24.879 | +0.160 ± 0.161 | level |
| | night, doubling blinds | 5.872 | 5.864 | -0.007 ± 0.009 | level |
| elite | elite | 4.856 | 4.884 | +0.029 ± 0.013 | UP |
| | elite_night | 5.440 | 5.450 | +0.010 ± 0.010 | level |
| | mirror | 4.506 | 4.533 | +0.026 ± 0.013 | UP |
| | elite_b | 4.609 | 4.626 | +0.017 ± 0.014 | UP |
| | mirror_b | 4.501 | 4.534 | +0.033 ± 0.013 | UP |
| exploit | exploit / exploit_3 | 5.765 / 8.491 | 5.742 / 8.428 | -0.023 ± 0.032 / -0.063 ± 0.095 | level |
| | exploit2 / exploit2_3 | 5.849 / 7.321 | 5.849 / 7.309 | -0.000 ± 0.021 / -0.012 ± 0.059 | level |
| | exploit3 / exploit3_3 | 5.447 / 7.520 | 5.488 / 7.561 | +0.042 ± 0.026 / +0.041 ± 0.066 | UP / level |
| | adapt / adapt_3 | 5.822 / 7.934 | 5.822 / 7.897 | +0.000 ± 0.024 / -0.037 ± 0.056 | level |
| | the four heads-up cells | | | 0 | identical |
| variants | top_heavy (realistic) | 28.455 | 28.371 | -0.084 ± 0.079 | **DOWN** |
| | fast_schedule (realistic) | 6.100 | 6.092 | -0.008 ± 0.007 | **DOWN** |
| | knockout_bounty / auction / bounty / bonus_card | | | -0.005 ± 0.008 / -0.002 ± 0.005 / -0.001 ± 0.004 / +0.000 ± 0.005 | level |
| | the other 20 (twists, antes, straddle, pot limit, fixed raise ...) | | | 0 | identical |

  Weighted (addendum 11): W +0.0058 ± 0.0051 (lower bound **+0.0007**), W-min +0.0033 ± 0.0059 (lower bound
  **-0.0026**), cap holds; families: ordinary +0.0086, strong +0.0180, adapters -0.0013, twist -0.0008. 0 timeouts,
  0 errors in every cell.
- 20:50 Where the realistic cells come from (survey at our three-handed decisions, F as shipped, diagnostic seeds
  11100-11129): the strong read is open at 0-4% of them at realistic (median read 0.10), 15% at night, 60-78% at elite
  (median 0.22-0.25). So the three realistic-field cells are the few ordinary tables whose read crosses 0.2, where F's
  reads beat an equilibrium. Per-seat re-raises of our first-in raises: at realistic 27-53% of opponent decisions
  come from a seat that has never re-raised us (tag 53%, timeout_then_recover 50%, pushfold 42%), at elite 3-17%
  (rival2 3%, rival3 4%, elite1 8%), at mirror 24-38%, the night pool 46%. **R5** = R4 with `short.three2_seat_rr` 1:
  the tables only while each opponent alive has re-raised at least one of our first-in raises this table (S14's
  "per-seat read" for the diluted table read; the minimum evidence, not a tuned count). Identity on the merged code
  (8af4fda, `goal/s20/idchk3`): 14 of 14 chunks identical to main's. R5's full screen (code 77634e3) running.
- 22:05 **R5 full screen** (screen set 10000-10199, stages exploit, elite, confirm, guards, all 26 variants, runout
  term, --aim strong; `q/070_R5_FULL.out`, `r_R5_screen.json`, code 77634e3, F's chunks pinned to bd36043bea):
  **ACCEPT**.

| stage | cell | F | R5 | R5 - F (corrected) | | raw |
|---|---|---|---|---|---|---|
| confirm | night | 6.006 | 6.014 | +0.008 ± 0.007 | **UP** | +0.009 ± 0.009 |
| guards | night_hard | 5.470 | 5.472 | +0.002 ± 0.008 | level | +0.003 ± 0.012 |
| | realistic | 6.350 | 6.348 | -0.002 ± 0.002 | level | -0.003 ± 0.004 |
| | top | 5.054 | 5.060 | +0.005 ± 0.008 | level | +0.005 ± 0.011 |
| | night @10/7/5/4/3/2/1/0 | 6.243 | 6.258 | +0.016 ± 0.015 | **UP** | +0.011 ± 0.022 |
| | night @50/25/12/6/3/2/1/1 | 24.719 | 24.854 | +0.135 ± 0.107 | **UP** | +0.139 ± 0.148 |
| | night, doubling blinds | 5.872 | 5.870 | -0.001 ± 0.005 | level | +0.004 ± 0.006 |
| elite | elite | 4.856 | 4.874 | +0.018 ± 0.012 | **UP** | +0.021 ± 0.015 |
| | elite_night | 5.440 | 5.447 | +0.007 ± 0.008 | level | +0.006 ± 0.011 |
| | mirror | 4.506 | 4.522 | +0.016 ± 0.011 | **UP** | +0.022 ± 0.016 |
| | elite_b | 4.609 | 4.620 | +0.011 ± 0.011 | level | +0.015 ± 0.016 |
| | mirror_b | 4.501 | 4.526 | +0.025 ± 0.011 | **UP** | +0.023 ± 0.014 |
| exploit | exploit (8-max) | 5.765 | 5.754 | -0.011 ± 0.020 | level | -0.006 ± 0.026 |
| | exploit_3 | 8.491 | 8.485 | -0.007 ± 0.034 | level | +0.003 ± 0.036 |
| | exploit2 (8-max) | 5.849 | 5.846 | -0.003 ± 0.017 | level | +0.005 ± 0.024 |
| | exploit2_3 | 7.321 | 7.322 | +0.001 ± 0.032 | level | -0.023 ± 0.048 |
| | exploit3 (8-max) | 5.447 | 5.466 | +0.020 ± 0.019 | **UP** | +0.010 ± 0.029 |
| | exploit3_3 | 7.520 | 7.544 | +0.024 ± 0.045 | level | -0.007 ± 0.059 |
| | adapt (8-max) | 5.822 | 5.834 | +0.013 ± 0.016 | level | +0.017 ± 0.024 |
| | adapt_3 | 7.934 | 7.930 | -0.004 ± 0.031 | level | -0.022 ± 0.054 |
| | exploit_hu, exploit2_hu, exploit3_hu, adapt_hu | | | 0 | identical | |
| variants | top_heavy (realistic) | 28.455 | 28.401 | -0.054 ± 0.062 | level | |
| | fast_schedule (realistic) | 6.100 | 6.099 | -0.001 ± 0.004 | level | |
| | knockout_bounty / bounty / auction / bonus_card | | | +0.001 ± 0.006 / -0.001 ± 0.002 / -0.000 ± 0.003 / +0.000 ± 0.004 | level | |
| | the other 20 | | | 0 | identical | |

  Weighted (addendum 11): **W +0.0047 ± 0.0036, lower bound +0.0011**; W-min +0.0033 ± 0.0038, lower bound -0.0006;
  cap holds. No cell's raw and corrected flags point opposite ways (some are UP corrected and level raw). 0 timeouts
  and 0 errors in every cell. The per-seat gate costs about a third of R4's strong-table gain (elite +0.029 -> +0.018,
  mirror_b +0.033 -> +0.025, elite_b +0.017 -> +0.011) and takes away the three realistic-field losses (realistic
  -0.005 -> -0.002, top_heavy -0.084 -> -0.054, fast_schedule -0.008 -> -0.001) and most of exploit_3's (-0.063 ->
  -0.007).

## Summary

**What is on the branch** (all off by default; SHIP_DIALS unchanged; F plays bit-identically: 14 of 14 identity
chunks equal to main's at 9e3af86, ff07018 and the merged 8af4fda):
- `tools/solve_short.py three2`: the second three-handed tree (the small blind's flat and the big blind's squeeze, two
  3-bet sizes 2.3x / 3.3x, 4-bets, cold 4-bets, the old tree's blinds battle; one generic betting walk), terminal flops
  priced by a realization fitted from our own postflop (`fit3.py`'s offsets over the old model by SPR, our seat in
  position / out of position / two other seats, three-way flops tilted by seat), solved once per hero seat
  (asymmetric) at ICM 1 / 0.4 / 0, CFR+ 400 iterations, 512 configurations: median exploitability 0.04 milli-prizes
  a hand per hero solve. Push/fold sanity, convergence and realization tests in tests/test_s20_three.py.
- `tables/extra/short_3b.json` (3.19 MB; 2.43 MB zipped; 0.30 s to build the member).
- The specialist (`hyperion/strategy/short.py`): `three2` (the generic walker: raises map onto each node's stored
  sizes on a log scale, a raise at 45% of the effective stack or more is the jam), `three2_file`, `three2_roles`,
  `three2_keep_defence`, `three2_seat_rr`. The composite (`hyperion/compose/bot.py`): `short_strong` (the short route
  only while the strong route's table read is open).

**Recommended candidate R5** (docs/drills/climb/s20-candidate.json):
`{"short_route": "pre_3way=short", "short.three2": true, "short.three2_file": "3b", "short.defer_3bet": 0.25,
"short_strong": true, "short.three2_keep_defence": true, "short.three2_roles": "btn,sb", "short.defer":
"dead,station,maniac,random,nit", "short.three2_seat_rr": 1}`. In words: three-handed, on the button and in the small
blind, our first-in decisions and our answers to opens come from the equilibrium tables, while the table reads strong
(our opens re-raised 20%+), every opponent alive has re-raised us at least once, none 3-bets our opens at 0.25 or more
(exploiter 1 does) and none reads as a leak archetype; once our raise is re-raised, F's 3-bet defence plays; F plays
the big blind and every all-in answer. Screen: ACCEPT; elite, mirror, mirror_b, night (and night at both other payout
tables), exploit3 up; nothing down. A ship with it on must carry tables/extra/short_3b.json (tools/pack.py copies only
tables/*.json).

**Every candidate screened** (screen seeds; deltas corrected; 100 seeds unless marked):

| candidate | strong cells up | exploit cells down | other down | W |
|---|---|---|---|---|
| U: tables, no gate | elite, elite_b, mirror_b | exploit, exploit_3, exploit2, adapt | - | -0.0051 |
| G: + strong read + 3-bet guard 0.4 | elite, elite_b, mirror_b | exploit, exploit_3, exploit2, adapt | - | +0.0008 |
| G2: G + leak archetypes | elite, elite_b, mirror_b | exploit, exploit_3, exploit2 | - | +0.0000 |
| GX: G with the pessimistic table | elite_b, mirror, mirror_b | exploit, exploit_3, adapt | - | - |
| GK: G + keep the defence | elite, elite_b, mirror_b | exploit, exploit2 | - | +0.0063 |
| GK25: GK + guard 0.25 | elite, elite_b, mirror_b | exploit2 | - | +0.0070 |
| GXK25: GK25 with table 3c | elite, elite_b, mirror_b | exploit, exploit2 | - | +0.0079 |
| GK25R: GK25, button and SB only | elite, elite_b, mirror_b (200: + mirror) | none | (200) realistic | +0.0123 |
| R3: GK25R, pre_3way only | elite, elite_b, mirror_b | none | (200) realistic | - |
| R4: R3 + leak archetypes (200, full) | elite, mirror, elite_b, mirror_b; night | none | realistic, top_heavy, fast_schedule | +0.0058 |
| **R5: R4 + per-seat re-raise (200, full)** | **elite, mirror, mirror_b; night** | **none** | **none** | **+0.0047** |

**What I would try next**
- Re-fit the realization on R5's own flops and re-solve (the fit came from F's ranges; the tables play different
  ones; U's recordings already showed our out-of-position realization moving from -0.15 to -0.04 with the new
  ranges), and give the deep configurations 600+ iterations (60-90 bb: 0.2-0.4 milli-prizes at 400).
- The big blind: F's re-shove (+0.69 bb a hand at strong tables) beats the tables' 80-100% defence, which rests on
  weak hands realizing nearly their equity out of position, where the fit has no data. A tree whose big blind
  defends by fold / jam / 3-bet only below ~25 bb, or a fit with an equity-dependent term from the tables' own play.
- The heads-up tables still use S13's fixed flop model: the same fit and per-hero-seat solve would apply (`pre_hu`).
- The strong read counts every re-raise; a per-seat read of sized re-raises versus jams would tell push/fold bots from
  strong builds (the realistic field's few open tables).
- 4- and 5-alive jam/fold under ~15 bb (S14's pre_open_short gap, F +0.11-0.14 bb a decision against elite1's
  +0.27-0.43) was not built: step 1 recorded only two- and three-handed hands, and time went to the gates.
- 22:12 Final checks on the branch code 77634e3 (main merged, every S20 dial): identity 14 of 14 chunks equal to
  main's (`goal/s20/idchk4`); full suite `pytest -q -m "not timing"`: **1,416 passed, 5 skipped, 0 failed** (6:41).

# R6 (branch climb/s20-r6, from the coordinator's scoping branch climb/b7-scope at 863f9f5)

R5 on held-out H30 (50000-50399, the coordinator's run, `goal/b28/s20_h30.md`): **REJECT** on one guard, realistic
-0.003 ± 0.002 DOWN (raw -0.003 ± 0.003); every strong cell up at 400 seeds (elite +0.017, elite_night +0.009,
mirror +0.030, elite_b +0.017, mirror_b +0.020), night_hard +0.009 and exploit3 +0.017 up, the rest level; W +0.0027
± 0.0019, W-min lower bound -0.0013 (route 2 fails too). H30 is used. Task: find where the route opens in the
realistic room on fresh diagnostic seeds 11400-11999, fix one general gate before any screen, screen it.

R5 in the scoped terms (plays as R5, tests/test_b7_scope.py; `goal/s20/cand_R5s.json`): `{"short_route":
"pre_3way=short", "short.three2": true, "short.three2_file": "3b", "short.defer_3bet_three": 0.25, "short_strong":
"pre_3way", "short.three2_keep_defence": true, "short.three2_roles": "btn,sb", "short.defer_three":
"dead,station,maniac,random,nit", "short.three2_seat_rr": 1}`.

- 01:12 Recordings (`goal/s20/d6.py`: d3.py plus, at each of our three-handed preflop decisions, the strong read,
  every opponent's re-raises of our first-in raises, the 3-bet read, the archetypes and whether the tables played),
  snapshot worktree at 863f9f5: realistic, seeds 11400-11999 (600 x 8), R5 and F; elite, mirror, elite_b, mirror_b,
  night, night_hard, top, seeds 11400-11519, R5 and F. Workers 3, nice 5.

## R6 step 1: where R5's route opens in the realistic room (diagnostic seeds 11400-11999)

- 01:20 **Gate open rates** at our three-handed preflop decisions (`a6.py gates`; realistic 600 seeds x 8, elite 120):

| field | decisions | strong read open | every opponent has re-raised us | 3-bet guard ok | no leak archetype | all four | the tables played |
|---|---|---|---|---|---|---|---|
| realistic | 84,444 | 3.9% | 35.9% | 100% | 64.4% | 1.8% | 1.2% |
| elite | 8,382 | 54.2% | 51.4% | 100% | 94.3% | 33.0% | 20.5% |

  At realistic the tables play 1.2% of our three-handed decisions, against rival1 1.8% of its decisions, loose_aggro
  1.8%, pushfold 1.0%, tag 0.9%, timeout_then_recover 0.4%, the montecarlo bots 0.2-0.4%; by effective stack 2.4% under
  8 bb, 1.7-1.9% at 8-18, 1.2% at 18-27, 0.5-0.6% deeper.
- 01:25 **Paired results on these seeds** (raw points, rotations averaged; `paired.py`): realistic R5 - F **+0.0006 ±
  0.0025** (48 of 600 seeds play differently), elite +0.024 ± 0.018, mirror +0.024 ± 0.022, elite_b +0.043 ± 0.023
  (120 seeds each). On fresh seeds the realistic loss does not reproduce (screen -0.002 ± 0.002, H30 -0.003 ± 0.002,
  here +0.0006 ± 0.0025); pooled it is about -0.001 points a seed, from about 2% of table-rotations.
- 01:30 **Which decisions lose at realistic** (`a6.py diverge`, `div_detail.py`: each diverging table-rotation's
  points booked to its first decision that differs from F's; 95 of 4,800 diverge, +2.92 points in all): the button
  gains (42 divergences, +5.89: the tables raise where F raises, a different size, +4.74; fold where F raises +1.05),
  the small blind loses (46, -1.97): first in, the tables fold where F raises (7, -4.01) or limp where F raises (7,
  -1.22), mostly against rival1 in the big blind (19 divergences, -3.19) and at 12-18 bb (17, -4.27). At strong
  tables the same small-blind spots gain (elite: fold for F's raise +2.99, limp for F's raise +2.11; by seat elite BTN
  +9.22 / SB +12.42, mirror +14.34 / +8.43, elite_b +20.46 / +20.45). So the small blind's first-in fold / limp beats
  F's open-raise against strong big blinds and loses to it against the realistic room's big blinds, which fold to
  raises more.
- 01:35 **Reads that do not separate the realistic tables where the route opens from strong tables** (offline
  what-if on the first divergences, `whatif.py`; and `alive_share.py`, `persist*.py`): the alive opponents' share of
  the table's re-raises (realistic median 0.77, elite 0.63) and their own re-raise read (0.174 / 0.171); per-seat
  re-raises >= 2 (would remove realistic +3.31 but elite +19.0 of +23.1); the read at 0.22 (removes elite +4.5 to keep
  realistic +0.7); persistence (realistic tables whose read is open when play becomes three-handed lose, -2.05, the
  transient ones gain, +4.96: the opposite of a persistence gate).
- 01:38 **Who the tables play against** (survey at our three-handed decisions with R5, F's profiler, fold to
  preflop raises with 10+ faced, where the tables played; seeds 11600-11719 realistic, 11600-11639 elite, 11600-11629
  the others): realistic tag 0.91 [p10 0.85, p90 0.92] (vpip 0.15), pushfold 0.86 [0.84, 0.89], loose_aggro 0.76,
  rival1 0.73; strong builds 0.71-0.81 (medians: elite1 0.73-0.78, elite2 0.71-0.79, elite4 0.76-0.81, rival2
  0.77-0.81, rival3 0.77-0.80, rival1 0.72-0.78, F's copies 0.79, hybrid3_x 0.77) with p90 at most 0.89; the elite
  rooms' agent bots 0.83-0.85 (p90 0.86-0.89).
- 01:40 **By seat, the first-in decisions** (the first divergences, points summed, by the fewest re-raises of our
  first-in raises among the seats still to act, `sb_bbrr.py`): the button gains in every room and at every level
  (realistic +4.66 / +0.68 at 1 / 2-3 re-raises; elite +7.70 / +1.47; mirror +8.08 / +7.26; elite_b +14.92 / +7.30;
  mirror_b +9.82 / +5.50); the small blind's sign changes by room and not by what the big blind does (realistic -0.32
  / -1.94 / -1.68 at 1 / 2-3 / 4+; elite +3.60 / +4.65 / +4.61; mirror +4.40 / +0.32 / -0.86; elite_b +7.88 / +2.78 /
  +11.43; mirror_b +0.03 / +0.96 / -2.14). Split by the big blind's identity the small blind's results also flip sign
  between rooms for the same bot (rival1 as the big blind: realistic -3.19 over 19, elite +3.69 over 14, elite_b +5.18
  over 9), so no read of the opponents found here tells the rooms apart; what holds in every room is the seat.

## R6: the gate, fixed before any screen

**R6 = R5 with the tables on the button only** (`short.three2_roles` "btn"; F plays the small blind and the big
blind). Why this gate: in every room measured, the tables' button decisions beat F's own play (first-divergence sums:
realistic +5.89 over 42, elite +9.22, mirror +14.34, elite_b +20.46, mirror_b about +16.5; the biggest single spot,
the button folding where F min-raises, is positive in all five), while the small blind's first-in fold / limp beats
F's open-raise in some rooms and loses in others (realistic -1.97, mirror_b about -1.2, elite +12.4, elite_b +20.5),
and neither the table's re-raise read, the per-seat re-raises, the alive seats' own read, the read's persistence nor
the big blind's fold-to-raise read separates the rooms where it wins (above). The route's room read lets a few weak
tables through (1.8% of our three-handed decisions at realistic); where a decision's gain depends on that read being
right, F's play is the safe default; the button's gain does not depend on it. It keys on the decision (our seat),
not on any bot. Expected cost: about half of R5's strong-table gain (the small blind's share at elite and elite_b);
expected realistic effect: the small blind's losing divergences removed.

R6 in the scoped terms (`docs/drills/climb/s20-r6-candidate.json`): `{"short_route": "pre_3way=short",
"short.three2": true, "short.three2_file": "3b", "short.defer_3bet_three": 0.25, "short_strong": "pre_3way",
"short.three2_keep_defence": true, "short.three2_roles": "btn", "short.defer_three":
"dead,station,maniac,random,nit", "short.three2_seat_rr": 1}`. No code change (the dial exists).
- 01:36 The rest of step 1's recordings (R5 and F, seeds 11400-11519): gate rates at our three-handed preflop
  decisions, the tables' share of them: elite 20.5%, elite_b 28.7%, mirror 14.7%, mirror_b 16.1%, top 10.7%,
  night_hard 8.8%, night 5.1%, realistic 1.2% (strong read open 54-70% at the strong rooms, 16-33% at night, night_hard
  and top, 3.9% at realistic). Paired, raw: mirror_b +0.014 ± 0.021, night +0.005 ± 0.013, night_hard +0.008 ±
  0.018, top +0.003 ± 0.013. mirror_b by seat (first divergences): button +16.48 over 86, small blind -4.93 over 68:
  the small blind also loses there, which the R6 gate was fixed without (it was in hand only as "about -1.2" from
  the first-in rows).
- 01:32 R6's screen started (snapshot worktree at 863f9f5, the R6 code; screen set, stages exploit, elite, confirm,
  guards, variants, aware, runout term, --aim strong, --workers 3, nice 5; F's chunks pinned to bd36043bea as before).

## R6's screen

- 02:53 **R6, screen set 10000-10199** (stages exploit, elite, confirm, guards, variants (27), aware (5), runout term,
  --aim strong, --workers 3, nice 5; `goal/s20/R6_screen.out`, `r_R6_screen.json`, code 863f9f5 = the branch's;
  candidate key 0c92ed200fb5): **ACCEPT**.

| stage | cell | F | R6 | R6 - F (corrected) | | raw | R5 on the same seeds |
|---|---|---|---|---|---|---|---|
| confirm | night | 6.006 | 6.014 | +0.007 ± 0.005 | **UP** | +0.008 ± 0.009 | +0.008 ± 0.007 UP |
| guards | night_hard | 5.470 | 5.475 | +0.006 ± 0.007 | level | +0.002 ± 0.009 | +0.002 |
| | realistic | 6.350 | 6.348 | -0.002 ± 0.003 | level | -0.001 ± 0.005 | -0.002 ± 0.002 |
| | top | 5.054 | 5.059 | +0.005 ± 0.007 | level | +0.009 ± 0.012 | +0.005 |
| | night @10/7/5/... | 6.243 | 6.255 | +0.012 ± 0.013 | level | +0.017 ± 0.018 | +0.016 UP |
| | night @50/25/12/... | 24.719 | 24.779 | +0.060 ± 0.100 | level | +0.166 ± 0.136 | +0.135 UP |
| | night, doubling blinds | 5.872 | 5.871 | -0.000 ± 0.005 | level | +0.004 ± 0.006 | -0.001 |
| elite | elite | 4.856 | 4.869 | +0.013 ± 0.009 | **UP** | +0.012 ± 0.015 | +0.018 UP |
| | elite_night | 5.440 | 5.439 | -0.001 ± 0.007 | level | -0.003 ± 0.010 | +0.007 |
| | mirror | 4.506 | 4.520 | +0.014 ± 0.010 | **UP** | +0.017 ± 0.016 | +0.016 UP |
| | elite_b | 4.609 | 4.629 | +0.020 ± 0.010 | **UP** | +0.024 ± 0.015 | +0.011 |
| | mirror_b | 4.501 | 4.527 | +0.026 ± 0.010 | **UP** | +0.023 ± 0.013 | +0.025 UP |
| exploit | exploit / exploit_3 | | | -0.008 ± 0.018 / -0.003 ± 0.022 | level | | |
| | exploit2 / exploit2_3 | | | -0.012 ± 0.014 / +0.004 ± 0.018 | level | | |
| | exploit3 / exploit3_3 | | | +0.016 ± 0.016 / +0.012 ± 0.029 | level | | |
| | adapt / adapt_3 | | | +0.013 ± 0.015 / +0.024 ± 0.030 | level | | |
| | the four heads-up cells | | | 0 | identical | | |
| variants | top_heavy / fast_schedule | | | -0.016 ± 0.064 / -0.001 ± 0.003 | level | | |
| | bonus_card / auction / bounty / knockout_bounty | | | +0.002 / -0.000 / -0.001 / +0.002 | level | | |
| | the other 21 (tranche_holdem included) | | | 0 | identical | | |
| aware | bounty_aware | | | -0.000 ± 0.001 | level | | |
| | toss_or_holdem, short_deck, river_of_blood, tranche_holdem aware | | | 0 | identical | | |

  Weighted (addendum 11): **W +0.0030 ± 0.0022, lower bound +0.0009**; W-min +0.0016 ± 0.0023, lower bound -0.0006;
  cap holds (families: ordinary +0.0056, strong +0.0110, adapters +0.0018, twist-blind -0.0000, twist-aware -0.0001).
  No cell's raw and corrected flags point opposite ways. 0 timeouts, 0 errors.

  Read: all four strong cells but elite_night stay up with the button alone (elite_b even rises, +0.011 -> +0.020; the
  small blind lost there on the diagnostic seeds too, -4.93 at mirror_b), night stays up, and the exploit cells are
  all level. The realistic cell does not move on these seeds: -0.0021 ± 0.0028 against R5's -0.0020 ± 0.0025 (17 of
  200 seeds play differently from F, 10 of them lower), so the screen cannot say R6 removes what H30 saw; what the
  gate removes is the seat whose sign depended on the room. The realistic guard is the cell to watch on a held-out
  set.
- 02:56 Identity (`tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards` on the
  branch code, `goal/s20/idchk5`): 14 of 14 chunks identical to main's. Full suite on the branch (872a1e3, load 14):
  1,420 passed, 5 skipped, 7 failed; re-run alone at load 14, six pass (test_nightof_latency's three wall-clock round
  trips, test_sim_engine's rotation test, test_sim_mirror's strong_bvb test, test_sim_night's sampler test) and
  test_drills_run's swap_holdem drill still fails on wall-clock timeouts (2 timeouts, max 4.1 ms at load 14; S13 saw
  the same). None touches the specialist. tests/test_s20_three.py: 8 passed, 4 skipped (numpy) under the venv.
