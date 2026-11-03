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
