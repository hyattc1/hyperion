# NOTEBOOK — o7 rival_bot (chart bot: Nash push/fold + ICM calls + position charts + MDF postflop)

T0 in T0.txt. Machine load ~14 on 8 cores; all runs `nice -n 5 timeout ...`, max 2 procs.

## E1 evaluator check
`python3 test_ev.py` — ev.py eval7 vs brute-force 5-of-7 reference, 20k hands: 0 mismatches, 3.9 us/eval.

## E2 equity matrix (precompute)
`python3 precompute_eq.py {0,1} 2 700` (2 shards) — 169x169 class-vs-class all-in equity, 700 MC trials per pair, blocker-exact combo weights. ~3 min.

## E3 Nash push/call charts
`python3 build_tables.py` — order = all-in equity vs random; EQR[class][x] = equity vs top-x%;
chip-EV Nash, first-in jam with k behind, single-caller approximation, everyone S bb, blinds 0.5/1, no ante, 80 damped iterations.
Sanity vs published HU Nash: SB push 10bb = 58% (published ~58%), BB call 10bb = 38% (published ~37%).
k=7 (UTG 8-max) push: 10bb 11%, 15bb 8%, 5bb 17%. BTN (k=2) push 10bb 30%.

## E4 first bot (v1) vs simple fields
Bot v1: OPEN charts by players-behind, push/fold <=13bb (<=15 BTN/SB) with Nash chart AND ICM-EV check, ICM call-off EV, deep 3bet/flat charts, postflop tiers+MDF thresholds.
Harness: `python3 harness.py rival_bot` -> exceptions=0 illegal=0, mean 51us, max 12117us. probe2 (min of 5 timings per obs, 4000 obs) -> median 9.7us p99 18us max 31us: spikes are OS scheduling (load ~14 on 8 cores), not compute.
`run.py 300 11 rival_bot:Bot,RandomBot,CallBot,Maniac,Rock,PushFold,ABC,ABC` -> rival 6.33+-0.16 (field avg 4.0); ABC 5.62/5.29, Rock 5.03 (Rock had an illegal-action bug, folded), PushFold 4.58, Random 2.07, Maniac 1.67, CallBot 1.43.
`run.py 300 12 rival_bot:Bot,PushFold x2,ABC x3,Rock x2` -> rival 5.44+-0.17; ABC 4.13/4.03/3.88, Rock 3.90/3.69, PushFold 3.89/3.04.
(Rock test-opponent bug fixed after this run.)

## E5 push-mode variants (same table)
`run.py 500 21 Bot(chart AND icm),Chart,ICM,NashPF(always jam/fold),ABC,ABC,PushFold,Rock`
Chart 4.99+-0.14 | ICM-only 4.63+-0.13 | NashPF 4.50+-0.14 | Bot(chart&icm) 4.34+-0.13 | PushFold 3.79 | ABC 3.55/3.35 | Rock 2.86.
=> ICM tightening of first-in jams loses (~0.65 pts vs pure chip-EV Nash chart). Fast blinds + 200-hand cap punish tightness. Default -> mode_push='chart'.
## E6 self-play 8x Bot v1
`run.py 200 22 Bot x8` -> 3.70..4.67, all within ~2 SE of 4.0; 0 illegal, no crashes.

## E7 ICM weight on all-in calls (push mode = chart)
`run.py 500 31 Bot(icm_w=1),Chip(icm_w=0),Half(0.5),NashPF,ABC,PushFold,Rock,RandomBot` -> Bot 4.96+-0.12, NashPF 4.85, Half 4.77, Chip 4.40, ABC 4.31, PushFold 3.99, Rock 3.90, Random 0.84
`run.py 500 32 Bot,Chip,Half,NashPF x2,ABC,PushFold,ABC` -> Bot 4.90+-0.14, NashPF 4.28/4.17, Half 4.07, Chip 3.99, ABC 3.64/3.44, PushFold 3.50
=> full ICM for calling off is clearly best (+0.5..0.9 over chip-EV calls). Keep icm_w=1.
Also fixed _call_allin_ev: when we cover the villain we only lose what he can win (was: assumed we bust).

## E8 push width and push/fold depth (after fix)
`run.py 600 41 Bot(x1.0),P085,P120,NashPF,ABC,PushFold,Rock,RandomBot` -> P120 5.29+-0.12, Bot 5.03, P085 4.82, NashPF 4.54, ABC 3.94, Rock 3.87, PushFold 3.75, Random 0.75
`run.py 600 42 Bot(13/15bb),PFlo(10/12bb),PFhi(18/20bb),NashPF,ABC,PushFold,Rock,RandomBot` -> PFlo 5.20+-0.12, Bot 4.91, PFhi 4.89, NashPF 4.48, ABC 4.35
=> wider-than-Nash jams and lower jam/fold depth both look ~+0.25 (1.5-2 SE). Needs a confirm run.

## E9 confirm push width / depth (board-wetness fix + big-raise-as-jam stat + station read in all variants)
`run.py 600 51 Bot,P120,PFlo,PFloP120,NashPF,ABC,PushFold,RandomBot` -> PFloP120 4.89, P120 4.84, PFlo 4.81, Bot 4.74 (+-0.12 each), NashPF 4.25, ABC 4.10, PushFold 3.64, Random 0.72
`run.py 600 52 Bot,P120,PFlo,PFloP120,NashPF,ABC,Rock,CallBot` -> PFloP120 5.12, P120 5.11, PFlo 4.89, Bot 4.89, NashPF 4.34, ABC 3.88, Rock 3.43, CallBot 0.34
Pooled 1200 tables: PFloP120 5.00, P120 4.98, PFlo 4.85, Bot 4.81 (SE ~0.085 each). Width x1.2 ~ +0.17 (consistent with E8), depth 10/12 ~ +0.05 (noise).

## E10 postflop knobs (new defaults: push x1.2, jam/fold <=10bb EP, <=12bb BTN/SB)
Tight = call_shift +0.05, bluff x0.6; Loose = call_shift -0.05; Old = push x1.0 at 13/15bb.
`run.py 600 61 Bot,Tight,Loose,Old,NashPF,ABC,PushFold,RandomBot` -> Tight 5.05, Loose 4.88, Bot 4.86, Old 4.76, NashPF 4.21, ABC 3.85, PushFold 3.54, Random 0.85
`run.py 600 62 Bot,Tight,Loose,Old,NashPF,ABC,Rock,Maniac` -> Bot 5.01, Tight 4.89, Old 4.85, Loose 4.61, NashPF 4.55, Rock 3.66, ABC 3.63, Maniac 0.81
Pooled: Tight 4.97, Bot 4.93, Old 4.80, Loose 4.74 (SE ~0.085). Loose postflop calling is worse; Tight ~ Bot. Runs are fast (600 tables ~25s) -> use 3000-table runs from here.

## E11 large: push width + tight postflop (3000 tables x 2 fields)
Bot here = push x1.2, 10/12bb. P100 = x1.0, P140 = x1.4, Tight = call_shift +0.05, bluff x0.6 (x1.2 push).
`run.py 3000 71 Bot,P100,P140,Tight,NashPF,ABC,PushFold,RandomBot` -> Tight 4.848, P100 4.836, Bot 4.780, P140 4.710 (+-0.053), NashPF 4.28, ABC 4.05, PushFold 3.66, Random 0.83
`run.py 3000 72 Bot,P100,P140,Tight,NashPF,ABC,Rock,Maniac` -> Tight 4.937, P100 4.849, P140 4.809, Bot 4.759 (+-0.055), NashPF 4.30, ABC 3.93, Rock 3.55, Maniac 0.87
Pooled 6000: Tight 4.89, P100 4.84, Bot 4.77, P140 4.76 (SE ~0.038).
=> The x1.2 "edge" from E8/E9 was noise; plain Nash width (x1.0) is at least as good -> back to x1.0 (matches the team's chart).
=> Tighter postflop (+0.05 call threshold, fewer bluffs) ~ +0.12 vs base (~2.2 SE). Adopt, and test further.

## E12 large: depth + postflop tightness (Bot now = Nash x1.0, 10/12bb, call_shift .05, bluff x0.6)
T13 = jam/fold at 13/15bb; Tighter = call_shift .10, bluff x0.4; CallOnly = call_shift .05, bluff x1.0
`run.py 3000 81 Bot,T13,Tighter,CallOnly,NashPF,ABC,PushFold,RandomBot` -> Tighter 4.934, T13 4.824, Bot 4.818, CallOnly 4.742 (+-0.053), NashPF 4.31, ABC 4.00, PushFold 3.55, Random 0.83
`run.py 3000 82 Bot,T13,Tighter,CallOnly,NashPF,ABC,Rock,CallBot` -> CallOnly 5.191, Tighter 5.010, T13 4.947, Bot 4.932, NashPF 4.27, ABC 3.77, Rock 3.57, CallBot 0.32
Pooled: Tighter 4.97, CallOnly 4.97, T13 4.89, Bot 4.88. Jam depth 10/12 vs 13/15: no difference. Bluff frequency effect flips by field.
Concern: my test bots bet mostly for value, so tight calling is flattered. Next: add a loose-aggressive Aggro opponent (c-bets 90%, barrels 50%).

## E13 large: postflop tightness with loose-aggressive Aggro opponents
`run.py 3000 91 Bot,Tighter,CallOnly,Loose2(call_shift 0),NashPF,Aggro,Aggro,ABC` -> Bot 4.722, Tighter 4.636, CallOnly 4.621, Loose2 4.480 (+-0.052), NashPF 4.43, ABC 3.44, Aggro 2.94/2.73
`run.py 3000 92 Bot,Tighter,CallOnly,Loose2,NashPF,Aggro,RandomBot,Rock` -> CallOnly 4.918, Bot 4.890, Tighter 4.876, Loose2 4.693, NashPF 4.51, Aggro 3.74, Rock 3.67, Random 0.71
E12+E13 (12000 tables): Bot 4.845, Tighter 4.865, CallOnly 4.87, Loose2 (E13 only) 4.59. Tightness beyond Bot only helps vs value-only bettors; Bot (call_shift .05, bluff x0.6) is the robust middle. Keep.

## E14 large: value of reads, squeeze penalty
NoRead = all per-seat stats off (priors only); Pen02/Pen0 = call-off penalty per player behind 0.02 / 0 (Bot 0.05 ICM pts).
`run.py 3000 101 Bot,NoRead,Pen02,Pen0,NashPF,Aggro,RandomBot,ABC` -> NoRead 4.818, Bot 4.800, Pen02 4.786, Pen0 4.777 (+-0.051), NashPF 4.62, ABC 3.79, Aggro 3.64, Random 0.77
`run.py 3000 102 Bot,NoRead,Pen02,Pen0,NashPF,Maniac,PushFold,Rock` -> NoRead 4.972, Pen0 4.873, Pen02 4.872, Bot 4.866 (+-0.053), NashPF 4.41, PushFold 3.57, Rock 3.56, Maniac 0.88
=> reads are neutral to slightly negative (+0.06 for NoRead pooled, ~1.2 SE); squeeze penalty irrelevant. Split the reads next.

## E15 large: which reads (PreOnly = raise/jam-rate range widening; PostOnly = station no-bluff + aggressive-bettor call widening)
`run.py 3000 111 Bot,NoRead,PreOnly,PostOnly,NashPF,Aggro,RandomBot,CallBot` -> PostOnly 5.236, Bot 5.175, PreOnly 5.162, NoRead 5.145 (+-0.048), NashPF 4.79, Aggro 4.30, Random 1.45, CallBot 0.75
`run.py 3000 112 Bot,NoRead,PreOnly,PostOnly,NashPF,Maniac,ABC,Rock` -> NoRead 4.923, PostOnly 4.890, PreOnly 4.827, Bot 4.743 (+-0.054), NashPF 4.39, ABC 3.89, Rock 3.52, Maniac 0.82
Pooled: PostOnly 5.06, NoRead 5.03, PreOnly 4.99, Bot 4.96. Preflop range-widening reads cost ~0.07-0.1 (a seat's overall raise rate is not its positional range); postflop obvious reads are neutral/slightly positive.
=> reads_pre = False (preflop is pure chart/Nash + ICM), reads_post = True.

## E16 large: final defaults (reads_pre off) vs tweaks
`run.py 3000 121 Bot,RaiseShift(+.08 when our bet is raised),AllReads,Tighter,NashPF,Aggro,RandomBot,ABC` -> Bot 4.853, AllReads 4.840, RaiseShift 4.789, Tighter 4.772 (+-0.051), NashPF 4.57, ABC 3.78, Aggro 3.61, Random 0.79
`run.py 3000 122 same 4 + NashPF,Maniac,PushFold,Rock` -> Tighter 4.994, Bot 4.954, RaiseShift 4.905, AllReads 4.725, NashPF 4.39, PushFold 3.68, Rock 3.46, Maniac 0.89
Pooled: Bot 4.90, Tighter 4.88, RaiseShift 4.85, AllReads 4.78. => freeze Bot defaults.

## Hardening
`fuzz.py {3,4,5}` (20k odd observations each: history None/garbage/out-of-range seats, bad button, min_raise==max_raise, hand_no None, 2-seat lists, rules None):
first pass 71 internal exceptions (raise from a seat index outside stacks; empty raise list when we hold the top bet) -> fixed -> 0 internal exceptions, 0 illegal on all three seeds.
`harness.py rival_bot 2000 {1,2,3}` -> exceptions 0, illegal 0, fold_when_check_legal 0; mean 60-92us, p99 300-390us, max 10-14ms (machine load 17-18 on 8 cores; trivial test bots show the same 8-16ms maxima in-engine).

## F1/F2 final bot
`run.py 3000 201 Bot,RandomBot,CallBot,Maniac,Rock,PushFold,ABC,Aggro` -> Bot 6.300+-0.048 | ABC 5.51, Aggro 5.07, Rock 5.02, PushFold 4.73, Random 2.07, Maniac 1.87, CallBot 1.44
`run.py 1000 202 Bot x8` (self-play) -> 3.78..4.11 (+-0.1 each), mean 4.0, 0 illegal, no crashes.

## F3 final vs stronger field
`run.py 3000 301 Bot,V1(first-bot settings),NashPF,NashPF,Tighter,Aggro,ABC,PushFold` -> Bot 4.608+-0.055 | Tighter 4.551, V1 4.416, NashPF 4.315/4.285, ABC 3.48, PushFold 3.39, Aggro 2.96

## F4 latency
`timing.py rival_bot 300` (in-engine, 36,405 decisions; slow ones re-run 3x from a copied state): raw median 14us, p99 180us, max 25.9ms, 182 over 1ms; true compute median 14us, p99 80us, p99.9 243us, max ~300us, 0 over 1ms.
`probe2.py rival_bot 4000 1` (harness obs, min of 5): median 9.4us p99 19us max 40us.
Noise floor: `harness.py trivial_bot` max 21us (its calls are too short to get preempted); harness with gc disabled shows the same 8-18ms spikes -> not GC; it is OS preemption at load ~19 on 8 cores.
Kit fallback: rival_bot imports in 0.05s with kit.py absent (`python3 -I` from a copy without kit), Agent stub used.

## FROZEN
Final `harness.py rival_bot`: import 0.03s, exceptions 0, illegal 0, fold_when_check_legal 0, mean 41.5us, median 18.0us, p99 232us, max 4176us (load 19.7).
rival_bot.py 91,754 bytes, md5 7ada9e818fe730583053e7b0c6f7a18b. Elapsed at freeze ~47 min.
