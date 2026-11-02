# vb-top-variants: the three likeliest twists against opponents that play them (2026-11-01/02)

Branch `climb/vb-top-variants` from main d1b6b59, rebased onto 6327dcd. Track V of the climb (docs/drills/goal-plan.md, backlog V1), for the
three likeliest variants (docs/drills/climb/variants-ranked.md): toss_or_holdem 11%, bounty 8%, short_deck 7%. F was
READY (first) on each against the `realistic` field, whose bots mostly ignore the twist; on the night every team's bot
knows the variant. Every number is model mode, eight rotations per seed, screen seeds 10000-10199 only (200 x 8), F as
hyperion.ship builds it (dials on top of SHIP_DIALS; `tools/climb_accept.py`, never `tools/swap.py` paired specs), at
most three worker processes on a host at load 7-9 (other workers running).

Sections: 1 the aware opponents, 2 where F stood, 3 the known gaps, 4 screens, 5 the candidate and the margins, 6
plain hold'em, 7 timing, 8 the other catalog entries, 9 checks, 10 next.

## 1. Variant-aware opponents (48e8055)

`hyperion/sim/aware.py`, registered in the bestiary, in the `<variant>_aware` fields only (never a night pool; tested).
Each field is `realistic` with Hero's seat, the entry's aware bots in the seats of the honest Monte Carlo bot, the
push/fold bot and the TAG, and the rest as it was (montecarlo30, loose_aggro, rival1, timeout_then_recover):

| field | aware bots (what each does with the twist) |
|---|---|
| `toss_or_holdem_aware` | `toss_tag`, `toss_pushfold`: ChartTAG / PushFoldBot on the Chen-best two of three, one range wider when the third card pairs, suits or connects with them twice; the toss keeps the best made hand with the flop, then the most live outs (every face-up toss so far and its own are dead), then high cards. `toss_mc`: Monte Carlo equity after the toss against two-card opponents, every toss dead. `toss_rival1` (in rival 1's seat): rival 1 unchanged, with the same toss |
| `bounty_aware` | `bounty_tag`, `bounty_pushfold`: one range (position) wider holding the bounty rank, and with the bounty hit, a half-pot bet when checked to in a pot of three or fewer. `bounty_mc`: 2 Chen points looser holding the rank, the same bet |
| `short_deck_aware` | `short_tag`, `short_pushfold`: ChartTAG's / PushFoldBot's ranges re-cut for the 36-card deck (the same share of combos by short-deck heads-up equity, opens a fifth wider), hands read with short-deck rankings (flush over full house, A-6-7-8-9). `short_mc`: Monte Carlo from the 36-card deck with short-deck rankings |

The Monte Carlo bots sample 48 runouts against at most three opponents, open-raise by Chen score by position, never
limp, and add up to 0.15 to their call margin as the bet grows to the pot (a bettor's range beats random); they have no
cost model, so they are never folded for time in model mode.

**Do they play the twist sensibly?** Checked against their variant-blind twins (scratch, seeds 10000-10099 x 8, the
variant on):
- toss: a toss read by equity, 400 random three-card hands on random flops, kept two against one random hand to the
  river: aware 0.589, the hook's default (pair, else suited, else highest) 0.556, the best of the three 0.599. As
  players: toss_tag 4.92 = tag 4.92, toss_pushfold 4.38 > pushfold 4.11 (one field with both). Handing rival 1 the
  Chen-best two preflop cost it 0.47 (its hold'em ranges then play too many hands), so toss_rival1 keeps its preflop
  and gets only the toss.
- bounty, paired seat swaps on `realistic` under bounty: the first try (calls and shoves one range wider holding the
  rank, any pair continues when hit) was worse than the blind bots (push/fold -0.27 +- 0.09, TAG -0.12 +- 0.09). Part by
  part for the push/fold bot: wider opens +0.02 +- 0.05, wider calls of raises and shoves -0.06 +- 0.03, continuing with
  any pair -0.16 +- 0.09. The bounty pays for winning pots, so the lever is fold equity: the bet when hit +0.09 +- 0.06
  (TAG), +0.05 (push/fold). Shipped: wider opens and the bet; TAG +0.06, push/fold +0.04, MC +0.07 over their twins.
- short deck (one field with both): short_tag 5.13 > tag 4.68, short_pushfold 4.83 > pushfold 4.29, short_mc 4.80.

`TossHooks` now asks in the postflop acting order (first seat left of the button first), as Keep2Hooks does, and the
prompt carries the face-up tosses made so far; the engine's comment that it passed holes out of position first was
wrong (it went in seat order). Every bot that ignores the new key plays the same: F's and every other seat's per-seed
samples on `realistic` under toss_or_holdem, seeds 10000-10049, are identical on main and the branch.

Tools: `tools/climb_accept.py --stages aware [--aware FIELD,...]` (each field under its variant, paired);
`tools/variant_matrix.py --aware [--dials JSON]`; `tools/skill_profile.py run --field X_aware --bots ship,...`
(`--variant`, and `ship` is F with `--dials` on top of SHIP_DIALS).

## 2. Where F stood (4d1f679, dials off: F as shipped)

All bots' points on each aware field, F in Hero's seat, 200 seeds x 8 (scratch `margins.py`; F minus each bot paired
per seed):

| field | F | best aware bot | F - it | best other |
|---|---|---|---|---|
| toss_or_holdem_aware | 6.131 +- 0.090 | toss_rival1 5.632 | **+0.499 +- 0.146** | toss_tag 5.146 |
| bounty_aware | 5.970 +- 0.107 | bounty_tag 4.976 | **+0.994 +- 0.145** | rival1 (blind) 5.338, +0.632 +- 0.163 |
| short_deck_aware | 5.754 +- 0.100 | short_tag 5.478 | **+0.276 +- 0.135** | short_mc 5.337 |

F first on all three; short deck is the closest. On all three tables Hero plays every decision (the base's
`table_reason`: three cards, bounty, deck), so F there is Hero with the layer and SHIP_DIALS.

## 3. The known gaps, checked

**toss_or_holdem: face-up tosses as dead cards.** Hero never read `extras["discards"]`. Dial `hero.toss_dead`: every
face-up toss (ours included) comes off the postflop draw outs, and the toss itself (variant_decide "discard") reads
the tosses made before ours (the prompt's new "discards") and the card it throws as dead. Measured +0.003 +- 0.004:
right, and nearly worthless, as deal5_keep2's revealed discards were (+0.000 +- 0.039, v-catalog-log section 5). Dead
cards move only the outs of a draw, and Hero's tier read rarely changes a decision on two or three outs.

**bounty: does F price the bounty in every all-in and call?** On a bounty table rival 3's core never played: the
base's `table_reason` is "bounty" (`hero_on_bounty`), so Hero played every decision. Hero prices it (Spot.bounty_bonus)
in every push/fold ICM gate, preflop call gate, postflop commitment gate and in the pot odds of every call, but (a) the
"net win" counted our own chips from earlier streets, (b) a shove's winning branch had no bounty on the chips the
caller adds, and (c) the range filters before the gates (push and call fractions) never widen for it. Dials:
`hero.bounty_exact` (a and b), `hero.bounty_call_scale` (the bounty's weight in the pot odds of a call),
`hero.bounty_bet_frac` (bet a hit bounty where Hero checks, the aware bots' best trick). For rival 3's core:
`base.hero_on_bounty: false` lets it play the bounty table where it can (preflop; Hero keeps postflop and short
facing a raise, the shipped route), and `r3.bounty` adds the bounty's chips to the steal and win branches of its
`_allin` price (Rival3Core; set per decision by HybridCore from `extras["bounties"]`).

Also fixed: BountyHooks drew a block's bounties at the payout of hands 0, 25, 50 ..., so hand 0 showed no bounty and
hands 25, 50 ... showed the old one while being scored with the new (the same draws now come at the block's first
deal; tests/test_vb_dials.py fails on the old hook). This moves bounty play by a hand in 25; every bounty number after
8957986 is on the fixed hook.

**short_deck: are the tables and push/fold ranges short-deck ones?** Yes in kind, not in detail. Hero loads
`tables/variants/short_deck/` (36-card deck, 81 live classes, a heads-up push/fold solve on the short-deck matrix),
but (a) the generator scored hold'em's showdown (flush below full house, no A-6-7-8-9), (b) at catalog samples (4,000
per class, 1,000 per matrix pair: J9o's percentile 0.635 there, 0.505 at 20,000), and (c) there was no multiway
push/fold table, so short deck used the heuristic multiway rule (`pushfold.mw` None). Postflop, Hero's read used
hold'em's straights and outs: A-6-7-8-9 missed, nine flush outs (five on a short deck), completers 2-5 counted, the
rule of 4 and 2 for 47 unseen cards (31 here). Fixes: the generator scores the short deck's showdown when the rules
say so (`category_order`, `low_straight`; tested against ShortDeckHooks on 3,000 random pairs);
`tables/variants/short_deck_v2/` regenerated with it at 20,000 / 5,000 samples plus `tools/gen_multiway.py` (51 s);
dials `hero.variant_tables: "short_deck_v2"` and `hero.short_deck_read` (the short-deck postflop read).

## 4. Screens (climb_accept `--stages aware`, F vs F with the dial, 200 x 8, paired per seed)

The weakest section first (`tools/skill_profile.py`, F, the best aware bot and one more in Hero's seat on each field,
scratch `prof0`): on all three, **facing a raise at 20+ bb** (`pre_raised_deep`, 18-19% of F's decisions). F flats
35% of raises there and loses -0.088 (short), +0.064 (toss), -0.127 (bounty) bb a decision; the aware TAGs continue
with 5-6% (premiums) and win +0.17 to +0.51. Hero's flat range is the top 45% of hands (`preflop.call_raise_frac`)
with an equity test against *random* hands; on plain hold'em rival 3's core plays preflop, so it never mattered there.
`hero.variant_preflop` sets PreflopParams for a catalogued twist's tables only (rules.extras["variant"] names one).

| dial | toss_or_holdem_aware | short_deck_aware | bounty_aware |
|---|---|---|---|
| `hero.preflop.call_raise_frac` 0.25 | +0.043 +- 0.063 | +0.070 +- 0.084 | +0.094 +- 0.078 UP |
| `hero.preflop.call_raise_frac` 0.15 | +0.082 +- 0.069 UP | +0.144 +- 0.095 UP | |
| `hero.variant_preflop` {call_raise_frac 0.15} | +0.082 +- 0.069 UP (the same) | +0.144 +- 0.095 UP (the same) | +0.140 +- 0.089 UP |
| ... {call_raise_frac 0.10} | +0.076 +- 0.072 UP | +0.183 +- 0.096 UP | +0.160 +- 0.094 UP |
| ... {call_raise_frac 0.15, three_bet_frac 0.05} | +0.096 +- 0.076 UP | +0.198 +- 0.097 UP | +0.125 +- 0.098 UP |
| `hero.preflop.setmine_ratio` 30 | -0.022 +- 0.032 | +0.012 +- 0.023 | |
| `hero.preflop.open_frac_mult` 0.8 | -0.034 +- 0.047 | -0.017 +- 0.055 | |
| `hero.pushfold.call_equity_margin` 0.05 | -0.005 +- 0.008 | +0.008 +- 0.011 | -0.010 +- 0.017 |
| `hero.toss_dead` | +0.003 +- 0.004 | | |
| `hero.toss_value_shift` 1 / 2 | +0.098 +- 0.073 UP / +0.134 +- 0.076 UP | | |
| `base.hero_on_three_cards` false (the core plays toss preflop from its best two) | -0.245 +- 0.107 DOWN | | |
| `hero.short_deck_read` | | +0.001 +- 0.049 | |
| `hero.bounty_exact` | | | +0.019 +- 0.041 |
| `hero.bounty_call_scale` 0 | | | -0.014 +- 0.070 |
| `hero.bounty_bet_frac` 0.5 | | | -0.148 +- 0.090 DOWN |
| `base.hero_on_bounty` false | | | **+0.278 +- 0.114 UP** |
| `r3.bounty` 1.0 / 0.5, on top of hero_on_bounty false | | | -0.033 +- 0.035 / -0.018 +- 0.027 |

(Screens before 8957986, so on the old bounty hook; the same base for both specs of a row.) What they say:
- The one lever common to the three tables is Hero's preflop facing a raise: flat less (and 3-bet a little more).
- On bounty the largest gain is not bounty pricing at all: rival 3's core plays the table's preflop better than Hero,
  as it does on plain hold'em. Pricing the bounty into either core's stack-offs is level or worse, and so is betting
  a hit bounty: the aware bots' lesson (the bounty pays for winning pots, not for calling) holds, and F already
  bets enough.
- toss_or_holdem: everyone kept the best two of three, so made hands are worth less than their tier (the deal5_keep2
  reason, `keep_value_shift` there): thresholds up two tiers.
- The short deck's tables and postflop read were wrong in detail, and correcting the read changed nothing measurable.

Two more, after 8957986: `hero.variant_tables: "short_deck_v2"` -0.009 +- 0.067 (the cleaner tables and the multiway
solve change nothing measurable either), `hero.toss_value_shift` 3 +0.122 +- 0.076 (level with 2).

## 5. The candidate: one dial set, every part gated to its twist

    {"hero.variant_preflop": {"call_raise_frac": 0.15, "three_bet_frac": 0.05}, "hero.toss_value_shift": 2,
     "hero.toss_dead": true, "base.hero_on_bounty": false}

`variant_preflop` acts only where rules.extras["variant"] names a twist (every Hero table, not plain hold'em),
`toss_*` only on a three-card face-up toss, `hero_on_bounty` only on a bounty (or knockout) table. Branch rebased onto
origin/main 06dfb4b (batch 2: SHIP_DIALS with the SafeBot governor) before these numbers; F's and the candidate's
numbers on the three aware fields came out identical to the pre-rebase runs (model mode). Rebased again onto
6327dcd (climb_accept workers replaced after two jobs: the memory fix) before the variants stage.

**Paired, the candidate against F** (`tools/climb_accept.py --stages aware --set screen`):

| field | F | candidate | candidate - F |
|---|---|---|---|
| toss_or_holdem_aware | 6.131 | 6.287 | **+0.156 +- 0.087 UP** |
| bounty_aware | 5.963 | 6.260 | **+0.298 +- 0.119 UP** |
| short_deck_aware | 5.754 | 5.953 | **+0.198 +- 0.097 UP** |

**F's margin over the best aware bot, before and after** (every bot's points, paired per seed with F):

| field | best aware bot | before: F - it | after: F - it | best bot of any kind, after |
|---|---|---|---|---|
| toss_or_holdem_aware | toss_rival1 (5.632 / 5.619) | +0.499 +- 0.146 | **+0.668 +- 0.121** | the same |
| bounty_aware | bounty_tag (4.961 / 4.944) | +1.002 +- 0.150 | **+1.317 +- 0.139** | rival1, blind (5.331 / 5.315): +0.632 -> +0.945 +- 0.148 |
| short_deck_aware | short_tag (5.478 / 5.423) | +0.276 +- 0.135 | **+0.529 +- 0.123** | the same |

F first on all three before and after; finishes first 29% (toss), 53% (bounty, from 45%), 36% (short deck) of seats.
After the candidate the short-deck profile (scratch `prof1`, F and short_tag in Hero's seat) has F's flats facing a
deep raise at 16% (from 35%) and that section at +0.069 bb a decision (from -0.088; the TAG +0.172); it is still F's
weakest section there, with facing an all-in (calls 28%, +0.097; the TAG 10%, +0.324) next.

## 6. Plain hold'em does not move

`tools/climb_accept.py --cand <the candidate> --set screen --stages confirm,guards` (after the rebase): every cell
**identical**, +0.000 +- 0.000, per seed: night 5.973, night_hard 5.485, realistic 6.346, top 5.035, night at
10/7/5/4/3/2/1/0 6.159, at 50/25/12/6/3/2/1/1 24.443, night with doubling blinds 5.828; 0 timeouts, 0 errors on both.
(The tool prints REJECT because the confirm line asks for night beyond noise up, which a variant-only change cannot
give; the guards line holds.) The p99 column there (543-1329 us) is the model-mode wall clock on a host at load 9+ with
other workers running, the same for both specs; section 7 has latency.py.

## 7. Timing

`tools/latency.py --bot composite --dials <spec> --rules <the twist's rules> --n 20000` (one process, load ~6):

| rules | F p50 / p99 / max us | candidate p50 / p99 / max us |
|---|---|---|
| bounty | 44.1 / 116.3 / 773 | 46.2 / 120.6 / 464 |
| toss_or_holdem | 44.4 / 114.0 / 384 | 44.9 / 116.0 / 324 |
| short_deck | 43.0 / 108.1 / 354 | 42.7 / 109.4 / 417 |

None over 1 ms. On bounty the candidate's preflop is rival 3's core (as on plain hold'em), which costs what it costs
there. 0 timeouts and 0 errors in every aware and plain run above (model mode).

## 8. The other catalog entries (the variants stage)

`tools/climb_accept.py --stages variants --set screen` (all 25 entries on `realistic`, 200 x 8, paired), the candidate
against F. `variant_preflop` reaches every Hero table, so this is where it could hurt:

| entry | candidate - F | | entry | candidate - F | |
|---|---|---|---|---|---|
| permuted_ranks | -0.012 +- 0.025 | level | bonus_card | +0.006 +- 0.019 | level |
| short_deck | +0.111 +- 0.069 | UP | auction | -0.015 +- 0.018 | level |
| lowball | -0.002 +- 0.053 | level | deal5_keep2 | +0.076 +- 0.048 | UP |
| wild_deuces | +0.124 +- 0.072 | UP | bounty | +0.294 +- 0.130 | UP |
| flush_over_full_house | +0.084 +- 0.092 | level | knockout_bounty | +0.310 +- 0.217 | UP |
| toss_or_holdem | +0.074 +- 0.077 | level | top_heavy | +0.213 +- 0.312 | level |
| three_card_blind_discard | +0.083 +- 0.072 | UP | hi_lo | +0.029 +- 0.101 | level |
| three_card_keep | +0.125 +- 0.080 | UP | pot_limit | +0.010 +- 0.028 | level |
| omaha_four | -0.065 +- 0.051 | **DOWN** | antes_from_level_3 | +0.024 +- 0.022 | UP |
| swap_holdem | -0.007 +- 0.036 | level | fixed_raise | -0.108 +- 0.073 | **DOWN** |
| swap_one_turn | +0.002 +- 0.022 | level | fast_schedule | -0.019 +- 0.030 | level |
| exposed_card | +0.065 +- 0.087 | level | straddle | +0.030 +- 0.092 | level |
| two_boards | +0.106 +- 0.098 | UP | | | |

Nine up, two down: fixed limit (a flat costs one bet, so the wide flat range pays) and Omaha (must use two of four:
hands run close). `variant_preflop` is now off on fixed-limit and must-use tables (a rule, not a list of names, so an
unseen twist of either kind is covered); with that gate the candidate is **identical** to F on omaha_four and
fixed_raise (per-seed samples, seeds 10000-10199), and unchanged everywhere else (three_card_keep's per-seed samples
on 10000-10024 equal the stage's cached candidate). So: no entry beyond noise down, eleven up (knockout_bounty's
+0.31 is `hero_on_bounty`, which also covers knockout points). (The stage ran after the memory incident with
`--workers 2` and main's Pool(maxtasksperchild=2); its first attempt was killed and reran from the cache.)

## 9. Checks

- Full suite on the final tree (ee1d2e8, the fixed-limit / must-use gate in): **985 passed, 1 skipped** in 192 s (and
  985 passed before the gate).
- Default play: every new dial is off by default (tested); plain hold'em with the candidate's dials on is
  bit-identical (section 6); the toss hook's acting order and prompt key leave every non-reading bot's play
  identical (section 1). The bounty hook's timing fix is the one deliberate change of default play (bounty only).
- The aware bots are deterministic for a seed and never in a night pool (tests/test_aware.py).
- Not touched: hyperion/drills/variants_unseen.py; no judge, outside or exploiter field used.

## 10. Next

- Ship the candidate's dials in DIALS (or SHIP_DIALS) through the protocol: they are inert on plain hold'em, so the
  held-out confirm cannot pass on `night`; the decision is the aware stage on a held-out set plus the variants stage.
  Rerun `--stages aware` on H-k (not screen) before shipping.
- Short deck stays the closest (+0.53): F still calls 28% of shoves (the aware TAG 10%) and that section is its
  worst after deep flats. The shover's range is read from the short-deck Nash push frequency (60% of hands at 10 bb),
  far wider than these bots shove: try `variant_preflop` shove_eq_margin / shove_range_mult, or the profiler's shove
  rate weighting, on short_deck_aware.
- The same `variant_preflop` reaches all 14 Hero tables; the variants stage says where it helps or hurts beyond these
  three. If it is level everywhere else, it can simply ship with the variant tables.
- Toss: profile F with the candidate for the next weakest section; the toss tables are 1,500 samples a class
  (`tools/gen_catalog.py`), cheap to regenerate at 10x.
- Bounty: with rival 3's core on the preflop, Hero still plays postflop and short facing a raise; route those (the
  composite's sections) to the base on bounty tables and measure.
- Aware opponents for the next likeliest twists (auction and deal5_keep2 have one each; omaha_four and two_boards none).
