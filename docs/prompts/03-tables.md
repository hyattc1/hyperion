# Prompt 03: regenerate tables (minute 17; ONLY if the strength or information axis moved)

The rule sheet says the <strength | information> axis moved: <one line, e.g. "ranks permuted so that
displayed 2 is strongest" or "three hole cards, one discarded face up before the flop">.

1. Write `rules_tonight.json` matching `hyperion/core/types.py:Rules`: hole_cards, board_sizes,
   rank_order (displayed rank index -> canonical strength index, 13 entries), n_suits, blind_levels and
   hands_per_level from the rule sheet, payouts from the rule sheet, and any `extras` the variant
   presets in `hyperion/drills/variants.py` document for this twist. If a preset matches, start from it.
2. Run `python tools/gen_tables.py --rules rules_tonight.json --out tables/ --workers <cores>` with
   the default samples. Time box 5 minutes; if `--variant-check` projects longer, pass `--skip-matrix`
   and let Hero re-solve push/fold at startup instead.
3. Spot check and show me: the equity of the strongest and weakest preflop class heads-up (under
   permuted ranks the strongest class is the permuted pair), and that `python -c "from
   hyperion.strategy import tables; tables.load()"` succeeds.
4. If hole cards are not two: the generator writes `hole_classes.json` describing the class scheme it
   chose. Confirm `hyperion/strategy/preflop.py` reads it; if it does not, make preflop fall back to
   ranking a holding by the best two-card class plus a one-step bonus for a third card that pairs or
   suits, and say so in `NIGHT.md`. Do not build a new preflop model.
5. The generator re-solves `tables/pushfold_hu.json` from the new matrix and Hero checks its
   fingerprint, but verify anyway: print `load_pushfold(tables)["matrix_fp"]` and confirm it matches
   `matrix_fingerprint(tables.hu)`. Then construct `make_bot()` once in a fresh process (it caches
   tables at import) and print one preflop and one flop decision on remapped cards, e.g. the
   permuted equivalent of AA on a dry flop, to see that the strongest displayed class is treated as
   the strongest.
6. Copy the new `tables/` into `submission/`. Re-run the kit simulator for 50 hands. Zero errors.

If anything here takes longer than its box, stop, keep the old tables, and tell me which axis fix
in prompt 05 compensates.
