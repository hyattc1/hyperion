# S18: horizon-aware ICM (the blinds each stack still owes)

Branch climb/s18-horizon-icm, from main 11cc61f (batch 5 is F). Item 5 of `docs/research/Edges against strong
opponents.md`. Screens only: seeds 10000-10199 (`--set screen`); diagnostics, if any, on seeds 8600-8699. No held-out
set, judge set, judge bot, judge field or held-out variant is run, read or tuned on. Workers: at most 3, nice 5.

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
