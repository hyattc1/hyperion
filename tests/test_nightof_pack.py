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
    from hyperion import ship

    assert len(rows) == 1 and f"| {ship.SHIP}: cheap bot |" in rows[0] and "import 0." in rows[0]
    assert night.index(sha) < night.index("## Windows"), "row goes under Submissions, not at the end"
    assert f"bot      {ship.SHIP}  dials {{}}" in r.stdout and "bot built in" in r.stdout


def test_pack_records_the_bot_and_dials_it_packed(tmp_path):
    """--bot / --dials go into the package's hyperion/ship.py (the gate reads them there); the repo's copy is untouched."""
    import ast

    spec = importlib.util.spec_from_file_location("ship_under_test", ROOT / "hyperion" / "ship.py")
    ship = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ship)
    (tmp_path / "agent.py").write_text("from hyperion.ship import make_bot\nBOT = make_bot()\n")
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist", "--bot", "hero",
                 "--dials", '{"preflop.three_bet_frac": 0.05}')
    assert r.returncode == 0, r.stdout + r.stderr
    rec = ship.read_record(tmp_path / "dist" / "submission" / "hyperion" / "ship.py")
    assert rec == ("hero", {"preflop.three_bet_frac": 0.05}), rec
    assert ship.read_record(ROOT / "hyperion" / "ship.py") == (ship.SHIP, ship.DIALS)
    ast.parse((tmp_path / "dist" / "submission" / "hyperion" / "ship.py").read_text())
    bad = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist2", "--bot", "nobody")
    assert bad.returncode != 0 and "BUILDERS" in bad.stdout + bad.stderr
    broken = run_pack(tmp_path, "--entry", "agent.py", "--out", "dist3", "--dials", '{"preflop.open_frac": 0.3}')
    assert broken.returncode == 1 and "import   FAIL" in broken.stdout, broken.stdout


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


SHIP_ENTRY = ('"""Any kit: the ship bot."""\nfrom hyperion import ship\n\nBOT = ship.make_bot()\n')
PLAY_EVERY_SHIP_BOT = r'''
import sys
sys.path.insert(0, sys.argv[1])
from hyperion import ship
from hyperion.core.types import Rules
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills import variants as V
from hyperion.sim.engine import BotStats, play_table
for name in ("composite", "hybrid3_x", "hybrid3", "hero", "cheap"):
    for rules, hooks in [(Rules(max_hands=30), None)] + [(V.get(v).rules, V.get(v).new_hooks()) for v in
                                                        ("short_deck", "omaha_four", "toss_or_holdem", "bounty")]:
        st = [BotStats(str(i)) for i in range(rules.n_players)]
        play_table([ship.make_bot(name, {}, seed=1)] + [CheapBot() for _ in range(rules.n_players - 1)],
                   rules, seed=3, mode="model", stats=st, variant=hooks)
        assert st[0].exceptions == 0 and st[0].safe_err == 0, (name, st[0].last_error)
mods = sorted(m for m in sys.modules if m.startswith("hyperion.sim.") and m not in ("hyperion.sim.engine",))
assert all(m.startswith(sys.argv[1]) for m in [getattr(sys.modules[m], "__file__", "") or sys.argv[1] for m in mods])
print("ok", mods)
'''


def test_slim_drops_the_opponents_and_every_ship_bot_still_builds_and_plays(tmp_path):
    """--slim leaves out the field bots, the judges (elite3 above all), the exploiter, the outside builds, the aware
    opponents and every rival but rival 3 (rival 3's core is hybrid3_x's and the composite's base). Each ship bot is
    then built and played from the package alone in a fresh `python -I` elsewhere, plain and under four variants."""
    (tmp_path / "agent.py").write_text(SHIP_ENTRY)
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "out", "--slim")
    assert r.returncode == 0, r.stdout + r.stderr
    hyp = tmp_path / "out" / "submission" / "hyperion"
    assert not (hyp / "sim" / "field").exists() and not (hyp / "sim" / "aware.py").exists()
    assert sorted(p.name for p in (hyp / "sim" / "rivals").glob("*.py")) == ["__init__.py", "rival3.py"]
    names = zipfile.ZipFile(tmp_path / "out" / "submission.zip").namelist()
    for bad in ("elite", "outside_", "exploiter", "judge", "rival1", "rival2", "rival4", "rival5", "agent_", "night.py",
                "trackb", "aware.py", "bestiary.py"):
        assert not [n for n in names if bad in n.rsplit("/", 1)[-1]], bad
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    out = subprocess.run([sys.executable, "-I", "-B", "-c", PLAY_EVERY_SHIP_BOT, str(hyp.parent)], cwd=elsewhere,
                         capture_output=True, text=True, timeout=600)
    assert out.returncode == 0 and out.stdout.startswith("ok"), out.stdout + out.stderr[-3000:]
    assert "hyperion.sim.rivals.rival3" in out.stdout


def test_slim_keeps_a_rival_the_recorded_route_names(tmp_path):
    (tmp_path / "agent.py").write_text(SHIP_ENTRY)
    r = run_pack(tmp_path, "--entry", "agent.py", "--out", "out", "--slim", "--dials", '{"route": "post=hero,pre_hu=r2x"}',
                 "--import-budget", "60")  # rival 2 runs a Monte Carlo at import: 1.2 s quiet, over 5 s on a busy host
    assert r.returncode == 0, r.stdout + r.stderr
    rivals = tmp_path / "out" / "submission" / "hyperion" / "sim" / "rivals"
    assert sorted(p.name for p in rivals.glob("*.py")) == ["__init__.py", "rival2.py", "rival3.py"]
    assert "rival2.py: kept" in r.stdout and "import   ok" in r.stdout
