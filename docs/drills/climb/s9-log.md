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

## 3. Adopting the strong builds' play in the three sections

The composite can route a section to another member, so adopting a better bot's code for a section is a route, not a
rewrite. New members (e3a7d6f): `elite1`, `elite2` (PersonaMember: the frozen builds through the bestiary's adapter,
the generator seeded per decision). Rival 2's core is already the `r2` member (donor `r2x`).

Runs: `climb_accept` on the screen seeds (10000-10199, 200 x 8), stages confirm and elite, base F. The base's cached
chunks are pinned to code version ab31e165de (scratch wrapper `goal/s9/s9_accept.py`): F's play does not change while
dials that are off by default are added (tests/test_sim_mirror.py; the light-shadow and gate tests below).

| candidate (sections pre_open_10, pre_3way, pre_hu to) | night | elite | elite_night | mirror |
|---|---|---|---|---|
| E1: elite1x | **-0.117 ± 0.074** | **+0.192 ± 0.084** | **+0.108 ± 0.069** | **+0.258 ± 0.088** |
| R2: r2x (rival 2's core) | -0.052 ± 0.067 | **+0.194 ± 0.078** | **+0.134 ± 0.061** | **+0.225 ± 0.085** |
| E2: elite2x | **-0.076 ± 0.065** | **+0.183 ± 0.083** | **+0.123 ± 0.059** | **+0.242 ± 0.077** |

All three strong builds' play gains about the same at strong tables, so the gain is in leaving rival 3's core's way in
these sections, whichever strong bot replaces it; and F's own way is worth more on night, where its wide min-raise
steals take what weak seats give away.

E1 is the size of the prize: at every strong table F plays elite1's way in those three sections and gains 0.1-0.26
points, which takes F from 2nd to 1st on elite (4.87 vs rival 2's 4.91 on the diagnostic seeds) and from last to 2nd
on the mirror. It loses on night: elite1's tighter opens give up F's profitable steals against weak seats.

Latency: as a full shadow on every decision elite1 adds about 26 us a decision (latency.py at load 10: mean 62 -> 88
us, p99 258 -> 358). With its light shadow (scan the history only; e3a7d6f) the cost is 62.4 -> 65.9 us mean, p99
within noise (150 vs 241 at load 10). The light shadow plays exactly as the full one (test).

## 4. A gate by the table's observed play

The leak's mechanism is F's first-in raise being re-raised. How often that happens (s9_rr.py, seeds 8400-8419 x 8,
F's non-all-in first-in preflop raises; overall / three-handed / heads-up):

| field | re-raised | 3 alive | 2 alive |
|---|---|---|---|
| night | 13.7% | 15.0% | 8.2% |
| night_hard | 16.7% | 19.4% | 12.5% |
| realistic | 11.9% | 12.0% | 9.7% |
| top | 20.4% | 23.1% | 24.6% |
| elite_night | 18.1% | 21.8% | 20.5% |
| elite | 24.0% | 31.2% | 32.2% |
| mirror | 25.9% | 49.0% | 31.6% |

So the composite's new `strong_route` (c833522) plays the named sections with the named donors only while the share
of our first-in raises re-raised this table, smoothed toward 0.15 with the weight of 10 raises, is at least
`strong_rr`. One value, chosen before any gated run, halfway between night's 14% and the strong fields' 24-26%:
**strong_rr 0.2**. At night's tables the read mostly stays under it; against seats that re-raise our opens (strong
bots, push/fold and loose-aggressive seats, an exploiter) it opens, which is where F's min-raises lose.

## 5. Scope change (coordinator, 05:45): heads-up and three-handed preflop go to S11

A second exploiter found F's short-handed leaks (docs/drills/exploiter2/FINDINGS.md on main); S11
(climb/s11-exploiter2-fixes) fixes blind-vs-blind and heads-up preflop, bet-size tells, check-raises and the big
blind's folds. So the three-handed and heads-up findings above are recorded for S11, not fixed here:
- **pre_3way** (elite): F +0.018 bb a decision against rival2 +0.238, elite2 +0.272, elite1 +0.356; F raises first in
  45% and folds 34% of those raises to a re-raise (rival2 13% / 18%, elite2 23% / 22%, elite1 19% / 17%). Mirror the
  same: F +0.083 vs +0.27 to +0.44, F's raises folded 44%.
- **pre_hu** (elite): F +0.072 vs +0.196 / +0.319 / +0.248; F raises 46%, folds 32% of them (elite2 28% / 16%).
  Mirror: F -0.007 vs +0.23 to +0.32, F's raises folded 46%.
- Routing pre_3way and pre_hu with pre_open_10 to any strong build was worth most of E1/R2/E2's strong-table gain
  (the split was not run after the scope change; G1, the gated version of E1, was stopped unfinished).

This worker's fix is now **pre_open_10 only** (unopened, 4+ alive, 10-20 bb: 4-8-handed short-stack opens), and the
strong route never plays a blind-vs-blind unopened pot (`strong_bvb` off; 372fddc), about 12% of pre_open_10's
decisions on elite. Secondary in-scope leak: pre_open_short (unopened, 4+ alive, under 10 bb), F +0.161 vs +0.20 to
+0.36 (elite), +0.117 vs +0.20 to +0.54 (mirror).

Variants: elite1 plays only on tables the base plays as plain hold'em (it is a raw rival: elsewhere the composite falls
back to the base). One table per catalogued entry with the route open: elite1 decides in swap_holdem, swap_one_turn,
bonus_card, auction, top_heavy, pot_limit, antes_from_level_3 and fast_schedule, and never in the other 17, where the
candidate therefore plays exactly as F. The variants screen runs those eight.

## 6. pre_open_10 alone, gated (screen, confirm + elite, 200 x 8, code 372fddc)

| candidate | night | elite | elite_night | mirror |
|---|---|---|---|---|
| G2: strong_route pre_open_10=elite1x, strong_rr 0.2 (no blind-vs-blind) | -0.017 ± 0.030 | +0.040 ± 0.047 | **+0.048 ± 0.037** | **+0.098 ± 0.062** |

The gate keeps night level (E1's three sections ungated were -0.117) and the change is up beyond noise on two of the
three strong fields. The gain is smaller than E1's because the three-handed and heads-up sections (most of E1's) are
now S11's.
| U2: the same, ungated (strong_rr 0) | -0.056 ± 0.062 | **+0.099 ± 0.080** | +0.053 ± 0.062 | **+0.165 ± 0.094** |

Ungated, pre_open_10 alone gains about twice as much at the all-strong tables but costs on night by its point estimate
(-0.056, an interval twice G2's), which 400 held-out seeds would likely show beyond noise. The gate is what lets the
change hold on night: it is kept.
| G3: G2 plus pre_open_short=elite1x (unopened, 4+ alive, under 10 bb) | -0.028 ± 0.033 | +0.047 ± 0.055 | +0.027 ± 0.040 | **+0.091 ± 0.071** |

Adding the push-or-fold section buys nothing (elite_night loses its gain, night's point estimate drops): not kept.
**G2 is the candidate.**
