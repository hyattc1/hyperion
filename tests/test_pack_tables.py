"""tools/pack.py and tools/gate.py on the tables a recorded bot needs (batch 8's freeze).

Batch 8's R6 reads tables/extra/short_3b.json. pack.py shipped only the top level of tables/*.json, the specialist's
loader returned None in the package, and R6 silently did not play there: no import failed, no bot failed to build, the
gate passed. These tests hold the fix: the pack ships what the recorded bot needs, and exits 1 by name on a package
that lacks a table, whether the bot opens it at its build (seen by tools/table_probe.py's audit hook) or only at a later
table start (the probe's declared map)."""
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tools" / "pack.py"
GATE = ROOT / "tools" / "gate.py"
PROBE = ROOT / "tools" / "table_probe.py"
ENTRY = "from hyperion.ship import make_bot\n\nBOT = make_bot()\n"
R6_OFF = '{"short.three2": false, "short_strong": false}'


def run_pack(cwd: Path, *args: str):
    return subprocess.run([sys.executable, str(PACK), *args], cwd=cwd, capture_output=True, text=True, timeout=240)


def probe(root: Path, *args: str):
    import json

    r = subprocess.run([sys.executable, "-I", "-B", str(PROBE), str(root), *args], cwd=root.parent if root.parent.exists()
                       else None, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def top_level_tables(into: Path, leave_out=()) -> Path:
    """What the old pack shipped: tables/*.json, the subdirectories left out."""
    into.mkdir()
    for f in sorted((ROOT / "tables").glob("*.json")):
        if f.name not in leave_out:
            shutil.copy2(f, into / f.name)
    return into


@pytest.fixture
def entry(tmp_path) -> Path:
    (tmp_path / "agent.py").write_text(ENTRY)
    return tmp_path / "agent.py"


def test_the_pack_ships_the_table_r6_reads(tmp_path, entry):
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "extra/short_3b.json" in r.stdout
    with zipfile.ZipFile(tmp_path / "dist" / "submission.zip") as z:
        names = z.namelist()
    assert "tables/extra/short_3b.json" in names
    assert "tables/extra/short_3.json" not in names  # needs, not the whole directory: short.three is off


def test_the_old_tables_fail_the_pack_by_name(tmp_path, entry):
    """The old package's tables exactly: the top level, no extra/. It built, imported and zipped before; now exit 1."""
    old = top_level_tables(tmp_path / "old")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null", "--tables-dir", str(old))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "FAIL" in r.stdout and "extra/short_3b.json" in r.stdout
    assert not (tmp_path / "dist" / "submission.zip").exists()


def test_a_bot_that_does_not_read_the_table_does_not_need_it(tmp_path, entry):
    old = top_level_tables(tmp_path / "old")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null", "--tables-dir", str(old),
                 "--dials", R6_OFF)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "short_3b" not in r.stdout


@pytest.mark.parametrize("table", ["known_m1s2x0u1.json", "auction_bid.json"])
def test_a_lazily_loaded_table_fails_the_pack_by_name(tmp_path, entry, table):
    """Neither is opened by a build or a plain table's start, only by a three-card or an auction table's: the opens alone
    would miss them, and the declared map catches them."""
    assert table not in probe(ROOT)["opened"]  # lazy: if it stops being lazy this test proves nothing
    tabs = top_level_tables(tmp_path / "tabs", leave_out=(table,))
    shutil.copytree(ROOT / "tables" / "extra", tabs / "extra")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null", "--tables-dir", str(tabs))
    assert r.returncode == 1, r.stdout + r.stderr
    assert table in r.stdout


def test_a_lazy_table_behind_a_dial_that_is_off_is_not_needed(tmp_path, entry):
    tabs = top_level_tables(tmp_path / "tabs", leave_out=("known_m1s2x0u1.json",))
    shutil.copytree(ROOT / "tables" / "extra", tabs / "extra")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null", "--tables-dir", str(tabs),
                 "--dials", '{"hero.known_cards": ""}')
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_table_no_tree_holds_fails_the_pack(tmp_path, entry):
    """The dial names a file that exists nowhere: the specialist's loader records the None and the pack says so."""
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null",
                 "--dials", '{"short.three2_file": "nosuch"}')
    assert r.returncode == 1, r.stdout + r.stderr
    assert "short_nosuch" in r.stdout


def test_the_specialist_records_a_missing_table_and_keeps_playing():
    """In a tournament a missing table must not kill the bot (it still plays F's route), but the None is on record."""
    from hyperion.strategy import short

    short._TABLES.pop("nosuch", None)
    short.MISSING.pop("nosuch", None)
    assert short._load("nosuch") is None
    assert "nosuch" in short.MISSING and "short_nosuch.json" in short.MISSING["nosuch"]
    assert short._load("hu") is not None and "hu" not in short.MISSING
    short._TABLES.pop("nosuch", None)
    short.MISSING.pop("nosuch", None)


def test_the_probe_reports_what_a_package_lacks(tmp_path):
    pkg = tmp_path / "pkg"
    shutil.copytree(ROOT / "hyperion", pkg / "hyperion", ignore=shutil.ignore_patterns("__pycache__"))
    top_level_tables(pkg / "tables")
    got = probe(pkg)
    assert "extra/short_3b.json" in got["lacking"]
    assert got["specialist_missing"]  # the loader's own record agrees
    shutil.copytree(ROOT / "tables" / "extra", pkg / "tables" / "extra")
    got = probe(pkg)
    assert got["lacking"] == [] and got["specialist_missing"] == {}
    assert "extra/short_3b.json" in got["opened"] and "auction_bid.json" in got["declared"]


def test_a_stripped_zip_fails_the_gate_before_any_table(tmp_path, entry):
    """A zip the pack would refuse (made by hand, or edited after) never reaches the gate's tables."""
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null")
    assert r.returncode == 0, r.stdout + r.stderr
    src = tmp_path / "dist" / "submission.zip"
    bad = tmp_path / "stripped.zip"
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            if n != "tables/extra/short_3b.json":
                zout.writestr(n, zin.read(n))
    g = subprocess.run([sys.executable, str(GATE), str(bad), "--kit", "b", "--entry", "agent.py", "--tables", "2"],
                       cwd=tmp_path, capture_output=True, text=True, timeout=300)
    assert g.returncode == 1, g.stdout + g.stderr
    assert "GATE FAIL" in g.stdout and "extra/short_3b.json" in g.stdout
    assert "tables  package" not in g.stderr  # failed before playing
