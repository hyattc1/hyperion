"""rival_bot.py -- "No Limit" SNG bot from a computation-first team (60-minute build).

Philosophy: whatever can be computed at import IS computed at import (budget 5 s, unmetered):
  * a 7-card evaluator on rank/suit bitmasks (only 8192-entry helper tables);
  * a 169x169 all-in equity matrix and the 169-class equity vs 1 / 2 / 4 random hands, by
    Monte Carlo over shared random boards (card-removal-correct, bit-sliced counters);
  * combo-weighted equity percentiles -> open / 3-bet / call ranges by players behind;
  * push/fold by iterated best response on the matrix for 1..7 players behind, 12 depths,
    stored as (fold probability, equity-when-called) so act() can re-price with ICM;
  * Malmuth-Harville ICM: exact per hand at <= 7 players (first decision of the hand),
    a canonical table at 8; both interpolated as a utility curve over our chip count.
act() is lookups and arithmetic plus a time-boxed postflop equity sample, wrapped in
try/except with a legal fallback. Opponent model: two Beta-prior numbers per seat.
"""
import random
import time
import math
import gc
from bisect import bisect_right

try:
    from kit import Agent
except Exception:  # pragma: no cover - tournament kit always provides it
    class Agent(object):
        def new_table(self, rules, seat, n_players):
            pass

        def act(self, obs):
            raise NotImplementedError

        def hand_end(self, result):
            pass

SEED = 20262
_T_IMPORT = time.perf_counter()
PTS = [10, 7, 5, 4, 3, 2, 1, 0]

# ----------------------------------------------------------------------------- evaluator
RBIT = [1 << (c >> 2) for c in range(52)]
POP = [bin(m).count('1') for m in range(8192)]
TOP1 = [0] * 8192
for _m in range(1, 8192):
    TOP1[_m] = 1 << (_m.bit_length() - 1)
TOP2 = [TOP1[_m] | TOP1[_m ^ TOP1[_m]] for _m in range(8192)]
TOP3 = [TOP2[_m] | TOP1[_m ^ TOP2[_m]] for _m in range(8192)]
TOP5 = [TOP3[_m] | TOP2[_m ^ TOP3[_m]] for _m in range(8192)]
STR = [0] * 8192
for _m in range(8192):
    _h = 0
    for _hi in range(12, 3, -1):
        if (_m >> (_hi - 4)) & 31 == 31:
            _h = _hi
            break
    if not _h and (_m & 0b1000000001111) == 0b1000000001111:
        _h = 3
    STR[_m] = _h


def st_add(st, cards):
    """Add cards to an evaluator state (m1,m2,m3,m4,s0,s1,s2,s3)."""
    m1, m2, m3, m4, s0, s1, s2, s3 = st
    for c in cards:
        b = RBIT[c]
        m4 |= m3 & b
        m3 |= m2 & b
        m2 |= m1 & b
        m1 |= b
        s = c & 3
        if s == 0:
            s0 |= b
        elif s == 1:
            s1 |= b
        elif s == 2:
            s2 |= b
        else:
            s3 |= b
    return (m1, m2, m3, m4, s0, s1, s2, s3)


ST0 = (0, 0, 0, 0, 0, 0, 0, 0)


def ev_add2(st, ca, cb):
    """Value of state + two cards. Higher is better; equal means a chop."""
    m1, m2, m3, m4, s0, s1, s2, s3 = st
    b = RBIT[ca]
    m4 |= m3 & b
    m3 |= m2 & b
    m2 |= m1 & b
    m1 |= b
    s = ca & 3
    if s == 0:
        s0 |= b
    elif s == 1:
        s1 |= b
    elif s == 2:
        s2 |= b
    else:
        s3 |= b
    b = RBIT[cb]
    m4 |= m3 & b
    m3 |= m2 & b
    m2 |= m1 & b
    m1 |= b
    s = cb & 3
    if s == 0:
        s0 |= b
    elif s == 1:
        s1 |= b
    elif s == 2:
        s2 |= b
    else:
        s3 |= b
    if POP[s0] >= 5:
        f = s0
    elif POP[s1] >= 5:
        f = s1
    elif POP[s2] >= 5:
        f = s2
    elif POP[s3] >= 5:
        f = s3
    else:
        f = 0
    if f:
        h = STR[f]
        if h:
            return (8 << 26) | h
        return (5 << 26) | TOP5[f]
    if m4:
        return (7 << 26) | (m4 << 13) | TOP1[m1 ^ m4]
    if m3:
        t = TOP1[m3]
        p = m2 ^ t
        if p:
            return (6 << 26) | (t << 13) | TOP1[p]
    h = STR[m1]
    if h:
        return (4 << 26) | h
    if m3:
        return (3 << 26) | (m3 << 13) | TOP2[m1 ^ m3]
    if m2:
        if m2 & (m2 - 1):
            t = TOP2[m2]
            return (2 << 26) | (t << 13) | TOP1[m1 ^ t]
        return (1 << 26) | (m2 << 13) | TOP3[m1 ^ m2]
    return TOP5[m1]


def evaluate(cards):
    cards = list(cards)
    return ev_add2(st_add(ST0, cards[:-2]), cards[-2], cards[-1])


# ----------------------------------------------------------------------------- 169 classes
def cls_of(c1, c2):
    r1, r2 = c1 >> 2, c2 >> 2
    if r1 < r2:
        r1, r2 = r2, r1
    if r1 == r2:
        return r1
    p = r1 * (r1 - 1) // 2 + r2
    return (13 + p) if (c1 & 3) == (c2 & 3) else (91 + p)


CLS = [cls_of(a, b) if a != b else 0 for a in range(52) for b in range(52)]
COMBOS = [[] for _ in range(169)]
for _a in range(52):
    for _b in range(_a + 1, 52):
        COMBOS[CLS[_a * 52 + _b]].append((_a, _b, (1 << _a) | (1 << _b)))
NMAX = [len(x) for x in COMBOS]
RANKS = '23456789TJQKA'


def cls_name(i):
    if i < 13:
        return RANKS[i] * 2
    p = i - 13 if i < 91 else i - 91
    r1 = 1
    while (r1 + 1) * r1 // 2 <= p:
        r1 += 1
    r2 = p - r1 * (r1 - 1) // 2
    return RANKS[r1] + RANKS[r2] + ('s' if i < 91 else 'o')


# ----------------------------------------------------------------------------- import-time Monte Carlo
NPL = 12  # bit planes per counter: up to 4095 boards


def _mc_tables(budget_s, bmax):
    rng = random.Random(SEED)
    W = [[0] * NPL for _ in range(169)]
    V = [[0] * NPL for _ in range(169)]
    cnt = [0] * 169
    win = [[0.0, 0.0, 0.0] for _ in range(169)]
    deck = list(range(52))
    t_end = time.perf_counter() + budget_s
    boards = 0
    rr = rng.random
    while boards < bmax:
        if (boards & 31) == 0 and time.perf_counter() > t_end:
            break
        rng.shuffle(deck)
        board = deck[:5]
        rest = deck[5:]
        bm = 0
        for c in board:
            bm |= 1 << c
        st = st_add(ST0, board)
        usedby = [0] * 52
        vals = [0] * 169
        combo = [None] * 169
        valid = []
        vmask = 0
        for i in range(169):
            av = [cb for cb in COMBOS[i] if not (cb[2] & bm)]
            n = len(av)
            if not n or rr() * NMAX[i] >= n:
                continue
            cb = av[int(rr() * n)]
            combo[i] = cb
            vals[i] = ev_add2(st, cb[0], cb[1])
            bit = 1 << i
            usedby[cb[0]] |= bit
            usedby[cb[1]] |= bit
            valid.append(i)
            vmask |= bit
        rng.shuffle(valid)  # random tie-break -> E[i][j] + E[j][i] == 1 exactly
        valid.sort(key=vals.__getitem__)
        acc = 0
        for i in valid:
            cb = combo[i]
            ex = usedby[cb[0]] | usedby[cb[1]]
            m = acc & ~ex
            pl = W[i]
            k = 0
            while m:
                p = pl[k]
                pl[k] = p ^ m
                m = p & m
                k += 1
            m = vmask & ~ex
            pl = V[i]
            k = 0
            while m:
                p = pl[k]
                pl[k] = p ^ m
                m = p & m
                k += 1
            acc |= 1 << i
        for _ in range(3):
            v = rng.sample(rest, 8)
            a = ev_add2(st, v[0], v[1])
            b = ev_add2(st, v[2], v[3])
            c = ev_add2(st, v[4], v[5])
            d = ev_add2(st, v[6], v[7])
            m1 = a
            m2 = a if a > b else b
            m4 = m2
            if c > m4:
                m4 = c
            if d > m4:
                m4 = d
            cm = (usedby[v[0]] | usedby[v[1]] | usedby[v[2]] | usedby[v[3]] |
                  usedby[v[4]] | usedby[v[5]] | usedby[v[6]] | usedby[v[7]])
            for i in valid:
                if (cm >> i) & 1:
                    continue
                x = vals[i]
                w = win[i]
                cnt[i] += 1
                if x > m1:
                    w[0] += 1.0
                elif x == m1:
                    w[0] += 0.5
                if x > m2:
                    w[1] += 1.0
                elif x == m2:
                    w[1] += 0.5
                if x > m4:
                    w[2] += 1.0
                elif x == m4:
                    w[2] += 0.5
        boards += 1
    # decode bit-sliced counters
    E = [[0.5] * 169 for _ in range(169)]
    for i in range(169):
        rw = [0] * 169
        rv = [0] * 169
        Wi = W[i]
        Vi = V[i]
        for k in range(NPL):
            p = Wi[k]
            if p:
                bits = [(p >> j) & 1 for j in range(169)]
                rw = [x | (y << k) for x, y in zip(rw, bits)]
            p = Vi[k]
            if p:
                bits = [(p >> j) & 1 for j in range(169)]
                rv = [x | (y << k) for x, y in zip(rv, bits)]
        Ei = E[i]
        for j in range(169):
            if j != i and rv[j]:
                Ei[j] = rw[j] / rv[j]
    E2 = [0.0] * 169
    E4 = [0.0] * 169
    E1s = [0.0] * 169
    for i in range(169):
        c = cnt[i] or 1
        E1s[i] = win[i][0] / c
        E2[i] = win[i][1] / c
        E4[i] = win[i][2] / c
    return E, E1s, E2, E4, boards


MC_BUDGET = 2.4
MC_BOARDS = 1500
E, E1S, E2, E4, MC_N = _mc_tables(MC_BUDGET, MC_BOARDS)

# card-removal weights: WREM[i][j] = number of class-j combos disjoint from a class-i combo
WREM = []
for _i in range(169):
    _mi = COMBOS[_i][0][2]
    WREM.append([sum(1 for cb in COMBOS[_j] if not (cb[2] & _mi)) for _j in range(169)])
WTOT = [float(sum(r)) for r in WREM]
E1 = [sum(WREM[i][j] * E[i][j] for j in range(169)) / WTOT[i] for i in range(169)]


def _percentiles(eq):
    order = sorted(range(169), key=lambda i: -eq[i])
    cum = []
    pct = [0.0] * 169
    acc = 0
    for i in order:
        acc += NMAX[i]
        pct[i] = acc / 1326.0
        cum.append(acc / 1326.0)
    return order, cum, pct


ORDER1, CUM1, P1 = _percentiles(E1)
ORDER2, CUM2, P2 = _percentiles(E2)
ORDER4, CUM4, P4 = _percentiles(E4)


def _value_ranking():
    top = [i for i in range(169) if P1[i] <= 0.20]
    eq = [0.0] * 169
    for j in range(169):
        row = WREM[j]
        er = E[j]
        w = we = 0.0
        for i in top:
            x = row[i]
            w += x
            we += x * er[i]
        eq[j] = we / w if w else 0.5
    return eq


def top_set(order, cum, frac):
    """Classes in the top `frac` of a ranking (combo weighted)."""
    m = bisect_right(cum, frac)
    if m < 1:
        m = 1
    return order[:m]


def equity_vs_set(j, classes):
    """Equity of class j against a uniform-combo set of classes (card removal applied)."""
    row = WREM[j]
    er = E[j]
    w = 0.0
    we = 0.0
    for i in classes:
        x = row[i]
        w += x
        we += x * er[i]
    return we / w if w else 0.5


EV20 = _value_ranking()
ORDERV, CUMV, PV = _percentiles(EV20)


# ----------------------------------------------------------------------------- push/fold solve
from operator import mul

WR = [[float(x) for x in row] for row in WREM]
WE = [[WREM[i][j] * E[i][j] for j in range(169)] for i in range(169)]
DEPTHS = [2.0, 3.0, 4.0, 5.0, 6.0, 8.0, 10.0, 12.0, 15.0, 20.0]
KS = [1, 2, 3, 5, 7]


def _solve_pushfold(iters=10):
    """Fictitious play: pusher vs k symmetric callers, chip EV, equal stacks s (bb).
    PF[k][d] = (push flags, F = fold prob of one caller vs our push, Ec = our equity when called,
    call flags). Strategies are the time-averages of best responses (damped, converges)."""
    out = {}
    for k in KS:
        bp = 0.5 if k == 1 else 0.0
        bc = 1.0 if k == 1 else 1.5 / k
        D = 1.5
        pbar = [1.0 if P1[j] <= 0.5 else 0.0 for j in range(169)]
        cbar = [1.0 if P1[j] <= 0.3 else 0.0 for j in range(169)]
        per_depth = []
        warm = 0
        for s in DEPTHS:
            G = 2 * s + D - bp - bc
            for it in range(1, iters + 1):
                bp_ = [0.0] * 169
                for i in range(169):
                    wc = sum(map(mul, WR[i], cbar))
                    F = 1.0 - wc / WTOT[i]
                    Ec = sum(map(mul, WE[i], cbar)) / wc if wc > 1e-9 else 0.5
                    Fk = F ** k
                    ev = Fk * (D - bp) + (1.0 - Fk) * (Ec * G - s)
                    if ev > -bp:
                        bp_[i] = 1.0
                bc_ = [0.0] * 169
                for j in range(169):
                    wp = sum(map(mul, WR[j], pbar))
                    Ej = sum(map(mul, WE[j], pbar)) / wp if wp > 1e-9 else 0.5
                    if Ej * G - s > -bc:
                        bc_[j] = 1.0
                a = 1.0 / (it + warm)
                pbar = [(1 - a) * x + a * y for x, y in zip(pbar, bp_)]
                cbar = [(1 - a) * x + a * y for x, y in zip(cbar, bc_)]
            warm = 3
            Fs = [0.0] * 169
            Ecs = [0.5] * 169
            for i in range(169):
                wc = sum(map(mul, WR[i], cbar))
                Fs[i] = 1.0 - wc / WTOT[i]
                Ecs[i] = sum(map(mul, WE[i], cbar)) / wc if wc > 1e-9 else 0.5
            per_depth.append(([1 if x > 0.5 else 0 for x in pbar], Fs, Ecs,
                              [1 if x > 0.5 else 0 for x in cbar], pbar[:], cbar[:]))
        out[k] = per_depth
    return out


PF = _solve_pushfold()

# re-shove: opener's best-response call set vs a shover whose range is the top X of P1
RESHOVE_X = [0.08, 0.12, 0.18, 0.26]
RESHOVE_CALL = {}
for _d in DEPTHS:
    row = []
    for _x in RESHOVE_X:
        sh = top_set(ORDER1, CUM1, _x)
        thr = (_d - 2.5) / (2 * _d + 1.5)
        row.append([1 if equity_vs_set(j, sh) > thr else 0 for j in range(169)])
    RESHOVE_CALL[_d] = row


def pf_index(s):
    """Interpolation weights over DEPTHS for effective stack s (bb)."""
    if s <= DEPTHS[0]:
        return 0, 0, 0.0
    if s >= DEPTHS[-1]:
        return len(DEPTHS) - 1, len(DEPTHS) - 1, 0.0
    hi = bisect_right(DEPTHS, s)
    lo = hi - 1
    t = (s - DEPTHS[lo]) / (DEPTHS[hi] - DEPTHS[lo])
    return lo, hi, t


def k_index(k):
    if k <= 1:
        return 1, 1, 0.0
    if k >= 7:
        return 7, 7, 0.0
    if k == 6:
        return 5, 7, 0.5
    if k == 4:
        return 3, 5, 0.5
    return k, k, 0.0


def push_params(cls, k, s):
    """(F, Ec) for pushing class cls with k players behind at effective depth s, interpolated."""
    k0, k1, tk = k_index(k)
    lo, hi, t = pf_index(s)
    F = Ec = 0.0
    for kk, wk in ((k0, 1 - tk), (k1, tk)):
        if wk == 0:
            continue
        tab = PF[kk]
        F += wk * ((1 - t) * tab[lo][1][cls] + t * tab[hi][1][cls])
        Ec += wk * ((1 - t) * tab[lo][2][cls] + t * tab[hi][2][cls])
    return F, Ec


def push_range(k, s):
    """Push set (list of classes) for k behind at depth s, nearest grid point."""
    k0, k1, tk = k_index(k)
    kk = k1 if tk > 0.5 else k0
    lo, hi, t = pf_index(s)
    d = hi if t > 0.5 else lo
    flags = PF[kk][d][0]
    return [i for i in range(169) if flags[i]]


# ----------------------------------------------------------------------------- ICM
def mh_points(stacks, me, pts):
    """Exact Malmuth-Harville expected points for player `me` (stacks all > 0)."""
    n = len(stacks)
    others = [j for j in range(n) if j != me]
    m = len(others)
    T = float(sum(stacks))
    sm = stacks[me]
    N = 1 << m
    f = [0.0] * N
    f[0] = 1.0
    sumS = [0.0] * N
    for S in range(1, N):
        low = S & -S
        sumS[S] = sumS[S ^ low] + stacks[others[low.bit_length() - 1]]
    place = [0.0] * n
    ob = [(1 << j, stacks[others[j]]) for j in range(m)]
    for S in range(N):
        fS = f[S]
        if fS == 0.0:
            continue
        rem = T - sumS[S]
        place[POP[S]] += fS * sm / rem
        for b, sj in ob:
            if not (S & b):
                f[S | b] += fS * sj / rem
    return sum(place[q] * pts[q] for q in range(n))


# canonical table: n equal opponents, our stack = m x average
CANON_M = [0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.5]
CANON = {}
for _n in range(2, 9):
    row = []
    for _mm in CANON_M:
        _T = 100.0 * _n
        _mine = _mm * 100.0
        if _mine >= _T - 1:
            row.append(float(PTS[0]))
            continue
        _o = (_T - _mine) / (_n - 1)
        row.append(mh_points([_mine] + [_o] * (_n - 1), 0, PTS))
    CANON[_n] = row


def canon_u(n, m):
    """Interpolated canonical ICM points for stack multiple m at n players."""
    row = CANON[max(2, min(8, n))]
    if m <= CANON_M[0]:
        return row[0] * m / CANON_M[0]
    if m >= CANON_M[-1]:
        return row[-1]
    hi = bisect_right(CANON_M, m)
    lo = hi - 1
    t = (m - CANON_M[lo]) / (CANON_M[hi] - CANON_M[lo])
    return row[lo] * (1 - t) + row[hi] * t


class Curve(object):
    """Piecewise-linear utility of our chip count (expected points)."""
    __slots__ = ('xs', 'us')

    def __init__(self, xs, us):
        self.xs = xs
        self.us = us

    def u(self, x):
        xs = self.xs
        us = self.us
        if x <= xs[0]:
            return us[0]
        if x >= xs[-1]:
            return us[-1]
        hi = bisect_right(xs, x)
        lo = hi - 1
        t = (x - xs[lo]) / (xs[hi] - xs[lo])
        return us[lo] * (1 - t) + us[hi] * t

    def req(self, fold_x, lose_x, win_x):
        """Equity needed so that gambling (win_x / lose_x) beats the sure fold_x."""
        uw = self.u(win_x)
        ul = self.u(lose_x)
        uf = self.u(fold_x)
        if uw <= ul:
            return 1.01
        r = (uf - ul) / (uw - ul)
        return r


def build_curve(totals, me, n_cap=8):
    """ICM curve for seat me from hand-start totals (0 = busted). Exact MH at <= n_cap alive."""
    alive = [i for i in range(len(totals)) if totals[i] > 0]
    n = len(alive)
    T = float(sum(totals[i] for i in alive))
    s0 = float(totals[me])
    if n <= 1 or s0 <= 0:
        return Curve([0.0, 1.0], [0.0, 0.0]), n
    pts = PTS[:n]
    u0 = float(pts[-1])
    uT = float(pts[0])
    if n == 2:
        return Curve([0.0, T], [u0, uT]), n
    knots = [0.5 * s0, s0, 2.0 * s0]
    xs = [0.0]
    us = [u0]
    if n <= n_cap:
        idx = alive.index(me)
        others = [float(totals[i]) for i in alive if i != me]
        rest = T - s0
        for x in knots:
            if x >= T - 1e-9:
                continue
            scale = (T - x) / rest if rest > 0 else 0.0
            st = [o * scale for o in others]
            st.insert(idx, x)
            xs.append(x)
            us.append(mh_points(st, idx, pts))
    else:
        avg = T / n
        for x in knots:
            if x >= T - 1e-9:
                continue
            xs.append(x)
            us.append(canon_u(n, x / avg))
    xs.append(T)
    us.append(uT)
    # enforce monotone (numerical safety)
    for i in range(1, len(us)):
        if us[i] < us[i - 1]:
            us[i] = us[i - 1]
    return Curve(xs, us), n


# ----------------------------------------------------------------------------- the bot
def f_open(k, hu=False):
    """Open-raise fraction with k players behind (combo weighted)."""
    if hu:
        return 0.62
    return 0.52 * (0.80 ** (k - 1))


def clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class Bot(Agent):
    MC_BUDGET_US = 260.0
    MC_MAX = 160
    DEBUG = False

    def __init__(self):
        self.new_table({}, 0, 8)

    # ------------------------------------------------------------------ bookkeeping
    def new_table(self, rules, seat, n_players):
        self.me = seat if isinstance(seat, int) else 0
        self.n = n_players if isinstance(n_players, int) and n_players > 1 else 8
        self.rng = random.Random(SEED * 31 + self.me)
        self.opp = {}  # seat -> [vpip_a, vpip_b, fta_a, fta_b]
        self.cur = None
        self.hands_seen = 0
        self._new_hand(None)

    def _new_hand(self, hand_no):
        self.cur = hand_no
        self.hist_i = 0
        self.entered = set()
        self.saw_fold = set()
        self.seen_seats = set()
        self.invested = set()
        self.pending_aggr = False
        self.aggr_seat = None
        self.street_of_entry = {}
        self.curve = None
        self.n_alive = 8
        self.totals = None
        self.pre_raisers = []
        self.we_raised_pre = False
        self.we_aggr_street = -1
        self.last_street = -1
        self.street_aggr = {}  # street -> last aggressor seat
        self.opp_range = {}  # seat -> P1 cutoff
        self.last_obs_pack = None

    def _o(self, seat):
        o = self.opp.get(seat)
        if o is None:
            o = [1.5, 4.5, 1.5, 1.5]
            self.opp[seat] = o
        return o

    def vpip(self, seat):
        o = self._o(seat)
        return o[0] / (o[0] + o[1])

    def fta(self, seat):
        o = self._o(seat)
        return o[2] / (o[2] + o[3])

    def _finish_hand(self):
        """Fold the previous hand's observations into the per-seat Beta counters."""
        pack = self.last_obs_pack
        if pack is None:
            return
        n, in_hand, stacks = pack
        for s in range(n):
            if s == self.me:
                continue
            o = self._o(s)
            if s in self.entered:
                o[0] += 1.0
            elif s in self.saw_fold or s in self.seen_seats:
                o[1] += 1.0

    def hand_end(self, result):
        try:
            if isinstance(result, dict):
                hn = result.get('hand_no')
                if hn is not None and hn == self.cur:
                    self._finish_hand()
                    self.last_obs_pack = None
        except Exception:
            pass

    # ------------------------------------------------------------------ history parsing
    def _parse_history(self, hist, street, bb, sb_seat, bb_seat, in_hand, n):
        """Incremental pass over obs.history: who entered, who folded to aggression."""
        i = self.hist_i
        L = len(hist)
        while i < L:
            h = hist[i]
            i += 1
            try:
                seat, act = h
                kind = act[0]
                amt = act[1] if len(act) > 1 else 0
            except Exception:
                continue
            if not isinstance(seat, int) or seat == self.me:
                if seat == self.me and kind == 'raise':
                    self.pending_aggr = True
                    self.aggr_seat = seat
                    self.street_aggr[street] = seat
                    if street == 0:
                        self.pre_raisers.append(seat)
                        self.we_raised_pre = True
                continue
            self.seen_seats.add(seat)
            if kind == 'raise':
                if street == 0:
                    try:
                        if amt is not None and amt <= bb and seat in (sb_seat, bb_seat) and i <= 2:
                            continue  # blind post
                    except Exception:
                        pass
                    self.pre_raisers.append(seat)
                self.entered.add(seat)
                self.invested.add(seat)
                self.pending_aggr = True
                self.aggr_seat = seat
                self.street_aggr[street] = seat
                if street > 0:
                    v = self.vpip(seat)
                    fac = 0.6 if v < 0.4 else (0.8 if v < 0.7 else 0.95)
                    self.opp_range[seat] = self.opp_range.get(seat, 0.5) * fac
            elif kind == 'call':
                if street == 0:
                    try:
                        if amt is not None and amt <= bb and seat in (sb_seat, bb_seat) and i <= 2:
                            continue
                    except Exception:
                        pass
                self.entered.add(seat)
                if self.pending_aggr and seat in self.invested:
                    self._o(seat)[3] += 1.0
                self.invested.add(seat)
            elif kind == 'fold':
                self.saw_fold.add(seat)
                if self.pending_aggr and seat in self.invested:
                    self._o(seat)[2] += 1.0
            elif kind == 'check':
                if street == 0:
                    self.entered.add(seat)
                self.invested.add(seat)
        self.hist_i = L
        if street > 0:
            for s in range(n):
                if s != self.me and in_hand[s]:
                    self.entered.add(s)

    # ------------------------------------------------------------------ equity sampling
    def equity_mc(self, hole, board, cuts, deadline, fits=None):
        rng = self.rng
        rr = rng.random
        kmask = 0
        for c in hole:
            kmask |= 1 << c
        for c in board:
            kmask |= 1 << c
        unseen = [c for c in range(52) if not ((kmask >> c) & 1)]
        need = 5 - len(board)
        stb = st_add(ST0, board)
        h0, h1 = hole
        nopp = len(cuts)
        if fits is None:
            fits = [0.0] * nopp
        PAIR = 1 << 26
        reps = 2 if nopp == 1 else 1
        wins = 0.0
        n = 0
        pc = time.perf_counter
        mx = self.MC_MAX
        while True:
            if need:
                run = rng.sample(unseen, need)
                st = st_add(stb, run)
                used0 = kmask
                for c in run:
                    used0 |= 1 << c
            else:
                st = stb
                used0 = kmask
            my = ev_add2(st, h0, h1)
            for _rep in range(reps):
                used = used0
                best = 0
                for oi in range(nopp):
                    cut = cuts[oi]
                    fit = fits[oi] > 0.0 and rr() < fits[oi]
                    cb = None
                    for _try in range(8 if fit else 5):
                        u = rr() * cut
                        ci = ORDER1[bisect_right(CUM1, u)]
                        cl = COMBOS[ci]
                        cb = cl[int(rr() * len(cl))]
                        if not (cb[2] & used):
                            if not fit or ev_add2(stb, cb[0], cb[1]) >= PAIR:
                                break
                            if _try == 7:
                                break
                        cb = None
                    if cb is None:
                        for _try in range(20):
                            a = unseen[int(rr() * len(unseen))]
                            b = unseen[int(rr() * len(unseen))]
                            if a != b and not ((used >> a) & 1) and not ((used >> b) & 1):
                                cb = (a, b, (1 << a) | (1 << b))
                                break
                        if cb is None:
                            continue
                    used |= cb[2]
                    v = ev_add2(st, cb[0], cb[1])
                    if v > best:
                        best = v
                if my > best:
                    wins += 1.0
                elif my == best:
                    wins += 0.5
                n += 1
            if n >= mx:
                break
            if (n & 7) == 0 and pc() > deadline:
                break
        return wins / n if n else 0.5

    # ------------------------------------------------------------------ act
    def act(self, obs):
        try:
            a = self._act(obs)
        except Exception:
            if self.DEBUG:
                raise
            a = None
        return self._legal(a, obs)

    def _legal(self, a, obs):
        try:
            legal = set(obs.legal) if obs.legal is not None else {'fold'}
        except Exception:
            legal = {'fold'}
        kind = None
        amt = 0
        if isinstance(a, tuple) and len(a) == 2:
            kind, amt = a
        if kind == 'raise' and 'raise' in legal:
            try:
                lo = int(obs.min_raise)
                hi = int(obs.max_raise)
                if lo > hi:
                    lo, hi = hi, lo
                amt = int(round(amt))
                if amt < lo:
                    amt = lo
                if amt > hi:
                    amt = hi
                return ('raise', amt)
            except Exception:
                kind = 'call'
        if kind == 'raise':
            kind = 'call'
        if kind == 'call' and 'call' in legal:
            return ('call', 0)
        if kind == 'call' and 'check' in legal:
            return ('check', 0)
        if 'check' in legal:
            return ('check', 0)
        if kind == 'fold' and 'fold' in legal:
            return ('fold', 0)
        if 'call' in legal and kind == 'check':
            return ('call', 0)
        if 'fold' in legal:
            return ('fold', 0)
        if 'call' in legal:
            return ('call', 0)
        for k in legal:
            if k == 'raise':
                return ('raise', int(obs.min_raise))
            return (k, 0)
        return ('fold', 0)

    def _act(self, obs):
        t0 = time.perf_counter()
        me = obs.seat if isinstance(obs.seat, int) else self.me
        self.me = me
        stacks = list(obs.stacks or [])
        n = len(stacks)
        if n < 2:
            return None
        bets = list(obs.bets or [0] * n)
        in_hand = list(obs.in_hand or [True] * n)
        while len(bets) < n:
            bets.append(0)
        while len(in_hand) < n:
            in_hand.append(False)
        street = obs.street or 0
        hole = tuple(obs.hole)
        board = tuple(obs.board or ())
        pot = obs.pot or 0
        to_call = max(0, int(obs.to_call or 0))
        legal = set(obs.legal or ())
        hist = obs.history or []
        blinds = obs.blinds or (10, 20)
        sb = max(1, int(blinds[0]))
        bb = max(1, int(blinds[1]))
        button = obs.button if isinstance(obs.button, int) else 0
        hand_no = obs.hand_no
        my_stack = max(0, int(stacks[me]))
        my_bet = int(bets[me])

        if hand_no != self.cur:
            self._finish_hand()
            self._new_hand(hand_no)
            self.hands_seen += 1
        if street != self.last_street:
            self.pending_aggr = False
            self.last_street = street

        # hand-start totals and ICM curve, once per hand
        alive = [i for i in range(n) if stacks[i] > 0 or in_hand[i]]
        n_alive = len(alive)
        self.n_alive = n_alive
        if self.totals is None:
            nin = max(1, sum(1 for i in range(n) if in_hand[i]))
            self.totals = [stacks[i] + bets[i] + (pot / nin if in_hand[i] else 0) for i in range(n)]
            self.curve, _ = build_curve(self.totals, me)
        curve = self.curve
        T = sum(self.totals)

        # blinds / order
        ring = []
        for d in range(1, n + 1):
            s = (button + d) % n
            if s in alive:
                ring.append(s)
        if len(ring) == 2 and button in alive:
            sb_seat, bb_seat = button, ring[0] if ring[0] != button else ring[1]
            order = [sb_seat, bb_seat]
        else:
            sb_seat = ring[0] if ring else button
            bb_seat = ring[1] if len(ring) > 1 else sb_seat
            order = ring[2:] + ring[:2]
        self._parse_history(hist, street, bb, sb_seat, bb_seat, in_hand, n)
        self.last_obs_pack = (n, in_hand, stacks)

        pot_now = pot + sum(bets)
        mx = max(bets) if bets else 0
        hu = n_alive == 2
        cls = CLS[hole[0] * 52 + hole[1]]
        opps_in = [i for i in range(n) if in_hand[i] and i != me]
        n_opp = len(opps_in)
        if n_opp == 0:
            return ('check', 0) if 'check' in legal else ('call', 0)
        my_total = my_stack + my_bet
        excess = max(0, mx - my_total)
        win_amt = pot_now - excess  # what we gain if we call and win
        behind = []
        if street == 0:
            seen_me = False
            for s in order:
                if s == me:
                    seen_me = True
                    continue
                if seen_me and in_hand[s] and stacks[s] > 0 and (bets[s] < mx or (s == bb_seat and mx <= bb)):
                    behind.append(s)
        else:
            # postflop order starts after the button
            seen_me = False
            for d in range(1, n + 1):
                s = (button + d) % n
                if s == me:
                    seen_me = True
                    continue
                if seen_me and in_hand[s] and stacks[s] > 0 and bets[s] < mx:
                    behind.append(s)
        n_behind = len(behind)
        in_pos = (n_behind == 0)

        if street == 0:
            return self._preflop(obs, t0, me, n, stacks, bets, in_hand, hole, cls, pot, pot_now, to_call,
                                 legal, sb, bb, mx, my_stack, my_bet, my_total, order, sb_seat, bb_seat,
                                 behind, opps_in, curve, hu, win_amt, T)
        return self._postflop(obs, t0, me, n, stacks, bets, in_hand, hole, board, street, pot, pot_now,
                              to_call, legal, bb, mx, my_stack, my_bet, my_total, behind, opps_in, curve,
                              win_amt, in_pos)

    # ------------------------------------------------------------------ helpers
    def _raise_to(self, amount, obs, my_stack, my_bet, shove_frac=0.42):
        """Legal raise-to amount; shove instead when the raise commits most of the stack."""
        lo = int(obs.min_raise)
        hi = int(obs.max_raise)
        amt = int(round(amount))
        if amt < lo:
            amt = lo
        if amt > hi:
            amt = hi
        if amt - my_bet >= shove_frac * my_stack:
            amt = hi
        return ('raise', amt)

    def _opp_cut(self, seat, k_pos=None, raiser=False):
        v = self.vpip(seat)
        if raiser:
            base = f_open(k_pos if k_pos is not None else 3)
            cut = 0.5 * base + 0.5 * clamp(v, 0.06, 0.6)
        else:
            cut = clamp(v + 0.08, 0.15, 0.75)
        return clamp(cut, 0.04, 1.0)

    # ------------------------------------------------------------------ preflop
    def _preflop(self, obs, t0, me, n, stacks, bets, in_hand, hole, cls, pot, pot_now, to_call, legal,
                 sb, bb, mx, my_stack, my_bet, my_total, order, sb_seat, bb_seat, behind, opps_in,
                 curve, hu, win_amt, T):
        rng = self.rng
        my_bb = my_total / bb
        n_raises = len(self.pre_raisers)
        if n_raises == 0 and mx > bb:
            n_raises = 1
        raised = mx > bb
        k = len(behind)
        n_alive = self.n_alive
        # who is the aggressor
        agg = None
        if raised:
            others = [s for s in self.pre_raisers if s != me]
            if others:
                agg = others[-1]
            if agg is None or agg == me or bets[agg] < mx:
                cands = [s for s in opps_in if bets[s] == mx]
                if cands:
                    agg = cands[0]
        callers = [s for s in opps_in if bets[s] == mx and s != agg] if raised else []
        limpers = [s for s in opps_in if bets[s] == bb and s != bb_seat] if not raised else []
        if not raised and sb_seat in opps_in and bets[sb_seat] == bb and sb_seat != bb_seat:
            if sb_seat not in limpers:
                limpers.append(sb_seat)
        fold_x = my_stack
        pts_k = k if k > 0 else 1

        # ---- unopened or limped
        if not raised:
            if to_call == 0:
                # we are BB, checked to (limpers) -- raise with the top of range, otherwise check
                if limpers and P1[cls] <= 0.10 * (1 + 0.4 * len(limpers)):
                    return self._raise_to(bb * (3 + len(limpers)) + mx, obs, my_stack, my_bet)
                return ('check', 0)
            # effective depth vs the players who can still call us
            cover = max([stacks[s] + bets[s] for s in behind] + [0]) if behind else 0
            eff_bb = min(my_total, cover) / bb if cover else my_bb
            if limpers:
                eff_bb = min(eff_bb, max(stacks[s] + bets[s] for s in limpers) / bb)
            # push/fold zone
            if eff_bb <= 13.0 or (eff_bb <= 16.0 and k <= 2) or my_bb <= 13.0:
                F, Ec = push_params(cls, pts_k, max(2.0, eff_bb))
                if limpers:
                    F *= 0.7  # a limper calls more often
                Fk = F ** pts_k
                dead = pot_now - my_bet
                eff_chips = min(my_total, cover) if cover else my_total
                u_fold = curve.u(fold_x)
                u_steal = curve.u(my_stack + pot_now)
                u_win = curve.u(my_total + eff_chips + max(0, dead - 0))
                u_lose = curve.u(my_total - eff_chips)
                eu = Fk * u_steal + (1 - Fk) * (Ec * u_win + (1 - Ec) * u_lose)
                if eu > u_fold + 1e-9:
                    return ('raise', int(obs.max_raise))
                # tiny completion from the SB with a free look is fine when it is very cheap
                if me == sb_seat and to_call <= 0.6 * bb and P2[cls] <= 0.55 and eff_bb > 6:
                    return ('call', 0)
                return ('fold', 0)
            # open-raise by equity percentile
            fta_b = sum(self.fta(s) for s in behind) / len(behind) if behind else 0.5
            frac = f_open(k, hu) * (0.8 + 0.5 * fta_b)
            if eff_bb < 25:
                frac *= 0.85
            if k <= 2:
                rank = P1[cls]
            elif k <= 4:
                rank = P2[cls]
            else:
                rank = P4[cls]
            if limpers:
                frac *= 0.6
                rank = P1[cls]
                if rank <= frac:
                    return self._raise_to(bb * 3 + bb * len(limpers) + mx, obs, my_stack, my_bet)
                if to_call <= bb and P4[cls] <= 0.40 and eff_bb >= 20:
                    return ('call', 0)
                return ('fold', 0)
            if rank <= frac:
                size = 2.5 if eff_bb > 30 else 2.2
                if me == sb_seat:
                    size = 3.0
                if hu:
                    size = 2.5
                return self._raise_to(bb * size, obs, my_stack, my_bet)
            if me == sb_seat and to_call <= 0.6 * bb and P2[cls] <= 0.5:
                return ('call', 0)
            return ('fold', 0)

        # ---- facing a raise
        if agg is None:
            agg = opps_in[0]
        agg_total = stacks[agg] + bets[agg]
        eff_chips = min(my_total, agg_total)
        eff_bb = eff_chips / bb
        # position of the aggressor: players behind it when it raised
        try:
            ia = order.index(agg)
            k_agg = len([s for s in order[ia + 1:] if s != agg])
        except ValueError:
            k_agg = 3
        agg_cut = self._opp_cut(agg, k_agg, raiser=True)
        if n_raises >= 2:
            agg_cut = clamp(0.09 * clamp(self.vpip(agg) / 0.25, 0.6, 1.8), 0.03, 0.2)
        dead = pot_now - my_bet - bets[agg]
        u_fold = curve.u(fold_x)
        all_in_agg = stacks[agg] == 0
        committed = to_call >= 0.5 * my_stack
        big = to_call >= 0.35 * my_total or eff_bb <= 8

        # shove-calling (opponent all in, or the call commits us)
        if all_in_agg or committed or big:
            if all_in_agg and agg_total <= 22 * bb and n_raises <= 1:
                rset = push_range(k_agg, max(2.0, agg_total / bb))
                base = sum(NMAX[i] for i in rset) / 1326.0
                scale = clamp(self.vpip(agg) / 0.25, 0.6, 1.6)
                rset = top_set(ORDER1, CUM1, clamp(base * scale, 0.03, 1.0))
            else:
                cut = agg_cut if n_raises <= 1 else agg_cut
                if all_in_agg and n_raises >= 2:
                    cut = clamp(cut * 0.8, 0.03, 0.2)
                rset = top_set(ORDER1, CUM1, cut)
            e = equity_vs_set(cls, rset)
            if callers:
                e = e ** (1 + 0.6 * len(callers))
            lose_x = my_total - min(eff_chips, my_total)
            win_x = my_stack - to_call + win_amt + to_call
            req = curve.req(fold_x, my_stack - to_call, win_x)
            margin = 0.015 + 0.025 * len(behind) + (0.03 if callers else 0.0)
            if e >= req + margin:
                if 'raise' in legal and not all_in_agg and (committed or to_call >= 0.3 * my_stack or eff_bb <= 10):
                    return ('raise', int(obs.max_raise))
                return ('call', 0)
            return ('fold', 0)

        # re-shove zone
        if 4.0 <= eff_bb <= 21.0 and n_raises == 1 and 'raise' in legal:
            lo, hi, t = pf_index(eff_bb)
            d = DEPTHS[hi if t > 0.5 else lo]
            xi = 2 if eff_bb < 14 else 1
            oset = top_set(ORDER1, CUM1, agg_cut)
            cflags = RESHOVE_CALL[d][xi]
            cset = [i for i in oset if cflags[i]]
            w_o = sum(NMAX[i] for i in oset)
            w_c = sum(NMAX[i] for i in cset)
            F = 1.0 - (w_c / w_o if w_o else 1.0)
            F = min(0.85, F * clamp(self.fta(agg) / 0.5, 0.6, 1.1))
            # tighter callers behind the opener too
            F *= (0.88 ** len(behind))
            if PV[cls] > 0.5 and P1[cls] > 0.45:
                F = 0.0  # junk never re-shoves on fold equity alone
            Ec = equity_vs_set(cls, cset) if cset else 0.5
            if callers:
                Ec = Ec ** (1 + 0.5 * len(callers))
            u_steal = curve.u(my_stack + pot_now)
            u_win = curve.u(my_total + eff_chips + dead)
            u_lose = curve.u(my_total - eff_chips)
            eu = F * u_steal + (1 - F) * (Ec * u_win + (1 - Ec) * u_lose)
            if eu > u_fold + 1e-9:
                return ('raise', int(obs.max_raise))
            # BB pot-odds defence vs a small raise still allowed below, but not when short
            if not (me == bb_seat and to_call <= 2.5 * bb and my_bb > 12):
                return ('fold', 0)

        # deeper play: 3-bet / 4-bet / call / fold
        i_am_blind = me in (sb_seat, bb_seat)
        late_open = k_agg <= 3
        if n_raises >= 3 or (n_raises >= 2 and eff_bb > 45 and not (self.we_raised_pre or me in self.pre_raisers)):
            # 4-bet pots and deeper: price our hand against a tight range, ICM-adjusted
            tight = top_set(ORDERV, CUMV, 0.03 if n_raises >= 3 else 0.06)
            e = equity_vs_set(cls, tight)
            win_x = my_stack - to_call + win_amt + to_call
            req = curve.req(fold_x, my_stack - to_call, win_x)
            if e >= req + 0.04:
                if to_call >= 0.3 * my_stack or eff_bb <= 60:
                    return ('raise', int(obs.max_raise)) if 'raise' in legal else ('call', 0)
                return ('call', 0)
            return ('fold', 0)
        if n_raises >= 2:
            # facing a 3-bet
            if self.we_raised_pre or me in self.pre_raisers:
                if PV[cls] <= (0.035 if eff_bb <= 45 else 0.02):
                    if eff_bb <= 45:
                        return ('raise', int(obs.max_raise))
                    return self._raise_to(mx * 2.3, obs, my_stack, my_bet)
                if PV[cls] <= 0.12 and to_call <= 0.14 * my_stack:
                    return ('call', 0)
                if P4[cls] <= 0.2 and to_call <= 0.07 * my_stack:
                    return ('call', 0)
                return ('fold', 0)
            # cold facing a 3-bet
            if PV[cls] <= 0.02:
                if eff_bb <= 50:
                    return ('raise', int(obs.max_raise))
                return self._raise_to(mx * 2.3, obs, my_stack, my_bet)
            if PV[cls] <= 0.05 and to_call <= 0.1 * my_stack:
                return ('call', 0)
            return ('fold', 0)
        # single raise in front of us
        val3 = 0.22 * agg_cut
        if PV[cls] <= val3 and 'raise' in legal:
            size = mx * (3.0 if not i_am_blind else 3.6) + bb * 0.8 * len(callers)
            if eff_bb <= 24:
                return ('raise', int(obs.max_raise))
            self.we_raised_pre = True
            return self._raise_to(size, obs, my_stack, my_bet, shove_frac=0.36)
        if i_am_blind and late_open and not callers and eff_bb >= 24 and 'raise' in legal:
            if val3 < PV[cls] <= 0.40 * agg_cut and self.fta(agg) >= 0.42:
                if rng.random() < 0.5 * clamp(self.fta(agg) / 0.5, 0.6, 1.4):
                    self.we_raised_pre = True
                    return self._raise_to(mx * 3.6, obs, my_stack, my_bet, shove_frac=0.36)
        # flat calls
        n_in = 1 + len(callers)
        if n_in <= 1:
            e_tab = E1[cls]
        elif n_in == 2:
            e_tab = E2[cls]
        else:
            e_tab = E4[cls] if n_in >= 4 else 0.5 * (E2[cls] + E4[cls])
        req_chip = to_call / float(pot_now + to_call) if pot_now + to_call > 0 else 1.0
        if i_am_blind:
            realize = 0.74 if eff_bb < 25 else (0.84 if eff_bb < 50 else 0.9)
            if me == sb_seat:
                realize -= 0.08
            if e_tab * realize >= req_chip + 0.03 and to_call <= 0.2 * my_stack:
                return ('call', 0)
            return ('fold', 0)
        # not a blind, in position or not
        ip = len(behind) <= 2 and all(s in (sb_seat, bb_seat) for s in behind)
        if eff_bb >= 25 and to_call <= 0.1 * my_stack:
            if ip and P2[cls] <= 0.6 * agg_cut:
                return ('call', 0)
            if P4[cls] <= 0.22 and to_call <= 0.06 * eff_chips:
                return ('call', 0)
            if e_tab * 0.86 >= req_chip + 0.06 and ip:
                return ('call', 0)
        return ('fold', 0)

    # ------------------------------------------------------------------ postflop
    def _postflop(self, obs, t0, me, n, stacks, bets, in_hand, hole, board, street, pot, pot_now,
                  to_call, legal, bb, mx, my_stack, my_bet, my_total, behind, opps_in, curve, win_amt,
                  in_pos):
        rng = self.rng
        n_opp = len(opps_in)
        # opponent ranges: preflop entry cut, tightened by their aggression
        cuts = []
        for s in opps_in:
            c = self.opp_range.get(s)
            if c is None:
                if s in self.pre_raisers:
                    c = self._opp_cut(s, 3, raiser=True)
                else:
                    c = self._opp_cut(s)
                if self.pre_raisers and s not in self.pre_raisers:
                    c = clamp(c, 0.12, 0.6)
                if not self.pre_raisers:
                    c = clamp(c + 0.2, 0.3, 1.0)
                self.opp_range[s] = c
            cuts.append(clamp(c, 0.04, 1.0))
        fits = []
        pre_agg = self.pre_raisers[-1] if self.pre_raisers else None
        for s in opps_in:
            v = self.vpip(s)
            base = 0.8 if v < 0.4 else (0.6 if v < 0.7 else 0.3)
            if self.street_aggr.get(street) == s:
                fits.append(base * (0.45 if (street == 1 and s == pre_agg) else 1.0))
            elif self.street_aggr.get(street - 1) == s and street >= 2:
                fits.append(base * 0.7)
            else:
                fits.append(0.0)
        if n_opp > 3:
            cuts = cuts[:3]
            fits = fits[:3]
        deadline = t0 + self.MC_BUDGET_US * 1e-6
        e = self.equity_mc(hole, board, cuts, deadline, fits)
        fta = sum(self.fta(s) for s in opps_in) / n_opp
        we_aggr = self.street_aggr.get(street - 1) == me or (street == 1 and self.we_raised_pre)
        spr = my_stack / float(pot_now) if pot_now > 0 else 10.0
        can_raise = 'raise' in legal
        fold_x = my_stack

        my_bb = my_total / float(bb)
        cat = evaluate(list(hole) + list(board)) >> 26
        deep_weak = cat <= 1 and my_bb >= 30
        if to_call == 0:
            thr = (0.58, 0.60, 0.62)[street - 1] + 0.06 * (n_opp - 1)
            if e >= thr and can_raise:
                if e >= 0.86:
                    frac = 1.0 if street >= 2 else 0.75
                elif e >= 0.74:
                    frac = 0.75
                elif e >= 0.64:
                    frac = 0.55
                else:
                    frac = 0.4
                amt = mx + pot_now * frac
                if spr < 1.6 and e >= 0.72 and not (deep_weak and e < 0.85):
                    return ('raise', int(obs.max_raise))
                if (amt - my_bet) >= 0.55 * my_stack and (e < 0.72 or (deep_weak and e < 0.85)):
                    amt = my_bet + 0.4 * my_stack
                self.street_aggr[street] = me
                return self._raise_to(amt, obs, my_stack, my_bet, shove_frac=0.55)
            # bluffs / semi-bluffs
            if can_raise and n_opp == 1 and (we_aggr or in_pos) and fta >= 0.4:
                p_bluff = 0.5 * clamp(fta / 0.5, 0.6, 1.5)
                if street == 3:
                    p_bluff *= 0.5
                    ok = e <= 0.3 and (0.6 * pot_now) <= 0.25 * my_stack
                else:
                    ok = e >= 0.18 and (0.55 * pot_now) <= 0.3 * my_stack
                if ok and rng.random() < p_bluff:
                    self.street_aggr[street] = me
                    return self._raise_to(mx + pot_now * 0.55, obs, my_stack, my_bet, shove_frac=0.6)
            return ('check', 0)

        # facing a bet
        lose_x = my_stack - to_call
        win_x = my_stack + win_amt
        req = curve.req(fold_x, lose_x, win_x)
        all_in_call = to_call >= my_stack
        margin = 0.02 + 0.03 * len(behind)
        if not all_in_call and street < 3:
            margin += 0.04
        raise_thr = 0.74 + 0.05 * (n_opp - 1)
        if street == 1:
            raise_thr -= 0.02
        big_spot = to_call >= 0.5 * my_stack or (mx + pot_now + to_call - my_bet) >= 0.5 * my_stack
        if deep_weak and big_spot:
            raise_thr = max(raise_thr, 0.84)
            margin += 0.12
        if e >= raise_thr and can_raise and not all_in_call:
            amt = mx + pot_now + to_call
            if (amt - my_bet) >= 0.5 * my_stack or spr < 2.0:
                return ('raise', int(obs.max_raise))
            self.street_aggr[street] = me
            return self._raise_to(amt, obs, my_stack, my_bet, shove_frac=0.5)
        if e >= req + margin:
            return ('call', 0)
        return ('fold', 0)


# ----------------------------------------------------------------------------- warm-up and freeze
def _warm():
    try:
        from kit import Obs
    except Exception:
        return
    b = Bot()
    b.new_table({}, 2, 8)
    o = Obs(hole=(50, 46), board=(), street=0, seat=2, button=0, stacks=[2000] * 8, bets=[0, 10, 20, 0, 0, 0, 0, 0],
            in_hand=[True] * 8, pot=0, to_call=20, min_raise=40, max_raise=2000, legal={'fold', 'call', 'raise'},
            hand_no=1, blinds=(10, 20), history=[])
    b.act(o)
    o.street = 1
    o.board = (0, 17, 33)
    o.to_call = 0
    o.legal = {'check', 'raise'}
    o.min_raise = 20
    o.pot = 60
    o.bets = [0] * 8
    o.in_hand = [False, False, True, False, False, True, False, False]
    b.act(o)
    o.to_call = 40
    o.bets[5] = 40
    o.legal = {'fold', 'call', 'raise'}
    o.min_raise = 80
    b.act(o)
    o.street = 3
    o.board = (0, 17, 33, 44, 9)
    b.act(o)


_warm()
IMPORT_SECONDS = time.perf_counter() - _T_IMPORT
try:
    gc.collect()
    gc.freeze()
except Exception:
    pass
