## 3. The design the rival chose, and why it differs from a heuristic team

Rival 1 was a hand-reading team: a typed preflop table, a fitted push formula, made-hand buckets
with outs, four opponent flags, three ICM heuristics. Rival 2 took the opposite bet: spend the
unmetered import on computing the objects a heuristic team types or fits, then make every decision a
lookup or a one-line expected-value formula over those objects.

- **Evaluator without big tables.** Four cumulative rank masks (ranks seen >=1,2,3,4 times) plus four
  suit masks, updated with three ORs per card; the only tables are 8,192-entry popcount, top-k-bits
  and straight tables. 0.3 us per evaluation from a precomputed board state on CPython 3.12. Rival 1
  built a 73,775-entry prime-product dictionary; rival 2 wanted an evaluator cheap enough to call
  from inside a per-decision Monte Carlo and inside the import-time matrix build.
- **The 169x169 all-in matrix and the vs-1/2/4 equity table are computed, not typed.** One pass over
  1,500 shared random boards: for every board, one combo per class (accepted with probability
  N_available/N_max so that (board, combo) is uniform), one random-tie-broken sort of the 169 values
  gives every pairwise "beats" relation at once, and 12-plane bit-sliced counters accumulate wins and
  valid (card-disjoint) pairs with 169-bit integer ops instead of a 169x169 inner loop. Three
  4-villain samples per board give equity vs 1, 2 and 4 random hands with card removal. All of it is
  unbiased by construction (rejection + conditioning) and lands within 0.3-0.6 points of the
  published numbers (AA 0.849 vs 0.852, AKs 0.666 vs 0.670, 22 0.498 vs 0.503, AK v QQ 0.428 vs
  0.43). 1.0 s.
- **Push/fold is solved, not remembered.** Fictitious play (time-averaged best responses) on the
  matrix for a pusher vs k symmetric callers (k = 1,2,3,5,7) at ten depths, with exact
  card-removal weights. Plain best response oscillated (the rival's first bug: "HU 10bb push 99%");
  damping fixed it in four minutes. The solve stores, per class, the fold probability F of one
  caller and the equity-when-called Ec, so act() re-prices the push with the real dead money and the
  ICM curve instead of reading a yes/no chart. Output: HU 10bb push 52% / call 33%, BTN 15bb 26%,
  UTG 8-handed 10bb 7%.
- **ICM exact, once per hand, interpolated.** Malmuth-Harville by a subset DP that skips every
  subset containing us (2^(n-1) states): 39 us for eight players. Five evaluations per hand (our
  stack at 0.5x, 0.9x, 1x, 1.1x, 2x, plus the exact endpoints 0 and T) give a piecewise-linear
  utility curve; every call, push and re-shove decision compares utilities on that curve, so pot
  odds, bubble pressure and ladder effects come out of one object. Two mistakes were found and
  fixed here: the first curve had knots only at 0.5x/1x/2x and its kink at 1x made a 70-into-110
  call need 0.39 equity instead of 0.28; and pricing our pushes by ICM while modelling callers by
  chip EV double-counted the tax, so callers' ranges are shrunk by the same ratio (icm_fold_boost).
- **Ranges are equity percentiles.** Opens: top f(k) of the vs-1 / vs-2 / vs-4 ranking by players
  behind (f = 0.52 * 0.80^(k-1), scaled by the blinds' fold-to-aggression). Blind defence: equity vs
  the opener's range (a slice of the ranking, width from position and VPIP) against pot odds with a
  realisation discount. 3-bets, 4-bets and 5-bets use a second ranking (equity vs the top 20%), and
  4-bet pots are priced as all-in equity vs the top 3% through the ICM curve. Re-shoves at 4-21 bb
  are priced as F * U(steal) + (1-F) * (Ec * U(win) + (1-Ec) * U(lose)) against the opener's
  best-response calling set precomputed at import.
- **Postflop is a time-boxed Monte Carlo, not a bucket table.** 48-160 samples (260 us soft budget,
  520 us hard cap from act() start): random runout, our hand and each opponent's hand drawn from
  the top-v slice of the ranking (v from VPIP and position), with a fit filter that makes an
  aggressor's sampled hand connect with the board at a rate set by how tight they are (nits bet top
  pair+ and raise two pair+, loose players pair+). Decisions compare the sampled equity with the
  ICM-required equity plus a margin, bet on a 0.4/0.55/0.75/1.0-pot ladder, and refuse deep
  one-pair stack-offs below 0.84.
- **Two numbers per seat.** VPIP ~ Beta(1.5, 4.5) and fold-to-aggression ~ Beta(1.5, 1.5), updated
  incrementally from obs.history (blind posts filtered). VPIP shapes every sampled range and the
  3-bet/re-shove maths; FTA shapes steal width, bluff frequency and the re-shove fold probability.
- **Safety.** act() is try/except with a legalizer that clamps raises and never folds a free check;
  a DEBUG switch re-raises internal exceptions for testing (the operator harness cannot see them
  otherwise); import warms every path and gc.freeze()s.
- **Why its own engine again.** The rival wrote a 230-line SNG engine (side pots, blind schedule,
  cap ICM, bust capture) at minute 6 and ran bust traces three times. Every strategic bug it found
  came from there, none from the harness: own raise not counted (Q4s "defended by pot odds" against
  a 3-bet of our own open), 4-bet wars decided by the vs-random ranking (TT/99/QQ stacked off
  80-160 bb), re-shove fold equity blind to the opener's observed folding (42s re-shoved into a nit),
  deep one-pair stack-offs, and paying off nits because sampled ranges were not conditioned on the
  board. The scenario file then caught the ICM kink and the 8-sample nut-flush-draw fold.
