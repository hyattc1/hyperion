# V-g: Ghost Hold'em in our sim, and does our sim transfer to an engine we did not write? (2026-11-02)

Branch climb/vg-ghost, from main d18b2fa. Drill 8's twist (kit F, Ghost Hold'em, written by a fresh organiser agent of
ours) is the first engine we did not write. The climb rests on one assumption: a change our sim measures as better is
better in the organisers' engine. This log tests it on kit F. Seeds: the screen set (10000-10199) for our sim, my own
seeds for the rest (kit F 801-806, diagnostics 555000+ and 777000+). No held-out set, judge bot or held-out variant was
used. Host shared (load 11-14 of 8 cores): every run `nice -n 5`, two worker processes, one run at a time. Scratch
scripts are in the session scratchpad (`goal/vg_work/scripts/`), not in the repo.

## Findings

1. **Our sim transfers to kit F when the field is the same.** I seated the same eight-bot field in both engines (our
   bots behind drill 8's adapter in kit F's simulator; "field B" below). On it the two engines agree on every
   candidate's sign and size, within noise: c2 +0.23 (ours) and +0.31 (kit F), both beyond noise up; c1 +0.04 and
   -0.04; c3 +0.01 and +0.02; c4 -0.02 and -0.19 (both level). F's own score is 11.17 and 11.35 there.
2. **Across fields the sizes do not hold; the field is why.** Against kit F's own sample bots (three `ghostwise`, two
   `tight`, a station and a random bot: "field K1", 9,600 tables) all four are level: c1 -0.005, c2 +0.055, c3
   +0.014 (± 0.135), c4 -0.02 (± 0.24, 3,200 tables). Our sim on our fields: c2 +0.09 to +0.52, c3 +0.01 to +0.20,
   c1 0.00 to +0.26, c4 about 0. The signs agree (nothing is down anywhere); the sizes shrink to zero on kit F's
   field. The same engine shows it: in kit F, c2 is +0.31 on field B and +0.06 on K1. The other suspects do not
   explain it: the twist (with and without the Ghost our sim ranks the four alike), scoring at the cap (both engines
   place by chips, and with ICM at the cap our sim gives the same deltas), timing (kit F's timeouts are 0.4-0.5% of
   decisions, equal across the candidates, and F with no time limit scores the same). See section 2.
3. **The drill's Stage 5 verdicts were noise.** The player measured c2 -0.9, c3 -0.5, c4 -0.24 (± about 0.5, 160-400
   tables). With 3,200 to 9,600 duplicate tables per candidate, paired by deal, none of the four is beyond noise in
   field K1, and c1's first 3,200 tables (-0.22 ± 0.23) went to -0.005 ± 0.135 at 9,600. Kit F's simulator at a few
   hundred unpaired tables cannot see a 0.3-point change.
4. **The Ghost fits our hooks; no engine change was needed for the twist.** `hyperion/drills/ghost_example.py`:
   `on_deal` deals the Ghost, `after_forced` puts the Haunt into the pot as dead money, `settle` replaces the award
   with kit F's. Checked against kit F's dealer on 20,000 random showdowns (side pots, folds, dead money, the "never
   ends a table" rule): 0 mismatches. One general engine option was needed for kit F's other rule: survivors at the
   hand cap placed by chip count (`Rules.extras["cap_places"] = "chips"`). Every existing table is bit-identical.
5. **The prepared twist tables did not price the Ghost; now they do.** `--prepare` dealt and scored through the
   hooks but never called `settle`, so the Ghost's table was plain hold'em (AA 0.852). Generic rollouts now price a
   `settle` hook through the engine's own award on a probe hand: AA 0.738, 22 0.315, 87s 0.346, where kit F's
   organiser table says 0.738, 0.310, 0.346. General for any payoff hook; no catalog entry has `settle`, so every
   catalog table and generic field is unchanged.
6. **The general path still does not find the Ghost's edges for F.** Batch 5's twin dials do nothing here: the
   Ghost's twins move hands by 0.042, under the dial's 0.05 gate (F + the dials plays bit-identically to F). With the
   gate at 0.035 the twins engage and gain nothing (+0.09 ± 0.10, -0.02 ± 0.08): on this table the composite's base
   (rival 3's core) plays the preflop and has its own hand classes, so the twins reach only Hero's sections. The
   Haunt hand needs nothing new: the base already widens its steal when obs.pot carries dead money. The showdown tax
   (thin value and one-pair calls) has no general read; c2, hand-made tighter calls, is the closest thing we have.
7. **A packaging bug that only an engine we did not write could show.** Kit F's loader deletes a bot's modules from
   `sys.modules` after `Agent()` returns and takes its folder off `sys.path`. Every import inside a function then fails
   with "No module named 'hyperion'". F's normal path has none (40 tables, nothing swallowed), but the twin dials
   import lazily at table start: every table start failed, silently (Adapter.start swallows it). Fixed in the
   Adapter: it pins its own package's modules when built and puts them back at each call. See section 3.

8. **A bot that keeps its reads across tables may be worth points in kit F.** The twin zip packed before the fix
   (every table start failed, so the base core, its exploit layer and the Hero member never reset between tables)
   scored +0.45 ± 0.26 over F in field K1. Kit F keeps one Agent and the same opponents for a whole session; our
   runner builds fresh bots for every table, so our sim cannot measure this at all. See section 3.

## 1. The Ghost as a variant file

`hyperion/drills/ghost_example.py` (`:variant`, registered by path as every tool takes it). The hooks:

- `on_deal` pops two cards from the undealt, shuffled spare cards: never on the board or in a hand, the same for
  every rotation of a duplicate table.
- `after_forced` moves last hand's haunted chips (`carry`) into this hand's pot (`hand.pot`, so obs.pot shows it, as
  kit F's `s.pot` does) and publishes it as `obs.extras["haunt"]` (kit F's `s.haunt`). It is no one's contribution.
- `settle` rebuilds the pots from the contributions the way kit F's dealer does (a layer only one player paid goes
  back; a layer with nobody eligible joins the pot below), adds the Haunt to the main pot, checks each pot with two
  or more eligible players against the Ghost, and writes the stacks; if haunting would leave nobody with chips it pays
  without the Ghost. The haunted chips become `carry`. A Haunt left at the table's end goes with the hooks.
- `result_extras` reports the Ghost (at a showdown), each pot and its winners, the chips haunted.

Kit F's other rules are in `docs/drills/drill8/rules_ghost.json` (drill 8's `rules_tonight.json` plus
`"extras": {"cap_places": "chips"}`): blinds 10/20, 15/30, 25/50, 40/80, 60/120, 100/200, 150/300, 250/500 every 25
hands, points 16/11/8/6/4/2/1/0, chip-count places at the cap. That file does not name the variant, so Hero is not
told a twist is on, as kit F's packed bot was not. The variant's own Rules (`ghost_rules()`) are the same plus
`"variant": "ghost"`, which the generic bots and Hero's twin tables need.

**The engine option.** At the hand cap our engine gave survivors ICM equity on their stacks; kit F places them by
chips (equal counts share the places' points). `Rules.extras["cap_places"] = "chips"` does that
(`Table._place_by_chips`); Hero reads the key as hold'em (`_HOLDEM_EXTRAS`), so its play does not change. Identity:
`tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, sample lists of all 14 cells
equal to main's, after the engine change and again at the branch head (every change in hyperion/ in).

Minor differences from kit F, not modelled: the first button (kit F: a random seat), two players busting in one hand
from exactly equal stacks (kit F: they share the places), and the preflop call when the big blind is all-in short
(kit F: the full big blind).

**Validation.**

| check | kit F | ours |
|---|---|---|
| settle against kit F's dealer `_settle`, 19,992 random synthetic showdowns (5,449 haunted) | - | 0 mismatches |
| P(the Ghost beats your hand) by category, 400k river spots: high card / pair / two pair / trips / straight / flush / full house / quads | 81.6 / 56.3 / 30.5 / 23.9 / 6.9 / 11.3 / 6.1 / 4.2 | the same |
| random showdown haunts, 2 / 3 / 4 players | 31.9 / 23.5 / 18.7% | 32.0 / 23.5 / 18.7% |
| eight stations, 2,000 tables: haunted showdowns | 15.1% | 15.2% |
| ... chips per haunt / Ghost KOs per table / chips discarded per table | 975 / 1.16 / 465 | 969 / 1.16 / 476 |
| ... tables over before hand 200 | 12% | 10% |
| field B with F, 3,200 tables (ours 480): haunted showdowns / chips per haunt | 23.0% / 2,066 | 22.8% / 2,129 |
| ... showdowns per table / Ghost KOs per table / tables over before hand 200 | 13.8 / 2.34 / 74% | 14.3 / 2.32 / 76% |
| field K1 with F, 3,200 tables (drill 8's R1 and R2: 22.1%, 22.9%) | 24.6% / 1,584 | - |

The 2-point gap in early finishes with stations is about two standard errors; kit F's full-big-blind call against a
short big blind moves more chips in multiway all-ins; that is my guess at the cause, not measured.

`tests/test_ghost.py`: chips kept every hand (stacks plus the carried Haunt), a haunted pot paid to the next hand's
winner by fold, the Haunt riding in a showdown's main pot and haunting again, the Ghost never ending a table, a side
pot haunting on its own, chip-count places with a tie, the generic pricing (below) and the Adapter's re-pin.

## 2. Sim-to-kit transfer

**Method.** Our sim: tools/climb_accept.py's cells (model mode, 8 rotations a seed, paired by seed), screen seeds
10000-10199, 1,600 tables a cell. Kit F: its own `engine.sim.run_session` (duplicate seating, cpu clock, one entry of
ours in slot 0) called by a scratch harness that keeps each table's points, so a candidate pairs with F by deal (one
deal = 8 rotations); seeds 801-802 (3,200 tables), plus 803-806 for F, c1, c2, c3. Each zip from `tools/pack.py
--slim --entry docs/drills/drill8/bot.py --extra docs/drills/drill8/adapter.py docs/drills/drill8/rules_tonight.json
--dials '<dials + late_us 0>' --max-mb 5`, run with Python 3.10 as the sandbox is. F is the ship's dials with
`{"late_us": 0}`; the candidates are drill 8's c1-c4 on top of that. Intervals are 95%, paired.

Fields:
- **night, realistic**: ours, Hero not told the twist (`rules_ghost.json`), the Ghost hooks on.
- **generic**: `generic_aware` under the variant's own Rules (so Hero is told; the generic bots need the name).
  "main" is main's generic bots, which played the Ghost as hold'em; "fixed" is after section 4's change.
- **field B**: `tag, gen_mc, gen_pushfold, loose_aggro, rival1, gen_tag, pushfold` and our seat, the generic bots
  told the Ghost's Rules, Hero not told. The same bots in kit F through drill 8's adapter (`goal/vg_work/kitbots/`).
  `generic_aware` without its two bots whose play depends on the clock (montecarlo30, timeout_then_recover).
- **K1**: kit F's sample bots, drill 8's R2 shape: our seat, ghostwise x3, tight x2, station, random_bot.

**The table** (candidate minus F; UP = beyond noise up):

| | c1 survival | c2 tighter calls 0.3 | c3 passive | c4 tighter calls 0.1 |
|---|---|---|---|---|
| ours, night (F 10.03) | +0.003 ± 0.179 | +0.087 ± 0.228 | +0.139 ± 0.188 | +0.025 ± 0.095 |
| ours, realistic (F 11.39) | +0.051 ± 0.157 | +0.179 ± 0.225 | +0.201 ± 0.176 UP | +0.000 ± 0.078 |
| ours, generic, main (F 10.91, told) | +0.257 ± 0.200 UP | +0.523 ± 0.232 UP | +0.174 ± 0.184 | -0.007 ± 0.086 |
| ours, generic, fixed (F 11.35, told) | +0.223 ± 0.188 UP | +0.301 ± 0.218 UP | - | - |
| **ours, field B** (F 11.17) | +0.044 ± 0.196 | **+0.234 ± 0.224 UP** | +0.011 ± 0.121 | -0.021 ± 0.110 |
| **kit F, field B** (F 11.35) | -0.043 ± 0.212 | **+0.313 ± 0.220 UP** | +0.022 ± 0.214 | -0.185 ± 0.223 |
| kit F, field K1, 3,200 tables (F 8.88) | -0.218 ± 0.234 | +0.033 ± 0.247 | +0.063 ± 0.225 | -0.024 ± 0.237 |
| **kit F, field K1, 9,600 tables** (F 8.85) | **-0.005 ± 0.135** | **+0.055 ± 0.137** | **+0.014 ± 0.134** | - |
| drill 8's player, kit F (160-400 tables) | level | -0.9 | -0.5 | -0.24 |

Controls in our sim (same seeds):

| | c1 | c2 | c3 | c4 |
|---|---|---|---|---|
| night, no Ghost (F 9.69) | +0.121 ± 0.186 | -0.119 ± 0.245 | -0.052 ± 0.180 | -0.077 ± 0.112 |
| realistic, no Ghost (F 10.85) | +0.117 ± 0.181 | +0.301 ± 0.241 UP | +0.167 ± 0.200 | +0.044 ± 0.095 |
| realistic, Ghost, Hero told (F 11.34) | +0.024 ± 0.157 | +0.133 ± 0.217 | +0.181 ± 0.171 UP | -0.036 ± 0.084 |
| realistic, Ghost, ICM at the cap (F 11.37) | +0.042 ± 0.154 | +0.108 ± 0.221 | +0.191 ± 0.171 UP | - |

**Why K1 differs.** The four suspects, one at a time:
- *The engine and the twist*: field B holds the field fixed and changes everything else at once (the dealer, the
  Ghost, the adapter, the clock), and the verdicts match. F's absolute score matches too (11.17 and 11.35, inside the
  noise of a mean).
- *The twist inside our sim*: with and without the Ghost the four rank alike (realistic c2 +0.30 without, +0.18 with;
  c3 +0.17 and +0.20); the Ghost moves F's own score (+0.5 on realistic) far more than the candidates' deltas.
- *Scoring at the cap*: both engines place by chips in every row above. With ICM at the cap instead (our old rule,
  drill 8's `rules_tonight.json`) our sim gives the same deltas (+0.04, +0.11, +0.19 against +0.05, +0.18, +0.20).
- *Timing*: kit F's cpu clock timed out F on 0.38% of decisions in K1 and 0.53% in B, the candidates within 0.03
  points of F. F with no time limit at all (`--limit-us 200000`, 0 timeouts) scored -0.11 ± 0.24 against F with the
  limit: the timeouts cost nothing we can see.
- *The field*: what is left, and the same engine shows it (c2 +0.31 on field B, +0.06 on K1, both in kit F). c2
  tightens calls (r3.call_margin 0.3, push and shove-call margins, Hero's postflop call margin 0.3). My guess at the
  mechanism, not measured: our bots bet and raise into F often enough that folding more pays; in K1, `tight` bets only
  top pair or better (folding to it saves little that F was not already folding), the station and the random bot
  rarely make F fold anything, and `ghostwise` stabs small pots and Haunt hands, where folding gives up dead money.

So the climb's assumption holds for the engine: a change our sim measures on a field transfers to kit F on that
field. It does not hold across fields, and the organisers' field is unknown. On the night, the field we measure on is
the risk, not our engine.

## 3. Kit F's loader and lazy imports

Kit F's `engine/loader.py` imports each bot, constructs it, then deletes from `sys.modules` every module whose file is
in the bot's folder (so two bots can each ship a `utils.py`) and removes the folder from `sys.path`. Hero imports some
modules inside functions (`from .tables import generic_doc` in `_twins`, the latency governor, ...). After the loader
returns, each such import raised `ModuleNotFoundError: No module named 'hyperion'`. The ship bot never hit one in 40
kit tables (a scratch harness counting what SafeBot and the entry swallow: nothing). Batch 5's twin dials hit one at
every table start: Hero's `new_table` stopped in `_configure`, and `Adapter.start` swallowed it, so the bot played
every table on the last table's state. The kit printed "new_table failed" to stderr, nothing else.

Fix (`hyperion/drills/adapter.py`): `pin_package()` records this copy's `hyperion` modules when an Adapter is built
(inside `Agent()`, before the loader unloads them); `repin_package()` puts them back at the top of `start`, `decide`
and `hand_end` when `sys.modules["hyperion"]` is gone or another copy's. One dictionary lookup a call when nothing is
wrong. Our sim never uses the Adapter, so no table there changes.

| kit F, K1, 3,200 tables | vs F told (8.78) |
|---|---|
| F + batch 5's twin dials, packed without the fix: every table start failed | +0.448 ± 0.260 UP |
| F + batch 5's twin dials, with the fix (plays as F in our sim) | +0.108 ± 0.246 |

The broken bot did better, beyond noise. What the failure skipped: the composite's table start stops at the first
member (the base's fallback Hero), so the base's rival 3 core, its exploit layer and the Hero member never reset
between tables; their reads of opponents (by relative seat) carry over the whole session. The told rules' preflop
patch (`hero.variant_preflop`) is never applied either, but told and not told are level here (F told minus F:
-0.095 ± 0.257). So in kit F a bot that keeps its reads across tables gained about 0.45 against the sample field,
even with the reads keyed by the wrong seats. That is the organiser notes' point 7 (`t.ids` is the same all session;
`ghostwise` learns across tables), and our sim cannot measure it: the runner builds fresh bots for every table, and
the Adapter ignores `t.ids`. Not proposed as is (a broken table start is not a candidate); see the last section.

## 4. The general path on the Ghost

**Do the prepared tables price the haunt? They did not.** `python -m hyperion.sim.generic --prepare
hyperion/drills/ghost_example.py:variant` dealt every class from the deal through the hooks (`on_deal` is overridden,
so not the hold'em reference), but the rollout scored the showdown with `score_hand` and `on_payout` only. `settle`
was never called: AA 0.852, 22 0.504, 87s 0.476 (plain hold'em), twin shift 0.0185 (sampling noise).

**The fix** (`hyperion/sim/generic.py`): when the hooks have `settle`, each runout's showdown goes through a probe
hand: the contenders' contributions (mine, each opponent as much, the rest of the pot dead money every contender is
eligible for), the engine's own `Table._award`, then `HooksVariant.settle`; my share is what my stack gained over the
pot. Such hooks run on the dynamic path (state reset and spare cards per runout), and `holdem_cards()` is False for
them. General for any payoff a hook applies after the award (a pot to nobody, a side game). The probe costs about 16 us
a runout heads-up (2.5 us without), so gen_mc still affords 15 runouts heads-up and 10 three-handed. Also: a variant
file's table key no longer depends on the repo's absolute path (`_hooks_id`). No catalog entry has `settle`, every
catalog key is unchanged, and `generic_aware` under wild_deuces, two_boards and bounty (10000-10039) is bit-identical.

The Ghost's table after the fix (`tables/generic/ghost-421005b3.json`, 4,000 hands a class):

| class | ours | kit F's organiser table |
|---|---|---|
| AA / KK | 0.738 / 0.694 | 0.738 / 0.692 |
| AKs / QJs | 0.517 / 0.450 | 0.513 / 0.444 |
| 44 / 33 / 22 | 0.373 / 0.339 / 0.315 | 0.366 / 0.336 / 0.310 |
| 98s / 87s / 65s | 0.356 / 0.346 / 0.301 | 0.364 / 0.346 / 0.311 |
| 72o | 0.226 | 0.213 |

Biggest risers in rank: 75s +25, 86s +23, 97s, T8s, J9o +22, 76s, 87s +21; fallers 22 -20, A4o -18, 33, Q4o, Q5o,
T2o -17. The organiser notes' edges (suited connectors up, small pairs down) are in the table. Twin shift 0.042.

**F with batch 5's twin dials** (`hero.twin_preflop` 0.05, `twin_multi` 0.07, the multi/must-use shifts,
`call_shift_ex` wild 2 deck 1), Hero told the twist (the twins need the variant's name):

| | vs F told |
|---|---|
| ours, generic (fixed) | +0.000 ± 0.000 (bit-identical) |
| ours, realistic | +0.000 ± 0.000 (bit-identical) |
| kit F, K1 | +0.108 ± 0.246 (with the Adapter fix; plays as F told) |

Bit-identical because the twins move hands by 0.042, under the 0.05 gate, and the other dials act only on three or
more hole cards or on a gate this table does not have. With the gate at 0.035 (the twins engage):

| | vs F told |
|---|---|
| ours, generic (fixed) | +0.094 ± 0.101 |
| ours, realistic | -0.022 ± 0.079 |

Not worth proposing. On this table the composite's base plays the preflop (rival 3's core: no showdown key in the
rules, so `table_reason` is None) with its own classes, and the twins reach only Hero's sections (postflop and short
stacks facing a raise).

**The generic opponents after the fix** read the Ghost (gen_mc's runouts and every bot's preflop twins). F scores
11.35 against them (10.91 against main's, which played hold'em); c1 and c2 stay up (+0.22, +0.30).

**Dead money (the Haunt hand).** Checked before adding anything: F's base already prices it. Its unopened branch
(`hyperion/hybrid/core3.py`) raises any hand up to 85% of the range when `ev_steal = pf * pot_tot - (1 - pf) * cost *
0.55` is positive, and `pot_tot` includes obs.pot, which carries the Haunt; facing a raise, pot odds include it too.
Measured in our sim (realistic, the Ghost, 240 tables, F's first-in decisions with more than 15 big blinds):

| dead money in the pot | decisions | F raises |
|---|---|---|
| none | 14,869 | 62.1% |
| under 3 bb | 86 | 65.1% |
| 3-10 bb | 101 | 80.2% |
| 10 bb or more | 236 | 85.6% |

F already opens wider the more dead money there is, up to the base's 85% cap. Nothing added.

**The showdown tax** (one pair loses to the Ghost 56% of the time, so thin value bets and one-pair calls lose) has no
general read in Hero: its postflop equity is hold'em's. c2 is the hand-made version: positive on every field of ours
(beyond noise on generic and field B), beyond noise up on field B in kit F, level on K1.

## What I would still try

- A general showdown-tax read: the prepared table's mean value share against one hand (0.501 in hold'em, 0.342 for
  the Ghost) is what a showdown pays. Hero could raise its call and value thresholds by it, gated on the table, so
  hold'em is unchanged. c2's gain on our fields says there is something there; field K1 says it depends on the room.
- Fields for the night that are not all ours: kit F's sample bots took c2's gain to zero. Our bots seat in a kit
  through the adapter in an evening (field B here); the reverse, a kit's own sample bots seated in our sim, would put
  them in every climb_accept cell as a second opinion on any candidate.
- Reads that last the session, keyed by the kit's player ids (`t.ids` here): the broken twin zip's +0.45 says it may
  be worth points in kit F. It needs our runner to keep bots across tables (as kit F does) before our sim can measure
  it, and a careful test, since the gain came with every other table-start reset skipped too.
- Make prompt 05 measure in the kit's simulator only paired by deal (the harness here, `goal/vg_work/scripts/
  kit_paired.py`), at 3,000+ tables: a few hundred unpaired tables decided drill 8's Stage 5 on noise.
- Kit F's short-big-blind call rule, if a future kit has it: it is the one difference left in the station check.
