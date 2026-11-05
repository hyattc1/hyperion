# S23b: the rest of the three-handed leak (running log)

Branch climb/s23b, worktree goal/wt_s23b, from climb/s23-firsts 8f5c4d1 (B18 on held-out H39 from that head; batch 8 is
F). Brief (coordinator, 2026-11-05 04:00): the three-handed first-in leak S23 priced (button and small blind at 8-27 bb,
F min-raises 55% / 72%, is jammed on 36% / 22%, folds 85-95%; about 0.08-0.10 a table under 10/7/5), then F's calls of
jams (about 0.03). Coin first, in points, fit and check on separate diagnostic seeds, the rule fixed before the screen,
no sweeps, tuning rooms only, nothing that leaks into the ordinary rooms; must sit on batch 8 with dials off playing it
exactly, coexist with B18 and H1 (climb/s20-h1: `hu2_*` dials, heads-up only; no name collides). 4 workers.

Seeds: S23 used 16000-16639; here fit 16640-16759, check 16760-16879; screens 10000-10199. Scratch `goal/s23b/`.

## Step 1: the shape, from S23's recordings (no new compute)

**The small blind's room dependence does not separate on reads of the big blind's answers** (`sbread.py` on S23's coin
records C_*: the tables on every seat, gates open; small-blind hands; tables - F in points a table, split by the
opponents' fold-to-raise rate (rival 3's per-seat fr_f / fr, shrunk 0.6 with weight 4; the most foldable, the least,
pooled), their re-raise rate and their raises faced). Under 10/7/5 the realistic room loses at every fold bucket (most
foldable opponent folds >= 85%: -0.049 ± 0.039; 75-85%: -0.018; < 75%: -0.015), night at every bucket but the thinnest,
and the strong rooms gain nowhere beyond noise (+0.011 ± 0.021 at 75-85%). The fold rates sit at 0.75-0.85 for most
seats in every room: a seat's answers over a table's history are 8-max answers and say nothing about how it answers a
small blind's open three-handed. **The small blind stays F's: a clean no** (as S20's R6 found; now with 2,800 eligible
hands a room instead of first-divergence sums).

**The button's remainder beyond B18** (the cell where neither read is open, and 18-27 bb): at the strong rooms the
tables gain where the most foldable opponent folds under 85% (+0.062 ± 0.022 of the button's +0.072) and nothing where
one folds 85%+ (+0.004 ± 0.013); night loses exactly there (-0.023 ± 0.025) and realistic deep (18-27 bb -0.028). So a
fold read does separate the button, but what it would add on top of B18 is about +0.01 a table and B18 is on held-out
from the other branch; not pursued now.

**The calls of jams: a counterfactual in points** (`cf_call.py`: the recordings hold every seat's cards and the dealt
runout, so for each jam F faced three-handed where its call closes the action (BB vs SB jam, BB vs BTN jam, the opener
vs a re-jam) the ICM value of calling minus folding is known hand by hand; bucket means are fair, only the buckets are
hindsight). Strong rooms pooled (3,840 F table-rotations a payout table): F calls 60-75% of its top-10% hands facing a
jam and 2-10% of its top-20%; at 8-18 bb the top-20% folds would have won 55-62% and were worth +0.1 to +0.4 points
each. The solved tables' own answers (tables/extra/short_3b.json, equal stacks) call 26 / 17 / 12% of hands facing the
small blind's jam at 8 / 12 / 18 bb, 12-17% facing the button's, and 31-52% facing a re-jam of the button's open at
8-12 bb; F calls 10-15% in each; the elites 18-42%. Rival 3's core prices the jammer's range as its PFR x 1.1 (about
0.25-0.33 for the elites), while they jam 45% of small blinds and 20% of buttons first in three-handed. **That is the
shape: F's answers to jams, not its jams.** Fixed rules without hindsight (call every jam with a top-20% hand at
8-18 bb): see the table in step 2. By jammer the counterfactual is opponent-dependent and thin (15-30 hands a jammer):
positive against the elites and F's copies, negative against the push/fold bot (Nash jammer) and often rival 1.

**Built** (commit bbc0b6c, tests in tests/test_s23_firsts.py): `short.three2_jams` (off), `three2_jam_roles`
("btn,sb,bb"), `three2_jams_after_raise` (True): with the composite's `short_route` carrying `pre_allin=short`, the
tables' fold / call nodes after a jam play three-handed for the dialed seats, under the same gates as the first-in
play (the 3-bet guard, the archetype guard, seat_rr / B18's either-or, three_max). Nothing routes `pre_allin` to the
member in batch 8, so with the dials off F is unchanged.

## Step 2: the coin on the jam answers (`d9.py`: the per-hand coin flips only the answers to a jam; first-in play is the
same in both arms; `ips3.py --jam`)

- 04:30 Fit run queued (`run_jam.sh`): identity with the dials off at bbc0b6c first (`idchk`), then J_<room>_<pay>:
  dials `short_route` + `pre_allin=short`, `three2_jams` true, `three2_seat_rr` 0 (gates open; the reads are recorded
  and the gate is chosen offline), seeds 16640-16759, seven rooms under 10/7/5 then 8..1, 4 workers.

**Fixed call rules valued on S23's recordings (seeds 16200-16319; points a table, x1000; the folds turned to calls):**

| room, payouts | call every jam with a top-20% hand at 8-18 bb | ... top-35% |
|---|---|---|
| strong rooms pooled, 10/7/5 | **+35.7** (637 folds) | +38.1 (1,272) |
| strong rooms pooled, 8..1 | +20.0 (597) | +17.2 (1,200) |
| night 10/7/5 / 8..1 | +5.7 / +3.7 | +1.7 / +0.4 |
| top 10/7/5 / 8..1 | +1.3 / +8.2 | -15.2 / +0.3 |
| realistic 10/7/5 / 8..1 | **-13.8** / -1.0 | **-31.2** / -11.9 |

The solved tables' answers sit between the two rules (they call 17-26% facing the small blind's jam at 8-12 bb and
31-52% facing a re-jam of the button's open). So the prize is about +0.02 to +0.035 a table at a strong table under
10/7/5 and the realistic room is where it costs (its jammers are the push/fold bot, a Nash jammer, and rival 1); a
200-seed screen's realistic guard resolves ±0.007. Without a read that tells the jammers apart this fails the guard;
the coin records the reads (the strong read, each opponent's re-raises of our opens, its fold / re-raise counts, its
name) to see whether one does.
