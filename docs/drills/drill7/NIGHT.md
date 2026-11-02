T0: 21:25

# NIGHT.md — drill 7 rehearsal (River of Blood kit), 2026-11-01

Copy this file to `NIGHT.md` at minute 0 (`cp docs/packet/NIGHT-template.md NIGHT.md`). The Verifier owns
it. Keep the T0 line exactly in this form: `tools/pack.py` reads it to stamp each submission's minute.

T0: 21:25
repo: not recorded (no git in this rehearsal)   kit: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/drill7/kit   variant (their name): River of Blood Hold'em   track: A
ship bot: SHIP = composite, DIALS = {}   (`--bot hero` restores Hero)
Stage 0 known-good number (re-measured at minute 2 with `--rules rules_tonight.json`, variant minus the red run): ship 300 31.802 ±2.435, tmo 10, exc 0, ill 0, p99 237 us (host load avg ~4-5 of 8 cores)
Hero's, for the fallback: not measured (no time spent; `--bot hero` only if the ship line fails)

## RULE SHEET (Stage 1, prompt 01; filled at minute 3)

- Hole cards dealt per player: 2. No discards, swaps, exposures or auctions.
- Board: 3/1/1 then RUN CARDS: "If the river card is red (a heart or a diamond), another community card is
  dealt, followed by another betting round. This repeats until a black card (a club or a spade) is dealt. The
  black card that ends the run gets its own betting round too." Streets numbered by board length (0,3,4,5,6,7...).
  Expected 0.96 run cards per contested river; kit sim saw a 12-card board. One board. ENGINE CANNOT REPRESENT
  (no `Rules` field for a conditional run): every sim line tonight is "variant minus the red run".
- Hand ranking: standard, "best five-card hand from your two hole cards plus every community card" (best 5 of
  2+N, N up to ~12). No must-use rule. Our evaluator is documented for 5 to 8 cards: N>=7 board (9+ cards) is
  outside it (see MOST DANGEROUS).
- Betting: no-limit. Min bet = bb on every street incl. run streets; min raise = last full raise increment;
  short all-ins do not reopen (TDA cumulative rule). Amounts are RAISE-TO street totals ("Amounts are street
  totals (raise-to)"). Antes: YES, "Every player dealt in posts the ante before the blinds. Antes are dead money"
  from level 4: 10/15/25/40/50. No straddle. Bet to call preflop is the full bb even if bb is short. Fold is
  illegal when check is offered. Raise amount must be an int (300.0 and True illegal); no clamping by engine.
- Blind schedule: 8 levels x 25 hands: 10/20, 15/30, 25/50, 40/80 a10, 60/120 a15, 100/200 a25, 150/300 a40,
  200/400 a50 (differs from our default at levels 4-5: 40/80, 60/120 not 50/100, 75/150). 2,000 chips, 8 seats,
  200-hand cap.
- Scoring: 50/25/15/10/0/0/0/0 by place (top half paid, 100 per table). ICM (Malmuth-Harville) at the cap. Ties
  in one hand: bigger starting stack higher; equal stacks share. No bounty/side payoff.
- Agent interface: `class Player` in `player.py`, no-arg constructor, one fresh module copy + instance per table
  (package `_kitbot<n>`, relative imports). Events: `take_seat(table)` (seat, seats, starting_stack, hand_cap,
  budget_ms, setup_ms, blinds list, payouts, variant), `start_hand(hand)` (hand 1-based, level, sb, bb, ante,
  button, sb_seat, bb_seat, order, stacks BEFORE posting, posts [{seat,kind,paid,all_in}], seat, hole ['As','Kc']),
  `see_cards({street, cards, board})`, `see_action({seat, street, move, amount (street total), paid, all_in,
  auto})` for every move incl. ours, `see_showdown({board, hands:[{seat,hole,rank,best}]})`, `end_hand({hand,
  board, returned, pots, stacks, net, busted})`, `choose({hand, street, budget_ms, options})` -> dict
  `{"move": "fold"|"check"|"call"|"raise", "amount": int street total}`. Options list exactly the legal moves
  (fold / check / call{amount,cost} / raise{min,max}). NO STATE SNAPSHOT: pot, stacks, bets tracked from events.
  Time: 1 ms wall per call for choose AND every event method (interrupted at 1.05 ms); setup (import + Player()
  + take_seat) 1 s per table. Errors -> check if free else fold. Busted seats get no more calls. Memory 256 MB.
- Tooling: `python3 simulate.py BOT ... -n N --seed S` (BOT = player.py, folder, or zip); `python3 selftest.py`.
  Submit one .zip with `player.py` at top level, <= 10 MB zipped (stricter than our 100 MB assumption),
  stdlib only, no threads/processes/file writes/reads outside own folder; extra modules imported relatively
  (`from . import x`), data via `os.path.dirname(__file__)`. Kit imports only stdlib.

## AXIS CLASSIFICATION

- Hand strength ordering moved? N. Standard ranks; more cards per hand only changes the evaluator's input size.
- Information moved? Y. Extra community cards after a red river: the river is not the last street ("The engine
  never says whether a street is the last one"); made-hand value can change after the river; boards of 6-12+.
- Payoff moved? N (point table 50/25/15/10/0... is an ASSUMPTION DIFF, carried by `Rules.payouts`).
- Betting structure moved? Y (minor): antes from level 4 and a different level 4-5 schedule; run streets are
  extra full NL betting rounds.

Stage 5 patch section: Information (run streets), with the antes line from Betting already carried by
`rules_tonight.json` (ante_from_level 3, ante_per_level).

## FIT VERDICT (minute 3; the Verifier holds it for the hour)

| prepared layer | KEEP / REGENERATE / DROP | reason |
|---|---|---|
| evaluator (best hand from 5 to 8 cards, rank remap through `Rules.rank_order`) | KEEP | standard ranks; 2+5 and 2+6 cards inside its range; 9+ cards handled by the adapter (no evaluator change) |
| preflop tables (169-class equity and ranks) | KEEP | 2 hole cards, standard deck; run cards change river equity slightly, not the class order enough to regenerate in the hour |
| push/fold solution | KEEP | per-bb solution; antes are fed through `Rules.ante_per_level` / stack_bb |
| postflop rule layer | KEEP | streets 3/4/5 as normal; run streets mapped to the river by the adapter (Stage 5 information patch if any) |
| opponent profiler | KEEP | seats anonymous per table, full action log via see_action |
| ICM curve (reads `Rules.payouts`) | KEEP | reads 50/25/15/10/0... from rules_tonight.json |

Path (mechanical): no REGENERATE, nothing DROP -> skip Stage 3, Stage 4 as normal. Tonight's path: Stage 2 ->
Stage 4 -> Stage 5 (information).

## ASSUMPTION DIFF

| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole cards, 3/1/1 board | 2 hole, 3/1/1 + red-run cards (street = board length, 6, 7, ...) | the river is not always last; evaluator past 8 cards | adapter maps run streets; `rules_tonight.json` keeps board_sizes (0,3,4,5); ENGINE CANNOT REPRESENT the run |
| standard rankings | standard | nothing | - |
| no-limit, raise-to totals | no-limit, raise-to street totals, exact legality, int amounts | nothing (adapter must send int) | adapter (from_action), `Rules.betting` nolimit |
| 10/20 rising every 25 hands, 2,000 chips, 8 seats, 200-hand cap | same, but level 4 = 40/80 and level 5 = 60/120 | sim schedule at levels 4-5 | blind_levels |
| no antes | antes 10/15/25/40/50 from level 4, dead, posted before blinds | pot size, stack_bb, push depth | ante_from_level 3, ante_per_level [0,0,0,10,15,25,40,50] |
| linear payouts 8..1 | 50/25/15/10/0/0/0/0 | ICM curve, sim scoring | payouts |
| 100 MB submission | 10 MB zipped | package size | pack.py size check; must check zip size <= 10 MB |
| per-table init outside budget | setup = import + Player() + take_seat <= 1 s per table, fresh module per table | import of our package must be well under 1 s cold | measured on the package |
| 1 ms per decision | 1 ms per call for choose AND every event method | event bookkeeping must be cheap | adapter event methods do O(1) work |

ENGINE CANNOT REPRESENT: the red run (conditional extra community cards and betting rounds). Every sim line is
captioned "variant minus the red run". Hand numbers: kit `hand` is 1-based, our `Rules.level_at` is 0-based ->
adapter passes hand_no = hand - 1.

## MOST DANGEROUS THING FOR A 1 ms BOT

The board grows past 5 cards (a 12-card board was seen in the kit's own example run), so hole + board reaches 9
to 14 cards. Our evaluator is built for 5 to 8 cards and builds a lookup table lazily per card count: a 9-card
evaluation inside `choose` could build a table at decision time (a timeout = fold) or crash. Second: the setup
budget is 1 s per table including a cold import of our whole package (fresh module copy every table), and every
event method also has the 1 ms clock. Third: no state snapshot, so a missed or mis-tracked event (pot with
antes as dead money, bets reset per street, run streets) silently corrupts what the bot sees.

## Verified (every command whose output decided something)

| minute | stage | command | the line that mattered |
|---|---|---|---|
| 2 | 0 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules rules_tonight.json` | ship 300 31.802 ±2.435, tmo 10 exc 0 ill 0 p99 237 us (variant minus the red run) |
| 7 | 2 | `python tools/pack.py --entry submission/player.py --out dist/ --extra submission/adapter.py submission/rules_tonight.json --bot cheap --max-mb 10 --note "cheap bot (Stage 2)"` | bot cheap; import ok 0.77 s; 993 KB; sha256 bcb00920...57bd8db |
| 7 | 2 | `HYPERION_CHECK=1 python simulate.py dist/submission.zip bots/random_legal bots/call_station -n 50` (in K) | 3 seats: 0 timeouts, 0 exceptions, 0 illegal; max 474 us; engine errors 0; conformance: only history_prefix (run streets, minute-9 adapter) and to_call_bets x2 (kit rule: full bb to call vs a short all-in bb); actions fold/check/call/raise all > 0 |
| 8 | 2 | `python tools/gate.py dist/submission.zip --kit submission/gate_seat.py --entry player.py --tables 30 --rules rules_tonight.json` | package 9.881 vs cheap (sim) 10.308; paired -0.427 ± 2.630; 0 exc 0 ill 0 tmo; import 0.87 s worst; GATE PASS |
| 8-13 | 2 | `python -m pytest -q -x` | 812 passed, 1 skipped in 278 s |
| 9 | 4 | adapter: run streets now keep the whole log (was: current run street only) | kit sim 30 tables HYPERION_CHECK=1: history_prefix gone; only to_call_bets x1-x2 per seat (kit rule) remains |
| 10 | 4 | `HYPERION_CHECK=1 python simulate.py ../hyperion/submission bots/random_legal bots/call_station -n 30` (ship bot from repo) | 0 exceptions, 0 illegal; timeouts 12-15 per seat of which 8-11 are end_hand event callbacks (1.05-5.4 ms); load avg 6.8 of 8 |
| 11 | 4 | timed wrapper (logs/timed) kit sim 20 tables, budget 1000 ms | end_hand p50 157 p99 658 us, over 1 ms 8/5629 (0.14%); choose p50 71 p99 233 us, over 1 ms 2/10434 (0.02%); load 6.5 |
| 12 | 4 | sample decisions through the adapter | AKo preflop -> raise 50; flop Ah7d2c checked to -> raise 55 into 110; run street 7 (Ah7d2c9hKdQhKs, AK full house) -> raise 88 in 142 us; river_view picked Ah 9h Kd Qh Ks |
| 12 | 4 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules rules_tonight.json` | ship 300 31.067 ±2.486 (Stage 0 31.802 ±2.435: inside CI), tmo 44 of 53486 hands (0.08%), exc 0, ill 0, p99 258 us (variant minus the red run) |
| 12 | 4 | same with `--tables 40 --rotate` | ship 32.890 ±2.672 first; tag 11.753, pushfold 11.984 (ship not last) |
| 12 | 4 | `python tools/latency.py --n 2000 --rules rules_tonight.json --adapter submission.adapter:TonightAdapter --native submission.latency_native:build` | bot.act p99 279 us, over 1 ms 0.05%; adapter.decide p99 308 us, over 1 ms 0.10%; exit 0 (generator load step skipped: host already loaded by other jobs and the 3-process cap) |
| 14 | 4 | import probe (fresh `python -I`) | import 0.003 s, warm(7) 0.142 s, warm(8) 0.621 s, make_bot 0.134 s: Hero.new_table's warm(8) is most of the 1 s setup budget |
| 15 | 4 | timed kit sim 30 tables with the warm cap (player.py caps Hero's warm at 7 cards) | unsuited tables built [5, 6, 7]: no 8-card evaluation in 30 tables (longest board 15); end_hand over 1 ms 0.36%, choose 0.14% (gate running alongside) |
| 15 | 4 | `python tools/gate.py dist/submission.zip --kit submission/gate_seat.py --entry player.py --tables 100 --rules rules_tonight.json` (57208f91) | package 33.228 vs composite (sim) 30.619, +2.609 ± 4.724; tmo 380 = 2.12%, p50 282 us; GATE FAIL (gate-seat artifact: hand end deferred into the timed call) |
| 18 | 4 | `HYPERION_CHECK=1 python simulate.py dist/submission.zip ... -n 40 --seed 9` (c6c0c948) | 0 exc 0 ill; conformance to_call_bets x5, board_len x1, in_hand_self x1 (missed events under load avg 7.8: start_hand took 2.4 ms) |
| 19 | 4 | same gate on d9f99623 (seat delivers the held hand end untimed) | package 35.086 vs 33.715, +1.371 ± 4.783; 0 exc 0 ill; tmo 0.11%; p50 95 p99 354 us; import 0.29 s worst; GATE PASS |
| 20 | 4 | `HYPERION_CHECK=1 python simulate.py dist/submission.zip ... -n 40 --seed 9` (d9f99623) | 0 exc 0 ill; conformance to_call_bets x11, raise_total x1 (stale bets after an interrupted see_cards) |
| 21 | 4 | `HYPERION_CHECK=1 python simulate.py dist/submission.zip ... -n 40 --seed 13` (574c98ca) | 0 exc 0 ill; conformance to_call_bets x9, pot_nonneg x1; load avg 8.06 |
| 21 | 4 | same gate on 574c98ca | package 31.113 vs 32.922, -1.809 ± 4.724; 0 exc 0 ill; tmo 0.03%; p50 95 p99 296 us; import 0.26 s worst; GATE PASS |
| 21 | 5 | package probe: Player().take_seat in a fresh `python -I` | SHIP composite DIALS {}; HybridCore and HeroCore rules.payouts (50, 25, 15, 10, 0, 0, 0, 0); levels 4-5 (40,80),(60,120); ante 10 from kit hand 76 |
| 22 | final | `python simulate.py dist/submission.zip bots/random_legal bots/call_station bots/template -n 40 --seed 21` | ours 28.36 and 24.14 avg, first and second; 0 exc 0 ill; the kit's own template bot also timed out (see_action 2.16 ms): host load |

## Stage notes, decisions, guesses and UNSPECIFIED (kept as they happened)

- Minute 0-3, Stage 1: rule sheet, axis, fit verdict above. `rules_tonight.json` (repo root, copy in submission/):
  kit schedule, antes `ante_from_level` 3 + `ante_per_level` [0,0,0,10,15,25,40,50], payouts 50/25/15/10/0/0/0/0,
  `extras.kit_variant` (deliberately NOT `extras.variant`: river_of_blood is not in the catalog and the tools look
  hooks up by that key). Our Rules count hands from 0, the kit from 1: the adapter passes hand_no = hand - 1.
- Minute 3: wrote a scratch file outside R by mistake (the rule-sheet draft); deleted at once. Temp files live in
  R/logs from then on.
- Stage 2 adapter design (submission/adapter.py, submission/player.py): the kit has no state snapshot, so
  player.py tracks pot (every chip paid incl. antes and this street), stacks behind, this street's bets, in-hand
  seats and the full action log from the events, and hands the adapter a snapshot at each `choose`.
  history_source "log" (see_action shows every move). Hand end passes every seat's net (deltas), the showdown
  ({} when none, the kit sends see_showdown only when 2+ show) and board[:5].
- Run streets (ENGINE CANNOT REPRESENT): street > 5 is shown to the bot as the river (street 3) with a 5-card
  sub-board on which our best hand equals our best hand on the whole board (searched over the last 9 board cards,
  ties broken by the strongest board, <= 126 sub-boards, ~110 us). pot = chips before this street, bets = this
  street. Guess: the bot plays every run street as a final river; a red river is treated as last. Not
  measurable in our sim (it has no run), so no Stage 5 patch for it (hard rule 6).
- Minute 9: the first adapter showed the bot only the current run street's actions (a clean river round);
  conformance flagged history_prefix (a kit log only grows) and prompt 04 requires zero, so the whole hand's log
  is passed instead (run actions follow the river's). Decision, not measured either way.
- Known conformance finding kept: `to_call_bets` (about 1 in 300 observations): the kit's rule "Bet to call
  preflop is the full big blind, even when the big blind is all-in for less" makes the call cost exceed
  max(bets) - my bet. The adapter passes the kit's true cost; changing bets would break chip conservation.
- Stage 3 SKIPPED (minute 13): fit verdict all KEEP. The information axis moved, but `tools/gen_tables.py` reads
  the same Rules, which cannot represent the run: regenerating would rebuild the default tables bit for bit.
- Minute 14: Hero.new_table calls warm(8) (0.62 s, the 8-card evaluator table) inside the kit's 1 s setup budget
  (import + Player() + take_seat). The bot never sees more than 7 cards tonight (river_view, board[:5] at hand
  end), so player.py caps Hero's warm-up at 7 cards (monkeypatch in the entry, no strategy file changed):
  fresh-process import 0.81 s -> 0.24-0.26 s. Verified: 30 kit tables, longest board 15, no 8-card table built.
  UNSPECIFIED: whether the official runner starts one process per table (cold import every table) or per bot; we
  assume the worst.
- Minute 15: GATE FAIL on the minute-14 zip (57208f91...): package timeouts 2.12%, p50 282 us. Cause: the gate's
  hand end carries only our delta, so the adapter deferred the bot's hand end into the next timed decision; the
  kit never does that (its end_hand carries every seat's net). Not uploaded. Fix is gate-side only
  (submission/gate_seat.py delivers the held hand end in `native`, untimed). A minute-17 try with
  defer_hand_end off gave the bot wrong stacks (package 26.6 vs 32.0 at 80 tables) and was killed; not a result.
- Minute 18: choose now check/folds when an event was missed (request hand != tracked hand, no hole cards, or
  request street != board length): seen under host load as start_hand / see_cards interrupted at 1.05 ms
  (in_hand_self, board_len, raise_total findings once each in 40 tables).
- Host load: load average 6.5-7.8 on 8 cores most of the hour (other jobs + ours). Trivial callbacks
  (see_action p50 1 us, start_hand p50 4 us) timed out at 1.05-2.4 ms, so part of every timeout count tonight
  is the host. end_hand (the bot's hand end: profiler, rival 3 replay, Hero's ICM curve twice, once for the
  composite's Hero and once for the base's fallback Hero) is p50 ~150 us, p99 ~660 us: its tail is ours.
- UNSPECIFIED: whether event-callback timeouts are scored or penalised beyond being counted (README: "counted as
  a timeout; the hand goes on"); whether the official runner reuses a process across tables; tie-break rules
  beyond the README; memory (256 MB) not enforced locally (our package is ~4 MB on disk).
- Stage 5 (prompt 05), decided at minute 21, override `{}`: no patch. Information axis: none of the prompt's
  information patches fits a red run (no extra hole cards, discards, swaps, exposed cards or second board), and
  the sim cannot play the run, so any run-street patch would ship unverified (hard rule 6). Betting (antes, the
  core plays them): prompt says no dial; antes are dead money in the pot the core reads and in stack_bb via
  `ante_per_level`. Payout table: `Rules.payouts` is the whole patch, confirmed in both HybridCore and HeroCore
  at new_table (Verified, minute 21). Nothing to measure in model mode with an empty dict; no run made.
- Submit and freeze (minute 21-25): final = 574c98ca... (pack minute 20, GATE PASS minute 21), copied to
  frozen/T1.zip. Upload due at minute 25 (the minute-18 zip went up at minute 20; one upload per five minutes).
  After that nothing was changed. Re-read: zip 993 KB (limit 10 MB zipped), player.py at the top level, class
  Player, stdlib only, no threads/processes/file writes, no network.
- Stage 6 (windows) is after the hour: not part of this rehearsal.
- Work stopped at 21:48:44 (minute 23 of 60): everything after this is the frozen T1.zip, nothing changed.

## Submissions

`python tools/pack.py --entry submission/<entry>.py --out dist/ --note "<what changed>"` (`--bot cheap` at Stage 2)
appends a row whose "what changed" starts with the bot it recorded and its dials;
the Verifier fills "verified by" with the portal's confirmation (time, or the hash the portal shows).

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|
| 7 | submission.zip | bcb009206aade0537a678defef92d236b8d098ed54856cce55e75c1f557bd8db | 993 KB / import 0.77 s | cheap: cheap bot (Stage 2) || GATE PASS minute 8 (30 tables, -0.427 ± 2.630, 0 exc/ill/tmo); uploaded minute 8 |
| 14 | submission.zip | 57208f916a98000cb3ef51bfb2a4cee34557e9104c2e74d6b4f401f389c28633 | 993 KB / import 0.81 s | composite: ship bot (Stage 4): composite behind the River of Blood adapter, full log, run streets shown as the river || GATE FAIL minute 15 (timeouts 2.12%: the gate seat deferred the hand end into the timed call); NOT uploaded |
| 17 | submission.zip | c6c0c94848c97dc64f8e70e3ed73a9b6b49af3ce318f49671067dffcfff09660 | 993 KB / import 0.26 s | composite: ship bot: composite; player.py caps Hero's warm-up at 7 cards (setup 1 s budget); full log; run streets shown as the river || gate run with a broken seat (defer off), killed at 80/100; never gated; NOT uploaded |
| 18 | submission.zip | d9f996235b52a170a214262b23d7d51aaef00f0df1867dc27ff24fcfbef78d5a | 993 KB / import 0.24 s | composite: ship bot: composite; warm cap 7 cards; choose check/folds if an event was missed (hand/street/hole mismatch); full log; run streets as the river || GATE PASS minute 19 (100 tables, +1.371 ± 4.783, 0 exc 0 ill, tmo 0.11%, import 0.29 s); uploaded minute 20 |
| 20 | submission.zip | 574c98cab14dfb4db16c2b25456d0d569fbbeb31e79b15cc8b1ebdba8cf1b381 | 993 KB / import 0.25 s | composite: ship bot: composite; as minute 18 plus see_cards resets bets before the board (a missed event leaves a stale board that choose detects) || GATE PASS minute 21 (100 tables, -1.809 ± 4.724, 0 exc 0 ill, tmo 0.03%, import 0.26 s); upload due minute 25 (one per five minutes after minute 20); FINAL |

Frozen known-good: 574c98cab14dfb4db16c2b25456d0d569fbbeb31e79b15cc8b1ebdba8cf1b381  (frozen/T1.zip, minute 21; also frozen/stage2_cheap.zip bcb00920..., frozen/stage4_d9f99623.zip)

Minutes in this table are pack.py's, counted from `T0: 21:25` (21:25:00); the true T0 was 21:25:46, so a row can read up to one minute later than the elapsed time.

## Windows

One change per window, verified before upload, upload by minute 15 or nothing. One upload per five minutes.

| window | standings in at minute | our rank / mean / spread | signal | recipe (and the dials it set) | model sim before -> after | uploaded (sha256 or nothing) |
|---|---|---|---|---|---|---|
| T2 | | | | | | |
| T3 | | | | | | |
| T4 | | | | | | |
| T5 | | | | | | |
| T6 | | | | | | |

## sha256

Linux: `sha256sum dist/submission.zip`   macOS: `shasum -a 256 dist/submission.zip`   (`tools/pack.py` prints the same)
