# Build log: rival_bot.py (team "o1_veterans")

Frozen at minute 38 (2290 s after T0). md5 `bffa539c16eabb4836c4518c5ba1a660` (FROZEN.md5).
Pure stdlib Python, import ~0.01 s, act() mean ~15-20 us, p99 <100 us (harness). No exceptions or
illegal actions in the harness, and none raised inside the unguarded `_act` over 20,000 random harness
observations. `act()` also wraps everything in try/except and falls back to check/fold.

## What we built
- **Hand evaluator** (own code): rank counts plus per-suit bitmasks, with 8192-entry straight and
  top-5 lookup tables built at import. About 3 us per 7-card hand; checked against the known 7-card
  category frequencies.
- **Preflop tables** (own offline Monte Carlo in `precompute.py`, embedded as constants): equity of
  each of the 169 hand classes vs a random hand (20k samples each), the combo percentile ranking
  that follows from it, and equity vs top-k% ranges for k = 3,6,10,15,20,30,40,55,75,100%
  (2.5k samples each).
- **ICM**: `util()` is an O(n) closed form for the 10/7/5/4/3/2/1/0 payout:
  points = opponents outlasted + [top 2] + 2*[1st]. P(outlast j) = s/(s+s_j), and P(top 2) is
  Harville. This turned out to match exact Malmuth-Harville ICM to the decimal (checked against the
  engine's recursive ICM).
- **Preflop**:
  - Push/fold at <=13 bb effective. Shove if E[ICM] beats folding, given each live opponent's
    call probability (Nash-like prior 2.8/eff_bb blended with observed continue-vs-raise; dead seats
    call 0) and equity vs that calling range.
  - Calling an all-in, or a big committing raise: ICM call with a margin of 0.15 points. The
    raiser's range is estimated from their PFR*0.9 plus a term for loose VPIP.
  - Re-shove over a single open at <=25 bb, with fold equity: the opener continues 45% of their
    range.
  - Deep stacks: open ranges by number of players behind (70% SB ... 17.5% UTG). Opens widen
    toward any-two when the seats behind fold to raises a lot or are dead. Iso-raise station
    limpers for value. 3-bet when equity vs the estimated range is >=0.60. Cheap calls, set-mining
    and BB defense by pot odds.
- **Postflop**: a heuristic strength level (0-5), built from the made hand and whether the hole
  cards improve the board, plus flush/open-ended draws.
  - Value-bet levels 3+ (bigger vs check/call stations). Thin value bets heads-up.
  - Semi-bluff strong draws. C-bet heads-up as the preflop raiser vs seats that fold.
  - Calls are pot-odds thresholds by level, wider vs high-aggression seats (random/maniac).
  - Stab any pot where every opponent is a dead/timeout seat.
- **Seat model** (per table, from `history`): fold/check/call/raise counts, preflop VPIP/PFR,
  fold-vs-raise, and a "dead" flag (only folds/checks after >=6 actions).

## Local test rig (own code)
- `engine.py`: 8-max SNG with side pots, blinds 10/20 rising every 25 hands, a 200-hand cap with
  Harville ICM, a chip-conservation assert and latency tracking.
- Paired comparisons: same seat permutation and deck stream per table index for both heroes.
- Opponents (`opponents.py`):
  - random-legal, check/call station, always-fold (timeout), maniac (shoves 45%), pusher (simple
    push/fold), TAG, tag2 (looser), nit, limper.
  - mcto: TAG preflop, times out (folds) every postflop decision.
  - Earlier versions of our own bot (`mod:`).
- Lineups:
  - default: random, station, folder, maniac, pusher, tag, nit
  - strong: tag2, pusher, nit, mod:base0, mod:v_ot, random, folder
  - loose (held out, never tuned on): random, random2, station, limper, tag, pusher, maniac
- Noise: one table's points have SD ~3.3, so 600-800 paired tables give SE ~0.12-0.18 on a
  difference. We only adopted changes at about 2 SE, or with the same sign on both lineups.

## Timeline (minutes from T0)
- m0: T0. Read BRIEF/kit/harness.
- m1: evaluator; sanity check on 7-card category frequencies.
- m3: offline precompute of the preflop equity tables.
- m4-5: bot v0 passes harness (0 exceptions / 0 illegal, ~13 us mean).
- m6-8: local engine and opponent pool. First result: hero 6.33 pts/table vs a 4.0 average. Rare
  >1 ms spikes hit every bot, including trivial ones. Re-timing the slow observations gives ~10 us,
  so the spikes are host noise.
- m9: CALL_MARGIN sweep (400 paired):
  - +0.08 beat 0.0 by 0.26 (se .18); -0.08 lost 0.35.
  - 0.15 beat 0.08 by 0.31 (se .18); 0.30 fell back. Adopted 0.15.
- m10: PF_DEPTH 10/13/17: no difference (se .17).
- m11 (800 paired):
  - Opening ranges x1.35: +0.28 (se .125). x0.7: -0.17.
  - RR_MULT 3.6: -0.25. RR 1.8, 3-bet equity 0.55 and CALL_PRIOR 2.0: noise.
- m12:
  - Station sizing, iso-raises, and counting limpers as shove callers: -0.11 (se .13, noise; kept).
  - Opens x1.3 again: +0.30 (se .13) default, +0.10 (se .12) loose. Adopted.
- m14.6: snap_m15.py.
- m15:
  - BB defense edge 0.08/0.15: noise; adopted 0.12 on theory.
  - Strong lineup: hero 5.14 vs base0 4.95, pusher 4.90.
- m16-18: strong lineup: PF_DEPTH 18 -0.34 (se .14); call margin, shove margin, call prior and
  reshove all noise.
- **m19: found the big bug.** `util()` returned 0 on a bust: it ignored places already secured
  (and that a heads-up bust is 2nd), and gave no credit for busting an opponent. Push ranges were
  absurdly tight (BTN 10 bb ~5%, heads-up SB ~15%). After the fix util equals exact ICM:
  **+0.63 (se .15) default and +0.58 (se .16) strong**.
- m21-24 (600+600 paired, after the fix):
  - CALL_MARGIN 0: worse (+.33/+.18). CALL_MARGIN 0.30: mixed.
  - CALL_PRIOR 1.8/4.0: noise. PF_DEPTH 10: mixed. PF_DEPTH 16: -.09/-.05.
  - Kept 0.15 / 2.8 / 13.
- m25: raiser range from PFR (+ a loose-VPIP term) instead of agg*2.6: -0.54 (se .17) and -0.12
  (se .18), i.e. better.
- m26: RR_PF 0.9 better again (-.29/-.24). RR_VP 0: mixed. m27: RR_PF 0.7 worse (+.09/+.31).
  Kept 0.9.
- m30: snap_m30.py.
- m29-30:
  - Re-shove with fold equity (no gain before the ICM fix): now -0.21/-0.41, i.e. better.
    Adopted.
  - PF_DEPTH 16 and no c-bet: both worse.
- m31-33: re-shove depth 18/35, opener continue 0.30/0.60, opener commitment adjustment: noise or
  worse. Kept 25 / 0.45 / off.
- m33-34: validation of base12 vs base7 (post-fix, pre-RR):
  - Held-out loose lineup: base12 better by 0.67 (se .165).
  - Self-play lineup: base12 better by 0.17 (se .21).
  - GC check: 0 collections during act(), and the spikes were identical with gc disabled, so they
    come from host contention (loadavg ~7 on 8 cores).
- m35-36: bet fraction 1.0, open 2.8 bb, open 2.0 bb: noise or worse. Kept.
- m37: "stab vs postflop folders": +.10/-.14, then +.11 (se .15) on a lineup with a postflop-timeout
  bot. Left out.
- m38: **froze** base13 (behaviour identical to the validated base12). Ran harness_final.txt and
  wrote FROZEN.md5.
- m39: final evaluation (below).
- m45 (2704 s): snap_m45.py saved, an identical copy of the frozen file. No bot changes after m38.

## Final local results (frozen bot; points/table, a random seat averages 4.0)
| lineup | tables | frozen bot | snap_m15 | paired diff (frozen - m15) |
|---|---|---|---|---|
| default | 600 | 7.37 (se .13) | 6.46 (se .12) | +0.91 (se .15) |
| strong (old versions of us as opponents) | 600 | 6.24 (se .14) | 5.06 (se .13) | +1.19 (se .18) |
| loose (held out) | 600 | 7.28 (se .11) | 6.84 (se .11) | +0.44 (se .15) |
| mcto + base10 + pusher/tag2/nit/random/folder | 500 | 6.22 (se .15) | - | base10 (our m30 version) 5.99 |

Caveats:
- The local field is our own invention. The real field's call and shove ranges will differ, and
  the seat model adapts to them.
- The >1 ms tail on this shared host (about 0.03-0.1% of our decisions, and some for every bot)
  is preemption, not our code. The bot's own work is ~15 us mean.
- Postflop play is a simple heuristic. Most chips move preflop in this format.
