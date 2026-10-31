# Track B: the from-scratch specification (paste after prompt 00 if no prepared code is allowed)

This is the compressed design of our prepared bot. Build it in this order, verifying each step with
a command. Stdlib only. Every function on the decision path is lookups and arithmetic.

## Step 1 (by minute 15): legal cheap bot
- Cards: int 0..51 = rank*4 + suit, rank 0 = deuce, 12 = ace. Write parse/format helpers for the
  kit's card strings.
- Preflop: a hand is "premium" if a pair of 9s or better, AK, AQ, AJs, KQs; "playable" if any pair,
  any two cards T or higher, suited ace, suited connectors 65s and up. Open premium from any seat to
  2.5 big blinds, playable only from the last three seats before the blinds; call a raise only with
  premium; 3-bet to three times the raise with QQ+ and AK.
- Under 12 big blinds effective: push or fold. Push any premium or playable from any seat, plus any
  ace, any king with a suited or T+ kicker, and any pair when under 8 big blinds. Call a shove with
  TT+ and AK, widen to 77+ and AQ when the shover is short or has shoved three times already.
- Postflop: compute made-hand category by counting ranks and suits (pair, two pair, trips, straight,
  flush, full house, quads). Bet 60 percent of pot with top pair or better when checked to; call a
  bet with top pair or better or with 8+ outs when the bet is under a third of pot; otherwise fold.
  Never bluff.
- Wrap the whole decision in try/except returning check-else-fold. Clamp raises to the legal range.
- Run the kit simulator 50 hands. Zero errors. Submit.

## Step 2 (by minute 30): evaluator and profiler
- Evaluator: at import, build two dicts for 5-card hands. Enumerate all 5-rank multisets (7462
  classes) and classify each into (category, tiebreak tuple); sort; assign strength 1..7462. Key the
  non-flush dict by the product of rank primes (2,3,5,7,11,13,17,19,23,29,31,37,41) and the flush dict
  by the 13-bit rank mask. For 6 and 7 cards, build at import a dict from the prime product of all
  cards to the best 5-card strength (iterate multisets of 6 and 7 ranks with at most 4 of a rank; a
  few seconds). Flush case: if any suit has 5+ cards, look up the suited rank mask in a mask table
  built for 5, 6 and 7 bit masks. With 7 or fewer cards, 5 suited cards rule out quads and full houses,
  so the flush lookup is final; with 8 take the max of both paths. Evaluate is then one suit count,
  one product, one dict lookup: a few microseconds.
- Profiler: per seat, counters with a Beta prior of 2 pseudo-observations at the population rate:
  voluntarily put money in preflop (VPIP, prior 0.3), raised preflop (PFR, 0.15), folded when facing a
  bet (0.5), shoved (0.05). Update from the action history each decision, tracking which actions were
  already counted. Flags after enough observations: dead seat = folded to every bet it faced but
  checked when checked to, 5 observations; station = fold-to-bet under 0.15 after 10; maniac = raise
  rate over 0.5 after 10; nit = VPIP under 0.12 after 20.
- Exploits: against a dead seat, shove anything when it must act after us and faces a bet, and
  always bet when it checks to us. Against a station, never bluff, bet 75 percent pot with top pair
  good kicker or better, wait for the river with medium hands. Against a maniac, call down with top
  pair, never fold an overpair, do not bluff. Against a nit, steal its blinds with any two from the
  button and cutoff, fold to its raises without QQ+/AK.

## Step 3 (by minute 45): equity table and ICM gate
- At import, Monte Carlo 169 preflop classes versus 1 and versus 3 random opponents with 400 samples
  each using the evaluator (a few seconds total; if it is slower than 5 seconds, cut samples). Rank
  classes by heads-up equity. Replace the hand lists in step 1 with percentile thresholds: open the
  top 15 percent from early seats, 25 percent middle, 40 percent button, defend the big blind with
  the top 35 percent versus one raise; push thresholds by stack: under 5 bb top 60 percent, 5 to 8
  top 40, 8 to 12 top 25 from early seats and top 45 from the button; call shoves with the top 12
  percent, widening to 20 against a flagged maniac.
- ICM: Malmuth-Harville over the 8 stacks and the point table, memoized, computed once per hand at
  hand start, never per decision. Before any all-in decision compare the ICM value of fold versus the
  equity-weighted ICM value of win and lose; require the ICM gain to be positive. Under linear points
  this makes you fold marginal coinflips when two or more shorter stacks are at the table.

## Step 4 (if time remains): the variant patch from prompt 05.

Verification at every step: kit simulator 50 hands with zero errors, and a timing loop that calls
the decision function 10,000 times on a fixed state and prints mean and max microseconds. Mean must
be under 100 µs and max under 500 µs before anything is submitted.
