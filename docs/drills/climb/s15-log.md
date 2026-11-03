# S15: closing exploiter 3's postflop edge (running log)

Branch climb/s15-exploiter3, from main 2a17295. Brief (coordinator, 2026-11-02 23:20): exploiter 3, a fresh red team
that played batch 5 as a black box, beats F heads-up (56% of matches) and three-handed (49% of first places against
39%); its own ablation (docs/drills/exploiter3/ablate.txt, on main) says the edge is its postflop counter,
`EXPLOIT_POST`. Name the F tendency it uses, fix it behind dials that are off by default, and screen against all three
exploiters and the guards. Screen seeds only (10000-10199); no held-out set, judge bot, judge field or held-out
variant was run, read or tuned on. Model mode at fixed speed through tools/climb_accept.py's own cells and cache
(scratch `goal/s15/quick.py` for chosen cells and `cmp.py` for the paired table). F's chunks are pinned to one
cache key, F as built at fcfb97e, because F plays identically behind the new dials. That was checked chunk for chunk
against main's F on every exploit cell (48 of 48 identical), and on confirm, guards and five variants at
10000-10039 at each code step (below). Workers 3, nice 5, host load 6-40 (other measurements running).

## Findings

**The leak: F folds too often when it checks and is bet into, heads-up, above all on the turn and river.** A bot
that bets every time F checks wins the pot often enough that its hand does not matter.

1. **What the counter does** (archive lines 922-944; our copy is the same code six lines lower). Heads-up, with
   nothing to call, the exploiter reads F's fold rate facing a single bet, per street and per position, smoothed
   toward priors it fitted by playing F (F out of position 0.66 / 0.73 / 0.57 on flop / turn / river, in position
   0.60 / 0.35 / 0.30) with the weight of 8 chances. Where that rate beats its bet's break-even by 0.05 it bets air
   and middling hands: in position 0.6 pot on the flop and 0.66 on the turn and river, air 90% / 85% / 70% of the
   time and middling hands 35% / 30% / 0%; out of position as the preflop raiser a 0.5-pot c-bet; out of position as
   the caller a 0.55-pot flop lead with draws (45%) and air (20%). Value bets 0.7-0.85 pot whatever F does. It never
   reads F's bet sizes, and F's check-raise rate only enters its answer to a raise.
2. **F's frequencies against it** (scratch `spots.py`, F as main ships in the exploit3_hu cell, screen seeds 10000-10199,
   400 tables, 24,514 hands; the exploiter's own counters agree):

   | F, heads-up pot | flop | turn | river |
   |---|---|---|---|
   | checks first out of position, then folds to the bet | 71% | 85% | 67% |
   | in position, folds to a lead | 74% | 64% | 64% |
   | exploiter bets after F's check | 79% | 75% | 41% |
   | break-even fold for its bet | 38% | 40% | 40% |

   Three-handed (exploit3_3) it is worse: F folds 81% / 92% / 89% after checking. By F's own tier read, F's
   checking range on the turn is 19% air, 19% overcards and gutshots, 44% weak and middle pairs (tier 2) and 17%
   tier 3; every tier-2 hand folds to the turn stab (99%) and to the river stab (100%): F's turn and river call
   margin (0.2 in SHIP_DIALS, on top of the price) leaves only tier 3 and up. F's check is capped (it bets every
   tier-4 hand first), it check-raises 4% of the time, and its checking range folds.
3. **What it bets** (scratch `reads.py`: the simulator's cards, F's tier read, heads-up tables, 100 seeds): after F
   checks the turn its bets are 26% air, 41% tier 2-3 and 33% tier 4 and up; as the aggressor (a barrel) 40% / 30% /
   29%. A tier-2 hand has about 0.4 equity against that and needs 0.28 to call.
4. **Where the points are** (scratch `abl.py`: the exploiter with `EXPLOIT_POST` on some streets only, heads-up,
   200 seeds, F's points of 10 / 7): on every street 8.268 (the cell), off 8.470, flop only 8.357, turn and river
   only 8.283, turn only 8.320, river only 8.365. The turn and river stabs carry nearly all of it (+0.19 of +0.20);
   the flop part adds little once those are there.
5. **The same tendency shows against other bots** that stab often, so the fix is not keyed to exploiter 3: F's
   turn fold after checking is 84% against elite1, 94% against rival3, 72% against exploiter 2, while their turn
   stabs are 21-44% air. Against value-heavy stabbers it is right: night's pool seats stab 40% of turns with 6% air
   (F folds 95%), rival1 16% with none.

**The fix: a stab read** (`hero.postflop.stab_*`, hyperion/strategy/postflop.py and profiler.py, every dial off by
default). The profiler counts, per seat and street, the seat's free action right after my check in a heads-up pot: a
c-bet, a barrel or a probe, whoever has the initiative. Facing the first bet of the street right after my check
heads-up, on the turn and river (`stab_streets` 6), the read takes the seat's smoothed rate over all three streets
(`stab_pool` 7, prior 0.4 worth 3 chances, no read before 3 chances). Above `stab_from` 0.55 it moves my equity
toward the tier's equity against a whole range (S11's WIDE_EQUITY tables plus a river row measured here) by the
weight (rate - 0.55) / (0.8 - 0.55), and the call margin toward `stab_margin` 0.03. A seat that bets nearly every
time I check bets most of its range there. Three gates keep it to opponents whose reads look like exploiter 3's:
- only while three or fewer players have chips (`stab_max_alive` 3);
- only against a seat that raises preflop at least 0.3 of its hands (`stab_pfr_min`: a loose-aggressive stabber);
- hold'em tables only (`stab_holdem_only`).

It never lowers a raise threshold and never bluffs (`stab_bluff`, off). Against exploiter 3, F's fold to the turn and
river stab after checking goes from 85% / 67% to 53% / 34% heads-up. Three-handed, with both opponents pooled, it goes
from 92% / 89% to 84% / 75%. F's heads-up postflop chips go from -3,640 to -1,669 bb in 400 tables. Exploiter 3 keeps
stabbing (turn 75% before and after, river 41% to 47%): its read of F's folds carries 8 hands of prior, and a
heads-up match lasts about 50 hands.

**The candidate, S15c** (code 6e63cbb, on top of SHIP_DIALS):

    {"dials": {"hero.postflop.stab_from": 0.55, "hero.postflop.stab_full": 0.8, "hero.postflop.stab_prior": 0.4,
               "hero.postflop.stab_min": 3, "hero.postflop.stab_pool": 7, "hero.postflop.stab_margin": 0.03,
               "hero.postflop.stab_max_alive": 3, "hero.postflop.stab_pfr_min": 0.3,
               "hero.postflop.stab_holdem_only": true}}

On the screen set it is up against exploiter 3 heads-up (+0.128 ± 0.110) and three-handed (+0.080 ± 0.058), and level
on every other exploit, confirm, guard, elite and variant cell (most of them identical or within ±0.001): ACCEPT under
`--aim exploit`. It does not touch the exploit layer's 0.33-pot stab, which is not exploiter 3's edge: exploiter 3
folds 53% to it, calls 43% and raises 4%. It raises only with strength 0.8 or more.

## The numbers

### Dev screens (quick.py, screen seeds 10000-10199, base F)

Every cell is 200 seeds (400 tables heads-up, 600 three-handed). Δ = candidate minus F in our seat's points, ± the
95% interval of the per-seed paired difference. F: exploit3_hu 8.268 (exploiter 8.732), exploit3_3 7.528 (7.952),
exploit_hu 9.227, exploit_3 8.458, exploit2_hu 7.848, exploit2_3 7.378 (S13's numbers for F, to the third decimal).

**Batch 1: the existing reads** (code 2a17295, dials on top of F):

| candidate | exploit3_hu | exploit3_3 | exploit_hu | exploit_3 | exploit2_hu | exploit2_3 |
|---|---|---|---|---|---|---|
| `cbet_from` 0.6 | -0.015 ± 0.108 | +0.093 ± 0.117 | +0.045 ± 0.112 | **-0.143 ± 0.140** | +0.098 ± 0.120 | +0.008 ± 0.116 |
| `wide_from` 0.6 | -0.045 ± 0.080 | -0.060 ± 0.124 | -0.030 ± 0.120 | -0.075 ± 0.152 | **+0.188 ± 0.123** | -0.063 ± 0.142 |
| `call_margin` 0.1 (everywhere) | +0.068 ± 0.122 | +0.033 ± 0.121 | -0.030 ± 0.100 | +0.000 ± 0.113 | **+0.255 ± 0.120** | -0.017 ± 0.122 |
| `probe_from` 0.6 | -0.037 ± 0.053 | -0.012 ± 0.085 | -0.015 ± 0.047 | -0.008 ± 0.056 | +0.007 ± 0.107 | +0.052 ± 0.112 |

S11's reads do not see exploiter 3. Its stabs are c-bets and barrels (the aggressor's read, which also fires on
exploiter 1), and its leads are rare (22% of flops), so the probe read stays under 0.75. A lower call margin
everywhere helps only against exploiter 2.

**Batch 2-5: the stab read** (`hero.postflop.stab_*`; every candidate also has `stab_margin` 0.03 and
`stab_holdem_only`; "pool 7" = the read over all three streets, "pool 6" = turn and river only):

| candidate | exploit3_hu | exploit3_3 | exploit_3 | exploit2_hu |
|---|---|---|---|---|
| always defend (weight 1 for every seat, turn and river) | +0.037 ± 0.139 | +0.018 ± 0.141 | | |
| from 0.5, full 0.75, prior 0.5 worth 3, pool 6 | **+0.128 ± 0.108** | +0.010 ± 0.112 | **-0.113 ± 0.113** | **+0.120 ± 0.101** |
| ... pool 7 | +0.113 ± 0.127 | +0.078 ± 0.112 | **-0.137 ± 0.119** | **+0.105 ± 0.099** |
| ... pool 7, also the flop, a flop check-raise bluff 0.5 | +0.098 ± 0.135 | +0.007 ± 0.142 | | |
| ... pool 7, only against the initiative (`stab_aggr_only`) | +0.052 ± 0.103 | +0.067 ± 0.078 | | |
| ... pool 6, `stab_aggr_only` | +0.068 ± 0.089 | +0.053 ± 0.079 | | |
| ... pool 7, `stab_aggr_only`, also the flop | +0.068 ± 0.134 | +0.107 ± 0.110 | | |
| pool 7, prior 0.4 worth 3 | **+0.142 ± 0.109** | **+0.115 ± 0.091** | -0.060 ± 0.106 | +0.098 ± 0.100 |
| pool 7, prior 0.4, no read before 3 chances | **+0.120 ± 0.111** | **+0.130 ± 0.086** | -0.067 ± 0.099 | +0.075 ± 0.099 |
| **S15** = pool 7, prior 0.4, min 3, from 0.55, full 0.8 | **+0.128 ± 0.110** | **+0.093 ± 0.074** | -0.047 ± 0.094 | +0.075 ± 0.099 |

S15 on the other two short cells: exploit_hu -0.060 ± 0.108, exploit2_3 -0.015 ± 0.085 (both level).

What the diagnostics showed between batches (scratch `spots.py`, `reads.py`, `linediff.py`, `rdiff.py`):
- **Always defending is worse than reading.** Exploiter 3 bluffs only while F's fold rate stays high. The weighted
  read lets F fold again against seats that stop stabbing, so F's calls stay mostly against air.
- **The read moves F's frequencies a lot.** With pool 7, from 0.5, prior 0.5, F's fold to the turn and river stab
  after checking goes from 85% / 67% to 33% / 24% heads-up, and from 92% / 89% to 51% / 46% three-handed. Most of the chips come back in one line:
  F checks and calls the flop, checks the turn and faces the barrel, which went from -2.74 to +2.74 bb a hand
  (307 hands; +1,650 bb in 400 tables). Heads-up postflop, F went from -3,640 bb to -1,995 bb.
- **`stab_aggr_only` did not pay.** It skips bets made after the seat called my bet, which hold its calling range
  (11% air on the turn, against 40% for its barrels). In that line F did lose about 70 bb by calling. Calling there
  anyway lowers F's fold rate on that street everywhere, and that fold rate is what exploiter 3 reads to decide its
  bluffs, so the screen favours defending every line. The dial stays (off) for a different opponent.
- **The prior was the cost against exploiter 1** (three-handed). There the read fired on the night seat (night.1,
  value-heavy, 31-41% of turns), not on exploiter 1: chips against exploiter 1 went up by 265-849 bb, against night
  down by 786 bb with prior 0.5. A prior at the threshold lets two early stabs switch the read on. Prior 0.4 and a
  3-chance minimum keep night out most of the time (F's turn fold against it 95% -> 82%, against exploiter 1
  69% -> 33%): night down 288 bb, exploiter 1 up 849 bb.

### S15 on confirm and guards (climb_accept, code fcfb97e = c8ffaeb289; the full run was stopped after these)

| cell | F | S15 | S15 - F | |
|---|---|---|---|---|
| night (confirm) | 5.972 | 5.963 | -0.010 ± 0.022 | level |
| night_hard | 5.499 | 5.493 | -0.006 ± 0.016 | level |
| realistic | 6.370 | 6.349 | **-0.021 ± 0.018** | DOWN |
| top | 5.058 | 5.062 | +0.004 ± 0.019 | level |
| night @10/7/5/4/3/2/1/0 | 6.199 | 6.163 | -0.037 ± 0.039 | level |
| night @50/25/12/6/3/2/1/1 | 24.699 | 24.567 | -0.133 ± 0.237 | level |
| night, doubling blinds | 5.848 | 5.833 | **-0.014 ± 0.014** | DOWN |

Two guards down: at 8-max the read fires on ordinary stabbers in heads-up pots. A seat there shows few heads-up
chances against me before the read can fire (three chances against a prior worth three), and night's seats stab 40-50%
of the time, close enough to the threshold that a few early stabs switch the read on. F's fold there is right: those
stabs are value. The fix for that (b5ce62a): `stab_max_alive` 3, the read only while three or fewer players have
chips. Exploiter 3's edge is heads-up and three-handed (it trails at 8-max). By the time an 8-max table is down to
three, each seat has shown its stabs over many hands. The heads-up and three-handed cells play exactly as with S15
(tested).

### S15b (S15 + `stab_max_alive` 3) on confirm and guards (b5ce62a; F's chunks those of the run above)

| cell | S15b - F | |
|---|---|---|
| night (confirm) | -0.004 ± 0.004 | DOWN (at the bound) |
| night_hard | -0.003 ± 0.005 | level |
| realistic | -0.004 ± 0.005 | level |
| top | -0.004 ± 0.005 | level |
| night @10/7/5/4/3/2/1/0 | -0.007 ± 0.010 | level |
| night @50/25/12/6/3/2/1/1 | -0.076 ± 0.096 | level |
| night, doubling blinds | -0.004 ± 0.006 | level |

Much smaller, still down on night. Where it fires (scratch `fires.py`, night 10000-10099 x 8): 47 times in 800
tables, all in endgames, spread over the seven night seats. Their stabs there were 53% tier 4 and up and 21% air
(exploiter 3's when the read fires on it heads-up: 36% and 31%), and F called 38% of them. Their stab rates by then
read 0.60-0.70, the same as exploiter 3's (median 0.69-0.70). A few decisive endgame hands are the whole difference
on night. Raising the threshold does not
separate them: from 0.6 / full 0.85 / min 4 and from 0.65 / full 0.9 / min 4 gave night -0.004 ± 0.004 and
-0.002 ± 0.003, exploit3_hu +0.083 and +0.075 (level), exploit3_3 +0.048 and +0.028. What separates them is preflop.
Where the read fired, the bettor's preflop raise rate (Profiler.pfr_rate) had a median of 0.41 three-handed and 0.48
heads-up for exploiter 3, and 0.09-0.23 for the night seats. Its late open rate was 0.74-0.88 against 0.37-0.65.
A tight seat that stabs often in an endgame has the hands; a loose-aggressive one does not. Hence `stab_pfr_min`
(6e63cbb): the read only against a seat that raises at least 0.3 of its hands preflop.

### S15c on every stage (screen seeds 10000-10199, code 6e63cbb = 25313e4d3d; F's chunks as above)

| stage | cell | F | S15c | S15c - F | | exploiter F / S15c |
|---|---|---|---|---|---|---|
| exploit | exploit (8-max, 10/7/5/4/3/2/1/0) | 5.839 | 5.845 | +0.006 ± 0.013 | level | 4.608 / 4.603 |
| | exploit_hu | 9.227 | 9.168 | -0.060 ± 0.108 | level | 7.772 / 7.832 |
| | exploit_3 | 8.458 | 8.465 | +0.007 ± 0.086 | level | 6.900 / 6.937 |
| | exploit2 (8-max) | 5.844 | 5.843 | -0.001 ± 0.004 | level | 5.086 / 5.086 |
| | exploit2_hu | 7.848 | 7.923 | +0.075 ± 0.099 | level | 9.152 / 9.078 |
| | exploit2_3 | 7.378 | 7.387 | +0.008 ± 0.061 | level | 8.165 / 8.143 |
| | exploit3 (8-max) | 5.471 | 5.469 | -0.002 ± 0.005 | level | 5.306 / 5.306 |
| | exploit3_hu | 8.268 | 8.395 | **+0.128 ± 0.110** | UP | 8.732 / 8.605 |
| | exploit3_3 | 7.528 | 7.608 | **+0.080 ± 0.058** | UP | 7.952 / 7.848 |
| confirm | night | 5.972 | 5.972 | -0.000 ± 0.001 | level | |
| guards | night_hard | 5.499 | 5.499 | +0.000 ± 0.000 | level | |
| | realistic | 6.370 | 6.370 | -0.000 ± 0.001 | level | |
| | top | 5.058 | 5.058 | +0.000 ± 0.000 | level | |
| | night @10/7/5/4/3/2/1/0 | 6.199 | 6.198 | -0.001 ± 0.006 | level | |
| | night @50/25/12/6/3/2/1/1 | 24.699 | 24.673 | -0.026 ± 0.036 | level | |
| | night, doubling blinds | 5.848 | 5.847 | -0.001 ± 0.001 | level | |
| elite | elite | 4.865 | 4.865 | +0.000 ± 0.000 | level | |
| | elite_night | 5.422 | 5.423 | +0.001 ± 0.001 | level | |
| | mirror | 4.498 | 4.499 | +0.001 ± 0.001 | level | |
| | elite_b | 4.638 | 4.638 | +0.000 ± 0.000 | level | |
| | mirror_b | 4.466 | 4.467 | +0.001 ± 0.003 | level | |
| variants | top_heavy (realistic) | 28.654 | 28.646 | -0.008 ± 0.013 | level | |
| | antes_from_level_3 | 6.496 | 6.496 | -0.000 ± 0.001 | level | |
| | fast_schedule | 6.122 | 6.121 | -0.001 ± 0.001 | level | |
| | straddle | 6.412 | 6.412 | +0.000 ± 0.000 | level | |

0 timeouts and 0 errors in either spec (5.3 million decisions each). Variants: the four catalog entries whose tables
are hold'em (the read's gate shuts on every other entry; tested on short_deck and bounty, and identical sample for
sample on river_of_blood, short_deck, bounty and swap_holdem at 40 seeds, below). Against exploiter 3, F heads-up
goes from 8.268 to 8.395 against 8.732 to 8.605 (still behind; switching the counter off entirely gives 8.470), and
three-handed from 7.528 to 7.608 against 7.952 to 7.848.

### Identity, latency, tests

- **Identity** (climb_accept `--cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, main's worktree at
  2a17295 against a detached worktree at the branch, sample lists compared chunk by chunk). fcfb97e: 14 of 14 chunks
  identical. c077ffa: 14 of 14, plus river_of_blood, short_deck, bounty, swap_holdem and top_heavy at 40 seeds,
  10 of 10. 6e63cbb (the candidate's code): 14 of 14 and 10 of 10.
- **Latency** (`tools/latency.py --bot composite --hand-end --reps 3 --tables 12`, per-call minimum, load 10, µs, F /
  S15c): realistic act p99 101.8 / 101.7, max 128.6 / 132.5, hand_end p99 137.3 / 138.9; exploit3_hu (hu.json) act
  p99 80.0 / 81.6, max 96.4 / 132.5, hand_end p99 84.7 / 85.9. Under 200 µs. The read costs a few counter updates per
  postflop action and, facing a bet, one smoothed rate.
- **Tests**: tests/test_s15_dials.py (the counters, a lead is not a stab, a long board, each dial reaches the
  decisions, the gates: heads-up with `stab_max_alive` as without, a `stab_pfr_min` no seat passes plays as F, twist
  tables play as F, three-handed replays exactly). Full suite at fcfb97e under load 14: 1,260 passed, 20 failed. One
  failure was real: river_of_blood deals past the river, the profiler's street reached 4, and the new counter indexed
  out of range at hand_end (SafeBot caught it, so play changed on that variant). Fixed in c077ffa: a long board's
  later streets count as the river, with a test. The other 19 are load:
  - wall-clock budgets (test_sim_bestiary under-budget, test_slowbox);
  - model-mode replay tests of fields with wall-clock members (exploit3, outside, elite_night, elite_judge_b); the
    exploit3 and outside ones, re-run on main's worktree, fail there the same way;
  - three that passed when re-run alone (fakekits, hand_end_interrupt, timeout_model).

  Full suite at 6e63cbb (the candidate's code), load 12: 1,284 passed, 5 failed, 2 skipped. The 5 were drills_run
  short_deck-b, nightof_latency, bestiary toss_mc and outside elite_judge / elite_judge_b. Re-run alone on the
  branch: 4 passed and 1 skipped. Re-run on main's worktree at the same time, 3 of them failed there.

## What I would still try

- **The flop lead into F in position.** Exploiter 3's 0.55-pot flop lead as the big blind is 51% air, and F folds
  74% of the time (-1,971 bb in 400 heads-up tables, the largest losing line left). Its lead rate is only 22%, so no
  frequency read finds it. Shown cards would (S12's size histograms), but F rarely calls far enough to see them.
- **Faster evidence.** Heads-up tables last about 50 hands, so the read fires only after a third of a match. A prior
  keyed to the table (short-handed, a loose-aggressive opener) instead of the seat's own count would start sooner.
  Keep the pfr gate, which is what kept night clean.
- **The checking range itself.** F checks only hands it will fold (it bets every tier-4 hand first, check-raises 4%).
  Checking some value hands against a seat that stabs often (S11's `probe_trap`, read by this stab rate) would make
  the stabs cost it, rather than only calling more.
- **The flop check-raise** (`stab_bluff` on the flop) was level in dev (+0.098 ± 0.135 heads-up). Exploiter 3 folds
  air and middling hands to a raise, so a cleaner version is worth a screen.
- **Exploiter 1 heads-up** is -0.060 ± 0.108 under S15c (level). The read fires on it (pfr 0.68, frequent stabs) and
  chips against it went up three-handed. Worth watching on the held-out set.
