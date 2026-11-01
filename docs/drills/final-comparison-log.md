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

## 08:06-08:10: `strong`, model mode, 400 seeds x 8

hero, pushfold, pushfold, tag, hero_tight, hero_loose, nit, loose_aggro. The two Hero clones carry the shipped layer for every candidate.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid_x | 5.510 ± 0.085 | +0.166 ± 0.108 | 1 of 7 (leader hybrid_x 5.51) | 37 | 56 |  | 16-22 |
| 2 | hybrid3_x | 5.414 ± 0.088 | +0.070 ± 0.104 | 1 of 7 (leader hybrid3_x 5.41) | 33 | 61 |  | 16-22 |
| 3 | Hero | 5.344 ± 0.076 | - | 1 of 7 (leader hero 5.34) | 33 | 61 |  | 16-22 |
| 4 | hybrid3 (no layer) | 5.137 ± 0.084 | -0.207 ± 0.100 | 3 of 7 (leader hero_loose 5.37) | 27 | 67 |  | 14-20 |
| 5 | rival3 (raw, reference) | 5.079 ± 0.085 | -0.265 ± 0.101 | 3 of 7 (leader hero_loose 5.36) | 29 | 66 |  | 15-22 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 555,215 | 24 / 89 | 136 (0.024%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 518,755 | 34 / 225 | 215 (0.041%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 93.44%; exploit:steal_fold 7.98, exploit:bet_checked 2.72, exploit:steal 0.75 |
| hybrid3_x | 526,286 | 40 / 145 | 196 (0.037%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 97.18%; exploit:bet_checked 2.72, exploit:steal_fold 1.86, exploit:steal 0.11, hero:core_none 0.10 |
| rival3 (raw, reference) | 509,082 | 28 / 94 | 140 (0.028%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 520,954 | 33 / 107 | 162 (0.031%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.95%; hero:core_none 0.08 |


hybrid_x +0.166 ± 0.108 (outside noise), hybrid3_x +0.070 ± 0.104 (level). Without the layer the rival 3 core loses
this room to Hero (-0.207 ± 0.100), and raw rival 3 by more (-0.265): the two layered Hero clones take pots from it.
The layer is worth +0.28 to the rival 3 core here, the most of any field.

## 08:10-08:16: `timeouts`, model mode, 400 seeds x 8

hero, montecarlo, montecarlo30, timeout_then_recover, timeout_burst, tag, pushfold, loose_aggro.

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.551 ± 0.071 | +0.112 ± 0.085 | 1 of 8 (leader hybrid3_x 6.55) | 62 | 37 |  | 12-17 |
| 2 | Hero | 6.439 ± 0.071 | - | 1 of 8 (leader hero 6.44) | 58 | 39 |  | 12-17 |
| 3 | hybrid3 (no layer) | 6.401 ± 0.071 | -0.038 ± 0.088 | 1 of 8 (leader hybrid3 6.40) | 56 | 42 |  | 12-17 |
| 4 | rival3 (raw, reference) | 6.297 ± 0.074 | -0.142 ± 0.089 | 1 of 8 (leader rival3 6.30) | 54 | 44 |  | 12-17 |
| 5 | hybrid_x | 6.034 ± 0.076 | -0.405 ± 0.089 | 1 of 8 (leader hybrid_x 6.03) | 50 | 49 |  | 12-17 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 564,565 | 27 / 107 | 175 (0.031%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 468,115 | 35 / 262 | 275 (0.059%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 92.51%; exploit:steal_fold 8.15, exploit:bet_checked 2.96, exploit:steal 0.82 |
| hybrid3_x | 513,308 | 37 / 143 | 253 (0.049%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 96.75%; exploit:bet_checked 2.95, exploit:steal_fold 2.09, exploit:steal 0.22, hero:core_none 0.15 |
| rival3 (raw, reference) | 508,758 | 25 / 103 | 153 (0.030%) | 0 (0.000%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 521,150 | 30 / 123 | 197 (0.038%) | 0 (0.000%) | 0 | 0 / 0 / 0 | core 99.93%; hero:core_none 0.12 |


Hero 6.439 is the exploit pass's final model-mode number on these deals, exactly. **hybrid3_x +0.112 ± 0.085 over Hero,
outside noise; hybrid_x -0.405 ± 0.089**, its worst field: the rival 2 core loses the most where the field is weakest.

## 09:00-09:16: strict mode (wall clock, everything as shipped: SafeBot panic on, soft deadline on), realistic and judge, 400 seeds x 8, six workers

The coordinator switched accounts after a usage-limit cutoff and reported the host quiet (load 0.06), so the strict runs went first, on six workers. `realistic` ran at load 1-4. `judge` started at load 2; other sessions started eight-process jobs at 09:12 and it finished at load 25. The judge is reported as it came out, not re-run.

### realistic.strict.lin.400  (09:00-09:07, 7 min, load 1 -> 2)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.094 ± 0.072 | +0.127 ± 0.091 | 1 of 8 (leader hybrid3_x 6.09) | 46 | 51 | - rival1 +0.546 ± 0.113 | 1-4 |
| 2 | hybrid3 (no layer) | 5.969 ± 0.072 | +0.002 ± 0.092 | 1 of 8 (leader hybrid3 5.97) | 41 | 55 | - rival1 +0.341 ± 0.114 | 1-3 |
| 3 | Hero | 5.967 ± 0.072 | - | 1 of 8 (leader hero 5.97) | 43 | 53 | - rival1 +0.423 ± 0.116 | 1-3 |
| 4 | rival3 (raw, reference) | 5.882 ± 0.070 | -0.085 ± 0.094 | 1 of 8 (leader rival3 5.88) | 40 | 56 | - rival1 +0.242 ± 0.110 | 1-4 |
| 5 | hybrid_x | 5.696 ± 0.073 | -0.271 ± 0.095 | 1 of 8 (leader hybrid_x 5.70) | 38 | 59 | - rival1 +0.039 ± 0.110 | 1-4 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 564,224 | 27 / 73 | 33 (0.006%) | 33 (0.006%) | 0 | 0 / 0 / 0 |  |
| hybrid_x | 486,918 | 34 / 220 | 60 (0.012%) | 60 (0.012%) | 0 | 0 / 0 / 0 | core 93.88%; exploit:steal_fold 6.52, exploit:bet_checked 2.90, exploit:steal 0.56, hero:soft_deadline 0.00 |
| hybrid3_x | 525,241 | 37 / 94 | 38 (0.007%) | 38 (0.007%) | 0 | 0 / 0 / 0 | core 97.20%; exploit:bet_checked 2.90, exploit:steal_fold 1.62, exploit:steal 0.13, hero:core_none 0.10, hero:soft_deadline 0.01 |
| rival3 (raw, reference) | 514,549 | 25 / 69 | 42 (0.008%) | 42 (0.008%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 526,598 | 29 / 79 | 29 (0.006%) | 29 (0.006%) | 0 | 0 / 0 / 0 | core 99.94%; hero:core_none 0.09, hero:soft_deadline 0.01 |


### judge.strict.lin.400  (09:07-09:16, 9 min, load 2 -> 25)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.209 ± 0.075 | +0.068 ± 0.095 | 1 of 8 (leader hybrid3_x 6.21) | 54 | 44 | - rival4 +0.659 ± 0.109 | 2-26 |
| 2 | Hero | 6.141 ± 0.078 | - | 1 of 8 (leader hero 6.14) | 52 | 44 | - rival4 +0.548 ± 0.109 | 2-26 |
| 3 | hybrid3 (no layer) | 6.076 ± 0.073 | -0.065 ± 0.093 | 1 of 8 (leader hybrid3 6.08) | 48 | 48 | - rival4 +0.433 ± 0.109 | 2-26 |
| 4 | rival3 (raw, reference) | 6.011 ± 0.074 | -0.130 ± 0.094 | 1 of 8 (leader rival3 6.01) | 48 | 49 | - rival4 +0.375 ± 0.108 | 2-26 |
| 5 | hybrid_x | 5.776 ± 0.080 | -0.365 ± 0.100 | 2 of 8 (leader rival4 5.78) | 44 | 53 | - rival4 -0.002 ± 0.111 | 2-26 |

| candidate | decisions | p50 / p99 us | wall >= 1 ms | engine timeouts | panicked tables | exc / ill / safe_err | routes and layer fires per table |
|---|---|---|---|---|---|---|---|
| Hero | 577,953 | 29 / 111 | 505 (0.087%) | 511 (0.088%) | 1 | 0 / 0 / 0 |  |
| hybrid_x | 494,143 | 36 / 248 | 950 (0.192%) | 954 (0.193%) | 25 | 0 / 0 / 0 | core 93.06%; exploit:steal_fold 7.11, exploit:bet_checked 3.34, exploit:steal 0.64, hero:panic 0.44, hero:soft_deadline 0.03 |
| hybrid3_x | 531,865 | 40 / 171 | 814 (0.153%) | 824 (0.155%) | 17 | 0 / 0 / 0 | core 96.54%; exploit:bet_checked 3.59, exploit:steal_fold 1.65, hero:panic 0.32, hero:soft_deadline 0.17, exploit:steal 0.14, hero:core_none 0.11 |
| rival3 (raw, reference) | 528,365 | 27 / 122 | 575 (0.109%) | 582 (0.110%) | 0 | 0 / 0 / 0 |  |
| hybrid3 (no layer) | 541,484 | 32 / 137 | 679 (0.125%) | 685 (0.127%) | 7 | 0 / 0 / 0 | core 99.73%; hero:soft_deadline 0.20, hero:panic 0.17, hero:core_none 0.10 |


In strict mode "engine timeouts" are the decisions the engine folded or checked for going over 1 ms on the wall
clock (they match "wall >= 1 ms" up to the first call of each table). "Panicked tables" are tables where SafeBot gave
the rest of the table to Hero's cheap path, of 3,200 per candidate.

- **realistic, quiet host:** hybrid3_x +0.127 ± 0.091 over Hero, outside noise (model mode: +0.100 ± 0.087); hybrid_x
  -0.271 ± 0.095. Everyone's timeouts are near zero: Hero 0.006%, hybrid3 0.006%, hybrid3_x 0.007%, rival3 0.008%,
  hybrid_x 0.012%. No table panicked.
- **judge, load 2 -> 25:** hybrid3_x +0.068 ± 0.095, inside noise (model mode +0.135 ± 0.097); hybrid_x -0.365 ± 0.100.
  Once the load rose, the hybrids timed out about twice as often as Hero (hybrid3_x 0.155%, hybrid_x 0.193%, Hero
  0.088%) and panicked on more tables (17 and 25 against Hero's 1).

## 09:16-09:27: payout tables on realistic and judge, model mode, 200 seeds x 8, six workers

`Rules(payouts=...)`: the engine scores by it, Hero and the hybrids read it, rival 4 reads it through its adapter; raw rival 3 prices all-ins on the brief's table whatever is passed. Uniform is 4.00 on the brief's 10/7/5/4/3/2/1/0 and 12.5 on top_heavy 50/25/12/6/3/2/1/1. Only the ranking tables are kept here; the latency of these runs is in the timing section.

### realistic.model.brief.200  (09:16-09:19, 2 min, load 24 -> 24)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.542 ± 0.176 | +0.233 ± 0.207 | 1 of 8 (leader hybrid3_x 6.54) | 47 | 50 | - rival1 +0.954 ± 0.274 | 24-25 |
| 2 | Hero | 6.308 ± 0.152 | - | 1 of 8 (leader hero 6.31) | 45 | 52 | - rival1 +0.821 ± 0.269 | 24-25 |
| 3 | rival3 (raw, reference) | 6.207 ± 0.171 | -0.101 ± 0.204 | 1 of 8 (leader rival3 6.21) | 41 | 54 | - rival1 +0.573 ± 0.279 | 24-25 |
| 4 | hybrid3 (no layer) | 6.202 ± 0.170 | -0.106 ± 0.204 | 1 of 8 (leader hybrid3 6.20) | 41 | 55 | - rival1 +0.574 ± 0.276 | 24-25 |
| 5 | hybrid_x | 5.961 ± 0.161 | -0.348 ± 0.204 | 1 of 8 (leader hybrid_x 5.96) | 39 | 57 | - rival1 +0.293 ± 0.239 | 24-25 |


### judge.model.brief.200  (09:19-09:21, 3 min, load 24 -> 25)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 6.667 ± 0.159 | +0.188 ± 0.196 | 1 of 8 (leader hybrid3_x 6.67) | 52 | 47 | - rival4 +1.264 ± 0.228 | 24-27 |
| 2 | Hero | 6.479 ± 0.172 | - | 1 of 8 (leader hero 6.48) | 48 | 49 | - rival4 +0.947 ± 0.248 | 24-26 |
| 3 | hybrid3 (no layer) | 6.477 ± 0.166 | -0.003 ± 0.207 | 1 of 8 (leader hybrid3 6.48) | 48 | 50 | - rival4 +0.961 ± 0.244 | 24-27 |
| 4 | rival3 (raw, reference) | 6.471 ± 0.166 | -0.008 ± 0.207 | 1 of 8 (leader rival3 6.47) | 48 | 50 | - rival4 +0.951 ± 0.244 | 24-27 |
| 5 | hybrid_x | 5.933 ± 0.176 | -0.547 ± 0.224 | 1 of 8 (leader hybrid_x 5.93) | 41 | 56 | - rival4 +0.246 ± 0.246 | 24-26 |


### realistic.model.th.200  (09:21-09:24, 3 min, load 25 -> 26)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 26.195 ± 1.109 | +0.377 ± 1.332 | 1 of 8 (leader hybrid3_x 26.19) | 45 | 52 | - rival1 +5.131 ± 1.800 | 25-27 |
| 2 | Hero | 25.818 ± 0.924 | - | 1 of 8 (leader hero 25.82) | 45 | 52 | - rival1 +5.186 ± 1.574 | 25-27 |
| 3 | rival3 (raw, reference) | 25.035 ± 1.048 | -0.783 ± 1.275 | 1 of 8 (leader rival3 25.03) | 41 | 54 | - rival1 +3.662 ± 1.753 | 25-27 |
| 4 | hybrid3 (no layer) | 24.664 ± 1.012 | -1.154 ± 1.290 | 1 of 8 (leader hybrid3 24.66) | 41 | 55 | - rival1 +3.122 ± 1.688 | 25-27 |
| 5 | hybrid_x | 23.262 ± 0.950 | -2.556 ± 1.249 | 1 of 8 (leader hybrid_x 23.26) | 38 | 59 | - rival1 +1.292 ± 1.462 | 25-27 |


### judge.model.th.200  (09:24-09:27, 3 min, load 26 -> 24)

| # | candidate | pts ± 95% | - Hero (paired) | rank in field | 1st % | bust % | gaps (paired) | load |
|---|---|---|---|---|---|---|---|---|
| 1 | hybrid3_x | 27.385 ± 0.969 | +0.804 ± 1.317 | 1 of 8 (leader hybrid3_x 27.38) | 49 | 50 | - rival4 +8.069 ± 1.455 | 26-27 |
| 2 | Hero | 26.581 ± 1.054 | - | 1 of 8 (leader hero 26.58) | 47 | 50 | - rival4 +6.816 ± 1.655 | 26-27 |
| 3 | rival3 (raw, reference) | 26.427 ± 0.966 | -0.153 ± 1.254 | 1 of 8 (leader rival3 26.43) | 46 | 52 | - rival4 +6.747 ± 1.521 | 26-27 |
| 4 | hybrid3 (no layer) | 25.763 ± 0.980 | -0.817 ± 1.261 | 1 of 8 (leader hybrid3 25.76) | 45 | 53 | - rival4 +6.161 ± 1.498 | 24-27 |
| 5 | hybrid_x | 23.368 ± 1.011 | -3.212 ± 1.301 | 1 of 8 (leader hybrid_x 23.37) | 40 | 57 | - rival4 +2.326 ± 1.542 | 26-27 |


Hero reproduces round 3 on the realistic payout deals exactly (6.308 and 25.818), and raw rival 3 its round 2 numbers
(6.207, 25.035). hybrid3_x is first on all four and ahead of Hero by +0.19 to +0.23 on the brief's table and +0.4 to
+0.8 on top_heavy, all inside noise at 200 seeds. **hybrid_x is behind beyond noise on all four** (-0.35 and -0.55 on
the brief's table, -2.6 and -3.2 on top_heavy). The layer is worth the most to the rival 3 core under top_heavy
(hybrid3_x - hybrid3 +1.5 and +1.6 points), where the layer's extra steals add up to more firsts.

## 09:28-09:30: the 23 variants, Hero against hybrid3_x, model mode, 200 unrotated tables per entry, four workers

Each catalogue entry's own field, the same table seeds for both. "Route" is where hybrid3_x's decisions went: the rival
3 core, or Hero for the whole table where the shell sends that variant to Hero (in which case the two play the same
code and the delta is exactly zero). Verdicts as in PLAYBOOK §4b (READY = first or second, no exceptions, VPIP ≥ 10).
Bold would mark a paired delta beyond its 95% interval; none is.

| variant | hybrid3_x route | Hero: pts, rank, verdict | hybrid3_x: pts, rank, verdict | hybrid3_x - Hero | p99 us Hero / h3x | wall >= 1 ms Hero / h3x | load |
|---|---|---|---|---|---|---|---|
| permuted_ranks | core 97% | 6.48, 1, READY | 6.70, 1, READY | +0.22 ± 0.34 | 150 / 205 | 0.17% / 0.24% | 23-22 |
| short_deck | Hero (deck) | 5.94, 1, READY | 5.94, 1, READY | +0.00 ± 0.00 | 191 / 194 | 0.18% / 0.09% | 23-22 |
| lowball | Hero (showdown) | 7.77, 1, READY | 7.77, 1, READY | +0.00 ± 0.00 | 148 / 140 | 0.21% / 0.18% | 23-22 |
| wild_deuces | Hero (showdown) | 7.09, 1, READY | 7.09, 1, READY | +0.00 ± 0.00 | 194 / 214 | 0.04% / 0.16% | 22-22 |
| flush_over_full_house | Hero (showdown) | 6.01, 1, READY | 6.01, 1, READY | +0.00 ± 0.00 | 126 / 128 | 0.21% / 0.21% | 22-23 |
| toss_or_holdem | Hero (three_cards) | 6.19, 1, READY | 6.19, 1, READY | +0.00 ± 0.00 | 192 / 134 | 0.11% / 0.18% | 22-22 |
| three_card_blind_discard | Hero (three_cards) | 6.16, 1, READY | 6.16, 1, READY | +0.00 ± 0.00 | 150 / 176 | 0.05% / 0.21% | 22-23 |
| three_card_keep | Hero (three_cards) | 6.19, 1, READY | 6.19, 1, READY | +0.00 ± 0.00 | 221 / 131 | 0.32% / 0.26% | 22-23 |
| omaha_four | Hero (must_use) | 6.78, 1, READY | 6.78, 1, READY | +0.00 ± 0.00 | 140 / 138 | 0.36% / 0.29% | 23-23 |
| swap_holdem | core 97% | 6.12, 1, READY | 6.12, 1, READY | -0.00 ± 0.38 | 97 / 136 | 0.20% / 0.30% | 23-25 |
| swap_one_turn | core 97% | 6.21, 1, READY | 6.30, 1, READY | +0.09 ± 0.34 | 132 / 228 | 0.04% / 0.22% | 23-25 |
| exposed_card | Hero (exposed) | 5.86, 1, READY | 5.86, 1, READY | +0.00 ± 0.00 | 113 / 179 | 0.21% / 0.25% | 23-25 |
| two_boards | Hero (showdown) | 6.02, 1, READY | 6.02, 1, READY | +0.00 ± 0.00 | 105 / 110 | 0.23% / 0.24% | 25-25 |
| bonus_card | core 75% | 5.96, 1, READY | 6.08, 1, READY | +0.12 ± 0.32 | 99 / 208 | 0.12% / 0.28% | 25-26 |
| bounty | Hero (bounty) | 5.82, 1, READY | 5.82, 1, READY | +0.00 ± 0.00 | 99 / 170 | 0.15% / 0.12% | 25-25 |
| knockout_bounty | Hero (bounty) | 7.75, 1, READY | 7.75, 1, READY | +0.00 ± 0.00 | 128 / 103 | 0.04% / 0.12% | 25-24 |
| top_heavy | core 97% | 26.42, 1, READY | 24.18, 1, READY | -2.25 ± 3.71 | 161 / 221 | 0.05% / 0.15% | 25-24 |
| hi_lo | Hero (showdown) | 5.92, 1, READY | 5.92, 1, READY | +0.00 ± 0.00 | 88 / 175 | 0.08% / 0.11% | 24-23 |
| pot_limit | core 97% | 5.86, 1, READY | 6.01, 1, READY | +0.16 ± 0.38 | 86 / 111 | 0.10% / 0.12% | 24-23 |
| antes_from_level_3 | core 97% | 6.00, 1, READY | 6.13, 1, READY | +0.13 ± 0.37 | 85 / 209 | 0.14% / 0.11% | 23-22 |
| fixed_raise | Hero (fixed_limit) | 5.93, 2, READY | 5.93, 2, READY | +0.00 ± 0.00 | 88 / 160 | 0.09% / 0.07% | 23-22 |
| fast_schedule | core 98% | 5.64, 1, READY | 5.78, 1, READY | +0.14 ± 0.39 | 163 / 128 | 0.12% / 0.16% | 23-22 |
| straddle | core 30% | 6.08, 1, READY | 5.90, 1, READY | -0.18 ± 0.35 | 84 / 114 | 0.05% / 0.09% | 22-22 |

**Hero: 23 of 23 READY, first on 22. hybrid3_x: 23 of 23 READY, first on 22.** Zero exceptions, zero inner fallbacks,
zero illegal actions for both. Fourteen entries route whole tables to Hero, so they are identical by construction. On the
nine where the rival 3 core plays, hybrid3_x is ahead on seven and behind on two, every one inside noise at 200 tables.
`top_heavy` (-2.25 ± 3.71, on a 50..1 point scale) is the widest interval in the matrix; the 200 x 8 rotated payout run
above is the better measure of that table and has hybrid3_x ahead (+0.38 realistic, +0.80 judge). `straddle` (-0.18 ±
0.35) is the one entry where the core plays only 30% of decisions; it stays READY and first.

## Timing: merged over the stages (from the same runs, no new tables)

Model mode, realistic + judge + timeouts, 9,600 tables per candidate, host load 12-34 (the separate blind-bot session
was running):

| candidate | decisions | p50 / p99 us | mean us | wall >= 1 ms | engine timeouts | panicked tables | load |
|---|---|---|---|---|---|---|---|
| Hero | 1,711,659 | 28 / 116 | 37.1 | 0.126% | 0.000% | 0 of 9,600 | 12-34 |
| hybrid_x | 1,447,461 | 36 / 273 | 68.4 | 0.218% | 0.000% | 0 of 9,600 | 12-34 |
| hybrid3_x | 1,573,640 | 39 / 177 | 51.3 | 0.187% | 0.000% | 0 of 9,600 | 12-34 |
| rival3 (raw, reference) | 1,553,001 | 26 / 111 | 34.7 | 0.126% | 0.000% | 0 of 9,600 | 12-34 |
| hybrid3 (no layer) | 1,589,976 | 31 / 137 | 41.2 | 0.144% | 0.000% | 0 of 9,600 | 12-34 |

Strict mode, realistic, 3,200 tables per candidate, quiet host (load 1-4), everything as shipped:

| candidate | decisions | p50 / p99 us | mean us | wall >= 1 ms | engine timeouts | panicked tables | load |
|---|---|---|---|---|---|---|---|
| Hero | 564,224 | 27 / 73 | 30.4 | 0.006% | 0.006% | 0 of 3,200 | 1-3 |
| hybrid_x | 486,918 | 34 / 220 | 54.5 | 0.012% | 0.012% | 0 of 3,200 | 1-4 |
| hybrid3_x | 525,241 | 37 / 94 | 40.8 | 0.007% | 0.007% | 0 of 3,200 | 1-4 |
| rival3 (raw, reference) | 514,549 | 25 / 69 | 28.3 | 0.008% | 0.008% | 0 of 3,200 | 1-4 |
| hybrid3 (no layer) | 526,598 | 29 / 79 | 33.0 | 0.006% | 0.006% | 0 of 3,200 | 1-3 |

On the quiet host hybrid3_x times out on 0.007% of decisions against Hero's 0.006% (about one more per 100,000
decisions); p99 94 against 73 µs. Under load it crosses 1 ms on 0.19% of decisions against Hero's 0.13%. No candidate
panicked a single table. The extra cost is the exploit layer plus rival 3's reads (hybrid3 without the layer: 0.006%).

## Verdict (written 12:05 by the coordinator; the measuring agent stopped after the variant run)

Points per field, ranked (model mode, 400 seeds x 8, unless marked strict):

| Field | 1st | 2nd | 3rd | 4th | 5th |
|---|---|---|---|---|---|
| judge (rival 4, never tuned on) | hybrid3_x 6.18 | hybrid3 6.04 | Hero 6.04 | rival3 5.95 | hybrid_x 5.69 |
| judge_top | hybrid_x 5.13 | hybrid3_x 4.89 | hybrid3 4.84 | Hero 4.83 | rival3 4.83 |
| realistic | hybrid3_x 6.12 | Hero 6.02 | hybrid3 5.95 | rival3 5.89 | hybrid_x 5.74 |
| realistic, strict | hybrid3_x 6.09 | hybrid3 5.97 | Hero 5.97 | rival3 5.88 | hybrid_x 5.70 |
| top | hybrid_x 5.10 | hybrid3_x 4.93 | hybrid3 4.84 | rival3 4.80 | Hero 4.79 |
| top2 | hybrid_x 5.09 | hybrid3_x 4.84 | hybrid3 4.72 | rival3 4.70 | Hero 4.69 |
| strong | hybrid_x 5.51 | hybrid3_x 5.41 | Hero 5.34 | hybrid3 5.14 | rival3 5.08 |
| timeouts | hybrid3_x 6.55 | Hero 6.44 | hybrid3 6.40 | rival3 6.30 | hybrid_x 6.03 |

- **hybrid3_x is first or second on every field and ahead of Hero on every field** (paired). Beyond noise on judge
  (+0.14 ± 0.10), realistic (+0.10 ± 0.09; strict +0.13 ± 0.09), timeouts (+0.11 ± 0.09), top (+0.14 ± 0.10) and top2
  (+0.14 ± 0.10); inside noise on judge_top, strong, judge strict and the payout tables, all positive.
- **hybrid_x wins the strong rooms and loses the rest beyond noise**: judge -0.35, realistic -0.28, timeouts -0.41,
  top_heavy -2.6 / -3.2. The rooms the event will look like are the realistic ones, so it fails the plan's test.
- **The plan's test** (HANDOFF, 04:00): best on realistic, top and the judge field; 23 READY; timeouts no worse than
  Hero's; robust across the payout tables. hybrid3_x meets it except that it is second to hybrid_x on top, and its
  timeouts are level with Hero's on a quiet host and 1.5x under load.
- **Recommendation: ship hybrid3_x.** Before it ships: import each core lazily (`hyperion.hybrid` imports rival 2's
  core too, 1.2-6 s), pack it, and pass `tools/gate.py` on the zip. The owner makes the call.
