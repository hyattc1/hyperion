# Prompt 06: the five windows after T1 (fire once per window; box 12 minutes, submit by minute 15)

T<k> standings are in. Here is our line and the field: <paste the standings>. Here is what our bot's
own logs say, if the kit exposes any: <paste or "none">. Recipes kept so far: <"none" or names, e.g. `dead_seats`>.

Rules of this loop, which you must not break:
- One change per window. If two ideas look good, take the one that reduces busts.
- A change is one recipe for the ship bot (see the switch: `python -m hyperion.ship` prints `SHIP` and `DIALS`).
  A recipe is a name (`survival`, `passive`, `dead_seats`, `strong_field`, `latency`, `timeouts`) that
  `--dials <name>` resolves for whichever bot the switch names: the composite's own dials (`COMPOSITE_RECIPES`),
  rival 3's core dials for hybrid3_x, Hero's Config keys for Hero (`hyperion/ship.py`; CONTRACTS.md lists them).
  Stack it on the dials already kept with `+`: `--dials dead_seats+survival`. The composite's governor (`slow_box`)
  is in its defaults: a recipe never removes it, so never add it there; on a fallback bot add it first.
- The steps, in order, with the minutes the rehearsal took (docs/drills/f1-windows-log.md: 2 workers at load 12;
  use 4). About 4 minutes in all, so the box has room for reading the standings and the upload:
  1. Measure (3.2 min cold, 1.6 with F cached at the freeze or by an earlier window): `python tools/climb_accept.py
     --stages window --base '<kept>' --cand '<kept>+<new>' --rules submission/rules_tonight.json --workers 4`
     (`--base ''` when nothing is kept; add `--variant <name>` if the catalog has tonight's twist). It plays both
     on the night field, 200 duplicate seeds x 8, paired and exactly replayable, and prints one row and a verdict:
     `[x] window: night not beyond noise down` passes, `[ ]` fails (do not keep it). A recipe answers tonight's
     standings; it is not expected to gain points on our field.
     If the switch names hybrid3_x or Hero (a fallback), climb_accept cannot build it: run `python -m hyperion.sim
     --tables 200 --rotate --seed 11 --mode model --field night@ship --rules submission/rules_tonight.json` once as
     it is and once with `--dials <kept>+<new>`, and keep it only if ship's points are not lower by more than its ±95%.
  2. Keep it (seconds): `python -m hyperion.ship --set <kept>+<new>` (writes `DIALS` in `hyperion/ship.py`; every
     tool and the package follow). Paste the printed `DIALS`.
  3. Strict run (0.3 min): `python -m hyperion.sim --tables 100 --seed 11 --mode strict --field realistic@ship
     --rules submission/rules_tonight.json`: ship exc 0 and ill 0 (tmo as in prompt 04 step 2).
  4. Kit simulator (seconds): prompt 04 step 1's command, 100 hands, `HYPERION_CHECK=1`: zero exceptions, illegal
     actions and conformance violations.
  5. Repack (seconds): prompt 04 step 5; its `bot` line must show the new `DIALS`.
  6. Gate (0.4 min): `python tools/gate.py dist/submission.zip --kit <same as Stage 2> --tables 40 --rules
     submission/rules_tonight.json` (plus `--variant <name>`, `--kit-log no` as in Stage 2; `--entry <file>` only if
     the gate asks): `GATE PASS`. Then upload.
- The frozen known-good submission is <sha256>. If the change is not verified by minute 12, submit
  nothing; the frozen bot stays active.
- Never add a new module in a window. Only dials, table swaps, or a one-line guard.

Read the standings for these signals and apply the matching recipe. Each was checked on the composite we ship (F),
paired in model mode on the night field and on a field that shows the signal (docs/drills/f1-windows-log.md): each
moves play the stated way. Only `dead_seats` gained points beyond noise on its own signal (among timing-out seats);
`latency` cuts timeouts at level points; the rest are level. A recipe answers tonight's standings; it is not a free
improvement.
- We are finishing 1st often but busting often (high first-place share, high 7th and 8th): `survival`.
  Fewer all-in calls (11% to 7%) and deep 3-bets (6% to 4%); 7th and 8th places down about a point. Postflop stays
  Hero's play. Points level on night and on a table that busts us (`strong`: +0.04 ± 0.08); it gained among dead
  seats (+0.08 ± 0.06) and on `night_hard` (+0.10 ± 0.07), where F's busts come from calling shoves.
- We are finishing mid-table, rarely 1st, rarely last: we are too passive for this field. `passive`: cutoff and button
  opens up 3-5 points, bets when checked to up 3-4 points (the exploit layer bets at a 0.35 fold read). Level on night;
  at a table of strong bots it does not help either (`elite`: -0.03 ± 0.07).
- Field is full of near-zero scorers (many bots scoring like always-fold): the dead-seat reads matter most.
  `dead_seats`: the layer steals at a 0.5 fold read (0.7 shipped), steals up 7-8 points, and Hero's reads act sooner.
  Among timing-out bots +0.06 ± 0.05; level on night. It costs at strong tables (`top` -0.12 ± 0.08, `elite` -0.16 ±
  0.08): apply it only on this signal.
- Field is strong and tight (top scores bunched): `strong_field` changes nothing measurable on F (±0.03 on night, `top`
  and `elite`): it is the frozen bot. Do not try to outplay them postflop; spend the window on another signal or on
  nothing.
- Our timeouts or errors are nonzero in any log the kit gives us: nothing else matters. If the latency is
  ours, `latency` first (no shadow decisions: the members not chosen skip the call, about 17 µs a call and 30 µs at
  p99; on a box 5-8x slower a fifth to a third fewer timeouts, points level). Errors, or timeouts that `latency` did
  not cure: `timeouts` (every decision Hero's cheap path, -1.6 points a table on 8..1 and -14 of 100 on a top-heavy
  table, even on a slow box: the governor already steps down on its own, so this is for errors, an emergency).
  Verify, submit.

Between windows, do not touch the bot. Write in `NIGHT.md` what we changed, why, the window line (`climb_accept`
row), and the sha256 submitted. If I ask for a change that violates the rules above, remind me of the rule and
ask once whether I still want it.
