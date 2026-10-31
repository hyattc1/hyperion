# tables/

Generated artifacts. Every file here is rebuilt by one command and never edited by hand:

    python tools/gen_tables.py --rules default --samples 20000 --out tables/
    python tools/gen_tables.py --rules variant.json --out tables/        # any Rules as JSON
    python tools/gen_tables.py --rules variant.json --variant-check      # time budget, no output

`variant.json` holds Rules fields (`hole_cards`, `board_sizes`, `rank_order`, `extras`...); lists become
tuples, unknown keys land in `extras`. `hyperion.drills.variants.get(name).rules_json()` writes one.
Default generation: about 50 s on 7 workers (preflop 37 s, matrix 10 s, flops 1 s); a 3-card variant
about 3 min. Stdlib + multiprocessing only. Cards in all keys are *displayed* ranks: under a
permuted `rank_order` the label `AKs` still means the cards printed A and K.

| file | shape | notes |
|---|---|---|
| `preflop_equity.json` | `{class: [e1, ..., e7]}` | `eN` = all-in equity of the class vs N random hands run to showdown, ties split. 169 classes for 2 cards (`core.cards.hole_class`), else the scheme in `hole_classes.json`. |
| `preflop_rank.json` | `{class: p}` | combo-weighted percentile by heads-up equity, `p = (combos strictly weaker + half own) / total`; `AA` is ~0.998, `32o` ~0.005. Use as the preflop ordering. |
| `hu_matrix.json` | `{"classes": [169], "equity": [[169 x 169]]}` | `equity[i][j]` = class i vs class j all-in, 1000 samples per pair (3 decimals), `equity[j][i] = 1 - equity[i][j]`, diagonal exactly 0.5. Classes in `all_hole_classes()` order. Only for 2-card rules; `--skip-matrix` omits it. ~160 KB. |
| `flop_strength.json` | `{"scheme": {...}, "buckets": {texture: {...}}}` | texture key `pair-suits-connect-high` from `hyperion.tablegen.texture_key(flop)`: `unpaired/paired/trips`, `rainbow/twotone/mono`, `connected` (span of distinct ranks <= 2) / `gapped` (<= 4) / `dry`, top rank. Each bucket: `n_flops` (real flops it covers), `example`, `hs_quantiles` p10..p90 of hand strength over all holdings on those flops (HS = share of opposing holdings beaten, ties half, exact with card removal for 2 cards), and `categories` {made-hand name: share of holdings, mean HS}. Deciles are near-uniform by construction; the categories are the prior ("a pair on a mono-connected board is HS 0.4"). |
| `hole_classes.json` | `{"scheme", "hole_cards", "classes": {label: n_combos}, ...}` | only when `hole_cards != 2`. Scheme `best2+tags`: `<169 label of the Chen-best two>+<tags>`, one tag per extra card: `p` pairs one of the two, `s` suited with one, `h` ten or higher, `l` low (sorted p,s,h,l). Label function: `hyperion.tablegen.hole_label(hole, rules)`. |
| `meta.json` | rules, samples, seed, workers, seconds per table, timestamp | the drill's T+30 check compares `rules` here with the variant. |

Rules extras the generator understands: `removed_ranks` (displayed rank indexes removed from the
deck, short deck) and `keep` (showdown uses the best `keep` hole cards, a perfect-hindsight discard,
for Toss or Hold'em). It does not reorder hand categories (short-deck flush over full house): that
lives in `hyperion.drills.variants.ShortDeckHooks.score_hand` and the engine has to use it.

Precision at the defaults: preflop equity standard error ~0.35% (20000 samples per class per
opponent count), matrix ~1.6% per cell. The strategy's `tables.py` falls back to building small
tables itself if these files are missing, so a cold clone still runs; it just plays worse.
