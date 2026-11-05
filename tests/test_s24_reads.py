"""S24's two reads against the over-folding exploiter 5 found (docs/drills/climb/s24-log.md), behind dials that default to the
shipped play (tests/test_compose.py replays the composite): the shove read's counts, and that each read's dials reach the decisions,
its gates keep other tables as F plays them, and a table replays exactly."""
import pytest

from hyperion.core.types import Rules
from hyperion.hybrid.core3 import sr_scan

from .test_s2_dials import _digest

HU = ["hero", "exploiter5"]
THREE = ["hero", "exploiter5", "loose_aggro"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
SR = {"r3.sr_depth": 15.0}
CBR = {"hero.postflop.cbr_from": 0.8, "hero.postflop.cbr_full": 0.95}


def test_the_shove_read_counts_first_actions_at_that_depth():
    start = [200, 100, 1000, 200]  # 20 a big blind: 10, 5, 50 and 10 bb
    hist = [(0, ("raise", 190)), (1, ("fold", 0)), (2, ("call", 190)), (3, ("fold", 0))]
    # seat 0's raise to 95% of its chips is an all-in; after it nobody has a chance; seat 2 is too deep anyway
    assert sr_scan(hist, start, 20, 15.0) == {0: True}


def test_the_shove_read_counts_a_chance_without_a_shove_and_each_seat_once():
    start = [200, 100, 1000, 200]
    hist = [(0, ("raise", 50)), (1, ("fold", 0)), (2, ("call", 50)), (3, ("raise", 200)), (0, ("raise", 200))]
    assert sr_scan(hist, start, 20, 15.0) == {0: False, 1: False, 3: True}  # seat 0's later shove is not a first action


def test_a_blind_posted_as_a_raise_is_not_an_action():
    start = [200, 100]
    assert sr_scan([(1, ("post", 10)), (0, ("raise", 20)), (0, ("raise", 200)), (1, ("fold", 0))], start, 20, 15.0) == {0: True}


@pytest.mark.parametrize("dials, seats, rules", [(SR, ["hero", "exploiter3", "exploiter5"], R3), (CBR, HU, R2)])
def test_the_reads_reach_the_decisions(dials, seats, rules):
    assert any(_digest(dials, t, seats, rules)[0] != _digest({}, t, seats, rules)[0] for t in range(80))


@pytest.mark.parametrize("shut", [{"r3.sr_depth": 0.0}, {"r3.sr_depth": 15.0, "r3.sr_min": 10_000},
                                  {"hero.postflop.cbr_from": 1.0}, {**CBR, "hero.postflop.cbr_min": 10_000},
                                  {**CBR, "hero.postflop.cbr_max_alive": 1}])
def test_a_shut_gate_plays_as_f(shut):
    assert all(_digest(shut, t, HU, R2)[0] == _digest({}, t, HU, R2)[0] for t in range(3))



def test_both_reads_play_a_twist_table_exactly_as_f():
    from hyperion.drills import variants as V

    d = {**SR, **CBR}
    for name in ("short_deck", "bounty"):
        rules = V.get(name).rules
        assert all(_digest(d, t, rules=rules)[0] == _digest({}, t, rules=rules)[0] for t in range(2)), name


def test_with_both_reads_a_table_replays_exactly():
    d = {**SR, **CBR}
    assert _digest(d, 1, THREE, R3)[0] == _digest(d, 1, THREE, R3)[0]
