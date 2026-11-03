# HANDOFF (written 2026-10-31, for a new session picking this up)

Start here. Then read `PLAYBOOK.md` and the last five entries of `docs/decisions.md`. Everything below
is either committed or named as lost-if-killed.

## State in one paragraph

**The climb is running** (since 2026-11-01 20:20 ET; brief `docs/prompts/goal.md`, plan and frozen protocol
`docs/drills/goal-plan.md`, running log `docs/drills/goal-log.md`, one-page leaderboard `docs/drills/goal-leaderboard.md`;
our regional is Pittsburgh, Nov 12; it stops by Nov 11 18:00 ET). The ship bot is still the composite F
(`hyperion/ship.py`: `SHIP = "composite"`, `DIALS = {}`), now batch 5 (3aac34d, SHIP_DIALS in
hyperion/compose/bot.py): the governor (batch 2), variant play (batch 3), the 3-bet defence and kit fixes (batch
4), and batch 5's strong-table route (elite1 plays opened pots preflop at tables that re-raise), the bet-size read,
the second exploiter's fixes (hold'em only) and twist play against twist-aware bots. Held-out against batch 4:
night +0.096, mirror +0.241, every exploit cell up. F is first on every judge field and first in the elite room.
Open gaps: exploiter 2 still wins heads-up (9.20 to 7.80) and three-handed (8.23 to 7.35): the short-handed
specialist (S13, `short_route`, off) is in held-out confirmation; V-f's per-family twist dials (off) too.
`BATCH5_OFF` (compose/bot.py) plays batch 4 from this tree. Every measurement of F goes through `tools/climb_accept.py`
(never `tools/swap.py paired` specs, which skip SHIP_DIALS); `--aim exploit|strong` for the addenda 6 and 8 rules.
Frozen fallback zips are in `frozen/` (git-ignored), listed with their sha256 in the leaderboard. Fallbacks are one word
away: `python -m hyperion.ship --bot hybrid3_x` or `--bot hero`. Decisions entries: "The climb: protocol addenda and
batches 1-2", "The climb: batch 3 (variant play) and addenda 7-8", "The climb: batch 4", "The climb: batch 5". Workers run on `climb/*` branches in worktrees under the session scratchpad; the coordinator merges.

History: Hero was tuned to finish first against every field we wrote, then a red-team rival built blind beat it; the
plan changed to choosing the best core behind Hero's shell (below), and then to combining the best sections.

## What was running when this was written, and how to relaunch each

**Plan change, 2026-11-01 04:00 ET (owner asked "why not just switch to the rival's code?").** Stop tuning
Hero's decision core for 0.1-point gains. Choose the best *core* behind Hero's shell (adapter, `Rules`,
23 variant hooks, SafeBot, tooling) and ship that. Candidates: Hero; hybrid with rival 2's core (built,
being measured); hybrid with rival 3's core (next, by the hybrid agent once v1 is written up). Rival 3 then
stops being a holdout; rival 4 (built blind, no assigned philosophy, scratchpad `redteam4/`) becomes the
judge. Winner = best on realistic, top and the rival-4 field, all 23 variants READY, timeouts no worse than
Hero's, robust across the three payout tables. The owner makes the final call on what ships.

**Launched 2026-11-01 13:45 ET, all finished by 18:00 ET (owner: "fully execute everything end-to-end").** Goal: the best possible base
for the night. Eight agents launched from the coordinating session; each commits per step. Relaunch any that died
from its brief below and `git log`.
- Base switch: DONE (shipped hybrid3_x until the composite replaced it at 17:30). Make hybrid3_x the shipped bot (lazy core imports, one ship switch used by pack/gate/latency/adapter,
  Hero one flag away, night-of dials working on the rival 3 core, rehearsal on a fake kit). Decisions entry "Ship
  hybrid3_x as the base". Owns hyperion/hybrid/, tools/pack.py, tools/gate*.py, tools/latency.py, hyperion/drills/,
  docs/prompts/, PLAYBOOK.md, docs/packet/.
- Field: a `night` field (each table draws 7 opponents from a weighted pool like a real regional's: one-hour
  agent-built bots, weak and broken archetypes, decent bots, rivals 1-3) and `night_hard`; the per-section skill
  profile (tools/skill_profile.py, docs/drills/skill-profile.md); rival 5 integrated as the second judge (`judge2`,
  `judge2_night`). Decisions entry "Night field and skill profile". Owns hyperion/sim/bestiary.py, hyperion/sim/rivals/,
  hyperion/sim/field/, docs/drills/redteam/, docs/drills/field/.
  **DONE (15:10).** night / night_hard / night0, the four persona bots, both Track B bots, and rival 5 with judge2 and
  judge2_night are in. Model mode is fixed-speed, so every night run replays exactly. Night ranking at 200 x 8: Hero
  5.75, hybrid3_x 5.75 (-0.01), hybrid_x 5.60, rival3 5.54. night_hard: Hero 5.39, hybrid_x 5.38, hybrid3_x 5.23
  (-0.17 ± 0.13, lost to rivals 1-3 equally, not to the untuned persona bots). Profile and chip-flow tables:
  docs/drills/skill-profile.md.
- Compose: sections (hyperion/compose/sections.py), a composite bot that routes each section to the best member
  (all members shadow every decision), the section swap matrix, greedy combination, a guarded hill climb, one final
  measurement on both judges, ship only if it beats hybrid3_x. Log docs/drills/compose-log.md; entry "Composite bot".
  **DONE (17:30), SHIPPED: `SHIP = "composite"` (d32d629).** It plays rival 3's core preflop and Hero postflop and
  short facing a raise, with the layer at a fold read of 0.4 and Hero's postflop call margin at 0.20. Measured once at
  400 x 8, it beats hybrid3_x and Hero beyond noise on night (+0.28 / +0.33, held-out seeds), night_hard, realistic,
  top, judge, judge2 and judge2_night, and is ahead on judge_top (+0.09 inside noise / +0.17). 23/23 READY, gate PASS
  on kits A and B, strict timeouts level with hybrid3_x. `--bot hybrid3_x` / `--bot hero` are the fallbacks. The
  owner's other bot won no section.
- Scratch builds (session scratchpad, no repo access): four bots built the way typical teams will build them
  (`field/f1_default`, `f2_montecarlo`, `f3_charts`, `f4_pushfold`, 60 minutes each) and rival 5, a fresh blind judge
  (`redteam5/`). Each is frozen when FROZEN.md5 appears; the field agent brings them into the repo.
- The owner's other bot is tested only as a black box from snapshot copies; it never enters the repo, and a section it
  wins is reported to the owner, not shipped.

**Running as of 2026-11-01 00:30 ET (three Opus agents, launched from the coordinating session):**
- Timeout and dead-seat exploit pass: DONE (section 1). The aggression pass before it is DONE too (entry "Mid-phase aggression pass").
- Rival 3: integrated as `rival3`, the holdout (never tuned on); on `holdout` Hero - rival3 -0.74 ± 0.16.
- Drill 5 follow-ups (item 4 below), then drill 6: Track A on kit A with toss_or_holdem, on a pinned copy.
- Gate the packaged bot: DONE. `tools/gate.py` plays the upload zip itself, paired against in-sim Hero, and
  the Stage 2 and Stage 4 gates run it before every upload. Drill 6's upload fails it (-2.46 ± 0.76), and so
  do drills 1, 2 and 4's (decisions entry "Gate the packaged bot").
- Hybrid candidate: DONE. `hybrid` (rival 2's core behind Hero's shell, `hyperion/hybrid/`) vs frozen Hero 7e51197:
  holdout -0.12 ± 0.13, realistic -0.11 ± 0.13, top +0.27, top2 +0.45; 1.5-3x Hero's timeouts. Recommendation: keep
  Hero, the switch is the owner's call (decisions entry "Hybrid candidate", log `docs/drills/hybrid-log.md`).
- Hybrid 3 candidate: DONE. `hybrid3` / `hybrid3_x` (rival 3's core behind Hero's shell, without / with the layer)
  vs Hero 0d660dc (current strategy) with the layer: hybrid3_x realistic +0.17, judge +0.18, top +0.18, top2 +0.22, 23/23
  READY, 1.4x Hero's timeouts (hybrid3 1.0x). Provisional; the final comparison decides (decisions "Hybrid 3 candidate").
- Final core comparison: DONE. hybrid3_x (rival 3's core + the exploit layer behind Hero's shell) is first or second on every
  field and ahead of Hero on all of them (judge +0.14, realistic +0.10, top +0.14, top2 +0.14, timeouts +0.11), 23/23 READY,
  timeouts level with Hero's on a quiet host. hybrid_x wins the strong rooms and loses the judge and realistic fields
  beyond noise. Recommendation: ship hybrid3_x after the lazy-import fix and a gate pass; **the owner decides**
  (decisions entry "Final core comparison", log `docs/drills/final-comparison-log.md`).
- Rival 4 (the judge): integrated as `rival4`, fields `judge` and `judge_top`, hero seat swapped by `judge@hybrid3` etc.;
  never tuned on; measured once in the final comparison (decisions entry "Rival 4 in the pool (the judge)").

- The ship switch: DONE; the composite now ships (above). `hyperion/ship.py` (`SHIP = "hybrid3_x"` at the time, `DIALS = {}`)
  names the ship bot for the entry, pack, gate, latency and `--field <field>@ship`; `--bot hero` restores Hero;
  `SHIP = "composite"` ships the composite. The compose agent's final measurement sets SHIP (hybrid3_x ties Hero on
  `night`, trails on `night_hard`, leads on realistic and the judges). Lazy imports (build 1.5 s -> 0.3 s), r3.* dials
  for rival 3's core (bit-identical at defaults), window recipes that resolve for whichever bot the switch names,
  hybrid3_x and Hero zips both gated PASS on kit A. The kit B rehearsal found that the gate failed every bot on kits with
  no action log; fixed (`--kit-log`). Open: without a log both bots lose 0.6-0.9 points a table; an adapter that infers
  the missing actions is the next lever (decisions entries "Ship hybrid3_x as the base" and its addendum).
- Action-log inference: DONE. On a kit with no log, or a partial one, every adapter rebuilds the hand's log from the
  states (`hyperion/drills/infer_history.py`; the night-of agent writes no history code). It wins back 86-95% of the
  0.56-0.92 points a table the missing log cost (realistic Hero +0.66, hybrid3_x +0.86; night +0.48, +0.53; 200 x 8,
  paired). Precision 100%; recall 100% at decisions, preflop 75% after our last one. Gate PASS on kits B (-0.06 ±
  0.34) and A (-0.20 ± 0.55); `--kit-log no` now pairs against the rebuild, and a zip without it fails (-0.80). With
  it hybrid3_x leads Hero on a no-log kit as with the log (realistic +0.14 ± 0.12, night level). Decisions entry
  "Infer the action log on kits without one".

Agents commit as they finish tasks. If one was killed, `git log` shows what landed; the rest is below.

### 1. Timeout and dead-seat exploit pass: DONE (2026-11-01).

The decisions entry is "Timeout and dead-seat exploit pass"; every table is in docs/drills/exploit-pass-log.md.
(The aggression pass's entry, "Mid-phase aggression pass", stands.)

**Timeouts can now be modelled.** Every timeout bot in the bestiary timed out on the wall clock, so strict screens
followed the host. Engine mode `model` (`--mode model` in the runner and `tools/sweep.py`; default off) folds only the
bots that report a modelled cost over 1 ms:
- Monte Carlo rollouts are costed from a calibration on this box;
- the sleeping bots report their sleep and skip it;
- no bot is folded on the wall clock.

Tables replay exactly. Against the wall clock it is within 0.2 points of timeout rate for the sleeping bots and 2
points lower for the honest Monte Carlo, which the model's quiet-host calibration explains. New: `timeout_burst`
(recovers between outages) and the `timeouts` field. Screen with `--mode model`.

**Shipped (1957983; the final commit is 8a7af98).** `hyperion/strategy/exploit.py` is a layer any core can call:
`observe(obs)`, `hand_end(result)`, `override(obs, proposed) -> Action | None`, or the `Exploited(inner)` wrapper. The
call pattern is in the entry. It reads each seat in three cells (preflop, postflop heads-up, postflop multiway): the
streak of passive decisions since its last call or raise, and a decayed fold rate. Hero's Config ships
`ShippedExploitParams`:
- bet a third of the pot when checked to by seats that fold, never into a seat that has just called;
- steal any two into dead seats;
- steal any two when the fold reads behind multiply to 0.7.

`ExploitParams()` is the neutral layer. The keys `exploit.bet_checked` false, `exploit.steal` false and
`exploit.steal_min_fold` 0 give 7e51197's play, bit-identical. Isolation and Hero's `dead_shift` are built, tested and
off.

**Final, 400 x 8, paired vs 7e51197.** model / strict, Hero's paired change: realistic +0.41 / +0.44, timeouts +0.38 / +0.39, top +0.13 / +0.20, top2 +0.18 / +0.21, base +0.12, strong +0.20, both payout tables up (+0.70, +4.6). Hero - rival1 +0.50 on realistic and +0.17 / +0.14 on top (**T1 met**). Hero - rival2 on top2 -0.26 / -0.20 (T7 met on the strict point estimate only). Hero + 7 rival1 4.65 (T2a met); Hero + 7 rival2 3.63 (-0.08, T2b not met). T3-T6 met: act() p99 40 us; **23 of 23 variants READY**, Hero first on 22. Holdout, measured once: Hero - rival3 -0.41 -> **+0.15** on `holdout`, -0.29 -> +0.01 on `top3` (strict +0.14, +0.12). Rival 3 stops being a holdout with the core comparison.

**Next lever:** a blind-specific fold-to-steal read for `steal_min_fold`. Against seven rival 2s the fold-read steal
loses 1.7 bb a table: rival 2 folds most raises but defends its blinds. Items 4 and 5 of the brief were cut when the
plan moved to choosing the core. For the core choice: the hybrids' comparisons so far are against the frozen Hero
7e51197, and Hero at 8a7af98 is that Hero plus the layer. `hybrid_x` / `hybrid3_x` put the same layer in front of
each hybrid: +0.25 / +0.33 for the rival 2 core and +0.13 / +0.18 for the rival 3 core on realistic / timeouts, about +0.05 on top.

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
