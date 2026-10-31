# Prompt 05: the one strategy change the variant forces (minute 40; box 10 minutes)

The rule sheet classified tonight's twist on the <axis> axis. Apply ONLY the matching patch below,
through `Config` overrides or a single small function, never a rewrite. Then re-run the 300-table
strict sim from prompt 04 and show that hero's points did not drop and errors stayed at zero. If
the patch makes it worse, revert it and say so.

## Strength ordering moved (permuted ranks, short deck, new categories)
Tables were regenerated in prompt 03; the evaluator remaps ranks through `Rules.rank_order`. Patch:
- Confirm the adapter passes DISPLAYED cards and that `Rules` carries the permutation; nothing in
  strategy should know the ranks changed.
- Short deck: straights and flushes rank differently and hit more often. Lower the value threshold
  for flushes by one tier and raise it for straights; drop the open-ended draw equity to the short
  deck value (about 2.4x outs instead of 2x). Set via `Config.postflop`.
- New categories (e.g. a five-of-a-kind, a new wild rule): if `hyperion/drills/variants.py` has a
  `score_hand` for it, pass it to the engine; otherwise treat the new category as the nuts when held
  and ignore it when not.

## Information moved (extra or fewer hole cards, swaps, exposed cards, two boards)
- Extra hole cards: preflop ranks by the best two-card class plus a bonus for a pairing or suiting
  third card (prompt 03 step 4). Tighten opens by one position step because everyone's hands are
  stronger. Postflop needs no change: the evaluator takes 5 to 8 cards.
- Discard decisions (toss or hold'em): discard the card that minimizes the best two-card class loss;
  if the discard goes to the board, prefer discarding a card that does not pair or suit your keepers.
- Swaps on later streets: a made hand on the flop is worth less. Multiply value thresholds on streets
  before the last swap by 1.15 and prefer checking back medium hands; after the last swap, standard.
- Exposed cards: feed them into the dead-card set for draws; nothing else.
- Two boards: evaluate each; bet when ahead on both, check-call when split, fold when behind on
  both. Use `Config.postflop` sizes halved, since pots split.

## Payoff moved (bounties, auctions, odd point tables)
- Bounties: when a bounty applies to the current hand for us, add its expected chip value to the pot
  in every pot-odds and shove-EV comparison (a `bounty_bonus` term in `Spot`). Do not chase bounties
  with hands below the normal threshold by more than one rank step.
- Auctions for a card: bid the chip EV of the card discounted by 30 percent, capped at 10 percent of
  the effective stack; never bid when under 15 big blinds.
- Point tables: paste the real payouts into `Rules.payouts`. Top-heavy tables (first place worth
  more than 40 percent of the pool) lower the ICM risk premium; flat tables raise it. Hero reads the
  payouts; no other change.

## Betting structure moved (pot limit, fixed sizes, antes, different schedule)
- Pot limit: the adapter clamps to `max_raise`; set `Config.postflop` all-in sizes to pot. Push/fold
  below 12 bb becomes bet-pot-or-fold.
- Fixed sizes: map our pot fractions to the nearest legal size in the adapter; Hero does not change.
- Antes: effective pot is bigger preflop; loosen opens by one step and the push/fold depth by 2 bb.
- Schedule: already in `Rules.blind_levels`; push/fold re-solves at startup from the matrix.

Report the override dict you applied and the before and after sim lines.
