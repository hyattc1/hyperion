from snapcall.core.types import Action, HandResult
from snapcall.strategy.profiler import NEUTRAL_DIALS, Profiler

from .strategy_helpers import make_obs, preflop_obs, street_obs

R, C, F, K = Action.raise_to, Action.call(), Action.fold(), Action.check()


def play_hand(prof, hand_no, pre_actions, post=(), showdown=None, deltas=None):
    """Feed one hand: hero (seat 1, BB) observes after the preflop actions, then hand_end sees the rest."""
    obs = preflop_obs("7h 2d", 1, actions=pre_actions, hand_no=hand_no)
    prof.observe(obs)
    history = list(pre_actions) + list(post)
    prof.hand_end(HandResult(hand_no, deltas or [0] * 8, showdown or {}, (), history))


def test_vpip_pfr_and_fold_to_raise_counts():
    prof = Profiler(8)
    # seat 2 opens, 3 folds, 4 calls, 5 folds, 6 folds, 7 folds, 0 folds; hero to act
    play_hand(prof, 0, [(2, R(50)), (3, F), (4, C), (5, F), (6, F), (7, F), (0, F)])
    assert prof.vpip[2] == 1 and prof.pfr[2] == 1
    assert prof.vpip[4] == 1 and prof.pfr[4] == 0
    assert prof.pre_faced[3] == 1 and prof.pre_folded[3] == 1
    assert prof.pre_faced[0] == 1 and prof.pre_folded[0] == 1
    assert prof.hands[2] == 1 and prof.hands[1] == 1


def test_streets_are_split_without_markers():
    prof = Profiler(8)
    pre = [(2, R(50)), (3, F), (4, F), (5, F), (6, F), (7, F), (0, F)]
    # hero (BB) calls; flop: hero checks, seat 2 bets, hero folds
    post = [(1, C), (1, K), (2, R(60)), (1, F)]
    play_hand(prof, 0, pre, post)
    assert prof.post_faced[1] == 1 and prof.post_folded[1] == 1
    assert prof.post_aggr[2] == 1 and prof.post_actions[2] == 1
    assert prof.pre_folded[1] == 0  # the preflop call was not a fold


def test_dead_seat_flag_and_dials():
    prof = Profiler(8)
    for h in range(6):
        # seat 3 is dead: folds to every raise it faces
        play_hand(prof, h, [(2, R(50)), (3, F), (4, F), (5, F), (6, F), (7, F), (0, F)])
    assert prof.dead_seat(3)
    assert not prof.dead_seat(2)
    d = prof.exploit_dials(3)
    assert d["steal_mult"] == 2.0 and d["bluff_mult"] == 3.0
    assert prof.archetype(3) == "dead"


def test_station_and_nit_flags():
    prof = Profiler(8)
    for h in range(24):
        # seat 4 calls every raise and never folds; seat 5 folds every hand
        play_hand(prof, h, [(2, R(50)), (3, F), (4, C), (5, F), (6, F), (7, F), (0, F)],
                  post=[(1, F), (2, R(60)), (4, C), (2, R(200)), (4, C)])
    assert prof.station(4) and prof.fold_to_bet(4) < 0.1
    assert prof.nit(5) and prof.vpip_rate(5) < 0.1
    assert prof.exploit_dials(4)["bluff_mult"] < 0.2
    assert prof.exploit_dials(5)["bluff_mult"] > 1.3


def test_maniac_and_shove_counters():
    prof = Profiler(8)
    for h in range(12):
        play_hand(prof, h, [(2, R(2000)), (3, F), (4, F), (5, F), (6, F), (7, F), (0, F)])
    assert prof.maniac(2) and prof.shoves[2] == 12 and prof.shove_rate(2) > 0.8
    assert prof.faced_shove[3] == 12 and prof.called_shove[3] == 0
    assert prof.exploit_dials(2)["call_down_mult"] > 1.2


def test_dials_neutral_without_data_and_reset():
    prof = Profiler(8)
    assert prof.exploit_dials(0) == NEUTRAL_DIALS
    play_hand(prof, 0, [(2, R(50)), (3, F), (4, F), (5, F), (6, F), (7, F), (0, F)])
    assert prof.exploit_dials(3) != NEUTRAL_DIALS or prof.actions[3] == 1
    prof.reset(8)
    assert prof.hands == [0] * 8 and prof.exploit_dials(2) == NEUTRAL_DIALS


def test_observe_is_incremental_and_hand_end_without_observe_is_tolerated():
    prof = Profiler(8)
    pre = [(2, R(50)), (3, F)]
    obs = preflop_obs("7h 2d", 4, actions=pre, hand_no=5)
    prof.observe(obs)
    prof.observe(obs)  # same history twice: nothing double counted
    assert prof.actions[2] == 1 and prof.pfr[2] == 1
    prof.hand_end(HandResult(5, [0] * 8, {2: (0, 1)}, (), pre + [(4, F), (5, F), (6, F), (7, F), (0, F), (1, F)]))
    assert prof.showdowns[2] == 1 and prof.actions[1] == 1
    # a hand we never saw
    prof.hand_end(HandResult(6, [0] * 8, {}, (), [(2, R(60)), (3, C)]))
    assert prof.actions[2] == 2 and prof.calls[3] == 1


def test_showdown_rate_and_summary():
    prof = Profiler(8)
    play_hand(prof, 0, [(2, R(50)), (3, F), (4, C), (5, F), (6, F), (7, F), (0, F)], post=[(1, F)],
              showdown={2: (0, 1), 4: (2, 3)})
    assert prof.wtsd(2) > prof.wtsd(3)
    s = prof.summary(2)
    assert s["hands"] == 1 and "type" in s
