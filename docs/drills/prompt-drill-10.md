# Prompt drill 10: Track A on kit H (the bot as its own process, JSON lines), Solo Hold'em

Date 2026-11-03, T0 06:46:13 EST, stopped at minute 53. The climb's fourth rehearsal, on batch 5's ship (repo pinned at
077b95f). Load 22-28 on 8 cores throughout (the climb's runs).

**Set-up.**
- Kit H was built by a fresh organiser agent with no repo access (goal/drill10/kit; 36 tests, 400 tables clean).
- **Interface.**
  - Each bot is its own process (`python3 -u bot.py`), speaking JSON lines over stdin/stdout. Each message gets one
    reply echoing its id; timing is on the engine's side, with one message in flight. A late bot is auto-played (check or
    fold) until its reply lands.
  - One process per session: hello 2 s, table start 50 ms, end of hand and end of table 1 ms.
  - Players are stable handles. Cards are 0-51. Actions are "f", "c", "r<N>" (raise-by). Legal actions are implied, and
    the history is a compact string.
  - Size cap: 5 MB zipped, 20 MB unzipped.
  - Points 13/8/5/3/2/1/0/-2: last place loses points.
  - Handout: docs/drills/drill10/kitH-README.md.
- **The twist: Solo Hold'em.** A hand uses exactly one hole card and exactly four board cards. Preflop values turn over:
  AA is 55th of 169, TT 149th, 22 last, and AKo and A9o first; suited is slightly worse than offsuit. In the organiser's
  runs, twist-aware sample bots scored 8.6-9.5 a table against 4.6-4.8 for unadapted hold'em bots.
- **Player:** a fresh agent with the pinned repo and the handout. Its files are in docs/drills/drill10/, and its Hero
  patch is player-hero.diff.

## Key numbers

| Checkpoint | Drill 10 | Drill 9 | Drill 8 | Target |
|---|---|---|---|---|
| Rule sheet, axis | minute 1 (hand strength: regenerate) | 1 | 1 | 5 |
| First valid upload | minute 6 | 5 | 1 | 12 |
| Ship bot gated and submitted | **minute 29** | 10 | 12 | 40 |
| Variant patch | **kept**, minute 41 (`hero.solo_flop`) | none | none | 50 |
| Stopped | minute 53 | 19 | 20 | 60 |

- **The final zip** plays the composite, with Hero playing the whole table under this rule. It has a flop fix (dial
  `hero.solo_flop`) and the regenerated tables/variants/solo.
- **The patch.**
  - Our sim, deterministic timing: 7.24 -> 8.16 a table.
  - Against twist-aware opponents: +0.86 ± 0.36.
  - Kit sim at 5 ms: 8.24 -> 8.63.
- **Kit sim at the real 1 ms**, 8 seats with the kit's bots: 6.36 ± 1.07. 49% of our decisions were auto-played; the
  kit's own do-nothing bot reached a 5 ms p99 at this load.

## What slowed it down or broke (minutes first)

1. **No entry or gate-seat template for a process kit (about 10 minutes).** The player wrote bot.py's JSON-lines loop
   and gate_seat.py by hand. The gate calls the bot in-process, so it never tests the stdin loop.
2. **Table generation under load (about 8 minutes, 5 of them on the critical path).** The default generator was
   projected far past 20 minutes for the one-hole-card showdown. The player restarted it with fewer samples, and twice
   its `pkill -f` killed its own shell; it finished with a resume script (gen_rest.py).
3. **Timeouts in the kit sim (about 7 minutes to diagnose).** 62% of the ship bot's decisions were auto-played, against
   15% for the cheap bot.
   - The composite does the hand-end work twice on a table Hero plays alone (the hero member and the base's fallback
     Hero), about 280 us of CPU, while the next message already waits on its 1 ms clock.
   - The entry's fix: answer first, defer, and skip the bot's hand end when a message is waiting. That took one seed
     from 5.57 to 7.13 points and from 61% to 33% timeouts.
4. **A gap in Hero (about 6 minutes).** Hero's must-use path checks or folds every flop when the board must supply four
   cards, because three are on it. Prompt 04's flop printout exposed it, and the player patched it (`hero.solo_flop`).
5. **The kit launches the bot with a fixed environment (1 minute).** HYPERION_CHECK never reached the bot; the player
   used a marker file instead.
6. **Package limits (half a minute).** pack.py's --max-mb checks the unzipped size, and the full package (8.4 MB) failed
   until --slim. The kit allows 2 s to start, but pack allows 5 s, and the gate measured 1.7-2.1 s imports under load.
7. **Parallel kit runs contaminate timing.** Three candidates run at once all showed 55-65% timeouts. The test suite
   started late (minute 42) and was stopped unread.

## Fixes that follow (H6, a worker)

- An entry and gate-seat template for process (JSON lines) kits, with answer-first, deferred and skip-when-waiting
  hand ends built in.
- No hand-end work for the base's fallback Hero on tables the hero member plays whole (play identical).
- Hero's must-use path plays the flop when the board must supply more cards than it has (the general form of the
  player's `hero.solo_flop`).
- Table generation: a preset for a loaded box, unbuffered progress, a resume flag; and prompts say "kill by PID".
- pack.py: the kit's own import budget (`--import-budget`) and both size caps; prompt 02 notes a kit that strips the
  environment.

## H6 (drill 10 fixes)

Branch climb/h6-drill10-fixes from main ed263bc. Each item, what changed, and how it was tested (`tests/test_h6_drill10.py`
unless named). The box ran at load 20-63 on 8 cores throughout; every measurement used at most two workers.

1. **A process-kit template.** `hyperion/drills/process_entry_template.py`, for a kit whose bot is its own process on
   JSON lines, with kit H's protocol as its worked defaults (TODOs 0-3: message names, answer forms, the translation,
   the warm-up). Built, warmed and pinned at import; fd 1 is pointed at stderr and the replies go unbuffered
   (`os.write`) to a private copy, so a stray print never reaches the protocol (only when run as the kit's process: pack's
   import probe prints on stdout). Every request is answered first: a decision decided then answered, a hand end or
   table end answered at once and processed after. The bot's hand end is deferred (`defer_hand_end(True)`, `idle()` after
   it), and both parts run only while no request is waiting on stdin (`select` on the raw fd, plus what the loop has
   buffered); a skipped hand end still keeps the chip chain, and is counted. The table start runs before its reply (its
   own 50 ms). Local checks by marker: `check.on` beside the entry sets HYPERION_CHECK, which kit H's fixed environment
   never passes. `hyperion/drills/process_gate_seat_template.py` (`PROCESS = True`): tools/gate_host.py hands it the
   entry's path instead of importing it, and the seat launches the entry as the kit does (`python -u`, the package as
   the working directory, kit H's environment), greets it in its constructor (so the gate's import time is the bot's),
   and plays every decision, hand end and table through the pipe; the gate's timed call is the round trip.
   tools/pack.py leaves the vendored template out, as it does entry_template.py. Prompt 02 says when (step 2), the
   marker (step 4) and the seat (step 7); the PLAYBOOK's Stage 2 too.
   Tests: a fake engine (kit H's engine side, cut down: its fixed environment, ids matched) round-trips hello, a table
   and a decision on every street one at a time, then a burst of nine written at once (hand ends, decisions, a table
   end and the next table start): every reply in order, one each, the decisions legal, 0 swallowed errors, 0
   conformance violations, and the hand ends that found a message waiting skipped. The template imported (as pack's
   probe does) leaves stdout alone. tools/gate.py with the process seat on a packed template plays a Solo table clean.
   By hand: 4 Solo tables through the gate, GATE PASS, 0 exceptions, 0 illegal, import 1.10 s; the pipe round trip p50
   160 us against the in-process baseline's 58 at load 45 (what the kit's clock charges, which an in-process seat never
   showed). In kit H's own simulator, a timing probe in a copy: `end` answered in 12 us p50 (p99 323), its deferred work
   134 us p50 (p99 557) after the reply.

2. **No doubled hand end.** On a table the base's core cannot play (HybridCore._table_why: 13 catalog entries, short
   deck, must-use, three hole cards, wild cards, two boards, fixed limit ...), every decision of the base's was its
   fallback Hero's: a HeroCore with the hero member's Config, seed and inputs. Both paid the hand end (ICM curve,
   profiler dials) and the base shadowed every postflop decision in full. Note that the composite did not hand every
   section to the hero member there: the base's Hero decided the preflop sections (omaha_four, one table: 58 of 82
   decisions). Now it does (`CompositeCore._whole`, when the two Configs compare equal): the hero member plays the
   base's sections and the variant prompts, and the base sleeps (`HybridCore.sleep`: no decision, no shadow, no Hero
   hand end; its chip chain and the core's end still run). The counts read `<section>:hero`.
   Identity, against main in a detached worktree (per-seed sample lists and the decision, timeout, error and illegal
   counts of every climb_accept `--out` chunk): plain hold'em `--cand '{"dials": {}}' --set 10000:10040 --stages
   confirm,guards`, 14 chunks, 280 samples, 374,461 decisions, identical; omaha_four, short_deck and wild_deuces at the
   same 40 seeds, 6 chunks, 161,513 decisions, identical (and again, all 20 chunks, with item 3 in). The test plays one
   table of each of the 13 Hero-whole catalog entries both ways in one process (`_same_hero` forced off for the old
   routing): every decision, variant answer and point the same; the base's Hero gets no hand end, the old routing's 20+.
   Hand-end cost, `tools/latency.py --hand-end --reps 3` (20 tables, the per-call minimum of 3 passes), main -> H6:

   | variant | hand_end mean | hand_end p99 | act mean | act p99 | load |
   |---|---|---|---|---|---|
   | omaha_four | 63.1 -> 37.8 us | 121 -> 80 | 61.7 -> 43.7 | 116 -> 79 | 45 / 45 |
   | short_deck | 68.7 -> 38.7 | 158 -> 87 | 45.7 -> 31.9 | 91 -> 58 | 62 / 43 |
   | wild_deuces | 66.8 -> 37.7 | 141 -> 80 | 52.0 -> 35.8 | 136 -> 83 | 63 / 44 |

   The acts fall too: the base's full postflop shadow is gone. What is left of the hand end (omaha_four, 6 tables): the
   hero member's own 28 us, the base's chain and core end 4, the layer 3, elite1 1. Nothing more there that play does
   not read.

3. **Hero's must-use path on a short board.** Must-use-k takes 5 - k board cards; on Solo's flop (k = 1) the board has
   three of the four, so Hero checked or folded every flop (the player's printed spot: A-K on A-9-4, folded to 40 into
   130). `Postflop.read_short` (Config `mu_short_board`, on) reads the hand by what the river can still make of it:
   each k-card choice of the hole with every board card so far, its rank groups that hold a card of ours a floor at the
   river (a group only on the board is everyone's), a flush draw when all k cards share a suit the board is one card
   short of, straight completers when k + board is four distinct ranks. The tiers are the hold'em tiers of the same
   heads-up equity against a random hand to the river (WIDE_EQUITY_FLOP), from Solo's flop measured over 200,000 deals:
   trips 0.954 (tier 7), top pair 0.851 (5), two pair over the board's pair 0.808 (5), middle pair 0.732 (4), two pair
   under it 0.709 (4), bottom pair 0.614 (2), the board's pair with a queen-plus kicker 0.587 (2), an overcard 0.470
   (1), nothing 0.319 (0); a flush draw or open-ender lifts our pair to 4 and anything else one tier (bottom pair with a
   flush draw 0.736, an overcard with one 0.601). The general form of the player's `hero.solo_flop`; turn and river read
   as before (the exact must-use strength). No catalog entry has such a board: omaha_four (the only must-use entry)
   flops the three it needs, and `_read` sends only a short board to the new read.
   `hyperion/drills/solo_example.py`: kit H's Solo Hold'em in ghost_example's shape (must_use_hole 1, its blinds,
   13/8/5/3/2/1/0/-2, chip-count places at the cap), with the player's regenerated `tables/variants/solo/` (284 KB:
   preflop 3,000 samples, matrix 50 a pair, push/fold re-solved, flops 2 a texture) and the generic aware bots' table
   (`tables/generic/solo-cdaf1a6f.json`).
   Identity: `climb_accept --stages variants --variants omaha_four --set screen` against main: 8 chunks, 200 samples,
   276,470 decisions, identical (and the 40-seed cells of item 2). Tests: the tiers above on eleven flops; `_read` sends
   Solo's flop, not its turn and not Omaha's flop, to read_short; F with top pair on Solo's flop calls or raises a bet
   and bets when checked to (before: fold and check); F on omaha_four decision for decision the same with the dial off.
   **Solo numbers:**
   - Our sim against twist-aware generic opponents, paired (`climb_accept --stages aware --aware
     generic:hyperion/drills/solo_example.py:variant --base '{"dials": {"hero.mu_short_board": false}}' --cand ''
     --set 10000:10100`): 7.428 -> 8.361, **+0.934 +- 0.397, UP** (the player's patch on drill 10's tree: +0.86 +-
     0.36).
   - F's flops there (30 tables, seed 11): facing a bet, 357 of 357 folded before; 225 folds, 66 calls, 3 raises after.
     Checked to: 350 checks and 233 bets (the layer's) before, 215 and 338 after.
   - Kit H's own simulator, the template-built zips (dials `{"hero.mu_short_board": false}` against `{}`), the
     player's 8-seat field (station, random, tight, solo_aware, station, random, tight), duplicate deals, unpaired
     intervals: at 50 ms (no timeouts; the box at load ~20 times out at 1 and 5 ms whatever the bot does), seed 7, 160
     tables: 10.160 +- 0.582 -> **11.025 +- 0.426**, first places 104 -> 123; at 5 ms, seed 7, 80 tables: 9.625 +- 0.788
     -> 11.912 +- 0.698 (timeouts 13.6% -> 6.0% of decisions, the box). Against three solo_aware bots, two tight, a
     station and a random at 50 ms, seed 11, 160 tables: 8.781 +- 1.084 -> **9.425 +- 0.741**. The README's 3-entry
     form wins every table either way (13.0).

4. **Table generation under load.** tools/gen_tables.py `--preset loaded`: 3,000 samples, 50 a heads-up pair, 2 flops a
   texture with 300 holdings (drill 10's restart, about 5 minutes for Solo on 3 workers at load 22-25); explicit flags
   win. Before the run it prints the 95% accuracy the counts buy, worst case: +-0.018 a preflop cell, +-0.139 a matrix
   cell, +-0.024 against a 20% range (push/fold reads ranges); meta.json records it and the preset. Progress is flushed,
   a line every tenth of the preflop and matrix stages with an ETA. `--resume` keeps the stages a stopped run finished
   for the same card rules (meta.json's `done` as it goes; for an older run, the files) and runs the rest; a new matrix
   re-solves push/fold. Prompts 03 (the preset, the PID file, `--resume`), 04 (the load generator) and 06, and PLAYBOOK
   (Stage 3 and hard rule 9): kill by PID, never `pkill -f`. Tests: the preset's numbers and accuracy, the first line
   (the accuracy) read from a pipe while the run is still going and nine or more progress lines a stage; a run stopped
   after its preflop resumed with the preflop files byte for byte, the rest rebuilt, the meta saying what was kept; an
   old-style partial run resumed from its files; other card rules keep nothing.

5. **pack.py.** `--import-budget` existed (default 5 s); its help and prompt 02 step 6 and 04 step 5 now set it from the
   kit's start budget (kit H: 2), the import line prints the budget and the load. `--max-mb` is the unzipped cap and
   `--max-zip-mb` the zipped one (default: the same), both printed on the zip line; kit H: `--max-mb 20 --max-zip-mb 5`.
   Test: the slim package passes kit H's caps, fails a 0.5 MB zipped cap on the zip, and a 1 MB unzipped cap on the
   package.

**Found on the way.** tools/climb_accept.py cached a set's short last chunk (10025-10039 of 10000:10040) under the full
chunk's name, so a later `--set screen` run in the same `--out` read its 15 samples as 25 and played 190 seeds (main's
first omaha_four screen run did). A short chunk is now named by its length (`.n15`); full chunks keep their names and
caches. Test: the two names differ.

**Suite.** `python -m pytest -q -m "not timing"` at load 17-22: 1296 passed, 2 skipped, 3 failed, all three failing on
main too (a detached worktree of ed263bc, the same tests): test_sim_rival5's judge2 field check fails every time (field
`outside_b` seats rival5); test_nightof_latency's kit D round trip fails its 500 us p99 under this load; test_sim_adapt's
twin test plays a strict-mode table, on the wall clock, and fails one run in three on both trees. tests/test_h6_drill10.py:
37 tests.
