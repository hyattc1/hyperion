# S12: reading opponents faster and punishing them (running log)

Branch `climb/s12-reads` from main 5c6af66. The owner's question: an 8-max sit-and-go gives 100-300 hands with each
opponent; bots are consistent; are we getting everything we can out of reading and punishing them within 1 ms?

Rules kept: no judge, outside, elite3 / elite_judge or held-out variant was run, read or profiled. Screen seeds
10000-10199 only for decisions; recording and survey seeds 8000-8049 (fresh, under 10000, not listed as used in
goal-plan). Model mode, eight rotations per seed, F as hyperion.ship builds it (`{"dials": {}}` on top of SHIP_DIALS).
Host shared at load 14-19 (8 cores): `--workers 2` under `nice -n 10`, at most two measurement processes.

Scratch tools (session scratchpad `goal/s12/`, measuring devices, never shipped):
- `warmlib.py`, `rec.py`: F's per-seat read state from its three stores (the front exploit layer; Hero's profiler in
  the hero member, which plays postflop; rival 3's core reads in the base, which plays preflop; plus the base's
  fallback Hero's profiler), extracted at every table end and summed per opponent identity (the bot, not the seat:
  night seats resolve to the drawn bot); and snapshots of every read at hands 5..199 of each table.
- `warm_accept.py`: tools/climb_accept.py with `{"bot": "warmf"}`, F whose per-seat state is loaded at table start
  from the recording for (field, payouts) against the same identity (warm reads). Counts summed over the whole
  recording; the layer's decayed fold reads at its full weight (1/(1-decay)) with the long-run rate; a seat that never
  called or raised in the long run starts with a dead streak.
- `settle.py`: snapshots against the long-run value.
- `survey.py`, `survey_report.py`: every decision of every seat with its hole cards (the simulator's truth), per
  identity: bet size against tier, facing bets by size, check-raises, c-bets by texture, opens by position, steals,
  3-bets.
- `oracle.py`: `{"bot": "orcf"}`, the composite with a candidate's dials and one read's true answer installed per
  identity (from the survey).

## 06:40-06:52: the recordings (seeds 8000-8049 x 8 rotations, F in the hero seat)

One recording per field and payout table (`rec.py`, 400 tables each). Hands F saw per opponent identity:

| recording | F points | identities | fewest hands (who) | median |
|---|---|---|---|---|
| night 8..1 | 6.194 | 24 | 289 (random) | 10,320 |
| realistic 8..1 | 6.329 | 7 | 23,919 (montecarlo30) | 35,486 |
| night_hard 8..1 | 5.495 | 20 | 152 (maniac) | 12,862 |
| top 8..1 | 5.062 | 6 | 33,591 (loose_aggro) | 42,086 |
| elite 8..1 | 4.731 | 7 | 37,264 (agent_default) | 38,650 |
| night 50/25/12/6/3/2/1/1 | 26.466 | 24 | 166 (allin) | 9,937 |
| realistic th | 28.066 | 7 | 22,272 | 33,728 |
| night_hard th | 19.568 | 20 | 140 (maniac) | 12,246 |
| top th | 15.672 | 6 | 31,371 | 38,295 |
| elite th | 14.028 | 7 | 35,003 | 36,353 |

Every identity but the four that bust at once (maniac, random, allin, station: 140-650 hands) has thousands of hands:
the warm profile is the long-run truth for the bots F actually meets.

## How fast F's reads settle (`settle.py`, the 8..1 recordings' snapshots, 2,000 tables)

Mean |read - long-run value| at hands 10 / 30 / 100 / 199 of a table, by opponent group (flags: share of tables where
the flag differs from the long-run flag). "Long-run" is the whole recording loaded at full weight.

| read | agent builds | weak or broken | decent | strong (rivals) | elite |
|---|---|---|---|---|---|
| VPIP (Hero's profiler) | 0.08/0.06/0.04/0.04 | 0.12/0.10/0.08/0.08 | 0.08/0.06/0.04/0.04 | 0.10/0.07/0.05/0.05 | 0.09/0.06/0.05/0.05 |
| PFR | 0.08/0.05/0.04/0.04 | 0.06/0.05/0.04/0.04 | 0.07/0.05/0.04/0.04 | 0.10/0.07/0.05/0.05 | 0.08/0.06/0.04/0.04 |
| fold to a preflop raise | 0.11/0.08/0.05/0.06 | 0.15/0.12/0.11/0.10 | 0.15/0.10/0.07/0.05 | 0.13/0.09/0.06/0.06 | 0.14/0.10/0.06/0.07 |
| fold to a postflop bet | 0.14/0.15/0.13/0.12 | 0.16/0.15/0.13/0.12 | 0.14/0.15/0.15/0.14 | 0.12/0.14/0.12/0.11 | 0.13/0.14/0.12/0.10 |
| postflop aggression | 0.17/0.14/0.09/0.09 | 0.14/0.11/0.09/0.09 | 0.13/0.14/0.12/0.11 | 0.14/0.12/0.08/0.07 | 0.14/0.11/0.09/0.10 |
| bets when checked to | 0.11/0.12/0.10/0.10 | 0.14/0.12/0.10/0.10 | 0.15/0.14/0.12/0.12 | 0.09/0.11/0.09/0.08 | 0.10/0.11/0.10/0.10 |
| fold to a c-bet | 0.21/0.20/0.18/0.17 | 0.10/0.11/0.11/0.11 | 0.30/0.29/0.25/0.24 | 0.13/0.13/0.12/0.11 | 0.12/0.12/0.12/0.11 |
| late open rate | 0.13/0.13/0.10/0.11 | 0.20/0.16/0.12/0.12 | 0.11/0.11/0.09/0.09 | 0.23/0.19/0.12/0.11 | 0.18/0.16/0.12/0.12 |
| calls a shove | 0.07/0.08/0.11/0.11 | 0.18/0.18/0.17/0.17 | 0.11/0.12/0.12/0.10 | 0.13/0.13/0.09/0.09 | 0.06/0.07/0.10/0.10 |
| layer: fold to a preflop raise | 0.08/0.09/0.08/0.08 | 0.11/0.10/0.10/0.09 | 0.08/0.07/0.08/0.07 | 0.09/0.08/0.08/0.08 | 0.09/0.08/0.09/0.09 |
| layer: fold postflop heads-up | 0.16/0.18/0.17/0.15 | 0.18/0.17/0.15/0.16 | 0.18/0.19/0.19/0.18 | 0.16/0.19/0.16/0.14 | 0.17/0.18/0.15/0.14 |
| rival 3: fold to a raise | 0.11/0.07/0.05/0.05 | 0.14/0.12/0.10/0.10 | 0.14/0.10/0.06/0.05 | 0.11/0.08/0.06/0.06 | 0.12/0.09/0.06/0.06 |
| rival 3: fold to a bet | 0.14/0.13/0.12/0.11 | 0.13/0.12/0.11/0.11 | 0.18/0.16/0.14/0.12 | 0.11/0.11/0.11/0.09 | 0.15/0.13/0.11/0.09 |
| archetype flag (share wrong) | 0.10/0.27/0.12/0.08 | 0.10/0.11/0.09/0.10 | 0.45/0.29/0.20/0.20 | 0.04/0.11/0.04/0.03 | 0.03/0.11/0.03/0.02 |

Read:
- **Preflop frequencies settle in 60-100 hands** (within 0.05 of the long run): VPIP, PFR, fold to a raise. These are
  the reads rival 3's core and the layer price steals with, and they are as good by mid-table as they will get.
- **Postflop reads never settle inside a table.** Fold to a postflop bet, fold to a c-bet, aggression and bets when
  checked to are still 0.10-0.24 off at hand 199: a seat faces only 10-20 postflop bets from anyone in a table, and
  the c-bet read only counts heads-up flops after a raise. No prior change fixes that; only a read that pools more
  spots (or a population prior that is already right) can.
- **The layer's decayed reads plateau by design** (memory about seven spots, for seats that break mid-table): 0.08
  preflop, 0.15 postflop, from hand 10 on.
- **The archetype flag misfires early**: at hand 30 it is wrong at 27% of agent-build tables and 29% of decent ones,
  mostly a false `nit` once 20 hands pass with a low VPIP (tight bots that are not nits) and `unknown` for TAGs that
  are nits in the long run. It recovers by hand 100.

## 06:56-07:06: what the opponents leak (`survey.py`, seeds 8000-8024 x 8, night, realistic, night_hard, top, elite)

Every decision of every seat with its hole cards, F in the hero seat, 1,000 tables. Tier = Hero's postflop strength
read (0 nothing ... 4 top pair good kicker / overpair, 5 two pair, 6 set / straight, 7 flush / full house). The full
tables are in the session scratchpad (`goal/s12/res/survey_lin.md`); the leaks that matter:

**1. Bet size names the hand.** Share of a seat's postflop bets at each size (of the pot before the bet), the mean
tier of the hands it bet, and the share of air (tier 0-1):

| bettor | 0.4-0.6 pot | 0.6-0.85 pot | 0.85-1.2 pot |
|---|---|---|---|
| rival1 | 40% of bets, tier 1.1, **65% air** | 55%, tier 4.1, 7% air | |
| rival3 | 54%, tier 1.6, **52% air** | 43%, tier 4.4, 0% air | |
| rival2 | 64%, tier 2.0, 38% air | 26%, tier 4.3, 0% air | 6%, tier 5.6 |
| pushfold | 32%, tier 1.4, **61% air** | 64%, tier 3.9, 2% air | |
| agent_charts | 40%, tier 2.4, 40% air | 53%, tier 4.6, 1% air | |
| agent_default | 50%, tier 2.6, 27% air | 43%, tier 4.0, 7% air | |
| agent_pushfold | 62%, tier 3.2, 12% air | 31%, tier 5.0 (60% two pair+), 0% air | |
| elite1 | 60%, tier 2.2, 33% air | 31%, tier 4.3, 6% air | 6%, tier 5.5 (77% two pair+) |
| elite2 (balanced) | 37%, tier 2.5, 23% air | 29%, tier 1.9, **50% air** | 14%, tier 4.9 |
| F itself | (0.33: 57% of bets, 61% air) 26%, tier 3.6 | 16%, tier 4.9 | |
| one size only | tag, loose_aggro, naive, timeout bots (0.4-0.6); montecarlo, montecarlo30, trackb3/5 (0.6-0.85) | | |

F answers every bet by pot odds plus a margin (0.2; 0.05 against a c-bet): it folds 72-75% to bets of 0.4 pot or
less, so it folds middle pair to half-pot bets that are 50-65% air from five of the eight strongest seats it meets,
and calls top pair against 0.75-pot bets that carry no air.

**2. Nobody check-raises, and a checked range holds no strong hands.** Raise share when a seat checked and then faced
a bet on the same street: 0-1% for every seat but montecarlo / montecarlo30 (5-7%) and maniac. The flop checking range
of every seat but the station, maniac and timeout bots has mean tier 0.8-1.6 and 0-2% two pair or better.

**3. Openers fold to 3-bets.** An opener's first answer to a 3-bet: fold rival3 89%, agent_pushfold 86%, trackb5
86%, rival1 83%, tag 78%, hero_tight 77%, trackb3 72%, agent_charts 72%, elite2 70%, rival2 67%; elite1 43%,
agent_montecarlo 47%; the limping Monte Carlo bots never fold. F 3-bets an open 7% of the time (rival 3's core: value
only).

**4. Rivals call rivers light.** Share of river calls made with tier 2 or less (middle pair or worse): rival1 56%,
rival3 55%, rival2 52%, agent_charts 51%; the Monte Carlo bots 77-94%. Thin river value gets paid by most seats.

**5. Smaller leaks:** fold to a c-bet barely depends on texture (dry vs wet within 5-10 points for most seats); opens
by position vary (trackb5 opens the button 65%, the small blind 29%), but the blinds' folds to a steal are already in
the layer's and rival 3's fold reads (61-95%).

Already read by F: fold to a raise (preflop steals), fold to a bet (the layer's bet-when-checked, rival 3's bluffs),
fold to a c-bet (Hero's c-bet read is off: `cbet_ftc_read` False), an opener's fold to a re-raise (Hero's re-shove
only, short stacks), shove and call-shove rates. Not read at all: bet size against strength, check-raise frequency,
fold to a 3-bet at depth (only for re-shoves), river call ranges.

## 07:00-07:30: a measurement accident (fixed): editing the code while a run was going

The first lin ceiling ran from the live worktree while I added the dials. Pool workers forked after the edit loaded
the new rival 3 core next to the main process's old dials class (`'Rival3Knobs' object has no attribute 'l3_on'` at
every hand end, ~27,000 SafeBot errors a chunk) and played F badly in both specs. Every chunk with an error was
deleted (40 of 78; every valid chunk has 0); all later runs go from a detached worktree at the measured commit
(`goal/wt_s12m` at 0db5695), as the coordinator does. F's play at 0db5695 equals F at 5c6af66 sample for sample
(night 10000-10024 x 8 checked), so its cached chunks were copied across code versions.

## 07:10-07:40: the ceiling, warm reads against cold (screen seeds 10000-10099 x 8)

`warm_accept.py`, `{"bot": "warmf", "warm": "full"}` against F, paired. 100 seeds (the host's load made 200 x 8 over
ten cells about four hours); the intervals are therefore about ±0.15 (8..1) and ±1.6-2.4 (of 100, top-heavy).

| field | 8..1: warm - cold | 50/25/12/6/3/2/1/1: warm - cold |
|---|---|---|
| night | +0.042 ± 0.144 | +1.110 ± 1.722 |
| realistic | **+0.181 ± 0.148** | **+2.108 ± 1.564** |
| night_hard | +0.022 ± 0.155 | +0.288 ± 1.587 |
| top | +0.021 ± 0.143 | +0.491 ± 1.556 |
| elite | **-0.236 ± 0.161** | -0.282 ± 1.332 |

Read: **reading faster with today's reads is worth little, and loses at the strongest table.** Perfect long-run
knowledge of every per-seat stat F keeps, from hand 0, gains beyond noise only on realistic (a weak-heavy room: two
Monte Carlo bots that time out, a bot that breaks, a loose student) and is level on night. At the elite table it is
beyond noise down: F's responses to its reads (archetype dials, steals by fold reads, call-down dials) are sized for
weak seats, and acting on them at full strength from the first hand costs against prepared bots, as `dead_seats`
did in F1 (-0.160 at elite). The value is not in reading sooner but in reading what F does not read yet.

## 07:00-07:10: three candidate reads, each a dial, off by default (0db5695)

- **`hero.postflop.size_read`** (Hero's postflop, which plays every postflop decision of F): facing a single bet heads-up
  (or a raise of my bet), the bettor's range for a bet of that size is a tier histogram: a prior worth
  `size_read_n0` (8) bets plus the bettor's own bets of that size whose cards were shown (counted at hand end from the
  showdown, `Profiler._size_end`). Equity against it is a tier race (a higher tier wins 0.78 / 0.86 / 0.97 of the
  time on the flop / turn / river, an equal tier splits). The call decision blends F's own (proxy equity - margin
  against pot odds) with this one (read equity - 0.03) at weight `size_read`. Size buckets of the pot before the bet:
  under 0.4, 0.4-0.6, 0.6-0.85, 0.85-1.2, over 1.2 (all-ins included), and a raise. Prior (`SIZE_PRIOR`): the survey's
  population histogram per street and bucket.
- **`hero.postflop.xr_shift`**: heads-up, nothing to call, the opponent checked to me this street and its check-raise
  rate (prior 0.02 worth 10 chances) is at most 0.04: value-bet `xr_shift` tiers thinner.
- **`r3.l3_on`** (rival 3's core, which plays F's preflop): facing one open and no caller, at least 25 bb deep, with a
  hand inside rival 3's top 35%: 3-bet to 3x + 1 bb when the opener's read fold-to-3-bet (prior 0.6 worth 6 3-bets;
  `o3_scan` counts every opener's reply to any 3-bet) is at least 0.65 and f x (the pot) > (1 - f) x 0.75 x (the
  raise), f including the folds of the seats behind (rival 3's own fold reads).

Counters only when a dial reads them (`Profiler.track_s12`), so F as shipped pays nothing; tests in
tests/test_s12_reads.py (each dial reaches decisions; counters count; off counts nothing; a table replays exactly).

## 07:20-07:45: oracle tests (screen seeds 10000-10099 x 8; F's cells shared)

`oracle.py`: the candidate's dials with that read's true answer per opponent identity installed at table start (from
the survey's simulator truth, every bet with its cards, not just showdowns). "Learned" is the same dial reading as it
ships. cand - F, paired:

| read | dials | night | top | elite |
|---|---|---|---|---|
| bet size against strength, **oracle** | size_read 1.0 | +0.102 ± 0.132 | **+0.228 ± 0.153** | **+0.280 ± 0.168** |
| bet size, learned (population prior per size + showdowns) | size_read 1.0 | -0.027 ± 0.116 | -0.113 ± 0.206 (50 seeds) | (stopped) |
| fold to a 3-bet, **oracle** (light 3-bets) | l3_on | +0.058 ± 0.093 | +0.084 ± 0.141 | +0.023 ± 0.121 |
| check-raise rate, learned (no oracle needed: 0-1% for nearly every seat) | xr_shift 1 | +0.016 ± 0.061 | (running) | |

Read: **the bet-size read is the one worth points**: with the true size-to-strength map per bot it gains beyond noise
at both strong tables, where the rivals and the elite builds bet two sizes that name their hand. A population map
per size does not hold online: one-size bots (tag, loose_aggro, the Monte Carlo bots) and two-size bots share no
histogram, and showdowns come too slowly to tell them apart (a seat shows down a handful of its bets a table). Next:
learn the map from what is always visible, the seat's own bet-size shares (`size_read_rank`).

## 07:40-07:55: why warm reads lose at the elite table (one store warm at a time, elite, 100 x 8)

| warm store | warm - cold |
|---|---|
| all four (above) | **-0.236 ± 0.161** |
| Hero's profilers only (archetype and call-down / bluff / steal dials; postflop) | +0.022 ± 0.095 |
| the front exploit layer only (steal by fold reads, bet when checked to) | -0.054 ± 0.119 |
| rival 3's core reads only (preflop: steal fold equity, opens against 3-bettors, VPIP/PFR ranges) | -0.112 ± 0.169 |

The loss is in the preflop reads: rival 3's core and the layer act on fold and 3-bet rates measured over whole
tables (where the elite builds have adapted to F) from the first hand, and steal and open into bots that defend.
Hero's postflop dials are neutral. So "read faster" is not the lever at strong tables; if anything F's preflop
reads should wait longer there (consistent with F1's `dead_seats` at elite, -0.160).

## 07:45-07:55: learning the size map online

The learned read with the population's map per size did not hold (above). Two learners from bet sizes alone
(always visible, unlike showdowns), each a slice of a population tier distribution:
- **A (`size_read_rank`)**: a seat's bet of size b is the slice of the population's *betting* range (weakest first)
  that its smaller sizes leave below, as wide as its share of bets of size b (shares shrunk toward the population's
  with 5 bets; pooled over streets, or per street with `size_read_rank_by_street`). A two-size bot's small bets read
  as its weak bets; a one-size bot reads as the whole betting range.
- B (offline only): the top r of the street's whole hand distribution, r the seat's bet-when-checked-to rate.

Offline against every bot's true map (`fitrank.py`, the survey's truth; mean |eq - true eq| over tiers 2-4, weighted
by bets): flop: population map 0.064, A pooled 0.054, A by street 0.048, B 0.076; turn: 0.083 / 0.098 / 0.120 /
0.108; river: 0.117 / 0.192 / 0.182 / 0.187. A wins on the flop (c-bets: rival 1-3, pushfold, tag, the Monte Carlo
bots), the population map on later streets (where rivals' small bets are value). B is out.

**Learned, A pooled (`size_read` 1.0, `size_read_rank` 5), screen 10000-10099 x 8:** night +0.025 ± 0.129, top
+0.115 ± 0.155, **elite +0.230 ± 0.146** (beyond noise up). Most of the oracle's gain at the elite table (+0.28),
half of it at top (+0.23), a quarter on night (+0.10). This is the candidate (C1); the flop-only hybrid (A by street
on the flop, the population map later: `size_read_rank_streets` 1, `size_read_rank_by_street`) fits the truth
better offline but was not measured (no compute left for it).

## 08:00: the blend (C2) and the overlap with S11

Offline by opponent group (mean |eq error|; `fitrank.py`): night-type bots (agent builds, Track B, Monte Carlo, the
decent archetypes) population map 0.076, A pooled (C1) **0.100**, A by street on the flop only 0.074, half A pooled
and half the population map 0.074; strong bots (rivals, elite builds, hero_tight) 0.074 / 0.064 / 0.056 / **0.052**.
C1's rank slice is worse than the population map against the agent and Track B builds (their small bets are not
their weak bets), which is where night's level result comes from. `size_read_rank_mix` 0.5 (4260f66) blends the two
priors; C2 = C1 + mix 0.5 is measured on night, top and elite after C1's screens.

**Overlap with S11** (climb/s11-exploiter2-fixes, read only): S11's wide-bettor read (probe / c-bet / free-bet rates)
edits the same facing-a-bet block of `Postflop.act` (eq, margin, a lower raise tier, a probe bluff-raise) and
PostflopParams. A textual conflict at the raise check is likely; the resolution keeps S11's block first, then the
size read's block, then F's call rule. With both on, the size read blends against F's decision with S11's eq and
margin (weight 1 - size_read), so at size_read 1.0 it overrides S11's call margin; the pair must be measured together.

## 07:55-08:45: C1's screens (code 36818ca, screen seeds 10000-10199 x 8)

C1 = `{"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0}`. climb_accept stages confirm, guards,
elite, exploit (`warm_accept.py` passes dials specs straight to tools/climb_accept.py; F's chunks shared):

| cell | F | C1 | C1 - F | |
|---|---|---|---|---|
| night | 5.973 | 5.947 | -0.026 ± 0.089 | level |
| night_hard | 5.485 | 5.562 | +0.077 ± 0.106 | level |
| realistic | 6.346 | 6.351 | +0.004 ± 0.087 | level |
| top | 5.035 | 5.143 | **+0.108 ± 0.107** | UP |
| night @10/7/5/4/3/2/1/0 | 6.159 | 6.244 | +0.085 ± 0.154 | level |
| night @50/25/12/6/3/2/1/1 | 24.443 | 24.549 | +0.106 ± 0.949 | level |
| night, doubling blinds | 5.828 | 5.778 | -0.050 ± 0.085 | level |
| elite | 4.681 | 4.959 | **+0.277 ± 0.105** | UP |
| elite_night | 5.329 | 5.556 | **+0.227 ± 0.098** | UP |
| exploit (8-max, exploiter1) | 4.999 | 4.962 | -0.037 ± 0.146 | level |
| exploit_hu | 8.005 | 7.720 | **-0.285 ± 0.146** | DOWN |
| exploit_3 | 7.027 | 6.743 | **-0.283 ± 0.153** | DOWN |

Read: C1 gains at every strong table (top, elite, elite_night) and is level on night and the weak-heavy rooms, but it
**loses exploit resistance short-handed**: exploiter 1 heads-up and three-handed takes 0.28 more off it. Why
(`flips.py` on exploit_hu, 20 x 2 tables, the read against F's own rule on the same spots): (1) facing bets under
0.4 pot the read calls 142 times with tier 0 (no pair, no draw) where F folds: equal tiers split in the tier race,
and against a range that is two thirds air an unpaired hand "splits" too often; (2) exploiter 1 bets three sizes,
the two smaller both mostly air (0.4-0.6 pot: 54% air), and the rank slice reads its middle size as medium-strong, so
the read folds tier 2-3 hands there that F called (57 + 45 spots). Fixes, both dials (c56d1e2): the blend with the
population map (`size_read_rank_mix` 0.5: the population's 0.4-0.6 bets are 43% air) and a floor (`size_read_call_tier`
2: the read turns a fold into a call only with a pair or better). C3 = C1 + both.

C1's variant subset (realistic under each entry, screen 10000-10099 x 8): bounty -0.092 ± 0.134, auction -0.106 ±
0.128, river_of_blood -0.054 ± 0.131, top_heavy +0.699 ± 1.459 (of 100): all level, three point estimates negative.

## 08:40-08:57: C3 (C1 + blend 0.5 + call floor tier 2; code c56d1e2), screen 10000-10099 x 8

| cell | C3 - F | C1 - F on the same 100 seeds |
|---|---|---|
| night | +0.027 ± 0.107 | +0.025 ± 0.129 |
| top | +0.016 ± 0.132 | +0.115 ± 0.155 |
| elite | +0.117 ± 0.133 | +0.230 ± 0.146 |
| exploit (8-max) | -0.024 ± 0.191 | |
| exploit_3 | -0.150 ± 0.214 | (200 seeds: -0.283) |
| exploit_hu | -0.105 ± 0.206 | (200 seeds: -0.285) |

The blend and the floor halve the short-handed loss to exploiter 1 and halve the strong-table gain with it: the same
calls that win against the rivals' air-heavy small bets are the ones a bot that bets small for value punishes.

## 08:57-09:05: C4 (floor only) and C6 (the read off short-handed), screen 10000-10099 x 8

| cell | C4 = C1 + `size_read_call_tier` 2 | C6 = C1 + `size_read_min_alive` 4 (e34942b) |
|---|---|---|
| night | | +0.013 ± 0.126 |
| top | | +0.114 ± 0.157 |
| elite | +0.080 ± 0.131 | +0.203 ± 0.146 |
| exploit (8-max) | -0.093 ± 0.180 | (below, 200 seeds) |
| exploit_3 | **-0.297 ± 0.209** | identical to F by construction (three alive: the read is off) |
| exploit_hu | **-0.330 ± 0.194** | identical to F by construction |

The floor alone fixes nothing (the tier-0 calls were not the short-handed leak; the blend's shift on the middle size
was what helped C3) and costs the elite gain. The gate keeps C1's strong-table gains (top +0.114 against C1's
+0.115, elite +0.203 against +0.230 on the same seeds): those gains are made at seven- to four-handed tables against
bots whose sizes follow the population, which is also where the read is right; heads-up and three-handed, ranges
widen and a bot built against us sizes its own way. **C6 is the candidate**; its screens follow at 200 x 8.

Full test suite (wt_s12 at 4260f66, load 13-18): 24 failed, 1,021 passed, 7 skipped (35 min). Re-run alone: the
`replay exactly in model mode` tests of the outside, elite and exploit fields, `test_random_pick_is_seeded`,
`test_auto_drill_hits_every_checkpoint[toss_or_holdem-c]`, slowbox timing and the pack's import-time row still fail;
the same replay tests and `test_random_pick_is_seeded` fail on the base commit 5c6af66 under the same load (plain
Hero's SafeBot reads the wall clock in those tests), so they are the host, not S12. `test_contracts_md_is_current`
was real: the API card is regenerated with the new dials (e34942b).
