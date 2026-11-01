# Mid-phase aggression pass: running log

Builder: aggression pass (2026-11-01). Brief: build and sweep Hero's mid-phase preflop aggression with rival 2 as
the target (docs/decisions.md "Deep Hero pass"). Every measurement and screen lands here as it finishes; the
decisions entry "Mid-phase aggression pass" summarises it at the end.

## Step 1: action frequencies by phase (HEAD f9481d3 = d917c45 strategy code)

Scratch script `scratch/aggr/freq.py` (not committed): every seat is wrapped, every decision is logged with its
street, and each preflop or flop decision is classified from the deciding seat's own observation. 120 duplicate
seeds x 8 rotations per field, seed 7, measure mode (no forced folds), 5 workers. Levels 1-3 = hands 0-74
(20-50 bb blinds on 2,000 chips), levels 4-8 = hands 75-199. Definitions:
- *open*: first in (no raise, no limper), any raise; position by players behind (SB 1, BTN 2, CO 3, MP 4-5,
  EP 6-7). Open % includes open-shoves. The 10-15 bb column splits first-in spots at that effective depth into
  non-all-in raises and shoves.
- *3-bet / re-shove*: the seat's first action facing exactly one non-all-in raise; a re-shove is a raise of 95%+ of
  its stack. Blinds vs other seats.
- *fold to 3-bet / re-shove*: the opener facing one re-raise (not all-in / all-in).
- *BB defence*: the big blind facing one open with no callers; the share that calls or raises, raises in brackets.
- *c-bet*: heads-up flop, the last preflop raiser's first flop action with no bet yet; *fold to c-bet*: the other
  player facing that bet. No all-in preflop.
- *net bb* per action = the seat's chip result in that hand, in big blinds, whatever happened later.
- *postflop no-showdown*: hands that reached the flop and ended without a showdown, the seat's result in bb.

| field, phase | bot | open % SB/BTN/CO/MP/EP | open size bb | 10-15 bb: raise / shove % | 3-bet % blinds / other | re-shove % blinds / other | fold to 3-bet / re-shove % | BB defence % (3-bet) | c-bet / fold to c-bet % (HU raised) | re-shoves at 10-25 bb per seat (net bb) | open-shoves per seat (net bb) | postflop no-showdown bb/seat, HU aggressor / HU caller |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| top2 L1-3 | hero | 76/74/42/27/19 | 2.50 | 38 / 0 | 3 / 3 | 0 / 0 | 89 / 65 | 43 (3) | 57 / 75 | 0.04 (+0.2) | 0.10 (+0.0) | +2.4 / -6.9 |
| top2 L1-3 | rival1 | 68/52/35/24/16 | 2.47 | 29 / 7 | 3 / 3 | 1 / 0 | 83 / 76 | 41 (5) | 100 / 49 | 0.18 (+0.5) | 0.21 (+0.2) | +6.5 / -3.2 |
| top2 L1-3 | rival2 | 51/41/32/24/15 | 2.53 | 5 / 10 | 6 / 4 | 2 / 1 | 52 / 80 | 50 (10) | 68 / 49 | 0.21 (+0.4) | 0.18 (+0.2) | +6.1 / +0.4 |
| top2 L4-8 | hero | 69/65/36/24/15 | 2.26 | 50 / 0 | 2 / 1 | 5 / 5 | 93 / 77 | 26 (7) | 55 / 78 | 0.18 (+0.5) | 2.51 (+2.3) | +0.9 / -1.9 |
| top2 L4-8 | rival1 | 64/45/34/27/18 | 2.19 | 33 / 18 | 3 / 2 | 13 / 5 | 93 / 81 | 36 (18) | 100 / 44 | 1.51 (+3.1) | 6.31 (+4.5) | +2.8 / -0.9 |
| top2 L4-8 | rival2 | 41/28/24/19/13 | 2.37 | 4 / 21 | 2 / 1 | 21 / 9 | 82 / 85 | 44 (25) | 62 / 49 | 2.58 (+5.1) | 5.49 (+4.4) | +1.6 / -0.2 |
| realistic L1-3 | hero | 73/74/43/28/18 | 2.50 | 46 / 0 | 4 / 4 | 1 / 0 | 91 / 56 | 43 (4) | 56 / 74 | 0.04 (+0.3) | 0.10 (+0.1) | -1.2 / -7.6 |
| realistic L1-3 | rival1 | 51/36/28/20/12 | 2.47 | 32 / 10 | 3 / 4 | 1 / 0 | 81 / 44 | 41 (5) | 100 / 44 | 0.15 (+0.5) | 0.18 (+0.2) | +1.9 / -3.9 |
| realistic L4-8 | hero | 73/71/38/28/20 | 2.25 | 54 / 0 | 2 / 2 | 4 / 5 | 94 / 75 | 30 (6) | 56 / 71 | 0.14 (+0.3) | 2.61 (+2.2) | +0.1 / -3.9 |
| realistic L4-8 | rival1 | 57/32/27/22/0 | 2.26 | 31 / 21 | 3 / 2 | 11 / 4 | 93 / 60 | 36 (15) | 99 / 54 | 1.20 (+2.4) | 4.75 (+3.3) | +2.0 / -1.6 |

Points in these runs (measure mode, 960 tables): top2 Hero 4.42, rival1 4.79, rival2 4.97; realistic Hero 5.75,
rival1 5.74.

**What the table says.**
1. Hero does not open too little. Its first-in open rate is the widest of the three at every position in both
   phases and both fields (top2 levels 4-8: 20.3 opens per seat, rival 1 18.6, rival 2 13.2). Steal widening
   (candidate a) and a wider mid-phase open chart (b as briefed) push the wrong way.
2. Re-shoves at 10-25 bb are the largest gap. In levels 4-8 on top2 rival 2 re-shoves over a single open 2.58 times
   per seat for +5.1 bb, rival 1 1.51 times for +3.1 bb, Hero 0.18 times for +0.5 bb. From the blinds rival 2
   re-shoves 21% of the opens it faces, rival 1 13%, Hero 5%. Above 10 bb Hero re-raises only its top ~3-6%
   (`three_bet_frac`), and its 3-bets become shoves through `shove_instead_frac`; nothing prices fold equity.
3. Hero's 10-15 bb first-in play is raise-or-fold where both rivals shove. At 10-15 bb effective Hero raises 50% of
   first-in spots to 2.25 bb and shoves 0%; rival 2 raises 4% and shoves 21%, rival 1 raises 33% and shoves 18%.
   Hero then folds 77% of the re-shoves it faces, and faces them 4.0 times per seat on top2 (rival 2 1.6). Its
   opens that end preflop with a loss cost -8.7 bb per seat in levels 4-8 on top2 (rival 2 -3.7). Open-shoves:
   Hero 2.5 per seat (+2.3 bb, all at <= 10 bb), rivals 5.5-6.3 (+4.4 bb).
4. BB defence: flats are the same (Hero 19%, rival 2 18%); the gap is all re-raises (Hero 7%, rival 2 25%, rival 1
   18%), which is item 2 seen from the big blind.
5. Postflop heads-up, where Hero called preflop, it loses in pots that end without a showdown: top2 -6.9 / -1.9
   bb per seat (levels 1-3 / 4-8) against rival 2's +0.4 / -0.2; realistic -7.6 / -3.9 against rival 1's -3.9 /
   -1.6. Hero folds 71-78% to a heads-up c-bet (rivals 44-54%) and c-bets 55-57% (rival 1 99%, rival 2 62-68%).
   Its flop call needs equity >= pot odds + 0.15 from a tier proxy, so middle pair (0.32) folds to a third-pot
   bet. Some of this loss buys Hero's better showdown results (deep pass: Hero +1,699 chips at showdown, rival 1
   +1,465).

**Ranking (Hero's deficit per seat in levels 4-8, top2 vs rival 2 / realistic vs rival 1, in bb; a level 4-8 bb
is ~7x the chips of a level 1-3 bb):** re-shoves at 10-25 bb ~4.6 / ~2.1; postflop heads-up no-showdown ~2.4 /
~4.3 (plus 6.5 / 6 bb at levels 1-3); 10-15 bb open-shoves instead of raise-folds ~2.1 / ~1.1; calling
re-shoves (Hero faces 2.5x as many as rival 2). Levers in that order: (c) mid-depth re-shoves priced by the solved
re-shove table with the opener's observed open rate as w; (b) reinterpreted as the first-in shove zone by
effective stack (push/fold first-in to ~13-15 bb, by position); (e) heads-up c-bet and fold-to-c-bet by reads;
(d) the per-seat switch to the per-opportunity re-shove read. (a) is built last, if at all: the table says
Hero already steals more than either rival.

## Step 2: levers built (all Config keys, off by default, tests in tests/test_strategy_aggression.py)

| commit | lever | keys |
|---|---|---|
| 0b6289b | (c) mid-depth re-shoves: facing one open with no callers above push/fold depth, shove the solved re-shove set (multiway table, 4-25 bb) when the ICM gate passes; the opener's width w from its observed first-in open rate (profiler, > 12 bb, late / early position class) instead of the seat prior x PFR ratio | `preflop.reshove_mid_bb` (+ `_max_behind`, `_opener_max_behind`, `_max_open_bb`, `_min_w`), `pushfold.reshove_w_observed`, `reshove_w_n0` |
| 75d484d | (b, as the measurement reframed it) the first-in shove zone: unopened pots stay push/fold (solved first-in table + ICM gate) above threshold_bb up to a depth, deeper from late seats; the rest fold or keep the chart's raise | `pushfold.fi_threshold_bb`, `fi_late_threshold_bb`, `fi_late_behind`, `fi_rest_open` |
| f82b5c8 | (d) per-seat switch to the per-opportunity re-shove read once a seat's smoothed re-shove rate at <= 25 bb passes a threshold; first-in shoves keep the per-hand read | `preflop.shove_ctx_auto`, `_n`, `_prior` |
| 1f56fa2 | (e) heads-up raised pots: lower call margin against a small flop c-bet from the preflop raiser (optionally only against frequent c-bettors); c-bet bluffs scaled by the caller's observed fold-to-c-bet | `postflop.vs_cbet_margin`, `vs_cbet_max_pot`, `vs_cbet_min_rate`, `cbet_ftc_read`, `cbet_ftc_prior`, `cbet_ftc_max` |

Profiler re-shove rates at <= 25 bb per "facing one open" spot, 60 tables (`scratch/aggr/rsrate.py`): top2 rival2 0.183,
rival1 0.129, hero_tight 0.076, loose_aggro 0.056, tag 0.036, pushfold 0.024; realistic rival1 0.152, the rest <= 0.05.
Per table (smoothed with 8 spots at 0.06) rival 2's 90th percentile is 0.21 and rival 1's 0.15: one table rarely
tells them apart.

## Step 3: screens

Method: `tools/sweep.py` from a clean worktree of the commit under test, duplicate deals, strict, seed 7, 5 workers,
paired deltas against the screen's base; `scratch/aggr/analyze.py` adds Hero-minus-rival gaps and the lone rival's
delta in the "rival + 7 Heroes" field. Every screen's base sets `panic_after` 1,000,000: during the first launch
another session ran a dozen busy-loop processes (load average 26 on 8 cores), and Hero's SafeBot went to panic
mode (cheap path: no reads, no ICM) in hundreds of tables, which switches the levers off mid-table and measures
the host. That launch was discarded. The final run uses the shipped defaults (panic on).

### Screen S1 (stage A): every lever, four fields, 160 seeds (commit 1f56fa2)

Base = defaults (panic off). Cells: Hero's paired delta ± 95%; the second block is the change in the Hero-minus-rival
gap (rival1 / rival2), the base row being the gap itself. Settings were queued one after another and a drill's
table generation loaded the host during the second half: Hero's strict-mode timeouts per cell rose from 36-105
(base and the first five settings) to 400-1,600 (from `shove_ctx_auto=0.12` on), and rival 2 timed out more too.
That biases the later rows against Hero on realistic and for it against rival 2; `tools/sweep.py` now queues
settings side by side (8e8a78c).

```
Δhero (paired vs base) ± 95%; in r2h7/r1h7: Δ of the lone rival (lower is better for Hero)
setting                                  realistic             top            top2            h7r2
base                                  5.605 ±0.108    4.565 ±0.109    4.349 ±0.120    3.636 ±0.107
preflop.reshove_mid_bb=20            +0.004 ±0.090   +0.004 ±0.104   -0.004 ±0.113   -0.046 ±0.130
preflop.reshove_mid_bb=25            -0.007 ±0.092   +0.001 ±0.091   +0.063 ±0.115   +0.025 ±0.122
pushfold.reshove_w_observed=true     -0.114 ±0.094   -0.012 ±0.093   +0.090 ±0.117   -0.024 ±0.128
pushfold.fi_threshold_bb=13          -0.121 ±0.102   -0.023 ±0.096   +0.021 ±0.130   +0.089 ±0.124
preflop.shove_ctx_auto=0.001         -0.042 ±0.096   -0.078 ±0.100   -0.003 ±0.126   -0.001 ±0.126
preflop.shove_ctx_auto=0.12          -0.087 ±0.101   -0.096 ±0.094   +0.027 ±0.130   -0.021 ±0.136
postflop.vs_cbet_margin=0.05         -0.053 ±0.097   -0.035 ±0.109   +0.042 ±0.129   +0.130 ±0.135
postflop.cbet_ftc_read=true          -0.032 ±0.097   -0.098 ±0.107   +0.061 ±0.122   -0.077 ±0.135
rmid25_late                          -0.126 ±0.098   -0.039 ±0.105   +0.058 ±0.125   +0.099 ±0.123
rmid25_wobs                          -0.044 ±0.096   -0.044 ±0.098   +0.034 ±0.117   +0.017 ±0.125
fi13_l16                             -0.187 ±0.093   -0.118 ±0.103   +0.051 ±0.121   +0.117 ±0.136
fi13_rest                            -0.134 ±0.103   -0.046 ±0.120   +0.050 ±0.121   -0.086 ±0.117

Hero - rival paired, relative to base (Δ of the gap) for rival1 / rival2 where present; base row = the gap itself
base                                         -0.09     -0.19/-0.36     -0.41/-0.64           -0.99
preflop.reshove_mid_bb=20                    +0.04     +0.03/-0.09     +0.01/+0.03           -0.05
preflop.reshove_mid_bb=25                    +0.00     +0.03/-0.07     +0.20/+0.02           +0.03
pushfold.reshove_w_observed=true             -0.06     -0.03/+0.01     +0.12/+0.17           -0.03
pushfold.fi_threshold_bb=13                  -0.17     -0.06/-0.11     +0.14/+0.04           +0.10
preflop.shove_ctx_auto=0.001                 -0.05     -0.08/-0.11     -0.02/+0.01           -0.00
preflop.shove_ctx_auto=0.12                  -0.06     -0.14/-0.18     +0.07/+0.04           -0.02
postflop.vs_cbet_margin=0.05                 -0.03     -0.04/-0.09     +0.05/+0.01           +0.15
postflop.cbet_ftc_read=true                  -0.01     -0.11/-0.28     +0.15/+0.02           -0.09
rmid25_late                                  -0.14     -0.04/-0.05     +0.04/+0.16           +0.11
rmid25_wobs                                  -0.00     -0.07/-0.05     +0.12/+0.04           +0.02
fi13_l16                                     -0.18     -0.18/-0.20     +0.02/+0.05           +0.13
```
Readings. Nothing is outside noise on realistic or top. On top2 and against seven rival 2s most levers point up
(+0.02 to +0.13) and most point down on realistic. Shoving more (first-in zone `fi_threshold_bb` 13: realistic
-0.12; with 16 from late seats -0.19) repeats the deep pass's finding: the Monte Carlo bots call shoves at 1.6-5x
Nash. The per-seat re-shove read (`shove_ctx_auto`) costs top -0.08/-0.10 like the deep pass's per-opportunity read.
Mid-depth re-shoves are neutral on realistic and top (`reshove_mid_bb` 20: +0.004 / +0.004; 25: -0.007 / +0.001) and
close the top2 gap to rival 1 by +0.20. A frequency check (`freq.py`, top2, 80 seeds, measure mode) confirms the lever
works as built: with `reshove_mid_bb` 25 and the observed width, Hero's re-shoves at 10-25 bb in levels 4-8 rise from
0.18 to 0.88 per seat (blinds 5% -> 11% of opens faced, big-blind 3-bets 7% -> 16%), each netting about +1.8 bb, like
rival 2's +2.1, but rival 2 still makes 2.58 per seat: the solved table and Hero's ICM gate stop at a third of its
volume.

## Add-on (coordinator): Hero without action history (c38259e)

Drill 6 found the reference adapters passed no `obs.history`, so Hero read every raised pot as unopened (3.2
points against 5.9). Now, when the history is empty, or preflop holds no raise although a bet is above the blind
(straddle-aware), `HeroCore.act` rebuilds this street's raises from the bets (one RAISE per bet level, credited to
the first seat in acting order; a short all-in below the top level is a call) for `Spot` and the modules, and
postflop uses its own preflop aggression for the c-bet decision. The profiler keeps the kit's own history (it counts
only what it sees) and stops counting hands with no visible action as dealt. Nothing changes when the history is
present (`HeroCore.inferred` counts the decisions that used the fallback). Realistic, 100 seeds x 8 rotations,
measure mode, Hero's seat stripped of history in act() and hand_end(): full 5.756 ± 0.116, stripped 5.505 ± 0.119,
paired -0.251 ± 0.108 (drill 6: stripped 3.21; the adapter's rebuild 5.20 against 5.50). What is left is the
opponent model, which sees nothing. Test: `tests/test_strategy_no_history.py` (paired table run, 3,301 inferred
decisions, 5.92 full vs 5.75 stripped).

### Screen S2 (stage B): survivors on all eight fields, 200 seeds (commit 8e8a78c, settings queued side by side)

Hero's timeouts are now level across settings (13-461 per cell, the same spread in every row). Fields: h7r1 / h7r2 =
Hero + 7 rival1 / rival2; r2h7 = rival2 + 7 Heroes, where the cell is rival 2's own delta (lower is better for Hero).

```
Δhero (paired vs base) ± 95%; in r2h7/r1h7: Δ of the lone rival (lower is better for Hero)
setting                                  realistic             top            top2            h7r1            h7r2            r2h7            base          strong
base                                  5.560 ±0.093    4.488 ±0.101    4.392 ±0.104    4.451 ±0.094    3.642 ±0.091    5.102 ±0.106    6.800 ±0.066    5.141 ±0.102
postflop.vs_cbet_margin=0.05         +0.013 ±0.094   +0.083 ±0.093   +0.029 ±0.102   +0.051 ±0.059   +0.051 ±0.112   -0.008 ±0.126   +0.006 ±0.010   +0.014 ±0.087
preflop.reshove_mid_bb=25            +0.025 ±0.085   +0.010 ±0.092   +0.068 ±0.099   +0.052 ±0.049   -0.023 ±0.109   -0.006 ±0.116   +0.004 ±0.017   -0.002 ±0.057
preflop.reshove_threat=1.0           -0.063 ±0.085   +0.108 ±0.081   +0.027 ±0.107   +0.012 ±0.034   +0.016 ±0.114   -0.048 ±0.116   -0.000 ±0.006   +0.028 ±0.028
preflop.reshove_mid_bb=20            -0.001 ±0.088   +0.071 ±0.087   +0.034 ±0.102   +0.050 ±0.046   -0.016 ±0.112   -0.042 ±0.123   -0.002 ±0.014   +0.016 ±0.056
rmid25_wobs                          +0.006 ±0.082   +0.066 ±0.092   +0.047 ±0.101   +0.050 ±0.053   +0.041 ±0.115   +0.069 ±0.112   +0.003 ±0.017   -0.024 ±0.066
rmid25_thr_vscb                      +0.047 ±0.093   +0.172 ±0.100   +0.067 ±0.097   +0.132 ±0.066   +0.081 ±0.112   -0.129 ±0.112   +0.012 ±0.020   -0.013 ±0.089

Hero - rival paired, relative to base (Δ of the gap) for rival1 / rival2 where present; base row = the gap itself
base                                         -0.09     -0.27/-0.51     -0.28/-0.63           -0.06           -0.98                                                
postflop.vs_cbet_margin=0.05                 +0.02     +0.13/+0.10     -0.01/+0.06           +0.06           +0.06                                                
preflop.reshove_mid_bb=25                    +0.05     +0.08/-0.04     +0.11/+0.08           +0.06           -0.03                                                
preflop.reshove_threat=1.0                   -0.06     +0.10/+0.21     -0.07/+0.03           +0.01           +0.02                                                
preflop.reshove_mid_bb=20                    +0.02     +0.12/+0.08     +0.04/+0.06           +0.06           -0.02                                                
rmid25_wobs                                  -0.01     +0.11/+0.08     +0.00/+0.08           +0.06           +0.05                                                
rmid25_thr_vscb                              +0.10     +0.25/+0.20     +0.09/+0.11           +0.15           +0.09                                                

timeouts (hero tmo, all seats), safe_err
base                                         246/0           104/0           110/0            69/0            75/0           402/0            40/0            58/0
postflop.vs_cbet_margin=0.05                 276/0            74/0            87/0            38/0            74/0           434/0            13/0            53/0
```
Readings. With the load spread evenly the picture is cleaner and mostly positive. `reshove_mid_bb` 25 passes the
shipping rule on its own (realistic +0.025, top +0.010, base / strong +0.004 / -0.002, Hero + 7 rival1 +0.052 ± 0.049
outside noise). `vs_cbet_margin` 0.05 is >= 0 on every Hero field but nothing is outside noise. `reshove_threat` 1.0
alone fails realistic (-0.063). The three together are the best row: top +0.172 ± 0.100 and Hero + 7 rival1 +0.132 ±
0.066 outside noise, realistic +0.047, top2 +0.067, rival 2 among seven Heroes -0.129, base / strong +0.012 / -0.013.
Next screen: the increments (the passing pair, then the threat read, then the exploitative re-shove pricing) with
the payout tables the coordinator asked for.

### Screen S3 (stage C): the increments, ten fields incl. two payout tables, 200 seeds (commit f238f5b)

Settings on top of the default base: rv = `reshove_mid_bb` 25 + `vs_cbet_margin` 0.05; rvt = rv + `reshove_threat` 1.0;
rvx = rv + `reshove_exploit`; rvtx = all four. real_p10 / real_th = the realistic field with payouts 10/7/5/4/3/2/1/0
and 50/25/12/6/3/2/1/1 (the coordinator's robustness check; points on those scales).

```
Δhero (paired vs base) ± 95%; in r2h7/r1h7: Δ of the lone rival (lower is better for Hero)
setting                                  realistic             top            top2            h7r1            h7r2            r2h7            base          strong        real_p10         real_th
rv                                   +0.083 ±0.081   +0.140 ±0.097   +0.047 ±0.111   +0.118 ±0.059   +0.152 ±0.113   -0.034 ±0.116   +0.014 ±0.020   -0.012 ±0.089   +0.221 ±0.147   +2.189 ±0.992
rvx                                  +0.027 ±0.089   +0.128 ±0.097   +0.036 ±0.108   +0.190 ±0.071   +0.255 ±0.111   -0.041 ±0.121   -0.031 ±0.027   -0.138 ±0.102   +0.294 ±0.159   +2.674 ±1.044
rvt                                  +0.068 ±0.087   +0.161 ±0.092   +0.127 ±0.104   +0.126 ±0.065   +0.211 ±0.109   -0.101 ±0.121   +0.009 ±0.021   -0.014 ±0.085   +0.192 ±0.147   +1.820 ±0.979
rvtx                                 +0.104 ±0.091   +0.071 ±0.101   +0.054 ±0.106   +0.184 ±0.070   +0.265 ±0.118   -0.066 ±0.128   -0.028 ±0.027   -0.135 ±0.099   +0.309 ±0.153   +2.630 ±1.002
base                                  5.511 ±0.093    4.486 ±0.102    4.416 ±0.102    4.453 ±0.094    3.581 ±0.094    5.136 ±0.104    6.801 ±0.066    5.145 ±0.100    5.368 ±0.138   18.724 ±0.862

Hero - rival paired, relative to base (Δ of the gap) for rival1 / rival2 where present; base row = the gap itself
rv                                           +0.13     +0.23/+0.17     +0.14/+0.08           +0.13           +0.17                                                           +0.32           +3.50
rvx                                          +0.12     +0.29/+0.14     +0.13/+0.09           +0.22           +0.29                                                           +0.49           +4.12
rvt                                          +0.13     +0.23/+0.26     +0.28/+0.16           +0.14           +0.24                                                           +0.24           +2.85
rvtx                                         +0.22     +0.22/+0.07     +0.20/+0.09           +0.21           +0.30                                                           +0.47           +3.94
base                                         -0.15     -0.27/-0.53     -0.30/-0.60           -0.05           -1.05                                                           -0.46           -4.38

timeouts (hero tmo, all seats), safe_err
rv                                           148/0           194/0           147/0            66/0           223/0           835/0            74/0            40/0            39/0           100/0
rvx                                          121/0           174/0           149/0            73/0           202/0           791/0            69/0            42/0            50/0            69/0
rvt                                          108/0           237/0           148/0            66/0           199/0           875/0            95/0            30/0            48/0            86/0
rvtx                                         144/0           208/0           128/0            56/0           254/0           858/0            43/0            36/0            34/0           103/0
base                                         126/0           193/0           154/0            78/0           222/0           773/0            74/0            34/0            47/0            83/0
```
**Decision.** rv ships (f349380): realistic +0.083 ± 0.081 and top +0.140 ± 0.097, Hero + 7 rival1 +0.118 ± 0.059 and
Hero + 7 rival2 +0.152 ± 0.113 outside noise, base +0.014, strong -0.012, and it gains under both payout tables
(+0.221 ± 0.147, +2.19 ± 0.99). The exploitative re-shove price gains most in the mirrors (Hero + 7 rival2 +0.26) but
fails strong (-0.138, -0.135 with the threat read): there the other Hero copies take the same config and re-shove
into each other. The re-shove-threat read helps exactly the rooms it was built for (top2 +0.08 and rival 2 among
seven Heroes -0.07 on top of rv) but its own increment is below zero on realistic again (-0.015 here, -0.063 alone
in S2), so by the shipping rule it stays opt-in: `preflop.reshove_threat` 1.0 for a room of frequent re-shovers.
