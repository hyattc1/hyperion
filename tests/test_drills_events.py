"""Event-driven kits (H3): EventTracker's bookkeeping, the worked example on the fake event kit against the dealer's
true state, robustness to interrupted events, and the gate seat template driving the packaged example."""
import importlib.util
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_card
from hyperion.drills import events as EV
from hyperion.drills.fakekits.kit_e_style import runner as KR

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "hyperion" / "drills" / "event_example.py"


def C(s):
    return [parse_card(x) for x in s.split()]


def _hand(t: EV.EventTracker):
    """Six seats, antes 5, blinds 10/20 by seats 1 and 2 (button 0), seat 3 short (25 chips)."""
    t.table(4, 6)
    t.hand_start(7, 0, (10, 20), {0: 2000, 1: 2000, 2: 2000, 3: 25, 4: 1500, 5: 0}, C("Ah Kd"))
    for s in range(5):
        t.post(s, 5, ante=True)
    t.post(1, 10)
    t.post(2, 20)


@pytest.mark.night
def test_tracker_keeps_pot_bets_stacks_and_the_log():
    t = EV.EventTracker()
    _hand(t)
    assert t.in_hand == [True, True, True, True, True, False]
    t.action(3, "call", paid=20)  # the short seat calls all in for its last 20
    t.action(4, "raise", total=60)
    o = t.observation(["fold", "call", "raise"], None, 100, 1495)
    assert o.hand_no == 7 and o.street == 0 and o.seat == 4 and o.button == 0
    assert o.bets == [0, 10, 20, 20, 60, 0] and o.stacks == [1995, 1985, 1975, 0, 1435, 0]
    assert o.pot == 25 and o.total_pot == 25 + 110  # antes are dead money: in the pot, never a bet
    assert o.history == [(3, Action(ActionKind.CALL)), (4, Action(ActionKind.RAISE, 60))]
    t.action(0, "fold")
    t.action(1, "call", total=60)
    t.action(2, "fold")
    t.board(C("Kh 7d 2c"))  # a new street: every bet back to 0
    o = t.observation(["check", "raise"], None, 20, 1435)
    assert o.street == 1 and o.bets == [0] * 6 and o.pot == 25 + 20 + 60 + 20 + 60
    assert o.in_hand == [False, True, False, True, True, False] and o.to_call == 0
    t.action(1, "check")
    t.action(4, "raise", total=100)
    t.action(1, "call")  # no amounts at all: the call matches the top bet
    assert t.bets[1] == 100 and t.stacks[1] == 1835
    assert t.deltas(net={"1": 300, "4": -165}) == [0, 300, 0, 0, -165, 0]
    assert t.deltas(chips_after={1: 2300})[1] == 300


@pytest.mark.night
def test_fresh_catches_a_missed_event():
    t = EV.EventTracker()
    _hand(t)
    assert t.fresh(7, 0)
    assert not t.fresh(8, 0)  # a missed hand start
    t.board(C("Kh 7d 2c"))
    assert not t.fresh(7, 4)  # the turn card's event never came
    t.action(4, "fold")
    assert not t.fresh(7, 3)  # we are not in the hand


@pytest.mark.night
def test_a_board_past_its_last_size_reads_as_the_river():
    t = EV.EventTracker()
    _hand(t)
    t.board(C("Kh 7d 2c 9h Qd 3h"))
    assert t.street == 3


def _example_adapter_class():
    spec = importlib.util.spec_from_file_location("_event_example_under_test", EXAMPLE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_example_tracks_the_dealers_true_state_at_every_decision(monkeypatch):
    """Every Observation the example builds from the events equals the one the dealer's own state gives."""
    from hyperion.drills.adapter import dealer_state  # noqa: F401 - the same fields, ours

    seen, truth = [], []
    orig = EV.EventAdapter.to_observation

    def spy(self, req):
        o = orig(self, req)
        seen.append(o)
        return o

    monkeypatch.setattr(EV.EventAdapter, "to_observation", spy)
    rep = KR.run(str(EXAMPLE), tables=3, hands=40, seed=5, budget_ms=1000.0, interrupt=False,
                 watch=lambda st, req: truth.append(dict(st)))
    assert rep["illegal"] == 0 and not rep["errors"] and rep["decisions"] > 40, rep
    assert len(seen) == len(truth) == rep["decisions"]
    for o, st in zip(seen, truth):
        assert o.hole == tuple(st["hole"]) and o.board == tuple(st["board"]) and o.street == st["street"]
        assert o.stacks == st["stacks"] and o.bets == st["bets"] and o.in_hand == st["in_hand"]
        assert o.pot == st["pot"] and o.to_call == st["to_call"] and o.button == st["button"]
        assert (o.min_raise, o.max_raise) == ((st["min_raise"], st["max_raise"]) if "raise" in st["legal"] else (0, 0))
        assert [(s, a.kind.value) for s, a in o.history] == [(s, k) for s, k, _ in st["history"]]


def test_the_example_runs_clean_with_conformance_on(monkeypatch):
    """Every Observation the example builds passes the conformance rules (the HYPERION_CHECK=1 report)."""
    from hyperion.drills import conformance

    adapters = []

    def checked(adapter):
        conformance.checked(adapter)
        adapters.append(adapter)
        return adapter

    monkeypatch.setattr(conformance, "maybe_checked", checked)  # each table's fresh module imports it
    rep = KR.run(str(EXAMPLE), tables=2, hands=40, seed=8, budget_ms=1000.0, interrupt=False)
    assert rep["illegal"] == 0 and not rep["errors"] and rep["setup_over"] == 0, rep
    assert len(adapters) == 2
    for a in adapters:
        r = a.conformance
        assert r.observations > 10 and r.total == 0, r.summary()


@pytest.mark.skipif(not hasattr(__import__("signal"), "setitimer"), reason="needs SIGALRM")
def test_interrupted_events_never_reach_the_kit_as_errors_or_illegal_moves(monkeypatch):
    """A 50 us budget: most calls are cut by the kit's interrupt (a BaseException inside them). The entry must keep
    answering legal moves (check/fold when its state is stale) and never raise an Exception of its own."""
    rep = KR.run(str(EXAMPLE), tables=2, hands=30, seed=3, budget_ms=0.05, interrupt=True)
    assert sum(rep["interrupted"].values()) > 10, rep
    assert rep["illegal"] == 0 and not rep["errors"], rep


def test_the_ship_bot_defers_its_hand_end_behind_the_example():
    """The fake kit times on_result: the example's hand end leaves the curve for idle() at the next on_hand."""
    rep = KR.run(str(EXAMPLE), tables=1, hands=40, seed=2, budget_ms=1000.0, interrupt=False)
    assert rep["illegal"] == 0 and not rep["errors"], rep
    assert rep["calls"]["on_result"] > 10


# ------------------------------------------------------------------ the gate seat template

def _load_tool(name):
    spec = importlib.util.spec_from_file_location(f"{name}_for_events", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


SEAT = '''from hyperion.drills.gate_seat_template import Seat as _Template


class Seat(_Template):
    """The fake event kit's names for the worked example's Agent."""
    ENTRY_CLASS = "Agent"
    TABLE_START = "on_table"
    HAND_END = "on_result"
'''


def test_the_gate_seat_template_plays_the_packaged_example_with_untimed_hand_ends(tmp_path):
    gate, pack = _load_tool("gate"), _load_tool("pack")
    from hyperion.sim import bestiary

    src = tmp_path / "src"
    src.mkdir()
    entry = src / "agent.py"
    entry.write_text(EXAMPLE.read_text())
    pkg = tmp_path / "pkg"
    pack.build(pkg, entry, [], False, None)
    seat = tmp_path / "gate_seat.py"
    seat.write_text(SEAT)
    scratch = tmp_path / "cwd"
    scratch.mkdir()
    cfg = gate.Config(pkg=pkg, entry="agent.py", kit="seat", kit_dir="-", scratch=str(scratch), seat_file=seat)
    bestiary.HERO_CONFIG = gate.CHEAP
    try:
        res, _ = gate.play(cfg, bestiary.field_names("realistic"), 2, 3, Rules(), None, "measure", "sim")
    finally:
        bestiary.HERO_CONFIG = None
    assert res.fatal is None, res.notes
    assert res.decisions > 20 and res.stats.exceptions == 0 and res.stats.illegal == 0, (res.stats.last_error, res.notes)
    assert res.lifecycle == 0, res.notes  # every hand end ran (untimed) without raising
