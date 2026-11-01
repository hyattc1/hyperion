# build_log: f3_charts (TAG chart bot, no ICM)

Persona: two-person team, strong live cash player. Positional preflop open and 3-bet charts typed in
from memory, standard c-bets, value-heavy TAG postflop with pot-odds calls. Little tournament theory.

## What was built (rival_bot.py, one file, stdlib only, ~800 lines)
- Preflop charts as range strings parsed at import ("66+,ATs+,KTs+,AQo+" style): RFI by seat from the button
  (UTG 8%, UTG1 12%, LJ 14%, HJ 19%, CO 25%, BTN 41%, SB 32%), iso-raise over limpers, 3-bet value
  (QQ+/AK vs early opens, JJ+/AQs+ vs late), a few A5s-A3s 3-bet bluffs at 45%, call ranges by opener
  position (IP, SB, BB defend), 4-bet KK+/AKs, call 3-bets with 99-QQ/AQs/AKo, fold-or-shove to 5-bets.
  Position is derived from button + dealt-in seats, so charts tighten/widen as the table shrinks. Heads-up
  has its own wide button/BB rule. Sizing 2.5-3bb open (+1bb per limper), 3x IP / 4x OOP 3-bet.
- Stack-depth guard added after the charts (blinds escalate every 25 hands): under 15bb it switches to
  shove/fold with a Chen-formula percentile table by stack and position; calls shoves by crude
  pot-odds vs a compressed equity estimate. Raises that are a big part of the stack only get called with
  tighter ranges.
- Postflop: hand classifier (category, kicker, overpair/top/middle/bottom pair, sets vs trips, board-played
  detection, flush/straight/full house/quads) plus flush and straight outs (rule of 4 / 2) -> one strength
  number. Flop c-bet when preflop aggressor (heads-up ~68% dry / 45% wet, multiway only with real hands
  or good draws), 66% pot value bets, semi-bluffs with draws, second barrel on turn, thin river value,
  few bluffs. Facing bets: raise sets-or-better, otherwise call only if strength beats pot odds plus a margin
  (3/5/7 points flop/turn/river), minus penalties for multiway, big bets, being raised, and opponents who
  bet every street. Commit/shove when a bet is over half the stack.
- act() is wrapped: any exception or illegal result is replaced by check/fold; raise amounts are clamped.
- Own test engine (engine.py): 8 players, side pots, blind schedule, ICM at cap, a pool of random, station,
  maniac, push-fold, nit and LAG opponents (run1.py, stats.py, lag.py, mirror.py, leaks.py, scen*.py).

## Minute marks
- m0-5: read kit, wrote first full bot (charts + postflop + short stack).
- m5-9: wrote engine, found no exceptions; scenario spot checks; widened UTG, fixed folding AA to an all-in
  when raise was not legal (value hands now call), big-raise call guards.
- m9-15 (snap_m15.py): river margin tightened after a chip-leak report (river bluff-catches lost most),
  short-stack BB defence tightened, removed dead code.
- m15-18: pairs fixed in push/fold ranking (Chen underrated 22-66), "he bet every street" penalty, fixed a
  real bug in straight-draw outs (counted ranks, not cards). Froze at about 17 min. snap_m30.py and
  snap_m45.py are identical copies of the final file (nothing was edited after minute 18).

## Results on my own engine (not the real field)
- vs mixed weak pool of 7: about 6.6 points per table (fair share 4.0). vs 7 LAG bots: about 4.9.
  Mirror (8 copies): seat means 3.4-4.5, noise only. 0 exceptions, 0 illegal over thousands of tables.
- Style: VPIP about 34% and PFR about 28% across a whole sit-and-go (inflated by short-handed play and
  shoves); folds to a flop bet about 63%, so it is exploitable by anyone who bets every flop.

## Known weaknesses
- No ICM and no bubble awareness; chip-EV TAG. Never adjusts to the cap or to pay jumps.
- No opponent modelling at all: no reads on stations or maniacs, folds too often to relentless aggression,
  bluff-catches poorly vs random bots, bluffs too little vs stations.
- Preflop 3-bet/4-bet ranges are static and small; 5-bet shoves only KK+/AKs. Cold-call ranges are guesses.
- Shove/fold uses a Chen ranking, not a real Nash table; call-vs-shove equity is a crude curve.
- Postflop strength is a hand-coded number, not an equity calculation; no blockers, no backdoor draws,
  no implied odds, no check-raise or slowplay lines, no sizing variation by opponent.
- Short-handed and heads-up ranges are approximations.

## With more time
- Real equity (precomputed preflop equity table, small lookup-based postflop equity) instead of hand-coded
  strength numbers.
- Per-table opponent stats from the history (VPIP, aggression, fold-to-cbet), then exploit stations/maniacs.
- Proper push/fold charts by stack and position, plus a basic ICM adjustment near the cap and for short stacks.
- Mix in check-raises and slowplays, tune c-bet and bluff frequencies against a real field.
