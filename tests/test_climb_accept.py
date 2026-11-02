"""tools/climb_accept.py as a window uses it (prompt 06): recipe names as specs, the night's rules file on the cells, and a
cache that survives `python -m hyperion.ship --set` (the switch's record lines leave the code version alone)."""
import importlib.util
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


CA = _load("climb_accept")


def test_a_spec_may_be_recipe_names_resolved_for_the_composite():
    from hyperion import ship

    assert CA.load_spec("") == {"dials": {}}
    assert CA.load_spec("survival") == {"dials": ship.recipe("survival", "composite")}
    assert CA.load_spec("dead_seats+survival") == {"dials": ship.recipe("dead_seats+survival", "composite")}
    assert CA.load_spec('{"dials": {"r3.open_scale": 1.1}}') == {"dials": {"r3.open_scale": 1.1}}
    # resolved on top of SHIP_DIALS, as hyperion.ship builds F: the governor and the route stay
    from hyperion.compose import bot as CB

    res = CA.resolve(CA.load_spec("survival"))["dials"]
    assert all(res[k] == v for k, v in CB.SHIP_DIALS.items() if k not in ship.recipe("survival", "composite"))


def test_the_nights_rules_file_reaches_a_cell_and_a_guards_payouts_win(tmp_path):
    rules = {"payouts": [50, 25, 12, 6, 3, 2, 1, 1], "blind_levels": [[10, 20], [20, 40]], "hands_per_level": 15}
    path = tmp_path / "rules_tonight.json"
    path.write_text(json.dumps(rules))
    r = CA._rules("lin", str(path))
    assert r.payouts == (50, 25, 12, 6, 3, 2, 1, 1) and r.blind_levels == ((10, 20), (20, 40)) and r.hands_per_level == 15
    assert CA._rules("brief", str(path)).payouts == (10, 7, 5, 4, 3, 2, 1, 0)
    assert CA._rules("lin", "double").blind_levels == CA._rules("lin", "double").blind_levels  # the named files still load
    assert CA._rules("lin", None) is None
    tag = CA._rules_tag(str(path))
    assert tag.startswith("f") and CA.cell_path("o", "k", ("night", "lin", str(path), None, 0)).endswith(
        f"night.lin.{tag}.-.0.json")
    path.write_text(json.dumps({**rules, "hands_per_level": 20}))
    assert CA._rules_tag(str(path)) != tag  # a changed file is a new cell
    assert CA.label(("night", "lin", str(path), None)) == "night +rules_tonight.json"


def test_the_switchs_record_lines_do_not_change_the_code_version():
    assert CA._record_line(b"+DIALS: dict = {'r3.call_margin': 0.03}")
    assert CA._record_line(b"-SHIP = 'composite'")
    assert not CA._record_line(b"+SHIP_DIALS: dict = {}") and not CA._record_line(b"+    deadline_ms: float = 0.5")


def _fake_run(monkeypatch, effects):
    """climb_accept's verdict on made-up samples: `effects` maps a cell label's start to the candidate's shift."""
    monkeypatch.setattr(CA, "run_cells", lambda *a, **k: None)
    monkeypatch.setattr(CA, "code_version", lambda: "test")
    base_key = CA.spec_key(CA.resolve({"dials": {}}), "test")

    def gather(out, key, c, lo, hi):
        n = hi - lo
        shift = 0.0 if key == base_key else next((v for k, v in effects.items() if CA.label(c).startswith(k)), 0.0)
        xs = [5.0 + shift + (0.01 if i % 2 else -0.01) * (1 + i % 3) for i in range(n)]
        return {"samples": xs, "mean": sum(xs) / n, "tmo": 0, "exc": 0, "ill": 0, "safe_err": 0, "p99": 100.0,
                "opp_mean": None}

    monkeypatch.setattr(CA, "gather", gather)


def test_aim_exploit_needs_an_exploit_field_up_not_night_up_and_a_lone_variant_down_replicates(monkeypatch, tmp_path):
    _fake_run(monkeypatch, {"exploit": 0.5, "bonus_card": -0.2})
    out = tmp_path / "v.json"
    CA.main(["--cand", '{"dials": {"x": 1}}', "--set", "screen", "--stages", "confirm,exploit,variants",
             "--aim", "exploit", "--json", str(out), "--out", str(tmp_path)])
    v = json.loads(out.read_text())
    assert v["accept"] is False and v["replicate"] == "bonus_card (realistic)"
    assert ["confirm: night not beyond noise down", True] in v["checks"]
    CA.main(["--cand", '{"dials": {"x": 1}}', "--set", "screen", "--stages", "confirm,exploit,variants",
             "--json", str(out), "--out", str(tmp_path)])  # aim night: night level is a reject, nothing to replicate
    v = json.loads(out.read_text())
    assert v["accept"] is False and v["replicate"] is None


def test_aim_exploit_without_an_exploit_gain_rejects(monkeypatch, tmp_path):
    _fake_run(monkeypatch, {})
    out = tmp_path / "v.json"
    CA.main(["--cand", '{"dials": {"x": 1}}', "--set", "screen", "--stages", "confirm,exploit",
             "--aim", "exploit", "--json", str(out), "--out", str(tmp_path)])
    v = json.loads(out.read_text())
    assert v["accept"] is False and v["replicate"] is None
