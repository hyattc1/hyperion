# V-e: F's strength under the twists, against opponents that play them (2026-11-02)

Branch climb/ve-variant-strength, from main 8286990. Track V of the climb. Targets from V-d's honest board
(docs/drills/climb/vd-log.md section 7): F's margin over the best opponent shrinks on lowball, wild_deuces and
short_deck once the opponents read the twist, and is about +0.5 on omaha_four, two_boards, three_card_keep and hi_lo.
Screen seeds only (10000-10199 for decisions; fresh diagnostic seeds 9000-9059, never used before, for the
recordings). No held-out seed, held-out variant, judge bot or judge field was used, read or tuned on. Host shared
(load 9-12 of 8 cores): every measurement `nice -n 10`, two workers, at most two measurement processes at once, each
from a detached worktree at a fixed commit (scratchpad `goal/ve_m*`). Scratch scripts live in the session scratchpad
(`goal/ve/scripts/`), not in the repo.

## Runs (in order)

| time | run | seeds | result |
|---|---|---|---|
| 10:59-11:22 | skill profiles, generic_aware@{ship, gen_tag, gen_mc, gen_pushfold} under lowball, wild_deuces, short_deck, omaha_four, two_boards, three_card_keep, hi_lo (base worktree 8286990) | 10000-10199 x 8 | section 1 |
| 11:05-11:12 | decision recordings, F in Hero's seat of generic_aware (scratch `diag.py`), five targets | 9000-9059 x 8 | section 1 |
| 11:12-11:21 | climb_accept aware, `hero.twin_preflop` 0.05 (f7055fa) | 10000-10199 x 8 | section 2 |
| 11:22-11:35 | climb_accept aware, batch 2 (9410fbb): two-board margins, tiers and sizes; short deck twins; three_card_keep and Omaha call shifts; Omaha flats (the batch's last four, low-value, stopped) | 10000-10199 x 8 | section 2 |
| 11:24-11:28 | skill profiles, F on realistic under lowball and wild_deuces; F + twin_preflop on generic_aware under wild_deuces | 10000-10199 x 8 | section 1 |
| 11:30- | climb_accept batch 3 (d3feb02): short-deck flats and 3-bets by the deck gate; variants stage for twin_preflop on the six entries it can reach; lowball flats | 10000-10199 x 8 | section 2 |
| 11:35- | climb_accept batch 4 (4e46a71): label re-cut (twin_multi) on Omaha, three_card_keep, toss; with the call shifts | 10000-10199 x 8 | section 2 |

## 1. Where F stands against the generic aware field (F as shipped, 8286990)

`tools/skill_profile.py run --field generic_aware --variant V --bots ship,gen_tag,gen_mc,gen_pushfold` (each bot in
Hero's seat of the same deals, seeds 10000-10199 x 8). Points, share of first places, bust rate:

| variant | F | 1st / bust | gen_tag | gen_mc | gen_pushfold | F's weakest sections (F's bb a decision vs the generic bots', busts) |
|---|---|---|---|---|---|---|
| lowball | 6.88 | 74% / 25% | 5.77 | 5.89 | 5.82 | none negative; busts from postflop value raises and calls (post_hu_bet 187 of ~400) |
| wild_deuces | 6.06 | 58% / 40% | 5.79 | 5.54 | 5.72 | pre_allin +0.07 (calls 35%) vs +0.48/+0.51 (calls 9%); pre_raised_deep 107 busts (raises 17%); pre_raised_short 77 busts |
| short_deck | 5.81 | 34% / 62% | 5.47 | 5.19 | 5.40 | pre_raised_deep +0.05 vs +0.10/+0.20; pre_allin +0.03 vs +0.18/+0.47; post_hu_bet +1.34 vs +1.91 (gen_tag) |
| omaha_four | 6.08 | 53% / 45% | 5.46 | 5.25 | 5.37 | pre_raised_deep: F flats 34% of raises (vpip 39%, raise 5%), +0.03 vs +0.17/+0.30, 102 busts; pre_allin +0.03 vs +0.26/+0.42 |
| two_boards | 6.09 | 42% / 43% | 4.89 | 4.71 | 4.93 | every postflop section: post_hu_bet +0.53 (never raises) vs +1.31 (gen_tag); post_hu_chk +0.43 vs +1.08; post_mw +0.17 vs +1.20 |
| three_card_keep | 5.87 | 44% / 52% | 5.40 | 5.12 | 5.36 | post_hu_bet: F continues 52%, +1.58, 248 busts vs gen_tag 35%, +2.57; pre_allin +0.19 vs +0.42/+0.57 |
| hi_lo | 6.04 | 47% / 46% | 4.98 | 4.63 | | none below the generic bots (the best opponent there is rival 1, blind) |

The recordings (F's every decision with the hand's result, 60 seeds x 8 per variant, scratch `diag.py`, `ana_*.py`)
say which of these are leaks and which are only descriptive:

- **wild_deuces, preflop.** Hero reads a deuce with x as the pair xx and AA as AA (`wild_map`). In the variant's own
  table (tables/generic/wild_deuces, dealt and scored through the hooks) 22 wins 0.99 of the pot against a random
  hand, every deuce hand is in the top 15% of combos, and AA (0.71) is a mid hand at the 16th percentile; 32o (0.84)
  is read as 33 (hold'em rank 0.63). F calls 35% of all-ins and loses chips there (-1,206 bb over 1,728 hands that
  ended preflop facing an all-in; the `call` line alone -494 bb, 13 busts); its re-raises over raises bust 107 times.
- **two_boards, postflop.** Facing a bet F folds 75% / 70% / 66% on flop / turn / river, and its calls are worth
  +5.9 / +15.4 / +20.3 bb each over folding (hand net plus the chips already in), winning 85-89% of their showdowns.
  The equity proxy there is the mean of the two boards' proxies and the call margin is F's 0.20; value bets need the
  weaker board's tier (`tier = min`) and every size is halved.
- **short_deck, omaha_four, lowball: the river and turn calls are not the leak.** Final calls (the hand's last
  decision a call, then showdown) are worth more than folding at every tier: short-deck river calls of tier 4 win
  52% at a price of 0.26. The losing hands' net is the chips put in on earlier streets.
- **omaha_four, preflop.** `hero.variant_preflop` (vb's tighter flats) is off on must-use tables because it measured
  -0.065 on the twist-blind field; against the generic aware field F flats 34% of deep raises at +0.03 bb a decision.
- **lowball.** F wins chips in every section and is first in 74% of tables; nothing the recordings show loses.

**Why F's lead collapses on lowball** (F's own profile, the same 200 seeds, twist-blind `realistic` against
`generic_aware`): F 7.79 -> 6.88 points, first 95% -> 74%, busts 5% -> 25%. F's chips per table fall in the
sections where the opponents put money in: facing a raise deep +43.4 -> +17.1 bb, postflop facing a bet +69.6 -> +22.3
(busts there 18 -> 187), nothing to call +67.4 -> +36.5, facing an all-in +8.4 -> +2.4. On realistic the TAG,
push/fold and Monte Carlo seats raise, bet and call with hold'em's strong hands (AA, sets, flushes), which lose at
2-7, and pay F off; the generic seats raise with real lows and stop paying. F's own decisions show no loss there
(every postflop line and every big value raise is worth more than folding or checking: river value raises of a
7-low win 78% of their showdowns), and reading each hand through the variant's own table instead of the mirror map
changes nothing (section 2). So most of lowball's shrink is the opponents, not a leak of F's.

**Why F's lead collapses on wild_deuces** (the same comparison): F 6.96 -> 6.06, first 79% -> 58%, busts 21% -> 40%.
Facing a raise deep +44.6 -> +13.4 bb a table (busts 73 -> 121), facing an all-in +7.8 -> +0.5 (busts 18 -> 62),
facing a raise short (busts 27 -> 91), postflop facing a bet +37.4 -> +15.8. Here part of it is F's own misread:
the twist-blind seats raise with AA and KK and fold deuces, so `wild_map` (a deuce with x is the pair xx, AA is AA)
cost F nothing there; the generic seats raise and shove with the deuce hands, and F's AA, KK and 3-bets meet them.
Reading each hand through the variant's own table (section 2) wins back most of it (+0.68).

## 2. The dials (all off by default; F's play with every one off is unchanged)

- **`hero.twin_preflop`** (float, 0 = off): on a two-card twist with no variant table set, Hero reads each hand as
  its hold'em twin: the hold'em class at the same combo percentile, the variant's classes ordered by their value
  share in the variant's own prepared table (tables/generic/<name>-<hash>.json, written by hyperion/sim/generic.py's
  `prepare` through the variant's hooks; `tables.generic_doc`, `tables.twin_classes`: the same rule as the generic
  bots' twins). It replaces the hand-written lowball mirror and wild map, and gives hi-lo (and any new showdown) an
  order of its own. Used when the twins move hands by at least the dial's value (`tables.twin_shift`, the
  combo-weighted mean |rank(twin) - rank(class)|): sampling noise in a prepared table of a twist that keeps
  hold'em's showdown moves them 0.015-0.03 (bounty, exposed, two boards, swaps, river of blood), lowball 0.50, wild
  deuces 0.21, hi-lo 0.10, swap_one_turn / bonus_card / auction 0.08 (core tables: rival 3's core plays their
  preflop). Not on a rank remap (permuted ranks: Hero remaps first). `hero.twin_force`: also where a two-card set
  exists (short deck). The twin maps are read once per process (~1.5 ms, at a table start). tools/pack.py now carries
  tables/generic/<variant>-*.json for the rules' variant, so the package has what the dial reads; on the night the
  twist's table must be prepared before packing (PLAYBOOK Stage 5's `--aware generic:<variant>` builds it).
- **`hero.twin_multi`** (float, 0 = off): a 3- or 4-card twist's label tables re-cut from its prepared table
  (`tables.recut_label_tables`): rank by the prepared value share, equity vs n opponents the set's own distribution
  at that rank (monotone, so one noisy label no longer moves its own number). The catalog's Omaha set was built at 300
  hands a label (quad deuces at equity 0.05, AQs+hh above most aces; its order agrees with the prepared table's,
  321,400 hands, at Spearman 0.62); mean |rank change| Omaha 0.17, toss and blind discard 0.08, three_card_keep 0.06.
- **`hero.multi_call_shift`, `hero.mu_call_shift`** (int, 0 = off): facing a bet with three or more hole cards still
  held (three_card_keep: all kept; Omaha: must use two), the made hand's equity read that many tiers lower (the call
  side of `keep_call_shift` / `toss_call_shift`: every hand at the table is stronger). Reaches any new twist that
  deals more hole cards.
- **`hero.variant_preflop_ex`** (dict) and **`hero.call_shift_ex`** (dict): PreflopParams overrides and facing-bet
  tier shifts by the twist table's rule ("must_use", "fixedlimit", "lowball": the tables `variant_preflop` leaves
  out; "deck", "boards", "wild": on top of it), the first rule that applies.
- **`hero.postflop.split_call_margin`**, **`hero.postflop.split_tier_eq`**: two boards' call margin, and value / raise
  thresholds read from the mean of the two boards' proxies instead of the weaker board's tier.

## 3. Screens (climb_accept `--stages aware`, F + dial vs F, generic_aware under the variant, 200 x 8, paired)

F's base cells are computed once per code version; where a later batch's version differs only by dials that are off,
the earlier version's cells are copied over (scratch `copybase.py`) and the first chunk of each cell (seeds
10000-10024) is played again at the new version as the check: identical per-seed samples in every cell checked.

| variant | dial(s) | F | cand | cand - F | |
|---|---|---|---|---|---|
| wild_deuces | `twin_preflop` 0.05 | 6.056 | 6.737 | +0.681 ± 0.127 | UP |
| lowball | `twin_preflop` 0.05 | 6.883 | 6.906 | +0.022 ± 0.094 | level |
| hi_lo | `twin_preflop` 0.05 | 6.046 | 6.165 | +0.119 ± 0.116 | UP |
| two_boards | `postflop.split_call_margin` 0.10 / 0.05 | 6.092 | 6.111 / 6.022 | +0.018 ± 0.082 / -0.071 ± 0.097 | level |
| two_boards | `postflop.split_tier_eq` | 6.092 | 6.126 | +0.034 ± 0.061 | level |
| two_boards | `postflop.two_boards_size_mult` 1.0 | 6.092 | 6.112 | +0.020 ± 0.062 | level |
| short_deck | `twin_preflop` 0.05 + `twin_force` | 5.810 | 5.853 | +0.043 ± 0.079 | level |
| short_deck | `variant_preflop_ex` deck call_raise_frac 0.25 / 0.10 | 5.810 | 5.753 / 5.850 | -0.057 ± 0.069 / +0.040 ± 0.059 | level |
| three_card_keep | `multi_call_shift` 1 / 2 | 5.874 | 6.129 / 6.212 | +0.255 ± 0.093 / +0.338 ± 0.100 | UP / UP |
| three_card_keep | `twin_multi` 0.05 | 5.874 | 5.845 | -0.028 ± 0.089 | level |
| omaha_four | `mu_call_shift` 1 / 2 | 6.081 | 6.215 / 6.203 | +0.134 ± 0.091 / +0.122 ± 0.101 | UP / UP |
| omaha_four | `twin_multi` 0.05 | 6.081 | 6.173 | +0.092 ± 0.112 | level |
| omaha_four | `variant_preflop_ex` must_use {call_raise_frac 0.15, three_bet_frac 0.05} | 6.081 | 6.064 | -0.017 ± 0.086 | level |
| omaha_four | `variant_preflop_ex` must_use {call_raise_frac 0.6} (wider flats) | 6.081 | 6.085 | +0.005 ± 0.065 | level |
| omaha_four | `twin_multi` 0.05 + `mu_call_shift` 1 | 6.081 | 6.272 | +0.192 ± 0.123 | UP |
| omaha_four | `mu_call_shift` 1 + `mu_value_shift` 1 | 6.081 | 6.346 | +0.265 ± 0.110 | UP |
| three_card_keep | `multi_call_shift` 3 | 5.874 | 6.223 | +0.349 ± 0.101 | UP |
| three_card_keep | `twin_multi` 0.05 + `multi_call_shift` 1 | 5.874 | 6.152 | +0.278 ± 0.109 | UP |
| three_card_keep | `multi_call_shift` 2 + `multi_value_shift` 1 | 5.874 | 6.198 | +0.325 ± 0.105 | UP |
| toss_or_holdem | `twin_multi` 0.05 | 6.396 | 6.470 | +0.074 ± 0.069 | UP |
| toss_or_holdem (toss_or_holdem_aware, hand-built) | `twin_multi` 0.05 | 6.328 | 6.360 | +0.032 ± 0.062 | level |
| three_card_blind_discard | `twin_multi` 0.07 | 6.299 | 6.350 | +0.052 ± 0.080 | level |
| wild_deuces | `twin_preflop` + `variant_preflop_ex` wild {shove_eq_margin 0.06} | 6.056 | 6.729 | +0.673 ± 0.127 | UP (= twins alone) |
| wild_deuces | `twin_preflop` + `call_shift_ex` {wild 1} | 6.056 | 6.921 | +0.865 ± 0.123 | UP |
| lowball | `variant_preflop_ex` lowball {call_raise_frac 0.15, three_bet_frac 0.05} | 6.883 | 7.117 | +0.233 ± 0.102 | UP |
| lowball (realistic, twist-blind) | the same | 7.785 | 7.783 | -0.002 ± 0.053 | level (V-b: -0.062 ± 0.047 on held-out H1) |
| short_deck | `variant_preflop_ex` deck {three_bet_frac 0.08} / {open_frac_mult 0.75} | 5.810 | 5.806 / 5.820 | -0.005 ± 0.061 / +0.009 ± 0.067 | level |
| short_deck | `variant_tables` short_deck_v2 / `short_deck_read` | 5.810 | 5.844 / 5.780 | +0.033 ± 0.064 / -0.031 ± 0.038 | level |
| two_boards | `postflop.split_call_margin` 0.30 | 6.092 | 5.932 | -0.160 ± 0.078 | DOWN |
| two_boards | `variant_preflop_ex` boards {shove_eq_margin 0.08} | 6.092 | 6.089 | -0.003 ± 0.031 | level |
| short_deck | `variant_preflop_ex` deck {three_bet_frac 0.03} | 5.810 | 5.773 | -0.037 ± 0.053 | level |
| lowball | `twin_preflop` + lowball flats {call_raise_frac 0.15, three_bet_frac 0.05} | 6.883 | 7.281 | +0.398 ± 0.103 | UP |
| lowball (realistic, twist-blind) | the same | 7.785 | 7.712 | -0.073 ± 0.058 | DOWN |

The variants stage for `twin_preflop` 0.05 on the six entries it reaches (`realistic`, twist-blind, 200 x 8): wild_deuces
+0.341 ± 0.106 UP, hi_lo +0.040 ± 0.109, lowball +0.011 ± 0.047, swap_one_turn -0.004 ± 0.040, bonus_card +0.008 ±
0.028, auction -0.003 ± 0.025 (all level). Two boards' call margin is near its best at F's 0.20 (0.05 -0.07, 0.10
+0.02, 0.30 -0.16).

Why the label re-cut helps toss: the catalog's toss set (tools/gen_tables.py, 1,500 hands a label) scores each
three-card hand by its best two at showdown with the whole board seen (a perfect toss, `_KEEP`), which overvalues
hands whose third card is only good in hindsight; the prepared table tosses on the flop through the hook. Omaha's set
is noisy rather than biased (300 hands a label).

## 4. The candidate

    {"hero.twin_preflop": 0.05, "hero.twin_multi": 0.07, "hero.multi_call_shift": 2, "hero.mu_call_shift": 1,
     "hero.mu_value_shift": 1, "hero.call_shift_ex": {"wild": 1}}

Where each part acts (every one twist-gated, so plain hold'em is identical by construction; section 5 checks it):
`twin_preflop` on the two-card twists whose prepared table moves the twins by 0.05 or more and that have no variant
set: lowball, wild_deuces, hi_lo, swap_one_turn, bonus_card, auction (the last three are core tables, where only the
sections routed to Hero read it); `twin_multi` on the label tables whose re-cut moves labels by 0.07 or more: Omaha
(0.17), toss_or_holdem and three_card_blind_discard (0.08), not three_card_keep (0.06, where it was level);
`multi_call_shift` on three_card_keep (and any twist that keeps three or more hole cards to the river);
`mu_call_shift` / `mu_value_shift` on Omaha (any must-use-k); `call_shift_ex` wild on wild cards.

Left out: the lowball flats (`variant_preflop_ex` lowball {call_raise_frac 0.15, three_bet_frac 0.05}: +0.23 on the
generic field alone and +0.40 with the twins, but against the twist-blind field level alone on screen seeds (V-b
measured the same parameters -0.062 ± 0.047 on held-out H1) and -0.073 ± 0.058 DOWN with the twins: the night's
field plays the twist, the acceptance rule counts the realistic cell too, so it is reported, not shipped); `multi_call_shift` 3 (level with 2); `multi_value_shift` (no gain);
`twin_force` and every short-deck and two-board dial (level, or down).
