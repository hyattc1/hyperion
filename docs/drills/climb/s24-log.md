# S24: exploiter 5 wired in; the over-folding it found (running log)

Branch climb/s24-overfold, worktree goal/wt_s24, from main 6138ef0 (batch 8 is F). Scratch goal/s24/. Diagnostics on seeds
18000-18999 only; screen on 10000-10199 with `--aim exploit`, every stage, runout term; identity against goal/idchk39.md. Held-out
seeds 20000-59999, judge seeds 60000+ and 70000+, and the judge bots (out_*, elite5, rival4, rival5, adapt2) are not used. Workers
at most 3, nice 5.

**Where I am / next:** Part 1 (wiring) committed. Part 2: diagnosis next.

## Part 1: exploiter 5 wired in

- Frozen copy `hyperion/sim/field/exploiter5.py` (md5 f4121d39, origin header + archive bytes), archive docs/drills/exploiter5/
  (notebook, brief, arena, bot). `Exploiter5Bot`, registry `exploiter5`; fields exploit5 (six night seats), exploit5_hu,
  exploit5_3; climb_accept's exploit stage gains the three cells, appended after exploit4_3 in the list (each cell's file is named by
  its field, so no earlier cell moves). Weighted score's adapter family: six bots, a sixth each (family weight and range unchanged).
- Clock: the bot reads perf_counter twice in act(), and the branch on it is `pass`, so play does not depend on it: no fixed clock.
  No random import. Two model-mode runs replay exactly (test). At import it does gc.freeze and raises the collector's threshold
  process-wide; the adapter puts the threshold back (here the collector is everyone's). Its env hooks (BOT_DEBUG, BOT_LOG) stay unset.
- Its arena against batch 8, before any fix (its notebook): 8-max 4.68-4.92 vs F 5.85-5.96; three-handed 2.01 vs 2.36; heads-up
  (2/1) 1.47-1.50 vs 1.51-1.54, level. F wins; that is the baseline to keep.
