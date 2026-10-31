# Prompt drill 5 — Track B (blank directory), spec v2, kit B (`decide(observation: dict) -> dict`, raise increments), variant `permuted_ranks` seed 0 (strength axis)

Date 2026-10-31, T0 07:43:29 EDT, repo HEAD `d4a744f99f3f9bf25b6bee74a44e70fc5729f508` at T0 (the working tree
carried uncommitted edits to `hyperion/strategy/*` and `tables/`). Another session committed three times during
the drill (`60362d5` 08:04:15, `1724258` 08:05:52, `9744f94` 08:09:12; 23 files, strategy and tables included), so
the `git archive HEAD` taken at 08:09:0x for the sim comparison is **`1724258`** (verified file by file: it has
that commit's `PLAYBOOK.md` and `docs/decisions.md`, not `9744f94`'s `HANDOFF.md`); "Hero" below is Hero at
`1724258`. The agent role was unaffected because it never read the repo (drill 2's protocol finding 4 again). Same protocol as drill 3 (`docs/drills/prompt-drill-3-trackB-kitA-bounty.md`): operator and
agent were the same model in strictly separated roles; the agent saw only prompts 00, 01 (with the operator's
rules text, appendix), the full text of `docs/prompts/track-b-from-scratch.md` **v2**, prompt 02's Track B
paragraph, and the kit copied into scratch. It never read, imported or grepped `/home/connor/dev/hyperion`.
Scratch: `/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/drill5/`
with `kit/fakekit/` (the copied kit), `bot/` (`submission.py`, per-step copies `submission_step{1,2,2b,3,3b}.py`,
`test_bot.py`, `bench.py`, `mix.py`, `NIGHT.md`, `rules_tonight.json`), `submissions/` (five hashed zips) and
`operator/` (rules text, prompts as pasted, clock log, `simcompare.py`, sim outputs, the `git archive` copy).
Venv: `uv venv .venv --python 3.12` (3.12.12) + pytest 9.2.0. The box was quiet this time (load 0.3–2.1 on 8
cores), unlike drills 1–3.

Hidden variant: the catalog's `permuted_ranks(seed=0)`: `rank_order = [1,10,9,5,11,2,3,7,8,4,0,12,6]`, i.e.
printed ranks ordered weakest to strongest `Q 2 7 8 J 5 A 9 T 4 3 6 K`; straights follow the new order (wheel =
printed K-Q-2-7-8); everything else standard 8-max SNG with points 10/7/5/4/3/2/1/0 and ICM at the cap. Kit B
shows printed ranks as ints 2..14 and expresses raises as increments. The kit's dealer settles showdowns in the
standard order; the agent had to find that out.

Kit set-up note (operator). The fake kits are now self-contained (`fakekits/_eval.py`, drill 3 finding 1):
`kit_b/` plus `_table.py`, `_eval.py` and a one-line `__init__.py` were copied to `scratch/kit/fakekit/`, verified
with `python -I -S` that the package imports with `hyperion` absent, and smoke-tested with a fold bot. The only
edits: `hyperion.drills.fakekits` -> `fakekit` in `runner.py` and `RUBRIC.md`, and three prose mentions of the
framework removed from `_table.py`/`_eval.py` docstrings. `RUBRIC.md`'s "Ours" column still names repo types
(`Action.raise_to`, `Bot.new_table`); the agent did not use them.

## Key numbers

| Score | Result | Drill 3 (v1, kit A) | Target |
|---|---|---|---|
| Step 0+1: legal cheap bot, kit runner PASS, tests green, zip hashed | **minute 7** (07:50:59) | 4 | 15 |
| Step 2: evaluator + profiler + exploits, runner PASS, zip | **minute 12** (07:56:23) | 9 | 30 |
| Step 2b: flags once per hand, bench re-run, zip | **minute 13** (07:57:05) | n/a | 33 |
| Step 3: equity table + charts + ICM curve + gate, runner PASS, zip | **minute 20** (08:03:31) | 17 | 45 |
| Step 3b: third column + push rule (inert by its own sanity clause), zip | **minute 23** (08:06:27) | n/a | 50 |
| Step 4: variant patch | **minute 24**, no-op (strength axis = step 0's remap) | 19 | if time |
| Agent role ended | minute 24 (spec exhausted; final verification done) | 20 | 60 |
| Final kit-runner line, `--hands 50 --seed 1` | `PASS: 50 hands, 45 decisions, 0 timeouts, 0 exceptions, 0 illegal, delta -1560, mean 0.016 ms, max 0.054 ms` | | 0 exc, 0 illegal |
| Long legality runs, final bot, `--hands 2000` seeds 11/12/13 | 1,772 + 1,378 + 1,499 = **4,649 decisions, 0 exceptions, 0 illegal, 0 timeouts** (max 0.085 / 0.061 / 0.206 ms); `--hands 500 --budget-ms 0.5`: 364 decisions 0/0/0 | 4,420 dec, 2 timeouts | |
| The spec's timing loop (`bench.py`, 2,000 calls rotating mid-hand / new hand / all-in call at 8 players), final bot, three runs | **over 1 ms: 0 / 0 / 0 (0.00 %)**; **p99 44.8 / 48.5 / 47.4 µs**; mean 13.7–14.1 µs, p50 12.2–12.4 µs, max 107–215 µs. Over the whole drill the only >1 ms calls were two at step 1 (0.10 %) and one at step 2 (0.05 %) | mean 4–5 µs, max 0.6–1.2 ms | < 0.3 % over 1 ms, p99 < 500 µs |
| Import time of the final bot, fresh process, other directory | **1.22–1.36 s** (evaluator 0.07 s, 169 × 2,000-sample table 0.93 s, 3b column 0.28 s) | 2.9–3.8 s | < 5 s |
| Lines of code written | `submission.py` **908** (794 non-blank; 327 after step 1, 606 after 2, 827 after 3, 908 after 3b); `test_bot.py` 203, `bench.py` 95, `mix.py` 35: **1,241 lines**, plus `NIGHT.md` 238 | 620 + 253 | |
| Human questions needed | **0 asked**; 38 ambiguities resolved by a recorded guess (step 0: 2, step 1: 16, step 2: 8, step 3: 8, step 3b: 4) | 0 / 34 | 0 |
| Rank remap applied correctly (operator, from the zipped file, 8 players, 100 bb, unraised) | **yes**: printed KK (= AA tonight) raises from UTG, MP and BTN; printed Q5o (= 72o tonight) folds from all three; printed AA (= 88) raises, printed 72o (= 32o) folds. Agent's own tests cover the table, the wheel (K-Q-2-7-8) and "T-J-Q-K-A is not a straight" | | |
| Kit dealer does not implement the scramble: discovered | yes, minute 1, in the rule sheet (`_eval.classify5` orders by raw rank) | | |
| Things we had to undo | none; three of the agent's own bugs caught by its own tests before a zip (65s bound, two profiler gaps) | | |
| Track B final vs the bestiary in the real sim, 300 tables strict seed 11, seed-0 permutation, payouts 10/7/5/4/3/2/1/0 (operator, after the drill) | realistic field **5.049 ± 0.291, 3rd of 8** (hero 6.020, rival1 5.130, pushfold 4.085, loose_aggro 4.024, tag 3.756); default field **6.366 ± 0.299, 2nd** (hero 6.972, tag 5.136, nit 4.945). exc 0, ill 0, **tmo 0** in both; p99 54–66 µs vs hero's 36–43 | 5.006 2nd / 5.821 2nd; tmo 135–254 | "not last" |
| Step-1 cheap bot in the same realistic seat | **4.691 ± 0.251, 3rd** (hero 6.234, rival1 5.161, tag 3.996); steps 2–3b are worth **+0.36** | +0.37 | |
| Reference: realistic field without us | hero 6.235, rival1 5.690, tag 4.410, loose_aggro 4.354, pushfold 4.275 | | |

Timeline (wall-clock minute at which each pass check was met):

| Prompt / step | Minute | Notes |
|---|---|---|
| 00 briefing | 0 | restated in one paragraph; "no repo path given" branch taken |
| 01 rule sheet | 1 | strength axis; `REMAP = [1,10,9,5,11,2,3,7,8,4,0,12,6]`; kit dealer plays the standard order, 4 seats, 6 levels, no 200-hand end; no history anywhere in kit B; raises are increments and `by` below the minimum is illegal, not clamped |
| Step 0 + 1 + prompt 02 (Track B) | 7 | 327 lines; runner 50 hands 103 decisions 0/0/0; own test caught `lo >= 4` for "65s+" (five is strength 3; drill 3 made the same slip); mix over 100 hands F66 C49 R38 + 4 calls; bench p99 27.6 µs, 2/2,000 over 1 ms; zip `3f248e61…b966b` |
| Step 2 | 12 | evaluator 7,462 classes, NF 73,775 keys, FL 4,719, built in 0.05–0.07 s, verified against brute force on 3,000 random 7-card hands; snapshot-diff profiler (kit B has no history); own test caught two profiler gaps (folds across a street boundary; my own raise never recorded as the bet faced); zip `e10d6693…a793` |
| Step 2b | 13 | flags dict rebuilt on a new hand number only; bench p99 71/82 µs; zip `ea98ab9a…eaf5` |
| Step 3 | 20 | 169 × (vs 1, vs 3) from one 2,000-sample deal per class in 0.93 s; percentile charts; exact Malmuth-Harville by subset DP, 43 µs at 8 players, curve 0.16 ms in `on_table_start`/`on_hand_end`; gate on shove calls and re-shoves; zip `aa440513…6123` |
| Step 3b | 23 | third column (1,000 samples vs the top 12 %) in 0.28 s; **the spec's own sanity check fails** (22 from the button at 10 bb: push EV 3.861 < V(S + 0.1 bb) 4.019), so `USE_3B = False` and step 3's percentiles stay, as the clause orders; zip `106509a1…a5c2` (final) |
| Step 4 | 24 | strength-only variant: nothing beyond step 0's remap; no zip; step 3's zip recorded as the fallback |

## How the rank remap was handled

1. **Rule sheet (minute 1).** Wrote the printed-to-strength table as a 0-based 13-entry list, quoted the straight
   rule, stated that after the remap the game is standard hold'em in strength space (wheel = strengths 12,0,1,2,3
   = printed K,Q,2,7,8), and found that the kit's dealer does not implement it ("the runner says PASS either way;
   every hand list, equity table and straight test must live in strength space, and only our own unit tests can
   prove the mapping" — named the most dangerous thing in the rules).
2. **Step 0 (inside the step-1 window).** `parse_card` maps the kit's `{"rank": 2..14, "suit": "H"}` (and, for the
   spec's test, `"Th"`/`"10h"`) through `REMAP` to `strength*4 + suit`; every later line of the bot is in strength
   space, including the hand lists ("99+" = strength pair 7+), the evaluator, the equity table and the charts.
   `test_bot.py` asserts the permutation, that printed KK is the best pair and printed AA is not premium, that
   printed K-Q-2-7-8 is a straight and printed T-J-Q-K-A is not, and that a printed-Six-high flush beats a
   printed-Ace-high flush.
3. **Steps 2–3b** needed nothing variant-specific: because the remap sits at parse time, the evaluator is the
   standard one and the equity table is computed in strength space (AA 0.853 vs 1, 72o 0.343).
4. **Step 4** was a no-op and the agent said so. Operator verification from the zipped file confirmed the remap in
   play (table above). Right behaviour throughout; v2's step 0 did exactly what it was added for, at no visible
   time cost.

## Sim comparison (operator role, untimed, after the agent role ended)

Wrapper `operator/simcompare.py` (the inverse of `KitBAdapter`: engine `Observation` -> kit B observation dict with
printed ranks `(c >> 2) + 2`, decision dict -> `Action`, `new_table` -> `on_table_start`, `hand_end` ->
`on_hand_end({"hand_id", "delta"})`), bots registered as `trackb` (final) and `trackb1` (step 1), run from the
`git archive HEAD` copy with the repo venv. **The permutation was passed explicitly** as
`Rules(rank_order=seed-0 perm, payouts=(10,7,5,4,3,2,1,0))` with `variant=variants.get("permuted_ranks", seed=0)`:
the sim CLI's `--variant permuted_ranks --seed 11` would have re-derived the permutation from seed 11 and tested
the bot under the wrong scramble (protocol finding 1). Realistic field at HEAD is
`hero, montecarlo30, montecarlo, pushfold, loose_aggro, rival1, tag, timeout_then_recover`; ours replaced the last.

```
D: Track B final in the realistic field | tables 300 seed 11 strict
bot              n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
hero           300  6.020 0.368    36   12   12   10   11    9    7    2   54.0     0     0     0     20     43    300      63
rival1         300  5.130 0.391    29   11    8   10   11   15   12    5   66.3     0     0     0     24     55    919     147
trackb         300  5.049 0.291    10   25   17   17   13    9    6    2   70.7     0     0     0     29     66    616      81
pushfold       300  4.085 0.282     7   14   19   17   16   11    8    8   82.7     0     0     0      4     12    126      22
loose_aggro    300  4.024 0.337    11   17   11   10   14   11   15   11   78.3     0     0     0      3      9    483      18
tag            300  3.756 0.250     2   13   20   23   12   10   10    9   91.3     0     0     0      4     10    368      24
montecarlo 2.098, montecarlo30 1.840.   55761 hands in 63.8s

D1: Track B step-1 cheap bot in the same seat
hero           300  6.234 0.389    41   13    8    7    9   12    5    4   48.7     1     0     0     20     50   3400      64
rival1         300  5.161 0.383    28   14    6   10   14   13   10    6   64.7     2     0     0     24     64   1094     231
trackb1        300  4.691 0.251     3   24   29   14   12   11    4    3   79.0     1     0     0     19     55   1110     751
pushfold 4.077, loose_aggro 4.028, tag 3.996, montecarlo30 1.971, montecarlo 1.841.

C: reference realistic field without us (timeout_then_recover in our seat)
hero 6.235 ± 0.369, rival1 5.690, tag 4.410, loose_aggro 4.354, pushfold 4.275, timeout_then_recover 2.549,
montecarlo30 2.248, montecarlo 2.240.

A: Track B final in the default field (trackb,hero,tag,nit,station,maniac,naive,allin)
hero         300  6.972 0.310    46   11   15   15   10    2    0    0   49.3     0     0     0     15     36    226      66
trackb       300  6.366 0.299    26   28   14   12   14    6    0    0   57.3     0     0     0     21     54    395     142
tag          300  5.136 0.232     6   26   26   21   14    4    1    1   84.0     0     0     0      3      8    221      29
nit          300  4.945 0.205     4   22   27   28   13    5    0    0   88.3     0     0     0      1      4     52      27
naive 3.207, allin 2.133, maniac 1.750, station 1.490.   48115 hands in 12.3s
```

Reading the lines. The final bot played about 104,000 engine hands over 600 tables with **no exception, no illegal
action and no strict-mode timeout** (drill 3's bot had 135–254 timeouts per 300 tables on a loaded box; this box
was quiet, and the kit-B bot's p99 of 54–66 µs is also lower than drill 3's 260–493 µs because the profiler is a
per-seat snapshot diff rather than a history scan). It finishes **second to Hero** in the default field and
**third** in the realistic field, 0.08 behind the repo's new `rival1` (inside both intervals) and 0.97 behind
Hero. The step-1 bot in the same seat scores 4.69; steps 2–3b add +0.36, the same increment drill 3 measured
(+0.37), and again it comes from the ICM gate and the chart ranges, not the profiler, whose flags barely fire.

**Caveat on the yardstick.** Only Hero remaps through `Rules.rank_order` (`hyperion/strategy/hero.py` lines
354–355); `tag`, `nit`, `pushfold`, `loose_aggro` and the Monte Carlo bots have no remap, so under this variant
they play printed ranks and are crippled (tag busts 91 % in D against 70–73 % in drill 3). "Level with tag" is
therefore a soft bar tonight; `rival1` (5.13 with us at the table, 5.69 without) is the honest comparison, and the
bot is level with it. Against Hero the gap is the same tier as drill 3: −0.6 in the default field, −1.0 in the
realistic field.

## Judgment: competitive, or just legal?

**Legal: yes, with 53 minutes to spare.** The cheap bot passed the kit runner at minute 7 and stayed clean through
4,649 kit decisions and 104,000 engine hands. Step 1 was three minutes slower than drill 3 because kit B has no
position field and no history, so the SB/BB/k derivation and the raiser/shove inference had to be written before
the first legal decision (327 lines against drill 3's 148; prompt 02's "about 150 lines" is a kit-A number).

**Competitive: mid-field, level with the repo's rival, second to Hero.** Spec v2 produced, in 24 minutes and
with no human question, a bot that applies the rank permutation correctly everywhere, beats every non-Hero
bestiary bot in the default field and is statistically level with `rival1` in the realistic one. The gap to Hero
(0.6–1.0 points on a 32-point table) is the same structural gap drill 3 found: no solved push/fold chart by stack
depth, no flop-strength tables, no bet sizing. v2's attempt to close part of it, step 3b, **fails its own sanity
check as written** (below) and therefore ships inert; its fallback clause worked exactly as intended, which is a
point for the spec's structure and against its formula. The remaining 36 minutes could not be spent by following
the text, because the text was exhausted at minute 24.

So Track B v2 is a better fallback than v1 in three measurable ways (zero timeouts and p99 under 70 µs from the
once-per-hand flags and the snapshot profiler; the rank remap handled as a first-class step and verified; the
definitions block removing most of drill 3's step-1 guesses) and the same in strength: TAG-plus in a standard
field, rival-level in the realistic one, fifth-to-third of eight when Hero-class bots are present.

## Repo and protocol findings (not prompt problems)

1. **The sim CLI re-derives `permuted_ranks` from `--seed`.** `hyperion/sim/runner.py` line 297 calls
   `variants.get(a.variant, seed=a.seed)`, so `--variant permuted_ranks --seed 11` plays the seed-11 permutation,
   not the seed-0 one the bot was built for. The comparison therefore had to pass `rules` explicitly. Give the
   CLI a `--variant-seed` (default 0) separate from the table seed, or have `--rules` win when both are given.
2. **Every bestiary bot except Hero ignores `Rules.rank_order`.** Under any rank permutation the field is
   weakened and comparisons against tag/nit mean less (tag 3.76, bust 91 %). Either remap in `bestiary.Bot` base
   `act` (one `remap(obs.hole, rules)` line) or document that strength-axis variants should be scored against
   Hero and `rival1` only.
3. **Kit B exposes no action history and a delta-only hand end.** The spec's profiler text (v2) covers kit A's
   "no history at hand end" but not "no history at all"; the agent diffed consecutive observations. Check what
   the real kit exposes; if it is like kit B, the snapshot-diff rules in defect 8 below are the profiler.
4. The kit's dealer settles showdowns in the standard order, so under a permutation the kit `delta` is noise
   (−10,200 to +59,900 over 2,000 hands here). Already noted in drill 1; a `--rank-order` option on the fake
   dealer would let a Track B agent see one honest number locally.
5. `simcompare.py` (kit B inverse) and drill 3's kit A inverse are now two 90-line operator scripts in scratch.
   They belong in `hyperion/drills/` as `trackb_sim.py --kit a|b` so a from-scratch bot is always scorable.
6. The box was quiet (load 0.3–2.1), so for once the timing numbers are the bot's. Drill 3's conclusion that
   "max under 500 µs" is unusable on a loaded box stands; v2's rate-plus-p99 gate produced no false failure.

## Questions the agent would have needed a human to answer

None were asked. The 38 guesses are itemised in `NIGHT.md` (scratch). The ones that change play and which a human
might have answered differently:

1. (step 1) "open playable from k ≤ 2": the blinds have no k. Guess: the SB counts as k = 2 when folded to, the BB
   never opens playable (checks its option, raises premium over limpers).
2. (step 1) "has shoved three times already": unobservable without history; counted only shoves faced at our own
   decisions, once per hand. Replaced by step 3 anyway.
3. (step 1) an all-in raise smaller than 10 bb is both "a raise that is not a shove" and "a shove": the definition
   won (it is a shove), so 88 folds to a 3 bb all-in.
4. (step 2) with no history, folds across a street boundary are scored against the previous street's last
   snapshot, and the agent's own raise is recorded as the bet the others face. Both were found by its tests.
5. (step 2) station/nit exploits apply only when every active opponent carries the flag.
6. (step 3) the 12/20 percent shove-call ranking is by heads-up equity; only the gate's `e` switches to the vs-3
   column; "money in" = committed more than the big blind or all-in.
7. (step 3) step 1's shove-call list is replaced entirely by top-12 + gate (the spec says "every other call of a
   raise keeps the premium list", which could be read as keeping it).
8. (step 3) the gate is preflop only; postflop all-in calls keep step 1's rule because the spec gives no postflop `e`.
9. (step 3) with a delta-only hand end, the hand-start stack is the stack at the first decision of the hand; a
   walk uses the previous estimate; the kit's silent table restart leaves the curve stale for one hand.
10. (step 3b) "S = effective stack" feeds V(S) even when we cover the table; taken literally.

## Where spec v2 is still ambiguous, insufficient to write the code without guessing, or wrong for this kit

v2 fixed drill 3's defects 1–7, 9, 11–12, 15–19, 21–25, 27–28, 30–32: the definitions block, the rank-remap step,
the kit-A profiler clause, the 2,000 samples, the curve-at-hand-end design, the open-shove exemption, the Track B
step-4 form and the rate-plus-p99 gate all held without a guess. What remains, with one-sentence edits:

### Definitions and step 0
1. "Parse the kit's card strings (a ten may be "10")": kit B gives dicts with int ranks. **Edit:** "Parse the kit's
   card representation (strings with a two-character ten, or dicts with rank 2..14 and a one-letter suit)".
2. "build a 13-entry list REMAP[displayed] = strength": rules tables are usually 1-based. **Edit:** "strength
   0..12 indexed by printed rank 2..A; if the rules number strengths 1..13, subtract one, and assert the list is a
   permutation".
3. "Effective stack ... min(your stack, the largest opponent stack still in the hand)" does not say whether stack
   includes this street's bets. **Edit:** "stack = chips behind plus chips committed this street".

### Step 1
4. "open playable from k ≤ 2" leaves the blinds without a k. **Edit:** "the SB folded to counts as k = 2; the BB
   never opens playable".
5. "77+ and AQ when the shover is short or has shoved three times already" is unobservable without history.
   **Edit:** "drop the three-shoves clause when the kit gives no history".
6. A short stack's all-in under 10 bb satisfies both branches. **Edit:** "an all-in raise of any size is a shove".
7. Prompt 02's "about 150 lines of code" is a kit-A number. **Edit:** "150 lines with a kit that gives position and
   history; about 300 with one that gives neither (kit B)".

### Step 2
8. "Update only from the per-decision history diff ... If the kit gives no history at hand end (kit A ...)" has no
   branch for no history at all. **Edit:** add "If the kit gives no history at all (kit B), diff consecutive
   observations per seat: active -> inactive = fold (facing a bet if the current bet exceeded its committed chips;
   across a street boundary use the previous street's last snapshot); committed up to a new maximum = raise
   (shove if its chips hit zero); up but below the maximum = call; active, nothing committed, acting before you
   with no bet = free check; record your own raise as the bet the others face; apply the kit-A floors."
9. Exploit scope with several opponents is given for dead only. **Edit:** "station and nit exploits apply only when
   every active opponent carries the flag; fold to a raise when the raiser is a nit".
10. "Maniac: call down with top pair, never fold an overpair" is already step 1's call rule. **Edit:** "(no change
    until step 3's 20 percent shove-call)".

### Step 3
11. "Call shoves with the top 12, 20 against a flagged maniac; equity vs 1 ... vs 3" does not say which column ranks
    the 12. **Edit:** "rank by heads-up equity; `e` for the gate is vs 1 when at most one opponent has committed
    more than the big blind or is all-in, else vs 3".
12. "every other call of a raise keeps the premium list" can be read as keeping step 1's shove-call list. **Edit:**
    "the top-12 rule replaces step 1's shove-call list".
13. "win = the pot with every bet and your call" needs the stack convention. **Edit:** "stack = chips + committed;
    win = table.pot + the opponents' committed chips; risk = to_call + your committed chips for a call, your stack
    for a re-shove".
14. "before calling an all-in" has no postflop `e`. **Edit:** "the gate is preflop only; postflop all-in calls keep
    step 1's rule".
15. The curve "from your new stack and the opponents' last-seen chips" needs the hand-start stack. **Edit:** "record
    your stack at your first decision of each hand; if you had none, use the previous estimate plus delta; if the
    kit restarts a table without a start callback, resync from the next observation".

### Step 3b
16. **The sanity check fails as written**, at 8 equal stacks under 10/7/5/4/3/2/1/0 with c = 0.12 per seat and e
    versus the top 12 percent: 22 from the button at 10 bb has p = 0.774, e = 0.406, push EV 3.861 points against
    V(S + 0.1 bb) = 4.019; the rule would push 3.8 percent of combos from the button at 10 bb and 1.4 percent from
    early, versus step 3's 45 and 25. The fallback clause fired and step 3's percentiles stayed, so the five
    minutes bought nothing. **Edit:** either delete step 3b until the formula is re-derived against a known
    push/fold chart, or state the sanity numbers it must hit (button 10 bb: at least 35 percent of combos) so the
    author sees it is a calibration problem, not an implementation one.
17. "S = effective stack" in V(S) misprices spots where you cover the table. **Edit:** "S = your stack; the amount at
    risk is the effective stack".
18. "b = seats behind you", "the value of 0.1 bb" and the per-seat c are undefined in detail. **Edit:** "b = the
    active opponents; c per seat from that seat's flags, p = their product; the 0.1 bb term = V(S + 0.1 bb) − V(S)".

### Step 4, the gate, prompts 01 and 02
19. Step 4 is right for a strength-only variant but does not say so. **Edit:** "Strength-only variant: step 4 is
    done; write that in NIGHT.md and use the time on a step-3 re-check instead".
20. Prompt 01 still lacks drill 3's edit 29. **Edit:** add "say whether the kit's local dealer implements each
    non-standard rule" (the agent found it anyway, but by reading `_eval.py`, which a real kit may not ship).
21. Prompt 02's Track B paragraph says "about 150 lines" and "steps 0 and 1" but the gate's `bench.py` three-state
    loop is described only in the spec. **Edit:** point at "the gate at the end of the spec" rather than restating
    part of it.

## Environment notes
- Box quiet throughout (load 0.3–2.1 on 8 cores); timing numbers are representative for once.
- Scratch venv: `uv venv .venv --python 3.12` (3.12.12) + pytest 9.2.0. The bot imports `random`, `time`,
  `itertools` only.
- The sim comparison used the repo venv (`/home/connor/dev/hyperion/.venv`, 3.12.12) with `PYTHONPATH` on the
  `git archive HEAD` copy; `hyperion.__file__` was checked to resolve to the archive.
- The real repo was not modified except for this report.

## Appendix: the operator's rules text as pasted to the agent

```
SEQUOIA POKER BOT NIGHT -- OFFICIAL RULES, FINAL (issued 19:30)

1. THE GAME
   Tonight is no-limit Texas Hold'em with one change: the ranks are scrambled (section 4).
   Standard 52-card deck of thirteen printed ranks in four suits, two hole cards per player, five
   community cards dealt flop / turn / river, best five-card hand from any combination of your
   two cards and the board. No wild cards, one board, no discards or swaps. The hand categories
   are the usual nine (high card, pair, two pair, three of a kind, straight, flush, full house,
   four of a kind, straight flush) in the usual order. What changes is which rank beats which.

2. TABLE FORMAT
   Eight (8) players per table, sit-and-go. Every player starts with 2,000 chips. A table ends
   when seven players have busted OR after hand 200, whichever comes first. Your module is
   imported once per table and told its seat; it may keep memory between hands at that table.
   Nothing persists between tables.

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
   this street, or one big blind if there has been none. A raise is expressed as the INCREMENT
   above the current highest bet ("raise by"), not as a total; the starter kit does the same.

4. THE SCRAMBLE
   The cards keep their printed faces. Tonight's strength order of the thirteen ranks, from the
   WEAKEST to the STRONGEST, is:

       Q  2  7  8  J  5  A  9  T  4  3  6  K

   The same thing as a table (strength 1 = weakest, 13 = strongest):

       Printed rank:         2    3    4    5    6    7    8    9    T    J    Q    K    A
       Tonight's strength:   2   11   10    6   12    3    4    8    9    5    1   13    7

   Every comparison that depends on rank uses tonight's strength: a pair of Kings is the best
   pair and a pair of Queens the worst; a Six-high flush beats an Ace-high flush; kickers compare
   by strength; three Threes beat three Aces. A straight is five cards CONSECUTIVE IN TONIGHT'S
   ORDER: Q-2-7-8-J is a straight (the second lowest), T-4-3-6-K is the highest straight, and
   T-J-Q-K-A is NOT a straight tonight. As in ordinary hold'em the strongest rank may also play
   as the card below the weakest, so K-Q-2-7-8 is the lowest straight (tonight's "wheel").
   Suits, flushes, pairs, trips, full houses and quads are formed exactly as usual; only the
   ordering of ranks within each category changes. The starter kit and the tournament server show
   you PRINTED ranks as the numbers 2 to 14 (Jack 11, Queen 12, King 13, Ace 14); they never show
   tonight's strength. The conversion is your bot's job. The order above is fixed for the whole
   night and the same at every table.

5. SCORING
   Points are awarded by finishing position at each table:
       1st 10    2nd 7    3rd 5    4th 4    5th 3    6th 2    7th 1    8th 0
   If the table reaches the 200-hand cap with more than one player alive, the points still on the
   table for the unfilled positions are split among the survivors by ICM (Malmuth-Harville) on
   their chip counts after hand 200. Players who busted keep the points for the position they
   busted in. Two players who bust on the same hand are ordered by chips at the start of that
   hand; ties split the points. Your tournament score is your average points over all tables you
   play (we expect about 10,000).

6. YOUR BOT
   Python 3. Your module defines `decide(observation) -> dict` as documented in the starter kit's
   `kit.py`, and may define `on_table_start(info)` and `on_hand_end(info)`. The observation dict,
   the return dict and the raise-by convention are documented in `kit.py`. One millisecond of wall
   clock per `decide` call, measured around the call. An exception, an illegal action or a slow
   reply is scored as a fold (a check when a check is legal) and is counted against you. Standard
   library only; you may also import the kit's own `kit` module. No network, no threads, no
   subprocesses.

7. SUBMISSION
   Upload a single zip under 100 MB through the portal. The zip must contain `submission.py` at
   its top level defining `decide`; the server imports it from the directory the zip unpacks
   into, so other files in the zip may be imported relative to that directory. You may resubmit as
   often as you like until the freeze; the last accepted upload plays.
```
