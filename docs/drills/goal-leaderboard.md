# The climb: leaderboard

One page, updated after every accepted batch. Points are per table, averaged over the seeds shown, every seed played
in all eight seat rotations; "margin" is F minus the other bot on the same deals, with the 95% interval.

## Where we stand (2026-11-04 23:30 ET, batch 8)

Batch 8 is the known-good upload (frozen/B8-77c5ea6). Against batch 7 on held-out H34: strong tables +0.06 to +0.09, exploit and
adapt cells up to +0.19, ordinary rooms level, nothing down. Judges on fresh seeds: five up, eight level, none down. Open risk:
through a kit's adapter, timeouts pass the gate's limit from about 1.5-2x slower than this box (12% at 3x); G1 is on it.
The tables below are batch 5's unless they say otherwise.

### Batch 7

Batch 7 (frozen, gate pass) changes plain hold'em only with three or fewer alive against
exploiter-like seats (its 8-max, judge and strong-table cells within ±0.002 of batch 6), so the judge, night and
elite-room numbers below are batch 5's and hold for batches 6 and 7. Batch 7 on held-out H31 against batch 6:
exploiter 2 heads-up +0.307, three-handed +0.086, exploiter 3 heads-up +0.096, auction +0.060, tranche_holdem +0.180.

**F (the composite) is first against every judge field.** On fresh seeds (30000-30399, 400 x 8), none of them ever
used for tuning. Batch 5 moved judge_top +0.106 and outside +0.087 (beyond noise) and left the rest level; the
fallbacks' margins below are batch 4's measured margins plus F's paired change on the same deals:

| field | 1. F | 2. hybrid3_x (margin) | 3. Hero (margin) |
|---|---|---|---|
| judge (rival 4 + realistic) | 6.457 | 6.263 (F +0.194) | 6.100 (F +0.357) |
| judge2 (rival 5 + realistic) | 6.524 | 6.328 (+0.196) | 6.192 (+0.332) |
| judge2_night (rival 5 + night pool) | 5.892 | 5.632 (+0.259) | 5.616 (+0.276) |
| judge_top (rivals 1-4) | 5.201 | 4.956 (+0.245) | 4.885 (+0.316) |
| outside (four fresh one-hour builds + night pool) | 5.507 | 5.281 (+0.226) | 5.138 (+0.368) |
| outside_strong (the four + rivals 4, 5 + agent_pushfold) | 5.059 | 4.947 (+0.113) | 4.805 (+0.254) |

**On the night field, batch 5 is up beyond noise** on held-out seeds (H13, 33000-33399): +0.096 ± 0.053 points a
table against batch 4, +0.23 under a 10/7/5 table and +1.0 under a top-heavy one.

**Against prepared top teams** (the elite builds: fresh agents told to make the strongest general bot; 150 seeds x 8,
every seat ranked, diagnostic): F is now **1st** in the room of strong bots (4.84; rival 2 4.80, elite 2 4.67; batch
4 was 2nd at 4.75) and 1st in the night room with two of them (5.34 vs elite 2 5.23). At the mirror table (three
copies of F with rival 2, elite 1, elite 2, hybrid3_x) F rose from 5th of six to about 3rd (4.52-4.54, rival 2 4.75):
paired on held-out seeds, +0.241 ± 0.065. Elite 2 and elite 1 still take 1st place more often (19-24% against F's
12-18%). Two more prepared-team builds are being made (elite 4 for tuning, elite 5 held out as a judge).

**Against bots built to beat F** (fresh agents that see F only by playing it), on held-out seeds after batch 5:
- exploiter 1: F wins every format: 8-max 5.72 vs 4.55, heads-up 9.27 vs 7.73, three-handed 8.47 vs 6.92.
- exploiter 2: F wins 8-max (5.79 vs 5.06); heads-up 7.80 vs its 9.20 and three-handed 7.35 vs 8.23 it still leads,
  by less than before (it was 7.50 vs 9.50 and 7.15 vs 8.57). Batch 7 adds +0.307 heads-up and +0.086 three-handed
  (held-out H31): about 8.11 vs 8.89 heads-up, the gap roughly halved; batch 8's C3h adds +0.225 heads-up alone (H28).

**On a slow sandbox:** with the governor (batch 2), F on a 3x slower box scores what it scores on a normal one.

**Variants:** 25 of 25 catalogued entries READY. Batch 6 (2026-11-03, twist tables only) adds, on held-out seeds:
exposed card +0.22, knockout bounty +0.11, bounty against bounty-aware bots +0.03. Batch 5 added: wild_deuces +0.39, three_card_keep
+0.19, omaha_four +0.16, short_deck +0.15 (and +0.22 against short-deck-aware bots), on top of batches 3-4 (toss,
bounty, short deck, keep2). A ninth catalog-free twist (drill 8's Ghost Hold'em, an organiser agent's own engine): the
drill's zip of batch 4 scored 7.64 a table against the organiser's Ghost-aware bot's 6.39.

**Rehearsals:** drill 7 (event-driven kit, unseen variant): legal upload minute 8, ship gated minute 20. Drill 8
(one Agent per session, int actions, Ghost Hold'em): insurance minute 1, ship gated minute 12.

## Since the start (the starting F against today's, plain hold'em)

The starting F's settings (2026-11-01 20:28, every dial added since at its default) against batch 6, on fresh seeds
(H17, 37000-37399, 400 x 8, paired; plain hold'em, so batch 6 plays as batch 5 here). Twist gains are on top (batches
3, 5 and 6, each measured against its own base).

| family | cell | start | now | change |
|---|---|---|---|---|
| strong tables | elite | 4.666 | 4.817 | **+0.151 ± 0.061** |
| | mirror (three F copies, rival 2, elite 1, elite 2, hybrid3_x) | 4.320 | 4.533 | **+0.213 ± 0.072** |
| | elite_b / mirror_b (second wave) | 4.620 / 4.390 | 4.695 / 4.561 | **+0.075 / +0.171** |
| | elite_night | 5.390 | 5.439 | +0.049 ± 0.055 |
| | top (rivals 1-4) | 5.061 | 5.165 | **+0.104 ± 0.059** |
| exploiters | exploiter 1: 8-max / heads-up / three-handed | 5.015 / 8.054 / 7.202 | 5.755 / 9.265 / 8.568 | **+0.74 / +1.21 / +1.37** |
| | exploiter 2: 8-max / heads-up / three-handed | 5.673 / 7.555 / 7.318 | 5.761 / 7.926 / 7.487 | +0.09 / **+0.37 / +0.17** |
| | exploiter 3: 8-max / heads-up / three-handed | 5.378 / 8.354 / 7.671 | 5.509 / 8.373 / 7.619 | **+0.13** / +0.02 / -0.05 |
| adaptive | adapt1: 8-max / heads-up / three-handed | 5.623 / 8.605 / 8.053 | 5.720 / 8.721 / 8.117 | **+0.10 / +0.12** / +0.06 |
| ordinary rooms | night / night_hard / realistic | 6.030 / 5.491 / 6.418 | 6.016 / 5.524 / 6.424 | -0.01 / +0.03 / +0.01 (level) |

Bold: beyond noise up. Nothing is beyond noise down. The weighted score (addendum 11): +0.084 ± 0.033 night points a
table (lower bound +0.051). The gains are where the climb aimed: strong tables, bots that hunt F's leaks, and twists.
On ordinary rooms F was already first, and it has not measurably moved there.

## Ship and frozen fallbacks

| when | ship | commit | kit B zip sha256 | why |
|---|---|---|---|---|
| 2026-11-01 20:28 (start) | composite F | d3a7ca5 | 3dc08142...0696d28783 | decisions entry "Composite bot" |
| 2026-11-01 22:52 (batch 1) | composite F | b48c272 | 8eeb870a...61987c3428d | same hold'em play; setup 0.95 -> 0.14 s, hand end cheaper and interrupt-safe, hook draws fixed, auction and deal5_keep2 |
| 2026-11-02 00:20 (batch 2) | composite F + governor | f7914c0 | a59f45b9...7f4f134327 | slow or noisy box: +3.64 of 100 (th), +0.14 (8..1) at 3x; bit-identical on a normal box |
| 2026-11-02 06:18 (batch 3) | composite F + governor + variant play | 9e620c8 | 774f0636...89bcf6f20 | twist tables: aware toss +0.13, bounty +0.30, short deck +0.18; plain hold'em identical |
| 2026-11-02 08:59 (batch 4) | + 3-bet defence, keep2/toss calls, kit fixes | e3cec13 | bb5820cc...6197fe | beats exploiter 1 in every format; keep2 +0.29; adapter reads 20 kit shapes; no test bots in the zip |
| 2026-11-02 20:56 (batch 5) | + strong-table route, size read, S11 fixes, twist play | 3aac34d | cbf2ccb3...95fa4803 | held-out night +0.096, mirror +0.241, every exploit cell up (heads-up vs exploiter 2 +0.30), wild/short deck/omaha/keep up |
| 2026-11-03 13:37 (batch 6) | + per-family twist dials, known opponent cards | 91014ae | a66eb4b3...d6666f77 | twist tables only: exposed card +0.22, knockout bounty +0.11, bounty-aware +0.03 (held-out H21); plain hold'em identical |
| 2026-11-04 08:40 (batch 7) | + heads-up specialist (gated), stab read, value of information, street-settled twin | 038c3f0 | 51c37f02...9848bdc4 | exploiter 2 heads-up +0.31, three-handed +0.09, exploiter 3 heads-up +0.10, auction +0.06, tranche +0.18 (H31); judges level; gate pass on plain, auction, bonus_card, tranche (load 4) |
| 2026-11-04 23:30 (batch 8) | + one stab size, solved three-handed button, big blind fold read | 77c5ea6 (merged eac472a) | 0d07654e...9372ba19 | H34: elite +0.08, mirror +0.09, elite_b +0.08, mirror_b +0.06, night_hard +0.04, exploit and adapt cells up to +0.19; ordinary rooms level; judges nothing down, five up; zip parity pass; gate pass |

Zips live in `frozen/` (git-ignored); each is rebuilt from its commit with `tools/pack.py --slim`.
