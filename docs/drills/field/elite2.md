# rival_bot build log

Frozen: `rival_bot.py`, md5 `70c29e1754bbe6a555cea331468756f3` (FROZEN.md5), frozen at T0+104 min
(2026-11-02 01:28:47 local). T0 = 1793594638 (23:43:58). File 144 KB, import 0.19 s, ~11 MB RSS.
Pure standard library. All code, including the evaluator, the tables, the simulator and every test
opponent, was written here from scratch.

## What the bot is

An ICM-aware bot that models each opponent's range. It does not try to solve the game. In order:

1. **Hand evaluator** (own design). A dict keyed by base-5 rank-multiset sums covers every 5–7 card
   rank multiset (73,775 entries, built at import in ~0.2 s). An 8192-entry suit-mask table covers
   flushes and straight flushes. Speed is 1.34 µs per 7-card eval, and it matched a brute-force
   5-of-7 evaluator on 20,000 random hands.
2. **Precomputed preflop tables** (pre.py, MC, embedded as 12-bit hex, ~89 KB):
   - a 169×169 heads-up equity matrix (1,500 samples per class pair);
   - equity of each of the 169 classes against 1–7 random hands (4,000 samples each).
   From these, the bot builds cumulative tables at import, so the equity of any hand against
   "top x% of hands" costs O(1). It also builds caller tables: for each perceived shove width, the
   fraction of hands that have the required equity.
3. **Exact, O(n) ICM for this payout table.** 10/7/5/4/3/2/1/0 is linear (8−place) plus a bonus of
   +3 for 1st and +1 for 2nd. Under Malmuth–Harville (Plackett–Luce), P(i finishes above j) =
   s_i/(s_i+s_j). Together these give:
   E_i = (8−k) + Σ_j s_i/(s_i+s_j) + 3·s_i/T + Σ_j (s_j/T)·s_i/(T−s_j).
   Every preflop all-in, call-off and commit decision is therefore valued in tournament points,
   not chips, at about 3 µs per scenario. The same formula covers bots still alive at the
   200-hand cap.
4. **Preflop**:
   - **≤14 bb effective, unopened pot:** push or fold by ICM EV. Each player behind calls with a
     probability taken from the caller tables. Inputs are the perceived width of our shove (by
     players behind and stack depth), the pot odds, and an ICM premium that is removed heads-up.
     This is blended with how often that seat has actually called big all-ins. A small "fold tax"
     stands in for blind pressure and fades out near the hand cap.
   - **Deeper, unopened pot:** position-based open ranges (2.2–2.6 bb, independent of hand),
     widened against blinds that fold to raises.
   - **Facing a raise:** 3-bet, call or fold by equity against the opener's estimated range. That
     range is a position prior × the seat's observed open rate. The bot adds out-of-position and
     implied-odds terms and occasional blocker 3-bet bluffs against wide, foldy openers.
   - **≤22 bb facing a raise, or any big bet:** shove, call or fold by ICM, using fold equity and a
     multiway equity approximation.
5. **Postflop**:
   - **Range enumeration:** opponent holdings are enumerated exactly, grouped by rank pair and
     flush class (about 91–260 groups), and weighted by the preflop range model.
   - **Range narrowing:** the bettor's range is narrowed to the top share by current hand value
     (share set by their observed aggression and bet size), plus a bluff share that grows with
     their aggression. Their earlier postflop calls narrow it further.
   - **Draws:** counted as outs, plus a small implied-odds term.
   - **Bet sizing:** chosen by EV over 0.4–1.1 pot (or all-in at low stack-to-pot ratio). The model
     assumes rational players continue less against bigger bets and random players do not care,
     so value sizing goes up against stations and random bots, and bluffing depends on observed
     fold rates.
   - **Committing calls:** use an ICM equity requirement, not raw pot odds.
6. **Opponent model**: the bot replays every hand's betting from `obs.history` with its own engine.
   It is robust to blind posts being in or out of the history and fills in the hand from
   `hand_end` when a history is supplied. Per seat it tracks VPIP, PFR, open rate, fold/call/raise
   versus raises, all-in calling rate, postflop aggression, fold-to-bet and raise-to-bet. All of it
   uses Bayesian priors, so it adapts within the 200 hands. The stats drive the range widths,
   which is why a player who steals or 3-bets a lot is automatically played back at more
   (counter-exploitation).
7. **Safety**:
   - every `act` is wrapped; any exception returns check, else fold;
   - a legality fixer clamps raise amounts to `[min_raise, max_raise]`, rounds near-all-in raises
     up to all-in, and never folds when a check is legal;
   - `gc.freeze()` after import keeps garbage-collection passes from walking the tables.

## Latency (pure Python, this host)

- Intrinsic cost (min of 4 runs per obs, 1,500 harness observations): mean 45 µs, p99 112 µs,
  max 153 µs. Preflop mean 25 µs; flop, turn and river means 50–66 µs.
- `harness.py rival_bot` (harness_final.txt, seeds 1–3): 0 exceptions, 0 illegal actions,
  fold_when_check_legal 0, mean 69–71 µs, p99 176–196 µs.
- The harness max of 0.5–1.5 ms is host scheduling jitter, not our code. A bare timing loop with
  no work also showed gaps up to 1.3 ms. Load average was 8 to 50 during the session, from other
  jobs.
- In-simulation max latencies of tens of ms, and two single multi-second stalls during the last
  runs, line up with the host being overloaded (load average 46–53, memory nearly full). The same
  observations re-time at 100–300 µs.

## Test rig

- **sim.py:** 8-seat NLHE sit-and-go engine with side pots, split pots, all-in rules, moving
  button, blinds 10/20 … 200/400 every 25 hands, 200-hand cap, and exact Malmuth–Harville ICM for
  survivors at the cap. Points are 10/7/5/4/3/2/1/0. Options: blind posts in the history, and a
  `hand_end` result that is full, partial or None.
- **Opponents (opps.py):**

  | Bot | What it does |
  |---|---|
  | RandomBot | uniform over legal actions, random sizes |
  | Station | calls almost everything |
  | EqBot | MC equity vs random hands; tight and loose variants |
  | Maniac | raises most hands, bets postflop often |
  | Rock | premium hands only |
  | PushFold | shove-or-fold by a hand score |
  | Exploiter | tracks fold rates, steals and bluffs foldy seats |
  | NashBot | chip-EV push/fold plus a solid deep game with MC postflop; two variants |
  | LAG | loose-aggressive, frequent 3-bets and barrels |
  | Exploiter2 | stat-driven exploiter built on my own replay and stat code: steals vs foldy blinds, light 3-bets vs openers who fold to raises, c-bets and barrels vs players who fold to bets, value only vs stations |
  | Barreler | Nash preflop, then bets 2/3 pot whenever checked to and min-raises bets as bluffs; punishes over-folding |
  | Earlier versions of this bot | v1–v7, plus AGG and FOLD_TAX variants |

- **Fields:**

  | Field | Seats besides the hero |
  |---|---|
  | mixed | random, station, eqbot, maniac, rock, pushfold, exploiter |
  | elite | v2, nash, nash2, lag, exploiter, v2agg, eqtight |
  | gauntlet | v3, nash, lag, exploiter2, v2agg, eqtight, random |
  | aggro | v5, barreler, lag, exploiter2, nash, random, maniac |
  | final (held out, not used for tuning) | v5, nash2, barreler, exploiter2, lag, station, random |

- **Measurement:**
  - Duplicate deals: the same deck sequence per table seed, the hero in 3 seat rotations per seed.
  - From b2 onward, every bot's RNG is reseeded per (seed, seat). Candidates then play identical
    cards against identically seeded opponents, which roughly halved the CI on paired
    differences.
  - "±" below is a 95% CI (1.96·SE over seed groups). Points are per table; the field average
    is 4.0.

## Timeline and results

| T0+ | Step |
|---|---|
| 4 min | Evaluator written and verified |
| 7 min | Preflop tables done (3.3 min of MC) |
| 10 min | Simulator and first opponents |
| 13 min | **v1**: first full bot. Mixed field, 300 seeds×2: v1 **7.37 ± 0.26** (pushfold 5.23, eqbot 5.13, exploiter 5.01, rock 4.71, maniac 1.68, random 1.58, station 1.29) |
| 18 min | **v2**: callers modelled against a perceived shove width; fold tax. Push charts had been far too tight and, from the SB, too loose (100%) |
| 22 min | **v3**: suit-bitmask enumeration (verified identical, 15–25% faster); position priors for open and shove ranges |
| 25 min | **v4**: size-aware bet EV (rational vs random continuation), cleaner ICM commit maths |
| 28–32 min | **v5**: narrowing by earlier calls, cap-aware fold tax, robust blind-post detection, stations told apart from random bots by aggression. **v6**: bluff share grows with bettor aggression; observed all-in calling rate |
| 45–55 min | **v7**: raisers who flat a re-raise get narrowed ranges; value raises guarded by the ICM requirement; caller ICM premium lowered and zeroed heads-up (heads-up SB shove went from 100% of hands at 10 bb to 78%); higher value-raise thresholds on later streets |
| 60–69 min | **v8** (faster random-bot detection) was clearly worse. **v9** parametrised randomness detection; turning it down or off was clearly better in mixed |
| 69–82 min | **v10**: preflop equity against loose players becomes a proper mixture (tight range plus random). **v10a** = v10 with randomness detection only at VPIP above ~0.55 |
| 82–88 min | PUSH_BB 14 vs 17 and BL0 0.12 vs 0.25: no difference within noise; defaults kept |
| 88 min | `rival_bot.py` = v10a. Held-out final field run |
| 104 min | Robustness run under other engine conventions: 0 errors with exceptions surfaced; frozen |

Paired comparisons. Hero slot, 3 rotations per seed. "Seeds" is seed groups:

| Batch | Field | Seeds | Result |
|---|---|---|---|
| b1 | gauntlet | 500 | v3 5.26 ± .15; v4 5.39 ± .16 (v4−v3 +0.13 ± 0.19) |
| b1 | elite | 500 | v3 5.47; v4 5.52 (+0.04 ± 0.16) |
| b2 | gauntlet | 500 | v4 5.47, v5 5.50, v6 5.42 (diffs ±0.13, n.s.) |
| b2 | mixed | 500 | v4 7.46, v5 7.57 (+0.11 ± 0.11), v6 7.55 |
| b2 | elite | 500 | v4 5.56, v5 5.48, v6 5.48 (−0.08 ± 0.14, n.s.) |
| b3 | aggro | 500 | v5 5.94, v7 5.98 (+0.05 ± 0.07) |
| b3 | gauntlet | 500 | v7 +0.08 ± 0.09 |
| b3 | mixed | 500 | v7 −0.06 ± 0.06 |
| b4 | mixed | 500 | v8 −0.32 ± 0.17 vs v7: **rejected** |
| b4 | gauntlet | 500 | v8 −0.04 ± 0.15 |
| b4 | aggro | 500 | v8 −0.07 ± 0.14 |
| b5 | mixed | 500 | v9 (= v7) 7.51; v9a (less randomness) +0.17 ± 0.12; v9off +0.20 ± 0.13 |
| b6 | mixed | 500 | v10off 7.77; v10 −0.15 ± 0.13; v10a −0.08 ± 0.10 |
| b6 | aggro | 500 | v10off 5.97; v10 −0.12 ± 0.09; v10a **+0.05 ± 0.05** |
| b6 | gauntlet | 500 | v10off 5.31; v10 +0.06 ± 0.09; v10a +0.03 ± 0.05 |
| b7 | gauntlet | 450 | v10a 5.27; PUSH_BB=17 +0.01 ± 0.10; BL0=0.25 −0.03 ± 0.09 |
| b7 | mixed | 450 | v10a 7.58; PUSH_BB=17 −0.04 ± 0.07; BL0=0.25 +0.02 ± 0.08 |
| b8 (held out) | final | 500 | **rival_bot 6.19 ± 0.15**; v5 6.14 ± 0.14 (v5−rb −0.05 ± 0.11); v1 6.04 ± 0.15 (v1−rb −0.15 ± 0.17) |

Simultaneous-variant table, t1 (4 copies of v7 with different parameters, plus nash, exploiter2,
random and barreler; 300 seeds × 4 rotations): every variant scored 5.0–5.2 and the other bots
3.5–4.0. Random scored 0.6.

Robustness, gauntlet, 40 seeds × 3, DEBUG on so exceptions would surface:

| hand_end result | Blind posts in history | Score | Errors |
|---|---|---|---|
| full | no | 5.73 ± 0.51 | 0 |
| None | yes | 4.97 ± 0.43 | 0 |
| partial | no | 5.32 ± 0.58 | 0 |

The bot plays correctly under all three conventions. Without a full `hand_end` history it learns
less about how players respond to its own shoves.

How the bot looks to an opponent's model, gauntlet field, 40 tables: VPIP 0.37–0.39, PFR
0.24–0.26, open 0.37–0.40, fold to preflop raise 0.64, postflop aggression 0.47–0.51, fold to
postflop bet 0.63–0.67. The last figure was checked against Barreler, a bot that bets every time
it is checked to. Barreler finishes well below the hero (3.6 vs 5.2), so the folding is not being
exploited.

## Honest caveats

- **Noise.** A table's points have SD ≈ 3.3, so most version-to-version differences after v4 are
  inside the noise. The progression v1 → v5 → rival_bot on the held-out field is monotone but not
  individually significant. The only significant findings are:
  - treating loose players as fully random was a mistake (v8, v9);
  - the bot beats every non-self opponent by a wide margin in every field.
- **Test opponents.** They are my own constructions. The strongest opposition in testing was
  earlier versions of this bot. Real elite bots may differ.
- **Not built:**
  - showdown-based learning (the result format is unknown; the code tallies `showdown` dicts but
    does not act on them);
  - multi-street planning;
  - a solved deep-stack strategy.
- **ICM tightness.** The ICM push/fold is deliberately tight when 7–8 players are alive. With this
  payout table, busting first is worth 0 against a 4-point average, so a full-stack flip is
  strongly −EV early.
