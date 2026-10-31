"""tools/rmh_check.py: the RangeMyHand JSON parser and the comparison, on a synthetic fixture in their layout
(invented frequencies; no RangeMyHand data in the repo, no network)."""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import rmh_check  # noqa: E402

from hyperion.strategy.multiway import load_multiway  # noqa: E402
from hyperion.strategy.tables import CLASSES, load  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "rmh_pushfold_small.json"
I = {c: k for k, c in enumerate(CLASSES)}


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_parser_reads_their_layout_and_reorders_hands():
    rmh = rmh_check.parse_rmh(FIXTURE.read_text())
    assert len(rmh["spots"]) == 6
    assert ("9max", "UTG", 8, 10.0) in rmh["spots"] and ("6max", "UTG", 5, 10.0) in rmh["spots"]
    row = rmh["spots"][("9max", "SB", 1, 10.0)]
    assert set(row) == set(CLASSES)
    raw = _fixture()
    pos = raw["hands"].index("AKo")
    assert pos == 13 and row["AKo"] == raw["spots"][1]["pushFreq"][pos]  # their grid order, not ours
    assert row["AA"] == 1.0 and row["72o"] == 0.0
    assert any(0.0 < x < 1.0 for x in row.values())
    assert rmh["meta"]["version"] == "0.0.0-fixture" and rmh["meta"]["model"]["deadMoneyBB"] == 1.5


@pytest.mark.parametrize("mutate", [
    lambda d: d.pop("hands"),
    lambda d: d.__setitem__("hands", d["hands"][:-1]),
    lambda d: d["hands"].__setitem__(0, "AAx"),
    lambda d: d["hands"].__setitem__(1, "AA"),  # duplicate
    lambda d: d["spots"][0]["pushFreq"].__setitem__(3, 1.5),
    lambda d: d["spots"][0]["pushFreq"].__setitem__(3, True),
    lambda d: d["spots"][0]["pushFreq"].pop(),
    lambda d: d["spots"][0].__setitem__("stackBB", "10"),
    lambda d: d["spots"].__setitem__(0, ["not", "a", "spot"]),
])
def test_parser_rejects_anything_else(mutate):
    d = _fixture()
    mutate(d)
    with pytest.raises(ValueError):
        rmh_check.parse_rmh(json.dumps(d))


def test_parser_rejects_non_json_and_other_tables():
    with pytest.raises(ValueError):
        rmh_check.parse_rmh("stack, 22, 32o\n1, 0, 1\n")
    with pytest.raises(ValueError):
        rmh_check.parse_rmh(json.dumps([1, 2, 3]))


def test_compare_counts_disagreements_and_mad():
    theirs = {c: 0.0 for c in CLASSES}
    theirs["AA"] = 1.0
    theirs["KK"] = 0.6
    theirs["72o"] = 0.49
    ours = [0] * len(CLASSES)
    ours[I["AA"]] = 1
    ours[I["QQ"]] = 1  # we shove, they fold
    ours[I["72o"]] = 1  # just under their threshold: a disagreement
    r = rmh_check.compare(ours, theirs, threshold=0.5, worst=10)
    assert r["n"] == 169 and r["disagree"] == 3
    assert r["we_only"] == ["QQ", "72o"] and r["they_only"] == ["KK"]
    assert r["mad"] == pytest.approx((1.0 + 0.6 + 0.51) / 169)
    assert r["worst"][0] == ("QQ", 1, 0.0) and len(r["worst"]) == 3
    assert r["freq_ours"] == pytest.approx((6 + 6 + 12) / 1326)
    assert r["freq_theirs"] == pytest.approx((6 + 0.6 * 6 + 0.49 * 12) / 1326)


def test_run_check_maps_seats_to_players_behind():
    rmh = rmh_check.parse_rmh(FIXTURE.read_text())
    zero = [0] * 169
    aa = [1 if c == "AA" else 0 for c in CLASSES]
    push = [None] + [[None, None] + [aa if k == 7 else zero] * 24 for k in range(1, 8)]
    mw = {"k_max": 7, "push": push, "p_push": [None] + [[None, None] + [0.0] * 24 for _ in range(7)]}
    res = rmh_check.run_check(rmh, mw, list(range(2, 26)))
    by = {r["seat"]: r for r in res}
    assert set(by) == {"SB", "BTN", "UTG6", "UTG"}  # CO's only fixture row is 1 bb, outside our depths
    assert [r["depth"] for r in by["SB"]["rows"]] == [5, 10]
    assert by["UTG"]["k"] == 7 and by["UTG"]["behind"] == 8 and by["UTG"]["note"]
    assert by["UTG6"]["k"] == 5
    t = rmh_check.totals(by["UTG"])
    assert t["depths"] == 1 and t["they_only"] > 0 and t["we_only"] == 0  # we shove only AA, they shove ~9%
    assert by["UTG"]["rows"][0]["freq_ours"] == pytest.approx(6 / 1326)


def test_main_runs_end_to_end_on_the_fixture(capsys):
    if load_multiway(load(need_hu=True)) is None:
        pytest.skip("tables/pushfold_multi.json missing or stale")
    assert rmh_check.main(["--file", str(FIXTURE), "--worst", "3"]) == 0
    out = capsys.readouterr().out
    assert rmh_check.ATTRIBUTION in out and "0.0.0-fixture" in out
    assert "### 9max SB (1 behind) vs our k = 1" in out and "| 10 |" in out
    assert "### 9max UTG (8 behind) vs our k = 7" in out and "| UTG | 8 / 7 |" in out


def test_main_refuses_a_bad_file(tmp_path, capsys):
    bad = tmp_path / "push-fold-ranges.json"
    bad.write_text('{"hands": [], "spots": []}')
    assert rmh_check.main(["--file", str(bad)]) == 2
    assert "hands" in capsys.readouterr().err
