"""H8, the drill 12 fixes (docs/drills/prompt-drill-12.md, "H8"): one test or more per item that changed code or prompts.
States in kit J's shape are built by hand or by hyperion/drills/closure_gate_seat_template.py from the gate's dealer state,
as the kit's handout gives them (docs/drills/drill12/kitJ-README.md)."""
from __future__ import annotations

import importlib.util
import json
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DRILLS = ROOT / "hyperion" / "drills"
DRILL12 = ROOT / "docs" / "drills" / "drill12"
KIT_RULES = json.loads((DRILL12 / "rules_tonight.json").read_text())


def _tool(name: str):
    spec = importlib.util.spec_from_file_location(f"h8_{name}", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _read(rel: str) -> str:
    return (ROOT / rel).read_text()


def _flat(text: str) -> str:
    return " ".join(text.split())


# ---------------------------------------------------------------------------------------------- item 1
PROBE = r'''
import gc, sys
sys.path.insert(0, sys.argv[1])
from hyperion import ship
from hyperion.core.types import Rules
from hyperion.strategy.tables import quick_start
full, unfrozen = [0], [0]
real_unfreeze = gc.unfreeze
def count_unfreeze():
    unfrozen[0] += 1
    real_unfreeze()
gc.unfreeze = count_unfreeze
inside = [False]
def watch(phase, info):
    if phase == "start" and inside[0] and info["generation"] == 2:
        full[0] += 1
gc.callbacks.append(watch)
bot = ship.make_bot()
bot.new_table(Rules(), 0, 8)
f0 = gc.get_freeze_count()
unfrozen[0] = 0  # the import's own, which collects: setup time
keep = []
for i in range(70):
    keep.append({"table": i})  # a tracked object alive at this table start: the freeze takes it
    inside[0] = True
    with quick_start():
        bot.new_table(Rules(), i % 8, 8)
    inside[0] = False
print(full[0], unfrozen[0], gc.get_freeze_count() - f0)
'''


@pytest.mark.night
def test_a_table_start_never_collects_and_still_freezes():
    """One bot through 70 table starts: no full collection inside any, no gc.unfreeze, and what is alive at each still
    leaves the collector's reach (drill 12: one table in 16 ran both, 20-29 ms against kit J's 25 ms, four copies in one
    process)."""
    out = subprocess.run([sys.executable, "-I", "-c", PROBE, str(ROOT)], capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr[-2000:]
    full, unfrozen, frozen = (int(x) for x in out.stdout.split())
    assert full == 0 and unfrozen == 0, out.stdout
    assert frozen >= 70, out.stdout


@pytest.mark.night
def test_a_bots_first_table_start_leaves_it_unfrozen_except_the_first_in_a_process(monkeypatch):
    """A runner that builds a fresh bot per table never pins the old ones, with no collection to free them; the first start
    in a process freezes what it loaded, and a bot at its second table freezes as before."""
    from hyperion.strategy import hero

    calls = []
    monkeypatch.setattr(hero.gc, "freeze", lambda: calls.append(1))
    monkeypatch.setattr(hero, "_table_starts", 0)
    hero.table_freeze(False)
    assert len(calls) == 1  # the first in this process
    hero.table_freeze(False)
    hero.table_freeze(False)
    assert len(calls) == 1  # fresh bots
    hero.table_freeze(True)
    assert len(calls) == 2  # a bot on its second table


SLOW_BOT = r'''
import time
class Slow:
    """A table start that takes 40 ms one time in 16, as a periodic collection would."""
    n = 0
    def new_table(self, rules, seat, n):
        Slow.n += 1
        if Slow.n % 16 == 0:
            time.sleep(0.04)
def make():
    return Slow()
'''


def test_latency_table_start_fails_a_periodic_overrun_and_passes_the_ship_bot(tmp_path):
    """`tools/latency.py --table-start`: p99 and max against the budget; the exit code says so."""
    (tmp_path / "slow_bot_h8.py").write_text(SLOW_BOT)
    env = {"PYTHONPATH": str(tmp_path), "PATH": "/usr/bin:/bin"}

    def run(*args):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "latency.py"), "--table-start", *args], text=True,
                              capture_output=True, timeout=240, env=env)

    out = run("--bot", "slow_bot_h8:make", "--tables", "64", "--budget-ms", "25")
    assert out.returncode == 1 and "FAIL table start" in out.stdout and "max" in out.stdout, out.stdout + out.stderr
    out = run("--bot", "slow_bot_h8:make", "--tables", "64", "--budget-ms", "500")
    assert out.returncode == 0 and "OK table start" in out.stdout, out.stdout + out.stderr
    # two copies of the package in one process, each its own modules; a wide budget: this is the tool, not the box
    out = run("--tables", "16", "--copies", "2", "--budget-ms", "400")
    assert out.returncode == 0 and "copies 2" in out.stdout and "n=32" in out.stdout, out.stdout + out.stderr


@pytest.mark.night
def test_gate_table_start_report_states_p99_and_max_against_the_budget():
    gate = _tool("gate")
    fast = [0.3] * 200
    line, fail, warn = gate.table_start_report(fast, 25.0)
    assert "p99 0.30 ms" in line and "max 0.30 ms" in line and "budget 25 ms" in line and fail is None and warn is None
    assert "no --setup-budget-ms" in gate.table_start_report(fast, None)[0]
    line, fail, warn = gate.table_start_report([0.3] * 199 + [40.0], 25.0)
    assert fail is None and "max 40.00" in warn  # one start over: a warning
    line, fail, warn = gate.table_start_report(([0.3] * 15 + [40.0]) * 8, 25.0)
    assert "p99 40.00" in fail  # one in 16: the table start's own cost, drill 12's


