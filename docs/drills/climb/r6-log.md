# R6: the adaptive test opponent (tuning copy), running log

Brief: the coordinator's R6 brief (decisions "The climb: addendum 9"; research report "Edges against strong opponents",
item 4). Branch climb/r6-adaptive from main 724cc7f. Bot: hyperion/sim/field/adapt1.py (`adapt1`, twin `adapt1_off`);
fields `adapt`, `adapt_hu`, `adapt_3`; curve tool tools/adapt_curve.py. Seeds: screen (10000-10199) only.

## Findings

(written at the end)

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
