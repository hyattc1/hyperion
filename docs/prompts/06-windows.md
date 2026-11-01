# Prompt 06: the five windows after T1 (fire once per window; box 12 minutes, submit by minute 15)

T<k> standings are in. Here is our line and the field: <paste the standings>. Here is what our bot's
own logs say, if the kit exposes any: <paste or "none">.

Rules of this loop, which you must not break:
- One change per window. If two ideas look good, take the one that reduces busts.
- A change is a dials dict for the shipped bot (`hyperion/ship.py`: hybrid3_x; `docs/packet/CONTRACTS.md`
  lists every key). Measure it: `python -m hyperion.sim --tables 300 --seed 11 --mode model --field
  realistic@ship --rules rules_tonight.json`, once as it is and once with `--dials '<current DIALS plus the
  change>'`; points not lower than the current bot on the same seed. Then write the dict into `DIALS` in
  `hyperion/ship.py`, the strict run and the kit simulator with zero errors, repack (prompt 04 step 5: its
  `bot` line shows the dials) and the new zip passes `tools/gate.py` (prompt 04 step 6, `--tables 40`).
- The frozen known-good submission is <sha256>. If the change is not verified by minute 12, submit
  nothing; the frozen bot stays active.
- Never add a new module in a window. Only dials, table swaps, or a one-line guard.

Read the standings for these signals and apply the matching dial. Each was checked to move the shipped bot's
play the stated way in a paired model-mode run (docs/decisions.md, "Ship hybrid3_x as the base"). The bracket
is the same dial for Hero, if Hero is what we ship (`--bot hero`).
- We are finishing 1st often but busting often (high first-place share, high 7th and 8th): survival
  dial: `{"r3.call_margin": 0.03, "r3.call_edge": 0.16, "r3.raise_shift": 0.05, "r3.three_bet_scale":
  0.7}` (fewer all-in calls, 3-bets and postflop calls). Not `r3.push_margin`: it cuts the short-stack shoves
  and the bot blinds out. [Hero: raise `preflop.patience_deep`, raise `postflop.icm_margin` and
  `postflop.big_value_tier` by one, lower `preflop.three_bet_frac`.]
  This is the most common mistake under finish-position scoring.
- We are finishing mid-table, rarely 1st, rarely last: we are too passive for this field.
  `{"r3.open_late_scale": 1.3, "r3.bluff_scale": 1.3}`: wider opens from the cutoff and the button and more
  bets when checked to. [Hero: raise `preflop.open_frac` for the last two seats before the blinds and
  `postflop.cbet_freq_ip_dry`.]
- Field is full of near-zero scorers (many bots scoring like always-fold): the dead-seat reads matter most.
  `{"r3.prior_scale": 0.5}`: the seat reads move twice as fast, so the core steals from folders sooner. [Hero:
  lower `profiler_blend_n` (8 to 4) and raise `profiler_dial_strength`; the dead-seat flag is not a key.]
- Field is strong and tight (top scores bunched): no dial on the shipped bot; keep the frozen bot. Hero's
  recipe measured -0.48 ± 0.33 on the core in our strong field. [Hero: lower `preflop.open_frac_default`, keep
  `preflop.patience_deep` up, and lower `profiler_prior_n` from 2 to 1 so reads bite sooner.] Do not try to
  outplay them postflop.
- Our timeouts or errors are nonzero in any log the kit gives us: nothing else matters. If the
  latency is ours, `{"exploit": null}` first (the layer's ~6 µs), else `{"cheap": true}` (every decision Hero's
  cheap path; about two points a table, an emergency) [Hero: `Config.cheap=True`, `{"cheap": true}`]; verify,
  submit.

Between windows, do not touch the bot. Write in `NIGHT.md` what we changed, why, the sim line, and
the sha256 submitted. If I ask for a change that violates the rules above, remind me of the rule and
ask once whether I still want it.
