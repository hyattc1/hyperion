# The climb: running log

Protocol: `docs/drills/goal-plan.md` section 2. Live held-out set: **H1 (20000-20399)**, 0 of 3 confirmations used.

## 2026-11-01 20:20 ET: Phase 0
- Plan written and committed before any bot code change.
- Test sets started: four outside builders (veterans, self-play, aggressive, quants) and the unseen-variant writer,
  each a fresh agent with no repo access, in the session scratchpad (`goal/outside/*`, `goal/unseen/`).

## 20:30: R1, first timing look (code d3a7ca5)
- Quiet-ish host (load 1-2), strict, night, seeds 10000-10099 x 8: F 6.025, 6 timeouts, 9 SafeBot overruns, max 11.9 ms
  (one preemption); hybrid3_x 5.828, 1 timeout, max 1.4 ms. `tools/latency.py` 20,000 calls: F p99 112 us, max 405
  us; hybrid3_x p99 84 us, max 659 us.
- Tail at a table (measure mode, night, 50 x 8, four runs side by side at load ~3): share of decisions a k-times slower
  box would time out (over 1000/k us here):

  | bot | p99 us | 1x | 2x | 3x | 4x | tables that entered panic (of 400) |
  |---|---|---|---|---|---|---|
  | F | 239 | 0.09% | 0.25% | 0.52% | 0.93% | 7 |
  | F, payouts 50/25/12/6/3/2/1/1 | 280 | 0.08% | 0.26% | 0.60% | 1.46% | 12 |
  | hybrid3_x | 196 | 0.08% | 0.21% | 0.39% | 0.68% | 5 |
  | Hero | 147 | 0.06% | 0.14% | 0.26% | 0.43% | 4 |

- SafeBot enters panic (Hero's cheap path for the rest of the table) after 5 overruns of its 0.5 ms soft deadline
  in one table. The `timeouts` recipe (cheap path everywhere) is about two points a table, so panic on a slow or busy
  sandbox is the largest risk found so far. R1 goes to a dedicated worker (branch climb/r1-timing).

## 20:42: unseen variants written; kit E and the held-out catalog started
- The fresh writer's five (order of its plausibility score): river_of_blood 8/10 (MIT 2023: red rivers deal extra
  streets until a black card), showtime 6/10 (folded hands shown face up), high_chicago 5/10 (half the pot to the
  highest spade in the hole), bomb_pot 5/10 (every fifth hand: no blinds, everyone antes, first decision on the flop),
  unfold 4/10 (folders may pay to re-enter a side pot). Held out: no strength work may use them.
- river_of_blood is the hidden variant of drill 7 (the next rehearsal). After that drill it is promoted to the main
  catalog and prepared like the 23, since an MIT variant is a real candidate for the night.
- Kit E: a fresh agent with no repo access builds an organiser-style kit (event-driven player class, no state
  snapshot, string cards, its own payout table and schedule) with river_of_blood in its dealer.
- The held-out catalog goes on branch climb/unseen-variants (engine support, default play bit-identical).
