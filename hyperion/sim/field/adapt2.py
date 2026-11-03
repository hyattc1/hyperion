# Origin: the climb's held-out adaptive opponent (decisions addendum 9; docs/drills/adapt2/NOTEBOOK.md is its builder's
# notebook). A fresh agent with no repo access built it in about 81 minutes against five anonymous strong targets
# (F among them) seen only through an arena; frozen at md5 ee30b9a61161cdbf3c126a6c345bac70 and copied here unchanged
# apart from this header. The archive is docs/drills/adapt2/adapt_bot.py. Played through
# hyperion.sim.bestiary.Adapt2Bot (registry name `adapt2`): a held-out judge, never tuned on. Do not edit.
#
"""rival_bot: an adaptive no-limit hold'em sit-and-go bot (pure standard library).

Base game: position-based preflop ranges, push/fold by expected value when short (with an ICM
margin when several players are alive), a rule-based postflop hand reader (made hand + draws +
board texture) with pot-odds calling.

Learning: every opponent seat is modelled from scratch at each table, from its actions only
(the engine reveals no hole cards). Each read is a shrunk, slowly-forgetting estimate that
starts at the value the base game already assumes, so with no evidence the bot plays its base
game. A counter moves a decision only once its read leaves a dead zone around that prior, and
it moves back as soon as the evidence does. No opponent is ever identified: every counter keys
on a tendency seen at this table only.

Counters (group names for Bot.DISABLED): steal, opener, light3, f3b, shover, callshove, fbet,
agg (incl. trap), xr, size, vcall. Bot.COUNTERS = False gives the identical bot with every
counter off (reads are still kept, never used).
"""
import random

try:
    from kit import Agent
except Exception:  # pragma: no cover - fallback when the kit is absent
    class Agent(object):
        def new_table(self, rules, seat, n_players):
            pass

        def act(self, obs):
            raise NotImplementedError

        def hand_end(self, result):
            pass


# ----------------------------------------------------------------------------- evaluator

def _build_straights():
    t = [-1] * 8192
    for m in range(8192):
        hi = -1
        for top in range(12, 3, -1):
            need = 0x1F << (top - 4)
            if m & need == need:
                hi = top
                break
        if hi < 0 and (m & 0x100F) == 0x100F:
            hi = 3
        t[m] = hi
    return t


STRAIGHT_HI = _build_straights()
BITCOUNT = [bin(m).count('1') for m in range(8192)]


def ev7(cards):
    """Comparable integer for the best hand in 1..7 cards: category << 20 | kickers."""
    rc = [0] * 13
    sm = [0, 0, 0, 0]
    sc = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        r = c >> 2
        s = c & 3
        rc[r] += 1
        sc[s] += 1
        sm[s] |= 1 << r
        mask |= 1 << r
    fs = -1
    if len(cards) >= 5:
        for s in range(4):
            if sc[s] >= 5:
                fs = s
                break
    if fs >= 0:
        sh = STRAIGHT_HI[sm[fs]]
        if sh >= 0:
            return (8 << 20) | (sh << 16)
    quad = -1
    trips = []
    pairs = []
    singles = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 0:
            continue
        if n == 4:
            quad = r
        elif n == 3:
            trips.append(r)
        elif n == 2:
            pairs.append(r)
        else:
            singles.append(r)
    if quad >= 0:
        k = 0
        for r in range(12, -1, -1):
            if r != quad and rc[r]:
                k = r
                break
        return (7 << 20) | (quad << 16) | (k << 12)
    if trips and (len(trips) >= 2 or pairs):
        t = trips[0]
        p = -1
        if len(trips) > 1:
            p = trips[1]
        if pairs and pairs[0] > p:
            p = pairs[0]
        return (6 << 20) | (t << 16) | (p << 12)
    if fs >= 0:
        m = sm[fs]
        v = 5 << 20
        sh = 16
        for r in range(12, -1, -1):
            if m >> r & 1:
                v |= r << sh
                sh -= 4
                if sh < 0:
                    break
        return v
    sh = STRAIGHT_HI[mask]
    if sh >= 0:
        return (4 << 20) | (sh << 16)
    if trips:
        ks = singles + pairs
        ks.sort(reverse=True)
        v = (3 << 20) | (trips[0] << 16)
        if ks:
            v |= ks[0] << 12
        if len(ks) > 1:
            v |= ks[1] << 8
        return v
    if len(pairs) >= 2:
        rest = singles + pairs[2:]
        k = max(rest) if rest else 0
        return (2 << 20) | (pairs[0] << 16) | (pairs[1] << 12) | (k << 8)
    if pairs:
        v = (1 << 20) | (pairs[0] << 16)
        sh = 12
        for r in singles[:3]:
            v |= r << sh
            sh -= 4
        return v
    v = 0
    sh = 16
    for r in singles[:5]:
        v |= r << sh
        sh -= 4
    return v


# ----------------------------------------------------------------------------- preflop tables

# Heads-up equity (%) of each starting hand against a random hand.
_PAIR_EQ = [50.3, 53.7, 57.0, 60.3, 63.3, 66.2, 69.1, 72.1, 75.1, 77.5, 79.9, 82.4, 85.3]  # 22..AA
_SUITED_EQ = {
    12: [67.0, 66.2, 65.4, 64.7, 63.0, 62.1, 61.1, 60.0, 59.9, 58.9, 58.0, 57.0],
    11: [63.4, 62.6, 61.9, 60.0, 58.5, 57.8, 56.8, 55.8, 54.7, 53.8, 52.9],
    10: [60.3, 59.5, 57.9, 56.2, 54.5, 53.8, 52.9, 51.7, 50.7, 49.9],
    9: [57.5, 55.8, 54.2, 52.4, 50.8, 50.0, 49.0, 47.9, 47.1],
    8: [54.3, 52.6, 51.0, 49.2, 47.2, 46.4, 45.5, 44.7],
    7: [51.1, 49.5, 47.7, 45.9, 43.8, 43.2, 42.3],
    6: [48.2, 46.5, 44.8, 42.7, 40.8, 40.3],
    5: [45.7, 43.9, 42.0, 40.1, 38.1],
    4: [43.2, 41.4, 39.4, 37.5],
    3: [41.1, 39.3, 37.5],
    2: [38.0, 36.3],
    1: [35.1],
}
_OFF_EQ = {
    12: [65.4, 64.5, 63.6, 62.9, 60.9, 60.0, 59.0, 57.8, 57.7, 56.7, 55.7, 54.6],
    11: [61.4, 60.6, 59.9, 58.0, 56.3, 55.4, 54.3, 53.3, 52.1, 51.2, 50.2],
    10: [58.2, 57.4, 55.5, 53.8, 51.9, 51.1, 50.2, 49.0, 47.9, 47.0],
    9: [55.4, 53.4, 51.7, 49.9, 47.9, 47.1, 46.1, 45.0, 44.0],
    8: [51.7, 50.0, 48.2, 46.3, 44.2, 43.4, 42.4, 41.5],
    7: [48.4, 46.7, 44.9, 42.9, 40.7, 40.0, 39.1],
    6: [45.5, 43.6, 41.7, 39.6, 37.5, 37.0],
    5: [42.7, 40.9, 38.9, 36.8, 34.6],
    4: [40.1, 38.0, 36.0, 34.0],
    3: [37.9, 35.9, 34.0],
    2: [34.4, 32.5],
    1: [31.2],
}


def hid_of(r1, r2, suited):
    if r1 < r2:
        r1, r2 = r2, r1
    if r1 == r2:
        suited = 0
    return r1 * 26 + r2 * 2 + (1 if suited else 0)


def _pair_vs(p, a, b, s):
    if p > a:
        e = 0.83
    elif p == a:
        e = 0.88
    elif p > b:
        e = 0.70
    elif p == b:
        e = 0.66
    else:
        e = 0.52 + 0.004 * p
    return e - 0.03 * s


def _hh_eq(A, B):
    a1, b1, s1 = A
    a2, b2, s2 = B
    if a1 == b1 and a2 == b2:
        if a1 == a2:
            return 0.5
        return 0.81 if a1 > a2 else 0.19
    if a1 == b1:
        return _pair_vs(a1, a2, b2, s2)
    if a2 == b2:
        return 1.0 - _pair_vs(a2, a1, b1, s1)
    if a1 == a2:
        e = 0.5 if b1 == b2 else (0.71 if b1 > b2 else 0.29)
    elif b1 == b2:
        e = 0.70 if a1 > a2 else 0.30
    elif a1 == b2:
        e = 0.26
    elif b1 == a2:
        e = 0.74
    elif a1 > a2:
        if b1 > a2:
            e = 0.64
        elif b1 > b2:
            e = 0.60
        else:
            e = 0.56
    else:
        if b2 > a1:
            e = 0.36
        elif b2 > b1:
            e = 0.40
        else:
            e = 0.44
    return e + 0.025 * (s1 - s2)


def _build_preflop():
    hands = []
    for a in range(13):
        for b in range(a + 1):
            if a == b:
                hands.append((a, b, 0, _PAIR_EQ[a] / 100.0, 6))
            else:
                hands.append((a, b, 1, _SUITED_EQ[a][a - 1 - b] / 100.0, 4))
                hands.append((a, b, 0, _OFF_EQ[a][a - 1 - b] / 100.0, 12))
    scored = []
    for (a, b, s, e, w) in hands:
        sc = e
        if a != b:
            if s:
                sc += 0.02
            gap = a - b
            if b >= 3:
                if gap == 1:
                    sc += 0.012
                elif gap == 2:
                    sc += 0.006
        scored.append((sc, a, b, s, e, w))
    scored.sort(reverse=True)
    n = len(scored)
    pct = [1.0] * 338
    erand = [0.5] * 338
    order = []
    cum = 0
    for (sc, a, b, s, e, w) in scored:
        cum += w
        h = hid_of(a, b, s)
        pct[h] = cum / 1326.0
        erand[h] = e
        order.append((h, (a, b, s), w))
    # equity of each hand against the top-w% of hands, for w = 1..100 %
    eqt = [None] * 338
    for (h, hand, _w) in order:
        row = [0.5] * 101
        tot = 0.0
        acc = 0.0
        j = 1
        cumw = 0
        for (h2, hand2, w2) in order:
            acc += _hh_eq(hand, hand2) * w2
            tot += w2
            cumw += w2
            while j <= 100 and cumw >= j * 13.26 - 1e-9:
                row[j] = acc / tot
                j += 1
        while j <= 100:
            row[j] = acc / tot
            j += 1
        row[0] = row[1]
        corr = erand[h] - row[100]
        for j in range(101):
            row[j] = min(0.95, max(0.05, row[j] + corr * (j / 100.0)))
        eqt[h] = row
    return pct, erand, eqt


PCT, ERAND, EQT = _build_preflop()


def eq_vs(h, w):
    j = int(w * 100 + 0.5)
    if j < 1:
        j = 1
    elif j > 100:
        j = 100
    return EQT[h][j]


def open_width(behind, ndealt):
    """Prior open-raise width (fraction of hands) for a player with `behind` players to act."""
    if ndealt == 2:
        return 0.80
    if behind <= 1:
        return 0.42
    if behind == 2:
        return 0.46 if ndealt <= 4 else 0.42
    return {3: 0.30, 4: 0.23, 5: 0.19, 6: 0.16}.get(behind, 0.14)


def shove_prior_width(x_bb, reshove):
    w = 3.0 / max(1.0, x_bb)
    if reshove:
        w *= 0.6
    return min(0.75, max(0.03, w))


def call_shove_prior(x_bb, posted_bb):
    if posted_bb:
        w = 2.4 / max(1.0, x_bb) + 0.05
    else:
        w = 1.6 / max(1.0, x_bb) + 0.04
    return min(0.7, max(0.05, w))


def soft(d, margin):
    """Dead zone: no effect within +-margin of the prior; outside it, most of the read applies."""
    if d > margin:
        return d - 0.5 * margin
    if d < -margin:
        return d + 0.5 * margin
    return 0.0


# ----------------------------------------------------------------------------- postflop reader

def post_strength(hole, board, street):
    """(s, outs, cat): s ~ equity vs a reasonable heads-up continuing range."""
    allc = [hole[0], hole[1]] + list(board)
    v = ev7(allc)
    cat = v >> 20
    bv = ev7(board)
    bcat = bv >> 20
    h1 = hole[0] >> 2
    h2 = hole[1] >> 2
    if h1 < h2:
        h1, h2 = h2, h1
    br = [c >> 2 for c in board]
    bmask = 0
    bsc = [0, 0, 0, 0]
    for c in board:
        bmask |= 1 << (c >> 2)
        bsc[c & 3] += 1
    bdist = sorted(set(br), reverse=True)
    top = bdist[0]
    bpaired = len(bdist) < len(br)
    bmaxsuit = max(bsc)
    sd = 0
    for t in range(12, 3, -1):
        m = (0x1F << (t - 4)) & bmask
        c = BITCOUNT[m]
        if c > sd:
            sd = c
    c = BITCOUNT[bmask & 0x100F]
    if c > sd:
        sd = c
    flush_pen = 0.0
    if bmaxsuit == 3:
        flush_pen = 0.10
    elif bmaxsuit >= 4:
        flush_pen = 0.22
    st_pen = 0.0
    if sd >= 4:
        st_pen = 0.09
    elif sd == 3:
        st_pen = 0.04
    if cat == 8:
        s = 0.5 if (street == 3 and v == bv) else 0.99
    elif cat == 7:
        s = 0.6 if bcat == 7 else 0.98
    elif cat == 6:
        if street == 3 and v == bv:
            s = 0.45
        elif bcat == 3 or bcat == 6:
            s = 0.74 + 0.015 * ((v >> 12) & 15)
        else:
            s = 0.94
    elif cat == 5:
        sc = [0, 0, 0, 0]
        for x in allc:
            sc[x & 3] += 1
        fs = 0
        for k in range(4):
            if sc[k] >= 5:
                fs = k
        hr = [x >> 2 for x in hole if (x & 3) == fs]
        if not hr:
            s = 0.33
        else:
            hi = max(hr)
            higher = 0
            bs = [x >> 2 for x in board if (x & 3) == fs]
            for r in range(hi + 1, 13):
                if r not in bs:
                    higher += 1
            s = (0.97, 0.91, 0.86, 0.81, 0.77, 0.74)[min(higher, 5)]
            if bsc[fs] >= 4 and len(hr) == 1:
                s -= 0.07
            if bpaired:
                s -= 0.08
    elif cat == 4:
        if street == 3 and v == bv:
            s = 0.38
        else:
            s = 0.85
            s -= 0.14 if bmaxsuit == 3 else (0.30 if bmaxsuit >= 4 else 0.0)
            if bpaired:
                s -= 0.07
            if sd >= 4:
                s -= 0.07
    elif cat == 3:
        t = (v >> 16) & 15
        if h1 == h2 == t:
            s = 0.92
        elif br.count(t) >= 3:
            s = 0.30 + (0.08 if h1 >= 11 else 0.0)
        else:
            kick = h2 if h1 == t else h1
            s = 0.74 + 0.011 * kick
        s -= flush_pen + st_pen
    elif cat == 2:
        p1 = (v >> 16) & 15
        p2 = (v >> 12) & 15
        if h1 == h2:
            s = _pair_val(h1, h1, bdist, True) - 0.03
        elif (h1 in (p1, p2)) and (h2 in (p1, p2)) and br.count(h1) == 1 and br.count(h2) == 1:
            if h1 == bdist[0] and len(bdist) > 1 and h2 == bdist[1]:
                s = 0.85
            elif h1 == bdist[0]:
                s = 0.80
            else:
                s = 0.75
            if bpaired:
                s -= 0.06
        elif (h1 in (p1, p2) and br.count(h1) == 1) or (h2 in (p1, p2) and br.count(h2) == 1):
            pr = h1 if (h1 in (p1, p2) and br.count(h1) == 1) else h2
            kick = h2 if pr == h1 else h1
            s = _pair_val(pr, kick, bdist, False) - 0.05
        else:
            s = _hc_val(h1, h2, top, street) + 0.05
        s -= 0.7 * (flush_pen + st_pen)
    elif cat == 1:
        p = (v >> 16) & 15
        if h1 == h2 == p:
            s = _pair_val(p, p, bdist, True)
        elif p == h1 or p == h2:
            kick = h2 if p == h1 else h1
            s = _pair_val(p, kick, bdist, False)
        else:
            s = _hc_val(h1, h2, top, street)
        if street >= 2:
            s -= 0.6 * (flush_pen + st_pen)
        else:
            s -= 0.3 * (flush_pen + st_pen)
        if bpaired and (p == h1 or p == h2):
            s -= 0.03
    else:
        s = _hc_val(h1, h2, top, street)
    outs = 0
    if street < 3 and cat < 4:
        allsc = [0, 0, 0, 0]
        for x in allc:
            allsc[x & 3] += 1
        for k in range(4):
            if allsc[k] == 4 and bsc[k] <= 3 and ((hole[0] & 3) == k or (hole[1] & 3) == k):
                outs += 9
                break
        hmask = bmask | (1 << h1) | (1 << h2)
        so = 0
        for r in range(13):
            if not (hmask >> r & 1):
                if STRAIGHT_HI[hmask | (1 << r)] >= 0 and STRAIGHT_HI[bmask | (1 << r)] < 0:
                    so += 1
        if so >= 2:
            outs += 8 if outs == 0 else 6
        elif so == 1:
            outs += 4 if outs == 0 else 3
        if cat == 0:
            overs = (1 if h1 > top else 0) + (1 if h2 > top else 0)
            outs += 2 * overs
        if bpaired and outs:
            outs -= 1
        if outs > 0:
            if street == 1:
                de = 1.0 - (1.0 - outs / 47.0) * (1.0 - outs / 46.0)
            else:
                de = outs / 46.0
            s = s + (1.0 - s) * de * 0.85
    if s < 0.02:
        s = 0.02
    return s, outs, cat


def _pair_val(p, kick, bdist, pocket):
    if pocket:
        above = 0
        for r in bdist:
            if r > p:
                above += 1
        if above == 0:
            return 0.70 + 0.012 * p
        if above == 1:
            return 0.48 + 0.008 * p
        if above == 2:
            return 0.36
        return 0.28
    idx = bdist.index(p) if p in bdist else len(bdist)
    if idx == 0:
        v = 0.60 + 0.011 * max(0, kick - 4)
        if p >= 11:
            v += 0.02
        return v
    if idx == 1:
        return 0.46 + 0.005 * kick
    return 0.37 + 0.004 * kick


def _hc_val(h1, h2, top, street):
    overs = (1 if h1 > top else 0) + (1 if h2 > top else 0)
    if street == 3:
        return 0.05 + (0.10 if h1 == 12 else (0.05 if h1 == 11 else 0.0)) + 0.02 * overs
    return 0.08 + 0.04 * overs + (0.07 if h1 == 12 else (0.03 if h1 == 11 else 0.0))


# ----------------------------------------------------------------------------- hand parser

def parse_hand(history, n, start, button, blinds, dealt):
    """Replay the action list, splitting it into streets. Returns (records, street, state).
    Each record: (street, seat, act, amount_to, facing, pot_before, nraises_before, allin,
                  limpers_before, my_seats_left)."""
    sb, bb = blinds
    if len(dealt) < 2:
        return [], 0, None
    seq = []
    for k in range(1, n + 1):
        i = (button + k) % n
        if i in dealt:
            seq.append(i)
    if len(dealt) == 2:
        sbs = button if button in dealt else seq[-1]
        bbs = seq[0] if seq[0] != sbs else seq[1]
        pre_order = [sbs, bbs]
        post_order = [bbs, sbs]
    else:
        sbs, bbs = seq[0], seq[1]
        pre_order = seq[2:] + seq[:2]
        post_order = seq
    stack = list(start)
    bet = [0] * n
    folded = [False] * n
    for i in range(n):
        if i not in dealt:
            folded[i] = True
    p = min(sb, stack[sbs])
    bet[sbs] = p
    stack[sbs] -= p
    p = min(bb, stack[bbs])
    bet[bbs] = p
    stack[bbs] -= p
    high = max(bet)
    pot = 0
    street = 0
    need = [i for i in pre_order if stack[i] > 0]
    nraise = 0
    limpers = 0
    recs = []
    for (seat, a) in history:
        try:
            act = a[0]
            amt = int(a[1])
        except Exception:
            continue
        if seat < 0 or seat >= n:
            continue
        facing = high - bet[seat]
        pot_before = pot + sum(bet)
        nr_before = nraise
        lp_before = limpers
        allin = False
        aggr = False
        if act == 'fold':
            folded[seat] = True
        elif act == 'call':
            put = min(facing, stack[seat])
            bet[seat] += put
            stack[seat] -= put
            if street == 0 and nraise == 0:
                limpers += 1
        elif act == 'raise':
            put = min(max(0, amt - bet[seat]), stack[seat])
            bet[seat] += put
            stack[seat] -= put
            if bet[seat] > high:
                high = bet[seat]
                nraise += 1
                aggr = True
                need = [i for i in (pre_order if street == 0 else post_order)
                        if i != seat and not folded[i] and stack[i] > 0]
        if stack[seat] == 0 and act in ('call', 'raise'):
            allin = True
        if seat in need:
            need.remove(seat)
        recs.append((street, seat, act, bet[seat], facing, pot_before, nr_before, allin, lp_before, aggr))
        alive = [i for i in range(n) if not folded[i]]
        if len(alive) <= 1:
            break
        if not need:
            pot += sum(bet)
            bet = [0] * n
            high = 0
            nraise = 0
            street += 1
            actors = [i for i in post_order if not folded[i] and stack[i] > 0]
            need = actors if len(actors) >= 2 else []
            if street > 3:
                break
    state = (stack, bet, folded, pot, pre_order, post_order, sbs, bbs)
    return recs, street, state


# ----------------------------------------------------------------------------- opponent model

class Stat(object):
    """Shrunk binary frequency with forgetting: est = (k + p0*W) / (n + W)."""
    __slots__ = ('k', 'n')

    def __init__(self):
        self.k = 0.0
        self.n = 0.0

    def add(self, x, decay=0.985):
        self.k = self.k * decay + x
        self.n = self.n * decay + 1.0

    def est(self, p0, w):
        return (self.k + p0 * w) / (self.n + w)


class Ratio(object):
    """Observed count of an action over the count a prior player would make: (k+A)/(E+A)."""
    __slots__ = ('k', 'e', 'n')

    def __init__(self):
        self.k = 0.0
        self.e = 0.0
        self.n = 0.0

    def add(self, x, p0, decay=0.985):
        self.k = self.k * decay + x
        self.e = self.e * decay + p0
        self.n = self.n * decay + 1.0

    def ratio(self, a):
        return (self.k + a) / (self.e + a)


class Resid(object):
    """Shrunk mean of (outcome - prediction)."""
    __slots__ = ('s', 'n')

    def __init__(self):
        self.s = 0.0
        self.n = 0.0

    def add(self, r):
        self.s = self.s * 0.97 + r
        self.n = self.n * 0.97 + 1.0

    def mean(self, w):
        return self.s / (self.n + w)


class Opp(object):
    def __init__(self):
        self.open = Ratio()        # open-raise when folded to
        self.cont = Ratio()        # continue (call/raise) when facing a single open
        self.threeb = Ratio()      # 3-bet when facing a single open
        self.f3b = Stat()          # fold to a 3-bet after opening
        self.shove = Stat()        # preflop all-in per preflop decision
        self.shove_r = Ratio()     # shoves vs prior at short depths
        self.callsh = Ratio()      # call when facing a preflop all-in
        self.fbet = Stat()         # fold when facing a postflop bet
        self.agg = Stat()          # bet when checked to, postflop
        self.xr = Stat()           # raise when facing a postflop bet
        self.bc = [Resid(), Resid()]  # hero's bluff-catch result vs prediction, by size small/big
        self.vcall = Resid()       # hero's value-bet result when this seat calls to showdown
        self.hands = 0
        self.vpip = 0
        self.pfr = 0


# ----------------------------------------------------------------------------- the bot

class Bot(Agent):
    COUNTERS = True      # False: the identical bot with every counter switched off
    DISABLED = ()        # names of single counters to switch off (ablation only)

    def __init__(self):
        self.rng = random.Random(0)
        self.seat = 0
        self.n = 2
        self.fired = {}
        self._reset_table(None, 0, 2)

    # -- table / hand bookkeeping
    def _reset_table(self, rules, seat, n_players):
        self.seat = seat
        self.n = n_players
        st = 2000
        if isinstance(rules, dict):
            try:
                st = int(rules.get('starting_stack', 2000))
            except Exception:
                st = 2000
        self.start = [st] * n_players
        self.opps = [Opp() for _ in range(n_players)]
        self.cur_hand = -1
        self.hand_start = None
        self.hand_button = None
        self.hand_blinds = (10, 20)
        self.hand_dealt = None
        self.pending_bc = []
        self.pending_vb = []
        self.last_board = ()
        self.last_hole = None

    def new_table(self, rules, seat, n_players):
        try:
            n_players = int(n_players)
        except Exception:
            n_players = 8
        if n_players < 2:
            n_players = 2
        self._reset_table(rules, seat if isinstance(seat, int) else 0, n_players)
        self.rng = random.Random(1000003 * (self.seat + 1) + 7919)

    def _fire(self, name):
        self.fired[name] = self.fired.get(name, 0) + 1

    def _on(self, group):
        return self.COUNTERS and group not in self.DISABLED

    def _begin_hand(self, obs):
        self.cur_hand = obs.hand_no
        n = len(obs.stacks)
        if n != self.n:
            self.n = n
            self.opps = [Opp() for _ in range(n)]
            self.start = [0] * n
        st = [0] * n
        for i in range(n):
            st[i] = obs.stacks[i] + (obs.bets[i] if obs.street == 0 else 0)
        if obs.street != 0:
            st = list(self.start)
        self.hand_start = st
        self.hand_button = obs.button
        self.hand_blinds = tuple(obs.blinds)
        folded = set()
        for (s, a) in obs.history:
            if a and a[0] == 'fold':
                folded.add(s)
        self.hand_dealt = set(i for i in range(n) if obs.in_hand[i] or i in folded)
        self.pending_bc = []
        self.pending_vb = []

    def act(self, obs):
        try:
            return self._act(obs)
        except Exception:
            if 'check' in obs.legal:
                return ('check', 0)
            if 'call' in obs.legal and obs.to_call <= max(1, obs.blinds[1]):
                return ('call', 0)
            return ('fold', 0) if 'fold' in obs.legal else ('call', 0)

    def _act(self, obs):
        if obs.hand_no != self.cur_hand:
            self._begin_hand(obs)
        self.seat = obs.seat
        self.last_board = tuple(obs.board)
        self.last_hole = tuple(obs.hole)
        u = self.rng.random()
        u2 = self.rng.random()
        n = len(obs.stacks)
        dealt = self.hand_dealt
        if dealt is None or len(dealt) < 2:
            dealt = set(i for i in range(n) if obs.in_hand[i])
        recs, street, state = parse_hand(obs.history, n, self.hand_start, self.hand_button,
                                         self.hand_blinds, dealt)
        ok = state is not None and street == obs.street
        if obs.street == 0:
            a = self._preflop(obs, recs if ok else None, state if ok else None, u, u2)
        else:
            a = self._postflop(obs, recs if ok else None, state if ok else None, u, u2)
        return self._legalize(obs, a)

    def _legalize(self, obs, a):
        kind, amt = a
        legal = obs.legal
        if kind == 'raise':
            if 'raise' not in legal:
                kind = 'call' if 'call' in legal else 'check'
            else:
                amt = int(amt)
                if amt >= obs.max_raise * 0.85:
                    amt = obs.max_raise
                if amt < obs.min_raise:
                    amt = obs.min_raise
                if amt > obs.max_raise:
                    amt = obs.max_raise
                return ('raise', int(amt))
        if kind == 'call' and 'call' not in legal:
            kind = 'check'
        if kind == 'check' and 'check' not in legal:
            kind = 'fold'
        if kind == 'fold' and 'check' in legal:
            kind = 'check'
        if kind not in legal:
            for k in ('check', 'call', 'fold'):
                if k in legal:
                    kind = k
                    break
        return (kind, 0)

    # -- counters: each returns the base value when COUNTERS is off or the read is inside the dead zone
    def _open_width_of(self, seat, base):
        if not self._on('opener'):
            return base
        r = self.opps[seat].open.ratio(3.0)
        d = soft(r - 1.0, 0.25)
        if d != 0.0:
            self._fire('opener_width')
        return min(1.0, max(0.05, base * (1.0 + d)))

    def _threeb_width_of(self, seat, base):
        if not self._on('light3'):
            return base
        r = self.opps[seat].threeb.ratio(1.5)
        d = soft(r - 1.0, 0.3)
        if d != 0.0:
            self._fire('light_3bet')
        return min(0.9, max(0.02, base * (1.0 + d)))

    def _fold_to_3bet(self, seat):
        base = 0.55
        if not self._on('f3b'):
            return base
        e = self.opps[seat].f3b.est(base, 6.0)
        d = soft(e - base, 0.08)
        if d != 0.0:
            self._fire('fold_to_3bet')
        return min(0.95, max(0.05, base + d))

    def _cont_vs_open(self, seat, base):
        """Probability this seat continues vs an open (prior base)."""
        if not self._on('steal'):
            return base
        r = self.opps[seat].cont.ratio(2.5)
        d = soft(r - 1.0, 0.2)
        return min(0.95, max(0.02, base * (1.0 + d)))

    def _shove_width_of(self, seat, x_bb, reshove):
        base = shove_prior_width(x_bb, reshove)
        if not self._on('shover'):
            return base
        o = self.opps[seat]
        w = base
        f = o.shove.k / (o.shove.n + 8.0)
        if f > w + 0.05:
            w = f
            self._fire('loose_shover')
        elif x_bb <= 20 and o.shove_r.e >= 2.0:
            r = o.shove_r.ratio(1.0)
            if r < 0.6:
                w = base * max(0.5, r + 0.4)
                self._fire('tight_shover')
        return min(0.95, max(0.02, w))

    def _call_shove_of(self, seat, x_bb, posted):
        base = call_shove_prior(x_bb, posted)
        if not self._on('callshove'):
            return base
        r = self.opps[seat].callsh.ratio(1.5)
        d = soft(r - 1.0, 0.3)
        if d != 0.0:
            self._fire('call_shove')
        return min(0.95, max(0.02, base * (1.0 + d)))

    def _fold_to_bet(self, seat):
        base = 0.45
        if not self._on('fbet'):
            return base
        e = self.opps[seat].fbet.est(base, 5.0)
        d = soft(e - base, 0.06)
        if d != 0.0:
            self._fire('fold_to_bet_hi' if d > 0 else 'station')
        return min(0.95, max(0.03, base + d))

    def _xr_of(self, seat):
        base = 0.12
        if not self._on('xr'):
            return base
        e = self.opps[seat].xr.est(base, 8.0)
        d = soft(e - base, 0.05)
        if d != 0.0:
            self._fire('raises_light' if d > 0 else 'raises_strong')
        return min(0.8, max(0.0, base + d))

    def _agg_of(self, seat):
        base = 0.35
        if not self._on('agg'):
            return base
        e = self.opps[seat].agg.est(base, 6.0)
        d = soft(e - base, 0.07)
        if d != 0.0:
            self._fire('aggressive' if d > 0 else 'passive')
        return min(0.95, max(0.03, base + d))

    def _bc_adj(self, seat, big):
        if not self._on('size'):
            return 0.0
        m = self.opps[seat].bc[1 if big else 0].mean(4.0)
        d = soft(m, 0.06)
        if d != 0.0:
            self._fire('size_tell_big' if big else 'size_tell_small')
        return max(-0.15, min(0.15, d))

    def _vcall_adj(self, seat):
        if not self._on('vcall'):
            return 0.0
        m = self.opps[seat].vcall.mean(4.0)
        d = soft(m, 0.08)
        if d != 0.0:
            self._fire('thin_value' if d > 0 else 'value_tighten')
        return max(-0.1, min(0.1, d))

    # -- preflop
    def _positions(self, obs, state):
        n = len(obs.stacks)
        if state is not None:
            pre_order = state[4]
            sbs, bbs = state[6], state[7]
        else:
            seq = [(obs.button + k) % n for k in range(1, n + 1) if obs.in_hand[(obs.button + k) % n]]
            if len(seq) < 2:
                seq = [obs.seat, (obs.seat + 1) % n]
            if len(seq) == 2:
                sbs = obs.button if obs.button in seq else seq[1]
                bbs = seq[0] if seq[0] != sbs else seq[1]
                pre_order = [sbs, bbs]
            else:
                sbs, bbs = seq[0], seq[1]
                pre_order = seq[2:] + seq[:2]
        return pre_order, sbs, bbs

    def _preflop(self, obs, recs, state, u, u2):
        me = obs.seat
        n = len(obs.stacks)
        sb, bb = obs.blinds
        bb = max(1, bb)
        r1, r2 = obs.hole[0] >> 2, obs.hole[1] >> 2
        suited = (obs.hole[0] & 3) == (obs.hole[1] & 3)
        h = hid_of(r1, r2, suited)
        pct = PCT[h]
        pre_order, sbs, bbs = self._positions(obs, state)
        ndealt = len(pre_order)
        my_total = obs.stacks[me] + obs.bets[me]
        opp_alive = [i for i in range(n) if i != me and obs.in_hand[i]]
        if not opp_alive:
            return ('check', 0) if 'check' in obs.legal else ('call', 0)
        others_total = [obs.stacks[i] + obs.bets[i] for i in opp_alive]
        eff = min(my_total, max(others_total))
        eff_bb = eff / float(bb)
        pot = obs.pot + sum(obs.bets)
        tc = obs.to_call
        # who has acted / is still to act
        raisers = []
        limpers = 0
        acted = set()
        shove_seats = set()
        if recs is not None:
            for rec in recs:
                if rec[0] != 0:
                    continue
                acted.add(rec[1])
                if rec[9]:
                    raisers.append(rec[1])
                    if rec[7]:
                        shove_seats.add(rec[1])
                elif rec[2] == 'call' and rec[6] == 0:
                    limpers += 1
        else:
            hb = max(obs.bets)
            if hb > bb:
                raisers = [obs.bets.index(hb)]
        try:
            my_idx = pre_order.index(me)
        except ValueError:
            my_idx = 0
        behind = [s for s in pre_order[my_idx + 1:] if obs.in_hand[s] and obs.stacks[s] > 0]
        is_bb = me == bbs
        hu = ndealt == 2
        in_pos_post = (me == sbs) if hu else (me == pre_order[-3] if ndealt >= 3 else False)
        nr = len(raisers)
        alive = sum(1 for st in obs.stacks if st > 0) + sum(1 for i in range(n) if obs.stacks[i] == 0 and obs.in_hand[i])
        icm = 0.0 if alive <= 2 else (0.02 if alive == 3 else 0.045)

        # ---- unopened
        if nr == 0:
            if tc == 0:
                # big blind option after limps
                if pct <= 0.12 + (0.10 if limpers <= 1 else 0.0) and 'raise' in obs.legal:
                    if eff_bb <= 15:
                        return ('raise', obs.max_raise)
                    return ('raise', obs.bets[me] + int(bb * (3 + limpers)))
                return ('check', 0)
            callers = behind[:]
            if eff_bb <= 13 or (limpers and eff_bb <= 16):
                ev = self._shove_ev(obs, h, callers, bbs, limpers > 0)
                if ev > 0.0:
                    return ('raise', obs.max_raise)
                if limpers == 0 and me == sbs and hu and pct <= 0.9 and eff_bb > 8:
                    return ('call', 0)
                return ('fold', 0)
            W = open_width(len(behind), ndealt)
            if limpers:
                W *= 0.55
            # steal adjustment: probability everyone behind folds, learned vs prior
            if self._on('steal') and behind:
                pf_base = 1.0
                pf_now = 1.0
                for s in behind:
                    c0 = self._cont_prior(s, me, bbs, sbs, hu, len(behind))
                    pf_base *= 1.0 - c0
                    pf_now *= 1.0 - self._cont_vs_open(s, c0)
                d = pf_now - pf_base
                if d != 0.0:
                    if d > 0.0:
                        self._fire('steal')
                        W = W * min(1.8, 1.0 + 1.8 * d)
            if pct <= W:
                size = 2.2 if (len(behind) <= 1 and not hu) or ndealt <= 3 else 2.4
                if hu:
                    size = 2.3
                if me == sbs and not hu:
                    size = 3.0
                to = int(bb * (size + limpers))
                if to >= 0.33 * my_total:
                    return ('raise', obs.max_raise)
                return ('raise', to)
            if limpers and tc <= bb and pct <= 0.40 and (len(behind) <= 2) and eff_bb >= 25:
                return ('call', 0)
            return ('fold', 0)

        # ---- facing a raise
        lr = raisers[-1]
        opener = raisers[0]
        lr_total = obs.stacks[lr] + obs.bets[lr]
        lr_allin = obs.stacks[lr] == 0 or lr in shove_seats
        raise_bb = obs.bets[lr] / float(bb)
        callers_after = 0
        if recs is not None:
            seen_r = False
            for rec in recs:
                if rec[0] == 0 and rec[1] == lr and rec[2] == 'raise':
                    seen_r = True
                    callers_after = 0
                elif seen_r and rec[0] == 0 and rec[2] == 'call':
                    callers_after += 1
        i_opened = me in raisers
        need = tc / float(pot + tc) if tc > 0 else 0.0
        big_commit = tc >= 0.4 * (obs.stacks[me] + 0.0) or lr_allin

        if nr == 1:
            x_bb = min(lr_total, my_total) / float(bb)
            if lr_allin or raise_bb >= 0.5 * lr_total / float(bb):
                w = self._shove_width_of(lr, x_bb, False)
            else:
                op_behind = self._behind_of(lr, pre_order, obs)
                base_w = open_width(op_behind, ndealt)
                if raise_bb > 4.0:
                    base_w *= 0.75
                w = self._open_width_of(lr, base_w)
            eq = eq_vs(h, w)
            if callers_after:
                eq = eq ** (1.0 + 0.45 * callers_after)
            if big_commit:
                if eq >= need + icm:
                    return ('call', 0)
                # reshove if it is cheaper to shove and we have equity vs the raiser
                return ('fold', 0)
            # short: shove-or-fold over the raise
            if eff_bb <= 22:
                f3 = self._fold_to_3bet(lr)
                ev = self._reshove_ev(obs, h, lr, w, f3, behind)
                if ev > 0.0 and (pct <= 0.5 * w + 0.02 or ev > 0.5 * bb):
                    return ('raise', obs.max_raise)
                if eq * (0.92 if in_pos_post else 0.8) >= need and tc <= 0.12 * obs.stacks[me]:
                    return ('call', 0)
                return ('fold', 0)
            value3 = pct <= max(0.025, min(0.11, 0.33 * w))
            bluff3 = False
            if not value3 and callers_after == 0:
                light_cand = (suited and (r1 == 12 or r2 == 12)) or (suited and abs(r1 - r2) <= 2 and min(r1, r2) >= 3)
                if light_cand or (pct <= 2.0 * max(0.025, min(0.11, 0.33 * w))):
                    f3 = self._fold_to_3bet(lr)
                    p3 = 0.30 * (f3 / 0.55) ** 2
                    if f3 < 0.45:
                        p3 *= 0.5
                    bluff3 = u < min(0.85, p3)
            if value3 or bluff3:
                mult = 3.0 if in_pos_post else 3.6
                to = int(obs.bets[lr] * mult + callers_after * obs.bets[lr])
                if to >= 0.35 * my_total:
                    if value3 or eq >= 0.45:
                        return ('raise', obs.max_raise)
                else:
                    return ('raise', to)
            realize = 0.92 if in_pos_post else 0.78
            if is_bb and hu:
                realize = 0.82
            imp = 0.0
            if r1 == r2 and eff_bb >= 40 and tc <= eff / 18.0:
                imp = 0.06
            if eq * realize + imp >= need + 0.01 and tc <= 0.25 * obs.stacks[me]:
                return ('call', 0)
            return ('fold', 0)

        # ---- facing a 3-bet or more
        x_bb = min(lr_total, my_total) / float(bb)
        if lr_allin or raise_bb * bb >= 0.5 * lr_total:
            w = self._shove_width_of(lr, x_bb, True)
            if nr >= 3:
                w *= 0.6
        else:
            base3 = 0.09 if hu else 0.06
            w = self._threeb_width_of(lr, base3)
            if nr >= 3:
                w *= 0.45
        eq = eq_vs(h, w)
        if callers_after:
            eq = eq ** (1.0 + 0.45 * callers_after)
        if not i_opened and nr >= 2:
            w = w * 0.7
            eq = eq_vs(h, w)
        if big_commit:
            return ('call', 0) if eq >= need + icm else ('fold', 0)
        value4 = pct <= max(0.02, 0.35 * w)
        if value4:
            if eff_bb <= 45 or nr >= 3:
                return ('raise', obs.max_raise)
            return ('raise', int(obs.bets[lr] * 2.3))
        realize = 0.9 if in_pos_post else 0.75
        if i_opened and eq * realize >= need + 0.02 and tc <= 0.2 * obs.stacks[me]:
            return ('call', 0)
        return ('fold', 0)

    def _behind_of(self, seat, pre_order, obs):
        try:
            i = pre_order.index(seat)
        except ValueError:
            return 3
        return len(pre_order) - 1 - i

    def _cont_prior(self, s, me, bbs, sbs, hu, nbehind):
        if hu:
            return 0.55
        if s == bbs:
            return 0.45 if nbehind <= 2 else 0.30
        if s == sbs:
            return 0.25
        return 0.12

    def _shove_ev(self, obs, h, callers, bbs, limped):
        me = obs.seat
        bb = max(1, obs.blinds[1])
        my_total = obs.stacks[me] + obs.bets[me]
        pot = obs.pot + sum(obs.bets)
        pf = 1.0
        best = None
        for s in callers:
            v_total = obs.stacks[s] + obs.bets[s]
            x = min(my_total, v_total)
            c = self._call_shove_of(s, x / float(bb), s == bbs)
            if limped:
                c *= 0.8
            pf *= 1.0 - c
            if best is None or c > best[0]:
                best = (c, s, x)
        if best is None:
            return pot
        c, s, x = best
        eq = eq_vs(h, c)
        pot_sd = obs.pot + sum(obs.bets[i] for i in range(len(obs.bets)) if i != s and i != me) + 2 * x
        gain_called = eq * pot_sd - (x - obs.bets[me])
        ev = pf * pot + (1.0 - pf) * gain_called
        alive = sum(1 for st in obs.stacks if st > 0)
        if alive > 2:
            ev -= (0.03 if alive == 3 else 0.06) * x * (1.0 - pf)
        return ev

    def _reshove_ev(self, obs, h, lr, w, f3, others):
        me = obs.seat
        my_total = obs.stacks[me] + obs.bets[me]
        lr_total = obs.stacks[lr] + obs.bets[lr]
        x = min(my_total, lr_total)
        pot = obs.pot + sum(obs.bets)
        fold_p = f3 * 0.9
        for s in others:
            if s != lr:
                fold_p *= 0.93
        cw = max(0.02, w * (1.0 - f3))
        eq = eq_vs(h, cw)
        pot_sd = obs.pot + sum(obs.bets[i] for i in range(len(obs.bets)) if i != lr and i != me) + 2 * x
        gain_called = eq * pot_sd - (x - obs.bets[me])
        ev = fold_p * pot + (1.0 - fold_p) * gain_called
        alive = sum(1 for st in obs.stacks if st > 0)
        if alive > 2:
            ev -= (0.03 if alive == 3 else 0.06) * x * (1.0 - fold_p)
        return ev

    # -- postflop
    def _postflop(self, obs, recs, state, u, u2):
        me = obs.seat
        n = len(obs.stacks)
        street = obs.street
        bb = max(1, obs.blinds[1])
        s, outs, cat = post_strength(obs.hole, obs.board, street)
        opps = [i for i in range(n) if i != me and obs.in_hand[i]]
        if not opps:
            return ('check', 0)
        n_opp = len(opps)
        live_opps = [i for i in opps if obs.stacks[i] > 0]
        pot = obs.pot + sum(obs.bets)
        tc = obs.to_call
        my_stack = obs.stacks[me]
        eff = min(my_stack + obs.bets[me], max(obs.stacks[i] + obs.bets[i] for i in opps))
        se = s ** (1.0 + 0.55 * (n_opp - 1)) if n_opp > 1 else s
        # preflop aggressor, aggression this street, who checked
        pfa = None
        last_aggr = None
        n_aggr = 0
        i_bet_prev = False
        if recs is not None:
            for rec in recs:
                if rec[9] and rec[0] == 0:
                    pfa = rec[1]
                if rec[0] == street and rec[9]:
                    last_aggr = rec[1]
                    n_aggr += 1
                if rec[0] == street - 1 and rec[9] and rec[1] == me:
                    i_bet_prev = True
        if last_aggr is None and tc > 0:
            hb = max(obs.bets)
            last_aggr = obs.bets.index(hb)
            n_aggr = 1
        post_order = state[5] if state is not None else None
        last_to_act = False
        if post_order is not None:
            act_left = [i for i in post_order if obs.in_hand[i] and obs.stacks[i] > 0]
            last_to_act = bool(act_left) and act_left[-1] == me
        spr = eff / float(max(1, pot))

        if tc == 0:
            vt = (0.0, 0.62, 0.64, 0.64)[street] + 0.06 * (n_opp - 1)
            station = 0.0
            if n_opp == 1 and live_opps:
                v = opps[0]
                fb = self._fold_to_bet(v)
                if fb < 0.45:
                    station = (0.45 - fb)
                vt -= 0.6 * station
                vt -= self._vcall_adj(v)
            if se >= vt and 'raise' in obs.legal:
                if se >= 0.93 and street == 1 and n_opp == 1 and u < 0.2 and spr > 3:
                    return ('check', 0)
                # trap: out of position against a seat that bets whenever checked to
                if n_opp == 1 and not last_to_act and street < 3 and live_opps and self._on('agg'):
                    ag = self._agg_of(opps[0])
                    if ag >= 0.55 and u2 < min(0.8, 2.0 * (ag - 0.45)):
                        self._fire('trap')
                        return ('check', 0)
                self.pending_vb.append((street, se))
                frac = 0.66 if street < 3 else 0.72
                if se >= 0.85:
                    frac += 0.1
                frac += 0.8 * station
                amt = int(pot * frac)
                if amt >= 0.6 * my_stack or spr <= 1.3:
                    return ('raise', obs.max_raise)
                return ('raise', obs.bets[me] + max(bb, amt))
            # bluffs / semi-bluffs
            p = 0.0
            if n_opp <= 2:
                if street == 1 and pfa == me:
                    p = 0.62 if n_opp == 1 else 0.30
                elif street >= 2 and i_bet_prev and n_opp == 1:
                    p = 0.36 if street == 2 else 0.24
                elif last_to_act and n_opp == 1:
                    p = 0.30 if street < 3 else 0.22
                elif n_opp == 1:
                    p = 0.12
                if outs >= 8 and street < 3:
                    p = max(p, 0.6)
                elif outs >= 4 and street < 3:
                    p = max(p, p + 0.1)
                if street == 3 and s >= 0.3:
                    p *= 0.3
                elif s >= 0.42 and outs < 8:
                    p *= 0.5
                if p > 0.0 and self._on('fbet'):
                    m = 1.0
                    for v in opps:
                        fb = self._fold_to_bet(v)
                        m *= (fb / (1.0 - fb)) / (0.45 / 0.55)
                    if m < 1.0:
                        m = m ** 1.5
                    p = p * m
                if n_opp == 2:
                    p *= 0.6
            if p > 0.0 and u < min(0.95, p) and 'raise' in obs.legal:
                frac = 0.5 if (street == 1) else 0.62
                amt = int(pot * frac)
                if amt >= 0.6 * my_stack:
                    if outs >= 8 or u2 < 0.3:
                        return ('raise', obs.max_raise)
                    return ('check', 0)
                return ('raise', obs.bets[me] + max(bb, amt))
            return ('check', 0)

        # facing a bet
        need = tc / float(pot + tc)
        bet_before = max(1, pot - tc)
        f = tc / float(bet_before)
        facing_raise = obs.bets[me] > 0 or n_aggr >= 2
        v = last_aggr if last_aggr is not None else opps[0]
        if v == me:
            v = opps[0]
        rpen = 0.0
        if facing_raise:
            rpen = 0.10
            if self.COUNTERS:
                rpen *= max(0.35, min(1.6, 1.0 - 3.0 * (self._xr_of(v) - 0.12)))
        pen = 0.04 + 0.10 * min(f, 1.5) + (0.04 if street == 3 else 0.0) + rpen
        big = f >= 0.6
        if self.COUNTERS:
            ag = self._agg_of(v)
            mult = 1.0 - 1.6 * (ag - 0.35)
            pen *= max(0.45, min(1.5, mult))
            pen -= self._bc_adj(v, big)
        if pen < 0.0:
            pen = 0.0
        e = se - pen
        margin = 0.02
        if outs >= 8 and street < 3 and tc < 0.3 * my_stack:
            margin -= 0.03
        allin_call = tc >= my_stack
        if allin_call:
            alive = sum(1 for st in obs.stacks if st > 0) + 1
            if e >= need + (0.0 if alive <= 2 else (0.02 if alive == 3 else 0.045)):
                self._note_call(v, e, big, True)
                return ('call', 0)
            return ('fold', 0)
        # raise for value
        if se >= 0.86 and 'raise' in obs.legal and n_aggr <= 2:
            self.pending_vb.append((street, se))
            if spr <= 2.5 or tc >= 0.35 * my_stack:
                return ('raise', obs.max_raise)
            to = int(obs.bets[v] * 2.8 + (pot - tc) * 0.3)
            return ('raise', to)
        if e >= need + margin:
            if outs >= 8 and street == 1 and n_opp == 1 and not facing_raise and u < 0.18 and 'raise' in obs.legal:
                to = int(obs.bets[v] * 3.0)
                if to >= 0.5 * (my_stack + obs.bets[me]):
                    return ('raise', obs.max_raise)
                return ('raise', to)
            self._note_call(v, e, big, street == 3)
            return ('call', 0)
        return ('fold', 0)

    def _note_call(self, v, e, big, final):
        if final:
            self.pending_bc.append((v, min(0.95, max(0.05, e)), big))

    # -- learning from the finished hand
    def hand_end(self, result):
        try:
            self._hand_end(result)
        except Exception:
            pass

    def _hand_end(self, result):
        if not isinstance(result, dict):
            return
        deltas = result.get('deltas')
        hist = result.get('history') or []
        n = self.n
        if deltas is not None and len(deltas) == n:
            start = self.hand_start if (self.hand_start is not None and result.get('hand_no') == self.cur_hand) else self.start
            self.start = [max(0, start[i] + deltas[i]) for i in range(n)]
        if result.get('hand_no') != self.cur_hand or self.hand_start is None:
            return
        dealt = self.hand_dealt
        if not dealt or len(dealt) < 2:
            return
        recs, street, state = parse_hand(hist, n, self.hand_start, self.hand_button, self.hand_blinds, dealt)
        if state is None:
            return
        me = self.seat
        bb = max(1, self.hand_blinds[1])
        pre_order = state[4]
        sbs, bbs = state[6], state[7]
        hu = len(pre_order) == 2
        first_pf = {}
        opener = None
        threebettor = None
        for rec in recs:
            st, seat, act, to, facing, pot_b, nr, allin, lp, aggr = rec
            o = self.opps[seat]
            if st == 0:
                if seat not in first_pf:
                    first_pf[seat] = rec
                    if seat != me:
                        o.hands += 1
                        if act in ('call', 'raise') and not (seat == bbs and facing == 0):
                            o.vpip += 1
                        if act == 'raise':
                            o.pfr += 1
                        depth = self.hand_start[seat] / float(bb)
                        is_shove = act == 'raise' and allin
                        o.shove.add(1.0 if is_shove else 0.0)
                        if depth <= 20 and nr == 0:
                            o.shove_r.add(1.0 if is_shove else 0.0, shove_prior_width(depth, False))
                        if nr == 0 and lp == 0 and facing > 0:
                            idx = pre_order.index(seat) if seat in pre_order else 0
                            o.open.add(1.0 if act == 'raise' else 0.0, open_width(len(pre_order) - 1 - idx, len(pre_order)))
                        elif nr == 1 and opener is not None:
                            nb = len(pre_order) - 1 - (pre_order.index(opener) if opener in pre_order else 0)
                            c0 = self._cont_prior(seat, opener, bbs, sbs, hu, nb)
                            o.cont.add(1.0 if act != 'fold' else 0.0, c0)
                            o.threeb.add(1.0 if act == 'raise' else 0.0, 0.09 if hu else 0.06)
                if aggr and nr == 0:
                    opener = seat
                elif aggr and nr == 1:
                    threebettor = seat
                if seat != me and facing > 0 and rec is not first_pf.get(seat):
                    if seat == opener and nr == 2 and threebettor is not None and threebettor != seat:
                        o.f3b.add(1.0 if act == 'fold' else 0.0)
            else:
                if seat == me:
                    continue
                if facing > 0:
                    o.fbet.add(1.0 if act == 'fold' else 0.0)
                    o.xr.add(1.0 if aggr else 0.0)
                else:
                    o.agg.add(1.0 if act == 'raise' else 0.0)
        # calls vs preflop shoves
        self._learn_callshove(recs, bb, bbs)
        # showdown reads: did the hand reach showdown with me in it?
        folded = state[2]
        alive = [i for i in range(n) if not folded[i]]
        if deltas is None or me not in alive or len(alive) < 2:
            return
        won = 1.0 if deltas[me] > 0 else 0.0
        for (v, e, big) in self.pending_bc[-1:]:
            if v in alive:
                self.opps[v].bc[1 if big else 0].add(won - e)
        # value bets that got called down
        last_hero_bet_street = -1
        for rec in recs:
            if rec[1] == me and rec[9] and rec[0] >= 1:
                last_hero_bet_street = rec[0]
        vb = [x for x in self.pending_vb if x[0] == last_hero_bet_street]
        if last_hero_bet_street == 3 and vb:
            for rec in recs:
                if rec[0] == last_hero_bet_street and rec[1] != me and rec[2] == 'call' and rec[1] in alive:
                    self.opps[rec[1]].vcall.add(won - 0.62)

    def _learn_callshove(self, recs, bb, bbs):
        shove_to = None
        shover = None
        for rec in recs:
            st, seat, act, to, facing, pot_b, nr, allin, lp, aggr = rec
            if st != 0:
                break
            if shove_to is not None and seat != shover and seat != self.seat and facing > 0:
                self.opps[seat].callsh.add(1.0 if act == 'call' or act == 'raise' else 0.0,
                                           call_shove_prior(max(1.0, shove_to / float(bb)), seat == bbs))
            if aggr and allin and shove_to is None:
                shove_to = to
                shover = seat
