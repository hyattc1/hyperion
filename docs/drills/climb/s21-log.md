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
