# R7: the all-in runout term in climb_accept (running log)

Branch climb/r7-runout, from main eecf4d8. Brief (coordinator, 2026-11-03): item 6 of docs/research/Edges against strong
opponents.md (evidence in notes/.../poker_ai_literature.md §11). Implement the term as an option of climb_accept, off by
default, then validate it before anyone uses it: zero mean on 400 screen-ish seeds (screen 10000-10199 plus our own
50000+; never H1-H21, 20000-41399, or the judge set), the same verdicts on two known comparisons (batch 5 against batch
4; S5, rejected), and the interval ratio per cell. Findings go at the top when done.

## Design (milestone 1)

**The term.** At a hand whose last decision leaves board cards to come with two or more players still in (an all-in
before the river), every seat alive at the hand gets

    term = V(post-hand stacks of the actual runout) - mean of V over the runouts the unseen cards allow

and its corrected points for the table are its points minus the sum of its terms. Every alive seat, not only the two
in the pot: a bust moves everyone up the ladder, and a bystander's ICM moves with it.

**V, fixed before any data.** Each seat's ICM points (hyperion.core.icm, Malmuth-Harville) on the post-hand stacks over
the cell's own points table (Rules.payouts: 8..1, 10/7/5/4/3/2/1/0, 50/25/..., 10/7 heads-up, ...), a seat busted in the
hand placed exactly as the engine places it (more chips at the hand's start = the better place, ties to the lower seat)
and given that place's points. V shares out a fixed total, so the terms of one table sum to zero over its seats.

**Why it is unbiased.** Given everything before the event (every hole card dealt, folded ones included, the board so far
and every decision), the cards still to come are uniform over the cards nobody has seen: the engine deals each hand by a
partial Fisher-Yates over the whole deck, so the undealt slots (the runout, a busted seat's slot, the rest) are
exchangeable. Each event's term therefore has mean zero given the past, whatever V is, and the sum over a table is a sum
of martingale differences. No bot sees anything but its Observation (checked: nothing in hyperion/ outside the engine
reads `runout` or the deck).

**The runouts.** All combinations of the cards to come when they number at most 1,100 (every turn all-in, about 40, and
every flop all-in, 600-1,000), else 50 draws without replacement (preflop: 5 cards, 1.5M boards) from
`random.Random("runout/<table seed>/<rotation>/<hand>")`, never the table's streams. The award depends only on who beats
whom, so runouts are grouped by the dense ranks of the contenders' scores and the award and V run once per distinct
outcome (2-6 per event). Sampling costs nothing in bias: the 50-draw mean has the right expectation; it adds 1/50 of the
term's own variance.

**How it records.** `tools/runout_term.py`: `RunoutTable` is the engine's `Table` with three read-only overrides:
`_ask` notes the board at the hand's last decision, `_award` keeps the stacks before the pots are paid, and
`_finish_hand` computes the term after the engine has finished the hand (the alternative boards go through the
engine's own `Table._award` on a copy of the hand, with the stacks swapped out and back). Nothing is drawn from the
table's generators (`rng`, `vrng`, `srng`; tested) and nothing a bot sees changes. Every event also re-awards the actual
board and raises if that misses the engine's stacks, so a wrong model of the hand's end fails loudly instead of biasing.
`run_tournament_rt` is `hyperion.sim.runner.run_tournament` with `play_table` swapped for the RunoutTable during the
call, and checks its own raw samples against the report's.

It lives in tools/, outside hyperion/, on purpose: climb_accept's code version is the tree of hyperion/ plus
tools/swap.py, so merging this branch changes no cache key, and the engine's play is unchanged by construction (the
engine's code is not touched).

**Where it applies.** Hold'em under any Rules, and twists whose hooks leave the hand alone after its last decision: no
`on_street`, `on_payout`, `next_card` or `settle` (score_hand, score_splits, on_deal, extras, on_bust and the deal's
charges are fine). Of the 26 catalog entries 16 qualify (permuted_ranks, short_deck, lowball, wild_deuces,
flush_over_full_house, three_card_keep, omaha_four, exposed_card, knockout_bounty, top_heavy, hi_lo, pot_limit,
antes_from_level_3, fixed_raise, fast_schedule, straddle); on the other 10 the term is zero and the corrected sample is
the raw one (toss_or_holdem, three_card_blind_discard, swap_holdem, swap_one_turn, two_boards, bonus_card, auction,
deal5_keep2, bounty, river_of_blood). Supporting those needs the hooks replayed per runout, with their cards and
generators; not done.

**climb_accept --runout-term.** Each chunk is cached apart (`<cell>.<off>.rt-<md5 of runout_term.py>.json`, raw samples,
corrected samples and events), so plain cells stay pure; when the plain chunk of the same key is cached, the term
chunk's raw samples must equal it or the run stops. The verdict reads the corrected paired delta; a `## runout term`
table prints per cell the raw delta and flag, the corrected one, the interval ratio, each spec's mean term (raw -
corrected, the zero-mean check) and the term events touching our seats. Off by default; without the flag nothing in
the tool's path changes (the plain job calls run_tournament as before).

**Cost.** About 5% of a table (night, F, 3 seeds x 8 rotations: 0.55 s of term in 9.9 s profiled; 55-70 term events
per table seed touch our seats).

Tests: tests/test_runout_term.py (play identical on hold'em, hi_lo, knockout_bounty, short_deck, omaha_four and
swap_holdem; streams untouched; a turn all-in averages V over exactly the 44 rivers; preflop draws 50 from its own seed;
V's bust places; the 16 / 10 split of the catalog; climb_accept refuses a term chunk whose raw samples differ).
