"""rival_bot.py -- one-file no-limit hold'em sit-and-go bot. Standard library only.

Built in a 60-minute window for the 8-max, 2,000-chip, 200-hand-cap format with a 1 ms decision
budget. Everything expensive happens at import (about 0.3 s): a 5/6/7-card evaluator built from a
rank-multiset prime-product table and flush/straight bitmask tables, a 169-class preflop table turned
into percentile rankings, and a warm-up pass over every code path followed by gc.freeze(). act() is
table lookups and arithmetic (typically 15-25 us, no search, no sampling) and is wrapped so that any
failure degrades to a legal check/fold; every action goes through a legalizer.

Strategy:
  * Preflop: position-aware opening percentiles, 3-bet premiums, set-mining only when cheap, a
    Nash-shaped push/fold fraction f(stack_bb, players behind) below ~10-12bb, and shove-calling from
    an estimate of the shover's range (stack depth, position, callers, players still to act).
  * Postflop: made-hand equity estimate from category and board texture, outs-based draw equity,
    multiway exponent, street-scaled respect for aggression on weak hands, pot-odds calls with
    implied-odds and stack-off guards, 2/3-pot value bets, shoves when committed.
  * Tournament: ICM-style tightening when much shorter stacks are present or the cap is near; near the
    cap a stack that can pay the blinds to hand 200 folds its way into the ICM payout.
  * Opponents: per-seat VPIP / PFR / fold-to-raise / aggression from obs.history -> folder, station,
    maniac, nit flags that widen steals, thin value bets, slow-plays, and shove-calling ranges.
"""
import itertools
import math
import random

# ----------------------------------------------------------------------------------------------
# Hand evaluator. Cards are ints rank*4+suit, rank 0=2 .. 12=A. Value: category*K + kickers.
# ----------------------------------------------------------------------------------------------
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
K = 13 ** 5  # category stride

STRAIGHT_HIGH = [-1] * 8192
for _m in range(8192):
    _best = -1
    for _top in range(12, 3, -1):
        _need = 0b11111 << (_top - 4)
        if _m & _need == _need:
            _best = _top
            break
    if _best < 0 and (_m & 0b1000000001111) == 0b1000000001111:
        _best = 3  # wheel
    STRAIGHT_HIGH[_m] = _best


def _top_bits(m, k):
    out = []
    for r in range(12, -1, -1):
        if m >> r & 1:
            out.append(r)
            if len(out) == k:
                break
    return out


FLUSH_VAL = [0] * 8192
for _m in range(8192):
    if bin(_m).count('1') >= 5:
        _st = STRAIGHT_HIGH[_m]
        if _st >= 0:
            FLUSH_VAL[_m] = 8 * K + _st
        else:
            _t = _top_bits(_m, 5)
            FLUSH_VAL[_m] = 5 * K + _t[0] * 28561 + _t[1] * 2197 + _t[2] * 169 + _t[3] * 13 + _t[4]


def _nonflush_value(ranks):
    cnt = [0] * 13
    for r in ranks:
        cnt[r] += 1
    quads = trips = -1
    pairs = []
    mask = 0
    for r in range(12, -1, -1):
        c = cnt[r]
        if not c:
            continue
        mask |= 1 << r
        if c == 4:
            quads = r
        elif c == 3:
            if trips < 0:
                trips = r
            else:
                pairs.append(r)
        elif c == 2:
            pairs.append(r)
    if quads >= 0:
        k = max(r for r in range(13) if cnt[r] and r != quads)
        return 7 * K + quads * 13 + k
    if trips >= 0 and pairs:
        return 6 * K + trips * 13 + pairs[0]
    st = STRAIGHT_HIGH[mask]
    if st >= 0:
        return 4 * K + st
    if trips >= 0:
        ks = [r for r in range(12, -1, -1) if cnt[r] and r != trips][:2]
        return 3 * K + trips * 169 + ks[0] * 13 + ks[1]
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        k = max(r for r in range(13) if cnt[r] and r != p1 and r != p2)
        return 2 * K + p1 * 169 + p2 * 13 + k
    if pairs:
        p = pairs[0]
        ks = [r for r in range(12, -1, -1) if cnt[r] and r != p][:3]
        return K + p * 2197 + ks[0] * 169 + ks[1] * 13 + ks[2]
    ks = _top_bits(mask, 5)
    return ks[0] * 28561 + ks[1] * 2197 + ks[2] * 169 + ks[3] * 13 + ks[4]


NONFLUSH = {}
for _k in (5, 6, 7):
    for _combo in itertools.combinations_with_replacement(range(13), _k):
        if any(_combo[i] == _combo[i - 4] for i in range(4, _k)):
            continue
        _p = 1
        for _r in _combo:
            _p *= PRIMES[_r]
        NONFLUSH[_p] = _nonflush_value(_combo)


def evaluate(cards):
    """Best 5-card value of 5, 6 or 7 cards. Higher is better."""
    p = 1
    sc = [0, 0, 0, 0]
    sm = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        s = c & 3
        p *= PRIMES[r]
        sc[s] += 1
        sm[s] |= 1 << r
    v = NONFLUSH[p]
    if sc[0] >= 5:
        f = FLUSH_VAL[sm[0]]
    elif sc[1] >= 5:
        f = FLUSH_VAL[sm[1]]
    elif sc[2] >= 5:
        f = FLUSH_VAL[sm[2]]
    elif sc[3] >= 5:
        f = FLUSH_VAL[sm[3]]
    else:
        return v
    return f if f > v else v


# ----------------------------------------------------------------------------------------------
# Preflop: heads-up equity vs a random hand for the 169 classes (from memory, standard table),
# turned into two percentiles: PCT_HU (pure showdown value, for all-in spots) and PCT_PLAY
# (with a playability bonus for suited / connected / small pairs, for opens and calls).
# ----------------------------------------------------------------------------------------------
_HU = """
AA 85.2 KK 82.4 QQ 79.9 JJ 77.5 TT 75.1 99 72.1 88 69.1 77 66.2 66 63.3 55 60.3 44 57.0 33 53.7 22 50.3
AKs 67.0 AQs 66.1 AJs 65.4 ATs 64.7 A9s 63.0 A8s 62.1 A7s 61.1 A6s 60.0 A5s 59.9 A4s 58.9 A3s 58.0 A2s 57.0
AKo 65.4 AQo 64.5 AJo 63.6 ATo 62.9 A9o 60.9 A8o 60.1 A7o 59.1 A6o 57.8 A5o 57.7 A4o 56.4 A3o 55.6 A2o 54.6
KQs 63.4 KJs 62.6 KTs 61.9 K9s 60.0 K8s 58.5 K7s 57.8 K6s 56.8 K5s 55.8 K4s 54.7 K3s 53.8 K2s 52.9
KQo 61.4 KJo 60.6 KTo 59.9 K9o 58.0 K8o 56.3 K7o 55.4 K6o 54.3 K5o 53.3 K4o 52.1 K3o 51.2 K2o 50.2
QJs 60.3 QTs 59.5 Q9s 57.9 Q8s 56.2 Q7s 54.5 Q6s 53.8 Q5s 52.9 Q4s 51.7 Q3s 50.7 Q2s 49.9
QJo 58.2 QTo 57.4 Q9o 55.5 Q8o 53.8 Q7o 51.9 Q6o 51.1 Q5o 50.2 Q4o 49.0 Q3o 47.9 Q2o 47.0
JTs 57.5 J9s 55.8 J8s 54.2 J7s 52.4 J6s 50.8 J5s 50.0 J4s 49.0 J3s 47.9 J2s 47.1
JTo 55.4 J9o 53.4 J8o 51.7 J7o 49.9 J6o 47.9 J5o 47.1 J4o 46.1 J3o 44.9 J2o 44.0
T9s 54.3 T8s 52.6 T7s 51.0 T6s 49.2 T5s 47.2 T4s 46.4 T3s 45.5 T2s 44.7
T9o 51.7 T8o 50.0 T7o 48.2 T6o 46.3 T5o 44.2 T4o 43.4 T3o 42.4 T2o 41.5
98s 51.1 97s 49.5 96s 47.7 95s 45.9 94s 43.8 93s 43.2 92s 42.3
98o 48.4 97o 46.7 96o 44.9 95o 42.9 94o 40.7 93o 40.0 92o 39.1
87s 48.2 86s 46.5 85s 44.8 84s 42.7 83s 40.8 82s 40.3
87o 45.5 86o 43.6 85o 41.7 84o 39.6 83o 37.5 82o 37.0
76s 45.7 75s 43.8 74s 41.8 73s 40.0 72s 38.1
76o 42.7 75o 40.8 74o 38.6 73o 36.6 72o 34.6
65s 43.2 64s 41.4 63s 39.4 62s 37.5
65o 40.1 64o 38.0 63o 35.9 62o 33.9
54s 41.1 53s 39.3 52s 37.5
54o 37.9 53o 35.8 52o 33.9
43s 38.0 42s 36.3
43o 34.4 42o 32.5
32s 35.1
32o 31.2
"""
_RC = '23456789TJQKA'
EQ_HU = {}
_tok = _HU.split()
for _i in range(0, len(_tok), 2):
    _name, _e = _tok[_i], float(_tok[_i + 1])
    _hi, _lo = _RC.index(_name[0]), _RC.index(_name[1])
    _s = 1 if len(_name) == 3 and _name[2] == 's' else 0
    EQ_HU[(_hi, _lo, _s)] = _e
assert len(EQ_HU) == 169


def _play_score(hi, lo, s):
    e = EQ_HU[(hi, lo, s)]
    if hi == lo:
        return e + (1.5 if hi <= 6 else 0.5)
    gap = hi - lo - 1
    b = 1.2 if s else 0.0
    if gap == 0:
        b += 1.0
    elif gap == 1:
        b += 0.6
    elif gap == 2:
        b += 0.3
    if not s and hi >= 9 and lo <= 4:
        b -= 1.2  # K4o-type and ace-rag offsuit: dominated, no playability
    return e + b


def _percentiles(score):
    items = [(score(h, l, s), 6 if h == l else (4 if s else 12), (h, l, s)) for (h, l, s) in EQ_HU]
    items.sort()
    out = {}
    below = 0
    i = 0
    while i < len(items):
        j = i
        same = 0
        while j < len(items) and items[j][0] == items[i][0]:
            same += items[j][1]
            j += 1
        for t in range(i, j):
            out[items[t][2]] = (below + same * 0.5) / 1326.0
        below += same
        i = j
    return out


PCT_HU = _percentiles(lambda h, l, s: EQ_HU[(h, l, s)])
PCT_PLAY = _percentiles(_play_score)


def hand_key(hole):
    a, b = hole[0], hole[1]
    r1, r2 = a >> 2, b >> 2
    if r1 < r2:
        r1, r2 = r2, r1
    return (r1, r2, 1 if (r1 != r2 and (a & 3) == (b & 3)) else 0)


# Nash-shaped push fraction: stack in big blinds, players still to act behind the pusher.
def f_push(bb, nb):
    nb = max(1, nb)
    f = 1.15 * math.exp(-0.065 * bb) * (0.77 ** (nb - 1))
    if bb <= 4:
        f = max(f, 0.55 - 0.05 * nb)
    return max(0.02, min(1.0, f))


F_OPEN = {0: 0.25, 1: 0.50, 2: 0.42, 3: 0.30, 4: 0.24, 5: 0.19, 6: 0.16, 7: 0.13}


# ----------------------------------------------------------------------------------------------
# Postflop hand reading: made-hand equity estimate + draw outs, from category and board texture.
# ----------------------------------------------------------------------------------------------
def analyze(hole, board):
    cards = tuple(hole) + tuple(board)
    v = evaluate(cards)
    cat = v // K
    h1, h2 = hole[0], hole[1]
    r1, r2, s1, s2 = h1 >> 2, h2 >> 2, h1 & 3, h2 & 3
    if r1 < r2:
        r1, r2, s1, s2 = r2, r1, s2, s1
    pocket = r1 == r2
    bcnt = [0] * 13
    bsuit = [0, 0, 0, 0]
    bmask = 0
    for c in board:
        r = c >> 2
        bcnt[r] += 1
        bsuit[c & 3] += 1
        bmask |= 1 << r
    branks = _top_bits(bmask, 2)
    bmax = branks[0]
    b2 = branks[1] if len(branks) > 1 else -1
    nb = len(board)
    pair_on_board = max(bcnt) >= 2
    wet3 = max(bsuit) >= 3
    wet4 = max(bsuit) >= 4

    if cat >= 7:
        made = 0.97
    elif cat == 6:
        made = 0.92 if (pocket or bcnt[r1] == 1 or bcnt[r2] == 1) else 0.85
    elif cat == 5:
        fs = s1 if (bsuit[s1] + (s1 == s1) + (s2 == s1)) >= 5 else s2
        hold = [r for (r, s) in ((r1, s1), (r2, s2)) if s == fs]
        bmaxs = max([c >> 2 for c in board if (c & 3) == fs] or [-1])
        if bsuit[fs] >= 5 and (not hold or max(hold) < bmaxs):
            made = 0.30
        else:
            top = max(hold)
            if bsuit[fs] == 4:
                made = 0.35 + 0.045 * top  # one-card flush: any higher card of the suit beats us
            else:
                made = 0.90 if top == 12 else (0.84 if top >= 10 else 0.76)
            if pair_on_board:
                made -= 0.06
    elif cat == 4:
        if STRAIGHT_HIGH[bmask] >= v - 4 * K:
            made = 0.30
        else:
            made = 0.84
            if wet3:
                made -= 0.10
            if pair_on_board:
                made -= 0.07
    elif cat == 3:
        if pocket:
            made = 0.88 if not (wet3 or pair_on_board) else 0.82
        elif bcnt[r1] == 2 or bcnt[r2] == 2:
            kick = r2 if bcnt[r1] == 2 else r1
            made = 0.76 + (0.04 if kick >= 10 else (-0.06 if kick <= 7 else 0.0))
        else:
            made = 0.45 if r1 == 12 else 0.33
    elif cat == 2:
        if not pocket and bcnt[r1] == 1 and bcnt[r2] == 1:
            made = 0.80 if r1 == bmax else 0.73
        elif pocket:
            if sum(1 for r in range(13) if bcnt[r] >= 2 and r > r1) >= 2:
                made = 0.22  # board two pair outranks our pocket pair: we play the board
            else:
                made = 0.66 if r1 > bmax else 0.48
        elif bcnt[r1] == 1 or bcnt[r2] == 1:
            pr = r1 if bcnt[r1] == 1 else r2
            made = 0.60 if pr == bmax else 0.46
        else:
            made = 0.26 if r1 == 12 else 0.2
    elif cat == 1:
        if pocket:
            if r1 > bmax:
                made = 0.72 - 0.03 * (nb - 3)
            elif r1 > b2:
                made = 0.50
            else:
                made = 0.40
        elif bcnt[r1] == 1 or bcnt[r2] == 1:
            pr, kick = (r1, r2) if bcnt[r1] == 1 else (r2, r1)
            if pr == bmax:
                made = 0.60 + (0.08 if kick == 12 else (0.05 if kick >= 10 else (0.0 if kick >= 7 else -0.05)))
                if wet3 or pair_on_board:
                    made -= 0.02 * (nb - 3)
            elif pr >= b2:
                made = 0.44
            else:
                made = 0.34
        else:
            made = 0.24 if r1 == 12 else 0.18
    else:
        made = 0.21 if r1 == 12 else (0.15 if r1 == 11 else 0.10)
    if cat < 5:
        if wet4:
            made *= 0.6
        elif wet3 and cat <= 2:
            made *= 0.9

    outs = 0.0
    fd = False
    if cat < 5 and nb < 5:
        for s in range(4):
            tot = bsuit[s] + (s1 == s) + (s2 == s)
            if tot == 4 and (s1 == s or s2 == s):
                fd = True
                outs += 9 if (s1 == s and s2 == s) else 6.5
                if (s1 == s and r1 == 12) or (s2 == s and r2 == 12):
                    outs += 1
        if cat < 4:
            allm = bmask | (1 << r1) | (1 << r2)
            so = 0
            for r in range(13):
                if allm >> r & 1:
                    continue
                if STRAIGHT_HIGH[allm | (1 << r)] >= 0 and STRAIGHT_HIGH[bmask | (1 << r)] < 0:
                    so += 1
            outs += so * (3.3 if fd else 4.0)
        if cat == 0:
            if r2 > bmax:
                outs += 3.0  # two overcards, half weight
            elif r1 == 12 and r1 > bmax:
                outs += 1.5
        elif cat == 1 and not pocket:
            outs += 1.5  # trips / two pair outs, low weight
    draw1 = min(0.45, outs * 0.0217) if nb < 5 else 0.0
    draw2 = min(0.62, outs * 0.04 - max(0.0, outs - 8) * 0.006) if nb == 3 else draw1
    return made, draw1, draw2, cat, fd


# ----------------------------------------------------------------------------------------------
# The bot.
# ----------------------------------------------------------------------------------------------
class Bot(object):
    debug = False  # set True in tests to surface exceptions that act() would otherwise swallow
    OPEN_SCALE = 1.0
    PUSH_SCALE = 1.0
    CAP_MODE = True
    ROR_DEEP = 0.05  # slice of a shover's range we stack off with when >50bb deep and not heads-up

    def __init__(self):
        self.new_table({}, 0, 8)

    # ---- lifecycle ----
    def new_table(self, rules, seat, n_players):
        self.rules = rules if isinstance(rules, dict) else {}
        self.seat = seat
        try:
            self.cap = int(self.rules.get('hand_cap', 200))
        except Exception:
            self.cap = 200
        n = n_players if isinstance(n_players, int) and n_players > 0 else 8
        self.stats = [dict(hands=0, vpip=0, pfr=0, faced=0, foldr=0, agg=0, pas=0, pbf=0, pbfold=0)
                      for _ in range(max(2, n))]
        self._hand_no = None
        self._seen = 0
        self._pre_raised = False
        self._vp = set()
        self._pfa = None
        self._post_bet = False
        self._last_street = 0
        self.rng = random.Random(7)

    def hand_end(self, result):
        return None  # everything we use is reconstructed from obs.history during act()

    # ---- entry ----
    def act(self, obs):
        try:
            a = self._decide(obs)
        except Exception:
            if self.debug:
                raise
            a = None
        return self._legalize(obs, a)

    def _legalize(self, obs, a):
        try:
            legal = set(obs.legal or ())
        except Exception:
            legal = set()
        kind, amt = None, 0
        try:
            kind, amt = a[0], a[1]
        except Exception:
            kind = None
        if kind == 'raise':
            if 'raise' in legal:
                try:
                    lo, hi = int(obs.min_raise), int(obs.max_raise)
                    if lo > hi:
                        lo = hi
                    amt = int(round(float(amt)))
                    return ('raise', max(lo, min(amt, hi)))
                except Exception:
                    pass
            kind = 'call'
        if kind == 'fold' and 'check' in legal:
            kind = 'check'
        if kind in legal and kind != 'raise':
            return (kind, 0)
        if 'check' in legal:
            return ('check', 0)
        if kind == 'call' and 'fold' in legal:
            return ('fold', 0)
        if 'fold' in legal:
            return ('fold', 0)
        if 'call' in legal:
            return ('call', 0)
        return ('fold', 0)

    # ---- opponent model, fed from obs.history ----
    def _update_model(self, obs):
        hist = obs.history or []
        n_stats = len(self.stats)
        if len(obs.stacks or []) > n_stats:
            self.stats.extend(dict(hands=0, vpip=0, pfr=0, faced=0, foldr=0, agg=0, pas=0, pbf=0, pbfold=0)
                              for _ in range(len(obs.stacks) - n_stats))
            n_stats = len(self.stats)
        if len(hist) < self._seen and obs.hand_no == self._hand_no:
            self._seen = 0  # kit hands us per-street history: start the window over, same hand
        if obs.hand_no != self._hand_no:
            self._hand_no = obs.hand_no
            self._seen = 0
            self._pre_raised = False
            self._vp = set()
            self._pfa = None
            self._post_bet = False
            self._last_street = 0
            stacks = obs.stacks or []
            inh = obs.in_hand or []
            for i in range(min(n_stats, len(stacks))):
                if stacks[i] > 0 or (i < len(inh) and inh[i]):
                    self.stats[i]['hands'] += 1
        if obs.street != self._last_street:
            # Entries unseen at a street change: the tail (one action per live opponent who acts
            # before us this street) belongs to the new street, the rest to the previous one.
            new = hist[self._seen:]
            n = len(obs.stacks)
            me = obs.seat
            mypos = (me - obs.button - 1) % n
            m = sum(1 for i in range(n) if i != me and i < len(obs.in_hand or []) and obs.in_hand[i]
                    and obs.stacks[i] > 0 and ((i - obs.button - 1) % n) < mypos)
            split = max(0, len(new) - m)
            self._consume(new[:split], self._last_street == 0, n_stats)
            self._seen += split
            self._post_bet = False
            self._last_street = obs.street
        self._consume(hist[self._seen:], obs.street == 0, n_stats)
        self._seen = len(hist)

    def _consume(self, entries, pre, n_stats):
        for ent in entries:
            try:
                seat, a = ent[0], ent[1]
                k = a[0] if isinstance(a, (tuple, list)) else a
            except Exception:
                continue
            if not isinstance(seat, int) or not (0 <= seat < n_stats):
                continue
            S = self.stats[seat]
            if pre:
                if k == 'raise':
                    if self._pre_raised:
                        S['faced'] += 1
                    S['pfr'] += 1
                    self._pre_raised = True
                    self._pfa = seat
                    if seat not in self._vp:
                        self._vp.add(seat)
                        S['vpip'] += 1
                elif k == 'call':
                    if self._pre_raised:
                        S['faced'] += 1
                    if seat not in self._vp:
                        self._vp.add(seat)
                        S['vpip'] += 1
                elif k == 'fold':
                    if self._pre_raised:
                        S['faced'] += 1
                        S['foldr'] += 1
            else:
                if k == 'raise':
                    S['agg'] += 1
                    if self._post_bet:
                        S['pbf'] += 1
                    self._post_bet = True
                elif k == 'call':
                    S['pas'] += 1
                    S['pbf'] += 1
                elif k == 'fold':
                    S['pbf'] += 1
                    S['pbfold'] += 1

    def _profile(self, i):
        S = self.stats[i] if 0 <= i < len(self.stats) else None
        if S is None:
            return {}
        h = S['hands']
        vpip = S['vpip'] / h if h >= 8 else None
        pfr = S['pfr'] / h if h >= 8 else None
        ftr = S['foldr'] / S['faced'] if S['faced'] >= 6 else None
        ap = S['agg'] + S['pas']
        agg = S['agg'] / ap if ap >= 8 else None
        ftb = S['pbfold'] / S['pbf'] if S['pbf'] >= 6 else None
        return dict(
            vpip=vpip, pfr=pfr, ftr=ftr, agg=agg, ftb=ftb,
            station=(vpip is not None and vpip >= 0.55 and (agg is None or agg < 0.6)),
            maniac=((pfr is not None and pfr >= 0.35) or (agg is not None and agg >= 0.7 and (vpip or 0) >= 0.4)),
            folder=((ftr is not None and ftr >= 0.75) or (ftb is not None and ftb >= 0.65)),
            nit=(vpip is not None and vpip <= 0.14 and h >= 15),
        )

    # ---- shared context ----
    def _ctx(self, obs):
        c = {}
        n = len(obs.stacks)
        me = obs.seat
        sb, bb = obs.blinds if obs.blinds else (10, 20)
        bb = max(1, int(bb))
        stacks = obs.stacks
        bets = obs.bets if obs.bets else [0] * n
        inh = obs.in_hand if obs.in_hand else [True] * n
        opps = [i for i in range(n) if i != me and i < len(inh) and inh[i]]
        c['n'] = n
        c['me'] = me
        c['bb'] = bb
        c['stack'] = stacks[me]
        c['my_bet'] = bets[me] if me < len(bets) else 0
        c['opps'] = opps
        c['n_opp'] = max(1, len(opps))
        mine = c['stack'] + c['my_bet']
        pot_total = (obs.pot or 0) + sum(min(b, mine) for b in bets)  # chips above our stack are not winnable
        c['pot_total'] = pot_total
        tc = obs.to_call or 0
        c['to_call'] = tc
        c['price'] = tc / float(pot_total + tc) if tc > 0 else 0.0
        opp_tot = max([stacks[i] + (bets[i] if i < len(bets) else 0) for i in opps] or [mine])
        c['eff'] = min(mine, opp_tot)
        c['eff_bb'] = c['eff'] / float(bb)
        c['my_bb'] = mine / float(bb)
        alive = [stacks[i] + (bets[i] if i < len(bets) else 0) for i in range(n)
                 if stacks[i] > 0 or (i < len(inh) and inh[i])]
        c['n_alive'] = max(2, len(alive))
        c['avg'] = sum(alive) / float(len(alive)) if alive else mine
        others = [stacks[i] + (bets[i] if i < len(bets) else 0) for i in range(n) if i != me and stacks[i] > 0]
        c['short_other_bb'] = (min(others) / float(bb)) if others else 99.0
        c['hands_left'] = self.cap - (obs.hand_no or 0)
        # ICM / survival pressure: someone much shorter than us is about to bust, or the cap is near
        c['icm_tight'] = (c['my_bb'] >= 8 and c['short_other_bb'] < 0.5 * c['my_bb'] and c['n_alive'] >= 3) or \
                         (c['hands_left'] <= 12 and mine >= c['avg'])
        # Hand cap: survivors are paid by ICM, busted players get 0. If the blinds between now and the
        # cap cost less than our stack, fold our way there and only play premium hands.
        blind_cost_bb = 1.5 * c['hands_left'] / float(c['n_alive']) + 1.0
        c['cap_mode'] = self.CAP_MODE and 0 < c['hands_left'] <= 20 and c['n_alive'] >= 3 and c['my_bb'] >= 1.4 * blind_cost_bb
        return c

    def _raise_to(self, obs, total):
        return ('raise', int(total))

    # ---- decision ----
    def _decide(self, obs):
        self._update_model(obs)
        if obs.street == 0 or not obs.board:
            return self._preflop(obs)
        return self._postflop(obs)

    def _preflop(self, obs):
        c = self._ctx(obs)
        me, bb = c['me'], c['bb']
        key = hand_key(obs.hole)
        pct = PCT_PLAY[key]
        pct_hu = PCT_HU[key]
        hist = obs.history or []
        acts = []
        for ent in hist:
            try:
                s, a = ent[0], ent[1]
                k = a[0] if isinstance(a, (tuple, list)) else a
            except Exception:
                continue
            if k in ('fold', 'check', 'call', 'raise'):
                acts.append((s, k))
        raises = [i for i, (s, k) in enumerate(acts) if k == 'raise']
        n_raises = len(raises)
        acted = set(s for s, k in acts)
        behind = [i for i in c['opps'] if i not in acted]
        n_behind = len(behind)
        limpers = sum(1 for s, k in acts if k == 'call' and s != me) if n_raises == 0 else 0
        i_raised = any(s == me and k == 'raise' for s, k in acts)
        to_call, stack, my_bet = c['to_call'], c['stack'], c['my_bet']
        eff_bb = c['eff_bb']
        can_raise = 'raise' in obs.legal
        shove = ('raise', obs.max_raise)

        # exploit: how often do the players behind fold to a raise?
        steal_mult = 1.0
        if behind:
            profs = [self._profile(i) for i in behind]
            if any(p.get('maniac') for p in profs):
                steal_mult = 0.45  # a maniac behind will shove on us: open only what can stand it
            elif all(p.get('folder') or p.get('nit') for p in profs):
                steal_mult = 1.6
            elif any(p.get('station') for p in profs):
                steal_mult = 0.85

        cap = 0.4 if c['cap_mode'] else 1.0

        # --- free option in the big blind (limped pot) ---
        if to_call <= 0:
            if can_raise:
                if eff_bb <= 10 and pct_hu >= 1.0 - f_push(eff_bb, c['n_opp']):
                    return shove
                if pct >= 0.80:
                    return self._raise_to(obs, (3 + limpers) * bb)
            return ('check', 0)

        # --- unopened or limped pot ---
        if n_raises == 0:
            if not can_raise:
                return ('call', 0) if c['price'] < 0.4 and pct_hu >= 0.3 else ('fold', 0)
            push_mode = eff_bb <= 10 or (eff_bb <= 12.5 and n_behind <= 2)
            if push_mode:
                f = f_push(eff_bb, n_behind + limpers) * steal_mult * cap * self.PUSH_SCALE
                if limpers:
                    f *= 0.75
                return shove if pct_hu >= 1.0 - f else ('fold', 0)
            f = F_OPEN.get(min(n_behind + limpers, 7), 0.12) * steal_mult * (0.7 if c['cap_mode'] else 1.0) * self.OPEN_SCALE
            if limpers:
                f *= 0.75
            if c['icm_tight'] and n_behind >= 3:
                f *= 0.85
            if pct >= 1.0 - f or (eff_bb <= 16 and pct_hu >= 1.0 - f * 0.9):
                mult = 2.5 if eff_bb > 30 else (2.2 if eff_bb > 16 else 2.0)
                return self._raise_to(obs, (mult + limpers) * bb)
            return ('fold', 0)

        # --- facing a raise ---
        last_r = acts[raises[-1]][0]
        callers_after = sum(1 for s, k in acts[raises[-1] + 1:] if k == 'call')
        rp = self._profile(last_r) if isinstance(last_r, int) else {}
        raiser_allin = isinstance(last_r, int) and 0 <= last_r < c['n'] and obs.stacks[last_r] == 0
        committing = raiser_allin or to_call >= 0.4 * stack or (stack - to_call) <= 0.4 * c['pot_total']
        if committing:
            # Estimate the shover's range from their stack depth and position, then call with the top
            # of our pure-equity ranking against it; tighten for players behind, callers, and ICM.
            p_tot = obs.stacks[last_r] + obs.bets[last_r] if isinstance(last_r, int) and 0 <= last_r < c['n'] else c['eff']
            p_bb = p_tot / float(bb)
            after = len(acts) - raises[-1] - 1
            remaining = len([i for i in c['opps'] if i not in set(s for s, k in acts[raises[-1] + 1:])])
            f_p = f_push(min(p_bb, 25.0), after + remaining)
            if n_raises >= 2:
                f_p *= 0.55
            if not raiser_allin:
                f_p *= 0.8
            if rp.get('maniac'):
                f_p = max(f_p * 1.6, 0.8)  # a maniac's raise is close to a random hand
            elif rp.get('station'):
                f_p = max(f_p * 1.6, 0.55)
            elif rp.get('nit'):
                f_p *= 0.6
            f_p = max(0.03, min(1.0, f_p))
            call_frac = f_p * (0.55 + 1.2 * (0.45 - c['price']))
            call_frac *= 0.78 ** n_behind
            call_frac *= 0.6 ** callers_after
            call_frac *= 0.6 ** max(0, c['n_opp'] - 1 - callers_after)  # others already in the pot
            if p_bb > 30 and not (rp.get('maniac') or rp.get('station')) and c['my_bb'] > 20:
                call_frac = min(call_frac, 0.022)  # a deep open-shove from an unknown: TT+ only
            if c['icm_tight']:
                call_frac *= 0.7
            if to_call >= 0.5 * stack and c['my_bb'] > 15 and c['n_alive'] >= 3:
                # Risk of ruin: the deeper we are, the smaller the slice of their range we stack off with.
                ror = self.ROR_DEEP if c['my_bb'] > 50 else (0.12 if c['my_bb'] > 25 else 0.22)
                call_frac = min(call_frac, f_p * ror)
            call_frac *= cap
            if c['price'] <= 0.12:
                call_frac = max(call_frac, 0.9)
            elif c['price'] <= 0.2:
                call_frac = max(call_frac, 0.7)
            call_frac = max(0.015, min(1.0, call_frac))
            if pct_hu >= 1.0 - call_frac:
                if can_raise and n_behind > 0 and pct_hu >= 0.9 and stack > to_call:
                    return shove
                return ('call', 0)
            return ('fold', 0)

        if n_raises == 1:
            loose = bool(rp.get('maniac') or rp.get('station'))
            three_thr = 0.965 - (0.035 if loose else 0.0)
            if pct_hu >= three_thr and can_raise:
                lvl = max(obs.bets) if obs.bets else 0
                target = lvl * (3.0 if n_behind <= 1 else 3.5) + callers_after * lvl
                if target >= 0.4 * (stack + my_bet):
                    return shove
                return self._raise_to(obs, target)
            # short: re-steal shove or fold
            if eff_bb <= 15:
                f = 0.55 * f_push(eff_bb, n_behind + 1) * (1.3 if loose else 1.0)
                if pct_hu >= 1.0 - f and can_raise:
                    return shove
                if c['price'] <= 0.22 and pct >= 0.5:
                    return ('call', 0)
                return ('fold', 0)
            # re-steal zone: shove over a steal with a decent hand when the raiser is loose or we are last
            if 15 < eff_bb <= 22 and can_raise and (loose or n_behind <= 1):
                f = 0.6 * f_push(eff_bb, n_behind + 1) * (1.3 if loose else 1.0)
                if pct_hu >= 1.0 - f:
                    return shove
            call_thr = 0.80 - max(0.0, 0.35 - c['price']) * 2.0
            if key[2] or key[0] == key[1]:
                call_thr -= 0.05
            if n_behind <= 1:
                call_thr -= 0.05
            else:
                call_thr += 0.03
            if loose:
                call_thr -= 0.08
            if c['icm_tight']:
                call_thr += 0.05
            if c['cap_mode']:
                call_thr += 0.1
            call_thr = max(0.45, min(0.9, call_thr))
            if key[0] == key[1] and to_call <= c['eff'] / 12.0 and my_bet + to_call <= 0.12 * (stack + my_bet):
                return ('call', 0)  # set mine
            if key[2] and key[0] - key[1] <= 2 and n_behind <= 1 and to_call <= c['eff'] / 25.0:
                return ('call', 0)  # suited connector in position, cheap
            if pct >= call_thr:
                return ('call', 0)
            return ('fold', 0)

        # facing a 3-bet or more
        nitty = rp.get('pfr') is not None and rp['pfr'] <= 0.15
        if pct_hu >= (0.99 if nitty else 0.985) or (pct_hu >= 0.985 and eff_bb <= 45):
            if can_raise:
                lvl = max(obs.bets) if obs.bets else 0
                target = lvl * 2.3
                if target >= 0.4 * (stack + my_bet) or eff_bb <= 70:
                    return shove
                return self._raise_to(obs, target)
            return ('call', 0)
        if pct_hu >= 0.965 and c['price'] <= 0.42 and (eff_bb >= 18 or pct_hu >= 0.98) \
                and (to_call <= 0.15 * (stack + my_bet) or pct_hu >= 0.98):
            return ('call', 0)
        if pct_hu >= 0.965 and eff_bb < 18 and can_raise and not nitty:
            return shove
        if pct_hu >= 0.93 and c['price'] <= 0.33 and eff_bb >= 30 and not c['icm_tight'] and not nitty \
                and to_call <= 0.15 * (stack + my_bet):
            return ('call', 0)
        if key[0] == key[1] and to_call <= c['eff'] / 15.0 and my_bet + to_call <= 0.12 * (stack + my_bet):
            return ('call', 0)
        if c['price'] <= 0.12 and pct_hu >= 0.5:
            return ('call', 0)
        return ('fold', 0)

    def _postflop(self, obs):
        c = self._ctx(obs)
        me, bb = c['me'], c['bb']
        street = obs.street
        made, draw1, draw2, cat, fd = analyze(obs.hole, obs.board)
        to_call, stack, my_bet, pot_total = c['to_call'], c['stack'], c['my_bet'], c['pot_total']
        n_opp = c['n_opp']
        bets = obs.bets or []
        levels = len(set(b for b in bets if b > 0))
        facing_raise = to_call > 0 and levels >= 2
        facing_bet = to_call > 0
        can_raise = 'raise' in obs.legal
        shove = ('raise', obs.max_raise)
        i_am_pfa = (self._pfa == me)

        # opponent read: single opponent's profile, or the most dangerous trait among several
        profs = [self._profile(i) for i in c['opps']]
        station = bool(profs) and all(p.get('station') for p in profs)
        maniac = any(p.get('maniac') for p in profs)
        folder = bool(profs) and all(p.get('folder') for p in profs)
        unknown = all(p.get('vpip') is None for p in profs)

        # equity estimate for this decision
        all_in_spot = to_call >= stack or (stack - to_call) <= 0.35 * pot_total
        if street == 1:
            dr = draw2 if (all_in_spot or to_call == 0) else draw1
        elif street == 2:
            dr = draw1
        else:
            dr = 0.0
        eq = made + (1.0 - made) * dr
        weak = made < 0.58 and cat <= 2          # underpairs, middle/bottom pair, board pairs
        medium = 0.58 <= made < 0.72 and cat <= 2  # top pair / overpair
        if maniac and cat <= 2 and (facing_bet or facing_raise):
            eq *= 0.9 if facing_raise else 0.95  # a maniac's bets carry little information
        elif facing_raise and cat <= 2:
            eq *= (0.75, 0.65, 0.55)[street - 1] if weak else (0.80, 0.72, 0.65)[street - 1]
        elif facing_bet and (weak or medium):
            eq *= (0.90, 0.80, 0.70)[street - 1] if weak else (0.95, 0.90, 0.85)[street - 1]
        eq_n = eq ** (1.0 + 0.45 * (n_opp - 1)) if n_opp > 1 else eq
        spr = stack / float(pot_total) if pot_total > 0 else 10.0
        in_position = all(((i - obs.button - 1) % c['n']) < ((me - obs.button - 1) % c['n']) for i in c['opps']) if c['n'] else False

        def bet(frac):
            size = max(bb, int(pot_total * frac))
            total = my_bet + to_call + size
            if (stack - to_call - size) <= 0.6 * (pot_total + to_call + size) or spr <= 1.3:
                return shove
            return self._raise_to(obs, total)

        capm = c['cap_mode']
        if to_call <= 0:
            if not can_raise:
                return ('check', 0)
            bet_thr = (0.58 if not station else 0.50) + (0.12 if capm else 0.0)
            if eq_n >= bet_thr:
                if maniac and street < 3 and self.rng.random() < 0.4:
                    return ('check', 0)  # let the maniac bet for us
                return bet(0.66 if street < 3 else 0.75)
            if capm:
                return ('check', 0)
            if street < 3 and draw2 >= 0.28 and n_opp <= 2 and (in_position or n_opp == 1) and not station \
                    and self.rng.random() < 0.6:
                return bet(0.6)
            if street == 1 and i_am_pfa and n_opp <= 2 and not station and (folder or unknown or n_opp == 1) \
                    and (eq >= 0.2 or n_opp == 1):
                return bet(0.5)
            if street == 3 and n_opp == 1 and folder and eq < 0.3 and 0.6 * pot_total <= 0.25 * stack \
                    and self.rng.random() < 0.35:
                return bet(0.6)
            return ('check', 0)

        # facing a bet
        price = c['price']
        strong = 0.74 if not station else 0.68
        if eq_n >= strong and can_raise:
            if maniac and street < 3 and self.rng.random() < 0.5:
                return ('call', 0)  # slow-play vs a maniac
            lvl = max(bets) if bets else 0
            target = max(lvl * 3, my_bet + to_call + int(pot_total * 0.8))
            if (stack + my_bet - target) <= 0.6 * (pot_total + target) or spr <= 2.0:
                return shove
            return self._raise_to(obs, target)
        margin = 0.04 + (0.04 if facing_raise else 0.0) - (0.03 if maniac else 0.0) + (0.10 if capm else 0.0)
        if c['icm_tight'] and to_call >= 0.5 * stack:
            margin += 0.06
        if street < 3 and dr >= 0.2 and to_call <= 0.12 * stack and not all_in_spot:
            margin -= 0.06  # implied odds on a live draw
        need = price + margin
        if to_call >= 0.5 * stack and c['my_bb'] > 12:
            need = max(need, 0.5)  # stacking off for the tournament: only with a real hand
        if eq_n >= need:
            if can_raise and (stack - to_call) <= 0.5 * (pot_total + to_call) and eq_n >= 0.45:
                return shove  # calling would leave crumbs: take the fold equity instead
            return ('call', 0)
        if all_in_spot and eq_n >= price + 0.01 and (c['my_bb'] <= 12 or price <= 0.2 or eq_n >= 0.5):
            return ('call', 0)
        return ('fold', 0)


# ----------------------------------------------------------------------------------------------
# Warm-up: touch every code path once so the first real decision is not the cold one, then
# freeze the import-time heap so the garbage collector never walks it during a decision.
# ----------------------------------------------------------------------------------------------
class _Obs(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)


def _warm():
    import gc
    rng = random.Random(1)
    bot = Bot()
    bot.new_table({}, 0, 8)
    for i in range(300):
        deck = list(range(52))
        rng.shuffle(deck)
        evaluate(deck[:7])
        evaluate(deck[:6])
        evaluate(deck[:5])
        n = rng.randint(2, 8)
        street = i % 4
        seat = rng.randrange(n)
        stacks = [rng.randint(0, 3000) for _ in range(n)]
        stacks[seat] = rng.randint(1, 3000)
        bets = [rng.choice([0, 20, 60, 200]) for _ in range(n)]
        bets[seat] = 0
        mx = max(bets)
        tc = min(mx, stacks[seat])
        legal = {'fold', 'call'} if tc else {'check'}
        if stacks[seat] > mx:
            legal.add('raise')
        hist = [(rng.randrange(n), (rng.choice(['fold', 'call', 'raise', 'check']), 60)) for _ in range(rng.randint(0, 6))]
        bot.act(_Obs(hole=tuple(deck[:2]), board=tuple(deck[2:2 + (0, 3, 4, 5)[street]]), street=street, seat=seat,
                     button=rng.randrange(n), stacks=stacks, bets=bets, in_hand=[True] * n, pot=rng.randint(0, 1000),
                     to_call=tc, min_raise=min(mx + 20, stacks[seat]), max_raise=stacks[seat], legal=legal,
                     hand_no=1 + i // 3, blinds=(10, 20), history=hist))
    gc.collect()
    gc.freeze()


_warm()
