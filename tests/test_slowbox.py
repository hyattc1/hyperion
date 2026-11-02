"""tools/slowbox.py: the dilated clock reaches every import-time binding, a slow box trips SafeBot and the engine's
1 ms check, the seat is strict while the room plays model mode, and a --det run pairs with tools/swap.py's model mode."""
import importlib.util
import os
import sys
import time

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SB = _load("slowbox")


@pytest.fixture(autouse=True)
def _real_clock():
    SB.uninstall()
    yield
    SB.uninstall()


def _busy(us: float) -> None:
    """Spin for `us` of wall time (the wall-clock test)."""
    end = SB.real_ns() + int(us * 1000)
    while SB.real_ns() < end:
        pass


def _spin(us: float) -> None:
    """Spin for `us` of this thread's CPU time (what --clock cpu counts, however busy the host is)."""
    end = time.thread_time_ns() + int(us * 1000)
    while time.thread_time_ns() < end:
        pass


def test_install_dilates_every_binding_and_uninstall_restores():
    from hyperion.sim import engine
    from hyperion.strategy import safe

    real_pc, real_ns = time.perf_counter, time.perf_counter_ns
    SB.install(3.0, "wall")
    assert safe.perf_counter is time.perf_counter is not real_pc  # `from time import perf_counter`, bound at import
    assert engine.perf_counter_ns is time.perf_counter_ns is not real_ns
    t0 = engine.perf_counter_ns()
    p0 = safe.perf_counter()
    _busy(3000)
    dt_ns = engine.perf_counter_ns() - t0
    dt_s = safe.perf_counter() - p0
    assert 8.9e6 < dt_ns < 20e6  # 3 ms real reads as 9 ms (more only if this host preempted us)
    assert 8.9e-3 < dt_s < 20e-3
    SB.install(2.0, "wall")  # a second install continues from the dilated reading: no jump back
    assert engine.perf_counter_ns() >= t0 + dt_ns
    SB.uninstall()
    assert safe.perf_counter is real_pc and engine.perf_counter_ns is real_ns and time.perf_counter is real_pc


def test_cpu_clock_counts_work_not_sleep():
    SB.install(2.0, "cpu")
    t0 = time.perf_counter_ns()
    time.sleep(0.03)
    slept = time.perf_counter_ns() - t0
    t1 = time.perf_counter_ns()
    _spin(3000)
    worked = time.perf_counter_ns() - t1
    assert slept < 3e6  # 30 ms asleep is (nearly) no CPU time
    assert 6e6 <= worked < 7e6  # 3 ms of CPU reads as 6 ms


def test_virtual_noise_adds_pauses():
    SB.install(1.0, "cpu", noise=(2000.0, 300.0))  # 2000 pauses a second of mean 300 us
    SB.reseed_noise(1)
    t0 = time.perf_counter_ns()
    c0 = time.thread_time_ns()
    while time.thread_time_ns() - c0 < 50e6:
        time.perf_counter_ns()
    extra = (time.perf_counter_ns() - t0) - (time.thread_time_ns() - c0)
    assert SB._NOISE["pauses"] > 20
    assert extra > 5e6  # ~100 pauses x 0.3 ms


class _Slow:
    """Busy-waits `us` real microseconds per decision, then checks or folds."""

    def __init__(self, us):
        self.us = us

    def new_table(self, rules, seat, n):
        pass

    def act(self, obs):
        from hyperion.strategy.safe import safe_action

        _spin(self.us)
        return safe_action(obs)

    def hand_end(self, result):
        pass


def test_safebot_panics_on_a_slow_box_only():
    from hyperion.core.types import Rules
    from hyperion.sim.engine import BotStats, play_table
    from hyperion.sim.bestiary import make_bot
    from hyperion.strategy.safe import SafeBot

    def run(k):
        SB.install(k, "cpu")
        bot = SafeBot(_Slow(200))  # 200 us here: 600 us on a 3x box, over the 0.5 ms soft deadline
        seat = SB.SlowSeat(bot)
        bots = [seat] + [make_bot("tag", seed=i) for i in range(1, 6)]
        st = [BotStats(str(i)) for i in range(6)]
        res = play_table(bots, Rules(n_players=6, max_hands=12), seed=3, mode="model", stats=st)
        SB.uninstall()
        return bot, st[0], res

    bot1, st1, _ = run(1.0)
    assert not bot1.panic_mode and st1.over_budget <= 1  # (one host hiccup over 1 ms is possible on a busy host)
    bot3, st3, _ = run(3.0)
    assert bot3.panic_mode and bot3.overruns >= 5
    assert st3.over_budget == 0  # 600 us is late for SafeBot, not for the engine


def test_seat_is_strict_while_the_room_plays_model_mode():
    from hyperion.core.types import Rules
    from hyperion.sim.engine import BotStats, play_table
    from hyperion.sim.bestiary import make_bot

    SB.install(3.0, "cpu")
    seat = SB.SlowSeat(_Slow(400))  # 1.2 ms on a 3x box: every decision times out
    bots = [seat] + [make_bot("tag", seed=i) for i in range(1, 6)]
    st = [BotStats(str(i)) for i in range(6)]
    play_table(bots, Rules(n_players=6, max_hands=8), seed=5, mode="model", stats=st)
    assert st[0].calls > 0 and st[0].over_budget == st[0].calls + st[0].first_calls  # (calls excludes the first)
    assert all(s.over_budget == 0 for s in st[1:])


def test_det_run_pairs_with_swap_model_mode():
    from hyperion.core.types import Rules

    rec, st, _, _ = SB.play("hybrid3_x", "night", 10000, 3, Rules(), det=True)
    sw = _load("swap")
    sw.setup_process("model")
    try:
        pts, _, _ = sw.play("night", "hybrid3_x", 10000, 3)
    finally:
        from hyperion.sim import bestiary as B

        B.HYBRID_CONFIG = None
        B.HERO_CONFIG = None
    assert rec["pts"] == pts
    ts, seats, me = SB.seating("night", 10000)
    ts2, seats2 = sw.seating("night@hybrid3_x", 10000)
    assert ts == ts2 and seats2[me] == "hybrid3_x"
    assert [x for i, x in enumerate(seats) if i != me] == [x for i, x in enumerate(seats2) if i != me]


def test_safebot_replay_rule():
    us = [100_000] * 10 + [300_000] * 6  # 6 calls of 300 us: over 0.5 ms at k = 2, the panic on the 5th
    assert SB.safebot_replay(us, 1.0) == (0, 0, -1)
    over, tmo, call = SB.safebot_replay(us, 2.0)
    assert over == 6 and tmo == 0 and call == 15
    over, tmo, call = SB.safebot_replay(us, 4.0)
    assert over == 6 and tmo == 6
