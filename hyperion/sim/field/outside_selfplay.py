# Origin: the climb's outside field (docs/drills/field/outside_selfplay.md is the builder's log). A fresh coding agent,
# playing a solo student who let the agent self-play-tune in its own simulator for the hour,
# built it in one hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# 5e739fa4f8f1833d2ea7212a28ef9aef (its FROZEN.md5) and copied here unchanged apart from this header. The archive is docs/drills/field/outside_selfplay_bot.py.
# Played through hyperion.sim.bestiary.Outside*Bot (registry name `out_selfplay`); a judge-like field, never tuned on.
# Do not edit; a new bot is a new file.
"""rival_bot: 8-max NLHE SNG bot. Preflop tables (own MC), push/fold short, MC postflop equity
vs opponent ranges narrowed by observed actions. Pure stdlib."""
import gc
import random
import time
try:
    from kit import Agent as _Base
except Exception:  # pragma: no cover
    _Base = object

DEBUG = False
_BLOB = "0,0,0,0.4517,0.510,0.457,0.474,0.412,0.335,0.224;1,0,0,0.9955,0.315,0.296,0.295,0.285,0.230,0.128;1,0,1,0.9442,0.372,0.357,0.327,0.307,0.270,0.186;1,1,0,0.3688,0.534,0.508,0.438,0.409,0.362,0.231;2,0,0,0.9864,0.330,0.310,0.300,0.277,0.229,0.144;2,0,1,0.9140,0.349,0.357,0.374,0.323,0.270,0.200;2,1,0,0.9502,0.333,0.326,0.329,0.297,0.264,0.164;2,1,1,0.9110,0.398,0.348,0.344,0.320,0.272,0.213;2,2,0,0.2466,0.561,0.503,0.458,0.427,0.350,0.255;3,0,0,0.9683,0.325,0.321,0.303,0.295,0.234,0.159;3,0,1,0.8446,0.388,0.345,0.337,0.349,0.268,0.200;3,1,0,0.9020,0.367,0.335,0.324,0.293,0.237,0.182;3,1,1,0.7903,0.374,0.379,0.357,0.332,0.278,0.218;3,2,0,0.8597,0.387,0.349,0.334,0.305,0.231,0.195;3,2,1,0.7873,0.428,0.395,0.332,0.351,0.302,0.234;3,3,0,0.1003,0.624,0.538,0.496,0.434,0.358,0.274;4,0,0,0.9774,0.341,0.309,0.285,0.286,0.222,0.149;4,0,1,0.9080,0.395,0.369,0.320,0.302,0.255,0.175;4,1,0,0.9291,0.361,0.313,0.300,0.293,0.211,0.174;4,1,1,0.8024,0.406,0.370,0.343,0.323,0.260,0.208;4,2,0,0.8205,0.389,0.344,0.337,0.287,0.256,0.177;4,2,1,0.7843,0.426,0.403,0.358,0.340,0.277,0.219;4,3,0,0.8839,0.393,0.383,0.327,0.301,0.259,0.191;4,3,1,0.7572,0.425,0.410,0.381,0.349,0.297,0.235;4,4,0,0.0867,0.613,0.557,0.516,0.466,0.371,0.302;5,0,0,0.9593,0.354,0.289,0.289,0.282,0.216,0.152;5,0,1,0.8658,0.359,0.328,0.337,0.308,0.248,0.165;5,1,0,0.9201,0.351,0.317,0.309,0.288,0.218,0.152;5,1,1,0.8778,0.401,0.359,0.319,0.321,0.271,0.206;5,2,0,0.8929,0.387,0.329,0.299,0.290,0.241,0.170;5,2,1,0.7029,0.392,0.381,0.352,0.316,0.277,0.202;5,3,0,0.8296,0.391,0.331,0.336,0.292,0.257,0.199;5,3,1,0.6486,0.458,0.387,0.364,0.344,0.291,0.236;5,4,0,0.7089,0.414,0.352,0.333,0.344,0.270,0.204;5,4,1,0.6244,0.443,0.372,0.395,0.350,0.303,0.260;5,5,0,0.0370,0.655,0.576,0.530,0.489,0.355,0.348;6,0,0,0.9382,0.370,0.304,0.274,0.267,0.230,0.158;6,0,1,0.8145,0.395,0.341,0.321,0.331,0.240,0.189;6,1,0,0.8718,0.376,0.311,0.275,0.286,0.227,0.145;6,1,1,0.7722,0.385,0.348,0.311,0.291,0.256,0.202;6,2,0,0.8084,0.401,0.338,0.309,0.286,0.245,0.174;6,2,1,0.7692,0.423,0.350,0.366,0.344,0.277,0.214;6,3,0,0.7783,0.407,0.330,0.315,0.303,0.253,0.204;6,3,1,0.6606,0.428,0.372,0.334,0.332,0.308,0.230;6,4,0,0.7632,0.427,0.355,0.343,0.298,0.255,0.206;6,4,1,0.6214,0.447,0.414,0.360,0.356,0.280,0.260;6,5,0,0.6546,0.478,0.367,0.372,0.355,0.287,0.227;6,5,1,0.5732,0.464,0.382,0.379,0.356,0.299,0.272;6,6,0,0.0294,0.694,0.629,0.533,0.502,0.381,0.391;7,0,0,0.8386,0.408,0.309,0.296,0.267,0.233,0.163;7,0,1,0.7149,0.409,0.354,0.327,0.309,0.267,0.204;7,1,0,0.8507,0.396,0.333,0.288,0.286,0.223,0.156;7,1,1,0.7541,0.430,0.355,0.340,0.322,0.265,0.219;7,2,0,0.7964,0.405,0.321,0.273,0.296,0.243,0.177;7,2,1,0.6998,0.447,0.363,0.343,0.291,0.262,0.210;7,3,0,0.7391,0.435,0.345,0.304,0.282,0.254,0.193;7,3,1,0.6033,0.447,0.378,0.347,0.341,0.305,0.225;7,4,0,0.6848,0.410,0.352,0.321,0.290,0.252,0.205;7,4,1,0.5490,0.455,0.381,0.335,0.347,0.305,0.257;7,5,0,0.6124,0.448,0.356,0.339,0.306,0.256,0.220;7,5,1,0.4359,0.489,0.379,0.370,0.342,0.309,0.262;7,6,0,0.5671,0.456,0.387,0.357,0.323,0.290,0.255;7,6,1,0.5068,0.484,0.406,0.386,0.365,0.296,0.274;7,7,0,0.0249,0.721,0.644,0.578,0.557,0.486,0.409;8,0,0,0.7481,0.418,0.319,0.304,0.281,0.208,0.183;8,0,1,0.6365,0.483,0.334,0.321,0.331,0.253,0.235;8,1,0,0.7210,0.409,0.317,0.305,0.309,0.226,0.177;8,1,1,0.6184,0.467,0.356,0.348,0.321,0.260,0.211;8,2,0,0.7300,0.453,0.329,0.309,0.303,0.233,0.181;8,2,1,0.6063,0.469,0.342,0.354,0.329,0.264,0.230;8,3,0,0.6667,0.422,0.317,0.311,0.301,0.238,0.196;8,3,1,0.5852,0.489,0.370,0.344,0.322,0.275,0.220;8,4,0,0.6305,0.467,0.359,0.346,0.301,0.269,0.216;8,4,1,0.5611,0.502,0.385,0.387,0.318,0.285,0.259;8,5,0,0.5128,0.500,0.371,0.338,0.309,0.252,0.228;8,5,1,0.4268,0.510,0.380,0.370,0.364,0.290,0.279;8,6,0,0.4585,0.500,0.368,0.345,0.320,0.284,0.239;8,6,1,0.4057,0.516,0.415,0.389,0.357,0.331,0.292;8,7,0,0.3846,0.512,0.394,0.364,0.351,0.294,0.277;8,7,1,0.3107,0.525,0.439,0.409,0.360,0.328,0.311;8,8,0,0.0204,0.750,0.682,0.641,0.584,0.507,0.449;9,0,0,0.6757,0.448,0.319,0.302,0.293,0.263,0.189;9,0,1,0.6003,0.477,0.351,0.358,0.310,0.293,0.230;9,1,0,0.6938,0.431,0.344,0.285,0.278,0.257,0.197;9,1,1,0.5882,0.492,0.371,0.348,0.316,0.266,0.227;9,2,0,0.5943,0.490,0.363,0.314,0.279,0.248,0.209;9,2,1,0.5460,0.504,0.387,0.350,0.326,0.320,0.243;9,3,0,0.6425,0.460,0.343,0.322,0.296,0.267,0.201;9,3,1,0.5038,0.507,0.387,0.336,0.321,0.315,0.240;9,4,0,0.5219,0.483,0.349,0.303,0.291,0.277,0.205;9,4,1,0.4389,0.513,0.373,0.331,0.334,0.311,0.257;9,5,0,0.4977,0.523,0.368,0.337,0.306,0.273,0.220;9,5,1,0.3499,0.531,0.373,0.363,0.327,0.309,0.265;9,6,0,0.4449,0.526,0.391,0.322,0.311,0.295,0.277;9,6,1,0.3756,0.557,0.410,0.356,0.347,0.319,0.284;9,7,0,0.4118,0.527,0.419,0.361,0.333,0.313,0.268;9,7,1,0.2896,0.558,0.452,0.403,0.392,0.355,0.331;9,8,0,0.2805,0.525,0.431,0.376,0.347,0.316,0.325;9,8,1,0.2217,0.566,0.460,0.416,0.389,0.343,0.353;9,9,0,0.0158,0.775,0.721,0.663,0.662,0.588,0.494;10,0,0,0.5400,0.462,0.377,0.333,0.298,0.268,0.199;10,0,1,0.4646,0.498,0.367,0.371,0.331,0.297,0.242;10,1,0,0.5792,0.486,0.364,0.310,0.310,0.260,0.202;10,1,1,0.4299,0.484,0.413,0.347,0.312,0.283,0.249;10,2,0,0.5309,0.499,0.375,0.320,0.304,0.290,0.208;10,2,1,0.3906,0.517,0.405,0.370,0.336,0.297,0.259;10,3,0,0.5551,0.495,0.394,0.325,0.305,0.290,0.226;10,3,1,0.4329,0.532,0.427,0.374,0.333,0.287,0.256;10,4,0,0.4706,0.507,0.395,0.333,0.312,0.272,0.216;10,4,1,0.3937,0.557,0.430,0.377,0.346,0.323,0.268;10,5,0,0.4208,0.506,0.413,0.322,0.284,0.286,0.234;10,5,1,0.3529,0.537,0.438,0.375,0.360,0.299,0.285;10,6,0,0.2097,0.531,0.418,0.346,0.313,0.283,0.264;10,6,1,0.2745,0.551,0.446,0.390,0.340,0.317,0.289;10,7,0,0.2956,0.541,0.456,0.377,0.334,0.289,0.297;10,7,1,0.2187,0.559,0.453,0.416,0.367,0.361,0.325;10,8,0,0.2594,0.577,0.486,0.424,0.366,0.319,0.328;10,8,1,0.1674,0.587,0.507,0.444,0.393,0.349,0.351;10,9,0,0.1614,0.613,0.485,0.457,0.347,0.357,0.334;10,9,1,0.1403,0.607,0.515,0.463,0.378,0.368,0.368;10,10,0,0.0113,0.795,0.754,0.719,0.704,0.629,0.530;11,0,0,0.4796,0.518,0.404,0.362,0.275,0.266,0.229;11,0,1,0.3650,0.554,0.416,0.373,0.327,0.282,0.260;11,1,0,0.4887,0.517,0.403,0.375,0.297,0.265,0.228;11,1,1,0.3786,0.542,0.437,0.417,0.333,0.318,0.284;11,2,0,0.3348,0.515,0.404,0.354,0.328,0.262,0.233;11,2,1,0.3725,0.550,0.464,0.418,0.318,0.315,0.274;11,3,0,0.3997,0.528,0.438,0.366,0.310,0.270,0.242;11,3,1,0.2504,0.548,0.452,0.421,0.342,0.324,0.279;11,4,0,0.3590,0.520,0.477,0.372,0.320,0.278,0.254;11,4,1,0.2866,0.581,0.488,0.409,0.337,0.290,0.304;11,5,0,0.3047,0.537,0.454,0.385,0.318,0.280,0.260;11,5,1,0.2157,0.581,0.475,0.431,0.346,0.329,0.287;11,6,0,0.2685,0.556,0.485,0.407,0.312,0.273,0.276;11,6,1,0.2534,0.564,0.499,0.418,0.347,0.314,0.312;11,7,0,0.1916,0.582,0.494,0.416,0.331,0.289,0.292;11,7,1,0.1523,0.589,0.536,0.457,0.361,0.347,0.338;11,8,0,0.1825,0.594,0.542,0.470,0.371,0.320,0.332;11,8,1,0.0935,0.652,0.557,0.517,0.379,0.335,0.347;11,9,0,0.1463,0.599,0.534,0.473,0.372,0.344,0.341;11,9,1,0.1161,0.644,0.558,0.507,0.432,0.377,0.360;11,10,0,0.1101,0.613,0.553,0.522,0.428,0.363,0.366;11,10,1,0.0965,0.638,0.593,0.546,0.432,0.367,0.372;11,11,0,0.0068,0.819,0.805,0.771,0.722,0.704,0.590;12,0,0,0.3167,0.541,0.506,0.424,0.357,0.271,0.273;12,0,1,0.2247,0.545,0.532,0.475,0.375,0.323,0.290;12,1,0,0.3439,0.553,0.494,0.437,0.357,0.294,0.266;12,1,1,0.1704,0.566,0.534,0.451,0.390,0.317,0.304;12,2,0,0.3258,0.573,0.499,0.441,0.355,0.294,0.257;12,2,1,0.1765,0.606,0.515,0.480,0.382,0.323,0.322;12,3,0,0.2398,0.562,0.521,0.461,0.370,0.285,0.266;12,3,1,0.1192,0.594,0.536,0.483,0.435,0.336,0.310;12,4,0,0.2006,0.569,0.525,0.459,0.366,0.276,0.265;12,4,1,0.1735,0.606,0.535,0.486,0.395,0.316,0.306;12,5,0,0.2308,0.576,0.517,0.475,0.355,0.279,0.297;12,5,1,0.1041,0.597,0.550,0.503,0.403,0.313,0.323;12,6,0,0.1252,0.581,0.556,0.504,0.391,0.280,0.297;12,6,1,0.1554,0.640,0.585,0.511,0.423,0.306,0.333;12,7,0,0.1342,0.626,0.582,0.531,0.401,0.289,0.307;12,7,1,0.0905,0.642,0.598,0.555,0.437,0.336,0.346;12,8,0,0.0618,0.620,0.608,0.572,0.464,0.345,0.338;12,8,1,0.0558,0.666,0.629,0.576,0.500,0.365,0.376;12,9,0,0.0799,0.611,0.646,0.567,0.483,0.424,0.347;12,9,1,0.0407,0.657,0.623,0.608,0.512,0.447,0.392;12,10,0,0.0709,0.664,0.636,0.601,0.558,0.438,0.355;12,10,1,0.0528,0.668,0.643,0.626,0.571,0.481,0.390;12,11,0,0.0468,0.623,0.679,0.644,0.602,0.486,0.382;12,11,1,0.0332,0.676,0.671,0.651,0.621,0.519,0.410;12,12,0,0.0023,0.851,0.861,0.848,0.848,0.821,0.634"

# ---------------- evaluator ----------------
_POP = [bin(i).count('1') for i in range(8192)]
_STR = [-1] * 8192
for _m in range(8192):
    for _h in range(12, 3, -1):
        _need = 0x1F << (_h - 4)
        if _m & _need == _need:
            _STR[_m] = _h
            break
    else:
        if _m & 0x100F == 0x100F:
            _STR[_m] = 3


def _top(m, k):
    v = 0
    n = 0
    for r in range(12, -1, -1):
        if m >> r & 1:
            v = v << 4 | r
            n += 1
            if n == k:
                break
    return v


_TOP5 = [_top(m, 5) for m in range(8192)]


def _ev(cards):
    rc = [0] * 13
    sm = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        rc[r] += 1
        sm[c & 3] |= 1 << r
    for s in sm:
        if _POP[s] >= 5:
            st = _STR[s]
            if st >= 0:
                return 0x800000 | st
            return 0x500000 | _TOP5[s]
    m = sm[0] | sm[1] | sm[2] | sm[3]
    q = t = p1 = p2 = t2 = -1
    for r in range(12, -1, -1):
        n = rc[r]
        if n < 2:
            continue
        if n == 4:
            q = r
        elif n == 3:
            if t < 0:
                t = r
            elif t2 < 0:
                t2 = r
        else:
            if p1 < 0:
                p1 = r
            elif p2 < 0:
                p2 = r
    if q >= 0:
        k = m & ~(1 << q)
        return 0x700000 | q << 4 | (k.bit_length() - 1)
    if t >= 0:
        pp = p1 if p1 > t2 else t2
        if pp >= 0:
            return 0x600000 | t << 4 | pp
    st = _STR[m]
    if st >= 0:
        return 0x400000 | st
    if t >= 0:
        return 0x300000 | t << 8 | _top(m & ~(1 << t), 2)
    if p2 >= 0:
        k = m & ~(1 << p1) & ~(1 << p2)
        return 0x200000 | p1 << 8 | p2 << 4 | (k.bit_length() - 1)
    if p1 >= 0:
        return 0x100000 | p1 << 12 | _top(m & ~(1 << p1), 3)
    return _TOP5[m]


# ---------------- preflop tables ----------------
_RG = (1.0, 0.5, 0.3, 0.15, 0.07)
_CLS = {}
for _row in _BLOB.split(';'):
    _f = _row.split(',')
    _CLS[(int(_f[0]), int(_f[1]), int(_f[2]))] = (float(_f[3]), tuple(float(x) for x in _f[4:9]), float(_f[9]))
# per card pair lookup
_PCT = [[1.0] * 52 for _ in range(52)]
_INFO = {}
for _a in range(52):
    for _b in range(52):
        if _a == _b:
            continue
        _ra, _rb = _a >> 2, _b >> 2
        _hi, _lo = (_ra, _rb) if _ra >= _rb else (_rb, _ra)
        _s = 1 if (_a & 3) == (_b & 3) and _hi != _lo else 0
        _PCT[_a][_b] = _CLS[(_hi, _lo, _s)][0]
        _INFO[(_a, _b)] = _CLS[(_hi, _lo, _s)]


def _eq_vs_range(info, w):
    eqs = info[1]
    if w >= 1.0:
        return eqs[0]
    if w <= 0.07:
        return eqs[4]
    for i in range(4):
        hi, lo = _RG[i], _RG[i + 1]
        if lo <= w <= hi:
            f = (w - lo) / (hi - lo)
            return eqs[i + 1] + f * (eqs[i] - eqs[i + 1])
    return eqs[0]


P = {
    'push_c': 10.0, 'commit_bb': 20.0, 'push_bb': 13.0,
    'open': (0.0, 0.40, 0.32, 0.24, 0.19, 0.16, 0.13, 0.11, 0.10),
    'open_size': 2.5, 'threebet_pct': 0.035, 'call_pct': 0.12,
    'call_margin': 0.18, 'v_bet': 0.62, 'v_raise': 0.78, 'cbet_freq': 0.3,
    'bet_frac': 0.7, 'tight_pen': 0.4, 'budget_ns': 140000, 'max_samples': 150,
    'range_mult': 2.0, 'pre_margin': 0.35, 'pre_lo': 0.35, 'fold_adj': 0.0, 'limp_pct': 0.45, 'sb_pct': 0.5, 'thin_adj': 0.0, 'post_lo': 0.18,
}


class Bot(_Base):
    def __init__(self, params=None):
        self.p = dict(P)
        if params:
            self.p.update(params)
        self.rng = random.Random(12345)
        self.new_table({}, 0, 8)

    def new_table(self, rules, seat, n_players):
        n = n_players if isinstance(n_players, int) and n_players > 0 else 8
        self.n = max(n, 10)
        self.seat = seat
        self.acts = [0] * 16
        self.raises = [0] * 16
        self.folds = [0] * 16
        self.calls = [0] * 16
        self.cur_hand = -1
        self.hidx = 0
        self.pf_aggr = False
        self.hand_raisers = set()
        self.hand_callers = set()

    def hand_end(self, result):
        pass

    # ---------- stats ----------
    def _update(self, obs):
        if obs.hand_no != self.cur_hand:
            self.cur_hand = obs.hand_no
            self.hidx = 0
            self.pf_aggr = False
            self.hand_raisers = set()
            self.hand_callers = set()
        h = obs.history or ()
        me = obs.seat
        for i in range(self.hidx, len(h)):
            try:
                s, a = h[i]
                k = a[0]
            except Exception:
                continue
            if not isinstance(s, int) or s < 0 or s >= 16:
                continue
            if s == me:
                if k == 'raise' and obs.street == 0:
                    self.pf_aggr = True
                continue
            if k == 'raise':
                self.acts[s] += 1
                self.raises[s] += 1
                self.hand_raisers.add(s)
            elif k == 'call':
                self.acts[s] += 1
                self.calls[s] += 1
                self.hand_callers.add(s)
            elif k == 'fold':
                self.acts[s] += 1
                self.folds[s] += 1
            elif k == 'check':
                self.acts[s] += 1
        self.hidx = len(h)

    def _rr(self, s):
        # smoothed raise rate
        return (self.raises[s] + 0.12 * 15) / (self.acts[s] + 15.0)

    def _fr(self, s):
        return (self.folds[s] + 0.45 * 15) / (self.acts[s] + 15.0)

    # ---------- act ----------
    def act(self, obs):
        ge = gc.isenabled()
        if ge:
            gc.disable()
        try:
            return self._act(obs)
        finally:
            if ge:
                gc.enable()

    def _act(self, obs):
        try:
            self._update(obs)
            if obs.street == 0:
                a = self._pre(obs)
            else:
                a = self._post(obs)
            return self._legalize(obs, a)
        except Exception:
            if DEBUG:
                raise
            return self._safe(obs)

    def _safe(self, obs):
        lg = obs.legal
        if 'check' in lg:
            return ('check', 0)
        return ('fold', 0)

    def _legalize(self, obs, a):
        k, amt = a
        lg = obs.legal
        if k == 'raise':
            if 'raise' not in lg:
                k = 'call' if 'call' in lg else 'check'
            else:
                amt = int(amt)
                if amt < obs.min_raise:
                    amt = obs.min_raise
                if amt > obs.max_raise:
                    amt = obs.max_raise
                if amt >= 0.8 * obs.max_raise:
                    amt = obs.max_raise
                return ('raise', int(amt))
        if k == 'call' and 'call' not in lg:
            k = 'check'
        if k == 'check' and 'check' not in lg:
            k = 'fold'
        if k == 'fold' and 'check' in lg:
            k = 'check'
        if k not in lg:
            return self._safe(obs)
        return (k, 0)

    def _raise_to(self, obs, amt):
        return ('raise', amt)

    def _pre(self, obs):
        p = self.p
        me = obs.seat
        n = len(obs.stacks)
        sb, bb = obs.blinds if obs.blinds else (10, 20)
        bb = max(1, bb)
        info = _INFO[(obs.hole[0], obs.hole[1])]
        pct = info[0]
        bets = obs.bets
        stacks = obs.stacks
        my_tot = stacks[me] + bets[me]
        opp = [i for i in range(n) if i != me and obs.in_hand[i]]
        opp_max = max([stacks[i] + bets[i] for i in opp] or [0])
        eff = min(my_tot, opp_max) / float(bb)
        mx = max(bets)
        to_call = obs.to_call
        pot_tot = obs.pot + sum(bets)
        # seat order from SB
        alive = [i for i in range(n) if (stacks[i] > 0 or bets[i] > 0 or obs.in_hand[i])]
        order = sorted(alive, key=lambda i: (i - obs.button - 1) % n)
        if len(order) == 2:
            order = [obs.button] + [i for i in order if i != obs.button]
        idx = order.index(me) if me in order else 0
        L = len(order)
        if L == 2:
            behind = 1 if idx == 0 else 0
        elif idx >= 2:
            behind = (L - 1 - idx) + 2
        else:
            behind = 1 - idx
        raisers = [s for s in self.hand_raisers if obs.in_hand[s]]
        unopened = mx <= bb and not raisers
        if unopened:
            limpers = sum(1 for i in opp if bets[i] >= bb) - (1 if behind >= 0 and idx != 1 else 0)
            limpers = max(0, limpers)
            if eff <= p['push_bb']:
                fr = sum(self._fr(i) for i in opp) / max(1, len(opp))
                thr = p['push_c'] * (1.0 + p['fold_adj'] * (fr - 0.45)) / (max(eff, 1.0) * (behind + 0.5) ** 0.8)
                if limpers:
                    thr *= 0.6
                if pct <= thr:
                    return ('raise', obs.max_raise)
                return ('check', 0) if to_call == 0 else ('fold', 0)
            op = p['open'][min(behind, 8)] if behind > 0 else 0.12
            if limpers:
                op *= 0.8
            if pct <= op:
                amt = int(bb * (p['open_size'] + limpers))
                if behind == 0:
                    amt = int(bb * (3 + limpers))
                return ('raise', amt)
            if to_call == 0:
                return ('check', 0)
            if limpers and to_call <= bb and pct <= p['limp_pct'] and eff > 30:
                return ('call', 0)
            if idx == 0 and to_call <= bb // 2 + 1 and pct <= p['sb_pct'] and eff > 25:
                return ('call', 0)
            return ('fold', 0)
        # facing a raise
        nr = max(1, len(raisers))
        if raisers:
            w = min(p['range_mult'] * self._rr(s) for s in raisers)
        else:
            w = 0.3
        if nr >= 2:
            w *= 0.5
        w = max(0.05, min(1.0, w))
        eq = _eq_vs_range(info, w)
        n_in = len(opp)
        if n_in >= 3:
            eq = eq * (info[2] / max(0.05, info[1][0])) ** 0.5
        need = to_call / float(pot_tot + to_call)
        commit = to_call >= 0.35 * my_tot or eff <= p['commit_bb'] or mx >= 0.35 * opp_max
        if commit:
            risk = min(my_tot, opp_max) / float(max(1, my_tot))
            marg = p['pre_lo'] + (p['pre_margin'] - p['pre_lo']) * risk
            if eq >= need + marg:
                if eq >= 0.55 and obs.max_raise > mx:
                    return ('raise', obs.max_raise)
                return ('call', 0)
            return ('fold', 0)
        # deep facing raise
        tb = p['threebet_pct'] if w < 0.4 else p['threebet_pct'] * 2.5
        if pct <= tb:
            amt = int(mx * 3 + (pot_tot - mx))
            return ('raise', amt)
        if (pct <= p['call_pct'] or (w >= 0.6 and eq >= need + 0.05)) and to_call <= 0.15 * my_tot:
            return ('call', 0)
        # set mining
        if info[0] < 0.6 and obs.hole[0] >> 2 == obs.hole[1] >> 2 and to_call <= 0.06 * min(my_tot, opp_max):
            return ('call', 0)
        return ('check', 0) if to_call == 0 else ('fold', 0)

    def _equity(self, obs, opp):
        p = self.p
        hole = obs.hole
        board = list(obs.board)
        dead = set(hole) | set(board)
        deck = [c for c in range(52) if c not in dead]
        widths = []
        for s in opp:
            if s in self.hand_raisers:
                w = max(0.12, min(1.0, p['range_mult'] * self._rr(s) * 1.2))
            elif s in self.hand_callers:
                w = max(0.3, min(1.0, 0.6 + self._rr(s)))
            else:
                w = 1.0
            widths.append(w)
        need = 5 - len(board)
        rng = self.rng
        t0 = time.perf_counter_ns()
        budget = p['budget_ns']
        maxs = p['max_samples']
        wins = 0.0
        nsm = 0
        hb = list(hole) + board
        mine0 = -1
        pct = _PCT
        nd = len(deck)
        while nsm < maxs:
            used = set()
            hands = []
            for w in widths:
                for _try in range(4):
                    a = deck[rng.randrange(nd)]
                    b = deck[rng.randrange(nd)]
                    if a == b or a in used or b in used:
                        continue
                    if pct[a][b] <= w or _try == 3:
                        break
                while a == b or a in used or b in used:
                    a = deck[rng.randrange(nd)]
                    b = deck[rng.randrange(nd)]
                used.add(a)
                used.add(b)
                hands.append((a, b))
            run = []
            while len(run) < need:
                c = deck[rng.randrange(nd)]
                if c not in used:
                    used.add(c)
                    run.append(c)
            if need:
                full = board + run
                mine = _ev(hb + run)
            else:
                full = board
                if mine0 < 0:
                    mine0 = _ev(hb)
                mine = mine0
            best = 0
            ties = 0
            lose = False
            for (a, b) in hands:
                v = _ev([a, b] + full)
                if v > mine:
                    lose = True
                    break
                if v == mine:
                    ties += 1
            if not lose:
                wins += 1.0 / (1 + ties)
            nsm += 1
            if time.perf_counter_ns() - t0 > budget:
                break
        return wins / max(1, nsm)

    def _post(self, obs):
        p = self.p
        me = obs.seat
        n = len(obs.stacks)
        bets = obs.bets
        stacks = obs.stacks
        opp = [i for i in range(n) if i != me and obs.in_hand[i]]
        if not opp:
            return ('check', 0)
        eq = self._equity(obs, opp)
        pot_tot = obs.pot + sum(bets)
        to_call = obs.to_call
        mx = max(bets)
        my_tot = stacks[me] + bets[me]
        if to_call == 0:
            fr = sum(self._fr(i) for i in opp) / len(opp)
            vb = p['v_bet'] - p['thin_adj'] * max(0.0, 0.45 - fr)
            if eq >= vb:
                size = int(p['bet_frac'] * pot_tot)
                if stacks[me] <= 1.3 * pot_tot:
                    return ('raise', obs.max_raise)
                return ('raise', max(size, obs.min_raise))
            if self.pf_aggr and len(opp) == 1 and obs.street == 1 and self.rng.random() < p['cbet_freq']:
                f = self._fr(opp[0])
                if eq >= 0.30 or f > 0.5:
                    return ('raise', max(int(0.5 * pot_tot), obs.min_raise))
            return ('check', 0)
        need = to_call / float(pot_tot + to_call)
        bettors = [s for s in opp if bets[s] > bets[me]]
        aggr = max([self._rr(s) for s in bettors] or [0.12])
        pen = p['tight_pen'] * max(0.0, 1.0 - aggr / 0.35)
        eqa = eq - pen
        if eqa >= p['v_raise'] and 'raise' in obs.legal:
            if stacks[me] <= 1.5 * (pot_tot + to_call):
                return ('raise', obs.max_raise)
            return ('raise', int(mx + (pot_tot + to_call)))
        risk = min(my_tot, max(stacks[s] + bets[s] for s in opp)) / float(max(1, my_tot))
        marg = p['post_lo'] + (p['call_margin'] - p['post_lo']) * risk
        if eqa >= need + marg:
            return ('call', 0)
        return ('fold', 0)
