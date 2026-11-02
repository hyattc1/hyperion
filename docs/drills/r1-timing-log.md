# R1: slow-box timing (branch climb/r1-timing)

Backlog item R1 (docs/drills/goal-plan.md section 5): the organisers' sandbox may be 2-3x slower than this box or shared
and noisy. SafeBot panics (Hero's cheap path for the rest of the table) after 5 overruns of its 0.5 ms soft deadline in
a table. Goal: F keeps its strength and never times out on a 2-3x slower or noisy machine. Screen seeds 10000-10199
only (x 8 rotations = 1,600 tables per row), night field, payouts `lin` (8..1, the default) and `th`
(50/25/12/6/3/2/1/1). Every number below has the 1-minute load average of the host next to it (8 cores, shared with
other agents' jobs; at most 2 of my timing processes at once).

## Summary (2026-11-01 23:55; screen seeds only, the coordinator runs the held-out confirmation)

- **The cliff, not the clock, is what a slow box costs F.** Panic (Hero's cheap path for the rest of the table) is
  worth -13.2 points a table on th and -1.58 on 8..1 when played whole, and on this host it fires on noise: F's own
  decisions never reach 0.3 ms quiet (max 142 us on 8..1, 235 us on th with the fast ICM), but this WSL2 host inflates
  ~1% of calls 2-7x, in CPU time too, and k multiplies that. Timeouts themselves are cheap (0.1-0.2 points each on th):
  F without panic and F with panic time out equally (a preemption lands whatever path runs).
- **Fix, behind dials (default = today's cliff, bit-identical in model mode):** SafeBot's governor (0.8 ms
  near-timeouts, counted only in clusters of 5 in 60 calls, a ladder of levels before the cheap path, recovery after 40
  quiet calls with backoff) and the composite's levels (noshadow, lean, hero). One word: `--dials slow_box`
  (hyperion/ship.py `SLOW_RECIPES`; to ship it, `python -m hyperion.ship --set slow_box`).
- **Fix without a dial (bit-identical play):** exact ICM (`icm_me`) at half the cost, which halves F's own tail under
  top-heavy payouts.

F as shipped (no dials, fast ICM) against F with `slow_box`, same seeds and same run (interleaved), night, 1,600
tables a row:

| payouts | k | F points | timeouts / table | panic tables | F + slow_box points | timeouts / table | panic tables | slow_box - F (paired) |
|---|---|---|---|---|---|---|---|---|
| th | 1 | 24.394 | 0.064 | 2 | 24.512 | 0.041 | 0 | +0.118 ± 0.173 |
| th | 2 | 24.366 | 0.039 | 3 | 24.396 | 0.036 | 0 | +0.030 ± 0.177 |
| th | 3 | 22.284 | 0.314 | 477 | 24.460 | 0.375 | 0 | +2.176 ± 0.642 |
| th | 5 | 16.830 | 0.749 | 1372 | 24.348 | 0.775 | 0 | +7.517 ± 1.005 |
| th | 8 | 13.961 | 1.833 | 1587 | 23.210 | 4.169 | 2 | +9.249 ± 1.166 |
| lin | 1 | 5.979 | 0.026 | 0 | 5.972 | 0.024 | 0 | -0.007 ± 0.010 |
| lin | 2 | 5.977 | 0.141 | 2 | 5.971 | 0.146 | 0 | -0.006 ± 0.021 |
| lin | 3 | 5.937 | 0.138 | 60 | 5.976 | 0.142 | 0 | +0.039 ± 0.029 |
| lin | 5 | 5.589 | 0.611 | 1127 | 5.971 | 0.716 | 0 | +0.382 ± 0.085 |
| lin | 8 | 4.724 | 1.542 | 1590 | 5.907 | 2.572 | 3 | +1.183 ± 0.124 |

With slow_box, F at k = 3 against F at k = 1 on the same seeds: th +0.066 ± 0.300, lin -0.003 ± 0.020 (as shipped:
-2.110 ± 0.593 and -0.042 ± 0.025). Today's ship at 01baada (old ICM, separate runs at other loads): th k = 1 / 2 / 3
24.316 / 24.137 / 22.171 with 5 / 61 / 438 panic tables; lin 5.980 / 5.923 / 5.825 with 13 / 219 / 519.
Real contention (a busy process on each pinned core): slow_box +0.023 ± 0.052 (lin), +0.158 ± 0.686 (th), no panic.

- **Largest risk left, not mine:** a kit whose hand-end signal has no chip deltas makes the adapter run hand_end inside
  the next decision; F's hand_end (two full Heroes) is twice its decision. With every hand_end there, F on a 3x box
  times out on 25% of decisions (-4.7 points on th). climb/h3-kit-fixes owns hand-end cost; numbers and two fixes are in
  the section "The adapter's deferred hand_end".

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

## Candidates on lin, k = 1 and k = 2 (22:14-22:32, load 3.4-8.1)

k = 1: F 5.979 ± 0.111, 0.026 timeouts a table, no panic; candidates -0.011 to +0.001 (F_lean -0.011 ± 0.010, its
governor never fired: timeout noise), F_lad8 -0.007 ± 0.010. k = 2: F 5.977, 0.141 timeouts, 2 panic tables;
candidates -0.024 to +0.002, none beyond noise (F_lad8 -0.006 ± 0.021). The baseline run at k = 2 had 219 panic
tables at load 6.8-7.9; this one 2 at 5.7-8.1: how often this host's noise clusters varies from run to run, and the
cliff's cost with it.

## What each level costs in strength (model mode: --det --free, k = 1, seeds 10000-10199 x 8; 22:33-22:46)

A whole table played at the level (`start_level`), paired against F on the same deals:

| level | th (100-point table) | lin (8..1) |
|---|---|---|
| F_dl8, F_lad8 (the governor itself) | +0.000 ± 0.000 (bit-identical) | +0.000 ± 0.000 (bit-identical) |
| noshadow | +0.056 ± 0.364 | -0.026 ± 0.029 |
| lean | -0.627 ± 1.005 | +0.000 ± 0.000 (no exact ICM under 8..1) |
| hero (every section to the hero member) | -1.306 ± 1.247 | -0.150 ± 0.118 |
| base (hybrid3_x's play) | -1.817 ± 1.172 | -0.225 ± 0.114 |
| cheap (today's panic) | -13.237 ± 1.131 | -1.580 ± 0.141 |

The ladder's order (noshadow, lean, hero, then cheap) is the order of these costs; the cliff jumps straight to the
last row. In model mode the governor cannot fire (panic_after is 10^9), so F with the recipe plays F's exact game.

## Safety: far slower boxes, th (22:46-22:58, load 3.4-7.0 at k = 5, 4.4-5.2 at k = 8)

| bot | k | points ± 95% | - F same run | timeouts / table | panic tables | calls in panic / degraded |
|---|---|---|---|---|---|---|
| F | 5 | 16.830 ± 0.917 | - | 0.749 | 1372 | 56.3% / - |
| F_nopanic | 5 | 23.847 ± 1.056 | +7.016 ± 0.947 | 0.808 | 0 | 0 / 0 |
| F_dl8 | 5 | 23.221 ± 1.017 | +6.391 ± 0.907 | 0.769 | 218 | 5.7% / 0 |
| F_lad8 (slow_box) | 5 | 24.348 ± 1.084 | +7.517 ± 1.005 | 0.775 | 0 | 0 / 1.7% |
| Hero | 5 | 23.281 ± 1.054 | +6.450 ± 1.186 | 0.160 | 7 | 0.1% / - |
| F | 8 | 13.961 ± 0.730 | - | 1.833 | 1587 | 95.0% / - |
| F_nopanic | 8 | 23.588 ± 1.057 | +9.627 ± 1.121 | 5.918 | 0 | 0 / 0 |
| F_dl8 | 8 | 16.811 ± 0.845 | +2.850 ± 0.933 | 3.054 | 1392 | 55.4% / - |
| F_lad8 (slow_box) | 8 | 23.210 ± 1.094 | +9.249 ± 1.166 | 4.169 | 2 | 0 / 41.3% (levels 1-3) |
| Hero | 8 | 19.825 ± 0.961 | +5.864 ± 1.073 | 0.690 | 500 | 11.9% / - |

The cliff is a collapse on a slow box: F at k = 5 is 7.5 below F with the recipe, at k = 8 9.2. With the recipe F at
k = 5 is still at its k = 1 level (24.35 vs 24.39). At k = 8 even six timeouts a table cost less than any level
(F_nopanic 23.59 vs the recipe's 23.21, inside noise), but a bot that never degrades folds every decision once the box
is slow enough that its median decision passes 1 ms (k of about 15-20 for F); the ladder's last step is there for
that box.

## Safety: far slower boxes, lin (22:58-23:09, load 3.9-6.6)

| bot | k | points ± 95% | - F same run | timeouts / table | panic tables | calls in panic / degraded |
|---|---|---|---|---|---|---|
| F | 5 | 5.589 ± 0.107 | - | 0.611 | 1127 | 34.3% / - |
| F_nopanic | 5 | 5.962 ± 0.113 | +0.373 ± 0.088 | 0.581 | 0 | 0 / 0 |
| F_dl8 | 5 | 5.929 ± 0.113 | +0.340 ± 0.085 | 0.639 | 53 | 1.2% / 0 |
| F_lad8 (slow_box) | 5 | 5.971 ± 0.111 | +0.382 ± 0.085 | 0.716 | 0 | 0 / 0.5% |
| Hero | 5 | 5.770 ± 0.099 | +0.181 ± 0.123 | 0.191 | 24 | 0.6% / - |
| F | 8 | 4.724 ± 0.101 | - | 1.542 | 1590 | 94.4% / - |
| F_nopanic | 8 | 5.966 ± 0.114 | +1.242 ± 0.127 | 2.751 | 0 | 0 / 0 |
| F_dl8 | 8 | 5.575 ± 0.106 | +0.851 ± 0.118 | 2.067 | 1224 | 36.0% / - |
| F_lad8 (slow_box) | 8 | 5.907 ± 0.108 | +1.183 ± 0.124 | 2.572 | 3 | 0.1% / 19.4% |
| Hero | 8 | 5.566 ± 0.099 | +0.842 ± 0.119 | 0.795 | 533 | 12.4% / - |

F with the recipe holds its k = 1 level (5.98) to k = 5 and loses 0.07 at k = 8; F as shipped loses 0.39 at k = 5
and 1.25 at k = 8.

## The adapter's deferred hand_end on a slow box (`--defer`, th, 23:09-23:22, load 6.1-7.7)

`--defer` delivers every hand_end at the top of the next act, inside the timed call: the adapter's behaviour for a kit
whose hand-end signal has no chip deltas, final stacks or showdown, on every hand (`hold_all`; by default only on hands
where a seat acted after our reply). Most of our decisions are the first of a hand (a preflop fold), so most calls
carry a hand_end.

| bot | k | points ± 95% | - F same run | timeouts / table | p50 / p99 us (box) |
|---|---|---|---|---|---|
| F | 1 | 24.550 ± 1.073 | - | 0.629 | 244 / 737 |
| F_lad8 (slow_box) | 1 | 24.438 ± 1.030 | -0.112 ± 0.518 | 0.705 | 245 / 759 |
| Hero | 1 | 23.045 ± 1.028 | -1.506 ± 1.251 | 0.215 | 116 / 447 |
| F | 3 | 19.663 ± 1.059 | - | 38.423 | 764 / 2124 |
| F_nopanic | 3 | 19.609 ± 1.076 | -0.054 ± 1.036 | 41.304 | 781 / 2193 |
| F_lad8 (slow_box) | 3 | 20.241 ± 1.038 | +0.578 ± 1.071 | 41.654 | 785 / 2135 |
| Hero | 3 | 22.684 ± 1.027 | +3.022 ± 1.299 | 4.826 | 350 / 1221 |

With hand_end in the timed call, F on a 3x box times out on a quarter of its decisions and loses ~4.7 points (of 100);
the governor cannot help (SafeBot times act only, and no level makes hand_end cheaper). This is the largest timing risk
found, and it is not mine to fix (climb/h3-kit-fixes owns hand-end cost). What I would hand them: (1) on a kit with no
chip deltas at hand end, `defer_hand_end = False` on the adapter keeps hand_end out of the timed call; (2) F runs two
full Hero hand_ends per hand (finding 3); the base's fallback Hero acts on ~0.1% of plain-table decisions
(`hero:core_none`: 3 in 4,495 on 16 tables), so computing its ICM curve lazily, at its first act after a hand end, is
bit-identical play and removes ~28% of F's hand_end; its profiler pass is another ~13%.

## Real contention (`--contend 1 --duty-ms 5,5 --cpus 6,7 --clock wall`, k = 1; 23:22-23:40, load 6.3-9.6)

Each worker pinned to a core shared with one busy process that wants half of it (exponential 5 ms busy / 5 ms asleep):

| bot | payouts | points ± 95% | - F same run | timeouts / table | panic tables |
|---|---|---|---|---|---|
| F | lin | 5.939 ± 0.112 | - | 1.239 | 32 |
| F_nopanic | lin | 5.969 ± 0.113 | +0.029 ± 0.058 | 1.256 | 0 |
| F_dl8 | lin | 5.975 ± 0.112 | +0.036 ± 0.055 | 1.289 | 19 |
| F_lad8 (slow_box) | lin | 5.962 ± 0.115 | +0.023 ± 0.052 | 1.268 | 0 |
| Hero | lin | 5.779 ± 0.102 | -0.160 ± 0.120 | 0.664 | 3 |
| F | th | 23.981 ± 0.997 | - | 1.413 | 87 |
| F_nopanic | th | 24.213 ± 1.075 | +0.232 ± 0.720 | 1.496 | 0 |
| F_dl8 | th | 24.204 ± 1.091 | +0.224 ± 0.739 | 1.457 | 50 |
| F_lad8 (slow_box) | th | 24.139 ± 1.057 | +0.158 ± 0.686 | 1.551 | 0 |
| Hero | th | 23.293 ± 1.019 | -0.687 ± 1.241 | 0.718 | 12 |

A shared core costs F 1.2-1.5 timeouts a table, the same with or without panic: a preemption lands mid-decision
whatever path is running. Hero's are half (decisions half as long, half the exposure) but it is weaker. The recipe
removes the panics and is level-to-ahead of F inside noise.

## What I would still try

- Hand-end cost in the timed call (owned by climb/h3-kit-fixes): `defer_hand_end = False` on a no-delta kit; a lazy
  ICM curve for the base's fallback Hero (bit-identical, ~28% of F's hand_end); then `slowbox run --defer` again.
- The ladder at k >= 8 steps down sooner than it pays (F_nopanic 23.59 vs 23.21 on th, 5.97 vs 5.91 on lin, inside
  noise): try 0.9 ms or 8 overruns in the window; and a speed estimate (the minimum of recent call times) to pick the
  level at table start instead of after the first cluster.
- `slow_box` on the fallbacks: it resolves for hybrid3_x (ladder: lean, then cheap) and Hero (window, recover) but is
  unmeasured there.
- The adapter's own cost (to_observation, the history rebuild) is in the kit's timer and dilates with k; the harness
  times bot.act only (the gate's p99 329 us vs ~240 us at a table). A `--kit` seat through hyperion/drills/adapter.py.
- The dilation model on real slower hardware (one run on a slower machine would calibrate it).
