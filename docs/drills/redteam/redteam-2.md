# Red-team drill 2: the bot a computation-first rival team ships in 60 minutes

**COMPLETE, last updated 2026-10-31 12:29 UTC, minute 33 of 60 (rival code frozen at minute 28, md5 1ad3b05acb26fff86130ea755dbb0148; operator scoring and report finished at minute 33)**

Operator/rival drill run 2026-10-31, same protocol as drill 1 (see `redteam-1.md`): the operator
set up the scratch directory, reused drill 1's brief, stub kit and smoke harness verbatim, kept the
clock and scored; the rival (a prepared computation-first team with a coding agent, no access to
this repository and no sight of `rival1_bot.py`) built `rival2_bot.py` in the timed window with a
deliberately different design philosophy from rival 1. The only files written into this repository
are this report and the bot.

Scratch directory (brief, kit, harness, engine, archetypes, scenarios, fuzz, A/B logs, snapshots):
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/redteam2/`

Clock: T0 = 2026-10-31 11:56:12 UTC. Bot file md5 at this checkpoint: `1ad3b05acb26fff86130ea755dbb0148`.

## Key numbers

| Measure | Result |
|---|---|
| Harness, CPython 3.12, 10,000 random legal obs (frozen file, clean machine) | 0 exceptions, 0 illegal, 0 fold-when-check-legal |
| act() latency, 3.12 | mean 162 us, median 214, p99 291, max 1,025 us (one outlier; replays <= 452 us; control bot max 361) |
| Harness, system CPython 3.10, 10,000 obs | 0 exceptions, 0 illegal; mean 178 us, median 268, p99 300, max 514 us |
| Import time / memory | 1.10 s (3.12), 1.33 s (3.10) for 1,500 Monte Carlo boards, the 169x169 matrix, the push/fold solve and the ICM table / 17.9 MB RSS |
| Internal exceptions (DEBUG re-raise), 4,000 obs | 0 |
| Hostile-input fuzz, 3,000 obs | 0 exceptions, 0 illegal |
| Size | 1,476 lines (1,320 non-blank non-comment), one file, stdlib only |
| Rival's own engine, frozen file, 100 tables each (uniform = 4.00) | mixed field 7.11 +- 0.29; 7 tight 5.29 +- 0.36 (they average 3.82); 7 semi-sane 6.22 +- 0.32 (3.69); 7 min-raise 9.01 +- 0.14; 1 push + 6 tight 5.62 +- 0.31; self-play 4.07 +- 0.28 (symmetric) |
| Heads-up from 2000 chips, frozen file, 100 matches each | 98% vs station, 81% vs tight, 76% vs random, 75% vs semi-sane, 71% vs maniac, 64% vs push-bot |
| Engine wall-clock > 1 ms (counted, not folded) | 22-109 per 100-table run (about 0.1-0.4% of decisions) with 12 processes on 8 cores; trivial 5-us archetype bots in the same runs peaked at 15.6 ms |
| **Operator head-to-head vs rival 1** (after the freeze; rival 1 executed from the repo; rival 2's engine and archetypes), 600 tables each | 6 semi-sane: rival 2 5.96 +- 0.12, rival 1 5.55 +- 0.13; 6 tight: rival 2 4.74 +- 0.14, rival 1 5.14 +- 0.16; mixed (2 tight, 2 semi-sane, maniac, random): 6.22 vs 6.30 +- 0.12; heads-up: rival 2 wins 56% of 600 matches |
| Engine > 1 ms, head-to-head runs | rival 2 51-96 per 600 tables (about 0.1% of ~120 decisions/table), rival 1 7-13; single-process run: rival 2 9, rival 1 1 per 150 tables |


## 1. The brief as given to the rival (verbatim from drill 1)

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


### kit.py (stub provided, verbatim)

```python
"""Minimal stand-in for the tournament kit: the observation and Agent shapes promised in BRIEF.md."""


class Obs:
    __slots__ = ('hole', 'board', 'street', 'seat', 'button', 'stacks', 'bets', 'in_hand', 'pot',
                 'to_call', 'min_raise', 'max_raise', 'legal', 'hand_no', 'blinds', 'history')

    def __init__(self, **kw):
        for k in self.__slots__:
            setattr(self, k, kw.get(k))

    def __repr__(self):
        return 'Obs(' + ', '.join('%s=%r' % (k, getattr(self, k)) for k in self.__slots__) + ')'


class Agent:
    def new_table(self, rules, seat, n_players):
        pass

    def act(self, obs):
        raise NotImplementedError

    def hand_end(self, result):
        pass
```


### harness.py (operator smoke harness, verbatim)

```python
import importlib, random, statistics, sys, time, traceback
from kit import Obs

LEVELS = [(10, 20), (15, 30), (25, 50), (50, 100), (75, 150), (100, 200), (150, 300), (200, 400)]
KINDS = ['fold', 'check', 'call', 'raise']


def rand_obs(rng, hand_no):
    n = rng.randint(2, 8); deck = list(range(52)); rng.shuffle(deck)
    street = rng.choice([0, 0, 1, 2, 3]); nb = (0, 3, 4, 5)[street]
    seat, button = rng.randrange(n), rng.randrange(n); sb, bb = LEVELS[min(7, (hand_no - 1) // 25)]
    stacks = [rng.choice([0, rng.randint(1, 6000)]) for _ in range(n)]; stacks[seat] = rng.randint(1, 6000)
    in_hand = [s > 0 and rng.random() < 0.8 for s in stacks]; in_hand[seat] = True
    if sum(in_hand) < 2: o = (seat + 1) % n; in_hand[o] = True; stacks[o] = max(stacks[o], 1)
    bets = [rng.choice([0, 0, bb, 2 * bb, 3 * bb, rng.randint(0, 800)]) if in_hand[i] else 0 for i in range(n)]
    bets[seat] = rng.choice([0, 0, sb, bb]); mx = max(bets)
    to_call = min(mx - bets[seat], stacks[seat]); pot = rng.randint(0, 3000) if street else 0
    legal = {'call', 'fold'} if to_call > 0 else {'check'}
    max_raise = bets[seat] + stacks[seat]; levels = sorted(set(bets)); last = levels[-1] - (levels[-2] if len(levels) > 1 else 0)
    min_raise = min(mx + max(bb, last), max_raise)
    if max_raise > mx: legal.add('raise')
    hist = [(rng.randrange(n), (rng.choice(KINDS), rng.randint(0, 600))) for _ in range(rng.randint(0, 10))]
    return Obs(hole=tuple(deck[:2]), board=tuple(deck[2:2 + nb]), street=street, seat=seat, button=button,
               stacks=stacks, bets=bets, in_hand=in_hand, pot=pot, to_call=to_call, min_raise=min_raise,
               max_raise=max_raise, legal=legal, hand_no=hand_no, blinds=(sb, bb), history=hist)


def main(mod, n=2000, seed=1):
    t = time.perf_counter(); Bot = importlib.import_module(mod).Bot; imp = time.perf_counter() - t
    rng = random.Random(seed); bot = Bot(); bot.new_table({'starting_stack': 2000, 'hand_cap': 200}, 0, 8)
    exc = ill = soft = 0; times = []; first = None
    for i in range(n):
        if i % 40 == 0: bot.new_table({'starting_stack': 2000}, rng.randrange(8), 8)
        obs = rand_obs(rng, 1 + (i % 200)); err = None
        t = time.perf_counter_ns()
        try: a = bot.act(obs)
        except Exception: a = None; exc += 1; err = traceback.format_exc()
        times.append((time.perf_counter_ns() - t) / 1000)
        ok = isinstance(a, tuple) and len(a) == 2 and a[0] in obs.legal and (a[0] != 'raise' or (isinstance(a[1], int) and obs.min_raise <= a[1] <= obs.max_raise))
        if a is not None and not ok: ill += 1; err = err or 'ILLEGAL %r legal=%r min=%s max=%s' % (a, obs.legal, obs.min_raise, obs.max_raise)
        if ok and a[0] == 'fold' and 'check' in obs.legal: soft += 1
        if err and first is None: first = err + '\n' + repr(obs)
        if i % 7 == 0: bot.hand_end({'hand_no': obs.hand_no, 'stacks': obs.stacks})
    print('module=%s n=%d import=%.2fs exceptions=%d illegal=%d fold_when_check_legal=%d' % (mod, n, imp, exc, ill, soft))
    print('act() us: mean=%.1f median=%.1f p99=%.1f max=%.1f' % (statistics.mean(times), statistics.median(times), sorted(times)[int(n * 0.99)], max(times)))
    if first: print('FIRST PROBLEM:\n' + first)
    return exc, ill


if __name__ == '__main__':
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 2000, int(sys.argv[3]) if len(sys.argv) > 3 else 1)
```


## 2. Build log (rival, minute by minute)

# Rival 2 build log (timestamps relative to T0 = 2026-10-31 11:56:12 UTC, see T0.txt)

## 00:00-03:40  first draft in one pass (rival_bot.py ~900 lines)
- Evaluator: 7-card bitmask evaluator (m1..m4 cumulative rank masks + 4 suit masks, 8192-entry
  POP/TOP-k/straight tables). 0.3 us per evaluate-from-state on CPython 3.12.
- Import-time Monte Carlo over 1,500 shared random boards: for each board one accepted combo per
  class (rejection makes (board, combo) uniform), a random tie-broken sort gives every pairwise
  "beats" relation at once; bit-sliced 12-plane counters accumulate W[i][j] and V[i][j] without a
  169x169 inner loop. Three 4-villain samples per board give equity vs 1/2/4 random hands.
  Card-removal weights WREM[i][j] are exact. Result: 169x169 all-in matrix + E1/E2/E4 in 1.0 s.
  Spot checks: AA 0.849 (true 0.852), AKs 0.666 (0.670), 22 0.498 (0.503), AA v KK 0.816 (0.82),
  AK v QQ 0.428 (0.43), AKs v 22 0.507 (0.50), JTs v AKo 0.397 (0.40).
- Push/fold: iterated best response on the matrix, pusher vs k symmetric callers, fold prob F and
  equity-when-called Ec stored per class so act() re-prices with ICM and real dead money.
- ICM: exact Malmuth-Harville subset DP (skips subsets containing us): 39 us for 8 players,
  so it runs exactly once per hand (three knots: 0.5x, 1x, 2x our stack) and act() interpolates.
- Preflop ranges = equity percentiles (P1/P2/P4 by players behind); open fraction
  0.52*0.80^(k-1) scaled by the blinds' fold-to-aggression; blinds defend by pot odds; light 3-bets
  from the blinds vs late opens; re-shove 7-21 bb priced as F*steal + (1-F)*(Ec*win + (1-Ec)*lose)
  through the ICM curve. Postflop: time-boxed Monte Carlo equity (opponent hands sampled from the
  top-v of P1 with v from VPIP, tightened when they bet) + ICM pot odds + a 0.4/0.55/0.75/1.0 ladder.
- Opponent model: per seat VPIP ~ Beta(1.5,4.5), fold-to-aggression ~ Beta(1.5,1.5), updated
  from obs.history incrementally; blind posts filtered.
## 03:40-05:00  first bug: plain best response oscillates (HU 10bb "push 99%")
- Replaced by fictitious play (time-averaged best responses, warm start across depths, dot
  products via sum(map(mul))). Now HU 10bb push 52% / call 33%, BTN 15bb 26%, UTG 8-handed 10bb 7%.
  Grid 5 k-values x 10 depths; import 1.17 s.
## 05:00-05:30  harness: 2,000 obs, 0 exceptions, 0 illegal, mean 194 us, p99 481, max 5.5 ms
- act() swallows exceptions, so added Bot.DEBUG to re-raise and debug_harness.py: 0 internal
  exceptions. The 5.5 ms max does not replay (slowest calls re-time at 210-280 us = MC budget);
  cut the MC budget to 260 us.
## 05:30-07:30  engine.py (side pots, blind schedule, cap ICM, bust capture) + arch.py archetypes
- Mixed field (random, station, folder, maniac, tight, semi-sane, min-raiser): 7.22 pts, 53% 1st.
## 07:30-11:00  background fields + bust replay (busts.py) found five real leaks
- Pre-fix: min-raise 8.40, 1 push + 6 tight 5.87, self 4.43, semi-sane 5.15, 7 tight 3.40 (25% 8th).
- Leaks: (1) own raise not counted in n_raises -> after opening and being 3-bet we "defended by
  pot odds" with Q4s; (2) 4-bet/5-bet wars decided by the vs-random ranking -> TT/99/QQ stacked
  off 80-160 bb; (3) re-shove fold equity ignored the opener's observed fold-to-aggression -> 42s
  re-shoved 18 bb into a nit; (4) one pair stacked off deep after a raise; (5) thin value bets with
  MC noise. Fixes: own raises tracked; a value ranking PV (equity vs top 20%) for 3-bet/4-bet
  decisions and equity-vs-top-3% with ICM pot odds for 4-bet+ pots; F scaled by FTA and capped at
  0.85, junk never re-shoves; deep one-pair guard (e >= 0.84 to raise, +0.12 to call when the
  spot is half our stack at 30bb+); bet thresholds 0.58/0.60/0.62 by street.
## MINUTE 15 state (log written at ~11:40; snapshot snap_m15_rival_bot.py taken at 14:43, md5 7e7844d5...): harness 0/0 (mean 163 us, p99 341, max 481), all fields run end to end,
   five leaks fixed, post-fix runs in flight. Open: tight field result, timing headroom.
## 15:00-18:30  scenarios.py (45 hand-written spots) found four more things
- BB defended 72o: blind defence used equity vs a random hand; now equity vs the opener's range
  (equity_vs_set over the top-agg_cut of P1), discounted per extra caller.
- JJ 4-bet 100 bb deep: 4-bet threshold PV <= 0.015 (QQ+) beyond 45 bb, 0.035 (JJ+, AKs) inside.
- Speculative 3-bet calls now in position only (postflop order vs the aggressor).
- The ICM curve had knots at 0.5x/1x/2x only, so a 70-into-110 call at 8 equal stacks needed 0.39
  equity instead of 0.28: the kink at 1x was an interpolation artefact. Added local knots at 0.9x
  and 1.1x (five exact MH evaluations per hand, ~200 us at 8 players, still once per hand).
- Caller-side ICM: our pushes were priced by ICM but callers by chip EV, a double penalty. Callers'
  calling fraction is now shrunk by ((1-e_icm)/(1-e_chip))^2 (icm_fold_boost). A9o re-shoves 12 bb
  vs a BTN open; K8o on the BTN at 8 bb with four equal stacks computes to breakeven under ICM (flat
  10/7/5/4 payouts for the last four make the tax large); not checked against an external solver.
## 18:30-21:00  nut-flush-draw fold traced to sampling, not strategy
- Trace showed equities in multiples of 1/8: the first act() of a hand built the ICM curve and
  left the time box 8 samples. Added MC_MIN (48 samples, scaled by opponents) and a hard deadline
  at 520 us from act() start; fit-filter retries capped at 5. The fold became a call (e 0.42).
- A scenario artefact noted as a real weakness: history parsed all at once at street 1 tags the
  preflop raise as a flop raise; in play the parse is incremental so only calls are mis-tagged.
## 21:00-23:00  second tight-field bust trace
- Busts are now mostly standard push/fold variance. Fixed: a raiser closing the action (k_agg=0)
  was modelled wider than a button opener; a raise over our limp/call is read at 0.55x the range;
  fit filter thresholds by opponent type: tight players bet top pair+ and raise two pair+, loose
  players pair+ / top pair+.
- Fields on the 20:30 version (60 tables): 7 tight 5.55, mixed 7.74, 7 semi-sane 6.14,
  1 push + 6 tight 8.82, 7 min-raise 6.52, self-play 3.95 +- 0.28 (engine symmetric).
## 23:00-24:00  clean timing (nothing else running)
- 3.12: 10,000 obs, 0/0, mean 163 us, p99 298, max 636. 3.10: mean 180, p99 314, max 1,987 us,
  but a control bot with a fixed 200 us busy loop hit 3.9 ms in the same conditions and every
  slow rival call replays at 10-280 us: scheduler noise. The bot's own worst path is the hard-
  capped MC (~280 us) or the first-act ICM build (~200 us at 8 players).
## MINUTE 24 snapshot (written at 24:29, before the 30-minute mark): snap_m30_rival_bot.py (md5 below).
   100-table fields and HU matches in flight on this exact code. Open: nothing structural.
7e7adfb3c29835b603b07479ca548eea  rival_bot.py
## 24:30-26:00  100-table fields on the minute-30 code, plus heads-up matches
- 7 tight 4.70 +- 0.32, mixed 7.30 +- 0.28, 7 semi-sane 5.84 +- 0.30, self-play 3.91 +- 0.29.
  HU from 2000 chips, 100 matches each: 97% vs station, 82% vs tight, 80% vs maniac, 80% vs random,
  75% vs semi-sane, 64% vs push-bot.
- The tight number is 1.5-2 SE under the two previous versions. Suspect: the last fit-filter
  tightening (nits "bet top pair+") over-respects a rule-bot's flop bets, which it makes with any
  pair. Made the thresholds a knob (FIT_TYPED) and launched a paired A/B, 150 tables per arm on the
  same seeds, tight and semi-sane fields. Decision rule: keep whichever wins the tight field unless
  it loses semi-sane by more than noise.
## 26:00-28:00  two paired A/Bs, then freeze
- FIT_TYPED (typed fit thresholds) vs plain pair+, 150 tables per arm, same seeds: typed lost
  0.16 (tight) and 0.13 (semi-sane). Plain pair+ kept.
- OPEN_BASE 0.52 vs 0.64 (wider steals), 200 tables per arm: 5.36 vs 5.28 tight, 6.00 vs 5.92
  semi-sane. Baseline kept; the open fraction is a local optimum here as it was for rival 1.
- CODE FROZEN at 28:00, md5 1ad3b05acb26fff86130ea755dbb0148. Every remaining candidate change
  moves less than the 0.25-point noise of a 200-table A/B, so the team stopped changing the bot and
  spent the rest of the window on verification of the frozen file.
## MINUTE 30 state: frozen file (md5 1ad3b05a...), verified. Final runs on the frozen file, 100 tables each
   (12 processes on 8 cores): mixed 7.11, 7 tight 5.29 (opponents 3.82), 7 semi-sane 6.22 (3.69),
   7 min-raise 9.01, 1 push + 6 tight 5.62, self-play 4.07. HU: 98% station, 81% tight, 76% random,
   75% semi-sane, 71% maniac, 64% push-bot. Engine counted 22-109 decisions over 1 ms per run under
   that load (not folded); the 5-us archetype bots in the same runs peaked at 15.6 ms.
## 30:00-31:00  the team stopped. Last two A/Bs inside noise; each further change risked a regression
   it could not measure in the time left.
## MINUTE 45 state: unchanged from the freeze. No code changes after 28:00.
## MINUTE 60 state: unchanged from the freeze (md5 1ad3b05acb26fff86130ea755dbb0148).


## 3. The design the rival chose, and why it differs from a heuristic team

Rival 1 was a hand-reading team: a typed preflop table, a fitted push formula, made-hand buckets
with outs, four opponent flags, three ICM heuristics. Rival 2 took the opposite bet: spend the
unmetered import on computing the objects a heuristic team types or fits, then make every decision a
lookup or a one-line expected-value formula over those objects.

- **Evaluator without big tables.** Four cumulative rank masks (ranks seen >=1,2,3,4 times) plus four
  suit masks, updated with three ORs per card; the only tables are 8,192-entry popcount, top-k-bits
  and straight tables. 0.3 us per evaluation from a precomputed board state on CPython 3.12. Rival 1
  built a 73,775-entry prime-product dictionary; rival 2 wanted an evaluator cheap enough to call
  from inside a per-decision Monte Carlo and inside the import-time matrix build.
- **The 169x169 all-in matrix and the vs-1/2/4 equity table are computed, not typed.** One pass over
  1,500 shared random boards: for every board, one combo per class (accepted with probability
  N_available/N_max so that (board, combo) is uniform), one random-tie-broken sort of the 169 values
  gives every pairwise "beats" relation at once, and 12-plane bit-sliced counters accumulate wins and
  valid (card-disjoint) pairs with 169-bit integer ops instead of a 169x169 inner loop. Three
  4-villain samples per board give equity vs 1, 2 and 4 random hands with card removal. All of it is
  unbiased by construction (rejection + conditioning) and lands within 0.3-0.6 points of the
  published numbers (AA 0.849 vs 0.852, AKs 0.666 vs 0.670, 22 0.498 vs 0.503, AK v QQ 0.428 vs
  0.43). 1.0 s.
- **Push/fold is solved, not remembered.** Fictitious play (time-averaged best responses) on the
  matrix for a pusher vs k symmetric callers (k = 1,2,3,5,7) at ten depths, with exact
  card-removal weights. Plain best response oscillated (the rival's first bug: "HU 10bb push 99%");
  damping fixed it in four minutes. The solve stores, per class, the fold probability F of one
  caller and the equity-when-called Ec, so act() re-prices the push with the real dead money and the
  ICM curve instead of reading a yes/no chart. Output: HU 10bb push 52% / call 33%, BTN 15bb 26%,
  UTG 8-handed 10bb 7%.
- **ICM exact, once per hand, interpolated.** Malmuth-Harville by a subset DP that skips every
  subset containing us (2^(n-1) states): 39 us for eight players. Five evaluations per hand (our
  stack at 0.5x, 0.9x, 1x, 1.1x, 2x, plus the exact endpoints 0 and T) give a piecewise-linear
  utility curve; every call, push and re-shove decision compares utilities on that curve, so pot
  odds, bubble pressure and ladder effects come out of one object. Two mistakes were found and
  fixed here: the first curve had knots only at 0.5x/1x/2x and its kink at 1x made a 70-into-110
  call need 0.39 equity instead of 0.28; and pricing our pushes by ICM while modelling callers by
  chip EV double-counted the tax, so callers' ranges are shrunk by the same ratio (icm_fold_boost).
- **Ranges are equity percentiles.** Opens: top f(k) of the vs-1 / vs-2 / vs-4 ranking by players
  behind (f = 0.52 * 0.80^(k-1), scaled by the blinds' fold-to-aggression). Blind defence: equity vs
  the opener's range (a slice of the ranking, width from position and VPIP) against pot odds with a
  realisation discount. 3-bets, 4-bets and 5-bets use a second ranking (equity vs the top 20%), and
  4-bet pots are priced as all-in equity vs the top 3% through the ICM curve. Re-shoves at 4-21 bb
  are priced as F * U(steal) + (1-F) * (Ec * U(win) + (1-Ec) * U(lose)) against the opener's
  best-response calling set precomputed at import.
- **Postflop is a time-boxed Monte Carlo, not a bucket table.** 48-160 samples (260 us soft budget,
  520 us hard cap from act() start): random runout, our hand and each opponent's hand drawn from
  the top-v slice of the ranking (v from VPIP and position), with a fit filter that makes an
  aggressor's sampled hand connect with the board at a rate set by how tight they are (nits bet top
  pair+ and raise two pair+, loose players pair+). Decisions compare the sampled equity with the
  ICM-required equity plus a margin, bet on a 0.4/0.55/0.75/1.0-pot ladder, and refuse deep
  one-pair stack-offs below 0.84.
- **Two numbers per seat.** VPIP ~ Beta(1.5, 4.5) and fold-to-aggression ~ Beta(1.5, 1.5), updated
  incrementally from obs.history (blind posts filtered). VPIP shapes every sampled range and the
  3-bet/re-shove maths; FTA shapes steal width, bluff frequency and the re-shove fold probability.
- **Safety.** act() is try/except with a legalizer that clamps raises and never folds a free check;
  a DEBUG switch re-raises internal exceptions for testing (the operator harness cannot see them
  otherwise); import warms every path and gc.freeze()s.
- **Why its own engine again.** The rival wrote a 230-line SNG engine (side pots, blind schedule,
  cap ICM, bust capture) at minute 6 and ran bust traces three times. Every strategic bug it found
  came from there, none from the harness: own raise not counted (Q4s "defended by pot odds" against
  a 3-bet of our own open), 4-bet wars decided by the vs-random ranking (TT/99/QQ stacked off
  80-160 bb), re-shove fold equity blind to the opener's observed folding (42s re-shoved into a nit),
  deep one-pair stack-offs, and paying off nits because sampled ranges were not conditioned on the
  board. The scenario file then caught the ICM kink and the 8-sample nut-flush-draw fold.


## 4. Harness results

Final verification of the frozen file (md5 1ad3b05acb26fff86130ea755dbb0148), run with nothing else
on the machine, from `final_check.sh`:

```
== md5 / size
1ad3b05acb26fff86130ea755dbb0148  rival_bot.py
1476 rival_bot.py
non-blank non-comment: 1320
== CPython 3.12, 10,000 random legal obs
module=rival_bot n=10000 import=1.10s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=161.6 median=213.7 p99=291.3 max=1024.5
== control bot 3.12
act() us: mean=200.6 median=200.2 p99=207.6 max=361.1
== system CPython 3.10, 10,000 obs
module=rival_bot n=10000 import=1.33s exceptions=0 illegal=0 fold_when_check_legal=0
act() us: mean=178.1 median=267.5 p99=299.8 max=514.1
== control bot 3.10
act() us: mean=201.1 median=200.3 p99=207.3 max=3406.1
== debug harness (internal exceptions surface), 3.12, 4,000 obs
internal exceptions: 0
us mean=162.2 median=218.6 p99=289.6 max=452.1
== hostile fuzz
fuzz n=3000 exceptions=0 illegal=0
== RSS after import (MB)
17.9
```

The single 1,025 us maximum in the 3.12 run is the only observation above 1 ms in 24,000 harness
decisions of the frozen file; the slowest calls of every run replay at 10-450 us, a fixed-200-us
control bot showed maxima of 361 us to 3.9 ms across runs in the same conditions, and the bot's
own worst path is bounded by the 520 us hard cap on the sampler. It is scheduler noise on this WSL2
host, but the rival lists the 1 ms budget on an unknown machine as a weakness regardless.

Hand-written scenarios (45 spots, `scenarios.py`; labels are the rival's chip-EV expectations): 38
match. Seven differ. Two are at 100 bb: 76s folds on the button (opens are about 44% of hands and the
vs-random ranking puts small suited connectors near the edge), and 99 at 15 bb under the gun
min-raises instead of shoving (push/fold starts at 13 bb from early position). Five are four-handed
short-stack spots where the bot folds and the label expected a Nash shove or call: 75s and K8o on
the button at 8 bb, Q3o in the small blind at 6 bb, KTs re-shoving 12 bb from the big blind, and AQo
calling a 15 bb under-the-gun shove. All five come from the ICM curve. With four left and 10/7/5/4
for the last four places, busting costs 2.5 points and doubling up gains about 1.55, so a call needs
about 0.62 equity. Whether that is right or too tight depends on the future-game term the static
Malmuth-Harville model leaves out (weakness 5). Full output: `final_check.txt` in the scratch
directory.

**Operator note on the time budget.** The operator harness starts a new hand on almost every
observation, so its numbers include the per-hand ICM build on every preflop call; the p99 of 291 us
is the honest worst path and leaves about 3x headroom. In the engine, though, the bot crossed 1 ms
about once per 2,000 decisions even in a single-process run (9 per 150 tables, rival 1: 1), and
about once per 1,000 with four processes on eight cores. The engine counts these and does not fold
them; the tournament would. The cause is exposure, not a slow path: a bot that spends 160-280 us per
decision is preempted mid-call far more often than one that spends 15 us. The expected cost is
small (a fold on ~0.1% of decisions, usually preflop junk) but it is a real, measured difference
from rival 1, and it grows on a slower or busier host.


## 5. The rival's own guess at its weaknesses

1. The 169x169 matrix and the vs-N table carry Monte Carlo noise of 1-3 points per cell (1,500
   boards). Push/fold ranges inherit it: the solve is a few percent tight of Nash at most depths and
   the multiway solve treats k callers as symmetric with averaged dead money and ignores multiple
   callers.
2. Postflop equity is 48-160 samples per decision: a standard error of 4-8 points on every call,
   bet and fold. Margins absorb some of it, but close decisions are coin-flipped by the sampler and
   an adaptive opponent could exploit the resulting inconsistency.
3. Opponent ranges are a slice of one ranking (top-v by equity vs random) plus a "connected with the
   board" filter. There is no notion of a polarised range, of blockers, or of a check-raise meaning
   something different from a bet; a bot that bets air and checks strength will be misread.
4. Two numbers per seat (VPIP, fold-to-aggression) learn slowly from Beta priors: a nit is read as a
   25% player for its first ten hands, and a maniac's raises are discounted as if from a sane
   player until its VPIP climbs. Aggression frequency is not tracked at all.
5. ICM is exact but static: no future-game term, so with equal short stacks it folds hands an
   HRC-style solver with future blind pressure would push, and the cap (hand 200) is not modelled
   beyond the fact that stacks are valued by ICM at all times.
6. History parsing attributes each action to the street at which we next see it. Actions by players
   behind us between our last act and the next street are mis-tagged (harmless for calls, wrong for
   a raise), and a kit that includes blind posts in a different shape could pollute VPIP.
7. Bet sizes are a fixed ladder from equity, c-bet and bluff frequencies are constants scaled by
   fold-to-aggression, and the light 3-bet slice is fixed: all of it is readable within a table.
8. Everything was validated against our own archetypes and our own 230-line engine. The 1 ms budget
   is respected by a time box with a 520 us hard cap, but the cap is measured on this machine; a
   tournament host two to three times slower would still fit, a GC pause or scheduler stall would not,
   and a timeout is a fold.


## 6. Operator judgment

**What the computation-first team bought.** It shipped the two things the drill-1 operator said a
top team would add to rival 1: a real range model (a card-removal-correct 169x169 all-in matrix and
range-vs-range equity on every all-in, 3-bet and re-shove decision) and exact Malmuth-Harville ICM
behind every call, push and re-shove, through a utility curve built once per hand. It also shipped
a solved push/fold table rather than a fitted formula, in 1.1 s of import. In the scenario checks
its blind defence and 3-bet-pot decisions match expectations. Its short-stack decisions are driven
by ICM and are tighter than chip-EV Nash in four-handed spots (it folds AQo to a 15 bb shove), which
is right only if a static ICM model is. All of these decisions come out of one object, the ICM
curve, rather than a stack of special cases. Heads-up, where ICM is linear and the preflop solve
matters most, it beats rival 1 56% of the time.

**What it did not buy.** Postflop is a 48-160-sample Monte Carlo over a range model that is one
equity ranking plus a "did the bettor hit the board" filter. Every postflop decision carries 4-8
points of sampling noise, and against tight rule-bots that bet only when they connect it pays off
more than a hand-reading bot does: its worst field is seven nits (4.7-5.3 points against their
3.6-3.9), where rival 1 scored 7.2 in its own engine. Two numbers per seat learn slowly and say
nothing about aggression. And its time budget is thinner: it is the first of the two bots whose
timeouts are measurable at all.

**Head-to-head, scored by the operator after the freeze.** At the same tables in rival 2's engine
(600 tables per field): rival 2 is better against median-team bots (6 semi-sane: 5.96 vs 5.55) and
heads-up (56% of 600 matches, about 3 standard errors), rival 1 is better against nits (6 tight:
5.14 vs 4.74), and they tie in a mixed field (6.22 vs 6.30). The engine and archetypes are rival 2's,
which favours rival 2 a little; the mixed-field tie is the fairest single number. The two bots are
the same strength by different routes, and their strengths are complementary: rival 2 wins the
preflop, all-in and heads-up game, rival 1 wins the postflop game against tight opponents.

**Against median and top teams.** A median team (200-400 lines, a hand-tier preflop, a c-bet rule,
fit-or-fold) is the `SemiSaneBot` this bot beats 6.0-6.2 to 3.4-3.7 points per table in seven-copy
fields and 75% of the time heads-up. A top team in this window ships the union of the two rivals:
rival 2's import-time matrix, solved push/fold and per-hand ICM curve, with rival 1's postflop hand
reading (or a postflop sampler conditioned on a real range model rather than a percentile slice),
a three-number opponent model that tracks aggression, and a decision path bounded well under
100 us. Rival 2 sits where rival 1 sits, clearly above median and below top, with the gap to top on
the other side: rival 1 computes too little before the flop, rival 2 computes too noisily after it.

**For our engine.** Keep both as anchors; they probe different leaks. Rival 2 is the sharper test
of our preflop, short-stack, ICM and heads-up play (it beats rival 1 there), and of whether our
postflop can push a sampler-driven bot off pots (its weakest area against aggression it cannot
read). Rival 1 remains the sharper test of our play against nits and of our postflop value
betting. A bot of ours that beats both in the mixed field is beating the realistic top of a
60-minute field; one that beats only rival 1 may still be losing all-in and heads-up spots to a
team that computed them.
