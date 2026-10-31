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
  evaluator stops at 8 cards. If the organizers use the discard-to-board rule, `board_sizes` becomes `(0, 2, 2+n, 3+n, 4+n)` and
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

## Kit D: the university-engine shape at 8 seats (2026-10-31)

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

## Public surface (2026-10-31)

The repo is private and stays private, but its public-facing surface now reads as a generic project: a
millisecond-budget poker engine, bot sandbox and strategy tables. Scrubbed in place: `README.md` (new intro,
no event framing or event links; layout, run commands and "what it does not do" kept), the `pyproject.toml`
description, `tables/README.md`, the design spec (event references became "the target format" with the
constraints stated plainly), and every docstring or comment under `core/`, `sim/`, `drills/`, `tools/` and
`tests/` that named the event, its hosts, its dates, or the competition the fake kits imitate.
`tools/export_public.py` builds the public tree: it copies the repo minus `.git`, `.venv`, `docs/research/`,
`docs/drills/`, `docs/packet/`, `docs/prompts/`, `PLAYBOOK.md`, `docs/night-of.md`, `drills/log/`, `NIGHT*.md`,
this log (a working journal with event references on two lines) and whatever `.publicignore` lists, drops
itself, its test and `.publicignore`, then checks every exported path and text file against the denylist and
exits non-zero listing `file:line` on any hit; `--init-git` makes a single squashed commit.
`tests/test_export_public.py` runs that export and fails on any hit, so the public surface cannot regress
unnoticed. Any public release must be a fresh-history export made by that tool: commit messages and the
excluded docs are event material and never ship. GitHub metadata checked: description generic, no homepage,
no topics.

## Night-of tooling: conformance, pack, latency, templates (2026-10-31)

Drills 1 and 2 and playbook review 1 kept finding the same three holes: an adapter bug the kit simulator
cannot see (both deliberately wrong adapters in `python -m hyperion.drills.conformance` PASS the kit B runner
with 0 illegal, because `Action.clamp` hides wrong raise bounds and a wrong pot is just a wrong number), a
packaging step done by hand under the clock, and a latency check read off a sim table that prints hands, not
decisions. Each is now one command, stdlib only:

- `hyperion/drills/conformance.py`: `check_observation(obs, rules)` returns named invariant violations;
  `checked(adapter)` wraps one instance's `to_observation` / `from_action` (adapter.py untouched) and keeps
  counts, five examples per rule, translation errors that `Adapter.decide` would otherwise swallow, and the
  action mix; `maybe_checked` turns it on under `HYPERION_CHECK=1` and prints at exit. Cross-call rules (chip
  total constant within a hand, button and seat constant) catch the pot-includes-bets bug; `raise_total`
  (min_raise must exceed the current bet) catches increments passed as totals. Reference kit B and C
  adapters: 0 violations.
- `tools/pack.py`: vendors `hyperion/` and `tables/` (default tables only; `--slim` drops fakekits and the
  bestiary), imports the entry from a fresh interpreter in another directory with `-I -B` and PYTHON* unset,
  checks that `hyperion` resolved from the package, times it (5 s), zips (no bytecode), prints sha256 and
  appends the Submissions row to `NIGHT.md`, minute computed from the template's `T0:` line.
- `tools/latency.py`: 2,000 random self-consistent Observations from `tests/strategy_helpers.random_obs`
  (seat fixed so an adapter round trip is consistent), each call timed alone into a preallocated list, GC
  collections and wall vs CPU reported, exit 1 above p99 500 µs. `--adapter module:Class --native kit_b`
  times `adapter.decide`; the fake kits' state builders are built in, the real kit needs a 10-line one.
  Hero alone: p99 65 µs; through `KitCAdapter`: p99 83 µs on this box.
- `hyperion/drills/adapter_template.py` (nine TODOs in the order the gotchas bit, each with the field it
  feeds and a one-line test), `docs/packet/NIGHT-template.md`, `docs/packet/EXAMPLE-rule-sheet.md` (drill 2's
  sheet, labelled as a rehearsal). Prompt 01 gained the FIT VERDICT block (KEEP / REGENERATE / DROP per
  prepared layer with a mechanical path rule) at the coordinator's request; it is the only prompt that grew.

Not done: the sim runner still prints `tmo` per hands, not decisions (prompt 04 says "per hands as printed");
`Config` still has no `profiler_dead_after`; the windows prompt (06) was not touched.

## Track B spec v2 and self-contained fake kits (2026-10-31)

Drill 3 ran the Track B spec from a blank directory (legal at minute 4, equity and ICM at 17, second to
Hero in the realistic field, fifth of eight in the strong one) and listed 32 defects; playbook review 1
added two (no rank remap; exact Malmuth-Harville on the decision path). The spec is now v2
(`docs/prompts/track-b-from-scratch.md`, under 1,600 words, tested) with these decisions:

- **ICM is a per-hand value curve, never an exact evaluation inside `act`.** Three Malmuth-Harville
  evaluations at 0.5x, 1x and 2x of our stack (opponents scaled pro rata) plus the two free endpoints,
  computed at `new_game` and in the untimed hand-end callback; decisions interpolate. Under kit A, whose
  `hand_over` carries only our chip change, the curve is built from our exact new stack and the
  opponents' last-seen chips scaled to the remaining total. Rejected: drill 3's own edit (fold value at the
  first decision, win and lose values at the all-in decision), because it keeps ~50 µs evaluations on the
  timed path and multiplies them in multiway spots; and the deep-stack linear stand-in, because the
  spec has no measured threshold for it.
- **The ICM gate applies to calls of an all-in and re-shoves only.** Open shoves get step 3b's push rule,
  which carries fold equity through the same curve; gating an open shove as if always called is the
  fold/fold failure drill 3 named.
- **Monte Carlo at 2,000 samples per class inside a 5 s import cap**, the count drill 3 validated (400
  put JJ above QQ and A3o in the top 12 percent); the sanity lines are in the spec.
- **The timing gate is a rate, not a max:** under 0.3 percent of 2,000 calls over 1 ms and p99 under
  500 µs, on three rotating states (mid-hand, first decision of a new hand, all-in call at 8 seats).
  Drill 3's edit of "p99 under 300 µs" was not taken: the loaded box's p99 for the final bot was 260
  to 493 µs and the rules' budget is 1 ms; 500 keeps the gate meaningful without failing on the box.
- **Profiler counts only what it saw:** the per-decision history diff and reported showdowns, one
  observation per seat per hand per counter with doubled floors when the kit gives nothing at hand end.
- **The fake kits import nothing from `hyperion`.** `hyperion/drills/fakekits/_eval.py` is a 50-line
  brute-force evaluator producing the same ordering tuple as `hyperion.core.eval._classify`, plus the
  deck and `card_str`; `_table.py` and kit D's runner use it. A kit now copies verbatim into a blank
  directory, which drill 3 could not do without handing the agent the real evaluator. Showdown results
  are identical (tested on 1,600 random pairs at 5 to 8 cards); the existing kit tests pass unchanged.
  Rejected: giving the kits their own copy of the prime-keyed evaluator (more code to drift, and a
  Track B agent would read it).

Not applied from drill 3's list, by ownership: the README timeline row (defect 32), prompt 01's "say
whether the kit's dealer implements each non-standard rule" (29; the spec's step 4 carries the
consequence instead), prompt 05's payoff wording (26; the spec's step 4 no longer points at 05). Stage 0's
"no Track B drill has run yet" line in the playbook is stale and outside this pass.

## Hero tuning pass (2026-10-31, builder: hero tuning)

Method: `tools/sweep.py` plays every setting on the same duplicate-dealt seed set (eight rotations per seed,
sample unit = one seed) across several fields in parallel and reports the paired delta against the base;
a lever was kept only when its delta was positive on every field in the stage. Six stages, 150-400 seeds
each; final confirmation at 1,000 seeds. Raw outputs lived under `scratch/` (gitignored).

**Before / after, 1,000 duplicate seeds, seed 7, strict.** "old defaults" = the same code with the previous
`Config` values, so the two middle columns separate the bug fixes from the tuning.

| field | hero before (old code) | hero, old defaults | hero after | tag after | hero - tag (paired) | hero bust% before -> after |
|---|---|---|---|---|---|---|
| realistic (`--field realistic`) | 5.30 (coordinator) | 5.296 ± 0.045 | **5.943 ± 0.043** | 5.574 ± 0.038 | +0.369 ± 0.061 | 66.8 -> 52.3 |
| strong (`--field strong`) | 4.71 (coordinator) | 4.564 ± 0.050 | **5.011 ± 0.048** | 4.658 ± 0.040 | +0.353 ± 0.068 | 68.7 -> 60.5 |
| mixed: hero,tag,nit,naive,station,maniac,random,allin | 6.420 ± 0.032 | 6.461 ± 0.031 | **6.825 ± 0.028** | 6.273 ± 0.027 | +0.551 ± 0.044 | 54.0 -> 46.3 |
| tag/nit: hero,tag,tag,nit,nit,naive,naive,tag | 5.312 ± 0.050 | - | **6.064 ± 0.048** | 5.136 ± 0.023 | +0.928 ± 0.059 | 52.9 -> 38.3 |
| weak: hero,station,station,random,maniac,allin,naive,random | 7.118 ± 0.021 | - | **7.373 ± 0.015** | (naive 5.891) | - | 52.6 -> 46.4 |

Hero is first on points in every field, the intervals against `tag` are disjoint everywhere, and
exceptions and illegal actions are zero on all 40,000 table-seats. Latency is unchanged: `act()` mean
14.1 us, p99 21.4 us (min-of-3), the 0.15 ms / 0.5 ms test passes. `hero_tight` and `hero_loose` inherit
every default they do not override, so they moved with the base and now also beat tag on the strong field.

**Where the busts came from (`--trace-busts hero`, new in the runner).** Before: 60% of hero's busts
happened with more than 50 bb at hand start, three to five players left, in the first 25 hands, and the
single biggest bucket (34%) was the deep-stack preflop module *calling a shove* with hands like ATo, A2o,
K6s against a bot that had just won a mountain of chips (allin, maniac, naive). Two causes:
(1) a bug: `IcmCurve.value` extrapolated linearly past its last sample (3x my stack), so when a covering
stack shoved, winning was valued at 8.34 points of a maximum 8 and anything passed the gate;
(2) a modelling gap: pure ICM says call A2o there (6.65 vs 6.16 for folding) because it does not know
the shover will offer the same spot next hand with a better hand for us. Postflop had no ICM gate at
all: another third of busts were top-pair calls and commitments on raw pot odds against bots that only
bet two pair or better. After the fixes the residual tail is the forced short-stack phase (16,000 chips
at 200/400 make everyone short; half of hero's remaining busts are push/fold shoves at <= 12 bb that get
called, loose_aggro first), and hero is above the table average through hand 100 in every field, so it
is not bleeding chips before that phase.

**Timeouts are hypervisor jitter, not hero's code.** Measured inside `act()` in the real engine with
`thread_time` and `perf_counter`, plus `gc.callbacks` and `sys.getallocatedblocks()`: per second spent
inside `act()`, hero and tag overrun at the same rate (114.5/s vs 115.8/s under load; a trivial 10 us
arithmetic loop in the same process spiked 98/s); every one of hero's 342 overruns replayed on the same
observation in 3-7 us, none over 1 ms; no GC collection started inside any overrun; hero nets 9
allocated blocks per call (tag 7), nothing accumulates. Hero shows ~3x tag's timeouts because it has
~3x the exposure: p50 15 us against 3 us and a few percent more calls. Lowering the per-call time
would lower the count proportionally, but p50 is already 15 us. Not fixed because nothing is broken;
recorded so nobody chases it again. Side effect worth knowing: under heavy load SafeBot's panic (5
overruns and >= 2% of calls) fires in ~1% of tables and plays the rest of that table in cheap mode.

**What changed in `Config` and why (all swept, numbers are paired deltas on mixed / strong / weak unless
stated).**
- `postflop.icm_gate_frac` 2.0 (off) -> 0.5, `icm_margin` 0.10: a call or value bet that risks half the
  stack must beat folding in ICM points. The biggest lever found: +0.14 / +0.15 / +0.07, busts 54 -> 50%.
- `preflop.open_frac` 0.40/0.42/0.28/... -> 0.60/0.60/0.42/0.30/0.24/0.20/0.17: tighter opens cost
  -0.17 against tags and nits, wider gained +0.16 and then +0.05 everywhere. The field folds too much.
- `postflop.call_margin` 0.05 -> 0.15: +0.07 against tags, neutral elsewhere; 0.20 starts costing the
  weak field.
- `preflop.patience_deep` 0.2 (new), scaled by the share of the stack at risk: the option value of
  waiting when deep. +0.09 / +0.01 / +0.13. The unscaled form folded AA to a 30%-of-stack shove at 100 bb;
  the scaled form is point-neutral and calls it.
- `preflop.three_bet_frac` 0.05 -> 0.03: +0.07 on the mixed field, neutral elsewhere; 0.08 was negative.
- `pushfold.threshold_bb` 12 -> 10: +0.06 / +0.14 / +0.01 on realistic / strong / mixed; 15 was -0.11.
- `preflop.reraise_margin` 0.15 (new): 4-bet and 5-bet shoves go through the ICM gate with the
  re-raiser's range discounted. Small but never negative; it stops QQ re-shoving into a nit's 4-bet.
- `icm_ratios` now dense around 1x (0.9, 1.0, 1.1, ...) and the ICM memo key keeps my exact chip share
  while rounding opponents: the old three-point curve had a kink at my stack that priced a +-7% flip at
  57% equity where exact ICM says 47%, biasing every gate against small risks. Point-neutral, correct.
  `ICM_BUCKETS` 40 -> 100: rounding seven opponents up by 12% had distorted V by 0.13 points.

**Tried and not kept.** Tightening the shoving range in any form (`push_equity_margin`, a larger
`multiway_equity_penalty`, `tighten_per_player` 0.45-0.8): negative on two or three fields each; the
shoves that bust are the price of the shoves that win. Conditioning the shove slice on the callers'
observed call-vs-shove rate (`loose_caller_tighten`, `loose_caller_equity_blend`, built as asked):
+0.010 +- 0.055 at 400 seeds on realistic, nothing elsewhere; left in at 0. A separate river threshold
(`river_call_margin`, `river_min_tier`): negative once the gate and `call_margin` were in. A patience
premium keyed to the shover's shove rate: nothing beyond `patience_deep`. Flipping the unknown-archetype
call-down slope (call down more against aggressive bettors): -0.54 on the tag field; in this room a
bettor's aggression stat signals strength. Disabling the profiler: -0.34 there. Hero with `value_tier`
5, `call_raise_frac` 0.3, a steeper call-down slope or 0.7 opens is better against tags only, and was
not taken. Open size, c-bet frequency and size, semibluff frequency, `commit_frac`, profiler blend and
prior: all within noise.

**Also fixed on the way.** Under a permuted `rank_order` postflop read the displayed board next to the
canonical hole (KeyError in the evaluator, swallowed by SafeBot): the canonical board is passed through
and a 50-table permuted-rules test guards it. The bestiary `Hero` is seeded and takes
`--hero-config` / `HERO_CONFIG` overrides, which is how the sweep reaches the levers.

## 2026-10-31 drill 4 follow-up (builder: tools/drills)

- **Drill 4's prompt edits land inside each prompt's previous byte count.** All of 01 (3), 02 (2), 03 (4),
  05 (4) and seven of 04's eight are in, and every file is at or under its old size, which is why other
  sentences got terser. Skipped: 04's `/tmp/load` -> scratch edit, because `tests/test_nightof_docs.py` pins
  `--out /tmp/load`. Relocated: the Stage 0 edit aimed at `NIGHT-template.md`'s header is a one-sentence note
  in prompt 01 instead (the template was not in this pass). Prompt 05's short-deck bullet names no key:
  `postflop.flush_tier_shift` / `straight_tier_shift` / `draw_outs_mult` were not in CONTRACTS.md when it was
  written and the test that 05 names only real keys must hold; reword the bullet when they land.
- **`tools/latency.py --native kit_d` hangs the state off a synthetic round-start parent** so the adapter's
  `previous_state` walk recovers the pot (drill 4 finding 4), and picks `last_raise` so `raise_bounds()`
  reproduces `min_raise`. Its round-trip test expects kit D's own legality rule, which differs from the sim's
  in two places (no FoldAction when a check is free; no RaiseAction when nobody left in the hand can call);
  the builder does not paper over that.
- **Kit D's runner keeps the last 4,000 characters of the bot's stderr in the note and, past that, the whole
  text in a temp file named in the note** (drill 4 finding 6). The tail is what the operator reads in the
  terminal; the file is for a long conformance report. Rejected homes for the file: the runner's cwd (litters
  the repo root under pytest) and the submission's directory (may be read-only, or the repo's reference dir).

## Rival 1 in the pool (2026-10-31)

**What landed.** Red-team drill 1's bot (`docs/drills/redteam/redteam-1.md`: built blind in 36 minutes against the
public brief, no access to this repo, 949 lines, stdlib only) is in the simulator as `rival1`. The file is
`hyperion/sim/rivals/rival1.py`, byte-identical to the archived original below a five-line origin header; it is
never edited, a new rival is a new file. `bestiary.RivalBot` is the adapter to the kit interface the brief promised:
`legal` as a set of strings, history as `(seat, ('kind', amount))` tuples converted incrementally per hand, 1-based
`hand_no`, rules as a dict carrying `hand_cap`; the rival's `('kind', amount_total)` answer becomes an `Action` and
goes through `Action.clamp`. The engine times the adapter and the rival together, so the rival sits under the same
enforcement as every bot. Through the adapter it decides in p50 16-28 us, p99 60-150 us (3-5 us over its native
15-22 us), with 0 exceptions and 0 illegal actions on several million decisions here, also when its own `debug` switch
makes it re-raise what its `act()` would swallow. Its strict-mode timeout rate is ~0.01%, the WSL scheduler
jitter every fast bot shows. Fields: `realistic` now seats `rival1` where `naive` was (`naive` stays registered);
the new `top` field is hero, rival1, rival1, pushfold, tag, hero_tight, loose_aggro, montecarlo30.

**Measurements**, 1,000 duplicate tables each (`--tables 125 --rotate --seed 7 --mode strict`), run four at a time on
the 8-core WSL2 box while other agents' sims were also running (which is why `tmo` and `maxus` are not zero for
anybody; p50/p99 are unaffected). CIs are ~2.8x wider than the tuning pass's, which used 1,000 seeds x 8.

`--field realistic` (new composition):
```
bot                      n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival1                 125  5.567 0.129    33   10   10   11   16    8    7    4   60.5    24     0     0     26     81
hero                   125  5.535 0.120    28   10   16   14   13   10    6    4   64.1    15     0     0     19     58
tag                    125  5.352 0.102     6   26   21   18   12    7    6    3   80.0     2     0     0      4     14
pushfold               125  5.024 0.114     8   20   20   13   13   10    8    7   77.5     2     0     0      5     19
loose_aggro            125  4.756 0.128    17   17    9   11   10   13   11   13   69.9     4     0     0      3     11
montecarlo             125  3.286 0.108     3    4    5   10   16   21   23   17   95.3 17936     0     0      3   1502
montecarlo30           125  3.268 0.119     4    5    7   10   12   19   20   23   93.7 11995     0     0      3   2229
timeout_then_recover   125  3.212 0.109     0    7   12   12    9   12   18   30   95.7 26964     0     0      3   2136
```
Paired hero - rival1 on the same seeds: **+0.017 ± 0.199** (a second, traced run: hero 5.587, rival1 5.570).

`--field top`:
```
bot              n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival1         125  5.091 0.103    27   12    9    9   11   13   11    8   66.1    50     0     0     23     91
hero_tight     125  4.839 0.117     8   17   15   15   17   15    9    4   81.4    16     0     0     18     59
hero           125  4.838 0.135    18   10   13   11   16   12   11    8   76.0    12     0     0     17     58
tag            125  4.804 0.120     3   16   23   21   11   11    9    6   86.8     1     0     0      4     19
pushfold       125  4.495 0.111     4   14   18   17   15   10    8   12   87.1     2     0     0      5     23
loose_aggro    125  4.123 0.139    11   14    9    9   11   11   16   19   78.7     5     0     0      3     15
montecarlo30   125  2.720 0.110     2    4    5    7    9   15   23   35   96.3 10141     0     0      4   2229
```
Paired hero - rival1: **-0.211 ± 0.202**; hero - hero_tight +0.006 ± 0.187; hero - tag +0.033 ± 0.182.

Pure strength, hero + 7 rival1 (uniform = 4.50):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival1       125  4.513 0.017    13   13   12   12   12   12   13   13   82.1   113     0     0     16     67
hero         125  4.409 0.117     9   10   14   14   16   15   12   10   87.3    16     0     0     20     60
```

Pure strength, rival1 + 7 hero (uniform = 4.50):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival1       125  4.780 0.139    17   17   10   10    9   12   10   14   74.6    82     0     0     35    135
hero         125  4.460 0.020    12   12   13   13   13   13   13   12   81.6   267     0     0     15     63
```

**Where Hero stands.** Level with the rival in the realistic room, behind it at the top table, and at par to a
little below it heads-up in copies. In `realistic` the two are tied on points (paired +0.02 ± 0.20) but not in
shape: the rival wins 33% of tables to hero's 28% and busts 4 points less often; hero makes up the difference with
more thirds and fourths, i.e. hero ladders better and the rival closes better. With `naive` gone from that field
hero's number fell from 5.94 (tuning pass) to 5.54: the seat that used to feed the table now takes points from
it. In `top`, where the rival sits twice, it is first by 0.25 and hero is in a three-way tie for second with
hero_tight and tag; the paired delta (-0.21 ± 0.20) is just past the noise. Against seven copies of the rival hero
scores 4.41 ± 0.12 (uniform 4.50): fewer firsts (9% vs 13%), the same eighths, and a centre-heavy finish list, so
it is ground down rather than knocked out early. The mirror is sharper: one rival among seven heroes scores 4.78 ± 0.14, +0.28 over uniform, with 17% firsts
and 17% seconds against the heroes' 12%, though also 14% eighths (it takes its stands earlier against a table
that folds). The asymmetry, +0.28 for the rival in a hero room against -0.09 for hero in a rival room, is the
cleanest statement that the rival is currently the stronger bot. (That run took 1,672 s against 205 s for its
mirror, for the reason in the last paragraph.)

**The rival's finish distribution** is top-heavy wherever it has weak bots to feed on and flat where it does not:
33/10/10/11/16/8/7/4 in `realistic`, 27/12/9/9/11/13/11/8 in `top`, 17/17/10/10/9/12/10/14 among seven
heroes, and by symmetry 13% in every place among its own copies. Its bust rate is the lowest of the competent bots in both fields (60.5%, 66.1%) because it folds its
way to the cap when it can afford the blinds (cap mode) and refuses deep 60/40s (risk-of-ruin cap), exactly the
two heuristics its build log describes.

**What the rival punishes** (`--trace-busts hero`, 602 / 750 / 871 busts in realistic / top / vs-7-rivals; every bust
is an all-in, as always). Three things, in order of weight.
1. *Hero calling the rival's shoves.* `preflop/pre/call/vs-shove` plus `pushfold/pre/call/vs-shove` are 21% of hero's
   busts in realistic, 24% in top and 35% against seven rivals, and the fatal classes are 99, JJ, 88, TT, ATo, AJo,
   QJo, A5o. The rival only shoves deep with a range it has capped by risk of ruin and 4-bet-shoves QQ+ only, so
   when hero's call model prices its shove as a wide pusher's, hero is behind. Hero's medium pairs and ace-x
   calls against *this* shover are the single biggest bucket the rival owns.
2. *Hero's own short shoves getting picked off.* `pushfold/pre/raise` (mostly at <= 12 bb) is 34-38% of busts in every field,
   as it was in the tuning pass; the rival's shove-calling range is a stack-and-position estimate that tightens per
   player behind, so against it hero's shoves get called more precisely than against the room average, and hero
   arrives at the short-stack phase more often than the rival does (bust% 64 vs 60, 76 vs 66).
3. *Turn and river calls against the rival's shoves* (14% of busts against seven rivals, 7-9% in the fields). The
   rival's late-street shoves are value: it never bluff-catches, and bluffs the river only against flagged
   folders when 0.6 pot is <= 25% of its stack. A hero call against a rival's turn or river shove is nearly always
   against a hand that beats top pair.
Behind all three is one measurable thing. The rival's opponent model reads hero as a *nit* (VPIP <= 14% after 15
hands) or a *folder* (fold-to-raise >= 75%) in about half of all table-views by hand 40 (nit 49%, folder 44% of
1,239 rival-views over 200 tables; hero's VPIP as the rival measures it is 17%, its fold-to-raise 72%, both a
hair from the thresholds), and once every player behind it is flagged that way it widens its steals 1.6x. The
rival is one of seven opponents in `realistic` yet the sole opponent in 30% of hero's busts there (38% counting
multiway pots); in `top`, two of seven and 36% (about half). Hero is not tuned here (not this builder's files).

**For the strategy owner to look at**, in this order: (a) the shove-calling range against a shover whose observed
shove rate is low: the tuning pass found a patience premium keyed to the shover's shove rate added nothing, but
that was measured in the old realistic field where the shovers were allin, maniac and naive; against a shover
whose deep shoves are capped by risk of ruin the busts say this is where its edge sits, so re-ask it with `rival1`
in the field; (b) blind defence and fold-to-raise: hero's 72% preflop fold-to-raise is what flips the
rival's folder flag and its steals, and `preflop.call_raise_frac` / 3-bet-as-defence are the levers; (c) the
turn/river call-down slope against a bettor with a high aggression stat *and* a low VPIP, where the rival's shoves
are value and hero's `call_margin` 0.15 still pays them off. Not a behaviour but worth knowing: in a table of
seven heroes hero's `hand_end` averages 6.4 ms per call (exact 8-player Malmuth-Harville in `compute` ->
`icm_value`, 98% of the table's wall time), which is outside the per-decision budget in our engine but would
matter if the real kit times `hand_end` or if that curve ever moves into `act()`.

**Not done here.** No Hero tuning; no rival tuning (its knobs OPEN_SCALE / PUSH_SCALE / CAP_MODE / ROR_DEEP stay at
the frozen values, and a tuned rival would be a second file). The `strong` and `chaos` fields are unchanged.

## Variant readiness pass (2026-10-31, builder: strategy/variants)

Scope: `hyperion/strategy/*`, `hyperion/tablegen.py`, `tools/gen_tables.py`, `tools/gen_catalog.py`,
`tables/`, tests, and the new `tools/variant_matrix.py`. The tuner's defaults are untouched; everything
below is gated on `Rules` / `Observation.extras` and is the plain game when they are default.

### Information axis: Hero plays three and four hole cards

- **Table resolution (`strategy/tables.py: tables_for`).** `tables/variants/<extras["variant"]>/` is used
  when its `meta.json` card rules match and the game differs from hold'em in a way a rank remap cannot fix
  (hole-card count, removed ranks, must-use); permuted ranks keep `tables/` and Hero's remap, which was
  already its best result. A 3- or 4-card game with no matching directory plays from a `LabelView`: the
  best-two class's rank and equity plus `label_bonus_pair` / `label_bonus_suited` per extra card, and
  `label_open_step` positions tighter on opens (Config keys). The modules for a variant set are built
  once per table set and cached; a table under default rules is exactly the tuner's bot.
- **Hand class.** Two cards: the 169 label. Three or four: `tablegen.hole_label` ('AKs+l'), the key of the
  catalog tables, computed on the displayed cards. `hole_label` now sorts the hand first: `max()` over
  Chen-tied pairs picked different pairs for a dealt hand than for `class_table`'s sorted combos, so one
  hand in ~25 got a label no table has (`KeyError` inside act(), eaten by SafeBot: the engine's `exc`
  column stayed 0 while `hero.safe.errors` climbed). `tools/variant_matrix.py` counts both.
- **Push/fold with labels.** `PushFold` keeps the 169 heads-up solution and its multiway rule; a label's
  percentile is `1 - rank` from the variant table, and its equity against the opposing range is its equity
  vs one random hand minus the gap between "vs random" and "vs the Nash range" measured on the 169 solution
  at that depth (`call_disc` / `push_disc`, ~0.03-0.06 bb-depth dependent). `with_tables()` shares the solved
  arrays, so the swap costs nothing per decision.
- **Postflop (`read_multi`).** The same board-relative tiers as `read`, over any number of hole cards, kept
  whole (8 cards at the river: `warm(8)` now runs in `new_table`, 0.55 s once per process, never inside a
  timed call) or must-use-two (Omaha: best of C(4,2) x C(board,3) evaluations, 18 us on the river; an Omaha
  flush draw needs two in hand and two on board). Made pairs and two pairs drop `multi_tier_penalty` (1)
  because every hand at the table is stronger; draws keep their outs.
- **`variant_decide`** on `HeroCore` (and guarded on `Hero`, so the engine finds it on `bot.impl`): discard
  keeps the two cards with the best flop read (tier equity, then outs, then preflop rank) or, before the
  flop, the best two-card class; swap keeps made hands and draws and replaces the lowest card that pairs
  nothing and is not part of a flush draw; buy_card buys when the price is at most a tenth of the stack.

### Extras-driven variants

- `Spot.bounty_bonus`: with `extras["bounties"]`, the expected extra chips if we win this pot (P(bounty rank
  in hand or still to come on the board) x ((ratio - 1) x net win + constant)); it sits in the pot for
  pot odds and in the winning branch of every shove / call / commit EV (prompt 05's promise).
- `Spot.ko_points` (knockout bounty): the house's points per bust are added to the winning branch of a
  push (times the share of live opponents we cover), a shove call (when we cover the shover) and a
  postflop commitment, only when the value curve is in points (`IcmCurve.points`; the chip-linear fallback
  ignores them).
- exposed_card: other seats' face-up cards are dead for flush and straight outs, a high card (Q+) showing
  behind us shrinks steals by `exposed_steal_mult` each, and a shover's exposed card moves the calling
  margin by `exposed_shove_margin` (both PreflopParams).
- two_boards: both boards are read; value needs the weaker board's tier, the equity proxy is the mean (a
  split is half a pot), every size is halved (`two_boards_size_mult`).
- swap_one_turn: value and big-value tiers are one higher on streets before the swap street.

### Ranking axis

- lowball: a mirror map over the 169 (the class at the mirrored position of the hold'em order; 72o reads as
  AA) feeds preflop and push/fold unchanged; postflop `read_low` scores the weakest five of my cards by
  the top card of a pairless, non-straight, non-flush low, with outs to a better low while cards are to come.
- wild_deuces: a wild with x reads as the pair of x preflop (22 as AA); postflop each wild becomes, greedily,
  the card that makes my best hand (48 evaluations per wild) and the normal read runs on the result, one
  tier lower when the wild sits on the shared board.
- flush_over_full_house (and short deck, which carries the same `category_order`): a full house on a
  three-flush board is tier 6, not 7. Prompt 05's short-deck bullets now have keys:
  `postflop.flush_tier_shift`, `postflop.straight_tier_shift`, `postflop.draw_outs_mult` (defaults 0, 0, 1.0).
- short_deck plays from `tables/variants/short_deck/` (81 classes, its own matrix and push/fold solve).

### Loader (drill 4 repo finding 1)

`tables.load()` accepts the class scheme the files declare: the 169 labels a `meta.json`'s rules imply
(or the equity file's own keys when there is no meta yet), filling absent classes with zero equity and
rank 0 so 169-indexed code still works, embedding a smaller matrix in the 169 order, and `hole_classes.json`
labels for 3 or 4 cards. `Tables.classes / combo_count / total_combos / live` carry the scheme; the push/fold
solver and `PushFold`'s percentiles use them (630 combos under a short deck, not 1,326). A fallback to built
tables is logged and warned, `strict=True` raises (`TablesError`), and the generator loads the set it just
wrote strictly, so a solve from a built fallback cannot happen again. `tests/test_strategy_variants.py`
regenerates a tiny short-deck set and asserts `source == "disk"` and 81 classes. The committed short-deck
set was regenerated: its old `pushfold_hu.json` had been solved from a built standard matrix.
`preflop.open_frac_default` (finding 3) is read only for more than 7 players behind, which an 8-max table
never has, so it is inert there by construction; `preflop.open_frac_mult` and `preflop.open_step` are the
levers for "a step wider / tighter", and the catalog's `config_patch` entries that lean on
`open_frac_default` should move to them (drills owner).

### Push/fold corrections (HRC cross-check)

- **Solver.** `solve_hu_pushfold` is fictitious play: each side best-responds to the other's average
  strategy, a depth warm-starts from the previous depth, and it stops when both best-response gains are
  under `tol` (1e-4 bb per hand; a cold start gets 40 damped iterations first). The old 40-iteration damped
  loop ended on alternate sides of the boundary at successive depths, which was the 21-25 bb zig-zag.
  Output is the mixed strategy thresholded at 0.5, the mixed frequencies, equities against the mixed range,
  and `converged` {depth: [iterations, gain]}. Default solve 17.8 s (worst gain 1.0e-4 bb).
- **Matrix.** 1,000 -> 5,000 samples per class pair (`tools/gen_tables.py --matrix-samples`, default
  `MATRIX_SAMPLES`); the catalog's 2-card entries get 1,000 (was 200). Default generation: preflop 35.0 s,
  matrix 46.3 s, push/fold 17.8 s, flops 0.6 s, **99.8 s total** on 7 workers (budget 3 min). The preflop
  and flop tables came out byte-identical (same seeds); `hu_matrix.json` and `pushfold_hu.json` changed.
- **HRC after** (`python tools/hrc_check.py`, matrix `24ca05de27f4111b`): push 28 disagreements over 24
  depths (**1.2 per depth**, was 73 / 3.0; target under 2), call 13 (0.5, was 17 / 0.7); mean MAD push 0.007
  (was 0.018), call 0.003 (0.004). Push frequency at 20-25 bb: 0.400, 0.388, 0.385, 0.382, 0.367, 0.360 against
  HRC's 0.402, 0.382, 0.382, 0.380, 0.380, 0.363: monotone, no oscillation. The 5-10 bb suited-junk pushes are
  down to one or two classes per depth (94s at 6-7, 43s/84s at 8-9). Per depth, push disagreements:
  2:1 3:0 4:0 5:1 6:2 7:2 8:2 9:2 10:1 11:1 12:2 13:1 14:0 15:2 16:0 17:1 18:1 19:0 20:1 21:2 22:1 23:1 24:3 25:1;
  calls: 2:0 3:0 4:0 5:1 6:0 7:1 8:0 9:0 10:1 11:1 12:0 13:1 14:0 15:1 16:2 17:0 18:1 19:0 20:0 21:0 22:1 23:2 24:1 25:0.

### Config keys added (CONTRACTS.md regenerated)

`profiler_dead_after / station_after / nit_after / maniac_after / random_after`, `icm_buckets`,
`icm_me_subdiv`, `label_bonus_pair`, `label_bonus_suited`, `label_open_step`, `preflop.open_frac_mult`,
`preflop.open_step`, `preflop.exposed_high_rank / exposed_steal_mult / exposed_shove_margin`,
`postflop.flush_tier_shift / straight_tier_shift / draw_outs_mult / multi_tier_penalty /
two_boards_size_mult / wild_board_penalty / low_draw_outs_cap`.

### Baseline protected (400 duplicate seeds x 8 rotations, seed 7, strict, same box, four runs in parallel)

"HEAD" is commit c28934a's code and tables in a separate worktree, i.e. the tuner's bot on today's fields;
"new" is this pass. The realistic field changed under the tuner's numbers: `rival1` took `naive`'s seat
(c28934a), and it is now the strongest bot in the room, which is why HEAD's realistic line is 5.52 and not
the 5.943 recorded above; the strong field is unchanged, so that line compares directly.

| field | hero HEAD | hero new | tag HEAD / new | leader | hero exc / ill | hero p50 / p99 us |
|---|---|---|---|---|---|---|
| realistic (rival1 seat) | 5.520 ± 0.070 | **5.554 ± 0.071** | 5.303 / 5.263 | rival1 5.660 / 5.654 | 0 / 0 | 21 / 74 |
| strong | 5.088 ± 0.077 | **5.075 ± 0.077** | 4.672 / 4.672 | hero both | 0 / 0 | 18 / 60 |

Both within the interval of the HEAD run (and strong is above the tuner's 5.011 ± 0.048); the new
push/fold tables and the variant plumbing cost nothing on the default game. The pytest latency gate
(`test_latency_two_thousand_random_decisions`, mean < 0.15 ms, p99 < 0.5 ms) passed inside the full suite
while four sims were running.

### Variant readiness (2026-10-31)

`python tools/variant_matrix.py --tables 300 --seed 7 --field realistic --workers 4` (427 s): one strict
`python -m hyperion.sim --variant NAME --field realistic --tables 300 --seed 7` per entry, Hero's rank among the
eight bot names by points. "before" is the catalog baseline above (hero points / rank; `*` = Hero folded every
hand, first place was the artifact described there), measured when `naive` held the seat `rival1` has now, so
the before column is the old field and the rest is today's. exc = engine exceptions + SafeBot inner errors (0
everywhere; the matrix counts both because SafeBot hides the latter from the engine). Verdicts: READY = plays
(VPIP >= 10%) and ranks top 2; PLAYS = 3-4; WEAK = 5+ or VPIP < 10%; BROKEN = any exception.

| variant | axis | before: pts / rank | hero pts (±95%) | rank | exc | ill | VPIP % | bust % | p99 us | verdict | reason |
|---|---|---|---|---|---|---|---|---|---|---|---|
| permuted_ranks | ranking | 6.33 / 1 | 6.34 ± 0.22 | 1 / 8 | 0 | 0 | 40 | 44 | 87 | **READY** | next rival1 5.66 |
| short_deck | ranking | 5.25 / 3 | 5.89 ± 0.21 | 1 / 8 | 0 | 0 | 43 | 69 | 84 | **READY** | next tag 5.60 |
| lowball | ranking | 4.99 / 1 | 7.74 ± 0.13 | 1 / 8 | 0 | 0 | 50 | 5 | 91 | **READY** | next tag 4.77 |
| wild_deuces | ranking | 5.19 / 4 | 7.04 ± 0.22 | 1 / 8 | 0 | 0 | 56 | 22 | 120 | **READY** | next tag 5.16 |
| flush_over_full_house | ranking | 5.31 / 2 | 5.42 ± 0.25 | 2 / 8 | 0 | 0 | 39 | 64 | 80 | **READY** | second to rival1 5.62 |
| toss_or_holdem | information | 6.49* / 1 | 6.07 ± 0.20 | 1 / 8 | 0 | 0 | 42 | 66 | 85 | **READY** | next rival1 5.63 |
| three_card_blind_discard | information | 6.49* / 1 | 5.97 ± 0.18 | 1 / 8 | 0 | 0 | 42 | 74 | 78 | **READY** | next rival1 5.65 |
| three_card_keep | information | 6.60* / 1 | 6.05 ± 0.19 | 1 / 8 | 0 | 0 | 42 | 70 | 104 | **READY** | next rival1 5.82 |
| omaha_four | information | 6.96* / 1 | 6.73 ± 0.16 | 1 / 8 | 0 | 0 | 43 | 55 | 127 | **READY** | next rival1 6.15 |
| swap_holdem | information | 5.33 / 3 | 5.55 ± 0.23 | 2 / 8 | 0 | 0 | 39 | 64 | 74 | **READY** | second to rival1 5.72 |
| swap_one_turn | information | 5.30 / 4 | 5.74 ± 0.24 | 1 / 8 | 0 | 0 | 40 | 58 | 69 | **READY** | next rival1 5.46 |
| exposed_card | information | 5.37 / 2 | 5.49 ± 0.22 | 2 / 8 | 0 | 0 | 37 | 69 | 71 | **READY** | second to rival1 5.58 |
| two_boards | information | 5.43 / 2 | 5.22 ± 0.22 | 3 / 8 | 0 | 0 | 34 | 65 | 75 | **PLAYS** | rank 3; rival1 6.03, tag 5.41 |
| bonus_card | information | 5.78 / 1 | 5.49 ± 0.24 | 1 / 8 | 0 | 0 | 42 | 68 | 66 | **READY** | next tag 5.24 |
| bounty | payoff | 5.30 / 4 | 5.37 ± 0.24 | 2 / 8 | 0 | 0 | 40 | 60 | 68 | **READY** | second to rival1 5.58 |
| knockout_bounty | payoff | 6.34 / 2 | 6.87 ± 0.39 | 1 / 8 | 0 | 0 | 40 | 64 | 66 | **READY** | next rival1 6.85 |
| top_heavy | payoff | 17.36 / 4 | 19.63 ± 2.15 | 2 / 8 | 0 | 0 | 40 | 64 | 62 | **READY** | second to rival1 22.17 |
| hi_lo | payoff | 5.32 / 2 | 5.55 ± 0.24 | 2 / 8 | 0 | 0 | 38 | 63 | 66 | **READY** | second to rival1 5.55 |
| pot_limit | betting | 5.21 / 4 | 5.45 ± 0.24 | 2 / 8 | 0 | 0 | 39 | 62 | 62 | **READY** | second to rival1 5.74 |
| antes_from_level_3 | betting | 5.20 / 4 | 5.53 ± 0.24 | 2 / 8 | 0 | 0 | 39 | 64 | 61 | **READY** | second to rival1 5.60 |
| fixed_raise | betting | 5.72 / 1 | 5.65 ± 0.24 | 2 / 8 | 0 | 0 | 36 | 53 | 58 | **READY** | second to rival1 6.15 |
| fast_schedule | betting | 5.18 / 4 | 5.49 ± 0.24 | 2 / 8 | 0 | 0 | 36 | 70 | 56 | **READY** | second to rival1 5.69 |
| straddle | betting | 5.32 / 2 | 5.62 ± 0.26 | 2 / 8 | 0 | 0 | 45 | 61 | 57 | **READY** | second to rival1 5.72 |

Verdicts: READY 22, PLAYS 1, WEAK 0, BROKEN 0. The one PLAYS: two_boards, third at 5.22 ± 0.22 behind rival1
6.03 and tag 5.41 (the baseline had Hero second at 5.43 with `naive` in the field); the min-tier value rule and
halved sizes keep Hero out of trouble but rival1 scoops more, and nothing here reads which board an opponent
is drawing to. rival1 is the leader on 15 of the 23 entries; Hero is first on the eight where the variant
changes what a hand is worth (permuted ranks, short deck, lowball, wild deuces, the four extra-card games),
plus swap_one_turn, bonus_card and knockout_bounty.

Not done, for the record: hi_lo still plays high only (second anyway); bounty uses the posted bounty rank and
pot size, not opponents' bounties; the discard decision does not read opponents' face-up discards as dead
cards; the Omaha straight-draw count is the two-card mask (it can count a wrap that needs three hole cards);
the label fallback's bonuses (0.04 / 0.02) and the multi-card tier penalty were not swept.
