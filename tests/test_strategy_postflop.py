import pytest

from hyperion.core.types import Action, ActionKind, parse_cards as P
from hyperion.strategy.postflop import Postflop, PostflopParams
from hyperion.strategy.profiler import Profiler
from hyperion.strategy.spot import Spot

from .strategy_helpers import street_obs

R, C, F, K = Action.raise_to, Action.call(), Action.fold(), Action.check()
HU = [False, True, False, False, False, False, False, True]  # seats 1 (BB) and 7 (button) in the hand
PRE = [(7, R(50)), (1, C)]


@pytest.mark.parametrize("hole,board,tier,outs", [
    ("Ah Kh", "Qh Jh 2c", 3, 12),  # flush draw + gutshot
    ("Ah Ad", "Kc 7d 2s", 4, 0),  # overpair
    ("Ac Kd", "Ks 7d 2s", 4, 0),  # top pair top kicker
    ("Kc 4d", "Ks 7d 2s", 3, 0),  # top pair weak kicker
    ("9c 9d", "Ks 7d 2s", 2, 0),  # underpair
    ("8c 7d", "9s 6d 2s", 3, 8),  # open-ender
    ("8c 7d", "9s 5d 2s", 1, 4),  # gutshot
    ("2c 3d", "Ks Kd Kh", 1, 0),  # board trips, nothing
    ("Ac Qd", "As Ad 2h 2c", 7, 0),  # full house
    ("5c 5d", "5s Kd 2h", 6, 0),  # set
    ("Jc Td", "9s 8d 7h", 6, 0),  # straight
    ("Ac 2d", "Kh Qh Jh Th 9h", 1, 0),  # playing the board
    ("Ac 9d", "Ad 9s 2h", 5, 0),  # two pair
    ("7c 2d", "As Kd Qh", 0, 0),  # air
    ("Ac Kd", "Qh 7h 2h 3h", 1, 3),  # four-flush board, we have none
])
def test_hand_reader(hole, board, tier, outs):
    t, o, _ = Postflop.read(P(hole), P(board))
    assert (t, o) == (tier, outs)


def test_texture_flags():
    assert Postflop.read(P("Ac 2d"), P("Ks 7d 2h"))[2] is False
    assert Postflop.read(P("Ac 2d"), P("9s 8d 7h"))[2] is True
    assert Postflop.read(P("Ac 2d"), P("Kh 7h 2h"))[2] is True


def decide(pp, obs, prof=None, aggressor=True, cheap=False):
    return pp.act(Spot(obs, obs.hole), obs.hole, prof, aggressor, cheap)


@pytest.fixture
def pp():
    return Postflop(PostflopParams(), seed=7)


def test_value_bets_and_raises(pp):
    obs = street_obs("5c 5d", "5s Kd 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    a = decide(pp, obs)
    assert a.kind is ActionKind.RAISE and 0.6 * 120 <= a.amount <= 120
    faced = street_obs("5c 5d", "5s Kd 2h", 7, pot=120, in_hand=HU, bets=[0, 100, 0, 0, 0, 0, 0, 0],
                       history=PRE + [(1, R(100))])
    a = decide(pp, faced)
    assert a.kind is ActionKind.RAISE and a.amount >= 300


def test_calls_by_pot_odds_and_folds_air(pp):
    bet = [0] * 8
    bet[7] = 60
    fd = street_obs("Ah 9h", "Kh 7h 2c", 1, pot=120, in_hand=HU, bets=bet, history=PRE + [(1, K), (7, R(60))])
    assert decide(pp, fd, aggressor=False) == C
    bet[7] = 120
    air = street_obs("7c 2d", "As Kd Qh", 1, pot=120, in_hand=HU, bets=bet, history=PRE + [(1, K), (7, R(120))])
    assert decide(pp, air, aggressor=False) == F
    gut = street_obs("8c 7d", "Ks 5d 2s", 1, pot=120, in_hand=HU, bets=bet, history=PRE + [(1, K), (7, R(120))])
    assert decide(pp, gut, aggressor=False) == F


def test_cbet_frequency_in_position_on_dry_board():
    pp = Postflop(PostflopParams(), seed=1)
    obs = street_obs("7c 6d", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    bets = sum(decide(pp, obs).kind is ActionKind.RAISE for _ in range(400))
    assert 180 <= bets <= 300  # ~60%
    oop = street_obs("7c 6d", "Ks 9d 2h", 1, pot=120, in_hand=HU, history=PRE)
    bets_oop = sum(decide(pp, oop).kind is ActionKind.RAISE for _ in range(400))
    assert bets_oop < bets
    multi = [False, True, False, True, False, False, False, True]
    mw = street_obs("7c 6d", "Ks 9d 2h", 7, pot=180, in_hand=multi, history=PRE + [(3, C), (1, K), (3, K)])
    bets_mw = sum(decide(pp, mw).kind is ActionKind.RAISE for _ in range(400))
    assert bets_mw < bets


def station_profiler(seat):
    prof = Profiler(8)
    prof.post_faced[seat] = 12
    prof.post_folded[seat] = 0
    prof.actions[seat] = 20
    prof.calls[seat] = 12
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    assert prof.station(seat)
    return prof


def test_versus_station_no_bluffs_wait_for_the_river_then_bet_big(pp):
    prof = station_profiler(1)
    air = street_obs("7c 6d", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    assert all(decide(pp, air, prof) == K for _ in range(50))
    tp = street_obs("Kc Qd", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    assert decide(pp, tp, prof) == K  # top pair waits
    river = street_obs("Kc Qd", "Ks 9d 2h 3c 4s", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    a = decide(pp, river, prof)
    assert a.kind is ActionKind.RAISE and a.amount >= 120


def test_versus_dead_seat_bet_anything(pp):
    prof = Profiler(8)
    prof.pre_faced[1] = 6
    prof.pre_folded[1] = 6
    prof.actions[1] = 6
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    air = street_obs("7c 2d", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    a = decide(pp, air, prof, aggressor=False)
    assert a.kind is ActionKind.RAISE and a.amount <= 0.4 * 120 + 1


def test_versus_folders_bets_small_and_often():
    prof = Profiler(8)
    prof.post_faced[1] = 20
    prof.post_folded[1] = 19
    prof.actions[1] = 30
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    pp = Postflop(PostflopParams(), seed=2)
    air = street_obs("7c 6d", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    bets = [decide(pp, air, prof) for _ in range(300)]
    n = sum(a.kind is ActionKind.RAISE for a in bets)
    assert n >= 240
    assert all(a.amount <= 60 for a in bets if a.kind is ActionKind.RAISE)


def test_calls_down_lighter_against_maniac(pp):
    prof = Profiler(8)
    prof.actions[7] = prof.raises[7] = 20
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    assert prof.maniac(7)
    bet = [0] * 8
    bet[7] = 120
    mid = street_obs("9c 8d", "Ks 9d 2h", 1, pot=120, in_hand=HU, bets=bet, history=PRE + [(1, K), (7, R(120))])
    assert decide(pp, mid, aggressor=False) == F
    assert decide(pp, mid, prof, aggressor=False) == C


def test_cheap_mode_only_value(pp):
    air = street_obs("7c 6d", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    assert decide(pp, air, cheap=True) == K
    two = street_obs("Kc 9c", "Ks 9d 2h", 7, pot=120, in_hand=HU, history=PRE + [(1, K)])
    assert decide(pp, two, cheap=True).kind is ActionKind.RAISE


def test_commits_rather_than_leaving_crumbs(pp):
    st = [2000] * 8
    st[7] = 150
    obs = street_obs("5c 5d", "5s Kd 2h", 7, stacks=st, pot=400, in_hand=HU, history=PRE + [(1, K)])
    a = decide(pp, obs)
    assert a == R(150)
