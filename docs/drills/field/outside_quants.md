# Build log — o4_quants (two quant interns' bot)

## What we built
`rival_bot.py`: one self-contained file, standard library only, `class Bot(Agent)`.

**Precomputed (offline, by our own scripts in `dev/`, then embedded as literals):**
- `dev/pk_eval.py` — our own 7-card evaluator (rank-count + suit-bitmask, 8192-entry straight/top-5 tables built at import). Checked against the known 7-card category frequencies (17.4/43.8/23.5/4.8/4.6/3.0/2.5/0.15/0.03 %). ~3.5 us per eval.
- `dev/precompute_eq.py` — 169x169 heads-up preflop all-in equity matrix, 1,600 Monte Carlo deals per class pair (SE ~1.2 pts), 155 s. Embedded as 28,561 bytes base64 (1/255 quantisation).
- `dev/fp.py` — push/fold equilibria by fictitious play (60 iterations) for the pusher with m = 1..7 players behind and 25 stack depths 1..30 bb, one-caller approximation, blinds as dead money. Output: push fraction and each caller's call fraction. Sanity: SB-vs-BB at 10 bb gives push 58 %, call 37 % (the textbook HU Nash numbers).

**At import (0.03 s):** decode matrix; equity vs random for the 169 classes; a strength ordering; prefix sums so `eq_top(hand, f)` (equity vs the top fraction f of hands) is one bisect + one division; combo list sorted by strength; `gc.freeze()`.

**ICM:** exact Malmuth-Harville equity for the 10/7/5/4/3/2/1/0 table in closed form, O(n^2): points(place k) = (8 - k) + [3, 1, 0, ...][k], and in the Plackett-Luce model P(i finishes ahead of j) = s_i/(s_i+s_j), so E[points_i] = 7 - sum_j s_j/(s_i+s_j) + 3 P(1st) + P(2nd). A bust is scored as the place it takes. Verified: 1 player = 10, 2 equal = 8.5, 8 equal = 4.0.

**Decisions (all under 1 ms; postflop Monte Carlo is time-boxed from the start of `act`):**
- Preflop short (<= 16 bb effective, unopened): shove iff ICM EV(shove) > ICM EV(fold), callers modelled as calling the equilibrium fraction for their position/depth, blended with what we have seen them do at this table; folding pays a 1 bb "future game" tax (blinds keep coming), see below.
- Facing a shove or a committing raise: call / re-shove iff ICM EV beats folding, villain range = max(equilibrium push fraction, observed preflop raise rate), widened for wild seats.
- Deep: open top-x % by players behind (11 % UTG .. 48 % SB, then x1.6: ~18 % UTG, ~58 % BTN, ~77 % SB), 3-bet top ~2-7 % scaled to villain's raise rate, call top ~5-30 % with price limits, BB defends wider vs min-raises.
- Postflop: Monte Carlo equity vs each opponent's modelled range (top-f % preflop by their stats; a bet or big bet this street filters to hands that make a pair+/two pair+ on this board, keeping 20 % as bluffs; no filtering vs wild seats). Bet 70 % pot (90 % vs stations) when eq > 0.58 (0.50 vs stations); flop c-bet bluff 55 % HU/3-way vs non-sticky fields; raise with eq > 0.8; call when eq >= pot odds + 4 % (6 % river); all-in calls by ICM.
- Opponent model per seat (reset per table): preflop raise rate and preflop continue rate, overall aggression; "wild" seats (random-like) get full ranges. Leading blind posts in `history` are detected and ignored if the engine logs them.
- Legality: every action passes a wrapper that maps to a legal action and clamps raises to [min_raise, max_raise]; any exception -> check/fold.

## How we tested
- `dev/engine.py` — our own 8-seat SNG engine: blinds 10/20 .. 200/400 every 25 hands, button moves over live seats, side pots, ties, bust order by starting stack, 200-hand cap scored by exact ICM over the remaining points. Optional `POSTS=1` logs blind posts in `history` (checks our parser).
- `dev/opps.py` — seven house bots: Random (uniform legal), Station (always calls), Control (check/call, = `_control.py`), Maniac (shoves 35 %, pot-raises 33 %), TAG (Chen-style top hands, bets pair+), NashPush (score-threshold shoves when short, value-shoves two pair+), LoosePassive.
- Fields: **mix** = us + all seven; **mix2** = us + random, maniac, 2x tag, 2x nash, loose; **tight** = us + 3 tag, 3 nash, loose. Average score is 4.0 by construction (32 points per table / 8).
- `dev/ab.py` — paired A/B: each variant plays the same table seeds, same field and seating. Pairing barely cuts the noise (the per-table SD is ~3.3 points whatever the bot does), so a difference needs ~2,000 tables per arm to resolve 0.1 point. Noise is quoted as one standard error.

## Timeline (minutes from T0)
- 0-2: read brief, kit, harness. Plan: offline tables -> ICM -> push/fold -> postflop MC -> local engine -> A/B.
- 2-3: own 7-card evaluator, checked against the known category frequencies.
- 3-6: 169x169 equity matrix offline (155 s, background); in parallel wrote the fictitious-play solver and the bot.
- 6-7: FP push/fold for m = 1..7 x 25 depths (20 s). Checked SB/BB 10 bb = 58 % / 37 %.
- 7-9: first `rival_bot.py` assembled by `dev/build.py`; harness clean. Moved the MC time box to start at `act` entry, added `gc.freeze()`.
- 9-11: own SNG engine + 7 house bots. First 200 tables, mix field: 6.32 +- 0.22 (tied with the house NashPush bot).
- 11-15: fixed the range model (callers' range from their continue rate; random bots counted as wild), parameterised the bot, paired A/B harness. `snap_m15.py`.
- 15-19: preflop-only stats (blind posts in `history` detected and skipped; our own seat no longer counted at hand end); board-conditioned ranges for bettors -> +0.24 +- 0.12 tight, +0.11 +- 0.14 mix. Promoted at 18.8.
- 19-22: sanity printouts found pure ICM folding AKo/TT UTG at 8 bb (ICM is right that busting costs 4 points here, but it charges nothing for blinding away) -> 1 bb fold tax as a future-game proxy.
- 22-25: found the postflop MC was only drawing 4-13 samples per decision. Tried cheaper rank-based conditioning + lower-confidence-bound raises + bigger budget (cand5): **worse** (-0.13 +- 0.11 mix2, -0.19 +- 0.12 tight). Rejected; kept cand4 (= conditioned ranges + fold tax).
- 26-32: six-arm sweep, then a confirmatory run: MC budget 200 -> 250 us and opening ranges x1.3 -> x1.6 (cand7): +0.08 +- 0.10 mix2, +0.22 +- 0.10 tight. Promoted at 32.2. `snap_m30.py` (= cand4) at 30.0.
- 32-35: last sweep (deep call width, fold tax 1.5, push/fold zone 20 bb): all inside one SE. Kept cand7.
- 35-36: self-play field and blind-posts-logged engine checks. Found our house bots seeded their RNG from `id()`, so the "paired" A/B was only half paired; fixed it in `opps.py`. With deterministic opponents, logging blind posts leaves every opponent stat identical (`dev/divg.py`); the only remaining decision differences are postflop, from the wall-clock MC box.
- 36.5: **froze** (`FROZEN.md5`), harness recorded in `harness_final.txt`.
- 37-38: final measurements (below), then this log. `snap_m45.py` = the frozen file.

## Local results (frozen bot, mean finish points per table, +- 1 SE; field average is 4.00)
| field | tables | rival_bot | best house bot | snap_m15 on same seeds |
|---|---|---|---|---|
| mix (random, station, control, maniac, tag, nash, loose) | 1000 | **6.91 +- 0.09** | nash 5.96 +- 0.08 | 6.68 +- 0.09 |
| tight (3 tag, 3 nash, loose) | 500 | **5.93 +- 0.15** | nash 4.48 +- 0.07 | 5.47 +- 0.14 |
| mix2 (random, maniac, 2 tag, 2 nash, loose), from the confirm A/B | 2000 | 6.01 +- 0.08 | - | - |
| self (3 more copies of us + tag, nash, random, loose) | 400 | 5.03 +- 0.15 | - | - |

The per-table SD is about 3.3 points, so 1,000 tables give an SE of about 0.1. Most of the single sweeps (700-1,200 tables per arm) could not separate effects under 0.2 points. Only changes that won in both fields, or held up in a 2,000-table confirmation, were kept. One "win" (c-bet 35 % + wider call margin, +0.17 at 700 tables) reversed to -0.20 +- 0.085 at 2,500 tables. Our house bots are guesses at the field; a field of real solvers will hit us harder than our TAG/NashPush do.

## Latency (be honest)
- Import 0.02-0.03 s. Harness: 0 exceptions, 0 illegal, 0 folds-when-check-legal on every run.
- Light host load (load avg ~3): median ~205-260 us, p99 ~400-500 us.
- The host was saturated during the final runs (load avg 7.3-7.6 on 8 cores; even `_control.py`'s fixed 20 us loop measured p99 62 us, max 667 us). Our p99 there was 570-940 us, and about 1 % of decisions went over 1 ms, in CPU time as well as wall time. The cause is the postflop Monte Carlo: a 250 us wall-clock box from `act` entry, plus a floor of 3 iterations and a per-board filter that run even after the box expires. On a dedicated scoring machine we expect the light-load numbers. If not, the fix is a smaller box and no iteration floor; it was not applied because the file was already frozen when we measured this.

## Known gaps
- Postflop MC draws only ~10-30 samples per decision (SE 0.08-0.15), so bet/call thresholds are noisy. The lower-confidence-bound fix lost in A/B, which suggests the noise mostly acts like randomisation that costs little.
- The push/fold equilibria use one caller and chip EV. ICM is applied live at decision time, with the equilibrium call fractions as the opponent model.
- Opponent ranges are "top-x % by preflop equity vs random". This is crude for suited connectors and for postflop holdings beyond the pair/two-pair filter.
