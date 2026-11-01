# build_log: rival_bot (team f4_pushfold, ICM push/fold quants)

Elapsed marks (wall clock from T0): ~45 min used, bot frozen at ~46 min. Snapshots: snap_m15.py, snap_m30.py, snap_m45.py (m45 == frozen file).

## What was built
- Offline (stdlib only): 7-card evaluator (evalr.py), Monte-Carlo class-vs-class equity matrix (169x169, 30k samples per hand class), turned into
  (a) a percentile ranking of the 169 hand classes and (b) equity of each class vs the top 3..100% of hands (embedded tables PCT / EQT).
- Malmuth-Harville ICM, exact, subset DP (about 40 us at 8 live players), used live for: bubble factor, call-vs-shove equity requirement,
  fold/call/jam EV when short facing an open, postflop all-in calls.
- Preflop (the focus):
  * stack in BB at the start of the action, position = players still to act behind (8-max aware).
  * M <= ~22: first-in shove if hand percentile <= push chart(M, players behind) * ICM adjustment * 1.15. Chart is a hand-entered Nash-like
    table (SB/BTN/CO/HJ/... by depth 3..25 bb). ICM adjustment = 1/(1+0.5*(BF-1)) with a depth-dependent floor (short stacks can't wait).
    M 14..22: min-raise 2.2bb with the wider open range, shove the push range.
  * Facing a shove (or a call that is all-in for us): equity of our class vs the shover's estimated range (push chart for his depth/position,
    blended with his observed raise frequency at this table) vs ICM-derived required equity (+2.5% margin, -8% per extra caller).
  * Short (<=15bb) facing a non-all-in open: compare ICM EV of fold / call / jam; jam EV uses the opener's fold frequency derived from pot odds.
  * Deeper: open-raise 2.5bb(+1 per limper) by position (x1.35 scale, found better in A/B), 3-bet/jam QQ+/AK (a bit wider vs loose raisers), call
    small raises with a tight range (BB wider), fold to 4-bets without premiums.
- Postflop (kept deliberately simple): made-hand tier (0-5) + draw outs; value bet tiers 3+, cbet bluff 25% HU as aggressor, semi-bluff draws,
  call by pot odds per tier, all-in calls use ICM-required equity.
- Safety: every action goes through _legalize (clamps raise, never folds when check is legal); any exception falls back to check/fold;
  gc.freeze at import; time guard (fallback heuristic if >260 us before the heavy jam EV).
- Test tooling in the dir: engine.py (small 8-max SNG engine with side pots, blinds schedule, 200-hand cap, points), bots.py (random, station,
  maniac, tag, nit, shove bot), sim.py/stats.py/ab.py/ab2.py (A/B runs).

## Results (own engine, so only indicative; fair = 4.0 points)
- vs mixed weak field (random, station, maniac, 2 tags, nit, shove bot): ~7.4
- vs tag/nit field: ~7.1; vs random/maniac/station field: ~8.0; vs 7 copies of itself: 3.9-4.2 (noise +-0.1).
- Parameter sweeps in self-play: ICM tightening strength, shove-range width and call margin all flat within noise; wider opens (x1.4) +0.15.

## Harness
exceptions=0, illegal=0, fuzz exceptions=0 illegal=0, mean ~15-50 us (machine was loaded), noise-free worst-case compute ~270 us.
(max in harness shows 2-5 ms spikes: the machine was at load average 5-10; a trivial 2 us loop shows the same 2 ms spikes.)

## Known weaknesses
- Push/call charts were typed from memory of Nash charts, not solved; the ICM adjustment for first-in pushes is a heuristic (bubble factor),
  not a full EV with a modelled calling range.
- Postflop is tier-based with no board texture, no range reasoning, no multiway adjustments; river bluff-catching is crude.
- Hand ranking is by equity vs a random hand, which undervalues suited connectors / overvalues dominated ace-x when called.
- Opponent model is only per-seat preflop raise frequency; no exploitation of nits, stations, or sizing tells.
- Effective stack for the first-in decision uses hero stack only (not the biggest stack behind); no squeeze/limp-trap play.
- Engine details assumed: blinds appear in bets, pot excludes current street bets, history is (seat, (action, amount)).

## With more time
- Solve push/fold Nash with ICM offline (fictitious play on the 169x169 matrix, 3-4 player models) and replace the typed charts.
- Proper EV-based first-in shove with modelled callers; effective stack by position.
- Real postflop: equity vs a range by Monte Carlo within budget, board texture, c-bet frequencies, sizing.
- Per-opponent models (VPIP, shove and call frequencies) with Bayesian priors; check sensitivity to different blind schedules.
