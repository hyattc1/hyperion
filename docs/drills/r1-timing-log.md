# R1: slow-box timing (branch climb/r1-timing)

Backlog item R1 (docs/drills/goal-plan.md section 5): the organisers' sandbox may be 2-3x slower than this box or shared
and noisy. SafeBot panics (Hero's cheap path for the rest of the table) after 5 overruns of its 0.5 ms soft deadline in
a table. Goal: F keeps its strength and never times out on a 2-3x slower or noisy machine. Screen seeds 10000-10199
only (x 8 rotations = 1,600 tables per row), night field, payouts `lin` (8..1, the default) and `th`
(50/25/12/6/3/2/1/1). Every number below has the 1-minute load average of the host next to it (8 cores, shared with
other agents' jobs; at most 2 of my timing processes at once).

## The harness: tools/slowbox.py (commit 01baada)

- **Dilated clock.** `install(k, basis)` replaces `time.perf_counter`, `perf_counter_ns`, `monotonic`, `monotonic_ns`
  and rebinds every import-time binding in `hyperion.*` (engine.py, safe.py, compose/bot.py, hybrid/bot.py, core3.py,
  core.py all do `from time import perf_counter`), so every interval reads k times its length: the engine's 1 ms
  check, SafeBot's 0.5 ms deadline and panic count, the hybrids' 350 us soft deadline, the composite's late_us.
  `--clock cpu` (default) counts this thread's CPU time: a quiet k-times slower box; `--clock wall` real time.
- **Seat-only strictness.** The engine runs in mode model, the candidate behind `SlowSeat`, which reports its own
  dilated time as `last_cost_ns`, so the engine folds or checks it over 1 ms as strict mode would while every opponent
  plays exactly as in model mode. A k change moves points only through the candidate's own clock; runs pair seed for
  seed with each other and with `tools/swap.py paired` (`--det --free` reproduces model mode exactly: test).
- **Noisy host.** `--contend N --duty-ms ON,OFF --cpus C --clock wall`: workers pinned to cores shared with N busy
  processes (real CPU contention). `--noise RATE,MEAN_US`: seeded virtual preemptions on the box's clock.
- **Quiet costs.** `quiet`: plays each table three times in det mode (identical play), keeps each decision's minimum
  CPU time (host noise only ever adds), replays SafeBot's panic rule on those costs at any k, and cProfiles the
  decisions whose quiet cost is over a threshold.
- **Trace.** `--trace-us X` records every decision over X us of CPU with its section, member, counters moved, street,
  players, first-of-hand, GC; `trace` gives counts, mean cost and the rate within each value.

Command: `.venv/bin/python tools/slowbox.py run --specs composite,hybrid3_x,hero --seeds 10000:10200 --k 3
--payouts lin --out DIR --workers 2` then `tools/slowbox.py table DIR/a.json DIR/b.json`.

## Finding 1: this host's noise is in CPU time too (21:00, load 5-8)

A fixed 62 us pure-Python workload, 10,000 calls pinned to each vCPU at load ~5: p50 62, p99 119-148, p99.9 274-299,
max 0.4-8 ms, 0.9-1.5% of calls over 2x the median, in thread CPU time and wall time alike (WSL2: the hypervisor's
steal and SMT contention are charged to the running thread). At load 7 the same workload had p99 488 us and p99.9 3.6 ms.
So no clock on this box separates our code's cost from the host's noise; `--clock cpu` only removes guest-scheduler
preemption. Every live number below is "F on a k-times slower box with this host's noise, dilated k-fold": a
pessimistic noisy sandbox. The quiet-cost replays are the noise-free view.

## Finding 2: F's own tail is small; the observed tail is noise (21:00, load 5.3)

`quiet --specs composite --seeds 10000:10004` (32 tables, 5,519 decisions, min of 3 replays, 0 mismatches): CPU us p50
51, p90 68, p99 97, p99.9 118, max 154. Replaying SafeBot's rule on those costs: no decision over 0.5 ms even at k = 3,
no table would panic. The same tables live at k = 1 (load 4.7): p99 314 us, 4.1% of decisions over 150 us CPU, spread
evenly over sections (2-6% each), i.e. noise.

## Baseline: F, hybrid3_x, Hero on the slow box (night, lin, seeds 10000-10199 x 8)

| bot | k | points ± 95% | - same bot at k = 1 (paired) | timeouts / table | tables with a timeout | panic tables | p50 / p99 us (box) | load |
|---|---|---|---|---|---|---|---|---|
| F | 1 | 5.980 ± 0.113 | - | 0.214 | 259 | 13 | 69 / 349 | 4.4-7.6 |
| F | 2 | 5.923 ± 0.109 | -0.057 ± 0.048 | 0.588 | 627 | 219 | 139 / 678 | 6.8-7.9 |
| F | 3 | 5.825 ± 0.108 | -0.155 ± 0.063 | 0.754 | 750 | 519 | 202 / 866 | 5.7-6.5 |
| hybrid3_x | 1 | 5.736 ± 0.116 | - | 0.145 | 195 | 0 | 50 / 263 | 4.4-7.8 |
| hybrid3_x | 2 | 5.733 ± 0.114 | -0.003 ± 0.040 | 0.351 | 425 | 29 | 101 / 487 | 6.5-7.9 |
| hybrid3_x | 3 | 5.729 ± 0.114 | -0.007 ± 0.045 | 0.504 | 537 | 104 | 150 / 626 | 5.7-6.6 |
| Hero | 1 | 5.793 ± 0.101 | - | 0.105 | 144 | 0 | 39 / 185 | 4.9-7.8 |
| Hero | 2 | 5.772 ± 0.102 | -0.022 ± 0.027 | 0.240 | 320 | 9 | 78 / 356 | 6.5-7.9 |
| Hero | 3 | 5.766 ± 0.103 | -0.027 ± 0.028 | 0.283 | 352 | 31 | 117 / 476 | 5.7-6.7 |

(1,600 tables a row; panic and timeout columns are counts of tables.) F - hybrid3_x on the same seeds: +0.244 at k = 1,
+0.190 at k = 2, +0.096 at k = 3; F - Hero: +0.187, +0.151, +0.059.

Reading: timeouts are cheap (hybrid3_x and Hero lose under 0.03 a table with 0.3-0.5 timeouts a table); F's loss is
its panic. At k = 2, 1.28% of F's decisions overran the 0.5 ms soft deadline (3,575 of 280k, CPU median 365 us against a
quiet max of 154 us: noise), panic fired at call 103 / 132 / 167 (quartiles) of ~175 a table.

## Finding 3: F's hand_end costs more than its decisions (21:21, load 5.3)

One pass over 8 det tables (seeds 10000-10003, rotations 0 and 3), CPU us per hand_end: lin p50 108, p90 153, p99 298,
max 751; th p50 164, p90 289, p99 440, max 778 (F's decisions: p50 ~51). cProfile (th, 6 tables): two Heroes run a
full hand_end every hand, the hero member and the base's own fallback Hero, 84% of the time: the ICM curve
(`IcmCurve.compute`, 13 or 9 exact ICM points; 55%) and the profiler's per-seat dials (`_compute_dials`, `archetype`;
26%); rival 3's final replay 10%. The engine never times hand_end, but the night's adapter does when the kit's
hand-end signal carries no chip deltas, final stacks or showdown and a seat acted after our reply (`defer_hand_end`,
hyperion/drills/adapter.py: delivered at the top of the next decide, "50-200 us"). On a 3x box that is +0.3-0.5 ms on
the first decision of such hands, +1.3 ms at p99 under th: soft overruns, and timeouts. SafeBot never sees it (it
times act only). The harness's `--defer` puts every hand_end inside the next act (the adapter's `hold_all`, the worst
case). The switch that exists: `defer_hand_end = False` on the adapter keeps hand_end untimed at the cost of the folds
after our reply in Hero's chip chain.

## Baseline on th payouts (night, 50/25/12/6/3/2/1/1, seeds 10000-10199 x 8; bot code 01baada)

| bot | k | points ± 95% | timeouts / table | tables with a timeout | panic tables | calls in panic | p50 / p99 us (box) | load |
|---|---|---|---|---|---|---|---|---|
| F | 1 | 24.316 ± 1.064 | 0.072 | 84 | 5 | - | 70 / 294 | 4.9-6.2 |
| F | 1.5 | 24.446 ± 1.076 | 0.025 | 37 | 0 | 0.0% | 104 / 404 | 4.0-6.0 |
| F | 2 | 24.137 ± 1.086 | 0.019 | 31 | 61 | - | 136 / 510 | 4.3-5.5 |
| F | 3 | 22.171 ± 1.001 | 0.130 | 180 | 438 | 12.7% | 193 / 764 | 4.3-5.0 |
| hybrid3_x | 1 | 22.326 ± 1.086 | 0.038 | 48 | 6 | - | 51 / 254 | 4.9-6.2 |
| hybrid3_x | 3 | 21.658 ± 1.044 | 0.065 | 94 | 215 | 6.7% | 143 / 666 | 4.1-5.0 |
| Hero | 1 | 23.345 ± 1.076 | 0.021 | 30 | 0 | - | 40 / 123 | 5.4-6.2 |
| Hero | 3 | 23.388 ± 1.073 | 0.002 | 3 | 0 | 0.0% | 114 / 276 | 4.1-5.0 |

(th points are on a 100-point table; the 8..1 table has 36.) At k = 3 F loses 2.1 and falls 1.2 behind Hero; F panics
on 27% of tables. Hero never panics: its ICM is a curve computed in hand_end, so its act stays cheap.

## Profile of the tail: quiet costs (min of 3 det replays; seeds 10000-10039 x 8, 320 tables each; load 4.9-6.1)

| code | payouts | p50 / p90 / p99 / p99.9 / max CPU us | hand_end p50 / p99 / max | soft overruns per table at k = 2 / 3 | tables that would panic at k = 2 / 3 (of 320) |
|---|---|---|---|---|---|
| 01baada | lin | 50 / 68 / 94 / 111 / 142 | 100 / 154 / 220 | 0 / 0 | 0 / 0 |
| 01baada | th | 52 / 73 / 208 / 265 / 299 | 115 / 174 / 348 | 0.54 / 2.41 | 4 / 46 |
| fast ICM (6c51604) | th | 51 / 71 / 151 / 197 / 235 | 113 / 169 / 396 | 0 / 1.08 | 0 / 8 |

No decision of F exceeds 1 ms on a quiet 3x box on either table; under lin nothing even reaches the 0.5 ms soft
deadline. Under th the decisions over 167 us CPU (the soft deadline at k = 3) are all preflop: pre_raised_deep 54%,
pre_allin 23%, pre_raised_short 20% (where the base is a full shadow), pre_open_short 3%; 98% of them with all eight
seats alive (7.8% of eight-alive decisions vs 1.9% at seven): rival 3's core pricing an all-in with exact ICM
(`_allin`: four `icm_points` calls, each the 2^7-subset pass at eight seats). cProfile of those decisions: `_allin`
47% of their time, `icm_me` 41%, history replay 9%. First decision of a hand: not special (1.4% vs 1.5%). Garbage
collection: none during any traced decision (Hero's gc.freeze at new_table; the decisions allocate little).
Multiway postflop: not in the tail (no postflop decision over 167 us). Everything else in the live tails is this
host's noise.

**Fix 1 (6c51604): exact ICM at half the cost, bit-identical.** `icm_me`'s forward pass now walks a per-m subset plan
built at import (lowest member, predecessor, size, successors): the same float operations in the same order as the
loop it replaced (kept as `_icm_me_ref`; test: equal on 2,000 random cases over five payout tables), 49 -> 25 us at
eight seats. On th it halves F's tail (p99 208 -> 151, max 299 -> 235) and cuts the quiet-3x panics from 46 to 8 of
320. No play changes, so it needs no dial.

**Which F (checked 21:44 after the coordinator's note on swap.py specs).** Every spec here is built by
`hyperion.ship.make_bot(bot, dials, seed)`, i.e. `CB.ship()`, which puts the dials on top of SHIP_DIALS: checked for
`{}` and for a governor spec, route `post=hero,pre_raised_short=hero`, `exploit.bet_min_fold` 0.4, the hero member's
`postflop.call_margin` 0.2, light shadows. "F" in this log is the shipped F; no number here used swap.py specs.

## Candidates on th, k = 3 (21:33-21:44, load 4.9-7.2; wt_r1 code, so every row has the fast ICM)

| candidate | dials (on top of the ship's) | points ± 95% | - F same run (paired) | timeouts / table | panic tables | calls in panic / below level 0 |
|---|---|---|---|---|---|---|
| F | - | 22.284 ± 1.023 | - | 0.314 | 477 | 13.9% / - |
| F_nopanic | panic_after 1e9 | 24.510 ± 1.097 | +2.225 ± 0.663 | 0.311 | 0 | 0 / 0 |
| F_dl8 | deadline_ms 0.8 | 24.436 ± 1.058 | +2.152 ± 0.674 | 0.339 | 15 | 0.2% / 0 |
| F_rec | panic_recover 40 | 23.326 ± 1.074 | +1.042 ± 0.739 | 0.381 | 480 | 6.8% / 6.8% |
| F_win | panic_window 60 | 23.452 ± 1.068 | +1.168 ± 0.597 | 0.305 | 256 | 7.6% / 7.6% |
| F_lean | degrade lean, ladder, recover 40 | 24.412 ± 1.091 | +2.128 ± 0.670 | 0.307 | 19 | 0.2% / 8.4% |
| F_lad | degrade noshadow,lean,hero, ladder, window 60, recover 40 | 24.301 ± 1.054 | +2.017 ± 0.648 | 0.369 | 0 | 0 / 5.0% |
| F_lad8 | F_lad + deadline_ms 0.8 | 24.460 ± 1.086 | +2.176 ± 0.642 | 0.375 | 0 | 0 / 0 |

F at k = 1 on th was 24.316 (baseline run): every row from F_nopanic down to F_lad8 is back to it. Panic bought
nothing: F and F_nopanic have the same timeouts (0.314 vs 0.311 a table, this host's preemptions, which no path is
cheap enough to dodge), and panic cost 2.2 points on a 100-point table.

## Candidates on th, k = 1 (21:44-21:54, load 5.5-8.7)

F 24.394 ± 1.068, 0.064 timeouts a table, 2 panic tables. Against it (paired): F_nopanic +0.052 ± 0.110, F_dl8 +0.086
± 0.117, F_rec +0.046 ± 0.166, F_win +0.059 ± 0.149, F_lean +0.064 ± 0.129, F_lad +0.063 ± 0.147, F_lad8 +0.118 ±
0.173; none panicked, timeouts 0.029-0.041 a table. No candidate costs anything on a normal box (the governor never
fires at k = 1; in model mode it cannot: panic_after is 10^9 there).

## Candidates on th, k = 2 (21:54-22:04, load 4.2-6.8)

F 24.366 ± 1.071, 0.039 timeouts a table, 3 panic tables (the 01baada baseline had 61 at k = 2: the fast ICM).
Against it: F_nopanic +0.037 ± 0.204, F_dl8 +0.050 ± 0.207, F_rec +0.074 ± 0.206, F_win +0.128 ± 0.207, F_lean +0.095 ±
0.217, F_lad +0.015 ± 0.211, F_lad8 +0.030 ± 0.177; panic tables 0-4; timeouts 0.035-0.048 a table. At k = 2 on th the
fast ICM alone removes the problem; at k = 3 (above) it does not (the noise times three still trips the cliff).

## The first decision of a table (coordinator's question, 22:05, load 6.7)

- Warm process (the quiet replays, 320 tables each, min of 3): the first call of a table costs p50 75 / p99 108 / max
  111 us CPU on lin (other calls p50 50, p99 94); th p50 79 / p99 246 / max 249 (fast ICM: 77 / 213 / 224). About
  +25 us of first-hand setup (the members' new-hand state, the exploit layer's and profiler's starts). Live at load
  5-8, 4% of tables had a first call over 200 us CPU (2% of other calls), median ~295 us: the same noise.
- Fresh process (`../cold.py`: import, build, three tables; two runs per payout table): import 50 ms, build 225-265 ms,
  the first table's new_table 600 ms, later tables' 113-170 us; the first act of the first table 163-250 us, then
  ~70-80 us from the second table on.
- So the 12-56 ms decisions and the 48 ms first call in the exploiter's arena are not F's code: no in-hand path of F
  costs over 0.3 ms quiet. The multi-ms in-hand calls are preemptions (this host); a first call that large is setup
  landing in act (a kit with no separate new_table, the 600 ms per-Rules warm-up), which climb/h3-kit-fixes owns, as
  it owns hand-end cost (finding 3 above is my measurement of it, for them). Mine: the in-hand tail (exact ICM under
  non-linear payouts) and the panic design.

## Candidates on lin, k = 3 (22:04-22:14, load 4.8-7.5)

| candidate | points ± 95% | - F same run (paired) | timeouts / table | panic tables | calls degraded |
|---|---|---|---|---|---|
| F | 5.937 ± 0.111 | - | 0.138 | 60 | - |
| F_nopanic | 5.965 ± 0.110 | +0.028 ± 0.031 | 0.145 | 0 | 0 |
| F_dl8 | 5.971 ± 0.110 | +0.035 ± 0.027 | 0.177 | 6 | 0.1% |
| F_dl8rec (+ recover 40) | 5.984 ± 0.109 | +0.048 ± 0.029 | 0.179 | 3 | 0.0% |
| F_hero (ladder to Hero, recover 40) | 5.967 ± 0.112 | +0.031 ± 0.030 | 0.154 | 1 | 0.6% |
| F_lean (ladder lean, recover 40) | 5.955 ± 0.113 | +0.018 ± 0.030 | 0.170 | 4 | 1.3% |
| F_lad | 5.969 ± 0.111 | +0.033 ± 0.030 | 0.111 | 0 | 0.1% |
| F_lad8 | 5.976 ± 0.110 | +0.039 ± 0.029 | 0.142 | 0 | 0.0% |

This run's host was quieter than the baseline's (F panicked on 60 tables here, 519 there; p99 469 vs 866 us): the
cliff's cost follows the host's noise, from 0.03 to 0.16 a table on 8..1. Every governed candidate removes it.

Recipe (hyperion/ship.py `SLOW_RECIPES`, not a window recipe): `--dials slow_box` = F_lad8 on the composite, the same
governor with hybrid3_x's one level (lean) on the core bots, window / recover / 0.8 ms on Hero; stacks with the
window recipes (`slow_box+survival`).
