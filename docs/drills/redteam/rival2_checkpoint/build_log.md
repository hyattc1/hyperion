# Rival 2 build log (timestamps relative to T0 = 2026-10-31 11:56:12 UTC, see T0.txt)

## 00:00-03:40  first draft in one pass (rival_bot.py ~900 lines)
- Evaluator: 7-card bitmask evaluator (m1..m4 cumulative rank masks + 4 suit masks, 8192-entry
  POP/TOP-k/straight tables). 0.3 us per evaluate-from-state on CPython 3.12.
- Import-time Monte Carlo over 1,500 shared random boards: for each board one accepted combo per
  class (rejection makes (board, combo) uniform), a random tie-broken sort gives every pairwise
  "beats" relation at once; bit-sliced 12-plane counters accumulate W[i][j] and V[i][j] without a
  169x169 inner loop. Three 4-villain samples per board give equity vs 1/2/4 random hands.
  Card-removal weights WREM[i][j] are exact. Result: 169x169 all-in matrix + E1/E2/E4 in 1.0 s.
  Spot checks: AA 0.849 (true 0.852), AKs 0.666 (0.670), 22 0.498 (0.503), AA v KK 0.816 (0.82),
  AK v QQ 0.428 (0.43), AKs v 22 0.507 (0.50), JTs v AKo 0.397 (0.40).
- Push/fold: iterated best response on the matrix, pusher vs k symmetric callers, fold prob F and
  equity-when-called Ec stored per class so act() re-prices with ICM and real dead money.
- ICM: exact Malmuth-Harville subset DP (skips subsets containing us): 39 us for 8 players,
  so it runs exactly once per hand (three knots: 0.5x, 1x, 2x our stack) and act() interpolates.
- Preflop ranges = equity percentiles (P1/P2/P4 by players behind); open fraction
  0.52*0.80^(k-1) scaled by the blinds' fold-to-aggression; blinds defend by pot odds; light 3-bets
  from the blinds vs late opens; re-shove 7-21 bb priced as F*steal + (1-F)*(Ec*win + (1-Ec)*lose)
  through the ICM curve. Postflop: time-boxed Monte Carlo equity (opponent hands sampled from the
  top-v of P1 with v from VPIP, tightened when they bet) + ICM pot odds + a 0.4/0.55/0.75/1.0 ladder.
- Opponent model: per seat VPIP ~ Beta(1.5,4.5), fold-to-aggression ~ Beta(1.5,1.5), updated
  from obs.history incrementally; blind posts filtered.
## 03:40-05:00  first bug: plain best response oscillates (HU 10bb "push 99%")
- Replaced by fictitious play (time-averaged best responses, warm start across depths, dot
  products via sum(map(mul))). Now HU 10bb push 52% / call 33%, BTN 15bb 26%, UTG 8-handed 10bb 7%.
  Grid 5 k-values x 10 depths; import 1.17 s.
## 05:00-05:30  harness: 2,000 obs, 0 exceptions, 0 illegal, mean 194 us, p99 481, max 5.5 ms
- act() swallows exceptions, so added Bot.DEBUG to re-raise and debug_harness.py: 0 internal
  exceptions. The 5.5 ms max does not replay (slowest calls re-time at 210-280 us = MC budget);
  cut the MC budget to 260 us.
## 05:30-07:30  engine.py (side pots, blind schedule, cap ICM, bust capture) + arch.py archetypes
- Mixed field (random, station, folder, maniac, tight, semi-sane, min-raiser): 7.22 pts, 53% 1st.
## 07:30-11:00  background fields + bust replay (busts.py) found five real leaks
- Pre-fix: min-raise 8.40, 1 push + 6 tight 5.87, self 4.43, semi-sane 5.15, 7 tight 3.40 (25% 8th).
- Leaks: (1) own raise not counted in n_raises -> after opening and being 3-bet we "defended by
  pot odds" with Q4s; (2) 4-bet/5-bet wars decided by the vs-random ranking -> TT/99/QQ stacked
  off 80-160 bb; (3) re-shove fold equity ignored the opener's observed fold-to-aggression -> 42s
  re-shoved 18 bb into a nit; (4) one pair stacked off deep after a raise; (5) thin value bets with
  MC noise. Fixes: own raises tracked; a value ranking PV (equity vs top 20%) for 3-bet/4-bet
  decisions and equity-vs-top-3% with ICM pot odds for 4-bet+ pots; F scaled by FTA and capped at
  0.85, junk never re-shoves; deep one-pair guard (e >= 0.84 to raise, +0.12 to call when the
  spot is half our stack at 30bb+); bet thresholds 0.58/0.60/0.62 by street.
## MINUTE 15 state: harness 0/0 (mean 163 us, p99 341, max 481), all fields run end to end,
   five leaks fixed, post-fix runs in flight. Open: tight field result, timing headroom.
## 15:00-18:30  scenarios.py (45 hand-written spots) found four more things
- BB defended 72o: blind defence used equity vs a random hand; now equity vs the opener's range
  (equity_vs_set over the top-agg_cut of P1), discounted per extra caller.
- JJ 4-bet 100 bb deep: 4-bet threshold PV <= 0.015 (QQ+) beyond 45 bb, 0.035 (JJ+, AKs) inside.
- Speculative 3-bet calls now in position only (postflop order vs the aggressor).
- The ICM curve had knots at 0.5x/1x/2x only, so a 70-into-110 call at 8 equal stacks needed 0.39
  equity instead of 0.28: the kink at 1x was an interpolation artefact. Added local knots at 0.9x
  and 1.1x (five exact MH evaluations per hand, ~200 us at 8 players, still once per hand).
- Caller-side ICM: our pushes were priced by ICM but callers by chip EV, a double penalty. Callers'
  calling fraction is now shrunk by ((1-e_icm)/(1-e_chip))^2 (icm_fold_boost). A9o re-shoves 12 bb
  vs a BTN open; K8o on the BTN at 8 bb with four equal stacks computes to breakeven, which is
  what an ICM solver says for 10/7/5/4 payouts.
## 18:30-21:00  nut-flush-draw fold traced to sampling, not strategy
- Trace showed equities in multiples of 1/8: the first act() of a hand built the ICM curve and
  left the time box 8 samples. Added MC_MIN (48 samples, scaled by opponents) and a hard deadline
  at 520 us from act() start; fit-filter retries capped at 5. The fold became a call (e 0.42).
- A scenario artefact noted as a real weakness: history parsed all at once at street 1 tags the
  preflop raise as a flop raise; in play the parse is incremental so only calls are mis-tagged.
## 21:00-23:00  second tight-field bust trace
- Busts are now mostly standard push/fold variance. Fixed: a raiser closing the action (k_agg=0)
  was modelled wider than a button opener; a raise over our limp/call is read at 0.55x the range;
  fit filter thresholds by opponent type: tight players bet top pair+ and raise two pair+, loose
  players pair+ / top pair+.
- Fields on the 20:30 version (60 tables): 7 tight 5.55, mixed 7.74, 7 semi-sane 6.14,
  1 push + 6 tight 8.82, 7 min-raise 6.52, self-play 3.95 +- 0.28 (engine symmetric).
## 23:00-24:00  clean timing (nothing else running)
- 3.12: 10,000 obs, 0/0, mean 163 us, p99 298, max 636. 3.10: mean 180, p99 314, max 1,987 us,
  but a control bot with a fixed 200 us busy loop hit 3.9 ms in the same conditions and every
  slow rival call replays at 10-280 us: scheduler noise. The bot's own worst path is the hard-
  capped MC (~280 us) or the first-act ICM build (~200 us at 8 players).
## MINUTE 30 state: snapshot snap_m30_rival_bot.py (md5 below). 100-table fields and HU matches
   in flight on this exact code. Open: nothing structural; remaining time is verification.
7e7adfb3c29835b603b07479ca548eea  rival_bot.py
## 24:30-26:00  100-table fields on the minute-30 code, plus heads-up matches
- 7 tight 4.70 +- 0.32, mixed 7.30 +- 0.28, 7 semi-sane 5.84 +- 0.30, self-play 3.91 +- 0.29.
  HU from 2000 chips, 100 matches each: 97% vs station, 82% vs tight, 80% vs maniac, 80% vs random,
  75% vs semi-sane, 64% vs push-bot.
- The tight number is 1.5-2 SE under the two previous versions. Suspect: the last fit-filter
  tightening (nits "bet top pair+") over-respects a rule-bot's flop bets, which it makes with any
  pair. Made the thresholds a knob (FIT_TYPED) and launched a paired A/B, 150 tables per arm on the
  same seeds, tight and semi-sane fields. Decision rule: keep whichever wins the tight field unless
  it loses semi-sane by more than noise.
