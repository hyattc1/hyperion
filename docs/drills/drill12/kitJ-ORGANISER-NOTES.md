# Organiser notes (not for teams)

## The twist in one paragraph

Each player has a trailing stop at 60% of their highest closing stack. Close a hand below it and you are eliminated, even with thousands of chips, and those chips are split among the survivors. This moves stack mechanics and the link between chips and points, which the last three events' twists left alone. The betting, cards and showdown are ordinary hold'em, so the dealer change is small, while the meaning of a chip changes completely.

## Why it is interesting

**Depth is room, not stack.** Room is stack minus stop. At the start it is 800 chips, so everyone is 40 big blinds deep, not 100. A stack at its peak always has room of 40% of itself, and a stack that has fallen may have almost none.

**Past the stop, chips behind are worthless.** Once a player's chips behind are under their stop, folding is elimination. Losing any further chips costs nothing more. So they should never fold, and they should bet it all.

**A short stack can eliminate a big one.** A 6,000 stack at its peak has room of 2,400, so a 2,500 shove is for its life. The usual big-stack bullying inverts, because the leader's risk grows with its stack.

**Everyone's room is public.** Bets can be sized to a named opponent's room. A bet of just over the room of a player with 3,000 chips is a tournament-life decision for that player, at a fraction of the cost of a real all-in.

**Players past their stop never fold if they understand the game.** That removes bluffing against them and adds thin value betting. Bots can read this from the same public numbers.

**Blinds become a deadline.** A player whose room is under the blind they must post is past the stop before they see their cards, unless they win the hand. This is known a hand ahead, and it can be attacked.

**Survival is paid.** Every elimination that leaves chips pays a dividend. When a big stack blows up, it can rescue a short stack on the ledge. So there is a real value in waiting, and it competes with the pressure from rising blinds.

**The ICM calculator misleads, and that is deliberate.** It is in the kit as promised and takes chips only. Our measurement of how far it misprices is below.

**The cap changes the end.** With two left, being stopped out and being behind at hand 200 both mean second place. So in the last hands the shorter stack has nothing to lose from its stop.

## What a naive bot gets wrong

1. It folds past its stop and eliminates itself with chips it could have used.
2. It reads SPR and depth from `stack`, so it plays 100 big blinds of poker with 40 big blinds of risk.
3. It sizes a bet that takes it just past its stop, rather than going all the way or staying out.
4. It treats the chip leader as safe, and calls a shove that eliminates it.
5. It bluffs a player who cannot fold.
6. It uses plain ICM as the value of a stack.
7. It hard-codes chip thresholds, while the interface is in big blinds that change with the level.

## Measurements

Fair share is 39 / 8 = 4.875 points per table. Figures are mean points with 95% half-widths. `tight.py` is a decent hold'em bot that ignores the stop, and `deskhand.py` adds rules for it. The two throwaway bots here, folder and shover, are not in the kit: folder only checks or folds, and shover always shoves.

| Lineup | Tables | Result |
|---|---|---|
| 7 tight + 1 deskhand | 500 | deskhand 7.11 +/- 0.47, tight 4.56 +/- 0.14 |
| 7 deskhand + 1 tight | 500 | tight 2.62 +/- 0.25, deskhand 5.20 +/- 0.15 |
| 4 deskhand + 4 tight | 500 | deskhand 6.18 +/- 0.21, tight 3.58 +/- 0.15 |
| 2 each of random, station, tight, deskhand | 1000 | deskhand 9.15, tight 6.87, random 2.00, station 1.49 |
| 7 tight + 1 folder | 500 | folder 3.49 +/- 0.14 |
| 7 deskhand + 1 folder | 500 | folder 1.89 +/- 0.09 |
| 7 tight + 1 shover | 500 | shover 0.51 +/- 0.12 |
| 7 deskhand + 1 shover | 500 | shover 0.38 +/- 0.10 |

So a plain hold'em bot cannot ignore the twist: it is down about 2.3 points per table against a field that plays the stop. The rules that win are not degenerate either, since neither pure folding nor pure shoving comes close to fair share in a competent field. Against tight bots, folding gets 3.49, which is less than fair share, but higher than I would like and worth watching. That bot survives on dividends.

**One rule at a time.** Each row is 1 patched copy of `tight.py` against 7 plain ones, over 2,000 tables.

| Patch | Points |
|---|---|
| Past the stop: never fold, shove | 5.53 +/- 0.20 |
| Would pass the stop to call: need a strong hand, then shove | 4.99 +/- 0.18 |
| Both | 5.99 +/- 0.20 |

The first patch takes 2 lines and is clearly worth having. The second is not clearly better than fair share alone, and it appears to add value on top of the first.

**How wrong is plain ICM?** 3,000 tables of 4 tight + 4 deskhand. At the close of hand 125, I took every survivor's plain-ICM equity, then compared it with the points they actually scored, bucketed by room as a share of stack.

| Room / stack | Players | Plain ICM | Actual points | Gap |
|---|---|---|---|---|
| under 5% | 170 | 5.51 | 3.27 | -2.24 |
| 5-10% | 229 | 5.81 | 4.10 | -1.71 |
| 10-20% | 750 | 5.98 | 4.92 | -1.05 |
| 20-30% | 1948 | 6.70 | 6.18 | -0.51 |
| 30-40% | 10394 | 7.93 | 8.18 | +0.25 |

Plain ICM overvalues a stack near its stop by up to 2 points or more. One caveat: these buckets mix the two bots, and weaker play may lead to low room, so not all of the gap is the stop itself. The direction and the scale are clear enough to warn teams through their own testing, without saying so in the handout. The handout says only that the calculator does not know about stops.

## How tables play out

- With competent fields, roughly 70% to 90% of tables reach the hand-200 cap, usually with about 2 survivors. In the mixed field it is 62%. So first against second is often decided by chips at the cap, which is a meaningful part of the scoring.
- Most eliminations leave chips behind: 70% in the mixed field and 59% in 4 deskhand + 4 tight. That is the twist working as intended.
- I first tried a gentler blind schedule, ending at 120/240, and 86% to 99.8% of tables reached the cap. The current one, ending at 250/500, is steeper for that reason. If you want fewer cap finishes, steepen it further, but the deskhand edge should be rechecked after.
- `deskhand.py` is deliberately only reasonable. It uses simple hand-strength rules with no opponent modelling, and I expect a good team to beat it.

## What teams must not miss

- `"r3"` is a raise-by, on top of the call. It is not a raise-to.
- Amounts are big blinds of the current level and change when the level rises. `v.bb` converts them.
- `stack` excludes chips already in the pot. So `stack < floor` is exactly the test for "folding now eliminates me".
- The check/fold fallback makes no exception for the stop. A timeout past the stop is elimination, so a slow bot is punished harder here than usual.
- `min_raise` and `max_raise` being 0.0 is the only sign that raising is closed.
- Tags change at each table, so opponent tracking across tables is impossible by design. Within a table, it is possible.
- Imports must be at the top of a file. A helper imported inside `decide` fails.
- The event's sandbox does not have `engine`. Copy `hand_eval.py` into the zip.
- `icm.py` copied alone needs its payouts passed in.
- ICM takes about 0.4 ms for 8 stacks, so calling it live uses over a third of the budget. Precompute or use it short-handed.

## Things the real event must supply

The local simulator keeps all bots in one process, and it does not isolate them. The event's runner needs real sandboxes with no network, a read-only bot folder, and its own dedicated cores if the wall clock is to be fair. The README states this as how the event runs, so it must be true on the day.

Expect some stray timeouts on any machine that is not dedicated. On this busy one, the rate was about 0.04% of decisions. Under this twist a stray fold past the stop eliminates a bot, so the event's machine matters.
