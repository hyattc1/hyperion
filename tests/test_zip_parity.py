"""tools/zip_parity.py: the zip plays as the source does, decision for decision, and the check cannot pass vacuously.

A real package of the recorded bot, then copies of its zip edited after the pack: the table R6 reads taken out, and a bot
changed in one decision. The pack would refuse the first, so these zips are made by hand."""
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "tools" / "pack.py"
PARITY = ROOT / "tools" / "zip_parity.py"
ENTRY = "from hyperion.ship import make_bot\n\nBOT = make_bot()\n"
# appended to the zip's hyperion/ship.py: the zip's bot folds its 20th decision of a table if folding is legal
ONE_DECISION = """

_make_bot = make_bot


def make_bot(*args, **kw):  # noqa: F811
    from .core.types import Action, ActionKind

    bot = _make_bot(*args, **kw)
    act, seen = bot.act, [0]

    def changed(obs):
        a = act(obs)
        seen[0] += 1
        return Action.fold() if seen[0] == 20 and a.kind is not ActionKind.FOLD else a

    bot.act = changed
    return bot
"""


@pytest.fixture(scope="module")
def packed(tmp_path_factory) -> Path:
    d = tmp_path_factory.mktemp("pack")
    (d / "agent.py").write_text(ENTRY)
    r = subprocess.run([sys.executable, str(PACK), "--entry", "agent.py", "--out", "dist", "--slim", "--night", "/dev/null"],
                       cwd=d, capture_output=True, text=True, timeout=240)
    assert r.returncode == 0, r.stdout + r.stderr
    return d / "dist" / "submission.zip"


def parity(zip_path: Path, *args: str):
    out = zip_path.parent / (zip_path.stem + ".parity.json")
    r = subprocess.run([sys.executable, str(PARITY), str(zip_path), "--workers", "2", "--json", str(out), *args],
                       cwd=zip_path.parent, capture_output=True, text=True, timeout=600)
    return r, json.loads(out.read_text()) if out.exists() else None


def edited(src: Path, into: Path, drop=(), append: dict | None = None) -> Path:
    with zipfile.ZipFile(src) as zin, zipfile.ZipFile(into, "w", zipfile.ZIP_DEFLATED) as zout:
        for n in zin.namelist():
            if n in drop:
                continue
            data = zin.read(n)
            if append and n in append:
                data += append[n].encode()
            zout.writestr(n, data)
    return into


def test_the_packed_zip_plays_as_the_source_and_every_route_fires(packed):
    r, rep = parity(packed, "--quick")
    assert r.returncode == 0, r.stdout + r.stderr
    assert "PARITY PASS" in r.stdout
    assert rep["total"]["decisions"] > 100 and rep["mismatches"] == []
    assert set(rep["routes"]) == {"strong", "hu", "3b"}
    for route in rep["routes"]:
        assert rep["fired"][route] > 0, route  # not vacuous: each route played decisions, on the source's own count
    assert "extra/short_3b.json" in rep["opened"]


def test_a_zip_without_r6s_table_fails(packed, tmp_path):
    bad = edited(packed, tmp_path / "no_3b.zip", drop=("tables/extra/short_3b.json",))
    r, rep = parity(bad, "--quick")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "PARITY FAIL" in r.stdout and "extra/short_3b.json" in r.stdout
    # the play itself tells them apart too, without the static check: R6's counter on the source against the zip's
    assert rep["mismatches"], rep["fails"]


def test_one_changed_decision_fails(packed, tmp_path):
    bad = edited(packed, tmp_path / "changed.zip", append={"hyperion/ship.py": ONE_DECISION})
    r, rep = parity(bad, "--quick", "--only", "exploit2_hu")
    assert r.returncode == 1, r.stdout + r.stderr
    assert rep["mismatches"] and "source" in rep["mismatches"][0] and "zip" in rep["mismatches"][0]


def test_a_route_that_never_fired_fails_even_with_no_mismatch(packed):
    """Heads-up only: the specialist plays, the strong route and R6 cannot, so the run proves nothing about them."""
    r, rep = parity(packed, "--quick", "--only", "exploit2_hu")
    assert rep["mismatches"] == []
    assert r.returncode == 1, r.stdout + r.stderr
    assert "never fired" in r.stdout and "3b" in r.stdout


def test_the_twists_play_as_the_source_only_with_their_own_tables(packed, tmp_path):
    """Found by this tool on batch 8's first zip: packed without tonight's rules, a zip had no tables/generic/, so
    hero.twin_preflop's table was None on every twist and the zip played them apart from the source, silently."""
    r, rep = parity(packed, "--only", "realistic", "--scale", "0.34")
    assert rep["mismatches"] == [] and rep["total"]["variant_decisions"] > 0, r.stdout
    with zipfile.ZipFile(packed) as z:
        drop = tuple(n for n in z.namelist() if n.startswith("tables/generic/"))
    assert drop
    bad = edited(packed, tmp_path / "no_generic.zip", drop=drop)
    r, rep = parity(bad, "--only", "realistic", "--scale", "0.34")
    assert r.returncode == 1 and "generic" in r.stdout, r.stdout + r.stderr
    assert rep["mismatches"], rep["fails"]  # the play itself tells them apart, not only the table check


def test_the_timing_tool_times_the_zips_bot_and_measures_the_slowdown(packed):
    timing = ROOT / "tools" / "zip_timing.py"
    out = packed.parent / "t.json"
    r = subprocess.run([sys.executable, str(timing), str(packed), "--k", "3", "--scale", "0.05", "--json", str(out)],
                       cwd=packed.parent, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    rep = json.loads(out.read_text())
    assert rep["all"]["decisions"] > 0 and rep["setup_ms"]["total"]["n"] > 0 and rep["all"]["max_us"] > 0
    assert 2.9 < rep["work_clock_ms"] / rep["work_cpu_ms"] < 3.1, rep  # the bot's clock reads 3x its CPU time
    assert "errors" not in rep


def test_the_gate_can_put_the_package_on_a_slower_clock(packed):
    gate = ROOT / "tools" / "gate.py"
    r = subprocess.run([sys.executable, str(gate), str(packed), "--kit", "b", "--entry", "agent.py", "--tables", "1", "--mode",
                        "measure", "--max-tmo-pct", "100", "--slow", "3"], cwd=packed.parent, capture_output=True, text=True,
                       timeout=300)
    assert "package import" in r.stdout and "exc" in r.stdout, r.stdout + r.stderr
    secs = float(r.stdout.split("package import ")[1].split()[0])
    assert secs > 0.6, r.stdout  # the import and build, three times what it takes on this box's own clock


def test_a_bot_that_never_sleeps_plays_the_same_table(packed):
    """--spin changes how the process waits, nothing else."""
    timing = ROOT / "tools" / "zip_timing.py"
    res = []
    for extra in ((), ("--spin",)):
        out = packed.parent / f"s{len(extra)}.json"
        r = subprocess.run([sys.executable, str(timing), str(packed), "--scale", "0.05", "--json", str(out), *extra],
                           cwd=packed.parent, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        res.append(json.loads(out.read_text()))
    assert res[0]["all"]["decisions"] > 0 and "errors" not in res[1]
    assert abs(res[0]["all"]["decisions"] - res[1]["all"]["decisions"]) < res[0]["all"]["decisions"] / 5
