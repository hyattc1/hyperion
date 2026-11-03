# Resume here (the climb, if the session or usage stops)

Updated 2026-11-03 13:37 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md (addenda
through 13, then "The climb: batch 6"). Main is pushed after every merge. F as it ships is batch 6 (91014ae,
frozen/B6-91014ae, kit B zip a66eb4b3; SHIP_DIALS in hyperion/compose/bot.py; BATCH6_OFF plays batch 5).

## Batch 6 (frozen 2026-11-03 13:37)
- V-f (H15) + V-h (H18), twist tables only; H21 ACCEPT (exposed card +0.216, knockout bounty +0.111, bounty-aware
  +0.026 up, none down). Gate pass plain, exposed_card, knockout_bounty. Nothing left to do for it.

## Queued, detached (/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/chain.sh, runs after H21; each against batch 5 + V-f + V-h, --runout-term)
- S17's C3 (one stab size with three or fewer alive) on H22: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/c3_h22.md
- V-i (twist decisions as value of information) on H23: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/vi_h23.md
- S16b's O3 (the open-answer read) on H24: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/o3_h24.md
- Each accepted part joins the next batch, which needs judges on fresh judge seeds 30800-31199 (addendum 12).

## Workers running (branches in worktrees under /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal; each commits as it goes)
- S13c done: S7 (S6 + a looseness gate) merged off; queued on H25 after the b23 chain: goal/b24/chain2.sh, output
  goal/b24/s7_h25.md (ends "done"); goal/b24/CHAIN2_DONE when finished.
- S15d done: S15e (the gated stab read) merged off; queued on H26 after S7: goal/b25/chain3.sh, output
  goal/b25/s15e_h26.md; goal/b25/CHAIN3_DONE when finished.
- S20 (climb/s20-three, wt_s20): the structural round's first idea, a three-handed preflop solved for strong tables
  (log docs/drills/climb/s20-log.md on its branch). Diagnostics 11000-11199.
- Drill 11 done (docs/drills/prompt-drill-11.md). Its fixes: H7 (climb/h7-drill11-fixes, wt_h7: night tooling and
  prompts) and V-j (climb/vj-tranche, wt_vj: street-settled pots in our engine and catalog, F's play there;
  diagnostics 12000-12199). H7 and V-j both touch prompt 05: merge H7 first.
- start-vs-now (goal/b18/run.sh, detached): confirm, guards, elite, exploit only; output goal/b18/start_vs_now.md.

## Dated items
- After Menlo Park (Nov 6) and Boston (Nov 9): search the web (X first, LinkedIn sparingly) for what they reveal of
  the twist, the kit's interface and the scoring; record it in the goal log and turn it into a drill or a catalog
  entry the same day. Our regional is Pittsburgh, Nov 12; the climb stops by Nov 11 18:00 ET.

## Held-out sets used
H1-H3 retired; H4-H21 used once each (H20 by the stopped four-part batch 6 run); in use or queued H22-H24; H25 queued for S7, H26 for S15e, H27 for
C3's bonus_card replicate (goal/b23/c3_rep_h27.md); next fresh H28 = 48000-48399. Judge seeds: 30000-30399 (batches 3-6), 30400-30799 (batch 6's replicate); next 30800-31199.

## End deliverables (goal.md)
Final SHIP and zip, a decisions entry, PLAYBOOK and HANDOFF, the last rehearsal on the final ship (drills 7-10 were
on batch 4-5's ship; the last one must run on the final ship), the one-page leaderboard, a list of what we would
still try (docs/research/Edges against strong opponents.md ranks it; the structural round's ideas are in the goal
log 06:20 entry).
