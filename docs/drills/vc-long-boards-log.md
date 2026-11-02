# vc-long-boards: river_of_blood in the catalog, boards past five, deal5_keep2 calls, short-deck shove calls (2026-11-02)

Branch `climb/vc-long-boards` from main ea4d36f. Track V of the climb (docs/drills/goal-plan.md, backlog V1 and V3;
drill 7's findings, docs/drills/prompt-drill-7.md). Every number is model mode, eight rotations per seed, screen seeds
10000-10199 (200 x 8) unless it says otherwise, F as hyperion.ship builds it (dials on top of SHIP_DIALS, through
`tools/climb_accept.py`; never tools/swap.py paired specs), at most two worker processes on a host at load 5-8 (other
workers running). Scratch scripts (probes, margins, twin checks, the run-bettor diagnostic) live in the session
scratchpad (`goal/vc/scripts/`), not in the repo.

Sections: 1 the promotion, 2 long boards in Hero's shell, 3 the aware opponents, 4 river_of_blood screens,
5 deal5_keep2, 6 short_deck, 7 the candidate, 8 timing, 9 checks, 10 next.

## 1. river_of_blood joins the catalog (b2bf939)

- `RiverOfBloodHooks`, `river_of_blood()`, the bots' evaluator guard (`install_eval_guard`, `EvaluatorLimit`, ...) move
  from hyperion/drills/variants_unseen.py to hyperion/drills/variants.py, unchanged; the entry is in `CATALOG` on the
  betting axis, so `catalog_names()` (26 entries), the climb's variants stage and tools/variant_matrix.py now cover it.
- The any-size evaluator `evaluate_many` moves to hyperion/core/eval.py (unchanged code; it never builds a table: rank
  counts and suit masks past 8 cards, `evaluate` up to 8). The engine's showdown still uses it.
- variants_unseen.py keeps the four other entries untouched (their code, rules and tests are as they were) and
  re-exports the moved names, so `U.RiverOfBloodHooks` / `U.evaluate_many` still resolve. `HELD_OUT` has four names.
  (Of the other four I read only the module docstring's one-line list, while editing the river_of_blood line out.)
- River of Blood's tests move to tests/test_river_of_blood.py (the spec numbers, the run streets, the guard), plus a
  conservation run and "evaluate_many never builds a table".
- Every catalog-wide test now plays it. The rival 2 hybrid (`hybrid`, not a ship or fallback bot) evaluates with
  core.eval past 8 cards, so under the guard it errors there and Hero answers (7 core errors in the test table): new
  HybridConfig dial `hero_on_long_board` (off) sends a board past five to Hero; the catalog test sets it for this
  entry. Rival 3's core (hybrid3_x, F's base) reads any length with its own evaluator and needs nothing.

## 2. Long boards in Hero's shell (698cfcb)

Before: Hero returned check-or-fold when hole + board > 8 (its guard against core.eval building a 9-card table, 3 s,
inside the call), so on a board of 7+ cards F checked or folded every decision, a made flush included; a 6-card board
(8 cards) was read as a river with no draws, and a red river was played as the last street.

`hero.long_board` (off by default): Hero's postflop read takes any board length.
- Evaluation: `core.eval.evaluate_many` past 8 cards (about 10-20 us at 9-14 cards; tested: no table past 8 is built
  in a decision). The 8-card table is warmed at table start already (`max_cards` returns 8 under `run_until_black`).
- The read (`Postflop.read(long=True, more=...)`): "playing the board" is checked against the board's own best five at
  any length (it was only checked on exactly five); flush and straight draws, and their outs, count while another
  card can come (`more`), not only before the river.
- The run: under `run_until_black` (rules.extras) a board of five or more whose last card is red means another card
  and round come. Such a street plays as a turn (`long_to_come` cards to come, default 1: the rule of 2 per out), and
  a board whose last card is black plays as the river (river margins, station river bets). This replaces drill 7's
  "river view" (a 5-card sub-board chosen so our best hand stays the same): the view showed the bot a river with the
  board's threats taken out (a four-flush or a fourth straight card not in the chosen five disappears) and cost
  C(n, 5) evaluations, about 110 us at 9 cards; the long read keeps the whole board's texture at one or two
  evaluations.
- `long_value_per_card`, `long_call_per_card` (0): value / raise thresholds up, and the made hand's equity facing a bet
  read lower, this many tiers per board card past five (everyone uses the extra cards).
- Plain hold'em boards are untouched with every long dial on (tested on three spots; section 7 has the full check).

Unit probe (tests/test_river_of_blood.py): Ah Jh on Kc 7d 3s 9h 4h Qh 8c facing a bet folds without the dial (path
`safe`) and raises with it (path `postflop.long`), also on a 12-card board.

Two more dials in the same commit, gated to their twists: `hero.keep_call_shift` (section 5) and
`hero.variant_pushfold` (section 6).

## 3. River of Blood-aware opponents and the field (a8b101a)

`hyperion/sim/aware.py`, registered in the bestiary, in `river_of_blood_aware` only (never a night pool; tested):
realistic with Hero's seat, the three aware bots in the seats of the honest Monte Carlo bot, the push/fold bot and the
TAG, and the rest as it was (montecarlo30 and rival 1 blind, loose_aggro, timeout_then_recover).

| bot | what it does with the twist |
|---|---|
| `rob_tag` | ChartTAG preflop and through the turn; from the river on, `rob_read`: any board length (evaluate_many), relative to the board's own best five: continue with two pair or better that uses a hole card and beats the board's category (top pair too on a five-card board; trips or better past six board cards), raise with a straight or better that beats it (not a straight on a four-flush board); while a red last card means another card, call half a pot or less with a flush draw or an open-ender |
| `rob_pushfold` | PushFoldBot preflop, the same read after the flop |
| `rob_mc` | the aware Monte Carlo bot (48 samples, at most three opponents) dealing the run in every sample (to five, then on while the last card is red, at most 8 more), scored with evaluate_many |

Their blind twins (ChartTAG, PushFoldBot) read hole + board with core.eval up to 8 cards, counting a pair or two pair
on the board as their own (so they bet and call with the board's hand), and check or fold past 8 cards; the blind
Monte Carlo bot hits the guard past 8 cards.

**Do they play the twist better than their twins?** One table with each aware bot and its twin (plus loose_aggro and
rival 1), river_of_blood, 400 seeds x 8 (10000-10399, scratch `twins2.py`; the twin of `rob_mc` is the same Monte
Carlo bot dealing a fixed five-card board with core.eval): rob_tag - tag **-0.035 +- 0.089**, rob_pushfold - pushfold
**+0.046 +- 0.092**, rob_mc - blind MC **-0.013 +- 0.086**. Level: as with toss_tag (vb-top-variants), the twist moves
few of these bots' decisions. Most of their pots end before the river, and a run street is reached in a few hands a
table. They are kept because they read every board correctly, which is the minimum a team that read the handout ships.

Tools: `tools/climb_accept.py --stages aware --aware river_of_blood_aware`; `--aware FIELD:VARIANT` runs any field
under any entry (used for `realistic_keep2:deal5_keep2`, section 5).

## 4. River of Blood: where F stood, and the long-board dials

**F as shipped on `river_of_blood_aware`** (every bot's points, F in Hero's seat, 200 x 8, F minus each paired per
seed, scratch `margins.py`): F 6.214; rival1 (blind) 5.263, **F - it +0.950 +- 0.174**; rob_tag 4.888, **+1.325 +-
0.139**; rob_pushfold 4.750, +1.463; rob_mc 4.482, +1.732; loose_aggro 4.296; timeout_then_recover 3.111; montecarlo30
2.996 (1,277 guard errors). F is first by nearly a point.

**How often a long board comes up** (probe, 25 seeds x 8, F's postflop decisions by board length, dial off / on):
flop 4,033, turn 1,600, river (5 cards) 851 / 854, six cards 245 / 241, seven or more 96 / 73. Past 8 cards F with
the dial off checked 93 times and folded to a bet 3 times; with the dial on it bets 12 of 73 and folds 3. On a red
river with the dial it bets more when checked to (170 bets of 627 checked-to decisions, against 136 of 628), drawing hands
semi-bluffing because a card still comes. About 1% of F's decisions are on a board of six or more cards, 0.3% on
seven or more, and they are rarely contested: the aware bots bet the run only with a made hand.

**Screens** (climb_accept `--stages aware --aware river_of_blood_aware`, candidate - F, 200 x 8, paired):

| dials (on top of SHIP_DIALS) | cand - F |
|---|---|
| `hero.long_board` | -0.003 +- 0.046 level |
| ... + `long_value_per_card` 1 | -0.021 +- 0.044 level |
| ... + `long_call_per_card` 1 | -0.006 +- 0.051 level |
| ... + `long_to_come` 2 | -0.006 +- 0.047 level |
| ... + `long_value_per_card` 1, `long_call_per_card` 1 | -0.006 +- 0.051 level |

**A blind-spot check** (scratch `runbettor.py`, not tuning input): the same field with rob_tag replaced by a "run
bettor" (rob_tag that bets half the pot on every board of seven or more cards when checked to: what a team that
noticed bots fold past 8 cards would add). F with `hero.long_board` - F: -0.001 +- 0.046, F 6.210, the run bettor
4.893 (rob_tag's 4.888 in its seat). F is in too few pots that reach seven cards for the blind spot to cost points.

So: the long read is correct (no check-or-fold of a made hand, no table built in a decision, the run counted) and
costs nothing measurable, but it is not where River of Blood's points are. It goes into the candidate as a
correctness fix at its defaults (`long_to_come` 1, no tier shifts).

## 5. deal5_keep2: the calls

**Where F stood** (`tools/skill_profile.py run --field realistic_keep2 --variant deal5_keep2 --bots ship,keep2_tag`,
150 seeds x 8, F as shipped): F 6.43 +- 0.07 (1st 23%, bust 76%), keep2_tag 4.98 (1st 15%, bust 85%). The bust rate
is mostly the format: on this table hands are strong, stacks go in and tables play down to one winner, so a seat that
does not finish first busts (F's finishes: 1st 23%, 2nd 31%, 3rd 26%, 4th 12%; survivals at the hand cap about 1%).
Per section (F's share of decisions, VPIP, bb per decision; busts are the section of the last chips in):

| section | F share | F vpip | F bb/dec | keep2_tag bb/dec | F busts |
|---|---|---|---|---|---|
| pre_open_40 | 6% | 45% | -0.423 | -0.037 | 0 |
| pre_raised_deep | 11% | 35% (raise 4%) | -0.587 | +0.739 | 2 |
| pre_3way | 15% | 42% | -0.121 | +0.339 | 53 |
| pre_hu | 22% | 55% | +0.019 | +0.153 | 135 |
| post_hu_bet | 18% | **79%** (raise 5%) | +1.852 | +2.014 | **411 (45%)** |
| post_hu_chk | 20% | 39% | +1.231 | +1.889 | 110 |
| post_mw | 6% | 46% | +1.206 | +1.762 | 161 (18%) |

The weakest section is facing a bet after the flop: F continues 79% of the time and 45% of its busts come from there
(63% with the multiway pots). The cause: `keep_value_shift` (v-catalog) moves Hero's value and raise thresholds up a
tier because everyone kept their best two of five on this flop, but a call reads the made hand's equity from the
hold'em tier table (TIER_EQUITY) against one random hand. On this table the bettor's two cards are a chosen pair, so
top pair is a bluff-catcher, not a 58% favourite.

**Dial `hero.keep_call_shift`** (0 = off): facing a bet on deal5_keep2 (the `discard_count` rule, Hero's
`_revealed_dead`), the made hand's equity is read this many tiers lower (draw equity unchanged). Unit test: Ah Kd on
Ks 8c 3d facing a half-pot bet calls at 0 and folds at 2; no shift on plain hold'em or toss_or_holdem.

Screens (climb_accept `--stages aware --aware realistic_keep2:deal5_keep2`, candidate - F, 200 x 8, F 6.418):

| dials | cand - F |
|---|---|
| `hero.keep_call_shift` 1 | **+0.241 +- 0.054 UP** |
| ... 2 | **+0.356 +- 0.062 UP** |
| ... 3 | +0.375 +- 0.067 UP |
| ... 4 | +0.359 +- 0.067 UP |
| ... 3, with `hero.keep_value_shift` 2 | +0.370 +- 0.067 UP |
| `hero.keep_value_shift` 2 (calls unshifted) | +0.040 +- 0.035 UP |
| `hero.variant_preflop` {call_raise_frac 0.15} (vb's flat dial, every twist table) | +0.070 +- 0.047 UP |

2, 3 and 4 are level with each other; kept at 2, the smaller step (v-catalog's rule for keep_value_shift). The value
side was already right: moving bets up another tier adds +0.04, moving calls down two adds +0.36.

## 6. short_deck: shove-call margins

vb-top-variants found F calls 28% of all-ins on `short_deck_aware` where the aware TAG calls 10%. F as shipped here
(skill profile, 200 x 8): `pre_allin` 2% of decisions, F VPIP 29%, +0.019 bb a decision; short_tag 10%, +0.324.
Where the calls come from (probe, 50 seeds x 8): at 10 bb or less, PushFold's `_call_shove` (the shover's range from
the short-deck Nash push frequency, scaled by its shove rate; margin `pushfold.call_equity_margin`) calls 178 of 371;
deeper, the preflop module's `_facing_shove` (range from the shove rate x `shove_range_mult`; margin
`shove_eq_margin`) calls 159 of 764.

**Dial `hero.variant_pushfold`** ({} = off): PushFoldParams overrides on catalogued twist tables, behind the same gate
as `variant_preflop` (not fixed limit, not must-use); a copy of the table's PushFold module sharing the solved arrays
(tested). The deeper calls already have their key: `variant_preflop`'s `shove_eq_margin` / `shove_range_mult`.

With both margins at 0.10 the calls drop from 48% to 25% (10 bb or less) and from 21% to 12% (deeper): the dials
reach the decisions. Screens (`--aware short_deck_aware`, candidate - base, 200 x 8):

| dials | base | cand - base |
|---|---|---|
| `hero.variant_pushfold` {call_equity_margin 0.05} | F 5.754 | +0.008 +- 0.011 level |
| ... {call_equity_margin 0.10} | F | +0.010 +- 0.016 level |
| `hero.variant_preflop` {shove_eq_margin 0.08} | F | -0.013 +- 0.023 level |
| ... {shove_range_mult 0.75} | F | -0.011 +- 0.016 level |
| call_equity_margin 0.05 and shove_eq_margin 0.08 | F | -0.006 +- 0.025 level |
| the same two, on top of vb's flats {call_raise_frac 0.15, three_bet_frac 0.05} | vb's candidate 5.953 | +0.001 +- 0.029 level |

Level everywhere, with tight intervals: the calls F gives up by tightening were break-even. The TAG's 10% and +0.32 are
descriptive (it reaches an all-in with the premiums it opened or 3-bet; F reaches it with wider opens and calls when
the price is right). Shove-call margins are not the short deck's lever; the deep flats are (vb's
`variant_preflop`, +0.20 on this field). No short-deck dial goes into the candidate. `variant_pushfold` stays in as a
tool (off).

## 7. The candidate

Measured first on the branch before its rebase (4e063a2, main ea4d36f; code version 53c6dc21ec):

    {"hero.long_board": true, "hero.keep_call_shift": 2}

`long_board` acts only on boards past five or under `run_until_black` (river_of_blood), `keep_call_shift` only under
the `discard_count` rule (deal5_keep2). Every number paired against F (dials {} on top of SHIP_DIALS), screen seeds
10000-10199 x 8.

**Aware stage** (`--stages aware`, the four aware fields plus `realistic_keep2:deal5_keep2`):

| field | F | candidate | candidate - F |
|---|---|---|---|
| toss_or_holdem_aware | 6.131 | 6.131 | +0.000 +- 0.000 (identical) |
| bounty_aware | 5.963 | 5.963 | +0.000 +- 0.000 (identical) |
| short_deck_aware | 5.754 | 5.754 | +0.000 +- 0.000 (identical) |
| river_of_blood_aware | 6.214 | 6.210 | -0.003 +- 0.046 level |
| realistic_keep2 (deal5_keep2) | 6.418 | 6.773 | **+0.356 +- 0.062 UP** |

**F's margins over the field, before and after** (every bot's points, paired per seed with F; scratch `margins.py`):

| field | best aware bot: F - it, before / after | best bot of any kind: F - it, before / after |
|---|---|---|
| river_of_blood_aware | rob_tag (4.888 / 4.904): +1.325 +- 0.139 / +1.306 +- 0.140 | rival1, blind (5.263 / 5.248): +0.950 +- 0.174 / +0.962 +- 0.177 |
| realistic_keep2 | keep2_tag (4.748 / 4.720): +1.669 +- 0.102 / **+2.053 +- 0.086** | rival1 (6.066 / 5.908): +0.352 +- 0.110 / **+0.865 +- 0.098** |

On deal5_keep2 F (skill profile, 150 x 8) goes 6.43 -> 6.78: facing a bet after the flop it continues 43% (from 79%)
and wins 68% of the showdowns it reaches from there (from 51%); busts from that section fall from 411 to 268 (45% to
30% of busts). The bust rate stays at 75% (the format: tables play down to one winner); the finishes move from
1st 23 / 2nd 31 / 3rd 26 / 4th 12% to 1st 20 / 2nd 50 / 3rd 21 / 4th 6%. Other payout tables (scratch
`paired_pay.py`, the same 200 x 8): 50/25/12/6/3/2/1/1 **+2.904 +- 0.816** of 100, 10/7/5/4/3/2/1/0 **+0.527 +- 0.118**.

**Variants stage** (`--stages variants`, all 26 entries on realistic, 200 x 8): **identical (+0.000 +- 0.000) on 24**;
deal5_keep2 6.591 -> 6.876, **+0.285 +- 0.059 UP**; river_of_blood 6.306 -> 6.284, -0.022 +- 0.048 level. None down.

**Plain hold'em** (`--stages confirm,guards`): every cell **identical**, +0.000 +- 0.000 per seed: night 5.973,
night_hard 5.485, realistic 6.346, top 5.035, night at 10/7/5/4/3/2/1/0 6.159, at 50/25/12/6/3/2/1/1 24.443, night
with doubling blinds 5.828; 0 timeouts and 0 errors for both. (The tool prints REJECT: the confirm line wants night
beyond noise up, which a variant-only change cannot give; the guards line holds.)

**After the rebase onto main 77d8932** (S2's dials, all defaulting to today's play, and the lowball gate on
`variant_preflop`; F's SHIP_DIALS unchanged): the two cells the candidate moves reproduce exactly (code 560f7cf78d):
deal5_keep2 6.418 -> 6.773, +0.356 +- 0.062; river_of_blood 6.214 -> 6.210, -0.003 +- 0.046.

### 7b. toss_or_holdem: the same lever (added after the measurements above)

deal5_keep2's finding (the value side of a "chosen hand" twist was shifted, the call side was not) applies to
toss_or_holdem, the likeliest twist (11%): vb-top-variants' `toss_value_shift` moves bets only. New dial
`hero.toss_call_shift` (0 = off; e78f26f), the call side, on the three-card face-up toss tables (Hero's `_toss`:
toss_or_holdem and three_card_blind_discard; tested off elsewhere). Screens on `toss_or_holdem_aware` (rebased code,
F 6.131):

| dials | cand - F |
|---|---|
| `hero.toss_call_shift` 1 | **+0.230 +- 0.078 UP** |
| ... 2 | +0.235 +- 0.082 UP |
| `hero.toss_value_shift` 2 (vb's; reproduces its +0.134) | +0.134 +- 0.076 UP |
| `toss_value_shift` 2 and `toss_call_shift` 2 | +0.166 +- 0.090 UP |

1 and 2 are level; kept at 1. The calls are the larger half here too, and the value shift adds nothing on top.

**The extended candidate**, measured on the rebased code (560f7cf78d):

    {"hero.long_board": true, "hero.keep_call_shift": 2, "hero.toss_call_shift": 1}

Aware stage: toss_or_holdem_aware 6.131 -> 6.361, **+0.230 +- 0.078 UP**; bounty_aware and short_deck_aware
identical; river_of_blood_aware -0.003 +- 0.046 level; realistic_keep2 **+0.356 +- 0.062 UP**. Variants stage on the
entries a gate reaches (`--variants`, realistic, 200 x 8; F's numbers equal the pre-rebase run's): toss_or_holdem
6.335 -> 6.511, **+0.176 +- 0.067 UP**; three_card_blind_discard 6.242 -> 6.400, **+0.158 +- 0.064 UP**; deal5_keep2
**+0.285 +- 0.059 UP**; river_of_blood -0.022 +- 0.048 level. The other 22 entries cannot be reached by any of the three
gates (Hero's `_run`, `_revealed_dead`, `_toss`; checked over the catalog) and were identical for the first candidate.
Plain hold'em (`--stages confirm,guards`, rebased code): every cell **identical**, +0.000 +- 0.000, with the same
values as before the rebase (night 5.973, night_hard 5.485, realistic 6.346, top 5.035, 6.159 and 24.443 under the
other payout tables, 5.828 with doubling blinds); 0 timeouts, 0 errors.

F's margins on `toss_or_holdem_aware` (scratch `margins.py`): over toss_rival1 (5.632 / 5.559) **+0.499 +- 0.146 ->
+0.801 +- 0.134**, over toss_tag +0.985 -> +1.212.

## 8. Timing

`tools/latency.py --bot ship --dials <spec> [--variant NAME] --n 20000` (latency.py now deals river_of_blood's run:
a river decision may sit anywhere along the red run, so long boards are timed), F / the extended candidate:

| rules | host load ~7 (the first candidate): p50 / p99 / max us | host load ~12 (the extended candidate): p99 |
|---|---|---|
| river_of_blood | F 51.0 / 188.8 / 3398, candidate 51.1 / 181.0 / 6956 | F 247.5, candidate 162.1 |
| deal5_keep2 | F 48.9 / 158.6 / 1043, candidate 49.0 / 166.8 / 3540 | F 272.1, candidate 249.9 |
| toss_or_holdem | | F 265.7, candidate 269.1 |
| plain hold'em | F 49.2 / 156.2 / 874, candidate 49.2 / 160.1 / 911 | F 277.5, candidate 303.9 |

The maxima and the over-1 ms counts (0.01-0.24%, F and the candidate alike) are preemption on a loaded host: the same
observations replayed three times on a fresh bot, per-call minimum (scratch `lat_min.py`), give for the extended
candidate river_of_blood p50 45.8 / p99 88.9 / max 165.8 us, toss_or_holdem 44.5 / 70.9 / 172.4, deal5_keep2 46.2 /
79.4 / 324.9, **none over 1 ms**. By board length on river_of_blood (min of three): five cards p99 62.6 us, six 86.4,
seven 90.7, eight 99.7, nine or more 101.8 (max 101.8). 0 timeouts in every model run above.

## 9. Checks

- Full suite on the branch before the rebase: 1016 passed, 1 skipped. After the rebase onto main 77d8932: 1032 passed,
  2 skipped, 1 failed, `tests/test_sim_outside.py::...[outside_strong]` (an exact-replay check of Hero in model mode,
  run while a climb_accept was playing at load 12; it passes alone, 14 of 14): the known load flake.
- **Final tree** (rebased again onto main 2d14fa5, F's dials unchanged there): 1020 passed, 13 skipped, 8 failed at
  load 12-13 with a climb_accept running beside it, every one a wall-clock test (test_slowbox x3, the kit D latency
  round trip, two exact-replay checks, two per-bot budget checks); the 8 rerun alone: **8 passed**. The budget check
  flakes on main too at this load (6 of 10 runs fail on main, 8 of 10 on the branch, which has three more bots in it).
  The two cells the extended candidate moves reproduce on this tree (code 190d1daed3): toss_or_holdem_aware +0.230 +-
  0.078, realistic_keep2 +0.356 +- 0.062.
- Every new dial is off by default (tests/test_vc_dials.py, tests/test_river_of_blood.py); with all of them on, plain
  hold'em is bit-identical (section 7, per seed) and 22 of 26 catalog entries are identical (section 7).
- tests/test_river_of_blood.py: the spec numbers and run streets (moved), conservation, `evaluate_many` against
  brute force at 5-14 cards and never building a table, Hero folding the probe flush without the dial and raising it
  with, playing the board on seven cards, outs only while a card can come, red last card as a turn and black as the
  river, the hybrid's `hero_on_long_board`.
- tests/test_aware.py: `rob_read` on the cases above; the field test plays `river_of_blood_aware` with no error.
- docs/packet/CONTRACTS.md regenerated (`python tools/apicard.py`).
- Not touched: the four held-out entries' code, rules and tests; no judge, outside, elite or exploiter field used.

## 10. Next

- Ship `{"hero.keep_call_shift": 2, "hero.toss_call_shift": 1, "hero.long_board": true}` through the protocol: inert
  on plain hold'em, so the decision is the aware and variants stages on a held-out set (rerun `--stages aware
  --aware toss_or_holdem_aware,realistic_keep2:deal5_keep2,river_of_blood_aware` and `--stages variants` on H-k).
  With vb's set (`variant_preflop` flats, `toss_value_shift` 2, `base.hero_on_bounty`): measure the stack once;
  on toss the value shift added nothing on top of the call shift here.
- The call side is the lever wherever a twist lets everyone choose their hand: bonus_card, auction (a third card
  bought), three_card_keep (three kept), swap_holdem / swap_one_turn. Each has a value-side read or a tier penalty
  (`multi_tier_penalty`, the swap value shift) and calls read from TIER_EQUITY; a `call_shift` by rule is one line in
  HeroCore.act each. Screen them on `realistic` (no aware field yet).
- river_of_blood: correct, not stronger. Its points would come from preflop (rival 3's core does not know the run:
  suited and connected hands gain) and from an aware field that bets the run more; the run-bettor check found F in too
  few long pots to matter. `HybridConfig.hero_on_long_board` (off) for the fallbacks: hybrid3_x's core reads a run
  street as a river.
- Short deck: ship the deep-flat dial (vb); shove-call margins are not where its points are.
