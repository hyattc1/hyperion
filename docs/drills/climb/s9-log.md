# S9 + S10: F at strong tables (mirror field, first-place conversion)

Branch climb/s9-strong-tables, from main 77d8932. Protocol: docs/drills/goal-plan.md section 2 and addendum 8 (a
strong-table change is accepted on a held-out set when it is beyond noise up on at least one of elite, elite_night or
mirror and beyond noise down on nothing else). This worker screens only: seeds 10000-10199 (`--set screen`) and fresh
seeds under 10000 for diagnostics; the coordinator runs the held-out confirmation. No judge bot, judge field or held-out
variant is run, read or tuned on here.

## 1. The mirror field

- `f_copy` (hyperion/sim/bestiary.py, ShipCopy): a copy of F as it ships (SHIP_DIALS, light shadows, the bestiary's
  model-mode settings through compose.bot.sim_kwargs, the same helper tools/swap.py's registered seats now use). It
  follows SHIP_DIALS, so when the ship changes the copies change with it.
- `mirror` = hero, f_copy x3, rival2, elite1, elite2, hybrid3_x (the strongest general bots we may tune on, F's own
  base among them).
- `mirror_night` = hero, f_copy x2, elite1, elite2 and elite_night's first three drawn night seats (diagnostic).
- climb_accept's elite stage now measures elite, elite_night and mirror.
- Copies of one bot at one table: the runner builds every seat its own instance with its own seed
  (table_seed * 64 + rotation * 8 + seat). tests/test_sim_mirror.py replays each of three copies alone, in a fresh
  instance with its seed and the observations it saw at the table, and every decision matches, so no copy's play
  depends on another's state; the field replays exactly in model mode; points sum to 36 a table.
- Cost: about 2.3 s per seed (8 rotations) in one process, about twice elite.

## 2. Diagnosis (diagnostic seeds 8000-8199, never used before; model mode, 8 rotations)

Tools (session scratchpad `goal/s9/`, not committed): `s9_diag.py` plays a field with every seat wrapped in
tools/skill_profile.py's Tracer (one counts table per bot name) and snapshots the stacks when a table first reaches
three and two players; `s9_spots.py` books, per bot and section, the hand's first decision there and the hand's net.

### Where F ranks (200 seeds x 8 each)

| field @ payouts | 1st | 2nd | 3rd | F | F's 1st % (best elite build's) |
|---|---|---|---|---|---|
| elite @ 8..1 | rival2 4.906 | **F 4.714** | elite2 4.642 | 2nd of 8 | 11.6 (elite2 19.4) |
| elite @ 50/25/12/6/3/2/1/1 | rival2 14.80 | elite2 14.75 | **F 13.89** | 3rd of 8 | 15.1 (elite2 18.9) |
| mirror @ 8..1 | rival2 4.791 | hybrid3_x 4.554 | f_copy 4.448 | **last: 4.432** (elite1 4.441, elite2 4.439) | 8.1 (elite1 23.4) |

Screen seeds (10000-10199), F alone: night 5.973, elite 4.681, elite_night 5.329, mirror 4.416.

In the mirror F is last of six names (its three copies average 4.448), 0.36 behind rival 2 and 0.12 behind its own base
hybrid3_x. It reaches three-handed 34% of the time with 30% of the chips and wins 23% from there (elite1 61%, elite2
51% with 39-42% of the chips); heads-up it wins 37.5% with 46.7% of the chips (elite1 73% with 61%). (Tables that
reach the 200-hand cap order survivors by chips but pay ICM, so "1st" there flatters chip leaders; the points do not.)

### By section (chips won per decision, bb; same tables, every seat traced)

Three sections lose against all three strong builds, in every strong field and both payout tables:

| section (share of F's decisions) | F | rival2 | elite2 | elite1 |
|---|---|---|---|---|
| elite, pre_open_10 (unopened 10-20 bb, 6%) | **-0.125** | +0.095 | +0.134 | +0.179 |
| elite, pre_3way (three-handed preflop, 4%) | **+0.018** | +0.238 | +0.272 | +0.356 |
| elite, pre_hu (heads-up preflop, 3.5%) | **+0.072** | +0.196 | +0.319 | +0.248 |
| mirror, pre_open_10 | **-0.097** | +0.086 | +0.141 | +0.276 |
| mirror, pre_3way | **+0.083** | +0.268 | +0.350 | +0.438 |
| mirror, pre_hu | **-0.007** | +0.231 | +0.317 | +0.314 |

Per 8 tables that is 15-50 bb (2-6 bb a table) behind each strong build in these three sections together. F is ahead
after the flop facing a bet (Hero's post_hu_bet: +0.27 vs rival2 -0.22, elite1 -0.28) and level or ahead elsewhere,
except deep 3-bet play against rival 2 (pre_raised_deep +0.003 vs +0.060) and the re-shove section (pre_raised_short
+0.25 vs rival 2's +0.45).

### Why: F min-raises too often there and folds a third of those raises to a re-raise

Hand's first decision in the section (elite, seeds 8000-8059 x 8):

| spot | F | rival2 | elite2 | elite1 |
|---|---|---|---|---|
| pre_open_10: raise / shove / fold | 54% / 0% / 45% | 17% / 6% / 76% | 21% / 15% / 64% | 14% / 24% / 62% |
| ... share of the raises then folded to a re-raise (-2.2 to -2.5 bb each) | **35%** | 24% | 30% | 25% |
| ... net bb over the section | +15 | +628 | +583 | +653 |
| pre_3way: raise / shove / fold | 45% / 13% / 36% | 13% / 17% / 63% | 23% / 22% / 46% | 19% / 25% / 46% |
| ... raises folded to a re-raise | **34%** | 18% | 22% | 17% |
| ... net bb | +75 | +201 | +538 | +815 |
| pre_hu: raise / shove / fold | 46% / 12% / 31% | 22% / 18% / 49% | 28% / 21% / 37% | 36% / 28% / 28% |
| ... raises folded to a re-raise | **32%** | 21% | 16% | 19% |
| ... net bb | -104 | -277 | +290 | +376 |

The mirror shows the same (F raises 45% / 36% / 41% of these spots and folds 37% / 44% / 46% of those raises). The
raises are rival 3's core's (the base), not the exploit layer's (the layer's steals are 60 of ~1,600 opens on
elite): its raise-first-in rule also opens any hand up to the 85th percentile whenever `pf * pot - (1 - pf) * size *
0.55 > 0` (pf: everyone behind folds), a price that never counts a re-raise, and short-handed it widens every
threshold by 1.2. It shoves only at 10 bb or less; rival 2 shoves at 13 bb or less (16 with two behind) and elite2 at
14 or less. Against weak seats the min-raise steal works (they fold or call); strong bots re-shove it.
