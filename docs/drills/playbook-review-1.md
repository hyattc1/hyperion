# Playbook review 1 (2026-10-31)

Scope: `PLAYBOOK.md` at commit `7e4a797` plus the context packet (`docs/packet/CHALLENGE.md`, `docs/packet/CONTRACTS.md`, the
revised `docs/prompts/00-briefing.md`). Read cold first (confusions recorded before anything else), then prompts 00-06 and
track B, drill 1 (`drills/log/`), drill 2 (`docs/drills/`), the design spec, `docs/decisions.md`, and the rules summary in
`docs/research/notes/.../competition_details.md`. Every command, flag, file, function and Config key the playbook names was
grepped. Four things were measured on this box (8 cores, load 6-8, same contamination as both drills); numbers are at the end.

One-line verdict: the process skeleton is right and drilled, but the Stage 4 gate is failed by the current Hero on the
playbook's own command, the Stage 4 fallback names a bot that cannot be configured, and the prompts the agent actually
executes still carry every drill-2 defect the playbook says it consolidated.

---

## 1. Defects, most dangerous first

Format: the sentence as written; why it is wrong; replacement.

**D1. The Stage 4 gate is failed by the current Hero on the command the playbook names.**
Sentence (Stage 0): "Known-good Hero number written down: `python -m hyperion.sim --tables 300 --seed 11 --mode strict --field
realistic`." and (Stage 4 row): "Hero ≥ tag − CI" on "our strict sim on the realistic field".
Why: measured for this review, that exact command gives tag 5.677 ± 0.197, hero 5.278 ± 0.234 (hero fourth; `decisions.md`
has the same at 1000 tables: 5.30 vs 5.77). Hero is below tag minus either CI. Prompt 04 runs a different command (the soft
bestiary `--bots hero,tag,nit,naive,station,maniac,random,allin`), where hero 6.494 ≥ tag 6.450 passes. So on the night the
Verifier with the playbook fails Hero at 0:40 and the Driver with prompt 04 passes it, and the fallback that then fires does
not exist (D2).
Replacement: "Pass check: kit sim 100 hands clean; strict sim 0 exc, 0 illegal, p99 < 300 µs; Hero within its own ±95% of the
Stage 0 number on the same command and seed. Hero vs tag is not the gate: in the realistic field Hero currently measures
third, and we ship it anyway because it wins 2x the tables (see section 6)." Pick one command for Stage 0, the stage table and
prompt 04, and write it in all three.

**D2. The Stage 4 fallback is a configuration the code cannot express, and its value is unmeasured.**
Sentence: "The fallback is not 'fix Hero.' It is the cheap bot plus the profiler's dead-seat and station flags, which is most
of Hero's edge against this field at a fraction of the surface area."
Why: `pushfold.py:295,334,361` read `if prof is not None and not cheap`, and `preflop.act` returns `_cheap(spot, rank)` with no
profiler argument, so `Config(cheap=True, use_profiler=True)` ignores the flags where it matters. Drill 1 (04.4) asked for the
override dict; nobody answered. "Most of Hero's edge" is asserted: the only measurement (`decisions.md`, strategy layer) says
"no profiler" stayed within ±0.3, and in the realistic field Hero's edge over tag is negative.
Replacement: "The fallback is the Stage 2 submission, `Hero.cheap()`, unchanged. There is no intermediate bot." If an
intermediate bot is wanted, build and measure `cheap + dead-seat exploit` before Nov 6 and name the dict here.

**D3. The prompts the agent executes were not revised after drill 2; the playbook says they were.**
Sentence (section 6): "Drill 2 ... Correctly reverted an unverifiable patch." and (section 0) "Revise it after every drill."
Why: none of drill 2's prompt edits are in `docs/prompts/` (grepped: `/tmp/load`, "rules_tonight.json now", "ENGINE CANNOT
REPRESENT", "one step =", "half its", "No knob", "median under 0.1" all absent). Consequences the agent will hit again:
prompt 04 step 4 runs the generator as load with no `--out`, so it overwrites `tables/` mid-hour (drill 2, 04.4); prompt 04
says "omit `--rules` if no rules file was needed", wrong whenever only payoff or betting moved (04.1); nothing writes
`rules_tonight.json` when Stage 3 is skipped (02.2); prompt 05 still presents an ICM-premium "knob" that does not exist
(05.1); the kit-sim "max under 0.5 ms" clause still fails to one OS spike (02.1, raised in both drills). Only "variant minus X"
reached the playbook, and not prompt 04. The agent follows the prompt at each stage, not the playbook.
Replacement: apply the drill-2 edit list to the prompt files before the next drill, and change the section 6 line to "Drill 2
prompt edits applied on <date>" with the commit.

**D4. Track B is the default, but the playbook is a Track A document and the Track B spec cannot build a legal bot under
the drilled axis.**
Sentences: "Default: **Track B** unless the organizers confirmed in writing that pre-written code and tables are allowed." and
(section 8) "which is the compressed specification of this repo: cheap bot by minute 15, evaluator and profiler by 30, equity
table and ICM gate by 45".
Why, in order of weight: (a) Under Track B there is no strict sim, no fingerprint, no `Config`, no `rules_tonight.json`; the
stage table's pass checks for Stages 3-5 and hard rule 3 ("verified by a command whose output the Verifier reads") have no
command. Prompt 05, which Track B step 4 points at, is written entirely in Track A objects (`Rules.rank_order`, `Spot`,
`Config.postflop`, `hyperion/drills/variants.py`). (b) The spec has no rank remap. Under permuted ranks, the one axis drilled,
"pair of 9s or better, AK, AQ" and the prime-keyed evaluator are wrong in displayed ranks from minute 15 on; one sentence
("remap displayed rank to strength at parse time; everything downstream is canonical") fixes it and is missing. (c) Step 3
puts exact Malmuth-Harville over eight stacks on the decision path ("Before any all-in decision compare the ICM value of fold
versus ... win and lose"). The repo's own measurement is ~470 µs for exact ICM with eight live seats after optimisation
(`decisions.md`), which is why Hero precomputes a curve per hand; a from-scratch version will time out. (d) "max under 500 µs"
over 10,000 calls is the clause both drills showed fails to OS jitter on a 1 µs bot. (e) The rules do not ban pre-written code:
§6.1's prohibited list is collusion, copying another team, platform interference, endpoint misuse; §3.3 hands teams a kit;
"from scratch" is a tweet. The playbook applies the strict reading to code but the loose reading to the tool (Claude Code by
default although §3.4 names Astra and Codex). Pick one risk posture.
Replacement: "Default: Track A. Track B only if the organizers say in writing that code written before the event may not be
used; in that case the hour is the Track B cheap bot (step 1) plus the windows, and steps 2-3 are dropped unless a Track B
drill has hit minute 30 clean." Then fix the spec: rank remap at parse; ICM from a per-hand cached curve, never per decision;
p99 instead of max; and a Track B pass-check column in the stage table.

**D5. The submission cadence in the rules breaks the Stage 2 and Stage 6 timing.**
Sentences: "At 0:12 with no clean adapter: submit the kit's own example bot. Never pass 0:15 without a submission" and
"Minutes 12 to 15: freeze then submit, or submit nothing."
Why: rules §3.5, "Each team may submit one bot every five minutes." An upload at 0:12 blocks the next until 0:17. The
playbook never mentions the limit; CHALLENGE does. The 0:50 submission's failure branch ("Resubmit the Stage 2 cheap bot") is
also at least five minutes away, and the cheap bot is already the active submission anyway.
Replacement: "One upload per five minutes (§3.5). 0:12: upload whichever is clean, the kit's example bot or ours; that upload is
the floor. 0:17 earliest for the next. Windows: one upload per window, at minute 12-15; if it is rejected there is no retry
before the freeze, so the frozen bot stays." Alarms: :12, :17, :28, :40, :50 (keep :28 only if it means something; say what).

**D6. The information-axis patch the axis table and CHALLENGE promise does not exist in strategy.**
Sentences (axis table): "best-two-card class plus a bonus" and (CHALLENGE): "preflop falls back to best-two-card class".
Why: nothing under `hyperion/strategy/` reads `hole_classes.json` or `hole_label` (grep); `decisions.md` says "Hole-card counts
other than 2 fall through (preflop check/fold ...)"; prompt 03 step 4 tells the agent to write the fallback in the hour, which
contradicts "the code is pre-designed ... zero research". With 3 hole cards Hero folds every preflop decision it is not
check-free for, from minute 25 to the end, unless the agent writes a preflop model under time.
Replacement: either build and test `best2+tags` in `preflop.py` this week, or write "Information axis: Hero preflop is
check/fold for ≠2 hole cards; Stage 5 is where the agent writes the best-two fallback (budget the whole 10 minutes, measure in
the sim, ship the cheap bot if not clean)."

**D7. Three pass checks cannot be read from any command output.**
Sentences: "bot folds/calls/raises at least once" (Stage 2); "timeouts < 0.3% of decisions" (Stage 4); "points did not drop
beyond CI" in "the same strict sim" (Stage 5).
Why: the kit runners print no action mix and the cheap bot made 0 calls in 50 hands (drill 1, 02.2); the sim runner prints
`tmo` and hands, not decisions per bot (drill 2, 04.5, unchanged: no `calls` column in `runner.py`); strict-mode points move
±0.2 run to run on a loaded box (drill 2 repo finding 1) while section 6 of this playbook says to use `--mode measure` for
comparisons, contradicting its own stage table.
Replacement: "fold, check-or-call, and raise each at least once over 100 hands, counted by a 10-line wrapper around `decide`";
"tmo ≤ 0.3% of hands as printed" (or add the column); "errors and latency from the strict run; points from `--mode measure
--rotate --tables 40` on the same seed, a drop only if the after line is below the before line by more than half its ±95%".

**D8. Stage 3's timing claim is not what was measured.**
Sentence: "Default generation is about 50 seconds on 7 cores; a 3-hole-card variant about 3 minutes."
Why: `decisions.md` records 90 s after raising samples to 20,000; drill 1 measured 152 s under load; `--variant-check` for this
review projects 133 s default (57 s of it the push/fold solve, which now runs inside `gen_tables`) and 152 s for 3 hole cards,
both at 7 workers on a loaded box. On a 4-core laptop the default is 4-5 minutes, which is prompt 03's whole generation box.
Replacement: "Generation is 2-3 minutes on 7 cores under load, about twice that on a 4-core laptop; 3 hole cards is the same
(no matrix, no push/fold solve). Run `--variant-check` first; it projects in 10 s." And start the generator the moment the
rule sheet names the axis, not at 0:15 (see ordering, section 4).

**D9. "What wins" states the placeholder schedule as a fact about the event.**
Sentence: "blinds reach 200/400 by hand 175 and every table ends in push/fold." (also CHALLENGE: "16,000 chips at 200/400
blinds means every table ends in push/fold").
Why: that is `Rules.blind_levels`' default in `types.py`; rules §4.4 give 10/20 rising every 25 hands and put the schedule in
the kit. Drill 2's variant had 320/640 by hand 101; another could stay at 50/100. The conclusion may hold; the premise is ours.
Replacement: "Under our placeholder schedule blinds reach 200/400 by hand 175 and every table ends in push/fold; the kit's
schedule replaces that in Stage 1 and sets how early push/fold starts."

**D10. The windows assume standings arrive at minute 0 of each window.**
Sentence: "Minutes 0 to 5: read standings; our rank, our mean, the spread ..."
Why: T_k must simulate 10,000 tables before standings exist; nothing in the rules says how long that takes or whether
per-table results are shown at all. If standings arrive at minute 8, the 5-12 dial window is gone. Also §3.4 permits AI tools
"during the build phase"; tool use in the windows is not stated (CHALLENGE notices this; the playbook does not).
Replacement: "Standings arrive at an unknown minute; until they do, the only permitted work is the error-log check. If
standings land after minute 10, submit nothing." And add the tool question to the email.

**D11. The signal table's dials name knobs that are not Config keys or point the wrong way by our own data.**
Sentences: "raise ICM premium", "dead-seat detection from 5 to 3 observations", "lower steal threshold", "faster profiler
weights".
Why: no key contains "premium" (nearest: `preflop.shove_call_margin` 0.10, `pushfold.push_equity_margin`,
`pushfold.call_equity_margin`); `dead_after` is a `Profiler` constructor argument that `HeroCore` does not expose
(`hero.py:180`), so it is a code edit, which hard rule "no new modules, only Config overrides" forbids in a window;
`preflop.steal_positions` is a seat count, not a threshold; "weights grow faster" is `profiler_blend_n`, not `profiler_prior_n`.
And `decisions.md` (strong field) measured hero_tight 4.42 and hero_loose 4.51, both below default 4.71: the "tighten opens"
and "lower steal threshold" rows have been measured not to help in the one field tried.
Replacement: write each dial as an override dict, e.g. `{"preflop.shove_call_margin": 0.15, "postflop.value_tier": 5,
"preflop.three_bet_frac": 0.03}`, and expose `profiler_dead_after` in `Config` this week or delete the row.

**D12. Stage 6's T6 sentence contradicts the one-dial-per-window rule.**
Sentence: "the bot that plays T6 should be a bot that has already played T4 or T5 clean."
Why: the stage table allows a dial in every window including the one before T6; this sentence forbids it. Both cannot be hard
rules. Replacement: "No change in the window before T6 unless it fixes an error in our own log."

**D13. The Stage 5 drill-2 lesson is stale and the ante line is still unmeasured.**
Sentence: "when the sim is blind to what the patch compensates for (it could not play antes), the prompt's own revert rule
fires".
Why: antes landed in `Rules` and the engine after drill 2 (`ante`, `ante_from_level`, `ante_per_level`; commit `bbbdea7`). The
sim can now see an ante patch, so the lesson no longer applies to antes, and the axis-table line "antes loosen opens one step
and push depth 2 bb" has never been measured with antes on. Replacement: "(drill 2's engine could not post antes; it can now,
so an ante patch is verifiable)" and run that measurement before the night or drop the line.

**D14. Flowchart and text disagree on when Stage 3 runs.**
Sentence (flowchart): "card axis moved?" Why: the four axes are Strength / Information / Payoff / Betting; "card axis" is not
one of them and the text says "strength or information". Replacement: "strength or information axis moved?"

**D15. Eligibility sentence misreads the rule.** Sentence: "Eligibility is students and the classes of 2025 and 2026 only."
Why: §1.1 is enrolled students of US/Canadian universities with no class-year limit, plus graduates of 2025 and 2026
(CHALLENGE has it right). Replacement: copy CHALLENGE's sentence.

**D16. Solo mode is undefined.** Sentence: "If solo, you are the Driver and the Verifier checklist is on paper." Why: the
roles table says the Driver "never reads rules in depth" and the Verifier "never touches the agent session"; a solo person
must do both and the playbook does not say which Verifier duty is dropped. Replacement: "Solo: you read the rules yourself
in Stage 1 (the agent waits), and the printed pass checks are the Verifier; skip the per-stage callouts."

**D17. Unsourced history.** Sentence: "the MIT archive never did it in seven years." Why: not in `docs/research/` (grep for
"seven years", "card sum", "never did" finds nothing). Replacement: cite the catalog year list or delete.

**D18. The briefing still hard-codes format numbers as "hard constraints".** Sentence (00-briefing): "Format: eight-player
sit-and-go tables, 2,000 starting chips, blinds 10/20 rising every 25 hands, table ends at bust-out or 200 hands". Why: drill
2's variant contradicted three of them and the agent had to choose which document wins (drill 2, 00.1, not applied).
CHALLENGE now carries the same numbers with "the handout wins". Replacement: "Format: see CHALLENGE.md; the rules text I paste
next overrides any number there."

---

## 2. Ledger: measured / sourced / asserted

"Measured" = a number in a drill log or `decisions.md`, or measured for this review. "Sourced" = a rule section or a code path
that exists. "Asserted" = neither.

| Claim | Status | Where |
|---|---|---|
| Eight-bot tables, 10,000 per tournament, points by finish, ICM at cap, weights 1..6, T1 4.8%, T5+T6 52% | sourced | rules §4.3-4.7 |
| 1 ms, 100 MB, no network, error/timeout folds-or-checks | sourced | §3.6-3.7 |
| Field is one-hour student bots; eligibility | sourced | §1, §3.3 |
| Blinds 200/400 by hand 175; every table ends in push/fold | asserted (placeholder schedule) | `types.py` defaults; §4.4 says schedule is in the kit |
| Deep postflop skill worth almost nothing | asserted; partly contradicted | bust tracer: 18% of Hero busts are river calls |
| ICM short-stack play is where points are | measured | ICM gate 5.86 → 6.48 (decisions) |
| Attacking dead/timing-out seats pays | measured in one field | chaos field hero 6.78, first |
| Never crash / never time out is the first edge | measured | drill logs: Hero 0 exc / 0 ill; `tmo` is box jitter |
| Stage 1: sheet by minute 2 | measured | drills 1, 2 |
| Stage 2: legal submission minute 2-3 | measured | drills 1, 2 |
| Stage 2: "folds/calls/raises at least once" checkable | contradicted | drill 1 02.2 |
| Stage 2: cheap bot is the most valuable thing | asserted (reasonable) | - |
| Stage 3: generator ~50 s / 3-card ~3 min | contradicted / roughly right | 133 s and 152 s projected (this review); 152 s drill 1 |
| Stage 3: loader verifies fingerprint; generator re-solves push/fold | sourced (verified in code) | `pushfold.py:175`, `gen_tables.py:132-140` |
| Stage 3: remapped-decision print catches the board-remap bug | measured | drill 1 repo bug 1 |
| Stage 4: Hero wired clean by minute 10 / 4 | measured | drills 1, 2 |
| Stage 4: p99 < 300 µs | measured | 46-191 µs in every run |
| Stage 4: timeouts < 0.3% of decisions | not computable from output | no decisions column |
| Stage 4: Hero ≥ tag − CI on realistic field | measured false | this review: 5.278 vs 5.677 ± 0.197 |
| Stage 4: fallback = cheap + profiler flags, "most of Hero's edge" | asserted; not configurable | D2 |
| Stage 5: patch verifiable at 300 tables | contradicted | ±0.17 CI vs 0.2 run spread; both drills ended `{}` |
| Stage 5: ship unpatched rather than unverified | sourced (policy) | drill 2 |
| Windows: standings at minute 0, 20-minute loop, submit by 15 | asserted / partly sourced | §4.1 spacing sourced; standings latency unknown |
| Axis: strength → regenerate, strategy untouched | measured | drill 1: +0.48, third → first |
| Axis: information → best-two + bonus, thresholds before last swap | asserted; code absent | D6 |
| Axis: payoff → paste `Rules.payouts`, Hero reads it | measured | drill 2 (`payouts seen by hero`) |
| Axis: payoff → side payoff into shove/call EV (`bounty_bonus`) | asserted; no such term in `Spot` | grep |
| Axis: betting → adapter clamps, `Config` sizes | sourced (pot-limit in `Rules.betting`); unmeasured | decisions catalog |
| Axis: betting → antes loosen opens one step, push depth +2 bb | asserted; measured only as cost without antes | drill 2 05 |
| Non-poker twist "a few percent; MIT never in seven years" | asserted | nothing in research |
| Signal row 1 (busting early → raise premium, value tier, stop 3-bets) | asserted | hero_tight below default in strong field |
| Signal row 2 (mid-table → steal more, c-bet more) | asserted; contrary evidence | hero_loose below default |
| Signal row 3 (dead field → dead_after 5 → 3) | asserted; not a Config key | D11 |
| Signal row 4 (strong field → tighten, premium high, faster weights) | asserted; contrary evidence | same sweep |
| Signal row 5 (timeouts → `cheap=True`) | measured as weak | drill 1: tmo 58 → 49, points −0.93 |
| Section 6 reproducibility ±0.2 | measured | drill 2 finding 1 |
| Track B: cheap bot by 15, evaluator+profiler by 30, ICM by 45 | asserted; never drilled | section 8 says so |
| Stage 0: Track B default is the conservative reading | asserted | §6.1 does not list it |

---

## 3. Nonexistent or wrong references (from greps)

PLAYBOOK.md
- "cheap bot plus the profiler's dead-seat and station flags": not expressible in `Config` (cheap paths skip `prof`).
- "dead-seat detection from 5 to 3 observations": `Profiler(dead_after=5)` is not reachable from `Config`.
- "ICM premium", "all-in value tier", "steal threshold": no key by these names (see D11 for nearest).
- "card axis": not an axis.
- `frozen/T1`: directory does not exist; add `mkdir -p frozen` to Stage 0 or the `cp` fails at 0:50.
- "One full drill per fake kit (A, B, C, D)": `hyperion/drills/run.py` has `KITS = ("a", "b", "c")`; kit D runs only via its
  own runner (its RUBRIC says the two edits needed).
- "Codex with Astra": Astra is the model (GPT-6 Astra) inside Codex; say "Codex (GPT-6 Astra)".
- Exists and verified: `--mode strict|measure`, `--field realistic`, `--rotate`, `Config.cheap`, `Config.use_profiler`,
  `Rules.payouts`, `make_bot()`, `Hero.cheap()`, `tables.load()`, `load_pushfold(...)["matrix_fp"]`, `matrix_fingerprint`,
  `hyperion/drills/fakekits/*/RUBRIC.md` (four), `05-variant-patch.md` axis sections, `tools/gen_tables.py --variant-check
  --skip-matrix --workers`.

docs/prompts
- 02: "the three reference adapters": four (`KitDAdapter` exists).
- 03 step 4: "Confirm `hyperion/strategy/preflop.py` reads it [`hole_classes.json`]": it does not; nothing in `strategy/` does.
- 04 step 4: generator as load without `--out`: writes into the real `tables/`.
- 05: "`bounty_bonus` term in `Spot`": no such attribute; it is an instruction to add one, phrased as if it exists.
- 05, 06: "ICM risk premium" / "`Config.pushfold` ICM premium": no key.
- 06: "dead-seat detection count from 5 to 3": not a Config key.
- track-b: "Step 4: the variant patch from prompt 05": prompt 05 is Track A vocabulary throughout.

docs/packet/CONTRACTS.md
- "`--kit a|b|c|d`": `d` is not accepted by `hyperion.drills.run` (hard-coded string, `apicard.py:26`).
- `Adapter.__init__` doc "Initialize self. See help(type(self)) for accurate signature.": `object.__init__`'s docstring leaked.
- Config table header `| key |  | default |`: the type column is empty for all 90 rows (`_config_rows` emits a blank).

docs/packet/CHALLENGE.md
- "preflop falls back to best-two-card class": no such code (D6).
- "`Rules.ante`, `ante_from_level` (engine support landing)": landed; stale.

---

## 4. Ordering and the Track B default

**Stage 3 before Stage 4.** The generator is one command that runs 2-3 minutes on its own cores; Stage 4 is where both drills
found Hero's real bugs (drill 1: a `KeyError` only the 300-table sim could surface). Serialising them wastes the generator's
wall time and delays the only check that finds crashes. Strictly better: when the rule sheet names a card axis at ~0:02,
start `gen_tables --out tables_tonight/` (never `tables/`) in a second terminal, do Stage 2 and begin Stage 4 against the old
tables, and swap in `tables_tonight/` with the fingerprint and remapped-decision checks when it finishes. Nothing in Stage 4's
error/latency checks depends on which tables are loaded. For the information axis, Stage 3 as written is strictly dominated:
its product (`hole_classes.json`) is read by nothing, so skip generation and spend the time in Stage 5 on the preflop
fallback (D6).

**Skipping Stage 5.** Both drills ended with override `{}`. For the strength axis the patch is a pure confirmation; for
point-table payoffs there is no knob (Hero reads payouts). In those two cases Stage 5 costs 10 minutes and its verdict is
inside run-to-run noise (D7). Strictly better: declare Stage 5 skipped for strength and point-table payoffs and spend 0:40-0:50
on the submission margin: import time in a fresh process with the cache deleted (drill 1, 04.5), the zip opened and run from a
clean directory, and `NIGHT.md`. Keep Stage 5 for betting (antes, pot limit, now representable) and information (where the code
must be written).

**Track B default.** Given the rules text, no. §6.1 enumerates prohibited conduct and pre-written code is not in it; §3.3
provides a kit; §5.4's code review is the only hook, and it reviews for malware, credentials and copying. The downside of
Track A if the organizers object is a conversation at check-in; the downside of Track B is an undrilled 45-minute rebuild
whose spec (D4) puts exact ICM on the decision path and has no rank remap, so under the one axis we have drilled it ships a
wrong bot at minute 15 and a timing-out one at minute 45. If Track B is forced, the right Track B is step 1 plus the windows.
The spec is sufficient for a legal cheap bot in 15 minutes (step 1 is ~150 lines, the checks are concrete) only if "remap
displayed ranks at parse" is added and the max-latency clause is replaced; it is not sufficient for steps 2-3 in the time given.

---

## 5. Context packet (`CHALLENGE.md`, `CONTRACTS.md`, revised `00-briefing.md`)

**As the Verifier.** CHALLENGE is the better rules digest of the two documents: it carries §3.5 (one upload per five minutes)
and the tool-permission gap in the windows, both of which the playbook lacks. The "Our assumptions" table is the right shape
for the rule-sheet diff. Defects: the "What wins" paragraph repeats D9 and adds "most students will write Monte Carlo equity,
which is 10 to 100 ms in Python" (our own `MonteCarloBot` at 200 rollouts is 1-3 ms; say "which times out at any useful
sample count"); the Lifecycle row says "if not, move table loading to module import" while prompt 04 step 5 moves loading the
other way when import exceeds 5 s; the Antes row is stale ("landing"); the Hole-cards row promises code that is not there (D6).
The timeline table and "The event" paragraph are correct and are Verifier material, not agent material.

**As the agent.** CONTRACTS answers the drill-1 pushfold-cache question implicitly (the loader now checks `matrix_fp`; it
should say so in one line so nobody deletes the file by hand) and the drill-2 "can the engine represent antes" question
(the `Rules` table). It does not answer the questions the agent actually asked: which `Rules` the cheap-bot adapter is
constructed with (`Adapter(bot, rules=None)` defaults to the placeholder; drills 1 and 2 both shipped the wrong `Rules` at
0:15 because nothing says "pass `rules_tonight`"); what the fallback dict is; what "one step" of opens means; how to A/B a
Config override without editing code (`python -m hyperion.sim --hero-config '{"pushfold.threshold_bb": 14}'` is the
mechanism Stages 5 and 6 are built on and appears nowhere in the packet or the prompts); the rules JSON shape (a flat object
of `Rules` fields; lists become tuples; the same file feeds `gen_tables --rules` and `sim --rules`); which `Adapter` methods
to override (`to_observation`, `from_action`, `native_safe`) versus inherit (`decide` already wraps in try/except and clamps;
`start`, `hand_end`), since the flat seven-method list invites an agent to reimplement `decide`; `make_observation(...)`
with lowercase legal names; `HandResult` fields; `Config.cheap_config()`; `hero.safe.stats()` for the window error check;
`evaluate_displayed(cards, rules)`. Missing from CHALLENGE for the agent: the default submission layout when the rules are
silent (drill 1 Q1). Nothing in the packet contradicts a prompt, but the packet plus playbook plus prompt 04 give the agent two
different Stage 4 commands (D1), which it will resolve silently.

**As the skeptic.** CHALLENGE's rule citations are sourced and match the research note. "Expect close scores" is sourced
(§4.8 inference). The assumption table's right-hand column mixes things that exist (`Rules.betting`, `Rules.payouts`) with
things that do not (best-two fallback, "loosen opens one step" as a defined operation); mark the second kind.

**As the context-budget skeptic.** 5,457 words is roughly 7,500 tokens: not a problem of size for the model, and the agent
reads it in well under a minute. The cost is relevance and conflict, not length. Of the playbook's 2,757 words, about 1,100
are for humans only and the agent cannot act on them: §1 Roles (lines 49-60), §2 Stage 0 (63-91), §6 Evidence (207-226), §8
Tracks (243-253), §9 Revision log (257-261), §10 The email (265-274). Worse than wasted, §2 and §8 tell the agent the plan may
be Track B and the tool may be Codex, which it will try to reconcile with a Track A repo in front of it. CONTRACTS spends
~900 of its 1,390 words on a 90-row Config table with an empty column; the playbook, prompts and signal table together name
about twelve keys. CHALLENGE's "The event" (lines 6-14) and "Timeline" (69-78) are ~190 words of Verifier material. Proposed
cuts, with exact lines:
- Playbook: generate `docs/packet/PLAYBOOK-agent.md` from §0, §3, §4, §5, §7 (lines 13-45, 94-176, 180-192, 195-203, 229-239)
  by a script next to `apicard.py`, so there is still one source. ~1,600 words.
- CONTRACTS: replace the Config table with the keys the prompts name (`cheap`, `use_profiler`, `use_icm`, `deadline_ms`,
  `pushfold.threshold_bb`, `preflop.open_frac`, `preflop.open_frac_default`, `preflop.three_bet_frac`,
  `preflop.shove_call_margin`, `postflop.value_tier`, `postflop.cbet_freq_ip_dry`, `profiler_prior_n`, `profiler_blend_n`)
  plus one line: "all keys: `python tools/apicard.py --config`". Delete the Observation "default" column (17 × "required").
  Add a "Commands" block of ~80 words: `--hero-config`, `--rules`, `--bots`, `--rotate`, `--mode measure`, `gen_tables
  --variant-check --skip-matrix --workers --out`, and the rules-JSON shape. Fix the header, the `__init__` doc and `--kit d`
  in `apicard.py`. Net ~500 words.
- CHALLENGE: cut lines 6-14 and 69-78 from the agent copy; keep them in the Verifier print. ~630 words.
- Briefing: replace the Format bullet with a pointer to CHALLENGE (D18). ~440 words.
Total for the agent at minute 0: ~3,200 words, with the Stage 4 command stated once.

---

## 6. Questions only the human can answer

1. **Track.** If the email is unanswered on Nov 5, do you accept the check-in-conversation risk of Track A, or the measured
   cost of Track B (a cheap bot only, since steps 2-3 are undrilled)? The rules text supports A; the "from scratch" framing
   and §5.4 code review are the residual risk. This review recommends A, but it is your disqualification appetite.
2. **Tool.** Will you run Claude Code in the room without written permission (§3.4 names Astra and Codex), and in the
   windows (§3.4 says "during the build phase")? If the answer is Codex, both drills, every effort setting and the prompts'
   tone were tested on a different model, and one drill on Codex is owed before Nov 6.
3. **The Stage 4 gate.** Do you want to ship Hero knowing it measures third in the realistic field (5.28 vs tag 5.68 on the
   playbook's own command), on the argument that it wins twice as many tables and the real field is softer, or do you want
   the gate to be "beats tag", in which case Hero fails it today and tuning, not the playbook, is the work this week?
4. **Solo or two.** Who is the Verifier? If solo, which Verifier duty is dropped (D16), and does the agent read the rules
   text itself in Stage 1?

---

## 7. Measurements taken for this review (this box, 8 cores, load 6-8 throughout)

```
pytest -q                                                   310 passed in 34.0 s
sim --tables 300 --seed 11 --mode strict --field realistic  tag 5.677 ±0.197 | pushfold 5.494 | loose_aggro 5.414 | hero 5.278 ±0.234 (4th)
                                                            hero exc 0 ill 0 tmo 7 p99 49 µs; 55,933 hands in 59.4 s
sim --tables 300 --seed 11 --mode strict --bots hero,tag,nit,naive,station,maniac,random,allin
                                                            hero 6.494 ±0.169 (1st) | tag 6.450 | nit 6.137; 45,836 hands in 5.1 s
gen_tables --variant-check (default, 7 workers)             projected 133 s (preflop 58 + matrix 18 + pushfold 57 + flops 1)
gen_tables --variant-check (toss_or_holdem, 3 hole cards)   projected 152 s (preflop 149 + flops 3; no matrix, no pushfold)
```
First-read confusions (recorded before reading anything else) are in the scratchpad; the ones that survived the full read
are D1, D4, D7, D14, D16 and the :28 alarm, which the playbook never explains.
