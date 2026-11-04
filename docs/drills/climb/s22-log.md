# S22: the river over-fold exploiter 4 found (running log)

Branch climb/s22-river, from main 7a352ba (batch 7 is F). Brief (coordinator, 2026-11-04 11:40): exploiter 4
(docs/drills/exploiter4/NOTEBOOK.md, F9) finds that F folds 66-81% to a 0.7-pot river bet heads-up (break-even
about 41%) and does not adapt. Diagnose on seeds 15000-15999 only, fix behind dials that are off by default, screen
on 10000-10199 with `--aim exploit`. No held-out set, judge set, judge bot or judge field is run, read or tuned on
(20000-60799 untouched). Workers 2, nice 5, detached runs with done-files.

**Where I am / next:** identity 14 of 14; the screen is running (scratch goal/s22/screen.sh, done-file screen.done; re-run the same script after a restart, chunks are cached); the full suite beside it.
from it, then the code.

## Diagnosis (seeds 15000-15199 heads-up and three-handed, 15000-15079 x 8 at 8-max; F = batch 7, model mode)

Scratch `goal/s22/diag.py` records every postflop decision of every seat in hands F plays, with the simulator's
cards, F's route and its reads of the bettor; `ana.py` takes heads-up pots (two players in the hand) on a street.
"F wins" is F's share of the pot at showdown against the bettor's actual cards (river), or its equity over every
river card (turn), whether or not the hand went to showdown. "Price" is the call's share of the final pot.

### 1. Exploiter 4 bets 70-72% of its river chances, and F's folds there give up most of those pots

Heads-up pots against F on the river, exploiter 4's free actions (nothing to call: it acts first, or F has
checked) and F's answer to the river's first bet (nothing of F's in). 200 seeds of each cell.

| cell | its river bet rate (after F's check / first to act / all) | its bets: air (tier 0-1) / weak pair / tier 3 / tier 4+ | F's hand beats its bet | F folds |
|---|---|---|---|---|
| exploit4_hu | 0.74 / 0.71 / **0.72** (1,304 of 1,820) | 0.46 / 0.26 / 0.05 / 0.23 | **0.58** | **0.74** |
| exploit4_3 | 0.71 / 0.70 / **0.70** | 0.45 / 0.26 / 0.05 / 0.25 | **0.55** | **0.71** |

F's folds and showdown share by its own tier (heads-up; price = the call's share of the final pot, 0.29 on average):

| F's tier | 0 air | 1 overcards | 2 weak / middle pair | 3 top pair weak kicker | 4+ |
|---|---|---|---|---|---|
| exploit4_hu: spots / F folds / F's share if it called | 290 / 100% / 0.29 | 210 / 100% / **0.48** | 427 / **93%** / **0.66** | 142 / 40% / 0.73 | 235 / 5% / 0.70-0.96 |
| exploit4_3 | 294 / 100% / 0.28 | 238 / 100% / 0.44 | 408 / 94% / 0.62 | 147 / 20% / 0.66 | 250 / 0% |

Calling every hand F folds would have won +0.40 pots a spot heads-up and +0.33 three-handed (chips, from the
cards, before any change in its play). Its bets come in three sizes that name the hand: 0.7 pot is its river bluff
(air and weak hands, F9's stab: equity under 0.45 bets with probability 0.85 x its fold read, when four or fewer have
chips), 0.6 and 0.75 pot its value (equity 0.62 and up). Most of its river bets are leads: heads-up, 928 of its
1,304 bets came when it acted first, so a read of bets after F's check sees only a third of them.

### 2. Why F's threshold does not move

F's river call is `equity proxy >= price + call_margin / call_down`. The proxy is the tier's TIER_EQUITY (tier 2:
0.32, tier 3: 0.42, tier 4: 0.58); call_margin is 0.2 (SHIP_DIALS); call_down (the profiler's read of a maniac) is
capped at 1.0 on the turn and river (late_calldown_cap) unless the bettor is a maniac or random. Facing 0.7 pot
(price 0.29) F needs 0.49: tier 4 and up calls, tier 3 folds, tier 2 always folds. Nothing in that line reads how
often the bettor bets. The one read that can move it, S15e's stab read, fired on 3% of F's river decisions against
exploiter 4 heads-up and 2% three-handed (scratch `why.py`): it reads only bets right after F's check (29% / 41% of
the spots), and exploiter 4 fails its gates about half the time each (pfr >= 0.35: 53%, lead rate <= 0.4: 48%, free
rate <= 0.5: 59%; the stab rate above 0.55: 36%). Exploiter 4's call-down read is above 1 in 86% of the spots and
capped to 1.

### 3. The other opponents (river, heads-up pots against F)

| cell / seat | river bet rate | its bets: air / weak / t3 / 4+ | F's hand beats | F folds | tier 2: folds / F's share |
|---|---|---|---|---|---|
| exploit_hu exploiter 1 | 0.55 (0.58 after F's check) | 0.35 / 0.29 / 0.06 / 0.30 | 0.44 | 0.78 | 93% / 0.56 |
| exploit_3 exploiter 1 | 0.55 | 0.32 / 0.29 / 0.08 / 0.32 | 0.49 | 0.66 | 87% / 0.50 |
| exploit2_hu exploiter 2 | 0.16 | 0.00 / 0.01 / 0.00 / 0.99 | 0.09 | 0.57 | 73% / 0.00 |
| exploit2_3 exploiter 2 | 0.20 | 0.00 / 0.03 / 0.00 / 0.97 | 0.22 | 0.49 | 83% / 0.00 |
| exploit3_hu exploiter 3 | 0.24 (0.46 after F's check) | 0.19 / 0.15 / 0.00 / 0.66 | 0.32 | 0.50 | 48% / 0.43 |
| exploit3_3 exploiter 3 | 0.23 | 0.15 / 0.15 / 0.00 / 0.70 | 0.26 | 0.61 | 72% / 0.29 |
| adapt_hu adapt1 | 0.30 | 0.28 / 0.18 / 0.03 / 0.51 | 0.46 | 0.47 | 72% / 0.41 |
| adapt_3 adapt1 | 0.36 | 0.29 / 0.20 / 0.04 / 0.48 | 0.49 | 0.52 | 90% / 0.43 |
| night seat in the three-handed cells (five cells pooled) | 0.29-0.31 | 0.08-0.16 / 0.18-0.25 / 0.09-0.10 / 0.56-0.59 | 0.24-0.28 | 0.71-0.75 | 91-97% / 0.15-0.20 |

The night seat's river bets are value (F's tier 2 wins 15-20% of them at a price of 0.27): F's folds are right
there, as the brief expects. Exploiter 1 is the other seat that bets rivers far more than the room, and F's weak pairs
win half the time against it too. Exploiters 2 and 3 bet the river at or under the room's rate, with value.

### 4. The turn

Exploiter 4 bets 0.36 of its heads-up turn chances (0.44 after F's check), about the night seat's rate (0.35-0.38):
on the turn its frequency does not stand out from the room. F folds 66% to its turn bets; F's tier 2 has 0.37 equity
over the river against them at a price of 0.28, but a turn call faces the river after it, and the frequency read
cannot tell exploiter 4 from an ordinary seat there. The fix stays on the river.

### 5. The rooms at 8-max (river, heads-up pots against F; 80 seeds x 8)

| room | seats' river bet rates (all alive) | their bets that F's hand beats | at three or fewer alive |
|---|---|---|---|
| night, night_hard | 0.29-0.31 | 0.28-0.29 | 0.24-0.28, F beats 0.26 |
| realistic | rival1 0.23, montecarlo 0.17-0.26, tag 0.57, pushfold 0.60, loose_aggro 0.62, timeout_then_recover 0.75 | 0.19-0.27 for the first three, 0.42-0.50 for the last four | 0.18-0.67 (6-18 chances each) |
| elite, elite_b, mirror | elite1 0.40-0.45, elite2 0.40-0.46, elite4 0.53, rival1-3 0.24-0.43, F's copy 0.48, agents 0.34-0.46 | 0.18-0.37, elite2 and elite4 0.49-0.55 | 0.11-0.67 (5-36 chances each) |
| exploit4 (six night seats) | exploiter 4 0.51, night 0.32 | 0.47 / 0.27 | exploiter 4 0.62 (F beats 0.57), night 0.23 |

The room bets about a third of its river chances (night 0.29-0.31, the elite builds 0.40-0.46, rival1 0.23), with value
behind most of them. A few ordinary seats bet more and bluff too (realistic's loose and push-fold seats, elite2 and
elite4), and there F's folds are also too many, but they are few chances at a table.

## The read, its prior and its gate (fixed from the diagnosis, before any screen)

`hero.postflop.rbet_*` (hyperion/strategy/postflop.py; the count in Profiler.river_bet_rate). Facing the river's
first bet heads-up (nothing of F's in: a lead or a bet after F's check) from a seat whose smoothed river bet rate is
above `rbet_from`, F's equity moves from the tier's proxy toward WIDE_EQUITY_RIVER (the tier against a whole range,
S15's river row) and its call margin from 0.2 toward `rbet_margin`, by the weight (r - from) / (full - from), at most
1. It only calls more: no raise, no bluff. Where S15e's stab read also acts, the larger weight decides.

- **The count:** every river action with nothing to call heads-up against F, whoever acts first. Two thirds of
  exploiter 4's river bets are leads (section 1); a count of bets after F's check alone sees a third of them.
- **The prior, 0.35 worth 4 chances; no read before 3 chances (`rbet_prior`, `rbet_n`, `rbet_min`).** The room's
  rate is about 0.30 (night 0.29-0.31; rival1 0.23; elite builds 0.40-0.46): 0.35 sits in it. A heads-up match gives
  about 4.5 river chances a table against exploiter 4, so the read must start early, but one or two early bets of an
  ordinary seat must not switch it on: with 4 chances of prior and 3 seen, a seat needs 3 bets of 3 (0.63) or 3 of 4
  (0.55) to pass 0.5.
- **The threshold, from 0.5, full at 0.65 (`rbet_from`, `rbet_full`).** Exploiter 4 bets 0.70-0.72, exploiter 1 0.55,
  the room 0.23-0.46. At the weight's full value the call needs price + 0.03 (`rbet_margin`, S15's stab margin):
  against a 0.7-pot bet tier 1 (0.34) calls, tier 0 (0.18) never; tier 2 calls from weight 0.4, tier 3 from 0.14.
  Against exploiter 4 F's tier 1 wins 0.44-0.48 of these pots, tier 2 0.62-0.66 (section 1); against exploiter 1,
  whose rate tops out near 0.55 (weight 0.33), tier 2 and 3 call and tier 1 does not (it wins 0.23-0.27 there).
- **The gate: three or fewer players with chips (`rbet_max_alive` 3), hold'em tables only (`rbet_holdem_only`).**
  As the brief asks, and as S15b found at 8-max: the decisive endgame hands against ordinary seats are where a
  frequency read costs. No pfr or lead gate: exploiter 4's preflop raise rate (0.33-0.36) and lead rate (0.41-0.43)
  sit inside the room's, and its river frequency alone separates it.

**Offline replay** (scratch `ana2.py`, `grid.py`: the read recomputed from the records in play order, each of F's
folds re-decided; chips from the cards, so a guide to where it fires, not a verdict; the opponents' answers to F's
new calls are not in it). At these dials, folds turned into calls, with their chips in pots before the bet:

| where | changed | chips |
|---|---|---|
| exploit4_hu / exploit4_3 / exploit4 (8-max), against exploiter 4 | 218 / 144 / 9 | +216 / +127 / +12 pots |
| exploit_hu / exploit_3, against exploiter 1 | 37 / 33 | +25 / +24 |
| adapt1, exploiters 2 and 3 (six cells) | 0-2 each | -1.3 to +1.0 each |
| every other seat in the fourteen cells (night, night_hard, realistic, elite, elite_b, mirror, the exploit cells' night seats) | 0-8 each, 37 in all | -1.0 to +4.7 each |

Faster settings found more against exploiter 4 and more elsewhere: from 0.45 (271 changes heads-up, +264) also
changed 9 decisions against exploiter 3 heads-up (-3.8); prior worth 2 chances with a 2-chance minimum (341, +326)
changed 10-17 a cell against the night seats (-3.2 to -3.8). From 0.55 / full 0.75 kept half the gain.
Without the alive gate the 8-max rooms change 3-11 decisions a cell (similar chips): the gate costs little here and
keeps the read out of full-table play, which these fields cannot test well.

**Points on the diagnostic seeds** (scratch `quick.py`: climb_accept's own cells and paired interval, F against the
candidate, seeds 15000-15199, not a screen):

| cell | F | S22 | S22 - F | exploiter F / S22 |
|---|---|---|---|---|
| exploit4_hu | 8.320 | 8.395 | +0.075 ± 0.077 | 8.680 / 8.605 |
| exploit4_3 | 7.687 | 7.760 | **+0.073 ± 0.059** | 7.797 / 7.722 |
| exploit_hu | 9.318 | 9.355 | +0.037 ± 0.044 | 7.683 / 7.645 |
| exploit_3 | 8.493 | 8.537 | **+0.043 ± 0.043** | 6.897 / 6.860 |

The candidate, `docs/drills/climb/s22-candidate.json` (on top of SHIP_DIALS):

    {"dials": {"hero.postflop.rbet_from": 0.5, "hero.postflop.rbet_full": 0.65, "hero.postflop.rbet_prior": 0.35,
               "hero.postflop.rbet_n": 4, "hero.postflop.rbet_min": 3, "hero.postflop.rbet_margin": 0.03,
               "hero.postflop.rbet_max_alive": 3, "hero.postflop.rbet_holdem_only": true}}

## Identity

The branch with the new dials off (25f37d5; SHIP_DIALS = batch 7) against batch 7's F (goal/idchk34/post):
`climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, chunk by chunk (scratch
`goal/s22/idchk.sh`, `idcmp.py`): **14 of 14 identical.** Code under hyperion/ is unchanged since 003aec8 (the screen's
cache key is the same tree).

