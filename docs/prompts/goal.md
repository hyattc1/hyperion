# The climb: the brief for a long /goal run

Start it with `/goal`, giving the one-line condition at the end of this file (the condition is capped at 4,000 characters, so the brief lives here).

Goal: win our regional. Hyperion (~/dev/hyperion, private repo hyattc1/hyperion) must go into the night as the strongest base we can make: the one that, after 60 minutes of adapting it to an unknown variant and starter kit, scores highest against the real field, and keeps scoring in the five windows after. Our simulator is a means, not the goal: a change that wins in our rooms but makes the bot harder to adapt, slower, more fragile on an unfamiliar kit, or that only beats opponents we wrote, is a loss. Being first on our own leaderboard is a checkpoint, not the finish line: keep climbing until nothing more helps.

Read first: HANDOFF.md, PLAYBOOK.md, docs/packet/CHALLENGE.md, CONTRACTS.md, the last ten entries of docs/decisions.md, and docs/drills/compose-log.md. The composite ships today (hyperion/ship.py); hybrid3_x and Hero are the fallbacks.

Phase 0, before any bot code changes: write docs/drills/goal-plan.md and commit it.
- Break the night score into its parts: strength against the real field; strength under the variant; adapting to an unseen variant and kit within the hour; robustness (interface shape, missing or partial log, payout table, a slower machine); never timing out or crashing; and the between-tournament windows.
- For each part, say how we measure it. Freeze the protocol: fields, screen seeds vs held-out seeds, table counts, the noise rule, the acceptance rule. Changing it later needs a decisions entry saying why.
- A backlog of ideas across all four tracks below, ranked by expected gain on the night per hour of work.

Test sets that keep us honest (build these first):
- Outside opponents: fresh agents with no repo access each build a bot the way real teams will (60 minutes, a starter-kit-style interface, different approaches: Monte Carlo, charts, push/fold, an agent's first draft). Build at least three. Nobody tunes on them.
- Unseen variants: a fresh agent with no access to our catalog writes 5 plausible variants we haven't catalogued.
- An exploiter: a fresh agent given only our packaged zip as a black box tries to build a bot that beats it. Whatever it finds, we fix.
- A change must hold up under different night-mix weights and payout tables, not just the defaults.
- Judges (rival 4, rival 5, the outside bots) are measured once per accepted batch, never tuned on.
- Held-out seeds get used up: after a set has confirmed three changes, retire it and draw a fresh one. Add a new outside bot every few rounds, so we're never climbing against the same opponents.

The loop (repeat; rotate the tracks so none is starved):
1. Strength. Profile by section, pick the weakest, change it. Fix weak sections rather than sweeping dials (the last climb's 54 one-dial trials were about noise). Directions: push/fold and call-off ranges with ICM at the payout table, short-handed and endgame play, faster reads of dead, timing-out and maniac seats, postflop against a single raiser, and anything the exploiter finds.
2. Variants. Rank the catalogued variants by likelihood. For the top ones, go past READY: make the bot strong under each variant against variant-aware opponents. Make the generic patch path fast enough for the unseen five.
3. The hour itself. Full rehearsals: a fresh agent gets only what we'll have on the night (the packet, the prompts, a new fake kit with an unseen variant and an unfamiliar interface, built by another fresh agent) and 60 minutes. Score its final gated submission against the held-out field, and the minutes to its first valid upload. Fix whatever slowed it down or broke, in the prompts, the packet or the code. Rehearse the five windows and their recipes too. Rehearse the composite and the simpler hybrid3_x; if the composite's complexity costs more on the night than its gain, say so and switch.
4. Robustness. Kits with every log shape, raise-to vs increment amounts, per-table vs per-tournament instances, a slower or busier machine (under load or with the CPU throttled), the memory cap, import time. Keep p99 well inside 1 ms and report the max.

Each round: screen on screen seeds, confirm on held-out seeds, then commit. Accept a change only if:
- it gains beyond noise on held-out night seeds;
- it loses beyond noise on no judge, variant, kit or payout table;
- p99 and timeouts stay within budget;
- the rehearsal is not worse.

After every accepted batch:
- update SHIP;
- freeze a known-good zip and its sha256 (so there is always a safe fallback);
- update the leaderboard: rank, bot, points, margin, in plain words.

When to stop: never just because we're first. Stop when three rounds in a row, each testing at least five ideas from at least three tracks, accept nothing on fresh held-out seeds. Then run one round of bigger structural ideas (a new member for the composite, a new solver, a rewritten section). Stop only if that also fails, or 24 hours before our regional. At the end:
- SHIP and the frozen zip are final;
- a decisions entry, PLAYBOOK and HANDOFF say what ships and why;
- the last rehearsal shows a fresh agent adapting it to an unseen variant and kit within the hour;
- a one-page leaderboard covers the held-out field, the judges, the variants and the rehearsals;
- a list of what we'd still try.

Rules that don't bend:
- Never copy outside or public code into our bots (rules §6.1). Rival, outside and persona bots are our own agents' code.
- Never read or modify ~/dev/sequoia-blind; grade it only from snapshot copies, numbers only.
- The repo stays private; nothing in the public export identifies the event (tools/export_public.py, 0 denylist hits).
- `git add` explicit paths only, commit per step, `pull --rebase`, push. docs/decisions.md is append-only.
- Don't stop to ask; record each decision and keep going. Don't interrupt long runs.

## The /goal condition

`Our regional is <city, date>. Follow docs/prompts/goal.md in ~/dev/hyperion end to end. The goal is met only when its stop rule fires (three rounds in a row accept nothing on fresh held-out seeds, then one round of structural ideas also fails, or it is 24 hours before our regional) and its end deliverables are committed and pushed.`
