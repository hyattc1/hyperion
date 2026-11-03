# V-i: twist decisions priced as value of information, and the showdown tax read (2026-11-03)

Branch climb/vi-twist-value, from main eecf4d8. Item 14 of docs/research/Edges against strong opponents.md
(competitions §5: value the twist's decision as an EV difference by quick simulation, scale by a fudge factor; GTO
Wizard's MIT 2024 auction entry bid the 3v2 - 2v3 equity difference x 1.8, the best of 0.5-2.5x). Seeds: the screen set
(10000-10199) for every measurement, my own for diagnostics (777 / 50000+ / 2026). No held-out set, judge bot or
held-out variant was run, read or tuned on. Host shared (load 14-18 of 8 cores): `nice -n 5`, at most three worker
processes. Scratch scripts: the session scratchpad, `goal/vi_work/scripts/`.

## Findings

**Candidate: `{"hero.voi": 1.5, "hero.sd_tax": true}`** (both off by default; with them off F plays main's F bit for
bit, 14/14 chunks of confirm and guards). Two independent dials; either can ship alone.

1. **The change.** `hero.voi` prices Hero's twist decisions as value of information: one multiplier on an option's
   worth in chips where a price stands against it (the auction's bid: voi x the indifference price, whose d already
   holds the denial value; the bonus card: buy when voi x (e3 - e2) x pot_eff covers (1 - e3) x price), and the option
   worth most where none does (keep, discard, swap), from precomputed tables (tools/gen_voi.py -> tables/voi.json).
   `hero.sd_tax` is V-g's showdown-tax read: a twist whose prepared table pays a showdown f of hold'em's (mean share
   off 0.5004 by more than 0.05) reads calls x f and moves the thin value thresholds up (Ghost: f 0.683, two tiers).
2. **The multiplier: 1.5 of 0.67 / 1.0 / 1.5 (fixed in advance).** Aware stage, auction: -0.039, 0.000, **+0.115 ±
   0.051 UP**; bonus_card: -0.045, +0.057, -0.008, all level. Best of three on the screen seeds: the held-out set
   decides. In GTO Wizard's units 1.5 is about 2.4x the raw equity difference (their best 1.8 is about our 1.1).
3. **Aware stage (generic:<entry>, 200 seeds): nothing down.** auction +0.115 ± 0.051 UP, bonus_card -0.008 ± 0.039,
   swap_holdem +0.000 (no decision), swap_one_turn -0.004 ± 0.082, toss_or_holdem +0.004 ± 0.021,
   three_card_blind_discard +0.009 ± 0.017, deal5_keep2 -0.008 ± 0.029.
4. **Variants stage (realistic): two up, nothing down.** auction +0.064 ± 0.045 UP, swap_one_turn +0.080 ± 0.072 UP,
   bonus_card -0.006, toss -0.006, blind discard -0.003, deal5_keep2 +0.001 (200 seeds each); the other twenty entries,
   where the candidate cannot act, have identical sample lists on 40 seeds. No timeouts, errors or illegal actions.
5. **The showdown tax on the Ghost (told): up.** Screen set +0.189 ± 0.302 (generic) and +0.183 ± 0.285 (realistic);
   with my own 200 seeds, pooled over 400: **+0.267 ± 0.218 and +0.264 ± 0.202, both beyond noise up**, about V-g's
   hand-made c2. The gate is shut on all 26 catalog entries; it needs the twist named in the rules (the table is
   found by name), so an untold Ghost plays F.
6. **Denial was already counted**, in the auction's d = e_win - e_lose: half the card's worth heads-up, a fifth to a
   third multiway, most of it for made hands; no other decision has any (a thrown card is dead whatever I keep). The
   multiplier's gain is in that part: at 1.0 a set bids under the unaware seats' quarter-pot default and loses the
   card to them.
7. **Latency in budget**: per-call minimum p99, F then candidate: swap_one_turn hand end 142.6 / 143.1 us, act 112.0 /
   103.1, variant decisions 33.6 / 181.8 (the swap: about 57 reads, once a hand); deal5_keep2 134.6 / 136.4, 92.9 /
   92.9 (93.3 F), 53.5 / 61.8. Load 56-60.
8. **What did not move**: keep, discard and the bonus card. The keep and toss were already priced by value share
   (against a long simulation VOI's picks agree with the best 81-82%, F's 78-83%); the bonus card's rule changes 3% of
   buys. The swap gains on realistic and is level against the generic field.

## Plan, fixed before measuring

- The multiplier `hero.voi` takes three values, fixed now: **0.67, 1.0, 1.5**. At 1.0 the auction bids the
  indifference price, which is F's bid today (d x pot_eff / (1 - d) already prices the dead money the price feeds and
  the betting to come, so it sits at about 1.4-1.7x GTO Wizard's raw equity difference; their best 1.8 is about our
  1.1, their 0.5-2.5 about our 0.3-1.5). No value outside these three is run.
- The multiplier only moves decisions that have a price against them (bid, buy). Keep, discard and swap take the
  option worth most, whatever the multiplier; so the three values are measured on the auction and bonus_card cells,
  the other aware cells once (they play the same at any value).
- The value carried forward (written after voi 1.0's aware cells, before 0.67's and 1.5's): the one of the three with
  the highest mean of its auction and bonus_card aware differences; the other aware cells do not depend on it.
- The showdown tax's gate margin is fixed now at 0.05 (every catalog twist with hold'em's payoff measures 0.4996-0.5015;
  the Ghost 0.342, bounty 0.569), and its tiers come from a formula (1 / (2f) - 1/2 of TIER_EQUITY above the value
  tier), not a sweep.

## 1. What F did, and the change

F's twist decisions are Hero's `variant_decide` (the composite's base answers with its fallback Hero):

| decision | F (dials off) | `hero.voi` on |
|---|---|---|
| bid (auction) | d x pot_eff / (1 - d), d = e_win - e_lose by flop read and bidders (tables/auction_bid.json), capped at 0.33 stack and 0.75 pot | the same price x voi, the same caps |
| buy_card (bonus_card) | buy when the price is at most a tenth of the stack (always, in practice) | buy when voi x (e3 - e2) x pot_eff >= (1 - e3) x price |
| swap (swap_one_turn) | keep made hands (tier 3+) and draws (8+ outs), else swap the lowest card that pairs nothing and is off any flush draw | swap card i when the mean pot share over every card that could replace it beats keeping |
| discard (toss, flop) | keep the two with the best max(TIER_EQUITY, outs x 0.04) + 0.01 x preflop rank | the two worth most against opponents who kept their best two of three |
| discard (blind, preflop) | keep the two with the best hold'em preflop rank | the kept class's hold'em equity against the opponents in |
| keep (deal5_keep2) | as the toss, every revealed discard and our own three dead | the pair worth most against opponents who kept their best two of five |

- **The option values** are precomputed (`tools/gen_voi.py` -> tables/voi.json, 240,000 deals per table and opponent
  count, 3 minutes on one worker): my pot share by Hero's read (tier, outs bucket) and opponents in (1..4+); `flop2`
  plain hold'em (it reproduces the auction table's `e_two` column), `flop3` / `flop5` against opponents who kept their
  best two of three / five by the flop (every discard dead), `turn` with one card to come, `buy` holding a third card or
  not against opponents holding three (the hook's default is to buy). The prompts carry neither the pot (buy_card) nor
  the opponents in (any but the bid): Hero reads both from the last observation of the hand, which the composite (and
  the hybrid) now hand the base's Hero in the prompt (`last_obs`), since that Hero sees few of the hand's decisions.
- **Denial.** Only the auction has it: a card I do not win goes to a rival. The bid's d already counts it, and the
  change keeps it: d = (e_win - e_two), what the card adds to my hand, + (e_two - e_lose), what it costs me in a
  rival's. Denial is half the card's worth heads-up (0.166 of 0.333 of the pot, weighted over flops) and a fifth to a
  third multiway (0.089 of 0.266 with two rivals, 0.040 of 0.199 with four), and most of it for made hands (top pair
  good kicker heads-up: 0.04 offence, 0.20 denial; a set 0.02 / 0.09). The bonus card has none (every buyer draws his
  own card), nor do the toss, the keep or the swap (a card I throw is dead whatever I keep).
- **The multiplier** scales only the decisions with a price against them; the choices without one take the option
  worth most. A table's swap decision costs about 93 us (one read per replacement card, the suits that cannot matter
  for a flush read once per rank: exactly the full enumeration's answer on 4,000 random turns); the others 3-26 us.
- **The showdown tax** (`hero.sd_tax`): at a table start Hero reads the twist's prepared table (tables/generic/, the
  value share of every class against one hand, dealt and scored through the hooks) and its combo-weighted mean share.
  When it differs from hold'em's 0.5004 by more than 0.05 (and Hero does not price the payoff itself: bounty,
  knockout), a showdown pays f = share / 0.5004 of the pot: facing a bet the equity is read x f, and the thin value
  thresholds (value_tier and the station tiers) move up by the tiers that cover a called bet's need, 1 / (2f) in place
  of a half. The big-value and raise tiers stay (the strong hands pay the least tax: the Ghost beats a straight 7% of
  the time, a pair 56%). Only the Ghost opens the gate (f 0.683, two tiers); bounty's 0.569 is Hero's own bounty term.
  The read needs the twist's name in the rules (the prepared table is found by it): told, not untold.

## 2. Offline checks (before the runs)

- **How often VOI decides otherwise** (F's prompts on 6 generic_aware tables, seed 777, each answered by F and by F +
  `hero.voi` 1.5; CPU per decision, thread time, minimum of 3, load 16-24):

  | decision | prompts | VOI differs | F mean / p99 us | VOI mean / p99 us |
  |---|---|---|---|---|
  | bid (auction) | 98 | 96.9% (the price x 1.5; at 1.0 none) | 5 / 32 | 3 / 7 |
  | buy_card (bonus_card) | 105 | 2.9% | 1 / 1 | 6 / 9 |
  | swap (swap_one_turn) | 60 | 41.7% | 4 / 12 | 165 / 263 (93 / 235 after the per-rank reads) |
  | discard (toss) | 142 | 2.1% | 9 / 21 | 9 / 19 |
  | discard (blind) | 129 | 3.1% | 2 / 5 | 3 / 8 |
  | keep (deal5_keep2) | 202 | 5.0% | 25 / 47 | 26 / 41 |

- **The swap's changes** (4,000 random turns): VOI swaps the card a one-card draw does not use (F keeps every 8-out
  draw: VOI swaps 94% of them, the made flush or straight still live on the card kept), picks the other card of air
  40% of the time, and swaps the kicker of some made hands. The table is coarse there: two pair on a paired board and
  top pair good kicker share tier 4, so Kc Jd on 4d 4s Jh Kh swaps the jack. Against a 600-sample simulation per spot
  (two random opponents, exact ranks), the table's choice agrees 79% of the time, F's rule 68%, and a 32-sample quick
  simulation 80% at twice the table's cost (191 us mean). So the table stays.
- **Keep and toss** against a 300-sample simulation per option (one opponent who kept his best two of N by the flop,
  every discard dead): the toss agrees with the simulation's best 81% (F 78%), mean share 0.4985 (F 0.4964); deal5's
  keep 82% (F 83%), 0.4925 (F 0.4940). Both about F's quality: these decisions were already priced by value share.

## 3. The aware stage (screen set, 10000-10199 x 8, generic_aware under each entry, paired by seed)

`climb_accept --stages aware --aware generic:<entry> --set screen --base '{"dials": {}}'`, code b1f8ab9. Base F's
cells were played on main eecf4d8 and reused (the identity check below: F on this branch plays main's F bit for bit).

| entry (generic_aware) | F | voi 0.67 | voi 1.0 | voi 1.5 |
|---|---|---|---|---|
| auction | 6.392 | -0.039 ± 0.079 | +0.000 ± 0.000 (the same bid) | **+0.115 ± 0.051 UP** |
| bonus_card | 6.058 | -0.045 ± 0.100 | +0.057 ± 0.073 | -0.008 ± 0.039 |
| mean of the two | | -0.042 | +0.028 | **+0.054** |
| swap_holdem (no decision) | 6.336 | | +0.000 ± 0.000 | |
| swap_one_turn | 6.462 | | -0.004 ± 0.082 | |
| toss_or_holdem | 6.470 | | +0.004 ± 0.021 | |
| three_card_blind_discard | 6.350 | | +0.009 ± 0.017 | |
| deal5_keep2 | 6.643 | | -0.008 ± 0.029 | |

The last five play the same at any multiplier (no price in them), so they were run once. No timeouts, errors or
illegal actions in any cell. By the rule fixed above, **1.5** goes forward: the auction is beyond noise up there, and
the auction is monotone in the multiplier (-0.04, 0, +0.12): bidding over the indifference price pays against this
field, as GTO Wizard found (their best 1.8x raw equity difference is about our 1.1; 1.5 is about their 2.4). Caution:
the best of three on the screen seeds, the risk item 14 names; the held-out set decides.

**The showdown tax on the Ghost** (`hyperion/drills/ghost_example.py:variant`, the variant's own rules: Hero told the
twist, kit F's points 16/11/8/6/4/2/1/0):

| Ghost, told | F | F + sd_tax |
|---|---|---|
| generic_aware | 11.348 | +0.189 ± 0.302 |
| realistic | 11.306 | +0.183 ± 0.285 |

Both up, inside noise; V-g's hand-made tighter calls (c2) measured +0.30 ± 0.22 and +0.13 ± 0.22 on the same two
fields. Every catalog entry keeps the gate shut (tests/test_vi_voi.py), so the tax read plays F everywhere else.

## 4. The variants stage (realistic, screen set), the candidate `{"hero.voi": 1.5, "hero.sd_tax": true}`

`climb_accept --stages variants --set screen --cand '{"dials": {"hero.voi": 1.5, "hero.sd_tax": true}}'`, code b1f8ab9;
base F's cells played on main eecf4d8 where they were cached, on this branch otherwise (the same play).

The six entries where the candidate can act, 200 seeds:

| entry | F | candidate | |
|---|---|---|---|
| auction | 6.531 | +0.064 ± 0.045 | UP |
| bonus_card | 5.980 | -0.006 ± 0.048 | level |
| swap_one_turn | 6.440 | +0.080 ± 0.072 | UP |
| toss_or_holdem | 6.497 | -0.006 ± 0.017 | level |
| three_card_blind_discard | 6.434 | -0.003 ± 0.011 | level |
| deal5_keep2 | 6.884 | +0.001 ± 0.009 | level |

The other twenty, 40 seeds (10000-10039): the candidate cannot act there (no variant decision is asked, and the tax
gate is shut on every catalog entry), and every one has the identical sample list, +0.000 ± 0.000: permuted_ranks,
short_deck, lowball, wild_deuces, flush_over_full_house, three_card_keep, omaha_four, swap_holdem, exposed_card,
two_boards, bounty, knockout_bounty, top_heavy, hi_lo, pot_limit, antes_from_level_3, fixed_raise, fast_schedule,
straddle, river_of_blood. (Where the printed base mean differs, its cached chunk 10025 held 25 seeds; the pairing
takes the 40.) Nothing beyond noise down; no timeouts, errors or illegal actions in any cell.

The auction gains on both fields (aware +0.115, realistic +0.064). The swap gains on realistic (+0.080 ± 0.072) and is
level against the generic aware field (-0.004 ± 0.082), whose own swap prices options by runouts.

## 5. Identity and latency

- **Dials off, F plays main's F bit for bit**: `climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages
  confirm,guards` on b1f8ab9, all 14 chunk sample lists (night and the six guards) equal to main eecf4d8's
  (`goal/idchk21`, main's own run). The added code reads nothing with the dials off (the composite's and the hybrid's
  `last_obs` key in the prompt is read only by the VOI options). So base F's cached cells from main were reused above.
- **The final spec is the cells assembled from two runs**: `{"hero.voi": 1.5, "hero.sd_tax": true}` on the aware
  cells' first chunk (10000-10024): auction and bonus_card equal voi 1.5's sample lists, the other five voi 1.0's.
- **Latency** (`tools/latency.py --hand-end --reps 3`, per-call minimum, 20 realistic tables; `variant` is new in the
  replay: each variant decision timed alone; load 50-60):

  | variant | F hand end p99 | cand | F act p99 | cand | F variant p99 | cand |
  |---|---|---|---|---|---|---|
  | swap_one_turn | 142.6 us | 143.1 | 112.0 | 103.1 | 33.6 (mean 25.0) | 181.8 (mean 119.7) |
  | deal5_keep2 | 134.6 | 136.4 | 93.3 | 92.9 | 53.5 (mean 41.8) | 61.8 (mean 45.3) |

  All under 200 us. The swap is the one decision that costs: about 57 reads a turn per player still in, once a hand
  (F's variant times include the base Hero's pending ICM curve, which a lazy Hero computes in its first call of a hand).

## 6. The Ghost on more seeds, and the tests

- **The tax read on my own seeds** (50000-50199 x 8, outside every held-out and judge range; base F played on this
  branch): generic_aware +0.346 ± 0.314 UP (F 11.516), realistic +0.346 ± 0.287 UP (F 11.370). **Pooled with the
  screen set, 400 seeds: generic_aware +0.267 ± 0.218 UP, realistic +0.264 ± 0.202 UP.** Hero told the twist both times.
- **Tests**: tests/test_vi_voi.py (12: the option tables, the parts, dials off as before, the bid's multiplier and
  caps, the bonus buy rule and its pot, the swap equal to the full enumeration, keep and discard, the composite handing
  over its observation, the mean shares and tax tiers, the gate open on the Ghost only and shut on all 26 catalog
  entries, the tax's call and thin-value moves, F playing the decision twists and the Ghost with both dials on).
  Full suite at load 50-60: 31 failed, 1319 passed, 13 skipped. Three were mine and are fixed (3b031f5: Hero kept its
  last observation across tables, which tests/test_lifetime.py catches twice; CONTRACTS.md lacked the four Config
  keys). The other 28 are wall-clock and budget tests at this load (14 bestiary budgets, rival 1's strict-mode
  timeouts, kit D's round trip, a cold setup, eight model-mode replay tests of the exploit and outside fields, two
  drill and gate runs that pass on a rerun): the replay, rival 1 and drill ones checked on main's worktree fail there too.
- **Identity again at the final code** (3b031f5): the same 14 chunks equal main's.

## What I would still try

- **The swap with a finer value.** The turn table keys by Hero's tier, which puts two pair on a paired board with
  top pair good kicker; a 32-sample quick simulation was no more accurate at twice the cost. A turn table keyed by the
  made category with both hole cards (or the kicker's rank) would stop the few bad kicker swaps.
- **The bid against the field's bids.** Bids are public after the auction (`extras["bids"]`): the second price is
  what we pay, so a read of the seats' bids (abh-win's marginal-EV bid against the opponent's empirical bids) could
  bid just over the field rather than a multiple of the value.
- **The tax beyond the mean.** One number prices every hand alike; the Ghost taxes a pair 56% and a straight 7%. A
  prepared table of the tax by made category (the hooks can score it as the value shares are scored) would tax one-pair
  calls harder and leave the strong hands' raises alone; and bluffs, which a haunt never touches, could go up.
- **Untold twists.** The tax read needs the twist's name to find its table; on the night we write the variant file and
  name it, but a kit that does not tell Hero gets F.

## Runs (screen set unless named; no held-out set, judge or held-out variant)

| run | seeds | result |
|---|---|---|
| base F, main eecf4d8: aware (7 + Ghost x2), variants (26, partly) | 10000-10199 | sections 3-4 (reused) |
| identity, b1f8ab9 and 3b031f5 | 10000-10039 | 14/14 chunks equal to main, twice |
| aware, voi 1.0 (7 cells), sd_tax (Ghost x2), voi 0.67 and 1.5 (auction, bonus_card) | 10000-10199 | section 3 |
| variants, the candidate: 6 entries at 200, 20 at 40 | 10000-10199 / -10039 | section 4 |
| the final spec on the aware cells' first chunk | 10000-10024 | equal to the assembled cells |
| latency, swap_one_turn and deal5_keep2, F and the candidate | latency.py's seed | section 5 |
| Ghost tax, my seeds | 50000-50199 | section 6 |
| full test suite | - | section 6 |
