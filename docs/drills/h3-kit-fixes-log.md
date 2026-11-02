# H3 / R5 / R6: kit fixes from drill 7 (log)

Branch `climb/h3-kit-fixes`, from main 0f0696a (drill 7). Host: 8 cores shared with other agents, load 4-7 throughout,
at most two of my processes at once. Every play check below is "the same decisions", not "the same score".

## R6: setup cost (import + make_bot + new_table, cold, `python -I`)

Before: Hero's table start called `warm(8)`, the 8-card evaluator table, 0.61 s, built by brute force over every
8-rank multiset's five-card subsets; 6 and 7 cards (built at import) cost 0.02 and 0.12 s the same way.

What changed (`hyperion/core/eval.py`, `HeroCore.new_table`):
- Each n-card table is grown from the (n-1)-card one: the best five of n cards is the best over the n multisets one
  card smaller, so each (n-1) entry raises its 13 one-rank extensions. Same entries (test against the brute force,
  kept as `_build_unsuited_slow`): 6, 7, 8 in about 3, 20, 60 ms. Flush masks the same way, 21 -> 3 ms.
- `eval.max_cards(rules)`: the cards one evaluation can hold (hole held at each street, after a discard, plus a
  bought card, plus that street's board; 5 for must-use; 8 for a running board). Hero's table start warms that,
  not 8: 7 for hold'em and toss_or_holdem, 8 for three_card_keep and bonus_card, 5 for omaha.
- An evaluate on 6-8 cards with no table never builds it inside the call: it takes the best of its (n-1)-card
  subsets (exact, ~8 lookups) and records the count; the next `warm()` (a table start) builds it. Past 8 cards
  nothing changed (lazy build; variants_unseen's guard still models it as a timeout in the sim).

Cold, seconds (setup_probe: import hyperion.ship, make_bot, new_table, in a fresh `python -I`):

| bot | default before | default after | toss_or_holdem after | three_card_keep (8 cards) after |
|---|---|---|---|---|
| composite (ship) | 0.95 | 0.14 | 0.13 | 0.19 |
| hybrid3_x | 0.93 | 0.12 | 0.13 | 0.18 |
| Hero | 0.88 | 0.12 | 0.12 | 0.17 |

The packaged event entry (tools/pack.py on hyperion/drills/event_example.py, unzipped, fresh `python -I`): import
0.01 s + Agent() 0.13 s + table start 0.000 s = 0.14 s (drill 7's entry: 0.81 s, 0.25 s with its monkeypatch).
What is left of the 0.13 s: two HeroCore constructions (push/fold and preflop tables, ~30 ms each), the strategy
imports (~45 ms), rival 3's import (10 ms). Not touched.

**First decision of a table** (coordinator's question: F's slowest first call was 48 ms in the exploiter's arena).
In a fresh process, after the table start, the first decision is 74-157 us against a median of 40-64 us (cold
caches, the interpreter's first pass), and nothing is built: no evaluator table, no curve (tests/test_setup_cost.py
asserts both, CPU time, 3 bots x 3 rule sets). The arena's 48 ms came with maximum decisions of 12-56 ms anywhere
in the same runs at load 5-8: the host, not a lazy build. Before R6 a first decision could have built a 6-8 card
table only if the table start had not (never with warm(8)); now no evaluate ever builds one up to 8 cards.

## R5: hand-end cost

Measured with the new `tools/latency.py --hand-end`: 20 tables of `realistic` recorded in model mode, replayed on a
fresh bot per table with the ICM memos emptied (as a fresh process per table would be), each hand_end timed alone;
per-call minimum of 3 replays (first pass in brackets). p50 / p99 in us.

Profile of the composite's hand end before (default payouts, ~100 us): two ICM curves (the hero member's and the
base's fallback Hero's, ~25 us each), two profilers (~20 us each, half of it every seat's dials), rival 3's history
replay (12-15 us), the exploit layer (5 us). Under kit E's 50/25/15/10/0/0/0/0 the curves dominate: each point is an
exact 2^7-subset ICM pass (~50 us) when the rounded key misses the memo, 9-13 points a curve.

What changed (play bit-identical, see below):
- `icm_me`: the subset walk reads a precomputed plan (low seat, parent mask, size, successors) instead of testing
  bits: the same additions in the same order, 1.6x faster (50 -> 30 us at eight seats).
- `IcmCurve.compute`: repeated points (several multiples past every chip) dropped before they are priced;
  icm_value's payout tests done once per curve instead of per point.
- The hybrids' fallback Hero (decides a few hands in a hundred where the core plays) keeps its curve and its
  profiler's dials pending until it decides (`HeroCore.set_lazy`, `Profiler.lazy`: a seat's dials on first read, the
  rest settled before the next observe changes a counter, so every read equals the eager value). Eager on tables
  Hero plays whole (variants, straddles, cheap, panic).
- `defer_hand_end(True)` on Hero, Hybrid and Composite (and EventAdapter): the hand end does the chip chains, the
  reads and rival 3's replay; the ICM curves and dials wait for `idle()` (call it from the kit's next event) or the
  next decision that needs them. Off by default: kits A-D (untimed hand ends) keep the eager hand end.

| bot, payouts | before | after (eager) | after, defer: hand_end + idle |
|---|---|---|---|
| composite, 8..1 | 91 / 132 (96 / 172) | 49 / 89 (50 / 109-137) | - |
| composite, 50/25/15/10/0... | 160 / 509 (173 / 552), max 688 | 96-100 / 279-293 (107 / 311-349) | 27 / 63 (30 / 86) + idle 68 / 226 |
| hybrid3_x, 8..1 | 53 / 86 | 20 / 50 | - |
| hybrid3_x, 50/25/15/10/0... | 113 / 477 | 20 / 49 | - |
| Hero, 8..1 | 38 / 58 | 28 / 48 | - |
| Hero, 50/25/15/10/0... | 96 / 441 | 75 / 250 | - |

The decisions in the same replays: composite act p99 81 -> 79-82 (8..1) and 148 -> 113-119 (kit E's payouts: the faster
ICM also prices rival 3's all-ins); tools/latency.py (20,000 random states, alternating trees at load 6.8): p50 48 vs
47-48, p99 139-150 vs 150-177, noise.

Goal "p99 well under 300 us at a table": met eagerly on linear payouts (89) and on hybrid3_x / Hero everywhere;
the composite under a top-heavy table is at 280-290 eagerly, 63 with defer (the curve's ~230 us then runs in the next
event's own budget). For a kit that times hand ends, the event template turns defer on (`HAND_END_TIMED`).

**Safe if interrupted.** Hand-end order is now: the chip chains first (HeroCore.last_stacks, HybridCore._start: a
few assignments), then the reads, then the curve, whose pending marker is cleared only once it is computed. Before,
an interruption before HybridCore's `_start` update left its chain stuck for the rest of the table (its next hand
end never matched again): tests/test_hand_end_interrupt.py interrupts the composite's and hybrid3_x's hand end at
13 points spread over the call (sys.settrace raising a BaseException, as kit E's SIGALRM does) and checks every later
call runs clean, the chain follows the table again by the next hand end, and nothing an eager Hero owes stays
pending; on main the same test fails at line 1 (`_start_hand` 30 vs 60). A missed hand end now re-anchors
HybridCore's chain on Hero's. An interrupted profiler pass leaves that hand's counts partial (the next hand starts
clean); rival 3's replay is frozen code and was not touched.

## Play check

- Fingerprint (scratch fp.py): every hand's deltas, board and actions plus final points, model mode as
  climb_accept plays it, F / hybrid3_x / Hero in Hero's seat of `realistic`, under default rules, kit E's payouts,
  toss_or_holdem and three_card_keep, 10 tables each: identical to 0f0696a after R6, after each R5 step, and with
  `defer_hand_end` on (idle after every hand end, or never: the decisions settle it).
- `tools/climb_accept.py --cand '{"dials": {}}' --set screen --stages confirm` on 0f0696a and on cd637b9 (R5):
  night 5.973023 both, the 200 per-seed samples identical (max abs diff 0.0), 280,221 calls both.
- tests/test_hand_end_interrupt.py::test_defer_hand_end_plays_as_the_eager_hand_end: the same decisions with defer.

## H3: event-driven kits

- `hyperion/drills/events.py`: `EventTracker` (hand start with chips before posting, posts with antes as dead
  money, the whole board so far, every action by total or paid, showdown, deltas from net or chips after, `fresh()`
  for a missed event, `load()` for a gate seat) and `EventAdapter` (decide from the tracker, the log as the history,
  `end_hand(net=...)` with every seat's chips and the showdown, `defer_hand_end` / `idle`).
- `hyperion/drills/event_player_template.py`: the entry to copy for an event kit, TODOs 0-11 (timed hand end?,
  cards, request, reply, one tracker call per event).
- `hyperion/drills/fakekits/kit_e_style/`: a fake event kit written for this (own protocol on the shared dealer:
  on_table / on_hand / on_board / on_action / on_reveal / on_result / decide, string seat keys, 1-based hands, every
  call timed, SIGALRM interrupt at 1.05 ms, a fresh module per table, setup timed, 1 s).
- `hyperion/drills/event_example.py`: the template filled in for it. Its runner: 0 illegal, 0 errors, 0 conformance
  violations; worst calls at load 6: decide 273-292 us, on_hand (with idle) 209-229, on_result 160-363.
- `hyperion/drills/gate_seat_template.py`: tools/gate.py's seat for an event entry: the tracker loaded from the
  gate's state, idle() run, the entry's own decide (the only timed call) and its own hand end with every seat's net
  (tools/gate.py now passes the hand's result to seat files; a seat passes on what the kit's hand end carries).
- tests/test_drills_events.py: the bookkeeping, the example's Observation equal to the dealer's true state at
  every decision (3 tables), conformance clean, a 50 us budget (most calls interrupted) never an error or an
  illegal move, the gate seat on the packaged example (0 exceptions, 0 illegal, 0 lifecycle errors).
- Prompts: 01 (and NIGHT-template) ask for the setup budget and fresh module/instance, timed events, the size cap;
  02 points an event kit at the two templates; 04 at `latency.py --hand-end --defer`.

## Not done / found

- The 0.13 s left in make_bot (two HeroCores' table structures) could be shared between the composite's two Heroes;
  not needed for a 1 s budget.
- Boards past 8 cards (river_of_blood runs) still build their table inside the call (seconds) or raise under the
  sim's guard; the exact subsets fallback stops at 8 on purpose (V3's river view is the fix; a direct 9+ evaluator
  would make the sim's guard obsolete and change the unseen-variant measurements).
- Wall-clock tests (test_hybrid3 decision cost, test_nightof_latency kit_d and kit_b/kit_c: a single 1 ms spike in
  100 calls) failed once each at load 6.9-8.3 while other jobs shared the host, and passed alone (3 of 3). Full suite
  on the final tree: 878 passed, 1 skipped (load 7.5).
- The fake event kit is in tests/test_drills_fakekits_selfcontained.py too (plays with hyperion absent).
