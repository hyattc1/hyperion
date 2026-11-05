"""S23: the pooled re-raise gate on the specialist's three-handed tables (`short.three2_rr_t`, hyperion/strategy/short.py),
off by default so F plays batch 8 exactly (tests/test_ship.py and the identity check in docs/drills/climb/s23-log.md)."""
import os

import pytest

from hyperion.compose.bot import SHIP_DIALS
from hyperion.core.types import Rules
from hyperion.strategy import short as SH
from hyperion.strategy.tables import TABLES_DIR

from .test_s20_three import _obs

R3 = Rules(n_players=3, payouts=(10, 7, 5))
T3B = os.path.join(TABLES_DIR, "extra", "short_3b.json")
has_table = pytest.mark.skipif(not os.path.exists(T3B), reason="no second three-handed table")


class _Stat:
    def __init__(self, fr, fr_r):
        self.fr, self.fr_r = fr, fr_r


class _Core:
    def __init__(self, stats):
        self.st = stats


class _Base:
    def __init__(self, stats):
        self.core = _Core(stats)


def test_the_new_dials_are_off_and_not_shipped():
    p = SH.ShortParams()
    assert p.three2_rr_t == 0.0 and p.three2_rr_k == 8.0 and p.three2_rr_prior == 0.075
    assert not any(k.startswith("short.three2_rr") for k in SHIP_DIALS)


def test_the_pooled_read_shrinks_to_its_prior():
    m = SH.ShortMember(SH.ShortParams(three2_rr_k=8.0, three2_rr_prior=0.075))
    # no raises faced yet: the prior
    assert m.rr3(_Base([_Stat(0, 0), _Stat(0, 0), _Stat(0, 0)]), [0, 1, 2], 0) == pytest.approx(0.075)
    # the two opponents re-raised 6 of the 24 raises they faced: (6 + 0.6) / (24 + 8)
    assert m.rr3(_Base([_Stat(99, 99), _Stat(12, 4), _Stat(12, 2)]), [0, 1, 2], 0) == pytest.approx(6.6 / 32)
    # the base has no such counts: None (the gate then shuts)
    assert m.rr3(object(), [0, 1, 2], 0) is None


@has_table
def test_the_gate_opens_against_re_raisers_and_shuts_against_folders():
    m = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0, three2_rr_t=0.2))
    m.new_table(R3, 0, 3)
    first = _obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=20, seat=0)
    m.light_observe(first)
    jammers = _Base([_Stat(0, 0), _Stat(20, 8), _Stat(20, 6)])  # pooled (14 + 0.6) / 48 = 0.30
    folders = _Base([_Stat(0, 0), _Stat(20, 1), _Stat(20, 0)])  # pooled (1 + 0.6) / 48 = 0.03
    assert m.wants(first, None, jammers)
    assert not m.wants(first, None, folders)
    assert not m.wants(first, None, None)  # no base: no read, F plays
    off = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0))
    off.new_table(R3, 0, 3)
    off.light_observe(first)
    assert off.wants(first, None, folders)  # the dial off: the read is not consulted
