# Which variant will Pittsburgh (Nov 12) use? A ranked guess

Written 2026-11-01. "P" is my probability that this is the main twist at the Pittsburgh
regional. The rows are roughly mutually exclusive, and they sum to about 100% including the
"plain" and "other" rows. These are judgment calls from the evidence below. The organizers have
published **no hint** (see official-changes.md), so no row is above 11%.

**The top five rows cover about 36%.** Grouped into families, the top five families cover about
51%: deal-extra-then-discard 20%, bounty 11%, extra card for a price 7%, short deck 7%, and
swap/redraw 6%. The team's catalogue covers about 81% of the mass (84% counting plain NLHE). The main gaps are a true
sealed-bid auction (5%), MIT 2023 "River of Blood" (2.5%), CMU-style deal 5 keep 2 (2%), and
"other/unlisted" (7%).

## Ranking

| # | Variant | P | One-line reason |
|---|---|---|---|
| 1 | **toss_or_holdem**: 3 hole cards, discard 1 after the flop (face up 8%, face down like Crazy Pineapple 3%) | **11%** | MIT's latest variant (2026), which Noam Brown's launch post points at, and CMU 2026 also used deal-extra-then-reveal-discard. Adapts to 8-max with dead discards, keeps NLHE and 2-card showdowns, and adds one public-information decision. |
| 2 | **bounty**: MIT 2025 bounty rank per player | **8%** | Trivial on top of an NLHE engine. The payoff twist interacts with ICM, which suits "point distribution may vary by poker variant". Spectator-friendly. |
| 3 | **short_deck**: 6+, flush beats full house | **7%** | The best-known "real" Hold'em variant (Triton). Keeps NL Hold'em, breaks every precomputed 52-card table, and fits 8-max (16+5 of 36 cards). A small team can build it with an off-the-shelf evaluator (pokerkit). |
| 4 | **auction**: sealed-bid (second-price) auction for a third hole card after the flop, MIT 2024. *Not in the catalogue; `bonus_card` is a posted-price stand-in* | **5%** | Citadel Securities is a market maker and an auction is its home turf. It is the MIT variant with the most "game theory" in it. It works 8-way but is harder to explain and build in an hour. |
| 5 | **omaha_four**: 4 hole cards, use exactly 2 (NL or PL) | **5%** | The obvious "different poker variant" to a non-specialist, and it fits 8-max (32+5 cards). But "No Limit" branding and the NLHE exhibits argue against a 4-card game, and PLO would contradict the name. |
| 6 | **two_boards**: two boards, pot split by board | **5%** | Popular in real cash games, close to MIT 2021's multi-board game, and 8-max-safe (16+10 cards). Doubles the evaluation work but needs no new action. |
| 7 | **three_card_blind_discard**: 3 cards, discard before the flop (Pineapple) | **4%** | The simplest member of the discard family: the discard is pure preflop hand selection. |
| 8 | **permuted_ranks**: MIT 2020 hidden rank permutation | **4%** | Loved by AI researchers (inference within a table), but brutal in 1 ms and 60 minutes, and pointless if the permutation is announced. More likely kept for the Finals. |
| 9 | **exposed_card**: one hole card face up | **4%** | A cheap information twist, great on spectator screens, and easy to engine. No precedent in MIT or CMU. |
| 10 | **swap_one_turn**: optional redraw of one hole card at the turn | **3%** | CMU 2025 used a similar revealed one-card redraw, though before the turn rather than at it. One extra decision. |
| 11 | **swap_holdem**: MIT 2022 random swaps (10% flop, 5% turn) | **3%** | Trivial to engine but adds no decision, so the organizers may find it too luck-driven to separate teams. |
| 12 | **three_card_keep**: 3 hole cards, best 5 from all 8 | **3%** | Pure hand-value inflation and the simplest 3-card rule. Less interesting than a discard. |
| 13 | **knockout_bounty**: reward per elimination | **3%** | A common real tournament format. But §4.5 ties points to finishing position, so knockout points would need a rule change, and knockout chips do not fit a fixed-chip SNG. |
| 14 | river_of_blood: MIT 2023, keep dealing board cards while the last card is red. *Not in the catalogue* | 2.5% | A one-line engine change and 8-max-safe, but an obscure, high-variance twist. |
| 15 | wild_deuces | 2.5% | A home-game favourite with dramatic hands, but wild-card evaluation is slow and fiddly in a Python engine. |
| 16 | antes_from_level_3 (as *the* twist) | 2.5% | More likely to show up inside the kit's blind schedule alongside another twist (see add-ons). |
| 17 | deal 5, keep 2, reveal 3 discards (CMU 2026). *Not in the catalogue* | 2% | Most recent CMU variant (Jump Trading sponsor). Fits 8-max on 52 cards (40+5) but not on CMU's 27-card deck. |
| 18 | flush_over_full_house (stand-alone) | 2% | Usually comes bundled with short deck. Alone it is a small, almost invisible twist. |
| 19 | bonus_card (posted-price third card) | 2% | The simpler cousin of the auction. Organizers who want a buy-a-card twist would more likely go full auction. |
| 20 | straddle | 2% | A structure tweak, not a "poker variant". |
| 21 | top_heavy (as the only twist) | 2% | A payout shape is a lever, not a variant. See add-ons. |
| 22 | other hand-ranking reorder (e.g. trips beat straights) | 1.5% | Cheap and invisible. Useful only to break memorized tables. |
| 23 | hi_lo (8-or-better split) | 1.5% | Natural in Omaha, odd in Hold'em, and harder to explain. |
| 24 | lowball (2-7 hold'em) | 1.5% | Inverts everything, which makes it nearly a different game, and is rare as a board game. |
| 25 | pot_limit | 1.5% | Contradicts the event's name. |
| 26 | fixed_raise | 1% | Contradicts the name even more. |
| 27 | fast_schedule | 1% | §4.4 already fixes "increase every 25 hands", so it would need a rule change. |
| 28 | plain NLHE (only payouts/blinds differ) | 2.5% | §3.2 and §5.2 talk about "the poker variant" and "a different poker variant", so a twist is near-certain. |
| 29 | other/unlisted | 7% | For example a "Showtime" exposed-folds rule, a 4-card two-board allocation (a Blotto-like analogue of MIT 2021), or something new. |

### Add-on levers (can co-occur with any row above)

| Lever | P | Why |
|---|---|---|
| Points table steeper than the brief's 10/7/5/4/3/2/1/0 (1st gets ≥40% of total points) | 35% | The organizers' one shown payout is the Castle Challenge four-way game: 9/4/2/0 (60/27/13/0). |
| Last place gets 0 points | 75% | Both the Castle Challenge and the brief's assumption do this. |
| Winner-take-all | 7% | Too swingy for a 10,000-table average with ICM at the cap, but possible for a "plot twist". |
| Antes appear somewhere in the blind schedule | 25% | The kit ships a blind schedule; modern tournament schedules often add big-blind antes. |
| Blinds roughly double each level (vs the gradual 15/30, 25/50 …) | 40% | Unpublished; the brief's gradual schedule is an assumption. |
| All three regionals share one variant | 55% | Wildcards are picked "across the regional games based on their scores", and §6.4 bars sharing the variant "before the event ends". |
| Finals variant is also in the team catalogue | 55% | The Finals is where a hard twist (permutation, auction) is most likely. |
| A pre-announced mid-event change (e.g. T4–T6 differ) | 10% | Shaun Maguire promised "some plot twists", but §9.1 limits post-build changes to necessity, so only a change built into the format announced at the start would fit. |

## Feasibility filter (8-max, 52 cards, 1 ms, 60 minutes)

- Card budget at 8 seats: 2 hole + 5 board = 21; 3 hole = 29; 4 hole (Omaha) = 37; 5 hole = 45;
  two boards with 2 hole = 26. **MIT 2021's six cards over three boards needs 63 cards, so it is
  infeasible.** Royal Hold'em (20 cards) is infeasible. Short deck (36 cards) works with 2 or 3 hole
  cards but not 4. CMU's 27-card deck works with 2 hole cards only.
- MIT 2026's discards join the board heads-up. Eight-handed that would put up to 12 cards on the
  board, so any 8-max adaptation must make discards dead (face up or face down). This is how the
  catalogue's `toss_or_holdem` already treats them.
- Fixed by the rules, so not variant levers: 8-bot tables, 2,000 chips, blinds starting 10/20 and
  rising every 25 hands, a 200-hand cap, ICM at the cap, one decision per ms, Python (§3.3, §4.4).
  Anything that changes betting structure fights the event's name.
- Engine cost: 10,000 tables per tournament, 20 minutes apart. Variants that reuse a standard
  7-card evaluator are cheapest: bounty, exposed card, swap, discard to two, permuted ranks.
  Omaha's 60 combinations per player, wild cards and hi-lo cost more but are still workable.

## Evidence

### MIT Pokerbots (6.9630), verified from mitpokerbots' public engines

| Year | Variant | Source |
|---|---|---|
| 2017 | Heads-up NLHE with discard-and-redraw after the flop and turn | 2017 entrant repos: [Fro116/Pokerbots](https://github.com/Fro116/Pokerbots) ("hand bucketing and discard logic"), [bran-dy-b/Pokerbot-2017](https://github.com/bran-dy-b/Pokerbot-2017) |
| 2018 | Cancelled | [The Tech, Dec 7 2017](https://thetech.com/2017/12/07/pokerbot-cancelled) |
| 2019 | Not verified (the 2019 repo is the vanilla [engine](https://github.com/mitpokerbots/engine)) | |
| **2020** | **Permuted ranks**: a hidden value permutation for the whole match (`PERM`, "Selects a value permutation for the whole game according the prior distribution") | [engine-2020/engine.py](https://github.com/mitpokerbots/engine-2020/blob/HEAD/engine.py) |
| **2021** | **Three boards**: `NUM_BOARDS = 3`, an `AssignAction` putting 6 hole cards two per board, a separate pot per board, 500 rounds | [engine-2021](https://github.com/mitpokerbots/engine-2021) |
| **2022** | **Swap**: each hole card is replaced at random, `FLOP_PERCENT = 0.1`, `TURN_PERCENT = 0.05` | [engine-2022](https://github.com/mitpokerbots/engine-2022) |
| **2023** | **"River of Blood"**: "CARDS MAY CONTINUE TO BE DEALT PAST THE RIVER UNTIL A BLACK CARD IS DEALT"; 400-chip stacks | [engine-2023/engine.py](https://github.com/mitpokerbots/engine-2023/blob/HEAD/engine.py) |
| **2024** | **Auction**: "an auction that occurs immediately after the flop … for a single card … second price auction … Bids are not capped"; `BidAction` | [engine-2024/engine.py](https://github.com/mitpokerbots/engine-2024/blob/HEAD/engine.py) |
| **2025** | **Bounty**: per-player bounty rank, `ROUNDS_PER_BOUNTY = 25`, `BOUNTY_RATIO = 1.5`, `BOUNTY_CONSTANT = 10` | [engine-2025/config.py](https://github.com/mitpokerbots/engine-2025/blob/HEAD/config.py) |
| **2026** | **Three hole cards, face-up discard after the flop**: "you get 3 hole cards pre-flop, and you choose a card to discard face up after the flop". In the engine, the discard is *added to the board*, the flop is 2 cards, and the board ends with 6 cards | [engine-2026 README](https://github.com/mitpokerbots/engine-2026), engine.py ("New action for discarding a card from your hand and adding it to the board"); [juanorbea/pokerbot](https://github.com/juanorbea/pokerbot) ("each player gets 3 hole cards and discards one face up after the flop. Heads-up, 1000 hands, 400-chip stacks") |

Correction for the catalogue: the `bonus_card` docstring calls the auction "MIT 2023". It was
**MIT 2024**; 2023 was River of Blood.

### CMU AI Poker Tournament (CMU Data Science Club with Jump Trading), relevant because Pittsburgh's field will be CMU-heavy

| Year | Variant | Source |
|---|---|---|
| 2024 | 27-card deck (ranks 1–9, 3 suits), 2 hole cards, a 1-card "flop" and a 1-card "river", 4-card hand rankings | [kawashite/poker-engine-2024 engine/evaluate.py](https://github.com/kawashite/poker-engine-2024) |
| 2025 | 27-card deck (2–9 and A, three suits, no quads), plus a **redraw**: "Each player may discard and redraw one card per hand … before the turn … Discarded card and drawn card are revealed"; heads-up, 1,000 hands, Python 3.12 on ARM64 | [riven8567/CMU-Poker-AI docs/rules.md](https://github.com/riven8567/CMU-Poker-AI/blob/HEAD/docs/rules.md); [cmudsc.com/archive/pokerai-2025](https://cmudsc.com/archive/pokerai-2025) ("The specific poker variant will be revealed when the competition starts") |
| 2026 (March) | 27-card deck, "Each player gets 5 hole cards, discards 3 (revealed), keeps 2" | [ZHANGV25/poker-engine-2026](https://github.com/ZHANGV25/poker-engine-2026), [darrenpintoo/PokerAI](https://github.com/darrenpintoo/PokerAI) ("mandatory flop discard (keep 2 of 5)") |

Pattern: both big student competitions converged on "deal extra cards, then discard face up"
in 2026, and both keep the variant secret until launch, as No Limit does. Two of the last three
years of each involved a discard or redraw. A trading-firm sponsor (Jump) stood behind the
small-deck and discard designs.

### Other competitions

- [Husky Hold'em (UW)](https://students.washington.edu/atcuw/hh.html): plain NLHE.
- [Husky Hold'em Bench, NeurIPS 2025](https://neurips.cc/virtual/2025/122372): LLM-written bots
  in 6-player NLHE. This is the AI-lab framing of "can a coding agent build a poker bot", and it
  used no twist.
- Third-party No Limit rehearsal repos guess at hand-ranking reorders, pot limit, raise caps,
  antes, turbo blinds and payout shapes ([mack-dot/poker-gym](https://github.com/mack-dot/poker-gym)),
  crazy pineapple, PLO, royal and short deck ([SpatheGithub/nolimit-arena](https://github.com/SpatheGithub/nolimit-arena)),
  and short deck and PLO4 ([aj002fr/poker_bot](https://github.com/aj002fr/poker_bot)). These are
  guesses, not evidence.

### Organizer signals (all from official-changes.md)

- Name and framing: "No Limit"; exhibits read "NO-LIMIT HOLD'EM" with a 52-card, 2-hole-card
  demo. This keeps NL betting and a Hold'em base likely, and pushes down pot_limit, fixed_raise
  and Omaha.
- Noam Brown, Oct 27: "Every winter, @MIT has run a 1-month class (6.9630) in which students make
  poker AIs … Coding agents have accelerated that process so much that it's now possible to build a
  poker bot in an *hour*." ([X](https://x.com/polynoamial/status/2115125429619343609)). The
  organizers are looking at MIT, which lifts MIT-style twists, especially the most recent (2026)
  and the easiest to port (2025 bounty).
- Shaun Maguire, Oct 27: "rules for the age of AI … some plot twists"
  ([X](https://x.com/shaunmmaguire/status/2115131879452295182)). Expect a twist that breaks
  memorized NLHE strategy: card counts, rankings or information.
- §4.5: "The point distribution may vary by poker variant." The organizers think of payouts as a
  per-variant lever, which favors payoff-sensitive twists (bounty) and makes a steep table likely.
- Castle Challenge: Colonel Blotto with a 9/4/2/0 four-way payout and "We reshuffle the groups
  thousands of times". The designers are game-theory literate and like allocation games and steep
  payouts.
- §7.2: AI-picked hands are replayed "on spectator screens". Visible twists (exposed cards,
  bounties, discards, two boards) show well.
- Sponsor taste: Citadel Securities (market making) favors auctions and pricing; OpenAI favors
  novel rules that show a coding agent adapting in an hour. The likely rule tools are Astra and
  Codex (§3.4).
- 1 ms and 60 minutes: twists that add at most one simple decision type (discard, swap, bid) and
  keep a standard evaluator usable are the buildable ones. The kit's local simulator will carry
  the evaluator in any case.

### What would move these numbers

- The Bay Area regional (Nov 6) and Boston (Nov 9) both come before Pittsburgh. §6.4 bars
  participants from sharing the variant publicly "before the event ends", so don't solicit leaks.
  Do watch the organizers' own posts after Nov 6 and Nov 9. If the regionals share a variant
  (about 55%), expect those posts to stay silent on it until after Nov 12.
- Sequoia's acceptance emails (Pittsburgh decisions by Nov 11, 11:59 PM ET) may describe the kit,
  the environment or logistics.
