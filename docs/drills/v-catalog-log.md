# v-catalog: two engine bugs fixed, two catalog entries added (2026-11-01)

Branch `climb/v-catalog` from main 27e0cff. Track V of the climb (docs/drills/goal-plan.md, backlog V1; goal-log
21:24, findings 2 and 4; 20:50, the research's gaps). Every number below is model mode (the engine's timeout model,
tools/swap.py's fixed-speed setup) unless it says strict, on the `realistic` field, seed 7, 300 unrotated tables per
entry (variant_matrix.py's convention), at most two processes at a time on a host at load 6-7.

`tools/variant_matrix.py` measured Hero only (bestiary `hero`). It now takes `--bot ship` (F, the composite as
hyperion.ship builds it, in Hero's seat, VPIP counted the same way) and `--mode model`. Scratch scripts (bias probe,
chip-loss probe, per-seed samples for paired differences, dial screens, ablations) live in the session scratchpad
(`va/`), not in the repo.

Commits, in order: f585bfa (matrix --bot/--mode), 512274a (engine: shuffled undealt cards, folded excess to the top
pot), 9dd44c4 (the two entries, F's bid and keep, aware opponents), 248081e (API card), 8da121f (deal5_keep2's head
view and value shift), e1dc30d (bonus_card's price as dead money), 771c910 (bestiary Monte Carlo on five cards,
prompt 05), then this log with PLAYBOOK 4b.

## 1. Bug: four hooks drew extra cards from an unshuffled deck tail

**Cause.** `Table.play_hand` shuffles only the slots it deals (a partial Fisher-Yates over `cards_per_hand`), and
`HooksVariant.on_deal` handed the hooks `deck[cards_per_hand:]`, the untouched tail, in near-deck order. Hooks pop
from the end, so the first extra card was card 51, the ace of spades, unless the deal had swapped it out (21 of 52
slots: 40%).

**Fix (512274a).** HooksVariant shuffles the undealt cards each hand (a full Fisher-Yates) with its own RNG,
`Table.srng = Random(seed * 1_000_033 + 11)`, a fixed number of draws per hand. The deal's RNG and the hooks' `vrng`
are untouched, so every hole card and board is what it was, and rotations stay duplicate (the undealt set and its
shuffled order do not depend on the rotation; tested). Default play never touches `srng` (tested).

**The bias, measured** (probe: every card a hook pops, eight check/call bots; collisions = a popped card that was
dealt this hand or popped twice):

| entry | before: As share of first extra cards, hand 0 (uniform 1.9%) | chi-square, 51 df | after: top card share | chi-square |
|---|---|---|---|---|
| swap_holdem (n = 1,839 of 2,000 seeds) | 60.5% | 33,937 | 2.8% | 76 |
| swap_one_turn (1,992) | 59.9% | 35,991 | 2.8% | 76 |
| two_boards (2,000) | 59.9% | 36,087 | 2.8% | 77 |
| bonus_card (2,000) | 59.9% | 36,087 | 2.8% | 77 |

All extra cards on hand 0, before: chi-square 22,123 / 25,693 / 30,972 / 27,505; after 41-59. Over 20 hands x 300
seeds the bias decays but stays: As 10.0% of first draws, chi-square ~2,250; after, 2.4% and 71. The same seeds feed
the same shuffles, which is why the four "after" rows agree; the 76 is one seed set (p ~ 0.01): over 50,000 seeds the
first popped card's top share is 2.09% and chi-square 61.7 (p ~ 0.15). Collisions: 0 before and after.

**Test.** tests/test_variant_draws.py: for each of the four entries over 1,500 seeds, top share < 4% and chi-square
< 100 (p ~ 5e-5 under uniform; fixed seeds, so the test is exact) for the first and for all extra cards, and zero
collisions; later hands too (two_boards, 15 hands x 200 seeds); the spare is the undealt set, rotation-independent.
On the old engine the uniformity tests fail at 60% (829/1380 .. 895/1500).

**Default play stays bit-identical.** The fingerprint test (tests/test_variants_unseen.py) hashed default Rules,
straddle, antes, fixed limit, hi_lo **and bonus_card and two_boards** into one digest, so no fix to a drawing hook
could keep it green. Split: the five cases that draw no card keep one digest, 8253b28f..., computed on main 27e0cff
before any change and unchanged on every commit of the branch (main's combined digest 4359fed2 was reproduced first);
bonus_card + two_boards get their own, re-pinned at each deliberate change (0e845501 on main, 65125a35 after the
shuffle, bfd7c392 after bonus_card's dead money).

**The four entries before and after** (variant_matrix.py rows; the difference is paired per seed, the same 300 seeds):

| entry | F before | F after | F after - before | Hero before | Hero after | Hero after - before |
|---|---|---|---|---|---|---|
| swap_holdem | 6.36 ± 0.23, 1st | 6.40 ± 0.23, 1st | +0.036 ± 0.285 | 6.15, 1st | 6.22, 1st | +0.072 ± 0.276 |
| swap_one_turn | 6.37 ± 0.22, 1st | 6.38 ± 0.23, 1st | +0.014 ± 0.247 | 6.21, 1st | 6.06, 1st | -0.150 ± 0.228 |
| two_boards | 6.07 ± 0.23, 1st | 6.02 ± 0.23, 1st | -0.055 ± 0.291 | 5.92, 1st | 5.91, 1st | -0.008 ± 0.284 |
| bonus_card | 6.11 ± 0.24, 1st | 6.06 ± 0.25, 1st | -0.050 ± 0.309 | 5.86, 1st | 5.57, 1st | -0.286 ± 0.320 |

All READY before and after, every one inside noise. Pairing does not tighten the interval here: a different extra
card changes the hand's outcome, not a little of it. Hero's bonus_card -0.29 is the largest move; everyone's bought
card used to be an ace 60% of the time on early hands.

## 2. Bug: the pot award could lose chips

**Cause.** `Table._award` built side pots from the contenders' contribution levels and capped every contribution at
the top level, so whatever a folded player had put in above every contender went nowhere.

**Reachability.** The top contributor never faces a bet, so never folds: unreachable in default play. Probe on main
(chips before and after `_award`, 100 tables each, a field of random, tag, loose_aggro, station, maniac, nit and
pushfold): bonus_card 15,494 hands, two_boards 18,773, hi_lo 17,490, swap_one_turn 17,577, bounty 17,756, zero hands
losing chips. tests/test_variant_draws.py also checks 30 random-bot tables with antes: zero.

**Fix (512274a).** The top pot takes what a folded player put in above every contender. Test: a variant that hands
chips back (all but 50 of each contender's contribution on the flop) after utg folded 200: 150 chips vanished before,
the sb's kings now win the main pot and the 150 (deltas [-50, 300, -50, -200]). Default digest unchanged.

## 3. Dead money (engine `charges_dead`), and bonus_card

A hook's `charges` were contributions: the price raised the payer's side-pot level, so nobody who had not paid could
win it and an unmatched price came back to the payer at showdown. MIT's auction payment is "added to the pot" and won
by whoever wins it. New: a hook with `charges_dead = True` puts the charge in the pot as dead money, a pot of its own
won by the best hand among the players still in who had chips behind when it was paid (a player all-in before then
cannot win it, as with a bet made after their all-in). `Table._settle_pot` is the per-pot payment, factored out of
`_award` unchanged (default digest unchanged). Hooks may also set `wants_view = True` to get `view` (stacks, pot,
button, blinds, contributions) before each street; the auction needs stacks (bids are capped at them) and the pot.

bonus_card's own docstring called its price dead money; it was a contribution. In the realistic field every bot buys
(the hook's default) and F buys while the price is at most a tenth of its stack, so the asymmetric case is rare: a
probe on main found no lone-buyer refund in 1,763 showdowns. e1dc30d makes it dead money (its own commit, easy to
drop): F 6.058 -> 6.056 (-0.003 ± 0.022), Hero 5.571 -> 5.575 (+0.004 ± 0.027), paired, same 300 seeds.

## 4. New entry `auction` (MIT Pokerbots 2024, "No-Limit Auction Hold'em")

**MIT's rules, read from mitpokerbots/engine-2024 (engine.py, rules only) and class-resources-2024 ("2024 Variant -
Auction Hold'em.pdf"):**
- When: "Deal flop / Auction for third hole card / Round of betting": right after the flop is dealt, before the flop
  betting (engine: `proceed_street` from street 0 enters street 3 with `auction=True`; the only legal action is a bid).
- Who bids: both players (heads-up, both are in at the flop). "Both players will post a bid without knowledge of the
  other player's bid." Bid range 0..own stack (`bid_bounds`); "Bids are not capped" beyond that. An illegal bid, or
  none, is a bid of 0 (`query` falls back to `BidAction(0)`).
- Price: second price, "the player with the higher bid wins the auction, and puts the losing bid's amount into the pot".
- Ties: "both players put that bid amount into the pot and receive a third hole card".
- Where the chips go: the pot (the winner's stack is debited; the showdown winner takes it).
- What the winner gets: a third hole card from the deck, private; after the auction both bids and both stacks go to
  both players (the `N` message). Showdown: the best five of two or three hole cards and the board.
- Not used: the engine appends each action code, the first bid's `A###` included, to both players' message queues, so
  in that engine the second bidder (the button; the big blind bids first) receives the first bid before bidding. The
  rules say sealed; we implement sealed.

**The 8-max extension (`AuctionHooks`, `variants.auction()`):** every player still in the hand at the flop bids
sealed, an integer 0..stack behind (players all-in before the flop bid 0 and are not asked). The highest bid wins and
pays the **second-highest bid of all** (a Vickrey auction; heads-up that is the loser's bid). Ties at the top: every
tied player gets a card and pays the tied amount, which is the same rule, since the second-highest bid then equals the
top one; everyone at 0 is a tie at 0 and every card is free. The price is dead money for the players who had chips
when it was paid (section 3). After the auction `obs.extras` carries `bids`, `auction_winners` and `auction_price`.
One deviation: a bot that does not answer the prompt (no `variant_decide`, or None) bids a quarter of the pot, capped at
its stack, so a field of unaware bots does not hand out free cards; an answer that is not a number in 0..stack is 0,
as in MIT. The third card comes from the shuffled undealt cards. tests/test_variant_auction_keep2.py checks each rule
with fixed cards, including the side-pot case (a price paid after the big blind's all-in goes with the side pot).

**F's bid** (Hero's `variant_decide({"decision": "bid", ...})`, which the composite's base answers). Winning the card at
price x is worth e_win (pot + x) - x; losing it (a rival pays x) is worth e_lose (pot + x). They are level at
x = d pot / (1 - d), d = e_win - e_lose. `tools/gen_auction.py` tabulates d by Hero's flop read (tier 0..8, outs
bucket) and opponents (1..4+), 2,000,000 Monte Carlo runouts per opponent count, both cases on the same cards
(`tables/auction_bid.json`, 72 cells, 38 s on two workers). Mean d: 0.333 heads-up, 0.265 with two opponents, 0.226,
0.198; highest for air (0.38 heads-up), lowest for strong made hands (a set 0.11). The pot is grown a little for the
stack still to bet (`auction_implied` 0.05 x min(stack / pot, 4)), and the bid capped at a third of the stack and
three quarters of the pot. Examples, pot 120, 1,900 behind, Kd 9s 4c: Ah 7d heads-up 89, Kh Ks 17, Kc Qh 45, Qd Jd on
Kd 9d 4c 67, Ah 7d three bidders 55, five bidders 33, with 60 behind 19. About 3 us a bid.

Screen (Hero, `realistic_auction`, dev seeds 11, 200 tables, paired): defaults 6.110; `auction_implied` 0 +0.062 ±
0.078, 0.15 +0.071 ± 0.159 (defaults kept); **never bidding -0.564 ± 0.335** (bids are worth half a point a table).

**Variant-aware opponent `auction_tag`** (bestiary): ChartTAG plus a bid by hand (0.45 of the pot heads-up, 0.30
three-way, 0.20 beyond; half with two pair or better; ±20% jitter; at most a quarter of the stack) and a read: when
someone else won a card and it did not, it continues only with two pair or better. Field `realistic_auction` = realistic
with the honest Monte Carlo seat and the TAG replaced by `auction_tag`.

**F's rows:**

| field, mode | pts (±95%) | rank | exc | ill | VPIP | bust | p99 us | verdict |
|---|---|---|---|---|---|---|---|---|
| realistic, model | 6.52 ± 0.23 | 1 / 8 | 0 | 0 | 51% | 41% | 171 | **READY**, next tag 5.14 |
| realistic_auction, model | 6.35 ± 0.25 | 1 / 7 | 0 | 0 | 50% | 41% | 244 | **READY**, next auction_tag 5.02 |
| realistic, strict | 6.49 ± 0.23 | 1 / 8 | 0 | 0 | 50% | 43% | 148 | **READY**, next tag 5.15 |

Hero alone (realistic, model): 6.03 ± 0.27, first. On F the rival 3 core plays preflop (two cards, plain hold'em) and
Hero every postflop decision, a third card included (its keep-all read), as on bonus_card.

## 5. New entry `deal5_keep2` (CMU AI Poker Tournament 2026, CMU Data Science Club with Jump Trading)

**CMU's rules, read from the 2026 engine `gym_env.py` ("CMU Poker Bot Competition Game Engine 2026"), as published in
two public team repos (ZHANGV25/poker-engine-2026 and darrenpintoo/PokerAI carry the same file; rules only):**
- Deal: five hole cards each (`NUM_PLAYER_CARDS`), preflop played with all five.
- When: on the flop, after the three board cards and before any flop bet: until a player has discarded, its only legal
  actions are DISCARD and FOLD (`_get_valid_actions`).
- How: the action names two indices to keep (`keep_card_1`, `keep_card_2`); the other three are discarded
  (`NUM_DISCARD_CARDS` 3). An invalid discard is treated as a fold.
- Order and reveal: the flop's acting order, big blind first, then the small blind; the discards are in the opponent's
  observation (`opp_discarded_cards`) at once, so the second player discards after seeing the first's.
- Showdown: the two kept cards and the five-card board; discards are dead.
- CMU's deck is 27 cards (three suits, 2-9 and A), heads-up, 100-chip stacks reset each hand.

**The 8-max adaptation (`Keep2Hooks`, `variants.deal5_keep2()`):** 52 cards and standard rankings (8 x 5 + 5 = 45
cards); every player still in at the flop keeps two and shows three, one at a time in the postflop acting order
(first seat left of the button first), each prompt carrying every discard made before it; players all-in before the
flop discard too. Deviations: a hook cannot fold a player, so an invalid or missing answer keeps `default_keep` (the
best made hand on the flop) instead of folding. Public: `obs.extras["revealed"]` = {seat: three cards} (a new key:
`hyperion/drills/adapter.py` reads `extras["discards"]` as one card per seat).

**F on it.** Five hole cards: the rival cores cannot play the table (`table_reason` "hole_cards"), so Hero plays it
whole; it is the 15th Hero table.
- First measurement (9dd44c4, the label view): **F 5.43 ± 0.22, second to rival1 6.46, VPIP 78%, bust 78%**. The
  label view prices a five-card hand as its best two against two-card hands, so most five-card hands looked like a
  top-30% hand.
- `tools/gen_keep2.py` prices each head (the Chen-best two, `hole_label`'s prefix) among five-card hands: k + 1 players
  dealt five, everyone keeps two on the flop with the default keep, 200,000 deals per k = 1..7, 97 s on two workers,
  thin heads shrunk toward the two-card equity plus the mean shift (`tables/variants/deal5_keep2/heads.json`).
  AA heads-up 0.71 (hold'em 0.85), AKs 0.53 (rank 0.79), KQo is the median five-card hand (rank 0.48), 77 rank 0.34.
  `tables_for` loads it as a "head view" (no tag bonuses, no extra tightening). Dev seeds 11 x 200: F 6.24 ± 0.18,
  VPIP 46%, still second to rival1 6.42.
- Everyone chose their two of five on this flop, so a made hand is worth less than its board tier: `keep_value_shift`
  (Hero's postflop value thresholds up, as before a swap street). Screen (Hero, realistic, dev seeds 11 x 200, paired
  against 0): 0 6.257; **1 6.448 (+0.191 ± 0.131)**; 2 6.510 (+0.253 ± 0.141); 3 6.421 (+0.164 ± 0.147). Kept at 1,
  the smaller step; 2 is level with it.
- The keep (`variant_decide({"decision": "keep", ...})`): the pair with the best flop read (made tier, then draws),
  every revealed discard and its own three as dead cards, the preflop rank breaking ties; ~24 us. Revealed discards
  also come off Hero's postflop outs (scoped to this rule: the held-out `showtime` uses the same extras key for folded
  hands, and the held-out set is not tuned on). Ablations (Hero, dev seeds 11 x 200): the hook's default keep instead
  -0.058 ± 0.095; no revealed dead cards +0.000 ± 0.039. Both small: the default keep (best made hand) is already a
  good keep, and dead cards rarely change a decision.
- The bestiary's Monte Carlo bots sampled five-card opponents here and evaluated 10 cards, building the 9- and 10-card
  lookup tables inside their act() (a 10-table run took 10 s instead of 1.2 s); for rules with hole + board > 8 they
  now sample opponents' two kept cards (771c910). That moved the field, so deal5_keep2 was measured again after it.

**Variant-aware opponent `keep2_tag`** (bestiary): preflop it plays its best two of five from ranges a notch tighter
than ChartTAG's, a notch wider with a second pair or a suited ace among the five; it keeps by made hand, then live
draws (flush and straight outs not among the revealed discards or its own), then high cards; ChartTAG postflop. Field
`realistic_keep2`.

**F's rows (771c910):**

| field, mode | pts (±95%) | rank | exc | ill | VPIP | bust | p99 us | verdict |
|---|---|---|---|---|---|---|---|---|
| realistic, model | 6.61 ± 0.14 | 1 / 8 | 0 | 0 | 47% | 76% | 132 | **READY**, next rival1 6.25 |
| realistic_keep2, model | 6.51 ± 0.15 | 1 / 7 | 0 | 0 | 50% | 78% | 131 | **READY**, next rival1 5.94 |
| realistic, strict | 6.59 ± 0.14 | 1 / 8 | 0 | 0 | 47% | 75% | 136 | **READY**, next rival1 6.23 |

Hero alone (realistic, model): 6.62 ± 0.14, first. The bust rate stays high (76% against ~45% on the other entries):
everyone's hands are strong, so stacks go in more often, and Hero's postflop tiers are still hold'em-calibrated beyond
the one-tier shift. rival1 is the one bot close: through its kit adapter it reads the first two of its five cards, so it
plays a tight random-two preflop and keeps the best made hand.

## 6. The whole catalog for F (e1dc30d, before the Monte Carlo fix, which moves only deal5_keep2)

`tools/variant_matrix.py --bot ship --mode model --tables 300 --seed 7 --field realistic` (354 s on 2 workers):
**25 READY, first on 24**, second on fixed_raise (6.13, level with rival1 6.13), 0 exceptions, 0 inner errors,
0 illegal actions. The rows (pts, rank, VPIP, bust, p99): permuted_ranks 6.76 1 48 33 167; short_deck 6.06 1 45 62 126;
lowball 7.72 1 54 6 151; wild_deuces 7.05 1 59 20 176; flush_over_full_house 6.12 1 45 48 133; toss_or_holdem 6.33
1 46 55 155; three_card_blind_discard 6.24 1 46 63 123; three_card_keep 6.35 1 46 60 228; omaha_four 6.83 1 46 53 198;
swap_holdem 6.40 1 45 42 168; swap_one_turn 6.38 1 46 43 156; exposed_card 5.98 1 43 52 132; two_boards 6.02 1 39 48
139; bonus_card 6.06 1 49 51 142; auction 6.52 1 51 41 171; deal5_keep2 6.56 1 45 78 118; bounty 6.05 1 46 44 223;
knockout_bounty 7.77 1 47 57 117; top_heavy 28.11 1 46 46 287; hi_lo 6.06 1 44 49 198; pot_limit 6.36 1 46 46 261;
antes_from_level_3 6.50 1 48 43 257; fixed_raise 6.13 2 40 41 210; fast_schedule 6.20 1 43 54 268; straddle 6.18 1 53
46 203.

## 7. Docs and tools

- `docs/packet/CONTRACTS.md` regenerated (`python tools/apicard.py`): the four `auction_*` dials and
  `keep_value_shift`. It lists no catalog entries.
- PLAYBOOK 4b: auction and deal5_keep2 in the Information row; the 25 hooks and 15 Hero tables in section 0; a dated
  paragraph with F's matrix.
- Prompt 05: the auction line (it said bid 70% of the card's EV, capped at 10% of the stack, never under 15 bb) and a
  deal-five-keep-two line now point at the shell's decisions.
- `tools/gen_catalog.py` raised KeyError 5 on a five-card entry (its sample counts are keyed 2..4): deal5_keep2's
  `tables` field is "unsupported" with a note pointing at tools/gen_keep2.py.
- `tables/README.md`: auction_bid.json.

## 8. Checks

- Full suite on the final tree (`.venv/bin/python -m pytest -q`): **895 passed, 1 skipped** in 297 s (main had 848
  passed at the held-out merge). The run before it failed one test, tests/test_export_public.py: the auction hook's
  docstring named the competition series in a denylisted spelling; reworded to "MIT 2024". 3 warnings: one is the
  known empty-tables warning of tests/test_strategy_tables.py, the other two were not inspected.
- Default-play digest 8253b28f... on every commit; the drawing digest re-pinned twice, deliberately.
- `tools/variant_matrix.py --bot ship` in strict mode on the two new entries: 0 exceptions, 0 inner errors, 0 illegal.
- Latency of the new decisions: bid ~3 us, keep ~24 us (the test bounds the bid at 200 us); F's p99 on the two
  entries 118-244 us.

## 9. Found elsewhere

- bonus_card's price was a contribution (section 3); fixed in its own commit, e1dc30d, measured level.
- `tools/gen_catalog.py` cannot plan an entry with five hole cards (KeyError on its per-count sample table).
- The bestiary Monte Carlo bots modelled opponents with the rules' hole-card count even when the game keeps two (fixed
  only where it built 9- and 10-card tables; toss_or_holdem's three-card opponents are unchanged).
- `hyperion/drills/adapter.py` (`history_rows`, `dealer_state`) assumes `extras["discards"]` is one card per seat; a
  kit with multi-card discards needs the adapter changed (deal5_keep2 uses `revealed` instead).
- `TossHooks`' comment says the engine passes holes ordered out of position first; it passes seat order. Harmless
  there (no discard prompt shows another seat's discard), wrong for any hook whose order matters (Keep2Hooks orders
  by the button itself).
- Hero never reads toss_or_holdem's face-up discards (`extras["discards"]`) as dead cards, and the same read would
  apply to the held-out showtime's revealed folds; left alone (the held-out set is not tuned on).
- MIT's 2024 engine relays the first bid to the second bidder before it bids (each action code goes to both players);
  the written rules say sealed.
- The climb's acceptance rule (variants stage, `tools/climb_accept.py`) iterates `catalog_names()`: 25 entries now.
- HANDOFF's "23/23 READY" and other docs that count 23 entries predate this branch.
