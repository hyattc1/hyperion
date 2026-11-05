# H8: the drill 12 fixes (branch climb/h8-drill12-fixes)

Drill 12 (kit J, Trailing Stop Hold'em; docs/drills/prompt-drill-12.md and docs/drills/drill12/) left seven items. Base: main
ad63e00 (main moved on during the pass, climb log edits only). Host: 16 threads shared with the climb's runs, load 14-19; at
most three workers of mine, `nice -n 5`. Tests: tests/test_h8_drill12.py unless named. Scratch: `goal/h8/`. Only the night's
tooling and table-start housekeeping changed; decisions are unchanged (Identity below).

## Item 1: a table start never collects

**What it was.** `table_freeze` (hyperion/strategy/hero.py) ran `gc.unfreeze(); gc.collect(); gc.freeze()` one Hero table start in
32, which is one table in 16 of the composite (two Heroes). Unfreezing puts every object of every copy of the package in the
process back in reach: measured alone at load 14, the best of five, 4.4 ms with one copy and 17 ms with four; inside `sit_down` at load
14-18, 5.9-14 ms and 24-37 ms. Each module copy keeps its own count, so four seats in one process run it four times as often.

**The fix.** A table start only freezes, which costs nothing (`gc.freeze` moves lists: 0.000 ms). Why the collection is not needed there:
- R2 added it for frozen objects that die in a reference cycle. One bot reused across tables pins none: over 500 kit J tables a
  full collection afterwards frees 0 objects either way, with the old code and the new, and RSS climbs alike (84 to 89.3 MB new, 84
  to 90.2 MB old; the climb is the sim's and the memos', as R2 found). The frozen count does grow by about 50 a table with no
  collection: tuples a collection would only untrack, not free.
- A fresh bot per table (R2's failure 1, 70 KB a table) is handled by not pinning it: a bot's first table start leaves it unfrozen,
  unless it is the first start in the process (which freezes what it loaded). 500 fresh bots: +0.3 MB, frozen +0, 223 tracked objects
  unfrozen. tests/test_lifetime.py's bound tightens from `frozen < 26 * 32` to `frozen < 26`.
- A fresh import per table (R2's other failure) still collects at import, on the import's clock: `refreeze()` unchanged. 5 re-imports:
  +13.1 MB, frozen -11.

**Timing, before and after.**

| Measure (kit J's zip, the same adapter and entry, load 14-18) | before | after |
|---|---|---|
| sit_down, one copy, 320 tables (CPU ms) | p50 0.34, p99 5.85, max 7.52 | p50 0.32, p99 0.67, max 2.83 |
| sit_down, four copies, 1,280 starts (CPU ms) | p50 0.35, p99 24.26, max 29.22; 8 over 25 ms, 80 over 10 ms | p50 0.36, p99 0.90, max 3.09; 0 over 10 ms |
| `tools/latency.py --table-start --copies 4`, 512 starts (wall ms) | p99 36.72, max 59.07; FAIL, 31 over 25 ms | p99 0.82, max 3.01; OK |
| Kit simulator, 4 copies + 4 others, 400 tables, seed 41, run side by side, CPU clock | `setup` 100 (25 a seat, 6.25%), autopilot 14,404 decisions | `setup` 0, autopilot 0 |
| the same run, decisions | mean 297.5 us, p99 690 us, tmo 441/200,756 (0.22%) | mean 293.8 us, p99 670 us, tmo 552/212,655 (0.26%) |
| the same run, RSS and peak | 275 and 287 MB | 275 and 290 MB |
| the same run, points (fair share 4.875) | 4.94 ± 0.25 | 5.03 ± 0.25 |
| Two more runs, 300 tables, seeds 71 and 72, final tree, load 13: `setup` | 70, 68 | 0, 0 |
| the same: autopilot decisions | 9,680, 9,570 | 0, 0 |
| the same: mean, p99 (us) | 267.1, 600; 265.8, 600 | 269.2, 610; 267.5, 610 |
| the same: timeouts | 7/148,285, 9/148,935 | 14/158,010, 9/161,253 |
| the same: points | 4.80 ± 0.28, 4.87 ± 0.28 | 4.88 ± 0.28, 5.08 ± 0.29 |

The first run's timeouts (0.22% against 0.26%, at load 16) made me repeat it: at load 13, 0.005% and 0.006% against 0.009% and 0.006%. The rate is the box's; I see no decision timeouts traded for the table starts. The
frozen count at the end is larger (85,000 against 210,000), which costs nothing in play and is no memory: the RSS columns match.

**Did the pauses move into decisions? No.** A reused bot's collector reaches what it reached before. A fresh bot stays unfrozen, the one real change for a decision's collector, so it is measured on its own in the last two rows.

| Measure, base and branch side by side | base | branch |
|---|---|---|
| `tools/latency.py --hand-end` (20 tables, 3 reps), per-call minimum: hand_end mean, p99 | 102.6, 211.8 us | 100.3, 208.9 us |
| the same, act mean, p99; first act p50 | 86.8, 144.5; 140.7 us | 84.4, 141.9; 138.4 us |
| `--hand-end --defer`: hand_end mean, p99; idle mean | 62.0, 165.5; 39.6 us | 62.2, 167.2; 39.6 us |
| `tools/lifetime.py` 800 tables, one object: CPU p50 / p99 by block | 105.4 / 238.0, 106.0 / 228.2 us | 105.4 / 230.7, 106.1 / 233.0 us |
| the same: collections inside act, gen 0/1/2 | 9 / 0 / 0, 0.3 ms | 0 / 0 / 0 |
| the same: RSS at the end | 116.6 MB | 117.2 MB |
| A fresh bot per table, night field, 60 tables (the sim's and a fresh-bot kit's path): CPU p50 / p99 | 105 / 218 us | 105 / 229 us |
| the same: collections inside act, gen 0/1/2 | 1 / 0 / 0 | 0 / 0 / 0 |

**The check that would have seen it.** `tools/latency.py --table-start --budget-ms <the kit's limit> --copies <our seats>`: per-table p50, p99
and max on the wall and CPU clocks; exit 1 on a wall p99 over the budget or two starts over it on the CPU clock; one start over it alone
(a preemption) is a WARN. Prompt 04 step 4 runs it. tools/gate.py prints the same through the real entry: one extra process of the
package, 64 table starts through the seat's `start`, `--setup-budget-ms` for the verdict (p99 over: FAIL; max over: WARN), since each gated
table is a fresh process and could never show a cost that returns every 16 tables. Tested: a bot whose table start takes 40 ms one time in 16
fails both; budgets above it pass; 64 starts through a closure package on the gate report four at 40 ms.

## Item 2: the closure template and its gate seat

`hyperion/drills/closure_entry_template.py` and `closure_gate_seat_template.py`, kit J's shape worked through. tools/pack.py leaves the entry template out
of the package. The entry: everything built and warmed at import, pinned; `sit_down` -> `decide` with the recap delivered inside it; the first table's
rules checked against rules_tonight.json; `deltas_sum` counted, the literal TODO "won: chips collected or net change?" with both formulas and
"does the figure leave anything out?" (kit J's `net` leaves out an eliminated seat's forfeit). The seat: the kit's loader (`load_entry`), kit J's View from
the gate's state, recaps queued for the next decide, the answer strings, the table-start limit as autopilot (`table_sat_out`), the hard stops raised
inside the call with setitimer, an entry that swallows one is a gate error. Tests: load and play by the kit's loader; hand-built state and answers; the
kit's clock; `tools/gate.py` (`gate.play`, one table) on the packed template with the drill's adapter, its stop patch on and the stop in the engine from
docs/drills/drill12/tonight.py: 0 exceptions, 0 illegal, 0 lifecycle errors, no table sat out.

By hand, kit J's own simulator on the packed template (the drill's adapter, 3.7 MB zip, import 0.59 s), two seats, HYPERION_CHECK=1, 60 tables, CPU clock: `entry: swallowed errors 0` on both copies, 8,424 and 8,279 observations, 0 violations, fold, check, call and raise all played, `setup` 0, 1 timeout of 16,703, +7.59 ± 0.94. tools/gate.py on it, 40 tables: plain rules, PASS, -0.450 ± 1.495, 0 exceptions, 0 illegal, 0 tmo, table start p50 0.33, p99 0.42, max 0.42 ms against 25, and the patch warning (the drill's adapter carries the class with its mode off: a WARN, no more). Stop A on and `--variant tonight.py:variant`, PASS, +0.625 ± 1.295, table start p99 0.41 ms.

For the merge: the other worker's governor change (climb/g1-governor) touches the older templates. This entry template is new, so whatever it adds there belongs here too.

## Item 3: prompt 05

"What a stack can lose moved", 13 lines before "Betting structure moved". It starts with the general question (three lines in NIGHT.md on what makes a normal
fold or a normal call wrong under tonight's rule), then the two checks (folding past the point of no return; a stack you cannot fully lose), then smallest
first with drill 12's numbers. Prompt 01's Payoff line names a stop or floor, so the axis leads there. Tested: the words, the length, the drill's StopBot.

## Item 4: `--variant` for a function patch

Prompt 02 step 7 says it, prompt 04 step 6 points there. tools/gate.py warns, among its last lines, when the package's adapter.py sets `TWIST_PATCH` (a new
line in adapter_template.py, None by default) or wraps `bot.act` in a class of its own (drill 12's StopBot, found with no marker), and no `--variant` is given.
Beyond the warning, the fix at the source: the closure seat reports no stop for anyone unless GATE_VARIANT (which the gate now sets from `--variant`) says the
engine plays the twist, so on plain rules a patch reading the floors stays quiet. Tested: template (none), named (its name), the drill's adapter (the class), the
drill 11 adapter (none; its patch is a function and would name itself); one table through gate.main with and without `--variant`; floors 0 and 60 bb.

## Item 5: the `timeouts` recipe

**Diagnosis.** `{"cheap": True}` on the composite sends every decision to Hero's cheap path, which `tools/latency.py` shows as cheap: `bot.act` mean 50.9 us against
110.7 us, p99 103 against 340. Through a kit it is not, because of the hand end, which kit J delivers inside the timed decide:
- Hero now meets every hand, so it computes its ICM curve on every hand. On the ship bot Hero's curve is lazy and paid only on the hands Hero plays. The cheap path
  reads the curve only to price an all-in.
- `cheap` left the profiler on, though the path reads next to nothing of it: observe at every decision, hand_end at every hand.
- The base's core replayed every hand (`core.end`, `start_hand`) though it never decides.
- The recipe folds most hands, so nearly every decision is a hand's first and carries all of this: 33,000 decisions a run against 60,000.

cProfile through kit J's adapter (40 tables): the curve 1.17 s of 4.07 s in decide, the profiler's hand end 0.58 s, the core's replay about 0.37 s. So the mean per decision
stays near the ship bot's and the p99 above it: at a 500 us limit (200 tables, seed 61, stop A, CPU clock, 2 seats each) mean 220.9 us, p99 620 us against 264.0 and 590. The
rehearsal's 479 us against 405 us was the same comparison at higher load; I could not reproduce those absolute numbers (ship timed out 1.9% here against 14.3% there).

**The fix** (only `cfg.cheap`; normal play takes neither branch): `LazyCurve`, the same curve from the same chips, computed when a decision reads it; no profiler under `cheap`; the
hybrid's hand end skips the core under `_cheap`.

| Kit simulator, 200 tables, seed 61, stop A, `--limit-us 500`, CPU clock | points | timeouts | mean us | p99 us |
|---|---|---|---|---|
| ship (branch) | 8.21 ± 0.52 | 695/60,544 (1.15%) | 255.0 | 520 |
| `latency` (branch) | 8.23 ± 0.51 | 571/61,369 (0.93%) | 215.2 | 490 |
| `timeouts` before | 4.60 ± 0.37 | 673/32,940 (2.04%) | 220.9 | 620 |
| `timeouts` after | 4.51 ± 0.37 | 43/32,146 (0.13%) | 88.1 | 230 |

A second run, no stop patch, 300 tables, seed 52, 1 ms limit: 198.7 us, p99 500, 3 timeouts before; 80.5 us, p99 170, 0 timeouts after; with the profiler kept, 117.1 us, p99 230. Points 4.841 in all three, decisions 49,752 in all three.

**Play of the recipe.** The lazy curve and the skipped replay change nothing, seed for seed (tested). Dropping the profiler matches Hero.cheap()'s "no reads" but is not bit for bit: the cheap path does read `prof.dead_seat`
and `prof.pre_raiser`. In our sim, 150 tables: identical on 8..1; on 14..0 one table moved, 4.080 to 4.093. In kit J's sim 300 tables: identical. I kept the drop: it is a third of the saving and only this recipe plays it.

**Which dial cuts time.** `latency` first, with level points (a sixth off through a kit); `timeouts` for errors or timeouts that `latency` did not cure, a third of the ship bot's time, at 1.6-3.7 points a table. Prompts 04 and 06, PLAYBOOK, and CONTRACTS.md through
tools/apicard.py (`--check` passes).

## Item 6: one adapter, one table at a time

The rule sheet asks (prompt 01 and the NIGHT template's copy, the same words; the setup bullet, so the bullet count stays). The closure, module and entry templates and the adapter template say so.
`TABLES_AT_ONCE` in the closure template builds that many adapters at import (about 15 ms each); `sit_down` takes the one whose table spoke last longest ago, so tables in turn reuse one. A `decide` from a table whose
adapter another table took answers the kit's check-or-fold, never plays on another table's state: `table_overlap` counted, one stderr line. The module template, whose kit names no table in a call, counts `hand_went_back` (a hand number that goes
back after table() restarted the adapter). Tested: tables in turn with old closures held: nothing counted; overlap: `f`/`c` answers, counted, one line, the holder plays on with no fallback; two interleaved tables on TABLES_AT_ONCE 2: every decision
through its own bot, seats apart, no restart.

## Item 7: the drill's other notes

- Prompt 04 step 1: the kit's `setup` column reads 0 (the 6% showed nowhere else).
- Prompt 04 step 4: one paired run of a recipe and no tuning beyond it (the 3-minute chase).
- Prompt 05's keep rule: name eight bots, a kit repeats a short list (the lineup slip).
- Prompt 05: a function patch's aware check is the kit's twist-aware sample bot (the note "aware check not run": only dials can run it).
- Not changed: tools/zip_parity.py stays out of the night (a freeze tool, 90 s, and it skips the adapter); the player's `--night /dev/null` for screening zips (works, no minutes); inert mode letters in the source (no minutes).

## Checks before the end

- Identity (F's play), `tools/climb_accept.py --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`, against goal/idchk39.md: all seven rows the same points, 0 timeouts, 0 errors, level: night 5.928, night_hard 5.735, realistic 6.265, top 5.047, night @10/7/5/4/3/2/1/0 6.098, night @50/25/12/6/3/2/1/1 25.571, night +double 5.925. The p99 column is a clock, not play: my first run, 3 workers at load 18, showed 4125 us on three cells against idchk39's 200, which I checked because a freeze change could do that. Base and branch side by side, one worker each, the same 40 seeds: p99 318-368 us on the branch, 317-520 us on base (night 355/318, night_hard 351/338, realistic 317/276, top 332/342, the two payout cells 343/331 and 372/351, double 520/368). So it was the box.
- Suite, `pytest -q -p no:cacheprovider -m "not timing"`, final code, load 14-19, alongside the identity runs: 1 failed, 1514 passed, 5 skipped, 114 deselected in 17.3 min. The failure: test_nightof_latency's cheap-bot round trip, one 4.08 ms decision in 100 on kit C (wall 9 ms, CPU 5 ms: a scheduler tick). Rerun alone, 4 of 4 pass on the branch and on base.
- `tools/zip_parity.py` on a fresh pack of the branch (composite, dials {}, sha256 aa508e22...): PARITY PASS, 112,522 decisions and 1,779 variant decisions identical over 730 tables; strong 1,105, specialist heads-up 1,533, R6 226; 93.6 s.
- Gate on plain: above, item 2 (PASS). `tools/apicard.py --check` passes.

## Left as it is

- The rehearsal's absolute numbers for the recipe (479 and 405 us, 40% and 14% timeouts at a 500 us limit) did not reproduce: here 221 and 264 us, 2% and 1.9%. The ordering at p99 did, and the cause is in the code path, so the fix does not rest on them.
- Through a kit the composite costs about 2.5 times `bot.act` (mean 255 against about 110 us): the translation, the rebuild and the recap inside the decide. Drill 12's AF cut it without moving p99 and lost points. Not touched here: the governor counting the whole timed call is climb/g1-governor's.
- `TABLES_AT_ONCE` takes the adapter whose table spoke last longest ago, so a table silent through a whole other table can lose its adapter: it then check-folds, counted. Interleaving is tested; threads are not.
- The exclusion list itself lives in the goal scratch prompts, which this pass did not edit: the entry to add is in docs/drills/prompt-drill-12.md.

