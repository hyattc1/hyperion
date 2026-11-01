# Composite bot: running log

The compose phase (HANDOFF, 13:45): for each section of the game, find whether another bot's decisions beat the base's
(hybrid3_x: rival 3's core + the exploit layer behind Hero's shell), combine the winners, then a guarded hill climb.
Ship only if the composite beats hybrid3_x beyond noise on night and realistic and is not worse on any judge field.
Summary goes to docs/decisions.md, "Composite bot".

## 13:20 ET: the sections (hyperion/compose/sections.py)

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

## 13:50: the composite bot (hyperion/compose/bot.py) and the swap tool (tools/swap.py)

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

## 14:10: determinism of the screens

The shortcut and the pairing need every seat to replay exactly. Two runs of the same tables in one process, swap.py's
setup: realistic, strong and the eight timeout and weak bots replay exactly. Fields with rival 2 did not. Besides its
260 us budget, its postflop call passes a hard stop at t0 + 520 us, which a loaded host reaches. swap.py now lifts both
(110 samples always), and rival 2, `night` and every other field replay exactly. Rival 2's import-time equity tables
stop at 1500 boards or 2.4 s, so a worker that imported it on a host slow enough for the clock to bind would differ
from the others. swap.py warns when that happens. The first `top` base run was made before the fix, so it is redone.

## 14:26: the screen on realistic (200 seeds x 8, model mode, seeds 0-199)

Each cell = the composite with that one section played by the donor, the rest by the base (hybrid3_x), paired on the
same deals. Base hybrid3_x 6.133 ± 0.112. Bold = beyond the 95% interval. Ranked best first; "differs" is the share of
the section's decisions where the donor's action differs from the base's.

| section | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| pre_open_40 | hybrid3 +0.001 | rival3 +0.001 | r2x -0.007 | rival1 -0.045 | hero -0.086 |
| pre_open_20 | hybrid3 -0.012 | rival3 -0.012 | hero -0.038 | rival1 -0.072 (worse) | r2x -0.075 (worse) |
| pre_open_10 | hybrid3 -0.003 | rival3 -0.003 | hero -0.025 | rival1 -0.056 | r2x -0.086 (worse) |
| pre_open_short | rival3 -0.009 | hybrid3 -0.009 | r2x -0.010 | rival1 -0.014 | hero -0.020 |
| pre_raised_deep | hybrid3 0 (never differs) | rival3 -0.045 (worse) | rival1 -0.066 | hero -0.261 (worse) | r2x -0.290 (worse) |
| pre_raised_short | hero +0.045 ± 0.061 | rival1 +0.016 | rival3 +0.012 | hybrid3 0 | r2x -0.029 |
| pre_allin | hybrid3 0 | rival3 -0.003 | rival1 -0.022 | r2x -0.026 (worse) | hero -0.062 (worse) |
| pre_3way | hybrid3 -0.002 | rival3 -0.003 | r2x -0.042 (worse) | hero -0.045 (worse) | rival1 -0.055 (worse) |
| pre_hu | hybrid3 +0.001 | hero +0.001 | rival3 -0.001 | r2x -0.011 (worse) | rival1 -0.030 (worse) |
| post_hu_bet | **hero +0.173 ± 0.096** | hybrid3 0 | rival3 -0.020 | rival1 -0.024 | r2x -0.053 |
| post_hu_chk | r2x +0.023 ± 0.085 | hero -0.012 | rival3 -0.132 (worse) | rival1 -0.136 (worse) | hybrid3 -0.137 (worse) |
| post_mw | hybrid3 +0.024 ± 0.035 | rival3 +0.022 | r2x -0.019 | hero -0.050 | rival1 -0.075 |

Read:
- **One swap beats the base beyond noise on realistic:** Hero facing a heads-up postflop bet (+0.17 ± 0.10). Its
  postflop calls and raises differ from rival 3's core on a quarter of those decisions.
- Everywhere preflop the base's core is first or level. Hero's and rival 2's deep 3-bet / call ranges facing a raise are
  the worst swaps measured (-0.26, -0.29).
- **The layer's worth by section:** turning it off costs -0.14 in post_hu_chk (bet when checked to) and nothing
  measurable elsewhere. Off in post_mw is +0.02 ± 0.04, inside noise.
- Raw rival 3 and the layer-off base are the same donor wherever the payout correction does not move a price.
  Raw rival 3 differs from the base on 0.2-8% of decisions.

The screen's top base run was redone after the determinism fixes (14:10). Every later run uses a frozen worktree of
the tree at 80e3dd7, so other agents' edits cannot reach a run halfway. Realistic re-verified there: 10 base and 10
replayed rotations identical.
