# Prompt drill 9: Track A on kit G (raises from a pot-fraction menu, string actions), Chain Hold'em

Date 2026-11-02, T0 22:30:34 EST, stopped at minute 19 (22:50:16). The climb's third rehearsal, on batch 5's ship
(repo pinned at 512b31f).

**Set-up.**
- Kit G was built by a fresh organiser agent with no repo access (goal/drill9/kit; 38 tests, 500 tables clean). The
  interface: one Agent for a session (3 s setup, `begin_table` 20 ms, sit-out on overrun); `decide(s)` returns a
  string, "F", "C", "A" or a raise token from a menu of pot fractions ("R33" .. "R250", the dealer works out the
  chips); no legal list; cards 0-51; seats as offsets from us; a compact history string; `hand_over` timed at 1 ms (late:
  the next decision is check/fold). Points 50/32/21/14/9/5/2/0, chips at the cap. Handout:
  `docs/drills/drill9/kitG-README.md`.
- The twist, **Chain Hold'em**: each player has one private card, and one "link" card sits between every two
  neighbours (both hold it and see it). Three cards a player, best five of eight; you know one card of each
  neighbour, and heads-up both links are shared (nearly open-card). Organiser's notes:
  `docs/drills/drill9/kitG-ORGANISER-NOTES.md`.
- Player: a fresh subagent with the pinned repo, the handout without the organiser's notes, prompts 00-05 and the
  playbook; `timeout` on long commands.

## Key numbers

| Checkpoint | Drill 9 | Drill 8 | Drill 7 | Target |
|---|---|---|---|---|
| Rule sheet, axis, FIT VERDICT | minute 1 | 1 | 3 | 5 |
| First valid upload | minute 5 (cheap bot; gate minute 7) | 1 (insurance), cheap 6 | 8 | 12 (hard 15) |
| Ship bot gated and submitted | **minute 10** | 12 | 18 | 40 |
| Stage 5 | three candidates measured in our sim with a Chain deal file; none better: kept the ship | four, none | none | 50 |
| Stopped | minute 19 | 20 (stuck call) | 23 | 60 |

The axis was information (three hole cards, two of them shared); the committed three_card_keep tables loaded, so no
regeneration. The final zip (`02-ship.zip`, sha256 d179b697...0216c5, 1.0 MB slim) plays composite F with DIALS {} behind
the player's adapter; with three hole cards Hero plays the whole table.

**Under the real twist, in the kit's own simulator** (the player's runs, load 6-8):

| zip | field | tables | ours | the kit's bots |
|---|---|---|---|---|
| ship | seven Chain-aware sample bots | 100 | **24.46** [21.3, 27.6] | chain 15.51 |
| ship | mixed, we hold two seats | 100 | **28.41** [26.2, 30.6] | chain 18.89, tight 15.67, random 5.09, station 1.97 |
| cheap | mixed, two seats | 100 | 20.7 | chain 25.5 |

A seat averages 16.6 under these points. F with no Chain patch beats the organiser's Chain-aware bot by about 9 points
a table, and the cheap bot does not: the ship bot is worth about 8 points a table over Stage 2's.

## What slowed it down or broke (minutes lost first)

1. **Twist candidates with no lever (about 4 minutes).** Heads-up both links are shared, so only the private cards
   differ, but Hero prices a hand made by a shared card as if it were private. Its candidates (tighter calls, tighter
   value, a table re-cut) measured -0.16 to -1.13 in our sim with the player's deal file. An exact heads-up check
   would be 44 eight-card evaluations, about 7 ms: not a dial.
2. **Gate seat (about 3 minutes).** Kit G is none of the fake kits, so the player wrote `submission/gate_seat.py`. The
   gate's state has no streets or blind posts in its history, so the seat sends one street's log, and the gate never
   tests the adapter's per-street log parsing (only the kit sim did).
3. **A table build inside a decision (about 2 minutes).** Renaming the variant so Hero would read a table built from
   the twist's own deal put a 491 ms build inside `act()` (278 deadline overruns swallowed by SafeBot). Dropped.
4. **Flaky timing tests (about 2 minutes reading).** The suite failed one timing test per run under load.
5. **Warm-up artefacts (about 1 minute).** The import-time warm-up shows as `history_prefix` and `button_changed`
   conformance findings on hand 1.
6. **The kit unloads our modules before `Agent()` is built** and drops our folder from sys.path. The adapter's re-pin
   (V-g) assumed after. No cost: the player pinned at import and put the folder on sys.path twice.
7. **A timed `hand_over`.** The composite's hand end ran 1-5 ms at load 7.6: 0.3-0.9% of hands forced the next
   decision to check/fold (3 at a 5 ms budget). Drill 8's player deferred the hand end; this one did not.
8. **Docs.** PLAYBOOK writes `--cand '<the dict>'`; climb_accept wants `{"dials": {...}}`.

## Fixes that follow (H5, a worker)

- The entry template pins the package at import (`pin_package()` after the bot is built and warmed), and keeps the
  folder on sys.path; prompt 02 says so.
- Prompt 02: a kit that times its hand-end callback gets `bot.defer_hand_end(True)` and a hand_over that only stores.
- Gate seat template: history rows tagged by street, blind posts included.
- Conformance: a reset after the import-time warm-up.
- A `timing` pytest marker the night can deselect (`-m "not timing"`).
- No table build inside a decision: a missing variant table at decision time falls back (to the twin or hold'em) and
  is built at table start or not at all.
- PLAYBOOK's `--cand` syntax.
- Variants track (V-h, later): shared and known cards (Chain's links, exposed_card) priced as the opponents' too.
