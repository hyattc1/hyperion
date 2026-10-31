# Prompt drill 2 — kit C (line protocol over stdin/stdout), variant "Top Heavy / Turbo" (payoff + betting axes, with an unsupported ante)

Date 2026-10-31, T0 04:50:18 EDT. Same protocol as drill 1 (`drills/log/prompt-drill-1-kitB-permuted.md`; note the
first report lives under `drills/log/`, not `docs/drills/`). Operator and agent were the same model in strictly
separated roles; the agent saw only the prompts, the operator's one-page rules text (appendix) and the kit path. Work
happened in a scratch copy (`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/drill2/hyperion`,
taken from the working tree at 04:50 with `.git`/`.venv` excluded); `NIGHT.md`, `submission/`, `rules_tonight.json`,
both zips and the sim outputs are there. The box again carried another session's work the whole time (a 6-worker
`tools/sweep.py` plus a rotate sim; load 7.5–8.6 on 8 cores), which shows in every latency tail below.

Hidden variant: standard hold'em cards; 8 players, 1,500 chips, blinds 10/20 → 320/640 in six levels every 20
hands, 150-hand cap; points 50/25/12/6/3/2/1/1 with ICM for survivors at the cap; and an ante of 5% of the big
blind from every player from level 3 on. The engine has no ante concept (`hyperion/sim/engine.py:4` says "no
antes"; `Rules` has no field), which was the deliberate trap.

## Key numbers

| Score | Result | Target |
|---|---|---|
| First legal submission (kit C runner PASS, 0 exc, 0 illegal, zip hashed) | **minute 3** (runner PASS at minute 2; zip + sha256 at 04:53:55) | 15 (hard fail 20) |
| Hero wired, strict 300-table sim meeting every prompt-04 criterion | **minute 4** (04:55:10); Hero zip hashed minute 6 | 40 |
| Hero vs bestiary at end, `--tables 300 --seed 11 --mode strict --rules rules_tonight.json`, default Config | **hero 25.761 ± 2.406 (1st)**, tag 19.900, nit 17.458; exc 0, ill 0, p99 82 µs | |
| Untouched Hero, same seed and Rules | identical code path (the agent changed no strategy code and reverted its own patch); five identical runs in the drill copy gave 25.761 / 25.673 / 25.634 / 25.551 / 25.761. The real repo (now at `ba2d759` plus an uncommitted `preflop.py` edit, different bestiary) gives 25.634 ± 2.403 | |
| Reference: untouched repo, default Rules, seed 11 | hero 6.485, tag 6.449, nit 6.149 | |
| Reference: drill schedule/stack/cap but the linear 8..1 payouts | hero 6.418, tag 6.256, nit 6.110 | |
| Prompt 03 skipped correctly | **yes**, at minute 4, citing its own header | |
| Unsupported ante rule | discovered at minute 1 by grep, stated in the rule sheet, carried through 04 and 05; patch applied via Config, measured, reverted per the prompt; one human question (below) | |
| Agent questions needing a human | **1** asked (ship an ante patch the sim cannot verify?); 6 ambiguities resolved conservatively without asking (below) | 0 |
| Things we had to undo | none | |
| Agent role ended | minute 8 (prompts 00–05 complete, 05 ended with override `{}`) | 60 |

Net effect of the hour on points: zero by construction. The shipped bot is the default Hero with tonight's `Rules`;
the only thing the variant changed is the `Rules` object (payouts, schedule, stack, cap), which prompt 04 wired.
The pool-share view says what that is worth: with the linear table Hero takes 17.8% of a 36-point pool against
tag's 17.4%; with the top-heavy table Hero takes 25.8% of a 100-point pool against tag's 19.9%, because Hero wins
42% of tables outright and tag 13%. The top-heavy table rewards exactly the thing Hero already does.

Prompt-04 sim line (minute 4, 04:55:10):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
hero         300 25.761 2.406    42    7   10   21   14    5    0    0   58.0     9     0     0     13     82   4044     211
tag          300 19.900 1.546    13   37   29   14    5    2    0    1   86.7     1     0     0      3     17   1662      22
300 tables, 28910 hands in 4.4s: 6,522 hands/s.
```
Criteria: exc 0, ill 0, p99 82 < 300 µs, timeouts 9 which is ≤ 0.031% even against the loosest bound of one
decision per hand (the runner still prints hands, not decisions per bot), hero 25.76 ≥ tag 19.90 − 1.55. Rotate
40: hero 24.347 (1st), tag 21.317, nit 17.020. Under generator load (step 4): hero 25.673, tmo 53 (≤ 0.18%), p99
49 µs, max 10.8 ms with tag's 3 µs-median bot showing the same 10.7 ms max, so no Config change. Import from
`/tmp`: 0.22 s. The sim ran the variant minus the ante and said so.

## Timeline (wall-clock minute at which each prompt's pass check was met)

| Prompt | Minute | Notes |
|---|---|---|
| 00 briefing | 0 | restated in one paragraph |
| 01 rule sheet | 1 | axes = payoff + betting structure; ante flagged as unrepresentable (grep: only "no antes" in engine and push/fold docstrings; no `Rules` field; kit dealer posts blinds only) |
| 02 adapter + cheap bot | 2 (runner), 3 (zip) | `KitCAdapter` fits unchanged; subclass hardens `serve` only; 50 hands 84 decisions 0/0/0 max 0.492 ms; 100 hands F92 K58 R13 C2; 197 tests green; `submission_cheap.zip` sha256 `ada4134e…00f63d` |
| 03 tables | skipped at 4 | header gate honoured |
| 04 wire Hero | 4 (12 re-verified under load at 5), zip at 6 | wrote `rules_tonight.json` here because 03 was skipped; flop decision printed canonical cards and `payouts seen by hero: (50, 25, 12, 6, 3, 2, 1, 1)`; `submission_hero.zip` sha256 `7a148182…f96174` |
| 05 payoff + betting patch | 8 | payoff: `{}` (no knob exists; Hero reads payouts); antes: patch tried, reverted; final `{}` |

## How the unsupported ante was handled

1. **Rule sheet (minute 1).** Quoted the ante rule verbatim, classified it under betting structure, and wrote: "Our
   engine has NO ante concept ... So the sim cannot represent the ante and no table or solve accounts for it.
   Prompt 05's betting-structure patch is the only lever; the antes are small (5% bb = 0.4 bb per orbit of 8), so
   the conservative choice if nothing else is to ignore them and say so."
2. **Prompt 04.** `rules_tonight.json` carries everything else; `extras` left empty because nothing reads an ante
   key. Every sim line is captioned "the variant minus the ante".
3. **Prompt 05.** Applied the prompt's ante line through Config: `pushfold.threshold_bb` 12 → 14 and opens one
   position step looser (`open_frac` shifted, `open_frac_default` 0.11). Measured on paired seeds: full patch
   25.340 vs 25.761 (rotate 24.142 vs 24.347); push/fold half alone 25.570; opens half alone 25.834. All inside
   the ±2.4 CI and inside the 0.2-point run-to-run spread, but the sim is structurally blind to the thing the
   patch compensates for, so it can only ever price the patch's cost. The agent reverted per "if the patch makes
   it worse, revert it" and the briefing's conservative rule, shipped the default Config, and asked the one human
   question of the night: ship it anyway? Operator: no.

The prompts handled the trap acceptably but not well: nothing in 01 asks "can our engine represent every rule?",
nothing in 04 covers a partially representable variant, and 05's ante line assumes a verification the simulator
cannot perform. Edits below.

## Repo and protocol findings (not prompt problems)

1. **Strict mode makes Hero's score non-reproducible on a loaded box.** Hero is seeded per table
   (`make_bot(nm, seed=table_seed*64+rot*8+s)`), yet five identical commands gave 25.551–25.761 because strict-mode
   timeouts (9, 18, 18, 29, 53 across runs) are wall-clock events that turn decisions into folds. Any A/B of the
   kind prompt 05 asks for is noise at this size. Either compare in `--mode measure` (same deals, no timeout
   folds) and report strictness separately, or print decisions per bot so a rate can be read.
2. **No antes anywhere.** The README's axis table lists antes under betting structure as handled by "the adapter
   clamps; the Config sizes change; push/fold recomputed", but the engine, `Rules`, the fake kits' dealer and the
   push/fold solve all assume none. Decide before the event: add `Rules.ante` (fraction of bb, from level N) to the
   engine and the solve, or state in the prompts that an ante variant is played unpatched.
3. **The kit C fake dealer's `delta` is not a chip count** even under standard rules (cheap bot −4,090 in 50 hands
   at 2,000 chips with 4 seats; Hero +2,620/+2,407/−2,955/−4,100 across seeds). Drill 1 blamed the permutation;
   it is the dealer. Legality is all the kit sim proves.
4. **The real repo moved under the drill** (commit `ba2d759` and an uncommitted `preflop.py` edit landed after the
   04:50 copy), so "untouched Hero in the real repo" is a different bot from the one the drill started with.
   Protocol fix: record `git rev-parse HEAD` and `git status --short` at T0 in the report header.
5. The drill-1 report path in the brief (`docs/drills/`) and the actual path (`drills/log/`) differ; this report
   is in `docs/drills/` as instructed. Pick one directory and say so in `docs/prompts/README.md`.

## Questions the agent would have needed a human to answer

1. (05, asked) The sim cannot post antes; it can only show the patch's cost without them (−0.4 ± 2.4). Ship the
   ante patch anyway? Answered no.

Resolved conservatively without asking (each is a prompt defect below):

2. (02) Should the cheap-bot adapter carry tonight's `Rules` or the default? Shipped default (same as drill 1 Q3).
3. (04) Prompt 03 writes `rules_tonight.json` and was skipped, yet 04's command needs it and tonight's schedule,
   stack, cap and payouts all differ. Agent wrote it in 04.
4. (04) Kit runner "max decision time under 0.5 ms": 0.506 ms, then 6.06 and 4.91 ms spikes on 0.035 ms medians
   with zero timeouts (load 8). Agent judged OS jitter and changed nothing.
5. (05) "Loosen opens by one step": `open_frac` is a dict of fractions by players behind with no step defined.
   Agent used the information section's "one position step".
6. (05) "Hero's points did not drop" with a ±2.4 CI and 0.2-point run noise: point estimate or interval? Agent
   treated any drop in the point estimate on paired seeds as a drop.
7. (05) Antes start at level 3 but Config is static; a level gate would be a strategy edit. Agent applied the
   patch from hand 1 (and then reverted it).

## Where a prompt was ambiguous, wrong for this kit or variant, named something the repo lacks, or wasted time

### 00-briefing
1. The "Format" bullet hard-codes 2,000 chips, 25-hand levels and a 200-hand cap as hard constraints; tonight's
   rules contradicted all three and the agent had to decide which document wins. **Edit:** "Format as announced in
   advance (the rules text I paste next overrides any of these numbers): eight-player sit-and-go ..."

### 01-rule-sheet
1. The sheet never asks whether our engine can represent each rule, so discovering the ante gap depended on the
   agent's initiative. **Edit (betting line):** "Antes? Straddles? For each betting rule that is not standard, say
   whether `Rules`/the engine has a field for it; if not, write ENGINE CANNOT REPRESENT and what the sim will play
   instead."

### 02-adapter-and-cheap-bot
1. Step 5's "max decision time under 0.5 ms after the first call" still fails to lone spikes (drill 1 proposed the
   edit; it was not applied). **Edit:** "...median under 0.1 ms and at most one decision per 100 over 1 ms; a lone
   multi-millisecond spike on a sub-0.1 ms median is the OS, note it and go on."
2. Nothing says what `Rules` the adapter gets; drill 1 raised it and it recurred. **Edit (step 2):** "Write
   `rules_tonight.json` now from the rule sheet (payouts, schedule, stack, cap, rank_order) and construct the
   adapter with it; prompts 03–05 reuse the file."
3. Step 1 reads as if the adapter must be written; for kit C the reference `KitCAdapter` was exact and the only
   work was hardening `serve`. The drill-1 edit ("subclass unchanged if one fits") was applied and worked; keep it.

### 03-tables
1. The header gate worked. Nothing to change, except that it is the only prompt that creates `rules_tonight.json`
   (see 04.1).

### 04-wire-hero
1. `--rules rules_tonight.json` assumes 03 ran; "omit `--rules` if no rules file was needed" is wrong whenever the
   payoff or betting axis moved without a card axis. **Edit (before step 1):** "If prompt 03 was skipped, write
   `rules_tonight.json` from the rule sheet now; omit `--rules` only when the assumption diff is empty."
2. "If the engine cannot represent the variant, run the standard game and say so" is all-or-nothing; tonight one
   rule of five was missing. **Edit:** "If the engine cannot represent one rule, run everything else under
   `rules_tonight.json`, name the missing rule in NIGHT.md and caption every sim line with it."
3. Step 1's kit-runner "max under 0.5 ms" has the same spike problem as 02.5 (0.506, 6.06, 4.91 ms on 0.035 ms
   medians). Same edit as 02.1.
4. Step 4 says "a second process runs the table generator" without `--out`; the generator's documented default is
   `tables/`, so a tired agent overwrites the real tables mid-drill. **Edit:** "run
   `python tools/gen_tables.py --rules rules_tonight.json --out /tmp/load --workers 4` (never the real `tables/`)
   and kill it when the sim finishes."
5. The timeout-rate check still cannot be computed exactly because the runner prints hands, not decisions per bot
   (drill 1 defect 04.2, half-applied: the prompt now says "compare rates" but the runner did not change). **Edit:**
   add a `calls` column to the runner, or accept "timeouts ≤ 0.3% of hands" as the printed criterion.

### 05-variant-patch (payoff and betting sections)
1. "Top-heavy tables lower the ICM risk premium; flat tables raise it" reads as an instruction but names no knob
   and none exists. **Edit:** "No knob: the ICM curve is built from `Rules.payouts`; confirm by printing
   `hero.core.payouts` after `new_table` and move on."
2. The antes line ("loosen opens by one step and the push/fold depth by 2 bb") assumes the re-run can verify it;
   the engine posts no antes, so the sim can only show the patch's cost and the prompt's own revert rule then
   removes it. **Edit:** "Antes: the engine does not post antes, so the sim cannot judge this patch; apply only
   `pushfold.threshold_bb` +2 bb (the smaller, solver-backed change), record it as unverified, and leave opens
   alone", or add antes to the engine first (repo finding 2).
3. "One step" for opens is undefined. **Edit:** "one step = every `preflop.open_frac` entry and
   `open_frac_default` × 1.15."
4. "Show that hero's points did not drop" is undecidable at 300 tables (±2.4 CI, 0.2-point run noise from strict
   timeouts). **Edit:** "Compare before and after in `--mode measure --rotate --tables 40` on the same seed; call
   it a drop only if the after line is below the before line by more than half its ±95%."
5. Config cannot express "from level 3", so an ante patch applies at 100 bb too. **Edit:** "Patches that apply
   from a level are applied globally; say so, and prefer the push/fold-only change, which only bites under 14 bb."

### README / timeline
- Budgets 0:40 for prompt 05 and 0:50 for the Hero submission; the whole sequence again finished inside 10
  minutes. The slack is real, but the only "if it fails" branch ever exercised across two drills is the revert in
  05. A drill that forces the fallback bot (break Hero on purpose) is still owed.
- The README's axis table promises an ante fix the repo does not have (repo finding 2).

## Environment notes
- Another session's `tools/sweep.py --workers 6` and a rotate sim ran on the same 8-core box throughout (load
  7.5–8.6). Points are affected only through strict-mode timeouts (repo finding 1); error counts are unaffected.
- Scratch venv built with `uv venv .venv && uv pip install -e ".[dev]"` (Python 3.12); 197 tests pass at minute 3.
- The real repo was not modified except for this report.

## Appendix: the operator's rules text as pasted to the agent

```
SEQUOIA POKER BOT NIGHT -- OFFICIAL RULES, FINAL (v3, issued 19:40)

1. THE GAME
   Tonight is Texas Hold'em. Standard 52-card deck, standard hand rankings, two hole cards per
   player, five community cards dealt flop / turn / river. Best five-card hand from any
   combination of your two cards and the board. No wild cards, no rank changes, no extra boards,
   no card exchanges. If you have played hold'em, you know the cards. The twist is in the money.

2. TABLE FORMAT
   Eight (8) players per table, sit-and-go. Every player starts with 1,500 chips.
   A table ends when seven players have busted OR after hand 150, whichever comes first.
   Your bot is launched once per table, as its own process, and may keep memory between hands at
   that table. Nothing persists between tables.

3. BLINDS AND ANTES -- "THE TURBO"
   Blinds rise every 20 hands:
       Level 1  hands   1-20    10 / 20
       Level 2  hands  21-40    20 / 40
       Level 3  hands  41-60    40 / 80
       Level 4  hands  61-80    80 / 160
       Level 5  hands  81-100  160 / 320
       Level 6  hands 101-150  320 / 640  (final level; stays here until the cap)
   Starting at Level 3, every player seated in the hand posts an ante of 5% of the big blind,
   rounded to the nearest chip (4 at 40/80, 8 at 80/160, 16 at 160/320, 32 at 320/640), before
   the cards are dealt. Antes go straight into the pot and do not count toward anyone's bet.
   A player who cannot cover the ante is all-in for whatever they have.
   Betting is no-limit. Minimum raise is the size of the last raise (or one big blind if there
   has been none). Raise amounts are expressed as the TOTAL you are raising to.

4. SCORING -- "TOP HEAVY"
   Points are awarded by finishing position at each table:
       1st  50      2nd  25      3rd  12      4th  6
       5th   3      6th   2      7th   1      8th  1
   If the table reaches the 150-hand cap with more than one player alive, the points still
   on the table for the unfilled positions are split among the survivors by ICM (Malmuth-Harville)
   on their chip counts at the end of hand 150. Players who busted keep the points for the
   position they busted in. A player who busts on the same hand as another is placed by chip count
   at the start of that hand; ties split the points.
   Your tournament score is your average points over all tables you play (we expect ~10,000).

5. YOUR BOT
   Python 3. Talks the line protocol in the starter kit (see kit README). One reply per decision.
   Your clock is pooled: 1 ms per expected decision for the whole table; a reply that takes more
   than 2 seconds marks the bot dead and it folds every remaining hand. Illegal replies and
   crashes are treated as a fold for that decision. Submissions must be a single zip under 100 MB.
   Standard library only, plus whatever the kit itself imports. No network access.

6. SUBMISSION
   Upload a zip through the portal. The zip must contain `submission.py` at its top level; it is
   launched as `python submission.py` from the directory the zip unpacks into. You may resubmit as
   often as you like until the freeze; the last accepted upload plays.
```
