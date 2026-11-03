# Prompt 02: adapter and cheap bot (minute 7; hard stop at minute 15 with a submission)

Using the rule sheet, write the adapter and submit our cheap bot. Time box: 8 minutes. One upload per
five minutes is allowed (§3.5): if the adapter is not clean at minute 12, upload the kit's own example
bot at 12 and ours at 17 earliest. Never promise two uploads inside five minutes.

Track A (repo present):
1. Copy `hyperion/drills/adapter_template.py` to `submission/adapter.py` and fill its TODOs in order;
   each names the Observation field it feeds and its one-line test. If a reference adapter in
   `hyperion/drills/adapter.py` fits the kit, subclass it unchanged. Construct it with `Rules` from
   `rules_tonight.json`. History (TODO 7b): say which the kit gives. A full action log: pass it as
   `history`, `history_source = "log"`. Some actions (this street, the last few, each player's last
   action): pass those, `history_source = "partial"`. None: leave `history` out, `history_source =
   "bets"`. For "partial" and "bets", `Adapter.decide` rebuilds the hand's log from the states it sees
   (`hyperion/drills/infer_history.py`: every fold, call, check and raise between our decisions; never an
   action that did not happen). It wins back 0.5 to 0.9 points a table, 86-95% of what a missing log
   costs. Do not write
   your own rebuild and do not override `decide`; the rebuild needs TODO 3 (pot), 6 (seats, in_hand) and
   the stacks exactly right. Drill 6's empty history cost 2.5 points a table.
   An event-driven kit (no state snapshot, one call per event): copy `hyperion/drills/event_player_template.py` as the entry instead (EventTracker keeps pot, stacks, bets and the log; worked example `hyperion/drills/event_example.py` on `fakekits/kit_e_style`), and for step 7 `hyperion/drills/gate_seat_template.py` as `submission/gate_seat.py` (hand end untimed).
2. The zip flattens `submission/`: the entry imports its adapter as a sibling (`from adapter import ...`), never
   `submission.adapter` (drill 8's first package failed the kit's import check on it). A kit that builds a bot object
   (class Agent and callbacks): copy `hyperion/drills/entry_template.py` as the entry and fill its TODOs.
   The entry pins the package at import (`pin_package()` after the bot is built and warmed, `repin_package()` at the
   top of every method): kit G's loader unloaded our modules before `Agent()` was built (drill 9), kit F's after it.
   The rule sheet's timed hand-end callback (prompt 01) sets the template's `HAND_END`: timed (kits E, F, G: 1 ms, a
   late one check/folds the next decision), `"defer"`: `bot.defer_hand_end(True)`, the callback runs only the light
   part and the ICM curve waits for the next decision (`"store"` moves all of it there: on kit G, twice the late
   decisions); untimed, `"eager"`.
   The kit's entry point builds `bot = hyperion.ship.make_bot()` behind `make_adapter(bot, rules)`, with
   everything imported and warmed at module import, not on the first decision; if the kit has no
   per-table hook, `start()` a throwaway adapter at import so every cache is hot before the first
   packet. `make_bot()` builds whatever the package records (step 6 packs it with `--bot cheap`:
   `Hero.cheap()` now; Stage 4 repacks the same entry as the ship bot, see the switch). Pass `hand_end`
   whatever the kit's hand-end signal carries (template TODO 8): the hand's actions (`history=`), every
   seat's chip change (`deltas=`), the hands at showdown (`showdown=`, only if the kit shows every hand
   still in). With only our own chip change, pass that: the adapter holds the hand end for the next
   hand's first state, whose stacks settle the folds after our last decision. A variant decision the kit asks for (discard, swap, buy) goes to
   `bot.variant_decide({"decision": ..., "hole": ..., "board": ...})`, never through `act`.
3. `native_safe` is the kit's check-else-fold, or a legal default when the only legal move is a variant
   move (a discard): fold is illegal there. Every kit call is wrapped so any exception returns it.
4. Kit's local simulator, 50+ hands, `HYPERION_CHECK=1` (every Observation checked, report at
   exit); show the output. Required: zero exceptions, zero illegal actions, zero conformance
   violations, under 0.3% of decisions over 1 ms (a lone spike on a sub-0.1 ms median is the OS: note
   it and go on; if the box load average exceeds the core count, re-run on a quiet box before failing
   the gate; the rate is 0.3% at normal load), and the report's action counts show fold, check-or-call
   and raise each at least once. On a kit with no or a partial log the report's history line says how
   many hands the rebuilt log stopped at a gap: near 0. Over 5% is a `history_gap` violation: the pot,
   bets, stacks or in-hand flags disagree with the betting (pot with this street's bets in it, a folded
   seat still in hand); fix TODO 3 or 6, not the rebuild.
5. `python -m pytest -q -m "not timing"` from the repo root; it must stay green. It takes 3 to 5 minutes and
   never imports `submission/`: run it while step 6 packs. On the night it always runs with `-m "not timing"`: the
   wall-clock tests (budgets, slow-box, hand-end timing) fail on a loaded box and say nothing about the adapter
   (drills 8 and 9 lost minutes reading them); the default `python -m pytest` still runs everything.
6. `python tools/pack.py --entry submission/<entry>.py --out dist/ --extra submission/adapter.py
   submission/rules_tonight.json --bot cheap --note "cheap bot"`: it vendors `hyperion/`, `tables/` and
   the variant set `rules_tonight.json` names (read its `tables` line), records the bot (`bot cheap`
   line) in the package's `hyperion/ship.py`, times a fresh-process import and bot build (fails over
   5 s), checks 100 MB, zips with the entry at the top level, prints the sha256 and writes the
   Submissions row in `NIGHT.md`. If the rules name another layout, match it and say so. Tell me to upload.
7. After the upload, gate that zip once: `python tools/gate.py dist/submission.zip --kit <a|b|c|d>
   --tables 30 --rules rules_tonight.json` (plus `--variant <name>` if the catalog has it). It imports
   the zip as the organisers would and plays it in our sim, paired against the bot the package records,
   in-sim (`baseline bot cheap` line: `Hero.cheap()`). A kit with no action log (the rule sheet says so):
   add `--kit-log no`, so the in-sim bot sees only what the kit gives, through the same rebuild
   (automatic for fake kits b, c, d); an adapter that loses the rebuild then fails the gate. A kit that is none of the fake kits: first write `submission/gate_seat.py`, class
   `Seat` copied from `KitA` in `tools/gate_host.py` with `native` and `parse` changed for this kit (its log in the
   kit's own shape, per street and with the blinds posted: the state's rows carry each action's street and chips and
   `posts` the forced bets; `hyperion/drills/gate_seat_template.py`'s `by_street` groups them, `kit_g_log` is drill
   9's kit worked through), and
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
