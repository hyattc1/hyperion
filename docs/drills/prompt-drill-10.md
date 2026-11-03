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
