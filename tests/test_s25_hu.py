"""S25's heads-up floors on an all-in opponent's width (docs/drills/climb/s25-log.md; hyperion/hybrid/dials.py hu_jam_w,
hu_openjam_scale, hu_jam_max_bb), behind dials that default to the shipped play: the floor's values, that the dials reach
the decisions heads-up and nowhere else, and that off they play exactly as F."""
import pytest

from hyperion.core.types import Rules
from hyperion.hybrid.core3 import Rival3Core, nash_push_width
from hyperion.hybrid.dials import Rival3Knobs

from .test_s2_dials import _digest

HU = ["hero", "elite1"]
THREE = ["hero", "elite1", "elite2"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
S25 = {"r3.hu_jam_w": 0.30, "r3.hu_openjam_scale": 1.0}


def test_the_nash_push_width_reads_the_table():
    assert 0.55 < nash_push_width(10) < 0.60  # 0.578 in tables/pushfold_hu.json
    assert 0.44 < nash_push_width(15) < 0.46
    assert nash_push_width(15.4) == nash_push_width(15)
    assert nash_push_width(100) == nash_push_width(25) and nash_push_width(0) == nash_push_width(1)


def test_the_floor_by_line():
    core = Rival3Core.__new__(Rival3Core)
    core.k = Rival3Knobs(hu_jam_w=0.30, hu_openjam_scale=0.5)
    assert core._hu_jam_floor(2, True, 15.0) == 0.30  # our open, re-jammed
    assert core._hu_jam_floor(1, False, 10.0) == pytest.approx(0.5 * nash_push_width(10))  # the button's first-in all-in
    assert core._hu_jam_floor(1, True, 10.0) == 0.0  # one raise and it was ours: not a jam we face
    assert core._hu_jam_floor(3, True, 10.0) == 0.0  # a 3-bet war: no floor
    core.k = Rival3Knobs(hu_jam_w=0.30)
    assert core._hu_jam_floor(1, False, 10.0) == 0.0  # the open-jam floor off


def test_the_floors_reach_the_heads_up_decisions():
    assert any(_digest(S25, t, HU, R2)[0] != _digest({}, t, HU, R2)[0] for t in range(40))


@pytest.mark.parametrize("shut", [{"r3.hu_jam_w": 0.0, "r3.hu_openjam_scale": 0.0}, {**S25, "r3.hu_jam_max_bb": 0.0}])
def test_a_shut_gate_plays_as_f(shut):
    assert all(_digest(shut, t, HU, R2)[0] == _digest({}, t, HU, R2)[0] for t in range(3))


def test_three_alive_plays_as_f():
    # the three-handed format never has two alive, so the floors never fire there
    assert all(_digest(S25, t, THREE, R3)[0] == _digest({}, t, THREE, R3)[0] for t in range(3))


def test_a_twist_table_plays_as_f():
    from hyperion.drills import variants as V

    for name in ("short_deck", "bounty"):
        rules = V.get(name).rules
        assert all(_digest(S25, t, rules=rules)[0] == _digest({}, t, rules=rules)[0] for t in range(2)), name


def test_a_table_replays_exactly():
    assert _digest(S25, 1, HU, R2)[0] == _digest(S25, 1, HU, R2)[0]
