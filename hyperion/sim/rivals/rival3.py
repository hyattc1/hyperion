# Origin: red-team drill 3 (docs/drills/redteam/redteam-3.md). Built blind in 35 minutes by an exploitation-first
# rival team against the same brief and kit interface as rivals 1 and 2, with no access to this repository or to
# either earlier rival; frozen at md5 4b36e8124818e110d659b9514f5975a0 and copied here unchanged apart from this
# header. The archived original is docs/drills/redteam/rival3_bot.py. It is played through
# hyperion.sim.bestiary.Rival3Bot (registry name `rival3`). It is the holdout: Hero is never tuned against it.
# Do not edit; a new rival is a new file.
"""rival_bot: read-and-exploit No-Limit SNG bot (stdlib only).
Baseline: equity-table preflop (push/fold when short), rule-based postflop.
Exploit layer: per-seat model built from obs.history (VPIP/PFR/fold-to-raise/3bet/shove/postflop folds,
dead-seat detection) that widens steals vs folders, isolates maniacs, never bluffs stations."""
try:
    from kit import Agent as _Base
except Exception:  # pragma: no cover
    _Base = object
# evaluator prototype (will be pasted into rival_bot.py)
_STR = [0]*8192
_TOP5 = [0]*8192
_PC = [0]*8192
for _m in range(8192):
    _PC[_m] = bin(_m).count('1')
    mm = (_m << 1) | ((_m >> 12) & 1)
    v = 0
    for hi in range(13, 3, -1):
        if (mm >> (hi - 4)) & 31 == 31:
            v = hi; break
    _STR[_m] = v
    k = 0; n = 0
    for r in range(12, -1, -1):
        if _m >> r & 1:
            k = (k << 4) | r; n += 1
            if n == 5: break
    while n < 5: k <<= 4; n += 1
    _TOP5[_m] = k

def ev7(cs):
    rc = [0]*13; sm = [0, 0, 0, 0]
    for c in cs:
        r = c >> 2; rc[r] += 1; sm[c & 3] |= 1 << r
    for m in sm:
        if _PC[m] >= 5:
            s = _STR[m]
            if s: return (8 << 20) | s
            return (5 << 20) | _TOP5[m]
    allm = sm[0] | sm[1] | sm[2] | sm[3]
    q = -1; t = []; p = []
    for r in range(12, -1, -1):
        n = rc[r]
        if n == 4: q = r
        elif n == 3: t.append(r)
        elif n == 2: p.append(r)
    if q >= 0:
        k = allm & ~(1 << q)
        return (7 << 20) | (q << 16) | (_TOP5[k] >> 16 << 12)
    if t:
        tr = t[0]
        pr = -1
        if len(t) > 1: pr = t[1]
        if p and p[0] > pr: pr = p[0]
        if pr >= 0: return (6 << 20) | (tr << 16) | (pr << 12)
    s = _STR[allm]
    if s: return (4 << 20) | s
    if t:
        tr = t[0]; k = allm & ~(1 << tr)
        return (3 << 20) | (tr << 16) | (_TOP5[k] >> 12 << 8)
    if len(p) >= 2:
        a, b = p[0], p[1]; k = allm & ~(1 << a) & ~(1 << b)
        return (2 << 20) | (a << 16) | (b << 12) | (_TOP5[k] >> 16 << 8)
    if p:
        a = p[0]; k = allm & ~(1 << a)
        return (1 << 20) | (a << 16) | (_TOP5[k] >> 8)
    return _TOP5[allm]
CLASSES = [(12, 12, 0), (12, 11, 1), (12, 11, 0), (12, 10, 1), (12, 10, 0), (12, 9, 1), (12, 9, 0), (12, 8, 1), (12, 8, 0), (12, 7, 1), (12, 7, 0), (12, 6, 1), (12, 6, 0), (12, 5, 1), (12, 5, 0), (12, 4, 1), (12, 4, 0), (12, 3, 1), (12, 3, 0), (12, 2, 1), (12, 2, 0), (12, 1, 1), (12, 1, 0), (12, 0, 1), (12, 0, 0), (11, 11, 0), (11, 10, 1), (11, 10, 0), (11, 9, 1), (11, 9, 0), (11, 8, 1), (11, 8, 0), (11, 7, 1), (11, 7, 0), (11, 6, 1), (11, 6, 0), (11, 5, 1), (11, 5, 0), (11, 4, 1), (11, 4, 0), (11, 3, 1), (11, 3, 0), (11, 2, 1), (11, 2, 0), (11, 1, 1), (11, 1, 0), (11, 0, 1), (11, 0, 0), (10, 10, 0), (10, 9, 1), (10, 9, 0), (10, 8, 1), (10, 8, 0), (10, 7, 1), (10, 7, 0), (10, 6, 1), (10, 6, 0), (10, 5, 1), (10, 5, 0), (10, 4, 1), (10, 4, 0), (10, 3, 1), (10, 3, 0), (10, 2, 1), (10, 2, 0), (10, 1, 1), (10, 1, 0), (10, 0, 1), (10, 0, 0), (9, 9, 0), (9, 8, 1), (9, 8, 0), (9, 7, 1), (9, 7, 0), (9, 6, 1), (9, 6, 0), (9, 5, 1), (9, 5, 0), (9, 4, 1), (9, 4, 0), (9, 3, 1), (9, 3, 0), (9, 2, 1), (9, 2, 0), (9, 1, 1), (9, 1, 0), (9, 0, 1), (9, 0, 0), (8, 8, 0), (8, 7, 1), (8, 7, 0), (8, 6, 1), (8, 6, 0), (8, 5, 1), (8, 5, 0), (8, 4, 1), (8, 4, 0), (8, 3, 1), (8, 3, 0), (8, 2, 1), (8, 2, 0), (8, 1, 1), (8, 1, 0), (8, 0, 1), (8, 0, 0), (7, 7, 0), (7, 6, 1), (7, 6, 0), (7, 5, 1), (7, 5, 0), (7, 4, 1), (7, 4, 0), (7, 3, 1), (7, 3, 0), (7, 2, 1), (7, 2, 0), (7, 1, 1), (7, 1, 0), (7, 0, 1), (7, 0, 0), (6, 6, 0), (6, 5, 1), (6, 5, 0), (6, 4, 1), (6, 4, 0), (6, 3, 1), (6, 3, 0), (6, 2, 1), (6, 2, 0), (6, 1, 1), (6, 1, 0), (6, 0, 1), (6, 0, 0), (5, 5, 0), (5, 4, 1), (5, 4, 0), (5, 3, 1), (5, 3, 0), (5, 2, 1), (5, 2, 0), (5, 1, 1), (5, 1, 0), (5, 0, 1), (5, 0, 0), (4, 4, 0), (4, 3, 1), (4, 3, 0), (4, 2, 1), (4, 2, 0), (4, 1, 1), (4, 1, 0), (4, 0, 1), (4, 0, 0), (3, 3, 0), (3, 2, 1), (3, 2, 0), (3, 1, 1), (3, 1, 0), (3, 0, 1), (3, 0, 0), (2, 2, 0), (2, 1, 1), (2, 1, 0), (2, 0, 1), (2, 0, 0), (1, 1, 0), (1, 0, 1), (1, 0, 0), (0, 0, 0)]
EQ_RAND = [0.855, 0.674, 0.644, 0.656, 0.651, 0.646, 0.639, 0.641, 0.629, 0.632, 0.61, 0.616, 0.602, 0.604, 0.583, 0.59, 0.576, 0.592, 0.587, 0.593, 0.569, 0.574, 0.551, 0.571, 0.546, 0.827, 0.63, 0.618, 0.623, 0.614, 0.613, 0.591, 0.601, 0.575, 0.585, 0.568, 0.579, 0.545, 0.566, 0.548, 0.56, 0.524, 0.546, 0.519, 0.543, 0.523, 0.525, 0.503, 0.794, 0.605, 0.576, 0.596, 0.568, 0.574, 0.559, 0.563, 0.545, 0.53, 0.519, 0.548, 0.509, 0.526, 0.503, 0.529, 0.49, 0.513, 0.486, 0.501, 0.479, 0.773, 0.572, 0.55, 0.551, 0.533, 0.528, 0.508, 0.521, 0.502, 0.514, 0.47, 0.506, 0.467, 0.488, 0.456, 0.484, 0.453, 0.479, 0.439, 0.754, 0.529, 0.503, 0.521, 0.485, 0.517, 0.474, 0.501, 0.459, 0.478, 0.438, 0.467, 0.429, 0.465, 0.421, 0.44, 0.418, 0.721, 0.514, 0.478, 0.495, 0.463, 0.481, 0.453, 0.45, 0.427, 0.432, 0.41, 0.434, 0.409, 0.43, 0.391, 0.699, 0.479, 0.452, 0.459, 0.432, 0.441, 0.411, 0.436, 0.401, 0.407, 0.376, 0.404, 0.362, 0.664, 0.458, 0.418, 0.438, 0.409, 0.428, 0.379, 0.4, 0.364, 0.381, 0.353, 0.633, 0.421, 0.394, 0.416, 0.368, 0.388, 0.361, 0.382, 0.343, 0.592, 0.413, 0.382, 0.391, 0.367, 0.373, 0.333, 0.571, 0.394, 0.356, 0.368, 0.339, 0.538, 0.36, 0.326, 0.5]
PCT = [0.0023, 0.0332, 0.0588, 0.0407, 0.0468, 0.0528, 0.0709, 0.0649, 0.0905, 0.0814, 0.1267, 0.1086, 0.1418, 0.1357, 0.1916, 0.1735, 0.2036, 0.1569, 0.1795, 0.1538, 0.2474, 0.2308, 0.2926, 0.2368, 0.3258, 0.0068, 0.0845, 0.1026, 0.0965, 0.1146, 0.1207, 0.1674, 0.1478, 0.2217, 0.1855, 0.2564, 0.1976, 0.3379, 0.2715, 0.3167, 0.2775, 0.3906, 0.3318, 0.4148, 0.3529, 0.3997, 0.3846, 0.4751, 0.0113, 0.1327, 0.2127, 0.1508, 0.2655, 0.2278, 0.2836, 0.2745, 0.3469, 0.3695, 0.4238, 0.3107, 0.4449, 0.3816, 0.4842, 0.3756, 0.5158, 0.4389, 0.5279, 0.5023, 0.552, 0.0158, 0.2338, 0.3047, 0.2986, 0.3635, 0.3786, 0.454, 0.4087, 0.4932, 0.4329, 0.5882, 0.46, 0.6003, 0.5219, 0.6365, 0.543, 0.6546, 0.5611, 0.6817, 0.0204, 0.3725, 0.4661, 0.4057, 0.537, 0.4299, 0.5792, 0.4992, 0.6214, 0.5641, 0.6908, 0.5943, 0.724, 0.6063, 0.7481, 0.6757, 0.7662, 0.0249, 0.4359, 0.5701, 0.5098, 0.6124, 0.546, 0.6456, 0.6697, 0.736, 0.7149, 0.7903, 0.7029, 0.8084, 0.7179, 0.8477, 0.0294, 0.5581, 0.6637, 0.6275, 0.7089, 0.6727, 0.7813, 0.6998, 0.8235, 0.8145, 0.8869, 0.8175, 0.9291, 0.037, 0.6305, 0.7572, 0.6968, 0.7994, 0.73, 0.8778, 0.8296, 0.9201, 0.8718, 0.9593, 0.0777, 0.7421, 0.8386, 0.7722, 0.8989, 0.8567, 0.9382, 0.8597, 0.9683, 0.1606, 0.7753, 0.8658, 0.8537, 0.911, 0.8929, 0.9864, 0.2406, 0.8326, 0.9502, 0.905, 0.9774, 0.3567, 0.9442, 0.9955, 0.506]
W = [0.03, 0.06, 0.1, 0.15, 0.22, 0.3, 0.4, 0.55, 0.75, 1.0]
EQW = [[0.81, 0.432, 0.386, 0.406, 0.351, 0.378, 0.349, 0.363, 0.332, 0.333, 0.287, 0.312, 0.268, 0.306, 0.267, 0.303, 0.266, 0.322, 0.272, 0.324, 0.285, 0.317, 0.266, 0.322, 0.278, 0.704, 0.383, 0.349, 0.379, 0.331, 0.334, 0.311, 0.292, 0.269, 0.274, 0.248, 0.274, 0.242, 0.288, 0.232, 0.291, 0.238, 0.274, 0.24, 0.261, 0.246, 0.254, 0.232, 0.603, 0.334, 0.32, 0.334, 0.292, 0.291, 0.246, 0.255, 0.219, 0.259, 0.22, 0.26, 0.223, 0.258, 0.22, 0.249, 0.215, 0.24, 0.207, 0.252, 0.199, 0.505, 0.316, 0.275, 0.283, 0.231, 0.244, 0.208, 0.242, 0.205, 0.245, 0.194, 0.233, 0.195, 0.229, 0.197, 0.237, 0.179, 0.225, 0.175, 0.401, 0.264, 0.226, 0.233, 0.188, 0.233, 0.197, 0.23, 0.183, 0.21, 0.173, 0.215, 0.168, 0.202, 0.169, 0.197, 0.167, 0.301, 0.224, 0.178, 0.219, 0.172, 0.21, 0.168, 0.195, 0.166, 0.185, 0.144, 0.186, 0.143, 0.183, 0.134, 0.196, 0.21, 0.166, 0.189, 0.166, 0.19, 0.157, 0.176, 0.132, 0.158, 0.1, 0.164, 0.127, 0.184, 0.199, 0.177, 0.212, 0.162, 0.182, 0.156, 0.179, 0.138, 0.159, 0.11, 0.198, 0.211, 0.184, 0.197, 0.163, 0.189, 0.147, 0.172, 0.123, 0.207, 0.222, 0.176, 0.199, 0.159, 0.19, 0.143, 0.189, 0.201, 0.163, 0.191, 0.137, 0.187, 0.171, 0.14, 0.187], [0.846, 0.522, 0.496, 0.425, 0.386, 0.363, 0.333, 0.35, 0.321, 0.338, 0.285, 0.324, 0.281, 0.292, 0.26, 0.305, 0.265, 0.314, 0.284, 0.318, 0.275, 0.316, 0.275, 0.3, 0.268, 0.701, 0.371, 0.328, 0.379, 0.326, 0.358, 0.324, 0.333, 0.297, 0.333, 0.292, 0.312, 0.272, 0.313, 0.275, 0.318, 0.286, 0.32, 0.268, 0.308, 0.266, 0.289, 0.266, 0.622, 0.358, 0.326, 0.36, 0.319, 0.328, 0.277, 0.31, 0.28, 0.282, 0.251, 0.294, 0.257, 0.295, 0.267, 0.297, 0.251, 0.295, 0.251, 0.285, 0.253, 0.551, 0.362, 0.341, 0.332, 0.288, 0.313, 0.281, 0.291, 0.251, 0.29, 0.254, 0.286, 0.254, 0.288, 0.258, 0.273, 0.25, 0.282, 0.244, 0.505, 0.336, 0.312, 0.34, 0.283, 0.299, 0.275, 0.291, 0.255, 0.286, 0.253, 0.282, 0.238, 0.266, 0.242, 0.281, 0.242, 0.453, 0.319, 0.283, 0.295, 0.268, 0.288, 0.255, 0.279, 0.254, 0.272, 0.244, 0.275, 0.223, 0.272, 0.23, 0.396, 0.3, 0.266, 0.299, 0.262, 0.283, 0.238, 0.27, 0.23, 0.262, 0.217, 0.265, 0.214, 0.345, 0.301, 0.255, 0.297, 0.243, 0.281, 0.25, 0.269, 0.211, 0.251, 0.2, 0.344, 0.296, 0.257, 0.275, 0.234, 0.272, 0.233, 0.25, 0.212, 0.332, 0.307, 0.275, 0.285, 0.235, 0.271, 0.226, 0.339, 0.274, 0.243, 0.269, 0.229, 0.332, 0.262, 0.229, 0.317], [0.848, 0.591, 0.566, 0.527, 0.512, 0.475, 0.433, 0.423, 0.376, 0.379, 0.349, 0.368, 0.337, 0.362, 0.33, 0.367, 0.324, 0.352, 0.339, 0.353, 0.319, 0.355, 0.33, 0.36, 0.324, 0.725, 0.415, 0.365, 0.376, 0.348, 0.37, 0.32, 0.353, 0.317, 0.334, 0.302, 0.357, 0.315, 0.32, 0.29, 0.335, 0.297, 0.326, 0.3, 0.331, 0.293, 0.319, 0.285, 0.665, 0.371, 0.322, 0.365, 0.319, 0.358, 0.308, 0.333, 0.298, 0.318, 0.281, 0.325, 0.284, 0.327, 0.283, 0.314, 0.287, 0.306, 0.278, 0.316, 0.269, 0.589, 0.372, 0.341, 0.358, 0.331, 0.339, 0.299, 0.351, 0.288, 0.3, 0.275, 0.308, 0.277, 0.321, 0.266, 0.319, 0.271, 0.296, 0.268, 0.556, 0.361, 0.333, 0.347, 0.314, 0.335, 0.298, 0.308, 0.278, 0.308, 0.274, 0.304, 0.268, 0.294, 0.257, 0.308, 0.252, 0.496, 0.363, 0.319, 0.338, 0.302, 0.333, 0.291, 0.32, 0.274, 0.293, 0.26, 0.301, 0.261, 0.302, 0.249, 0.476, 0.377, 0.302, 0.34, 0.304, 0.332, 0.291, 0.318, 0.277, 0.296, 0.259, 0.291, 0.254, 0.441, 0.328, 0.304, 0.328, 0.295, 0.31, 0.278, 0.285, 0.264, 0.281, 0.246, 0.412, 0.337, 0.295, 0.333, 0.284, 0.317, 0.269, 0.289, 0.257, 0.392, 0.318, 0.305, 0.306, 0.272, 0.306, 0.269, 0.385, 0.308, 0.269, 0.292, 0.265, 0.402, 0.3, 0.266, 0.384], [0.859, 0.62, 0.621, 0.557, 0.561, 0.548, 0.529, 0.489, 0.46, 0.455, 0.416, 0.411, 0.402, 0.397, 0.364, 0.404, 0.358, 0.407, 0.364, 0.404, 0.376, 0.397, 0.382, 0.385, 0.362, 0.753, 0.464, 0.413, 0.41, 0.39, 0.403, 0.368, 0.366, 0.323, 0.356, 0.309, 0.35, 0.319, 0.356, 0.308, 0.341, 0.31, 0.351, 0.307, 0.355, 0.318, 0.337, 0.317, 0.685, 0.375, 0.363, 0.376, 0.347, 0.364, 0.323, 0.334, 0.307, 0.333, 0.309, 0.324, 0.299, 0.349, 0.315, 0.34, 0.303, 0.334, 0.296, 0.325, 0.299, 0.635, 0.378, 0.358, 0.348, 0.328, 0.355, 0.318, 0.337, 0.302, 0.324, 0.29, 0.329, 0.296, 0.32, 0.281, 0.328, 0.286, 0.322, 0.278, 0.597, 0.351, 0.33, 0.358, 0.321, 0.341, 0.313, 0.346, 0.302, 0.322, 0.288, 0.33, 0.297, 0.321, 0.286, 0.31, 0.27, 0.528, 0.351, 0.318, 0.355, 0.311, 0.352, 0.314, 0.328, 0.286, 0.31, 0.264, 0.319, 0.281, 0.314, 0.286, 0.497, 0.365, 0.318, 0.336, 0.287, 0.344, 0.287, 0.319, 0.275, 0.307, 0.276, 0.305, 0.266, 0.468, 0.35, 0.315, 0.334, 0.303, 0.33, 0.278, 0.319, 0.283, 0.305, 0.273, 0.447, 0.35, 0.318, 0.35, 0.307, 0.324, 0.285, 0.31, 0.271, 0.444, 0.345, 0.315, 0.323, 0.312, 0.327, 0.286, 0.448, 0.333, 0.297, 0.322, 0.281, 0.442, 0.328, 0.274, 0.424], [0.858, 0.65, 0.633, 0.608, 0.587, 0.582, 0.572, 0.559, 0.535, 0.518, 0.491, 0.48, 0.457, 0.467, 0.438, 0.453, 0.413, 0.448, 0.411, 0.433, 0.405, 0.433, 0.4, 0.423, 0.401, 0.749, 0.483, 0.467, 0.47, 0.434, 0.444, 0.407, 0.409, 0.367, 0.384, 0.343, 0.367, 0.336, 0.363, 0.335, 0.364, 0.34, 0.365, 0.32, 0.369, 0.322, 0.37, 0.324, 0.691, 0.417, 0.377, 0.394, 0.366, 0.377, 0.352, 0.367, 0.334, 0.349, 0.31, 0.363, 0.311, 0.346, 0.318, 0.338, 0.318, 0.347, 0.3, 0.338, 0.297, 0.653, 0.408, 0.384, 0.39, 0.349, 0.365, 0.322, 0.351, 0.304, 0.336, 0.304, 0.351, 0.302, 0.342, 0.312, 0.338, 0.312, 0.337, 0.303, 0.608, 0.389, 0.357, 0.382, 0.343, 0.348, 0.327, 0.344, 0.305, 0.34, 0.298, 0.337, 0.306, 0.343, 0.308, 0.332, 0.297, 0.576, 0.377, 0.345, 0.366, 0.332, 0.339, 0.315, 0.341, 0.304, 0.316, 0.286, 0.335, 0.276, 0.33, 0.3, 0.544, 0.381, 0.337, 0.359, 0.324, 0.335, 0.311, 0.342, 0.292, 0.322, 0.285, 0.328, 0.285, 0.51, 0.366, 0.336, 0.344, 0.315, 0.346, 0.31, 0.339, 0.297, 0.318, 0.276, 0.494, 0.368, 0.322, 0.366, 0.32, 0.34, 0.303, 0.327, 0.277, 0.48, 0.363, 0.32, 0.34, 0.308, 0.334, 0.296, 0.463, 0.341, 0.309, 0.344, 0.294, 0.449, 0.345, 0.293, 0.441], [0.849, 0.669, 0.665, 0.634, 0.616, 0.603, 0.582, 0.588, 0.562, 0.542, 0.524, 0.528, 0.501, 0.5, 0.466, 0.475, 0.452, 0.472, 0.446, 0.475, 0.435, 0.463, 0.439, 0.471, 0.434, 0.763, 0.523, 0.486, 0.5, 0.48, 0.463, 0.443, 0.429, 0.409, 0.41, 0.378, 0.398, 0.363, 0.41, 0.368, 0.395, 0.359, 0.389, 0.339, 0.386, 0.353, 0.395, 0.343, 0.723, 0.452, 0.421, 0.43, 0.398, 0.389, 0.372, 0.38, 0.346, 0.362, 0.329, 0.379, 0.33, 0.366, 0.323, 0.37, 0.315, 0.352, 0.322, 0.345, 0.329, 0.672, 0.42, 0.389, 0.395, 0.363, 0.4, 0.343, 0.384, 0.34, 0.359, 0.335, 0.372, 0.317, 0.363, 0.32, 0.342, 0.319, 0.339, 0.315, 0.642, 0.398, 0.366, 0.391, 0.344, 0.381, 0.328, 0.367, 0.335, 0.34, 0.322, 0.354, 0.3, 0.341, 0.314, 0.343, 0.306, 0.587, 0.388, 0.362, 0.381, 0.355, 0.36, 0.33, 0.355, 0.321, 0.349, 0.299, 0.327, 0.303, 0.341, 0.302, 0.56, 0.387, 0.365, 0.367, 0.35, 0.347, 0.344, 0.346, 0.31, 0.332, 0.292, 0.332, 0.285, 0.548, 0.376, 0.334, 0.372, 0.319, 0.345, 0.318, 0.332, 0.299, 0.34, 0.293, 0.536, 0.378, 0.341, 0.366, 0.325, 0.344, 0.302, 0.332, 0.289, 0.498, 0.377, 0.333, 0.363, 0.321, 0.353, 0.296, 0.477, 0.347, 0.307, 0.347, 0.31, 0.477, 0.326, 0.287, 0.463], [0.866, 0.672, 0.647, 0.636, 0.618, 0.634, 0.616, 0.598, 0.581, 0.561, 0.554, 0.548, 0.528, 0.534, 0.517, 0.528, 0.491, 0.518, 0.49, 0.505, 0.473, 0.503, 0.481, 0.505, 0.463, 0.792, 0.539, 0.547, 0.544, 0.522, 0.521, 0.498, 0.483, 0.462, 0.468, 0.447, 0.457, 0.415, 0.443, 0.4, 0.431, 0.391, 0.432, 0.39, 0.41, 0.379, 0.4, 0.38, 0.725, 0.483, 0.46, 0.465, 0.419, 0.438, 0.409, 0.414, 0.374, 0.391, 0.369, 0.395, 0.374, 0.38, 0.341, 0.384, 0.336, 0.36, 0.33, 0.368, 0.337, 0.673, 0.44, 0.418, 0.421, 0.383, 0.399, 0.356, 0.385, 0.359, 0.352, 0.337, 0.376, 0.336, 0.364, 0.346, 0.363, 0.32, 0.368, 0.324, 0.661, 0.412, 0.38, 0.391, 0.373, 0.382, 0.353, 0.365, 0.329, 0.36, 0.321, 0.354, 0.329, 0.351, 0.311, 0.33, 0.314, 0.62, 0.416, 0.376, 0.391, 0.35, 0.379, 0.329, 0.364, 0.342, 0.36, 0.316, 0.349, 0.314, 0.344, 0.307, 0.602, 0.39, 0.374, 0.389, 0.352, 0.376, 0.339, 0.357, 0.315, 0.339, 0.316, 0.332, 0.304, 0.569, 0.401, 0.35, 0.386, 0.334, 0.363, 0.322, 0.345, 0.295, 0.325, 0.306, 0.55, 0.383, 0.357, 0.371, 0.329, 0.354, 0.32, 0.337, 0.315, 0.527, 0.383, 0.343, 0.373, 0.338, 0.35, 0.313, 0.51, 0.353, 0.314, 0.335, 0.303, 0.473, 0.338, 0.289, 0.466], [0.856, 0.67, 0.655, 0.661, 0.62, 0.635, 0.617, 0.629, 0.606, 0.593, 0.547, 0.575, 0.566, 0.56, 0.536, 0.556, 0.525, 0.55, 0.521, 0.547, 0.521, 0.54, 0.499, 0.517, 0.496, 0.802, 0.592, 0.587, 0.584, 0.559, 0.561, 0.54, 0.535, 0.513, 0.513, 0.488, 0.52, 0.487, 0.481, 0.465, 0.498, 0.463, 0.476, 0.447, 0.456, 0.431, 0.464, 0.421, 0.751, 0.535, 0.519, 0.528, 0.489, 0.481, 0.482, 0.445, 0.444, 0.443, 0.403, 0.44, 0.394, 0.431, 0.392, 0.423, 0.377, 0.413, 0.378, 0.409, 0.373, 0.714, 0.497, 0.439, 0.456, 0.42, 0.445, 0.41, 0.415, 0.381, 0.393, 0.354, 0.408, 0.364, 0.402, 0.355, 0.387, 0.351, 0.368, 0.324, 0.687, 0.434, 0.41, 0.413, 0.394, 0.399, 0.371, 0.4, 0.362, 0.374, 0.339, 0.357, 0.326, 0.359, 0.324, 0.361, 0.327, 0.653, 0.426, 0.369, 0.414, 0.37, 0.385, 0.358, 0.379, 0.338, 0.361, 0.324, 0.34, 0.318, 0.35, 0.323, 0.614, 0.398, 0.375, 0.395, 0.365, 0.395, 0.331, 0.349, 0.31, 0.349, 0.308, 0.332, 0.308, 0.587, 0.412, 0.372, 0.395, 0.357, 0.388, 0.329, 0.354, 0.338, 0.345, 0.301, 0.565, 0.386, 0.36, 0.381, 0.353, 0.365, 0.334, 0.345, 0.316, 0.539, 0.386, 0.363, 0.361, 0.333, 0.343, 0.322, 0.519, 0.379, 0.318, 0.341, 0.319, 0.49, 0.346, 0.298, 0.481], [0.84, 0.677, 0.658, 0.668, 0.644, 0.646, 0.633, 0.639, 0.602, 0.617, 0.596, 0.612, 0.57, 0.58, 0.554, 0.587, 0.548, 0.583, 0.565, 0.566, 0.548, 0.547, 0.535, 0.534, 0.525, 0.813, 0.626, 0.61, 0.613, 0.585, 0.59, 0.583, 0.57, 0.542, 0.556, 0.524, 0.541, 0.527, 0.54, 0.509, 0.523, 0.497, 0.511, 0.482, 0.508, 0.476, 0.495, 0.467, 0.782, 0.586, 0.558, 0.561, 0.532, 0.531, 0.515, 0.522, 0.487, 0.5, 0.47, 0.504, 0.464, 0.491, 0.448, 0.468, 0.427, 0.461, 0.437, 0.47, 0.41, 0.759, 0.542, 0.52, 0.519, 0.488, 0.498, 0.462, 0.469, 0.441, 0.436, 0.411, 0.45, 0.423, 0.435, 0.418, 0.428, 0.409, 0.416, 0.393, 0.719, 0.498, 0.46, 0.485, 0.425, 0.445, 0.417, 0.438, 0.391, 0.413, 0.376, 0.407, 0.373, 0.402, 0.365, 0.397, 0.356, 0.69, 0.449, 0.405, 0.444, 0.4, 0.424, 0.383, 0.392, 0.356, 0.378, 0.35, 0.383, 0.343, 0.369, 0.343, 0.649, 0.421, 0.4, 0.4, 0.377, 0.382, 0.361, 0.377, 0.342, 0.362, 0.325, 0.367, 0.332, 0.615, 0.417, 0.384, 0.399, 0.358, 0.359, 0.338, 0.366, 0.323, 0.355, 0.303, 0.599, 0.394, 0.368, 0.394, 0.365, 0.365, 0.337, 0.354, 0.32, 0.559, 0.4, 0.36, 0.366, 0.339, 0.366, 0.317, 0.542, 0.369, 0.345, 0.362, 0.317, 0.517, 0.357, 0.304, 0.491], [0.857, 0.673, 0.657, 0.659, 0.646, 0.652, 0.628, 0.658, 0.63, 0.626, 0.618, 0.621, 0.611, 0.601, 0.593, 0.602, 0.576, 0.607, 0.583, 0.596, 0.565, 0.585, 0.564, 0.58, 0.55, 0.821, 0.624, 0.626, 0.636, 0.601, 0.634, 0.595, 0.589, 0.58, 0.575, 0.568, 0.584, 0.546, 0.569, 0.542, 0.567, 0.534, 0.553, 0.508, 0.545, 0.5, 0.517, 0.498, 0.802, 0.594, 0.587, 0.592, 0.581, 0.58, 0.55, 0.559, 0.53, 0.546, 0.52, 0.523, 0.526, 0.534, 0.496, 0.519, 0.5, 0.515, 0.465, 0.502, 0.456, 0.764, 0.579, 0.546, 0.547, 0.54, 0.537, 0.518, 0.524, 0.505, 0.507, 0.484, 0.499, 0.483, 0.482, 0.47, 0.491, 0.469, 0.482, 0.445, 0.756, 0.533, 0.498, 0.536, 0.498, 0.489, 0.479, 0.483, 0.469, 0.467, 0.44, 0.467, 0.438, 0.439, 0.422, 0.437, 0.415, 0.726, 0.521, 0.479, 0.49, 0.457, 0.465, 0.447, 0.435, 0.415, 0.443, 0.407, 0.422, 0.4, 0.416, 0.399, 0.695, 0.48, 0.446, 0.461, 0.433, 0.446, 0.412, 0.435, 0.388, 0.412, 0.382, 0.406, 0.367, 0.669, 0.445, 0.423, 0.436, 0.404, 0.431, 0.392, 0.406, 0.355, 0.373, 0.345, 0.649, 0.436, 0.398, 0.418, 0.378, 0.395, 0.355, 0.382, 0.341, 0.602, 0.42, 0.379, 0.393, 0.362, 0.38, 0.339, 0.56, 0.391, 0.361, 0.367, 0.327, 0.525, 0.359, 0.313, 0.492]]

_CIDX = {}
for _i, _c in enumerate(CLASSES):
    _CIDX[_c] = _i
_NW = len(W)


def _cls(h):
    a, b = h[0], h[1]
    ra, rb = a >> 2, b >> 2
    if ra < rb: ra, rb = rb, ra
    s = 1 if (a & 3) == (b & 3) and ra != rb else 0
    return _CIDX.get((ra, rb, s), 84)


def _eqvs(ci, w):
    """equity of class ci vs top-w range (w in 0..1)."""
    if w <= W[0]: return EQW[0][ci]
    if w >= 1.0: return EQW[-1][ci]
    j = 1
    while j < _NW and W[j] < w: j += 1
    w0, w1 = W[j - 1], W[j]
    t = (w - w0) / (w1 - w0)
    return EQW[j - 1][ci] * (1 - t) + EQW[j][ci] * t


_PTS = (10, 7, 5, 4, 3, 2, 1, 0)


def _icm1(st, i):
    """Exact Harville ICM for payouts 10/7/5/4/3/2/1/0: pts(place)=8-place+3[1st]+[2nd], and
    Plackett-Luce gives P(j ahead of i)=sj/(si+sj), so it is O(n)."""
    si = st[i]
    if si <= 0: return 0.0
    T = 0.0
    for x in st:
        if x > 0: T += x
    ep = 1.0; p2 = 0.0
    for j in range(len(st)):
        sj = st[j]
        if j == i or sj <= 0: continue
        ep += sj / (si + sj); p2 += (sj / T) * si / (T - sj)
    return 8.0 - ep + 3.0 * si / T + p2


def _card(c):
    if isinstance(c, int): return c
    if isinstance(c, str) and len(c) >= 2:
        return '23456789TJQKA'.index(c[0].upper()) * 4 + 'cdhs'.index(c[-1].lower())
    return int(c)


_POSTS = ('post', 'blind', 'sb', 'bb', 'ante', 'small_blind', 'big_blind', 'post_sb', 'post_bb')


class _St(object):
    __slots__ = ('hands', 'vpip', 'pfr', 'uo', 'uo_r', 'uo_f', 'uo_l', 'fr', 'fr_f', 'fr_c', 'fr_r',
                 'shv', 'rz', 'dead', 'fb', 'fb_f', 'fb_c', 'fb_r', 'nb', 'nb_b', 'bbf')

    def __init__(self):
        for k in self.__slots__:
            setattr(self, k, 0)


class Bot(_Base):
    def __init__(self):
        self.rng = __import__('random').Random(12345)
        self._reset(8)

    def _reset(self, n):
        try:
            n = int(n)
        except Exception:
            n = 8
        if n < 2 or n > 12: n = 8
        self.n = n
        self.st = [_St() for _ in range(12)]
        self.hand = None
        self.done = 0          # history entries already counted for current hand
        self.start = None      # stacks at start of current hand
        self.pf_aggr = None    # last preflop aggressor
        self.my_pf_raise = False

    # ---------------------------------------------------------------- kit hooks
    def new_table(self, rules, seat, n_players):
        try:
            self._reset(n_players if n_players else 8)
        except Exception:
            self._reset(8)

    def hand_end(self, result):
        try:
            if isinstance(result, dict):
                h = result.get('history') or result.get('actions')
                if isinstance(h, (list, tuple)) and len(h) <= 200 and self.hand is not None and self.start is not None:
                    self._replay(h, self._lastobs, final=True)
        except Exception:
            pass
        self.hand = None; self.done = 0; self.start = None

    # ---------------------------------------------------------------- entry
    def act(self, obs):
        try:
            a = self._act(obs)
        except Exception:
            a = None
        return self._legalize(a, obs)

    def _legalize(self, a, obs):
        try:
            legal = obs.legal
            legal = set(legal) if legal is not None else set()
        except Exception:
            legal = set()
        try:
            tc = int(obs.to_call or 0)
        except Exception:
            tc = 1
        if a is not None and isinstance(a, tuple) and len(a) == 2 and a[0] in legal:
            if a[0] != 'raise':
                return (a[0], 0)
            try:
                lo, hi = int(obs.min_raise), int(obs.max_raise)
                if lo > hi: lo, hi = hi, lo
                amt = int(a[1])
                if amt < lo: amt = lo
                if amt > hi: amt = hi
                return ('raise', amt)
            except Exception:
                a = ('call', 0) if 'call' in legal else None
                if a: return a
        if 'check' in legal: return ('check', 0)
        if a is not None and a[0] == 'call' and 'call' in legal: return ('call', 0)
        if 'fold' in legal: return ('fold', 0)
        if 'call' in legal: return ('call', 0)
        if legal: return (sorted(legal)[0], 0) if 'raise' not in legal else ('fold', 0)
        return ('check', 0) if tc <= 0 else ('fold', 0)

    # ---------------------------------------------------------------- model
    def _blind_seats(self, alive, button, n):
        # alive: list of seat indices in order; returns (sb, bb)
        if len(alive) < 2: return (None, None)
        if len(alive) == 2:
            b = button if button in alive else alive[0]
            o = alive[1] if alive[0] == b else alive[0]
            return (b, o)
        order = []
        for k in range(1, n + 1):
            s = (button + k) % n
            if s in alive: order.append(s)
        return (order[0], order[1])

    def _replay(self, hist, o, final=False):
        """Replay this hand's history from scratch; count stats for entries >= self.done."""
        start = self.start; n = len(start); bb = self.bb; sbv = self.sbv
        alive = [s for s in range(n) if start[s] > 0]
        sbs, bbs = self._blind_seats(alive, self.button, n)
        contrib = [0] * n; total = [0] * n
        insets = set(alive)
        if sbs is not None:
            contrib[sbs] = min(sbv, start[sbs]); contrib[bbs] = min(bb, start[bbs])
        level = bb; acted = set(); street = 0; raises = 0; posts_seen = 0
        st = self.st; done = self.done; aggr = None
        for idx in range(len(hist)):
            e = hist[idx]
            try:
                s = int(e[0]); act = e[1]
                if isinstance(act, (tuple, list)):
                    kind = act[0]; amt = int(act[1]) if len(act) > 1 and act[1] is not None else 0
                else:
                    kind = act; amt = 0
                if not (0 <= s < n): continue
            except Exception:
                continue
            count = idx >= done
            if not isinstance(kind, str): continue
            kind = kind.lower()
            if kind in _POSTS or (street == 0 and kind == 'raise' and amt <= bb and raises == 0 and s in (sbs, bbs) and posts_seen < 2 and s not in acted):
                posts_seen += 1
                if amt > 0: contrib[s] = amt
                if amt > level: level = amt
                continue
            S = st[s] if s < 12 else None
            if S is None: continue
            facing = level > contrib[s]
            if street == 0:
                if count:
                    first = s not in self.pf_seen
                    if first:
                        self.pf_seen.add(s); S.hands += 1
                        if kind in ('call', 'raise') and not (kind == 'call' and not facing):
                            S.vpip += 1
                        if kind == 'raise': S.pfr += 1
                    elif kind == 'raise' and s not in self.pf_raised:
                        S.pfr += 1
                    if kind == 'raise': self.pf_raised.add(s)
                    if raises == 0:
                        S.uo += 1
                        if kind == 'raise': S.uo_r += 1
                        elif kind == 'fold':
                            S.uo_f += 1
                            if s == bbs and not facing: S.bbf += 1; S.dead += 1
                        elif kind == 'call': S.uo_l += 1
                    else:
                        S.fr += 1
                        if kind == 'fold': S.fr_f += 1
                        elif kind == 'call': S.fr_c += 1
                        elif kind == 'raise': S.fr_r += 1
                    if kind == 'raise':
                        S.rz += 1
                        if amt >= 0.85 * start[s]: S.shv += 1
            else:
                if count:
                    if facing:
                        S.fb += 1
                        if kind == 'fold': S.fb_f += 1
                        elif kind == 'call': S.fb_c += 1
                        elif kind == 'raise': S.fb_r += 1
                    else:
                        S.nb += 1
                        if kind == 'raise': S.nb_b += 1
                        elif kind == 'fold': S.dead += 1
            # apply
            if kind == 'fold':
                insets.discard(s)
            elif kind == 'check':
                acted.add(s)
            elif kind == 'call':
                cap = start[s] - total[s]
                contrib[s] = min(level, cap if cap > 0 else level); acted.add(s)
            elif kind == 'raise':
                if amt > level:
                    level = amt; raises += 1; acted = set([s])
                    if street == 0: aggr = s
                else:
                    acted.add(s)
                contrib[s] = max(amt, contrib[s])
            else:
                continue
            # round over?
            live = [x for x in insets if start[x] - total[x] - contrib[x] > 0]
            if len(insets) <= 1:
                break
            if all((x in acted and contrib[x] >= level) for x in live):
                for x in range(n): total[x] += contrib[x]
                contrib = [0] * n; level = 0; acted = set(); street += 1
        if not final:
            self.done = max(self.done, len(hist))
            self.pf_aggr = aggr
            self.n_raises = raises if street == 0 else self.n_raises
        else:
            self.done = len(hist)

    def _rates(self, s):
        S = self.st[s]; h = S.hands
        vp = (S.vpip + 1.0) / (h + 4.0)
        pfr = (S.pfr + 0.6) / (h + 4.0)
        f2r = (S.fr_f + 2.4) / (S.fr + 4.0)
        r3 = (S.fr_r + 0.3) / (S.fr + 4.0)
        shv = (S.shv + 0.2) / (S.rz + 2.0)
        fb = (S.fb_f + 1.8) / (S.fb + 4.0)
        agg = (S.nb_b + 1.2) / (S.nb + 4.0)
        dead = (S.dead >= 1 and S.vpip == 0 and h >= 3) or (h >= 22 and S.vpip == 0)
        return vp, pfr, f2r, r3, shv, fb, agg, dead

    def _fold_prob(self, s, short):
        """P(seat s folds to our raise/shove now)."""
        vp, pfr, f2r, r3, shv, fb, agg, dead = self._rates(s)
        if dead: return 1.0
        f = f2r
        if short: f = min(f, 1.0 - min(0.9, vp * 0.6))  # vs a shove, callers ~ a part of vpip
        return max(0.05, min(0.97, f))

    def _allin(self, stacks, bets, inh, seat, opp, pot, n_alive):
        """ICM values (fold, steal, win, lose) for an all-in confrontation between me and opp."""
        n = len(stacks)
        tot = [stacks[j] + bets[j] for j in range(n)]
        mytot = tot[seat]
        pot_all = pot + sum(bets)
        dead_other = pot_all - bets[seat] - bets[opp]
        c = min(tot[opp], mytot)
        base = list(stacks)
        f = list(base); f[opp] += pot_all
        ev_fold = _icm1(f, seat)
        st = list(base); st[seat] = mytot + pot_all - bets[seat]
        ev_steal = _icm1(st, seat)
        w = list(base); w[seat] = mytot + c + dead_other; w[opp] = tot[opp] - c
        ev_win = _icm1(w, seat)
        l = list(base); l[seat] = mytot - c; l[opp] = tot[opp] + c + dead_other
        if l[seat] <= 0:
            ev_lose = float(_PTS[min(7, max(1, n_alive) - 1)])
        else:
            ev_lose = _icm1(l, seat)
        return ev_fold, ev_steal, ev_win, ev_lose

    # ---------------------------------------------------------------- decision
    def _act(self, o):
        legal = set(o.legal) if o.legal is not None else set()
        if not legal: return None
        hole = tuple(_card(c) for c in o.hole) if o.hole is not None else ()
        board = tuple(_card(c) for c in o.board) if o.board is not None else ()
        if len(hole) == 2 and hole[0] == hole[1]: return None
        for c in hole + board:
            if not (0 <= c < 52): return None
        if len(hole) != 2: return None
        stacks = list(o.stacks) if o.stacks is not None else []
        n = len(stacks)
        if n < 2: return None
        seat = o.seat if isinstance(o.seat, int) and 0 <= o.seat < n else 0
        bets = list(o.bets) if o.bets is not None and len(o.bets) == n else [0] * n
        inh = list(o.in_hand) if o.in_hand is not None and len(o.in_hand) == n else [stacks[i] > 0 or i == seat for i in range(n)]
        try:
            sbv, bb = int(o.blinds[0]), int(o.blinds[1])
            if bb <= 0: raise ValueError
        except Exception:
            sbv, bb = 10, 20
        pot = int(o.pot or 0)
        to_call = int(o.to_call or 0)
        street = o.street if o.street in (0, 1, 2, 3) else {0: 0, 3: 1, 4: 2, 5: 3}.get(len(board), 0)
        button = o.button if isinstance(o.button, int) and 0 <= o.button < n else 0
        hn = o.hand_no
        self._lastobs = o
        self.bb = bb; self.sbv = sbv; self.button = button
        # --- model update
        if hn is not None and isinstance(o.history, (list, tuple)) and len(o.history) <= 90:
            if hn != self.hand or self.start is None or len(self.start) != n:
                self.hand = hn; self.done = 0; self.pf_seen = set(); self.pf_raised = set(); self.n_raises = 0
                if street == 0:
                    self.start = [stacks[i] + bets[i] for i in range(n)]
                else:
                    self.start = [stacks[i] + bets[i] + (pot // max(1, sum(1 for x in inh if x)) if inh[i] else 0) for i in range(n)]
                self.my_pf_raise = False
            try:
                self._replay(o.history, o)
            except Exception:
                pass
        elif hn != self.hand:
            self.hand = hn; self.start = None; self.my_pf_raise = False; self.pf_aggr = None; self.n_raises = 0
        if street == 0:
            a = self._pre(o, legal, hole, stacks, bets, inh, n, seat, sbv, bb, pot, to_call, button)
            if a and a[0] == 'raise': self.my_pf_raise = True
            return a
        return self._post(o, legal, hole, board, stacks, bets, inh, n, seat, bb, pot, to_call, street)

    def _raise(self, legal, o, amt):
        if 'raise' not in legal: return None
        lo, hi = int(o.min_raise), int(o.max_raise)
        if lo > hi: lo, hi = hi, lo
        amt = int(amt)
        if amt < lo: amt = lo
        if amt >= hi * 0.8: amt = hi
        if amt > hi: amt = hi
        return ('raise', amt)

    def _call_or_check(self, legal):
        if 'check' in legal: return ('check', 0)
        if 'call' in legal: return ('call', 0)
        return ('fold', 0)

    def _fold(self, legal):
        return ('check', 0) if 'check' in legal else ('fold', 0)

    def _icm_margin(self, stacks, seat, n_alive, risk_all):
        if n_alive <= 2: return 0.0
        m = 0.0
        if n_alive <= 5: m += 0.02
        if risk_all:
            mine = stacks[seat]
            shorter = sum(1 for i in range(len(stacks)) if i != seat and 0 < stacks[i] < mine)
            if shorter >= 2: m += 0.03
            elif shorter >= 1: m += 0.015
        return m

    def _pre(self, o, legal, hole, stacks, bets, inh, n, seat, sbv, bb, pot, to_call, button):
        ci = _cls(hole); p = PCT[ci]
        tot = [stacks[i] + bets[i] for i in range(n)]
        mytot = tot[seat]
        alive = [i for i in range(n) if tot[i] > 0 or inh[i]]
        n_alive = len(alive)
        opp_in = [i for i in range(n) if inh[i] and i != seat]
        if not opp_in: return self._call_or_check(legal)
        eff = min(mytot, max(tot[i] for i in opp_in))
        eff_bb = eff / float(bb)
        level = max(bets) if bets else 0
        pot_tot = pot + sum(min(b, mytot) for b in bets)  # chips I can actually win
        # players still to act behind me (in hand, not yet having put in level)
        order = []
        for k in range(1, n):
            s = (seat + k) % n
            order.append(s)
        # seats that act after me this round: those in hand who haven't matched/acted -> approximate by position
        sbs, bbs = self._blind_seats(alive, button, n)
        behind = []
        # positions: after me until the BB (inclusive)
        if bbs is not None and seat != bbs:
            for s in order:
                if inh[s] and stacks[s] > 0: behind.append(s)
                if s == bbs: break
        raisers = []
        for s in range(n):
            if s != seat and inh[s] and bets[s] > bb: raisers.append(s)
        n_raises = max(getattr(self, 'n_raises', 0), 1 if raisers else 0)
        if level <= bb:
            n_raises = 0
        short = eff_bb <= 10
        # ---------------- unopened (maybe limpers)
        if n_raises == 0:
            limpers = [s for s in opp_in if bets[s] >= bb and s != bbs]
            # fold equity of everybody behind
            pf = 1.0
            for s in behind: pf *= self._fold_prob(s, short)
            for s in limpers: pf *= self._fold_prob(s, short) * 0.9
            n_beh = len(behind) + len(limpers)
            if short:
                cands = behind + limpers
                if not cands:
                    return self._raise(legal, o, o.max_raise) if p <= 0.5 else self._call_or_check(legal)
                # likely caller: the loosest seat behind; its calling range = 1 - fold prob
                fps = [(self._fold_prob(s, True), s) for s in cands]
                fmin, caller = min(fps)
                big = max(cands, key=lambda s: tot[s])
                opp = caller if tot[caller] >= mytot else big
                wc = min(1.0, max(0.03, 1.0 - fmin))
                eqc = _eqvs(ci, wc)
                ncall = sum(1 for f_, s_ in fps if f_ < 0.5)
                if ncall >= 2: eqc = eqc ** (1.0 + 0.5 * (ncall - 1))
                evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, opp, pot, n_alive)
                ev_sh = pf * evs + (1 - pf) * (eqc * evw + (1 - eqc) * evl)
                if ev_sh > evf + 0.002:
                    return self._raise(legal, o, o.max_raise)
                return self._fold(legal) if to_call > 0 else self._call_or_check(legal)
            # deeper: raise-first-in / isolate
            base = {0: 1.0, 1: 0.48, 2: 0.36, 3: 0.27, 4: 0.21, 5: 0.17, 6: 0.14, 7: 0.12}.get(len(behind), 0.11)
            if limpers:
                base = 0.14 + 0.03 * sum(1 for s in limpers if self._rates(s)[0] > 0.5)
            if n_alive <= 4: base *= 1.2
            # re-shovers / 3bettors behind tighten
            r3max = max([self._rates(s)[3] for s in behind] or [0])
            if r3max > 0.2: base *= 0.75
            size = bb * (2.5 if len(behind) > 1 else 2.2) + bb * len(limpers)
            if limpers and any(self._rates(s)[0] > 0.55 for s in limpers): size += bb * len(limpers)
            ev_steal = pf * pot_tot - (1 - pf) * (size - bets[seat]) * 0.55
            if p <= base or (n_beh and ev_steal > 0 and p <= 0.85) or (n_beh and pf > 0.9):
                return self._raise(legal, o, size)
            if 'check' in legal: return ('check', 0)
            if seat == sbs and to_call <= sbv and p <= 0.45 and len(limpers) == 0:
                return ('call', 0)
            if limpers and to_call <= bb and p <= 0.30 and eff_bb > 30:
                return ('call', 0)
            return ('fold', 0)
        # ---------------- facing raise(s)
        agg = max(raisers, key=lambda s: bets[s]) if raisers else (self.pf_aggr if self.pf_aggr is not None else None)
        if agg is None or not (0 <= agg < n): agg = opp_in[0]
        vp, pfr, f2r, r3, shv, fb, aggf, dead = self._rates(agg)
        agg_allin = stacks[agg] == 0 and inh[agg]
        if n_raises <= 1:
            w = min(1.0, max(0.04, pfr * 1.25))
            if bets[agg] >= 0.85 * tot[agg] or agg_allin:
                w = min(1.0, max(0.05, pfr * 1.1))
        else:
            w = min(0.6, max(0.03, r3 * 0.9 + 0.02))
        eq = _eqvs(ci, w)
        # multiway: every other opponent who put money in beyond the blind must also be beaten
        k = sum(1 for s in opp_in if bets[s] > bb)
        if k >= 2:
            eq = eq ** (1.0 + 0.75 * (k - 1))
        nb = len([s for s in behind if s not in raisers])
        if nb: eq *= (1.0 - 0.015 * nb)
        callamt = min(to_call, stacks[seat])
        req = callamt / float(pot_tot + callamt) if pot_tot + callamt > 0 else 1.0
        commit = callamt >= 0.4 * stacks[seat] or eff_bb <= 18 or agg_allin or n_raises >= 2
        margin = self._icm_margin(stacks, seat, n_alive, commit)
        if commit:
            evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, agg, pot, n_alive)
            ev_call = eq * evw + (1 - eq) * evl
            can_shove = 'raise' in legal and not agg_allin
            if can_shove:
                # fold equity of the aggressor (and anyone behind) vs our shove
                fo = self._fold_prob(agg, True) * (0.5 if n_raises >= 2 else 0.8)
                for s in behind:
                    if s != agg: fo *= self._fold_prob(s, True)
                wc = min(1.0, max(0.03, w * 0.6))
                eqc = _eqvs(ci, wc)
                if k >= 2: eqc = eqc ** (1.0 + 0.75 * (k - 1))
                ev_sh = fo * evs + (1 - fo) * (eqc * evw + (1 - eqc) * evl)
                if ev_sh > evf + 0.002 and ev_sh >= ev_call:
                    return self._raise(legal, o, o.max_raise)
            if ev_call > evf + 0.002:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            return self._fold(legal)
        # deep: 3bet value / call / fold
        if n_raises == 1:
            v3 = min(0.06, w * 0.3) if pfr < 0.35 else min(0.18, w * 0.35)
            if p <= max(0.025, v3):
                size = bets[agg] * 3 + bb
                if size > 0.4 * mytot: size = o.max_raise
                return self._raise(legal, o, size)
            implied = 0.06 if eff_bb > 40 and callamt < 0.1 * stacks[seat] else 0.0
            if ci is not None and CLASSES[ci][0] == CLASSES[ci][1] and callamt <= 0.07 * stacks[seat]:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            if eq + implied >= req + 0.08 and p <= max(0.22, w * 0.7):
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            if seat == bbs and callamt <= 2 * bb and eq >= req and p <= 0.5:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            return self._fold(legal)
        # 3bet+ deep
        if p <= 0.025 or eq >= 0.6:
            return self._raise(legal, o, o.max_raise) if 'raise' in legal else self._call_or_check(legal)
        if p <= 0.05 and eq >= req + 0.05:
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        return self._fold(legal)

    # ---------------------------------------------------------------- postflop
    def _strength(self, hole, board, street):
        cards = list(hole) + list(board)
        v = ev7(cards); cat = v >> 20
        bv = ev7(list(board)); bcat = bv >> 20
        hr = sorted([hole[0] >> 2, hole[1] >> 2], reverse=True)
        br = sorted([c >> 2 for c in board], reverse=True)
        top = br[0] if br else 0
        e = 0.12
        if cat >= 4 and v > bv and cat > bcat:
            e = 0.93 if cat >= 6 else 0.88
            # one-card flush on 4-flush board / board straight etc
            if cat == 5:
                sc = {}
                for c in board: sc[c & 3] = sc.get(c & 3, 0) + 1
                if max(sc.values()) >= 4:
                    fs = max(sc, key=sc.get)
                    mine = [h >> 2 for h in hole if h & 3 == fs]
                    e = 0.85 if mine and max(mine) >= 10 else 0.62
        elif cat == 3:
            if hr[0] == hr[1]: e = 0.9  # set
            elif bcat < 3: e = 0.8 if max(hr) >= 9 else 0.74  # trips with one card
            else: e = 0.3 if hr[0] >= 11 else 0.15
        elif cat == 2:
            if bcat == 1:
                # board pair + my pair
                if hr[0] == hr[1]:
                    e = 0.72 if hr[0] > top else 0.45
                elif hr[0] in br or hr[1] in br:
                    pr = hr[0] if hr[0] in br else hr[1]
                    e = 0.68 if pr == top else 0.5
                else: e = 0.2
            elif bcat == 2:
                e = 0.25 if hr[0] < 12 else 0.35
            else:
                e = 0.82  # two pair using both cards
        elif cat == 1:
            if bcat == 1:
                e = 0.2 if hr[0] >= 11 else 0.1
            elif hr[0] == hr[1]:
                if hr[0] > top: e = 0.72 if hr[0] >= 9 else 0.62
                elif len(br) > 1 and hr[0] > br[1]: e = 0.45
                else: e = 0.3
            else:
                pr = hr[0] if hr[0] in br else hr[1]
                kick = hr[1] if pr == hr[0] else hr[0]
                if pr == top:
                    e = 0.66 if kick >= 9 else 0.57
                    if pr >= 11: e += 0.03
                elif len(br) > 1 and pr == br[1]: e = 0.43
                else: e = 0.32
        else:
            e = 0.12 + (0.06 if hr[0] > top else 0) + (0.04 if hr[1] > top else 0)
        # draws
        draw = 0.0
        if street < 3:
            sc = [0, 0, 0, 0]
            for c in cards: sc[c & 3] += 1
            for su in range(4):
                if sc[su] == 4 and ((hole[0] & 3) == su or (hole[1] & 3) == su):
                    draw = max(draw, 0.34 if street == 1 else 0.19)
            m = 0; bm = 0
            for c in cards: m |= 1 << (c >> 2)
            for c in board: bm |= 1 << (c >> 2)
            cur = _STR[m]
            if not cur:
                outs = 0
                for r in range(13):
                    if not (m >> r) & 1:
                        s2 = _STR[m | (1 << r)]
                        if s2 and s2 > _STR[bm | (1 << r)]: outs += 1
                if outs >= 2: draw = max(draw, 0.31 if street == 1 else 0.17)
                elif outs == 1: draw = max(draw, 0.16 if street == 1 else 0.09)
        if draw and e < 0.6:
            e = max(e, draw) + min(draw, e) * 0.3
        return e, draw

    def _post(self, o, legal, hole, board, stacks, bets, inh, n, seat, bb, pot, to_call, street):
        if len(board) < 3: return self._call_or_check(legal) if to_call == 0 else self._fold(legal)
        e, draw = self._strength(hole, board, street)
        opps = [i for i in range(n) if inh[i] and i != seat]
        if not opps: return self._call_or_check(legal)
        nop = len(opps)
        if nop > 1: e = e ** (1.0 + 0.45 * (nop - 1)) if e < 0.85 else e - 0.03 * (nop - 1)
        rates = [self._rates(s) for s in opps]
        stations = sum(1 for r in rates if r[0] > 0.5 and r[5] < 0.35)
        avg_fold = 1.0
        for r in rates: avg_fold *= (1.0 if r[7] else r[5])
        pot_tot = pot + sum(bets)
        mystack = stacks[seat]
        spr = mystack / float(max(1, pot_tot))
        if to_call <= 0:
            # value
            thr = 0.6 if stations == 0 else 0.52
            if e >= thr:
                frac = 0.65 if stations == 0 else 0.85
                if e >= 0.85: frac = 0.8 if stations == 0 else 1.0
                amt = bets[seat] + max(bb, int(pot_tot * frac))
                if spr < 1.3 and e >= 0.6: amt = o.max_raise
                return self._raise(legal, o, amt) or self._call_or_check(legal)
            # bluffs / semi-bluffs, never into stations
            if stations == 0 and nop <= 2:
                bluffp = 0.0
                if self.my_pf_raise and street == 1: bluffp = 0.55 if avg_fold > 0.45 else 0.3
                elif street >= 2 and avg_fold > 0.6 and nop == 1: bluffp = 0.4
                if draw: bluffp = max(bluffp, 0.5)
                if avg_fold > 0.85: bluffp = 0.9
                if self.rng.random() < bluffp:
                    amt = bets[seat] + max(bb, int(pot_tot * 0.5))
                    return self._raise(legal, o, amt) or self._call_or_check(legal)
            return self._call_or_check(legal)
        # facing a bet
        aggr = max(opps, key=lambda s: bets[s])
        vp, pfr, f2r, r3, shv, fb, ag, dead = self._rates(aggr)
        adj = 0.0
        raised_me = bets[seat] > 0
        if ag > 0.5 or pfr > 0.4: adj += (0.08 if not raised_me else 0.02)   # maniac: range is wide
        elif ag < 0.25 and vp < 0.3: adj -= 0.08    # nit bets: believe it
        if vp > 0.5 and ag < 0.3: adj -= 0.03       # station betting = real hand
        if raised_me and e < 0.85: adj -= 0.12      # a raise over my bet is stronger than a bet
        e2 = min(0.97, e + adj)
        callamt = min(to_call, mystack)
        req = callamt / float(pot_tot + callamt)
        if callamt > 0.35 * mystack and e2 < 0.6 and street < 3 and not draw:
            req = max(req, 0.5)
        if callamt >= 0.45 * mystack:
            try:
                n_alive = sum(1 for i in range(n) if stacks[i] + bets[i] > 0 or inh[i])
                evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, aggr, pot, n_alive)
                if evw > evl: req = max(req, (evf - evl) / (evw - evl))
            except Exception:
                pass
        if e2 >= 0.8 or (e2 >= 0.7 and spr < 2):
            amt = bets[aggr] * 3 if spr > 2 else o.max_raise
            if stations or ag > 0.5: amt = max(amt, bets[seat] + int(pot_tot + callamt))
            r = self._raise(legal, o, amt)
            if r and self.rng.random() < 0.8: return r
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        implied = 0.05 if draw and spr > 3 and street < 3 else 0.0
        if e2 + implied >= req + 0.12:
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        return self._fold(legal)
