# R2, R3, R4: instance lifetime, kit shapes, memory and import (branch climb/r2-lifetime-kits)

Backlog items R2-R4 (docs/drills/goal-plan.md section 5), robustness track. Base: main 98a7259 (F = the composite,
`SHIP_DIALS` with the governor). Host: 8 cores shared with the other workers; the 1-minute load was 10-13 for the whole
session, so every wall-clock maximum below includes preemption (multiples of the 4 ms scheduler tick) and, on this
WSL2 host, CPU-time maxima are inflated too (R1's finding). My processes ran under `nice -n 10`, at most two at once.
Scratch files: the session scratchpad, `goal/r2/`.

## Summary

| check | result | numbers |
|---|---|---|
| R2: one object, 10,000 night tables, as shipped (main) | pass | RSS 95.9 -> 124.9 MB (3.1 KB a table: the simulator's per-seed cache, not F; F's own +18 bytes a table); CPU p50 58-61 us, p99 195-250 us per 500-table block, no trend |
| R2: one object plays each table as a fresh one (model mode, main) | pass | 200 of 200 tables replayed by a fresh object: identical points, places, hands, stacks |
| R2: state after new_table vs a fresh object | pass after fix | before: `HeroCore._pre_aggr` carried over (never read stale); after: no difference |
| R2: SafeBot panic, governor level, composite level, profiler, exploit reads reset at new_table | pass | test_lifetime.py |
| R2: per-decision time creep over 10,000 tables | pass | first vs last 2,000 tables: CPU mean 70.7 -> 69.2 us, p99 233 -> 212 us (main); C: no trend, p99 142-422 us block to block with the host load |
| R2: garbage collection inside a decision | pass | 136 gen-0 collections in 10,000 tables, 3.5 ms in all; no gen 1 or 2 |
| R2: a fresh bot object per table, one process | **FAIL -> fixed** | +70.8 KB a table for good (gc.freeze pinned each old bot) -> 0.0 KB |
| R2: a fresh import of the package per table, one process | **FAIL -> fixed** | +28 MB a table (190 MB at table 6, kit E's 256 MB cap by table 8) -> flat 64 MB |
| R2: one object, no table-start hook (kit reuses the object) | **FAIL -> fixed** | the bot's new_table ran once: panic, reads and seat carried into every later table -> restarted when the hand number goes back |
| R2: a hook that names our seat from 1 | fixed | the bot's tables were reset with the wrong seat -> put right at the first decision |
| R2: kit E's own runner, 200 tables in one process | pass | max RSS 61.7 MB (main) / 65.4 MB (branch); the kit itself unfreezes and collects after each table |
| R3: 20 kit shapes through the adapter, ship bot, model mode | 7 broke -> all pass | before: 5 shapes fell back to check/fold on every decision, 2 on 13-21%, 2 misplayed; after: 0 fallbacks, the plain shape's decisions on all 20 |
| R3: the same 20 shapes through tools/gate.py, packed zip, ship bot | pass | 20/20 GATE PASS, 0 exceptions, 0 illegal; timeouts 0.1-0.8% under load (the in-sim baseline 1.2%) |
| R4: peak RSS, every table packaged and every catalog variant's tables loaded | pass | 65.1 MB (Python 3.12), 61.7 MB (3.10) |
| R4: import from a cold start elsewhere (`python -I -B`, no .pyc) | pass | import 0.02-0.05 s; make_bot + new_table 0.22-0.50 s; kit E setup budget 1 s |
| R4: sizes against 100 MB / 10 MB zipped | pass | default 4.9 MB / 1.2 MB zip; every table 8.0 MB / 1.7 MB zip; slim kit B 3.7 MB / 807 KB zip (was 4.7 MB / 1.16 MB) |
| R4: stdlib only, clean `/usr/bin/python3 -I` (3.10, no venv) | pass | imports, builds, plays; no module from outside the package and the stdlib |
| R4: decision time, `tools/latency.py`, 20,000 calls | report | 3.12: p50 50 us, p99 444 us, max 9.7 ms (load 10-12); 3.10: p50 75 us, CPU 1.38x 3.12's |
| R4: slim leaves the opponents out | done | `--slim` drops sim/field, sim/aware.py, every rival but rival 3; slim kit B zip 1,159,582 -> 807,488 bytes |
| identical play (climb_accept screen, confirm + guards) | see below | |

## R2: instance lifetime

### The tool

`tools/lifetime.py` plays one object through N tables in Hero's seat of a field (tools/swap.py's seating, rotation
t % 8), the other seats fresh each table, and every 500 tables prints RSS, our decisions' p50 / p99 / max on the wall
clock and on the thread's CPU clock, and the garbage collections that ran inside our act(). `--mode model` uses the
climb's deterministic F and with `--fresh-every K` replays every K-th table with a fresh object (its random generators
copied into the old object first, so a difference is state, not luck). At the end the old object and a fresh one both
get new_table and their attribute graphs are compared (`state_diff`, counters and per-decision scratch skipped).

### Runs (night field, 10,000 tables each)

| run | code | mode | RSS at 500 -> 10,000 | per table | CPU p50 / p99 per block | CPU max | wall max |
|---|---|---|---|---|---|---|---|
| A | main | measure, `ship.make_bot()` as shipped | 95.9 -> 124.9 MB | 3.1 KB | 58-61 / 195-250 us | 12.1 ms | 144 ms |
| B | main | model, fresh replay every 50th table | 99.7 -> 180.3 MB | 8.5 KB | 75-78 / 244-311 us | 12.0 ms | 215 ms |
| C | branch | measure, as shipped | 95.3 -> 120.1 MB | 2.6 KB | 55-63 / 142-422 us | 21.8 ms | 57 ms |

- B: 200 of 200 replayed tables identical (points, places, hands, final stacks). B grows faster because it builds two
  fresh objects per replayed table, and before the fix each one stayed in memory (below).
- No creep: A's first 2,000 vs last 2,000 tables: CPU mean 70.7 -> 69.2 us, p50 60.5 -> 60.0, p99 233 -> 212. C's
  p99 moves 142-422 us from block to block with what else ran on the host (gate runs, tests), with no trend.
- The 10-22 ms CPU maxima are not the collector (C counted 136 gen-0 collections inside act over 10,000 tables, 3.5 ms
  in all, no gen 1 or 2). They appear from the first block on and do not grow; R1 found the same on this host (WSL2
  charges the hypervisor's preemption to the thread's CPU clock).
- The one-object growth (3 KB a table on main, 2.6 after the fix) is the simulator's, not F's. tracemalloc over tables
  100-600 (run T, one frame): +987 KB at hyperion/sim/field/night.py:138 (the night pool's draw cache, one entry per
  table seed), +626 KB in the engine's per-table stats, +20 KB in the bestiary; F's own allocations +6.5 KB (profiler)
  and +2.6 KB (rival 3's core) over 500 tables, about 18 bytes a table. The two ICM memos were empty (8..1 payouts
  take the closed form); under top-heavy payouts they fill to at most 65,536 and 32,768 entries (bounded LRU).

### Failure 1: gc.freeze() pinned dead objects for good

Hero's `new_table` and its module import call `gc.freeze()` so no full collection over the tables lands inside a timed
act(). A frozen object is never collected; one that dies later in a reference cycle stays in memory for good.

- A fresh bot object per table in one process (the package cached; a runner that builds a new Player per table):
  +70.8 KB a table (26 tracked objects), so 1,000 tables 70 MB.
- A fresh import of the package per table in one process (a sandbox that purges the bot's modules between tables):
  +28 MB a table. RSS 162 MB at table 5, 190 MB at table 6: kit E's 256 MB cap by table 8, then the bot is stopped and
  check/folds.

Fix (hyperion/strategy/hero.py): `refreeze()` = `gc.unfreeze(); gc.collect(); gc.freeze()`, at import always (setup,
10-20 ms) and at one Hero table start in 32 (`table_freeze`; 16 tables of the composite, which holds two Heroes). The
other table starts only freeze, as before, so a kit with no table-start hook pays the 10-20 ms collection inside a
first decision one table in 16. After: fresh object per table 0.0 KB a table (setup mean 25.9 -> 17.5 ms, p50
24 -> 12.5 ms), fresh import per table flat at 64.1 MB. Tests: tests/test_lifetime.py (both cases in a subprocess;
they fail on main: +84 MB and 27,786 frozen objects over three re-imports; 1,664 frozen objects over 64 fresh bots).

Kit E's own runner (fresh module copy and fresh Player per table, all in one process) never showed this: it calls
`gc.unfreeze(); gc.collect()` itself after each table. 200 tables of kit E with one seat ours: max RSS 61.7 MB (main),
65.4 MB (branch). One kit E run (the first, cold unzip) crashed in the kit's own end-of-table `gc.collect()` with its
alarm firing (`kit.sandbox.Interrupted`); ten more runs with either package, five of them cold, did not repeat it. A
kit-side race, noted for whoever maintains kit E.

### Failure 2: one object for many tables with no table-start hook

`Adapter.start` (the bot's new_table) ran from the kit's table-start hook or lazily on the first decision. A kit that
keeps one object for every table and has no hook (kit D's `handle_new_round` only, or a tournament-wide instance)
got new_table once: SafeBot's panic, the governor's level, the profiler and exploit reads, the hand-end state and our
seat all carried into every later table. Fix (hyperion/drills/adapter.py): `decide()` restarts the bot (Adapter.start
itself, so a subclass's own start, such as EventAdapter's tracker reset, is untouched) when the hand number goes back,
counted in `adapter.tables_seen`. Test: test_kit_shapes.py, three tables with our seat moving 0, 1, 2 and panic forced
before each: on main new_table is called once; now three times, the seat right and panic off each time.

Related: a hook that names our seat differently from the states (numbered from 1, or an id) reset the bot's table
state with that wrong seat. Now the first decision after a start compares and restarts with the observed seat
(`adapter.seat_fixes`). Also `adapter.fallbacks` counts decisions that went to native_safe.

### Stale state found by the attribute diff

`HeroCore._pre_aggr` ("I was the last preflop raiser") survived new_table. Never read stale (hand_no is -1 after
new_table, so the table's first act and the composite's resync reset it first), but now reset in new_table so the
diff is clean. Everything else (SafeBot panic and governor, the composite's level and panic, profiler, exploit layer,
ICM curve, hand-end state, inference) matched a fresh object after 10,000 tables.

## R3: kit shapes

Fake kit S (hyperion/drills/fakekits/kit_s, RUBRIC.md there): the dealer's state with one quirk switched on, 20
shapes; `KitSAdapter` is written the template's way (cards through parse_card, the kit's legal list and raise bounds
straight into make_observation, seats and amounts through the rule sheet's conventions). tests/test_kit_shapes.py
plays each shape for two 80-hand tables, realistic field, the climb's deterministic F behind the adapter.

| shape | main's helpers: fallbacks to check/fold (of ~205 decisions) | effect | after |
|---|---|---|---|
| raise_by, put_in (increments) | 0 | same decisions | same decisions |
| log_own, log_last3, log_none | 0 | same (the inference rebuilds the log) | same |
| posts (blinds logged as bets) | 1 | different play: every unopened pot read as raised and re-raised | posts dropped, same decisions |
| bounds_swapped | 0 | every raise became an all-in (clamp takes the larger bound): 106 decisions, busted early | same decisions |
| bounds_missing | every decision | `int(None)` | derived, same decisions |
| allin_short (min above my stack) | 0 here | a raise above the all-in when it fires (unit test) | min = all-in |
| seats_from_1, seats_me | 0 | same | same |
| cards_ten ("10h") | 28 (13%: every hand with a ten) | | same decisions |
| cards_lower ("th") | 0 | | same |
| cards_unicode ("T♥"), cards_suit_first ("hT") | every decision | | same decisions |
| legal_upper | 0 | | same |
| legal_dicts, legal_string | every decision | | same decisions |
| legal_words ("bet", "all-in") | 47 (21%) | | same decisions |

(Main's column counts one extra fallback in every row: the kit omits min/max when raising is not legal and main's
make_observation needs ints. A writer on main would have passed 0 there.)

Fixes:
- `parse_card` (hyperion/core/types.py): the fast path unchanged; anything else goes to `parse_card_any`: "10h", "th",
  "TH", unicode suits (with or without the emoji selector), suit first, "10 of hearts", "1h" as the ace, (rank, suit)
  pairs, {"rank", "suit"} dicts, rank 2-14 or 1. Bare ints are refused (their order is the kit's).
- `make_observation` (hyperion/drills/adapter.py): `legal_kinds` takes our names in any case, "bet", F/K/X/R/B, "c"
  and "check/call" (a check when nothing is owed), "all-in" (a call when the call takes every chip, else a raise),
  a separated string, dicts with a type/action/kind/name key, ActionKinds and classes (CheckAction); an unknown word
  still raises KeyError. `raise_bounds`: None bounds derived (max = stack + bet, min = top bet + the last increment,
  at least the big blind), swapped bounds ordered, a max above everything I have capped, a min above my all-in
  lowered to it. `drop_blind_posts`: leading raises to the big blind or less (after the flop only when the first is
  below the big blind, so a street-only log's min bet survives). to_call None is derived. What was put right goes in
  `obs.extras["kit_fixes"]`; nothing is added on a clean kit (a clean kit's legal list and bounds take the old fast
  path: make_observation 2.5 us on main, 4.1 us now, 7.1 us before the fast path). Kits A-E play as before; one kit C
  unit test had a hand-made state whose max raise (2000) was above the seat's chips (1980), which the cap now lowers,
  so its stacks were made consistent.
- Conformance: the report lists the quirks make_observation put right (not violations); new rule `history_blind`;
  `seat_range` / `button_range` / `history_seat` say "numbered from 1?" when the index is n.
- Templates (adapter_template.py, event_player_template.py): TODO 1 (what parse_card reads), TODO 4 (the three amount
  conventions both ways; pass None for a missing bound), TODO 5 (the kit's words; reply in the kit's word), TODO 6
  (numbered from 1, from us, ids or numbers that move every hand), TODO 7b (posts logged as calls are not dropped;
  only-our-actions logs are "partial"), TODO 8 (one object for many tables: pass the kit's hand number as it is).

Through the gate (`tools/gate.py <zip> --kit seat_<shape>.py --kit-module kit_s/kit.py --entry entry.py --tables 6
--mode measure --field realistic`, the shipped F packed `--slim`, one fresh `python -I` per table): all 20 GATE PASS,
0 exceptions, 0 illegal, import 0.04-0.09 s. Timeouts 0.10-0.82% of decisions, under load 10-13 (the gate's load
clause; the in-sim baseline itself timed out on 1.16%). Package p50 152-167 us, p99 332-893 us; the reference kit A
adapter through the same gate: p50 158 us, p99 624 us. So kit S costs what kit A does. In one process the adapter path
(translation + the log inference) costs about 35 us at p50 over the bot's ~52 us.

Conformance on each shape (HYPERION_CHECK's report, one table): no violation on any shape with a full log; the
quirk counted where make_observation put it right (posts: blind_posts_dropped on every hand; bounds_swapped,
bounds_missing, allin_short likewise). The partial-log shapes show history_raise / history_prefix only because
KitSAdapter switches history_source per state, after the report was made for a "log" kit (a real adapter sets it once).

Not fixed, noted: a kit that numbers seats relative to the button (renumbered every hand) or drops busted seats from
its lists mixes the per-seat reads; the template now says to map ids to fixed seats at table start. A kit that logs
the blind posts as calls is not detected (the template says to skip them).

## R4: memory and import

Probe (goal/r2/r4probe.py, stdlib only), run with `env -i` and `python -I -B` from an empty directory, the package
first on sys.path: import the entry, build F, new_table under the default rules and under each of the 25 catalog
variants (their table sets loaded), play one table against seven cheap bots.

| python | import | make_bot + new_table | RSS after build | every variant loaded (peak) | one table p50 / p99 | outside modules |
|---|---|---|---|---|---|---|
| venv 3.12, `-I` | 0.019-0.045 s | 0.22-0.50 s | 53.6 MB | 65.2 MB (65.1) | 44-49 / 256-636 us | none (102 modules) |
| /usr/bin/python3 3.10, `-I`, no venv | 0.021-0.051 s | 0.23-0.45 s | 50.7 MB | 62.1 MB (61.7) | 70-74 / 665-723 us | none (95 modules) |

- Sizes: default pack 4.9 MB, zip 1.2 MB; with every table (`--tables-dir tables`) 8.0 MB, zip 1.7 MB; kit E's slim
  entry 4.7 MB, zip 1.2 MB; slim kit B (after the slim change below) 3.7 MB, zip 807 KB. Caps 100 MB and 10 MB zipped.
- `tools/latency.py --n 20000` (load 10-12): Python 3.12 p50 50.4 us, p99 444 us, max 9.7 ms, 0.49% over 1 ms (wall
  1659 ms, CPU 1330 ms for the run); Python 3.10 p50 74.6 us, CPU 1831 ms (1.38x). On 3.10 every decision costs about
  40-50% more: worth knowing if the sandbox runs 3.10 (kit E says "3.10+"); R1's governor is the guard.

### --slim and the simulator's opponents (coordinator's request)

`tools/pack.py --slim` shipped every test opponent: hyperion/sim/field (field bots, judges, elite1-3, the outside builds,
exploiter1), hyperion/sim/aware.py and rivals 1, 2, 4, 5 (and microholdem). Which simulator modules the ship bots import,
measured (goal/r2/simimports.py: each bot built, new_table under the default rules and every catalog variant, a plain
table and a table of each of the 25 variants, the composite with each of its six recipes):

| bot | hyperion.sim modules imported |
|---|---|
| composite (F), all recipes | hyperion.sim.rivals, hyperion.sim.rivals.rival3 |
| hybrid3_x | hyperion.sim.rivals, hyperion.sim.rivals.rival3 |
| hero, cheap | none |

`--slim` now drops sim/field, sim/aware.py and every rival but rival3 (an allow-list, so a new opponent added later
is dropped too); a recorded route naming another rival's donor (rival1, r2, ...) copies that rival back, and pack's
build check still builds the recorded bot from the package. Slim kit B entry: 90 files, 4.70 MB, zip 1,159,582 bytes
(main) -> 68 files, 3.72 MB, zip 807,488 bytes. Tests (test_nightof_pack.py): a slim package builds and plays each of
composite, hybrid3_x, hybrid3, hero and cheap from the package alone in a fresh `python -I` elsewhere (plain and four
variants), and holds no field bot, judge, elite, outside build, exploiter, aware opponent or rival but 3; a route
naming r2x keeps rival2.

## Identical play

`tools/climb_accept.py --cand '{"dials": {}}' --base '{"dials": {}}' --set screen --stages confirm,guards`, run from a
detached worktree at main 98a7259 (cache key cced8a8907c0) and from this branch (code at 05c0208, key 1a6024be79c3;
the later commits touch only tools/lifetime.py and tests; the branch run was split into seeds 10000-10099 and
10100-10199, two processes of one worker each, same cache, then read back as `--set screen`). Both report F at
+0.000 ± 0.000 against itself, so the evidence is the per-seed comparison of the two caches
(goal/r2/compare_ca.py):

| cell | seeds | identical per seed | main | branch | timeouts / exceptions / illegal |
|---|---|---|---|---|---|
| night | 200 | 200 | 5.9730 | 5.9730 | 0 / 0 / 0 both |
| night_hard | 200 | 200 | 5.4851 | 5.4851 | same |
| realistic | 200 | 200 | 6.3465 | 6.3465 | same |
| top | 200 | 200 | 5.0350 | 5.0350 | same |
| night @10/7/5/4/3/2/1/0 | 200 | 200 | 6.1587 | 6.1587 | same |
| night @50/25/12/6/3/2/1/1 | 200 | 200 | 24.4427 | 24.4427 | same |
| night, doubling blinds | 200 | 200 | 5.8281 | 5.8281 | same |

Every one of the 1,400 per-seed samples (8 rotations each) is the same float on both trees. Under protocol addendum 2
the changes are accepted on play-identity plus the demonstrated failures above (memory: 28 MB a table on a re-import,
70 KB a table per fresh object; the hookless one-object kit; seven kit shapes that fell back or misplayed).

## Tests

New: tests/test_lifetime.py (4: one object plays like a fresh one and keeps nothing; new_table resets panic, levels and
reads; a fresh import per table and a fresh object per table free the old copy, in subprocesses), tests/test_kit_shapes.py
(64: every shape at real tables, the quirk report, the hookless one-object kit, the 1-based hook seat, parse_card,
legal_kinds, raise_bounds, drop_blind_posts, make_observation unchanged on a clean kit, the new conformance rules),
tests/test_nightof_pack.py (+2: slim builds and plays every ship bot from the package and holds no opponent; a route
naming r2x keeps rival2). The lifetime tool and the kit S fixture take their registrations out of the bestiary when
done (the first full run caught `python -m hyperion.sim --list` failing on the tool's unnamed seat).

Full suite (`python -m pytest -q`, 1,089 tests), twice, at load 13-17: 15 and 17 failures, all in the wall-clock family
the goal log already lists as flaky under load (test_sim_bestiary budget, test_sim_outside / test_sim_exploiter /
test_sim_timeout_model replays, test_slowbox, test_nightof_latency, the gate's history test, whose verdict gained a
timeout clause), plus two of mine since fixed (the runner's --list, and the r2x pack test's 5 s import budget, now 60 s:
rival 2 runs a Monte Carlo at import). Re-run alone: my tests and the replay tests in one process, 98 passed; the
wall-clock set fails the same way on main's tree at the same load (14 failures there, 11 on the branch, different bots
each run).
