"""Red-team rival 5 (`rival5`, built blind by a fresh team) behind the bestiary adapter, and the two fields it judges
from: `judge2` (realistic-shaped, rival 5 in the holdout seat) and `judge2_night` (the night pool with rival 5 in one
seat). Rival 5 is the second judge: nobody tunes on it, and the compose agent measures the candidates on it once, at
the end. These tests check that it plays legally and in time and that the fields are wired, never how well anything
does; no number from a run here is read."""
import hashlib
from pathlib import Path
from time import perf_counter_ns

import pytest

from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from hyperion.sim.field import night as N
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Auditor

ROOT = Path(__file__).resolve().parents[1]
MD5 = "c0af68a4e0bd175fc6da59c386f8c3cb"


@pytest.fixture
def rival5_debug(monkeypatch):
    """Rival 5's act() swallows every exception into a legal action; unwrap it so one reaches the engine's counters."""
    from hyperion.sim.rivals import rival5

    monkeypatch.setattr(rival5.Bot, "act", lambda self, obs: self._act(obs))


def test_frozen_source_matches_its_archive_and_md5():
    raw = (ROOT / "docs/drills/redteam/rival5_bot.py").read_bytes()
    assert hashlib.md5(raw).hexdigest() == MD5
    lines = (ROOT / "hyperion/sim/rivals/rival5.py").read_bytes().splitlines(keepends=True)
    assert all(ln.startswith(b"#") for ln in lines[:6]) and MD5.encode() in b"".join(lines[:6])
    assert b"".join(lines[6:]) == raw


def test_rival5_plays_300_hands_in_measure_mode_with_zero_exceptions(rival5_debug):
    rules = Rules(max_hands=300, starting_stack=16000)  # deep enough that busts do not end it early
    hands = decisions = seed = 0
    while hands < 300:
        bots = [Auditor(B.make_bot("rival5", seed=seed * 8 + s), 8 * 16000) for s in range(8)]
        t = Table(bots, rules, seed=seed, mode="measure")
        while not t.done:
            t.play_hand()
            hands += 1
        for s in range(8):
            assert t.stats[s].exceptions == 0, t.stats[s].last_error
            assert t.stats[s].illegal == 0
        decisions += sum(len(b.decisions) for b in bots)
        seed += 1
    assert hands >= 300 and decisions > 300


def _host_overrun_rate(us: int = 30, n: int = 4000) -> float:
    over = 0
    for _ in range(n):
        t0 = perf_counter_ns()
        end = t0 + us * 1000
        while perf_counter_ns() < end:
            pass
        over += perf_counter_ns() - t0 > 1_000_000
    return over / n


def test_rival5_timeout_rate_in_strict_mode_is_under_one_percent_on_a_quiet_host():
    # Its postflop sampler stops at 130 us; its builder saw p99 over 1 ms only at load 53-57, where a 20 us control
    # loop spiked too. Over 1%, a fixed 30 us loop decides whose fault it is: skip if it overruns too.
    names = ["rival5", "tag", "pushfold", "loose_aggro", "nit", "station", "random", "rival1"]
    calls = over = 0
    for seed in range(6):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(names)]
        st = play_table(bots, Rules(), seed=seed, mode="strict").stats[0]
        assert st.exceptions == 0 and st.illegal == 0, st.last_error
        calls += st.calls + st.first_calls
        over += st.over_budget
    assert calls >= 300
    rate = over / calls
    if rate >= 0.01:
        host = _host_overrun_rate()
        if host >= 0.003:
            pytest.skip(f"host oversubscribed: rival5 {rate:.2%} over 1 ms, a fixed 30 us loop {host:.2%}")
    assert rate < 0.01, (over, calls)


def test_rival5_has_no_cost_model_so_mode_model_never_folds_it_and_step_us_makes_it_replay_exactly(monkeypatch):
    bot = B.make_bot("rival5", seed=1)
    assert not hasattr(bot, "use_cost_model") and getattr(bot, "last_cost_ns", None) is None
    names = ["rival5", "tag", "pushfold", "loose_aggro", "nit", "station", "maniac", "montecarlo"]

    def once():
        r = play_table([B.make_bot(n, seed=s) for s, n in enumerate(names)], Rules(), seed=3, mode="model")
        return r.points, r.hands, r.stacks, r.stats[0].over_budget

    monkeypatch.setattr(B.Rival5Bot, "STEP_US", 4.0)
    a = once()
    assert a == once() and a[3] == 0  # a fixed-speed sampler replays exactly; never folded for time
    from hyperion.sim.rivals import rival5

    monkeypatch.setattr(B.Rival5Bot, "STEP_US", None)
    once()
    assert rival5.time is __import__("time")  # as built, it reads the real clock


def test_adapter_passes_the_hand_cap_and_payouts():
    bot = B.make_bot("rival5", seed=1)
    bot.new_table(Rules(max_hands=150), 2, 8)
    assert bot.impl.hand_cap == 150
    assert bot.kit_rules(Rules(), 8)["payouts"] == list(Rules().payouts)


def test_judge2_fields_have_the_agreed_seats_and_swaps():
    assert B.field_names("judge2") == ["rival5" if m == "rival4" else m for m in B.FIELDS["judge"]]
    jn = B.field_names("judge2_night")
    assert jn == ["hero", "rival5"] + [f"judge2_night.{k}" for k in range(1, 7)]
    for t in range(200):  # six distinct pool bots around rival 5, never a judge
        d = N.draw("judge2_night", t)
        assert len(set(d)) == 6 and not {"rival4", "rival5"} & set(d)
    for field in ("judge2", "judge2_night"):
        for cand in B.JUDGE_CANDIDATES:
            assert B.field_names(f"{field}@{cand}") == [cand] + B.field_names(field)[1:]
            assert f"{field}@{cand}" in B.FIELDS
    for name, members in B.FIELDS.items():
        if not name.startswith("judge2"):
            assert "rival5" not in members, name  # no other field seats the judge
    for pool in N.POOLS.values():
        assert "rival5" not in {b for _, _, ms in pool.groups for b, _ in ms}


@pytest.mark.parametrize("field", ["judge2", "judge2_night"])
def test_judge2_field_smoke_runs_in_model_mode(field):
    # conservation and legality only; a cheap bot in Hero's seat; no number from it is read
    members = B.field_names(f"{field}@nit")
    rep = run_tournament(members, tables=4, seed=1, mode="model")
    assert set(rep.bots) == set(members)
    for name, b in rep.bots.items():
        assert b.stats.illegal == 0, name
        if name == "rival5":
            assert b.stats.exceptions == 0 and b.stats.over_budget == 0, b.stats.last_error
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 4 - sum(Rules().payouts)) < 1e-6
