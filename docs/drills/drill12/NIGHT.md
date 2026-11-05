T0: 23:28:49

# NIGHT.md - drill 12 rehearsal, kit "Trailing Stop Hold'em"
repo: eac472a   kit: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/drill12/night/kitdl/trailing-stop-kit   variant: Trailing Stop Hold'em   track: A
ship bot: SHIP='composite' DIALS={}   (--bot hero restores Hero)
Stage 0 known-good number: EMPTY - one person both roles; prompt 04's Stage 0 clause skipped.

Prompt 00 restated: Python bot behind the kit interface; 1 ms a decision (exception/timeout = check or fold), lookups only, heavy work at import; no network, stdlib only (kit caps below override 100 MB); 8-max SNG, 2000 chips, kit's blinds and points, many tables; one adapter, strategy never imports the kit; priority (1) legal bot <15 min, (2) ship bot through adapter, gated, (3) smallest forced patch under the keep rule. Verify by commands; conservative choices, noted; NIGHT.md logs.

## RULE SHEET (minute 2)
- Hole 2; no discards/swaps/exposures/auctions. Board 3/1/1, one board. Standard ranking, no must-use.
- Betting: NL. Raise = "r<x>" raise-BY x bb ON TOP of the call (pays owe+x); clamped to min/max silently; "r1000000" shoves. Min raise = last full raise, >= 1 bb. Short all-in does not reopen for those who acted. "A short blind still sets the full price" => extras.full_bb_call true. No antes, no straddle. Fold when could check stands.
- TWIST (quote): "every player has a trailing stop, and closing a hand below it eliminates you, however many chips you still hold." Peak = highest closing stack, start 2000, never falls; stop = ceil(0.6*peak), start 1200. At close: (1) mark, all at once, below stop out, exactly on survives; (2) liquidation: stopped-out chips split equally among survivors, odd chips clockwise from left of button; (3) new peaks (a dividend can raise a peak). "If your chips behind are below your stop and you fold, you are out." Everyone's stack/peak/stop are public, in every decide.
- ENGINE: our sim has no stop; hooks settle()/extras() can carry it as a file (submission/tonight.py) if Stage 5 needs it; kit sim is the measure otherwise.
- Blinds: 10/20 15/30 25/50 40/80 60/120 100/200 150/300 250/500, 25 hands a level (differs from default at levels 4,5,8). 2000 chips, 8 seats, 200 hand cap.
- Scoring: 14 9 6 4 3 2 1 0 by finish; same-hand eliminations rank by chips at the mark then start stack; at cap survivors rank by STACK (no ICM): extras.cap_places chips; exact ties share.
- Interface: module-level sit_down(table) -> decide(v), closure; v fields per README 5; amounts FLOATS IN BB OF CURRENT LEVEL; v.players clockwise from SB, eliminated not listed, indices rotate each hand; tags random per table, table.tags gives 8 in fixed clockwise order; legal not listed (from owe/min_raise/max_raise); cards = int bit mask, bit=13*suit+rank-2. Answer "f","c","r<x>". Full log string in v.log, tag+verb+amount, "/" per street.
- Setup: import 5 s (hard 15) per seat, sit_down 25 ms (hard 500), decide 1 ms (hard 50). Module globals survive tables in a process, not guaranteed. One module copy per seat.
- Event callbacks: NONE. Hand ends arrive as v.recap INSIDE the next timed decide (dividend, net, out, shown): our hand-end work is on the 1 ms clock. HAND_END defer does not help beyond "same call".
- Size: 5 MiB zipped, 25 MiB unzipped, 2000 files (pack --max-zip-mb 5 --max-mb 25 --slim). CPython 3.10 stdlib only. Overrun is a BaseException at the hard stop; no bare except.
- Tooling: python3 -m engine.sim team.zip bots/tight.py ... --clock cpu; zip checks = engine.loader.check_zip via the sim loading the zip. Zip with bot.py at root.

## AXIS CLASSIFICATION
- Strength: N. Information: N (public stops; no card change). 
- Payoff: Y - what a chip is worth: chips below the stop are not yours to lose; losing the cushion forfeits the rest to the survivors; dividends on others' exits.
- Betting structure: minor - schedule only (blind_levels in rules).
Stage 5 patch section: payoff (point table + twist not in prompt 05's list: a small function in the adapter, kit simulator measures).

## FIT VERDICT
evaluator KEEP; preflop tables KEEP; push/fold KEEP (values ignore stops; Stage 5); postflop KEEP; profiler KEEP (log given); ICM curve KEEP, reads payouts (knows no stops).
Path: no REGENERATE, Stage 3 skipped. 

## ASSUMPTION DIFF
- Raise-to -> raise-by on top of call: adapter. Amounts in bb floats -> adapter rounds to chips. Linear payouts -> Rules.payouts. Levels 4,5,8 -> blind_levels. ICM at cap -> chips ranking (cap_places). 100 MB -> 5/25 MiB. Hand-end callback -> recap inside decide. Per-table init: yes, sit_down, 25 ms. Bust = 0 chips -> stop eliminates with chips: ENGINE CANNOT REPRESENT without a hook file; lines captioned "variant minus stop" in our sim.

## MOST DANGEROUS THING FOR A 1 ms BOT
A timeout or error folds, and past the stop (a posted blind can put you there) a fold is elimination with all your chips: lost milliseconds now cost whole tables. Second: the hand end runs inside the next decide's clock.

## Checkpoints
rule sheet + axis: minute 2

## Verified

## Submissions

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|
| 4 | submission.zip | cf9382d4206e23642179ea1265a8cac5f8edd8354056dd6d9949ed53fde1b1cf | 1.1 MB / import 0.29 s | cheap: cheap bot | |
| 5 | submission.zip | fe0f70cd68e7dba9f406bf7d31aff63ac5f5867e0467b95654d49440d9fb908b | 3.7 MB / import 0.69 s | composite: ship bot | |
FIRST VALID SUBMISSION: minute 3 out/01-cheap.zip sha256 cf9382d4206e23642179ea1265a8cac5f8edd8354056dd6d9949ed53fde1b1cf bot cheap, dials {}; check_zip ok; kit sim 60 tables seed 1 vs tight/deskhand/station/random, cpu clock: 5.65 +/- 0.83 (tight 5.80, deskhand 7.18, station 0.78, random 0.97), tmo 0, err 0.
SHIP BOT GATED AND SUBMITTED: minute 8 out/02-ship.zip sha256 fe0f70cd68e7dba9f406bf7d31aff63ac5f5867e0467b95654d49440d9fb908b composite dials {} no stop patch; GATE PASS -0.020 +/- 0.848 (100 tables, tmo 0.19%, load 15). Kit sim 200 tables seed 1 cpu clock, 2 seats each vs tight deskhand + station random: 7.75 +/- 0.52 (tight 4.16, deskhand 6.89, station 0.51, random 0.88), tmo 158/57341 (0.28%), err 0. Strict sim ("variant minus stop") 300 tables: ship 9.22 +/- 0.61, exc 0, ill 0, p99 342 us. Stage 0 clause skipped: no number under tonight's rules. Night tests: 153 passed.

## Stage 5 patch (decided minute 17)
Patch: StopBot in submission/adapter.py, mode A (stop_patch.txt "A"): past the stop (stack behind < floor), all-in if we can raise, else call, else check; the bot is not asked. Nothing else.
Rejected on screens (400 tables, same table, one seat each vs deskhand x2, tight x2): B rooms as stacks 5.03 vs A 5.74 (and 4x timeouts); C crossing lens 5.24; D crossing call priced as whole stack 5.37 vs A 6.30; E D+raise cut 5.85; AR 5.46, AX 4.91 vs A 5.77; AL 5.81 (level, not smaller).
Keep rule, kit simulator, patched and unpatched zips in the same tables, cpu clock: seed 31, 500 tables, 2 seats each + deskhand tight station random: A 7.25 +/- 0.30, base 5.70 +/- 0.26 (+1.55); seed 32, 300 tables, A x4 base x3 deskhand: 5.53 +/- 0.27 vs 3.49 +/- 0.23 (+2.03); seed 33, 300 tables, A x4 base x3 tight: 5.83 +/- 0.28 vs 3.99 +/- 0.25 (+1.83). 1,100 tables, every run up: KEPT.
Non-strategy fix also in this zip: hero.table_freeze off in bot.py: the full gc.collect every 16 tables made sit_down 20-27 ms against the 25 ms limit; 6% of tables lost on autopilot in the first 4-copy screen (setup 22-24), 0 after.
FINAL-CANDIDATE: minute 17 out/03-stopA.zip sha256 264c04ee6da011ab2a547bae5d5b56c0294718dc57f513be59a983de50f739f4 composite dials {} stop A; GATE PASS +1.230 +/- 0.911 (100 tables, --variant submission/tonight.py:variant, tmo 0.17%). 

## Timing checks after the patch (not kept)
AF (skip the log kit's unused rebuild) and AF+latency: tmo 0.61% / 0.56% vs A 0.73%, p99 unchanged ~920 us, points 5.33 / 5.14 vs A 6.15 (+/- ~0.5, 300 tables, cpu clock): not kept. --limit-us 500 (a box about 2x slower, 300 tables): A 7.11 with 14.3% timeouts, still top; A + recipe timeouts 4.09 with 40.3% timeouts and mean 479 us: on the composite that recipe is SLOWER than the ship bot.

## Checkpoints (minutes since T0)
rule sheet and axis 2; first valid submission 3; ship bot gated and submitted 8; variant patch decided 17; final submission 17; stop 20.
Final: out/03-stopA.zip  sha256 264c04ee6da011ab2a547bae5d5b56c0294718dc57f513be59a983de50f739f4  composite, dials {}, stop mode A. Frozen: hyperion/frozen/T1.zip

## Kit simulator results by submission
01-cheap: 60 tables, cpu, seed 1, 2 seats vs tight x2, deskhand x2, station, random: 5.65 +/- 0.83 (tight 5.80, deskhand 7.18, station 0.78, random 0.97); tmo 0, err 0.
02-ship: 200 tables, cpu, seed 1: 7.75 +/- 0.52 (tight 4.16, deskhand 6.89, station 0.51, random 0.88); tmo 158/57341 (0.28%), err 0. 100 tables, wall, seed 2: 8.12 +/- 0.73 (4.12, 6.57, 0.46, 0.94); tmo 19/29267 (0.06%), err 0.
03-stopA: 300 tables, wall, seed 7, load 17: 8.15 +/- 0.41 (tight 4.03, deskhand 6.59, station 0.57, random 0.88); tmo 1304/91806 (1.42%), err 0, setup 0; deskhand 22 tmo in the same run. Cpu-clock timeouts in the paired runs 0.48-0.86%.

## What slowed us or broke
1. sit_down near its limit (about 2 min; found minute 9). Hero's table_freeze ran a full gc.collect every 16 tables: 10 ms with one copy, 20-27 ms with four, against 25 ms. 22-24 of 400 tables per seat went to autopilot in the first 4-copy screen. 02-ship still has this code (0 setup failures in its 2-copy runs). Avoided by: a setup-time check in tools/latency.py or the gate; entry template lines for kits that collect between tables.
2. No template for this kit's shape (about 1 min): sit_down closure and recap inside decide. module_entry_template and module_gate_seat_template were adapted by hand; the seat had to be rewritten. Avoided by: a closure-shaped template.
3. Patch not in prompt 05 (about 4 min): an elimination threshold fits no axis section, so candidates were reasoned and screened from scratch. Avoided by: a section on "a stack is not all yours to lose" naming past-the-point folds. The first candidates (B, C, D) were my larger ideas; the smallest, A, won.
4. Gate meaningless without the twist (about 1 min): on plain rules the seat's floors fire with no stop in the engine, so tonight.py had to carry the stop. Playbook covers the file; prompt 02 step 7 could say a function patch needs --variant.
5. Timing chase with no gain (about 3 min): AF and latency left p99 at about 920 us. Prompt 04 step 4's rule reverted them. The recipe `timeouts` on the composite is slower than the ship bot (mean 479 us vs 405, 40% timeouts at a 500 us limit); CONTRACTS.md presents it as the cure. Needs a look on the day.
6. My lineup slip (no minutes): seeds 32 and 33 used 5 bots, so the kit repeated the list to A x4, base x3, one opponent, not two seats each as prompt 05 says. All three runs still up; seed 31 is the proper shape.

## Not done or caveats
Stage 0 clause skipped. Load generator in prompt 04 step 4 skipped, box already at load 15. tools/zip_parity.py not run. climb_accept aware check not run: the patch is an adapter function, so the kit sim measures it, with deskhand as the aware opponent. The screens were one seat each at about +/- 0.5, so the rejected candidates are "not better than the smaller patch", not proven worse. One module-level adapter assumes one table at a time per process: true of the kit sim, unstated for the event. Source submission/adapter.py carries inert mode letters that 03-stopA.zip does not (it was built before F).
