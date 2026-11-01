"""The deterministic timeout model (engine mode "model"): bots that report a modelled cost are folded by it, nothing is
folded by the wall clock, and a table replays exactly."""
import time

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.sim import bestiary
from hyperion.sim.bestiary import (CallingStation, MonteCarloBot, MonteCarloTimeout30, TimeoutBot, TimeoutBurst,
                                   TimeoutThenRecover, make_bot)
from hyperion.sim.engine import BUDGET_NS, Table
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Recorder

FOLD, CHECK = ActionKind.FOLD, ActionKind.CHECK


def collect(bots, rules, **kw):
    t = Table(bots, rules, **kw)
    hist = []
    while not t.done:
        hist.extend(t.play_hand().history)
    return t.result(), hist


class Sleeper(Recorder):
    """A slow calling station with no cost model: the model never folds it."""

    def act(self, obs):
        time.sleep(0.0015)
        super().act(obs)
        return Action.call() if obs.to_call > 0 else Action.check()


def test_model_mode_folds_a_modelled_timeout_without_sleeping():
    bots = [TimeoutBot(sleep_s=0.05)] + [CallingStation() for _ in range(7)]
    t0 = time.perf_counter()
    res, hist = collect(bots, Rules(max_hands=10), seed=1, mode="model")
    assert time.perf_counter() - t0 < 0.4  # 10 hands of 50 ms sleeps would take far longer
    mine = [a for s, a in hist if s == 0]
    assert mine and res.stats[0].over_budget == len(mine)
    assert all(a.kind in (FOLD, CHECK) for a in mine)


def test_model_mode_never_folds_an_unmodelled_bot_for_time():
    bots = [Sleeper()] + [CallingStation() for _ in range(7)]
    res, hist = collect(bots, Rules(max_hands=4), seed=1, mode="model")
    st = res.stats[0]
    assert st.over_budget == 0 and st.max_ns > BUDGET_NS  # it was slow, and it was let through
    assert any(a.kind is ActionKind.CALL for s, a in hist if s == 0)


def test_strict_mode_leaves_the_bots_sleeping():
    bot = TimeoutBot(sleep_s=0.002)
    Table([bot] + [CallingStation() for _ in range(7)], Rules(max_hands=1), mode="model")
    assert bot.cost_model
    Table([bot] + [CallingStation() for _ in range(7)], Rules(max_hands=1), mode="strict")
    assert not bot.cost_model  # the engine switches it back: strict mode is unchanged


def test_honest_monte_carlo_costs_a_millisecond_heads_up_and_more_multiway():
    mc = MonteCarloBot()
    hu, three, eight = (mc.model_cost_ns(200, k, False) for k in (1, 2, 7))
    assert 0.95 * BUDGET_NS <= hu <= 1.05 * BUDGET_NS
    assert three > 1.05 * BUDGET_NS and eight > 1.5 * BUDGET_NS
    assert mc.model_cost_ns(30, 7, True) < 0.3 * BUDGET_NS  # montecarlo30's fast rollouts always land


def test_montecarlo30_times_out_on_its_draws_only():
    names = ["montecarlo30"] + ["station"] * 7
    rep = run_tournament(names, 3, seed=5, rotate=False, mode="model")
    st = rep.bots["montecarlo30"].stats
    assert 0 < st.over_budget < st.calls + st.first_calls


def test_timeout_burst_recovers_between_outages():
    b = TimeoutBurst(seed=3)
    b.new_table(Rules(), 0, 8)
    lo, hi = b._windows[0]
    assert lo == b.fail_from and 10 <= hi - lo <= 30
    assert not b.failing(lo - 1) and b.failing(lo) and b.failing(hi - 1) and not b.failing(hi)
    lo2, _ = b._windows[1]
    assert 20 <= lo2 - hi <= 50 and b.failing(lo2)
    ttr = TimeoutThenRecover(seed=3)
    ttr.new_table(Rules(), 0, 8)
    assert ttr.failing(ttr.fail_from) and ttr.failing(10_000)


def test_model_mode_replays_a_table_exactly():
    # duplicate deals and seeded bots: the same seeds give the same points and the same timeouts, whatever the host
    names = bestiary.field_names("timeouts")
    a = run_tournament(names, 2, seed=11, rotate=False, mode="model")
    b = run_tournament(names, 2, seed=11, rotate=False, mode="model")
    for nm in names:
        assert a.bots[nm].samples == b.bots[nm].samples
        assert a.bots[nm].stats.over_budget == b.bots[nm].stats.over_budget


def test_timeouts_field_seats_four_timeout_prone_bots():
    names = bestiary.field_names("timeouts")
    assert len(names) == 8 and names[0] == "hero"
    prone = [nm for nm in names if isinstance(make_bot(nm), (MonteCarloBot, TimeoutThenRecover))]
    assert len(prone) == 4 and any(isinstance(make_bot(nm), MonteCarloTimeout30) for nm in prone)
