# The climb: leaderboard

One page, updated after every accepted batch. Points are per table, averaged over the seeds shown, every seed played
in all eight seat rotations; "margin" is F minus the other bot on the same deals, with the 95% interval.

## Where we stand (2026-11-02 06:18 ET, batch 3)

**F (the composite) is first against every judge field.** On fresh seeds (30000-30399, 400 x 8), none of them ever
used for tuning (batch 3 changes only twist tables, so these hold'em numbers stand):

| field | 1. F | 2. hybrid3_x (margin) | 3. Hero (margin) |
|---|---|---|---|
| judge (rival 4 + realistic) | 6.483 | 6.263 (F +0.220 ± 0.082) | 6.100 (F +0.383 ± 0.085) |
| judge2 (rival 5 + realistic) | 6.524 | 6.328 (+0.196 ± 0.080) | 6.192 (+0.332 ± 0.088) |
| judge2_night (rival 5 + night pool) | 5.903 | 5.632 (+0.270 ± 0.086) | 5.616 (+0.287 ± 0.081) |
| judge_top (rivals 1-4) | 5.095 | 4.956 (+0.139 ± 0.084) | 4.885 (+0.210 ± 0.095) |
| outside (four fresh one-hour builds + night pool) | 5.418 | 5.281 (+0.137 ± 0.075) | 5.138 (+0.279 ± 0.086) |
| outside_strong (the four + rivals 4, 5 + agent_pushfold) | 5.034 | 4.947 (+0.088 ± 0.088, level) | 4.805 (+0.229 ± 0.091) |

**Against prepared top teams** (the elite field, three fresh builds told to make the strongest general bot; 150 seeds,
every seat ranked): F is 1st in a night room with two of them (5.35 vs 5.18) and 1st in the held-out strongest room
(4.93 vs 4.81), but 3rd at a table of only strong bots (4.67, behind rival 2 4.83 and elite 2 4.70, inside noise of
elite 2). It wins 1st place less often than they do.

**Against bots built to beat F** (fresh agents that see F only by playing it):
- exploiter 1: F loses (8-max 5.07 vs 5.26, heads-up 8.07 vs 8.93). Its fix, a 3-bet defence that reads a seat's
  3-bet rate, turns every format around on held-out seeds (+0.58 / +1.08 / +1.34) and is being confirmed alone for
  batch 4 (its companion c-bet change lost on one variant and opened a new leak).
- exploiter 2, against F with that fix: heads-up 9.52 vs F 7.48, three-handed 8.61 vs 7.21; 8-max F still ahead
  (5.65 vs 5.15). It defends wide against F's small-blind opens, reads F's bet sizes, and stabs when F checks. Fixes
  in progress (S11). Short-handed play decides 1st place, so this is the biggest open gap.

**On a slow sandbox:** with the governor (batch 2), F on a 3x slower box scores what it scores on a normal one; before
it lost 3.6 points of 100 under a top-heavy table (half the tables fell to the cheap path).

**Variants:** 25 of 25 catalogued entries READY, first on 24 (second on fixed_raise, level with rival 1). Against
variant-aware opponents (bots built for the twist), batch 3 adds toss_or_holdem +0.13, bounty +0.30, short deck +0.18
points a table (held-out seeds).

**Rehearsal (drill 7):** a fresh agent on an unfamiliar event-driven kit with an unseen variant had a legal upload at
minute 8 and the ship bot gated at minute 20; that zip beat raw F under the variant (+3.4 ± 6.5 of 100).

## Ship and frozen fallbacks

| when | ship | commit | kit B zip sha256 | why |
|---|---|---|---|---|
| 2026-11-01 20:28 (start) | composite F | d3a7ca5 | 3dc08142...0696d28783 | decisions entry "Composite bot" |
| 2026-11-01 22:52 (batch 1) | composite F | b48c272 | 8eeb870a...61987c3428d | same hold'em play; setup 0.95 -> 0.14 s, hand end cheaper and interrupt-safe, hook draws fixed, auction and deal5_keep2 |
| 2026-11-02 00:20 (batch 2) | composite F + governor | f7914c0 | a59f45b9...7f4f134327 | slow or noisy box: +3.64 of 100 (th), +0.14 (8..1) at 3x; bit-identical on a normal box |
| 2026-11-02 06:18 (batch 3) | composite F + governor + variant play | 9e620c8 | 774f0636...89bcf6f20 | twist tables: aware toss +0.13, bounty +0.30, short deck +0.18; plain hold'em identical |

Zips live in `frozen/` (git-ignored); each is rebuilt from its commit with `tools/pack.py --slim`.
