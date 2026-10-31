"""tools/latency.py: the gate as a subprocess, and the helpers (stats, generator, native builders)."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

from hyperion.core.types import ActionKind
from hyperion.drills.adapter import KitBAdapter, KitCAdapter, KitDAdapter
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills.conformance import check_observation

ROOT = Path(__file__).resolve().parents[1]
LAT = ROOT / "tools" / "latency.py"
FIELDS = ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot", "to_call",
          "min_raise", "max_raise", "legal", "hand_no", "blinds")


def load_latency():
    spec = importlib.util.spec_from_file_location("latency_under_test", LAT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_latency(*args: str, env=None):
    return subprocess.run([sys.executable, str(LAT), *args], cwd=ROOT, capture_output=True, text=True,
                          timeout=300, env=env)


def test_cheap_bot_round_trip_through_kit_b_and_kit_c_passes():
    r = run_latency("--bot", "cheap", "--n", "300", "--warm", "20",
                    "--adapter", "hyperion.drills.adapter:KitBAdapter", "--native", "kit_b")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "bot.act" in r.stdout and "adapter.decide" in r.stdout and "OK p99" in r.stdout
    assert "gc gen0/1/2" in r.stdout and "timer floor" in r.stdout and "over 1 ms" in r.stdout
    r = run_latency("--bot", "cheap", "--n", "100", "--warm", "10",
                    "--adapter", "hyperion.drills.adapter:KitCAdapter", "--native", "kit_c")
    assert r.returncode == 0, r.stdout + r.stderr


def test_cheap_bot_round_trip_through_kit_d_passes():
    r = run_latency("--bot", "cheap", "--n", "100", "--warm", "10",
                    "--adapter", "hyperion.drills.adapter:KitDAdapter", "--native", "kit_d")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "adapter.decide" in r.stdout and "OK p99" in r.stdout


def test_slow_bot_fails_the_gate(tmp_path):
    (tmp_path / "slowmod.py").write_text(
        "from hyperion.drills.cheapbot import SlowBot\n\ndef make_bot():\n    return SlowBot(0.002)\n")
    env = dict(os.environ, PYTHONPATH=str(tmp_path))
    r = run_latency("--bot", "slowmod:make_bot", "--n", "30", "--warm", "2", env=env)
    assert r.returncode == 1 and "FAIL p99" in r.stdout, r.stdout + r.stderr


def test_stats():
    lat = load_latency()
    st = lat.stats([0.0001] * 98 + [0.002, 0.0005])
    assert st["n"] == 100 and st["over_1ms"] == 1 and st["max"] == 0.002 and st["p99"] == 0.002
    assert st["p50"] == 0.0001 and abs(st["mean"] - (98 * 0.0001 + 0.0025) / 100) < 1e-12


def test_generator_is_seat_fixed_and_conformant_and_builders_round_trip():
    lat = load_latency()
    obs = lat.observations(60, 7, 8, 0)
    assert len(obs) == 60 and all(o.seat == 0 for o in obs)
    assert all(check_observation(o) == [] for o in obs)
    b_adapter, c_adapter = KitBAdapter(CheapBot()), KitCAdapter(CheapBot())
    c_adapter.seat = 0
    build_b, build_c = lat.native_builder("kit_b"), lat.native_builder("kit_c")
    for o in obs:
        for back in (b_adapter.to_observation(build_b(o)), c_adapter.to_observation(build_c(o))):
            for f in FIELDS:
                if f in ("min_raise", "max_raise") and ActionKind.RAISE not in o.legal:
                    continue  # undefined when raising is not legal; kit C encodes none
                assert getattr(back, f) == getattr(o, f), (f, o, back)
    lat.measure(lambda x: None, obs)  # the timing loop runs on anything callable


def kit_d_legal(o) -> frozenset:
    """What kit D's legal_actions() offers for an Observation: no FoldAction when a check is free, and no
    RaiseAction into a hand where nobody left in it can call (the sim offers RAISE whenever any seat has chips)."""
    legal = set(o.legal)
    if ActionKind.CHECK in legal:
        legal.discard(ActionKind.FOLD)
    if o.to_call > 0 and not any(o.in_hand[s] and o.stacks[s] > 0 for s in range(o.n_players) if s != o.seat):
        legal.discard(ActionKind.RAISE)
    return frozenset(legal)


def test_kit_d_builder_round_trips_through_the_reference_adapter():
    """kit_d_native gives KitDAdapter a state whose every field comes back, the pot included (a lone
    RoundState has none; the builder hangs it off a round-start state). The legal set comes back as kit D
    derives it from the state (kit_d_legal), which differs from the sim's rule in two documented places."""
    lat = load_latency()
    obs = lat.observations(60, 7, 8, 0)
    assert any(o.pot > 0 for o in obs)
    adapter = KitDAdapter(CheapBot())
    build = lat.native_builder("kit_d")
    for o in obs:
        native = build(o)
        assert native[2] == o.seat and native[1].previous_state is not None and native[1].acting == o.seat
        back = adapter.to_observation(native)
        want_legal = kit_d_legal(o)
        for f in FIELDS:
            if f in ("min_raise", "max_raise") and ActionKind.RAISE not in want_legal:
                continue
            want = want_legal if f == "legal" else getattr(o, f)
            assert getattr(back, f) == want, (f, o, back)
        reply = adapter.decide(native)
        assert type(reply).__name__ in {c.__name__ for c in native[1].legal_actions()}, reply
