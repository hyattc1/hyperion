#!/usr/bin/env python
"""The short-handed specialist's preflop tables (S13): our own small solver, offline, stdlib only.

    .venv/bin/python tools/solve_short.py hu --iters 600 --workers 2          # tables/short_hu.json
    .venv/bin/python tools/solve_short.py three --iters 300 --workers 2       # tables/short_3.json
    .venv/bin/python tools/solve_short.py check --depth 10                    # push/fold tree vs pushfold_hu

**The game.** An abstracted preflop tree at one stack configuration (blinds 0.5 / 1 bb, no antes), 169 hand classes
per player with card-removal weights (hyperion.strategy.pushfold.removal_weights) and the all-in equity matrix
tables/hu_matrix.json. Actions per node are fold, call (limp / check / flat), one raise size the tree fixes by depth,
and all-in. A call that closes the action before everyone is all-in ends the tree at the flop, where each player gets
a share of the pot from a realization model (below) instead of a postflop game.

**Heads-up** (`hu`): chip EV, which is exact with two players left (the payout is linear in chips). The button (small
blind) acts first preflop and is in position after it. Lines: SB fold / limp / open r1 / jam; BB vs a limp check /
raise to `iso` / jam; SB vs the raise fold / call / jam; BB vs the open fold / call / 3-bet t3 / jam; SB vs the 3-bet
fold / call / 4-bet t4 / jam; BB vs the 4-bet fold / call / jam; anyone vs a jam fold / call. A raise that would put in
over ~40% of the effective stack is the jam instead.

**Three-handed** (`three`): ICM at a payout table whose prizes for 1st / 2nd / 3rd are 1 / rho / 0 (rho = (p2 - p3)
/ (p1 - p3); 0.4 for 10/7/5), on a grid of the three stacks (button, small blind, big blind). Lines: BTN fold / open r1
/ jam; after the button folds, the small and big blinds play the heads-up tree (ICM utilities, the button's stack in
the payout); vs the open, SB fold / 3-bet / jam (no flat: no three-way flops in the tree), then BB (SB folded) fold /
call / 3-bet / jam, or (SB 3-bet) fold / jam, then the button ...; vs the button's jam SB fold / call, BB fold / call.
Three-way all-ins are scored on 20 equity buckets with a pairwise product model of who wins; lines the tree does not
have (a limp from the button, a flat from the small blind) are where the specialist hands the decision back to F.

**Realization at the flop.** The in-position player's share of the pot is E + k E (1 - E) + s (b_ip - b_oop), E its
all-in equity, k = 0.25 min(1, SPR / 8) (position's worth grows with the stack behind), s = min(1, SPR / 6) and b a
small playability bonus (suited, connected, pairs; offsuit gappers lose a little). Zero-sum by construction.

**The solver** is CFR+ (regrets floored at zero, alternating updates, linearly weighted average strategy) on the
vector form of the tree: each information set is (node, hand class), one regret per action. Convergence is measured
as the exploitability of the average strategy in the abstract game: each player's best-response gain against the
other's (others') average, summed, in milli-big-blinds a hand heads-up and in milli-prizes (1st - 3rd prize = 1000)
three-handed. Every depth and configuration's iterations and exploitability are written to the table.

**Output** (JSON): per depth (configuration), per node (the action string from the root: f fold, c call, r raise,
j jam), the actions and, per class (169, in tables.CLASSES order), each action's probability quantized to 1/40
(one character each, chr(48 + q)). The three-handed file keeps those nodes zlib-compressed in one base85 string
("z", 1.4 MB for 512 configurations instead of 5.2 MB) next to each configuration's convergence ("meta").
hyperion/strategy/short.py loads both and decides by lookup.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from operator import mul

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from hyperion.strategy.pushfold import removal_weights  # noqa: E402
from hyperion.strategy.tables import CLASSES, COMBO_COUNT, TABLES_DIR, read_json  # noqa: E402

N = len(CLASSES)
Q = 40  # probabilities are stored in steps of 1/Q

HU_DEPTHS = (5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 22, 25, 28, 32, 36, 40, 45, 50, 60, 70, 85, 100)
THREE_GRID = (5, 8, 12, 18, 27, 40, 60)
RHOS = (0.4,)


# ------------------------------------------------------------------------------------------------ equity data
_G: dict = {}


def _globals():
    if _G:
        return _G
    hu = read_json(os.path.join(TABLES_DIR, "hu_matrix.json"))
    assert hu["classes"] == list(CLASSES)
    E = hu["equity"]
    W = removal_weights()
    _G["E"] = E
    _G["W"] = [[float(x) for x in row] for row in W]
    _G["WE"] = [[W[i][j] * E[i][j] for j in range(N)] for i in range(N)]
    _G["bonus"] = [_playability(c) for c in CLASSES]
    _G["realize"] = {}
    _G["total"] = sum(COMBO_COUNT[i] * sum(W[i]) for i in range(N))
    return _G


def _playability(cls: str) -> float:
    r = "23456789TJQKA"
    a, b = r.index(cls[0]), r.index(cls[1])
    if a == b:
        return 0.01
    gap = a - b
    v = 0.0
    if cls[2] == "s":
        v += 0.025
    if gap == 1:
        v += 0.015
    elif gap == 2:
        v += 0.008
    if b >= 8:
        v += 0.005
    if cls[2] == "o" and gap >= 4 and b < 7:
        v -= 0.015
    return v


def realize_mats(spr: float):
    """(W * share_ip, W * share_oop) at this SPR (rounded to a bucket), rows = the player's own class."""
    g = _globals()
    key = round(min(spr, 40.0) * 2) / 2
    m = g["realize"].get(key)
    if m is not None:
        return m
    E, W, b = g["E"], g["W"], g["bonus"]
    k = 0.25 * min(1.0, key / 8.0)
    s = min(1.0, key / 6.0)
    ip = [[0.0] * N for _ in range(N)]
    oop = [[0.0] * N for _ in range(N)]
    for i in range(N):
        Ei, Wi, bi = E[i], W[i], b[i]
        for j in range(N):
            e = Ei[j]
            r = e + k * e * (1.0 - e) + s * (bi - b[j])
            r = 0.01 if r < 0.01 else 0.99 if r > 0.99 else r
            ip[i][j] = Wi[j] * r  # i in position against j
            oop[j][i] = W[j][i] * (1.0 - r)  # j out of position against i
    g["realize"][key] = m = (ip, oop)
    return m


def matvec(M, v):
    return [sum(map(mul, row, v)) for row in M]


# ------------------------------------------------------------------------------------------------ tree
class Node:
    __slots__ = ("player", "acts", "kids", "key", "term", "reg", "avg", "n")

    def __init__(self, player=-1, key=""):
        self.player = player
        self.acts: list = []
        self.kids: list = []
        self.key = key
        self.term = None
        self.reg = None
        self.avg = None


def dec(player, key, children):
    n = Node(player, key)
    for a, kid in children:
        n.acts.append(a)
        n.kids.append(kid)
    na = len(n.acts)
    n.reg = [[0.0] * N for _ in range(na)]
    n.avg = [[0.0] * N for _ in range(na)]
    return n


def term(spec):
    n = Node()
    n.term = spec
    return n


# Terminal specs (chips relative to the start of the hand, in bb, for each player p, of each outcome):
#   ("fold", u)                      u[p]: the hand ended without a showdown
#   ("sd2", a, b, ua, ub, mats)      a and b contest; ua[p] / ub[p] if a / b wins; mats: (W*share for a, for b) rows
#   ("sd3", order_u)                 three players all in: order_u[(x, y, z)][p] (x best, then y over z)


def hu_tree(S: float, util_of=None):
    """The heads-up tree at effective stack S (bb). util_of(commit_sb, commit_bb, winner or None) -> (u_sb, u_bb):
    default chip EV. Players: 0 = SB (button), 1 = BB."""
    if util_of is None:
        def util_of(c, winner, pot_win=None):
            # chip EV: the winner gains what the other put in
            u = [-c[0], -c[1]]
            u[winner] += c[0] + c[1]
            return u

    r1 = 2.0 if S <= 25 else 2.25 if S <= 60 else 2.5
    iso = 3.0 if S > 12 else 2.5

    def raise_ok(to, S):
        return to <= 0.4 * S

    def jam_vs(player_to_act, c, key):
        """The other has jammed (all in for S); player_to_act folds or calls."""
        other = 1 - player_to_act
        cf = list(c)
        fold = term(("fold", util_of(cf, other)))
        call = showdown([S, S])
        return dec(player_to_act, key, [("f", fold), ("c", call)])

    def showdown(c):
        return term(("sd2", 0, 1, util_of(c, 0), util_of(c, 1), None))

    def flop(c):
        pot = c[0] + c[1]
        spr = (S - c[0]) / pot  # the stack behind over the pot
        ip, oop = realize_mats(spr)
        return term(("sd2", 0, 1, util_of(c, 0), util_of(c, 1), (ip, oop)))

    # BB facing a jam from SB at root
    root_kids = []
    root_kids.append(("f", term(("fold", util_of([0.5, 1.0], 1)))))
    # limp
    c_l = [1.0, 1.0]
    bb_vs_limp = []
    bb_vs_limp.append(("c", flop(c_l)))
    if raise_ok(iso, S):
        c_i = [1.0, iso]
        sb_vs_iso = [("f", term(("fold", util_of(c_i, 1)))), ("c", flop([iso, iso])),
                     ("j", jam_vs(1, [S, iso], "lrj"))]
        bb_vs_limp.append(("r", dec(0, "lr", sb_vs_iso)))
    bb_vs_limp.append(("j", jam_vs(0, [1.0, S], "lj")))
    root_kids.append(("c", dec(1, "l", bb_vs_limp)))
    # open
    if raise_ok(r1, S):
        c_o = [r1, 1.0]
        bb_vs_open = [("f", term(("fold", util_of(c_o, 0)))), ("c", flop([r1, r1]))]
        t3 = round(3.5 * r1 * 2) / 2
        if raise_ok(t3, S):
            c_3 = [r1, t3]
            sb_vs_3 = [("f", term(("fold", util_of(c_3, 1)))), ("c", flop([t3, t3]))]
            t4 = round(2.2 * t3 * 2) / 2
            if t4 <= 0.45 * S:
                c_4 = [t4, t3]
                bb_vs_4 = [("f", term(("fold", util_of(c_4, 0)))), ("c", flop([t4, t4])),
                           ("j", jam_vs(0, [t4, S], "rrrj"))]
                sb_vs_3.append(("r", dec(1, "rrr", bb_vs_4)))
            sb_vs_3.append(("j", jam_vs(1, [S, t3], "rrj")))
            bb_vs_open.append(("r", dec(0, "rr", sb_vs_3)))
        bb_vs_open.append(("j", jam_vs(0, [r1, S], "rj")))
        root_kids.append(("r", dec(1, "r", bb_vs_open)))
    root_kids.append(("j", jam_vs(1, [S, 1.0], "j")))
    root = dec(0, "", root_kids)
    meta = {"S": S, "r1": r1, "iso": iso}
    return root, meta


# ------------------------------------------------------------------------------------------------ CFR+
def _strategy(node):
    reg = node.reg
    na = len(reg)
    out = [[0.0] * N for _ in range(na)]
    for i in range(N):
        tot = 0.0
        for a in range(na):
            x = reg[a][i]
            if x > 0:
                tot += x
        if tot > 0:
            for a in range(na):
                x = reg[a][i]
                out[a][i] = x / tot if x > 0 else 0.0
        else:
            u = 1.0 / na
            for a in range(na):
                out[a][i] = u
    return out


def _avg_strategy(node):
    avg = node.avg
    na = len(avg)
    out = [[0.0] * N for _ in range(na)]
    for i in range(N):
        tot = sum(avg[a][i] for a in range(na))
        if tot > 0:
            for a in range(na):
                out[a][i] = avg[a][i] / tot
        else:
            for a in range(na):
                out[a][i] = 1.0 / na
    return out


def _term_value(spec, reach, p, nplayers):
    """Counterfactual value vector of player p at a terminal (others' reaches in `reach`)."""
    g = _globals()
    W = g["W"]
    kind = spec[0]
    if kind == "fold":
        u = spec[1][p]
        if nplayers == 2:
            wr = matvec(W, reach[1 - p])
            return [u * x for x in wr]
        out = [u] * N
        for q in range(nplayers):
            if q != p:
                wr = matvec(W, reach[q])
                out = [o * x for o, x in zip(out, wr)]
        return out
    if kind == "sd2":
        _, a, b, ua, ub, mats = spec
        if p == a or p == b:
            o = b if p == a else a
            win_u = ua[p] if p == a else ub[p]
            lose_u = ub[p] if p == a else ua[p]
            wr = matvec(W, reach[o])
            if mats is None:
                er = matvec(g["WE"], reach[o])
            else:
                er = matvec(mats[0] if p == a else mats[1], reach[o])
            out = [lose_u * x + (win_u - lose_u) * y for x, y in zip(wr, er)]
            for q in range(nplayers):  # a folded third player's hands only scale the weight
                if q != a and q != b:
                    s = sum(reach[q][j] * COMBO_COUNT[j] for j in range(N)) / 1326.0
                    out = [v * s for v in out]
            return out
        # p folded earlier: the outcome probabilities of a vs b, weighted
        wr_b = matvec(W, reach[b])
        tot = sum(map(mul, reach[a], wr_b))
        if mats is None:
            er = matvec(g["WE"], reach[b])
        else:
            er = matvec(mats[0], reach[b])
        pa = sum(map(mul, reach[a], er))
        v = ub[p] * tot + (ua[p] - ub[p]) * pa
        # p's own class: scale by compatible combos (ignored: removal against two hands), per-combo weight
        return [v / 1326.0 * 1225.0 / 1225.0] * N
    if kind == "sd3":
        return _sd3_value(spec, reach, p)
    raise ValueError(kind)


def walk(node, reach, p, nplayers, t):
    if node.term is not None:
        return _term_value(node.term, reach, p, nplayers)
    q = node.player
    sigma = _strategy(node)
    na = len(node.acts)
    if q == p:
        vals = []
        rq = reach[q]
        for a in range(na):
            r2 = list(reach)
            sa = sigma[a]
            r2[q] = [x * y for x, y in zip(rq, sa)]
            vals.append(walk(node.kids[a], r2, p, nplayers, t))
        nv = [0.0] * N
        for a in range(na):
            sa, va = sigma[a], vals[a]
            for i in range(N):
                nv[i] += sa[i] * va[i]
        for a in range(na):
            ra, va = node.reg[a], vals[a]
            av, sa = node.avg[a], sigma[a]
            for i in range(N):
                x = ra[i] + va[i] - nv[i]
                ra[i] = x if x > 0 else 0.0
                av[i] += t * rq[i] * sa[i]
        return nv
    out = None
    rq = reach[q]
    for a in range(na):
        r2 = list(reach)
        sa = sigma[a]
        r2[q] = [x * y for x, y in zip(rq, sa)]
        v = walk(node.kids[a], r2, p, nplayers, t)
        if out is None:
            out = v
        else:
            out = [x + y for x, y in zip(out, v)]
    return out


def br_walk(node, reach, p, nplayers):
    """Best response of p against the others' average strategies; also the value of p's average strategy."""
    if node.term is not None:
        v = _term_value(node.term, reach, p, nplayers)
        return v, v
    q = node.player
    sigma = _avg_strategy(node)
    na = len(node.acts)
    if q == p:
        brs, avs = [], []
        for a in range(na):
            br, av = br_walk(node.kids[a], reach, p, nplayers)
            brs.append(br)
            avs.append(av)
        best = [max(brs[a][i] for a in range(na)) for i in range(N)]
        cur = [sum(sigma[a][i] * avs[a][i] for a in range(na)) for i in range(N)]
        return best, cur
    ob, oa = None, None
    rq = reach[q]
    for a in range(na):
        r2 = list(reach)
        r2[q] = [x * y for x, y in zip(rq, sigma[a])]
        b, v = br_walk(node.kids[a], r2, p, nplayers)
        ob = b if ob is None else [x + y for x, y in zip(ob, b)]
        oa = v if oa is None else [x + y for x, y in zip(oa, v)]
    return ob, oa


def exploitability(root, nplayers, norm):
    """Sum over players of the best-response gain over the average strategy (per hand, in the utility's unit)."""
    gains = []
    for p in range(nplayers):
        reach = [[1.0] * N for _ in range(nplayers)]
        br, av = br_walk(root, reach, p, nplayers)
        b = sum(COMBO_COUNT[i] * br[i] for i in range(N)) / norm
        a = sum(COMBO_COUNT[i] * av[i] for i in range(N)) / norm
        gains.append(b - a)
    return gains


def solve(root, nplayers, iters, norm, check_every=0, log=None):
    hist = []
    for t in range(1, iters + 1):
        for p in range(nplayers):
            reach = [[1.0] * N for _ in range(nplayers)]
            walk(root, reach, p, nplayers, t)
        if check_every and (t % check_every == 0 or t == iters):
            g = exploitability(root, nplayers, norm)
            hist.append((t, [round(x, 6) for x in g]))
            if log:
                log(t, g)
    return hist


def nodes_of(root):
    out = []
    st = [root]
    while st:
        n = st.pop()
        if n.term is None:
            out.append(n)
            st.extend(n.kids)
    return out


def encode(root):
    out = {}
    for n in nodes_of(root):
        s = _avg_strategy(n)
        na = len(n.acts)
        chars = []
        for i in range(N):
            qs = [int(round(s[a][i] * Q)) for a in range(na)]
            d = Q - sum(qs)  # keep each class summing to Q
            k = max(range(na), key=lambda a: s[a][i])
            qs[k] += d
            chars.append("".join(chr(48 + x) for x in qs))
        out[n.key] = {"p": n.player, "a": "".join(n.acts), "s": "".join(chars)}
    return out



# ------------------------------------------------------------------------------------------------ three-handed
# The three-handed solve runs on numpy (offline only: any Python that has it; the tables it writes are plain JSON and
# the bot reads them with the standard library). Players 0 = button, 1 = small blind, 2 = big blind.
B3 = 20  # equity buckets for three-way all-ins
_POST_RANK = (2, 0, 1)  # postflop order: SB first, then BB, the button last


def icm3(final, start, rho):
    """Prize equity of three stacks at prizes 1 / rho / 0 (Malmuth-Harville); a bust takes 3rd, two busts in one hand
    are ordered by the stacks they started the hand with."""
    alive = [i for i in range(3) if final[i] > 1e-9]
    u = [0.0, 0.0, 0.0]
    if len(alive) == 3:
        T = sum(final)
        for i in range(3):
            p1 = final[i] / T
            p2 = sum(final[j] / T * final[i] / (T - final[j]) for j in range(3) if j != i)
            u[i] = p1 + rho * p2
        return u
    if len(alive) == 2:
        a, b = alive
        T = final[a] + final[b]
        u[a] = rho + (1 - rho) * final[a] / T
        u[b] = rho + (1 - rho) * final[b] / T
        return u
    w = alive[0]
    u[w] = 1.0
    bust = [i for i in range(3) if i != w]
    x, y = bust
    if start[x] > start[y]:
        u[x] = rho
    elif start[y] > start[x]:
        u[y] = rho
    else:
        u[x] = u[y] = rho / 2
    return u


def _distribute(c, start, order, inpot):
    """Final stacks when the players in `inpot` show down in strength order `order` (best first): pot layers by
    contribution, folded players' chips in the first layer, a layer only one player reaches goes back to him."""
    final = [start[i] - c[i] for i in range(3)]
    levels = sorted(set(c[i] for i in inpot))
    dead = sum(c[i] for i in range(3) if i not in inpot)
    prev = 0.0
    for k, lv in enumerate(levels):
        elig = [i for i in inpot if c[i] >= lv - 1e-12]
        layer = (lv - prev) * len(elig) + (dead if k == 0 else 0.0)
        # contributions of in-pot players below this level were counted in lower layers
        best = next(i for i in order if i in elig)
        final[best] += layer
        prev = lv
    return final


def three_tree(st, rho):
    """The three-handed tree (module doc) at stacks st = [button, SB, BB] in bb, prizes 1 / rho / 0."""
    from itertools import permutations

    start = list(st)

    def U(final):
        return icm3(final, start, rho)

    def fold_term(c, winner):
        final = [start[i] - c[i] for i in range(3)]
        final[winner] += sum(c)
        return term(("fold", U(final)))

    def sd(c, inpot, flop=False):
        inpot = list(inpot)
        if len(inpot) == 2:
            a, b = inpot
            ua = U(_distribute(c, start, [a, b], inpot))
            ub = U(_distribute(c, start, [b, a], inpot))
            mats = None
            if flop:
                pot = sum(c)
                spr = min(start[a] - c[a], start[b] - c[b]) / pot if pot else 40.0
                ip, oop = realize_mats_np(spr)
                mats = (ip, oop) if _POST_RANK[a] > _POST_RANK[b] else (oop, ip)
            return term(("sd2", a, b, ua, ub, mats))
        outs = {}
        for order in permutations(range(3)):
            outs[order] = U(_distribute(c, start, list(order), [0, 1, 2]))
        return term(("sd3", outs))

    def eff_of(p, alive):
        others = max(start[j] for j in alive if j != p)
        return min(start[p], others)

    def r1_of(e):
        return 2.0 if e <= 25 else 2.25 if e <= 60 else 2.5

    def commit(c, p, to):
        c2 = list(c)
        c2[p] = min(to, start[p])
        return c2

    def jam_resp(c, order, alive_after, key):
        """Each player in `order` (in turn) folds or calls an all-in; alive_after: players still in before them."""
        p = order[0]
        rest = order[1:]
        cur = max(c)
        cf, cc = list(c), commit(c, p, cur)
        inf = [x for x in alive_after if x != p]
        if rest:
            kf = jam_resp(cf, rest, inf, key + "f")
            kc = jam_resp(cc, rest, alive_after, key + "c")
        else:
            kf = fold_term(cf, inf[0]) if len(inf) == 1 else sd(cf, inf)
            kc = sd(cc, alive_after)
        return dec(p, key, [("f", kf), ("c", kc)])

    c0 = [0.0, 0.5, 1.0]
    kids = []
    # --- the button folds: the blinds' heads-up tree (SB out of position postflop) ---
    cS = c0
    eS = eff_of(1, [1, 2])
    r1 = r1_of(eS)
    iso = 3.0 if eS > 12 else 2.5
    sbk = [("f", fold_term(cS, 2))]
    cl = commit(cS, 1, 1.0)
    bbl = [("c", sd(cl, [1, 2], flop=True))]
    if iso <= 0.4 * eS:
        ci = commit(cl, 2, iso)
        sbi = [("f", fold_term(ci, 2)), ("c", sd(commit(ci, 1, iso), [1, 2], flop=True)),
               ("j", jam_resp(commit(ci, 1, start[1]), [2], [1, 2], "fcrj"))]
        bbl.append(("r", dec(1, "fcr", sbi)))
    bbl.append(("j", jam_resp(commit(cl, 2, start[2]), [1], [1, 2], "fcj")))
    sbk.append(("c", dec(2, "fc", bbl)))
    if r1 <= 0.4 * eS:
        co = commit(cS, 1, r1)
        bbo = [("f", fold_term(co, 1)), ("c", sd(commit(co, 2, r1), [1, 2], flop=True))]
        t3 = round(3.5 * r1 * 2) / 2
        if t3 <= 0.4 * eS:
            c3 = commit(co, 2, t3)
            sb3 = [("f", fold_term(c3, 2)), ("c", sd(commit(c3, 1, t3), [1, 2], flop=True))]
            t4 = round(2.2 * t3 * 2) / 2
            if t4 <= 0.45 * eS:
                c4 = commit(c3, 1, t4)
                bb4 = [("f", fold_term(c4, 1)), ("c", sd(commit(c4, 2, t4), [1, 2], flop=True)),
                       ("j", jam_resp(commit(c4, 2, start[2]), [1], [1, 2], "frrrj"))]
                sb3.append(("r", dec(2, "frrr", bb4)))
            sb3.append(("j", jam_resp(commit(c3, 1, start[1]), [2], [1, 2], "frrj")))
            bbo.append(("r", dec(1, "frr", sb3)))
        bbo.append(("j", jam_resp(commit(co, 2, start[2]), [1], [1, 2], "frj")))
        sbk.append(("r", dec(2, "fr", bbo)))
    sbk.append(("j", jam_resp(commit(cS, 1, start[1]), [2], [1, 2], "fj")))
    kids.append(("f", dec(1, "f", sbk)))
    # --- the button opens ---
    eB = eff_of(0, [0, 1, 2])
    r1b = r1_of(eB)
    if r1b <= 0.4 * eB:
        co = commit(c0, 0, r1b)
        t3 = round(3.5 * r1b * 2) / 2
        # SB: fold / 3-bet / jam
        sbo = []
        # SB folds: BB vs the open
        bbv = [("f", fold_term(co, 0)), ("c", sd(commit(co, 2, r1b), [0, 2], flop=True))]
        e2 = min(start[2], start[0])
        if t3 <= 0.4 * e2:
            c3 = commit(co, 2, t3)
            bt = [("f", fold_term(c3, 2)), ("c", sd(commit(c3, 0, t3), [0, 2], flop=True)),
                  ("j", jam_resp(commit(c3, 0, start[0]), [2], [0, 2], "rfrj"))]
            bbv.append(("r", dec(0, "rfr", bt)))
        bbv.append(("j", jam_resp(commit(co, 2, start[2]), [0], [0, 2], "rfj")))
        sbo.append(("f", dec(2, "rf", bbv)))
        e1 = min(start[1], max(start[0], start[2]))
        if t3 <= 0.4 * e1:
            c3 = commit(co, 1, t3)
            # BB vs open + 3-bet: fold / jam
            bt = [("f", fold_term(c3, 1)), ("c", sd(commit(c3, 0, t3), [0, 1], flop=True)),
                  ("j", jam_resp(commit(c3, 0, start[0]), [1], [0, 1], "rrfj"))]
            bb3 = [("f", dec(0, "rrf", bt)),
                   ("j", jam_resp(commit(c3, 2, start[2]), [0, 1], [0, 1, 2], "rrj"))]
            sbo.append(("r", dec(2, "rr", bb3)))
        sbo.append(("j", jam_resp(commit(co, 1, start[1]), [2, 0], [0, 1, 2], "rj")))
        kids.append(("r", dec(1, "r", sbo)))
    kids.append(("j", jam_resp(commit(c0, 0, start[0]), [1, 2], [0, 1, 2], "j")))
    root = dec(0, "", kids)
    return root, {"st": start, "rho": rho, "r1": r1b, "r1_sb": r1, "iso": iso}


_NP: dict = {}


def _np_globals():
    if _NP:
        return _NP
    import numpy as np

    g = _globals()
    _NP["np"] = np
    _NP["W"] = np.array(g["W"])
    _NP["WE"] = np.array(g["WE"])
    _NP["c"] = np.array([float(x) for x in COMBO_COUNT])
    pe = read_json(os.path.join(TABLES_DIR, "preflop_equity.json"))
    e2 = [pe[cl][1] for cl in CLASSES]
    order = sorted(range(N), key=lambda i: e2[i])
    cum, tot = 0.0, float(sum(COMBO_COUNT))
    bucket = [0] * N
    for i in order:
        bucket[i] = min(B3 - 1, int(cum / tot * B3))
        cum += COMBO_COUNT[i]
    bucket = np.array(bucket)
    BM = np.zeros((B3, N))
    for i in range(N):
        BM[bucket[i], i] = COMBO_COUNT[i]
    E = np.array(g["E"])
    W = _NP["W"]
    num = BM @ (W * E) @ BM.T / np.maximum(1.0, (BM @ W @ BM.T))  # combo-weighted, removal-aware bucket equity
    EB = num * 0  # symmetrize: EB + EB.T = 1
    EB = 0.5 * (num + (1.0 - num.T))
    _NP["bucket"], _NP["BM"], _NP["EB"] = bucket, BM, EB
    # P(x best) for the three players' buckets, then the order probabilities
    e01, e02, e12 = EB[:, :, None], EB[:, None, :], EB[None, :, :]
    p0 = EB[:, :, None] * EB[:, None, :]
    p1 = EB.T[:, :, None] * EB[None, :, :]
    p2 = EB.T[:, None, :] * EB.T[None, :, :]
    tot3 = p0 + p1 + p2
    _NP["pbest"] = (p0 / tot3, p1 / tot3, p2 / tot3)
    _NP["realize"] = {}
    _NP["F2"] = 1176.0 / 1326.0
    _NP["F3"] = 1225.0 * 1176.0 / 1326.0 ** 2
    wsum = W.sum(axis=1)
    _NP["norm3"] = float((_NP["c"] * wsum * wsum).sum() * 1176.0 / 1225.0)
    return _NP


def realize_mats_np(spr):
    g = _np_globals()
    key = round(min(spr, 40.0) * 2) / 2
    m = g["realize"].get(key)
    if m is None:
        np = g["np"]
        ip, oop = realize_mats(key)
        m = g["realize"][key] = (np.array(ip), np.array(oop))
    return m


def _order_tensor(outs, p):
    """T[b0, b1, b2]: player p's expected prize at a three-way all-in, by the three players' buckets."""
    g = _np_globals()
    np = g["np"]
    EB = g["EB"]
    pb = g["pbest"]
    T = np.zeros((B3, B3, B3))
    pair = {(1, 2): EB[None, :, :], (2, 1): EB.T[None, :, :], (0, 2): EB[:, None, :], (2, 0): EB.T[:, None, :],
            (0, 1): EB[:, :, None], (1, 0): EB.T[:, :, None]}
    for order, u in outs.items():
        x, y, z = order
        T += pb[x] * pair[(y, z)] * u[p]
    return T


def _prep3(root):
    """Precompute every sd3 terminal's per-player tensor once."""
    for n in _all_nodes(root):
        if n.term is not None and n.term[0] == "sd3" and len(n.term) == 2:
            n.term = ("sd3", n.term[1], [_order_tensor(n.term[1], p) for p in range(3)])


def _all_nodes(root):
    out, st = [], [root]
    while st:
        n = st.pop()
        out.append(n)
        if n.term is None:
            st.extend(n.kids)
    return out


def _tv3(spec, reach, p):
    g = _np_globals()
    np = g["np"]
    W = g["W"]
    kind = spec[0]
    if kind == "fold":
        u = spec[1][p]
        out = np.full(N, u)
        for q in range(3):
            if q != p:
                out = out * (W @ reach[q])
        return out
    if kind == "sd2":
        _, a, b, ua, ub, mats = spec
        third = 3 - a - b
        if p == a or p == b:
            o = b if p == a else a
            win_u = ua[p] if p == a else ub[p]
            lose_u = ub[p] if p == a else ua[p]
            M = g["WE"] if mats is None else (mats[0] if p == a else mats[1])
            return (lose_u * (W @ reach[o]) + (win_u - lose_u) * (M @ reach[o])) * (W @ reach[third])
        M = g["WE"] if mats is None else mats[0]
        ca = g["c"] * reach[a]
        s1 = ca @ (W @ reach[b])
        s2 = ca @ (M @ reach[b])
        return np.full(N, (ub[p] * s1 + (ua[p] - ub[p]) * s2) * g["F2"])
    if kind == "sd3":
        T = spec[2][p]
        BM = g["BM"]
        others = [q for q in range(3) if q != p]
        R = [BM @ reach[q] for q in others]
        if p == 0:
            vb = np.einsum("xyz,y,z->x", T, R[0], R[1])
        elif p == 1:
            vb = np.einsum("yxz,y,z->x", T, R[0], R[1])
        else:
            vb = np.einsum("yzx,y,z->x", T, R[0], R[1])
        return vb[g["bucket"]] * g["F3"]
    raise ValueError(kind)


def _sigma_np(node, np):
    reg = node.reg
    pos = np.maximum(reg, 0.0)
    tot = pos.sum(axis=0)
    na = reg.shape[0]
    out = np.where(tot > 0, pos / np.where(tot > 0, tot, 1.0), 1.0 / na)
    return out


def _avg_np(node, np):
    tot = node.avg.sum(axis=0)
    na = node.avg.shape[0]
    return np.where(tot > 0, node.avg / np.where(tot > 0, tot, 1.0), 1.0 / na)


def walk3(node, reach, p, t, np):
    if node.term is not None:
        return _tv3(node.term, reach, p)
    q = node.player
    sigma = _sigma_np(node, np)
    na = len(node.acts)
    rq = reach[q]
    if q == p:
        vals = []
        for a in range(na):
            r2 = list(reach)
            r2[q] = rq * sigma[a]
            vals.append(walk3(node.kids[a], r2, p, t, np))
        V = np.array(vals)
        nv = (sigma * V).sum(axis=0)
        node.reg = np.maximum(node.reg + V - nv, 0.0)
        node.avg += t * rq * sigma
        return nv
    out = 0.0
    for a in range(na):
        r2 = list(reach)
        r2[q] = rq * sigma[a]
        out = out + walk3(node.kids[a], r2, p, t, np)
    return out


def br3(node, reach, p, np):
    if node.term is not None:
        v = _tv3(node.term, reach, p)
        return v, v
    q = node.player
    sigma = _avg_np(node, np)
    na = len(node.acts)
    if q == p:
        res = [br3(node.kids[a], reach, p, np) for a in range(na)]
        best = np.max(np.array([r[0] for r in res]), axis=0)
        cur = (sigma * np.array([r[1] for r in res])).sum(axis=0)
        return best, cur
    ob, oa = 0.0, 0.0
    for a in range(na):
        r2 = list(reach)
        r2[q] = reach[q] * sigma[a]
        b, v = br3(node.kids[a], r2, p, np)
        ob, oa = ob + b, oa + v
    return ob, oa


def solve3(root, iters, every):
    g = _np_globals()
    np = g["np"]
    for n in _all_nodes(root):
        if n.term is None:
            n.reg = np.zeros((len(n.acts), N))
            n.avg = np.zeros((len(n.acts), N))
    _prep3(root)
    hist = []
    for t in range(1, iters + 1):
        for p in range(3):
            walk3(root, [np.ones(N)] * 3, p, t, np)
        if every and (t % every == 0 or t == iters):
            gains = []
            for p in range(3):
                b, v = br3(root, [np.ones(N)] * 3, p, np)
                gains.append(float((g["c"] * (b - v)).sum() / g["norm3"]))
            hist.append((t, [round(x, 6) for x in gains]))
    return hist


def encode_np(root, np):
    out = {}
    for n in _all_nodes(root):
        if n.term is not None:
            continue
        s = _avg_np(n, np)
        na = len(n.acts)
        chars = []
        for i in range(N):
            qs = [int(round(float(s[a][i]) * Q)) for a in range(na)]
            k = max(range(na), key=lambda a: s[a][i])
            qs[k] += Q - sum(qs)
            chars.append("".join(chr(48 + x) for x in qs))
        out[n.key] = {"p": n.player, "a": "".join(n.acts), "s": "".join(chars)}
    return out


def solve_three_cfg(args):
    st, rho, iters, every = args
    t0 = time.time()
    import numpy as np

    root, meta = three_tree(st, rho)
    hist = solve3(root, iters, every)
    expl = hist[-1][1] if hist else None
    return st, rho, {"meta": meta, "nodes": encode_np(root, np), "iters": iters, "expl": expl,
                     "expl_mprize": round(1000 * sum(expl), 3) if expl else None, "history": hist,
                     "secs": round(time.time() - t0, 1)}


def cmd_three(a):
    grid = [float(x) for x in a.grid.split(",")] if a.grid else THREE_GRID
    rho = float(a.rho)
    cfgs = [(x, y, z) for x in grid for y in grid for z in grid]
    if a.only:
        cfgs = [tuple(float(v) for v in a.only.split(","))]
    jobs = [(list(c), rho, a.iters, a.every) for c in cfgs]
    out = {"version": 1, "kind": "three", "q": Q, "classes": list(CLASSES), "grid": list(grid), "rho": [rho],
           "solve": {}}
    t0 = time.time()
    with Pool(a.workers) as p:
        for st, r, res in p.imap_unordered(solve_three_cfg, jobs):
            key = "%g,%g,%g" % tuple(st)
            out["solve"][key] = res
            print(f"{key:>12} iters {res['iters']} expl {res['expl_mprize']} mprize/hand ({res['secs']} s)",
                  flush=True)
    out["secs"] = round(time.time() - t0, 1)
    path = a.out or os.path.join(TABLES_DIR, "short_3.json")
    with open(path, "w") as fh:
        json.dump(compact(out), fh, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "bytes")


def compact(out):
    """The solutions as one zlib-compressed, base85 string ("z": decoded once at load); convergence stays readable."""
    import base64
    import zlib

    nodes = {k: v["nodes"] for k, v in out["solve"].items()}
    raw = json.dumps(nodes, separators=(",", ":")).encode()
    res = {k: v for k, v in out.items() if k != "solve"}
    res["meta"] = {k: {kk: vv for kk, vv in v.items() if kk != "nodes"} for k, v in out["solve"].items()}
    res["z"] = base64.b85encode(zlib.compress(raw, 9)).decode()
    return res


def cmd_compact(a):
    with open(a.src) as fh:
        out = json.load(fh)
    if "z" in out:
        raise SystemExit("already compact")
    with open(a.dst, "w") as fh:
        json.dump(compact(out), fh, separators=(",", ":"))
    print("wrote", a.dst, os.path.getsize(a.dst), "bytes")


# ------------------------------------------------------------------------------------------------ jobs
def _norm2():
    return _globals()["total"]


def solve_hu_depth(args):
    S, iters, every = args
    t0 = time.time()
    root, meta = hu_tree(S)
    hist = solve(root, 2, iters, _norm2(), check_every=every)
    expl = hist[-1][1] if hist else None
    return S, {"meta": meta, "nodes": encode(root), "iters": iters, "expl_bb": expl,
               "expl_mbb": round(1000 * sum(expl), 2) if expl else None, "history": hist,
               "secs": round(time.time() - t0, 1)}


def cmd_hu(a):
    depths = [float(x) for x in a.depths.split(",")] if a.depths else HU_DEPTHS
    jobs = [(S, a.iters, a.every) for S in depths]
    out = {"version": 1, "kind": "hu", "q": Q, "classes": list(CLASSES), "depths": list(depths), "solve": {}}
    t0 = time.time()
    with Pool(a.workers) as p:
        for S, res in p.imap_unordered(solve_hu_depth, jobs):
            key = ("%g" % S)
            out["solve"][key] = res
            print(f"S={key:>5} iters {res['iters']} expl {res['expl_mbb']} mbb/hand ({res['secs']} s)", flush=True)
    out["secs"] = round(time.time() - t0, 1)
    path = a.out or os.path.join(TABLES_DIR, "short_hu.json")
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "bytes")


def cmd_check(a):
    """The heads-up tree cut to push / fold, against the repo's push/fold solution (tables/pushfold_hu.json)."""
    S = float(a.depth)
    root, _ = hu_tree(S)
    # keep only fold and jam at the root, fold and call vs the jam
    keep = [k for k, x in zip(root.acts, root.kids) if k in ("f", "j")]
    kids = [x for k, x in zip(root.acts, root.kids) if k in ("f", "j")]
    root.acts, root.kids = keep, kids
    root.reg = [[0.0] * N for _ in keep]
    root.avg = [[0.0] * N for _ in keep]
    hist = solve(root, 2, a.iters, _norm2(), check_every=50,
                 log=lambda t, g: print(t, [round(1000 * x, 2) for x in g], flush=True))
    s = _avg_strategy(root)
    jam = s[1]
    call = _avg_strategy(root.kids[1])[1]
    pf = read_json(os.path.join(TABLES_DIR, "pushfold_hu.json"))
    key = str(int(S))
    ref_p, ref_c = pf["push"][key], pf["call"][key]
    tot = sum(COMBO_COUNT)
    print("push freq ours %.3f ref %.3f" % (sum(COMBO_COUNT[i] * jam[i] for i in range(N)) / tot, pf["p_push"][key]))
    print("call freq ours %.3f ref %.3f" % (sum(COMBO_COUNT[i] * call[i] for i in range(N)) / tot, pf["p_call"][key]))
    dp = [CLASSES[i] for i in range(N) if (jam[i] >= 0.5) != bool(ref_p[i])]
    dc = [CLASSES[i] for i in range(N) if (call[i] >= 0.5) != bool(ref_c[i])]
    print("push differs:", dp)
    print("call differs:", dc)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    h = sub.add_parser("hu")
    h.add_argument("--iters", type=int, default=600)
    h.add_argument("--every", type=int, default=100)
    h.add_argument("--workers", type=int, default=2)
    h.add_argument("--depths", default=None)
    h.add_argument("--out", default=None)
    t = sub.add_parser("three")
    t.add_argument("--iters", type=int, default=300)
    t.add_argument("--every", type=int, default=100)
    t.add_argument("--workers", type=int, default=2)
    t.add_argument("--grid", default=None)
    t.add_argument("--rho", default="0.4")
    t.add_argument("--only", default=None)
    t.add_argument("--out", default=None)
    k = sub.add_parser("compact")
    k.add_argument("src")
    k.add_argument("dst")
    c = sub.add_parser("check")
    c.add_argument("--depth", default="10")
    c.add_argument("--iters", type=int, default=300)
    a = p.parse_args(argv)
    {"hu": cmd_hu, "three": cmd_three, "check": cmd_check, "compact": cmd_compact}[a.cmd](a)


if __name__ == "__main__":
    main()
