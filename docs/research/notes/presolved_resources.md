# Pre-solved resources for a 1 ms Python bot (checked 2026-10-31)

Scope: four asks from the Pre-build section of the report. Everything below was fetched on 2026-10-31
(GitHub API, raw files, vendor pages). Numbers are quoted from the source; where I derived a number
myself (parsing a downloaded file) it says "derived". Known context not repeated here: rules text,
HoldemResources HU chart thresholds already in `exploitative_play.md`, MIT engine clock numbers already
in `competition_lessons.md`.

Two facts that bear on all four items:

- Rules §3.4 reads "Teams may use Astra and Codex to write, debug, and refine their bots during the
  build phase. Publicly available documentation is permitted." Diffing the rules page against
  poker-gym's 2026-10-28 snapshot shows exactly one change since then: §1.2 now allows under-18s with
  parental consent. Nothing about pre-written code, packages, or sandbox CPU was added
  ([rules](https://pokerbot.sequoiacap.com/rules.html); snapshot
  [docs/spec/rules_2026-10-28.html](https://github.com/mack-dot/poker-gym/blob/HEAD/docs/spec/rules_2026-10-28.html)).
- No organizer Q&A exists in public text. x.com and xcancel.com both return HTTP 451 from here; web
  search over X returns only the announcement posts (Sequoia 2115111389501218868, Malani
  2115113318893670464 / 2115494123365126450 "Leaderboards are live", Brown 2115125429619343609,
  Maguire 2115131879452295182). None of the eight prep repos surveyed in item 4 records an answer
  from pokerbot@sequoiacap.com.

---

## 1. Free, machine-readable or transcribable tournament preflop ranges

### 1a. GTO Wizard

**What is free.** The free plan is a per-day view quota, not a depth tier: "100 preflop solutions,
1 postflop solution and 10 Trainer hands a day", 10 analyzed hands a month; the 100 preflop views are
"shared between Cash and Tournament"; custom preflop spots solve free only "when stacks are 10 big
blinds or less" (PokerSkill pricing article, "checked October 2026",
[pokerskill.com/blog/gto-wizard-pricing](https://www.pokerskill.com/blog/gto-wizard-pricing/)). A
second source says the ICM Solver is free "for spots with up to a 10bb effective stack"
([pokerlistings](https://www.pokerlistings.com/news/gto-wizard-introduces-preflop-icm-solving)).
Tiers after the 2026-03-31 consolidation into Cash and Tournament tracks: Starter $49/mo ($39
annual), Premium $99 ($79) = "every preflop solution (ICM spots included in Tournament)", Elite $169
($139) adds postflop ICM, Ultra $279 ($229) early bird until 2026-10-15 13:00 CEST then $359 ($289)
= custom multiway "preflop with up to nine players" ([pokerskill](https://www.pokerskill.com/blog/gto-wizard-pricing/);
[PokerNews plans](https://www.pokernews.com/poker-tools/gto-wizard/plans-and-pricing.htm)). MTT library
coverage I could confirm: ICM sims "10-70 big blind depths at three-max to eight-max tables"
([PokerNews 2025-09](https://www.pokernews.com/news/2025/09/icm-sims-available-at-gto-wizard-49733.htm));
"200-Entry Final Table" set, 3-max to 9-max, 15-60 BB mixed stacks, 560 solutions tagged
"PREFLOP - PREMIUM" ([GTO Wizard blog](https://blog.gtowizard.com/kick-off-2025-with-new-cash-and-icm-solutions/));
8-max General and Simple ChipEV preflop sets exist ([blog](https://blog.gtowizard.com/new-cash-game-mtt-solutions-aggregated-reports-and-new-solutions-for-hh-analyzer/)).
I could not find a page stating which 8-max ChipEV depths a free account can open; the pricing page
redirects to the logged-in app. Assume: 8-max ChipEV RFI/vs-RFI nodes are viewable 100 per day, ICM
nodes are Premium.

**Format.** Web UI only (13x13 grid with per-hand frequencies). No export on any plan that I could
verify; the pokerdata API below is the only machine-readable tournament solver data found.

**Terms (amagama s.r.o., Prague; [gtowizard.com/terms](https://gtowizard.com/terms/)).** §7.5: user
"may not monetize or otherwise use in commerce" content including "poker ranges, poker trees and
poker charts downloaded or otherwise obtained from Service". §7.7: "User shall not use any automated
requests or any scripts within Service." §7.1: no use during a live game (RTA). §8.1: the programs are
copyrighted. There is no clause that literally forbids hand-copying a grid for private, non-commercial
use; there is also no clause granting it. The separate API/Leaderboard terms
([gtowizard.com/benchmark/terms](https://gtowizard.com/benchmark/terms), last updated 2026-02-21) §4.1
forbid "scrape, harvest, or systematically query the API to extract the underlying strategy" and
using benchmarking data "to train, fine-tune, or calibrate any third-party artificial intelligence or
poker solver" ("Model Distillation"). Reading: transcribing a handful of grids into a private repo is
low risk; committing them to a public GitHub repo is redistribution of copyrighted charts and the
"use in commerce" clause is arguable once a $100k prize is involved. Keep anything GTO Wizard-derived
out of the public repo, or regenerate the numbers yourself.

### 1b. Other free range sets (tournament-relevant first)

| Source | Positions | Depths | Spots | Sizes / ante | Format | License |
|---|---|---|---|---|---|---|
| RangeConverter free MTT 8-max ([index](https://rangeconverter.com/free-poker-charts); [100bb](https://rangeconverter.com/articles/poker-charts-8max-mtt-100bb-no-limit-texas-holdem-tournaments); [20bb](https://rangeconverter.com/articles/poker-charts-8max-mtt-20bb-no-limit-texas-holdem-tournaments); also 60/50/40/30/10bb URLs of the same pattern) | all 8-max seats (UTG..BB) | 100, 60, 50, 40, 30 bb with 1bb ante (12.5%); 20 and 10 bb "No Limp" | RFI, facing a raise, facing a 3-bet (at 20bb the 3-bet response is vs all-in only) | open size not stated; frequencies "rounded to the nearest 50%" | one PDF per depth + PNG per chart | none stated; "(c) Stratech Solutions Ltd. All rights reserved" |
| pokerdata.io via `hft-studio/pokerdata-mcp` ([repo](https://github.com/hft-studio/pokerdata-mcp), bridge MIT, pushed 2026-10-30) | 8-max | `nlmtt8`: 10 to 300 bb, 1bb BB ante; `nlh8-hydra`: 10/20/30/60 bb, 0.1bb ante all seats | every preflop node (tokens Fold/Call/Limp/AI/Open/3B), per-hand frequency and EV in sb, `sizeBb` per raise (e.g. 40bb UTG open = 2.19bb) | solver not named; "nlmtt8 is chip-EV only"; ICM, PKO, 9-max MTT explicitly unsupported | JSON over MCP or REST, 169-hand weight maps | Starter key free: 25 calls or 50 MB/month, "Personal use"; redistribution and bulk export need the Custom plan |
| RangeMyHand mirror `hasuwini77/push-fold-ranges` ([repo](https://github.com/hasuwini77/push-fold-ranges), v0.3.0, 2026-10-12) | 9-max UTG(8 behind)/MP(6)/CO(3)/BTN(2)/SB(1); 6-max UTG/CO/BTN/SB | 1 to 25 bb, integer steps | unopened shove only; calling ranges computed but not published | chip-EV, 1.5bb dead, no antes; fictitious play 220 iterations, 6,000 MC samples per matchup | JSON 513,798 B (`spots[]` with `pushFreq[169]`), CSV 991,671 B | CC BY 4.0 |
| PokerNews range charts ([page](https://www.pokernews.com/poker-range-charts)) | six-max and nine-handed, by seat | 6, 9, 12, 15, 18 bb | unopened shove-or-fold | source not named | 10 PNGs + one shared PDF | site notice: may not be reproduced without permission |
| Preflop Wizard MTT guide ([page](https://www.preflopwizard.app/blog/mtt-preflop-strategy)) | UTG..SB (UTG+1 only at 40bb); BB defend % by raiser | RFI at 100/50/40/30; shove at 25/20/15/12/10; 5 and 10bb jam-vs-raise-small | RFI percentages, shove tables, BB defend % | "approximate", solver unnamed, internal inconsistencies (2.5x vs 2.5bb at 30bb) | HTML text tables | none; (c) Heater LLC |
| Freebetrange MTT ([article](https://blog.freebetrange.com/article/mtt-preflop-charts-for-all-positions-and-stack-sizes)) | LJ/HJ/CO/BTN/SB/BB at 50bb; early/middle/late push-fold | 1 to 50 bb (original), 4 to 30 bb (2026 set, HRC solver, 6-max and 8-max) | charts plus push-fold | chip-EV (2026), "GTO and ICM concepts adapted" (original) | images + PDF; account needed for the 2026 set, 50 trainer hands/day free | all rights reserved |
| PokerStrategy BSS full ring ([page](https://www.pokerstrategy.com/strategy/bss/1635/)) | 10-handed UTG1..SB | not stated | open-raise only, three tables (standard/minimal/maximal); e.g. standard UTG1 = 77+, AKo+, AQs+; BTN = 22+, A2o+, A2s+ | open 4bb + 1bb per limper | PDF | (c) PokerStrategy.com |
| PokerStrategy SNG push-or-fold ([page](https://www.pokerstrategy.com/strategy/sit-and-go/787/)) | Early/Middle/CO/BTN/SB | push at <= 13bb (cell = max bb to shove, 4..13) + three rebound charts | push, rebound not in blinds / SB / BB | ICM-based, with Florian "Morgoth" Langmann; not Nash | PDF | (c) PokerStrategy.com |
| pokertournaments101 ([tool](https://pokertournaments101.com/tools/push-fold)) | 10 seats UTG..SB | 1 to 15 bb slider | unopened shove, chip-EV Nash, 12.5% antes | browser only | none, no download |
| PokerAssist `ethoranges-crypto/PokerAssist` ([repo](https://github.com/ethoranges-crypto/PokerAssist), 2026-10-21) | 2 to 9 handed, every open-shove seat and every caller behind | 1.5 to 20 bb in 0.5 steps | push and call thresholds, antes 0 and 0.125 | chip-EV fictitious play, max exploitability 0.00837 BB | `data/pushfold/nash_v1.json` 235,389 B (13x13 threshold grids); `data/equity/preflop_169.json` 292,953 B; `cash_9max_v1.json` hand-authored | **no LICENSE file** (all rights reserved by default) |

Cash-only GitHub sets found and rejected for this game: `rohan2008/poker-preflop-trainer` (80 cash
charts in three JSON files), `tarekmoumane-create/preflop-coach` (~100bb `ranges.json`),
`rdpharr/libregto` (MIT trainer, opening `ranges.js`), `michaellhan/preflop` (now 404),
`HoldemPokerTools/RangeAssistant` (app), PokerBench (LLM dataset, not ranges). Upswing's "Preflop
Prodigy" and PokerCoaching/Jonathan Little free charts are email-gated web apps; no 8-max MTT set by
depth was located for either. No 2+2 thread with posted 9-max Nash tables surfaced in three searches.

RangeMyHand numbers (derived from the JSON, combo-weighted shove %, 9-max): UTG 5bb 18.5%, 10bb
8.9%, 15bb 6.9%, 20bb 5.5%; MP 10bb 10.8%; CO 10bb 23.7%, 15bb 16.9%, 20bb 11.9%; BTN 10bb 33.0%,
15bb 26.0%, 20bb 19.8%; SB 10bb 58.2%, 15bb 45.4%, 20bb 40.4%. UTG 10bb shoves exactly 66+, AJs+,
AQo+. Its 6-max CO/BTN/SB rows are identical to 9-max (the model keys only on players behind), so
8-max seats with 7, 5 or 4 behind are missing and must be interpolated or re-solved.

### 1c. Recommendation for 8-max at 100, 50, 30, 20 bb

Transcribe **RangeConverter's 8-max MTT PDFs** at 100, 50, 30 and 20 bb. They are the only free set
that is 8-max (no seat interpolation), covers RFI + facing-a-raise + facing-a-3-bet, and spans the
four depths asked for; the 50% rounding makes each grid a two-state table that transcribes in about
two minutes. Two corrections to apply: they assume a 1bb big-blind ante (12.5%), and the Sequoia
format has no announced antes, so tighten every RFI by roughly one class step (Preflop Wizard and
pokertournaments101 both state ante-free ranges are tighter; the RangeMyHand ante variant shows
"3 to 23 percentage points wider" with an ante, [methodology](https://www.rangemyhand.com/methodology)),
and they are chip-EV, so the ICM layer stays in code. Cross-check the 20bb and 50bb RFI against
pokerdata `nlmtt8` (28 `get_range` calls fit in one free Starter key) and spot-check a few nodes in
GTO Wizard's free quota. Do not commit pokerdata or GTO Wizard output to the public repo.

---

## 2. Multiway push/fold with ICM

### 2a. HoldemResources free heads-up Nash data (exact format)

- Zip: https://www.holdemresources.net/hrdata/holdemresources_hu_equilibrium.zip, 86,510 bytes,
  contains `holdemresources_hu_push.csv` (2,080,409 B) and `holdemresources_hu_call.csv`
  (2,063,926 B), file dates 2012-05-06 (derived from the archive).
- Layout (derived): header `stack, 22, 32o, 42o, ..., A2o, 32s, 33, 43o, ..., AKs, AA` = 1 + 169
  columns, order is the 13x13 grid flattened row by row from the deuce row (offsuit left of the
  diagonal, suited right). 3,981 data rows, `stack` from 1.00 to 200.00 in 0.05 steps. Cell values
  are push (or call) **frequencies** 0..1 at 0.01 resolution (101 distinct values), not thresholds;
  mixed cells appear near each hand's boundary (e.g. 22 push = 0.65 at 52.50, 0.41 at 52.55).
- Thresholds derived from the files (last stack with nonzero frequency), push / call: 22 59.8 /
  15.1; A2o 29.2 / 16.1; K2o 11.65 / 8.3; J2s 8.85 / 5.65; T3s 7.7 / 4.85; Q2o 7.05 / 5.65; 72o
  1.6 / 2.65; AA 200 / 200. These agree with the on-page chart (22 "20+", K2o 11.6, T3s 7.7, Q2o
  calls 5.6) to within one 0.05 step; the page warns the download "was re-calculated with a later
  version than the original chart data" ([HUNE page](https://www.holdemresources.net/hune)).
- No license or terms on the page or in the zip; the site's Terms of Use page only governs HRC
  license keys ([legal](https://www.holdemresources.net/legal)). Entity: HoldemResources GmbH.
- Free web **Nash ICM Calculator** ([nashicm](https://www.holdemresources.net/nashicm)): three
  inputs (Stacks, Blinds, Prizes), "free push-or-fold Nash ICM calculations for the endgame"; the
  page states no player limit or algorithm. PokerStrategy's Nash push-or-fold article says its ranges
  were produced with this free calculator ([pokerstrategy 1779](https://www.pokerstrategy.com/strategy/sit-and-go/1779/)).
  Useful for spot-checking a handful of 8-stack ICM spots by hand, not for bulk extraction.

### 2b. What the commercial tools run

- **HRC (desktop):** "Run Nash Calculation" offers Fictitious Play (default) or CFR+; FP iterations
  25 to 100,000; convergence shown as "Exploit%"; the official support thread says Nash
  calculations are "restricted to a maximum of 3 active players" (older statement, may be stale);
  the multi-table ICM model is advertised as "within +/- 0.01%" of true ICM
  ([2+2 HRC thread p.24](https://forumserver.twoplustwo.com/167/poker-software/holdemresources-calculator-hrc-1705032/index24.html);
  [PokerStrategy support thread](https://www.pokerstrategy.com/forum/thread.php?threadid=213128&page=9)).
- **ICMIZER 3:** "CFR+ Nash calculation engine"; ICMIZER 2 used "linear methods"; models ICM, FGS
  (depth up to 6) and ChipEV; vendor says it returns "the Nash equilibrium approximation which is
  closest to the ideal" ([features](https://www.icmizer.com/en/icmizer-3-features/)). Free use:
  1 calculation/day as guest, 3/day registered (launch-era blog), 7-day trial
  ([icmizer blog](https://icmizer.com/en/blog/icmizer-is-officially-released)).
- **SNG Wizard:** no algorithm published; a competitor claims it uses simplified ICM (4 outcomes vs
  13) and obtains Nash ranges from an external web page
  ([icmizer comparison](https://icmizer.com/en/blog/icmizer-1-year-birthday-and-vs-sng-wizard-comparison)).

Pattern: every tool solves the all-in-or-fold tree over 169 classes with an equity matrix, iterates
best responses (fictitious play) or regret matching (CFR+), and swaps the chip payoff for an ICM
payoff computed from the stack vector after each outcome. None of the three is open.

### 2c. Open-source implementations that could solve 8-player all-in-or-fold with ICM in minutes

- **`ryankkhalil19/microholdem`** ([repo](https://github.com/ryankkhalil19/microholdem), MIT, created
  2026-10-29, built "for the format of the No Limit pokerbot tournament"). `pushfold.solve_multiway`
  is a 150-line numpy CFR+ (regret matching+, linear averaging) for a first-in jammer against k <= 7
  independent callers, no-overcall model, callers conditioned on reaching; convergence reported as
  the largest best-response gain because the game is general-sum. Shipped tables: 2 to 25 bb step 1
  x 1..7 behind (`pushfold_multi.npz`, 1,042,838 B), max BR gain 1.86e-5 BB/hand, whole multiway
  table build 200.95 s on an M1 at 2,000 iterations (`data/meta.json`); heads-up tables 1 to 25 bb
  step 0.5, max exploitability 4.9e-5 BB, 10bb SB jams 58.4%. ICM is applied at decision time, not in
  the solve: `_icm_jam_vs_fold` re-evaluates a first-in jam in ICM equity using the solved calling
  ranges (up to 16 ICM calls at 1.8 us each in the C++ subset DP), and `_icm_call_allin` does the
  same facing a shove. Also ships a 169x169 MC class-equity matrix (40,000 deals per pair, SE ~0.25%),
  an 8-max SNG simulator with the exact Sequoia schedule (2,000 chips, 10/20 rising every 25 hands,
  200-hand cap, ICM at the cap, dead button) and a latency harness (agent p99 125 us). Needs a C++17
  compiler for the pybind11 core; the solver itself is pure numpy.
- **`ethoranges-crypto/PokerAssist`** `engine/pushfold.py`: fictitious play with step 1/(t+1), 1,500
  iterations, 2 to 9 players, antes supported, exact card removal between pusher and caller, reports
  exploitability; the chart builder uses `multiprocessing.Pool` over 2 antes x 8 table sizes x seats
  x 38 stacks. Pure numpy, but no license.
- **OpenSpiel `universal_poker`:** `kMaxUniversalPokerPlayers = 10`, `numPlayers` parameter,
  `betting=nolimit`, `bettingAbstraction=fcpa`
  ([universal_poker.h](https://github.com/google-deepmind/open_spiel/blob/master/open_spiel/games/universal_poker/universal_poker.h)).
  It can represent an 8-player all-in-or-fold game, but the payoff is chips, CFR in n-player
  general-sum games has no convergence guarantee, and the ACPC gamedef route is more work than the
  numpy solver above. Not recommended.
- `rt500/Heads-Up-Push-or-Fold` (C++ HU solver) now returns 404.

**Build note for our own ICM solve.** Take microholdem's `solve_multiway` and replace the chip payoff
per (hero class, caller class, outcome) with `ICM(stacks_after) - ICM(stacks_before)` for the actual
8-stack vector and the announced point vector. The payoff then depends on the full stack vector, so
tables must be keyed on (players left, position, hero stack bucket, a coarse "covering/covered"
descriptor) rather than one effective stack; a 5-bucket x 8-seat x 7-players-left grid at 1,500
iterations of 169x169 numpy is on the order of 10^3 to 10^4 solves, i.e. minutes to an hour on a
laptop, and can be regenerated at build start once the payouts are known (import-time compute is not
clocked by rule 3.7 as written). Validate the chip-EV special case against HRC HU (above) and
RangeMyHand 9-max (within 2 pp of HRC at 5/10/15/20 bb per their own check).

---

## 3. MIT Pokerbots 2026 engine and skeleton; Sequoia pages

### 3a. Exact Python skeleton (engine-2026, master, fetched raw)

- Repo: https://github.com/mitpokerbots/engine-2026 (created 2025-11-16, last push 2026-01-16, **no
  LICENSE file**; engine-2022 was MIT). Variant: 3 hole cards, discard one face-up after the flop.
  Files: `engine.py` (594 lines), `config.py`, `python_skeleton/{player.py, commands.json,
  skeleton/{bot.py, runner.py, states.py, actions.py}}`, plus `java_skeleton/`, `cpp_skeleton/`,
  `player_chatbot/` (a stdin-driven human player).
- `skeleton/bot.py`: `class Bot` with `handle_new_round(self, game_state, round_state, active)`,
  `handle_round_over(self, game_state, terminal_state, active)`, `get_action(self, game_state,
  round_state, active)`; each raises `NotImplementedError`. `player.py` defines `class Player(Bot)`
  and ends with `run_bot(Player(), parse_args())`.
- `skeleton/states.py`: `GameState = namedtuple('GameState', ['bankroll', 'game_clock',
  'round_num'])`; `TerminalState = namedtuple('TerminalState', ['deltas', 'previous_state'])`;
  `class RoundState(namedtuple('_RoundState', ['button', 'street', 'pips', 'stacks', 'hands',
  'board', 'previous_state']))` with `legal_actions()` returning a **set of action classes**
  (e.g. `{FoldAction, CallAction, RaiseAction}`), `raise_bounds()` returning `(min_raise_to,
  max_raise_to)` as total street contributions (`pips[active] + contribution`), `proceed(action)`,
  `proceed_street()`, and a stub `showdown()` that returns zero deltas (the real one lives in the
  engine). Constants `NUM_ROUNDS = 1000`, `STARTING_STACK = 400`, `BIG_BLIND = 2`, `SMALL_BLIND = 1`.
  Active player is `button % 2`; everything is hard-wired to two players (`hands[1-active]`,
  `deltas = [-delta, -delta]`).
- `skeleton/actions.py`: `FoldAction = namedtuple('FoldAction', [])`, `CallAction`, `CheckAction`
  (empty), `DiscardAction(card)` (index 0..2), `RaiseAction(amount)` ("we coalesce BetAction and
  RaiseAction").
- `skeleton/runner.py`: `Runner(pokerbot, socketfile)`; `receive()` yields `readline().strip().split(' ')`;
  `send()` writes `F`, `C`, `K`, `D<idx>` or `R<amount>` + `\n`; `run()` rebuilds state from clauses
  `T<clock>`, `P<index>`, `H<c1,c2,c3>`, `G` (round start, triggers `handle_new_round`), `F/C/K/D#/R###`
  (history), `B<cards>`, `O<opp cards>` (backtrack to a `TerminalState`), `A<delta>` (triggers
  `handle_round_over`), `Q` (quit); sends `K` as an ack whenever it is not the bot's turn.
  `parse_args()` takes a positional `port` and `--host` (default localhost); `run_bot()` opens
  `socket.create_connection` and `sock.makefile('rw')`.
- Engine side (`engine.py`): `Player.build()` reads `commands.json` (`{"build": [], "run":
  ["python3", "player.py"]}`), runs `build` with `BUILD_TIMEOUT = 10.0`, then `run` with the port
  appended, accepts with `CONNECT_TIMEOUT = 10.0`, sets the per-message socket timeout
  `PLAYER_TIMEOUT = 120`. `query()` writes `T{clock:.3f} ...`, measures `perf_counter()` around
  `readline()`, subtracts from `game_clock` (`STARTING_GAME_CLOCK = 60.0`, `ENFORCE_GAME_CLOCK =
  True`), validates the action against `legal_actions()` and `raise_bounds()`, and on timeout,
  disconnect, misformat or illegal action returns `CheckAction() if CheckAction in legal_actions else
  FoldAction()`. Hand evaluation is the custom `pkrbot` package (pyproject: `cython>=3.2.3`,
  `pkrbot>=1.1.0`; README says 1.0.4), installed with `uv sync`.
- **Local run with custom bots: yes.** Edit `config.py` (`PLAYER_1_PATH = "./player_chatbot"`,
  `PLAYER_2_PATH = "./python_skeleton"`, names, `GAME_LOG_FILENAME`, `NUM_ROUNDS`, stacks, blinds),
  point a path at any directory containing `commands.json`, run `.venv/bin/python engine.py`.
  Heads-up only; adding seats means rewriting `RoundState`.
- Reference bots for 2026: `reference-1-2026` .. `reference-3-2026`; 2025 had eight including a CFR
  demo, a PyTorch demo and an "Exploitative Bandit Bot" ([org listing](https://github.com/orgs/mitpokerbots/repositories)).

Transfer value to the Sequoia kit: the organizers say "Agent interface", singular, and a local
simulator in one kit, which is closer to poker-gym's in-process `act(obs)` than to MIT's socket
process. The MIT pattern worth keeping is the trio of hooks (new round, action, round over), legal
actions as a set, and raise bounds as absolute "raise-to" totals; code the adapter to tolerate both
raise-to and raise-by.

### 3b. People, Citadel, MIT on the Sequoia pages

- Landing page, rules and privacy name **no individuals**. The only identifiers are "Department of
  Algorithmic Play, 2800 Sand Hill Road, Menlo Park", "Organized by Sequoia Capital Operations, LLC
  and Hosted by OpenAI and Citadel Securities", and pokerbot@sequoiacap.com. Citadel Securities
  appears only as Host (rules preamble, §8.2 recruiting-data consent, §8.3 photo release). "MIT" does
  not appear anywhere on the site; the MIT link is Noam Brown's post about 6.9630 and his statement
  that he will be at the finals. Decorative exhibit bots are named CFR-7, MONTE and NASH.
- FAQ answers present on the landing page: eligibility (US/Canada students via school email, classes
  of 2025/2026, 18+ or consent), teams of two, travel covered for top teams, application deadlines
  Nov 3 PT / Nov 6 ET / Nov 9 ET, decisions by Nov 5 / Nov 8 / Nov 11.

### 3c. Castle Challenge code and data idioms

- `/castle_challenge/data/leaderboard.json` (598.8 KB, `generated_at` 2026-10-31T08:51:35Z, 3,189
  g1 and 1,603 g2 entries): top-level keys `g1`, `g2`, `generated_at`; each entry
  `{f, id, l, n, p, r, s}` = first name, 10-hex id, last initial, display name, points (3 dp), rank,
  school. Single-letter minified keys, snake_case for the one multi-word key.
- `app.js` (19,520 B) and `lib.js` (5,767 B): vanilla ES5/ES6, UMD wrapper, `const CONFIG = {
  DATA_URL, CLAIM_WEBHOOK_URL: 'https://hooks.zapier.com/hooks/catch/10281689/49ht6h2/', ACCENT:
  '#2EE6A6' }`, `fetch(CONFIG.DATA_URL, { cache: 'no-store' })`, camelCase helpers (`displayName`,
  `padRank`, `formatScore`), Google Analytics tag, "claim your spot" posts to a Zapier webhook.
  Game 2 text confirms placement payouts 9/4/2/0 over "1,000,000 randomly drawn groups"; Game 1 is
  the full pairwise matrix.
- Reading: a small marketing-engineering surface (static JS + Zapier + a 15-minute batch job), not a
  platform team. It gives no signal about the Python kit's field naming beyond "short keys,
  snake_case in data files". Do not infer the Agent interface from it.

---

## 4. Unofficial prep repos (as of 2026-10-31)

### 4a. `mack-dot/poker-gym` (MIT, created and last pushed 2026-10-28, 96 files)

- **Guessed interface** (`pokergym/agent.py`): `class Agent(Protocol): reset(self, table:
  TableInfo) -> None; act(self, obs: Observation) -> Action`. `TableInfo(seat, num_players,
  starting_stack, rules_name, seed)`. `Observation` slots: `hand_number, street, seat, button,
  small_blind, big_blind, ante, hole_cards, board, stacks, bets, committed, in_hand, all_in, pot,
  to_call, can_check, can_raise, min_raise_to, max_raise_to, history, num_players, live_players`;
  `legal_actions` property; `is_legal(a)`. `Action(kind: ActionType{FOLD, CHECK, CALL, RAISE},
  amount)` where amount is the **raise-to total for the street**; text codec `"raise:400"`.
  `AgentAdapter(deadline_ms=1.0, mode="enforce"|"record"|"off")` times `act()` with
  `perf_counter_ns`, catches exceptions, checks legality, falls back to check-else-fold. The docstring
  is explicit that the official names are unknown; `adapters.py` holds an `OfficialAgentShim` with
  injected translators, and `bridge.build_observation(**plain_values)` derives pot/to-call/bounds.
- **Strategies shipped:** fixtures `CallBot`, `RandomBot`, `HeuristicBot` (Chen score, open
  thresholds 9.0/8.0/6.5/7.5 by early/middle/late/blinds, shove under 10bb, 3-bet at score >= 11);
  sparring `tag`, `lag`, `shortstack`, `icm` (TAG plus an ICM risk premium from `icm_equity_for`),
  `adaptive` (uses `OpponentTracker`: VPIP, PFR, 3-bet, fold-to-steal, c-bet, aggression); `examples/
  my_bot.py` opens by `hand_percentile` with widths (0.12, 0.17, 0.28, 0.32) by position bucket at
  2.5bb, shoves at <= 12bb with 1.8x width, calls shoves by `equity_vs_top(c1, c2, 0.15)` vs pot odds
  + 0.05. Data: `preflop_equity.json` 24,050 B (169 classes vs N opponents, MC).
- **Variant assumptions:** baseline NLHE; SYNTHETIC payouts `(100, 60, 40, 25, 15, 10, 5, 0)`;
  SYNTHETIC blinds `(10,20) (15,30) (25,50) (50,100) (75,150) (100,200) (150,300) (200,400)`, no
  antes; dead button; same-hand busts ranked by starting stack. Mutation pool for the sealed drill:
  17 rules in 6 families (hand ranking swaps such as two-pair-beats-trips, raise cap 1 or 2, antes
  0.25/0.5 bb, turbo blinds, payouts winner-take-all / top-heavy (150,60,25,10,5,3,2,0) /
  flat-top-four / survival, board patterns two-two-one / four-one / all-five).
- **Measured:** 30-34k hands/s per core, 10,000 tables in 6-21 s on 8 workers, fixture-bot latency
  p50 0.1-2 us, p99.9 <= 21 us, 1 call in 214,293 over 1 ms from a GC pause; `deadline_mode="enforce"`
  made replays non-deterministic (2-6 of ~350,000 decisions per run), so the default is `record`.
- **Defect to know:** `docs/runbook_60min.md` and `drills/fake_kit/README.md` both say the budget is
  "1,000 ms per rule 3.7"; the rules and the repo's own `official_rules_v1.md` say 1 ms. The code
  default is 1.0 ms. Do not copy the prose.
- **From the organizer:** nothing beyond the rules snapshot; `docs/fidelity.md` lists the unknowns
  (interface, payouts, schedule, deadline semantics, hardware) verbatim as unknowns.

### 4b. `amalkoch/pokerbot-lab` (no license file, created 2026-10-28, pushed 2026-10-30)

- **Interface:** two-player Kuhn poker only. `Observation(card, history, seat, legal_actions)`,
  policy = `Callable[[Observation, random.Random], str]` returning `"check" | "bet" | "call" |
  "fold"`; exceptions and illegal actions fall back to check-else-fold; `run_match` swaps seats on
  each deal and reports chips/hand with a 95% half-width and per-seat timing (median, p99, max,
  count over 1 ms).
- **Strategies:** `cautious`, `calling`, `random`, `mixed`; OpenSpiel CFR / CFR+ / external MCCFR
  on Kuhn and Leduc (CFR+ Leduc exploitability 0.000246 after 1,000 iterations, 6.81 s); PokerBench
  preflop imitation models (decision tree 91.42% grouped test accuracy, p99 0.116 ms; boosted trees
  91.69%, p99 0.634 ms with 4 of 1,000 calls over 1 ms; zero check targets in training because of the
  grouped split). `poker_math.icm_equities` (subset-cached Malmuth-Harville), `tournament_risk.py`
  (chip EV vs ICM EV example: +4 chips but -1.3667 points, break-even 60.2564%).
- **Variant assumptions:** none modelled; invented payouts only in examples.
- **From the organizer:** none. The README says "Do not assume prewritten code can be brought into
  the competition; confirm that with the organizer" and "The event variant and Python Agent interface
  are not yet available."

### 4c. Repos created since 2026-10-27 that mention or match the format

GitHub search (`created:>2026-10-27`, terms pokerbot / "No Limit" / sequoia / millisecond) returns
ten repos; after reading READMEs and trees:

| Repo | Created | What it is | Interface guess | Sequoia-specific content |
|---|---|---|---|---|
| `ryankkhalil19/microholdem` | 2026-10-29 | C++/numpy engine + solvers + SNG simulator "built for the format" (see 2c) | `MicroAgent.reset(seat, n_seats, seed)`, `act(obs)` with `obs.payouts` | quotes rules 3.2-4.5; notes 3.4 "publicly available documentation" and 8.4 third-party licenses; "whether any of it may be reused at the event is a question for the organizers" |
| `ela57/pokerbot` ("Poker Practice") | 2026-10-30 | PokerKit 0.7.7 engine, 8-player SNG runner, SQLite logs, paired-seed compare | `Bot.on_table_start(TableStartInfo)`, `act(obs) -> Action`, `on_hand_end(PublicHandResult)`; `Observation` has `seats[]` with `anon_id`, `pot_breakdown`, `level`, `hands_remaining`, `payouts`, `legal` with `min_raise_to/max_raise_to`; RAISE = total street contribution | `configs/rules.yaml` uses the **same** synthetic payouts (100,60,40,25,15,10,5,0) and blind ladder as poker-gym, labelled ASSUMPTION; `timing.yaml` 1 ms soft + 50 ms `setitimer` hard; `aggregate6` notes the weighting normalization is unknown |
| `qbeka/No-Limit-a-bot-building-tournament-simulations` | 2026-10-29 | Castle Challenge only; exact scoring of all 4,598,126 Game 1 allocations under synthetic fields | n/a | chosen allocations `[3,5,27,2,63]` (9.3542/15 modelled) and `[2,34,3,59,2]` (6.9413 payout modelled); confirms Game 2 payouts 9/4/2/0 |
| `YosiefAbraham/pokerbot` | 2026-10-28 | 8-bot NLHE bench, 50/100 blinds, 10,000-chip rebuy cash, tight profiler bot | own `GameState` dataclass; `adapter.py` is the only file that knows a dealer format; JSON over stdin/stdout planned | none; not the tournament format |
| `GeorgeBarnes06/pokerbot` | 2026-10-28 | Rust 8-player simulator + Next.js replay viewer; runner is a stub `println!` | none yet | none |
| `pokerbots-dev/pokerbots` | 2026-10-29 | separate product pokerbots.dev (USDC payouts, Cloudflare workers, sandboxed runner) | template `class Bot: def act(self, state): ... return ("check",)`, `state["legal"]` | none; unrelated commercial launch |
| `anaerobia/pokerbot` | 2026-10-28 | heads-up MIT-style teaching engine, `get_action(view)` | n/a | none |
| `justmycode37/Pokerbot`, `AdarshPay/PokerBot` | 2026-10-31 / 10-28 | empty | | |

Also seen: `hanifnoerr/poker-challenge` (local arena, five-game matches, not this format) and
`hyattc1/hyperion` (ours). Two independent repos converging on the identical synthetic payout vector
and blind ladder is a sign both were drafted by the same class of coding agent, not of leaked
organizer data; treat those numbers as placeholders.

---

## Recommendations

**Item 1, pre-solved preflop ranges: pull in, privately.** Transcribe RangeConverter's 8-max MTT
PDFs at 100/50/30/20 bb (RFI, vs-RFI, vs-3-bet; about 60 two-state grids per depth at 50% rounding),
tighten one class for no ante, and store them as a 169-entry dict per (depth, position, spot) in a
private data file; pull pokerdata `nlmtt8` RFI at the same depths through a free Starter key (28
calls) as the machine-readable cross-check and keep it out of the public repo; spend at most 30
minutes in GTO Wizard's free quota on the 20bb and 30bb BTN/SB/BB nodes. Effort: 1 day for
transcription plus a 2-hour cross-check script. Skip PokerNews, Preflop Wizard, Freebetrange and the
cash-only GitHub sets.

**Item 2, multiway push/fold with ICM: pull in microholdem's solver, cross-check everything else.**
Vendor the ~150-line `solve_multiway` (MIT) into our generator, swap the chip payoff for an ICM
delta on the real 8-stack vector, and emit tables keyed on players left, position and hero stack
bucket; regenerate at build start when payouts are announced. Validate the chip-EV case against the
HRC HU CSVs (thresholds above, 0.05 bb grid) and RangeMyHand 9-max (CC BY 4.0, cite it), and use
HRC's free Nash ICM web calculator for three or four hand-entered 8-stack spots. Do not copy
PokerAssist's data (no license); its FP code is a useful second reference for antes. Effort: 1 day to
port and validate, half a day for the ICM payoff and bucketing, 10-60 min of laptop compute per
table set.

**Item 3, MIT engine and Sequoia pages: cross-check only.** The MIT skeleton is heads-up and
socket-based, so none of it ships; what carries over is the hook trio, legal actions as a set,
absolute raise bounds, and the fallback rule, all of which the adapter drill should tolerate
alongside the in-process `act(obs)` style. The Sequoia site names nobody and the Castle code is a
static page plus a Zapier hook, so there is nothing to mine for the kit's idioms. Effort: 1 hour to
add the MIT variants to the fake-kit drill; zero further time on the Sequoia pages until the kit
drops.

**Item 4, unofficial prep repos: pull in two pieces, skip the rest.** Take poker-gym's fake-kit drill
pattern (the traps table: raise-to vs raise-by, card spelling, pot inclusion, status encoding, per-hand
vs per-street totals) and ela57's richer `Observation` field list as the superset our adapter must
map from; take microholdem's SNG simulator semantics (dead button, short-all-in rule, ICM at the cap)
as a second reference for our harness. Nothing in any repo came from the organizers, both poker-gym
docs misstate the deadline as 1,000 ms, and the shared synthetic payouts are placeholders. Effort: 2
hours to read the drill and port the trap table into our own drill; skip pokerbot-lab (Kuhn only),
YosiefAbraham, GeorgeBarnes, pokerbots.dev and the empty repos.
