# rival_bot build log

Blind build, done only inside this folder. The bot is `rival_bot.py`, pure standard library,
476 KB. A cold import takes about 0.003-0.06 s. `build.py` generates it from `bot_src.py` and embeds
the tables computed under `pre/`.

## What the bot is

The bot looks up offline-solved tables and then picks the highest-EV action. Every decision that
risks the stack is scored in finish points under ICM.

**Offline work (C in `pre/pc.c`, Python in `pre/*.py`):**
- 7-card evaluator in C. It computes:
  - equity of each of the 169 hand classes against 1-7 random hands (100k trials each);
  - a 169x169 heads-up equity matrix (20k trials per pair).
- Equity of each class against a top-f% range: `EQF`, 169 x 50 bins.
- Heads-up push/fold Nash, solved by fictitious play, for depths 1-30 BB in 0.5 BB steps
  (`PUSHF`/`CALLF`). It matches the known charts: at 10 BB the small blind pushes 58% and the
  big blind calls 37%.
- `CALLFR[r][req]`: how often a caller continues against a top-r% shove when they need `req`
  equity. This is the callers' best response that the bot's own shove EV uses.
- Postflop equity vs random (E1) from a feature-bucket table. The feature is the made hand
  relative to the board, plus kicker, draws (flush, nut flush, OESD, gutshot, backdoor) and board
  texture, with 4 fallback levels. It was fit on 3.5M random situations whose E1 the C code
  computed (Monte Carlo with 400 runouts on flop and turn, exact enumeration on the river).
  Holdout RMSE: flop 0.032, turn 0.043, river 0.059.
- Range-vs-range tables per street (`EQR`): the mean equity of a hand with a given E1 against
  an opponent range made of the top-f percentile of hands on the same board. Built from 1500
  boards per street, each with every combo's E1 and 4000 sampled matchups.

**Runtime (about 25 µs median, 76 µs intrinsic worst case):**
- **ICM.** Harville ICM in closed form. For each player, E[place] is the sum of pairwise
  probabilities s_j/(s_i+s_j), and P(2nd) is O(n), so the points for 10/7/5/4/3/2/1/0 cost O(n)
  per scenario. The final value is a blend 1.3·ICM - 0.3·chip-linear, which is a little more
  risk-averse than ICM; A/B tests below show why.
- **Preflop.**
  - Open-raise ranges depend on how many players are left to act (scaled by `OPENSCALE` = 1.1).
  - At 14 BB or less, unopened pots are push/fold. The bot compares the ICM EV of shoving against
    folding. Each caller is modelled from `CALLFR` against our perceived range (Nash push % ×
    position factor), and is tighter when more players remain behind them.
  - Facing a raise, the raiser's range comes from that seat's observed open, 3-bet and push
    frequencies, blended with priors and widened when the seat looks "wild" (random). Shove-sized
    raises use the Nash push range for the shover's position.
  - All-in decisions (call, shove, re-shove) are exact ICM EV comparisons. Deep stacks use
    3-bet/call thresholds relative to the raiser's range, a little mixed 3-bet bluffing, and a
    big-blind defence that accounts for equity realization.
- **Postflop.**
  - The bot computes E1, then each opponent's range fraction f. f starts from the preflop range
    (f_pre^0.55) and is narrowed by that seat's actions this hand: a bet keeps the share of hands
    the seat observably bets with, a raise its raise share, a call its non-fold share. Wild seats
    are barely narrowed.
  - Equity is the product over opponents of EQR(E1, f).
  - When checked to, it scores check against bets of 0.35, 0.7 and 1.1 pot and all-in. Each bet's
    fold probability comes from per-seat fold-to-bet stats scaled by size, and the equity if
    called is computed against the narrowed calling range. A softmax mix between near-equal sizes
    keeps sizing from leaking strength, and some marginal bluffs are randomly skipped.
  - When facing a bet, it scores fold, call and raise. Stack-committing calls are decided in ICM
    points. Semi-bluff raises on flop and turn are allowed only when the EV calculation says so.
- **Opponent model.** Per seat and per table: VPIP, open-raise, cold-call, 3-bet, big-raise rate,
  postflop bet, fold, call and raise frequencies. History is parsed incrementally, with streets
  segmented by "seat acts again without an intervening raise". The parser copes with blind posts
  appearing in history, missing or `None` history, a partial or `None` `hand_end` result, flat
  `(seat, kind, amt)` entries, and upper-case or 'bet'/'allin' action names.
- **Safety.**
  - Every path goes through a legalizer: raises are clamped to [min_raise, max_raise] and are
    always ints; illegal kinds fall back to call, check or fold; it never folds when check is
    legal.
  - Exceptions are caught and the bot plays the safe action.
  - GC is paused during `act()` and restored afterwards, so a collection the host triggers never
    lands inside our millisecond.

## Simulator and opponents (built here)
- `engine.py` is an 8-seat NLHE sit-and-go with side pots, moving button, the blind schedule from
  the brief every 25 hands, the 200-hand cap, and 10/7/5/4/3/2/1/0 points with exact Harville ICM
  at the cap. Decks are seeded per hand. It measures act() latency.
- `opps.py`:
  - RandomBot (uniform legal action, raise size uniform);
  - StationBot;
  - TAGBot (positional chart, category-based postflop);
  - LAGBot (TAG ×2.2 loose);
  - PushFoldBot (stack-depth jam/fold);
  - EquityBot (Monte Carlo equity vs random, pot odds), with an "aggr" variant and a loose TAG.
- Strong opponents built from this bot:
  - earlier versions of it (v2, v3, v6j, v7, v9b);
  - `v_aggro` (looser opens, more bluffs, no bluff skipping);
  - `v_nit` (tight, rarely bluffs);
  - `v_3bettor` (an exploiter that 3-bets 30% of hands light).
- Robustness: `test_formats.py` covers blinds in history, no history, 6-handed, heads-up, odd
  blind levels and flat or upper-case history. In all of them: 0 errors, 0 illegal actions,
  0 internal exceptions.

## Results (final bot, mean finish points per table ± SE; 1st place = 10)
| field (8 distinct bots per table) | N | rival | best other |
|---|---|---|---|
| mixed: 2×random, station, TAG, LAG, pushfold, equity | 2000 | **6.16 ± 0.06** | TAG 5.62, pushfold 5.26, LAG 5.15, equity 4.84, random 1.9, station 1.2 |
| tough: TAG, equity, pushfold, LAG, equity-aggr, TAG-loose, own v2 | 2000 | **5.29 ± 0.07** | v2 4.94, TAG 4.46, pushfold 4.16 |
| gauntlet: own v9b, aggro-variant, nit-variant, TAG, pushfold, equity, LAG | 2000 | **4.82 ± 0.07** | v9b 4.75, aggro 4.68, nit 4.61, pushfold 3.98, TAG 3.87 |
| exploit: own v7, 2×light-3-bettor, aggro, TAG, pushfold, LAG | 2000 | 4.56 ± 0.07 | aggro 4.60 (tie), v7 4.44, 3-bettors 4.39/4.40 |
| self-play: 4× final vs 4× v2 | 1500 | 4.03 avg | v2 3.97 avg |

The final build was re-checked on the mixed and tough fields (N=1000): 6.16 and 5.20, 1st in
both. In the tough field the bot busts rarely: of 600 tables it finished 8th 12 times and 7th
32 times (TAG: 51 and 58).

Heads-up endgame (`hu.py`: 40 BB start, blinds up every 10 hands, N=300 each), win rate:

| opponent | win rate |
|---|---|
| TAG | 84% |
| station | 84% |
| equity | 74% |
| random | 74% |
| pushfold | 71% |
| LAG | 65% |
| own older version | 54% |
| aggro variant | 49% |

A/B log. Most of these were run in the same table as the previous version over 1500 tables. The
difference has an SE of about 0.10-0.15, because the two copies are negatively correlated.

| change | outcome |
|---|---|
| v1 → v2: tighter 4-bet/5-bet wars, stricter "wild" detection | tough 4.57 → 5.32, mixed 5.59 → 5.96. v1 shoved 99 and A5o in 100 BB raise wars. |
| v3: callers modelled as a best response to our perceived shove range (`CALLFR`), position-aware push ranges for shovers, more river training data | +0.19 tough, +0.00 h2h. Kept. |
| v4: softmax mixing between bet sizes | Neutral (+0.01 / -0.08). Kept for unexploitability. |
| ICM weight 0.6 (less risk-averse) | -0.35 weak, -0.13 tough. Rejected. |
| ICM weight 1.3 | +0.21 weak, +0.08 tough. Adopted. |
| ICM weight 1.6 vs 1.3 | -0.10, -0.17. Rejected. |
| Equity-realization factors for preflop and postflop calls | Neutral to small plus. Kept. |
| Adaptive 3-bet defence widening with the opponent's 3-bet frequency | -0.22 in both fields. Reverted. The cause was a counting bias in the facing-raise stats, now fixed (v9: +0.08 exploit, +0.02 tough). |
| Decaying the ICM risk premium toward the hand cap | -0.01 / -0.08. Reverted. |
| EV-gated semi-bluff raises on flop and turn (v11) | +0.20 tough, +0.01 exploit. Kept. |
| Postflop range exponent 0.7, fold prior 0.30, open scale 0.85 / 1.15 / 1.3 | All within noise. |

## Latency
- Intrinsic cost, taking the minimum of 5 timings per observation over 4000 harness observations:
  median 25 µs, p99 48 µs, max 76 µs.
- `python3 harness.py rival_bot`: 0 exceptions, 0 illegal actions, 0 folds when check was
  legal. Mean about 37 µs, p99 about 100 µs.
- The reported max on this machine (load average 8-11 on 8 cores, shared) ranges from 0.8 to
  4 ms. Those spikes are scheduler preemption, not bot work: the same observation re-timed runs
  in 25-35 µs. Under this load about 0.02-0.3% of simulated decisions exceeded 1 ms. On an idle
  machine the max should sit at about 0.1 ms.
- Python 3.10 and 3.12 both pass.

## With more time
- **Exact river hand strength.** Enumerate the 91 opponent rank pairs with flush corrections,
  roughly 300 µs, in place of the feature table (RMSE 0.059). It needs a time guard.
- **Better postflop range model.** Replace the percentile-plus-narrowing model with ranges
  propagated card by card (weights over the 1326 combos), or with small precomputed river
  subgames. Also learn the preflop→postflop mapping from data rather than the f^0.55 heuristic.
- **Multiway push/fold.** Solve multiway push/fold Nash with ICM offline (3-8 players by stack
  shape) in place of the HU Nash × position factor. Add future-game simulation so the bot values
  blinding down.
- **Opponent modelling.** Use showdown cards when `hand_end` provides them; add a Bayesian random-
  vs-solver classifier.
- **Better evaluation.** Run a bigger, more diverse evaluation (around 10k tables per field) to
  resolve the many ±0.1 parameter questions. Train an exploiter against the frozen bot (best
  response by self-play) to measure exploitability directly.
