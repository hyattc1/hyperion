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
