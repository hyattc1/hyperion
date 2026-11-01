# Origin: the night field's persona builds (docs/drills/field/agent_montecarlo.md is the builder's log). A coding agent,
# playing a three-person team that insisted on Monte Carlo hand equity against pot odds in pure Python, built it in one
# hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# 653c9c29fe77708d6318d237ca88e17c (its FROZEN.md5, minute 46) and copied here unchanged apart from this header. The
# archived original is docs/drills/field/agent_montecarlo_bot.py. It is played through
# hyperion.sim.bestiary.AgentMonteCarloBot (registry name `agent_montecarlo`). Do not edit; a new bot is a new file.
"""No Limit team bot: Monte Carlo hand equity vs the opponents still in the hand, compared to pot odds.
Pure standard library. Everything is built for speed: table-driven 7-card evaluator (one dict lookup per
hand for non-flushes), partial Fisher-Yates dealing, early exit as soon as an opponent beats us, a
perf_counter budget inside the simulation loop, and a preflop equity table simulated at import time."""
import gc
import random
import time
from itertools import combinations_with_replacement

try:
    from kit import Agent
except Exception:  # the tournament kit provides Agent
    class Agent(object):
        pass

gc.disable()  # no GC pauses inside a decision; we allocate no cycles

# ------------------------------------------------------------------ evaluator tables
P5 = [5 ** r for r in range(13)]
OFF = 0x3333 << 32          # +3 per 4-bit suit field: bit 3 of a field set <=> that suit has >= 5 cards
FM = 0x8888 << 32
M32 = 0xFFFFFFFF
W = [P5[c >> 2] | ((1 << (4 * (c & 3))) << 32) for c in range(52)]


def _straight_top(mask):
    for top in range(12, 3, -1):
        m = 31 << (top - 4)
        if mask & m == m:
            return top
    if mask & 0x100F == 0x100F:
        return 3
    return -1


def _pack(cat, ranks):
    v = cat << 20
    sh = 16
    for r in ranks:
        v |= (r + 1) << sh
        sh -= 4
    return v


def _rank_value(cnt):
    quads = []; trips = []; pairs = []; singles = []
    mask = 0
    for r in range(12, -1, -1):
        c = cnt[r]
        if c:
            mask |= 1 << r
            if c == 4: quads.append(r)
            elif c == 3: trips.append(r)
            elif c == 2: pairs.append(r)
            else: singles.append(r)
    if quads:
        q = quads[0]
        kick = max(r for r in range(13) if cnt[r] and r != q)
        return _pack(7, (q, kick))
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        p = max(trips[1:] + pairs)
        return _pack(6, (t, p))
    st = _straight_top(mask)
    if st >= 0:
        return _pack(4, (st,))
    if trips:
        return _pack(3, [trips[0]] + singles[:2])
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        kick = max(r for r in range(13) if cnt[r] and r != p1 and r != p2)
        return _pack(2, (p1, p2, kick))
    if pairs:
        return _pack(1, [pairs[0]] + singles[:3])
    return _pack(0, singles[:5])


def _build_tables():
    nf = {}
    for combo in combinations_with_replacement(range(13), 7):
        cnt = [0] * 13
        key = 0
        for r in combo:
            cnt[r] += 1
            key += P5[r]
        if max(cnt) > 4:
            continue
        nf[key] = _rank_value(cnt)
    fl = [0] * 8192
    for mask in range(8192):
        if bin(mask).count('1') >= 5:
            st = _straight_top(mask)
            if st >= 0:
                fl[mask] = _pack(8, (st,))
            else:
                rs = [r for r in range(12, -1, -1) if mask >> r & 1][:5]
                fl[mask] = _pack(5, rs)
    return nf, fl


NF, FL = _build_tables()


def _flush_val(cards):
    m = [0, 0, 0, 0]
    for c in cards:
        m[c & 3] |= 1 << (c >> 2)
    for x in m:
        if bin(x).count('1') >= 5:
            return FL[x]
    return 0


def eval7(cards):
    k = OFF
    for c in cards:
        k += W[c]
    if k & FM:
        return _flush_val(cards)
    return NF[k & M32]


# ------------------------------------------------------------------ preflop equity table (import time)
def _pf_trials(c0, c1, nt, rnd):
    """Equity of hole cards c0,c1 vs 1..7 random hands; one shared board per trial. Returns 7 sums."""
    deck = [c for c in range(52) if c != c0 and c != c1]
    sums = [0.0] * 7
    hw = W[c0] + W[c1]
    for _ in range(nt):
        for i in range(19):
            j = i + int(rnd() * (50 - i))
            deck[i], deck[j] = deck[j], deck[i]
        b = deck[:5]
        kb = OFF + W[b[0]] + W[b[1]] + W[b[2]] + W[b[3]] + W[b[4]]
        hk = kb + hw
        hv = _flush_val([c0, c1] + b) if hk & FM else NF[hk & M32]
        ties = 0
        for i in range(7):
            o1 = deck[5 + 2 * i]; o2 = deck[6 + 2 * i]
            ok = kb + W[o1] + W[o2]
            ov = _flush_val([o1, o2] + b) if ok & FM else NF[ok & M32]
            if ov > hv:
                break
            if ov == hv:
                ties += 1
            sums[i] += 1.0 / (ties + 1)
    return sums


def _class_key(c0, c1):
    r0 = c0 >> 2; r1 = c1 >> 2
    hi = r0 if r0 > r1 else r1
    lo = r1 if r0 > r1 else r0
    return hi * 13 + lo + (169 if (c0 & 3) == (c1 & 3) and r0 != r1 else 0)


PFS = {}   # class key -> [sum per k]
PFN = {}   # class key -> trials
PFW = {}   # class key -> combos
_rng = random.Random(20261101)


def _build_pf(trials):
    rnd = _rng.random
    for hi in range(13):
        for lo in range(hi + 1):
            variants = [(hi * 4 + 0, lo * 4 + 1, False)] if hi == lo else \
                [(hi * 4 + 0, lo * 4 + 0, True), (hi * 4 + 0, lo * 4 + 1, False)]
            for c0, c1, suited in variants:
                key = _class_key(c0, c1)
                PFS[key] = _pf_trials(c0, c1, trials, rnd)
                PFN[key] = trials
                PFW[key] = 6 if hi == lo else (4 if suited else 12)


_T_IMPORT = time.perf_counter()
_build_pf(1000)
_T_IMPORT = time.perf_counter() - _T_IMPORT


def _pf_eq(c0, c1, k):
    key = _class_key(c0, c1)
    return PFS[key][k - 1] / PFN[key]


# equity at the top-X% boundary of the 169 classes (weighted by combos), per number of opponents
_BT = {}


def _boundary(k, frac):
    key = (k, int(round(frac * 100)))
    v = _BT.get(key)
    if v is None:
        items = sorted(((PFS[c][k - 1] / PFN[c], PFW[c]) for c in PFS), reverse=True)
        acc = 0
        v = items[-1][0]
        for e, w in items:
            acc += w
            if acc / 1326.0 >= frac:
                v = e
                break
        _BT[key] = v
    return v


for _k in range(1, 8):
    for _f in range(1, 101):
        _boundary(_k, _f / 100.0)

# percentile (0 = best) of every two-card combo by heads-up equity of its class: used to narrow ranges
_cls = sorted(((PFS[c][0] / PFN[c], c) for c in PFS), reverse=True)
_pct = {}
_acc = 0
for _e, _c in _cls:
    _acc += PFW[_c]
    _pct[_c] = _acc / 1326.0
PCT = [[_pct[_class_key(a, b)] if a != b else 1.0 for b in range(52)] for a in range(52)]


# preflop equity vs one NARROWED opponent (top 35% = raised once, top 12% = re-raised) plus k-1 random hands
def _pf_trials_rng(c0, c1, nt, rnd, combos):
    deck = [c for c in range(52) if c != c0 and c != c1]
    sums = [0.0] * 7
    hw = W[c0] + W[c1]
    nc = len(combos)
    for _ in range(nt):
        while True:
            v1, v2 = combos[int(rnd() * nc)]
            if v1 != c0 and v1 != c1 and v2 != c0 and v2 != c1:
                break
        deck.remove(v1); deck.remove(v2)
        for i in range(17):
            j = i + int(rnd() * (48 - i))
            deck[i], deck[j] = deck[j], deck[i]
        b = deck[:5]
        kb = OFF + W[b[0]] + W[b[1]] + W[b[2]] + W[b[3]] + W[b[4]]
        hk = kb + hw
        hv = _flush_val([c0, c1] + b) if hk & FM else NF[hk & M32]
        ok = kb + W[v1] + W[v2]
        ov = _flush_val([v1, v2] + b) if ok & FM else NF[ok & M32]
        deck.append(v1); deck.append(v2)
        if ov > hv:
            continue
        ties = 1 if ov == hv else 0
        sums[0] += 1.0 / (ties + 1)
        for i in range(6):
            o1 = deck[5 + 2 * i]; o2 = deck[6 + 2 * i]
            ok = kb + W[o1] + W[o2]
            ov = _flush_val([o1, o2] + b) if ok & FM else NF[ok & M32]
            if ov > hv:
                break
            if ov == hv:
                ties += 1
            sums[i + 1] += 1.0 / (ties + 1)
    return sums


PFR = [None, {}, {}]    # level -> class key -> sums
PFRN = 450


def _build_pfr(trials):
    rnd = _rng.random
    for lv, cut in ((1, 0.35), (2, 0.12)):
        combos = [(x, y) for x in range(52) for y in range(x + 1, 52) if PCT[x][y] <= cut]
        for hi in range(13):
            for lo in range(hi + 1):
                variants = [(hi * 4 + 0, lo * 4 + 1)] if hi == lo else \
                    [(hi * 4 + 0, lo * 4 + 0), (hi * 4 + 0, lo * 4 + 1)]
                for c0, c1 in variants:
                    PFR[lv][_class_key(c0, c1)] = _pf_trials_rng(c0, c1, trials, rnd, combos)


_build_pfr(PFRN)


def _pfr_eq(c0, c1, lv, k):
    return PFR[lv][_class_key(c0, c1)][k - 1] / PFRN


_RB = {}


def _rboundary(lv, k, frac):
    key = (lv, k, int(round(frac * 100)))
    v = _RB.get(key)
    if v is None:
        items = sorted(((PFR[lv][c][k - 1] / PFRN, PFW[c]) for c in PFR[lv]), reverse=True)
        acc = 0
        v = items[-1][0]
        for e, w in items:
            acc += w
            if acc / 1326.0 >= frac:
                v = e
                break
        _RB[key] = v
    return v


for _lv in (1, 2):
    for _k in range(1, 8):
        for _f in range(1, 31):
            _rboundary(_lv, _k, _f / 100.0)

_rand = random.random
_perf = time.perf_counter


# ------------------------------------------------------------------ postflop Monte Carlo
def _sim(hero, board, n_opp, tl, thr, budget_s, t0, nmax=3000):
    """Equity of hero vs n_opp hands on this board. tl[i] is the tightness level of opponent i (0 = any two
    cards, 1 = top ~50%, 2 = top ~20%, via rejection sampling). Stops on the clock (perf_counter), or early once
    the estimate is 3 standard errors away from every decision threshold in thr. Returns (equity, trials)."""
    dead = set(hero); dead.update(board)
    deck = [c for c in range(52) if c not in dead]
    nd = len(deck)
    need_b = 5 - len(board)
    kb0 = OFF
    for c in board:
        kb0 += W[c]
    hw = W[hero[0]] + W[hero[1]]
    base = list(board)
    h0, h1 = hero
    wins = 0.0
    n = 0
    rnd = _rand
    deadline = t0 + budget_s
    nb2 = need_b
    pct = PCT
    cuts = (1.0, 0.5, 0.2)
    lows = (1.0, 0.25, 0.08)
    while n < nmax:
        for _blk in range(4):
            kb = kb0
            for i in range(nb2):
                j = i + int(rnd() * (nd - i))
                deck[i], deck[j] = deck[j], deck[i]
                kb += W[deck[i]]
            hk = kb + hw
            if hk & FM:
                hv = _flush_val([h0, h1] + base + deck[:nb2])
            else:
                hv = NF[hk & M32]
            ties = 0
            lost = False
            p = nb2
            for o in range(n_opp):
                lv = tl[o]
                tries = 0
                while True:
                    i = p
                    j = i + int(rnd() * (nd - i))
                    deck[i], deck[j] = deck[j], deck[i]
                    i += 1
                    j = i + int(rnd() * (nd - i))
                    deck[i], deck[j] = deck[j], deck[i]
                    o1 = deck[p]; o2 = deck[p + 1]
                    if lv == 0 or tries >= 3:
                        break
                    if pct[o1][o2] <= cuts[lv] or rnd() < lows[lv]:
                        break
                    tries += 1
                p += 2
                ok = kb + W[o1] + W[o2]
                if ok & FM:
                    ov = _flush_val([o1, o2] + base + deck[:nb2])
                else:
                    ov = NF[ok & M32]
                if ov > hv:
                    lost = True
                    break
                if ov == hv:
                    ties += 1
            if not lost:
                wins += 1.0 / (ties + 1)
            n += 1
        if _perf() >= deadline:
            break
        if n >= 40 and (n & 15) == 0:
            pe = wins / n
            se = (max(pe * (1.0 - pe), 0.02) / n) ** 0.5 * 2.5
            clear = True
            for t in thr:
                if abs(pe - t) < se:
                    clear = False
                    break
            if clear:
                break
    return wins / n, n


# warm the code paths once at import
_sim((0, 5), (9, 14, 22), 2, [0, 0], [0.5], 0.002, _perf())


# ------------------------------------------------------------------ the bot
_STYLE_ON = False   # per-seat aggression tracking: built, then switched off after it lost points in our own sims


class Bot(Agent):
    def __init__(self):
        self.table_seat = None
        self.n_players = 8
        self._reset_stats()

    def _reset_stats(self):
        self.stats = {}        # seat -> [aggressive actions, actions seen] over earlier hands at this table
        self._hn = None
        self._last_hist = ()

    def new_table(self, rules=None, seat=None, n_players=None):
        self.table_seat = seat
        self.n_players = n_players or 8
        self._reset_stats()

    def _ingest(self, hist, bb):
        for item in hist:
            try:
                s, a = item
                if not isinstance(a[0], str):
                    continue
                if a[0] == 'raise' and a[1] <= bb:
                    continue
                st = self.stats.setdefault(s, [0, 0])
                st[1] += 1
                if a[0] == 'raise':
                    st[0] += 1
            except Exception:
                pass

    def _style(self, seat):
        """-1 = loose-aggressive (raises are cheap), 0 = unknown/normal, +1 = tight (raises are real)."""
        if not _STYLE_ON:
            return 0
        st = self.stats.get(seat)
        if not st or st[1] < 14:
            return 0
        r = st[0] / float(st[1])
        if r >= 0.40:
            return -1
        if r <= 0.08:
            return 1
        return 0

    def hand_end(self, result=None):
        pass

    # --------------------------------------------------------------
    def act(self, obs):
        t0 = _perf()
        try:
            a = self._act(obs, t0)
        except Exception:
            return self._fallback(obs)
        try:
            return self._sanitize(a, obs)
        except Exception:
            return self._fallback(obs)

    def _fallback(self, obs):
        try:
            legal = set(obs.legal)
        except Exception:
            return ('fold', 0)
        if 'check' in legal:
            return ('check', 0)
        if 'fold' in legal:
            return ('fold', 0)
        if 'call' in legal:
            return ('call', 0)
        return ('fold', 0)

    def _sanitize(self, a, obs):
        legal = set(obs.legal)
        kind, amt = a
        if kind == 'raise':
            if 'raise' not in legal:
                kind = 'call' if 'call' in legal else 'check'
            else:
                lo = min(obs.min_raise, obs.max_raise)
                hi = max(obs.min_raise, obs.max_raise)
                amt = int(max(lo, min(hi, amt)))
                return ('raise', amt)
        if kind == 'call' and 'call' not in legal:
            kind = 'check' if 'check' in legal else 'fold'
        if kind == 'check' and 'check' not in legal:
            kind = 'call' if 'call' in legal else 'fold'
        if kind == 'fold' and 'fold' not in legal:
            kind = 'check' if 'check' in legal else 'call'
        if kind not in legal:
            return self._fallback(obs)
        return (kind, 0)

    # --------------------------------------------------------------
    def _act(self, obs, t0):
        hole = tuple(obs.hole)
        board = tuple(obs.board or ())
        legal = set(obs.legal)
        seat = obs.seat
        stacks = obs.stacks
        in_hand = obs.in_hand
        n = len(in_hand) if in_hand is not None else len(stacks)
        bets = list(obs.bets) if obs.bets is not None else [0] * n
        if len(bets) < n:
            bets = bets + [0] * (n - len(bets))
        try:
            bb = obs.blinds[1]
        except Exception:
            bb = 20
        bb = max(1, bb or 20)
        try:
            hn = obs.hand_no
            if hn != self._hn:
                self._ingest(self._last_hist, bb)
                self._hn = hn
            self._last_hist = list(obs.history or ())
        except Exception:
            pass
        pot = obs.pot or 0
        to_call = max(0, obs.to_call or 0)
        mx = max(bets) if bets else 0
        mybet = bets[seat] if 0 <= seat < len(bets) else 0
        mystack = stacks[seat]
        pot_total = pot + sum(bets)
        if in_hand is not None:
            opps = [i for i, v in enumerate(in_hand) if v and i != seat]
        else:
            opps = [i for i, s in enumerate(stacks[:n]) if i != seat and (s > 0 or bets[i] > 0)]
        if not opps:
            opps = [(seat + 1) % max(n, 2)]
        opps = opps[:7]
        n_opp = len(opps)
        lo = min(obs.min_raise, obs.max_raise)
        hi = max(obs.min_raise, obs.max_raise)
        can_raise = 'raise' in legal
        if can_raise and not any(stacks[i] > 0 for i in opps if 0 <= i < len(stacks)):
            can_raise = False       # everyone else is all-in: a raise can't get called
        # aggression per opponent from the hand history (raises by seat), total raises by others
        rc = {}
        raises = 0
        last_raiser = None
        try:
            for item in (obs.history or ()):
                try:
                    s, a = item
                    if s != seat and a[0] == 'raise' and a[1] > bb:   # ignore blind posts shown as raises
                        raises += 1
                        rc[s] = rc.get(s, 0) + 1
                        last_raiser = s
                except Exception:
                    pass
        except Exception:
            pass

        f = 1.0 / (n_opp + 1)
        nboard = len(board)
        eff = mystack + mybet           # my total commitment cap this street
        # --------- preflop (table lookup)
        if nboard == 0:
            eq = _pf_eq(hole[0], hole[1], n_opp)
            facing_raise = mx > bb
            if not facing_raise:
                frac = (0.60, 0.60, 0.40, 0.30, 0.25, 0.20, 0.18, 0.17)[n_opp]
                if eff <= 6 * bb: frac = min(1.0, frac * 2.2)
                elif eff <= 10 * bb: frac = min(1.0, frac * 1.7)
                elif eff <= 15 * bb: frac = min(1.0, frac * 1.3)
                if can_raise and eq >= _boundary(n_opp, frac):
                    limpers = sum(1 for b in bets if b == bb) - 1
                    target = bb * 3 + bb * max(0, limpers)
                    if eff <= 12 * bb or target >= 0.35 * eff:
                        target = hi
                    return ('raise', target)
                if to_call == 0:
                    return ('check', 0)
                need = to_call / float(pot_total + to_call)
                if eq > need + 0.06 and to_call <= 2 * bb:
                    return ('call', 0)
                return ('fold', 0)
            need = to_call / float(pot_total + to_call)
            lv = 1 if raises <= 1 else 2
            if mx >= 8 * bb and lv == 1:
                lv = 2
            sty = self._style(last_raiser) if last_raiser is not None else 0
            if sty < 0:
                eqr = eq                      # a loose-aggressive raiser: treat the range as random hands
            else:
                if sty > 0 and lv == 1:
                    lv = 2
                eqr = _pfr_eq(hole[0], hole[1], lv, n_opp)
            fr = (0.07 if lv == 1 else 0.03)
            if eff <= 25 * bb:
                fr *= 1.6
            if can_raise and eqr >= _rboundary(lv, n_opp, min(fr, 0.30)) and raises <= 2:
                target = mx * 3
                if eff <= 25 * bb or target >= 0.4 * eff:
                    target = hi
                return ('raise', target)
            if eqr > need + 0.035 + 0.02 * min(raises, 3):
                return ('call', 0)
            return ('fold', 0)
        # --------- postflop: Monte Carlo
        tl = []
        for i in opps:
            lv = min(2, rc.get(i, 0))
            if bets[i] > 0 and lv < 1:
                lv = 1
            if bets[i] > 0.75 * max(1, pot) and lv < 2 and bets[i] > bb * 2:
                lv = 2
            if lv:
                sty = self._style(i)
                if sty < 0:
                    lv -= 1
                elif sty > 0 and lv < 2:
                    lv += 1
            tl.append(lv)
        need = to_call / float(pot_total + to_call) if to_call > 0 else 0.0
        bf = to_call / float(max(1, pot_total - to_call))
        margin = 0.06 + 0.06 * min(2.0, bf)
        thr = []
        if to_call == 0:
            thr.append(f + 0.30 * (1 - f)); thr.append(f + 0.55 * (1 - f))
        else:
            thr.append(need + margin); thr.append(f + 0.62 * (1 - f))
        eq, _n = _sim(hole, board, n_opp, tl, thr, 0.00018, t0)
        strength = (eq - f) / (1.0 - f)
        if to_call == 0:
            if can_raise and strength >= 0.30:
                frac = 0.5 if strength < 0.55 else 0.75
                target = mybet + int(pot_total * frac)
                if target >= 0.5 * eff:
                    target = hi
                return ('raise', target)
            return ('check', 0)
        if can_raise and strength >= 0.62 and raises <= 2:
            target = mx + int(pot_total + to_call)
            if target >= 0.5 * eff:
                target = hi
            return ('raise', target)
        if eq > need + margin:
            return ('call', 0)
        return ('fold', 0)
