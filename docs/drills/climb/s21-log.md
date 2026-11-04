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
