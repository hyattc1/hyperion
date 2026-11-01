# redteam5 build log: rival_bot.py

Frozen md5: `c0af68a4e0bd175fc6da59c386f8c3cb`, the same file as snap_m45.py. Frozen at T0+46.6 min; no edits after that.

## Approach
- **Evaluator.** The 5, 6 and 7-card evaluator uses an additive rank-multiset key (sum of 5^rank) into a dict of 73,775 entries built at import. Flushes are found from an additive suit counter and scored from a 13-bit mask table. One evaluation takes about 0.5 us. Import takes about 0.4 s.
- **Embedded preflop tables (generated in-session).**
  - Equity of each of the 169 starting-hand classes against 1 to 7 random hands (2,500 Monte Carlo samples each).
  - A hand ranking order.
  - Equity of each class against a hand drawn from the top 3%, 5%, 8%, 12%, 17%, 25%, 35%, 50%, 70% or 100% of hands (1,500 samples each).
- **Preflop.**
  - **Unopened pot, effective stack of 14 BB or less** (18 BB or less with two or fewer players behind): push or fold. The bot compares the ICM value of shoving and folding, with each player behind modelled as calling with a top-c% range (c is about 1.6/stack in BB, widened for loose seats).
  - **Unopened pot, deeper:** position-based open ranges with a 2.2 to 3 BB raise. Short-handed ranges are wider (heads-up 75%, three-handed 48 to 58%).
  - **Facing a raise:** the raiser's range is estimated from that seat's preflop raise rate at this table, narrowed for 3-bets and widened for loose seats and short all-ins.
    - Big pots use ICM to choose between jam, call and fold.
    - Deep pots use a 3-bet range and an equity-versus-pot-odds call.
- **Postflop.**
  - A time-boxed Monte Carlo (130 us budget, about 50 to 150 samples) samples each opponent's hand from their estimated preflop range.
  - When an opponent bets, each sample is weighted by how strong that hand is on the current board: high card, weak pair, top pair or better, two pair, trips or better.
  - How hard the weighting bites depends on the seat's aggression rate. It is harder on the river and much harder when they raise over our bet.
  - The bot bets for value against thresholds that depend on the number of opponents, with thinner and larger bets against seats that rarely fold. It bluffs rarely, only heads-up against seats that fold often, and shoves when the stack-to-pot ratio is low.
  - Calls are equity against pot odds plus a margin (+0.05 on the river). Big calls use ICM.
- **ICM and a bust penalty (the largest gain).**
  - A fast approximation of Harville ICM over 10/7/5/4/3/2/1/0: 2 + 3·P(1st) + P(2nd) + the linear part, using pairwise finish order.
  - Busting costs an extra skill-edge penalty of E = 8 · (hands left / cap) · (alive − 2)/6. This avoids early coin-flips against maniacs and random bots, who bust anyway.
  - This term alone moved the mixed field from about 6.1 to about 6.4 and the tight field from about 4.7 to about 5.0.
- **Robustness.**
  - Every input field is defended; act() is wrapped in try/except with a legal fallback.
  - Raise amounts are clamped to the range given by min and max of min_raise and max_raise, which handles swapped values.
  - gc.freeze() runs at import.

## Minute marks
- m0–4: evaluator and preflop equity precompute. A forked helper wrote engine.py (full 8-max SNG simulator with ICM at the 200-hand cap) and opps.py.
- m7: first full bot. harness and fuzz clean. About 6.1 in the mixed field.
- m15 (snap_m15): mark-array Monte Carlo, jam equity measured against the calling range, narrower ranges when facing a raise over our bet, wider ranges for loose seats.
- m15–21: diagnostics showed that 97 of 181 busts happened in hands 1–25, on deep-stacked preflop all-ins. That led to the bust penalty (P_EDGE), tested at 0, 1, 2, 3.5, 5 and 8.
- m21–30 (snap_m30): parameter sweep. Opens, call margin, value threshold, bluffing, push depth and narrowing were all flat within noise. Shove EV now counts limpers as callers. Thin value against sticky seats added.
- m30–45 (snap_m45, final): a chip-flow breakdown showed river calls were the biggest postflop leak. Fixes: finer range-weight classes, a river margin, wider short-handed opening and defending, MC budget cut to 130 us, E = 8.

## Test results (mean finish points per table, 8 seats, average 4.0; SE about 0.08 at 1,000 tables)
Fields (rival plus 7):
- mix = Random, RandomSmall, Station, Maniac, Nit, TAG, LAG
- soft = Random, RandomSmall, Station, Maniac, Random, TAG, Nit
- tight = Nit, TAG, LAG, TAG, Nit, LAG, Pusher
- self = snap_m15, v5 (an early version with no bust penalty), TAG, LAG, Nit, Pusher, Random

| version | mix | soft | tight | self |
|---|---|---|---|---|
| first build (m7) | 6.07–6.22 | – | 4.73 | – |
| snap_m15 | 6.21 | 6.59 | 4.67 | – |
| snap_m30 | 6.42 | 6.96 | – | ~5.05–5.23 |
| snap_m45 = final | 6.57 | 7.07 | 5.01–5.10 | 5.14–5.29 |

One 800-table run of the mixed field with engine.py: rival 6.65, Nit 6.11, TAG 5.89, LAG 5.42, Random 2.31, RandomSmall 2.20, Maniac 1.96, Station 1.46. No exceptions or illegal actions from any bot.

In the self field, the Nit opponent scored 5.41 against our 5.20 in one 600-table run. Pure survival is very strong under this payout table and the ICM-scored cap.

## Final checks (on a shared machine with load average about 54 on 8 cores)
- harness: exceptions=0, illegal=0, fold_when_check_legal=0. act() median about 151 us. p99 was 661, 398, 2544 and 3170 us across four runs (load average 53–57).
- The 20 us control bot had p99 of 54–60 us in the same minutes, with max over 3 ms.
- On the lightly loaded machine earlier, p99 was 230–475 us.
- fuzz: exceptions=0, illegal=0.

## Known weaknesses
- **Latency under load.** The Monte Carlo is time-boxed, but about 150 us of compute per postflop decision is exposed to OS preemption. On a heavily oversubscribed host, p99 can exceed 1 ms, and a timeout is a fold.
- **Opponent model.** It only uses the actions the bot sees, which stop once it folds. It ignores showdowns. A random bot's raise frequency (about 35–40%) is partly read as a range rather than as noise.
- **Postflop strategy.** It is heuristic: equity thresholds, no check-raises or slow plays, little river bluffing. A thinking opponent can exploit the predictable bet-means-value pattern.
- **ICM.** It is an approximation (pairwise finish order). All-in EV assumes one caller and ignores side pots and overcalls.
- **Bust penalty.** E was tuned against these test fields. Against a field of tight solvers the extra caution may give up some steal and call EV, though the tight field still improved.
- **Blind posts in history.** If they appear in a format other than leading raise or call entries equal to the blinds, the preflop stats would be slightly contaminated.
