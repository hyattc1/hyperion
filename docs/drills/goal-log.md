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

## 21:00: research pass (variants ranked, official surfaces re-checked)
Files: `docs/drills/climb/variants-ranked.md`, `docs/drills/climb/official-changes-2026-11-01.md`.
- **Nothing about the game changed** on the official site since Oct 27 (diffed against Wayback captures). Only
  eligibility moved (Canada; under-18s with consent).
- **Top variants for Pittsburgh** (probability it is the main twist): toss_or_holdem 11%, bounty 8%, short_deck 7%,
  a true sealed-bid auction for a third card 5% (not catalogued; bonus_card is a posted-price stand-in), omaha_four
  5%, two_boards 5%, three_card_blind_discard 4%, permuted_ranks 4%, exposed_card 4%. Catalogue coverage about 81%;
  gaps: auction, river_of_blood (2.5%), CMU 2026's deal 5 keep 2 (2%).
- **Add-on levers:** a payout table steeper than 10/7/5/4/3/2/1/0 35%; blinds roughly doubling each level 40%;
  antes somewhere 25%; all three regionals share one variant 55%.
- **Field:** CMU has the most Castle Challenge entries of any school (364 of 3,740), so Pittsburgh's room is likely
  stronger than the night pool assumes. night_hard weighs more as a guard.
- Plan changes that follow (recorded here, protocol entry in docs/decisions.md with the first batch):
  - a guard for a **doubling blind schedule** joins the payout guards (tools/swap.py paired gets `--rules`);
  - track V works the ranked list top down and adds **auction** and **deal 5 keep 2** to the main catalogue;
  - variant-aware opponents (fresh one-hour builds per top variant) so "first on 22 of 23" is not against bots that
    ignore the twist.

## 20:57: S1, payout tables (diagnostic; screen seeds 10000-10199, 200 x 8, night, model, load 3-9)
| payouts | F | Hero (- F) | hybrid3_x (- F) | F p99 us |
|---|---|---|---|---|
| 10/7/5/4/3/2/1/0 | 6.072 | -0.155 ± 0.177 | **-0.255 ± 0.192** | 395 |
| 50/25/12/6/3/2/1/1 (points out of 100) | 23.636 | -0.250 ± 1.166 | -1.223 ± 1.231 | 366 |

F stays first under both tables; every member already prices all-ins from `Rules.payouts` (hybrid/core3.py). The
cost is time: the exact ICM under a non-linear table lifts F's p99 (R1 has it). S1 closed as a diagnostic; the payout
tables stay as guards.

## 21:40: test sets in
- **Outside field wired** (c1c18c7): four fresh one-hour builds, no repo access: `out_veterans` (minute 38),
  `out_selfplay` (45), `out_lag` (39), `out_quants` (36). Fields `outside` (the four + three night-pool seats) and
  `outside_strong` (the four + rival 4 + rival 5 + agent_pushfold: the stronger room Pittsburgh is expected to be).
  The two Monte Carlo builds read the wall clock; in model mode they play at a fixed speed calibrated from measured
  cost per sample (4.5 / 5.5 us). Both fields replay exactly (tests/test_sim_outside.py).
- **Held-out catalog merged** (9e490a0, branch climb/unseen-variants): `hyperion/drills/variants_unseen.py`, optional
  engine hooks, default play fingerprinted bit-identical. Full suite 848 passed. The implementer's findings:
  1. On river_of_blood F checks or folds every decision on a board of 7+ cards, made hands included. Left alone
     until drill 7 has run (the drill should find it).
  2. **Bug:** four catalogued hooks (swap_holdem, swap_one_turn, two_boards, bonus_card) draw from an unshuffled deck
     tail (two_boards' second board starts with the ace of spades in 60% of seeds on hand 0). Track V fixes it.
  3. `python -m hyperion.sim --field night@ship --mode model` does not replay exactly under load: the ship's own
     wall-clock guards stay on there. `tools/swap.py paired` turns them off, so the protocol's runs replay.
  4. The engine's pot award can lose chips if a folded player put in more than anyone still in the hand (no default
     play reaches it). Fix with a test.
  5. showtime and unfold test little against this field (nobody reads reveals; nobody re-enters).
- **Kit E built** (session scratchpad `goal/kitE`): an event-driven `Player` (take_seat, start_hand, see_cards,
  see_action, see_showdown, end_hand, choose(request) with legal options and no state snapshot), raise-to amounts,
  payouts 50/25/15/10/0/0/0/0, antes from level 4, river_of_blood in the dealer; self-test 141/141.
