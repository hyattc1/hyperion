# Origin: the climb's outside judges, fourth wave (proposed decisions addendum 16; notebook docs/drills/field/out_o10.md).
# A fresh agent with no repo access, playing a strict 60-minute team (a tight-aggressive build from a blank directory in about 48 minutes),
# built it against the elite brief and kit; frozen at md5 bedcbd0c079f847c005af61f8807db10 and copied here unchanged apart from this header.
# The archive is docs/drills/field/out_o10_bot.py. Played through hyperion.sim.bestiary (registry name
# `out_o10`): a held-out judge, never tuned on, never in a night pool. Do not edit; a new bot is a new file.
#
"""rival_bot: tight-aggressive 8-max SNG bot. Standard library only."""
import gc, random, time
from kit import Agent

POP = [bin(i).count('1') for i in range(8192)]
STRAIGHT = [0] * 8192
for _m in range(8192):
    for _h in range(12, 3, -1):
        _b = 0
        for _k in range(5):
            _b |= 1 << (_h - _k if _h - _k >= 0 else 12)
        if _m & _b == _b:
            STRAIGHT[_m] = _h
            break
    else:
        if _m & 0b1000000001111 == 0b1000000001111:
            STRAIGHT[_m] = 3

def ev7(cards):
    rc = [0] * 13
    sm = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        rc[r] += 1
        sm[c & 3] |= 1 << r
    fl = 0
    for m in sm:
        if POP[m] >= 5:
            s = STRAIGHT[m]
            if s:
                return (8 << 20) | s
            while POP[m] > 5:
                m &= m - 1
            fl = (5 << 20) | m
    quad = -1
    trips = []
    pairs = []
    singles = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 4:
            quad = r
        elif n == 3:
            trips.append(r)
        elif n == 2:
            pairs.append(r)
        elif n == 1:
            singles.append(r)
    if quad >= 0:
        k = 0
        for r in range(12, -1, -1):
            if rc[r] and r != quad:
                k = r
                break
        return (7 << 20) | (quad << 4) | k
    if trips and (len(trips) > 1 or pairs):
        p = pairs[0] if pairs else -1
        if len(trips) > 1 and trips[1] > p:
            p = trips[1]
        return (6 << 20) | (trips[0] << 4) | p
    if fl:
        return fl
    mask = sm[0] | sm[1] | sm[2] | sm[3]
    s = STRAIGHT[mask]
    if s:
        return (4 << 20) | s
    if trips:
        ks = (pairs + singles)
        ks.sort(reverse=True)
        return (3 << 20) | (trips[0] << 8) | (ks[0] << 4) | ks[1]
    if len(pairs) >= 2:
        k = pairs[2] if len(pairs) > 2 else -1
        if singles and singles[0] > k:
            k = singles[0]
        return (2 << 20) | (pairs[0] << 8) | (pairs[1] << 4) | k
    if pairs:
        return (1 << 20) | (pairs[0] << 12) | (singles[0] << 8) | (singles[1] << 4) | singles[2]
    return (singles[0] << 16) | (singles[1] << 12) | (singles[2] << 8) | (singles[3] << 4) | singles[4]

PCT = [563, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 986, 832, 459, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 977, 799, 886, 711, 382, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 959, 717, 904, 621, 784, 567, 245, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 968, 802, 914, 669, 859, 579, 723, 443, 174, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 995, 835, 877, 714, 895, 618, 733, 505, 702, 455, 85, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 950, 769, 941, 748, 850, 612, 826, 466, 654, 357, 597, 306, 53, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 932, 708, 923, 639, 868, 636, 763, 493, 663, 469, 535, 324, 449, 269, 24, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 808, 624, 841, 615, 775, 582, 793, 463, 645, 416, 544, 354, 428, 232, 297, 158, 20, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 817, 511, 742, 550, 754, 419, 630, 508, 684, 386, 556, 336, 375, 235, 276, 155, 208, 104, 15, 1000, 1000, 1000, 1000, 1000, 1000, 1000, 675, 481, 693, 422, 606, 369, 573, 339, 487, 303, 475, 321, 410, 238, 251, 149, 167, 81, 143, 69, 11, 1000, 1000, 1000, 1000, 1000, 588, 351, 517, 309, 526, 291, 499, 257, 437, 241, 392, 180, 315, 217, 223, 119, 134, 88, 110, 49, 95, 34, 6, 1000, 1000, 1000, 401, 229, 363, 184, 345, 177, 285, 161, 330, 214, 263, 152, 190, 116, 199, 101, 125, 66, 75, 37, 60, 31, 43, 28, 2, 1000]


def _cls(c1, c2):
    r1 = c1 >> 2
    r2 = c2 >> 2
    if r1 < r2:
        r1, r2 = r2, r1
    return (r1 * 13 + r2) * 2 + (1 if (c1 & 3) == (c2 & 3) else 0)


# open-raise percentile cutoff by number of players left to act behind (BB=0, SB=1, BTN=2, ...)
OPEN = [0.30, 0.45, 0.50, 0.30, 0.23, 0.19, 0.17, 0.16, 0.15]
P = {'open': 1.0, 'push': 1.0, 'call': 0.45, 'v3': 0.045, 'tv': 0.57, 'marg': 0.05, 'rv': 0.80, 'bluff': 0.3, 'iso': 0.20, 'sbluff': 0.06, 'b3': 0.05, 'allin_m': 0.03, 'allin_c': 0.85, 'callai': 0.5, 'sfloor': 0.85}
POSMULT = [1.3, 1.15, 1.0, 0.85, 0.7, 0.6, 0.52, 0.47, 0.45]


class Bot(Agent):
    def __init__(self):
        self._init_state(0, 8, 2000)

    def _init_state(self, seat, n, stack):
        self.seat = seat
        self.n = n
        seed = (seat * 1000003 + n * 9176 + stack * 31 + 12345) & 0x7FFFFFFF
        self.rng = random.Random(seed)
        self.hand = -1
        self.hidx = 0
        self.last_street = -1
        self.pf_raiser = False
        # per seat stats: hands, pf raises, post folds, post calls, post raises
        self.hands = [0] * 16
        self.pfr = [0] * 16
        self.pfold = [0] * 16
        self.pcall = [0] * 16
        self.praise = [0] * 16

    def new_table(self, rules, seat, n_players):
        try:
            stack = 2000
            if isinstance(rules, dict):
                stack = int(rules.get('starting_stack', 2000) or 2000)
            self._init_state(int(seat), int(n_players or 8), stack)
        except Exception:
            self._init_state(0, 8, 2000)

    def hand_end(self, result):
        pass

    # ---------------------------------------------------------------- public
    def act(self, obs):
        was = gc.isenabled()
        gc.disable()
        try:
            a = self._act(obs)
        except Exception:
            a = None
        finally:
            if was:
                gc.enable()
        return self._fix(obs, a)

    def _fix(self, obs, a):
        legal = obs.legal
        try:
            if isinstance(a, tuple) and len(a) == 2 and a[0] in legal:
                if a[0] == 'raise':
                    amt = int(a[1])
                    amt = min(obs.max_raise, max(obs.min_raise, amt))
                    return ('raise', amt)
                return (a[0], 0)
        except Exception:
            pass
        if 'check' in legal:
            return ('check', 0)
        return ('fold', 0)

    # ------------------------------------------------------------ bookkeeping
    @staticmethod
    def _hist(obs):
        out = []
        for e in (obs.history or ()):
            try:
                s, act = e
                a, amt = act
                out.append((int(s), a, amt if isinstance(amt, (int, float)) else 0))
            except Exception:
                pass
        return out

    def _track(self, obs):
        bb = obs.blinds[1]
        if obs.hand_no != self.hand:
            self.hand = obs.hand_no
            self.hidx = 0
            self.last_street = -1
            self.pf_raiser = False
            for i, s in enumerate(obs.stacks):
                if (s > 0 or obs.bets[i] > 0) and i < 16:
                    self.hands[i] += 1
        hist = self._hist(obs)
        post = obs.street >= 1 and self.last_street >= 1
        pre = obs.street == 0
        for k in range(self.hidx, len(hist)):
            s, a, amt = hist[k]
            if s >= 16 or s == obs.seat:
                continue
            if pre:
                if a == 'raise' and amt > bb:
                    self.pfr[s] += 1
            elif post:
                if a == 'fold':
                    self.pfold[s] += 1
                elif a == 'call':
                    self.pcall[s] += 1
                elif a == 'raise':
                    self.praise[s] += 1
        self.hidx = len(hist)
        self.last_street = obs.street

    def _loose(self, s):
        """preflop raiser looseness multiplier"""
        if s is None or s >= 16:
            return 1.0
        h = self.hands[s]
        est = (self.pfr[s] + 0.12 * 12.0) / (h + 12.0)
        v = est / 0.12
        return 0.6 if v < 0.6 else (2.2 if v > 2.2 else v)

    def _fold_rate(self, s):
        f = self.pfold[s]
        d = f + self.pcall[s] + 0.5 * self.praise[s]
        return (f + 3.0) / (d + 8.0)

    def _agg(self, s):
        r = self.praise[s]
        c = self.pcall[s]
        return (r + 1.0) / (r + c + 5.0)

    # ------------------------------------------------------------------- main
    def _act(self, obs):
        self._track(obs)
        if obs.street == 0:
            return self._preflop(obs)
        return self._postflop(obs)

    def _shove_or(self, obs, amt):
        if amt >= 0.5 * obs.max_raise or obs.max_raise - amt < obs.blinds[1] * 2:
            return ('raise', obs.max_raise)
        return ('raise', int(amt))

    def _positions(self, obs):
        n = len(obs.stacks)
        st = obs.stacks
        bets = obs.bets
        seated = [i for i in range(n) if st[i] > 0 or bets[i] > 0 or obs.in_hand[i]]
        btn = obs.button
        order = [(btn + k) % n for k in range(1, n + 1) if ((btn + k) % n) in seated]
        if len(order) == 2:
            sb = btn
            bbs = order[0] if order[0] != btn else order[1]
        elif len(order) >= 3:
            sb = order[0]
            bbs = order[1]
        else:
            return 0, obs.seat
        # behind: in-hand players acting after me up to and including bb
        me = obs.seat
        if me == bbs:
            return 0, bbs
        c = 0
        i = me
        for _ in range(n):
            i = (i + 1) % n
            if obs.in_hand[i]:
                c += 1
            if i == bbs:
                break
        return c, bbs

    def _preflop(self, obs):
        me = obs.seat
        bb = obs.blinds[1]
        stack = obs.stacks[me]
        mybet = obs.bets[me]
        maxbet = max(obs.bets)
        tp = obs.pot + sum(obs.bets)
        p = PCT[_cls(obs.hole[0], obs.hole[1])] / 1000.0
        behind, bbseat = self._positions(obs)
        if behind > 8:
            behind = 8
        # effective stack in bb
        opp_max = 0
        for i in range(len(obs.stacks)):
            if i != me and obs.in_hand[i]:
                v = obs.stacks[i] + obs.bets[i]
                if v > opp_max:
                    opp_max = v
        eff = min(stack + mybet, opp_max) if opp_max else stack + mybet
        effbb = eff / float(bb)
        legal = obs.legal
        can_raise = 'raise' in legal
        to_call = obs.to_call

        raised = maxbet > bb
        nr = 0
        last_raiser = None
        for s, a, amt in self._hist(obs):
            if a == 'raise' and amt > bb:
                nr += 1
                last_raiser = s
        if raised and nr == 0:
            nr = 1
        if not raised:
            nr = 0

        if not raised:
            # unraised pot
            limpers = 0
            for i in range(len(obs.stacks)):
                if i != me and i != bbseat and obs.in_hand[i] and obs.bets[i] >= bb:
                    limpers += 1
            if effbb <= 11:
                cut = min(0.92, (0.95 - 0.05 * effbb) * POSMULT[behind] * P['push'])
                if limpers:
                    cut *= 0.75
                if 'check' in legal and behind == 0 and not limpers:
                    return ('check', 0)
                if p < cut and can_raise:
                    return ('raise', obs.max_raise)
                if 'check' in legal:
                    return ('check', 0)
                if to_call <= 0.5 * bb and p < 0.5:
                    return ('call', 0)
                return ('fold', 0)
            cut = OPEN[behind] * P['open']
            if limpers:
                cut = min(cut, P['iso'])
            if p < cut and can_raise:
                sz = (2.4 + limpers) * bb
                if self.rng.random() < 0.25:
                    sz += 0.5 * bb
                return self._shove_or(obs, max(obs.min_raise, sz))
            if 'check' in legal:
                return ('check', 0)
            if to_call <= 0.5 * bb and p < 0.40:
                return ('call', 0)
            return ('fold', 0)

        # facing a raise
        base = (0.17, 0.07, 0.035)[min(nr, 3) - 1]
        w = self._loose(last_raiser)
        rcut = base * w
        # short-stack shoves are wide
        if last_raiser is not None and last_raiser < len(obs.stacks):
            lr_tot = obs.stacks[last_raiser] + obs.bets[last_raiser]
            if obs.stacks[last_raiser] == 0 and lr_tot <= 14 * bb:
                rcut = max(rcut, 0.30 if nr == 1 else 0.18)
        need = to_call / float(tp + to_call) if to_call > 0 else 0.0
        k = 2.0 - 1.5 * need
        k = 0.7 if k < 0.7 else (1.8 if k > 1.8 else k)
        cm = P['call']
        if to_call >= 0.4 * stack:
            cm = P['callai']
            if effbb <= 10 and cm < P['sfloor']:
                cm = P['sfloor']
        ccut = rcut * k * cm
        if behind >= 2:
            ccut *= 0.85
        if me == bbseat:
            ccut *= 1.1
        allin_call = to_call >= 0.9 * stack
        if allin_call and effbb > 12:
            ccut *= P['allin_c']
        # value raise
        v3 = P['v3'] * w if nr == 1 else 0.02 * w
        v3 = min(v3, rcut * 0.6)
        if nr == 1 and p < max(v3, 0.03) and can_raise:
            if effbb < 28:
                return ('raise', obs.max_raise)
            sz = maxbet * 3.0 + (0.0 if behind == 0 else bb)
            return self._shove_or(obs, max(obs.min_raise, sz))
        if nr >= 2 and p < max(v3, 0.02) and can_raise:
            return ('raise', obs.max_raise)
        if p < ccut:
            return ('call', 0)
        # light 3-bet bluff
        if nr == 1 and can_raise and effbb > 30 and p < 0.35 and behind <= 2 and last_raiser is not None \
                and self.rng.random() < P['b3'] and maxbet <= 4 * bb:
            return self._shove_or(obs, max(obs.min_raise, maxbet * 3.0))
        if 'check' in legal:
            return ('check', 0)
        return ('fold', 0)

    # --------------------------------------------------------------- postflop
    def _equity(self, obs, cut, nsamp):
        t0 = time.perf_counter()
        hole = obs.hole
        board = obs.board
        used = set(hole)
        used.update(board)
        deck = [c for c in range(52) if c not in used]
        D = len(deck)
        need = 5 - len(board)
        rnd = self.rng.random
        bd0 = list(board)
        h0 = hole[0]
        h1 = hole[1]
        wins = 0.0
        done = 0
        ccut = int(cut * 1000)
        for it in range(nsamp):
            if (it & 3) == 3 and time.perf_counter() - t0 > 0.0005:
                break
            tries = 0
            while True:
                i = int(rnd() * D)
                j = int(rnd() * D)
                if i == j:
                    continue
                a = deck[i]
                b = deck[j]
                tries += 1
                if PCT[_cls(a, b)] <= ccut or tries >= 8:
                    break
            if need:
                sel = [i, j]
                bd = bd0[:]
                while len(bd) < 5:
                    r = int(rnd() * D)
                    if r in sel:
                        continue
                    sel.append(r)
                    bd.append(deck[r])
            else:
                bd = bd0
            me = ev7([h0, h1] + bd)
            op = ev7([a, b] + bd)
            if me > op:
                wins += 1.0
            elif me == op:
                wins += 0.5
            done += 1
        return wins / done if done else 0.5

    def _postflop(self, obs):
        me = obs.seat
        bb = obs.blinds[1]
        stack = obs.stacks[me]
        tp = obs.pot + sum(obs.bets)
        to_call = obs.to_call
        legal = obs.legal
        can_raise = 'raise' in legal
        maxbet = max(obs.bets)
        actives = [i for i in range(len(obs.stacks)) if i != me and obs.in_hand[i]]
        opps = len(actives)
        if opps == 0:
            return ('check', 0) if 'check' in legal else ('call', 0)
        # preflop aggression in this hand
        pf_nr = 0
        aggressor = None
        for s, a, amt in self._hist(obs):
            if a == 'raise' and amt > bb:
                pf_nr += 1
        for i in actives:
            if obs.bets[i] == maxbet and maxbet > 0:
                aggressor = i
        # opponent range width (percentile cutoff on preflop strength)
        if to_call <= 0:
            cut = 0.75 if pf_nr == 0 else (0.55 if pf_nr == 1 else 0.35)
        else:
            ratio = to_call / float(max(tp - to_call, 1))
            if ratio < 0.3:
                cut = 0.62
            elif ratio < 0.6:
                cut = 0.52
            elif ratio < 1.0:
                cut = 0.44
            elif ratio < 2.0:
                cut = 0.36
            else:
                cut = 0.30
            if pf_nr >= 2:
                cut *= 0.7
            if aggressor is not None:
                ag = self._agg(aggressor)
                cut *= 1.5 if ag > 0.5 else (0.85 if ag < 0.15 else 1.0)
        if cut > 0.95:
            cut = 0.95
        nsamp = 36 if obs.street < 3 else 44
        e = self._equity(obs, cut, nsamp)
        k = opps if opps < 4 else 4
        emw = e ** (1.0 + 0.55 * (k - 1)) if k > 1 else e
        rng = self.rng
        street = obs.street

        if to_call <= 0:
            # check or bet
            tv = P['tv'] + 0.04 * (k - 1)
            if can_raise:
                if emw >= tv:
                    frac = 0.72 if emw > 0.72 else 0.5
                    if emw > 0.88:
                        frac = 0.9 if rng.random() < 0.6 else 0.35
                    amt = maxbet + tp * frac
                    return self._shove_or(obs, max(obs.min_raise, amt))
                # bluff
                if emw < 0.5 and opps <= 2:
                    fr = 0.0
                    for i in actives:
                        fr += self._fold_rate(i)
                    fr /= opps
                    scale = (fr - 0.12) / 0.28
                    scale = 0.0 if scale < 0 else (1.6 if scale > 1.6 else scale)
                    if street == 1:
                        pb = 0.40 if self.pf_raiser or pf_nr == 0 else 0.15
                    elif street == 2:
                        pb = 0.22
                    else:
                        pb = 0.12 if e < 0.25 else 0.0
                    pb *= scale * P['bluff']
                    if tp > 0 and rng.random() < pb:
                        return self._shove_or(obs, max(obs.min_raise, maxbet + tp * 0.6))
            return ('check', 0)

        need = to_call / float(tp + to_call)
        margin = P['marg'] + 0.02 * (k - 1)
        if to_call >= 0.9 * stack:
            margin += P['allin_m']
        if can_raise and emw > P['rv'] and (street < 3 or emw > P['rv'] + 0.05):
            amt = maxbet + (tp) * 0.75
            return self._shove_or(obs, max(obs.min_raise, amt))
        if emw > need + margin:
            return ('call', 0)
        # semi-bluff raise
        if can_raise and 0.3 < e < 0.5 and street < 3 and opps == 1 and rng.random() < 0.06 and to_call < 0.7 * tp:
            return self._shove_or(obs, max(obs.min_raise, maxbet + tp * 0.8))
        return ('fold', 0)
