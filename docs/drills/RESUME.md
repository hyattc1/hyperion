# Resume here (the climb, if the session or usage stops)

Written 2026-11-03 05:53 ET. Everything decided is in docs/drills/goal-log.md (newest last) and docs/decisions.md. Main is pushed
after every merge. F as it ships is batch 5 (frozen/B5-3aac34d, kit B zip cbf2ccb3; SHIP_DIALS in
hyperion/compose/bot.py).

## Accepted on held-out seeds, not yet frozen (batch 6)
- V-f (H15): {"hero.postflop.size_read_twists": "discard,bounty,knockout,swap,exposed",
  "hero.postflop.s11_twists": "knockout,buy,swap,exposed", "strong_route_twists": "bounty,knockout,buy"}
- S6 (H16): {"short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
  "short.pre_open_min": 0.65, "short.like_probe": 0.75, "short.like_bet": 0.6, "short.like_pfr": 0.15}
- V-h (H18): {"hero.known_cards": "pre"}
- Pending: S15c on H19 (39000-39399), spec in /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b20/s15c.json, output /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b20/s15c_h19.md.

To freeze batch 6: add the accepted dials to SHIP_DIALS (and a BATCH6_OFF like BATCH5_OFF), run the combined check
against batch 5 on the next fresh set (H21 = 41000-41399, every stage), the judges once (now incl. elite_judge_b,
adapt_judge*, and outside_b once wired), timing, then tools/pack.py --slim and tools/gate.py --kit b --tables 40,
and the decisions entry, leaderboard, HANDOFF, log (batch 5's entry is the template).

## Running when this was written (outputs land on disk even if the agents stop)
- start-vs-now: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b18/start_vs_now.md (the starting F's dials against batch 5 on H17; for the leaderboard).
- S15c on H19: /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/b20/s15c_h19.md.
- Workers (branches in worktrees under /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal; each commits as it goes):
  S16b climb/s16b-open-answer (wt_s16b), S17 climb/s17-stab-size (wt_s17), S18 climb/s18-horizon-icm (wt_s18).
- Outside judges wave 2 (addendum 10, held out): /tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/goal/outside2/o5, o6, o7 (o7 done, md5 7ada9e81). Wire them in as
  elite5 and adapt2 were (frozen copy below an origin header, a bestiary class seeding self.rng per table, the
  field outside_b in the judges stage, tests).

## Held-out sets used
H1-H3 retired; H4-H18 used once or more (see the log); H19 in use; next fresh: H20 = 40000-40399, H21 = 41000-41399.

## End deliverables (goal.md): final SHIP and zip, a decisions entry, PLAYBOOK and HANDOFF, the last rehearsal on the
final ship, the one-page leaderboard, a list of what we would still try (docs/research/Edges against strong
opponents.md has the ranked list to start from).
