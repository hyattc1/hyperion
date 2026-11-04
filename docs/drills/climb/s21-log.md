# S21: O3 behind the strong-table read (running log)

Branch climb/s21-o3s, from main f3c7925 (528d009 + the goal log's S21 entry). Brief (coordinator, 2026-11-03): O3
(S16b's open-answer read: `r3.oa_read`, `exploit.open_read`, both capped, four or more alive) was rejected on H24
(44000-44399): every strong cell up (elite +0.091, elite_night +0.067, mirror +0.087, elite_b +0.079, mirror_b
+0.061, each about ± 0.04), but realistic -0.044 ± 0.028 and fast_schedule (realistic field) -0.053 ± 0.034 DOWN.
S20's `short_strong` showed the shape that keeps a strong-table gain off the ordinary room: open its route only while
the composite's strong-table read (`CompositeCore.strong_table()`) is open. S21 puts O3 behind the same read: a
composite dial `oa_strong` (off by default) under which both halves of O3 act only while `strong_table()` is true.
Survey first (diagnostic seeds 11200-11399), then a screen (10000-10199, `--aim strong`, every stage, runout term).

## Log

- 22:20 Worktree goal/wt_s21 at f3c7925. Where O3 acts: rival 3's core in an unopened pot with no limper, deeper than
  10 bb, four or more with chips (core3.py, `oa_read`); the layer's steal_min_fold when F is first in and four or more
  were dealt in (exploit.py, `open_read`). Under SHIP_DIALS the strong read (`strong_rr` 0.2, prior 0.15 with weight 10)
  is closed at a table's start and opens only once enough of F's first-in raises are re-raised; while it is open,
  `pre_open_10` (10-20 bb unopened) goes to elite1x, so there only the layer's half of O3 can act. Rival 3's half acts
  in `pre_open_40` and `pre_open_20` (the base's sections) whatever the read.
- 22:30 The gate (cadc5cf): `oa_strong` in ComposeConfig (off by default). Before each preflop decision the composite
  sets rival 3's core's `oa_on` (a new attribute, True by default, read in the open-answer clause only) and the layer's
  `open_fold` (the core's `oa_fold`, or None) from `strong_table()`. It keeps the strong read's counts on (`_rr_on`)
  if no strong route does. The core counts the answers all table long whatever the gate, so the read is warm when it
  opens. Off, nothing reads it. Tests (tests/test_s21_oa_strong.py): off by default and off = O3; the gate follows the
  read decision by decision; read never open (`strong_rr` 1.01 on both sides) = F, still counting; read always open
  (`strong_rr` 0) = O3; as shipped, a test table whose read stays under 0.2 plays as F where O3 differs, one whose
  read opens with four or more alive differs from F. A scan of 16 test tables (strong field): O3 differs from F on 13,
  the gated read on 4 of them; on two tables whose read ended at 0.24-0.26 it opened only after fewer than four
  were left, where O3 does not act.
- Candidate (docs/drills/climb/s21-candidate.json): O3's six dials + `oa_strong` true.
- 22:40 **Survey** (F as shipped, Hero's seat only, diagnostic seeds 11200-11399 x 8 rotations; goal/s21/survey_oa.py):
  at the decisions where O3 would act (preflop, plain hold'em, four or more with chips, F first in: every earlier
  action a fold), the share with `strong_table()` open:

  | field | decisions | read open | open, over 10 bb | tables where it ever opens | read median [p10, p90] | open by section 40 / 20 / 10 / short |
  |---|---|---|---|---|---|---|
  | realistic | 83,993 | 0.081 | 0.081 | 0.34 | 0.125 [0.074, 0.192] | 0.09 / 0.06 / 0.09 / 0.08 |
  | fast_schedule (realistic) | 60,303 | 0.111 | 0.102 | 0.35 | 0.136 [0.083, 0.206] | 0.10 / 0.09 / 0.12 / 0.17 |
  | night | 85,514 | 0.152 | 0.147 | 0.44 | 0.136 [0.079, 0.219] | 0.14 / 0.13 / 0.21 / 0.24 |
  | night_hard | 89,866 | 0.167 | 0.155 | 0.51 | 0.139 [0.088, 0.219] | 0.12 / 0.14 / 0.29 / 0.34 |
  | top | 102,181 | 0.188 | 0.170 | 0.54 | 0.146 [0.088, 0.224] | 0.11 / 0.17 / 0.31 / 0.36 |
  | elite | 93,587 | 0.250 | 0.233 | 0.62 | 0.150 [0.100, 0.237] | 0.16 / 0.25 / 0.42 / 0.44 |
  | mirror | 93,865 | 0.285 | 0.266 | 0.66 | 0.156 [0.100, 0.250] | 0.19 / 0.28 / 0.46 / 0.47 |
  | elite_b | 93,625 | 0.313 | 0.293 | 0.70 | 0.159 [0.107, 0.250] | 0.20 / 0.33 / 0.51 / 0.54 |
  | mirror_b | 96,057 | 0.317 | 0.297 | 0.69 | 0.162 [0.107, 0.250] | 0.21 / 0.33 / 0.48 / 0.51 |

  The read is rarely open in the realistic room (8% of O3's decisions there, 11% on fast_schedule), so the gate can
  separate it; it is 3-4 times as often open at the strong tables. But even there it is closed at about 70% of O3's
  decisions: most of them are deep (`pre_open_40`) and early in a table, before enough of F's opens have been
  re-raised to lift the read over 0.2 (prior 0.15 with weight 10). So the gated O3 keeps at best a quarter to a third
  of O3's strong-table decisions; whether the gain lives in them is what the screen tells. Not a reason to stop:
  screen as briefed.
- 22:42 **Identity** (goal/s21/idchk_s21.sh, idchk26.sh's command from this worktree at 74511af: F, confirm and guards,
  10000-10039): **14 of 14 chunks identical** to goal/idchk26/post (each chunk's samples). SHIP_DIALS unchanged.
- 22:43 Screen of G (the gated O3, goal/s21/cand_G.json = docs/drills/climb/s21-candidate.json) started: base F
  (`{"dials": {}}`), 10000-10199, `--aim strong --runout-term`, stages confirm, guards, elite, exploit, aware,
  variants, 2 workers, nice 5 (goal/s21/screen_G.sh, output goal/s21/screen_G.md).
- 23:08 G's screen, first stages (corrected deltas, read from the cache before the tool's report): night +0.011 ±
  0.028, night_hard +0.039 ± 0.033 UP, **realistic -0.020 ± 0.017 DOWN**, top +0.018 ± 0.027, night 10/7/5/... -0.006
  ± 0.051, night 50/25/... -0.036 ± 0.306, night +double +0.010 ± 0.021. The gate halves realistic's loss (H24's O3
  -0.044 ± 0.028 on other seeds) but does not remove it, though the read is open at only 8% of O3's decisions there:
  the loss sits at the third of realistic tables where the read opens. Elite and the rest still running.
- 23:18 **Why the gate leaks** (diagnostic, goal/s21/calib.py, seeds 11400-11499 x 8, F as shipped with the core
  counting the read unused): at F's first-in raises with four or more alive, each answering seat's actual fold
  against O3's capped read (min of oa_fold and F's pooled read) and F's own read, by the strong read open or not:

  | field, read | big blind: actual / F / O3 capped | small blind | not a blind |
  |---|---|---|---|
  | realistic, closed | 0.800 / 0.774 / 0.707 | 0.833 / 0.779 / 0.765 | 0.843 / 0.762 / 0.757 |
  | realistic, open | 0.786 / 0.740 / 0.655 | 0.834 / 0.754 / 0.731 | 0.824 / 0.723 / 0.714 |
  | elite, closed | 0.639 / 0.768 / 0.660 | 0.789 / 0.769 / 0.754 | 0.873 / 0.763 / 0.761 |
  | elite, open | 0.629 / 0.772 / 0.634 | 0.779 / 0.774 / 0.749 | 0.868 / 0.763 / 0.758 |
  | mirror_b, closed | 0.636 / 0.754 / 0.653 | 0.794 / 0.754 / 0.744 | 0.856 / 0.750 / 0.748 |
  | mirror_b, open | 0.617 / 0.762 / 0.628 | 0.770 / 0.765 / 0.741 | 0.857 / 0.758 / 0.751 |

  O3 is a big-blind read: the cap binds there (70-93% of answers) and nearly nowhere else. At strong tables it fixes
  F's error on the big blind (F reads 0.75-0.77, the seat folds 0.62-0.64; O3 0.63-0.66). In the realistic room the
  big blind folds 0.79-0.80 **whether the strong read is open or not**, and O3 reads it 0.66-0.71 (the pooled prior
  0.668 moves slowly). The strong read counts re-raises of our opens; a realistic table that crosses 0.2 has a
  re-raiser in it, but its big blinds still fold like realistic's. Neither alive count (4-7) nor the seat's own
  re-raises of our opens (S20's per-seat gate) separate the two either (realistic big blind 0.76-0.81 in every
  split, strong 0.58-0.68). So the strong-table read is the wrong discriminator for what O3 reads; the separating
  evidence is the big blinds' own answers at this table. (Also seen: F underreads non-blind seats everywhere, 0.76
  against 0.84-0.87; O3's cap keeps that as it is.)
- 23:42 **G's elite stage** (corrected): elite -0.002 ± 0.031, elite_night +0.006 ± 0.025, mirror +0.037 ± 0.038,
  elite_b +0.025 ± 0.039, **mirror_b +0.053 ± 0.034 UP**. On the same screen seeds O3 ungated had mirror +0.105 ±
  0.083 and mirror_b +0.197 ± 0.092 UP (S16b, raw deltas): the gate keeps about a quarter to a third of the gain,
  as the survey's coverage said. With realistic DOWN at the guards, **G is rejected** by the screen's rule whatever
  the later stages say (exploit, aware, variants were running; the aware cells done so far are identical by
  construction).
- 23:45 BB answers to anyone's open (goal/s21/bbopen.py, 11500-11549 x 8, F as shipped): the big blind folds to F's
  opens 0.793 at realistic, 0.718 night, 0.595 elite, 0.596 mirror_b; to others' opens 0.731 / 0.693 / 0.636 / 0.620,
  42-74 of them a table. On the first ten answers a table's big-blind rate is 0.70 [0.60, 0.90] at realistic
  against 0.60 [0.40, 0.80] at elite: within a table the evidence that tells the two rooms' big blinds apart comes
  slowly, from either source.
- 23:47 Offline, from the calibration rows (O3's read shifted by (mu' - 0.668) x 20 / (n + 20), n this table's
  big-blind answers): with the big blind's prior at the ordinary room's 0.799 (S16b's survey, realistic), O3's capped
  read where the gate is open is 0.712 at realistic (G: 0.655; F 0.740; actual 0.786) and 0.70-0.71 at elite and
  mirror_b (G: 0.63; F 0.76-0.77; actual 0.62-0.63). It cuts the realistic error G adds by about two thirds and
  about half of G's correction at strong tables.
- 23:48 **Variant 1, G1 = G + `r3.oa_mu_bb` 0.799** (one value, from S16b's survey, fixed before any screen). Why:
  behind the gate the realistic loss comes from the prior, not from evidence: the realistic tables that open the read
  do so early (6.7 big-blind answers at the gated decisions against 14.7 where it is closed), so the read there is
  mostly the pooled prior 0.668, a strong-field number (strong fields 0.602, guard fields 0.718, realistic 0.799).
  With the ordinary room's big blind as the prior the capped read starts at F's (the cap) and lowers the big blind's
  fold only as this table's own big blinds show it. The risk: it also halves what G keeps at strong tables (mirror_b
  was UP by 0.019). G's screen is stopped here (its decisive stages are in) so G1 can use the 2 workers; F's cells
  are cached and shared (the same code, a dials-only change).
- 23:59 G1's guards (corrected): night -0.001 ± 0.020, night_hard +0.045 ± 0.030 UP, **realistic -0.011 ± 0.010
  DOWN** (G -0.020 ± 0.017), top +0.007 ± 0.023, night 10/7/5/... -0.018 ± 0.035. The prior halves the realistic loss
  again but does not remove it: at realistic F already reads the big blind a little under what it folds (0.774
  against 0.800), so any read that can only lower it (the cap) loses there, and the minimum of two noisy reads is
  biased low even when both are centred. G1 is rejected at the guards too; its elite stage is next.
- 00:12 G1's elite stage (corrected): elite +0.003 ± 0.025, elite_night +0.006 ± 0.022, **mirror +0.035 ± 0.032 UP**,
  elite_b +0.008 ± 0.030, **mirror_b +0.030 ± 0.029 UP** (G: -0.002, +0.006, +0.037, +0.025, +0.053 UP). The prior
  cost G little at strong tables and halved its realistic loss: G1 is a near miss (realistic down by 0.001 at the
  interval's edge). Offline the gated read is about the same number in both rooms where it is open (0.71 at
  realistic, 0.70 at elite), so G1 is in effect "while the table reads strong, read the big blind's fold about 0.06
  lower": the gate does all the separating, and its leak (the realistic tables that open it) is the loss. G1's
  later stages (exploit, aware, variants) running; it is the candidate (docs/drills/climb/s21-candidate.json now
  holds G1; G was the six O3 dials + `oa_strong`).
- No second variant. The ones the data leaves are a stricter gate (a second `strong_rr` for this read, a tuned
  number on our own fields: the survey's realistic p90 is 0.19, the strong fields' 0.24-0.25) or the read without the
  gate (more realistic decisions at the same bias). Neither is principled enough to spend a screen on.
- 00:44 Suite (`pytest -q -m "not timing"`, at 74511af, load 9-10): 1,406 passed, 2 skipped, 7 failed, all
  wall-clock or replay-under-load: three drill checkpoints (2-3 timeouts, 12 ms max latency; swap_holdem-a fails the
  same way on main at 88d456c under this load), test_gate's sim table, S16's replay, rival 2's fixed sampler, the
  model-mode replay. Each re-run alone: all 7 pass (the drill three on a second try). No code changed since.
- 00:44 G1's exploit and aware stages (corrected): exploit -0.034 ± 0.072, exploit2 +0.011 ± 0.041, exploit3 +0.016 ±
  0.043 level; every heads-up and three-handed exploit cell and every aware cell identical (0 ± 0). Variants
  running.
- 02:20 **G1's full screen: REJECT** (goal/s21/screen_G1.md, code 22d411f4b2, 151.8 min; corrected deltas, 200
  seeds; 0 timeouts and 0 errors in every cell for both; the p99 column reads 400-4,100 µs for base and candidate
  alike, the box at load 9-10):

  | stage | cell | cand - base | |
  |---|---|---|---|
  | confirm | night | -0.001 ± 0.020 | level |
  | guards | night_hard | +0.045 ± 0.030 | UP |
  | | realistic | -0.011 ± 0.010 | **DOWN** (raw -0.007 ± 0.015) |
  | | top | +0.007 ± 0.023 | level |
  | | night @10/7/5/4/3/2/1/0 | -0.018 ± 0.035 | level |
  | | night @50/25/12/6/3/2/1/1 | -0.062 ± 0.230 | level |
  | | night +double | +0.001 ± 0.014 | level |
  | elite | elite | +0.003 ± 0.025 | level |
  | | elite_night | +0.006 ± 0.022 | level |
  | | mirror | +0.035 ± 0.032 | UP |
  | | elite_b | +0.008 ± 0.030 | level |
  | | mirror_b | +0.030 ± 0.029 | UP |
  | exploit | exploit / exploit2 / exploit3 / adapt (8-max) | -0.034 ± 0.072 / +0.011 ± 0.041 / +0.016 ± 0.043 / -0.024 ± 0.044 | level |
  | | the eight heads-up and three-handed cells | 0 ± 0 | identical |
  | variants | top_heavy | -0.122 ± 0.139 | level |
  | | antes_from_level_3 / fast_schedule | -0.000 ± 0.011 / -0.003 ± 0.010 | level |
  | | the other 24 | 0 ± 0 | identical |
  | aware | all 5 | 0 ± 0 | identical |

  Weighted: W +0.0024 ± 0.0062 (lower bound -0.0038); W-min +0.0019 ± 0.0087 (lower bound -0.0068); cap holds.
  Against O3 on H24 (other seeds): realistic -0.044 -> -0.011, fast_schedule -0.053 -> -0.003, strong cells
  +0.06-0.09 -> +0.00-0.04. One oddity: exploit's raw delta is -0.122 ± 0.093 DOWN with a paired runout term of
  -0.088 ± 0.055 (the corrected delta level); a paired term beyond noise in one cell of about 60.
- **G's partial screen** (confirm, guards, elite done; stopped at 23:45; goal/s21/screen, key de8023b98718): night
  +0.011 ± 0.028; night_hard +0.039 ± 0.033 UP, **realistic -0.020 ± 0.017 DOWN**, top +0.018 ± 0.027, night
  10/7/5/... -0.006 ± 0.051, 50/25/... -0.036 ± 0.306, +double +0.010 ± 0.021; elite -0.002 ± 0.031, elite_night
  +0.006 ± 0.025, mirror +0.037 ± 0.038, elite_b +0.025 ± 0.039, mirror_b +0.053 ± 0.034 UP; the five aware cells
  identical. REJECT at the guards.

## Summary

The composite dial `oa_strong` (off by default; F identical, 14 of 14 chunks) puts O3's open-answer read behind
`strong_table()`. The read is open at 8% of O3's decisions in the realistic room and 25-32% at strong tables, so the
gate separates the rooms by a factor of 3-4 but keeps only a third of O3's reach where it pays. G (O3 + the gate):
realistic -0.020 DOWN, mirror_b +0.053 UP. G1 (+ the ordinary room's big-blind prior 0.799): realistic -0.011 ± 0.010
DOWN, mirror and mirror_b UP, everything else level or identical; rejected by a hair. Why it does not go away: O3 is
a big-blind read (the cap binds there and almost nowhere else), realistic's big blinds fold 0.79-0.80 to our opens
whether the table reads strong or not, and F's read (0.77) is already under that, so a read that can only lower it
loses wherever it opens in that room. The strong read measures re-raises, not big-blind folds. The evidence that
separates the rooms is the big blinds' own answers, and a table gives about ten of them to our opens (42-74 to
anyone's). Next, if O3 is pursued: a big-blind read that also counts answers to other seats' opens, or a gate on
the table's own big-blind answers; not another threshold on the re-raise read.

# O5: the big blind's read from everyone's opens (branch climb/s21-o5 from dcf376c)

Brief (coordinator, 02:25): take the summary's suggestion forward. Per seat, as the big blind, folds / chances facing a
first-in raise by any seat, so the evidence arrives several times faster than from F's opens alone; the estimator
chosen offline by Brier score against the big blinds' answers to F's opens on the nine fields before any screen; fed
where O3's read went (rival 3's steal price and open clauses, the layer's open_fold) for the big blind only; a cap or
the strong gate only if the offline numbers want one. Diagnostic seeds 12000-12999.

- 02:30 Survey (goal/s21o5/o5_survey.py; F as shipped, rival 3's core counting O3's read unused): per table every
  big-blind answer to a first-in raise by anyone (not all-in; the big blind's first action unless a re-raise came
  first), and at each of F's first-in raises every seat's answer with what F's reads said then (rival 3's
  `_fold_prob`, the layer's `fold_rate`, O3's `oa_fold`). Nine fields, 12000-12099 to choose (7,060 tables, 124,936
  big-blind answers to F's opens with four or more alive), 12100-12199 to check.
- **The opener's position matters, and so does who opens** (12000-12049; big blind's fold by opener class: the small
  blind opened / the button / the cutoff / earlier):

  | field | to F's opens | to others' opens |
  |---|---|---|
  | realistic | 0.78 / 0.82 / 0.80 / 0.80 | 0.64 / 0.73 / 0.78 / 0.78 |
  | night | 0.66 / 0.71 / 0.75 / 0.76 | 0.61 / 0.66 / 0.72 / 0.74 |
  | elite | 0.55 / 0.59 / 0.67 / 0.69 | 0.59 / 0.59 / 0.64 / 0.68 |
  | mirror | 0.46 / 0.55 / 0.61 / 0.65 | 0.52 / 0.57 / 0.63 / 0.64 |

  Later opens are defended more (0.08-0.20 from the earliest class to the small blind's). Realistic's big blinds fold
  more to F than to the room's other openers, most at the small blind and button opens; at strong tables the two are
  about equal. So others' opens are evidence of a seat's level but not the same quantity as its answer to F.
- **Estimators** (Brier against the big blind's answers to F's opens, four or more alive, fit seeds 12000-12099;
  per field Brier and the mean bias, predicted - actual; `goal/s21o5/grid_fit.md` has all 40):

  | estimator | pooled | realistic | night | night_hard | top | elite | elite_night | mirror | elite_b | mirror_b |
  |---|---|---|---|---|---|---|---|---|---|---|
  | F's read (rival 3's `_fold_prob`) | 0.2195 | 0.1563 (-0.028) | 0.2008 (+0.079) | 0.2340 (+0.127) | 0.2001 (+0.061) | 0.2449 (+0.125) | 0.2209 (+0.095) | 0.2629 (+0.144) | 0.2583 (+0.142) | 0.2461 (+0.118) |
  | the layer's `fold_rate` | 0.2184 | 0.1578 (-0.037) | 0.1979 (+0.055) | 0.2299 (+0.106) | 0.2022 (+0.049) | 0.2439 (+0.118) | 0.2179 (+0.080) | 0.2627 (+0.144) | 0.2573 (+0.136) | 0.2458 (+0.116) |
  | O3's `oa_fold` | 0.2113 | 0.1632 (-0.077) | 0.1965 (-0.023) | 0.2198 (+0.009) | 0.2015 (-0.028) | 0.2298 (+0.018) | 0.2139 (-0.001) | 0.2422 (+0.039) | 0.2382 (+0.034) | 0.2330 (+0.018) |
  | O3 capped (as screened) | 0.2114 | 0.1663 (-0.096) | 0.1963 (-0.032) | 0.2192 (+0.002) | 0.2019 (-0.038) | 0.2292 (+0.010) | 0.2134 (-0.011) | 0.2416 (+0.031) | 0.2375 (+0.027) | 0.2323 (+0.010) |
  | seat's answers to F's opens, pooled prior 0.688, k 10 | 0.2099 | 0.1631 (-0.089) | 0.1930 (-0.026) | 0.2166 (+0.019) | 0.1987 (-0.022) | 0.2294 (+0.038) | 0.2118 (+0.009) | 0.2432 (+0.068) | 0.2388 (+0.060) | 0.2333 (+0.042) |
  | seat's answers to all opens, pooled prior 0.688, k 10 | 0.2070 | 0.1578 (-0.069) | 0.1887 (-0.013) | 0.2117 (+0.023) | 0.1940 (-0.015) | 0.2291 (+0.026) | 0.2074 (+0.013) | 0.2444 (+0.043) | 0.2389 (+0.046) | 0.2347 (+0.020) |
  | pooled class rates + seat's excess over them (all opens), k 10 (best pooled) | 0.2067 | 0.1588 (-0.072) | 0.1882 (-0.013) | 0.2119 (+0.025) | 0.1939 (-0.013) | 0.2283 (+0.029) | 0.2066 (+0.014) | 0.2431 (+0.049) | 0.2379 (+0.049) | 0.2339 (+0.024) |
  | **F's read as the prior + seat's answers to all opens, k 10** | 0.2118 | **0.1550 (-0.022)** | 0.1919 (+0.053) | 0.2192 (+0.083) | 0.1960 (+0.033) | 0.2371 (+0.073) | 0.2114 (+0.062) | 0.2541 (+0.079) | 0.2491 (+0.087) | 0.2413 (+0.058) |
  | ... the same, class-adjusted answers | 0.2120 | 0.1548 (-0.020) | 0.1919 (+0.056) | 0.2199 (+0.087) | 0.1963 (+0.037) | 0.2373 (+0.077) | 0.2114 (+0.066) | 0.2544 (+0.086) | 0.2494 (+0.092) | 0.2414 (+0.064) |
  | ... the same, class-adjusted, F's answers weighted 2 | 0.2117 | 0.1556 (-0.021) | 0.1913 (+0.048) | 0.2185 (+0.078) | 0.1964 (+0.033) | 0.2369 (+0.071) | 0.2106 (+0.059) | 0.2543 (+0.079) | 0.2490 (+0.086) | 0.2417 (+0.059) |
  | ... class-adjusted, k 5 | 0.2126 | 0.1563 (-0.017) | 0.1916 (+0.047) | 0.2183 (+0.073) | 0.1978 (+0.029) | 0.2384 (+0.060) | 0.2112 (+0.054) | 0.2558 (+0.063) | 0.2501 (+0.073) | 0.2439 (+0.044) |
  | ... class-adjusted, k 20 | 0.2131 | 0.1546 (-0.023) | 0.1937 (+0.063) | 0.2231 (+0.100) | 0.1964 (+0.045) | 0.2383 (+0.094) | 0.2133 (+0.076) | 0.2554 (+0.106) | 0.2507 (+0.109) | 0.2412 (+0.082) |
  | ... the same, capped by F's read | 0.2109 | 0.1568 (-0.047) | 0.1910 (+0.041) | 0.2186 (+0.076) | 0.1950 (+0.021) | 0.2354 (+0.069) | 0.2101 (+0.052) | 0.2523 (+0.079) | 0.2470 (+0.083) | 0.2394 (+0.056) |
  | ... answers to F's opens only | 0.2149 | 0.1558 (-0.028) | 0.1945 (+0.060) | 0.2251 (+0.103) | 0.1976 (+0.048) | 0.2404 (+0.106) | 0.2148 (+0.077) | 0.2585 (+0.124) | 0.2537 (+0.123) | 0.2437 (+0.100) |

  Every estimator that starts from a pooled prior (ours: 0.69, or the class rates 0.60-0.71)
  beats F at the strong tables and loses to it in the realistic room (bias -0.07 to -0.10: the prior sits far under
  realistic's 0.80 and the answers move it slowly), the shape that cost O3 and G1 their screens. **Only the
  estimators that start from F's own read and move with the seat's answers beat F's read on all nine fields,
  realistic included** (k 5 ties F at realistic; k 20 trades the strong fields for realistic); k 10, and class
  adjustment and weighting F's answers change the third decimal at most, so the simplest form is kept. With four to seven times the answers, the seat's own evidence carries it from F's
  read toward the truth: at strong tables it takes half of F's error off (elite +0.125 -> +0.073), in the realistic
  room a little (-0.028 -> -0.022).
- **No cap.** Capped by F's read the estimator is better than uncapped at the eight fields where F overreads the big
  blind, and worse than F's own read in the realistic room (0.1568 against 0.1563): the cap keeps the answers that
  lower the read and drops the ones that raise it, so where F already reads the big blind low it adds only the
  noise's downward half (the minimum of two centred reads is biased low). Uncapped it is better than F everywhere.
- **No strong gate.** The gate's job was to keep the read off tables where it misreads; this read beats F's at every
  field, and the gate closes it at 70% of decisions at strong tables (S21's survey).
- **Other positions off.** O3's read at the small blind and at seats that are not a blind, capped as O3 ships it, is
  worse than F's read at both on every field (small blind pooled 0.1528 against 0.1519; not a blind 0.1276 against
  0.1271), so O5 is the big blind only (`r3.oa_bb_only`, `exploit.open_bb_only`). Seen in passing: uncapped, O3's
  read of the seats that are not a blind beats F's on all nine fields (0.1146 against 0.1271; F underreads their folds
  by 0.08-0.11 everywhere), a separate lead for later; not in O5.
- **Chosen before any screen:** big blind's fold = (its folds as the big blind to any first-in raise this table +
  `_fold_prob` x 10) / (its answers + 10), clamped to [0.05, 0.97]; the layer reads the same number for the big blind
  (from the core); its prior there is rival 3's read rather than the layer's own (the layer's prior gives 0.2116
  pooled, the same family; one function serves both). Four or more alive, plain hold'em, no straddle, as O3.
- 02:50 Code (a9262d5): `bb_scan` and per-seat `bbn` / `bbf` in rival 3's core, counted at hand end; `oa_fold(s, 2)`
  reads them under `r3.bb_read` (prior weight `r3.bb_k` 10); `r3.oa_bb_only` keeps every other seat on its
  fold-to-any-raise read in the open clause; `exploit.open_bb_only` the same in the layer. All off by default.
  CONTRACTS.md regenerated (five rows). Tests: tests/test_s21_o5.py (the scan, the estimator's start and move, the
  layer reading the big blind only, counting and exact replay, twist and straddle tables as F, SHIP_DIALS off).
- 02:55 **Check seeds** (12100-12199, 7,200 tables, 127,960 answers; bases and the choice from the fit seeds): the
  chosen read beats F's on all nine fields again (realistic 0.1558 (-0.018) against 0.1565 (-0.022); night 0.1874
  against 0.1974; night_hard 0.2143 / 0.2269; top 0.1965 / 0.2017; elite 0.2404 / 0.2489; elite_night 0.2160 / 0.2264;
  mirror 0.2520 / 0.2616; elite_b 0.2449 / 0.2547; mirror_b 0.2380 / 0.2444), and the layer's own read on all nine
  (realistic 0.1582). Capped, realistic 0.1568 is again worse than F's; the pooled-prior estimator again loses
  realistic (0.1604 (-0.070)). Other positions as on the fit seeds (O3 capped worse than F's read at both).
  goal/s21o5/grid_val.md.
- 03:05 **Identity** (goal/s21o5/idchk.sh: idchk26's command from this worktree at a9262d5 and later docs): **14 of 14
  chunks identical** to goal/idchk26/post. SHIP_DIALS unchanged.
- 03:06 Candidate O5 (docs/drills/climb/s21-o5-candidate.json): `r3.oa_read`, `r3.bb_read`, `r3.bb_k` 10,
  `r3.oa_bb_only`, `r3.oa_min_alive` 4, `exploit.open_read`, `exploit.open_bb_only`, `exploit.open_min_alive` 4; no
  cap, no gate. Screen started: base F, 10000-10199, `--aim strong --runout-term`, every stage, 2 workers, nice 5
  (goal/s21o5/screen_O5.sh, output goal/s21o5/screen_O5.md). F's 448 chunks are pinned from S21's screen (same
  seeds, stages and runout-term version; copied to this code's F key 0a1f38fe5bf0): every O5 path is behind a dial
  F leaves off, the identity check is 14 of 14, and its seven 25-seed chunks equal the S21 screen's F chunks sample
  for sample. Only the candidate's cells run.
- 03:43 Suite (`pytest -q -m "not timing"`, at 614d6a2, load 13-16): 1,406 passed, 4 skipped, 11 failed, all
  wall-clock or replay-under-load (drill checkpoints, kit d, the gate's fake kits, two night-of latency tests, S12's
  and S16's replays, S21's gate test, rival 2's sampler, the model-mode replay). Re-run alone: 8 pass; the drill
  checkpoints (2 of 3) and `test_model_mode_replays_a_table_exactly` still fail at load 16, and that one fails the
  same way on main (c38b7db: one of two runs) — it seats Hero, not the composite. The O5, O3 and S21 tests pass.
- 04:20 O5's screen so far (corrected): night +0.003 ± 0.046; night_hard +0.090 ± 0.052 UP, realistic -0.004 ±
  0.034, top +0.052 ± 0.055, night 10/7/5/... +0.059 ± 0.079, 50/25/... +0.320 ± 0.500, +double +0.030 ± 0.041; elite
  +0.004 ± 0.048, elite_night +0.005 ± 0.050, mirror +0.045 ± 0.057, **elite_b +0.067 ± 0.053 UP, mirror_b +0.062 ±
  0.047 UP**; exploit +0.011 ± 0.090, exploit2 -0.046 ± 0.098, exploit3 +0.076 ± 0.084, heads-up and three-handed
  identical; aware identical. The intervals are about twice G1's: O5 moves more decisions (no cap, no gate). The
  realistic room is level for the first time in this line of work. Adapt cells and variants running.
- 05:55 **O5's screen: ACCEPT** (goal/s21o5/screen_O5.md, 10000-10199, `--aim strong`, every stage, runout term;
  corrected deltas; 0 timeouts and 0 errors in every cell):

  | stage | cell | cand - base | |
  |---|---|---|---|
  | confirm | night | +0.003 ± 0.046 | level |
  | guards | night_hard | +0.090 ± 0.052 | UP |
  | | realistic | -0.004 ± 0.034 | level |
  | | top | +0.052 ± 0.055 | level |
  | | night @10/7/5/4/3/2/1/0 | +0.059 ± 0.079 | level |
  | | night @50/25/12/6/3/2/1/1 | +0.320 ± 0.500 | level |
  | | night +double | +0.030 ± 0.041 | level |
  | elite | elite | +0.004 ± 0.048 | level |
  | | elite_night | +0.005 ± 0.050 | level |
  | | mirror | +0.045 ± 0.057 | level |
  | | elite_b | +0.067 ± 0.053 | UP |
  | | mirror_b | +0.062 ± 0.047 | UP |
  | exploit | exploit / exploit2 / exploit3 / adapt (8-max) | +0.011 ± 0.090 / -0.046 ± 0.098 / +0.076 ± 0.084 / -0.003 ± 0.079 | level |
  | | the eight heads-up and three-handed cells | 0 ± 0 | identical |
  | variants | top_heavy | +0.052 ± 0.468 | level |
  | | antes_from_level_3 / fast_schedule | -0.023 ± 0.036 / -0.005 ± 0.032 | level |
  | | the other 24 | 0 ± 0 | identical |
  | aware | all 5 | 0 ± 0 | identical |

  Weighted: **W +0.0114 ± 0.0129 (lower bound -0.0015); W-min +0.0130 ± 0.0185 (lower bound -0.0055)**; cap holds;
  families: ordinary room +0.031, strong tables +0.034, adapters +0.002, twist-blind -0.0005, twist-aware 0. Against
  G1 (the same seeds): realistic -0.011 DOWN -> -0.004 level, night_hard +0.045 -> +0.090, top +0.007 -> +0.052,
  mirror_b +0.030 -> +0.062, elite_b +0.008 -> +0.067; the intervals are 1.5-2 times wider (more decisions move).
  Runout term: the paired term is inside noise everywhere but night (+0.042 ± 0.036, the raw delta +0.045 and the
  corrected +0.003). exploit3's raw delta is +0.145 UP, corrected +0.076 level.
- Latency (tools/latency.py, 2,000 calls, F and O5 alternated twice, load 16): act p50 58.6-59.5 µs for F and
  61.6-62.6 for O5; the p99 at this load is the box's (F 4,074-4,102 µs, O5 429-4,180), not a measurement. O5 adds
  a per-hand scan at hand end and one fold read per big blind at the steal price.
- No variant run (the screen passed). O5 is the candidate for a held-out set.

# O6: the seats that are not a blind (branch climb/s21-o6 from 2de5070)

Brief (coordinator, 06:00): O5's lead. F underreads how often the seats that are not a blind fold to its opens
(0.08-0.11 on every field) and O3's uncapped read beat F's there on all nine fields. Offline first, by the same Brier
method, for those seats and separately the small blind: F's read, O3 uncapped, and the O5 family (F's read as the
prior + the seat's answers to all opens from that position); keep only one that beats F's read on every field on both
seed sets, realistic included, or stop. Check how much F's open decisions depend on these seats' reads. Diagnostic
seeds 12200-12999.

- 06:00 Survey (goal/s21o6/o6_survey.py; F as shipped): every seat's answer to each hand's first-in raise by anyone
  (its first action after the open until a re-raise; its position and the seats still to act behind it), and at F's
  first-in raises every seat's answer with F's reads then. Fit 12200-12299, check 12600-12699, nine fields.
- 06:40 **Who answers what** (fit seeds, fold to anyone's open): a seat that is not a blind folds 0.854-0.876
  whatever the number of seats left behind it (2: 0.854, 3: 0.873, 4-5+: 0.875), and the same to F's opens as to
  others' (0.86-0.88 against 0.85-0.88); the small blind 0.81 (F's 0.81, others' 0.80); the big blind 0.66. Unlike the
  big blind, these seats fold about the same in every room (realistic 0.84 to F's opens, mirror 0.86), so F's
  underread is one systematic error, not a room difference.
- **Estimators** (Brier against the seats' answers to F's first-in raises, four or more alive; fit 12200-12299, check
  12600-12699; "beats F" counts fields where the Brier is under F's read; columns: pooled, beats F, realistic,
  night, elite, mirror_b with the mean bias; goal/s21o6/fit_all.md has every field and estimator):

  | seats that are not a blind | fit pooled | beats F | realistic | night | elite | mirror_b | check pooled | beats F | realistic | elite |
  |---|---|---|---|---|---|---|---|---|---|---|
  | F's read (`_fold_prob`) | 0.1268 | - | 0.1414 (-0.088) | 0.1068 (-0.083) | 0.1286 (-0.118) | 0.1368 (-0.109) | 0.1282 | - | 0.1366 (-0.084) | 0.1270 (-0.112) |
  | the layer's `fold_rate` | 0.1282 | 0/9 | 0.1416 (-0.092) | 0.1106 (-0.108) | 0.1287 (-0.122) | 0.1370 (-0.111) | 0.1297 | 1/9 | 0.1363 | 0.1282 |
  | O3 capped | 0.1273 | 0/9 | 0.1418 (-0.092) | 0.1073 (-0.089) | 0.1290 (-0.121) | 0.1370 (-0.112) | 0.1286 | 0/9 | 0.1371 | 0.1274 |
  | **O3 uncapped (`oa_fold`)** | **0.1129** | **9/9** | 0.1315 (+0.019) | 0.0986 (-0.003) | 0.1102 (-0.010) | 0.1208 (-0.002) | **0.1152** | **9/9** | 0.1277 (+0.017) | 0.1106 (-0.008) |
  | F's read as prior + answers to all opens from this position, k 5 | 0.1217 | 9/9 | 0.1403 (-0.047) | 0.1029 (-0.035) | 0.1213 (-0.058) | 0.1316 (-0.059) | 0.1235 | 9/9 | 0.1353 | 0.1206 |
  | ... k 10 | 0.1219 | 9/9 | 0.1395 (-0.058) | 0.1031 (-0.047) | 0.1219 (-0.072) | 0.1317 (-0.071) | 0.1236 | 9/9 | 0.1346 | 0.1210 |
  | (for reference) pooled rate by seats behind + seat excess, all opens, k 20 | 0.1117 | 9/9 | 0.1309 (+0.014) | 0.0975 (-0.012) | 0.1088 (-0.009) | 0.1194 (-0.002) | 0.1139 | 9/9 | 0.1272 | 0.1091 |

  | small blind | fit pooled | beats F | check pooled | beats F |
  |---|---|---|---|---|
  | F's read | 0.1501 | - | 0.1507 | - |
  | O3 uncapped | 0.1483 | 7/9 (loses top, elite_night) | 0.1491 | 7/9 |
  | F's read as prior + answers from this position, k 10 / 20 | 0.1510 / 0.1501 | 2/9 / 4/9 | 0.1518 / 0.1508 | 2/9 / 4/9 |
  | pooled rate + seat excess, k 20 | 0.1473 | 8/9 (loses top) | 0.1481 | 9/9 |

- **Choice, before any screen: the seats that are not a blind take O3's own read, uncapped**; the small blind stays
  on F's read (no estimator beats F's at the small blind on every field on both seed sets). O3 uncapped and the O5
  family both beat F's read on all nine fields on both sets; O3 uncapped by far (pooled 0.1129 / 0.1152 against
  0.1217-0.1236; biases within ±0.02 on every field, the O5 family's -0.04 to -0.07). The reason is the opposite of the
  big blind's: here F's read is wrong by the same 0.08-0.12 in every room, so a pooled prior near the seats' common
  0.87 (O3's `oa_mu_other` 0.866, from S16b's survey) is right everywhere, while starting from F's read carries its
  bias for many answers. The pooled-rate-plus-excess form on all opens is a hair better (0.1117 / 0.1139) but new
  code; O3's estimator is already built and measured. No cap (the cap is what made O3 0/9 here). No gate.
- **Do F's open decisions depend on these seats?** (goal/s21o6/o6_dep.py, 12800-12849 x 8; O5 plays; at each of its
  preflop decisions first in with four or more alive over 10 bb, rival 3's core is asked again with the non-blind
  seats on O3's uncapped read, and the layer's steal_fold condition is evaluated both ways; "bb" asks instead with
  the big blind on F's read, i.e. what O5's own read moves):

  | field | decisions | a non-blind seat behind (mean seats) | core flips, O6 read | (to raise / from) | layer flips | core flips, O5's big blind | layer flips |
  |---|---|---|---|---|---|---|---|
  | realistic | 19,568 | 0.72 (1.6) | 7.2% | 1,355 / 53 | 1.9% | 2.7% | 4.4% |
  | night | 20,058 | 0.76 (1.8) | 8.6% | 1,695 / 29 | 3.2% | 3.6% | 4.6% |
  | elite | 20,916 | 0.83 (2.3) | 6.8% | 1,399 / 17 | 1.0% | 3.4% | 2.9% |
  | mirror_b | 20,634 | 0.86 (2.5) | 4.5% | 897 / 27 | 0.6% | 3.0% | 2.3% |

  Yes, and more than the big blind's: rival 3's steal price multiplies every seat's fold read behind, these seats
  are behind in 72-86% of F's first-in decisions, and lifting each of 1.6-2.5 reads by about 0.09 moves the product
  past the steal clause's break-even (about 0.48 for a 2.5 bb open) at 4.5-8.6% of decisions, almost all toward
  opening. The layer (steal_min_fold 0.7) rarely reaches its threshold with such seats behind. So O6 is a looser open
  from early and middle position, on reads that are calibrated; whether rival 3's crude call-cost term (0.55 of the
  raise lost when called) prices those extra opens right is what the screen tests.
- 06:55 Code (607a152): `r3.oa_other` (with `r3.oa_bb_only`: the seats that are not a blind take `oa_fold(s, 0)`,
  O3's estimator, in the open clause; the small blind keeps `_fold_prob`) and `exploit.open_other` (the same in the
  layer's steal_min_fold); off by default; CONTRACTS.md regenerated. Tests added to tests/test_s21_o5.py (the layer
  reads the big blind and the non-blind seats but not the small blind; off = O5 exactly; on, it moves play and
  replays; twist and straddle tables as F; SHIP_DIALS off).
- **Identity** (goal/s21o6/idchk.sh from this worktree at 607a152): **14 of 14** identical to goal/idchk26/post; and
  this code's F chunk 10000 equals the S21 screen's cached F sample for sample on all seven cells (the check O5's
  pin used), so F's 448 cached chunks are pinned again (key 02b03d100fcc).
- Candidate O6 (docs/drills/climb/s21-o6-candidate.json) = O5's dials + `r3.oa_other` + `exploit.open_other`.
  Screen started: 10000-10199, every stage, `--aim strong --runout-term`, 2 workers, nice 5 (goal/s21o6/screen_O6.sh,
  output goal/s21o6/screen_O6.md).
- 07:26 **O6's screen: REJECT** (stopped after the elite stage; the confirm, guard and elite verdicts are in;
  corrected deltas, 200 seeds; goal/s21o6/screen, key 72b3dac9c984):

  | cell | O6 - F | | O5 - F (the same seeds) |
  |---|---|---|---|
  | night (confirm) | -0.065 ± 0.064 | **DOWN** | +0.003 ± 0.046 |
  | night_hard | +0.068 ± 0.069 | level | +0.090 UP |
  | realistic | +0.000 ± 0.053 | level | -0.004 |
  | top | +0.019 ± 0.070 | level | +0.052 |
  | night @10/7/5/4/3/2/1/0 | -0.125 ± 0.102 | **DOWN** | +0.059 |
  | night @50/25/12/6/3/2/1/1 | -0.453 ± 0.700 | level | +0.320 |
  | night +double | -0.008 ± 0.052 | level | +0.030 |
  | elite | -0.122 ± 0.067 | **DOWN** | +0.004 |
  | elite_night | -0.131 ± 0.065 | **DOWN** | +0.005 |
  | mirror | -0.061 ± 0.076 | level | +0.045 |

  The non-blind read costs 0.07-0.18 night points on top of O5 at night and at strong tables. The read is right
  (Brier 9/9 on both seed sets) but rival 3's open clause cannot use it: it opens any hand up to the 85th percentile
  whenever pf x pot beats (1 - pf) x 0.55 x the raise, so lifting 1.6-2.5 fold reads by 0.09 each turns 4.5-8.6% of
  first-in decisions into opens, almost all of them loose opens from early and middle position, and the 0.55 call
  cost is far too light for those hands against seats that call and 3-bet well (elite, elite_night down most). F's
  underread of these seats has been holding that clause tight; the two errors cancel. O6 stays off.
- **No variant run.** The only principled one left is the read in the layer alone (its steal_min_fold 0.7 is a pure
  fold-equity steal with margin, where a calibrated read is safe), but it changes under 1% of first-in decisions
  (0.35-0.9% with the member passive) and would be O5 within noise at 200 seeds. A read restricted to the cutoff's
  opens (one non-blind seat behind: 24-36% of the flips) still goes through the same clause. The fix that would let
  F use the calibrated read is in the clause (a call cost that depends on the hand and the seats left to act), a
  separate change to F's open logic, not a variant of O6.
- Suite (`pytest -q -m "not timing"`, at ab4602a, load 12-14): 1,418 passed, 2 skipped, 5 failed (two drill
  checkpoints and the seeded drill pick, two night-of kit round trips, the adapt twin); each passes re-run alone.
