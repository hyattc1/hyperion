# Final core comparison: running log

The single final comparison that decides which bot ships: Hero against the two hybrids, each with the exploit layer,
on the same seats, deals and opponents. Measurements land here field by field; the summary goes to docs/decisions.md,
"Final core comparison". The owner makes the call on what ships.

## 07:32 ET: protocol

- **Code:** a clean worktree at `ac2db3e` (HEAD of main). Nothing under `hyperion/` changed since `0d660dc`, where the
  hybrid agent's round 3 and judge rows ran, except one comment in `bestiary.py`. This pass edits no code.
- **Seating:** every candidate sits in Hero's seat through `<field>@<bot>`, so the seat, the deals and the opponents'
  seeds are the same for all five. The deals are duplicate (`rotate`), seed 7, table seeds `7 * 1_000_003 + t`. Seeds
  0-199 are therefore the same deals as the hybrid agent's 200-seed runs.
- **Seeds:** 400 per field for the main and judge fields; 200 for the payout tables; 200 unrotated tables per entry for
  the variants.
- **Primary mode `model`:** the engine's deterministic timeout model. For the Heroes, Hero clones and hybrids, SafeBot
  panic and the hybrids' soft deadline are off (`panic_after` 10^9, `soft_us` 10^6), as in the exploit pass and the
  hybrid agent's rounds 2 and 3. Nothing then reads the wall clock except rival 2's sampler, in `top`, `top2` and
  `judge_top`, and the rival 2 core's sampler in `hybrid_x`; both are time-boxed by design.
- **Strict mode** (wall clock, everything as shipped, SafeBot panic on) as a second column, on realistic and judge only.
- **Paired deltas** are means of per-seed differences against `hero` on the same seeds, with 95% intervals. Uniform is
  4.50 on the default 8..1 table.
- **Workers:** four, each candidate's chunks interleaved with the others' (50 seeds per job), so the five candidates of a
  field run side by side at the same load. Load is the 1-minute average at the start and end of each job.
- **Scripts:** `fc/fc.py` (driver) and `fc/an.py` (tables) in the session scratchpad; per-seed samples in `fc/out/`.

## 07:30: what each candidate runs (a short check before the big runs)

`fc/check.py` and `fc/check2.py` build each bot through the bestiary, as the runs do, and print its configuration.

| candidate | decision core | exploit layer in front | its fallback Hero's own layer |
|---|---|---|---|
| `hero` | Hero | Hero's own: `Config().exploit` = `ShippedExploitParams` (bet when checked to, dead-seat steal, steal at fold product 0.7) | (is Hero) |
| `hybrid_x` | rival 2's | `HybridConfig.exploit = "hero"` = `Config().exploit`, the same `ShippedExploitParams` object values | neutral `ExploitParams()` (switched off, so one layer sees every decision) |
| `hybrid3_x` | rival 3's | the same shipped params | neutral (off) |
| `hybrid3` | rival 3's | none | **shipped**: the fallback Hero carries the layer, but it only sees the decisions routed to Hero (on plain hold'em ~0.03%: `hero:core_none`), so it hardly ever fires there; on the 14 variant tables Hero plays whole, it is fully on |
| `rival3` | rival 3 as built, kit adapter, no shell | rival 3's own seat reads | - |

The layer's params come from `Config()`, not from `HERO_CONFIG`, so the panic override the model runs pass to every
Hero does not touch them. A two-seed realistic smoke confirms the layer fires: `hybrid3_x` bet_checked 55, steal_fold
11, steal 3 over 16 tables; `hybrid_x` 52 / 93 / 21; `hybrid3` none.

`judge_top` already seats rival 3, so rival 3's reference row there is a second copy of it in Hero's seat
(`rival3_seat`, the same class under another name, so the report keeps the two seats apart).

On the judge: the hybrid agent measured the same code on `judge` and `judge_top` at 06:07 (200 seeds, model mode,
`docs/drills/hybrid-log.md`). This run is the final one: 400 seeds, which include those 200 deals. No candidate
changed between the two, and nobody tuned on either.

## 07:32-07:39: `judge` (the judge field, measured once), model mode, 400 seeds x 8

Rival 4 in rival 3's holdout seat; never tuned on. Ranked by points; paired against Hero on the same 400 seeds.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.176 ± 0.076 | +0.135 ± 0.097 | 1 of 8 (leader hybrid3_x 6.18) | 53 | 44 | - rival4 +0.583 ± 0.109 | 24-34 |
| 2 | hybrid3 (no layer) | 6.041 ± 0.074 | +0.001 ± 0.100 | 1 of 8 (leader hybrid3 6.04) | 48 | 49 | - rival4 +0.407 ± 0.109 | 25-34 |
| 3 | Hero | 6.041 ± 0.079 | - | 1 of 8 (leader hero 6.04) | 49 | 48 | - rival4 +0.398 ± 0.108 | 24-34 |
| 4 | rival3 (raw, reference) | 5.951 ± 0.077 | -0.090 ± 0.099 | 1 of 8 (leader rival3 5.95) | 47 | 51 | - rival4 +0.297 ± 0.112 | 24-34 |
| 5 | hybrid_x | 5.691 ± 0.082 | -0.350 ± 0.099 | 2 of 8 (leader rival4 5.75) | 43 | 54 | - rival4 -0.058 ± 0.110 | 24-34 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 576,255 | 29 / 132 | 1394 (0.242%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 487,653 | 36 / 301 | 1967 (0.403%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 93.43%; exploit:steal_fold 6.87, exploit:bet_checked 3.29, exploit:steal 0.63 |
| hybrid3_x | 531,692 | 40 / 230 | 1943 (0.365%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 96.89%; exploit:bet_checked 3.57, exploit:steal_fold 1.54, exploit:steal 0.14, hero:core_none 0.11 |
| rival3 (raw, reference) | 526,265 | 26 / 126 | 1267 (0.241%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 540,441 | 31 / 154 | 1473 (0.273%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.95%; hero:core_none 0.09 |


"wall >= 1 ms" is the share of the candidate's decisions (the first call of each table excluded) that took 1 ms or
more of wall time at this load; mode "model" folds none of them (no candidate reports a modelled cost), so these
count host preemption plus each bot's own tail. "engine timeouts" are the decisions the engine folded: 0 by construction.

Reproducibility check on the first 200 seeds (the hybrid agent's judge deals, 06:07): Hero 6.034 ± 0.111 here and
there, exactly, so the deals and Hero are the same; hybrid3_x 6.215 (there 6.210; not traced: any wall-clock guard
left on in that run, such as the 350 us soft deadline, moves a few decisions to Hero on a loaded host); hybrid3 6.109
(6.094, with its fallback Hero's layer off there);
hybrid_x 5.707 (5.657: rival 2's sampler is on the wall clock). On those 200 seeds, hybrid3_x - Hero +0.180 ± 0.134.
On all 400: **hybrid3_x - Hero +0.135 ± 0.097**, outside noise but only just; hybrid3 (no layer) +0.001; rival3 raw
-0.090 ± 0.099; **hybrid_x -0.350 ± 0.099**, the only candidate the judge out-scores.

## 07:39-07:45: `judge_top` (the judge's strong room, measured once), model mode, 400 seeds x 8

hero, rival1, rival2, rival3, rival4, pushfold, tag, loose_aggro; each candidate in Hero's seat. rival3's reference row is a second copy of rival 3 in Hero's seat (`rival3_seat`); its "- rival3" gap is against the other copy.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid_x | 5.131 ± 0.075 | +0.300 ± 0.098 | 1 of 8 (leader hybrid_x 5.13) | 25 | 67 | - rival4 +0.611 ± 0.110; - rival1 +0.391 ± 0.115; - rival3 +0.319 ± 0.119 | 25-26 |
| 2 | hybrid3_x | 4.892 ± 0.076 | +0.061 ± 0.100 | 2 of 8 (leader rival2 5.00) | 22 | 73 | - rival4 +0.400 ± 0.107; - rival1 +0.108 ± 0.116; - rival3 +0.001 ± 0.123 | 25-26 |
| 3 | hybrid3 (no layer) | 4.839 ± 0.075 | +0.008 ± 0.100 | 3 of 8 (leader rival2 4.96) | 20 | 75 | - rival4 +0.336 ± 0.105; - rival1 +0.058 ± 0.121; - rival3 -0.081 ± 0.119 | 25-26 |
| 4 | Hero | 4.831 ± 0.077 | - | 3 of 8 (leader rival2 5.01) | 24 | 73 | - rival4 +0.236 ± 0.107; - rival1 +0.147 ± 0.120; - rival3 -0.023 ± 0.123 | 25-26 |
| 5 | rival3 (raw, reference) | 4.828 ± 0.078 | -0.004 ± 0.106 | 3 of 8 (leader rival2 4.97) | 21 | 74 | - rival4 +0.290 ± 0.108; - rival1 +0.040 ± 0.119; - rival3 -0.068 ± 0.121 | 25-26 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 540,775 | 33 / 143 | 731 (0.135%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 516,565 | 37 / 238 | 1016 (0.197%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 95.67%; exploit:steal_fold 4.56, exploit:bet_checked 2.54, exploit:steal 0.25 |
| hybrid3_x | 512,694 | 42 / 185 | 969 (0.189%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 97.73%; exploit:bet_checked 2.65, exploit:steal_fold 1.01, exploit:steal 0.05, hero:core_none 0.04 |
| rival3 (raw, reference) | 509,968 | 26 / 108 | 665 (0.130%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 517,051 | 32 / 152 | 655 (0.127%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.98%; hero:core_none 0.03 |


Rival 2 is at this table, and its sampler is on the wall clock, so the field itself moves a little with the host: on the
first 200 seeds Hero scores 4.767 here against 4.814 in the hybrid agent's run on the same deals (load 41-46 there,
25-26 here). The five candidates ran interleaved at one load, so the pairs share it.

**hybrid_x leads (+0.300 ± 0.098), outside noise; hybrid3_x +0.061 ± 0.100, hybrid3 +0.008 and rival3 -0.004 are level
with Hero.** Every candidate beats rival 4 here (+0.24 to +0.61). Rival 2 leads the room whenever hybrid_x is not in it.

## 07:45-07:51: `realistic`, model mode, 400 seeds x 8

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.120 ± 0.072 | +0.100 ± 0.087 | 1 of 8 (leader hybrid3_x 6.12) | 47 | 50 | - rival1 +0.557 ± 0.119 | 24-31 |
| 2 | Hero | 6.020 ± 0.070 | - | 1 of 8 (leader hero 6.02) | 45 | 50 | - rival1 +0.495 ± 0.121 | 24-31 |
| 3 | hybrid3 (no layer) | 5.954 ± 0.070 | -0.067 ± 0.089 | 1 of 8 (leader hybrid3 5.95) | 41 | 54 | - rival1 +0.356 ± 0.118 | 24-31 |
| 4 | rival3 (raw, reference) | 5.887 ± 0.074 | -0.133 ± 0.090 | 1 of 8 (leader rival3 5.89) | 41 | 55 | - rival1 +0.292 ± 0.121 | 24-31 |
| 5 | hybrid_x | 5.737 ± 0.078 | -0.283 ± 0.094 | 1 of 8 (leader hybrid_x 5.74) | 40 | 56 | - rival1 +0.105 ± 0.115 | 24-30 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 570,839 | 29 / 114 | 588 (0.103%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 491,693 | 36 / 267 | 912 (0.185%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 93.71%; exploit:steal_fold 6.59, exploit:bet_checked 3.14, exploit:steal 0.64 |
| hybrid3_x | 528,640 | 39 / 165 | 747 (0.141%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 97.10%; exploit:bet_checked 3.11, exploit:steal_fold 1.61, exploit:steal 0.13, hero:core_none 0.11 |
| rival3 (raw, reference) | 517,978 | 26 / 109 | 542 (0.105%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 528,385 | 31 / 140 | 615 (0.116%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.94%; hero:core_none 0.09 |


Hero reproduces both earlier runs on these deals exactly: 6.020 over 400 seeds is the exploit pass's final model-mode
number, and 5.967 over the first 200 is the hybrid agent's round 3. hybrid3_x is 6.133 on the first 200 (round 3: 6.141).

**hybrid3_x +0.100 ± 0.087 over Hero, just outside noise** (first 200 seeds +0.166 ± 0.128, all 400 smaller). Without
the layer the rival 3 core is level-to-behind (-0.067), raw rival 3 behind (-0.133 ± 0.090), and **hybrid_x behind,
-0.283 ± 0.094**. The layer is worth +0.17 to the rival 3 core here (hybrid3_x - hybrid3, same deals).

## 07:51-07:57: `top`, model mode, 400 seeds x 8

hero, rival1, rival1, pushfold, tag, hero_tight, loose_aggro, rival2. hero_tight is a Hero clone with the shipped layer for every candidate.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid_x | 5.097 ± 0.077 | +0.305 ± 0.101 | 1 of 7 (leader hybrid_x 5.10) | 23 | 70 | - rival1 +0.481 ± 0.103; - rival2 +0.091 ± 0.114 | 25-31 |
| 2 | hybrid3_x | 4.934 ± 0.077 | +0.141 ± 0.099 | 2 of 7 (leader rival2 5.05) | 20 | 75 | - rival1 +0.283 ± 0.103; - rival2 -0.117 ± 0.118 | 25-31 |
| 3 | hybrid3 (no layer) | 4.835 ± 0.074 | +0.042 ± 0.093 | 3 of 7 (leader rival2 5.01) | 17 | 77 | - rival1 +0.160 ± 0.105; - rival2 -0.174 ± 0.113 | 26-31 |
| 4 | rival3 (raw, reference) | 4.800 ± 0.072 | +0.007 ± 0.095 | 3 of 7 (leader rival2 4.97) | 19 | 76 | - rival1 +0.121 ± 0.098; - rival2 -0.168 ± 0.115 | 26-31 |
| 5 | Hero | 4.793 ± 0.073 | - | 3 of 7 (leader rival2 4.92) | 21 | 75 | - rival1 +0.145 ± 0.104; - rival2 -0.124 ± 0.117 | 26-31 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 533,568 | 29 / 109 | 657 (0.123%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 509,403 | 36 / 236 | 968 (0.190%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 95.65%; exploit:steal_fold 4.63, exploit:bet_checked 2.43, exploit:steal 0.22 |
| hybrid3_x | 511,359 | 43 / 179 | 836 (0.163%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 97.83%; exploit:bet_checked 2.40, exploit:steal_fold 1.09, exploit:steal 0.03, hero:core_none 0.03 |
| rival3 (raw, reference) | 499,288 | 30 / 129 | 563 (0.113%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 509,333 | 34 / 137 | 747 (0.147%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.98%; hero:core_none 0.03 |


**hybrid_x +0.305 ± 0.101 and hybrid3_x +0.141 ± 0.099 over Hero, both outside noise**; hybrid3 +0.042 and raw rival 3
+0.007 level. Rival 2 leads the room unless hybrid_x sits in it. (First 200 seeds: Hero 4.743 here against 4.765 in
round 3 on the same deals; rival 2's sampler reads the wall clock.)

## 07:57-08:06: `top2`, model mode, 400 seeds x 8

hero, rival1, rival2, rival2, pushfold, tag, hero_tight, loose_aggro.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid_x | 5.086 ± 0.079 | +0.394 ± 0.104 | 1 of 7 (leader hybrid_x 5.09) | 23 | 68 | - rival1 +0.563 ± 0.116; - rival2 +0.184 ± 0.102 | 25-36 |
| 2 | hybrid3_x | 4.835 ± 0.075 | +0.142 ± 0.099 | 2 of 7 (leader rival2 4.94) | 19 | 75 | - rival1 +0.230 ± 0.118; - rival2 -0.107 ± 0.105 | 25-36 |
| 3 | hybrid3 (no layer) | 4.721 ± 0.078 | +0.029 ± 0.102 | 3 of 7 (leader rival2 4.96) | 16 | 78 | - rival1 +0.137 ± 0.119; - rival2 -0.237 ± 0.102 | 22-36 |
| 4 | rival3 (raw, reference) | 4.702 ± 0.077 | +0.010 ± 0.099 | 3 of 7 (leader rival2 4.93) | 19 | 75 | - rival1 +0.113 ± 0.116; - rival2 -0.230 ± 0.104 | 23-36 |
| 5 | Hero | 4.692 ± 0.079 | - | 3 of 7 (leader rival2 4.95) | 20 | 77 | - rival1 +0.129 ± 0.124; - rival2 -0.253 ± 0.106 | 27-36 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 529,998 | 31 / 119 | 920 (0.174%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 515,518 | 37 / 235 | 1258 (0.244%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 95.38%; exploit:steal_fold 5.21, exploit:bet_checked 2.33, exploit:steal 0.31 |
| hybrid3_x | 512,519 | 45 / 202 | 1270 (0.248%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 97.78%; exploit:bet_checked 2.39, exploit:steal_fold 1.19, exploit:steal 0.05, hero:core_none 0.04 |
| rival3 (raw, reference) | 497,407 | 31 / 139 | 717 (0.144%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 507,284 | 36 / 159 | 863 (0.170%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.98%; hero:core_none 0.03 |


**hybrid_x +0.394 ± 0.104 and hybrid3_x +0.142 ± 0.099 over Hero, both outside noise**; hybrid3 and raw rival 3 level.
hybrid_x is the only candidate ahead of rival 2 here (+0.18 ± 0.10).

(A usage-limit cutoff hit after this stage; the driver had already finished top2, strong and timeouts and written their
samples to disk, so these three entries are written from those files, nothing re-run.)
