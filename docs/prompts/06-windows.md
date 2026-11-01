# Prompt 06: the five windows after T1 (fire once per window; box 12 minutes, submit by minute 15)

T<k> standings are in. Here is our line and the field: <paste the standings>. Here is what our bot's
own logs say, if the kit exposes any: <paste or "none">.

Rules of this loop, which you must not break:
- One change per window. If two ideas look good, take the one that reduces busts.
- Every change is verified in strict mode before submission: the 300-table sim from prompt 04 plus
  the kit simulator, zero errors, points not lower than the current bot on the same seed; then the new
  zip passes `tools/gate.py` (prompt 04 step 6, `--tables 40`).
- The frozen known-good submission is <sha256>. If the change is not verified by minute 12, submit
  nothing; the frozen bot stays active.
- Never add a new module in a window. Only `Config` overrides, table swaps, or a one-line guard.

Read the standings for these signals and apply the matching dial:
- We are finishing 1st often but busting often (high first-place share, high 7th and 8th): survival
  dial. Raise `preflop.patience_deep`, raise `postflop.icm_margin` and `postflop.big_value_tier` by one,
  lower `preflop.three_bet_frac`. This is the most common mistake under finish-position scoring.
- We are finishing mid-table, rarely 1st, rarely last: we are too passive for this field. Raise
  `preflop.open_frac` for the last two seats before the blinds and `postflop.cbet_freq_ip_dry`.
- Field is full of near-zero scorers (many bots scoring like always-fold): the dead-seat exploit
  matters most. Lower `profiler_blend_n` (8 to 4) so reads act sooner and raise
  `profiler_dial_strength`; the dead-seat flag itself is not a Config key.
- Field is strong and tight (top scores bunched): lower `preflop.open_frac_default`, keep
  `preflop.patience_deep` up, and lower `profiler_prior_n` from 2 to 1 so reads bite sooner. Do not
  try to outplay them postflop.
- Our timeouts or errors are nonzero in any log the kit gives us: nothing else matters. Switch to
  `Config.cheap=True`, verify, submit.

Between windows, do not touch the bot. Write in `NIGHT.md` what we changed, why, the sim line, and
the sha256 submitted. If I ask for a change that violates the rules above, remind me of the rule and
ask once whether I still want it.
