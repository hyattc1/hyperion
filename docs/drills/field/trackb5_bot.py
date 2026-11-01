"""Sequoia bot night, Track B from scratch, kit B. Scrambled ranks. Steps 0, 1, 2, 2b and 3 of the spec.
Standard library only. Cards are ints 0..51 = strength*4 + suit, strength 0 = weakest .. 12 = strongest."""
from __future__ import annotations

import random
import time
from itertools import combinations, combinations_with_replacement

_T_IMPORT = time.perf_counter()

# ----------------------------------------------------------------------------- step 0: cards
# Printed rank index (0 = printed 2 .. 12 = printed A) -> tonight's strength (0 weakest .. 12 strongest).
REMAP = [1, 10, 9, 5, 11, 2, 3, 7, 8, 4, 0, 12, 6]
SUITS = "cdhs"
PRINTED = "23456789TJQKA"


def parse_card(c) -> int:
    """Kit card {"rank": 2..14, "suit": "H"} or a string like "Th", "10h", "AS" -> strength card int."""
    if isinstance(c, dict):
        d = int(c["rank"]) - 2
        s = SUITS.index(str(c["suit"])[0].lower())
    else:
        t = str(c).strip()
        s = SUITS.index(t[-1].lower())
        r = t[:-1].upper()
        d = 8 if r == "10" else PRINTED.index(r)
    return REMAP[d] * 4 + s


def parse_cards(cs) -> tuple:
    return tuple(parse_card(c) for c in cs)


# ----------------------------------------------------------------------------- step 2: evaluator
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
_WHEEL = 0b1000000001111


def _straight_top(mask: int) -> int:
    """Top strength of the straight in a 5-distinct-rank mask, or -1."""
    for top in range(12, 3, -1):
        if (mask >> (top - 4)) & 31 == 31:
            return top
    return 3 if mask == _WHEEL else -1


def _class5(ranks) -> tuple:
    """(category, tiebreaks) for five ranks that are not a flush."""
    cnt: dict = {}
    for r in ranks:
        cnt[r] = cnt.get(r, 0) + 1
    groups = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    pattern = tuple(n for _, n in groups)
    kick = tuple(r for r, _ in groups)
    if pattern == (4, 1):
        return (7,) + kick
    if pattern == (3, 2):
        return (6,) + kick
    if len(cnt) == 5:
        mask = 0
        for r in ranks:
            mask |= 1 << r
        t = _straight_top(mask)
        return (4, t) if t >= 0 else (0,) + kick
    if pattern == (3, 1, 1):
        return (3,) + kick
    if pattern == (2, 2, 1):
        return (2,) + kick
    return (1,) + kick


def _build_evaluator():
    classes = set()
    nf5 = {}
    for ranks in combinations_with_replacement(range(13), 5):
        if ranks[0] == ranks[4]:  # five of a rank
            continue
        cls = _class5(ranks)
        prod = 1
        for r in ranks:
            prod *= PRIMES[r]
        nf5[prod] = cls
        classes.add(cls)
    fl5 = {}
    for ranks in combinations(range(13), 5):
        mask = 0
        for r in ranks:
            mask |= 1 << r
        t = _straight_top(mask)
        cls = (8, t) if t >= 0 else (5,) + tuple(sorted(ranks, reverse=True))
        fl5[mask] = cls
        classes.add(cls)
    order = {cls: i + 1 for i, cls in enumerate(sorted(classes))}
    nf = {p: order[c] for p, c in nf5.items()}
    fl = {m: order[c] for m, c in fl5.items()}
    for size in (6, 7):
        for ranks in combinations_with_replacement(range(13), size):
            prod = 1
            bad = False
            last = -1
            run = 0
            for r in ranks:
                prod *= PRIMES[r]
                if r == last:
                    run += 1
                    if run >= 5:
                        bad = True
                        break
                else:
                    last, run = r, 1
            if bad:
                continue
            best = 0
            for r in set(ranks):
                v = nf[prod // PRIMES[r]]
                if v > best:
                    best = v
            nf[prod] = best
    for size in (6, 7):
        for ranks in combinations(range(13), size):
            mask = 0
            for r in ranks:
                mask |= 1 << r
            fl[mask] = max(fl[mask & ~(1 << r)] for r in ranks)
    return nf, fl, len(classes)


NF, FL, N_CLASSES = _build_evaluator()


def evaluate(cards) -> int:
    """Strength 1..7462 of the best five-card hand among 5 to 7 strength-space cards."""
    cnt = [0, 0, 0, 0]
    m = [0, 0, 0, 0]
    prod = 1
    for c in cards:
        r = c >> 2
        s = c & 3
        prod *= PRIMES[r]
        m[s] |= 1 << r
        cnt[s] += 1
    for s in range(4):
        if cnt[s] >= 5:
            return FL[m[s]]
    return NF[prod]


def _ev2(c0: int, c1: int, bp: int, bm: list, bc: list) -> int:
    """Strength of hole (c0, c1) on a 5-card board given as prime product, suit masks and suit counts."""
    r0, s0, r1, s1 = c0 >> 2, c0 & 3, c1 >> 2, c1 & 3
    if s0 == s1:
        if bc[s0] >= 3:
            return FL[bm[s0] | (1 << r0) | (1 << r1)]
    else:
        if bc[s0] >= 4:
            return FL[bm[s0] | (1 << r0)]
        if bc[s1] >= 4:
            return FL[bm[s1] | (1 << r1)]
    if 5 in bc:
        return FL[bm[bc.index(5)]]
    return NF[bp * PRIMES[r0] * PRIMES[r1]]


# ----------------------------------------------------------------------------- step 1: lists (strength ranks)
# strength: 0=2 1=3 2=4 3=5 4=6 5=7 6=8 7=9 8=T 9=J 10=Q 11=K 12=A (standard names in strength space)
def hand_class(hole) -> tuple:
    """(hi, lo, suited) in strength ranks; pairs are (r, r, False)."""
    a, b = hole
    ra, rb = a >> 2, b >> 2
    hi, lo = (ra, rb) if ra >= rb else (rb, ra)
    return hi, lo, (a & 3) == (b & 3) and ra != rb


def is_premium(hc) -> bool:  # 99+, AK, AQ, AJs, KQs
    hi, lo, s = hc
    if hi == lo:
        return hi >= 7
    if hi == 12 and lo >= 10:
        return True
    if hi == 12 and lo == 9 and s:
        return True
    return hi == 11 and lo == 10 and s


def is_playable(hc) -> bool:  # any pair, two cards T+, suited ace, suited connectors 65s+
    hi, lo, s = hc
    if hi == lo:
        return True
    if lo >= 8:
        return True
    if s and hi == 12:
        return True
    return s and hi - lo == 1 and lo >= 3  # 65s: five is strength 3


def is_short_push(hc) -> bool:  # under 8 bb extras: any ace, any king with a suited or T+ kicker
    hi, lo, s = hc
    return hi == 12 or (hi == 11 and (s or lo >= 8))


def is_qq_ak(hc) -> bool:
    hi, lo, s = hc
    return (hi == lo and hi >= 10) or (hi == 12 and lo == 11)


def is_tt_ak(hc) -> bool:
    hi, lo, s = hc
    return (hi == lo and hi >= 8) or (hi == 12 and lo == 11)


def is_77_aq(hc) -> bool:
    hi, lo, s = hc
    return (hi == lo and hi >= 5) or (hi == 12 and lo >= 10)


# ----------------------------------------------------------------------------- step 3: equity table (import)
def _classes() -> list:
    out = []
    for hi in range(13):
        for lo in range(hi + 1):
            if hi == lo:
                out.append((hi, lo, False))
            else:
                out.append((hi, lo, True))
                out.append((hi, lo, False))
    return out


CLASSES = _classes()  # 169
WEIGHT = {c: (6 if c[0] == c[1] else (4 if c[2] else 12)) for c in CLASSES}


def _rep(cls) -> tuple:
    hi, lo, s = cls
    if hi == lo:
        return (hi * 4, hi * 4 + 1)
    return (hi * 4, lo * 4) if s else (hi * 4, lo * 4 + 1)


def _equities(hole, samples: int, rng) -> tuple:
    """(equity vs 1, equity vs 3) from one set of deals: three random opponents, the first is the vs-1 opponent."""
    h0, h1 = hole
    rest = [c for c in range(52) if c != h0 and c != h1]
    sample = rng.sample
    pr = PRIMES
    w1 = 0.0
    w3 = 0.0
    for _ in range(samples):
        cs = sample(rest, 11)
        bp = 1
        bm = [0, 0, 0, 0]
        bc = [0, 0, 0, 0]
        for c in cs[:5]:
            r = c >> 2
            s = c & 3
            bp *= pr[r]
            bm[s] |= 1 << r
            bc[s] += 1
        hv = _ev2(h0, h1, bp, bm, bc)
        o1 = _ev2(cs[5], cs[6], bp, bm, bc)
        if hv > o1:
            w1 += 1.0
        elif hv == o1:
            w1 += 0.5
        o2 = _ev2(cs[7], cs[8], bp, bm, bc)
        o3 = _ev2(cs[9], cs[10], bp, bm, bc)
        mx = o1 if o1 >= o2 else o2
        if o3 > mx:
            mx = o3
        if hv > mx:
            w3 += 1.0
        elif hv == mx:
            w3 += 1.0 / (1 + (o1 == mx) + (o2 == mx) + (o3 == mx))
    return w1 / samples, w3 / samples


SAMPLES = 2000
EQ1: dict = {}
EQ3: dict = {}
PCT: dict = {}


def _build_equity(samples: int) -> None:
    rng = random.Random(20261031)
    for cls in CLASSES:
        EQ1[cls], EQ3[cls] = _equities(_rep(cls), samples, rng)
    above = 0
    for cls in sorted(CLASSES, key=lambda c: -EQ1[c]):
        PCT[cls] = above / 1326.0
        above += WEIGHT[cls]


_build_equity(SAMPLES)

# step 3b: third column, equity versus one opponent dealt from the top 12 percent
EQT: dict = {}
SAMPLES_T = 1000


def _build_third(samples: int) -> None:
    top = [(a, b) for a in range(52) for b in range(a + 1, 52) if PCT[hand_class((a, b))] < 0.12]
    rng = random.Random(7)
    rr = rng.randrange
    sample = rng.sample
    pr = PRIMES
    for cls in CLASSES:
        h0, h1 = _rep(cls)
        pool = [p for p in top if h0 not in p and h1 not in p]
        rest = [c for c in range(52) if c != h0 and c != h1]
        npool = len(pool)
        w = 0.0
        for _ in range(samples):
            o0, o1 = pool[rr(npool)]
            while True:
                cs = sample(rest, 5)
                if o0 not in cs and o1 not in cs:
                    break
            bp = 1
            bm = [0, 0, 0, 0]
            bc = [0, 0, 0, 0]
            for c in cs:
                r = c >> 2
                s = c & 3
                bp *= pr[r]
                bm[s] |= 1 << r
                bc[s] += 1
            hv = _ev2(h0, h1, bp, bm, bc)
            ov = _ev2(o0, o1, bp, bm, bc)
            if hv > ov:
                w += 1.0
            elif hv == ov:
                w += 0.5
        EQT[cls] = w / samples


_build_third(SAMPLES_T)
IMPORT_SECONDS = time.perf_counter() - _T_IMPORT

# ----------------------------------------------------------------------------- step 3: ICM curve
PAYOUTS = (10.0, 7.0, 5.0, 4.0, 3.0, 2.0, 1.0, 0.0)


def icm_value(stacks, me: int, payouts=PAYOUTS) -> float:
    """Malmuth-Harville expected points of seat `me` over the live stacks (subset DP over the other seats)."""
    live = [i for i, s in enumerate(stacks) if s > 0]
    n = len(live)
    if n == 0:
        return 0.0
    if stacks[me] <= 0:
        return payouts[n] if n < len(payouts) else 0.0
    others = [float(stacks[i]) for i in live if i != me]
    mine = float(stacks[me])
    tot = mine + sum(others)
    k = len(others)
    nsub = 1 << k
    sums = [0.0] * nsub
    f = [0.0] * nsub
    f[0] = 1.0
    res = 0.0
    npay = len(payouts)
    for S in range(nsub):
        if S:
            low = S & -S
            j = low.bit_length() - 1
            sums[S] = sums[S ^ low] + others[j]
            acc = 0.0
            T = S
            while T:
                lb = T & -T
                j = lb.bit_length() - 1
                T ^= lb
                Sp = S ^ lb
                acc += f[Sp] * others[j] / (tot - sums[Sp])
            f[S] = acc
        pos = bin(S).count("1")
        if pos < npay:
            res += payouts[pos] * f[S] * mine / (tot - sums[S])
    return res


C = {"pts": None}


def build_curve(stacks, me: int) -> None:
    """V at 0, 0.5x, x, 2x and all the chips, opponents scaled pro rata; decisions interpolate."""
    s = float(stacks[me])
    tot = float(sum(v for v in stacks if v > 0))
    n_live = sum(1 for v in stacks if v > 0)
    if s <= 0 or tot <= 0 or n_live == 0:
        C["pts"] = None
        return
    pts = [(0.0, PAYOUTS[n_live - 1] if n_live - 1 < len(PAYOUTS) else 0.0)]
    if tot > s:
        for mult in (0.5, 1.0, 2.0):
            x = s * mult
            if x >= tot:
                break
            scale = (tot - x) / (tot - s)
            st = [x if i == me else (v * scale if v > 0 else 0.0) for i, v in enumerate(stacks)]
            pts.append((x, icm_value(st, me)))
    pts.append((tot, PAYOUTS[0]))
    C["pts"] = pts


def V(x: float) -> float:
    pts = C["pts"]
    if x <= pts[0][0]:
        return pts[0][1]
    for i in range(1, len(pts)):
        x1, v1 = pts[i]
        if x <= x1:
            x0, v0 = pts[i - 1]
            return v0 + (v1 - v0) * (x - x0) / (x1 - x0) if x1 > x0 else v1
    return pts[-1][1]


def icm_gate(stack: float, win: float, risk: float, e: float) -> bool:
    """True when the all-in call / re-shove is +ICM (chip EV when no curve exists yet)."""
    if C["pts"] is None:
        return e * win > (1.0 - e) * risk
    return e * V(stack + win) + (1.0 - e) * V(stack - risk) > V(stack) + 1e-6


# ----------------------------------------------------------------------------- step 3b: push rule
def push_rule(hc: tuple, eff_chips: float, bb: float, opp_flags: list) -> bool:
    """Spec 3b: p = prod(1 - c) over the seats behind (c = 0.12, 0.20 maniac, 0.08 nit), e = equity versus a
    top-12 % caller; push when p*V(S + blinds) + (1 - p)*(e*V(2S + blinds) + (1 - e)*V(0)) > V(S + 0.1 bb)."""
    if C["pts"] is None:
        return False
    p = 1.0
    for fl in opp_flags:
        p *= 1.0 - (0.20 if fl[2] else (0.08 if fl[3] else 0.12))
    e = EQT.get(hc, 0.3)
    blinds = 1.5 * bb
    ev = p * V(eff_chips + blinds) + (1.0 - p) * (e * V(2.0 * eff_chips + blinds) + (1.0 - e) * V(0.0))
    return ev > V(eff_chips + 0.1 * bb)


def _sanity_3b() -> bool:
    """22 from the button at 10 bb pushes; 72o from early at 12 bb does not (8 equal stacks)."""
    saved = C["pts"]
    try:
        build_curve([1000] * 8, 0)
        a = push_rule((0, 0, False), 1000.0, 100.0, [(False,) * 4] * 2)
        build_curve([1200] * 8, 0)
        b = push_rule((5, 0, False), 1200.0, 100.0, [(False,) * 4] * 7)
        return a and not b
    except Exception:  # noqa: BLE001
        return False
    finally:
        C["pts"] = saved


USE_3B = _sanity_3b()


# ----------------------------------------------------------------------------- made hands and draws
def _straight(mask: int) -> bool:
    if mask & _WHEEL == _WHEEL:
        return True
    for i in range(9):
        if (mask >> i) & 31 == 31:
            return True
    return False


def made_category(hole, board) -> int:
    """0 nothing/underpair-ish, 1 pair below top, 2 top pair or overpair, 3 two pair, 4 trips, 5 straight,
    6 flush, 7 full house, 8 quads, 9 straight flush. Counting ranks and suits only."""
    cards = tuple(hole) + tuple(board)
    cnt: dict = {}
    scnt = [0, 0, 0, 0]
    smask = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        r, s = c >> 2, c & 3
        cnt[r] = cnt.get(r, 0) + 1
        scnt[s] += 1
        smask[s] |= 1 << r
        mask |= 1 << r
    groups = sorted(cnt.values(), reverse=True)
    flush = max(scnt) >= 5
    if flush and _straight(smask[scnt.index(max(scnt))]):
        return 9
    if groups[0] == 4:
        return 8
    if groups[0] == 3 and len(groups) > 1 and groups[1] >= 2:
        return 7
    if flush:
        return 6
    if _straight(mask):
        return 5
    if groups[0] == 3:
        return 4
    if groups[0] == 2 and len(groups) > 1 and groups[1] == 2:
        return 3
    br = [c >> 2 for c in board]
    top = max(br) if br else -1
    h0, h1 = hole[0] >> 2, hole[1] >> 2
    if h0 == h1:
        return 2 if h0 > top else 1
    if h0 == top or h1 == top:
        return 2
    if h0 in br or h1 in br:
        return 1
    return 0


def top_pair_kicker(hole, board) -> int:
    """Kicker strength for a top pair (the unpaired hole card), 12 for an overpair."""
    br = [c >> 2 for c in board]
    top = max(br)
    h0, h1 = hole[0] >> 2, hole[1] >> 2
    if h0 == h1:
        return 12
    return h1 if h0 == top else h0


def outs(hole, board) -> int:
    """9 for a flush draw, 8 for an open-ended straight draw; flop and turn only."""
    if len(board) not in (3, 4):
        return 0
    cards = tuple(hole) + tuple(board)
    scnt = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        scnt[c & 3] += 1
        mask |= 1 << (c >> 2)
    if max(scnt) == 4:
        return 9
    if _straight(mask):
        return 0
    for i in range(1, 9):  # four in a row with both ends open: i-1 >= 0 and i+4 <= 12
        if (mask >> i) & 15 == 15:
            return 8
    return 0


# ----------------------------------------------------------------------------- step 2: profiler (kit B: snapshot diffs)
# counters per seat: [hands, vpip, pfr, faced, folded, shoved, acts, raises, free_checks]
HANDS, VPIP, PFR, FACED, FOLDED, SHOVED, ACTS, RAISES, CHECKS = range(9)
P: dict = {}
H = {"hand": None, "street": -1, "snap": {}, "cur": 0, "seen": set(), "flags": {}}
S = {"seat": None, "n": 0, "stack0": 2000, "total": 16000, "est": [], "hand_start": None, "hand_start_id": None}


def on_table_start(info: dict) -> None:
    S["seat"] = info.get("seat")
    S["n"] = int(info.get("players", 8) or 8)
    S["stack0"] = int(info.get("stack", 2000) or 2000)
    S["total"] = S["n"] * S["stack0"]
    S["est"] = [S["stack0"]] * S["n"]
    S["hand_start"] = None
    S["hand_start_id"] = None
    P.clear()
    H.update(hand=None, street=-1, snap={}, cur=0, seen=set(), flags={})
    try:
        build_curve(S["est"], S["seat"] if S["seat"] is not None else 0)
    except Exception:  # noqa: BLE001
        C["pts"] = None


def on_hand_end(info: dict) -> None:
    """Untimed: rebuild the ICM curve from my new stack and the opponents' last-seen chips, scaled."""
    try:
        me = S["seat"]
        if me is None or not S["est"]:
            return
        delta = int(info.get("delta", 0) or 0)
        base = S["hand_start"] if S.get("hand_start_id") == info.get("hand_id") and S["hand_start"] is not None \
            else S["est"][me]
        mine = max(0, base + delta)
        est = list(S["est"])
        others = sum(v for i, v in enumerate(est) if i != me)
        target = S["total"] - mine
        if others > 0 and target >= 0:
            scale = target / others
            est = [mine if i == me else v * scale for i, v in enumerate(est)]
        else:
            est[me] = mine
        S["est"] = est
        build_curve(est, me)
    except Exception:  # noqa: BLE001
        C["pts"] = None


def _tick(s: int, i: int) -> None:
    key = (s, i)
    if key in H["seen"]:
        return
    H["seen"].add(key)
    P[s][i] += 1


def flags_for(s: int) -> tuple:
    """(dead, station, maniac, nit) with the kit-A floors doubled (no history at all in kit B)."""
    c = P.get(s)
    if c is None:
        return (False, False, False, False)
    h, v, pf, fa, fo, sh, ac, ra, ch = c
    dead = fa >= 10 and fo == fa and ch >= 1 and ra == 0
    station = fa >= 20 and (fo + 1.0) / (fa + 2.0) < 0.15
    maniac = ac >= 20 and ra / ac > 0.5
    nit = h >= 40 and (v + 0.6) / (h + 2.0) < 0.12
    return (dead, station, maniac, nit)


def rates(s: int) -> dict:
    """Beta-prior rates (2 pseudo-observations at the population rate)."""
    h, v, pf, fa, fo, sh, ac, ra, ch = P.get(s, [0] * 9)
    return {"vpip": (v + 0.6) / (h + 2.0), "pfr": (pf + 0.3) / (h + 2.0), "fold_to_bet": (fo + 1.0) / (fa + 2.0),
            "shove": (sh + 0.1) / (h + 2.0), "raise_rate": (ra / ac) if ac else 0.0}


def _observe(obs: dict, t: dict) -> None:
    """Update counters from the diff between this observation and the previous one (same hand)."""
    hid = obs["hand_id"]
    street = obs["street"]
    me = t["me"]
    players = t["players"]
    bb = t["bb"]
    new_hand = hid != H["hand"]
    # stack estimates for the ICM curve, every decision
    if S["est"] and len(S["est"]) >= t["n"]:
        for s in t["dealt"]:
            S["est"][s] = players[s]["chips"] + players[s]["committed"]
        for s in range(t["n"]):
            if s not in t["players"] or (s not in t["dealt"]):
                S["est"][s] = 0
    if new_hand:
        S["hand_start"] = t["my_stack"]
        S["hand_start_id"] = hid
        H["hand"] = hid
        H["street"] = street
        H["seen"] = set()
        sbs, bbs = t["sb"], t["bb_seat"]
        snap = {}
        for s in t["dealt"]:
            if s not in P:
                P[s] = [0] * 9
            base = 0
            if s == sbs:
                base = obs["blinds"]["sb"]
            elif s == bbs:
                base = bb
            snap[s] = (base, True)
            if s != me:
                P[s][HANDS] += 1
        H["snap"] = snap
        H["cur"] = bb if street == 0 else 0
    elif street != H["street"]:
        # a seat that went inactive across the street boundary folded facing the previous street's last bet
        old, oldcur, oldstreet = H["snap"], H["cur"], H["street"]
        for s in t["dealt"]:
            if s == me:
                continue
            pc, pa = old.get(s, (0, True))
            if pa and not players[s]["active"]:
                _tick(s, ACTS)
                if oldcur > pc and (oldstreet > 0 or oldcur > bb) and (s, FACED) not in H["seen"]:
                    _tick(s, FACED)
                    _tick(s, FOLDED)
        H["street"] = street
        H["snap"] = {s: (0, players[s]["active"]) for s in old}
        H["cur"] = 0
    cur_before = H["cur"]
    snap = H["snap"]
    new_max = max(players[s]["committed"] for s in t["dealt"]) if t["dealt"] else 0
    if street > 0 and cur_before == 0:
        first = t["first_post"]
        order = [(first + i) % t["n"] for i in range(t["n"])]
        before_me = set(order[:order.index(me)]) if me in order else set()
    else:
        before_me = set()
    for s in t["dealt"]:
        if s == me:
            continue
        pc, pa = snap.get(s, (0, True))
        p = players[s]
        c, a = p["committed"], p["active"]
        if pa and not a:
            _tick(s, ACTS)
            if cur_before > pc and (street > 0 or cur_before > bb) and (s, FACED) not in H["seen"]:
                _tick(s, FACED)
                _tick(s, FOLDED)
        elif c > pc:
            _tick(s, ACTS)
            if street == 0:
                _tick(s, VPIP)
            if c > cur_before and c == new_max:
                _tick(s, RAISES)
                if street == 0:
                    _tick(s, PFR)
                if p["chips"] == 0:
                    _tick(s, SHOVED)
            else:
                _tick(s, FACED)
        elif a and s in before_me and c == 0:
            _tick(s, CHECKS)
    H["snap"] = {s: (players[s]["committed"], players[s]["active"]) for s in t["dealt"]}
    H["cur"] = new_max
    # step 2b: every seat's flags once per hand, at my first decision of it; later decisions read the dict
    if new_hand:
        H["flags"] = {s: flags_for(s) for s in t["dealt"] if s != me}


def _read(obs: dict) -> dict:
    """Everything the decision needs, in one pass over the observation."""
    me = obs["you"]["seat"]
    btn = obs["table"]["button"]
    players = {p["seat"]: p for p in obs["table"]["players"]}
    n = max(players) + 1
    dealt = [s for s in range(n) if s in players and
             (players[s]["active"] or players[s]["committed"] > 0 or players[s]["chips"] > 0)]
    dset = set(dealt)
    committed = {s: players[s]["committed"] for s in players}
    current = max(committed.values()) if committed else 0
    bb = obs["blinds"]["bb"]

    def nxt(s):
        for i in range(1, n + 1):
            u = (s + i) % n
            if u in dset:
                return u
        return s
    sb = btn if len(dealt) == 2 else nxt(btn)
    bbs = nxt(sb)
    k = 0
    if me != btn:
        s = me
        for _ in range(n):
            s = (s + 1) % n
            if s in dset:
                k += 1
            if s == btn:
                break
    active_opp = [s for s in dealt if s != me and players[s]["active"]]
    my_stack = players[me]["chips"] + committed[me]
    opp_max = max((players[s]["chips"] + committed[s] for s in active_opp), default=0)
    eff_bb = min(my_stack, opp_max) / bb if bb else 999.0
    raiser = None
    if current > bb or (obs["street"] > 0 and current > 0):
        cands = [s for s in active_opp if committed[s] == current]
        raiser = cands[0] if cands else None
    return dict(me=me, btn=btn, players=players, n=n, dealt=dealt, sb=sb, bb_seat=bbs, k=k, bb=bb,
                committed=committed, current=current, active_opp=active_opp, my_stack=my_stack,
                eff_bb=eff_bb, raiser=raiser, to_call=obs["you"]["to_call"], first_post=nxt(btn))


def _all_flag(t: dict, i: int) -> bool:
    fl = H["flags"]
    opps = t["active_opp"]
    return bool(opps) and all(fl.get(s, (False,) * 4)[i] for s in opps)


OPEN_PCT = (0.15, 0.25, 0.40)      # early, middle, late
PUSH_8_12 = (0.25, 0.35, 0.45)


def _bucket(t: dict, folded_to: bool) -> int:
    """0 early, 1 middle, 2 late."""
    me = t["me"]
    if me == t["bb_seat"]:
        return 0
    if me == t["sb"]:
        return 1 if folded_to else 0
    k = t["k"]
    return 2 if k <= 1 else (1 if k <= 3 else 0)


def _preflop(obs: dict, t: dict, hc: tuple) -> tuple:
    bb, cur, me = t["bb"], t["current"], t["me"]
    to_call = t["to_call"]
    raised = cur > bb
    pct = PCT.get(hc, 1.0)
    shove = False
    raiser_nit = False
    raiser_maniac = False
    if raised and t["raiser"] is not None:
        r = t["raiser"]
        p = t["players"][r]
        shove = p["chips"] == 0 or cur >= 10 * bb
        fl = H["flags"].get(r, (False,) * 4)
        raiser_nit, raiser_maniac = fl[3], fl[2]
    limpers = sum(1 for s in t["active_opp"] if t["committed"][s] == cur and s != t["bb_seat"]) if not raised else 0
    folded_to = not raised and all(s in (t["sb"], t["bb_seat"]) for s in t["active_opp"])
    bucket = _bucket(t, folded_to)
    open_by = int(2.5 * bb + limpers * bb) - cur
    eff = t["eff_bb"]
    stack = float(t["my_stack"])
    my_c = t["committed"][me]
    win = obs["table"]["pot"] + sum(v for s, v in t["committed"].items() if s != me)
    n_in = sum(1 for s in t["active_opp"] if t["committed"][s] > bb or t["players"][s]["chips"] == 0)
    # exploits that act before the charts
    if not raised and _all_flag(t, 0):  # every opponent left is dead: raise any two
        return "raise", open_by
    if not raised and limpers == 0 and bucket == 2 and _all_flag(t, 3):  # nit blinds: steal any two
        return "raise", open_by
    if raised and raiser_nit and not is_qq_ak(hc):  # fold to a nit's raise without QQ+/AK
        return "fold", 0
    if not raised:
        if eff >= 12:
            thr = OPEN_PCT[bucket]
            if pct < thr:
                return "raise", open_by
            return ("check", 0) if to_call == 0 else ("fold", 0)
        if USE_3B and C["pts"] is not None:  # step 3b: the push rule from the equity table
            opp_flags = [H["flags"].get(s, (False,) * 4) for s in t["active_opp"]]
            if push_rule(hc, eff * bb, float(bb), opp_flags):
                return "raise", obs["you"]["max_raise_by"]
            return ("check", 0) if to_call == 0 else ("fold", 0)
        thr = 0.60 if eff < 5 else (0.40 if eff < 8 else PUSH_8_12[bucket])
        if pct < thr:
            return "raise", obs["you"]["max_raise_by"]  # open shove: never gated
        return ("check", 0) if to_call == 0 else ("fold", 0)
    if not shove:
        one_raise = sum(1 for s in t["active_opp"] if t["committed"][s] > bb) == 1
        if eff >= 12:
            if is_qq_ak(hc):
                return "raise", 2 * cur  # raise-to 3x the raise = by 2x
            if is_premium(hc):
                return "call", 0
            if me == t["bb_seat"] and one_raise and pct < 0.35:
                return "call", 0
            return "fold", 0
        if is_premium(hc):  # re-shove over a raise: gated, risk = my stack
            if icm_gate(stack, win, stack, EQ1.get(hc, 0.5)):
                return "raise", obs["you"]["max_raise_by"]
        return "fold", 0
    # facing a shove: top 12 (20 against a flagged maniac), then the ICM gate
    thr = 0.20 if raiser_maniac else 0.12
    if pct < thr:
        e = EQ1.get(hc, 0.5) if n_in <= 1 else EQ3.get(hc, 0.25)
        if icm_gate(stack, win, float(to_call + my_c), e):
            return "call", 0
    return "fold", 0


def _postflop(obs: dict, t: dict, hole, board) -> tuple:
    cat = made_category(hole, board)
    pot_prev = obs["table"]["pot"]
    to_call = t["to_call"]
    if to_call == 0:
        if _all_flag(t, 0):  # dead seats: bet every street when checked to
            return "raise", max(int(0.6 * pot_prev), 1)
        if _all_flag(t, 1):  # stations: 75 % with top pair kicker T+ or better; medium waits for the river
            if cat >= 3 or (cat == 2 and top_pair_kicker(hole, board) >= 8):
                return "raise", int(0.75 * pot_prev)
            if cat == 2:
                return ("raise", int(0.75 * pot_prev)) if len(board) == 5 else ("check", 0)
            return "check", 0
        if cat >= 2:
            return "raise", int(0.6 * pot_prev)
        return "check", 0
    if cat >= 2:  # top pair or better calls any size (maniac: call down with top pair, never fold an overpair)
        return "call", 0
    pot_now = pot_prev + sum(t["committed"].values())
    if outs(hole, board) >= 8 and to_call * 3 < pot_now:
        return "call", 0
    return "fold", 0


def _decide(obs: dict) -> tuple:
    hole = parse_cards(obs["hand"]["cards"])
    board = parse_cards(obs["table"]["board"])
    t = _read(obs)
    try:
        _observe(obs, t)
    except Exception:  # noqa: BLE001 - the profiler must never cost a decision
        pass
    if obs["street"] == 0 and not board:
        return _preflop(obs, t, hand_class(hole))
    return _postflop(obs, t, hole, board)


def _safe(obs) -> dict:
    try:
        return {"action": "check"} if "check" in obs["actions"] else {"action": "fold"}
    except Exception:  # noqa: BLE001
        return {"action": "fold"}


def _legalize(kind: str, by: int, obs: dict) -> dict:
    acts = obs["actions"]
    if kind == "raise":
        if "raise" in acts:
            lo, hi = obs["you"]["min_raise_by"], obs["you"]["max_raise_by"]
            return {"action": "raise", "by": int(max(lo, min(hi, int(by))))}
        kind = "call"
    if kind == "call":
        if "call" in acts:
            return {"action": "call"}
        return _safe(obs)
    if kind == "check":
        return {"action": "check"} if "check" in acts else _safe(obs)
    return {"action": "fold"} if "fold" in acts else _safe(obs)


def decide(obs: dict) -> dict:
    try:
        kind, by = _decide(obs)
        out = _legalize(kind, by, obs)
        if out["action"] == "raise":
            H["cur"] += out["by"]  # my own raise is the bet the others now face
        return out
    except Exception:  # noqa: BLE001
        return _safe(obs)
