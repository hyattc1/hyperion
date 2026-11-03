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
