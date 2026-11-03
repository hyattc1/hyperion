# rival_bot build log

## What the bot is

`rival_bot.py` (one file, pure standard library, ~100 KB, imports in ~0.4 s) defines `class Bot(Agent)`
(Agent imported from `kit`, with a stand-in class if `kit` is missing).

**Sound base**
- **Evaluator.** A rank-count-key dict covering every 5, 6 and 7-card rank multiset (73,775 entries,
  built at import), plus a 13-bit flush/straight-flush table. One evaluation costs about 0.4 µs. It was checked
  against brute force on 20,000 random 7-card hands and against the exact 5-card category counts.
- **Preflop tables, embedded (zlib+base64, 38 KB).** A 169x169 heads-up equity matrix (4,000 MC
  samples per matchup) and the equity of each of the 169 classes against 1 to 7 random hands (8,000 samples).
  Hands are ordered by a blend of heads-up and 3-way equity. Cumulative combo tables
  (card-removal aware) give the equity of any class against "top x%" or a percentile band in O(log n).
- **ICM.** `chip_value()` gives the exact Malmuth-Harville expected points for the 10/7/5/4/3/2/1/0
  payout in O(n). It is exact because the payout equals "players outlasted + 3·P(1st) + P(2nd)", and
  Harville's pairwise order is s_i/(s_i+s_j). It matches the full recursive ICM to two decimals on every test case.
  **Every** call, bet, raise and shove decision compares outcomes in ICM points, not chips. At 8 equal
  stacks, calling all-in needs about 67% equity. This was the largest single gain.
- **Preflop.** Opening widths depend on how many players are left to act and widen or narrow with the
  measured fold rate of the players behind. Push/fold at 14 bb or less uses an ICM EV over the players behind, each with a
  modelled calling width. Resteal shoves come in at 25 bb or less. 3-bets for value are chosen by equity against the
  raiser's modelled range. Light 3-bets go only against openers who are measured to over-fold. Calls compare ICM EV,
  with realization by position. Facing a shove, the call is decided on ICM EV.
- **Postflop.** A range-weighted Monte Carlo runs under a wall-clock deadline (330 µs after act() entry).
  Each opponent's hands are sampled from their modelled preflop range. They are ranked by strength on the current
  board (draws lifted to a draw percentile) and reweighted by that opponent's line on each street. A bet keeps the
  top `bet-rate` share plus a bluff weight; a call keeps the top `1 - fold-rate`; a check caps the range. Heads-up, the bot
  keeps per-hand win counts, so it can compute the equity against the part of the range that continues against a
  bet of each size. EV in ICM points is computed for check, bet 0.5/0.8/1.25 pot or all-in, call, and raise
  2.8x or all-in. The highest wins. Calls use an equity-dependent realization factor. Implied odds count only for real draws.

**Opponent model (per seat, reset per table)**
- Each hand's history is replayed through a betting state machine (blind seats, raise sizes,
  all-ins, street ends), and the result is checked against every observation. On any disagreement it resyncs
  to the observed state and carries on, so no particular history convention is required.
- Counted per seat: unopened fold/limp/raise and shove; fold/call/3-bet against one raise and against 3-bets;
  the opener's reaction to a 3-bet; calls against all-ins; bet frequency overall and by street; c-bet; fold/call/raise
  against a bet, against **our** bets, and against raises; average bet size as a share of the pot. If `hand_end` supplies
  showdown cards, it also counts how weak the cards behind river and turn aggression were (bluff rate) and how wide the
  shown preflop raising hands were.
- Every rate is shrunk toward a sound prior (Beta-style, 3 to 8 pseudo-counts). Rates are also kept by table size
  (5 or more, 3 to 4, heads-up), each shrunk toward the seat's overall rate, which covers "how they play short-handed".
  The rates feed both the opponent's range (who they are when they bet, call or shove) and our fold-equity estimates
  (who over-folds gets bluffed; who never folds gets value-bet bigger and is never bluffed). Shove and call-shove
  frequencies use weak priors (3), so a random or maniac shover is called wide within a few hands.
- If we bet and never act again before the river, everyone folded; that counts as a fold even when
  `hand_end` is empty.

**Safety.** act() is wrapped: any exception returns check, a near-free call, or fold. Every returned action
is legalized: kind in `legal`, raise clamped to [min_raise, max_raise], near-all-in raises rounded to all-in. A second
guard skips the MC when building the hand pools has already taken 450 µs.

## How it was tested

**Simulator** (`sim.py`). 8-seat NLHE sit-and-go with the kit's `Obs` interface. It has side pots, odd-chip
rules, short all-in raises that do not reopen the action, blinds rising every 25 hands on the brief's schedule,
a 200-hand cap, 10/7/5/4/3/2/1/0 finish points (players busting on the same hand are ordered by starting stack),
and exact Malmuth-Harville ICM for the bots alive at the cap. Seats are shuffled every table. `hand_end` can be sent
the full result (history and showdown cards), a partial one (stacks only) or `None`. Blind posts can be left out of
`history`, written as `('post', x)`, or written as `('raise', x)`. Every act() of the hero is timed and checked
for legality.

**Opponents I built** (`opponents.py`, `variants*.py`):
- weak/exploitable: `RandomBot` (uniform legal actions and raise sizes), `StationBot` (loose-passive),
  `NitBot` (plays ~10%), `ManiacBot` (opens 50%, barrels 70%, shoves often);
- solid: `TagBot` (position-aware opens, c-bets, MC equity, push/fold at 12 bb or less) in three parameter sets;
  `PushFoldBot` (Nash-like shove/fold); `AdaptiveBot` (a TAG that tracks fold-to-bet and aggression per seat and
  bluffs over-folders and calls down maniacs); `TrapBot` (built to punish over-betting: slowplays, check-raises
  for value and as a bluff, calls light);
- strongest and adaptive: frozen copies of this bot itself (v1 and v6 snapshots) with different knobs
  (Loose, Tight, Bluffy, Sticky, Plain, ChipEV). Each runs the full opponent model, so these are the
  adaptive model-based opponents the team asked for.

**Fields** (8 distinct bots each, the hero is one of them, mean of 1/8 = 4.00 points is break-even):
- `weak`: hero + 2 Random, 2 Station, 2 Maniac, Nit
- `mixed`: hero + Tag, Adaptive, PushFold, Maniac, Station, Nit, Random
- `strong`: hero + 3 Tag variants, 2 Adaptive variants, PushFold, Nit
- `self` / `self6`: hero + 4-6 frozen copies of this bot with different knobs, Tag, Adaptive/PushFold
- `trap`: hero + 2 TrapBots, Tag, Adaptive, Sticky-v6, Tight-v6, PushFold

The A/B runner (`ab.sh`) runs each candidate on the same seeds in two processes (nice 5) and prints the
hero's mean points with its standard error (about 0.09 to 0.10 per 1,000 tables).

## Development history (hero mean points per table, 1,000 tables, SE about 0.09 to 0.10; 4.00 = break-even)

| step | change | result |
|---|---|---|
| v1 | first complete build (tables, evaluator, model, MC) | mixed 5.95, strong 4.95 |
| v2 | weak priors (3) on shove / call-shove, so wide shovers are called wide early | mixed 5.89, strong 4.93, self 4.20, weak 7.02 |
| knob scan on v2 | +0.03 equity demanded on calls: mixed 6.03, strong 5.17. Narrower opens (0.8x): worse | so calls were too loose |
| v3 | **all decisions in exact ICM points** (calls, bets, raises, preflop calls) | mixed 6.04, strong 5.20, self 4.62, weak 7.13 |
| v3 blend test | ICM weight 0.7: 5.95 / 5.10; ICM weight 0.4: 5.99 / 4.86 | full ICM kept |
| v4 | resteal shoves at 25 bb or less, 1.25-pot overbet, pool-time guard | neutral (strong 5.26, weak 7.24) |
| leak study | 300 strong tables: the biggest loss was "raise pre, call flop, call turn, fold river" (62 hands, -72k chips) | |
| v5 | realization depends on equity for calls; implied odds only with a real draw; per-street bet frequencies | strong 5.36; that leak fell to 24 hands, -22k |
| v6 | self-healing history replay (resync to the observation on any mismatch) and fallback ranges | with history ignored completely: 3.40 -> 5.00 (5.19 with history) |
| self6 knob scan | v6: 4.16; calls +0.03: 4.43; opens 0.85x and calls +0.02: 4.44 (strong 5.46, mixed 6.25) | opens 0.9x and calls +0.025 adopted |
| v8 | position-split opening stats per opponent (4 or more behind vs 3 or fewer) and over-limping speculative hands | neutral (kept) |
| v9 | tighter preflop cold calls (realization -0.05) | self6 4.49 -> 4.65, strong 5.39 -> 5.61, mixed 6.20 -> 6.20 |
| v9 deadline | MC deadline 220 µs instead of 330 µs: 4.58 / 5.47 (slightly worse, not significant) | 280 µs chosen as a compromise |
| v10 (rejected) | scale the safety margins down against measurably leaky opponents | weak +0.06, strong +0.03, mixed -0.18, self6 -0.29, so it stays off (`K_SKILL = False`) |

## Final numbers (frozen `rival_bot.py`, seed 700, 1,000 tables per field, compared with v2 on the same seeds)

| field | final | v2 (early version) | gain |
|---|---|---|---|
| strong (Tag x3, Adaptive x2, PushFold, Nit) | **5.49 ± 0.10** | 4.89 | +0.60 |
| self6 (6 frozen adaptive copies of this bot + Tag) | **4.56 ± 0.09** | 4.37 | +0.19 |
| mixed (Tag, Adaptive, PushFold, Maniac, Station, Nit, Random) | **6.17 ± 0.09** | 5.76 | +0.41 |
| trap (2 check-raising TrapBots, Tag, Adaptive, Sticky-v6, Tight-v6, PushFold) | **5.07 ± 0.10** | 4.77 | +0.30 |
| weak (2 Random, 2 Station, 2 Maniac, Nit) | **6.92 ± 0.09** | 6.94 | 0.00 |

The same build on other seeds: strong 5.48 to 5.61, self6 4.65 to 4.82, mixed 6.20 to 6.23, weak 7.11. Break-even is 4.00 and the maximum is 10.
In every field the hero has the highest mean of the 8 bots. The one exception is self6, where the frozen "Tight" copy of
an earlier version (4.5 to 4.7) is level with it. That copy is this same engine with tighter knobs, and is the reason the knobs
moved toward it.

Robustness (500 tables each, no errors, no illegal actions):
- `hand_end(None)` with blind posts written as `('post', x)` in history: strong 5.01 (it loses showdown reads and the
  ends of hands after its own last action, but nothing breaks)
- partial `hand_end` (stacks only) with blinds written as `('raise', x)`: mixed 6.20
- history ignored entirely (forced, so the bot resyncs at every decision): strong 5.00
- history replay agreed with the observation at more than 99.9% of decisions under all three blind-post conventions

Latency (`python3 harness.py rival_bot`): 0 exceptions, 0 illegal actions, 0 folds when check was legal, import 0.32 s
(0.20 s on 3.12), mean 165 to 180 µs, p99 335 to 420 µs. In a quiet moment, 10,000 harness observations measured with
`thread_time` gave a CPU-time max of 735 µs and none over 1 ms. Re-running the slowest observations alone takes 120 to
340 µs. This machine runs at a load of 7 to 12 on 8 cores (other jobs), so wall-clock maxima of 1 to 5 ms show up
whenever the process is descheduled. Those spikes do not reproduce on re-run, and a trivial check/fold bot shows them too.
In the simulator the hero went over 1 ms on 0.01 to 0.04% of decisions in calm periods and up to about 1% at peak load.
Monte Carlo stops at 280 µs after act() entry, and is skipped if building the hand pools has already taken 450 µs. Peak memory is 22 MB.

## What I would do with more time
- **Bigger samples.** Most single changes were worth 0.1 to 0.3 points, about 1 to 3 SE at 1,000 tables. 5,000+ tables
  per arm (or paired seeds with common deals) would make the knob choices firmer.
- **Multiway postflop.** Multiway is the crudest part (one bet size, a shrink factor instead of continuing-range equity per
  opponent). Proper per-opponent continuing ranges and squeeze logic preflop would come next.
- **Sizing tells from showdowns.** Learn each seat's bet-size to strength mapping from shown hands, not just "bigger than their
  usual means stronger". Also model check-raise frequency per street.
- **Faster type detection.** A mixture prior (random / maniac / station / nit / solid) would identify a random-legal bot in
  2 or 3 hands instead of 5 to 10, which matters because those bots bust in the first dozen hands and whoever reads them
  first collects their chips.
- **Position-aware defence and skill-aware margins.** Re-test v10's skill scaling with a softer curve. Make the safety margins depend on
  position and the opponent's postflop aggression, not just their preflop looseness.
- **Precomputed flop/turn equity buckets.** Precomputing these would replace part of the Monte Carlo and halve both the
  latency and the estimate noise.
- **Blind-clock awareness in push/fold.** Count hands left to the next level and to the 200-hand cap.
- **Outside opponents.** Test against bots written by someone else. Every opponent here, including the adaptive ones, is mine.

## Files
- `rival_bot.py`: the deliverable (built by `build_bot.py` from `bot_src.py` plus `pre_tables.json`)
- `evalcore.py`, `precompute.py`, `pre_tables.json`: evaluator and preflop precompute
- `sim.py`, `run.py`, `ab.sh`: simulator, field runner, A/B runner
- `opponents.py`, `variants.py`, `variants6.py`, `v1_bot.py`, `v6_bot.py`: test opponents and frozen snapshots
- `leak.py`, `leak2.py`, `leak3.py`, `diag.py`, `prof*.py`, `harness_cpu.py`, `harness_over.py`: diagnostics
