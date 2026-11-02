# Prompt drill 8: Track A on kit F (one Agent per session, int actions), Ghost Hold'em

Date 2026-11-02, T0 16:29:38 EST. Last action minute 20 (16:50): a tool call that never returned; the operator
stopped the agent at 17:56. The climb's second rehearsal, on batch 4's ship (repo pinned at 15df280).

**Set-up.**
- Kit F was built by a fresh organiser agent with no repo access (goal/drill8/kit; 50 engine tests, 1,400 tables
  clean). Interface: one `Agent` for a session of hundreds of tables (import + `Agent()` 2 s once, `new_table` 50 ms,
  `act` 1 ms, `hand_over` 1 ms, all timed; a `hand_over` overrun skips our next decision); the action is one int,
  the chips put in now (no legal list: legality from `owe`, `min_raise`, `stack`); cards are ints 0-51 in our order;
  seats relative (0 is us) with session-wide ids; the history a compact string log; points 16/11/8/6/4/2/1/0, placed
  by chip count at the 200-hand cap; zip at most 5 MB; a static import check (stdlib and the zip's own modules only).
  Handout: `docs/drills/drill8/kitF-README.md`.
- The twist (not in any catalog of ours): **Ghost Hold'em.** Every hand deals a ninth face-down two-card hand, the
  Ghost. A showdown pot whose best hand the Ghost beats goes to nobody: it haunts into the next hand's main pot as dead
  money, won by whoever wins that pot, folds included. One pair loses to the Ghost 56% of the time, two pair 31%
  (`docs/drills/drill8/kitF-ORGANISER-NOTES.md`). A payoff twist that taxes showdowns and pays fold equity.
- Player: a fresh subagent (Opus 5.5) with the pinned repo, the handout zip, PLAYBOOK and prompts 00-05; no
  docs/drills, decisions, HANDOFF or research. Load 10-12 on 8 cores (the climb's runs alongside).
- Its NIGHT.md, adapter, entry, gate seat and rules are in `docs/drills/drill8/`.

## Key numbers

| Checkpoint | Drill 8 | Drill 7 | Target |
|---|---|---|---|
| Rule sheet, axis, FIT VERDICT | minute 1 | 3 | 5 |
| First valid upload | minute 1 (insurance: QQ+/AK all-in, else check/fold) | 8 | 12 (hard 15) |
| Cheap bot gated | minute 6 | 8 | 12 |
| Ship bot gated | **minute 12** | 18 | 40 |
| Stage 5 | 4 candidates measured in the kit's simulator, none better: kept the ship bot | no patch | 50 |
| Questions needing a human | 0 | 0 | 0 |

**The final zip under the real twist** (operator, after the drill: the kit's own simulator, cpu clock, load 12):

| field | ship zip | others |
|---|---|---|
| ship, cheap, the organiser's Ghost-aware bot, tight; duplicate, 400 deals x 8 | **7.64** (7.76, 7.53 ± 0.55) | ghostwise 6.39, tight 5.88, cheap 4.09 |
| ship + ghostwise x3, tight x2, station, random; 400 tables | **8.98 ± 0.50** | ghostwise 7.67, tight 7.06, random 1.34, station 0.54 |

A seat averages 6.0. F with no Ghost patch beats the organiser's Ghost-aware bot by about 1.25 points a table. 22% of
showdowns haunted. Ship timeouts 0.48% of decisions and 0-1 hand-end overruns per seat in 400 tables, at load 12.

## What slowed it down or broke (minutes lost first)

1. **Packaging, about 3 minutes and two failed packages.** (a) The kit's import check failed on rival 3's
   `from kit import Agent` (inside a try) and on the player's entry importing `submission.adapter` (the zip flattens
   `submission/`). The player wrote a `kit.py` stub, which would shadow a real `kit` module on a night whose runner
   has one. (b) `hand_over` over 1 ms (1.47 ms): Hero's hand end under a non-linear points table (the ICM curve, about
   210 us at eight seats at this load, once per Hero). Deferring it into the next `act` pushed act's p99 to 2-3 ms;
   `bot.defer_hand_end(True)` (only the deciding Hero computes) and the `latency` recipe brought p99 to 570 us.
2. **Stage 5 had no simulator but the kit's.** The rule sheet wrote "ENGINE CANNOT REPRESENT the Ghost", and every
   line of our sim was "the variant minus the Ghost". Our hooks can express it (`on_deal` deals the Ghost, `settle`
   takes a beaten pot back, `after_forced` puts the haunt into the next pot as dead money); prompt 01 lists only the
   `Rules` fields, not the extended hooks. The four candidates (survival dials; tighter calls 0.3; passive opens and
   bets; tighter calls 0.1) were each measured against three kit bots, 160-400 tables (± 0.5): tighter calls lost
   0.9 and 0.24, passive lost 0.5, survival level. None kept.
3. **Tests flaky under load.** The pinned repo's timing tests (setup cost, bestiary budgets) failed at load 11; re-run
   alone they passed.
4. **A tool call that never returned** (minute 20, a kit sim; harness, not our tooling). The ship bot was already in.

## Fixes that follow

- **Done (a46f958).** pack.py drops the red-team rivals' `kit` import in the packed copy (they subclass `object`, as
  with no kit) and prints an `imports` line naming any module outside the stdlib and the package.
- **Prompt 01 and 02.** "ENGINE CANNOT REPRESENT" only after checking the extended hooks (settle, after_forced,
  charges_dead, next_card, on_fold, score_splits, on_bust); the entry imports its adapter as a sibling module.
- **V-g (robustness, payoff twists that move a pot).** Ghost Hold'em as a variant file in our hooks; check its haunt
  rate against the kit's (22% of showdowns); then two questions: does our sim's verdict on the four Stage 5
  candidates match the kit's (does our sim transfer to an organiser's engine), and does the general path (prepared
  twist tables, generic aware opponents) find the Ghost's edges (haunt-hand steals, thinner showdown value) by itself.
- **Hand end under non-linear points.** The base's Hero and the hero member compute the same curve; the second hits
  the ICM cache, so sharing it saves only the bookkeeping. Measure on a quiet box before changing anything.
