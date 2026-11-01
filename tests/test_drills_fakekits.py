import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind
from hyperion.drills.adapter import KitAAdapter, KitBAdapter, KitCAdapter
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills.fakekits.kit_a import kit as kit_a, runner as run_a
from hyperion.drills.fakekits.kit_b import kit as kit_b, runner as run_b
from hyperion.drills.fakekits.kit_c import runner as run_c

REF = Path(__file__).resolve().parents[1] / "hyperion" / "drills" / "reference"


@pytest.fixture(autouse=True)
def cheap_bot(monkeypatch):
    monkeypatch.setenv("HYPERION_DRILL_BOT", "cheap")  # these tests measure adapters, not hero


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


# ----- kit A toss mode (toss-or-hold'em: 3 hole cards, one face-up discard after the flop) -----

class _TossAgent(kit_a.Agent):
    """Discards the first card, then checks or folds; records what it saw."""

    def __init__(self):
        self.seen = []

    def act(self, state):
        self.seen.append((state.street, len(state.hand), list(state.legal_moves), dict(state.discards),
                          list(state.action_log)))
        if state.legal_moves == ["DISCARD"]:
            return "DISCARD:0"
        return "CHECK" if "CHECK" in state.legal_moves else "FOLD"


def test_kit_a_toss_asks_one_discard_per_flop_and_shows_it():
    agents = []

    class Rec(_TossAgent):
        def __init__(self):
            super().__init__()
            agents.append(self)

    r = run_a.run(Rec, hands=60, seed=5, toss=True)
    assert r.passed and r.illegal == 0 and r.exceptions == 0, r.summary()
    seen = agents[0].seen
    asks = [s for s in seen if s[2] == ["DISCARD"]]
    assert asks and all(st == "flop" and n == 3 for st, n, *_ in asks)
    assert all(n == 3 for st, n, *_ in seen if st == "preflop")
    after = [s for s in seen if s[0] != "preflop" and s[2] != ["DISCARD"]]
    assert after and all(n == 2 for _, n, *_ in after)  # two cards once the toss is done
    assert any(0 in d for *_, d, _ in after)  # our tossed card is public
    assert any(any(a.startswith("DISCARD:") for _, a in log) for *_, log in after)


def test_kit_a_toss_counts_a_non_discard_answer_as_illegal_and_tosses_for_you():
    class Ignores(kit_a.Agent):
        def act(self, state):
            return "CHECK" if "CHECK" in state.legal_moves else "FOLD"

    r = run_a.run(Ignores, hands=60, seed=5, toss=True)
    assert r.illegal > 0 and r.exceptions == 0
    assert not r.passed


def test_kit_a_parses_discard_and_dealer_default_keeps_a_pair():
    from hyperion.drills.fakekits import _table

    assert kit_a.parse_action("DISCARD:2") == ("discard", 2)
    with pytest.raises(ValueError):
        kit_a.parse_action("DISCARD: 2")
    # 7c 7d As: keep the sevens, toss the ace (index 2); Kh Qh 2c: keep the suited two, toss the deuce
    assert _table.default_toss((20, 21, 51)) == 2
    assert _table.default_toss((46, 42, 0)) == 2
    st = {"hole": (20, 21, 51), "legal": {"discard"}}
    assert _table.is_legal("discard", 1, st) and not _table.is_legal("discard", 3, st)
    assert not _table.is_legal("check", 0, st)


# ----- obs.history through the adapters (drill 6: an empty history cost Hero 2.5 points a table) -----

def test_kit_a_adapter_passes_the_action_log_as_history():
    st = {
        "hole": (48, 33), "board": (8, 20, 30), "street": 1, "seat": 1, "button": 3,
        "stacks": [1940, 1880, 0, 2000], "bets": [0, 0, 0, 0], "in_hand": [True, True, False, False],
        "pot": 260, "to_call": 0, "min_raise": 20, "max_raise": 1880, "legal": {"fold", "check", "raise"},
        "hand_no": 4, "blinds": (10, 20),
        "history": [(2, "fold", 0), (0, "raise", 60), (1, "raise", 120), (0, "call", 0), (1, "discard", 51)],
    }
    obs = KitAAdapter(CheapBot()).to_observation(kit_a.to_state(st))
    assert [(s, a.kind, a.amount) for s, a in obs.history] == [
        (2, ActionKind.FOLD, 0), (0, ActionKind.RAISE, 60), (1, ActionKind.RAISE, 120), (0, ActionKind.CALL, 0)]


def test_make_observation_rebuilds_raises_from_bets_when_the_kit_has_no_history():
    from hyperion.drills.adapter import history_from_bets, make_observation

    # button 0, SB 1, BB 2; seat 3 opened to 60, seat 5 called 60, seat 6 is all-in short for 45 (a call)
    stacks, bets = [2000, 1990, 1980, 1940, 2000, 1940, 0, 2000], [0, 10, 20, 60, 0, 60, 45, 0]
    h = history_from_bets(0, 0, stacks, bets, 20)
    assert [(s, a.kind, a.amount) for s, a in h] == [(3, ActionKind.RAISE, 60)]
    obs = make_observation(hole=(48, 33), board=(), street=0, seat=7, button=0, stacks=stacks, bets=bets,
                           in_hand=[True] * 8, pot=0, to_call=60, min_raise=100, max_raise=2000,
                           legal=["fold", "call", "raise"], hand_no=1, blinds=(10, 20))
    assert [(s, a.amount) for s, a in obs.history] == [(3, 60)]
    # blinds only: nothing to rebuild; a real history is never replaced
    assert history_from_bets(0, 0, stacks, [0, 10, 20, 0, 0, 0, 0, 0], 20) == []
    real = [(4, Action(ActionKind.CALL))]
    obs2 = make_observation(hole=(48, 33), board=(), street=0, seat=7, button=0, stacks=stacks, bets=bets,
                            in_hand=[True] * 8, pot=0, to_call=60, min_raise=100, max_raise=2000,
                            legal=["fold", "call", "raise"], hand_no=1, blinds=(10, 20), history=real)
    assert obs2.history == real
