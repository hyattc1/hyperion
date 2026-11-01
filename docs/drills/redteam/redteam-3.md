# Red-team drill 3: the bot an exploitation-first rival team ships in 60 minutes

**COMPLETE, rival code frozen at minute 35 (file last written at 34:34), md5 4b36e8124818e110d659b9514f5975a0;
operator gates re-run 2026-11-01 05:23 UTC on the frozen file. A holdout: Hero is never tuned against it.**

Operator/rival drill run 2026-11-01, same protocol as drills 1 and 2 (see `redteam-1.md`, `redteam-2.md`): the
operator set up the scratch directory with the same brief, stub kit and smoke harness as drills 1 and 2, plus a
new hostile-input fuzz, kept the clock and scored. The rival was a prepared team with a coding agent, no access
to this repository and no sight of `rival1_bot.py` or `rival2_bot.py`. It built `rival_bot.py` in the timed window
with a design philosophy different from both earlier rivals: exploitation first. The only files written into this
repository for the drill are this report and the bot (`rival3_bot.py`, byte-identical to the frozen file). The
simulator plays it as `rival3` through `hyperion/sim/rivals/rival3.py`.

Scratch directory (brief, kit, harness, fuzz, engine, archetypes, table generator, A/B outputs, snapshots):
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/redteam3/`
Operator gate re-run (scripts and raw output): `.../scratchpad/rival3_gate/`

Clock: T0 = 2026-11-01 04:32:12 UTC (`T0.txt`). Frozen file md5 `4b36e8124818e110d659b9514f5975a0`. Snapshots:
`snap_m15.py` (md5 `e9c9c4cd...`, file time 14:55), `snap_m30.py` (`0c925d27...`, 30:00), `snap_m45.py` (45:04,
identical to the frozen file).

## Key numbers

All harness rows are the operator's re-run on the frozen file, with the 8-core WSL2 host at load average 8.4-10.8
(five sweep workers belonging to another agent were running). The tail-latency rows are the host's, not the bot's:
see section 4.

| Measure | Result |
|---|---|
| Harness, CPython 3.12 (project venv), 10,000 random legal obs, seeds 1 and 2 | 0 exceptions, 0 illegal, 0 fold-when-check-legal |
| act() latency, 3.12 | seed 1: mean 63.0 us, median 23.5, p99 527, max 8,296; seed 2: mean 60.0, median 23.2, p99 280, max 10,173. A fixed 30-us control bot at the same moment: median 30.2, p99 610, max 9,019 |
| Harness, system CPython 3.10, 10,000 obs, seeds 1 and 2 | 0 exceptions, 0 illegal; seed 1: mean 39.2 us, median 32.1, p99 182, max 2,158; seed 2: mean 49.5, median 32.1, p99 314, max 12,423 |
| Over 1 ms, rival and 30-us control interleaved on the same obs, 3 x 10,000 | 3.12: rival 0.10-0.40%, control 0.16-0.42%; 3.10: rival 0.21-0.65%, control 0.12-0.45% |
| Import time / memory | 0.019-0.024 s (3.12), 0.046-0.061 s (3.10), five fresh interpreters each; nothing is computed at import (the equity tables are literals generated offline in the window) / 16.5 MB RSS after import, 10.1 MB for a bare interpreter (3.12) |
| Internal exceptions (`_act` and `_replay` wrapped to re-raise; the bot has no DEBUG switch), 10,000 obs | 0 (3.12 and 3.10) |
| Hostile-input fuzz, 3,000 obs: the drill-3 operator fuzz, and drill 2's fuzz | 0 exceptions, 0 illegal, both fuzzers, both interpreters |
| Size | 724 lines (658 non-blank non-comment, including four long table literals), one file, stdlib only |
| Rival's own engine, frozen file, 1,000 tables per field (uniform = 4.00; the rival's ± is one standard error) | F1 7.78 ± 0.09 (next best tag 5.20); F2 7.15 ± 0.11 (shark 4.45); F3 7.01 ± 0.10 (shark 4.90); F4 7.29 ± 0.10 (shark 4.49). First in every field; 39-52% firsts |
| Head-to-head with its own snapshots, rival's engine, 600 tables | final 5.14, snap_m15 4.91, snap_m30 4.82, then nit 3.84, shark 3.77; second field final 6.72, snap_m30 6.19 |
| hand_end history withheld (frozen file, rival's engine, 600 tables) | F2 6.71 (7.15 with it), F3 6.68 (7.01): 0.33-0.44 lower |
| Engine wall-clock > 1 ms (counted, not folded), frozen file | 12-80 per 1,000-table run (0.008-0.056% of decisions), two processes |
| **In our engine** (`rival3`, 1,600 duplicate tables, strict, seed 7; `docs/decisions.md`, "Rival 3 in the pool") | `holdout`: rival 3 first at 6.11 ± 0.10, Hero 5.37, Hero - rival3 **-0.74 ± 0.16** paired (rival 1 in that seat on the same seeds: -0.14 ± 0.16). `top3`: rival2 5.03, rival3 4.93, rival1 4.82 (each pair within noise), Hero 4.45, Hero - rival3 -0.48 ± 0.16. One rival 3 among seven Heroes 5.00 ± 0.11; Hero among seven rival 3s 4.11 ± 0.11 (uniform 4.50) |
| Latency and timeouts in our engine | p50 29-32 us, p99 150-330 us through the adapter; 0 exceptions, 0 illegal in 3.87 million decisions; over 1 ms 0.2-0.7% depending on host load (Hero 0.1-0.5%, rival 2 3.1% in the same runs) |

The rival's fields (`ab.sh`; seven archetypes from its own `field.py` plus the bot): F1 nit, tag, maniac, station,
random, pusher, crash (a dead seat); F2 nit, tag, lag, shark (push/fold to 20 bb), pusher, mctimeout (sane preflop,
auto-folds postflop), station; F3 nit, tag, lag, shark, pusher, maniac, random; F4 tag, lag, shark, nit, pusher,
station, mctimeout. F3 and F4 put blind posts into the history, F1 and F2 do not.


## 1. The brief as given to the rival (verbatim, same as drills 1 and 2)

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


`kit.py` is byte-identical to drills 1 and 2 (reproduced in `redteam-2.md` §1). `harness.py` is byte-identical apart
from a two-line docstring at the top. New in this drill, the operator supplied a hostile-input fuzz before T0:

### fuzz.py (operator, verbatim)

```python
"""Hostile observations: missing/None fields, lists for sets, inconsistent sizes. act() must stay legal."""
import random, rival_bot
from kit import Obs
import harness
rng = random.Random(9); bot = rival_bot.Bot(); bad = exc = 0
for i in range(3000):
    o = harness.rand_obs(rng, 1 + i % 200)
    k = rng.randrange(12)
    if k == 0: o.history = None
    elif k == 1: o.bets = None
    elif k == 2: o.in_hand = None
    elif k == 3: o.legal = list(o.legal)
    elif k == 4: o.blinds = None
    elif k == 5: o.hole = list(o.hole); o.board = list(o.board)
    elif k == 6: o.history = [(99, 'raise'), ('x', None), (0, ('weird', -5)), (1,)]
    elif k == 7: o.pot = None
    elif k == 8: o.stacks = o.stacks + [500, 500]
    elif k == 9: o.min_raise, o.max_raise = o.max_raise, o.min_raise  # inconsistent
    elif k == 10: o.hand_no = None
    try:
        a = bot.act(o)
    except Exception as e:
        exc += 1; print('EXC', k, e); continue
    legal = set(o.legal)
    lo, hi = min(o.min_raise, o.max_raise), max(o.min_raise, o.max_raise)
    ok = a[0] in legal and (a[0] != 'raise' or (isinstance(a[1], int) and lo <= a[1] <= hi))
    if not ok: bad += 1; print('BAD', k, a, legal, o.min_raise, o.max_raise)
    if i % 50 == 0: bot.new_table(None, None, None); bot.hand_end(None)
print('fuzz: exceptions=%d illegal=%d' % (exc, bad))
```

### The philosophy given to the rival

Exploitation first. A fast chart and push/fold baseline, plus a per-seat model that flags dead seats, stations,
maniacs and nits and changes play per opponent. The rival added, on its own, that every all-in decision goes
through an O(n) finish-order ICM (minute 14, below).


## 2. Build log (rival, verbatim)

# Rival team (read-and-exploit) build log
T0 = 2026-11-01T04:32:12Z (T0.txt). Times are minutes after T0.

- m00: read BRIEF/kit/harness/fuzz. Notes: fuzz swaps min/max_raise (clamp to [min,max]), legal may be list,
  history may hold junk tuples, bets/in_hand/blinds/pot/hand_no may be None. Plan: one file, every act()
  wrapped with a legalizer; model built incrementally from obs.history (dedupe by hand_no + index).
- m01: 7-card evaluator (bitmask straight/top5 tables), unit-tested vs 16 hands; ~2 us/eval.
- m02: offline MC table gen_table.py: equity of 169 classes vs random and vs top-w ranges (10 widths), 1k samples. Launched a 4k-sample rerun (table_v2) in background.
- m06: rival_bot v1 assembled (src_head + ev + table + src_bot): per-seat model replayed from history
  (VPIP/PFR, unopened fold/limp/raise, fold-to-raise, 3bet, shove rate, postflop fold-to-bet/bet rate,
  dead-seat signal = BB folds unraised / folds with check). Preflop: push/fold <=13bb driven by fold
  equity behind; RFI chart by #behind; steal EV vs folders; all-in calls by equity vs estimated range
  (+ICM margin). Postflop: hand-class equity proxy + draws; value thin vs stations, bluff only vs folders.
  harness 10k: 0 exc / 0 illegal, p99 175us (one 2.4ms outlier, first call/GC); fuzz clean; internal
  swallowed exceptions 0 on 10k.
- m06: switched to table_v2 (4k samples vs range, 8k vs random). build.sh assembles rival_bot.py.
- m07: engine.py (8 seats, side-pot layering, schedule every 25 hands, 200 cap, places by bust order with
  bigger start stack placing higher, Harville ICM at cap, timeouts/exceptions = fold, also when check is
  legal; optional blind posts in history). Verified chip conservation + 32 pts per table over 60 tables.
  field.py archetypes: nit, tag, lag, shark (push/fold <=20bb), maniac, station, random, pusher, crash
  (dead seat), mctimeout (sane preflop, auto-folds postflop). ab.sh = 4 fields x N tables, 2 procs.
- m08: v1 on 200 tables/field: F1 4.75 pts (tag 6.00 top), F2 4.71, F3 5.26, F4 5.56. 30% wins but busting
  early. Bust replays: calling shoves with 79o/Q6o/64o/34o. BUG: pot odds counted the shover's full
  8,000 bet, not the part I can win (req ~0.19). Also multiway all-ins used eq*0.85.
- m09: fix: pot capped at my total; multiway eq^(1+0.75(k-1)); shover range = pfr*1.1 (not shv*pfr*2).
  400 tables/field: F1 6.71 (+1.96), F2 6.27 (+1.56), F3 5.99 (+0.73), F4 6.33 (+0.77). ME is #1 in all four.
- m10: v2 postflop: a raise over my bet costs -0.12 equity; facing >35% of stack with <0.6 and no draw
  needs >=50%; maniac bonus only for bets, not raises. 400 tables: F1 6.68, F2 6.49, F3 6.15, F4 6.49
  (F2-F4 up ~0.16). Slow>1ms spikes (6-11 ms) traced: no GC events in those calls, history length 0-7;
  they are OS preemption from 2 parallel sims on a shared WSL box, not bot work.
- m11: diag.py (model readout per archetype at hands 25/60, with/without hand_end history): crash is
  flagged dead 97% by hand 25; nit false-dead 10% (h>=10 and vpip==0) -> rule moved to h>=22.
  Without end-of-hand history the model gets ~half the samples but the same ordering.
- m12-13: A/B 1000 tables/field (SE ~0.1/field): v3 6.85/6.34/6.15/6.21; weaker priors (v4)
  6.84/6.23/6.03/6.12; v5 (v4 priors, old station rule) 6.85/6.22/6.08/6.29. No win -> kept v3 priors
  plus the stricter dead rule. ab.sh output parse fixed.
- m14: snap_m15.py taken (md5 e9c9c4cd...). bustcat.py: most busts are deep all-in calls with top-7%
  hands vs pushers/maniacs. ICM check with engine.icm: at 8 x 2000 a pure flip needs 67% equity
  (6 left 61%, 4 left 60%, HU 50%) -> my +0.02..0.05 margin was far too small.
  Found: for payouts 10/7/5/4/3/2/1/0, pts(place) = 8 - place + 3[1st] + [2nd], and Harville is
  Plackett-Luce so P(j ahead of i) = sj/(si+sj): exact ICM in O(n) (verified = exact Harville on
  random stacks). Cost ~5 us.
- m15: v6: every all-in decision (short push/fold, call/reshove when committed) now compares ICM EV of
  fold / steal / win / lose, with fold equity and caller range from the per-seat model.
  1000 tables/field: F1 7.63 (+0.78 vs v3), F2 6.65 (+0.31), F3 6.61 (+0.46), F4 6.69 (+0.48).
- m16: v7: 3bet+ pots always go through the ICM all-in EV; postflop calls of >=45% of stack need
  max(pot odds, ICM-required equity). 1000/field: F1 7.70, F2 6.99, F3 6.86, F4 6.98 (+0.07..+0.34 vs v6).
- m18: slow>1ms counts (200-290 per 200k decisions) investigated: replaying each slow decision with the
  pickled bot state takes 22-35 us; CPU p50 28 us, p99 131 us under 2-proc load; load avg 3.2 on the box.
  The spikes are steal/preemption, not code paths.
- m20: A/B short-stack (push/fold) threshold: 16bb 7.66/6.92/6.76/6.90, 13bb 7.70/6.99/6.86/6.98,
  10bb 7.78/6.97/6.91/6.97 -> 10bb (v8). Box load avg hit 12.6 on 8 cores (other work): sims slowed and
  harness p99 jumped to 1.6 ms with a median of 33 us; latency gate must be re-run when load drops.
- m21: hardening: string cards ('As') parsed, duplicate/out-of-range cards -> safe fallback, model replay
  skipped for histories >160 entries (bounded time), hand_end history capped at 200.
- m22: no-end-of-hand-history mode (hand_end gets None): F2 6.63 / F3 6.67 vs ~6.9-7.0 with it; the model
  still pays but loses ~0.3 when only act-time history is visible. Looser f2r prior (0.7): 6.75/6.60, noise.
- m24-27: A/B at 600 tables/field (box load avg 14-16): v8 7.78/6.88/6.92/7.08; opens x1.2 7.81/6.86/6.88/7.03;
  bluffs x0.4 7.87/6.88/6.78/7.12; thinner value (0.55/0.48) 7.74/6.82/6.84/7.04. All within noise or
  worse -> keep v8.
- m30: snap_m30.py = v8 (md5 0c925d27190d93a95066c97236cd709b). Postflop call margin A/B: +0.07 -> 7.83/6.87/7.04/7.13 (vs +0.03: 7.78/6.88/6.92/7.08).
- m33: margin +0.11 -> 7.82/6.97/7.07/7.40; +0.15 -> 7.77/7.00/7.08/7.39 (plateau). v9 = margin +0.12.
- m34: deep preflop call tightening (req+0.12, p<=max(0.17,0.6w)) 7.77/7.02/6.91/7.40 vs v9 7.80/6.97/7.05/7.40
  -> rejected. Gate on v9: harness 10k x2 seeds 0 exc / 0 illegal, p99 125 / 93 us, fuzz clean, import 0.014 s,
  0 swallowed internal exceptions.
- m36: worst-case latency probe (cold bot, long synthetic histories): replay cap lowered 160 -> 90 entries;
  p99 96/204/215/293 us at 10/30/60/90 entries.
- m35: final validation (1000 tables/field): F1 7.78 (next: tag 5.20), F2 7.15 (shark 4.45), F3 7.01 (shark 4.90),
  F4 7.29 (shark 4.49). ME first in every field. Head-to-head vs own snapshots, 600 tables:
  final 5.14 / snap_m15 4.91 / snap_m30 4.82 / nit 3.84 / shark 3.77 ...; second field final 6.72 / snap_m30 6.19 / shark 4.45.

## FREEZE
- m35: rival_bot.py frozen (made read-only). md5 4b36e8124818e110d659b9514f5975a0. No edits after this line.
- post-freeze checks (no edits): frozen file with hand_end history withheld: F3 6.68 (shark 4.93), F2 6.71
  (shark 4.49). Gate rerun on frozen file: 10k obs 0 exc / 0 illegal, p99 133 us, fuzz clean.
- m45: snap_m45.py copied from the frozen file (same md5 4b36e8124818e110d659b9514f5975a0).


## 3. The design the rival chose, and how it differs from rivals 1 and 2

Rival 1 hand-read: a typed preflop table, a fitted push formula, made-hand buckets with outs, four opponent
flags. Rival 2 computed: a 169x169 matrix, a solved push/fold table and an exact ICM curve, all built in 1.1 s of
import, with a Monte Carlo postflop. Rival 3 spent its effort on the opponent. Its baseline is deliberately
cheap and fixed, and most of its code is a per-seat model that changes the baseline seat by seat.

- **Baseline from literal tables, nothing computed at import.** A 7-card evaluator on rank counts and suit masks
  (8,192-entry straight and top-five tables, ~2 us per evaluation). The preflop objects are equity of the 169
  classes vs a random hand, a percentile ranking, and equity vs the top-w range for ten widths (3% to 100%). They
  were generated by an offline Monte Carlo inside the window (`gen_table.py`, 4,000 samples vs ranges, 8,000 vs
  random) and pasted into the file as literals. Import takes 20 ms, against rival 2's 1.1 s.
- **A per-seat model of 21 counters, replayed from the history.** Each decision replays the hand's history from
  the start and counts only the new entries: VPIP and PFR; unopened raise, limp and fold; fold, call and raise
  facing a raise (3-bet); the share of raises that are shoves; postflop fold, call and raise facing a bet; bet
  rate when not facing one. It also counts a "dead" signal: an unraised big blind that folds, or a fold when a
  check was free. hand_end replays the result's full history once more, which picks up actions that came after
  the bot's last decision. Small priors turn the counts into rates, for example fold-to-raise (f + 2.4) / (n + 4).
  The labels come from thresholds on those rates. A seat is *dead* once it has a dead signal and zero VPIP over
  three hands, or zero VPIP over 22. A *station* has VPIP > 0.5 and folds to bets < 35%. A *maniac* bets more
  than half the time unprompted, or has PFR > 0.4. A *nit* has VPIP < 0.3 and bets < 25%. Blind posts are
  filtered by name, or inferred when the first raise is at most the big blind. Replay is skipped past 90 entries
  to bound time.
- **Preflop: open by players behind, steal by measured fold equity.** Open fractions by players behind are
  48/36/27/21/17/14/12%, times 1.2 at four or fewer alive and times 0.75 if anyone behind 3-bets more than 20%. It
  also raises any hand up to the 85th percentile when the chip EV of a steal is positive against the product of
  the per-seat fold probabilities, and any two cards when that product is above 0.9: against dead blinds it
  opens 100%. Facing a raise, it reads the raiser's range as PFR x 1.25 (x 1.1 for a shove), or 3-bet rate x 0.9
  in a 3-bet pot, and takes its equity against that range from the table. Above 10 bb it 3-bets a value slice,
  set-mines pairs that cost at most 7% of its stack, and calls when equity plus implied odds clears the pot odds
  by 0.08.
- **Every all-in decision is an ICM expected value.** At 10 bb or less, unopened, it pushes when
  P(all fold) x U(steal) + (1 - P(all fold)) x (e x U(win) + (1 - e) x U(lose)) beats U(fold). P(all fold) is the
  product of the seats' modelled fold probabilities, and e is equity against the loosest likely caller's range,
  with a multiway exponent. It treats any spot where it commits (call >= 40% of its stack, effective stack
  <= 18 bb, raiser all-in, or a 3-bet pot) the same way, comparing fold, call and shove. Postflop calls of 45% of
  its stack or more need max(pot odds, the ICM-required equity).
- **The ICM is exact and O(n).** The rival noticed at minute 14 that the payouts 10/7/5/4/3/2/1/0 are
  8 - place + 3 x [1st] + [2nd]. Under Malmuth-Harville (a Plackett-Luce model) P(j finishes ahead of i) =
  s_j / (s_i + s_j). So E[points] = 8 - (1 + sum_j s_j/(s_i+s_j)) + 3 s_i/T + sum_j (s_j/T)(s_i/(T - s_j)), one pass
  over the stacks. Operator check: over 300 random stack vectors with 2-8 alive it matches brute-force Harville
  to 3e-14 points, at 1.6 us per call on 3.12. That is exact per decision, where rival 2 ran a 39 us subset DP
  once per hand and interpolated. The shortcut depends on these payouts having that shape; a different payout
  table would break it.
- **Postflop is a rule table, not a sampler.** An equity proxy from made-hand category against board category,
  kicker and pair rank, plus outs-based draw equity, with a multiway exponent. It value-bets at 0.60 (0.52 with a
  station in the hand) and bets bigger into stations. It bluffs only with no station in the hand and two or fewer
  opponents, at a frequency set by their fold-to-bet (0.9 if they fold more than 85%). Facing a bet it adds 0.08
  against a maniac, subtracts 0.08 against a nit, 0.03 against a station's bet, and 0.12 when its own bet is
  raised. There is no Monte Carlo anywhere, so its play is bit-reproducible: its one RNG is seeded once per bot,
  not per table, and it has no wall-clock time box.
- **Safety.** act() is wrapped in try/except with a legalizer that clamps raises and never folds a free check.
  The legalizer also handles cards as strings, duplicate or out-of-range cards, and None, short or list-typed
  fields. There is no DEBUG switch; the operator wrapped `_act` and `_replay` to surface internal exceptions
  (section 4).

The three rivals spend their minutes in different places: rival 1 on hand reading, rival 2 on computation, rival 3
on reading the opponent. Speed follows from that. Rival 3's median decision is 23 us (3.12), between rival 1's
15 us and rival 2's 160-210 us. Its cost is the history replay, which grows with the length of the hand, not a
sampler.


## 4. Harness results (operator re-run on the frozen file)

`rival3_gate/gate.sh`, one process at a time, 2026-11-01 05:23 UTC, five CPU-bound sweep workers from another
agent on the same 8 cores (load average 8.4 at the start, 9.7 at the end):

```
== md5 / size
4b36e8124818e110d659b9514f5975a0  rival_bot.py
724
== Python 3.12.12 harness, 10,000 obs, seed 1
module=rival_bot n=10000 import=0.05s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=63.0 median=23.5 p99=526.8 max=8295.8
 01:23:25 up 8 days,  4:10,  0 users,  load average: 8.40, 6.20, 7.71
== Python 3.12.12 harness, 10,000 obs, seed 2
module=rival_bot n=10000 import=0.04s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=60.0 median=23.2 p99=280.0 max=10172.7
== Python 3.12.12 control 30 us
act() us: mean=71.0 median=30.2 p99=609.6 max=9019.4
== Python 3.12.12 control 200 us
act() us: mean=383.4 median=200.4 p99=4181.5 max=20122.1
== Python 3.12.12 rival's own fuzz, 3,000 hostile obs
fuzz: exceptions=0 illegal=0
== Python 3.12.12 drill-2 operator fuzz, 3,000 hostile obs
fuzz n=3000 exceptions=0 illegal=0
== Python 3.12.12 internal exceptions (_act and _replay wrapped to re-raise), 10,000 obs seed 3
module=rival_bot n=10000 import=0.00s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=34.4 median=23.8 p99=155.1 max=4614.6
== Python 3.12.12 import time x5 (fresh interpreter each) and RSS after import
0.0237 s
0.0197 s
0.0218 s
0.0209 s
0.0192 s
RSS after import 16.5 MB
RSS bare interpreter 10.1 MB
== Python 3.10.12 harness, 10,000 obs, seed 1
module=rival_bot n=10000 import=0.02s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=39.2 median=32.1 p99=181.9 max=2157.7
 01:23:34 up 8 days,  4:10,  0 users,  load average: 8.70, 6.35, 7.74
== Python 3.10.12 harness, 10,000 obs, seed 2
module=rival_bot n=10000 import=0.02s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=49.5 median=32.1 p99=314.2 max=12422.9
== Python 3.10.12 control 30 us
act() us: mean=37.9 median=30.3 p99=161.6 max=8437.7
== Python 3.10.12 control 200 us
act() us: mean=419.1 median=200.6 p99=4370.9 max=28006.4
== Python 3.10.12 rival's own fuzz, 3,000 hostile obs
fuzz: exceptions=0 illegal=0
== Python 3.10.12 drill-2 operator fuzz, 3,000 hostile obs
fuzz n=3000 exceptions=0 illegal=0
== Python 3.10.12 internal exceptions (_act and _replay wrapped to re-raise), 10,000 obs seed 3
module=rival_bot n=10000 import=0.00s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=81.7 median=33.5 p99=987.4 max=8432.5
== Python 3.10.12 import time x5 (fresh interpreter each) and RSS after import
0.0466 s
0.0478 s
0.0463 s
0.0610 s
0.0568 s
RSS after import 14.0 MB
RSS bare interpreter 8.5 MB
== end
Sun Nov  1 05:23:44 UTC 2026
 01:23:44 up 8 days,  4:10,  0 users,  load average: 9.68, 6.63, 7.82
```

Interleaved with the fixed 30-us control bot, call by call on the same observations (`overcount.py`, load 10-11):

```
Python 3.12.12
rival_bot  n=10000 median=24.8 p99=179.4 p999=4069.5 max=9150  >0.5ms=36  >1ms=24 (0.240%)
control30  n=10000 median=30.3 p99=158.1 p999=4041.9 max=12178  >0.5ms=38  >1ms=27 (0.270%)
rival_bot  n=10000 median=24.6 p99=157.5 p999=4048.4 max=8838  >0.5ms=19  >1ms=10 (0.100%)
control30  n=10000 median=30.3 p99=117.5 p999=4023.2 max=4110  >0.5ms=20  >1ms=16 (0.160%)
rival_bot  n=10000 median=24.8 p99=176.2 p999=4095.9 max=7630  >0.5ms=44  >1ms=40 (0.400%)
control30  n=10000 median=30.3 p99=162.4 p999=4044.3 max=5225  >0.5ms=55  >1ms=42 (0.420%)
Python 3.10.12
rival_bot  n=10000 median=34.0 p99=198.0 p999=4108.7 max=12794  >0.5ms=31  >1ms=21 (0.210%)
control30  n=10000 median=30.4 p99=132.5 p999=4017.6 max=4248  >0.5ms=17  >1ms=12 (0.120%)
rival_bot  n=10000 median=33.4 p99=192.4 p999=4210.8 max=13591  >0.5ms=57  >1ms=50 (0.500%)
control30  n=10000 median=30.5 p99=95.9 p999=4039.3 max=8057  >0.5ms=46  >1ms=41 (0.410%)
rival_bot  n=10000 median=34.6 p99=317.8 p999=4297.1 max=9344  >0.5ms=74  >1ms=65 (0.650%)
control30  n=10000 median=30.5 p99=195.4 p999=4049.3 max=7456  >0.5ms=56  >1ms=45 (0.450%)
```

The over-1 ms rate of the rival tracks the control's run for run (0.10-0.65% against 0.12-0.45%). The control
does nothing but spin for 30 us, so those overruns are the host preempting the process, not a slow path in the
bot. Thread CPU time does not separate the two on this WSL2 host: the hypervisor's steal shows up in it too
(`cputime.txt`). The bot's own worst path is the history replay. With a 90-entry history (the cap) on a cold bot
its CPU median is 38 us (3.12) / 49 us (3.10). The rival's own probe on a quieter box put p99 at 293 us for 90
entries. Compared with drill 2, the clean-host numbers cannot be reproduced while the other agent's sweeps run.
What can be said is that rival 3 spends a tenth of rival 2's time per decision, so it is preempted past 1 ms far
less often than rival 2 on the same host, about as often as a 30-us bot.


## 5. The rival's own guess at its weaknesses

The build log names one. With `hand_end` passing no history, the model gets about half its samples (actions after
its own last decision in each hand are never seen) and scores about 0.3 lower. The frozen file in its own engine
with hand_end history withheld scored 6.71 (F2) and 6.68 (F3), against 7.15 and 7.01 with it.

Operator additions, from reading the code and the log:
1. Its model is the exploit, and every number in it comes from the history. A kit whose history is per street,
   carries blind posts in an unexpected shape, or is absent cripples the model. The bot then falls back to
   priors and a fixed chart, and it has no Monte Carlo or solved table to fall back on.
2. The labels are thresholds on rates with small priors, so they move fast. A bot that plays tight for 20 hands
   and then opens up is read as a nit for that long. One with zero VPIP over 22 hands is read as dead and stolen
   from with any two cards. Nothing decays.
3. The postflop rule table is coarse: one equity proxy per made-hand category, with no range model. Its fields
   contained archetypes that bet when they connect, and against those that is enough. A thinking opponent that
   bets air into it and checks strength will be misread the same way as by rival 2.
4. The exact O(n) ICM is specific to 10/7/5/4/3/2/1/0. Any other payout table makes `_icm1` wrong silently. Our
   simulator's default is linear 8..1, so in every run in our engine it prices all-ins with the brief's table
   rather than the one that scores it. Rivals 1 and 2 share the mismatch.
5. Its validation is its own archetypes in its own 230-line engine, as with rivals 1 and 2. None of its fields
   contained a computed short-stack player like rival 2 or Hero.


## 6. Drill-rule breaches

As stated by the rival's agent:
- snap_m15 was taken at minute 14.
- Once, it briefly ran 3 processes instead of 2.

Operator notes on the record (not breaches). The file times agree with the first item: `snap_m15.py` was written
at 14:55. The build log lists an "m36" entry (replay cap lowered from 160 to 90) above the "m35" final validation
and the freeze line. The frozen file contains that change (`len(o.history) <= 90`) and was last written at 34:34,
so the label is out of order; nothing was edited after the freeze. `snap_m45.py` is byte-identical to the frozen
file.


## 7. Operator judgment

**What the exploitation-first team bought.** It shipped a working opponent model, which neither earlier rival
had. Rival 2's two Beta numbers barely moved off their priors in our engine. Rival 1's four flags were coarse
but did widen its steals against Hero. Rival 3 keeps 21 counters per seat, turns them into labels within
10-25 hands, and changes four things per seat: steal width (any two cards into dead blinds), the caller range
behind its pushes, bluff frequency (never into a station) and its read of a bet (believe a nit, discount a
maniac). In its own engine this is worth a lot: first in every field at 7.0-7.8 points, with the next bot at
4.5-5.2. Its rivals were archetypes with fixed tendencies, which is exactly what a per-seat model reads best. It
also found the closed form for this payout table's ICM and put every all-in decision through it exactly, at
1.6 us. That is the best ICM of the three rivals. All of it decides in a median 23 us with a 20 ms import, so
it is the least exposed to the 1 ms budget of any of them after rival 1.

**What it did not buy.** Its baseline is the weakest of the three. A fixed open chart by players behind, a
rule-table postflop with no sampling and no range, and push/fold only at 10 bb or less (it tested 13 and 16 bb and
kept 10). Against an opponent that its labels do not separate, such as a competent short-stack player whose
fold rates sit near the priors, it plays that baseline. Its whole edge also depends on the kit's history. With
none at hand_end it loses about 0.3-0.4; with none at all it would be a chart bot.

**Against median and top teams.** A median team is a fixed rule-bot, and fixed rule-bots are exactly what this
model was built and tuned to read: it beat its archetypes by 2-3 points per table. A top team in this window
would ship this model on top of rival 2's computed baseline, and would decay the labels. Rival 3 sits
with rivals 1 and 2, clearly above median and below top, and its gap to top is on the baseline side, where
rival 2's strength is.

**For our engine.** Keep rival 3 as the holdout. It reads Hero, rather than playing a baseline that ignores it,
so it is the rival most likely to find a tendency that Hero's tuning against rivals 1 and 2 introduced. If a
Hero change gains against rival 1 and rival 2 but loses against rival 3, the change was fitted to the two
rivals rather than to the game. Hero is never tuned on it, and the numbers against it are reported, not
optimised. Measurements in our engine are in `docs/decisions.md`, "Rival 3 in the pool". In short, it is the
strongest bot on `holdout` (6.11, first at half the tables, 0.74 ahead of Hero, where rival 1 in that seat is 0.14
ahead). It is level with rivals 1 and 2 on `top3`, and it beats Hero in both mirrors. Its holdout edge halves in
measure mode (-0.36), where bots that overrun are no longer folded for it to steal from.
