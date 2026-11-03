# Prompt drill 11: Track A on kit I (module functions, chips-now ints, relative seats), Tranche Hold'em

Date 2026-11-03, T0 14:21:57 EST, stopped at minute 29. The climb's fifth rehearsal and the first on batch 6's ship
(repo pinned at c8d64fa). Load 17-19 on 8 cores throughout (the climb's runs).

**Set-up.**
- Kit I was built by a fresh organiser agent with no repo access (goal/drill11/kit; 35 tests, 500 tables clean).
- **Interface.** Module-level functions, one module for the session: `start(session)` 3 s, `table(info)` 50 ms (an
  overrun sits the bot out for the table), `act(v)` 1 ms, `done(h)` 1 ms. `act` returns one int, the chips to put in
  now (0 = check or fold, which is also what a timeout or error does). No legal list (to_call and min_raise only).
  Seats relative to us (0 = me), reshuffled every table. Cards 0-51. A compact history string. A timer raises an
  `Overtime` BaseException inside the bot at the limit. The loader drops the bot folder from sys.path and the helper
  modules from sys.modules right after import. Handout: docs/drills/drill11/kitI-README.md.
- **The twist: Tranche Hold'em.** Each betting round's chips are their own pot, won at showdown by the best hand as it
  stood on that street: two cards preflop (any pair over AK, suits never count), hole cards plus the flop, plus the
  turn, then ordinary hold'em on the river. Folding gives up every tranche paid into. Once betting is over no more
  cards come, so an all-in settles on the cards already out (a preflop all-in has no board). Points
  +16/+10/+6/+3/+1/0/-1/-3; 86-92% of the organiser's tables reach the 200-hand cap, ranked by chips. In the
  organiser's runs a twist-aware sample bot beat a plain hold'em one by 2.6 points a table. Organiser's notes:
  docs/drills/drill11/kitI-ORGANISER-NOTES.md.
- **Player:** a fresh agent with the pinned repo and the handout, prompts 00-05 and the playbook.

## Key numbers

| Checkpoint | Drill 11 | Drill 10 | Drill 9 | Drill 8 | Target |
|---|---|---|---|---|---|
| Rule sheet, axis | minute 3 (payoff and two-card strength) | 1 | 1 | 1 | 5 |
| First valid upload | minute 6 | 6 | 5 | 1 | 12 |
| Ship bot gated and submitted | **minute 12** | 29 | 10 | 12 | 40 |
| Variant patch | **kept**, minute 26 (two-card twin preflop) | kept, 41 | none | none | 50 |
| Stopped | minute 29 | 53 | 19 | 20 | 60 |

- **Kit simulator** (200 tables, seed 9, CPU clock; two seats ours against 2 tight, 2 tranche_bot, station, random):
  cheap +3.87 ± 0.51, ship +9.12 ± 0.67, ship + patch +9.16 ± 0.66 (tight +3.27, the organiser's twist-aware bot
  +5.47). Timeouts 1.6% on the wall clock at load 17-19; the kit checker on the CPU clock 0.11-0.20%. 0 errors.
- **The patch** (`twin_hole` in the adapter, every preflop decision): the bot is shown the hold'em class at the same
  combo percentile as its hand's two-card rank (22 as ATs, KQ as A3s); real cards after the flop. Paired in the
  kit's sim on the same tables, 1,000 tables: +0.35 (+0.62, +0.28, +0.06, every run up). A version only at 20 bb or
  less was level over 1,100 tables.
- Final zip `out/03-twin.zip`, sha256 f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa: the composite,
  dials {}, the adapter's twin. Gate PASS all three zips, 0 exceptions, 0 illegal.

## What slowed it down or broke (minutes first)

1. **No entry template for a module-function kit (3 min).** And the template's hand end copies kit G's `won` as each
   seat's chip change; here `won` is chips collected (change = won - sum(paid)): pasted as is, it silently feeds the
   bot wrong stacks.
2. **No gate seat for this shape (2 min).**
3. **"Passes the kit's checks" on a loaded box (2 min).** The wall-clock checker flags every bot, the kit's own too.
4. **The test suite gave no signal (one heavy slot for 6.5 min).** 16% done at its timeout at load 18.
5. **Conformance false alarms (1 min).** The kit makes everyone call the full big blind after a short blind post.
6. **The latency recipe (4 min).** tools/latency.py said it halves act time; the kit's sim showed the same timeouts
   and lower points. Reverted.
7. **The twist (14 min).** Prompt 05 has no section for street-settled pots and our simulator cannot play them, so
   every measurement was kit-sim A/B.
8. **Three keep rules disagree (1 min).** Prompt 05 "rise by more than half the CI", PLAYBOOK Stage 5 "not beyond the
   CI down", the brief "not worse".
9. **No Stage 0 number under tonight's rules** (one person in both roles).
10. `python -m hyperion.ship --set` rewrote the SHIP line and dropped its comment (seen in the pinned repo's diff).

## Fixes that follow
- H7 (a worker): items 1-6, 8-10: a module-function entry and seat template (with a "won: collected or net?" TODO),
  the checker's pass rule on a loaded box, a one-minute night test subset, a Rules flag for the full-big-blind rule,
  prompt 04's latency check in the kit's own sim, one keep rule, the Stage 0 clause on a solo night, ship --set.
- V-j (a worker): item 7: street-settled pots in our engine and catalog, a twist-aware test bot, and F's play there.
