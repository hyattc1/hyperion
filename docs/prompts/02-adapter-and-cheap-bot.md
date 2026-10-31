# Prompt 02: adapter and cheap bot (minute 7; hard stop at minute 15 with a submission)

Using the rule sheet, write the adapter and submit our cheap bot. Time box: 8 minutes. One upload per
five minutes is allowed (§3.5): if the adapter is not clean at minute 12, upload the kit's own example
bot at 12 and ours at 17 earliest. Never promise two uploads inside five minutes.

Track A (repo present):
1. Copy `hyperion/drills/adapter_template.py` to `submission/adapter.py` and fill its TODOs in order
   (card encoding, street, pot, raise totals vs increments, legal names, seats and button, blinds,
   per-table init, `native_safe`); each names the Observation field it feeds and its one-line test. If
   one of the four reference adapters in `hyperion/drills/adapter.py` fits the kit, subclass it
   unchanged. Construct the adapter with `Rules` loaded from `rules_tonight.json`.
2. Create the kit's entry point so that it instantiates `hyperion.strategy.hero.Hero.cheap()` behind
   `make_adapter(bot, rules)`, with everything imported and warmed at module import, not on the first
   decision.
3. `native_safe` returns the kit's representation of check-else-fold; every kit call is wrapped so that
   any exception returns it.
4. Run the kit's local simulator for at least 50 hands with `HYPERION_CHECK=1` set, so every
   Observation is checked and the report prints at exit. Show me the output. Required: zero
   exceptions, zero illegal actions, zero conformance violations, under 0.3% of decisions over 1 ms (a
   lone spike on a sub-0.1 ms median is the OS: note it and go on), and the report's action counts show
   fold, check-or-call and raise each at least once.
5. Run our test suite (`python -m pytest -q`) from the repo root; it must stay green.
6. `python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py --note
   "cheap bot"`: it vendors `hyperion/` and `tables/`, verifies the import from a fresh process in another
   directory (fails over 5 s), checks 100 MB, zips with the entry at the top level, prints the sha256 and
   writes the Submissions row in `NIGHT.md`. If the rules name another layout, match it and say so. Tell
   me to upload.

Track B (blank directory): steps 1 and 4 are "one file, no vendoring". `submission.py` is steps 0 and 1
of the from-scratch spec I pasted: the rank map at parse time, the safe wrapper and clamp first, the
premium and playable lists, push or fold under 12 bb effective, call with top pair or better postflop,
fold otherwise, no bluffs; about 150 lines of code, standard library only. Step 5's suite is
`test_bot.py` (the card parser with the two-character ten, the two hand lists, one legal-action check),
written now and kept green from here. Step 4's run is the kit's own runner for 50 hands plus
`bench.py`'s 2,000-call loop: zero exceptions, zero illegal actions, under 0.3% of calls over 1 ms, p99
under 500 µs; over 100 hands the action mix shows fold, check and raise each at least once (a call is
not required: the tight list made none in 100 hands in drill 3). Zip with `submission.py` at the top
level, record the sha256 and the minute in `NIGHT.md`, tell me to upload.

Do not optimize anything. Do not touch strategy. Report with the command outputs, not prose.
