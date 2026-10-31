"""Multiway chip-EV push/fold, solved offline: first-in shoves against k players behind and re-shoves
over an open raise. tools/gen_multiway.py writes tables/pushfold_multi.json; `load_multiway` reads it.
Nothing here is solved at decision time.

The game (all amounts in big blinds, chip EV)
---------------------------------------------
Every player starts the hand with S (blinds included). SB posts 0.5, BB posts 1, no antes. A shove
puts the shover's whole S in. Card removal is pairwise only: the shover's class against each
responder's class (`removal_weights`); removal between responders is ignored, and so is what an
earlier responder's fold says about the shover's cards (a third-party removal effect), which is what
lets every responder of one type share one strategy.

No-overcall: the responders behind act in order; each one calls or folds only when everyone before
it folded, and the first call ends the action (everyone else folds). A responder's call is a
heads-up all-in; its best response depends only on the shover's range and its own posted blind
(types "n" non-blind 0, "sb" 0.5, "bb" 1).

(a) First in, k behind (k = 1..7). k = 1: the shover is the SB (posted 0.5) and the BB is the only
responder (the heads-up game of pushfold.solve_hu_pushfold). k >= 2: the shover posted nothing and
behind it sit k-2 non-blinds, then SB, then BB. With posted_P the shover's blind, b_j responder j's
blind, dead_j = 1.5 - posted_P - b_j the blind money of the players who folded, and e(h, h') the
all-in equity, the shover's net chips against folding are

    fold          -posted_P
    all fold      +(1.5 - posted_P)                         (the blinds)
    j calls       e(h, h_j) * (2S + dead_j) - S

    G(h) = EV_push(h) + posted_P,
    EV_push(h) = R_k+1(h) (1.5 - posted_P) + sum_j R_j(h) [ (2S + dead_j) WEc_j(h) - S Wc_j(h) ] / Wsum(h)

with c_j responder j's calling strategy, Wc_j(h) = sum_h' w(h'|h) c_j(h'), WEc_j(h) = sum_h' w(h'|h)
c_j(h') e(h, h'), Wsum(h) = sum_h' w(h'|h), and R_j(h) = prod_{i<j} (1 - Wc_i(h)/Wsum(h)) the chance
everyone before j folds. Responder j holding h' gains, by calling instead of folding,

    T_j(h') = (2S + dead_j) WEp(h') - (S - b_j) Wp(h')        (sign = best response)

with p the shover's strategy, Wp(h') = sum_h w(h|h') p(h), WEp(h') = sum_h w(h|h') p(h) e(h', h).

(b) Re-shove over an open. A non-blind opener raised to o = 2.3 with the top w of hands by
tables.rank (rank >= 1 - w) and everyone between folded. The re-shover R has m players behind:
m = 0 it is the BB (posted 1, the SB's 0.5 is dead), m = 1 the SB (posted 0.5, BB behind), m >= 2 a
non-blind (m-2 non-blinds, SB, BB behind). R shoves S or folds; the players behind respond as in (a)
(pot 2S + o + 1.5 - posted_R - b_j when j calls: the opener's o is dead); if none calls, the opener
calls (pot 2S + 1.5 - posted_R, folding loses o) or folds, and R takes o + 1.5 - posted_R when everyone
folds. The opener's call is responder "o" with support = its opening range (normalised by
Wop(h) = sum_h' w(h'|h) open(h') instead of Wsum).

Solving. Fictitious play in its alternating, linearly weighted form: at iteration t the shover
best-responds to the responders' average strategies and its average moves toward that best response by
a = 2 / (t + 1 + t0) (iteration t's best response carries weight ~t), then every responder type
best-responds to the shover's new average and moves by the same a. Plain simultaneous 1/t averaging
needed 3,743 iterations at k = 7, S = 22 for what this does in 123 (same frequencies). The first depth
starts from "shove everything", the responders' best response to it and 40 damped (step 0.5)
best-response steps; each later depth warm-starts from the previous one with `WARM_DAMPED` damped steps
(push/fold equilibria are nearly pure, so this snaps onto them) and t0 = `WARM_T0`. A solve stops when
the largest best-response gain is under `tol`: the shover's per dealt hand, each responder type's per
hand in which it faces the shove (stricter for the rarely reached calls). tol = 1e-4 bb is the heads-up
table's standard: one 4-combo class misplayed by 0.05 bb is 1.5e-4 bb per hand. FP has no convergence
guarantee with more than two players; `converged` records [iterations, max gain] per solve.

Uniqueness. First-in solves give the same sets (0-2 classes per depth) whether the depths are walked up
from 2 bb or down from 25 bb. Re-shoves do not: with no overcalls the opener's 2.3 bb is dead money for
whoever calls behind, so at short stacks the re-shover and the players behind both profit from
gambling (at S = 4, 3.8 bb is dead against a 4 bb stack), a second equilibrium in which the re-shover
shoves ~85-95% and the players behind call almost as wide. A committed opener would overcall in real
play, so that branch is an artifact of the model. Re-shove families are therefore solved from 25 bb
down, which stays on the deep-stack branch wherever it exists. In the shipped grid 63 of 550 cells are
on the gamble branch, all with m >= 1: S = 4-5 for w = 0.10, 4-6 for w = 0.17 and 0.25 (and 0.40 with
m = 1), 4-7 for w = 0.40 with m >= 2 and for w = 0.60; never with m = 0. `p_bcall` (the behind types'
call frequencies) marks them: a behind call frequency above 0.5 means the gamble branch.

Outputs per solve: the shover's set (mixed strategy thresholded at 0.5) and combo frequency of the
mixed strategy; per shover class pnc (nobody calls, removal included) and eqc (equity when called,
averaged over who calls, weighted by the chance that responder is the one); per responder type the
call set and frequency; eq_vs_push (a responder's equity holding h against the mixed shoving range).
`push_order` / `call_order` / `reshove order`: each class's combo share of hands strictly ahead of it
by (deepest S at which it is in the set, then tables.rank), the "top f" ordering pushfold.py uses.
"""
from __future__ import annotations

import operator
import time
from itertools import repeat

from .pushfold import matrix_fingerprint, removal_weights
from .tables import CLASSES, COMBO_COUNT, TABLES_DIR, TOTAL_COMBOS, Tables, read_json, write_json

FILE = "pushfold_multi.json"
VERSION = 1
TYPES = ("n", "sb", "bb")
POSTED = {"n": 0.0, "sb": 0.5, "bb": 1.0}
K_GRID = tuple(range(1, 8))
S_GRID = tuple(range(2, 26))
OPEN_TO = 2.3
W_GRID = (0.10, 0.17, 0.25, 0.40, 0.60)
M_GRID = (0, 1, 2, 3, 4)  # 4 stands for "4 or more": two non-blinds, SB, BB behind
RS_S_GRID = tuple(range(4, 26))
TOL = 1e-4
MAX_ITERS = 4000
WARM_T0 = 4
WARM_DAMPED = 10
COLD_DAMPED = 40

_mul = operator.mul
_add = operator.add

MODEL = (
    "Chip-EV all-in-or-fold in big blinds. Every player starts the hand with S bb, blinds included; SB posts "
    "0.5, BB 1, no antes. first_in: the shover is first in with k players behind (k = 1: it is the SB and the "
    "BB responds; k >= 2: it posted nothing and k-2 non-blinds, SB, BB act behind it in that order). reshove: "
    "a non-blind opened to 2.3 bb with the top w of hands by preflop rank and everyone between folded; the "
    "re-shover has m behind (m = 0 BB, m = 1 SB, m >= 2 non-blind with m-2 non-blinds, SB, BB behind; m = 4 "
    "stands for 4+), and if nobody behind calls the opener calls or folds. No overcalls: each responder acts "
    "only if everyone before it folded and the first call ends the hand. Card removal is pairwise between the "
    "shover and each responder; removal between responders, and what earlier folds say about the shover's "
    "cards, are ignored, so responders of one type (non-blind, SB, BB, opener) share one strategy. Solved by "
    "alternating fictitious play with linearly weighted averages (best responses to the others' averages), "
    "warm-started across depths (first_in walking up from 2 bb, reshove down from 25 bb), until every player's "
    "best-response gain is under tol bb (the shover per hand dealt, responders per hand facing the shove). With "
    "no overcalls the opener's 2.3 bb is dead money for a caller behind, so short-stack reshove spots with "
    "players behind have a 'gamble' equilibrium (re-shove and behind calls ~85-95%); it is the only one at 4-5 bb "
    "and an artifact of the model (a committed opener would overcall); p_bcall above ~0.5 marks it. Sets are the "
    "mixed strategy thresholded at 0.5; frequencies are combo-weighted over the mixed strategy (p_ocall: share "
    "of the opening range). ICM is not modelled."
)


# ---------------------------------------------------------------- seats

def behind_types(k: int) -> list[str]:
    """Responder types in acting order behind a shover with k players behind (k = 1: just the BB)."""
    if k <= 0:
        return []
    if k == 1:
        return ["bb"]
    return ["n"] * (k - 2) + ["sb", "bb"]


def first_in_posted(k: int) -> float:
    return 0.5 if k == 1 else 0.0


def reshove_posted(m: int) -> float:
    return 1.0 if m == 0 else 0.5 if m == 1 else 0.0


def types_for_k(k: int) -> tuple[str, ...]:
    present = set(behind_types(k))
    return tuple(t for t in TYPES if t in present)


# ---------------------------------------------------------------- context

class Ctx:
    """Removal-weighted rows for one equity matrix (built once per worker).

    W[h][h'] = w(h'|h) (float), WE[h][h'] = w(h'|h) e(h, h'), columns of both for sparse products."""

    def __init__(self, matrix, live=None, rank=None):
        n = len(CLASSES)
        w = removal_weights(live)
        self.n = n
        self.live = live
        self.counts = [COMBO_COUNT[i] if (live is None or live[i]) else 0 for i in range(n)]
        self.total = sum(self.counts) or TOTAL_COMBOS
        self.W = [[float(x) for x in row] for row in w]
        self.WE = [[w[i][j] * matrix[i][j] for j in range(n)] for i in range(n)]
        self.Wc = [list(c) for c in zip(*self.W)]
        self.WEc = [list(c) for c in zip(*self.WE)]
        self.Wsum = [sum(r) for r in self.W]
        self.live_idx = [i for i in range(n) if self.counts[i]]
        self.eq_rand = [(sum(self.WE[i]) / self.Wsum[i]) if self.Wsum[i] else 0.5 for i in range(n)]
        self.rank = list(rank) if rank is not None else None

    def mv(self, rows, cols, v):
        """rows . v, by columns when v is mostly zeros (FP leaves never-played classes at exactly 0)."""
        nz = [j for j, x in enumerate(v) if x]
        if 2 * len(nz) >= self.n:
            return [sum(map(_mul, r, v)) for r in rows]
        acc = [0.0] * self.n
        for j in nz:
            acc = list(map(_add, acc, map(_mul, cols[j], repeat(v[j]))))
        return acc

    def open_mask(self, w: float) -> list[float]:
        """The opener's range: top w of hands by rank (rank >= 1 - w), live classes only."""
        if self.rank is None:
            raise ValueError("Ctx needs a rank list to build an opening range")
        return [1.0 if (self.counts[i] and self.rank[i] >= 1.0 - w - 1e-12) else 0.0 for i in range(self.n)]


# ---------------------------------------------------------------- one solve

class _Responder:
    __slots__ = ("key", "dead", "posted", "norm")

    def __init__(self, key: str, dead: float, posted: float, norm):
        self.key, self.dead, self.posted, self.norm = key, dead, posted, norm


def _shover_eval(ctx: Ctx, S: float, seq: list[_Responder], posted_P: float, steal: float, keys,
                 p: list[float], c: dict):
    """The shover against the responders' current averages: best response, gain per dealt hand, pnc, eqc."""
    n = ctx.n
    counts, live_idx = ctx.counts, ctx.live_idx
    twoS = 2.0 * S
    Wc = {k: ctx.mv(ctx.W, ctx.Wc, c[k]) for k in keys}
    WEc = {k: ctx.mv(ctx.WE, ctx.WEc, c[k]) for k in keys}
    pnc = [0.0] * n
    eqc = [0.0] * n
    br = [0.0] * n
    g = 0.0
    for h in live_idx:
        reach = 1.0
        ev = num = den = 0.0
        for r in seq:
            N = r.norm[h]
            if N <= 0.0:
                continue
            wc = Wc[r.key][h] / N
            if wc <= 0.0:
                continue
            we = WEc[r.key][h] / N
            ev += reach * ((twoS + r.dead) * we - S * wc)
            num += reach * we
            den += reach * wc
            reach *= 1.0 - wc
        G = ev + reach * steal + posted_P  # shove minus fold
        if G > 0.0:
            br[h] = 1.0
        g += counts[h] * (br[h] - p[h]) * G
        pnc[h] = reach
        eqc[h] = num / den if den > 0.0 else ctx.eq_rand[h]
    return br, g / ctx.total, pnc, eqc


def _resp_eval(ctx: Ctx, S: float, by_key: dict, sup_idx: dict, p: list[float]):
    """Every responder type against the shover's current average: best responses and the call-minus-fold
    totals T = (2S + dead) WEp - (S - posted) Wp (unnormalised: sign and gain weights only)."""
    Wp = ctx.mv(ctx.W, ctx.Wc, p)
    WEp = ctx.mv(ctx.WE, ctx.WEc, p)
    twoS = 2.0 * S
    br_c, T_c = {}, {}
    for k, r in by_key.items():
        dS, sb = twoS + r.dead, S - r.posted
        br = [0.0] * ctx.n
        T = [0.0] * ctx.n
        for h in sup_idx[k]:
            x = dS * WEp[h] - sb * Wp[h]
            T[h] = x
            if x > 0.0:
                br[h] = 1.0
        br_c[k], T_c[k] = br, T
    return br_c, T_c, Wp, WEp


def _resp_gains(ctx: Ctx, sup_idx: dict, br_c: dict, T_c: dict, Wp, c: dict) -> dict:
    """Each responder type's best-response gain per hand in which it faces the shove."""
    counts = ctx.counts
    out = {}
    for k, br in br_c.items():
        T, ck = T_c[k], c[k]
        num = den = 0.0
        for h in sup_idx[k]:
            num += counts[h] * (br[h] - ck[h]) * T[h]
            den += counts[h] * Wp[h]
        out[k] = num / den if den > 0.0 else 0.0
    return out


def _prep(ctx: Ctx, seq, support):
    by_key = {}
    for r in seq:
        by_key.setdefault(r.key, r)
    sup_idx = {k: [i for i in ctx.live_idx if support.get(k) is None or support[k][i]] for k in by_key}
    return list(by_key), by_key, sup_idx


def _fp(ctx: Ctx, S: float, seq: list[_Responder], posted_P: float, steal: float, support: dict,
        p: list[float], c: dict, t0: int, tol: float, max_iters: int):
    """Alternating fictitious play for one depth with linearly weighted averages.

    seq: responders in acting order (keys may repeat: one shared strategy per type); support[key]: 0/1
    mask of the hands that responder can hold (absent = all live). Iteration t: the shover best-responds
    to the responders' averages and its average moves by a = 2 / (t + 1 + t0); then every responder
    best-responds to that new shover average and moves by the same a. Each check measures all players'
    gains against the same (p, c). Mutates and returns (p, c, info)."""
    keys, by_key, sup_idx = _prep(ctx, seq, support)
    br_c, T_c, Wp, WEp = _resp_eval(ctx, S, by_key, sup_idx, p)
    it = 0
    while True:
        br_p, g_p, pnc, eqc = _shover_eval(ctx, S, seq, posted_P, steal, keys, p, c)
        gains = {"push": g_p, **_resp_gains(ctx, sup_idx, br_c, T_c, Wp, c)}
        gmax = max(gains.values())
        if gmax < tol or it >= max_iters:
            break
        it += 1
        a = 2.0 / (it + 1 + t0)
        for h in ctx.live_idx:
            p[h] += a * (br_p[h] - p[h])
        br_c, T_c, Wp, WEp = _resp_eval(ctx, S, by_key, sup_idx, p)
        for k in keys:
            ck, br = c[k], br_c[k]
            for h in sup_idx[k]:
                ck[h] += a * (br[h] - ck[h])
    eq_vs = [(WEp[h] / Wp[h]) if Wp[h] > 0.0 else ctx.eq_rand[h] for h in range(ctx.n)]
    info = {"iters": it, "gain": gmax, "gains": gains, "pnc": pnc, "eqc": eqc, "eq_vs_push": eq_vs}
    return p, c, info


def _damped(ctx: Ctx, S: float, seq, posted_P, steal, support, p, c, steps: int, alpha: float = 0.5):
    """Damped alternating best responses: snaps onto a nearby (near-)pure equilibrium, which push/fold
    equilibria mostly are, before the averaging starts."""
    keys, by_key, sup_idx = _prep(ctx, seq, support)
    for _ in range(steps):
        br_p, *_ = _shover_eval(ctx, S, seq, posted_P, steal, keys, p, c)
        for h in ctx.live_idx:
            p[h] += alpha * (br_p[h] - p[h])
        br_c, *_ = _resp_eval(ctx, S, by_key, sup_idx, p)
        for k in keys:
            ck, br = c[k], br_c[k]
            for h in sup_idx[k]:
                ck[h] += alpha * (br[h] - ck[h])
    return p, c


def _cold_start(ctx: Ctx, S: float, seq, posted_P, steal, support):
    """"Shove everything", the responders' best response to it, then damped steps."""
    keys, by_key, sup_idx = _prep(ctx, seq, support)
    p = [1.0 if ctx.counts[i] else 0.0 for i in range(ctx.n)]
    br_c, *_ = _resp_eval(ctx, S, by_key, sup_idx, p)
    c = {k: br_c[k][:] for k in keys}
    return _damped(ctx, S, seq, posted_P, steal, support, p, c, COLD_DAMPED)


def _freq(v, counts, total, support=None) -> float:
    if support is None:
        return sum(counts[i] * v[i] for i in range(len(v))) / total
    den = sum(counts[i] for i in range(len(v)) if support[i])
    return sum(counts[i] * v[i] for i in range(len(v)) if support[i]) / den if den else 0.0


def _set(v, counts) -> list[int]:
    return [1 if (x >= 0.5 and counts[i]) else 0 for i, x in enumerate(v)]


def _r4(v):
    return [round(x, 4) for x in v]


def solve_sequence(ctx: Ctx, depths, seq_fn, tol: float = TOL, max_iters: int = MAX_ITERS,
                   t0: int = WARM_T0, damped: int = WARM_DAMPED, descending: bool = False) -> list[dict]:
    """Solve one spot family over the depths with warm starts, ascending (or descending) in S.

    seq_fn(S) -> (seq, posted_P, steal, support). Returns one dict per depth in ascending S: p (mixed),
    c {key: mixed}, plus the _fp info."""
    res = []
    p = c = None
    for S in sorted(depths, reverse=descending):
        seq, posted_P, steal, support = seq_fn(S)
        if p is None:
            p, c = _cold_start(ctx, S, seq, posted_P, steal, support)
        elif damped:
            p, c = _damped(ctx, S, seq, posted_P, steal, support, p, c, damped)
        p, c, info = _fp(ctx, S, seq, posted_P, steal, support, p, c, t0, tol, max_iters)
        res.append({"S": S, "p": p[:], "c": {k: v[:] for k, v in c.items()}, **info})
    return sorted(res, key=lambda r: r["S"])


def first_in_spec(ctx: Ctx, k: int):
    posted_P = first_in_posted(k)
    types = behind_types(k)

    def seq_fn(S):
        seq = [_Responder(t, 1.5 - posted_P - POSTED[t], POSTED[t], ctx.Wsum) for t in types]
        return seq, posted_P, 1.5 - posted_P, {}
    return seq_fn


def reshove_spec(ctx: Ctx, w: float, m: int, o: float = OPEN_TO):
    posted_R = reshove_posted(m)
    types = behind_types(m)
    op = ctx.open_mask(w)
    Wop = ctx.mv(ctx.W, ctx.Wc, op)

    def seq_fn(S):
        seq = [_Responder(t, o + 1.5 - posted_R - POSTED[t], POSTED[t], ctx.Wsum) for t in types]
        seq.append(_Responder("o", 1.5 - posted_R, o, Wop))
        return seq, posted_R, o + 1.5 - posted_R, {"o": op}
    return seq_fn, op


def solve_first_in(ctx: Ctx, k: int, depths=S_GRID, tol: float = TOL, max_iters: int = MAX_ITERS) -> dict:
    """First-in shove with k behind over `depths`. Compact per-depth records (rounded, 0/1 sets)."""
    rows = solve_sequence(ctx, depths, first_in_spec(ctx, k), tol, max_iters)
    counts, total = ctx.counts, ctx.total
    types = types_for_k(k)
    out = {"k": k, "S": [r["S"] for r in rows], "push": [], "p_push": [], "pnc": [], "eqc": [], "eq_vs_push": [],
           "call": {t: [] for t in types}, "p_call": {t: [] for t in types}, "converged": []}
    for r in rows:
        out["push"].append(_set(r["p"], counts))
        out["p_push"].append(round(_freq(r["p"], counts, total), 4))
        out["pnc"].append(_r4(r["pnc"]))
        out["eqc"].append(_r4(r["eqc"]))
        out["eq_vs_push"].append(_r4(r["eq_vs_push"]))
        for t in types:
            out["call"][t].append(_set(r["c"][t], counts))
            out["p_call"][t].append(round(_freq(r["c"][t], counts, total), 4))
        out["converged"].append([r["iters"], float("%.3g" % r["gain"])])
    return out


def solve_reshove(ctx: Ctx, w: float, m: int, depths=RS_S_GRID, tol: float = TOL, max_iters: int = MAX_ITERS,
                  o: float = OPEN_TO) -> dict:
    """Re-shove over an open to `o` by the top `w`, m behind, over `depths`, solved from the deepest S down
    (see the module doc: short stacks have a second, "gamble" equilibrium; descending keeps the branch
    continuous with deep stacks wherever it exists)."""
    seq_fn, op = reshove_spec(ctx, w, m, o)
    rows = solve_sequence(ctx, depths, seq_fn, tol, max_iters, descending=True)
    counts, total = ctx.counts, ctx.total
    types = [t for t in TYPES if t in behind_types(m)]
    out = {"w": w, "m": m, "S": [r["S"] for r in rows], "push": [], "p_push": [], "pnc": [], "eqc": [],
           "ocall": [], "p_ocall": [], "p_bcall": [], "converged": []}
    for r in rows:
        out["push"].append(_set(r["p"], counts))
        out["p_push"].append(round(_freq(r["p"], counts, total), 4))
        out["pnc"].append(_r4(r["pnc"]))
        out["eqc"].append(_r4(r["eqc"]))
        oc = [x if op[i] else 0.0 for i, x in enumerate(r["c"]["o"])]
        out["ocall"].append(_set(oc, counts))
        out["p_ocall"].append(round(_freq(oc, counts, total, op), 4))
        out["p_bcall"].append([round(_freq(r["c"][t], counts, total), 4) if t in types else None for t in TYPES])
        out["converged"].append([r["iters"], float("%.3g" % r["gain"])])
    return out


def order_from_sets(sets_by_S: list[list[int]], depths, rank, counts, total) -> list[float]:
    """cls index -> combo share of live hands strictly ahead of it by (deepest S in the set, then rank)."""
    n = len(counts)
    keyed = []
    for i in range(n):
        d = 0
        for S, s in zip(depths, sets_by_S):
            if s[i]:
                d = max(d, S)
        keyed.append((-d, -rank[i], i))
    keyed.sort()
    out = [0.0] * n
    before = 0
    for _, _, i in keyed:
        out[i] = round(before / total, 4)
        before += counts[i]
    return out


# ---------------------------------------------------------------- the whole table

_WCTX: Ctx | None = None


def _init_worker(matrix, live, rank):
    global _WCTX
    _WCTX = Ctx(matrix, live, rank)


def _task(job):
    kind, args, tol, max_iters, depths = job
    t = time.time()
    if kind == "first_in":
        res = solve_first_in(_WCTX, args[0], depths, tol, max_iters)
    else:
        res = solve_reshove(_WCTX, args[0], args[1], depths, tol, max_iters)
    return kind, args, res, time.time() - t


def solve_all(tables: Tables, workers: int = 7, k_grid=K_GRID, s_grid=S_GRID, w_grid=W_GRID, m_grid=M_GRID,
              rs_s_grid=RS_S_GRID, tol: float = TOL, max_iters: int = MAX_ITERS, log=None) -> dict:
    """Solve (a) over k_grid x s_grid and (b) over w_grid x m_grid x rs_s_grid; the JSON-able table."""
    rank = [tables.rank[c] for c in CLASSES]
    t_start = time.time()
    jobs = [("reshove", (w, m), tol, max_iters, tuple(rs_s_grid)) for w in w_grid for m in m_grid]
    jobs = sorted(jobs, key=lambda j: (-j[1][1], j[1][0]))  # many behind and tight openers are the slow ones
    jobs += [("first_in", (k,), tol, max_iters, tuple(s_grid)) for k in sorted(k_grid, reverse=True)]
    results = []
    if workers > 1 and len(jobs) > 1:
        from multiprocessing import get_context

        with get_context("fork").Pool(workers, _init_worker, (tables.hu, tables.live, rank)) as pool:
            for r in pool.imap_unordered(_task, jobs):
                results.append(r)
                if log:
                    log(f"  {r[0]} {r[1]}: {r[3]:.1f} s, worst gain {max(g for _, g in r[2]['converged']):.2g}")
    else:
        _init_worker(tables.hu, tables.live, rank)
        for j in jobs:
            r = _task(j)
            results.append(r)
            if log:
                log(f"  {r[0]} {r[1]}: {r[3]:.1f} s, worst gain {max(g for _, g in r[2]['converged']):.2g}")
    ctx_counts = [COMBO_COUNT[i] if (tables.live is None or tables.live[i]) else 0 for i in range(len(CLASSES))]
    total = sum(ctx_counts) or TOTAL_COMBOS
    fi = {r[1][0]: r[2] for r in results if r[0] == "first_in"}
    rs = {r[1]: r[2] for r in results if r[0] == "reshove"}
    ks = sorted(fi)
    first_in = {"k": ks, "S": list(s_grid), "types": {str(k): list(types_for_k(k)) for k in ks},
                "push": [], "p_push": [], "pnc": [], "eqc": [], "eq_vs_push": [], "push_order": [],
                "call": {t: [] for t in TYPES}, "p_call": {t: [] for t in TYPES}, "call_order": {t: [] for t in TYPES},
                "converged": []}
    for k in ks:
        r = fi[k]
        for key in ("push", "p_push", "pnc", "eqc", "eq_vs_push", "converged"):
            first_in[key].append(r[key])
        first_in["push_order"].append(order_from_sets(r["push"], r["S"], rank, ctx_counts, total))
        for t in TYPES:
            if t in r["call"]:
                first_in["call"][t].append(r["call"][t])
                first_in["p_call"][t].append(r["p_call"][t])
                first_in["call_order"][t].append(order_from_sets(r["call"][t], r["S"], rank, ctx_counts, total))
            else:
                first_in["call"][t].append(None)
                first_in["p_call"][t].append(None)
                first_in["call_order"][t].append(None)
    ws, ms = list(w_grid), list(m_grid)
    reshove = {"o": OPEN_TO, "w": ws, "m": ms, "S": list(rs_s_grid), "push": [], "p_push": [], "pnc": [], "eqc": [],
               "ocall": [], "p_ocall": [], "p_bcall": [], "order": [], "converged": []}
    if rs:
        for w in ws:
            per = {key: [] for key in ("push", "p_push", "pnc", "eqc", "ocall", "p_ocall", "p_bcall", "order", "converged")}
            for m in ms:
                r = rs[(w, m)]
                for key in ("push", "p_push", "pnc", "eqc", "ocall", "p_ocall", "p_bcall", "converged"):
                    per[key].append(r[key])
                per["order"].append(order_from_sets(r["push"], r["S"], rank, ctx_counts, total))
            for key, v in per.items():
                reshove[key].append(v)
    worst = [g for row in first_in["converged"] for _, g in row]
    worst += [g for per_w in reshove["converged"] for row in per_w for _, g in row]  # 3 significant digits
    iters = [i for row in first_in["converged"] for i, _ in row]
    iters += [i for per_w in reshove["converged"] for row in per_w for i, _ in row]
    return {
        "version": VERSION,
        "matrix_fp": matrix_fingerprint(tables.hu),
        "classes": list(CLASSES),
        "model": MODEL,
        "tol": tol,
        "max_iters": max_iters,
        "first_in": first_in,
        "reshove": reshove,
        "summary": {"solves": len(iters), "worst_gain": max(worst) if worst else 0.0,
                    "max_iters_used": max(iters) if iters else 0, "mean_iters": round(sum(iters) / len(iters), 1) if iters else 0,
                    "unconverged": sum(1 for i in iters if i >= max_iters)},  # stopped by the cap, not by tol
        "seconds": round(time.time() - t_start, 1),
        "workers": workers,
    }


def build_multiway(tables: Tables, tables_dir: str = TABLES_DIR, write: bool = True, **kw) -> dict:
    sol = solve_all(tables, **kw)
    if write:
        write_json(FILE, sol, tables_dir)
    _MW.pop(tables_dir, None)
    return sol


# ---------------------------------------------------------------- loading

_MW: dict[str, tuple[str, dict | None]] = {}
_FP: dict[int, tuple[object, str]] = {}


def _fingerprint(hu) -> str:
    got = _FP.get(id(hu))
    if got is not None and got[0] is hu:
        return got[1]
    fp = matrix_fingerprint(hu)
    _FP[id(hu)] = (hu, fp)
    return fp


def _by_k_S(rows, ks, Ss):
    """[k index][S index] JSON arrays -> lists indexed by the real k and S (None outside the grid)."""
    out = [None] * (max(ks) + 1)
    for k, per_S in zip(ks, rows):
        if per_S is None:
            continue
        lst = [None] * (max(Ss) + 1)
        for S, v in zip(Ss, per_S):
            lst[S] = v
        out[k] = lst
    return out


def _shape(raw: dict) -> dict:
    fi = raw["first_in"]
    ks, Ss = [int(k) for k in fi["k"]], [int(s) for s in fi["S"]]
    out = {
        "matrix_fp": raw["matrix_fp"],
        "classes": tuple(raw["classes"]),
        "k_max": max(ks), "S_min": min(Ss), "S_max": max(Ss),
        "types": {int(k): tuple(v) for k, v in fi["types"].items()},
        "push": _by_k_S(fi["push"], ks, Ss),
        "p_push": _by_k_S(fi["p_push"], ks, Ss),
        "pnc": _by_k_S(fi["pnc"], ks, Ss),
        "eqc": _by_k_S(fi["eqc"], ks, Ss),
        "eq_vs_push": _by_k_S(fi["eq_vs_push"], ks, Ss),
        "call": {t: _by_k_S(fi["call"][t], ks, Ss) for t in TYPES},
        "p_call": {t: _by_k_S(fi["p_call"][t], ks, Ss) for t in TYPES},
        "push_order": [None] * (max(ks) + 1),
        "call_order": {t: [None] * (max(ks) + 1) for t in TYPES},
        "converged": _by_k_S(fi["converged"], ks, Ss),
    }
    for k, v in zip(ks, fi["push_order"]):
        out["push_order"][k] = v
    for t in TYPES:
        for k, v in zip(ks, fi["call_order"][t]):
            out["call_order"][t][k] = v
    rs = raw.get("reshove") or {}
    if rs.get("push"):
        ms, RS = [int(m) for m in rs["m"]], [int(s) for s in rs["S"]]
        shaped = {"o": rs["o"], "w": tuple(rs["w"]), "m_max": max(ms), "S_min": min(RS), "S_max": max(RS)}
        for key in ("push", "p_push", "pnc", "eqc", "ocall", "p_ocall", "p_bcall", "converged"):
            shaped[key] = [_by_k_S(per_w, ms, RS) for per_w in rs[key]]
        shaped["order"] = []
        for per_w in rs["order"]:
            lst = [None] * (max(ms) + 1)
            for m, v in zip(ms, per_w):
                lst[m] = v
            shaped["order"].append(lst)
        out["reshove"] = shaped
    else:
        out["reshove"] = None
    out["summary"] = raw.get("summary", {})
    return out


def load_multiway(tables: Tables, tables_dir: str | None = None) -> dict | None:
    """tables/pushfold_multi.json shaped for O(1) lookups, or None when the file is missing, malformed or
    was solved from another matrix (never re-solved here: the caller falls back). Memoised per directory.

    Lookups (k = players behind 1..7, S = depth in bb from depth(), t in "n"/"sb"/"bb", i = class index):
      mw["push"][k][S][i]            0/1 first-in shove set      mw["p_push"][k][S]  combo frequency
      mw["pnc"][k][S][i]             P(nobody calls | shover holds i)
      mw["eqc"][k][S][i]             shover's equity when called
      mw["eq_vs_push"][k][S][i]      a responder's equity holding i against the shoving range
      mw["call"][t][k][S][i]         0/1 call set of responder type t (None when t is not behind for k)
      mw["p_call"][t][k][S]          its combo frequency
      mw["push_order"][k][i]         combo share of hands strictly ahead of i (shove the top f: order < f)
      mw["call_order"][t][k][i]      same for calls
      rs = mw["reshove"]; wi = nearest_w(mw, w); m = min(behind, rs["m_max"]); S from depth(mw, x, rs)
      rs["push"][wi][m][S][i], rs["p_push"][wi][m][S], rs["pnc"][wi][m][S][i], rs["eqc"][wi][m][S][i],
      rs["ocall"][wi][m][S][i] (opener's call set), rs["p_ocall"][wi][m][S] (share of its opening range),
      rs["p_bcall"][wi][m][S] ([n, sb, bb] call frequencies behind, None where absent; > 0.5 = gamble branch),
      rs["order"][wi][m][i]
    Also: mw["types"][k] (responder types behind k, in TYPES order), mw["k_max"], mw["S_min"], mw["S_max"],
    mw["converged"][k][S] and rs["converged"][wi][m][S] ([iterations, max gain]), mw["summary"].
    """
    if tables is None or tables.hu is None:
        return None
    tables_dir = tables_dir or tables.dir or TABLES_DIR
    fp = _fingerprint(tables.hu)
    got = _MW.get(tables_dir)
    if got is not None and got[0] == fp:
        return got[1]
    shaped = None
    try:
        raw = read_json(FILE, tables_dir)
        if raw and raw.get("version") == VERSION and raw.get("matrix_fp") == fp and raw.get("classes") == list(CLASSES):
            shaped = _shape(raw)
    except (OSError, ValueError, KeyError, TypeError, IndexError):
        shaped = None
    _MW[tables_dir] = (fp, shaped)
    return shaped


def depth(mw_or_rs: dict, eff_bb: float) -> int:
    """Nearest grid depth, clamped to the table's range."""
    d = int(eff_bb + 0.5)
    lo, hi = mw_or_rs["S_min"], mw_or_rs["S_max"]
    return lo if d < lo else hi if d > hi else d


def nearest_w(mw: dict, w: float) -> int:
    ws = mw["reshove"]["w"]
    return min(range(len(ws)), key=lambda i: abs(ws[i] - w))
