# R7: the all-in runout term in climb_accept

Branch climb/r7-runout, from main eecf4d8. Brief (coordinator, 2026-11-03): item 6 of docs/research/Edges against strong
opponents.md (evidence in notes/.../poker_ai_literature.md §11). Implement the term as an option of climb_accept, off by
default, then validate it before anyone uses it: zero mean on 400 screen-ish seeds (screen 10000-10199 plus our own
50000+; never H1-H21, 20000-41399, or the judge set), the same verdicts on two known comparisons (batch 5 against batch
4; S5, rejected), and the interval ratio per cell. Findings go at the top when done.

## Findings (2026-11-03, 11:45)

The checks pass. The term is unbiased as far as any of our measurements can resolve, it leaves both known verdicts
where they were, and it narrows the climb's intervals by a median 1.30x. That is a variance cut of 1.7x, on top of
duplicate deals and pairing, against the 1.07x the literature found for a chance-only correction on Pluribus' 6-max
hands (poker_ai_literature §11). A draft protocol addendum is at the end of this section.

1. **What it is.** `tools/climb_accept.py --runout-term` (off by default). For every hand whose last decision leaves
   board cards to come with two or more players in, every seat alive at the hand has V(actual runout) - mean V over
   the runouts the unseen cards allow subtracted from its points. V is the seat's ICM points on the post-hand stacks
   over the cell's own payouts, with a seat busted in the hand given its place's points as the engine places it. Turn
   and flop runouts are enumerated (at most 1,100); preflop draws 50 from `Random("runout/<seed>/<rotation>/<hand>")`.
   The code is `tools/runout_term.py`: a Table subclass with read-only overrides, outside hyperion/. The engine's code
   is untouched and climb_accept's code version stays c11b90b8ae, so merging invalidates no cache.
2. **Play unchanged.** 211 term chunks have a plain chunk of the same key (27 of F's screen cells from S16's cache, and
   the 50k night chunk of all three specs): about 42,000 tables, every raw sample identical. The table's three
   generators are untouched (tested). climb_accept stops on any mismatch.
3. **Zero mean.**
   - Fast field (seven simple bots), 6,000 seeds of hold'em and 3,000 each of hi_lo, short_deck, omaha_four and
     knockout_bounty: every bot's term is within ±0.01-0.02 points a table seed of zero. A lean for the station on
     seeds 60000-62999 (the same deals under three deck-keeping rules) did not replicate on 66000-71999, event by event
     and street by street.
   - Real fields, each spec's term (per spec per cell): sum z^2 40.1 over 40 cells (batch 4) and 51.6 over 40 (F) in the
     batch 5 run, 33.6 and 32.4 over 27 in the S5 run, 9.8 / 4.0 / 3.2 over 7 at 400 seeds. Batch 4's night_hard term,
     z +2.75 at 400 seeds, was re-run on 400 fresh seeds (50200-50599): +0.009 ± 0.037, z +0.48.
   - The paired term (cand - base, the part that can move a verdict): sum z^2 27.4 over 34 cells and 13.9 over 27
     (screen), 10.0 and 3.5 over 7 (400 seeds), z +0.69 on the fresh night_hard seeds. No sign of bias.
4. **Same verdicts.**
   - Batch 5 against batch 4 (--aim strong, screen, every stage): ACCEPT raw, ACCEPT corrected, every check the same.
   - S5 against F (--aim exploit, screen, every stage): REJECT raw, REJECT corrected. Raw rejects on realistic and
     top_heavy down; corrected rejects on realistic and antes_from_level_3 down. H14 rejected S5 on all three of these
     cells (plus night_hard).
   - Cell flags changed in 7 of 61 cells, plus top in each of the two 400-seed pools. Every change is between UP and
     level or between level and DOWN, at the edge of its interval. None is between UP and DOWN.
   - The largest paired term among the changed cells is batch 5's exploit at 10/7/5, +0.101 ± 0.090 (z 2.2): UP raw,
     level corrected, i.e. batch 5 ran luckier in that cell's all-ins. The rest are within |z| ≤ 1.6.
5. **Interval ratio** (raw interval / corrected), by stage:

   | stage | batch 5 - batch 4 (screen) | S5 - F (screen) | 400 seeds pooled |
   |---|---|---|---|
   | confirm (night) | 1.21 | 1.22 | 1.23 / 1.30 |
   | guards | 1.27-1.39 | 1.00-1.40 | 1.25-1.34 / 1.15-1.68 |
   | elite | 1.21-1.52 | 1.21-1.48 | - |
   | exploit | 1.15-1.62 | 1.22-1.54 | - |
   | variants (100 seeds) | 1.05-1.37 | 0.98-1.28 | - |
   | median | 1.30 (34 cells) | 1.33 (27 cells) | 1.27 / 1.28 |

   Heads-up and three-handed cells gain the most (exploit3_hu 1.62, exploit3_3 1.59, adapt_3 1.54), lowball,
   top_heavy and realistic for S5 the least (0.98-1.05). A ratio from 100-200 seeds is itself uncertain by roughly
   ±5-10%. In seeds, the same interval needs about 59% of them (1/1.30^2).
6. **Cost.** About 5% of a table's time (night, F: 0.55 s of term in 9.9 s profiled). Term chunks are cached apart
   (`.rt-<version>.json`), so the first run with the term replays its base once per set.
7. **Limits.**
   - The term is zero, and the sample raw, on the 10 catalog twists whose hooks act after the last decision:
     toss_or_holdem, three_card_blind_discard, swap_holdem, swap_one_turn, two_boards, bonus_card, auction,
     deal5_keep2, bounty, river_of_blood. Covering them needs each runout replayed through the hooks.
   - Judges and aware stages: the option runs there and the argument holds, but they are not measured here (the judge
     set is not for workers).
   - Only the chance part of AIVAT. The decision terms (§11: "the action terms are where the gain is") would need a
     value per action of our own mixed decisions; not attempted.
   - Not done for lack of time at load 20-50: the 50k half of elite, exploit and variants (screen only, 200 and 100
     seeds).

### Draft protocol addendum (for docs/decisions.md; the coordinator's to place and number)

> **Addendum N: the all-in runout term (R7, 2026-11-03).** From the first acceptance run started after this entry,
> every climb_accept run (screen, held-out, window) adds `--runout-term`. The verdict is read on the corrected paired
> delta by the unchanged rule: UP / DOWN beyond the 95% interval of the per-seed paired difference. Stages, aims,
> addenda 6-10, held-out sets and seed counts stay as they are.
>
> *The term.* At each hand whose last decision leaves board cards to come with two or more players in, each seat alive
> at the hand has V(actual runout) - mean V over the runouts the unseen cards allow subtracted from its points. V is
> the seat's ICM points (Malmuth-Harville) on the post-hand stacks over the cell's own payouts, a seat busted in the
> hand taking its place's points as the engine places it. Runouts: all combinations when at most 1,100 (turn, flop),
> else 50 drawn from `Random("runout/<table seed>/<rotation>/<hand>")` (preflop). This is fixed as tools/runout_term.py
> at version 198453df, the tag in every term chunk's file name. Changing that file is a protocol change: repeat R7's
> checks before the changed term judges anything.
>
> *Why it is allowed.* Given everything before the event, the cards to come are uniform over the unseen cards and no
> bot sees more than its Observation, so the term has mean zero for any V fixed in advance and the corrected mean is
> unbiased. R7 (docs/drills/climb/r7-log.md) found:
> - no bias at 6,000-12,000 fast-field seeds, nor in the paired term on any real cell (61 at 200 seeds, 14 at 400);
> - the same verdicts on batch 5 against batch 4 (ACCEPT) and S5 against F (REJECT);
> - a median interval ratio of 1.30 (0.98-1.62 by cell);
> - identical play on 211 chunks.
>
> *Rules.*
> 1. One estimator per decision, fixed before the run starts. A run started before this entry is read raw; a run
>    started after it is read corrected. Never run both and keep the one that passes, because that inflates false
>    accepts. A set already measured is not re-read with the other estimator to change a verdict.
> 2. The raw delta and flag stay printed beside each cell and in the verdict JSON, for the record. If a cell's raw
>    and corrected flags ever point opposite ways (UP against DOWN), log it and replicate that cell on the next set as
>    addendum 7 does. R7 saw none.
> 3. The gain is taken as narrower intervals, not fewer seeds: held-out sets stay at 400 (the climb's effects sit near
>    noise).
> 4. Where the term is zero by construction (twists whose hooks act after the hand's last decision: the ten catalog
>    entries in tools/runout_term.py's doc, and any file variant with on_street, on_payout, next_card or settle), the
>    cell is read raw. That is the same number, so nothing changes there.

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

## The validation runs (milestone 3)

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
  help (why is not measured here; a ratio from 100-200 seeds is itself uncertain by about ±10%), exploit3_hu 1.47,
  adapt_3 1.54.

## 400 seeds pooled: confirm and guards (milestone 6)

Our own 50000-50199 (11:14 batch 5, 11:28 S5; 2 workers) pooled with the screen chunks above, through climb_accept's
own rule (scratch pool.py --pool). Both verdict lines read REJECT only because these two stages alone cannot meet
the aims' own conditions (an elite cell up for --aim strong, an exploit cell up for --aim exploit); the checks that
can be compared agree, raw and corrected.

**B5 - B4, 400 seeds pooled (10000-10199 + 50000-50199), confirm and guards**

| stage | cell | n | raw delta | | corrected | | ratio | term base | term cand | term c - b (z) | events b/c |
|---|---|---|---|---|---|---|---|---|---|---|---|
| confirm | night | 400 | +0.002 ± 0.054 | level | +0.021 ± 0.044 | level | 1.23 | +0.006 ± 0.034 | -0.012 ± 0.034 | -0.018 ± 0.030 (-1.2) | 69/70 |
| guards | night_hard | 400 | -0.005 ± 0.058 | level | +0.032 ± 0.046 | level | 1.25 | +0.052 ± 0.037 | +0.015 ± 0.038 | -0.037 ± 0.037 (-2.0) | 66/66 |
| guards | realistic | 400 | -0.004 ± 0.048 | level | -0.015 ± 0.038 | level | 1.27 | -0.001 ± 0.033 | +0.010 ± 0.032 | +0.011 ± 0.024 (+0.9) | 74/74 |
| guards | top | 400 | +0.042 ± 0.059 | level | +0.073 ± 0.045 | UP **≠** | 1.29 | +0.029 ± 0.041 | -0.002 ± 0.040 | -0.031 ± 0.039 (-1.6) | 65/66 |
| guards | night @10/7/5/4/3/2/1/0 | 400 | +0.031 ± 0.097 | level | +0.045 ± 0.075 | level | 1.28 | +0.008 ± 0.057 | -0.006 ± 0.052 | -0.014 ± 0.054 (-0.5) | 69/70 |
| guards | night @50/25/12/6/3/2/1/1 | 400 | +0.376 ± 0.588 | level | +0.223 ± 0.465 | level | 1.27 | +0.094 ± 0.377 | +0.247 ± 0.348 | +0.153 ± 0.384 (+0.8) | 67/68 |
| guards | night +double | 400 | -0.002 ± 0.049 | level | +0.011 ± 0.037 | level | 1.34 | -0.002 ± 0.040 | -0.015 ± 0.041 | -0.013 ± 0.034 (-0.7) | 72/72 |

- z of the term (base): 7 cells, sum z^2 9.8, |z| > 1.96 in 1, max |z| 2.72
- z of the term (cand): 7 cells, sum z^2 4.0, |z| > 1.96 in 0, max |z| 1.39
- z of the term (cand - base): 7 cells, sum z^2 10.0, |z| > 1.96 in 0, max |z| 1.95
- verdict raw: REJECT; corrected: REJECT
  - raw [x] confirm: night not beyond noise down  |  corrected [x] confirm: night not beyond noise down
  - raw [x] guards: none beyond noise down  |  corrected [x] guards: none beyond noise down
- interval ratio: median 1.27, range 1.23-1.34 over 7 cells

**S5 - F, 400 seeds pooled (10000-10199 + 50000-50199), confirm and guards**

| stage | cell | n | raw delta | | corrected | | ratio | term base | term cand | term c - b (z) | events b/c |
|---|---|---|---|---|---|---|---|---|---|---|---|
| confirm | night | 400 | +0.002 ± 0.005 | level | -0.000 ± 0.004 | level | 1.30 | -0.012 ± 0.034 | -0.010 ± 0.033 | +0.002 ± 0.004 (+1.0) | 70/70 |
| guards | night_hard | 400 | -0.002 ± 0.005 | level | -0.001 ± 0.004 | level | 1.27 | +0.015 ± 0.038 | +0.013 ± 0.038 | -0.002 ± 0.004 (-0.9) | 66/66 |
| guards | realistic | 400 | -0.007 ± 0.004 | DOWN | -0.008 ± 0.004 | DOWN | 1.15 | +0.010 ± 0.032 | +0.011 ± 0.032 | +0.001 ± 0.004 (+0.6) | 74/74 |
| guards | top | 400 | +0.003 ± 0.004 | level | +0.003 ± 0.003 | UP **≠** | 1.23 | -0.002 ± 0.040 | -0.002 ± 0.040 | -0.000 ± 0.003 (-0.0) | 66/66 |
| guards | night @10/7/5/4/3/2/1/0 | 400 | -0.010 ± 0.016 | level | -0.007 ± 0.013 | level | 1.28 | -0.006 ± 0.052 | -0.008 ± 0.052 | -0.002 ± 0.011 (-0.4) | 70/70 |
| guards | night @50/25/12/6/3/2/1/1 | 400 | -0.107 ± 0.138 | level | -0.071 ± 0.106 | level | 1.30 | +0.247 ± 0.348 | +0.212 ± 0.347 | -0.036 ± 0.093 (-0.8) | 68/68 |
| guards | night +double | 400 | -0.000 ± 0.005 | level | -0.002 ± 0.003 | level | 1.68 | -0.015 ± 0.041 | -0.013 ± 0.041 | +0.002 ± 0.004 (+0.8) | 72/72 |

- z of the term (base): 7 cells, sum z^2 4.0, |z| > 1.96 in 0, max |z| 1.39
- z of the term (cand): 7 cells, sum z^2 3.2, |z| > 1.96 in 0, max |z| 1.20
- z of the term (cand - base): 7 cells, sum z^2 3.5, |z| > 1.96 in 0, max |z| 1.02
- verdict raw: REJECT; corrected: REJECT
  - raw [x] confirm: night not beyond noise down  |  corrected [x] confirm: night not beyond noise down
  - raw [ ] guards: none beyond noise down (down: realistic)  |  corrected [ ] guards: none beyond noise down (down: realistic)
- interval ratio: median 1.28, range 1.15-1.68 over 7 cells

Read: at 400 seeds the ratios hold (1.23-1.34 for batch 5, 1.15-1.68 for S5), the paired term is within noise
everywhere (sum z^2 10.0 and 3.5 over 7 cells), and every per-spec term is within noise but one: batch 4's own term on
night_hard, +0.052 ± 0.037 (z +2.75), positive on both halves (screen +0.056 ± 0.052, 50k +0.048 ± 0.053). One of 14 at
that size is an 8% event, but a same-sign repeat on a second seed set is what a leak would look like, so it was
re-measured on fresh seeds (below). Play unchanged: every term chunk with a plain chunk of the same key (211 chunks,
27 of F's screen cells from S16's cache and the 50k night chunk of all three specs, about 42,000 tables) has identical
raw samples.

## Batch 4's night_hard term on fresh seeds (milestone 7)

`one_cell.py` (scratch; climb_accept's own run_cells and gather on one cell), night_hard, 50200-50599, batch 4 and F,
2 workers, 11:39: batch 4's term +0.009 ± 0.037 (z +0.48), F's +0.023 ± 0.039 (z +1.15), paired +0.014 ± 0.038 (z
+0.69). Not replicated: the z +2.75 at 400 seeds was chance. On these seeds batch 5 - batch 4 is +0.093 ± 0.058 raw
and +0.079 ± 0.045 corrected (both UP), ratio 1.28.

Tests after the runs: tests/test_runout_term.py, test_climb_accept.py, test_generic_aware.py, test_h5_drill9.py,
test_sim_adapt.py, test_sim_engine.py, test_sim_runner.py: 116 passed.

Scratch, for whoever re-checks (goal/r7/): b4.json and s5.json (the specs); main_run2.sh and main_run3.sh (the runs);
A_*.md / B_*.md (climb_accept's printouts); pool.py and summary.py (the raw verdict and the pooled 400 from the cached
chunks, through climb_accept's own rule); cheap.py and events.py (the fast field); one_cell.py; ca/ (every chunk).
