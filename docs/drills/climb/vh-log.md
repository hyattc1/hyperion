# V-h: cards an opponent is known to hold, ours included, priced as his (2026-11-02)

Branch climb/vh-known-cards, from main e736e7c. Drill 9's twist (kit G, Chain Hold'em) gave every player one
private card and a "link" card shared with each ring neighbour: you know one card of each neighbour, and heads-up two
of the opponent's three. Our bot played the links as private, and the drill's player found no dial for it. This
branch adds the general capability: known opponent cards, some of them our own, come in through the observation's
extras, and Hero prices them as his. Seeds: the screen set (10000-10199) and my own (50000-50199; kit G seed 1, tables 0-2399). No
held-out set, judge bot or held-out variant was run. Host shared (load 7-25): `nice -n 5`, two worker processes, one
run at a time. Scratch scripts: the session scratchpad, `goal/vh_work/scripts/`.

## Findings

**Candidate: `{"hero.known_cards": "pre"}`** (off by default; F plays bit-identically without it, and with it everywhere
but where known cards exist). Chain in our sim +1.06 ± 0.58 (realistic) and +0.73 ± 0.48 (generic aware), both
beyond noise up; kit G +0.28 ± 0.83, level; exposed_card +0.19 and +0.15, both up. `"pre,post"` is the alternative:
a little higher in our sim, behind `pre` in the kit; not recommended.

1. **What was wrong.** Hero's only path for an opponent's cards was exposed_card's `extras["exposed"]`, and it had
   no idea a known card could be ours too. Fed a shared card, it (a) put our own card in the opponent's
   `Spot.exposed`, so the preflop reads took our high link behind us as his high card (steals x0.85 each) and moved
   the shove-call margin by our own card's rank; (b) left the hand class untouched: the preflop class is the dealt
   hand's (a pair of links is a premium pair heads-up, though he holds the same pair); (c) left the postflop read
   untouched: top pair made with a shared card read as top pair, though against that neighbour it is a pair on the
   board. Dead cards were fine (the outs skip a dead card that is in our hand). Hero has no Monte Carlo on the
   decision path, so the "equity" here is the class tables before the flop and the tier read after it. The generic
   aware opponents never saw the links either (no key carried them).
2. **The change** (`hyperion/strategy/known.py`, dial `hero.known_cards`, off by default). `extras["known"]` =
   {seat: cards}, or {viewer: {seat: cards}} when one dict serves every seat as in our sim; `extras["exposed"]` joins
   it. Against one opponent known to hold K: K and our hole are *shared* (a board card between us), K minus our hole
   is *exposed* (his), our hole minus K is what separates us. Two parts:
   - `pre`: heads-up before the flop (one opponent left in the hand), the hand is read as the class whose heads-up
     equity is ours against him: a prepared table of that equity (his hand = the shared cards + his exposed ones +
     random cards; best five of all) by a suit-invariant key, then the nearest class of the table set in play. Three
     shapes are prepared (tables/known_*.json, 5,083 keys each, 6,000 samples, about a minute each at two workers):
     Chain heads-up (1 private card, 2 shared), Chain against one neighbour (2 and 1), exposed_card heads-up (2
     against 1 face-up card). The exposed-card range reads stand down for that decision (the class already prices his
     card). Any other showdown (must-use, lowball, wild, short deck, two boards) keeps the dealt class.
   - `post`: after the flop, against each opponent in the hand who shares cards with us, the hand is read with the
     shared cards on the board (`Postflop.read_shared`): two separating cards through the hold'em read on the longer
     board (draws while cards come); one (Chain heads-up) through the share of his possible cards it beats now, read
     as the hold'em tier whose hands beat that share (calibrated on 1,500 random hold'em hands a street). The lowest
     read over the opponents is the hand's; when every opponent shares cards, the plain read is left out (it prices
     the shared cards as ours alone). Facing a bet a shared read is not given the three-card call shift (the pairwise
     read already is his hand on the same board).
3. **Chain, our sim: `pre` is the lever, beyond noise up on both fields.** F + `pre`: +1.06 ± 0.58 against the
   realistic field (the drill's rules, the deal file with the links reported), +0.73 ± 0.48 against generic aware
   opponents (400 seeds), who now hold our links in their neighbours' hands too. `post` on its own is level (+0.34 ±
   0.57), and on top of `pre` it adds +0.12 ± 0.62 and +0.17 ± 0.51: nothing measurable. The first `post` (the
   lowest of the plain and the shared reads, always) only ever read lower and measured +0.02; leaving the plain read
   out when every opponent shares cards moved it to +0.34.
4. **Kit G's own simulator agrees on the sign, not the size.** The player's entry and adapter, the adapter now
   passing the links as known cards, packed `--slim` three times (dials {}, `pre`, `pre,post`; each carries the
   three tables), against seven of the kit's Chain-aware bots, paired by table: `pre` +0.28 ± 0.83 (2,400 tables at
   5 ms limits) and +0.48 ± 1.53 (800 at the real 1 ms); `pre,post` -0.24 ± 0.84 and +0.34 ± 1.51; with two of our
   seats in the kit's mixed field, `pre,post` +0.68 ± 0.82. Nothing beyond noise either way; `pre` is ahead of F in
   every kit cell, `post` is not. As V-g found on kit F, the kit's field shrinks what our fields show. Two cautions
   on these runs: the host ran at load 13-25, and under load the composite's own clock (deadline 0.8 ms, its
   degrade and panic levels) changes how it plays, so the same zip on the same tables is not the same game twice
   (a rerun of F on tables 800-1599 made 128 decisions a table, against 178 the first time); the kit pairs poorly
   for that reason (an interval of ±0.83 at 2,400 tables). And the candidate zips ran late more often in the batches
   (0.4-0.7% against 0.2% at 5 ms), each of which ran F first and the candidates later as the load rose: the
   mixed-field pair, run back to back, is level (0.16% and 0.17%), latency.py's replay shows no added cost, and the
   one decision-time cost the change had, reading a prepared table on its first use, now happens at a table start
   (4b919fb; it plays the same: 50 Chain seeds, sample lists equal).
5. **exposed_card does not lose; it gains, beyond noise.** The same dial (there are no shared cards there, so `pre`
   and `pre,post` play alike) prices our two cards against his face-up card plus one: +0.186 ± 0.066 against
   realistic and +0.148 ± 0.078 against generic aware (screen set, 200 seeds, linear points). The exposed-card
   range reads (steals x0.85 per high card behind, the shove margin by the shover's card) stand down only in the
   heads-up spots the class now prices.
6. **Identity.** With the dial off, F on this branch plays main's F bit for bit: `climb_accept --cand '{"dials":
   {}}' --set 10000:10040 --stages confirm,guards` in a detached worktree on e736e7c and here, sample lists equal on
   all 7 cells. With the dial on (`pre,post`), F + dial against F on the same seeds: identical sample lists on the 7
   hold'em cells and on 25 of the 26 catalog variants (`--stages variants --variant-seeds 40`); exposed_card is the
   one that moves (+0.152 ± 0.158 on those 40 seeds). `pre` alone is the same code with the post reads off, and
   those never run without shared cards, so the same holds for it.
7. **Latency stays in budget.** `tools/latency.py --hand-end --reps 3`, p99 of the per-call minimum, F then F +
   `pre,post`: hold'em act 108 / 107 us, hand end 141 / 142 us (the protocol's check: under 200); Chain act 104 / 107
   us, hand end 367 / 338 us (Chain's hand end is over 200 us on F already: three-card tables, not this change);
   exposed_card act 88 / 105 us (mean 48 / 55: every decision there now reads the eight face-up cards through
   `known.parse`), hand end 137 / 140 us. The heads-up class is a dict lookup and a bisect; the one-card shared read
   is about 45 evaluations, on heads-up Chain flops, turns and rivers only.

## The numbers

Our sim: `climb_accept`'s cells (model mode, eight rotations a seed, paired by seed; the interval is 95% of the
per-seed difference), run through `goal/vh_work/scripts/cells.py` for cells the stages do not name. "realistic" is
the realistic field under the drill's rules (`docs/drills/drill9/rules_tonight.json`: three_card_keep's tables, kit
G's blinds and points) with the Chain hooks (`--variant docs/drills/drill9/chain_variant.py:variant`). "generic
aware" is `generic_aware` under the Chain file's own rules, with `hero.variant_tables: three_card_keep` on both arms so
Hero plays the tables it would play on the night (without it Hero plays a label view, which `pre` cannot read: there
`pre,post` measured +0.55 ± 0.76, the `post` part alone).

| Chain, our sim | seeds | F | F + pre | F + pre,post | F + post |
|---|---|---|---|---|---|
| realistic | 10000-10199 | 30.61 | +1.064 ± 0.580 UP | +1.186 ± 0.669 UP | +0.339 ± 0.567 |
| generic aware | 10000-10199 | 30.77 | +0.563 ± 0.743 | +0.728 ± 0.879 | -0.234 ± 0.782 (first post) |
| generic aware | 50000-50199 | 30.34 | +0.901 ± 0.613 UP | +1.072 ± 0.843 UP | |
| generic aware, both | 400 seeds | 30.55 | +0.732 ± 0.481 UP | +0.900 ± 0.608 UP | |

pre,post against pre: realistic +0.122 ± 0.618, generic aware (400) +0.168 ± 0.511. No timeouts, errors or
illegal actions in any cell.

| exposed_card (`climb_accept --stages variants,aware`, screen set; no shared cards, so pre,post plays as pre) | F | F + pre,post | |
|---|---|---|---|
| realistic | 6.167 | 6.353 | +0.186 ± 0.066 UP |
| generic aware | 6.134 | 6.282 | +0.148 ± 0.078 UP |

Kit G's simulator (`goal/vh_work/scripts/kit_paired.py`: the kit's own `run_tables`, our zip in one seat, per-table
points saved so two zips pair by table; seed 1, tables 0-799 and 800-2399), the late share is of our decisions:

| kit G field | limits | tables | F | F + pre | F + pre,post | chain bots (F's table) |
|---|---|---|---|---|---|---|
| us + 7 chain | 1 ms | 0-799 | 25.19 (late 2.4%) | +0.481 ± 1.534 (3.2%) | +0.344 ± 1.508 (3.4%) | 15.4 |
| us + 7 chain | 5 ms | 0-799 | 24.61 (0.18%) | +1.218 ± 1.432 (0.41%) | +0.344 ± 1.419 (0.23%) | 15.5 |
| us + 7 chain | 5 ms | 800-2399 | 25.24 (0.17%) | -0.192 ± 1.023 (0.47%) | -0.529 ± 1.048 (0.69%) | 15.4 |
| us + 7 chain | 5 ms | 0-2399 | 25.03 ± 0.63 | +0.278 ± 0.833 | -0.238 ± 0.844 | 15.4 |
| us x2 + chain x2, tight x2, station, random | 5 ms | 0-799 | 27.35 (0.16%) | | +0.682 ± 0.824 (0.17%) | chain 20.6, tight 15.5 |

No errors in any kit run.

Latency (`tools/latency.py --hand-end --reps 3`, per-call minimum, p99 us, load 13.5):

| rules | act F | act F + pre,post | hand end F | hand end F + pre,post |
|---|---|---|---|---|
| hold'em | 107.7 | 107.1 | 141.3 | 142.4 |
| exposed_card | 87.5 | 104.5 | 136.9 | 139.9 |
| Chain (drill rules + hooks) | 104.3 | 106.6 | 366.7 | 338.3 |

## What I would still try

- **Read his range by the card we know.** The organiser's notes: "a neighbour who raises while holding your deuce has
  made the raise with his other two cards." The class prices his hand as random around the known cards; a raiser's
  range narrowed through his known card (the preflop module's shove-range width, conditioned on it) is the next lever.
- **Beyond heads-up.** `pre` reads only spots with one opponent left. Facing one raiser who shares a link, with
  others still to act, the class could blend the two equities; three-handed both opponents share a card each.
- **Our own exposure.** Our neighbours see our links. Hero does not yet bluff less into a player who sees a card of
  ours, or value-bet more when the card he sees is a blank.
- **`post` with the opponent's range.** The shared reads are right about what beats what, but level in both
  simulators; the heads-up one-card read could weigh his possible cards by his betting (only about 44 of them) rather
  than counting them evenly, and its tier cuts are a first calibration.
- **Kit G's points at the cap** (chips rank at hand 200, not ICM): untouched here.
