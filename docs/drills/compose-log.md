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

## 14:59: the screen on night (the primary field; 200 x 8, seeds 0-199, the final night field 003ca48)

Base hybrid3_x 5.748 ± 0.116 (the field agent's number on the same field: 5.75). The night fields replay exactly once
agent_montecarlo and agent_pushfold run at fixed speed (swap.py; fbbac19 makes it the engine's model mode, the same
settings).

| section | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| pre_open_40 | hybrid3 -0.020 | rival3 -0.020 | hero -0.034 | r2x -0.078 | rival1 -0.097 (worse) |
| pre_open_20 | hybrid3 -0.020 | rival3 -0.020 | rival1 -0.034 | hero -0.037 | r2x -0.087 (worse) |
| pre_open_10 | hybrid3 +0.002 | rival3 +0.002 | r2x -0.003 | hero -0.005 | rival1 -0.009 |
| pre_open_short | hero -0.003 | hybrid3 -0.004 | r2x -0.013 | rival3 -0.016 | rival1 -0.066 (worse) |
| pre_raised_deep | hybrid3 0 | rival3 -0.006 | r2x -0.073 | rival1 -0.114 | hero -0.135 (worse) |
| pre_raised_short | hero +0.063 ± 0.070 | hybrid3 0 | rival3 -0.003 | rival1 -0.007 | r2x -0.041 |
| pre_allin | hybrid3 0 | rival3 -0.022 | r2x -0.025 | rival1 -0.042 | hero -0.069 (worse) |
| pre_3way | rival3 -0.005 | hybrid3 -0.007 | r2x -0.020 | rival1 -0.032 (worse) | hero -0.033 (worse) |
| pre_hu | rival3 -0.001 | hybrid3 -0.002 | hero -0.011 | r2x -0.029 (worse) | rival1 -0.040 (worse) |
| post_hu_bet | **hero +0.086 ± 0.086** | hybrid3 0 | rival3 -0.004 | r2x -0.005 | rival1 -0.094 (worse) |
| post_hu_chk | r2x -0.020 | hero -0.021 | rival1 -0.072 | rival3 -0.157 (worse) | hybrid3 -0.162 (worse) |
| post_mw | hero +0.013 | rival3 +0.009 | hybrid3 +0.007 | r2x -0.004 | rival1 -0.044 |

The same two Hero swaps lead as on realistic: facing a heads-up postflop bet (+0.09, just outside noise) and facing a
raise short (+0.06, inside). Everywhere else the base is first or level. The layer is worth +0.16 when checked to.

**Hero ties hybrid3_x on night overall (field agent: -0.01 ± 0.12), yet Hero's single-section swaps sum to about
-0.19 here.** The sections do not add up: Hero's deep preflop ranges (-0.14 facing a raise) are built to go with its own
postflop play. So the matrix is also being run with Hero as the base (every section Hero; each section swapped to the
hybrid3_x base, hybrid3, r2x, rival1, rival3, or Hero without the layer), on night and night_hard. Greedy combining
then starts from whichever base the two matrices favour.

**The ship rule has changed (coordinator, 14:50).** The composite must beat both hybrid3_x and Hero beyond noise on
night. It must not be worse than either beyond noise on night_hard, realistic and top. It must not lose to either on the
judge fields, measured once at the end. If no composite clears that, the log reports which of Hero and hybrid3_x is
better on night and the judges, and no composite ships. night_hard carries ~1.9 strong seats a table, mostly rivals 1-2,
which Hero was tuned on, so it partly favours Hero by construction. Where night and night_hard disagree, night and
judge2_night (untuned opponents) weigh more.

## 15:31: the screen with Hero as the base (night, 200 x 8, seeds 0-199)

Every section on Hero (bit-identical to Hero: 5.754 ± 0.113; hybrid3_x 5.748 on the same deals). Each cell swaps one
section to a donor: `base` = the hybrid3_x core with the layer, `hybrid3` = without it, `hero_nl` = Hero without the
layer.

| section | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|
| pre_open_40 | **r2x +0.114 ± 0.083** | base +0.026 | rival1 +0.003 | rival3 -0.001 | hybrid3 -0.001 | hero_nl -0.019 |
| pre_open_20 | base -0.011 | hero_nl -0.026 | rival3 -0.027 | hybrid3 -0.027 | rival1 -0.029 | r2x -0.029 |
| pre_open_10 | base +0.021 | rival1 +0.010 | hybrid3 +0.007 | rival3 +0.007 | r2x -0.007 | hero_nl -0.036 |
| pre_open_short | rival1 +0.015 | hybrid3 +0.008 | r2x +0.007 | base +0.005 | hero_nl +0.002 | rival3 +0.001 |
| pre_raised_deep | **base +0.138 ± 0.110** | **hybrid3 +0.138** | **rival3 +0.116** | rival1 +0.054 | hero_nl 0 | r2x -0.027 |
| pre_raised_short | rival1 +0.004 | hero_nl 0 | r2x -0.036 | rival3 -0.040 | hybrid3 -0.041 | base -0.041 |
| pre_allin | r2x +0.045 | base +0.027 | hybrid3 +0.027 | rival1 +0.004 | rival3 +0.002 | hero_nl 0 |
| pre_3way | base +0.019 | hybrid3 +0.003 | rival3 +0.002 | r2x -0.002 | rival1 -0.018 | hero_nl -0.027 (worse) |
| pre_hu | base +0.008 | rival3 +0.005 | hybrid3 +0.002 | hero_nl -0.013 (worse) | r2x -0.026 (worse) | rival1 -0.038 (worse) |
| post_hu_bet | hero_nl 0 | r2x -0.123 (worse) | base -0.185 (worse) | hybrid3 -0.185 (worse) | rival3 -0.213 (worse) | rival1 -0.253 (worse) |
| post_hu_chk | r2x -0.016 | base -0.056 | rival1 -0.093 (worse) | rival3 -0.172 (worse) | hybrid3 -0.172 (worse) | hero_nl -0.203 (worse) |
| post_mw | r2x +0.001 | hero_nl 0 | rival1 -0.013 | base -0.014 | rival3 -0.016 | hybrid3 -0.019 |

**The two matrices agree on the two biggest sections.**
- Facing a deep preflop raise, rival 3's core beats Hero by about 0.14 from either base (+0.138 here, -0.135 the
  other way).
- Facing a heads-up postflop bet, Hero beats it: +0.086 from the hybrid3_x base, +0.185 here.
- Facing a raise short, Hero is ahead of the core from both bases (+0.06 there, +0.04 here).

Rival 2's deep opens help only behind Hero's postflop play (+0.11 here, -0.08 behind the core's). Opening ranges and
the postflop play behind them go together, which is why single swaps do not add up.

**The owner's other bot as a donor** (black box, scratch only, the snapshot matching its current dist md5 07f2f6ed,
night, hybrid3_x base): it wins no section. It is worse beyond noise in 7 of 12 sections (pre_raised_deep -0.20,
post_hu_bet -0.24, post_hu_chk -0.27) and level in the other five. Nothing of it is shipped or combined.

## 15:40-15:55: greedy combination on night (screen seeds 0-199, 200 x 8)

Every route is measured once, as one composite, and paired on the same deals against both hybrid3_x and Hero
(tools/swap.py `joint`: the rotations where the route can differ from the base run are replayed; here that is
1465-1600 of 1600). These seeds are the screen's, so the numbers carry selection bias. The pick is confirmed on fresh
seeds 1000-1399 next, and the final check uses held-out seeds 5000-5399, used once.

Round 1, the screens' leading swaps combined:

| # | route (sections not named: the hybrid3_x base) | points | - hybrid3_x | - Hero |
|---|---|---|---|---|
| 1 | **postflop all Hero, pre_raised_short Hero** | 5.971 | **+0.223 ± 0.113** | **+0.217 ± 0.118** |
| 2 | post_hu_bet Hero, pre_raised_short Hero | 5.896 | **+0.148 ± 0.099** | **+0.142 ± 0.121** |
| 3 | every section Hero but pre_raised_deep (the base) | 5.892 | **+0.144 ± 0.124** | **+0.138 ± 0.110** |
| 4 | post_hu_bet + post_mw Hero, pre_raised_short Hero | 5.890 | **+0.141 ± 0.107** | **+0.135 ± 0.118** |
| 5 | as 3, pre_open_40 r2x | 5.863 | +0.115 ± 0.122 | **+0.109 ± 0.104** |
| 6 | as 5, pre_allin r2x | 5.847 | +0.098 ± 0.121 | +0.092 ± 0.107 |

Round 2, one more change to route 1 (paired against route 1):

| # | change to route 1 | - route 1 | - hybrid3_x | - Hero |
|---|---|---|---|---|
| 1 | pre_open_short Hero | +0.023 ± 0.039 | +0.246 | +0.240 |
| 2 | pre_open_10 Hero | +0.014 ± 0.060 | +0.236 | +0.230 |
| 3 | pre_hu Hero | -0.007 ± 0.011 | +0.216 | +0.210 |
| 4 | pre_open_20 Hero | -0.016 ± 0.071 | +0.206 | +0.200 |
| 5 | pre_allin Hero | -0.027 ± 0.055 | +0.196 | +0.189 |
| 6 | pre_3way Hero | **-0.035 ± 0.029** | +0.188 | +0.182 |
| 7 | post_hu_chk r2x | -0.045 ± 0.095 | +0.178 | +0.172 |
| 8 | pre_allin r2x | **-0.050 ± 0.045** | +0.172 | +0.166 |
| 9 | post_mw back to the base | -0.055 ± 0.073 | +0.167 | +0.161 |
| 10 | pre_raised_short back to the base (postflop Hero only) | **-0.077 ± 0.064** | +0.145 | +0.139 |
| 11 | pre_open_40 Hero | -0.080 ± 0.100 | +0.142 | +0.136 |
| 12 | pre_open_40 r2x | -0.093 ± 0.100 | +0.130 | +0.123 |

**Nothing improves route 1 beyond noise, so the greedy stops there.** The pick ("P") is rival 3's core and the layer
preflop, Hero facing a raise when short (under 20 bb effective), and Hero and the layer postflop. Each of its three
parts pays: postflop facing a bet (+0.09 alone), postflop checked to (+0.08 on top), and the short raise spot (+0.08 on
top). Hero's checked-to play loses alone (-0.02) but pays once Hero also plays the bets: the two halves of a postflop
strategy fit together.

## 15:51-16:05: P confirmed on fresh seeds (1000-1399, 400 x 8, model mode, code 4bbd794)

P = `post=hero,pre_raised_short=hero` (every other section on the hybrid3_x base). Full runs, the three bots paired
on the same deals; these seeds were never used to choose anything.

| field | P | Hero | hybrid3_x | P - hybrid3_x | P - Hero | Hero - hybrid3_x |
|---|---|---|---|---|---|---|
| night | 5.954 | 5.764 | 5.756 | **+0.199 ± 0.077** | **+0.191 ± 0.083** | +0.008 ± 0.093 |
| night_hard | 5.496 | 5.313 | 5.308 | **+0.188 ± 0.089** | **+0.183 ± 0.087** | +0.005 ± 0.100 |
| realistic | 6.342 | 6.075 | 6.150 | **+0.192 ± 0.074** | **+0.268 ± 0.083** | -0.076 ± 0.088 |
| top | 5.034 | 4.788 | 4.921 | **+0.112 ± 0.084** | **+0.246 ± 0.086** | **-0.134 ± 0.094** |

P beats both bases beyond noise on all four fields. Its gain on night (+0.20) is the screen's (+0.22) less a little
selection bias. Latency in these model runs (load 3-8): P p50 / p99 69 / 257 us, hybrid3_x 39 / 154, Hero 29 / 111. P
runs both members on every decision. Strict-mode timing and the variant matrix come next, then the climb from P.
