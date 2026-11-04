"""H5, drill 9's fixes (docs/drills/prompt-drill-9.md): the entry template pinned at import under a loader that unloads
before the Agent is built (kit G), its timed hand end stored and delivered at the next decision, the gate seat's
tagged rows and posts (a kit's per-street log round-trips through drill 9's own parser), the conformance report after
the warm-up, a table start inside a decision that builds nothing, and the night docs (the timing marker, --cand)."""
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.drills import conformance
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.cheapbot import CheapBot

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _state(hand_no=0, street=0, button=0, history=(), hole=(51, 47), seat=3):
    pre = street == 0
    n = 8
    return dict(hole=list(hole), board=[0, 9, 22, 33, 44][: (0, 3, 4, 5)[street]], street=street, seat=seat,
                button=button, stacks=[1990 if i == 1 else 1980 if i == 2 else 2000 for i in range(n)] if pre else
                [1900] * n, bets=[0, 10, 20, 0, 0, 0, 0, 0] if pre else [0] * n, in_hand=[True] * n,
                pot=0 if pre else 800, to_call=20 if pre else 0, min_raise=40 if pre else 20,
                max_raise=2000 if pre else 1900, legal=["fold", "call", "raise"] if pre else ["check", "raise"],
                hand_no=hand_no, blinds=(10, 20), history=list(history))


# ------------------------------------------------------------------ 1, 2: the entry template under kit G's loader

ADAPTER = '''from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked


def history(log):
    return []


class TonightAdapter(Adapter):
    """A dict state; each decision makes two imports nothing made at import."""

    def to_observation(self, st):
        import lazy_helper  # noqa: F401 - the entry's own top-level module: found through the folder kept on sys.path
        from hyperion.drills import gate_seat_template  # noqa: F401 - a submodule: through the pinned package

        return make_observation(**st)

    def from_action(self, a, obs, st):
        return a.kind.value

    def native_safe(self, st):
        return "fallback"


def make_adapter(bot, rules=None):
    return maybe_checked(TonightAdapter(bot, rules))
'''

LOADER = r'''
import importlib.util, json, os, sys, time, types
pkg = sys.argv[1]
st0, st1 = json.loads(sys.argv[2]), json.loads(sys.argv[3])
# the sandbox has no other hyperion (a venv's editable install would answer the imports the loader broke)
sys.path[:] = [p for p in sys.path if not os.path.isdir(os.path.join(p, "hyperion"))]
before = set(sys.modules)
sys.path.insert(0, pkg)
spec = importlib.util.spec_from_file_location("_bot1_bot", os.path.join(pkg, "bot.py"))
mod = importlib.util.module_from_spec(spec)
sys.modules["_bot1_bot"] = mod
spec.loader.exec_module(mod)
# kit G's import_bot (drill 9): the folder off sys.path and every module from it out of sys.modules, BEFORE Agent()
sys.path.remove(pkg)
for k in set(sys.modules) - before:
    f = getattr(sys.modules[k], "__file__", None) or ""
    if k == "_bot1_bot" or os.path.abspath(f).startswith(pkg + os.sep):
        del sys.modules[k]
out = {"unloaded": "hyperion" not in sys.modules and importlib.util.find_spec("hyperion") is None}
agent = mod.Agent()
out["path_back"] = pkg in sys.path
agent.begin_table(types.SimpleNamespace(table=0))
out["first"] = agent.decide(st0)
out["fallbacks"] = agent.ad.fallbacks
out["lazy"] = [getattr(sys.modules.get(m), "__file__", None) for m in ("lazy_helper", "hyperion.drills.gate_seat_template")]
calls = []
he, act = agent.ad.hand_end, agent.ad.bot.act
agent.ad.hand_end = lambda *a, **k: (calls.append("hand_end"), he(*a, **k))[1]
agent.ad.bot.act = lambda obs: (calls.append("act"), act(obs))[1]
r = types.SimpleNamespace(hand=0, won=(0, -10, 30, -20, 0, 0, 0, 0), log="", shown=(), board=(), table_over=False,
                          place=0)
t = time.thread_time()
agent.hand_over(r)
out["hand_over_us"] = (time.thread_time() - t) * 1e6
out["after_hand_over"], out["pending"] = list(calls), len(agent.pending)
heroes = [h for h in (getattr(m, "hero", m) for m in agent.ad.bot.core.members) if hasattr(h, "deferred")]
out["curve_owed"] = any(h._curve_todo is not None for h in heroes)  # the deferred part, after the callback
out["second"] = agent.decide(st1)
out["after_decide"] = list(calls)
out["deferred"] = [h.deferred for h in heroes]
out["errors"] = dict(mod.ERRORS)
print(json.dumps(out))
'''


def _package(tmp_path: Path, name: str, entry: str) -> Path:
    pkg = tmp_path / name
    pkg.mkdir()
    (pkg / "hyperion").symlink_to(ROOT / "hyperion", target_is_directory=True)
    (pkg / "tables").symlink_to(ROOT / "tables", target_is_directory=True)
    (pkg / "bot.py").write_text(entry)
    (pkg / "adapter.py").write_text(ADAPTER)
    (pkg / "lazy_helper.py").write_text("X = 1\n")
    return pkg


def _run_loader(tmp_path: Path, pkg: Path) -> dict:
    child = tmp_path / "child" / "loader.py"
    child.parent.mkdir(exist_ok=True)
    child.write_text(LOADER)
    st0, st1 = _state(0), _state(1, button=1)
    out = subprocess.run([sys.executable, "-I", "-B", str(child), str(pkg), json.dumps(st0), json.dumps(st1)],
                         capture_output=True, text=True, timeout=180, cwd=child.parent)
    assert out.returncode == 0, out.stderr[-3000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


@pytest.mark.night
@pytest.mark.parametrize("mode", ["defer", "store"])
def test_the_entry_template_survives_a_loader_that_unloads_before_the_agent_and_defers_a_timed_hand_end(tmp_path, mode):
    entry = (ROOT / "hyperion" / "drills" / "entry_template.py").read_text()
    assert entry.count('HAND_END = "defer"') == 1
    r = _run_loader(tmp_path, _package(tmp_path, "pkg", entry.replace('HAND_END = "defer"', f'HAND_END = "{mode}"')))
    assert r["unloaded"]  # the loader really took the package away before Agent()
    assert r["path_back"]  # the first call put the folder back on sys.path
    pkg = str(tmp_path / "pkg")
    assert r["first"] in ("fold", "call", "raise") and r["fallbacks"] == 0, r
    assert all(f and f.startswith(pkg + os.sep) for f in r["lazy"]), r["lazy"]  # both imports, from this copy
    assert r["deferred"] and all(r["deferred"]), r["deferred"]  # bot.defer_hand_end(True) reached every Hero
    if mode == "defer":  # the callback ran the light part; the curve waits for the next decision
        assert r["pending"] == 0 and r["after_hand_over"] == ["hand_end"] and r["curve_owed"], r
        assert r["after_decide"] == ["hand_end", "act"], r
        assert r["hand_over_us"] < 1000, r["hand_over_us"]  # CPU time, in a 1 ms callback
    else:  # the callback stored the result and called nothing; the next decision delivered it first
        assert r["pending"] == 1 and r["after_hand_over"] == [] and not r["curve_owed"], r
        assert r["after_decide"] == ["hand_end", "act"], r
        assert r["hand_over_us"] < 200, r["hand_over_us"]  # an append (the eager hand end ran 1-5 ms at load 7.6)
    assert r["second"] in ("fold", "call", "raise") and r["errors"] == {}, r


@pytest.mark.night
def test_without_the_folder_pinned_the_same_lazy_import_falls_to_the_kits_fold(tmp_path):
    """The control: the entry minus its pin_package(<folder>) at import. The package itself is still pinned (the Adapter
    built at import pins it), but the entry's own module is gone with the folder: the decision is the kit's fold."""
    entry = (ROOT / "hyperion" / "drills" / "entry_template.py").read_text()
    assert entry.count("pin_package(*_ROOTS)") == 1
    r = _run_loader(tmp_path, _package(tmp_path, "nopin", entry.replace("pin_package(*_ROOTS)", "pass")))
    assert r["unloaded"] and not r["path_back"]
    assert r["first"] == "fallback" and r["fallbacks"] == 1, r


# ------------------------------------------------------------------ 3: the gate seat's rows, posts and a kit's log

def test_the_gate_seat_state_carries_streets_chips_and_posts_and_a_per_street_log_round_trips(tmp_path):
    from hyperion.drills.gate_seat_template import by_street, kit_g_log
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import BotStats

    gate = _load(ROOT / "tools" / "gate.py", "gate_for_h5")
    drill9 = _load(ROOT / "docs" / "drills" / "drill9" / "adapter.py", "drill9_adapter_for_h5")

    class Recorder(gate.HostProxy):
        """kind seat, no host process: the state a seat file gets, answered by CheapBot."""

        def __init__(self):
            super().__init__(gate.Config(pkg=tmp_path, entry="x.py", kit="seat", kit_dir=tmp_path,
                                         scratch=str(tmp_path)), "seat")
            self.bot, self.seen, self.ends = CheapBot(), [], []

        def open(self):
            self.proc = True  # hand_end sends only to an open host
            self.bot.new_table(self.rules, self.seat, self.n)

        def decide(self, obs):
            self.seen.append((obs, json.loads(json.dumps(self.state(obs)))))
            a = self.bot.act(obs)
            return gate.Reply(kind=a.kind.value, total=int(a.amount), ns=1000)

        def _send(self, obj):
            if obj.get("op") == "end":
                self.ends.append(json.loads(json.dumps(obj)))
            return True

    names = ["maniac", "tag", "station", "loose_aggro", "nit", "random", "pushfold"]
    for seed in (3, 4):
        p = Recorder()
        bots = [p] + [B.make_bot(nm, seed=seed * 8 + s) for s, nm in enumerate(names)]
        table = gate.GateTable(bots, Rules(), seed, "measure", None, [BotStats(str(i)) for i in range(8)], 0, p)
        table.play()
        assert len(p.seen) > 30 and len(p.ends) > 10
        assert any(obs.street >= 2 and any(a.kind is ActionKind.RAISE for _, a in obs.history) for obs, _ in p.seen)
        n, me = 8, 0
        for obs, st in p.seen:
            rows, posts = st["history"], st["posts"]
            assert len(rows) == len(obs.history) and all(len(row) == 5 for row in rows)
            streets = [row[3] for row in rows]
            assert streets == sorted(streets) and (not streets or streets[-1] <= obs.street)
            sb, bb = obs.blinds
            assert [k for _, k, _ in posts] == ["sb", "bb"] and posts[1][2] <= bb and posts[0][2] <= sb
            # each seat's chips on this street: the posts (preflop) and the puts add up to the bets
            here = by_street(rows, posts, obs.street)[obs.street]
            for s in range(n):
                put = sum(x[3] for x in here if x[0] == s and x[1] != "ante")
                assert put == obs.bets[s], (s, here, obs.bets)
            # drill 9's kit G log, per street with the blinds posted, through the drill 9 player's own parser
            got = drill9.history(kit_g_log(rows, posts, me, n, obs.street))
            want = [((s - me) % n, a) for s, a in obs.history]
            assert [(s, a.kind, a.amount if a.kind is ActionKind.RAISE else 0) for s, a in got] == \
                [(s, a.kind, a.amount if a.kind is ActionKind.RAISE else 0) for s, a in want]
        for end in p.ends:
            res = end["result"]
            assert res["posts"] and all(len(row) == 5 for row in res["history"])
            got = drill9.history(kit_g_log(res["history"], res["posts"], me, n))
            assert [a.kind.value for _, a in got] == [row[1] for row in res["history"]]


def test_the_fake_kits_keep_their_three_field_rows():
    from hyperion.drills.adapter import dealer_state, history_rows

    obs = make_observation(**{**_state(0), "history": [(3, Action(ActionKind.RAISE, 60)), (4, Action(ActionKind.CALL))]})
    assert dealer_state(obs)["history"] == [[3, "raise", 60], [4, "call", 0]] and "posts" not in dealer_state(obs)
    assert history_rows(obs.history, {5: 12}, 1, tags=[(0, 60), (0, 60)]) == [
        [3, "raise", 60, 0, 60], [5, "discard", 12, 1, 0], [4, "call", 0, 0, 60]]


# ------------------------------------------------------------------ 4: conformance after the warm-up

class _Dict(Adapter):
    history_source = "log"

    def to_observation(self, st):
        return make_observation(**st)

    def from_action(self, a, obs, st):
        return a.kind.value

    def native_safe(self, st):
        return "fold"


@pytest.mark.night
def test_the_warm_up_leaves_no_findings_on_the_kits_first_hand():
    ad = conformance.checked(_Dict(CheapBot(), Rules()))
    # drill 9's warm-up: a made-up hand 1 (button 4, a raise in its log), then the bot started for the kit's table
    ad.decide(_state(1, button=4, history=[(4, Action(ActionKind.RAISE, 60))]))
    ad.start(3, 8, Rules())
    ad.decide(_state(1, button=0))  # the kit's real hand 1: another button, a log that does not extend the made-up one
    assert not {"history_prefix", "button_changed"} & set(ad.conformance.counts), ad.conformance.summary()
    assert ad.conformance.observations == 2
    conformance.warmed(ad)
    r = ad.conformance
    assert r.observations == 0 and r.total == 0 and sum(r.actions.values()) == 0
    # within a table the cross-call rules still hold
    ad.decide(_state(2, button=0))
    ad.decide(_state(2, button=5))
    assert r.counts["button_changed"] == 1


# ------------------------------------------------------------------ 6: no table build inside a decision

QUICK = r'''
import json, os, sys, time
sys.path[:] = [sys.argv[1]] + [p for p in sys.path if not os.path.isdir(os.path.join(p, "hyperion"))]
st0, st1 = json.loads(sys.argv[2]), json.loads(sys.argv[3])
from hyperion import ship
from hyperion.core.types import Rules
from hyperion.drills import variants as V
from hyperion.drills.adapter import Adapter, make_observation


class DictAdapter(Adapter):  # no table-start hook: decide() starts the bot lazily, inside the decision
    def to_observation(self, st):
        return make_observation(**st)

    def from_action(self, a, obs, st):
        return a.kind.value

    def native_safe(self, st):
        return "fallback"


def heroes(bot):
    return [h for h in (getattr(m, "hero", m) for m in bot.core.members) if hasattr(h, "active")]


def where(bot):
    return [h.active.source + ":" + h.active.dir.rstrip("/").split("/")[-1] for h in heroes(bot)]


out = {}
for name, rules, k in (("chain_holdem", Rules(hole_cards=3, extras={"variant": "chain_holdem"}), 3),
                       ("three_card_keep", V.get("three_card_keep").rules, 3), ("short_deck", V.get("short_deck").rules, 2)):
    ad = DictAdapter(ship.make_bot(), rules)
    a, b = dict(st0, hole=st0["hole"][:k]), dict(st1, hole=st1["hole"][:k])
    t = time.thread_time()
    first = ad.decide(a)
    ms = (time.thread_time() - t) * 1e3
    out[name] = {"ms": ms, "answers": [first, ad.decide(b)], "fallbacks": ad.fallbacks, "where": where(ad.bot)}
bot = ship.make_bot()
t = time.thread_time()
bot.new_table(V.get("three_card_keep").rules, 3, 8)  # the same start outside a decision: what the guard kept out
out["full_ms"], out["full_where"] = (time.thread_time() - t) * 1e3, where(bot)
ad = DictAdapter(ship.make_bot(), V.get("three_card_keep").rules)
ad.decide(st0)
out["warm_where"] = where(ad.bot)  # a lazy start after a full one: the set this process loaded
print(json.dumps(out))
'''


@pytest.mark.night
def test_a_table_start_inside_a_decision_builds_nothing_and_plays_legally(tmp_path):
    """Cold process, a kit with no table-start hook: the first decision starts the bot. Before H5 that start, inside
    the decision, built the 8-card evaluator and loaded the variant set (67 ms for three hole cards, 33 ms short deck,
    CPU time); now it reads nothing from disk and plays the plain tables, and a later start outside a decision loads
    them."""
    child = tmp_path / "quick.py"
    child.write_text(QUICK)
    st0 = _state(0, hole=(51, 47, 26))
    st1 = _state(0, street=1, hole=(51, 47, 26))
    out = subprocess.run([sys.executable, "-I", "-B", str(child), str(ROOT), json.dumps(st0), json.dumps(st1)],
                         capture_output=True, text=True, timeout=300, cwd=tmp_path)
    assert out.returncode == 0, out.stderr[-3000:]
    r = json.loads(out.stdout.strip().splitlines()[-1])
    for name in ("chain_holdem", "three_card_keep", "short_deck"):
        c = r[name]
        assert c["ms"] < 15, (name, c)  # (0.3-1.6 ms here; CPU time, so a loaded host barely moves it)
        assert c["answers"][0] in ("fold", "call", "raise") and c["answers"][1] in ("check", "raise"), (name, c)
        assert c["fallbacks"] == 0, (name, c)
    assert all(w.endswith("+labelview:tables") for w in r["chain_holdem"]["where"] + r["three_card_keep"]["where"])
    assert all(w == "disk:tables" for w in r["short_deck"]["where"])  # the plain 169 tables, not the 81-class set
    assert r["full_ms"] > 20 and all(w == "disk:three_card_keep" for w in r["full_where"]), r
    assert all(w == "disk:three_card_keep" for w in r["warm_where"]), r


# ------------------------------------------------------------------ 5, 7: the night docs

def test_the_timing_marker_is_registered_and_the_night_deselects_it():
    text = (ROOT / "pyproject.toml").read_text()
    assert re.search(r'markers = \[\s*"timing: ', text)
    p02 = (ROOT / "docs" / "prompts" / "02-adapter-and-cheap-bot.md").read_text()
    assert '-m "not timing"' in p02 and "entry_template.py" in p02 and "HAND_END" in p02 and "defer_hand_end(True)" in p02
    assert "pin_package()" in p02 and "by_street" in p02
    marked = [p.name for p in (ROOT / "tests").glob("test_*.py") if "mark.timing" in p.read_text()]
    for name in ("test_sim_bestiary.py", "test_slowbox.py", "test_drills_fakekits.py", "test_setup_cost.py",
                 "test_hand_end_interrupt.py"):
        assert name in marked, name


def test_every_cand_example_is_a_spec_climb_accept_reads():
    docs = [ROOT / "PLAYBOOK.md", *sorted((ROOT / "docs" / "prompts").glob("*.md")), ROOT / "docs" / "packet" /
            "CONTRACTS.md"]
    seen = 0
    for path in docs:
        for m in re.finditer(r"--cand\s+'([^']*)'", path.read_text()):
            seen += 1
            spec = m.group(1)
            assert spec != "<the dict>", path
            if spec.startswith("{"):  # JSON: {"dials": ...} or {"bot": ...}; anything else is recipe names
                assert spec.startswith('{"dials"') or spec.startswith('{"bot"'), (path, spec)
    assert seen >= 4
