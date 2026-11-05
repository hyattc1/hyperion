# Prompt drill 12: Track A on kit J (a closure per table, amounts in big blinds), Trailing Stop Hold'em

Date 2026-11-04, T0 23:28:49 EST, stopped at minute 20. The climb's sixth rehearsal and the first on batch 8's ship
(repo pinned at eac472a). Load 15-17 on 16 threads throughout (the climb's runs).

**Set-up.**
- Kit J was built by a fresh organiser agent with no repo access (goal/drill12/kit; its checks in the kit's TESTS.md).
- **Interface.** One module function: `sit_down(table)` returns the `decide(v)` closure for that table, 25 ms (hard stop
  500 ms; an overrun plays the whole table on check/fold autopilot); `decide(v)` 1 ms (hard stop 50 ms). No other
  callback: a finished hand arrives as `v.recap`, inside the next timed decide. Amounts are floats in big blinds of the
  current level. Cards are one int bit mask (bit = 13 * suit + rank - 2). Answers are strings: `"f"`, `"c"`, `"r<x>"`
  (raise by x on top of the call). No legal list. Tags are random per table, with no seat numbers. One module copy per
  seat; the kit's simulator keeps every copy in one process, turns automatic collection off during a table and collects
  between tables on its own time. Handout: docs/drills/drill12/kitJ-README.md.
- **The twist: Trailing Stop Hold'em.** Every player has a public stop at 60% of their highest closing stack (it starts
  at 1,200 and never falls). Closing a hand below it eliminates the player whatever chips they still hold; those chips
  are split among the survivors. So past the stop (`stack < floor`) a fold is elimination with chips in hand, and a
  timeout or an error, which folds, is the same. Points 14/9/6/4/3/2/1/0; 9-20% of our tables reached the 200-hand cap,
  ranked by stack. In the organiser's runs a twist-aware sample bot beat a plain hold'em one by 2.3 points a table.
  Organiser's notes: docs/drills/drill12/kitJ-ORGANISER-NOTES.md.
- **Player:** a fresh agent with the pinned repo and the handout, prompts 00-05 and the playbook.

## Key numbers

| Checkpoint | Drill 12 | Drill 11 | Drill 10 | Drill 9 | Target |
|---|---|---|---|---|---|
| Rule sheet, axis | minute 2 (payoff) | 3 | 1 | 1 | 5 |
| First valid upload | **minute 3** | 6 | 6 | 5 | 12 |
| Ship bot gated and submitted | **minute 8** | 12 | 29 | 10 | 40 |
| Variant patch | **kept**, minute 17 (past the stop, shove) | kept, 26 | kept, 41 | none | 50 |
| Stopped | minute 20 | 29 | 53 | 19 | 60 |

- **Kit simulator** (seed 1, CPU clock; two seats ours against 2 tight, 2 deskhand, station, random): cheap +5.65 ± 0.83
  (60 tables), ship +7.75 ± 0.52 (200 tables), ship + patch +8.15 ± 0.41 (300 tables, seed 7, wall clock at load 17;
  tight +4.03, the organiser's twist-aware deskhand +6.59). Timeouts: ship 0.28% on the CPU clock; ship + patch 1.42% on
  the wall clock at load 17, 0.48-0.86% on the CPU clock. 0 errors.
- **The patch** (`StopBot` in the adapter, mode A): past the stop, all-in if we can raise, else call, else check; the bot
  is not asked. Paired in the kit's simulator on the same tables, 1,100 tables, every run up: +1.55 (seed 31, 500 tables,
  the proper lineup), +2.03, +1.83. Larger ideas lost on one-seat screens (400 tables, about ± 0.5): the stop-relative
  stacks as depth 5.03 vs 5.74, a crossing call priced as the whole stack 5.37 vs 6.30.
- Final zip `out/03-stopA.zip`, sha256 264c04ee6da011ab2a547bae5d5b56c0294718dc57f513be59a983de50f739f4: the composite,
  dials {}, stop mode A, and `hero.table_freeze` switched off in the entry (item 1 below). Gate PASS all three zips, 0
  exceptions, 0 illegal; the patch's gate `--variant submission/tonight.py:variant` +1.230 ± 0.911.

The record, in docs/drills/drill12/: NIGHT.md, adapter.py, bot.py (the entry), gate_seat.py, tonight.py (the twist as a
hooks file), rules_tonight.json, the handout and the organiser's notes. adapter.py carries inert mode letters that
03-stopA.zip's copy does not (it was built before F); the zip's only live mode is A (`stop_patch.txt`).

## What slowed it down or broke (minutes first)

1. **Table start near its limit (2 min).** Hero's `table_freeze` ran a full `gc.collect` every 16 tables: 10 ms with one
   copy, 20-27 ms with four, against 25 ms. 22-24 of 400 tables per seat went to autopilot in the first 4-copy screen,
   and past the stop an autopilot folds. Found at minute 9 only because the kit prints a `setup` column.
2. **No template for this kit's shape (1 min).** The module-function template and seat were adapted by hand; the seat had
   to be rewritten.
3. **No section in prompt 05 for an elimination threshold (4 min).** It fits no axis section, so candidates were reasoned
   and screened from scratch; the first three were larger than the one that won.
4. **The gate means nothing without the twist (1 min).** On plain rules the seat's floors fire with no stop in the
   engine, so the patch shoves at nothing unless `--variant` carries the stop.
5. **A timing chase with no gain (3 min).** Skipping the log kit's rebuild and the `latency` recipe left p99 at about
   920 us. The `timeouts` recipe measured slower than the ship bot (mean 479 us against 405 us at a 500 us limit, 40%
   timeouts against 14%), though the docs present it as the cure.
6. **A lineup slip (no minutes).** Two of the three keep-rule runs listed 5 bots, so the kit repeated the list and the
   lineup was A x4, base x3 and one opponent, not two seats each.
7. **Unstated:** one module-level adapter assumes one table at a time per process. True of the kit's simulator, not
   promised for the event.

## Fixes that follow

H8 (a worker): the items above; see "H8" below and docs/drills/climb/h8-log.md.

**Future organiser briefs exclude `trailing_stop`.** The exclusion list lives in the organiser prompts
(goal/drill12/organiser_prompt.txt, the sentence starting "It must NOT be any of these"). The entry to add after
`tranche_holdem (...)`: `trailing_stop (a public stop at a share of each player's highest closing stack; closing a hand
below it eliminates them, however many chips they hold, and the chips go to the survivors)`. The interface sentence
gains: a module function returning a decide closure per table, with recaps inside the timed decide.

## H8 (drill 12 fixes)

Branch climb/h8-drill12-fixes from main ad63e00; running log and every number: docs/drills/climb/h8-log.md. Tests: tests/test_h8_drill12.py.

1. **A table start never collects.** `table_freeze` only freezes, and only a bot at its second table or the process's first start. Four copies, `sit_down` p99 24.3 to 0.9 ms, max 29.2 to 3.1 ms (one copy: 5.85 to 0.67); kit simulator `setup` 100 of 1,600 to 0, autopilot 14,404 decisions to 0, in 400 tables. Decisions and hand ends level (mean 297.5 and 293.8 us; hand_end p99 211.8 and 208.9 us; no gen 1 or 2 collection in act either way), RSS level. `tools/latency.py --table-start` and the gate's `--setup-budget-ms` state p99 and max against the kit's limit; the old code fails the first.
2. **A closure template and seat.** `closure_entry_template.py`, `closure_gate_seat_template.py`. Kit J's simulator: 0 errors, 0 violations, `setup` 0; the gate passes on plain rules and with the stop as a hooks file.
3. **Prompt 05** asks what makes a normal fold or call wrong under tonight's rule, then the two checks, smallest patch first.
4. **`--variant` for a function patch**: prompt 02 step 7, a gate WARN (`TWIST_PATCH`, or a class in front of `bot.act`), and the seat reports no stop unless the engine plays one.
5. **`timeouts` pays only for what it reads.** It computed the ICM curve and ran the profiler and the core's replay on every hand. Through kit J's adapter 220.9 to 88.1 us, p99 620 to 230 us, timeouts 2.04% to 0.13% at a 500 us limit, against the ship bot's 255.0, 520 and 1.15%. `latency` (215.2, 490, points level) stays the first dial.
6. **One adapter, one table at a time**: the rule sheet asks, the templates say so, `TABLES_AT_ONCE` handles it, and past that the table that lost its adapter check-folds and is counted.
7. **The other notes**: the kit's `setup` column, one paired recipe run, name eight bots, a function patch's aware check.

**Identity.** `climb_accept --set 10000:10040 --stages confirm,guards`: all seven rows' points, timeouts and errors as goal/idchk39.md. **Suite** 1514 passed, 5 skipped, 1 failed (a scheduler tick in a wall-clock test; passes 4 of 4 alone, on base too). **Parity** PASS, 112,522 decisions. **Gate** PASS on plain.
