# Resume here (the climb, if the session or usage stops)

Updated 2026-11-04 15:20 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md (addenda
through 13, then "The climb: batch 6" and "The climb: batch 7"). Main is pushed after every merge. F as it ships is batch 7 (038c3f0,
frozen/B7-038c3f0, kit B zip 51c37f02; SHIP_DIALS in hyperion/compose/bot.py; BATCH7_OFF plays batch 6). Gate pass
(re-run at load 4): batch 7's zip is the known-good upload.
Identity reference for worker branches: goal/idchk34/post (batch 7's F).

## Batch 6 (frozen 2026-11-03 13:37)
- V-f (H15) + V-h (H18), twist tables only; H21 ACCEPT (exposed card +0.216, knockout bounty +0.111, bounty-aware
  +0.026 up, none down). Gate pass plain, exposed_card, knockout_bounty. Nothing left to do for it.

## Held-out results this round (goal-log 22:15)
- V-i (H23) ACCEPT, c6 (H29) ACCEPT: both twist-only, both join batch 7. S7 (H25) ACCEPT (plain hold'em, heads-up
  and three-handed against exploiter 2 only). S15e (H26) ACCEPT (plain hold'em, short-handed).
  C3h (H28) ACCEPT: joins batch 8 (exploiter 2 heads-up +0.225; overlaps S7's spots, so batch 8's combined check). O3 (H24) REJECT. C3 rejected (H27).
- S20's R5 (H30) REJECT on realistic -0.003 ± 0.002 (all five strong cells up); R6 (button only) ACCEPT on H32:
  joins batch 8 (merge climb/s20-r6, 2cac7e3; keep S7's route, goal-log R6 entry). If a later S20 version passes: climb/b7-scope (863f9f5) has the per-route scoping.
- Batch 7 needs judges on fresh judge seeds 60000-60399 (addendum 12) only if a plain hold'em part joins it.

## Paused 2026-11-04 ~11:40 ET for the owner's hardware change (CPU and RAM): restart here
Nothing is lost: everything decided is committed and pushed; the scratchpad (goal/ = /tmp/claude-1000/...
/scratchpad/goal, on the root disk, not a tmpfs) is also copied to /home/connor/dev/hyperion-goal-backup/goal
(without the result caches accept_* and the git worktrees wt_*, which are rebuilt from branches).
1. Check: `nproc`, `free -g` (WSL takes half the RAM unless C:\Users\Connor\.wslconfig sets memory=); `git -C
   ~/dev/hyperion status`; `ls goal/` still there (else copy back from the backup and re-add worktrees).
2. O8 passed its screen (14:00; goal-log 14:05) and is on H35 on top of batch 8: climb/b8-o8 (goal/wt_b8o8 = batch 8 +
   main + climb/s21-o8), goal/b35/run.sh (identity first, goal/idchk36.md against idchk34, goal/b35/identity.txt; then
   o8_h35.md; RUN_DONE). If no RUN_DONE, re-run it as is (cached chunks in goal/idchk36 and goal/accept_b8o8 stand;
   delete any chunk JSON that fails to load). If it passes, O8 joins batch 9 (not batch 8).
2b. S22 (the river-bet read, climb/s22-river 3627f1f) passed its screen under --aim exploit (exploit4_hu +0.123 ± 0.054
   UP, nothing down) and is on H36 on top of batch 8: climb/b8-s22 (goal/wt_b8s22 = batch 8 + main + S22),
   goal/b36/run.sh (identity first: goal/idchk37.md, goal/b36/identity.txt; then s22_h36.md; RUN_DONE). Re-run as is
   if no RUN_DONE (caches goal/idchk37, goal/accept_b8s22). If it passes, S22 joins batch 9 with O8.
2c. Paused 15:20 ET (second pause). On restart re-run, in this order, each as is (cached chunks stand; delete any
   chunk JSON that fails to load first: a shutdown can cut one): goal/b34/run.sh (H34 is done and ACCEPTED, goal-log
   15:10, so it replays from cache in seconds; then the judges 60400-60799, then timing), goal/b35/run.sh (O8, H35),
   goal/b36/run.sh (S22, H36). Workers: 3 + 2 + 2, more with the new cores. The batch 8 freeze staging worker
   (climb/batch8-freeze, goal/wt_b8f) was stopped: resume from its branch's last WIP commit (SHIP_DIALS + BATCH8_OFF,
   identity both ways goal/idchk38 and idchk39, suite, setup time); the brief is in the goal log's 15:10 entry. The
   backup (~/dev/hyperion-goal-backup/goal) now holds the result caches too (accept_*); /tmp is not cleared at boot
   (no systemd in this WSL).
3. Batch 8 on climb/batch8 (goal/wt_b8, ac1f18c: O5 merged, candidate C3h + R6 scoped + O5, identity 14/14): ACCEPTED on
   H34 (15:10); its combined check runs as goal/b34/run.sh (outputs b8_h34.md, judges.md, lat_*; RUN_DONE): if no RUN_DONE, re-run it
   as is (cached chunks in goal/accept_b8 stand; delete any chunk JSON that fails to load). It is the check on H34 (54000-54399) against
   batch 7, every stage, --aim strong, runout term; judges 60400-60799 (13 cells now, outside_c included); timing;
   then SHIP_DIALS + BATCH8_OFF, identity, suite, pack, gate, freeze, docs (batch 7's entry is the template).
   If O8 passes its screen, it goes to its own held-out set (H35) and joins batch 9, not batch 8.
4. Workers to resume (agents, by their logs on their branches): H1 (climb/s20-h1: settle the S7 coexistence rule
   and R6's exploiter-1 guards, full solve, screen); exploiter 4 is wired in (addendum 15); S22 (climb/s22-river,
   goal/wt_s22, log docs/drills/climb/s22-log.md): exploiter 4's river over-fold, resume from its log.
5. Re-time on the quiet new box (latency.py, gate) and keep the rehearsal on the final ship for the end.

## Batch 8 (being composed)
- climb/batch8 (worktree goal/wt_b8): main + climb/s20-r6; candidate docs/drills/climb/batch8-candidate.json (C3h + R6
  scoped, S7's route kept). O5 ACCEPTED on H33: merge climb/s21-o5 (2de5070) into climb/batch8 and add its dials. Then: combined check on a fresh
  held-out set (H34 = 54000-54399) against batch 7, every stage, --aim strong; judges 60400-60799; timing; freeze as batch 7.

## Queued or running, detached (each against batch 6, --runout-term)
- Batch 7's combined check (V-i + c6 + S7 + S15e) on H31, then judges 60000-60399, then timing: goal/b29/run.sh,
  outputs goal/b29/b7_h31.md, judges.md, lat_*.txt; RUN_DONE. Then merge climb/batch7 (6fddb13, staged: SHIP_DIALS + BATCH7_OFF, identity 14/14, tests fixed),
  pack, gate, freeze, docs.

## Workers running (branches in worktrees under /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal; each commits as it goes)
- S13c done (S7 merged off), S15d done (S15e merged off).
- S20 done (climb/s20-three, d046fef, not merged; log docs/drills/climb/s20-log.md on its branch): R5 on H30.
- S21 done: rejected on its screen (O3 parked). O5 (2de5070) passed its screen: on H33 after C3h (goal/b31/run.sh,
  output goal/b31/o5_h33.md, RUN_DONE). O6 (climb/s21-o6, the non-blind seats' fold read) with the same worker.
- Drill 11 done (docs/drills/prompt-drill-11.md); H7 and V-j merged. Future organiser briefs exclude tranche_holdem.
- start-vs-now done (the leaderboard's "Since the start" table).

## Dated items
- After Menlo Park (Nov 6) and Boston (Nov 9): search the web (X first, LinkedIn sparingly) for what they reveal of
  the twist, the kit's interface and the scoring; record it in the goal log and turn it into a drill or a catalog
  entry the same day. Our regional is Pittsburgh, Nov 12; the climb stops by Nov 11 18:00 ET.

## Held-out sets used
H1-H3 retired; H4-H21 used once each (H20 by the stopped four-part batch 6 run); H22-H24 used (C3, V-i, O3); H25 used (S7), H26 used (S15e), H27 for
C3's bonus_card replicate (down: C3 rejected), H28 used (C3h), H29 used by V-j's c6, H30 used by S20's R5, H31 for batch 7's combined check, H32 used (R6), H33 used (O5), H34 for batch 8's combined check, H35 for O8 (on batch 8), H36 for S22 (on batch 8); next fresh H37 = 57000-57399
(worker briefs say held-out is 20000-49999: widen it to 20000-59999 in the next brief). Judge seeds: 30000-30399 (batches 3-6), 30400-30799 (batch 6's replicate); next 60000-60399 (30800-31199 would overlap H11's 31000-31399), then 60400-60799 for a replicate.

## End deliverables (goal.md)
Final SHIP and zip, a decisions entry, PLAYBOOK and HANDOFF, the last rehearsal on the final ship (drills 7-10 were
on batch 4-5's ship; the last one must run on the final ship), the one-page leaderboard, a list of what we would
still try (docs/research/Edges against strong opponents.md ranks it; the structural round's ideas are in the goal
log 06:20 entry).
