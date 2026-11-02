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
