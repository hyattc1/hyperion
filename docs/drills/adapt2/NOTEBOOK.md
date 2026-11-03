# Adaptive rival bot: notebook

## Summary

**Deliverables.** `rival_bot.py` (frozen v7, md5 `ee30b9a61161cdbf3c126a6c345bac70`, also in FROZEN.md5),
this notebook. Standard library only: `class Bot(Agent)`, importing Agent from kit with a fallback.
`python3 harness.py rival_bot` gives 0 exceptions, 0 illegal actions, 0 folds when a check was legal,
median 33 us, p99 about 100-200 us. On this machine (8 cores, load average 12-13) the harness max is
0.5-5 ms, and about 1 call in 2,000 exceeds 1 ms. Re-running each of the 60 slowest calls from the
same state takes 20-42 us, so those spikes are the scheduler preempting us, not work the bot does.
Replay: the only randomness is `self.rng`, seeded in `new_table` from the seat. Each decision draws
exactly two numbers, so the on and off copies use the RNG in step. `replay_test.py` confirms that
the same seeds give identical actions.

**Design.**
- *Base game (all counters off).*
  - Preflop: a table of each hand's heads-up equity against a random hand, plus a 169x169
    hand-vs-hand heuristic built at import. That gives the equity of any hand against the top w%
    of hands.
  - Open widths depend on how many players are left to act (HU small blind 80%, button about 44%,
    UTG 14%). Value 3-bets take the top third of the opener's range, plus 3-bet bluffs with suited
    aces and suited connectors. Calls are by pot odds times a realization factor (in position .92,
    out of position .78).
  - Push/fold at 13 bb or less, decided by explicit EV with prior calling widths. Re-shoves at 22 bb
    or less. Facing an all-in: our equity against the shove range must reach the pot odds plus an
    ICM margin (+.045 when 4 or more players are alive).
  - Postflop: a 7-card evaluator and a rule-based reader turn the made hand, the board texture
    (flush, straight, paired) and the outs into s, roughly our equity against a reasonable range.
    Value bets at s of about .62 or more. Heads-up the bot c-bets 62%, barrels, probes, and
    semi-bluffs with 8 or more outs.
  - Facing a bet: s minus a range penalty that grows with bet size, street and raises, against the
    pot odds.
- *Opponent model.* Each seat starts from zero at every table and is read from its actions alone:
  the engine never shows hole cards. The history lists no blind posts and marks no street breaks,
  so the bot rebuilds the streets by replaying the betting rules. Over all 10.0 million logged decisions
  in every run, there were 0 mismatches against the engine and 0 exceptions.
  - Every read is shrunk toward the value the base game already assumes, and forgets at 0.985 per
    observation. With no evidence the bot plays its base game.
  - Each counter acts only outside a dead zone around its prior, so it switches on from a tendency
    seen at this table and switches off when the read comes back. There is no fingerprinting: no
    rule mentions any particular bot.
  - The switch-off demo: a seat folds 75% to bets, then 20%. The working read goes .71 -> .45 -> .36:
    bluff-more is on by spot 10, off by spot 60, and station mode is on by spot 70.

| counter (DISABLED name) | read (prior) | what it changes |
|---|---|---|
| steal | continue vs an open, ratio to the prior | widen opens when the players behind over-fold (widen only; the ablation showed that tightening against wide defenders cost) |
| opener | open-raise frequency, ratio | width of the opener's range for 3-bet, call and defend decisions |
| light3 | 3-bet frequency, ratio (.09 HU, .06 multi) | width of the 3-bettor's range for 4-bet and call decisions |
| f3b | fold to a 3-bet (.55) | frequency of 3-bet bluffs |
| shover / callshove | all-in frequency; calls against shoves, ratio | range assumed when calling a shove; fold equity in shove EV |
| fbet | fold to a postflop bet (.45) | c-bet, barrel and probe frequency (odds multiplier); station mode: no bluffs, thinner and bigger value bets |
| agg (+ trap) | bets when checked to (.35) | penalty when facing that seat's bets (bluff-catch wider against bettors, fold more against passive ones); check strong hands out of position against bettors |
| xr | raises when facing a bet (.12) | penalty when facing that seat's raises |
| size | river bluff-catch result minus prediction, small vs big bets | calling adjustment by bet size (needs our own river showdowns, so it is the weakest read) |
| vcall | river value bets that got called: result minus prediction | thinner or tighter value bets |

**Learning results** (frozen bot, fresh seeds never used in tuning; counters on minus an identical
copy with counters off; chips per table, paired table by table on the same deals; 95% intervals;
bold means the interval excludes 0):

*Heads-up, seed 201: counters on minus off, chips per table (95% interval)*

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 1.584 / 1.511 (+0.073) | **+71 +-22** | **+203 +-89** | +18 +-39 | **+292 +-100** | 1600 |
| B | 1.611 / 1.605 (+0.006) | +12 +-25 | +18 +-75 | -7 +-33 | +22 +-88 | 1600 |
| C | 1.643 / 1.620 (+0.023) | **+47 +-41** | +47 +-74 | -2 +-5 | **+92 +-84** | 1600 |
| D | 1.583 / 1.583 (+0.000) | +17 +-21 | -12 +-81 | -8 +-41 | -2 +-91 | 1600 |
| E | 1.564 / 1.534 (+0.030) | +13 +-23 | **+115 +-81** | -8 +-41 | **+120 +-93** | 1600 |

*3-handed, seed 202: counters on minus off, chips per table (95% interval)*

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 2.199 / 2.167 (+0.032) | +31 +-34 | **+189 +-159** | -61 +-138 | +160 +-220 | 900 |
| B | 2.198 / 2.132 (+0.066) | +33 +-39 | **+221 +-129** | -13 +-133 | **+240 +-192** | 900 |
| C | 2.242 / 2.170 (+0.072) | +30 +-42 | **+320 +-154** | -96 +-134 | **+253 +-213** | 900 |
| D | 2.256 / 2.224 (+0.032) | +25 +-35 | +86 +-144 | +35 +-136 | +147 +-204 | 900 |
| E | 2.211 / 2.181 (+0.030) | +12 +-36 | +121 +-148 | +87 +-131 | **+220 +-201** | 900 |

*8-max, seed 203: counters on minus off, chips per table (95% interval)*

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 5.283 / 5.089 (+0.194) | +34 +-34 | **+161 +-123** | **+1131 +-428** | **+1326 +-468** | 1200 |
| B | 5.190 / 5.075 (+0.115) | +37 +-37 | **+155 +-119** | +375 +-399 | **+567 +-434** | 1200 |
| C | 5.229 / 5.104 (+0.125) | +17 +-32 | **+211 +-124** | **+721 +-394** | **+949 +-431** | 1200 |
| D | 5.275 / 5.245 (+0.030) | **+38 +-35** | +52 +-128 | **+540 +-414** | **+630 +-450** | 1200 |
| E | 5.231 / 5.207 (+0.024) | **+42 +-34** | +8 +-125 | **+716 +-411** | **+765 +-451** | 1200 |

Reading the results:
- *It learns, and the gain grows with the window.* At 8-max, the five-target mean is about +34 chips
  in hands 1-30, +117 in 31-100 and +700 in 101-200, and all five "all hands" totals are significant.
  Three-handed, every target is positive (+147..+253), mostly in 31-100. Heads-up, matches last
  about 50 hands (C about 28), so 101-200 is nearly empty and the gain sits in 1-30 and 31-100.
- *It exploits only what a target actually does.* Heads-up, the gain is large against A (folds to a
  postflop bet 71%: +292 a match), E (folds 61% and bets 61% when checked to: +120) and C (station
  plus maniac, raises 54% of bets: +92). It is about zero against B and D, whose postflop folding
  sits near the prior (B is passive, D is near-prior everywhere). That is the intended behaviour:
  nothing to exploit, nothing switches on hard, nothing lost. No target or format is significantly negative.
- *Against bots it has never met.* At 3- and 8-handed most counter firings are on the pool bots.
  Steal, fold-to-bet and opener-width fire most, because many pool bots over-fold, some by timing
  out. The gains there come from tendencies, not from knowing who is who.
- *Points.* Heads-up +0.00..+0.07 (A +0.073 is outside noise), 3-handed +0.03..+0.07, 8-max +0.02..+0.19
  (each arm's interval is about +-0.13-0.15, so a difference needs about +-0.19; A's +0.19 is at that edge, the rest are inside it). Chips are the more
  sensitive measure. The target's own 8-max score falls when our counters are on (A 5.87 -> 5.67).
- Seeds: tuning used 11, 21, 31, 41, 61, 71; the results above use 201 (HU, 800 deals x 2 seats),
  202 (3-handed, 300 x 3) and 203 (8-max, 150 x 8).

**Limits, plainly.**
- The engine shows no hole cards, so size tells can only be learned from our own river showdowns.
  That read rarely moves a decision, and its ablation was inconclusive.
- Our 8-max base game scores below the targets' (5.2-5.3 against their 5.3-5.9). We win more 1sts than
  the target but take fewer 2nd-4th places. Stronger ICM margins (v8) did not help.
- Measurement only: meas.py wraps the bot to log chips per hand; analyze.py, mdrow.py and report.py
  build the tables. They are not part of the bot. rival_v6.py, rival_v7.py and rival_v8.py are the
  snapshots from the base-game A/B tests (v7 equals rival_bot.py except for its docstring).
  Raw run outputs are in runs/.
- Time: T0 1793691469; the final results were in at about 81 minutes.

## Log

- T0 = 1793691469 (epoch s).
- Probe (check/call bot, HU, 2 tables, seed 1, target A): the engine's `hand_end` result is
  `{'hand_no', 'deltas', 'history'}`; no hole cards are ever revealed. History entries are
  `(seat, (action, amount))`, raise amounts are raise-to totals for the street, blind posts are
  not listed and street breaks are not marked. So every read on an opponent has to come from
  their actions plus who won the pot, and showdown reads come only from hands the bot itself
  takes to showdown (we know our own cards and whether we won).

### v1: first complete bot, heads-up against each target (counters on vs off)
Command (each target T, run as an on/off pair at once): `COUNTERS=1|0 MEAS_OUT=... nice -n 5 python arena.py meas.py --tables 200 --seed 11 --target T --players 2`
(meas.py wraps rival_bot.Bot only to log each hand's chip delta; the bot is unchanged.) 200 deals x 2 seat rotations = 400 matches per arm.
The intervals are 95% intervals on the paired on-minus-off difference, matched table by table (same seed, same deal).

| target | pts on | pts off | 1-30 on-off (chips) | 31-100 | 101-200 | all |
|---|---|---|---|---|---|---|
| A | 1.490 | 1.510 | -16 +-34 | -47 +-166 | -17 +-82 | -80 +-188 |
| B | 1.613 | 1.620 | **-52 +-37** | +20 +-153 | +2 +-61 | -30 +-163 |
| C | 1.675 | 1.635 | +65 +-80 | +95 +-157 | (no hands) | +160 +-173 |
| D | 1.580 | 1.562 | -15 +-28 | +75 +-142 | +10 +-76 | +70 +-163 |
| E | 1.577 | 1.562 | **-51 +-34** | +68 +-150 | +43 +-79 | +60 +-166 |

Our base game beats every target heads-up (1.51-1.64 pts out of a 1-2 range), so its basic play holds up.
What the targets do heads-up (reads at the end of each match, averaged over the 400 counters-off matches):
- A: VPIP .72, PFR .53, **folds to a postflop bet 71%**, bets 62% when checked to, 3-bets 1.4x our prior.
- B: VPIP .81, PFR .49, folds to bets 57%, **passive postflop (bets 31% when checked to)**.
- C: VPIP .85, **a station (folds to bets 33%) and a maniac (bets 91% when checked to)**; matches are short (27 hands on average).
- D: folds to bets 64%, bets 42% when checked to. E: folds 64%, bets 60% when checked to.
- Every target calls our shoves wider than the prior (1.2-1.4x) and 3-bets lighter (1.2-1.6x).
Findings:
- Heads-up matches last about 50 hands, so the 101-200 window has little data.
- On B and E the 1-30 window is significantly negative. The early counters (steal width, fold-to-bet,
  aggression) are firing on very little evidence; noise reads cost chips.
- The size-tell read (bluff-catch result minus prediction) came out positive against every target
  (+0.06..+0.18). That is a bias in how it was measured, not a read on any target: calls that we
  later folded never reached showdown, so the losses dropped out of the sample. Fixed in v2: the
  read now counts only river calls and all-in calls, where nothing comes after.

### v2: 8-max, target A, 50 deals x 8 rotations (seed 21)
`... arena.py meas.py --tables 50 --seed 21 --target A --players 8` (counters on/off pair).
pts on 5.229 +-0.235, off 5.105 +-0.206 (diff +0.12). Chips on-off: 1-30 -15 +-59, 31-100 +136 +-178,
**101-200 +554 +-636**, all +675 +-686. The learning shows where we expected it: late, against the pool.
Target A scored 5.55 at these tables. Counters consulted while outside their dead zone, by window:
1-30 steal 12k, opener_width 1.2k; 31-100 steal 26k, opener 4.5k, fold_to_bet_hi 2.4k; 101-200 fold_to_bet_hi 2.5k,
fold_to_3bet 1.4k, call_shove 1.2k. Several pool bots time out or throw (tmo/exc columns).

### v3: bigger heads-up sample (600 deals x 2 = 1200 matches per arm, seed 31)
What changed: the dead zone now subtracts only half its width once a read is outside it, so counters
hit harder once they are on. Steal tightening is capped at 0.85x (widening up to 1.8x). New 'trap'
counter: out of position against a seat that bets most times it is checked to, check the value
hands. Against stations, bluffs drop faster (odds multiplier^1.5 when it is below 1). A small
probe-bluff frequency (12%) heads-up.
`./batch.sh v3 2 600 31 A B C D E` (each target: on/off pair, `--players 2 --tables 600 --seed 31`)

| target | pts on / off | 1-30 on-off (chips) | 31-100 | 101-200 | all |
|---|---|---|---|---|---|
| A | 1.568 / 1.514 | **+50 +-20** | **+208 +-101** | -41 +-46 | **+217 +-112** |
| B | 1.589 / 1.603 | -21 +-26 | -51 +-89 | +19 +-43 | -53 +-100 |
| C | 1.638 / 1.633 | +43 +-45 | -21 +-84 | -3 +-7 | +20 +-96 |
| D | 1.572 / 1.568 | +18 +-20 | +29 +-90 | -34 +-43 | +13 +-101 |
| E | 1.575 / 1.523 | +18 +-23 | **+165 +-90** | +24 +-41 | **+207 +-101** |

The reads match v1 (A: folds to bets 72%; C: folds 33% and bets 91% when checked to; B: passive,
bets 32% when checked to, and defends its blind more than the prior, continue ratio 1.14).
The gains against A and E come from the fold-to-bet counter (it fires the most: 34k consultations in
31-100 against A) and the aggression read. B is the one target where the counters look negative.
B's traits: passive postflop, and its blind defence is wide. Next: ablations against B and A to
find which counter costs against B.

### Ablations, heads-up, seed 31, 1200 matches per arm (on minus on-without-counter; positive means the counter earns)
`DISABLED=G COUNTERS=1 ... arena.py meas.py --tables 600 --seed 31 --target T --players 2`, paired against the v3 on run.

| ablation | 1-30 | 31-100 | 101-200 | all |
|---|---|---|---|---|
| B no_steal | **-20 +-17** | -21 +-76 | +24 +-37 | -17 +-84 |
| B no_fbet | +9 +-18 | -39 +-70 | +23 +-40 | -7 +-82 |
| B no_agg | +1 +-11 | +27 +-31 | +6 +-14 | +33 +-37 |
| B no_size | +5 +-8 | +5 +-36 | +13 +-20 | +23 +-45 |
| A no_steal | **+15 +-12** | +1 +-67 | +14 +-33 | +30 +-75 |
| A no_fbet | **+37 +-14** | **+107 +-86** | -18 +-42 | **+127 +-95** |
| A no_agg | +4 +-11 | +54 +-64 | -25 +-29 | +33 +-70 |
| A no_size | -4 +-8 | -14 +-59 | -22 +-30 | -40 +-66 |

Reading:
- Fold-to-bet is the earner against a seat that over-folds (A): +127 chips a match. Against B,
  which folds about as often as the prior, it does nothing either way. That is the behaviour we want.
- Steal width has a sign that depends on the read. It earns against A, which defends its blind less
  than the prior. It costs against B, which defends more, because there the counter tightened our
  button opens and threw away steal equity that our postflop play would have won. Change: the steal
  counter now only widens. A wide blind defence no longer tightens our opens.
- The aggression read (bluff-catch wider against bettors, fold more against passive bettors) is mildly positive on both.
- Size tell: no clear sign (+23 on B, -40 on A, both inside noise). Kept, but it is the weakest read
  because it needs river showdowns.

### v4: 8-max against every target (50 deals x 8 rotations = 400 tables per arm, seed 41), steal now widen-only
`./batch.sh v4 8 50 41 A B C D E` (`--players 8 --tables 50 --seed 41`, on/off pairs)

| target | pts on / off (diff) | 1-30 | 31-100 | 101-200 | all (chips) |
|---|---|---|---|---|---|
| A | 5.243 / 5.133 (+0.110) | +16 +-60 | +208 +-237 | +704 +-739 | **+928 +-815** |
| B | 5.198 / 5.264 (-0.066) | +17 +-62 | +73 +-221 | -137 +-696 | -47 +-772 |
| C | 5.165 / 5.242 (-0.077) | +18 +-63 | +64 +-192 | +524 +-678 | +605 +-723 |
| D | 5.209 / 5.291 (-0.082) | +10 +-57 | -127 +-226 | +281 +-750 | +163 +-833 |
| E | 5.365 / 5.267 (+0.098) | +15 +-57 | +77 +-201 | +465 +-762 | +557 +-830 |

- The chip gain grows with the hand window, as learning should: the five-target mean is about +15
  chips in 1-30, +60 in 31-100 and +370 in 101-200. Points move within their +-0.25 noise. 400 tables
  per arm cannot resolve a points difference at 8-max, so the final run uses more.
- At 8-max most of what the counters see is the pool, not the target. Averaged over all opponents
  (2,800 seat-reads, counters off): VPIP .26, PFR .17, folds to a postflop bet 60%, bets 41% when checked to.
  Many pool bots time out or throw (tmo/exc columns), which is a forced fold, so they over-fold:
  the steal and fold-to-bet counters fire most at 8-max (A: steal 8.2k and fold_to_bet_hi 3.3k consultations in 31-100).
- Our 8-max finish profile: 1st 32% (the target's is 28%) but 2nd only 6%; the target finishes in the top 4 more evenly.

### v5: fold-to-bet read faster (prior weight 8 -> 5, dead zone .07 -> .06), aggression read prior 8 -> 6, station value-thinning stronger
Heads-up, seed 31, counters-on runs only (`./onlyon.sh v5 2 600 31 A B C D E`), paired against the v3 off runs.
Code that only runs with counters off is unchanged, so v3 off is still the off arm.

| target | pts on / off | 1-30 | 31-100 | 101-200 | all |
|---|---|---|---|---|---|
| A | 1.590 / 1.514 | **+49 +-23** | **+292 +-108** | -38 +-47 | **+303 +-119** |
| B | 1.593 / 1.603 | -13 +-28 | -28 +-87 | +1 +-42 | -40 +-98 |
| C | 1.641 / 1.633 | **+64 +-48** | -35 +-83 | +1 +-7 | +30 +-96 |
| D | 1.584 / 1.568 | +18 +-24 | +74 +-94 | -29 +-41 | +63 +-104 |
| E | 1.557 / 1.523 | +22 +-26 | +93 +-94 | +18 +-41 | **+133 +-106** |

v5 on minus v3 on: A +87, B +13, C +10, D +50, E -73 chips a match, all inside noise. The changes are kept
(their mean is positive), but this run does not prove them.

Checks: replay_test.py shows identical actions for the same seeds (seat seed, and an external
`bot.rng` reseed); different seeds give different actions. Switch-off demo: a seat folds 75% to bets
for 40 spots, then 20% for 60 spots. The bot's working fold-to-bet read goes
.71 .69 .67 .64 | .48 .45 .41 .40 .39 .36 at spots 10..100. So the bluff-more counter is on by spot 10, off
by spot 60 (back at the .45 prior) and has flipped to station mode by spot 70.

### v5: 3-handed against target A (200 deals x 3 rotations = 600 tables per arm, seed 61)
`./pair.sh v5_3p_A A 3 200 61`. pts on 2.185 +-0.059, off 2.110 +-0.064 (+0.075); target A 2.158.
Chips on-off: 1-30 +30 +-33, **31-100 +268 +-189**, 101-200 +62 +-160, **all +360 +-250**.
Three-handed the counters fire on both the target and one pool bot: fold_to_bet_hi 20k, steal 9.9k, opener_width 8.8k, aggressive 6.8k, station 3.3k.

### v6: new check-raise read ('xr': raises when facing a postflop bet, prior .12, weight 8)
It scales the extra penalty for facing a raise. Against a seat that raises light, call its raises
lighter (x0.35 at most); against one that raises only strong hands, fold more (x1.6 at most).
Heads-up, seed 31, v6 on minus v5 on: A -17 +-28, B +3 +-11, C +7 +-13, D 0, E 0 chips a match, so it is neutral.
Raise-when-facing-a-bet reads: A .02, B .05, **C .50**, D .04, E .04. The read fires correctly:
C raises half the time it faces a bet (call its raises lighter), and the others almost never do
(so their raises are strong). Facing a raise is rare, though, so the chips at stake are small. Kept.

### Base-game change v7: ICM-aware all-in margins (affects both arms)
With 8 alive, the points table 10/7/5/4/3/2/1/0 makes chips worth less than their face value. Stack-off
margins: +.045 equity (4+ alive, was .02), and a shove-EV risk premium of 6% of the stake (was 4%).
Test, counters on in both, paired: `BOTMOD=rival_v6|rival_v7 ... --players 8 --tables 150 --seed 71 --target A`.
v7 5.330 vs v6 5.291 pts (+0.04); chips -70 +-309. That is within noise, but in the direction ICM predicts
(fewer chips, better finishes). Kept.
Where the bot busts at 8-max (v7, 1200 tables): by blind level 0..7: 87, 70, 97, **197**, 133, 112, 61, 30.
The peak is level 3 (50/100, about 20 bb stacks), the push/fold phase. Finish profile 34/7/10/11/10/12/11/5 %
against the target's 26/14/15/15/11/10/6/4. We take more 1sts than the target and fewer 2nd-4th places.

### v8 (rejected): stronger ICM (+.07 equity and a 10% premium with 5+ alive)
Same 8-max test (seed 71, 1200 tables): v8 5.324 vs v7 5.330 pts, chips -190 +-324. No gain, so v7 stays.
3-handed, v7 on vs v5 on (seed 61): +20 +-88 chips (neutral). v7 on vs v5 off: +380 +-248.

### Frozen: v7 = rival_bot.py, md5 ee30b9a61161cdbf3c126a6c345bac70
harness: `python3 harness.py rival_bot` gives 0 exceptions, 0 illegal, mean 35 us, median 33 us,
p99 93-190 us. The max varies run to run (0.5-2 ms, up to 4.6 ms with gc disabled) while the
machine's load average is 13. Timing each observation three times and taking the minimum puts
the deterministic worst case at about 90 us, so the spikes are the scheduler preempting us, not
the bot.
Final evaluation uses fresh seeds never used in tuning: HU seed 201 (800 deals, 1600 matches per arm),
3-handed seed 202 (300 deals, 900 tables), 8-max seed 203 (150 deals, 1200 tables).

### FINAL (frozen v7, md5 ee30b9a6...): heads-up
`./batch.sh fin 2 800 201 A B C D E` (`--players 2 --tables 800 --seed 201`, on/off pair per target)
#### Heads-up, seed 201: counters on minus off, chips per table (95% interval)

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 1.584 / 1.511 (+0.073) | **+71 +-22** | **+203 +-89** | +18 +-39 | **+292 +-100** | 1600 |
| B | 1.611 / 1.605 (+0.006) | +12 +-25 | +18 +-75 | -7 +-33 | +22 +-88 | 1600 |
| C | 1.643 / 1.620 (+0.023) | **+47 +-41** | +47 +-74 | -2 +-5 | **+92 +-84** | 1600 |
| D | 1.583 / 1.583 (+0.000) | +17 +-21 | -12 +-81 | -8 +-41 | -2 +-91 | 1600 |
| E | 1.564 / 1.534 (+0.030) | +13 +-23 | **+115 +-81** | -8 +-41 | **+120 +-93** | 1600 |

Counters consulted while active (counters-on runs, summed over targets), by window:
- 1-30: fold_to_bet_hi 121827, aggressive 49675, station 26464, steal 16168, size_tell_small 5892, passive 5400, light_3bet 5377, size_tell_big 2952, fold_to_3bet 1217
- 31-100: fold_to_bet_hi 147444, aggressive 50250, station 16931, steal 16745, size_tell_small 16276, fold_to_3bet 12326, light_3bet 8613, size_tell_big 6108, passive 5433
- 101-200: call_shove 968, fold_to_bet_hi 444, fold_to_3bet 256, aggressive 75, size_tell_small 40, station 17, value_tighten 16, steal 13, size_tell_big 13

Target reads at the end of each match (counters-off arm, averaged over 1600 matches):
- A: hands=51.90 vpip=0.72 pfr=0.52 open_r=1.21 cont_r=0.91 3b_r=1.36 f3b=0.61 shove_f=0.02 callsh_r=1.33 fbet_raw=0.71 fbet=0.60 agg_raw=0.61 agg=0.55 bc_s=0.04 bc_b=-0.00 vcall=0.01 xr_raw=0.02
- B: hands=43.34 vpip=0.80 pfr=0.49 open_r=1.19 cont_r=1.13 3b_r=1.20 f3b=0.63 shove_f=0.06 callsh_r=1.24 fbet_raw=0.55 fbet=0.51 agg_raw=0.31 agg=0.32 bc_s=0.01 bc_b=-0.02 vcall=0.03 xr_raw=0.04
- C: hands=28.21 vpip=0.85 pfr=0.51 open_r=1.19 cont_r=1.30 3b_r=1.53 f3b=0.57 shove_f=0.02 callsh_r=1.42 fbet_raw=0.32 fbet=0.41 agg_raw=0.91 agg=0.74 bc_s=0.10 bc_b=0.03 vcall=0.01 xr_raw=0.54
- D: hands=50.44 vpip=0.72 pfr=0.52 open_r=1.21 cont_r=0.92 3b_r=1.36 f3b=0.67 shove_f=0.02 callsh_r=1.36 fbet_raw=0.61 fbet=0.55 agg_raw=0.43 agg=0.41 bc_s=0.02 bc_b=-0.02 vcall=0.03 xr_raw=0.03
- E: hands=49.55 vpip=0.72 pfr=0.52 open_r=1.21 cont_r=0.92 3b_r=1.35 f3b=0.67 shove_f=0.02 callsh_r=1.33 fbet_raw=0.61 fbet=0.54 agg_raw=0.61 agg=0.55 bc_s=0.04 bc_b=-0.02 vcall=0.03 xr_raw=0.04

### FINAL: 3-handed (target + challenger + one pool bot)
`./batch.sh fin 3 300 202 A B C D E` (`--players 3 --tables 300 --seed 202`)

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 2.199 / 2.167 (+0.032) | +31 +-34 | **+189 +-159** | -61 +-138 | +160 +-220 | 900 |
| B | 2.198 / 2.132 (+0.066) | +33 +-39 | **+221 +-129** | -13 +-133 | **+240 +-192** | 900 |
| C | 2.242 / 2.170 (+0.072) | +30 +-42 | **+320 +-154** | -96 +-134 | **+253 +-213** | 900 |
| D | 2.256 / 2.224 (+0.032) | +25 +-35 | +86 +-144 | +35 +-136 | +147 +-204 | 900 |
| E | 2.211 / 2.181 (+0.030) | +12 +-36 | +121 +-148 | +87 +-131 | **+220 +-201** | 900 |

Counters consulted while active (counters-on runs, summed over targets), by window:
- 1-30: fold_to_bet_hi 34740, steal 21695, opener_width 16004, station 15393, aggressive 13856, passive 3201, light_3bet 1983, size_tell_small 1014, fold_to_3bet 780
- 31-100: fold_to_bet_hi 91837, steal 45193, opener_width 34208, aggressive 27252, station 17222, fold_to_3bet 11145, size_tell_small 6074, passive 5012, light_3bet 4703
- 101-200: fold_to_bet_hi 4550, call_shove 3459, fold_to_3bet 2484, steal 2189, opener_width 1608, aggressive 803, station 408, size_tell_small 290, tight_shover 263

Three-handed, every target shows the learning gain, and it is largest in 31-100, once the reads have built up.
In 101-200 most tables are already heads-up or decided, so that window is noisy and near zero.

### FINAL: 8-max (target + challenger + six pool bots)
`./batch.sh fin 8 150 203 A B C D E` (`--players 8 --tables 150 --seed 203`)

| target | pts on / off (diff) | hands 1-30 | 31-100 | 101-200 | all hands | tables per arm |
|---|---|---|---|---|---|---|
| A | 5.283 / 5.089 (+0.194) | +34 +-34 | **+161 +-123** | **+1131 +-428** | **+1326 +-468** | 1200 |
| B | 5.190 / 5.075 (+0.115) | +37 +-37 | **+155 +-119** | +375 +-399 | **+567 +-434** | 1200 |
| C | 5.229 / 5.104 (+0.125) | +17 +-32 | **+211 +-124** | **+721 +-394** | **+949 +-431** | 1200 |
| D | 5.275 / 5.245 (+0.030) | **+38 +-35** | +52 +-128 | **+540 +-414** | **+630 +-450** | 1200 |
| E | 5.231 / 5.207 (+0.024) | **+42 +-34** | +8 +-125 | **+716 +-411** | **+765 +-451** | 1200 |

Counters consulted while active (counters-on runs, summed over targets), by window:
- 1-30: steal 42398, opener_width 17248, fold_to_bet_hi 16606, station 9306, aggressive 6316, passive 2919, light_3bet 1917, loose_shover 893, fold_to_3bet 363
- 31-100: steal 123435, fold_to_bet_hi 59943, opener_width 59277, station 18768, aggressive 16794, fold_to_3bet 10437, passive 6667, light_3bet 6528, call_shove 3684
- 101-200: steal 58423, fold_to_bet_hi 45620, opener_width 26394, call_shove 18262, fold_to_3bet 16252, station 10275, aggressive 9029, tight_shover 6114, passive 3327

Each arm's own points interval is about +-0.13-0.15, so a difference needs about +-0.19 to count. A's +0.19 is at that edge; the others are inside it.
The target's own score falls when our counters are on (A: 5.874 -> 5.667, D 5.415 -> 5.312, E 5.517 -> 5.448): part of what we win comes out of the target's pocket.
Pool reads at 8-max (8,400 seat-reads, counters off): VPIP .26, PFR .17, continue vs an open 0.81x the prior, fold to a bet 60%, bets 41% when checked to, raises a bet 5%.
