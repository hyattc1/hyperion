"""hyperion/drills/conformance.py: single-observation invariants, the cross-call report, and the
adapter wrapper on the kit B and kit C reference adapters (clean) and on deliberately wrong ones."""
import atexit
import random
import sys
import types

import pytest

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.drills.adapter import KitBAdapter
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills import conformance
from hyperion.drills.conformance import ConformanceReport, check_observation, checked, maybe_checked
from hyperion.drills.fakekits.kit_b import runner as run_b
from hyperion.drills.fakekits.kit_c import runner as run_c

from .strategy_helpers import make_obs, random_obs

CHECK, CALL, FOLD, RAISE = ActionKind.CHECK, ActionKind.CALL, ActionKind.FOLD, ActionKind.RAISE


def rules_hit(violations):
    return {v.split(":", 1)[0] for v in violations}


def sb_obs(**kw):
    """Unopened preflop, we are the small blind: to_call 10, legal fold/call/raise, min_raise 40."""
    return make_obs(seat=0, bets=[10, 20, 0, 0, 0, 0, 0, 0], hole="Ah Ad", **kw)


def test_clean_observations_have_no_violations():
    assert check_observation(sb_obs()) == []
    bb = make_obs(seat=1, bets=[10, 20, 0, 0, 0, 0, 0, 0])
    assert bb.to_call == 0 and check_observation(bb) == []
    flop = make_obs(hole="Ah Ad", board="Kh 7d 2c", street=1, seat=2, pot=60)
    assert check_observation(flop) == []


def test_two_thousand_random_observations_are_clean():
    rng = random.Random(2026)
    bad = [v for _ in range(2000) for v in check_observation(random_obs(rng), Rules())]
    assert bad == [], bad[:5]


@pytest.mark.parametrize("field,value,rule", [
    ("hole", (0,), "hole_len"),
    ("street", 7, "street_range"),
    ("board", (0, 5, 10), "board_len"),
    ("hole", (0, 99), "card_range"),
    ("hole", (0, "Ah"), "card_range"),
    ("seat", 8, "seat_range"),
    ("button", -1, "button_range"),
    ("bets", [0] * 7, "lengths"),
    ("stacks", [-1] + [2000] * 7, "stacks_nonneg"),
    ("bets", [10, -20, 0, 0, 0, 0, 0, 0], "bets_nonneg"),
    ("in_hand", [False] + [True] * 7, "in_hand_self"),
    ("pot", -5, "pot_nonneg"),
    ("to_call", -1, "to_call_nonneg"),
    ("to_call", 5, "to_call_bets"),
    ("legal", frozenset(), "legal_empty"),
    ("legal", frozenset({"fold", "call"}), "legal_kinds"),
    ("legal", frozenset({FOLD, CHECK, CALL, RAISE}), "check_vs_call"),  # CHECK while to_call > 0
    ("legal", frozenset({FOLD, RAISE}), "check_vs_call"),  # CALL missing while to_call > 0
    ("min_raise", 20, "raise_total"),  # not above the current bet: an increment
    ("min_raise", 3000, "raise_bounds"),
    ("max_raise", 5000, "raise_max_stack"),
    ("blinds", (20, 10), "blinds_order"),
    ("blinds", (0, 20), "blinds_positive"),
    ("hand_no", -1, "hand_no"),
    ("history", [(9, Action.fold())], "history_seat"),
    ("history", [(1, "fold")], "history_action"),
])
def test_each_rule_fires_once_on_the_broken_field(field, value, rule):
    obs = sb_obs()
    setattr(obs, field, value)
    assert rule in rules_hit(check_observation(obs)), check_observation(obs)


def test_duplicate_card_across_hole_and_board():
    obs = make_obs(hole="Ah Ad", board="Ah 7d 2c", street=1, seat=2, pot=60)
    assert rules_hit(check_observation(obs)) == {"card_dup"}


def test_zero_to_call_with_call_legal_or_check_missing():
    obs = make_obs(seat=1, bets=[10, 20, 0, 0, 0, 0, 0, 0])
    obs.legal = frozenset({FOLD, CALL, RAISE})
    assert rules_hit(check_observation(obs)) == {"check_vs_call"}


def test_all_in_player_is_not_asked_for_a_call():
    obs = make_obs(seat=0, stacks=[0] + [2000] * 7, bets=[10, 20, 0, 0, 0, 0, 0, 0], to_call=0,
                   legal=frozenset({CHECK}))
    assert check_observation(obs) == []


def test_rules_drive_hole_and_board_counts():
    three = make_obs(hole="Ah Ad Kc")
    assert "hole_len" in rules_hit(check_observation(three))
    assert check_observation(three, Rules(hole_cards=3)) == []


def test_malformed_observation_is_a_finding_not_a_crash():
    obs = sb_obs()
    obs.stacks = None
    (only,) = check_observation(obs)
    assert only.startswith("malformed:")


def test_report_groups_by_rule_and_keeps_five_examples():
    r = ConformanceReport()
    for i in range(9):
        r.record([f"raise_total: example {i}", "pot_nonneg: once" if i == 0 else "raise_total: twin"])
    assert r.counts["raise_total"] == 17 and r.counts["pot_nonneg"] == 1 and r.total == 18
    assert len(r.examples["raise_total"]) == 5 and r.examples["raise_total"][0] == "raise_total: example 0"
    assert "18 violations in 2 rules" in r.summary() and "raise_total x17" in r.summary()


def test_report_cross_call_rules():
    r = ConformanceReport()
    a = sb_obs(hand_no=4)
    assert r.check(a) == []
    b = sb_obs(hand_no=4, button=6)
    b.pot += 30  # chips appeared mid-hand
    assert rules_hit(r.check(b)) == {"chips", "button_changed"}
    c = sb_obs(hand_no=5)  # a new hand resets the chip baseline
    c.pot += 30
    assert r.check(c) == []
    d = make_obs(seat=3, hand_no=5)
    assert rules_hit(r.check(d)) >= {"seat_changed"}
    assert r.observations == 4


def kit_b_module(adapter):
    return types.SimpleNamespace(
        decide=adapter.decide,
        on_table_start=lambda info: adapter.start(info["seat"], info["players"]),
        on_hand_end=lambda info: adapter.hand_end(info["hand_id"], info["delta"]),
    )


def test_kit_b_reference_adapter_is_clean_through_the_runner():
    adapter = checked(KitBAdapter(CheapBot()))
    r = run_b.run(kit_b_module(adapter), hands=50, seed=3)
    rep = adapter.conformance
    assert r.exceptions == 0 and r.illegal == 0 and rep.clean, r.summary() + "\n" + rep.summary()
    assert rep.observations == r.decisions > 50
    assert rep.actions["fold"] > 0 and rep.actions["raise"] > 0 and sum(rep.actions.values()) == r.decisions
    assert checked(adapter) is adapter and adapter.conformance is rep  # idempotent


def test_kit_c_reference_adapter_is_clean_via_env_var(tmp_path, monkeypatch):
    sub = tmp_path / "submission.py"
    sub.write_text(
        "import sys\nfrom hyperion.drills.adapter import KitCAdapter\nfrom hyperion.drills.cheapbot import CheapBot\n"
        "from hyperion.drills.conformance import maybe_checked\n"
        "maybe_checked(KitCAdapter(CheapBot())).serve(sys.stdin, sys.stdout)\n"
    )
    monkeypatch.setenv("HYPERION_CHECK", "1")
    r = run_c.run([sys.executable, str(sub)], hands=30, seed=3)
    assert r.exceptions == 0 and r.illegal == 0, r.summary() + " " + "; ".join(r.notes)
    stderr = [n for n in r.notes if n.startswith("stderr:")]
    assert stderr and f"{r.decisions} observations checked, 0 violations" in stderr[0], r.notes


class IncrementAsTotal(KitBAdapter):
    """The increment-vs-total bug: kit B's min/max_raise_by passed through as raise-to totals."""

    def to_observation(self, o):
        obs = super().to_observation(o)
        obs.min_raise, obs.max_raise = o["you"]["min_raise_by"], o["you"]["max_raise_by"]
        return obs


class PotIncludesBets(KitBAdapter):
    def to_observation(self, o):
        obs = super().to_observation(o)
        obs.pot += sum(obs.bets)
        return obs


class Crashing(KitBAdapter):
    def to_observation(self, o):
        raise KeyError("suit")


def test_increment_bug_passes_the_kit_runner_but_not_conformance():
    adapter = checked(IncrementAsTotal(CheapBot()))
    r = run_b.run(kit_b_module(adapter), hands=50, seed=3)
    rep = adapter.conformance
    assert r.illegal == 0 and r.exceptions == 0, r.summary()  # the kit sim is blind to it: clamp() hides the bounds
    assert rep.counts["raise_total"] > 10 and set(rep.counts) == {"raise_total"}, rep.summary()
    assert "increment passed as a total" in rep.examples["raise_total"][0]


def test_pot_bug_is_caught_by_chip_conservation():
    adapter = checked(PotIncludesBets(CheapBot()))
    run_b.run(kit_b_module(adapter), hands=30, seed=3)
    assert adapter.conformance.counts["chips"] > 0 and "pot includes" in adapter.conformance.examples["chips"][0]


def test_translation_errors_are_counted_not_swallowed():
    adapter = checked(Crashing(CheapBot()))
    r = run_b.run(kit_b_module(adapter), hands=5, seed=3)
    assert r.exceptions == 0  # Adapter.decide fell back to native_safe, the kit saw nothing
    assert adapter.conformance.counts["translate_error"] == r.decisions > 0


def test_maybe_checked_only_wraps_when_asked(monkeypatch):
    monkeypatch.delenv("HYPERION_CHECK", raising=False)
    a = KitBAdapter(CheapBot())
    assert maybe_checked(a) is a and getattr(a, "conformance", None) is None
    monkeypatch.setenv("HYPERION_CHECK", "1")
    assert maybe_checked(a) is a and a.conformance is not None
    atexit.unregister(conformance._print_report)  # keep the report out of pytest's own exit
