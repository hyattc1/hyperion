# Origin: the climb's outside field (docs/drills/field/outside_veterans.md is the builder's log). A fresh coding agent,
# playing two former university pokerbots finalists who prepared for two weeks (ICM push/fold first, punish weak seats),
# built it in one hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# bffa539c16eabb4836c4518c5ba1a660 (its FROZEN.md5) and copied here unchanged apart from this header. The archive is docs/drills/field/outside_veterans_bot.py.
# Played through hyperion.sim.bestiary.Outside*Bot (registry name `out_veterans`); a judge-like field, never tuned on.
# Do not edit; a new bot is a new file.
"""Rival bot: ICM-aware push/fold + tight value postflop + seat exploitation. Stdlib only."""
try:
    from kit import Agent
except Exception:
    class Agent(object):
        def new_table(self, rules, seat, n_players): pass
        def act(self, obs): raise NotImplementedError
        def hand_end(self, result): pass
"""Hand evaluator (written for this bot). card = rank*4+suit. Higher score = better."""
STRAIGHT = [0] * 8192
POP = [0] * 8192
TOP5 = [0] * 8192
for _m in range(8192):
    POP[_m] = bin(_m).count('1')
    _b = 0
    for _hi in range(12, 3, -1):
        _need = 31 << (_hi - 4)
        if _m & _need == _need:
            _b = _hi + 1
            break
    if not _b and (_m & 4111) == 4111:
        _b = 4
    STRAIGHT[_m] = _b
    _v = 0; _k = 0
    for _r in range(12, -1, -1):
        if _m >> _r & 1:
            _v = (_v << 4) | _r; _k += 1
            if _k == 5:
                break
    while _k < 5:
        _v <<= 4; _k += 1
    TOP5[_m] = _v
RANGE13 = tuple(range(12, -1, -1))


def ev(cards):
    sb = [0, 0, 0, 0]
    cnt = [0] * 13
    for c in cards:
        r = c >> 2
        cnt[r] += 1
        sb[c & 3] |= 1 << r
    for m in sb:
        if POP[m] >= 5:
            s = STRAIGHT[m]
            if s:
                return 0x800000 | s
            return 0x500000 | TOP5[m]
    rbits = sb[0] | sb[1] | sb[2] | sb[3]
    q = -1; t = []; p = []; sg = []
    for r in RANGE13:
        c = cnt[r]
        if c:
            if c == 1: sg.append(r)
            elif c == 2: p.append(r)
            elif c == 3: t.append(r)
            else: q = r
    if q >= 0:
        k = -1
        if t: k = t[0]
        if p and p[0] > k: k = p[0]
        if sg and sg[0] > k: k = sg[0]
        return 0x700000 | q << 4 | (k if k > 0 else 0)
    if t and (len(t) > 1 or p):
        pr = t[1] if len(t) > 1 else -1
        if p and p[0] > pr: pr = p[0]
        return 0x600000 | t[0] << 4 | pr
    s = STRAIGHT[rbits]
    if s:
        return 0x400000 | s
    sg += [0, 0, 0]
    if t:
        return 0x300000 | t[0] << 8 | sg[0] << 4 | sg[1]
    if len(p) >= 2:
        k = p[2] if len(p) > 2 else 0
        if sg[0] > k: k = sg[0]
        return 0x200000 | p[0] << 8 | p[1] << 4 | k
    if p:
        return 0x100000 | p[0] << 12 | sg[0] << 8 | sg[1] << 4 | sg[2]
    return TOP5[rbits]
EQ1=[0.501, 0.324, 0.334, 0.344, 0.338, 0.343, 0.366, 0.396, 0.418, 0.442, 0.476, 0.509, 0.553, 0.355, 0.541, 0.351, 0.368, 0.366, 0.367, 0.376, 0.405, 0.428, 0.454, 0.477, 0.513, 0.553, 0.37, 0.386, 0.577, 0.388, 0.376, 0.392, 0.394, 0.399, 0.432, 0.465, 0.49, 0.52, 0.566, 0.382, 0.395, 0.412, 0.609, 0.395, 0.403, 0.413, 0.422, 0.437, 0.467, 0.501, 0.532, 0.575, 0.381, 0.394, 0.413, 0.427, 0.633, 0.424, 0.429, 0.447, 0.461, 0.479, 0.512, 0.539, 0.581, 0.383, 0.395, 0.418, 0.438, 0.446, 0.664, 0.447, 0.472, 0.48, 0.498, 0.522, 0.549, 0.587, 0.4, 0.416, 0.429, 0.443, 0.465, 0.476, 0.692, 0.484, 0.498, 0.509, 0.543, 0.557, 0.594, 0.425, 0.43, 0.44, 0.461, 0.472, 0.497, 0.506, 0.719, 0.518, 0.534, 0.557, 0.581, 0.608, 0.448, 0.457, 0.463, 0.472, 0.485, 0.511, 0.527, 0.545, 0.752, 0.551, 0.574, 0.596, 0.626, 0.477, 0.481, 0.492, 0.504, 0.514, 0.521, 0.536, 0.555, 0.572, 0.774, 0.58, 0.608, 0.635, 0.508, 0.512, 0.522, 0.525, 0.538, 0.545, 0.559, 0.578, 0.589, 0.598, 0.8, 0.614, 0.641, 0.532, 0.541, 0.549, 0.557, 0.566, 0.577, 0.58, 0.603, 0.618, 0.623, 0.632, 0.821, 0.653, 0.578, 0.58, 0.589, 0.598, 0.601, 0.604, 0.617, 0.628, 0.648, 0.66, 0.661, 0.671, 0.858]
PCT=[0.4872, 1.0, 0.991, 0.9638, 0.9819, 0.9729, 0.9336, 0.8281, 0.7677, 0.6863, 0.5867, 0.4646, 0.3092, 0.9457, 0.3499, 0.9548, 0.9155, 0.9427, 0.9246, 0.9035, 0.7979, 0.7345, 0.6501, 0.5747, 0.4404, 0.3002, 0.9065, 0.8763, 0.2278, 0.8733, 0.8944, 0.8643, 0.8552, 0.819, 0.7104, 0.6229, 0.5294, 0.4193, 0.264, 0.8824, 0.8431, 0.7888, 0.1176, 0.8401, 0.8069, 0.7828, 0.7587, 0.7014, 0.6109, 0.4962, 0.3861, 0.2398, 0.8854, 0.8462, 0.7858, 0.7376, 0.0799, 0.7496, 0.7255, 0.6621, 0.635, 0.5626, 0.4525, 0.362, 0.1931, 0.8793, 0.8311, 0.7707, 0.6923, 0.6742, 0.0392, 0.6712, 0.6018, 0.5535, 0.5053, 0.4042, 0.3273, 0.184, 0.81, 0.7738, 0.7164, 0.6772, 0.6139, 0.5777, 0.0317, 0.5415, 0.5143, 0.4736, 0.3454, 0.2881, 0.1689, 0.7406, 0.7134, 0.6893, 0.638, 0.5897, 0.5173, 0.4796, 0.0271, 0.4284, 0.3771, 0.276, 0.2021, 0.1357, 0.6531, 0.641, 0.6259, 0.5928, 0.5324, 0.4555, 0.3922, 0.3363, 0.0226, 0.3183, 0.2489, 0.1599, 0.095, 0.5656, 0.5445, 0.5204, 0.4827, 0.4314, 0.4103, 0.368, 0.2911, 0.2519, 0.0181, 0.2172, 0.1267, 0.0754, 0.4766, 0.4434, 0.4072, 0.3952, 0.365, 0.3333, 0.267, 0.2232, 0.1719, 0.1508, 0.0136, 0.1131, 0.0664, 0.3891, 0.3529, 0.3303, 0.279, 0.2549, 0.2308, 0.2051, 0.1418, 0.1011, 0.098, 0.083, 0.009, 0.0543, 0.2202, 0.2081, 0.175, 0.1478, 0.1448, 0.1388, 0.1041, 0.086, 0.0573, 0.0452, 0.0422, 0.0347, 0.0045]
KS=[0.03, 0.06, 0.1, 0.15, 0.2, 0.3, 0.4, 0.55, 0.75, 1.0]
EQR=[[0.181, 0.303, 0.369, 0.401, 0.435, 0.452, 0.46, 0.472, 0.497, 0.496], [0.129, 0.211, 0.257, 0.269, 0.275, 0.283, 0.295, 0.305, 0.322, 0.342], [0.157, 0.214, 0.263, 0.285, 0.292, 0.289, 0.29, 0.312, 0.324, 0.341], [0.144, 0.203, 0.243, 0.284, 0.294, 0.302, 0.303, 0.337, 0.33, 0.332], [0.142, 0.21, 0.251, 0.267, 0.29, 0.302, 0.284, 0.315, 0.306, 0.347], [0.132, 0.186, 0.238, 0.277, 0.277, 0.288, 0.304, 0.304, 0.295, 0.349], [0.126, 0.191, 0.261, 0.256, 0.286, 0.293, 0.295, 0.296, 0.33, 0.373], [0.119, 0.21, 0.263, 0.279, 0.313, 0.286, 0.298, 0.319, 0.337, 0.4], [0.148, 0.222, 0.259, 0.266, 0.301, 0.306, 0.324, 0.306, 0.352, 0.394], [0.161, 0.242, 0.259, 0.28, 0.314, 0.303, 0.335, 0.34, 0.387, 0.444], [0.187, 0.262, 0.284, 0.289, 0.302, 0.315, 0.332, 0.381, 0.433, 0.467], [0.219, 0.255, 0.281, 0.284, 0.311, 0.353, 0.389, 0.427, 0.476, 0.516], [0.272, 0.256, 0.289, 0.344, 0.368, 0.437, 0.466, 0.505, 0.542, 0.537], [0.174, 0.255, 0.304, 0.318, 0.327, 0.323, 0.339, 0.348, 0.355, 0.362], [0.18, 0.306, 0.378, 0.416, 0.429, 0.452, 0.485, 0.496, 0.524, 0.53], [0.154, 0.236, 0.264, 0.286, 0.29, 0.325, 0.318, 0.338, 0.326, 0.327], [0.175, 0.238, 0.271, 0.297, 0.306, 0.309, 0.329, 0.338, 0.348, 0.38], [0.152, 0.214, 0.254, 0.289, 0.305, 0.31, 0.328, 0.329, 0.336, 0.354], [0.133, 0.199, 0.254, 0.274, 0.283, 0.317, 0.302, 0.321, 0.325, 0.383], [0.123, 0.213, 0.264, 0.267, 0.288, 0.308, 0.293, 0.294, 0.323, 0.364], [0.117, 0.231, 0.25, 0.276, 0.29, 0.286, 0.298, 0.319, 0.348, 0.399], [0.138, 0.226, 0.265, 0.283, 0.298, 0.295, 0.327, 0.322, 0.373, 0.424], [0.178, 0.257, 0.291, 0.282, 0.312, 0.306, 0.321, 0.342, 0.394, 0.451], [0.201, 0.251, 0.272, 0.29, 0.311, 0.309, 0.338, 0.379, 0.449, 0.462], [0.232, 0.254, 0.291, 0.289, 0.317, 0.349, 0.378, 0.459, 0.468, 0.505], [0.251, 0.296, 0.29, 0.344, 0.394, 0.424, 0.463, 0.491, 0.53, 0.568], [0.181, 0.259, 0.291, 0.314, 0.342, 0.346, 0.337, 0.333, 0.358, 0.358], [0.199, 0.273, 0.315, 0.333, 0.341, 0.349, 0.36, 0.357, 0.381, 0.396], [0.176, 0.312, 0.375, 0.401, 0.441, 0.456, 0.497, 0.512, 0.538, 0.568], [0.173, 0.251, 0.287, 0.324, 0.322, 0.349, 0.34, 0.339, 0.357, 0.396], [0.155, 0.235, 0.268, 0.307, 0.298, 0.304, 0.341, 0.341, 0.34, 0.39], [0.161, 0.216, 0.259, 0.311, 0.311, 0.318, 0.338, 0.335, 0.348, 0.378], [0.141, 0.21, 0.267, 0.28, 0.28, 0.305, 0.312, 0.324, 0.344, 0.385], [0.122, 0.218, 0.272, 0.285, 0.291, 0.301, 0.317, 0.3, 0.342, 0.405], [0.148, 0.205, 0.261, 0.284, 0.285, 0.302, 0.325, 0.344, 0.384, 0.439], [0.185, 0.255, 0.268, 0.269, 0.296, 0.292, 0.341, 0.333, 0.41, 0.483], [0.217, 0.248, 0.283, 0.284, 0.309, 0.321, 0.341, 0.375, 0.456, 0.495], [0.232, 0.25, 0.289, 0.293, 0.317, 0.33, 0.381, 0.433, 0.487, 0.517], [0.27, 0.276, 0.313, 0.364, 0.387, 0.428, 0.471, 0.502, 0.539, 0.579], [0.187, 0.244, 0.292, 0.327, 0.331, 0.344, 0.338, 0.342, 0.36, 0.382], [0.21, 0.272, 0.309, 0.339, 0.341, 0.366, 0.349, 0.367, 0.371, 0.391], [0.225, 0.298, 0.33, 0.33, 0.344, 0.358, 0.379, 0.373, 0.383, 0.416], [0.21, 0.303, 0.39, 0.432, 0.459, 0.488, 0.519, 0.556, 0.553, 0.591], [0.172, 0.236, 0.291, 0.318, 0.311, 0.333, 0.359, 0.369, 0.359, 0.397], [0.159, 0.237, 0.277, 0.318, 0.313, 0.342, 0.342, 0.351, 0.368, 0.408], [0.159, 0.239, 0.293, 0.306, 0.308, 0.306, 0.321, 0.338, 0.357, 0.423], [0.127, 0.225, 0.265, 0.292, 0.3, 0.305, 0.332, 0.33, 0.362, 0.446], [0.153, 0.237, 0.268, 0.292, 0.311, 0.304, 0.322, 0.346, 0.369, 0.446], [0.174, 0.263, 0.279, 0.288, 0.303, 0.321, 0.312, 0.354, 0.402, 0.457], [0.206, 0.267, 0.278, 0.287, 0.321, 0.325, 0.348, 0.398, 0.461, 0.489], [0.241, 0.259, 0.285, 0.307, 0.303, 0.35, 0.394, 0.445, 0.496, 0.541], [0.289, 0.278, 0.313, 0.36, 0.386, 0.443, 0.479, 0.509, 0.544, 0.589], [0.167, 0.242, 0.297, 0.308, 0.317, 0.343, 0.343, 0.341, 0.357, 0.401], [0.189, 0.263, 0.294, 0.312, 0.34, 0.355, 0.365, 0.365, 0.354, 0.375], [0.215, 0.268, 0.328, 0.331, 0.347, 0.369, 0.368, 0.358, 0.405, 0.417], [0.224, 0.284, 0.329, 0.341, 0.345, 0.375, 0.375, 0.397, 0.388, 0.426], [0.19, 0.33, 0.403, 0.48, 0.496, 0.514, 0.541, 0.566, 0.582, 0.631], [0.187, 0.251, 0.314, 0.322, 0.324, 0.34, 0.35, 0.369, 0.376, 0.421], [0.162, 0.24, 0.285, 0.311, 0.34, 0.34, 0.349, 0.365, 0.393, 0.436], [0.156, 0.243, 0.297, 0.298, 0.33, 0.318, 0.342, 0.345, 0.372, 0.441], [0.156, 0.239, 0.269, 0.311, 0.319, 0.325, 0.335, 0.347, 0.399, 0.47], [0.164, 0.239, 0.28, 0.3, 0.302, 0.318, 0.328, 0.355, 0.435, 0.49], [0.2, 0.27, 0.282, 0.318, 0.306, 0.334, 0.36, 0.41, 0.462, 0.508], [0.24, 0.273, 0.298, 0.319, 0.329, 0.371, 0.391, 0.443, 0.515, 0.537], [0.256, 0.268, 0.284, 0.384, 0.385, 0.462, 0.479, 0.525, 0.55, 0.587], [0.154, 0.232, 0.274, 0.31, 0.314, 0.318, 0.325, 0.349, 0.343, 0.371], [0.176, 0.258, 0.29, 0.309, 0.321, 0.329, 0.356, 0.353, 0.35, 0.4], [0.175, 0.249, 0.308, 0.329, 0.337, 0.35, 0.367, 0.358, 0.39, 0.418], [0.208, 0.274, 0.311, 0.329, 0.359, 0.366, 0.365, 0.394, 0.382, 0.448], [0.224, 0.29, 0.339, 0.341, 0.376, 0.383, 0.384, 0.386, 0.429, 0.453], [0.185, 0.335, 0.438, 0.487, 0.502, 0.564, 0.566, 0.603, 0.634, 0.662], [0.17, 0.242, 0.299, 0.325, 0.334, 0.376, 0.366, 0.365, 0.393, 0.45], [0.167, 0.254, 0.303, 0.319, 0.331, 0.337, 0.358, 0.367, 0.406, 0.479], [0.171, 0.257, 0.291, 0.334, 0.302, 0.339, 0.343, 0.368, 0.42, 0.477], [0.18, 0.248, 0.287, 0.316, 0.313, 0.328, 0.346, 0.379, 0.44, 0.493], [0.203, 0.275, 0.285, 0.301, 0.322, 0.321, 0.345, 0.424, 0.474, 0.511], [0.25, 0.251, 0.275, 0.311, 0.329, 0.361, 0.419, 0.473, 0.515, 0.559], [0.272, 0.274, 0.296, 0.376, 0.408, 0.473, 0.503, 0.549, 0.582, 0.59], [0.149, 0.239, 0.296, 0.302, 0.309, 0.332, 0.342, 0.347, 0.368, 0.398], [0.159, 0.245, 0.294, 0.314, 0.326, 0.335, 0.324, 0.351, 0.374, 0.399], [0.17, 0.242, 0.324, 0.31, 0.333, 0.348, 0.354, 0.362, 0.386, 0.435], [0.185, 0.293, 0.289, 0.335, 0.346, 0.354, 0.386, 0.395, 0.396, 0.443], [0.195, 0.283, 0.346, 0.35, 0.358, 0.374, 0.386, 0.395, 0.401, 0.467], [0.203, 0.284, 0.341, 0.365, 0.381, 0.383, 0.38, 0.404, 0.431, 0.483], [0.191, 0.387, 0.453, 0.515, 0.556, 0.556, 0.591, 0.617, 0.662, 0.691], [0.157, 0.281, 0.316, 0.33, 0.346, 0.354, 0.364, 0.366, 0.422, 0.476], [0.193, 0.274, 0.33, 0.33, 0.324, 0.348, 0.352, 0.398, 0.434, 0.5], [0.188, 0.274, 0.289, 0.324, 0.318, 0.352, 0.372, 0.411, 0.448, 0.51], [0.196, 0.276, 0.315, 0.319, 0.329, 0.354, 0.4, 0.435, 0.502, 0.531], [0.233, 0.266, 0.306, 0.314, 0.317, 0.378, 0.436, 0.498, 0.518, 0.567], [0.257, 0.296, 0.306, 0.375, 0.413, 0.498, 0.525, 0.56, 0.57, 0.597], [0.153, 0.271, 0.308, 0.315, 0.327, 0.332, 0.342, 0.353, 0.376, 0.419], [0.159, 0.242, 0.305, 0.314, 0.31, 0.348, 0.352, 0.366, 0.384, 0.412], [0.152, 0.277, 0.299, 0.326, 0.347, 0.338, 0.347, 0.367, 0.379, 0.431], [0.18, 0.281, 0.312, 0.333, 0.353, 0.352, 0.357, 0.374, 0.408, 0.451], [0.18, 0.294, 0.326, 0.346, 0.357, 0.354, 0.39, 0.386, 0.418, 0.474], [0.202, 0.304, 0.339, 0.357, 0.371, 0.386, 0.406, 0.38, 0.437, 0.487], [0.207, 0.32, 0.356, 0.367, 0.388, 0.395, 0.39, 0.412, 0.452, 0.513], [0.19, 0.426, 0.494, 0.539, 0.567, 0.59, 0.619, 0.648, 0.675, 0.733], [0.177, 0.291, 0.313, 0.328, 0.35, 0.36, 0.378, 0.409, 0.453, 0.51], [0.207, 0.301, 0.326, 0.328, 0.344, 0.348, 0.374, 0.421, 0.486, 0.54], [0.211, 0.295, 0.322, 0.312, 0.355, 0.364, 0.418, 0.47, 0.524, 0.557], [0.237, 0.287, 0.331, 0.31, 0.338, 0.418, 0.467, 0.52, 0.563, 0.581], [0.252, 0.28, 0.33, 0.399, 0.446, 0.508, 0.552, 0.576, 0.587, 0.619], [0.19, 0.254, 0.289, 0.317, 0.323, 0.344, 0.332, 0.36, 0.388, 0.445], [0.193, 0.261, 0.304, 0.32, 0.344, 0.337, 0.356, 0.368, 0.391, 0.447], [0.181, 0.262, 0.298, 0.313, 0.333, 0.33, 0.346, 0.373, 0.396, 0.476], [0.203, 0.273, 0.301, 0.311, 0.335, 0.35, 0.367, 0.363, 0.399, 0.454], [0.196, 0.277, 0.318, 0.34, 0.347, 0.363, 0.384, 0.395, 0.423, 0.501], [0.226, 0.273, 0.321, 0.347, 0.364, 0.385, 0.378, 0.376, 0.446, 0.519], [0.227, 0.315, 0.331, 0.346, 0.382, 0.376, 0.408, 0.419, 0.475, 0.534], [0.218, 0.336, 0.349, 0.363, 0.383, 0.397, 0.422, 0.444, 0.481, 0.535], [0.318, 0.507, 0.54, 0.58, 0.613, 0.63, 0.648, 0.673, 0.713, 0.745], [0.246, 0.313, 0.345, 0.346, 0.365, 0.374, 0.417, 0.455, 0.515, 0.545], [0.241, 0.308, 0.352, 0.335, 0.357, 0.389, 0.421, 0.483, 0.549, 0.576], [0.275, 0.316, 0.335, 0.372, 0.377, 0.449, 0.491, 0.538, 0.584, 0.598], [0.294, 0.31, 0.362, 0.454, 0.521, 0.569, 0.58, 0.603, 0.624, 0.622], [0.217, 0.28, 0.298, 0.327, 0.333, 0.336, 0.337, 0.383, 0.418, 0.481], [0.223, 0.279, 0.3, 0.327, 0.329, 0.36, 0.357, 0.377, 0.423, 0.471], [0.205, 0.277, 0.304, 0.316, 0.337, 0.36, 0.368, 0.383, 0.434, 0.478], [0.222, 0.291, 0.323, 0.313, 0.341, 0.368, 0.354, 0.395, 0.454, 0.504], [0.218, 0.28, 0.315, 0.314, 0.335, 0.356, 0.363, 0.384, 0.455, 0.513], [0.233, 0.289, 0.316, 0.324, 0.372, 0.371, 0.371, 0.418, 0.493, 0.518], [0.244, 0.316, 0.347, 0.346, 0.392, 0.386, 0.388, 0.415, 0.471, 0.55], [0.244, 0.337, 0.356, 0.366, 0.371, 0.396, 0.431, 0.451, 0.511, 0.534], [0.281, 0.362, 0.364, 0.39, 0.397, 0.422, 0.439, 0.47, 0.543, 0.585], [0.424, 0.557, 0.603, 0.616, 0.664, 0.681, 0.684, 0.707, 0.739, 0.785], [0.272, 0.341, 0.347, 0.38, 0.39, 0.396, 0.454, 0.487, 0.559, 0.575], [0.311, 0.313, 0.344, 0.375, 0.409, 0.483, 0.493, 0.542, 0.587, 0.606], [0.336, 0.349, 0.434, 0.496, 0.538, 0.582, 0.585, 0.611, 0.616, 0.623], [0.227, 0.284, 0.303, 0.32, 0.335, 0.323, 0.362, 0.405, 0.47, 0.501], [0.23, 0.3, 0.331, 0.338, 0.333, 0.333, 0.368, 0.41, 0.462, 0.509], [0.261, 0.301, 0.291, 0.339, 0.344, 0.352, 0.375, 0.425, 0.475, 0.515], [0.245, 0.287, 0.335, 0.34, 0.339, 0.355, 0.387, 0.428, 0.485, 0.533], [0.248, 0.296, 0.311, 0.34, 0.34, 0.357, 0.386, 0.431, 0.492, 0.524], [0.241, 0.303, 0.317, 0.345, 0.338, 0.357, 0.394, 0.434, 0.488, 0.543], [0.264, 0.318, 0.342, 0.358, 0.389, 0.376, 0.383, 0.465, 0.511, 0.577], [0.259, 0.326, 0.371, 0.372, 0.381, 0.4, 0.432, 0.489, 0.543, 0.584], [0.286, 0.358, 0.384, 0.384, 0.406, 0.42, 0.459, 0.518, 0.573, 0.602], [0.295, 0.353, 0.362, 0.378, 0.412, 0.446, 0.488, 0.526, 0.562, 0.622], [0.565, 0.627, 0.659, 0.683, 0.678, 0.716, 0.722, 0.764, 0.787, 0.8], [0.342, 0.336, 0.355, 0.432, 0.441, 0.475, 0.532, 0.583, 0.61, 0.626], [0.355, 0.387, 0.483, 0.558, 0.564, 0.628, 0.638, 0.629, 0.653, 0.658], [0.257, 0.28, 0.31, 0.332, 0.347, 0.368, 0.399, 0.46, 0.483, 0.518], [0.257, 0.299, 0.32, 0.338, 0.349, 0.38, 0.418, 0.455, 0.497, 0.561], [0.253, 0.303, 0.318, 0.354, 0.362, 0.377, 0.426, 0.461, 0.508, 0.566], [0.268, 0.302, 0.325, 0.322, 0.343, 0.399, 0.413, 0.479, 0.516, 0.556], [0.273, 0.31, 0.314, 0.338, 0.35, 0.39, 0.443, 0.472, 0.532, 0.566], [0.27, 0.309, 0.344, 0.349, 0.372, 0.406, 0.451, 0.508, 0.538, 0.552], [0.254, 0.316, 0.34, 0.361, 0.358, 0.415, 0.467, 0.506, 0.546, 0.587], [0.257, 0.341, 0.362, 0.35, 0.385, 0.446, 0.494, 0.544, 0.583, 0.587], [0.307, 0.352, 0.371, 0.372, 0.411, 0.464, 0.525, 0.554, 0.608, 0.632], [0.335, 0.372, 0.386, 0.399, 0.436, 0.506, 0.538, 0.572, 0.615, 0.616], [0.354, 0.37, 0.422, 0.425, 0.467, 0.51, 0.56, 0.601, 0.629, 0.642], [0.69, 0.714, 0.711, 0.744, 0.746, 0.746, 0.771, 0.797, 0.822, 0.827], [0.419, 0.467, 0.552, 0.611, 0.642, 0.64, 0.667, 0.663, 0.648, 0.657], [0.307, 0.298, 0.323, 0.397, 0.394, 0.477, 0.49, 0.54, 0.548, 0.594], [0.324, 0.326, 0.336, 0.373, 0.417, 0.464, 0.509, 0.525, 0.578, 0.585], [0.322, 0.313, 0.328, 0.38, 0.414, 0.468, 0.514, 0.523, 0.559, 0.583], [0.327, 0.313, 0.334, 0.39, 0.414, 0.494, 0.529, 0.564, 0.581, 0.603], [0.298, 0.301, 0.323, 0.393, 0.419, 0.491, 0.505, 0.542, 0.575, 0.595], [0.3, 0.303, 0.355, 0.384, 0.435, 0.492, 0.531, 0.557, 0.595, 0.61], [0.306, 0.328, 0.347, 0.414, 0.463, 0.539, 0.563, 0.58, 0.598, 0.628], [0.289, 0.33, 0.361, 0.451, 0.478, 0.539, 0.582, 0.585, 0.614, 0.646], [0.321, 0.379, 0.401, 0.498, 0.536, 0.582, 0.607, 0.623, 0.635, 0.648], [0.368, 0.391, 0.451, 0.521, 0.569, 0.598, 0.626, 0.632, 0.648, 0.662], [0.4, 0.411, 0.516, 0.576, 0.617, 0.65, 0.646, 0.647, 0.662, 0.665], [0.415, 0.498, 0.578, 0.614, 0.649, 0.648, 0.678, 0.684, 0.67, 0.677], [0.809, 0.824, 0.848, 0.846, 0.849, 0.867, 0.854, 0.862, 0.866, 0.85]]
OPEN_THR = [0.70, 0.64, 0.49, 0.36, 0.29, 0.23, 0.195, 0.175]
SHOVE_MARGIN = 0.0
CALL_MARGIN = 0.15
PF_DEPTH = 13.0
PF_CALL_DEPTH = 15.0
RR_MULT = 2.6
TB_EQ = 0.60
CALL_PRIOR = 2.8
STATION_BIG = 1.0
STATION_MED = 0.7
ISO_THR = 0.30
CBET_ON = True
L3_LIM = 0.36
L2_HAVE = 0.30
RESHOVE = True
RESHOVE_BB = 25.0
RESHOVE_CALL = 0.45
DEF_EDGE = 0.12
RR_MODE = 1
RR_PF = 0.9
RR_VP = 1.5
RS_COMMIT = False
BIG_FRAC = 0.75
OPEN_BB = 2.2
NKS = len(KS)


def hand_class(a, b):
    ra, rb = a >> 2, b >> 2
    if ra < rb:
        ra, rb = rb, ra
    if ra == rb:
        return ra * 13 + ra
    if (a & 3) == (b & 3):
        return ra * 13 + rb
    return rb * 13 + ra


def eq_vs(cls, r):
    """Equity of class vs a top-r fraction range (linear interpolation over KS)."""
    row = EQR[cls]
    if r <= KS[0]:
        return row[0]
    for i in range(1, NKS):
        if r <= KS[i]:
            k0 = KS[i - 1]
            w = (r - k0) / (KS[i] - k0)
            return row[i - 1] + (row[i] - row[i - 1]) * w
    return row[-1]


def util(st, me):
    """Cheap ICM proxy for 10/7/5/4/3/2/1/0: points = opponents outlasted + [top2] + 2*[1st]."""
    s = st[me]
    if s <= 0:
        # busting now: we still beat everyone already out; heads-up bust = 2nd (+1)
        dead = 0
        live = 0
        for j in range(len(st)):
            if j != me:
                if st[j] <= 0:
                    dead += 1
                else:
                    live += 1
        return dead + (1.0 if live == 1 else 0.0)
    T = 0
    for x in st:
        T += x
    out = 0.0
    p2 = 0.0
    for j in range(len(st)):
        sj = st[j]
        if j == me:
            continue
        if sj <= 0:
            out += 1.0   # busted (now or earlier): outlasted for sure
            continue
        out += s / (s + sj)
        if T - sj > 0:
            p2 += sj / T * s / (T - sj)
    p1 = s / T
    return out + 3.0 * p1 + p2


class Seat(object):
    __slots__ = ('n', 'f', 'c', 'r', 'k', 'pf_n', 'pf_v', 'pf_r', 'fr_n', 'fr_f')

    def __init__(self):
        self.n = self.f = self.c = self.r = self.k = 0
        self.pf_n = self.pf_v = self.pf_r = 0
        self.fr_n = self.fr_f = 0

    def agg(self):          # raise frequency, prior 0.12
        return (self.r + 0.12 * 8) / (self.n + 8)

    def loose(self):        # call+raise frequency, prior 0.3
        return (self.r + self.c + 0.3 * 8) / (self.n + 8)

    def fold_vs_raise(self):  # prior 0.6
        return (self.fr_f + 0.6 * 4) / (self.fr_n + 4)

    def deadish(self):
        return self.n >= 6 and self.f + self.k >= self.n - 0 and self.r == 0 and self.c == 0


class Bot(Agent):
    def __init__(self):
        self.new_table({}, 0, 8)

    def new_table(self, rules, seat, n_players):
        try:
            n = int(n_players) if n_players else 8
        except Exception:
            n = 8
        self.n = max(2, min(10, n))
        self.seats = [Seat() for _ in range(10)]
        self.cur = None
        self.hseen = 0
        self.pf_aggr = False
        self.raised_street = -1

    def hand_end(self, result):
        pass

    # ---------- bookkeeping ----------
    def _track(self, obs, me):
        if obs.hand_no != self.cur:
            self.cur = obs.hand_no
            self.hseen = 0
            self.pf_aggr = False
            self.raised_street = -1
            self.pf_raise_seen = False
            self.pf_acted = set()
        h = obs.history
        if not h:
            return
        L = len(h)
        if L < self.hseen:
            self.hseen = 0
        i = self.hseen
        seats = self.seats
        pre = obs.street == 0
        while i < L:
            e = h[i]
            i += 1
            try:
                s = e[0]
                a = e[1][0]
            except Exception:
                continue
            if not isinstance(s, int) or s < 0 or s >= 10:
                continue
            if s == me:
                if a == 'raise' and pre:
                    self.pf_raise_seen = True
                continue
            st = seats[s]
            st.n += 1
            if a == 'fold':
                st.f += 1
            elif a == 'call':
                st.c += 1
            elif a == 'raise':
                st.r += 1
            else:
                st.k += 1
            if pre:
                if s not in self.pf_acted:
                    self.pf_acted.add(s)
                    st.pf_n += 1
                    if a == 'call' or a == 'raise':
                        st.pf_v += 1
                    if a == 'raise':
                        st.pf_r += 1
                if self.pf_raise_seen:
                    st.fr_n += 1
                    if a == 'fold':
                        st.fr_f += 1
                if a == 'raise':
                    self.pf_raise_seen = True
        self.hseen = L

    # ---------- action helpers ----------
    @staticmethod
    def _passive(obs):
        if 'check' in obs.legal:
            return ('check', 0)
        return ('fold', 0)

    @staticmethod
    def _raise_to(obs, amt):
        if 'raise' not in obs.legal:
            if 'call' in obs.legal:
                return ('call', 0)
            return ('check', 0)
        try:
            lo = int(-(-obs.min_raise // 1))
            hi = int(obs.max_raise // 1)
        except Exception:
            lo, hi = 1, 0
        if lo > hi:
            if 'call' in obs.legal:
                return ('call', 0)
            return ('check', 0) if 'check' in obs.legal else ('fold', 0)
        a = int(amt)
        if a < lo:
            a = lo
        if a > hi:
            a = hi
        # if the raise leaves us with little behind, just go all-in
        mybet = obs.bets[obs.seat]
        behind_after = obs.stacks[obs.seat] - (a - mybet)
        if behind_after < 0.25 * (a - mybet + 1) or behind_after < 2 * obs.blinds[1]:
            a = hi
        return ('raise', int(a))

    @staticmethod
    def _call(obs):
        if 'call' in obs.legal:
            return ('call', 0)
        return ('check', 0)

    def act(self, obs):
        try:
            return self._act(obs)
        except Exception:
            try:
                return self._passive(obs)
            except Exception:
                return ('fold', 0)

    def _act(self, obs):
        me = obs.seat
        if not obs.blinds or obs.blinds[1] <= 0:
            obs.blinds = (max(1, obs.to_call or 1), max(2, obs.to_call or 2))
        self._track(obs, me)
        n = len(obs.stacks)
        if n > len(self.seats):
            self.seats.extend(Seat() for _ in range(n - len(self.seats)))
        if obs.street == 0:
            return self._preflop(obs, me, n)
        return self._postflop(obs, me, n)

    # ---------- preflop ----------
    def _order(self, obs, n):
        alive = [i for i in range(n) if obs.stacks[i] > 0 or obs.in_hand[i] or obs.bets[i] > 0]
        b = obs.button if isinstance(obs.button, int) else 0
        alive.sort(key=lambda i: (i - b - 1) % n)
        if len(alive) == 2:
            return alive, alive[1:] + alive[:1]
        return alive, alive[2:] + alive[:2]

    def _preflop(self, obs, me, n):
        sb, bb = obs.blinds
        bb = max(1, bb)
        stacks = obs.stacks
        bets = obs.bets
        cls = hand_class(obs.hole[0], obs.hole[1])
        pct = PCT[cls]
        my_tot = stacks[me] + bets[me]
        mx = max(bets)
        to_call = obs.to_call or 0
        pot_tot = (obs.pot or 0) + sum(bets)
        rot, order = self._order(obs, n)
        try:
            idx = order.index(me)
        except ValueError:
            idx = 0
        behind = [s for s in order[idx + 1:] if obs.in_hand[s] and stacks[s] > 0]
        opp_live = [s for s in range(n) if s != me and obs.in_hand[s]]
        max_opp = 0
        for s in opp_live:
            t = stacks[s] + bets[s]
            if t > max_opp:
                max_opp = t
        eff = min(my_tot, max_opp)
        eff_bb = eff / bb
        seats = self.seats
        unopened = mx <= bb
        tot = [stacks[i] + bets[i] for i in range(n)]

        if unopened:
            limpers = sum(1 for s in opp_live if bets[s] >= bb and s not in behind) - (0 if me in rot[1:2] else 0)
            if eff_bb <= PF_DEPTH or my_tot <= PF_DEPTH * bb:
                return self._shove_or_fold(obs, me, n, cls, behind + [s for s in opp_live if s not in behind and stacks[s] > 0], tot, pot_tot)
            nb = len(behind)
            thr = OPEN_THR[min(nb, 7)]
            if limpers > 0:
                thr *= 0.75
            # steal vs folding/dead seats behind
            if behind:
                fold_p = 1.0
                for s in behind:
                    st = seats[s]
                    fv = st.fold_vs_raise()
                    if st.deadish():
                        fv = 1.0
                    fold_p *= fv
                if fold_p > 0.55:
                    thr = max(thr, 0.25 + 0.75 * (fold_p - 0.55) / 0.45)
            lim_seats = [s for s in opp_live if s not in behind and bets[s] >= bb]
            st_lim = [s for s in lim_seats if seats[s].loose() > 0.6 and seats[s].agg() < 0.12]
            iso = False
            if st_lim and len(lim_seats) <= 2 and eff_bb > 20:
                thr = max(thr, ISO_THR)
                iso = True
            if pct <= thr:
                size = (OPEN_BB + 0.3 if nb >= 3 else OPEN_BB) * bb + limpers * bb
                if iso:
                    size = 4 * bb + 1.5 * bb * limpers
                self.pf_aggr = True
                return self._raise_to(obs, size)
            if to_call == 0:
                return ('check', 0)
            # SB completes cheaply with decent hands; set-mine / limp along behind limpers
            if to_call <= 0.5 * bb + 1 and pct <= 0.55:
                return self._call(obs)
            if limpers > 0 and to_call <= bb and pct <= 0.22 and eff_bb > 25:
                return self._call(obs)
            return self._passive(obs)

        # facing a raise
        raiser = None
        rmax = -1
        for s in opp_live:
            if bets[s] > rmax:
                rmax = bets[s]
                raiser = s
        st = seats[raiser] if raiser is not None else Seat()
        rt = stacks[raiser] + bets[raiser] if raiser is not None else mx
        if RR_MODE == 1:
            pfr = (st.pf_r + 0.15 * 6) / (st.pf_n + 6)
            vp = (st.pf_v + 0.3 * 6) / (st.pf_n + 6)
            rr = min(1.0, max(0.03, pfr * RR_PF + max(0.0, vp - 0.5) * RR_VP))
        else:
            rr = min(1.0, max(0.03, st.agg() * RR_MULT))
        allin_like = stacks[raiser] == 0 if raiser is not None else False
        size_bb = mx / bb
        if size_bb > 20 and not (st.agg() > 0.25):
            rr *= 0.6
        if self.pf_raise_seen and bets[me] > bb:  # we already raised; they re-raised
            rr *= 0.7
        eq = eq_vs(cls, rr)
        if behind:
            eq *= 0.97 ** len(behind)
        committed = to_call >= 0.33 * my_tot or (my_tot - mx) < 10 * bb or allin_like or eff_bb <= PF_CALL_DEPTH
        if (RESHOVE and not allin_like and raiser is not None and 'raise' in obs.legal and eff_bb <= RESHOVE_BB
                and not (self.pf_raise_seen and bets[me] > bb) and rt > 0):
            # re-shove over a single open: fold equity from the opener + players behind
            pc = min(0.9, max(0.15, RESHOVE_CALL))
            if RS_COMMIT and tot[raiser] > 0:
                frac_in = bets[raiser] / float(tot[raiser])
                if frac_in >= 0.33:
                    pc = max(pc, min(0.95, 0.45 + frac_in))
                if st.loose() > 0.6 and st.agg() < 0.12:
                    pc = max(pc, 0.8)
            sp = {raiser: (pc, max(0.02, rr * pc))}
            callers = [raiser] + [s for s in behind if s != raiser] + [s for s in opp_live if s != raiser and s not in behind and stacks[s] > 0]
            r = self._shove_or_fold(obs, me, n, cls, callers, tot, pot_tot, sp, dry=True)
            if r:
                ok_call = committed and self._call_allin_ok(obs, me, n, tot, raiser, eq, pot_tot)
                if r[0] > r[1] + SHOVE_MARGIN and (not ok_call or my_tot <= rt or r[0] >= r[2]):
                    self.pf_aggr = True
                    return self._raise_to(obs, obs.max_raise)
        if committed:
            # all-in decision under the ICM proxy
            if self._call_allin_ok(obs, me, n, tot, raiser, eq, pot_tot):
                if 'raise' in obs.legal and not allin_like and my_tot <= 1.0 * rt:
                    return self._raise_to(obs, obs.max_raise)
                if 'call' in obs.legal:
                    return ('call', 0)
                return self._raise_to(obs, obs.max_raise)
            return self._passive(obs)
        # deep: 3-bet / call / fold
        if eq >= TB_EQ and 'raise' in obs.legal:
            self.pf_aggr = True
            return self._raise_to(obs, 3 * mx + (pot_tot - mx - bets[me]) * 0.5)
        price = to_call / float(my_tot)
        if eq >= 0.50 and price <= 0.12:
            return self._call(obs)
        po = to_call / float(pot_tot + to_call)
        if DEF_EDGE < 1 and price <= 0.08 and eq >= po + DEF_EDGE and not behind:
            return self._call(obs)
        if (cls // 13) == (cls % 13) and price <= 0.06 and eff_bb >= 30:
            return self._call(obs)
        if price <= 0.03 and eq >= 0.42:
            return self._call(obs)
        return self._passive(obs)

    def _caller_prob(self, s, eff_bb):
        st = self.seats[s]
        if st.deadish():
            return 0.0
        prior = min(0.9, max(0.06, CALL_PRIOR / max(1.0, eff_bb)))
        # observed continue-vs-raise
        cont = (st.fr_n - st.fr_f + prior * 4) / (st.fr_n + 4)
        return min(1.0, max(0.02, cont))

    def _shove_or_fold(self, obs, me, n, cls, behind, tot, pot_tot, special=None, dry=False):
        bets = obs.bets
        stacks = obs.stacks
        bb = max(1, obs.blinds[1])
        my_tot = tot[me]
        # fold scenario: blinds go to biggest bettor
        st_fold = list(stacks)
        w = max(range(n), key=lambda i: bets[i] if i != me else -1)
        st_fold[w] += pot_tot
        u_fold = util(st_fold, me)
        st_steal = list(stacks)
        st_steal[me] += pot_tot
        u_steal = util(st_steal, me)
        p_none = 1.0
        eu = 0.0
        for s in behind:
            e = min(my_tot, tot[s])
            if special and s in special:
                c, wdt = special[s]
            else:
                c = self._caller_prob(s, e / bb)
                wdt = c
            if c <= 0:
                continue
            p = p_none * c
            q = eq_vs(cls, wdt)
            dead = pot_tot - bets[me] - bets[s]
            win = list(stacks)
            win[me] = my_tot - e + dead + 2 * e
            win[s] = tot[s] - e
            lose = list(stacks)
            lose[me] = my_tot - e
            lose[s] = tot[s] - e + dead + 2 * e
            eu += p * (q * util(win, me) + (1 - q) * util(lose, me))
            p_none *= (1 - c)
        eu += p_none * u_steal
        if dry:
            # (eu shove, u fold, eu of calling all-in vs the first special seat is computed by caller)
            return (eu, u_fold, -1e9)
        if eu > u_fold + SHOVE_MARGIN:
            self.pf_aggr = True
            return self._raise_to(obs, obs.max_raise)
        if obs.to_call == 0:
            return ('check', 0)
        return ('fold', 0)

    def _call_allin_ok(self, obs, me, n, tot, raiser, eq, pot_tot):
        stacks = obs.stacks
        bets = obs.bets
        if raiser is None:
            return eq > 0.6
        my_tot = tot[me]
        e = min(my_tot, tot[raiser])
        st_fold = list(stacks)
        st_fold[raiser] += pot_tot
        u_fold = util(st_fold, me)
        dead = pot_tot - bets[me] - bets[raiser]
        win = list(stacks)
        win[me] = my_tot - e + dead + 2 * e
        win[raiser] = tot[raiser] - e
        lose = list(stacks)
        lose[me] = my_tot - e
        lose[raiser] = tot[raiser] - e + dead + 2 * e
        eu = eq * util(win, me) + (1 - eq) * util(lose, me)
        return eu > u_fold + CALL_MARGIN

    # ---------- postflop ----------
    def _strength(self, hole, board):
        cards = list(hole) + list(board)
        hs = ev(cards)
        cat = hs >> 20
        bs = ev(list(board))
        bcat = bs >> 20
        br = sorted([c >> 2 for c in board], reverse=True)
        h0, h1 = hole[0] >> 2, hole[1] >> 2
        level = 0
        if cat >= 4:
            if cat > bcat:
                level = 5
                if cat == 4 and bcat < 4:
                    # straight with 4-flush board is weaker
                    suits = [0, 0, 0, 0]
                    for c in board:
                        suits[c & 3] += 1
                    if max(suits) >= 3:
                        level = 4
            else:
                level = 1
        elif cat == 3:
            if h0 == h1:
                level = 5
            elif bcat >= 3:
                level = 1 if max(h0, h1) >= 10 else 0
            else:
                level = 4
        elif cat == 2:
            if bcat == 2:
                level = 1 if max(h0, h1) >= 11 else 0
            elif bcat == 1:
                # one pair on board + we pair one card or have pocket pair
                if h0 == h1:
                    level = 3 if h0 > br[0] else 2
                else:
                    level = 3 if (h0 == br[0] or h1 == br[0]) else 2
            else:
                level = 4
        elif cat == 1:
            if bcat == 1:
                level = 1 if max(h0, h1) >= 11 else 0
            elif h0 == h1:
                if h0 > br[0]:
                    level = 4 if h0 >= 9 else 3
                elif h0 > br[1]:
                    level = 2
                else:
                    level = 1
            else:
                pr = h0 if (h0 in br) else h1
                kick = h1 if pr == h0 else h0
                if pr == br[0]:
                    level = 3 if kick >= 9 or pr >= 11 else 2
                    if kick >= 11:
                        level = 4 if len(board) == 3 else 3
                elif len(br) > 1 and pr == br[1]:
                    level = 2
                else:
                    level = 1
        # draws
        draw = 0.0
        if len(board) < 5:
            suits = [0, 0, 0, 0]
            for c in cards:
                suits[c & 3] += 1
            for su in range(4):
                if suits[su] >= 4 and ((hole[0] & 3) == su or (hole[1] & 3) == su) and cat < 5:
                    draw += 0.18
                    break
            m = 0
            for c in cards:
                m |= 1 << (c >> 2)
            if m & 4096:
                m |= 1 << 13  # ace low marker handled below
            rb = 0
            for c in cards:
                rb |= 1 << (c >> 2)
            hm = (1 << h0) | (1 << h1)
            if cat < 4:
                for lo in range(0, 10):
                    w4 = 15 << lo
                    if (rb & w4) == w4 and (hm & w4):
                        if lo >= 1 and lo + 4 <= 12:
                            draw += 0.16
                        else:
                            draw += 0.08
                        break
        return level, draw, cat

    def _postflop(self, obs, me, n):
        bb = max(1, obs.blinds[1])
        stacks = obs.stacks
        bets = obs.bets
        pot_tot = (obs.pot or 0) + sum(bets)
        to_call = obs.to_call or 0
        my_stack = stacks[me]
        opps = [s for s in range(n) if s != me and obs.in_hand[s]]
        nopp = len(opps)
        level, draw, cat = self._strength(obs.hole, obs.board)
        street = obs.street
        seats = self.seats
        station = all(seats[s].loose() > 0.6 and seats[s].agg() < 0.12 for s in opps) if opps else False
        maniac = False
        bettor = None
        if to_call > 0:
            bm = -1
            for s in opps:
                if bets[s] > bm:
                    bm = bets[s]
                    bettor = s
            if bettor is not None and seats[bettor].agg() > 0.28:
                maniac = True
        spr = my_stack / float(max(1, pot_tot))
        if to_call == 0:
            # betting decision
            if opps and all(seats[s].deadish() for s in opps):
                return self._bet(obs, pot_tot, 0.3)
            if level >= 4:
                frac = BIG_FRAC if nopp <= 2 else BIG_FRAC + 0.1
                if station:
                    frac = STATION_BIG
                if spr < 1.6:
                    return self._raise_to(obs, obs.max_raise)
                return self._bet(obs, pot_tot, frac)
            if level == 3:
                if spr < 1.0:
                    return self._raise_to(obs, obs.max_raise)
                return self._bet(obs, pot_tot, STATION_MED if station else (0.55 if nopp <= 2 else 0.5))
            if level == 2 and nopp == 1 and (station or street < 3):
                return self._bet(obs, pot_tot, 0.45)
            if draw >= 0.16 and nopp <= 2 and street < 3 and not station:
                return self._bet(obs, pot_tot, 0.55)
            if CBET_ON and self.pf_aggr and street == 1 and nopp == 1 and not station and level <= 1:
                bs = seats[opps[0]]
                if bs.fold_vs_raise() > 0.45:
                    return self._bet(obs, pot_tot, 0.4)
            return ('check', 0)
        # facing a bet
        po = to_call / float(pot_tot + to_call)
        allin = to_call >= my_stack
        if level >= 5:
            if 'raise' in obs.legal:
                return self._raise_to(obs, max(bets) * 3 + pot_tot * 0.3)
            return self._call(obs)
        if level == 4:
            if spr < 2.0 and 'raise' in obs.legal and nopp <= 2:
                return self._raise_to(obs, obs.max_raise)
            if po <= 0.42 or maniac or nopp == 1:
                return self._call(obs)
            return ('fold', 0)
        if level == 3:
            lim = L3_LIM if nopp == 1 else L3_LIM - 0.08
            if maniac:
                lim = 0.48
            if allin and not maniac:
                lim -= 0.06
            if po <= lim:
                return self._call(obs)
            return ('fold', 0)
        need = po
        have = 0.0
        if level == 2:
            have = L2_HAVE if not maniac else L2_HAVE + 0.12
        elif level == 1:
            have = 0.12 if not maniac else 0.25
        if street < 3:
            d = draw * (2 if street == 1 and not allin else 1) * 1.0
            have = max(have, d + (0.05 if not allin else 0.0))
        if need <= have:
            return self._call(obs)
        return ('fold', 0)

    def _bet(self, obs, pot_tot, frac):
        mybet = obs.bets[obs.seat]
        amt = mybet + max(obs.blinds[1], int(pot_tot * frac))
        return self._raise_to(obs, amt)
