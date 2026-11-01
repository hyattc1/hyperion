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
