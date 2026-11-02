# NIGHT

T0: 16:29:38

repo: hyperion @ 15df280 (R)   kit: K = night/kitdl/ghost-holdem-kit   variant (their name): Ghost Hold'em   track: A
ship bot: SHIP = 'composite', DIALS = {}   (`--bot hero` restores Hero)
Stage 0 known-good number: not re-measured (rehearsal; machine load ~10)

## Prompt 00 restatement (minute 0)
Python bot implementing the kit's `Agent` (bot.py, class Agent; act(s) -> int chips put in now); 1 ms per act
(error/timeout = check-else-fold), new_table 50 ms, hand_over 1 ms, import+Agent() 2 s; no network, Python 3.10
stdlib only, zip <=5 MB zipped / 25 MB unzipped (kit's cap, tighter than 100 MB); 8-max SNG, 2000 chips, 10/20
rising every 25 hands, 200-hand cap, points 16/11/8/6/4/2/1/0 by place with chip-count placing at the cap
(kit says chip count, not ICM split); twist = the Ghost. Priorities: (1) never-crashing legal bot submitted
by minute 15, (2) ship bot through the adapter, gated, (3) smallest variant change, only if not worse.
Strategy never imports the kit; one adapter. Verify with commands.

## RULE SHEET (Stage 1, prompt 01) — minute 1
Rules text: K/README.md sections 1-6 (pasted by path; quoted below where non-standard).
- Hole cards: 2 per player, no discards/swaps/exposures/auctions. Plus "one more two-card hand face down: the
  Ghost" dealt from the same deck after hole cards; never bets.
- Board: standard 3/1/1, one board. Burn cards as usual.
- Hand ranking: standard, best five of seven, suits never rank.
- Showdown twist (ENGINE CANNOT REPRESENT in our sim): "If the Ghost's hand is strictly better, nobody wins that
  pot. The pot haunts." Ties go to players. Each side pot checked separately vs best eligible hand. Haunted chips
  go into the NEXT hand's main pot as dead money (`s.haunt`, already in `s.pot`), won by whoever wins the main pot,
  fold-wins included; Haunt carries/grows; discarded at table end. Pots won without showdown never haunt. Ghost
  never ends a table (ignored if haunting would leave nobody with chips). Ghost cards revealed in hand_over on
  showdown (`r.ghost`).
- Betting: no-limit; min bet/raise >= BB and >= last full raise; short all-in does not reopen. Action = int chips
  put in NOW (increment, not raise-to): n<owe fold (check if owe 0); owe<=n<min_raise call; min_raise<=n<stack
  raise of exactly n; n>=stack all-in; min_raise==0 means cannot raise. Float floored; bool/None/str = error.
  No antes, no straddle. Preflop call is full BB even if BB all-in short.
- Blinds: 10/20 rising every 25 hands (schedule in K/PAYOUTS.md, engine/blinds.py); 2000 chips; 8 seats;
  200-hand cap. Heads-up button posts SB. No dead button.
- Scoring: 16/11/8/6/4/2/1/0 by place. Bust same hand: bigger starting stack places better. At hand 200:
  placed by CHIP COUNT (not ICM split; README §4), Haunt discarded. No bounty.
- Interface: bot.py, class Agent; __init__() once per session (import+init 2 s); new_table(t) optional 50 ms;
  act(s) -> int, 1 ms; hand_over(r) optional 1 ms (overrun -> next act skipped). ONE instance per session plays
  hundreds of tables; state on self persists across tables; t.ids give opponent ids stable across session.
  State s: hand_no, street(0-3), hole(int,int), board, stack (behind), owe, min_raise (0 = cannot raise), pot
  (ALL chips incl. this street's bets and haunt), haunt, sb, bb, button (relative), stacks[8], bets[8] (this
  street), status str8 (A/X/F/-), log (full action log, relative seats). Seat 0 = me, seat 1 acts after me.
  Cards int 4*rank+suit, rank 0=deuce..12=ace, suit c d h s = 0..3 (same as ours).
  No legal-action list: legality via owe/min_raise/stack.
- Setup budget: import + Agent() 2 s once per session; new_table 50 ms per table; one object for the whole session.
- Callbacks: new_table / hand_over timed (50 ms / 1 ms); overrun/raise in new_table -> sit out that table;
  hand_over overrun -> next act gets default action. A call still running after 1 s -> process killed.
- Submission: one zip, bot.py at root; <=5 MB zipped, <=25 MB unzipped; only .py and data files.
  `python3 -m engine.check team.zip` (layout, import, timing, 20 tables). pack.py needs --max-mb 5.
- Tooling: `python3 -m engine.sim <bot> bots/ghostwise bots/tight.py bots/station.py -t N [-j] [--limit-us]`.
  Kit imports stdlib only. History: full log -> history_source = "log".

## AXIS CLASSIFICATION
- Strength ordering moved? N (standard ranks; the Ghost removes 2 unseen cards, negligible).
- Information moved? N for decisions (Ghost hidden until showdown).
- Payoff moved? Y: a showdown pot is paid only if the best hand beats a random 2-card Ghost; else it is dead
  money for the next hand's main pot (won also by fold). Showdown value of marginal hands drops; fold equity and
  stealing gain value (Haunt is dead money to steal).
- Betting structure moved? N.
Stage 5 patch section: payoff (nearest: "ghost/haunt" is new, not in catalog).

## FIT VERDICT
| layer | verdict | reason |
|---|---|---|
| evaluator | KEEP | standard ranks |
| preflop tables | KEEP | 169-class order stands; the Ghost lowers absolute showdown equity of weak hands, not the order much |
| push/fold | KEEP | all-in pots can haunt (bust by Ghost), shifts calls tighter; Stage 5 dial at most |
| postflop rule layer | KEEP | value thresholds may want +1 tier (weak made hands lose to Ghost) — Stage 5 |
| profiler | KEEP | full log given |
| ICM curve | KEEP | reads Rules.payouts = 16/11/8/6/4/2/1/0 |
Path: no REGENERATE -> skip Stage 3, Stage 4 as normal.

## ASSUMPTION DIFF
| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole, 3/1/1 | same | nothing | - |
| standard rankings | same | nothing | - |
| no-limit, raise-to totals | no-limit, INCREMENT (chips put in now) | from_action | adapter: return amount - bets[0] |
| 10/20 x25, 2000, 8, 200 | same (schedule check vs PAYOUTS.md) | nothing | blind_levels |
| no antes | same | nothing | - |
| linear payouts 8..1 | 16/11/8/6/4/2/1/0 | ICM curve | Rules.payouts |
| ICM split at cap | chip-count placing at cap | end-of-table ICM (minor) | none (note) |
| pot excludes street bets | kit pot INCLUDES street bets and Haunt | obs.pot | adapter: pot - sum(bets) |
ENGINE CANNOT REPRESENT: the Ghost/haunt. Every sim line is "variant minus Ghost"; the kit simulator is the only
place the Ghost plays.

## MOST DANGEROUS THING FOR A 1 ms BOT
The int action is chips-put-in-now, and a wrong translation is silent: returning a raise-to total over-raises,
returning 0 when meaning call folds, and min_raise == 0 (cannot raise) must turn a raise into a call. Second: one
Agent plays a whole session, so per-table state must reset in new_table, and anything slow in hand_over (1 ms)
costs the next decision. Strategically: big multiway showdown pots with marginal hands can vanish to the Ghost,
and an all-in that haunts busts us.

Note: kit blind schedule differs from our default: 10/20, 15/30, 25/50, 40/80, 60/120, 100/200, 150/300, 250/500
(engine/blinds.py) -> Rules.blind_levels.

## Submissions
| minute | file | sha256 | what | verified by |
|---|---|---|---|---|
| 1 (16:31:02) | out/insurance.zip | ba481485a3e8cc5610ebe7a81d2cc169af0bb17b7e3d9af6b321de2ad7b160ff | own minimal bot: QQ+/AK all-in preflop, else check/fold | engine.check PASS: 20 tables 6.12 pts, p99 10us, 0 tmout, 0 err |
| 3 | submission.zip | b0f92f554509e3fb262e71fe923e8af82fa77bb157a147c999f4eef578505697 | 849 KB / import 0.39 s | cheap: cheap bot | |
| 4 | submission.zip | b7a7334dbee2dfeeb32ce6833559801447acfb2e82b4474df32d0248942f0cd5 | 849 KB / import 0.37 s | cheap: cheap bot (import fix) | |
| 4 | submission.zip | 3b2f0aee0fa9d93ff97035791bda56bc5426fa1bade516707b8ccf598d139843 | 849 KB / import 0.20 s | cheap: cheap bot (hand_over deferred) | |
| 6 (16:35:40) | out/cheap.zip | 3b2f0aee0fa9d93ff97035791bda56bc5426fa1bade516707b8ccf598d139843 | Stage 2: Hero.cheap() through submission/adapter.py, hand_over deferred to next act | engine.check PASS (20 t: 6.75 pts, p99 200us, 3 tmout, 0 err, 0 cbfail); gate PASS 30 t (-0.73 ± 1.21, 0 exc, 0 ill) |
| 6 | submission.zip | 564b2242459314366756efa947e12a21652ae59953c40d4a1da8740599ca0715 | 849 KB / import 0.30 s | composite: ship bot (composite) build 1 | |
| 9 | submission.zip | 5fe6ebf35f7a91331d14344aee7d7f11bae38045a94a8100da13b342a32d7552 | 849 KB / import 0.34 s | composite: ship bot build 2 (defer_hand_end) | |
| 9 | submission.zip | c78ac98b5aa950dafb5a7fb6a1aac96c7d158aeb5feaae4ca8992648105126db | 849 KB / import 0.44 s | composite {"late_us": 0}: ship bot build 3 (defer + latency recipe) | |

(The pack.py rows above at minutes 3-4 are intermediate builds, NOT submitted: the first failed engine.check on
imports `kit`/`submission`, the second on a hand_over over 1 ms.)

## Verified
| minute | stage | command | line that mattered |
|---|---|---|---|
| 1 | 2 | engine.check out/insurance.zip | PASS 6.12 pts, 0 tmout |
| 3 | 2 | engine.check dist/submission.zip (cheap v1) | imports FAIL: kit, submission (rival3.py `from kit import` in a try; bot.py `from submission.adapter`) -> kit.py stub + `from adapter import` |
| 3 | 2 | engine.check (cheap v2) | cb fail 2: hand_over 1.47 ms > 1 ms -> hand_over stores r, next act/new_table flushes |
| 4 | 2 | engine.check (cheap v3) | PASS 6.75 pts/table, p99 200 us, tmout 3, err 0, cbfail 0 |
| 5 | 2 | HYPERION_CHECK=1 engine.sim cheap.zip ghostwise tight station -t 40 --seed 5 | conformance 3473 obs, 1 violation (to_call_bets: kit owe 60 vs bets 90-60; kit quirk); fold 2284 check 678 call 73 raise 438; cheap 4.85/7.63 vs ghostwise 8.65/8.35, tight 8.80/7.23, station 1.31/1.19; tmout 24+38 of ~8000 (load ~11 + pytest) |
| 6 | 2 | gate.py dist/submission.zip --entry bot.py --kit submission/gate_seat.py --tables 30 --rules submission/rules_tonight.json | GATE PASS -0.726 ± 1.206, 0 exc, 0 ill, tmo 0.23% |
| 4 | stage 3 | skipped: FIT VERDICT has no REGENERATE (prompt 03 not run) | - |
| 7 | 4 | HYPERION_CHECK=1 engine.sim ship(build1) ghostwise tight station -t 40 --seed 5 | conformance 6392 obs, 6 violations all to_call_bets (kit rule: preflop owe is the full BB when the BB is all-in short) ; p50 320 p99 1920-2900 us, tmout 2% -> too slow |
| 8 | 4 | cProfile of kit sim | 64% of act was the deferred hand_end: Hero's ICM curve (icm_me, non-linear payouts 16/11/8.. => 2^7 pass) x2 Heros |
| 9 | 4 | build2: bot.defer_hand_end(True) (curve+dials wait for the deciding Hero), --clock cpu | p50 220 p99 700, tmout 0.45% |
| 10 | 4 | build3: + recipe latency {'late_us': 0}; engine.check | PASS 9.35 pts/table (cheap 6.75 same seeds), p99 570us, 21 tmout/3080 (0.7%, load 11), 0 err, 0 cbfail |
| 11 | 4 | hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json (variant minus Ghost) | ship 11.134 ± 0.633, exc 0 ill 0, p50 51 p99 381us, tmo 349/55199 hands (0.63%, load > cores); next rival1 8.88 |
| 12 | 4 | gate.py dist/submission.zip --entry bot.py --kit submission/gate_seat.py --tables 100 --rules submission/rules_tonight.json | GATE PASS -0.279 ± 1.015, 0 exc 0 ill, tmo 0.61% (load clause WARN) |
| 10 | - | pytest -q -x (pinned repo, unmodified) | 1 failed tests/test_hand_end_interrupt.py::test_defer_hand_end_plays_as_the_eager_hand_end[idle]; re-run alone: 5 passed (flaky under load) |

## Submissions (cont.)
| minute | file | sha256 | what | verified by |
|---|---|---|---|---|
| 12 (16:41:45) | out/ship.zip | c78ac98b5aa950dafb5a7fb6a1aac96c7d158aeb5feaae4ca8992648105126db | Stage 4: composite, dials {'late_us': 0} (recipe latency), bot.defer_hand_end(True), hand_over stores / next act flushes | engine.check PASS 9.35 pts 0 cbfail; gate PASS 100 t; strict sim 11.13 ± 0.63 |
Frozen known-good: c78ac98b5aa950dafb5a7fb6a1aac96c7d158aeb5feaae4ca8992648105126db (R/frozen/T1.zip)
