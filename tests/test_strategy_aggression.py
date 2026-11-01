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


def test_per_seat_switch_to_the_reshove_read(tables):
    """The per-opportunity read switches on for one seat's re-shoves once its smoothed re-shove rate at <= 25 bb
    passes the threshold: a frequent re-shover's range widens (A9o calls), a rare one keeps the per-hand read; a
    first-in shove never switches."""
    core = core_with(tables, {"preflop.shove_ctx_auto": 0.12}, seat=7)
    pre = core.preflop
    obs = preflop_obs("Ad 9c", 7, stacks=[400] * 8, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(50)), (0, F), (1, R(400))])
    spot = Spot(obs, obs.hole)
    frequent, rare = Profiler(8), Profiler(8)
    for prof in (frequent, rare):
        prof.reset(8, 7)
    frequent.vo_opp_b[1][1], frequent.vo_shove_b[1][1] = 30, 9  # 30% of 30 spots
    rare.vo_opp_b[1][1], rare.vo_shove_b[1][1] = 30, 1
    assert pre.frequent_reshover(frequent, 1) and not pre.frequent_reshover(rare, 1)
    assert not pre.frequent_reshover(rare, 2)  # no data: the prior 0.06 is under the threshold
    per_hand = pre.shover_range(spot, rare)
    assert pre.shover_range(spot, frequent) > per_hand
    off = core_with(tables, {}, seat=7).preflop
    assert off.shover_range(spot, frequent) == pytest.approx(off.shover_range(spot, rare))  # off: the per-hand read
    assert pre.act(spot, frequent) == C
    assert pre.act(spot, rare) == F
    # a first-in shove from a frequent re-shover keeps the per-hand read
    frequent.vo_opp_b[6][1], frequent.vo_shove_b[6][1] = 30, 9
    fi = preflop_obs("Ad 9c", 7, stacks=[400] * 8, actions=FOLDS(2, 3, 4, 5) + [(6, R(400))])
    fs = Spot(fi, fi.hole)
    assert fs.facing_shove and pre._shove_ctx(fs) == (1, -1) and pre.frequent_reshover(frequent, 6)
    assert pre.shover_range(fs, frequent) == pytest.approx(off.shover_range(fs, frequent))


# ---------------------------------------------------------------- heads-up raised pots

from hyperion.core.types import HandResult  # noqa: E402
from hyperion.strategy.postflop import Postflop, PostflopParams  # noqa: E402

from .strategy_helpers import street_obs  # noqa: E402

CHECK = Action.check()
BTN_OPEN_BB_CALL = FOLDS(2, 3, 4, 5, 6) + [(7, R(50)), (0, F), (1, C)]


def _play_hand(prof, flop_actions, hand_no=3):
    prof.observe(preflop_obs("Ah Kh", 0, button=7, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(50))], hand_no=hand_no))
    prof.hand_end(HandResult(hand_no, [0] * 8, {}, (), BTN_OPEN_BB_CALL + flop_actions))


def test_profiler_counts_cbets_and_folds_to_them():
    prof = Profiler(8)
    prof.reset(8, 0)
    _play_hand(prof, [(1, CHECK), (7, R(36)), (1, F)])
    assert (prof.cb_opp[7], prof.cbets[7], prof.fcb_opp[1], prof.fcb_fold[1]) == (1, 1, 1, 1)
    _play_hand(prof, [(1, CHECK), (7, CHECK)], hand_no=4)  # the raiser checked back: a chance, no c-bet
    assert (prof.cb_opp[7], prof.cbets[7], prof.fcb_opp[1]) == (2, 1, 1)
    _play_hand(prof, [(1, R(36)), (7, F)], hand_no=5)  # the caller led: no c-bet chance
    assert prof.cb_opp[7] == 2 and prof.fcb_opp[1] == 1
    assert prof.cbet_rate(7) == pytest.approx((1 + 0.65 * 4) / 6)
    assert prof.fold_to_cbet(1) == pytest.approx((1 + 0.5 * 4) / 5)


def _facing_cbet(hole="8h 7h", board="Kc 8d 3s", bet=36):
    st = [1950] * 8
    st[7] = 1950 - bet
    bets = [0] * 8
    bets[7] = bet
    in_hand = [s in (1, 7) for s in range(8)]
    hist = BTN_OPEN_BB_CALL + [(1, CHECK), (7, R(bet))]
    return street_obs(hole, board, 1, button=7, stacks=st, pot=110, in_hand=in_hand, bets=bets, history=hist)


def test_middle_pair_calls_a_small_cbet_only_with_the_lever():
    obs = _facing_cbet()
    prof = Profiler(8)
    prof.reset(8, 1)
    prof.pre_raiser = 7
    off = Postflop(PostflopParams(), seed=1)
    on = Postflop(PostflopParams(vs_cbet_margin=0.05), seed=1)
    spot = Spot(obs, obs.hole)
    assert off.act(spot, obs.hole, prof, False) == F  # middle pair (0.32) under pot odds 0.20 + 0.15
    assert on.act(spot, obs.hole, prof, False) == C
    big = _facing_cbet(bet=110)  # a pot-sized bet is not a small c-bet
    assert on.act(Spot(big, big.hole), big.hole, prof, False) == F
    prof.pre_raiser = 4  # the bettor was not the preflop raiser
    assert on.act(spot, obs.hole, prof, False) == F
    rare = Postflop(PostflopParams(vs_cbet_margin=0.05, vs_cbet_min_rate=0.8), seed=1)
    prof.pre_raiser = 7
    assert rare.act(spot, obs.hole, prof, False) == F  # no c-bet data: the prior 0.65 is under 0.8


def test_cbet_bluffs_follow_the_callers_fold_to_cbet():
    st = [1950] * 8
    in_hand = [s in (1, 7) for s in range(8)]
    obs = street_obs("5h 4c", "Kc 9d 2s", 7, button=7, stacks=st, pot=110, in_hand=in_hand,
                     history=BTN_OPEN_BB_CALL + [(1, CHECK)])
    spot = Spot(obs, obs.hole)
    folder, sticky = Profiler(8), Profiler(8)
    for prof, k in ((folder, 18), (sticky, 1)):
        prof.reset(8, 7)
        prof.fcb_opp[1], prof.fcb_fold[1] = 20, k
    read = Postflop(PostflopParams(cbet_ftc_read=True), seed=3)
    counts = {}
    for name, prof in (("folder", folder), ("sticky", sticky)):
        counts[name] = sum(read.act(spot, obs.hole, prof, True).kind is ActionKind.RAISE for _ in range(300))
    assert counts["folder"] > 200 and counts["sticky"] < 60


def test_opens_tighten_against_a_reshove_threat_behind(tables):
    """15 bb on the button: blinds that re-shove 40% of the opens they face shrink the open range (K5o folds),
    blinds at the prior do not, and the multiplier never widens."""
    core = core_with(tables, {"preflop.reshove_threat": 2.0}, seat=7)
    pre = core.preflop
    obs = _btn_first_in("Kh 5c", 15)
    spot = Spot(obs, obs.hole)
    calm, threat = Profiler(8), Profiler(8)
    for prof in (calm, threat):
        prof.reset(8, 7)
    for s in (0, 1):
        threat.vo_opp_b[s][1], threat.vo_shove_b[s][1] = 30, 12
        calm.vo_opp_b[s][1], calm.vo_shove_b[s][1] = 30, 0
    assert pre.reshove_threat_mult(spot, calm) == 1.0
    assert pre.reshove_threat_mult(spot, threat) < 0.8
    assert pre.act(spot, calm).kind is ActionKind.RAISE
    assert pre.act(spot, threat) == F
    off = core_with(tables, {}, seat=7).preflop
    assert off.act(spot, threat).kind is ActionKind.RAISE


def test_profiler_counts_how_often_an_opener_folds_to_a_reraise():
    prof = Profiler(8)
    prof.reset(8, 0)
    prof.observe(preflop_obs("Ah Kh", 0, button=7, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(50))], hand_no=3))
    prof.hand_end(HandResult(3, [0] * 8, {}, (), FOLDS(2, 3, 4, 5, 6) + [(7, R(50)), (0, F), (1, R(2000)), (7, F)]))
    assert (prof.oft_opp[7], prof.oft_fold[7]) == (1, 1)
    assert prof.oft_opp[1] == 0  # the re-raiser is not the opener
    assert prof.open_fold_to_reraise(7) == pytest.approx((1 + 0.75 * 5) / 6)


def test_exploitative_reshove_reads_the_openers_fold_rate(tables):
    """18 bb in the big blind against a button min-raise: against an opener that folds 18 of 20 opens to a re-raise
    J7o re-shoves on fold equity; against one that folds 4 of 20 it folds, and 72o never re-shoves."""
    core = core_with(tables, {"preflop.reshove_mid_bb": 25, "pushfold.reshove_exploit": True})
    folder, caller = Profiler(8), Profiler(8)
    for prof, k in ((folder, 18), (caller, 4)):
        prof.reset(8, 1)
        prof.oft_opp[7], prof.oft_fold[7] = 20, k

    def act(hole, prof):
        obs = preflop_obs(hole, 1, button=7, stacks=[360] * 8, actions=BTN_OPEN)
        return core.preflop.act(Spot(obs, obs.hole), prof)

    assert act("Jh 7c", folder).kind is ActionKind.RAISE and core.pushfold.last == "reshove_exploit"
    assert act("Jh 7c", caller) == F
    assert act("7h 2c", folder) == F
    assert act("Ah 8c", caller).kind is ActionKind.RAISE  # a real hand still re-shoves against callers
    table_only = core_with(tables, {"preflop.reshove_mid_bb": 25})
    obs = preflop_obs("Jh 7c", 1, button=7, stacks=[360] * 8, actions=BTN_OPEN)
    assert table_only.preflop.act(Spot(obs, obs.hole), folder) == F
