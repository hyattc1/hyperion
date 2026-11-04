# What we would still try

The climb's end deliverable (docs/prompts/goal.md). Updated as ideas are tried; the newest state is last in
docs/drills/goal-log.md. Ranked by the gain we expect at the tables the night is likely to have, best first. Each
line says what it is, why we think it would help, and what it would cost.

## Strength at strong tables

1. **Heads-up solved per seat, like R6.** S20's realization fit and per-seat solve applied to heads-up preflop
   (`pre_hu`). Elite bots still win 1st from three-handed more often than F; R6 took the button three-handed
   (+0.015 to +0.019 at every strong table, H32). About a day: refit, solve, screen, held-out.
2. **A big-blind tree under 25 bb** (fold / jam / 3-bet). The equilibrium defends 80-100% there, and F's re-shove beats
   it; the realization fit has no data on the weak hands that defence relies on. Half a day.
3. **A room-dependent open range.** O7's points-valued check (goal-log, O7 entry) found F's base open range too loose
   at strong tables (+0.18 to +0.42 a table seed offline) and about right in the ordinary room. It needs a switch that
   tells the rooms apart early and does not leak into the realistic room; the table-level strong read leaks (S21).
   O5's big-blind read, or the seats' answers to every open, are candidates for that switch.
4. **Four and five alive, under 15 bb: jam or fold from a solved table.** Not built; S20 did three-handed only.
5. **A strong-table read that tells sized re-raises from jams**, so push/fold bots stop opening the strong routes.

## Against bots that adapt

6. **Exploiter 4**: a fresh agent builds a bot to beat batch 7's F (F changed short-handed in batch 7), then we fix
   what it finds. Exploiter 2 still leads F heads-up (about 8.9 to 8.1 after batch 7).
7. **A new outside bot every few rounds** (goal.md), so the climb never fits a fixed set of opponents.

## Reads

8. **The non-blind seats' fold read with the open clause priced in points.** O6's read is more accurate than F's
   (Brier 0.113 against 0.127, all nine fields), but F's open clause turns it into junk opens; O7's chip-priced fix
   loosened further. The two need fixing together, valued in points offline first (the check that matched the screens).
9. **O3's big-blind read where it helps** (O5 is the version on held-out; if it fails there, O3 parked).

## The night

10. **The twist reveals after Menlo Park (Nov 6) and Boston (Nov 9)**: turn whatever they show into a catalog entry and
    a drill the same day.
11. **A last rehearsal on the final ship** with a fresh agent, an unseen variant and an unfamiliar kit (goal.md).

## Tried and set aside (so nobody repeats them blind)

- O3 (the open-answer read): up at every strong table on held-out (+0.06 to +0.09), down in the realistic room; gated
  by the strong read (S21) still down. O6 and O7: see above. C3 (one stab size) leaked onto twists; C3h (plain
  hold'em only) was accepted.
- S20's R5 (three-handed tables on the button and the small blind): the small blind's first-in folds and limps lost
  in the realistic room; R6 (button only) was accepted.
- Playing for first when three or fewer remain: under 8..1 points first place is worth what ICM already prices.
- A bandit over a portfolio of strategies: the research expects a small edge at 150-200 hands.
