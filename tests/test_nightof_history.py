"""Conformance holds adapters to the history Hero needs (drill 6): after a raise the Observation must carry it,
and an adapter that passes the kit's log must never drop a raise later in the hand, unless it declares that
its kit has no log and the history is rebuilt from the bets. The reference adapters pass through the fake
kits' runners with no history violation, and the template says how."""
from pathlib import Path

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.drills.adapter import Adapter, KitAAdapter, KitBAdapter, KitCAdapter, KitDAdapter, make_observation
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills.conformance import ConformanceReport, check_observation, checked
from hyperion.drills.fakekits.kit_a import runner as run_a
from hyperion.drills.fakekits.kit_b import runner as run_b

from .strategy_helpers import make_obs, preflop_obs, street_obs

ROOT = Path(__file__).resolve().parents[1]
RAISE = ActionKind.RAISE


def rules_hit(violations):
    return {v.split(":", 1)[0] for v in violations}


def raised_pot(history):
    """UTG raised to 60, we are on the button facing it."""
    obs = preflop_obs("Ah Kd", seat=7, button=7, actions=[(2, Action.raise_to(60))] + [(s, Action.fold()) for s in
                                                                                       (3, 4, 5, 6)])
    obs.history = history
    return obs


def test_a_raise_in_the_bets_must_be_in_the_history():
    assert check_observation(raised_pot([(2, Action.raise_to(60))])) == []
    v = check_observation(raised_pot([]))
    assert rules_hit(v) == {"history_raise"} and "2.5 points" in v[0] and "action log" in v[0]
    v = check_observation(raised_pot([(2, Action.call())]))
    assert rules_hit(v) == {"history_raise"}
    v = check_observation(raised_pot([(2, Action.raise_to(40))]))  # an increment passed as the total
    assert rules_hit(v) == {"history_raise"} and "raise-to totals" in v[0]


def test_no_raise_needed_when_nobody_bet_above_the_base():
    assert check_observation(make_obs(seat=3, bets=[10, 20, 0, 0, 0, 0, 0, 0])) == []  # unopened, blinds only
    limp = make_obs(seat=4, bets=[10, 20, 0, 20, 0, 0, 0, 0], history=[(3, Action.call())])
    assert check_observation(limp) == []
    checked_flop = street_obs("Ah Kd", "Kh 7d 2c", seat=2, pot=60)
    assert check_observation(checked_flop) == []
    straddled = make_obs(seat=4, bets=[10, 20, 40, 0, 0, 0, 0, 0])
    assert rules_hit(check_observation(straddled)) == {"history_raise"}
    assert check_observation(straddled, Rules(straddle=2)) == []


def test_make_observation_rebuilds_the_raise_when_the_kit_has_no_log():
    o = raised_pot([])
    rebuilt = make_observation(hole=o.hole, board=o.board, street=0, seat=7, button=7, stacks=o.stacks, bets=o.bets,
                               in_hand=o.in_hand, pot=0, to_call=o.to_call, min_raise=o.min_raise,
                               max_raise=o.max_raise, legal=[k.value for k in o.legal], hand_no=3, blinds=(10, 20))
    assert [(s, a.kind, a.amount) for s, a in rebuilt.history] == [(2, RAISE, 60)]
    assert check_observation(rebuilt) == []


def test_a_log_adapter_must_not_drop_a_raise_later_in_the_hand():
    pre = raised_pot([(2, Action.raise_to(60))])
    flop = street_obs("Ah Kd", "Kh 7d 2c", seat=7, button=7, pot=150, history=[], hand_no=3)
    log = ConformanceReport()
    assert log.check(pre) == []
    v = log.check(flop)
    assert "history_prefix" in rules_hit(v) and 'history_source = "bets"' in " ".join(v)
    bets = ConformanceReport(history_source="bets")
    bets.check(pre)
    assert "history_prefix" not in rules_hit(bets.check(flop))  # (the made-up flop's chip total differs: not this test)
    assert "rebuilt from the bets" in bets.summary() and "action log" in log.summary()
    log2 = ConformanceReport()
    log2.check(pre)
    grown = street_obs("Ah Kd", "Kh 7d 2c", seat=7, button=7, pot=150, hand_no=3,
                       history=[(2, Action.raise_to(60)), (7, Action.call())])
    assert "history_prefix" not in rules_hit(log2.check(grown))


def test_adapters_declare_their_history_source():
    assert Adapter.history_source == KitAAdapter.history_source == "log"
    assert KitBAdapter.history_source == KitCAdapter.history_source == KitDAdapter.history_source == "bets"
    assert checked(KitBAdapter(CheapBot())).conformance.history_source == "bets"
    assert checked(KitAAdapter(CheapBot())).conformance.history_source == "log"


def test_reference_adapters_carry_history_through_the_kit_runners():
    import types

    a = checked(KitAAdapter(CheapBot()))
    raised = []

    class Agent:
        def new_game(self, seat, n, stack):
            a.start(seat, n)

        def act(self, state):
            base = state.big_blind if state.street == "preflop" else 0
            raised.append(state.current_bet > base)
            return a.decide(state)

        def hand_over(self, hand_no, delta):
            pass

    r = run_a.run(Agent, hands=80, seed=4)
    assert r.exceptions == 0 and r.illegal == 0 and a.conformance.clean, a.conformance.summary()
    assert sum(raised) >= 5  # the runner's maniac raises often: those decisions carried the raise
    b = checked(KitBAdapter(CheapBot()))
    mod = types.SimpleNamespace(decide=b.decide, on_table_start=lambda info: b.start(info["seat"], info["players"]),
                                on_hand_end=lambda info: None)
    r = run_b.run(mod, hands=80, seed=4)
    assert r.exceptions == 0 and b.conformance.clean, b.conformance.summary()


def test_template_passes_the_log_and_documents_the_bets_path():
    src = (ROOT / "hyperion" / "drills" / "adapter_template.py").read_text()
    assert src.index("TODO 7  BLINDS") < src.index("TODO 7b HISTORY") < src.index("TODO 8  PER-TABLE INIT")
    assert "history=history(native)" in src and 'history_source = "log"' in src
    assert "rebuilds the hand's" in src and 'history_source = "bets"' in src and 'history_source = "partial"' in src
    assert "infer_history.py" in src and "history_gap" in src and "defer_hand_end" in src
    assert "tools/gate.py" in src
    from hyperion.drills.adapter_template import TonightAdapter, history

    assert history(None) == [] and TonightAdapter.history_source == "log"
