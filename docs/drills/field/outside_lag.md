# Build log: rival_bot (team "LAG grinders")

Frozen at minute 39 (2366 s after T0). md5 is in FROZEN.md5: `7f2cf88729b2db29a6d7d4c425843cce`.
After that only logs and snapshots were written.

## What I built
- `rival_bot.py`: `class Bot(Agent)`, stdlib only. No Monte Carlo at decision time. Import takes about 1 ms.
  The slowest deterministic decision measured (min of 3 runs per obs, 20k random obs) was 85 us;
  median 12 us.
  - **Preflop.** A table of all 169 starting-hand types, ranked by a hand-written score that approximates equity
    against a random hand and weighted by combos, gives each hand a percentile.
    - Unopened pots: LAG open ranges keyed on how many players are left to act
      (UTG ~20%, CO ~50%, BTN ~65%, SB ~85%).
    - Steal width follows the fold rate the bot has observed for the players behind.
    - At 13 bb effective or less: push/fold, with Nash-flavoured push widths scaled by stack depth.
    - Facing one raise at 13–28 bb: re-shove a wide range, wider still against late-position openers and
      loose-raising seats.
    - Deeper: value 3-bet, plus light 3-bets with suited hands 25% of the time.
    - Tight responses to 3-bets and 4-bets.
    - **All-in calls are ICM-disciplined.** The bot calls only when equity >= price + margin.
      - Equity comes from a 9x6 grid (hand percentile x villain range width) that I computed with my own
        Monte Carlo and the sim evaluator, then hardcoded and smoothed.
      - The margin is up to 0.40. It scales with the fraction of my stack at risk and shrinks below about 4 bb.
      - AA and KK always call.
    - Late in the game (5 or fewer players left, or hand 150+): when I cover everyone, or everyone behind me,
      open and push ranges widen by 1.25. This puts ICM pressure on the medium stacks.
  - **Postflop.** Heuristic made-hand strength:
    - Inputs: category, top/middle/bottom pair, kicker, overpair or set, flush and straight texture penalties,
      and a multiway discount.
    - Draw equity from flush and straight outs (counted by completing ranks) and overcards.
    - Value-bet at 0.6+, bigger at 0.82+. Shove when SPR is low. Semi-bluff draws.
    - With weak hands it c-bets and barrels when checked to: as aggressor 80/60/45% by street, in position
      55/45/35%. These rates are scaled by the opponent's observed fold rate.
    - Calls are priced (pot odds + 0.07), and a bettor's aggression stat loosens them.
    - Deep-stack brake: no calls of bets over 25 bb that are over 30% of my stack with one pair.
  - Opponent stats per seat, from `history`: actions, raises, folds, calls, and preflop raise frequency.
    Stats reset every table.
  - Every action is clamped to `legal` and `[min_raise, max_raise]`, with a try/except fallback to check/fold.
- `sim.py`: my own 8-seat NLHE SNG engine.
  - Rules: blinds rising every 25 hands (the BRIEF schedule), 200-hand cap, side pots, a 7-card evaluator
    (checked: AA v KK 82%, AKo v 22 48%), and finish points 10/7/5/4/3/2/1/0 with ICM at the cap.
  - Opponents I wrote: RandomBot, Station, Nit, TAG, Maniac, Jammer (push/fold), Weak.
  - Fields: default (those 7), `FIELD=tough` (3 TAG, 2 Nit, Jammer, Weak), and `FIELD=snaps`
    (snap_m15 and snap_m30 plus fish and regulars).
- `tune.py`: overrides the K_* knobs. `diag.py`: chip results per preflop line. `dist.py`: finish distribution.
  `eqgrid.txt`: the Monte Carlo equity grid.

## Timeline (minutes from T0)
- 0–3: read the brief and kit, planned the work.
- 3–5: wrote rival_bot v1 (preflop percentile table, push/fold, reshove, postflop heuristics).
  Harness clean, about 18 us mean.
- 5–6: wrote sim.py (engine plus 7 opponents). First test: 4.79 points over 40 tables.
- 7: 1000 tables gave 5.09 ± 0.10; the check/call control scored 2.03.
- 8: added knobs and fold-rate tracking. Bluff, open and call knobs showed no clear signal.
- 8–9: diag showed the leak: preflop calls of big raises and shoves lost about 300 chips each, and hero busted early
  (62 hands per table on average against TAG's 121).
- 9–13: added an ICM margin on committed calls and jams.
  Sweep at margin 0 / 0.04 / 0.08 / 0.12 / 0.17 / 0.23 / 0.30: 5.28 / 5.41 / 5.70 / 5.93 / 6.36 / 6.62 / 7.05.
  Split it into a margin for calling all-ins and one for jamming. Checked the evaluator.
- 13–15: snap_m15. All-in margin set at 0.45, jam margin 0.30.
- 15–17: widened preflop (seed 3, 1500 tables). Baseline 6.91. Open x1.25: 7.23. Push x1.3: 7.14. Reshove x1.4: 7.15.
  Combined: 7.24. Combined x1.5/1.6/1.8: 7.36.
  Postflop call margin -0.04 was worse (7.09); +0.06 was flat. Bluff x0.4 and x1.5 were both flat.
- 17–19: adaptive steal (fold rate of players behind): +0.1 to +0.18, noise level. Kept at 1.5.
  Weighted widening toward late position. Latency audit: worst code path about 113 us.
- 19–21: light 3-bet frequency and value thresholds: flat. All-in margin 0.55 vs 0.45: 7.52 vs 7.24.
- 22–25: AA/KK override (7.49 vs 7.37). Margin scaled by fraction of stack at risk (7.46 vs 7.38).
  Added the tough field: the bot scored 6.70 there and was still the best single bot. Tighter calls held up there too.
- 25–27: postflop stack-risk margin: flat or worse, left off. Push x1.8, reshove x2.0, cover-widen x1.6: all flat.
- 27–28: finish distribution: 41% wins, but a cluster of 4th places. Tried loosening calls as players bust:
  much worse (6.13 vs 7.48), left off.
- 28–30: measured true equity against ranges by Monte Carlo. The old formula overestimated by 0.07–0.16, so I
  replaced it with the grid. Margin retune with the grid: 0.2 / 0.35 / 0.5 / 0.65 gave 6.80 / 7.46 / 7.55 / 7.55.
  snap_m30.
- 31–33: tough field, margin 0.5 vs 0.3: 6.85 vs 6.67. Push zone 10/13/16 bb: 7.50/7.64/7.63 (kept 13).
  Premium override AA only / AA+KK / QQ+: 7.80/7.64/7.60.
- 33–35: chose margin 0.40 and AA+KK. Reasoning: in my field the bot is far above average, so survival is worth
  more than it will be against real opponents. The snaps field agreed: margin 0.25/0.40/0.55 gave 5.60/5.88/5.70.
- 35–38: ICM pressure when I cover the players behind: flat, enabled because the brief asks for it.
  Open size x0.9/x1.25: 7.54/7.41, kept x1.0. Ran 300 tables counting exceptions and illegal action kinds inside
  the engine: zero of each.
- 38–39: final validation, harness, freeze.

## Local results (points per table, mean of 10/7/5/4/3/2/1/0; the average seat scores 4.0)
| config | field | tables | mean | se |
|---|---|---|---|---|
| v1 (first build) | default | 1000 | 5.09 | 0.10 |
| _control (check/call) | default | 1500 | 1.96 | 0.05 |
| frozen | default, seed 41 | 1500 | 7.46 | 0.07 |
| frozen | default, seed 42 | 1500 | 7.50 | 0.07 |
| frozen minus K_BEHIND | default, seeds 21/22 | 1500 each | 7.55 / 7.60 | 0.07 |
| frozen | tough (3 TAG, 2 Nit, Jammer, Weak) | 1500 | 6.92 | 0.09 |
| frozen | snaps (with snap_m15 and snap_m30 at the table) | 1200 | 5.64 (seed 43), 5.88 (seed 23) | 0.09 |

How to read the noise: one run of 1500 tables has a standard error of about 0.07–0.08. Knob comparisons on the same
seed share seating and deck streams for a while, then drift apart, so I treated differences under about 0.15 as
noise. Only these effects were clearly real: the all-in discipline (+2 points overall), the wider preflop
ranges (+0.3), the equity grid (+0.1, small), and the rejected loosen-as-players-bust change (-1.3).

Caveats:
- All opponents are my own, and the field is fish-heavy. That rewards survival. It is why the all-in
  margin tuned so large. I set the frozen margin below the field's optimum on purpose.
- Timing spikes in the sim (max act 10–50 ms) also appeared for the 20 us control bot, so they are host jitter on the
  shared machine, not the bot.

## Harness (final)
See harness_final.txt: 2000 obs, 0 exceptions, 0 illegal, mean ~21 us, p99 ~75 us.

## Snapshots
- snap_m15.py: state at about minute 14. Old equity formula, all-in margin 0.45.
- snap_m30.py: state at minute 30. MC equity grid, margin 0.5.
- snap_m45.py: written at minute 40 as a byte-identical copy of the frozen rival_bot.py. The bot was frozen at
  minute 39, so this file is also its state at minute 45.
