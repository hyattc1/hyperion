# S20 H1: a solved heads-up preflop for strong tables (running log)

Branch climb/s20-h1, from main f028f50 (batch 7 is F: S7's heads-up specialist routes `pre_hu`, `post_hu_bet`,
`post_hu_chk` to the specialist behind its looseness gate). The three-handed work (S20, R5, R6) and its method are in
docs/drills/climb/s20-log.md on climb/s20-three and climb/s20-r6 (R6 accepted on H32, in batch 8). Task (coordinator,
2026-11-04): heads-up preflop solved per seat with the same method (a realization fit from our own postflop, a richer
tree, a per-seat solve), for strong tables, coexisting with S7's decisions. This session is the measuring half only
(the machine stops for a hardware change at 11:30 ET): diagnosis on fresh diagnostic seeds 14000-14999, the heads-up
realization fit by SPR, where F loses heads-up at strong tables by line. No screen, held-out or judge seed is used.

## Runs (appended as each finishes)

- 09:23 Recordings of F (batch 7) with `goal/s20/d6.py` (d3.py's recorder: every hand that starts with two or three
  alive, every decision, every seat's hole class, the deltas, and per decision whether the specialist made it),
  snapshot worktree at f028f50, workers 3, nice 5: elite, mirror, elite_b, mirror_b on seeds 14000-14299; exploit_hu,
  exploit2_hu, exploit3_hu, adapt_hu (rules hu.json) on 14300-14399; night on 14400-14599; elite_night on 14600-14799.
