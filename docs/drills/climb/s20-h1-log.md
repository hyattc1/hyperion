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

## Step 1: where F loses heads-up at strong tables

- 09:36 **First line book, elite + mirror** (seeds 14000-14299 each, hands that start heads-up; `goal/s20/h1a.py`,
  bb a hand booked to each decision's spot, ± the 95% interval). S7's specialist made none of F's heads-up decisions
  at these tables (its looseness gate admits exploiter-2-like seats only), so this is batch 7's own heads-up play.

| bot | button (SB) bb a hand | big blind bb a hand |
|---|---|---|
| F | +0.007 ± 0.072 (13,190 hands) | +0.080 ± 0.064 |
| elite1 | +0.160 ± 0.076 | +0.206 ± 0.066 |
| elite2 | +0.051 ± 0.063 | +0.185 ± 0.079 |
| rival2 | -0.048 ± 0.056 | -0.078 ± 0.065 |

| spot | F | elite1 | elite2 |
|---|---|---|---|
| button first in: fold / raise / jam | 11% / 75% (-0.0) / 14% (+0.4): +0.01 | 9% / 58% (+0.2) / 33% (+0.3): +0.16 | 31% / 43% / 26%: +0.05 |
| button facing a jam: fold / call | **3,062 times**, 90% / 10%: -1.48 | 1,153, 91% / 9%: -1.91 | 991, 77% / 23%: -1.03 |
| button facing a 3-bet up to 3.6x: fold / call / 4-bet / jam | 55% / 2% / 15% / 28% (-5.2): -2.69 (260) | 55% / 28% / 2% / 15%: -3.04 (297) | 87% / 10% / - / 2%: -2.59 |
| big blind vs an open of 2.25 bb or less: fold / call / 3-bet / jam | 44% / 26% / 3% / 27% (+1.4): **+0.15** | 33% / 15% / 2% / 51% (+1.4): **+0.43** | 15% / 42% / 3% / 41%: +0.30 |
| big blind vs an open of 2.25-3 bb | 48% / 37% / 4% / 10%: -0.07 | 48% / 22% / 3% / 27%: +0.01 | 36% / 39% / 5% / 20%: +0.05 |
| big blind vs a jam: fold / call | 79% / 21%: -0.28 (3,160) | 83% / 17%: -0.44 | 68% / 32%: -0.39 |

  The same shape as three-handed: F's button min-raises 75% and is re-shoved on nearly three times as often as
  elite1's (3,062 against 1,153), folding 90% of those; elite1 jams a third of its buttons. F's big blind folds 44% to a
  min-raise and re-shoves 27% where elite1 folds 33% and re-shoves 51% (+0.43 a hand against +0.15).
