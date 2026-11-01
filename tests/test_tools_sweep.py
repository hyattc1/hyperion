"""tools/sweep.py: settings from a spec, and the paired report (Hero-minus-rival gaps, the lone bot in a mirror)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import sweep  # noqa: E402


def _bot(xs):
    return {"samples": xs, "seats": 8, "busts": 2, "places": [1] * 8, "tmo": 0, "exc": 0, "ill": 0, "safe_err": 0,
            "safe_over": 0}


def test_settings_from_spec_applies_the_base_to_every_setting():
    s = sweep.settings_from_spec({"base": {"a": 1}, "sweep": {"b": [2, 3]}, "settings": {"c": {"d": 4}}})
    assert s == {"base": {"a": 1}, "b=2": {"a": 1, "b": 2}, "b=3": {"a": 1, "b": 3}, "c": {"a": 1, "d": 4}}


def test_report_pairs_hero_against_each_rival_and_the_lone_bot_in_a_mirror():
    fields = {"top2": "hero,rival1,rival2", "r2h7": "rival2,hero,hero,hero,hero,hero,hero,hero"}
    res = {"base": {"top2": {"hero": _bot([4.0, 4.2]), "rival1": _bot([5.0, 4.8]), "rival2": _bot([5.1, 5.0])},
                    "r2h7": {"hero": _bot([4.4, 4.4]), "rival2": _bot([5.2, 5.1])}},
           "x": {"top2": {"hero": _bot([4.2, 4.3]), "rival1": _bot([4.9, 4.8]), "rival2": _bot([5.0, 4.9])},
                 "r2h7": {"hero": _bot([4.45, 4.42]), "rival2": _bot([4.9, 5.0])}}}
    out = sweep.format_results(res, fields, {"base": {}, "x": {}}, "rival1,rival2").splitlines()
    top2 = next(ln for ln in out if ln.startswith("x") and " top2 " in ln).split()
    assert top2[7] == "+0.150"  # Hero's paired delta
    assert top2[10] == "+0.200" and top2[12] == "+0.250"  # the gap to rival1 and to rival2 closed by that much
    mirror = next(ln for ln in out if ln.startswith("x") and " r2h7 " in ln)
    assert "-0.200" in mirror  # the lone rival2 lost 0.2 among seven Heroes


def test_field_rules_override_the_payouts():
    r = sweep.rules_from({"payouts": [10, 7, 5, 4, 3, 2, 1, 0]})
    assert r.payouts == (10, 7, 5, 4, 3, 2, 1, 0) and r.n_players == 8
    assert sweep.rules_from(None) is None
