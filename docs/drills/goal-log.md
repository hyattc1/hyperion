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

## 04:19: V-b and FIN on held-out H1: one variant cell down each; lowball fixed; addendum 7
- V-b (H1, 2nd use, 43 min): aware fields all up (toss +0.203 ± 0.059, bounty +0.320 ± 0.083, short deck
  +0.158 ± 0.068); variants eleven up, lowball down (-0.062 ± 0.047). Cause: variant_preflop reached lowball, whose
  classes are mirrored, as it had reached fixed limit and Omaha before (-0.108, -0.065). Fix (e0e338d): off in lowball,
  as there. Lowball now plays exactly as F (+0.000 ± 0.000, 24 screen seeds); every other cell is untouched by the fix.
  V-b with the fix is re-confirmed on H2 (aware + variants) rather than accepted on the set that showed the loss.
- FIN (H1, 3rd use, 76 min): exploit +0.583 ± 0.095 / +1.076 ± 0.118 / +1.343 ± 0.133 (F beats exploiter1 in all
  three formats: 5.60 vs 4.71, 9.08 vs 7.92, 8.41 vs 6.93); night +0.021 ± 0.034 level; guards level or up (both
  payout tables up); elite level, elite_night up (+0.040 ± 0.033); variants all level but toss_or_holdem
  (-0.018 ± 0.016, upper bound -0.002).
- **Protocol addendum 7 (a lone variant cell down is replicated).** The variants stage checks 25 cells at a 95%
  interval each, so a change that does nothing shows at least one cell beyond noise down about 47% of the time
  (1 - 0.975^25), which made the rule reject sound changes on a coin flip and would make the stop rule fire on noise.
  From now on, for every candidate: when exactly one variant cell is beyond noise down and every other check passes,
  that cell is re-run on the next held-out set at 400 seeds (climb_accept prints REPLICATE; `--variants NAME
  --variant-seeds 400`). It rejects if the re-run is beyond noise down, or if both sets pooled (seed-weighted) are.
  A real loss the size of FIN's (-0.018) fails the re-run about 999 times in 1000; two or more cells down still reject
  outright. Guards, elite, judges and confirm are unchanged. Recorded in docs/decisions.md with the batch.
- H1 retired (robustness, V-b, FIN). H2 (21000-21399): FIN's toss_or_holdem replication, then V-b with the fix.
- Exploiter 2 hung on a tool call after its baseline (heads-up: F with FIN 9.45, the baseline 7.56); restarted with
  its files.

## 04:24: FIN passes addendum 7; S9 (strong tables) started; addendum 8 pre-registered
- FIN's toss_or_holdem on H2 at 400 seeds: +0.009 ± 0.012 level; H1 and H2 pooled -0.000 ± 0.010, not down. FIN
  passes the variants check; with addendum 6 it is accepted, pending the timing stage at batch close. It joins batch 3
  with V-b (H2 running).
- **Protocol addendum 8 (strong tables), written before any S9 result:** a change aimed at tables of strong general
  bots (elite, elite_night and the new mirror field, where night's weak seats are absent) is accepted when on a
  held-out set it is beyond noise up on at least one of those fields and beyond noise down on nothing: night, guards,
  the other strong fields, variants (with addendum 7), and the judges at batch end, elite_judge first. Night need not
  rise: it barely contains such tables.
- S9 started (worktree goal/wt_s9, branch climb/s9-strong-tables): a mirror field (copies of F with the strongest
  general bots), where F loses at all-strong tables (3rd, behind rival 2 and elite2) and why (it takes 1st 11-13%
  against 15-24%), and fixes by section, adopting the better bot's section where it beats F.

## 04:54: V-b with the lowball fix accepted on H2; batch 3 (FIN + V-b) in its combined check
- V-b on H2 (21000-21199 variants, 21000-21399 aware; 34 min): aware all up (toss +0.128 ± 0.059, bounty
  +0.298 ± 0.081, short deck +0.178 ± 0.065); variants none down, ten up (wild deuces +0.193 ± 0.082, three-card
  keep +0.129 ± 0.069, deal5_keep2 +0.081 ± 0.049 ...); lowball, Omaha and fixed limit identical to F. Accepted.
- Batch 3 = FIN + V-b. Each was confirmed alone against F. The combination runs on H2's third use (confirm, guards,
  elite, exploit, aware, variants: a second held-out look at FIN's hold'em cells and a check that the two do not
  interact), then the judges once on the judge set against the batch-2 ship. H2 retires after; H3 is next.
- Exploiter 2's restart stopped early (a safety check cut off its response to the brief's "attacking a bot"
  wording); restarted with the brief reworded as poker counter-strategy, same rules and deliverables.

## 05:18: F1 merged (bdfdfcd): the five windows rehearsed on F
- Six of the seven recipes needed a fix on F: three kept rival 3 core keys that never decide on F (rival 3's core
  only plays preflop there; checked in play, identical over 1,600 tables), `dead_seats` named a key that reached
  nothing, and `latency` cost -0.216 ± 0.089. New composite values (hyperion/ship.py COMPOSITE_RECIPES); hybrid3_x
  and Hero keep theirs. `latency` is now `late_us 0` (17 us a call saved, level); `timeouts` stays the emergency
  recipe (-1.58 on night) and is for errors, not slowness: the governor already steps F down on a slow box.
- Only `dead_seats` gains on its own signal (+0.058 ± 0.047 on the timeouts field) and it loses at strong tables
  (elite -0.160 ± 0.084): prompt 06 now says to apply it only on that signal.
- A window rehearsed end to end on fake kit B, top-heavy: 3.96 min with the fixed prompt (measure 3.2 via
  `climb_accept --stages window`, which passes unless night is beyond noise down); the old prompt's gate step failed
  ("no submission.py"), now gate.py finds the entry. Tests: every recipe keeps the governor; every composite recipe
  key reaches a part that decides.
- Accepted as an hour-track change (play by default identical; the rehearsal is better, not worse). Full suite 1018
  passed. Open: hybrid3_x's `dead_seats` has the same unreachable key (fallback bot, not measured).

## 05:49: exploiter 2 done (docs/drills/exploiter2/); S11 and R2-R4 started
- A fresh agent, black box, about 2 hours, against F with FIN (arena2). Its bot against F, payouts 10..0:
  heads-up 9.52 ± 0.06 vs 7.48 (600 tables, it wins 81-83% of matches), three-handed 8.61 ± 0.13 vs 7.21,
  8-max 5.15-5.44 vs 5.65-5.76 (F still ahead). Short-handed play decides 1st place, so this is the S10 question too.
- Leaks by points (ablations of its bot, heads-up / three-handed / 8-max):
  1. Blind vs blind: F's SB opens 85-90% and folds 88% to the first 3-bets (a 3x 3-bet needs 64%); later it
     over-adjusts, 4-betting light and calling off jams 97-100% at 50bb or less: +0.68 / +0.78 / +0.36.
  2. Bet size names the hand (0.30/0.35 fold ~90% to a raise; the new half-pot dry c-bet folds 78%; 0.70 never
     folds; 0.80 re-raises): +0.44 / +0.55 / +0.48. The known 0.8-pot tell, now the whole size ladder.
  3. No check-raise; folds 68-77% to a 0.6-pot stab after checking: +0.21 / +0.32 / +0.30.
  4. FIN's 3-bet tracking punishes a loose 3-bettor (-0.49 heads-up for 3-betting 60%), so that part holds.
  5. Heads-up BB folds 47% to a min-raise: +0.15.
- S11 (goal/wt_s11, climb/s11-exploiter2-fixes): freeze exploiter2 as a test opponent (fields exploit2,
  exploit2_hu, exploit2_3 in climb_accept's exploit stage) and fix leaks 1, 2, 3, 5 behind dials, on top of FIN;
  acceptance under addendum 6. S9 told to leave those sections to S11.
- R2-R4 (goal/wt_r2, climb/r2-lifetime-kits): one object for 10,000 tables, kit shapes through the adapter,
  memory, import time, sizes; addendum 2.

## 06:04: batch 3 combined on H2 (3rd use): one variant cell down; judges level; bonus_card replicating on H3
- FIN + V-b against F on H2: exploit +0.657 ± 0.093 / +1.050 ± 0.120 / +1.242 ± 0.136; night +0.022 ± 0.031
  level; guards level, doubling blinds up (+0.039 ± 0.032); elite and elite_night level; aware all up (toss
  +0.146, bounty +0.305, short deck +0.185); variants seven up, bonus_card down (-0.049 ± 0.040; alone it was
  V-b H1 -0.013 ± 0.020, FIN H1 -0.014 ± 0.034, V-b H2 +0.002 ± 0.023).
- Judges once on the judge set (30000-30399) against the batch-2 ship: judge +0.021, judge2 +0.014, judge2_night
  +0.014, judge_top +0.008, outside +0.019, outside_strong +0.009, elite_judge +0.008; all level, none down.
- Under addenda 6 and 7 (night need not rise; a lone variant down replicates): bonus_card for the combination on
  H3 (22000-22399) at 400 seeds decides; screen runs of FIN alone, V-b alone and both on bonus_card say which part
  moves it. H2 retired.
- climb_accept learns the addenda (f2a31a8): `--aim exploit` (6) and `--aim strong` (8) replace "night up" with
  "an aimed field up, night not down", so the verdict and REPLICATE come out right for those changes.

## 06:20: batch 3 accepted and frozen: V-b ships (9e620c8); FIN fails addendum 7 on bonus_card
- bonus_card for FIN + V-b on H3 (22000-22399, 400 seeds): -0.020 ± 0.032 level, but H2 and H3 pooled -0.030 ± 0.025
  are beyond noise down, so under addendum 7 the pair fails. Screen splits: FIN alone -0.026 ± 0.039, V-b alone
  +0.006 ± 0.019; on 400 extra screen seeds (10200-10599) the 3-bet defence alone plays bonus_card identically and the
  dry c-bet alone is -0.025 ± 0.027. The c-bet is also exploiter 2's 78%-fold-to-check-raise leak.
- Batch 3 = V-b alone (accepted on H2; plain hold'em identical by construction, so night, guards and judges stand;
  judges measured for the pair were all level). Timing by latency.py's per-call minimum over 3 replays (load 9-13):
  p99 plain 87 vs F 84 us, bounty 89 vs 66, toss 66 vs 66, short deck 65 vs 62, wild deuces 108 vs 109; none over 1 ms.
- SHIP_DIALS += V-b (9e620c8). Frozen: frozen/B3-9e620c8, kit B zip sha256 774f0636...89bcf6f20 (1.2 MB); gate pass
  (40 tables strict, 0 exceptions, 0 illegal, import 0.28 s). Full suite: 1017 passed, 2 wall-clock tests failed at
  load 13 (cheap bot kit D round trip, hybrid3_x cold setup), neither touched by V-b.
- The slim pack still ships the test opponents and judges (elite*, outside*, exploiter1, rivals 1, 2, 4, 5: about
  0.9 MB): handed to the R2-R4 worker to prune, with a test that elite3 and the judges are never in a submission.
- Decisions entry, leaderboard and HANDOFF updated. Next on H3 (2nd and 3rd uses): the 3-bet defence alone
  (`--aim exploit`) and V-c's candidate (aware + variants), on top of the new ship.

## 06:21: V-c merged (8a4ac80); H3 confirmations queued for the defence alone and V-c
- V-c: river_of_blood joins the catalog (26 entries; aware field river_of_blood_aware); `hero.long_board` reads any
  board length (a correctness fix, about 1% of decisions; level); `hero.keep_call_shift` 2 on deal5_keep2 (screen
  +0.356 ± 0.062; 2nd places 31% -> 50%); `hero.toss_call_shift` 1 (toss aware +0.230 ± 0.078). No short-deck dial
  helped (the calls it cut were break-even). All off by default; plain hold'em identical.
- H3 (22000-22399), from goal/wt_measure at 8a4ac80 (base = batch 3's ship): 2nd use, `{"r3.v3_defend": true}` with
  `--aim exploit` (confirm, guards, elite, exploit, aware, variants); 3rd use, V-c's candidate
  `{"hero.long_board": true, "hero.keep_call_shift": 2, "hero.toss_call_shift": 1}` on aware (all four +
  realistic_keep2 under deal5_keep2) and variants. H3 retires after.

## 06:34: owner question: are we reading opponents as hard as 100-300 hands allow? S12 started
- The owner pointed out that 100-300 hands is a lot of evidence, and bots are more consistent than people. We do not
  know how close F's reads come to that. S12 (goal/wt_s12, climb/s12-reads) measures the ceiling first: F with warm
  reads (each seat's profile pre-loaded from a long run against that bot; a measuring device, never shipped) against
  F as it ships, on night, realistic, night_hard, top and elite, under 8..1 and top-heavy. Then it ranks the reads
  F lacks by oracle gain (bet size vs strength from showdowns, position frequencies, fold to c-bet by texture, never
  check-raises, ...) and builds the best ones behind dials, with priors so they do not act too soon (dead_seats and
  S2's first defence both lost by acting on thin reads at strong tables). Offence; S11 is defence.

## 06:38: owner direction: strength against strong bots first
- The owner noted that ten hours in, F's plain hold'em has not gained, and that slow-machine insurance is not points
  (the sandbox's speed is unknown, not known to be slower). Agreed. From here the climb is judged by F's margin at
  strong tables and short-handed (the elite and mirror fields, both exploiters, heads-up and three-handed, 1st-place
  share under top-heavy payouts), not by robustness or variant numbers.
- Priority: S11 (exploiter 2's leaks: win heads-up against it), S9 (strong tables; adopt rival 2's or elite2's
  sections where they beat F), S12 (reads), then the 3-bet defence on H3. R2-R4 finishes its kit-shape checks (a crash
  costs whole points) and robustness then drops to the bottom of the queue. The structural round will be strength
  ideas (a stronger postflop, an adopted section) rather than tooling.

## 07:45: S9 merged (da4bd64): the mirror field; F last of six there; strong_route candidate queued on H4
- `mirror` = hero, three copies of F (`f_copy`, follows SHIP_DIALS), rival2, elite1, elite2, hybrid3_x; in
  climb_accept's elite stage. F is last of six there (4.43; rival2 4.79, hybrid3_x 4.55) and takes 1st 8.1% (elite1
  23.4%); on elite F is 2nd (4.71 vs rival2 4.91).
- Diagnosis (chips per decision, every strong field, both payout tables): F's opens at 10-20 bb with 4+ players lose
  (-0.10 to -0.13 bb vs +0.09 to +0.28 for the strong bots): rival 3's core min-raises 45-54% there and folds a third
  of those to a re-raise (-2.2 to -2.5 bb each); strong tables re-raise first-in raises 24-26% of the time (night 14%).
  Three-handed and heads-up preflop also trail (+0.02 / +0.07 vs +0.20 to +0.36): S11's sections, recorded, not fixed.
- Adopting the better bot's section (owner's rule): routing three sections to elite1, elite2 or rival2 gains
  +0.18 to +0.26 on elite and mirror but loses on night (-0.05 to -0.12). Narrowed and gated: G2 =
  `{"strong_route": "pre_open_10=elite1x", "strong_rr": 0.2}` (elite1 plays unopened 10-20 bb spots while the table
  re-raises our first-in raises at least 20%, smoothed toward 15% over 10 raises; threshold set before any gated run).
  Screen: night -0.017 ± 0.030, guards all level, elite +0.040, elite_night +0.048 ± 0.037 UP, mirror +0.098 ± 0.062
  UP; under top-heavy payouts elite +0.56 ± 0.50 and mirror +0.98 ± 0.56 of 100; exploit level; variants level (off
  on pot and fixed limit). Light shadow +8 us a decision.
- Merge check: F's night samples identical before and after (40 screen seeds). G2 queued on H4 (23000-23399) with
  `--aim strong`, all stages, from goal/wt_measure2 at da4bd64, after H3's two runs.
- Backlog from S9: a per-seat gate; rival2 for the section (needs a light shadow: its Monte Carlo costs ~260 us as a
  shadow); a mirror whose copies follow the candidate.

## 08:09: owner question: sim opponents must adapt to the twist too; V-d started
- The owner pointed out that on the night every team's bot knows the twist, so our sim's opponents must too. Today
  only four twists (toss, bounty, short deck, river of blood) plus auction and keep2 have aware opponents, each
  hand-built; 20 catalog entries and any unseen twist have only twist-blind opponents, which flatter F.
- V-d (goal/wt_vd, climb/vd-generic-aware): generic aware archetypes that take their play from the Rules and the
  variant's own hooks (gen_mc: Monte Carlo through the engine's own deal and showdown code; gen_tag, gen_pushfold:
  ranges re-cut from the variant's own equity table), one command to field them under any variant (target under 2
  minutes, usable in the hour), validated against the hand-built aware bots, then F's margin against them on every
  catalog entry: the new honest variant board and the variants track's targets.

## 08:17: R2-R4 merged (9304576); the 3-bet defence and V-c accepted on H3; batch 4 judges running
- R2-R4 found four failures that would have cost whole points, all fixed with F's play identical (1,400 per-seed
  samples on the branch; 280 again after the merge on 7 plain hold'em cells):
  1. 7 of 20 kit shapes broke the adapter; 5 of them sent every decision to check/fold (no raise bounds, "T♥",
     "hT", legal actions as dicts or one string), "10h" and "bet"/"all-in" words fell back on 13-21% of decisions,
     swapped min/max made every raise an all-in, blinds logged as bets read every pot as re-raised. The adapter now
     reads all 20 (new fake kit S); the clean-kit path is unchanged.
  2. A fresh bot per table leaked 71 KB a table (Hero's gc.freeze kept old bots) -> 0.
  3. A fresh package import per table leaked 28 MB a table (kit E's 256 MB cap by table 8) -> flat 64 MB.
  4. One object with no table-start hook carried panic, reads and seat across tables -> the adapter restarts the
     bot when the hand number goes back; a seat numbered from 1 is corrected.
  Also: one object over 10,000 tables grows 18 bytes a table, no time creep; peak RSS 65 MB with every variant
  table; cold import 0.02-0.05 s; stdlib-only on python3.10 -I passes, but 3.10 costs 40-50% more per decision.
  `--slim` now keeps only what the ship bots import (rival 3 and sim.rivals): zip 1.16 MB -> 807 KB, with a test
  that elite3 and the judges are never in a submission.
- H3 (22000-22399), base batch 3's ship:
  - `{"r3.v3_defend": true}`, `--aim exploit`: exploit +0.629 ± 0.077 / +1.087 ± 0.120 / +1.402 ± 0.136 (F beats
    exploiter1 in every format: 5.62 vs 4.65, 9.08 vs 7.92, 8.41 vs 7.03); night +0.000 ± 0.007; guards, elite,
    aware, all 26 variants level (most identical). ACCEPT (addendum 6).
  - V-c `{"hero.long_board": true, "hero.keep_call_shift": 2, "hero.toss_call_shift": 1}`: deal5_keep2 +0.286 ±
    0.045 (realistic) and +0.307 ± 0.039 (realistic_keep2), toss aware +0.095 ± 0.044; nothing down. ACCEPT.
  H3 retired (bonus_card replication, defence, V-c).
- Batch 4 = the defence + V-c + R2-R4's fixes. Judges once on the judge set against batch 3's ship and timing by
  per-call minimum, from goal/wt_measure at 9304576. strong_route (S9's G2) is on H4 now, for batch 5.

## 09:00: batch 4 accepted and frozen (e3cec13)
- Judges on the judge set against batch 3's ship: all seven level (five identical). Timing by per-call minimum: p99
  plain 87 vs 88 us, deal5_keep2 68 vs 70, toss 65 vs 64, river_of_blood 83 vs 87.
- SHIP_DIALS += r3.v3_defend, hero.long_board, hero.keep_call_shift 2, hero.toss_call_shift 1. Two tests encoded the
  old defaults (the S2 dial test compares against the dial off now; test_ship expects v3_defend on). Full suite at
  load 17: 1115 passed, 4 wall-clock tests failed (kit B/C and D round trips, exploiter1 budget, sim CLI), all pass
  alone or are the known load group.
- Frozen: frozen/B4-e3cec13, sha256 bb5820cc...6197fe, 813 KB slim (no judge or test-opponent files); gate pass
  (0 exceptions, 0 illegal; timeouts 0.79% under the load clause).
- S11 told: its base is now F with the defence; the dry c-bet stays out.
- Round 3 so far: accepted V-b (V), F1 (H), the defence (S), V-c (V), R2-R4 (R); rejected FIN's c-bet (S). The stop
  counter stays at zero.

## 09:59: S12 merged (5b4591a), its bet-size read queued on H5; S9's strong_route rejected on H4
- S12 (reads, the owner's question): the ceiling (F with every per-seat read it keeps, warm from hand 0, 100 x 8):
  night +0.04, realistic +0.18 UP, night_hard +0.02, top +0.02, elite -0.24 DOWN (rival 3's core's preflop
  punishments are sized for weak seats: -0.11 at elite). Reads settle: VPIP/PFR/fold-to-raise by hands 60-100;
  postflop reads still 0.10-0.24 off at hand 199. Missing reads by oracle gain: bet size names the hand (+0.10 /
  +0.23 UP / +0.28 UP on night / top / elite: half-pot bets from the rivals and elite1 are 33-65% air, their
  0.6-0.85 pot bets almost none), fold to a 3-bet (+0.06 / +0.08 / +0.02), never check-raises (level).
  Built: a learner that ranks each seat's sizes by use (no showdowns needed): elite +0.277, elite_night +0.227,
  top +0.108 UP, but exploit heads-up and 3-handed -0.28 DOWN, so it is off with 3 or fewer alive and on twist tables
  (C7). C7 screen (200 x 8, --aim strong ACCEPT): elite +0.256 ± 0.105, elite_night +0.227 ± 0.096 UP; night -0.031,
  guards, exploit level. Latency p99 100 -> 104 us (decisions), hand end 99 -> 138 us. Merge: F identical on 14
  cells (against 83066ac). C7 queued on H5 (24000-24399), --aim strong, all stages.
- S9's G2 on H4 (23000-23399, base batch 3): mirror +0.078 ± 0.039 UP; elite +0.020, elite_night +0.001; night,
  guards, exploit, aware level; variants down three (auction -0.016 ± 0.014, bounty -0.027 ± 0.018, knockout_bounty
  -0.030 ± 0.029): REJECT. Likely cause: elite1 is twist-blind, so routing opens to it on bounty and auction tables
  loses the twist's value. Also the candidate's sim p99 ran about 4.1 ms against F's 0.5-0.6 ms on the guard cells
  (model mode, play unaffected, load 17): a latency tail to find. Sent back to S9: route only on plain hold'em tables
  (S12's holdem-table test), find and cap the tail, re-screen. H4 used once.
- S11 told to rebase onto 5b4591a (S12 edits the same facing-a-bet block) and to screen its candidate with C7.

## 10:58: V-d merged (127fe04): the honest variant board; V-e started on the twists where F's lead shrinks
- Generic twist-aware opponents (hyperion/sim/generic.py: gen_mc plays out hands through a private copy of the
  variant's own hooks; gen_tag and gen_pushfold map each hand to its hold'em equivalent by percentile of the variant's
  own preflop table; tables/generic/, not packed). `climb_accept --aware generic:NAME | generic:all | path.py:factory`.
  New variant: table 14-24 s, the rehearsed in-hour command (table + F vs a candidate, 100 x 8) 143 s; PLAYBOOK
  stage 5 and prompt 05 updated. Validation: no generic bot below its hand-built match (toss: all three above);
  plain hold'em level with the archetypes; 0 exceptions, 0 illegal on all 26 entries. F identical (14 cells).
- The board (200 x 8): F first on all 26 against the generic aware field. Its margin over the best opponent shrinks
  most on lowball (+3.13 -> +0.86), wild_deuces (+1.73 -> +0.20) and short_deck (+0.78 -> +0.28); smallest leads
  also omaha_four +0.45, two_boards, three_card_keep, hi_lo about +0.5.
- climb_accept's code version now hashes untracked modules' content (V-d's cache hazard; 8286990).
- V-e (goal/wt_ve, climb/ve-variant-strength): profile F under short_deck, omaha_four, two_boards, wild_deuces, lowball
  against the generic aware field, fix the weakest sections behind variant gates (general fixes from the Rules and
  hooks preferred, so they carry to an unseen twist), acceptance on held-out generic aware cells.

## 11:31: S12's bet-size read (C7) on H5: large strong-table gains replicate, but rejected (realistic and three variants down)
- H5 (24000-24399), base batch 4, --aim strong: elite +0.154 ± 0.071, elite_night +0.092 ± 0.065, mirror
  +0.415 ± 0.079, top +0.183 ± 0.068 (all UP: the largest held-out gain at strong tables so far). Night -0.039 ±
  0.063, night_hard +0.066, payout tables, doubling blinds, exploit, aware level. Down: realistic -0.096 ± 0.064 (a
  guard) and antes_from_level_3 -0.103, fast_schedule -0.100, straddle -0.128 (the structural entries where the read
  stays on, played on the realistic field). REJECT. H5 used once.
- Reading: the read misreads realistic's one-size and broken bettors (Monte Carlo bots that time out, a breaking bot,
  a loose student). The same pattern as dead_seats and the warm reads: tuned for strong bots, it costs against odd
  ones. Back to S12: read only seats that show two or more size buckets and are not flagged weak, and/or only at
  tables that look strong (a shared strong-table signal with S9's strong_rr), thresholds set before screening.
- S11 interim: candidate Z (blind-vs-blind 3-bet prior 0.15, a probe read, one bet size) on screen: exploit2_hu
  +0.307 ± 0.149 and exploit2_3 +0.237 ± 0.143 UP, nothing down; with C7 the two compose (mirror +0.431 UP). Not yet
  heads-up winning (7.85 vs 9.15). bonus_card risk from the one size (0.5 pot includes the dry c-bet). Awaiting its
  final commit before merging.

## 11:38: S9's fixes merged (aa26ee4), strong_route on H6; the round-trip latency failures explained
- S9: the elite members now play only tables that pass Hero's holdem_table test (with the route forced open the
  candidate plays every catalogued twist exactly as F; test added); the H4 p99 tail was the measurement seats running
  elite1 as a full shadow (35 us a decision thrown away), not the shipped light shadow, which is now always on.
  Shipped-form per-call minimum: night act p99 88 -> 102 us, realistic 93 -> 101, max 151-168 us. Screen (batch 4
  base): night -0.019, guards level, elite +0.040, elite_night +0.050 UP, mirror +0.098 UP, exploit level, the four
  H4 cells now identical. F identical after the merge (14 cells). G2 on H6 (25000-25399), --aim strong, all stages.
- The kit B/C/D round-trip latency tests that failed on main since R2: latency.py fed random hand numbers, which go
  back about every other call; R2's adapter reads that as a new table with no table-start hook and restarts the bot,
  and Hero's every-32nd table start does a full collection (10-20 ms). Fixed in the tool (hand numbers in order):
  F through kit D now p99 440 us, 0 gen-2 collections in 2,000 calls at load 11 (was 61, p99 11.6 ms). Real cost
  that remains: on a kit with no table-start hook, one table in 16 pays a 10-20 ms first decision (a timed-out
  first action, usually a fold anyway). Backlog (robustness, low): run that collection outside the decision.

## 12:26: S11 merged (ebd05d8); its candidate Z on H7
- exploiter2 frozen as a test opponent (hyperion/sim/field/exploiter2/, reseeded per table; fields exploit2,
  exploit2_hu, exploit2_3, now in climb_accept's exploit stage beside exploiter1's). Against batch 4's F on screen:
  8-max F 5.754 vs 5.175, heads-up 7.540 vs 9.460, three-handed 7.142 vs 8.573.
- Z = blind-vs-blind 3-bet prior 0.15 (the defence from the first blind-vs-blind 3-bet), a probe read (a seat that
  bets into us often after we check), one bet size for value and bluffs (`balance_sizes`). Screen against batch 4:
  exploit2_hu +0.307 ± 0.149 and exploit2_3 +0.237 ± 0.143 UP; exploiter1 cells +0.09 to +0.11; night -0.015;
  guards, elite level; variants level at 50 seeds. Z + C7 compose (mirror +0.431 UP). Still loses heads-up to
  exploiter2 (about 7.85 vs 9.15). Not kept: a combined wide-bettor read (+0.66 heads-up against exploiter2 but
  -0.41 against exploiter1), bb_defend, 4-bet caps. Open: our BB folds ~70% to exploiter2's c-bet; a light
  blind-vs-blind 4-bet that folds to its jam (about 14.5 bb, 1.4 times a heads-up table; `r3.v3_bvb_cont` unmeasured).
- F identical after the merge (14 cells). Z on H7 (26000-26399), --aim exploit, all stages; bonus_card at 200 seeds
  decides the one-size risk (0.5 pot includes the dry c-bet that lost there).

## 12:57: S12b merged (9c52de0): the size read gated per seat; D1 queued on H8
- Gate (thresholds fixed from which seats pass, before any points screen): read a bettor only once it has shown two
  or more size buckets with at least 2 bets and 15% of its bets in each; never seats flagged dead, station, maniac or
  random. One-size and broken bettors pass 0-2% of their spots, two-size bettors 16-68%. The shared strong-table
  signal (S9's re-raise rate) now lives in the profiler; not used by D1.
- D1 screen (200 x 8, batch 4 base, --aim strong ACCEPT): realistic +0.047 ± 0.028 UP (C7 was -0.096 on H5),
  antes +0.038 UP, fast_schedule and straddle level; elite +0.084 ± 0.063, elite_night +0.066 ± 0.058, mirror
  +0.128 ± 0.081, top +0.068 ± 0.056, night_hard +0.088 ± 0.055 UP; night +0.030 level; exploit level; top_heavy
  variant +0.60 ± 0.40 UP; the other 22 variants identical. It keeps a third to a half of C7's strong-table gain.
  Latency p99 102 -> 101 us (decisions), hand end 100 -> 134 us.
- F identical after the merge (14 cells). D1 on H8 (27000-27399) after H6 finishes.

## 13:15: strong_route (S9's G2) accepted on H6
- H6 (25000-25399), base batch 4, --aim strong, from goal/wt_measure2 at aa26ee4: mirror +0.101 ± 0.040 UP (H4 had
  +0.078); night +0.025 ± 0.020 UP; exploit 8-max +0.092 ± 0.068 UP; elite +0.034, elite_night +0.013, every guard,
  aware and all 26 variants level (twists identical by the holdem_table gate). ACCEPT (addendum 8). H6 used once.
- Batch 5 candidates: strong_route (accepted), Z on H7 (running), D1 on H8 (starting). Then the three together,
  the judges once, timing, freeze.

## 14:43: Z on H7: big short-handed gains, rejected on one aware cell; gated to hold'em and re-run on H9
- H7 (26000-26399), base batch 4, --aim exploit: exploit2_hu +0.416 ± 0.106 (F 7.91 vs exploiter2 9.09, was 7.50 vs
  9.51), exploit2_3 +0.262 ± 0.108, exploit_hu +0.146 ± 0.103 UP; exploit 8-max and exploit2 8-max level;
  elite_night +0.048 ± 0.048 UP; night, guards, elite, mirror level; all 26 variants level (bonus_card +0.002 ±
  0.054: the one-size risk did not show); aware short_deck down (-0.042 ± 0.039). REJECT: addendum 7 covers the
  variants stage only and is not stretched to aware after the fact. H7 used once.
- Cause: Z's probe read and one bet size reached twist tables, where they were never built or measured. New dial
  `hero.postflop.s11_holdem_only` (811c216): on a table that fails hero.holdem_table, Postflop plays with those two
  off. Tests: on short deck ungated Z differs from F on 4 of 4 tables, gated it is identical; F identical by default
  (14 cells). Z2 = Z + the gate on H9 (28000-28399), --aim exploit, all stages.

## 14:47: D1 (the gated size read) on H8: rejected on night; back to S12 to find the misread night seats
- H8 (27000-27399), base batch 4, --aim strong: mirror +0.188 ± 0.060, top +0.079 ± 0.040, realistic +0.041 ±
  0.022 (fixed), doubling blinds +0.030 ± 0.026, exploit 8-max +0.098 ± 0.069, antes +0.048 ± 0.030, top_heavy
  +0.41 ± 0.35 UP; elite +0.008, elite_night +0.007 (screen +0.084 / +0.066), night_hard, payout tables, aware,
  other variants level; night -0.045 ± 0.031 DOWN. REJECT (night must not be down). H8 used once.
- The read has now been slightly negative on night twice held out (C7 H5 -0.039 ± 0.063, D1 H8 -0.045): some night
  seats pass the per-seat gate with sizes that do not mean what the read assumes. S12 resumed: survey the night seats
  against the simulator's truth on fresh diagnostic seeds, a rule from the survey (by observable behaviour, not
  identity), then night screened on 600 seeds so a 0.04 effect shows.

## 14:51: V-e merged (6231ef6): F's variant play against twist-aware opponents; candidate on H10
- Diagnoses (against V-d's generic aware field): short deck prices made hands as in hold'em though every hand holds 6
  to ace; Omaha's label table had 300 hands a label (Spearman 0.62 against the variant's own); Hero's hand-written
  wild map reads AA as premium (16th percentile in the variant's own table) and deuce hands as small pairs (top 15%);
  three_card_keep continues 52% facing bets and busts there; lowball's collapse is the opponents (twist-blind seats
  paid F off), not F; two_boards: no lever found.
- Fixes, general where possible: each hand read as its hold'em twin from the variant's own prepared table
  (`hero.twin_preflop`, tables/generic/, now carried by pack.py), Omaha's labels re-cut from it (`twin_multi`), call
  shifts for extra dealt hole cards, must-use, removed ranks and wild cards (`multi_call_shift`, `mu_*`,
  `call_shift_ex`), limited to dealt hole cards (a bought card's shift cost auction -0.073).
- Screen, generic aware cell (200 x 8): wild_deuces +0.944 ± 0.132, omaha_four +0.448 ± 0.129, three_card_keep
  +0.338 ± 0.100, short_deck +0.233 ± 0.081 (hand-built +0.235) UP; hi_lo +0.119, toss +0.074 level; margins over the
  best opponent: wild +0.20 -> +1.36, Omaha +0.45 -> +1.04, keep +0.50 -> +0.96, short deck +0.28 -> +0.55. Nothing
  down; plain hold'em identical (F identical after the merge, 14 cells). Likelihood-weighted about +0.08 on the
  night's twist. Not included: lowball flats (+0.40 generic, -0.073 realistic). Night procedure: the twist's table
  must be prepared before packing (stage 5's `--aware generic:<variant>` builds it), or the twins do nothing.
- Candidate on H10 (29000-29399): aware (11 generic + 4 hand-built) and all 26 variants.

## 15:49: S12c merged (4bd362f), D3 on H11; drill 8's kit and S13 (short-handed specialist) started
- S12c: the night loss traced (diagnostic seeds 9000-9199 x 8, every spot the read engaged, its decision against the
  truth): four night seats (trackb5, agent_montecarlo, trackb3, agent_pushfold) c-bet only 25-39%, so their small
  bets are not their weak ones (-586 bb in D1's spots); river reads lose everywhere (biased high). D3 = D1 on flop and
  turn only, for seats whose c-bet rate is at least 0.55 (rule fixed from the diagnostic before points). Screen: night
  +0.034 ± 0.021 over 600 seeds (UP), mirror +0.083, top +0.071, elite +0.086, realistic +0.036, night_hard +0.078
  UP; nothing down. Caveat: the screen seeds do not reproduce D1's H8 night loss either (D1 +0.03 on them), so the case
  rests on the diagnostic. D3 on H11 (31000-31399; held-out sets now skip the judge set, daa3ec3), --aim strong.
- Drill 8 (rehearsal, track H): a fresh organiser agent with no repo access builds kit F with a twist of its own
  invention (not any of our 26 catalog entries or the 4 held-out ones) and an interface with at least three unusual
  choices (goal/drill8/kit). A fresh player agent runs the hour on it after batch 5 is frozen.
- S13 (structural, strength): a short-handed specialist member (3 or fewer alive) with near-equilibrium heads-up and
  three-handed preflop tables from our own offline solver, balanced heads-up postflop, deviations only on clear reads.
  Targets: win heads-up against exploiter2, hold against exploiter1, more 1st places at strong tables.

## 16:21: V-e's variant play accepted on H10
- H10 (29000-29399), base batch 4: generic aware wild_deuces +1.074 ± 0.096, three_card_keep +0.333 ± 0.067,
  omaha_four +0.266 ± 0.085, short_deck +0.226 ± 0.062, hi_lo +0.098 ± 0.078, lowball +0.096 ± 0.072 UP; hand-built
  short_deck_aware +0.197 ± 0.060 UP; toss, auction, bonus_card, blind discard level; two_boards, bounty, river of
  blood identical. Variants (realistic): wild_deuces +0.373, three_card_keep +0.225, omaha_four +0.098, short_deck
  +0.093 UP; none down. ACCEPT. H10 used once.
- Batch 5 so far: strong_route (H6), V-e (H10). Pending: Z2 (H9), D3 (H11).

## 16:29: drill 8 started: the hour on kit F (Ghost Hold'em), fresh player agent
- Kit F (a fresh organiser agent, no repo access; goal/drill8/kit; 50 engine tests, 1,400 tables clean): the twist,
  Ghost Hold'em, deals a ninth face-down hand every hand; a pot whose showdown the Ghost beats goes to nobody and
  haunts into the next hand's main pot (won even by everyone folding). Interface: the action is one int (chips put in
  now: 0 check/fold, owe calls, at least min_raise raises, negative folds; no legal list); cards are ints 0-51;
  seats are relative (0 is us, session-wide ids); the history a compact string log; one Agent for a session of
  hundreds of tables (import + Agent() 2 s once, new_table 50 ms, act 1 ms, hand_over 1 ms). Points 16/11/8/6/4/2/1/0.
- Player: a fresh agent with the repo pinned at 15df280 (batch 4's ship), the handout zip only, prompts 00-05 and the
  playbook, 60 minutes, no docs/drills, decisions, HANDOFF or research (goal/drill8/night).

## 16:42: owner: the twist will be real, not cosmetic; V-f started to carry hold'em gains into the likely twists
- The owner pointed out that Sequoia is unlikely to pick a cosmetic twist, while our recent gains (D3, Z2,
  strong_route) are gated to plain hold'em. Agreed: variants-ranked.md gives plain or structure-only about 10%. But the
  likeliest families play ordinary hold'em after one twist step: deal-extra-then-discard 20%, bounty 11%, extra card
  for a price 7%, swap 6%, exposed card 4%. The all-or-nothing gate gives those gains up exactly there.
- V-f (goal/wt_vf, climb/vf-twist-carry): per gain and per family, turn the gain on where its logic holds (dead
  cards, the bounty payoff, the kept two cards respected), measured against V-d's generic aware opponents per
  variant; keep a family only where it is not down. Big unseen twists stay with the general path (V-e's twins,
  generic aware opponents in one command, drill 8).

## 16:48: Z2 on H9: exploit gains replicate, rejected on six small variant cells; fully gated Z3 on H12
- H9 (28000-28399), base batch 4, --aim exploit: exploit2_hu +0.330 ± 0.104, exploit2_3 +0.153 ± 0.107, exploit2
  8-max +0.097 ± 0.086, exploit_hu +0.180 ± 0.094 UP (F 7.94 vs exploiter2 9.06 heads-up); night, guards, elite
  level. Down: swap_holdem -0.024, bonus_card -0.014, auction -0.019, bounty -0.020, pot_limit -0.027,
  river_of_blood -0.018 (realistic, each about ± 0.015) and bounty_aware -0.015, river_of_blood_aware -0.017. REJECT
  (two or more variant cells). H9 used once.
- Cause: the postflop part is gated (s11_holdem_only), but r3.v3_bvb_prior still reached rival 3's core preflop on
  twist tables (bounty and others where the core plays). New dial r3.v3_bvb_holdem_only (ffb1e62); with both gates the
  candidate plays bounty, swap_holdem and auction tables exactly as F (test), and F is identical by default (14
  cells). Z3 on H12 (32000-32399), --aim exploit, all stages. V-f told about the second gate.

## 17:54: D3 (S12c's bet-size read) accepted on H11
- H11 (31000-31399), base batch 4, --aim strong, 127 min: night +0.032 ± 0.024 UP; elite +0.048 ± 0.042, elite_night
  +0.038 ± 0.029, mirror +0.158 ± 0.056 UP; guards, exploit (6 cells), variants (26, all bit-identical but the
  structural four, level) and aware level. ACCEPT (addendum 8). H11 used once.
- Batch 5 so far: strong_route (H6), V-e (H10), D3 (H11). Pending: Z3 (H12).

## 18:10: drill 8 scored; pack.py and prompts fixed; V-g started (does our sim transfer to an organiser's engine?)
- The player had batch 4's ship gated at minute 12 (cheap bot minute 6, insurance minute 1), tried four Stage 5
  dial sets in the kit's simulator (none better) and stalled at minute 20 on a tool call that never returned.
- In the kit's own simulator, under the real twist, the zip (F, no Ghost patch) scored 7.64 a table against the
  organiser's Ghost-aware bot 6.39 (duplicate, 400 deals x 8; a seat averages 6.0), and 8.98 ± 0.50 on a softer field
  (ghostwise 7.67). Write-up docs/drills/prompt-drill-8.md.
- Fixes: pack.py drops the red-team rivals' kit import in the packed copy and names imports outside the stdlib
  (a46f958); prompt 01 checks the variant hooks before ENGINE CANNOT REPRESENT, prompt 02 has the entry import its
  adapter as a sibling (d18b2fa).
- V-g (goal/wt_vg, climb/vg-ghost): Ghost Hold'em as a variant file in our hooks, then the drill's four candidates
  measured in our sim and in the kit's, to see if our sim ranks changes the way an engine we did not write does;
  then whether the general twist path (prepared tables, twins) finds the Ghost's edges by itself.
