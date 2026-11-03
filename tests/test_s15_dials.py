"""S15's fix against the third exploiter (docs/drills/climb/s15-log.md): the stab read, behind dials that default to
the shipped play (tests/test_compose.py replays the composite); here the read counts what it says, the dials reach the
decisions they name, the gate keeps twist tables as F plays them, and a table replays exactly."""
import pytest

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules
from hyperion.strategy.profiler import Profiler

from .test_s2_dials import _digest

HU = ["hero", "exploiter3"]
THREE = ["hero", "exploiter3", "loose_aggro"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
# S15's candidate
S = {"hero.postflop.stab_from": 0.55, "hero.postflop.stab_full": 0.8, "hero.postflop.stab_prior": 0.4,
     "hero.postflop.stab_min": 3, "hero.postflop.stab_pool": 7, "hero.postflop.stab_margin": 0.03,
     "hero.postflop.stab_holdem_only": True}


def _obs(seat, hist, bets, to_call):
    return Observation(hole=(0, 1), board=(), street=0, seat=seat, button=0, stacks=[1000, 1000], bets=list(bets),
                       in_hand=[True, True], pot=0, to_call=to_call, min_raise=40, max_raise=1000,
                       legal=frozenset(ActionKind), hand_no=0, blinds=(10, 20), history=list(hist))


def _hand(prof, me, post):
    """Heads-up, seat 0 on the button: it opens, seat 1 (the big blind) calls; then the postflop actions `post`."""
    pre = [(0, Action.raise_to(50)), (1, Action.call())]
    if me == 1:
        prof.observe(_obs(1, pre[:1], (50, 20), 30))
    else:
        prof.observe(_obs(0, [], (10, 20), 10))
    prof.hand_end(HandResult(hand_no=0, deltas=[0, 0], history=pre + post, showdown={}, board=()))


def test_the_stab_read_counts_bets_right_after_my_check_by_street_kind():
    prof = Profiler(2)
    prof.reset(2, 1)  # me seat 1, out of position after the flop
    # flop: I check, it bets (a stab), I call; turn: I check, it checks (a chance not taken); river: I bet
    _hand(prof, 1, [(1, Action.check()), (0, Action.raise_to(60)), (1, Action.call()),
                    (1, Action.check()), (0, Action.check()), (1, Action.raise_to(100)), (0, Action.fold())])
    assert prof.st_opp[0] == [1, 1, 0] and prof.st_bet[0] == [1, 0, 0]
    _hand(prof, 1, [(1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.raise_to(60)),
                    (1, Action.fold())])
    assert prof.st_opp[0] == [2, 2, 0] and prof.st_bet[0] == [1, 1, 0]
    assert prof.stab_rate(0, 1, 0.5, 2.0) == pytest.approx((1 + 1.0) / (2 + 2.0))
    assert prof.stab_rate(0, 3, 0.5, 2.0, pool=6) == prof.stab_rate(0, 2, 0.5, 2.0)  # turn and river pooled
    assert prof.stab_rate(0, 1, 0.5, 2.0, pool=7) == pytest.approx((2 + 1.0) / (4 + 2.0))
    assert prof.st_opp[1] == [0, 0, 0]  # my own actions are never counted


def test_a_lead_into_me_is_not_a_stab():
    prof = Profiler(2)
    prof.reset(2, 0)  # me seat 0 on the button: in position after the flop
    _hand(prof, 0, [(1, Action.raise_to(40)), (0, Action.call()), (1, Action.check()), (0, Action.check()),
                    (1, Action.check()), (0, Action.raise_to(80)), (1, Action.fold())])
    assert prof.st_opp[1] == [0, 0, 0]  # it led the flop and acted first on the turn and river: no check of mine


S7 = {**S, "hero.postflop.stab_streets": 7}


@pytest.mark.parametrize("dials,ref", [(S, {}), (S7, S), ({**S7, "hero.postflop.stab_bluff": 1.0}, S7),
                                       ({**S, "hero.postflop.stab_aggr_only": True}, S)])
def test_each_s15_dial_reaches_the_decisions(dials, ref):
    assert any(_digest(dials, t, HU, R2)[0] != _digest(ref, t, HU, R2)[0] for t in range(10)), dials


def test_three_handed_with_every_s15_dial_replays_exactly():
    d = {**S, "hero.postflop.stab_bluff": 0.5, "hero.postflop.stab_streets": 7}
    assert _digest(d, 1, THREE, R3)[0] == _digest(d, 1, THREE, R3)[0]


def test_the_stab_read_counts_a_long_board_without_an_error():
    """river_of_blood deals past the river (obs.street 4 and up, the profiler's street with it): those count as the
    river."""
    prof = Profiler(2)
    prof.reset(2, 1)
    prof._start_blank()
    prof.tstreet, prof.inhand, prof.need = 4, 0b11, 0b11
    prof._consume([(1, Action.check()), (0, Action.raise_to(50))], 4)
    assert prof.st_opp[0] == [0, 0, 1] and prof.st_bet[0] == [0, 0, 1]


def test_stab_holdem_only_plays_a_twist_table_exactly_as_f():
    from hyperion.drills import variants as V

    for name in ("short_deck", "bounty"):
        rules = V.get(name).rules
        d = {**S, "hero.postflop.stab_bluff": 0.5, "hero.postflop.stab_streets": 7}
        assert all(_digest(d, t, rules=rules)[0] == _digest({}, t, rules=rules)[0] for t in range(2)), name


def test_stab_max_alive_plays_heads_up_as_without_it():
    d = {**S, "hero.postflop.stab_max_alive": 3}
    assert all(_digest(d, t, HU, R2)[0] == _digest(S, t, HU, R2)[0] for t in range(3))


def test_stab_pfr_min_reaches_the_decisions():
    """Exploiter 3 raises preflop far more than 0.3 of its hands heads-up: the gate passes it some of the time, and a
    gate no seat passes plays as F."""
    d = {**S, "hero.postflop.stab_pfr_min": 0.3}
    assert any(_digest(d, t, HU, R2)[0] != _digest({}, t, HU, R2)[0] for t in range(10))
    shut = {**S, "hero.postflop.stab_pfr_min": 1.01}
    assert all(_digest(shut, t, HU, R2)[0] == _digest({}, t, HU, R2)[0] for t in range(3))


def test_the_lead_rate_leaves_out_the_stabs_after_my_check():
    """S15d: a seat's free bets apart from the ones right after my check in a heads-up pot."""
    prof = Profiler(2)
    prof.reset(2, 1)  # me seat 1, out of position after the flop
    # flop: I check, it bets (a stab); turn: I check, it checks; river: I check, it bets (a stab)
    _hand(prof, 1, [(1, Action.check()), (0, Action.raise_to(60)), (1, Action.call()),
                    (1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.raise_to(80)),
                    (1, Action.fold())])
    assert prof.post_free[0] == 3 and prof.post_free_bets[0] == 2 and sum(prof.st_opp[0]) == 3
    assert prof.lead_rate(0, 0.3, 2.0) == pytest.approx((0 + 0.6) / (0 + 2.0))
    prof2 = Profiler(2)
    prof2.reset(2, 0)  # me seat 0 on the button: seat 1 acts first after the flop, its bets are leads
    _hand(prof2, 0, [(1, Action.raise_to(40)), (0, Action.call()), (1, Action.raise_to(80)), (0, Action.fold())])
    assert prof2.lead_rate(1, 0.3, 2.0) == pytest.approx((2 + 0.6) / (2 + 2.0))


def test_stab_lead_max_reaches_the_decisions_and_shut_plays_as_f():
    d = {**S, "hero.postflop.stab_pfr_min": 0.35, "hero.postflop.stab_lead_max": 0.4}
    assert any(_digest(d, t, HU, R2)[0] != _digest({}, t, HU, R2)[0] for t in range(10))
    shut = {**S, "hero.postflop.stab_lead_max": -0.01}
    assert all(_digest(shut, t, HU, R2)[0] == _digest({}, t, HU, R2)[0] for t in range(3))
