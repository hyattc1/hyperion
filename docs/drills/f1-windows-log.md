# F1: the five windows on the composite F (2026-11-02)

Branch `climb/f1-windows` from main ea4d36f. Backlog F1 (docs/drills/goal-plan.md): T5 and T6 are 52% of the score and
the window recipes were last checked on hybrid3_x, before the composite F shipped with the governor in its defaults.
Every number is model mode, eight rotations per seed, F as hyperion.ship builds it (dials on top of SHIP_DIALS; never
`tools/swap.py paired` specs), screen seeds 10000-10199 (200 x 8) unless named, at most two worker processes on a host
at load 5-7 (other workers running). No judge, outside, elite3/elite_judge or held-out field or variant was used.

Sections: 1 what each recipe reaches on F, 2 does it move play as stated, 3 points (confirm and guards), 4 the signal
table against F, 5 the window rehearsal, 6 stacking and the governor, 7 what changed, 8 open.

Scratch tools (session scratchpad `goal/f1/`, not in the repo): `probe.py` (F + dials in Hero's seat, every decision
booked: VPIP, PFR, first-in opens, cutoff/button opens, steals (first in from CO, BTN, SB), deep 3-bets, calls facing
an all-in, folds facing a postflop bet, bets when checked to; per seed points and busts, paired with F), `standings.py`
(a field's leaderboard with F in Hero's seat), `cfgdiff.py` (which member settings a recipe changes). The probe's
per-seed points equal climb_accept's night samples exactly (checked on a chunk: `equal: True 0.0`).

## 1. What each recipe reaches on F

F is not hybrid3_x with a route. Rival 3's core decides preflop only (route `post=hero,pre_raised_short=hero`: Hero
plays every postflop section and short facing a raise), and one exploit layer sits in front of every member: each
member's own layer is reset to the neutral `ExploitParams()` when it is built (hyperion/compose/bot.py, `_hero_member`,
`_hybrid_member`). So, resolved the hybrid3_x way (core dials plus Hero's recipe as `hero.<key>`):

| recipe (as on main) | keys that reach nothing on F | why |
|---|---|---|
| `survival` | `r3.call_edge`, `r3.raise_shift` | core postflop dials; postflop is Hero's |
| `passive` | `r3.bluff_scale` | the same; and `hero.preflop.open_frac` moves only the tables Hero plays whole |
| `dead_seats` | `hero.exploit.steal_min_fold` | the members' own layers are reset; the layer F has is `exploit.*` |
| `strong_field` | (all reach Hero, which plays only postflop on plain hold'em) | |
| `latency` | none (`{"exploit": null}` turns the front layer off) | |

Proof that the core postflop dials are dead in play, not only in config: survival with and without `r3.call_edge` and
`r3.raise_shift`, and passive with and without `r3.bluff_scale`, gave identical per-seed points and identical counts of
every booked decision over 1,600 night tables (and survival again over 1,600 `strong` tables).

## 2. Does each recipe move F's play the stated way? (night, 200 x 8)

| spec | pts | bust % | 1st % | 7-8th % | VPIP | open | CO/BTN open | steal | deep 3-bet | call an all-in | fold to a postflop bet | bet when checked to | spec - F | p99 us (wall) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F | 5.973 | 56.4 | 37.6 | 8.1 | 43.6 | 48.4 | 59.9 | 69.7 | 5.7 | 10.9 | 74.3 | 54.3 | | 301 |
| survival (main) | 5.982 | 57.9 | 37.4 | 7.2 | 42.9 | 48.4 | 59.6 | 69.4 | **4.0** | **6.8** | 73.9 | 54.2 | +0.009 ± 0.066 | 243 |
| survival + `hero.postflop.call_margin` 0.25 | 5.993 | 58.2 | 37.1 | 6.9 | 42.8 | 48.2 | 59.3 | 69.2 | 4.0 | 6.9 | **76.5** | 54.0 | +0.020 ± 0.073 | 220 |
| passive (main) | 5.971 | 55.9 | 38.6 | 8.3 | 44.2 | 49.7 | **63.5** | 72.4 | 5.8 | 10.6 | 74.2 | 55.3 | -0.002 ± 0.054 | 222 |
| passive F (layer `bet_min_fold` 0.35, no `r3.bluff_scale`) | 5.971 | 56.2 | 38.7 | 8.2 | 44.2 | 49.8 | **63.4** | 72.3 | 5.8 | 10.5 | 74.2 | **58.1** | -0.002 ± 0.062 | 209 |
| dead_seats (main: `r3.prior_scale` 0.5 + Hero's) | 6.022 | 55.8 | 39.8 | 7.8 | 45.0 | 51.3 | 63.8 | 72.5 | 6.0 | 11.2 | 74.9 | 54.2 | +0.049 ± 0.080 | 260 |
| dead_seats F (layer `steal_min_fold` 0.5, `hero.profiler_blend_n` 4) | 5.979 | 55.6 | 41.2 | 7.9 | 46.5 | 53.5 | **68.3** | **76.7** | 5.7 | 10.9 | 74.5 | 54.4 | +0.006 ± 0.074 | 262 |
| strong_field | 5.969 | 56.6 | 37.6 | 8.1 | 43.6 | 48.5 | 60.1 | 69.8 | 5.7 | 11.0 | 74.4 | 54.2 | -0.004 ± 0.021 | 217 |
| latency (main: `{"exploit": null}`) | 5.757 | 64.1 | 30.9 | 8.9 | 41.9 | 46.7 | 58.7 | 66.6 | 5.7 | 10.6 | 74.1 | **31.6** | **-0.216 ± 0.089** | 226 |
| latency F (`{"late_us": 0}`: no shadow decisions) | 5.952 | 57.7 | 36.8 | 7.9 | 43.1 | 48.0 | 59.2 | 69.1 | 5.7 | 10.8 | 73.8 | 54.4 | -0.021 ± 0.047 | 138 |
| every section to Hero, no shadows | 5.823 | 59.0 | 36.6 | 9.5 | 42.7 | 49.4 | 65.3 | 70.8 | 3.6 | 16.9 | 74.3 | 51.6 | -0.150 ± 0.118 | 108 |
| timeouts (`{"cheap": true}`) | 4.393 | 82.1 | 6.2 | 27.2 | **12.7** | 12.3 | 12.1 | 13.0 | 11.0 | 28.3 | 64.8 | 8.0 | **-1.580 ± 0.141** | 136 |

(The last numeric column is spec - F, paired per seed; bold = the stated effect, or a loss beyond noise. The p99 column
is the engine's wall-clock reading at load 6-7, not a latency measure.)

Latency, `tools/latency.py --bot composite --dials ... --n 20000` (random observations; load 5-7; the max and the
over-1-ms counts follow the host):

| dials | 8..1 mean / p99 us | 50/25/12/6/3/2/1/1 mean / p99 us |
|---|---|---|
| F | 53-56 / 133-152 | 59 / 186 |
| `{"exploit": null}` (latency on main) | 48-51 / 123-127 | 58 / 186 |
| `{"late_us": 0}` (latency F) | 36-38 / 96-97 | 43 / 158 |
| `{"late_us": 0, "exploit": null}` | | 38 / 148 |
| every section to Hero, no shadows | 30 / 90 | 30 / 78 |
| `{"start_level": 3}` (the governor's hero level) | 42 / 106 | |
| `{"cheap": true}` | 21 / 60 | 22 / 58 |

Verdict per recipe:
- `survival`: all-in calls and deep 3-bets drop as stated (10.9% -> 6.8%, 5.7% -> 4.0%), 7th-8th finishes 8.1% ->
  7.2%. "Fewer postflop calls" did not hold on F (Hero plays postflop; the core's call edge never decides). Hero's
  postflop call margin 0.25 makes it hold (folds 74.3% -> 76.5%) but measured -0.062 ± 0.055 against plain survival on
  the busting field (`strong`, section 4) and +0.011 ± 0.035 on night, so the recipe keeps Hero's play postflop and
  the claim was changed instead. Fixed: the two dead keys dropped (same play).
- `passive`: cutoff and button opens up as stated (+3.5); bets when checked to only +1.0, because postflop is Hero's.
  Fixed: the layer's `exploit.bet_min_fold` 0.35 (0.4 shipped) in place of the dead `r3.bluff_scale`: +3.8.
- `dead_seats`: on main it moved F's opens (+2.9) but the Hero half (steals by fold reads) reached nothing. Fixed: the
  layer's own `exploit.steal_min_fold` 0.5: steals +7.0, cutoff and button opens +8.4. `r3.prior_scale` 0.5 dropped
  (section 4: on F it costs on a dead-seat table and at strong tables).
- `strong_field`: changes nothing measurable on F, as the playbook says of the core: -0.004 ± 0.021 night. Kept.
- `latency`: on main it turned the layer off: about 5 us a call, nothing at p99 under top-heavy payouts, and -0.22
  points beyond noise (busts +0.62 a seed): the layer is worth more on F than on hybrid3_x. Fixed: `late_us` 0, the
  members not chosen skip the call (no shadows), 17 us a call and 30-37 us at p99, -0.021 ± 0.047.
- `timeouts`: every decision Hero's cheap path, as stated; -1.58 ± 0.14, an emergency.
- `slow_box`: resolves to exactly the governor already in SHIP_DIALS, so on F it is a no-op (identical spec after
  resolution); it remains the way to give the governor to the fallbacks.

## 3. Points: climb_accept confirm and guards (screen seeds)

`tools/climb_accept.py --set screen --stages confirm,guards --cand '{"dials": <the recipe as F resolves it>}'`
(`hyperion.ship.recipe(name, "composite")` after the fixes), base F, code 7d35910e32, 200 x 8 per cell, 03:37-04:52 at
load 6-13. cand - base, paired; bold = beyond noise. Every cell: 0 exceptions, 0 illegal, 0 timeouts for both.

| recipe | night | night_hard | realistic | top | night @10/7/5/4/3/2/1/0 | night @50/25/12/6/3/2/1/1 | night +double |
|---|---|---|---|---|---|---|---|
| `survival` | +0.009 ± 0.066 | **+0.096 ± 0.069** | +0.061 ± 0.066 | +0.000 ± 0.083 | +0.020 ± 0.106 | -0.390 ± 0.673 | +0.009 ± 0.063 |
| `passive` | -0.002 ± 0.062 | -0.046 ± 0.065 | **+0.075 ± 0.072** | -0.015 ± 0.069 | +0.006 ± 0.111 | +0.194 ± 0.740 | +0.028 ± 0.060 |
| `dead_seats` | +0.006 ± 0.074 | -0.001 ± 0.083 | **+0.106 ± 0.060** | **-0.115 ± 0.081** | +0.085 ± 0.122 | +0.013 ± 0.854 | +0.001 ± 0.065 |
| `strong_field` | -0.004 ± 0.021 | +0.016 ± 0.027 | +0.010 ± 0.018 | -0.003 ± 0.030 | +0.035 ± 0.038 | -0.036 ± 0.213 | +0.018 ± 0.019 |
| `latency` | -0.021 ± 0.047 | +0.018 ± 0.049 | -0.011 ± 0.035 | -0.015 ± 0.057 | -0.001 ± 0.082 | -0.129 ± 0.587 | -0.005 ± 0.048 |
| `timeouts` | **-1.580 ± 0.141** | **-1.254 ± 0.147** | **-2.067 ± 0.130** | **-1.137 ± 0.143** | **-2.356 ± 0.206** | **-13.237 ± 1.131** | **-1.331 ± 0.128** |
| `slow_box` | identical to F (the same resolved spec) | | | | | | |

Main's `latency` (the layer off) on night: -0.216 ± 0.089 (section 2). Nothing is a free gain (no recipe is up on
night, the primary field), and only the emergency `timeouts` costs everywhere; `dead_seats` costs at `top` (-0.12 ±
0.08), as at `elite` (section 4): a strong table's seats are not dead.

## 4. The signal table against F

Each signal needs standings that show it. F's line in candidate fields (standings.py, 50 x 8, 8..1): F rarely busts
early at a loose table (7th-8th 0-5% with maniacs and all-in bots in the field), so the "many firsts, many 7th/8th"
pattern is a strong table's: `strong` (F 1st 35.5%, 7th-8th 15.0%, against 37.6% / 8.1% on night) and `top` (18.8% /
14.8%). F sits mid-table only among top-team builds: `elite` (5th of 8, 1st 10.2%, 7th-8th 18.0%, 45.5% in 4th-6th; the
top six within 0.12 points, so it also shows the strong-and-tight signal). Near-zero scorers: a table with four of them
(`hero, crasher, timeout, timeout_then_recover, timeout_burst, tag, pushfold, loose_aggro`, below "deadx": they score
2.9-4.3 of 8..1, F 1st 80%) and the stock `timeouts` field. Timeouts of our own: tools/slowbox.py's 8x and 5x slower box
(seat scope, CPU clock). Every row below is 200 x 8 paired against F (slow box: 100 x 8).

| signal | field | recipe | what moved | spec - F | busts a seed |
|---|---|---|---|---|---|
| many firsts, many 7th/8th | `strong` | survival | all-in calls 10.5% -> 7.0%, 3-bets 6.3% -> 4.3%, 7th-8th 16.0% -> 14.3%, 1st 34.8% -> 32.8% | +0.035 ± 0.084 | +0.06 |
| | | survival + `hero.postflop.call_margin` 0.25 | the same, folds to a postflop bet 69.5% -> 72.4% | -0.027 ± 0.093 (-0.062 ± 0.055 against survival) | +0.14 |
| | | passive / dead_seats / latency (elsewhere) | | +0.026 ± 0.063 / -0.032 ± 0.099 / -0.011 ± 0.064 | |
| mid-table, few firsts, few lasts | `elite` | passive (main) | CO/BTN opens 46.7% -> 51.2% | -0.064 ± 0.063 | +0.04 |
| | | passive (F) | CO/BTN opens 46.7% -> 51.5%, bets when checked to 55.4% -> 58.5% | -0.030 ± 0.069 | -0.03 |
| | | survival + cm 0.25 / strong_field (elsewhere) | | +0.025 ± 0.085 / -0.008 ± 0.020 | |
| | | dead_seats (F) / with `r3.prior_scale` 0.5 too (elsewhere) | steals 58.5% -> 65.9% / 68.3% | **-0.160 ± 0.084** / **-0.218 ± 0.097** | +0.19 / +0.20 |
| many near-zero scorers | deadx | dead_seats (main: `r3.prior_scale` 0.5, Hero's keys) | opens 66.6% -> 68.6% | **-0.109 ± 0.063** | +0.14 |
| | | `r3.prior_scale` 0.5 + layer steal 0.5 + Hero's | steals 85.5% -> 92.4% | -0.013 ± 0.077 | -0.06 |
| | | dead_seats (F: layer steal 0.5, `hero.profiler_blend_n` 4) | steals 85.5% -> 92.1%, opens 66.6% -> 74.6% | +0.057 ± 0.063 | -0.14 |
| | | layer steal 0.5 alone | the same | +0.051 ± 0.060 | -0.12 |
| | | survival / survival + cm 0.25 (elsewhere) | all-in calls 15.0% -> 7.3% | **+0.082 ± 0.064** / **+0.121 ± 0.073** | -0.09 / -0.14 |
| | | passive (F) (elsewhere) | | +0.002 ± 0.048 | |
| | `timeouts` | dead_seats (main) | CO/BTN opens 53.9% -> 56.6% | -0.022 ± 0.064 | -0.01 |
| | | `r3.prior_scale` 0.5 + layer steal 0.5 + Hero's | steals 67.2% -> 76.7% | +0.033 ± 0.070 | -0.13 |
| | | dead_seats (F) | steals 67.2% -> 75.4%, CO/BTN opens 53.9% -> 64.3% | **+0.058 ± 0.047** | -0.17 |
| | | layer steal 0.5 alone | the same | **+0.056 ± 0.046** | -0.17 |
| strong and tight | `top` | strong_field | nothing over 0.1 point of any rate | -0.003 ± 0.030 | +0.02 |
| | `elite` | strong_field | the same | -0.008 ± 0.020 | +0.02 |

Our own timeouts: F on a slower box (tools/slowbox.py, night, seeds 10000-10099 x 8, the governor on as shipped):

| box | spec | points ± 95% | spec - F | timeouts a table | decisions below level 0 |
|---|---|---|---|---|---|
| 8x, 8..1 | F | 5.932 ± 0.168 | | 4.34 | 30.4% |
| | latency (F: `late_us` 0) | 5.921 ± 0.160 | -0.011 ± 0.128 | **2.96** | 4.5% |
| | latency (main: the layer off) | 5.592 ± 0.151 | **-0.340 ± 0.130** | 3.32 | 11.3% |
| | timeouts (`cheap`) | 4.361 ± 0.155 | **-1.571 ± 0.199** | 0.39 | 0 |
| 5x, 50/25/12/6/3/2/1/1 | F | 24.759 ± 1.618 | | 1.55 | 3.2% |
| | latency (F) | 24.278 ± 1.441 | -0.481 ± 1.290 | **1.26** | 0.9% |
| | latency (main) | 21.203 ± 1.455 | **-3.556 ± 1.553** | 1.23 | 1.6% |
| | timeouts | 11.034 ± 0.921 | **-13.724 ± 1.791** | 0.15 | 0 |

What the signal table gets right and wrong on F:
- **survival** answers its signal: early busts down a point or two of share, points level on the busting table (+0.04 ±
  0.08) and on every guard (section 3). It does not beat no change beyond noise on its own signal. It did beyond noise
  on two others: among dead seats (deadx +0.082 ± 0.064; the seats that bust F there are the live ones that shove) and
  on `night_hard` (+0.096 ± 0.069). A cheap second choice whenever F's busts come from calling shoves.
- **passive** moves play as stated and is level on its signal (`elite`, -0.03 ± 0.07): F mid-table among top-team builds
  is not "too passive", it is the room. The fix made it less costly there than main's (-0.06).
- **dead_seats** as on main lost on its own signal (-0.11 ± 0.06 on deadx): `r3.prior_scale` 0.5 opens F wider than
  the layer's dead-seat reads already do. With the layer's steal key instead it is the one recipe that gains beyond noise
  on its signal (`timeouts` +0.06 ± 0.05), and it must stay on that signal: -0.16 ± 0.08 at a table of top-team builds.
- **strong_field** is the frozen bot on F (no rate moves by 0.3 points). The row now says so.
- **latency / timeouts**: main's `latency` cost a third of a point on a slow box. F's (no shadows) cuts timeouts by a
  fifth to a third at level points. `timeouts` cuts them by 90% but loses 1.6 (8..1) and 14 of 100 (top-heavy) even on
  the slow box, because the governor already steps F down level by level: it is for errors, not slowness.

## 5. Window rehearsal on recorded standings

A rehearsal repo (detached worktree of this branch, session scratchpad `goal/f1/reh/repo`), fake kit B (module
`decide`; the reference entry as `submission/agent.py`), `rules_tonight.json` = the catalog's `top_heavy` (payouts
50/25/12/6/3/2/1/1). Frozen T1 package: F, packed at the freeze. T1 standings: standings.py on a field with four
near-zero scorers under those payouts, seeds 40000-40099 x 8 (F as shipped):

| rank | bot | mean points | 1st % | 2nd-3rd % | 4th-6th % | 7th-8th % | bust % |
|---|---|---|---|---|---|---|---|
| 1 | ourbot | 36.6 ± 1.3 | 70.6 | 6.4 | 10.8 | 12.2 | 27.9 |
| 2 | loose_aggro | 14.5 | 14.4 | 33.8 | 22.9 | 29.0 | 79.6 |
| 3 | tag | 13.6 | 3.6 | 51.2 | 30.4 | 14.8 | 83.4 |
| 4 | pushfold | 13.2 | 6.1 | 44.9 | 28.1 | 20.9 | 83.8 |
| 5 | timeout_burst | 6.7 | 4.6 | 16.2 | 17.2 | 61.9 | 91.0 |
| 6 | crasher | 5.2 | 0.0 | 13.2 | 84.2 | 2.5 | 99.5 |
| 7 | timeout | 5.1 | 0.0 | 14.5 | 84.2 | 1.2 | 99.6 |
| 8 | timeout_then_recover | 5.1 | 0.6 | 19.8 | 22.1 | 57.5 | 96.5 |

Read: four seats score like always-fold; we win 71% and finish 7th-8th only 12% (under the 25% of a fair seat), so the
busting signal is not on. Signal: near-zero scorers -> `dead_seats`.

**R1, prompt 06 as on main** (03:32-03:36, load 5-6), each step timed (`goal/f1/step.sh`):

| step | command | minutes | result |
|---|---|---|---|
| measure, before | `python -m hyperion.sim --tables 300 --seed 11 --mode model --field realistic@ship --rules submission/rules_tonight.json` | 0.48 | ship 27.01 ± 2.46 |
| measure, after | the same with `--dials dead_seats` | 0.47 | ship 28.94 ± 2.47: "not lower", so kept |
| keep | `python -m hyperion.ship --set dead_seats` | 0.00 | DIALS printed |
| strict run | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules ...` | 0.86 | exc 0, ill 0, tmo 2 |
| kit simulator | `HYPERION_CHECK=1 python -m hyperion.drills.fakekits.kit_b.runner submission/agent.py --hands 100` | 0.00 | PASS, 0 / 0 / 0 |
| repack | `python tools/pack.py --entry submission/agent.py --out dist/ --extra submission/rules_tonight.json --note ...` | 0.01 | `bot composite dials {...}` |
| gate | `python tools/gate.py dist/submission.zip --kit b --tables 40 --rules ...` | 0.00 | **GATE FAIL: no submission.py at the top of dist/submission.zip** |
| gate again | the same with `--entry agent.py` | 0.37 | GATE PASS, -1.25 ± 7.34 |

What broke or could not be trusted:
1. **The gate failed a good package**: prompt 04 packs `--entry submission/<entry>.py` under the entry's own name, and
   the gate's default entry was `submission.py`. Fixed: the gate finds the entry (submission.py, else the package's only
   top-level .py; several: it asks for `--entry`), with a test.
2. **The measure step could not verify anything.** Two unpaired 300-table runs on `realistic` (not the night field) with
   the wall-clock guards on (model mode in hyperion.sim keeps SafeBot's clock and the governor, so a loaded box changes
   the play): ±2.5 points of 100 each under top-heavy payouts, so "not lower" passes or fails by luck. Replaced by
   `tools/climb_accept.py --stages window`: the night field under tonight's rules file (and variant), 200 seeds x 8,
   paired, exactly replayable; the verdict is "not beyond noise down". Recipe names are specs (`--cand
   dead_seats+survival`), and the cache survives `--set` (the switch's record lines are left out of the code version),
   so a later window replays only its candidate. A spec named twice runs once (warming F's cache at the freeze).
3. Prompt 06 named "the strict run and the kit simulator" without commands. It now gives each step's command and time.

**R2, prompt 06 as fixed** (04:54-04:59, load 9.5-13, 2 workers, cache cold):

| step | minutes | result |
|---|---|---|
| 1. window check: `climb_accept --stages window --base '' --cand 'dead_seats' --rules submission/rules_tonight.json --workers 2` | 3.22 | night +rules: +0.013 ± 0.854 of 100, `[x]` |
| 2. `python -m hyperion.ship --set dead_seats` | 0.00 | `DIALS = {'exploit.steal_min_fold': 0.5, 'hero.profiler_blend_n': 4.0}` |
| 3. strict run, 100 tables | 0.31 | ship exc 0, ill 0 (tmo 40 of 18,332 hands at load 12) |
| 4. kit simulator, 100 hands, `HYPERION_CHECK=1` | 0.00 | PASS, 0 timeouts, 0 exceptions, 0 illegal |
| 5. repack | 0.01 | `bot composite dials {'exploit.steal_min_fold': 0.5, 'hero.profiler_blend_n': 4.0}` |
| 6. gate, 40 tables, no `--entry` | 0.41 | GATE PASS, +2.67 ± 6.66; it found agent.py |
| total | **3.96** | |

**R3, the next window** (T3, `dead_seats` kept, cache warm from R2): `--base dead_seats --cand dead_seats+survival`:
1.57 minutes (the base came from the cache: the same code version after `--set`), -0.130 ± 0.679, `[x]`.

On the night laptop (8 cores, `--workers 4`, quiet) the check should take about half of these. With the cache warmed at
the freeze, every window's check plays only its candidate. The whole loop fits the 12-minute box with 6-8 minutes to
spare for the standings and the upload.

The uploaded zip itself keeps the governor (section 6). The frozen sha256 of two packs of the same tree differed (zip
entries carry file times): the frozen hash is the one recorded at the freeze, as the playbook says.

## 6. Stacking and the governor

The governor is in the composite's SHIP_DIALS since batch 2 (`deadline_ms` 0.8, `panic_window` 60, `panic_ladder`,
`panic_recover` 40, `degrade` "noshadow,lean,hero"). `python -m hyperion.ship --set <recipes>` writes only the
recipes' dials into DIALS, and `hyperion.compose.bot.ship()` lays DIALS on top of SHIP_DIALS, so nothing a window keeps
can drop it. `slow_box` resolves to exactly those five keys on the composite (a no-op there, identical spec after
resolution); on hybrid3_x and Hero it is how they get a governor (they have none by default).

Proof (tests/test_ship.py):
- `test_set_keeps_the_composites_governor`: for every recipe, `slow_box`, and the stacks `survival+passive`,
  `slow_box+survival`, `survival+slow_box`, `dead_seats+latency`, `latency+dead_seats`, `passive+timeouts`,
  `strong_field+survival+passive`: `--set` on a copy of ship.py, read the record back, build: SafeBot's deadline
  0.8 ms, window 60, ladder, recover 40, the composite's three levels and its `degrade` string, every time; the record
  carries no governor key unless `slow_box` was named; the record a package carries (write_record / read_record, as
  tools/pack.py and tools/gate.py use it) builds the same; hybrid3_x with `--set survival` has none, with
  `slow_box+survival` it has one.
- `test_every_composite_recipe_key_reaches_a_part_that_decides`: every key of every composite recipe changes a setting
  of the built bot; none is a core postflop dial while the shipped route sends every postflop section to Hero; Hero's
  recipe keys reach the composite as `hero.<key>`, the layer's as `exploit.<key>`.
- In the rehearsal (section 5) the uploaded zip itself, unpacked and imported with `python -I` from another
  directory: `SHIP composite`, `DIALS {'exploit.steal_min_fold': 0.5, 'hero.profiler_blend_n': 4.0}`, governor
  `0.0008 60 True 40`, levels 3, degrade `noshadow,lean,hero`, the layer's steal read 0.5.

On main, `latency+dead_seats` would also have been safe (the dead Hero key did not conflict with the layer off). With
F's `latency` no longer turning the layer off, no composite stack mixes `{"exploit": null}` with `exploit.*` keys
(parse_dials raises on that: loud, not silent).

## 7. What changed (commits on climb/f1-windows)

- `hyperion/ship.py`: COMPOSITE_RECIPES, the composite's own recipes (survival without the core's dead postflop dials;
  passive with the layer's `exploit.bet_min_fold` 0.35; dead_seats with the layer's `exploit.steal_min_fold` 0.5 and
  `hero.profiler_blend_n` 4, without `r3.prior_scale`; strong_field Hero's keys; latency `late_us` 0; timeouts `cheap`).
  hybrid3_x and Hero keep theirs. The API card (`tools/apicard.py`, CONTRACTS.md) shows all three columns.
- `tools/climb_accept.py`: `--stages window`, recipe names as specs, `--rules FILE` and `--variant` on the window,
  confirm, guards and elite cells, a code version that ignores the switch's record lines, a spec named twice runs once.
- `tools/gate.py`: finds an entry not named submission.py.
- Tests: `test_set_keeps_the_composites_governor`, `test_every_composite_recipe_key_reaches_a_part_that_decides`
  (tests/test_ship.py), tests/test_climb_accept.py, `test_the_entry_is_found_when_it_is_not_named_submission_py`.
- Docs: prompt 06 (F's recipes, the six steps with commands and rehearsed minutes, the window check), PLAYBOOK section
  5 (F's column with what moved and the points; the two stale, headerless tables below it removed), Stage 6, the stage
  table, the freeze (warm the cache), the revision log; docs/decisions.md entry "The windows on F".

## 8. Open

- hybrid3_x's `dead_seats` has the same dead Hero key (`hero.exploit.steal_min_fold`: its fallback Hero's layer is off
  when the front layer is on). Not changed: the fallback was not measured here.
- No recipe gains on night, and two of them (`dead_seats`, `passive`) are level or worse at a table of top-team builds.
  The windows answer standings; they do not buy points. `survival` gained beyond noise among dead seats and on
  `night_hard`, so it is the cheap second choice when the standings show busts from calling shoves.
- The signal fields are our own constructions (a table with four near-zero scorers, `strong`, `elite`); the night's
  room will mix them. The window check plays the night field, which is our guess at that mix.
- Pack's zip is not byte-reproducible (file times): harmless for the windows, worth a deterministic zip if anyone
  compares hashes across packs.
