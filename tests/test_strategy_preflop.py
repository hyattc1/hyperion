import pytest

from snapcall.core.types import Action, ActionKind
from snapcall.strategy.preflop import Preflop, PreflopParams
from snapcall.strategy.profiler import Profiler
from snapcall.strategy.spot import Spot
from snapcall.strategy.tables import load

from .strategy_helpers import preflop_obs

R, C, F = Action.raise_to, Action.call(), Action.fold()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731


@pytest.fixture(scope="module")
def pf():
    return Preflop(PreflopParams(), load())


def decide(pf, obs, prof=None, cheap=False):
    return pf.act(Spot(obs, obs.hole), prof, cheap)


def test_aa_opens_utg_and_four_bets(pf):
    a = decide(pf, preflop_obs("Ah Ad", 2))
    assert a.kind is ActionKind.RAISE and a.amount == 50  # 2.5 bb at 10/20
    obs = preflop_obs("Ah Ad", 2, actions=[(2, R(50))] + FOLDS(3, 4) + [(5, R(160))] + FOLDS(6, 7, 0, 1))
    a = decide(pf, obs)
    assert a.kind is ActionKind.RAISE and a.amount >= 2 * 160


def test_72o_folds_early_and_opens_nothing_in_between(pf):
    assert decide(pf, preflop_obs("7h 2d", 2)) == F
    assert decide(pf, preflop_obs("7h 2d", 5)) == F
    assert decide(pf, preflop_obs("Jh 4d", 2)) == F


def test_position_widens_the_open(pf):
    # K9o: fold under the gun, open on the button when folded to
    assert decide(pf, preflop_obs("Kh 9d", 2)) == F
    a = decide(pf, preflop_obs("Kh 9d", 7, actions=FOLDS(2, 3, 4, 5, 6)))
    assert a.kind is ActionKind.RAISE
    # small blind completes with a medium hand, folds junk
    assert decide(pf, preflop_obs("8h 7s", 0, actions=FOLDS(2, 3, 4, 5, 6, 7))) in (C, F)
    assert decide(pf, preflop_obs("7h 2d", 0, actions=FOLDS(2, 3, 4, 5, 6, 7))) == F


def test_big_blind_checks_free_flop_and_raises_strong_over_limps(pf):
    limps = [(2, C)] + FOLDS(3, 4) + [(5, C)] + FOLDS(6, 7) + [(0, C)]
    assert decide(pf, preflop_obs("Jh 4d", 1, actions=limps)) == Action.check()
    a = decide(pf, preflop_obs("Ah Kd", 1, actions=limps))
    assert a.kind is ActionKind.RAISE and a.amount > 50  # bigger with limpers


def test_three_bet_call_and_fold_versus_an_open(pf):
    open_ = [(2, R(50))] + FOLDS(3, 4, 5, 6)
    assert decide(pf, preflop_obs("Qh Qd", 7, actions=open_)).kind is ActionKind.RAISE
    assert decide(pf, preflop_obs("2h 2d", 7, actions=open_)) == C  # set mine, 40x behind
    assert decide(pf, preflop_obs("9h 3d", 7, actions=open_)) == F
    assert decide(pf, preflop_obs("Ah Jd", 7, actions=open_)) == C


def test_short_stacks_do_not_flat(pf):
    st = [2000] * 8
    st[7] = 400  # 20 bb: above push/fold, below raise-or-fold depth
    open_ = [(2, R(50))] + FOLDS(3, 4, 5, 6)
    assert decide(pf, preflop_obs("Ah Jd", 7, stacks=st, actions=open_)) == C  # top 12% may still flat
    assert decide(pf, preflop_obs("Jh Td", 7, stacks=st, actions=open_)) == F


def test_facing_shove_uses_pot_odds_versus_equity(pf):
    st = [2000] * 8
    st[5] = 600
    shove = FOLDS(2, 3, 4) + [(5, R(600))] + FOLDS(6)
    assert decide(pf, preflop_obs("Ah Kd", 7, stacks=st, actions=shove)) == C
    assert decide(pf, preflop_obs("7h 2d", 7, stacks=st, actions=shove)) == F
    assert decide(pf, preflop_obs("Qh Jd", 7, stacks=st, actions=shove)) == F


def test_open_size_shrinks_as_blinds_grow(pf):
    a = decide(pf, preflop_obs("Ah Ad", 2, blinds=(100, 200)))
    assert a.amount == int(2.2 * 200)


def test_steal_dial_from_profiler_widens_button(pf):
    prof = Profiler(8)
    # blinds (seats 0 and 1) fold to everything: mark them dead
    for s in (0, 1):
        prof.pre_faced[s] = 10
        prof.pre_folded[s] = 10
        prof.actions[s] = 10
        prof.folds[s] = 10
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    obs = preflop_obs("Jh 7d", 7, actions=FOLDS(2, 3, 4, 5, 6))
    assert decide(pf, obs) == F
    assert decide(pf, obs, prof).kind is ActionKind.RAISE


def test_cheap_mode_is_tight_and_legal(pf):
    assert decide(pf, preflop_obs("Ah Kd", 2), cheap=True).kind is ActionKind.RAISE
    assert decide(pf, preflop_obs("Kh 9d", 7, actions=FOLDS(2, 3, 4, 5, 6)), cheap=True) == F
