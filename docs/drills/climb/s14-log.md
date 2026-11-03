# S14: where the strong bots beat F, and playing their way there

Branch climb/s14-strong-sections, from main 3896840 (batch 5 is F). Screens only: seeds 10000-10199 (`--set screen`).
Diagnostics ran on fresh seeds 8200-8349, which no earlier log lists. No held-out set, judge set, judge bot, judge
field or held-out variant was run, read or tuned on. elite3 and elite5 are not members and were never run. Every screen
used tools/climb_accept.py's own cells and cache, with F's chunks keyed to main's code version cfbcd1af69 (scratch
`goal/s14/accept.py`), because F plays identically on this branch (section 6). Workers: 2-3 at nice 5, host load 5-18.
The branch predates exploiter 3 (main 2a17295), so the exploit stage has no exploit3 cells.

## 1. Findings

- **F's weakest sections at strong tables are four preflop ones, the same in all four fields** (elite, elite_b,
  mirror, mirror_b):
  - re-shove or fold, facing a raise under 20 bb (`pre_raised_short`);
  - facing a raise at 20+ bb (`pre_raised_deep`);
  - three-handed preflop (`pre_3way`);
  - heads-up preflop (`pre_hu`).

  Per table seat (8 rotations), F trails rival 2 there by 16, 19, 15 and 10 bb. After the flop F is the best bot at
  these tables: facing a bet it is 22 bb a seat ahead of rival 2.
- **How the strong bots play those spots differently:**
  - *Re-shoves.* Rival 2 re-shoves 22% of the raises it faces under 20 bb. F (Hero plays this section) re-shoves 13%
    and flat-calls 6%. Rival 2 makes +0.48 to +0.50 bb a decision there; F and every elite build make +0.15 to +0.28.
  - *Three-handed and heads-up.* F min-raises 38-39% of the time and folds 40-42% of those raises to a re-raise. This
    is the leak S9 found in pre_open_10. elite1 raises 18-32%, shoves 27-30%, and folds 18-22% of its raises.
  - *Deep, facing a raise.* Rival 2 folds more, flat-calls less, and 4-bets all-in more. It is the only bot ahead of
    F there.
  - *Why rival 2 tops every field.* It reaches three-handed more often (43-46% of its tables, against F's 37-41%); it
    does not win more from there. The elite builds are the ones that win from three-handed (46-57% first given
    three-handed, against F's 22-31%).
- **Adopting the strong bots' play wins at strong tables, but exploiter 1 punishes every version that touches
  short-handed preflop.** On 20 diagnostic tables against exploiter 1, which 3-bets every open, each donor's
  short-handed preflop (elite1, elite2, elite4, rival 2's core) loses 1.3 to 1.7 points heads-up and 0.8 to 1.6
  three-handed. F's own short-handed play was hardened
  against that exploiter (batch 4, S11). Results, all screens at 200 x 8:
  - *K11* (rival 2's core at re-shove spots; elite1 three-handed and heads-up; on batch 5's gate): **all five strong
    fields beyond noise up** (elite +0.109, elite_night +0.054, mirror +0.122, elite_b +0.102, mirror_b +0.148), night
    level. But it is down against exploiter 1 heads-up (-0.713) and three-handed (-0.867), and on fast_schedule
    (-0.053).
  - *K18* (elite1 three-handed and heads-up on a second gated route, `strong2_route`, with F's own 3-bet defence kept
    once our raise is re-raised): elite, mirror, elite_b and mirror_b beyond noise up (+0.036 to +0.044); night_hard
    and top up; night level (+0.014). Every guard, variant and exploit cell passes except **exploit_3** (exploiter 1,
    three-handed from the start): **-0.238 ± 0.159, DOWN**. Keeping the defence fixed heads-up (-0.713 → +0.045).
  - *K19* (K18 with heads-up only) clears exploiter 1 but gains only +0.01, and its fast_schedule cell is down by
    -0.003 ± 0.003.
- **By the task's rule (a strong field up, nothing down), no candidate here is ready to keep.** The closest is K18:
  everything passes except the three-handed exploiter-1 cell. Two things remain:
  - a way to keep elite1's three-handed play at strong tables without handing it to an exploiter. The table-level
    re-raise read cannot tell exploiter 1 from strong bots three-handed, because the third seat dilutes the read;
  - for K11's re-shove part, the fast_schedule cost: rival 2's re-shoves lose where faster blinds open the gate at
    ordinary tables.
- **Not adopted:**
  - rival 2's deep play (`pre_raised_deep`): it gains on mirror_b but costs on elite and night (K1, K3);
  - elite1's push-or-fold opens under 10 bb: they give back the endgame gain (K12, as S9's G3 found);
  - elite2 as the endgame donor: it gains less than elite1 (K7);
  - also routing the blind-vs-blind heads-up and three-handed pots: nothing measurable (K13, K14);
  - elite1's deeper opens (20+ bb): they add only on mirror_b, against copies of F (K15 over K11: +0.076 ± 0.069 there,
    level elsewhere).
- **elite4** is not the best bot in any section at these tables. It is close to F preflop and weaker after the flop.
  It is registered as a member (`elite4`, `elite4x`) but not routed.
- **Rival 2's core needed a light shadow.** Its postflop Monte Carlo costs about 260 us a decision as built. The new
  member `r2s` is rival 2's core behind the same shell, with four changes:
  - its generator is seeded per decision;
  - its light shadow runs the history read and stops at the Monte Carlo;
  - its own-action flags follow the action taken whenever it is not chosen;
  - its ICM curve is built at the first decision that reads it.

  Light and full shadows play every decision the same (test: 3 fields x 3 tables x 8 rotations), and so do elite2's
  and elite4's new light shadows. Lazy and eager curves also play the same.
- **A routing bug fixed on the way.** A strong-route donor that cannot play a table (a twist, permuted ranks) fell back
  to the base, even in Hero's sections. So a route into pre_raised_short changed play on permuted_ranks. It now falls
  back to the section's own donor. F's own strong route has only a base section, so F was not affected.

### What is on the branch (all off by default; F builds none of it)

- Members `r2s` (donors `r2s`, `r2sx`) and `elite4` (`elite4`, `elite4x`); light shadows for elite2, elite4 and r2s
  (ALWAYS_LIGHT); `RESYNC_ALWAYS` for r2s.
- `strong_bvb` may name sections (`"pre_hu"`).
- `strong2_route`, `strong2_rr`, `strong2_rr_max`: a second route on the same read with its own band.
  `strong2_keep_defence`: once our own preflop raise has been re-raised, the decision stays with the section's own
  donor.
- The fallback fix above.


## 2. The section profile (diagnostic seeds 8200-8349, 150 x 8, every seat traced, F = batch 5)

Tool: S9's `s9_diag.py` (scratch `goal/s14/`): every seat wrapped in tools/skill_profile.py's Tracer; chips won per
decision in big blinds, by section, from the same tables. F is the `ship` seat (in the mirrors, its three copies agree
to within noise).

Points (diagnostic seeds): elite rival2 4.905, F 4.828, elite2 4.596; elite_b rival2 4.860, F 4.823, elite1 4.462,
elite4 4.325; mirror rival2 4.654, F 4.552, f_copy 4.518; mirror_b rival2 4.805, F 4.581, elite2 4.373, elite4 4.312.

bb per decision, F / rival2 / elite1 / elite2 / elite4 (elite4 sits only in elite_b and mirror_b):

| section | elite: F / r2 / e1 / e2 / e4 | elite_b: F / r2 / e1 / e2 / e4 | mirror: F / r2 / e1 / e2 / e4 | mirror_b: F / r2 / e1 / e2 / e4 |
|---|---|---|---|---|
| pre_open_40 | +0.03 / +0.03 / +0.06 / +0.01 / - | +0.01 / +0.02 / +0.05 / -0.02 / -0.02 | -0.03 / -0.01 / +0.03 / -0.05 / - | -0.03 / -0.01 / +0.03 / -0.06 / -0.07 |
| pre_open_20 | +0.07 / +0.04 / +0.08 / +0.08 / - | +0.04 / +0.02 / +0.07 / +0.04 / +0.01 | +0.01 / +0.01 / +0.08 / +0.01 / - | +0.01 / -0.00 / +0.06 / +0.01 / -0.03 |
| pre_open_10 | +0.01 / +0.08 / +0.14 / +0.12 / - | +0.05 / +0.07 / +0.17 / +0.09 / +0.03 | +0.06 / +0.08 / +0.22 / +0.17 / - | +0.09 / +0.07 / +0.24 / +0.18 / +0.04 |
| pre_open_short | +0.11 / +0.21 / +0.31 / +0.20 / - | +0.13 / +0.16 / +0.27 / +0.28 / +0.14 | +0.12 / +0.17 / +0.43 / +0.34 / - | +0.14 / +0.16 / +0.40 / +0.33 / +0.15 |
| pre_raised_deep | +0.00 / +0.07 / -0.07 / -0.04 / - | +0.03 / +0.08 / -0.04 / -0.07 / -0.02 | +0.02 / +0.08 / -0.01 / -0.04 / - | +0.02 / +0.08 / -0.01 / -0.06 / +0.03 |
| pre_raised_short | +0.28 / +0.48 / +0.23 / +0.21 / - | +0.25 / +0.50 / +0.21 / +0.20 / +0.15 | +0.26 / +0.49 / +0.19 / +0.23 / - | +0.23 / +0.50 / +0.18 / +0.20 / +0.18 |
| pre_allin | +0.18 / +0.28 / +0.28 / +0.39 / - | +0.26 / +0.25 / +0.26 / +0.18 / +0.31 | +0.19 / +0.19 / +0.20 / +0.18 / - | +0.18 / +0.22 / +0.16 / +0.17 / +0.24 |
| pre_3way | -0.01 / +0.26 / +0.33 / +0.23 / - | -0.01 / +0.25 / +0.34 / +0.24 / +0.16 | -0.01 / +0.25 / +0.42 / +0.31 / - | +0.04 / +0.31 / +0.40 / +0.25 / +0.22 |
| pre_hu | +0.11 / +0.20 / +0.27 / +0.19 / - | +0.06 / +0.20 / +0.32 / +0.25 / +0.13 | +0.02 / +0.26 / +0.22 / +0.31 / - | -0.02 / +0.22 / +0.26 / +0.25 / +0.15 |
| post_hu_bet | +0.25 / -0.07 / -0.25 / +0.10 / - | +0.34 / +0.05 / -0.10 / +0.10 / -0.03 | +0.20 / -0.26 / -0.19 / -0.04 / - | +0.20 / -0.02 / -0.36 / -0.01 / +0.12 |
| post_hu_chk | +0.78 / +0.82 / +0.77 / +0.64 / - | +0.86 / +0.96 / +0.92 / +0.71 / +0.46 | +0.73 / +0.79 / +0.81 / +0.62 / - | +0.77 / +0.87 / +0.78 / +0.70 / +0.59 |
| post_mw | +0.51 / +0.31 / +0.38 / +0.32 / - | +0.46 / +0.32 / +0.29 / +0.36 / +0.09 | +0.36 / +0.36 / +0.34 / +0.32 / - | +0.46 / +0.21 / +0.35 / +0.35 / +0.08 |

Where the gap is, in chips per table seat (8 rotations), mean of the four fields:

| section | share of F's decisions | F - rival2, bb per table seat (8 rotations), mean over 4 fields | F - best elite |
|---|---|---|---|
| pre_open_40 | 18.3% | -3.1 | -10.3 |
| pre_open_20 | 7.9% | +1.4 | -4.3 |
| pre_open_10 | 6.5% | -1.2 | -10.4 |
| pre_open_short | 3.0% | -0.1 | -5.5 |
| pre_raised_deep | 25.4% | -18.9 | +9.3 |
| pre_raised_short | 6.6% | -16.3 | +4.1 |
| pre_allin | 7.7% | -0.1 | +0.0 |
| pre_3way | 3.5% | -15.0 | -15.6 |
| pre_hu | 3.4% | -9.7 | -10.8 |
| post_hu_bet | 5.4% | +22.1 | +12.9 |
| post_hu_chk | 9.6% | +10.1 | -1.3 |
| post_mw | 2.7% | +5.2 | -7.7 |

Reach and conversion (diagnostic seeds):

| field | bot | reach 3-handed | chips at 3 | 1st given 3 | reach HU | win HU |
|---|---|---|---|---|---|---|
| elite | rival2 | 45.6% | 32.3% | 31.8% | 30.8% | 45.7% |
| elite | F | 41.0% | 32.4% | 31.1% | 24.5% | 52.0% |
| elite | elite2 | 37.4% | 38.2% | 46.5% | 26.4% | 64.4% |
| elite | elite1 | 37.8% | 35.9% | 48.8% | 26.8% | 67.1% |
| elite_b | rival2 | 45.6% | 31.1% | 31.1% | 29.5% | 46.9% |
| elite_b | F | 40.5% | 32.5% | 29.8% | 23.9% | 50.5% |
| elite_b | elite1 | 37.8% | 40.5% | 54.4% | 29.0% | 70.7% |
| elite_b | elite2 | 34.1% | 37.5% | 46.0% | 23.3% | 64.6% |
| elite_b | elite4 | 30.8% | 31.5% | 28.2% | 19.4% | 43.8% |
| mirror | rival2 | 43.3% | 29.8% | 27.9% | 28.2% | 41.4% |
| mirror | F | 36.6% | 31.5% | 22.3% | 20.9% | 38.2% |
| mirror | elite2 | 36.2% | 38.9% | 49.4% | 26.2% | 67.5% |
| mirror | elite1 | 35.3% | 40.9% | 56.6% | 28.2% | 67.6% |
| mirror_b | rival2 | 44.1% | 31.2% | 28.2% | 31.1% | 38.9% |
| mirror_b | F | 37.9% | 32.7% | 27.7% | 23.2% | 43.9% |
| mirror_b | elite2 | 35.6% | 38.0% | 45.2% | 24.6% | 65.1% |
| mirror_b | elite4 | 31.8% | 29.0% | 29.9% | 20.4% | 45.7% |
| mirror_b | elite1 | 33.9% | 41.7% | 56.0% | 26.4% | 69.1% |

## 3. How they play there (spot book, seeds 8200-8259, 60 x 8 per field, four fields pooled)

Tool `goal/s14/s14_spots.py`: every decision's action by section; raise size as chips added over the pot; the hand's
net booked to the hand's first decision in the section; "raises then folded" is the share of our non-all-in preflop
raises whose next decision this hand was a fold.

| section | bot | fold | call | raise (size / pot) | all-in | raises then folded | first decision's hand net, bb |
|---|---|---|---|---|---|---|---|
| pre_raised_short | F | 81% | 6% | 1% (1.79) | 13% | 1% | -0.09 |
|  | rival2 | 75% | 2% | 0% | 22% | - | +0.15 |
|  | elite1 | 78% | 11% | 0% | 11% | - | -0.11 |
|  | elite2 | 89% | 1% | 0% | 9% | - | -0.20 |
|  | elite4 | 80% | 6% | 1% (1.95) | 14% | 2% | -0.16 |
| pre_raised_deep | F | 79% | 15% | 5% (1.92) | 0% | 9% | -0.15 |
|  | rival2 | 81% | 13% | 4% (1.88) | 2% | 7% | -0.12 |
|  | elite1 | 77% | 17% | 4% (1.81) | 1% | 8% | -0.24 |
|  | elite2 | 71% | 23% | 5% (1.76) | 1% | 8% | -0.21 |
|  | elite4 | 78% | 14% | 8% (1.88) | 1% | 14% | -0.30 |
| pre_3way | F | 38% | 6% | 39% (1.51) | 17% | 42% | -0.00 |
|  | rival2 | 63% | 6% | 13% (1.59) | 17% | 28% | +0.06 |
|  | elite1 | 46% | 8% | 18% (1.57) | 27% | 18% | +0.30 |
|  | elite2 | 47% | 9% | 21% (1.43) | 23% | 23% | +0.20 |
|  | elite4 | 60% | 6% | 18% (1.59) | 15% | 28% | +0.01 |
| pre_hu | F | 37% | 11% | 38% (1.15) | 13% | 40% | -0.15 |
|  | rival2 | 50% | 11% | 20% (1.38) | 19% | 23% | -0.10 |
|  | elite1 | 30% | 8% | 32% (1.34) | 30% | 22% | +0.08 |
|  | elite2 | 35% | 16% | 25% (1.21) | 23% | 23% | +0.17 |
|  | elite4 | 45% | 12% | 26% (1.71) | 16% | 27% | -0.17 |
| pre_open_short | F | 78% | 0% | 3% (1.23) | 18% | 52% | +0.14 |
|  | rival2 | 80% | 1% | 0% | 19% | - | +0.14 |
|  | elite1 | 44% | 1% | 0% | 55% | - | +0.40 |
|  | elite2 | 63% | 0% | 0% | 37% | - | +0.30 |
|  | elite4 | 88% | 0% | 0% | 12% | - | +0.10 |


## 4. Screens (screen seeds 10000-10199, 200 x 8; F = batch 5)

Every candidate is on top of SHIP_DIALS, so it keeps batch 5's `pre_open_10=elite1x` and gate: `strong_rr` 0.2, with
a prior of 0.15 at a weight of 10 raises. Blind-vs-blind unopened pots are excluded unless named. F's screen means:
night 5.972, elite 4.865, elite_night 5.422, mirror 4.498, elite_b 4.638, mirror_b 4.466.

| cand | strong route added (all `...x`: the exploit layer on) |
|---|---|
| K1 | pre_raised_deep, pre_raised_short = r2s |
| K2 | pre_3way, pre_hu = elite1 |
| K3 | K1 + K2 |
| K4 | pre_raised_short = r2s |
| K7 | pre_3way, pre_hu = elite2 |
| K11 | K2 + pre_raised_short = r2s |
| K12 | K2 + pre_open_short = elite1 |
| K13 / K14 | K11 + `strong_bvb` "pre_hu" / "pre_hu,pre_3way" |
| K15 | K11 + pre_open_20, pre_open_40 = elite1 |
| K17 | `strong2_route` pre_3way, pre_hu = elite1, band [0.2, 0.6) |
| K18 | K17 + `strong2_keep_defence` |
| K19 | K18 with pre_hu only |

Confirm and elite stages (paired difference with F, 95% interval):

| cand | night | elite | elite_night | mirror | elite_b | mirror_b |
|---|---|---|---|---|---|---|
| K1 | -0.040 ± 0.064 | +0.002 ± 0.084 | -0.043 ± 0.065 | +0.030 ± 0.093 | +0.048 ± 0.083 | +0.174 ± 0.082 **UP** |
| K2 | +0.018 ± 0.014 **UP** | +0.043 ± 0.025 **UP** | +0.018 ± 0.021 | +0.041 ± 0.021 **UP** | +0.042 ± 0.024 **UP** | +0.035 ± 0.022 **UP** |
| K3 | -0.049 ± 0.063 | +0.035 ± 0.085 | -0.027 ± 0.065 | +0.085 ± 0.099 | +0.087 ± 0.085 **UP** | +0.221 ± 0.085 **UP** |
| K4 | +0.013 ± 0.035 | +0.059 ± 0.070 | -0.003 ± 0.056 | +0.060 ± 0.101 | +0.070 ± 0.096 | +0.177 ± 0.075 **UP** |
| K7 | +0.013 ± 0.015 | +0.013 ± 0.021 | +0.019 ± 0.019 **UP** | +0.042 ± 0.019 **UP** | +0.023 ± 0.021 **UP** | +0.031 ± 0.020 **UP** |
| K11 | +0.020 ± 0.035 | +0.109 ± 0.058 **UP** | +0.054 ± 0.041 **UP** | +0.122 ± 0.066 **UP** | +0.102 ± 0.068 **UP** | +0.148 ± 0.070 **UP** |
| K12 | +0.005 ± 0.021 | +0.044 ± 0.048 | +0.013 ± 0.026 | +0.048 ± 0.056 | +0.015 ± 0.043 | +0.008 ± 0.050 |
| K13 | +0.021 ± 0.035 | +0.104 ± 0.058 **UP** | +0.054 ± 0.041 **UP** | +0.123 ± 0.067 **UP** | +0.102 ± 0.068 **UP** | +0.150 ± 0.070 **UP** |
| K14 | +0.021 ± 0.037 | +0.106 ± 0.057 **UP** | +0.059 ± 0.040 **UP** | +0.126 ± 0.067 **UP** | +0.094 ± 0.067 **UP** | +0.151 ± 0.068 **UP** |
| K15 | +0.024 ± 0.054 | +0.116 ± 0.069 **UP** | +0.090 ± 0.057 **UP** | +0.153 ± 0.076 **UP** | +0.061 ± 0.077 | +0.223 ± 0.074 **UP** |
| K17 | +0.018 ± 0.014 **UP** | +0.043 ± 0.025 **UP** | +0.018 ± 0.021 | +0.041 ± 0.021 **UP** | +0.042 ± 0.024 **UP** | +0.035 ± 0.022 **UP** |
| K18 | +0.014 ± 0.014 | +0.040 ± 0.023 **UP** | +0.018 ± 0.022 | +0.044 ± 0.022 **UP** | +0.042 ± 0.022 **UP** | +0.036 ± 0.021 **UP** |
| K19 | -0.000 ± 0.003 | +0.010 ± 0.009 **UP** | +0.001 ± 0.006 | +0.009 ± 0.008 **UP** | +0.008 ± 0.007 **UP** | +0.006 ± 0.007 |

Code: K1, K2, K3, K7, K11 and K12 ran at 0214c19; K13, K14 and K15 at f680f9a, as did K4's and K11's full screens;
K17 at 4e3a4e0; K18 and K19 at 8e3971e. The later commits change no play at plain hold'em tables for the earlier
specs: K11's confirm and elite cells are identical at 0214c19 and f680f9a.

Notes:
- K17 plays exactly as K2 on every cell. The band's top (0.6) never closes the route at these tables, nor against
  exploiter 1, whose read sits at 0.3-0.55 heads-up. A top at 0.4 halves the heads-up loss on 20 diagnostic tables
  (9.475 → 9.025, F 9.475) and leaves the three-handed one (8.783 → 7.567).
- climb_accept's verdict with `--aim strong` checks guards, elite and variants for cells down, but not the exploit
  stage. K17 printed ACCEPT with exploit_hu and exploit_3 down. The verdicts here apply the task's rule (nothing down
  anywhere) by hand.
- Paired between candidates: K11 - K2 is elite +0.066 ± 0.057 UP, mirror +0.080 ± 0.064 UP, mirror_b +0.113 ± 0.067
  UP, the rest level. K15 - K11 is mirror_b +0.076 ± 0.069 UP, the rest level (elite_b -0.041 ± 0.066).

### Full screens

**K11** `{"strong_route": "pre_open_10=elite1x,pre_3way=elite1x,pre_hu=elite1x,pre_raised_short=r2sx"}` (code
b7c99f1592):

| stage | cell | F | cand | cand - F |
|---|---|---|---|---|
| confirm | night | 5.972 | 5.992 | +0.020 ± 0.035 level |
| guards | night_hard | 5.499 | 5.524 | +0.026 ± 0.038 level |
|  | realistic | 6.370 | 6.363 | -0.007 ± 0.023 level |
|  | top | 5.058 | 5.127 | +0.069 ± 0.059 **UP** |
|  | night @10/7/5/4/3/2/1/0 | 6.199 | 6.212 | +0.012 ± 0.062 level |
|  | night @50/25/12/6/3/2/1/1 | 24.699 | 24.736 | +0.036 ± 0.404 level |
|  | night +double | 5.848 | 5.820 | -0.028 ± 0.036 level |
| elite | elite | 4.865 | 4.974 | +0.109 ± 0.058 **UP** |
|  | elite_night | 5.422 | 5.476 | +0.054 ± 0.041 **UP** |
|  | mirror | 4.498 | 4.619 | +0.122 ± 0.066 **UP** |
|  | elite_b | 4.638 | 4.740 | +0.102 ± 0.068 **UP** |
|  | mirror_b | 4.466 | 4.614 | +0.148 ± 0.070 **UP** |
| exploit | exploit @10/7/5/4/3/2/1/0 | 5.839 | 5.786 | -0.053 ± 0.113 level (exploiter 4.608 -> 4.676) |
|  | exploit_hu +hu | 9.227 | 8.515 | -0.713 ± 0.164 **DOWN** (exploiter 7.772 -> 8.485) |
|  | exploit_3 +three | 8.458 | 7.592 | -0.867 ± 0.206 **DOWN** (exploiter 6.900 -> 7.770) |
|  | exploit2 @10/7/5/4/3/2/1/0 | 5.844 | 5.872 | +0.028 ± 0.055 level (exploiter 5.086 -> 5.040) |
|  | exploit2_hu +hu | 7.848 | 7.885 | +0.037 ± 0.103 level (exploiter 9.152 -> 9.115) |
|  | exploit2_3 +three | 7.378 | 7.357 | -0.022 ± 0.119 level (exploiter 8.165 -> 8.227) |
| variants | top_heavy (realistic) | 28.654 | 28.631 | -0.023 ± 0.298 level |
|  | antes_from_level_3 (realistic) | 6.496 | 6.482 | -0.015 ± 0.026 level |
|  | fast_schedule (realistic) | 6.122 | 6.069 | -0.053 ± 0.037 **DOWN** |
|  | straddle (realistic) | 6.412 | 6.412 | +0.000 ± 0.000 level |

**K4** `{"strong_route": "pre_open_10=elite1x,pre_raised_short=r2sx"}` (code b7c99f1592). Elite stage: elite +0.059 ±
0.070, elite_night -0.003 ± 0.056, mirror +0.060 ± 0.101, elite_b +0.070 ± 0.096, mirror_b +0.177 ± 0.075 UP.
Heads-up and three-handed exploit cells identical (the section needs 4+ alive). Guards level, but night under
50/25/12/... is -0.255 ± 0.328 and under 10/7/5/... -0.046 ± 0.052. **fast_schedule -0.047 ± 0.037 DOWN.**

**K18** `{"strong2_route": "pre_3way=elite1x,pre_hu=elite1x", "strong2_rr": 0.2, "strong2_rr_max": 0.6,
"strong2_keep_defence": true}` (code 43d093622c):

| stage | cell | F | cand | cand - F |
|---|---|---|---|---|
| confirm | night | 5.972 | 5.986 | +0.014 ± 0.014 level |
| guards | night_hard | 5.499 | 5.520 | +0.021 ± 0.016 **UP** |
|  | realistic | 6.370 | 6.371 | +0.001 ± 0.007 level |
|  | top | 5.058 | 5.079 | +0.021 ± 0.016 **UP** |
|  | night @10/7/5/4/3/2/1/0 | 6.199 | 6.219 | +0.019 ± 0.033 level |
|  | night @50/25/12/6/3/2/1/1 | 24.699 | 24.765 | +0.066 ± 0.242 level |
|  | night +double | 5.848 | 5.848 | +0.001 ± 0.013 level |
| elite | elite | 4.865 | 4.905 | +0.040 ± 0.023 **UP** |
|  | elite_night | 5.422 | 5.439 | +0.018 ± 0.022 level |
|  | mirror | 4.498 | 4.542 | +0.044 ± 0.022 **UP** |
|  | elite_b | 4.638 | 4.680 | +0.042 ± 0.022 **UP** |
|  | mirror_b | 4.466 | 4.502 | +0.036 ± 0.021 **UP** |
| exploit | exploit @10/7/5/4/3/2/1/0 | 5.839 | 5.810 | -0.029 ± 0.056 level (exploiter 4.608 -> 4.610) |
|  | exploit_hu +hu | 9.227 | 9.273 | +0.045 ± 0.120 level (exploiter 7.772 -> 7.728) |
|  | exploit_3 +three | 8.458 | 8.220 | -0.238 ± 0.159 **DOWN** (exploiter 6.900 -> 7.098) |
|  | exploit2 @10/7/5/4/3/2/1/0 | 5.844 | 5.849 | +0.005 ± 0.037 level (exploiter 5.086 -> 5.063) |
|  | exploit2_hu +hu | 7.848 | 7.825 | -0.022 ± 0.087 level (exploiter 9.152 -> 9.175) |
|  | exploit2_3 +three | 7.378 | 7.370 | -0.008 ± 0.077 level (exploiter 8.165 -> 8.172) |
| variants | top_heavy (realistic) | 28.654 | 28.673 | +0.019 ± 0.101 level |
|  | antes_from_level_3 (realistic) | 6.496 | 6.489 | -0.007 ± 0.008 level |
|  | fast_schedule (realistic) | 6.122 | 6.116 | -0.006 ± 0.010 level |
|  | straddle (realistic) | 6.412 | 6.412 | +0.000 ± 0.000 level |

**K19** (K18 with `strong2_route` "pre_hu=elite1x"): elite +0.010 ± 0.009 UP, mirror +0.009 ± 0.008 UP, elite_b +0.008
± 0.007 UP. Every exploit cell level or up (exploit +0.025 UP, exploit2 +0.019 UP, exploit_hu +0.045, exploit_3
+0.015). **fast_schedule -0.003 ± 0.003 DOWN**; the rest level.

**Splitting K18's three-handed loss** (exploit_3 field, diagnostic seeds 8200-8219 x 8, F 8.783): pre_hu alone 8.733;
pre_3way alone 8.350; pre_3way first-in decisions only (a trial dial, not kept) 8.483. Three-handed, exploiter 1 beats
elite1's opens as well as its answers.

## 5. Latency (tools/latency.py --hand-end --tables 20 --reps 3, per-call minimum; load 10-14)

| table | bot | act mean / p99 / max | hand_end mean / p99 / max |
|---|---|---|---|
| plain hold'em (realistic) | F | 53.9 / 102.3 / 140.4 | 61.1 / 135.5 / 181.9 |
| plain hold'em (realistic) | K18 (as specced) | 53.8 / 102.6 / 143.8 | 61.0 / 136.2 / 187.0 |
| plain hold'em (realistic) | K18, route always open | 56.9 / 103.7 / 150.9 | 61.8 / 138.0 / 197.0 |
| top_heavy (realistic) | F | 60.5 / 141.5 / 209.1 | 128.2 / 324.6 / 378.1 |
| top_heavy (realistic) | K18 (as specced) | 61.8 / 143.4 / 238.4 | 130.6 / 341.0 / 452.7 |
| top_heavy (realistic) | K18, route always open | 63.2 / 141.0 / 208.0 | 128.3 / 325.2 / 405.4 |
| fast_schedule (realistic) | F | 56.8 / 110.7 / 141.8 | 62.1 / 136.8 / 191.2 |
| fast_schedule (realistic) | K18 (as specced) | 57.5 / 113.9 / 153.8 | 61.9 / 139.5 / 181.9 |
| fast_schedule (realistic) | K18, route always open | 59.2 / 106.9 / 133.3 | 60.1 / 137.0 / 184.9 |
| plain hold'em (mirror) | F | 60.6 / 109.6 / 138.6 | 69.0 / 136.0 / 186.5 |
| plain hold'em (mirror) | K18, route always open | 62.3 / 111.9 / 143.6 | 68.5 / 134.9 / 562.6 |

K11's members (r2s with its light shadow and lazy curve), gate always open: realistic act 74.3 / 143.0 / 207.1, hand
end 73.5 / 158.4 / 204.1; mirror act 85.2 / 150.0 / 193.0, hand end 83.0 / 152.7 / 186.5. F there: act 54.0 / 101.7,
hand end 61.3 / 134.2. Before the lazy curve, r2s cost +22 us at every hand end.

Under top_heavy payouts F's own hand-end p99 is above 200 us (324.6). That is F's ICM work at the hand end, not this
change. Every act p99 is under 200 us.

## 6. Identity

`tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`: on main 3896840 (code
cfbcd1af69) and on this branch at 559b416 (code 43d093622c), with separate output directories. All 14 chunks' sample
lists are identical (night, night_hard, realistic, top, night at both payout tables, night with doubling blinds). F
builds none of the new members (test), and `ship({})`'s members are base, hero, elite1 as before.

Tests: tests/test_sim_mirror.py adds nine S14 tests:
- members registered;
- light equals full, every decision, for r2s, elite2 and elite4;
- lazy curve equals eager;
- every twist plays as F with all new members routed;
- `strong_bvb` by section;
- the second route always open, never open, and its read;
- keep-defence.

With tests/test_compose*.py and tests/test_ship.py: 75 passed.

## 7. What I would still try

- **Three-handed preflop that holds against an exploiter.** This is the biggest open item: about +0.04 at four strong
  fields, against -0.24 three-handed with exploiter 1. Ideas:
  - a per-seat read (who re-raises our opens, and how often), since the table-level read is diluted by the third seat;
  - S13's `wants()` style test ("no opponent alive reads as a clear leak");
  - building three-handed preflop into S13's specialist, from solved tables rather than a donor.
- **Rival 2's re-shoves with a stricter gate.** K4/K11's re-shove part is worth +0.06 to +0.11 at strong fields but
  loses on fast_schedule (and its point estimates on night's payout guards are negative). A gate that reads the seat
  that raised, not the table, might keep strong openers and drop the ordinary ones that faster blinds turn into
  shovers.
- **Exploiter 3** (main 2a17295) was not run here: the branch predates it.
- **S13 overlap.** S13's `short_route` overrides both strong routes wherever it wants the decision (heads-up big blind
  only in its S5 spec). A paired screen with both on is needed before both ship.
