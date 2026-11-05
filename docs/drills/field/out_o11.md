# rival_bot notebook

Deliverable: `rival_bot.py` (single file, standard library only, ~90 KB with embedded tables,
imports in <0.1 s). Everything else in this directory is tooling built for this job:

| file | purpose |
|---|---|
| `peval.py` | 7-card evaluator used by the simulator and sparring bots (same code is embedded in the bot); brute-force verified against 5-card decomposition on 3,000 random hands, ~2 us per hand |
| `engine.py` | 8-max NLHE sit-and-go simulator: 2,000 chips, blinds 10/20 rising every 25 hands over the 8 assumed levels, 200-hand cap, side pots, points 10/7/5/4/3/2/1/0 with exact Malmuth-Harville ICM at the cap, 1 ms wall-clock guard, legality/exception guard, chip-conservation assertion every hand |
| `opponents.py` | sparring field: `random` (random legal), `station` (never folds, never raises), `tightpas`, `tag` / `tag_tight` (position-aware TAG with c-bets and push/fold), `lag` (wide, pressure), `equity` / `equity_agg` (Monte-Carlo equity players, untimed in sparring) |
| `spar.py` | runs N tables of a lineup with seats shuffled per table; reports mean points, standard error, finish distribution, exceptions, illegal actions, slow (>1 ms) calls, mean/max microseconds |
| `diag.py` | replays tables with a traced copy of the bot and prints every hand in which it busted (hole, board, pot, action, the model's internal numbers) |
| `precompute.py` | offline table builder (`pre`, `post`, `merge`); writes the literals between the `TABLES` markers in `rival_bot.py` |

## Where the points come from (the thinking behind the design)

* Finish points 10/7/5/4/3/2/1/0: first place is worth 3 more than second and the gap then shrinks
  to 1 per place. Mean is 4. The structure is top-heavy, so chip accumulation is rewarded, but an
  early bust (0 or 1) is a disaster relative to the mean, and ICM at the 200-hand cap pays every
  survivor roughly by stack. Both tails matter: win a lot of tables, bust early rarely.
* Blinds reach 200/400 by hand 176 with 16,000 chips on the table: the second half is a short-stack
  game. A correct jam/call-jam model is the single most important component, so it is built
  explicitly (fold equity x calling ranges x precomputed equities, converted to points by ICM)
  rather than approximated with rules of thumb.
* Short-handed play and the last hands: the ICM conversion makes the bot naturally tighter when
  it is comfortable and when short stacks are about to bust, and an extra margin (`eps`) grows
  over the last 25 hands so the bot stops gambling for small edges when ICM at the cap already pays it.
* The field is "anything from random-legal bots to tight solvers", anonymous per table. The bot
  therefore keeps a per-seat model from `obs.history` (vpip, aggression, fold rate, erratic
  sizing, never-folding) and reads it in the jam model (calling-range width), the postflop
  strength model and the bluffing decisions (never bluff a station; value-bet thin against
  stations and erratic players; steal more against tables that fold).

## What the bot does

Decision time is 1 ms wall-clock in Python, so nothing is simulated at decision time. All
knowledge is precomputed offline by `precompute.py` and embedded:

1. `EQ_RANDOM[n][class]`: equity of each of the 169 preflop classes vs n = 1..7 random hands
   (2,500 boards each).
2. `EQ_RANGE[x][class]`: equity vs an opponent holding a top-x fraction of hands (x on a 13-point
   grid, hands ordered by heads-up equity), used for jam/call-jam decisions.
3. `PF_EQ`: postflop equity vs 1 and vs 2 random hands bucketed by a 9-field feature key computed
   by `pf_key()` (street, made-hand category, sub-type such as overpair / top pair / second pair /
   set vs trips / nut-ish flush, kicker bucket, flush draw, straight draw, board suitedness, board
   connectedness, board pairing). 1.2M random runouts; 1,111 full keys with >= 25 samples, with
   coarser fallbacks (151 mid keys, 27 category keys). `pf_key` lives in the bot and the
   precompute imports it, so the table and the lookup cannot diverge.

Preflop:
* `PRE_RANK[class]` = percentile of 0.55 x eq-vs-1 + 0.45 x eq-vs-4 (0 = best).
* Deep (more than ~11 BB): open-raise by players left to act (10% from the front to 40% on the
  button, 70% heads-up), widened against tables that fold and narrowed against stations and
  limpers; 2.1-2.5 BB sizes; medium hands with 12-18 BB open-jam when the jam model says so
  (strong hands raise small). Facing a raise: value 3-bet (top ~4.5%, scaled by the raiser's
  looseness, jam when the 3-bet would commit 40% of the stack), occasional light 3-bet in
  position against frequent folders, calls with position-dependent ranges and a price cap,
  set-mining pairs and suited connectors at <= 5.5% of the effective stack. Facing a 3-bet:
  4-bet/jam with the top 3%, call tight with a price cap.
* Short (<= 11 BB, or <= 15 BB facing a raise, or effective stack <= 9 BB): jam or fold. For each
  opponent still to act, the calling-range width is `2.6 / effective_BB` scaled by the
  opponent's observed looseness, widened if they already raised; erratic players call 67% with
  a random range, stations 95%. Jam EV in *points*: P(all fold) x ICM(win blinds) + sum over
  callers of (equity vs their range x ICM(win) + (1 - equity) x ICM(lose or bust)) minus
  ICM(fold). Exact ICM for the two most likely callers, linearised for the rest.
* Facing a shove or a raise that commits us: the shover's range width comes from shove size in BB
  and the players behind, scaled by looseness, tightened for re-raises; call if ICM EV beats
  folding by a margin (0.015, more near the cap).

Postflop:
* Equity from the feature table. Shown strength is modelled as *extra random opponents to beat*:
  each postflop bet/raise by an opponent counts 0.7 of a hand, each call 0.3 (nothing for a
  station's call, nothing at all for erratic players), an open 0.25, a 3-bet 0.9, a 4-bet 1.6; a
  large bet, a bet from a passive player, a raise over our own bet and river bets add more. The
  1- and 2-opponent equities are extrapolated to the fractional opponent count.
* Facing a bet: if the call commits >= 40% of the stack, the ICM call model decides; otherwise
  raise for value with >= 0.74 (0.66 vs stations / erratic), call when equity beats pot odds plus
  a margin that grows with players, semi-bluff raise strong draws vs folders, otherwise fold.
* No bet: value bet at >= 0.60 (1 opp) / 0.66 / 0.72, bigger vs stations, all-in when the bet
  would commit the stack anyway; c-bet as preflop aggressor, semi-bluff draws, barrel and river
  bluffs only when nobody has shown aggression and the opponents fold enough; thin value in
  position on the river. Never bluff a station.

ICM: exact Malmuth-Harville for 1st-3rd place, a smooth stack-dependent payout for 4th and below
(calibrated against the exact recursion in `engine.py`: 0.10 points mean abs error on win/lose
deltas, 43 us per call at 8 players; exact for 4 or fewer players).

Safety: every decision is wrapped; any exception or illegal result falls back to check/fold; raise
sizes are clamped to `[min_raise, max_raise]`; the wall clock is read once per `act()` and only
used to skip the exact-ICM refinement when the call is already slow (`budget_ok`). The RNG is
`random.Random(seat * 1000003 + n_players * 7919 + 12345)` seeded in `new_table`; randomness is
used only for mixed frequencies (light 3-bets, c-bet / barrel / bluff frequencies, raise-vs-call
with strong hands). `gc.freeze()` is called at import so the embedded tables never get scanned
by the cyclic collector, and `new_table` warms the lookups.

## Testing

1. Evaluator: brute-force equality with the best 5-card hand on 3,000 random 7-card hands; hand
   category assertions for every category including wheels and steel wheels.
2. Harness: `python harness.py rival_bot` (2,000 random legal observations) — 0 exceptions,
   0 illegal actions, 0 folds when check was legal, on every run during development. Final run
   numbers are in the last section.
3. Engine: chip conservation asserted after every hand across all runs; ordering of the sparring
   field without the rival is as expected (TAGs on top, station and random at the bottom).
4. Sparring with `spar.py` on several lineups, 60-100 tables each (seats shuffled per table),
   and `diag.py` to read every busting hand. Three iterations came out of the bust traces:
   * a bug in the all-in call model (the win scenario counted the called chips twice), which made
     calling off 1,890 chips with 87o at 43% equity look +EV;
   * equity vs *random* hands is far too optimistic against players who bet several streets or
     3-bet preflop (88 on 77K calling three bets four-way; second pair calling down a double
     barrel) — replaced by the "extra opponents" strength model above;
   * the first ICM approximation spread the lower payouts by stack *rank*, so winning a pot that
     moved us up two ranks looked worth ~0.6 points at a full table (equal stacks scored 4.94 down
     to 3.06 instead of 4.0 each). Replaced by exact 3rd place + a smooth rest term, calibrated.

## Sparring results

Mean finish points per table (8-bot tables, mean of the field is 4.0 by construction).
Standard errors are ~0.3-0.45 at 60 tables. Same seeds before and after each change.

Mixed lineup (`rival, random, station, tightpas, tag, lag, equity, tag_tight`):

| version | rival | best opponent |
|---|---|---|
| first full version (60 tables, seed 2) | 5.95 +/- 0.42 | tag 5.97 |
| + strength model, cap tightening | 6.48 +/- 0.42 | tag 5.57 |
| + ICM fix, preflop strength, no barrels into raisers | 6.09 +/- 0.39 | tag_tight 5.53 |

Strong lineup (`rival, tag, tag, tag_tight, equity, equity, equity_agg, lag` — no weak bots):

| version | rival | best opponent |
|---|---|---|
| before ICM fix (60 tables, seed 3) | 3.73 +/- 0.38 | tag 5.25 |
| after ICM fix + preflop strength model | 5.15 +/- 0.44 (17 firsts of 60) | tag 4.96 |

Confirmation runs with fresh seeds (filled in from `run_strong.log`, `run_tags.log`,
`run_mixed.log`):

| lineup | tables | rival | 1st-place share | best opponent |
|---|---|---|---|---|
| mixed (seed 12) | 100 | **6.54 +/- 0.33** | 42% | lag 5.15, tag_tight 5.09 |
| TAGs only (`rival` + 5 `tag` + 2 `tag_tight`, seed 13) | 80 | **4.78 +/- 0.42** | 35% | tag 4.45 |
| strong (seed 11) | 100 | 4.62 +/- 0.35 | 26% (most of the field) | tag_tight 4.80, tag 4.71 |

Reading: against mixed and TAG-only fields the bot is clearly first on points and wins far more
tables than anyone else. Against the strong field it wins the most tables but gives back the
difference in 6th-8th finishes (40% of tables), ending level with the TAGs within noise.
Two A/B tests on the same seed of an open-jam margin (`JAM_EPS` 0.025 / 0.05) and a narrower
medium-hand open-jam range (`OPENJAM_MAX` 0.25 / 0.20) changed nothing or hurt (4.59, <4.63),
so the defaults stay; the bust cluster is in the 10-20 BB mid-game but not in marginal open-jams.
That is the first thing to chase next (likely candidates: calling-range widths assumed for
TAG-like players in the jam model, and resteal jams against openers).

## Harness

`python harness.py rival_bot` (2,000 random legal observations, idle machine):

```
module=rival_bot n=2000 import=0.04s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=39.1 median=30.9 p99=123.4 max=4074.5      (seed 1)
module=rival_bot n=2000 import=0.02s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=37.1 median=32.1 p99=130.0 max=232.5       (seed 2)
module=rival_bot n=2000 import=0.04s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=35.4 median=31.0 p99=119.5 max=232.7       (seed 3)
```

The 4.07 ms maximum on seed 1 is one call; re-running the identical seed-1 sequence gave a
447-620 us worst call, and re-timing that same slowest observation 50 times gives a 17-76 us
median. So the bot's worst code path is well under 1 ms and the occasional ~4 ms value is the
WSL2 scheduler tick (it also hits the 0.2 us station bot in sparring). On real tournament
hardware this would still be worth a look: if the organisers' box shows the same tick, nothing a
bot can do avoids it.

Determinism: the same seed and observation sequence produces an identical action sequence
(checked over 600 decisions); the RNG is seeded from `new_table` inputs only.

Note on latency: with two niced simulations running on this WSL2 box, a few calls per hundred
thousand of *every* bot (including the 0.2 us station bot) show ~4 ms spikes; they are the OS
scheduler tick, not bot work (gc stats showed zero collections). The bot's own work is 25-40 us
on average and ~250-650 us worst case on an idle machine.

## Known limits / next steps

* Postflop equities are vs random hands with a heuristic strength model; a table of equities vs
  continuing ranges per board texture would be the next big step.
* No explicit heads-up postflop solver; heads-up relies on the wide preflop ranges, the jam model
  and the generic postflop logic.
* Opponent stats reset every table (as the rules require); the first ~15 hands run on priors.
* `EQ_RANGE` orders hands by heads-up equity, which slightly overrates suited aces inside tight
  calling ranges (AQo vs top 3% shows 0.385 where ~0.33 is expected).
