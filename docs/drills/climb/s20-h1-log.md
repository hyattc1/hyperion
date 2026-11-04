# S20 H1: a solved heads-up preflop for strong tables (running log)

Branch climb/s20-h1, from main f028f50 (batch 7 is F: S7's heads-up specialist routes `pre_hu`, `post_hu_bet`,
`post_hu_chk` to the specialist behind its looseness gate). The three-handed work (S20, R5, R6) and its method are in
docs/drills/climb/s20-log.md on climb/s20-three and climb/s20-r6 (R6 accepted on H32, in batch 8). Task (coordinator,
2026-11-04): heads-up preflop solved per seat with the same method (a realization fit from our own postflop, a richer
tree, a per-seat solve), for strong tables, coexisting with S7's decisions. This session is the measuring half only
(the machine stops for a hardware change at 11:30 ET): diagnosis on fresh diagnostic seeds 14000-14999, the heads-up
realization fit by SPR, where F loses heads-up at strong tables by line. No screen, held-out or judge seed is used.

## Runs (appended as each finishes)

- 09:23 Recordings of F (batch 7) with `goal/s20/d6.py` (d3.py's recorder: every hand that starts with two or three
  alive, every decision, every seat's hole class, the deltas, and per decision whether the specialist made it),
  snapshot worktree at f028f50, workers 3, nice 5: elite, mirror, elite_b, mirror_b on seeds 14000-14299; exploit_hu,
  exploit2_hu, exploit3_hu, adapt_hu (rules hu.json) on 14300-14399; night on 14400-14599; elite_night on 14600-14799.

## Step 1: where F loses heads-up at strong tables

- 09:36 **First line book, elite + mirror** (seeds 14000-14299 each, hands that start heads-up; `goal/s20/h1a.py`,
  bb a hand booked to each decision's spot, ± the 95% interval). S7's specialist made none of F's heads-up decisions
  at these tables (its looseness gate admits exploiter-2-like seats only), so this is batch 7's own heads-up play.

| bot | button (SB) bb a hand | big blind bb a hand |
|---|---|---|
| F | +0.007 ± 0.072 (13,190 hands) | +0.080 ± 0.064 |
| elite1 | +0.160 ± 0.076 | +0.206 ± 0.066 |
| elite2 | +0.051 ± 0.063 | +0.185 ± 0.079 |
| rival2 | -0.048 ± 0.056 | -0.078 ± 0.065 |

| spot | F | elite1 | elite2 |
|---|---|---|---|
| button first in: fold / raise / jam | 11% / 75% (-0.0) / 14% (+0.4): +0.01 | 9% / 58% (+0.2) / 33% (+0.3): +0.16 | 31% / 43% / 26%: +0.05 |
| button facing a jam: fold / call | **3,062 times**, 90% / 10%: -1.48 | 1,153, 91% / 9%: -1.91 | 991, 77% / 23%: -1.03 |
| button facing a 3-bet up to 3.6x: fold / call / 4-bet / jam | 55% / 2% / 15% / 28% (-5.2): -2.69 (260) | 55% / 28% / 2% / 15%: -3.04 (297) | 87% / 10% / - / 2%: -2.59 |
| big blind vs an open of 2.25 bb or less: fold / call / 3-bet / jam | 44% / 26% / 3% / 27% (+1.4): **+0.15** | 33% / 15% / 2% / 51% (+1.4): **+0.43** | 15% / 42% / 3% / 41%: +0.30 |
| big blind vs an open of 2.25-3 bb | 48% / 37% / 4% / 10%: -0.07 | 48% / 22% / 3% / 27%: +0.01 | 36% / 39% / 5% / 20%: +0.05 |
| big blind vs a jam: fold / call | 79% / 21%: -0.28 (3,160) | 83% / 17%: -0.44 | 68% / 32%: -0.39 |

  The same shape as three-handed: F's button min-raises 75% and is re-shoved on nearly three times as often as
  elite1's (3,062 against 1,153), folding 90% of those; elite1 jams a third of its buttons. F's big blind folds 44% to a
  min-raise and re-shoves 27% where elite1 folds 33% and re-shoves 51% (+0.43 a hand against +0.15).
- 09:40 **By effective stack** (elite + mirror, `h1a.py --by-depth`): the loss is at 10-20 bb, nearly nowhere else.

| depth | F button | elite1 button | F big blind | elite1 big blind | elite2 big blind |
|---|---|---|---|---|---|
| under 10 bb | +0.393 ± 0.168 (1,997) | +0.343 ± 0.166 | -0.332 ± 0.148 | -0.266 ± 0.137 | |
| 10-20 bb | **-0.284 ± 0.089** (6,938) | +0.057 ± 0.107 | **+0.233 ± 0.088** (7,013) | +0.431 ± 0.097 | +0.431 ± 0.114 |
| 20-40 bb | +0.268 ± 0.154 (4,012) | +0.204 ± 0.131 | +0.021 ± 0.121 | +0.120 ± 0.114 | +0.051 ± 0.136 |
| 40+ bb | +0.829 ± 0.520 (243) | +0.834 ± 0.905 | -0.070 ± 0.310 | +0.041 ± 0.604 | |

  At 10-20 bb F's button raises 88% and never jams (-0.28 bb a hand), elite1 raises 48% and jams 42% (+0.06); F's
  button then faces a jam 2,705 times there (elite1 966) and folds 90% (-1.51 a hand in that spot). F's big blind
  against a min-raise at 10-20 bb folds 39% and re-shoves 41% (+0.30), elite1 folds 21% and re-shoves 73% (+0.80),
  elite2 folds 11% and re-shoves 61% (+0.60). Under 10 bb F pushes 95% of buttons, like the elites, and at 20-40 bb
  F's button is level with them. So the heads-up target is 10-20 bb, where a jam-or-fold button and a re-shove-heavy
  big blind beat F's min-raise-and-fold; that is also where a flop's realization matters least (SPR under ~4).
- 09:42 **For comparison, S13's heads-up equilibrium** (tables/short_hu.json, chip EV, the old fixed flop model):
  at 10-20 bb its button folds 1-22%, *limps* 35-88% (more as stacks deepen), never min-raises, and jams 42% at 10
  bb, 15% at 16, 3% at 20; its big blind against an open folds 2-9%, calls 54-72%, jams 21-36%. Neither F nor the
  strong builds limp (F's big blind faced a limp 73 times in 26,328 heads-up hands), so the limped pot's realization,
  on which that limp-heavy button rests, cannot be measured from our own play; the re-solve should either drop the
  button's limp below ~25 bb or price it from the big blind's side of limped pots, and say which.
- 09:41 **Replicated at elite_b + mirror_b** (seeds 14000-14299): F's button at 10-20 bb -0.316 ± 0.096 (6,187
  hands; elite1 -0.062 ± 0.108, elite2 +0.085 ± 0.103), F's big blind at 10-20 bb +0.220 ± 0.095 (elite1 +0.496 ±
  0.105, elite2 +0.384 ± 0.111, elite4 +0.217 ± 0.121); at 20-40 bb F's button +0.233 (elite1 +0.305) and big blind
  -0.115 (elite1 +0.124, elite4 -0.109); under 10 bb F's button +0.169 (elite1 +0.334). Across the four strong rooms F
  gives up about 0.3 bb a hand on the button and 0.2-0.25 in the big blind at 10-20 bb to the best builds, about 13,000
  hands of each role per 600 tables-seeds x 8.

## Step 1b: heads-up realization by SPR, and where S7 plays

- 09:45 **Where batch 7's S7 plays heads-up** (the exploit fields, seeds 14300-14399, `h1a.py --split-s7`): only as
  the big blind against exploiter 2 (3,342 decisions facing its open, 181 facing a jam), 13 decisions against adapt1,
  none against exploiters 1 and 3 and none at the four strong rooms. F's heads-up bb a hand by role (button / big
  blind): against exploiter 1 +1.491 / -0.320, exploiter 2 -0.501 / -0.109, exploiter 3 +0.104 / -0.286, adapt1
  +0.328 / +0.047. So H1 and S7 barely overlap in the field: S7 is an exploiter-2 read, H1 a strong-table one.
- 09:47 **Heads-up realization** (`fit3.py` with ALIVE=2: flops in hands that start heads-up; our share of the flop
  pot over the old model's E + k E (1 - E) + s (b_ip - b_oop), piecewise linear at SPR 2 / 6 / 15; groups strong =
  elite, mirror, elite_b, mirror_b, exploit = the four heads-up exploit cells, equal weight; `goal/s20/real_hu_v0.json`,
  `fit_hu_v0.txt`). Our share - E at E = 0.5:

| | SPR 2 | SPR 6 | SPR 15 |
|---|---|---|---|
| old model, in position / out of position | +0.016 / -0.016 | +0.047 / -0.047 | +0.062 / -0.062 |
| our button (in position), mix (14,782 flops) | +0.086 | +0.079 | +0.091 |
| ... strong rooms (7,650) / exploit cells (7,132) | **+0.121** / -0.006 | +0.040 / +0.114 | +0.315 ± 0.39 / +0.082 |
| our big blind (out of position), mix (14,765) | +0.029 | -0.092 | -0.137 |
| ... strong / exploit | **+0.025** / -0.057 | -0.036 / -0.199 | +0.243 ± 0.38 / -0.130 |
| two other seats (the in-position one), strong (13,340) | +0.049 | +0.134 | -0.385 ± 0.34 |

  (offsets' 95% intervals: ±0.05-0.07 at SPR 2 and 6 for the strong group, ±0.06-0.15 for the exploit group, ±0.35-0.4
  at SPR 15 for strong, where heads-up flops at strong tables are rare.) Read: at the depths that matter here (10-20
  bb, SPR 1-4 after a called min-raise) our heads-up postflop at strong tables realizes more than the old model
  assumed in both seats (in position +0.12 of the pot at E = 0.5, out of position +0.03 instead of -0.02), while
  against the exploiters our out-of-position flops lose (-0.06 to -0.20). How much the fit moves across fields: at
  SPR 2 by +0.13 in position and +0.08 out of position between the strong rooms and the exploit cells.
- 09:50 **What heads-up is worth at strong tables** (`huwin.py`, the four strong rooms, seeds 14000-14299 each; the
  first hand with two alive in each table-rotation; win = finishing first): F reaches heads-up 2,173 times and wins
  48.4% at a mean chip share of 47.4% (+1.0 points over its chips); elite1 68.5% at 58.7% (+9.7), elite2 65.0% at
  58.0% (+7.0), rival3 +2.5, elite4 -1.3, F's copies -3.9, rival2 -3.6. By our chip share when heads-up begins (F /
  elite1 / elite2): under 35% 18.6% / 36.9% / 27.3%; 35-50% 43.5% / 52.2% / 53.7%; 50-65% 59.7% / 68.1% / 67.3%; 65%+
  81.1% / 88.9% / 84.2%. Under 8..1 a heads-up win is one point, so converting like elite1 (+8 points of win share a
  heads-up) at F's reach (about 23% of strong tables) would be about +0.02 points a table: the size of R6's strong-
  table gain again.
