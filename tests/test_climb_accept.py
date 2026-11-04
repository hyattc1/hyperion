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

    def gather(out, key, c, lo, hi, rt=False):
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


def test_an_exploit_cell_down_rejects_under_every_aim(monkeypatch, tmp_path):
    _fake_run(monkeypatch, {"elite": 0.5, "exploit_3": -0.5})
    out = tmp_path / "v.json"
    CA.main(["--cand", '{"dials": {"x": 1}}', "--set", "screen", "--stages", "confirm,elite,exploit",
             "--aim", "strong", "--json", str(out), "--out", str(tmp_path)])
    v = json.loads(out.read_text())
    assert v["accept"] is False
    assert any(txt.startswith("exploit: none beyond noise down (down: exploit_3") and not ok for txt, ok in v["checks"])


def test_aim_exploit_without_an_exploit_gain_rejects(monkeypatch, tmp_path):
    _fake_run(monkeypatch, {})
    out = tmp_path / "v.json"
    CA.main(["--cand", '{"dials": {"x": 1}}', "--set", "screen", "--stages", "confirm,exploit",
             "--aim", "exploit", "--json", str(out), "--out", str(tmp_path)])
    v = json.loads(out.read_text())
    assert v["accept"] is False and v["replicate"] is None


def test_an_edit_to_an_untracked_module_changes_the_code_version(tmp_path):
    p = os.path.join(ROOT, "hyperion", "_cv_probe_untracked.py")
    try:
        with open(p, "w") as fh:
            fh.write("A = 1\n")
        v1 = CA.code_version()
        with open(p, "w") as fh:
            fh.write("A = 2\n")
        v2 = CA.code_version()
        assert v1 != v2
    finally:
        os.remove(p)


def test_no_held_out_set_overlaps_the_judge_set():
    jl, jh = CA.seed_range("judge")
    for k in range(1, 30):
        lo, hi = CA.seed_range(f"H{k}")
        assert hi <= jl or lo >= jh, k
    assert CA.seed_range("H10") == (29000, 29400) and CA.seed_range("H11") == (31000, 31400)


# --- addendum 11: the weighted score (tools/accept_weights.json, tools/accept_weighted.py) ---------------------------

import itertools
import math

import pytest

WS = CA.WS
WTS = WS.load()
EVERY_STAGE = "confirm,guards,elite,exploit,variants,aware"


def _fake_cells(monkeypatch, effects, calls=None):
    """Made-up samples with a set mean and interval: `effects` maps a cell's exact label to (delta, ci). The candidate's
    per-seed difference alternates +-s around delta, so its 95% interval is 1.96 s / sqrt(n - 1)."""
    monkeypatch.setattr(CA, "run_cells", lambda *a, **k: calls.append(a) if calls is not None else None)
    monkeypatch.setattr(CA, "code_version", lambda: "test")
    base_key = CA.spec_key(CA.resolve({"dials": {}}), "test")

    def gather(out, key, c, lo, hi, rt=False):
        n = hi - lo
        base = [5.0 + 0.01 * (i % 3) for i in range(n)]
        if key == base_key:
            xs = base
        else:
            d, ci = effects.get(CA.label(c), (0.0, 0.0))
            s = ci * math.sqrt(n - 1) / 1.96
            xs = [b + d + (s if i % 2 else -s) for i, b in enumerate(base)]
        return {"samples": xs, "mean": sum(xs) / n, "tmo": 0, "exc": 0, "ill": 0, "safe_err": 0, "p99": 100.0,
                "opp_mean": None}

    monkeypatch.setattr(CA, "gather", gather)


def _run(tmp_path, *args, cand='{"dials": {"x": 1}}'):
    out = tmp_path / "v.json"
    CA.main(["--cand", cand, "--json", str(out), "--out", str(tmp_path), *args])
    return json.loads(out.read_text())


def test_the_weights_file_is_the_reviews_section():
    F = WTS["families"]
    assert {f: F[f]["weight"] for f in WS.FAMILIES} == {"ordinary": 0.20, "strong": 0.15, "adapters": 0.15,
                                                        "twist_realistic": 0.20, "twist_aware": 0.30}
    assert {f: F[f]["range"] for f in WS.FAMILIES} == {"ordinary": [0.10, 0.35], "strong": [0.05, 0.30],
                                                       "adapters": [0.05, 0.30], "twist_realistic": [0.10, 0.30],
                                                       "twist_aware": [0.15, 0.45]}
    assert sum(F[f]["weight"] for f in WS.FAMILIES) == pytest.approx(1.0)
    for f in ("ordinary", "strong"):
        assert sum(F[f]["cells"].values()) == pytest.approx(1.0)
    assert F["strong"]["cells"]["elite_b"] == 0.20 and F["strong"]["cells"]["mirror_b"] == 0.10
    assert F["adapters"]["bot_share"] * len(F["adapters"]["bots"]) == 1.0
    from hyperion.drills import variants as V

    # tranche_holdem (drill 11's twist, V-j, 2026-11-03) weighs as an unlisted twist ("unlisted": 1), kept out of the
    # table so the saved reviews' weighted scores reproduce (a new row would reweight every one of them)
    assert set(WTS["variant_probability"]["p"]) == set(V.catalog_names()) - {"tranche_holdem"}
    assert sum(WTS["variant_probability"]["p"].values()) == 89  # variants-ranked.md's rows for the 26 entries
    u = WTS["units"]
    own = WTS["cap"]["own_points"]  # addendum 11's per-scale caps are 0.03 night points in each scale's own points
    for scale, factor in (("8..1", u["payouts"]["8..1"]), ("10/7/5/4/3/2/1/0", u["payouts"]["10/7/5/4/3/2/1/0"]),
                          ("50/25/12/6/3/2/1/1", u["payouts"]["50/25/12/6/3/2/1/1"]),
                          ("top_heavy", u["variants"]["top_heavy"]), ("heads-up 10/7", u["rules"]["hu"]),
                          ("three-handed 10/7/5", u["rules"]["three"])):
        assert own[scale] == pytest.approx(WTS["cap"]["night_points"] / factor, abs=0.0005), scale


def test_every_climb_accept_cell_maps_to_a_family():
    from hyperion.drills import variants as V
    from hyperion.sim import aware as AW

    fam = lambda stage, c: WS.classify(WTS, stage, CA.label(c if len(c) == 4 else (*c, None)))["family"]
    assert [fam("confirm", c) for c in CA.CONFIRM] == ["ordinary"]
    assert [fam("guards", c) for c in CA.GUARDS] == ["ordinary", "ordinary", "strong", "ordinary", "ordinary",
                                                     "ordinary"]
    assert {fam("elite", c) for c in CA.ELITE} == {"strong"}
    assert {fam("exploit", c) for c in CA.EXPLOIT} == {"adapters"}
    assert {fam("judges", c) for c in CA.JUDGES} == {"judges"}
    assert {fam("variants", (CA.VARIANT_FIELD, "lin", None, v)) for v in V.catalog_names()} == {"twist_realistic"}
    assert {fam("aware", (f, "lin", None, AW.AWARE_VARIANT[f])) for f in AW.AWARE_FIELDS} == {"twist_aware"}
    assert fam("aware", ("generic_aware", "lin", None, "auction")) == "twist_aware"
    # every hold'em cell has its own share in the section's table, and every adapter cell is one bot in one format
    for c in CA.CONFIRM + CA.GUARDS + CA.ELITE:
        f = fam("confirm", c)
        assert CA.label((*c, None)) in WTS["families"][f]["cells"]
    seats = {(x["bot"], x["fmt"]) for x in (WS.classify(WTS, "exploit", CA.label((*c, None))) for c in CA.EXPLOIT)}
    assert seats == {(b, f) for b in ("exploiter1", "exploiter2", "exploiter3", "exploiter4", "adapt1") for f in ("8max", "hu",
                                                                                                    "three")}
    units = {CA.label((*c, None)): WS.classify(WTS, "exploit", CA.label((*c, None)))["unit"] for c in CA.EXPLOIT}
    assert units["adapt @10/7/5/4/3/2/1/0"] == 0.7 and units["exploit3_hu +hu"] == pytest.approx(1 / 3)
    assert units["adapt_3 +three"] == 0.4


def test_the_weighted_blocks_arithmetic_on_a_hand_made_case(monkeypatch, tmp_path):
    _fake_cells(monkeypatch, {"night": (0.02, 0.01), "realistic": (-0.01, 0.01), "elite": (0.03, 0.02),
                              "exploit2_hu +hu": (0.3, 0.3), "bounty (realistic)": (0.05, 0.05),
                              "bounty (bounty_aware)": (0.04, 0.02)})
    v = _run(tmp_path, "--set", "screen", "--stages", EVERY_STAGE, "--aim", "exploit")
    w = v["weighted"]
    # by hand, in night points: each family's mean and half-width (cells perfectly correlated inside a family)
    ordinary = (0.40 * 0.02 + 0.10 * -0.01, 0.40 * 0.01 + 0.10 * 0.01)
    strong = (0.20 * 0.03, 0.20 * 0.02)
    adapters = (1 / 3 * 1 / 5 * 1 / 3 * 0.3, 1 / 3 * 1 / 5 * 1 / 3 * 0.3)  # format third, bot fifth (addendum 15), hu 1/3
    # bounty's P over the catalogue's 89 plus tranche_holdem's 1 (an unlisted twist's weight: not in the table)
    twist = (8 / 90 * 0.05, 8 / 90 * 0.05)
    aware = (8 / 29.5 * 0.04, 8 / 29.5 * 0.02)  # over the five aware fields' twists (11 + 8 + 7 + 2.5 + 1)
    fams = {"ordinary": ordinary, "strong": strong, "adapters": adapters, "twist_realistic": twist,
            "twist_aware": aware}
    wt = {"ordinary": 0.20, "strong": 0.15, "adapters": 0.15, "twist_realistic": 0.20, "twist_aware": 0.30}
    for f, (m, h) in fams.items():
        assert w["families"][f]["mean"] == pytest.approx(m) and w["families"][f]["half"] == pytest.approx(h), f
    mean = sum(wt[f] * fams[f][0] for f in fams)
    half = math.sqrt(sum((wt[f] * fams[f][1]) ** 2 for f in fams))
    assert w["mean"] == pytest.approx(mean) and w["half"] == pytest.approx(half)
    assert w["lb"] == pytest.approx(mean - half) and mean == pytest.approx(0.0074431, abs=1e-7)
    assert w["dropped"] == [] and w["cap"]["broken"] == [] and w["missing"] == {}


def test_the_cap_fires_in_night_points(monkeypatch, tmp_path):
    # the same -0.08 is beyond the cap three-handed (x 0.4 = -0.032) but not heads-up (x 1/3 = -0.027); top_heavy's
    # -0.15 is -0.021 night points (cap 0.21 in its own points), and realistic's -0.035 is beyond it
    _fake_cells(monkeypatch, {"exploit_3 +three": (-0.08, 0.0), "exploit_hu +hu": (-0.08, 0.0),
                              "top_heavy (realistic)": (-0.15, 0.0), "realistic": (-0.035, 0.004)})
    w = _run(tmp_path, "--set", "screen", "--stages", EVERY_STAGE, "--aim", "exploit")["weighted"]
    broken = {b["cell"]: b["upper_night_points"] for b in w["cap"]["broken"]}
    assert set(broken) == {"exploit_3 +three", "realistic"}
    assert broken["exploit_3 +three"] == pytest.approx(-0.032) and broken["realistic"] == pytest.approx(-0.031)


def test_w_min_takes_the_worst_corner(monkeypatch, tmp_path):
    # ordinary room and the twist-aware field down, adapters up a lot: the worst weights load the losers to their
    # range tops and starve the adapters
    _fake_cells(monkeypatch, {"night": (-0.01, 0.004), "toss_or_holdem (toss_or_holdem_aware)": (-0.03, 0.01),
                              "exploit_hu +hu": (0.9, 0.2), "elite": (0.01, 0.01)})
    w = _run(tmp_path, "--set", "screen", "--stages", EVERY_STAGE, "--aim", "exploit")["weighted"]
    fs = w["families"]
    corner = w["w_min"]["weights"]
    assert corner["adapters"] == pytest.approx(0.05) and corner["twist_aware"] == pytest.approx(0.45)
    assert corner["ordinary"] == pytest.approx(0.35)

    def lb(ws):
        m = sum(ws[f] * fs[f]["mean"] for f in fs)
        return m - math.sqrt(sum((ws[f] * fs[f]["half"]) ** 2 for f in fs))

    # brute force over every weighting in the ranges on a 0.05 grid (it holds every corner): none is worse
    F = WTS["families"]
    grid = {f: [round(x * 0.05, 2) for x in range(round(F[f]["range"][0] / 0.05), round(F[f]["range"][1] / 0.05) + 1)]
            for f in WS.FAMILIES}
    worst = min(lb(dict(zip(WS.FAMILIES, ws))) for ws in itertools.product(*grid.values())
                if abs(sum(ws) - 1) < 1e-9)
    assert w["w_min"]["lb"] == pytest.approx(worst) and w["w_min"]["lb"] < w["lb"]
    assert w["w_min"]["lb"] == pytest.approx(lb(corner))


def test_route2_refuses_a_screen_set_or_a_missing_stage_before_playing(monkeypatch, tmp_path):
    calls = []
    _fake_cells(monkeypatch, {}, calls)
    with pytest.raises(SystemExit, match="--route2 refuses: set 'screen' is not a held-out set"):
        _run(tmp_path, "--set", "screen", "--stages", EVERY_STAGE, "--route2")
    with pytest.raises(SystemExit, match="stages not run: elite, exploit, aware"):
        _run(tmp_path, "--set", "H30", "--stages", "confirm,guards,variants", "--route2")
    with pytest.raises(SystemExit, match="part of the catalogue"):
        _run(tmp_path, "--set", "H30", "--stages", EVERY_STAGE, "--variants", "bounty", "--route2")
    with pytest.raises(SystemExit, match="not a held-out set"):
        _run(tmp_path, "--set", "judge", "--stages", EVERY_STAGE, "--route2")
    with pytest.raises(SystemExit, match="--identical: unknown holdm"):
        _run(tmp_path, "--set", "screen", "--stages", "confirm", "--identical", "holdm")
    assert calls == []
    # without --route2 a screen prints the weighted block and nothing refuses
    assert _run(tmp_path, "--set", "screen", "--stages", "confirm")["weighted"]["dropped"] == [
        "strong", "adapters", "twist_realistic", "twist_aware"]


def test_the_main_verdict_is_unchanged_by_the_weighted_score_and_route2(monkeypatch, tmp_path, capsys):
    # main rule: realistic down rejects; weighted: the heads-up gain carries W-min above zero, no cap broken
    effects = {"realistic": (-0.004, 0.003), "exploit2_hu +hu": (0.6, 0.1)}
    _fake_cells(monkeypatch, effects)
    judges = _run(tmp_path, "--set", "judge", "--stages", "judges")
    (tmp_path / "judges.json").write_text(json.dumps(judges))
    capsys.readouterr()
    plain = _run(tmp_path, "--set", "H30", "--stages", EVERY_STAGE, "--aim", "exploit")
    out_plain = capsys.readouterr().out
    r2 = _run(tmp_path, "--set", "H30", "--stages", EVERY_STAGE, "--aim", "exploit", "--route2", "--judges-json",
              str(tmp_path / "judges.json"))
    out_r2 = capsys.readouterr().out
    monkeypatch.setattr(WS, "score", lambda stages, identical: None)  # no weighted code at all
    monkeypatch.setattr(WS, "lines", lambda ws: [])
    bare = _run(tmp_path, "--set", "H30", "--stages", EVERY_STAGE, "--aim", "exploit")
    out_bare = capsys.readouterr().out
    main = lambda v: {k: v[k] for k in ("version", "set", "seeds", "base", "cand", "stages", "checks", "accept",
                                        "replicate")}
    assert main(plain) == main(r2) == main(bare)
    assert plain["accept"] is False and ["guards: none beyond noise down (down: realistic)", False] in plain["checks"]
    head = out_bare.rstrip("\n")
    assert out_plain.startswith(head) and out_r2.startswith(head) and "\n## weighted" not in head
    assert out_plain.index("**REJECT**") < out_plain.index("## weighted (addendum 11")
    # route 2 is its own verdict: here it accepts what the main rule rejects, once the down cell is in the log
    assert r2["route2"]["applies"] and r2["route2"]["accept"] is True and r2["route2"]["log_down_cells"] == [
        "realistic"]
    assert r2["weighted"]["w_min"]["lb"] > 0 and "**ROUTE 2: ACCEPT**" in out_r2 and "route2" not in plain
    # a judge down, or no judges at all, and route 2 does not accept
    _fake_cells(monkeypatch, {**effects, "judge2": (-0.05, 0.01)})
    j = _run(tmp_path, "--set", "judge", "--stages", "judges")
    assert WS.route2(r2["weighted"], False, j["stages"]["judges"])["accept"] is False
    assert WS.route2(r2["weighted"], False, None)["accept"] is None
    # another candidate's judges are refused
    with pytest.raises(SystemExit, match="another base or candidate"):
        _run(tmp_path, "--set", "H30", "--stages", EVERY_STAGE, "--route2", "--judges-json",
             str(tmp_path / "judges.json"), cand='{"dials": {"x": 2}}')


# The review's re-scored rows (docs/research/acceptance-rule-review.md, scripts and final_rows.json in the session's
# acc/ scratchpad), from the saved verdicts it read: goal/b15/s5_h14.json and goal/b16/vf_h15.json, copied verbatim to
# tests/fixtures/accept_review/. The identity claims are its registry's: S5 changes hold'em tables only (live =
# the four hold'em-table twists); V-f plays nine twists and plain hold'em identically.
REVIEW = os.path.join(ROOT, "tests", "fixtures", "accept_review")
VF_LIVE = ("toss_or_holdem", "three_card_blind_discard", "bounty", "knockout_bounty", "bonus_card", "auction",
           "swap_holdem", "swap_one_turn", "exposed_card")


def _weights_before_addendum_15():
    """The weights the review's rows were scored under: four adapter bots, a fixed quarter each (addendum 15 added
    exploiter 4 and made it a fifth each; every past verdict keeps the rule it was scored by)."""
    W = WS.load()
    ad = W["families"]["adapters"]
    ad["bots"].pop("exploiter4")
    ad["bot_share"] = 0.25
    return W


@pytest.mark.parametrize("name, path, identical, row", [
    ("S5 on H14", "s5_h14.json", ["twists"],
     {"W": 0.004719703361898699, "lb": 0.0009120812331385774, "lbmin": -0.002723069485978417,
      "fx_lb": -0.0005033003923710221, "fx_min": -0.0035156036125737135}),
    ("V-f on H15", "vf_h15.json", ["holdem"] + [v for v in WTS["variant_probability"]["p"] if v not in VF_LIVE],
     {"W": 0.002211377704760369, "lb": -0.004057934685576477, "lbmin": -0.006086902028364716,
      "fx_lb": -0.004057934685576477, "fx_min": -0.006086902028364716}),
])
def test_the_reviews_rescored_rows_reproduce_from_their_saved_verdicts(name, path, identical, row):
    with open(os.path.join(REVIEW, path)) as fh:
        v = json.load(fh)
    W = _weights_before_addendum_15()
    fixed = WS.score(v["stages"], identical, W)  # the committed rule then: a fixed quarter per adapter bot
    shared = WS.score(v["stages"], identical, W, adapters="shared")  # the review's W columns before that change
    assert shared["mean"] == pytest.approx(row["W"], rel=1e-9, abs=1e-12)
    assert shared["lb"] == pytest.approx(row["lb"], rel=1e-9, abs=1e-12)
    assert shared["w_min"]["lb"] == pytest.approx(row["lbmin"], rel=1e-9, abs=1e-12)
    assert fixed["lb"] == pytest.approx(row["fx_lb"], rel=1e-9, abs=1e-12)
    assert fixed["w_min"]["lb"] == pytest.approx(row["fx_min"], rel=1e-9, abs=1e-12)
    assert fixed["cap"]["broken"] == [] and fixed["dropped"] == [] and fixed["contradicted"] == []
    # both fail route 2's condition (a) on W-min (V-f, accepted by the main rule, never needed route 2)
    r = WS.route2(fixed, False, None)
    assert r["accept"] is False and [ok for txt, ok in r["checks"] if txt.startswith("(a)")] == [False]
