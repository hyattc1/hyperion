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
