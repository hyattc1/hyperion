# Decisions

Append only. Newest at the bottom. One paragraph each: what was decided, why, what it rules out.

## 2026-10-31 tooling and drills (builder: tools/drills)

- **Generation library lives in `snapcall/tablegen.py`, the CLI in `tools/gen_tables.py`.** The strategy
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
- **Reference submissions use hero when present, the cheap bot otherwise**; `SNAPCALL_DRILL_BOT=cheap` pins the
  cheap bot. Adapter tests set it so they measure translation, not hero's latency.
- **`hu_matrix.json` diagonal is set to 0.5 exactly and classes follow `all_hole_classes()` order**, matching
  what `strategy/tables.py` asserts. 1000 samples per cell (SE 1.6%), 160 KB.
- **Default samples raised from 10000 to 20000** after measuring 35 s for the whole default run on 7 workers;
  90 s buys half the standard error and still leaves three minutes of the five-minute budget on a 4-core laptop.

## Strategy layer (snapcall/strategy/, 2026-10-31)

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
  `snapcall.strategy.pushfold.build_pushfold_tables(tables)` after regenerating the matrix, or the
  hero solves it at load (~4 s) and writes it if the directory is writable.
- **Position = players still to act.** Preflop ranges are keyed by `behind` (7 = UTG eight-handed,
  2 = button, 1 = SB, 0 = BB), which stays meaningful as seats bust. All open/3-bet/call fractions
  are in `PreflopParams`; "top X" means `preflop_rank >= 1 - X` (combo-weighted midpoint percentile,
  same definition as `snapcall.tablegen`). Flat-calling an open counts the raiser plus one extra
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
