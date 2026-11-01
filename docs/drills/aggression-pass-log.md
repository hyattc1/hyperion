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
