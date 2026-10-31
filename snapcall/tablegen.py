"""Table generation library behind tools/gen_tables.py. Offline only; nothing here runs at decision time.

Everything is parameterized by Rules so a variant regenerates every table:
  - the deck is deck_for(rules) minus rules.extras["removed_ranks"] (displayed ranks, for short deck)
  - cards are *displayed* ints; evaluation goes through the canonical remap so permuted ranks just work
  - hole-card classes: the 169 labels for 2 cards, or the best2+tags scheme (hole_label) otherwise

Workers are plain module functions so multiprocessing can pickle them; the Rules object is set once
per worker by _init_worker.
"""
from __future__ import annotations

import random
from bisect import bisect_left
from itertools import combinations, permutations
from typing import Iterable, Sequence

from .core.cards import all_hole_classes, deck_for, hole_class
from .core.eval import CATEGORY_NAMES, category, evaluate, warm
from .core.types import RANKS, SUITS, Rules, card_str

HS_BINS = 20
QUANTILES = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
TAG_ORDER = "pshl"  # pairs one of the best two, suited with one, high (T+), low


# ---------------------------------------------------------------- rules helpers

def rules_from_dict(d: dict) -> Rules:
    """Build Rules from JSON-ish fields; lists become tuples, unknown keys go to extras."""
    fields = {f for f in Rules.__dataclass_fields__}
    kw = {}
    extras = dict(d.get("extras", {}))
    for k, v in d.items():
        if k == "extras":
            continue
        if k not in fields:
            extras[k] = v
            continue
        if isinstance(v, list):
            v = tuple(tuple(x) if isinstance(x, list) else x for x in v)
        kw[k] = v
    kw["extras"] = extras
    return Rules(**kw)


def rules_to_dict(rules: Rules) -> dict:
    out = {}
    for f in Rules.__dataclass_fields__:
        v = getattr(rules, f)
        out[f] = list(list(x) if isinstance(x, tuple) else x for x in v) if isinstance(v, tuple) else v
    return out


def live_deck(rules: Rules) -> tuple[int, ...]:
    """Displayed cards in play: deck_for(rules) minus extras['removed_ranks'] (displayed rank indexes)."""
    removed = set(rules.extras.get("removed_ranks", ()))
    return tuple(c for c in deck_for(rules) if (c >> 2) not in removed)


def canon_map(rules: Rules) -> tuple[int, ...]:
    """Displayed card int -> canonical-strength card int, for all 52."""
    return tuple(rules.rank_order[c >> 2] * 4 + (c & 3) for c in range(52))


# ---------------------------------------------------------------- hole classes

def _chen(a: int, b: int) -> float:
    """Chen formula on canonical cards; used only to pick the 'best two' of a bigger hand."""
    ra, rb = a >> 2, b >> 2
    hi, lo = max(ra, rb), min(ra, rb)
    pts = {12: 10.0, 11: 8.0, 10: 7.0, 9: 6.0}.get(hi, (hi + 2) / 2.0)
    if ra == rb:
        return max(5.0, pts * 2)
    if (a & 3) == (b & 3):
        pts += 2
    gap = hi - lo - 1
    pts -= (0, 1, 2, 4)[gap] if gap < 4 else 5
    if gap <= 1 and hi < 10:
        pts += 1
    return pts


def hole_label(hole: Sequence[int], rules: Rules = Rules(), cmap: Sequence[int] | None = None) -> str:
    """Class label of a displayed hole hand under rules.

    2 cards: the 169 label ('AKs', 'TT', '72o') in displayed ranks.
    k>2 cards: '<best2 label>+<tags>' where best2 is the Chen-best pair of cards (judged on canonical
    strength) and each remaining card gets one tag: p pairs one of the two, s shares a suit with one,
    h is T or higher (canonical), l otherwise. Tags are sorted, e.g. 'AKs+p', 'QJo+hl'.
    """
    if len(hole) == 2:
        return hole_class(hole)
    cmap = cmap or canon_map(rules)
    canon = [cmap[c] for c in hole]
    best = max(combinations(range(len(hole)), 2), key=lambda ij: _chen(canon[ij[0]], canon[ij[1]]))
    a, b = hole[best[0]], hole[best[1]]
    label = hole_class((a, b))
    tags = []
    for i, c in enumerate(hole):
        if i in best:
            continue
        if (c >> 2) in ((a >> 2), (b >> 2)):
            tags.append("p")
        elif (c & 3) in ((a & 3), (b & 3)):
            tags.append("s")
        elif (cmap[c] >> 2) >= 8:
            tags.append("h")
        else:
            tags.append("l")
    return label + "+" + "".join(sorted(tags, key=TAG_ORDER.index))


def class_table(rules: Rules) -> dict[str, list[tuple[int, ...]]]:
    """label -> all displayed combos in that class, over the live deck."""
    cmap = canon_map(rules)
    out: dict[str, list[tuple[int, ...]]] = {}
    for combo in combinations(live_deck(rules), rules.hole_cards):
        out.setdefault(hole_label(combo, rules, cmap), []).append(combo)
    if rules.hole_cards == 2:  # the strategy's CLASS_INDEX order
        order = {c: i for i, c in enumerate(all_hole_classes())}
        out = dict(sorted(out.items(), key=lambda kv: order[kv[0]]))
    return out


def hole_classes_doc(rules: Rules, classes: dict[str, list]) -> dict:
    return {
        "scheme": "169" if rules.hole_cards == 2 else "best2+tags",
        "hole_cards": rules.hole_cards,
        "n_classes": len(classes),
        "how": hole_label.__doc__.strip(),
        "function": "snapcall.tablegen.hole_label(hole, rules)",
        "classes": {k: len(v) for k, v in classes.items()},
    }


# ---------------------------------------------------------------- worker state

_R: Rules = Rules()
_DECK: tuple[int, ...] = tuple(range(52))
_CMAP: tuple[int, ...] = tuple(range(52))
_CLASSES: dict[str, list[tuple[int, ...]]] = {}
_KEEP: int = 0  # extras['keep']: showdown uses the best `keep` hole cards (discard variants); 0 = all


def _init_worker(rules_dict: dict, classes: dict | None = None) -> None:
    global _R, _DECK, _CMAP, _CLASSES, _KEEP
    _R = rules_from_dict(rules_dict)
    _DECK = live_deck(_R)
    _CMAP = canon_map(_R)
    _CLASSES = classes or {}
    _KEEP = int(_R.extras.get("keep", 0) or 0)
    if _KEEP >= _R.hole_cards:
        _KEEP = 0
    warm(min(8, (_KEEP or _R.hole_cards) + _R.board_sizes[-1]))


def _strength(cards: Iterable[int]) -> int:
    return evaluate([_CMAP[c] for c in cards])


def _showdown(hole: Sequence[int], board: Sequence[int]) -> int:
    """Strength of hole+board; with a keep rule, the best keep-subset of the hole (perfect discard)."""
    if _KEEP:
        return max(_strength(tuple(sub) + tuple(board)) for sub in combinations(hole, _KEEP))
    return _strength(tuple(hole) + tuple(board))


# ---------------------------------------------------------------- preflop equity

def preflop_job(args: tuple[str, int, int, int]) -> tuple[str, int, float]:
    """(label, n_opp, samples, seed) -> equity of the class vs n_opp random hands, all-in preflop."""
    label, n_opp, samples, seed = args
    rng = random.Random(seed)
    combos = _CLASSES[label]
    k = _R.hole_cards
    need = n_opp * k + _R.board_sizes[-1]
    deck = _DECK
    deadset = set()
    total = 0.0
    for _ in range(samples):
        hero = combos[rng.randrange(len(combos))]
        deadset = set(hero)
        while True:
            drawn = rng.sample(deck, need)
            if deadset.isdisjoint(drawn):
                break
        board = drawn[n_opp * k :]
        mine = _showdown(hero, board)
        best = 0
        ties = 0
        for v in range(n_opp):
            s = _showdown(drawn[v * k : v * k + k], board)
            if s > best:
                best, ties = s, 1
            elif s == best:
                ties += 1
        if mine > best:
            total += 1.0
        elif mine == best:
            total += 1.0 / (ties + 1)
    return label, n_opp, total / samples


def rank_percentiles(equity: dict[str, list[float]], classes: dict[str, list]) -> dict[str, float]:
    """Combo-weighted percentile of each class by heads-up equity. 1.0 = best class."""
    order = sorted(equity, key=lambda c: equity[c][0])
    total = sum(len(classes[c]) for c in order)
    below = 0
    out = {}
    for c in order:
        n = len(classes[c])
        out[c] = round((below + 0.5 * n) / total, 4)
        below += n
    return out


# ---------------------------------------------------------------- heads-up matrix

def matrix_job(args: tuple[int, int, int, int]) -> tuple[int, int, float]:
    """(i, j, samples, seed) over the 2-card class list -> equity of class i vs class j."""
    i, j, samples, seed = args
    rng = random.Random(seed)
    labels = list(_CLASSES)
    ci, cj = _CLASSES[labels[i]], _CLASSES[labels[j]]
    deck = _DECK
    nb = _R.board_sizes[-1]
    total = 0.0
    for _ in range(samples):
        while True:
            a = ci[rng.randrange(len(ci))]
            b = cj[rng.randrange(len(cj))]
            if a[0] != b[0] and a[0] != b[1] and a[1] != b[0] and a[1] != b[1]:
                break
        dead = {a[0], a[1], b[0], b[1]}
        while True:
            board = rng.sample(deck, nb)
            if dead.isdisjoint(board):
                break
        sa = _strength(a + tuple(board))
        sb = _strength(b + tuple(board))
        total += 1.0 if sa > sb else 0.5 if sa == sb else 0.0
    return i, j, total / samples


# ---------------------------------------------------------------- flop textures

def canonical_flops(deck: Sequence[int]) -> list[tuple[tuple[int, int, int], int]]:
    """Suit-isomorphism classes of 3-card flops over deck: (representative, multiplicity)."""
    seen: dict[tuple, list] = {}
    perms = list(permutations(range(4)))
    for flop in combinations(deck, 3):
        key = min(tuple(sorted(((c >> 2) * 4 + p[c & 3]) for c in flop)) for p in perms)
        entry = seen.get(key)
        if entry is None:
            seen[key] = [flop, 1]
        else:
            entry[1] += 1
    return [(tuple(rep), n) for rep, n in seen.values()]


def texture_key(flop: Sequence[int]) -> str:
    """'pair-suits-connect-high' bucket of a displayed flop."""
    ranks = sorted((c >> 2 for c in flop), reverse=True)
    distinct = sorted(set(ranks), reverse=True)
    n_suits = len({c & 3 for c in flop})
    pair = ("trips", "paired", "unpaired")[len(distinct) - 1]
    suits = ("mono", "twotone", "rainbow")[n_suits - 1]
    if len(distinct) == 1:
        connect = "none"
    else:
        span = distinct[0] - distinct[-1]
        connect = "connected" if span <= 2 else "gapped" if span <= 4 else "dry"
    return f"{pair}-{suits}-{connect}-{RANKS[ranks[0]]}"


def flop_job(args: tuple[tuple[int, ...], int, int, int]) -> tuple[str, int, list[int], list[list[float]]]:
    """(flop, multiplicity, max_holdings, seed) -> (texture, weight, hs histogram, per-category [n, hs_sum])."""
    flop, weight, max_holdings, seed = args
    rng = random.Random(seed)
    k = _R.hole_cards
    stub = [c for c in _DECK if c not in flop]
    holdings = list(combinations(stub, k))
    if len(holdings) > max_holdings:
        holdings = rng.sample(holdings, max_holdings)
    strengths = [_showdown(h, flop) for h in holdings]
    srt = sorted(strengths)
    n = len(srt)
    # exact-ish HS: rank among holdings that share no card with ours (per-card sorted lists)
    per_card: dict[int, list[int]] = {}
    for h, s in zip(holdings, strengths):
        for c in h:
            per_card.setdefault(c, []).append(s)
    for lst in per_card.values():
        lst.sort()
    hist = [0] * HS_BINS
    cats = [[0, 0.0] for _ in CATEGORY_NAMES]

    def span(lst: list[int], s: int) -> tuple[int, int]:
        lo = bisect_left(lst, s)
        return lo, bisect_left(lst, s + 1) - lo  # (#below, #equal)

    for h, s in zip(holdings, strengths):
        below, ties = span(srt, s)
        others = n - 1
        if k == 2:
            # exact: drop holdings sharing a card (A u B, with A n B = this holding)
            a_lo, a_eq = span(per_card[h[0]], s)
            b_lo, b_eq = span(per_card[h[1]], s)
            below -= a_lo + b_lo
            ties -= (a_eq - 1) + (b_eq - 1)  # colliders tied with us, not counting us
            others -= len(per_card[h[0]]) + len(per_card[h[1]]) - 2
        ties -= 1  # the holding itself
        hs = (below + 0.5 * ties) / others if others > 0 else 0.5
        hs = min(1.0, max(0.0, hs))
        hist[min(HS_BINS - 1, int(hs * HS_BINS))] += 1
        cat = cats[category(s)]
        cat[0] += 1
        cat[1] += hs
    return texture_key(flop), weight, hist, cats


def merge_flops(results: Iterable[tuple[str, int, list[int], list[list[float]]]]) -> dict:
    buckets: dict[str, dict] = {}
    for key, weight, hist, cats in results:
        b = buckets.setdefault(key, {"n_flops": 0, "hist": [0.0] * HS_BINS, "cats": [[0.0, 0.0] for _ in cats]})
        b["n_flops"] += weight
        for i, v in enumerate(hist):
            b["hist"][i] += v * weight
        for i, (n, hs) in enumerate(cats):
            b["cats"][i][0] += n * weight
            b["cats"][i][1] += hs * weight
    out = {}
    for key, b in buckets.items():
        total = sum(b["hist"]) or 1.0
        cum, q, qi = 0.0, {}, 0
        for i, v in enumerate(b["hist"]):
            prev = cum
            cum += v
            while qi < len(QUANTILES) and cum / total >= QUANTILES[qi]:
                frac = (QUANTILES[qi] * total - prev) / v if v else 0.0
                q[f"p{int(QUANTILES[qi] * 100)}"] = round((i + frac) / HS_BINS, 4)
                qi += 1
        cats_n = sum(c[0] for c in b["cats"]) or 1.0
        out[key] = {
            "n_flops": int(b["n_flops"]),
            "hs_quantiles": q,
            "categories": {
                CATEGORY_NAMES[i]: {"share": round(c[0] / cats_n, 4), "mean_hs": round(c[1] / c[0], 4)}
                for i, c in enumerate(b["cats"])
                if c[0] > 0
            },
        }
    return dict(sorted(out.items()))


def flop_example(flop: Sequence[int]) -> str:
    return " ".join(card_str(c) for c in flop)


__all__ = [
    "rules_from_dict", "rules_to_dict", "live_deck", "canon_map", "hole_label", "class_table",
    "hole_classes_doc", "preflop_job", "rank_percentiles", "matrix_job", "canonical_flops",
    "texture_key", "flop_job", "merge_flops", "RANKS", "SUITS",
]
