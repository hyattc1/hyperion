"""Mid-phase aggression levers (docs/decisions.md, "Mid-phase aggression pass"): re-shoves above push/fold depth
from the solved re-shove table with the opener's observed open rate as its width, and the reads they use."""
import pytest

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.strategy.hero import HeroCore, config_from_dict
from hyperion.strategy.profiler import Profiler
from hyperion.strategy.spot import Spot
from hyperion.strategy.tables import load

from .strategy_helpers import preflop_obs

R, C, F = Action.raise_to, Action.call(), Action.fold()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731
BTN_OPEN = FOLDS(2, 3, 4, 5, 6) + [(7, R(45)), (0, F)]  # button min-raises to 2.25 bb, the small blind folds


@pytest.fixture(scope="module")
def tables():
    return load(need_hu=True)


def core_with(tables, cfg: dict, seat: int = 1) -> HeroCore:
    core = HeroCore(config_from_dict(cfg, seed=1), tables)
    core.new_table(Rules(), seat, 8)  # installs the ICM curve
    return core


def test_profiler_counts_first_in_opens_by_position_class():
    prof = Profiler(8)
    prof.reset(8, 0)
    # button 7: UTG is seat 2 (five behind), seat 5 has four behind, the cutoff 6 three (7, 0, 1)
    prof.observe(preflop_obs("Ah Kh", 0, button=7, actions=FOLDS(2, 3, 4, 5) + [(6, R(50))] + FOLDS(7)))
    assert prof.open_opp[5] == [0, 1] and prof.opens[5] == [0, 0]  # folded first in with four behind: early
    assert prof.open_opp[6] == [1, 0] and prof.opens[6] == [1, 0]  # the cutoff opened: a late open
    assert prof.open_opp[7] == [0, 0]  # the button faced a raise: not first in


def test_profiler_skips_limped_pots_and_short_stacks():
    prof = Profiler(8)
    prof.reset(8, 0)
    prof.observe(preflop_obs("Ah Kh", 0, button=7, actions=[(2, C)] + FOLDS(3, 4) + [(5, R(80))] + FOLDS(6)))
    assert prof.open_opp[2] == [0, 1] and prof.opens[2] == [0, 0]  # the limper was first in and did not raise
    assert prof.open_opp[5] == [0, 0]  # an iso-raise over a limper is not an open
    prof = Profiler(8)
    prof.reset(8, 0)
    st = [2000] * 8
    st[5] = 200  # 10 bb: a first-in raise there is push/fold, not a width read
    prof.observe(preflop_obs("Ah Kh", 0, button=7, stacks=st, actions=FOLDS(2, 3, 4) + [(5, R(200))] + FOLDS(6)))
    assert prof.open_opp[5] == [0, 0]


def test_open_rate_is_smoothed_toward_the_prior():
    prof = Profiler(8)
    prof.reset(8, 0)
    assert prof.open_rate(3, True, 0.4, 6.0) == pytest.approx(0.4)
    prof.open_opp[3][0], prof.opens[3][0] = 40, 32
    assert 0.7 < prof.open_rate(3, True, 0.4, 6.0) < 0.8
    assert prof.open_rate(3, False, 0.15, 6.0) == pytest.approx(0.15)  # the early class saw nothing


def test_big_blind_reshoves_at_mid_depth_only_with_the_lever(tables):
    """18 bb in the big blind against a button min-raise: the default re-raises only its value slice (A8o folds);
    with the lever the solved re-shove set shoves A8o and 55 and still folds 72o."""
    st = [360] * 8
    off = core_with(tables, {})
    on = core_with(tables, {"preflop.reshove_mid_bb": 25})
    for hole in ("Ah 8c", "5h 5c"):
        obs = preflop_obs(hole, 1, button=7, stacks=st, actions=BTN_OPEN)
        assert off.act(obs) == F
        a = on.act(obs)
        assert a.kind is ActionKind.RAISE and a.amount == obs.max_raise and on.preflop.last == "reshove_mid"
    assert on.act(preflop_obs("7h 2c", 1, button=7, stacks=st, actions=BTN_OPEN)) == F
    deep = [800] * 8  # 40 bb: beyond the table and the lever
    assert on.act(preflop_obs("Ah 8c", 1, button=7, stacks=deep, actions=BTN_OPEN)).kind is not ActionKind.RAISE


def test_mid_reshove_filters_by_seat_and_opener(tables):
    st = [360] * 8
    sb = core_with(tables, {"preflop.reshove_mid_bb": 25, "preflop.reshove_mid_max_behind": 0}, seat=0)
    obs = preflop_obs("Ah 8c", 0, button=7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(45))])
    assert sb.act(obs).kind is not ActionKind.RAISE  # the small blind has the big blind behind it: filtered out
    late = core_with(tables, {"preflop.reshove_mid_bb": 25, "preflop.reshove_mid_opener_max_behind": 3})
    utg = preflop_obs("Ah 8c", 1, button=7, stacks=st, actions=[(2, R(45))] + FOLDS(3, 4, 5, 6, 7, 0))
    assert late.act(utg).kind is not ActionKind.RAISE  # an under-the-gun open is not a late open
    assert late.act(preflop_obs("Ah 8c", 1, button=7, stacks=st, actions=BTN_OPEN, hand_no=4)).kind is ActionKind.RAISE


def test_reshove_width_reads_the_openers_observed_open_rate(tables):
    """The re-shove table's w is the opener's late-position open rate: against a button that opens 80% the big
    blind shoves A8o; against one that opens 10% it folds it."""
    core = core_with(tables, {"preflop.reshove_mid_bb": 25, "pushfold.reshove_w_observed": True})
    st = [360] * 8
    obs = preflop_obs("Ah 8c", 1, button=7, stacks=st, actions=BTN_OPEN)
    spot = Spot(obs, obs.hole)
    loose, tight = Profiler(8), Profiler(8)
    for prof, k in ((loose, 32), (tight, 4)):
        prof.reset(8, 1)
        prof.open_opp[7][0], prof.opens[7][0] = 40, k
    pf = core.pushfold
    assert pf.opener_width(spot, tight, 7) < pf.opener_width(spot, None, 7) < pf.opener_width(spot, loose, 7)
    assert core.preflop.act(spot, loose).kind is ActionKind.RAISE
    assert core.preflop.act(spot, tight) == F
    # off: the seat prior times the PFR ratio, as the deep pass had it (one hand seen: PFR jumps)
    old = core_with(tables, {"preflop.reshove_mid_bb": 25})
    assert old.pushfold.opener_width(spot, tight, 7) == pytest.approx(0.40)


def _btn_first_in(hole, bb_deep, seat=7, folds=(2, 3, 4, 5, 6), hand_no=3):
    return preflop_obs(hole, seat, button=7, stacks=[20 * bb_deep] * 8, actions=FOLDS(*folds), hand_no=hand_no)


def test_first_in_shove_zone_above_push_fold_depth(tables):
    """13 bb on the button, folded to: the default min-raises 44 and K8o; with the zone at 13 bb the solved first-in
    table shoves 44 and folds K8o (outside the solved 30%), and with fi_rest_open K8o keeps the chart's raise."""
    off = core_with(tables, {}, seat=7)
    a = off.act(_btn_first_in("4h 4c", 13))
    assert a.kind is ActionKind.RAISE and a.amount < 100
    zone = core_with(tables, {"pushfold.fi_threshold_bb": 13}, seat=7)
    obs = _btn_first_in("4h 4c", 13)
    a = zone.act(obs)
    assert a.kind is ActionKind.RAISE and a.amount == obs.max_raise and zone.last_path == "pushfold"
    assert zone.act(_btn_first_in("Kh 8c", 13, hand_no=4)) == F
    rest = core_with(tables, {"pushfold.fi_threshold_bb": 13, "pushfold.fi_rest_open": True}, seat=7)
    a = rest.act(_btn_first_in("Kh 8c", 13))
    assert a.kind is ActionKind.RAISE and a.amount < 100 and rest.last_path == "preflop"
    deeper = _btn_first_in("4h 4c", 16, hand_no=5)  # beyond the zone: the chart again
    assert zone.act(deeper).amount < 100


def test_first_in_shove_zone_reaches_deeper_from_late_seats(tables):
    late = core_with(tables, {"pushfold.fi_late_threshold_bb": 16}, seat=7)
    obs = _btn_first_in("4h 4c", 16)
    assert late.act(obs).amount == obs.max_raise  # the button has two behind: in the zone at 16 bb
    utg = core_with(tables, {"pushfold.fi_late_threshold_bb": 16}, seat=2)
    obs = preflop_obs("Ah Kc", 2, button=7, stacks=[320] * 8)
    a = utg.act(obs)
    assert a.kind is ActionKind.RAISE and a.amount < obs.max_raise  # under the gun at 16 bb opens normally
    assert not utg.pushfold.fi_zone(Spot(obs, obs.hole))
