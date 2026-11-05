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


# ---------------------------------------------------------------------------------------------- item 2
def _seat_module():
    spec = importlib.util.spec_from_file_location("h8_seat", DRILLS / "closure_gate_seat_template.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def alarm():
    old = signal.getsignal(signal.SIGALRM)
    yield
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, old)


@pytest.fixture
def clean_path(monkeypatch):
    """The entry pins its folder onto sys.path and its modules into hyperion.drills.adapter's lists: undone after."""
    from hyperion.drills import adapter as A

    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.setattr(A, "_KEEP", list(A._KEEP))
    monkeypatch.setattr(A, "_PINNED", dict(A._PINNED))
    yield


def _entry(tmp_path: Path, tables_at_once: int = 1):
    """submission/ for kit J: the closure template as bot.py, the drill 12 player's adapter, kit J's rules; loaded by the
    gate seat's copy of the kit's loader."""
    d = tmp_path / f"sub{tables_at_once}"
    d.mkdir()
    text = (DRILLS / "closure_entry_template.py").read_text()
    assert "TABLES_AT_ONCE = 1\n" in text
    (d / "bot.py").write_text(text.replace("TABLES_AT_ONCE = 1\n", f"TABLES_AT_ONCE = {tables_at_once}\n"))
    shutil.copy(DRILL12 / "adapter.py", d / "adapter.py")
    (d / "rules_tonight.json").write_text(json.dumps(KIT_RULES))
    return _seat_module().load_entry(str(d / "bot.py"))


def _table(mod, tags, me):
    return mod._T(me, tags, 2000, tuple(tuple(b) for b in KIT_RULES["blind_levels"]), 25, 200,
                  tuple(KIT_RULES["payouts"]))


def _view(mod, tags, me_i, hand, recap=()):
    """A preflop decision in kit J's shape: blinds posted by tags[0] and tags[1], we are tags[me_i], everyone before us
    folded. Amounts in big blinds at level 1."""
    assert me_i >= 2
    players = []
    for i, t in enumerate(tags):
        put = (0.5, 1.0)[i] if i < 2 else 0.0
        players.append(mod._P(t, 100.0 - put, 100.0, 60.0, put, put, "F" if 2 <= i < me_i else "L"))
    log = f"{tags[0]}S0.5 {tags[1]}B1 " + " ".join(f"{t}F" for t in tags[2:me_i])
    hole = (1 << (13 * 3 + 12)) | (1 << (13 * 2 + 12))  # As Ah
    return mod._V(hand, 1, 20, 25 - (hand - 1) % 25, 0, hole, 0, 1.5, 1.0, 1.0, 99.0, me_i, 7, tuple(players), log.strip(),
                  tuple(recap))


TAGS_A = ("qx", "mv", "tk", "ab", "cd", "ef", "gh", "ij")
TAGS_B = ("zz", "yy", "xx", "ww", "vv", "uu", "ss", "rr")


def _done(mod, tags, hand, me_i):
    """The recap of a hand we folded, the blinds' fold and call settled."""
    net = tuple((t, (-0.5 if i == 0 else 0.5 if i == 1 else 0.0)) for i, t in enumerate(tags))
    log = f"{tags[0]}S0.5 {tags[1]}B1 " + " ".join(f"{t}F" for t in tags[2:]) + f" {tags[0]}F"
    return mod._R(hand, 20, log, 0, (), net, (), 0.0)


@pytest.mark.night
def test_closure_entry_loads_as_the_kit_loads_it_and_plays(tmp_path, clean_path):
    """Right after the kit's loader the folder is off sys.path and `adapter` out of sys.modules; sit_down returns the closure;
    the closure takes the recap inside the decide and answers one of the kit's strings; the error line is empty."""
    mod = _entry(tmp_path)
    assert "adapter" not in sys.modules
    decide = mod.sit_down(_table(mod, TAGS_A, "ab"))
    assert callable(decide)
    answers = [decide(_view(mod, TAGS_A, 3, 1))]
    answers.append(decide(_view(mod, TAGS_A, 3, 2, recap=(_done(mod, TAGS_A, 1, 3),))))
    for a in answers:
        assert a in ("f", "c") or (a[0] == "r" and float(a[1:]) > 0), answers
    assert not +mod.ERRORS, mod.ERRORS


@pytest.mark.night
def test_closure_entry_counts_a_net_read_wrong_and_rules_that_differ(tmp_path, clean_path):
    mod = _entry(tmp_path)
    bad = _table(mod, TAGS_A, "ab")._replace(points=(16, 10, 6, 3, 1, 0, -1, -3))
    decide = mod.sit_down(bad)
    assert mod.ERRORS["rules_points"] == 1
    decide(_view(mod, TAGS_A, 3, 1))
    r = _done(mod, TAGS_A, 1, 3)
    wrong = r._replace(net=tuple((t, n + 1.0 if t == "qx" else n) for t, n in r.net))  # does not sum to 0
    decide(_view(mod, TAGS_A, 3, 2, recap=(wrong,)))
    assert mod.ERRORS["deltas_sum"] == 1


@pytest.mark.night
def test_closure_seat_builds_kit_j_state_and_answers(alarm, monkeypatch):
    monkeypatch.delenv("GATE_VARIANT", raising=False)
    seat_mod = _seat_module()
    fake = type("M", (), {"sit_down": staticmethod(lambda table: (lambda v: "c"))})
    seat = seat_mod.Seat(fake, None)
    seat.start(3, 8, 2000, (10, 20))
    st = {"seat": 3, "stacks": [1990, 1980, 2000, 2000, 2000, 2000, 2000, 2000], "bets": [10, 20, 0, 0, 0, 0, 0, 0],
          "in_hand": [True] * 8, "blinds": (10, 20), "street": 0, "button": 7, "hand_no": 0, "pot": 0, "to_call": 20,
          "min_raise": 40, "max_raise": 2000, "legal": {"fold", "call", "raise"}, "hole": (48, 45), "board": (),
          "posts": [(0, "sb", 10), (1, "bb", 20)], "history": [(2, "fold", 0, 0, 0)]}
    v = seat.native(st)
    assert v.bb == 20 and v.hand == 1 and v.level == 1 and v.owe == 1.0 and v.min_raise == 1.0 and v.max_raise == 99.0
    assert v.players[v.me].tag == "ab" and v.players[0].tag == "qx" and v.players[0].in_pot == 0.5  # clockwise from the SB
    assert v.log == "qxS0.5 mvB1 tkF" and v.pot == 1.5
    assert v.hole == (1 << 12) | (1 << (13 + 11))  # ours 48 Ac, 45 Kd: bit = 13 * suit + rank - 2
    assert seat.parse("f", st) == ("fold", 0) and seat.parse("c", st) == ("call", 20)
    assert seat.parse("r1000000", st) == ("raise", 2000) and seat.parse("r0.1", st) == ("raise", 40)
    assert seat.parse("r3", st) == ("raise", 80)  # owe + 3 bb: a raise-by on top of the call
    for bad in ("r0", "r-3", "rnan", "rinf", "x", None, 5):
        with pytest.raises((ValueError, TypeError)):
            seat.parse(bad, st)
    seat.end(0, -10, {"deltas": [-10, 10, 0, 0, 0, 0, 0, 0], "history": [(2, "fold", 0, 0, 0)], "posts": st["posts"]})
    v2 = seat.native({**st, "hand_no": 1, "button": 0, "history": []})
    assert len(v2.recap) == 1 and v2.recap[0].hand == 1 and dict(v2.recap[0].net)["mv"] == 0.5
    assert seat.native({**st, "hand_no": 1, "button": 0, "history": []}).recap == ()  # delivered once


@pytest.mark.night
def test_closure_seat_reports_stops_only_when_the_engine_plays_the_twist(alarm, monkeypatch):
    """Drill 12: on plain rules the seat's floors fired, with no stop in the engine. Without --variant nobody has a stop."""
    seat_mod = _seat_module()
    fake = type("M", (), {"sit_down": staticmethod(lambda table: (lambda v: "c"))})
    st = {"seat": 3, "stacks": [2000] * 8, "bets": [0] * 8, "in_hand": [True] * 8, "blinds": (10, 20), "street": 0,
          "button": 7, "hand_no": 0, "pot": 0, "to_call": 0, "legal": {"check"}, "hole": (48, 45), "board": ()}
    monkeypatch.delenv("GATE_VARIANT", raising=False)
    plain = seat_mod.Seat(fake, None)
    plain.start(3, 8, 2000, (10, 20))
    assert all(p.floor == 0.0 for p in plain.native(st).players)
    monkeypatch.setenv("GATE_VARIANT", "submission/tonight.py:variant")
    twist = seat_mod.Seat(fake, None)
    twist.start(3, 8, 2000, (10, 20))
    assert all(p.floor == 60.0 for p in twist.native(st).players)  # 1,200 chips, 60 bb at 20


def _busy(ms):
    end = time.perf_counter() + ms / 1000.0
    while time.perf_counter() < end:
        pass


@pytest.mark.night
def test_closure_seat_runs_the_kits_clock(alarm):
    """Past the table-start limit the table is on autopilot; past the hard stops the call is cut and counted; a bot that
    swallows the kit's stop and runs on is an error."""
    seat_mod = _seat_module()
    v = type("V", (), {"owe": 1.0})()

    class Slow:
        @staticmethod
        def sit_down(table):
            _busy(30)
            return lambda v: "c"

    seat = seat_mod.Seat(Slow, None)
    seat.start(0, 8, 2000, (10, 20))
    assert seat.gate_counts == {"table_sat_out": 1} and seat.call(v) == "f"

    class Hard:
        @staticmethod
        def sit_down(table):
            def decide(v):
                _busy(80)
                return "c"
            return decide

    seat = seat_mod.Seat(Hard, None)
    seat.start(0, 8, 2000, (10, 20))
    assert seat.call(v) == "f" and seat.gate_counts == {"decide_hard_stop": 1}

    class Swallow:
        @staticmethod
        def sit_down(table):
            def decide(v):
                try:
                    _busy(80)
                except BaseException:  # noqa: BLE001
                    pass
                return "c"
            return decide

    seat = seat_mod.Seat(Swallow, None)
    seat.start(0, 8, 2000, (10, 20))
    with pytest.raises(RuntimeError, match="caught the kit's hard stop"):
        seat.call(v)


def test_the_gate_plays_the_packed_closure_entry_with_the_twist_as_a_hooks_file(tmp_path):
    """tools/gate.py with the closure seat on the packed template and the drill's adapter with its stop patch on: the
    package loads through the seat's load_entry, the stop is in the engine and the floors in the state, one table is clean,
    and the template is not vendored into the package."""
    from hyperion.sim import bestiary as B
    from hyperion.tablegen import rules_from_dict

    gate, pack = _tool("gate"), _tool("pack")
    d = tmp_path / "sub"
    d.mkdir()
    shutil.copy(DRILLS / "closure_entry_template.py", d / "bot.py")
    shutil.copy(DRILL12 / "adapter.py", d / "adapter.py")
    (d / "rules_tonight.json").write_text(json.dumps(KIT_RULES))
    (d / "stop_patch.txt").write_text("A\n")
    dest = tmp_path / "pkg"
    pack.build(dest, d / "bot.py", [d / "adapter.py", d / "rules_tonight.json", d / "stop_patch.txt"], True, None)
    pack.keep_built_modules(dest, *pack.record_bot(dest, None, None))  # as pack's main does after a --slim build
    assert not (dest / "hyperion" / "drills" / "closure_entry_template.py").exists()
    spec = importlib.util.spec_from_file_location("h8_tonight", DRILL12 / "tonight.py")
    tonight = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tonight)
    cfg = _cfg(gate, tmp_path, dest, variant="tonight.py:variant")
    pkg, _ = gate.play(cfg, B.field_names("realistic"), 1, 3, rules_from_dict(KIT_RULES), tonight.variant(), "measure", "sim")
    assert pkg.fatal is None, pkg.notes
    assert pkg.decisions > 10 and pkg.stats.exceptions == 0 and pkg.stats.illegal == 0, (pkg.stats.last_error, pkg.notes)
    assert pkg.lifecycle == 0, pkg.notes
    assert not pkg.counts.get("table_sat_out"), pkg.counts


def _closure_package(folder: Path, every: int = 0) -> None:
    """A tiny closure bot: sit_down sleeps 40 ms every `every` calls; decide checks or folds."""
    folder.mkdir()
    (folder / "bot.py").write_text(
        "import time\nN = [0]\ndef sit_down(table):\n    N[0] += 1\n"
        f"    if {every} and N[0] % {every or 1} == 0:\n        time.sleep(0.04)\n"
        "    def decide(v):\n        return 'c' if v.owe <= 0 else 'f'\n    return decide\n")


def _cfg(gate, tmp_path, pkg, variant=None):
    shutil.copy(DRILLS / "closure_gate_seat_template.py", tmp_path / "gate_seat.py")
    scratch = tmp_path / "cwd"
    scratch.mkdir(exist_ok=True)
    return gate.Config(pkg=pkg, entry="bot.py", kit="seat", kit_dir=Path("-"), scratch=str(scratch),
                       seat_file=tmp_path / "gate_seat.py", variant=variant)


def test_the_gate_times_table_starts_through_the_entry_in_a_process_of_their_own(tmp_path):
    from hyperion.tablegen import rules_from_dict

    gate = _tool("gate")
    _closure_package(tmp_path / "pkg", every=16)
    times = gate.table_starts(_cfg(gate, tmp_path, tmp_path / "pkg"), rules_from_dict(KIT_RULES), 64)
    assert len(times) == 64 and sum(1 for t in times if t >= 39) == 4, times
    assert gate.table_start_report(times, 25.0)[1] is not None


# ---------------------------------------------------------------------------------------------- item 3
@pytest.mark.night
def test_prompt_05_has_a_section_for_what_a_stack_can_lose():
    """Short, and general: the list comes first, then the two checks, then the drill's kept patch and the keep rule."""
    text = _read("docs/prompts/05-variant-patch.md")
    head = "## What a stack can lose moved"
    assert head in text
    sec = text[text.index(head):text.index("## Betting structure moved")]
    flat = _flat(sec)
    assert len(sec.splitlines()) <= 16
    assert "what makes a normal fold or a normal call wrong under tonight's rule" in flat
    for words in ("past the point of no return", "a stack you cannot fully lose", "elimination threshold",
                  "the keep rule", "TWIST_PATCH", "StopBot"):
        assert words.lower() in flat.lower(), words
    assert "class StopBot" in (DRILL12 / "adapter.py").read_text()


