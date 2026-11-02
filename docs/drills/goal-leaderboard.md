# The climb: leaderboard

One page, updated after every accepted batch. Points are per table, averaged over the seeds shown, every seed played
in all eight seat rotations; "margin" is F minus the other bot on the same deals, with the 95% interval.

## Where we stand (2026-11-01 22:50 ET, batch 1)

**F (the composite) is first against every judge field.** On fresh seeds (30000-30399, 400 x 8), none of them ever
used for tuning:

| field | 1. F | 2. hybrid3_x (margin) | 3. Hero (margin) |
|---|---|---|---|
| judge (rival 4 + realistic) | 6.483 | 6.263 (F +0.220 ± 0.082) | 6.100 (F +0.383 ± 0.085) |
| judge2 (rival 5 + realistic) | 6.524 | 6.328 (+0.196 ± 0.080) | 6.192 (+0.332 ± 0.088) |
| judge2_night (rival 5 + night pool) | 5.903 | 5.632 (+0.270 ± 0.086) | 5.616 (+0.287 ± 0.081) |
| judge_top (rivals 1-4) | 5.095 | 4.956 (+0.139 ± 0.084) | 4.885 (+0.210 ± 0.095) |
| outside (four fresh one-hour builds + night pool) | 5.418 | 5.281 (+0.137 ± 0.075) | 5.138 (+0.279 ± 0.086) |
| outside_strong (the four + rivals 4, 5 + agent_pushfold) | 5.034 | 4.947 (+0.088 ± 0.088, level) | 4.805 (+0.229 ± 0.091) |

**Against the exploiter** (a bot built to beat F from the black box), F loses: 8-max 5.065 vs 5.255, heads-up 8.071
vs 8.929. The fixes are in progress (S2).

**Variants:** 25 of 25 catalogued entries READY, first on 24 (second on fixed_raise, level with rival 1).

**Rehearsal (drill 7):** a fresh agent on an unfamiliar event-driven kit with an unseen variant had a legal upload at
minute 8 and the ship bot gated at minute 20; that zip beat raw F under the variant (+3.4 ± 6.5 of 100).

## Ship and frozen fallbacks

| when | ship | commit | kit B zip sha256 | why |
|---|---|---|---|---|
| 2026-11-01 20:28 (start) | composite F | d3a7ca5 | 3dc08142...0696d28783 | decisions entry "Composite bot" |
| 2026-11-01 22:52 (batch 1) | composite F | b48c272 | 8eeb870a...61987c3428d | same hold'em play; setup 0.95 -> 0.14 s, hand end cheaper and interrupt-safe, hook draws fixed, auction and deal5_keep2 |

Zips live in `frozen/` (git-ignored); each is rebuilt from its commit with `tools/pack.py --slim`.
