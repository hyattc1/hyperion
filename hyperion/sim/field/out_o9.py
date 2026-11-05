# Origin: the climb's outside judges, fourth wave (proposed decisions addendum 16; notebook docs/drills/field/out_o9.md).
# A fresh agent with no repo access, playing an unconventional team (limp-traps, tiny 3-bets, small probes and big polarised sizes, kept where its sparring paid),
# built it against the elite brief and kit; frozen at md5 f85066a0bd7e92551dad61a0d559bc89 and copied here unchanged apart from this header.
# The archive is docs/drills/field/out_o9_bot.py. Played through hyperion.sim.bestiary (registry name
# `out_o9`): a held-out judge, never tuned on, never in a night pool. Do not edit; a new bot is a new file.
#
"""rival_bot — the "unconventional" 8-max SNG bot. Standard library only.

Strategy summary (details in NOTEBOOK.md):
  * preflop: equity-table ranges by seats-behind, limp-trap with premiums in front of aggressors,
    tiny 3-bets with premiums to keep callers in, over-limps with speculative hands, push/fold short
  * postflop: Monte-Carlo equity vs N random hands (time-guarded), adaptive sizing: big/overbet
    value vs callers, small probes and leads vs folders, polarised overbets with the nuts
  * opponent model per seat: VPIP, PFR, call-vs-fold ratio, aggression; reset per table
  * ICM pressure margin near the bubble / hand cap; deterministic RNG seeded in new_table
"""
import random
import time

try:
    from kit import Agent
except Exception:  # pragma: no cover - kit missing in some harnesses
    class Agent(object):
        def new_table(self, rules, seat, n_players): pass
        def act(self, obs): raise NotImplementedError
        def hand_end(self, result): pass

# ---------------------------------------------------------------------------------------------
# precomputed preflop all-in equity per 169 hand classes vs 1/2/3/5 random hands (precompute.py)
# ---------------------------------------------------------------------------------------------
PRE_EQ = {
    1: (0.505, 0.544, 0.582, 0.600, 0.635, 0.656, 0.691, 0.722, 0.745, 0.771, 0.806, 0.818, 0.852, 0.370, 0.378, 0.380, 0.387, 0.398, 0.421, 0.374, 0.397, 0.419, 0.433, 0.379, 0.390, 0.419, 0.438, 0.451, 0.403, 0.414, 0.425, 0.446, 0.457, 0.480, 0.433, 0.437, 0.431, 0.459, 0.471, 0.493, 0.507, 0.447, 0.443, 0.459, 0.471, 0.485, 0.503, 0.530, 0.539, 0.475, 0.491, 0.499, 0.502, 0.500, 0.522, 0.528, 0.552, 0.582, 0.494, 0.513, 0.509, 0.530, 0.538, 0.549, 0.558, 0.581, 0.598, 0.607, 0.531, 0.534, 0.552, 0.552, 0.564, 0.574, 0.590, 0.605, 0.622, 0.612, 0.631, 0.567, 0.579, 0.596, 0.607, 0.591, 0.616, 0.622, 0.618, 0.641, 0.641, 0.658, 0.682, 0.328, 0.339, 0.350, 0.342, 0.376, 0.385, 0.345, 0.367, 0.379, 0.403, 0.345, 0.367, 0.391, 0.404, 0.429, 0.373, 0.375, 0.389, 0.413, 0.425, 0.458, 0.405, 0.403, 0.405, 0.433, 0.453, 0.464, 0.471, 0.425, 0.416, 0.422, 0.442, 0.459, 0.483, 0.501, 0.515, 0.444, 0.449, 0.464, 0.479, 0.479, 0.513, 0.512, 0.536, 0.549, 0.469, 0.488, 0.501, 0.493, 0.520, 0.520, 0.537, 0.552, 0.570, 0.594, 0.508, 0.521, 0.509, 0.530, 0.545, 0.551, 0.566, 0.581, 0.605, 0.607, 0.621, 0.547, 0.561, 0.574, 0.581, 0.586, 0.592, 0.608, 0.608, 0.635, 0.633, 0.645, 0.659),
    2: (0.311, 0.330, 0.372, 0.404, 0.428, 0.465, 0.497, 0.532, 0.581, 0.598, 0.643, 0.685, 0.731, 0.241, 0.245, 0.252, 0.255, 0.270, 0.293, 0.254, 0.261, 0.277, 0.295, 0.255, 0.262, 0.287, 0.299, 0.307, 0.258, 0.269, 0.286, 0.297, 0.331, 0.331, 0.262, 0.286, 0.290, 0.299, 0.320, 0.340, 0.368, 0.299, 0.302, 0.296, 0.313, 0.330, 0.350, 0.373, 0.388, 0.308, 0.325, 0.328, 0.330, 0.329, 0.361, 0.368, 0.395, 0.407, 0.327, 0.334, 0.341, 0.356, 0.355, 0.361, 0.387, 0.413, 0.429, 0.433, 0.341, 0.358, 0.369, 0.374, 0.382, 0.390, 0.416, 0.428, 0.458, 0.450, 0.480, 0.383, 0.400, 0.403, 0.407, 0.413, 0.426, 0.441, 0.440, 0.455, 0.488, 0.488, 0.503, 0.192, 0.204, 0.216, 0.206, 0.238, 0.248, 0.210, 0.218, 0.257, 0.276, 0.210, 0.227, 0.249, 0.263, 0.286, 0.224, 0.229, 0.250, 0.262, 0.285, 0.300, 0.231, 0.241, 0.248, 0.262, 0.287, 0.307, 0.325, 0.243, 0.262, 0.272, 0.274, 0.296, 0.320, 0.327, 0.352, 0.266, 0.274, 0.285, 0.296, 0.296, 0.320, 0.343, 0.369, 0.394, 0.278, 0.298, 0.301, 0.309, 0.329, 0.338, 0.359, 0.372, 0.402, 0.413, 0.301, 0.316, 0.317, 0.339, 0.352, 0.354, 0.373, 0.393, 0.418, 0.429, 0.449, 0.356, 0.358, 0.366, 0.373, 0.370, 0.389, 0.412, 0.420, 0.431, 0.463, 0.473, 0.473),
    3: (0.215, 0.234, 0.265, 0.283, 0.310, 0.348, 0.366, 0.402, 0.448, 0.494, 0.534, 0.580, 0.635, 0.185, 0.194, 0.206, 0.197, 0.202, 0.233, 0.188, 0.205, 0.227, 0.230, 0.175, 0.205, 0.221, 0.234, 0.252, 0.191, 0.202, 0.210, 0.235, 0.245, 0.280, 0.206, 0.214, 0.213, 0.225, 0.242, 0.258, 0.286, 0.211, 0.217, 0.229, 0.240, 0.246, 0.262, 0.286, 0.316, 0.231, 0.234, 0.237, 0.251, 0.253, 0.273, 0.290, 0.310, 0.342, 0.235, 0.252, 0.246, 0.266, 0.269, 0.281, 0.291, 0.319, 0.334, 0.354, 0.264, 0.269, 0.282, 0.288, 0.298, 0.302, 0.299, 0.322, 0.362, 0.362, 0.379, 0.294, 0.305, 0.310, 0.319, 0.308, 0.317, 0.329, 0.345, 0.369, 0.394, 0.397, 0.422, 0.135, 0.143, 0.160, 0.153, 0.168, 0.195, 0.145, 0.172, 0.183, 0.203, 0.139, 0.153, 0.178, 0.200, 0.204, 0.149, 0.157, 0.181, 0.196, 0.203, 0.232, 0.156, 0.165, 0.172, 0.187, 0.212, 0.232, 0.249, 0.166, 0.181, 0.183, 0.191, 0.219, 0.225, 0.262, 0.277, 0.191, 0.195, 0.189, 0.200, 0.214, 0.233, 0.265, 0.266, 0.308, 0.203, 0.204, 0.220, 0.218, 0.229, 0.235, 0.258, 0.287, 0.321, 0.314, 0.219, 0.224, 0.244, 0.229, 0.259, 0.246, 0.277, 0.291, 0.325, 0.329, 0.338, 0.250, 0.260, 0.269, 0.296, 0.279, 0.296, 0.291, 0.298, 0.333, 0.344, 0.364, 0.388),
    5: (0.148, 0.171, 0.178, 0.180, 0.207, 0.211, 0.237, 0.264, 0.305, 0.353, 0.382, 0.419, 0.493, 0.125, 0.140, 0.147, 0.144, 0.151, 0.164, 0.129, 0.154, 0.161, 0.166, 0.119, 0.142, 0.153, 0.164, 0.176, 0.140, 0.142, 0.149, 0.155, 0.179, 0.188, 0.140, 0.144, 0.152, 0.158, 0.170, 0.188, 0.200, 0.144, 0.153, 0.154, 0.166, 0.169, 0.187, 0.211, 0.213, 0.154, 0.162, 0.153, 0.171, 0.169, 0.186, 0.209, 0.214, 0.239, 0.172, 0.183, 0.188, 0.189, 0.186, 0.186, 0.201, 0.228, 0.254, 0.263, 0.180, 0.179, 0.189, 0.201, 0.197, 0.202, 0.216, 0.229, 0.257, 0.269, 0.290, 0.215, 0.213, 0.223, 0.216, 0.214, 0.226, 0.233, 0.244, 0.272, 0.282, 0.294, 0.311, 0.095, 0.094, 0.113, 0.101, 0.116, 0.132, 0.096, 0.101, 0.113, 0.126, 0.087, 0.097, 0.116, 0.125, 0.147, 0.090, 0.091, 0.109, 0.129, 0.138, 0.156, 0.104, 0.102, 0.105, 0.115, 0.134, 0.154, 0.161, 0.103, 0.112, 0.115, 0.129, 0.133, 0.150, 0.172, 0.185, 0.112, 0.115, 0.125, 0.128, 0.134, 0.144, 0.172, 0.191, 0.215, 0.127, 0.124, 0.142, 0.139, 0.153, 0.153, 0.159, 0.202, 0.209, 0.225, 0.139, 0.140, 0.148, 0.148, 0.171, 0.164, 0.177, 0.188, 0.225, 0.240, 0.249, 0.162, 0.173, 0.181, 0.175, 0.167, 0.189, 0.192, 0.201, 0.228, 0.248, 0.254, 0.280),
}

# ---------------------------------------------------------------------------------------------
# hand evaluator (7 cards, bitmask based)
# ---------------------------------------------------------------------------------------------
_STRAIGHT = [-1] * 8192
_TOP5 = [0] * 8192
_POP = [0] * 8192
for _m in range(8192):
    _best = -1
    for _top in range(12, 3, -1):
        _need = 0b11111 << (_top - 4)
        if _m & _need == _need:
            _best = _top
            break
    if _best < 0 and _m & 0b1000000001111 == 0b1000000001111:
        _best = 3
    _STRAIGHT[_m] = _best
    _t = _m; _k = 0; _out = 0
    for _r in range(12, -1, -1):
        if _t >> _r & 1:
            _out |= 1 << _r; _k += 1
            if _k == 5:
                break
    _TOP5[_m] = _out
    _POP[_m] = bin(_m).count('1')


def eval7(cards):
    c0 = [0] * 13
    rm = 0
    sm = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        c0[r] += 1
        rm |= 1 << r
        sm[c & 3] |= 1 << r
    for m in sm:
        if _POP[m] >= 5:
            st = _STRAIGHT[m]
            if st >= 0:
                return (8 << 20) | st
            return (5 << 20) | _TOP5[m]
    quad = -1; trips = -1; p1 = -1; p2 = -1
    for r in range(12, -1, -1):
        n = c0[r]
        if n == 4:
            quad = r
        elif n == 3:
            if trips < 0:
                trips = r
            elif p1 < 0:
                p1 = r
        elif n == 2:
            if p1 < 0:
                p1 = r
            elif p2 < 0:
                p2 = r
    if quad >= 0:
        k = rm & ~(1 << quad)
        return (7 << 20) | (quad << 4) | (k.bit_length() - 1)
    if trips >= 0 and p1 >= 0:
        return (6 << 20) | (trips << 4) | p1
    st = _STRAIGHT[rm]
    if st >= 0:
        return (4 << 20) | st
    if trips >= 0:
        k = rm & ~(1 << trips)
        k1 = k.bit_length() - 1
        k &= ~(1 << k1)
        return (3 << 20) | (trips << 8) | (k1 << 4) | (k.bit_length() - 1)
    if p1 >= 0 and p2 >= 0:
        k = rm & ~(1 << p1) & ~(1 << p2)
        return (2 << 20) | (p1 << 8) | (p2 << 4) | (k.bit_length() - 1)
    if p1 >= 0:
        k = rm & ~(1 << p1)
        kk = 0
        for _ in range(3):
            b = k.bit_length() - 1
            kk = (kk << 4) | b
            k &= ~(1 << b)
        return (1 << 20) | (p1 << 12) | kk
    return _TOP5[rm]


def hand_class(c1, c2):
    r1 = c1 >> 2; r2 = c2 >> 2
    if r1 == r2:
        return r1
    if r1 > r2:
        hi, lo = r1, r2
    else:
        hi, lo = r2, r1
    base = 13 + (hi * (hi - 1) // 2 + lo)
    return base if (c1 & 3) == (c2 & 3) else base + 78


# percentile (0 = best) of each class by heads-up equity
_ORDER = sorted(range(169), key=lambda k: -PRE_EQ[1][k])
PCT = [0.0] * 169
for _i, _k in enumerate(_ORDER):
    PCT[_k] = _i / 168.0


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


class Bot(Agent):
    TIME_BUDGET = 0.00050  # safety net: stop Monte-Carlo sampling after this many seconds

    # ------------------------------------------------------------------ lifecycle
    def __init__(self):
        self.rng = random.Random(1)
        self.n = 8
        self.seat = 0
        self.errors = 0
        self.debug = False
        self._reset_table()

    def _reset_table(self):
        self.stats = {}
        self.cur_hand = -1
        self.hist_idx = 0
        self.eq_cache = {}
        self.pfr_seat = -1       # preflop raiser this hand (last raiser)
        self.i_raised_pre = False
        self.i_limped_trap = False
        self.aggr_streets = set()

    def new_table(self, rules, seat, n_players):
        seed = 0
        try:
            if isinstance(rules, dict):
                s = rules.get('seed')
                if s is not None:
                    seed = int(s) & 0xFFFFFFFF
        except Exception:
            seed = 0
        self.seat = int(seat) if isinstance(seat, int) else 0
        self.n = int(n_players) if isinstance(n_players, int) and n_players > 0 else 8
        self.rng = random.Random(seed * 1009 + self.seat * 31 + self.n)
        self._reset_table()

    def hand_end(self, result):
        pass

    # ------------------------------------------------------------------ opponent model
    def _stat(self, s):
        st = self.stats.get(s)
        if st is None:
            st = self.stats[s] = {'hands': 0, 'vpip': 0, 'pfr': 0, 'calls': 0, 'folds': 0, 'raises': 0, 'acts': 0}
        return st

    def _update_model(self, obs):
        hist = obs.history or ()
        if obs.hand_no != self.cur_hand:
            self.cur_hand = obs.hand_no
            self.hist_idx = 0
            self.eq_cache = {}
            self.pfr_seat = -1
            self.i_raised_pre = False
            self.i_limped_trap = False
            self.aggr_streets = set()
            for s, f in enumerate(obs.in_hand or ()):
                if f and s != obs.seat:
                    self._stat(s)['hands'] += 1
        bb = obs.blinds[1] if obs.blinds else 20
        n = len(hist)
        i = self.hist_idx
        while i < n:
            try:
                s, a = hist[i]
                kind = a[0]
            except Exception:
                i += 1
                continue
            if s != obs.seat:
                st = self._stat(s)
                st['acts'] += 1
                if kind == 'raise':
                    st['raises'] += 1
                    if obs.street == 0:
                        st['pfr'] += 1; st['vpip'] += 1
                elif kind == 'call':
                    st['calls'] += 1
                    if obs.street == 0:
                        st['vpip'] += 1
                elif kind == 'fold':
                    st['folds'] += 1
            if kind == 'raise' and obs.street == 0:
                self.pfr_seat = s
                if s == obs.seat:
                    self.i_raised_pre = True
            i += 1
        self.hist_idx = n

    def _callrate(self, s):
        """0..1: how often this seat calls rather than folds when it acts (station-ness)."""
        st = self.stats.get(s)
        if not st or st['calls'] + st['folds'] < 6:
            return 0.5
        return (st['calls'] + 1.0) / (st['calls'] + st['folds'] + 2.0)

    def _aggr(self, s):
        st = self.stats.get(s)
        if not st or st['hands'] < 8:
            return 0.15
        return st['pfr'] / float(st['hands'])

    def _raise_ratio(self, s):
        """Share of this seat's actions that were raises (postflop+preflop); low = bets mean strength."""
        st = self.stats.get(s)
        if not st or st['acts'] < 10:
            return 0.2
        return st['raises'] / float(st['acts'])

    # ------------------------------------------------------------------ equity
    def _equity(self, obs, n_opp, t0):
        """Monte-Carlo equity vs n_opp random hands on the current board; time guarded."""
        key = (obs.hole, obs.board, n_opp)
        v = self.eq_cache.get(key)
        if v is not None:
            return v
        hole = obs.hole; board = obs.board
        used = set(hole); used.update(board)
        deck = [c for c in range(52) if c not in used]
        L = len(deck)
        need = 5 - len(board)
        draw = need + 2 * n_opp
        rnd = self.rng.random
        wins = 0.0; samples = 0
        # fixed sample count => deterministic given the seed; the time guard only trips on a slow machine
        max_samples = 40 if n_opp <= 1 else 30 if n_opp == 2 else 20 if n_opp <= 4 else 12
        board_l = list(board)
        hole_l = list(hole)
        pc = time.perf_counter
        budget = self.TIME_BUDGET
        while samples < max_samples:
            if samples & 3 == 3 and pc() - t0 > budget:
                break
            # partial Fisher-Yates
            for i in range(draw):
                j = i + int(rnd() * (L - i))
                deck[i], deck[j] = deck[j], deck[i]
            b = board_l + deck[:need]
            me = eval7(b + hole_l)
            best = 0; i = need
            for _o in range(n_opp):
                ov = eval7(b + deck[i:i + 2]); i += 2
                if ov > best:
                    best = ov
            if me > best:
                wins += 1.0
            elif me == best:
                wins += 0.5
            samples += 1
        eq = wins / samples if samples else 0.5
        self.eq_cache[key] = eq
        return eq

    # ------------------------------------------------------------------ helpers
    def _raise(self, obs, target):
        if 'raise' not in obs.legal:
            return ('call', 0) if 'call' in obs.legal else ('check', 0) if 'check' in obs.legal else ('fold', 0)
        try:
            t = int(target)
        except Exception:
            t = obs.min_raise
        if t < obs.min_raise:
            t = obs.min_raise
        if t > obs.max_raise:
            t = obs.max_raise
        return ('raise', t)

    def _passive(self, obs):
        return ('check', 0) if 'check' in obs.legal else ('call', 0) if 'call' in obs.legal else ('fold', 0)

    def _fold(self, obs):
        return ('check', 0) if 'check' in obs.legal else ('fold', 0)

    # ------------------------------------------------------------------ main
    def act(self, obs):
        t0 = time.perf_counter()
        try:
            a = self._act(obs, t0)
        except Exception:
            a = None
            self.errors += 1
            if self.debug:
                raise
        legal = obs.legal
        if isinstance(a, tuple) and len(a) == 2 and a[0] in legal:
            if a[0] != 'raise':
                return (a[0], 0)
            amt = a[1]
            if isinstance(amt, int) and obs.min_raise <= amt <= obs.max_raise:
                return a
            return ('raise', max(obs.min_raise, min(obs.max_raise, int(amt) if isinstance(amt, (int, float)) else obs.min_raise)))
        if 'check' in legal:
            return ('check', 0)
        if 'call' in legal and obs.to_call <= (obs.blinds[1] if obs.blinds else 20):
            return ('call', 0)
        return ('fold', 0)

    def _act(self, obs, t0):
        self._update_model(obs)
        me = obs.seat
        n = len(obs.stacks)
        bb = max(1, obs.blinds[1] if obs.blinds else 20)
        stack = obs.stacks[me]
        my_bet = obs.bets[me]
        mx = max(obs.bets)
        pot_total = obs.pot + sum(obs.bets)
        opps = [i for i in range(n) if i != me and obs.in_hand[i]]
        n_opp = max(1, len(opps))
        alive = [i for i in range(n) if obs.stacks[i] > 0 or obs.in_hand[i]]
        n_alive = max(2, len(alive))
        to_call = obs.to_call
        legal = obs.legal
        # ICM pressure: how much extra equity margin to demand before risking the stack
        margin = self._icm_margin(obs, stack, bb, alive)
        if obs.street == 0:
            return self._preflop(obs, t0, me, n, bb, stack, my_bet, mx, pot_total, opps, n_opp, n_alive, margin)
        return self._postflop(obs, t0, me, n, bb, stack, my_bet, mx, pot_total, opps, n_opp, margin)

    def _icm_margin(self, obs, stack, bb, alive):
        n_alive = len(alive)
        if n_alive <= 1:
            return 0.0
        stacks = [obs.stacks[i] + obs.bets[i] for i in alive]
        avg = sum(stacks) / float(n_alive)
        mine = stack + obs.bets[obs.seat]
        shorts = sum(1 for s in stacks if s < 8 * bb and s < mine * 0.5)
        m = 0.0
        if mine > avg * 0.9:
            m += 0.02 + 0.015 * shorts
        if n_alive <= 4:
            m += 0.02
        hands_left = 200 - (obs.hand_no or 0)
        if 0 <= hands_left < 25 and mine > avg * 0.8:
            m += 0.03
        return _clamp(m, 0.0, 0.10)

    # ------------------------------------------------------------------ preflop
    def _preflop(self, obs, t0, me, n, bb, stack, my_bet, mx, pot_total, opps, n_opp, n_alive, margin):
        k = hand_class(obs.hole[0], obs.hole[1])
        pct = PCT[k]
        eq1 = PRE_EQ[1][k]
        legal = obs.legal
        to_call = obs.to_call
        rnd = self.rng.random
        # who is still to act behind me (in hand, has not acted yet, not me)
        acted = set()
        for h in obs.history or ():
            try:
                acted.add(h[0])
            except Exception:
                pass
        behind = [i for i in opps if i not in acted and obs.bets[i] <= bb]
        n_behind = len(behind)
        raised = mx > bb
        n_callers = sum(1 for i in opps if obs.bets[i] >= bb and i in acted)
        M = (stack + my_bet) / float(bb)
        limpers = [i for i in opps if obs.bets[i] == bb and i in acted]
        # effective stack: smallest of mine vs biggest opponent still in
        eff = min(stack + my_bet, max([obs.stacks[i] + obs.bets[i] for i in opps] or [stack]))
        eff_M = eff / float(bb)
        aggressive_behind = any(self._aggr(i) > 0.22 for i in behind)
        station_behind = sum(1 for i in behind if self._callrate(i) > 0.65)

        # -------- all-in or short-stack regime: push/fold
        if eff_M <= 11 or (raised and to_call >= 0.4 * stack):
            if raised:
                # facing a raise/shove: call or re-shove if equity beats pot odds vs expected hands
                n_call = max(1, sum(1 for i in opps if obs.bets[i] > bb))
                eq = PRE_EQ[min(n_call, 3) if n_call < 5 else 5][k]
                # raiser's range is tighter than random: discount (a deep-stacked shover is very tight)
                eq -= 0.06 if n_call == 1 else 0.09
                odds = to_call / float(pot_total + to_call) if to_call > 0 else 0.0
                risk = min(1.0, to_call / float(max(1, stack)))
                need = odds + 0.03 + margin
                # ICM: do not call off a healthy stack without a real hand
                if M > 30:
                    need += 0.15 * risk
                elif M > 18:
                    need += 0.10 * risk
                elif M > 12:
                    need += 0.03 * risk
                if eq >= need:
                    if 'raise' in legal and eq1 > 0.55:
                        return self._raise(obs, obs.max_raise) if to_call < stack else ('call', 0)
                    return ('call', 0) if 'call' in legal else self._passive(obs)
                return self._fold(obs)
            # unraised: shove with a range widening as the stack shrinks and fewer players behind
            thr = 0.455 + 0.009 * min(eff_M, 12) + 0.013 * n_behind
            if n_callers > 0:
                thr += 0.03
            thr += margin * 0.5
            if eq1 >= thr:
                if 'raise' in legal:
                    # a tiny raise sometimes looks weak and gets called by junk; but short we just shove
                    return self._raise(obs, obs.max_raise)
                return self._passive(obs)
            # BB free check / cheap completion with playable hands
            if 'check' in legal:
                return ('check', 0)
            if to_call <= bb // 2 and pct < 0.6 and 'call' in legal:
                return ('call', 0)
            return self._fold(obs)

        # -------- deep-ish stacks
        if not raised:
            # open threshold by seats behind (7 behind = UTG at 8-max)
            open_thr = _clamp(0.11 + 0.05 * (7 - n_behind), 0.11, 0.45)
            # steal wider when the players behind fold a lot
            if n_behind <= 3 and behind and all(self._callrate(i) < 0.45 for i in behind):
                open_thr += 0.08
            if 'check' in legal:
                # BB, nobody raised: raise with strong hands (bigger vs limpers), otherwise check
                if pct < 0.08 + 0.02 * len(limpers):
                    size = (3 + len(limpers)) * bb
                    return self._raise(obs, size)
                return ('check', 0)
            if n_behind == 1 and obs.bets[me] > 0:
                open_thr = 0.33  # small blind: raise-or-fold mostly, complete with suited junk
            # limp-trap: premium hand, aggressive player still to act -> limp and re-raise later
            if pct < 0.025 and aggressive_behind and n_behind >= 2 and eff_M > 20 and rnd() < 0.8:
                self.i_limped_trap = True
                return ('call', 0) if 'call' in legal else self._passive(obs)
            if pct < open_thr:
                if 'raise' not in legal:
                    return ('call', 0) if 'call' in legal else self._passive(obs)
                # sizing: bigger when stations are behind or there are limpers; otherwise small
                if station_behind >= 2 or len(limpers) >= 2:
                    size = (3.5 + len(limpers)) * bb
                elif pct < 0.05 and station_behind >= 1:
                    size = (4 + len(limpers)) * bb
                else:
                    size = (2.3 + 0.8 * len(limpers)) * bb
                # unconventional: occasionally min-raise with the top of range to induce
                if pct < 0.04 and rnd() < 0.25 and not limpers:
                    size = 2 * bb
                return self._raise(obs, size)
            # over-limp speculative hands when there is already a limper and stacks are deep
            if limpers and eff_M > 25 and pct < 0.45 and to_call <= bb and 'call' in legal:
                hi, lo = max(obs.hole[0] >> 2, obs.hole[1] >> 2), min(obs.hole[0] >> 2, obs.hole[1] >> 2)
                suited = (obs.hole[0] & 3) == (obs.hole[1] & 3)
                pair = hi == lo
                if pair or (suited and hi - lo <= 3) or (hi - lo == 1 and lo >= 4):
                    return ('call', 0)
            # small blind completion with suited/connected junk when BB is passive
            if n_behind == 1 and obs.bets[me] > 0 and to_call <= bb // 2 and pct < 0.55 and 'call' in legal:
                if self._aggr(behind[0]) < 0.2 if behind else True:
                    return ('call', 0)
            return self._fold(obs)

        # -------- facing a raise
        raiser = self.pfr_seat if self.pfr_seat >= 0 and self.pfr_seat != me else -1
        n_raises = sum(1 for h in (obs.history or ()) if isinstance(h, tuple) and len(h) == 2 and isinstance(h[1], tuple) and h[1][0] == 'raise')
        raise_frac = to_call / float(stack + my_bet)
        if self.i_raised_pre and n_raises >= 2:
            # we raised and got 3-bet
            if pct < 0.025 or (pct < 0.05 and eff_M < 30):
                if to_call >= 0.3 * stack or eff_M < 25:
                    return self._raise(obs, obs.max_raise)
                return self._raise(obs, max(obs.min_raise, int(2.5 * mx)))
            if pct < 0.09 and raise_frac < 0.12:
                return ('call', 0) if 'call' in legal else self._passive(obs)
            if pct < 0.2 and raise_frac < 0.05:
                return ('call', 0) if 'call' in legal else self._passive(obs)
            return self._fold(obs)
        if self.i_limped_trap or (pct < 0.025):
            # premium: tiny 3-bet (keeps the raiser and stations in) unless it is already big
            if n_raises >= 2 or raise_frac > 0.25 or eff_M < 22:
                return self._raise(obs, obs.max_raise)
            if 'raise' in legal:
                target = int(mx * 2.2) + bb * n_callers
                if self.i_limped_trap:
                    target = int(mx * 3) + bb * n_callers
                return self._raise(obs, target)
            return ('call', 0) if 'call' in legal else self._passive(obs)
        if pct < 0.06:
            # strong but not premium: 3-bet small vs frequent raisers, call vs tight raisers
            if raiser >= 0 and self._aggr(raiser) > 0.25 and n_raises == 1 and 'raise' in legal and raise_frac < 0.15:
                return self._raise(obs, int(mx * 2.5) + bb * n_callers)
            if raise_frac <= 0.2:
                return ('call', 0) if 'call' in legal else self._passive(obs)
            return self._fold(obs)
        # speculative calls: suited/connected/pairs when the price is small and stacks deep
        hi = max(obs.hole[0] >> 2, obs.hole[1] >> 2); lo = min(obs.hole[0] >> 2, obs.hole[1] >> 2)
        suited = (obs.hole[0] & 3) == (obs.hole[1] & 3)
        pair = hi == lo
        spec = pair or (suited and (hi - lo <= 2 or hi == 12)) or (hi - lo == 1 and lo >= 5)
        if n_raises == 1 and 'call' in legal:
            if pct < 0.14 and raise_frac <= 0.10:
                return ('call', 0)
            if spec and raise_frac <= 0.06 and eff_M > 25 and (n_callers >= 1 or pct < 0.35):
                return ('call', 0)
            if 'check' not in legal and obs.bets[me] == bb and raise_frac <= 0.08 and pct < 0.30:
                return ('call', 0)  # BB defence vs small raises
        return self._fold(obs)

    # ------------------------------------------------------------------ postflop
    def _postflop(self, obs, t0, me, n, bb, stack, my_bet, mx, pot_total, opps, n_opp, margin):
        legal = obs.legal
        to_call = obs.to_call
        rnd = self.rng.random
        street = obs.street
        eq = self._equity(obs, n_opp, t0)
        # opponents who saw a raised pot hold better-than-random hands
        raised_pre = self.pfr_seat >= 0
        adj = eq
        if raised_pre:
            adj -= 0.03 * n_opp
        if n_opp >= 3:
            adj -= 0.02
        if to_call > 0:
            # someone bet: their hand is much better than random; tight/passive bettors even more so
            bettors = [i for i in opps if obs.bets[i] == mx]
            disc = 0.07
            if bettors:
                ar = min(self._raise_ratio(i) for i in bettors)
                disc += 0.07 if ar < 0.12 else 0.03 if ar < 0.25 else -0.02
            if street == 3:
                disc += 0.04  # bots rarely bluff rivers
            if street >= 2 and len([h for h in (obs.history or ()) if isinstance(h, tuple) and h[1][0] == 'raise']) >= 3:
                disc += 0.03  # multiple aggressive actions this hand
            adj -= disc
        adj = _clamp(adj, 0.0, 1.0)
        pot_after = pot_total + to_call
        station = max([self._callrate(i) for i in opps] or [0.5])
        folder = min([self._callrate(i) for i in opps] or [0.5])
        stack_pot = stack / float(max(1, pot_total))
        made = eval7(list(obs.hole) + list(obs.board))
        cat = made >> 20

        if to_call == 0:
            # ---- we can check or bet
            if adj >= 0.80:
                # value: big vs callers, polarised overbet with the nuts on later streets
                if cat >= 4 and street >= 2 and (station > 0.6 or rnd() < 0.5):
                    size = pot_total * (1.4 if stack_pot > 2.0 else 1.0)
                elif station > 0.65:
                    size = pot_total * 0.95
                else:
                    size = pot_total * 0.66
                if stack_pot < 1.6 and adj > 0.86:
                    size = stack  # just shove when short relative to pot
                return self._raise(obs, mx + int(size))
            if adj >= 0.60:
                # medium strength: small bet to deny equity / get value from worse
                if n_opp <= 2 or adj > 0.68:
                    size = pot_total * (0.5 if station > 0.6 else 0.35)
                    return self._raise(obs, mx + int(size))
                return ('check', 0)
            # bluffs / probes: small bets into folders; lead into the preflop raiser
            if n_opp == 1 and folder < 0.45:
                if (self.i_raised_pre and street == 1 and adj > 0.25 and rnd() < 0.75) or \
                        (not self.i_raised_pre and raised_pre and street == 1 and adj > 0.3 and rnd() < 0.4) or \
                        (adj > 0.35 and street == 2 and rnd() < 0.3):
                    return self._raise(obs, mx + int(pot_total * 0.33))
            if n_opp == 1 and self.i_raised_pre and street == 1 and adj > 0.30 and rnd() < 0.5:
                return self._raise(obs, mx + int(pot_total * 0.33))
            # river: polarised big bet with air into a single folder who has shown no strength
            if n_opp == 1 and street == 3 and folder < 0.40 and adj < 0.30 and stack > pot_total and rnd() < 0.30:
                return self._raise(obs, mx + int(pot_total * 0.8))
            return ('check', 0)

        # ---- facing a bet
        odds = to_call / float(pot_after) if pot_after > 0 else 1.0
        bet_frac = to_call / float(max(1, pot_total - to_call)) if pot_total > to_call else 1.0
        # stack-risk margin: the deeper we are, the more equity we demand before committing the stack
        M = (stack + my_bet) / float(bb)
        risk = min(1.0, to_call / float(max(1, stack)))
        depth_pen = 0.12 if M > 30 else 0.08 if M > 18 else 0.03 if M > 12 else 0.0
        # raise for value
        if adj >= 0.78 and 'raise' in legal:
            commit = stack <= 3 * pot_after
            if commit and adj < 0.80 + depth_pen * 0.6:
                return ('call', 0) if adj >= odds + 0.04 + margin + depth_pen * risk else ('fold', 0)
            if adj >= 0.9 or stack <= 2.5 * pot_after:
                return self._raise(obs, obs.max_raise if commit else mx + int(pot_after * 1.2))
            if station > 0.55 or rnd() < 0.6:
                return self._raise(obs, mx + int(pot_after * 0.9))
            return ('call', 0)
        # semi-bluff raise with strong draws vs folders, single opponent, flop only
        if street == 1 and n_opp == 1 and folder < 0.4 and 0.38 <= adj < 0.55 and bet_frac <= 0.6 and 'raise' in legal and rnd() < 0.35 and stack > 4 * pot_after:
            return self._raise(obs, mx + int(pot_after * 0.9))
        # call with equity above pot odds plus margin (bigger margin when the bet is huge / ICM / deep)
        need = odds + 0.04 + margin + depth_pen * risk
        if to_call >= 0.5 * stack:
            need += 0.04
        if bet_frac > 1.2:
            need += 0.03
        if adj >= need:
            return ('call', 0)
        # calling station exploitation: do not pay off, but call very small bets with any pair/draw
        if adj >= odds - 0.02 and bet_frac <= 0.25 and street < 3:
            return ('call', 0)
        return ('fold', 0)
