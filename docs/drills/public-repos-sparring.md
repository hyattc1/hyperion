# Public-repo sparring

**Status (09:03, 2026-10-31): COMPLETE.** Every repo was audited and every playable bot ran 300+ strict
tables. All numbers below are from runs against Hero **pinned at commit `5257118`**, exported into scratch
with `git archive`. The deep-pass agent's uncommitted edits to `hyperion/strategy/*` landed in the
shared tree at 08:39, in the middle of the first runs. The first runs (08:33-08:36, the tree as it stood
then) agree with the pinned reruns to within 0.13 point for every bot, and within 0.06 for most.

> **PRIORITY FLAG: microholdem's `MicroAgent` (ryankkhalil19/microholdem, MIT) is within 0.3 points of
> Hero in every field it sat in, and ahead of Hero in one run.**
>
> | field (strict) | Hero | MicroAgent | gap |
> |---|---|---|---|
> | Hero + tag + 2 MicroAgent + 4 microholdem archetypes, 300 tables | 5.678 ± 0.199 | 5.840 ± 0.128 | **MicroAgent +0.16** |
> | same field, 300 seeds × 8 duplicate-dealt rotations | 5.825 ± 0.073 | 5.682 ± 0.043 | Hero +0.14 |
> | our **top** field, MicroAgent in the 2nd rival1 seat, 2,400 rotated | 4.954 ± 0.081 | 4.766 ± 0.073 | Hero +0.19 |
> | our **realistic** field, MicroAgent in the timeout_then_recover seat, 2,400 rotated | 5.166 ± 0.087 | 4.967 ± 0.078 | Hero +0.20 |
> | best-of-public field (one seat each), 1,200 rotated | 5.648 ± 0.135 | 4.680 ± 0.108 | Hero +0.97 |
> | mirror: Hero among 7 MicroAgents, 800 rotated (uniform 4.5) | 4.901 ± 0.174 | 4.443 ± 0.025 | Hero +0.40 over uniform |
> | mirror: MicroAgent among 7 Heroes, 800 rotated (uniform 4.5) | 4.477 ± 0.019 | 4.658 ± 0.130 | **MicroAgent +0.16 over uniform** |
>
> Read: MicroAgent is a peer of Hero, not a ceiling. It is level with Hero at a table of weak bots and
> 0.19-0.20 behind in our top and realistic fields, where it lands between `tag` and `pushfold`. rival1 is
> still the strongest opponent we have (top 5.24, realistic 5.45, both ahead of Hero). Hero wins the
> mirror (+0.40 among MicroAgents), but **a single MicroAgent also beats a table of seven Heroes (+0.16 ±
> 0.13)**. That fails the bar the handoff sets for rival1 (≤ uniform + 0.1) and points at something in
> Hero that MicroAgent exploits. The likely candidate is the push/fold band (see takeaways). It is kept as an
> opponent: **`hyperion/sim/rivals/microholdem.py`** (ours) imports the clone named by
> `HYPERION_MICROHOLDEM` and is disabled when that is unset. Every other public bot is at least 0.37 behind Hero
> in its own field (0.49 in the duplicate-dealt poker-gym run) and 0.90 behind in the best-of field.

Bounded side task, 90-minute cap (08:25 to 09:55). The competitor prep repos from
`docs/research/notes/presolved_resources.md` section 4 (and everything else listed there) were cloned
fresh into an isolated scratch directory. Each was read for unsafe behaviour before running, adapted in
scratch to our Bot protocol, and run as opponents. **Nothing from these repos is copied into this repo.**

## Results

All runs use strict mode and the default `Rules()` (our realistic structure: 2,000 chips, 10/20 to
200/400 every 25 hands, 200-hand cap, placeholder payouts 8..1). The field is Hero + tag + their bots
unless named otherwise. "tmo" is the share of `act()` calls over 1 ms. p99 is `act()` latency including our
adapter, whose hand replay adds about 7-10 µs. **The machine was loaded the whole time** (another agent's
sweep ran 10 processes on 8 cores; load 6-13), so tmo, p99 and max are inflated for every bot. The first
microholdem pass at load 3 showed MicroAgent at 0.001% tmo and p99 153 µs. Hero's SafeBot swallowed 0
exceptions in every run, but 47-1,572 of its own deadline overruns per run (safe_over, from load
again). It entered panic mode on 0-3 tables per run (6 of the 12,400 pinned tables).

### microholdem (MIT)

*300 seeds (seed 11), 49,854 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs | read |
|---|---|---|---|---|---|---|---|---|
| **MicroAgent** | 2 | 5.840 ± 0.128 | 25 16 19 16 13 7 4 0 | 69 | 0 | 0.38 | 354 | Format-built: live ICM jam/fold to 20 bb with solved multiway calling ranges, rank-fraction opens by players behind, 3-bet 6-7.5%, postflop C++ Monte Carlo vs ranges read from each line (100 µs budget), heads-up river CFR table; no cross-hand opponent model |
| Hero | 1 | 5.678 ± 0.199 | 24 13 16 17 18 9 3 0 | 71 | 0 | 0.16 | 100 | ours (pinned at 5257118) |
| tag | 1 | 5.512 ± 0.184 | 7 28 18 21 11 10 4 1 | 80 | 0 | 0.04 | 19 | ours (bestiary ChartTAG) |
| granite | 1 | 4.475 ± 0.201 | 3 15 14 14 18 23 12 1 | 92 | 0 | 0.14 | 103 | Tight: pot-raises at preflop equity ≥ .66 vs random, postflop raises ≥ .85 (61-413 raises per run below the minimum, clamped by the engine) |
| jammer | 1 | 4.392 ± 0.232 | 13 8 10 11 17 20 19 2 | 85 | 0 | 0.16 | 126 | Push/fold tables ≤ 20 bb, raises ≥ .62 deeper, shoves postflop ≥ .7 when ≤ 15 bb |
| oracle | 1 | 2.250 ± 0.193 | 3 3 2 3 6 14 26 45 | 97 | 0 | 0.22 | 176 | Equity vs one random hand, raises .7 pot, calls whenever equity > pot odds (spews multiway) |
| blitz | 1 | 2.013 ± 0.174 | 2 2 1 2 4 10 29 50 | 98 | 0 | 0.13 | 161 | Raises at equity ≥ .5 or 35% at random, calls at pot odds − .05 |

*8 rotations × 300 seeds (seed 12), 402,904 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| Hero | 1 | 5.825 ± 0.073 | 28 14 15 15 15 9 3 0 | 68 | 0 | 0.05 | 64 |
| **MicroAgent** | 2 | 5.682 ± 0.043 | 21 17 18 16 13 10 4 1 | 73 | 0 | 0.13 | 211 |
| tag | 1 | 5.506 ± 0.064 | 8 26 22 17 12 9 5 1 | 80 | 0 | 0.01 | 17 |
| granite | 1 | 4.658 ± 0.064 | 6 14 15 15 20 20 10 1 | 88 | 0 | 0.04 | 74 |
| jammer | 1 | 4.320 ± 0.080 | 11 8 9 13 15 19 20 3 | 86 | 0 | 0.05 | 79 |
| oracle | 1 | 2.284 ± 0.062 | 2 2 3 4 6 13 27 43 | 98 | 0 | 0.06 | 94 |
| blitz | 1 | 2.043 ± 0.060 | 2 1 1 3 5 11 27 50 | 97 | 0 | 0.07 | 94 |

Our top field with MicroAgent in the second rival1 seat:

*8 rotations × 300 seeds (seed 13), 447,972 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| rival1 | 1 | 5.241 ± 0.093 | 32 11 6 10 10 11 12 8 | 62 | 0 | 0.06 | 101 |
| Hero | 1 | 4.954 ± 0.081 | 21 11 11 12 13 15 9 7 | 71 | 0 | 0.05 | 73 |
| tag | 1 | 4.905 ± 0.073 | 5 18 22 19 14 10 8 6 | 82 | 0 | 0.01 | 18 |
| hero_tight | 1 | 4.881 ± 0.076 | 10 16 15 15 16 14 10 4 | 78 | 0 | 0.05 | 70 |
| **MicroAgent** | 1 | 4.766 ± 0.073 | 10 13 17 16 15 12 9 8 | 81 | 0 | 0.15 | 250 |
| pushfold | 1 | 4.548 ± 0.071 | 5 16 17 15 13 11 12 10 | 83 | 0 | 0.01 | 22 |
| loose_aggro | 1 | 4.151 ± 0.091 | 14 12 9 8 10 12 16 19 | 76 | 0 | 0.01 | 12 |
| montecarlo30 | 1 | 2.554 ± 0.066 | 2 3 4 6 8 14 25 38 | 96 | 0 | 9.58 | 2633 |

Our realistic field with MicroAgent in the timeout_then_recover seat:

*8 rotations × 300 seeds (seed 14), 445,410 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| rival1 | 1 | 5.447 ± 0.093 | 35 12 7 10 11 10 9 7 | 59 | 0 | 0.09 | 100 |
| Hero | 1 | 5.166 ± 0.087 | 22 12 14 13 13 12 8 6 | 70 | 0 | 0.06 | 76 |
| tag | 1 | 5.082 ± 0.071 | 5 21 24 17 13 10 6 5 | 81 | 0 | 0.02 | 18 |
| **MicroAgent** | 1 | 4.967 ± 0.078 | 13 14 15 17 16 10 8 6 | 79 | 0 | 0.18 | 251 |
| pushfold | 1 | 4.909 ± 0.073 | 7 19 19 16 12 11 8 7 | 81 | 0 | 0.02 | 22 |
| loose_aggro | 1 | 4.583 ± 0.089 | 16 15 10 10 10 12 13 14 | 72 | 0 | 0.01 | 12 |
| montecarlo | 1 | 2.987 ± 0.068 | 1 3 6 9 15 21 25 21 | 98 | 0 | 22.51 | 2703 |
| montecarlo30 | 1 | 2.859 ± 0.076 | 3 4 6 8 10 14 23 32 | 95 | 0 | 10.27 | 2889 |

Mirror tests:

*8 rotations × 100 seeds (seed 31), 144,235 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| Hero | 1 | 4.901 ± 0.174 | 26 13 9 8 8 11 13 12 | 70 | 0 | 0.08 | 70 |
| **MicroAgent** | 7 | 4.443 ± 0.025 | 11 12 13 13 13 13 12 13 | 83 | 0 | 0.16 | 206 |

*8 rotations × 100 seeds (seed 32), 146,728 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| **MicroAgent** | 1 | 4.658 ± 0.130 | 8 12 19 17 15 10 9 10 | 86 | 0 | 0.42 | 292 |
| Hero | 7 | 4.477 ± 0.019 | 13 13 12 12 12 13 13 13 | 79 | 0 | 0.13 | 65 |

### poker-gym (MIT)

*300 seeds (seed 11), 55,987 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs | read |
|---|---|---|---|---|---|---|---|---|
| Hero | 1 | 5.158 ± 0.244 | 20 14 11 11 17 14 8 5 | 68 | 0 | 0.12 | 75 | ours (pinned at 5257118) |
| tag | 1 | 4.841 ± 0.208 | 2 16 24 20 16 9 7 7 | 85 | 0 | 0.01 | 18 | ours (bestiary ChartTAG) |
| ShortStackBot | 1 | 4.784 ± 0.235 | 10 17 14 14 15 14 10 7 | 80 | 0 | 0.13 | 101 | Nit profile (opens .07/.10/.17/.20), shoves ≤ 14 bb, reshoves 11% |
| IcmBot | 1 | 4.483 ± 0.264 | 13 13 12 11 11 14 13 13 | 76 | 0 | 0.19 | 141 | TAG + ICM risk premium ≤ .18 (exact ICM ≤ 5 players), given our payouts |
| TagBot | 1 | 4.339 ± 0.263 | 14 11 11 12 10 12 17 13 | 82 | 0 | 0.15 | 99 | Opens .11/.16/.27/.30 to 2.5 bb, push/fold ≤ 11 bb, c-bet 65%, calls at pot odds + .04 |
| AdaptiveBot | 1 | 4.311 ± 0.274 | 16 8 11 11 10 15 12 17 | 78 | 0 | 0.15 | 120 | TAG + VPIP/PFR/fold-to-steal tracker (steals more vs folders, bluffs less vs stations) |
| examples/my_bot | 1 | 4.245 ± 0.254 | 7 16 12 13 12 10 17 14 | 84 | 0 | 0.17 | 96 | examples/my_bot.py: percentile opens by position, shoves ≤ 12 bb at 1.8× width, calls shoves vs top 15% |
| LagBot | 1 | 3.840 ± 0.287 | 18 5 6 8 9 14 17 24 | 81 | 0 | 0.14 | 110 | Opens .20-.42 to 3 bb, 3-bet 9%, c-bet 85%, bluff 35% |

*8 rotations × 150 seeds (seed 12), 223,185 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| Hero | 1 | 5.243 ± 0.100 | 21 15 14 12 14 10 10 5 | 67 | 0 | 0.02 | 57 |
| tag | 1 | 4.801 ± 0.100 | 5 15 22 18 16 10 6 8 | 84 | 0 | 0.00 | 14 |
| ShortStackBot | 1 | 4.752 ± 0.105 | 11 16 13 15 14 12 9 10 | 78 | 0 | 0.03 | 68 |
| AdaptiveBot | 1 | 4.378 ± 0.111 | 15 10 10 11 12 15 13 13 | 78 | 0 | 0.02 | 81 |
| IcmBot | 1 | 4.376 ± 0.113 | 12 12 13 11 9 15 14 14 | 79 | 0 | 0.03 | 90 |
| examples/my_bot | 1 | 4.332 ± 0.110 | 6 15 12 14 13 13 12 14 | 83 | 0 | 0.03 | 73 |
| TagBot | 1 | 4.253 ± 0.104 | 12 11 10 12 12 13 15 15 | 81 | 0 | 0.03 | 75 |
| LagBot | 1 | 3.865 ± 0.129 | 18 6 6 6 10 11 20 22 | 79 | 0 | 0.02 | 76 |

Hero's margin over our own `tag` is thinnest here (0.32-0.44): seven competent TAG/nit variants make a
tight table. The fixtures CallBot, RandomBot and HeuristicBot were not seated.

### ela57/pokerbot (no license)

*300 seeds (seed 11), 53,942 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs | read |
|---|---|---|---|---|---|---|---|---|
| Hero | 1 | 6.231 ± 0.251 | 51 10 6 8 9 7 4 5 | 43 | 0 | 0.21 | 91 | ours (pinned at 5257118) |
| bots/my_bot | 1 | 5.122 ± 0.154 | 1 11 33 31 13 7 4 1 | 94 | 0 | 0.31 | 196 | bots/my_bot.py v2: opens only QQ+/AKs, folds AA to a raise; survives to 3rd-4th, almost never wins |
| tag | 1 | 5.064 ± 0.251 | 13 25 11 10 11 11 11 7 | 78 | 0 | 0.03 | 21 | ours (bestiary ChartTAG) |
| NitBot | 1 | 4.946 ± 0.197 | 2 18 25 18 15 11 7 4 | 88 | 0 | 0.38 | 222 | Percentile ranges 8/12/3 × position factor; postflop strength from hand category |
| EquityBot | 1 | 4.458 ± 0.263 | 14 14 7 12 14 13 17 10 | 77 | 0 | 1.19 | 1274 | 30/40/11 ranges; 30-sample eval7 Monte Carlo vs assumed ranges postflop |
| TAGBot | 1 | 3.796 ± 0.248 | 8 11 5 8 13 19 21 14 | 86 | 0 | 0.41 | 265 | 22/30/9, aggression .48, bluff .07 |
| ShortStackBot | 1 | 3.761 ± 0.240 | 6 8 11 8 16 19 15 18 | 90 | 0 | 0.45 | 288 | Shoves top 25% ≤ 15 bb; limps any hand when unraised (leak) |
| LAGBot | 1 | 2.622 ± 0.226 | 5 3 3 5 9 12 21 41 | 95 | 0 | 0.47 | 285 | 39/49/17, bluff .21, bets .82 pot |

CallingStationBot and ManiacBot were not seated (neither ever folds to a postflop bet; donors only).

### YosiefAbraham/pokerbot (no license)

*300 seeds (seed 11), 59,158 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs | read |
|---|---|---|---|---|---|---|---|---|
| Hero | 1 | 6.160 ± 0.263 | 49 17 7 4 4 5 7 7 | 30 | 0 | 0.03 | 70 | ours (pinned at 5257118) |
| tag | 1 | 4.705 ± 0.252 | 10 21 11 12 12 11 11 12 | 65 | 0 | 0.01 | 21 | ours (bestiary ChartTAG) |
| TightProfiler | 2 | 4.445 ± 0.139 | 5 8 17 18 19 16 12 6 | 77 | 0 | 1.01 | 1266 | TightProfiler: 22+/AT+ base by position, 4 bb opens, 3-bets QQ+/AK, set-mines, per-name VPIP/PFR/tilt profiler, 300-sample pure-Python equity calls (breaks 1 ms) |
| GTOBot | 2 | 4.402 ± 0.152 | 10 11 12 13 15 18 15 7 | 74 | 0 | 15.93 | 5532 | GTOBot: open fractions .12 (UTG) to .45 (BTN) at 2.5 bb, 150-sample equity bets .33-.75 pot (breaks 1 ms on 1 decision in 6) |
| STARTER | 2 | 3.720 ± 0.158 | 5 12 12 11 9 9 14 28 | 76 | 0 | 0.02 | 73 | STARTER: simple tight rules |

Both real bots are pure-Python Monte Carlo and break the 1 ms budget, so in strict mode some of their
postflop is played as check/fold. Their own dealer has no deadline. The adapter feeds `observe()` every
event, blinds included, and also covers hands our seat never acted in. 12-15 hands per bot (of about
59,000) were not fed because the button was not yet known: the seat's first hand ended before it acted.

### Best of each public repo at one table (Hero + tag + one seat each)

*8 rotations × 150 seeds (seed 41), 230,607 hands, strict.*

| bot | seats | pts ± 95% | p1..p8 % | bust % | exc | tmo % | p99 µs |
|---|---|---|---|---|---|---|---|
| Hero | 1 | 5.648 ± 0.135 | 37 16 10 6 7 7 9 9 | 49 | 0 | 0.14 | 77 |
| TightProfiler | 1 | 4.747 ± 0.093 | 4 11 20 20 19 14 7 4 | 81 | 0 | 2.05 | 6999 |
| tag | 1 | 4.733 ± 0.118 | 7 20 18 14 9 11 11 10 | 75 | 0 | 0.04 | 21 |
| **MicroAgent** | 1 | 4.680 ± 0.108 | 13 11 16 14 12 11 11 12 | 74 | 0 | 0.33 | 258 |
| ShortStackBot | 1 | 4.649 ± 0.128 | 18 19 8 8 8 11 14 15 | 67 | 0 | 0.16 | 98 |
| IcmBot | 1 | 4.455 ± 0.140 | 19 14 12 6 6 9 15 19 | 66 | 0 | 0.18 | 116 |
| bots/my_bot | 1 | 3.787 ± 0.079 | 0 2 8 23 29 21 10 8 | 98 | 0 | 0.21 | 140 |
| NitBot | 1 | 3.301 ± 0.099 | 3 7 8 10 12 16 22 23 | 91 | 0 | 0.23 | 171 |

In a mixed room TightProfiler, not MicroAgent, is the best public bot, despite its 2% timeouts. Hero
leads by 0.90.

### Not run

| repo | why |
|---|---|
| amalkoch/pokerbot-lab (no license) | No hold'em bot (Kuhn/Leduc only). The PokerBench preflop imitation model is not committed; using it needs a network download, a training run and a joblib pickle load |
| anaerobia/pokerbot (no license) | Heads-up only (`GameView` has scalar `opp_*` fields). An 8-max shim would merge all opponents into one and measure the shim |
| hanifnoerr/poker-challenge (no license) | Heads-up Kaggle-style `agent(obs, config)`. `tight_aggressive` is a two-rule bot; skipped |
| pokerbots-dev/pokerbots (no license file; CLI metadata says MIT) | Only a check/fold template and three one-formula house bots |
| GeorgeBarnes06/pokerbot | Rust; the bot files are one doc comment each and the runner prints a string |
| qbeka/No-Limit-…-simulations | Castle (Blotto) only, no poker |
| justmycode37/Pokerbot, AdarshPay/PokerBot | Empty |

## What MicroAgent does that Hero does not (for prioritising)

Read from its source (`agent.py`). None of this was copied.

- **ICM jam/fold at up to 20 bb, computed live.** First-in at an effective stack of 20 bb or less
  (`PUSHFOLD_MAX_BB = 20`), it compares the ICM value of folding against jamming. The jam value walks the
  players behind with solved per-position calling ranges (no-overcall model) and uses the real payout
  vector cut to the players left. Calling an all-in also uses ICM. Hero switches to push/fold only at
  10 bb (`pushfold.threshold_bb`) and gates pushes with a value curve, not exact ICM.
- **A solved multiway first-in table.** Chip-EV, players behind × 2-25 bb, regret matching. It is much
  tighter than Hero's `HU / (1 + 0.3 (k-1))` rule (see the cross-check below).
- **Postflop equity by Monte Carlo against ranges read from each opponent's line this hand**, in C++
  with a 100 µs budget calibrated at start-up (48-800 samples). It bets 0.66 pot at equity ≥ 1/(n+1) + .15
  and calls at pot odds plus a street margin. Heads-up rivers come from a CFR table.
- **No opponent model across hands** (no VPIP/PFR, no profiler). It does not punish stations or maniacs
  more than its ranges already do. Its weakness shows in the 1st-place rate: 10-13% in our top and realistic
  fields against Hero's 21-22%, with a bust rate of about 80%.

Implication: a team that downloads MicroAgent and brings it (MIT; whether prewritten code is allowed is
the organisers' call) sits just below our `tag` in our fields (0.12-0.14 behind), and level with Hero at a table of
weak bots. rival1 is still the stronger sparring partner. The cheapest lesson for Hero is the push/fold
band: solved multiway first-in ranges with ICM, possibly up to 15-20 bb, which is deep-pass task 3.

## microholdem push/fold cross-check (their solver output is not used; comparison only)

Their committed `pushfold_hu.npz` and `pushfold_multi.npz` were read as plain arrays
(`allow_pickle=False`; none of their code ran) and compared class by class (169 classes, jam frequency ≥
0.5 = push) with our `tables/pushfold_hu.json` and Hero's multiway base rule. The deep-pass agent has not
yet committed multiway tables, so there is nothing else of ours to compare.

- **Heads-up (SB vs BB), 2-25 bb: agree.** 0-3 of 169 classes differ per depth (30
  class disagreements across 24 depths, all borderline hands such as 43s, 84s, Q5s). Push frequencies are
  within 0.011 at every depth (10 bb: ours 0.578, theirs 0.584). Two independent heads-up Nash solves match.
- **Multiway first-in: disagree, systematically.** Hero's base rule `p_push[D] / (1 + 0.3 (k - 1))` (k =
  players behind) is much looser than their chip-EV multiway solve (regret matching, no-overcall model,
  symmetric stacks, no ante). **1,325 of 9,126 class
  decisions disagree (14.5%)** over k = 2..7
  and 2-10 bb, about 14% of combos per cell on average. Examples (ours/theirs push share): button (k=2) at
  10 bb 0.44/0.32; UTG (k=7) at 10 bb 0.21/0.11; UTG at 20 bb 0.14/0.05. They agree only at 2-3 bb.
  Matching their table needs a per-player divisor of about 0.7-0.8 at 10 bb, rising above 1 at 20 bb, not
  0.3. Hero's ICM/EV gate (`_push_ev_ok`) tightens after the range step, so Hero's real first-in ranges
  are somewhat tighter than the base rule, but this supports deep-pass task 3.

## What each repo assumes about the real kit (data for the adapter drills)

| | poker-gym | ela57 | microholdem | Yosief | others |
|---|---|---|---|---|---|
| Entry points | `reset(TableInfo)`, `act(obs) -> Action`; no hand-end hook | `on_table_start(TableStartInfo)`, `act(obs)`, `on_hand_end(PublicHandResult)` | `reset(seat, n_seats, seed)`, `act(obs)` | `new_hand(id, positions, hole)`, `observe(Event)` for every event incl. blinds, `act(GameState) -> tuple`, `end_hand(nets, shown, board)` | anaerobia `get_action(view)` (MIT style); hanif `agent(obs, config) -> dict`; pokerbots.dev `act(state: dict) -> tuple` |
| Cards | ints rank*4+suit, cdhs (same as ours) | strings `"As"`, suits order shdc | ints rank*4+suit, cdhs | strings `"As"` (also `"10h"`, `"A♠"`) | anaerobia `Card(rank 2..14, suit)`; hanif `"As"` |
| Raise amount | raise-to, street total | raise-to, street total (`min/max_raise_to` None when illegal) | raise-to, street total (0/0 when illegal) | raise-to, street total; their adapter has a TODO about raise-by | all raise-to; poker-gym's own fake kit drills raise-by |
| Pot | all chips this hand incl. current bets and antes | `pot_total` incl. current bets; `pot_breakdown` = collected pots only | incl. current bets | incl. current bets | |
| Per-seat money | `stacks` behind, `bets` street, `committed` hand | `seats[]` with `stack`, `bet_this_street`, `total_contributed`, `folded`, `all_in`, `active` (= not folded), `position` string, `anon_id` | `stacks`, `bets` (antes posted into bets) | dicts by player name | pokerbots.dev `stacks_start` |
| History | `(street, seat, kind 0-3, amount)`, no blinds; call amount = chips added, raise = to | `PublicAction(seat_anon, street, kind, amount)`, no blinds, amounts as poker-gym | same tuple as poker-gym | `Event(player, street, kind blind/fold/check/call/bet/raise, amount added, to, pot_before, to_call_before)` | |
| to_call | capped at stack | capped | capped | capped | pokerbots.dev uncapped |
| Tournament info | none in obs (payouts via `configure(rules)`) | `level` 0-based, `hand_number` 1-based, `hands_remaining`, `players_remaining`, `payouts` | `payouts` cut to live players, `hand_number` | none (cash game, rebuys) | |
| Payouts / blinds assumed | SYNTHETIC 100/60/40/25/15/10/5/0; 10/20 to 200/400 every 25 hands, no ante | same synthetic payouts and ladder, labelled ASSUMPTION | 50/30/20 in its simulator; 15/30 to 500/1000 | 50/100, 10k chips, rebuys | |
| Deadline | 1 ms in code (`docs` wrongly say 1,000 ms); `record` mode default | 1 ms soft (perf_counter) + 50 ms SIGALRM hard; hooks untimed | self-budget 1 ms, equity 100 µs | none (diagnostics aim at 50 ms) | pokerbots.dev 20 ms CPU / 100 ms wall; hanif 3 s |
| Fallback on error/timeout | check else fold | check else fold | fold, or check if free; clamp sizes | fold/check; clamp sizes | |

Traps worth adding to the fake kits: string cards with suit order `shdc` (ela57), a `can_fold` that is
False when a check is free (PokerKit), `min_raise_to`/`max_raise_to` = None or 0 when raising is illegal,
`active` meaning "not folded" rather than "alive", blinds present in history (Yosief) or absent (the
rest), players keyed by name or anon id instead of seat, `payouts` cut to the players left, and a 1-based
`hand_number` next to a 0-based `level`.

## Safety review

Every Python file in every repo was read before anything ran (four parallel readers plus my own grep). The
bots were run with `python -I -B` from our scratch scripts directory, in a throwaway venv per repo, with
their paths passed as arguments. No interpreter was started inside their directories, and `git status`
in each clone was clean after the runs.

| repo | license | verdict | notes |
|---|---|---|---|
| mack-dot/poker-gym | MIT | bots SAFE TO IMPORT | **Refused: `pokergym/arena/*`.** `isolation.py`'s self-test opens a socket to 1.1.1.1:53, and on Linux/WSL there is no sandbox, so it really connects. `arena/__main__.py cmd_smoke` runs `rmtree` on any existing `--root`. `session.py` copies arbitrary paths named in inbox requests. `validate_runner.py` installs SIGALRM handlers. Also not run: `scripts/gen_preflop_equity.py` (overwrites their data), benchmarks, tests (subprocess). Only `pokergym.agent`, `pokergym.bots`, `pokergym.equity` and `examples/my_bot.py` were imported |
| ela57/pokerbot | none | bots SAFE TO IMPORT | Not run: `bots/roster.py` file loader (`exec_module` of a path), `timing.py` (SIGALRM/setitimer), `logging_store.py` (`git rev-parse` subprocess, SQLite and gzip writes under `runs/`), `batch.py` (multiprocessing spawn), `cli.py`. `pokerpractice.engine` was pre-registered as a bare package so `engine/base.py` loads without PokerKit. Dependency `eval7==0.1.11` from PyPI |
| ryankkhalil19/microholdem | MIT | SAFE once `_core` is compiled by us | No network, eval, pickle, env, threads, ctypes. `_core.cpp` includes only pybind11 and STL headers. **We compiled `_core.cpp` ourselves** with `c++ -O3 -shared -fPIC $(python -m pybind11 --includes)` into scratch. Their `setup.py` was never run. Not run: `bench.py` (subprocess, global GC toggles, writes `./bench`), `tables build` (overwrites shipped tables). `.npy/.npz` loaded with `allow_pickle=False`; all dtypes numeric or short strings |
| amalkoch/pokerbot-lab | none | nothing run | `audit_pluribus.py`/`validate_uci.py`/`audit_pokerbench.py --download` download datasets; `train_preflop.py` writes a joblib pickle |
| YosiefAbraham/pokerbot | none | `bot`, `gto`, `protocol`, `ranges`, `cards`, `strategy`, `profiles` SAFE | Not imported: `bots/__init__.py` (imports every `bots/*.py` at import time, non-obvious; `bots/starter.py` was loaded by path instead), `dashboard.py` (HTTP server, process pool), `diagnostics.py` (subprocess pytest, urllib to localhost), `adapter.py` (stdin loop) |
| anaerobia, hanifnoerr | none | not run (heads-up only) | hanif `script_worker.py` uses `runpy.run_path` on an argument, and `submissions.py` uses subprocess. Both are obvious-purpose |
| pokerbots-dev/pokerbots | none | not run | **Refused: `cli/src/pokerbots_cli/host.py`** runs at import (`sys.path.insert(0, ".")`, `from bot import Bot` from the current directory, stdin loop). `api.py`, `auth.py` and `wallet.py` read env credentials, call GitHub and Cloudflare, write `~/.config/pokerbots/credentials.json`, and write a Solana private key. `runner/server.py` runs `mount` and serves on 0.0.0.0 |
| qbeka | none | not run | `reference/originals/castle_fourway.py` does `ctypes.CDLL('/workspace/scratch/.../castle_eval.so')` at import and module-level writes to absolute paths |

## Method

- Harness: our own scratch script. It builds each field from bot factories and calls
  `hyperion.sim.engine.play_table(..., mode="strict")` directly, with the default `Rules()` (2,000 chips,
  10/20 to 200/400 every 25 hands, 200-hand cap, payouts 8..1). `bestiary.py` was not modified. The
  seating is shuffled per table seed. The sample unit is one table seed (the average of a name's seats, and
  of the 8 rotations when rotated).
- Our adapters are written from scratch. Our `Observation` has no street markers in its history, so a
  shared scratch helper replays each hand from the history with our engine's betting rules to recover the
  per-street history and per-hand contributions their interfaces want. It was verified against our engine
  with zero mismatches over 14,134 decisions, including maniac and all-in bots, and it raised zero
  mismatches in every run here.
- Hero is pinned: `git archive 5257118` of this repo into scratch, passed to the harness as the hyperion
  path. Every run logs which hyperion it imported and checks that the real `hyperion.strategy.hero.Hero`
  loaded (not the bestiary's ChartTAG fallback).
- Each bot was given our payout vector where its interface takes one (poker-gym `payouts`, ela57
  `payouts`, microholdem `payouts` cut to the players left), as a competitor would once the payouts are
  announced. poker-gym's equity JSON was pre-warmed at import, as its own notes advise.
- MicroAgent calibrates its Monte Carlo sample counts by timing its C++ call at construction, so runs are
  not bit-reproducible. The kept adapter (`hyperion/sim/rivals/microholdem.py`) was checked against the
  scratch adapter by building both observations on every decision of 30 tables: 0 field differences over
  13,799 decisions.

## Scratch artifacts (not in the repo)

Under `/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/`:
`publicrepos/<owner_repo>/` (the clones, still clean per `git status --ignored`), `venvs/<name>/` (one
throwaway venv per repo, plus `mixed` for the best-of field), `mh_build/` (our build of microholdem's
`_core`), `hyperion_pinned/` (Hero at 5257118), and `scripts/spar/`, which holds the harness `spar.py`, the
replay helper `ourobs.py`, the adapters `adapt_{pokergym,microholdem,ela57,yosief}.py`,
`pf_crosscheck.py`, and every result as `out/P_*.json` and `out/P_*.txt`.

To rerun one field: `venvs/microholdem/bin/python -I -B scripts/spar/spar.py --hyperion <hyperion>
--adapter scripts/spar/adapt_microholdem.py --repo publicrepos/ryankkhalil19_microholdem --rotate --roster
hero,tag,mh_micro,h:rival1,h:pushfold,h:loose_aggro,h:montecarlo30,h:hero_tight --tables 300 --seed 13
--out x.json`.
