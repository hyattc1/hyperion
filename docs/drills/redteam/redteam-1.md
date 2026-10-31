# Red-team drill 1: the bot a strong rival team ships in 60 minutes

Operator/rival drill run 2026-10-31. Roles were strictly separated: the operator set up the scratch
directory, wrote the brief, stub kit and smoke harness, kept the clock and scored; the rival (a
prepared CMU/MIT-style team with a coding agent, no access to this repository) built `rival1_bot.py`
in the timed window. The only files written into this repository are this report and the bot.

Scratch directory (venv, brief, kit, harness, engine, experiments, logs):
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/redteam1/`

Clock: T0 = 2026-10-31 10:17:15 UTC. Code frozen at T0+36 min (md5 6275bb10c44cf8996dca5d532f8d9440); no changes after that.

## Key numbers

| Measure | Result |
|---|---|
| Harness, CPython 3.12, 10,000 random legal obs | 0 exceptions, 0 illegal, 0 fold-when-check-legal |
| act() latency, 3.12 | mean 15.1 us, median 14.8, p99 39.2, max 206 us |
| Harness, system CPython 3.10, 10,000 obs | 0 exceptions, 0 illegal; mean 22.2 us, p99 55.7, max 229 us |
| Import time / memory | 0.19-0.26 s / 18.7 MB RSS |
| Hostile-input fuzz, 3,000 obs | 0 exceptions, 0 illegal |
| Size | 949 lines (842 non-blank non-comment), one file, stdlib only |
| Rival's own engine, points/table (uniform = 4.00) | mixed field 7.50; 7 tight 7.24; 7 semi-sane 5.92; 7 min-raise 8.49; 1 push + 6 tight 5.14; self-play 4.00 |

## 1. The brief as given to the rival

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


### kit.py (stub provided)

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

### harness.py (operator smoke harness, 53 lines)

```python
"""Operator smoke harness: random LEGAL observations, no poker engine. Checks latency + legality.
Usage: python harness.py <module> [n=2000] [seed=1]"""
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

# Rival build log (timestamps from T0.txt)

## 00:00-05:30  first draft in one pass (rival_bot.py ~640 lines)
- Evaluator: rank-multiset prime-product dict for 5/6/7 cards (73,775 entries) + 8192-entry flush/straight
  tables; built in 0.2 s at import; ~1-3 us per evaluate().
- Preflop: 169-class heads-up-equity table typed from memory, two percentile rankings (pure equity for
  all-in spots, playability-adjusted for opens/calls). Nash-shaped push fraction f(bb, players behind).
- Postflop: made-hand equity estimate by category x board texture, outs-based draw equity, multiway
  exponent, discounts when facing raises; pot-odds calls, value bets 2/3 pot, shove when committed.
- Opponent model from obs.history: VPIP/PFR/fold-to-raise/aggression per seat -> folder / station /
  maniac / nit flags used for steals, thin value, slow-plays and shove-calling ranges.
- act() wrapped in try/except, every action passed through a legalizer (never folds when check is free).
- Harness: 2,000 obs, 0 exceptions, 0 illegal, mean 14.5 us, max 211 us.
## 05:30-09:00  debug switch + 30 hand-written scenarios
- Found: c-bet never fired (preflop history seen on the flop was tagged postflop), AKs folded to a
  3-bet at 100bb, TPTK checked on river, 3-high flush on 4-flush board overvalued, button treated as
  first to act postflop. All fixed. Timing outliers (0.7-9 ms max) shown to be WSL scheduler noise:
  not reproducible on replay, and a control bot with a fixed 20 us busy loop shows the same maxima.
  Added import-time warm-up of all paths + gc.freeze() anyway.
## 09:00-12:00  minimal SNG engine (mini_engine.py) + simple opponents (random, call, fold, maniac, tight)
- Results: 7.56 pts vs mixed field (58% firsts), 7.00 vs 3 tight + 4 random, 6.00 vs 7 tight bots
  (but 7% eighth places there), self-play symmetric at 4.00. Illegal actions: 0 in ~30k decisions.
## MINUTE 15 state: everything above works end to end. Open: bust causes vs tight field, folder exploit speed.
## 15:00-17:00  bust trace vs 7 tight bots (busts.py)
- 51/59 busts were preflop 4-bet shoves with TT/99/JJ over 3-bets from 12%-range raisers, and
  call-downs with underpairs / pocket pair under two board pairs. Fixed: 4-bet shove only QQ+ at <=45bb
  (JJ/TT/AK call when cheap), street-scaled discounts on weak made hands facing bets, "pocket under
  two board pairs plays the board", crumbs-shove only with real equity, nits count as folders for steals.
  vs 7 tight: 6.00 -> 6.82 (eighths 7% -> 3%). Mixed field 7.56 -> 7.68.
## 17:00-20:00  cap mode + hostile-input fuzz
- Cap mode: with <=20 hands to the cap and a stack that covers the blinds to hand 200, fold into the
  ICM payout (shove/call ranges x0.4, opens x0.7, no bluffs, +0.10 call margin). Also: 3-bet calls
  with JJ-99 only when they cost <=15% of stack. fuzz.py (None fields, list legal, extra stacks, swapped
  min/max raise): 0 exceptions, 0 illegal over 3,000 obs. Mixed 7.76, tight 6.81.
## 20:00-  per-street history tolerated (only hand_no starts a new hand); knobs for A/B tests launched
## 20:00-25:00  A/B knobs and replayed bust hands
- Self-play A/Bs (120 tables each, +-0.27): looser opens 3.57 vs 4.0 baseline; pushes x1.3 -> 3.28,
  x0.75 -> 3.29. Baseline parameters are a local optimum; left alone. Cap mode made no difference in
  the tight field (3+ players rarely alive at the cap there).
- Replayed real observations of three busts the rules should not have produced. Found: (1) pot-odds
  counted the part of an opponent's over-bet above our stack (3350 into 120 with 1675 behind read as
  price 0.33 instead of 0.48) -> bets capped at our stack; (2) 99 called a 4-bet four-way because the
  cheap-call rule ignored commitment and opponents in the pot -> commitment on remaining stack, x0.6 per
  extra opponent, non-premium 3-bet calls only when <=15% of stack; (3) 44 called off 65bb on the river
  vs a maniac -> stack-off guard (>=50% of stack needs >=0.50 equity unless short), smaller maniac bonus;
  (4) 88 called a 100bb open-shove from an unknown -> TT+ only vs deep unknown shoves.
- After: mixed 7.77 (places 5-8: 5 of 150), vs 7 tight 6.97, new vs 7 copies of the previous version
  4.22 +- 0.24 (old 3.97). Harness 0/0, fuzz 0/0, 923 lines.
## MINUTE 30 state: feature-complete; remaining time is verification and small exploit tuning.
## 25:00-36:00  archetype testing found one more real hole; then freeze
- Lowered opponent-profile sample to 8 hands (HU matches last 20-40 hands). HU: 89% vs tight,
  98% vs call-station, 100% vs fold-bot, 81% vs maniac, 71% vs random.
- Maniac handling: a flagged maniac's raise is treated as a near-random hand (shove-calling range
  floor 0.8), and its bets discount our made hands far less (x0.95) than a sane player's.
- All-in fallback now respects the stack-off guard; set-mining capped at 12% of stack total; the
  river bluff vs folders only when 0.6 pot <= 25% of our stack.
- New archetype: PushBot (shoves every hand). Exposed a tournament-losing leak: once flagged a
  maniac, pot odds alone had us calling 100bb with A9o/AJo/KQo at hand 9 (60/40s for our life at
  8 players). Added a risk-of-ruin cap on deep stack-offs: top 5% / 12% / 22% of the shover's
  estimated range at >50bb / >25bb / >15bb, none when short or heads-up (knob ROR_DEEP; A/B 0.03 ->
  5.18, 0.07 -> 5.10, 0.12 -> 4.62 in the push field, +-0.35; set 0.05). Also: with a maniac still to
  act, open only hands that can stand a shove.
- New archetypes MinRaiseBot and SemiSaneBot (a median-team stand-in: 25% opens, always c-bets,
  fit-or-fold): rival 8.49 vs 7 min-raisers, 5.92 +- 0.37 vs 7 semi-sane (they average 3.73).
  Semi-sane bust trace: push/fold variance and coolers, nothing systematic. CODE FROZEN at ~36:00,
  md5 6275bb10c44cf8996dca5d532f8d9440.
## MINUTE 45 state: unchanged from the freeze. No code changes after 36:00.
## MINUTE 60 state: unchanged. The team stopped early because the last three A/Bs were inside noise
   and each further change risked a regression it could not measure in the time left.

## Final verification of the frozen file
- Operator harness, CPython 3.12 (venv), 10,000 random legal obs: exceptions 0, illegal 0,
  fold-when-check-legal 0; act() mean 15.1 us, median 14.8, p99 39.2, max 206.3 us.
- Operator harness, system CPython 3.10, 10,000 obs: exceptions 0, illegal 0; mean 22.2 us,
  median 21.8, p99 55.7, max 228.6 us; import 0.19 s.
- Hostile-input fuzz (3,000 obs with None/list/oversized/inconsistent fields): 0 exceptions, 0 illegal.
- 30 hand-written scenarios: 28 as expected; the 2 misses are borderline by design (7bb BTN 86s folds;
  a 3-high one-card flush on a four-flush board calls a 2/3-pot river bet).
- Size: 949 lines (842 non-blank non-comment), 24 functions/methods; RSS 18.7 MB after import.
- Own engine, points per table (uniform seating = 4.00): mixed field 7.50 (n=200), 7 tight 7.24
  (n=150), 3 tight + 4 random 7.34, 7 semi-sane 5.92, 7 min-raise 8.49, 1 push + 6 tight 5.14,
  self-play 4.00 (symmetric), new vs 7 copies of the minute-20 version 4.41 +- 0.23.

## The rival's own guess at its weaknesses
1. Preflop equities were typed from memory; a point or two of error in places is likely. Multiway
   strength is a playability bonus on heads-up equity, not a real N-opponent table.
2. Postflop has no equity calculation: made-hand buckets plus outs. It is blind to combo draws it
   does not enumerate, to board straights (except on the river), and to blockers. It overvalues
   top pair on dynamic boards and never bluff-catches a sane opponent on the river.
3. Shove-calling is a formula over "fraction of hands", not range-vs-range equity; against a real
   Nash pusher it will be off in both directions in places. Multiway all-in logic is crude.
4. ICM is three heuristics (shorter stacks present, cap near, risk-of-ruin cap), not Malmuth-Harville
   per decision. Cap mode never showed an effect in A/B; it is on because the argument is sound.
5. The opponent model needs 8+ hands and restarts every table; it is four coarse flags. A bot that
   mixes strategies will be mislabelled, and we have no defence against being modelled ourselves:
   fixed open sizes, 2/3-pot bets, a predictable fold-to-3-bet range (QQ+ continue deep).
6. Our randomness is a fixed seed per table; an adaptive opponent could learn our semi-bluff and
   slow-play frequencies within 200 hands.
7. Everything was tested on our own 150-line engine against archetypes we wrote. We never faced a
   solver-grade bot, and the real kit may differ on history format, all-in-for-less raise rules, or
   whether blind posts appear in history. The code tolerates these but was not validated against them.
8. Timing is safe here (p99 < 60 us) but the 1 ms budget is a property of the tournament machine;
   we cannot rule out GC or scheduler outliers there, and a timeout costs a fold.


## 3. The design the rival chose, and why

- **Evaluator at import, nothing at decision time.** A rank-multiset table keyed by prime products
  (73,775 entries for 5/6/7 cards) plus 8,192-entry flush/straight bitmask tables. Built in 0.2 s,
  evaluates a 7-card hand in 1-3 us. The rival judged a correct, fast evaluator the one thing it could
  not do without, and the one thing cheap to get right.
- **169-class preflop table from memory, two percentile rankings.** Heads-up equity vs a random hand
  for every class (typed, not simulated: deterministic and instant), converted to a combo-weighted
  percentile. One ranking is pure equity (used for all-in spots), one adds a playability bonus for
  suited, connected and small-pair hands (used for opens and calls). No Monte Carlo anywhere.
- **Push/fold by formula, not chart.** `f(bb, players_behind) = 1.15 e^(-0.065 bb) 0.77^(behind-1)`,
  calibrated to the Nash numbers the team remembered (SB 8bb ~65%, BTN 15bb ~30%, UTG 8-handed 8bb
  ~13%). Shove-calling estimates the shover's range from stack depth and position, tightens per
  player behind, per caller, per extra opponent in the pot, and caps the slice of that range we will
  stack off with when deep (risk of ruin).
- **Postflop by hand reading, not equity.** Made-hand equity estimate from category x board texture
  (overpair, top pair by kicker, set vs trips vs board trips, one-card flushes, playing the board),
  outs-based draw equity with rule-of-4/2, a multiway exponent, and street-scaled respect for
  aggression on weak hands. Value bets 2/3 pot, shoves when committed, folds when the price is wrong.
- **Tournament awareness as three heuristics.** Tighten when much shorter stacks exist (ladder), when
  the cap is near and we are above average, and refuse deep 60/40s for our life at a full table. Near
  the cap, a stack that can pay the blinds to hand 200 folds into the ICM payout.
- **A cheap opponent model that pays for itself.** Per-seat VPIP / PFR / fold-to-raise / aggression
  from `obs.history`, four flags (folder, station, maniac, nit), used to steal wider, value-bet
  thinner, slow-play, and read a maniac's shove as a random hand.
- **Safety first.** `act()` is try/except-wrapped; every action passes a legalizer that clamps raise
  amounts and never folds when a check is free; import warms every code path and `gc.freeze()`s.
- **Why a self-built engine.** The operator harness proves legality and latency, not poker. The rival
  wrote a 150-line engine with side pots and archetype opponents at minute 9 and used replayed bust
  hands to find the bugs that mattered: a pot-odds formula that counted an opponent's over-bet above
  our stack, a 4-bet call rule that ignored commitment, and pot-odds shove-calling that risked the
  tournament on 60/40s against an every-hand shover. None of these would have shown in the harness.

## 4. Harness results

See the key numbers table. Timing maxima in the millisecond range appeared in a few early runs on
this WSL2 machine; the rival showed they were not reproducible on replay and that a control bot
doing a fixed 20 us busy loop produced the same maxima, i.e. scheduler noise, not the bot. The final
10,000-observation runs on both interpreters (one background job running) had max 206 and 229 us.

## 5. The rival's own guess at its weaknesses

(Verbatim from the build log above, section "The rival's own guess at its weaknesses".)

## 6. Operator judgment

A median team in this window ships 200-400 lines: a Chen-formula or hand-tier preflop, a c-bet
rule, maybe a push/fold chart, a slow or incomplete evaluator, and usually one legality or timeout
bug they never saw because they had no harness. That is roughly the rival's own `SemiSaneBot` and
`TightBot`, which this bot beats 5.9 vs 3.7 and 7.2 vs 3.5 points per table, with 45-50% firsts.
A top team ships the same architecture as this rival but with the two things it skipped: a real
range model (precomputed N-opponent equities or a 169x169 matchup table, and range-vs-range calls on
shoves) and real ICM (Malmuth-Harville per all-in decision, cheap for eight players), plus a
tested Nash chart instead of a fitted formula. The rival sits clearly above median and below top:
its decisive edge over a median team is not any single rule but the engine-plus-bust-replay loop
that found three tournament-losing bugs, and its decisive gap to a top team is that every postflop
and all-in decision is a heuristic about ranges rather than a computation over them. For our
opponent pool it is a strong-median anchor: it will punish random, passive and maniac bots hard,
hold its own against tight rule-based bots, and lose range wars and late-stage ICM spots to a bot
that actually computes them.
