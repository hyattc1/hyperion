# Resume here (the climb, if the session or usage stops)

Updated 2026-11-03 23:10 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md (addenda
through 13, then "The climb: batch 6"). Main is pushed after every merge. F as it ships is batch 6 (91014ae,
frozen/B6-91014ae, kit B zip a66eb4b3; SHIP_DIALS in hyperion/compose/bot.py; BATCH6_OFF plays batch 5).

## Batch 6 (frozen 2026-11-03 13:37)
- V-f (H15) + V-h (H18), twist tables only; H21 ACCEPT (exposed card +0.216, knockout bounty +0.111, bounty-aware
  +0.026 up, none down). Gate pass plain, exposed_card, knockout_bounty. Nothing left to do for it.

## Held-out results this round (goal-log 22:15)
- V-i (H23) ACCEPT, c6 (H29) ACCEPT: both twist-only, both join batch 7. S7 (H25) ACCEPT (plain hold'em, heads-up
  and three-handed against exploiter 2 only). S15e (H26) ACCEPT (plain hold'em, short-handed). O3 (H24) REJECT. C3 rejected (H27).
- S20's R5 (H30) REJECT on realistic -0.003 ± 0.002 (all five strong cells up); R6 (a gate from a realistic-room
  diagnosis) with S20's worker. If a later S20 version passes: climb/b7-scope (863f9f5) has the per-route scoping.
- Batch 7 needs judges on fresh judge seeds 60000-60399 (addendum 12) only if a plain hold'em part joins it.

## Queued or running, detached (each against batch 6, --runout-term)
- Batch 7's combined check (V-i + c6 + S7 + S15e) on H31, then judges 60000-60399, then timing: goal/b29/run.sh,
  outputs goal/b29/b7_h31.md, judges.md, lat_*.txt; RUN_DONE. Then freeze (SHIP_DIALS + BATCH7_OFF, tests, pack, gate).
- C3h on H28 (running since 01:59): goal/b26/chain4.sh, output goal/b26/c3h_h28.md, CHAIN4_DONE.

## Workers running (branches in worktrees under /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal; each commits as it goes)
- S13c done (S7 merged off), S15d done (S15e merged off).
- S20 done (climb/s20-three, d046fef, not merged; log docs/drills/climb/s20-log.md on its branch): R5 on H30.
- S21 (climb/s21-o3s, goal/wt_s21): O3 behind the strong-table read (O3 was up on all five strong cells on H24 and
  down in the realistic room); survey on 11200-11399, screen 10000-10199 --aim strong.
- Drill 11 done (docs/drills/prompt-drill-11.md); H7 and V-j merged. Future organiser briefs exclude tranche_holdem.
- start-vs-now done (the leaderboard's "Since the start" table).

## Dated items
- After Menlo Park (Nov 6) and Boston (Nov 9): search the web (X first, LinkedIn sparingly) for what they reveal of
  the twist, the kit's interface and the scoring; record it in the goal log and turn it into a drill or a catalog
  entry the same day. Our regional is Pittsburgh, Nov 12; the climb stops by Nov 11 18:00 ET.

## Held-out sets used
H1-H3 retired; H4-H21 used once each (H20 by the stopped four-part batch 6 run); H22-H24 used (C3, V-i, O3); H25 used (S7), H26 used (S15e), H27 for
C3's bonus_card replicate (down: C3 rejected), H28 for C3h (goal/b26/chain4.sh, output
goal/b26/c3h_h28.md, CHAIN4_DONE), H29 used by V-j's c6, H30 used by S20's R5, H31 for batch 7's combined check; next fresh H32 = 52000-52399
(worker briefs say held-out is 20000-49999: widen it to 20000-59999 in the next brief). Judge seeds: 30000-30399 (batches 3-6), 30400-30799 (batch 6's replicate); next 60000-60399 (30800-31199 would overlap H11's 31000-31399), then 60400-60799 for a replicate.

## End deliverables (goal.md)
Final SHIP and zip, a decisions entry, PLAYBOOK and HANDOFF, the last rehearsal on the final ship (drills 7-10 were
on batch 4-5's ship; the last one must run on the final ship), the one-page leaderboard, a list of what we would
still try (docs/research/Edges against strong opponents.md ranks it; the structural round's ideas are in the goal
log 06:20 entry).
