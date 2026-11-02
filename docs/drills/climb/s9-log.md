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

## 7. G2's full screen (screen seeds 10000-10199, 200 x 8, code 372fddc)

Spec: `{"dials": {"strong_route": "pre_open_10=elite1x", "strong_rr": 0.2}}` (on top of SHIP_DIALS).

| stage | cell | F | G2 | G2 - F |
|---|---|---|---|---|
| confirm | night | 5.973 | 5.956 | -0.017 ± 0.030 level |
| guards | night_hard | 5.485 | 5.494 | +0.009 ± 0.039 level |
| | realistic | 6.346 | 6.337 | -0.010 ± 0.018 level |
| | top | 5.035 | 5.075 | +0.040 ± 0.045 level |
| | night @10/7/5/4/3/2/1/0 | 6.159 | 6.132 | -0.026 ± 0.055 level |
| | night @50/25/12/6/3/2/1/1 | 24.443 | 24.465 | +0.023 ± 0.299 level |
| | night, doubling blinds | 5.828 | 5.826 | -0.003 ± 0.032 level |
| elite | elite | 4.681 | 4.722 | +0.040 ± 0.047 level |
| | elite_night | 5.329 | 5.376 | **+0.048 ± 0.037 UP** |
| | mirror | 4.416 | 4.514 | **+0.098 ± 0.062 UP** |
| exploit | exploit (8-max, 10/7/5/...) | 4.999 | 5.027 | +0.028 ± 0.099 level (exploiter1 5.37 -> 5.33) |
| | exploit_hu, exploit_3 | | | identical (pre_open_10 needs 4+ alive) |
| variants | swap_holdem / swap_one_turn / bonus_card / auction | | | +0.008 / -0.008 / -0.003 / -0.008, all level |
| | top_heavy | 28.416 | 28.261 | -0.155 ± 0.236 level |
| | **pot_limit** | 6.377 | 6.355 | **-0.022 ± 0.021 DOWN** |
| | antes_from_level_3 / fast_schedule | | | +0.008 / -0.009, level |
| | the other 17 entries | | | identical to F (elite1 never plays there; checked on 2 tables each) |

pot_limit: elite1 was built for no-limit, and its jams are clamped to a pot-sized raise there. Fixed in 4704d4c (the
elite members play no-limit tables only; the composite plays the base on pot- and fixed-limit tables), so the
candidate now plays pot_limit exactly as F (checked on 2 tables; re-screened below).

Timing (latency.py, 20,000 calls, light shadows as shipped, load 10-12, two passes each): F mean 64.7 / 55.9 us, p50
49.3 / 47.7; G2 mean 71.2 / 68.1, p50 56.7 / 56.0; p99s 148-276 for both (load noise). elite1's light scan costs
about 8 us a decision.

### S10: the strong fields under the top-heavy table (50/25/12/6/3/2/1/1, points of 100; screen seeds, 200 x 8)

| field | F | G2 | G2 - F |
|---|---|---|---|
| elite | 13.290 | 13.849 | **+0.559 ± 0.498 UP** |
| mirror | 11.924 | 12.909 | **+0.984 ± 0.560 UP** |

Relative to a seat's average (12.5 of 100 here, 4.5 under 8..1) the gain is four times larger under the top-heavy
table (elite +4.5% vs +0.9%; mirror +7.9% vs +2.2%): the change converts strong tables into first places, which is
what S10 asked. (Diagnostic: climb_accept's elite stage measures 8..1 only; run with the scratch wrapper's
S9_ELITE_PAY=th.)

### Re-screen after the pot-limit fix (code 4704d4c)

night -0.017 ± 0.030 (the same samples as at 372fddc: no-limit play is unchanged); pot_limit +0.000 ± 0.000 (identical
to F). The other cells of section 7 stand: the fix changes play only on pot- and fixed-limit tables.

### Finish positions with G2 (diagnostic seeds 8000-8099, 100 x 8, every seat traced; F's own run on the same seeds)

| field | F pts | G2 pts | F 1st % | G2 1st % | reach 3-handed | chips at 3-handed |
|---|---|---|---|---|---|---|
| elite | 4.644 | 4.732 | 11.8 | 12.4 | 36.9% -> 39.9% | 31.2% -> 32.4% |
| mirror | 4.485 | 4.532 | 7.9 | 8.4 | 35.2% -> 37.1% | 29.3% -> 30.4% |

On these seeds G2 ranks 2nd of six names on the mirror (rival 2 4.897, G2 4.532, hybrid3_x 4.473, elite2 4.451,
f_copy 4.418, elite1 4.393) where F ranked last on the 200 diagnostic seeds. The gain is chips kept before the
endgame: F reaches three-handed more often and with more chips. Converting those chips into first places is the
three-handed and heads-up play that S11 now owns (section 5).

## 8. Recommendation

Candidate spec (on top of SHIP_DIALS; code 4704d4c or later):

    {"dials": {"strong_route": "pre_open_10=elite1x", "strong_rr": 0.2}}

Unopened pots at 10-20 bb with four or more players alive (not blind against blind) are played by the elite1 build,
with the exploit layer on, while this table re-raises our first-in raises at least 20% of the time (smoothed from a
15% prior worth 10 raises); everything else is F. At night's tables the read mostly stays shut and F keeps its steals.

Screen evidence (10000-10199): night -0.017 ± 0.030; every guard level; elite +0.040 ± 0.047, elite_night +0.048 ±
0.037 UP, mirror +0.098 ± 0.062 UP; under 50/25/12/6/3/2/1/1 elite +0.56 ± 0.50 UP, mirror +0.98 ± 0.56 UP; exploit
level (8-max +0.028 ± 0.099; heads-up and 3-handed identical); variants: the eight entries where elite1 can play all
level after the pot-limit fix, the other 17 identical to F. Timing: about +8 us a decision (elite1's light scan).

For the coordinator's held-out confirmation (addendum 8): stages confirm, guards, elite (incl. mirror), variants.
Notes:
- Compatible with FIN (batch 3): FIN's 3-bet defence acts after our open is 3-bet, in sections this route does not
  touch; the route only replaces the open decision at 10-20 bb.
- The mirror's copies are F as it ships; once G2 ships, the copies play G2 (f_copy follows SHIP_DIALS).
- Not tried for lack of time: a per-seat version of the gate (route only when the seats behind have re-raised us); a
  mirror whose copies follow the candidate; elite2's or rival 2's code for pre_open_10 (rival 2 needs a light shadow
  first: its postflop Monte Carlo as a shadow would cost about 260 us a decision).

Full suite at 4704d4c (load 15-18): 993 passed, 8 skipped, 21 failed, all wall-clock or timing tests; re-run alone,
20 pass and one skips on its own oversubscribed-host guard.

## 9. After H4 (coordinator, 2026-11-02 ~10:00): twist tables and the timing tail

H4 (23000-23399, against batch 3's ship): mirror +0.078 ± 0.039 UP; elite, elite_night, night, guards, exploit, aware
level; **three variants down**: auction -0.016 ± 0.014, bounty -0.027 ± 0.018, knockout_bounty -0.030 ± 0.029. And the
sim's p99 column was several times F's (e.g. night_hard 643 vs 4110 us at load ~17). Rebased onto main 5b4591a (batch
4 ships: r3.v3_defend and V-c's dials; S12's hero.holdem_table).

**Twist tables (361a1de).** elite1 is twist-blind, and batch 3 lets the base play bounty tables (base.hero_on_bounty
false), so the route reached them. The elite members now play only tables that are hold'em by Hero's test
(hero.holdem_table, S12's: only payouts, blinds, antes or a straddle may differ; any twist key turns it off); the
composite plays the base in their sections everywhere else. With the route open (strong_rr 0) the candidate now plays
every catalogued twist exactly as F (2 screen tables each, and a test with one table each); before the fix, swap_holdem,
auction, knockout_bounty and river_of_blood differed on the same tables. The route still plays the hold'em-structure
entries top_heavy, antes_from_level_3 and fast_schedule (straddle falls back: the base's own straddle rule).

**The timing tail (aec41bd).** The shipped bot builds the composite with light shadows; climb_accept's seats do not, so
in every screen elite1 decided in full on each of our decisions as a shadow and the answer was thrown away. That was
the tail. Its light shadow plays exactly as the full one (test), so it is now used everywhere (ALWAYS_LIGHT).

Per decision, model mode as climb_accept builds the seat, night_hard seeds 8600-8602 x 8, interleaved twice, load 12
(one stray run used seeds 23400-23401, outside every held-out set, for timing only):

| | mean us | p50 | p99 |
|---|---|---|---|
| F | 107 / 126 | 78 / 79 | 597 / 754 |
| candidate, elite1 full shadow (before) | 155 / 154 | 113 / 114 | 806 / 709 |
| candidate, light shadow (after) | 136 / 119 | 88 / 88 | 730 / 663 |

The shipped form, tools/latency.py --hand-end --tables 20 --reps 3 (per-call minimum), load 12-13:

| field | bot | act p99 / max | first act mean / max | hand_end p99 / max |
|---|---|---|---|---|
| night | F | 88.5 / 118.2 | 87.8 / 101.3 | 93.4 / 121.7 |
| night | candidate (gate 0.2) | 102.2 / 150.8 | 107.6 / 139.0 | 99.2 / 132.6 |
| realistic | F | 92.7 / 218.6 | 93.9 / 107.3 | 96.3 / 142.6 |
| realistic | candidate (gate 0.2) | 101.1 / 159.7 | 107.7 / 132.9 | 99.3 / 142.6 |
| night | candidate, gate always open | 111.2 / 158.5 | 117.8 / 139.0 | 104.4 / 215.4 |
| mirror | F | 106.3 / 183.8 | 107.6 / 139.8 | 100.5 / 166.9 |
| mirror | candidate, gate always open | 117.5 / 186.3 | 114.8 / 137.3 | 105.7 / 586.0 |

Slowest calls (mirror, gate open, per-call minimum of 3): act max 168 us, of which elite1 84 us (a pre_open_10 decision it
plays); elite1's part of a decision p50 5.8 us, p99 41.5, max 83.5; of a hand end p99 3.1, max 43.7. The 586 us hand
end did not repeat (max 177 on the next pass, elite1 6.6 of it). Nothing near 1 ms; the candidate costs about 10 us
a decision over F (elite1's history scan, and its decision when it plays).

### The fixed candidate's screen (code aec41bd, version b2e72aab1d; against batch 4's ship; --aim strong; 200 x 8)

| stage | cell | F | candidate | candidate - F |
|---|---|---|---|---|
| confirm | night | 5.968 | 5.949 | -0.019 ± 0.030 level |
| guards | night_hard / realistic / top | | | +0.010 ± 0.039 / -0.010 ± 0.018 / +0.040 ± 0.045, level |
| | night @10/7/5... / @50/25/12... / doubling blinds | | | -0.027 ± 0.055 / +0.023 ± 0.299 / +0.001 ± 0.032, level |
| elite | elite | 4.681 | 4.722 | +0.040 ± 0.047 level |
| | elite_night | 5.328 | 5.379 | **+0.050 ± 0.037 UP** |
| | mirror | 4.414 | 4.512 | **+0.098 ± 0.062 UP** |
| exploit | 8-max / heads-up / 3-handed | | | +0.026 ± 0.086 / identical / identical |
| variants | top_heavy / antes_from_level_3 / fast_schedule | | | -0.134 ± 0.240 / +0.010 ± 0.018 / -0.007 ± 0.029, level |
| | straddle, bounty, knockout_bounty, auction | | | +0.000 ± 0.000 (identical to F) |

climb_accept's verdict on confirm, guards and elite with --aim strong: ACCEPT (elite_night and mirror up, night not down,
nothing down). The variants run took the four entries elite1 can still play and the three H4 rejected on, plus straddle;
the other 18 twist entries play exactly as F by construction (the route falls back on every non-hold'em table) and by
test (one table each) and check (two screen tables each), so they were not re-run at 200 seeds. The p99 column is
now level between F and the candidate (e.g. elite 4141/4156, mirror 4097/4119, night 8693/8199 us at load ~15: every
column is the worst chunk's p99 on a loaded host).

Full suite at aec41bd (load 7-10): 1113 passed, 7 skipped, 15 failed; re-run alone 13 pass. The two left,
tests/test_nightof_latency.py's cheap-bot round trips through kits b/c and d, fail the same way on main 5b4591a (four
runs, two each, at load 5-8): one gen-2 collection inside 100 adapter calls is their p99 (4.7 ms). Not from this
branch.

### Recommendation (unchanged spec, fixed code)

    {"dials": {"strong_route": "pre_open_10=elite1x", "strong_rr": 0.2}}    at aec41bd (or later)

With aec41bd's code the route can no longer reach a twist table, and elite1 costs what the ship pays (light shadow).
