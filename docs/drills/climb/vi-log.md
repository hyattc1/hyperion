# V-i: twist decisions priced as value of information, and the showdown tax read (2026-11-03)

Branch climb/vi-twist-value, from main eecf4d8. Item 14 of docs/research/Edges against strong opponents.md
(competitions §5: value the twist's decision as an EV difference by quick simulation, scale by a fudge factor; GTO
Wizard's MIT 2024 auction entry bid the 3v2 - 2v3 equity difference x 1.8, the best of 0.5-2.5x). Seeds: the screen set
(10000-10199) for every measurement, my own for diagnostics (777 / 50000+ / 2026). No held-out set, judge bot or
held-out variant was run, read or tuned on. Host shared (load 14-18 of 8 cores): `nice -n 5`, at most three worker
processes. Scratch scripts: the session scratchpad, `goal/vi_work/scripts/`.

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
