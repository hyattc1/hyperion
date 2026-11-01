# Prompt 05: the one strategy change the variant forces (minute 40; box 10 minutes)

The rule sheet classified tonight's twist on the <axis> axis. Apply ONLY the matching patch below, as dials
(one JSON dict, `docs/packet/CONTRACTS.md` lists every key) or a single small function, never a rewrite.

Who decides what. The shipped bot (`hyperion/ship.py`: hybrid3_x) has rival 3's core decide plain hold'em,
permuted ranks, antes, pot limit, swaps and any schedule or payout table; Hero plays the whole table for short
deck, lowball, wild cards, category orders, hi/lo, two boards, must-use, three or more hole cards, fixed limit,
bounties and exposed cards, and the straddle preflop (`hero:table:<why>` in the bot's route counters). So a
Hero patch below reaches the shipped bot only on Hero's tables, written `hero.<key>`; the core's dials are
`r3.<name>`. With `--bot hero` (Hero is the ship bot) the Hero keys are written bare.

Measure before and after with prompt 04's 300-table sim in `--mode model` on the same seed:
`python -m hyperion.sim --tables 300 --seed 11 --mode model --field realistic@ship --rules rules_tonight.json`,
then the same with `--dials '<the dict>'`. Keep the patch only if the ship line's points rise by more than half
their CI, else revert it and say so. Kept: write the dict into `DIALS` in `hyperion/ship.py` (one line; the
kit simulator, latency, pack and the sim all read it), then one strict run: errors zero.

## Strength ordering moved (permuted ranks, short deck, new categories)
The evaluator remaps ranks through `Rules.rank_order`. If prompt 03 ended on its restore branch,
caption every line "on hold'em tables" and expect the patch to do nothing. Patch:
- Confirm the adapter passes DISPLAYED cards and that `Rules` carries the permutation; nothing in
  strategy should know the ranks changed. The shell remaps the cards before the core sees them: no dial.
- Short deck (Hero's table): set the short-deck keys listed in CONTRACTS.md under postflop, as
  `hero.postflop.<key>` on the shipped bot, else no change.
- New categories (e.g. a five-of-a-kind, a new wild rule; Hero's table): if `hyperion/drills/variants.py`
  has a `score_hand` for it, pass it to the engine; otherwise treat the new category as the nuts when held
  and ignore it when not.

## Information moved (extra or fewer hole cards, swaps, exposed cards, two boards)
- Extra hole cards (Hero's table): with a variant table set loaded (`tables/variants/<name>`) its classes
  already price the extra card: no bonus, no tightening (`preflop.open_step` 1 measured +0.02 in drill 6,
  reverted). Without one, Hero's label fallback adds the pairing/suiting bonus and one step tighter itself.
  Postflop needs no change: the evaluator takes 5 to 8 cards.
- Discard decisions (toss or hold'em): the shell's Hero already chooses through `variant_decide` (keeps the
  best two by its flop read); the patch is the adapter routing the kit's discard there (prompt 02). No new rule.
- Swaps on later streets (the core plays them; swap_holdem and swap_one_turn are READY in the variant matrix,
  hybrid3 +0.59 ± 0.38 over Hero on swap_holdem): no dial on the shipped bot. With `--bot hero`: a made hand
  on the flop is worth less; multiply value thresholds on streets before the last swap by 1.15 and prefer
  checking back medium hands; after the last swap, standard.
- Exposed cards (Hero's table): feed them into the dead-card set for draws; nothing else.
- Two boards (Hero's table): evaluate each; bet when ahead on both, check-call when split, fold when behind
  on both. Use `Config.postflop` sizes halved, since pots split.

## Payoff moved (bounties, auctions, odd point tables)
- Bounties (Hero's table): when a bounty applies to the current hand for us, add its expected chip value to
  the pot in every pot-odds and shove-EV comparison (a `bounty_bonus` term in `Spot`). Do not chase bounties
  with hands below the normal threshold by more than one rank step.
- Auctions for a card (`variant_decide`, Hero): bid the chip EV of the card discounted by 30 percent, capped
  at 10 percent of the effective stack; never bid when under 15 big blinds.
- Point tables: `Rules.payouts` in `rules_tonight.json` is the whole patch; Hero's ICM curve and the core's
  all-in prices are both built from it (print the payouts of the `Rules` passed to `new_table` to confirm).
  No ICM-premium key exists; `preflop.shove_call_margin` (Hero) and `r3.push_margin` / `r3.call_margin` (the
  core) are window dials, not this patch. Override `{}`.

## Betting structure moved (pot limit, fixed sizes, antes, different schedule)
- Pot limit (the core): the adapter clamps to `max_raise`, and the core's all-in is `max_raise`, the pot cap:
  no dial. With `--bot hero`: set `Config.postflop` all-in sizes to pot; push/fold below 12 bb becomes
  bet-pot-or-fold.
- Fixed sizes (Hero's table): map our pot fractions to the nearest legal size in the adapter; Hero does not change.
- Antes (the core): the antes are dead money in the pot the core reads, so it already steals more.
  No dial: Hero's recipe as core dials (`r3.open_scale` 1.15, `r3.short_bb` 12) measured -0.03 ± 0.19 on
  antes_from_level_3 (200 tables, model mode). With `--bot hero`: loosen opens by one step and the push/fold
  depth by 2 bb.
- Straddle: Hero decides preflop, the core after; no dial.
- Schedule: already in `Rules.blind_levels`; push/fold is solved per big blind, so no re-solve (a new
  matrix re-solves; the cache fingerprint forces it).

Report the dials dict you applied and the before and after sim lines. If the patch is kept, repack
(prompt 04 step 5; read its `bot` line: the dials are recorded) and run `tools/gate.py` on the new zip
(step 6) before I upload it.
