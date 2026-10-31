# Decisions

Append only. Newest at the bottom. One paragraph each: what was decided, why, what it rules out.

## 2026-10-31 tooling and drills (builder: tools/drills)

- **Generation library lives in `hyperion/tablegen.py`, the CLI in `tools/gen_tables.py`.** The strategy
  needs the same class labeler at runtime for 3-card variants (`hole_label`) and the same texture key
  (`texture_key`); `tools/` is not a package, so the shared functions sit in the package and the CLI is thin.
- **Hole classes for `hole_cards != 2` are `best2+tags`** (Chen-best pair of cards + one tag per extra card:
  pairs / suited / high / low), 676 labels at most for 3 cards. Rejected: full rank-multiset + suit pattern
  (1755 classes for 3 cards, too thin per class in 5 minutes and no reuse of 2-card charts). The best-2 is
  chosen on canonical strength so permuted ranks pick the right pair.
- **Discard variants are modeled with `extras["keep"]`**: showdown scores the best `keep` hole cards (perfect
  hindsight). Equities are an upper bound and an ordering, not a price; the postflop discard decision is a
  bot decision the engine asks for through the hook's `ask` callback.
- **Toss or Hold'em preset is the 8-max adaptation**: discards are face-up but dead, not community cards.
  MIT 2026 heads-up put them on the board, which at 8-max means 12 board cards and best-5-of-14; the
  evaluator stops at 8 cards. If Sequoia keeps MIT's rule, `board_sizes` becomes `(0, 2, 2+n, 3+n, 4+n)` and
  the evaluator needs a best-5-of-many path. Recorded as a known gap, not built.
- **Short deck is `extras["removed_ranks"]` plus a `score_hand` hook**, not a Rules field. Rules is frozen by
  the core builder; the generator honours `removed_ranks` for the deck, the category reorder (flush over full
  house, A6789 straight) is only in `ShortDeckHooks.score_hand`, so tables for short deck are slightly wrong at
  the top until the sim and hero use the hook.
- **Flop textures: 160 buckets keyed `pair-suits-connect-high`**, computed exactly over all 1755 suit-isomorphic
  flops. The HS deciles are nearly uniform by construction (HS is a rank statistic); the per-category share
  and mean HS are the usable prior. Kept the deciles because the brief asked for the distribution.
- **Fake kits share one mini dealer (`fakekits/_table.py`)** and differ only in interface. The point of the drill
  is the unknown interface, not three poker engines. The dealer restarts the table when it ends so a runner
  always plays the requested number of hands.
- **Kit C enforces a pooled game clock (MIT style), kits A and B a per-call 1 ms.** Pipe round trips here are
  73 us median but spike to several ms under OS jitter, so a strict per-call millisecond over a pipe would
  fail a correct bot. A `T` handshake with a 10 s build timeout keeps imports and warm-up off the clock.
- **Pass criterion for a kit runner**: zero exceptions, zero illegal actions, timeouts within 1% of decisions
  (at least one allowed). One stray OS stall should not fail a drill; a slow bot still fails every time.
- **Reference submissions use hero when present, the cheap bot otherwise**; `HYPERION_DRILL_BOT=cheap` pins the
  cheap bot. Adapter tests set it so they measure translation, not hero's latency.
- **`hu_matrix.json` diagonal is set to 0.5 exactly and classes follow `all_hole_classes()` order**, matching
  what `strategy/tables.py` asserts. 1000 samples per cell (SE 1.6%), 160 KB.
- **Default samples raised from 10000 to 20000** after measuring 35 s for the whole default run on 7 workers;
  90 s buys half the standard error and still leaves three minutes of the five-minute budget on a 4-core laptop.

## Strategy layer (hyperion/strategy/, 2026-10-31)

- **Hero is always behind SafeBot.** `Hero()` builds `HeroCore` and wraps it in `SafeBot` itself, so the
  bestiary's `strategy.hero.Hero()` and `make_bot()` both get the guard. Telemetry: `hero.safe.stats()`.
- **Panic needs a rate, not a count.** A preempted process overruns 0.5 ms no matter how cheap its code
  is. SafeBot enters panic after `panic_after=5` overruns *and* an overrun share above `panic_rate=2%`.
- **Exact ICM is off the decision path.** `core.icm.icm_equity` costs ~470 us with eight live seats.
  Hero computes a value curve V(my stack) at 7 multiples of my stack (0, 0.5 .. 3x) in `hand_end` /
  `new_table`, chips moving to or from the field pro rata, V(0) = the payout for busting now; the
  decision path interpolates. Each ICM call goes through `icm_value`, which rounds live stacks to
  1/40 of the chips in play and memoises (`lru_cache`), so the curve costs microseconds after the
  first tables. If `core.icm` fails to import, V is chip-proportional, i.e. chip EV.
- **ICM gates every all-in call, deep or short.** The push/fold engine and the deep-stack preflop
  module both require ICM-weighted EV > fold for shoves and shove calls (equity vs random minus a
  0.10 range premium). In the harness (150 tables, seed 7, bestiary mix) this moved the hero from
  5.86 to 6.48 points per table (nit 6.34), mostly by cutting 5th-6th finishes from 31% to 14%;
  `use_icm=False` gives 5.84, so the gain is the gate. The sweep of other levers (threshold 8/15 bb,
  c = 0.5, tighter opens, no bluffs, no profiler) stayed within +-0.3, the 95% interval.
- **Push/fold tables.** `tables/pushfold_hu.json` = heads-up push/call sets for 1..25 bb from damped
  best-response iteration (40 rounds, damping 0.5) on `hu_matrix.json` with card-removal weights.
  Edges match HoldemResources (K2o pushes to ~10 bb, 72o not past 2 bb, any-two calls at 2 bb).
  Multiway: push the top `p_push_HU(S) / (1 + 0.3 (k-1))` of hands ordered by (deepest HU push
  depth, HU equity); k = live, non-dead opponents who can call. c = 0.3 puts the 10 bb button near
  39% and UTG eight-handed near 18%. Calls use the same shape with the call order.
  `tools/gen_tables.py` does not yet write this file; call
  `hyperion.strategy.pushfold.build_pushfold_tables(tables)` after regenerating the matrix, or the
  hero solves it at load (~4 s) and writes it if the directory is writable.
- **Position = players still to act.** Preflop ranges are keyed by `behind` (7 = UTG eight-handed,
  2 = button, 1 = SB, 0 = BB), which stays meaningful as seats bust. All open/3-bet/call fractions
  are in `PreflopParams`; "top X" means `preflop_rank >= 1 - X` (combo-weighted midpoint percentile,
  same definition as `hyperion.tablegen`). Flat-calling an open counts the raiser plus one extra
  opponent only when three or more players are still behind.
- **Profiler streets.** `Observation.history` has no street markers, so the profiler replays it with
  a betting-round tracker (round closes when nobody owes an action; a seat acting while owing none
  means a new street). It resyncs money and membership from each Observation and rebuilds the
  owes-set only when the street slipped. Dead seat = faced >= 5 bets with zero voluntary chips;
  station = fold-to-bet < 0.2 after 10; maniac = raise share > 0.5 after 10 actions; nit = VPIP
  < 0.12 after 20 hands. Dials blend toward neutral with weight n/(n+8) actions.
- **Postflop strength is a tier, not a table.** Made-hand category relative to the board (board
  pairs/trips do not count for us), top pair / overpair by rank arithmetic, draws by a precomputed
  13-bit straight-completer table and suit counts, scary-board demotions. `core.eval.warm(7)` runs
  at import: the lazy 6/7-card tables cost ~100 ms each on first use and showed up as overruns.
  `gc.freeze()` runs after import and in `new_table` so the big tables are never traversed by a
  collection during a decision.
- **Latency, and how to read it on this box.** 2,000 random self-consistent observations: mean 13-25
  us, p99 ~20 us as the per-observation minimum of three passes (single pass p99 40-130 us). In
  the engine: p50 11-14 us, p99 60-200 us, with a handful of 1-10 ms calls per 100 tables. Those
  are not the bot: a 6 us arithmetic loop measured with `thread_time` shows 2-4 ms spikes 45-90
  times a second here (WSL2: a vCPU descheduled by the host still accrues guest CPU time), no GC
  collection overlaps them, and they land in a different trivial stage each time. Treat `tmo` for
  any bot on this machine as environment noise; judge the hero by p50/p99 and by a quiet machine.
- **Left out.** Hole-card counts other than 2 fall through (preflop check/fold, postflop still uses
  the evaluator for 3 hole cards; 4+ hole cards exceed its 8-card limit and SafeBot folds). No
  bounty/auction hooks. The profiler models frequencies, not ranges. Parameters are untuned beyond
  the one sweep above; `Config` is the place to tune.

## Realistic fields baseline (2026-10-31)

Three named fields in `hyperion/sim/bestiary.py` (`python -m hyperion.sim --field NAME`), each run for
1000 strict tables: `--tables 125 --seed 7 --rotate`. The three runs went in parallel on the WSL2 box,
so `tmo` for the fast bots (Hero 80-380, tag 30-80) is the host's scheduling noise described above, not
the bots; the slow bots' `tmo` is real (MonteCarloBot's 200 rollouts cost 1-3 ms, the modeled
timeouts sleep 2 ms). Hero's `1st_us` of ~4 ms is its per-table ICM curve and warm-up, as before. Hero
entered panic mode on 2 of 1000 tables in realistic and chaos, none in strong.

**realistic** = hero, montecarlo30, montecarlo, pushfold, loose_aggro, naive, tag, timeout_then_recover

```
bot                      n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
tag                    125  5.768 0.108    14   30   19   14    9    5    5    3   62.0    81     0     0      3     16  13390    4019
pushfold               125  5.548 0.121    19   21   20   13   10    7    6    5   65.3   129     0     0      4     22  22785    4032
hero                   125  5.299 0.127    22   14   12   14   14   11    7    5   66.0   378     0     0     17     83  14335    4051
loose_aggro            125  5.218 0.148    31   11   10    9   10   10   10    9   60.5    70     0     0      2     11  26179    4045
montecarlo             125  3.828 0.085     1    4   11   20   22   19   12   11   97.9 36463     0     0      3   5709  37715      47
montecarlo30           125  3.690 0.115     6    6    9   11   15   20   18   15   91.5 13756     0     0      3   6440  43462    4020
timeout_then_recover   125  3.326 0.104     1    8   13   10    8   14   20   26   91.7 28249     0     0      3   5816  29028    4345
naive                  125  3.323 0.128     7    6    6    9   12   13   21   27   90.5    36     0     0      2      7   8019     192
1000 tables, 184426 hands in 286.1s: 645 hands/s. p1..pN are finish-position percentages; 1st_us is the slowest first call of a table.
```

**strong** = hero, pushfold, pushfold, tag, hero_tight, hero_loose, nit, loose_aggro (pushfold holds two
seats, so one line with twice the seats; the field averages 36/8 = 4.5 points per name-seat)

```
bot             n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
tag           125  4.887 0.109     7   20   18   15   13   12    7    8   73.5    31     0     0      4     17  11208      43
hero          125  4.708 0.129    24   11    8    8   10   14   14   12   65.8   104     0     0     15     60  11421    4874
hero_loose    125  4.505 0.155    20   10    9    8   12   12   17   12   71.2    82     0     0     15     60  10226     211
hero_tight    125  4.424 0.150    14   12   10   10   10   16   17   10   73.6    90     0     0     15     58  23810     328
nit           125  4.421 0.087     0    7   20   26   20   11    7    8   91.2    11     0     0      1      6   4667    2434
pushfold      125  4.416 0.083     8   15   14   14   13   11   12   14   76.9    57     0     0      4     22  15639     287
loose_aggro   125  4.223 0.141    19   10    8    6    9   12   14   21   69.5    23     0     0      3     14   4567     134
1000 tables, 191940 hands in 301.2s: 637 hands/s. p1..pN are finish-position percentages; 1st_us is the slowest first call of a table.
```

**chaos** = hero, crasher, random, allin, station, montecarlo, maniac, timeout_then_recover

```
bot                      n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us  maxus  1st_us
hero                   125  6.778 0.084    53    9   12   16    8    1    0    0   41.6   387     0     0     16     74  17642    4748
crasher                125  6.272 0.045     0   39   48   12    0    0    0    0   93.7    22 137239     0      0      4   8017     114
montecarlo             125  5.319 0.120    17   20   11   19   14    9    6    5   73.4 57095     0     0      6   5819  29277      73
timeout_then_recover   125  5.176 0.111     8   25   11   17   20   10    4    4   78.7 44755     0     0      4   7287  28684    4761
random                 125  3.588 0.100     3    2    5   13   25   30   11   10   96.6     3     0     0      1      4   8014      66
allin                  125  3.132 0.151    10    1    4    7   11   17   23   28   89.8     2     0     0      0      2   4016      27
maniac                 125  2.940 0.123     7    0    6    6    8   17   29   26   92.8     2     0     0      1      3   4014    5150
station                125  2.794 0.117     1    4    3    9   13   16   28   27   98.3     6     0     0      0      1  10357    4014
1000 tables, 149995 hands in 268.2s: 559 hands/s. p1..pN are finish-position percentages; 1st_us is the slowest first call of a table.
```

**Where Hero stands.** Hero wins the most tables in every field (22% / 24% / 53% first places) but it is
only first on points in chaos (6.78 ± 0.08, where surviving the self-destructors is the whole game and
even the crasher finishes 2nd-3rd by folding). In realistic it is third, 5.30 ± 0.13 behind `tag`
(5.77) and `pushfold` (5.55), and in strong second, 4.71 ± 0.13 behind `tag` (4.89), with CIs that
barely overlap. The gap is the tail, not the top: Hero finishes 5th-8th 37% of the time in realistic
against tag's 22%, and busts 66% vs 62%. The bust tracer on the realistic field (240 seats) says 37% of
Hero's busts are push/fold shoves at or below 12 bb that get called and lose, 18% are river calls, and
the opponent most often on the other side is `loose_aggro` (alone in the pot for 18% of busts, present in
29%), which calls short shoves and 3-bets wide enough that Hero's shoving range, tuned against folders,
pays it off; `montecarlo30` is second (11%). So the archetype that hurts Hero most is the loose-aggressive
student, and the lever is the shove range vs opponents whose observed call rate is high, not postflop.
The two presets bracket the default (hero_loose 4.51, hero_tight 4.42, both below 4.71), so neither
direction of the preflop dials alone closes the gap to `tag`. Note what `tag` and `pushfold` have in
common: they never shove light and they fold the river; that is the baseline Hero must beat before any
exploit matters.
