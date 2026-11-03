T0: 22:30:34

# NIGHT log

repo: 512b31f (pinned copy)   kit: kitdl/chain-holdem-kit   variant (their name): Chain Hold'em   track: A
ship bot: composite, DIALS {} (to confirm with `python -m hyperion.ship`)

## Prompt 00 restatement (min 1)
Python `bot.py` with class `Agent` (`__init__`, optional `begin_table(info)`, `decide(s)->str`, optional `hand_over(r)`),
one instance per session of many tables; 1 ms per decide and per hand_over (late = check/fold, late hand_over forces the
next decision), 20 ms begin_table, 3 s import+Agent(); stdlib only, no threads/processes, no network, zip <= 10 MB zipped /
50 MB unzipped / 500 files with bot.py at root, kit `engine` not importable in the sandbox. 8-max SNG, 2,000 chips, blinds
10/20 rising every 25 hands to 250/500, cap 200 hands, points 50/32/21/14/9/5/2/0, cap ranked by CHIPS not ICM. Twist:
Chain Hold'em (1 private + 2 link cards shared with neighbours; best 5 of 8). Priorities: legal never-crash bot by min 15,
then prepared ship bot through one adapter, gated; then smallest variant patch only if measured not worse.

## RULE SHEET (Stage 1, prompt 01)
- Hole cards: 3 per player = 1 private + left link + right link. "Between every two neighbours in the ring the dealer
  places one link card ... Both neighbours see it and both hold it." 16 hole cards at a full table (n private + n links).
  No discards, swaps, exposures, auctions. Heads-up: both links shared with the one opponent (only their private hidden).
  Folded players' links still play for neighbours at showdown.
- Board: 3/1/1, one board.
- Hand ranking: standard; best five of eight (private + 2 links + 5 board); "You may use any five; you do not have to use
  any hole card." No must-use. Ties common ("two neighbours who both play their shared card often hold the same five").
- Betting: no-limit, but sizes from a fixed menu of tokens: F, C, R33/R50/R75/R100/R150/R250 (raise BY pct of pot after
  call, floored at min_raise_by, capped at stack), A. Min raise = last full raise increment (>= bb); short all-in does not
  reopen. Raise expressed as increment-by-pct tokens, not totals. No antes. No straddles. Invalid token = error -> check/fold.
- Blind schedule: 10/20, 15/30, 25/50, 40/80, 60/120, 100/200, 150/300, 250/500, 25 hands each; 2,000 chips; 8 seats; cap 200.
- Scoring: 50/32/21/14/9/5/2/0. Same-hand busts ordered by start-of-hand stacks. "If hand 200 ends with several players
  left, they are ranked by chips at that moment ... ICM does not apply at the cap." Ties share. No bounty/side payoff.
- Agent interface: class Agent; decide(s) -> str token. State fields: hand, street (0-3), card, left, right, left_nb,
  right_nb, board, pot (INCLUDES this street's bets), to_call (capped at stack), min_raise_by (increment), can_raise,
  stacks/bets/in_pot (8-tuples by offset, 0 = me, clockwise), status (8 chars A/L/F/O), button, sb, bb, level,
  hands_left, log (full action log string, offsets), cost(token). Legal actions not listed: derive (every token always
  accepted; F with to_call 0 = check). Cards int rank*4+suit, rank 0=deuce..12=ace, suits c d h s = 0..3 (same as ours).
  Seats are offsets from me (I am always 0). One Agent instance per session (many tables); begin_table resets.
  hand_over(r): hand, board, log, shown, won, stacks, place, points, table_over.
- Setup budget: import + Agent() 3,000 ms (once per session; over = sit out the whole session); begin_table 20 ms (over =
  sit out that table); one object per session.
- Callbacks: decide 1 ms (late = check/fold, answer discarded); hand_over 1 ms (late/raise -> NEXT decision forced
  check/fold); runaway interrupted at 25 ms (500 ms begin_table, 30 s setup). gc disabled during table.
- Submission cap: 10 MB zipped, 50 MB unzipped, 500 files; bot.py at zip root. pack.py --max-mb 10.
- Tooling: `python3 -m engine.sim mybot.zip --fill bots/chain.py -t 50` from kit top folder = the upload server's checks.
  Python 3.10, stdlib only.

## AXIS CLASSIFICATION
- Strength ordering moved? N (standard ranks; best 5 of 8 is the three-card evaluator path).
- Information moved? Y: 3 hole cards, two of them shared with the neighbours (correlated ranges, frequent splits,
  you know one card of each neighbour; heads-up you know 2 of the opponent's 3).
- Payoff moved? N (point table differs: ASSUMPTION DIFF; cap by chips not ICM).
- Betting structure moved? Partly: fixed pot-fraction raise menu (adapter maps raise-to totals to the nearest token);
  blind schedule differs (rules_tonight.json). No antes/limits.
Stage 5 patch section: Information (nearest catalog entry: three_card_keep).

## FIT VERDICT
| prepared layer | verdict | reason |
|---|---|---|
| evaluator | KEEP | standard ranks, 5-8 cards already supported |
| preflop tables | REGENERATE (three_card_keep scheme) | 3 hole cards: 169-class tables wrong; catalog's three_card_keep tables are the nearest (independent 3rd card; links sharing not modelled) |
| push/fold solution | REGENERATE (with tables) | built on 2-card equities |
| postflop rule layer | KEEP (Hero's three-card path) | best-5-of-8 tiers; made hands more frequent |
| opponent profiler | KEEP | kit gives a full log |
| ICM curve | KEEP, paste payouts | reads Rules.payouts; cap ranked by chips (approximation: ICM near cap) |
Path: REGENERATE -> Stage 3 (check first whether committed three_card_keep tables exist: then 0 s).

## ASSUMPTION DIFF
| Our default | Tonight | Invalidates | Carried by |
|---|---|---|---|
| 2 hole cards, 3/1/1 | 3 hole cards (1 private, 2 shared links), 3/1/1 | preflop tables, push/fold | hole_cards=3, extras.variant three_card_keep |
| standard rankings | standard, best 5 of 8, no must-use | nothing | - |
| no-limit, raise-to totals | NL via token menu: raise BY pct of pot-after-call | adapter from_action | adapter maps total -> nearest token (cost()) |
| 10/20..200/400 (50/100, 75/150 at L4/L5) | 10/20,15/30,25/50,40/80,60/120,100/200,150/300,250/500 | late push depths | blind_levels |
| no antes | none | - | - |
| linear 8..1, ICM at cap | 50/32/21/14/9/5/2/0, chips rank at cap | ICM curve | payouts |
ENGINE CANNOT REPRESENT: link sharing (our sim deals independent 3-card hands; sim lines are "variant minus shared links").
Raise menu: our sim plays continuous raises; captioned "minus token menu".

## MOST DANGEROUS THING FOR A 1 ms BOT
The raise translation: our strategy returns raise-TO totals; the kit only accepts menu tokens raising BY a pot fraction
after the call, and any wrong string is an error -> check/fold. The adapter must map every raise through s.cost() to a
valid token, never emit anything else, and wrap everything in try/except returning "C"/"F". Second: 8-card evaluation per
decision on the three-card path must stay well under 1 ms on a busy box; and the one Agent per session must reset per table.

## Submissions

| minute | file | sha256 | size / import | what changed | verified by |
|---|---|---|---|---|---|
| 5 | out/01-cheap.zip (SUBMITTED min 5, 22:35:54) | d29ca87fff8e535611f25206928263d4daf07671d8a7b82faf990d17d8ebb37f | 1.7 MB, 141 files / import 0.23 s | cheap: Hero.cheap() behind TonightAdapter | kit sim `python3 -m engine.sim out/01-cheap.zip --fill bots/chain.py -t 50` (zip checks passed): 18.58 pts/table [14.02, 23.14] vs chain 16.35; 5461 decisions, 1 late, 0 errors, 1 forced, p99 250 us, setup 262 ms |
| 10 | out/02-ship.zip (SUBMITTED min 10, 22:41:03) | d179b697c1b1ad8a6af824a0eabfa717ee39c9cb4286505b035bbf753c0216c5 | 1.0 MB, 85 files (--slim) / import 0.28 s | composite dials {} behind TonightAdapter | GATE PASS -0.838 ± 2.371 (100 tables); kit sim vs chain x7 (100 t): 24.46 [21.29,27.63] vs chain 15.51, late 21/16625, err 0, forced 37; kit sim mixed (chain,tight,station,random, 2 seats, 100 t): 28.41 [26.18,30.64] vs chain 18.89 tight 15.67 random 5.09 station 1.97, late 12/33567, err 0, forced 14, begin_table max 11.8 ms |

## Verified
| minute | stage | command | the line that mattered |
|---|---|---|---|
| 5 | 2 | `HYPERION_CHECK=1 python3 -m engine.sim dist/cheap/submission.zip --fill bots/chain.py -t 50` (kit dir) | submission 18.58 [14.02,23.14]; 5461 dec, late 1, errors 0, forced 1, p99 250us; actions fold 3480 check 1122 call 174 raise 688; conformance 8 violations: history_prefix/button_changed all on "hand 1" (warm-up state + new-table hand 1 repeats: benign), to_call_bets x3 = kit's short-big-blind rule (to_call is the full bb), kit quirk |
| 7 | 2 | `python tools/gate.py dist/cheap/submission.zip --kit submission/gate_seat.py --entry bot.py --tables 30 --rules submission/rules_tonight.json --variant three_card_keep` | GATE PASS +0.474 ± 1.467 (package 23.15 vs cheap sim 22.68), 0 exc, 0 ill, 0 tmo, p99 146us, import 0.24 s. gate_seat.py written for this kit (one-street log; kit sim covers the real log) |
| 8 | 2 | `python -m pytest -q -x` (first run) | 1 failed, 62 passed: test_drills_fakekits a: 2 timeouts in 69 decisions, max 1.53 ms under load ~7-8 (machine, not our code: fake kit A's reference adapter untouched). Re-running full suite without -x |
| 8 | 3 | `tables.tables_for(rules_tonight)` | source disk, 338 classes (committed tables/variants/three_card_keep): Stage 3 = KEEP committed tables, 0 s, no regeneration |
| 9 | 4 | `python -m hyperion.ship` | SHIP = 'composite', DIALS = {} |
| 9 | 4 | `pack.py --entry submission/bot.py --out dist/ship --extra submission/adapter.py submission/rules_tonight.json --slim --max-mb 10 --import-budget 3` | bot composite dials {}; 85 files 4.5 MB unzipped, 1.0 MB zip; import 0.28 s; imports stdlib+package only; sha256 d179b697... |
| 9 | 4 | `HYPERION_CHECK=1 python3 -m engine.sim dist/ship/submission.zip --fill bots/chain.py -t 100` | submission 24.46 [21.29, 27.63] vs chain 15.51; 16625 dec, late 21 (0.13%), errors 0, forced 37 (hand_over late 37/~13k hands, load ~6), p99 420us; conformance 8 violations: to_call_bets x5 (kit's short-blind rule), history_prefix x2 + button_changed x1 on hand 1 (warm-up/new-table artefact); actions fold 7183 check 2547 call 740 raise 6122 |
| 9 | 4 | flop decision through the adapter (AsAh4h on Ad5d7h) | pre R50, flop R75; 2c3d5h on Ad5d7h: C; fallbacks 0 |
| 10 | 4 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json --variant three_card_keep` ("variant minus shared links, minus token menu") | ship 30.262 ± 1.645 (rival1 21.16, tag 19.63, pushfold 18.44); exc 0, ill 0, tmo 17 / 48326 hands, p99 193us. No separate Stage 0 number was measured tonight (rehearsal): this run is the baseline |
| 10 | 4 | `python tools/latency.py --n 2000 --rules submission/rules_tonight.json` | composite, 3 hole cards: mean 75us p99 220us max 412us, over 1 ms 0; OK (generator load step skipped: shared box already at load 5-8) |
| 10 | 4 | `python tools/gate.py dist/ship/submission.zip --kit submission/gate_seat.py --entry bot.py --tables 100 --rules submission/rules_tonight.json --variant three_card_keep` | package 27.754 vs composite (sim) 28.592: paired -0.838 ± 2.371; 0 exc, 0 ill, tmo 2 (0.01%); GATE PASS |
| 11 | 4 | begin_table timing in the packed zip (50 calls) | p50 0.23 ms, p90 0.52, max 4.8 ms (budget 20); the kit sim's 11-13 ms "table ms" is its slowest single call under load |
| 11 | 5 | `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json --variant submission/chain_variant.py:variant` (chain hooks file: links shared) | ship 30.785 ± 1.682 (rival1 22.51, tag 20.59, pushfold 18.68), exc 0, ill 0, tmo 6 / 44882 hands, p99 183us |
| 12 | 5 | model sim, same command `--mode model`, chain hooks, with and without `--dials '{"hero.multi_call_shift": 1}'` | base 31.156 ± 1.712; cand 30.997 ± 1.745 (-0.16, inside CI; does not rise by half a CI) |
| 12 | 5 | idea dropped: heads-up exact equity from the two known opponent cards (HU both links are shared). `hyperion.core.eval.evaluate` on 8 cards = 160 us, 44 candidates = 7 ms: does not fit 1 ms; not a "small function" in the box |
| 15 | 2 | `python -m pytest -q` (full, second run) | 1 failed, 1271 passed, 1 skipped in 388 s: test_slowbox::test_safebot_panics_on_a_slow_box_only (timing, "worst 1.083 ms" under load); first run's fakekits-a timeout test passed this time. Both timing flakes from the shared box; no code under test changed (submission/ is not imported by tests) |
| 14 | 5 | `python tools/climb_accept.py --stages aware --aware generic:submission/chain_variant.py:variant --base '' --cand '{"dials": {"hero.multi_call_shift": 1}}' --set 10000:10100 --workers 2` | generic_aware (chain_holdem table built 12 s): base 30.745, cand 30.411, -0.334 ± 0.843 level -> multi_call_shift REVERTED (no rise on either field) |
| 16 | 5 | model sim with `--rules submission/rules_chain.json` (variant renamed chain_holdem so Hero reads the hooks-dealt generic table) `--dials '{"hero.twin_multi": 0.01, "hero.variant_tables": "three_card_keep"}'`, and the rename alone | both 30.027 ± 1.731 (identical: twin re-cut not in effect), -1.13 vs base, safe_over 278, max 491 ms (something built inside act): DROPPED, rules stay three_card_keep |
| 17 | 5 | model sim chain hooks `--dials '{"hero.multi_value_shift": 1}'` | 30.640 ± 1.659 vs base 31.156 (-0.52): DROPPED |
| 17 | 5 | aware check `{"dials": {"hero.multi_value_shift": 1}}` | generic_aware 30.745 -> 29.570, -1.175 ± 1.218: DROPPED |
| 17 | 5 | VARIANT PATCH DECIDED: none. Prompt 05 Information: extra hole cards with a variant set loaded (three_card_keep) need no bonus/tightening; the two twist-motivated dials (multi_call_shift 1, multi_value_shift 1) and the hooks-table re-cut all measured level-to-worse; the prompt's keep rule (rise > half CI) fails. Ship unpatched: 02-ship.zip stays the submission | |
| 18 | 4 | `python -m hyperion.sim --tables 40 --rotate --seed 11 --mode strict --field realistic@ship --rules submission/rules_tonight.json --variant submission/chain_variant.py:variant` | ship first 30.770 ± 1.618 (rival1 21.69, tag 19.54, pushfold 16.79); exc 0, ill 0, tmo 73 / 46562 hands (0.16%) |
| 18 | - | kit sim cheap, mixed field (100 t) | 01-cheap pooled 20.7 (22.74 / 18.71) vs chain 25.5, tight 16.8, random 4.38, station 2.50; late 12/19153, err 0, forced 1 |
| 18 | - | `python3 -m engine.sim out/02-ship.zip --fill bots/chain.py -t 50` (the final file itself) | 25.68 [21.16, 30.20] vs chain 15.33; late 27/8395 (0.32%), err 0, forced 59 (hand_over late), p99 580us at load 7.6 (other sessions' arena/climb jobs) |
| 19 | - | same with `--decision-ms 5 --callback-ms 5` | 26.40 vs 15.23; late 1, forced 3: the lates were the machine |

Frozen known-good: d179b697c1b1ad8a6af824a0eabfa717ee39c9cb4286505b035bbf753c0216c5 (hyperion/frozen/T1.zip). Windows cache warm-up skipped (the rehearsal ends at 60; no windows).

## END OF HOUR (stop 22:50:16, minute 19)

Checkpoints (minutes since T0 22:30:34):
- rule sheet + axis classification: min 1 (22:32:05). Axis: information (3 hole cards, 2 shared links); payouts/schedule in rules_tonight.json; token menu in the adapter.
- first valid submission: min 5 (22:35:54) out/01-cheap.zip, sha256 d29ca87fff8e535611f25206928263d4daf07671d8a7b82faf990d17d8ebb37f (Hero.cheap()); gate PASS at min 7.
- ship bot gated and submitted: min 10 (22:41:03) out/02-ship.zip, sha256 d179b697c1b1ad8a6af824a0eabfa717ee39c9cb4286505b035bbf753c0216c5, GATE PASS -0.838 ± 2.371 (100 t).
- variant patch decided: min 17 (22:47:55): none (two dials + a table re-cut measured level-to-worse; prompt 05 keep rule fails).
- final submission: out/02-ship.zip (submitted min 10; re-checked on the out/ file min 18).
- stop: min 19 (22:50:16).

Final: out/02-ship.zip  sha256 d179b697c1b1ad8a6af824a0eabfa717ee39c9cb4286505b035bbf753c0216c5
Plays: composite (rival 3's core preflop / Hero postflop; on 3-hole-card tables Hero plays the table whole on the committed
three_card_keep tables), DIALS {} (SHIP_DIALS as measured), behind submission/adapter.py:TonightAdapter, rules_tonight.json
(hole_cards 3, tonight's blinds, payouts 50/32/21/14/9/5/2/0, extras.variant three_card_keep). Packed --slim, 85 files.

Kit simulator results:
| submission | field | tables | pts/table [95% CI] | best sample bot | late | errors | forced |
|---|---|---|---|---|---|---|---|
| 01-cheap | chain x7 | 50 | 18.58 [14.02, 23.14] | chain 16.35 pooled | 1 / 5461 | 0 | 1 |
| 01-cheap | chain,tight,station,random (2 seats ours) | 100 | 20.7 pooled (22.74, 18.71) | chain 25.5 | 12 / 19153 | 0 | 1 |
| 02-ship | chain x7 | 100 | 24.46 [21.29, 27.63] | chain 15.51 pooled | 21 / 16625 | 0 | 37 |
| 02-ship | chain,tight,station,random (2 seats ours) | 100 | 28.41 [26.18, 30.64] | chain 18.89, tight 15.67 | 12 / 33567 | 0 | 14 |
| 02-ship (out/ file) | chain x7 | 50 | 25.68 [21.16, 30.20] | chain 15.33 | 27 / 8395 | 0 | 59 |
| 02-ship, 5 ms budgets | chain x7 | 50 | 26.40 [21.77, 31.03] | chain 15.23 | 1 / 8934 | 0 | 3 |

What slowed us or broke (minutes) and what would have avoided it:
1. Gate seat for a kit that is none of the fake kits (~3 min, min 6-8): wrote submission/gate_seat.py from KitA. The gate's
   dealer dict carries history rows without streets or blind posts, so the seat cannot rebuild this kit's per-street log;
   it emits a one-street log with increments chosen so the parser recovers the totals. The gate therefore does not test the
   real '/'-separated parser (the kit sim does). Fix: put each row's street (and blind posts) in dealer_state's history, and
   ship a generic "state-object kit" seat with a log-builder hook.
2. The kit's loader unloads the bot's modules and drops its folder from sys.path right after exec_module, BEFORE Agent();
   adapter.py's pin comment assumes it happens after Agent(). Handled at 0 cost by building+warming at module import, pinning
   there, and adding the folder to sys.path twice. Fix: say "pin at module import" in prompt 02 / the template.
3. Warm-up decisions at import show up in HYPERION_CHECK as history_prefix/button_changed on "hand 1" (~1 min to rule out).
   Fix: a conformance reset after warm-up (or tag warm-up states).
4. pytest timing tests fail under load (fakekits-a 2 timeouts, then test_slowbox; ~1 min each to read, 6.5 min suite):
   machine, not code. Fix: a `timing` marker the night can deselect, or a load-aware skip.
5. Twist-forced change has no dial (~4 min of candidates): the real lever is the shared links (heads-up both links are
   shared, so only the private cards differ; Hero prices link-made hands as private). The catalog's nearest entry
   (three_card_keep) deals independent cards; core.eval.evaluate on 8 cards is 160 us, so an exact heads-up enumeration
   (44 x 8-card evals = 7 ms) cannot run in act(). A shared-card variant in the catalog with a prepared table, or a fast
   7/8-card evaluator, would make this a dial.
6. Renaming the variant so Hero reads the hooks-dealt generic table (`hero.twin_multi`, `hero.variant_tables`) lost 1.1 pts
   and put a 491 ms build inside act() (safe_over 278): a latent hazard in the shell's lazy table path for a new variant
   name (~2 min).
7. hand_over is timed at 1 ms here; the composite's hand end (history replay) runs 1-5 ms under load 7.6: 0.3-0.9% of hands
   force the next decision to check/fold; 3 at a 5 ms budget. Machine-dominated, noted, not chased. A deferred hand end for
   state-object kits (as HAND_END_TIMED does for event kits) would remove the exposure.
8. No Stage 0 known-good number in this rehearsal (no Verifier); the strict run at min 10 served as the baseline.
9. climb_accept's --cand format: PLAYBOOK writes `--cand '<the dict>'`, climb_accept's docstring wants {"dials": {...}};
   used the latter.
