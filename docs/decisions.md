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

## Variant catalog (2026-10-31, builder: sim/drills)

- **The engine plays the drills' hooks contract directly.** `play_table(..., variant=hooks)` accepts a
  `hyperion.drills.variants.VariantHooks` object and wraps it in `engine.HooksVariant`: `on_deal` and
  `on_street` get the per-seat holes (empty for seats out of the hand) and a `spare` list of the hand's
  undealt cards they may pop from; a changed board is written back into the runout so later streets keep
  it; `score_hand` (or `score_splits`) judges the showdown; `on_payout` adjusts chip deltas; `on_bust`
  adds points; `extras(hand)` fills `Observation.extras` per street; `charges` moves chips into the pot.
  With `variant=None` every hook is a no-op and the hand loop is unchanged (same results, same speed).
  Rejected: a second engine or a per-variant subclass of `Table`; the contract already named the four
  points where a twist can act, and one bridge keeps the drills' presets and the sim's measurement on the
  same objects.
- **A bot answers variant decisions through `variant_decide(prompt) -> object`.** The engine looks for it
  on the bot, then `bot.impl`, then `bot.impl.core`, then `bot.inner`, so the bestiary's `Hero` wrapper
  and SafeBot do not have to forward it. The call is enforced like `act` (exceptions counted, strict-mode
  budget), and `None` or an error means the hook's default decision. Prompts are plain dicts
  (`{"decision": "discard" | "swap" | "buy_card", "hole", "board", "seat", "hand_no", "stacks", ...}`).
  Hero has no `variant_decide` yet; it gets the defaults everywhere (toss the lowest unpaired card, swap a
  low unpaired card, buy the bonus card).
- **Rules grew betting fields with standard-game defaults**: `ante` (chips) with `ante_from_level` and an
  optional `ante_per_level` schedule (the drill-2 turbo's 4/8/16/32 is now representable, closing that
  report's repo finding 2), `betting` in nolimit / potlimit / fixedlimit, `straddle` (big blinds), and
  `must_use_hole` for Omaha-style showdowns (the engine evaluates exactly k hole + 5-k board; `tablegen`
  honours it too). Antes go straight into `Observation.pot`, never into bets, and a short stack is all-in
  for what it has. Pot-limit cap = current bet + pot after the call (the same formula as
  `pot_limit_max_raise`); fixed-limit cap = current bet + 1 bb (preflop, flop) or 2 bb (turn, river) with
  no raise cap; a straddle is a live blind raise with min re-raise twice the straddle, heads-up none.
  Everything is gated on the field so the default path pays nothing. `Rules.extras["removed_ranks"]` now
  also shrinks the engine's deck (short deck played with 36 cards before only in the generator).
- **Split pots are columns.** `score_splits` returns one score per pot share (two boards: one per board;
  hi/lo: high and a qualifying low or `None`); each side pot is split evenly over the columns, the
  remainder and any column nobody qualifies for go to column 0, and odd chips inside a column go clockwise
  from the button as before.
- **Bounties: chips from the house by default, points from the house for knockouts.** `BountyHooks`
  funds the bonus from the house unless `extras["bounty_funding"] == "losers"` (then it is taken pro
  rata from the hand's losers and chips are conserved); chips in play grow under house funding, which ICM
  at the cap tolerates. `KnockoutHooks.on_bust` adds points, not chips, to the hand's biggest winner, so a
  table's points no longer sum to the payouts there. Bounty ranks are public in `obs.extras["bounties"]`
  (MIT kept them private; a private per-seat extras channel is not built).
- **Catalog of 23, four axes, every hooks entry implemented.** `hyperion.drills.variants.catalog()`;
  `names()` stays the seven drill presets so `hyperion.drills.run --variant random` is unchanged. Each
  entry carries the axis, a summary in the organizers' voice, Rules, hooks (fresh per table via
  `new_hooks()`, since hooks keep per-hand state), what breaks, a checklist, a `tables` status for
  `tools/gen_catalog.py` and a `config_patch` sketch. `--list`, `--show NAME` and `--rules NAME --out
  rules_NAME.json` write the Rules JSON that `tools/gen_tables.py --rules` and `python -m hyperion.sim
  --rules` accept; `python -m hyperion.sim --variant NAME` plays an entry's Rules and hooks. Two entries
  are honest simplifications: `bonus_card` posts a fixed price instead of MIT 2023's auction, and the
  three-card discards are dead, not community (toss_or_holdem's docstring explains why). Not built:
  boards above eight cards, a real auction, private extras.
- **`tools/gen_catalog.py` writes `tables/variants/NAME/` only where card rules differ** (hole/board
  counts, rank order, removed ranks, must-use) and records every entry in `tables/variants/manifest.json`
  as generate / default / unsupported with the reason. Reduced samples (2 cards 4000, 3 cards 1500,
  4 cards 300) keep the whole run to a few minutes on 7 workers; the 169x169 matrix is a 2-card object,
  so 3- and 4-card entries get `hole_classes.json` instead. lowball, wild_deuces and hi_lo get no tables:
  the generator has no score hook, and the high-hand tables would be wrong in the exact direction that
  matters. Hero still loads `tables/` only; pointing it at a variant directory is a strategy knob
  (`tables_dir`) that does not exist yet, so the baseline below measures Hero with default tables on
  every entry, which is the honest event-night picture unless that knob is added.

## Variant catalog baseline (2026-10-31)

Hero against `--field realistic` for 300 tables on every catalog entry: `python -m hyperion.sim --variant
NAME --field realistic --tables 300 --seed 7` (strict mode, three runs at a time on the WSL2 box, so `tmo`
is the usual scheduling noise). Hero plays with the default tables and no `variant_decide` on every entry;
rank is Hero's place among the 8 bot names by points. Reference: the default game on this field is Hero
5.30 ± 0.13, third behind tag 5.77 and pushfold 5.55 (1000 tables, above).

| variant | axis | hero pts (±95%) | rank / 8 | bust% | exc | ill | tmo | p99 us | leader (if not hero) |
|---|---|---|---|---|---|---|---|---|---|
| permuted_ranks | ranking | 6.33 ± 0.24 | 1 | 39.7 | 0 | 0 | 12 | 63 | next tag 5.22 |
| short_deck | ranking | 5.25 ± 0.24 | 3 | 77.3 | 0 | 0 | 9 | 54 | tag 5.79 |
| lowball | ranking | 4.99 ± 0.25 | 1 | 72.7 | 0 | 0 | 13 | 57 | next pushfold 4.76 |
| wild_deuces | ranking | 5.19 ± 0.25 | 4 | 68.3 | 0 | 0 | 6 | 61 | tag 5.64 |
| flush_over_full_house | ranking | 5.31 ± 0.24 | 2 | 66.7 | 0 | 0 | 30 | 64 | tag 5.74 |
| toss_or_holdem | information | 6.49 ± 0.08 | 1 | 94.0 | 0 | 0 | 17 | 49 | next tag 5.75 |
| three_card_blind_discard | information | 6.49 ± 0.08 | 1 | 94.0 | 0 | 0 | 15 | 47 | next tag 5.78 |
| three_card_keep | information | 6.60 ± 0.06 | 1 | 95.7 | 0 | 0 | 13 | 43 | next tag 5.35 |
| omaha_four | information | 6.96 ± 0.02 | 1 | 92.7 | 0 | 0 | 9 | 44 | next tag 5.19 |
| swap_holdem | information | 5.33 ± 0.24 | 3 | 67.3 | 0 | 0 | 17 | 66 | tag 5.61 |
| swap_one_turn | information | 5.30 ± 0.24 | 4 | 67.0 | 0 | 0 | 9 | 64 | tag 5.62 |
| exposed_card | information | 5.37 ± 0.24 | 2 | 62.7 | 0 | 0 | 14 | 61 | tag 5.67 |
| two_boards | information | 5.43 ± 0.24 | 2 | 58.0 | 0 | 0 | 30 | 90 | tag 5.84 |
| bonus_card | information | 5.78 ± 0.16 | 1 | 81.7 | 0 | 0 | 58 | 81 | next tag 5.35 |
| bounty | payoff | 5.30 ± 0.24 | 4 | 60.7 | 0 | 0 | 50 | 94 | tag 5.54 |
| knockout_bounty | payoff | 6.34 ± 0.36 | 2 | 68.3 | 0 | 0 | 9 | 61 | loose_aggro 6.69 |
| top_heavy | payoff | 17.36 ± 2.00 | 4 | 68.0 | 0 | 0 | 10 | 61 | loose_aggro 20.74 |
| hi_lo | payoff | 5.32 ± 0.24 | 2 | 66.0 | 0 | 0 | 19 | 67 | tag 5.72 |
| pot_limit | betting | 5.21 ± 0.24 | 4 | 67.3 | 0 | 0 | 19 | 65 | tag 5.66 |
| antes_from_level_3 | betting | 5.20 ± 0.24 | 4 | 70.7 | 0 | 0 | 11 | 56 | tag 5.68 |
| fixed_raise | betting | 5.72 ± 0.23 | 1 | 57.7 | 0 | 0 | 11 | 55 | next tag 5.52 |
| fast_schedule | betting | 5.18 ± 0.25 | 4 | 70.0 | 0 | 0 | 7 | 54 | tag 5.60 |
| straddle | betting | 5.32 ± 0.28 | 2 | 62.0 | 0 | 0 | 13 | 67 | tag 5.36 |

**Reading it.** Hero throws no exceptions and makes no illegal action on any entry (SafeBot clamps the
one legal size under fixed_raise; so do the bestiary's helpers), and it never ranks last. The table is
still mostly bad news for the strategy owner, in three groups:

1. **Entries Hero does not play at all (first place is an artifact).** toss_or_holdem,
   three_card_blind_discard, three_card_keep and omaha_four: Hero has no preflop path for three or four
   hole cards, so it check/folds every hand (0% first places, 62-95% second). It "wins" because the
   bestiary's two-card helpers overvalue eight- and nine-card hands and the other seven bust each other
   first; against any field that can fold, a bot that never plays a hand finishes 7th. Cause: `HeroCore.act`
   falls through to check/fold when `len(hole) != 2` (preflop) and to `safe_action` postflop. Fix: preflop
   by `tablegen.hole_label` + `tables/variants/NAME/preflop_rank.json`, a `variant_decide('discard')`, and
   a two-of-four path for Omaha (`engine.evaluate_must_use`).
2. **Entries Hero plays blind to the twist (within noise of the default game).** lowball 4.99 (first, but
   only because every bot values the wrong hands; absolute points are Hero's lowest), wild_deuces 5.19
   (4th), bounty 5.30 (4th), hi_lo 5.32, exposed_card 5.37, two_boards 5.43, swap_one_turn 5.30: Hero reads
   none of `obs.extras` (bounties, boards, exposed, discards, swapped) and uses the hold'em evaluator for
   showdown value. Cause: no hook from Rules.extras or Observation.extras into the strategy; the
   `config_patch` on each entry is the first lever, a `score_hand`-aware HS estimate the second.
3. **Betting-structure entries where the gap to tag is the usual one.** pot_limit 5.21, antes_from_level_3
   5.20, fast_schedule 5.18 (all 4th, tag 5.6-5.7): the same tail problem as the default baseline, now with
   a sim that actually posts antes and caps raises. The ante entry is the one drill 2 could not price; the
   `pushfold.threshold_bb` +2 patch can now be measured honestly. knockout_bounty and top_heavy reward
   the loose-aggressive student most (20.74 vs Hero 17.36 on top_heavy; drill 2 had Hero first against a
   tag+nit field, so the ordering is field-dependent), and permuted_ranks is Hero's best result (6.33,
   first, 40% bust) because Hero remaps through `rank_order` and the bestiary evaluates displayed cards.
   fixed_raise and bonus_card put Hero first; bonus_card because the default (buy) gives the other bots a
   third card they misplay more than Hero's safe action misplays it.

Broken-entry list for the strategy owner, one line each: toss_or_holdem / three_card_blind_discard /
three_card_keep (no 3-card preflop path, folds every hand); omaha_four (no 4-card path, folds every hand);
lowball (evaluator sign is wrong for the variant: values the hands it should fold); wild_deuces (deuces
ranked as the worst cards); hi_lo (plays high only, loses the low half); bounty / knockout_bounty / two_boards
/ exposed_card / swap_one_turn (ignores `obs.extras`); bonus_card (buys the card by default, then takes the
safe action with three hole cards); pot_limit / antes_from_level_3 / fast_schedule / straddle (no structural
break, the default-game gap to tag; `stack_bb` ignores antes and the straddle). None throws.

## HRC cross-check (2026-10-31, builder: tools/hrc_check.py)

`tools/hrc_check.py` downloads HoldemResources' free heads-up Nash push/fold zip
(`holdemresources_hu_equilibrium.zip`, 86,510 B, two CSVs of 3,981 stack rows x 169 classes, push and
call **frequencies** at 0.01 resolution) to `~/.cache/hyperion/hrc` (never into the repo: the files carry
no license) and compares it with `tables/pushfold_hu.json` (matrix `09e796abef5676e2`, read through
`load_pushfold`) at depths 2..25 bb. HRC's `stack` is the whole effective stack, blind included, the same
convention as our S (the exact agreement at 4 and 16 bb rules out an off-by-half-blind reading). A class
"disagrees" when we push (call) and HRC's frequency is below 0.5, or the reverse; MAD is the mean
absolute difference between our 0/1 and their frequency over the 169 classes; freq is combo-weighted.

| depth | push: disagree (we push / they fold, they push / we fold) | MAD | freq ours / HRC | worst (ours/HRC) |
|---|---|---|---|---|
| 2 | 1 (1 / 0) | 0.006 | 0.903 / 0.894 | 83o(1/0.00) |
| 3 | 0 (0 / 0) | 0.002 | 0.777 / 0.780 | T2o(0/0.35) 85o(1/0.96) |
| 4 | 0 (0 / 0) | 0.000 | 0.738 / 0.738 |  |
| 5 | 3 (2 / 1) | 0.017 | 0.716 / 0.715 | 93s(1/0.00) J3o(0/1.00) 96o(1/0.16) |
| 6 | 4 (4 / 0) | 0.023 | 0.701 / 0.683 | 93s(1/0.00) 94s(1/0.00) 96o(1/0.00) 63s(1/0.06) |
| 7 | 2 (1 / 1) | 0.010 | 0.659 / 0.663 | 94s(1/0.00) 86o(0/0.77) |
| 8 | 6 (6 / 0) | 0.034 | 0.641 / 0.619 | 43s(1/0.00) 63s(1/0.00) 84s(1/0.00) 94s(1/0.00) T3s(1/0.00) Q4o(1/0.19) |
| 9 | 4 (2 / 2) | 0.024 | 0.593 / 0.599 | 97o(0/1.00) J2s(1/0.00) Q5o(1/0.00) T7o(0/1.00) |
| 10 | 4 (4 / 0) | 0.025 | 0.608 / 0.583 | 94s(1/0.00) J2s(1/0.00) Q6o(1/0.00) T7o(1/0.00) 43s(1/0.72) |
| 11 | 2 (1 / 1) | 0.012 | 0.551 / 0.545 | T5s(0/1.00) 76o(1/0.05) |
| 12 | 5 (0 / 5) | 0.030 | 0.505 / 0.532 | 53s(0/1.00) 74s(0/1.00) 87o(0/1.00) J4s(0/1.00) J8o(0/1.00) |
| 13 | 5 (1 / 4) | 0.028 | 0.496 / 0.515 | 74s(0/1.00) J4s(0/1.00) K4o(0/1.00) Q2s(1/0.00) J8o(0/0.79) |
| 14 | 1 (0 / 1) | 0.008 | 0.472 / 0.484 | K5o(0/1.00) J8o(0/0.27) |
| 15 | 3 (0 / 3) | 0.017 | 0.436 / 0.457 | K6o(0/1.00) T8o(0/1.00) Q4s(0/0.85) |
| 16 | 0 (0 / 0) | 0.000 | 0.448 / 0.448 | K7o(1/0.96) Q4s(1/0.98) |
| 17 | 2 (0 / 2) | 0.009 | 0.415 / 0.429 | K8o(0/1.00) T8o(0/0.60) |
| 18 | 2 (0 / 2) | 0.011 | 0.412 / 0.423 | K8o(0/1.00) J6s(0/0.88) |
| 19 | 1 (0 / 1) | 0.006 | 0.406 / 0.409 | Q5s(0/1.00) |
| 20 | 1 (0 / 1) | 0.004 | 0.400 / 0.402 | Q5s(0/0.76) |
| 21 | 4 (2 / 2) | 0.024 | 0.394 / 0.382 | 98o(1/0.00) Q5s(0/1.00) Q6s(0/1.00) Q9o(1/0.00) |
| 22 | 5 (5 / 0) | 0.028 | 0.409 / 0.382 | 98o(1/0.00) J6s(1/0.00) Q4s(1/0.00) Q9o(1/0.00) T6s(1/0.24) |
| 23 | 11 (0 / 11) | 0.061 | 0.333 / 0.380 | 75s(0/1.00) 96s(0/1.00) J9o(0/1.00) K4s(0/1.00) Q5s(0/1.00) Q6s(0/1.00) Q7s(0/1.00) T9o(0/1.00) T6s(0/0.98) 54s(0/0.71) |
| 24 | 6 (0 / 6) | 0.036 | 0.357 / 0.380 | Q5s(0/1.00) Q6s(0/1.00) Q7s(0/1.00) T6s(0/1.00) T9o(0/1.00) Q9o(0/0.62) K9o(1/0.55) |
| 25 | 1 (1 / 0) | 0.006 | 0.373 / 0.363 | Q9o(1/0.00) |

| depth | call: disagree (we call / they fold, they call / we fold) | MAD | freq ours / HRC | worst (ours/HRC) |
|---|---|---|---|---|
| 2 | 0 (0 / 0) | 0.000 | 1.000 / 1.000 |  |
| 3 | 1 (1 / 0) | 0.003 | 0.928 / 0.923 | 63o(1/0.46) |
| 4 | 0 (0 / 0) | 0.000 | 0.741 / 0.741 |  |
| 5 | 1 (0 / 1) | 0.004 | 0.614 / 0.621 | 97o(0/0.75) |
| 6 | 1 (0 / 1) | 0.006 | 0.535 / 0.544 | 98o(0/1.00) |
| 7 | 1 (0 / 1) | 0.004 | 0.484 / 0.486 | 97s(0/0.65) |
| 8 | 2 (0 / 2) | 0.009 | 0.436 / 0.450 | K2o(0/1.00) Q7o(0/0.53) |
| 9 | 0 (0 / 0) | 0.000 | 0.406 / 0.406 |  |
| 10 | 1 (0 / 1) | 0.008 | 0.363 / 0.374 | K5o(0/1.00) Q6s(0/0.40) |
| 11 | 1 (1 / 0) | 0.009 | 0.357 / 0.350 | K2s(1/0.00) K6o(1/0.56) |
| 12 | 1 (1 / 0) | 0.006 | 0.339 / 0.330 | Q9o(1/0.00) |
| 13 | 2 (1 / 1) | 0.012 | 0.315 / 0.310 | Q8s(0/1.00) JTo(1/0.04) |
| 14 | 1 (1 / 0) | 0.007 | 0.294 / 0.293 | J9s(1/0.00) K8o(0/0.21) |
| 15 | 0 (0 / 0) | 0.002 | 0.288 / 0.285 | QTo(1/0.71) |
| 16 | 0 (0 / 0) | 0.002 | 0.262 / 0.265 | A2o(0/0.26) |
| 17 | 0 (0 / 0) | 0.001 | 0.250 / 0.248 | K9o(1/0.77) |
| 18 | 0 (0 / 0) | 0.001 | 0.238 / 0.238 | JTs(1/0.79) |
| 19 | 0 (0 / 0) | 0.000 | 0.226 / 0.226 |  |
| 20 | 0 (0 / 0) | 0.000 | 0.217 / 0.217 |  |
| 21 | 0 (0 / 0) | 0.000 | 0.208 / 0.208 |  |
| 22 | 2 (0 / 2) | 0.012 | 0.193 / 0.199 | K9s(0/1.00) QTs(0/0.97) |
| 23 | 1 (1 / 0) | 0.009 | 0.195 / 0.187 | K9s(1/0.00) KTo(1/0.59) QTs(1/0.86) |
| 24 | 2 (2 / 0) | 0.010 | 0.183 / 0.179 | K9s(1/0.10) QTs(1/0.26) KTo(0/0.13) |
| 25 | 0 (0 / 0) | 0.000 | 0.173 / 0.173 |  |

Totals over 24 depths: push 73 disagreements (3.0 per depth, mean MAD 0.018), call 17 (0.7 per depth,
mean MAD 0.004). Only depth 23 crosses the ~8-classes-per-depth bar (11). Not fixed here: `pushfold.py`
has an owner. The pattern, for them:

1. **21 to 25 bb: an unconverged oscillation, not a bias.** HRC's push frequency is smooth there (0.382,
   0.382, 0.380, 0.380, 0.363); ours zig-zags around it (0.394, 0.409, 0.333, 0.357, 0.373). At 22 bb all
   five disagreements are hands we push and HRC folds (98o, J6s, Q4s, Q9o, T6s); at 23 bb all eleven are
   hands we fold and HRC pushes (75s, 96s, J9o, K4s, Q5s-Q7s, T9o, T6s, 54s), i.e. the damped best-response
   loop (40 iterations, damping 0.5) ends on alternate sides of the boundary from one depth to the next.
   Reading: more iterations or a convergence check per depth (best-response gain), and warm-starting each
   depth from the previous one, should remove it. The call side at the same depths is within 2 classes.
2. **5 to 10 bb: we push low suited junk that HRC never pushes.** 93s, 94s, 63s, 43s, 84s, T3s, J2s all
   appear as "we push / HRC 0.00" (6 of 6 at 8 bb, 4 of 4 at 6 and 10 bb), and our frequency is 1 to 2.5
   points above HRC's at 6, 8 and 10 bb. That is the equity matrix (1,000 Monte Carlo deals per class pair,
   `tables/meta.json`), which can flatter suited low cards by a point or two; a matrix with more samples per
   pair is the test, not the solver.
3. **12 to 20 bb: slightly tight, all in one direction.** 24 of the 25 disagreements are hands HRC pushes
   and we fold (74s, J4s, 53s, 87o, J8o, K4o-K8o, T8o, Q5s), and our frequency sits 1 to 3 points under
   HRC's. Small and consistent; likely the same two causes meeting in the middle.
4. **Calls agree.** Never more than 2 classes per depth; the flips are boundary hands (K2o at 8, K5o at
   10, K9s/QTs at 22 to 24) and HRC's own mixed cells.

Test: `tests/test_hrc_crosscheck.py` exercises the parser and the comparison on a synthetic CSV in the
HRC layout (`tests/fixtures/hrc_hu_small.csv`, invented values, real header order). If the download
fails, `--zip` accepts a local copy.

## Kit D: the MIT Pokerbots shape at 8 seats (2026-10-31)

`hyperion/drills/fakekits/kit_d/` imitates the engine-2026 python skeleton from the documented interface
(research note section 3a), not from its code: `Bot` with `handle_new_round` / `get_action` /
`handle_round_over(game_state, round_state, active)`, namedtuple `GameState`, `RoundState`,
`TerminalState`, action namedtuples, `legal_actions()` as a set of classes with no `FoldAction` when a
check is free, `raise_bounds()` as raise-to totals, a TCP socket (`python player.py <port>`), a single
game clock charged on every round trip, and the letter protocol (T P H G F/C/K/R B O A Q) with three
additions the SNG table needs: `S` stacks and `I` pips at round start (stacks carry over), `L` blinds, and
8-wide `A` deltas. The skeleton replays every action, ours included, exactly as MIT does; a test runs the
replay against the dealer for 180 hands with a random legal bot and asserts pips, stacks, actor, legal set,
raise bounds and derived pot agree at every decision. The reference `KitDAdapter` pulls the action classes
out of the legal set, so `adapter.py` still imports no kit. The rubric lists the traps; the one that bit
during the build is the pooled clock meeting a lazy 8-card evaluator table (1.4 s on first use): with
three hole cards a submission must warm it before `run_bot`.

`hyperion/drills/run.py` does not list kit D: adding it is two edits (`KITS` and a branch in
`Drill.run_kit`), spelled out at the end of `kit_d/RUBRIC.md`; run.py is owned elsewhere this round.
