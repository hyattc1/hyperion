# S12: reading opponents faster and punishing them (running log)

Branch `climb/s12-reads` from main 5c6af66. The owner's question: an 8-max sit-and-go gives 100-300 hands with each
opponent; bots are consistent; are we getting everything we can out of reading and punishing them within 1 ms?

**Summary.** (1) The ceiling: F's existing reads, known perfectly from hand 0 (warm, from 400-table recordings),
are worth little: night +0.04 ± 0.14, realistic +0.18 ± 0.15 (up), night_hard and top level, and elite -0.24 ± 0.16
(down) at 8..1; the same pattern at 50/25/12/6/3/2/1/1. Preflop reads settle in 60-100 hands; postflop reads never
settle inside a table. Reading faster is not the lever. (2) What F does not read: bet size against strength is worth
the most (oracle: night +0.10, top +0.23 up, elite +0.28 up); light 3-bets against folding openers +0.02 to +0.08;
thin value against non-check-raisers nothing. (3) Built: a size read learned from each seat's bet-size shares, off
heads-up / three-handed and on twist tables (C7). Screen: elite +0.256 ± 0.105, elite_night +0.227 ± 0.096 (both up),
top +0.103, night -0.031, every guard level, exploit resistance unchanged, latency +2 µs a decision. Recommended for
held-out confirmation under addendum 8.

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
| check-raise rate, learned (no oracle needed: 0-1% for nearly every seat) | xr_shift 1 | +0.016 ± 0.061 | -0.020 ± 0.047 | -0.030 ± 0.057 |

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
priors. C2 = C1 + mix 0.5 was not measured alone: after C1's exploit screen it became C3 (the blend and a call floor).

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

## 09:20-09:30: C7 = C6 + the read off on twist tables (de6875e)

C6's variant subset (realistic under each entry, 10000-10099 x 8): bounty -0.100 ± 0.131, toss_or_holdem -0.067 ±
0.078, short_deck +0.041 ± 0.078, top_heavy +1.100 ± 1.450 (of 100); C1's: auction -0.106 ± 0.128, river_of_blood
-0.054 ± 0.131. None beyond noise, but the read's prior and tier race were fitted on hold'em hands and sizes, and on
a twist table neither holds (three hole cards, a bounty, a short deck). `size_read_holdem_only` keeps the read on a
hold'em table only (`hero.holdem_table`: two hole cards, the standard board, deck and rank order, no-limit, and no
Rules.extras key but `variant` / `ante_rule` with a structural entry: top_heavy, antes_from_level_3, fast_schedule,
straddle). An unseen twist with any new key turns it off. Also: the read now takes F's own `call_shift` (toss / keep /
long-board dials), as F's call rule does; zero on hold'em.

By construction C7 plays every twist table exactly as F (tested: bounty, three tables) and every hold'em table exactly
as C6 (tested; and on screen night 10000-10024 x 8 C7's samples equal C6's sample for sample). So C7's screens are
C6's on hold'em cells and top_heavy, and identical to F on the other 22 catalogued variants.

## 09:05-09:40: the candidate's screens (C6 at e34942b = C7 on hold'em; screen seeds 10000-10199 x 8)

`climb_accept --set screen --stages confirm,guards,elite --aim strong` (addendum 8) and `--stages exploit`; the
variants at 100 seeds (realistic). cand - F, paired; 0 errors and 0 timeouts in every cell for both specs.

| cell | F | C6 / C7 | C6 / C7 - F | |
|---|---|---|---|---|
| night | 5.973 | 5.942 | -0.031 ± 0.087 | level |
| night_hard | 5.485 | 5.555 | +0.070 ± 0.104 | level |
| realistic | 6.346 | 6.345 | -0.001 ± 0.088 | level |
| top | 5.035 | 5.138 | +0.103 ± 0.108 | level (lower bound -0.005) |
| night @10/7/5/4/3/2/1/0 | 6.159 | 6.213 | +0.055 ± 0.149 | level |
| night @50/25/12/6/3/2/1/1 | 24.443 | 24.391 | -0.052 ± 0.937 | level |
| night, doubling blinds | 5.828 | 5.782 | -0.046 ± 0.085 | level |
| **elite** | 4.681 | 4.937 | **+0.256 ± 0.105** | UP |
| **elite_night** | 5.329 | 5.555 | **+0.227 ± 0.096** | UP |
| exploit (8-max, exploiter 1) | 4.999 | 4.943 | -0.056 ± 0.144 | level |
| exploit_hu | 8.005 | 8.005 | +0.000 ± 0.000 | identical (the read is off) |
| exploit_3 | 7.027 | 7.027 | +0.000 ± 0.000 | identical |
| top_heavy (variant, 100 seeds) | 27.175 | 28.275 | +1.100 ± 1.450 | level |
| the 22 twist variants (C7) | | | identical to F by construction | |
| antes_from_level_3, fast_schedule, straddle | | | the read plays as on hold'em; not measured | |

Verdict (`--aim strong`): ACCEPT on the screen (an elite field beyond noise up, night not down, no guard or elite cell
down). C6's own twist cells, before the hold'em gate: bounty -0.100 ± 0.131, toss_or_holdem -0.067 ± 0.078,
short_deck +0.041 ± 0.078.

**Latency** (`tools/latency.py`, code de6875e, C7 against F, host at load 13-18, two simulator processes running):

| | F | C7 |
|---|---|---|
| decisions, 20,000 random observations, p50 (two runs) | 51.9 / 52.4 µs | 52.6 / 53.3 µs |
| same, p99 / max (the host: wall 3.3-4.3 s against CPU 1.4 s) | 4,585 / 4,100 µs; max 33.8 ms | 6,582 / 8,095 µs; max 30.5 ms |
| decisions on 20 recorded night tables, per-call minimum of 3: mean / p99 / max | 47.7 / 100.4 / 278 µs | 49.8 / 104.0 / 208 µs |
| hand end, per-call minimum of 3: mean / p99 / max | 54.1 / 99.1 / 174 µs | 58.2 / 137.6 / 175 µs |
| each table's first decision, minimum: mean / max | 106 / 122 µs | 110 / 138 µs |

The read costs about 2 µs a decision on average (a 9-tier sum and a slice of 9 shares, only facing a heads-up bet)
and about 4 µs a hand end on average, 38 µs at the hand end's p99: `Profiler._size_end` reads each shown bettor's tier
at each of its bets (one evaluator call each). Far inside 1 ms; if a kit times the hand end tightly, that pass can move
to `idle()` with Hero's deferred work (not done).

## What I kept, and why

- **Kept (recommended): C7** = `{"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0,
  "hero.postflop.size_read_min_alive": 4, "hero.postflop.size_read_holdem_only": true}`, aim **strong** (addendum 8):
  bet size against strength, learned from each seat's own size shares (no showdowns needed), off heads-up and
  three-handed, off on twist tables. Gains at every strong table (elite +0.26, elite_night +0.23, top +0.10), level on
  night and every guard; against exploiter 1 heads-up and three-handed it is F, at 8-max level.
- **Built, not recommended:** C1 (the same read everywhere: exploit_hu -0.285 and exploit_3 -0.283 beyond noise);
  C3 (blend 0.5 + floor: halves both the leak and the gain); C4 (floor only: nothing fixed); the population map per
  size (no gain online); `xr_shift` (thin value when a non-check-raiser checks: +0.016 / -0.020 / -0.030 on night /
  top / elite); `r3.l3_on` (light 3-bets: oracle +0.058 / +0.084 / +0.023, never beyond noise; the learned version was
  not measured). All stay as dials, off.
- **Ceiling device and oracles:** scratch only (`goal/s12/`), never in hyperion/.

## Open (for the coordinator and the next worker)

1. Held-out confirmation of C7 with `--aim strong` (elite, elite_night, top on H-next; night, guards, exploit,
   aware, variants; the judges at batch end, elite_judge first).
2. The size read with S11's wide-bettor read on: both edit Postflop's facing-a-bet block; at weight 1 the size read
   overrides S11's margin there. Measure together before both ship.
3. The flop-only hybrid (`size_read_rank_streets` 1 + `size_read_rank_by_street`) or the blend fit the truth better
   offline (strong bots 0.052-0.056 against C1's 0.064); with the short-handed gate they might keep the strong-table
   gain and add some on night. Not measured.
4. Preflop reads at strong tables: warm rival 3 core reads cost at elite (-0.11) and the layer's (-0.05); F's
   preflop exploitation of fold and 3-bet reads looks too strong against prepared bots. A dampening by opponent
   strength (or a slower prior at strong tables) is the next read-side idea; S9's territory overlaps.
5. `Profiler._size_end` could move to `idle()` for kits that time the hand end.

## 09:43-09:50: the full suite at the final code (de6875e, load 13-15)

1,040 passed, 11 failed, 4 skipped (6 min). The failures are the host's: per-bot budget checks in a mixed field
(five bots, none of them ours), the gate's history-dropping package and the kit-D cheap-bot round trip (wall-clock
latency; the climb log already lists the round trip as failing at load 13 on main), and the `replay exactly in model
mode` tests (they fail the same way on base 5c6af66 under this load: plain Hero's SafeBot reads the wall clock
there). `test_aware_bots_are_deterministic_for_a_seed` passed alone. tests/test_s12_reads.py: 12 passed; the
targeted suites (ship, compose, strategy, hybrid3, S2 / V-b / V-c dials, variants, API card, climb_accept): 207 passed.
F's default play is unchanged on the branch: checked chunk for chunk (night 10000-10024 x 8) against 5c6af66 at
0db5695, 36818ca, c56d1e2 and e34942b; at de6875e by the tests (every new dial is off by default and inert off).

# S12b: the size read only where it has evidence (branch climb/s12b-gated from main 63bd29f)

The coordinator's H5 run of C7 (24000-24399, base batch 4, `--aim strong`): elite +0.154 ± 0.071, elite_night +0.092
± 0.065, mirror +0.415 ± 0.079, top +0.183 ± 0.068 (all up); rejected for realistic -0.096 ± 0.064 and the three
structural variants the hold'em gate leaves the read on (antes_from_level_3 -0.103, fast_schedule -0.100, straddle
-0.128; all played on realistic). Realistic's seats are one-size or broken bettors (loose_aggro, tag, the Monte Carlo
bots, the bot that breaks).

## 11:20-11:35: the gates, and the thresholds fixed before any screen

New dials (Postflop, off by default; counters in the profiler only with `track_s12`):
- per seat: `size_read_min_bets` / `size_read_min_share` / `size_read_min_buckets`: read a bettor only once it has
  shown that many size buckets with that many bets and that share of its bets each (`Profiler.size_evidence`, every
  street pooled); `size_read_skip_weak`: never a seat flagged dead, station, maniac or random;
- per table: `size_read_strong_rr` (+ prior, weight): only while my first-in raises (not all-in) are re-raised at least
  that often, smoothed (`Profiler.strong_table`: S9's strong_rr signal counted in the profiler, so Hero's reads and
  any other part can share it).

Firing diagnostic before choosing (no points; seeds 8000-8003 x 8, C7's read spots, the share each gate passes, by
bettor; `goal/s12b/gaterate.py`):

| field | spots | 3 bets per bucket | 2 bets per bucket | table reads strong (0.20 / 0.15 / 10) |
|---|---|---|---|---|
| realistic | 275 | 0.04 | 0.10 | 0.07 |
| elite | 228 | 0.15 | 0.31 | 0.19 |
| top | 227 | 0.14 | 0.22 | 0.18 |
| mirror | 262 | 0.20 | 0.44 | 0.23 |
| night | 268 | 0.12 | 0.22 | 0.12 |

By bettor, 2 per bucket: one-size and broken bettors 0-2% (loose_aggro 0/73 and 0/66, tag 0/33, timeout_then_recover
0/40, montecarlo30 1/43, naive 0/21, timeout_burst 0/17); two-size bettors 16-68% (rival1 33-47%, rival3 36%, elite1
20-32%, elite2 35-46%, f_copy 55%, hybrid3_x 68%, agent_default 30-62%, agent_montecarlo 60%). 3 per bucket excludes
the same bettors and halves the rest. The table signal is on in only 12-23% of spots even at the strong tables (its
prior needs re-raises to accumulate), so as the only gate it would remove most of the read.

**Pre-registered:** candidate **D1** = C7 + `size_read_min_bets` 2, `size_read_min_share` 0.15,
`size_read_min_buckets` 2, `size_read_skip_weak` true. Fallback D2 = D1 + `size_read_strong_rr` 0.20 (prior 0.15,
10 raises), only if D1 is still beyond noise down on realistic or a structural variant. No sweep.

## 11:36-12:53: D1's screens (code 6bd9fbb, base batch 4's ship = main 63bd29f's F; screen 10000-10199 x 8)

`climb_accept --set screen --stages confirm,guards,elite,exploit,variants --variants antes_from_level_3,fast_schedule,
straddle,top_heavy --variant-seeds 200 --aim strong` (run from a detached worktree at 6bd9fbb; the cells were first
filled by two queues, the failed cells first). D1 - F, paired; 0 errors and 0 timeouts in every cell for both specs.

| cell | F | D1 | D1 - F | | C7 on screen (old base) | C7 on H5 |
|---|---|---|---|---|---|---|
| night | 5.968 | 5.998 | +0.030 ± 0.050 | level | -0.031 ± 0.087 | -0.039 ± 0.063 |
| night_hard | 5.486 | 5.575 | **+0.088 ± 0.055** | UP | +0.070 | +0.066 |
| **realistic** | 6.346 | 6.394 | **+0.047 ± 0.028** | UP | -0.001 ± 0.088 | **-0.096 ± 0.064** |
| top | 5.035 | 5.103 | **+0.068 ± 0.056** | UP | +0.103 ± 0.108 | +0.183 ± 0.068 |
| night @10/7/5/4/3/2/1/0 | 6.149 | 6.227 | +0.078 ± 0.090 | level | +0.055 | |
| night @50/25/12/6/3/2/1/1 | 24.406 | 24.916 | +0.510 ± 0.603 | level | -0.052 | |
| night, doubling blinds | 5.830 | 5.812 | -0.018 ± 0.040 | level | -0.046 | |
| elite | 4.681 | 4.765 | **+0.084 ± 0.063** | UP | +0.256 ± 0.105 | +0.154 ± 0.071 |
| elite_night | 5.328 | 5.394 | **+0.066 ± 0.058** | UP | +0.227 ± 0.096 | +0.092 ± 0.065 |
| mirror | 4.414 | 4.543 | **+0.128 ± 0.081** | UP | (not run) | +0.415 ± 0.079 |
| exploit (8-max) | 5.619 | 5.645 | +0.026 ± 0.093 | level | -0.056 | +0.015 |
| exploit_hu / exploit_3 | 9.115 / 8.354 | same | identical | | identical | |
| **antes_from_level_3** | 6.494 | 6.532 | **+0.038 ± 0.029** | UP | | **-0.103 ± 0.090** |
| **fast_schedule** | 6.114 | 6.106 | -0.008 ± 0.022 | level | | **-0.100 ± 0.083** |
| **straddle** | 6.380 | 6.391 | +0.011 ± 0.022 | level | | **-0.128 ± 0.088** |
| top_heavy | 28.629 | 29.232 | **+0.603 ± 0.402** | UP | +1.100 ± 1.450 | |
| the 22 twist variants | | | identical to F by construction (the hold'em gate; tests) | | | |

Verdict: **ACCEPT** (addendum 8: elite, elite_night and mirror beyond noise up; night not down; no guard, elite or
variant cell down). The four cells that failed on H5 are now up or level, and the tight intervals there (± 0.022 to
0.029) are the gate's doing: on realistic it lets through about a tenth of C7's spots (rival 1, pushfold), so the
paired difference is small and steady. The price is at the strong tables: about a third of C7's screen gain at elite and
elite_night, and mirror +0.128 against C7's held-out +0.415 (different seeds and base; comparable size is unknown).
The early-table spots where C7 read a two-size bettor from the prior alone are the ones given up.

**Latency** (`tools/latency.py`, 6bd9fbb, D1 against F, load 9-12): decisions on 20 recorded night tables, per-call
minimum of 3: mean / p99 / max F 48.2 / 102.0 / 163 µs, D1 49.6 / 100.8 / 155 µs; hand end F 55.9 / 99.9 / 134 µs,
D1 60.2 / 133.9 / 230 µs; first decision of a table F 104 / 118, D1 102 / 140 µs (mean / max). 20,000 random
observations: p50 52.9 against 53.3-53.9 µs; p99 4-12 ms for both (the host). The gate adds a pass over five bucket
counts and an archetype lookup on read spots only.

**Tests:** tests/test_s12_reads.py 15 passed (new: size evidence, the strong-table count, the gates reach decisions
and change nothing off). Full suite at 6bd9fbb: 1,153 passed, 9 failed, 26 skipped (18.6 min, load 9-12); the 9 are
the load failures seen before (the outside / elite field and model-mode replay tests that read the wall clock, the
gate's history-dropping package, the kit-D cheap-bot round trip, slowbox); `test_model_mode_replays_a_table_exactly`
passed alone.

**Recommended (aim strong, addendum 8):** D1 = `{"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0,
"hero.postflop.size_read_min_alive": 4, "hero.postflop.size_read_holdem_only": true, "hero.postflop.size_read_min_bets":
2, "hero.postflop.size_read_min_share": 0.15, "hero.postflop.size_read_min_buckets": 2,
"hero.postflop.size_read_skip_weak": true}`. D2 (the table gate) was not needed and not run; `size_read_strong_rr` and
`Profiler.strong_table` stay as a shared signal, off.

Open: a weaker per-seat bar (one bet in each of two buckets with the share test) would fire earlier at strong tables;
it was not screened (no sweep). S11's facing-a-bet changes still need measuring together with this read.
