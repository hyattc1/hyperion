# Held-out variants: implementation log (2026-11-01)

Five variants we did not prepare for, implemented as a **held-out catalog**: a test set nobody tunes on. They measure how
the shipped bot, and a bot adapted in a rehearsal, cope with a twist outside our 23 entries. The spec (handout text and
exact engine rules) was written by a fresh agent that knew only our 23 names; it is not in the repo. This log maps each
engine rule to what was built.

- Module: `hyperion/drills/variants_unseen.py` (`HELD_OUT`, `names()`, `get()`). Not in `variants.CATALOG`, `PRESETS` or
  `catalog_names()`, so no screen, matrix default, drill or climb loop picks them up. No entry carries a Config patch.
- Run one: `python -m hyperion.sim --variant river_of_blood --field realistic@ship --tables 50 --seed 30000 --mode model --rotate`
  (`variants.get(NAME)` falls back to the held-out module, so every tool that takes a variant name reaches them).
  All five through the matrix: `python tools/variant_matrix.py --unseen --seed 30000 --tables 50` (it measures Hero, as
  it does for the 23). List / show: `python -m hyperion.drills.variants_unseen --list | --show NAME`.
- The goal plan's protocol: measured only on the judge seeds 30000-30399, once per accepted batch.

## The five

| entry | faithful? | how it is represented |
|---|---|---|
| river_of_blood | faithful, one modelling choice | a red river deals one more board card and a full betting round, repeated until a black card; showdown is the best five of hole + every board card (`evaluate_many`). The bots' own `core.eval` on 9+ cards is played as a 1 ms timeout (below). Street numbers are our round index (4, 5, ... for run cards), not MIT's board length |
| showtime | faithful except event delivery | a fold puts the folder's hole cards in `obs.extras["revealed"]` / `["dead_cards"]` for every later observation and in `HandResult.extras["revealed"]`; a fold with nothing to call is a check. No event channel: a bot that already folded sees the reveals at hand end |
| high_chicago | faithful | the engine's split-pot path with two columns (best hand, highest hole spade); `HandResult.extras["pots"]` reports each pot's winners and amounts |
| bomb_pot | faithful | hands 5, 10, ... 200: no blinds, a 2 bb ante from everyone (a contribution, so side pots form), no preflop round, first decision on the flop; `obs.extras["bomb_pot"]` |
| unfold | approximated in two places | the buy-back is the engine's existing variant decision (`variant_decide({"decision": "unfold", ...})`), not a new action kind; refunds are paid at hand end, not at the flop |

### 1. river_of_blood (`RiverOfBloodHooks`)

| spec engine rule | implemented |
|---|---|
| Dealing: after the river round, a red last card deals one more card and a round; repeat until black; flop and turn colours ignored | `next_card(street, board, deck, rng)` after the last street of `Rules.board_sizes`: returns a card while `board[-1]` is a diamond or heart, None on a club or spade. The run is popped from the hand's undealt cards, shuffled with the table's variant rng at the deal, so it depends only on (seed, hand): duplicate rotations see the same run (tested), and folds never change later hands' deals |
| Streets: MIT numbering 0, 3, 4, 5, 6, ... (street = board length); each run street a full no-limit round, min bet 1 bb, first to act left of the button | Our `Observation.street` is the betting-round index (0 pre, 1 flop, 2 turn, 3 river), so run streets are 4, 5, ...; `len(obs.board)` is MIT's number. Each run street: bets reset, min raise-to = 1 bb, first live seat left of the button (tested). `Rules.board_sizes` stays (0, 3, 4, 5); nothing says a street is final |
| Termination: the run cannot exhaust the deck | an engine assert at 64 streets and a RuntimeError if the deck ran out (never seen) |
| Showdown: best five of 2 + N board cards; the evaluator must take more than 7 cards | `evaluate_many`: `core.eval.evaluate` up to 8 cards; past 8, best flush / straight flush per suit mask and best non-flush from rank counts, each looked up in the 5-card tables. Tested equal to `evaluate_slow` on 1,100 random 5-14 card sets |
| All-ins: the rest of the board, run included, dealt with no betting | yes (tested) |
| Folds: the hand ends at once, no more cards | yes: the engine only asks for a card while two or more are in (tested) |
| Told: each card as usual; no final-street flag | yes |

**Spec numbers, checked** (tests): P(extra card | river reached) in 0.45-0.55, mean board 5.8-6.1, mean run 1.75-2.1 cards
(12 tables x 200 hands of check-down); a spade flush draw on a red river completes in the run 0.42 +- 0.025 and a heart
draw 0.27 +- 0.025 (8,000 conditioned deals each, the spec's setup: two suited hole cards, seven opponents, a board with
exactly two of the suit and a red river).

**What differs: the bots' evaluator past 8 cards.** Every bot evaluates hole + board with `core.eval.evaluate`, which
builds a lookup table for each new hand size lazily, inside the call: 0.8 s at 8 cards, 3.0 s at 9 (measured), about x3
per extra card, hours and gigabytes by 14-15 cards, and boards of 12+ cards come up a few times per thousand river hands.
Left alone, a 50-table run would stall for hours. `RiverOfBloodHooks()` therefore installs `install_eval_guard()`: a
9+ card evaluation raises `EvaluatorLimit`, which the bot's SafeBot or the engine turns into a check or fold, as a
1 ms engine would treat a multi-second decision. It is slightly pessimistic (a bot whose process survived the first build
would be fast at that size afterwards). `RiverOfBloodHooks(guard_bot_eval=False)` leaves the bots to build the tables.
The engine's own showdown never uses the guarded path.

Found while doing it: **the ship bot never reaches that guard.** Hero, which plays every postflop decision of the
composite, has its own rule: `hole + board > 8 cards -> check or fold` (`hyperion/strategy/hero.py`, `act`). So on a
board of 7 or more cards the ship checks or folds every decision, a made flush included (probed: Ah Jh on
Kc 7d 3s 9h 4h Qh 8c facing a bet folds), and no error is counted anywhere. The field's Monte Carlo bots do hit the guard
(engine exceptions in the smoke run).

### 2. showtime (`ShowtimeHooks`)

| spec engine rule | implemented |
|---|---|
| A fold (any street, timeouts and illegal actions included) reveals both hole cards until the hand ends | engine hook `on_fold(seat, hole, street)` after each fold; the observations after it carry `extras["revealed"] = {seat: hole}` and `extras["dead_cards"]` (sorted). A fresh dict each time, so earlier observations keep their snapshot (tested). An exception facing a bet is a fold and reveals (tested) |
| A fold when checking is legal is a check and reveals nothing | `free_fold_checks = True`: the engine plays it as a check and records a check (tested) |
| Uncontested pot: the winner does not show | yes (`HandResult.showdown` is empty, the winner is not in `revealed`) |
| Showdown unchanged | yes |
| Everyone folds to the big blind: 7 hands revealed | yes (tested) |
| Revealed cards never return to the deck | they are never re-dealt in a hand (no draws in this variant) |
| Told: each fold event, with cards, to every bot in the hand, those that folded included; the cumulative map per decision; every revealed and showdown hand at hand end | the map per decision: yes; at hand end `HandResult.extras["revealed"]` plus `showdown`. **Differs:** this engine has no events, so a bot that has already folded learns the later reveals only at hand end, and a live bot learns a fold at its next decision |

### 3. high_chicago (`HighChicagoHooks`)

| spec engine rule | implemented |
|---|---|
| Each pot (main and side) settled separately among its eligible players | the engine's existing split-pot path (`score_splits` -> [hand strength, highest hole spade rank or None]) |
| Spade half floor(P/2), high half P - floor(P/2) | the engine splits each pot over the two columns with the remainder to column 0, the hand: the same (tested on a 33-chip pot: 16 / 17) |
| High half to the best hand, ties split, odd chips per the base rules | yes (tested: three-way tie on a broadway board) |
| Spade half to the highest hole spade, board spades never count, no ties | yes (tested) |
| No hole spade among the eligible: the whole pot to the best hand | a column nobody qualifies for goes to column 0's winners: yes (tested) |
| A scoop is possible; a spade winner who ties the high takes both | yes (tested) |
| Uncontested pots never split | yes (tested) |
| Side pots: a short all-in can win only the main pot's spade half; each side pot's spade half to its own highest spade | yes (tested: A-spades all-in for 100 takes 150 of the 300 main pot, K-spades takes 200 of the 400 side pot) |
| Told: per pot, the high winner(s), the spade winner or "none", the amounts | `HandResult.extras["pots"]`: amount, high_winners, high_amount, spade_winner (None), spade_amount, uncontested |

### 4. bomb_pot (`BombPotHooks`)

| spec engine rule | implemented |
|---|---|
| Hands whose 1-based number divides by 5 (40 of 200), any table size | `hand_no % 5 == 4` (0-based), heads-up included (tested) |
| No blinds; everyone dealt in antes 2 x the current big blind; a stack at most the ante is all-in for it; the ante is a contribution (side pots) | engine hook `forced_bets` -> {"ante", "blinds": False, "preflop": False}; the engine's ante path puts the ante in `contrib` and the pot (tested: a 30-chip stack is all-in for 30, chips conserved, all-in from the ante deals out with no decisions) |
| Button moves as usual; next hand's blinds follow the button; no missed blinds | yes (tested) |
| No preflop round; flop dealt at once; postflop normal NL, min bet 1 bb, first to act left of the button | yes (tested: first decision on street 1, empty history, bets all 0, min raise-to 20, first seat left of the button) |
| Told at hand start: bomb_pot, the ante, the pot, no blinds posted; first request on the flop | `obs.extras = {"bomb_pot": True, "ante": 40, "blinds_posted": False}` on every decision of a bomb pot, `{"bomb_pot": False}` otherwise; `obs.pot` holds the antes; `obs.blinds` stays the level's (it is the minimum bet; a (0, 0) there would divide by zero in every bot's stack_bb). The schedule is in `Rules.extras` (bomb_every, bomb_ante_bb). There is no hand-start message in this engine: the first observation is the hand start |

### 5. unfold (`UnfoldHooks`)

| spec engine rule | implemented |
|---|---|
| Only with 4+ players dealt in | yes (tested: off at 3) |
| After the blinds, each player dealt in posts ceil(bb/4) into a separate unfold pot; not a bet, call or side-pot contribution; a stack below the ante after its blind posts none and cannot unfold | engine hook `after_forced(table, hand)`: the hook takes the ante from the stack and holds it; `obs.pot` never includes it (tested: a 22-chip big blind posts no ante, cost 25) |
| Main pot won preflop: every ante refunded, no unfold phase | yes (tested) |
| Phase right after the flop, before flop betting: each preflop folder who posted and has the cost behind is asked once, Unfold or Pass; cost = total antes; simultaneous; timeout = Pass | in `on_street(1)` through `ask(seat, {"decision": "unfold", "hole", "board", "cost", "unfold_pot", "eligible"})` -> the bot's `variant_decide`; True or "unfold" unfolds, anything else passes (no method, None, an error, a strict-mode overrun). Asked one at a time, nobody sees another's answer (tested: prompts, cost 30 with six players, no prompt to live players) |
| Fewer than two unfold: everything refunded | yes, **paid at hand end** (see below) |
| Two or more: they pay into the unfold pot; the unfolded seats are announced before flop betting | yes: `obs.extras["unfolders"]`, `unfold_status = "running"`, `unfold_pot` (tested) |
| Main hand continues; unfolders never act again; the board is dealt to five even if the main pot is decided early | yes: unfolders are folded seats; `settle` runs after the main award and uses the five-card runout; `HandResult.board` shows the five cards (tested) |
| Unfold showdown: best hand among unfolders takes the whole unfold pot; ties split, odd chips per base rules; their hands shown | yes; `HandResult.extras["unfold"]` has the hands, winners and amounts (tested) |
| A player can bust by unfolding and losing | yes (tested) |
| Told: hand start (active, ante, pot); after the flop a separate decision request; then the unfolded seats or "refunded"; hand end the unfold showdown | `obs.extras` {unfold_active, unfold_ante, unfold_pot, unfold_cost, unfold_status, unfolders}; the request is `variant_decide`; `HandResult.extras["unfold"]` |

**What differs.** (1) The spec's new decision type (UnfoldAction / PassAction delivered to a folded seat) is the decision
channel the catalog already has (`variant_decide` with a prompt), outside the betting loop. Bots with no `variant_decide`
pass, as the spec's timeout does; the ship bot has one and answers None (pass) to a prompt it does not know. (2) A refund is
paid at hand end rather than at the flop. The final chips are the same; the difference is that a stack all-in preflop
stays all-in. Paying it at the flop gave such a stack its 5-chip ante back mid-hand, betting reopened, and a raiser whose
excess nobody covered could then fold it away (the engine's award only pays levels of players still in, so those chips
vanished: found by the conservation test, fixed by moving the refund).

## Engine changes (`hyperion/sim/engine.py`, `hyperion/core/types.py`)

Optional hooks, each None / False on the base `Variant` and bound by `HooksVariant` only when the hooks object has the
method, so every other variant and default play never call them:

- `forced_bets(hand_no, blinds, n_in_hand) -> dict | None`: this hand's ante, whether blinds are posted, whether there is
  a preflop round (bomb_pot).
- `after_forced(table, hand)`: after the blinds (unfold's antes).
- `next_card(street, board, deck, rng) -> card | None`: an extra street after the last one, with its betting round
  (river_of_blood). In `play_hand` this is a `for ... else` after the street loop, so it runs only when two or more are
  still in after the river.
- `on_fold(seat, hole, street)` with the observation extras recomputed after it, and `free_fold_checks` (showtime).
- `settle(table, hand)`: after the main award, before the deltas (unfold).
- `result_extras(hand) -> dict` into the new `HandResult.extras` (default `{}`: every existing bot and adapter that
  builds or reads a HandResult is unchanged; CONTRACTS.md does not list HandResult, so the API card is unchanged).

`hyperion/drills/variants.py`: `get()` falls back to the held-out module for a name not in the catalog.
`tools/variant_matrix.py`: `--unseen`; `--only` accepts held-out names.

## Checks

**Default play is bit-identical.**

- The requested run, `python -m hyperion.sim --field night@ship --mode model --tables 20 --seed 1 --rotate`, is not
  reproducible on this host even with no code change: two runs on the base commit gave ship 5.868 and 5.862 (the other
  seats moved too). After the change it gave 5.899. The ship bot reads the wall clock (the composite's late-shadow cut,
  rival 3 core's soft deadline, SafeBot's overrun count and panic), and the host was at load 6+ from other agents, so its
  decisions vary from run to run; model mode fixes the field bots' speed, not the ship's. (HANDOFF says model-mode night
  runs replay exactly; that holds for the field, not for `@ship` on a loaded host.)
- So the check that decides is the same run with every clock the bots read advancing 1 ns per call (no deadline can
  fire): `det_run.py` (scratchpad), run on a worktree of the base commit 519dce1 and on this branch. Output (every
  seat's per-seed samples, places, busts, hands) **md5 cdcfcaf1c2500d81ee1b3cd911fc2e0b on both**, before the engine
  change, after it, and at the branch head; ship 5.872189, 28,304 hands. Two concurrent runs of the base also matched,
  so the script itself is deterministic under load.
- In the suite: `test_default_play_is_bit_identical_to_the_engine_before_the_hooks` hashes every hand's deltas, board and
  actions plus final points over default Rules, a straddle, antes, fixed limit and three catalogued hooks (bonus_card,
  two_boards, hi_lo), 42 tables; the expected hash was computed on 519dce1.

**Tests** (`tests/test_variants_unseen.py`, 36): held out (not in the catalog, reachable by name, the CLI and the matrix
flag), legality and chip conservation per entry (every observation's invariants with unfold money counted, every action
legal, no exceptions, chips conserved every hand), and each entry's own rules as listed above.
Full suite on the branch: `.venv/bin/python -m pytest -q`: 833 passed, 1 skipped (296 s).

## Smoke run (not tuning input)

`python -m hyperion.sim --variant NAME --field realistic@ship --tables 50 --seed 30000 --mode model --rotate`, through a
wrapper that calls the same `runner.main` and then prints the composite's silent fallbacks (`fallback:error` when a
member raised, `hero:core_error` when rival 3's core raised and Hero decided), which the report's exc / safe_err columns
cannot see. 400 tables per entry. Rank is among the field's 8 bot names.

| entry | ship pts (±95%) | rank | ship errors: engine exc / SafeBot / composite fallbacks | second | notes |
|---|---|---|---|---|---|
| (plain hold'em, same seeds) | 6.291 ± 0.196 | 1 / 8 | 0 / 0 / 0 | rival1 5.760 | reference, not a variant |
| river_of_blood | 6.363 ± 0.195 | 1 / 8 | 0 / 0 / 0 | rival1 5.460 | montecarlo 385 and montecarlo30 401 engine exceptions (the 9+ card guard) |
| showtime | 6.228 ± 0.198 | 1 / 8 | 0 / 0 / 0 | rival1 5.763 | |
| high_chicago | 6.299 ± 0.202 | 1 / 8 | 0 / 0 / 0 | rival1 5.811 | |
| bomb_pot | 6.332 ± 0.184 | 1 / 8 | 0 / 0 / 0 | rival1 5.693 | |
| unfold | 6.291 ± 0.215 | 1 / 8 | 0 / 0 / 0 | rival1 5.680 | the unfold game never ran (below) |

Timeouts (tmo) 0 and illegal actions 0 for the ship on every entry. SafeBot's wall-clock overrun counter (safe_over,
not enforced in model mode) read 166 on plain and 230-333 on the entries: host load, not the variants. The
differences from plain are all inside the intervals, and the runs are not paired (a variant changes the deals' play),
so read them as "the ship plays every entry without breaking", not as a variant cost.

Probes behind the notes (20 tables x 8, same seeds): on river_of_blood the ship made 92 decisions with 9+ cards out of
28,333 (85 checks, 7 bets from the exploit layer, which needs no evaluator) and about 1% of its decisions on run
streets (street 4: 213, 5: 58, 6: 20, 7-9: 14). On unfold, of 29,452 hands: 8,386 off (under four players), 10,940 won
preflop (refunded), 10,126 refunded after the phase, 0 with two or more unfolders.

## Findings for the coordinator

1. **The ship plays all five without an error and finishes first on each, level with plain hold'em.** That is a weak
   test: the field is not variant-aware either. Two entries are nearly inert against this field. Showtime: no bot reads
   `extras["revealed"]`, so the only change is that a fold with nothing to call becomes a check. Unfold: no bot in the
   field answers the unfold prompt (the ship's `variant_decide` returns None for a decision it does not know), so the
   unfold game ran on no hand. Both start measuring only with a rehearsal-adapted bot or variant-aware opponents in the
   field.
2. **River of Blood: on a board of 7+ cards the ship checks or folds every decision, the nuts included.** Hero, which
   plays the composite's postflop, returns check-or-fold when hole + board > 8 (its guard against the evaluator's
   8-card limit). Whether it plays a red river as the last street was not measured. Rare here
   (0.3% of its decisions) because it is in few pots that reach the run; in a variant-aware field that bets the run
   it would be folding made hands.
3. **`core.eval.evaluate` past 8 cards is a 1 ms timeout on the night.** It builds each new hand size's table inside
   the call: 3.0 s at 9 cards (measured), about x3 per card. Any bot adapted for River of Blood needs a many-card
   evaluator; `evaluate_many` (in the held-out module) is one, tested against brute force. If rehearsals should find
   their own, do not point the rehearsal agent at it.
4. **`--field night@ship --mode model` does not replay exactly on a loaded host.** Two runs of the same commit gave the
   ship 5.868 and 5.862; the composite's late-shadow cut, rival 3 core's soft deadline and SafeBot's overrun counter
   read the wall clock. HANDOFF's "model mode replays exactly" holds for the field bots. Paired runs in the climb's
   protocol carry this noise when the host is busy; a 1 ns-per-call clock (as `det_run.py` does) removes it.
5. **The catalogued hooks that draw from the undealt deck draw from an unshuffled tail** (`deck.pop()` in SwapHooks,
   SwapOneHooks, TwoBoardsHooks, BonusCardHooks). The engine shuffles only the cards it deals (a partial
   Fisher-Yates), so the tail keeps the deck's order until enough hands have mixed it: board 2's first card on two_boards
   is the ace of spades in 60% of seeds on hand 0, 36% on hand 1, 7% on hand 5 (uniform is 3%; mixed by about hand 20).
   Not changed here, since that would move the catalogued numbers; the fix is the held-out hooks' way (shuffle the
   hand's spare cards at `on_deal`, then pop).
6. **The engine's award loses chips in one shape that default play never reaches.** `_award` pays only up to the
   contribution levels of players still in, so chips a folded player put in above every remaining player's
   contribution are not paid to anyone. In standard play the uncovered bettor never acts again, so it cannot fold. A
   variant that gives chips back mid-hand can produce it (unfold did, until its refunds moved to hand end). Left as is,
   because changing `_award` touches the default path; a new hook that returns chips mid-hand must avoid it.
