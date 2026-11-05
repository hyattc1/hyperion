#!/usr/bin/env python
"""The short-handed specialist's preflop tables (S13): our own small solver, offline, stdlib only.

    .venv/bin/python tools/solve_short.py hu --iters 600 --workers 2          # tables/short_hu.json
    .venv/bin/python tools/solve_short.py three --iters 300 --workers 2       # tables/extra/short_3.json
    .venv/bin/python tools/solve_short.py hu2 --real FIT.json --workers 2     # tables/short_hu2.json (S20 H1)
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
    __slots__ = ("player", "acts", "kids", "key", "term", "reg", "avg", "n", "lock", "sizes")

    def __init__(self, player=-1, key=""):
        self.player = player
        self.acts: list = []
        self.kids: list = []
        self.key = key
        self.term = None
        self.reg = None
        self.avg = None
        self.lock = None  # a fixed strategy (per action, per class): a node-locked opponent (cmd_lock)
        self.sizes = None  # the raise sizes of the node's raise actions (three_tree2, hu2_tree)


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


def hu_tree(S: float, util_of=None, t3_mult: float = 3.5):
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
        t3 = round(t3_mult * r1 * 4) / 4 if t3_mult != 3.5 else round(3.5 * r1 * 2) / 2
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
    meta = {"S": S, "r1": r1, "iso": iso, "t3_mult": t3_mult}
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
    sigma = node.lock or _strategy(node)
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
        if node.lock is not None:
            return nv
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
    sigma = node.lock or _avg_strategy(node)
    na = len(node.acts)
    if q == p:
        brs, avs = [], []
        for a in range(na):
            br, av = br_walk(node.kids[a], reach, p, nplayers)
            brs.append(br)
            avs.append(av)
        if node.lock is not None:  # a locked player cannot deviate here
            cur = [sum(sigma[a][i] * avs[a][i] for a in range(na)) for i in range(N)]
            curb = [sum(sigma[a][i] * brs[a][i] for a in range(na)) for i in range(N)]
            return curb, cur
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
        if n.lock is not None:
            continue
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
    path = a.out or os.path.join(TABLES_DIR, "extra", "short_3.json")
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


# ------------------------------------------------------------------------------------------------ heads-up, v2 (S20 H1)
# The second heads-up tree (docs/drills/climb/s20-h1-log.md), pure Python like `hu`. What changed from `hu` and why:
# - the button limps only at H2_LIMP_MIN bb or deeper: no bot we measured limps heads-up, so the limped pot's
#   realization is unmeasured (S13's tree limped 35-88% of buttons at 10-20 bb on the old flop model);
# - the big blind 3-bets an open at two sizes (H2_X, multiples of the open: a size between maps on a log scale), and the
#   button answers each with fold / call / 4-bet / jam; the big blind's re-shove stays (the jam at every node);
# - the flop's share comes from our own postflop's fit (`--real`: offsets over the old model by SPR, our seat in position
#   and out of position, as tools/solve_short.py three2 reads them; default the old fixed model), and the solve is per
#   hero seat: in the solve for hero h every flop is priced at our seat's share for h's position (heads-up every flop has
#   the hero in it), and the table keeps each seat's nodes from its own solve.
# Every node records its raise sizes ("z": {action: raise-to as a multiple of the bet it faces}).
H2_X = (2.3, 3.3)
H2_R4 = 2.2
H2_LIMP_MIN = 25.0
REAL_H2_DEFAULT = {"spr": [0.0, 6.0, 8.0, 40.0],
                   "hero_ip": {"k": [0.0, 0.1875, 0.25, 0.25], "s": [0.0, 1.0, 1.0, 1.0], "c": [0.0, 0.0, 0.0, 0.0]},
                   "hero_oop": {"k": [-0.0, -0.1875, -0.25, -0.25], "s": [0.0, 1.0, 1.0, 1.0],
                                "c": [0.0, 0.0, 0.0, 0.0]}}


def _h2_interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= x:
            w = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + w * (ys[i] - ys[i - 1])
    return ys[-1]


_H2R: dict = {}


def realize_h2(real, spr, mode, key=""):
    """(IP matrix, OOP matrix) as lists, W x share, rows the player's own class, the button (class i) in position
    against the big blind (class j). mode "hero_ip": the hero is the button, its share E + k E (1 - E) + s (b_i - b_j)
    + c from real["hero_ip"]; "hero_oop": the hero is the big blind, its own share (1 - E) + k E (1 - E) - s (b_i -
    b_j) + c from real["hero_oop"] (k negative there for the old model), the button's share 1 minus it."""
    g = _globals()
    sp = round(min(spr, 40.0) * 2) / 2
    ck = (key, sp, mode)
    m = _H2R.get(ck)
    if m is not None:
        return m
    E, W, b = g["E"], g["W"], g["bonus"]
    co = real[mode]
    xs = real["spr"]
    k, s, c = (_h2_interp(xs, co[x], sp) for x in ("k", "s", "c"))
    lo, hi = real.get("clip", (0.01, 0.99))
    ip = [[0.0] * N for _ in range(N)]
    oop = [[0.0] * N for _ in range(N)]
    for i in range(N):
        Ei, Wi, bi = E[i], W[i], b[i]
        for j in range(N):
            e = Ei[j]
            ee = e * (1.0 - e)
            db = bi - b[j]
            if mode == "hero_ip":
                r = e + k * ee + s * db + c
            else:
                r = 1.0 - ((1.0 - e) + k * ee - s * db + c)
            r = lo if r < lo else hi if r > hi else r
            ip[i][j] = Wi[j] * r
            oop[j][i] = W[j][i] * (1.0 - r)
    _H2R[ck] = m = (ip, oop)
    return m


def hu2_tree(S: float, real=None, hero: int = 0, x_sizes=H2_X, limp_min: float = H2_LIMP_MIN):
    """The second heads-up tree at effective stack S (bb), chip EV, players 0 = the button (small blind), 1 = the big
    blind; flops at our seat's fitted share for `hero`'s position. Keys are the action strings from the root (f c j; r
    the node's one raise; s / t the small / big 3-bet)."""
    real = real or REAL_H2_DEFAULT
    rkey = json.dumps(real, sort_keys=True)
    mode = "hero_ip" if hero == 0 else "hero_oop"

    def util_of(c, winner):
        u = [-c[0], -c[1]]
        u[winner] += c[0] + c[1]
        return u

    r1 = 2.0 if S <= 25 else 2.25 if S <= 60 else 2.5
    iso = 3.0 if S > 12 else 2.5

    def fold(c, loser):
        return term(("fold", util_of(c, 1 - loser)))

    def showdown(c):
        return term(("sd2", 0, 1, util_of(c, 0), util_of(c, 1), None))

    def flop(c):
        pot = c[0] + c[1]
        spr = (S - c[0]) / pot
        return term(("sd2", 0, 1, util_of(c, 0), util_of(c, 1), realize_h2(real, spr, mode, rkey)))

    def jam_vs(p, c, key):
        return dec(p, key, [("f", fold(c, p)), ("c", showdown([S, S]))])

    def node(p, key, kids, sizes):
        n = dec(p, key, kids)
        n.sizes = sizes
        return n

    root = []
    root.append(("f", fold([0.5, 1.0], 0)))
    sizes0 = {}
    if S >= limp_min:
        bbl = [("c", flop([1.0, 1.0]))]
        sz = {}
        if iso <= 0.4 * S:
            ci = [1.0, iso]
            bbl.append(("r", node(0, "cr", [("f", fold(ci, 0)), ("c", flop([iso, iso])),
                                            ("j", jam_vs(1, [S, iso], "crj"))], {})))
            sz["r"] = iso
        bbl.append(("j", jam_vs(0, [1.0, S], "cj")))
        root.append(("c", node(1, "c", bbl, sz)))
    if r1 <= 0.4 * S:
        co = [r1, 1.0]
        bbo = [("f", fold(co, 1)), ("c", flop([r1, r1]))]
        szo = {}
        for ch, mult in zip("st", x_sizes):
            t3 = round(mult * r1 * 4) / 4
            if t3 > 0.4 * S:
                continue
            c3 = [r1, t3]
            sb3 = [("f", fold(c3, 0)), ("c", flop([t3, t3]))]
            sz3 = {}
            t4 = round(H2_R4 * t3 * 2) / 2
            if t4 <= 0.45 * S:
                c4 = [t4, t3]
                sb3.append(("r", node(1, "r" + ch + "r", [("f", fold(c4, 1)), ("c", flop([t4, t4])),
                                                         ("j", jam_vs(0, [t4, S], "r" + ch + "rj"))], {})))
                sz3["r"] = H2_R4
            sb3.append(("j", jam_vs(1, [S, t3], "r" + ch + "j")))
            bbo.append((ch, node(0, "r" + ch, sb3, sz3)))
            szo[ch] = mult
        bbo.append(("j", jam_vs(0, [r1, S], "rj")))
        root.append(("r", node(1, "r", bbo, szo)))
        sizes0["r"] = r1
    root.append(("j", jam_vs(1, [S, 1.0], "j")))
    n0 = node(0, "", root, sizes0)
    return n0, {"S": S, "r1": r1, "iso": iso, "x": list(x_sizes), "r4": H2_R4, "limp_min": limp_min, "hero": hero}


def encode2(root, players=None):
    """`encode` with each node's raise sizes ("z"), only the nodes of `players` (all when None)."""
    out = {}
    for n in nodes_of(root):
        if n.lock is not None or (players is not None and n.player not in players):
            continue
        s = _avg_strategy(n)
        na = len(n.acts)
        chars = []
        for i in range(N):
            qs = [int(round(s[a][i] * Q)) for a in range(na)]
            k = max(range(na), key=lambda a: s[a][i])
            qs[k] += Q - sum(qs)
            chars.append("".join(chr(48 + x) for x in qs))
        rec = {"p": n.player, "a": "".join(n.acts), "s": "".join(chars)}
        if n.sizes:
            rec["z"] = n.sizes
        out[n.key] = rec
    return out


def solve_hu2_depth(args):
    """One depth, solved once per hero seat (each seat's nodes from its own solve)."""
    S, iters, every, real, heroes = args
    t0 = time.time()
    nodes, expl, hist = {}, {}, {}
    meta = None
    for hero in heroes:
        root, meta = hu2_tree(S, real, hero)
        h = solve(root, 2, iters, _norm2(), check_every=every)
        nodes.update(encode2(root, {hero}))
        expl[str(hero)] = h[-1][1] if h else None
        hist[str(hero)] = h
    meta = dict(meta, hero=None)
    return S, {"meta": meta, "nodes": nodes, "iters": iters, "expl_bb": expl,
               "expl_mbb": {k: (round(1000 * sum(v), 2) if v else None) for k, v in expl.items()},
               "history": hist, "secs": round(time.time() - t0, 1)}


def cmd_hu2(a):
    depths = [float(x) for x in a.depths.split(",")] if a.depths else HU_DEPTHS
    real = None
    if a.real:
        with open(a.real) as fh:
            real = json.load(fh)
    heroes = [0, 1]
    path = a.out or os.path.join(TABLES_DIR, "short_hu2.json")
    out = {"version": 2, "kind": "hu2", "q": Q, "classes": list(CLASSES), "depths": list(depths), "real": real,
           "solve": {}}
    if os.path.exists(path):  # a resumed solve: the depths already saved at these iterations stand
        with open(path) as fh:
            old = json.load(fh)
        if old.get("real") == real:
            out["solve"] = {k: v for k, v in old.get("solve", {}).items()
                            if v.get("iters") == a.iters and float(k) in depths}
    jobs = [(S, a.iters, a.every, real, heroes) for S in depths if "%g" % S not in out["solve"]]

    def save():
        tmp = path + ".tmp"
        with open(tmp, "w") as fh:
            json.dump(out, fh, separators=(",", ":"))
        os.replace(tmp, path)

    t0 = time.time()
    with Pool(a.workers) as p:
        for S, res in p.imap_unordered(solve_hu2_depth, jobs):
            out["solve"]["%g" % S] = res
            print(f"S={S:>5g} iters {res['iters']} expl {res['expl_mbb']} mbb/hand ({res['secs']} s)", flush=True)
            save()  # progress: a stopped solve resumes from the depths saved here
    out["secs"] = round(time.time() - t0, 1)
    save()
    print("wrote", path, os.path.getsize(path), "bytes")


def cut_push_fold(root):
    """The root cut to fold / jam (the push/fold sanity check)."""
    keep = [i for i, x in enumerate(root.acts) if x in ("f", "j")]
    root.acts = [root.acts[i] for i in keep]
    root.kids = [root.kids[i] for i in keep]
    root.reg = [[0.0] * N for _ in keep]
    root.avg = [[0.0] * N for _ in keep]
    return root


# ------------------------------------------------------------------------------------------------ three-handed, v2 (S20)
# The second three-handed tree (docs/drills/climb/s20-log.md). What changed from `three` and why:
# - the small blind may flat the button's open (three-way and heads-up flops), and the big blind then squeezes;
# - two 3-bet sizes (T2_X: small and big, multiples of the open), so a small 3-bet is answered from its own node;
# - non-all-in 4-bets wherever the stacks allow (the opener against a 3-bet, the big blind's cold 4-bet over the small
#   blind's 3-bet), answered by fold / call / jam;
# - the flop's realization is fitted from our own postflop's measured pot shares (`--real`, a JSON of coefficients by
#   SPR) instead of the fixed E + k E (1 - E) + s (b_ip - b_oop), and it is asymmetric: `hero` is the seat whose
#   strategy the solve is for, and its flops use our postflop's fitted share (in position, out of position), the
#   others' flops a symmetric fit. A configuration is solved once per hero seat and each seat keeps its own nodes.
# The tree is built by one generic betting-round walk (`_t2_node`), so every line has the same action rules.
T2_X = (2.3, 3.3)  # 3-bets: small and big, as multiples of the open (three-handed 3-bets seen on the diagnostic seeds
#                    run 2.0-3.7x the open: exploiter 1 at 2.0-2.5, exploiter 2 and the elite builds 2.6-3.1, F,
#                    rival 2 and exploiter 3 3.1-3.7; two sizes geometric over that span)
T2_SQ = 4.0  # the squeeze over one flat, a multiple of the open
T2_R4 = 2.2  # 4-bets, a multiple of the 3-bet
T2_ISO = (2.5, 3.0)  # the big blind's raise over a limp, to this many bb (12 bb or less, deeper)
T2_CAP = 0.4  # a raise to more than this share of the effective stack is the jam (0.45 for 4-bets)
T2_GRID = (5, 8, 12, 18, 27, 40, 60, 90)

# the realization model's default coefficients (the old fixed model, for checks): per SPR knot, the in-position share
# r = E + k E (1 - E) + s (b_ip - b_oop) + c; `fit3.py` (s20) writes measured ones in the same shape
REAL_DEFAULT = {"spr": [0.0, 6.0, 8.0, 40.0],
                "sym": {"k": [0.0, 0.1875, 0.25, 0.25], "s": [0.0, 1.0, 1.0, 1.0], "c": [0.0, 0.0, 0.0, 0.0]},
                "hero_ip": None, "hero_oop": None, "w3": [0.0, 0.0, 0.0]}


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if xs[i] >= x:
            w = (x - xs[i - 1]) / (xs[i] - xs[i - 1])
            return ys[i - 1] + w * (ys[i] - ys[i - 1])
    return ys[-1]


def _coef(real, kind, spr):
    m = real.get(kind) or real["sym"]
    xs = real["spr"]
    return _interp(xs, m["k"], spr), _interp(xs, m["s"], spr), _interp(xs, m["c"], spr)


_RM2: dict = {}


def realize_fit(real, spr, mode, key=""):
    """(IP matrix, OOP matrix) as numpy arrays, W x share, rows the player's own class, for an IP player of class i
    against an OOP player of class j. mode "sym": both seats are the field (the symmetric fit); "hero_ip": the hero is
    in position (its own fitted share); "hero_oop": the hero is out of position (the IP share is 1 - the hero's)."""
    g = _np_globals()
    np = g["np"]
    sp = round(min(spr, 40.0) * 2) / 2
    ck = (key, sp, mode)
    m = _RM2.get(ck)
    if m is not None:
        return m
    G = _globals()
    E = np.array(G["E"])
    W = g["W"]
    b = np.array(G["bonus"])
    db = b[:, None] - b[None, :]  # b_ip - b_oop
    ee = E * (1.0 - E)
    if mode == "hero_oop" and real.get("hero_oop"):
        k, s, c = _coef(real, "hero_oop", sp)
        # the hero (OOP, class j) has share (1 - E) + k E (1 - E) + s (b_j - b_i) + c
        r = 1.0 - ((1.0 - E) + k * ee - s * db + c)
    else:
        k, s, c = _coef(real, "hero_ip" if mode == "hero_ip" else "sym", sp)
        r = E + k * ee + s * db + c
    lo, hi = real.get("clip", (0.01, 0.99))  # a fitted share may leave [0, 1]: postflop money beyond the pot
    r = np.clip(r, lo, hi)
    m = _RM2[ck] = (W * r, W * (1.0 - r).T)  # oop[j][i] = W[j][i] (1 - r[i][j]), as realize_mats
    return m


_W3: dict = {}


def _fl3_tensors(U_by_winner, w3, start_key=""):
    """Three-way flop: player p's prize by the three players' buckets, the pot's winner drawn from the bucket product
    model (pbest) tilted by position (w3[x]: log weight of player x's postflop seat; 0 = all-in odds)."""
    g = _np_globals()
    np = g["np"]
    pb = g["pbest"]
    ws = tuple(round(x, 4) for x in w3)
    P = _W3.get(ws)
    if P is None:
        raw = [pb[x] * math.exp(w3[x]) for x in range(3)]
        tot = raw[0] + raw[1] + raw[2]
        P = _W3[ws] = [r / tot for r in raw]
    return [sum(P[x] * U_by_winner[x][p] for x in range(3)) for p in range(3)]


def three_tree2(st, rho, real=None, hero=None, x_sizes=T2_X, flat=True, r4=True, limp_btn=False):
    """The second three-handed tree (block comment above) at stacks st = [button, SB, BB] in bb, prizes 1 / rho / 0.
    Returns (root, meta). Node keys are the action strings from the root (f c j, r = the node's one raise, s / t =
    the small / big 3-bet); every node records its raise sizes as multiples of the bet it faces ("z")."""
    real = real or REAL_DEFAULT
    rkey = json.dumps(real, sort_keys=True)
    start = [float(x) for x in st]
    pos_rank = (2, 0, 1)  # postflop order: SB first (0), then BB (1), the button last (2)

    def U(final):
        return icm3(final, start, rho)

    def eff(p, inh):
        return min(start[p], max(start[q] for q in inh if q != p))

    def r1_of(e):
        return 2.0 if e <= 25 else 2.25 if e <= 60 else 2.5

    def terminal(c, inh):
        inh = sorted(inh)
        if len(inh) == 1:
            final = [start[i] - c[i] for i in range(3)]
            final[inh[0]] += sum(c)
            return term(("fold", U(final)))
        allin = any(c[i] >= start[i] - 1e-9 for i in inh)
        if len(inh) == 2:
            a, b = inh
            ua = U(_distribute(c, start, [a, b], inh))
            ub = U(_distribute(c, start, [b, a], inh))
            mats = None
            if not allin:
                pot = sum(c)
                spr = min(start[a] - c[a], start[b] - c[b]) / pot
                ip, oop = (a, b) if pos_rank[a] > pos_rank[b] else (b, a)
                mode = "hero_ip" if hero == ip else "hero_oop" if hero == oop else "sym"
                mi, mo = realize_fit(real, spr, mode, rkey)
                mats = (mi, mo) if ip == a else (mo, mi)
            return term(("sd2", a, b, ua, ub, mats))
        if allin:
            from itertools import permutations

            outs = {order: U(_distribute(c, start, list(order), [0, 1, 2])) for order in permutations(range(3))}
            return term(("sd3", outs))
        Ub = []
        for x in range(3):
            final = [start[i] - c[i] for i in range(3)]
            final[x] += sum(c)
            Ub.append(U(final))
        w3 = [real.get("w3", [0.0, 0.0, 0.0])[pos_rank[x]] for x in range(3)]
        if hero is not None and real.get("w3_hero") is not None:
            w3[hero] = real["w3_hero"][pos_rank[hero]]
        return term(("sd3", None, _fl3_tensors(Ub, w3)))

    def node(c, inh, pending, nr, key, raisers, vol, flats):
        """c: chips in per player; inh: players in the hand; pending: players still to act, in order; nr: raises so
        far; raisers: who made each raise, in order; vol: players who put chips in voluntarily; flats: players who
        called the current raise level."""
        pending = [p for p in pending if p in inh and c[p] < start[p] - 1e-9]
        if len(inh) == 1 or not pending:
            return terminal(c, inh)
        p = pending[0]
        rest = pending[1:]
        cur = max(c)
        facing = cur > c[p] + 1e-9
        e = eff(p, inh)
        kids = []
        sizes = {}

        def after_raise(q, to):
            c2 = list(c)
            c2[q] = to
            order = [(q + d) % 3 for d in (1, 2)]
            return c2, [x for x in order if x in inh]

        jam_open = any(c[i] >= start[i] - 1e-9 for i in inh)  # someone is all in: fold / call only
        # fold
        if facing:
            inh_f = [x for x in inh if x != p]
            kids.append(("f", node(c, inh_f, rest, nr, key + "f", raisers, vol, flats)))
        # call / check / limp
        call_to = min(cur, start[p])
        c_c = list(c)
        c_c[p] = call_to
        if True:
            limp = nr == 0 and facing
            allow_call = True
            if limp and p == 0 and not limp_btn:
                allow_call = False
            if limp and p == 1 and 0 in inh:  # the small blind completing behind a limp: not in the tree
                allow_call = False
            if nr >= 2 and facing and p not in vol and not jam_open:
                allow_call = False  # no cold call of a 3-bet or more
            if nr >= 3 and facing and not jam_open and raisers and raisers[-2:-1] != [p]:
                allow_call = False  # facing a 4-bet: only the 3-bettor may call
            if allow_call:
                fl = flats + [p] if facing and nr >= 1 else flats
                kids.append(("c", node(c_c, inh, rest, nr, key + "c", raisers, vol | ({p} if facing else set()), fl)))
        # raises (none once someone is all in, and none for a player who can only call)
        if not jam_open and start[p] > cur + 1e-9:
            opts = []
            if nr == 0:
                if facing:
                    to = r1_of(e)
                    opts.append(("r", to, to / cur))
                else:  # the big blind's option over the small blind's limp
                    to = T2_ISO[0] if e <= 12 else T2_ISO[1]
                    opts.append(("r", to, to / cur))
            elif nr == 1 and raisers[0] != p:
                if p in vol and facing and not flats:
                    pass  # a limper facing the raise over its limp: fold / call / jam
                elif flats:
                    if p not in vol:
                        opts.append(("r", T2_SQ * cur, T2_SQ))  # the squeeze over the flat
                else:
                    for ch, m in zip("st", x_sizes):
                        opts.append((ch, m * cur, m))
            elif nr == 2 and r4:
                if p == raisers[0] and not flats:
                    opts.append(("r", T2_R4 * cur, T2_R4))  # the opener's 4-bet
                elif p not in vol and p != raisers[-1]:
                    opts.append(("r", T2_R4 * cur, T2_R4))  # the cold 4-bet
            for ch, to, mult in opts:
                cap = (0.45 if nr == 2 else T2_CAP) * e
                if to > cap or to >= start[p] - 1e-9:
                    continue
                c2, order = after_raise(p, to)
                kids.append((ch, node(c2, inh, order, nr + 1, key + ch, raisers + [p], vol | {p}, [])))
                sizes[ch] = round(mult, 4)
            # jam
            c2, order = after_raise(p, start[p])
            kids.append(("j", node(c2, inh, order, nr + 1, key + "j", raisers + [p], vol | {p}, [])))
        if len(kids) == 1:  # one legal line: no decision (a player who can only call an all-in)
            return kids[0][1]
        n = dec(p, key, kids)
        n.sizes = sizes
        return n

    c0 = [0.0, min(0.5, start[1]), min(1.0, start[2])]
    root = node(c0, [0, 1, 2], [0, 1, 2], 0, "", [], set(), [])
    return root, {"st": start, "rho": rho, "x": list(x_sizes), "sq": T2_SQ, "r4": T2_R4, "v": 2}


def encode_np2(root, np, players=None):
    """Nodes as encode_np, with each node's raise sizes ("z": {action: multiple of the bet it faces}); only the
    nodes of `players` (all when None)."""
    out = {}
    for n in _all_nodes(root):
        if n.term is not None or (players is not None and n.player not in players):
            continue
        s = _avg_np(n, np)
        na = len(n.acts)
        chars = []
        for i in range(N):
            qs = [int(round(float(s[a][i]) * Q)) for a in range(na)]
            k = max(range(na), key=lambda a: s[a][i])
            qs[k] += Q - sum(qs)
            chars.append("".join(chr(48 + x) for x in qs))
        rec = {"p": n.player, "a": "".join(n.acts), "s": "".join(chars)}
        z = getattr(n, "sizes", None)
        if z:
            rec["z"] = z
        out[n.key] = rec
    return out


def solve_three2_cfg(args):
    """One configuration, solved once per hero seat (each seat's nodes from its own solve), or once (hero None)."""
    st, rho, iters, every, real, heroes = args
    t0 = time.time()
    import numpy as np

    nodes, expl, hist = {}, {}, {}
    for hero in heroes:
        root, meta = three_tree2(st, rho, real, hero)
        h = solve3(root, iters, every)
        nodes.update(encode_np2(root, np, None if hero is None else {hero}))
        expl[str(hero)] = h[-1][1] if h else None
        hist[str(hero)] = h
    tot = {k: (round(1000 * sum(v), 3) if v else None) for k, v in expl.items()}
    return st, rho, {"meta": meta, "nodes": nodes, "iters": iters, "expl": expl, "expl_mprize": tot,
                     "history": hist, "secs": round(time.time() - t0, 1)}


def cmd_three2(a):
    grid = [float(x) for x in a.grid.split(",")] if a.grid else T2_GRID
    rho = float(a.rho)
    real = None
    if a.real:
        with open(a.real) as fh:
            real = json.load(fh)
    heroes = [None] if a.symmetric else [0, 1, 2]
    cfgs = [(x, y, z) for x in grid for y in grid for z in grid]
    if a.only:
        cfgs = [tuple(float(v) for v in c.split(",")) for c in a.only.split(";")]
    jobs = [(list(c), rho, a.iters, a.every, real, heroes) for c in cfgs]
    out = {"version": 2, "kind": "three2", "q": Q, "classes": list(CLASSES), "grid": list(grid), "rho": [rho],
           "real": real, "heroes": heroes, "solve": {}}
    t0 = time.time()
    with Pool(a.workers) as p:
        for st, r, res in p.imap_unordered(solve_three2_cfg, jobs):
            key = "%g,%g,%g" % tuple(st)
            out["solve"][key] = res
            print(f"{key:>12} iters {res['iters']} expl {res['expl_mprize']} mprize/hand ({res['secs']} s)",
                  flush=True)
    out["secs"] = round(time.time() - t0, 1)
    path = a.out or os.path.join(TABLES_DIR, "extra", "short_3b.json")
    with open(path, "w") as fh:
        json.dump(compact(out), fh, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "bytes")


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


LOCK_W = (0.7, 0.85, 1.0)


def top_classes(w):
    """The top share w of hands (combos) by heads-up equity percentile (tables/preflop_rank.json): per class, the
    probability it is in (the boundary class mixed)."""
    rank = read_json(os.path.join(TABLES_DIR, "preflop_rank.json"))
    order = sorted(range(N), key=lambda i: -rank[CLASSES[i]])
    out = [0.0] * N
    left = w * sum(COMBO_COUNT)
    for i in order:
        c = COMBO_COUNT[i]
        if left <= 0:
            break
        out[i] = min(1.0, left / c)
        left -= c
    return out


def solve_lock_depth(args):
    """The heads-up tree with the small blind's first action locked: open the top w of hands, fold the rest (no limps,
    no jams), as both exploiters play it; the rest solved (the big blind's counter to a wide opener)."""
    S, w, iters, every = args
    t0 = time.time()
    root, meta = hu_tree(S)
    top = top_classes(w)
    lock = []
    for a in root.acts:
        if a == "r":
            lock.append(list(top))
        elif a == "f":
            lock.append([1.0 - x for x in top])
        else:
            lock.append([0.0] * N)
    if "r" not in root.acts:  # too short for an open: the lock jams the same hands
        lock = [[1.0 - x for x in top] if a == "f" else (list(top) if a == "j" else [0.0] * N) for a in root.acts]
    root.lock = lock
    hist = solve(root, 2, iters, _norm2(), check_every=every)
    expl = hist[-1][1] if hist else None
    return S, w, {"meta": meta, "nodes": encode(root), "iters": iters, "expl_bb": expl,
                  "expl_mbb": round(1000 * sum(expl), 2) if expl else None, "history": hist,
                  "secs": round(time.time() - t0, 1)}


def cmd_lock(a):
    depths = [float(x) for x in a.depths.split(",")] if a.depths else HU_DEPTHS
    ws = [float(x) for x in a.w.split(",")] if a.w else LOCK_W
    jobs = [(S, w, a.iters, a.every) for w in ws for S in depths]
    out = {"version": 1, "kind": "hu_lock", "q": Q, "classes": list(CLASSES), "depths": list(depths), "w": ws,
           "lock": "small blind opens the top w (preflop_rank), folds the rest", "solve": {}}
    t0 = time.time()
    with Pool(a.workers) as p:
        for S, w, res in p.imap_unordered(solve_lock_depth, jobs):
            key = "%g@%g" % (S, w)
            out["solve"][key] = res
            print(f"S={key:>9} iters {res['iters']} expl {res['expl_mbb']} mbb/hand ({res['secs']} s)", flush=True)
    out["secs"] = round(time.time() - t0, 1)
    path = a.out or os.path.join(TABLES_DIR, "short_hu_lock.json")
    with open(path, "w") as fh:
        json.dump(out, fh, separators=(",", ":"))
    print("wrote", path, os.path.getsize(path), "bytes")


T3_SIZES = (2.2, 2.75)


def _decode(node_rec):
    na = len(node_rec["a"])
    st = node_rec["s"]
    return [[(ord(st[i * na + x]) - 48) / Q for i in range(N)] for x in range(na)]


def solve_size_depth(args):
    """The small blind's answer to a 3-bet of t3_mult times its open (an off-tree size): the tree rebuilt with that
    3-bet, the small blind's first action and the big blind's answer to the open locked to the equilibrium of
    tables/short_hu.json (the 3-bet's mass moved to the new size), the rest solved."""
    S, mult, iters, every, eq = args
    t0 = time.time()
    root, meta = hu_tree(S, t3_mult=mult)
    if "".join(root.acts) != eq[""]["a"] or "r" not in root.acts:
        return S, mult, None
    root.lock = _decode(eq[""])
    bbn = root.kids[root.acts.index("r")]
    if "r" not in bbn.acts or "r" not in eq or eq["r"]["a"] != "".join(bbn.acts):
        return S, mult, None
    bbn.lock = _decode(eq["r"])
    hist = solve(root, 2, iters, _norm2(), check_every=every)
    expl = hist[-1][1] if hist else None
    return S, mult, {"meta": meta, "nodes": encode(root), "iters": iters, "expl_bb": expl,
                     "expl_mbb": round(1000 * sum(expl), 2) if expl else None, "history": hist,
                     "secs": round(time.time() - t0, 1)}


def cmd_sizes(a):
    with open(os.path.join(TABLES_DIR, "short_hu.json")) as fh:
        base = json.load(fh)
    depths = [float(x) for x in a.depths.split(",")] if a.depths else [float(x) for x in base["depths"]]
    mults = [float(x) for x in a.mult.split(",")] if a.mult else T3_SIZES
    jobs = [(S, m, a.iters, a.every, base["solve"]["%g" % S]["nodes"]) for m in mults for S in depths]
    out = {"version": 1, "kind": "hu_t3", "q": Q, "classes": list(CLASSES), "depths": depths, "mult": mults,
           "lock": "root and the big blind's answer to the open locked to short_hu.json; 3-bet = mult x open",
           "solve": {}}
    t0 = time.time()
    with Pool(a.workers) as p:
        for S, m, res in p.imap_unordered(solve_size_depth, jobs):
            if res is None:
                continue
            key = "%g@%g" % (S, m)
            out["solve"][key] = res
            print(f"S={key:>9} iters {res['iters']} expl {res['expl_mbb']} mbb/hand ({res['secs']} s)", flush=True)
    out["secs"] = round(time.time() - t0, 1)
    path = a.out or os.path.join(TABLES_DIR, "short_hu_t3.json")
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
    lk = sub.add_parser("lock")
    lk.add_argument("--iters", type=int, default=400)
    lk.add_argument("--every", type=int, default=100)
    lk.add_argument("--workers", type=int, default=2)
    lk.add_argument("--depths", default=None)
    lk.add_argument("--w", default=None)
    lk.add_argument("--out", default=None)
    sz = sub.add_parser("sizes")
    sz.add_argument("--iters", type=int, default=400)
    sz.add_argument("--every", type=int, default=100)
    sz.add_argument("--workers", type=int, default=1)
    sz.add_argument("--depths", default=None)
    sz.add_argument("--mult", default=None)
    sz.add_argument("--out", default=None)
    t2 = sub.add_parser("three2")
    t2.add_argument("--iters", type=int, default=300)
    t2.add_argument("--every", type=int, default=100)
    t2.add_argument("--workers", type=int, default=2)
    t2.add_argument("--grid", default=None)
    t2.add_argument("--rho", default="0.4")
    t2.add_argument("--only", default=None, help="configurations 'b,s,B;b,s,B' (button, small blind, big blind bb)")
    t2.add_argument("--real", default=None, help="the realization model's coefficients (JSON; default the old model)")
    t2.add_argument("--symmetric", action="store_true", help="one solve per configuration, no hero seat")
    t2.add_argument("--out", default=None)
    h2 = sub.add_parser("hu2")
    h2.add_argument("--iters", type=int, default=500)
    h2.add_argument("--every", type=int, default=100)
    h2.add_argument("--workers", type=int, default=2)
    h2.add_argument("--depths", default=None)
    h2.add_argument("--real", default=None, help="the realization fit (JSON with hero_ip / hero_oop; default the old model)")
    h2.add_argument("--out", default=None)
    k = sub.add_parser("compact")
    k.add_argument("src")
    k.add_argument("dst")
    c = sub.add_parser("check")
    c.add_argument("--depth", default="10")
    c.add_argument("--iters", type=int, default=300)
    a = p.parse_args(argv)
    {"hu": cmd_hu, "three": cmd_three, "check": cmd_check, "compact": cmd_compact, "lock": cmd_lock,
     "sizes": cmd_sizes, "three2": cmd_three2, "hu2": cmd_hu2}[a.cmd](a)


if __name__ == "__main__":
    main()
