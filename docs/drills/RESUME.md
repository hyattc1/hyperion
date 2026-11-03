# Resume here (the climb, if the session or usage stops)

Updated 2026-11-03 12:35 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md (addenda
through 13). Main is pushed after every merge. F as it ships is still batch 5 (frozen/B5-3aac34d, kit B zip
cbf2ccb3; SHIP_DIALS in hyperion/compose/bot.py).

## Batch 6 (not yet frozen)
- The four-part batch 6 failed the judges (addendum 12: outside, pooled -0.0032 ± 0.0021). Batch 6 is now
  V-f (H15) + V-h (H18), twist-only, identical on every judge field by construction: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b22/b6p.json.
- Its combined check: H21, variants and aware, --runout-term: output /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b22/b6p_h21.md (ends "done").
- To freeze when H21 accepts: on climb/batch6 (worktree /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/wt_b6, SHIP_DIALS holds all four parts) remove S6's and
  S15c's dials from SHIP_DIALS and from BATCH6_OFF's tests, or rebuild the branch with V-f and V-h only; re-run the
  digest proof (BATCH6_OFF plays batch 5) and the tests; merge; tools/pack.py --slim and tools/gate.py --kit b
  --tables 40; decisions entry, leaderboard, HANDOFF, log (batch 5's entry is the template). No judge run is needed:
  every judge field is plain hold'em, where V-f and V-h are identical (say so in the entry).

## Queued, detached (/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/chain.sh, runs after H21; each against batch 5 + V-f + V-h, --runout-term)
- S17's C3 (one stab size with three or fewer alive) on H22: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/c3_h22.md
- V-i (twist decisions as value of information) on H23: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/vi_h23.md
- S16b's O3 (the open-answer read) on H24: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b23/o3_h24.md
- Each accepted part joins the next batch, which needs judges on fresh judge seeds 30800-31199 (addendum 12).

## Workers running (branches in worktrees under /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal; each commits as it goes)
- S13c (climb/s13c-gate): S6's gate tightened on tuning fields only, so it fires close to never against non-exploiters.
- S15d (climb/s15d-gate): S15c's stab-read gate, the same.
- start-vs-now: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b18/start_vs_now.md (the starting F against batch 5 on H17, for the leaderboard).

## Held-out sets used
H1-H3 retired; H4-H21 used once each (H20 by the stopped four-part batch 6 run); in use or queued H22-H24; next
fresh H25 = 45000-45399. Judge seeds: 30000-30399 (batches 3-6), 30400-30799 (batch 6's replicate); next 30800-31199.

## End deliverables (goal.md)
Final SHIP and zip, a decisions entry, PLAYBOOK and HANDOFF, the last rehearsal on the final ship (drills 7-10 were
on batch 4-5's ship; the last one must run on the final ship), the one-page leaderboard, a list of what we would
still try (docs/research/Edges against strong opponents.md ranks it; the structural round's ideas are in the goal
log 06:20 entry).
