"""Load the JSON tables under tables/ into plain dicts, or build defaults when they are missing.

Decision-path code only ever touches the dicts returned by `load()`. The generators here run
offline (tools/gen_tables.py calls them) or as a slow fallback so tests and the hero work on a
cold clone. Formats:

  preflop_equity.json  {cls: [equity vs 1 opp, vs 2, ..., vs 7]}      every class the set declares
  preflop_rank.json    {cls: fraction of combos strictly weaker by heads-up equity, 0..1}
  hu_matrix.json       {"classes": [names], "equity": [[e(i vs j)]]}  e[j][i] = 1 - e[i][j]
  hole_classes.json    {"scheme": "best2+tags", "classes": {label: combos}}  only for 3+ hole cards
  meta.json            {"rules": {...}, ...}  the Rules the set was generated for

The class scheme is whatever the files declare, not a hard-coded 169: a short-deck set has 81
classes (the missing 88 are filled with zero equity and rank 0 so 169-indexed code still works and
`Tables.live` says which are real), a 3- or 4-card set is keyed by `hyperion.tablegen.hole_label`
labels. `Tables.source` is "disk" when the files were used and "built" when the loader had to
generate small standard tables; a fallback is logged at WARNING, warned through `warnings`, and
raises when `strict=True` (drill 4: a regenerated short-deck set was silently rejected and Hero
degraded without anything saying so).

`tables_for(rules)` is the strategy's resolution rule: `tables/variants/<extras["variant"]>/` when a
catalog set with matching card rules exists and the card rules differ from hold'em in a way a rank
remap cannot fix (hole-card count, removed ranks, must-use), else `tables/`.
"""
from __future__ import annotations

import json
import logging
import os
import random
import warnings
from typing import Sequence

from ..core.cards import all_hole_classes, class_combos, deck_for, is_identity_order, remap
from ..core.equity import preflop_equity, showdown_share
from ..core.types import RANKS, Rules

log = logging.getLogger("hyperion.tables")

TABLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tables")
VARIANTS_DIR = os.path.join(TABLES_DIR, "variants")
CLASSES: tuple[str, ...] = tuple(all_hole_classes())
CLASS_INDEX: dict[str, int] = {c: i for i, c in enumerate(CLASSES)}
MAX_OPP = 7
TOTAL_COMBOS = 1326


class TablesError(RuntimeError):
    """A table set that was explicitly asked for is missing or invalid (strict loads only)."""


def combos_of(cls: str) -> int:
    return 6 if cls[0] == cls[1] else 4 if cls[2] == "s" else 12


COMBO_COUNT: tuple[int, ...] = tuple(combos_of(c) for c in CLASSES)


def classes_for_rules(rules_dict: dict | None) -> tuple[str, ...]:
    """The 169 labels that exist under a 2-card rules dict (extras.removed_ranks are displayed rank indexes)."""
    removed = set((rules_dict or {}).get("extras", {}).get("removed_ranks", ()) or ())
    if not removed:
        return CLASSES
    gone = {RANKS[r] for r in removed if 0 <= int(r) < 13}
    return tuple(c for c in CLASSES if c[0] not in gone and c[1] not in gone)


def rank_from_equity(equity: dict[str, Sequence[float]], classes: Sequence[str] | None = None) -> dict[str, float]:
    """Combo-weighted midpoint percentile by heads-up equity (same definition as hyperion.tablegen):
    32o ~ 0.005, AA ~ 0.998. 'Top X of hands' means rank >= 1 - X. Over `classes` when given (a
    short deck ranks within its own 81), else over the 169."""
    pool = tuple(classes) if classes is not None else CLASSES
    order = sorted(pool, key=lambda c: equity[c][0])
    total = sum(combos_of(c) for c in pool)
    out: dict[str, float] = {}
    below = 0
    for c in order:
        k = combos_of(c)
        out[c] = round((below + 0.5 * k) / total, 4)
        below += k
    return out


def _equity_row(args) -> tuple[str, list[float]]:
    cls, samples, seed, rules = args
    rng = random.Random(seed)
    return cls, [preflop_equity(cls, n, samples, rules, seed=rng.randrange(1 << 30)) for n in range(1, MAX_OPP + 1)]


def build_default_tables(samples: int = 200, rules: Rules = Rules(), seed: int = 0, workers: int = 1):
    """(equity, rank) dicts from core.equity. `samples` is per class per opponent count."""
    jobs = [(c, samples, seed * 1000 + i, rules) for i, c in enumerate(CLASSES)]
    if workers > 1:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            rows = pool.map(_equity_row, jobs, chunksize=4)
    else:
        rows = [_equity_row(j) for j in jobs]
    equity = {c: row for c, row in rows}
    return equity, rank_from_equity(equity)


def _hu_pair(args) -> tuple[int, int, float]:
    i, j, samples, seed, rules = args
    rng = random.Random(seed)
    ident = is_identity_order(rules)
    a_combos = class_combos(CLASSES[i])
    b_combos = class_combos(CLASSES[j])
    deck = deck_for(rules)
    total = 0.0
    n = 0
    while n < samples:
        a = a_combos[rng.randrange(len(a_combos))]
        b = b_combos[rng.randrange(len(b_combos))]
        if a[0] in b or a[1] in b:
            continue
        dead = (a[0], a[1], b[0], b[1])
        board = []
        while len(board) < rules.board_sizes[-1]:
            c = deck[rng.randrange(len(deck))]
            if c not in dead and c not in board:
                board.append(c)
        if not ident:
            a2, b2, board2 = remap(a, rules), remap(b, rules), remap(board, rules)
        else:
            a2, b2, board2 = a, b, board
        total += showdown_share(a2, (b2,), board2)
        n += 1
    return i, j, total / samples


def build_hu_matrix(samples: int = 300, rules: Rules = Rules(), seed: int = 0, workers: int = 1) -> list[list[float]]:
    """169x169 all-in equity matrix e[i][j] = equity of CLASSES[i] vs CLASSES[j], random boards."""
    n = len(CLASSES)
    jobs = [(i, j, samples, seed * 100003 + i * 169 + j, rules) for i in range(n) for j in range(i + 1, n)]
    if workers > 1:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            res = pool.map(_hu_pair, jobs, chunksize=64)
    else:
        res = [_hu_pair(j) for j in jobs]
    m = [[0.5] * n for _ in range(n)]
    for i, j, e in res:
        m[i][j] = e
        m[j][i] = 1.0 - e
    return m


def write_json(name: str, obj, tables_dir: str = TABLES_DIR) -> str:
    os.makedirs(tables_dir, exist_ok=True)
    path = os.path.join(tables_dir, name)
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    return path


def read_json(name: str, tables_dir: str = TABLES_DIR):
    path = os.path.join(tables_dir, name)
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


class Tables:
    """Plain-dict holder. equity[cls][n-1] = equity vs n opponents; rank[cls] in 0..1.

    scheme       "169" (2-card labels, possibly a live subset) or "best2+tags" (hole_label labels)
    classes      the labels this set really covers (81 for short deck, 338 for three cards, ...)
    combo_count  label -> combos in the live deck (0 for a 169 label the deck cannot make)
    total_combos sum of combo_count
    live         scheme "169" only: 169 bools in CLASSES order, True where the class exists
    source       "disk" or "built"; dir is where it came from
    """

    __slots__ = ("equity", "rank", "hu", "source", "dir", "scheme", "hole_cards", "classes", "combo_count",
                 "total_combos", "live")

    def __init__(self, equity, rank, hu, source: str, tables_dir: str = TABLES_DIR, scheme: str = "169",
                 hole_cards: int = 2, classes: Sequence[str] | None = None, combo_count: dict | None = None):
        self.equity = equity
        self.rank = rank
        self.hu = hu
        self.source = source
        self.dir = tables_dir
        self.scheme = scheme
        self.hole_cards = hole_cards
        self.classes = tuple(classes) if classes is not None else CLASSES
        if combo_count is None:
            combo_count = {c: combos_of(c) for c in self.classes} if scheme == "169" else {}
        self.combo_count = combo_count
        self.total_combos = sum(combo_count.values())
        self.live = [c in combo_count and combo_count[c] > 0 for c in CLASSES] if scheme == "169" else None

    def __repr__(self) -> str:
        return f"Tables({self.scheme}, {len(self.classes)} classes, source={self.source!r}, dir={self.dir!r})"


_CACHE: dict[str, Tables] = {}


def _fallback(explicit: bool, strict: bool | None, tables_dir: str, what: str) -> None:
    msg = (f"tables: {what} in {tables_dir!r}; building small standard tables instead (Tables.source == 'built'). "
           f"Hero will play hold'em from coarse tables. Regenerate with tools/gen_tables.py.")
    if strict:
        raise TablesError(msg)
    log.warning(msg)
    if explicit or strict is None:
        warnings.warn(msg, RuntimeWarning, stacklevel=3)


def _declared_classes(equity, rules_d: dict) -> tuple[str, ...]:
    """The 2-card classes a set covers: what meta.json's rules imply when there is one, else the equity
    file's own keys (every one a 169 label), so a set is judged by what it declares, never by a hard 169."""
    if rules_d:
        return classes_for_rules(rules_d)
    if isinstance(equity, dict) and equity and all(c in CLASS_INDEX for c in equity):
        return tuple(c for c in CLASSES if c in equity)
    return CLASSES


def _embed_matrix(raw, declared: Sequence[str]) -> list[list[float]] | None:
    """A matrix whose class list is any subset of CLASSES covering `declared`, in our 169 order; 0.5 elsewhere."""
    if not raw:
        return None
    names = raw.get("classes") or ()
    eq = raw.get("equity") or ()
    if len(names) != len(eq) or any(n not in CLASS_INDEX for n in names) or any(c not in names for c in declared):
        return None
    if list(names) == list(CLASSES):
        return eq
    pos = {n: k for k, n in enumerate(names)}
    m = [[0.5] * len(CLASSES) for _ in CLASSES]
    for a, ca in enumerate(CLASSES):
        pa = pos.get(ca)
        if pa is None:
            continue
        row, src = m[a], eq[pa]
        for b, cb in enumerate(CLASSES):
            pb = pos.get(cb)
            if pb is not None:
                row[b] = src[pb]
    return m


def load(tables_dir: str = TABLES_DIR, fallback_samples: int = 60, need_hu: bool = False,
         strict: bool | None = None) -> Tables:
    """Load a table set from disk; build small defaults for anything missing. Cached per directory.

    strict=True raises TablesError instead of building; the default warns (always through logging, and
    through `warnings` when a directory other than tables/ was asked for). A 3- or 4-card set cannot be
    built, so a missing one always raises."""
    key = tables_dir + ("+hu" if need_hu else "")
    t = _CACHE.get(key)
    if t is not None:
        return t
    base = _CACHE.get(tables_dir)
    if base is not None and (not need_hu or base.hu is not None):
        _CACHE[key] = base
        return base
    explicit = os.path.abspath(tables_dir) != os.path.abspath(TABLES_DIR)
    meta = read_json("meta.json", tables_dir) or {}
    rules_d = meta.get("rules") or {}
    hole_cards = int(rules_d.get("hole_cards", 2) or 2)
    hc = read_json("hole_classes.json", tables_dir)
    equity = base.equity if base else read_json("preflop_equity.json", tables_dir)
    rank = base.rank if base else read_json("preflop_rank.json", tables_dir)

    if hole_cards != 2 or (hc and hc.get("scheme") not in (None, "169")):
        # label scheme: the files are the only source; nothing here can build them
        classes = tuple((hc or {}).get("classes", {}) or (equity or {}))
        if not equity or not classes or any(c not in equity or len(equity[c]) != MAX_OPP for c in classes):
            raise TablesError(f"tables: {tables_dir!r} declares a {hole_cards}-card class scheme but has no usable "
                              f"preflop_equity.json / hole_classes.json")
        if not rank or any(c not in rank for c in classes):
            counts = (hc or {}).get("classes") or {c: 1 for c in classes}
            from ..tablegen import rank_percentiles

            rank = rank_percentiles(equity, {c: [None] * counts[c] for c in classes})
        combo_count = {c: int(n) for c, n in ((hc or {}).get("classes") or {}).items()} or {c: 1 for c in classes}
        t = Tables(equity, rank, None, "disk", tables_dir, (hc or {}).get("scheme", "best2+tags"), hole_cards,
                   classes, combo_count)
        _CACHE[key] = _CACHE[tables_dir] = t
        return t

    declared = _declared_classes(equity, rules_d)
    source = "disk"
    if base is not None:
        declared = base.classes
    elif not equity or any(c not in equity or len(equity[c]) != MAX_OPP for c in declared):
        _fallback(explicit, strict, tables_dir, "preflop_equity.json is missing or does not cover its classes")
        equity, rank = build_default_tables(fallback_samples)
        declared = CLASSES
        source = "built"
    elif not rank or any(c not in rank for c in declared):
        rank = rank_from_equity(equity, declared)
    if len(declared) < len(CLASSES):  # a live subset (short deck): 169-indexed code still finds every label
        equity = dict(equity)
        rank = dict(rank)
        for c in CLASSES:
            if c not in declared:
                equity.setdefault(c, [0.0] * MAX_OPP)
                rank.setdefault(c, 0.0)
    hu = base.hu if base else None
    if need_hu and hu is None:
        hu = _embed_matrix(read_json("hu_matrix.json", tables_dir), declared)
        if hu is None:
            _fallback(explicit, strict, tables_dir, "hu_matrix.json is missing or does not cover its classes")
            hu = build_hu_matrix(40)
            source = "built"
    combo_count = {c: (combos_of(c) if c in declared else 0) for c in CLASSES}
    t = Tables(equity, rank, hu, source if base is None else base.source, tables_dir, "169", 2, declared, combo_count)
    _CACHE[key] = t
    if need_hu or base is None:
        _CACHE[tables_dir] = t
    return t


# ---------------------------------------------------------------- variant resolution

def _card_rules(d: dict) -> tuple:
    ex = d.get("extras") or {}
    return (int(d.get("hole_cards", 2) or 2), tuple(d.get("board_sizes") or (0, 3, 4, 5)),
            tuple(d.get("rank_order") or range(13)), int(d.get("must_use_hole", 0) or 0),
            tuple(sorted(ex.get("removed_ranks") or ())), int(ex.get("keep", 0) or 0))


def variant_dir_for(rules: Rules, root: str = VARIANTS_DIR) -> str | None:
    """tables/variants/<extras["variant"]>/ when it exists and its meta.json card rules match `rules`."""
    name = (rules.extras or {}).get("variant")
    if not name:
        return None
    d = os.path.join(root, str(name))
    meta = read_json("meta.json", d)
    if not meta or not os.path.exists(os.path.join(d, "preflop_equity.json")):
        return None
    from ..tablegen import rules_to_dict

    return d if _card_rules(meta.get("rules") or {}) == _card_rules(rules_to_dict(rules)) else None


def needs_variant_tables(rules: Rules) -> bool:
    """True when a rank remap cannot turn the game into hold'em: more hole cards, a shorter deck, must-use."""
    ex = rules.extras or {}
    return rules.hole_cards != 2 or bool(ex.get("removed_ranks")) or bool(rules.must_use_hole)


def tables_for(rules: Rules, base: Tables | None = None, root: str = VARIANTS_DIR) -> Tables:
    """The set Hero should play `rules` with. Default hold'em (and anything a rank remap fixes, like
    permuted ranks) keeps `base`; otherwise the matching catalog directory, strictly loaded; and when no
    directory matches a 3- or 4-card game, a label view derived from `base` (best-two class plus tag bonuses)."""
    base = base if base is not None else load(need_hu=True)
    if not needs_variant_tables(rules):
        return base
    d = variant_dir_for(rules, root)
    if d is not None:
        try:
            return load(d, need_hu=rules.hole_cards == 2, strict=True)
        except Exception as e:  # noqa: BLE001 - a broken variant set must not stop the bot
            log.warning("tables: variant set %r unusable (%s); falling back", d, e)
    if rules.hole_cards != 2:
        heads = head_tables(rules, base, root)
        return heads if heads is not None else fallback_label_tables(base)
    return base


# ---------------------------------------------------------------- label fallback (no variant set)

class LabelView:
    """rank / equity for `best2+tags` labels derived from a 169 table: the best-two class's value plus a
    bonus per pairing (p) or suited (s) extra card, minus a flat penalty when the hand has extra cards
    at all (the "one-step tightening": everyone's hands are stronger)."""

    __slots__ = ("base", "vector", "bonus_p", "bonus_s", "penalty")

    def __init__(self, base: dict, vector: bool, bonus_p: float = 0.04, bonus_s: float = 0.02, penalty: float = 0.03):
        self.base = base
        self.vector = vector
        self.bonus_p, self.bonus_s, self.penalty = bonus_p, bonus_s, penalty

    def _adj(self, tags: str) -> float:
        if not tags:
            return 0.0
        return self.bonus_p * tags.count("p") + self.bonus_s * tags.count("s") - self.penalty

    def __getitem__(self, label: str):
        head, _, tags = label.partition("+")
        v = self.base[head]
        adj = self._adj(tags)
        if self.vector:
            return [0.0 if e + adj < 0.0 else 1.0 if e + adj > 1.0 else e + adj for e in v]
        x = v + adj
        return 0.001 if x < 0.001 else 0.999 if x > 0.999 else x

    def get(self, label: str, default=None):
        try:
            return self[label]
        except KeyError:
            return default

    def __contains__(self, label: str) -> bool:
        return label.partition("+")[0] in self.base


def head_tables(rules: Rules, base: Tables, root: str = VARIANTS_DIR) -> Tables | None:
    """A 'headview': tables/variants/<extras["variant"]>/heads.json, equity and rank by the head of the label (the
    Chen-best two) priced among hands of this game (tools/gen_keep2.py writes deal5_keep2's). No tag bonuses and no
    extra tightening: the prices already are this game's. None when the variant has no such file or it is unreadable."""
    name = (rules.extras or {}).get("variant")
    if not name:
        return None
    raw = read_json("heads.json", os.path.join(root, str(name)))
    if not raw:
        return None
    try:
        eq = {c: [float(x) for x in raw["equity"][c]] for c in CLASSES}
        rk = {c: float(raw["rank"][c]) for c in CLASSES}
    except (KeyError, TypeError, ValueError) as e:
        log.warning("tables: %s/heads.json unusable (%s); label view instead", name, e)
        return None
    return Tables(LabelView(eq, True, 0.0, 0.0, 0.0), LabelView(rk, False, 0.0, 0.0, 0.0), None,
                  base.source + "+headview", os.path.join(root, str(name)), "best2+tags", rules.hole_cards, (), {})


def fallback_label_tables(base: Tables) -> Tables:
    return Tables(LabelView(base.equity, True), LabelView(base.rank, False), None, base.source + "+labelview",
                  base.dir, "best2+tags", 3, (), {})
