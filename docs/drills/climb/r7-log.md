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

## Zero mean at high power, on a fast field (milestone 2)

A field of seven simple bots (tag twice, nit, station, maniac, naive, random, allin; model mode, 8 rotations a seed,
SW.SEED 7), our own seeds 60000+, nothing to do with any held-out set. Scratch `goal/r7/cheap.py` (per table seed,
each bot's raw and corrected sample) and `goal/r7/events.py` (per event, by cards to come). Term = raw - corrected.

Per table seed (95% intervals; sd ratio = raw sd / corrected sd, unpaired):

| rules, seeds | allin | maniac | naive | nit | random | station | tag | sd ratio |
|---|---|---|---|---|---|---|---|---|
| hold'em, 60000-65999 | -0.003 ± 0.013 | +0.001 ± 0.012 | -0.005 ± 0.013 | -0.000 ± 0.008 | +0.001 ± 0.012 | +0.011 ± 0.012 | -0.005 ± 0.007 | 1.07-1.31 |
| hi_lo, 60000-62999 | -0.014 ± 0.022 | +0.002 ± 0.021 | -0.009 ± 0.020 | -0.001 ± 0.013 | -0.003 ± 0.019 | +0.026 ± 0.020 | -0.010 ± 0.013 | 0.99-1.32 |
| short_deck, 60000-62999 | +0.007 ± 0.018 | -0.015 ± 0.017 | -0.003 ± 0.018 | +0.009 ± 0.013 | +0.011 ± 0.017 | -0.007 ± 0.016 | +0.004 ± 0.012 | 1.10-1.26 |
| omaha_four, 60000-62999 | -0.002 ± 0.016 | +0.004 ± 0.016 | +0.007 ± 0.017 | +0.001 ± 0.013 | -0.001 ± 0.016 | -0.006 ± 0.015 | +0.007 ± 0.013 | 1.10-1.31 |
| knockout_bounty, 60000-62999 | -0.013 ± 0.018 | -0.003 ± 0.018 | -0.004 ± 0.018 | -0.004 ± 0.011 | +0.004 ± 0.017 | +0.023 ± 0.017 | -0.009 ± 0.010 | 1.16-1.42 |

33 of 35 within their 95% interval; the two outside are the station, which leans up on all three of hold'em (z +1.84),
hi_lo (+2.53) and knockout_bounty (+2.78)
on the same seeds 60000-62999. Those three rules keep the deck, so they replay the same deals with the same
deterministic station: one lucky realization seen three times, not three. short_deck and omaha_four, which change the
deck, give -0.85 and -0.79. Replicated on fresh seeds 66000-71999 (hold'em, per event, split by cards to come):

| bot | turn (1 card, enumerated) | flop (2, enumerated) | preflop (5, 50 sampled) |
|---|---|---|---|
| station | +0.0024 ± 0.0062 (7,766 events) | -0.0033 ± 0.0104 (5,448) | -0.0016 ± 0.0157 (63,616) |
| tag | +0.0003 ± 0.0024 (40,974) | -0.0034 ± 0.0025 (44,194; z -2.64) | +0.0001 ± 0.0014 (245,861) |
| nit | -0.0010 ± 0.0021 | +0.0018 ± 0.0025 | +0.0004 ± 0.0016 |
| (all seven) | sum z^2 15.7 over 21 cells (expected about 21; the seat terms sum to zero, so a little less) | | |

The station is clean on fresh seeds; tag's flop z -2.64 is 1 of 21 (16% chance of one that size). No bias is
detectable: at most about 0.01 points a table seed on hold'em, 0.02 on the twists, which is below what the
climb's cells resolve (±0.03-0.1). The unpaired sd falls 1.1-1.4x on these fields (variance 1.2-2x).

Note: the per-event run (3 workers) overlapped the last five minutes of the cheap run (3 workers) by mistake: my
`ps | grep` check came back empty through the command-rewriting hook and I took the cheap run for dead. Six processes
for about five minutes; checks since use pgrep.

## The validation runs (milestone 3, running)

Plan (scratch `goal/r7/`): batch 5 against batch 4 (`--base '{"dials": BATCH5_OFF}' --cand '{"dials": {}}'`, --aim
strong, as H13 judged it) and S5 against F (S13's spec, --aim exploit, as S13 and H14 judged it), each with
`--runout-term`, stages confirm, guards, elite, exploit, variants. Variants: the 16 catalog entries the term applies to
for batch 5 (on the other 10 the corrected sample is the raw one, so raw and corrected verdicts agree by construction),
and top_heavy, antes_from_level_3, fast_schedule for S5 (S13: the only entries it plays; elsewhere it is F). Screen
10000-10199 every stage (variants on the first 100); our own 50000-50199 confirm and guards only, for 400 seeds pooled.
The full plan (both sets, every stage) was about 13 hours at load 19, so the 50k set was cut to confirm and guards and
the run restarted from the cache at 07:30 (no chunk lost but the three in flight). F's term chunks on the screen set are
checked against the plain chunks of the same key copied from S16's cache (code c11b90b8ae, the same as this branch):
the raw samples must be identical or the run stops; none has stopped. 08:24: the coordinator capped workers at 2 (load
45); the running A screen run finishes at 3, everything after it runs at 2 (`main_run3.sh`).

Interim (B5 - B4, screen, 200 seeds), paired sd raw / corrected: night 1.21, night_hard 1.31, realistic 1.27, top
1.39, night at 10/7/5 1.30, at 50/25/12 1.30, under double blinds 1.34: 1.5-1.9x fewer seeds for the same interval.

## Batch 5 against batch 4 with the term (milestone 4)

`climb_accept --base B4 --cand F --set screen --stages confirm,guards,elite,exploit,variants --variants <the 16>
--variant-seeds 100 --aim strong --runout-term` (09:51, 3 workers); the raw verdict from the same chunks (scratch
`pool.py --raw`: climb_accept's own rule on the raw samples, which are identical to a plain run's: F's matched S16's
plain cells chunk for chunk). Term = raw - corrected; z of the paired term in brackets.



| stage | cell | n | raw delta | | corrected | | ratio | term base | term cand | term c - b (z) | events b/c |
|---|---|---|---|---|---|---|---|---|---|---|---|
| confirm | night | 200 | +0.004 ± 0.079 | level | +0.038 ± 0.065 | level | 1.21 | -0.000 ± 0.049 | -0.034 ± 0.049 | -0.034 ± 0.044 (-1.5) | 69/69 |
| guards | night_hard | 200 | +0.012 ± 0.082 | level | +0.039 ± 0.062 | level | 1.31 | +0.056 ± 0.052 | +0.029 ± 0.054 | -0.027 ± 0.053 (-1.0) | 66/66 |
| guards | realistic | 200 | +0.023 ± 0.065 | level | +0.003 ± 0.051 | level | 1.27 | -0.001 ± 0.048 | +0.019 ± 0.045 | +0.020 ± 0.032 (+1.3) | 75/75 |
| guards | top | 200 | +0.023 ± 0.078 | level | +0.033 ± 0.056 | level | 1.39 | +0.014 ± 0.058 | +0.003 ± 0.057 | -0.010 ± 0.051 (-0.4) | 64/64 |
| guards | night @10/7/5/4/3/2/1/0 | 200 | +0.051 ± 0.136 | level | +0.084 ± 0.104 | level | 1.30 | -0.011 ± 0.080 | -0.043 ± 0.069 | -0.033 ± 0.076 (-0.8) | 68/69 |
| guards | night @50/25/12/6/3/2/1/1 | 200 | +0.293 ± 0.820 | level | +0.266 ± 0.630 | level | 1.30 | -0.046 ± 0.526 | -0.020 ± 0.475 | +0.027 ± 0.525 (+0.1) | 66/67 |
| guards | night +double | 200 | +0.018 ± 0.069 | level | +0.022 ± 0.051 | level | 1.34 | -0.020 ± 0.056 | -0.024 ± 0.057 | -0.004 ± 0.047 (-0.2) | 72/71 |
| elite | elite | 200 | +0.184 ± 0.090 | UP | +0.163 ± 0.073 | UP | 1.24 | -0.011 ± 0.061 | +0.010 ± 0.056 | +0.021 ± 0.058 (+0.7) | 59/60 |
| elite | elite_night | 200 | +0.094 ± 0.077 | UP | +0.063 ± 0.059 | UP | 1.30 | -0.049 ± 0.055 | -0.018 ± 0.056 | +0.031 ± 0.052 (+1.2) | 65/67 |
| elite | mirror | 200 | +0.151 ± 0.089 | UP | +0.179 ± 0.073 | UP | 1.21 | +0.019 ± 0.061 | -0.009 ± 0.058 | -0.028 ± 0.067 (-0.8) | 58/59 |
| elite | elite_b | 200 | +0.130 ± 0.089 | UP | +0.120 ± 0.069 | UP | 1.29 | +0.019 ± 0.065 | +0.029 ± 0.062 | +0.010 ± 0.067 (+0.3) | 59/60 |
| elite | mirror_b | 200 | +0.114 ± 0.103 | UP | +0.134 ± 0.068 | UP | 1.52 | -0.015 ± 0.064 | -0.035 ± 0.061 | -0.020 ± 0.077 (-0.5) | 59/60 |
| exploit | exploit @10/7/5/4/3/2/1/0 | 200 | +0.220 ± 0.159 | UP | +0.119 ± 0.124 | level **≠** | 1.27 | -0.027 ± 0.083 | +0.074 ± 0.082 | +0.101 ± 0.090 (+2.2) | 66/67 |
| exploit | exploit_hu +hu | 200 | +0.113 ± 0.140 | level | +0.149 ± 0.121 | UP **≠** | 1.15 | +0.016 ± 0.093 | -0.020 ± 0.098 | -0.036 ± 0.120 (-0.6) | 4/4 |
| exploit | exploit_3 +three | 200 | +0.105 ± 0.143 | level | +0.102 ± 0.109 | level | 1.31 | -0.036 ± 0.095 | -0.033 ± 0.100 | +0.003 ± 0.108 (+0.0) | 9/10 |
| exploit | exploit2 @10/7/5/4/3/2/1/0 | 200 | +0.090 ± 0.131 | level | +0.121 ± 0.100 | UP **≠** | 1.31 | +0.026 ± 0.082 | -0.005 ± 0.079 | -0.031 ± 0.079 (-0.8) | 67/68 |
| exploit | exploit2_hu +hu | 200 | +0.307 ± 0.149 | UP | +0.341 ± 0.105 | UP | 1.42 | -0.022 ± 0.089 | -0.056 ± 0.089 | -0.033 ± 0.119 (-0.5) | 4/4 |
| exploit | exploit2_3 +three | 200 | +0.237 ± 0.143 | UP | +0.173 ± 0.099 | UP | 1.43 | -0.006 ± 0.097 | +0.058 ± 0.099 | +0.064 ± 0.108 (+1.2) | 9/9 |
| exploit | exploit3 @10/7/5/4/3/2/1/0 | 200 | +0.040 ± 0.131 | level | +0.013 ± 0.098 | level | 1.33 | -0.003 ± 0.085 | +0.024 ± 0.088 | +0.027 ± 0.085 (+0.6) | 68/70 |
| exploit | exploit3_hu +hu | 200 | -0.075 ± 0.131 | level | -0.076 ± 0.081 | level | 1.62 | -0.072 ± 0.101 | -0.071 ± 0.106 | +0.001 ± 0.108 (+0.0) | 4/4 |
| exploit | exploit3_3 +three | 200 | -0.043 ± 0.147 | level | -0.032 ± 0.093 | level | 1.59 | +0.020 ± 0.089 | +0.008 ± 0.110 | -0.012 ± 0.120 (-0.2) | 9/9 |
| exploit | adapt @10/7/5/4/3/2/1/0 | 200 | +0.136 ± 0.135 | UP | +0.130 ± 0.101 | UP | 1.34 | +0.061 ± 0.079 | +0.067 ± 0.077 | +0.006 ± 0.083 (+0.1) | 68/70 |
| exploit | adapt_hu +hu | 200 | +0.060 ± 0.121 | level | +0.094 ± 0.084 | UP **≠** | 1.44 | -0.027 ± 0.097 | -0.061 ± 0.102 | -0.034 ± 0.109 (-0.6) | 4/4 |
| exploit | adapt_3 +three | 200 | +0.052 ± 0.136 | level | +0.027 ± 0.092 | level | 1.47 | +0.048 ± 0.100 | +0.072 ± 0.096 | +0.025 ± 0.097 (+0.5) | 10/10 |
| variants | permuted_ranks (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | -0.078 ± 0.067 | -0.078 ± 0.067 | +0.000 ± 0.000 (+0.0) | 76/76 |
| variants | short_deck (realistic) | 100 | +0.195 ± 0.096 | UP | +0.157 ± 0.085 | UP | 1.13 | +0.020 ± 0.067 | +0.058 ± 0.067 | +0.038 ± 0.045 (+1.6) | 64/68 |
| variants | lowball (realistic) | 100 | +0.019 ± 0.052 | level | +0.035 ± 0.050 | level | 1.05 | +0.030 ± 0.042 | +0.014 ± 0.043 | -0.016 ± 0.032 (-1.0) | 69/71 |
| variants | wild_deuces (realistic) | 100 | +0.492 ± 0.163 | UP | +0.497 ± 0.143 | UP | 1.15 | +0.010 ± 0.079 | +0.005 ± 0.052 | -0.006 ± 0.080 (-0.1) | 71/80 |
| variants | flush_over_full_house (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | +0.012 ± 0.069 | +0.012 ± 0.069 | +0.000 ± 0.000 (+0.0) | 71/71 |
| variants | three_card_keep (realistic) | 100 | +0.206 ± 0.104 | UP | +0.216 ± 0.086 | UP | 1.21 | -0.038 ± 0.067 | -0.048 ± 0.070 | -0.010 ± 0.054 (-0.4) | 67/71 |
| variants | omaha_four (realistic) | 100 | +0.143 ± 0.123 | UP | +0.139 ± 0.090 | UP | 1.37 | +0.007 ± 0.058 | +0.011 ± 0.057 | +0.005 ± 0.069 (+0.1) | 68/74 |
| variants | exposed_card (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | +0.053 ± 0.066 | +0.053 ± 0.066 | +0.000 ± 0.000 (+0.0) | 73/73 |
| variants | knockout_bounty (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | -0.060 ± 0.066 | -0.060 ± 0.066 | +0.000 ± 0.000 (+0.0) | 76/76 |
| variants | top_heavy (realistic) | 100 | +0.657 ± 1.183 | level | +0.427 ± 0.950 | level | 1.24 | -0.364 ± 0.602 | -0.134 ± 0.580 | +0.231 ± 0.591 (+0.8) | 73/74 |
| variants | hi_lo (realistic) | 100 | +0.069 ± 0.155 | level | +0.095 ± 0.134 | level | 1.16 | +0.008 ± 0.072 | -0.018 ± 0.076 | -0.026 ± 0.074 (-0.7) | 80/83 |
| variants | pot_limit (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | -0.015 ± 0.062 | -0.015 ± 0.062 | +0.000 ± 0.000 (+0.0) | 77/77 |
| variants | antes_from_level_3 (realistic) | 100 | -0.033 ± 0.091 | level | -0.006 ± 0.077 | level | 1.19 | -0.022 ± 0.064 | -0.049 ± 0.062 | -0.027 ± 0.049 (-1.1) | 78/78 |
| variants | fixed_raise (realistic) | 100 | +0.000 ± 0.000 | level | +0.000 ± 0.000 | level | - | +0.018 ± 0.060 | +0.018 ± 0.060 | +0.000 ± 0.000 (+0.0) | 62/62 |
| variants | fast_schedule (realistic) | 100 | +0.001 ± 0.088 | level | +0.008 ± 0.079 | level | 1.11 | -0.092 ± 0.071 | -0.099 ± 0.071 | -0.007 ± 0.059 (-0.2) | 76/75 |
| variants | straddle (realistic) | 100 | +0.066 ± 0.104 | level | +0.024 ± 0.094 | level | 1.11 | -0.008 ± 0.063 | +0.033 ± 0.062 | +0.041 ± 0.039 (+2.0) | 73/74 |

- z of the term (base): 40 cells, sum z^2 40.1, |z| > 1.96 in 3, max |z| 2.53
- z of the term (cand): 40 cells, sum z^2 51.6, |z| > 1.96 in 2, max |z| 2.72
- z of the term (cand - base): 34 cells, sum z^2 27.4, |z| > 1.96 in 2, max |z| 2.19
- verdict raw: ACCEPT; corrected: ACCEPT
  - raw [x] confirm: night not beyond noise down  |  corrected [x] confirm: night not beyond noise down
  - raw [x] elite (addendum 8): a strong field beyond noise up (elite, elite_night, mirror, elite_b, mirror_b)  |  corrected [x] elite (addendum 8): a strong field beyond noise up (elite, elite_night, mirror, elite_b, mirror_b)
  - raw [x] guards: none beyond noise down  |  corrected [x] guards: none beyond noise down
  - raw [x] elite: none beyond noise down  |  corrected [x] elite: none beyond noise down
  - raw [x] variants: none beyond noise down  |  corrected [x] variants: none beyond noise down
  - raw [x] exploit: none beyond noise down  |  corrected [x] exploit: none beyond noise down
- interval ratio: median 1.30, range 1.05-1.62 over 34 cells

Read:
- **Same verdict.** ACCEPT raw and ACCEPT corrected, every check the same. Four of the 34 cells that differ between the
  specs change flag between UP and level, none between UP and DOWN: exploit at 10/7/5 UP -> level (the paired term
  +0.101 ± 0.090, z +2.2, the largest of the 34: batch 5 ran luckier than batch 4 in that cell's all-ins), and
  exploit_hu, exploit2 and adapt_hu level -> UP (their raw deltas were within noise and the corrected intervals are
  narrower). Under --aim strong only a DOWN in the exploit stage would count, so the verdict cannot move on these.
- **Zero mean.** Paired term (cand - base, the part that can move a verdict): sum z^2 27.4 over 34 cells, 2 beyond
  1.96 (exploit +2.2, straddle +2.0); expected 34 and 1.7. Per spec: base 40.1 over 40 cells (3 beyond), cand 51.6 over
  40 (2 beyond); the large ones are fast_schedule (-2.5 / -2.7) and permuted_ranks (-2.3 both), where the two specs
  play the same or nearly the same tables, so each pair is one realization, not two. Six cells play identically for
  both specs (permuted_ranks, flush_over_full_house, exposed_card, knockout_bounty, pot_limit, fixed_raise: batch 5's
  dials are gated off there), so their paired term is exactly zero.
- **Interval ratio** (raw interval / corrected): median 1.30 (variance 1.69x: the same interval from 59% of the seeds),
  1.21-1.39 on confirm and guards, 1.21-1.52 on elite, 1.15-1.62 on exploit (heads-up and three-handed highest:
  exploit3_hu 1.62, exploit3_3 1.59, adapt_3 1.47), 1.05-1.37 on the variants (lowball 1.05, omaha_four 1.37).

## S5 against F with the term (milestone 5)

`climb_accept --base F --cand S5 --set screen --stages confirm,guards,elite,exploit,variants --variants
top_heavy,antes_from_level_3,fast_schedule --variant-seeds 100 --aim exploit --runout-term` (10:41, 2 workers), F's chunks
shared with the batch 5 run; the raw verdict from the same chunks as before (pool.py's corrected output is identical to
climb_accept's own, checked).



| stage | cell | n | raw delta | | corrected | | ratio | term base | term cand | term c - b (z) | events b/c |
|---|---|---|---|---|---|---|---|---|---|---|---|
| confirm | night | 200 | +0.003 ± 0.007 | level | +0.003 ± 0.006 | level | 1.22 | -0.034 ± 0.049 | -0.034 ± 0.048 | +0.000 ± 0.005 (+0.0) | 69/69 |
| guards | night_hard | 200 | -0.004 ± 0.007 | level | -0.004 ± 0.005 | level | 1.24 | +0.029 ± 0.054 | +0.029 ± 0.054 | -0.000 ± 0.005 (-0.1) | 66/66 |
| guards | realistic | 200 | -0.009 ± 0.006 | DOWN | -0.008 ± 0.006 | DOWN | 1.00 | +0.019 ± 0.045 | +0.018 ± 0.045 | -0.001 ± 0.005 (-0.4) | 75/75 |
| guards | top | 200 | +0.003 ± 0.006 | level | +0.005 ± 0.004 | UP **≠** | 1.35 | +0.003 ± 0.057 | +0.002 ± 0.057 | -0.002 ± 0.004 (-0.8) | 64/64 |
| guards | night @10/7/5/4/3/2/1/0 | 200 | -0.010 ± 0.023 | level | -0.007 ± 0.018 | level | 1.28 | -0.043 ± 0.069 | -0.046 ± 0.070 | -0.002 ± 0.015 (-0.3) | 69/69 |
| guards | night @50/25/12/6/3/2/1/1 | 200 | -0.081 ± 0.189 | level | -0.069 ± 0.156 | level | 1.21 | -0.020 ± 0.475 | -0.033 ± 0.483 | -0.013 ± 0.124 (-0.2) | 67/67 |
| guards | night +double | 200 | -0.001 ± 0.005 | level | -0.002 ± 0.003 | level | 1.40 | -0.024 ± 0.057 | -0.023 ± 0.057 | +0.001 ± 0.004 (+0.3) | 71/71 |
| elite | elite | 200 | -0.004 ± 0.008 | level | -0.001 ± 0.005 | level | 1.40 | +0.010 ± 0.056 | +0.006 ± 0.056 | -0.003 ± 0.005 (-1.2) | 60/60 |
| elite | elite_night | 200 | +0.003 ± 0.008 | level | +0.001 ± 0.006 | level | 1.21 | -0.018 ± 0.056 | -0.016 ± 0.055 | +0.002 ± 0.006 (+0.7) | 67/67 |
| elite | mirror | 200 | -0.001 ± 0.008 | level | +0.000 ± 0.006 | level | 1.38 | -0.009 ± 0.058 | -0.010 ± 0.058 | -0.001 ± 0.006 (-0.5) | 59/60 |
| elite | elite_b | 200 | +0.011 ± 0.008 | UP | +0.010 ± 0.005 | UP | 1.45 | +0.029 ± 0.062 | +0.029 ± 0.062 | +0.001 ± 0.006 (+0.3) | 60/60 |
| elite | mirror_b | 200 | -0.003 ± 0.008 | level | +0.001 ± 0.005 | level | 1.48 | -0.035 ± 0.061 | -0.039 ± 0.060 | -0.004 ± 0.006 (-1.5) | 60/60 |
| exploit | exploit @10/7/5/4/3/2/1/0 | 200 | +0.024 ± 0.024 | UP | +0.024 ± 0.017 | UP | 1.37 | +0.074 ± 0.082 | +0.074 ± 0.083 | +0.001 ± 0.017 (+0.1) | 67/67 |
| exploit | exploit_hu +hu | 200 | +0.158 ± 0.129 | UP | +0.161 ± 0.098 | UP | 1.32 | -0.020 ± 0.098 | -0.023 ± 0.094 | -0.003 ± 0.119 (-0.1) | 4/4 |
| exploit | exploit_3 +three | 200 | +0.040 ± 0.077 | level | +0.036 ± 0.058 | level | 1.33 | -0.033 ± 0.100 | -0.029 ± 0.102 | +0.004 ± 0.064 (+0.1) | 10/10 |
| exploit | exploit2 @10/7/5/4/3/2/1/0 | 200 | +0.011 ± 0.027 | level | +0.016 ± 0.020 | level | 1.36 | -0.005 ± 0.079 | -0.010 ± 0.080 | -0.005 ± 0.022 (-0.4) | 68/68 |
| exploit | exploit2_hu +hu | 200 | +0.600 ± 0.167 | UP | +0.496 ± 0.128 | UP | 1.30 | -0.056 ± 0.089 | +0.048 ± 0.096 | +0.104 ± 0.106 (+1.9) | 4/3 |
| exploit | exploit2_3 +three | 200 | +0.120 ± 0.077 | UP | +0.134 ± 0.058 | UP | 1.32 | +0.058 ± 0.099 | +0.043 ± 0.095 | -0.014 ± 0.066 (-0.4) | 9/9 |
| exploit | exploit3 @10/7/5/4/3/2/1/0 | 200 | -0.001 ± 0.019 | level | -0.001 ± 0.014 | level | 1.39 | +0.024 ± 0.088 | +0.024 ± 0.088 | -0.000 ± 0.016 (-0.0) | 70/70 |
| exploit | exploit3_hu +hu | 200 | +0.045 ± 0.156 | level | +0.010 ± 0.106 | level | 1.47 | -0.071 ± 0.106 | -0.037 ± 0.102 | +0.035 ± 0.126 (+0.5) | 4/4 |
| exploit | exploit3_3 +three | 200 | +0.025 ± 0.061 | level | +0.013 ± 0.045 | level | 1.35 | +0.008 ± 0.110 | +0.021 ± 0.109 | +0.012 ± 0.053 (+0.5) | 9/9 |
| exploit | adapt @10/7/5/4/3/2/1/0 | 200 | +0.001 ± 0.028 | level | -0.006 ± 0.023 | level | 1.22 | +0.067 ± 0.077 | +0.074 ± 0.079 | +0.007 ± 0.020 (+0.7) | 70/70 |
| exploit | adapt_hu +hu | 200 | +0.030 ± 0.155 | level | -0.029 ± 0.107 | level | 1.44 | -0.061 ± 0.102 | -0.002 ± 0.089 | +0.059 ± 0.116 (+1.0) | 4/3 |
| exploit | adapt_3 +three | 200 | +0.045 ± 0.091 | level | +0.013 ± 0.059 | level | 1.54 | +0.072 ± 0.096 | +0.104 ± 0.103 | +0.032 ± 0.074 (+0.8) | 10/10 |
| variants | top_heavy (realistic) | 100 | -0.239 ± 0.191 | DOWN | -0.180 ± 0.194 | level **≠** | 0.98 | -0.134 ± 0.580 | -0.193 ± 0.596 | -0.059 ± 0.153 (-0.8) | 74/74 |
| variants | antes_from_level_3 (realistic) | 100 | -0.006 ± 0.008 | level | -0.009 ± 0.007 | DOWN **≠** | 1.12 | -0.049 ± 0.062 | -0.046 ± 0.062 | +0.003 ± 0.005 (+1.0) | 78/79 |
| variants | fast_schedule (realistic) | 100 | +0.002 ± 0.007 | level | +0.001 ± 0.006 | level | 1.28 | -0.099 ± 0.071 | -0.097 ± 0.071 | +0.002 ± 0.006 (+0.5) | 75/75 |

- z of the term (base): 27 cells, sum z^2 33.6, |z| > 1.96 in 1, max |z| 2.72
- z of the term (cand): 27 cells, sum z^2 32.4, |z| > 1.96 in 2, max |z| 2.68
- z of the term (cand - base): 27 cells, sum z^2 13.9, |z| > 1.96 in 0, max |z| 1.92
- verdict raw: REJECT; corrected: REJECT
  - raw [x] confirm: night not beyond noise down  |  corrected [x] confirm: night not beyond noise down
  - raw [x] exploit (addendum 6): an exploit field beyond noise up (exploit @10/7/5/4/3/2/1/0, exploit_hu +hu, exploit2_hu +hu, exploit2_3 +three)  |  corrected [x] exploit (addendum 6): an exploit field beyond noise up (exploit @10/7/5/4/3/2/1/0, exploit_hu +hu, exploit2_hu +hu, exploit2_3 +three)
  - raw [x] exploit: none beyond noise down  |  corrected [x] exploit: none beyond noise down
  - raw [ ] guards: none beyond noise down (down: realistic)  |  corrected [ ] guards: none beyond noise down (down: realistic)
  - raw [x] elite: none beyond noise down  |  corrected [x] elite: none beyond noise down
  - raw [ ] variants: none beyond noise down (down: top_heavy (realistic))  |  corrected [ ] variants: none beyond noise down (down: antes_from_level_3 (realistic))
- interval ratio: median 1.33, range 0.98-1.54 over 27 cells

Read:
- **Same verdict.** REJECT raw and REJECT corrected, and for the same kind of reason H14 gave (realistic, night_hard,
  top_heavy and antes_from_level_3 down there): raw rejects on realistic (-0.009 ± 0.006) and top_heavy (-0.239 ±
  0.191), corrected on realistic (-0.008 ± 0.006) and antes_from_level_3 (-0.009 ± 0.007). Three cells change flag, all
  at the edge of their intervals and none by more than its noise: top level -> UP (+0.003 ± 0.006 -> +0.005 ± 0.004;
  paired term z -0.8), top_heavy DOWN -> level (-0.239 ± 0.191 -> -0.180 ± 0.194; z -0.8, ratio 0.98: the term bought
  nothing in that cell), antes_from_level_3 level -> DOWN (-0.006 ± 0.008 -> -0.009 ± 0.007; z +1.0). None goes
  between UP and DOWN. (S13's screen ACCEPT was against batch 4's F at code b0b7dbc; batch 5's F is the base here, as on
  H14.)
- **Zero mean.** Paired term sum z^2 13.9 over 27 cells, none beyond 1.96 (S5 and F diverge in few hands, so most
  seeds' paired term is exactly zero). Per spec: F 33.6 over 27 (1 beyond: fast_schedule, the same realization as in
  the batch 5 run), S5 32.4 over 27 (2 beyond).
- **Interval ratio:** median 1.33, 0.98-1.54; realistic 1.00 and top_heavy 0.98 are the two cells where it did not
  help (S5's divergences there are not decided by a runout), exploit3_hu 1.47, adapt_3 1.54.
