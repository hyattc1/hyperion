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

## 20:50: research pass (variants ranked, official surfaces re-checked)
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

**Correction (21:33):** the spec `{"dials": {}}` in `tools/swap.py paired` is NOT F: swap.py hands a spec's dials to
`parse_dials` alone, without `SHIP_DIALS`, so the "F" above is P (F before the last climb's two dials: layer fold read
0.5, Hero call margin 0.15). The numbers stand for P. `tools/climb_accept.py` resolves dials on top of `SHIP_DIALS`
(as `hyperion.ship` builds the bot); S1 is re-measured on F with it. Every member already prices all-ins from
`Rules.payouts` (hybrid/core3.py); the cost is time (R1 has it).

## 21:24: test sets in
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

## 21:33: tools/climb_accept.py
One command for the protocol's acceptance rule: a candidate spec against the ship on a set (`screen`, `H1`.., `judge`)
through stages confirm, guards, variants, judges, timing; per-spec cached results keyed by the code tree, so a batch's
base runs once. Dials specs are resolved on top of `SHIP_DIALS`, so `{"dials": {}}` is F (the trap above).

## 21:51: drill 7 (H1) done: report docs/drills/prompt-drill-7.md
- First valid upload minute 8, ship bot gated minute 18, final minute 20, stopped minute 23 (drill 6: 12 / 29 / 34).
- Final zip under the real variant (operator, main's sim with the held-out hooks, kit E's payouts and antes, night,
  seeds 30000-30059): package 26.70 vs raw F 23.30 points of 100, paired +3.40 ± 6.49; 0 exc, 0 ill, 1 timeout.
- New backlog items from it: H3 event-driven adapter and gate-seat templates; R5 cheap, interrupt-safe hand end (kit E
  times end_hand: ours p99 658 us); R6 setup only for the card counts the rules imply (warm(8) is 0.62 s of a 1 s
  per-table budget); V3 a generic river view for boards longer than 5; prompt 01 asks for setup budget, timed
  callbacks and the zip cap.
- river_of_blood is now promoted out of the held-out set (into the main catalog with V3); the held-out set keeps
  showtime, high_chicago, bomb_pot, unfold.

## 21:56: the exploiter (S2) done: docs/drills/exploiter/FINDINGS.md
A fresh agent with only the black-box arena (the packed F of d3a7ca5) built `exploit_bot.py` (md5 183c150c) in ~80
minutes. It beats F in every format (payouts 10/7/5/4/3/2/1/0): 8-max 5.255 vs 5.065 (500 tables), heads-up 8.929 vs
8.071 (wins 64%), three-handed 8.378 vs 7.013 (300 tables). With its exploits off it scores 4.335 vs F's 6.129, so
the exploits are worth about +0.92 / -1.06 at 8-max and ±1.05 heads-up. Findings, largest first:
1. F opens very wide (SB 95%, BTN 79%, CO 58%) and folds 88-93% to a 3-bet of any size: a 1.16-point swing at 8-max.
   Heads-up it adapts after ~110 hands.
2. Bet size tells strength: 0.8 pot and river bets of half pot or more are nearly always strong; 0.33 pot is weak
   (folds 78% to a check-raise of it).
3. Heads-up: opens and shoves any two (100% at 10 bb or less); big-blind defence ignores the raise size.
4. Over-folds to postflop bets (76-80% heads-up) before adapting; reads need 20-40 observations of a spot.
5. Solid: all-in calls, river bets and calls, its own 3-bets and 4-bets.
Odd: under load F's slowest decisions reached 12-56 ms and its slowest first call of a table 48 ms (model mode, so
not folded; strict would fold them). Sent to R1/R6.
These go to a strength worker (S2), fixes behind dials, measured against the exploiter as a frozen bot and guarded on
the standard fields; the outside field (with its loose-aggressive 3-bettor) judges the batch.

## 22:52: batch 1 (infrastructure; hold'em play unchanged) merged and frozen
- climb/v-catalog (23da153): hooks draw from the shuffled undealt cards (the ace-of-spades bias is gone; chi-square
  61.7 on 51 df); pot award fix and a dead-money charge option; bonus_card's price is dead money; new entries auction
  (MIT 2024, sealed bid, 8-way second price) and deal5_keep2 (CMU 2026, 52-card) with F's bid and keep decisions and
  a variant-aware opponent each. F 25/25 READY, first on 24.
- climb/h3-kit-fixes (b48c272): setup 0.95 -> 0.14 s cold; hand end p99 132 -> 89 us (8..1), 509 -> 293 us (kit E's
  payouts; 63 us deferred); interrupt-safe; event-kit entry and gate-seat templates; prompt 01 rule-sheet lines.
- Play check: F's per-seed night samples on 10000-10049 identical before and after both merges (6.045); full suite
  925 passed. The hold'em judges therefore stand as measured at the start (leaderboard).
- Frozen: frozen/B1-b48c272, kit B zip sha256 8eeb870a...61987c3428d.
- Found for later: Hero ignores toss_or_holdem's face-up discards as dead cards (toss is the likeliest variant, 11%);
  F busts 76% of tables on deal5_keep2; boards past 8 cards still build an evaluator table inside the call (V3);
  gen_catalog.py crashes on five hole cards; two wall-clock tests flake at load 7-8.

## 23:44: owner direction: prepare for the top teams, not only niche styles
The owner pointed out that most strong teams will build a good general bot (as we did), not a niche style, and that
Pittsburgh's top tables will hold prepared quant teams who adapt and exploit. Changes:
- **Elite field.** Three fresh agents (no repo access), one shared brief: a prepared top team (quants and a
  pokerbots finalist), two weeks of prep, may bring code and tables; "the strongest general bot, hard to exploit,
  takes everything weak bots give away"; about 2.5 hours each (session scratchpad `goal/elite/e1..e3`).
  Two (elite1, elite2) become a tuning field `elite`; the third stays a held-out judge. Plus mirror tables (strong
  bots and copies of F), since empty seats are filled with copies of submitted bots.
- The exploiter's findings (S2) are what a strong adaptive team would use; they stay first in the strength queue.
- Backlog: **S8** play against the elite field (profile, fix the weakest section); **S9** mirror and strong-table play
  (F against copies of itself and the elite bots).

## 00:24: batch 2 accepted: the governor (slow_box) ships in F's defaults (f7914c0)
- R1 merged (ca8563e): tools/slowbox.py (dilated clock, seat-only timing, contention, noise), SafeBot's governor
  (near-timeouts 0.8 ms, clusters of 5 in 60 calls, one level per cluster, recovery), the composite's levels, exact ICM
  at half the cost (bit-identical).
- Held-out confirm (H1 seeds 20000-20199 x 8, k = 3, CPU-time clock, load 4-7): th **+3.640 ± 0.796** of 100, panic
  tables 772 -> 0 of 1600; lin **+0.144 ± 0.072**, 502 -> 0. Bit-identical in model mode (R1's checks).
- Accepted under addendum 2 (robustness rule, decisions entry). Frozen: frozen/B2-f7914c0, kit B zip sha256
  a59f45b9...7f4f134327. H1 confirmations used: 1 of 3 (robustness), so H1 stays live.
- Wall-clock tests flake at load 9-10 (a different two to six each full run, all pass alone); none fails consistently.

## 01:31: host incident: memory, not CPU
At 01:30 memory was 14.9 of 15.5 GB with 2.9 GB of swap used, and the 5-minute load had reached 35 (the elite builders
saw 43-53). Cause: tools/climb_accept.py pool workers that played many variants each held ~2.7 GB (every variant's
tables and evaluator caches), five of them across two workers' runs. Fix 5719074: workers are replaced after two jobs
(`maxtasksperchild=2`). Both workers' runs were stopped (cached chunks kept) and asked to take the fix, use at most
2 workers and run one climb_accept at a time. Memory after: 13.8 GB free. Timing numbers from the elite builders'
last hour carry this load (their harness tails).

## 01:39: elite field wired (11ecac6)
Three fresh agents, one shared brief (a prepared top team: quants and a pokerbots finalist; two weeks of prep; may bring
code and tables; "the strongest general bot: hard to exploit, takes everything weak bots give away"), about 105 minutes
each, no repo access:
- elite1 (md5 9bf36037): points-based all-in decisions, shove/fold by expected points with per-seat call rates, ranges
  from measured frequencies, settles unseen folds from the next stacks, a 5 us postflop classifier, heads-up opens 85%.
- elite2 (70c29e17): exact fast ICM (10/7/5/4/3/2/1/0 hard-coded), push/fold at 14 bb or less, range equity from
  169x169 tables, postflop exact enumeration over aggression- and size-narrowed ranges, EV-sized bets.
- elite3 (c5e956bd): points-based big decisions, push/fold about 13 bb, an 85 us postflop Monte Carlo over ranges
  narrowed by size and barrels, adaptive opens. Held out.
Fields: `elite` (elite1, elite2, rivals 1-3, agent_pushfold, agent_default: a top table) and `elite_night` (the two
in a night room) are tuning fields; `elite_judge` (elite3, elite1, elite2, rivals 4 and 5, out_veterans, out_quants)
is a judge. All three bots were reseeded per table from the seat seed (they used unseeded generators; elite2 seeded
from the time of day); elite3 plays at a fixed speed in model mode (8 us per clock read). climb_accept stages `elite`
and (in judges) `elite_judge`.

## 01:41: F against the elite field (diagnostic, 150 seeds x 8, model, every seat ranked)
| field | 1 | 2 | 3 | F |
|---|---|---|---|---|
| elite (top table: elite1, elite2, rivals 1-3, agent_pushfold, agent_default) | rival2 4.829 | elite2 4.699 | **F 4.665** | 3rd, level with elite2 (± 0.12) |
| elite_night (elite1, elite2 + five night seats) | **F 5.349** | elite2 5.180 | elite1 4.883 | 1st |
| elite_judge (elite3 held out + elite1, elite2, rivals 4, 5, two outside builds) | **F 4.930** | elite2 4.806 | rival4 4.606 | 1st |

- At a table of only strong bots F is level with the best, not ahead. elite2 is the strongest elite build in every room.
- F takes 1st place 11-13% of the time at these tables against 15-24% for the elite builds, and makes it up with more
  3rd-5th places: a survival profile that fits 8..1 points and fits a top-heavy table (35% likely) worse.
- Backlog: **S8** the elite tuning fields join the strength screens (climb_accept --stages elite); **S10** first-place
  conversion at strong tables under top-heavy payouts (endgame and heads-up, overlapping S2's heads-up fixes).

## 02:11: V-b merged (ea4d36f); its candidate in held-out confirmation; V-c and F1 started
- Variant-aware fields for toss_or_holdem, bounty, short_deck (hyperion/sim/aware.py; aware opponents in the realistic
  seats of the Monte Carlo, push/fold and TAG bots, plus toss_rival1). Bounty hook fix: hands 0, 25, 50... were scored
  with bounties other than the ones shown (bounty-only change to default play). Full suite 998 passed.
- Candidate (screen, F's margin over the best aware bot before -> after; candidate - F):
  toss +0.50 -> +0.67 (+0.156 ± 0.087), bounty +1.00 -> +1.32 (+0.298 ± 0.119), short_deck +0.28 -> +0.53
  (+0.198 ± 0.097); plain hold'em identical on all seven confirm/guard cells; variants none down, eleven up.
  Dials: hero.variant_preflop {call_raise_frac 0.15, three_bet_frac 0.05} (twist tables only, off on fixed-limit and
  must-use), hero.toss_value_shift 2, hero.toss_dead, base.hero_on_bounty false (rival 3's core plays bounty preflop).
- Confirmation running: H1 (2nd use), stages aware + variants.
- Started: V-c (river_of_blood promoted to the main catalog; boards longer than 5 cards; deal5_keep2 busts; short-deck
  shove calls) and F1 (the five windows rehearsed on F: every recipe re-checked, the signal table, a timed window).

## 02:41: S2 merged (b0bd3e8); its candidate FIN queued for held-out confirmation
- exploiter1 is a frozen test opponent (fields exploit, exploit_hu, exploit_3; climb_accept stage exploit).
  Against the frozen copy F loses as in the arena: 5.00 vs 5.37 (8-max), 8.01 vs 9.00 (heads-up), 7.03 vs 8.33 (3).
- FIN = {"r3.v3_defend": true, "hero.postflop.cbet_size_dry": 0.5}: a 3-bet defence that reads a seat's observed 3-bet
  rate (prior 0.08 worth 20 chances, plays from an estimated rate of 0.2, fold-to-4-bet capped at 0.6), and a half-pot
  dry-board c-bet. Screen: exploit +0.712 / +1.103 / +1.332 (F then beats the exploiter in all three formats: 5.71 vs
  4.68, 9.11 vs 7.89, 8.36 vs 6.99); night +0.023 ± 0.048; every guard, both elite fields and all 25 variants level.
  The first, looser defence lost on night (-0.037 ± 0.030) and three guards by reading nits as 3-bettors; the guarded
  one almost never fires against our fields.
- Not kept: big-blind defence by price (no points, -0.10 heads-up with the defence), calling down frequent bettors
  (level), 0.7-pot big-value bets (doubling blinds -0.019 ± 0.018). Heads-up push/fold is near Nash; no change.
- **Protocol addendum 6 (exploit resistance):** a change aimed at adaptive, exploiting opponents (which no tuning field
  contains, so night cannot show it) is accepted when on a held-out set it is beyond noise up on at least one exploit
  field and beyond noise down on nothing: night, guards, elite fields, variants (and the judges at batch end). Recorded
  in docs/decisions.md with the batch.
- Process fix: long measurements now run from a detached worktree at the measured commit (goal/wt_measure at b0bd3e8),
  not from the live tree, where merges can land mid-run (the V-b run started from the live tree; S2's merge leaves
  default play unchanged, so it stands).
- Next exploit work (S2 list): squeezes; fold-to-4-bet learned from more than 4-bets; heads-up shove/fold 10-15 bb; the
  0.8-pot tell; and a fresh exploiter against F with FIN on.
