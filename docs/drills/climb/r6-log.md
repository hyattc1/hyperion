# R6: the adaptive test opponent (tuning copy), running log

Brief: the coordinator's R6 brief (decisions "The climb: addendum 9"; research report "Edges against strong opponents",
item 4). Branch climb/r6-adaptive from main 724cc7f. Bot: hyperion/sim/field/adapt1.py (`adapt1`, twin `adapt1_off`);
fields `adapt`, `adapt_hu`, `adapt_3`; curve tool tools/adapt_curve.py. Seeds: screen (10000-10199) only.

## Findings

1. **adapt1 learns F inside one table, and beats its counters-off twin against F in all three cells** (screen, 200
   seeds; same deals, same seeds; the two play identically through hand 30).

   | cell | adapt1 - twin, points | F with adapt1 - F with twin | flow from F per hand, adapt1: 1-30 / 31-100 / 101-200 | twin |
   |---|---|---|---|---|
   | adapt (8-max, six night seats) | **+0.480 ± 0.143** | **-0.318 ± 0.129** | -0.36 / +1.70 / +4.31 | -0.36 / -1.74 / -7.79 |
   | adapt_3 | **+0.517 ± 0.157** | **-0.397 ± 0.145** | -4.06 / +1.13 / +5.77 | -4.06 / -9.43 / -5.57 |
   | adapt_hu | **+0.412 ± 0.130** | -0.412 (zero-sum) | -7.92 / +1.50 / +21.29 | -7.92 / -12.50 / +48.98 |

   "Flow from F" is the chips that went from F's seat to adapt1's (each loser's chips split over the winners pro rata;
   exact heads-up). Against F it rises window to window in all three cells; the twin's falls (8-max, 3-handed) or
   stays down. Heads-up only 2% of hands are past hand 100 (468 and 423), so that last window is noise for both.
   Paired per table, the flow from F gains +197 ± 49 / +430 ± 164 chips (8-max), +563 ± 126 / +101 ± 156
   (3-handed) and +577 ± 152 / -27 ± 84 (heads-up) in hands 31-100 / 101-200.
2. **F's current numbers** (screen, through climb_accept's run_cells): adapt **5.889 ± 0.147** (adapt1 5.106),
   adapt_hu **8.605 ± 0.131** (adapt1 8.395), adapt_3 **8.007 ± 0.149** (adapt1 7.657). Against the twin F would
   score 6.206, 9.018 and 8.403. No timeouts or errors.
3. **Without F the rise mostly goes away, but not entirely.** Control (rival2 in the hero seat): 3-handed the counters
   gain +0.10 ± 0.15 points (against +0.52 with F); at 8-max adapt1 gains the same +0.46 as with F (that part comes
   from the night seats) but the hero seat loses nothing (-0.09 ± 0.17 against F's -0.32 ± 0.13) and the flow from
   it in hands 31-100 is level (+55 ± 60 against +197 ± 49); heads-up adapt1 learns rival2 too, about half as much
   (+0.20 ± 0.13 against +0.41 ± 0.13). Raw chips per hand rise with the blinds for either bot; the twin difference
   is the measure of learning.
4. **What adapt1 sees in F** (counts summed over tables, run 3): F folds to a single bet 62-75% (flop), 67-80%
   (turn); after checking it folds 80-90%; it folds to a raise after a small bet 80-100%; its small bets show 0.28-0.32
   strength at showdown against 0.75-0.78 for its large ones; it folds to 3-bets 73-91% (61% heads-up by table end);
   it calls 9% of all-ins at 8-max. Its postflop folding does not move during a table (heads-up 0.73 at hand 30,
   0.75 at the end). Its 3-bet defence does: heads-up it folds to the first two or three 3-bets, then 4-bets about
   40% of the next.
5. **Which counters pay against F** (adapt1's chips in the hands each fired, first-level bb): bluff bets into
   over-folders +2.9 (heads-up) to +10.8 (8-max) per hand, the most firings everywhere; raising F's small bets +5.5
   to +43; thin value +10 to +21; wider opens +1.5 to +2.8; light 3-bets +9.0 at 8-max, about even 3-handed and
   **-5.0 heads-up** (F 4-bets the first light 3-bet in most tables; the counter then stops). Raising F's half-pot
   bets on its general fold rate lost -25 per hand and went; a c-bet float lost -2.6 and went; wide jams on others'
   call rates lost (F calls wider against a wider jammer) and now read only calls of our own jams.
6. **F played bit-identically on main's fields**: confirm and guards on 10000-10039, 14/14 chunks with the same samples
   and call counts as a clean export of 724cc7f.
7. For the coordinator: the adapt cells are in climb_accept's exploit stage (adapt1's points print beside F's).
   tools/adapt_curve.py measures any adapter's learning curve against the hero seat, so the held-out copy can be
   checked the same way. tests/test_sim_exploiter.py's model-mode replay test fails under load on main as well
   (Hero's wall-clock panic mode); it is not this branch.

## Runs, as they happened

### 1. F's baseline on main (before any change)

From a clean export of 724cc7f (`git archive`, so no edit here could reach its workers):
`nice -n 5 python tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards --workers 2`
(10.5 min, load 22-50). F: night 5.965, night_hard 5.638, realistic 6.269, top 5.023, night @brief 6.218, night @th
24.589, night +double 5.853. Sample lists kept in scratch (main_fg.json) for the bit-identity check.

### 2. Smoke: legality

`adapt_hu`, `adapt_3`, `adapt` with Hero, 1 seed x rotations, model mode: no exceptions, no illegal actions.

### 3. What adapt1 counts of F (first version, counts summed over tables)

scratch diag.py, F in the hero seat; adapt_hu 10000-10019 (40 tables), adapt_3 10000-10009 (30), adapt 10000-10004 (40).

| | HU @30 | HU end | 3-h end | 8-max end | night seats, 8-max |
|---|---|---|---|---|---|
| fold to a bet, flop | 52/71 0.73 | 152/202 0.75 | 110/152 0.72 | 131/210 0.62 | 0.55 |
| fold to a bet, turn | 15/20 0.75 | 40/50 0.80 | 0.70 | 0.67 | 0.37 |
| check, then fold to a bet | 37/46 0.80 | 0.79 | 0.90 | 0.81 | 0.58 |
| fold to a raise after betting | 7/9 0.78 | 40/53 0.75 | 16/18 0.89 | 13/25 0.52 | 0.16 |
| fold to a 3-bet as opener | 45/57 0.79 | 91/148 0.61 | 0.73 | 78/90 0.87 | 0.74 |
| c-bet | 0.93 | 0.90 | 0.71 | 0.71 | 0.57 |
| call an all-in | 2/3 | 49/147 0.33 | 0.28 | 24/258 0.09 | 0.23 |
| showdown strength, small / large bets | | 0.32 (81) / - | 0.28 (45) / - | 0.29 (37) / 0.78 (8) | 0.55 / 0.67 |

F over-folds everywhere and its small bets are weak. But by hand 30 adapt1 has seen about 2 single bets per table,
so a 5-observation threshold per street almost never trips. Changed: postflop folds pooled over streets (threshold 4),
each street's and the check-then-fold rate shrunk toward the pooled rate, fold-to-raise shrunk toward it too; the
3-bet threshold 2 observations, all-in calls 3.

### 4. Curves, version 2 (pooled folds)

`python tools/adapt_curve.py --field adapt_hu --set 10000:10080 --workers 1` (F in the hero seat; adapt1 and its twin
on the same deals). Points heads-up: adapt1 8.144, F 8.856; twin 7.994, F 9.006. adapt1 - twin +0.150 ± 0.237. bb per
hand, hands 1-30 / 31-100: adapt1 -0.246 / -0.232, twin -0.246 / -0.325.
`--field adapt_3 --set 10000:10040`: adapt1 7.483, F 7.950; twin 7.042, F 8.425. adapt1 - twin **+0.442 ± 0.404**;
window 31-100 +520 ± 461 chips per table.

### 5. Which counters fire (scratch trace.py: tags per counter, adapt1's chips in those hands, first-level bb)

adapt_hu 10000-10079: bluff bet 511 hands, +3.66 per hand; light 3-bet 324, -6.10; raise a small bet 94, +5.05;
wide jam 84, -1.71; raise a bet on the pooled fold rate 42, **-25.0** (F's half-pot bets hold value; only its small
ones are weak). Changed: a larger bet is raised only on that seat's own folds to raises after larger bets (3+ seen,
70%); light 3-bets need 70% folds and 4-bets at most 1 in 5; wide jams at 20% calls.
Then adapt_hu: light 3-bet still -5.84 (153); adapt_3 10000-10039: bluff +3.31 (493), light 3-bet -0.34 (184),
wide jam -6.16 (118), raise small +10.7 (13), thin value +9.8 (8), open wider +2.49 (44).

### 6. Light 3-bets and wide jams heads-up (scratch t3b.py: the opener's answer)

adapt_hu 10000-10079, light 3-bets: F folds 78 (+3.75 bb), 4-bets **66** (-16.7 bb), calls 5. F folds to the first
two or three 3-bets and 4-bets the next about 40% of the time: its 3-bet defence answers a 3-bettor, and adapt1's
baseline already 3-bet 12% heads-up. Wide jams: F called 4 of 13 (-87 bb each), far over the 20% estimate. Changed:
light 3-bets stop after any 4-bet in the opener's last six answers (and 4-bets at most 1 in 8 overall); wide jams are
priced (jam beats folding at the estimated call chance) and read only calls of our own jams; the baseline value 3-bet
range halved (0.15 to 0.08 of the opener's range); the c-bet float (call c-bets wider at 75%+ c-bets: -2.6 per hand,
48) dropped. After: heads-up light 3-bets 108, still -4.98 (the first light 3-bet of a table is the one F 4-bets).

### 7. Version 7 curves

`adapt_curve --field adapt_hu --set 10000:10080`: adapt1 8.331, F 8.669; twin 7.862, F 9.137; adapt1 - twin
**+0.469 ± 0.249**. Chips per hand 1-30 / 31-100 / 101-200: adapt1 -7.80 / +0.03 / +1.32; twin -7.80 / -12.07 / -45.85.
`--field adapt --set 10000:10030` (8-max, F and six night seats): adapt1 5.003, F 6.113; twin 4.680, F 6.206; adapt1 -
twin +0.323 ± 0.335; window 31-100 +370 ± 229 chips per table (flow from F +210 ± 129).
Trace, adapt 10000-10029: every counter pays at 8-max: bluff +10.75 (813), light 3-bet +8.98 (436; F folds to 87% of
3-bets there), open wider +1.80 (692), thin value +21.4 (40), wide jam +7.0 (27), raise small +43 (10).

### 8. Baseline fixes (both twins)

Heads-up a half-pot flop bet was defended only at 0.475 strength while F c-bets 90%: one flop bet heads-up is now
defended 0.06 wider. adapt_hu 10000-10079: twin 7.862 to 7.919, adapt1 8.387, adapt1 - twin +0.469 ± 0.259.
As the heads-up opener (80% of hands) adapt1 folded about 90% to a 3-bet: its 3-bet defence now scales with its open
range (jam 0.1 r, call 0.35 r at 25 bb or more). adapt_hu 10000-10079: **adapt1 8.556, F 8.444**; twin 8.050, F
8.950; adapt1 - twin **+0.506 ± 0.222**; hands 1-30 -0.265 bb per hand (was -0.361).
Same code, `--field adapt_3 --set 10000:10040`: adapt1 7.608, F 8.092; twin 7.183, F 8.367; +0.425 ± 0.390.
`--field adapt --set 10000:10030`: adapt1 4.953, F 6.133; twin 4.624, F 6.254; +0.329 ± 0.369; window 31-100 +419 ±
215 chips per table.
Trace by window, adapt_3: in hands 101-200 the counters barely fire (bluff 52, wide jam 20, tight jam 5), so that
window's difference is which tables reach it, not the counters. adapt: every counter pays in both windows and fires
more late (bluff 390 / 435 hands, +6.3 / +15.1; light 3-bet 281 / 162, +6.5 / +13.4).
Control heads-up with rival2 in the hero seat (10000-10019): adapt1 8.800, rival2 8.200; twin 8.650; +0.150 ± 0.294;
adapt1 bb per hand 1-30 / 31-100 +0.257 / +0.247 (flat).
Latency: adapt1's own act(), 8-max mixed tables, 1,887 calls, p50 13 us, p99 101 us (load 10).

### 9. F plays bit-identically on main's fields (54c3489)

`climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards --workers 2` on this branch (4.0 min),
then scratch cmp_fg.py against run 1's cache: **14/14 chunks identical** (samples and call counts) across night,
night_hard, realistic, top, night @brief, night @th, night +double. The same means as run 1 to the third decimal.

### 10. Full screen, heads-up and 3-handed (54c3489)

`adapt_curve --field adapt_hu --set screen --workers 1` (200 seeds x 2 rotations) and `--field adapt_3` (x 3).

| | heads-up adapt1 | twin | 3-handed adapt1 | twin |
|---|---|---|---|---|
| flow from F per hand, hands 1-30 | -7.92 | -7.92 | -4.06 | -4.06 |
| 31-100 | +1.50 | -12.50 | +1.13 | -9.43 |
| 101-200 | +21.29 (468 hands) | +48.98 (423) | +5.77 | -5.57 |
| bb per hand (all chips), 1-30 / 31-100 / 101-200 | -0.355 / +0.013 / +0.148 | -0.355 / -0.304 / +0.325 | -0.043 / +0.089 / +0.106 | -0.043 / -0.150 / +0.048 |
| points | 8.395 (F 8.605) | 7.982 (F 9.018) | 7.657 (F 8.007) | 7.140 (F 8.403) |

Paired adapt1 - twin: heads-up **+0.412 ± 0.130** points, window 31-100 +577 ± 152 chips per table, 101-200 -27 ± 84;
3-handed **+0.517 ± 0.157** (F -0.397 ± 0.145), 31-100 +717 ± 156 (flow from F +563 ± 126), 101-200 +63 ± 172.
Heads-up only 2% of hands are past hand 100, so that window is a few lucky long tables for either bot.

### 11. F's numbers in the three cells (screen, 54c3489)

scratch f_cells.py: tools/climb_accept.py's own run_cells and gather on the three adapt cells (the exploit stage's
cache layout), F = `{"dials": {}}`, 1 worker. Code 289d626e76.

| cell | F | ± | adapt1 | n | tmo / err |
|---|---|---|---|---|---|
| adapt @10/7/5/4/3/2/1/0 | 5.889 | 0.147 | 5.106 | 200 x 8 | 0 / 0 |
| adapt_hu +hu | 8.605 | 0.131 | 8.395 | 200 x 2 | 0 / 0 |
| adapt_3 +three | 8.007 | 0.149 | 7.657 | 200 x 3 | 0 / 0 |

tools/adapt_curve.py's hero-seat points equal these per seed in all three cells (200 of 200 identical).

### 12. Full screen, 8-max (54c3489)

`adapt_curve --field adapt --set screen --workers 2` (200 seeds x 8). Flow from F per hand, hands 1-30 / 31-100 /
101-200: adapt1 -0.36 / +1.70 / +4.31; twin -0.36 / -1.74 / -7.79. All chips, bb per hand: adapt1 +0.231 / +0.158 /
+0.170; twin +0.231 / +0.045 / +0.038. Points: adapt1 5.106 (F 5.889), twin 4.627 (F 6.206). Paired adapt1 - twin
**+0.480 ± 0.143** points, F **-0.318 ± 0.129**; window chips +439 ± 98 / +926 ± 310 per table, flow from F +197 ± 49
/ +430 ± 164.

### 13. Controls: a field without F (rival2 in the hero seat)

`adapt_curve --hero rival2`: adapt_hu and adapt_3 on screen, adapt on 10000-10099.

| cell | flow from the hero seat per hand, adapt1 | twin | adapt1 - twin, points | hero seat |
|---|---|---|---|---|
| adapt_hu | +2.06 / +8.53 / +44.91 (111 hands) | +2.06 / +1.94 / -42.74 (217) | +0.203 ± 0.131 | -0.203 |
| adapt_3 | -1.48 / +4.20 / -0.18 | -1.48 / +0.41 / +10.91 | +0.102 ± 0.152 | -0.123 ± 0.138 |
| adapt (100 seeds) | -0.20 / +0.67 / +5.89 | -0.20 / -0.32 / -1.22 | +0.458 ± 0.202 | -0.086 ± 0.168 |

Paired flow from the hero seat, 31-100 / 101-200: heads-up +234 ± 169 / +36 ± 67; 3-handed +189 ± 135 / -79 ± 138;
8-max +55 ± 60 / +266 ± 246 (F: +577, +563 and +197 in 31-100).

### 14. Tests and the tool

`pytest tests/test_sim_adapt.py tests/test_climb_accept.py tests/test_sim_fields.py tests/test_sim_night.py
tests/test_sim_bestiary.py -k "adapt or climb or fields or night or registered"`: 65 passed.
tests/test_sim_exploiter.py: 18 passed, 1 failed (`exploit3` replay); on clean main 724cc7f the same test fails too
(`exploit2` that time): Hero's panic mode reads the wall clock and the host was at load 13-50. test_sim_adapt's replay
test turns the panic off, as climb_accept does.
tools/adapt_curve.py now reads the adaptive seat's hand ends on the instance, not by patching Adapt1Bot, so it measures
any adapter (`--field adapt_judge_hu --seat <its name> --bot <its name> --twin ''`); adapt_3 10000-10009 printed the
same table before and after.
