# Prompt 06: the five windows after T1 (fire once per window; box 12 minutes, submit by minute 15)

T<k> standings are in. Here is our line and the field: <paste the standings>. Here is what our bot's
own logs say, if the kit exposes any: <paste or "none">.

Rules of this loop, which you must not break:
- One change per window. If two ideas look good, take the one that reduces busts.
- A change is one recipe for the ship bot (see the switch: `python -m hyperion.ship` prints `SHIP` and `DIALS`).
  A recipe is a name (`survival`, `passive`, `dead_seats`, `strong_field`, `latency`, `timeouts`) that
  `--dials <name>` resolves for whichever bot the switch names: rival 3's core dials for hybrid3_x and the
  composite, Hero's Config keys for Hero (`hyperion/ship.py`, RECIPES; CONTRACTS.md lists them). Stack one on
  the dials already kept with `+`: `--dials survival+passive`.
- Measure it: `python -m hyperion.sim --tables 300 --seed 11 --mode model --field realistic@ship --rules
  rules_tonight.json`, once as it is and once with `--dials <kept recipes>+<new one>`; points not lower than the
  current bot on the same seed. Then keep it, `python -m hyperion.ship --set <kept recipes>+<new one>` (writes
  `DIALS` in `hyperion/ship.py`; every tool and the package follow), the strict run and the kit simulator with
  zero errors, repack (prompt 04 step 5: its `bot` line shows the dials) and the new zip passes `tools/gate.py`
  (prompt 04 step 6, `--tables 40`).
- The frozen known-good submission is <sha256>. If the change is not verified by minute 12, submit
  nothing; the frozen bot stays active.
- Never add a new module in a window. Only dials, table swaps, or a one-line guard.

Read the standings for these signals and apply the matching recipe. Each recipe was checked on both bots to move
play the stated way in a paired model-mode run (docs/decisions.md, "Ship hybrid3_x as the base"); none gained
points beyond noise on our fields, so a recipe answers tonight's standings, not a free improvement.
- We are finishing 1st often but busting often (high first-place share, high 7th and 8th): `survival`.
  Fewer stack-off calls, 3-bets and postflop calls on the core; more patience and a higher value bar on Hero.
  This is the most common mistake under finish-position scoring.
- We are finishing mid-table, rarely 1st, rarely last: we are too passive for this field. `passive`: wider
  opens from the cutoff and the button, more bets when checked to (and more continuation bets on Hero).
- Field is full of near-zero scorers (many bots scoring like always-fold): the dead-seat reads matter most.
  `dead_seats`: the core's seat reads move twice as fast; Hero steals by fold reads sooner and its profiler acts
  sooner.
- Field is strong and tight (top scores bunched): `strong_field`. On Hero it opens a little tighter and reads
  sooner. On rival 3's core it changes nothing: Hero's recipe measured -0.48 ± 0.33 there, so the core keeps its
  own play. Do not try to outplay them postflop.
- Our timeouts or errors are nonzero in any log the kit gives us: nothing else matters. If the latency is
  ours, `latency` first (the core's exploit layer off, about 6 µs; Hero's profiler off), else `timeouts` (every
  decision Hero's cheap path; about two points a table, an emergency); verify, submit.

Between windows, do not touch the bot. Write in `NIGHT.md` what we changed, why, the sim line, and
the sha256 submitted. If I ask for a change that violates the rules above, remind me of the rule and
ask once whether I still want it.
