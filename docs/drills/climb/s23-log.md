# S23: where F's first places go at strong tables (running log)

Branch climb/s23-firsts, worktree goal/wt_s23, from main 8d03ba0 (batch 8 is F). Brief (coordinator, 2026-11-04 late):
at the strongest held-out room F is third of eight on points, takes 1st 12.3% (an even share is 12.5%) against 18-22%
for the two best bots, busts more, and the gap doubles under 10/7/5/4/3/2/1/0 against 8..1. Decompose finish position
at the strong tuning rooms, price each leak in points, build the top one or two behind dials off by default, screen.

Rules kept here: held-out judges (out_reads, elite5, out_cfr, out_press, out_charts, out_o9/o10/o11, rival4, rival5,
adapt2) are never run, read or looked at. Diagnosis on tuning rooms only (elite, elite_b, mirror, mirror_b, top,
night, realistic; checked in hyperion/sim/bestiary.py: none seats a held-out bot). Diagnostic seeds 16000-16999;
screens 10000-10199. Any change sits behind dials off by default; identity with them off against batch 8
(goal/idchk39's rows). Plain hold'em only unless shown to help a twist. Last bot change Nov 10 18:00 ET; anything to
ship must pass its screen by Nov 9 12:00 ET.

Scratch: `goal/s23/` (recorder `d23.py`, analysis `a23.py`, recordings `rec_<field>_<pay>.jsonl.gz`, `run_d23.sh`).

## Runs (appended as each finishes)

- 2026-11-05 00:00 Step 1 recordings started (`run_d23.sh`, 3 workers, nice 5): d23.py plays each field as
  climb_accept seats it (seed 7, 8 rotations, model mode, F = SHIP_DIALS in the hero seat) hand by hand and records,
  per table-rotation, places, points, hands, the cap, the stacks when the alive count first reaches 4 / 3 / 2, every
  seat's bust (hand, alive count, blinds, its last action: street, kind, facing a bet or first in, players in hand)
  and F's compact action string (to compare F's play across payout tables on the same deals). Cells: elite, mirror,
  elite_b, mirror_b under 8..1, 10/7/5/4/3/2/1/0 and 50/25/12/6/3/2/1/1; top and night under 8..1 and
  50/25/12/6/3/2/1/1. Seeds 16000-16199 (200 x 8). About 0.36 s a table-rotation: about an hour in all.

## Step 1: the decomposition (diagnostic seeds 16000-16199, F = batch 8)

(pending)
