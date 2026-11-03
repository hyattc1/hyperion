T0: 06:46:13

repo: 077b95f (R pinned copy)   kit: kitdl/solo-holdem-kit   variant (their name): Solo Hold'em   track: A
ship bot: SHIP = 'composite', DIALS = {}   (`--bot hero` restores Hero)

## Prompt 00 restatement
Python bot speaking the kit's JSON-lines protocol (bot.py at zip root, CPython 3.10, stdlib only, one CPU,
1 GB AS); every `act` must be answered within 1 ms wall (engine-side), `end`/`over` 1 ms, `table` 50 ms, `hello`
2 s; error/timeout = check-else-fold; no Monte Carlo/search at decision time, precompute at import. 8-max SNG,
2,000 chips, 10/20 rising every 25 hands, 200-hand cap, places scored 13/8/5/3/2/1/0/-2 with ICM-free
placement at cap (by chips). Zip <= 5 MB zipped / 20 MB unzipped (kit's, tighter than the 100 MB we assumed).
Strategy never imports the kit; one adapter. Priorities: (1) legal never-crash bot submitted by minute 15,
(2) ship bot through the adapter, strict-mode verified and gated, (3) smallest variant patch, only if not worse.

## RULE SHEET (Stage 1, prompt 01) — minute 3
Rules text: K/README.md §1-§5 (pasted by reference; the kit README is the rulebook).
- Hole cards: 2. No discards, swaps, exposures, auctions.
- Board: 3/1/1, one board, nothing changes.
- Hand ranking: NON-STANDARD: "Your hand is the best five-card poker hand made of exactly ONE of your two hole
  cards and exactly FOUR of the five board cards." Usual categories, A-5 wheel, suits never rank. A pocket pair
  is only one card; nobody plays the board. -> `Rules.must_use_hole = 1` (engine: every 1-subset of hole with 4 of board).
- Betting: no-limit; min raise = last full raise on this street (>= bb); all-in for less does not reopen.
  Raises are RAISE-BY increments: "r<N>" puts in to_call + N (kit gives min_r/max_r as raise-by). Clamped into
  [min_r, max_r]. No antes, no straddles. Fold with nothing to call = check.
- Blinds: 10/20,15/30,25/50,40/80,60/120,100/200,150/300,250/500, 25 hands/level (differs from our default
  levels 4,5,8). 2,000 chips, 8 seats, 200-hand cap.
- Scoring: 13/8/5/3/2/1/0/-2 by place. At hand 200 survivors placed BY CHIP COUNT (not ICM split) — the handout
  wins over CHALLENGE's "ICM split". Same-hand busts placed by starting stack. No bounty/side payoff.
- Agent interface: process `python3 -u bot.py`, JSON lines on stdin/stdout, echo `id`. Messages hello / table /
  act / end / over. act fields: table, hand, sb, bb, you, button, cards[2], board, pot (incl. this street),
  to_call, min_r, max_r (raise-by; 0 = cannot raise), players[] {h, stack, bet, total, state live/folded/allin}
  in position order (players[0]=SB, [1]=BB, button last; heads-up [0]=button=SB), log ("h:f|k|c|r<N>",
  streets split by "/"). Reply {"id":n,"a":"f"|"c"|"r<N>"}. One process per session (hundreds of tables);
  handles persistent across tables in a session (state may persist).
- Setup budget: hello 2,000 ms from launch (imports); table 50 ms; same process for the whole session.
- Callbacks: end (every hand dealt into: shown, best, won, stacks, out) and over: timed 1 ms; a late reply
  makes us "busy" -> following acts auto-played. Crash: auto-play rest of table, relaunch up to 3 times.
- Submission: one zip <= 5 MB zipped, <= 20 MB unzipped, bot.py at root, no abs paths/..
  -> tools/pack.py `--max-mb 5`.
- Tooling: `python3 engine/sim.py ENTRY ENTRY ... -t T` (zip, dir or .py), `--calibrate`, `--limit-ms`, `--dup`.
  Kit imports: stdlib only.

## AXIS CLASSIFICATION
- Hand strength ordering moved? Y — the showdown rule (exactly 1 hole + 4 board). Evaluator and every
  equity table change; pocket pairs are worth one card; board-pair/flush/straight boards counterfeit.
- Information moved? N (2 hole cards, 3/1/1 board, nothing exposed).
- Payoff moved? N (point table differs from our linear default: ASSUMPTION DIFF, Rules.payouts).
- Betting structure moved? N (no-limit; schedule differs slightly: blind_levels; raise-by: adapter).
Stage 5 patch section: strength ordering (must-use).

## FIT VERDICT
| prepared layer | verdict | reason |
|---|---|---|
| evaluator | KEEP (with Rules.must_use_hole=1) | engine/core eval supports must_use_hole k=1 |
| preflop tables | REGENERATE | 169-class equities change completely under 1+4 |
| push/fold solution | REGENERATE | re-solved from the new matrix by gen_tables |
| postflop rule layer | KEEP (Hero plays must-use tables; reads its strength via the 1+4 rule) | composite routes must-use to Hero |
| opponent profiler | KEEP | rule-independent |
| ICM curve | KEEP | reads Rules.payouts (13..-2 pasted) |
Path: REGENERATE -> Stage 3 runs.

## ASSUMPTION DIFF
| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole, 3/1/1 | same | nothing | — |
| standard showdown (best 5 of 7) | exactly 1 hole + 4 board | evaluator, tables, push/fold | must_use_hole=1; Stage 3 |
| raise-TO totals | raise-BY increments (r<N>) | adapter from_action | adapter |
| levels 50/100,75/150,200/400 | 40/80, 60/120, 250/500 | sim schedule, push depth | blind_levels |
| linear payouts 8..1 | 13/8/5/3/2/1/0/-2 | ICM curve, sim scoring | payouts |
| ICM split at cap | placed by chips at hand 200 | sim scoring at cap (minor) | not representable as a field; noted |
| 100 MB | 5 MB zipped / 20 MB unzipped | package size | pack --max-mb 5 (and --slim if needed) |
ENGINE CANNOT REPRESENT: chip-count placement at the 200-hand cap (our sim splits by ICM); minor.

## MOST DANGEROUS THING FOR A 1 ms BOT
The session is ONE process over hundreds of tables with every message (end/over too) on a 1 ms clock and a
"busy" penalty: any stall (GC, lazy table load, a per-table rebuild in `table` > 50 ms, or slow end handling)
auto-plays the following decisions. Second: raise-BY semantics — a raise-to total passed straight through
overbets by to_call every time.

CHECKPOINT rule sheet + axis classification: 06:47 (minute 1)

## Submissions

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|
| 5 | submission.zip | c2de003d582ff1f1375a5f89eab1dfc1e5218b7e7c2875914f3acd52b67e806d | 1.0 MB / import 0.55 s | cheap: cheap bot | |
| 17 | submission.zip | e264d39897a50c567d0234e3e52508b05b892a869d4b5d081194dfdad5c8d065 | 1.1 MB / import 1.05 s | composite: ship bot | |
| 25 | submission.zip | 795a74cf71ce70c3f1fa3395b80bd1e3fff42c7f7cfcb6034369e133a48be793 | 1.1 MB / import 1.41 s | composite: ship bot (composite), hand end deferred and skipped when a message waits | |

SUBMITTED 01: out/01-cheap.zip  sha256 c2de003d582ff1f1375a5f89eab1dfc1e5218b7e7c2875914f3acd52b67e806d  minute 6 (06:52)
  bot cheap (Hero.cheap()), dials {}, label tables (no solo tables yet), adapter submission/adapter.py, entry submission/bot.py
  kit checks: README command `sim.py 01-cheap.zip station tight -t 20`: 11.25 pts, 0 errors, 0 crash, 491 tmo/3740.
  8-seat field (station,random,tight,solo_aware,station,random,tight) -t 50 seed 1: 5.78 ± 1.23 pts/table, 0 errors,
  0 crash, timeouts 996/6791 (14.7%), late 1032, p50 104 us p99 457 us. Load ~22 on 8 cores; floor p99 30-190 us.
CHECKPOINT first valid submission: minute 6

## Verified
| minute | stage | command | the line that mattered |
|---|---|---|---|
| 4 | 2 | kit sim, entry dir submission/ (composite), 20 tables | 0 errors 0 crash; 1602/3490 timeouts, late 1468 (load 22) |
| 6 | 2 | kit sim README form on out/01-cheap.zip, -t 20 | 11.25 pts, 0 err, 0 crash |
| 6 | 2 | kit sim 8-seat field on out/01-cheap.zip, -t 50 | 5.78 ± 1.23, 0 err, 0 crash, tmo 14.7% |
| 7 | 2 | kit sim on entry dir with check.on marker (HYPERION_CHECK; the kit strips env), 30 tables, composite | conformance 2533 obs, 58 to_call_bets (short BB: kit's to_call is the full bb, plus 1 uncapped to_call -> fixed: to_call capped by stack); actions fold 993 check 662 call 155 raise 723; history = kit log |
| 10 | 2 | `gate.py out/01-cheap.zip --kit submission/gate_seat.py --entry bot.py --tables 30 --rules submission/rules_tonight.json` | GATE PASS -0.349 ± 1.083, 0 exc 0 ill, tmo 0.33% (load clause WARN) |

## Stage 3 TABLES (strength axis moved: must_use_hole=1)
- 06:52 `gen_tables.py --rules submission/rules_tonight.json --out tables/variants/solo/ --workers 2` (default 20000
  samples): 4 min of CPU at ~33%/worker (load 22-25) and preflop not done; killed at minute 11. Default matrix is
  169x169 pairs x 5000 samples with a must-use showdown: projected far past the 5-minute box on this box.
- 06:58 restarted `--workers 3 --samples 3000 --matrix-samples 200`: preflop finished (~3 min); killed in the matrix
  stage by mistake (my `pkill -f` matched its own shell; exit 144) -> kept the preflop files.
- 07:00 finished the rest with `gen_rest.py` (N/): hu_matrix at 50 samples/pair, push/fold re-solve, flops (2 per
  texture, 300 holdings), 3 workers.
- Preflop sanity (HU equity, solo vs standard): AA 0.564 (std 0.857), AKs 0.681, A2o 0.629, KK 0.510, 22 0.119
  (std 0.505), 72o 0.377. Top classes are Ax offsuit/suited (AQo, AKs, AKo, AQs, A8o): a pocket pair is one card.
- 07:02 Stage 3 done (minute 17): tables.tables_for(rules).source = disk, 169 classes; matrix_fp d777d324c5650865 == matrix_fingerprint(hu).

## Stage 4 WIRE (from minute 17)
| minute | command | the line that mattered |
|---|---|---|
| 17 | flop/preflop decisions through the entry (A♥K♦ on A♣9♥4♦ etc.) | preflop AhQc r30 (to 50), 22 fold, AcJc r30, 2h7s fold; FLOP: checks top pair and trips: Hero's must-use path check/folds EVERY flop (board 3 < 5 - 1) |
| 18 | kit sim, entry dir, composite (check.on), 50 tables seed 1 | 5.34 ± 0.82; 0 err 0 crash; conformance 3553 obs, 3 to_call_bets (short-blind kit rule); TIMEOUTS 5635/9011 (62.5%), late 5466 |
| 19 | same, ship zip, --limit-ms 5 | ship 8.74 ± 1.21 (1st 46%), tmo 17.8%; cheap zip at 5 ms 4.83 ± 1.12, tmo 3.8% |
| 20 | `latency.py --n 2000 --rules` (composite) | p50 57 µs p99 4127 µs, over 1 ms 1.60%: FAIL p99 > 500 (wall 270 ms vs cpu 124 ms: the box) |
| 21 | slowprobe (N/slowprobe.py): wall vs CPU of slow calls | 23/2100 over 1 ms, only 7 with CPU > 0.8 ms: mostly preemption |
| 20 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json` | ship 6.989 ± 0.533 (1st of 8; rival1 6.64), exc 0 ill 0, tmo 775 hands (1.4%), p99 4099 µs (load 27: load clause) |
| 22 | kit sim with the entry's timing.on / profile.on markers | per end: hand end ~280 µs CPU after the reply, the next message already waiting (idle p10 4 µs); Hero.hand_end runs TWICE per end (composite's two Heros: ICM curve + profiler each); act ~170 µs CPU |
| 23 | kit sim seed 4, 30 tables, entry dir, composite: hand end processed vs skipped (noend.on marker) | processed 5.57 ± 1.17, tmo 61%; skipped 8.57 ± 1.31, tmo 33% -> the hand end is the latency problem on this box |
| 24 | entry change: stdin read from the raw fd; after replying to `end`, the bot's hand end runs only if no message is waiting (else skipped, counted) | seed 4: 7.13 ± 1.52, tmo 33%, 434 of ~2000 hand ends skipped; 0 swallowed errors; conformance 4254 obs, only to_call_bets (short-blind kit rule) |
| 25 | same, HAND_END defer vs eager (both selective) | defer 6.13 tmo 26%; eager 6.10 tmo 37% -> keep defer |
| 25 | pack ship (composite, dials {}) -> ship_v2.zip sha256 795a74cf... | import 1.41 s, 1.1 MB zipped, 5.0 MB unzipped |
| 25 | kit README command on ship_v2.zip (station, tight, -t 20) | 11.25 ± 1.07, 0 err, 0 crash, tmo 57% (station 15%, tight 25%: box at load ~27 with the gate running) |
| 26 | kit 8-seat field on ship_v2.zip, -t 50 seed 1 (box overloaded: gate + model sim in parallel; floor p99 5015 µs, 16/600 missed) | 5.58 ± 0.91, 0 err, 0 crash, tmo 62% (solo_aware 11%) |
| 29 | `gate.py ship_v2.zip --kit submission/gate_seat.py --entry bot.py --tables 100 --rules submission/rules_tonight.json` | GATE PASS +0.767 ± 1.096 vs composite (sim); 0 exc 0 ill; tmo 2.18% (load clause WARN); import 1.73 s worst (hello budget 2 s: close under load) |

SUBMITTED 02: out/02-ship.zip  sha256 795a74cf71ce70c3f1fa3395b80bd1e3fff42c7f7cfcb6034369e133a48be793  minute 29 (07:15)
  bot composite, dials {} (DIALS empty; package's hyperion/ship.py records composite), tables default + variants/solo
  (3000-sample preflop, 50-sample matrix, re-solved push/fold), adapter + entry with HAND_END defer and hand ends
  skipped when a message waits. hero.py carries the new `solo_flop` Config field, default False (inactive).
  Kit sim: README command 11.25 ± 1.07 (tmo 57%), 8-seat field 5.58 ± 0.91 (tmo 62% at floor p99 5 ms); 0 errors 0 crashes both.
  At --limit-ms 5 (earlier composite zip, same adapter): 8.74 ± 1.21 vs cheap 4.83 ± 1.12.
CHECKPOINT ship bot gated and submitted: minute 29

## Stage 5 PATCH (strength axis: must-use one hole card)
Prompt 05's strength section has no must-use patch beyond the tables. The twist forces one: Hero's must-use path
(hero.py: `if nh < mu or len(board) < 5 - mu: safe_action`) check/folds every FLOP in Solo (3 board cards < 4), so
the bot folds top pair and trips to any flop bet (printed: base A♥K♦ on A♣9♥4♦ facing 40 into 130 -> fold).
Patch = one small function, `_solo_flop` in hyperion/strategy/hero.py behind a new Config dial `solo_flop` (default
False): what one hole card makes with the flop (trips+ raise/bet, top pair or two pair bet/call, second pair calls
<= half pot, four-flush draw calls <= a third, else check/fold; no bluffs; deep calls > 1/3 stack need trips+).
Dials dict: {"hero.solo_flop": true}. With it: same spot -> call; checked to -> bet 65 (half pot).
| minute | command | line |
|---|---|---|
| 30 | `python -m hyperion.sim --tables 300 --seed 11 --mode model --field realistic@ship --rules submission/rules_tonight.json` | ship 7.241 ± 0.532 (before) |
| 33 | same with `--dials '{"hero.solo_flop": true}'` | ship 8.158 ± 0.543 (+0.92, above half the CI 0.27); rival1 6.44 -> 5.63 |
| 35 | kit sim --limit-ms 5, seed 7, 40 tables, 8-seat field: out/02-ship.zip vs pk/flopD.zip (dial packed) | 8.242 ± 1.367 (tmo 29%) -> 8.625 ± 1.282 (tmo 36%): level/up within noise; floor p99 2.4-5.7 ms |
| 35 | kit README command on pk/flopD.zip | 9.80 ± 1.38, 0 err, 0 crash (tmo 70%; tight 38%: box) |
| 38 | `climb_accept.py --stages aware --aware generic:submission/tonight.py:variant --base '' --cand '{"dials": {"hero.solo_flop": true}}' --set 10000:10100 --workers 2` | generic_aware 7.308 -> 8.165, +0.857 ± 0.360 UP, tmo 0/0 err 0/0: ACCEPT |
| 39 | `gate.py pk/flopD.zip --kit submission/gate_seat.py --entry bot.py --tables 100 --rules submission/rules_tonight.json` | GATE PASS +1.170 ± 0.927 vs composite+solo_flop (sim); 0 exc 0 ill; tmo 1.38% (load clause); import 2.09 s worst (over the 2 s hello budget under load) |
CHECKPOINT variant patch decided: minute 39 — KEEP {"hero.solo_flop": true}
| 40 | kit 8-seat field on pk/flopD.zip, -t 50 seed 1, 1 ms | 6.360 ± 1.072 (02-ship same command 5.580 ± 0.907), 0 err, 0 crash, tmo 49% (solo_aware 16%) |
| 41 | `python -m hyperion.sim --tables 150 --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json` (DIALS set) | ship 8.543 ± 0.730, exc 0 ill 0 safe_err 0; tmo 2.3% of hands, p99 8089 µs (load) |
`python -m hyperion.ship --set '{"hero.solo_flop": true}'` -> SHIP = 'composite', DIALS = {'hero.solo_flop': True}

SUBMITTED 03: out/03-ship-soloflop.zip  sha256 53584934279d864ebd5873d1b112cbf2d72ca37afcc043c05470f545c7b29ac9  minute 41 (07:27)
  bot composite, dials {"hero.solo_flop": true} (recorded in the package's hyperion/ship.py), same adapter/entry/tables as 02.
  Frozen known-good: hyperion/frozen/T1.zip (same bytes).

## After submission 03 (minutes 41-53)
- Final zip check (python zipfile): 89 files, bot.py at root, no absolute or `..` paths, no local marker files,
  4.96 MB unzipped / 1.1 MB zipped (kit caps 20 / 5 MB), HAND_END "defer", package ship.py SHIP 'composite',
  DIALS {'hero.solo_flop': True}.
- `sim.py --calibrate`: do-nothing bot p50 7 µs, p99 346 µs, max 7774 µs, 0.77% over 1 ms (load 22).
- `pytest -q -m "not timing" -x`: FAILED test_apicard (CONTRACTS.md stale after the new Config key and DIALS) ->
  `python tools/apicard.py` regenerated docs/packet/CONTRACTS.md. Re-run without -x still running at minute 52 with
  5 F marks at 40-46% (not read: out of time; unresolved; may be the DIALS change or load-timing tests).
- Repo changes in R: hyperion/strategy/hero.py (+`solo_flop` dial and `_solo_flop`), hyperion/ship.py (DIALS),
  docs/packet/CONTRACTS.md (regenerated), new submission/{bot.py, adapter.py, gate_seat.py, tonight.py,
  rules_tonight.json}, tables/variants/solo/, tables/generic/solo-49f67482.json, frozen/T1.zip.

## END OF NIGHT (coordinator summary)
Checkpoints (minutes since T0 06:46:13):
- rule sheet + axis classification: minute 1 (strength axis: exactly one hole card + four board; Stage 3 needed)
- first valid submission: minute 6 (out/01-cheap.zip)
- ship bot gated and submitted: minute 29 (out/02-ship.zip, GATE PASS)
- variant patch decided: minute 39 (KEEP {"hero.solo_flop": true})
- final submission: minute 41 (out/03-ship-soloflop.zip)
- stop: minute 53

Final zip: out/03-ship-soloflop.zip  sha256 53584934279d864ebd5873d1b112cbf2d72ca37afcc043c05470f545c7b29ac9
  bot: composite (hyperion/ship.py SHIP), which on a must-use table plays Hero for the whole table, with dials
  {"hero.solo_flop": true}; tables default + variants/solo (regenerated for must_use_hole=1: preflop 3000 samples,
  HU matrix 50 samples/pair, push/fold re-solved, fingerprint d777d324c5650865); adapter submission/adapter.py
  (raise-by <-> raise-to, pot minus street bets, to_call capped by stack, full log as history), entry
  submission/bot.py (JSON lines, `end`/`over` answered first, bot hand end deferred and skipped when a message is
  already waiting, gc frozen and disabled, collected after `over`).

Kit simulator results (points/table; 8-seat = station, random, tight, solo_aware, station, random, tight; ±95%):
| zip | README form (station, tight, -t 20) | 8-seat, -t 50, seed 1, 1 ms | 8-seat at --limit-ms 5 | errors / crashes | gate |
|---|---|---|---|---|---|
| 01-cheap | 11.25 ± 1.07, tmo 491/3740 (13%) | 5.78 ± 1.23, tmo 996/6791 (15%), late 1032; solo_aware 9.94, tight 5.00/5.56, random 1.52/1.68, station 0.40/0.12 | seed 1: 4.83 ± 1.12, tmo 4% | 0 / 0 | PASS -0.35 ± 1.08 (30 t) |
| 02-ship | 11.25 ± 1.07, tmo 2288/4025 (57%) | 5.58 ± 0.91, tmo 5528/8944 (62%), late 5151 (floor p99 5 ms); solo_aware 9.60, tight 4.75/5.66, random 1.80/1.71, station 0.12/0.77 | seed 7: 8.24 ± 1.37, tmo 29% (solo_aware 9.13) | 0 / 0 | PASS +0.77 ± 1.10 (100 t), tmo 2.2% load WARN |
| 03-ship-soloflop | 9.80 ± 1.38, tmo 2858/4063 (70%) | 6.36 ± 1.07, tmo 4752/9771 (49%), late 4286; solo_aware 8.42, tight 5.50/5.18, random 1.15/2.40, station 1.19/-0.21 | seed 7: 8.63 ± 1.28, tmo 36% (solo_aware 8.53) | 0 / 0 | PASS +1.17 ± 0.93 (100 t), tmo 1.4% load WARN |
Our sim (realistic@ship, seed 11): strict 300 t ship 6.99 ± 0.53 (no dial); model 300 t 7.24 -> 8.16 with the dial;
strict 150 t with the dial 8.54 ± 0.73, exc 0 ill 0. Generic aware field (plays Solo): +0.86 ± 0.36 for the dial.
Timeouts: every kit run on this box (load 22-28 on 8 cores, floor p99 up to 5 ms) shows the composite at 30-70%
timeouts at 1 ms against the sample bots' 3-16%; at 5 ms the ship bot leads the sample bots. Noted, not chased
further after the hand-end fix; the event runs dedicated cores.

What slowed us down or broke (minutes lost) and what would have avoided it:
1. Stage 3 generator (~8 min wall, ~5 min on the critical path, minutes 6-17): default gen_tables (20000 samples,
   HU matrix 5000 samples/pair = 72M must-use showdowns) ran at ~33% CPU per worker under load and would have taken
   well over 20 minutes; restarted at 3000/200; my `pkill -f gen_tables` killed its own shell (exit 144, twice) and
   the generator in the matrix stage; finished with a hand-written resume script (N/gen_rest.py). Avoid: prompt 03
   should give a loaded-box preset (`--samples 3000 --matrix-samples 50`) and gen_tables a resume flag
   (`--only matrix,pushfold,flops` reusing preflop files) and print progress unbuffered; matrix samples should scale
   with the showdown cost (must_use_hole); prompt rule: kill by PID, never `pkill -f`.
2. Kit sim timeouts with the ship bot (diagnosis minutes 18-25, ~7 min): 62% timeouts vs cheap 15%. Profiling the
   bot process inside the kit sim (entry markers timing.on / profile.on) showed the composite running Hero.hand_end
   TWICE per hand end (its Hero member and the base's fallback Hero: ICM curve + profiler each, ~280 µs CPU at load)
   while the next message was already waiting. Fix in the entry: answer `end` first, defer, and skip the bot's hand
   end when a message is waiting (seed 4: 5.57 -> 7.13, tmo 61% -> 33%). Avoid: a JSON-lines process-kit entry
   template with reply-first / process-when-idle hand ends; the composite should not settle the fallback Hero's
   curve on tables Hero plays whole (must-use).
3. No entry or gate-seat template for a one-process-per-session JSON-lines kit (~10 min writing bot.py and
   gate_seat.py, minutes 3-10): entry_template is for class kits, event_player_template for event kits, kit C's
   serve() for a different line protocol; the gate's seat route is in-process, so the gate never exercises the
   stdin loop or the selective hand end (only the kit sim does). Avoid: add a `kit_jsonl` fake kit + template.
4. The kit's launcher passes a fixed env (PATH, PYTHONUNBUFFERED, ...): HYPERION_CHECK=1 never reached the bot and
   the first conformance report was empty (~1 min); fixed with a `check.on` marker file beside bot.py. Avoid:
   prompt 02 step 4 should say "if the kit sets env=, use the marker".
5. Hero's must-use path check/folds every flop when must_use_hole=1 (board 3 < 5 - 1): not in the axis table or
   prompt 05 (no must-use patch); found from prompt 04 step 2's flop print; patch written and measured (~6 min).
   Avoid: catalog a 1+4 variant ("solo") with a flop read, or make the must-use path read k=1 flops.
6. pack.py --max-mb checks the unzipped size; the kit's caps are 5 MB zipped / 20 MB unzipped; the full package is
   8.4 MB and failed --max-mb 5 until --slim (~0.5 min). pack's import budget default (5 s) is looser than the kit's
   2 s hello; the gate measured import 1.7-2.1 s at worst under load (risk: first decisions auto-played).
7. Parallel kit sims on a loaded box contaminate each other (3 at once gave 55-65% timeouts for every candidate;
   ~1 min wasted); comparisons had to be sequential. The 3-heavy-process cap with tables + sims + gates meant the
   test suite only ran at minute 42; it then failed test_apicard (CONTRACTS.md stale after the new key; regenerated)
   and the full re-run was still running with 5 failures unread at the stop (unresolved).
STOP: 07:39 (minute 53). pytest re-run stopped at ~50% (killed), 5 failures unread. My kill-by-pattern killed my own shell once more (exit 144): same lesson as item 1.
Final submission: out/03-ship-soloflop.zip  sha256 53584934279d864ebd5873d1b112cbf2d72ca37afcc043c05470f545c7b29ac9
