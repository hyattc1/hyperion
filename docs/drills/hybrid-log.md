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
