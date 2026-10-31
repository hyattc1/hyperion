import sys
from pathlib import Path

import pytest

from snapcall.core.types import Action, ActionKind
from snapcall.drills.adapter import KitAAdapter, KitBAdapter, KitCAdapter
from snapcall.drills.cheapbot import CheapBot
from snapcall.drills.fakekits.kit_a import kit as kit_a, runner as run_a
from snapcall.drills.fakekits.kit_b import kit as kit_b, runner as run_b
from snapcall.drills.fakekits.kit_c import runner as run_c

REF = Path(__file__).resolve().parents[1] / "snapcall" / "drills" / "reference"


@pytest.fixture(autouse=True)
def cheap_bot(monkeypatch):
    monkeypatch.setenv("SNAPCALL_DRILL_BOT", "cheap")  # these tests measure adapters, not hero


def run_kit(kit: str, submission: str, hands: int = 30, hole_cards: int = 2):
    path = str(REF / submission)
    if kit == "a":
        return run_a.run(run_a.load_agent_class(path), hands=hands, seed=3, hole_cards=hole_cards)
    if kit == "b":
        return run_b.run(run_b.load_module(path), hands=hands, seed=3, hole_cards=hole_cards)
    return run_c.run([sys.executable, path], hands=hands, seed=3, hole_cards=hole_cards)


@pytest.mark.parametrize("kit", ["a", "b", "c"])
def test_reference_adapter_passes_runner(kit):
    r = run_kit(kit, f"kit_{kit}_submission.py")
    assert r.passed, r.summary() + " " + "; ".join(r.notes)
    assert r.hands == 30 and r.decisions > 30
    assert r.exceptions == 0 and r.illegal == 0


@pytest.mark.parametrize("kit", ["a", "b", "c"])
def test_slow_adapter_is_auto_folded(kit):
    r = run_kit(kit, f"slow_kit_{kit}.py", hands=8)
    assert not r.passed
    assert r.timeouts > 0 and r.exceptions == 0 and r.illegal == 0
    assert r.hands == 8  # the runner survives a slow bot and finishes the hands


@pytest.mark.parametrize("kit", ["a", "b"])
def test_three_hole_cards_through_kits(kit):
    r = run_kit(kit, f"kit_{kit}_submission.py", hands=10, hole_cards=3)
    assert r.passed, r.summary()


def test_kit_a_adapter_translates_state():
    st = {
        "hole": (48, 33), "board": (), "street": 0, "seat": 1, "button": 3,
        "stacks": [1980, 1960, 2000, 2000], "bets": [10, 20, 0, 0], "in_hand": [True, True, True, True],
        "pot": 0, "to_call": 0, "min_raise": 40, "max_raise": 1980, "legal": {"fold", "check", "raise"},
        "hand_no": 4, "blinds": (10, 20), "history": [],
    }
    state = kit_a.to_state(st)
    assert state.hand == ["Ac", "10d"] and state.pot_size == 30 and state.legal_moves == ["FOLD", "CHECK", "RAISE"]
    obs = KitAAdapter(CheapBot()).to_observation(state)
    assert obs.hole == (48, 33) and obs.pot == 0 and obs.to_call == 0 and obs.seat == 1 and obs.button == 3
    assert obs.legal == frozenset({ActionKind.FOLD, ActionKind.CHECK, ActionKind.RAISE})
    assert KitAAdapter(CheapBot()).from_action(Action.raise_to(60), obs, state) == "RAISE:60"
    assert kit_a.parse_action("RAISE:60") == ("raise", 60)
    with pytest.raises(ValueError):
        kit_a.parse_action("RAISE: 60")


def test_kit_b_adapter_uses_increments():
    st = {
        "hole": (48, 33), "board": (0, 5, 10), "street": 1, "seat": 0, "button": 1,
        "stacks": [1900, 1900], "bets": [0, 100], "in_hand": [True, True],
        "pot": 200, "to_call": 100, "min_raise": 200, "max_raise": 1900, "legal": {"fold", "call", "raise"},
        "hand_no": 4, "blinds": (10, 20), "history": [],
    }
    o = kit_b.to_observation(st)
    assert o["street"] == 3 and o["you"]["min_raise_by"] == 100 and o["you"]["max_raise_by"] == 1800
    assert o["hand"]["cards"][0] == {"rank": 14, "suit": "C"}
    obs = KitBAdapter(CheapBot()).to_observation(o)
    assert obs.street == 1 and obs.min_raise == 200 and obs.max_raise == 1900 and obs.to_call == 100
    d = KitBAdapter(CheapBot()).from_action(Action.raise_to(300), obs, o)
    assert d == {"action": "raise", "by": 200}
    assert kit_b.parse_decision(d, st) == ("raise", 300)


def test_kit_c_adapter_parses_lines_and_only_answers_L_lines(capsys):
    ad = KitCAdapter(CheapBot())
    import io

    inp = io.StringIO("T4 P2 Z2000 V10/20\nH1 D0 S0 KAs,Ad B- C2000,1990,1980,2000 E0,10,20,0 I1111 O0 "
                      "LF,C,R40-2000 V10/20 T90.0\nX1 W20\nQ\n")
    out = io.StringIO()
    ad.serve(inp, out)
    lines = out.getvalue().split("\n")
    assert lines[0] == "OK" and lines[1].startswith("R") and lines[2] == "" and len(lines) == 3
    obs = ad.to_observation("H1 D0 S1 KAs,Ad BKh,7d,2c C2000,1990,1980,2000 E0,0,0,0 I1011 O60 LF,K,R20-2000 V10/20 T9")
    assert obs.seat == 2 and obs.pot == 60 and obs.to_call == 0 and obs.in_hand == [True, False, True, True]
    assert obs.min_raise == 20 and obs.max_raise == 2000 and ActionKind.CALL not in obs.legal
