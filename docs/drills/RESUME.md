# Resume here (the climb, if the session or usage stops)

Updated 2026-11-04 15:20 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md (addenda
through 13, then "The climb: batch 6" and "The climb: batch 7"). Main is pushed after every merge. F as it ships is batch 7 (038c3f0,
frozen/B7-038c3f0, kit B zip 51c37f02; SHIP_DIALS in hyperion/compose/bot.py; BATCH7_OFF plays batch 6). Gate pass
(re-run at load 4): batch 7's zip is the known-good upload.
Identity reference for worker branches: goal/idchk34/post (batch 7's F).


## 2026-11-05 12:10: PAUSED for a WSL shutdown (owner's request). Start here.
Nothing is running. The known-good upload is still batch 8 + G1 (frozen/B8G-e370fb3, zip 94136077); nothing was frozen or merged since. Deadlines are unchanged (goal text: docs/drills/goal-condition.txt).
In order, on resuming:
1. Re-arm the timers, which died with the session: Nov 7 08:00 ET and Nov 10 08:00 ET reveal searches, 3-hour progress check. If either time has passed, search at once.
2. Re-run unchanged: goal/b42/run.sh (S25 on H42 on top of batch 9) and goal/b43/run.sh (batch 9 combined on H43). Cached chunks stand (674 and 499 at the pause; every chunk file loaded). First delete any chunk JSON that fails to load. Do not change the code in goal/wt_s25 or goal/wt_b9.
3. Resume the workers with SendMessage if this session was resumed; otherwise start a fresh agent from the log and branch.
   - Elite 6 (a79bb0ee6f32ef3d9, goal/elite/e6) and elite 7 (a569f48959aa8e0e9, goal/elite/e7): held-out judges in the making, about 2h of their 2.5h used, stopped mid-test. Give each 30 minutes to finish and deliver rival_bot.py, NOTEBOOK.md, FROZEN.md5, harness run. A fresh agent gets no repo access and the same brief. Do not read their notebooks or code beyond wiring them.
   - S26 (a58537e12e6778722, climb/s26 e0d5aba, goal/wt_s26; log docs/drills/climb/s26-log.md): re-jam read v2 passes its coin; H1's reach and the three-alive read were on their fit coins, which were stopped and must be re-run.
   - G2 (a94fdc3c575eb4c63, climb/g2-bare 7e0f7fb, goal/wt_g2; log docs/drills/climb/g2-log.md): root cause found, identity passes, dial off. Its timing run was stopped at load about 20: discard it and re-run at a stated load. Points runs have not started.
4. When S25's verdict is in, run judges on 70800-71199 on what would ship, then freeze per PLAYBOOK. Next fresh held-out H44 = 85000-85399. Next plan after the two builds are wired: goal log "10:15" and "10:25" entries (out_reads opened as a study opponent; the guards are fixed in advance).
Caches: goal/ on /tmp is on the real disk and has survived reboots. Backup at ~/dev/hyperion-goal-backup (goal/ and frozen/, taken at the pause). Do not clear /tmp/claude-1000.
Owed from staging: addendum 17 text in docs/drills/climb/s24-log.md goes in docs/decisions.md when batch 9 merges.

## Restarted 2026-11-04 21:55 ET on the new box
The new /goal's deadlines: last bot change Nov 10 18:00 ET; final rehearsal and deliverables Nov 11 12:00 ET. Section 2c's
runs were restarted (workers 6 + 4 + 4); the goal log's newest entry says what else is live. Agents from session e2efc890
cannot be messaged; resume them from their logs and branches. Outside builds in goal/outside4, drill 12 in goal/drill12.

## 2026-11-05 07:20: the known-good upload is batch 8 + G1 (frozen/B8G-e370fb3, zip 94136077)
Main 92b8e45 has batch 8, H8 and G1. Accepted for batch 9: S22 (H36), H1 (H38), B18 (H39). S24 rejected on H40; its shove read alone on H41 (82000-82399; goal/b41/run.sh). Staging: climb/batch9, goal/wt_b9. Next fresh held-out H42 = 83000-83399, +1000 each. Next judge seeds 70800-71199. Final rehearsal's kit is ready and unseen: goal/drill13/kit (One-Shot Hold'em); keep its organiser notes from the player. Timers for the reveal searches live in the session: if it restarts, Nov 7 08:00 and Nov 10 08:00 ET must be re-armed. Plan: `strong_room` window recipe from O8 after batch 9.

## 2026-11-04 23:30: batch 8 is the ship (frozen/B8-77c5ea6, zip 0d07654e)
Merged to main at eac472a. Live on branches, each with its log: climb/g1-governor (G1, the whole-call governor; worktree
goal/wt_g1, docs/drills/climb/g1-log.md), climb/outside-d (o9, o10, o11 as judges; goal/wt_od), climb/s20-h1 (H1's screen). Drill 12:
goal/drill12 (kit J Trailing Stop Hold'em; player on eac472a). Exploiter 5: goal/exploiter5 (target goal/wt_target8). O8 and S22:
goal/b35, goal/b36. Identity reference for later branches is now batch 8's F. Next fresh held-out H37 = 57000-57399; judge seeds
70000-70399 used by outside-d, next 70400-70799.

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
   identity both ways goal/idchk38 and idchk39, suite, setup time); the brief is goal/b8f_brief.md. Its WIP commit
   9bc51e8 (pushed): SHIP_DIALS + BATCH8_OFF done, identity (a) PASS (9 of 9 rows, base and cand both BATCH8_OFF as
   idchk33 did). Left: identity (b) (re-run goal/idchk38.sh: the wt_b8ref half with --cand goal/b32/b8.json into
   goal/idchk39ref, then the wt_b8f half with --cand {} into goal/idchk39; compare cand columns), remove wt_b8ref,
   the suite (expected to fail and move onto BATCH8_OFF: test_s20_three.py:202, test_s13_short.py's route set,
   test_s17_stab_size.py, test_s21_o5.py and test_s16b_open.py's {} reference), setup time, a final commit.
   **Pack caveat (found 15:25):** tools/pack.py ships only the top level of tables/*.json, so it leaves out
   tables/extra/short_3b.json (3.0 MB, R6's three-handed table); the specialist's loader then returns None and R6
   silently does not play in the package. Batch 7's zip is unaffected (it uses no extra table). At batch 8's pack:
   include the file, and make a missing table that a shipped dial names fail loudly (pack or gate), not silently;
   measure setup time and size with it included. The
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
- Drill 12 done (docs/drills/prompt-drill-12.md); fixes on climb/h8-drill12-fixes. Future organiser briefs exclude trailing_stop.
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
