# rival_bot build log

## What I built

The deliverable is one self-contained file, `rival_bot.py`, about 109 KB. It uses only the standard library. Import takes 0.2–0.5 s. The source is `bot_src.py`, and `build.py` embeds the preflop tables into it.
Supporting tools, all written from scratch here:

| file | purpose |
|---|---|
| `ev.py` | 7-card evaluator. The key is a sum of per-card constants: a base-5 rank multiset in the low 31 bits and 3-bit suit counters above it. One dict lookup covers non-flush hands and an 8192-entry table covers flushes. It needs no combinations and runs at about 0.4 µs per eval. Checked against an independent 5-card ranker on 20k random pairs and against best-of-21 on 3k random 7-card hands. |
| `gen_tables.py` | Offline Monte Carlo. It builds a 169×169 class-vs-class preflop equity matrix (800 deals per pair) and a 169×7 table of equity against k random hands (3000 deals each). Both are encoded as base64 12-bit values in `pfdata.txt` and embedded in the bot. |
| `sim.py` | 8-seat NLHE sit-and-go engine. It follows the BRIEF: 2000 chips, 25-hand levels, 200-hand cap, 10/7/5/4/3/2/1/0 points and Harville ICM at the cap. It handles side pots, heads-up blinds and min-raise rules, and same-hand busts are ordered by starting stack. It times every `act()`, counts exceptions and illegal actions, and folds on an illegal action as the rules do. |
| `opps.py` | Test opponents: random-legal, calling station, maniac, nit, TAG (tight/normal/loose), LAG, all-in-or-fold shover (normal and wide), **Thief** and **PFNash**. Thief is an adaptive exploiter: it tracks each seat's fold-to-raise and steals or 3-bets against folders, shoves wide when short, and barrels heads-up. PFNash plays TAG when deep and position-aware push/fold at 15 bb or less. Earlier versions of my own bot (`v1`, `v2*`), with aggressive or tight parameter sets, also serve as opponents. |
| `run.py`, `cmp.py` | Duplicate-deal runner. For each seed, 8 tables use the same deck seeds, with seating rotated so every bot plays every seat. All bot RNGs are seeded, so candidates replay the same deals and opponent seeds. `cmp.py` gives each candidate's mean ± SE (unit: one seed, 8 tables) and the paired difference ± SE against a baseline. |
| `harness.py` runs, `t_robust.py`, `t_lat.py`, `t_pftime.py`, `t_ranges.py`, `t_replay.py` | Legality, latency, mutated-observation robustness, push/call range printouts and replay-consistency checks. |

## The bot's approach

1. **Preflop, by equity and range rather than fixed charts.** I sort the 169 classes once, mostly by heads-up strength with some multiway playability. Every opponent range is modelled as a "top-x%" slice of that ordering, and `EQTOP[class][x]` is precomputed at import from the matrix. Each opponent's x comes from per-seat counters: open rate, 3-bet rate, shove rate, VPIP, PFR and a "wild" score that flags random or maniac bots. Opens depend on position and widen or tighten with the fold-to-raise and 3-bet rates of the players behind. Isolation raises over limpers, value 3-bets scaled to the opener's width, light 3-bets against foldy wide openers, and BB defence using pot odds all follow from the same estimate.
2. **ICM for every big decision.** These are shoves, calls of all-ins, re-shoves, and postflop calls of 35% of the stack or more. Each is decided on expected tournament points, not chips. Utility is Harville ICM over the remaining places' points: exact DP when 5 or fewer players remain, an exact equal-others recursion otherwise. Each outcome (fold, steal, win, lose) moves our stack and the opponent's, and dead money goes to the right players. Push/fold applies at about 13 bb or less effective: it sums over each player behind calling or folding, using a caller model (a prior adjusted by that seat's observed call-versus-raise rate and wildness) and equity against the caller's range.
3. **Postflop, by time-boxed range-weighted Monte Carlo.** About 85 µs per decision gives roughly 50–150 samples. Opponent hands are sampled from their modelled range slices. Flatters and limpers get capped slices, since their premiums would have raised; a BB who checked gets a wide one. The aggressor's samples are then narrowed to the top q of their range by current made-hand strength, with the rest weighted 0.25. q comes from that seat's observed bet or raise frequency and the bet size, shrinks with repeated barrels, and is pushed toward 1 for wild bots. The MC gives three numbers: equity against the full range, against the narrowed range, and against the top half of the range (a proxy for their calling range). Value bets, c-bets and stabs, draw semi-bluffs, value raises, pot-odds calls with multiway and caller margins, and ICM all-in calls are all thresholds on those numbers.
4. **Opponent model rebuilt from `obs.history`.** A small replay engine re-simulates the hand from start-of-hand stacks: blinds, streets, round ends, all-ins. That lets each history entry be credited to a street and a situation (unopened, facing open, facing 3-bet, facing bet, checked to) without any street markers. It skips blind posts if the host logs them and maps `bet` and `allin` to `raise`. If the replay ever disagrees with the observed street, it marks itself unreliable for the rest of that hand. In sim tables it matched observed bets and stacks on 721 of 721 decisions.
5. **Safety.** Every path is wrapped. An exception falls back to a minimal strategy that only reads `hole`, `board`, `legal` and `to_call`. Every action goes through a legaliser that clamps raises into [min, max], turns an illegal check into a fold and a fold into a check when check is free, and so on. The Monte Carlo stops on a wall-clock deadline. `gc.freeze()` runs after import. Random numbers come from the bot's own `random.Random`.

## Why this approach

- The format rewards survival. Points are flat (10/7/5/4/3/2/1/0) and **81% of sim tables reach the 200-hand cap, usually with 2–4 players alive**. ICM at the cap decides most of the score, so I made tournament-point utility the core of every stack-risking decision.
- The 1 ms limit in pure Python rules out real-time solving. A precomputed preflop matrix plus a small, range-aware Monte Carlo is the most accurate thing that fits in about 100 µs.
- The field ranges from random bots to adaptive solvers, so nothing is hard-coded per opponent type. Ranges, narrowing, calling and stealing all flow from per-seat frequencies with priors. Against a random bot the estimates drift to "any two, no information in its bets", so the bot calls it down and value-bets it. Against nits it steals and folds to their aggression. Against a thief its open-rate estimate widens, which widens the bot's defence.

## Timeline (T0 = `T0.txt`)

Times are approximate minutes from T0.

- **0–5** Evaluator written and validated. Preflop Monte Carlo started in the background (about 2 min of CPU).
- **5–12** Simulator, test opponents and bot v1 written. Harness clean. First latency fix: the Monte Carlo was given a deadline and its post-processing was made cheaper.
- **13–15** v1 against the "mixed" field (random, station, maniac, nit, TAG, shover, LAG): **6.26 ± 0.10** points per table over 800 duplicate tables, against an average of 4.0. Against the "tough" field (three TAG variants, LAG, nit, two shovers): **5.25 ± 0.08**. Saved as `v1.py`.
- **15–20** Added Thief and a field built around my own variants. Wrote the paired sweep runner.
- **20–24** **Found an ICM accounting bug.** An all-in opponent has 0 chips behind, so the fold baseline treated them as busted, which inflated the value of folding. Dead money was also not credited. Fixed with per-outcome final stacks for every player. Added an optional blend toward a chip-linear model under blind pressure (`press`).
- **24–35** Seeded, paired duplicate comparisons (`cmp.py`). Added draws, stabs, semi-bluffs, short-handed and heads-up opening widths, mixed bet sizes, thinner value bets against stations, multiway caller margins, and the fallback strategy.
- **35–50** ICM experiments on field A (see results). **Pure ICM is best.** Blending toward chip EV hurts, and so does extra risk aversion beyond ICM. Default set to `press=0`.
- **50–60** Parameter screen (c-bet, call margin, open width, ICM margin, push depth): all flat within noise. Capped ranges for flatters and limpers in the Monte Carlo. The replay now tolerates blind posts and `bet`/`allin` names. `snap_m60.py`.
- **60–75** Strong-field checks (fields D and E): capped ranges neutral, aggression variants neutral or worse. Mutated-observation robustness test: 0 bad actions.
- **75–100** Monte Carlo budget cut from 125 µs to 85 µs, which was quality-neutral (+0.02 ± 0.06) and gives a lower timeout risk. Caller-model multiplier tested: +0.19 in one strong-field run, but −0.07, −0.03 and −0.01 in the other three runs, so it stays at 1.0. Host load climbed to 40–50 on 8 cores from other users' jobs, which made runs very slow. `snap_m90.py` was saved late, at about 103 min.
- **104 FROZEN** (T0 + 6236 s, 2026-11-02 01:28 local). md5 `c5e956bd211896e22bafe0f2acfeeed4`.

Snapshots: `snap_m30.py` at 30 min, `snap_m60.py` at 60 min, `snap_m90.py` at about 103 min (late, see above). `v1.py` and `v2a`–`v2j` are the intermediate versions used as opponents.

## Test results

All scores are tournament points per table: average 4.0, maximum 10. Each mean ± SE uses one seed as the unit, and each seed is 8 duplicate tables with rotated seating, so 300 seeds means 2400 tables. "diff" is the paired difference on identical deals and opponent seeds. The noise between two *identical* configurations was about 0.07–0.09 at 220–300 seeds, so anything under about 0.15 is not a real difference.

**Fields** (our bot plus 7 others, all distinct, as in the real format):
- *mixed*: random, station, maniac, nit, tag, shover, lag
- *tough*: tag, tag-tight, tag-loose, lag, shover, nit, shover-wide
- *A*: thief, tag, tag-tight, lag, shover, nit, random (mostly competent, with one random bot)
- *D*: v2c (my earlier bot), pfnash, thief, tag-tight, lag, shover, station
- *E* (strong, no weak bots): v2e, v2e-aggressive, v1, pfnash, thief, lag, tag-tight

### Absolute level
| bot | field | seeds (tables) | points/table |
|---|---|---|---|
| v1 | mixed | 100 (800) | 6.26 ± 0.10 (best opponent: LAG at 5.65) |
| v1 | tough | 100 (800) | 5.25 ± 0.08 (best opponent: tag-tight at 4.33) |
| v1 | A | 400 (3200) | 5.09 ± 0.05 |
| **final (v2j)** | A | 220 (1760) | **5.21 ± 0.08** |
| **final (v2j)** | D | 220 (1760) | **5.12 ± 0.07** |
| **final (v2j)** | E | 200 (1600) and 160 (1280) | **4.38 ± 0.09**, **4.28 ± 0.09** |

Field E is mostly my own bot's lineage, so roughly 4.3–4.4 against 4.0 is about what a slightly better clone should score. In one 480-table field-E run, every bot's score was: v2g (≈ final) 4.37, v2e-aggressive 4.57, v1 4.33, v2e 4.26, tag-tight 4.16, pfnash 3.67, thief 3.51, lag 3.12, each ± about 0.13.

### Experiments that decided the design (paired, field A unless noted)
| change | diff | verdict |
|---|---|---|
| v2c (ICM fix + `press`=0.6) vs v1 | −0.07 ± 0.06 | not better |
| `press`=0.3 / 0.9 vs v1 | −0.03 ± 0.06 / **−0.34 ± 0.06** | chip-EV blending hurts |
| `icm_w`=0.8 vs v1 | **−0.26 ± 0.07** | hurts |
| `push_bb`=10 / 16 vs v1 | −0.19 ± 0.06 / −0.11 ± 0.06 | 13 kept |
| **pure ICM (`press`=0) vs v1** | **+0.14 ± 0.07** | adopted |
| extra ICM margin 0.05 / 0.12 vs v1 | −0.13 ± 0.07 / **−0.40 ± 0.06** | extra risk aversion hurts |
| ICM margin −0.03, `press`=0.15, c-bet 0.35/0.8, call margin 0/0.05, open width ×0.8/×1.2 | all within ±0.09 (SE about 0.06) | flat, defaults kept |
| capped flatter/limper ranges (field E / D) | −0.02 ± 0.09 / +0.00 ± 0.07 | neutral, kept as more principled |
| aggressive preflop + postflop / postflop only / preflop only (field E) | −0.02 / −0.01 / −0.09 (± 0.09) | rejected |
| Monte Carlo 80 µs vs 125 µs | +0.02 ± 0.06 | 85 µs adopted for latency margin |
| caller-model ×0.7 (A / E), ×0.75 (D / E) | −0.01 / +0.19 / −0.03 / −0.07 (± 0.07–0.11) | rejected, the E result was noise |

**Final check after freezing** (field A, 150 seeds = 1200 tables, paired on identical deals): v1 scored 5.06 ± 0.08 and the frozen bot scored **5.32 ± 0.09**, a **diff of +0.26 ± 0.10**. That is about 2.7σ, consistent with the earlier +0.14 ± 0.07 at 300 seeds.

**Main lesson:** with flat payouts and most tables decided by ICM at the hand cap, correct ICM for every stack-risking decision is worth more than any aggression knob. Measured at about +0.4 points per table, it was the biggest effect found, ranging from too loose (`press`=0.9) to too tight (margin 0.12).

### Legality and latency
- `harness.py rival_bot`: **0 exceptions, 0 illegal actions, 0 folds when check was free.** Import 0.20 s. act() mean 111 µs, median 105 µs, p99 329 µs, max 2.1 ms. A second seed gave p99 443 µs and max 9.7 ms. The host load average was **43–53 on 8 cores** from other jobs during this run. Spikes do not reproduce when the same observation is rerun (`t_lat.py`, `t_pftime.py`): reruns take 140–220 µs postflop and under 100 µs preflop. The preflop path has median 36 µs and p90 77 µs. The full output is in `harness_final.txt`.
- In-sim latency, measured on every decision of thousands of tables, was mean 60–130 µs. Decisions over 1 ms were 0.1–1.3% depending on host load; every one was a preemption, not compute. The Monte Carlo is deadline-bounded (85 µs plus a minimum of 24 samples heads-up or 12 multiway), and everything else is O(players).
- `t_robust.py` fed mutated observations to the bot and recorded **0 bad actions in about 900 decisions**: blind posts in the history, `bet` instead of `raise`, tuples and lists instead of sets, `history=None`, `hand_no=None`, `rules=None`, and `None` or `{}` hand results.

### Known limits and honest caveats
- My opponents are heuristic bots and my own lineage, not real solvers. Rankings against unseen strong bots may differ.
- The equal-others ICM approximation applies when 6 or more players remain. Exact Harville is only used with 5 or fewer, for speed.
- The bot does not use showdown cards even if `hand_end` provides them. It does read `result['history']` if present, to finish its counters.
- Under heavy host contention, rare preemptions over 1 ms are unavoidable in pure Python. The bot keeps typical compute around 100 µs to minimise exposure.
