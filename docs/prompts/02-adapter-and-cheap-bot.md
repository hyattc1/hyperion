# Prompt 02: adapter and cheap bot (minute 7; hard stop at minute 15 with a submission)

Using the rule sheet, write the adapter and submit our cheap bot. Time box: 8 minutes. One upload per
five minutes is allowed (§3.5): if the adapter is not clean at minute 12, upload the kit's own example
bot at 12 and ours at 17 earliest. Never promise two uploads inside five minutes.

Track A (repo present):
1. Copy `hyperion/drills/adapter_template.py` to `submission/adapter.py` and fill its TODOs in order;
   each names the Observation field it feeds and its one-line test. If a reference adapter in
   `hyperion/drills/adapter.py` fits the kit, subclass it unchanged. Construct it with `Rules` from
   `rules_tonight.json`. Pass the kit's action log as `history` (TODO 7b): Hero reads who raised from
   it alone, and an empty history cost 2.5 points a table in drill 6; with no log, `make_observation`
   rebuilds the raises from the bets.
2. The kit's entry point builds `bot = hyperion.ship.make_bot()` behind `make_adapter(bot, rules)`, with
   everything imported and warmed at module import, not on the first decision; if the kit has no
   per-table hook, `start()` a throwaway adapter at import so every cache is hot before the first
   packet. `make_bot()` builds whatever the package records (step 6 packs it with `--bot cheap`:
   `Hero.cheap()` now; Stage 4 repacks the same entry as the shipped bot). If the kit's hand-end signal
   carries the hand's actions or every seat's chip change, pass them to `hand_end` (template TODO 8). A variant decision the kit asks for (discard, swap, buy) goes to
   `bot.variant_decide({"decision": ..., "hole": ..., "board": ...})`, never through `act`.
3. `native_safe` is the kit's check-else-fold, or a legal default when the only legal move is a variant
   move (a discard): fold is illegal there. Every kit call is wrapped so any exception returns it.
4. Kit's local simulator, 50+ hands, `HYPERION_CHECK=1` (every Observation checked, report at
   exit); show the output. Required: zero exceptions, zero illegal actions, zero conformance
   violations, under 0.3% of decisions over 1 ms (a lone spike on a sub-0.1 ms median is the OS: note
   it and go on; if the box load average exceeds the core count, re-run on a quiet box before failing
   the gate; the rate is 0.3% at normal load), and the report's action counts show fold, check-or-call
   and raise each at least once.
5. `python -m pytest -q` from the repo root; it must stay green. It takes 3 to 5 minutes and never
   imports `submission/`: run it while step 6 packs.
6. `python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py
   submission/rules_tonight.json --bot cheap --note "cheap bot"`: it vendors `hyperion/`, `tables/` and
   the variant set `rules_tonight.json` names (read its `tables` line), records the bot (`bot cheap`
   line) in the package's `hyperion/ship.py`, times a fresh-process import and bot build (fails over
   5 s), checks 100 MB, zips with the entry at the top level, prints the sha256 and writes the
   Submissions row in `NIGHT.md`. If the rules name another layout, match it and say so. Tell me to upload.
7. After the upload, gate that zip once: `python tools/gate.py dist/submission.zip --kit <a|b|c|d>
   --tables 30 --rules rules_tonight.json` (plus `--variant <name>` if the catalog has it). It imports
   the zip as the organisers would and plays it in our sim, paired against the bot the package records,
   in-sim (`baseline bot cheap` line: `Hero.cheap()`). A kit that is none of the fake kits: first write `submission/gate_seat.py`, class
   `Seat` copied from `KitA` in `tools/gate_host.py` with `native` and `parse` changed for this kit, and
   pass `--kit submission/gate_seat.py --kit-module <their kit.py>` (a subprocess kit unlike c or d:
   say the gate cannot run). Required: `GATE PASS`. It proves the reverse adapter now, so Stage 4's gate
   is one command; a FAIL on the delta means the adapter loses something the sim's Hero has.

Track B (blank directory): steps 1 and 4 are "one file, no vendoring". `submission.py` is steps 0 and 1
of the from-scratch spec I pasted: the rank map at parse time, the safe wrapper and clamp first, the
premium and playable lists, push or fold under 12 bb effective, call with top pair or better postflop,
fold otherwise, no bluffs; about 150 lines of code, standard library only. Step 5's suite is
`test_bot.py` (the card parser with the two-character ten, the two hand lists, one legal-action check),
written now and kept green from here. Step 4's run is the kit's own runner for 50 hands plus
`bench.py`'s 2,000-call loop: zero exceptions, zero illegal actions, under 0.3% of calls over 1 ms (same
load clause), p99 under 500 µs; over 100 hands the action mix shows fold, check and raise each at least
once (a call is not required: the tight list made none in 100 hands in drill 3). Zip with
`submission.py` at the top level, record the sha256 and the minute in `NIGHT.md`, tell me to upload.

Do not optimize anything. Do not touch strategy. Report with the command outputs, not prose.
