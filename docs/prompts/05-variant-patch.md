# Prompt 05: the one strategy change the variant forces (minute 40; box 10 minutes)

The rule sheet classified tonight's twist on the <axis> axis. Apply ONLY the matching patch below,
through `Config` overrides or a single small function, never a rewrite. Measure it with prompt 04's
300-table sim in `--mode measure` on the same seed, before and after: keep the patch only if hero's
points rise by more than half their CI, else revert it and say so. Then one strict run: errors zero.

## Strength ordering moved (permuted ranks, short deck, new categories)
The evaluator remaps ranks through `Rules.rank_order`. If prompt 03 ended on its restore branch,
caption every line "Hero on hold'em tables" and expect the patch to do nothing. Patch:
- Confirm the adapter passes DISPLAYED cards and that `Rules` carries the permutation; nothing in
  strategy should know the ranks changed.
- Short deck: set the short-deck keys listed in CONTRACTS.md under postflop, else no change.
- New categories (e.g. a five-of-a-kind, a new wild rule): if `hyperion/drills/variants.py` has a
  `score_hand` for it, pass it to the engine; otherwise treat the new category as the nuts when held
  and ignore it when not.

## Information moved (extra or fewer hole cards, swaps, exposed cards, two boards)
- Extra hole cards: with a variant table set loaded (`tables/variants/<name>`) its classes already price
  the extra card: no bonus, no tightening (`preflop.open_step` 1 measured +0.02 in drill 6, reverted).
  Without one, Hero's label fallback adds the pairing/suiting bonus and one step tighter itself.
  Postflop needs no change: the evaluator takes 5 to 8 cards.
- Discard decisions (toss or hold'em): Hero already chooses through `variant_decide` (keeps the best two
  by its flop read); the patch is the adapter routing the kit's discard there (prompt 02). No new rule.
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
- Point tables: `Rules.payouts` in `rules_tonight.json` is the whole patch; the ICM curve is built from
  it (print the payouts of the `Rules` passed to `new_table` to confirm). No ICM-premium key exists;
  `preflop.shove_call_margin` is a window dial, not this patch. Override `{}`.

## Betting structure moved (pot limit, fixed sizes, antes, different schedule)
- Pot limit: the adapter clamps to `max_raise`; set `Config.postflop` all-in sizes to pot. Push/fold
  below 12 bb becomes bet-pot-or-fold.
- Fixed sizes: map our pot fractions to the nearest legal size in the adapter; Hero does not change.
- Antes: effective pot is bigger preflop; loosen opens by one step and the push/fold depth by 2 bb.
- Schedule: already in `Rules.blind_levels`; push/fold is solved per big blind, so no re-solve (a new
  matrix re-solves; the cache fingerprint forces it).

Report the override dict you applied and the before and after sim lines.
