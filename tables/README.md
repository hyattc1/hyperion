# tables/

Generated artifacts. Every file here is rebuilt by one command and never edited by hand:

    python tools/gen_tables.py --rules default --samples 20000 --out tables/
    python tools/gen_tables.py --rules variant.json --out tables/        # any Rules as JSON
    python tools/gen_tables.py --rules variant.json --variant-check      # time budget, no output

`variant.json` holds Rules fields (`hole_cards`, `board_sizes`, `rank_order`, `extras`...); lists become
tuples, unknown keys land in `extras`. `hyperion.drills.variants.get(name).rules_json()` writes one.
Default generation: about 100 s on 7 workers (preflop 35 s, matrix 46 s at 5,000 samples per pair, push/fold
solve 18 s, flops 1 s); a 3-card variant about 3 min. `--matrix-samples N` sets the matrix on its own. Stdlib + multiprocessing only. Cards in all keys are *displayed* ranks: under a
permuted `rank_order` the label `AKs` still means the cards printed A and K.

| file | shape | notes |
|---|---|---|
| `preflop_equity.json` | `{class: [e1, ..., e7]}` | `eN` = all-in equity of the class vs N random hands run to showdown, ties split. 169 classes for 2 cards (`core.cards.hole_class`), else the scheme in `hole_classes.json`. |
| `preflop_rank.json` | `{class: p}` | combo-weighted percentile by heads-up equity, `p = (combos strictly weaker + half own) / total`; `AA` is ~0.998, `32o` ~0.005. Use as the preflop ordering. |
| `hu_matrix.json` | `{"classes": [N], "equity": [[N x N]]}` | `equity[i][j]` = class i vs class j all-in, 5,000 samples per pair (3 decimals; 1,000 until 2026-10-31, when the HRC cross-check traced low suited junk pushes to its 1.6% noise), `equity[j][i] = 1 - equity[i][j]`, diagonal exactly 0.5. Classes in `all_hole_classes()` order, only the live ones under a short deck (81); the loader embeds a subset in the 169 order. Only for 2-card rules; `--skip-matrix` omits it. ~160 KB. |
| `pushfold_hu.json` | `{"depths", "push", "call", "p_push", "p_call", "eq_vs_call", "eq_vs_push", "converged", "matrix_fp", "n_classes"}` | heads-up push/fold per depth 1..25 bb by fictitious play on the matrix (`hyperion.strategy.pushfold.solve_hu_pushfold`): 0/1 sets (the mixed strategy at 0.5), the mixed frequencies, each class's equity against the opposing mixed range, and per depth the iterations used and the final best-response gain in bb. `matrix_fp` ties it to the matrix: the loader re-solves when they differ. Dead classes under a short deck are out of both ranges. |
| `pushfold_multi.json` | `{"version", "matrix_fp", "classes", "model", "push", "p_push", "pnc", "eqc", "eq_vs_push", "call", "p_call", "push_order", "call_order", "reshove", "converged", "summary"}` | multiway chip-EV push/fold (`hyperion.strategy.multiway`, written by `tools/gen_multiway.py`, ~37 s on 7 workers): first-in shoves against k = 1..7 behind at 2..25 bb, callers by seat type (non-blind, SB, BB) under a no-overcall model; re-shoves over a 2.3 bb open from the top w of hands (w x m behind x 4..25 bb). Per class: no-call probability and equity when called, which Hero's ICM gate reads. `matrix_fp` ties it to the matrix and `load_multiway` returns None on a mismatch (Hero then uses the heuristic multiway rule); rerun the generator whenever `hu_matrix.json` changes. ~2.4 MB. |
| `flop_strength.json` | `{"scheme": {...}, "buckets": {texture: {...}}}` | texture key `pair-suits-connect-high` from `hyperion.tablegen.texture_key(flop)`: `unpaired/paired/trips`, `rainbow/twotone/mono`, `connected` (span of distinct ranks <= 2) / `gapped` (<= 4) / `dry`, top rank. Each bucket: `n_flops` (real flops it covers), `example`, `hs_quantiles` p10..p90 of hand strength over all holdings on those flops (HS = share of opposing holdings beaten, ties half, exact with card removal for 2 cards), and `categories` {made-hand name: share of holdings, mean HS}. Deciles are near-uniform by construction; the categories are the prior ("a pair on a mono-connected board is HS 0.4"). |
| `hole_classes.json` | `{"scheme", "hole_cards", "classes": {label: n_combos}, ...}` | only when `hole_cards != 2`. Scheme `best2+tags`: `<169 label of the Chen-best two>+<tags>`, one tag per extra card: `p` pairs one of the two, `s` suited with one, `h` ten or higher, `l` low (sorted p,s,h,l). Label function: `hyperion.tablegen.hole_label(hole, rules)`. |
| `meta.json` | rules, samples, seed, workers, seconds per table, timestamp | the drill's T+30 check compares `rules` here with the variant. |

Rules extras the generator understands: `removed_ranks` (displayed rank indexes removed from the
deck, short deck) and `keep` (showdown uses the best `keep` hole cards, a perfect-hindsight discard,
for Toss or Hold'em). It does not reorder hand categories (short-deck flush over full house): that
lives in `hyperion.drills.variants.ShortDeckHooks.score_hand` and the engine has to use it.

Precision at the defaults: preflop equity standard error ~0.35% (20000 samples per class per
opponent count), matrix ~0.7% per cell. The strategy's `tables.py` falls back to building small
tables itself if these files are missing, so a cold clone still runs; it just plays worse, and since
2026-10-31 it says so: the fallback is logged and warned (`Tables.source == "built"`), and
`load(dir, strict=True)` raises instead. The loader accepts the class scheme the files declare (81 classes
for a short deck, `hole_classes.json` labels for 3 or 4 cards) rather than requiring the 169; drill 4 had
found a regenerated short-deck set silently rejected.

## tables/variants/

One directory per catalog entry whose card rules differ from default hold'em, written by
`python tools/gen_catalog.py` at reduced samples (2 cards 4000, 3 cards 1500, 4 cards 300; the
matrix at 1/20 of that) so the whole catalog generates in a few minutes on 7 workers.
`manifest.json` records, per entry, whether tables were generated (seconds, files, bytes, rules),
shared with `tables/` ("default"), or cannot be generated ("unsupported": lowball, wild_deuces and
hi_lo need a score hook the generator does not have). The 169x169 matrix exists only for 2-card
entries; 3- and 4-card entries get `hole_classes.json`. `tools/gen_catalog.py --only NAME`
regenerates one entry; raise `SAMPLES` in that file when precision matters more than minutes. The 2-card entries'
matrix is 1,000 samples per pair. Hero reads these directories through `strategy.tables.tables_for(rules)`: when
`Rules.extras["variant"]` names an entry here whose meta.json card rules match and the game differs from hold'em
in a way a rank remap cannot fix (hole-card count, removed ranks, must-use), that directory is loaded strictly;
permuted ranks keep `tables/` (Hero remaps); a 3- or 4-card game with no directory plays from the best-two class
plus tag bonuses (`tables.fallback_label_tables`).
