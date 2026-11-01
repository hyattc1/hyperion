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

**Running as of 2026-11-01 00:30 ET (three Opus agents, launched from the coordinating session):**
- Mid-phase aggression pass: Hero's 10–25 bb preflop volume (steals by fold-to-steal read, light 3-bets
  from the blinds, per-seat re-shove read), rival 2 the main target. Running log, committed per screen:
  `docs/drills/aggression-pass-log.md`. Owns `hyperion/strategy/*`, `tools/sweep.py`. Relaunch from the log.
- Rival 3: integrated as `rival3`, the holdout (never tuned on); on `holdout` Hero - rival3 -0.74 ± 0.16.
- Drill 5 follow-ups (item 4 below), then drill 6: Track A on kit A with toss_or_holdem, on a pinned copy.

Agents commit as they finish tasks. If one was killed, `git log` shows what landed; the rest is below.

### 1. Deep Hero pass: DONE in substance, cut off by the Opus 5-hour limit (resets 1:30 PM ET) while writing its
report. All code is committed (ce5a137, c5cb3db, 745bf82, d917c45, 5257118, f955955); its full entry is in
docs/decisions.md, "Deep Hero pass". Shipped: solved multiway push/fold and re-shove tables (36 s to generate),
shove calls read against the shover's observed range, a late call-down cap, hand_end 6.4 ms to 49 µs p99,
safe_err / safe_over columns. Readiness still 22 READY / 1 PLAYS, Hero first on 15 of 23 variants.
Targets: met T2b, T3, T4, T5, T6 (MicroAgent pushed below uniform). NOT met: T1 (Hero − rival1 −0.14 realistic,
−0.13 top, was −0.30), T2a, T7 (Hero − rival2 −0.56 on top2), T8. Its diagnosis: the rivals win on the VOLUME of
uncontested preflop pots they take at 10–25 bb (wide opens scaled by the blinds' fold rate, light 3-bets from
the blinds, frequent re-shoves). No single gate fixes that; it is Hero's own preflop aggression in the middle
phase. Next pass: build and sweep exactly that, with rival 2 as the target. The fallback in item 2 below
(rival decision core behind Hero's shell) is the owner's call and has not been taken.

### 2. Red-team rival 2: DONE and integrated (`rival2`, fields `top`, `top2`; decisions entry "Rival 2 in the
pool"). It is the strongest opponent: top2 Hero 4.36 vs rival2 4.98; one rival2 among 7 Heroes +0.69 over
uniform; it beats rival1 in our engine. Its leak on Hero is the opposite of rival1's: Hero folds 93% to its
13-25 bb shoves while the calls Hero makes win 63%. The deep pass has this as targets T7 and T8.
A competitor's public bot, MicroAgent (microholdem, MIT), is registered as `micro` with a `public` field when
HYPERION_MICROHOLDEM is set; it is an opponent and cross-check only, never copied into Hero (rules §6.1).
Report: docs/drills/public-repos-sparring.md. Target T6: one micro among 7 Heroes ≤ uniform + 0.1.

### 3. Drill 5: DONE (report committed). Numbers: legal bot minute 7, spec exhausted minute 24, level with rival1.
Operator protocol as in drill 3; kit B copied self-contained; hidden variant permuted_ranks (seed 0);
agent role sees only the prompts and spec, never the repo; score minutes per checkpoint vs drill 3's
4/9/17/19, the rank-remap correctness (permuted AA raises, permuted 72o folds), and a 300-table comparison
vs Hero on `--variant permuted_ranks --field realistic`.

### 4. Public-repo sparring: DONE (report committed). Original brief, kept for reference:
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
4. ~~Drill 5 follow-ups (small): Track B spec step 3b's push-EV formula fails its own sanity check (22 on
   the button at 10 bb: push EV below fold), fix the calibration (edit 16 in the drill 5 report); add a
   spec clause for kits with no action history at all; add `--variant-seed` to `python -m hyperion.sim` so
   the permutation is not derived from the table seed; make tag/nit/pushfold remap `rank_order` so they
   are honest yardsticks under permuted ranks (only Hero and rival1 do today).~~ DONE 2026-11-01: step 3b
   is chip EV (c 0.2, e vs top 20%) and the no-history clause is in step 2, spec v2.1 (8515fc5);
   `--variant-seed` in `hyperion/sim/runner.py` (fa43da8); `bestiary.strength_view` for tag/nit/pushfold,
   PLAYBOOK §4b re-measured (be14544); why and numbers in docs/decisions.md, "Drill 5 follow-ups".
5. Re-run the competition research on Nov 7: the Menlo Park variant and kit interface will be known.

## Decisions already made (do not reopen without the owner)

- Track A default. Track B is the fallback; spec v2 measured in drill 5.
- Repo stays private until after the Finals. Public release only via `tools/export_public.py`.
- Preparation is not something to hide; the upload is lean because that is good engineering.
- Tool on the night: Claude Code with Opus 5.5 fast mode if allowed, else Codex with Astra; effort xhigh
  for prompts 01 and 05, medium/high for 02 to 04.
- The owner wants the big picture, not micro-narration, and no punny names.
- Rival 3 (`rival3`, fields `holdout` and `top3`) is the holdout: Hero is never tuned against it, and no Hero
  leak analysis is done against it. It checks whether gains against rivals 1 and 2 generalise.

## Open items only the owner can answer

- Who sits at the table (eligibility: enrolled students or classes of 2025/2026) and which regional.
- Whether to send the four-question email in `PLAYBOOK.md` §10 to pokerbot@sequoiacap.com.
- Whether to add a teammate to the private repo.

## Working rules in this tree

Several agents share one working tree. `git add <explicit paths>` only, never `-A`. Commit before
`git pull --rebase`. Owner-of-files per task is stated in each brief; `docs/decisions.md` is append-only.
