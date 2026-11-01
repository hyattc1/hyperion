"""rival_bot: ICM-aware push/fold bot (stdlib only)."""
import random, time
try:
    from kit import Agent
except Exception:
    class Agent(object):
        pass

LEVELS = [3, 5, 8, 12, 16, 20, 25, 33, 50, 100]
PCT = [43.7, 99.5, 98.6, 96.8, 97.7, 95.9, 92.0, 85.1, 76.6, 67.9, 59.7, 48.0, 30.8, 94.4, 32.4, 95.0, 93.8, 92.9, 90.8, 88.1, 81.7, 74.5, 65.5, 54.0, 43.0, 27.8, 91.4, 85.7, 20.1, 89.0, 89.9, 86.6, 83.9, 79.0, 70.3, 63.0, 51.9, 40.3, 25.9, 87.2, 83.3, 78.4, 12.4, 82.7, 80.8, 77.8, 73.3, 69.1, 58.8, 49.2, 38.2, 23.2, 87.5, 84.5, 77.2, 72.7, 7.2, 75.7, 71.8, 67.0, 61.8, 54.9, 45.2, 34.8, 22.3, 86.0, 80.2, 75.1, 70.9, 66.1, 3.7, 64.6, 60.9, 57.3, 50.1, 42.1, 33.0, 18.6, 79.9, 79.6, 72.4, 68.5, 62.4, 55.5, 2.9, 56.4, 51.0, 46.2, 36.3, 26.8, 16.4, 73.9, 71.2, 69.7, 64.0, 58.2, 52.8, 44.6, 2.5, 41.2, 37.3, 29.6, 21.1, 13.4, 66.4, 63.7, 60.3, 57.9, 53.1, 46.8, 39.4, 33.9, 2.0, 31.7, 24.4, 15.2, 9.4, 55.8, 53.4, 52.5, 48.6, 47.1, 39.7, 35.4, 29.0, 20.5, 1.6, 19.5, 11.8, 7.8, 47.4, 44.3, 44.0, 39.1, 35.7, 33.6, 28.7, 23.8, 17.0, 14.0, 1.1, 10.6, 6.2, 38.8, 34.2, 30.2, 28.4, 25.3, 21.7, 17.9, 14.6, 10.0, 8.7, 6.8, 0.7, 4.7, 25.0, 17.3, 17.6, 14.3, 15.8, 12.8, 11.2, 8.4, 5.6, 5.3, 4.1, 3.3, 0.2]
EQT = [
[20, 29, 36, 40, 42, 44, 44, 46, 48, 51],
[15, 21, 25, 28, 29, 30, 30, 30, 31, 32],
[13, 19, 24, 26, 27, 28, 29, 29, 30, 33],
[14, 19, 25, 29, 29, 30, 30, 30, 31, 34],
[13, 17, 22, 25, 27, 28, 29, 29, 30, 34],
[12, 17, 23, 25, 27, 27, 28, 29, 29, 34],
[12, 19, 23, 25, 27, 28, 28, 29, 30, 37],
[14, 20, 23, 24, 26, 27, 28, 29, 30, 39],
[16, 22, 24, 25, 27, 28, 29, 30, 31, 42],
[16, 22, 24, 26, 28, 28, 29, 30, 32, 44],
[18, 22, 25, 27, 28, 28, 30, 31, 35, 47],
[24, 25, 27, 28, 30, 32, 33, 34, 40, 50],
[21, 22, 25, 30, 34, 36, 39, 42, 48, 55],
[17, 24, 28, 31, 32, 33, 33, 33, 34, 36],
[17, 26, 35, 40, 42, 44, 45, 48, 50, 55],
[16, 21, 25, 28, 29, 29, 30, 31, 32, 35],
[17, 22, 25, 29, 29, 30, 31, 32, 33, 36],
[14, 19, 24, 27, 29, 29, 30, 31, 32, 36],
[12, 19, 24, 26, 27, 28, 29, 30, 31, 37],
[13, 19, 24, 26, 28, 27, 28, 29, 30, 38],
[14, 20, 25, 27, 27, 28, 29, 29, 31, 40],
[16, 23, 27, 27, 27, 28, 29, 30, 31, 42],
[17, 23, 25, 27, 28, 29, 30, 31, 33, 46],
[19, 24, 26, 28, 29, 29, 30, 31, 35, 48],
[23, 24, 27, 28, 29, 31, 33, 35, 41, 52],
[28, 29, 30, 36, 38, 39, 41, 44, 50, 56],
[20, 25, 28, 30, 31, 33, 33, 34, 35, 37],
[22, 26, 30, 32, 33, 34, 34, 35, 36, 39],
[18, 28, 36, 42, 43, 45, 47, 50, 53, 58],
[16, 22, 25, 29, 30, 32, 32, 33, 34, 38],
[16, 21, 25, 28, 30, 31, 31, 32, 33, 38],
[17, 21, 25, 28, 29, 30, 30, 31, 32, 38],
[16, 21, 25, 28, 29, 30, 31, 31, 32, 40],
[14, 21, 25, 28, 29, 30, 30, 31, 32, 41],
[15, 21, 24, 26, 27, 28, 29, 31, 32, 43],
[17, 23, 24, 28, 29, 29, 31, 31, 34, 46],
[22, 25, 26, 29, 29, 30, 31, 33, 36, 49],
[22, 25, 28, 29, 30, 32, 34, 36, 42, 52],
[29, 29, 30, 35, 37, 38, 41, 44, 49, 56],
[18, 24, 29, 31, 32, 33, 33, 34, 35, 38],
[21, 26, 30, 32, 34, 35, 35, 36, 37, 40],
[23, 26, 29, 32, 33, 35, 36, 37, 38, 41],
[20, 29, 36, 41, 44, 47, 49, 52, 55, 61],
[18, 22, 26, 30, 31, 32, 32, 34, 35, 40],
[17, 20, 26, 29, 30, 31, 32, 33, 34, 40],
[16, 23, 26, 29, 30, 31, 31, 33, 34, 41],
[14, 21, 26, 28, 29, 30, 30, 32, 33, 43],
[16, 22, 25, 26, 27, 29, 30, 31, 32, 44],
[21, 26, 28, 29, 29, 30, 31, 32, 34, 47],
[23, 27, 27, 29, 30, 31, 31, 33, 37, 50],
[23, 25, 28, 29, 30, 32, 34, 36, 43, 53],
[26, 28, 29, 34, 37, 38, 41, 45, 51, 57],
[16, 21, 25, 29, 31, 32, 33, 34, 35, 38],
[18, 24, 28, 31, 32, 33, 33, 35, 36, 40],
[19, 24, 29, 33, 33, 35, 36, 37, 38, 41],
[23, 26, 30, 34, 35, 36, 36, 38, 39, 43],
[19, 30, 39, 43, 48, 49, 51, 54, 57, 64],
[18, 22, 27, 29, 31, 32, 33, 35, 36, 42],
[17, 24, 27, 30, 31, 32, 33, 34, 35, 43],
[17, 24, 27, 29, 30, 32, 32, 33, 34, 44],
[17, 23, 26, 28, 30, 30, 31, 33, 34, 46],
[18, 23, 25, 27, 28, 30, 31, 32, 35, 48],
[21, 24, 27, 29, 31, 31, 32, 33, 38, 51],
[23, 24, 27, 28, 30, 32, 34, 37, 44, 54],
[24, 25, 27, 32, 36, 38, 41, 45, 51, 57],
[15, 21, 26, 30, 31, 31, 32, 33, 34, 38],
[18, 22, 27, 30, 32, 33, 34, 34, 35, 40],
[19, 24, 29, 33, 34, 35, 36, 37, 37, 42],
[20, 24, 29, 33, 34, 35, 35, 37, 38, 43],
[23, 28, 33, 35, 36, 36, 37, 39, 39, 45],
[20, 32, 42, 47, 50, 52, 54, 56, 59, 67],
[17, 22, 28, 31, 33, 34, 35, 36, 37, 46],
[16, 22, 27, 29, 30, 31, 33, 34, 35, 46],
[18, 24, 29, 30, 31, 31, 32, 34, 35, 48],
[18, 24, 27, 28, 30, 30, 31, 33, 36, 50],
[19, 25, 27, 30, 31, 31, 32, 34, 39, 52],
[22, 24, 28, 29, 31, 32, 34, 37, 45, 55],
[25, 25, 28, 34, 37, 40, 43, 47, 53, 59],
[15, 22, 26, 29, 31, 31, 32, 33, 34, 41],
[17, 24, 29, 31, 32, 32, 33, 34, 34, 41],
[16, 23, 27, 30, 32, 32, 34, 34, 35, 43],
[20, 27, 30, 33, 34, 35, 35, 36, 37, 44],
[19, 26, 30, 33, 35, 36, 36, 37, 38, 46],
[19, 27, 32, 35, 36, 36, 37, 38, 40, 48],
[23, 38, 46, 50, 52, 54, 56, 58, 61, 70],
[17, 25, 30, 32, 33, 34, 35, 35, 37, 48],
[20, 27, 30, 31, 33, 34, 35, 35, 37, 49],
[17, 24, 27, 28, 30, 31, 32, 33, 37, 51],
[18, 25, 28, 29, 30, 31, 32, 34, 41, 54],
[23, 26, 30, 29, 30, 33, 35, 39, 47, 56],
[25, 28, 28, 34, 38, 42, 45, 49, 54, 60],
[15, 23, 27, 30, 31, 32, 33, 33, 34, 43],
[18, 23, 27, 30, 31, 32, 32, 33, 34, 43],
[19, 25, 28, 31, 31, 32, 33, 34, 35, 44],
[19, 26, 30, 32, 33, 34, 34, 35, 36, 46],
[17, 25, 30, 33, 34, 36, 36, 37, 38, 47],
[22, 28, 32, 34, 35, 36, 37, 38, 39, 49],
[23, 29, 33, 35, 36, 37, 37, 39, 40, 51],
[29, 42, 48, 51, 54, 56, 59, 61, 64, 72],
[20, 28, 32, 33, 34, 36, 36, 38, 40, 52],
[23, 30, 32, 31, 32, 33, 34, 36, 41, 53],
[22, 27, 29, 30, 32, 33, 34, 37, 44, 55],
[25, 28, 32, 31, 32, 35, 38, 42, 50, 58],
[26, 28, 29, 35, 41, 45, 49, 52, 56, 60],
[21, 26, 29, 31, 32, 33, 33, 33, 35, 45],
[20, 25, 28, 30, 31, 32, 33, 34, 35, 46],
[20, 25, 30, 31, 32, 34, 34, 35, 36, 46],
[20, 24, 29, 30, 32, 33, 33, 35, 36, 47],
[22, 28, 31, 32, 33, 34, 35, 37, 38, 49],
[21, 28, 31, 33, 34, 34, 36, 37, 39, 51],
[21, 28, 33, 34, 35, 36, 37, 38, 40, 52],
[24, 31, 35, 36, 37, 38, 39, 40, 43, 54],
[38, 49, 53, 56, 59, 61, 63, 64, 67, 75],
[25, 31, 33, 32, 33, 34, 36, 38, 43, 55],
[28, 33, 33, 32, 34, 35, 37, 41, 47, 57],
[30, 31, 34, 33, 37, 40, 43, 47, 53, 60],
[28, 31, 33, 41, 47, 51, 54, 57, 59, 63],
[22, 26, 27, 30, 31, 32, 33, 34, 36, 48],
[21, 25, 27, 29, 31, 32, 33, 34, 37, 48],
[21, 26, 30, 31, 32, 33, 34, 35, 38, 49],
[22, 28, 30, 32, 33, 34, 34, 35, 38, 50],
[22, 26, 30, 31, 32, 33, 34, 35, 38, 51],
[23, 29, 32, 33, 34, 34, 35, 36, 39, 52],
[23, 30, 33, 34, 35, 36, 37, 38, 41, 54],
[27, 32, 35, 35, 36, 37, 38, 39, 44, 56],
[29, 35, 36, 36, 37, 39, 40, 42, 47, 58],
[47, 54, 58, 60, 63, 64, 66, 68, 71, 78],
[28, 31, 31, 32, 34, 36, 40, 43, 49, 58],
[32, 32, 33, 36, 40, 43, 46, 48, 55, 61],
[33, 32, 36, 46, 51, 55, 57, 60, 61, 64],
[22, 26, 27, 30, 31, 32, 34, 35, 39, 50],
[23, 27, 30, 32, 33, 34, 35, 36, 39, 51],
[24, 28, 30, 32, 33, 34, 34, 36, 40, 51],
[26, 29, 31, 32, 33, 34, 35, 36, 41, 52],
[25, 29, 31, 32, 33, 34, 34, 37, 41, 54],
[22, 27, 30, 33, 34, 34, 36, 37, 43, 54],
[25, 30, 32, 33, 34, 35, 35, 37, 44, 56],
[27, 31, 34, 35, 37, 37, 38, 41, 47, 57],
[31, 35, 36, 35, 37, 38, 40, 44, 50, 59],
[32, 35, 35, 35, 38, 40, 43, 46, 52, 60],
[57, 61, 65, 66, 68, 69, 71, 72, 76, 81],
[32, 31, 33, 39, 43, 45, 48, 50, 57, 62],
[33, 33, 42, 51, 55, 58, 60, 62, 64, 64],
[27, 29, 31, 32, 33, 35, 37, 39, 44, 53],
[27, 29, 32, 33, 34, 35, 37, 38, 44, 54],
[24, 27, 30, 31, 33, 35, 37, 39, 45, 55],
[26, 27, 32, 32, 34, 36, 37, 40, 46, 56],
[27, 29, 31, 32, 33, 36, 37, 40, 47, 57],
[30, 30, 34, 34, 35, 36, 38, 41, 48, 57],
[27, 29, 32, 33, 34, 36, 38, 42, 50, 59],
[30, 34, 36, 35, 36, 39, 42, 46, 53, 60],
[32, 34, 36, 35, 39, 42, 46, 50, 56, 62],
[37, 37, 36, 39, 44, 46, 48, 51, 57, 63],
[36, 35, 37, 43, 47, 49, 51, 54, 59, 64],
[67, 69, 71, 74, 76, 76, 77, 78, 81, 83],
[36, 42, 51, 58, 60, 62, 64, 65, 66, 66],
[32, 32, 33, 38, 39, 41, 43, 46, 51, 57],
[33, 31, 33, 38, 40, 42, 44, 47, 52, 59],
[30, 32, 33, 39, 42, 43, 45, 48, 53, 59],
[31, 31, 33, 38, 41, 42, 45, 49, 54, 60],
[31, 31, 32, 37, 41, 42, 46, 49, 54, 60],
[29, 31, 33, 38, 41, 43, 47, 50, 55, 61],
[28, 29, 31, 36, 40, 44, 48, 52, 56, 62],
[31, 33, 34, 39, 44, 48, 52, 55, 59, 63],
[34, 35, 35, 43, 48, 52, 56, 59, 61, 65],
[34, 34, 38, 48, 53, 57, 58, 61, 63, 66],
[37, 37, 46, 54, 56, 60, 61, 63, 65, 67],
[40, 46, 55, 62, 64, 65, 67, 68, 69, 68],
[76, 81, 84, 85, 85, 86, 86, 87, 86, 86]]

"""7-card evaluator, stdlib only. card = rank*4+suit. Higher score = better."""
STRAIGHT = [-1] * 8192
for _m in range(8192):
    # highest straight top rank (0-based rank index of top card), wheel -> 3
    for top in range(12, 2, -1):
        need = 0
        for k in range(5):
            r = top - k
            if r < 0:
                r = 12  # ace low
            need |= 1 << r
        if top == 3:
            need = (1 << 12) | 0b1111
        if (_m & need) == need:
            STRAIGHT[_m] = top
            break
POP = [bin(i).count('1') for i in range(8192)]


def top_ranks(mask, n):
    out = 0
    cnt = 0
    r = 12
    while r >= 0 and cnt < n:
        if mask >> r & 1:
            out = out * 13 + r
            cnt += 1
        r -= 1
    return out


def ev7(cards):
    sm = [0, 0, 0, 0]
    rc = [0] * 13
    for c in cards:
        r = c >> 2
        sm[c & 3] |= 1 << r
        rc[r] += 1
    allm = sm[0] | sm[1] | sm[2] | sm[3]
    for s in range(4):
        if POP[sm[s]] >= 5:
            st = STRAIGHT[sm[s]]
            if st >= 0:
                return (8 << 24) | st
            return (5 << 24) | top_ranks(sm[s], 5)
    quads = trips = 0
    pairs = []
    trip_l = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 4:
            quads = r + 1
        elif n == 3:
            trip_l.append(r)
        elif n == 2:
            pairs.append(r)
    if quads:
        q = quads - 1
        rest = allm & ~(1 << q)
        return (7 << 24) | (q << 8) | top_ranks(rest, 1)
    if trip_l and (len(trip_l) > 1 or pairs):
        t = trip_l[0]
        p = max(trip_l[1:] + pairs)
        return (6 << 24) | (t << 8) | p
    st = STRAIGHT[allm]
    if st >= 0:
        return (4 << 24) | st
    if trip_l:
        t = trip_l[0]
        rest = allm & ~(1 << t)
        return (3 << 24) | (t << 16) | top_ranks(rest, 2)
    if len(pairs) >= 2:
        a, b = pairs[0], pairs[1]
        rest = allm & ~(1 << a) & ~(1 << b)
        return (2 << 24) | (a << 16) | (b << 8) | top_ranks(rest, 1)
    if pairs:
        a = pairs[0]
        rest = allm & ~(1 << a)
        return (1 << 24) | (a << 16) | top_ranks(rest, 3)
    return top_ranks(allm, 5)

# ---------------------------------------------------------------- ICM (Malmuth-Harville, exact, subset DP)
PAY = (10.0, 7.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0)
_TR = {}


def _trans(m):
    t = _TR.get(m)
    if t is None:
        t = []
        for mask in range(1, 1 << m):
            pc = bin(mask).count('1')
            if pc > 6:
                continue
            t.append((mask, pc, tuple((j, mask ^ (1 << j)) for j in range(m) if mask >> j & 1)))
        _TR[m] = t
    return t


for _m in range(1, 8):
    _trans(_m)


def icm_eq(stacks, h):
    """expected finish points of player h given chip list `stacks` (all > 0)."""
    n = len(stacks)
    if n <= 1:
        return PAY[0]
    if n > 8:
        # too many for the payout table: keep the 8 biggest plus hero
        idx = sorted(range(n), key=lambda i: -stacks[i])[:8]
        if h not in idx:
            idx[-1] = h
        stacks = [stacks[i] for i in idx]
        h = idx.index(h)
        n = 8
    sh = stacks[h]
    o = stacks[:h] + stacks[h + 1:]
    m = n - 1
    S = float(sum(o) + sh)
    sm = [0.0] * (1 << m)
    for mask in range(1, 1 << m):
        low = mask & -mask
        sm[mask] = sm[mask ^ low] + o[low.bit_length() - 1]
    f = [0.0] * (1 << m)
    f[0] = 1.0
    eq = sh / S * PAY[0]
    for mask, pc, prevs in _trans(m):
        v = 0.0
        for j, p in prevs:
            v += f[p] * o[j] / (S - sm[p])
        f[mask] = v
        pay = PAY[pc]
        if pay:
            eq += v * sh / (S - sm[mask]) * pay
    return eq


def icm_hero(others, hero_chips):
    """others: list of positive chip counts of the other live players."""
    if hero_chips <= 0:
        return PAY[min(7, len(others))]
    return icm_eq([hero_chips] + [x for x in others if x > 0], 0)


# ---------------------------------------------------------------- push / fold charts (percent of combos)
STK = (3, 4, 5, 6, 8, 10, 12, 15, 20, 25)
PUSH = {
    1: (100, 100, 100, 95, 75, 58, 46, 35, 24, 17),   # SB (BB behind)
    2: (100, 100, 90, 75, 56, 42, 32, 23, 14, 10),    # BTN
    3: (95, 78, 58, 45, 38, 30, 22, 15, 9, 6),        # CO
    4: (85, 65, 45, 35, 28, 22, 16, 11, 7, 5),        # HJ
    5: (80, 60, 40, 32, 24, 18, 13, 9, 6, 4),
    6: (75, 55, 36, 28, 21, 16, 11, 8, 5, 3.5),
    7: (72, 52, 34, 26, 19, 14, 10, 7, 4.5, 3),       # UTG in 8-max
}
OPEN = {1: 42, 2: 38, 3: 24, 4: 17, 5: 14, 6: 12, 7: 11}


def _interp(xs, ys, x):
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            t = (x - xs[i - 1]) / float(xs[i] - xs[i - 1])
            return ys[i - 1] + t * (ys[i] - ys[i - 1])
    return ys[-1]


def push_pct(M, k):
    k = 1 if k < 1 else (7 if k > 7 else int(k))
    if M > 25:
        return PUSH[k][-1] * 25.0 / M
    return _interp(STK, PUSH[k], M)


def open_pct(k):
    k = 1 if k < 1 else (7 if k > 7 else int(k))
    return OPEN[k]


def cid(c1, c2):
    r1, r2 = c1 >> 2, c2 >> 2
    if r1 < r2:
        r1, r2 = r2, r1
        c1, c2 = c2, c1
    if r1 == r2:
        return r1 * 13 + r2
    return r1 * 13 + r2 if (c1 & 3) == (c2 & 3) else r2 * 13 + r1


def eq_vs_top(c, X):
    """hero class c equity (0..1) vs a range of the top X percent of combos."""
    if X < 3.0:
        X = 3.0
    return _interp(LEVELS, EQT[c], X) / 100.0


# classes sorted by percentile, with combo counts (for calling-frequency estimates)
_ORDER = sorted((PCT[c], c) for c in range(169) if PCT[c] > 0)


def _combos(c):
    hi, lo = divmod(c, 13)
    if hi == lo:
        return 6
    return 4 if hi > lo else 12


_ORDER = [(p, c, _combos(c)) for p, c in _ORDER]


def call_freq(Xo, need, lvl_idx=4):
    """percent of combos (out of all) within the top Xo% whose equity vs a ~16% range >= need."""
    tot = 0
    for p, c, w in _ORDER:
        if p > Xo:
            break
        if EQT[c][lvl_idx] / 100.0 >= need:
            tot += w
    return tot / 13.26


# ---------------------------------------------------------------- the bot
class Bot(Agent):
    DEBUG = False
    PUSH_BF_K = 0.5      # how hard the bubble factor tightens first-in shoves
    OPEN_BF_K = 0.4      # ... and deep open-raises
    CALL_MARGIN = 0.025  # extra equity over the ICM requirement to call a shove
    XS_MULT = 1.1        # widen the assumed shove range
    PUSH_SCALE = 1.15
    OPEN_SCALE = 1.35

    def __init__(self):
        self.rng = random.Random(20260)
        self.new_table(None, None, None)

    def new_table(self, rules, seat, n_players):
        self.seen = {}
        self.rais = {}
        self._h = -1
        self._ptr = 0
        self._hs = set()
        self._hr = set()
        self.rng = random.Random(777)

    def hand_end(self, result):
        pass

    # ------------------------------------------------------------ entry
    def _el(self):
        return (time.perf_counter() - self._t0) * 1e6

    def act(self, obs):
        self._t0 = time.perf_counter()
        try:
            a = self._act(obs)
        except Exception:
            if Bot.DEBUG:
                raise
            a = None
        return self._legalize(obs, a)

    def _legalize(self, obs, a):
        try:
            legal = set(obs.legal)
        except Exception:
            legal = {'fold', 'check', 'call'}
        try:
            lo, hi = obs.min_raise, obs.max_raise
            lo, hi = (lo, hi) if lo <= hi else (hi, lo)
        except Exception:
            lo = hi = 0
        kind, amt = ('check', 0) if a is None else a
        if kind == 'raise':
            if 'raise' in legal:
                try:
                    amt = int(amt)
                except Exception:
                    amt = lo
                amt = lo if amt < lo else (hi if amt > hi else amt)
                return ('raise', amt)
            kind = 'call' if 'call' in legal else 'check'
        if kind == 'fold' and 'check' in legal:
            kind = 'check'
        if kind in legal:
            return (kind, 0)
        for k in ('check', 'fold', 'call'):
            if k in legal:
                return (k, 0)
        return ('fold', 0)

    # ------------------------------------------------------------ helpers
    def _prep(self, obs):
        n = len(obs.stacks)
        stacks = [int(x) for x in obs.stacks]
        bets = [int(x) for x in obs.bets] if obs.bets is not None and len(obs.bets) == n else [0] * n
        inh = list(obs.in_hand) if obs.in_hand is not None and len(obs.in_hand) == n else [s > 0 for s in stacks]
        c = {}
        c['n'] = n
        c['stacks'] = stacks
        c['bets'] = bets
        c['inh'] = inh
        c['h'] = obs.seat
        bl = obs.blinds
        try:
            sb, bb = bl
            bb = max(1, int(bb))
            sb = max(1, int(sb))
        except Exception:
            sb, bb = 10, 20
        c['sb'] = sb
        c['bb'] = bb
        c['pot'] = obs.pot if isinstance(obs.pot, (int, float)) else 0
        c['hist'] = obs.history if isinstance(obs.history, (list, tuple)) else []
        return c

    def _positions(self, obs, c):
        n = c['n']
        alive = [i for i in range(n) if c['stacks'][i] > 0 or c['inh'][i]]
        aset = set(alive)
        btn = obs.button if isinstance(obs.button, int) else 0

        def nxt(i):
            j = i
            for _ in range(n):
                j = (j + 1) % n
                if j in aset:
                    return j
            return i
        if len(alive) <= 1:
            c['order'] = alive[:]
            c['alive'] = alive
            return
        if len(alive) == 2:
            sbs = btn if btn in aset else alive[0]
            bbs = alive[0] if alive[1] == sbs else alive[1]
        else:
            sbs = nxt(btn)
            bbs = nxt(sbs)
        order = []
        j = bbs
        for _ in range(len(alive) - 1):
            j = nxt(j)
            order.append(j)
        order.append(bbs)
        c['order'] = order      # preflop action order, BB last
        c['alive'] = alive
        c['bbseat'] = bbs
        c['sbseat'] = sbs

    def _behind(self, c, seat):
        """players after `seat` in preflop order (alive at hand start), and those still live."""
        order = c['order']
        if seat not in order:
            return 3, 3
        i = order.index(seat)
        after = order[i + 1:]
        live = [s for s in after if c['inh'][s] and c['stacks'][s] > 0]
        return len(after), len(live)

    def _observe(self, obs, c):
        try:
            if obs.hand_no != self._h:
                self._h = obs.hand_no
                self._ptr = 0
                self._hs = set()
                self._hr = set()
            hist = c['hist']
            for (s, a) in list(hist)[self._ptr:]:
                try:
                    if s not in self._hs:
                        self._hs.add(s)
                        self.seen[s] = self.seen.get(s, 0) + 1
                    if a[0] == 'raise' and a[1] > c['bb'] and s not in self._hr:
                        self._hr.add(s)
                        self.rais[s] = self.rais.get(s, 0) + 1
                except Exception:
                    pass
            self._ptr = len(hist)
        except Exception:
            pass

    def _obs_agg(self, s):
        sn = self.seen.get(s, 0)
        return sn, 100.0 * (self.rais.get(s, 0) + 2.0) / (sn + 10.0)

    def _bf(self, c, v):
        """bubble factor of risking min(hero, v) chips against seat v."""
        chips = {i: c['stacks'][i] + c['bets'][i] for i in c['alive'] if c['stacks'][i] + c['bets'][i] > 0}
        h = c['h']
        if h not in chips or v not in chips or len(chips) < 3:
            return 1.0
        r = min(chips[h], chips[v])
        oth = [x for i, x in chips.items() if i != h and i != v]
        e0 = icm_hero([chips[v]] + oth, chips[h])
        ew = icm_hero([chips[v] - r] + oth, chips[h] + r)
        el = icm_hero([chips[v] + r] + oth, chips[h] - r)
        if ew - e0 < 1e-6:
            return 1.0
        return max(0.8, min(4.0, (e0 - el) / (ew - e0)))

    def _scenario(self, c, v, hero_c, v_c, want_fold=True):
        """ICM points for hero: (fold, win, lose, split-free) when hero puts hero_c in total and v puts v_c
        (both totals including chips already in front). Others keep their stacks behind."""
        h = c['h']
        st, bt = c['stacks'], c['bets']
        hero_tot = st[h] + bt[h]
        v_tot = st[v] + bt[v]
        dead = c['pot'] + sum(bt) - bt[h] - bt[v]
        others = [st[i] for i in c['alive'] if i != h and i != v and st[i] > 0]
        # fold: hero keeps his stack behind, villain takes the pot
        e_fold = icm_hero([st[v] + dead + bt[h] + bt[v]] + others, st[h]) if want_fold else 0.0
        match = min(hero_c, v_c, hero_tot, v_tot)
        main = dead + 2 * match
        h_behind = hero_tot - match
        v_behind = v_tot - match
        e_win = icm_hero([v_behind] + others, h_behind + main)
        e_lose = icm_hero([v_behind + main] + others, h_behind)
        return e_fold, e_win, e_lose

    # ------------------------------------------------------------ main
    def _act(self, obs):
        c = self._prep(obs)
        if obs.street == 0:
            self._observe(obs, c)
            return self._pre(obs, c)
        return self._post(obs, c)

    def _shove(self, obs):
        return ('raise', obs.max_raise)

    def _raise_to(self, obs, amt):
        return ('raise', max(obs.min_raise, min(obs.max_raise, int(amt))))

    # ------------------------------------------------------------ preflop
    def _pre(self, obs, c):
        self._positions(obs, c)
        h, bb = c['h'], c['bb']
        st, bt = c['stacks'], c['bets']
        hole = obs.hole
        cl = cid(hole[0], hole[1])
        p = PCT[cl]
        mystack = st[h]
        chips = mystack + bt[h]
        M = chips / float(bb)
        to_call = obs.to_call
        mx = max(bt)
        raises = [a for (s, a) in c['hist'] if isinstance(a, (tuple, list)) and len(a) > 1 and a[0] == 'raise'
                  and isinstance(a[1], (int, float)) and a[1] > bb]
        nr = len(raises)
        raised = mx > bb or nr > 0
        n_after, k = self._behind(c, h)
        can_check = 'check' in obs.legal
        if not raised:
            return self._pre_unraised(obs, c, cl, p, M, k, can_check, to_call)
        return self._pre_raised(obs, c, cl, p, M, nr, to_call)

    def _vill_behind(self, c):
        """biggest live opponent behind hero (the one most likely to be the caller)."""
        h = c['h']
        best, bs = -1, None
        # opponents still to act after hero
        order = c['order']
        if h in order:
            after = [s for s in order[order.index(h) + 1:] if c['inh'][s] and c['stacks'][s] > 0]
        else:
            after = []
        for s in after:
            tot = c['stacks'][s] + c['bets'][s]
            if tot > best:
                best, bs = tot, s
        return bs

    def _pre_unraised(self, obs, c, cl, p, M, k, can_check, to_call):
        h, bb = c['h'], c['bb']
        st, bt = c['stacks'], c['bets']
        limpers = max(0, sum(1 for i in range(c['n']) if c['inh'][i] and i != h and bt[i] >= bb
                             and i != c.get('bbseat')))
        # big stacks protect: risk premium
        bf = 1.0
        v = self._vill_behind(c)
        if v is not None and M <= 25:
            bf = self._bf(c, v)
        adj = 1.0 / (1.0 + self.PUSH_BF_K * (bf - 1.0))
        floor = _interp((4, 6, 8, 10, 14), (0.9, 0.72, 0.6, 0.52, 0.45), M)
        if adj < floor:
            adj = floor
        is_bb = (h == c.get('bbseat')) or (k == 0 and can_check)
        kk = max(1, k)
        if M <= 4.0:
            adj = max(adj, 0.9)
        if M <= 22:
            if is_bb:
                # big blind, option
                if limpers > 0 or True:
                    thr = min(push_pct(M, 1), 30) * adj * 0.6
                    if M <= 12 and p <= thr and limpers > 0:
                        return self._shove(obs)
                    if p <= 8 and M > 12:
                        return self._raise_to(obs, bb * (3.5 + limpers))
                return ('check', 0)
            thr = push_pct(M, kk) * adj * self.PUSH_SCALE
            if limpers:
                thr *= 1.0
            if p <= thr or (M <= 2.5):
                return self._shove(obs)
            if M > 14:
                o = open_pct(kk) * adj
                if p <= o:
                    return self._raise_to(obs, bb * (2.2 + limpers))
            if can_check:
                return ('check', 0)
            # small blind completes only when it is nearly free
            if to_call <= bb * 0.5 + 1 and M >= 8 and p <= 40 and k == 1:
                return ('call', 0)
            return ('fold', 0)
        # deep
        if is_bb:
            if p <= 9 and limpers > 0:
                return self._raise_to(obs, bb * (3.5 + limpers))
            return ('check', 0)
        o = open_pct(kk) * self.OPEN_SCALE * (1.0 / (1.0 + self.OPEN_BF_K * (bf - 1.0)))
        if p <= o:
            amt = bb * (2.5 + limpers)
            if amt >= 0.4 * (c['stacks'][h] + bt[h]):
                return self._shove(obs)
            return self._raise_to(obs, amt)
        if can_check:
            return ('check', 0)
        return ('fold', 0)

    def _pre_raised(self, obs, c, cl, p, M, nr, to_call):
        h, bb = c['h'], c['bb']
        st, bt = c['stacks'], c['bets']
        # the raiser = largest bet among others
        r, rb = None, -1
        for i in range(c['n']):
            if i != h and bt[i] > rb:
                r, rb = i, bt[i]
        if r is None:
            return ('fold', 0)
        r_tot = st[r] + bt[r]
        r_M = r_tot / float(bb)
        r_allin = st[r] == 0
        _, k_r = self._behind(c, r)
        k_r = max(1, k_r)
        # extra live opponents who already put chips in
        extra = sum(1 for i in range(c['n']) if i != h and i != r and c['inh'][i] and bt[i] >= max(bb, rb * 0.9))
        hero_tot = st[h] + bt[h]
        call_is_allin = to_call >= st[h]
        sn, obs_pct = self._obs_agg(r)
        # opponent range estimates
        xo = open_pct(k_r)
        if sn >= 6:
            xo = 0.55 * xo + 0.45 * min(60.0, obs_pct)
        if nr >= 2:
            xo = min(xo, 7.0)
        if r_allin or rb >= 0.85 * r_tot:
            xs = push_pct(r_M, k_r)
            if sn >= 6:
                xs = 0.6 * xs + 0.4 * min(70.0, obs_pct)
            if nr >= 2:
                xs = min(xs, 6.0)
            xs = max(3.0, min(80.0, xs * self.XS_MULT))
        else:
            xs = xo
        # ---------- committed spots: call vs fold by ICM
        if r_allin or call_is_allin and M <= 40:
            e_fold, e_win, e_lose = self._scenario(c, r, bt[h] + min(to_call, st[h]), rb)
            need = (e_fold - e_lose) / max(1e-9, (e_win - e_lose))
            if r_allin:
                X = xs
            else:
                X = max(xo * 0.8, 4.0) if nr < 2 else 6.0
            eq = eq_vs_top(cl, X) - 0.08 * extra
            if eq >= need + self.CALL_MARGIN:
                return ('call', 0)
            # facing a non-all-in raise we cannot call: jam is the same as calling here
            return ('fold', 0)
        # ---------- short stack, facing an open: fold / call / jam by ICM EV
        if M <= 15 and rb < 0.5 * r_tot:
            return self._short_vs_open(obs, c, cl, p, M, r, rb, xo, to_call, extra, nr)
        # ---------- deeper: simple rules
        bf = self._bf(c, r) if M <= 40 else 1.0
        tight = 1.0 / (1.0 + 0.5 * (bf - 1.0))
        wide = max(0.0, min(1.5, (xo - 22.0) / 20.0))
        jam_thr = (3.6 + 3.0 * wide) * 1.2 if nr == 1 else 3.6
        size_bb = to_call / float(bb)
        if p <= jam_thr:
            if M <= 40 or nr >= 2 or rb >= 0.3 * hero_tot:
                return self._shove(obs)
            return self._raise_to(obs, 3.0 * rb + extra * rb)
        callp = 6.5 * (1.0 + wide)
        is_bb = h == c.get('bbseat')
        if is_bb and size_bb <= 3.2:
            callp = 24.0
        elif size_bb <= 3.0:
            callp = 9.0
        if to_call > 0.25 * st[h]:
            callp = min(callp, 5.5)
        if nr >= 2:
            callp = min(callp, 4.5)
        callp *= tight
        if p <= callp and nr < 2:
            return ('call', 0)
        if p <= callp and nr >= 2 and p <= 3.6:
            return ('call', 0)
        return ('fold', 0)

    def _short_vs_open(self, obs, c, cl, p, M, r, rb, xo, to_call, extra, nr):
        h, bb = c['h'], c['bb']
        st, bt = c['stacks'], c['bets']
        hero_tot = st[h] + bt[h]
        v_tot = st[r] + bt[r]
        if p > 55 and M > 5:
            return ('fold', 0)
        # fold
        e_fold, _, _ = self._scenario(c, r, bt[h], rb)
        # call (hero commits to_call; treat as showdown-equity with a realization haircut)
        hc = bt[h] + to_call
        _, e_w, e_l = self._scenario(c, r, hc, rb, False)
        eq_c = eq_vs_top(cl, xo) * 0.9 - 0.05 * extra
        ev_call = eq_c * e_w + (1 - eq_c) * e_l
        if self._el() > 260:
            return self._shove(obs) if p <= max(4.0, min(30.0, 40 - 2.2 * M)) else ('fold', 0)
        # jam: villain continues with the part of his range that beats the pot odds
        jam_c = hero_tot
        v_extra = min(jam_c, v_tot) - rb
        dead = c['pot'] + sum(bt) - bt[h] - bt[r]
        final = dead + 2 * min(jam_c, v_tot)
        need = max(0.15, v_extra / max(1.0, final)) * 1.12
        cf = call_freq(xo, need)
        cf = min(cf, xo)
        pf = max(0.0, 1.0 - cf / max(1.0, xo))
        if extra:
            pf *= 0.5 ** extra
        eq_j = eq_vs_top(cl, max(3.0, cf)) - 0.08 * extra
        # steal: hero takes the pot
        others = [st[i] for i in c['alive'] if i != h and i != r and st[i] > 0]
        e_steal = icm_hero([st[r]] + others, st[h] + bt[h] + c['pot'] + sum(bt) - bt[h])
        _, jw, jl = self._scenario(c, r, jam_c, jam_c, False)
        ev_jam = pf * e_steal + (1 - pf) * (eq_j * jw + (1 - eq_j) * jl)
        best = max(e_fold, ev_call, ev_jam)
        if best <= e_fold + 0.005:
            return ('fold', 0)
        if ev_jam >= ev_call:
            return self._shove(obs)
        return ('call', 0)

    # ------------------------------------------------------------ postflop
    def _tier(self, obs):
        hole, board = list(obs.hole), list(obs.board)
        sc = ev7(hole + board)
        cat = sc >> 24
        hr = sorted((x >> 2 for x in hole), reverse=True)
        br = sorted((x >> 2 for x in board), reverse=True)
        bset = set(br)
        pocket = hr[0] == hr[1]
        tier = 0
        if cat >= 4:
            tier = 5
            if len(board) == 5 and ev7(board) >= sc:
                tier = 1
            elif cat == 5:
                top = (sc >> 0) & 0xFFFFFFF
                hs = [x for x in hole if sum(1 for y in board if (y & 3) == (x & 3)) >= 3]
                if hs and max(x >> 2 for x in hs) < 10:
                    tier = 3
            elif cat == 4 and len(board) >= 4:
                # straight with only one hole card contributing on a connected board: keep, but not a monster
                pass
        elif cat == 3:
            t = (sc >> 16) & 0xFF
            if pocket and hr[0] in bset:
                tier = 5
            elif (hr[0] in bset or hr[1] in bset):
                tier = 4
            else:
                tier = 1
        elif cat == 2:
            if hr[0] in bset and hr[1] in bset:
                tier = 4
            elif pocket and hr[0] > br[0]:
                tier = 4
            elif hr[0] in bset or hr[1] in bset:
                tier = 3 if (br[0] in hr) else 2
            else:
                tier = 1
        elif cat == 1:
            pr = (sc >> 16) & 0xFF
            if pocket:
                if hr[0] > br[0]:
                    tier = 4 if hr[0] >= 7 else 3
                elif len(br) > 1 and hr[0] > br[1]:
                    tier = 2
                else:
                    tier = 1
            elif pr in hr:
                kick = hr[1] if pr == hr[0] else hr[0]
                if pr == br[0]:
                    tier = 3 if kick >= 8 else 2
                elif len(br) > 1 and pr == br[1]:
                    tier = 2
                else:
                    tier = 1
            else:
                tier = 0
        else:
            tier = 0
        # draws
        outs = 0
        allc = hole + board
        if len(board) < 5:
            for s in range(4):
                cnt = sum(1 for x in allc if (x & 3) == s)
                if cnt == 4 and any((x & 3) == s for x in hole):
                    outs = 9
            bm = 0
            for x in board:
                bm |= 1 << (x >> 2)
            hm = 0
            for x in hole:
                if not (bm >> (x >> 2)) & 1:
                    hm |= 1 << (x >> 2)
            full = bm | hm | sum(1 << (x >> 2) for x in hole if (bm >> (x >> 2)) & 1)
            if hm and cat < 4:
                comp = 0
                for r in range(13):
                    if not (full >> r) & 1:
                        m2 = full | (1 << r)
                        if STRAIGHT[m2] >= 0 and STRAIGHT[m2 & ~hm] < 0:
                            comp += 1
                outs = min(15, outs + 4 * comp)
        return tier, outs

    def _post(self, obs, c):
        h = c['h']
        st, bt = c['stacks'], c['bets']
        mystack = st[h]
        tier, outs = self._tier(obs)
        pot = c['pot'] + sum(bt)
        to_call = obs.to_call
        street = obs.street
        nopp = sum(1 for i in range(c['n']) if c['inh'][i] and i != h)
        left = 2 if street == 1 else 1
        draw_eq = min(0.6, outs * (0.04 if street == 1 else 0.022))
        spr = mystack / float(max(1, pot))
        rr = self.rng.random()
        if to_call <= 0:
            # we can bet
            bet = None
            if tier >= 4:
                bet = 0.7 * pot
            elif tier == 3:
                bet = 0.55 * pot if (nopp <= 2 or rr < 0.5) else None
            elif tier == 2 and nopp == 1 and rr < 0.25:
                bet = 0.4 * pot
            elif outs >= 8 and street < 3 and rr < 0.55 and nopp <= 2:
                bet = 0.5 * pot
            elif tier <= 1 and nopp == 1 and street == 1 and rr < 0.25 and self._we_raised_pre(c):
                bet = 0.4 * pot
            if bet is None:
                return ('check', 0)
            if spr <= 1.2 or bet >= 0.5 * mystack:
                if tier >= 3 or outs >= 8:
                    return self._shove(obs)
            return self._raise_to(obs, bt[h] + max(bet, c['bb']))
        # facing a bet
        odds = to_call / float(pot + to_call) if pot + to_call > 0 else 0.5
        allin = to_call >= mystack
        if allin:
            need = self._icm_need(c, to_call)
            eqs = {5: 0.9, 4: 0.78, 3: 0.62, 2: 0.45, 1: 0.3, 0: 0.15}
            eq = max(eqs[tier], draw_eq + 0.05 if outs else 0)
            return ('call', 0) if eq >= need + 0.04 else ('fold', 0)
        if tier == 5:
            if spr < 3 or rr < 0.5:
                return self._shove(obs) if spr < 3 else self._raise_to(obs, bt[h] + to_call + 0.9 * (pot + to_call))
            return ('call', 0)
        if tier == 4:
            return ('call', 0) if odds < 0.45 or street < 3 else ('call', 0)
        if tier == 3:
            return ('call', 0) if odds <= 0.34 else ('fold', 0)
        if tier == 2:
            return ('call', 0) if odds <= (0.25 if street < 3 else 0.17) else ('fold', 0)
        if outs and draw_eq * 1.15 >= odds:
            return ('call', 0)
        if tier == 1 and odds <= 0.12:
            return ('call', 0)
        return ('fold', 0)

    def _we_raised_pre(self, c):
        for (s, a) in c['hist']:
            try:
                if s == c['h'] and a[0] == 'raise' and a[1] > c['bb']:
                    return True
            except Exception:
                pass
        return False

    def _icm_need(self, c, to_call):
        """equity needed to call an all-in postflop, ICM-adjusted (villain = biggest bettor)."""
        h = c['h']
        st, bt = c['stacks'], c['bets']
        v, vb = None, -1
        for i in range(c['n']):
            if i != h and c['inh'][i] and bt[i] > vb:
                v, vb = i, bt[i]
        if v is None:
            return 0.5
        try:
            hero_c = bt[h] + min(to_call, st[h])
            e_fold, e_win, e_lose = self._scenario(c, v, hero_c, vb)
            # chips committed earlier are already inside the pot: fold keeps only the stack behind
            return max(0.05, min(0.95, (e_fold - e_lose) / max(1e-9, e_win - e_lose)))
        except Exception:
            return 0.5


try:
    import gc
    gc.collect()
    gc.freeze()
except Exception:
    pass
