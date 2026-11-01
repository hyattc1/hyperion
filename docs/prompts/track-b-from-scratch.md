# Track B: the from-scratch specification, v2.1 (paste after prompt 00)

Build in this order. After every step run the gate (at the end), zip `submission.py` at top level,
submit. Stdlib only.

**Definitions.** Cards are ints 0..51 = rank*4 + suit, rank 0 = deuce, 12 = ace. `k` = players dealt
in between you and the button clockwise: button 0, cutoff 1, hijack 2. Buckets: late k ≤ 1; middle k
2–3 and the SB when folded to; early the rest and the BB (opens the early range over limpers, else
checks). Effective stack, "bb" = min(your stack, the largest opponent stack still in the hand) in
big blinds. Shove = a raise that is all-in or at least 10 bb; a short shover began the hand under 12
bb. Top pair = a hole card pairing the highest board card, or a pocket pair above the board. Outs: 9
for a flush draw, 8 for an open-ended straight draw, flop and turn only. Pot = chips from previous
streets (your bet sizes are fractions of it); facing a bet, pot includes this street's bets and the
one you face. Percent of hands = percent of the 1,326 two-card combos (pair class 6, suited 4,
offsuit 12) ranked by heads-up equity.

## Step 0 (minutes 0–2): cards and the rank map
- Parse the kit's card strings (a ten may be "10"). Start `test_bot.py`: the parser, step 1's two
  lists, one legal-action check; keep it green.
- If the rules permute ranks, build a 13-entry list `REMAP[displayed] = strength` and apply it to
  every card at parse time, before anything else; everything downstream is in strength ranks.

## Step 1 (by minute 15): legal cheap bot
- Safety first: wrap `act` in try/except returning check-else-fold; clamp raise totals into the legal
  range; an illegal raise becomes a call, an illegal call check-else-fold.
- Lists: premium = 99+, AK, AQ, AJs, KQs; playable = any pair, two cards T+, suited ace, suited
  connectors 65s+.
- Deeper than 12 bb: open premium from any seat to 2.5 bb plus one bb per limper; open playable from
  k ≤ 2, button only when fewer than six are dealt in. Facing a raise that is not a shove: call with
  premium; 3-bet to three times it with QQ+ and AK. Facing a shove: call with TT+ and AK; 77+ and AQ
  when the shover is short.
- Under 12 bb: push (raise to the maximum) or fold. Push premium or playable from any seat; under
  8 bb also any ace and any king with a suited or T+ kicker. Facing a raise: re-shove with premium,
  else fold. Facing a shove: the call rule above.
- Postflop: made-hand category by counting ranks and suits. Bet 60 percent of pot with top pair or
  better when checked to. Facing a bet: call with top pair or better at any size, with 8+ outs only
  when the bet is under a third of the pot; else fold. Never bluff or raise postflop.

## Step 2 (by minute 30): evaluator and profiler
- Evaluator: at import, enumerate all 5-rank multisets (7,462 classes), classify each into
  (category, tiebreak tuple), sort, assign strength 1..7462; key a non-flush dict by the product of
  rank primes (2,3,5,7,11,13,17,19,23,29,31,37,41) and a flush dict by the 13-bit rank mask. For 6 and
  7 cards build a dict from the prime product of all cards to the best 5-card strength (rank multisets
  with at most 4 of a rank; about 0.2 s). If a suit has 5+ cards, look its rank mask up in a 5-, 6-
  and 7-bit mask table: final with up to 7 cards; with 8 take the max of both paths. Verify against
  brute force on 3,000 random 7-card hands.
- Profiler: per seat, counters with a Beta prior of 2 pseudo-observations at the population rate:
  VPIP (0.3), PFR (0.15), folded facing a bet (0.5), shoved (0.05); raise rate = raises over all
  observed actions, no prior. Update only from the per-decision history diff (entries since your
  previous decision this hand; keep an index, reset on a new hand number) and from reported
  showdowns. Never infer what you did not see. If the kit gives no history at hand end (kit A:
  unseen folds, seen raises) or none at all, count at most one observation per seat per hand per
  counter and double the floors. With none at all (kit B), diff each seat's active flag and committed
  chips between your observations (after a street change, against that street's last): went
  inactive = fold; committed to a new high = raise (shove at zero behind); matched = call; your own
  raise is the bet others face. Flags: dead = five bets faced, all folded, at least one free check,
  no raise ever; station = fold-to-bet under 0.15 after 10 bets faced; maniac = raise rate over 0.5
  after 10 actions; nit = VPIP under 0.12 after 20 hands dealt in.
- Exploits: when every opponent left in the hand is flagged dead, raise any two preflop and bet every
  street when checked to. Station: bet 75 percent with top pair kicker T+; medium (top pair, worse
  kicker) checks to the river, then bets 75 percent. Maniac: call down with top pair, never fold an
  overpair. Nit: steal its blinds with any two from k ≤ 1; fold to its raises without QQ+/AK. With
  sparse history flags form late or never: exploits unchanged, unflagged seats get the charts.

## Step 2b (minutes 30–33): flags once per hand
- Compute every seat's flags once per hand, at your first decision, into a list by seat; later
  decisions read the list. Counter updates stay per decision. Re-run `bench.py`.

## Step 3 (by minute 45): equity table, charts and the ICM curve
- At import, Monte Carlo the 169 classes versus 1 and versus 3 random opponents, 2,000 samples each
  (about 3 s; over a 5 s import cut to 1,000, never lower). A class's percentile is the
  combo-weighted share ranked above it. `test_bot.py` asserts QQ above JJ, TT above 99,
  A3o outside the top 12 percent.
- Replace the lists. Open the top 15 percent early, 25 middle, 40 late; defend the
  BB with the top 35 versus one raise; every other call of a raise keeps the premium list. Push by
  effective stack: under 5 bb top 60, 5–8 top 40, from any seat; 8–12: 25 early, 35
  middle, 45 late. Call shoves with the top 12, 20 against a flagged maniac; equity vs 1 when one
  opponent is all-in, vs 3 when two or more have money in.
- ICM curve. V(stacks) = your Malmuth-Harville points over the live stacks and the point table;
  never run it inside `act` (about 50 µs). Once per hand build a curve: V at your stack times 0.5, 1
  and 2 (opponents scaled pro rata, total unchanged), plus 0 = the points for busting now and all the
  chips = first place; decisions interpolate V(x) linearly. Evaluate at `new_game` and in the untimed
  hand-end callback, from the stacks it passes (only your chip change, kit A: your new stack and the
  opponents' last-seen chips scaled to the rest); with no callback, at your first decision of a hand.
- Gate: before calling an all-in or re-shoving over a raise, never before an open shove (it has fold
  equity), require e·V(stack + win) + (1 − e)·V(stack − risk) > V(stack) + 1e-6: e from the table,
  win = the pot with every bet and your call, risk = the call (a re-shove risks your stack).

## Step 3b (minutes 45–50): push rule from the equity table
- A third column: equity versus one opponent from the top 20 percent (1,000 samples, about 1 s).
  Under 12 bb, unraised, push on chip EV (bb) instead of percentiles: S = effective stack, B =
  the pot (1.5 plus antes and limps), c = each live opponent's call chance (0.2; maniac 0.3, nit 0.1,
  dead 0), p = the product of (1 − c), e = the third column: push when
  p·B + (1 − p)·(e·(2S + B) − S) > 0 (not V: ICM folds 22 here; it stays on calls). Sanity, 8
  players: button 10 bb about 38 percent, 22 in; early 12 bb about 12, 72o out; wider with fewer
  bb or opponents. On failure keep step 3's percentiles.

## Step 4 (if time remains): the variant patch, Track B form
- Strength: done in step 0. Payoff (bounty, side pot): add its expected value to the pot in
  every all-in comparison and in pot odds; widen percentiles one class for qualifying hands while
  the payoff is at least one bb. Betting: antes join B in the push rule; pot limit clamps
  sizes. Information (extra hole cards): class = best two cards, thresholds one bucket tighter.
- Nothing local measures the patch (the kit's dealer rarely pays the twist): gate for legality,
  record it unverified, keep the pre-patch zip as the fallback.

## The gate (every step, before every zip)
1. Kit runner, 50 hands: zero exceptions, zero illegal actions, timeouts within 1 percent.
2. `bench.py`: 2,000 timed calls rotating three states: mid-hand, the first decision of a new hand
   (new hand number each call), an all-in call at 8 players. Pass: under 0.3 percent of calls over
   1 ms and p99 under 500 µs. Report the max, do not gate on it.
3. `test_bot.py` green; import under 5 s from another directory.
4. Zip; sha256, minute, what changed and every guess go in `NIGHT.md`.
