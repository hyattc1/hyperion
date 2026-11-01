# Composite bot: running log

The compose phase (HANDOFF, 13:45): for each section of the game, find whether another bot's decisions beat the base's
(hybrid3_x: rival 3's core + the exploit layer behind Hero's shell), combine the winners, then a guarded hill climb.
Ship only if the composite beats hybrid3_x beyond noise on night and realistic and is not worse on any judge field.
Summary goes to docs/decisions.md, "Composite bot".

## 14:10 ET: the sections (hyperion/compose/sections.py)

Twelve sections, read from the Observation alone in about 1 us (0.87-1.0 us per call on this box, best of five passes
over 20,000 recorded decisions). Axes in the order they are read:

- **street:** preflop is 78% of hybrid3_x's decisions on realistic, and in a 200-hand turbo from 100 bb most of the points
  move there (opens, steals, re-shoves, calling all-ins under ICM).
- **postflop:** by players in the hand. Multiway (3+) is 2-4% of decisions, so it is one section; a heads-up pot splits
  on whether we face a bet, because the exploit layer's bet-when-checked-to acts only when nothing is to call.
- **alive, preflop:** heads-up (2 alive) and three-handed (3) are their own sections: ICM and ranges change most there.
- **what we face, preflop:** unopened (blinds and limps), a raise we can re-raise, or an all-in (the raiser is all-in,
  calling costs my stack, or no raise is legal).
- **effective stack** (min of my chips and the biggest other stack still in the hand, this street's bets included):
  < 10 / 10-20 / 20-40 / 40+ bb for unopened pots, < 20 / 20+ facing a raise.

Shares of hybrid3_x's decisions, model mode, 50 seeds x 8, in Hero's seat (%):

| # | section | realistic | top | strong |
|---|---|---|---|---|
| 0 | pre_open_40 | 23.4 | 19.2 | 20.0 |
| 1 | pre_open_20 | 8.8 | 8.8 | 9.6 |
| 2 | pre_open_10 | 4.4 | 6.8 | 8.2 |
| 3 | pre_open_short | 1.3 | 3.1 | 3.6 |
| 4 | pre_raised_deep | 18.5 | 23.6 | 22.6 |
| 5 | pre_raised_short | 2.8 | 6.2 | 6.5 |
| 6 | pre_allin | 3.1 | 6.6 | 5.4 |
| 7 | pre_3way | 8.7 | 4.8 | 4.6 |
| 8 | pre_hu | 6.9 | 3.2 | 3.5 |
| 9 | post_hu_bet | 6.2 | 4.9 | 5.2 |
| 10 | post_hu_chk | 12.1 | 9.7 | 9.1 |
| 11 | post_mw | 3.7 | 2.9 | 1.8 |

Every section holds at least 1.3% of decisions on every field. Decision share is not points share: a section's weight in
the swap matrix shows up as the size of its paired delta. Tests: tests/test_compose_sections.py.

## 14:50: the composite bot (hyperion/compose/bot.py) and the swap tool (tools/swap.py)

**Members and donors.** A route maps each section to a donor: a member bot and whether the exploit layer acts there.

| donor | member | layer | is, with every section on it |
|---|---|---|---|
| base | rival 3's core behind Hero's shell | on | hybrid3_x |
| hybrid3 | the same | off | hybrid3 |
| hero | Hero's HeroCore | on | Hero as it ships |
| r2x | rival 2's core behind the shell | on | hybrid_x |
| rival1 | rival 1 as built, kit adapter | off | rival1 |
| rival3 | rival 3 as built, kit adapter | off | rival3 (brief's payouts, no shell) |

- **The layer sits in front of the whole composite, one instance.** It observes every decision and replaces a passive
  action only where the donor has it on. It reads only the table, so one copy per member would read the same and cost
  ~6 us each. "Layer off in section X" is the donor `hybrid3` in X.
- **Every member in the route acts on every observation and gets every hand_end.** The members not chosen compute
  their decision too, and it is discarded. Rival 3 keeps one fact about its own past ("I raised preflop", which raises
  its flop bluff rate). When its answer was not the action taken, that flag is set from the action that was. Every
  other member reads its state from the history.
- **Only the route's members are built,** plus the base, which answers variant prompts and plays where a raw rival
  cannot: Hero's 14 variant tables, permuted ranks, straddles (counted `fallback:plain`).
- **Errors.** A failing chosen member gives the base's answer; a failing shadow is ignored; a late chosen member skips
  the shadows (`late_us`, off in deterministic runs).

**Both directions verified on real tables** (model mode, panic and soft deadlines off; per-decision sha1 in Hero's seat
plus every seat's points; tests/test_compose.py):

| route | against | result |
|---|---|---|
| every section `base` | hybrid3_x | bit-identical, with and without every other member shadowing |
| every section `hybrid3` | hybrid3 | bit-identical |
| every section `hero` | Hero | bit-identical, with every other member shadowing |
| every section `rival3` | rival3 in Hero's seat | bit-identical, shadows on |
| every section `rival1` | rival1 (strong; realistic already seats it) | bit-identical, shadows on |
| every section `r2x` | hybrid_x | differs: rival 2's sampler stops on the wall clock. With its budget lifted (32 samples always) both are bit-identical |

Members never change the observation (deep copies before and after every call, every member shadowing).

**The swap tool's exact shortcut** (tools/swap.py). The base run plays the base route with every member shadowing.
For each (table seed, rotation) it records which (section, donor) cells ever disagree with the action taken in their
section. A rotation where the donor agrees at every decision of its section follows the base's trajectory exactly, so
only disagreeing rotations are replayed. Checked against full replays: 0 mismatches over 5 cells x 48 rotations, plus a
test. It also measures any combined route (the union of its cells' rotations).

For determinism every run fixes rival 2's sampler at a sample count: opponents 110 (its host-speed average heads-up),
the r2 member 32. That is a fixed-speed rival 2; the final measurement plays it as built.

How often a donor's action differs from the base's on the first 6 seeds of realistic (rotations out of 48 with at least
one difference): Hero, rival 1 and rival 2's core differ in nearly every rotation in the big preflop sections. Raw
rival 3 differs from the base only where the payout correction moves an all-in price (7-15 of 48), and never facing a
postflop bet. The layer-off donor differs where the layer fires (41 of 48 in post_hu_chk).
