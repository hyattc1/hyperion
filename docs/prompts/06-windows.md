# Prompt 06: the five windows after T1 (fire once per window; box 12 minutes, submit by minute 15)

T<k> standings are in. Here is our line and the field: <paste the standings>. Here is what our bot's
own logs say, if the kit exposes any: <paste or "none">.

Rules of this loop, which you must not break:
- One change per window. If two ideas look good, take the one that reduces busts.
- Every change is verified in strict mode before submission: the 300-table sim from prompt 04 plus
  the kit simulator, zero errors, points not lower than the current bot on the same seed.
- The frozen known-good submission is <sha256>. If the change is not verified by minute 12, submit
  nothing; the frozen bot stays active.
- Never add a new module in a window. Only `Config` overrides, table swaps, or a one-line guard.

Read the standings for these signals and apply the matching dial:
- We are finishing 1st often but busting often (high first-place share, high 7th and 8th): survival
  dial. Raise `Config.pushfold` ICM premium, raise the all-in value threshold one tier, stop 3-betting
  light. This is the most common mistake under finish-position scoring.
- We are finishing mid-table, rarely 1st, rarely last: we are too passive for this field. Lower the
  steal threshold one step on the button and cutoff, raise c-bet frequency against folders.
- Field is full of near-zero scorers (many bots scoring like always-fold): the dead-seat exploit
  matters most. Lower the dead-seat detection count from 5 to 3 and widen shoves against flagged
  dead seats.
- Field is strong and tight (top scores bunched): tighten opens, keep the ICM premium high, and let
  the profiler's weights grow faster (prior 2 to 1). Do not try to outplay them postflop.
- Our timeouts or errors are nonzero in any log the kit gives us: nothing else matters. Switch to
  `Config.cheap=True`, verify, submit.

Between windows, do not touch the bot. Write in `NIGHT.md` what we changed, why, the sim line, and
the sha256 submitted. If I ask for a change that violates the rules above, remind me of the rule and
ask once whether I still want it.
