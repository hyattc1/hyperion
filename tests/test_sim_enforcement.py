import time

import pytest

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.sim.bestiary import CallingStation, Crasher, TimeoutBot
from hyperion.sim.engine import BUDGET_NS, BotStats, Table, play_table
from tests.sim_helpers import Recorder

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


def collect(bots, rules, **kw):
    """Play a table hand by hand and return (result, all history entries)."""
    t = Table(bots, rules, **kw)
    hist = []
    while not t.done:
        hs = t.play_hand()
        hist.extend(hs.history)
    return t.result(), hist


def test_exceptions_fold_or_check_and_are_counted():
    bots = [Crasher()] + [CallingStation() for _ in range(7)]
    res, hist = collect(bots, Rules(max_hands=40), seed=1)
    st = res.stats[0]
    decisions = [a for s, a in hist if s == 0]
    assert decisions and st.exceptions == len(decisions)
    assert all(a.kind in (FOLD, CHECK) for a in decisions)
    assert st.illegal == 0
    assert "Crasher" in st.last_error
    assert res.hands == 40 or not res.survived[0]


def test_strict_mode_turns_slow_decisions_into_checks_or_folds():
    bots = [TimeoutBot(sleep_s=0.002)] + [CallingStation() for _ in range(7)]
    res, hist = collect(bots, Rules(max_hands=10), seed=1, mode="strict")
    st = res.stats[0]
    mine = [a for s, a in hist if s == 0]
    assert mine and st.over_budget == len(mine) + 0  # every call was slow
    assert all(a.kind in (FOLD, CHECK) for a in mine)
    assert st.exceptions == 0
    assert st.percentile_us(0.5) >= 1000 or st.first_max_ns >= BUDGET_NS


def test_measure_mode_records_but_lets_the_action_through():
    bots = [TimeoutBot(sleep_s=0.002)] + [CallingStation() for _ in range(7)]
    res, hist = collect(bots, Rules(max_hands=10), seed=1, mode="measure")
    st = res.stats[0]
    mine = [a for s, a in hist if s == 0]
    assert any(a.kind is RAISE for a in mine)
    assert st.over_budget == len(mine)


def test_illegal_actions_are_clamped_and_counted():
    class Overbet:
        def new_table(self, rules, seat, n):
            pass

        def act(self, obs):
            return Action.raise_to(10 ** 9)

        def hand_end(self, result):
            pass

    class WrongKind:
        def new_table(self, rules, seat, n):
            pass

        def act(self, obs):
            return Action.check()  # illegal when facing a bet

        def hand_end(self, result):
            pass

    class Garbage:
        def new_table(self, rules, seat, n):
            pass

        def act(self, obs):
            return "fold"

        def hand_end(self, result):
            pass

    bots = [Overbet(), WrongKind(), Garbage()] + [CallingStation() for _ in range(5)]
    res, hist = collect(bots, Rules(max_hands=5), seed=2)
    over = [a for s, a in hist if s == 0]
    assert over and all(a.kind is RAISE or a.kind is CALL for a in over)
    assert res.stats[0].illegal == len(over)
    wrong = [a for s, a in hist if s == 1]
    assert all(a.kind in (CHECK, CALL) for a in wrong)
    assert res.stats[1].illegal == sum(1 for a in wrong if a.kind is CALL)
    garbage = [a for s, a in hist if s == 2]
    assert garbage and all(a.kind in (CHECK, FOLD) for a in garbage)
    assert res.stats[2].illegal == len(garbage)
    assert sum(res.stacks) == 16000


def test_float_raise_amount_is_coerced_and_counted():
    class FloatRaiser:
        def new_table(self, rules, seat, n):
            pass

        def act(self, obs):
            return Action(ActionKind.RAISE, float(obs.max_raise)) if RAISE in obs.legal else Action.call()

        def hand_end(self, result):
            pass

    bots = [FloatRaiser()] + [CallingStation() for _ in range(7)]
    res, hist = collect(bots, Rules(max_hands=3), seed=2)
    assert all(type(a.amount) is int for _, a in hist)
    assert all(type(s) is int for s in res.stacks)
    assert res.stats[0].illegal > 0


def test_exceptions_in_new_table_and_hand_end_are_recorded_not_fatal():
    class Fragile(Recorder):
        def new_table(self, rules, seat, n):
            raise ValueError("boom at setup")

        def hand_end(self, result):
            raise ValueError("boom at hand end")

    bots = [Fragile()] + [CallingStation() for _ in range(7)]
    res = play_table(bots, Rules(max_hands=4), seed=1)
    assert res.hands == 4
    assert res.stats[0].exceptions == 1 + 4


def test_first_call_is_reported_separately_and_stats_merge():
    bots = [Recorder() for _ in range(8)]
    stats = [BotStats(f"r{i}") for i in range(8)]
    play_table(bots, Rules(max_hands=20), seed=1, stats=stats)
    for s, st in enumerate(stats):
        decisions = len(bots[s].obs)
        assert st.first_calls == (1 if decisions else 0)
        assert st.calls == max(0, decisions - 1)
    play_table([Recorder() for _ in range(8)], Rules(max_hands=20), seed=2, stats=stats)
    assert all(st.first_calls == 2 for st in stats if st.calls)
    merged = BotStats("all")
    for st in stats:
        merged.merge(st)
    assert merged.calls == sum(st.calls for st in stats)
    assert merged.first_calls == sum(st.first_calls for st in stats)
    assert 0 <= merged.percentile_us(0.5) <= merged.percentile_us(0.99) <= max(merged.max_ns / 1000, 1)


@pytest.mark.timing
def test_latency_percentiles_track_a_known_sleep():
    class Sleepy(Recorder):
        def act(self, obs):
            time.sleep(0.0003)
            return super().act(obs)

    bots = [Sleepy()] + [CallingStation() for _ in range(7)]
    res = play_table(bots, Rules(max_hands=20), seed=1, mode="measure")
    st = res.stats[0]
    assert st.calls > 5
    assert 250 <= st.percentile_us(0.5) <= 2000
    assert st.mean_us >= 250
