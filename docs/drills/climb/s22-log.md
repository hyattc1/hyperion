# S22: the river over-fold exploiter 4 found (running log)

Branch climb/s22-river, from main 7a352ba (batch 7 is F). Brief (coordinator, 2026-11-04 11:40): exploiter 4
(docs/drills/exploiter4/NOTEBOOK.md, F9) finds that F folds 66-81% to a 0.7-pot river bet heads-up (break-even
about 41%) and does not adapt. Diagnose on seeds 15000-15999 only, fix behind dials that are off by default, screen
on 10000-10199 with `--aim exploit`. No held-out set, judge set, judge bot or judge field is run, read or tuned on
(20000-60799 untouched). Workers 2, nice 5, detached runs with done-files.

**Where I am / next:** diagnosis of the exploit cells done (sections 1-4); 8-max rooms running; the read is coded (off by default, 6a below), its prior and gate next.
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

