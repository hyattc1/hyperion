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
| 11:12-11:21 | climb_accept aware, `hero.twin_preflop` 0.05 (f7055fa) | 10000-10199 x 8 | section 3 |
| 11:22-11:35 | climb_accept aware, batch 2 (9410fbb): two-board margins, tiers and sizes; short deck twins; three_card_keep and Omaha call shifts; Omaha flats (the batch's last five, low-value, stopped) | 10000-10199 x 8 | section 3 |
| 11:24-11:28 | skill profiles, F on realistic under lowball and wild_deuces; F + twin_preflop on generic_aware under wild_deuces | 10000-10199 x 8 | section 1 |
| 11:30-12:08 | climb_accept batch 3 (d3feb02): short-deck flats and 3-bets by the deck gate; variants stage for twin_preflop on the six entries it can reach; lowball flats | 10000-10199 x 8 | section 3 |
| 11:35-11:52 | climb_accept batch 4 (4e46a71): label re-cut (twin_multi) on Omaha, three_card_keep, toss (generic and hand-built); with the call shifts | 10000-10199 x 8 | section 3 |
| 11:52-12:22 | climb_accept batch 6 (9776488): blind-discard re-cut, wild shove calls, Omaha and three_card_keep value shifts, short-deck tables / read / opens / 3-bets, Omaha wide flats, two-board margin 0.30 and shove calls | 10000-10199 x 8 | section 3 |
| 12:07-12:12 | climb_accept batch 5 (9776488): wild call shift 1, three_card_keep shift 3 (its last four screens stopped) | 10000-10199 x 8 | section 3 |
| 12:12-12:22 | climb_accept batch 7 (9776488): lowball flats on realistic, alone and with the twins | 10000-10199 x 8 | section 3 |
| 12:22-12:27 | climb_accept batch 8 (9776488): wild call shift 2, short-deck call shift (the latter not reached before the final screens) | 10000-10199 x 8 | section 3 |
| 12:22- | the candidate's screens (9776488): aware generic (9 entries) and hand-built (4 fields), confirm (night, 200 seeds), guards (50 seeds), variants (the 10 entries a dial reaches at 200 seeds, the other 16 at 50), latency, every seat's points (aware_board) | 10000-10199 x 8 / 10000-10049 x 8 | section 5 |
| 12:27-12:48 | full suite on the branch | - | section 6 |
| 13:17-13:34 | the failed tests alone, on the branch and at 8286990 | - | section 6 |
| 14:11-14:17 | auction's parts apart (9776488): the call shift alone, the twins alone | 10000-10199 x 8 | section 5b |
| 14:15-14:35 | the candidate at d761587 on the cells the last changes reach; aware_board margins for five entries | 10000-10199 x 8 | sections 5, 5b |
| 14:35-14:41 | full suite at d761587 | - | section 6 |
| 14:36-14:47 | the candidate with the short-deck shift on its three short-deck cells; the shift at 2 alone; aware_board short_deck | 10000-10199 x 8 | section 5b |

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
| two_boards | `variant_preflop_ex` boards {shove_eq_margin -0.03} | 6.092 | 6.040 | -0.052 ± 0.037 | DOWN |
| wild_deuces | `twin_preflop` + `call_shift_ex` {wild 2} | 6.056 | 7.001 | +0.944 ± 0.132 | UP |
| short_deck | `call_shift_ex` {deck 1} | 5.810 | 6.044 | **+0.233 ± 0.081** | UP |
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
     "hero.mu_value_shift": 1, "hero.call_shift_ex": {"wild": 2, "deck": 1}}

at d761587. Section 5's full screens ran at 9776488 with `call_shift_ex` {"wild": 1}; the three later changes (the
wild shift 1 -> 2, acting on wild-card tables only; the short-deck shift, acting on tables with removed ranks only; and
multi/mu shifts on dealt hole cards only, acting on bonus_card and auction only) were measured again at d761587 on
every cell they reach (section 5b). The short-deck shift's screen (batch 8, 12:31) was read late, after the final
screens had started; hence the separate pass.

Where each part acts (every one twist-gated, so plain hold'em is identical by construction; section 5 checks it):
`twin_preflop` on the two-card twists whose prepared table moves the twins by 0.05 or more and that have no variant
set: lowball, wild_deuces, hi_lo, swap_one_turn, bonus_card, auction (the last three are core tables, where only the
sections routed to Hero read it); `twin_multi` on the label tables whose re-cut moves labels by 0.07 or more: Omaha
(0.17), toss_or_holdem and three_card_blind_discard (0.08), not three_card_keep (0.06, where it was level);
`multi_call_shift` on three_card_keep (any twist that deals three or more hole cards and leaves them in the hand
after the flop; since d761587 not a third card bought at bonus_card or auction, section 5b);
`mu_call_shift` / `mu_value_shift` on Omaha (any must-use-k); `call_shift_ex` on wild cards (two tiers) and on a
short deck (one tier: any twist that removes ranks).

Left out: the lowball flats (`variant_preflop_ex` lowball {call_raise_frac 0.15, three_bet_frac 0.05}: +0.23 on the
generic field alone and +0.40 with the twins, but against the twist-blind field level alone on screen seeds (V-b
measured the same parameters -0.062 ± 0.047 on held-out H1) and -0.073 ± 0.058 DOWN with the twins: the night's
field plays the twist, the acceptance rule counts the realistic cell too, so it is reported, not shipped); `multi_call_shift` 3 (level with 2); `multi_value_shift` (no gain);
`twin_force` and every short-deck and two-board dial (level, or down).

## 5. The candidate's screens (9776488, screen seeds 10000-10199 x 8, paired against F `{"dials": {}}`)

**aware, generic field** (`--aware generic:...`):

| variant | F | candidate | candidate - F | |
|---|---|---|---|---|
| wild_deuces | 6.056 | 6.921 | +0.865 ± 0.123 | UP |
| omaha_four | 6.081 | 6.529 | +0.448 ± 0.129 | UP |
| three_card_keep | 5.874 | 6.212 | +0.338 ± 0.100 | UP |
| hi_lo | 6.046 | 6.165 | +0.119 ± 0.116 | UP |
| toss_or_holdem | 6.396 | 6.470 | +0.074 ± 0.069 | UP |
| three_card_blind_discard | 6.299 | 6.350 | +0.052 ± 0.080 | level |
| lowball | 6.883 | 6.906 | +0.022 ± 0.094 | level |
| short_deck | 5.810 | 5.810 | +0.000 ± 0.000 | identical |
| two_boards | 6.092 | 6.092 | +0.000 ± 0.000 | identical |

These are F's own points (climb_accept records the hero seat only). On V-d's board F's margin over the best opponent
there was +0.20 (wild_deuces), +0.45 (Omaha), +0.50 (three_card_keep), +0.50 (hi_lo, rival 1); the opponents' points
move a little when F's play changes, so the new margins are not these sums exactly.

**aware, hand-built fields**: short_deck_aware 5.953 -> 5.953 (identical), toss_or_holdem_aware 6.328 -> 6.360
(+0.032 ± 0.062, level), bounty_aware 6.260 -> 6.260 (identical), river_of_blood_aware 6.231 -> 6.231 (identical).

**confirm, guards** (plain hold'em; every dial is twist-gated): night 5.968 -> 5.968 on all 200 seeds, identical per
seed. The guards at seeds 10000-10049 x 8 (the 200-seed run was stopped at night_hard's first chunk to save an hour;
identical per-seed samples are the proof, as V-d's 40-seed check): night_hard 5.597, realistic 6.167, top 5.134, night
at 10/7/5/4/3/2/1/0 6.219, at 50/25/12/6/3/2/1/1 25.365, night with doubling blinds 5.850: every cell +0.000 ± 0.000,
identical per seed; 0 timeouts, 0 errors.

**variants** (`realistic`, twist-blind; the ten entries a dial reaches at 200 seeds):

| entry | F | candidate | candidate - F | |
|---|---|---|---|---|
| wild_deuces | 6.962 | 7.353 | +0.391 ± 0.114 | UP |
| three_card_keep | 6.168 | 6.425 | +0.258 ± 0.075 | UP |
| bonus_card | 5.973 | 6.137 | +0.164 ± 0.107 | UP |
| omaha_four | 6.665 | 6.826 | +0.161 ± 0.080 | UP |
| three_card_blind_discard | 6.377 | 6.434 | +0.057 ± 0.058 | level |
| hi_lo | 6.126 | 6.166 | +0.040 ± 0.109 | level |
| toss_or_holdem | 6.460 | 6.497 | +0.037 ± 0.057 | level |
| lowball | 7.785 | 7.796 | +0.011 ± 0.047 | level |
| swap_one_turn | 6.445 | 6.440 | -0.004 ± 0.040 | level |
| auction | 6.534 | 6.517 | -0.017 ± 0.094 | level |

The other sixteen at seeds 10000-10049 x 8 (no dial reaches them): permuted_ranks, short_deck, flush_over_full_house,
swap_holdem, exposed_card, two_boards, deal5_keep2, bounty, knockout_bounty, top_heavy, pot_limit, antes_from_level_3,
fixed_raise, fast_schedule, straddle, river_of_blood: every one +0.000 ± 0.000, identical per seed.

bonus_card and auction move with more than the twins (twins alone: +0.008, -0.003): a bought third card leaves three
hole cards after the flop, so `multi_call_shift` reaches them. Against the generic field: bonus_card 6.066 -> 6.182
(+0.117 ± 0.112, UP), auction 6.387 -> 6.299 (-0.088 ± 0.099, level, leaning down; section 5b).

**latency** (`tools/latency.py --hand-end --reps 3 --variant V`, 20 recorded tables, per-call minimum over the three
replays, µs; F = `{}`, candidate = the dials above with the wild call shift at 1, 9776488; the later two changes add no
work to a decision). Host load 12-14.

| variant | hand_end p99 F / cand | act p99 F / cand | first act p99 F / cand |
|---|---|---|---|
| short_deck | 100.9 / 102.0 | 70.0 / 71.8 | 103.5 / 92.3 |
| omaha_four | 99.0 / 97.9 | 100.2 / 99.0 | 103.4 / 99.2 |
| two_boards | 91.1 / 96.3 | 72.7 / 75.1 | 88.7 / 86.7 |
| wild_deuces | 90.1 / 93.4 | 112.9 / 121.7 | 92.3 / 96.2 |
| lowball | 93.5 / 90.5 | 66.7 / 62.5 | 86.7 / 77.0 |
| three_card_keep | 99.9 / 103.3 | 80.1 / 88.4 | 99.4 / 109.1 |
| hi_lo | 94.8 / 95.4 | 72.9 / 73.3 | 99.3 / 97.1 |
| toss_or_holdem | 96.5 / 100.1 | 71.3 / 71.1 | 113.5 / 107.3 |
| auction | 97.7 / 98.8 | 95.8 / 96.6 | 131.6 / 147.2 |

Every p99 near 0.1 ms, the candidate level with F within the host's noise: the dials change which numbers a decision
reads, not how many. The one new cost is at a table start, once per process: reading the prepared table, 1.5 ms for a
two-card twist's twins, 5 ms for Omaha's re-cut (2 ms the file, 3 ms the re-cut), beside the variant set's own load.

### 5b. Auction, and the three last changes

Auction (5%) against the generic field, the parts apart (9776488): the candidate -0.088 ± 0.099, `multi_call_shift` 2
alone -0.073 ± 0.098, the twins alone +0.005 ± 0.034. A bought third card is not a dealt one (the hand was chosen as two
and the third is a price paid on the flop), so d761587 keeps the multi / mu shifts to tables that deal three or more
hole cards (Rules.hole_cards >= 3). That gives back bonus_card's gain (+0.12 generic, +0.16 realistic) to keep
auction level; at 2% against 5%, and with the acceptance rule counting every cell, auction decides.

The wild shift at 2 against 1, paired (9776488, generic wild_deuces): +0.080 ± 0.067; with the whole candidate,
wild_deuces generic 6.056 -> 7.001 (+0.944 ± 0.132), realistic 6.962 -> 7.422 (+0.460 ± 0.115).

**Margins over the best opponent** with the final candidate in Hero's seat (`tools/aware_board.py --fields
generic_aware --spec <the candidate>`, d761587, seeds 10000-10199 x 8; the short-deck row with the short-deck shift, the
other five rows ran before it was added and are unchanged by it), against V-d's board for F as shipped (the same
seeds and field):

| variant | F (V-d) | margin (V-d) | candidate | margin now |
|---|---|---|---|---|
| short_deck | 5.810 | +0.280 ± 0.127 (gen_tag) | 6.044 | **+0.545 ± 0.116** (gen_tag) |
| wild_deuces | 6.056 | +0.200 ± 0.160 (gen_tag) | 7.001 | **+1.363 ± 0.128** (gen_tag) |
| omaha_four | 6.081 | +0.453 ± 0.138 (gen_tag) | 6.529 | **+1.036 ± 0.127** (gen_tag) |
| three_card_keep | 5.874 | +0.501 ± 0.136 (gen_tag) | 6.212 | **+0.964 ± 0.134** (gen_tag) |
| hi_lo | 6.046 | +0.501 ± 0.184 (rival1) | 6.165 | +0.655 ± 0.170 (rival1) |
| toss_or_holdem | 6.284 | +1.026 ± 0.149 (rival1) | 6.470 | +1.188 ± 0.135 (rival1) |

(toss_or_holdem's F on V-d's board, 6.284, differs from F's 6.396 in my cells: V-d's board ran at c73a229, before batch
4 (e3cec13) put `hero.toss_call_shift` in SHIP_DIALS; on the other four entries F's numbers agree to the third decimal.)

**The final candidate at d761587**, every cell the two last changes reach (climb_accept, 200 x 8; F's base cells
copied from 9776488 with each cell's first chunk replayed: identical):

| cell | F | candidate | candidate - F | |
|---|---|---|---|---|
| wild_deuces (generic_aware) | 6.056 | 7.001 | +0.944 ± 0.132 | UP |
| wild_deuces (realistic) | 6.962 | 7.422 | +0.460 ± 0.115 | UP |
| auction (generic_aware) | 6.387 | 6.392 | +0.005 ± 0.034 | level |
| auction (realistic) | 6.534 | 6.531 | -0.003 ± 0.025 | level |
| bonus_card (generic_aware) | 6.066 | 6.058 | -0.008 ± 0.031 | level |
| bonus_card (realistic) | 5.973 | 5.980 | +0.008 ± 0.028 | level |
| omaha_four (generic_aware) | 6.081 | 6.529 | +0.448 ± 0.129 | UP |
| three_card_keep (generic_aware) | 5.874 | 6.212 | +0.338 ± 0.100 | UP |

With the short-deck shift (the candidate above), every cell the deck gate reaches:

| cell | F | candidate | candidate - F | |
|---|---|---|---|---|
| short_deck (generic_aware) | 5.810 | 6.044 | +0.233 ± 0.081 | UP |
| short_deck (short_deck_aware, hand-built) | 5.953 | 6.188 | +0.235 ± 0.077 | UP |
| short_deck (realistic) | 6.164 | 6.362 | +0.198 ± 0.065 | UP |

(The shift at 2 alone: +0.297 ± 0.098 on the generic field, +0.064 ± 0.066 over the shift at 1, paired: level, so 1.)
Facing a bet on a short deck, the made hand reads one tier lower: pairs and two pairs are worth less where every hand
holds 6 to ace (V-b's `short_deck_read` corrected the outs and straights, and changed nothing; the price of a made hand
was the lever).

Omaha and three_card_keep at d761587 are identical per seed to section 5's candidate at 9776488, and wild_deuces
(generic) identical per seed to 9776488's candidate with the wild shift at 2: the changes reach only the cells they
should. Every other cell of section 5 holds for the final candidate unchanged (neither change reaches it).

## 6. Tests

- tests/test_ve_dials.py (9 tests): every new key off by default; twins from the prepared tables (lowball, wild deuces,
  hold'em cards give the classes themselves, plain hold'em names none); twin_preflop replaces the mirror and wild maps
  only when on, never under the threshold, on a variant set, a rank remap or plain hold'em; twin_force; the Omaha
  re-cut (shift, monotone equity columns, the threshold); split_call_margin and split_tier_eq on two boards only;
  variant_preflop_ex and call_shift_ex by gate; multi/mu call and value shifts reach their tables only.
  tests/test_nightof_pack.py: the package carries the variant's prepared table (expectation updated: a bounty package
  now has tables/generic/bounty-*.json).
- docs/packet/CONTRACTS.md regenerated (tools/apicard.py: the new Hero keys).
- Full suite on the branch (9776488's code, the candidate's), host load 12-15 with my two measurement processes and other workers':
  **1156 passed, 23 failed, 15 skipped** (20.7 min). Rerun alone: 14 pass. The 9 still failing (test_drills_run
  toss_or_holdem-c, test_gate history-dropping package, test_hand_end_interrupt idle, test_nightof_latency kit D round
  trip, the model-mode replay tests in test_sim_exploiter and test_sim_outside) **fail the same way at the base commit
  8286990** run alone at the same load (9 failed): wall-clock budgets and replays that follow the wall clock, as V-d
  found. None involves a V-e dial (all off in those tests).
- Full suite at d761587 (the candidate's final code), host load 8-10: **1189 passed, 4 failed, 1 skipped** (5 min).
  Rerun alone: test_sim_bestiary's budget test for f_copy and test_slowbox's panic test pass; the two
  test_nightof_latency kit round trips fail the same way at 8286990 (a gen-2 garbage collection inside one of 100
  adapter calls, 4.5 ms, makes the p99).

## 7. Summary per target variant

| variant (likelihood) | diagnosis | change | generic aware cell | margin over best opponent |
|---|---|---|---|---|
| short_deck (7%) | no preflop line loses; facing bets F prices pairs and two pairs as in hold'em, where every hand holds 6 to ace (flop tier-4 stack-offs win 41%) | facing a bet one tier lower (`call_shift_ex` deck); twins, flats, 3-bets, opens, v2 tables, the short-deck read all level | **+0.233 ± 0.081** (hand-built +0.235, realistic +0.198) | +0.28 -> **+0.55** |
| omaha_four (5%) | the catalog label set (300 hands a label) mis-orders hands; big calls with top pair / overpair facing bets lose (river tier-4 calls win 7%); flop raises with sets and straights bust | label tables re-cut from the prepared table; facing a bet one tier lower; bets and raises one tier higher | **+0.448 ± 0.129** | +0.45 -> **+1.04** |
| two_boards (5%) | F trails the generic bots in every postflop section, descriptively; its calls beat folding on average | none kept (margins, tiers, sizes, flats, shove calls: level or down) | +0.000 | +0.51 (unchanged) |
| three_card_keep (3%) | postflop calls facing bets: F continues 52%, 248 busts | facing a bet two tiers lower | **+0.338 ± 0.100** | +0.50 -> **+0.96** |
| wild_deuces (2.5%) | `wild_map` reads AA as a premium and deuce hands as small pairs; F's all-in calls and re-raises meet the generic seats' deuce hands | twins from the prepared table; facing a bet two tiers lower | **+0.944 ± 0.132** | +0.20 -> **+1.36** |
| lowball (1.5%) | the shrink is the opponents (realistic seats pay off with hold'em's strong hands); no F section loses | twins (level); the flats help here (+0.23 / +0.40) but are down on realistic, left out | +0.022 ± 0.094 | +0.86 (about) |
| hi_lo (1.5%) | Hero plays high only; hold'em's order | twins from the prepared table | **+0.119 ± 0.116** | +0.50 -> +0.66 |
| toss_or_holdem (11%, not a target) | the catalog toss set scores a perfect hindsight toss | label tables re-cut | **+0.074 ± 0.069** | +1.03 -> +1.19 |

Likelihood-weighted, the candidate adds about +0.08 points a table on the night's expected twist against twist-reading
opponents (short deck 0.07 x 0.23, wild 0.025 x 0.94, Omaha 0.05 x 0.45, three_card_keep 0.03 x 0.34, hi-lo 0.015 x
0.12, toss 0.11 x 0.07), and nothing on plain hold'em.
## What remains

- **short_deck** (7%): the facing-bet shift is the one lever found (+0.23); every preflop dial was level. The shift at
  2 may be a little better (+0.06 over 1, inside noise). F's margin over gen_tag is +0.55 with it.
- **two_boards** (5%): F trails the generic bots in every postflop section by the profile, but no postflop dial
  moved points: call margins 0.30 / 0.10 / 0.05, tier from the mean, full bet sizes, flats, shove-call margins.
  The best opponent there is rival 1 (blind).
- **hi_lo**: Hero still plays high only (no low read); the twins gave +0.12.
- **lowball**: nothing to fix found; the shrink is the opponents.
- **A postflop read dealt through the variant's hooks** (the generic bots' made share) is not built for F: a showdown
  score costs 9 us (lowball) to 120 us (wild deuces) in Python, 48 of them do not fit F's budget; F's tier reads for
  the catalogued showdowns hold up in the recordings (every final call beats folding on average).
- **On the night**: twin_preflop and twin_multi read tables/generic/<variant>-*.json; prepare the twist's table
  before packing (PLAYBOOK Stage 5's `--aware generic:<variant>` builds it; tools/pack.py now carries it). Without the
  file both dials do nothing.
