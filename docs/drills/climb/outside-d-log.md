# The fourth outside judges: wiring and the one measurement (2026-11-04)

Three fresh builds wired as held-out judges (branch climb/outside-d, proposed addendum 16), then the upcoming ship
measured against them once. Nobody tunes on these numbers; F's code, dials and tables are untouched by this branch.

## What it found

- **No new bot beats F.** F is ahead of each of the three, beyond noise, in all eight cells. The closest is out_o11:
  F +1.142 ± 0.092 at `outside_d`, +0.787 ± 0.087 at `outside_d_strong`, 60.0% of heads-up tables.
- **An older judge does beat F, in the strong room.** At `outside_d_strong` out_reads (o8) outscores batch 8 by 0.138 ±
  0.093 (F - seat), beyond noise, and takes 22.3% of first places against F's 12.9%. elite5 is level on points (F
  +0.011 ± 0.087) and takes more firsts (17.8%). F ranks 2 of 8 by points, 3 of 8 by first places, and its share of firsts
  is barely above an even share (12.5%). One set of seeds.
- **The cells pay 8..1, as the outside fields do; the brief pays 10/7/5/4/3/2/1/0.** F reads the payouts it is given, so
  a flat table may itself hold down its firsts. Which way the strong room goes on the brief's payouts is not measured
  here: the arithmetic below is only a pointer (it puts batch 8 third), and F would play that table differently.
- **Batch 8 against batch 7:** none of the eight down; `outside_d` +0.037 ± 0.034 and `outside_d_strong` +0.091 ± 0.038 up
  (corrected), the rest level. Against out_reads batch 8 closes the gap from -0.280 ± 0.087 to -0.138 ± 0.093.

## The bots

| registry name | build | md5 of rival_bot.py | bytes | model-mode clock step |
|---|---|---|---|---|
| out_o9 | an unconventional team | f85066a0bd7e92551dad61a0d559bc89 | 32,121 | 18.8 us a read |
| out_o10 | a strict 60-minute team (built in about 48) | bedcbd0c079f847c005af61f8807db10 | 19,422 | 19.7 us a read |
| out_o11 | a prepared top team | 5f92fb3b1b7519f06b79234d41cfa5ba | 95,251 | 53.2 us a read |

Copied as out_reads was: the original and notebook in docs/drills/field/, the package copy in hyperion/sim/field/ below
a six-line origin header, read for wiring only (imports, clock, generator, table start). All three read
`time.perf_counter` through their module's `time` to guard work (out_o9 and out_o10 a sampler at 500 us, read every
fourth sample; out_o11 exact ICM at 450 us) and hold one generator, `self.rng`, seeded from seat and table size. None
opens a file, a socket or a process; out_o10 pauses the collector inside act() and restores it, out_o11 calls
gc.freeze() at import (as out_cfr does). out_o10 needs the brief's `kit` at import; hyperion.sim.field.load gives it.

**Steps.** Median wall time between consecutive clock reads inside one decision, in the real adapter at `outside_d`,
30 seeds x 8 rotations, 1 process, load 15 on 16 cores (the chain restarts at every act(), so the wait for other seats
never counts, and the recording clock is bound inside act(), after the module has loaded):

| bot | decisions | gaps | median us | p25 | p75 | p99 |
|---|---|---|---|---|---|---|
| out_o9 | 34,796 | 77,841 | 18.79 | 17.16 | 22.72 | 53.69 |
| out_o10 | 30,341 | 56,657 | 19.68 | 17.83 | 21.67 | 53.87 |
| out_o11 | 33,664 | 1,376 | 53.23 | 38.25 | 82.67 | 141.28 |

**In model mode the guards never bite at these steps:** 8 seeds of all eight cells replay identically with the clock
standing still (STEP_US 0). A forced step past the guard (400 us) trips it and still replays (a test). So the steps
matter little to these numbers; the bots play as on a quiet host.

## The checks

- **Identity (wiring, F's dials as on main; a756a42, code 5690ae77ef):** 10000:10040, confirm and guards: all 7 rows of
  goal/idchk34.md equal (points, n, timeouts, errors), and per-seed samples equal in all 14 chunks. The cell file names
  are unchanged. The cache directory key is not: it hashes the code version, the tree of hyperion/, which changes
  with any commit there (as out_reads' did), so a run after this merges plays its cells afresh and gets the same samples.
- **Identity (the measured tree, bcf949f, code 01ea9c0627):** `--base` BATCH8_OFF equals goal/idchk34.md's batch 7 and
  `--cand` {} equals goal/idchk39.md's batch 8 in all 7 rows.
- **Determinism:** two whole climb_accept runs of the eight cells on 96000:96009 (both specs, runout term; 4 workers and
  then 2, so different process histories): 16 chunk files, every field equal but the wall-clock ones (secs, load, p50,
  p99, max_us), content md5 e043736ef096e83ca4f1887f21e3639e.
- **Dials:** F with `--cand '{"dials": {}}'` at 77c5ea6 + climb/outside-d equals batch 8's own branch (ac1f18c + goal/b32/b8.json)
  in all 91 effective dials; goal/b8off.json equals BATCH8_OFF (21 keys).
- **Swallowed exceptions:** each bot catches its own errors, which the engine cannot see, so a diagnostic wrapper counted
  them over 8 seeds of all eight cells: 0 in 23,561 (out_o9), 20,662 (out_o10) and 21,146 (out_o11) decisions.
- **Suite:** `-m "not timing"` at a756a42: 1444 passed, 1 skipped, 114 deselected. The two touched test files pass on the
  measured tree too (68).

## The measurement

Once, at bcf949f: climb/batch8-freeze's 77c5ea6 merged with climb/outside-d, detached. Fresh judge seeds, in no earlier
log. Model mode, runout term on (the corrected points decide; raw beside them), batch 7 as the pair.

    tools/climb_accept.py --base goal/b8off.json --cand '{"dials": {}}' --set 70000:70400 --stages judges \
        --judge-cells outside_d,outside_d_strong,outside_d_o9_hu,outside_d_o9_3,outside_d_o10_hu,outside_d_o10_3,outside_d_o11_hu,outside_d_o11_3 \
        --runout-term --workers 4

Read these with the following in mind.
- Rotations are the table size's, as in the exploit cells: 400 seeds x 8 rotations at 8-max (3,200 tables), x 2 heads-up
  (800), x 3 three-handed (1,200). Heads-up pays 10/7 and three-handed 10/7/5, so those points are not comparable to 8-max.
- `night.k` is a drawn seat, a different bot table by table, so its row is a pool average. Its timeouts and exceptions are
  the pool's weak and broken group, as designed; nothing about the new bots.
- F - seat is paired seed by seed on the corrected points: the seats of a table share its luck, so this interval, not
  the two seats' own, says who is ahead.
- The three were built for 8-max, not for short tables, and F has tuned short-handed routes. F's big short-handed wins say
  little about F against a team that prepared those formats (exploiter 4 is the better test of that).
- The two 8-max cells seat strong bots in the second and a night room in the first: compare a bot across them with care.

### Batch 8 against batch 7, the same deals

| cell | batch 7 | batch 8 | batch 8 - batch 7 (corrected) | | raw difference | | F's rank by points | by first places |
|---|---|---|---|---|---|---|---|---|
| outside_d | 5.833 | 5.871 | +0.037 ± 0.034 | UP | +0.015 ± 0.044 | level | 1 of 8 | 1 of 8 |
| outside_d_strong | 4.815 | 4.906 | +0.091 ± 0.038 | UP | +0.093 ± 0.051 | UP | 2 of 8 | 3 of 8 |
| outside_d_o9_hu +hu | 9.236 | 9.247 | +0.011 ± 0.045 | level | -0.045 ± 0.067 | level | 1 of 2 | 1 of 2 |
| outside_d_o9_3 +three | 8.435 | 8.431 | -0.005 ± 0.061 | level | -0.020 ± 0.079 | level | 1 of 3 | 1 of 3 |
| outside_d_o10_hu +hu | 9.020 | 9.031 | +0.011 ± 0.034 | level | +0.041 ± 0.054 | level | 1 of 2 | 1 of 2 |
| outside_d_o10_3 +three | 8.487 | 8.503 | +0.015 ± 0.061 | level | -0.006 ± 0.084 | level | 1 of 3 | 1 of 3 |
| outside_d_o11_hu +hu | 8.851 | 8.858 | +0.008 ± 0.038 | level | -0.030 ± 0.062 | level | 1 of 2 | 1 of 2 |
| outside_d_o11_3 +three | 8.415 | 8.451 | +0.036 ± 0.059 | level | +0.122 ± 0.085 | UP | 1 of 3 | 1 of 3 |

### Every seat, batch 8 in F's seat

**outside_d** (F ranks 1 of 8 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 5.871 ± 0.062 | 5.882 ± 0.068 |  |  | 34.7 | 61.6 | 0 | 0 |
| out_o11 | 4.729 ± 0.064 | 4.733 ± 0.076 | +1.142 ± 0.092 | F ahead | 14.1 | 84.6 | 0 | 0 |
| out_o9 | 4.371 ± 0.072 | 4.346 ± 0.078 | +1.500 ± 0.095 | F ahead | 10.9 | 85.3 | 0 | 0 |
| out_o10 | 4.362 ± 0.069 | 4.376 ± 0.082 | +1.509 ± 0.091 | F ahead | 10.9 | 85.2 | 0 | 0 |
| night.4 | 4.197 ± 0.113 | 4.178 ± 0.116 | +1.674 ± 0.136 | F ahead | 7.0 | 89.4 | 15397 | 2877 |
| night.3 | 4.171 ± 0.116 | 4.162 ± 0.122 | +1.700 ± 0.139 | F ahead | 7.8 | 88.8 | 13016 | 965 |
| night.1 | 4.160 ± 0.108 | 4.160 ± 0.112 | +1.711 ± 0.133 | F ahead | 7.0 | 89.4 | 13045 | 7843 |
| night.2 | 4.140 ± 0.113 | 4.164 ± 0.118 | +1.731 ± 0.133 | F ahead | 7.6 | 88.5 | 12176 | 7674 |

**outside_d_strong** (F ranks 2 of 8 by points, 3 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| out_reads | 5.044 ± 0.064 | 5.042 ± 0.078 | -0.138 ± 0.093 | F behind | 22.3 | 76.8 | 0 | 0 |
| F | 4.906 ± 0.056 | 4.888 ± 0.067 |  |  | 12.9 | 84.3 | 0 | 0 |
| elite5 | 4.895 ± 0.063 | 4.863 ± 0.076 | +0.011 ± 0.087 | level | 17.8 | 79.8 | 0 | 0 |
| rival4 | 4.740 ± 0.050 | 4.744 ± 0.061 | +0.166 ± 0.077 | F ahead | 5.8 | 90.2 | 0 | 0 |
| out_cfr | 4.451 ± 0.060 | 4.489 ± 0.078 | +0.455 ± 0.085 | F ahead | 12.4 | 85.0 | 0 | 0 |
| out_o11 | 4.119 ± 0.059 | 4.107 ± 0.075 | +0.787 ± 0.087 | F ahead | 10.3 | 88.9 | 0 | 0 |
| out_o10 | 3.956 ± 0.061 | 3.964 ± 0.074 | +0.950 ± 0.090 | F ahead | 7.9 | 89.1 | 0 | 0 |
| out_o9 | 3.889 ± 0.064 | 3.903 ± 0.076 | +1.016 ± 0.090 | F ahead | 10.5 | 87.1 | 0 | 0 |

**outside_d_o9_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 9.247 ± 0.069 | 9.209 ± 0.088 |  |  | 73.6 | 26.4 | 0 | 0 |
| out_o9 | 7.753 ± 0.069 | 7.791 ± 0.088 | +1.494 ± 0.138 | F ahead | 26.4 | 73.6 | 0 | 0 |

**outside_d_o9_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.431 ± 0.091 | 8.469 ± 0.107 |  |  | 61.8 | 38.2 | 0 | 0 |
| out_o9 | 7.010 ± 0.086 | 6.937 ± 0.102 | +1.421 ± 0.155 | F ahead | 22.4 | 77.6 | 0 | 0 |
| night.1 | 6.559 ± 0.085 | 6.594 ± 0.096 | +1.872 ± 0.154 | F ahead | 15.8 | 84.1 | 4231 | 2145 |

**outside_d_o10_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 9.031 ± 0.072 | 9.040 ± 0.091 |  |  | 68.0 | 32.0 | 0 | 0 |
| out_o10 | 7.969 ± 0.072 | 7.960 ± 0.091 | +1.061 ± 0.145 | F ahead | 32.0 | 68.0 | 0 | 0 |

**outside_d_o10_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.503 ± 0.094 | 8.498 ± 0.118 |  |  | 62.3 | 37.8 | 0 | 0 |
| out_o10 | 6.794 ± 0.088 | 6.797 ± 0.105 | +1.709 ± 0.158 | F ahead | 22.0 | 78.0 | 0 | 0 |
| night.1 | 6.704 ± 0.090 | 6.706 ± 0.100 | +1.799 ± 0.162 | F ahead | 15.8 | 84.2 | 3647 | 2060 |

**outside_d_o11_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.858 ± 0.070 | 8.800 ± 0.090 |  |  | 60.0 | 40.0 | 0 | 0 |
| out_o11 | 8.142 ± 0.070 | 8.200 ± 0.090 | +0.717 ± 0.141 | F ahead | 40.0 | 60.0 | 0 | 0 |

**outside_d_o11_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.451 ± 0.100 | 8.510 ± 0.111 |  |  | 62.0 | 38.0 | 0 | 0 |
| out_o11 | 7.078 ± 0.082 | 7.048 ± 0.102 | +1.373 ± 0.162 | F ahead | 25.5 | 74.5 | 0 | 0 |
| night.1 | 6.471 ± 0.084 | 6.442 ± 0.092 | +1.980 ± 0.165 | F ahead | 12.5 | 87.5 | 3719 | 2070 |


### Every seat, batch 7 in F's seat

**outside_d** (F ranks 1 of 8 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 5.833 ± 0.062 | 5.868 ± 0.069 |  |  | 33.8 | 62.4 | 0 | 0 |
| out_o11 | 4.750 ± 0.061 | 4.734 ± 0.073 | +1.083 ± 0.089 | F ahead | 13.9 | 84.4 | 0 | 0 |
| out_o9 | 4.391 ± 0.073 | 4.362 ± 0.081 | +1.443 ± 0.099 | F ahead | 11.3 | 85.0 | 0 | 0 |
| out_o10 | 4.376 ± 0.071 | 4.389 ± 0.082 | +1.457 ± 0.094 | F ahead | 10.6 | 85.7 | 0 | 0 |
| night.4 | 4.207 ± 0.112 | 4.208 ± 0.117 | +1.626 ± 0.135 | F ahead | 8.0 | 88.4 | 15447 | 2863 |
| night.1 | 4.162 ± 0.107 | 4.142 ± 0.110 | +1.671 ± 0.131 | F ahead | 7.0 | 89.4 | 13180 | 7865 |
| night.3 | 4.154 ± 0.116 | 4.157 ± 0.123 | +1.680 ± 0.141 | F ahead | 7.8 | 88.6 | 12971 | 963 |
| night.2 | 4.126 ± 0.112 | 4.139 ± 0.117 | +1.708 ± 0.131 | F ahead | 7.5 | 89.1 | 12136 | 7661 |

**outside_d_strong** (F ranks 3 of 8 by points, 3 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| out_reads | 5.095 ± 0.060 | 5.112 ± 0.076 | -0.280 ± 0.087 | F behind | 22.8 | 76.1 | 0 | 0 |
| elite5 | 4.929 ± 0.061 | 4.896 ± 0.077 | -0.114 ± 0.083 | F behind | 19.0 | 78.7 | 0 | 0 |
| F | 4.815 ± 0.053 | 4.795 ± 0.062 |  |  | 11.4 | 85.8 | 0 | 0 |
| rival4 | 4.744 ± 0.048 | 4.713 ± 0.059 | +0.071 ± 0.076 | level | 5.5 | 91.1 | 0 | 0 |
| out_cfr | 4.422 ± 0.059 | 4.456 ± 0.076 | +0.393 ± 0.083 | F ahead | 11.3 | 86.0 | 0 | 0 |
| out_o11 | 4.119 ± 0.060 | 4.101 ± 0.074 | +0.696 ± 0.084 | F ahead | 10.5 | 88.9 | 0 | 0 |
| out_o10 | 3.974 ± 0.061 | 3.983 ± 0.076 | +0.841 ± 0.088 | F ahead | 8.6 | 88.6 | 0 | 0 |
| out_o9 | 3.903 ± 0.062 | 3.945 ± 0.074 | +0.912 ± 0.086 | F ahead | 11.0 | 86.5 | 0 | 0 |

**outside_d_o9_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 9.236 ± 0.066 | 9.254 ± 0.085 |  |  | 75.1 | 24.9 | 0 | 0 |
| out_o9 | 7.764 ± 0.066 | 7.746 ± 0.085 | +1.472 ± 0.132 | F ahead | 24.9 | 75.1 | 0 | 0 |

**outside_d_o9_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.435 ± 0.095 | 8.489 ± 0.110 |  |  | 62.4 | 37.6 | 0 | 0 |
| out_o9 | 6.971 ± 0.085 | 6.913 ± 0.097 | +1.464 ± 0.157 | F ahead | 21.3 | 78.7 | 0 | 0 |
| night.1 | 6.593 ± 0.089 | 6.598 ± 0.100 | +1.842 ± 0.163 | F ahead | 16.2 | 83.8 | 4237 | 2128 |

**outside_d_o10_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 9.020 ± 0.070 | 8.999 ± 0.092 |  |  | 66.6 | 33.4 | 0 | 0 |
| out_o10 | 7.980 ± 0.070 | 8.001 ± 0.092 | +1.040 ± 0.140 | F ahead | 33.4 | 66.6 | 0 | 0 |

**outside_d_o10_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.487 ± 0.097 | 8.503 ± 0.114 |  |  | 62.0 | 38.0 | 0 | 0 |
| out_o10 | 6.825 ± 0.090 | 6.833 ± 0.104 | +1.663 ± 0.162 | F ahead | 22.3 | 77.7 | 0 | 0 |
| night.1 | 6.688 ± 0.092 | 6.663 ± 0.101 | +1.799 ± 0.166 | F ahead | 15.7 | 84.3 | 3699 | 2058 |

**outside_d_o11_hu +hu** (F ranks 1 of 2 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.851 ± 0.071 | 8.830 ± 0.090 |  |  | 61.0 | 39.0 | 0 | 0 |
| out_o11 | 8.149 ± 0.071 | 8.170 ± 0.090 | +0.702 ± 0.141 | F ahead | 39.0 | 61.0 | 0 | 0 |

**outside_d_o11_3 +three** (F ranks 1 of 3 by points, 1 by first places)

| seat | points (corrected) | points (raw) | F - seat (corrected) | | 1st % | bust % | tmo | exc |
|---|---|---|---|---|---|---|---|---|
| F | 8.415 ± 0.095 | 8.388 ± 0.108 |  |  | 59.3 | 40.7 | 0 | 0 |
| out_o11 | 7.102 ± 0.081 | 7.087 ± 0.100 | +1.313 ± 0.157 | F ahead | 26.7 | 73.3 | 0 | 0 |
| night.1 | 6.484 ± 0.080 | 6.525 ± 0.091 | +1.931 ± 0.156 | F ahead | 14.0 | 86.0 | 3774 | 2091 |

## The 8-max cells on the brief's payouts

Arithmetic on the recorded finishes, no new play: 10/7/5/4/3/2/1/0 on each seat's place shares, without intervals. Not
what these seats would score there. Every seat played the 8..1 tables, and F reads the payouts it is given, so on the
brief's table F would play differently; none of the three new bots, nor out_reads or elite5, reads the rules' payouts
(out_o11's ICM is hard-coded to the brief's). As arithmetic it is close (8..1 on the same shares gives F 4.886 where its raw points at
`outside_d_strong` are 4.888). A real answer means playing the cell at the brief's payouts, which this run did not.

| cell, F = batch 8 | seat | points on 10/7/5/4/3/2/1/0 | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|---|---|
| outside_d | F | 6.063 | 34.7 | 13.3 | 12.6 | 12.4 | 10.6 | 8.5 | 4.9 | 3.0 |
| outside_d | out_o11 | 4.292 | 14.1 | 13.2 | 13.3 | 11.5 | 14.0 | 14.6 | 12.2 | 7.1 |
| outside_d | out_o10 | 3.834 | 10.9 | 13.3 | 12.4 | 10.9 | 11.7 | 13.1 | 13.8 | 13.8 |
| outside_d | out_o9 | 3.808 | 10.9 | 13.0 | 9.9 | 11.1 | 13.8 | 15.1 | 15.0 | 11.2 |
| outside_d_strong | out_reads | 4.838 | 22.3 | 12.4 | 11.2 | 12.1 | 12.6 | 11.1 | 9.3 | 8.9 |
| outside_d_strong | elite5 | 4.535 | 17.8 | 13.5 | 13.0 | 12.7 | 11.0 | 10.7 | 10.5 | 10.7 |
| outside_d_strong | F | 4.420 | 12.9 | 14.4 | 14.8 | 15.0 | 14.3 | 12.6 | 9.8 | 6.2 |
| outside_d_strong | rival4 | 4.046 | 5.8 | 13.5 | 18.2 | 19.3 | 16.9 | 12.4 | 8.2 | 5.7 |
| outside_d_strong | out_cfr | 3.984 | 12.4 | 12.2 | 12.8 | 12.5 | 11.8 | 12.9 | 12.8 | 12.5 |
| outside_d_strong | out_o11 | 3.530 | 10.3 | 11.2 | 9.7 | 9.3 | 12.1 | 15.8 | 17.4 | 14.1 |
| outside_d_strong | out_o9 | 3.327 | 10.5 | 10.5 | 9.1 | 8.9 | 10.0 | 13.2 | 16.8 | 21.0 |
| outside_d_strong | out_o10 | 3.320 | 7.9 | 12.1 | 11.2 | 10.2 | 11.2 | 11.2 | 15.2 | 21.0 |

## Timeouts in strict mode

The bots as built, wall clock on, a call over 1 ms a fold; batch 8 in F's seat, 40 seeds (97000-97039) of each cell, one
process at nice 5, load 16-17 on 16 cores. Mostly the box: maxima of 4-12 ms hit every seat at `outside_d`, and F's rate is
the highest of these four. An upper bound for a quiet host, not an estimate of it; each bot's notebook attributes its own spikes to the
scheduler too. Too few to change a result, and none of the three threw an exception.

| seat | calls | timeouts | % |
|---|---|---|---|
| F | 171,713 | 80 | 0.047 |
| out_o9 | 113,877 | 31 | 0.027 |
| out_o10 | 103,886 | 29 | 0.028 |
| out_o11 | 104,642 | 8 | 0.008 |

| cell | seat | calls | tmo | tmo % | exc | ill | safe_err | p50 us | p99 us | max us | load |
|---|---|---|---|---|---|---|---|---|---|---|---|
| outside_d | F | 57003 | 47 | 0.082 | 0 | 0 | 0 | 124 | 256 | 11180 | 17.2 |
| outside_d | out_o10 | 42413 | 21 | 0.050 | 0 | 0 | 0 | 18 | 277 | 6162 | 17.2 |
| outside_d | out_o11 | 42870 | 6 | 0.014 | 0 | 0 | 0 | 26 | 187 | 4241 | 17.2 |
| outside_d | out_o9 | 45312 | 25 | 0.055 | 0 | 0 | 0 | 23 | 297 | 5964 | 17.2 |
| outside_d_strong | F | 50989 | 12 | 0.024 | 0 | 0 | 0 | 126 | 240 | 3494 | 16.4 |
| outside_d_strong | out_o10 | 40118 | 1 | 0.002 | 0 | 0 | 0 | 17 | 272 | 1067 | 16.4 |
| outside_d_strong | out_o11 | 41233 | 1 | 0.002 | 0 | 0 | 0 | 26 | 194 | 1064 | 16.4 |
| outside_d_strong | out_o9 | 44148 | 4 | 0.009 | 0 | 0 | 0 | 23 | 285 | 1913 | 16.4 |
| outside_d_o9_hu | F | 6898 | 0 | 0.000 | 0 | 0 | 0 | 90 | 180 | 526 | 15.7 |
| outside_d_o9_hu | out_o9 | 9054 | 0 | 0.000 | 0 | 0 | 0 | 17 | 274 | 928 | 15.7 |
| outside_d_o9_3 | F | 14944 | 1 | 0.007 | 0 | 0 | 0 | 99 | 199 | 1847 | 15.7 |
| outside_d_o9_3 | out_o9 | 15363 | 2 | 0.013 | 0 | 0 | 0 | 20 | 284 | 1285 | 15.7 |
| outside_d_o10_hu | F | 6358 | 0 | 0.000 | 0 | 0 | 0 | 91 | 199 | 963 | 15.6 |
| outside_d_o10_hu | out_o10 | 7659 | 0 | 0.000 | 0 | 0 | 0 | 14 | 285 | 625 | 15.6 |
| outside_d_o10_3 | F | 14734 | 11 | 0.075 | 0 | 0 | 0 | 100 | 206 | 4204 | 15.6 |
| outside_d_o10_3 | out_o10 | 13696 | 7 | 0.051 | 0 | 0 | 0 | 15 | 288 | 9803 | 15.6 |
| outside_d_o11_hu | F | 6508 | 7 | 0.108 | 0 | 0 | 0 | 92 | 190 | 3361 | 15.6 |
| outside_d_o11_hu | out_o11 | 7170 | 1 | 0.014 | 0 | 0 | 0 | 26 | 72 | 1316 | 15.6 |
| outside_d_o11_3 | F | 14279 | 2 | 0.014 | 0 | 0 | 0 | 99 | 188 | 2122 | 15.8 |
| outside_d_o11_3 | out_o11 | 13369 | 0 | 0.000 | 0 | 0 | 0 | 23 | 74 | 548 | 15.8 |

## What looks wrong, and what does not

- **Nothing wrong with the three.** 0 engine exceptions, 0 illegal actions, 0 modelled timeouts over the run, 0 swallowed
  errors in the diagnostic; each result means what it says.
- **`night.k`, as designed:** in model mode 3-4% of calls time out and up to 2% raise in those rows (the pool's broken
  bots). `outside_d` is therefore a softer room than its name suggests: F's 34.7% of firsts is earned partly off them.
- **`outside_d_strong` pays 8..1, not the brief's table,** so its ranks may not carry to the real payouts, in either
  direction (above). A run on the brief's table would be a different cell; this branch keeps the outside fields' payouts.
- **Worth asking of out_reads:** it now leads a room F does not, on one set. That is a judge's result and nobody tunes on
  it; a second held-out set would say whether it stands.
