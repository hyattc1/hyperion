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
- 05:40 Identity at bbc0b6c with the dials off (`goal/s23b/idchk`): **14 of 14 chunks identical** to idchk39's rows.
- 06:25 **The fit under 10/7/5** (seven rooms, 120 seeds x 8 each; eligible = the hands where the tables wanted the jam
  answer with the gates open; tables - F in points a table, 95%):

| room | all jam answers | big blind | button (its open re-jammed) | small blind |
|---|---|---|---|---|
| four strong rooms pooled | **-0.010 ± 0.032** | -0.004 ± 0.020 | +0.010 ± 0.020 | -0.015 ± 0.018 |
| realistic | -0.026 ± 0.050 | -0.015 ± 0.033 | -0.022 ± 0.032 | +0.012 ± 0.020 |
| night | +0.017 ± 0.052 | +0.024 ± 0.027 | +0.012 ± 0.034 | -0.019 ± 0.029 |
| top | +0.017 ± 0.060 | -0.009 ± 0.036 | +0.014 ± 0.036 | +0.011 ± 0.029 |

  By R6's gate parts at the strong rooms nothing stands out (strong & all>=1: BB +0.004 ± 0.013, BTN +0.007 ± 0.011,
  SB -0.012 ± 0.013; the other cells -0.015 to +0.005); by depth the only positive cell is the button's at 8-12 bb
  (+0.009 ± 0.009 at the strong rooms, 60 hands an arm; realistic -0.006, night +0.001, top +0.010), which is a
  split picked after the fact, not a rule. By opponents present, no pair is beyond noise.
- **Reading: the solved tables' answers to jams are not better than F's own**, at the strong rooms (-0.010 ± 0.032)
  or anywhere; the counterfactual's +0.036 a table for "call every jam with a top-20% hand at 8-18 bb" does not carry
  to the equilibrium answers (which call other hands, and 31-52% facing a re-jam of the button's open), and the
  hindsight in the counterfactual's buckets was worth more than I allowed. The 8..1 cells were stopped unplayed (the
  effect under 8..1 is smaller still). **A clean no on the calls of jams**, as built here. `short.three2_jams` stays on
  the branch, off, measured.

## Summary

1. **The small blind's first-in play three-handed: a clean no.** The solved tables' small blind is level with F's at the
   strong rooms (+0.015 ± 0.024 under 10/7/5) and loses in the realistic (-0.081 ± 0.053) and night (-0.049) rooms;
   no read of the big blind's answers over the table's history (fold-to-raise, re-raise rate, raises faced, pooled or
   per seat) separates the rooms: the rates sit at 0.75-0.85 everywhere, because a table's answers are 8-max answers.
   A read of the big blind's answers to small opens *when short-handed* would need its own counts and gets a handful
   of hands a table; not built.
2. **The button's first-in play**: R6 plus B18 (on H39) take what is clean; the remainder (about +0.01 a table) sits
   behind a fold read (the most foldable opponent under 85%) that also keeps night level; not pursued while B18 is on
   held-out from the other branch.
3. **The calls of jams: a clean no** on the shape built (the tables' equilibrium answers; -0.010 ± 0.032 at the strong
   rooms under 10/7/5, nothing by role, depth, gate part or opponents). The counterfactual that motivated it (F calls
   60-75% of its top-10% hands and 2-10% of its top-20% facing a jam; a fixed top-20 rule at 8-18 bb +0.036 a table at
   the strong rooms, -0.014 realistic) stands as a diagnosis: rival 3's core prices a three-handed jammer's range as
   its PFR x 1.1, and the elites jam 20-45% first in. A rule on the core's range width (not the tables) is the untested
   shape; it needs a read that tells the elites' jams from the push/fold bot's and rival 1's, which this data (15-30
   hands a jammer) cannot fit honestly.
4. Nothing from S23b goes to a screen. Branch climb/s23b (head this commit, code bbc0b6c: the jam-answer dials, off;
   identity 14 of 14); tools in `goal/s23b/` (`sbread.py`, `cf_call.py`, `d9.py`, `ips3.py --jam`); recordings
   `goal/s23/rec3_<room>_<pay>.jsonl.gz` now for all seven rooms, `goal/s23b/J_<room>_brief.jsonl.gz`.

## S23c (asked 2026-11-05 04:10): a jam-range floor in rival 3's core behind a per-seat short-handed jam read: not built

The coordinator's brief: a width floor on the jammer's range by depth and role for three-handed jammers, gated by a
per-seat read of short-handed jams that keeps the strong rooms' +0.036 (10/7/5) / +0.020 (8..1) a table and loses the
realistic room's -0.014; first compute whether such a read sees enough and separates. `goal/s23b/jamread.py` on the
rec3 recordings (seven rooms, both tables, 14 cells, 18,553 three-handed jam decisions of F where its call closes the
action): walking each table in hand order, each seat's first-in preflop opportunities and first-in jams with four or
fewer alive; the read at the decision is (jams + 0.3 x 4) / (opportunities + 4) over the jammer's earlier short-handed
hands.

- **How much the read sees**: at the decision the jammer has had a median 17 short-handed first-in opportunities (p25
  10, p75 26) but a **median of 1 observed jam (31% none, 50% two or more)**. The read is mostly its prior.
- **How it reads the seats** (mean over F's jam decisions): elite1 0.26-0.29, elite2 0.22-0.25, **agent_pushfold 0.22**
  (a Nash jammer reads like an elite), elite4 0.16-0.18, F's copies 0.18-0.20, rival2 0.14; realistic's rival1 0.12,
  tag 0.11-0.12, pushfold 0.13-0.15; top's rival1 0.20-0.21, pushfold 0.18-0.20. The elites sit about 0.1 above the
  realistic room's seats with wide overlap, and a push/fold bot sits on either side depending on the room.
- **Whether it separates the gain from the loss** (the fixed rule "call every jam with a top-20% hand at 8-18 bb" on
  F's folds, by read bucket; points a table x1000, folds, mean per fold):

| group | read < .25 | .25-.35 | .35-.45 | .45-.55 | >= .55 | all |
|---|---|---|---|---|---|---|
| strong 10/7/5 | **+34.0** (518, +252) | +0.2 (61) | +0.7 (33) | +1.2 (15) | -0.4 (10) | +35.7 |
| strong 8..1 | **+14.7** (477, +118) | +2.2 (59) | +1.6 (37) | +0.7 (15) | +0.8 (9) | +20.0 |
| realistic 10/7/5 | **-14.0** (77, -175) | +0.2 (4) | 0 | 0 | 0 | -13.8 |
| realistic 8..1 | -1.1 (90) | -0.5 (2) | +0.9 (2) | -0.3 (1) | 0 | -1.0 |
| night 10/7/5 / 8..1 | +3.9 / +1.7 | +0.4 / +1.1 | +1.4 / +1.0 | 0 | 0 | +5.7 / +3.7 |
| top 10/7/5 / 8..1 | +2.3 / +5.7 | -2.3 / +1.8 | +1.3 / +0.7 | 0 | 0 | +1.3 / +8.2 |

  The whole gain at the strong rooms and the whole loss in the realistic room sit in the same bucket, read < 0.25: the
  jams F faces come mostly from seats that had shown few or no short-handed jams before (the first jam a seat makes
  three-handed is often the one F faces). **The read cannot keep the first and lose the second. Not built; stopped
  here**, as the brief asked.

**Ruled out for the jam calls, so nobody repeats it blind**: (1) the solved tables' equilibrium answers to jams (level
at the strong rooms, -0.010 ± 0.032 under 10/7/5; S23b step 2); (2) a wider fixed call range (top-20% at 8-18 bb:
+0.036 strong, -0.014 realistic under 10/7/5; no room-independent rule); (3) a per-seat short-handed jam read as the
gate (one jam observed at the median; the gain and the loss both at read < 0.25). What would still separate is the
jammer's identity-level style over a whole table (8-max VPIP / PFR / shove share), which rival 3's core already reads
(PFR x 1.1 is its range guess), or a larger depth-and-role prior for three-handed jams with no per-seat read at all,
which the fixed rules above say loses the realistic guard. The open leak stays as diagnosed: F's three-handed calls of
jams are too tight against the elites by about 0.02-0.035 a table under 10/7/5 and right against push/fold bots.
