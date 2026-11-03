# S18: horizon-aware ICM (the blinds each stack still owes)

Branch climb/s18-horizon-icm, from main 11cc61f (batch 5 is F). Item 5 of `docs/research/Edges against strong
opponents.md`. Screens only: seeds 10000-10199 (`--set screen`); diagnostics, if any, on seeds 8600-8699. No held-out
set, judge set, judge bot, judge field or held-out variant is run, read or tuned on. Workers: at most 3, nice 5.

## Findings

- **Not accepted: the horizon is level where it should gain and down in four cells.** One form, fixed before any
  screen (section 0), screen set 10000-10199, base F:
  - night +0.010 ± 0.044 (level, not up);
  - guards all level; no guard payout table is up (10/7/5/4/3/2/1/0 +0.020 ± 0.074, 50/25/12/6/3/2/1/1 -0.024 ±
    0.551, doubling blinds -0.012 ± 0.044);
  - the three variants the report expected most from are level (fast_schedule -0.036 ± 0.048, antes_from_level_3
    -0.018 ± 0.036, top_heavy +0.015 ± 0.461); elite's five fields level (-0.026 to +0.038);
  - **down: exploit (exploiter 1, 8-max) -0.107 ± 0.104, adapt (adapt1, 8-max) -0.081 ± 0.077**, three_card_keep
    -0.020 ± 0.018 and auction -0.025 ± 0.024, each just past its interval; up: two_boards +0.060 ± 0.046.
  - An exploit cell down rejects under every aim, so it is a reject whatever the aim.
- **The form barely changes play.** 0.30% of F's decisions differ (13 of 4,343 on 24 diagnostic night tables, about
  one every two tables). Far from the cap every stack but the next button's loses about 1.5 bb, which moves ICM only
  for short stacks; within the last orbit the correction fades to nothing, where ICM is the cap's payoff anyway. The
  report's expected +0.01 to +0.03 would be under this screen's resolution (± 0.044 on night) even if it were there.
- **The late-table report (F, tables still three-or-more-handed at hand 150):** about half of all tables (night 777
  of 1,600; night_hard 882, realistic 866, top 1,206, elite 914-1,042; doubling blinds only 43). On them F scores
  5.87 at night (5.97 overall), is already out of 36% of them by hand 150 (realistic 30%, top 45%, elite ~50%), and
  busts 32% of the seats still in during the last 50 hands (realistic 19%, top 55%, elite 56-73%). The horizon moves
  none of these beyond noise (paired on F's late tables: night -0.012 ± 0.079; brief +0.050 ± 0.128; top-heavy +0.27 ±
  0.93, its busts after 150 32.1 -> 29.6%, the expected direction but inside the noise).
- **The 150-hand cap guard** (`docs/drills/climb/rules/cap150.json`): 94-99% of tables reach hand 100 three-or-more-
  handed, so the cap governs nearly every table; every cell is level (night +0.007 ± 0.037, top-heavy -0.119 ±
  0.356).
- **Cost.** No per-decision cost beyond noise (act p99 108.5 -> 113.0 us plain, 157.2 -> 154.0 top_heavy). Hand end
  +9 us on plain (p99 146.7 -> 155.5) and +14 us under top_heavy (p99 343.9 -> 357.5): the owed blinds move with the
  button every hand, so the curve's memoised exact ICM hits less. That is the form's own cost.
- **Identity.** With the dial off F plays bit for bit: 14 of 14 chunks identical to main 11cc61f on 10000-10039
  (confirm and guards), at both commits that touch code.
- **What stays, all off by default:** `icm.horizon` (`hero.icm_horizon`, `r3.icm_horizon`; hero.blinds_owed,
  horizon_stack), `climb_accept --late` (records kept in every cell; the report for confirm, guards, elite, window),
  `run_tournament(late_at=)`, the cap150 rules file, and the note on `cap_vol_bb` (kit F's chip-rank rule, not the
  official ICM split, so it stays off). Not swept, as specified; I would not try other forms of this rule on the
  screen set: the decisions it changes are too few to measure, and the cells that moved moved against it.

## 0. The form, fixed before any screen

Written before any code ran. One form, not swept. The rule is the research note's own heuristic (poker_ai_literature
§8: "subtract the blinds a stack must post before its next button before evaluating ICM ... not from the literature"),
motivated by Ganzfried & Sandholm's worst ICM error (a big blind about to post most of his stack).

For the hand being priced, h (0-based), with button b_h, the seats A with chips at its start (k = |A|), the hand cap
C = `rules.max_hands` and blinds (SB_t, BB_t) = `rules.blinds_at(t)`:

- The button of hand h+1 is the next seat of A clockwise after b_h. Number A's seats clockwise from it, offset
  j = 0 (the button of h+1), 1, ..., k-1. Nobody is assumed to bust.
- **Blinds owed** before the seat's next button (hand h+1+j) or the cap, whichever comes first:
  - k >= 3: the seat at offset j >= 1 posts the small blind at hand h+j and, if j >= 2, the big blind at hand h+j-1:
    `o = [h+j < C] SB_{h+j} + [j >= 2] [h+j-1 < C] BB_{h+j-1}`; offset 0 owes 0.
  - k = 2 (heads-up, the button posts the small blind on its own button hand): the seat off the button at h+1 owes
    `[h+1 < C] BB_{h+1}`; the button owes 0.
  - Antes and a straddle are not counted (blinds only).
- **Effective stack** `s' = max(s - o, s / 2)` for every s > 0 (0 stays 0): a stack that cannot cover what it owes is
  all-in in the blinds, not busted, so it keeps half (every live seat stays in ICM, and no stack loses more than half).
  The floor is part of the form, fixed here, not swept.
- **ICM on effective stacks.** Every ICM evaluation of a scenario (my stack after the hand and each other stack) uses
  s' in place of s, with the table's payouts. A scenario where I hold 0 is the bust payout, unchanged. In the last
  hand (h = C-1) nothing is owed and ICM is the cap's payoff exactly.
- **Where.** Dial `icm.horizon` (off by default), which sets both:
  - `hero.icm_horizon`: Hero's `IcmCurve` (built at hand end): at each sampled stack x of mine (the others pro rata),
    x and the other stacks become effective. b_h is the next live seat after the last button Hero saw (advanced one
    live seat per hand since); the curve for a table's first hand (no button seen yet) is plain ICM.
  - `r3.icm_horizon`: rival 3's core, in `_allin` (fold, steal, win, lose) and `_vs3bet`'s lose: each scenario's
    stacks become effective, o computed once per hand from that hand's button and live seats (chips or in the hand).
- `cap_vol_bb` stays off: it ranks survivors by chips at the cap (kit F's `cap_places: chips`), not the official ICM
  split.

## 1. Runs

### 1.1 Diagnostic: how often the dial changes a decision (after the form was written; nothing tuned on it)

`WT=<worktree> python goal/s18/flips.py night 8600 8603` (scratch): F plays night (seeds 8600-8602, 8 rotations, model
mode); a copy of F with `icm.horizon` on sees the same observations and hand ends, and every decision where the two
differ is counted. **13 of 4,343 decisions differ (0.30%)**, about one every two tables: 5 preflop at hand < 100 with
5+ alive, 4 preflop at hands 100-149, 3 preflop heads-up after hand 150, 1 postflop. F fold -> horizon raise 5, call ->
fold 4, raise -> fold 2, check -> raise 1, call -> raise 1. The effect is small by construction: far from the cap
every stack but the next button loses about 1.5 bb, which moves ICM only for short stacks.

### 1.2 Identity: the dial off plays F bit for bit

`tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, one worker each, separate
output directories: on main 11cc61f in a detached worktree (code f730e26b45) and on this branch with the dial and the
late-table records in (code f730e26b45-4ed08657). **All 14 chunks' sample lists are identical** (night, night_hard,
realistic, top, night at 10/7/5/4/3/2/1/0 and 50/25/12/6/3/2/1/1, night with doubling blinds), and identical to the
coordinator's own run after the S14 merge (goal/idchk20). Night 5.965, night_hard 5.638, realistic 6.269, top 5.023,
brief 6.218, top-heavy 24.589, doubling 5.853. The late-table records drive the same tables hand by hand
(tests/test_s18_horizon.py checks the samples are unchanged).

Commits: c1b7a23 (the dial, the late records, cap150.json), fcb06d6 (the same values, cheaper: below). Identity re-run
on fcb06d6 (code 8793138c55, the branch side only, against main's chunks above): **14 of 14 identical**.

Tests: the full suite at c1b7a23 under host load 9-14 had 17 failures, all wall-clock ones: per-bot p99 budgets in a
mixed field (test_sim_bestiary, 11 bots none of which this branch touches), the cheap bot's kit_d round trip, the
slow-box panic, the gate's measure-mode timeouts (0.42% > 0.3%), and the three "replay exactly in model mode" tests
that are marked timing. Rerun alone: the replay and gate tests pass (17 of 17); the budget tests pass except two other
untouched bots (out_quants, rob_mc) on that run. tests/test_s18_horizon.py (10 tests) passes.

## 2. Latency

`tools/latency.py --hand-end --tables 20 --reps 3 --p99-us 100000 [--variant top_heavy] [--dials '{"icm.horizon":
true}']`, realistic field, per-call minimum of 3, host load 13.7-14.5, at fcb06d6. Each bot is timed on the tables it
plays itself (the dial changes them a little: 2,946 vs 2,896 hand ends on plain).

| table | bot | hand_end mean / p99 / max | act mean / p99 / max |
|---|---|---|---|
| plain hold'em | F | 64.0 / 146.7 / 227.6 | 56.2 / 108.5 / 146.3 |
| plain hold'em | icm.horizon | 72.8 / 155.5 / 208.8 | 57.3 / 113.0 / 221.6 |
| top_heavy | F | 131.5 / 343.9 / 416.3 | 63.1 / 157.2 / 220.7 |
| top_heavy | icm.horizon | 146.2 / 357.5 / 548.5 | 64.4 / 154.0 / 222.1 |

- Act p99 is under 200 us everywhere; the per-decision cost is within noise (+1 us mean). Rival 3's core prices
  all-ins inside decisions: the blinds owed are computed in its `start_hand` (hand end) and a decision only adds the
  effective-stack list to each of its four ICM calls (+1.4 us an all-in price, micro-benchmark).
- Hand end costs +9 us on plain hold'em (the curve's 13 points each build the effective stacks; +4 us a curve by
  micro-benchmark, plus `blinds_owed` 1.2 us) and **+14 us at p99 under top_heavy**: there the curve is memoised exact
  ICM on rounded stacks, and the owed blinds move with the button every hand, so fewer points hit the memo. That cost
  is the form's (the values cannot be kept and the keys reused); the only way to remove it would be to change the form.
- The first version (c1b7a23) cost more: +12 us hand end on plain and +13 us for the first all-in price of each hand
  inside a decision (the owed blinds computed there). fcb06d6 moved that to the hand end and fused the curve's loops;
  the values are the same (tests).

## 3. Screens (seeds 10000-10199, 8 rotations each, model mode, code 8793138c55 = fcb06d6)

Scratch runner goal/s18/screen2.sh, cache goal/s18/ca, 3 workers at nice 5, host load 14-21. Base `{"dials": {}}`
(F), candidate `{"dials": {"icm.horizon": true}}`.

### 3.1 s1: confirm and guards, with the late-table report (25 min)

`tools/climb_accept.py --cand '{"dials": {"icm.horizon": true}}' --set screen --stages confirm,guards --late
--workers 3`. F's numbers are batch 5's on this set (S14's base: night 5.972, night_hard 5.499 ...).

| cell | F | horizon | horizon - F | |
|---|---|---|---|---|
| night | 5.972 | 5.982 | +0.010 ± 0.044 | level |
| night_hard | 5.499 | 5.479 | -0.020 ± 0.051 | level |
| realistic | 6.370 | 6.364 | -0.006 ± 0.040 | level |
| top | 5.058 | 5.074 | +0.016 ± 0.058 | level |
| night @10/7/5/4/3/2/1/0 | 6.199 | 6.219 | +0.020 ± 0.074 | level |
| night @50/25/12/6/3/2/1/1 | 24.699 | 24.675 | -0.024 ± 0.551 | level |
| night +double | 5.848 | 5.836 | -0.012 ± 0.044 | level |

**The late-table report** (tables still running at hand 150 with three or more players alive; 1,600 tables a cell =
200 seeds x 8 rotations; "bust" = F's seats busted by the end on those tables, "alive then" = F still in at hand 150,
"bust after" = busted in the last 50 hands given alive at 150; the last column is the paired difference on F's own late
tables, the same deals, 95% interval clustered by seed):

| cell | late tables F/hz | F pts there | hz pts there | bust F/hz | alive at 150 F/hz | bust after F/hz | hz - F on F's late tables |
|---|---|---|---|---|---|---|---|
| night | 777/759 | 5.868 ± 0.144 | 5.888 ± 0.150 | 56.5/56.5% | 64.4/65.0% | 32.4/33.1% | -0.012 ± 0.079 |
| night_hard | 882/892 | 5.355 ± 0.160 | 5.389 ± 0.163 | 67.3/66.8% | 57.3/58.2% | 43.0/43.0% | -0.011 ± 0.075 |
| realistic | 866/874 | 6.349 ± 0.131 | 6.340 ± 0.129 | 42.7/43.8% | 70.3/69.8% | 18.6/19.5% | -0.015 ± 0.060 |
| top | 1206/1202 | 4.976 ± 0.125 | 4.997 ± 0.123 | 75.1/72.8% | 54.7/55.5% | 54.5/51.0% | +0.017 ± 0.071 |
| night @10/7/5/... | 749/749 | 6.036 ± 0.233 | 6.159 ± 0.247 | 55.9/54.5% | 61.5/63.2% | 28.4/27.9% | +0.050 ± 0.128 |
| night @50/25/12/... | 722/732 | 23.165 ± 1.498 | 23.964 ± 1.482 | 58.4/55.9% | 61.2/62.7% | 32.1/29.6% | +0.272 ± 0.927 |
| night +double | 43/38 | 5.326 ± 0.604 | 5.395 ± 0.540 | 76.7/76.3% | 46.5/47.4% | 50.0/50.0% | -0.070 ± 0.434 |

- About half the tables (47-55%; 75% at `top`) are still three-or-more-handed at hand 150, as the pro note guessed;
  with doubling blinds almost none are (43 of 1,600).
- On those tables F scores a little under its overall mean (night 5.87 against 5.97) and is already out of 36% of them
  by hand 150; of the seats still in, a third bust in the last 50 hands (night 32%, realistic 19%, top 55%).
- The dial moves none of it beyond noise. The largest late-table shifts are under the two non-linear payout tables
  (brief +0.050 ± 0.128, top-heavy +0.27 ± 0.93; F's busts after hand 150 there 28.4 -> 27.9% and 32.1 -> 29.6%),
  the direction the report expected, but inside the noise.

### 3.2 Elite and exploit (part of `--stages confirm,guards,elite,exploit,variants --late --aim night`)

Printed from the cache with `--stages elite,exploit --late` once both specs' chunks were in (goal/s18/s3a.md).

| cell | F | horizon | horizon - F | | exploiter F/hz |
|---|---|---|---|---|---|
| exploit (exploiter 1, 8-max, 10/7/5/...) | 5.839 | 5.731 | **-0.107 ± 0.104** | **DOWN** | 4.608/4.676 |
| exploit_hu | 9.227 | 9.175 | -0.052 ± 0.070 | level | 7.772/7.825 |
| exploit_3 | 8.458 | 8.418 | -0.040 ± 0.076 | level | 6.900/6.890 |
| exploit2 | 5.844 | 5.882 | +0.038 ± 0.082 | level | 5.086/5.056 |
| exploit2_hu | 7.848 | 7.862 | +0.015 ± 0.047 | level | 9.152/9.137 |
| exploit2_3 | 7.378 | 7.348 | -0.030 ± 0.076 | level | 8.165/8.162 |
| exploit3 | 5.471 | 5.433 | -0.038 ± 0.081 | level | 5.306/5.324 |
| exploit3_hu | 8.268 | 8.275 | +0.007 ± 0.053 | level | 8.732/8.725 |
| exploit3_3 | 7.528 | 7.572 | +0.043 ± 0.091 | level | 7.952/7.895 |
| adapt (adapt1, 8-max, 10/7/5/...) | 5.889 | 5.808 | **-0.081 ± 0.077** | **DOWN** | 5.106/5.136 |
| adapt_hu | 8.605 | 8.605 | +0.000 ± 0.055 | level | 8.395/8.395 |
| adapt_3 | 8.007 | 7.987 | -0.020 ± 0.075 | level | 7.657/7.677 |
| elite | 4.865 | 4.839 | -0.026 ± 0.052 | level | |
| elite_night | 5.422 | 5.434 | +0.012 ± 0.042 | level | |
| mirror | 4.498 | 4.533 | +0.035 ± 0.056 | level | |
| elite_b | 4.638 | 4.676 | +0.038 ± 0.060 | level | |
| mirror_b | 4.466 | 4.490 | +0.024 ± 0.057 | level | |

Late tables at elite (hand 150, 3+ alive; hz - F on F's late tables): elite -0.041 ± 0.079, elite_night +0.012 ±
0.072, mirror -0.005 ± 0.088, elite_b +0.050 ± 0.087, mirror_b +0.039 ± 0.078, all level. F is out of about half of
these tables by hand 150 and busts 56-73% of the rest in the last 50 hands.

**Two exploit cells are beyond noise down, so the candidate is rejected under every aim** (climb_accept's rule since
S14). Both are the 8-max cells under the brief's payouts (exploiter 1 and adapt1); both are just past the edge of the
interval (-0.107 against ± 0.104, -0.081 against ± 0.077), and the heads-up and three-handed cells of the same bots are
level. Two downs in twelve cells at that margin could be partly chance, but the rule counts them and I did not
re-run them on other seeds (that would be choosing seeds after the fact).

The run was then reordered (goal/s18/screen3.sh, detached): the 150-hand cap on confirm and guards, then the three
named variants, then the whole catalog.

### 3.3 s2: the 150-hand cap (`--rules docs/drills/climb/rules/cap150.json --stages confirm,guards --late`)

The guard file caps the table at 150 hands; the late checkpoint is then hand 100 (50 before the cap). The doubling cell
keeps its own rules file, so it is s1's.

| cell (cap 150) | F | horizon | horizon - F | | late tables F/hz | hz - F on F's late tables |
|---|---|---|---|---|---|---|
| night | 5.870 | 5.877 | +0.007 ± 0.037 | level | 1510/1507 | +0.007 ± 0.039 |
| night_hard | 5.429 | 5.413 | -0.016 ± 0.041 | level | 1558/1556 | -0.019 ± 0.042 |
| realistic | 6.182 | 6.183 | +0.001 ± 0.030 | level | 1526/1527 | +0.002 ± 0.031 |
| top | 5.089 | 5.081 | -0.008 ± 0.045 | level | 1591/1590 | -0.008 ± 0.045 |
| night @10/7/5/... | 5.908 | 5.928 | +0.019 ± 0.052 | level | 1505/1501 | +0.019 ± 0.055 |
| night @50/25/12/... | 22.661 | 22.542 | -0.119 ± 0.356 | level | 1505/1503 | -0.129 ± 0.378 |

With the cap at 150, 94-99% of tables are still three-or-more-handed at hand 100, so nearly every table ends at the
cap and the horizon is in play for its whole last stretch; still nothing moves. F at hand 100: alive 73-81%, busting
18-34% of those seats in the last 50 hands.

### 3.4 s4: the three named variants (`--stages variants --variants fast_schedule,antes_from_level_3,top_heavy`)

| cell (realistic) | F | horizon | horizon - F | |
|---|---|---|---|---|
| fast_schedule | 6.122 | 6.087 | -0.036 ± 0.048 | level |
| antes_from_level_3 | 6.496 | 6.478 | -0.018 ± 0.036 | level |
| top_heavy | 28.654 | 28.669 | +0.015 ± 0.461 | level |

None of the three the report expected to gain most (faster blinds, antes, top-heavy payouts) moves.

### 3.5 s3: every stage (`--stages confirm,guards,elite,exploit,variants --late --aim night`), the whole catalog

Confirm, guards, elite and exploit as above (cached). The catalog on realistic, 200 seeds each (s4's three included):

| cell | F | horizon | horizon - F | |
|---|---|---|---|---|
| permuted_ranks | 6.693 | 6.669 | -0.023 ± 0.036 | level |
| short_deck | 6.362 | 6.371 | +0.009 ± 0.017 | level |
| lowball | 7.796 | 7.804 | +0.008 ± 0.009 | level |
| wild_deuces | 7.422 | 7.433 | +0.011 ± 0.020 | level |
| flush_over_full_house | 6.140 | 6.131 | -0.009 ± 0.029 | level |
| toss_or_holdem | 6.497 | 6.491 | -0.006 ± 0.021 | level |
| three_card_blind_discard | 6.434 | 6.422 | -0.012 ± 0.020 | level |
| three_card_keep | 6.425 | 6.405 | **-0.020 ± 0.018** | **DOWN** |
| omaha_four | 6.826 | 6.821 | -0.005 ± 0.011 | level |
| swap_holdem | 6.343 | 6.354 | +0.012 ± 0.039 | level |
| swap_one_turn | 6.440 | 6.427 | -0.013 ± 0.037 | level |
| exposed_card | 6.167 | 6.175 | +0.008 ± 0.030 | level |
| two_boards | 6.127 | 6.188 | +0.060 ± 0.046 | UP |
| bonus_card | 5.980 | 5.968 | -0.012 ± 0.032 | level |
| auction | 6.531 | 6.506 | **-0.025 ± 0.024** | **DOWN** |
| deal5_keep2 | 6.884 | 6.884 | -0.000 ± 0.006 | level |
| bounty | 6.389 | 6.377 | -0.013 ± 0.032 | level |
| knockout_bounty | 8.102 | 8.093 | -0.009 ± 0.063 | level |
| top_heavy | 28.654 | 28.669 | +0.015 ± 0.461 | level |
| hi_lo | 6.166 | 6.169 | +0.002 ± 0.034 | level |
| pot_limit | 6.387 | 6.344 | -0.043 ± 0.045 | level |
| antes_from_level_3 | 6.496 | 6.478 | -0.018 ± 0.036 | level |
| fixed_raise | 6.307 | 6.309 | +0.003 ± 0.032 | level |
| fast_schedule | 6.122 | 6.087 | -0.036 ± 0.048 | level |
| straddle | 6.412 | 6.402 | -0.010 ± 0.026 | level |
| river_of_blood | 6.301 | 6.298 | -0.003 ± 0.037 | level |

Verdict (`--aim night`): **REJECT**. Confirm: night level, not up. Guards none down. Elite none down. Variants: two
down (three_card_keep, auction; both just past the interval), so not addendum 7's lone-cell
replication case either. Exploit: two down (exploit, adapt; section 3.2). 23 of 26 variant cells moved by less than
0.03. The catalog took 108 minutes at host load 16-56 (3 workers, started before the coordinator capped runs at 2).
