# Prompt drill 4 — kit D (MIT-shaped socket skeleton, 8 seats), variant "Six-Plus Hold'em" (short deck; strength axis)

Date 2026-10-31, T0 06:20:45 EDT. Same protocol as drills 1–3 (`drills/log/prompt-drill-1-kitB-permuted.md`,
`docs/drills/prompt-drill-2-kitC-payoff.md`, `docs/drills/prompt-drill-3-trackB-kitA-bounty.md`): operator and agent
were the same model in strictly separated roles; the agent saw only the prompts, the operator's one-page rules text
(appendix), the kit path and the files the prompts name. New this time: the repo was sourced from its **committed
state only** (`git archive HEAD` at `1e564b51761378cf0e3e46451680de030bc55fce`), because the working tree carried
other agents' uncommitted strategy edits; by the time the drill ended HEAD had moved to `cb10472` with a different
set of uncommitted edits (drill 2's protocol finding 4 for the third time; the archive made it irrelevant here).
Scratch: `/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/drill4/` with
`hyperion/` (the agent's copy: `NIGHT.md`, `submission/`, `dist/`, `frozen/T1.zip`, `rules_tonight.json`,
`tables_shortdeck_rejected/`), `pristine/` (an untouched copy for baselines), `rejected/` (pristine plus the
regenerated tables) and `operator/` (rules text, `clock.log`, every sim and latency output, the shipped zip). Venv:
`uv venv .venv && uv pip install -e ".[dev]"` (Python 3.12.12; 379 tests). The box carried other sessions' work
until about minute 20 (load 6.5–11.3 on 8 cores) and went quiet after (1.9–3.6), which splits every latency and
timeout figure below into "in the drill" and "re-checked after".

Hidden variant: the catalog's `short_deck`. Deuces through fives removed (36 cards), a flush beats a full house,
A-6-7-8-9 is a straight; everything else the standard 8-max SNG (2,000 chips, 10/20 rising every 25 hands over
eight levels, 200-hand cap) with points 10/7/5/4/3/2/1/0 and ICM at the cap. The payouts differ from the repo's
8..1 placeholder on purpose, as the real table will. Kit D is the socket skeleton: `class Player(Bot)` with
`handle_new_round` / `get_action` / `handle_round_over`, namedtuple states, `legal_actions()` returning a set of
classes with `FoldAction` absent when a check is free, raise-to totals, no pot field, a pooled game clock charged on
every round trip including the acks, launched as `python submission.py <port>`. The agent was told that the kit is
`kit.py` and `runner.py` and that `RUBRIC.md` is not part of it; it never read the rubric. `CONTRACTS.md` names
`hyperion/drills/adapter.py`, so the reference `KitDAdapter` was in bounds (as `KitBAdapter` and `KitCAdapter`
were in drills 1 and 2); the agent subclassed it unchanged.

## Key numbers

Minutes are floor(mm:ss after T0), as in the earlier reports; the exact offsets are in brackets.

| Score | Result | Target |
|---|---|---|
| First legal upload-ready package (kit D runner PASS over the socket, 0 exc, 0 illegal, conformance 0 violations, `pack.py` sha256) | **minute 6** [06:11]: runner PASS at 04:50, suite green at 05:50, zip at 06:11; sha256 `80fc8caef0a95785d1458e7e8cf0cab293f1d0b9a3225beaf205ad46d9f686c4`, 213 KB, import 0.30 s | 15 (hard fail 20) |
| Hero wired, strict sim meeting prompt 04's gate (Hero within its own CI of the Stage 0 number) | **minute 13** [13:31] against the Stage 0 number as the playbook writes it (5.316 inside [4.747, 5.471]); the prompt's parenthetical "re-measured with `--rules`" number 5.485 was missed by 0.014; the printed timeout rate (0.375%) failed its 0.3% line on a box at load 10.8, where the untouched Hero shows 0.36% in the same game. Hero zip at **minute 16** [16:05], sha256 `14947f38c966197518299c559db5c7a97e93c7b9904793d82225583cdf8b8988`, import 0.38 s. Re-checked after the drill on the quiet box: `hero 300 5.321 0.373 ... tmo 0 exc 0 ill 0 p99 39`, every criterion met | 40 |
| Prompt 03 regenerated tables for short deck | **yes**: `gen_tables` 48.2 s on 7 workers (its own `--variant-check` projected 194 s), 81 classes, pass check at minute 8 [08:43]. **But the loader silently rejected the result** (found at minute 11 [11:03], repo finding 1); the old tables were restored at minute 12 [12:32] | 0:17–0:25 |
| Prompt 05 short-deck patch | **not shippable as written**: none of its three bullets has a `Config` key (repo finding 2). The catalog's own Config patch was measured instead: `postflop.value_tier` 3 gives 4.982 vs 5.064 before on paired seeds (measure mode), `preflop.open_frac_default` 0.14 changes nothing (5.064 = 5.064). Reverted; override `{}` | points did not drop |
| Hero's final points, `--variant short_deck --field realistic --tables 300 --seed 11` (strict, default mode) | shipped bot **5.276 ± 0.252, 3rd** (tag 5.793, pushfold 5.518, loose_aggro 4.525); untouched copy **5.278 ± 0.250, 3rd** (tag 5.787, pushfold 5.509); tmo 1 vs 0, exc 0, ill 0, p99 34 vs 36 µs. The shipped bot is code-identical to the untouched one (default Config, byte-identical tables), so the difference is one timeout | |
| Same command, Hero on the regenerated-then-rejected tables (what prompt 03 would have shipped unnoticed) | 5.242 ± 0.248, 3rd | |
| Reference, Stage 0 (untouched, default rules): | `hero 300 5.316 0.242` (4th: tag 5.583, pushfold 5.532, loose_aggro 5.380); with tonight's payouts on the standard deck `hero 300 5.485 0.357` (1st: tag 5.447) | |
| Agent questions needing a human | **1** asked (patch the table loader, or restore the old tables?); 11 ambiguities resolved conservatively (below) | 0 |
| Things we had to undo | none in the submission; the prompt-03 tables were restored by the agent itself. One operator error: the first NIGHT.md write failed (shell without the venv) and cost 47 s on prompt 01's clock | |
| Agent role ended | minute 20 [20:44] | 60 |

Net effect of the hour on points: zero by construction, again. Stage 3 produced tables the code cannot use; Stage 5
has no knob for the axis it names; the shipped Hero is the default Hero with `rules_tonight.json`. What the hour did
buy: a legal socket bot at minute 6, the right payouts in the ICM curve, and the discovery that the repo's short-deck
support ends at the generator.

The two Hero gate lines (prompt 04 step 2, strict, `--field realistic --variant short_deck --rules rules_tonight.json`):
```
Stage 0 (Verifier, untouched copy, default rules, 06:17):
hero                   300  5.316 0.242    22   13   16   14   13   10    8    5   68.3     8     0     0     16     52  11713      62
Stage 0 re-measured with tonight's payouts, standard deck (Verifier, untouched copy, 06:19):
hero                   300  5.485 0.357    25   18   13   12   11    8    8    4   61.7    14     0     0     17     66   7338      79
Agent, minute 13 [13:31], load 10.8:
hero                   300  5.109 0.362    22   14   15   13   13   11    8    5   76.7   130     0     0     16    159  29092    7177
300 tables, 34666 hands in 56.9s: 610 hands/s.
Untouched copy, same game and load (Verifier, 06:31):
hero                   300  5.157 0.369    23   14   10   17   13    9    8    6   75.7   125     0     0     16    142  25717    8085
Agent's bot re-run after the drill, load 1.9:
hero                   300  5.321 0.373    26   14    9   16   13    9    7    6   72.7     0     0     0     13     39    314      54
```
Rotate 40 (minute 14): hero 5.011 ± 0.334, 3rd of 8 (tag 5.556, pushfold 5.374): not last. Latency under the
prompt's generator load (minute 15): bot p99 58.8 µs, adapter round trip p99 181.2 µs, exit 0, but over 1 ms 9
(0.45%) and 12 (0.60%) with gc 0/0/0 and wall 71 ms against cpu 36 ms, i.e. preemption; without the generator
(minute 16): p99 52.8 / 83.4 µs, over 1 ms 2 (0.10%) / 1 (0.05%). Default Config kept.

## Timeline (minute at which each prompt's pass check was met)

| Prompt | Minute | Notes |
|---|---|---|
| 00 briefing | 0 [00:23] | restated in one paragraph; read PLAYBOOK §3/4/7, CHALLENGE.md, CONTRACTS.md and nothing else |
| 01 rule sheet | 3 [03:36] | axis = strength; FIT VERDICT: evaluator KEEP with caveat (cannot order flush over full house or see A6789), preflop tables and push/fold REGENERATE, rest KEEP; payouts to `Rules.payouts`; found that `--rules` alone scores showdowns in hold'em order and that `--variant short_deck --rules rules_tonight.json` is needed for the hooks; kit dealer plays 52 cards (legality only). First write failed at 02:49 (operator shell error), landed at 03:36 |
| 02 adapter + cheap bot | 4 [04:50] runner, 5 [05:50] tests, 6 [06:11] zip | `TonightAdapter(KitDAdapter)` unchanged plus a six-line rules loader; entry warms a throwaway adapter at import because kit D has no table-start hook; runner 50 hands 65 decisions 0/0/0 max 0.432 ms, conformance 0 violations, fold 29 check 22 call 0 raise 14; 379 tests; zip `80fc8cae…86c4` |
| 03 tables | 8 [08:43] | `--variant-check` 194 s projected, 48.2 s actual; 81 classes, AA 0.7435 / 76o 0.3232 heads-up, no 2–5 classes, fingerprint match, AA raises preflop and bets K96, 86o folds, kit runner PASS. All of it on files the loader then ignored |
| 04 wire Hero | 13 [13:31] gate, 16 [16:05] zip | minute 9–11: kit runner 100 hands PASS; `tables.load().source == "built"` found; question asked; old tables restored from the minute-6 package; flop decision through the adapter (AhKh on Qh9h6c -> CheckAction, cards remapped correctly, pot 0 because a lone RoundState carries none); strict sim, rotate, latency with a hand-written kit D native builder, pack |
| 05 strength patch | 20 [20:03] | before 5.064 ± 0.360 (measure); catalog patch 4.982; `value_tier` alone 4.982; `open_frac_default` alone 5.064; reverted; override `{}`; NIGHT.md closed at 20:44 |

## How the short deck was handled

1. **Rule sheet (minute 3).** Quoted the three rule changes, kept `rank_order` as the identity (the surviving ranks
   keep their order), put `removed_ranks [0,1,2,3]` plus the catalog's `category_order` and `low_straight` keys in
   `extras`, and wrote the ENGINE line: nothing is unrepresentable by `Rules` field, but `--rules` alone deals 36
   cards and scores a flush under a full house; the catalog's `ShortDeckHooks` fix the showdown, so every sim line
   runs with `--variant short_deck --rules rules_tonight.json`. Hero's own strength reads keep hold'em order;
   caption "Hero's reads minus flush>full house and A6789". Most dangerous thing: the pooled clock charged on every
   round trip, which turns one slow first call into folds for the rest of the table.
2. **Prompt 03 (minute 6–8).** Regeneration ran clean and every printed check passed: 81 classes, sane equities, a
   matching push/fold fingerprint, sensible decisions, kit runner PASS. None of those checks reads what Hero
   actually loaded.
3. **Prompt 04 (minute 9–12).** `make_bot()` in a fresh process took 4.0 s where the cheap bot's import had taken
   0.3 s. Reading the loader explained it: `tables.load()` requires all 169 hold'em classes and otherwise builds
   60-sample standard tables at load (`hyperion/strategy/tables.py:157–158`), and the heads-up matrix likewise
   (`:165–173`, 40 samples); the generator's push/fold solve goes through the same loader
   (`tools/gen_tables.py:138`), so `pushfold_hu.json` was solved from the built standard matrix, which is why its
   fingerprint "matched". Confirmed by `tables.load(need_hu=True).source == "built"`, `'22' in t.equity`, and
   `t.equity['AA'][0] == 0.8167` against the file's 0.7435. The agent asked its one question (patch the loader to
   accept a subset, with an unverified effect on a push/fold solver that hard-codes 1,326 combos, or restore the old
   tables per prompt 03's fail branch); the operator answered restore, per the playbook's Stage 3 "if it fails"
   row. Tables came back from `dist/submission/tables/` (byte-identical to the originals, verified by sha256) and
   `source == "disk"`, load 0.25 s. Hero then ran as a hold'em bot on a short-deck game, which is what the untouched
   repo also does.
4. **Prompt 05 (minute 17–20).** The prompt's short-deck bullets (lower the flush value tier, raise the straight
   tier, change the draw multiplier) map onto nothing: `postflop.read` assigns tier 6 to a straight, 7 to a flush
   and a full house, 8 to quads, in code; `act` computes `draw_eq = outs * (4 if two cards to come else 2) / 100`;
   there is one `postflop.value_tier` for every category. The agent read the catalog entry the prompt points at and
   measured its documented `config_patch` as the only Config-expressible short-deck change: a drop. Reverted.

## Repo and protocol findings (not prompt problems)

1. **Short-deck regeneration is a silent no-op that degrades Hero.** `tables.load()` rejects any equity file missing
   one of the 169 classes and any heads-up matrix whose class list is not the full 169, and builds coarse standard
   tables instead (`hyperion/strategy/tables.py:157–158, 165–173`). `tools/gen_tables.py` honours `removed_ranks`
   and writes 81-class files, then solves push/fold through the same loader (`:138`), so the solve is from the
   built standard matrix and the fingerprint check in prompt 03 step 5 passes vacuously. The catalog labels
   `short_deck` tables "approximate"; they are unused. Nothing printed by prompt 03 shows it; `Tables.source` does.
   Fixes, smallest first: (a) prompt 03 prints `source` and stops on `built`; (b) the loader accepts a subset when
   `meta.json`'s rules carry `removed_ranks`, filling absent classes with zero equity and rank 0 and the matrix with
   0.5, **and** the push/fold solver derives its class list and `TOTAL_COMBOS` (hard-coded 1326 at `tables.py:26`)
   from the rules; (c) a `tests/` case that regenerates with `removed_ranks` into a temp dir and asserts
   `load(...).source == "disk"` and `len(equity) == 81`. Side effect worth knowing: the fallback build takes 3.5–4.8 s
   under load, which is most of `pack.py`'s 5 s import budget and lands inside the socket's 10 s connect window.
2. **The strength-axis patch has no knobs.** One `postflop.value_tier` for all categories; category tiers and the
   2x/4x draw rule are literals in `postflop.py`. If the short-deck patch is to exist, add `postflop.flush_tier_shift`,
   `postflop.straight_tier_shift` and `postflop.draw_outs_mult` (defaults 0, 0, 1.0), or delete the bullets.
3. **`preflop.open_frac_default` is inert in the realistic field.** 0.14 vs 0.10 gave identical 300-table results
   (5.064 = 5.064, same finish histogram), so `open_frac` must cover every position the sim reaches. The catalog's
   `config_patch` for short deck and the signal table's "lower `preflop.open_frac_default`" row both lean on it.
4. **`tools/latency.py` has no kit D native builder** (`--native` offers `kit_a | kit_b | kit_c`), and prompt 04 says
   "fake kits: `--native kit_b`". The agent wrote `submission/native_kit_d.py` (12 lines). A lone `RoundState` has no
   `previous_state`, so the adapter sees pot 0 unless `round_total` is set; harmless for latency, misleading for the
   step-2 "one flop decision through the adapter" print.
5. **Timeout gates versus load, fourth drill running.** In the drill the printed rate was 0.375% (gate 0.3%) at
   load 10.8 with the untouched Hero at 0.36% in the same game, `tag` timing out 26 times on a 3 µs median, and the
   latency tool at 0.45–0.60% over 1 ms with the prompt's own generator running; on the quiet box the same bot
   shows 0 timeouts in 30,950 hands and 0.05–0.10% over 1 ms. The playbook's §6 note (measure mode for points,
   strict for counts) is right; the prompt-04 and latency gates still need a load clause (edits below).
6. **Kit D's runner keeps only the last 400 characters of the bot's stderr.** The conformance report fit tonight (two
   lines); a report with violations (up to five examples per rule) would be truncated. Print the full stderr, or
   have `maybe_checked` write the report to `HYPERION_CHECK_OUT` when set.
7. **Sourcing from `git archive HEAD` worked** and should be the protocol: the real repo's HEAD moved from
   `1e564b5` to `cb10472` during the drill and its uncommitted strategy edits changed; the drill never saw either.
8. The packaged entry runs over the socket from `dist/submission/` (PASS, 83 decisions 0/0/0, imports `hyperion`
   from the package in 0.19 s), but the kit D runner puts the repo root on `PYTHONPATH`, so this is not a clean
   isolation test; `pack.py`'s fresh-process import check is.
9. Stale text: kit D's RUBRIC says wiring kit D into `hyperion/drills/run.py` "takes two edits"; both are already in
   (`KITS = ("a","b","c","d")`, the `kit == "d"` branch).
10. `gen_tables --variant-check` over-projects by about 4x on Python 3.12 (194 s projected, 48 s measured, 7 workers
    at load 8–11). Fine as a conservative bound, but say so, or the 5-minute box triggers `--skip-matrix` needlessly.

## Questions the agent would have needed a human to answer

1. (04, asked) The regenerated tables were rejected by the loader; patch the loader inside the 5-minute rule or
   restore the old tables per prompt 03's fail branch? Answered: restore.

Resolved conservatively without asking (each is a prompt defect below):

2. (01) Is a point table that differs from the placeholder a moved payoff axis? Took N: carried by `Rules.payouts`,
   prompt 05's payoff section says override `{}`.
3. (01) The NIGHT template wants the Stage 0 number at minute 0; nothing before prompt 04 uses it. Left a note for
   the Verifier; filled at prompt 04 with both numbers the operator gave.
4. (02) `pack.py --extra submission/adapter.py` does not carry `rules_tonight.json`, which the adapter loads from
   beside the entry. Added it as a second `--extra`.
5. (02) Kit D has no per-table hook and the first `G` packet is charged; "warmed at module import" was read as
   "start a throwaway adapter on a dummy seat at import so every cache is hot".
6. (03) Step 6 "copy the new tables into `submission/`" is obsolete: `pack.py` vendors `tables/` at pack time. Skipped
   the copy, re-ran the kit simulator.
7. (04) Which Stage 0 number is the gate, 5.316 (default rules) or 5.485 (re-measured with tonight's payouts), and
   on which Hero should the re-measurement run when the agent's own copy already has regenerated tables? Recorded
   both, called the gate met on the playbook's wording and missed by 0.014 on the prompt's.
8. (04) Timeout rate 0.375% against 0.3% at load 10.8. Judged the box (untouched Hero 0.36%, tag 26, latency tool
   clean without the generator); kept the default Config rather than `use_profiler=False`.
9. (04) `--native kit_b` for a kit D adapter. Wrote the builder.
10. (04) `/tmp/load` for the generator: used the session's scratch directory instead, per the environment's rule.
11. (05) No Config key for any short-deck bullet. Measured the catalog's documented `config_patch` as the nearest
    Config-expressible patch rather than editing `postflop.py`; reverted on a drop.
12. (05) "did not drop": point estimate on paired seeds in measure mode (playbook §6), not the strict line.

## Where a prompt was ambiguous, wrong for this kit or variant, named something the repo lacks, or wasted time

### 00-briefing
Nothing new. The "Format" bullet's numbers matched tonight's rules; the drill-2 edit (rules text overrides them) is
still worth applying for the night when they do not.

### 01-rule-sheet
1. The FIT VERDICT has no way to say "REGENERATE, but the code cannot consume the result". **Edit (preflop-tables
   line):** "if the deck loses ranks, write REGENERATE (loader must accept <169 classes; check `tables.load().source`
   after prompt 03)".
2. "Payoff moved? (... non-standard points)" invites a Y for every real point table. **Edit:** "a point table that
   differs from our placeholder is not a moved axis: write it in the ASSUMPTION DIFF, carry it in `Rules.payouts`."
3. The Stage 0 line is asked for at minute 0 and needed at prompt 04, re-measured. **Edit (template header):** "Stage
   0 known-good number: the Verifier writes the hero line here before T0 and, while Stage 2 runs, re-measures it on
   the untouched repo with `--rules rules_tonight.json` (and `--variant <name>` if the catalog has hooks)."

### 02-adapter-and-cheap-bot
1. Step 6's `--extra submission/adapter.py` omits the rules file. **Edit:** "`--extra submission/adapter.py
   submission/rules_tonight.json`".
2. Step 2's "warmed at module import" does not cover a kit with no table-start hook and a charged first packet.
   **Edit:** "if the kit has no per-table hook, construct and `start()` a throwaway adapter at import so the
   tables, push/fold and evaluator caches are hot before the first packet."
3. Step 4's "fold, check-or-call and raise each at least once" passed (call 0, check 22), as in drills 1–3; fine.

### 03-tables
1. **Step 3's `tables.load()` "succeeds" is satisfied by the fallback and is the check that let the hour's biggest
   failure through.** **Edit:** "print `tables.load(need_hu=True).source` and `len(t.equity)`; `source` must be
   `disk` and the class count must match the generator's log; `built` means the loader rejected the new tables and
   Hero is on 60-sample standard tables: stop, restore, and say so."
2. Step 5's fingerprint check passes when both sides come from the same fallback. **Edit:** "also compare
   `t.equity['AA'][0]` with the value in `tables/preflop_equity.json`."
3. Step 6's "Copy the new `tables/` into `submission/`" is obsolete. **Edit:** "nothing to copy: `pack.py` vendors
   `tables/` when it builds the zip; re-run the kit simulator for 50 hands."
4. `--variant-check` projects about 4x long on 3.12. **Edit (step 2):** "the projection is conservative by about 4x;
   pass `--skip-matrix` only if it projects over 20 minutes."

### 04-wire-hero
1. Step 2's command has no `--variant`, so a catalog twist with hooks (short deck's showdown order) is scored wrong
   under `--rules` alone. **Edit:** "`... --rules rules_tonight.json` plus `--variant <catalog name>` whenever
   `python -m hyperion.drills.variants --list` has an entry with hooks for tonight's twist."
2. The gate's "(re-measured with `--rules` if payouts or schedule changed)" names no one and no copy. **Edit:** "the
   Verifier's re-measured number from the NIGHT.md header is the gate; if it is missing, use the plain Stage 0
   number and say so."
3. "tmo under 0.3% of hands as printed" fails on a loaded laptop for every bot. **Edit:** "if hero's rate exceeds
   0.3%, read tag's and `uptime`: tag also timing out with load above the core count is the box, record it and go
   on; otherwise `Config.use_profiler=False` and re-run."
4. Step 3 "not last among tag, nit, hero": nit is not in the realistic field. **Edit:** "not last among the chart
   bots in the field (tag, pushfold)."
5. Step 4's "fake kits: `--native kit_b`" is wrong for kit D and the real kit. **Edit:** "fake kits a/b/c: `--native
   kit_<x>`; kit D or the real kit: write `build(obs) -> native` (12 lines; `submission/native_kit_d.py` from drill 4
   is the template) and pass `module:build`."
6. Step 4's generator load pushes the over-1 ms count past 0.3% on a box that is already loaded. **Edit:** "run the
   generator only if `uptime` is under one per core; otherwise record the load and run `latency.py` alone."
7. Step 2's "print one Hero flop decision through the adapter" shows pot 0 for kit D because a lone `RoundState`
   has no history. **Edit:** "build the state from a round start (or set the adapter's `round_total`) so the pot is
   right, and print the Observation's hole, board, pot and legal set beside the reply."
8. `/tmp/load` is a system path; the agent used the scratch directory. **Edit:** "`--out <scratch>/load`".

### 05-variant-patch (strength section, short deck bullets)
1. The three short-deck bullets name knobs that do not exist (repo finding 2). **Edit (until the knobs exist):**
   "Short deck: Config has one `postflop.value_tier` for every category and no draw multiplier; the only expressible
   change is `postflop.value_tier` 3 (the catalog's patch); measure it in `--mode measure` on the same seed, expect
   about −0.1, and ship `{}` unless it wins by more than half its CI." **Or** add the three keys and keep the text.
2. "about 2.4x outs instead of 2x" is the wrong number and "drop" the wrong direction: in a 36-card deck an out is
   worth about 3.2% per card. **Edit:** "raise the draw multiplier to about 3.2x per card to come."
3. "Tables were regenerated in prompt 03" assumes success. **Edit:** "if prompt 03 ended on its restore branch,
   caption every line 'Hero on hold'em tables' and expect the patch to do nothing."
4. "show that hero's points did not drop" is still the strict line in the text; the playbook's §6 says measure
   mode. Drill 2's edit (measure mode, same seed, half-CI rule) is still unapplied. Apply it.

### README / PLAYBOOK
- The playbook's Stage 3 text ("the generator re-solves push/fold from the new matrix and the loader verifies the
  fingerprint, which closed the bug drill 1 found") is true for 169-class variants and false for short deck; add
  "the loader accepts only full 169-class tables (drill 4)" until repo finding 1 is fixed.
- The axis table's "short deck shifts flush/straight thresholds" promises a patch the Config cannot express.
- Targets: drills 2 and 4 both had the Hero package by minute 16 or earlier and the agent idle by minute 20; the
  budget's slack is spent entirely on the first failure, as it should be. This drill is the first in which a
  stage's own pass checks all passed while the stage had failed; the edits above add the one print that catches it.

## Environment notes
- Other sessions' work ran on the same 8-core box until about minute 20 (load 6.5–11.3), then stopped (1.9–3.6 by
  the scoring runs). Error counts are unaffected; every in-drill latency tail and timeout count is contaminated, and
  the after-drill re-checks are quoted beside them.
- Scratch venv: `uv venv .venv && uv pip install -e ".[dev]"` (Python 3.12.12); 379 tests pass at minute 5.
- One operator error: a shell without the venv active made the first NIGHT.md write fail; 47 s added to prompt 01.
  Protocol: every operator command sources the venv.
- The real repo was not modified except for this report.

## Appendix: the operator's rules text as pasted to the agent

```
SEQUOIA POKER BOT NIGHT -- OFFICIAL RULES, FINAL (issued 19:35)

1. THE GAME
   Tonight is no-limit SIX-PLUS HOLD'EM, also called short deck. The deck has 36 cards: every
   deuce, three, four and five has been removed, so the ranks in play are 6, 7, 8, 9, T, J, Q, K, A
   in the usual four suits. Two hole cards per player, five community cards dealt flop / turn /
   river, best five-card hand from any combination of your two cards and the board. No must-use-two
   rule, no wild cards, one board, no discards or swaps.
   Hand rankings are hold'em rankings with ONE change: a FLUSH BEATS A FULL HOUSE. From the top:
   straight flush, four of a kind, flush, full house, straight, three of a kind, two pair, one pair,
   high card. Within a category, hands compare as in hold'em (higher ranks win; the ace is high).
   Because the five is gone, the ace also plays LOW to make the bottom straight: A-6-7-8-9 is a
   straight (and A-6-7-8-9 suited is a straight flush), ranking below 6-7-8-9-T. A-K-Q-J-T remains
   the highest straight. There is no other wheel.

2. TABLE FORMAT
   Eight (8) players per table, sit-and-go. Every player starts with 2,000 chips. A table ends when
   seven players have busted OR after hand 200, whichever comes first. Your bot is launched once per
   table as its own process and told its seat; it may keep memory between hands at that table.
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
   this street, or one big blind if there has been none. Raise amounts are expressed as the TOTAL
   you are raising to this street, not the increment.

4. SCORING
   Points are awarded by finishing position at each table:
       1st 10    2nd 7    3rd 5    4th 4    5th 3    6th 2    7th 1    8th 0
   If the table reaches the 200-hand cap with more than one player alive, the points still on the
   table for the unfilled positions are split among the survivors by ICM (Malmuth-Harville) on
   their chip counts after hand 200. Players who busted keep the points for the position they
   busted in. Two players who bust on the same hand are ordered by chips at the start of that hand;
   ties split the points. Your tournament score is your average points over all tables you play
   (we expect about 10,000).

5. YOUR BOT
   Python 3. Subclass the `Bot` class in the starter kit's `kit.py` as `Player` and implement
   `handle_new_round`, `get_action` and `handle_round_over`; the kit's `run_bot` and `parse_args`
   connect you to the engine on the port the engine passes on the command line. Card strings,
   state objects, the legal-action set and the action classes are documented in `kit.py`; the
   engine's packet protocol is in the same file and in `runner.py`. Your clock is POOLED over the
   whole table: budget roughly one millisecond per decision, charged by wall-clock round trip; the
   T clause of every packet tells you what is left. A single reply slower than 2 seconds marks the
   bot dead, and a bot whose clock runs out folds every remaining decision. An illegal action is
   played as a fold (a check when a check is free) and counted against you. Standard library only;
   you may also import the kit's own `kit` module. No network, no threads, no subprocesses.

6. SUBMISSION
   Upload a single zip under 100 MB through the portal. The zip must contain `submission.py` at
   its top level; the server runs `python submission.py <port>` from the directory the zip unpacks
   into, so other files in the zip may be imported relative to that directory. Connect within 10
   seconds of launch. You may resubmit as often as you like until the freeze; the last accepted
   upload plays.
```
