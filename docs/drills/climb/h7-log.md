# H7: the drill 11 fixes (branch climb/h7-drill11-fixes)

Drill 11 (kit I, Tranche Hold'em; docs/drills/prompt-drill-11.md and docs/drills/drill11/) left ten items. This pass does
items 1-6 and 8-10; the twist itself (item 7 there: street-settled pots in our engine and catalog) is V-j's. Base: main
8310cc0 (main moved to f5c49bb during the pass, a RESUME edit only). Host: 8 cores shared with the climb's runs, load
16-19; at most two heavy processes of mine, `nice -n 10`, `timeout` on the long ones. Tests: tests/test_h7_drill11.py
unless named. Scratch: the session scratchpad, `goal/h7/`.

## Item 9: `python -m hyperion.ship --set` keeps the line

`write_record(path, name=None, dials=None)` (hyperion/ship.py) now replaces only the value it is given, and only when it
changes, in place: the SHIP string keeps its quotes, `DIALS: dict` its annotation, both their comments. `main()` passes
the name only with `--bot` and the dials only with `--set`. tools/pack.py's call is unchanged (it gives both; an unchanged
value is left alone). Before, both lines were rewritten from `repr()` every time: the pinned repo's diff showed
`SHIP = 'composite'` for `SHIP = "composite"  # the composite (...)`.
Tested: `--set survival` on a copy changes the DIALS line only (diff of one line), `--set ''` restores the file byte for
byte, `--bot hero` keeps the double quotes and the comment, `--bot composite` back gives the original file.

## Item 5: the full big blind after a short blind post

`Rules.extras["full_bb_call"]` (an extras flag, not a Rules field: extras are outside Rules' hash and compare, so no
table fingerprint or cached result moves). hyperion/drills/conformance.py's to_call check, preflop with the flag, runs
from the big blind when max(bets) is below it (kit I: "A bot that cannot cover a blind posts what it has and is all-in.
The others must still call the full big blind"), and the raise-total check with it. Without the flag, a to_call that
matches the full big blind names the flag in the violation text. The conformance module's docstring lists the extras
it reads. Prompt 01's betting line (and the NIGHT template's copy, which test_nightof_docs keeps verbatim) asks the
question and names the flag.
Tested: a three-seat hand with the big blind all-in for 10 of 20: to_call 20 is one `to_call_bets` naming the flag
without it and clean with it; to_call 10 is clean without it and a violation with it; rules_from_dict keeps the flag.
The fake kit I below plays the rule end to end (0 violations with the flag in rules_tonight.json).

## Item 1: the module-function entry template

`hyperion/drills/module_entry_template.py` (a new file rather than an option of entry_template.py: the shapes share
little past the build, and the night copies one file whole). Kit I's shape is the worked default: `start(session)`,
`table(info)`, `act(v)` -> one int, `done(h)`; seats relative to us; no legal list. Everything is imported, built,
started and warmed at import and the package pinned there (the loader drops the folder from sys.path and the helper
modules from sys.modules right after it); every function repins first; `table()` restarts the adapter and bot under
`quick_start` (nothing read or built inside the 50 ms). Every wrapper is `except Exception`, so the kit's Overtime ends
the call; done() builds its whole translation before the one call into the bot. TODOs 0-5: the hand end's clock
(`HAND_END`), the answer type and check-or-fold, the warm-up (kit I's v and h, made up and consistent: three streets'
worth of fields, `u` on the uncalled flop bet), the hand end with **TODO 3a "won: chips collected or net change?"** and
both formulas, the rules the session must match (points, blinds, stack, hands per level, hand cap: a difference is
counted on the error line), the seat and seat count at a table. Two checks that turn silent bugs into counted ones:
`deltas_sum` (a hand end whose deltas do not sum to 0: the `won` formula the wrong way round) and `rules_<field>`.
tools/pack.py leaves the vendored copy out (SKIP_NAMES), as it does the other two entry templates.
The same TODO 3a, both formulas, is now in entry_template.py (its hand end computes the deltas first, kit G's net, and
counts `deltas_sum`), process_entry_template.py (Session.end: kit H gives stacks after; a `won` kit's two formulas),
event_player_template.py (TODO 11), adapter_template.py (TODO 8's hand end) and both older gate seat templates (the
reverse: what a seat must send).

Tested (tests/test_h7_drill11.py, a fake kit I written from the handout: module functions, the loader's purge, setitimer
and Overtime at the limits, chips-now ints with kit I's min-raise and no-reopen rules, the full big blind after a short
post, `u`, no cards after the betting, one pot with side pots, `won` collected):
- two copies of the template in one table (seats 0 and 4, each its own module and start(), as the kit seats them),
  each right after a 15-chip folder so a short big blind comes up: right after each import the folder is off sys.path
  and `adapter` out of sys.modules; two tables in one session (70 hands): every answer an int, the error line empty,
  0 conformance violations with `full_bb_call` (2 short-blind spots played), folds, calls, checks and raises, no
  adapter fallback;
- the template with kit G's line pasted on kit I (`deltas = won`): `deltas_sum` counted on 10+ of 25 hands;
- the loader (and the gate seat's copy of it) drops the folder and its helper: an import inside act() raises
  ModuleNotFoundError, one at the top of bot.py works;
- Overtime raised by sys.settrace at a spread of lines (2 to 6,000) inside 14 act() and 8 done() calls of one table:
  every one ended the call (none swallowed), and every later call answered an int, with nothing swallowed on the
  error line, no adapter fallback and no SafeBot error.

## Item 2: the gate seat for a module-function kit

`hyperion/drills/module_gate_seat_template.py`, standard library only. Its `load_entry(path)` is the kit's loader (the
folder first on sys.path for the import, then off it, every copy, and every module from the folder out of
sys.modules); tools/gate_host.py calls a seat's `load_entry` instead of its own import when the seat has one (as it
honours `PROCESS = True` for the process seat). The seat raises the kit's Overtime with signal.setitimer at kit I's
limits (start 3 s, table 50 ms, act and done 1 ms; TODO 1): a cut act() answers the kit's 0 (and the gate counts it
late), a cut done() is counted, a cut table() sits the table out, a cut start() the session; a call that caught the
Overtime and returned is raised to the gate as an error (GATE FAIL). `native` builds kit I's v from the gate's state
(relative seats, paid per street, tranches, chips-now min_raise, the log with the posts, chips added and `!`); `parse`
maps the int to (kind, raise-to total) by kit I's rule and rejects anything but an int; `end` builds kit I's h with
`won` = delta + what the seat paid, the top bet nobody matched given back as `u` (and off paid), stacks tracked from
the table start. The seat's `gate_counts` go back with the table's close and tools/gate.py prints their sums
(`note: seat counts ...`). gate.py and gate_host.py name the seat in their headers.
Tested: the seat's v on a hand-built flop state (we opened, the button raised the flop) is the log
`6s10 7b20 0r60 1f 2f 3f 4f 5c60 6f 7c40/7k 0r100 5r300 7f`, paid and tranches per street, min_raise 400 chips now,
and the drill 11 adapter reads it with 0 conformance violations; the answers 0/199/200/399/400/5000 map to fold, fold,
call 300, call 300, raise to 500, raise to 1940, and True, "200", 200.0, None are rejected; the hand end (the button's
turn bet uncalled) gives `... 0c200/5r500 0f 5u500`, won 790 for the button and 0 for us, won - paid = the gate's
deltas. A 40 ms act() under the 1 ms limit: cut, 0 answered, counted; one that catches BaseException: RuntimeError.
tools/gate.py (`play`, 1 table) on the template packed `--slim` as pack's main packs it: 0 exceptions, 0 illegal, 0
lifecycle errors through load_entry; on a tiny package whose act() imports its helper lazily, every decision an
exception naming `helper` (one cut by the 1 ms Overtime first: the failing module search under load), and with the
import at the top, none.
Found on the way: `pack.build(..., slim=True)` alone no longer imports the composite (its elite1 member needs
hyperion/sim/field since batch 5); pack's main puts those modules back (`keep_built_modules`), so the CLI is fine; the
test calls the same two steps.

By hand (items 1-2), kit I's own tools on the template built for kit I (the drill 11 player's adapter, its
rules_tonight.json plus `full_bb_call`; `tools/pack.py --slim --import-budget 3 --max-mb 25 --max-zip-mb 5`: 4.8 MB / 1.1
MB zip, import 2.17 s at load 17):
- `engine.check --clock cpu` with HYPERION_CHECK=1: `entry: swallowed errors 0`, conformance 4,036 observations, 0
  violations (drill 11's adapter alone had 4-18 `to_call_bets` a run), fold 1,282 / check 410 / call 168 / raise 2,175.
- Its timeouts are the box's: four checks at load 15-16 alternating the template's zip and the player's own
  out/03-twin.zip, act over 1 ms on the CPU clock: template 50/3,522 and 43/3,595, the player's 78/3,886 and
  36/3,912 (the kit's tranche_bot 18-28 in the same runs). Drill 11 saw 0.11-0.20% at load 17-19; the box is noisier
  today, the two zips alike.
- `tools/gate.py --kit gate_seat.py (the module seat) --entry bot.py --tables 20`: GATE PASS, +0.700 +- 3.000, 0
  exceptions, 0 illegal; `note: seat counts ... act_overtime 79, done_overtime 39`: 118 Overtimes raised inside the
  bot by the seat, none swallowed, nothing broken after them; tmo 2.34% against the in-sim baseline's 2.47% (load
  clause WARN).

## Item 3: the organisers' checker on a loaded box

The pass rule, in prompt 02 step 6 (the zip's first check, kit I's `python3 -m engine.check <zip> --clock cpu`) and
PLAYBOOK Stage 2; prompt 04 step 5 runs it on every repack by that rule. The wall clock flags every bot under load,
the kit's sample bots too; use the CPU clock if the checker has one; pass = layout, size caps and loading fine, 0
errors, and our timeouts per decision no worse than the worst of the kit's sample bots in the same run, the box's load
written beside it. No CPU clock: the same rule on the wall clock with nothing else heavy running; ours worse than the
kit's bots there is ours (prompt 04 step 4). The drill's operator answer had read it the same way.
Tested: the rule's words in prompt 02 and PLAYBOOK Stage 2, prompt 04's pointer. Measured by hand above: today's box
fails the "no worse" half for both the template's zip and the drill's own (1.2-2.0% against tranche_bot's 0.4-0.5%):
the rule says that is ours to fix, and prompt 04 step 4 is the fix; I did not soften it.

## Item 4: the one-minute night subset

A `night` pytest marker (pyproject.toml). Marked: tests/test_nightof_conformance.py, test_nightof_history.py and
test_kit_shapes.py whole (adapter shapes, conformance, history); in test_nightof_pack.py the build/verify/zip test,
the broken-import fail, the row helpers and the slim build; the entry template's loader tests and its warm-up and
table-start tests (test_h5_drill9.py); the process template's round trip and quiet import (test_h6_drill10.py); the
ship switch's build, recipes/--set, governor and adapter hand-end tests (test_ship.py); the inference unit tests and
kit B end to end (test_infer_history.py); the event tracker's unit tests (test_drills_events.py); H7's template,
seat, switch and doc tests. 147 tests: 49.7 s and 51.5 s wall at load 17-20 (collection 11 s of it). Left out on
purpose: anything over ~5 s (pack's cap test, 16.5 s; the inference's real-table recall, 20 s; the gate runs) and
anything on a wall clock. Two marked tests failed under load before the pass and are fixed: test_nightof_pack's row
check asserted an import under 1 s ("import 0."; 1.4-1.8 s at load 17): it now checks the row carries an import
time; test_nightof_conformance's kit C run ran out of kit C's pooled 1 ms clock at decision 69 of 74: it now runs at
50 ms a decision (the test is the report, not the clock). Prompt 02 step 5 and prompt 00 run `-m night` (prompt 02
keeps the full suite for the day: `-m "not timing"`, which test_h5_drill9 still checks), PLAYBOOK Stage 2 names it,
and CONTRACTS.md's commands list it (tools/apicard.py regenerated; `--check` passes).
Tested: `pytest --collect-only -m night` collects 100-220 tests including each group above, `-m "night and timing"`
collects none, the marker is registered, prompts 00 and 02 name it. Five timed runs of the subset at load 14-20: 69 s
(with the cap test, then dropped), 49-57 s after.

## Item 6: the latency recipe, verified in the kit's own simulator

Prompt 04 step 4: a recipe (`latency`, then `timeouts`) is kept with `--set` only when the kit's own simulator shows
it, the same tables with and without it, paired (two seats each, the same seed, its CPU clock if any): fewer timeouts
and points not down beyond noise; tools/latency.py alone is not the check (drill 11's numbers quoted). The recipe's
description now says what `latency` is on the composite (no shadow decisions), as hyperion/ship.py has it. Prompt
06's `latency` line and PLAYBOOK Stage 6's hard-rules line say the same. Tested: the words in prompts 04 and 06.

## Item 7: one keep rule

Written once, in prompt 05 (**The keep rule**): measured paired, the same tables with and without the patch, in our
simulator with `--variant` when it can play the twist (a catalog entry or a hooks file), else the kit's own simulator
(the patched and unpatched zip in the same tables, two seats each, the same seeds); the most tables the box allows,
never fewer than 600 paired tables (pooled over seeds); kept when the pooled point estimate is above zero and no
paired check (each run, and the generic-aware check) is down beyond its 95% interval; else reverted. The measuring
commands under it are now paired too: `climb_accept --stages window ... --variant` for dials (1,600 paired tables),
`hyperion.sim --tables 600` with and without `--dials` for a fallback bot climb_accept cannot build, the kit's
simulator for an adapter function; the generic-aware check (800 paired) is the rule's second check. Pointers, no
restatement: PLAYBOOK Stage 5 and its stage-table row, hard rule 6 (a patch ships only by the keep rule; when neither
our sim nor the kit's can see it, it does not), prompt 00's priority (3) and the prompts README's 0:40 row. The three
old phrasings ("rise by more than half their CI", "did not drop beyond the confidence interval", "the score did not
drop") are gone. Decision noted: "above zero" alone would keep a +0.01 patch over 600 tables; the rule as given asks
for that and nothing more, and the drill's kept twin (+0.35, every run up) passes it while its 20 bb version (+0.04
pooled over 1,100) also would, where the old prompt-05 rule dropped it. I kept the rule as specified.
Tested: the rule's parts in prompt 05, written once; no old phrasing in PLAYBOOK or any prompt; the pointers.

## Item 8: the Stage 0 clause on a solo night

Prompt 04 step 2: with no Stage 0 number under tonight's rules (one person in both roles, nobody re-measured it),
skip the "within ship's own ±95% of Stage 0" clause and write "Stage 0 clause skipped: no number under tonight's rules"
in NIGHT.md. The PLAYBOOK stage table's Stage 4 row says skipped and noted; prompt 01's header line says the solo
night leaves it empty. Tested: the words in prompts 04 and 01 and the PLAYBOOK row.

## Item 10: prompt 05, pots settled by street

A bullet under "Payoff moved": a street-settled twist (drill 11's Tranche Hold'em) is measured in our sim with
`--variant` when the catalog has the entry (V-j's, with Rules fields for how the pots settle; `python -m
hyperion.drills.variants --list` says), else in the kit's simulator; the first move is drill 11's kept patch, the
two-card twin preflop (the hold'em class at the same combo percentile as the two-card rank, real cards from the
flop; `twin_hole` in docs/drills/drill11/adapter.py), kept by the keep rule (+0.35 over 1,000 kit-sim tables; the
20 bb version level). Seven lines; V-j may extend it. Tested: the bullet names --variant, twin_hole, the keep rule and
the kit's simulator, and the drill's adapter has twin_hole.
