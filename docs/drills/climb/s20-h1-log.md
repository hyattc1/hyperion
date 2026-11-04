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
- 09:55 **The 10-20 bb ranges** (four strong rooms, `hu_ranges.py`: action shares by the hole class's quintile of
  tables/preflop_rank.json, q0 the weakest 20% of hands; fold / call / raise / jam, %):

| spot | bot | q0 | q1 | q2 | q3 | q4 |
|---|---|---|---|---|---|---|
| button first in | F | 58 / 0 / 42 / 0 | 0 / 0 / 100 / 0 | 0 / 0 / 100 / 0 | 0 / 0 / 100 / 0 | 0 / 0 / 100 / 0 |
| | elite1 | 36 / 0 / 25 / 39 | 13 / 0 / 46 / 41 | 4 / 0 / 54 / 42 | 0 / 0 / 56 / 43 | 0 / 0 / 54 / 46 |
| | elite2 | 73 / 0 / 0 / 27 | 67 / 0 / 5 / 28 | 10 / 0 / 60 / 30 | 0 / 0 / 70 / 30 | 0 / 0 / 70 / 30 |
| big blind vs a min-raise | F | 74 / 0 / 0 / 26 | 66 / 0 / 0 / 34 | 46 / 14 / 0 / 39 | 11 / 24 / 0 / 65 | 0 / 55 / 8 / 37 |
| | elite1 | 41 / 0 / 0 / 59 | 29 / 3 / 0 / 67 | 19 / 11 / 0 / 69 | 5 / 12 / 0 / 82 | 0 / 3 / 0 / 96 |
| | elite2 | 19 / 0 / 0 / 81 | 14 / 0 / 0 / 86 | 11 / 4 / 0 / 86 | 2 / 75 / 0 / 23 | 0 / 61 / 0 / 39 |

  F's button min-raises every hand above the bottom fifth and jams none; elite1 jams about 40% of every quintile (a
  balanced jam) and elite2 30%. F's big blind folds two thirds of its bottom 40% to a min-raise and flat-calls 55% of
  its top fifth; elite1 re-shoves 59-96% across the quintiles, elite2 81-86% of its weaker 60% and flats its best.
- 10:00 **Realization by our own equity at low SPR** (our heads-up flops at the four strong rooms, SPR under 5,
  against seats other than our copies; share - E with its 95% interval, the old model beside): in position E 0.2-0.4
  +0.092 ± 0.047 (1,860; old +0.021), 0.4-0.6 +0.076 ± 0.058 (1,482; +0.030), 0.6-0.8 +0.134 ± 0.107 (713; +0.029);
  out of position 0.2-0.4 +0.025 ± 0.078 (868; old -0.032), 0.4-0.6 -0.002 ± 0.052 (1,691; -0.031), 0.6-0.8 -0.039 ±
  0.051 (1,692; -0.022). Flat across equity within noise, so the offset-by-SPR form of the three-handed fit fits
  heads-up too; weak hands out of position show no extra penalty at these SPRs (unlike the three-handed question
  about the big blind's 100% defence, where the data had no weak hands).
- 10:05 **The heads-up fit with the ordinary room added** (night, elite_night, seeds 14400-14799; `real_hu_v1.json`,
  committed as docs/drills/climb/s20-h1-real.json for the solve): our share - E at E = 0.5, SPR 2 / 6 / 15:

| | SPR 2 | SPR 6 | SPR 15 |
|---|---|---|---|
| our button (in position), mix of the three groups (18,676 flops) | **+0.135** | +0.082 | +0.098 |
| ... strong / night / exploit | +0.121 / +0.187 / -0.006 | +0.040 / +0.075 / +0.114 | +0.315 / +0.240 / +0.082 |
| our big blind (out of position), mix (17,300) | **+0.027** | -0.053 | -0.101 |
| ... strong / night / exploit | +0.025 / +0.039 / -0.057 | -0.036 / -0.021 / -0.199 | +0.243 / +0.291 / -0.130 |
| two other seats (in position), mix of strong and night (21,441) | +0.083 | +0.100 | -0.094 |
| old model, in position / out of position | +0.016 / -0.016 | +0.047 / -0.047 | +0.062 / -0.062 |

  How much the fit moves across fields: at SPR 2, by 0.19 in position (night +0.187 against exploit -0.006) and 0.10
  out of position (night +0.039 against exploit -0.057); strong and night agree within noise, the exploit cells are
  the outlier (our out-of-position flops against the exploiters lose at every SPR). SPR 15 is poorly measured outside
  the exploit cells (heads-up flops that deep are rare at 8-max tables).

## H1: the plan, and how it coexists with S7

**Target.** Heads-up preflop at 10-20 bb at strong tables (F's button -0.28 to -0.32 bb a hand there, the elites up
to +0.09; F's big blind +0.22 against their +0.38-0.50), where F min-raises every button above the weakest fifth and
never jams, and its big blind folds two thirds of its weaker hands to a min-raise and flats its best. Under 10 bb and
at 20-40 bb F is level with the elites.

**Solve (next session).** S13's heads-up tree (`solve_short.py hu`) with: (1) the flop priced by this fit, per seat
(the button's flops at our in-position share, the big blind's at our out-of-position share; one solve per hero seat,
each keeping its own nodes, as three-handed); (2) the button's limp dropped below 25 bb (no bot here limps, so the
limped pot's realization is unmeasured; S13's tree limps 35-88% at 10-20 bb on the old model); (3) two 3-bet sizes
(2.3x / 3.3x as three-handed) and the 45%-of-stack jam mapping; (4) ICM is chip EV heads-up (exact). Depths 5-100 bb
as S13; the route only reads 8-40 bb if the screen says the deeper ones do not help.

**Coexistence with S7.** S7's heads-up routes (`pre_hu`, `post_hu_bet`, `post_hu_chk` to the specialist, big blind
only, behind `short.like_*` with `like_max_alive` 2) stay exactly as accepted: in `ShortMember.wants` the like gates
are checked first and, when they admit the seat, the decision is S7's (its tables, its roles). H1 adds a second
heads-up path behind a new dial (`short.hu2`, off): only when the like gates do *not* admit the seat (so never on an
S7 decision) and only while the composite's strong read is open for heads-up. The strong read cannot use
`short_strong` "pre_hu" (that would also shut S7's route on weak-reading tables), so the composite passes its read to
the member (one boolean set before `wants`, as it passes the profiler), and H1 checks it itself. A test will replay S7
with `short.hu2` on and require its decisions and digests unchanged (tests/test_b7_scope.py's pattern).

## The code half (the coordinator, 09:50: the tree, the fitted flops, push/fold, a small solve, the member path)

- 09:52 **`tools/solve_short.py hu2`** (block "heads-up, v2 (S20 H1)", pure Python like `hu`): `hu2_tree(S, real,
  hero)`. The button folds / opens (2.0 bb to 25 bb, 2.25 to 60, 2.5 deeper) / jams, and limps only from 25 bb
  (`H2_LIMP_MIN`; over a limp the big blind checks / raises to 2.5-3 bb / jams); the big blind facing the open folds /
  calls / 3-bets 2.3x / 3-bets 3.3x / re-shoves; the button facing each 3-bet folds / calls / 4-bets 2.2x / jams; the
  big blind facing a 4-bet folds / calls / jams; anyone facing a jam folds / calls; a raise over 40% of the stack (45%
  for 4-bets) is the jam. Chip EV (exact heads-up). Flops: `realize_h2(real, spr, mode)`, our seat's fitted share
  for the hero's position (`hero_ip` the button, `hero_oop` the big blind; offsets over the old model by SPR, as the
  three-handed fit); every heads-up flop has the hero in it, so a depth is solved once per hero seat and each seat
  keeps its own nodes (`solve_hu2_depth`). Nodes carry their raise sizes ("z"). `cmd_hu2`: depths, iterations,
  `--real` (default the old model), out tables/short_hu2.json. Sizes at 15 bb: 6 decision nodes (no limp, one 3-bet
  size: the big one is a jam there); at 20 bb 8; at 30 bb 14; at 60 bb 16.
- 09:53 The fit for the solve: docs/drills/climb/s20-h1-real.json (the three-group mix above) with shares clipped to
  [-0.3, 1.3] as three-handed.
- 09:54 **A small solve** (15 and 40 bb, 400 iterations, the fit, 2 workers: 18 s and 48 s): exploitability in the
  abstract game, mbb a hand, per hero seat (button / big blind): 15 bb 2.41 / 2.44 at 100 iterations, 0.76 / 0.72 at
  200, 0.38 / 0.40 at 300, **0.24 / 0.26** at 400; 40 bb 11.6 / 19.3, 4.7 / 6.9, 2.9 / 3.8, **2.0 / 2.6** (S13's `hu`
  at 40 bb: 1.2-1.3 at 500). Committed as tables/extra/short_hu2_dev.json (15 KB), a development fixture for the
  tests, not a table to play from. What it plays at 15 bb: the button folds 30% / min-raises 67% / jams 2% (by hand-
  strength fifth: folds the weakest fifth, half the second, raises the rest); the big blind against the min-raise
  folds 0% / calls 69% / 3-bets 3% / re-shoves 28% (calls 84-99% of its weaker 60%, re-shoves 42% / 76% of the top two
  fifths); facing the 2.3x 3-bet the button folds 16% / calls 60% / jams 23%. At 40 bb the button limps 56% and raises
  44%. So with our fitted flops (out of position +0.03 of the pot at SPR 2) the equilibrium big blind flats rather
  than re-shoves, unlike the elites' 60-80% re-shoves: the screen will say which is right against strong tables.
- 09:55 **The member path** (`hyperion/strategy/short.py`): `wants` is now S7's own path first (`_wants_s7`, the old
  body unchanged, its like gates factored into `_like_ok` with the same arithmetic), then, only if S7's path refuses,
  `_wants_hu2`: preflop, heads-up, no antes, the composite's strong read open (`strong_open`), the opponent *not*
  admitted by the like gates (a seat S7's gates admit is never H1's), `hu2_defer_3bet` and the archetype deferral,
  `hu2_keep_defence`, the hand mapping onto the hu2 table (`_hu2_node`, the generic walker with `_map_raise2`), our
  seat in `hu2_roles`, the depth in [`hu2_min`, `hu2_max`]. Dials `short.hu2`, `hu2_file`, `hu2_roles`,
  `hu2_defer_3bet`, `hu2_keep_defence`, `hu2_min`, `hu2_max`, all off. The composite (`hyperion/compose/bot.py`) sets
  the member's `strong_open` from `strong_table()` before each `wants` when the member asks for it (`needs_strong`,
  true only with `short.hu2`), and keeps the read then.
- 09:56 **Tests** (tests/test_s20_h1.py, 10, all pass; with test_s13_short, test_compose, test_ship: 72 passed): the
  tree's lines; the default flop model equals the old `realize_mats` exactly; the fit raises our in-position share;
  **push/fold sanity**: the tree cut to fold / jam at 10 bb gives tables/pushfold_hu.json's push and call
  frequencies within 0.02; a small solve converges (12 bb, under 4 mbb a hand at 120 iterations); the walker maps an
  open and a 2.3x 3-bet onto "rs"; F builds no second path by default; with the strong read shut (strong_rr 0.99) F
  plays bit-identically to batch 7 against exploiter 2 heads-up; **S7's decisions stay S7's**: with `short.hu2` on at
  the shipped threshold, at every decision S7's own path wants (a twin member without hu2 replays each, 100+ of them
  against exploiter 2) the decision is S7's with S7's action, and those tables play bit-identically to batch 7; the
  second path plays against elite1 heads-up when the read is open.
- 09:58 **A coexistence finding to resolve before screening.** With the strong read forced always open (strong_rr
  0.01) against exploiter 2 heads-up, H1 takes the early preflop decisions, and exploiter 2's probe read (the one S7's
  gate keys on) then never climbs past 0.3-0.48 (batch 7 alone: 0.72 at hand 10, 0.82-0.90 from hand 20), so S7 never
  plays: H1's preflop changes the postflop spots S7's read is measured in. At the shipped threshold (0.2) this does
  not happen against exploiter 2 (the read stays at 0.14-0.19 heads-up, H1 plays 0-3 decisions a table and S7's 50 are
  unchanged), but against exploiter 1 heads-up the read is 0.32-0.48 and H1 plays (S7 never plays there), and at
  8-max strong tables the read is open at heads-up time most of the time. Options for the next session: keep H1 off
  until the like reads have enough chances to have refused (the probe read's chances, `pb_opp`), or let S7's gate be
  read from the table's 8-max play only; and the exploiter-1 guard (`hu2_defer_3bet` 0.25, `hu2_keep_defence`) as in
  R6.
- 10:01 **Identity** (`tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards` on the
  branch at 3479ca4, `goal/s20/idchk6`): 14 of 14 chunks identical to batch 7's reference (`goal/idchk34/post`).

## Where I am / next (10:10, before the 11:30 shutdown)

- **Done:** the measuring half (above) and the code half: the hu2 tree and its per-seat solve with the fitted flops,
  the push/fold check, a two-depth solve that converges (fixture tables/extra/short_hu2_dev.json), the member's
  `short.hu2` path behind its dial with S7's decisions kept S7's (tested), the composite passing its strong read,
  identity with batch 7 (14 of 14). Full suite: see the line below.
- **Next (after the restart):** (1) decide the coexistence rule above (H1 off until S7's like reads have refused with
  enough chances, or S7's gate read from the 8-max part) and the exploiter-1 guard; (2) the full solve:
  `tools/solve_short.py hu2 --real docs/drills/climb/s20-h1-real.json --iters 600 --workers N` over HU_DEPTHS (26
  depths x 2 hero seats, pure Python: about 2 x S13's 19 minutes on 2 workers, less on the new cores); (3) diagnostics
  of the new table on seeds 14800-14999 (the 10-20 bb lines against F's, `h1a.py`); (4) the screen on 10000-10199,
  every stage, runout term, --aim strong, with candidates H1 (`short.hu2` on, roles sb,bb) and, if the big blind's
  flat-heavy equilibrium loses to F's re-shoves, H1 on the button only; (5) identity against goal/idchk34/post again.
