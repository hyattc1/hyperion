# Prompt drill 3 — Track B (blank directory), kit A (class-based `Agent.act(state) -> str`), variant "Lucky Seven bounty" (payoff axis)

Date 2026-10-31, T0 05:43:48 EDT. Same protocol as drills 1 and 2 (`drills/log/prompt-drill-1-kitB-permuted.md`,
`docs/drills/prompt-drill-2-kitC-payoff.md`): operator and agent were the same model in strictly separated roles.
This time the agent had **no repository**: it saw only the prompts, the operator's one-page rules text (appendix),
the kit copied into a scratch directory, and the text of `docs/prompts/track-b-from-scratch.md`. It never read,
imported or grepped `/home/connor/dev/hyperion` (every path in `NIGHT.md` is under the scratch directory). The real
repo was at `7a7c084` with a clean working tree at T0; this drill wrote only this report. Another session edited
`hyperion/strategy/{hero,postflop,preflop,pushfold}.py` and two tests between 05:52 and 05:56 (37 insertions, 17
deletions, uncommitted), before the 06:05 sim comparison below, so "Hero" there is `7a7c084` plus those edits
(drill 2's protocol finding 4 again; the agent role was unaffected because it never read the repo). Scratch:
`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/drill3/` with `kit/`
(the copied kit), `bot/` (`submission.py`, the per-step copies `submission_step{1,2,3}.py`, `test_bot.py`,
`bench.py`, `mix.py`, `NIGHT.md`), `submissions/` (four hashed zips) and `operator/` (rules text, clock log, the
sim wrapper). Venv: `uv venv .venv --python 3.12` (3.12.12) plus pytest 9.2.0, nothing else. The box carried
another session's work throughout (load 5.5–8.4 on 8 cores), which shows in every latency tail below.

Hidden variant: standard hold'em, 8-max SNG, 2,000 chips, 10/20 rising every 25 hands over eight levels, 200-hand
cap, points 10/7/5/4/3/2/1/0 with ICM at the cap, and a house bounty: a player who wins a pot **at showdown**
holding a Seven gets 50 chips added to their stack by the house (adapted from the catalog's `bounty` entry in
`hyperion/drills/variants.py`, simplified to a fixed rank and a fixed sum). The kit's dealer does not pay it; the
agent had to find that out.

Kit set-up note (operator). `fakekits/_table.py` imports `hyperion.core.{cards,eval,types}`; copying those would
have put the real evaluator in front of a Track B agent whose step 2 is "write the evaluator". The copy therefore
carries an operator-written `_core.py` (52-card deck, brute-force showdown evaluator, trivial `Rules`) and the
import line changed to `from ._core import ...`; the kit's prose lost its two framework names and the rubric's run
line became `python -m fakekit.kit_a.runner submission.py`. Nothing else in the kit changed.

## Key numbers

| Score | Result | Target |
|---|---|---|
| Legal cheap bot: kit runner PASS, tests green, zip hashed | **minute 4** (05:48:10) | 15 |
| Evaluator + profiler + exploits in, runner PASS, zip hashed | **minute 9** (05:53:47) | 30 |
| Equity table + ICM gate in, runner PASS, zip hashed | **minute 17** (06:01:09) | 45 |
| Bounty patch (prompt 05 payoff section) in, runner PASS, zip hashed | **minute 19** (06:03:01) | if time |
| Agent role ended | minute 20 (spec exhausted) | 60 |
| Final kit-runner line, `--hands 50 --seed 1` | `PASS: 50 hands, 87 decisions, 0 timeouts, 0 exceptions, 0 illegal, delta -783, mean 0.016 ms, max 0.060 ms` | 0 exc, 0 illegal |
| Long legality runs, final bot, `--hands 2000` seeds 11/12/13 | 1,559 + 1,461 + 1,400 = **4,420 decisions, 0 exceptions, 0 illegal, 2 timeouts** (one 4.04 ms spike on seed 12; max 0.39 / 4.04 / 0.25 ms); `--hands 500 --budget-ms 0.5`: 403 decisions 0/0/0 | |
| 2,000-call timing loop on the final bot, three runs (load 7.1) | **mean 4.9 / 4.6 / 3.9 µs; max 1,155 / 784 / 619 µs**; p99 14.8 / 21.7 / 11.5 µs. Constructed worst cases at 8 players: first act of a hand (ICM fold value) mean 50 µs max 124; new hand plus shove-call (two more ICM evaluations) mean 100 µs, max 318–664 | mean < 100, max < 500 |
| Import time of the final bot | 2.9–3.8 s (evaluator 0.17 s, Monte Carlo 2.7 s) | no stated budget |
| Lines of code written | `submission.py` **452** (401 non-blank; 148 after step 1, 340 after 2, 449 after 3, +10/−7 for step 4); `test_bot.py` 84, `bench.py` 50, `mix.py` 34: **620 lines of code**, plus `NIGHT.md` 253 lines | |
| Human questions needed | **0 asked**; 34 ambiguities resolved by a recorded guess (12 in step 1, 8 in step 2, 11 in step 3, 3 in step 4) | 0 |
| Bounty discovered as unimplemented in the kit | yes, minute 1, in the rule sheet, by reading `_table.Table._showdown` | |
| Things we had to undo | none; two of the agent's own bugs caught by its own tests before a zip (65s bound, exploit gate) | |
| Track B final bot vs the bestiary in the real sim, 300 tables strict seed 11, tonight's payouts (operator, after the drill) | default field **5.821 ± 0.280, 2nd** (hero 6.785, tag 5.697, nit 5.036); realistic field **5.006 ± 0.315, 2nd** (hero 5.560, tag 4.909, loose_aggro 4.878, pushfold 4.554); strong field **3.879 ± 0.343, 5th of 8** (hero 4.816, tag 4.190, hero_tight 4.006, pushfold 3.577). exc 0, ill 0 everywhere; timeouts 135 / 222 / 254 vs hero's 87 / 105 / 84 | "not last" |
| Step-1 cheap bot in the same default field | **5.448 ± 0.264, 3rd** (hero 7.151, tag 5.762, nit 5.004); steps 2–3 are worth +0.37 | |
| Reference: untouched Hero, same field without us, tonight's payouts | hero 7.330, tag 6.137, nit 5.589 | |

Timeline (wall-clock minute at which each pass check was met):

| Prompt / step | Minute | Notes |
|---|---|---|
| 00 briefing | 0 | restated in one paragraph; "no repo path given" branch taken |
| 01 rule sheet | 1 | payoff axis (bounty + point table); every other default confirmed; kit dealer pays no bounty, is 4-seat with six levels and never ends a table at 200 hands |
| Track B step 1 + prompt 02 (Track B section) | 4 | 148 lines, zero imports; runner 50 hands 98 decisions 0/0/0 max 0.192 ms; first test run caught my own 65s bound (`b >= 4` is 76s+); mix over 100 hands F67 C57 R37, no CALL on seed 1 (one on seed 4); zip `4cc8f2f1…cc409` |
| step 2 | 9 | evaluator 7,462 classes, NF 73,775 keys, FL 4,719, built in 0.17 s, verified against brute force on 3,000 random 7-card hands; profiler flagged the kit's rock as "maniac" (observation bias, below); zip `63c1b2ad…f18d` |
| step 3 | 17 | 169 × 2 Monte Carlo, ICM exact (8 equal stacks 4.0000, seats sum to 32.0000), 48 µs per evaluation at 8 players; samples raised 400 → 2,000 (deviation, below); zip `1b6982b3…0d82` |
| step 4 (prompt 05, payoff section) | 19 | 50 chips added to dead money in every all-in ICM gate and to the pot in the draw pot-odds test; thresholds widened by one class for Seven hands while bb ≤ 50; zip `8fab0ef1…2ae` |

## How the bounty was handled

1. **Rule sheet (minute 1).** Quoted s.4 verbatim under "Scoring: any bounty or side payoff", classified the
   variant as payoff-only, and wrote: "The kit's local dealer does NOT pay this bonus: `_table.Table._showdown`
   awards the pot and side pots only, nothing reads hole ranks after the showdown ... So nothing we measure
   locally can show the bounty's value; it has to be reasoned, not simmed." Assumption diff: payouts and bounty
   only; "invalidates no table".
2. **Steps 1–3** ignored it, as the spec orders (step 4 is the variant patch).
3. **Step 4 (minute 19).** Applied prompt 05's payoff lines literally where they map onto the from-scratch bot:
   `bounty = 50` when a hole card is a Seven; added to the dead money of every all-in ICM comparison (an all-in
   goes to showdown, so the bonus is certain when we win) and to the pot in the draw call test; percentile
   thresholds widened by `0.01` (about one class, the spec's "not more than one rank step") for Seven hands, and
   only while 50 chips is at least a big blind (levels 1–3). Demonstrated on constructed spots: 77 vs a 20 bb
   shove gain +0.157 → +0.183 points, 76s stays a fold (−0.075 → −0.056), 76hh flush draw facing 100 into 300
   calls where 86hh folds. The agent stated that the re-run proves legality only and that prompt 05's "show that
   hero's points did not drop" cannot be executed in Track B, and kept the step-3 zip as the fallback.

Right behaviour throughout; the only cost of the bounty was two minutes.

## Sim comparison (operator role, untimed, after the agent role ended)

Drills 1 and 2 scored "Hero points vs the bestiary"; Track B has no Hero, so the operator wrote a 40-line wrapper
(`operator/simcompare.py` in scratch) that turns the engine's `Observation` into kit A's `GameState` (the inverse
of `KitAAdapter`), registered the final bot as `trackb` and the step-1 cheap bot as `trackb1` in
`bestiary.REGISTRY`, and ran `run_tournament(..., tables=300, seed=11, mode="strict", rules=Rules(payouts=(10,7,5,
4,3,2,1,0)))` from the real repo's venv. The engine does not pay tonight's bounty (the catalog's `bounty` hooks
implement a different rule), so every line below is the variant minus the bounty under tonight's point table; the
step-4 term is inert here except for the one-class widening at levels 1–3. The box was at load 7–8 throughout, so
strict-mode timeouts (each one a fold) are inflated for every bot.

```
A: Track B final in the default field
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
hero         300  6.785 0.329    45    7   15   17   14    2    0    0   51.7    87     0     0     15    154  11529    4148
trackb       300  5.821 0.280    17   30   12   17   18    5    0    0   66.3   135     0     0     21    260  12436    4140
tag          300  5.697 0.260    16   25   25   16   12    4    1    1   72.7    13     0     0      4     31   8622     152
nit          300  5.036 0.189     3   24   33   24   12    4    0    0   90.7     9     0     0      1      6   5123     288
naive 3.811, allin 1.883, maniac 1.637, station 1.330.   300 tables, 50185 hands in 15.2s

B: Track B step-1 cheap bot in the same field
hero         300  7.151 0.313    51    9   12   15   11    2    0    0   43.0    79     0     0     15    133   9709    4048
tag          300  5.762 0.263    18   26   18   20   12    3    1    1   66.7    19     0     0      3     31   4477      78
trackb1      300  5.448 0.264    11   27   23   15   14    8    1    1   69.7    61     0     0     12    120  10851     420
nit          300  5.004 0.199    ...

C: reference field without us (random in our seat)
hero 7.330 ± 0.292, tag 6.137, nit 5.589, naive 4.256, random 2.551, allin 2.353, maniac 2.060, station 1.723

D: Track B final in the 'realistic' field (replacing naive)
hero                   300  5.560 0.391    34    8   14    8    9   13    6    7   55.0   105     0     0     20    154  15355    1275
trackb                 300  5.006 0.315    12   26   14   13   15    9    6    5   66.7   222     0     0     36    411  12207    5967
tag                    300  4.909 0.289    11   23   22   13   10   11    6    4   69.7    29     0     0      4     34  11003     269
loose_aggro            300  4.878 0.383    25   14    8   12    9   10   11   10   62.7    19     0     0      3     26   8030     354
pushfold               300  4.554 0.301    12   15   18   20   12    9    6    7   75.3    27     0     0      5     43   8035    3946
montecarlo 2.580, montecarlo30 2.275, timeout_then_recover 2.239.   57055 hands in 104.9s

E: Track B final in the 'strong' field (replacing one pushfold)
hero_loose    300  4.852 0.383    25   12   10   12    9   11   14    7   64.7    87     0     0     18    119  15836     473
hero          300  4.816 0.387    26   11   10    9   10   14   11   10   62.7    84     0     0     17    117  19004     164
tag           300  4.190 0.290     4   20   16   17   14   13    6    9   76.0    21     0     0      5     32  11151      61
hero_tight    300  4.006 0.338    13   13   11    9   16   16   12   10   77.7    68     0     0     17    108  16043     181
trackb        300  3.879 0.343    10   16   12    9   11   14   13   14   77.0   254     0     0     54    493  28306    5761
pushfold      300  3.577 0.308     7   12   15   16   10   10   16   15   80.3    33     0     0      6     41   8032      72
loose_aggro 3.443, nit 3.236.   57999 hands in 174.3s
```

Reading the lines: the final Track B bot never crashed and never played an illegal action in roughly 1,500 tables
(165,000 engine hands). It finishes **second to Hero** in the default and realistic fields, at or just above the
repo's chart TAG (5.82 vs 5.70; 5.01 vs 4.91, both inside the ±0.3 intervals), and **fifth of eight** in the strong
field, below all three Hero variants and TAG but above `pushfold`, `loose_aggro` and `nit`. It wins tables far
less often than Hero (p1 17% vs 45% in A) and lives on second and third places, which is what a tight,
ICM-gated bot with no postflop aggression does under a 10/7/5 table. The step-1 cheap bot scores 5.45 in the same
seat; steps 2–3 added +0.37 points, about 40 percent of the cheap bot's gap to TAG-plus-Hero. Its timing profile
is the weak spot: p50 21–54 µs and p99 260–493 µs against Hero's 15–20 / 117–154, and 1.5–3× Hero's timeouts in
strict mode; the extra cost is the per-decision profile flags over eight seats and the ICM evaluations on all-in
decisions.

## Judgment: competitive, or just legal?

**Legal: yes, with 55 minutes to spare.** The cheap bot passed the kit runner at minute 4 and stayed clean through
4,420 kit decisions and 165,000 engine hands; the from-scratch spec's step 1 is sufficient for legality even with
a dozen guesses in it, because the safe wrapper and the clamp are the first two things it asks for.

**Competitive: mid-field, not Hero.** Evidence: in 20 minutes the spec produced a bot that beats every non-Hero
bestiary bot in the default and realistic fields and is statistically level with the repo's TAG, and finishes
fifth of eight when three Hero variants are at the table. The gap to Hero is 0.5–1.0 points on a 32-point table
(roughly 10–15 percent of score) and it is structural: Hero's edges in an SNG are a solved push/fold chart by
stack depth, flop-strength tables, bet sizing, and a profiler fed by showdowns, none of which the spec contains.
The 40 unused minutes would not close it by following the spec's text, because the text is exhausted at minute 19;
they would close part of it only if the spec grew a step 3b (the push/fold chart, which is a 15-minute solve from
the equity table already built) and a step 2b that moves the profile flags to once per hand (the timing tail).
The step-1 → step-4 delta of +0.37 points also says where the spec's own value sits: most of the hour's score is
in the cheap bot's tight ranges and the ICM gate, not in the profiler, whose flags barely fire against the kit and
fire wrongly when they do (kit A's biased log).

So Track B is a real fallback, not a substitute: if the organizers forbid prepared code, this spec reliably yields
a legal bot by minute 5 and a TAG-strength bot by minute 20 on the first attempt, with one deviation (sample
count) and 34 recorded guesses, none of which needed a human. Whether that is enough depends on the room. Against
the "realistic" field it is second; against a room of prepared Hero-class bots it is fifth.

## Repo and protocol findings (not prompt problems)

1. **The fake kits are not self-contained.** `fakekits/_table.py` imports `hyperion.core.cards`, `.eval` and
   `.types`, so a blank-directory drill cannot copy a kit verbatim without handing the agent the real evaluator.
   Give `_table.py` its own tiny deck and a brute-force showdown evaluator (the operator stub is 60 lines) and
   drop the three imports; the kits then work from any directory, which is also what a real starter kit does.
2. **Kit A starves a profiler.** `hand_over(hand_number, chip_change)` carries no history and no showdown, and
   `action_log` stops at our own decision, so a seat's folds are mostly unobserved while its raises always are.
   The kit's rock was flagged "maniac" (16 raises in 18 observed actions) after 200 hands. Check what the real
   kit exposes at hand end before relying on the step-2 flags; if it is like kit A, the maniac and nit flags need
   per-hand (not per-action) counting and a higher observation floor.
3. **Timing tails on this box are the box.** A 1.99 ms and a 4.04 ms spike appeared in two kit-runner runs and a
   4.3 ms max in one 10k loop, on 4–7 µs means. GC A/B (default / `gc.freeze()` / `gc.disable()`, 3 × 20k calls
   each) showed zero gen-2 collections and the same 180–620 µs maxima in every mode. Same conclusion as drills 1
   and 2: the spec's "max under 500 µs" is not a usable criterion on a loaded machine.
4. **Python 3.12 is faster than the spec assumes.** The spec budgets "a few seconds" for the 6/7-card evaluator
   build (0.17 s) and 5 s for 400-sample equities (0.55 s). The slack should be spent on samples (below).
5. The RTK shell hook reformats `diff` output, so `diff a b | grep -c '^[<>]'` reported 0 for files that differ;
   use `difflib` or `rtk proxy diff` when a diff is measured in a drill.
6. The sim wrapper used for the comparison (`operator/simcompare.py` in scratch) is the inverse of
   `KitAAdapter`: `Observation` → kit-A `GameState`. If Track B drills continue, it belongs in
   `hyperion/drills/` so a from-scratch bot can always be scored against the bestiary.

## Questions the agent would have needed a human to answer

None were asked. The 34 guesses are itemised in `NIGHT.md` (scratch). The ones that change play, and which a
human might have answered differently:

1. (step 1) "playable only from the last three seats before the blinds" → button, cutoff, hijack; 4-handed that
   leaves the button only.
2. (step 1) "call a bet with top pair or better or with 8+ outs when the bet is under a third of pot" → the size
   clause binds the draw only; top pair calls any size.
3. (step 1) "plus any ace, any king with a suited or T+ kicker, and any pair when under 8 big blinds" → the
   "under 8" governs the whole list (any pair is already playable).
4. (step 2) "shove anything when [a dead seat] must act after us and faces a bet" → only when every unfolded
   opponent is flagged dead, because a raise reopens the action for all of them.
5. (step 3) "top 15 percent" → of 1,326 combos, ranked by heads-up equity.
6. (step 3) "computed once per hand at hand start, never per decision" versus "before any all-in decision
   compare the ICM value of fold versus ... win and lose" → fold value at the first act of the hand, win/lose
   values at the all-in decision.
7. (step 3) "before any all-in decision" → calls of a shove and re-shoves over a raise, not open shoves (gating
   an open shove as if always called turns push/fold into fold/fold).
8. (step 3) 400 samples → 2,000 (JJ > QQ, 99 > TT and A3o inside the top 12% at 400). This is the one place the
   agent knowingly departed from the spec's number, inside the spec's own 5 s cap.
9. (step 4) "one rank step" → one class, about 1% of combos.
10. (prompt 02) "under 150 lines" → total lines after collapsing blank runs (148); non-blank was 130 throughout.

## Where the spec or a prompt was ambiguous, insufficient to write the code without guessing, or wrong for Track B

### track-b-from-scratch.md, step 1
1. "playable only from the last three seats before the blinds" names no seats. **Edit:** "from the button,
   cutoff and hijack (the three seats acting last before the small blind); with fewer than six players dealt,
   the button only."
2. "Under 12 big blinds effective" never defines effective. **Edit:** "effective stack = min(your stack, the
   largest stack still in the hand), in big blinds."
3. "Call a shove" never defines a shove, nor "the shover is short". **Edit:** "a shove is a raise that puts the
   raiser all-in or is at least 10 bb; short means the shover started the hand under 12 bb."
4. "plus any ace, any king with a suited or T+ kicker, and any pair when under 8 big blinds" is ambiguous and
   "any pair" is already playable. **Edit:** "under 8 bb also push any ace and any king with a suited or T+ kicker."
5. Facing a raise that is not a shove while under 12 bb is not covered. **Edit:** add "facing a raise under
   12 bb, re-shove with premium, otherwise fold."
6. The postflop call sentence has two readings. **Edit:** "call any bet with top pair or better; call with 8+
   outs only when the bet is under a third of the pot (pot including the bet); otherwise fold."
7. "top pair", "8+ outs" and "pot" (with or without this street's bets) are undefined; three of the agent's
   guesses. **Edit:** "top pair = a hole card pairing the highest board card or a pocket pair above the board;
   outs = 9 for a flush draw, 8 for an open-ended straight draw, flop and turn only; bet sizes are fractions of
   the pot before this street's bets."
8. "Run the kit simulator 50 hands. Zero errors. Submit." plus prompt 02's "folds, calls and raises at least once
   each": the tight list produced no CALL in 100 hands on seed 1 (drill 1 saw the same). **Edit (02 step 5):**
   "fold, check and raise each at least once over 100 hands; a call is not required."

### track-b-from-scratch.md, step 2
9. The evaluator paragraph is exact and buildable as written (the one paragraph of the spec that needed no
   guess). Its cost estimate is 20× pessimistic on 3.12 (0.17 s). **Edit:** "about 0.2 s on Python 3.12."
10. "Update from the action history each decision" assumes a complete history. Kit A exposes the log only up to
    our decision and nothing at hand end, which biases every counter toward raises. **Edit:** "If the kit gives no
    end-of-hand history, count at most one observation per seat per hand per counter and double the observation
    floors; the maniac flag then needs 20 hands, not 10 actions."
11. "raise rate" is not one of the four counters the prior sentence defines. **Edit:** "raise rate = raises over
    all observed actions, no prior."
12. "dead seat = folded to every bet it faced but checked when checked to, 5 observations" does not say whether a
    raise ever disqualifies it. **Edit:** "five bets faced, all folded, at least one free check, and no raise ever."
13. "Against a dead seat, shove anything when it must act after us and faces a bet" is unsafe as written because a
    raise reopens the action for everyone. **Edit:** "only when every unfolded opponent is flagged dead."
14. "top pair good kicker" and "wait for the river with medium hands" are undefined. **Edit:** "kicker T or better;
    medium = top pair with a worse kicker, which checks until the river and then bets 75 percent."
15. Nothing says what the evaluator replaces in the step-1 decision path (it replaces nothing until step 3).
    **Edit:** "Use it for the made-hand category now; its real consumer is step 3."

### track-b-from-scratch.md, step 3
16. "top 15 percent" (and every other percentage) does not say of what. **Edit:** "percent of the 1,326 two-card
    combos (pairs 6, suited 4, offsuit 12), ranked by heads-up equity."
17. "early seats, middle, button" are not mapped to seats, and the blinds are not placed. **Edit:** "button =
    BTN and CO; middle = the two seats before them and the SB when folded to; early = the rest; the BB opens the
    early range over limpers and otherwise checks."
18. "defend the big blind with the top 35 percent versus one raise" leaves every other facing-a-raise case to the
    step-1 premium list, silently. **Edit:** "every other call of a raise keeps step 1's premium list."
19. "8 to 12 top 25 from early seats and top 45 from the button" has no middle value and may or may not apply to
    the shallower bands. **Edit:** "under 8 bb from any seat; 8 to 12 bb: 25 early, 35 middle, 45 button."
20. "400 samples each" is too few: SE 2.4 percent per class gave JJ > QQ, 99 > TT, A3o inside the top 12 percent.
    **Edit:** "2,000 samples each (about 3 s on 3.12); drop to 400 only if import must stay under one second."
21. "memoized, computed once per hand at hand start, never per decision" contradicts "before any all-in decision
    compare the ICM value of fold versus the equity-weighted ICM value of win and lose", whose stacks depend on the
    opponent and the amount. **Edit:** "compute the fold value at the first decision of the hand and the win and
    lose values at the all-in decision; one Malmuth-Harville evaluation over 8 stacks is about 50 µs."
22. "Before any all-in decision" gates open shoves, which have fold equity, and would fold almost all of them.
    **Edit:** "before calling an all-in or re-shoving over a raise; never gate an open shove."
23. Kit A has no hand-start callback. **Edit:** "'hand start' means our first decision of the hand, which the kit
    times; keep it under 100 µs."
24. The spec never says which equity (vs 1 or vs 3) feeds the gate. **Edit:** "vs 1 when one opponent is all-in,
    vs 3 when two or more have money in."

### track-b-from-scratch.md, step 4 and verification
25. Step 4 points at prompt 05, which assumes the 300-table sim; Track B has no simulator with points, so "show
    that hero's points did not drop" cannot be run. **Edit:** "Track B: apply the patch, re-run the kit runner for
    legality, record the patch as unverified, and keep the pre-patch zip as the fallback."
26. Prompt 05's payoff section names Track A code ("a `bounty_bonus` term in `Spot`") and an undefined "one rank
    step". **Edit:** "add the bonus to the dead money in every all-in comparison and to the pot in pot-odds; one
    rank step = one class, about 1 percent of combos."
27. "Mean must be under 100 µs and max under 500 µs before anything is submitted" fails on lone spikes on any
    loaded machine (drills 1–3). **Edit:** "mean under 100 µs and p99 under 300 µs; report the max and ignore a
    lone spike on a sub-10 µs mean."
28. "a timing loop that calls the decision function 10,000 times on a fixed state" never exercises the first act
    of a hand or an all-in decision, the two expensive paths. **Edit:** "include one state per hand number and one
    shove-call state."

### 00-briefing, 01-rule-sheet, 02-adapter-and-cheap-bot, README
29. 00: "if I do not give one, we build from scratch" worked; nothing to change. 01: the "any bounty or side
    payoff" line caught the variant in one minute; add "say whether the kit's local dealer implements each
    non-standard rule" so the discovery is required rather than incidental.
30. 02 step 6 "Run our test suite" has no suite in Track B. **Edit (Track B section):** "write `test_bot.py` with
    the card parser (ten is two characters), the hand lists and one legal-action check; keep it green from here."
31. 02 step 4 ("vendor `hyperion/` and `tables/`") and step 1 ("read `hyperion/drills/adapter.py`") are Track A
    text that the Track B section inherits by "do steps 1 to 7". **Edit:** "Track B: steps 1 and 4 are 'one file,
    no vendoring'."
32. The README timeline is Track A only (tables at 0:17, Hero at 0:25). **Edit:** add a Track B row: "0:15 cheap
    bot, 0:30 evaluator + profiler, 0:45 equity + ICM, 0:50 submit, 0:55 freeze", and note that this drill hit
    them at 4 / 9 / 17 / 19.

## Environment notes
- Another session's work ran on the same 8-core box throughout (load 5.5–8.4); error counts are unaffected,
  every latency tail is contaminated, and strict-mode points in the sim comparison carry the usual timeout noise.
- Scratch venv: `uv venv .venv --python 3.12` (3.12.12) + pytest 9.2.0. The agent's bot has no third-party imports.
- The real repo was not modified except for this report.

## Appendix: the operator's rules text as pasted to the agent

```
SEQUOIA POKER BOT NIGHT -- OFFICIAL RULES, FINAL (issued 19:30)

1. THE GAME
   Tonight is no-limit Texas Hold'em. Standard 52-card deck, standard hand rankings, two hole
   cards per player, five community cards dealt flop / turn / river, best five-card hand from any
   combination of your two cards and the board. No wild cards, no rank changes, one board, no
   discards or swaps. If you have played hold'em you know the cards. The twist is in section 4.

2. TABLE FORMAT
   Eight (8) players per table, sit-and-go. Every player starts with 2,000 chips. A table ends
   when seven players have busted OR after hand 200, whichever comes first. Your bot is
   instantiated once per table and told its seat; it may keep memory between hands at that
   table. Nothing persists between tables.

3. BLINDS
   Blinds rise every 25 hands and stay at the last level until the cap:
       Level 1  hands   1-25     10 /  20
       Level 2  hands  26-50     15 /  30
       Level 3  hands  51-75     25 /  50
       Level 4  hands  76-100    50 / 100
       Level 5  hands 101-125    75 / 150
       Level 6  hands 126-150   100 / 200
       Level 7  hands 151-175   150 / 300
       Level 8  hands 176-200   200 / 400
   No antes, no straddles. Betting is no-limit. The minimum raise is the size of the last raise
   this street, or one big blind if there has been none. Raise amounts are expressed as the
   TOTAL you are raising to this street, not the increment.

4. THE LUCKY SEVEN BOUNTY
   Whenever a hand goes to showdown and the player who wins the pot is holding at least one
   Seven (7c, 7d, 7h or 7s) among their two hole cards, the house adds 50 chips to that player's
   stack immediately after the pot is awarded. The bonus is paid by the house, not by the other
   players, and is paid in addition to the pot. A pot won without a showdown (everyone else
   folded) earns no bonus. If a showdown pot is split, every winner holding a Seven receives the
   full 50. When there are side pots, the bonus is paid at most once per hand per player, to each
   player who won any pot (main or side) at that showdown while holding a Seven. Bonus chips are
   ordinary chips for every purpose: blinds, all-ins, and ICM at the cap. Over a table the chips
   in play therefore grow.

5. SCORING
   Points are awarded by finishing position at each table:
       1st 10    2nd 7    3rd 5    4th 4    5th 3    6th 2    7th 1    8th 0
   If the table reaches the 200-hand cap with more than one player alive, the points still on the
   table for the unfilled positions are split among the survivors by ICM (Malmuth-Harville) on
   their chip counts after hand 200, bonus chips included. Players who busted keep the points for
   the position they busted in. Two players who bust on the same hand are ordered by chips at the
   start of that hand; ties split the points. Your tournament score is your average points over
   all tables you play (we expect about 10,000).

6. YOUR BOT
   Python 3. Implement `class Agent` as shown in the starter kit's `kit.py`: `new_game(my_index,
   n_players, starting_stack)`, `act(state) -> str`, `hand_over(hand_number, chip_change)`. The
   state object and the action strings are documented in `kit.py`. One millisecond of wall clock
   per `act` call, measured around the call. An exception, an illegal action or a slow reply is
   scored as a fold (a check when a check is legal) and is counted against you. Standard library
   only; you may also import the kit's own `kit` module. No network, no threads, no subprocesses.

7. SUBMISSION
   Upload a single zip under 100 MB through the portal. The zip must contain `submission.py` at
   its top level defining `class Agent`; the server imports it from the directory the zip unpacks
   into, so other files in the zip may be imported relative to that directory. You may resubmit as
   often as you like until the freeze; the last accepted upload plays.
```
