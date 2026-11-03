# S13: a short-handed specialist member (running log)

Branch climb/s13-shorthanded, from main 4bd362f. Brief (coordinator, 2026-11-02): first place decides the most points
and is decided heads-up and three-handed, where F is weakest (S9: F's pre_3way / pre_hu chips a decision +0.02 /
+0.07 against +0.20 to +0.36 for the strong builds; exploiter 2 beats F heads-up 9.46 to 7.54). Build a member of the
composite for tables with three or fewer alive, close to unexploitable by default, its preflop computed offline by
our own solver, routed by a dial that is off by default. Screen seeds only (10000-10199; diagnostics on fresh seeds
9500-9799 and 8800-8803, not listed as used in goal-plan); no judge bot, judge field or held-out variant is run, read
or tuned on here. Every screen is model mode at fixed speed through tools/climb_accept.py's own cells and cache
(scratch `goal/s13/q.py`: chosen cells and seeds, and F's chunks pinned to main's code version 5ab71e63bc, since F
plays identically behind the new dials; the base means below reproduce S11's exactly). Workers 2, nice 10, host load
9-14 with other measurements running.

## The specialist

`hyperion/strategy/short.py` (`ShortMember`), member `short` of the composite (donors `short`, `shortx` with the exploit
layer), routed by `short_route` (sections -> donor) while at most `short_alive` (3) players have chips and the member
wants the decision. Off by default: SHIP_DIALS has no short route, so F builds no such member (tested).

- **Preflop**: a lookup in tables solved offline by `tools/solve_short.py` (below). The hand's preflop history is mapped
  onto the tree's lines; a raise between the tree's size and all-in maps to either by a log-scale split drawn once per
  hand; a line the tree lacks (a limp-raise, a flat in a three-way pot) is not ours and F plays it.
- **Postflop, heads-up pots** (two in the hand, at most `short.post_alive` alive, default 2): one size per street for
  value and bluffs (flop 0.5 pot, turn 0.66, river 0.75); the hand's place in its range from Hero's tier read as a
  percentile of random holdings on that kind of board, moved up by the range's history (each bet we called keeps the
  top minimum-defence share); facing a bet, continue with the top P / (P + b) of the range (minimum defence), raise
  its top part and strong draws, a few bluff raises from the folding part; with nothing to call, the aggressor bets
  its top share plus draws and bottom air in a balanced ratio, the defender stabs a little less, and out of position
  the defender checks.
- **Deviations**: the decision goes back to F (its reads and the exploit layer) while an opponent alive reads to F's
  profiler as dead or a station (`short.defer`; maniac and random fire on both exploiters short-handed, so they are not
  clear leaks there), and preflop goes back to F while an opponent alive 3-bets our opens far above equilibrium
  (`short.defer_3bet` 0.4 on rival 3's core's 3-bet read).
- The member keeps no state from its own answers (it replays the hand's history), so its light shadow records only
  the hand's starting chips.

## The solver and its convergence

`tools/solve_short.py`: CFR+ (regrets floored at zero, alternating updates, linearly weighted average) on the vector
form of an abstracted preflop tree, 169 classes with card-removal weights and tables/hu_matrix.json's all-in equity.
A call that does not end all in ends the tree at the flop, where the in-position player's share of the pot is
E + k E (1 - E) + s (b_ip - b_oop) (k = 0.25 min(1, SPR / 8), s = min(1, SPR / 6), b a small playability bonus for
suited, connected and paired hands): zero-sum by construction. Exploitability = the summed best-response gains
against the average strategy, in the abstract game.

- Check: the tree cut to push / fold at 10 bb reproduces tables/pushfold_hu.json (pushes 58.4% vs 57.8%, calls 37.5%
  vs 37.6%, the same call set, two boundary pushes differ) at 0.04 mbb/hand after 300 iterations (a test).
- **Heads-up** (`tables/short_hu.json`, 127 KB, chip EV): 26 depths 5-100 bb, 500 iterations each (pure Python, 2
  workers, 19 min). Lines: SB fold / limp / open (2.0 bb to 25 bb, 2.25 to 60, 2.5 deeper) / jam; BB vs the limp check
  / raise to 3 bb / jam; vs the open fold / call / 3-bet to 3.5x / jam; SB vs the 3-bet fold / call / 4-bet 2.2x /
  jam; BB vs the 4-bet fold / call / jam; anyone vs a jam fold / call (a raise over 40% of the stack is the jam).
  Exploitability (mbb a hand): 0.02 at 5 bb, 0.17-0.46 at 7-16, 0.7-0.9 at 18-25, 1.2-1.3 at 32-40, 2.0-2.6 at 50-70,
  3.4-3.7 at 85-100.
- **Three-handed** (`tables/short_3.json`, 1.5 MB compact, ICM at prizes 1 / 0.4 / 0 = 10/7/5): the three stacks on
  the grid 5, 8, 12, 18, 27, 40, 60, 90 bb (512 configurations), 300 iterations each (numpy, offline only; 2 workers,
  14 min). Lines: button fold / open / jam; after its fold the blinds play the heads-up tree (the small blind out of
  position); vs the open, SB fold / 3-bet / jam (no flat: no three-way flops), BB fold / call / 3-bet / jam (SB folded)
  or fold / jam (SB 3-bet), the button's answers; three-way all-ins on 20 equity buckets with a pairwise product model.
  Exploitability in milli-prizes a hand (the 1st - 3rd prize gap = 1000): median 0.026, 90th percentile 0.063, worst
  1.65 (5, 60, 12 bb: a short button between deep blinds). At ~0.01 prize per big blind in these configurations that
  is about 2.6 mbb a hand at the median.
- Loading: 89 ms for both tables, once per process when the member is built; a decision is a dict and string lookup.

## Screens

F's base on the screen seeds reproduces S11's numbers exactly (code main 4bd362f): exploit2_hu 7.540 (exploiter 2
9.460), exploit2_3 7.142 (8.573), exploit_hu 9.115 (exploiter 1 7.885), exploit_3 8.354 (6.993), exploit2 5.754
(5.175), exploit 5.619 (4.727).

Deltas are candidate minus F in our seat's points, ± the 95% interval of the per-seed paired difference; UP / DOWN =
beyond noise. Every candidate is `{"dials": {...}}` on top of SHIP_DIALS. Routes: R5 = `pre_hu, pre_3way, pre_allin,
post_hu_bet, post_hu_chk` to `short`; R3 = `pre_hu, post_hu_bet, post_hu_chk`; RP = `post_hu_bet, post_hu_chk`.

### Dev batch 1 (code 8872a77 / d4405b1): the whole specialist, and its parts

| candidate | seeds | exploit_hu | exploit_3 | exploit2_hu | exploit2_3 |
|---|---|---|---|---|---|
| C1: R5 (everything) | 200 | **-0.390 ± 0.186** | **-0.914 ± 0.213** | **+1.170 ± 0.168** | +0.170 ± 0.187 |
| C2: R3 (heads-up pre + post) | 100 | **-0.375 ± 0.252** | **-0.244 ± 0.137** | **+1.245 ± 0.240** | **+0.370 ± 0.152** |
| C3: three-handed preflop only | 100 | 0 (not played) | **-0.481 ± 0.281** | 0 | -0.203 ± 0.246 |
| C4: heads-up preflop only | 100 | **-1.020 ± 0.243** | **-0.364 ± 0.144** | +0.015 ± 0.203 | -0.010 ± 0.149 |
| C5: RP (heads-up postflop only) | 100 | +0.135 ± 0.201 | -0.104 ± 0.125 | **+0.885 ± 0.218** | **+0.220 ± 0.135** |

C1 wins heads-up against exploiter 2 (8.710 to 8.290; F 7.540 to 9.460) but loses to F against exploiter 1 heads-up and
three-handed. The parts: the postflop play alone is the gain and costs nothing against exploiter 1; the heads-up
preflop tables alone lose against exploiter 1 (-1.02) and add to the postflop against exploiter 2 only together with
it (C2 +1.245 against C5 +0.885); the three-handed tables lose against both.

Why (diagnostic tables, seeds 9500-9559): exploiter 2 reads to Hero's profiler as a maniac heads-up (raise share over
0.5) and exploiter 1 as random three-handed, so the first default (`defer` = dead, station, maniac, random) handed
almost every decision back to F; maniac and random are dropped from the default. Three-handed, the losing lines are the
button calling a 3-bet and playing the flop (Hero's postflop, -95 and -30 chips a time) and folding to the blinds'
3-bets: exploiter 1 3-bets small and often, which the tree maps onto its 3.5x node.

### Dev batch 2-3 (code ece875a / 422b7ab): deferral by the 3-bet read, roles, three-handed pots postflop

| candidate | exploit_hu | exploit_3 | exploit2_hu | exploit2_3 |
|---|---|---|---|---|
| C6: R3, preflop to F against a 3-bettor over 0.4 (`defer_3bet`) | **-0.390 ± 0.256** | -0.134 ± 0.137 | **+1.245 ± 0.240** | **+0.370 ± 0.152** |
| C7: R5 with the same | **-0.390 ± 0.256** | **-0.574 ± 0.297** | **+1.245 ± 0.240** | +0.217 ± 0.267 |
| C9: C6 + `post_alive` 3 (heads-up pots of three-handed tables too) | **-0.390 ± 0.256** | -0.171 ± 0.233 | **+1.245 ± 0.240** | **+0.463 ± 0.266** |
| C14: RP + `post_alive` 3 | +0.135 ± 0.201 | -0.011 ± 0.227 | **+0.885 ± 0.218** | **+0.393 ± 0.248** |
| C11: C9 with the small blind's preflop only (`pre_roles` sb) | **-0.405 ± 0.260** | -0.191 ± 0.211 | **+1.035 ± 0.246** | **+0.423 ± 0.267** |
| C12: C9 with the big blind's preflop only (`pre_roles` bb) | +0.135 ± 0.233 | +0.049 ± 0.231 | **+0.975 ± 0.206** | **+0.323 ± 0.245** |
| C13: C9 + the steal read (`steal_ftb` 0.42: limp -> min-raise) | -0.240 ± 0.273 | -0.091 ± 0.225 | **+1.155 ± 0.236** | **+0.373 ± 0.252** |

(100 seeds each, 10000-10099; base F 9.130 / 8.201 / 7.585 / 7.137 on those seeds.)

- Heads-up, exploiter 1's 3-bet read stays under 0.4 (it adapts its 3-bet rate heads-up), so `defer_3bet` never fires
  there; three-handed it fires (1,736 deferrals in 80 tables) but the three-handed tables still lose.
- The small blind's preflop is the whole loss against exploiter 1 (C11 against C12). The steal read recovers part
  (exploiter 1 and 2 fold 45-51% of big blinds to a min-raise, about twice equilibrium's 24% at 100 bb, and the
  equilibrium limps 44% of buttons at 100 bb).
- **C12 is the first clean candidate (S1)**: the big blind's preflop from the tables, every heads-up pot postflop
  (three-handed tables included), F everywhere else. It wins heads-up against exploiter 2 (8.560 to 8.440 on these 100
  seeds) and is level or up everywhere.

### S1's first cells, and where the 8-max loss is (code 422b7ab, 200 seeds unless noted)

S1 = C12 = R3, `short.post_alive` 3, `short.pre_roles` bb.

| cell | F | S1 | S1 - F | exploiter F / S1 |
|---|---|---|---|---|
| exploit_hu | 9.115 | 9.227 | +0.113 ± 0.149 | 7.885 / 7.772 |
| exploit2_hu | 7.540 | 8.477 | **+0.938 ± 0.148** | 9.460 / 8.523 |
| exploit_3 | 8.354 | 8.270 | -0.084 ± 0.176 | 6.993 / 7.073 |
| exploit2_3 | 7.142 | 7.430 | **+0.288 ± 0.182** | 8.573 / 7.940 |
| exploit (8-max) | 5.619 | 5.492 | **-0.126 ± 0.062** | 4.727 / 4.718 |
| exploit2 (8-max) | 5.754 | 5.710 | -0.044 ± 0.070 | 5.175 / 5.025 |
| elite | 4.681 | 4.676 | -0.005 ± 0.018 | |

On 200 seeds S1 no longer wins heads-up against exploiter 2 (8.48 to 8.52). The 8-max exploit cell is down while
exploiter 1's own points do not move: the points go to the pool seats (night bots) we meet in endgames. Located on
that cell (100 seeds, F 5.648):

| candidate | exploit (8-max) |
|---|---|
| P1: RP, `post_alive` 3 (= C14) | **-0.102 ± 0.088** |
| P0: RP, `post_alive` 2 | -0.031 ± 0.047 |

The heads-up pots of three-handed tables are where the balanced postflop gives up what F's reads take from weak seats;
true heads-up costs nothing measurable. `post_alive` stays 2 (the default) from here; S1 was stopped there.

### Two more solves: a counter to a wide opener, and small 3-bets

- **Node-locked counter** (`solve_short.py lock`, `tables/short_hu_lock.json`, 153 KB, 17 min on one worker): the
  heads-up tree with the small blind's first action locked to "open the top w of hands (preflop_rank), fold the rest"
  (how both exploiters play: 85-95% opens, never a limp), the rest solved; w = 0.75, 0.9, 1.0 at 12 depths 6-100 bb,
  400 iterations. Exploitability of the unlocked part 0.01-0.05 mbb/hand at 6-16 bb, 0.3-0.6 at 20-25, 0.8-1.2 at
  32-50, 1.1-1.8 at 70-100. At 20 bb against a 90% opener the big blind folds 0% (equilibrium 6%) and jams 36% (21%).
  Used (`short.wide_open`, off by default) as the big blind facing an open from a seat whose open rate from the
  button (F's profiler, `open_rate` late, smoothed toward 0.5 with 6) is at least the dial, with the nearest w.
- **Small 3-bets** (`solve_short.py sizes`, `tables/short_hu_t3.json`, 127 KB, 17 min): the tree rebuilt with the
  big blind's 3-bet at 2.2x and 2.75x the open, the small blind's first action and the big blind's answer to the open
  locked to the equilibrium of short_hu.json (the 3-bet's mass moved to the new size), the rest solved; 14 depths
  18-100 bb (below 18 bb a 3.5x 3-bet is a jam in the tree), 400 iterations, exploitability 0.15-0.41 mbb/hand. At
  40 bb the small blind's open range folds 0% to a 2.2x 3-bet and calls 94%, against 50% folds to the 3.5x one: the
  old mapping (every 3-bet onto the 3.5x node) folded half the range to exploiter 1's ~2.2x 3-bets. Used
  (`short.t3_sizes`, on whenever the small blind's preflop is routed) with a log-scale split between 2.2, 2.75 and 3.5.

### Dev batch 5 (code 632a59b, 200 seeds): both blinds' preflop with the new tables; the big blind alone

| candidate | exploit_hu | exploit_3 | exploit2_hu | exploit2_3 |
|---|---|---|---|---|
| S2d: R3, both roles, `steal_ftb` 0.42, `wide_open` 0.72 | **-0.345 ± 0.168** | **-0.112 ± 0.097** | **+1.087 ± 0.174** | **+0.315 ± 0.106** |

And on the 8-max exploit cell (100 seeds): P2 = R3 with the big blind's preflop only (`post_alive` 2) **-0.060 ± 0.059**;
P3 = the big blind's preflop alone (no postflop) +0.024 ± 0.045.

S2d wins heads-up against exploiter 2 (8.627 to 8.373) but the small blind's preflop still loses against exploiter 1.
Its lines (diagnostic seeds 9600-9659, 120 tables): the small 3-bets are now answered from their own table (357 times
at 2.2x, 40 at 2.75x; the open range calls them instead of folding half), the steal read turns most limps into opens
(exploiter 1 then folds 68% of its big blinds: +32.7 chips a steal), but the pots it calls (-47.9 chips a hand, 118) and
the 3-bet pots we call (-17.4, 326) lose: as the preflop raiser in a called pot our postflop does worse than F's against
this seat. The small blind's preflop stays off (`pre_roles` bb) in the candidates below.

Postflop against the pool's seats: the balanced postflop defends against bettors and gives up what F's reads take
from passive seats (P0 -0.031, P1 -0.102 above). S11's survey of heads-up bets per chance (flop and turn, leads and
stabs with the aggressor's bets): exploiter 2 0.84, exploiter 1 0.86, elite2 0.76, elite1 0.56, rival3 0.43, rival1
0.18, night's seats 0.34. So `short.post_aggr` (6e8b62f): the specialist plays a heads-up pot postflop only while the
opponent's rate (F's profiler counters, smoothed toward 0.4 with 4 chances) is at least the dial; S3a uses 0.5.

### S3a: the big blind's preflop and gated heads-up postflop (code 6e8b62f, 200 seeds)

S3a = `{"short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
"short.post_aggr": 0.5}`.

| cell | F | S3a | S3a - F | | exploiter F / S3a |
|---|---|---|---|---|---|
| exploit (8-max, 10/7/5/4/3/2/1/0) | 5.619 | 5.613 | -0.005 ± 0.035 | level | 4.727 / 4.725 |
| exploit_hu (10/7) | 9.115 | 9.213 | +0.098 ± 0.137 | level | 7.885 / 7.787 |
| exploit_3 (10/7/5) | 8.354 | 8.447 | **+0.093 ± 0.089** | UP | 6.993 / 6.898 |
| exploit2 (8-max) | 5.754 | 5.810 | **+0.055 ± 0.038** | UP | 5.175 / 5.106 |
| exploit2_hu | 7.540 | 8.470 | **+0.930 ± 0.145** | UP | 9.460 / 8.530 |
| exploit2_3 | 7.142 | 7.457 | **+0.315 ± 0.099** | UP | 8.573 / 8.258 |
| night (confirm) | 5.968 | 5.968 | -0.000 ± 0.012 | level | |
| elite | 4.681 | 4.679 | -0.003 ± 0.008 | level | |
| elite_night | 5.328 | 5.333 | +0.005 ± 0.011 | level | |
| mirror | 4.414 | 4.417 | +0.002 ± 0.009 | level | |

The gate takes the 8-max cost away (exploit -0.005, night -0.000) and keeps the gains against both exploiters short-
handed: no exploit cell down, four up. Heads-up against exploiter 2 it is level, not yet a win (8.47 to 8.53).

Finish positions (the simulator's places for our seat, 200 seeds x 8; F / S3a): reach heads-up and reach three-handed
are identical (the specialist plays only once two are left), so the changes are conversions:

| field | 1st | heads-up win | win from three-handed |
|---|---|---|---|
| night | 37.4% / 38.0% | 75.2% / 76.4% | 60.5% / 61.4% |
| elite | 11.6% / 11.1% | 51.7% / 49.4% | 30.6% / 29.2% |
| elite_night | 18.3% / 18.7% | 53.6% / 54.7% | 36.2% / 36.9% |
| mirror | 8.9% / 9.1% | 44.1% / 45.1% | 26.0% / 26.5% |

(F reaches heads-up at 21.5% of elite tables and 19.0% of mirror tables; under 8..1 a heads-up win is one point, so a
few points of heads-up win rate move a seat's mean by about 0.01.)

### Dropped: the counter to a wide opener, the gated button, and S3a itself (variants)

- S3b = S3a + `wide_open` 0.72: equal to S3a within noise on all six exploit cells (exploit2_hu +0.930 ± 0.155, the
  same mean; exploit_hu +0.083, exploit_3 +0.048, exploit2_3 +0.290, exploit2 +0.055, exploit -0.002). Off.
- S4 = R3 with both roles, `post_aggr` 0.5 and the button back to F against an over-folding big blind (`sb_ftb_max`
  0.4): exploit2_hu +0.885 ± 0.162, exploit_hu -0.150 ± 0.190, worse than S3a on both. Off.
- S3a + Z (Z = S11's dials, `r3.v3_bvb_prior` 0.15 and the probe / one-size postflop dials) on the exploit stage:
  exploit_hu **+0.285 ± 0.145**, exploit2_hu **+0.863 ± 0.159**, exploit_3 +0.110 ± 0.147, exploit2_3 **+0.362 ±
  0.141**, exploit2 +0.101 ± 0.117, exploit +0.100 ± 0.140: nothing down, they compose.
- Where S3a still trails exploiter 2 heads-up (diagnostic seeds 9700-9739, chips a hand by our role and whether the
  hand saw a flop; F / S3a): big blind preflop -13.9 / +8.3, big blind postflop -34.6 / -11.9, button postflop -22.7 /
  +19.6, button preflop -19.9 / -20.7. What is left is F's own button preflop (its opens folding to exploiter 2's
  3-bets, S11's leak), which the specialist's button fixes (S2b wins heads-up, 8.688 to 8.312) at a cost against
  exploiter 1.
- **S3a's variants** (realistic, the screen set's first 100 seeds): top_heavy **-0.381 ± 0.312**, antes_from_level_3
  **-0.018 ± 0.016**, fast_schedule +0.001 ± 0.013. Heads-up the specialist is chip-EV exact under any payout table
  (with two left the payout is linear in chips), so top-heavy points amplify a small heads-up loss against the
  realistic field's weaker bots: the big blind's equilibrium preflop played every opponent. And the trees have no
  antes, so with antes the big blind defends too tight.

The fix (b0b7dbc), both principled limits rather than tuned values:
- **no specialist preflop with antes** in the pot (unconditional: the trees have none);
- **`short.pre_open_min`**: the big blind's preflop is the specialist's only against a seat that opens at least that
  share of its buttons (F's profiler, open_rate late, smoothed toward 0.5 with 6). Survey at our heads-up big blind
  (diagnostic seeds 9750+, median of the read): exploiter 2 0.86, exploiter 1 0.85; night's bots 0.09-0.62 (rival3
  0.78), realistic's 0.12-0.58, elite and mirror builds 0.43-0.61. The value 0.65 sits between the exploiters and
  everyone else but rival 3: the equilibrium big blind defends against a wide opener, and F's big blind (its reads)
  plays the rest.

S5 = S3a + `short.pre_open_min` 0.65 (and the ante rule) is the candidate; S5 + Z the stacked one. Both run every
stage from here (code b0b7dbc).

## The recommended candidate: S5, full screen (code b0b7dbc, screen seeds 10000-10199)

S5 = `{"dials": {"short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
"short.post_aggr": 0.5, "short.pre_open_min": 0.65}}` on top of SHIP_DIALS (F as it ships). What it does: with two
players left, the big blind's preflop against a wide opener comes from the heads-up equilibrium tables, and every
heads-up pot postflop against a seat that bets into us is played by the balanced postflop; with dead seats or stations
alive, with antes, on twist tables, and everywhere else, F plays.

`tools/climb_accept.py --set screen --stages exploit,elite,confirm,guards,variants --variants
top_heavy,antes_from_level_3,fast_schedule --variant-seeds 100 --aim exploit` (through scratch `accept.py`, which only
pins F's cache key; every chunk was computed by the same cells): **ACCEPT**.

| stage | cell | F | S5 | S5 - F | | exploiter F / S5 |
|---|---|---|---|---|---|---|
| exploit | exploit (8-max, 10/7/5/4/3/2/1/0) | 5.619 | 5.608 | -0.010 ± 0.026 | level | 4.727 / 4.725 |
| | exploit_hu (10/7) | 9.115 | 9.220 | +0.105 ± 0.137 | level | 7.885 / 7.780 |
| | exploit_3 (10/7/5) | 8.354 | 8.419 | +0.065 ± 0.072 | level | 6.993 / 6.903 |
| | exploit2 (8-max) | 5.754 | 5.815 | **+0.061 ± 0.027** | UP | 5.175 / 5.107 |
| | exploit2_hu | 7.540 | 8.387 | **+0.848 ± 0.144** | UP | 9.460 / 8.613 |
| | exploit2_3 | 7.142 | 7.392 | **+0.250 ± 0.094** | UP | 8.573 / 8.298 |
| confirm | night | 5.968 | 5.970 | +0.002 ± 0.007 | level | |
| guards | night_hard | 5.486 | 5.493 | **+0.007 ± 0.006** | UP | |
| | realistic | 6.346 | 6.340 | -0.006 ± 0.007 | level | |
| | top | 5.035 | 5.036 | +0.001 ± 0.005 | level | |
| | night @10/7/5/4/3/2/1/0 | 6.149 | 6.134 | -0.014 ± 0.021 | level | |
| | night @50/25/12/6/3/2/1/1 | 24.406 | 24.366 | -0.040 ± 0.190 | level | |
| | night, doubling blinds | 5.830 | 5.826 | -0.004 ± 0.006 | level | |
| elite | elite | 4.681 | 4.679 | -0.002 ± 0.007 | level | |
| | elite_night | 5.328 | 5.334 | +0.006 ± 0.008 | level | |
| | mirror | 4.414 | 4.418 | +0.004 ± 0.008 | level | |
| variants | top_heavy (realistic, 100 seeds) | 27.175 | 27.117 | -0.058 ± 0.228 | level | |
| | antes_from_level_3 | 6.489 | 6.480 | -0.008 ± 0.010 | level | |
| | fast_schedule | 5.986 | 5.993 | +0.007 ± 0.007 | level | |

0 timeouts and 0 errors in every cell. The other 23 catalog variants play exactly as F by construction (the route
requires a plain hold'em table: hero.holdem_table, identity rank order, no straddle; tested on short_deck).

Heads-up win rates from the points (10 / 7): against exploiter 2, F 18.0% -> S5 46.2%; against exploiter 1, 70.5% ->
74.0%. Three-handed against exploiter 2, F 7.142 -> 7.392 points against its 8.573 -> 8.298.

Finish positions (our seat, 200 seeds x 8; F / S5; reach heads-up and three-handed are identical by construction):

| field | 1st | heads-up win | win from three-handed |
|---|---|---|---|
| elite | 11.6% / 11.3% | 51.7% / 50.3% | 30.6% / 29.7% |
| elite_night | 18.3% / 19.0% | 53.6% / 55.7% | 36.2% / 37.5% |
| mirror | 8.9% / 9.3% | 44.1% / 46.1% | 26.0% / 27.1% |
| night | 37.4% / 37.9% | 75.2% / 76.2% | 60.5% / 61.3% |
| night_hard | 28.3% / 28.7% | 72.0% / 73.0% | 53.0% / 53.7% |
| realistic | 50.4% / 49.7% | 83.0% / 81.7% | 74.0% / 72.9% |
| top | 18.8% / 19.1% | 60.0% / 60.9% | 41.3% / 41.8% |

Latency (tools/latency.py --hand-end --tables 20 --reps 3, per-call minimum, load 12.7-13.3, F / S5, µs):

| field | act p99 | act max | hand_end p99 | hand_end max | first decision mean |
|---|---|---|---|---|---|
| exploit2_hu (rules hu.json) | 70.3 / 86.1 | 96.2 / 112.3 | 53.2 / 58.3 | 58.1 / 65.6 | 82.3 / 91.5 |
| mirror | 106.2 / 101.5 | 8,202.9 / 150.0 | 102.1 / 101.3 | 197.3 / 136.0 | 105.5 / 104.0 |
| night | 100.3 / 102.8 | 129.3 / 139.5 | 99.4 / 102.0 | 136.3 / 137.9 | 105.5 / 105.7 |

(F's one 8.2 ms call on mirror is its own, in all three passes of that call: a host stall or F's slow path, not the
specialist's, which F does not build.) Nothing near
1 ms. Tables: short_hu.json 127 KB (33 KB zipped), short_hu_t3.json 127 KB (18 KB), short_hu_lock.json 153 KB (17 KB),
short_3.json 1.5 MB (1.16 MB; loaded only with `short.three`). tools/pack.py --slim: F 3.8 MB / 846 KB zip, with the
new tables 5.8 MB / 2.1 MB zip; import 0.29 s; the member builds in 48 ms (114 ms with the lock and three-handed tables).
## S5 stacked with Z (code b0b7dbc, screen seeds; climb_accept --aim exploit: ACCEPT)

S5 + Z = S5's dials plus S11's Z (`r3.v3_bvb_prior` 0.15, `hero.postflop.probe_from` 0.75, `probe_n` 2,
`probe_margin` 0.03, `probe_raise_tier` 5, `probe_bluff` 0.4, `balance_sizes`). Z alone against the same F (S11's log,
same base means): exploit_hu +0.113, exploit_3 +0.105, exploit2_hu +0.307, exploit2_3 +0.237, night -0.015, elite
+0.082, elite_night +0.064, mirror +0.002.

| cell | F | S5 + Z | - F | | exploiter F / S5+Z |
|---|---|---|---|---|---|
| exploit (8-max) | 5.619 | 5.733 | +0.115 ± 0.139 | level | 4.727 / 4.769 |
| exploit_hu | 9.115 | 9.385 | **+0.270 ± 0.139** | UP | 7.885 / 7.615 |
| exploit_3 | 8.354 | 8.498 | **+0.145 ± 0.144** | UP | 6.993 / 6.850 |
| exploit2 (8-max) | 5.754 | 5.856 | +0.102 ± 0.118 | level | 5.175 / 5.066 |
| exploit2_hu | 7.540 | 8.447 | **+0.907 ± 0.164** | UP | 9.460 / 8.553 |
| exploit2_3 | 7.142 | 7.498 | **+0.357 ± 0.135** | UP | 8.573 / 8.035 |
| night (confirm) | 5.968 | 5.951 | -0.017 ± 0.072 | level | |
| night_hard / realistic / top | | | -0.041 ± 0.074 / +0.000 ± 0.057 / -0.009 ± 0.074 | level | |
| night @10/7/5... / @50/25/12... / doubling | | | +0.023 ± 0.129 / +0.199 ± 0.769 / +0.017 ± 0.065 | level | |
| elite / elite_night / mirror | | | +0.077 ± 0.085 / +0.067 ± 0.067 / +0.013 ± 0.076 | level | |
| top_heavy / antes_from_level_3 / fast_schedule (100 seeds) | | | -0.091 ± 1.138 / -0.033 ± 0.088 / +0.018 ± 0.091 | level | |

They compose: against exploiter 1 heads-up S5 and Z add up (+0.105, +0.113 -> +0.270); against exploiter 2 heads-up
they overlap (+0.848, +0.307 -> +0.907: both reach the same postflop spots). Heads-up win rates: against exploiter 2
48.2% (F 18.0%), against exploiter 1 79.5% (F 70.5%). Finish positions (F / S5 + Z): elite 1st 11.6% / 12.4%, heads-up
win 51.7% / 51.1%, reaching heads-up 21.5% / 23.3% (Z's play before the endgame); elite_night 18.3% / 19.4%; mirror
8.9% / 9.1%, heads-up win 44.1% / 46.1%; night 37.4% / 36.4%, heads-up win 75.2% / 72.6%.

## Test suite (b0b7dbc)

Full suite at a1fc6c7 (the code before the last two gates, which touch only short.py's routing check; load 11-15):
1,218 passed, 9 skipped, 11 failed. Re-run alone: the drill on swap_holdem (two wall-clock timeouts), hybrid3's strict
timeout order, the kit-D round trip, both outside-field model-mode replays (Hero's seat diverged between the two runs;
it fails the same way on main's tree at that load) and slowbox's paired run pass; test_sim_bestiary's under-budget
check fails for a different bot on each run (five, then one: rob_mc), a wall-clock budget at load 12 from other runs.
At b0b7dbc: tests/test_s13_short.py (14), test_compose, test_ship, test_apicard, test_sim_mirror, test_s11_dials pass
(82). F plays identically behind the new dials (test_ship / test_compose replay it; seven S3a table digests are equal
at 6e8b62f and a1fc6c7).

## Summary

**The specialist.** `hyperion/strategy/short.py`, member `short` behind `short_route` (off by default; F builds no such
member). Preflop by lookup in tables our own CFR+ solver computed offline (`tools/solve_short.py`): heads-up chip-EV
tables at 26 depths 5-100 bb (exploitability 0.02-3.7 mbb/hand in the abstract game), three-handed ICM tables on 512
stack configurations (median 0.026 milli-prizes a hand), and two node-locked re-solves (a counter to a wide opener;
small 3-bets). Postflop in heads-up pots: one size per street and minimum-defence continuing by the hand's place in its
range. Deviations: back to F against dead seats and stations, preflop against a seat 3-betting far above equilibrium,
and the gates below.

**Recommended: S5** = `{"short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
"short.post_aggr": 0.5, "short.pre_open_min": 0.65}` (code b0b7dbc or later), ACCEPT on the screen set with --aim
exploit: up on exploit2 (+0.061), exploit2_hu (+0.848) and exploit2_3 (+0.250); every other exploit, confirm, guard,
elite and variant cell level (night +0.002 ± 0.007, night_hard +0.007 UP). With Z also ACCEPT, and up against
exploiter 1 too (exploit_hu +0.270, exploit_3 +0.145). For the coordinator's held-out confirmation: stages exploit,
confirm, guards, elite, variants (top_heavy, antes_from_level_3, fast_schedule are the only catalog entries it can
play).

Against the brief's targets:
1. **Win heads-up against exploiter 2: not met by an accepted candidate.** F 7.540 to 9.460 (18% of matches); S5
   8.387 to 8.613 (46%); S5 + Z 8.447 to 8.553 (48%). Two of the three named leaks are closed: facing its flop c-bet
   after calling its open, the big blind folds 41% (444 of 1,087; calls 36%, raises 23%) where F folds 67% (389 of 580;
   diagnostic seeds 9780-9819), and the layer's 0.33 bluff is gone from the heads-up pots the specialist plays (one
   size, the layer off); the light blind-vs-blind 4-bet is the button's, still F's. A candidate that
   wins (S2b: the specialist on both blinds, 8.688 to 8.312, 56%) loses to exploiter 1 heads-up (-0.383 ± 0.191) and
   three-handed (-0.127 ± 0.101).
2. **Not lose to exploiter 1: met.** S5 heads-up 9.220 to 7.780 (+0.105, level), three-handed 8.419 (+0.065, level),
   8-max level; with Z both up.
3. **First place at strong tables: barely moved, and night held.** 1st 11.6% -> 11.3% (elite), 18.3% -> 19.0%
   (elite_night), 8.9% -> 9.3% (mirror); heads-up win 51.7% -> 50.3%, 53.6% -> 55.7%, 44.1% -> 46.1%; night level.
   The specialist plays only once two are left (21% of elite tables, 19% of mirror), against wide openers preflop
   (the elite builds open 0.43-0.61 of buttons: F plays their big blinds) and postflop against bettors.

**What remains.**
- The button's preflop heads-up. The specialist's button wins against exploiter 2 and loses against exploiter 1, in
  the pots exploiter 1 calls or 3-bets (as the preflop raiser our postflop does worse than F's against it). F's own
  button against exploiter 2 is the last leak (-20.7 chips a hand on the diagnostic seeds: its opens folding to
  3-bets). Next: a read that separates the two from play (S11's probe read, 0.99 against 0.61, does), or a better
  postflop as the raiser in called pots.
- The three-handed preflop tables lose against both exploiters (C3, C7): the tree has no small-blind flat, no 4-bet
  from the big blind, and maps small 3-bets onto 3.5x; three-handed pots postflop are Hero's. The heads-up size
  re-solve (`sizes`) is the template. Off (`short.three`), the table kept (1.16 MB of the zip; 2.1 MB in all).
- Strong tables: the HU route reaches 20% of tables and under 8..1 a heads-up win is one point; a three-handed
  specialist that works is where first places at strong tables would come from.
- Postflop strength is Hero's nine tiers read as a percentile of random holdings (coarse); a finer per-board strength
  would sharpen minimum defence. The size read (S12's showdown histograms) is the natural deviation against a seat
  whose sizes name its hand (exploiter 2's 0.70 / 0.80), not tried.
- The gates' values (0.5 bets per chance, 0.65 opens) were set from surveys of the screen fields before measuring,
  not tuned; held-out sets decide.

# S13b: gate the specialist to exploiter-like opponents (branch climb/s13b-gate, from main e5ebfdb)

S5 on held-out H14 against batch 5 (main's F: D3's size read, Z3's S11 fixes with both hold'em gates, the strong route,
V-e): REJECT. Up exploit2_hu +0.443 ± 0.108, exploit2_3 +0.123 ± 0.059, exploit2 +0.021 ± 0.020; level against
exploiter 1, night, top, elite, elite_night, mirror; down night_hard -0.005 ± 0.005, realistic -0.005 ± 0.005,
top_heavy -0.247 ± 0.165, antes_from_level_3 -0.010 ± 0.007 (the last two on the realistic field). The coordinator's
read: it takes heads-up spots against ordinary bots, where F's exploitative play does better, and under a top-heavy
table first place is decided there.

## Where it plays on the ordinary fields (diagnostic seeds 3000-3399, never used before)

Paired F / S5 tables on realistic under top_heavy (60 seeds x 8; F as main ships): the per-table differences are far
too noisy to rank opponents (one heads-up decides 25+ points of 100), but they show who the specialist plays: of the 79
tables where it acted, LooseAggroStudent (256 postflop decisions in 32 tables), RivalBot (130 postflop, 70 preflop),
PushFoldBot (79 postflop), ChartTAG and TimeoutThenRecover. All of them pass S5's gates (postflop: bets into us at
least 0.5 of chances; preflop: opens at least 0.65 of buttons, which RivalBot reaches at its tail).

## The reads that separate the exploiters (survey.py, seeds 3100-3115 x 8 per field)

F's own profiler reads of the heads-up opponent at our decisions with two alive (every third hand), median [p10,
p90]; probe = its bets per chance in heads-up pots with us where the initiative is not its own (leads into us, stabs
after our check), (bets + 0.9) / (chances + 2); bet = the same with the aggressor's bets counted too, (bets + 1.6) /
(chances + 4); pfr from the profiler.

| field | opponent | probe | bet | pfr | open (button) |
|---|---|---|---|---|---|
| exploit2_hu | exploiter 2 | 0.86 [0.63, 0.93] | 0.73 [0.58, 0.80] | 0.53 [0.43, 0.60] | 0.86 [0.67, 0.92] |
| exploit2_3 | exploiter 2 | 0.88 [0.72, 0.93] | 0.69 [0.52, 0.78] | 0.42 [0.26, 0.53] | 0.74 [0.51, 0.88] |
| exploit2 (8-max) | exploiter 2 | 0.88 [0.63, 0.92] | 0.74 [0.60, 0.84] | 0.23 [0.17, 0.31] | 0.55 [0.41, 0.73] |
| exploit_hu | exploiter 1 | 0.45 [0.30, 0.63] | 0.68 [0.40, 0.80] | 0.68 [0.46, 0.76] | 0.85 [0.62, 0.92] |
| realistic | LooseAggroStudent | 0.54 [0.27, 0.72] | 0.58 [0.47, 0.82] | 0.24 [0.22, 0.30] | 0.50 |
| realistic | RivalBot | 0.31 [0.15, 0.47] | 0.41 [0.26, 0.51] | 0.25 [0.16, 0.30] | 0.56 |
| realistic | PushFoldBot | 0.45 [0.30, 0.72] | 0.51 [0.32, 0.60] | 0.14 | 0.36 |
| night_hard | naive | 0.77 [0.72, 0.84] | 0.70 [0.69, 0.76] | 0.07 [0.06, 0.08] | 0.14 |
| night_hard | rival3 | 0.31 [0.18, 0.47] | 0.36 | 0.37 | 0.79 |
| exploit2_3 | rival2 | 0.74 [0.54, 0.79] | 0.68 [0.54, 0.74] | 0.27 | 0.70 |
| mirror | Elite2Bot / ShipCopy | 0.52 / 0.45 (p90 0.70 / 0.78) | 0.61 / 0.52 | 0.21 / 0.25 | 0.53 / 0.72 |

Every other opponent surveyed (night, night_hard, realistic, top, elite, mirror and the exploit fields' pool seats) has
a probe median of 0.69 or less (timeout_burst three-handed 0.69 with pfr 0.07; the rest 0.63 or less). The
exploiters share postflop aggression (bet 0.68-0.74), and exploiter 2 alone leads and stabs into us nearly every time
(0.86-0.88 in all three formats, 8-max endgames included, where its preflop frequencies are diluted by the 8-max hands).
The one ordinary bot that probes that often (naive) never raises preflop. S5 gained nothing against exploiter 1, so
nothing is lost by leaving it to F.

**The gate (81afd88), thresholds fixed from this table before any screen:** every specialist decision needs the
heads-up opponent's probe >= 0.75 (below exploiter 2's medians, above every ordinary median but naive's and at rival2's
three-handed median), bet >= 0.60 (exploiter 2's p10 heads-up is 0.58, its medians 0.69-0.74), and pfr >= 0.15 (takes
out naive, 0.07-0.10; exploiter 2's 8-max p10 is 0.17): `short.like_probe` 0.75, `short.like_bet` 0.6,
`short.like_pfr` 0.15. S5's `post_aggr` 0.5 is implied by `like_bet` and dropped; `pre_open_min` 0.65 stays for the big
blind's preflop.

Check (gatecount.py, seeds 3300-3305 x 8): the specialist takes 61% of our heads-up decisions against exploiter 2 heads-
up and 56% three-handed (the rest are F's button preflop and the hands before its probe read crosses 0.75); 6 of 1,417
against exploiter 1; none of 1,068 on realistic and 3 of 730 on night_hard (rival3).

S6 = `{"short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
"short.pre_open_min": 0.65, "short.like_probe": 0.75, "short.like_bet": 0.6, "short.like_pfr": 0.15}`.

## S6 on the screen set against main's F (code 81afd88; climb_accept --aim exploit: ACCEPT)

Base = main's F (`{"dials": {}}`, e5ebfdb: batch 5's SHIP_DIALS), its chunks computed in a clean main worktree; the
candidate's in a detached worktree at 81afd88 (scratch `accept.py` pins only F's cache key to main's code version).
Stages exploit, confirm, guards, elite, variants (top_heavy, antes_from_level_3, fast_schedule, straddle at 200 seeds).

| stage | cell | F | S6 | S6 - F | | exploiter F / S6 |
|---|---|---|---|---|---|---|
| exploit | exploit (8-max, 10/7/5/4/3/2/1/0) | 5.839 | 5.840 | +0.001 ± 0.002 | level | 4.608 / 4.607 |
| | exploit_hu | 9.227 | 9.227 | +0.000 ± 0.029 | level | 7.772 / 7.772 |
| | exploit_3 | 8.458 | 8.448 | -0.010 ± 0.020 | level | 6.900 / 6.910 |
| | exploit2 (8-max) | 5.844 | 5.856 | +0.012 ± 0.018 | level | 5.086 / 5.073 |
| | exploit2_hu | 7.848 | 8.268 | **+0.420 ± 0.159** | UP | 9.152 / 8.732 |
| | exploit2_3 | 7.378 | 7.478 | **+0.100 ± 0.067** | UP | 8.165 / 8.065 |
| confirm | night | 5.972 | 5.972 | +0.000 ± 0.000 | level | |
| guards | night_hard | 5.499 | 5.499 | +0.001 ± 0.001 | level | |
| | realistic | 6.370 | 6.370 | +0.000 ± 0.000 | level | |
| | top | 5.058 | 5.059 | +0.001 ± 0.001 | level | |
| | night @10/7/5/4/3/2/1/0 | 6.199 | 6.198 | -0.002 ± 0.004 | level | |
| | night @50/25/12/6/3/2/1/1 | 24.699 | 24.684 | -0.016 ± 0.031 | level | |
| | night, doubling blinds | 5.848 | 5.848 | +0.000 ± 0.000 | level | |
| elite | elite | 4.865 | 4.866 | +0.000 ± 0.001 | level | |
| | elite_night | 5.422 | 5.421 | -0.000 ± 0.003 | level | |
| | mirror | 4.498 | 4.495 | -0.003 ± 0.003 | level | |
| variants | top_heavy (realistic) | 28.654 | 28.638 | -0.016 ± 0.031 | level | |
| | antes_from_level_3 | 6.496 | 6.496 | +0.000 ± 0.000 | level | |
| | fast_schedule | 6.122 | 6.122 | +0.000 ± 0.000 | level | |
| | straddle | 6.412 | 6.412 | +0.000 ± 0.000 | level | |

0 timeouts, 0 errors. The ordinary fields play almost exactly as F (realistic, night, antes and the doubling schedule
identical sample for sample); the exploiter 2 gains stay: heads-up 8.268 to 8.732 (42% of matches; F 28%), against
S5's +0.443 on H14 (S5 vs this F was not screened here), three-handed +0.100.

Who the gate still admits (gatecount.py, seeds 3300-3311 x 8): on mirror, Hybrid3X (102 of 186 heads-up decisions)
and the F copies (86 of 425): F-like bots probe often because the exploit layer stabs small into checks; on top,
HeroTight (20 of 216); on elite, rival3 (7 of 40). That is mirror's -0.003 ± 0.003, the one cell at its bound; at
400 held-out seeds it could show. Not re-tuned here (the thresholds were fixed before this run); a stricter probe
(0.85) or a size condition (the layer's stab is 0.33 pot, exploiter 2's 0.6) would take the copies out, unscreened.

Latency (latency.py --hand-end --reps 3 --tables 12, per-call minimum, load 4.6-4.8, F / S6, µs): exploit2_hu act
p99 72.0 / 84.8, max 85.5 / 108.3, hand_end p99 79.2 / 85.6; mirror act p99 107.1 / 107.7, max 122.8 / 145.5. Full
suite at 81afd88: 1,257 passed, 1 skipped.
