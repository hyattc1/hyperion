# Red-team drill 4: the bot the strongest team in the room ships in 60 minutes

**COMPLETE, rival code frozen at minute 40.8 (file last written at 40:17), md5 28a0655f583ce9f5d6ac11b72bed0d72;
operator gates re-run 2026-11-01 09:47 UTC on the frozen file. The judge: no candidate core is measured against it
or tuned on it before the one final comparison.**

Operator/rival drill run 2026-11-01, same protocol as drills 1 to 3 (see `redteam-1.md` to `redteam-3.md`): the
operator set up the scratch directory with the same brief, stub kit, smoke harness and hostile-input fuzz as drill
3, kept the clock and scored. The rival was a prepared team with a coding agent, no access to this repository and
no sight of any earlier rival. Unlike drills 2 and 3 it was given **no design philosophy**: "the strongest team in
the room, build whatever scores most". The only files written into this repository for the drill are this report
and the bot (`rival4_bot.py`, byte-identical to the frozen file). The simulator plays it as `rival4` through
`hyperion/sim/rivals/rival4.py`.

Scratch directory (brief, kit, harness, fuzz, the rival's engine, archetypes, A/B outputs, snapshots):
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/redteam4/`
Operator gate re-run (scripts and raw output): `.../scratchpad/rival4_gate/`

Clock: T0 = 2026-11-01 08:56:33 UTC (`T0.txt`). Frozen 09:37:23 UTC (m40.8), file mode 444. Frozen file md5
`28a0655f583ce9f5d6ac11b72bed0d72`. Snapshots: `snap_m15.py` (md5 `7e6b37d9...`, file time 12:45), `snap_m30.py`
(`ec1a3251...`, 31:05), `snap_m45.py` (45:02, identical to the frozen file). Two snapshot copies were early; see
section 6.

## Key numbers

All harness rows are the operator's re-run on the frozen file, with the 8-core WSL2 host at load average 11.0-13.9
(other agents' sweeps were running; the interleaved count ran at load 15). The tail-latency rows are the host's,
not the bot's: see section 4.

| Measure | Result |
|---|---|
| Harness, CPython 3.12 (project venv), 10,000 random legal obs, seeds 1 and 2 | 0 exceptions, 0 illegal, 0 fold-when-check-legal |
| act() latency, 3.12 | seed 1: mean 64.1 us, median 20.5, p99 291, max 13,210; seed 2: mean 27.8, median 20.3, p99 77.9, max 7,509. A fixed 30-us control bot at the same moment: median 30.2, p99 62.5, max 8,028 |
| Harness, system CPython 3.10, 10,000 obs, seeds 1 and 2 | 0 exceptions, 0 illegal; seed 1: mean 48.8 us, median 28.8, p99 312, max 9,968; seed 2: mean 67.3, median 28.7, p99 275, max 17,108 |
| Over 1 ms, rival and 30-us control interleaved on the same obs, 3 x 10,000 | 3.12 (load 15): rival 0.75-0.94%, control 0.82-1.00%; 3.10: rival 0.29-0.59%, control 0.22-0.45% |
| Import time / memory | 0.012-0.015 s (3.12), 0.027-0.082 s (3.10), five fresh interpreters each; nothing is computed at import (the equity tables are literals generated offline in the window) / 16.8 MB RSS after import, 10.2 MB for a bare interpreter (3.12) |
| Internal exceptions (`_act`, `_finalize`, `_set_pay` wrapped to re-raise; the bot has no DEBUG switch), 10,000 obs | 0 (3.12 and 3.10) |
| Hostile-input fuzz, 3,000 obs: the drill-3 operator fuzz (given to the rival), and drill 2's fuzz | 0 exceptions, 0 illegal, both fuzzers, both interpreters |
| ICM against brute-force Malmuth-Harville, 400 random stack vectors with 2-8 alive | exact (spread under 1e-13 points) for the brief's 10/7/5/4/3/2/1/0 and for our default 8..1 once it is given the table; off by up to 2.9-5.3 points on top_heavy 50/25/12/6/3/2/1/1 with 4 or more alive; 1.3-1.4 us per call (3.12) |
| Size | 657 lines (598 non-blank non-comment; three of them are the table literals, 18 KB), one file, stdlib only |
| Rival's own engine, frozen file, 500 tables per field (uniform = 4.00; the rival's ± is one standard error) | weak 7.29 ± 0.12, mid 6.89 ± 0.12, strong 5.74 ± 0.14, mixed 6.08 ± 0.13, chaos 6.78 ± 0.11, pros 5.61 ± 0.14. It (or its second copy, SELF, in strong, mixed and pros) is first in every field |
| Self-reported at the freeze | median 28 us, p99 73-150 us (load), import 0.015 s |
| **In our engine** (`rival4`, rivals only; `docs/decisions.md`, "Rival 4 in the pool (the judge)") | see section 8 |

The rival's fields (`run.py`; its own archetypes from `bots.py` plus the bot, one seat each, random seats, no
duplicate deals): weak = Random, Push, Station, Maniac, Folder (always folds: a dead seat), SemiSane, Tight; mid =
SemiSane, Tight, LAG, Station, Shover (push/fold by depth), Crashy (crashes 30%), Random; strong = SELF (a second
copy), SNAP (its own v1), Shover, Tight, LAG, Nit, SemiSane; mixed = SELF, Push, Shover, LAG, Station, Folder,
Tight; chaos = Maniac, Random, Push, Station, Crashy, LAG, Folder; pros = SELF, SNAP, SNAP30 (`snap_m30.py`),
Shover, Tight, Nit, SemiSane. Its engine pays 10/7/5/4/3/2/1/0, keeps blind posts out of the history, passes
`{'starting_stack', 'hand_cap', 'n_players'}` to new_table (no payouts) and `{'hand_no', 'stacks'}` to hand_end (no
history).


## 1. The brief as given to the rival (verbatim, byte-identical to drills 1 to 3)

# Rival brief — "No Limit" poker bot tournament (public rules as the rival knows them)

You are a 3-person CMU/MIT team with poker knowledge and a coding agent. You have 60 minutes
from T0. You may use only the Python standard library. You have read these public rules and
prepared mentally; you have no code to bring in.

## Format
- 8-bot sit-and-gos, no-limit Texas hold'em, standard rules for this drill.
- 2,000 chips each. Blinds start 10/20 and rise every 25 hands. The exact schedule is not
  published; assume something like 10/20, 15/30, 25/50, 50/100, 75/150, 100/200, 150/300,
  200/400. Read `obs.blinds` every hand rather than assuming.
- 200-hand cap per table. Finish-position points 10/7/5/4/3/2/1/0 (1st..8th). Bots still
  alive at the cap are scored by ICM over the points for the remaining places.
- 10,000 tables per tournament; six tournaments weighted 1..6 (the last counts six times the
  first). Final score is the weighted mean of points per table.
- Python. ONE MILLISECOND wall-clock per decision; a timeout is an automatic fold. 100 MB
  memory. No network, no threads, no files. State is reset per table. Opponents are anonymous
  (seat numbers only, re-seated every table). Seat assignment is random per table.
- Each table seats one copy of each of 8 distinct bots (the field varies; expect anything
  from random-legal bots to tight solvers).

## Agent interface the kit provides (see kit.py)
```python
class Agent:
    def new_table(self, rules, seat, n_players): ...   # rules: dict, may be partial
    def act(self, obs) -> tuple[str, int]: ...          # ('fold'|'check'|'call'|'raise', amount_total)
    def hand_end(self, result): ...                     # result: dict, may be partial or None
```
`obs` attributes:
- `hole`: tuple of 2 ints, card = rank*4 + suit, rank 0=deuce .. 12=ace, suit 0..3
- `board`: tuple of 0/3/4/5 ints, same encoding
- `street`: 0 preflop, 1 flop, 2 turn, 3 river
- `seat`: your seat index; `button`: dealer seat index
- `stacks`: list of ints, chips behind for every seat (0 = busted or all-in)
- `bets`: list of ints, chips each seat has put in THIS street
- `in_hand`: list of bool, still contesting the pot
- `pot`: chips from previous streets (does not include `bets`)
- `to_call`: chips you must add to call (already capped at your stack)
- `min_raise`: minimum legal raise-TO total; `max_raise`: maximum legal raise-TO total (all-in)
- `legal`: set of strings from {'fold','check','call','raise'}
- `hand_no`: 1-based hand number at this table
- `blinds`: (small_blind, big_blind)
- `history`: list of (seat, action) tuples for this hand so far, oldest first; `action` is the
  same tuple shape you return. Blind posts may or may not appear.

The action you return must be in `legal`; a raise amount must satisfy
`min_raise <= amount <= max_raise` (integers). Anything else, or an exception, or >1 ms, folds.
For 'fold'/'check'/'call' the amount is ignored (return 0).

## Deliverable
One file `rival_bot.py` defining `class Bot(Agent)` (or any class exported as `Bot`). Import
time should be a few seconds at most. Test with `python harness.py rival_bot` (2,000 random
legal observations: counts exceptions, illegal actions, mean/max microseconds).

`kit.py`, `harness.py` and the operator's hostile-input `fuzz.py` are byte-identical to drill 3's (all three are
reproduced in `redteam-2.md` §1 and `redteam-3.md` §1).

### The philosophy given to the rival

None. The rival was told it is the strongest team in the room and to build whatever scores most. It chose, on its
own: exact ICM at every all-in decision, an embedded 169-class equity table, push/fold at 8 bb or less, postflop
equity from the made hand plus outs with no Monte Carlo, and a small per-seat model that flags seats that never
play.


## 2. Build log (rival, verbatim)

# build_log (times relative to T0 = 2026-11-01T08:56:33Z)

- m00: read brief/kit/harness/fuzz. Key design insight: payout 10/7/5/4/3/2/1/0 = (#players outlasted) + 3*P(1st) + 1*P(2nd).
  Under Harville ICM pairwise P(i outlasts j) = s_i/(s_i+s_j), so exact ICM equity is O(n^2) -> usable inside every decision.
- m04: plan: (1) offline MC preflop table (169 hands vs random + vs top-x% ranges) hardcoded; (2) ICM-driven push/fold + all-in calls;
  (3) position open ranges deeper; (4) rule-based postflop equity classes; (5) per-seat opponent model (raise/shove freq, folders).
- m09: precompute launched in background (vs-random 2500 samples/hand, vs-top-x ranges 500 samples). ev7 = 18us/eval (offline only; bot does not MC).
- m07: v1 rival_bot.py done (embedded 169-hand MC table; ICM exact O(n^2); push/fold via ICM EV with modeled callers; positional opens;
  3bet/call by equity vs estimated raiser range; postflop class-equity + draws; per-seat aggr/vpip/folder model).
  harness 10k: exc=0 illegal=0, median 27us, p99 750us (spikes). fuzz: 0/0.
- m09: prof.py: swallowed internal exceptions = 0. replay.py: all >250us calls replay at <=30us min-of-7 -> spikes are machine load.
- m10: snapshot snap_m15.py taken early (legal safe v1). Next: engine with side pots + archetype field.
- m11: engine.py (side pots, schedule, 200 cap, exact Harville ICM at cap) + bots.py archetypes (Folder/crash, Crashy, Random, Push,
  Station, Maniac, Tight, SemiSane, LAG, Nit, Shover) + run.py fields weak/mid/strong/mixed (strong includes SELF + v1 copies).
  v1 400 tables: weak 6.45, mid 5.70, mixed 5.76, strong 4.86 (field mean 4.0). >1ms in-engine 0.8% of decisions = load (replays ~30us).
- m12: bust.py replays: LEAK 1 light preflop re-shoves (Q4o, 83o, KTo vs 3-bet) because shove fold-equity was a flat 55-75%.
  LEAK 2 calling down vs postflop raises of our bet (JJ vs two-pair+). LEAK 3 turn barrels with TT after flop raise.
  Fix: raiser continue-fraction from the price he gets (committed raisers ~never fold), raise-over-our-bet penalty, barrel only w/ equity/draw.
  A/B same seeds 400 tables: strong 4.93 -> 5.25, mid 5.41 -> 6.16.
- m13: v1 kept as v1.py (test opponent 'SNAP'); snap_m15.py = current (re-copied at m15).
- m15: snap_m15.py was copied at m12.8; bot unchanged in behaviour through m15 (only constant->attribute refactor after).
- m16-20: paired A/B (abp.py: same tables/decks, 300 tables): P_PUSH 10 vs 13.5: strong +0.25+-0.09, mid +0.09+-0.08;
  8 vs 10: strong +0.27+-0.07, mid +0.12+-0.05; 6 vs 8: +0.02+-0.07 (flat). -> P_PUSH=8. P_OPEN 1.3 vs 1.0: +0.18+-0.13 (n.s.).
- m20-27: A/B (paired): P_COMMIT 12: -0.11+-0.07, 20: -0.50+-0.12 (keep 16). P_MARGIN 0.03: 0.00, -0.01: -0.06+-0.03 (keep 0.01).
  P_OPEN 1.3: mid +0.23+-0.11 (adopted), 1.6 vs 1.3: -0.01 (keep 1.3). P_CBET 0.3: -0.13+-0.09; 0.85: 0.00/+0.06 (keep 0.6).
  P_VALUE 0.62: +0.07/-0.04 (n.s., keep). Station exploit (thin value, no bluffs vs loose-passive): weak -0.03+-0.04, mixed +0.03+-0.06 (kept, neutral).
  P_CALLC (assumed caller width vs our shove) 0.7: +0.12+-0.07, 1.4: -0.17+-0.06 -> hedged at 0.8 (archetypes call tight; real field unknown;
  the per-seat looseness blend adapts after 5 hands).
- m28: _legalize hardened for hi<=0 raise bounds.
- m31: snap_m30.py taken (md5 810b27f4d524c88f321078550a43694b). BUG found: AKs UTG 8bb folds: ICM breakeven 78% (static ICM ignores blind drain of the fold branch; also 7 callers x 24% each). Adding P_TAU blend ICM->chip-linear.
- m30.8: snap_m30.py re-copied at true m30.8 (md5 ec1a325123636482654e3c683bdd65fc); earlier copy was m29 (my clock estimate ran ahead). P_TAU/P_MULTI default 0 = same behaviour.
- m31: P_TAU=0.3: +0.02/-0.02 (n.s.). P_TAU=0.6: strong +0.11+-0.14, mid +0.01+-0.11, weak +0.08+-0.13 (consistent small +). P_MULTI: -0.02+-0.03.
  Making tau time-aware: tau_now = P_TAU * clamp((cap-hand)/120,0,1) since ICM is exact at the cap.
- m33: time-aware tau 0.7: strong +0.04+-0.11, mixed -0.37+-0.14 (significant) -> P_TAU stays 0: survival premium real when weak bots self-destruct.
- m33-35: P_TEX (flush-board penalty for pair/two pair): strong -0.04+-0.07, mixed -0.05+-0.06; P_STR (turn/river bet factor): -0.05/-0.06 -> both off.
  New fields chaos/pros: current vs v1 same seeds: chaos 6.22 -> 6.62, pros 4.61 -> 5.25.
- m36: hu.py (heads-up, 100/200 start, 2000 each): HU win-rate vs PushBot 0.02, Maniac 0.07, LAG 0.12 -> MAJOR LEAK.
  BUG A: icm() gave a busted player 0, but HU the loser keeps P(top2)=1 (+1). Fix -> PushBot 0.12, LAG 0.31.
  BUG B: icm() dropped opponents who bust in the win branch instead of crediting +1 outlasted -> every call vs a shorter all-in
  was undervalued by ~1 point x equity (AKs UTG 8bb folded; A8s HU vs 4.5bb shove folded). Fix: pass alive-at-decision set.
  HU after both: PushBot 0.37, Maniac 0.43, LAG 0.53, Shover 0.74, Tight 0.98, SemiSane 0.74, Random 0.59, V1 0.96.
- m37: paired BUSTFIX 1 vs 0: mixed +0.12+-0.10, strong +0.35+-0.14, weak +0.30+-0.10, chaos +0.04+-0.09 -> kept.
- m38: re-tune after ICM fix: P_PUSH 11 vs 8: mixed -0.08+-0.06, strong -0.18+-0.10 (keep 8). P_CALLC 1.0 vs 0.8: -0.02+-0.01, -0.09+-0.04 (keep 0.8).
- m39: P_VALUE 0.65 + P_CBET 0.7 combined: mixed +0.06+-0.10, strong +0.04+-0.12 (n.s., not adopted).
  Gate: harness 10k exc=0 ill=0 median 26.7us p99 72.7us; fuzz 0/0; slow calls replay <=29us; swallowed internal errors 0 (harness + 150 engine tables).
- m39.5 final field runs (500 tables each, our avg points; field mean = 4.0):
  weak 7.29 | mid 6.89 | strong 5.74 | mixed 6.08 | chaos 6.78 | pros 5.61. In-engine act median ~17us, p99 ~45-50us, >1ms 0-2 of ~80k.
- m40: HU trace vs PushBot: model learns shove rate slowly. Tried P_SHOVEMODEL (use per-seat shove rate for all-in ranges):
  chaos -0.03+-0.05, mixed -0.04+-0.05, strong -0.05+-0.04, weak -0.10+-0.07 -> OFF (8-handed: others bust the maniac; survival pays).
- m40.8 FINAL GATE on frozen file: cold import 0.015s; harness 10k seed1: exc=0 ill=0 median 28.0us p99 150.8us (load);
  seed7: median 27.4 p99 93.6; fuzz exc=0 ill=0; replay of 93 slow calls: worst min-of-7 = 34us; internal errors 0.
- FROZEN at m40.8 (09:37:23Z). rival_bot.py md5 28a0655f583ce9f5d6ac11b72bed0d72 (chmod 444; not edited after this).
- m45.0 (09:41:35Z): snap_m45.py copied from the frozen file (md5 identical: 28a0655f583ce9f5d6ac11b72bed0d72).


## 3. The design the rival chose, and how it differs from rivals 1 to 3

Rival 1 hand-read (a typed preflop table, a fitted push formula, made-hand buckets with outs, four opponent flags).
Rival 2 computed (a 169x169 matrix, a solved push/fold table and an ICM curve, built in 1.1 s of import, with a
time-boxed Monte Carlo postflop). Rival 3 read the opponent (21 counters per seat, labels, steals by measured fold
equity). Rival 4, free to choose, spent its effort on **pricing every big decision in finish points**, and kept
the rest small.

- **Baseline from literal tables, nothing computed at import.** Equity of the 169 classes against a random hand,
  a percentile rank, and equity against the top-w range for nine widths (3% to 100%), from an offline Monte Carlo
  run inside the window (`precompute.py`: 2,500 samples per class against random, 500 against each range) and
  pasted into the file as three literals (`embed.py`). A 7-card evaluator on rank counts is used only postflop.
  Import takes 12-15 ms.
- **The ICM is exact, O(n^2), and reads the payout table.** At minute 0 the rival wrote down that
  10/7/5/4/3/2/1/0 = (players outlasted) + 3 x [1st] + 1 x [2nd], and that under Malmuth-Harville P(i outlasts j) =
  s_i / (s_i + s_j). Its `icm()` returns base x E[players outlasted] + d1x x P(1st) + d2x x P(top 2), with base,
  d1x and d2x taken from the payout table: `new_table` reads `payouts` (or `points`, `payout`, `finish_points`,
  `place_points`) from the rules dict and falls back to the brief's table. That form is exact whenever every
  place from third down is worth the same step, which holds for the brief's table and for our default 8..1 (where
  it reduces to E[players outlasted]). Operator check (`icm_check.py`, 400 random stack vectors): it matches
  brute-force Harville to 1e-13 points on both, at 1.3-1.4 us per call; on top_heavy 50/25/12/6/3/2/1/1 it is off
  by up to 5.3 points with 4 or more alive. Two bugs found in its heads-up probe at minute 36 were fixed before the
  freeze: a player busting heads-up keeps the second-place bonus, and opponents who bust in the outcome being
  priced count as outlasted (`P_BUSTFIX`; +0.04 to +0.35 in its fields).
- **Every all-in decision is an ICM expected value.** At 8 bb or less, unopened, it shoves when P(all fold) x
  U(steal) + the sum over callers of P(reach) x c x (e x U(win) + (1 - e) x U(lose)) beats U(fold) by 0.003. Each
  seat behind calls with c = 0.8 x (0.10 + 1.6 / depth in bb), x 1.25 in the big blind, blended half and half with
  0.8 x its observed VPIP once it has 5 hands, and 0 for a seat flagged as a folder; e is the equity against the
  top-c range from the table. Facing a raise it treats any committing spot the same way (call of 35% or more of
  its stack, raiser all-in, effective stack 16 bb or less, or under 6 bb left after calling): fold, call and shove
  are each priced in ICM, the shove with the raiser's continue fraction taken from the price the shove gives him.
  Postflop, any call of 30% or more of its stack is an ICM comparison of fold and call.
- **Preflop above 8 bb: a positional chart, not a solver.** Open fractions by players behind 42/36/27/21/17/14/12%,
  x 1.3, scaled 0.7-1.4 by how loose the seats behind have played, x 0.6 with limpers, and 100% when every seat
  behind is a folder; 2.3-2.5 bb, or all-in when that is 40% of its stack. Facing a raise it reads the raiser's
  range from the raise size and count (20/16/12% for an open by size, 6% for a 3-bet, 3.5% beyond), blended with
  the seat's raise rate; it 3-bets a value slice (the top quarter of that range, at least 3%) and calls when equity
  plus implied odds (pairs and close suited hands, when cheap) clears the pot odds by 0.06 in position, 0.10 out.
- **Postflop is a rule table, not a sampler.** An equity proxy per made-hand category, adjusted for board pairing
  and flush and straight texture, plus outs for draws, with a multiway exponent e^(1 + 0.75 (k - 1)). It bets for
  value at 0.70, c-bets the flop 60% heads-up as the preflop raiser, barrels the turn 40% with 0.5 or a draw,
  semi-bluffs 8+ outs half the time. Facing a bet it discounts its equity by the bet size and the bettor's raise
  rate (a maniac read discounts less), and by much more when its own bet was raised. Against one loose-passive seat
  (VPIP over 0.55, raise rate under 0.2, 6+ hands) it value-bets thinner and never bluffs.
- **The opponent model is three counters.** Per seat, from the hand's history at the end of each hand: hands
  seen, VPIP, raised, and shoves (raises of 8 bb or more), with priors of 4 hands at VPIP 0.25 and raise rate 0.15.
  A seat seen in 6 or more hands with no VPIP is a *folder*: it is given 0 calls behind a shove and every open
  goes in against it. The shove-rate model was built and turned off (minute 40, -0.03 to -0.10). Compared with
  rival 3's 21 counters and four labels this is small; compared with rival 2's two Beta numbers it moves faster.
- **Reproducible and safe.** Its one RNG is `random.Random(0x5EED)`, seeded once per bot (the same constant for
  every copy), and it has no wall-clock time box, so its play is bit-reproducible. act() is wrapped in try/except
  with a legalizer that clamps raises, never folds a free check, and handles None, short or list-typed fields;
  new_table and hand_end swallow their own failures.

The four rivals spend their minutes in four places: rival 1 on hand reading, rival 2 on computation, rival 3 on
the opponent, rival 4 on the payout table. Rival 4 is the only one that reads the payouts it is given, so it is
the only one that prices all-ins on the table our engine scores. Its median decision is 20 us (3.12), the fastest
of the four with rival 1 (15 us); rival 3 is 23 us and rival 2 160-210 us.


## 4. Harness results (operator re-run on the frozen file)

`rival4_gate/gate.sh`, one process at a time, 2026-11-01 09:47 UTC, other agents' sweeps on the same 8 cores (load
average 11.0 at the start, 13.9 at the end):

```
== date / load
Sun Nov  1 09:47:32 UTC 2026
 04:47:32 up 8 days,  8:34,  0 users,  load average: 11.00, 8.92, 13.37
== md5 / size
28a0655f583ce9f5d6ac11b72bed0d72  rival_bot.py
657
== Python 3.12.12 harness, 10,000 obs, seed 1
module=rival_bot n=10000 import=0.09s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=64.1 median=20.5 p99=291.4 max=13210.3
 04:47:33 up 8 days,  8:34,  0 users,  load average: 11.00, 8.92, 13.37
== Python 3.12.12 harness, 10,000 obs, seed 2
module=rival_bot n=10000 import=0.02s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=27.8 median=20.3 p99=77.9 max=7509.1
== Python 3.12.12 control 30 us
act() us: mean=36.7 median=30.2 p99=62.5 max=8027.8
== Python 3.12.12 control 200 us
act() us: mean=309.4 median=200.5 p99=4158.7 max=12658.8
== Python 3.12.12 operator fuzz (drill 3's, given to the rival), 3,000 hostile obs
fuzz: exceptions=0 illegal=0
== Python 3.12.12 drill-2 operator fuzz, 3,000 hostile obs
fuzz n=3000 exceptions=0 illegal=0
== Python 3.12.12 internal exceptions (_act, _finalize, _set_pay wrapped to re-raise), 10,000 obs seed 3
module=rival_bot n=10000 import=0.00s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=51.3 median=21.2 p99=111.1 max=25627.9
internal exceptions: 0
== Python 3.12.12 import time x5 (fresh interpreter each) and RSS after import
0.0146 s
0.0116 s
0.0141 s
0.0127 s
0.0126 s
RSS after import 16.8 MB
RSS bare interpreter 10.2 MB
== Python 3.12.12 ICM vs brute-force Harville
brief 10/7/5/4/3/2/1/0         base=1 d1x=2 d2x=1  max spread of (Harville - icm) by alive count: 2:3.6e-15 3:3.6e-15 4:4.9e-15 5:8.9e-15 6:2e-14 7:3.5e-14 8:9.2e-14  (1.29 us/call)
ours 8..1                      base=1 d1x=0 d2x=0  max spread of (Harville - icm) by alive count: 2:1.8e-15 3:3.6e-15 4:3.6e-15 5:7.1e-15 6:1.6e-14 7:4e-14 8:9.4e-14  (1.40 us/call)
top_heavy 50/25/12/6/3/2/1/1   base=3 d1x=22 d2x=10  max spread of (Harville - icm) by alive count: 2:1.4e-14 3:1.4e-14 4:2.9 5:2.9 6:2.2 7:2.9 8:5.3  (1.36 us/call)
== Python 3.10.12 harness, 10,000 obs, seed 1
module=rival_bot n=10000 import=0.01s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=48.8 median=28.8 p99=312.4 max=9968.3
 04:47:45 up 8 days,  8:34,  0 users,  load average: 11.32, 9.09, 13.36
== Python 3.10.12 harness, 10,000 obs, seed 2
module=rival_bot n=10000 import=0.02s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=67.3 median=28.7 p99=274.9 max=17108.0
== Python 3.10.12 control 30 us
act() us: mean=73.6 median=30.4 p99=223.1 max=12029.8
== Python 3.10.12 control 200 us
act() us: mean=501.4 median=200.6 p99=8130.4 max=19007.2
== Python 3.10.12 operator fuzz (drill 3's, given to the rival), 3,000 hostile obs
fuzz: exceptions=0 illegal=0
== Python 3.10.12 drill-2 operator fuzz, 3,000 hostile obs
fuzz n=3000 exceptions=0 illegal=0
== Python 3.10.12 internal exceptions (_act, _finalize, _set_pay wrapped to re-raise), 10,000 obs seed 3
module=rival_bot n=10000 import=0.00s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=93.9 median=30.9 p99=1029.5 max=27471.7
internal exceptions: 0
== Python 3.10.12 import time x5 (fresh interpreter each) and RSS after import
0.0273 s
0.0423 s
0.0772 s
0.0418 s
0.0819 s
RSS after import 14.2 MB
RSS bare interpreter 8.5 MB
== Python 3.10.12 ICM vs brute-force Harville
brief 10/7/5/4/3/2/1/0         base=1 d1x=2 d2x=1  max spread of (Harville - icm) by alive count: 2:3.6e-15 3:3.6e-15 4:4.9e-15 5:8.9e-15 6:2e-14 7:3.5e-14 8:9.2e-14  (2.71 us/call)
ours 8..1                      base=1 d1x=0 d2x=0  max spread of (Harville - icm) by alive count: 2:1.8e-15 3:3.6e-15 4:3.6e-15 5:7.1e-15 6:1.6e-14 7:4e-14 8:9.4e-14  (2.09 us/call)
top_heavy 50/25/12/6/3/2/1/1   base=3 d1x=22 d2x=10  max spread of (Harville - icm) by alive count: 2:1.4e-14 3:1.4e-14 4:2.9 5:2.9 6:2.2 7:2.9 8:5.3  (5.86 us/call)
== end
Sun Nov  1 09:48:11 UTC 2026
 04:48:11 up 8 days,  8:34,  0 users,  load average: 13.94, 9.89, 13.51
```

Interleaved with the fixed 30-us control bot, call by call on the same observations (`overcount.py`, load 15):

```
Python 3.12.12
rival_bot  n=10000 median=23.3 p99=875.3 p999=10822.8 max=18554  >0.5ms=130  >1ms=92 (0.920%)
control30  n=10000 median=30.4 p99=707.2 p999=10606.2 max=15555  >0.5ms=112  >1ms=85 (0.850%)
rival_bot  n=10000 median=23.0 p99=703.1 p999=9068.8 max=17372  >0.5ms=105  >1ms=94 (0.940%)
control30  n=10000 median=30.4 p99=1065.5 p999=10170.2 max=17473  >0.5ms=108  >1ms=100 (1.000%)
rival_bot  n=10000 median=22.5 p99=208.2 p999=8100.4 max=14765  >0.5ms=82  >1ms=75 (0.750%)
control30  n=10000 median=30.4 p99=295.3 p999=8091.5 max=15061  >0.5ms=89  >1ms=82 (0.820%)
 04:48:31 up 8 days,  8:35,  0 users,  load average: 15.32, 10.46, 13.62
Python 3.10.12
rival_bot  n=10000 median=31.3 p99=201.0 p999=7385.5 max=11118  >0.5ms=71  >1ms=59 (0.590%)
control30  n=10000 median=30.5 p99=108.1 p999=5164.9 max=26554  >0.5ms=55  >1ms=45 (0.450%)
rival_bot  n=10000 median=30.6 p99=305.4 p999=2525.8 max=6843  >0.5ms=65  >1ms=29 (0.290%)
control30  n=10000 median=30.5 p99=99.5 p999=4032.7 max=13790  >0.5ms=39  >1ms=22 (0.220%)
rival_bot  n=10000 median=29.7 p99=215.7 p999=6171.9 max=12129  >0.5ms=68  >1ms=40 (0.400%)
control30  n=10000 median=30.5 p99=108.8 p999=4049.2 max=8030  >0.5ms=46  >1ms=32 (0.320%)
 04:48:36 up 8 days,  8:35,  0 users,  load average: 14.90, 10.46, 13.60
```

The over-1 ms rate of the rival tracks the control's run for run (0.29-0.94% against 0.22-1.00%). The control
does nothing but spin for 30 us, so those overruns are the host preempting the process, not a slow path in the
bot. The rival's own probe found the same at the freeze: all 93 calls over 250 us replayed at 34 us or less
(min of 7). It has no history replay and no sampler, so no input makes it slow: its work per decision is a few
ICM calls (1.3 us each) and table lookups.


## 5. The rival's own guess at its weaknesses

The build log names two. The model learns a seat's shove rate slowly (minute 40, heads-up against PushBot); a
shove-rate model fixed that heads-up but lost 0.03-0.10 eight-handed and was left off. And the assumed caller
width behind its shoves (`P_CALLC` 0.8) is a hedge: its archetypes call tight, the real field is unknown, and the
per-seat looseness blend only takes over after 5 hands.

Operator additions, from reading the code and the log:
1. Postflop is a rule table with no range model. Facing a bet it discounts its equity by the bet size and the
   bettor's raise rate, nothing else. A thinking opponent that bets air and checks strength is misread, as with
   rivals 2 and 3.
2. The model has one hard flag. A seat with 6 hands and no VPIP is a *folder*: it is given zero calls behind a
   shove, and every open goes in when all seats behind are folders. Nothing decays, but one call or raise clears
   the flag, so a seat that times out and then recovers is read correctly again within a hand.
3. Push/fold is only at 8 bb or less (it tested 10 and 13.5 and kept 8). Between 8 and 16 bb its first-in play is
   the chart with a 2.3 bb open; only the committed spots (facing a raise) are ICM-priced there.
4. The exact ICM depends on the payout table's shape. On a table where places from third down are not equal steps
   (top_heavy) it is silently wrong by up to 5 points.
5. Its validation is its own archetypes in its own 173-line engine, as with every rival. Its fields held two
   fixed push/fold bots (Shover, Nit) and its own snapshots, but no computed short-stack player that adapts like
   rival 2 or Hero, and no Monte Carlo bot.


## 6. Drill-rule breaches

As stated by the rival's build log:
- the first snap_m15 and snap_m30 copies were early, at m12.8 and m29;
- snap_m30 was re-copied at m30.8;
- snap_m15 was not re-copied.

Operator notes on the record (not breaches):
- The file times agree. `snap_m15.py` was last written at 12:45, so it was never re-copied. The log's "m13" line
  says "re-copied at m15"; its own "m15" line and the file time contradict that.
- `snap_m30.py` was last written at 31:05 with md5 `ec1a3251...`, the re-copy's md5 as logged. The log puts the
  re-copy at m30.8, 17 s earlier, within the agent's clock estimate. The first copy (md5 `810b27f4...`) survives
  only in the log.
- Some log labels are out of order ("m09" before "m07", "m31" before "m30.8"). Nothing changed after the freeze:
  `rival_bot.py` was last written at 40:17, is mode 444, and `snap_m45.py` (45:02) is byte-identical to it.
- The rival ran everything on the system CPython 3.10 (the scratch `__pycache__` holds only 3.10 files).


## 7. Operator judgment

**What the free team bought.** Given no philosophy, the rival spent its effort where finish points are decided:
the all-in. It found the closed form of the brief's ICM at minute 0, made it read whatever payout table the kit
passes, and put every shove, every committed call and every big postflop call through it. A heads-up probe found
two real ICM bugs (the heads-up bust bonus, opponents busting in the priced outcome), and both were fixed before
the freeze. It is the only rival of the four that prices all-ins on the table that scores it, in its own engine and
in ours. The rest is deliberately cheap: literal equity tables, a positional chart and a postflop rule table, at a
20 us median with a 15 ms import. In its own engine it was first in every field (5.6 to 7.3 against a uniform
4.00); those fields are not rival 3's, so the margins do not compare.

**What it did not buy.** No postflop sampler or range, an opponent model of three counters and one hard flag,
push/fold only to 8 bb, and no handling of any twist beyond the payout table. Against an opponent that its folder
flag does not catch, it plays its baseline, and its baseline postflop is the coarsest of the four rivals.

**Against median and top teams.** Above median: it gets the decisions that move finish points right, exactly, and
it cannot time out. Below top: a top team would put a sampler or a range model postflop and a wider solved
push/fold zone on top of this ICM.

**For our engine: the judge.** Rival 4 was built blind, with no philosophy imposed, and nobody has measured a
candidate against it, so it is the closest stand-in we have for a strong team we have not seen. It reads the
payouts it is given, so it plays the table we score, and it is bit-reproducible, so only strict-mode timeouts make
its results depend on the host. It decides between the candidate cores (Hero; `hybrid`; `hybrid3`; each with and
without the exploit layer) in **one final comparison**. Until then no candidate sits next to it beyond smoke tests,
and nobody tunes on it. The measurements in this report and in the decisions entry are rivals only.


## 8. In our engine

Integration (adapter, fields) and the rivals-only measurements are in `docs/decisions.md`, "Rival 4 in the pool (the
judge)".
