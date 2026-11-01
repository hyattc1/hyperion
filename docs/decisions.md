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

## Rival 2 in the pool (2026-10-31)

**What landed** (commit `fd8a3fa`). Red-team drill 2's bot (`docs/drills/redteam/redteam-2.md`: a computation-first
team, built blind in 31 minutes against the same brief and kit as rival 1, with no access to this repo or to rival 1;
1,476 lines, stdlib only) is in the simulator as `rival2`. `hyperion/sim/rivals/rival2.py` is byte-identical to the
frozen original (md5 `1ad3b05a...`) below a five-line origin header. `bestiary.Rival2Bot` is `RivalBot` with
`MODULE = "rival2"` and nothing else: rival 2 reads exactly the kit fields rival 1 does, only `hand_no` from
`hand_end`, and ignores the rules dict (it never learns the 200-hand cap; its ICM curve values stacks at all
times). Two process-level facts: importing it costs ~1.15 s (the 169x169 matrix, the push/fold solve, the ICM
table) and ends in `gc.freeze()`, which applies to the whole importing process; `kit` is not importable here, so it
uses its own fallback `Agent` and skips its `_warm()` (first act of a table: mean ~230 us, max ~360 us, so the
skipped warm-up costs nothing on 3.10). Its postflop sampler is time-boxed on the wall clock, so unlike every
other bot here its play is not bit-reproducible: the same 1,000 seeds traced a second time gave hero 3.530 ± 0.124
against 3.556 ± 0.111. Fields: `top` seats `rival2` where `montecarlo30` was (hero, rival1, rival1, pushfold, tag,
hero_tight, loose_aggro, rival2; not re-measured here); new `top2` is hero, rival1, rival2, rival2, pushfold, tag,
hero_tight, loose_aggro; `realistic` is unchanged.

**Latency and timeouts.** Through the adapter under engine enforcement it decides in p50 54-163 us (depending on the
field), p90 ~280 us, p99 284-287 us on a quiet host; the adapter adds ~3 us over its native
p50 54-111 / p99 280-282 us. 0 exceptions and 0 illegal actions on ~6.7 million decisions in the runs below, and
0 on 1.26 million more with its `DEBUG` switch re-raising what its `act()` would swallow (top2, hero + 7 rival2 and
rival1 + 7 rival2, 480 tables each, measure mode). Its strict-mode timeout rate depends on the host far more than
any other bot's, because it spends 5-8x as long per decision as rival 1 and is preempted mid-call that much more often:

| host load (8-core WSL2) | rival2 over 1 ms | rival1 | hero | 5-us bots |
|---|---|---|---|---|
| quiet, one process (30 tables) | 0.003-0.04% | ~0.01% (rival 1 entry) | | |
| ~9 CPU-bound processes (measure-mode runs below) | 0.48-0.92% | 0.06-0.14% | 0.05-0.11% | 0.02-0.03% |
| ~12 CPU-bound processes (strict runs below) | 1.78-2.69% | 0.34-0.45% | 0.25-0.34% | 0.07-0.10% |

A fixed 200-us busy loop overran 1 ms 1.2-3.3% of the time at the worst of that load, the same as rival 2: these are
the host's timeouts, not a slow path in the bot (its own worst path is the sampler's 520-us hard cap). On a
tournament host that gives each table a core the expected rate is the quiet row; on a shared or slower host it is
real and costs it a fold on that fraction of decisions. The test
(`test_rival2_timeout_rate_in_strict_mode_is_under_two_percent`) asserts < 2%, and when it is over it times the
same busy loop and skips with both numbers if the host is the cause.

**Measurements**, 1,000 duplicate tables each (`--tables 125 --rotate --seed 7 --mode strict`), all at HEAD `fd8a3fa`
(run from a clean worktree of that commit: hero is the committed `hyperion/strategy`, not the deep pass's
uncommitted edits), five at a time while the deep pass's 7-worker sweep was running, i.e. the ~12-process row
above. Uniform is 4.50 points.

`--field top2` (HEAD `fd8a3fa`):
```
bot             n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival2        125  4.980 0.094    21   14   12   10   12   11   11    9   71.0  8220     0     0    123   4247
rival1        125  4.722 0.146    24   11    8    8   10   13   14   12   69.9   720     0     0     24    205
tag           125  4.568 0.109     2   14   20   19   16   11   10    8   87.3   128     0     0      4     23
hero_tight    125  4.415 0.114     8   12   14   15   13   16   14    9   82.9   475     0     0     17    130
hero          125  4.363 0.122    12   11   11   10   15   15   14   11   82.5   548     0     0     18    142
pushfold      125  4.257 0.124     3   14   14   19   12   12   12   14   86.0   138     0     0      5     28
loose_aggro   125  3.715 0.141     9   10    9    9   11   10   14   28   83.8   100     0     0      4     20
```
Paired on the same seeds: hero - rival2 **-0.617 ± 0.177**, hero - rival1 -0.358 ± 0.201, hero - tag -0.205 ± 0.173,
hero - hero_tight -0.051 ± 0.176, rival1 - rival2 -0.258 ± 0.194.

hero + 7 rival2 (HEAD `fd8a3fa`):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival2       125  4.635 0.016    13   14   13   13   12   12   12   12   72.6 21219     0     0    128   4147
hero         125  3.556 0.111     6    5    8   11   13   18   19   19   88.9   445     0     0     23    136
```
Paired hero - rival2 **-1.079 ± 0.127** (traced replicate: hero 3.530, -1.109 ± 0.141).

rival2 + 7 hero (HEAD `fd8a3fa`):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival2       125  5.189 0.122    19   17   16   10   11   11    6    9   75.5  4265     0     0    163   4265
hero         125  4.402 0.017    12   12   12   13   13   13   13   13   82.5  2874     0     0     13     87
```
Paired rival2 - hero **+0.788 ± 0.139**.

rival1 + 7 rival2, the rivals head to head in our engine (HEAD `fd8a3fa`):
```
bot            n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill  p50us  p99us
rival2       125  4.554 0.021    12   13   13   13   13   13   12   12   75.6 23023     0     0    125   4179
rival1       125  4.125 0.145    17    8    9    9    8   12   19   18   77.0   551     0     0     26    163
```
Paired rival1 - rival2 **-0.429 ± 0.166**.

The same four in measure mode (HEAD `fd8a3fa`, two at a time, nothing folded for time), to check that the
forced folds above do not carry the result: top2 rival2 5.030, rival1 4.641, hero 4.351 (hero - rival2 -0.679 ±
0.176); hero + 7 rival2: hero 3.563 (-1.071 ± 0.135); rival2 + 7 hero: rival2 5.350 (+0.971 ± 0.146); rival1 +
7 rival2: rival1 4.116 (-0.438 ± 0.144). The timeouts cost the lone rival 2 among heroes 0.16 points and change
nothing else by more than noise.

**Where Hero stands, and how the two rivals compare in our engine.** Hero is well behind rival 2, further than it is
behind rival 1, and rival 2 is the stronger rival here. Against seven copies of rival 2 hero scores 3.56 ± 0.11,
0.94 under uniform (against seven rival 1s it was 4.41, -0.09), with 6% firsts and 38% sevenths-or-eighths, and it
busts in 89% of its seats (rival 2's copies: 73%). The mirror says the same thing from the other side: one
rival 2 among seven heroes scores 5.19 ± 0.12 (5.35 with no time enforcement), +0.69 over uniform where rival 1
managed +0.28, with 19% firsts and 17% seconds. In `top2` rival 2 is first (4.98), rival 1 second (4.72), and hero
fifth of seven at 4.36, behind tag and level with hero_tight; the paired gap to rival 2 is -0.62 ± 0.18, nearly
twice the gap to rival 1. Head to head, one rival 1 among seven rival 2s scores 4.13 ± 0.15 (-0.43 paired), with
the top-heavy, bust-heavy shape it shows everywhere: 17% firsts but 37% sevenths-or-eighths. That is a clearer
verdict than the drill operator's tie in rival 2's own engine (6.22 vs 6.30 in the mixed field, rival 1 ahead
against nits). The likely reason is the field: ours are competent short-stack players (hero, pushfold, tag,
the rivals) rather than rule-bot nits, and the operator's summary was that rival 2 wins the preflop, all-in and
heads-up game, while rival 1 wins the postflop game against nits. Against these fields the preflop and all-in
game decides the table.

**What rival 2 punishes** (`--trace-busts hero`, hero + 7 rival2: 896 busts in 1,000 seats, every one an all-in;
plus a 600-table log of every preflop all-in between hero and the field, with the showdown hands, against seven
rival 1s and seven rival 2s for contrast; percentiles below are of rival 2's own equity-vs-random ranking, lower
is stronger). By module: `preflop.call_shove` 27.7%, `pushfold.call_shove` 21.9%, `pushfold.reshove` 15.7%,
`pushfold.push` 14.6%, postflop calls of a shove 8.3% (turn and river 7.3%, half the 14% against rival 1). 64%
start the hand at <= 12 bb (16% at <= 5) and 21% at 13-25 bb. The classes hero busts with most preflop are
ATo, JJ, QQ, KQo, 99, AJo, AKo, TT, KTo, 77 and A9o. Read with the all-in log, the busts say three things, in
order of weight.
1. *Hero folds to its shoves and re-shoves at 13-25 bb.* This is the leak, and the trace cannot see it because
   folds do not bust. Rival 2 shoves or re-shoves into hero 2,861 times per 600 tables at 13-25 bb, against 1,472
   for rival 1. Its re-shove engine prices F x steal + (1-F) x showdown through the ICM curve over every open it
   sees, so its range there is wide: showdown hands average the top 22%, against rival 1's top 14%. Hero folds
   93%. The 7% it calls (hands averaging the top 7%) win 63% of 212 showdowns (± ~6.5 points; 50% against rival 1),
   where a call of a 15-20 bb re-shove over an open needs roughly 40-45% with ICM. So hero's calling threshold
   there is far tighter than this range warrants. That is an inference from showdowns, not a solve. Each fold
   gives up hero's open, and the bleed shows up downstream: hero open-shoves at <= 12 bb 961 times per 600 tables
   against rival 2, against 334 against rival 1.
2. *Hero faces its short shoves more often; it does not call them worse.* Calls of a shove are half of hero's busts
   (35% against seven rival 1s), but per call hero does fine. At <= 12 bb rival 2's shoves are tighter than rival
   1's (showdown hands average the top 19% against 28%), hero calls tighter to match (23% of spots against 28%), and
   it wins 50% of 980 showdowns, the same 50% as against rival 1, while needing well under 50% with the dead money.
   The bust share is high because rival 2 shoves into hero 69% more often at that depth (4,319 vs 2,562 spots), and
   hero is at that depth more often (item 1).
3. *Hero's own short shoves get called by tighter hands.* Rival 2 folds to them more often than rival 1 (it calls
   24% of hero's <= 12 bb open-shoves against 32%, and 29% of its re-shoves against 53%) but calls with stronger
   hands (top 6% against re-shoves, against rival 1's top 9%). Hero wins 43% of called open-shoves and 35% of called
   re-shoves, against 47% and 32% versus rival 1. That is about the same as rival 1, so this is not where rival 2
   gains; together these are 30% of busts, a little under the 34-38% in the rival 1 fields.

None of this is exploitation. Rival 2's two-number opponent model barely moves. At the end of each of 100 tables,
its fold-to-aggression posterior is 0.46-0.50 for every opponent (prior 0.50). It reads hero's VPIP as 0.27-0.31
(prior 0.25; it reads tag at 0.12 and loose_aggro at 0.33). So it treats hero as an average player and plays its
computed baseline. Rival 1, by contrast, flagged hero as a nit or folder in about half its views and widened its
steals 1.6x. Rival 2 beats hero with the objects it computed: a push/fold solve, an exact ICM curve per hand, and
re-shove equity against the opener's range.

**For the strategy owner**, in this order (Hero is not tuned here; not this builder's files). (a) Calling re-shoves at
13-25 bb: 93% folds against a range averaging the top 22%, with the calls winning 63%. The lever is the calling
range against a re-shover whose shove rate is high, the other side of the rival 1 entry's item (a). (b) Shove
pressure at <= 12 bb: hero's calls win their share of showdowns, but it faces 69% more shoves. Whether its fold-heavy
short-stack play, or the chips lost in (a), is what puts it there so often is the question to measure first.
Also worth knowing from these runs: under the ~12-process load, Hero's SafeBot went to panic mode ("after 5
overruns") 5-12 times per 1,000-table strict run, with `safe_over` at 523-694 for one hero seat and 3,699 across
seven. That is the same host effect as rival 2's timeouts, seen from inside Hero.

**Also registered here: `micro` and the `public` field** (added at the coordinator's request after the measurements
above). `hyperion/sim/rivals/microholdem.py` (the sparring agent's adapter, `96bd898`) plays MicroAgent from the
public repo ryankkhalil19/microholdem (MIT). Per `docs/drills/public-repos-sparring.md` it is the strongest public
prep bot, level with Hero. Nothing from that repo is copied here; the adapter imports a clone at run time. The
bestiary registers it as `micro` only when `HYPERION_MICROHOLDEM` is set. When it is unset, `micro` is absent from
`REGISTRY` and `--list`, and `make_bot("micro")` and `field_names("public")` raise `bestiary.BotUnavailable` (a
`KeyError`) naming the variable and what it must point at. The new field `public` (hero, micro, micro, rival1, rival2,
tag, pushfold, loose_aggro) exists only when `micro` is registered. The gate is the variable alone, so importing the
bestiary never loads numpy or their package. A setup with the variable set but broken fails when the bot is built,
with the adapter's reason. MicroAgent's engine refuses anything but two hole cards (`ValueError: hero must hold
exactly two cards`), so `test_bots_survive_a_three_card_variant_with_permuted_ranks` now leaves out
`bestiary.OPTIONAL_BOTS`; with the variable set, `micro` stays in the 200-hand and budget tests and passes them. Two
tests cover it. One checks, in a fresh interpreter with the variable removed, that both are disabled and the error
names the variable. The other plays four strict `public` tables when the variable is set (0 exceptions, 0 illegal, 0
replay mismatches; MicroAgent p50 20 / p99 145 us) and skips otherwise. To enable it on this box, under the session
scratchpad (`/tmp/claude-1000/-home-connor-dev-grimoire/e2efc890-5e87-4f77-a595-b50b696294b8/scratchpad/`):
`HYPERION_MICROHOLDEM=<scratchpad>/publicrepos/ryankkhalil19_microholdem`,
`HYPERION_MICROHOLDEM_CORE=<scratchpad>/mh_build/_core.cpython-312-x86_64-linux-gnu.so`, plus numpy. The project venv
has no numpy, so for the tests `<scratchpad>/venvs/microholdem/lib/python3.12/site-packages` went on `PYTHONPATH`
rather than installing anything; run with `python -B` to keep bytecode out of the clone, which `git status --ignored`
still shows clean. One rough edge, in a file this builder does not own: with the variable unset, `--field public`
fails in the runner's argparse as an invalid choice (`choices=sorted(FIELDS)`), not with the `BotUnavailable` message.
`micro` was not measured at 1,000 tables here; the deep pass will do that. It is an opponent only, and nothing from it
goes into Hero.

**Not done here.** No Hero tuning; no rival tuning (rival 2's knobs `OPEN_BASE`, `MC_BUDGET_US`, `FIT_TYPED` stay at
the frozen values; a tuned copy would be a new file). `realistic`, `strong` and `chaos` are unchanged; the new
`top` composition was not measured. The repeat on a quiet host was not possible: the deep pass's sweeps kept the
box at 8-12 CPU-bound processes throughout. The strict tables above therefore overstate rival 2's timeouts against
a dedicated host. The measure-mode companions bound the effect on points.

## Deep Hero pass (2026-10-31, builder: deep pass)

Scope: `hyperion/strategy/*`, `hyperion/sim/runner.py` and `engine.py` (observability only), `tools/sweep.py`,
`tools/gen_multiway.py`, `tools/rmh_check.py`, `tables/pushfold_multi.json`, tests. Targets as briefed: T1 Hero >=
rival1 + 0.15 on realistic and top with disjoint intervals; T2 Hero among 7 rival1 >= uniform and rival1 among 7
Heroes <= uniform + 0.1; T3 no regression on base and strong; T4 latency gate plus hand_end / new_table p99 < 1 ms;
T5 readiness not worse; added mid-pass: T6 MicroAgent among 7 Heroes <= uniform + 0.1, T7 Hero >= rival2 - 0.1 on
top2, T8 rival2 among 7 Heroes <= uniform + 0.2.

### Observability (commit f955955)

`BotStats.safe_err` / `safe_over`: once per table the engine reads the SafeBot inside each bot (`find_safe` walks
`.safe`, `.impl`, `.inner`) and adds the exceptions it swallowed and the calls that ran past its own deadline. The
runner prints both columns and a WARNING line when any error was swallowed; `tools/sweep.py` carries them
(`serr`). `--trace-busts` names `module.sub_decision` (each module exposes `last`, e.g. `pushfold.reshove`,
`preflop.call_shove`) and flags `inner_error` (SafeBot's fallback acted) and `overran`. safe_err was 0 on every
run of this pass.

### hand_end and new_table (commit 5257118)

Under Malmuth-Harville (a Plackett-Luce ranking) the chance that j finishes above me is s_j / (s_me + s_j). With
linear payouts (8..1) my points are therefore pay_1 - step * sum_j s_j / (s_me + s_j): exact, O(n), ~1 us at
eight seats. `icm_me` uses that, and a forward pass over the 2^(n-1) opponent subsets for other payouts (~50 us
at eight seats against ~350 us for the full recursion, which computed every seat). With non-linear payouts and 7+
alive the curve samples a thinner ratio set (`icm_ratios_many`). Replayed table of eight Heroes, min of three cold
replays (`tests/test_hand_end_timing.py`): hand_end mean 34 us / p99 42 us on the default payouts, mean 228 /
p99 433 us on top-heavy ones; new_table p99 46 / 425 us. It was 6.4 ms mean per hand_end.

### Solved multiway push/fold (commit ce5a137)

`hyperion/strategy/multiway.py`, `tools/gen_multiway.py`, `tables/pushfold_multi.json` (2.5 MB, 433 KB compressed).
Chip-EV all-in-or-fold in big blinds, every stack S at hand start, SB 0.5 / BB 1, no antes, pairwise card removal
(shover vs each responder). (a) First-in shove against k = 1..7 behind at 2..25 bb: k = 1 is the SB against the
BB (the heads-up game); for k >= 2 the shover posted nothing and k-2 non-blinds, the SB and the BB act behind it.
No-overcall model: the first call ends the action, so a caller's best response depends only on the shover's range
and its own blind, and callers come in three types (n / sb / bb). (b) Re-shove over a 2.3 bb open from the top w
of hands (w = 0.10, 0.17, 0.25, 0.40, 0.60) with m = 0..4+ behind at 4..25 bb; if nobody behind calls, the opener
calls or folds. Solver: alternating fictitious play with linearly weighted averages and a few damped warm-start
steps per depth (plain 1/t FP needed 3,743 iterations at k = 7, 22 bb for what this does in 123). 718 solves, tol
1e-4 bb per hand; first-in mean 19 iterations, worst gain 9.99e-5; one re-shove cell (w 0.25, m 4, 7 bb) stopped at
the 4,000 cap with 5.0e-4 bb. **36.5 s wall on 7 workers** (budget 10 minutes). Outputs per solve: the set, its
combo frequency, per class P(nobody calls) and equity when called, each caller type's call set and frequency, a
caller's equity against the shoving range, and a combo-weighted order.

Checks: k = 1 reproduces `pushfold_hu.json` within 0-2 classes per depth (push 1 class at 5, 9, 13, 22 bb, 2 at
10; calls 1 class at six depths), frequencies within 0.01. Two model facts worth knowing: P(nobody calls) does not
fall with k at equilibrium (the shover tightens, so the callers do: 0.63..0.65 at 10 bb for k = 1..7), and the
re-shove family has a second, gambling equilibrium at short stacks (with no overcalls the opener's 2.3 bb is dead
money for everyone behind); the re-shove solves run from 25 bb down to stay on the realistic branch, and the 63 of
550 cells still on the other branch (m >= 1, 4-7 bb, detectable by any caller type calling > 0.5) are not used.

**RangeMyHand cross-check** (`tools/rmh_check.py`; `hasuwini77/push-fold-ranges` commit c913a16, CC BY 4.0,
downloaded to `~/.cache/hyperion/rmh/`, never committed; their seats key on players behind):

| their seat -> ours | disagreements (we shove / they shove) | per depth | mean MAD | shove % ours / theirs at 5, 10, 15, 20 bb |
|---|---|---|---|---|
| SB (1 behind) -> k1 | 101 (39 / 62) | 4.2 | 0.034 | 72.4/72.2, 58.4/58.2, 45.2/45.4, 40.0/40.4 |
| BTN (2) -> k2 | 140 (64 / 76) | 5.8 | 0.045 | 40.5/40.3, 32.3/33.0, 26.5/26.0, 22.0/19.8 |
| CO (3) -> k3 | 145 (111 / 34) | 6.0 | 0.047 | 32.6/32.6, 25.2/23.7, 18.3/16.9, 14.0/11.9 |
| 6-max UTG (5) -> k5 | 198 (170 / 28) | 8.2 | 0.055 | 24.3/23.1, 15.4/13.1, 10.9/8.9, 8.2/7.1 |
| MP (6) -> k6 | 180 (146 / 34) | 7.5 | 0.052 | 21.1/21.3, 12.9/10.8, 8.9/7.8, 6.8/6.4 |
| UTG (8) -> k7 (8 vs 7 behind) | 177 (139 / 38) | 7.4 | 0.053 | 18.4/18.5, 10.9/8.9, 7.2/6.9, 4.9/5.5 |

With three or more behind we shove blocker hands they fold (A4s-A8s, QTs, JTs, QJs, KTs, KJs, K9s, KQo, KJo; they
have 0.01-0.10) and they shove 66-99 where we fold; we are 1.5-2.5 points wider at 10-20 bb. Two checks say our side
holds: a Monte Carlo deal of all eight hands with full card removal agrees with our shove EVs (k = 7, 15 bb: the
callers take TT+, AQs+, AK, so 88 is -0.08 bb and A5s +0.06 bb), and rebuilding their stated recipe (no card removal,
220 rounds of plain FP) from our matrix reproduces their tables within 1.5-2.8 classes per depth; that 220-round
profile still has best-response gains of 3-6e-3 bb for the shover and 0.03-0.06 bb per shove faced for the callers,
30-600x our tolerance. Switching card removal off halves the disagreement, which is why their SB seat (heads-up) is
close to ours and to HoldemResources. The sparring pass's MicroAgent cross-check (Hero's old rule shoved 44% on
the button at 10 bb, the solve 32%) agrees: the table puts the button at 32.3% and UTG at 10.9% (the heuristic said
21%). microholdem was used as an opponent and a cross-check only; nothing of it is in Hero.

Wiring (`PushFold`): first-in shoves take the top `p_push[k][S]` by the solve's order, stretched by the callers'
steal dials, then the ICM gate with the solve's P(nobody calls) (scaled by the callers' observed looseness) and
equity when called; re-shoves read the re-shove family with the opener's range from its seat (`bb_open_prior`)
and PFR and m = live players behind; `nash_push_freq(k, S)` feeds the shove-call read below. `use_multiway` /
`use_reshove_table` switch it off; `tighten_per_player` is the fallback when the table is missing or was solved from
another matrix (and for 3/4-card label variants).

### Exploit-resistance levers (commits ce5a137, c5cb3db, 745bf82)

Every lever is a Config key; what is on by default is marked.
- **(a) Shove calls against the shover's observed range** (on: `preflop.shove_range_model`, `shove_ctx_model`).
  `ranges.RangeEquity` gives each class's all-in equity against the top x of hands (heads-up matrix, card removal,
  18-point grid; 47 ms once per table set). The profiler counts each seat's preflop shoves by its own depth bucket
  (<= 12, <= 25, <= 50, > 50 bb) per *opportunity*: first-in shoves per first-in spot and re-shoves per "facing one
  open" spot (`shove_counts_ctx`), plus a per-hand count for 4-bet and later shoves. A first-in shove is read as the
  Nash frequency for the shover's seat and depth (multiway table) times its observed first-in rate over the prior; a
  re-shove as the solved re-shove frequency against the opener's range (Hero's own open fraction when Hero opened)
  times its observed re-shove rate over the prior; without a solved base (deep), the smoothed rate is the width.
  Calls go through the ICM gate against that range (`range_call_ok`; with a caller already in, the normalised
  product of pairwise equities). The deep path keeps `patience_deep`. Per opportunity matters: rival 2 re-shoves
  13-25 bb over opens far more often than its per-hand rate shows (Hero faced 207 such re-shoves in 96 top2 tables,
  called 8% with the per-hand read and won 11 of 17; with the per-opportunity read it calls 26% and won 21 of 44,
  and calls 51% of rival 2's <= 12 bb re-shoves, winning 19 of 34). Against rival 1's rare deep shoves the read
  tightens toward QQ+/AK (`tests/test_strategy_exploit.py` pins both directions).
- **(b) Big-blind defence by pot odds** (`preflop.bb_defend`, off): call when equity against the opener's estimated
  range (seat prior x PFR) times `bb_realize` beats the pot odds, 3-bet the value slice plus `bb_3bet_bluffs`
  (A5s, A4s). Swept and not kept (below).
- **(c) Late-street call-downs** (on: `postflop.late_calldown_cap` 1.0; off: `tight_aggro_margin`). The unknown-
  archetype call-down dial is 1.4 - 0.8 x aggression, i.e. above 1 (lighter calls) against passive bettors; rival 1
  reads as postflop aggression 0.24-0.29, and its late bets are value. Capping the dial at 1 on the turn and river
  (maniacs and random seats keep theirs) is the lever that helped against rival 1 copies. The tight-aggressive margin
  (VPIP < 0.22 and aggression > 0.40) was neutral: neither rival is low-VPIP (rival 1 0.26, rival 2 0.25).
- **(d) Early-game risk-of-ruin margin** (`ror_margin`, `ror_from_bb` / `ror_full_bb` / `ror_hands`, off): extra
  equity needed for any stack-off (half the stack or more, preflop or postflop) while deep and early, carried on
  `Spot.ror`. Swept 0.05 / 0.10: within noise, sign flipping between fields.
- **(e) Steals from the folder read** (`preflop.folder_steal_mult`, `folder_ftr` / `folder_min_n`, off): steals widen
  when every player to act folded >= 75% of the >= 4 raises it faced. 1.4 was -0.02 / -0.05.
- Two more built on the way, both off: a **hand-cap-aware value curve** (`cap_vol_bb`: survivors are ranked by chips
  at hand 200, so near the cap my points blend Malmuth-Harville's s_j / (s_me + s_j) with Phi((s_j - s_me) / sigma)
  over the variance still to come, with samples on both sides of every rank step; not swept after rival 1's own
  cap mode measured as worth nothing to it: 5.698 with, 5.759 without, 60 seeds) and **exploitative first-in shoves**
  (`pushfold.exploit_push`: shove any hand whose ICM EV beats folding when each caller calls the top c_j, c_j = its
  seat type's solved call frequency times its calls over a solved caller's calls in the shoves it faced;
  `profiler.call_looseness` reads rival 2 0.94, rival 1 0.5-0.8, tag 0.4-0.5, montecarlo 5.2). With neutral reads it
  reproduces the solved set (150-167 of 169 classes agree); with reads it lost 0.05-0.10 on top and top2.

### Where the points go (diagnostics that drove the second half)

The first screen (every lever above, 160 seeds, realistic and top) found nothing outside +-0.10, so the second half
looked for where the points are lost rather than for more levers. Scratch scripts (not committed) on duplicate deals:
- **Who reaches the final two** (200 realistic tables): rival 1 is in the final pair in ~52% of tables, Hero in ~28%;
  when the two meet in the final, rival 1 wins 25 to Hero's 16 (realistic) and Hero 27 to rival 1's 24 (top). About
  half of all tables end at the 200-hand cap with two or three survivors. Hero's deficit is getting there.
- **Chip flow per table** (realistic, 160 tables, chips): rival 1 nets +2,802 in hands that end preflop without a
  showdown, Hero +898; postflop without showdown rival 1 -775, Hero -1,340; at showdown Hero +1,699, rival 1 +1,465.
  By level Hero is ahead at level 1 (+15.3 bb vs +10.7) and behind from level 4 on.
- **Preflop uncontested, levels 4-8** (hands 75-200, 336 tables): rival 1 raises and takes it down 13.0 times per table
  (+17.2 bb), Hero 9.2 (+12.2 bb); Hero gives up more blinds (-10.2 vs -8.2 bb); net rival 1 +12.1 bb, Hero +3.8.
  On top2, rival 2 takes 11.1 raised pots per table (+20.9 bb) to Hero's 7.3 (+11.5); Hero's lost opens (-5.2 bb) are
  mostly folds to rival 2's re-shoves, which is what lever (a)'s per-opportunity read was built for.
- **What the room calls** (Hero's profiler, call-vs-shove against a solved caller in the same spots): tags and the
  short-stack bot call 0.4-0.5x Nash, rival 1 0.5-0.8x, rival 2 0.94x, the Monte Carlo bots 1.6-5x. Per-hand preflop
  shove rates at <= 12 bb are 0.05-0.16 for every bot (the 0.20 prior first used was too high and is not what the
  per-opportunity read uses).

### Results (400 duplicate seeds x 8 rotations, seed 7, strict, one sweep from a clean worktree of 745bf82)

"before" is the same code with every lever of this pass off (`pushfold.use_multiway`, `preflop.shove_range_model`,
`shove_ctx_model` false, `postflop.late_calldown_cap` 9): the tuner's bot plus exact ICM. "after" is the shipped
default (d917c45: solved tables, per-hand shove read, call-down cap; the per-opportunity read off). Paired deltas
are means of per-seed differences. Uniform is 4.50. The same sweep ran the per-opportunity read on (745bf82's
default) as a third column; it is quoted where it differs.

| target | field | before | after | paired after - before | met? |
|---|---|---|---|---|---|
| T1 | realistic: Hero / rival1 | 5.513 / 5.613 (paired -0.101) | 5.564 +- 0.068 / 5.701 +- 0.075 | Hero +0.051 +- 0.068; Hero - rival1 **-0.137 +- 0.115** | no |
| T1 | top: Hero / rival1 / rival2 | 4.479 / 4.775 / 5.000 | 4.620 +- 0.072 / 4.752 / 4.991 | Hero **+0.141 +- 0.070**; Hero - rival1 **-0.131 +- 0.102** (was -0.295) | no |
| T2 | Hero + 7 rival1 | 4.310 | 4.430 +- 0.065 | +0.119 +- 0.056 | no (< 4.50) |
| T2 | rival1 + 7 Heroes (rival1) | 4.664 | **4.496 +- 0.082** | rival1 -0.168 +- 0.087 | yes (<= 4.60) |
| T3 | base (hero,tag,nit,naive,station,maniac,random,allin) | 6.835 | 6.812 +- 0.045 | -0.022 +- 0.025 | yes (within CI) |
| T3 | strong | 5.075 | 5.150 +- 0.073 | +0.075 +- 0.067 | yes |
| T6 | MicroAgent + 7 Heroes (micro; microholdem venv, from the d917c45 worktree) | 4.646 +- 0.068 | **4.453 +- 0.065** | micro -0.194 +- 0.073 | yes (<= 4.60) |
| T7 | top2: Hero - rival2 | -0.642 | **-0.557 +- 0.098** (Hero 4.435, rival2 4.992) | Hero +0.070 +- 0.077 | no (needs >= -0.10) |
| T8 | rival2 + 7 Heroes (rival2) | 5.231 | 5.105 +- 0.075 (4.967 with the per-opportunity read) | rival2 -0.127 +- 0.085 | no (<= 4.70) |
| - | Hero + 7 rival2 | 3.542 | 3.514 +- 0.065 | -0.028 +- 0.080 | - |

T4: `act()` min-of-3 mean 17.4 us, p99 29.7 us (the tuning pass: 14.1 / 21.4; the range read and the seat-order
walk cost ~3 us); hand_end p99 49 us, new_table p99 58 us on the default payouts (top-heavy: 487 / 476 us). safe_err
0 and exc 0 in every cell above. T5 (`tools/variant_matrix.py --tables 300 --seed 7 --field realistic --workers 6`, d917c45 worktree, 183 s):
**READY 22, PLAYS 1, WEAK 0, BROKEN 0**, the same count as the variant pass. two_boards rose to READY (second, 5.32);
hi_lo is the PLAYS (third at 5.42 +- 0.23 behind rival1 5.46 and tag 5.44, all inside each other's intervals).
Hero is first on 15 of 23 entries (was 11); exc and ill are 0 everywhere; p99 48-78 us.

**The per-opportunity read, on vs off (same sweep):** top -0.112 +- 0.067, realistic -0.051, top2 -0.006, base and
strong +-0.01, Hero + 7 rival1 -0.006; rival1 + 7 Heroes -0.040 and rival2 + 7 Heroes -0.137 +- 0.081 for the rival.
It does what it was built for (rival 2's re-shoves) and costs the mixed rooms more than it gains there, so it ships
off; turn it on (`preflop.shove_ctx_model`) for a room of frequent re-shovers.

**Where that leaves Hero.** Hero closed half the gap to rival 1 on `top` (paired -0.295 -> -0.131) and pushed both
rivals down in the Hero rooms (rival1 +0.16 -> 0.00 over uniform, rival2 +0.73 -> +0.61, MicroAgent +0.15 -> -0.05),
but T1, T2's first half, T7 and T8 are not met. Rival 2 is the strongest bot here by a wide margin: it out-scores
rival 1 on top and top2, and in a room of seven rival 2s Hero scores 3.51. The diagnostics above say where its
edge is: the volume of uncontested preflop pots it takes in the 10-25 bb phase (wide opens scaled by the blinds'
fold-to-aggression, light 3-bets from the blinds, frequent re-shoves) and Monte Carlo postflop equity against
VPIP-shaped ranges. None of the gates added here change Hero's own preflop volume; that is the next lever, not
another threshold. Per HANDOFF "After those land" item 2, the agreed fallback (the rival's decision core behind
Hero's adapter) is now on the table for the owner; it was not taken here.

### Screens and what did not help

`tools/sweep.py`, duplicate deals, seed 7, strict, paired deltas against each screen's base (+- is the 95% interval of
the paired delta; at 160 seeds it is ~0.10, at 240 ~0.08-0.09). The box ran 7 sweep workers plus 2-4 processes of
other agents throughout, so rival 2 (the slowest bot, 5-8x rival 1 per decision) times out more here than on a
quiet host; that handicaps it equally in every setting of a screen.

| lever (screen) | realistic | top | top2 | Hero + 7 rival1 | rival1 among 7 Heroes (rival1 pts) | kept? |
|---|---|---|---|---|---|---|
| shove range model, per hand (S1, 160) | -0.012 +- 0.106 | +0.001 +- 0.102 | | | | yes (became per opportunity) |
| ... range width x1.0 / x2.5 (S1) | +0.048 / +0.020 | -0.051 / -0.096 | | | | no |
| BB defence, realise 0.85 (S1) | -0.144 +- 0.113 | -0.155 +- 0.119 | | | | **no** |
| BB defence, realise 0.75 (S1) | -0.000 | -0.048 | | | | no |
| tight-aggressive margin 0.06 (S1) | +0.015 | -0.028 | | | | no |
| risk-of-ruin margin 0.05 / 0.10 (S1) | +0.075 / -0.037 | -0.109 / +0.050 | | | | no (noise) |
| ... 0.10 (S2, 160) | +0.080 | +0.068 | | +0.036 | 4.730 | no (noise) |
| folder steal x1.4 (S1) | -0.017 | -0.052 | | | | no |
| profiler_dead_after 10 (S1) | -0.049 | -0.010 | | | | no |
| solved table off (S2) | +0.077 | +0.033 | | -0.016 | 4.802 (+0.04) | table kept: neutral on fields, helps mirrors |
| re-shove table off (S2) | +0.074 | +0.035 | | -0.019 | 4.753 | kept |
| threshold_bb 12 / 15 / 18 / 20 (S2) | -0.001 / -0.054 / -0.037 / -0.058 | +0.035 / -0.025 / +0.099 / +0.042 | | +0.024 / +0.060 / +0.089 / +0.148 | 4.685 / 4.598 / 4.601 / 4.711 | no: 10 stays |
| late call-down cap 1.0 (S2 / S3) | +0.133 / -0.018 | +0.038 / -0.012 | +0.005 (S3) | +0.130 / +0.133 | 4.598 / 4.548 | **yes** |
| exploit push, crude normalisation (S3, 240) | -0.029 | -0.100 +- 0.072 | -0.100 | -0.006 | 4.725 | no |
| ... with threshold 15 / 20 (S3) | -0.159 / -0.124 | +0.005 / -0.008 | +0.071 / +0.022 | +0.063 / +0.113 | 4.613 / 4.655 | no |
| exploit + cap + threshold 15 (S3) | -0.076 | +0.021 | +0.035 | +0.195 +- 0.085 | 4.496 | no: realistic -0.08 |
| shove priors recalibrated (S4, 240, base = cap on) | +0.002 | +0.005 | -0.022 | -0.041 | 4.605 | no |
| exploit push, expected-call normalisation (S4) | -0.009 | -0.051 | -0.046 | +0.019 | 4.587 | no |
| ... with threshold 15 / 12 and priors (S4) | -0.093 / -0.091 | -0.009 / +0.011 | +0.005 / -0.034 | +0.050 / +0.023 | 4.501 / 4.582 | no |

Readings. (1) Nothing in this list is worth more than ~0.1 on the realistic or top fields; the mirrors move more
because there the same lever acts at seven seats. (2) Shoving more (higher threshold, exploitative shoves) helps
against rival copies and costs the realistic field, where two Monte Carlo bots call shoves at 1.6-5x Nash. (3) The
rivals' edge is the volume of uncontested preflop pots they take in the 10-25 bb phase, which no single gate fixes;
what moved it was reading re-shoves per opportunity (calling rival 2's re-shoves at the right width) and the
call-down cap (not paying off rival 1's value bets). (4) The hand cap is not an edge here: rival 1's cap mode is
worth nothing to it.

## Drill 5 follow-ups (2026-11-01, builder: drill 5 follow-ups)

- **Track B step 3b pushes on chip EV, not the ICM curve (spec v2.1).** The v2 rule (p·V(S + blinds) + (1 − p)·
  (e·V(2S + blinds) + (1 − e)·V(0)) > V(S) + 0.1 bb, c = 0.12 per seat, e vs the top 12%) failed its own sanity
  check: at 8 equal 10 bb stacks under 10/7/5/4/3/2/1/0, 22 on the button is 3.85 points against 4.02 for folding
  and the rule pushes 5% of hands from the button. Exact ICM in place of the 5-point curve gives 3.92 against 4.03,
  so the static ICM model is the cause, not the interpolation; an orbit of blinds charged to the fold flips it to
  all-or-nothing (100% button, 5% UTG). Replaced by p·B + (1 − p)·(e·(2S + B) − S) > 0 in bb with c = 0.2 per live
  opponent (0.3 maniac, 0.1 nit, 0 dead) and e vs the top 20%: on `tables/hu_matrix.json` that is 38% from the button
  at 10 bb (solved chart 32%) with 22 in at +0.74 bb, 12% from UTG at 12 bb (chart 9%) with 72o at −3.7 bb, and
  monotone in S and opponents. It is wider than the chart at 6–8 bb from the last two seats and pushes any two from
  the small blind, because a fixed caller does not widen against a wide shover. ICM stays on calls and re-shoves.
  Sim check with drill 5's own bot (standard ranks, realistic field, 500 tables, seed 11, strict, loaded box): step 3
  percentiles 4.25 ± 0.22, v2 ICM rule forced on 4.44, chip EV c 0.2 4.50, c 0.25 4.38; all inside each other's
  intervals, so the change is for correctness of the sanity checks, not a measured gain.
- **No-history kits (spec v2.1).** The profiler diffs each seat's active flag and committed chips between our
  observations (against the previous street's last when the street changed) under kit A's one-per-hand limits; the
  exploits are unchanged and seats that never flag get the charts. This is what drill 5's agent built for kit B.
- **`python -m hyperion.sim --variant-seed N`** sets a seeded variant's permutation; without it the table seed
  still does, as before.
- **tag, nit and pushfold remap `rank_order`** through `bestiary.strength_view`; the other archetypes stay naive.
  permuted_ranks re-measured (variant_matrix, realistic, 300 tables, seed 7): Hero 5.95 ± 0.23, first, READY, next
  rival1 5.52 (was 6.34 / 5.66); tag 4.96 → 5.44 and pushfold 4.74 → 5.34 in that field.
- CONTRACTS.md unchanged: nothing it covers moved.

## Drill 6: adapters pass action history (2026-11-01, builder: drill 6)

- **Every reference adapter now gives Hero a history.** Drill 6 played its shipped kit-A Agent in the real sim
  (300 tables, realistic, toss_or_holdem): 3.39 against pinned Hero's 5.90. The cause was `obs.history` being
  empty behind every reference adapter. Hero reads who raised (`Spot.n_raises`, `Spot.raiser`, the opener and
  shove reads) only from history; stripped of it, Hero scores 3.21 on standard hold'em (5.50 with it, 100
  tables).
  - `KitAAdapter` now parses kit A's `action_log`.
  - `make_observation` rebuilds the current street's raises from the bets when a kit gives none: 5.20, which
    loses the earlier streets and the re-raise count.
  - With this, the shipped Agent scores 5.81 measure and 5.93 strict.
- **Still open, for the strategy owner:** `Spot` should infer at least one raise from `max(bets)` above the
  street's base when history is empty.
- **Still open, for drills:** a `shipped_sim.py` that gates the packaged entry rather than the bestiary Hero.
  Prompt 04 now prints `obs.history` after a raise until it exists.
- Report and prompt edits: `docs/drills/prompt-drill-6.md`.

## Rival 3 in the pool (2026-11-01)

**What landed** (`91abdb8` archive, `2fd22df` report, `2fc1b90` adapter, fields and tests). Red-team drill 3's bot
(`docs/drills/redteam/redteam-3.md`: an exploitation-first team, built blind in 35 minutes against the same brief and
kit as rivals 1 and 2, with no access to this repo or to either rival; 724 lines, stdlib only) is in the simulator as
`rival3`. **It is the holdout: Hero is never tuned against `rival3` or on the `holdout` field.** They exist to show
whether a gain measured against rivals 1 and 2 generalises, so numbers against them are reported, never optimised.
No leak analysis of Hero against rival 3 is done either: once a holdout is studied for leaks it stops being a
holdout. `hyperion/sim/rivals/rival3.py` is the frozen file (md5 `4b36e812...`) below a six-line origin header.
`bestiary.Rival3Bot` is `RivalBot` with `MODULE = "rival3"` and one difference: `hand_end` passes the hand's history
in the kit's `(seat, (kind, amount))` shape, as the rival's own engine did. Rival 3 replays it there to count the
actions that came after its last decision. Rivals 1 and 2 read only `hand_no` there and are unchanged. On `holdout`,
same seeds, that history is worth +0.22 ± 0.11 to rival 3 (5.88 without it); the rival measured 0.33-0.44 in its own
engine. Fields: `top3` = hero, rival1, rival2, rival3, pushfold, tag, hero_tight, loose_aggro; `holdout` =
`realistic` with rival 3 in rival 1's seat. No other field changed. `tests/test_sim_rival3.py` has 8 tests:
- 300 hands of eight copies, with its exception swallowing unwrapped;
- the strict timeout rate (< 1%; skips if a fixed 30-us loop overruns too);
- the adapter round trip, including the hand_end history;
- push/fold sanity;
- run-to-run reproducibility;
- the field seats, and 12 strict tables per field.

**A payout mismatch every rival shares.** Our default `Rules` pay 8..1 (linear, uniform 4.50). Rivals 1, 2 and 3
hard-code the brief's 10/7/5/4/3/2/1/0 (uniform 4.00). Rival 3's closed-form ICM is exact for the brief's table, so
in our engine it prices every all-in with a more top-heavy table than the one that scores it. It was measured as
built.

**Measurements.** 1,600 duplicate tables each (`--tables 200 --rotate --seed 7 --mode strict`) at HEAD `2fc1b90`, run
from a clean worktree, so Hero is the committed `hyperion/strategy` without the aggression pass's uncommitted edits.
Two ran at a time while the aggression pass's sweeps ran, at load average 8.5-15.8 on 8 cores. Uniform is 4.50.
Paired deltas are means of per-seed differences, with 95% intervals. Script: `rival3_measure/measure3.py` in the
session scratchpad (run_tournament plus paired deltas); raw output and per-seed samples are beside it.

`--field holdout`:
```
bot                      n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill safe_err safe_over  p50us  p99us  maxus  1st_us
rival3                 200  6.105 0.101    50    7    7    8   11    8    5    3   47.7  1692     0     0        0         0     30    323  43919   29799
hero                   200  5.369 0.096    21   14   15   16   14    8    7    4   69.6  1189     0     0        0      1475     22    197  31883   10895
tag                    200  5.213 0.084     4   24   23   18   11    8    6    5   82.2   193     0     0        0         0      4     27  29997    9541
pushfold               200  5.091 0.091     7   23   18   19   10    9    7    7   80.4   235     0     0        0         0      5     36  28450    4185
loose_aggro            200  4.738 0.106    16   16   12   10   11   11   11   12   74.6   177     0     0        0         0      3     20  27152    5760
timeout_then_recover   200  3.173 0.091     0    7   13   10    9   11   20   30   96.8 46383     0     0        0         0      3   6814  31542    6172
montecarlo             200  3.163 0.067     0    2    5   11   20   26   21   15   98.9 50593     0     0        0         0      2   9291  50357    4041
montecarlo30           200  3.148 0.093     3    6    6    8   13   17   22   24   93.9 19360     0     0        0         0      2   8060  35350    4278
```
Paired: hero - rival3 **-0.736 ± 0.155**, rival3 - tag +0.892 ± 0.141, hero - tag +0.157 ± 0.132.

`--field top3`:
```
bot             n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill safe_err safe_over  p50us  p99us  maxus  1st_us
rival2        200  5.032 0.098    20   16   11   11   11   11   11    8   69.8  7924     0     0        0         0    131   4316  43502   27974
rival3        200  4.925 0.107    24   11    9   11   13   10   11   11   70.2  1697     0     0        0         0     31    308  31201   12165
rival1        200  4.821 0.109    24   14    8    8    7   12   14   12   68.2  1389     0     0        0         0     24    215  34810   16389
tag           200  4.543 0.085     2   15   18   19   15   12    9    9   87.6   235     0     0        0         0      4     28  16494    4089
hero_tight    200  4.477 0.085     6   13   14   14   17   16   13    7   85.3  1055     0     0        0      1224     20    164  28266    9955
hero          200  4.446 0.102    13   10   12   12   14   15   13   10   80.9  1259     0     0        0      1434     21    178  39318    4193
pushfold      200  4.207 0.097     2   13   17   15   13   13   13   13   88.4   276     0     0        0         0      5     31  22330    8037
loose_aggro   200  3.548 0.117     8    8   10    9    9   10   17   28   85.6   171     0     0        0         0      3     21  10457    8051
```
Paired: hero - rival3 **-0.479 ± 0.159**, hero - rival1 -0.374 ± 0.177, hero - rival2 -0.585 ± 0.157. The rivals head
to head: rival3 - rival1 **+0.105 ± 0.169**, rival3 - rival2 **-0.106 ± 0.153**, rival1 - rival2 -0.211 ± 0.142.

Mirrors (uniform 4.50):
- rival3 + 7 hero: rival3 **4.998 ± 0.106** (23% firsts); paired rival3 - hero +0.569 ± 0.121.
- hero + 7 rival3: hero **4.112 ± 0.108** (6% firsts, 28% seventh or eighth, busts in 90% of seats); paired
  hero - rival3 -0.443 ± 0.123.

The rival 2 entry measured these mirrors for rivals 1 and 2 against Hero at `fd8a3fa`, before the deep pass (one
rival among seven Heroes: rival 2 +0.69 over uniform, rival 1 +0.28). They were not re-measured here, so they do not
rank rival 3 against the current Hero.

Context, on the same seeds and HEAD:
- `--field realistic` (rival 1 in that seat): rival1 5.661, hero 5.524, hero - rival1 -0.137 ± 0.162.
- `--field holdout --mode measure`: rival3 5.931 ± 0.100, hero 5.569 ± 0.093, hero - rival3 -0.362 ± 0.141. Nothing
  is folded for time in this mode, which also stops the Monte Carlo bots and timeout_then_recover folding when they
  overrun.

**Latency and timeouts in our engine.** Through the adapter, rival 3 decides in p50 29-32 us (21 us in the field of
seven copies), p99 150-330 us. It had 0 exceptions and 0 illegal actions in 3.87 million decisions, and no bot had
any in these runs. Over 1 ms (strict: counted, and folded) it ran 0.19-0.21% at load ~8.5 (the variant runs) and
0.51-0.68% at load 10-16. At the same moments Hero ran 0.14-0.47%, rival1 0.53%, rival2 3.07% (top3) and tag
0.03-0.11%. The rate follows the host. In the gate re-run it matched a fixed 30-us loop (report §4).

**Under catalogue twists.** For information only: rival 3 handles none, and that is expected. `holdout` field, same
settings:

| variant | rival3 | hero | hero - rival3 | note |
|---|---|---|---|---|
| none | 6.105 ± 0.101 | 5.369 ± 0.096 | -0.736 ± 0.155 | |
| top_heavy (50/25/12/6/3/2/1/1, uniform 12.5) | 27.70 ± 1.08 | 18.09 ± 0.87 | -9.61 ± 1.73 | first in 49% of tables; its ICM is for the wrong table here too |
| permuted_ranks (permutation from seed 7) | 5.753 ± 0.112 | 6.055 ± 0.093 | +0.302 ± 0.171 | it does not remap ranks and still finishes second |
| antes_from_level_3 | 6.172 ± 0.098 | 5.457 ± 0.101 | -0.716 ± 0.162 | antes change nothing for it |

**What it says.**
1. *Hero's level with the top rival on `realistic` does not generalise.* On `holdout` rival 3 is first by a wide
   margin: 6.11, first at half the tables, 0.74 ahead of Hero paired. On the same seeds rival 1 in that seat is 0.14
   ahead of Hero.
2. *On `top3` the three rivals are level within noise* (5.03, 4.93, 4.82; each pair inside its interval). Hero is
   sixth of eight at 4.45, 0.37-0.59 behind each rival. Rival 3 beats Hero in both mirrors.
3. *Its holdout edge is largest when the engine folds bots that overrun:* -0.74 in strict mode, -0.36 in measure
   mode. In strict mode the Monte Carlo bots' and timeout_then_recover's overruns become folds.
   - At table end, rival 3 reads those three seats with fold-to-raise 0.63-0.70 and fold-to-bet 0.38-0.67, and
     never labels them dead (`rival3_measure/labels.py`, 100 tables).
   - Its labels are coarse. It reads tag as a maniac in 42% of tables, because c-bets count as unprompted bets.
   - The likeliest source of the edge, from its code and these reads, is the measured fold rates, not the labels.
     Its steal rule raises any hand up to the 85th percentile when the steal's chip EV is positive against the
     product of the seats' fold probabilities. With fold rates like these, that opens wide from late position.
   - This is an inference, not a trace.
4. *Its play does not depend on the twist.* It keeps its lead through antes, and it stays second under permuted
   ranks with its hand values scrambled. That suggests its edge on this field comes more from reading the
   opponents than from its card values.

**Not done here.**
- No Hero tuning, and none against rival 3, ever.
- No rival tuning.
- No bust trace or leak analysis of Hero against rival 3, on purpose.
- `realistic`, `strong`, `top`, `top2` and `chaos` are unchanged.
- No quiet-host repeat: the aggression pass's sweeps kept the box at load 6-16 throughout, so the strict tables
  overstate every bot's timeouts against a dedicated host.

## Gate the packaged bot (2026-11-01, builder: gate pass)

**Why.** Drill 6's upload played 2.5 points a table below Hero, and nothing we ran could see it. Every gate
(prompt 04's sim, prompt 05, the windows) played the bestiary Hero, which the engine feeds its full history.
The uploaded bot sees only what its adapter passes, and none of the reference adapters passed history. From
now on we gate what we upload.

**What landed** (`c4ad5e5`, `d1aee18`, `b5463e4`, `56f9485`, `ba45884`):
- `tools/gate.py ZIP --kit a|b|c|d|seat.py`, with `tools/gate_host.py` as its child. It unpacks the zip and
  imports it in a fresh `python -I -B` per table, the way the organisers would:
  - the package directory first on sys.path, the kit's `kit.py` importable as `kit`;
  - a scratch working directory, and no `PYTHON*` or `HYPERION_*` variables.
- Each engine Observation goes to the kit's state through `hyperion.drills.adapter.dealer_state` (the inverse
  of `make_observation`, history and toss discards included) and the kit's own constructor, and the reply
  comes back through the kit's own parser.
- How each kit is timed:
  - kits A and B run in process; the host times the bot call alone against 1 ms;
  - kits C and D run their entry as a subprocess on the kit's line or socket protocol, charged to its pooled
    clock (1 ms x max_hands x 3), as their runners do;
  - a seat file (class `Seat`, copied from `gate_host.KitA`) covers tonight's in-process kit, with
    `--kit-module` pointing at the organisers' `kit.py`.
- An exception, an illegal or unreadable reply, or a late one is a check or fold, as the rules score it.
- Each table seed is played twice: the package in the field's `hero` seat, then the baseline in that seat,
  with every other bot and the deal identical. The baseline is one of:
  - in-sim Hero (`--baseline sim`, with `--hero-config`, `cheap` for the Stage 2 package);
  - the package's own Hero behind no adapter (`--baseline package`), for packages built from older code. It
    also reads the package's tables, so it cannot see a missing variant set.
- FAIL when the package trails by more than the paired 95% interval, raises, sends an illegal action, never
  imports, or times out on more than 0.3% of decisions (a warning under the playbook's load clause).
- `GateTable` subclasses the engine's `Table` (`_ask`, `_ask_variant`, `_needs_betting`); no engine edit.
- Conformance, with both rules hard:
  - `history_raise`: a bet above the street's base needs a RAISE to that total in obs.history;
  - `history_prefix`: an adapter declaring `history_source = "log"` must never drop a raise later in the
    hand. Kits B, C and D's reference adapters declare `"bets"`. The template passes the log in TODO 7b and
    documents the bets path.
- `pack.py` vendors `tables/variants/<extras.variant>/` from the rules JSON on its own; `--tables-dir` is an
  override.
- `latency.py` deals the rules' hole-card count, board and deck, and takes `--variant`. With toss_or_holdem
  Hero shows 0 SafeBot errors, where drill 6 had 468.

**Proof.** 100 strict tables, realistic field, `--variant toss_or_holdem`, seed 11:

| package | paired delta vs in-sim Hero | verdict |
|---|---|---|
| drill 6's upload (`787c70a6`, Hero at 857dbe9, adapter passed no history) | -2.456 ± 0.761 (3.58 vs 6.03) | FAIL |
| the same `submission/` repacked over drill 6's history-fixed tree (`70d34824`) | -0.221 ± 0.397 (5.72 vs 5.94) | PASS |

`tests/test_gate.py` repeats this on this tree, with Hero's bets inference switched off in both packages,
because drill 6's Hero had none. It runs 32 tables in measure mode, with both Heroes seeded and the baseline
shared. It is deterministic per tree. At 48 tables the same set-up measured -1.71 ± 0.66 dropping history,
and +0.16 ± 0.43 fixed.

**Earlier drills** (100 strict tables, `--baseline package`, which isolates the kit path from code drift
since Oct 31):

| drill | kit, twist | package | own Hero, no adapter | paired delta | gate |
|---|---|---|---|---|---|
| 1 | B, permuted ranks (payouts 8..1) | 3.561 ± 0.435 | 4.782 ± 0.426 | -1.221 ± 0.531 | FAIL |
| 2 | C, top-heavy 50/25/... and fast schedule | 12.650 ± 3.533 | 18.977 ± 4.081 | -6.328 ± 4.812 | FAIL |
| 4 | D, short deck | 2.940 ± 0.536 | 4.671 ± 0.642 | -1.731 ± 0.733 | FAIL |

All three shipped drill 6's flaw: kits with no action log, adapters that rebuilt nothing, and a Hero that
inferred nothing. There were no exceptions, illegal actions or timeouts. Kit D's one raise after a short all-in
is a rule mismatch, played as a call. The zips and hashes are in the drill 6 report's follow-up section.

**What else it showed.**
- *Resolution.* The paired interval is ±0.4 to ±0.8 points at 100 tables (wider when the package busts
  often) and about ±0.9 at 30. It catches drill-6-sized losses, not 0.2-point ones. The two Heroes drift apart even when the adapter loses nothing: postflop RNG, and kit A's
  `hand_over` carries no showdown, so the two profilers diverge. That drift is real and the gate counts it.
- *Today's Hero heals most of drill 6's flaw by itself.* Since `c38259e` it infers raises from the bets.
  A fresh history-dropping package from this tree scored +0.03 ± 0.51 at 40 tables and passed. The gate is
  the check that does not depend on Hero's inference.
- *Kit D charges the round-start packet to its pooled clock.* A kit D entry that builds Hero's tables on the
  first `G` packet spends about 1 s of the 0.6 s clock, and every later action folds. Drill 4's entry warmed
  at import, which is the fix.
- *Cost.* 100 tables take about 2 minutes on this loaded box (0.3 s of that per table is the fresh import).
  The suite gains about 85 s, 75 s of it the proof test.

**Limits.**
- Seat files cover in-process kits only. A subprocess kit unlike C or D cannot be gated.
- Kits B, C and D cannot carry variant decisions; the dealer's default plays them and the report counts them.
- Kit D refuses a straddle, and any variant that changes cards mid-hand.
- Kit D's legal set ignores our engine's short-all-in no-reopen rule. A raise there is reported as a rule
  mismatch and played as a call.

## Mid-phase aggression pass (2026-11-01, builder: aggression pass)

Scope: `hyperion/strategy/*`, `tools/sweep.py`, the strategy and sweep tests. Brief: rival 1 and rival 2 out-take Hero
in the 10-25 bb phase (deep pass); measure where before coding, build levers as Config keys off by default, screen
them, ship only by the rule (paired delta >= 0 on realistic and on top, not below -0.03 on base or strong, at least
one field outside noise). Running log with every table: `docs/drills/aggression-pass-log.md`.

### What the measurement said (step 1)

A per-phase action-frequency table (every seat wrapped, every preflop and flop decision classified; top2 and
realistic, 120 seeds x 8 each) overturned half the diagnosis. Hero does not open too little: its first-in open
rate is the widest of the three bots at every position in both phases (levels 4-8 on top2: 20.3 opens per seat,
rival 1 18.6, rival 2 13.2). What it lacked, in order of size (levels 4-8, bb per seat): re-shoves over single opens at
10-25 bb (rival 2 2.58 per seat for +5.1 bb, Hero 0.18 for +0.5; from the blinds 21% of opens faced against Hero's
5%); heads-up postflop where Hero called preflop (it folds 71-78% to a c-bet, the rivals 44-54%, and loses -6.9 /
-1.9 bb per seat in non-showdown pots at levels 1-3 / 4-8 against rival 2's +0.4 / -0.2); and at 10-15 bb Hero
raises 50% of first-in spots to 2.25 bb and shoves none where both rivals shove ~20%, then folds 77% of the
re-shoves it faces. Big-blind flats were equal (19% vs 18%); the defence gap was all re-raises.

### What shipped (f349380)

- `preflop.reshove_mid_bb` = 25 (lever c, 0b6289b): facing one open with no callers above push/fold depth, shove
  the solved re-shove set (the multiway table's 4-25 bb family over a 2.3 bb open) when push/fold's ICM gate passes.
  It raises Hero's 10-25 bb re-shoves from 0.18 to ~0.9 per seat in levels 4-8 (blinds 5% -> 11% of opens faced,
  big-blind 3-bets 7% -> 16%), each worth about +1.8 bb.
- `postflop.vs_cbet_margin` = 0.05 (lever e, 1f56fa2): facing the preflop raiser's small flop c-bet heads-up (the
  first bet of the street, at most 0.75 pot), the call margin is 0.05 instead of 0.15; middle pair stopped folding
  to a third-pot bet.
- Hero infers the betting state from the bets when the history cannot explain them (coordinator add-on, c38259e):
  realistic with Hero's history stripped 5.505 against 5.756 with it (drill 6: 3.21); nothing changes with history.
- Built and left off (all Config keys with tests): the observed-opener width and the exploitative re-shove price
  for the re-shove table (`pushfold.reshove_w_observed`, `reshove_exploit`), the first-in shove zone
  (`pushfold.fi_threshold_bb`, `fi_late_threshold_bb`, `fi_rest_open`), the per-seat re-shove read
  (`preflop.shove_ctx_auto`), c-bet bluffs by fold-to-c-bet (`postflop.cbet_ftc_read`), and opens tightened against
  a re-shove threat behind (`preflop.reshove_threat`). New profiler reads: first-in opens per opportunity by
  position class, an opener's fold to a re-raise, c-bets and folds to them. `tools/sweep.py`: several rivals in
  the report and the lone bot's delta in a mirror, per-field Rules, and jobs queued with every setting side by side.

### Results (400 duplicate seeds x 8 rotations, seed 7, strict, one sweep from a clean worktree of f349380)

"before" = d917c45 behaviour (the shipped keys off; bit-identical to d917c45 on a 7,590-hand check), "after" = the
shipped defaults; panic on as shipped. Uniform is 4.50. Gaps are paired Hero-minus-rival means.

| target | requirement | before (d917c45) | after (f349380) | paired after - before | met? |
|---|---|---|---|---|---|
| T1 | Hero - rival1 >= 0, realistic | -0.120 ± 0.115 | **-0.031 ± 0.109** (Hero 5.595, rival1 5.626) | Hero +0.051 ± 0.061; gap +0.089 | no (inside noise of 0) |
| T1 | Hero - rival1 >= 0, top | -0.203 ± 0.107 | **-0.019 ± 0.106** (Hero 4.639, rival1 4.659) | Hero **+0.082 ± 0.068**; gap +0.184 | no (inside noise of 0) |
| T7 | Hero - rival2 >= -0.20, top2 | -0.578 ± 0.094 | **-0.469 ± 0.098** (Hero 4.511, rival2 4.980) | Hero **+0.095 ± 0.074**; gap +0.109 | no |
| T2 | Hero + 7 rival1 >= 4.50 | 4.436 ± 0.062 | **4.515 ± 0.064** | **+0.080 ± 0.045** | **yes** |
| T2 | Hero + 7 rival2 >= 4.00 | 3.600 ± 0.067 | 3.671 ± 0.071 | +0.071 ± 0.083 | no |
| T3 | base within the CI of now | 6.813 ± 0.045 | 6.826 ± 0.044 | +0.013 ± 0.015 | yes |
| T3 | strong within the CI of now | 5.134 ± 0.073 | 5.143 ± 0.076 | +0.008 ± 0.065 | yes |
| T4 | act() p99 < 100 µs; hand_end, new_table p99 < 1 ms | act 56-87 µs | act mean 20 µs, p99 51-56 µs; hand_end 46 µs, new_table 51 µs (top-heavy 445 / 431 µs) | | yes |
| T5 | READY >= 22; Hero first on >= 15 of 23 | 22 / 15 (deep pass) | **22 READY, 1 PLAYS (two_boards); first on 18** | | yes |
| T6 | MicroAgent among 7 Heroes <= 4.60 | 4.442 ± 0.065 | 4.485 ± 0.068 | micro +0.043 ± 0.061 | yes |
| holdout | Hero - rival3 on `holdout` (never tuned on) | -0.510 ± 0.106 | -0.372 ± 0.110 (Hero 5.575, rival3 5.947) | Hero **+0.109 ± 0.057**; gap +0.138 | (holdout) |
| - | rival1 among 7 Heroes | 4.539 ± 0.082 | **4.423 ± 0.077** | rival1 -0.116 ± 0.074 | - |
| - | rival2 among 7 Heroes | 5.138 ± 0.076 | 5.107 ± 0.071 | rival2 -0.030 ± 0.084 | - |
| - | realistic, payouts 10/7/5/4/3/2/1/0 | Hero 5.429, gap to rival1 -0.398 | 5.612, gap -0.067 | Hero **+0.183 ± 0.102** | not worse: yes |
| - | realistic, payouts 50/25/12/6/3/2/1/1 | Hero 18.86, gap -3.96 | 21.25, gap -0.63 | Hero **+2.39 ± 0.68** | not worse: yes |

On top Hero gained on rival 1 but not on rival 2 (gap -0.39 -> -0.43); on top2 it gained on both. The holdout row
differs from the rival 3 entry's -0.74 ± 0.16 (2fc1b90, 200 seeds) because this one is paired over 400 seeds on this
commit's code and a quiet host; the delta (+0.138 ± ~0.08) is the comparable number, and rival 3 was never in a screen.

### Screens (tools/sweep.py, strict, seed 7, 5 workers, panic off in every screen base)

S1 (160 seeds, realistic / top / top2 / Hero + 7 rival2, every lever): nothing outside noise on realistic or top;
most levers up on top2 and down on realistic; the first-in shove zone -0.12 to -0.19 on realistic. A dozen busy-loop
processes from another session put Hero's SafeBot into panic in hundreds of tables during the first launch (discarded;
every screen base sets `panic_after` 1,000,000), and S1's settings were queued one after another, so its later rows ran
under 10x the timeouts of its base: `tools/sweep.py` now queues settings side by side. S2 (200 seeds, eight fields):
`reshove_mid_bb` 25 passed alone (Hero + 7 rival1 +0.052 ± 0.049), `vs_cbet_margin` 0.05 was >= 0 everywhere, the threat
read failed realistic. S3 (200 seeds, ten fields with two payout tables): the pair passed every clause (realistic
+0.083 ± 0.081, top +0.140 ± 0.097); the exploitative re-shove price on top of it failed strong (-0.14); the threat
read on top of it helped top2 (+0.08) and rival 2 among Heroes (-0.07) but cost realistic again (-0.015).

| lever (key) | best result | why not shipped |
|---|---|---|
| (a) steal widening by fold-to-steal | not built | step 1: Hero already opens more than either rival everywhere |
| (b) first-in shove zone (`pushfold.fi_threshold_bb` ...) | top2 +0.02-0.05, Hero + 7 rival2 +0.09-0.12 | realistic -0.12 to -0.19: the Monte Carlo bots call shoves wide (the deep pass's finding) |
| (c) observed opener width (`pushfold.reshove_w_observed`) | top2 +0.09 alone | realistic -0.11 alone, ~0 with mid re-shoves; rival 2 among Heroes +0.07 |
| (c) exploitative re-shove price (`pushfold.reshove_exploit`) | on top of the pair: Hero + 7 rival1 +0.19, Hero + 7 rival2 +0.26 | strong -0.14 (Hero copies re-shove into each other), base -0.03 |
| (d) per-seat re-shove read (`preflop.shove_ctx_auto`) | top2 +0.03 | top -0.08 / -0.10 |
| (e) c-bet bluffs by fold-to-c-bet (`postflop.cbet_ftc_read`) | top2 +0.06 | top -0.10 (S1) |
| (f) opens tightened against a re-shove threat (`preflop.reshove_threat`) | on top of the pair: top2 +0.08, rival 2 among Heroes -0.07 | realistic -0.06 alone, -0.015 on top; opt-in for a room of frequent re-shovers |

**Readings.** (1) The deep pass's "volume" was the right axis but the wrong half: the gap is re-raising, not opening,
and pricing re-shoves from a solved table plus an ICM gate takes a third of rival 2's volume and most of its value
per re-shove. (2) Every way of shoving more on Hero's own initiative (first-in zone, exploit price, per-seat reads)
costs the realistic or strong room more than it gains against the rivals; what survives is narrow: re-shove the
solved set over single opens, and stop folding middle pair to small c-bets. (3) Heads-up postflop was worth as much
as the preflop lever in the measurement and is the least-explored part: one margin moved here; c-bet frequency and
turn play were not.

### Assessment: rival 2's decision core behind Hero's shell (not built; the owner's call)

Hero still trails rival 2 by 0.47 on top2 (> 0.30), so the brief asks what the fallback would take. A separate agent
started a hybrid in `hyperion/hybrid/` during this pass; this is the cost from the strategy side, not a review of it.

*What it would take.* Rival 2 is one 1,481-line stdlib file whose `Bot._act` takes the kit-shaped observation
`bestiary.Rival2Bot` already builds from ours, so the adapter exists. The hybrid is a router in `HeroCore.act`: plain
two-card hold'em decisions to a frozen copy of rival 2's `_preflop` / `_postflop`, everything else to Hero's modules,
with Hero keeping `new_table`, the variant wiring, `variant_decide`, SafeBot and the Config. Four pieces need work.
(1) Its ICM curve uses fixed points 10/7/5/4/3/2/1/0 and never reads Rules: payouts (and the hand cap) must be wired
in, or the default 8..1 and top_heavy are both mispriced. (2) Its import costs ~1.15 s (a Monte Carlo 169x169 matrix,
a push/fold solve) and ends in a process-wide `gc.freeze()`; any regenerated variant table set needs its matrix too.
(3) Latency: its postflop sampler is time-boxed on the wall clock (260 µs, hard cap 520 µs), so act() p99 is ~285 µs
against T4's 100 µs, its strict-mode timeouts reached 1.8-2.7% on a loaded host, and its play is not reproducible
under duplicate deals; cutting the budget changes the bot that was measured. (4) No Config lever or read of Hero's
reaches the routed path; tuning means editing the copy.

*Cost on the 23 variants.* The routed path understands two hole cards, a 52-card deck and the standard ranking. With an
observation-level rank remap and the payouts wired in it could take plain hold'em and about seven variants
(permuted_ranks, top_heavy, pot_limit and fixed_raise through the adapter's clamp, with sizing unaware of the cap,
antes_from_level_3, fast_schedule, straddle). The other sixteen (short_deck, lowball, wild_deuces,
flush_over_full_house, toss_or_holdem, both three-card games, omaha_four, both swaps, exposed_card, two_boards,
bonus_card, bounty, knockout_bounty, hi_lo) need Hero's modules: readiness there holds only if the router is exact,
and each routed variant needs a re-measure against the 22-READY baseline. The upside is bounded by rival 2's own
margin here (top2 +0.47 over Hero after this pass; as the lone rival 2 among Heroes 5.11, +0.61 over uniform), less
whatever its latency fix costs.

**Next lever.** Heads-up postflop as the preflop caller and as the raiser, read-driven: the measurement put Hero's
non-showdown postflop loss level with the re-shove gap, and one margin closed part of it. Second: re-shoves from the
threat side (the opt-in `reshove_threat` is the one lever that moves the rival 2 rooms without touching the
re-shove calls), re-tested at 400 seeds on realistic.


## Hybrid candidate (2026-11-01, builder: hybrid)

The fallback the owner agreed to if Hero kept losing after the deep pass: rival 2's decision core behind Hero's
shell, built as a candidate and measured. It does not replace Hero; which bot ships is the owner's decision. Running
log with every table: `docs/drills/hybrid-log.md`.

### What it is (dafb258, d3616b1, 133a837 = v1; 0a8314c = v1.1)

`hyperion/hybrid/`, simulator name `hybrid`, fields `realistic_h`, `top_h`, `top2_h`, `holdout_h` (the hybrid in
Hero's seat, everything else identical, so seating and deals match seed for seed). Nothing in `hyperion/sim/rivals/`
or `hyperion/strategy/` is edited or copied: `Rival2Core` subclasses rival 2's `Bot`, and Hero's `HeroCore`,
`SafeBot`, `icm_value` and `config_from_dict` are imported.
- **Decisions.** Rival 2's core takes plain hold'em: two hole cards, 52 cards, best five of seven, no-limit or pot
  limit (its all-in is `max_raise`, the pot-limit cap), any blind schedule (it reads the current blinds; it has no
  place for future levels or the hand cap), antes (they are in `pot`, which it reads as dead money; its push/fold solve
  has none), any payout table, any rank order (cards are remapped through `Rules.rank_order` before the core sees
  them). Hero takes every table the core cannot represent, by a counter `hero:table:<why>`: short deck, lowball, wild
  cards, flush over full house, hi/lo, two boards, Omaha, three hole cards (v1.1), fixed limit, bounties, knockout
  points, exposed cards. Per decision: preflop with a straddle (`hero:straddle`; the core reads it as an open raise),
  postflop with three hole cards after buying one (`hero:extra_hole`). Discards, swaps and buying a card are Hero's
  `variant_decide`.
- **Payouts.** Rival 2 hard-codes 10/7/5/4/3/2/1/0 in its per-hand ICM curve. The curve is now built from
  `Rules.payouts` at rival 2's own knots with Hero's exact `icm_value`, in hand_end from the exact hand-start chips
  (rival 2 built it inside the first decision of each hand: ~115 us p50, ~500 us p99). Its module globals are untouched,
  so a `rival2` opponent in the same process still plays as built (tested).
- **Timing.** The postflop sampler: 32 samples (rival 2: 160, cut by its 260 us clock at ~110 heads-up), a 200 us
  wall budget, a 450 us hard stop. 32, 64 and rival 2's own sampler measured level with each other (100 seeds, top2_h
  and realistic_h, every pairwise delta inside ±0.18), so v1 takes the cheapest. Soft deadline: if a decision has
  used 350 us before the sampler starts (the process was preempted), Hero's cheap path answers (`hero:soft_deadline`).
  SafeBot around it with Hero's settings (0.5 ms deadline, panic after 5 overruns and 2% of calls: Hero's cheap path
  for the rest of the table, `hero:panic`). A core exception is Hero's decision (`hero:core_error`), never a fold.
- **v1.1.** v1 followed the brief for 3-card games (the core plays preflop from its best two, Hero discards). That
  measured 0.35-0.63 worse than Hero on the three 3-card entries, where Hero plays from 3-card variant tables, so v1.1
  gives Hero those tables. No 2-card decision changed, so every 2-card number below holds for both versions.
- **Tests.** `tests/test_hybrid.py`, 36: 300 deep hands legal with no error swallowed; all 23 catalogue entries with
  no exception and the expected routing; the rank-remap round trip (a recorded plain table replayed under a rank
  permutation, every card in displayed ranks: every decision identical); permuted aces shove and permuted 72o folds;
  payouts in the curve; the fallbacks; and timing (p99 < 300 us, strict timeouts < 1%, with a busy-loop host check).

Counters in every plain hold'em run below: the core took 99.6% or more of the decisions; the rest were soft-deadline
(4-385 per run) and panic (0-799 per run, on loaded hosts) fallbacks. 0 exceptions, 0 illegal actions, 0 swallowed
errors, 0 core errors anywhere.

### Measurements

Duplicate deals, `--rotate`, strict, seed 7, 200 seeds x 8 rotations unless noted, the same deals for both bots;
paired deltas are means of per-seed differences with 95% intervals. Uniform is 4.50. Hero is the frozen Hero at
7e51197 (after the aggression pass shipped f349380). The first runs were against Hero at 133a837 (before it); both
columns are kept. Where the hybrid's table holds no Hero clone (realistic, holdout, the rival 2 mirrors), its runs
are from 133a837 and paired with the new Hero's: its opponents are the same code and the core took all but 0.1% of
its decisions. Load is the 1-minute average on the 8-core box during the runs.

**1-2. The fields and the holdout.**

| field | Hero 7e51197 | hybrid | hybrid - Hero 7e51197 | hybrid - Hero 133a837 | load (Hero / hybrid runs) |
|---|---|---|---|---|---|
| realistic | 5.598 ± 0.097 | 5.491 ± 0.106 | -0.107 ± 0.132 | +0.001 ± 0.129 | 0.9-1.0 / 4.2-7.2 |
| **holdout** (measured once) | 5.552 ± 0.097 | 5.430 ± 0.109 | -0.123 ± 0.128 | -0.021 ± 0.133 | 0.9-1.0 / 6.4-7.2 |
| top | 4.668 ± 0.104 | 4.940 ± 0.108 | **+0.272 ± 0.135** | +0.491 ± 0.139 | 0.9-2.9 |
| top2 | 4.511 ± 0.103 | 4.961 ± 0.103 | **+0.450 ± 0.139** | +0.493 ± 0.148 | 2.7-2.9 |
| strong | 5.133 ± 0.105 | 5.123 ± 0.109 | -0.009 ± 0.139 | +0.015 ± 0.143 | 2.6-3.0 |

On the same seeds against the rivals: holdout hybrid - rival3 -0.446 ± 0.169 (Hero 7e51197 -0.362 ± 0.159); realistic
hybrid - rival1 -0.230 ± 0.167 (Hero -0.041 ± 0.165); top hybrid - rival1 +0.284 ± 0.143 (Hero +0.012 ± 0.143); top2
hybrid - rival2 +0.031 ± 0.127 (Hero -0.424 ± 0.139). The hybrid is first in top2 and strong, second in the others
(behind rival1 on realistic, rival3 on the holdout, rival2 on top by 0.06).

**3. The mirrors** (the hybrid runs from 133a837; their tables are all rival 2).

| room | lone bot | the same room with Hero 7e51197 | paired |
|---|---|---|---|
| hybrid + 7 rival2 | hybrid **4.551 ± 0.099** | Hero 3.680 ± 0.095 | hybrid - Hero **+0.871 ± 0.136** |
| rival2 + 7 hybrids | rival2 **4.430 ± 0.097** (the hybrids 4.510) | rival2 among 7 Heroes 5.131 ± 0.104 | rival 2 **-0.701 ± 0.149** |

**4. Readiness on the 23 entries** (variant_matrix.py's rules, `--field realistic`, 200 unrotated tables per entry,
seed 7, strict, the hybrid in Hero's seat of the same tables; one worker each).

| variant | route | Hero 7e51197 | hybrid v1.1 | paired | over 1 ms, hybrid (Hero) | load | v1 vs Hero 133a837 (load 5.0-5.7) |
|---|---|---|---|---|---|---|---|
| permuted_ranks | core 100% | 6.23, 1, READY | 6.15, 1, READY | -0.08 ± 0.36 | 0.06% (0.02%) | 5 | -0.00 ± 0.37 |
| short_deck | Hero (deck) | 5.72, 1, READY | 5.86, 1, READY | +0.13 ± 0.15 | 0.02% (0.02%) | 5 | +0.07 ± 0.16 |
| lowball | Hero (showdown) | 7.79, 1, READY | 7.75, 1, READY | -0.04 ± 0.12 | 0.03% (0.03%) | 6 | -0.01 ± 0.12 |
| wild_deuces | Hero (showdown) | 7.16, 1, READY | 7.12, 1, READY | -0.04 ± 0.18 | 0.23% (0.25%) | 8 | -0.14 ± 0.17 |
| flush_over_full_house | Hero (showdown) | 5.60, 1, READY | 5.59, 1, READY | -0.01 ± 0.21 | 0.38% (0.35%) | 9 | **+0.26 ± 0.22** |
| toss_or_holdem | Hero (three_cards), panic 1% | 6.06, 1, READY | 6.17, 1, READY | +0.11 ± 0.15 | 0.28% (0.17%) | 9 | **-0.45 ± 0.33** |
| three_card_blind_discard | Hero (three_cards), panic 1% | 6.00, 1, READY | 6.02, 1, READY | +0.02 ± 0.16 | 0.76% (0.71%) | 13 | **-0.35 ± 0.32** |
| three_card_keep | Hero (three_cards), panic 1% | 5.95, 1, READY | 6.05, 1, READY | +0.10 ± 0.18 | 0.82% (0.77%) | 16 | **-0.63 ± 0.32** |
| omaha_four | Hero (must_use), panic 3% | 6.65, 1, READY | 6.66, 1, READY | +0.01 ± 0.11 | 0.86% (0.86%) | 17 | -0.01 ± 0.05 |
| swap_holdem | core 93%, panic 7% | 5.59, 3, PLAYS | 5.53, 2, READY | -0.06 ± 0.36 | 1.29% (0.59%) | 20 | +0.17 ± 0.38 |
| swap_one_turn | core 98%, panic 2% | 5.82, 1, READY | 5.69, 2, READY | -0.13 ± 0.36 | 0.28% (0.15%) | 14 | -0.10 ± 0.36 |
| exposed_card | Hero (exposed) | 5.79, 1, READY | 5.67, 1, READY | -0.12 ± 0.22 | 0.03% (0.03%) | 11 | +0.09 ± 0.20 |
| two_boards | Hero (showdown) | 5.25, 3, PLAYS | 5.35, 2, READY | +0.10 ± 0.26 | 0.01% (0.01%) | 8 | -0.02 ± 0.23 |
| bonus_card | core 77%, extra_hole 23% | 5.62, 1, READY | 5.49, 1, READY | -0.13 ± 0.31 | 0.01% (0.02%) | 7 | +0.07 ± 0.30 |
| bounty | Hero (bounty) | 5.55, 2, READY | 5.54, 1, READY | -0.00 ± 0.20 | 0.01% (0.01%) | 7 | -0.12 ± 0.24 |
| knockout_bounty | Hero (bounty) | 7.16, 1, READY | 7.33, 1, READY | +0.17 ± 0.39 | 0.06% (0.04%) | 7 | -0.03 ± 0.35 |
| top_heavy | core 100% | 20.90, 2, READY | 17.98, 2, READY | -2.92 ± 3.18 | 0.20% (0.09%) | 7 | -2.53 ± 3.16 |
| hi_lo | Hero (showdown), panic 1% | 5.68, 2, READY | 5.58, 2, READY | -0.10 ± 0.25 | 0.81% (0.67%) | 16 | +0.16 ± 0.22 |
| pot_limit | core 94%, panic 5% | 5.60, 2, READY | 5.70, 2, READY | +0.11 ± 0.32 | 1.37% (0.83%) | 18 | -0.02 ± 0.33 |
| antes_from_level_3 | core 94%, panic 6% | 5.58, 1, READY | 5.61, 2, READY | +0.02 ± 0.37 | 1.37% (0.84%) | 16 | -0.33 ± 0.35 |
| fixed_raise | Hero (fixed_limit), panic 4% | 5.71, 2, READY | 5.58, 2, READY | -0.13 ± 0.25 | 1.03% (0.91%) | 28 | +0.10 ± 0.19 |
| fast_schedule | core 96%, panic 4% | 5.44, 2, READY | 5.40, 2, READY | -0.04 ± 0.38 | 1.74% (0.93%) | 32 | -0.19 ± 0.37 |
| straddle | core 26%, straddle 56%, panic 18% | 5.97, 1, READY | 5.60, 2, READY | **-0.37 ± 0.34** | 1.97% (0.85%) | 35 | +0.17 ± 0.31 |

Route is the hybrid's; "panic" is the share of its decisions that SafeBot's panic gave to Hero's cheap path. The last
column is v1 (3-card tables still on the core) against Hero 133a837, run earlier at a steady load of 5.0-5.7.
**Verdicts (variant_matrix.py): hybrid v1.1 READY 23, first on 13; Hero 7e51197 READY 21, PLAYS 2 (swap_holdem,
two_boards), first on 15** (v1 against Hero 133a837: hybrid READY 21, PLAYS 2, first on 8; Hero READY 22, PLAYS 1,
first on 12). 0 exceptions, 0 illegal, 0 swallowed errors and 0 core errors for either bot. Another session took the
box from load 5 to 35 during this run, so its later rows measure the host as much as the bots (both bots ran side by
side at the same load; the hybrid's timeouts reached 1.3-2.0% there and its panic share 4-18%). The Hero-routed rows
are a null check (Hero's code and seed; strict-mode timeouts are host events and one different decision changes the
rest of a table): they spread -0.13 to +0.17 and none is outside its interval in this run (one of 11 was in v1's).
The rows that measured a real cost were v1's 3-card games (fixed in v1.1, now +0.02 to +0.11) and antes in v1 (-0.33 ±
0.35, inside noise in this run). top_heavy here is 200 unrotated tables (± 3); the payout runs below are the read.

**5. Payout robustness** (`--rules` payouts on realistic and top; linear 8..1 is the default rows above).

| field, payouts | Hero 7e51197 | hybrid | hybrid - Hero 7e51197 | hybrid - Hero 133a837 | load |
|---|---|---|---|---|---|
| realistic, 8..1 | 5.598 | 5.491 | -0.107 ± 0.132 | +0.001 ± 0.129 | above |
| realistic, brief 10/7/5/4/3/2/1/0 (uniform 4.0) | 5.628 ± 0.153 | 5.492 ± 0.154 | -0.136 ± 0.190 | +0.116 ± 0.197 | 3.0-10.0 / 1.4-5.5 |
| realistic, top_heavy 50/25/12/6/3/2/1/1 (uniform 12.5) | 20.83 ± 0.89 | 20.09 ± 0.94 | -0.74 ± 1.22 | +0.57 ± 1.23 | 2.6-9.6 / 5.0-6.0 |
| top, 8..1 | 4.668 | 4.940 | +0.272 ± 0.135 | +0.491 ± 0.139 | above |
| top, brief | 4.263 ± 0.139 | 4.541 ± 0.149 | +0.278 ± 0.188 | +0.624 ± 0.196 | 9.6-10.0 / 6.0-9.6 |
| top, top_heavy | 13.94 ± 0.83 | 14.74 ± 0.83 | +0.80 ± 1.03 | +2.62 ± 1.06 | 3.5-9.7 / 3.9-6.0 |

Under top_heavy Hero 133a837 was the weak one (19.5 on realistic, 12.7 on top, 3.4-3.7 behind both rivals on top);
the aggression pass took most of that back (20.8, 13.9), and the hybrid's remaining margin there is inside noise.
The hybrid's own top_heavy points (20.1, 14.7-15.4) sit with the rivals' (rival1 22-23 on realistic; 15-16 on top).

**6. Latency and timeouts in our engine.** In one field with both bots (hybrid, hero, rival1, rival2, pushfold, tag,
hero_tight, loose_aggro):

| run | load | hybrid p50 / p99 / mean, over 1 ms | Hero p50 / p99 / mean, over 1 ms | rival2 as built |
|---|---|---|---|---|
| 80 seeds, quiet | 1.2-1.5 | 24 / 179 / 38.7 us, 1 in 100,039 | 19 / 54 / 21.5 us, 1 in 110,240 | 119 / 305 us, 5 in 99,866 |
| 200 seeds | 5.0 -> 2.0 | 24 / 192 / 39.8 us, 0.009% | 19 / 61 / 21.8 us, 0.003% | 120 / 350 us, 0.035% |

Against hero_tight (the same code path as Hero) in the same field runs at load 3-9: the hybrid timed out 1.5-3x as
often (top_h 0.224% vs 0.127% at load 6.5-8.9; top2_h 0.065% vs 0.044%; strong 0.009% vs 0.003%) and 4-7x less often
than rival 2 as built (0.33-0.90%). Its p99 stayed 175-292 us in every run (Hero 53-152 us). hand_end, untimed here:
p99 226 us (Hero 137) on linear payouts, 599 us (Hero 527) on top_heavy; new_table p50 101 us (Hero 46). **The p99
target (< 300 us) is met; the timeout target (under Hero's rate at the same load) is not, and no sampler budget meets
it.** Overruns track the mean time per decision; the core's preflop alone (p50 22-32 us) costs about what Hero's whole
decision does, and postflop is 17% of its decisions and ~45% of its time. Rival 2's measured 3.1% becomes 0.01-0.22%.

### Verdict

On the two judges the brief named, the hybrid is not better than Hero by more than noise. On the holdout it is
-0.12 ± 0.13 against the frozen Hero (-0.02 ± 0.13 against Hero before the aggression pass), on realistic -0.11 ±
0.13 (+0.00 ± 0.13); both point estimates now lean to Hero. Its gain is real but confined to the rooms built from
rivals 1 and 2: top +0.27 ± 0.14, top2 +0.45 ± 0.14, uniform alone among seven rival 2s where Hero is 0.82 under it,
and a lone rival 2 held to 4.43 where seven Heroes let it reach 5.13. Strong is level, and no payout table shows a
difference beyond noise against the current Hero. The aggression pass already took back about half of the hybrid's
margin on top (+0.49 -> +0.27) and little on top2 (+0.49 -> +0.45). On the twists, v1.1 costs nothing beyond noise on
22 of 23 entries against the frozen Hero (23 READY against Hero's 21 READY and 2 PLAYS; first on 13 against 15); the one
row outside its interval, straddle -0.37 ± 0.34, ran at load 35 with 18% of its decisions in SafeBot panic. v1's
best-two rule cost 0.35-0.63 on the 3-card games, which is why v1.1 exists. On timing it costs 1.5-3x Hero's timeout
rate at the same load and a p99 of ~175-290 us against Hero's ~55-150; on a loaded host, SafeBot's panic gives a few
tables per run to Hero's cheap path.

### Recommendation (the decision is the owner's)

Keep Hero as the default. The hybrid buys 0.3-0.45 points only in rooms seeded with copies of rival 1 and rival 2,
and nothing on the holdout, the one measurement neither bot was tuned for. It pays for that in timeouts. Keep `hybrid`
registered and tested as the ready alternative. If the Nov 7 research says the field will be mostly strong
agent-built bots like rivals 1 and 2, the top rows are the relevant ones. Switching then means the entry file builds
`hyperion.hybrid.make_bot` instead of Hero's. tools/pack.py already copies `hyperion/hybrid/` and
`hyperion/sim/rivals/rival2.py` into the zip, but the import gets ~1.2 s slower (rival 2's import-time Monte Carlo and
push/fold solve, ending in a process-wide `gc.freeze()`). Re-run tools/gate.py on that zip before trusting it; it has
not been run with the hybrid. Two things could change this recommendation: wiring the exploit layer into the hybrid (a
follow-up), and Hero's next lever (heads-up postflop), where the aggression pass located the rest of rival 2's margin.

### Not done, and notes for the strategy owner

- Nothing in `hyperion/strategy/*` was changed, and nothing there needs to change. One coupling to know: when Hero
  meets a hand after the core acted in it, `HybridCore` writes `HeroCore.hand_no` and `hand_start` (the exact
  hand-start chips) so Hero's hand_end chip chain stays exact. If those attributes are renamed, keep an alias.
- The holdout was measured once (v1, 133a837) and never tuned on; v1.1 changes no 2-card decision. No leak analysis
  against rival 3.
- The hybrid's realistic and holdout runs ran at load 4-7 and the frozen Hero's at load ~1; strict-mode timeouts cost
  the hybrid those runs' 0.04-0.09% of decisions. A load-matched re-run of the hybrid on realistic was queued and
  dropped: another session took the box to load 34 at 03:40. The holdout is not re-run, on purpose (once per
  candidate version).
- The exploit layer (`observe` / `hand_end` / `override`) is not wired in; that is a follow-up.
- Rival 2's import-time tables depend on the host. Its import-time Monte Carlo stops at 1,500 boards or a 2.4 s budget,
  whichever comes first. At load ~30 it stopped at 1,088 and 1,152 boards and the import took 5.9-6.4 s; on a quiet
  host it reaches 1,500 in ~1.15 s. So on a slow tournament host the core plays from noisier equity tables, and the
  submission's import takes several seconds. This applies to the hybrid and to `rival2` alike.
- Not measured: MicroAgent against the hybrid; the hybrid in `top3`; the hybrid's play is reproducible only where the
  sampler's wall budget never binds (multiway spots and preempted calls are time-boxed).

## Rival 4 in the pool (the judge) (2026-11-01)

**What landed** (`fa51655` archive, `c477b22` report, `0d660dc` adapter, fields and tests). Red-team drill 4's bot
(`docs/drills/redteam/redteam-4.md`) was built blind in 41 minutes against the same brief and kit as rivals 1 to 3,
with no access to this repository or to any earlier rival, and with **no assigned philosophy** ("the strongest team in
the room, build whatever scores most"). It is 657 lines, stdlib only, and is in the simulator as `rival4`. Its design:
exact ICM at every all-in decision, read from the payout table it is given; an embedded 169-class equity table;
push/fold at 8 bb or less; postflop equity from the made hand plus outs, with no Monte Carlo; and a per-seat model of
three counters that flags seats that never play.

**It is the judge.** It decides between the candidate cores in **one final comparison**: Hero, `hybrid` (rival 2's
core) and `hybrid3` (rival 3's core), each with and without the exploit layer. Until then:
- no candidate (Hero, a Hero preset, any hybrid) sits next to it beyond the smoke tests in `tests/test_sim_rival4.py`;
- nobody tunes on it or on `judge` / `judge_top`;
- no leak analysis of any candidate against it.

Everything measured below is rivals only.

`hyperion/sim/rivals/rival4.py` is the frozen file (md5 `28a0655f...`) below a seven-line origin header.
`bestiary.Rival4Bot` is the shared kit adapter with two differences, both things the brief's kit may pass:
- new_table's rules dict carries `payouts` (`Rules.payouts`). The rival reads it (keys `payouts`, `points`, ...),
  so its ICM prices all-ins on the table that scores it, not the brief's 10/7/5/4/3/2/1/0 hard-coded by rivals
  1 to 3. Its decomposition (base x players outlasted + bonuses for first and top two) is exact for any table whose
  places from third down are equal steps. Operator check against brute-force Harville: exact to 1e-13 for the brief's
  table and for our 8..1, off by up to 5.3 points on top_heavy with 4 or more alive.
- hand_end passes the hand's history in the kit's `(seat, (kind, amount))` shape, as rival 3's adapter does. Rival 4
  counts each seat's VPIP, raises and shoves from it.

Its own engine passed neither. The shared rules dict moved into `RivalBot.kit_rules`, unchanged for rivals 1 to 3.

Fields:
- `judge` = `holdout` with rival 4 in rival 3's seat, seat for seat (so `realistic`'s bots with rival 4 for rival 1):
  hero, rival4, montecarlo30, montecarlo, pushfold, loose_aggro, tag, timeout_then_recover;
- `judge_top` = hero, rival1, rival2, rival3, rival4, pushfold, tag, loose_aggro.

No other field changed.

**The hero seat is swapped by name: `<field>@<bot>`.** `bestiary.field_names("judge@hybrid3")` returns the field with
`hybrid3` in Hero's seat and every other entry unchanged. The runner shuffles a field's seating with the table seed
alone, so the swapped bot sits exactly where Hero sat, with the same deals and the same opponents' seeds:
`judge@X - judge` is paired seed for seed, as `realistic_h - realistic` is. It works for any field with one `hero` and
any registered bot not already seated (a bot seated twice would merge in the report, so that is refused). The eight
judge swaps for `hybrid`, `hybrid_x`, `hybrid3` and `hybrid3_x` are also listed in `FIELDS`, so
`python -m hyperion.sim --field judge_top@hybrid3_x` works. Hero with or without the layer stays in Hero's own seat:
- `hero` ships with the layer since `1957983`;
- `--hero-config '{"exploit.bet_checked": false, "exploit.steal": false, "exploit.steal_min_fold": 0}'` switches it
  off (7e51197's behaviour).

Do not pass `--hero-config` on a hybrid run: the hybrids' fallback Hero takes it too.

`tests/test_sim_rival4.py` has 12 tests:
- 300 hands of eight copies, with its exception swallowing unwrapped;
- the strict timeout rate (< 1%; skips if a fixed 30-us loop overruns too);
- mode "model" never folds it;
- the payouts and its ICM through the adapter;
- the hand_end history round trip;
- the folder flag;
- push/fold sanity and reproducibility;
- the fields and the swap;
- one 12-table strict smoke run per judge field (conservation and legality only; no number from them is read).

**Measurements (rivals only).** 1,600 duplicate tables each (`--tables 200 --rotate --seed 7`), from a clean worktree
at `0d660dc`, two at a time. Hero's seat is taken by `tag`, so `judge_top` here seats two tags (one line in the
report). Uniform is 4.50. Paired deltas are means of per-seed differences, with 95% intervals. Script:
`rival4_measure/measure4.py` in the session scratchpad. It refuses any candidate name; raw output and per-seed samples
are beside it.

`judge_top` with tag in Hero's seat, strict, load 11-14:
```
bot             n    pts  ±95%    p1   p2   p3   p4   p5   p6   p7   p8  bust%   tmo   exc   ill safe_err safe_over  p50us  p99us  maxus  1st_us
rival3        200  4.968 0.127    27   11    8    9   10   12   12   11   67.0   297     0     0        0         0     28    158  14323    4047
rival2        200  4.932 0.110    22   14    9   10   11   11   13   10   68.2  1415     0     0        0         0    124    627  27294    5980
rival4        200  4.822 0.085    12   13   15   15   16   14    9    6   79.2   229     0     0        0         0     22    128  10708     287
rival1        200  4.819 0.124    26   13    7    6    8   12   14   13   66.0   198     0     0        0         0     21    116  15734     789
tag           200  4.400 0.058     1   13   18   19   16   13   11    9   88.8    73     0     0        0         0      3     16  11125     211
pushfold      200  4.194 0.088     2   14   16   14   14   13   12   14   86.8    51     0     0        0         0      4     20  12053    1176
loose_aggro   200  3.466 0.114     7   10    8    7    9   12   18   29   85.6    28     0     0        0         0      3     12   4839     219
```

Paired, strict: rival4 - rival1 **+0.003 ± 0.163**, rival4 - rival2 **-0.109 ± 0.153**, rival4 - rival3 **-0.145 ±
0.158**, rival4 - tag +0.423 ± 0.107. The other rivals: rival3 - rival1 +0.149 ± 0.196, rival3 - rival2 +0.036 ± 0.184,
rival1 - rival2 -0.113 ± 0.171.

Same seeds in mode "model", where nobody at this table is folded for time: rival4 4.802, rival2 4.985, rival3 4.925,
rival1 4.785. Paired: rival4 - rival1 +0.018 ± 0.165, rival4 - rival2 -0.182 ± 0.146, rival4 - rival3 -0.123 ± 0.156.

rival4 + 7 tag: rival4 **6.076 ± 0.098** (46% firsts, busts in 28.5% of seats); paired rival4 - tag **+1.801 ± 0.112**.
Model mode: 6.071, +1.795 ± 0.112.

The two adapter choices, same seeds, mode "model" (no timeouts at these tables, so the pairs are clean). A first pass
in strict mode ran at load 20-27, where the timeouts rose 3-20x.
| rival4 with ... minus without | `judge_top` (tag in Hero's seat) | rival4 + 7 tag |
|---|---|---|
| payouts passed (8..1) vs withheld (the brief's table) | +0.014 ± 0.089 | **-0.105 ± 0.050** (6.07 vs 6.18; 46% vs 51% firsts) |
| hand_end history passed vs withheld | +0.090 ± 0.082 | +0.106 ± 0.085 |

**Latency and timeouts in our engine.**
- Through the adapter, rival 4 decides in p50 22 us (15 us among seven tags), p99 128-138 us (89-122 us).
- 0 exceptions and 0 illegal actions in 3.3 million decisions over the 12 runs; no bot had any.
- Strict (wall clock), at load 11-14:
  - rival 4 is over 1 ms on 0.085% of decisions on `judge_top` and 0.026% among seven tags;
  - at the same moments: tag 0.017%, rival1 0.077%, rival3 0.115%, rival2 0.56%.
- Strict at load 20-27: rival 4 0.40% / 0.56%, rival1 0.36%, rival3 0.49%, rival2 2.3%, tag 0.07%.

The rate follows the host. In the gate re-run it matched a fixed 30-us loop call for call (report §4).

**Mode "model" cannot model rival 4, and says so by construction.** The mode folds or checks a bot only when the bot
reports a modelled cost for the decision in `last_cost_ns`. Only the Monte Carlo and timeout bots do. Rival 4
reports none, like rivals 1 to 3, Hero and the hybrids, so it is never folded for time there: 0 timeouts by
construction. Its wall-clock time is still recorded: 0.03-0.43% of its decisions took over 1 ms of wall time in those
runs, all of it host preemption. Its own work (table lookups, a few 1.3-us ICM calls, no sampler, no replay) never
comes near the budget. A cost model for it would report a constant ~20 us and fold nothing, which is what the mode
does already. So in mode "model" the judge never times out. In strict mode it times out about as often as a 30-us
loop on the same host.

**What it says.**
1. *The rival built with no philosophy is level with the other three on `judge_top`.* Strict: 4.82, against
   4.82-4.97 for rivals 1 to 3, every pair inside its interval. In mode "model" rival 2 gains (it is not folded for
   its 0.56% overruns), and rival4 - rival2 is -0.18 ± 0.15.
2. *Its style is different.* It wins the fewest tables of the four (12% firsts, against 22-27%). It busts the least
   (in 79% of seats, against 66-68%) and is last the least (6%). Its ICM on our linear table values only outlasting.
   It keeps that profile with the brief's table too (13% firsts), so the style is its own, not the table's.
3. *Giving it our payout table does not help it.* On `judge_top` there is no difference. Against seven tags it scores
   0.11 more pricing all-ins on the brief's top-heavy table, which plays for first more often. We pass the payouts
   anyway, so it is judged on the table we play.
4. *The history at hand_end is worth about +0.1 to it,* less than the +0.22 it is worth to rival 3. Its model is
   three counters.

**Not done here.**
- No candidate is measured against rival 4, and none is tuned on it: not Hero, not a Hero preset, not a hybrid.
- No `judge` run with a non-candidate in Hero's seat (not on the list).
- No rival tuning, and no twists.
- Every earlier field is unchanged.
- The judge is never tuned on. It is measured once, in the final comparison.

## Timeout and dead-seat exploit pass (2026-11-01, builder: exploit pass)

Scope: `hyperion/strategy/*` (the new `exploit.py`), `tools/sweep.py`, the strategy and sweep tests. In the engine
and the bestiary, only the deterministic timeout model, one bot (`timeout_burst`) and the `timeouts` field.

Brief: make the field's timeouts measurable; build a layer that reads dead and timing-out seats and attacks them,
callable by any decision core; screen it; ship by the rule. The rule: paired delta >= 0 on realistic and top, not
below -0.03 on base or strong, and at least one field outside noise.

Running log with every table: `docs/drills/exploit-pass-log.md`. The coordinator cut items 4
(`preflop.reshove_threat` at 400 seeds) and 5 (heads-up postflop reads) mid-pass: the plan moved to choosing the
decision core.

**Why this lever.**
- CHALLENGE.md names attacking dead and timing-out seats as an edge against one-hour student bots.
- The choice was also informed by one holdout number, the only one used: rival 3's lead over Hero on `holdout` halves
  without the field's timeouts (`--mode measure`, -0.74 -> -0.36).
- Rival 3's code was not read, its decisions were not traced, and nothing was screened on `holdout`. The holdout row
  below was measured once, in the final run.
- Rival 3 is about to stop being a holdout (the core comparison; rival 4 is the judge).

### 1. Timeouts were wall-clock; now they can be modelled (72440a6)

Every timeout bot in the bestiary timed out on the wall clock:
- `montecarlo`: 200 honest rollouts, about 1.0 ms heads-up on this box (half over the budget on a quiet host, all
  of them when it is loaded); 2+ opponents always over;
- `montecarlo30`: a 2 ms sleep on 30% of its postflop decisions;
- `timeout_then_recover` and `timeout`: 2 ms sleeps.

So a strict screen's timeouts followed the host. Engine mode `model` (`--mode model` in the runner and
`tools/sweep.py`; default off, strict and measure unchanged, Hero bit-identical):
- no bot is folded on the wall clock;
- a bot that reports `last_cost_ns` is folded when that cost is over 1 ms;
- `MonteCarloBot` reports 5 us + samples x a per-rollout cost calibrated on this box (4.0 us + 0.5 us per hand
  evaluated for honest rollouts), with a seeded lognormal spread of 0.05;
- the sleeping bots report their sleep and skip it;
- modelled bots do the same work and draw the same decision RNG as in strict mode, so tables replay exactly.

Against the wall clock on the same seeds (100 x 8, load 7.5-10.9, not quiet), as a share of all the bot's decisions:

| bot | wall clock | model |
|---|---|---|
| montecarlo30 | 10.9% | 10.8% |
| timeout_then_recover | 29.4% | 29.35% |
| timeout_burst | 10.9% | 10.7% |
| montecarlo | 25.0-26.5% | 22.6-24.4% |

The honest Monte Carlo is the one that moves, and it is lower under the model, which is calibrated quiet. Every bot's
points agree within noise. A quiet-host repeat was not possible: other sessions held the box at load 15-50 for most of
the pass.

New:
- `timeout_burst`: outages of 10-30 hands with 20-50 hands of recovery between them;
- field `timeouts`: hero, montecarlo, montecarlo30, timeout_then_recover, timeout_burst, tag, pushfold, loose_aggro.

In the model the honest Monte Carlo times out 55% heads-up and 99-100% with 3+ in the hand. When it plays, it calls
91% of bets. So it is a folder multiway and a coin flip heads-up.

### 2. The layer (8302a59, 003f4d2, 1957983)

`hyperion/strategy/exploit.py` imports only `hyperion.core.types`, and its own betting-round replay of
`obs.history` matches engine-logged decisions seat by seat (0 resyncs). Reads per seat, in three cells (preflop,
postflop heads-up, postflop with 3+):
- the streak of passive decisions since the last call or raise. A timed-out decision is always a check or a fold,
  and one call or raise ends the streak: that is recovery.
- a decayed (0.85), smoothed fold rate facing a bet (preflop: a raise);
- raises ever.

Spots (Config `exploit.*`):

| spot | what it does | shipped |
|---|---|---|
| `bet_checked` | no bet to call, and every opponent left has at least `post_streak` (1) passive decisions in the cell since its last call or raise (a seat that has just called is never bluffed), with a product of fold rates of at least `bet_min_fold` (0.5): bet a third of the pot instead of checking | on |
| `steal` | first in, every seat to act has 12 passive preflop decisions in a row (reads dead): raise any two to 2 bb | on |
| `steal_min_fold` | the same raise when the product of the preflop fold rates behind (1 for a dead seat) is at least 0.7 | 0.7 |
| `isolate` | raise a limp, or call a small raise, from a seat that folds postflop, instead of folding | off (S2: strong -0.12, nothing gained) |
| `dead_shift` | Hero only: dead seats behind count as folded for the open range | off (S2: strong -0.05) |

`ExploitParams()` is neutral (every spot off). `ExploitParams.shipped()`, or the dataclass `ShippedExploitParams`,
is the set above, and is what Hero's Config defaults to. Without action history the layer is inert.

**How a core that is not Hero calls the layer.** The layer is `hyperion/strategy/exploit.py`. It imports only
`hyperion.core.types` and holds no reference to Hero.

*Either* wrap the whole bot:
```python
from hyperion.strategy.exploit import ExploitParams, Exploited
bot = Exploited(inner_bot, ExploitParams.shipped())
```
The wrapper observes, lets `inner_bot.act` decide, overrides, and forwards `hand_end`. The engine reaches
`variant_decide` through `.inner`. A slip in the layer keeps the inner action.

*Or* call it inside a core, in this order:
```python
from hyperion.strategy.exploit import Exploit, ExploitParams
self.xl = Exploit(ExploitParams.shipped())     # __init__; ExploitParams() is off, .shipped() is Hero's set
self.xl.new_table(n_players, seat)             # new_table
self.xl.observe(obs)                           # act(): first, on the kit's own observation (its own history,
                                               #   before any rebuilt history), every decision
a = my_core_decision(obs)
b = self.xl.override(obs, a)                   # None = keep a; skip in a panic or cheap path
a = b if b is not None else a
self.xl.hand_end(result)                       # hand_end, every hand
```
Wrap each call in try/except as Hero does: a slip there must not cost the decision. Two rules:
- observe every decision, the ones another module makes included, or the replay misses actions and the reads
  drift;
- keep one layer per bot. A shell that wraps a core and also builds Hero's fallback should give the fallback
  `exploit=ExploitParams()`, as `hyperion/hybrid/bot.py` does, or each decision is read twice.

What it needs from `obs`: `history` (the flat (seat, Action) list for the hand), `stacks`, `bets`, `in_hand`,
`button`, `blinds`, `street`, `hand_no`, `to_call`, `min_raise`, `max_raise`, `legal`, `pot`. With no history it is
inert (it reads only what it is shown). Its cost is a few microseconds per decision: a replay of the new history
tail, and a product over at most seven seats.

### 3. Screens (model mode, seed 7, duplicate deals, paired)

- **S0** (60 seeds; realistic, timeouts): the bet with a short streak was the big one (+0.32 / +0.25). The
  dead-seat steal was small and steady (+0.04), isolation nothing.
- **S1** (160 seeds, eight fields): bet + steal gained on every field.

  | field | Δhero |
  |---|---|
  | realistic | +0.311 ± 0.076 |
  | timeouts | +0.239 |
  | top | +0.132 ± 0.102 |
  | top2 | +0.212 |
  | base | +0.060 ± 0.026 |
  | strong | +0.091 |
  | Hero + 7 rival1 | +0.076 |
  | Hero + 7 rival2 | +0.114 |

  Streak 0, 1 and 2 were within noise of each other. A fold product of 0.6 instead of 0.5 gave up a third of the
  gain.
- **S2** (160 seeds, five fields, on top of bet + steal): the fold-read steal gained everywhere it was seated:
  realistic +0.107 ± 0.055, timeouts +0.179 ± 0.052, base +0.067 ± 0.031, top +0.05, strong +0.08. The rest is in
  the table above, or was level: half-pot bets, streak 2.

The bet is not only a dead-seat lever. It fires 4.3 hands a table on `top`, mostly against rival 1, which folds a
lot after checking. It is a read-driven "bet when checked to", and it covers much of what item 5 (heads-up postflop
reads) was going to try.

### 4. Final (8a7af98, clean worktree, 400 seeds x 8 rotations; "before" = the three keys off, bit-identical to 7e51197)

Model = `--mode model`, SafeBot panic off, every field. Strict = the wall clock, panic on as shipped, nine fields, at
load 31-61 from other sessions (105 of 57,600 tables panicked). Cells: Hero's paired change, then gaps to the
rivals before -> after.

| field | model | strict | gaps (model; strict) |
|---|---|---|---|
| realistic | **+0.411 ± 0.055** | **+0.442 ± 0.063** | Hero - rival1 +0.000 -> **+0.495**; +0.019 -> **+0.507** |
| timeouts | **+0.382 ± 0.052** | **+0.389 ± 0.060** | |
| top | **+0.133 ± 0.078** | **+0.195 ± 0.076** | rival1 -0.030 -> **+0.167**, rival2 -0.346 -> -0.187; rival1 -0.082 -> **+0.143**, rival2 -0.410 -> -0.110 |
| top2 | **+0.178 ± 0.078** | **+0.210 ± 0.084** | rival2 -0.516 -> -0.264; -0.440 -> **-0.196** |
| Hero + 7 rival1 | **+0.130 ± 0.059** (4.646) | **+0.125 ± 0.064** (4.640) | |
| Hero + 7 rival2 | -0.075 ± 0.077 (3.632) | - | |
| rival1 / rival2 among 7 Heroes | rival1 **-0.121 ± 0.082**, rival2 -0.076 ± 0.086 | - | |
| base | **+0.124 ± 0.022** | **+0.120 ± 0.024** | |
| strong | **+0.200 ± 0.079** | **+0.198 ± 0.077** | |
| realistic, payouts 10/7/5/4/3/2/1/0 | **+0.701 ± 0.094** | - | rival1 +0.005 -> +0.857 |
| realistic, payouts 50/25/12/6/3/2/1/1 | **+4.62 ± 0.64** | - | rival1 -0.32 -> +5.36 |
| **holdout** (measured once) | **+0.379 ± 0.057** | **+0.410 ± 0.065** | Hero - rival3 **-0.413 -> +0.151 ± 0.116**; **-0.369 -> +0.137 ± 0.112** |
| **top3** (measured once) | **+0.199 ± 0.075** | **+0.201 ± 0.079** | Hero - rival3 -0.293 -> +0.011; -0.245 -> +0.115 |

Targets:
- **T1 met** on realistic and on top, in both modes.
- **T7**: -0.196 strict (met on the point estimate), -0.264 under the model (not met).
- **T2**: rival1's room 4.65 (met); rival2's room 3.63 (not met).
- **T3 met**: base and strong both up.
- **T4 met**: act() p99 40 us with the layer and 32 us without, on real-table observations replayed three times,
  minimum per call; the layer costs ~7 us a decision. hand_end p99 63 us, new_table 73 us (top-heavy 514 / 525 us).
- **T5 met**: READY 23 of 23 (two_boards was PLAYS); Hero first on 22 of 23.
- **T6 met**: MicroAgent among seven Heroes 4.505.

**On either core** (160 x 8, model mode, panic off; the hybrid agent's `hybrid_x` / `hybrid3_x` against the plain
hybrids, paired):

| field | rival 2 core | rival 3 core |
|---|---|---|
| realistic | +0.253 ± 0.117 | +0.125 ± 0.089 |
| timeouts | +0.328 ± 0.094 | +0.181 ± 0.070 |
| top | +0.055 | +0.049 |

The rival 3 core already reads seats itself, and gains about half as much.

### What did not work, and the next lever

- **Isolation** never paid. The honest Monte Carlo heads-up is only a coin flip of a folder, and the other bots that
  limp are alive.
- **`dead_shift`** cost strong 0.05. The `recover_cut` in the first build biased the fold rates of part-time
  timers (0.59 read as 0.28) and is off.
- **The fold-read steal costs Hero in the one room where it should not fire: Hero + 7 rival2** (final -0.075 ±
  0.077, inside noise). Six tables of that room, per spot: `steal_fold` fires 2.2 hands a table, wins 42%, and nets
  -0.78 bb a hand (-1.7 bb a table); `bet_checked` there nets +1.0 bb a hand (+3.3 a table). Rival 2 folds most
  raises but defends its blinds by re-shoving.
- **Next lever:** read the blinds' fold to a steal specifically: the seat in the blind, facing one late-position raise
  with no callers, its own cell. Price `steal_min_fold` on that, not on folds to any raise. It is a change inside
  the layer, so every core gets it.

**For the hybrids.**
- With `HybridConfig.exploit` off, the fallback `HeroCore` the hybrid builds now carries Hero's shipped layer and
  reads the decisions routed to Hero. The hybrid's own `exploit="hero"` path turns that copy off.
- `test_hybrid3`'s check of `{}` was written against the old default: since `ExploitParams()` stopped being the
  shipped set, "{} = Hero's shipped params" means a layer exactly when `Config().exploit.active`. One line, 8a7af98.
- The hybrid comparisons so far are against the frozen Hero 7e51197. Hero at 8a7af98 is that Hero plus this layer.

## Hybrid 3 candidate (2026-11-01, builder: hybrid)

The plan change (HANDOFF, 04:00): choose the best decision core behind Hero's shell. This entry adds rival 3's core as
`hybrid3` and measures it against three bots: the frozen Hero (7e51197), Hero with the exploit layer as shipped
(1957983), and the rival 2 hybrid. Each core runs with and without the layer, and each candidate is judged once on rival 4's fields.
Which bot ships is the owner's decision. Running log with every table: `docs/drills/hybrid-log.md`.

**Read this first.** Sections 1, 2 and 4-5's left halves, and the first numbers of the verdict, are against
**pre-layer Hero**: the frozen 7e51197. Those comparisons are out of date for the core decision. The exploit layer has
since shipped as Hero's default (1957983, 8a7af98; coordinator, 07:30: Hero - rival1 +0.50 on realistic, Hero - rival3
on holdout from -0.41 to +0.15, 23/23 READY). Round 3 (section 3), the right halves of 4-5, timing (6) and the judge rows
(7) are against Hero at 0d660dc. Its `hyperion/strategy` is unchanged at HEAD, so that is current Hero with the shipped
layer, measured here in model mode with panic off. The core decision rests on the separate final comparison of Hero at
HEAD, hybrid_x, hybrid3_x and raw rival3 on the same deals and the judge fields. These numbers do not depend on Hero's
version: hybrid3 against raw rival3, the shell's behaviour on the twists, the layer's overlap with rival 3, and timing.

### What it is (4973806, cb51fae)

- **The core.** `hyperion/hybrid/core3.py`: `Rival3Core` subclasses rival 3's `Bot`; rival3.py is not edited.
  - Rival 3's one ICM method, `_allin` (20 lines), is re-implemented with `Rules.payouts`. It uses rival 3's O(n)
    closed form, generalised to any payouts linear from third place down (8..1 and the brief's table), and Hero's
    exact `icm_me` otherwise (top_heavy).
  - Its bust value comes from the same table.
  - Rival 3's module globals are untouched, so a `rival3` opponent still plays as built (tested).
- **Same shell as `hybrid`.** One router serves both cores (`HybridConfig.core`) through one adapter.
  - The rival 2 hybrid's play is bit-identical across the refactor (563 decisions, same sha).
  - Ranks are remapped before the core sees cards.
  - 3-card and other unrepresentable tables go to Hero, as in v1.1, with counters.
  - hand_end passes the hand's history in the kit's shape.
  - A soft deadline falls back to Hero's cheap path, and SafeBot wraps it with Hero's settings.
  - New route `hero:core_none`: rival 3 returns nothing when the move it wants is illegal (a shove with only call or
    fold offered; as built it then folds). Hero decides those, about 1 per table.
- **The exploit layer** (`HybridConfig.exploit`, off by default; `hybrid_x` and `hybrid3_x` carry Hero's shipped params).
  - One `Exploit` instance sits in front of every decision, core or Hero. The fallback Hero's own copy is switched
    off, so no decision is observed twice.
  - The layer only replaces passive actions (a fold or check preflop, a check postflop). It cannot double an action
    the core already took.
  - Where rival 3's own exploitation overlaps the layer, the layer fires less and is worth less (below).
- **Tests.** `tests/test_hybrid3.py`, 34 tests: legality, all 23 catalogue entries with the expected routing, the
  rank-remap round trip, `icm_points` against `_icm1` and `icm_me`, payouts in `_allin`, the hand_end history, declines,
  the soft deadline, the layer composing once, and timing. Full suite green at each commit (timing flakes at load 30+
  re-run green).

### How it was measured, and why the protocol changed from the "Hybrid candidate" entry

- **Sample:** 200 duplicate seeds x 8 rotations, seed 7, paired per seed.
- **Points:** engine mode "model" with SafeBot panic off, for every Hero, Hero clone and hybrid. Other sessions swung
  the host from load 2 to 60 during these runs.
  - In strict mode, load moves the field's Monte Carlo and timeout bots' timeouts and every bot's SafeBot panic, so
    runs made at different times played different fields.
  - Mode "model" (72440a6) folds those bots by a modelled cost instead; the exploit pass screens with it.
  - Load still reaches rival 2's wall-clock sampler (in rival 2 and the rival 2 hybrids).
- **Timing:** strict mode, all candidates seated at one table.
- **Two worlds:**
  - Round 2 = 4973806 with `hyperion/strategy` at 7e51197: Hero, its clones and every fallback without the layer.
  - Round 3 = HEAD 0d660dc: Hero and its clones with the shipped layer.
  - Pairs are taken within a world. Across worlds, pairs are used only where no Hero clone sits at the table
    (realistic, the judge fields, the mirrors).

**1. The fields and the payout tables, without the layer (round 2), against the frozen Hero.** Rank among the
field's bot names in brackets.

| field | Hero 7e51197 (rank) | hybrid3 (rank) | hybrid3 - Hero | hybrid (rank) | hybrid - Hero |
|---|---|---|---|---|---|
| realistic | 5.528 ± 0.092 (2) | 5.984 ± 0.102 (1) | **+0.456 ± 0.126** | 5.526 ± 0.105 (2) | -0.002 ± 0.118 |
| top | 4.648 ± 0.102 (4) | 4.892 ± 0.100 (2) | **+0.244 ± 0.138** | 5.064 ± 0.111 (1) | **+0.415 ± 0.132** |
| top2 | 4.474 ± 0.102 (4) | 4.871 ± 0.115 (2) | **+0.397 ± 0.135** | 5.055 ± 0.105 (1) | **+0.581 ± 0.151** |
| strong | 5.132 ± 0.104 (1) | 5.458 ± 0.117 (1) | **+0.326 ± 0.143** | 5.129 ± 0.107 (1) | -0.003 ± 0.136 |
| realistic, brief 10/7/5/4/3/2/1/0 | 5.575 ± 0.144 (2) | 6.202 ± 0.170 (1) | **+0.628 ± 0.197** | 5.503 ± 0.163 (2) | -0.072 ± 0.188 |
| top, brief 10/7/5/4/3/2/1/0 | 4.281 ± 0.148 (3) | 4.448 ± 0.159 (2) | +0.167 ± 0.204 | 4.563 ± 0.147 (2) | **+0.282 ± 0.191** |
| realistic, top_heavy | 20.891 ± 0.879 (2) | 24.725 ± 1.015 (1) | **+3.834 ± 1.243** | 20.336 ± 0.925 (2) | -0.555 ± 1.116 |
| top, top_heavy | 13.600 ± 0.815 (3) | 14.724 ± 0.830 (3) | **+1.123 ± 1.097** | 14.753 ± 0.768 (3) | **+1.153 ± 1.055** |

**2. Raw `rival3` in Hero's seat** (the bestiary bot, no shell: the brief's payouts in its ICM, displayed cards,
folds where it declines; the kit adapter already passes it the hand's history), on the same deals as hybrid3:

| field | raw rival3 in Hero's seat | hybrid3 | hybrid3 - rival3 (paired) | Hero 7e51197 | rival3 - Hero |
|---|---|---|---|---|---|
| realistic | 5.897 ± 0.109 | 5.984 ± 0.102 | **+0.087 ± 0.058** | 5.528 ± 0.092 | **+0.369 ± 0.128** |
| top | 4.824 ± 0.104 | 4.892 ± 0.100 | +0.069 ± 0.098 | 4.648 ± 0.102 | **+0.175 ± 0.145** |
| top2 | 4.728 ± 0.110 | 4.871 ± 0.115 | **+0.143 ± 0.114** | 4.474 ± 0.102 | **+0.254 ± 0.132** |
| strong | 5.324 ± 0.125 | 5.458 ± 0.117 | **+0.134 ± 0.077** | 5.132 ± 0.104 | **+0.192 ± 0.146** |
| realistic, brief | 6.207 ± 0.171 | 6.202 ± 0.170 | -0.005 ± 0.011 | 5.575 ± 0.144 | **+0.633 ± 0.198** |
| top, brief | 4.493 ± 0.152 | 4.448 ± 0.159 | -0.045 ± 0.148 | 4.281 ± 0.148 | **+0.212 ± 0.200** |
| realistic, top_heavy | 25.035 ± 1.048 | 24.725 ± 1.015 | -0.310 ± 0.699 | 20.891 ± 0.879 | **+4.144 ± 1.266** |
| top, top_heavy | 14.710 ± 0.891 | 14.724 ± 0.830 | +0.014 ± 0.865 | 13.600 ± 0.815 | +1.109 ± 1.134 |

What the shell adds on plain hold'em:
- +0.07 to +0.14 on the default 8..1 table, beyond noise on realistic, top2 and strong;
- nothing on the brief's table (-0.005 ± 0.011), where rival 3's ICM is already exact;
- nothing measurable on top_heavy.

On plain hold'em, rival 3 by itself and the rival 3 hybrid make nearly the same decisions: the gain is the payout
correction. The shell's other value is the twists (section 5): rival 3 alone remaps no ranks and cannot play the 14
tables Hero takes.

**3. With the layer (round 3), against Hero HEAD.** The last three columns pair on realistic, where the deals and
opponents match round 2.

| field | Hero HEAD (rank) | hybrid3_x (rank) | hybrid3_x - Hero HEAD | hybrid_x (rank) | hybrid_x - Hero HEAD | Hero HEAD - Hero 7e51197 | hybrid3_x - hybrid3 | hybrid_x - hybrid |
|---|---|---|---|---|---|---|---|---|
| realistic | 5.967 (1) | 6.141 (1) | **+0.174 ± 0.128** | 5.790 (1) | **-0.177 ± 0.122** | **+0.439 ± 0.073** | **+0.157 ± 0.078** | **+0.265 ± 0.086** |
| top | 4.765 (3) | 4.949 (2) | **+0.183 ± 0.135** | 5.124 (1) | **+0.358 ± 0.143** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| top2 | 4.653 (3) | 4.870 (2) | **+0.217 ± 0.136** | 5.160 (1) | **+0.507 ± 0.167** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| strong | 5.299 (2) | 5.363 (1) | +0.064 ± 0.145 | 5.560 (1) | **+0.262 ± 0.142** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| realistic, brief | 6.308 (1) | 6.514 (1) | +0.206 ± 0.213 | 5.946 (1) | **-0.363 ± 0.202** | **+0.734 ± 0.134** | **+0.312 ± 0.141** | **+0.443 ± 0.163** |
| top, brief | 4.458 (3) | 4.672 (1) | +0.214 ± 0.215 | 4.817 (1) | **+0.359 ± 0.196** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |
| realistic, top_heavy | 25.818 (1) | 26.129 (1) | +0.311 ± 1.339 | 24.093 (1) | **-1.725 ± 1.171** | **+4.927 ± 0.966** | **+1.404 ± 0.946** | **+3.757 ± 1.006** |
| top, top_heavy | 15.322 (3) | 16.033 (2) | +0.711 ± 1.118 | 16.594 (1) | **+1.272 ± 1.194** | (Hero clones differ) | (Hero clones differ) | (Hero clones differ) |

How rival 3's own dead-seat logic overlaps the layer, in the layer's fires per table at the hybrid:

| field | bot | bet_checked | steal_fold | steal |
|---|---|---|---|---|
| realistic | hybrid3_x | 3.1 | 1.6 | 0.1 |
| realistic | hybrid_x | 3.1 | 6.7 | 0.7 |
| top | hybrid3_x | 2.4 | 1.1 | 0.0 |
| top | hybrid_x | 2.5 | 4.8 | 0.2 |
| strong | hybrid3_x | 2.6 | 1.8 | 0.1 |
| strong | hybrid_x | 2.8 | 8.0 | 0.8 |

Rival 3 already steals against folders, so the layer's fold-read steal fires a quarter as often on top of it. The
layer is worth +0.16 to hybrid3 on realistic, against +0.27 to the rival 2 hybrid and +0.44 to Hero. Betting when
checked to fires equally for every core.

**4. The mirrors** (uniform 4.50).

| room | Hero 7e51197 | hybrid3 | hybrid | hybrid3 - Hero | hybrid - Hero |
|---|---|---|---|---|---|
| candidate + 7 rival3 (candidate's points) | 4.312 ± 0.111 | 4.467 ± 0.070 | 4.996 ± 0.112 | +0.155 ± 0.136 | +0.684 ± 0.158 |
| rival3 + 7 candidates (rival3's points, lower is better) | 4.833 ± 0.101 | 4.531 ± 0.077 | 4.053 ± 0.111 | -0.301 ± 0.128 | -0.780 ± 0.148 |
| candidate + 7 rival2 (candidate's points) | 3.714 ± 0.099 | 4.084 ± 0.112 | 4.585 ± 0.082 | +0.370 ± 0.138 | +0.871 ± 0.125 |
| rival2 + 7 candidates (rival2's points, lower is better) | 5.108 ± 0.095 | 4.985 ± 0.111 | 4.437 ± 0.089 | -0.124 ± 0.144 | -0.671 ± 0.127 |

With the layer (round 3, against Hero HEAD):

| room (round 3, the layer on) | Hero HEAD | hybrid3_x | hybrid_x | hybrid3_x - Hero | hybrid_x - Hero |
|---|---|---|---|---|---|
| candidate + 7 rival3 (candidate's points) | 4.508 | 4.484 | 4.924 | -0.024 ± 0.139 | **+0.416 ± 0.148** |
| rival3 + 7 candidates (rival3's points, lower is better) | 4.626 | 4.564 | 4.300 | -0.062 ± 0.137 | **-0.326 ± 0.151** |
| candidate + 7 rival2 (candidate's points) | 3.689 | 4.005 | 4.381 | **+0.315 ± 0.132** | **+0.691 ± 0.141** |
| rival2 + 7 candidates (rival2's points, lower is better) | 5.026 | 4.949 | not run | -0.077 ± 0.150 | - |

**5. The 23 twists** (variant_matrix.py's rules, `--field realistic`, 200 unrotated tables per entry, seed 7, model
mode, panic off; the candidate in Hero's seat of the same tables).
- Without the layer:
  - hybrid3: READY 22, PLAYS 1 (bounty, which is Hero's own table and row), first on 16.
  - Hero 7e51197: READY 22, PLAYS 1 (bounty), first on 11.
  - Core-routed rows, hybrid3 - Hero: permuted_ranks **+0.65 ± 0.37**, swap_holdem **+0.59 ± 0.38**, fast_schedule
    **+0.41 ± 0.36**; antes +0.28, pot_limit +0.23, bonus_card +0.21, swap_one_turn +0.19 and top_heavy +1.12 ± 3.39
    are inside noise, and straddle -0.18 ± 0.34.
- With the layer:
  - hybrid3_x and Hero HEAD are both READY 23, first on 22.
  - Every core-routed row is inside noise: -0.18 (straddle) to +0.18 (permuted_ranks), with top_heavy -2.70 ± 3.68.
- Every Hero-routed row is +0.00 ± 0.00 in both comparisons. With nothing reading the wall clock, the shell plays
  those 14 tables bit for bit as Hero does.
- The rival 2 hybrid's last matrix (v1.1 against Hero 7e51197, strict, load 5-35, "Hybrid candidate") was READY 23,
  first on 13.

**6. Timing, strict, every candidate at one table** (hybrid, hybrid3, Hero HEAD, hybrid3_x, rival1, rival2, pushfold,
tag; 200 seeds x 8, SafeBot as shipped; load 34 -> 26 from other sessions, the same for every seat):

| bot | p50 / p99 / mean us | over 1 ms | x Hero |
|---|---|---|---|
| Hero HEAD (layer) | 35 / 173 / 47.6 | 0.214% | 1.0 |
| hybrid3 | 34 / 176 / 48.3 | 0.224% | **1.0** |
| hybrid3_x | 43 / 223 / 60.9 | 0.289% | 1.4 |
| hybrid (rival 2 core) | 28 / 243 / 56.5 | 0.264% | 1.2 |
| rival1 | 25 / 121 / 35.1 | 0.164% | 0.8 |
| rival2 as built | 136 / 1033 / 201.4 | 1.024% | 4.8 |

Best-of-5 replay (each decision's minimum over five replays of the same recorded tables, the bot's own cost): hybrid3
mean 22.8 / p99 42 us, hybrid3_x 29.2 / 49, Hero HEAD 20.9 / 38, the rival 2 hybrid 33.9 / 157. Rival 3's core costs
what Hero's does; the layer in front of it adds ~6 us, which is the 1.4x. The wall-clock p99 test of hybrid3 that
failed half the time under load was measuring the host; it is now a best-of-replay cost test plus a same-table
timeout test (07:30 in the log). Panic in this run: every SafeBot here entered it in a few tables at this load (hybrid
family 796 decisions to Hero's cheap path across the three of them).

**7. The judge, once per candidate** (rival 4, 0d660dc; same protocol, load 27-49). `judge` = holdout with rival 4 in
rival 3's seat; `judge_top` = hero, rival1-4, pushfold, tag, loose_aggro. "Hero 7e51197" here is Hero HEAD with the
three shipped layer keys off (the exploit pass's stated equivalent), and the no-layer hybrids' fallback Hero runs
with its layer off too.

`judge`:

| candidate | points (rank) | - Hero 7e51197 | - Hero HEAD | candidate - rival4 | rival4 | load |
|---|---|---|---|---|---|---|
| Hero 7e51197 (no layer) | 5.707 ± 0.104 (1) | - | **-0.327 ± 0.078** | +0.032 ± 0.145 | 5.675 | 37-41 |
| Hero HEAD (layer) | 6.034 ± 0.111 (1) | **+0.327 ± 0.078** | - | **+0.379 ± 0.153** | 5.655 | 41-35 |
| hybrid | 5.505 ± 0.108 (2) | **-0.202 ± 0.126** | **-0.529 ± 0.133** | **-0.362 ± 0.144** | 5.867 | 27-34 |
| hybrid_x | 5.657 ± 0.111 (2) | -0.050 ± 0.134 | **-0.377 ± 0.138** | -0.125 ± 0.152 | 5.781 | 27-41 |
| hybrid3 | 6.094 ± 0.101 (1) | **+0.387 ± 0.133** | +0.060 ± 0.137 | **+0.501 ± 0.145** | 5.593 | 41-27 |
| hybrid3_x | 6.210 ± 0.096 (1) | **+0.503 ± 0.124** | **+0.176 ± 0.133** | **+0.657 ± 0.138** | 5.553 | 35-27 |

`judge_top`:

| candidate | points (rank) | - Hero 7e51197 | - Hero HEAD | candidate - rival4 | rival4 | load |
|---|---|---|---|---|---|---|
| Hero 7e51197 (no layer) | 4.599 ± 0.111 (5) | - | **-0.215 ± 0.111** | -0.052 ± 0.156 | 4.651 | 34-49 |
| Hero HEAD (layer) | 4.814 ± 0.111 (2) | **+0.215 ± 0.111** | - | **+0.165 ± 0.156** | 4.649 | 41-46 |
| hybrid | 4.933 ± 0.103 (1) | **+0.334 ± 0.140** | +0.119 ± 0.142 | **+0.298 ± 0.149** | 4.635 | 47-47 |
| hybrid_x | 5.128 ± 0.103 (1) | **+0.529 ± 0.134** | **+0.314 ± 0.128** | **+0.581 ± 0.144** | 4.548 | 47-44 |
| hybrid3 | 4.869 ± 0.106 (3) | **+0.270 ± 0.138** | +0.055 ± 0.138 | **+0.289 ± 0.159** | 4.580 | 49-47 |
| hybrid3_x | 4.927 ± 0.108 (2) | **+0.328 ± 0.134** | +0.113 ± 0.131 | **+0.404 ± 0.150** | 4.523 | 46-47 |

### All candidates

| candidate | realistic | top | top2 | strong | judge | judge_top | realistic brief | realistic top_heavy | top brief | top top_heavy | alone among 7 rival2 | twists READY / PLAYS | p50 / p99 us, over 1 ms (x Hero), strict, one table |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Hero 7e51197 (no layer) | 5.53 | 4.65 | 4.47 | 5.13 | 5.71 | 4.60 | 5.57 | 20.89 | 4.28 | 13.60 | 3.71 | 22 / 1, first 11 | - |
| Hero HEAD (layer) | 5.97 | 4.77 | 4.65 | 5.30 | 6.03 | 4.81 | 6.31 | 25.82 | 4.46 | 15.32 | 3.69 | 23 / 0, first 22 | 35 / 173, 0.214% |
| hybrid (rival 2 core) | 5.53 | 5.06 | 5.06 | 5.13 | 5.50 | 4.93 | 5.50 | 20.34 | 4.56 | 14.75 | **4.59** | 23 / 0, first 13 (strict) | 28 / 243, 0.264% (1.2x) |
| hybrid_x (+ layer) | 5.79 | **5.12** | **5.16** | **5.56** | 5.66 | **5.13** | 5.95 | 24.09 | **4.82** | **16.59** | 4.38 | - | - |
| hybrid3 (rival 3 core) | 5.98 | 4.89 | 4.87 | 5.46 | 6.09 | 4.87 | 6.20 | 24.72 | 4.45 | 14.72 | 4.08 | 22 / 1, first 16 | 34 / 176, 0.224% (1.0x) |
| hybrid3_x (+ layer) | **6.14** | 4.95 | 4.87 | 5.36 | **6.21** | 4.93 | **6.51** | **26.13** | 4.67 | 16.03 | 4.00 | 23 / 0, first 22 | 43 / 223, 0.289% (1.4x) |
| raw rival3 (reference, no shell) | 5.90 | 4.82 | 4.73 | 5.32 | - | - | 6.21 | 25.03 | 4.49 | 14.71 | - | plays none of the 14 | - |

Bold is the best of the six candidates in the column (the raw rival 3 row is a reference, not a candidate).
Points are on each table's own scale (uniform 4.50; 4.00 for the brief's table; 12.5 for top_heavy), 200 seeds x 8,
on the same deals. Every column but top, top2 and strong seats the same opponents for every candidate. In those three
the Hero clones (hero_tight, hero_loose) are the candidate's own world: without the layer for the first, third and
fifth rows, with it for the second, fourth and sixth. Read those three columns within a world (sections 1 and 3 give
the paired deltas). Twists: READY / PLAYS on the 23 entries in model mode, except the rival 2 hybrid's, which is the
strict run of "Hybrid candidate"; hybrid_x's matrix was not run.

### Verdict

**Rival 3's core is the better of the two cores behind Hero's shell, and the only candidate ahead of Hero by more than
noise on the realistic room and on the judge.**

Without the layer, hybrid3 against the frozen Hero:
- realistic +0.46 ± 0.13, strong +0.33 ± 0.14, top +0.24 ± 0.14, top2 +0.40 ± 0.14;
- judge +0.39 ± 0.13 (measured once); judge_top +0.27 ± 0.14;
- realistic under the brief's table +0.63 ± 0.20, under top_heavy +3.8 ± 1.2;
- first on 16 of the 23 twists against Hero's 11, and worse beyond noise on none.

With the shipped layer on both sides, hybrid3_x against Hero HEAD:
- realistic +0.17 ± 0.13, judge +0.18 ± 0.13, top +0.18 ± 0.14, top2 +0.22 ± 0.14;
- strong +0.06, judge_top +0.11 and every payout row are inside noise but none below zero;
- all 23 twists READY for both, first on 22 for both.

The aggression pass and the exploit layer closed most of the gap. Hero HEAD is +0.44 over the frozen Hero on realistic and
+0.33 on the judge, and the layer is worth less on top of rival 3 (+0.16), because rival 3 already steals from folders.

The rival 2 hybrid is the strongest bot in the rival rooms: top +0.36, top2 +0.51, judge_top +0.31 against Hero HEAD,
with the layer. It also holds uniform alone among seven rival 2s or seven rival 3s. But it loses realistic (-0.18 ±
0.12) and the judge (-0.38 ± 0.14) to Hero HEAD, and it times out 1.2x as often as Hero at one table here (1.5-3x in round 1).

Raw rival 3 against hybrid3 answers the owner's question. On plain hold'em they make nearly the same decisions. The
shell's correct payouts add +0.07 to +0.14 on the default table and nothing on the brief's, which is rival 3's own.
The shell also lets rival 3's core play all 23 twists, 14 of them as Hero.

On timing, at one table in strict mode, hybrid3 times out as often as Hero HEAD (1.0x), hybrid3_x 1.4x, the rival 2
hybrid 1.2x, and rival 2 as built 4.8x. Best-of-replay costs: hybrid3 23 us mean, Hero 21.

**The comparisons against the frozen 7e51197 are out of date for the core decision.** Round 3 and the judge rows are
against current Hero code (0d660dc, unchanged at HEAD) with the shipped layer. The separate final comparison (Hero at
HEAD, hybrid_x, hybrid3_x, raw rival3, the judge fields, on the same deals) is the one the decision should rest on.

### Recommendation (the decision is the owner's)

If the owner switches cores, the measurements point to **hybrid3_x**: rival 3's core with the shipped exploit layer
behind Hero's shell.

Against the plan's criteria (HANDOFF, 04:00):
- **Best on realistic:** yes. 6.14 against Hero HEAD's 5.97 and hybrid_x's 5.79.
- **Best on the rival-4 field:** yes on `judge` (6.21; +0.18 over Hero HEAD). On `judge_top` it is level with Hero HEAD
  (+0.11 ± 0.13), and hybrid_x leads there.
- **Best on top:** no. hybrid_x leads top (5.12 against 4.95), though hybrid3_x is ahead of Hero HEAD there (+0.18).
- **All 23 variants READY:** yes, first on 22, the same as Hero HEAD.
- **Robust across the three payout tables:** yes. At or above Hero HEAD on all six payout rows, and best of the six
  candidates on both realistic payout tables.
- **Timeouts no worse than Hero's:** hybrid3 yes (1.0x Hero at the same table); hybrid3_x no, by a little
  (1.4x: the layer's ~6 us in front of the core). If that matters, the layer's observe/override is the cost to trim.

No candidate meets every criterion. hybrid_x wins the rival rooms but loses realistic and the judge to Hero HEAD.

Switching is a one-name change: the entry builds `hyperion.hybrid.make_bot(overrides={"core": "rival3", "exploit":
"hero"})`, and tools/pack.py already copies `hyperion/hybrid/` and `hyperion/sim/rivals/rival3.py`. One cost to remove first:
`hyperion.hybrid` imports both cores today, so hybrid3 also pays rival 2's import (its import-time Monte Carlo, ~1.2 s
quiet and up to ~6 s on a loaded host, and a process-wide `gc.freeze()`). Rival 3 alone imports in ~20 ms. Splitting
the kit helpers out of `hybrid/core.py` and importing each core lazily fixes that without touching a decision. Before
an upload, tools/gate.py should play that zip; it has not been run with any hybrid.

The alternative is to keep Hero HEAD. It is 0.17-0.22 behind hybrid3_x on realistic, top, top2 and the judge, level
elsewhere, and its decisions are the ones the team has tuned and understands. That trade is the owner's call.

This recommendation is provisional: the separate final comparison decides between Hero HEAD, hybrid_x and hybrid3_x on
current code. Only round 3 and the judge rows here are against current Hero.

## Final core comparison (2026-11-01, builder: final comparison; verdict by the coordinator)

The one comparison the plan change (HANDOFF, 04:00) called for: which decision core ships behind Hero's shell. Five
candidates in Hero's seat on the same deals, seeds and opponents: Hero (with the shipped exploit layer), `hybrid_x`
(rival 2's core + layer), `hybrid3_x` (rival 3's core + layer), `hybrid3` (no layer) and raw rival 3 as a reference.
400 seeds x 8 rotations per field in model mode, strict mode on realistic and judge, the brief's and top_heavy payout
tables at 200 x 8, and all 23 variants for Hero and hybrid3_x. Code at `ac2db3e`; nothing was edited. Every table:
`docs/drills/final-comparison-log.md`. The measuring agent stopped after the variant run; the coordinator ran the last
two analysis scripts on its saved samples and wrote the verdict.

**Result.** hybrid3_x is first or second on every field and ahead of Hero on every field, paired:

| Field | hybrid3_x - Hero | hybrid_x - Hero |
|---|---|---|
| judge (rival 4, measured once) | **+0.14 ± 0.10** | **-0.35 ± 0.10** |
| judge_top | +0.06 ± 0.10 | **+0.30 ± 0.10** |
| realistic | **+0.10 ± 0.09** | **-0.28 ± 0.09** |
| realistic, strict | **+0.13 ± 0.09** | **-0.27 ± 0.10** |
| judge, strict | +0.07 ± 0.10 | **-0.37 ± 0.10** |
| top | **+0.14 ± 0.10** | **+0.31 ± 0.10** |
| top2 | **+0.14 ± 0.10** | **+0.39 ± 0.10** |
| strong | +0.07 ± 0.10 | **+0.17 ± 0.11** |
| timeouts | **+0.11 ± 0.09** | **-0.41 ± 0.09** |
| brief's table, realistic / judge | +0.23 / +0.19 | -0.35 / -0.55 (both beyond noise) |
| top_heavy, realistic / judge | +0.38 / +0.80 | -2.6 / -3.2 (both beyond noise) |

Bold is beyond the 95% interval. Variants: both 23 of 23 READY, first on 22, zero exceptions; 14 entries route the whole
table to Hero, and on the other nine the deltas are all inside noise (seven ahead, two behind). Timing: on a quiet host
hybrid3_x times out on 0.007% of decisions against Hero's 0.006%, p99 94 against 73 µs; under load 12-34 it crosses
1 ms on 0.19% against 0.13%. No candidate panicked a table.

**Decision.** Recommend shipping hybrid3_x; the owner makes the call. hybrid_x is the best bot in rooms full of strong
bots and the worst in the rooms the event will look like, beyond noise on the judge. Hero stays the fallback and the
shell. Before hybrid3_x ships: import each core lazily, so a hybrid3 package does not load rival 2's core (1.2-6 s at
import); pack it; pass `tools/gate.py` on the zip; re-check timeouts strict on a quiet host.

## Ship hybrid3_x as the base (2026-11-01, builder: base switch)

The owner approved hybrid3_x (rival 3's decision core plus the exploit layer behind Hero's shell) as the shipped
base after the final core comparison. This pass makes the night's pipeline pack, check and upload it, with Hero
one flag away. Commits b11b3f4 to 1774e4a. Measured on a host shared with a heavy session (load 9 to 60 on 8
cores); every point comparison is in model mode, paired on the same seeds.

**What changed.**
- *Lazy imports* (`hyperion/hybrid/`). Each core is imported on first use (`bot.CORES`, `core_class`); the kit
  helpers moved to `hybrid/kit.py`. A hybrid3 package no longer loads rival 2's module, which runs a Monte Carlo
  and `gc.freeze()` at import. Building hybrid3_x in a fresh `python -I` from another directory on a quiet host
  (load 1-3) went from 1.45-1.69 s to 0.27-0.31 s (Hero 0.24 s). A test checks rival 2 stays out of `sys.modules`.
- *One switch* (`hyperion/ship.py`): `SHIP = "hybrid3_x"` and `DIALS = {}`. `make_bot()` builds it, and every
  tool follows it:
  - the entry and the reference adapters (`_default_bot`);
  - `tools/pack.py` (`--bot` / `--dials`), which writes the pair it packed into the package's own copy of the file
    and builds that bot once in its fresh-process probe;
  - `tools/gate.py`, which reads that record and seats the same bot in-sim as its paired baseline, not Hero
    (`--bot` / `--dials` override; `--hero-config` keeps its old meaning);
  - `tools/gate_host.py`'s direct baseline and `tools/latency.py` (`--bot ship` is the default);
  - `python -m hyperion.sim --field <field>@ship --dials ...`. This takes four lines in `hyperion/sim/runner.py`,
    which no agent owns. The runner also takes `<field>@<bot>` for any registered bot, and an unknown field is
    now an argparse error.
- *The core's dials* (`hyperion/hybrid/dials.py`, `r3.<name>`). Rival 3's `_pre`, `_post` and `_rates` are copied
  into `core3.py` with twelve literals named as knobs: open widths (all positions, the cutoff and button),
  push/fold depth and margin, commit depth, committing-call margin, 3-bet range, bluff rate, postflop call edge
  and raise threshold, read prior, dead-seat hands. At the defaults every decision is bit-identical to rival 3's
  own methods (whole-table digests in `tests/test_ship.py`). One dials dict reaches the whole bot:
  - flat HybridConfig fields;
  - `r3.*` for the core;
  - `exploit.*` for the layer, or `{"exploit": null}` to turn it off;
  - `hero.<key>` for the fallback Hero;
  - `cheap` (every decision Hero's cheap path).

  A bare Hero key on the hybrid is an error, because it would move only the decisions Hero takes. CONTRACTS.md
  lists every key with its meaning.
- *Docs.* Prompts 02-06, PLAYBOOK stages 2-6, section 0 ("What we ship") and section 5, the NIGHT template, the
  prompt README and the API card all follow the switch:
  - Stage 2's entry already builds `hyperion.ship.make_bot()`, packed with `--bot cheap`, so Stage 4 is a repack
    of the same entry rather than an edit.
  - A docs test checks that every dial the night docs name exists in CONTRACTS.md.
- *Found in the rehearsal* (below):
  - `NoLogSeat` and `gate.py --kit-log auto|yes|no`;
  - `Adapter.hand_end(..., history=, deltas=)`, with deltas sized to the table;
  - a history rebuilt from the bets is flagged (`extras["history_from_bets"]`) and reaches rival 3's core as none;
  - `gate.py` drops `tools/` from `sys.path` (the field agent's `tools/profile.py` shadowed the stdlib; since renamed).

**Pack and gate.** The hybrid3_x zip with fake kit A's reference entry:
- 854 KB (89 files, 3.8 MB unpacked, not slim);
- entry import 0.03 s plus bot build 0.43 s in pack's probe (load 12), and import plus `Agent()` 0.34-0.38 s from
  another directory at load 50;
- `tools/gate.py --kit a --tables 100`, strict, load 9-10: **GATE PASS**, package 5.81 ± 0.40 against hybrid3_x
  in-sim 6.03 ± 0.42, paired **-0.22 ± 0.48**; 0 exceptions, 0 illegal; package timeouts 0.07% of decisions, p99
  206 µs. Drill 6's fixed Hero package measured -0.22 ± 0.40 on the same gate.

**Latency** (`tools/latency.py --n 2000`, at load 50):

| bot | bot p50 / p99 | over 1 ms | kit B round trip p99 | over 1 ms |
|---|---|---|---|---|
| hybrid3_x | 32 / 123 µs | 0.15% | 170 µs | 0.20% |
| Hero | 24 / 92 µs | 0.15% | 118 µs | 0.15% |

The quiet-host strict check the final comparison asked for could not be made today: the host never got quiet.

**The dials** (paired, model mode, 200 tables, seed 7, realistic unless named; the ship bot in Hero's seat with
panic off):

| dial | what moved (base -> dial) | points, paired | busts, paired |
|---|---|---|---|
| `r3.open_scale` 1.25 / 0.8 | opens 51.6% -> 54.6% / 49.5% | -0.16 ± 0.23 / -0.17 ± 0.21 | +4.0 / +3.5 ± 6 |
| `r3.open_late_scale` 1.3 | cutoff and button opens 57.7% -> 61.4% | -0.09 ± 0.15 | +1.0 ± 5.0 |
| `r3.short_bb` 12 | shoves at 10-12 bb 0% -> 40% | -0.04 ± 0.09 | +2.0 |
| `r3.push_margin` 0.01 / 0.03 / -0.01 / -0.03 | short-stack shoves 72% -> 65% / 22% / 76% / 79% | +0.00 / -0.03 / -0.05 / -0.12 ± 0.05-0.14 | ±0 to +1.5 |
| `r3.call_margin` 0.03 | calls of an all-in 16.2% -> 8.7% | -0.05 ± 0.08 | +2.5 ± 2.9 |
| `r3.commit_bb` 25 | 3-bets +0.7, shoves -2.8 | -0.02 ± 0.11 | +1.5 |
| `r3.three_bet_scale` 0.6 / 1.6 | deep 3-bets 6.3% -> 3.8% / 9.7% | -0.09 ± 0.20 / -0.03 ± 0.21 | +2.5 / +2.0 |
| `r3.bluff_scale` 1.4 / 0.6 | bets when checked to 55.8% -> 60.9% / 48.3% | -0.10 ± 0.16 / +0.01 ± 0.20 | +1.5 / 0 |
| `r3.call_edge` 0.16 / 0.18 | folds to a postflop bet 61.6% -> 67.5% / 70.1% | +0.01 ± 0.15 / +0.07 ± 0.20 | -1.0 / -3.0 ± 5 |
| `r3.raise_shift` 0.05 | raises of a postflop bet 4.7% -> 3.5% | -0.03 ± 0.07 | +0.5 ± 2.2 |
| `r3.prior_scale` 0.5, `timeouts` field | opens 55.9% -> 58.0%, late opens 56.8% -> 60.5% | +0.12 ± 0.18 | -4.5 ± 5.3 |
| `r3.dead_hands` 10, `timeouts` field | nothing measurable (opens -0.2) | -0.04 ± 0.05 | +0.5 |
| survival set (signal 1, below) | all-in calls 16% -> 10%, 3-bets 6.3% -> 4.4%, postflop folds 62% -> 67% | -0.04 ± 0.23 | +3.0 ± 5.9 |
| survival with `r3.push_margin` 0.03 | the same, plus short-stack shoves 72% -> 22% | -0.09 ± 0.24 | +3.5 ± 6.3 |
| passive set (signal 2) | late opens +3.6, bets when checked to +3.3 | -0.04 ± 0.17 | -0.5 ± 6.0 |
| Hero's strong-field set on the core, `top` (`r3.open_scale` 0.85, `r3.prior_scale` 0.5) | opens -3.2 | **-0.48 ± 0.33** | **+11.0 ± 7.5** |
| ... each half alone, `top` | opens -2.2 / late opens +1.6 | -0.05 ± 0.28 / -0.22 ± 0.30 | +0.5 / +7.5 |
| `cheap: true` | every decision Hero's cheap path (opens 12%) | **-1.86 ± 0.38** | **+32** |
| antes patch on antes_from_level_3 (`r3.open_scale` 1.15, `r3.short_bb` 12) | opens +1.6, 10-12 bb shoves 58% | -0.03 ± 0.19 | +4.0 |

What the dials table shows:
- Every dial moves play the stated way.
- No dial gains points beyond noise on our fields. Rival 3 as built sits near a local optimum there, so a window
  dial is an answer to tonight's standings, not a free improvement.
- Two of Hero's recipes are wrong on this core:
  - Hero's strong-field dial (tighter opens, faster reads) loses beyond noise on `top`. On the shipped bot that
    signal now says "keep the frozen bot".
  - Raising `r3.push_margin` for survival makes the short stack blind out (busts rose). The survival set leaves
    it alone. It is the steepest dial: step it by 0.01.
- `r3.dead_hands` hardly moves play even among timing-out bots; the reads' prior (`r3.prior_scale`) is the dial
  for dead seats.
- Antes need no dial on the core, which already prices them as dead money.

The windows table (PLAYBOOK section 5, prompt 06) carries these dicts, what each did, and Hero's keys alongside.

**Rehearsal: Stages 2 and 4 on fake kit B** (load 50-60; scratch `base_switch/rehearsal_b`). The submission was
the reference `KitBAdapter` subclassed unchanged, and an entry that builds `hyperion.ship.make_bot()` at import.
- Stage 2:
  - kit simulator, 50 hands, `HYPERION_CHECK=1`: 0 exceptions, 0 illegal, 69 observations with 0 violations, every
    action kind seen, 1 timeout (4 ms, the host);
  - `pack.py --bot cheap`: import 1.48 s, `bot cheap` recorded;
  - gate, 30 tables: PASS, -0.34 ± 0.35 against in-sim Hero.cheap().
- Stage 4:
  - kit simulator, 100 hands: 0 exceptions, 0 illegal, 0 violations. 3 timeouts in 284 decisions, each about
    4 ms of host stall at load 58, so the runner's 1% line failed;
  - strict sim `--field realistic@ship`, 100 tables: 6.11 ± 0.44, 0 exceptions, 0 illegal, p99 243 µs;
    timeouts 0.6% of hands at load 58 (the load clause);
  - latency through the adapter: p99 589 µs, a FAIL at load 58 (wall 139 ms against CPU 90 ms: preemption);
  - repack: `bot hybrid3_x` recorded, import 1.39 s, the NIGHT.md rows stamped "cheap: cheap bot" and
    "hybrid3_x: shipped bot".
- **The gate failed: -1.23 ± 0.81 at 60 tables.**
  - The cause is the kit, not the adapter or the switch. Kit B has no action log, and the in-sim baseline was
    fed the engine's full history.
  - A Hero package fails the same way: -0.83 ± 0.46. Drill 1's kit B package measured -1.22 in "Gate the
    packaged bot".
  - So on any kit without a log, Stage 4's gate would have blocked every upload.
  - Fix: on such a kit the baseline sees what the kit gives (`NoLogSeat`: the raises rebuilt from the bets, a hand
    end with only its own chip change), automatic for fake kits b, c and d and `--kit-log no` for tonight's.
  - The same zip then passes: **+0.31 ± 0.32 at 100 tables**.
- Flagging the rebuilt history so rival 3 reads none, rather than booking every raiser as a seat that raises every
  hand, moved nothing measurable (5.31 -> 5.30 at 60 tables). It stays as the honest input.

**Hero against hybrid3_x through the kits, and without a log.**

Package against package, 100 strict tables through each kit (seed 11):

| kit | hybrid3_x | Hero | hybrid3_x - Hero, paired |
|---|---|---|---|
| A (log) | 5.72 | 5.89 | -0.17 ± 0.48 |
| B (no log) | 5.21 | 5.39 | -0.17 ± 0.43 |

In-sim, model mode, 400 unrotated tables (seed 7), both bots in Hero's seat:

| field | with the log: hybrid3_x - Hero | through `NoLogSeat`: hybrid3_x - Hero |
|---|---|---|
| realistic | -0.05 ± 0.27 | -0.14 ± 0.23 |
| judge | +0.19 ± 0.26 | -0.12 ± 0.26 |

- Without a log, Hero loses 0.66 points a table on realistic and 0.60 on judge; hybrid3_x loses 0.75 and 0.91.
  Rival 3's core is the one built on reads.
- None of these differences is beyond noise. The final comparison's +0.10 to +0.14 (400 seeds x 8 rotations) is
  still the strongest evidence for a kit that gives the log.
- On a kit without a log the two bots are level, leaning Hero. That is the owner's call on the night. The tools
  make either a one-flag change.

**How to switch back.**
- For good: `SHIP = "hero"` in `hyperion/ship.py`. The entry, pack, the gate's baseline, latency and `@ship` all
  follow.
- For one package: `--bot hero` on pack. The gate then reads `hero` from the zip, and the sim line is
  `--field realistic`.
- Hero's Config keys are its dials, written bare (PLAYBOOK section 5's last column).

**How to register another ship bot.**
- A builder is one line in `BUILDERS`: name to `"module:function"`.
- The function takes `(dials: dict, seed: int | None)` and returns a bot with `new_table`, `act`, `hand_end` and
  `variant_decide`. It must import only from `hyperion/`, because pack vendors only `hyperion/` and `tables/`, and
  it should not need `hyperion/sim/bestiary.py` (`--slim` drops it).
- The compose agent's composite is already registered: `"composite": "hyperion.compose.bot:ship"`. Shipping it is
  the one line `SHIP = "composite"`, with its route and dials in `DIALS`.
- From then on the entry builds it, pack probes and records it, the gate pairs the zip against it in-sim, and
  `python -m hyperion.sim --field realistic@ship` and `tools/latency.py` measure it. `--bot composite` tries it on
  pack, gate and latency without changing SHIP.

**Unfinished, and the next levers.**
- The quiet-host strict timing check was not made: load never dropped below 9 after the first hour.
- An adapter for kits without a log that infers the actions between our decisions from the state (a seat whose
  active flag drops folded; a raised bet is a raise). The missing log costs 0.6-0.9 points a table, more than any
  dial, and more to the shipped bot than to Hero.
- A larger package-against-package run (400+ tables a kit) to resolve the ±0.45 above.
- `hyperion/sim/runner.py` took a four-line change; its owner, if any, should know.

## Ship hybrid3_x as the base: addendum (2026-11-01, builder: base switch)

**The switch is provisional.** On the new night-like fields (the field agent's measurements), hybrid3_x ties Hero
on `night` (-0.01 ± 0.12) and trails on `night_hard` (-0.17 ± 0.13). It still leads on realistic and the judges.
`SHIP` stays `hybrid3_x` for now, marked provisional in `hyperion/ship.py`, and the compose agent's final
measurement sets it: Hero, hybrid3_x or the composite. Nothing in PLAYBOOK or the prompts says which bot ships;
they say "the ship bot (see the switch)". The entry above is the record of the mechanism and of the measurements,
not of a settled choice.

**Both paths are gated.** Fake kit A, 100 strict tables, seed 11, each zip paired against the bot it records:

| zip | package | in-sim | paired | gate |
|---|---|---|---|---|
| hybrid3_x | 5.81 | 6.03 | -0.22 ± 0.48 | PASS |
| Hero (`--bot hero`) | 5.99 | 6.15 | -0.16 ± 0.40 | PASS |

Both had 0 exceptions and 0 illegal actions. The Hero package timed out on 0.09% of decisions, p99 169 µs, at
load 42.

**The window dials are recipes, so the prompts are right whatever the switch says.**
- `hyperion/ship.py` RECIPES names six: `survival`, `passive`, `dead_seats`, `strong_field`, `latency` and
  `timeouts`.
- `--dials <names>` on the sim, pack, gate and latency resolves them for the bot the switch (or `--bot`) names.
  Names stack with `+`.
  - On rival 3's core (hybrid3_x, hybrid3, the composite's base) a recipe is the core's dials, plus Hero's recipe
    as `hero.<key>` for the tables (or sections) Hero plays there.
  - On Hero it is Hero's Config keys.
- `python -m hyperion.ship` prints the switch; `--set <recipes>` keeps dials in it.
- Every recipe builds on hybrid3_x, Hero and the composite (`tests/test_ship.py`).
- Hero's recipes, checked the same way (paired, model mode, 200 tables):

| recipe | Hero keys | what moved | points | busts |
|---|---|---|---|---|
| `survival` (realistic) | `preflop.patience_deep` 0.3, `postflop.icm_margin` 0.15, `postflop.big_value_tier` 7, `preflop.three_bet_frac` 0.02 | 3-bets 4.5% -> 3.5% | -0.00 ± 0.16 | -0.5 ± 4.7 |
| `passive` (realistic) | `preflop.open_frac` 2 / 3 behind -> 0.66 / 0.48, `postflop.cbet_freq_ip_dry` 0.7 | late opens 52.5% -> 55.7%, opens +1.7 | -0.01 ± 0.15 | 0 ± 5.0 |
| `dead_seats` (`timeouts`) | `exploit.steal_min_fold` 0.5, `profiler_blend_n` 4 | opens 48.6% -> 58.2%, late opens 55.9% -> 70.0% | +0.10 ± 0.16 | -3.5 ± 5.3 |
| `strong_field` (`top`) | `preflop.open_frac_mult` 0.9, `profiler_prior_n` 1 | opens 46.5% -> 43.1%, late opens 62.3% -> 57.7% | +0.23 ± 0.24 | -5.0 ± 6.9 |
| previous dead-seat keys (`timeouts`) | `profiler_blend_n` 4, `profiler_dial_strength` 1.5 | nothing over 0.4 points | -0.06 ± 0.11 | +3.0 ± 3.7 |
| previous strong-field keys (`top`) | `preflop.open_frac_default` 0.08, `profiler_prior_n` 1 | nothing over 0.8 points | +0.02 ± 0.12 | -1.0 ± 3.1 |

- The old PLAYBOOK dials for those two signals barely moved Hero: `preflop.open_frac_default` applies only past
  seven seats behind. They are replaced.
- `strong_field` on rival 3's core stays empty: Hero's recipe measured -0.48 ± 0.33 there.

**Shipping the composite** is the one line `SHIP = "composite"` (`python -m hyperion.ship --bot composite`).
Its builder is registered, and the recipes resolve for it as for hybrid3_x. Its `r3.*` dials reach its base and
its `hero.*` dials reach its Hero member.

**Suite.** 771 passed, 2 skipped, 5 failed, none in files this pass touched:
- three p99-under-1 ms budget tests, whose failing bot changes from run to run at load 41-45;
- a night-field wall-clock test, which passed on re-run;
- `test_bots_survive_a_three_card_variant_with_permuted_ranks`. The bestiary grew to 33 bots, so its half-field
  tables now seat 17 at three hole cards: 56 cards, more than the deck holds. That one is for the bestiary's
  owner.

## Night field and skill profile (2026-11-01, builder: field)

Scope: hyperion/sim/bestiary.py, hyperion/sim/field/ (new), hyperion/sim/rivals/rival5.py, docs/drills/field/ (new),
docs/drills/redteam/ (rival 5), tools/skill_profile.py (new), docs/drills/skill-profile.md (new), and their tests.
Commits: `072a674` night and the Track B bots; `654ad45`, `abb3404`, `003ca48` the four persona bots; `0038639`
rival 5; `fbbac19` fixed-speed model mode; `3784948`, `9e3bb9d`, `16b81dc`, `2dacc75` the profile tool; then the
docs commit.

**The `night` field.** No fixed 8-bot field looks like the real room: whatever the student teams build in the hour,
seated eight at a time at random. So `night` is Hero's seat plus seven seats (`night.1` .. `night.7`). Each seat draws
a distinct bot from a weighted pool, using the table seed alone. The weights are a guess, stated so they can be argued
with (hyperion/sim/field/night.py has the reasoning):

| group | `night` | `night_hard` | members |
|---|---|---|---|
| one-hour agent builds | 40% | 45% | the four persona bots, the two Track B bots (persona bots weigh 2x in `night_hard`) |
| weak or broken | 30% | 10% | Monte Carlo bots that time out (heaviest), bots that break mid-table, station, random, maniac, nit, all-in, crashers |
| decent | 15% | 15% | tag, pushfold, loose_aggro |
| strong teams | 15% | 30% | rivals 1, 2 and 3 |

- *Why these shares.* Nearly every team has a coding agent and one hour, so agent builds are the room: 2.8 seats a
  table. The 1 ms clock and the hour break about two seats a table: pure-Python Monte Carlo overruns, state grows,
  placeholders ship. Teams with poker knowledge are about one seat, and so are competent chart bots.
- *The draw.* For each seat, pick a group by weight among the groups with an undrawn member, then a member by weight;
  no bot is drawn twice. Realised seats per table over 20,000 tables:
  - `night`: 2.81 / 2.11 / 1.05 / 1.03;
  - `night_hard`: 3.26 / 0.72 / 1.08 / 1.94 (strong runs short of 2.1 because the group has only three bots).
- *Pairing.* A pool seat reads the table seed from the seat seed the runner gives every bot. So every rotation and
  every `night@<bot>` swap sees the same seven opponents with the same seeds, in the same seats. Tests check this
  through the runner, plus the same draw in another process with another hash seed.
- *What is never in a pool:* Hero, its presets, the hybrids and composites, rivals 4 and 5, and `micro`.
- `night0` is the version shipped before the persona bots froze (only the two Track B bots in the agent group). It is
  kept so runs made on it can be repeated.
- The runner reports by seat name, so `night.3` mixes whatever sat in slot 3. Read the Hero seat. For the opponents,
  use `night.opponents()` or the profile tool.

**New bots in the pool.** All are our own agents' code, read first: none uses the network, a subprocess, exec or file
writes. Each is a frozen copy below an origin header, with the original archived in docs/drills/field/ and an md5 test.
- `agent_default` (md5 `cd47da88`, minute 45): what an agent builds when told only "build the strongest bot you can".
  A rule-based TAG.
- `agent_montecarlo` (`653c9c29`, minute 46): the Monte Carlo equity team. A 0.18 ms sampler, no charts, no ICM.
- `agent_charts` (`8d684a43`, minute 17): the live chart player. TAG charts from memory, no ICM, no reads.
- `agent_pushfold` (`d221bdd6`, minute 46): the ICM push/fold quants. Exact ICM, push charts from memory.
- `trackb3`, `trackb5`: drills 3 and 5's Track B uploads (`b40150c0`, `aeb14d3b`), on fake kits A and B.
- The builders' logs are docs/drills/field/agent_*.md.

**Adaptations.** Each one exists because we run every bot in one process.
- The persona bots play through `PersonaBot`, the red-team adapter, with the payouts and the hand's history passed
  (the brief allows both).
- `hyperion.sim.field.load` makes the brief's kit importable as `kit` while a persona loads (agent_default imports it
  with no fallback). It also turns the garbage collector back on after agent_montecarlo's `gc.disable()`.
- agent_montecarlo samples from its own seeded RNG per seat, not the global `random`.
- trackb3 plays with its bounty patch off, since plain hold'em pays no bounty.
- trackb5 reads its rank map from `Rules.rank_order`, so it is right on plain hold'em and under any permutation. It
  keeps its module-level state per seat.
- Two event-name words were dropped from the Track B docstrings for the public export; the export check reports 0
  hits.

**Rival 5, the second judge.** Built blind by a fresh team against the brief and kit (md5 `c0af68a4`, archived with
its builder's log), played through rival 4's adapter.
- Fields: `judge2` is `judge` with rival 5 in rival 4's seat (realistic-shaped, rival 5 in the holdout seat).
  `judge2_night` is Hero's seat, rival 5, and six drawn from the night pool. The candidate swaps are listed.
- Never tuned on and not measured here. The tests check legality, timing (skipped on an oversubscribed host), wiring
  and conservation. The compose agent measures it once, at the end.

**Mode `model` is now fixed-speed, so night replays exactly.** Five bots' play follows the wall clock: rival 2's
sampler, rival 5's sampler, agent_montecarlo's sampler, agent_pushfold's 260 µs guard, and rival 2's import-time
tables. On a host at load 40-60, that made fields with them differ run to run. `bestiary._FixedSpeedInModel` uses the
engine's existing `use_cost_model(True)` call at table start in mode "model" as the switch; strict and measure play
everything as built. `last_cost_ns` stays None, so these bots are never folded for time.
- rival 2: a fixed 110 samples, no budget, no hard stop (tools/swap.py's setting). It is also always imported with its
  clock held still, so its tables are the full 1500 boards at any load.
- rival 5: a clock that advances 4.0 µs per read.
- agent_montecarlo: a clock that advances 3.5 µs per read. Each value is the CPU time of the work between two clock
  reads on this box.
- agent_pushfold: its guard reads 0.
- **This changes the protocol:** model-mode runs on `top`, `top2` and `judge_top` used to play rival 2 with its
  wall-clock sampler. Tests show night and night_hard replaying exactly, every seat and rotation.

**Sanity check: the candidates on the night fields.** 200 seeds × 8 rotations, mode model, code at `00efa2c`. Each bot
sits in Hero's seat of the same deals. Paired deltas against Hero, ± 95%.

| field | 1 | 2 | 3 | 4 |
|---|---|---|---|---|
| `night` | Hero 5.75 | hybrid3_x 5.75 (−0.01 ± 0.12) | hybrid_x 5.60 (**−0.16 ± 0.12**) | rival3 5.54 (**−0.21 ± 0.13**) |
| `night_hard` | Hero 5.39 | hybrid_x 5.38 (−0.01 ± 0.13) | hybrid3_x 5.23 (**−0.17 ± 0.13**) | rival3 5.17 (**−0.23 ± 0.15**) |
| `realistic` (100 seeds) | hybrid3_x 6.09 (+0.11 ± 0.18) | Hero 5.98 | rival3 5.91 (−0.07) | hybrid_x 5.71 (**−0.27 ± 0.18**) |

hybrid3_x leads Hero on `realistic`, as the final comparison found. It ties Hero on `night` and is behind beyond noise
on `night_hard`. A chip-flow split shows where (docs/drills/skill-profile.md has the tables). Each hand's net chips
for the bot in Hero's seat go to the opponents on the other side of it.
- On `night`, hybrid3_x wins +3.2 ± 2.7 bb a table more than Hero from the weak or broken seats (the two Monte Carlo
  bots). It wins −3.0 ± 2.4 less from the one-hour agent builds (mostly trackb3). Against the strong teams the
  difference is +1.4 ± 1.7. The two effects cancel.
- On `night_hard`, its gap is the strong teams: −4.9 ± 2.0 bb a table, about equally from rival 1 (−2.4), rival 2
  (−2.9) and rival 3 (−2.3). Against the persona and Track B bots it is −2.4 ± 2.8, inside noise.
- So it is not an effect of rivals 1 and 2, which Hero was tuned against. Rival 3 was never a Hero tuning target, and
  hybrid3_x gives up as much to it.
- hybrid_x is level with Hero on `night_hard` and ahead at tables with all three rivals (+0.27 ± 0.22).
- **Tuning caveat.** Hero was tuned against rivals 1 and 2 and most of the bestiary. The hybrids' exploit layer was
  screened on the same bestiary. Nobody tuned on the persona bots, the Track B bots or the judges. That is about 40% of
  the `night` seats, untuned for every candidate.

**The skill profile.** `tools/skill_profile.py` (named so, because `tools/profile.py` shadowed the standard library's
`profile` for every tool script; renamed in `9e3bb9d`) seats each bot in Hero's seat and books every decision to one
of the compose agent's twelve sections.
- Per section: share, VPIP, raise rate, aggression, all-in rate, showdown win rate, bust sections, and bb won per
  decision. A hand's net is split over the decisions that put chips in, pro rata; the rows add up to the net exactly.
  Each figure carries a 95% interval, with the seed as the unit.
- Ranked lists per section and per group are in docs/drills/skill-profile.md. They are descriptive, not causal: the
  swap test is the causal measure.

Headlines on `night`:
- *Deep preflop:* 1. hybrid3_x, 2. agent_montecarlo, 3. hybrid_x. Hero is 10th of 12.
- *Short stack:* 1. rival1, 2. agent_montecarlo, 3. rival2, 4. hybrid_x. Hero is 7th.
- *Endgame:* 1. hybrid3_x, 2. rival1, 3. rival3, 4. Hero.
- *After the flop:* 1. rival2, 2. hybrid_x, 3. agent_pushfold. Hero is 6th.
- Hero's plainest leak is facing a raise with 20+ bb, 17-19% of its decisions. It is last on both fields: −0.11 bb a
  decision on `night`, −0.17 on `realistic`. hybrid3_x is at +0.02 there.
- The owner's other bot was profiled from a snapshot as a black box, numbers only: `night` 4.86, 11th of 13;
  `realistic` 4.85, 12th of 13. Its run was at load 35-60, and it reads the wall clock.

**Also fixed.** `test_bots_survive_a_three_card_variant_with_permuted_ranks` now plays eight-seat tables. With 33 bots
registered, its two half-tables seated 17, which is 56 cards at three hole cards.

**Not done.**
- No measurement of anything against rival 5.
- No strict-mode night run: the host was at load 40-60 throughout, so strict timeouts would have measured the host.
- The pool weights are a guess. Re-weigh them when the regional's field is known.

## Infer the action log on kits without one (2026-11-01, builder: action-log inference)

**Why.** The base-switch rehearsal found that a kit with no action log costs both bots 0.6 to 0.9 points a table.
Their opponent reads go blind: Hero's raise counts and profiler, the exploit layer's fold streaks and dead or
timing-out seats, rival 3's seat reads. The real kit's interface is unknown. Fake kit B has no log; fake kit A has
one at our decisions but nothing after our last one. Every kit does show, at each of our decisions, each seat's
in-hand flag, chips behind, chips in this street and the pot. That is enough to rebuild the log.

**What landed** (598148d, bacce90, ca19c55, 4de1cfd, f2181b3 and the docs commit after this entry).
- `hyperion/drills/infer_history.py`, `HistoryInference`. It replays the engine's betting procedure with each
  seat's action as the unknown:
  - blinds and straddle posted, who still has to act, full and short raises, the order from the button;
  - between two of our decisions each other seat acts at most once a street, so the change settles it: out of the
    hand = fold, more chips to a new high = raise to that total, to the high (or all-in below it) = call, nothing
    more and still in where the order says it was asked owing nothing = check;
  - across a street change, the old street's last bets come from the chips behind;
  - every observation is checked against the state the walk predicts. An action the states do not settle is a gap,
    and the log stops there for the hand. Example: a big blind that owed nothing preflop and is out by our flop
    turn folded its free option or checked and folded to the flop bet; both fit.
  - our own reply is read back from the next state like any other seat's.
- Hand end. The bot's hand end carries the log up to our last decision and our reply as sent. The folds after it are
  added when the kit shows how the hand ended: every seat's deltas or final stacks, and the showdown. A seat that
  owed chips, put nothing more in and was not shown folded. With chip counts alone, only a whole fold-out to one
  seat with nobody all-in is accepted. A kit whose hand end says nothing still shows every seat's stack in the next
  hand's first state (`chips_after_hand`). So when some seat owed chips after our reply, `Adapter` holds the hand
  end and delivers it at the top of that decision, with every seat's deltas.
- `Adapter` (every reference adapter and entry, and the template) runs it on every decision.
  - `history_source = "log"`: the kit's log as it is. `"partial"`: some actions, merged where they overlap the
    rebuilt prefix. `"bets"`: none; make_observation's raises-from-bets stand-in is dropped.
  - Kit D's round end goes through it with every delta and the shown hands.
  - The night-of agent writes no history code.
- `tools/gate.py --kit-log no` (auto for fake kits b, c, d) seats the in-sim baseline behind `InferSeat`, the same
  rebuild on the bare states (kit d: with its deltas and showdowns). An upload that loses the rebuild now fails.
  `--kit-log bets` keeps the old `NoLogSeat` baseline for packages from before it.
- Conformance checks the history the bot reads: `history_infer` (it must explain the bets unless it stopped at a
  gap, and grow within a hand) and `history_gap` (gaps in more than 5% of hands: the state translation disagrees
  with the betting). The demo's pot-includes-bets adapter stops at a gap in 25 of 50 hands.
- `python -m hyperion.drills.infer_eval`: the paired measurement below, and `--check` for precision and recall.

**Correctness** (the rebuilt log against the engine's, on real sim tables; `--check`, hand end as the adapter gets
it on a kit that says nothing):

| field / bot (40 tables) | decision entries | false | recall at decisions | hand-end entries | false | hand-end recall: preflop / flop / turn / river |
|---|---|---|---|---|---|---|
| realistic / Hero | 24,400 | 0 | 100% every street | 21,847 | 0 | 75.5 / 53.5 / 45.4 / 33.2% |
| realistic / hybrid3_x | 19,213 | 0 | 100% every street | 19,480 | 0 | 74.0 / 43.2 / 35.3 / 24.9% |
| night / Hero | 27,416 | 0 | 100% every street | 24,614 | 0 | 75.4 / 57.5 / 50.9 / 40.3% |
| night / hybrid3_x | 23,294 | 0 | 100% every street | 23,467 | 0 | 75.0 / 47.7 / 41.5 / 34.0% |

- Precision is 100%: no entry it emitted was false. Hand end without holding it for the next state: preflop
  recall 63%; with every seat's deltas, 76%; with the showdown too, 83%.

- Property test (`tests/test_infer_history.py`): 160 random tables, 2 to 8 seats, any stacks, antes, straddles, no,
  pot and fixed limit, folds with a free check, odd raises and all-ins, from every seat, all four hand-end modes:
  no false entry.
- Kit B end to end (engine, kit B's dict, KitBAdapter, the bot): the bot's log equals the engine's at every
  decision; held hand ends carry every seat's true deltas.
- Gaps: 0 in 4,500 sim hands; 1 in 50 on fake kit B's dealer (the big blind's free option above).

**What it wins back** (model mode, 200 seeds x 8 rotations, paired; the bot in Hero's seat):

| field / bot | no log | rebuilt | full log | the log's cost | won back | left |
|---|---|---|---|---|---|---|
| realistic / Hero | 5.27 | 5.93 | 5.97 | 0.70 ± 0.10 | **+0.66 ± 0.10 (95%)** | 0.04 ± 0.08 |
| realistic / hybrid3_x | 5.21 | 6.07 | 6.13 | 0.92 ± 0.13 | **+0.86 ± 0.12 (94%)** | 0.06 ± 0.10 |
| night / Hero | 5.20 | 5.68 | 5.75 | 0.56 ± 0.09 | **+0.48 ± 0.10 (86%)** | 0.08 ± 0.09 |
| night / hybrid3_x | 5.17 | 5.70 | 5.75 | 0.58 ± 0.13 | **+0.53 ± 0.13 (92%)** | 0.05 ± 0.10 |

"No log" is `NoLogSeat` (the gate's baseline before this: the street's raises from the bets, a bare hand end);
"rebuilt" is `InferSeat` on the same bare states, the hand end held as the adapter holds it; "full log" is the
engine's. The won-back and left columns are paired, seed for seed.

- With the rebuild, the two bots compare on a no-log kit as they do with the log. hybrid3_x - Hero on realistic:
  -0.06 ± 0.13 with no log, +0.14 ± 0.12 rebuilt, +0.17 ± 0.13 with the full log. On night: -0.03, +0.03, -0.01,
  all ± 0.12. The rehearsal's caveat (on a kit without a log the bots are level, leaning Hero) no longer holds.

- The rebuild wins back 86% to 95% of what the missing log cost. What is left is within noise on every row.
- Holding the hand end for the next state adds 0.08 to 0.25 of it. Without the hold (`infer_none`: the hand end at
  once, with the log up to our reply) the rebuild wins back 58% to 79% (Hero 0.41 / 0.32, hybrid3_x 0.66 / 0.46 on
  realistic / night).
- Holding every hand end (`infer_all`, every seat's deltas every hand) gains nothing over holding only those
  where a fold can be settled. So `hold_all` stays off.

**Cost.** Measured through KitBAdapter on real tables at load 5:
- the inference is 12 µs a decision at the median, p99 40-50 µs;
- a held hand end runs the bot's own hand end (Hero's ICM curve, the profiler's dials, rival 3's replay) inside the
  next hand's first decision: 55-80 µs median, p99 130-240 µs, on about 70% of the hands we act in (those where a
  seat owed chips after our reply; hybrid3_x 1,363 of 1,913).
- `defer_hand_end = False` moves it back outside the clock and gives up the 0.08 to 0.25 above. Do that if the
  gate's timeouts say so.

**Gate** (fake kits, 100 strict tables, seed 11, the reference entries packed from 4bbd794):

| zip (hybrid3_x, reference entry) | kit | baseline in-sim | package | baseline | paired | timeouts, p99 | gate |
|---|---|---|---|---|---|---|---|
| `make_kit_b_module()` | B, no log | the rebuild (`InferSeat`) | 6.09 | 6.15 | -0.06 ± 0.34 | 0.03%, 300 µs | **PASS** |
| `KitAAgent` | A, log at our decisions | the full log | 6.03 | 6.23 | -0.20 ± 0.55 | 0%, 256 µs | **PASS** |
| kit B with the rebuild switched off | B, no log | the rebuild | 5.53 | 6.33 | **-0.80 ± 0.52** | 0%, 99 µs | **FAIL** |

- 0 exceptions and 0 illegal actions on all three; load 6. The base-switch rehearsal's hybrid3_x zip scored 5.21 through
  kit B on the same seed and field; this one 6.09.
- The third row is the check that the gate now catches an upload whose adapter drops the rebuild.

**Limits.**
- Gaps stop the log for the rest of the hand; they are rare on the engine's rules. A kit whose dealer differs (dead
  button, blinds in the log, a seat asked with nobody left to bet into) shows up as gaps, and conformance names it.
- After our last decision only folds are settled, and only up to the first seat that put more in. Hand-end recall
  preflop is about 75%; the rest are unknown, never guessed.
- The partial-log merge needs the kit's entries to overlap the rebuilt prefix by at least one entry.
- Variants that change chips mid-hand were not in the measurement. Payouts at hand end are safe: the fold-out test
  then fails and nothing is added.

**Not done.**
- No quiet-host strict timing of a held hand end inside the decision clock.
- Track B's spec keeps its own no-history clause; it was not changed.

## Composite bot (2026-11-01, builder: compose)

Brief (HANDOFF, 13:45): find, for each section of the game, whether another bot's decisions beat the base's; combine
the winners; run a guarded hill climb; measure once on both judges; ship only if the result beats hybrid3_x. At 14:50
the coordinator widened the rule: the composite must beat both hybrid3_x and Hero beyond noise on night, be no worse
than either beyond noise on night_hard, realistic and top, and lose to neither on the judges. Running log with every
table: `docs/drills/compose-log.md`.

**What shipped (d32d629): `SHIP = "composite"`, called F below.**
- Preflop, rival 3's core plays, the hybrid3_x base.
- Hero plays every postflop decision, and preflop when facing a raise short (under 20 bb effective, four or more
  players alive).
- The exploit layer sits in front of both. Two dials came out of the climb: the layer bets when checked to at a fold
  read of 0.4 (was 0.5), and Hero calls a postflop bet only with 0.20 equity to spare (was 0.15).

`hyperion.ship.make_bot()` builds it: `composite` with no dials is F (`hyperion.compose.bot.SHIP_DIALS`).
hybrid3_x and Hero are each one word away.

**Final numbers, measured once** (400 x 8, model mode at fixed speed, F against both bases on the same deals). The
judges ran on seeds 0-399, the guard fields on held-out seeds 5000-5399.

| field | F - hybrid3_x | F - Hero |
|---|---|---|
| judge (rival 4) | **+0.30 ± 0.08** | **+0.43 ± 0.09** |
| judge_top | +0.09 ± 0.09 | **+0.17 ± 0.10** |
| judge2 (rival 5) | **+0.33 ± 0.08** | **+0.42 ± 0.09** |
| judge2_night | **+0.23 ± 0.08** | **+0.27 ± 0.09** |
| night | **+0.28 ± 0.08** | **+0.33 ± 0.08** |
| night_hard | **+0.29 ± 0.09** | **+0.32 ± 0.09** |
| realistic | **+0.28 ± 0.08** | **+0.42 ± 0.08** |
| top | **+0.16 ± 0.09** | **+0.35 ± 0.09** |

Bold is beyond the 95% interval. Other checks:
- **Variants:** 23 of 23 READY, first on 22. Level or ahead of hybrid3_x on every entry but lowball (-0.07 ± 0.07).
- **No action log:** with the log rebuilt by the adapters' inference, P (F before the climb) still beat both, beyond
  noise: +0.22 / +0.18 on night, +0.37 / +0.33 on realistic.
- **Gate:** PASS on kit B (night, the log rebuilt, -0.06 ± 0.44) and on kit A (realistic, +0.02 ± 0.49).
- **Timing:** strict timeouts level with hybrid3_x on a quiet host (1 against 2 of ~270,000 decisions). p99 113 us at a
  table, 127 us through the kit B adapter, 329 us in the gate with the deferred hand end; hybrid3_x 80 / 88 / 239.
- **Repo checks:** full suite green; export 0 denylist hits.

**How it was found.**
1. *Sections* (`hyperion/compose/sections.py`). Twelve, read from the Observation in ~1 us:
   - preflop by players alive (heads-up, three-handed, four or more), by what we face (unopened, a raise, an all-in),
     and by effective stack (10 / 20 / 40 bb bands);
   - postflop: heads-up facing a bet, heads-up checked to, multiway.

   Each holds 1.3-23% of decisions.
2. *The composite* (`hyperion/compose/bot.py`). A route sends each section to a donor: a member bot, with or without
   the layer.
   - Every member in the route sees every observation and hand end; members not chosen still decide ("shadow"), or,
     where nothing they keep depends on it, only update their state ("light").
   - Rival 3's and Hero's "I raised preflop" flags follow the action actually taken.
   - With every section on one donor it plays bit-identically to that bot alone, for hybrid3_x, hybrid3, Hero, raw
     rival 1 and raw rival 3, and for hybrid_x once rival 2's clock is fixed.
3. *The swap matrix* (`tools/swap.py`, 200 x 8). An exact shortcut makes it cheap: a base run records where each donor
   would act differently, and only those rotations are replayed. It was run on realistic and night with hybrid3_x as
   the base, and on night with Hero as the base. Both matrices agree on the two big sections:
   - facing a deep preflop raise, rival 3's core beats Hero by ~0.14 (from either base);
   - facing a heads-up postflop bet, Hero beats the core: +0.09 from the hybrid3_x base, +0.19 from the Hero base.
4. *Sections do not add.* Hero's single swaps from the hybrid3_x base sum to about -0.19 on night, yet the two bases
   tie. Opening ranges and the postflop play behind them fit together, so combining was done by measuring whole
   routes.
5. *Greedy* on night, every route paired against both bases. P = Hero postflop plus Hero facing a raise short came out
   first (+0.22 / +0.22 on the screen seeds), and no further section change helped. P was confirmed on fresh seeds
   1000-1399: beyond noise over both bases on night, night_hard, realistic and top (+0.11 to +0.27).
6. *Guarded climb* from P.
   - 54 one-dial trials on night: rival 3's core dials, the layer's params, and Hero's postflop and re-shove dials.
     One trial passed the screen up and five went down, about what chance gives.
   - The best four were confirmed one at a time on fresh seeds 6000-6399. None was beyond noise on night alone.
   - Tested together once on seeds 7000-7399, two of them were beyond noise on night (+0.06) and better on realistic
     (+0.09) and top (+0.08). That pair is the only accepted step.
7. *The owner's other bot* was tried as a black box donor (scratch only, a snapshot matching its current dist). It won
   no section on night: worse beyond noise in 7 of 12, level in the rest. Nothing of it is used.

**Rankings by section** (night, hybrid3_x base; the first donor is the best, the base itself is level 0):
- **Hero beats the base in two sections.** Facing a heads-up postflop bet, Hero +0.09 is beyond noise. Facing a raise
  short, Hero +0.06 is inside noise.
- **The base is first or level in the other ten**, among Hero, rival 1, the rival 2 core, raw rival 3 and the base
  without the layer. Rival 1 and the rival 2 core are worse beyond noise in four and three sections.
- **Turning the layer off** costs 0.16 when checked to postflop, and nothing measurable anywhere else.

Every section's full list on night, on realistic and with Hero as the base is in the log.

**What it did not do.**
- The per-section matrices on night_hard, top and strong were stopped for the greedy step: the guard fields were
  measured on whole composites instead.
- Strong was not used as a guard under the widened rule.
- Hero's dials in the climb were replayed in full, not by the shortcut.

**Caveats.**
- The screens and greedy rounds reused seeds 0-199. Every adopted change was confirmed on fresh seeds, and the final
  row is on seeds used nowhere else.
- night_hard carries ~1.9 strong seats a table that Hero was tuned on. Night and judge2_night, whose opponents nobody
  tuned on, are the fields to weigh, and F leads on all three.
- Model mode now plays rival 2, rival 5, agent_montecarlo and agent_pushfold at a fixed speed. Top numbers here are
  not comparable with the final core comparison's top / top2 rows, which played rival 2 on the wall clock.
