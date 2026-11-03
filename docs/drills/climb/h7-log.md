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
