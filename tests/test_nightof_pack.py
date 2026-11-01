"""tools/pack.py: vendors hyperion + tables + entry, verifies the import from elsewhere, zips, hashes,
logs to NIGHT.md. Run as a subprocess the way the night uses it, plus the two pure helpers."""
import hashlib
import importlib.util
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tools" / "pack.py"
ENTRY = ('"""fake kit B entry: Hero behind the kit B adapter."""\n'
         "from hyperion.drills.adapter import make_kit_b_module\n"
         "from hyperion.strategy.hero import make_bot\n\n"
         "decide, on_table_start, on_hand_end = make_kit_b_module(make_bot())\n")
NIGHT = ("# NIGHT\n\nT0: 00:00\n\n## Submissions\n\n"
         "| minute | file | sha256 | size / import | what changed | verified by |\n|---|---|---|---|---|---|\n\n## Windows\n")


def load_pack():
    spec = importlib.util.spec_from_file_location("pack_under_test", PACK)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_pack(cwd: Path, *args: str):
    return subprocess.run([sys.executable, str(PACK), *args], cwd=cwd, capture_output=True, text=True, timeout=240)


def test_pack_builds_verifies_zips_and_logs(tmp_path):
    sub = tmp_path / "submission"
    sub.mkdir()
    (sub / "agent.py").write_text(ENTRY)
    (sub / "adapter.py").write_text("X = 1\n")
    (tmp_path / "NIGHT.md").write_text(NIGHT)
    r = run_pack(tmp_path, "--entry", "submission/agent.py", "--out", "dist", "--slim",
                 "--extra", "submission/adapter.py", "--note", "cheap bot")
    assert r.returncode == 0, r.stdout + r.stderr
    dest, zpath = tmp_path / "dist" / "submission", tmp_path / "dist" / "submission.zip"
    assert (dest / "agent.py").exists() and (dest / "adapter.py").exists()
    assert (dest / "hyperion" / "strategy" / "hero.py").exists() and (dest / "tables" / "preflop_rank.json").exists()
    assert not (dest / "tables" / "variants").exists(), "default tables only"
    assert not (dest / "hyperion" / "drills" / "fakekits").exists() and not (dest / "hyperion" / "sim" / "bestiary.py").exists()
    assert not list(dest.rglob("tests")) and not any("__pycache__" in n or n.endswith(".pyc") for n in zipfile.ZipFile(zpath).namelist())
    sha = hashlib.sha256(zpath.read_bytes()).hexdigest()
    assert sha in r.stdout and "import   ok" in r.stdout and f"hyperion from {dest}" in r.stdout
    names = zipfile.ZipFile(zpath).namelist()
    assert "agent.py" in names and "hyperion/__init__.py" in names and "tables/meta.json" in names
    night = (tmp_path / "NIGHT.md").read_text()
    rows = [line for line in night.splitlines() if sha in line]
    assert len(rows) == 1 and "| cheap bot |" in rows[0] and "import 0." in rows[0]
    assert night.index(sha) < night.index("## Windows"), "row goes under Submissions, not at the end"


def test_pack_without_slim_keeps_fakekits_and_skips_night_when_absent(tmp_path):
    (tmp_path / "agent.py").write_text(ENTRY)
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "out")
    assert r.returncode == 0, r.stdout + r.stderr
    dest = tmp_path / "out" / "submission"
    assert (dest / "hyperion" / "drills" / "fakekits" / "kit_b" / "kit.py").exists()
    assert (dest / "hyperion" / "sim" / "bestiary.py").exists()
    assert not (tmp_path / "NIGHT.md").exists() and "NIGHT.md row" not in r.stdout


def test_pack_fails_on_a_broken_import(tmp_path):
    (tmp_path / "agent.py").write_text("import no_such_module_xyz\n")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist")
    assert r.returncode == 1 and "import   FAIL" in r.stdout and "no_such_module_xyz" in r.stdout
    assert not (tmp_path / "dist" / "submission.zip").exists()


def test_pack_fails_on_a_slow_import(tmp_path):
    (tmp_path / "agent.py").write_text("import time\ntime.sleep(0.3)\n")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--import-budget", "0.1")
    assert r.returncode == 1 and "budget" in r.stdout


def test_tables_dir_is_packaged_whole(tmp_path):
    td = tmp_path / "tabs"
    td.mkdir()
    for name in ("preflop_rank.json", "hole_classes.json"):
        (td / name).write_text("{}")
    (tmp_path / "agent.py").write_text("X = 1\n")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--tables-dir", str(td))
    assert r.returncode == 0, r.stdout + r.stderr
    assert (tmp_path / "dist" / "submission" / "tables" / "hole_classes.json").exists()
    assert "entry does not import hyperion" in r.stdout


def test_minute_and_night_row_helpers(tmp_path):
    pack = load_pack()
    assert pack.minute_since_t0("T0: 18:00", datetime(2026, 11, 6, 18, 12)) == "12"
    assert pack.minute_since_t0("T0 23:50:00 EST repo abc", datetime(2026, 11, 7, 0, 5)) == "15"
    assert pack.minute_since_t0("no t-zero here", datetime(2026, 11, 6, 7, 5)) == "07:05"
    night = tmp_path / "N.md"
    night.write_text("# x\n\n## Windows\nstuff\n")
    pack.append_night_row(night, "| 1 | a.zip | s | 1 KB | n | |")
    text = night.read_text()
    assert "## Submissions" in text and text.rstrip().endswith("| 1 | a.zip | s | 1 KB | n | |")
    pack.append_night_row(night, "| 2 | b.zip | t | 1 KB | n | |")
    lines = night.read_text().splitlines()
    assert lines.index("| 2 | b.zip | t | 1 KB | n | |") == lines.index("| 1 | a.zip | s | 1 KB | n | |") + 1
    assert lines.count("## Submissions") == 1


def test_the_active_variant_tables_are_vendored_without_a_flag(tmp_path):
    """Drill 6 shipped without tables/variants/toss_or_holdem because --tables-dir was not passed."""
    pack = load_pack()
    (tmp_path / "rules_tonight.json").write_text('{"hole_cards": 3, "extras": {"variant": "toss_or_holdem", '
                                                 '"discard_street": 1, "keep": 2}}')
    (tmp_path / "agent.py").write_text("X = 1\n")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--extra", "rules_tonight.json")
    assert r.returncode == 0, r.stdout + r.stderr
    tables = tmp_path / "dist" / "submission" / "tables"
    assert (tables / "variants" / "toss_or_holdem" / "meta.json").exists() and (tables / "preflop_rank.json").exists()
    assert not (tables / "variants" / "omaha_four").exists()
    assert "tables   default + variants/toss_or_holdem" in r.stdout
    entry, extras = tmp_path / "agent.py", []
    assert pack.find_rules(entry, extras, None) == tmp_path / "rules_tonight.json"  # beside the entry
    assert pack.active_variant(tmp_path / "rules_tonight.json") == ("toss_or_holdem", True)
    (tmp_path / "rules_bounty.json").write_text('{"extras": {"variant": "bounty"}}')
    assert pack.active_variant(tmp_path / "rules_bounty.json") == ("bounty", False)
    what = pack.build(tmp_path / "b", entry, [], False, None, "bounty")
    assert what == "default"  # no set needed, none shipped, no warning
    what = pack.build(tmp_path / "c", entry, [], False, None, "made_up_three_card", needs_variant=True)
    assert "WARN" in what and "label tables" in what
