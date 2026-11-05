"""S22's fix against the fourth exploiter (docs/drills/climb/s22-log.md): the river-bet read, behind dials that default to
the shipped play (tests/test_compose.py replays the composite); here the read counts what it says, the dials reach the
decisions they name, the gates keep the other tables as F plays them, and a table replays exactly."""
import pytest

from hyperion.core.types import Action, Rules
from hyperion.strategy.profiler import Profiler

from .test_s15_dials import _hand
from .test_s2_dials import _digest

HU = ["hero", "exploiter4"]
THREE = ["hero", "exploiter4", "loose_aggro"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
# S22's candidate on top of SHIP_DIALS (batch 7's F)
S = {"hero.postflop.rbet_from": 0.5, "hero.postflop.rbet_full": 0.65, "hero.postflop.rbet_prior": 0.35,
     "hero.postflop.rbet_n": 4.0, "hero.postflop.rbet_min": 3, "hero.postflop.rbet_margin": 0.03,
     "hero.postflop.rbet_max_alive": 3, "hero.postflop.rbet_holdem_only": True}


def test_the_river_read_counts_leads_and_bets_after_my_check():
    prof = Profiler(2)
    prof.reset(2, 1)  # me seat 1, out of position after the flop: its river action comes after my check
    _hand(prof, 1, [(1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.check()),
                    (1, Action.check()), (0, Action.raise_to(60)), (1, Action.fold())])
    assert prof.rv_opp == [1, 0] and prof.rv_bet == [1, 0]
    prof2 = Profiler(2)
    prof2.reset(2, 0)  # me seat 0 on the button: seat 1 acts first on the river (a lead, or a check)
    _hand(prof2, 0, [(1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.check()),
                     (1, Action.raise_to(40)), (0, Action.fold())])
    _hand(prof2, 0, [(1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.check()),
                     (1, Action.check()), (0, Action.check())])
    assert prof2.rv_opp == [0, 2] and prof2.rv_bet == [0, 1]  # my own river actions are never counted
    assert prof2.river_bet_rate(1, 0.35, 4.0) == pytest.approx((1 + 1.4) / (2 + 4.0))
    assert prof2.river_bet_rate(1, 0.35, 4.0, min_n=3) == 0.0  # no read before min_n chances


def test_a_river_raise_of_my_bet_and_the_turn_are_not_chances():
    prof = Profiler(2)
    prof.reset(2, 1)
    # turn: I check, it bets (a turn chance, not the river's); river: I bet, it raises (facing a bet: no chance)
    _hand(prof, 1, [(1, Action.check()), (0, Action.check()), (1, Action.check()), (0, Action.raise_to(40)),
                    (1, Action.call()), (1, Action.raise_to(80)), (0, Action.raise_to(240)), (1, Action.fold())])
    assert prof.rv_opp == [0, 0] and prof.rv_bet == [0, 0]


def test_the_river_read_counts_a_long_board_as_the_river():
    prof = Profiler(2)
    prof.reset(2, 1)
    prof._start_blank()
    prof.tstreet, prof.inhand, prof.need = 3, 0b11, 0b11
    prof._consume([(1, Action.check()), (0, Action.raise_to(50))], 4)
    assert prof.rv_opp[0] == 1 and prof.rv_bet[0] == 1


def test_the_rbet_dials_reach_the_decisions():
    assert any(_digest(S, t, HU, R2)[0] != _digest({}, t, HU, R2)[0] for t in range(10))


@pytest.mark.parametrize("shut", [{"hero.postflop.rbet_from": 1.0}, {"hero.postflop.rbet_min": 10_000},
                                  {"hero.postflop.rbet_max_alive": 1}])
def test_a_shut_rbet_gate_plays_as_f(shut):
    d = {**S, **shut}
    assert all(_digest(d, t, HU, R2)[0] == _digest({}, t, HU, R2)[0] for t in range(3))


def test_rbet_max_alive_plays_heads_up_as_without_it():
    d = {**S, "hero.postflop.rbet_max_alive": 0}
    assert all(_digest(d, t, HU, R2)[0] == _digest(S, t, HU, R2)[0] for t in range(3))


def test_rbet_margin_reaches_the_decisions():
    d = {**S, "hero.postflop.rbet_margin": -1.0}  # the margin stays at call_margin: only the equity moves
    assert any(_digest(d, t, HU, R2)[0] != _digest(S, t, HU, R2)[0] for t in range(10))


def test_rbet_holdem_only_plays_a_twist_table_exactly_as_f():
    from hyperion.drills import variants as V

    for name in ("short_deck", "bounty"):
        rules = V.get(name).rules
        assert all(_digest(S, t, rules=rules)[0] == _digest({}, t, rules=rules)[0] for t in range(2)), name


def test_three_handed_with_the_rbet_read_replays_exactly():
    assert _digest(S, 1, THREE, R3)[0] == _digest(S, 1, THREE, R3)[0]
