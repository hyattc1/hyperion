# NOTEBOOK — rival_bot build (o6)

T0 = 1793700162 (see T0.txt). Time box ~2h.

## Inputs
- BRIEF.md: 8-max SNG, 2000 chips, blinds up every 25 hands, 200-hand cap, points 10/7/5/4/3/2/1/0,
  ICM at cap, 1 ms per decision, stdlib only.
- Note: BRIEF.md describes the team as "two quant interns + pokerbots finalist" wanting a hard-to-exploit
  general bot; the task message describes "two aggressive online pros + programmer" wanting a pressure
  style. Rules/format are taken from BRIEF.md; style direction from the task message, but I test the
  "bots fold too much" premise instead of assuming it, and keep the bot from bleeding against stations.

## Plan
1. pe.py: fast 7-card evaluator (bitmask), checked against brute force.
2. precompute.py: preflop tables (169 classes): equity vs n random, 169x169 matrix -> eq vs top-X%.
3. engine.py + opps.py: 8-max SNG simulator with blinds, side pots, ICM-at-cap scoring; opponent pool.
4. rival_bot.py; experiments; freeze.

## Log
- [t+11m] pe.py evaluator: 0 mismatches vs brute force on 3000 random 7-card hands; 2.5 us/eval.
- [t+13m] precompute.py 1200 500 (eq vs n random, 1200 trials; 169x169 matrix, 500 trials/matchup): 109 s.
  gen_tables.py: ranking from matrix-averaged eq vs random (less noisy than direct MC); EQX = eq vs top-X% (40 steps).
- Fast ICM: Harville = pairwise order term (P(i above j) = s_i/(s_i+s_j)) + 3*P(1st) + 1*P(2nd), since
  points 10/7/5/4/3/2/1/0 = (8-place) + bonus(3,1). Max diff vs exact subset DP 6e-15 over 200 random cases.
  ICM facts: 8x2000 -> 4.0 pts each; double up to 4000 -> 5.96; so a full-stack flip needs ~67% equity. Strong ICM.
- [t+20m] harness rival_bot v1: exceptions=0 illegal=0 fold_when_check_legal=0; wall mean 69 us, median 22, p99 576, max 10.9 ms.
  The max is machine noise: load avg 13-17 on 8 cores (WSL); a trivial 300-iteration loop shows max 4.3 ms on the same box.
  Intrinsic cost (min of 5 repeats per obs, slow2.py): median 16 us, p99 35 us, max 50 us.
- [t+16m] run.py first fields, 400 tables each (v1, before ICM-outcome bug fix):
  mix (station,nit,icmnit,tag,maniac,pushfold,random): rival 5.705, tag 5.768 (se ~0.18)
  tight (nit,icmnit,tag x2,nit,icmnit,pushfold): rival 4.029 (avg seat = 4.0) — not exploiting tight bots
  loose (station x2,maniac x2,random x2,tag): rival 6.919, tag 6.948
  mix2 with variants:Tight in field: Tight 6.171 vs rival 5.456  -> the tight knob set beats the pressure set.
- Fixed bugs: shove-EV outcome stacks double counted our own posted chips; postflop ICM-call win stack too big by the call.
- [t+18m] ab.py 300 5 (300 tables per field, paired seeds; fields mix/tight/loose/strong/self; se ~0.2/field, ~0.09 avg):
  Bot(pressure) avg 4.946 | Tight 5.656 | Prior40 5.174 | No3b 5.509 | LowCbet 5.017 | TightOpen 5.083 | Margin(0.05) 5.152 | NoAdapt 4.953
  -> Light 3-bet/4-bet is the biggest leak (+0.56 by removing); fold-prior 0.55 too optimistic (+0.23 at 0.40);
     requiring an ICM margin on all-ins helps (+0.21). Opponent adaptation is worth ~0 at this sample.
- [t+20m] leak finder (instr.py rival_bot:Bot mix/strong 300 5; chips in bb attributed to each line taken in a hand):
  biggest losers: pre_3b_shove_light (-25 bb/hand mix, -12.5 strong), turn/river air bets (-12 / -18..-28 bb/hand),
  river calls with weak hands (-9 / -15). Root cause of the 3-bet shove leak: shove-EV treated the opener's call
  probability as a fraction of ALL hands times his range -> opener "folded" ~85% to 3-bet shoves.
  Fix: caller j with range W_j calls with prob min(1, w/W_j), calling range top min(w, W_j).
  Added: street fold priors FOLD_ST=(.47,.40,.36), BARREL_M, ST_DISC, B3_BAND/B3_EFF knobs.
- [t+22m] ab.py 300 5 (v2 = range-aware shove EV):
  Bot 5.544 (v1 4.946) | Tight 5.718 | No3b 5.732 | Margin 5.669 | Barrel 5.525 | P2 (prior .45, margin .03, barrel/disc, 3b only >=30bb band .30) 5.746
  fields for Bot: mix 6.449 tight 5.384 loose 7.059 strong 4.374 self 4.452
- [t+24m] leak finder on v2 (instr.py rival_bot:Bot strong|tight 300 5): preflop now healthy
  (open shoves light +0.6..0.7 bb/hand, 3b-shove light ~0, 3b-shove value +4..13). Remaining leaks are postflop:
  turn air bets -16 / -23 bb/hand, river air bets -25 / -37, turn/river calls with weak hands -10..-28,
  preflop flats -2.2 / -3.2 bb/hand. Tight bots that call the flop have it; fold stats pooled over streets hid that.
  v3 knobs: PER_STREET fold stats (flop/turn/river separately), priors (.47,.38,.34), bluff sizes (.66,.66,.8),
  FLAT_MULT, ST_DISC, BARREL_M.
- [t+27m] ab.py 300 5: Push10 5.522 | Push20 5.391 | P3 (P2 + 3b/4b .15 + margin .05) 5.755 | P4 (P3 + PUSH_BB 12) 5.944
- [t+31m] ab.py 300 5: V3 (P2 + per-street stats, low late priors, smaller bluffs, flats x0.7, late discounts) 6.045 |
  V3b (V3 + 3b/4b .15 + margin .05) 6.254 | V3c (V3 with flats x1.0) 6.013
  V3b by field: mix 7.051 tight 6.273 loose 7.570 strong 5.522 self 4.857
- [1720s] ab.py 300 5: V4 (V3b + PUSH_BB 12) 6.217 | V4m (V4, margin .08) 6.160 | P4m 5.785 -> keep PUSH_BB 15, MARGIN .05.
  V3b leak finder (strong 5.676 / tight 6.402 pts): remaining leaks = turn/river calls with weak no-draw hands
  (-11..-19 bb/hand), flats vs tight raisers (-3.2 bb/hand in tight field). Added AIR_AG and FLAT_PFR knobs (V5).
- [1820s] ab.py 300 5: V5 (V3b + AIR_AG .28 + FLAT_PFR) 6.232 | V5a (AIR_AG only) 6.066 -> no gain; not adopted.
- [1830s] robust.py (posts as none/'raise'/'post', hand_end None/partial, tuple obs, 8/6/2 seats; 180 tables): illegal 0, errors 0.
- Defaults set to V3b. Then preflop seats/limpers derived from button+bets instead of history (robust if posts appear as calls);
  raise level = max(history raises, distinct bet levels above bb).
- [2077s] ab.py 300 5, pressure sweep around V3b defaults (run before the seat-derivation change, which is behavior-neutral here):
  default 6.172 | OpenWide(x1.2) 6.180 | OpenTight(x0.8) 5.864 | CBET .95 6.074 | CBET .6 5.877 | 3b/4b light .25 6.153 |
  3b/4b off 6.232 | flop fold prior .52 6.144 | TeamPrior (literal brief: fold priors .55/.50/.45, 3b .35, 4b .30, no margin, cbet .9) 5.510 |
  Tight (same code, tight knobs) 5.841.
  Reading: wide opens and frequent flop c-bets pay; light 3/4-bets are neutral (+-0.1); assuming opponents fold
  (TeamPrior) costs 0.66 pts/table; going tight costs 0.33. Calibrated pressure beats both.
- [2100s] harness timing under load: 3 seeds -> exceptions 0, illegal 0; median 21 us, p99 100-470 us, max 8-27 ms.
  With gc disabled max still 0.7-1.7 ms -> spikes are OS preemption (load avg 13-16; ~7 other nice-5 python jobs
  at 55-66% CPU each), not the bot. Intrinsic cost (slow2.py, min of 5) median 16 us, max 50 us.
- [2163s] started final eval (seed 99), then stopped it: code review found strength() valued "board pair + our pair"
  (two pair category, paired board) with the two-pair bitmask read as a pair rank (garbage 0.42..0.80), and the trips
  kicker used the wrong card. Fixed (rival_old.py = pre-fix copy). A/B ab.py 300 5 rival_old:Bot vs rival_bot:Bot.
  ab.py fields now include 'pros' = [Bot, Bot, Tight, Tight, TeamPrior, tag, nit].
- [2318s] ab.py 300 5 (6 fields incl. pros): rival_old (pre-fix) 6.049 | fixed 6.095
  fixed by field: mix 7.394 tight 6.900 loose 7.166 strong 5.500 self 5.429 pros 4.182. Fix kept (correctness; +0.05 is noise).
- [2370s] run.py pros-heavy table (3x Bot, 2x Tight, TeamPrior, tag, nit), 500 tables seed 7:
  Bot 4.225 (se .087) > Tight 4.114 (.093) > TeamPrior 3.887 (.157) > nit 3.682 > tag 3.526. errors 0, illegal 0.
  timed decisions 372,577: wall max 57.6 ms, 1,401 (0.38%) over 1 ms on this loaded box.
  instr.py pros 400 7: remaining leak = calling bets with weak no-draw hands (flop -9, turn -15, river -27 bb/hand).
- [2486s] ab.py 300 5: Disc2 (ST_DISC .03/.07/.12) 6.010 | Disc2Air (+AIR_AG .30) 6.076 vs baseline 6.095 -> not adopted.
  The "call with weak hand" tags are confounded (a later fold books the whole loss); stopping knob tuning here.
- [2530s] slow3.py 40 (pros field, real game states): 61 decisions >300 us on the wall clock; replayed (min of 7)
  their intrinsic cost is at most 40 us. Spikes are the shared machine.
- [2537s] final eval launched on fresh seed 99 with build md5 88037a1d... (copy kept as rival_eval.py).
- Then hardened _consume against obs.blinds=None (behavior-neutral): 0 decision diffs on 5000 harness obs and
  30 engine tables bit-identical vs rival_eval.py with deterministic opponents.
  (Note: opps.Base seeds rng with id(self), so A/B pairing was on decks/seats only, not opponent rng.)
- [2878s] FINAL EVAL seed 99 (fresh, never tuned on). ab.py 1000 99 rival_bot:Bot / ab.py 500 99 Tight,TeamPrior:
  Bot       avg 5.898 | mix 7.362(.11) tight 6.588(.13) loose 7.415(.08) strong 5.102(.12) self 4.684(.10) pros 4.236(.10)
  Tight     avg 5.740 | mix 6.958(.15) tight 6.087(.17) loose 7.419(.11) strong 4.884(.16) self 4.876(.14) pros 4.213(.14)
  TeamPrior avg 5.459 | mix 6.629(.16) tight 5.994(.19) loose 6.831(.12) strong 4.857(.18) self 4.463(.16) pros 3.978(.16)
  (seat average is 4.0). Against tables of its own copies the tight version scores higher (4.88 vs 4.68).
- [2878-3122s] ab.py 600 123: Bot 5.966 vs Mid (bluff priors half-way to Tight) 5.912 -> not adopted.
- Added a GC guard in act() (disable cyclic GC during the decision, restore previous state; import-safe if gc missing).
  Decisions identical to the evaluated build (0 diffs / 5000 harness obs). Verified kit-less import fallback (python3 -I).
- FINAL CHECKS on frozen build:
  robust.py: illegal 0, engine errors 0, internal errors 0.
  run.py (2x Bot, Tight, tag, nit, station, pushfold, random) 300 tables seed 77: Bot 5.674 (se .136), Tight 5.474, tag 4.364,
    nit 4.338, pushfold 4.255, station 1.185, random 1.036; 122,249 timed decisions, 0 errors, 0 illegal; wall max 20 ms,
    462 over 1 ms (0.38%) at load avg ~19.
  harness.py rival_bot (2000 obs) seeds 1/2/3: exceptions 0, illegal 0, fold_when_check_legal 0; median 20-22 us;
    max 8094 / 790 / 404 us (wall clock, load avg 19). Intrinsic (slow2.py min of 5): median 16.7 us, p99 34 us, max 83 us.
  Size 75 KB, import 0.02-0.09 s.
- FROZEN md5 1d724a694a88ab2b05df763801dddb99 at 3262s.

## Summary
Approach: ICM-aware pressure bot. Exact O(n) Harville ICM (pairwise + 1st/2nd bonus) drives every all-in decision
(open shove, re-shove, call all-in) with a caller model (price-based calling width, tighter when covered,
adapted by each seat's VPIP and fold-to-our-raise stats, range-aware for openers). Wide opens by players-behind,
2.2-3 bb sizes, light 3/4-bets at 15% in a band when deep (>=30 bb), shove when a raise would commit >1/3 of the stack.
Postflop: evaluator-based strength + draw outs; c-bet 80% heads-up, big value sizes (overbet rivers with the nuts,
x1.2 vs stations), turn/river bluffs only when per-street fold stats support them; calls discounted by villain
aggression and street, with ICM-adjusted price for big calls.
What the tests said about the pressure direction: wide opens and frequent flop c-bets pay; assuming bots fold
(literal direction) cost ~0.4-0.66 pts/table; a tight version of the same code was 0.16 worse on the fresh seed,
but better against tables of its own copies (4.88 vs 4.68).
