# Origin: the climb's outside field (docs/drills/field/outside_lag.md is the builder's log). A fresh coding agent,
# playing three online-poker grinders playing loose-aggressive (steals, light 3-bets, wide re-shoves),
# built it in one hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# 7f2cf88729b2db29a6d7d4c425843cce (its FROZEN.md5) and copied here unchanged apart from this header. The archive is docs/drills/field/outside_lag_bot.py.
# Played through hyperion.sim.bestiary.Outside*Bot (registry name `out_lag`); a judge-like field, never tuned on.
# Do not edit; a new bot is a new file.
"""rival_bot: loose-aggressive SNG bot. Pure stdlib, table lookups + heuristics, no Monte Carlo.

Preflop: combo-weighted hand percentile table built at import; LAG open/steal ranges by seats
behind, Nash-flavoured push/fold <= 13bb, re-shove 13-28bb over opens, light 3-bets deeper.
Postflop: category-based made-hand strength + draw equity; c-bet/barrel when checked to,
value-bet/raise strong hands, price-based calls with a deep-stack big-bet brake.
"""
import random

try:
    from kit import Agent
except Exception:  # pragma: no cover
    class Agent(object):
        def new_table(self, rules, seat, n_players):
            pass

        def act(self, obs):
            raise NotImplementedError

        def hand_end(self, result):
            pass


# ---------------------------------------------------------------- preflop table
def _pf_eq(hi, lo, suited):
    if hi == lo:
        return 0.503 + 0.029 * hi
    e = 0.295 + 0.0205 * hi + 0.0095 * lo
    if suited:
        e += 0.032
    gap = hi - lo - 1
    pen = (0.0, 0.006, 0.015, 0.025, 0.035)[gap if gap < 4 else 4]
    if hi == 12:
        e += 0.02
        pen *= 0.3
    return e - pen


def _build_pct():
    hands = []
    for hi in range(13):
        for lo in range(hi + 1):
            if hi == lo:
                hands.append((_pf_eq(hi, lo, False), 6, (hi, lo, False)))
            else:
                hands.append((_pf_eq(hi, lo, True), 4, (hi, lo, True)))
                hands.append((_pf_eq(hi, lo, False), 12, (hi, lo, False)))
    hands.sort(key=lambda x: -x[0])
    pct = {}
    eq = {}
    cum = 0
    for e, n, k in hands:
        cum += n
        pct[k] = cum / 1326.0
        eq[k] = e
    return pct, eq


PCT, PFEQ = _build_pct()

# tuning knobs
K_OPEN = 1.15
K_OPEN_LATE = 1.25
K_PUSH = 1.45
K_STEALADJ = 1.5
K_BLUFF = 1.0
K_CALL = 0.03
K_RESHOVE = 1.6
K_LIGHT3 = 0.25
K_VALUE = 0.0
K_AIM = 0.4
K_JAM = 0.3
K_SHORT = 0.35
K_PREM = 0.0095
K_RISK = 1.5
K_PRISK = 0.0
K_COVER = 1.25
K_PUSHBB = 13.0
K_BEHIND = 1.0
K_OSIZE = 1.0
K_AIMN = 0.0
K_AIMFLOOR = 0.2

# open percentile by number of players still to act behind (incl. blinds)
OPEN_PCT = {0: 0.0, 1: 0.62, 2: 0.52, 3: 0.36, 4: 0.27, 5: 0.22, 6: 0.19, 7: 0.17}
# push percentile at 10bb by players behind
PUSH10 = {0: 0.0, 1: 0.66, 2: 0.46, 3: 0.35, 4: 0.28, 5: 0.23, 6: 0.20, 7: 0.18}


def _hole_key(hole):
    r1, r2 = hole[0] >> 2, hole[1] >> 2
    s = (hole[0] & 3) == (hole[1] & 3)
    if r1 >= r2:
        return (r1, r2, s and r1 != r2)
    return (r2, r1, s)


# all-in equity of a hand at percentile p (rows: range width w) -- my own Monte Carlo, smoothed
_EQ_P = (0.005, 0.02, 0.05, 0.1, 0.2, 0.35, 0.5, 0.75, 1.0)
_EQ_W = (0.03, 0.08, 0.15, 0.3, 0.5, 1.0)
_EQ_G = ((0.685, 0.417, 0.38, 0.286, 0.275, 0.244, 0.197, 0.176, 0.13), (0.723, 0.577, 0.46, 0.365, 0.31, 0.28, 0.28, 0.261, 0.226), (0.735, 0.605, 0.577, 0.449, 0.365, 0.319, 0.319, 0.319, 0.286), (0.751, 0.66, 0.635, 0.52, 0.436, 0.364, 0.364, 0.364, 0.296), (0.808, 0.728, 0.65, 0.581, 0.476, 0.41, 0.41, 0.364, 0.3), (0.835, 0.748, 0.672, 0.63, 0.566, 0.542, 0.494, 0.415, 0.313))


def _eq_vs_range(p, w):
    """All-in equity of a hand at percentile p versus the top-w range (bilinear lookup)."""
    P, W, G = _EQ_P, _EQ_W, _EQ_G
    if p < P[0]:
        p = P[0]
    if p > 1.0:
        p = 1.0
    if w < W[0]:
        w = W[0]
    if w > 1.0:
        w = 1.0
    i = 0
    while i < len(P) - 2 and P[i + 1] < p:
        i += 1
    j = 0
    while j < len(W) - 2 and W[j + 1] < w:
        j += 1
    fp = (p - P[i]) / (P[i + 1] - P[i])
    fw = (w - W[j]) / (W[j + 1] - W[j])
    a = G[j][i] + (G[j][i + 1] - G[j][i]) * fp
    b = G[j + 1][i] + (G[j + 1][i + 1] - G[j + 1][i]) * fp
    return a + (b - a) * fw


# ---------------------------------------------------------------- hand evaluation
def _straight_high(mask):
    for top in range(12, 3, -1):
        if (mask >> (top - 4)) & 31 == 31:
            return top
    if mask & 0x100F == 0x100F:
        return 3
    return -1


def _cat(cards):
    """Return (category, primary rank) for best hand among cards. 0 high .. 8 straight flush."""
    rc = [0] * 13
    sc = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        r = c >> 2
        rc[r] += 1
        sc[c & 3] += 1
        mask |= 1 << r
    fs = -1
    for s in range(4):
        if sc[s] >= 5:
            fs = s
    if fs >= 0:
        fm = 0
        for c in cards:
            if c & 3 == fs:
                fm |= 1 << (c >> 2)
        sh = _straight_high(fm)
        if sh >= 0:
            return 8, sh
    quad = trip = -1
    pairs = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 4:
            quad = r
        elif n == 3:
            if trip < 0:
                trip = r
            else:
                pairs.append(r)
        elif n == 2:
            pairs.append(r)
    if quad >= 0:
        return 7, quad
    if trip >= 0 and pairs:
        return 6, trip
    if fs >= 0:
        return 5, 0
    sh = _straight_high(mask)
    if sh >= 0:
        return 4, sh
    if trip >= 0:
        return 3, trip
    if len(pairs) >= 2:
        return 2, pairs[0]
    if pairs:
        return 1, pairs[0]
    return 0, max(r for r in range(13) if rc[r])


def _analyze(hole, board):
    """Heuristic made-hand strength in [0,1] and draw equity for the remaining cards."""
    h1, h2 = hole[0] >> 2, hole[1] >> 2
    hr = (h1, h2)
    allc = list(hole) + list(board)
    cat, prim = _cat(allc)
    bcat, bprim = _cat(board)
    brs = sorted((c >> 2 for c in board), reverse=True)
    top = brs[0]
    bsuit = [0, 0, 0, 0]
    for c in board:
        bsuit[c & 3] += 1
    maxsuit = max(bsuit)
    bmask = 0
    for r in brs:
        bmask |= 1 << r
    paired_board = len(set(brs)) < len(brs)
    s = 0.1
    if cat >= 7:
        s = 0.99 if bcat < cat else 0.5
    elif cat == 6:
        if bcat == 6:
            s = 0.45
        elif bcat == 3 and prim == bprim and h1 not in brs and h2 not in brs and h1 != h2:
            s = 0.75  # board trips + our pair
        else:
            s = 0.95
    elif cat == 5:
        # flush: best hole card of the flush suit
        fsuit = -1
        sc = [0, 0, 0, 0]
        for c in allc:
            sc[c & 3] += 1
        for q in range(4):
            if sc[q] >= 5:
                fsuit = q
        hf = [c >> 2 for c in hole if c & 3 == fsuit]
        if not hf:
            s = 0.4
        else:
            hb = max(hf)
            higher_missing = 0
            for r in range(hb + 1, 13):
                if not any((c >> 2) == r and (c & 3) == fsuit for c in board):
                    higher_missing += 1
            s = 0.95 - 0.035 * higher_missing
            if bsuit[fsuit] >= 4 and len(hf) == 1:
                s -= 0.08
            if paired_board:
                s -= 0.08
    elif cat == 4:
        if bcat == 4:
            s = 0.4
        else:
            s = 0.84
            if maxsuit >= 3:
                s -= 0.12
            if paired_board:
                s -= 0.06
    elif cat == 3:
        if bcat == 3:
            s = 0.2 + 0.015 * max(h1, h2)
        elif h1 == h2:
            s = 0.9  # set
        else:
            k = h2 if h1 == prim else h1
            s = 0.76 + 0.006 * k
        if maxsuit >= 3:
            s -= 0.07
    elif cat == 2:
        hole_pairs = (h1 in brs) + (h2 in brs)
        if h1 == h2:
            # pocket pair plus board pair
            if h1 > top:
                s = 0.7
            else:
                s = 0.4
        elif hole_pairs == 2:
            s = 0.8 if not paired_board else 0.6
        elif hole_pairs == 1:
            pr = h1 if h1 in brs else h2
            if pr == top:
                s = 0.58
            else:
                s = 0.42
        else:
            s = 0.15 + 0.01 * max(h1, h2)
        if maxsuit >= 3 and s > 0.5:
            s -= 0.06
    elif cat == 1:
        if bcat == 1:
            s = 0.12 + 0.012 * max(h1, h2)
        elif h1 == h2:
            if h1 > top:
                s = 0.7 + 0.012 * (h1 - 8)
            elif h1 > brs[1] if len(brs) > 1 else False:
                s = 0.42
            else:
                s = 0.3
        else:
            pr = h1 if h1 in brs else h2
            kick = h2 if pr == h1 else h1
            if pr == top:
                s = 0.54 + 0.008 * kick
            elif len(brs) > 1 and pr == brs[1]:
                s = 0.4 + 0.004 * kick
            else:
                s = 0.3
        if maxsuit >= 3:
            s -= 0.05
    else:
        s = 0.04 + 0.012 * max(h1, h2)
    # draws
    draw = 0.0
    street = len(board)
    if street < 5:
        mult = 0.039 if street == 3 else 0.022
        outs = 0
        fd = False
        for q in range(4):
            if bsuit[q] + ((hole[0] & 3) == q) + ((hole[1] & 3) == q) == 4 and bsuit[q] < 4:
                fd = True
        if fd and cat < 5:
            outs += 9
        if cat < 4:
            m = bmask | (1 << h1) | (1 << h2)
            comp = 0
            for r in range(13):
                if m >> r & 1:
                    continue
                if _straight_high(m | (1 << r)) >= 0 and _straight_high(bmask | (1 << r)) < 0:
                    comp += 1
            if comp >= 2:
                outs += 8 if not fd else 6
            elif comp == 1:
                outs += 4 if not fd else 3
        if cat == 0 and street == 3:
            over = (h1 > top) + (h2 > top)
            outs += 3 * over
        draw = outs * mult
        if draw > 0.55:
            draw = 0.55
    return s, draw, cat


# ---------------------------------------------------------------- bot
class Bot(Agent):
    def __init__(self):
        self.rng = random.Random(0x1A6)
        self.new_table({}, 0, 8)

    def new_table(self, rules, seat, n_players):
        self.n = n_players or 8
        self.acts = {}
        self.raises = {}
        self.folds = {}
        self.calls = {}
        self.pfh = {}
        self.pfr = {}
        self.cur_hand = None
        self.hidx = 0
        self.my_last = {}
        self.pf_seen = set()
        self.pf_raised = set()

    def hand_end(self, result):
        pass

    # ---- opponent stats
    def _track(self, obs):
        hn = obs.hand_no
        if hn != self.cur_hand:
            self.cur_hand = hn
            self.hidx = 0
            self.my_last = {}
            self.pf_seen = set()
            self.pf_raised = set()
        hist = obs.history or ()
        bb = obs.blinds[1] if obs.blinds else 0
        i = self.hidx
        L = len(hist)
        while i < L:
            try:
                st, a = hist[i]
                kind = a[0]
                amt = a[1] if len(a) > 1 else 0
            except Exception:
                i += 1
                continue
            if st != obs.seat:
                if obs.street == 0 and kind == 'raise' and amt <= bb:
                    i += 1
                    continue  # blind post
                self.acts[st] = self.acts.get(st, 0) + 1
                if kind == 'fold':
                    self.folds[st] = self.folds.get(st, 0) + 1
                elif kind == 'call':
                    self.calls[st] = self.calls.get(st, 0) + 1
                if kind == 'raise':
                    self.raises[st] = self.raises.get(st, 0) + 1
                if obs.street == 0:
                    if st not in self.pf_seen:
                        self.pf_seen.add(st)
                        self.pfh[st] = self.pfh.get(st, 0) + 1
                    if kind == 'raise' and st not in self.pf_raised:
                        self.pf_raised.add(st)
                        self.pfr[st] = self.pfr.get(st, 0) + 1
            i += 1
        self.hidx = L

    def _foldr(self, s):
        f = self.folds.get(s, 0)
        return (f + 2.0) / (f + self.calls.get(s, 0) + self.raises.get(s, 0) + 4.0)

    def _agg(self, s):
        return (self.raises.get(s, 0) + 1.0) / (self.acts.get(s, 0) + 6.0)

    def _pfr(self, s):
        return (self.pfr.get(s, 0) + 1.0) / (self.pfh.get(s, 0) + 7.0)

    # ---- action helpers
    @staticmethod
    def _raise(obs, amt):
        if 'raise' in obs.legal:
            a = int(amt)
            if a < obs.min_raise:
                a = obs.min_raise
            if a > obs.max_raise:
                a = obs.max_raise
            if a >= 0.85 * obs.max_raise:
                a = obs.max_raise
            return ('raise', int(a))
        if 'call' in obs.legal:
            return ('call', 0)
        return ('check', 0)

    @staticmethod
    def _shove(obs):
        if 'raise' in obs.legal:
            return ('raise', int(obs.max_raise))
        if 'call' in obs.legal:
            return ('call', 0)
        return ('check', 0)

    @staticmethod
    def _call(obs):
        if 'call' in obs.legal:
            return ('call', 0)
        return ('check', 0)

    @staticmethod
    def _fold(obs):
        if 'check' in obs.legal:
            return ('check', 0)
        return ('fold', 0)

    def act(self, obs):
        try:
            a = self._act(obs)
        except Exception:
            a = None
        if not a or a[0] not in obs.legal:
            if 'check' in obs.legal:
                a = ('check', 0)
            elif 'call' in obs.legal and obs.to_call <= max(1, obs.blinds[1] if obs.blinds else 1):
                a = ('call', 0)
            else:
                a = ('fold', 0) if 'fold' in obs.legal else (sorted(obs.legal)[0], 0)
        if a[0] == 'raise':
            amt = a[1]
            if not isinstance(amt, int):
                amt = int(amt)
            if amt < obs.min_raise:
                amt = obs.min_raise
            if amt > obs.max_raise:
                amt = obs.max_raise
            a = ('raise', amt)
        else:
            a = (a[0], 0)
        self.my_last[obs.street] = a[0]
        return a

    def _act(self, obs):
        self._track(obs)
        if obs.street == 0:
            return self._preflop(obs)
        return self._postflop(obs)

    # ---- table geometry
    def _geometry(self, obs):
        n = len(obs.stacks)
        dealt = [i for i in range(n) if obs.in_hand[i] or obs.stacks[i] > 0 or obs.bets[i] > 0]
        btn = obs.button
        L = []
        for k in range(1, n + 1):
            s = (btn + k) % n
            if s in dealt:
                L.append(s)
        if len(L) == 2:
            pre = [btn, L[0] if L[0] != btn else L[1]]
            post = [pre[1], pre[0]]
        else:
            pre = L[2:] + L[:2]
            post = L
        return pre, post

    # ---- preflop
    def _preflop(self, obs):
        bb = obs.blinds[1] or 1
        me = obs.seat
        stacks, bets = obs.stacks, obs.bets
        my_total = stacks[me] + bets[me]
        key = _hole_key(obs.hole)
        p = PCT[key]
        pre, post = self._geometry(obs)
        idx = pre.index(me) if me in pre else len(pre) - 1
        after = len(pre) - 1 - idx
        n_left = len(pre)
        others = [i for i in range(len(stacks)) if i != me and obs.in_hand[i]]
        if not others:
            return self._fold(obs)
        max_other = max(stacks[i] + bets[i] for i in others)
        eff = min(my_total, max_other)
        eff_bb = eff / float(bb)
        max_bet = max(bets)
        to_call = obs.to_call
        pot_total = obs.pot + sum(bets)
        nraise = 0
        for st, a in (obs.history or ()):
            try:
                if st != me and a[0] == 'raise' and a[1] > bb:
                    nraise += 1
            except Exception:
                pass
        if max_bet > bb and nraise == 0:
            nraise = 1
        # ICM context
        alive = [i for i in range(len(stacks)) if stacks[i] > 0 or obs.in_hand[i]]
        n_alive = len(alive)
        totals = sorted((stacks[i] + bets[i] for i in alive), reverse=True)
        late = n_alive <= 4 or obs.hand_no >= 150
        covers = all(my_total >= stacks[i] + bets[i] for i in others)
        widen = 1.0
        if late and covers:
            widen = K_COVER
        icm_margin = 0.015
        if late and not covers:
            icm_margin = 0.04
            if n_alive >= 3 and my_total < totals[0] and my_total > totals[-1] * 1.3:
                icm_margin = 0.06
        rng = self.rng

        if max_bet <= bb and nraise == 0:
            behind = pre[idx + 1:]
            if late and K_BEHIND and behind and widen < K_COVER and all(
                    my_total >= stacks[x] + bets[x] for x in behind):
                widen = K_COVER
            if behind and K_STEALADJ:
                fr = sum(self._foldr(x) for x in behind) / len(behind)
                widen *= 1.0 + max(-0.35, min(0.35, (fr - 0.4) * K_STEALADJ))
            if after <= 3:
                widen *= K_OPEN_LATE
            limpers = sum(1 for i in others if bets[i] >= bb and i != (pre[-1] if n_left > 2 else -1))
            if n_left > 2 and me == pre[-1]:
                pass
            # BB option
            if to_call == 0:
                if limpers and p <= 0.13 and eff_bb > K_PUSHBB:
                    return self._raise(obs, bets[me] + bb * (3 + limpers))
                if limpers and eff_bb <= K_PUSHBB and p <= 0.10:
                    return self._shove(obs)
                return ('check', 0)
            if eff_bb <= K_PUSHBB:
                thr = PUSH10.get(after, 0.18) * (10.0 / max(eff_bb, 2.0)) ** 0.6 * 1.08 * widen * K_PUSH
                if limpers:
                    thr *= 0.55
                if p <= thr:
                    return self._shove(obs)
                if after == 1 and to_call <= bb and limpers == 0 and p <= 0.85 and eff_bb > 8:
                    return self._call(obs)
                return self._fold(obs)
            thr = min(0.85, OPEN_PCT.get(after, 0.17) * widen * K_OPEN)
            if limpers:
                thr *= 0.55
            if p <= thr:
                size = 2.2 if eff_bb <= 25 else 2.5
                if after == 1:
                    size = 2.8
                size = size * K_OSIZE + limpers
                return self._raise(obs, bb * size)
            # SB complete with cheap price
            if after == 1 and limpers == 0 and p <= 0.8 and to_call <= bb:
                return self._call(obs)
            return self._fold(obs)

        # facing a raise
        raiser = max(others, key=lambda i: bets[i])
        r_total = stacks[raiser] + bets[raiser]
        r_allin = stacks[raiser] == 0
        callers = sum(1 for i in others if i != raiser and bets[i] >= max_bet)
        price = to_call / float(pot_total + to_call) if to_call else 0.0
        # raiser range width estimate
        if nraise == 1:
            ridx = pre.index(raiser) if raiser in pre else 0
            r_after = len(pre) - 1 - ridx
            w = OPEN_PCT.get(r_after, 0.17) * 0.85
            if r_allin or r_total <= 15 * bb:
                w = max(w, PUSH10.get(r_after, 0.18) * (10.0 / max(r_total / float(bb), 2.0)) ** 0.6)
        elif nraise == 2:
            w = 0.07
        else:
            w = 0.035
        agg = self._pfr(raiser)
        w *= min(4.0, max(0.6, agg / 0.16))
        if w > 1.0:
            w = 1.0
        if callers:
            w *= 0.7 ** callers
        eq = _eq_vs_range(p, w)
        if callers:
            eq -= 0.06 * callers

        commit = r_allin or to_call >= 0.4 * my_total or (eff - max_bet) < 1.2 * (pot_total + to_call)
        if commit:
            if r_allin or 'raise' not in obs.legal:
                risk = min(1.0, (to_call + bets[me]) / float(my_total) * K_RISK)
                ascale = 1.0
                if K_AIMN:
                    ascale = 0.0 if n_alive <= 2 else min(1.0, max(K_AIMFLOOR, (n_alive - 3) / 5.0))
                m = icm_margin + K_AIM * min(1.0, (my_total / float(bb)) / (12.0 * K_SHORT)) * risk * ascale
            else:
                m = icm_margin + K_JAM
            if eq >= price + m or p <= K_PREM:
                if r_allin or 'raise' not in obs.legal:
                    return self._call(obs)
                return self._shove(obs)
            return self._fold(obs)

        raise_bb = max_bet / float(bb)
        ip = after == 0 or (me not in pre[-2:] and len(pre) > 2)
        if eff_bb <= 28 and nraise == 1:
            rthr = max(0.06, min(0.26, w * 0.6)) * widen * K_RESHOVE
            if callers:
                rthr *= 0.6
            if p <= rthr:
                return self._shove(obs)
            # BB flat with very good price and decent hand
            if price <= 0.3 and p <= max(0.12, w * 0.9) and eff_bb > 16:
                return self._call(obs)
            return self._fold(obs)
        if nraise == 1:
            vthr = max(0.03, w * 0.22)
            if p <= vthr or (p <= 0.30 and key[2] and raise_bb <= 3.5 and callers == 0
                             and rng.random() < K_LIGHT3 and p > 0.1):
                size = max_bet * (3.0 if ip else 3.8) + callers * max_bet
                if size >= 0.4 * my_total:
                    return self._shove(obs)
                return self._raise(obs, size)
            cthr = w * (0.75 if ip else 0.55)
            if me == pre[-1] and price <= 0.3:
                cthr = max(cthr, 0.35)
            if p <= cthr and price <= 0.36:
                return self._call(obs)
            return self._fold(obs)
        if nraise == 2:
            i_opened = self.my_last.get(0) == 'raise'
            if p <= 0.022:
                if eff_bb <= 45:
                    return self._shove(obs)
                return self._raise(obs, max_bet * 2.3)
            if p <= (0.09 if i_opened else 0.055) and price <= 0.38:
                return self._call(obs)
            return self._fold(obs)
        if p <= 0.012:
            return self._shove(obs)
        if p <= 0.03 and price <= 0.33:
            return self._call(obs)
        return self._fold(obs)

    # ---- postflop
    def _postflop(self, obs):
        me = obs.seat
        bb = obs.blinds[1] or 1
        stacks, bets = obs.stacks, obs.bets
        s, draw, cat = _analyze(obs.hole, obs.board)
        others = [i for i in range(len(stacks)) if i != me and obs.in_hand[i]]
        if not others:
            return self._fold(obs)
        nopp = len(others)
        to_call = obs.to_call
        pot_total = obs.pot + sum(bets)
        my_stack = stacks[me]
        eff_behind = min(my_stack, max(stacks[i] for i in others) + max(0, max(bets[i] for i in others) - bets[me]))
        street = obs.street
        rng = self.rng
        pre, post = self._geometry(obs)
        live = [x for x in post if x == me or (obs.in_hand[x] and stacks[x] > 0)]
        ip = bool(live) and live[-1] == me
        was_agg = self.my_last.get(street - 1) == 'raise'
        # multiway discount
        sm = s - 0.06 * (nopp - 1) if s < 0.85 else s - 0.02 * (nopp - 1)
        e = max(sm, draw + (0.05 if sm > 0.3 else 0.0))
        if draw and sm > 0.3:
            e = max(sm, sm * 0.5 + draw)
        spr = eff_behind / float(pot_total) if pot_total else 9.0

        if to_call == 0:
            # check or bet
            if sm >= 0.82 - K_VALUE:
                frac = 0.75 if street < 3 else 0.85
                if spr < 1.5:
                    return self._shove(obs)
                return self._raise(obs, bets[me] + pot_total * frac)
            if sm >= 0.6 - K_VALUE:
                if spr < 1.2:
                    return self._shove(obs)
                if nopp <= 2 or sm >= 0.7:
                    return self._raise(obs, bets[me] + pot_total * 0.6)
                return ('check', 0)
            if draw >= 0.15 and street < 3 and nopp <= 2:
                if rng.random() < 0.75:
                    return self._raise(obs, bets[me] + pot_total * 0.6)
                return ('check', 0)
            # bluff / barrel with weak hands
            fr = self._foldr(others[0])
            fold_adj = min(1.25, max(0.3, (fr - 0.2) / 0.3))
            if nopp == 1:
                freq = 0.0
                if was_agg:
                    freq = (0.8, 0.6, 0.45)[street - 1]
                elif ip:
                    freq = (0.55, 0.45, 0.35)[street - 1]
                if street == 3 and sm >= 0.35:
                    freq *= 0.3  # showdown value: check it down more
                if rng.random() < freq * K_BLUFF * fold_adj:
                    return self._raise(obs, bets[me] + pot_total * (0.5 if street == 1 else 0.6))
            elif nopp == 2 and was_agg and street == 1 and rng.random() < 0.4:
                return self._raise(obs, bets[me] + pot_total * 0.5)
            return ('check', 0)

        # facing a bet
        bettor = max(others, key=lambda i: bets[i])
        bet_sz = bets[bettor] - bets[me]
        prior_pot = pot_total - bets[bettor] - bets[me] + bets[me]
        pot_before = max(1, obs.pot)
        bet_frac = bets[bettor] / float(pot_before)
        price = to_call / float(pot_total + to_call)
        agg = self._agg(bettor)
        adj = 0.0
        if agg > 0.33:
            adj += min(0.14, (agg - 0.33) * 0.6)
        ev = e + adj
        if s >= 0.86 or (s >= 0.8 and nopp == 1):
            if spr < 2.5 or to_call >= 0.35 * my_stack:
                return self._shove(obs)
            return self._raise(obs, bets[bettor] + (pot_total + to_call) * 0.8)
        need = price + 0.04 + K_CALL
        if K_PRISK and s < 0.86:
            need += K_PRISK * min(1.0, to_call / float(max(1, my_stack + bets[me])) * 1.5)
        if bet_frac > 0.75:
            need += 0.08 * min(2.0, bet_frac - 0.75)
        big = to_call > 25 * bb and to_call > 0.3 * (my_stack + bets[me])
        if big and s < 0.7 and adj < 0.08:
            # deep-stack brake: no hero calls of big bets with one pair
            if draw >= price and to_call < 0.5 * my_stack and street < 3:
                return self._call(obs)
            return self._fold(obs)
        # semi-bluff raise
        if street == 1 and draw >= 0.3 and nopp == 1 and to_call < 0.25 * my_stack and rng.random() < 0.4:
            return self._raise(obs, bets[bettor] + (pot_total + to_call) * 0.8)
        dval = draw
        if street < 3 and dval > 0:
            dval += 0.04  # implied odds
        if ev >= need or dval >= price:
            return self._call(obs)
        return self._fold(obs)
