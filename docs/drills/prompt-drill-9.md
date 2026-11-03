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

## H5 (drill 9 fixes)

Branch climb/h5-drill9-fixes from main 8744c7d. Each item, what changed, and how it was tested (`tests/test_h5_drill9.py`
unless named).

1. **Module pinning at import.** `pin_package(*folders)` (hyperion/drills/adapter.py) also keeps the given folders on
   sys.path, and `repin_package()` (every Adapter start, decide and hand end, and the top of every entry method) puts
   the modules back and re-appends a folder a loader removed: one copy appended last, so it survives
   `sys.path.remove` and never shadows anything. A new Agent-style entry template, `hyperion/drills/entry_template.py`
   (kit A, F, G shapes): builds, starts and warms the bot at module import, then `pin_package(<its folder>)`; the first
   Agent takes that warm adapter. The event template and the event example now build and pin at import too; the
   adapter template's notes and prompt 02 step 2 point at it (tools/pack.py leaves the vendored template out: its
   `from adapter import` would fail a kit's static import check). Test: a child process loads the template as kit G's
   `import_bot` does (folder off sys.path, every module from it deleted, BEFORE `Agent()`; the venv's editable
   install stripped so no other hyperion answers), then decides on a state whose translation makes two imports nothing
   made before: a top-level module beside the entry and an unimported package submodule. Both load from the package,
   no fallback. Control: the same entry minus its `pin_package(<folder>)` falls to the kit's fold (the package alone
   is pinned by the Adapter built at import; the folder is not).
2. **Timed hand-end callbacks.** The template's `HAND_END` (TODO 0, from prompt 01's timed-callbacks question):
   `"eager"` untimed; `"defer"` (default) `bot.defer_hand_end(True)` and the callback runs only the light part of the
   hand end; `"store"` the callback only appends the result and the next decision delivers it first (drill 8's way).
   Prompt 02 says which. Measured, the composite under kit G's rules (tools/latency.py --hand-end, load 6.5): whole
   hand end mean 105 us p99 334; deferred 22 us p99 64, the pending curve and dials 82 us p99 270 (computed by the
   Hero that decides next, only its own). On kit G's own harness (its engine.sim, the same deals, chain bots, one seat
   ours, the template filled as the drill 9 player would; runs with a load spike that sat tables out marked *):

   | seed, tables, load | eager: late / forced | defer | store |
   |---|---|---|---|
   | 7, 50, 6.5 | 7 / 5 | | 23 / 0 |
   | 11, 150, 7.1 | 15 / 30 | 48 / 1 | 93 / 0 |
   | 41, 200, 8.9 | 150 / 159 * | 206 / 33 | 452 / 3 * |
   | 42, 200, 8.8 | 223 / 234 | 49 / 5 | 375 / 0 * |
   | 43, 200, 7.8 | 28 / 34 | 325 / 82 * | 77 / 1 |

   The forced check/folds go away (store 0-3, defer 1-33 in its clean runs, eager 30-234), but a stored hand end
   lands on the first decision of every hand (most hands we decide once): decide p50 120 -> 210 us, p99 350 -> 660,
   and twice the late decisions; defer p50 190, p99 530. Points level within noise in every pair (differences -2.1 to
   +4.0, each run's CI +-2.2-2.6). So the default is defer, not the store the fix list asked for; store stays one
   word away. Tests: under the loader above, defer: the callback calls the adapter's hand end, the Heroes still owe
   their curve, the next decision acts; store: the callback calls nothing (an append, under 200 us CPU), the next
   decision delivers then acts; `defer_hand_end(True)` reached every Hero in both. The final template-built zip on
   kit G (seed 7, 50 tables, load 6, HYPERION_CHECK=1): 26.22 vs chain 15-17, late 1 of 8474, forced 0, entry errors 0.
3. **Gate seat.** For a seat file (`--kit seat.py`) tools/gate.py now sends each history row as
   `[seat, kind, total, street, put]` (the street from where each betting round began; `put` the chips it added,
   replayed from the stacks after the posts) and `posts`, the hand's forced bets `[[seat, "ante" | "sb" | "bb" |
   "straddle", chips]]`, in the decision state, the discard state and the hand-end result. Kits a, b, c, d and the
   direct baseline keep their three-field rows (their kit modules unpack three); fake kit S's seat unpacks any length.
   `hyperion/drills/gate_seat_template.py` gains `by_street(rows, posts, upto)` (one list per street, posts first, each
   `(seat, kind, to, put)`) and `kit_g_log`, drill 9's kit worked through; prompt 02 step 7 and gate_host's KitA notes
   say to build the kit's own log. Test: two GateTable tables with a recording seat proxy: rows and decisions agree,
   streets ascend, the posts plus each street's puts equal every seat's bet, and kit G's per-street log built from the
   state parses, through the drill 9 player's own `history()` (docs/drills/drill9/adapter.py), back to the same
   actions and raise-to totals at every decision and hand end. Every existing gate test passes.
4. **Conformance after the warm-up.** The checked adapter's `start` clears the report's cross-call state (seat,
   button, chips, last history) at each table, and `conformance.warmed(adapter)` clears the whole report; the entry
   template calls it after its warm-up. Test: drill 9's pattern (a made-up hand 1 with button 4 and a raise, `start`,
   the kit's hand 1 with another button and no log) leaves no `history_prefix` or `button_changed`; `warmed` zeroes
   the counts; a button change within a table is still caught. On kit G the template-built zip reports only the kit's
   own `to_call_bets` (drill 9 had 2 `history_prefix` and 1 `button_changed` on hand 1).
5. **`timing` marker.** Registered in pyproject.toml; marked: the bestiary budget test, test_slowbox (module), fake
   kit reference runners (kit A's timeouts) and the three-hole-card run, test_setup_cost (module),
   test_hand_end_interrupt (module), and four more wall-clock thresholds (hand_end p99, Hero's latency, hybrid p99,
   a known sleep's percentiles) plus the gate's drop-history test, whose verdict counts timeouts (it failed at load 12
   during H5: 0.44% > 0.3%; passed alone, as on main). 90 of 1274 tests; `python -m pytest` still runs all of them.
   Prompt 02 step 5: on the night `python -m pytest -q -m "not timing"`.
6. **No table build inside a decision.** Drill 9's 491 ms did not reproduce: the player's exact run (rules_chain.json,
   the chain hooks, `{"hero.twin_multi": 0.01, "hero.variant_tables": "three_card_keep"}`, model mode, 300 tables, its
   generic chain_holdem table in place) gives the same 30.027 and max 8.7 ms, safe_over 170, against the base's
   31.156, max 18 ms, safe_over 193 at the same load: host stalls, not a build (thread-CPU per act at most 1.3 ms in
   four tables of each; a SIGALRM probe 2.5 ms into each slow act found only ordinary decision code). Hero's act has no table path. The one path where a
   decision does load or build tables is a table start inside it: Adapter.decide starting the bot (a kit with no
   table-start hook, or the hand number going back). Cold, that start cost 67 ms CPU for three hole cards (the 8-card
   evaluator), 33 ms on short deck (the 81-class set and its push/fold arrays), 4.4-5.5 ms on a two-card twist with
   a prepared table (each new bot's variant preflop layer), every one inside a 1 ms decision. Now Adapter.decide wraps those
   starts in `tables.quick_start()`: `tables_for` returns a set only if this process loaded it, else the plain tables
   (`tables/`, or its label view for 3+ cards); `generic_doc` returns no twin; Hero skips `warm()` (the evaluations
   go through the subsets, exact), builds no 169-class set's modules and no variant preflop layer it lacks, and caches
   no twin or recut it could not read. A later start outside a decision (a table-start hook, the template's import)
   loads everything as before. The simulator never starts a table inside a decision, so F plays as before. Test:
   cold child process, an adapter with no hook, rules chain_holdem (3 cards), three_card_keep, short_deck: the first
   decision, table start included, 0.3-1.6 ms CPU (bound 15 ms; main 67, 3.3 and 33 ms), legal answers preflop and on
   the flop, plain tables; the same start outside a decision 68 ms and the committed set; a lazy start after it plays
   the committed set. (The two-card twist, by hand: 0.3-0.4 ms against main's 4.4-5.5.)
7. **`--cand`.** PLAYBOOK Stage 5 and prompt 05 now write `--cand '{"dials": <the dict>}'`. The other examples
   (prompt 06, CONTRACTS, tools/apicard, the variant examples) pass recipe names, which climb_accept reads. Test: every
   `--cand '...'` in PLAYBOOK, the prompts and CONTRACTS is a recipe or a `{"dials"`/`{"bot"` spec.

**F's play.** `tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards --workers 2` on
this branch and on main (a detached worktree of 8744c7d): every cell's per-seed sample list in the `--out` caches is
identical (14 cells, 280 samples, and the same 374,461 decisions, timeouts, errors and illegal counts); confirm
night 5.965 on both, guards level at +0.000.

**Suite.** `python -m pytest -q` (everything, the timing tests included) at load 6-7.6: 1282 passed, 1 skipped in
362 s; `-m "not timing"` deselects 90.
