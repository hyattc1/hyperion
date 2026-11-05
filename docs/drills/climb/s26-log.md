# S26: a heads-up re-jam read, H1's reach, chips on arrival (running log)

Branch climb/s26, worktree goal/wt_s26, from climb/s25-hu 05dbdef. F here = SHIP_DIALS + goal/b42/cand.json (batch 9 + S24's shove read +
S25). Order from the coordinator: (b) a heads-up re-jam read from the big blind, (c) H1 without the strong read, (a) chips on arrival only if
a clean idea is left. Each priced first with the coin, in ICM points, on separate fit and check seeds. Diagnostic seeds 20000-20999. Judges
(out_reads, elite5, out_cfr, out_press, out_charts, out_o9/o10/o11, rival4, rival5, adapt2, elite6/7) are never run or read here.
Scratch: `goal/s26/`.

## (b) The heads-up re-jam read

### What the recordings already say (S25's rec_*_brief, F = batch 9, seeds 19000-19199; `a26.py scan`, `a26.py cf`)

Every opener over-folds to a heads-up re-jam, in every room, at every depth: f_copy 0.91, elite1 0.91, rival3 0.91, rival2 0.88, rival1 0.87,
elite2 0.80, F 0.81, elite4 0.76 (strong rooms); the ordinary rooms' F 0.88, rival1 0.83, loose_aggro 0.87, tag 0.89, pushfold 0.83, the night
pool 0.77, hero_tight 0.71; montecarlo30 0.00 (22 answers). The equilibrium opener folds 0.55-0.74 (S25's H1 widths). F's big blind against a
non-jam open at 15-22 bb re-jams 24% (elite1 66%, elite2 53%, rival2 35%), at 10-15 bb 56%.

First-order value of re-jamming instead of F's fold or call (the opener answers at the fold rate measured for that bot and depth, calling with
its top hands by rank, against its actual hand; 8-30 bb; milli-points a table-rotation under 10/7/5): strong rooms +82 (5,631 spots), q0 +25, q1
+20, q2 +19, q3 +11, q4 +8; replacing folds +39, calls +44. Night +53, top +46, realistic +5 (montecarlo30's seats -11, the rest +16). So the
prize looks large, four times S25's, and it is a first-order number: it holds the openers' answers fixed as the jam widens. The coin is what
counts.

### The rule (hyperion/compose/bot.py `_hu_rejam`, ComposeConfig.hu_rejam_*; off by default, tests/test_s26_rejam.py)

Plain hold'em (not a straddle), heads-up, our big blind facing the button's first-in raise (not all-in, under 40% of the effective stack), at 10 to 22
bb effective, the members not already raising. Read of the opener's fold: the profiler's `open_fold_to_reraise` (answers to any re-raise this table, shrunk
to prior 0.5 with weight 5, at least 3 answers seen), then our own heads-up re-jams' answers on top with that read counting as 4 of them, so a seat that
starts calling our jams shuts the rule fast. The rule needs the read at 0.70 or more (`hu_rejam_t`). Then the chip gain over folding must be positive:
read x pot + (1 - read) x ((2 eq - 1) x effective + our blind), eq = rival 3's equity table against the top (1 - read) x 0.7 of hands. It overrides the
members (S7, H1, the base) after the exploit layer, once they answer fold or call.

Pre-registered before any coin result: v1 = the values above (t 0.70, any hand the sum allows, 10-22 bb, over folds and calls). Fallbacks, in order, one
fixed rule each, no sweep: (i) if the weakest hands or the realistic room lose, `hu_rejam_cap` 0.66 (no hand outside the top 66%, the widest an elite re-jams
at this depth); (ii) if the rule's overrides of F's calls lose while its overrides of F's folds gain, folds only. If neither pays, the idea stops.
