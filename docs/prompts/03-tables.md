# Prompt 03: regenerate tables (minute 17; ONLY if the strength or information axis moved)

The rule sheet says the <strength | information> axis moved: <one line, e.g. "ranks permuted so that
displayed 2 is strongest" or "three hole cards, one discarded face up before the flop">.

1. Check `rules_tonight.json` against `hyperion/core/types.py:Rules`: hole_cards, board_sizes,
   rank_order (displayed index -> canonical strength index, 13 entries), n_suits, blind_levels,
   hands_per_level, payouts, and any `extras` the matching preset in `hyperion/drills/variants.py`
   documents.
2. If `tables.tables_for(rules)` already loads `tables/variants/<name>/` from disk (a catalog entry with
   tonight's card rules), print its `source` and class count, keep it and go to step 5. Otherwise
   `python tools/gen_tables.py --rules rules_tonight.json --out tables/ --workers <cores>`, default
   samples, box 5 minutes; when the hole-card count or the deck changes, never `--out tables/` (it
   overwrites the 2-card set): `--out tables/variants/<name>/` with `extras.variant` = `<name>`. `--variant-check` over-projects by about 4x: pass `--skip-matrix` (Hero then
   re-solves push/fold at startup) only if it projects over 20 minutes.
3. From `hyperion.strategy`, `t = tables.load(need_hu=True)`; print `t.source` and `len(t.equity)`.
   `source` must be `disk` and the count must match the generator's log. `built` means the loader
   rejected the new files and Hero is on 60-sample standard tables: STOP, say "tables rejected",
   restore the old `tables/`. Then the heads-up equity of the strongest and weakest preflop class
   (under permuted ranks the strongest is the permuted pair).
4. If hole cards are not two: the generator writes `hole_classes.json`. Confirm
   `hyperion/strategy/preflop.py` reads it; if not, make preflop rank a holding by the best two-card
   class plus a one-step bonus for a third card that pairs or suits, and say so in `NIGHT.md`. Do not
   build a new preflop model.
5. Print `load_pushfold(tables)["matrix_fp"]` and confirm it matches `matrix_fingerprint(tables.hu)`;
   also compare `t.equity['AA'][0]` with the value in `tables/preflop_equity.json`. Then construct
   `make_bot()` once in a fresh process and print one preflop and one flop decision on remapped cards
   (the permuted AA on a dry flop): the strongest displayed class is treated as the strongest.
6. Nothing to copy: `pack.py` vendors `tables/` when it builds the zip. Re-run the kit simulator for
   50 hands. Zero errors.

If anything here takes longer than its box, stop, keep the old tables, and tell me which axis fix
in prompt 05 compensates.
