# rival_bot notebook

Deliverable: `rival_bot.py` (standard library only, ~31 KB, imports in 0.04 s). Everything else in this
directory is my own tooling: `pokercore.py` (evaluator shared by the tools), `precompute.py` (preflop
equity tables), `sim.py` (8-max SNG engine with ICM scoring), `opponents.py` (sparring field),
`test_eval.py`, `test_determinism.py`.

## What the bot does

**Hand evaluation.** A 7-card evaluator built on 13-bit rank masks with two 8192-entry lookup tables
(straight-high, top-5-bits) built at import; ~2 us per evaluation on this box. Tested against hand-
category and kicker cases in `test_eval.py`.

**Preflop.** A precomputed table (`PRE_EQ`, from `precompute.py`, 6,000 Monte-Carlo deals per class) gives
each of the 169 hand classes its all-in equity vs 1/2/3/5 random hands; hands are ranked into a percentile
by heads-up equity. Decisions:
- Opening ranges keyed on *seats still to act*, not fixed positions (7 behind = UTG: top 11%; button: ~36%),
  widened by 8 points when everyone behind folds a lot (tracked per seat).
- Unconventional pieces kept because they earned in sparring: **limp-trap** with the top 2.5% in front of an
  aggressive raiser (then 3x re-raise); **tiny 3-bets** (2.2x the raise) with premiums to keep the raiser and
  stations in; occasional **min-raise** opens with the top of range; **over-limps** with pairs / suited
  connectors behind a limper at 25bb+; bigger opens (3.5-4bb) only when stations are behind.
- **Push/fold** at <= 11bb effective: shove threshold from the equity table
  (0.455 + 0.009*M + 0.013*seats_behind).
- **All-in calls** demand equity above pot odds plus a margin that scales with the fraction of the stack at
  risk and with depth (up to +0.15 when > 30bb deep). This single rule was worth about +0.6 points.

**Postflop.** Monte-Carlo equity vs N random hands with the actual board run out (40 samples heads-up,
30/20/12 for 2/3-4/5+ opponents; fixed counts so the bot is deterministic; a 0.5 ms time guard is a
safety net only). Equity is discounted when facing a bet by how rarely the bettor raises (bets from
passive seats mean strength), on the river, and after multiple raises. Then:
- Value: pot-sized bets vs callers, 2/3 pot otherwise, **1.4x-pot polarised overbets** with straights or
  better on turn/river, shove when short relative to the pot.
- Medium hands: small 35-50% pot bets. Air: 1/3-pot probes and **leads into the preflop raiser** against
  seats that fold a lot, c-bets heads-up, and a 30% frequency 0.8-pot river bluff vs a folder.
- Facing bets: raise with >= 0.78 adjusted equity (shove when committed), call when equity beats pot odds
  + 0.04 + ICM margin + depth*risk margin, otherwise fold; tiny bets (<= 1/4 pot) are called with near-odds.

**Opponent model.** Per seat for the table: hands seen, VPIP, PFR, calls, folds, raises, actions. Derived
"call-rate" (station-ness) drives bet sizing and bluff selection; "raise-ratio" drives how much a bet is
respected; PFR drives limp-trapping and 3-bet choice. All reset in `new_table`.

**ICM.** A margin (0-0.10) added to calling thresholds when we are above average with short stacks at the
table, when 4 or fewer remain, and in the last 25 hands before the cap.

**Safety.** `act()` wraps the strategy in try/except and validates the action against `legal`,
`min_raise`, `max_raise` before returning; any failure degrades to check / cheap call / fold. RNG is
seeded in `new_table` from `rules['seed']` (if present), seat and player count; the only clock read is
the Monte-Carlo guard.

## How it was tested

- `python harness.py rival_bot` (and seed 2): 0 exceptions, 0 illegal, 0 folds-when-check-legal,
  import 0.04 s, mean 147-231 us, median 195 us, p99 396 us on a quiet run. Max 4-9 ms on this shared
  WSL2 box: identical observations re-timed take ~500 us, GC collections were zero during the spikes,
  so the spikes are OS scheduling jitter, not the bot (all sparring bots show them). On a dedicated
  machine the per-sample costs (4.6 + 2.1*n_opp us) put a worst-case decision around 250 us.
- `test_determinism.py`: the same table seed twice gives identical action sequences.
- `sim.py`: full NLHE engine (side pots, all-ins, min-raise rules, dead-blind-free rotation, 25-hand
  blind levels, 200-hand cap, Malmuth-Harville ICM over the remaining places, chip-conservation assert),
  with per-hand diagnostics for the focus bot (chips by how the hand ended, busts by opponent/street).
  Those diagnostics are what found the two big leaks: calling bets with equity vs *random* hands
  (-164 chips per passive showdown) and calling off deep stacks preflop vs shovers (103 of ~400 busts).

## Sparring results (fresh seed 5, 500 tables each, points per table, se ~0.1-0.15)

Field: `random` (uniform legal), `station` (never folds), `rock` (top 12%, passive), `tag` (textbook
2.5bb opens, 2/3-pot c-bets, pot-odds calls, short-stack shoves), `lag` (raises half its hands, pot bets),
`shover` (push/fold only), `sticky` (hero-calls any pair). Average points per seat is 4.0.

| config  | field                      | rival | best opponent      |
|---------|----------------------------|-------|--------------------|
| mixed   | one of each                | 6.84  | tag 5.57, rock 5.35 |
| tight   | 5 tag + 2 rock             | 4.91  | tag 4.16           |
| tagonly | 7 tag                      | 4.87  | tag 4.24           |
| loose   | 3 station + 2 lag + 2 random | 7.77 | lag 5.46           |

Progression on the mixed field (seed 1, 600 tables): 5.40 initial -> 5.78 after discounting equity when
facing bets -> 5.82 after wider steals / river bluffs (noise) -> 6.36 after the stack-risk margins ->
6.47 after tightening deep all-in calls further. Bottom-3 finish rate fell from 16% to 6%.

Caveat: the opponents are my own models; the TAG in particular folds to big bets in a way a real solver
may not, so the overbet/bluff frequencies are kept modest (30% or less) and gated on observed fold rates.
