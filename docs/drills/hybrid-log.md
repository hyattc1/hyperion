# Hybrid candidate: running log

Rival 2's decision core behind Hero's shell (`hyperion/hybrid/`, simulator name `hybrid`). A candidate measured
against Hero, not a replacement: which bot ships is the owner's decision. Measurements land here as they finish;
the summary goes to docs/decisions.md, "Hybrid candidate". Rival 3 (`holdout`) is measured once per candidate
version and never tuned on.

## 2026-11-01 01:30 ET: v1 built (commit below)

- `hyperion/hybrid/core.py`: `Rival2Core` subclasses rival 2's `Bot` (nothing in `hyperion/sim/rivals/` edited or
  copied). Its ICM curve is built from `Rules.payouts` at rival 2's own knots with Hero's exact `icm_value`, in
  hand_end (outside the clock; rival 2 built it inside the first decision of every hand: ~115 us p50, ~500 us
  p99). Sampler: `mc_max` 64 samples (rival 2: 160, cut by its 260 us clock at ~110 heads-up), 200 us wall
  budget, 450 us hard stop; soft deadline 350 us before sampling starts -> Hero's cheap path.
- `hyperion/hybrid/bot.py`: `HybridCore` routes; `Hybrid` is SafeBot around it with Hero's deadline and panic
  settings. Core: plain hold'em, any rank order (remapped first), any payouts, antes (in `pot`), pot limit
  (its all-in is the cap), 3-card hands before the discard (its best two). Hero: short deck, lowball, wild
  cards, category order, hi/lo, two boards, Omaha, fixed limit, bounties, knockout points, exposed cards,
  preflop with a straddle, postflop with 3+ hole cards; discards, swaps and buying a card are Hero's
  `variant_decide`.
- Bestiary: `hybrid`; fields `realistic_h`, `top_h`, `top2_h`, `holdout_h` (hybrid in Hero's seat, else identical,
  so seating and deals match seed for seed).
- `tests/test_hybrid.py`: 36 tests (legality over 300 deep hands, all 23 catalogue entries with no error and the
  expected routing, the rank-remap round trip on a recorded table, payouts in the curve with rival 2's globals
  untouched, the fallbacks, timing). Full suite 570 passed, 1 skipped.
- Smoke, measure mode, top2_h, 3 seeds x 8: hybrid p50 25 us, p99 226 us.

## 01:35-01:42: the sampler budget (100 seeds x 8, strict, seed 7, pinned worktree d3616b1; 2 runs at a time, load 4-8)

Hybrid's own paired deltas between sampler settings (same seeds). "built" is rival 2's own sampler: 160 samples,
260 us budget, 520 us hard stop.

| field | mc 32 | mc 64 | built | 64 - 32 | built - 32 | built - 64 |
|---|---|---|---|---|---|---|
| top2_h | 4.954 ± 0.147 | 5.058 ± 0.148 | 4.941 ± 0.145 | +0.104 ± 0.167 | -0.013 ± 0.180 | -0.117 ± 0.164 |
| realistic_h | 5.513 ± 0.151 | 5.443 ± 0.154 | 5.452 ± 0.150 | -0.070 ± 0.159 | -0.061 ± 0.168 | +0.008 ± 0.158 |

No measurable difference. Timing in the same runs (top2_h, load 4-5): mc 32 p50 27 / p99 296 us, 0.264% over
1 ms (hero_tight in the same run 0.155%); mc 64 p99 314, 0.282% (hero_tight 0.168%); built p99 492 and its 0.5 ms
overruns pushed SafeBot into panic (Hero's cheap path) for 3,901 decisions. Earlier, on a quieter host (load 3-6,
40 seeds, hybrid and Hero in one field): mc 32 p99 240 us, 0.070% over 1 ms vs Hero 0.041%; mc 64 p99 293, 0.170%
vs Hero 0.072%. **v1 ships mc_max 32.** Where the time goes (measure mode, top2_h): postflop is 17% of decisions
and ~47% of the hybrid's time (mean ~226 us at mc 64); preflop p50 22-32 us, like Hero's ~20. Timeouts follow
mean time per decision, and the core's preflop alone costs about what Hero's whole decision does, so no sampler
budget brings the hybrid's timeout rate under Hero's at the same load: it runs ~1.7x Hero's.

## 01:45-01:55: v1 (133a837) vs Hero on realistic and the holdout (200 seeds x 8, strict, seed 7, pinned worktree)

Hero is the committed `hyperion/strategy` at 133a837 (last strategy commit c38259e). Two runs at a time, load 4-7.

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| realistic | 5.491 ± 0.099 | 5.491 ± 0.106 | **+0.001 ± 0.129** | 2 of 8; rival1 5.721 | 20/79 us, 0.05% | 26/232 us, 0.09% |
| holdout (measured once) | 5.451 ± 0.099 | 5.430 ± 0.109 | **-0.021 ± 0.133** | 2 of 8; rival3 5.876 | 20/63 us, 0.02% | 26/222 us, 0.04% |

Gaps to the field's rival on the same seeds: realistic hybrid - rival1 -0.230 ± 0.167 (Hero - rival1 -0.183 ± 0.166);
holdout hybrid - rival3 -0.446 ± 0.169 (Hero - rival3 -0.555 ± 0.153); rival 3 itself scores 5.876 against the
hybrid's table and 6.005 against Hero's (paired -0.130 ± 0.121). Routes: realistic core 248,398, soft deadline 36,
panic 200 (one table); holdout core 245,773, soft deadline 19. 0 exceptions, 0 illegal, 0 swallowed errors.

## 01:55-02:00: top and top2 (same settings)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, next/leader | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| top | 4.497 ± 0.105 | 4.988 ± 0.099 | **+0.491 ± 0.139** | 1 of 7; rival2 4.930 | 20/113 us, 0.09% (load 6-9) | 26/292 us, 0.22% |
| top2 | 4.490 ± 0.108 | 4.983 ± 0.107 | **+0.493 ± 0.148** | 1 of 7; rival2 4.916 | 21/102 us, 0.07% (load 6-9) | 26/220 us, 0.07% |

Same seeds, gaps to the rivals: top hybrid - rival1 +0.263 ± 0.129 (Hero -0.263 ± 0.152), hybrid - rival2 +0.058
± 0.151 (Hero -0.462 ± 0.160); top2 hybrid - rival2 +0.067 ± 0.135 (Hero -0.549 ± 0.151). In the rival-heavy rooms the
hybrid is rival 2 (level with it) and half a point over Hero; on realistic and the holdout it is level with Hero.
Routes: top core 252,387, soft deadline 89, panic 799 (two tables); top2 core 255,815, soft deadline 32, panic 64.

## 02:01: strong (same settings; hybrid in Hero's seat of hero,pushfold,pushfold,tag,hero_tight,hero_loose,nit,loose_aggro)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank | Hero p50/p99, over 1 ms | hybrid p50/p99, over 1 ms |
|---|---|---|---|---|---|---|
| strong | 5.150 ± 0.101 | 5.165 ± 0.117 | **+0.015 ± 0.143** | 1 of 7; hero_loose 4.800 | 16/58 us, 0.01% (load 5-7) | 23/182 us, 0.01% (load 4-6) |

Routes: core 254,012, nothing else.

## 02:09-02:17: payout robustness, the brief's 10/7/5/4/3/2/1/0 (uniform 4.00; same seeds; load 1.4-5.7)

`--payouts` sets `Rules.payouts`: the engine scores by it, Hero reads it, the hybrid's curve is built from it.

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader |
|---|---|---|---|---|
| realistic, brief payouts | 5.376 ± 0.145 | 5.492 ± 0.154 | +0.116 ± 0.197 | 2 of 8; rival1 5.965 |
| top, brief payouts | 3.929 ± 0.128 | 4.553 ± 0.157 | **+0.624 ± 0.196** | 2 of 7; rival2 4.748 |

(Linear 8..1 is the default: realistic +0.001 ± 0.129, top +0.491 ± 0.139 above.) Under the brief's table Hero is
fourth on top, 0.85 behind rival 2 and level with tag; the hybrid is second, 0.20 behind rival 2.

## 02:17-02:26: payout robustness, top_heavy 50/25/12/6/3/2/1/1 (uniform 12.5; same seeds; load 4.4-6.1)

| field | Hero | hybrid | hybrid - Hero (paired) | hybrid's rank, leader |
|---|---|---|---|---|
| realistic, top_heavy | 19.53 ± 0.92 | 20.09 ± 0.94 | +0.57 ± 1.23 | 2 of 8; rival1 23.18 |
| top, top_heavy | 12.75 ± 0.78 | 15.36 ± 0.77 | **+2.62 ± 1.06** | 3 of 7; rival1 15.96, rival2 15.92 |

On top, Hero is 3.4-3.7 behind both rivals under top_heavy; the hybrid is level with them (-0.6). Routes: realistic
core 241,388, soft deadline 54, panic 49; top core 239,508, soft deadline 37, panic 95.
