"""O8's price (docs/drills/climb/s21-log.md, "O7" and "O8"): F's result relative to folding when its first-in open is
called or re-raised, in big-blind equivalents of ICM points (payouts 8..1, at F's own points per chip), by rival 3's
hand percentile band, the seats behind and the effective depth. Measured on diagnostic tables (seeds 13000-13099, nine
fields pooled, hierarchical shrinkage k = 160 at each level, chosen on seeds 13100-13179) and fixed before any screen.
Generated from docs/drills/climb/s21-o7-table.json by goal/s21o7/gen_module.py; do not edit by hand."""
from __future__ import annotations

# upper edges of the hand bands (rival 3's PCT, 0 = best); the last band runs to 1
P_BANDS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)
# TABLE[hand band][seats behind 1, 2, 3, 4, 5+][depth: 10-20 bb, 20-40 bb, over 40 bb]
TABLE = (
    ((-0.923, -0.889, -1.604), (-2.159, +0.728, -0.336), (-3.154, -0.509, -0.068), (-0.584, -0.043, +1.238), (-0.844, -0.309, -0.076)),
    ((-0.571, +0.380, +0.056), (-0.936, -1.039, -0.015), (-1.123, -0.941, -0.114), (-1.534, -0.754, -1.684), (-1.171, -1.199, -0.148)),
    ((-0.968, -0.111, +0.959), (-1.547, -1.238, -0.158), (-1.748, -1.475, -0.481), (-1.310, -0.959, -0.483), (-1.212, -1.344, -0.136)),
    ((-1.070, -0.930, -0.169), (-1.342, -1.247, -0.519), (-2.074, -0.950, -1.242), (-1.979, -0.881, -0.312), (-1.265, -1.081, -0.793)),
    ((-0.420, -0.104, -0.482), (-1.503, -0.919, -0.396), (-1.715, -1.300, -1.699), (-1.128, -1.081, -0.296), (-1.224, -1.156, -0.447)),
    ((-0.976, -0.274, -0.608), (-1.415, -1.342, -0.912), (-1.466, -1.329, -0.779), (-1.759, -0.876, -0.234), (-1.557, -0.821, -0.750)),
    ((-1.406, -0.830, +0.117), (-1.684, -1.859, -0.440), (-2.272, -1.215, -2.955), (-1.579, -0.880, -0.437), (-1.449, -1.522, -0.978)),
    ((-0.701, -0.584, -0.881), (-1.687, -1.351, -1.585), (-1.747, -0.706, -0.906), (-1.642, -1.018, -1.171), (-1.536, -1.163, -1.040)),
    ((-0.551, -0.695, -0.272), (-1.905, -2.858, -1.204), (-1.542, -1.346, -1.554), (-1.155, -1.464, -0.406), (-1.895, -1.348, -1.693)),
    ((-0.465, -0.334, -1.027), (-1.509, -1.177, -1.165), (-1.949, -2.584, -1.400), (-1.427, -1.116, -0.491), (-1.449, -1.251, -0.898)),
)


def open_ev(p: float, behind: int, eff_bb: float) -> float:
    """E[F's result | its first-in open is called or re-raised] in big-blind equivalents (a table lookup)."""
    b = 0
    for edge in P_BANDS:
        if p < edge:
            break
        b += 1
    nb = behind - 1 if behind < 5 else 4
    if nb < 0:
        nb = 0
    return TABLE[b][nb][0 if eff_bb <= 20.0 else 1 if eff_bb <= 40.0 else 2]
