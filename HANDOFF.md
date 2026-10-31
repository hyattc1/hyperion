# HANDOFF (written 2026-10-31, for a new session picking this up)

Start here. Then read `PLAYBOOK.md` and the last five entries of `docs/decisions.md`. Everything below
is either committed or named as lost-if-killed.

## State in one paragraph

Hero, the bot, plays all 23 catalogued twists (22 READY, 1 PLAYS), decides in ~15 µs, passes 430+
tests, and was tuned to finish first against every field we wrote. Then a red-team rival built blind in
36 minutes (`hyperion/sim/rivals/rival1.py`) turned out stronger: tied on the realistic field, ahead on the
top field, and it wins the mirror test. The owner's position: Hero is still a tuned chart bot with lots
of room; the rival is a sparring partner, not a ceiling. The prep for the hour (prompts, playbook, four
fake kits, tooling, five drills) is in good shape; Track A (bring the repo) is the default.

## What was running when this was written, and how to relaunch each

Agents commit as they finish tasks. If one was killed, `git log` shows what landed; the rest is below.

### 1. Deep Hero pass: STOPPED at 96% usage during task 1 (observability). Its uncommitted edits to
engine.py, runner.py, hero/postflop/preflop/pushfold.py, tools/sweep.py and a new tests/test_sim_observability.py
are in `git stash list` as "deep-pass WIP"; inspect with `git stash show -p stash@{0}` and either apply or
drop before relaunching. Relaunch with this brief:
Owns hyperion/strategy/*, sim/runner.py and sim/engine.py (observability only), tools/sweep.py, tables/,
tests, decisions.md (append), CONTRACTS.md via `python tools/apicard.py`. Targets: (T1) Hero ≥ rival1 + 0.15
on `--field realistic` and `--field top` with disjoint 95% CIs at ≥ 400 duplicate seeds; (T2) Hero among 7
rival1 ≥ uniform, rival1 among 7 Heroes ≤ uniform + 0.1; (T3) no regression on mixed base and strong
fields; (T4) latency gate plus hand_end/new_table p99 < 1 ms; (T5) `tools/variant_matrix.py` not worse.
Tasks: (1) surface SafeBot-swallowed errors and overruns as runner columns (`safe_err`, `safe_over`), bust
tracer attributes to the acting module; (2) hand_end cost: exact 8-player ICM in the per-hand curve was
6.4 ms, bring p99 under 1 ms; (3) solved multiway all-in-or-fold push/fold with ICM: first-in shove per
seat vs k behind at 2..25 bb, plus re-shove and call-vs-shove, fictitious play or CFR+, chip-EV tables
offline, ICM via the value curve, cross-check vs RangeMyHand 9-max frequencies (CC BY 4.0, download only),
replace `tighten_per_player` with the table; (4) exploit-resistance: shove-calling conditioned on the
shover's observed shove frequency; big-blind defence at pot-odds-correct frequency with a small polarised
3-bet set; call-down tightening vs low-VPIP high-aggression seats; early-game risk-of-ruin cap as a Config
key; steal dials driven by the folder read within 20 hands; (5) sweep on realistic and top, confirm on
base and strong, both mirror tests, readiness matrix; (6) add `rival2` to fields when it lands.

### 2. Red-team rival 2 (writes only at the end). If `docs/drills/redteam/rival2_bot.py` is absent, relaunch:
A computation-first team, seed 20262, no access to this repo and must not read rival1: builds its own
169-class equity table by Monte Carlo at import (≤ 5 s), ranges from equity percentiles by position and
players behind, heads-up push/fold by iterated best response tightened multiway, exact ICM once per hand
with interpolation, wide steal-and-defend game, two-number opponent model with Beta priors, 60-minute cap,
verified on the harness from `docs/drills/redteam/redteam-1.md`. Output: rival2_bot.py and redteam-2.md.
Then integrate like rival 1: `hyperion/sim/rivals/rival2.py`, `RivalBot`-style adapter in bestiary.py,
seat it in `top` and a new `top2` field, measure realistic/top/mirrors, decisions entry.

### 3. Drill 5: DONE (report committed). Numbers: legal bot minute 7, spec exhausted minute 24, level with rival1.
Operator protocol as in drill 3; kit B copied self-contained; hidden variant permuted_ranks (seed 0);
agent role sees only the prompts and spec, never the repo; score minutes per checkpoint vs drill 3's
4/9/17/19, the rank-remap correctness (permuted AA raises, permuted 72o folds), and a 300-table comparison
vs Hero on `--variant permuted_ranks --field realistic`.

### 4. Public-repo sparring: STOPPED at 96% usage before it ran anything; nothing to recover. Relaunch:
Clone the competitor prep repos named in `docs/research/notes/presolved_resources.md` §4 into isolated
scratch dirs, read every file for network/subprocess/exec before running, adapt any playable bot to our
Bot protocol in scratch, run 300 strict tables vs Hero and tag, report strength and what each assumes the
kit looks like. Copy nothing into this repo. microholdem's solver output is a cross-check only.

## After those land

1. Final numbers into `PLAYBOOK.md` section 6 and a revision row; `python tools/apicard.py`; full suite;
   `python tools/export_public.py --out /tmp/x` must report zero denylist hits.
2. If Hero still loses the mirror test after the deep pass: the agreed fallback is the rival's decision
   core behind Hero's adapter, tables and Config shell. Not before.
3. Optional: a third red-team rival with a third philosophy (exploitative maniac-hunter), and one drill on
   kit A with an information-axis twist (toss_or_holdem) now that Hero plays it.
4. Drill 5 follow-ups (small): Track B spec step 3b's push-EV formula fails its own sanity check (22 on
   the button at 10 bb: push EV below fold), fix the calibration (edit 16 in the drill 5 report); add a
   spec clause for kits with no action history at all; add `--variant-seed` to `python -m hyperion.sim` so
   the permutation is not derived from the table seed; make tag/nit/pushfold remap `rank_order` so they
   are honest yardsticks under permuted ranks (only Hero and rival1 do today).
5. Re-run the competition research on Nov 7: the Menlo Park variant and kit interface will be known.

## Decisions already made (do not reopen without the owner)

- Track A default. Track B is the fallback; spec v2 measured in drill 5.
- Repo stays private until after the Finals. Public release only via `tools/export_public.py`.
- Preparation is not something to hide; the upload is lean because that is good engineering.
- Tool on the night: Claude Code with Opus 5.5 fast mode if allowed, else Codex with Astra; effort xhigh
  for prompts 01 and 05, medium/high for 02 to 04.
- The owner wants the big picture, not micro-narration, and no punny names.

## Open items only the owner can answer

- Who sits at the table (eligibility: enrolled students or classes of 2025/2026) and which regional.
- Whether to send the four-question email in `PLAYBOOK.md` §10 to pokerbot@sequoiacap.com.
- Whether to add a teammate to the private repo.

## Working rules in this tree

Several agents share one working tree. `git add <explicit paths>` only, never `-A`. Commit before
`git pull --rebase`. Owner-of-files per task is stated in each brief; `docs/decisions.md` is append-only.
