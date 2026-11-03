# Prompt 05: the one strategy change the variant forces (minute 40; box 10 minutes)

The rule sheet classified tonight's twist on the <axis> axis. Apply ONLY the matching patch below, as dials
(one JSON dict, `docs/packet/CONTRACTS.md` lists every key) or a single small function, never a rewrite.

Who decides what. If the ship bot (see the switch: `python -m hyperion.ship`) is hybrid3_x or the composite,
rival 3's core decides plain hold'em,
permuted ranks, antes, pot limit, swaps and any schedule or payout table; Hero plays the whole table for short
deck, lowball, wild cards, category orders, hi/lo, two boards, must-use, three or more hole cards, fixed limit,
bounties and exposed cards, and the straddle preflop (`hero:table:<why>` in the bot's route counters). So a
Hero patch below reaches such a bot only on Hero's tables, written `hero.<key>`; the core's dials are
`r3.<name>`. With `--bot hero` (Hero is the ship bot) the Hero keys are written bare.

**The keep rule** (the one rule for this patch; PLAYBOOK Stage 5, hard rule 6 and prompt 00 point here). Measure it
paired, the same tables with and without it: in our simulator with `--variant` when it can play tonight's twist (a
catalog entry, or its hooks as a file), else in the kit's own simulator (the patched and the unpatched zip in the same
tables, two seats each, the same seeds; its CPU clock if it has one). Use the most tables the box allows in the box's
time, never fewer than 600 paired tables in all (pool runs on different seeds). Keep it when the pooled point estimate
is above zero and no paired check is down beyond its 95% interval (each run, and the aware check below). Otherwise
revert it and say so. Drill 11's twin: +0.35 over 1,000 kit-sim tables, every run up: kept.

Dials, in our simulator: `python tools/climb_accept.py --stages window --base '' --cand '{"dials": <the dict>}' --rules
rules_tonight.json --variant <name> --workers 2` (F with and without them on the night field under tonight's rules, 200
seeds x 8 = 1,600 paired tables, about 3 minutes cold; the spec wraps the dials: `{"dials": {"hero.multi_call_shift":
1}}`). A fallback ship bot climb_accept cannot build (hybrid3_x, Hero): `python -m hyperion.sim --tables 600 --seed 11
--mode model --field realistic@ship --rules rules_tonight.json` once as it is and once with `--dials '<the dict>'` (the
same seed is the same tables). A patch that is a function in the adapter, not dials: the kit's simulator, as above.
Kept: `python -m hyperion.ship --set '<the dict>'` writes it into `DIALS` in `hyperion/ship.py` (the kit simulator,
latency, pack and the sim all read it), then one strict run: errors zero.

The night field ignores most twists (only toss, bounty, short deck, river of blood, auction and keep-two have opponents
that play them), so the second check is against opponents that read tonight's rules too, in one command:
`python tools/climb_accept.py --stages aware --aware generic:<variant> --base '' --cand '{"dials": <the dict>}'
--set 10000:10100 --workers 2` (800 paired tables). `<variant>` is the catalog name; for a twist the catalog lacks, first write its Rules and
hooks as a file (copy `hyperion/drills/variant_file_example.py`: name the variant in `Rules.extras["variant"]`, give
the hooks `restore()` if their public state is published under another name) and pass `generic:path/to/file.py:variant`.
The command builds the twist's table if missing (catalog: committed; a new twist 15-45 s) and pairs F and the
candidate in `generic_aware`, whose Monte Carlo, TAG and push/fold seats deal, score and pay through the variant's own
hooks. Rehearsed on a twist the catalog lacks: 2.4 minutes end to end (table 14 s) at two workers. Down beyond noise
there, the keep rule reverts the patch whatever the night field said.

## Strength ordering moved (permuted ranks, short deck, new categories)
The evaluator remaps ranks through `Rules.rank_order`. If prompt 03 ended on its restore branch,
caption every line "on hold'em tables" and expect the patch to do nothing. Patch:
- Confirm the adapter passes DISPLAYED cards and that `Rules` carries the permutation; nothing in
  strategy should know the ranks changed. The shell remaps the cards before the core sees them: no dial.
- Short deck (Hero's table): set the short-deck keys listed in CONTRACTS.md under postflop, as
  `hero.postflop.<key>` on a core-based ship bot, else no change.
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
- Deal five, keep two (CMU 2026, catalog `deal5_keep2`): Hero answers `{"decision": "keep", "hole", "board",
  "revealed"}` with two indices (the best pair by its flop read, revealed discards dead) and prices five cards
  from `tables/variants/deal5_keep2/heads.json` when the rules name the variant; another deal-N-keep-2 needs
  `tools/gen_keep2.py` rerun for its N (or Hero plays the label view: loose, measured 78% VPIP at N = 5).
- Swaps on later streets (the core plays them; swap_holdem and swap_one_turn are READY in the variant matrix,
  hybrid3 +0.59 ± 0.38 over Hero on swap_holdem): no dial on a core-based ship bot. With `--bot hero`: a made hand
  on the flop is worth less; multiply value thresholds on streets before the last swap by 1.15 and prefer
  checking back medium hands; after the last swap, standard.
- Exposed cards (Hero's table): feed them into the dead-card set for draws (heads-up, the known-cards dial below prices
  them too).
- Cards we know an opponent holds (a twist shows us some of his cards, or deals cards several players share, as
  Chain Hold'em's links in drill 9): in the adapter, pass them as `make_observation(..., extras={"known": {seat:
  (cards,)}})`, seats as the observation numbers them, our own cards included when he holds them too (a shared card
  is in both hands); face-up cards may stay in `{"exposed": {seat: card}}`. Then `{"hero.known_cards": "pre"}`
  (Hero's tables): heads-up before the flop Hero reads its hand as the class whose equity is ours against him, a
  shared card counting for both hands (`hyperion/strategy/known.py`; prepared for Chain heads-up, Chain against one
  neighbour and one face-up card; `python -m hyperion.strategy.known --build M,S,X,U` adds a shape in about a minute
  at two workers). Measured on Chain in our sim: +1.06 ± 0.58 against realistic, +0.73 ± 0.48 against generic
  aware; kit G's own simulator +0.28 ± 0.83 (2,400 tables, level); exposed_card +0.19 realistic, +0.15 generic aware. `"pre,post"` also reads
  the hand after the flop with the shared cards on the board: no better. For the generic aware check, the variant
  file's `extras` hook reports them keyed by viewer, `{"known": {viewer: {seat: cards}}}`
  (`docs/drills/drill9/chain_variant.py`).
- Two boards (Hero's table): evaluate each; bet when ahead on both, check-call when split, fold when behind
  on both. Use `Config.postflop` sizes halved, since pots split.

## Payoff moved (bounties, auctions, odd point tables)
- Bounties (Hero's table): when a bounty applies to the current hand for us, add its expected chip value to
  the pot in every pot-odds and shove-EV comparison (a `bounty_bonus` term in `Spot`). Do not chase bounties
  with hands below the normal threshold by more than one rank step.
- Auctions for a card (MIT 2024, catalog `auction`): the shell's Hero bids through `variant_decide({"decision":
  "bid", "hole", "board", "pot", "max_bid", "n_bidders"})` with the price at which winning and losing the card come
  out level (`tables/auction_bid.json`), capped at a third of the stack: the patch is the adapter routing the kit's
  bid request there, and `charges_dead`-style accounting in the sim if the price goes to the pot. Bidding nothing
  measured -0.56 ± 0.34 a table (Hero, realistic_auction, 200 seeds). A first-price auction (pay your own bid)
  wants the bid shaded, by (n - 1) / n for n bidders on the textbook uniform-value rule: not measured here.
- Pots settled by street (each betting round's chips a pot of their own, won by the best hand as it stood on that
  street; drill 11's Tranche Hold'em: two cards preflop, a preflop all-in has no board). Our engine plays it from two
  Rules extras keys, each usable alone: `"settle": "street"` and `"no_runout": true` (no cards once the betting is
  over); the catalog's `tranche_holdem` is kit I's twist (`--variant tranche_holdem`; aware field
  `tranche_holdem_aware`, and `generic:tranche_holdem`). Tonight: put the keys and `"variant"` in rules_tonight.json's
  extras, and have the adapter pass the earlier streets' pots, `make_observation(..., extras={"tranches": (T0, T1,
  ...)})` (kit I: `v.tranches[:v.street]`). The dials read the rule, not the adapter: `{"tranche_twin": "all",
  "hero.tranche": "now,sunk", "hero.tranche_claim_early": 0.25}`. The twin is drill 11's kept patch as a dial (every
  preflop decision, for every member of F, sees the hold'em class at the same combo percentile as our hand's two-card
  rank: a pair over any non-pair, then the higher card, then the lower; 22 as ATs, KQ as A3s; with `no_runout` alone
  only the all-in decisions). `now` reads the hand as it is after the flop (draws count for nothing); `sunk` prices a
  call against this street's pot, (call - claim) / (this street's chips + call), where the claim is the earlier pots
  times our chance of holding each. It counts in full where the call ends the betting and a quarter before (all of it
  before measured -0.18). Our sim, 200 seeds x 8 (realistic / tranche aware / generic aware): the twin alone +0.03 /
  -0.02 / +0.01, all three dials +0.09 / +0.05 / +0.04, each level (docs/drills/climb/vj-log.md); kit I's simulator,
  the three dials +0.28 over 1,200 tables, every run up. Keep or revert by the keep rule above. For a twist of this
  family the two keys cannot express, the twin goes in the adapter (`twin_hole` in docs/drills/drill11/adapter.py,
  kept in drill 11 at +0.35 over 1,000 tables of the kit's simulator) and the kit's simulator measures.
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
