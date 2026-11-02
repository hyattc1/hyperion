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
| top | +0.021 ± 0.143 | (running) |
| elite | **-0.236 ± 0.161** | (running) |

Read: **reading faster with today's reads is worth little, and loses at the strongest table.** Perfect long-run
knowledge of every per-seat stat F keeps, from hand 0, gains beyond noise only on realistic (a weak-heavy room: two
Monte Carlo bots that time out, a bot that breaks, a loose student) and is level on night. At the elite table it is
beyond noise down: F's responses to its reads (archetype dials, steals by fold reads, call-down dials) are sized for
weak seats, and acting on them at full strength from the first hand costs against prepared bots, as `dead_seats`
did in F1 (-0.160 at elite). The value is not in reading sooner but in reading what F does not read yet.
