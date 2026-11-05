# S25: why F under-converts heads-up at strong tables (running log)

Branch climb/s25-hu, worktree goal/wt_s25, from climb/batch9 ded60ba (F here = SHIP_DIALS + docs/drills/climb/batch9-candidate.json:
S22's river read, H1's solved heads-up preflop, B18). Brief (coordinator, 2026-11-05 07:30): heads-up at strong tables F converts
45-53% from two alive against the elites' 67-70%, arriving with 0.48 of the chips against 0.58-0.62; priced at +0.07 to +0.09 a
table under 10/7/5 (F -0.24 to -0.33 per heads-up arrival against an elite). H1 recovered about +0.008. First split the gap into
the shorter stack and worse play at equal stacks; then price F's play by line and street against the best tuning bots, with H1 on;
build the biggest sound fix behind a dial, off by default; coin on fit and check seeds before any screen.

Rules kept here: held-out judges (out_reads, elite5, out_cfr, out_press, out_charts, out_o9/o10/o11, rival4, rival5, adapt2) never
run, read or looked at; the rooms used (elite, elite_b, mirror, mirror_b; checked in hyperion/sim/bestiary.py FIELDS) seat none of
them. Diagnostic seeds 19000-19999; screens 10000-10199. Identity with the dials off against batch 9 before any screen. Plain hold'em
only unless shown otherwise. Deadline: a passing screen by Nov 9 12:00 ET.

Scratch: `goal/s25/` (recorder `d25.py` = S23's d3b plus which composite section:donor made each of F's decisions; analysis
`a25.py`: `split` the chips/play split per arrival, `lines` the heads-up hand book, `dec` the postflop decision mix;
recordings `rec_<room>_<pay>.jsonl.gz`, `run_rec.sh`).

## Runs (appended as each finishes)

- 07:35 Recordings started (`run_rec.sh`, 4 workers, nice 5): d25.py plays elite, mirror, elite_b, mirror_b under 10/7/5/4/3/2/1/0
  (brief) and 8..1 (lin) on seeds 19000-19199 (200 x 8 a cell), F = batch 9 (`goal/s25/b9.json` on SHIP_DIALS), recording every
  hand with 2-4 alive: every decision (street, seat, kind, amount, to call, pot, stacks, who decided), every seat's cards, the
  runout, the deltas; per table-rotation points, places, the composite's section counts.
- 07:47 Recordings done (8 cells, 12 minutes). 07:50 the same seeds with F = batch 8 (`rec8_*`, brief) for a paired batch 9 - batch 8
  comparison; 08:00 the ordinary rooms (realistic, night, top; `rec_<room>_brief`) for the room check of any rule.

## Step 1: the split of the heads-up gap into chips and play (seeds 19000-19199, 200 x 8 x 4 strong rooms)

Method (`a25.py split`): for each table-rotation, the first hand with two alive; each survivor's chip share s then; its final points.
Heads-up ICM is linear, so its value on arrival is pay2 + (pay1 - pay2) s, and at the 200-hand cap the engine pays exactly that on the
final stacks (hyperion/sim/engine.py: `icm_equity` of the survivors; nobody is "placed first" at the cap, S23's "1st given 2 alive"
counted places and so read every capped table as a loss for both). The heads-up stage's gain = final points - arrival value ("play");
the chips part = (pay1 - pay2)(s - 0.5). "Play less luck" subtracts the all-in luck of the heads-up hands (the realized delta minus
(2 eq - 1) x the effective stack for every hand that ended all-in before the river; preflop equities from tables/hu_matrix.json, flop
and turn all-ins enumerated). Per-seed 95% intervals.

| F = | pay | bot | arrivals | share on arrival | 1st outright | chips Δ(s-.5) | play | play less luck | total per arrival |
|---|---|---|---|---|---|---|---|---|---|
| batch 9 | 10/7/5 | F | 1646 | 0.501 | 46.1% | +0.002 | +0.137 ± 0.056 | **+0.096 ± 0.040** | +0.133 |
| batch 9 | 10/7/5 | elite1 | 1694 | 0.563 | 54.6% | +0.190 | +0.173 ± 0.059 | **+0.208 ± 0.040** | +0.363 |
| batch 9 | 10/7/5 | elite2 | 1611 | 0.570 | 57.4% | +0.211 | +0.198 ± 0.064 | **+0.196 ± 0.043** | +0.407 |
| batch 8 (same seeds) | 10/7/5 | F | 1630 | 0.500 | 38.5% | +0.001 | -0.007 ± 0.060 | **-0.032 ± 0.041** | -0.017 |
| batch 8 | 10/7/5 | elite1 | 1700 | 0.564 | 55.8% | +0.191 | +0.222 ± 0.058 | +0.241 ± 0.040 | +0.414 |
| batch 8 | 10/7/5 | elite2 | 1600 | 0.572 | 59.2% | +0.217 | +0.255 ± 0.062 | +0.238 ± 0.046 | +0.474 |
| batch 9 | 8..1 | F | 1581 | 0.475 | 41.4% | -0.025 | +0.023 ± 0.020 | +0.021 ± 0.013 | +0.003 |
| batch 9 | 8..1 | elite1 | 1714 | 0.584 | 55.1% | +0.084 | +0.056 ± 0.020 | +0.061 ± 0.012 | +0.136 |
| batch 9 | 8..1 | elite2 | 1698 | 0.581 | 58.0% | +0.081 | +0.063 ± 0.019 | +0.066 ± 0.013 | +0.146 |

**The split.** Under 10/7/5 at a strong table the elites take about +0.37 to +0.41 a heads-up arrival over an even split and F +0.13:
a gap of 0.25-0.27 per arrival, of which **chips on arrival 0.19-0.21 (about 70%)** and **play 0.10-0.11 ± 0.06 (about 30%)**. Under
8..1 the same thirds (chips 0.11, play 0.04 ± 0.02). F arrives at 0.50 of the chips (0.475 under 8..1), the elites at 0.56-0.58: that
part is the three-handed and earlier stages (S23's leak), not heads-up play. Per table (F reaches heads-up in 25% of its table-rotations):
play about +0.027 under 10/7/5 and +0.010 under 8..1 if F converted like the elites; chips about +0.05 / +0.027.

**Batch 9 closed most of the play gap.** On the same seeds batch 8's F made -0.03 ± 0.04 a heads-up arrival in play against the elites'
+0.24; batch 9's F makes +0.10 ± 0.04: **+0.13 per arrival (about +0.033 a table under 10/7/5)**, nearly all of it H1 (S22 touches the
river read, B18 the three-handed stage). Against the elites themselves F is now level: F vs elite1 -0.02 ± 0.10 per arrival (batch 8
-0.24 ± 0.11), vs elite2 -0.06 ± 0.11 (batch 8 -0.32 ± 0.12); F's hands against the elites sum to +0.0006 ± 0.0083 a table-rotation.
Where the remaining play gap sits, by opponent (10/7/5, play less luck, per arrival): against F's own copies F +0.13 ± 0.10 where
elite1 makes +0.32 and elite2 +0.51 (355 arrivals); against rival2 +0.07 / +0.19 / +0.06; against rival1, agent_pushfold the same as
the elites (+0.37-0.47). So the elites' heads-up edge over F is not what they do to F but what they do to F-like bots (the copies in the
mirror rooms, which play batch 8's heads-up: min-raise 75-88% of buttons and fold 90% to re-jams; elite1 re-jams 64-74% of the opens it
faces heads-up at 8-22 bb, elite2 55-58%, F 30-34%, the copies 38%; see below).

Other splits (batch 9, 10/7/5, play less luck): by depth on arrival F is 0.1-0.15 below the elites at 15-50 bb and level under 10;
by hands left to the cap nothing (F +0.00 ± 0.10 with under 20 hands left, the elites +0.03 / +0.13: the cap itself is not a leak);
by room F +0.13 / +0.12 (elite, elite_b) against the elites' +0.15 to +0.26, and +0.06 / +0.08 at mirror / mirror_b against +0.19 to
+0.23 (the copies are there).

**H1's reach** (`hu2why.py`, elite 10/7/5, 30 seeds): at 10-22 bb H1 plays 26-27% of F's heads-up preflop decisions; the strong read is
shut on 51-53% of them (the table-level share of our opens re-raised, averaged over the 8-max history), `hu2_like_opp` < 3 on another
20%; at 22-40 bb the strong read is shut on 74% and the button cap takes 13%. The rest of F's heads-up preflop is rival 3's core.

## Step 2: the play by line (4 strong rooms, 10/7/5; `a25.py lines`, `dec`, `cf_hu.py`)

- Postflop (`dec`): F folds 75% facing a bet heads-up (the elites 55-61%), bets 57% when checked to (52-56%); its results per decision
  are the elites' or better facing a bet (-75 milli-points a decision against -91 / -101) and between them with nothing to call (+24
  against +38 / +1). Against the copies F folds the turn 85% facing a bet (the elites 56 / 45%) and loses -217 a decision against -135 /
  -147; the called pots against copies sum to F -1.8 against elite1 +1.5 and elite2 +7.1 milli-points a table-rotation. Small.
- Preflop lines (F against the elites, per table-rotation, milli-points): the button's open re-jammed and folded -21.0 (1,086 folds of
  1,419, 77%) against the calls +19.2 (333, +369 each); the big blind's fold to an open-jam -10.2 (1,060); the big blind's re-jams +3.9
  net (324 of 2,671 opens faced, 12%, folded 88%). The elites against F: elite1's re-jams are break-even now (+1.5 net: F calls 21%).
- **The counterfactual on F's folds to jams** (`cf_hu.py`: the jammer's actual hand against F's folded hand at hu_matrix equity, (2 eq - 1)
  x the effective stack, minus the fold's delta; the jammer's hand does not depend on F's fold, so bucket means are fair; buckets by F's
  class rank = its equity against a random hand). 4 strong rooms, 10/7/5, milli-points a table-rotation (6,400 rotations):

| spot | who decided F's folds | folds | calls made | call every fold | q2 (.46-.52) | q3 (.52-.58) | **q4 (>= .58)** |
|---|---|---|---|---|---|---|---|
| BTN open, BB re-jam | all | 2,933 | 693 (+316 each) | +19.1 | +5.5 (998) | **+15.1 (650, +149 each)** | **+9.3 (263, +227 each)** |
| ... | rival 3's core (base) | 2,219 | 195 | +12.4 | +0.9 (621) | **+12.6 (534)** | **+9.3 (263)** |
| ... | H1 | 714 | 498 | +6.7 | +4.6 (377) | +2.5 (116) | - |
| BB vs BTN open-jam | all | 3,041 | 894 (+139) | -12.7 | +1.6 (845) | **+7.0 (602, +74 each)** | +1.2 (71) |
| ... | base | 2,670 | 726 | -7.5 | +2.2 | +6.8 (561) | +1.2 (71) |
| batch 8 F, BTN open re-jammed | all | 4,283 | 432 | +49.5 | +10.7 | +32.7 (1,129) | +20.3 (478) |

By depth (BTN re-jammed, q3+q4 folds): 10-15 bb +13.9, 15-20 +10.2, 20-30 +0.6. The elites fold the same spots too (elite1 1,417 folds,
q3+q4 worth +12.3; elite2 994, +11.7): everyone's button over-folds to the heads-up re-jam, but F most, because **rival 3's core prices
the re-jammer's range as its re-raise rate over the 8-max table (w = 0.9 x r3 + 0.02, about 0.10-0.16 for an elite) and an open-jammer as
1.1 x its 8-max PFR (0.2-0.3), while heads-up at 8-22 bb elite1 re-jams 64-74% of the opens it faces, elite2 55-58%, rival2 36-38%, F's
copies 38%, elite4 32%, rival3 32%, and open-jams 23-43% of its buttons** (`a25` room scan). H1's own tree, where it plays, folds
q0-q1 and mixes q2 (its folds are worth +6.7 all told, +2.5 at q3): about right.

Room check (realistic, night; `rec_<room>_brief`): the re-jammers there are narrow (rival1 22%, tag 2%, pushfold 2%, loose_aggro 0%, the
night pool 11%; open-jams rival1 18%, pushfold 10%, the pool 13%), and the counterfactual follows: BTN re-jammed q3 folds realistic -2.3
(111 folds, -33 each), night -1.0; **q4 folds +9.5 (57) / +3.6 (52): positive in every room**; BB vs open-jam q3 realistic +0.8, night
+2.8, q4 +0.8 / +3.5: positive everywhere, as the open-jammers are wide in every room (the push/fold Nash width at 10-15 bb is 0.45-0.58).
So a blanket q3 call to re-jams fails the realistic guard (S23b's three-handed finding again); a floor that reaches q4 to re-jams and q3
to open-jams is positive in every room.

**Equilibrium widths for the prior** (tables/short_hu2.json, H1's solve, per-class strategies weighted by combos): the big blind re-jams
the button's min-raise 0.49 at 5 bb, 0.35 at 8, 0.32 at 10, 0.25-0.29 at 12-16, 0.25 at 18-20, 0.24 at 22; the button facing a re-jam of
its open calls 0.45 at 10 bb, 0.33 at 15, 0.26 at 20 (F's base calls 8%, H1 41%). The push/fold Nash push width (tables/pushfold_hu.json)
is 0.72 at 5 bb, 0.62 at 8, 0.58 at 10, 0.45 at 15, 0.40 at 20.

## Step 3: the rule, and the coin (fit seeds 19200-19319, check 19320-19439)

**Built (commit c14393e)**: in rival 3's core (hyperion/hybrid/core3.py, the base member that plays F's heads-up preflop where H1 does
not), heads-up, plain hold'em, one opponent all-in, at or under `r3.hu_jam_max_bb` (20) effective: the width of the all-in opponent's
range has a floor. Our open re-jammed (the hand's second raise is its all-in): `r3.hu_jam_w` (0 = off). Its first-in all-in from the
button against our blind: `r3.hu_openjam_scale` x the push/fold Nash push width at the depth (tables/pushfold_hu.json p_push: 0.58 at
10 bb, 0.45 at 15, 0.40 at 20; 0 = off). Calls only (the width only widens; rival 3's all-in price, ICM, decides, and heads-up ICM is
chips), after S24's shove read where that is on; H1's decisions never see it. Tests tests/test_s25_hu.py (8: the Nash width, the floor
by line, the dials reach heads-up decisions, shut gates and three-handed and twist tables play as F, a table replays). The coin recorder
`goal/s25/d25c.py` toggles `core.hu_jam_on` per heads-up hand and records `would` (a floor above rival 3's width at one of F's
decisions), who decided, the strong read, the opponent, F's class; `ips_hu.py` is the IPS judge on the hands where the base's decision
saw a floor.

What rival 3 then calls with (its `_eqvs` against the top w of hands at the all-in price; share of hands, by our class rank): a re-jam of
our 2 bb open at 15 bb: w 0.15 (an elite's 8-max re-raise rate, F today) calls 11% (q4 only, and not all of it); 0.20 15.5% (q4 0.14 of
0.17, q3 0.01); 0.25 18.6% (q4 0.15, q3 0.03); **0.30 24% (q4 0.17, q3 0.07)**; 0.35 27% (q3 0.09); 0.45 31.5% (q3 0.14). At 10 bb
0.30 calls 28% (q3 0.10), at 20 bb 20% (q3 0.04). An open-jam at 12 bb: w 0.58 (Nash) calls 35% (q4 0.17, q3 0.16); 0.45 28.5% (q3
0.11). The fit values: `hu_jam_w` 0.30 (the equilibrium big blind's re-jam width at 10-18 bb; every strong build is wider),
`hu_openjam_scale` 1.0 (the Nash width). If the coin says the q3 calls lose where the room's re-jammers are narrow, 0.20-0.25 reaches
q4 alone, which the counterfactual found positive in every room; that would be a second fixed rule from the same diagnosis, not a sweep.

### The fit (seeds 19200-19319, 120 x 8 a room, 10/7/5; `C_<room>_brief.jsonl.gz`; floors - F in points a table-rotation, 95%)

Eligible = the heads-up hands where a floor was above rival 3's width at a decision the base made (about 1 in 7 heads-up hands).

| room | all | BB vs open-jam | BTN open, re-jammed | re-jam q2 / q3 / q4 | open-jam q2 / q3 / q4 |
|---|---|---|---|---|---|
| four strong rooms pooled | **+0.021 ± 0.019** | +0.016 ± 0.014 | +0.005 ± 0.013 | +0.001 / +0.003 / +0.004 | +0.003 / +0.009 / +0.005 |
| realistic | -0.014 ± 0.034 | +0.004 ± 0.028 | **-0.018 ± 0.021** | -0.005 / -0.006 / -0.003 | -0.001 / +0.006 / -0.002 |
| night | -0.006 ± 0.055 | -0.003 ± 0.044 | -0.003 ± 0.028 | +0.001 / +0.006 / -0.008 | -0.004 / -0.003 / +0.002 |
| top | +0.011 ± 0.033 | +0.003 ± 0.028 | +0.008 ± 0.026 | +0.004 / -0.004 / +0.004 | 0.000 / +0.003 / +0.004 |

Reading: at the strong rooms the floors are worth about +0.02 a table under 10/7/5 (about +0.007 under 8..1: below what the screen
resolves there), most of it the open-jam floor (the big blind's calls of the button's all-in with q3 hands, +0.009, positive in
realistic and top as well). The re-jam floor at 0.30 is level at the strong rooms and **down in the realistic room (-0.018 ± 0.021),
exactly where the counterfactual said it would be: the floors' arm calls q2 and q3 hands against narrow re-jammers (rival1, tag) and
loses -0.005 / -0.006 there**, while its q4 calls are the positive part at the strong rooms (+0.004). So the second fixed rule from the
same diagnosis, written above before the fit: **candidate B = `r3.hu_jam_w` 0.20 (the re-jam floor reaches q4 alone: 15.5% of hands
at 15 bb), `r3.hu_openjam_scale` 1.0**. Run on the fit seeds again (`B_*`) and on the check seeds 19320-19439 (`D_*`), both rooms sets.
- 08:45 **Identity** (`goal/s25/run_idchk.sh`: climb_accept `--cand goal/s25/b9spec.json` (batch 9's dials, S25's absent) on 10000:10040
  confirm,guards, run on this branch at c14393e and on climb/batch9 ded60ba (worktree goal/wt_s25ref), chunk samples compared with
  `idcmp.py`): **14 of 14 chunks identical** for batch 9's dials and 14 of 14 for F (SHIP_DIALS) too.

### Candidate B: the fit again and the check (`B_*` seeds 19200-19319, `D_*` seeds 19320-19439; 10/7/5; floors - F, points a table-rotation)

| room | B on the fit seeds | **B on the check seeds** | of which open-jam floor (fit / check) | re-jam floor (fit / check) |
|---|---|---|---|---|
| four strong rooms pooled | +0.017 ± 0.018 | **+0.024 ± 0.017 UP** | +0.015 ± 0.014 / +0.008 ± 0.013 | +0.002 ± 0.012 / +0.016 ± 0.012 |
| realistic | -0.014 ± 0.034 | +0.001 ± 0.038 | +0.004 / -0.015 | -0.018 / +0.016 |
| night | -0.012 ± 0.055 | +0.035 ± 0.046 | -0.006 / +0.027 | -0.006 / +0.008 |
| top | +0.017 ± 0.031 | +0.011 ± 0.036 | -0.005 / +0.010 | +0.021 / +0.001 |

Fit and check together at the strong rooms: about **+0.02 ± 0.012 a table under 10/7/5 (about +0.007 under 8..1)**, the two floors
sharing it (open-jam q3 calls +0.010 on both sets; re-jam q4 calls +0.002 / +0.010); the ordinary rooms level on both sets (every cell
inside its noise, the signs split). A coin that says yes at the strong rooms and no harm elsewhere: the screen runs.
- 09:20 **Screen started** (`run_screen.sh`, CAND goal/s25/s25bspec.json = batch 9's dials + `{"r3.hu_jam_w": 0.20,
  "r3.hu_openjam_scale": 1.0}`, `--base goal/s25/b9spec.json` (batch 9), --set screen, every stage, --aim strong, --runout-term, 4
  workers, nice 5; out goal/s25/S25_screen.md / .json; then elite under 10/7/5/4/3/2/1/0, S25_elite_brief.md; RUN_DONE in screen.done).
  The candidate as a file: docs/drills/climb/s25-candidate.json (the two dials on top of batch 9's). To resume after a stop: run
  run_screen.sh again at the same tree (cached chunks stand); do not change hyperion/ or tools/ in wt_s25 while it runs.

## Step 4: candidate B's screen (10000-10199, every stage, --aim strong, runout term; against batch 9)

11:00 **ACCEPT** (`goal/s25/S25_screen.md`, `.json`; code 299c1568cb = f30854d's hyperion/ (c14393e's code); 95 minutes, 4 workers;
0 timeouts, 0 errors). Corrected deltas, cand - batch 9, 200 seeds x 8:

| stage | cell | batch 9 | cand | cand - base | | raw |
|---|---|---|---|---|---|---|
| confirm | night | 6.023 | 6.023 | -0.001 ± 0.004 | level | +0.006 ± 0.006 |
| guards | night_hard / realistic / top | | | +0.001 / +0.000 / +0.001 (± 0.003-0.004) | level | |
| | night @10/7/5/4/3/2/1/0 | 6.333 | 6.329 | -0.004 ± 0.011 | level | +0.010 ± 0.018 |
| | night @50/25/12/6/3/2/1/1 | 25.240 | 25.221 | -0.018 ± 0.100 | level | |
| | night, doubling blinds | 5.909 | 5.908 | -0.001 ± 0.006 | level | |
| elite | elite | 4.902 | 4.906 | **+0.004 ± 0.004** | **UP** | +0.006 ± 0.007 |
| | elite_night | 5.468 | 5.473 | **+0.005 ± 0.003** | **UP** | +0.002 ± 0.006 |
| | mirror | 4.504 | 4.508 | **+0.004 ± 0.003** | **UP** | +0.003 ± 0.005 |
| | elite_b | 4.703 | 4.709 | **+0.005 ± 0.004** | **UP** | +0.008 ± 0.006 UP |
| | mirror_b | 4.525 | 4.532 | **+0.007 ± 0.003** | **UP** | +0.002 ± 0.006 |
| exploit | exploit / 2 / 3 / 4 / 5 (8-max @10/7/5) | | | -0.005 / +0.014 UP / +0.020 UP / +0.009 / -0.005 (± 0.009-0.013) | | |
| | the five heads-up cells, adapt_hu | | | 0 (exploit_hu identical) / +0.007 / +0.003 / +0.007 / +0.008 / -0.003 | level | |
| | the five three-handed cells, adapt, adapt_3 | | | -0.004 / +0.004 / -0.001 / +0.004 / -0.014 / +0.010 / +0.032 ± 0.031 UP | level | |
| variants | 22 of 26 identical; top_heavy -0.009 ± 0.081, antes_from_level_3 +0.001 ± 0.004, fast_schedule +0.000 ± 0.005 | | | | level | |
| aware | all five identical | | | | | |

Weighted (addendum 11): W +0.0009 ± 0.0016 (lower bound -0.0007), W-min +0.0007 ± 0.0029 (lower bound -0.0021); cap holds. p99 base /
cand 170-190 µs in every hold'em cell (the floor is two comparisons).

**elite under 10/7/5/4/3/2/1/0** (`S25_elite_brief.md`, 21 min): **ACCEPT**; elite **+0.013 ± 0.010 UP**, elite_night **+0.014 ± 0.012
UP**, mirror +0.009 ± 0.010, elite_b **+0.017 ± 0.011 UP**, mirror_b **+0.013 ± 0.010 UP**; W +0.0130 ± 0.0106 (lower bound +0.0024).
So the screen reads the candidate where the coin put it: about +0.005 at the strong rooms under 8..1 (five of five cells beyond noise
with the term), +0.013 under 10/7/5, the ordinary rooms, every exploit cell and every twist cell level or identical.

**For a held-out run** (on top of batch 9; `--aim strong`, every stage, runout term): branch climb/s25-hu at the head this entry is
committed on (code of hyperion/ as at c14393e), candidate docs/drills/climb/s25-candidate.json = `{"r3.hu_jam_w": 0.2,
"r3.hu_openjam_scale": 1.0}` on batch 9's dials (goal/s25/s25bspec.json is the full spec). Identity with the dials absent: 14 of 14
against climb/batch9 (goal/s25/idchk_*). No new table file (tables/pushfold_hu.json ships already); the zip is unchanged.

## Summary (what this found, and what to try next)

1. **The heads-up gap splits 70 / 30 chips / play, and batch 9 had already closed most of the play part.** At a strong table under
   10/7/5 the elites take +0.37 to +0.41 a heads-up arrival over an even split, F +0.13: of the 0.25-0.27 gap, chips on arrival are
   0.19-0.21 (F arrives at 0.50 of the chips, the elites at 0.56-0.58: the three-handed and earlier stages, S23's leak) and play
   0.10-0.11 ± 0.06 (0.04 ± 0.02 under 8..1). On the same seeds batch 8's F made -0.03 ± 0.04 a heads-up arrival in play and batch 9's
   +0.10 ± 0.04: H1 is worth about +0.13 per arrival (+0.033 a table under 10/7/5), more than its coin or screen could resolve. Against
   the elites themselves F is now level (-0.02 / -0.06 ± 0.10 per arrival; +0.0006 ± 0.008 a table); the remaining play gap is what the
   elites take from F-like bots (the copies: elite1 +0.32, elite2 +0.51, F +0.13 per arrival) by re-jamming their min-raises 55-74% of
   the time. S23's "F converts at 45-53% against 67-70%" also counted every capped table as a loss for both players (the engine pays
   the ICM of the stacks at the cap); the points are right in the table above.
2. **By line and street**: postflop F is level with the elites per decision (it folds more facing a bet, 75% against 55-61%, and
   loses less per decision); the preflop jam answers are the leak that is left. The counterfactual with the jammer's actual hand
   (fair per bucket) prices F's folds: the button's open re-jammed, folded with a top-quintile hand, +9.3 milli-points a table-rotation
   under 10/7/5 (263 folds; +227 each), with q3 +15.1 at strong rooms but -2.3 / -1.0 in realistic / night (narrow re-jammers: tag 2%,
   pushfold 2%, rival1 22%, the night pool 11%, against the elites' 55-74%); the big blind's fold to the button's open-jam with q3 / q4
   +7.0 / +1.2 at strong rooms, positive in every room. Rival 3's core, which plays F's heads-up where H1 does not (H1 plays 26% of the
   decisions at 10-22 bb: the strong read is shut on half, `hu2_like_opp` takes a fifth), prices the re-jammer as its 8-max re-raise
   rate (0.10-0.16) and the open-jammer as 1.1 x its 8-max PFR.
3. **Built: S25 = two floors on a heads-up all-in opponent's width in rival 3's core** (`r3.hu_jam_w` 0.20 for a re-jam of our open,
   `r3.hu_openjam_scale` 1.0 x the push/fold Nash push width for the button's open-jam, both at or under 20 bb, plain hold'em, calls
   only; the all-in price still decides). Coin: fit +0.017 ± 0.018, check **+0.024 ± 0.017** a table under 10/7/5 at the strong rooms,
   the ordinary rooms level on both sets; the first version (re-jam floor 0.30, reaching q3) was down in the realistic room (-0.018 ±
   0.021) as the counterfactual predicted and was replaced by the pre-registered fallback, not a sweep. **Screen ACCEPT: five of five
   strong cells UP under 8..1 (+0.004 to +0.007), four of five under 10/7/5 (+0.009 to +0.017), nothing down anywhere.** About a third
   of the play part of the gap; the chips part is not a heads-up fix.
4. **Next, in order.** (a) The chips on arrival (0.2 a heads-up arrival, +0.05 a table under 10/7/5) are the three-handed stage: S23's
   diagnosis stands, B18 took the clean piece; the rest needs a read of the big blind's answers to short-handed opens (S23b). (b) The
   elites' edge over F-like bots: a heads-up read of the opener's fold to a re-jam (the profiler's `open_fold_to_reraise` exists, unused
   heads-up) to re-jam min-raises wider from the big blind; F's big blind re-jams 12% of the elites' opens, calls 51%; the copies fold
   91% to a re-jam. Price it with the same coin; `pushfold.reshove_exploit` was rejected at 8-max in 2026-10 because Hero's copies
   re-shoved into each other, so the read must see the fold rate before it widens. (c) H1's reach: the strong read shuts it on half
   its decisions at strong tables; whether H1 without the strong read keeps its gain is a coin away (the first H1 coin, unguarded,
   was +0.0118 against +0.0078 gated, but lost -0.44 to exploiter 1 before `hu2_btn_max`). (d) Nothing in the postflop heads-up lines
   was worth a rule: the called pots sum to a few milli-points a table either way.

**Ruled out here, so nobody repeats it blind**: the cap (F's play with under 20 hands left is level with the elites'); F's postflop
heads-up folds (its results per decision are the elites' or better); a re-jam floor that reaches q3 hands (0.30: the realistic room's
narrow re-jammers punish it); a heads-up play gap against the elites themselves with H1 on (none within ±0.03 a table).
