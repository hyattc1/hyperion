"""The dials of rival 3's decision core: the night's window and variant dials for the shipped base (`hybrid3_x`).

On plain hold'em rival 3's core makes ~97% of hybrid3_x's decisions, so Hero's `Config` keys (`preflop.open_frac` and
the rest) only reach the 14 tables Hero plays whole and the ~0.1 decision a table the core declines. These dials say
the same things to the core. Each is a named copy of one literal in rival 3's own code; the defaults are those
literals, so with no dial set every decision is bit-identical to rival 3 as built (tests/test_ship.py).

Set them as `r3.<name>` in a dials dict (hyperion/ship.py, `--dials` on the tools):

    {"r3.open_late_scale": 1.3, "r3.bluff_scale": 1.3}       # too passive for this field
    {"r3.push_margin": 0.03, "r3.call_margin": 0.03, "r3.raise_shift": 0.05, "r3.three_bet_scale": 0.7}   # survival

Directions were checked with paired runs in model mode (docs/decisions.md, "Ship hybrid3_x as the base").
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _dial(default, doc: str):
    return field(default=default, metadata={"doc": doc})


@dataclass
class Rival3Knobs:
    # preflop, unopened, deeper than short_bb: rival 3 raises first in (or isolates limpers) when the hand's percentile
    # is inside the position's threshold: 0.48 with one seat behind, 0.36 with two ... 0.12 with seven
    open_scale: float = _dial(1.0, "multiplies every position's raise-first-in threshold: above 1 opens wider, below 1 "
                                   "tighter")
    open_late_scale: float = _dial(1.0, "multiplies it again for the cutoff and the button (two or three seats behind)")
    # push or fold
    short_bb: float = _dial(10.0, "effective stack in big blinds at or under which an unopened pot is shove or fold")
    push_margin: float = _dial(0.002, "points (ICM on the table's payouts) a shove must beat folding by, open or "
                                      "re-shove: higher = fewer shoves, lower or negative = more")
    # facing a raise
    commit_bb: float = _dial(18.0, "at or under this effective depth, a call or re-shove facing a raise is priced as "
                                   "all-in by ICM")
    call_margin: float = _dial(0.002, "points a committing call must beat folding by: higher = fewer stack-off calls")
    three_bet_scale: float = _dial(1.0, "multiplies the deep value 3-bet range: below 1 tighter")
    # postflop
    bluff_scale: float = _dial(1.0, "multiplies the chance of every bluff and semi-bluff, the flop continuation bet "
                                    "included")
    call_edge: float = _dial(0.12, "strength over the price a postflop call needs: higher folds more")
    raise_shift: float = _dial(0.0, "added to the strength rival 3 raises a bet with (0.8; 0.7 when shallow): higher = "
                                    "fewer stack-offs")
    # opponent reads
    prior_scale: float = _dial(1.0, "weight of the prior in every seat read (about four actions' worth): below 1 the "
                                    "reads move sooner")
    dead_hands: int = _dial(22, "hands with no voluntary chip before a seat reads as dead (folds to everything): lower "
                                "catches folding and timing-out seats sooner")
