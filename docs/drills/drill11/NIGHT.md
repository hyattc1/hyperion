T0: 14:21:57

# NIGHT log

repo: hyperion c8d64fa (pinned copy)   kit: kitdl/tranche-holdem-kit   variant (their name): Tranche Hold'em   track: A
operator role: played by the agent; questions answered conservatively and noted inline as "OPERATOR ANSWER".

## Prompt 00 restatement (minute 1)
Python bot in the kit's interface (module-level start/table/act/done in bot.py, act returns an int of chips to add now);
every act() and done() must return inside 1 ms wall clock (timer-interrupted; timeout/error = check-else-fold), so
lookups and arithmetic only, all precompute at import/start (3 s) or table (50 ms). Stdlib only, no network, one core,
no threads; zip <= 5 MB zipped / 25 MB unpacked with bot.py at root. 8-max SNG, 2000 chips, blinds 10/20 rising every
25 hands, 200-hand cap ranked by stack (not ICM), points +16/+10/+6/+3/+1/0/-1/-3. Strategy never imports the kit; one
adapter. Priorities: (1) never-crashing legal bot submitted by minute 15; (2) prepared ship bot through the adapter,
strict-sim and gate verified; (3) smallest twist-forced change, kept only if measured not worse. Verify by commands.

## RULE SHEET (Stage 1, prompt 01; minute 2-4)

- Hole cards: 2. No discards, swaps, exposures, auctions.
- Board: 3/1/1, one board, nothing changes. BUT "No cards after the betting is over. If, after a betting round, at most
  one bot in the hand still has chips behind ... no more cards are dealt ... A preflop all-in is settled on two-card
  hands with no board at all."
- Hand ranking (THE TWIST, "Tranche Hold'em"): "Each betting round's chips form their own pot, called a tranche. At
  showdown, each tranche goes to the best hand as it stood on that street." Tranche 0 (blinds + preflop bets) = two
  hole cards only: "A pair beats any non-pair; a higher pair beats a lower pair. Non-pairs compare the higher card, then
  the lower card. Suits never count" (2-2 beats A-K, A-2 beats K-Q). Tranche 1 (flop bets) = exactly hole + 3 flop.
  Tranche 2 (turn bets) = best 5 of 6. Tranche 3 (river) = ordinary hold'em. Side pots layered per tranche by what each
  paid on that street. "Folding gives up every tranche". Ties split; odd chip first clockwise from button.
- Betting: no-limit; min bet 1 bb; min raise = largest full bet/raise on the street; short all-in does not reopen.
  Uncalled chips returned at end of round (`u` in log). Action amount = chips ADDED NOW (increment), not raise-to.
  No antes, no straddles.
- Blind schedule: 10/20, 15/30, 25/50, 40/80, 60/120, 100/200, 150/300, 250/500; 25 hands/level; 2000 chips; 8 seats;
  cap 200 hands. Heads-up: button posts SB, acts first preflop.
- Scoring: +16 +10 +6 +3 +1 0 -1 -3 by finish. At hand 200 survivors ranked BY STACK (not ICM); ties share. Same-hand
  busts ordered by starting stack. No bounties.
- Agent interface: module `bot.py`, module-level functions, no class. `start(session)` 3000 ms once per session;
  `table(info)` 50 ms per table; `act(v)` 1 ms per decision -> int; `done(h)` 1 ms per hand. v fields: hole, board,
  street, to_call (capped at stack), min_raise (0 = may not raise; == stack if full raise needs more), stack, stacks[8],
  seats str 'p'/'a'/'f'/'x', paid[8][4], tranches[4], button, sb, bb, hand (1..200), level, log (full action log,
  relative seats, `s b f k c r u`, `!` all-in). Seats RELATIVE: 0 = me, 1 = to my left. Return n < to_call = fold
  (check if to_call 0); to_call <= n < min_raise = call; n >= min_raise > 0 = raise by putting n in; n >= stack all-in.
  Non-number return = error. One module per session (few hundred tables), globals persist; reset in table().
- Setup budget: import not timed locally; start 3 s once per session; table 50 ms. One fresh module instance per seat.
  The bot folder is on sys.path ONLY during import, and helper modules from the folder are dropped from sys.modules
  after import: every import must happen at bot.py import time.
- Callbacks: timed by setitimer; overrun raises Overtime (BaseException) inside our code; late return = timeout.
  done() overrun: nothing happens to play, counted. table() fail: sit out the table. start() fail: sit out session.
- Submission: zip, bot.py at root, 5 MB zipped / 25 MB unpacked (pack.py --max-zip-mb 5 --max-mb 25 --import-budget 3).
- Tooling: `python3 -m engine.sim BOT... -t N`; `python3 -m engine.check team.zip` (layout, caps, load, 20 tables).
  CPython 3.10 stdlib only; one core; no threads/processes; files read-only.

## AXIS CLASSIFICATION

- Hand strength ordering moved? Y (for preflop chips): tranche 0 and every preflop all-in rank on two cards only, pair >
  non-pair, high card then kicker; no board. Postflop chips judged on the street they were bet: flop chips on exactly
  hole+flop (draws worth nothing for that tranche), turn chips on 6 cards.
- Information moved? N.
- Payoff moved? Y: the pot is split into per-street tranches won by different hands; points table +16..-3 (a points
  table unlike ours is an ASSUMPTION DIFF, Rules.payouts).
- Betting structure moved? N (no-limit, standard min-raise); schedule differs from our default above level 3 (diff).
- Stage 5 patch section: strength ordering (preflop / push-fold) — the tranche-0 two-card ranking. Payoff split noted.

## FIT VERDICT

| prepared layer | verdict | reason |
|---|---|---|
| evaluator | KEEP | 5-7 card hands are ordinary poker; river tranche is hold'em; flop tranche = 5 cards (evaluator handles) |
| preflop tables (169-class) | REGENERATE in principle / KEEP tonight | all-in preflop equity is deterministic two-card ranking, unlike hold'em equity. Generator has no Rules field for "no board on all-in" -> cannot regenerate with tools/gen_tables.py; Stage 5 carries it as a small preflop override |
| push/fold solution | REGENERATE in principle | same reason: a push/call is a two-card showdown. Not reachable by the generator; Stage 5 patch |
| postflop rule layer | KEEP | made-hand reads are right for flop/turn/river tranches; draws over-valued on flop/turn chips (Stage 5 note) |
| opponent profiler | KEEP | reads actions; the log is full (history_source = "log") |
| ICM curve | KEEP | reads Rules.payouts; cap ranks by chips -> extras.cap_places = "chips" |

Path: no DROP pair -> Track A. REGENERATE layers are not reachable by the generator (no Rules field for the two-card
showdown), so Stage 3 is SKIPPED (noted) and Stage 5 carries the preflop two-card ranking as one small override.

## ASSUMPTION DIFF

| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole cards, 3/1/1 board | same; no board after betting closes (preflop all-in = no board) | preflop all-in equity, push/fold | Stage 5 patch; ENGINE CANNOT REPRESENT |
| standard rankings, one pot | per-street tranches: two-card ranking preflop, hole+flop on flop, 6 cards on turn | pot odds, draw value, all-in equity | Stage 5; ENGINE CANNOT REPRESENT |
| no-limit, raise-to totals | no-limit, return = chips added now (increment) | from_action | adapter |
| levels 4,5,8 = 50/100, 75/150, 200/400 | 40/80, 60/120, 250/500 | sim schedule | rules_tonight.json blind_levels |
| no antes | none | - | - |
| linear payouts 8..1, ICM at cap | +16/+10/+6/+3/+1/0/-1/-3, cap ranked by chips | ICM curve | payouts, extras.cap_places=chips |

ENGINE CANNOT REPRESENT: tranche settlement and the no-board preflop all-in. Every hyperion sim line tonight is
captioned "variant minus tranches" (plain hold'em with tonight's schedule and points); the kit simulator is the truth.

## MOST DANGEROUS THING FOR A 1 ms BOT

The loader drops the bot folder from sys.path and deletes every helper module from sys.modules right after bot.py is
imported: any lazy import inside hyperion (in start(), table(), act() or done()) raises ModuleNotFoundError or re-imports
inside a 1 ms call -> errors = check/fold every decision. Second: act() returns an increment (chips added now), so a
raise-to total passed straight through over-raises by our street contribution; and relative seats (0 = me).

CHECKPOINT rule sheet + axis classification: 14:24:44 = minute 3
## Stage 2 notes
- Kit is closest to the entry template's kit G shape (done(h) has hand/won/shown/log/board), but module-level
  functions, so submission/bot.py is a module-level entry built from entry_template.py; adapter from adapter_template.
- done(h).won is chips COLLECTED, not a delta: delta = won - sum(paid) (the template's kit-G line would be wrong here).
- Kit sim, 8 tables, HYPERION_CHECK=1, composite: 0 errors, 101/3137 act timeouts (3.2%, load 17 on 8 cores; the kit's
  own tranche_bot also timed out 30/2739), conformance 18 violations, all `to_call_bets`: the kit's rule "the others must
  still call the full big blind" after a short blind (to_call 200 with max(bets) 100). Kit quirk, not a translation bug:
  the adapter passes the kit's to_call as it is. Actions fold/check/call/raise all > 0.

## Submissions

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|
| 6 | submission.zip | 2b887ec710fe09ddacaa70395596e055a8e652e8ccf66627f12a9b04a7d0e4b0 | 2.1 MB / import 0.24 s | cheap: cheap bot | |
| 6 (submitted 14:28:19 = minute 6) | out/01-cheap.zip | 2b887ec710fe09ddacaa70395596e055a8e652e8ccf66627f12a9b04a7d0e4b0 | 2.1 MB zipped / 8.5 MB unzipped, import 0.24 s | bot cheap, dials {} (Hero.cheap()) | engine.check --clock cpu: OK, 20 tables, 0 t/o 0 err, max act 774 us |
| 9 | submission.zip | d376c821c20d14c2eb99d48225b8b853e81b08bdeb05b214a898757cc038a405 | 2.1 MB / import 0.79 s | composite: ship bot (composite) | |
| 24 | submission.zip | f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa | 2.1 MB / import 0.41 s | composite: ship + two-card twin on every preflop decision (TWIN_BB 1000) | |

CHECKPOINT first valid submission: 14:28:19 = minute 6 (out/01-cheap.zip, sha256 2b887ec710fe09ddacaa70395596e055a8e652e8ccf66627f12a9b04a7d0e4b0).
- engine.check wall clock (load 17): PROBLEMS 8 act timeouts / 2359 (0.34%) and 6 done() over limit; the kit's own
  tranche_bot timed out 18 and tight 1 in the same run -> machine load (README sec. 6: use --clock cpu). CPU clock: OK.
- Kit check results (cpu clock, 20 tables, 1 seat of ours vs 2 tranche_bot, 2 tight, 2 station, 1 random):
  cheap +4.50 +-1.87 (place 3.80), tranche_bot +9.65, tight +6.03, station -1.18, random -1.48; 0 t/o 0 err.

## Verified (every command whose output decided something)

| minute | stage | command | the line that mattered |
|---|---|---|---|
| 5 | 2 | `HYPERION_CHECK=1 python3 -m engine.sim submission/bot.py bots/tight.py bots/tranche_bot.py bots/station.py -t 8` (composite) | 0 err; conformance 18 to_call_bets (kit's full-big-blind rule after a short blind: kit quirk); fold 598 check 179 call 112 raise 654; 101 t/o of 3137 at load 17 |
| 6 | 2 | `tools/pack.py --entry submission/bot.py ... --bot cheap --import-budget 3 --max-mb 25 --max-zip-mb 5` | import ok 0.24 s; 2.1 MB zipped / 8.5 MB; sha256 2b887ec7... |
| 6 | 2 | `python3 -m engine.check out/01-cheap.zip --clock cpu` | OK: loads, starts and plays 20 tables with no timeouts or errors |
| 8 | 2 | `tools/gate.py out/01-cheap.zip --kit submission/gate_seat.py --entry bot.py --tables 30 --rules submission/rules_tonight.json` | GATE PASS +0.100 +- 1.237 vs cheap (sim), 0 exc 0 ill, tmo 0.12% |

Stage 3 (TABLES): SKIPPED. The moved strength axis (two-card showdown preflop) has no Rules field the generator reads,
so regenerating is not possible in the hour; Stage 5 carries it.
| 12 (submitted 14:34:17 = minute 12) | out/02-ship.zip | d376c821c20d14c2eb99d48225b8b853e81b08bdeb05b214a898757cc038a405 | 2.1 MB / 8.5 MB, import 0.79 s | bot composite, dials {} (the ship bot) | gate PASS -0.150 +- 1.317 (100 t); engine.check --clock cpu 0 err, 4-6 act t/o of 3400-3700 (0.11-0.18%) |

CHECKPOINT ship bot gated and submitted: 14:34:17 = minute 12 (out/02-ship.zip, sha256 d376c821c20d14c2eb99d48225b8b853e81b08bdeb05b214a898757cc038a405).
- Stage 4 checks (all "variant minus tranches" for our sim):
  - hyperion.sim 300 t strict realistic@ship --rules: ship 9.557 +- 0.786 (first; rival1 7.40, pushfold 4.76, tag 4.38),
    exc 0 ill 0, but tmo 921 and p99 4129 us at load 16-18 with 3 heavy jobs (load clause; no quiet box). No Stage 0
    number was re-measured with tonight's rules, so "within CI of Stage 0" cannot be judged (noted).
  - gate 100 t: package 10.950 +- 1.281 vs composite (sim) 11.100; paired -0.150 +- 1.317; 0 exc 0 ill; tmo 1.22%
    (in-sim baseline 1.73%: machine) -> GATE PASS with load-clause WARN.
  - engine.check --clock cpu (20 t, two runs): ship +12.20 +- 2.66 and +11.40 +- 2.75 vs tranche_bot +7.20/+7.53,
    tight +4.60/+4.62, station -1.44/-1.28, random -0.92/-1.12; 0 errors; act t/o 4/3694 and 6/3419; done() over
    limit 4-5. The kit's own tranche_bot timed out 7 and 1 in the same runs: load. Wall clock check: PROBLEMS
    (timeouts) for every bot incl. the kit's.
  - OPERATOR ANSWER (conservative): "passes the kit's upload checks" read as layout/caps/load/start OK, 0 errors,
    act timeouts < 0.3% on the cpu clock, the kit's own bots timing out in the same run.
  - tools/latency.py --n 2000: composite p99 4708-5702 us wall, over 1 ms 2.25-2.9%, wall 425-486 ms vs cpu 218-224
    ms (the box). With --dials latency: mean 96.5 us, over 1 ms 1.10%, cpu 152 ms -> carry the latency recipe into the next
    package (hard rule 7: timeouts first).
  - pytest -m "not timing": at 16% after 5.7 min under load 18; killed by its 400 s timeout (note: the suite never
    imports submission/, and the repo's code is unchanged).

## Stage 5 (PATCH) — strength axis, the two-card twin
- Prompt 05 has no section for a per-street pot twist; the strength-ordering section's tools (rank_order remap,
  regenerated tables) cannot express "preflop all-in = two-card showdown". Smallest change: one small function in
  submission/adapter.py, `twin_hole`: on a preflop decision whose effective stack is <= TWIN_BB (20) big blinds, or
  facing a call >= 40% of our stack, the bot is shown the hold'em class at the same combo percentile as our hand's
  two-card rank (22 -> ATs, 66 -> 77, AK -> AKo, A2 -> QJo, KQ -> A3s, 72 -> 54o). Postflop and deep preflop: real
  cards. Strategy untouched.
- Our sim cannot play tranches (ENGINE CANNOT REPRESENT), so hard rule 6 would drop the patch on our sim alone; the
  kit simulator IS the game, so the measure is the kit sim, paired in the same tables: A (ship+latency, no twin) and B
  (ship+latency+twin) two seats each with 2 tranche_bot and 2 tight, cpu clock.
- Also measured: A against out/02-ship.zip (the latency recipe alone), same layout.
- minute 15, kit sim 200 t seed 202 cpu clock (latency recipe alone): A = ship+latency +5.317 +- 0.657, 964 t/o of
  69647; 02-ship +6.067 +- 0.686, 952 t/o of 71826 (tranche_bot +2.83, tight +1.79). No timeout gain in the kit's
  own sim (mean act 215.6 vs 214.1 us: the adapter and the box dominate, not the shadow decisions) and points lower
  (within noise) -> latency recipe REVERTED (`python -m hyperion.ship --set '{}'`), DIALS {} again.
- minute 15, kit sim 400 t seed 101 cpu clock (twin): A (ship+latency) +5.716 +- 0.467, B (ship+latency+twin20)
  +5.587 +- 0.475; tranche_bot +3.09, tight +1.60. B sat out 1 table (table() over 50 ms under load; A none in this
  run). Level within noise, not up -> not kept on this run alone; re-measured on two more seeds/fields below.
- minute 19, kit sim 400 t seed 303 cpu (ship vs ship+twin20, DIALS {}): 02-ship +5.401 +- 0.463, B2 +5.600 +- 0.484;
  tranche_bot +3.42, tight +1.58; no sit-outs.
- minute 20, kit sim 300 t seed 404 cpu, field + station + random: 02-ship +6.815 +- 0.487, B2 +6.853 +- 0.490;
  tranche_bot +5.07, tight +3.44, station -2.17, random -1.67.
- Pooled twin20 effect over the three runs (1,100 tables): -0.13, +0.20, +0.04 -> about +0.04. Level: not worse, but
  not the "rise by more than half the CI" prompt 05 asks. One more candidate on the same function before deciding:
  C = twin on EVERY preflop decision (TWIN_BB 1000), since tranche 0 (blinds and every preflop bet) is always won by the
  better two-card hand at showdown; two runs, seeds 505 and 606.
- minute 22, C run 1 (400 t seed 505 cpu, tranche_bot x2 tight x2): 02-ship +5.354 +- 0.469, C +5.973 +- 0.479
  (C sat out 1 table: table() over 50 ms under load); tranche_bot +2.98, tight +1.69.
- minute 23, C run 2 (300 t seed 606, + station + random): 02-ship +6.716 +- 0.491, C +6.995 +- 0.485; tranche_bot
  +5.01, tight +3.42, station -2.31, random -1.55.
- minute 26, C run 3 (300 t seed 707, confirmation, the packed zip itself): 02-ship +5.748 +- 0.547, C +5.805 +- 0.547;
  tranche_bot +2.90, tight +1.55.
- Pooled C effect, 1,000 tables, same tables as the ship: +0.62, +0.28, +0.06 -> +0.35, every run up. Kept.
- C = twin on every preflop decision: TWIN_BB = 1000 in submission/adapter.py (no hyperion dial; DIALS {}).
- engine.check --clock cpu on the C zip: +12.45 +- 2.81 (tranche_bot +6.38, tight +5.35, station -1.39, random -1.12),
  0 errors, 6 act t/o of 3054 (0.20%; same class as the ship's 4-6). gate 100 t: package 9.830 +- 1.340 vs composite
  (sim) 9.780, paired +0.050 +- 1.566, 0 exc 0 ill, tmo 0.70% (sim baseline 1.73%: the box) -> GATE PASS (load WARN).

CHECKPOINT variant patch decided: 14:48:17 = minute 26 (keep C: two-card twin on every preflop decision).

| 26 (submitted 14:48:32) | out/03-twin.zip | f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa | 2.1 MB / 8.5 MB, import 0.41 s | bot composite, dials {}, adapter TWIN_BB 1000 (two-card twin preflop) | gate PASS +0.050 +- 1.566; engine.check cpu 0 err, t/o 0.20%; kit A/B +0.35 over 1,000 t |

CHECKPOINT final-candidate submission: 14:48:32 = minute 26 (out/03-twin.zip, sha256 f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa).

Frozen known-good: f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa (cp out/03-twin.zip hyperion/frozen/T1.zip)
Verified in the zip itself (kit loader engine.seat.load_module): adapter TWIN_BB 1000, 91 two-card classes mapped,
real 2c2d shown to the bot as AsTs, act() returned 50 (an open to 2.5 bb).

## Uniform kit-sim results per submission (minute 28; 200 tables, seed 9, cpu clock; 2 seats ours, tight x2,
## tranche_bot x2, station, random; load 17-19 with three sims in parallel)

| submission | ours pts +-95% | place | t/o of decisions | err | tight | tranche_bot | station | random |
|---|---|---|---|---|---|---|---|---|
| out/01-cheap.zip | +3.868 +- 0.512 | 4.37 | 271 / 42590 (0.64%) | 0 | +5.204 | +8.697 | -2.177 | -1.362 |
| out/02-ship.zip | +9.120 +- 0.668 | 2.79 | 1202 / 76938 (1.56%) | 0 | +3.853 | +4.942 | -2.405 | -1.425 |
| out/03-twin.zip | +9.162 +- 0.662 | 2.76 | 1193 / 76049 (1.57%) | 0 | +3.270 | +5.473 | -2.300 | -1.510 |

Timeouts: our bot's mean act is 250 us cpu under this load (the kit's tranche_bot 50 us), so the box inflates ours
most; engine.check at lower load gave 0.11-0.20%. The cheap path that would remove them (recipe timeouts) is the
-5 points the cheap row shows, and the latency recipe measured no fewer timeouts in the kit sim: kept as is (noted).

## End of the hour (stop 14:51:16)

Checkpoints (minutes since T0 14:21:57):
- rule sheet and axis classification: 14:24:44 = minute 3
- first valid submission: 14:28:19 = minute 6 (out/01-cheap.zip)
- ship bot gated and submitted: 14:34:17 = minute 12 (out/02-ship.zip)
- variant patch decided: 14:48:17 = minute 26 (keep the two-card twin on every preflop decision)
- final submission: 14:48:32 = minute 27 (out/03-twin.zip)
- stop: 14:51:16 = minute 29 (hard rule 4: one axis patch in the hour; nothing left that a measurement asked for)

Final zip: out/03-twin.zip, sha256 f2d8195cd82ca2833ff055810969156a2f0635cb5d561f146912a56cf21668fa.
Plays: the composite ship bot (hyperion.ship SHIP 'composite', DIALS {}), behind submission/adapter.py with the Stage 5
function twin_hole at TWIN_BB 1000 (every preflop decision sees the hold'em class at the same combo percentile as our
hand's two-card rank; postflop the real cards).

## What slowed us down or broke (minutes) and what would have avoided it

1. No entry template for a kit of module-level functions whose loader drops the bot folder from sys.path and the
   helper modules from sys.modules after import (3 min adapting entry_template.py). Its hand_end copies kit G's
   r.won as the deltas; here won is chips collected (delta = won - sum(paid)): a silent wrong-stacks bug if pasted.
   Fix: a module-function entry template, and a TODO line "won = collected or net?" in the template.
2. Gate seat for a non-fake kit (2 min writing submission/gate_seat.py; by_street saved most of it). Fix: ship a
   seat template for a module-function, relative-seat, log-string kit (this kit's shape is kit G's plus ints).
3. Kit checker under load (2 min): the wall-clock check prints PROBLEMS for every bot including the kit's own; the
   cpu clock still shows 0.1-0.2% for ours. "Passes the kit's checks" had to be decided (OPERATOR ANSWER above).
   Fix: the playbook should state the pass rule for the organisers' checker on a loaded box.
4. pytest -m "not timing" (0 min of attention, one heavy slot for 6.5 min): 16% done after 5.7 min at load 18,
   killed by its timeout, no signal. Fix: a 1-minute night subset (adapter, conformance, pack) for loaded boxes.
5. Conformance to_call_bets (1 min): 4-18 per run, the kit's "others must still call the full big blind" after a
   short blind. Fix: a Rules flag for that blind rule so the check knows it.
6. The latency recipe (4 min): tools/latency.py said it halves act time; the kit sim showed the same mean, the same
   timeouts and lower points. Fix: prompt 04 step 4 should verify a latency recipe in the kit's own sim.
7. The twist has no prompt-05 section and our sim cannot represent per-street pots (no hook for them; generic aware
   check impossible): designing the twin and measuring it took 14 min of kit-sim A/B (the 20 bb version, 1,100 tables,
   level; the all-preflop version, 1,000 tables, +0.35). Fix: a catalog entry for street-settled pots, or a
   settle-hook example that splits the pot by street, so our sim and the aware field can play it.
8. Conflicting keep rules (1 min): prompt 05 "rise by more than half the CI", PLAYBOOK Stage 5 "did not drop beyond
   the CI", the brief "not worse". Fix: one rule in all three places.
9. No Stage 0 number re-measured with tonight's rules (one person playing both roles): prompt 04's "within the CI of
   Stage 0" could not be judged. Fix: pre-compute Stage 0 per likely schedule, or drop the clause on a solo night.
10. Two NIGHT.md lines mangled by backticks in an unquoted heredoc (1 min, my own slip).
11. Load (no minutes, but noise everywhere): 1.2-1.9% timeouts in the strict sim, gate and kit sim; two table()
    sit-outs over 50 ms in 2,200 seat-tables (median table() 0.16 ms); SafeBot panic lines on stderr.
