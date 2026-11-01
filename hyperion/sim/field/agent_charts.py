# Origin: the night field's persona builds (docs/drills/field/agent_charts.md is the builder's log). A coding agent,
# playing a two-person team led by a strong live cash player, built it in one hour from T0 against the red-team brief
# and kit, with no access to this repository; frozen at md5 8d684a439cabe518f86a1c471e343d2b (its FROZEN.md5, minute
# 17) and copied here unchanged apart from this header. The archived original is docs/drills/field/agent_charts_bot.py.
# It is played through hyperion.sim.bestiary.AgentChartsBot (registry name `agent_charts`), one of the `night` pool's
# one-hour builds. Do not edit; a new bot is a new file.
"""rival_bot.py -- tight-aggressive cash-game bot: positional preflop charts typed in from memory,
standard c-bets, value-heavy postflop with pot-odds calls.  No ICM.  Standard library only."""
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

RK = '23456789TJQKA'


# ----------------------------------------------------------------------------------------------
# range strings -> sets of (hi, lo, suited)
# ----------------------------------------------------------------------------------------------
def _one(t):
    r1 = RK.index(t[0])
    r2 = RK.index(t[1])
    s = len(t) > 2 and t[2] == 's'
    if r1 < r2:
        r1, r2 = r2, r1
    return r1, r2, (s and r1 != r2)


def _parse(spec):
    out = set()
    for tok in spec.replace(' ', '').split(','):
        if not tok:
            continue
        if '-' in tok:
            a, b = tok.split('-')
            r1a, r2a, sa = _one(a)
            r1b, r2b, sb = _one(b)
            if r1a == r2a:
                for r in range(min(r1a, r1b), max(r1a, r1b) + 1):
                    out.add((r, r, False))
            else:
                for lo in range(min(r2a, r2b), max(r2a, r2b) + 1):
                    out.add((r1a, lo, sa))
        elif tok.endswith('+'):
            r1, r2, s = _one(tok[:-1])
            if r1 == r2:
                for r in range(r1, 13):
                    out.add((r, r, False))
            else:
                for lo in range(r2, r1):
                    out.add((r1, lo, s))
        else:
            out.add(_one(tok))
    return frozenset(out)


OPEN = {k: _parse(v) for k, v in {
    'UTG': "66+,ATs+,KTs+,QTs+,JTs,AQo+,KQo",
    'UTG1': "55+,A9s+,A5s,KTs+,QTs+,J9s+,T9s,AJo+,KQo",
    'LJ': "55+,A8s+,A5s-A4s,KTs+,QTs+,J9s+,T9s,98s,ATo+,KQo",
    'HJ': "44+,A2s+,K9s+,Q9s+,J9s+,T9s,98s,87s,ATo+,KJo+,QJo",
    'CO': "22+,A2s+,K7s+,Q9s+,J9s+,T8s+,98s,87s,76s,65s,A9o+,KTo+,QTo+,JTo",
    'BTN': "22+,A2s+,K2s+,Q4s+,J7s+,T7s+,97s+,86s+,75s+,64s+,54s,A2o+,K8o+,Q9o+,J9o+,T9o",
    'SB': "22+,A2s+,K5s+,Q8s+,J8s+,T8s+,97s+,87s,76s,65s,54s,A4o+,K9o+,QTo+,JTo",
}.items()}

ISO = _parse("77+,ATs+,KJs+,QJs,JTs,AJo+,KQo")          # raise over limpers
LIMP_BEHIND = _parse("22-99,A2s-A9s,KTs,QTs,JTs,T9s,98s,87s,76s,65s")
TB_VAL_EP = _parse("QQ+,AKs,AKo")                         # 3-bet for value vs early opens
TB_VAL_LP = _parse("JJ+,AQs+,AKo")                        # vs late opens
TB_BLUFF = _parse("A5s-A3s")
CALL_VS_EP = _parse("66-JJ,ATs-AQs,KTs+,QJs,JTs,T9s,98s,AQo")
CALL_VS_LP = _parse("22-TT,ATs-AQs,KTs+,QTs+,J9s+,T9s,98s,87s,76s,65s,AJo-AQo,KQo")
BB_VS_EP = _parse("22-JJ,A9s-AQs,KTs+,QTs+,J9s+,T9s,98s,87s,76s,65s,AJo-AQo,KQo")
BB_VS_LP = _parse("22-TT,A2s-AQs,K5s+,Q8s+,J8s+,T7s+,97s+,86s+,75s+,65s,54s,A7o-AQo,K9o+,QTo+,JTo,T9o")
SB_CALL_EP = _parse("88-JJ,AQs,KQs")
SB_CALL_LP = _parse("55-TT,AJs-AQs,KQs,AQo")
FOURBET_VAL = _parse("KK+,AKs")
CALL_3BET = _parse("99-QQ,AJs-AQs,AKo,KQs")
CALL_3BET_BIG = _parse("QQ,AKo")                           # when the 3-bet is a large part of the stack
CALL_5BET = _parse("QQ,AKo")
TIGHT_CALL = _parse("77-JJ,AJs-AQs,KQs,AQo")                # big raise relative to the stack
HUGE_CALL = _parse("TT-QQ,AQs,AKo")                         # raise is a third or more of the stack


# ----------------------------------------------------------------------------------------------
# hand percentiles (Chen formula ordering) for push/fold and equity-vs-range estimates
# ----------------------------------------------------------------------------------------------
def _chen(hi, lo, suited):
    pts = {12: 10, 11: 8, 10: 7, 9: 6}
    s = float(pts.get(hi, (hi + 2) / 2.0))
    if hi == lo:
        return max(8.0, s * 2)      # Chen undervalues small pairs for shove/fold
    if suited:
        s += 2
    gap = hi - lo - 1
    s -= (0, 1, 2, 4, 5)[min(gap, 4)]
    if gap <= 1 and hi < 10:
        s += 1
    return float(int(s + 0.999))


def _build_pct():
    hands = []
    for hi in range(13):
        for lo in range(hi + 1):
            if hi == lo:
                hands.append(((hi, lo, False), 6))
            else:
                hands.append(((hi, lo, True), 4))
                hands.append(((hi, lo, False), 12))
    hands.sort(key=lambda h: (-_chen(*h[0]), -h[0][0], -h[0][1], not h[0][2]))
    out = {}
    cum = 0
    for k, c in hands:
        out[k] = (cum + c / 2.0) / 1326.0
        cum += c
    return out


PCT = _build_pct()


def _eq_random(p):
    return 0.34 + 0.52 * (1.0 - p) ** 1.3


def _push_pct(eff_bb, tier):
    if eff_bb <= 4:
        b = 0.72
    elif eff_bb <= 6:
        b = 0.58
    elif eff_bb <= 8:
        b = 0.44
    elif eff_bb <= 10:
        b = 0.36
    elif eff_bb <= 12:
        b = 0.29
    else:
        b = 0.23
    m = {'BTN': 1.3, 'SB': 1.3, 'CO': 1.15, 'HJ': 1.0, 'LJ': 0.9, 'UTG1': 0.8, 'UTG': 0.75, 'BB': 1.0}.get(tier, 0.9)
    return min(0.95, b * m)


# ----------------------------------------------------------------------------------------------
# postflop hand analysis
# ----------------------------------------------------------------------------------------------
_WINS = []
for _hi in range(4, 13):
    _WINS.append(sum(1 << r for r in range(_hi - 4, _hi + 1)))
_WINS.append((1 << 12) | 0b1111)  # wheel


def _straight_high(mask):
    for hi in range(12, 3, -1):
        w = 31 << (hi - 4)
        if mask & w == w:
            return hi
    if mask & ((1 << 12) | 15) == ((1 << 12) | 15):
        return 3
    return -1


def _analyze(hole, board, street):
    """returns (strength, draw_equity, wet, outs)"""
    r1 = hole[0] >> 2
    r2 = hole[1] >> 2
    s1 = hole[0] & 3
    s2 = hole[1] & 3
    cnt = [0] * 13
    bcnt = [0] * 13
    suit = [0] * 4
    bsuit = [0] * 4
    mask = 0
    bmask = 0
    for c in board:
        r = c >> 2
        bcnt[r] += 1
        cnt[r] += 1
        suit[c & 3] += 1
        bsuit[c & 3] += 1
        bmask |= 1 << r
    cnt[r1] += 1
    cnt[r2] += 1
    suit[s1] += 1
    suit[s2] += 1
    mask = bmask | (1 << r1) | (1 << r2)
    br = sorted([c >> 2 for c in board], reverse=True)
    hi_h = r1 if r1 > r2 else r2
    lo_h = r2 if r1 > r2 else r1

    # board texture
    flushy = max(bsuit) >= 3
    sh_b = _straight_high(bmask)
    straighty = False
    if len(br) >= 3:
        rs = sorted(set(br))
        for i in range(len(rs) - 2):
            if rs[i + 2] - rs[i] <= 4:
                straighty = True
                break
        if 12 in rs and len([r for r in rs if r <= 3]) >= 2:
            straighty = True
    paired = max(bcnt) >= 2
    wet = flushy or straighty
    pen = 0.04 if (wet and street < 3) else 0.0

    quads = trips = None
    trips_l = []
    pairs_l = []
    for r in range(12, -1, -1):
        c = cnt[r]
        if c == 4:
            quads = r
        elif c == 3:
            trips_l.append(r)
        elif c == 2:
            pairs_l.append(r)
    hole_r = (r1, r2)

    # flush
    fl_suit = -1
    for sdx in range(4):
        if suit[sdx] >= 5:
            fl_suit = sdx
    sh_all = _straight_high(mask)

    s = None
    if quads is not None:
        s = 0.98 if quads in hole_r else 0.30
    if s is None and fl_suit >= 0 and sh_all >= 0:
        # straight flush check
        sm = 0
        for c in board:
            if (c & 3) == fl_suit:
                sm |= 1 << (c >> 2)
        if s1 == fl_suit:
            sm |= 1 << r1
        if s2 == fl_suit:
            sm |= 1 << r2
        if _straight_high(sm) >= 0 and bsuit[fl_suit] < 5:
            s = 0.995
    if s is None and trips_l and (len(trips_l) > 1 or pairs_l):
        if max(bcnt) == 3 and sum(1 for x in bcnt if x == 2) >= 1 and len(board) == 5:
            s = 0.35
        else:
            s = 0.93
    if s is None and fl_suit >= 0:
        hs = [r for r, sx in ((r1, s1), (r2, s2)) if sx == fl_suit]
        if bsuit[fl_suit] >= 5:
            best = max(hs) if hs else -1
            s = 0.9 if best == 12 else (0.5 if best >= 10 else 0.3)
        else:
            s = 0.80 + 0.012 * max(hs)
    if s is None and sh_all >= 0:
        if sh_all > sh_b:
            s = 0.84 - pen - (0.04 if paired else 0.0)
            if r1 != r2 and sh_all >= 8:
                s += 0.02
        else:
            s = 0.30
    if s is None and trips_l:
        r = trips_l[0]
        if r1 == r2 == r:
            s = 0.88 - pen
        elif r in hole_r:
            s = 0.80 - pen
        else:
            s = 0.30 + (0.05 if hi_h == 12 else 0.0)
    if s is None and len(pairs_l) >= 2:
        hp = [r for r in pairs_l if r in hole_r]
        if len(hp) >= 2:
            s = 0.78 - pen + (0.02 if hp[0] == br[0] else 0.0)
        elif len(hp) == 1:
            pr = hp[0]
            if r1 == r2:
                s = 0.72 if r1 > br[0] else 0.45
            else:
                other = [r for r in pairs_l if r != pr][0]
                s = 0.55 if pr > other else 0.40
            s -= pen / 2
        else:
            s = 0.18 + (0.08 if hi_h == 12 else 0.0)
    if s is None and len(pairs_l) == 1:
        pr = pairs_l[0]
        if r1 == r2:
            if len(br) == 0:
                s = 0.64 + 0.012 * r1
            elif r1 > br[0]:
                s = 0.64 + 0.012 * r1 - pen * 0.75
            elif len(br) > 1 and r1 > br[1]:
                s = 0.42
            else:
                s = 0.30
        elif pr in hole_r:
            k = lo_h if pr == hi_h else hi_h
            if pr == br[0]:
                s = 0.50 + 0.015 * k + (0.02 if pr >= 9 else 0.0) - pen * 0.5
            elif len(br) > 1 and pr == br[1]:
                s = 0.34 + 0.006 * k
            else:
                s = 0.25 + 0.004 * k
        else:
            s = 0.10 + (0.07 if hi_h == 12 else (0.03 if hi_h >= 10 else 0.0))
    if s is None:
        s = 0.05 + 0.011 * hi_h
        if br and lo_h > br[0]:
            s += 0.04

    # draws
    d = 0.0
    outs = 0
    if street < 3 and s < 0.8:
        for sdx in range(4):
            if suit[sdx] == 4 and ((s1 == sdx) or (s2 == sdx)):
                outs += 9
                if (s1 == sdx and r1 == 12) or (s2 == sdx and r2 == 12):
                    outs += 1
        if sh_all < 0:
            hm = (1 << r1) | (1 << r2)
            so = 0
            for r in range(13):
                if mask & (1 << r):
                    continue
                m = mask | (1 << r)
                for w in _WINS:
                    if (w >> r) & 1 and (m & w) == w and (hm & w):
                        so += 1
                        break
            outs += so * 4          # four cards per completing rank
        outs = min(outs, 15)
        d = outs * (0.042 if street == 1 else 0.0215)
    return s, d, wet, outs


# ----------------------------------------------------------------------------------------------
class Bot(Agent):
    DEBUG = False

    def __init__(self):
        self.rng = random.Random(1234567)
        self.hand_no = -1
        self.aggr = False
        self.barreled = False
        self.had_draw = False
        self.called = 0
        self.n_seen = 0

    def new_table(self, rules, seat, n_players):
        self.hand_no = -1
        self.aggr = False
        self.barreled = False
        self.had_draw = False
        self.called = 0

    def hand_end(self, result):
        pass

    # ------------------------------------------------------------------ public
    def act(self, obs):
        try:
            a = self._act(obs)
            return self._sane(a, obs)
        except Exception:
            if self.DEBUG:
                raise
            return self._safe(obs)

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _safe(o):
        try:
            lg = set(o.legal)
        except Exception:
            return ('fold', 0)
        if 'check' in lg:
            return ('check', 0)
        if 'fold' in lg:
            return ('fold', 0)
        if 'call' in lg:
            return ('call', 0)
        for k in lg:
            return (k, 0)
        return ('fold', 0)

    def _sane(self, a, o):
        lg = set(o.legal)
        if not isinstance(a, tuple) or len(a) != 2 or a[0] not in lg:
            return self._safe(o)
        if a[0] == 'raise':
            lo = min(o.min_raise, o.max_raise)
            hi = max(o.min_raise, o.max_raise)
            t = int(a[1])
            if t < lo:
                t = lo
            if t > hi:
                t = hi
            return ('raise', t)
        return (a[0], 0)

    def _raise_to(self, o, target):
        lo = min(o.min_raise, o.max_raise)
        hi = max(o.min_raise, o.max_raise)
        t = int(target)
        if t < lo:
            t = lo
        if t >= hi or (hi - t) < 0.3 * t:
            t = hi
        return ('raise', t)

    # ------------------------------------------------------------------ main
    def _act(self, o):
        lg = set(o.legal)
        n = len(o.stacks)
        me = o.seat
        if o.hand_no != self.hand_no:
            self.hand_no = o.hand_no
            self.aggr = False
            self.barreled = False
            self.had_draw = False
            self.called = 0
        if o.street == 0:
            a = self._preflop(o, lg, n, me)
        else:
            a = self._postflop(o, lg, n, me)
        return a

    # ------------------------------------------------------------------ preflop
    def _preflop(self, o, lg, n, me):
        bb = o.blinds[1]
        sb = o.blinds[0]
        h1, h2 = o.hole
        r1 = h1 >> 2
        r2 = h2 >> 2
        if r1 < r2:
            r1, r2 = r2, r1
        key = (r1, r2, (h1 & 3) == (h2 & 3) and r1 != r2)
        pct = PCT[key]
        self.aggr = False
        bets = o.bets
        stacks = o.stacks
        mx = max(bets)
        my_total = stacks[me] + bets[me]
        to_call = o.to_call
        # dealt-in seats and positions
        dealt = [i for i in range(n) if o.in_hand[i] or stacks[i] > 0 or bets[i] > 0]
        if me not in dealt:
            dealt.append(me)
        order = [(o.button + 1 + k) % n for k in range(n) if ((o.button + 1 + k) % n) in dealt]
        nd = len(order)
        idx = order.index(me) if me in order else nd - 1
        if nd == 2:
            tier = 'BTN' if me == o.button else 'BB'
        elif idx == 0:
            tier = 'SB'
        elif idx == 1:
            tier = 'BB'
        else:
            dist = nd - 1 - idx
            tier = ('BTN', 'CO', 'HJ', 'LJ', 'UTG1', 'UTG')[min(dist, 5)]
        # effective stack
        opp_tot = [stacks[i] + bets[i] for i in range(n) if i != me and o.in_hand[i]]
        eff = min(my_total, max(opp_tot)) if opp_tot else my_total
        eff_bb = eff / float(bb)

        # raise count
        nraise = 0
        raiser = None
        if mx > bb:
            for h in (o.history or []):
                try:
                    sx, a = h
                    if a[0] == 'raise' and int(a[1]) > bb:
                        nraise += 1
                        raiser = sx
                except Exception:
                    pass
            if nraise == 0:
                nraise = 1 if mx <= 6 * bb else (2 if mx <= 15 * bb else 3)
            if raiser is None or raiser == me or not (0 <= raiser < n) or bets[raiser] != mx:
                best = -1
                for i in range(n):
                    if i != me and bets[i] == mx:
                        best = i
                        break
                raiser = best if best >= 0 else None
        limpers = 0
        if nraise == 0:
            cnt = sum(1 for i in range(n) if i != me and bets[i] >= bb)
            limpers = max(0, cnt - (0 if tier == 'BB' else 1))
        callers = 0
        if nraise >= 1:
            callers = sum(1 for i in range(n) if i != me and 0 < bets[i] == mx and i != raiser)

        raiser_tier = None
        if raiser is not None and raiser in order:
            ri = order.index(raiser)
            if nd == 2:
                raiser_tier = 'BTN' if raiser == o.button else 'BB'
            elif ri == 0:
                raiser_tier = 'SB'
            elif ri == 1:
                raiser_tier = 'BB'
            else:
                raiser_tier = ('BTN', 'CO', 'HJ', 'LJ', 'UTG1', 'UTG')[min(nd - 1 - ri, 5)]
        early_opener = raiser_tier in ('UTG', 'UTG1', 'LJ')

        shove = ('raise', o.max_raise)

        # ---------------- short stack: push / fold
        if eff_bb <= 15:
            if nraise == 0:
                lim = _push_pct(eff_bb, tier)
                if tier == 'BB' and limpers == 0:
                    return ('check', 0) if 'check' in lg else ('fold', 0)
                if limpers:
                    lim *= 0.85
                if pct <= lim and 'raise' in lg:
                    self.aggr = True
                    return shove
                if tier == 'BB' and 'check' in lg:
                    return ('check', 0)
                if 'check' in lg:
                    return ('check', 0)
                if tier == 'SB' and eff_bb > 8 and to_call <= sb and pct < 0.55:
                    return ('call', 0)
                return ('fold', 0)
            # facing a raise
            pot_total = o.pot + sum(bets)
            req = to_call / float(pot_total + to_call) if (pot_total + to_call) > 0 else 0.5
            eqr = 0.5 + (_eq_random(pct) - 0.5) * (0.78 if nraise == 1 else 0.6)
            facing_big = to_call >= 0.5 * (my_total)
            if pct <= (0.045 if eff_bb > 10 else 0.08) and 'raise' in lg:
                self.aggr = True
                return shove
            if eqr >= req + (0.04 if facing_big else 0.02) and 'call' in lg:
                if to_call >= stacks[me] and pct > 0.30:
                    return ('fold', 0)
                if to_call < 0.4 * stacks[me] and pct > 0.65:
                    return ('fold', 0)       # not getting committed: do not defend with garbage
                return ('call', 0)
            return ('check', 0) if 'check' in lg else ('fold', 0)

        # ---------------- deep stacks: charts
        def sized(mult_bb_or_total):
            return self._raise_to(o, mult_bb_or_total)

        if nraise == 0:
            if tier == 'BB':
                if limpers and key in ISO and 'raise' in lg:
                    self.aggr = True
                    return sized(bb * (3 + limpers))
                if 'check' in lg:
                    return ('check', 0)
                return ('fold', 0)
            if nd == 2 and tier == 'BTN':
                if pct <= 0.78 and 'raise' in lg:
                    self.aggr = True
                    return sized(bb * 2.5)
                if 'call' in lg and pct < 0.9:
                    return ('call', 0)
                return ('fold', 0)
            rng_open = OPEN[tier]
            if key in rng_open:
                if limpers and tier != 'SB' and key not in ISO and key[0] != key[1] and key[2] is False and pct > 0.25:
                    # marginal offsuit hand behind limpers: just overlimp from late position
                    if 'call' in lg and tier in ('BTN', 'CO'):
                        return ('call', 0)
                if 'raise' in lg:
                    self.aggr = True
                    base = 2.5 if tier in ('BTN', 'CO', 'SB') else 3.0
                    if eff_bb < 40:
                        base = 2.2 if tier in ('BTN', 'CO', 'SB') else 2.5
                    return sized(bb * (base + limpers))
            if limpers >= 2 and key in LIMP_BEHIND and 'call' in lg and to_call <= bb:
                return ('call', 0)
            if tier == 'SB' and limpers and to_call <= bb - sb and pct < 0.5:
                return ('call', 0)
            return ('check', 0) if 'check' in lg else ('fold', 0)

        if nraise == 1:
            val = TB_VAL_EP if early_opener else TB_VAL_LP
            raise_bb = mx / float(bb)
            if raise_bb > 5:
                val = TB_VAL_EP
            if key in val and 'raise' in lg:
                self.aggr = True
                ip = tier in ('BTN', 'CO', 'HJ', 'LJ')
                mult = 3.0 if ip else 4.0
                return sized(mx * mult + callers * mx)
            if key in val and 'call' in lg:
                return ('call', 0)
            fr = to_call / float(my_total) if my_total else 1.0
            if fr > 0.12 and 'call' in lg:
                if fr > 0.33:
                    return ('call', 0) if key in HUGE_CALL else ('fold', 0)
                return ('call', 0) if key in TIGHT_CALL else ('fold', 0)
            if (key in TB_BLUFF and not early_opener and callers == 0 and raise_bb <= 3.6 and
                    'raise' in lg and self.rng.random() < 0.45 and tier != 'BB'):
                self.aggr = True
                return sized(mx * (3.0 if tier in ('BTN', 'CO') else 3.8))
            if tier == 'BB':
                rng_call = BB_VS_EP if early_opener else BB_VS_LP
                if raise_bb > 4 or callers >= 2:
                    rng_call = BB_VS_EP
                if key in rng_call and 'call' in lg:
                    return ('call', 0)
                return ('fold', 0)
            if tier == 'SB':
                rng_call = SB_CALL_EP if early_opener else SB_CALL_LP
                if key in rng_call and 'call' in lg and raise_bb <= 4:
                    return ('call', 0)
                return ('fold', 0)
            rng_call = CALL_VS_EP if early_opener else CALL_VS_LP
            if raise_bb > 5:
                rng_call = CALL_VS_EP
            if key in rng_call and 'call' in lg and to_call <= 0.12 * my_total:
                return ('call', 0)
            return ('fold', 0)

        if nraise == 2:
            i_raised = bets[me] > bb
            frac = to_call / float(my_total) if my_total else 1.0
            if key in FOURBET_VAL and 'raise' in lg:
                self.aggr = True
                return sized(mx * 2.3)
            if key in FOURBET_VAL and 'call' in lg:
                return ('call', 0)
            if i_raised:
                rng_c = CALL_3BET if frac <= 0.22 else CALL_3BET_BIG
                if key == (12, 11, False) and 'raise' in lg and self.rng.random() < 0.35 and frac <= 0.3:
                    self.aggr = True
                    return sized(mx * 2.3)
                if key in rng_c and 'call' in lg:
                    return ('call', 0)
                return ('fold', 0)
            # cold facing a 3-bet
            if key in CALL_3BET_BIG and 'call' in lg and frac <= 0.25:
                return ('call', 0)
            return ('fold', 0)

        # four-bet and up
        if key in FOURBET_VAL:
            if 'raise' in lg:
                self.aggr = True
                return shove
            return ('call', 0) if 'call' in lg else ('check', 0)
        if key in CALL_5BET and 'call' in lg and to_call <= 0.4 * my_total:
            return ('call', 0)
        return ('fold', 0)

    # ------------------------------------------------------------------ postflop
    def _postflop(self, o, lg, n, me):
        bb = o.blinds[1]
        st = o.street
        bets = o.bets
        stacks = o.stacks
        my_stack = stacks[me]
        s, d, wet, outs = _analyze(o.hole, o.board, st)
        n_opp = sum(1 for i in range(n) if i != me and o.in_hand[i])
        if n_opp < 1:
            n_opp = 1
        pot_total = o.pot + sum(bets)
        to_call = o.to_call
        mx = max(bets)
        rnd = self.rng.random
        # position: last to act among remaining
        def key(i):
            k = (i - o.button) % n
            return n if k == 0 else k
        ip = all(key(me) > key(i) for i in range(n) if i != me and o.in_hand[i])
        e = s if s >= 0.7 else s + (1.0 - s) * d * 0.85
        if st == 3:
            e = s
        if d >= 0.25:
            self.had_draw = True
        can_raise = 'raise' in lg

        def bet(frac):
            amt = bets[me] + max(bb, int(frac * pot_total))
            if amt >= 0.5 * (my_stack + bets[me]) or my_stack <= 0.9 * pot_total:
                amt = o.max_raise
            return self._raise_to(o, amt)

        # ---------------- facing a bet
        if to_call > 0:
            prior = max(1, pot_total - to_call)
            ratio = to_call / float(prior)
            req = to_call / float(pot_total + to_call)
            adj = e - 0.04 * (n_opp - 1)
            if ratio > 1.0:
                adj -= 0.05
            elif ratio > 0.7:
                adj -= 0.03
            if self.aggr_this_street(o):
                adj -= 0.07          # we bet and got raised: value-heavy raise
            if self.called and st > 1:
                adj -= 0.03 * min(self.called, 2)   # he has bet every street: believe him
            # strong hand: raise for value
            if s >= 0.80 and can_raise:
                if st < 3 or s >= 0.85:
                    if rnd() < 0.85:
                        amt = mx + int(0.8 * (pot_total + to_call))
                        self.barreled = True
                        return self._raise_to(o, amt)
                return ('call', 0)
            if st < 3 and d >= 0.30 and n_opp == 1 and can_raise and ratio <= 0.8 and rnd() < 0.28:
                self.barreled = True
                return self._raise_to(o, mx + int(0.75 * (pot_total + to_call)))
            margin = 0.03 if st == 1 else (0.05 if st == 2 else 0.07)
            if st == 3:
                adj -= 0.03      # river bets are mostly value; fold the marginal bluff-catchers
            if adj >= req + margin and 'call' in lg:
                self.called += 1
                return ('call', 0)
            return ('fold', 0) if 'fold' in lg else ('check', 0)

        # ---------------- checked to us / first to act
        if not can_raise:
            return ('check', 0)
        if st == 1:
            if self.aggr:
                if n_opp == 1:
                    if s >= 0.62:
                        self.barreled = True
                        return bet(0.66 if wet else 0.55)
                    if d >= 0.25 and rnd() < 0.8:
                        self.barreled = True
                        return bet(0.6)
                    f = 0.45 if wet else 0.68
                    if s >= 0.28:
                        f -= 0.1
                    if rnd() < f:
                        self.barreled = True
                        return bet(0.4 if not wet else 0.5)
                    return ('check', 0)
                if s >= 0.55:
                    self.barreled = True
                    return bet(0.6)
                if d >= 0.3 and rnd() < 0.6:
                    self.barreled = True
                    return bet(0.55)
                if n_opp == 2 and rnd() < 0.15:
                    self.barreled = True
                    return bet(0.4)
                return ('check', 0)
            if s >= 0.62:
                return bet(0.66)
            if d >= 0.25 and rnd() < (0.5 if ip else 0.33):
                return bet(0.6)
            if n_opp == 1 and ip and not wet and rnd() < 0.25:
                return bet(0.4)
            return ('check', 0)
        if st == 2:
            if s >= 0.80:
                self.barreled = True
                return bet(0.75)
            if s >= 0.62:
                self.barreled = True
                return bet(0.66)
            if s >= 0.48 and ip and n_opp == 1 and rnd() < 0.35:
                return bet(0.4)
            if d >= 0.18 and n_opp == 1 and rnd() < 0.45:
                self.barreled = True
                return bet(0.6)
            if self.barreled and self.aggr and n_opp == 1 and rnd() < (0.3 if ip else 0.2):
                return bet(0.55)
            return ('check', 0)
        # river
        if s >= 0.82:
            return bet(0.8)
        if s >= 0.66:
            if n_opp == 1 or s >= 0.74:
                return bet(0.5) if rnd() < 0.85 else ('check', 0)
        if s >= 0.55 and n_opp == 1 and ip and rnd() < 0.3:
            return bet(0.33)
        if s < 0.3 and n_opp == 1 and self.had_draw and rnd() < 0.25:
            return bet(0.6)
        if s < 0.3 and n_opp == 1 and self.barreled and rnd() < 0.1:
            return bet(0.6)
        return ('check', 0)

    @staticmethod
    def aggr_this_street(o):
        # did we already bet on this street (history has our seat raising after the last street break)?
        # no street markers in history; approximate: we hold a chip contribution this street
        try:
            return o.bets[o.seat] > 0
        except Exception:
            return False
