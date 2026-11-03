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
