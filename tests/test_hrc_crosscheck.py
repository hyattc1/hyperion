"""tools/hrc_check.py: the HRC CSV parser and the comparison, on a synthetic fixture (no HRC data in the repo)."""
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hrc_check  # noqa: E402

from hyperion.strategy.tables import CLASSES  # noqa: E402

FIXTURE = ROOT / "tests" / "fixtures" / "hrc_hu_small.csv"


def test_parser_reads_the_hrc_layout():
    table = hrc_check.parse_hrc_csv(FIXTURE.read_text())
    assert sorted(table) == [5.0, 10.0, 10.05, 15.0]
    row = table[10.0]
    assert len(row) == 169 and set(row) == set(CLASSES)  # the same 169 names, in HRC's grid order
    assert row["AA"] == 1.0 and row["72o"] == 0.0 and 0.0 <= row["A5s"] <= 1.0
    assert hrc_check.row_for(table, 10) is row and hrc_check.row_for(table, 10.04) is table[10.05]
    assert hrc_check.row_for(table, 12) is None


def test_parser_rejects_other_tables():
    with pytest.raises(ValueError):
        hrc_check.parse_hrc_csv("hand, 22, 33\n1, 0, 1\n")


def test_compare_counts_disagreements_and_mad():
    theirs = {c: 0.0 for c in CLASSES}
    theirs["AA"] = 1.0
    theirs["KK"] = 0.6
    theirs["72o"] = 0.49
    ours = [0] * len(CLASSES)
    i = {c: k for k, c in enumerate(CLASSES)}
    ours[i["AA"]] = 1
    ours[i["QQ"]] = 1  # we push, they fold
    ours[i["72o"]] = 1  # we push, they are just under the threshold: counts as a disagreement
    r = hrc_check.compare(ours, theirs, threshold=0.5, worst=10)
    assert r["n"] == 169
    assert r["we_only"] == ["QQ", "72o"] and r["they_only"] == ["KK"] and r["disagree"] == 3
    assert r["mad"] == pytest.approx((1.0 + 0.6 + 0.51) / 169)
    assert r["worst"][0] == ("QQ", 1, 0.0) and len(r["worst"]) == 3
    assert r["freq_ours"] == pytest.approx((6 + 6 + 12) / 1326)


def test_main_runs_end_to_end_on_a_fixture_zip(tmp_path, capsys):
    z = tmp_path / "fake_hrc.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(FIXTURE, hrc_check.PUSH_CSV)
        zf.write(FIXTURE, hrc_check.CALL_CSV)
    assert hrc_check.main(["--zip", str(z), "--depths", "5,10,15", "--worst", "3"]) == 0
    out = capsys.readouterr().out
    assert "| 5 |" in out and "| 10 |" in out and "| 15 |" in out and "totals over 3 depths" in out
