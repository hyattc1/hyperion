import pytest

from hyperion.core.types import Action, ActionKind
from hyperion.strategy import pushfold as PF
from hyperion.strategy.profiler import Profiler
from hyperion.strategy.spot import Spot
from hyperion.strategy.tables import CLASS_INDEX, load

from .strategy_helpers import preflop_obs

R, C, F = Action.raise_to, Action.call(), Action.fold()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731


@pytest.fixture(scope="module")
def tables():
    return load(need_hu=True)


@pytest.fixture(scope="module")
def engine(tables):
    return PF.PushFold(PF.PushFoldParams(), tables)


def decide(engine, obs, prof=None, cheap=False):
    return engine.act(Spot(obs, obs.hole), prof, cheap)


def test_solver_reproduces_heads_up_nash_shape(engine):
    # HoldemResources edges: K2o pushes to ~11.6 bb, 72o only to 1.6, calls are any-two at 2 bb
    assert engine.push_set[2][CLASS_INDEX["72o"]] == 0 or engine.p_push[2] > 0.85
    assert engine.push_set[10][CLASS_INDEX["K2o"]] == 1
    assert engine.push_set[20][CLASS_INDEX["K2o"]] == 0
    assert engine.push_set[20][CLASS_INDEX["22"]] == 1
    assert engine.call_set[2][CLASS_INDEX["72o"]] == 1
    assert engine.call_set[15][CLASS_INDEX["72o"]] == 0
    assert 0.5 < engine.p_push[10] < 0.65 and 0.3 < engine.p_call[10] < 0.45
    assert engine.p_push[5] > engine.p_push[15] > engine.p_push[25]
    assert engine.p_call[5] > engine.p_call[15] > engine.p_call[25]


def test_solver_small_grid_runs_from_matrix(tables):
    sol = PF.solve_hu_pushfold(tables.hu, depths=(3, 12), iters=10)
    assert set(sol["push"]) == {"3", "12"} and len(sol["eq_vs_call"]["12"]) == 169
    assert sol["p_push"]["3"] > sol["p_push"]["12"]
    assert 0.4 < sol["eq_vs_call"]["12"][CLASS_INDEX["AA"]] <= 1.0


def test_six_bb_button_shoves_a9o_folds_83o(engine):
    st = [2000] * 8
    st[7] = 120
    folded = FOLDS(2, 3, 4, 5, 6)
    a = decide(engine, preflop_obs("Ah 9d", 7, stacks=st, actions=folded))
    assert a.kind is ActionKind.RAISE and a.amount == 120
    assert decide(engine, preflop_obs("8h 3d", 7, stacks=st, actions=folded)) == F


def test_multiway_rule_tightens_early_position(engine):
    st = [200] * 8  # everyone 10 bb
    # K9o: a heads-up push at 10 bb, a fold under the gun eight-handed, a push on the button
    assert engine.push_set[10][CLASS_INDEX["K9o"]] == 1
    assert decide(engine, preflop_obs("Kh 9d", 2, stacks=st)) == F
    assert decide(engine, preflop_obs("Kh 9d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))).kind is ActionKind.RAISE
    assert decide(engine, preflop_obs("Ah Ad", 2, stacks=st)).kind is ActionKind.RAISE


def test_dead_seats_get_shoved_into_with_anything(engine):
    prof = Profiler(8)
    for s in (0, 1):
        prof.pre_faced[s] = 6
        prof.pre_folded[s] = 6
        prof.actions[s] = 6
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    assert prof.dead_seat(0) and prof.dead_seat(1)
    st = [2000] * 8
    st[7] = 160
    obs = preflop_obs("7h 2d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))
    assert decide(engine, obs) == F
    a = decide(engine, obs, prof)
    assert a.kind is ActionKind.RAISE and a.amount == obs.max_raise


def test_call_shove_by_range_and_equity(engine):
    st = [2000] * 8
    st[5] = 160
    shove = FOLDS(2, 3, 4) + [(5, R(160))] + FOLDS(6, 7, 0)
    assert decide(engine, preflop_obs("Ah Kd", 1, stacks=st, actions=shove)) == C
    assert decide(engine, preflop_obs("7h 2d", 1, stacks=st, actions=shove)) == F
    # a shover known to shove constantly gets called wider
    prof = Profiler(8)
    prof.shoves[5] = prof.shove_opps[5] = prof.actions[5] = prof.raises[5] = 12
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    wide = preflop_obs("Kh 8d", 1, stacks=st, actions=shove)
    assert decide(engine, wide, prof) == C


def test_reshove_over_a_raise_when_short(engine):
    st = [2000] * 8
    st[1] = 200  # hero 10 bb in the big blind
    open_ = [(2, R(50))] + FOLDS(3, 4, 5, 6, 7, 0)
    a = decide(engine, preflop_obs("Ah Qd", 1, stacks=st, actions=open_))
    assert a.kind is ActionKind.RAISE and a.amount == 200
    assert decide(engine, preflop_obs("7h 2d", 1, stacks=st, actions=open_)) == F


class FlatCurve:
    """ICM so punishing that gaining chips is worth nothing and losing them costs everything."""

    def __init__(self, now):
        self.now = now

    def value(self, x):
        return 1.0 if x >= self.now else 0.0


def test_icm_gate_can_turn_a_marginal_push_into_a_fold(tables):
    eng = PF.PushFold(PF.PushFoldParams(), tables)
    st = [2000] * 8
    st[7] = 200
    obs = preflop_obs("Kh 9d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))
    assert decide(eng, obs).kind is ActionKind.RAISE
    eng.curve = FlatCurve(obs.stacks[7])
    assert decide(eng, obs) == F
    # premium hands still go in: the gate is EV, not fear
    eng.curve = PF._Linear()
    assert decide(eng, preflop_obs("Ah Ad", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))).kind is ActionKind.RAISE


def test_threshold_is_configurable(tables):
    tight = PF.PushFold(PF.PushFoldParams(threshold_bb=5), tables)
    st = [2000] * 8
    st[7] = 200
    obs = preflop_obs("Ah 9d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))
    assert not tight.applies(Spot(obs, obs.hole))
    assert PF.PushFold(PF.PushFoldParams(), tables).applies(Spot(obs, obs.hole))
