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

**Plan change, 2026-11-01 04:00 ET (owner asked "why not just switch to the rival's code?").** Stop tuning
Hero's decision core for 0.1-point gains. Choose the best *core* behind Hero's shell (adapter, `Rules`,
23 variant hooks, SafeBot, tooling) and ship that. Candidates: Hero; hybrid with rival 2's core (built,
being measured); hybrid with rival 3's core (next, by the hybrid agent once v1 is written up). Rival 3 then
stops being a holdout; rival 4 (built blind, no assigned philosophy, scratchpad `redteam4/`) becomes the
judge. Winner = best on realistic, top and the rival-4 field, all 23 variants READY, timeouts no worse than
Hero's, robust across the three payout tables. The owner makes the final call on what ships.

**Running as of 2026-11-01 00:30 ET (three Opus agents, launched from the coordinating session):**
- Mid-phase aggression pass: Hero's 10–25 bb preflop volume (steals by fold-to-steal read, light 3-bets
  from the blinds, per-seat re-shove read), rival 2 the main target. Running log, committed per screen:
  `docs/drills/aggression-pass-log.md`. Owns `hyperion/strategy/*`, `tools/sweep.py`. Relaunch from the log.
- Rival 3: integrated as `rival3`, the holdout (never tuned on); on `holdout` Hero - rival3 -0.74 ± 0.16.
- Drill 5 follow-ups (item 4 below), then drill 6: Track A on kit A with toss_or_holdem, on a pinned copy.
- Gate the packaged bot: DONE. `tools/gate.py` plays the upload zip itself, paired against in-sim Hero, and
  the Stage 2 and Stage 4 gates run it before every upload. Drill 6's upload fails it (-2.46 ± 0.76), and so
  do drills 1, 2 and 4's (decisions entry "Gate the packaged bot").
- Hybrid candidate: DONE. `hybrid` (rival 2's core behind Hero's shell, `hyperion/hybrid/`) vs frozen Hero 7e51197:
  holdout -0.12 ± 0.13, realistic -0.11 ± 0.13, top +0.27, top2 +0.45; 1.5-3x Hero's timeouts. Recommendation: keep
  Hero, the switch is the owner's call (decisions entry "Hybrid candidate", log `docs/drills/hybrid-log.md`).
- Rival 4 (the judge): integrated as `rival4`, fields `judge` and `judge_top`, hero seat swapped by `judge@hybrid3` etc.;
  never tuned on; measured once in the final comparison (decisions entry "Rival 4 in the pool (the judge)").

Agents commit as they finish tasks. If one was killed, `git log` shows what landed; the rest is below.

### 1. Mid-phase aggression pass: DONE (2026-11-01). Entry "Mid-phase aggression pass" in docs/decisions.md; every
table in docs/drills/aggression-pass-log.md. (It follows the deep pass, whose entry "Deep Hero pass" stands.)
Measured first: Hero already opens wider than both rivals at every position; its gap is re-raising (rival 2
re-shoves 2.6 times per seat at 10-25 bb in levels 4-8, Hero 0.2) and heads-up postflop after calling (Hero folds
71-78% to c-bets). Shipped (f349380): `preflop.reshove_mid_bb` 25 (re-shove the solved re-shove set over single
opens up to 25 bb, ICM-gated) and `postflop.vs_cbet_margin` 0.05; plus Hero infers the betting state from the bets
when an adapter passes no history (c38259e; stripped-history Hero 5.51 vs 5.76 with it, drill 6 had 3.21). Six more
levers are built, tested and off (first-in shove zone, observed opener width, exploitative re-shove price, per-seat
re-shove read, c-bet bluffs by fold-to-c-bet, opens tightened against a re-shove threat); why each failed the
shipping rule is in the entry. Final, 400 seeds x 8, paired vs d917c45: Hero + realistic +0.05, top +0.08, top2
+0.10, Hero + 7 rival1 4.52 (T2a met), holdout +0.11, both payout tables up, base/strong flat. Hero - rival1 -0.03
realistic / -0.02 top (T1 inside noise of 0, not met on the point estimate); Hero - rival2 on top2 -0.47 (T7 not met);
Hero + 7 rival2 3.67 (T2b not met). T3-T6 met; T5 22 READY / 1 PLAYS (two_boards), Hero first on 18 of 23.
**Next lever:** heads-up postflop, read-driven (c-bet frequency, turn play, defence as the preflop caller): the
measurement put it level with the re-shove gap and one margin closed part of it. Then `preflop.reshove_threat` 1.0
(the one lever that moves the rival 2 rooms without touching re-shove calls) re-tested at 400 seeds on realistic.
The rival-2-core fallback is assessed in the entry (cost: latency p99 ~285 us vs T4, fixed 10..0 ICM points, about 7
of 23 variants routable); a hybrid is being built separately in hyperion/hybrid/ and is the owner's call.

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
