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
