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
