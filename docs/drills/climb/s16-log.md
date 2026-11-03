# S16: a trust weight on the risk-taking preflop reads at strong tables (running log)

Branch climb/s16-read-trust, from main 724cc7f (batch 5's F). Brief (coordinator, 2026-11-03): item 3 of
docs/research/Edges against strong opponents.md. First repeat S12's warm-store split on the strong fields at 200
seeds: does the loss at strong tables come from the preflop reads that widen F's risk (rival 3's core's fold reads in
its steal price and open clauses, the layer's steal read)? If yes, add `r3.read_trust` and `exploit.read_trust`
(prior + (observed - prior) x n / (n + 10), nothing below 10 chances, only while Profiler.strong_table reads strong at
batch 5's threshold; the defensive reads untouched), fix a per-seat fallback gate before screening, and screen with
`--aim strong`.

Rules kept: screen seeds 10000-10199 only for points; recordings and the firing diagnostic on 8800-8849 (fresh, under
10000; S13 used 8800-8803 for a diagnostic). No held-out set (H1-H18), judge seed, judge bot, judge field or held-out
variant was run, read or profiled. Model mode, eight rotations per seed. At most three worker processes, nice 5; the
host was at load 19-37 with other measurements running. Every measurement of F runs from a detached worktree at main's
code (`goal/wt_s16m`, 724cc7f); scratch tools in `goal/s16/` (never shipped).

## Tools (scratch, `goal/s16/`)

- `warmlib16.py`, `rec16.py`: S12's warm-read device (goal/s12/warmlib.py) ported to batch 5's composite (members by
  name: the base's rival 3 core, the hero member's profiler, the base's fallback Hero's profiler, the front layer).
  S12's stores and counters exactly (the size, probe and raise-guard counters added since stay cold in every arm).
- `warm16.py`: tools/climb_accept.py with four arms of F, `{"bot": "w16_<arm>"}`, F's own cells shared:
  - `all`: S12's warm full (every store at the long-run truth from hand 0);
  - `risk`: only the reads that widen preflop risk warm: rival 3's core's fold read in an unopened pot (`_fold_prob`
    while max(bets) <= bb: the steal price `ev_steal`, the open clauses `ev_steal > 0` and `pf > 0.9`, the short
    shove's fold equity and caller) and the layer's preflop cell (steal_min_fold's rates, a long-run-dead seat's
    streak);
  - `rest`: every other store S12 loaded warm, the risk reads cold (Hero's two profilers, the layer's postflop cells,
    rival 3's other reads and its 3-bet reads);
  - `prior`: cold F with the risk reads at their priors (rival 3's 0.6 and its VPIP prior, dead seats kept; the
    layer's 0.65, so steal_min_fold 0.7 never fires; the dead-seat steal kept). The limit s -> infinity of the
    trust weight, ungated: whether F's own cold fold reads pay or cost at strong tables.
  Patches are instance-gated: only F's seat reads differently (the mirror's f_copy seats play as shipped).
- Recordings: `rec16.py`, seeds 8800-8849 x 8, F in the hero seat, per field (elite, elite_b, mirror, mirror_b).

## 01:50: the recordings (rec16.py, 8800-8849 x 8, F at 724cc7f in the hero seat)

| field | F points | hands per identity | seconds (3 workers, load 25-37) |
|---|---|---|---|
| elite | 4.907 | 37,000-42,000 | 85 |
| elite_b | 4.900 | 38,700-43,700 | 77 |
| mirror | 4.603 | 40,600-44,300 (f_copy 131,700 over three seats) | 166 |
| mirror_b | 4.754 | 41,100-43,700 (f_copy 131,300) | 103 |

What the risk reads see in the long run (rival 3's core: folds per raise faced, re-raises per raise faced, VPIP; the
layer's decayed preflop fold rate):

| field | seats, fold to a raise (rival 3) | re-raise rate | raises faced per 200 hands | layer's fold rate |
|---|---|---|---|---|
| elite | agent_pushfold 0.87, agent_default 0.86, rival2 0.81, rival3 0.80, elite1 0.77, rival1 0.76, elite2 0.74 | 0.025-0.077 | 106-109 | 0.73-0.81 |
| elite_b | agent_pushfold 0.87, rival2 0.82, rival3 0.81, elite4 0.79, elite1 0.78, rival1 0.75, elite2 0.75 | 0.052-0.083 | 107-110 | 0.74-0.81 |
| mirror | rival2 0.82, hybrid3_x 0.82, f_copy 0.82, elite1 0.79, elite2 0.76 | 0.054-0.074 | 105-109 | 0.75-0.80 |
| mirror_b | rival2 0.82, f_copy 0.82, elite4 0.80, elite1 0.79, elite2 0.75 | 0.054-0.079 | 105-108 | 0.75-0.80 |

Every strong seat folds to 74-87% of the raises it faces, above both priors (rival 3's 0.6, the layer's 0.65), and
faces about one raise every two hands. S12's night recording (older F) has the same range for the decent seats
(0.70-0.95; stations and maniacs 0.0). So the fold read alone does not tell a strong seat from a night seat, and the
trust weight's n passes 10 by about hand 20 of a table; from there on, with s = 10, it moves a 0.8 read by about
0.01-0.03 (n = 50: 0.767 against 0.785 as built). Most of what the weight can change is the first 20-30 hands.

## 02:00-02:19: the warm-store split, elite and elite_b (screen 10000-10199 x 8; arm - F, paired)

`warm16.py --cand '{"bot": "w16_<arm>"}' --set screen --stages elite --cells el2 --workers 3 --out ca` (F's cells
shared; 0 errors, 0 timeouts in every cell).

| arm | elite | elite_b |
|---|---|---|
| F (cold, as shipped) | 4.865 | 4.638 |
| all warm (S12's ceiling) | **-0.142 ± 0.124** DOWN | +0.028 ± 0.117 |
| risk reads warm only | **-0.133 ± 0.104** DOWN | -0.070 ± 0.092 |
| everything else warm (risk reads cold) | -0.000 ± 0.104 | +0.056 ± 0.110 |
| risk reads at their priors (cold F, ungated) | +0.056 ± 0.090 | **+0.136 ± 0.088** UP |

## Pre-registered before any screen (02:20)

The candidate rule is the brief's, with three choices fixed here:
- **One-sided.** The trusted read caps the read: a seat's fold read is min(read as built, prior + (observed - prior)
  x n / (n + 10)), and the prior alone (0.6 rival 3, 0.65 the layer) while n < 10. A fold read under its prior (a seat
  that calls our raises) already narrows our risk; the symmetric formula would raise it to the prior early in a
  table, i.e. widen our risk on the prior's say-so. A dead seat's 1.0 stays (rival 3's dead flag and the layer's dead
  streak are not fold rates). The short shove's caller range (rival 3 models it as 1 - the loosest seat's fold read)
  keeps the read as built: shrinking it would widen the assumed calling range and raise the shove's equity.
- **Where.** Rival 3's core: every `_fold_prob` of its unopened branch that enters the fold equity `pf` (behind and
  limpers: the deep steal price `ev_steal`, its open clauses `ev_steal > 0` and `pf > 0.9`, and the short shove's
  `pf`). The layer: steal_min_fold's product. Untouched: the 3-bet defence (`r3.v3_defend` and its reads), the
  re-shove's fold equity facing a raise, the size read (D3), the probe read (S11), the layer's postflop cells, Hero.
- **Gate.** The hero member's Profiler.strong_table at the strong route's threshold (strong_rr 0.2, prior 0.15 worth
  10 raises: batch 5's), evaluated before each preflop decision; hold'em tables only (hero.holdem_table), so the 22
  twist variants play exactly as F (test) and only top_heavy, antes_from_level_3, fast_schedule and straddle are
  screened.

Candidates (dials on top of SHIP_DIALS):
- **T1** = `{"r3.read_trust": 10, "exploit.read_trust": 10}` (min_n 10 by default): the brief's.
- **T2, the fallback** = T1 + `{"trust_seat_rr": 1}`: a seat that re-raised one of my first-in raises this table
  takes the weight even while the table does not read strong (the per-seat share of the strong-table signal: the
  seats that make the table read strong are the seats that re-raise my opens). **Rule:** T2 replaces T1 if the firing
  diagnostic (gaterate16.py, 8800-8805 x 8, no points) finds the table gate on in fewer than half of F's unopened
  preflop decisions at the four strong fields pooled.
- **T3** (only if the chosen T1/T2 has no strong cell beyond noise up): the same gate with `read_trust` 10^9, i.e.
  the risk reads at their priors while the gate is open: the `prior` arm above, gated. Motivated by the split, not by
  any screen. No other value is tried.

Screens: each candidate's elite stage first (the five strong cells); the full `--aim strong` table (confirm, guards,
elite, exploit, the four hold'em-structure variants) only for a candidate with a strong cell beyond noise up.

## 02:20-02:47: the warm-store split, mirror and mirror_b (same command, `--cells mi2`)

The whole split, arm - F, paired, 200 seeds x 8 (0 errors, 0 timeouts in every cell):

| arm | elite | elite_b | mirror | mirror_b |
|---|---|---|---|---|
| F | 4.865 | 4.638 | 4.498 | 4.466 |
| all warm (S12's ceiling) | **-0.142 ± 0.124** DOWN | +0.028 ± 0.117 | -0.050 ± 0.121 | -0.022 ± 0.129 |
| risk reads warm only | **-0.133 ± 0.104** DOWN | -0.070 ± 0.092 | **-0.217 ± 0.096** DOWN | -0.065 ± 0.100 |
| everything else warm | -0.000 ± 0.104 | +0.056 ± 0.110 | +0.094 ± 0.115 | **+0.130 ± 0.117** UP |
| risk reads at their priors | +0.056 ± 0.090 | **+0.136 ± 0.088** UP | **+0.147 ± 0.091** UP | **+0.210 ± 0.093** UP |

**The diagnostic's answer: yes, and more clearly than S12's.** The preflop reads that widen F's risk carry the loss at
strong tables: known perfectly from hand 0 they lose in all four fields (two beyond noise), while every other read
known perfectly is level or gains (mirror_b up). Read at their priors instead of observed, they gain in all four
(three beyond noise). S12's -0.236 at elite was the risk reads' (-0.133 here), not Hero's or the 3-bet defence's.

But the split also says what kind of error it is. The warm arm is the long-run truth (rival 3's fold-to-a-raise
0.74-0.87 for every strong seat), and F's cold read reaches it within the table (S12: preflop reads settle in 60-100
hands). So the loss is not small-sample noise in the read: it comes from acting on a correct long-run
fold-to-a-raise rate. Likely reason (not measured here): the rate pools every raise a seat faces, most of them not
steals, and a strong seat defends a late steal more than that (F's first-in raises are re-raised 24-49% at these
tables, S9), so the read overstates the steal's fold equity and the prior (0.6) is closer to the spot. A trust weight with s = 10 shrinks small samples; it cannot fix a read that is biased at any
sample size, and after about 20 hands it leaves the read within 0.01-0.03 of the long-run rate. T3 (pre-registered
above) is the version that matches this finding.

## 02:48-02:55: the firing diagnostic (gaterate16.py at 1b875ec, T2's dials, 8800-8805 x 8, no points)

At each preflop decision of F in an unopened pot on a hold'em table: is the table gate on (hero member's
Profiler.strong_table 0.2 / 0.15 / 10), does the per-seat gate add a seat, and does rival 3's core's answer change
with the weight (the same decision recomputed without it). Share of spots (the first run wrapped its patches once per
job, so its absolute counts are inflated by a per-worker factor; shares and the per-decision change rate are not; a
clean re-run is below):

| field | table gate on | per-seat gate adds | either | rival 3's decision changed by the weight | layer steal_fold fires (48 tables) |
|---|---|---|---|---|---|
| elite | 0.27 | 0.43 | 0.70 | 1.6% of weighted spots | 43 |
| elite_b | 0.35 | 0.40 | 0.76 | 2.0% | 44 |
| mirror | 0.42 | 0.31 | 0.73 | 1.4% | 139 |
| mirror_b | 0.40 | 0.34 | 0.74 | 2.1% | 137 |
| elite_night | 0.26 | 0.41 | 0.67 | 1.9% | 49 |
| night | 0.11 | 0.60 | 0.71 | 1.2% | 71 |
| realistic | 0.12 | 0.51 | 0.63 | 1.4% | 71 |

Every change is a raise the core would have made and no longer makes. By the pre-registered rule (the table gate on
in fewer than half of the strong fields' spots: 0.27-0.42), **T2 (the per-seat fallback) replaces T1**. Two things
this shows before any screen:
- The per-seat gate does not tell strong tables from weak ones: night's seats re-raise F's opens too (0.60 of night's
  spots have such a seat behind). The table gate does (0.11-0.12 on night and realistic, 0.26-0.42 at strong tables).
- The weight changes 1-2% of the core's unopened decisions wherever it applies, because it acts mostly where n < 10
  (the first ~20 hands, when the table gate is still shut by its own prior). Expect T2 near F everywhere.

## 02:50-02:57: identity (idcheck.py)

`climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards` (the brief's check) and `--set
10000:10025 --stages elite,exploit`, once in the detached main worktree (724cc7f) and once on the branch (1b875ec),
separate caches: **all 28 cells identical sample for sample** (night, night_hard, realistic, top, night under both
payout tables and the doubling schedule; elite, elite_night, mirror, elite_b, mirror_b; all nine exploit cells). With
the dials off no gate runs (`_trust_prof` is None), rival 3's core takes `_fold_prob` and the layer's steal product
skips the cap; the new counters (the layer's undecayed raises faced, the profiler's re-raises by seat) feed nothing
else. F's cached cells at main's version were then copied to F's key at the branch's version (fda64bac50, key
e7752e7cf440) for the screens.

**Amendment to T3, 02:58 (after the firing diagnostic, before any screen of a candidate).** T3 keeps T1's table gate
alone, not T2's per-seat fallback: T3 = `{"r3.read_trust": 1e9, "exploit.read_trust": 1e9}`. The fallback was fixed
for a weight that changes 1-2% of decisions; at the priors the change is large (the `prior` arm moved the strong fields
by +0.06 to +0.21), and the per-seat gate is open at 0.60 of night's spots against the table gate's 0.11, so with it T3
would remove the fold-read steals that pay against night's weak seats. The table gate is the one that tells the
tables apart.

## 02:57-03:08: T2's elite stage (code 1b875ec, version fda64bac50; screen 10000-10199 x 8)

`climb_accept --cand '{"dials": {"r3.read_trust": 10.0, "exploit.read_trust": 10.0, "trust_seat_rr": 1}}' --set
screen --stages elite --aim strong --workers 3 --out ../s16/ca` (from wt_s16; F's cells copied, elite_night's new):

| cell | F | T2 | T2 - F | |
|---|---|---|---|---|
| elite | 4.865 | 4.888 | +0.023 ± 0.042 | level |
| elite_night | 5.422 | 5.419 | -0.003 ± 0.045 | level |
| mirror | 4.498 | 4.524 | +0.026 ± 0.051 | level |
| elite_b | 4.638 | 4.649 | +0.011 ± 0.049 | level |
| mirror_b | 4.466 | 4.537 | **+0.070 ± 0.049** | UP |

Small, as the firing diagnostic said (intervals a half of the split's: few decisions change), and four of five point
estimates positive. mirror_b is beyond noise up, so by the pre-registered plan T2 gets the full table; T3 does not run.

## 03:08-03:57: T2's full screen (code 1b875ec; screen 10000-10199 x 8)

`climb_accept --cand '{"dials": {"r3.read_trust": 10.0, "exploit.read_trust": 10.0, "trust_seat_rr": 1}}' --set screen
--stages confirm,guards,elite,exploit,variants --variants top_heavy,antes_from_level_3,fast_schedule,straddle
--variant-seeds 200 --aim strong --workers 3 --out ../s16/ca`. T2 - F, paired; 0 errors and 0 timeouts in every
cell for both specs.

| stage | cell | F | T2 | T2 - F | |
|---|---|---|---|---|---|
| confirm | night | 5.972 | 5.956 | -0.016 ± 0.045 | level |
| guards | night_hard | 5.499 | 5.530 | +0.031 ± 0.052 | level |
| | realistic | 6.370 | 6.358 | -0.012 ± 0.036 | level |
| | top | 5.058 | 5.071 | +0.013 ± 0.048 | level |
| | night @10/7/5/4/3/2/1/0 | 6.199 | 6.210 | +0.010 ± 0.080 | level |
| | night @50/25/12/6/3/2/1/1 | 24.699 | 24.568 | -0.131 ± 0.530 | level |
| | night, doubling blinds | 5.848 | 5.814 | -0.033 ± 0.041 | level |
| elite | elite | 4.865 | 4.888 | +0.023 ± 0.042 | level |
| | elite_night | 5.422 | 5.419 | -0.003 ± 0.045 | level |
| | mirror | 4.498 | 4.524 | +0.026 ± 0.051 | level |
| | elite_b | 4.638 | 4.649 | +0.011 ± 0.049 | level |
| | **mirror_b** | 4.466 | 4.537 | **+0.070 ± 0.049** | UP |
| exploit | exploit (exploiter 1, 8-max) | 5.839 | 5.836 | -0.003 ± 0.111 | level (exploiter 4.608 -> 4.646) |
| | exploit_hu | 9.227 | 9.205 | -0.022 ± 0.025 | level (upper bound +0.003) |
| | exploit_3 | 8.458 | 8.395 | -0.063 ± 0.093 | level |
| | exploit2 / exploit2_3 | 5.844 / 7.378 | 5.826 / 7.382 | -0.018 ± 0.088 / +0.003 ± 0.034 | level |
| | exploit2_hu | 7.848 | 7.848 | +0.000 ± 0.000 | identical |
| | exploit3 / exploit3_3 | 5.471 / 7.528 | 5.483 / 7.492 | +0.012 ± 0.093 / -0.037 ± 0.061 | level |
| | exploit3_hu | 8.268 | 8.268 | +0.000 ± 0.000 | identical |
| variants | top_heavy (of 100) | 28.654 | 28.662 | +0.008 ± 0.462 | level |
| | antes_from_level_3 | 6.496 | 6.467 | -0.029 ± 0.042 | level |
| | fast_schedule | 6.122 | 6.135 | +0.013 ± 0.035 | level |
| | straddle | 6.412 | 6.405 | -0.007 ± 0.010 | level (upper bound +0.003) |
| | the other 22 entries | | | | identical by construction (hold'em gate; test) |

Verdict (`--aim strong`): **ACCEPT** on the screen: mirror_b beyond noise up, night not down, no guard, elite,
exploit or variant cell down. The gain is small and narrow: one strong cell of five, +0.07, the other four within
+0.03. Closest to a down call: exploit_hu (-0.022 ± 0.025) and straddle (-0.007 ± 0.010), both with upper bounds at
+0.003; exploiter 1 heads-up re-raises our opens (the per-seat gate opens), and the weight then gives up some of the
button's raise-first-in steals against it.

**T3 is screened as well (amendment, 03:58, before any T3 number).** The plan ran T3 only if T2 failed; T2 passed, but
its gain is a sixth of what the split says the risk reads cost (the `prior` arm: +0.14 to +0.21 at three strong
fields), and the coordinator should see the version that matches the diagnosis measured the same way. Both are
reported; neither is picked over the other on the screen alone.

## 03:57-03:59: the firing diagnostic re-run clean, and latency

gaterate16.py with its patches applied once per process (8800-8805 x 8, T2's dials, 48 tables a field):

| field | unopened spots | table gate on | per-seat gate adds | either | rival 3's decision changed | layer steal_fold fires (T2) |
|---|---|---|---|---|---|---|
| elite | 3,025 | 0.26 | 0.44 | 0.70 | 33 (1.6% of weighted spots) | 43 |
| elite_b | 3,090 | 0.36 | 0.41 | 0.76 | 47 (2.0%) | 44 |
| mirror | 3,486 | 0.38 | 0.34 | 0.72 | 36 (1.4%) | 139 |
| mirror_b | 3,277 | 0.39 | 0.35 | 0.74 | 52 (2.2%) | 137 |
| elite_night | 3,306 | 0.23 | 0.44 | 0.67 | 41 (1.9%) | 49 |
| night | 3,635 | 0.15 | 0.57 | 0.72 | 37 (1.4%) | 71 |
| realistic | 3,900 | 0.11 | 0.52 | 0.62 | 30 (1.2%) | 71 |

The shares match the first run; the rule's outcome (T2) stands. About one unopened decision in 90 changes, always a
raise that becomes a fold or a check: under one a table.

**Latency** (`tools/latency.py --hand-end --reps 3 --tables 20`, per-call minimum, code 1b875ec, load 12-13; T2 as
`--dials` on top of SHIP_DIALS):

| field | bot | act mean / p99 / max µs | hand end mean / p99 / max µs | first act mean / max µs |
|---|---|---|---|---|
| realistic | F | 54.7 / 102.4 / 143.5 | 62.0 / 137.4 / 178.4 | 106.7 / 138.8 |
| realistic | T2 | 56.2 / 107.3 / 198.8 | 61.9 / 142.0 / 210.6 | 108.4 / 132.1 |
| elite | F | 58.0 / 102.7 / 124.8 | 66.2 / 130.2 / 261.1 | 102.5 / 121.7 |
| elite | T2 | 59.6 / 108.6 / 131.8 | 66.5 / 128.9 / 161.2 | 111.3 / 131.8 |

p99 under 200 µs everywhere (act 107-109, hand end 129-142). The gate costs about 1.5 µs a decision on average (a
strong_table read and, preflop, a list of eight flags); the hand end is unchanged within noise.

## 03:59-04:09: T3's elite stage (`{"r3.read_trust": 1e9, "exploit.read_trust": 1e9}`, the table gate alone)

| cell | F | T3 | T3 - F | | ungated `prior` arm (the split) | T2 |
|---|---|---|---|---|---|---|
| elite | 4.865 | 4.855 | -0.010 ± 0.055 | level | +0.056 ± 0.090 | +0.023 ± 0.042 |
| elite_night | 5.422 | 5.427 | +0.005 ± 0.045 | level | (not run) | -0.003 ± 0.045 |
| mirror | 4.498 | 4.584 | **+0.087 ± 0.058** | UP | +0.147 ± 0.091 | +0.026 ± 0.051 |
| elite_b | 4.638 | 4.644 | +0.006 ± 0.054 | level | +0.136 ± 0.088 | +0.011 ± 0.049 |
| mirror_b | 4.466 | 4.552 | **+0.086 ± 0.060** | UP | +0.210 ± 0.093 | +0.070 ± 0.049 |

Gated, the priors keep about half of the ungated arm's gain on the two mirrors and none of it on elite_b: the table
gate is open at a quarter to two fifths of the spots, mostly late in a table (its own prior keeps it shut early). Its
full table follows.
