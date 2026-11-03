# S15d: a stricter gate for the stab read (running log)

Branch climb/s15d-gate, from main a2a7bf6. Brief (coordinator, 2026-11-03 11:57): batch 6 failed the judges
(`outside` -0.0032 ± 0.0021 pooled over the judge set and a fresh replicate). Every judge field is plain hold'em and
only S6 and S15c act there, so one or both fire against seats they should not. Audit S15c's stab read on tuning fields
only, make its gate stricter so it fires only against seats that stab like exploiter 3, and screen. No judge bot or
judge field was run, read or looked at here (outside*, out_*, rival4, rival5, elite3, elite5, adapt2, elite_judge*,
adapt_judge*, judge*). Audit seeds 11000-11099 (diagnostic, not a screen, held-out or judge range); screen seeds
10000-10199. Workers 2, nice 5, detached.

## Findings

**Where S15c acts against seats it was not built for.** Scratch `goal/s15d/audit.py`: F with S15c's dials, every
time the read's gates pass (three or fewer alive, the bettor raising 30%+ preflop, hold'em, a bet right after F's
check heads-up). It records who the bettor is, whether the read acts (its rate above 0.55), and whether F's decision
changes against a shadow decision without the read (same RNG state). The run covers 50 seeds x 8 of each 8-max
field (night, night_hard, realistic, top, elite, elite_night, elite_b, mirror, mirror_b, and exploit, exploit2,
exploit3, adapt), and 100 seeds x 2 or x 3 of each heads-up and three-handed exploit and adapt cell, about 6,800
tables in all.

| seat type | where | gates pass | S15c acts | decisions changed | S15d acts | S15d changed |
|---|---|---|---|---|---|---|
| Rival3Bot | night, night_hard, elite, elite_night, exploit/adapt pools | 43 | 12 | 2 | 2 | 0 |
| Rival2Bot | night_hard, exploit/adapt pools | 40 | 12 | 4 | 0 | 0 |
| Elite1Bot | elite, elite_night, mirror_b | 9 | 7 | 4 | 2 | 2 |
| Elite2Bot | elite_night, mirror | 7 | 6 | 4 | 0 | 0 |
| RivalBot (rival1) | realistic, elite_b, night_hard, exploit pools | 12 | 5 | 4 | 0 | 0 |
| LooseAggroStudent | realistic, elite_night | 8 | 5 | 5 | 0 | 0 |
| ShipCopy (F) | mirror, mirror_b | 6 | 5 | 3 | 0 | 0 |
| AgentMonteCarloBot | night, exploit/adapt pools | 40 | 1 | 0 | 0 | 0 |
| Maniac, AgentPushFold, TrackB kits, AgentCharts, NaiveEquity | night pools | 58 | 0 | 0 | 0 | 0 |
| **all non-exploiter seats** | | 223 | **53** | **26** | **4** | **2** |
| exploiter 3 | exploit3, exploit3_hu, exploit3_3 | 826 | 533 | 257 | 454 | 219 |
| exploiter 1 | exploit, exploit_hu, exploit_3 | 1,513 | 1,324 | 743 | 726 | 418 |
| exploiter 2 | exploit2, exploit2_hu, exploit2_3 | 541 | 487 | 326 | 28 | 18 |
| adapt1 | adapt, adapt_hu, adapt_3 | 397 | 149 | 100 | 58 | 36 |

Every changed decision against a non-exploiter seat is a fold turned into a call, and those stabs were mostly
value. The S15c gate passes ordinary seats that raise 30-33% preflop in short-handed endgames: the elite builds,
rival 1-3, F's own copies (whose exploit layer stabs into checks) and the loose-aggressive student. With 3-6 heads-up
chances against F by then, their stab rate reads 0.6-0.75, the same as exploiter 3's.

**What separates exploiter 3** (the bettor's profiler reads where S15c acts, p10 / median):

| | stab rate (bets right after F checks, raw) | pfr | lead rate (its other free bets) |
|---|---|---|---|
| exploiter 3 | 0.67 / 0.80 | 0.36 / 0.48 | 0.10 / 0.20 |
| elite1, elite2 | 0.60-0.64 / 0.69-1.00 | 0.30 / 0.30-0.31 | 0.23-0.29 / 0.40 |
| rival 1, 2, 3 | 0.67-0.75 / 0.75-0.83 | 0.31-0.34 / 0.31-0.42 | 0.23-0.38 / 0.37-0.44 |
| F's copies | 1.00 / 1.00 | 0.31 / 0.31 | 0.44 / 0.48 |
| loose-aggressive student | 0.75 / 1.00 | 0.31 / 0.32 | 0.64 / 0.65 |

(Lead rate = (its free bets apart from right after F's checks + 0.6) / (those chances + 2), from the profiler's own
counters.) Exploiter 3 bets when F checks and rarely otherwise: it bluffs where it has read F's folds, and leads only
a few flops. An ordinary aggressive seat bets wherever it may, so its stabs are a slice of its betting range, value
included. Exploiter 3 also raises preflop more than the ordinary seats that pass the 0.3 gate.

**The gate, fixed from the audit before any screen:** S15c plus `stab_pfr_min` 0.35 (from 0.3) and the new
`stab_lead_max` 0.4 (Profiler.lead_rate, prior 0.3 worth 2 chances). On the audit's events this keeps 4 of the 53
non-exploiter acts (two decisions changed, both in one elite_night hand against elite1) and 454 of exploiter 3's 533
(85%; 219 of 257 changed decisions). Exploiter 1 keeps 726 of 1,324, exploiter 2 only 28 of 487 (it leads into F
nearly every chance; S11's probe read is its fix), adapt1 58 of 149. Stricter choices did not remove the elite1 hand:
lead 0.35 with pfr 0.35 keeps 3 non-exploiter acts and 79% of exploiter 3's, and pfr 0.38 alone keeps 11 and 86%.

S15d = `{"dials": {"hero.postflop.stab_from": 0.55, "hero.postflop.stab_full": 0.8, "hero.postflop.stab_prior": 0.4,
"hero.postflop.stab_min": 3, "hero.postflop.stab_pool": 7, "hero.postflop.stab_margin": 0.03,
"hero.postflop.stab_max_alive": 3, "hero.postflop.stab_pfr_min": 0.35, "hero.postflop.stab_lead_max": 0.4,
"hero.postflop.stab_holdem_only": true}}` (code 6aff475).

**S15d on the screen set** (climb_accept `--aim exploit --runout-term --identical twists`, every stage, code
0e3c9d90bb, 82 min; corrected deltas): REJECT.
- Every ordinary, strong and variant cell is identical to F sample for sample: night, night_hard, realistic, top,
  elite, elite_night, mirror, elite_b, mirror_b, the doubling schedule, top_heavy, antes_from_level_3, fast_schedule
  and straddle are all +0.000 ± 0.000. The two other payout tables are -0.000 ± 0.005 and -0.016 ± 0.031 (a few
  changed tables). So against ordinary seats the gate does what the audit said.
- exploit3_hu **+0.116 ± 0.073 UP** (raw +0.128 ± 0.110). exploit3_3 +0.028 ± 0.030 (level; S15c had +0.080 raw).
- **exploit_hu -0.060 ± 0.059 DOWN** (raw +0.037 ± 0.084: the term moved +0.097 ± 0.077 toward the base; F with
  S15d got the better runouts). Against exploiter 1 heads-up the read still acts (551 of the audit's 1,324 events are
  heads-up, all passing the S15d gate), and calling its stabs wider loses. S11 found the same with its aggressor's
  read.

**What separates exploiter 1 from exploiter 3** (the same events, p10 / p25 / p50 / p75):

| | lead rate | free-bet rate, stabs included ((bets + 0.8) / (chances + 2)) | pfr |
|---|---|---|---|
| exploiter 3 | 0.10 / 0.13 / 0.20 / 0.30 | 0.27 / 0.32 / 0.40 / 0.51 | 0.36 / 0.42 / 0.48 / 0.53 |
| exploiter 1 | 0.30 / 0.30 / 0.33 / 0.55 | 0.58 / 0.67 / 0.75 / 0.82 | 0.58 / 0.64 / 0.70 / 0.75 |
| exploiter 2 | 0.40 / 0.50 / 0.58 / 0.66 | 0.59 / 0.66 / 0.72 / 0.79 | 0.36 / 0.50 / 0.56 / 0.59 |
| non-exploiter seats | 0.27 / 0.30 / 0.43 / 0.52 | 0.37 / 0.46 / 0.51 / 0.59 | 0.30 / 0.31 / 0.32 / 0.36 |

Exploiter 1 bets 75% of all its free chances (Monte Carlo equity against F's weak checking range: it has the hand
often enough). Exploiter 3 bets 40%: it stabs after F's checks and checks most of its other chances. A seat that bets
most of its free chances is betting a range, not attacking checks. Hence `stab_free_max` (c3cfb75: Profiler.free_bet_rate,
prior 0.4 worth 2), fixed at 0.5 from these events before the screen. On the audit's events, S15d plus free 0.5 keeps:
- 3 non-exploiter acts (the elite1 hand and one rival3 decision, unchanged);
- 372 of exploiter 3's 533 (270 of 305 heads-up, 100 of 147 three-handed);
- exploiter 1: 60 of 1,324 (10 heads-up); exploiter 2: 9; adapt1: 49.

Lead 0.25 without a free gate kept 315 of exploiter 3's and 85 of exploiter 1's. Free 0.55 kept 409 and 90.

S15e = S15d + `"hero.postflop.stab_free_max": 0.5` (code c3cfb75), the candidate:

    {"dials": {"hero.postflop.stab_from": 0.55, "hero.postflop.stab_full": 0.8, "hero.postflop.stab_prior": 0.4,
               "hero.postflop.stab_min": 3, "hero.postflop.stab_pool": 7, "hero.postflop.stab_margin": 0.03,
               "hero.postflop.stab_max_alive": 3, "hero.postflop.stab_pfr_min": 0.35,
               "hero.postflop.stab_lead_max": 0.4, "hero.postflop.stab_free_max": 0.5,
               "hero.postflop.stab_holdem_only": true}}

**S15e on the screen set** (climb_accept `--aim exploit --runout-term --identical twists`, every stage, code
c3cfb75, workers 2, load 14-21; corrected deltas): **ACCEPT**.

| stage | cell | F | S15e | S15e - F | | exploiter F / S15e |
|---|---|---|---|---|---|---|
| exploit | exploit (8-max) | 5.765 | 5.764 | -0.001 ± 0.006 | level | 4.608 / 4.610 |
| | exploit_hu | 9.247 | 9.246 | -0.001 ± 0.007 | level | 7.772 / 7.772 |
| | exploit_3 | 8.491 | 8.502 | +0.010 ± 0.020 | level | 6.900 / 6.908 |
| | exploit2 (8-max) | 5.849 | 5.849 | +0.000 ± 0.000 | level | 5.086 / 5.086 |
| | exploit2_hu | 7.903 | 7.903 | +0.000 ± 0.000 | level | 9.152 / 9.152 |
| | exploit2_3 | 7.321 | 7.324 | +0.003 ± 0.018 | level | 8.165 / 8.180 |
| | exploit3 (8-max) | 5.447 | 5.447 | +0.001 ± 0.002 | level | 5.306 / 5.306 |
| | exploit3_hu | 8.339 | 8.457 | **+0.118 ± 0.074** | UP | 8.732 / 8.590 |
| | exploit3_3 | 7.520 | 7.547 | **+0.027 ± 0.026** | UP | 7.952 / 7.913 |
| | adapt (8-max) | 5.822 | 5.823 | +0.001 ± 0.003 | level | 5.106 / 5.106 |
| | adapt_hu | 8.666 | 8.667 | +0.001 ± 0.029 | level | 8.395 / 8.387 |
| | adapt_3 | 7.934 | 7.938 | +0.004 ± 0.008 | level | 7.657 / 7.662 |
| confirm | night | 6.006 | 6.006 | +0.000 ± 0.000 | level | |
| guards | night_hard | 5.470 | 5.470 | +0.000 ± 0.000 | level | |
| | realistic | 6.350 | 6.350 | +0.000 ± 0.000 | level | |
| | top | 5.054 | 5.054 | +0.000 ± 0.000 | level | |
| | night @10/7/5/4/3/2/1/0 | 6.243 | 6.243 | -0.000 ± 0.005 | level | |
| | night @50/25/12/6/3/2/1/1 | 24.719 | 24.703 | -0.016 ± 0.031 | level | |
| | night, doubling blinds | 5.872 | 5.872 | +0.000 ± 0.000 | level | |
| elite | elite, elite_night, mirror, elite_b, mirror_b | | | +0.000 ± 0.000 each | level | |
| variants | top_heavy, antes_from_level_3, fast_schedule, straddle | | | +0.000 ± 0.000 each | level | |

0 timeouts, 0 errors. Weighted score (addendum 11): +0.0007 ± 0.0009 night points, lower bound -0.0003 (W-min
-0.0005); the cap holds.
- **Ordinary and strong seats.** Sample for sample identical to F on every ordinary, strong and variant cell except
  two payout guards. In those, one chunk each of night @10/7/5/... and night @50/25/... differs, from a few endgame
  hands that net to -0.000 and -0.016 ± 0.031.
- **Exploiter 1 heads-up**, S15d's down cell, is now -0.001 ± 0.007: the free-bet gate takes it out.
- **Exploiter 3.** The read keeps heads-up against it: +0.118 against S15c's +0.128 raw. Three-handed it keeps a third
  of S15c's gain (+0.027 UP against S15c's +0.080 raw).
- **Exploiter 2** is no longer touched (S11's probe read is its fix). Adapt1 is level.

### The audit again, at S15e's dials (the same audit seeds and fields)

| seat type | where | gates pass | S15e acts | decisions changed |
|---|---|---|---|---|
| Elite1Bot | elite_night (one hand: its turn and river stab) | 2 | 2 | 2 |
| Rival3Bot | night, night_hard, exploit/adapt pools | 9 | 1 | 0 |
| AgentMonteCarlo, Rival2, AgentCharts, Maniac, AgentPushFold, RivalBot | exploit/adapt pools | 25 | 0 | 0 |
| **all non-exploiter seats** | | 36 | **3** | **2** |
| exploiter 3 | exploit3_hu 269 / 134, exploit3_3 98 / 41 | 571 | 367 | 175 |
| exploiter 1 | exploit, exploit_hu, exploit_3 | 119 | 58 | 35 |
| exploiter 2 | exploit2_3 | 13 | 9 | 6 |
| adapt1 | adapt_hu, adapt_3 | 203 | 47 | 27 |

The offline estimate held. Against non-exploiter seats the read acts 3 times in about 6,800 tables (S15c: 53) and
changes 2 decisions (S15c: 26). Against exploiter 3 it acts 367 times (S15c: 533).

### Identity, latency, tests

- **Identity**: the branch with the new dials off (31b8f5c, main c8d64fa merged in) against main's F at c8d64fa
  (`climb_accept --cand '{"dials": {}}' --set 10000:10040`). Confirm, guards and five variants (river_of_blood,
  short_deck, bounty, swap_holdem, top_heavy at 40 seeds) from detached worktrees: 24 of 24 chunks identical. The
  screen ran at c3cfb75, before main's batch 6 commit (V-f + V-h) was merged in; batch 6's dials act only on twist
  tables. So every cell screened (plain hold'em, and the four hold'em-structure variants) plays the same at 31b8f5c.
- **Latency** (`tools/latency.py --bot composite --hand-end --reps 3 --tables 12`, per-call minimum, load 14, µs, F /
  S15e): realistic act p99 108.9 / 106.3, hand_end p99 145.1 / 141.3; exploit3_hu (hu.json) act p99 98.0 / 92.5,
  hand_end p99 85.2 / 91.2. Under 200.
- **Tests**: tests/test_s15_dials.py (+3: the lead rate's counting, and each new gate reaches the decisions and plays
  as F when shut), test_s11_dials, test_apicard (the card regenerated), test_compose: 50 passed.

## What I would still try

- **Three-handed.** S15e keeps a third of S15c's three-handed gain (+0.027 against +0.080 raw). There exploiter 3
  plays more multiway hands, and its free-bet rate (median 0.40, 75th percentile 0.51 over all its events) runs
  into the 0.5 gate there: 100 of its 147 three-handed events are kept, against 270 of 305 heads-up. A free-bet rate over heads-up pots only would separate it better. The
  profiler counts free actions in every pot.
- **The one elite1 hand.** Two decisions in about 6,800 tables. Its lead and free rates were low that table (0.28,
  under 0.5) and its pfr 0.39. A per-table minimum of free-action evidence (it had few heads-up free chances) would
  take it out, untested.
- **Exploiter 1.** Calling its stabs wider loses (S11, and S15d here), and the free-bet gate is what removes it.
  Exploiter 1 bets 75% of its free chances. A seat that bets 50-60% with a weak checking range against it would sit
  at the gate's edge, and no tuning field has one.
