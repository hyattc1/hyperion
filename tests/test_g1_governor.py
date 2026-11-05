"""G1: the governor counts the whole timed call. SafeBot with and without an adapter's reports, Adapter.decide's report on every way
out, the budget-aware hand end and its bound, the dial that plays batch 8's clock, tools/gate.py's check, and identity on the kit path."""
import random
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hyperion import ship
from hyperion.compose.bot import G1_OFF, SHIP_DIALS
from hyperion.core.types import Action, ActionKind, HandResult, Rules
from hyperion.drills.adapter import KitBAdapter, dealer_state
from hyperion.drills.fakekits.kit_b import kit as K
from hyperion.sim import bestiary as B
from hyperion.sim.engine import BotStats, play_table
from hyperion.strategy.safe import Governor, SafeBot

ROOT = Path(__file__).resolve().parents[1]
GOV = Governor(window=60, ladder=True, recover=40)
DET = {"panic_after": 10 ** 9, "late_us": 1e9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9}


class Inner:
    """Levels and a stopwatch-free act."""

    levels = 3

    def __init__(self):
        self.level = 0
        self.panic = False

    def new_table(self, *a):
        pass

    def act(self, obs):
        return Action.fold()

    def hand_end(self, r):
        pass

    def set_level(self, n):
        self.level = n

    def set_panic(self, on):
        self.panic = on


class Obs:
    legal = frozenset({ActionKind.FOLD})
    min_raise = max_raise = 0


def safe(whole=True, **kw):
    return SafeBot(Inner(), deadline_ms=0.8, panic_after=5, gov=GOV, whole_call=whole, **kw)


def test_no_reports_act_alone_counts_as_before():
    s = SafeBot(Inner(), deadline_ms=0.0, panic_after=5, gov=GOV, whole_call=True)  # every act overruns a zero deadline
    for _ in range(5):
        s.act(Obs())
    assert s.overruns == 5 and s.degrade_level == 1


def test_with_reports_the_whole_call_counts_and_act_does_not():
    s = SafeBot(Inner(), deadline_ms=0.0, panic_after=5, gov=GOV, whole_call=True)
    assert s.expect_reports() is True
    for _ in range(10):
        s.act(Obs())
    assert s.overruns == 0 and s.degrade_level == 0  # act alone would have fired above
    s = safe()
    s.expect_reports()
    for _ in range(5):
        s.act(Obs())
        s.report_call(0.0009)  # over the 0.8 ms line, though act took microseconds
    assert s.overruns == 5 and s.degrade_level == 1 and s.reports == 5
    assert abs(s.worst - 0.0009) < 1e-9


def test_the_window_and_the_deadline_are_the_same_line():
    s = safe()
    s.expect_reports()
    for _ in range(300):  # 0.79 ms: under the line, never a step; four overruns in 60: not a cluster
        s.act(Obs())
        s.report_call(0.00079)
    assert s.degrade_level == 0
    for i in range(300):
        s.act(Obs())
        s.report_call(0.0009 if i % 15 == 0 else 0.0001)
    assert s.degrade_level == 0 and s.level_max == 0


def test_the_dial_off_is_batch_8s_clock():
    s = safe(whole=False)
    assert s.expect_reports() is False
    for _ in range(20):
        s.act(Obs())
        s.report_call(0.5)
    assert s.overruns == 0 and s.degrade_level == 0 and s.reports == 20  # reported, not counted
    bot = ship.make_bot(dials=G1_OFF)
    assert bot.safe.whole_on is False and bot.safe.end_budget == 0.0
    a = KitBAdapter(bot)
    hero = bot.core.members[bot.core._hero_idx]
    assert a._whole is False and a._budget == 0.0 and hero.deferred is False  # the hand end whole, as batch 8's
    on = ship.make_bot()
    assert on.safe.whole_on is True and SHIP_DIALS["whole_call"] is True
    KitBAdapter(on)
    assert on.core.members[on.core._hero_idx].deferred is True


def test_model_mode_never_reads_the_clock_for_the_hand_end():
    bot = ship.make_bot(dials=DET)
    assert bot.safe.end_budget == 0.0 and KitBAdapter(bot)._budget == 0.0
    assert ship.make_bot().safe.end_budget == 0.00075


class Slow(KitBAdapter):
    """Kit B's adapter whose translation burns `slow` seconds on the clock, and that can blow up."""

    slow = 0.0
    boom = False

    def to_observation(self, o):
        t = time.perf_counter()
        while time.perf_counter() - t < self.slow:
            pass
        if self.boom:
            raise ValueError("boom")
        return super().to_observation(o)


def _native(seat=3, hand=1):
    st = {"hole": [48, 49], "board": [], "street": 0, "seat": seat, "button": 0,
          "stacks": [2000, 1990, 1980, 2000, 2000, 2000, 2000, 2000], "bets": [0, 10, 20, 0, 0, 0, 0, 0],
          "in_hand": [True] * 8, "pot": 0, "to_call": 20, "min_raise": 40, "max_raise": 2000,
          "legal": ["fold", "call", "raise"], "hand_no": hand, "blinds": [10, 20], "history": [], "discards": {}}
    return K.to_observation(st)


def test_the_governor_sees_a_slow_translation_through_the_adapter():
    bot = ship.make_bot(seed=1)
    a = Slow(bot)
    a.start(3, 8)
    a.slow = 0.0009
    for i in range(6):
        a.decide(_native(hand=i + 1))
    assert bot.safe.overruns >= 5 and bot.safe.degrade_level >= 1 and bot.safe.reports == 6


def test_batch_8s_clock_is_blind_to_it():
    bot = ship.make_bot(dials=G1_OFF, seed=1)
    a = Slow(bot)
    a.start(3, 8)
    a.slow = 0.0009
    for i in range(6):
        a.decide(_native(hand=i + 1))
    assert bot.safe.level_max == 0


def test_the_report_comes_on_every_way_out_and_t0_moves_the_start():
    bot = ship.make_bot(seed=1)
    a = Slow(bot)
    a.start(3, 8)
    a.boom = True
    assert a.decide(_native())["action"] in ("fold", "check")
    assert bot.safe.reports == 1 and bot.safe.calls == 0
    a.boom = False
    t = time.perf_counter() - 0.002
    a.decide(_native(hand=2), t)
    assert bot.safe.worst >= 0.002


def test_a_stand_in_is_not_built_where_the_rebuilt_log_replaces_it():
    """Same bot history: make_observation's stand-in was thrown away on every decision of a kit with no log."""
    seen = []
    bot = ship.make_bot(seed=1)
    a = KitBAdapter(bot)
    a.start(3, 8)
    orig = bot.act

    def spy(obs):
        seen.append(obs)
        return orig(obs)

    bot.act = spy
    a.decide(_native())
    assert seen[0].extras.get("history_inferred") and "history_from_bets" not in seen[0].extras


# ---------------------------------------------------------------------------- the budget-aware hand end
def _hold_ready(a, hand):
    """A decision in `hand` after which a seat still has to act owing chips: the hand end has a tail to wait for."""
    a.decide(_native(hand=hand))
    assert a.inference.tail_open() or a.inference.sent is not None


def _adapter(bot=None):
    a = KitBAdapter(bot or ship.make_bot(seed=1))
    a.start(3, 8)
    return a


def test_on_a_normal_box_the_hand_end_waits_for_the_next_state():
    a = _adapter()
    a._n_call, a._e_call, a._e_end = 100, 0.00018, 0.00008  # what a loaded 1x box measures
    assert a.short_of_time() is False
    _hold_ready(a, 1)
    if a.inference.tail_open():
        a.hand_end(1, -20)
        assert a._pending is not None and a.tails_lost == 0


def test_short_of_time_the_hand_end_runs_at_the_kits_callback_and_the_bound_keeps_some_tails():
    a = _adapter()
    a._n_call, a._e_call, a._e_end = 100, 0.0005, 0.0003
    assert a.short_of_time() is True
    ends = []
    orig = a.bot.hand_end
    a.bot.hand_end = lambda r: (ends.append(r.hand_no), orig(r))
    held = lost = 0
    for h in range(1, 41):
        a.decide(_native(hand=h))
        a._e_call, a._e_end, a._n_call = 0.0005, 0.0003, 100
        if not a.inference.tail_open():
            pytest.skip("this spot has no tail")
        a.hand_end(h, -20)
        if a._pending is not None:
            held += 1
        else:
            lost += 1
    assert held and lost and lost >= (a.tail_every - 1) * (held - 1)  # thinned, never cut off
    assert a.tails_lost == lost and a.tails_forced == held
    assert a._safe.life["tail_lost"] == lost and a._safe.life["forced"] == held
    assert len(ends) >= lost  # none lost silently: the bot got every hand end


def test_the_means_ignore_one_stall_and_a_cold_start():
    a = _adapter()
    for _ in range(15):
        a._note_call(0.002)
    a._note_end(0.002)
    assert a.short_of_time() is False  # under 16 calls: a warm-up says nothing
    a = _adapter()
    for _ in range(200):
        a._note_call(0.00015)
        a._note_end(0.00008)
    a._note_call(0.05)  # one 50 ms stall: clipped at 1 ms, a sixteenth of it
    a._note_end(0.05)
    assert a.short_of_time() is False


def test_a_table_start_forgets_the_means():
    a = _adapter()
    for _ in range(200):
        a._note_call(0.0009)
    a.start(3, 8)
    assert a._n_call == 0 and a.short_of_time() is False


def test_the_stored_hand_end_is_dropped_within_its_bound(monkeypatch):
    """entry_template.py's _flush, the same rule: its logic against a stub adapter."""
    src = (ROOT / "hyperion" / "drills" / "entry_template.py").read_text()
    assert "self.ad.short_of_time() and self.skipped < STORE_SKIP_MAX" in src and "self.ad.drop_hand_end(len(pend))" in src
    a = _adapter()
    a.drop_hand_end(2)
    assert a.ends_dropped == 2 and a._safe.life["dropped"] == 2


# ---------------------------------------------------------------------------- identity on the kit path
class KitSeat:
    """The ship bot behind kit B's adapter in-process: what a package plays, on the engine's Observation."""

    dials: dict = {}

    def __init__(self, seed=None):
        self.ad = KitBAdapter(ship.make_bot(dials=dict(self.dials), seed=seed))
        self.trace = []
        KitSeat.last = self

    def new_table(self, rules, seat, n):
        self.ad.start(seat, n, rules)

    def act(self, obs):
        d = self.ad.decide(K.to_observation(dealer_state(obs)))
        kind, total = K.parse_decision(d, {"bets": list(obs.bets)})
        self.trace.append((obs.hand_no, obs.street, kind, total))
        return Action(ActionKind(kind), total) if kind == "raise" else Action(ActionKind(kind))

    def hand_end(self, r: HandResult):
        self.ad.hand_end(r.hand_no, r.deltas[self.ad.seat])

    def variant_decide(self, p):
        return self.ad.bot.variant_decide(p)


def _play(dials, t):
    KitSeat.dials = dials
    B.REGISTRY["kit_seat_g1"] = KitSeat
    names = [x.strip().lower() for x in B.field_names("realistic@kit_seat_g1") if x.strip()]
    rng = random.Random(7000 + t)
    seats = list(names[:8])
    while len(seats) < 8:
        seats.append(rng.choice(names))
    rng.shuffle(seats)
    bots = [B.make_bot(nm, seed=t * 64 + s) for s, nm in enumerate(seats)]
    try:
        play_table(bots, Rules(), seed=7000 + t, rotation=t % 8, mode="model", stats=[BotStats(nm) for nm in seats])
    finally:
        B.REGISTRY.pop("kit_seat_g1", None)
    return KitSeat.last.trace


@pytest.mark.parametrize("t", [0, 1, 2])
def test_in_model_mode_the_kit_path_decides_as_batch_8s_clock_does(t):
    on = _play(DET, t)
    off = _play({**DET, **G1_OFF}, t)
    assert on == off and len(on) > 20


# ---------------------------------------------------------------------------- the gate's check
def _gate():
    import importlib.util

    spec = importlib.util.spec_from_file_location("gate_g1", ROOT / "tools" / "gate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["gate_g1"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_gate_verdict_on_the_governors_report():
    g = _gate()
    fails, warns = g.gov_verdict({"capable": True, "acts": 100, "reports": 100, "whole_on": True, "whole": True})
    assert not fails and not warns
    fails, warns = g.gov_verdict({"capable": True, "acts": 100, "reports": 0, "whole_on": True})
    assert fails and "does not report" in fails[0].replace("\n", " ")
    fails, warns = g.gov_verdict({"capable": True, "acts": 100, "reports": 0, "whole_on": False})
    assert not fails and "G1_OFF" in warns[0]
    fails, warns = g.gov_verdict({"capable": False, "acts": 100, "reports": 0})
    assert not fails and "predates" in warns[0]
    fails, warns = g.gov_verdict({"no_report": 3})
    assert not fails and "no governor report" in warns[0]


def test_add_gov_and_its_line():
    g = _gate()
    tot = {}
    g.add_gov(tot, {"capable": True, "acts": 10, "reports": 10, "overruns": 2, "tables": 1, "level_tables": 1, "panic_tables": 0,
                    "tail_lost": 3, "forced": 1, "dropped": 0, "level_max": 2, "lvl_calls": {"0": 7, "2": 3}, "whole_on": True,
                    "whole": True})
    g.add_gov(tot, None)
    assert tot["acts"] == 10 and tot["no_report"] == 1 and tot["lvl_calls"]["2"] == 3
    line = g.gov_line(tot)
    assert "level_max 2" in line and "level 2 3" in line and "3 without their tail" in line


ENTRY_NO_REPORT = """import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperion.drills.adapter import KitBAdapter
from hyperion import ship
_ad = KitBAdapter(ship.make_bot())

def decide(o):
    # an agent's own decide around bot.act, under time pressure: no report reaches the governor
    obs = _ad.with_history(_ad.to_observation(o))
    return _ad.from_action(_ad.bot.act(obs).clamp(obs), obs, o)

def on_table_start(i):
    _ad.start(i["seat"], i["players"])

def on_hand_end(i):
    _ad.hand_end(i["hand_id"], i["delta"])
"""
ENTRY_OK = """import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperion.drills.adapter import make_kit_b_module
decide, on_table_start, on_hand_end = make_kit_b_module()
"""


@pytest.fixture(scope="module")
def pkg_dir(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("g1pkg")
    (tmp / "entry_ok.py").write_text(ENTRY_OK)
    (tmp / "entry_bad.py").write_text(ENTRY_NO_REPORT)
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "pack.py"), "--entry", "entry_ok.py", "--extra", "entry_bad.py",
                        "--out", "dist", "--slim", "--night", "/dev/null"], cwd=tmp, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    return tmp / "dist" / "submission"


def _run_gate(pkg, entry, *more):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "gate.py"), str(pkg), "--kit", "b", "--entry", entry, "--tables",
                           "2", "--baseline", "package", "--max-tmo-pct", "100", *more], capture_output=True, text=True,
                          timeout=400)


def test_the_gate_passes_the_template_way_and_prints_the_line(pkg_dir):
    r = _run_gate(pkg_dir, "entry_ok.py")
    assert "whole calls reported (counted)" in r.stdout and "level_max" in r.stdout, r.stdout + r.stderr
    assert "not report" not in r.stdout


def test_the_gate_fails_an_adapter_that_does_not_report(pkg_dir):
    r = _run_gate(pkg_dir, "entry_bad.py")
    assert r.returncode == 1, r.stdout + r.stderr
    assert "GATE FAIL" in r.stdout and "does not report" in r.stdout


# ---------------------------------------------------------------------------- the floor: a box measured slow
def test_a_box_measured_slow_holds_the_first_rung_and_a_normal_one_never():
    bot = ship.make_bot(seed=1)
    a = _adapter(bot)
    for _ in range(400):  # a loaded 1x box: the mean stays under 0.6 of the budget
        a._note_call(0.00019)
    assert bot.safe.degrade_level == 0 and bot.safe.level_max == 0
    for _ in range(100):  # a 2x box
        a._note_call(0.00034)
    assert bot.safe.degrade_level == 1 and a._floored
    for _ in range(100):  # the rung takes a quarter off: it stays
        a._note_call(0.00026)
    assert bot.safe.degrade_level == 1 and a._floored
    for _ in range(100):  # the box was busy, now it is not
        a._note_call(0.00012)
    assert not a._floored and bot.safe._floor == 0


def test_the_floor_holds_against_recovery_and_a_table_start_clears_it():
    s = safe()
    s.inner.levels = 3
    s._levels = 3
    s.expect_reports()
    s.set_floor(1)
    assert s.degrade_level == 1
    for _ in range(500):
        s.act(Obs())
        s.report_call(0.0001)
    assert s.degrade_level == 1  # quiet calls do not recover past the floor
    s.set_floor(0)
    for _ in range(100):
        s.act(Obs())
        s.report_call(0.0001)
    assert s.degrade_level == 0
    s.set_floor(1)
    s.new_table(Rules(), 0, 8)
    assert s.degrade_level == 0 and s._floor == 0


def test_a_bot_with_no_ladder_has_no_floor():
    s = SafeBot(Inner(), deadline_ms=0.8, gov=Governor(window=60, recover=40), whole_call=True)
    s.set_floor(1)
    assert s.degrade_level == 0 and s.panic_mode is False


# ---------------------------------------------------------------------------- a kit that gives the whole log
def test_a_log_kits_hand_end_is_the_kits_log_and_the_walk_needs_no_keeping():
    from hyperion.drills.adapter import make_observation

    class LogKit(KitBAdapter):
        history_source = "log"

        def to_observation(self, o):
            obs = super().to_observation(o)
            obs.history = [(4, Action.fold())]
            obs.extras = {}
            return obs

    got = []
    bot = ship.make_bot(seed=1)
    orig = bot.hand_end
    bot.hand_end = lambda r: (got.append(r), orig(r))
    a = LogKit(bot)
    a.log_at_end = True
    a.start(3, 8)
    a.decide(_native())
    assert a.inference.hand_no is None  # nothing walked
    log = [(4, Action.fold()), (3, Action.call())]
    a.hand_end(1, -20, 8, history=log, deltas=[0, 0, 0, -20, 0, 0, 20, 0], showdown={}, board=())
    assert got and got[-1].history == log and got[-1].deltas[3] == -20
    assert make_observation is not None


def test_a_recap_dropped_for_the_budget_still_keeps_the_chips():
    src = (ROOT / "hyperion" / "drills" / "closure_entry_template.py").read_text()
    assert "t0 = perf_counter()" in src and "ad.decide(v, t0)" in src and "ad.short_of_time()" in src
    assert "if not deliver:\n        return\n" in src  # after the chip chain, before the bot's hand end


@pytest.mark.parametrize("name", ["entry_template", "module_entry_template", "closure_entry_template"])
def test_every_state_entry_passes_its_first_clock_read(name):
    src = (ROOT / "hyperion" / "drills" / f"{name}.py").read_text()
    assert "from time import perf_counter" in src and "t0 = perf_counter()" in src and ", t0)" in src


# ---------------------------------------------------------------------------- a stall is not a slow box
def test_a_stall_is_late_and_counts_for_nothing():
    s = safe()
    s.expect_reports()
    for _ in range(50):  # 3 ms on the wall, 0.2 ms of CPU: the scheduler's, and stepping down answers nothing
        s.act(Obs())
        s.report_call(0.003, 0.0002)
    assert s.overruns == 0 and s.degrade_level == 0 and s.worst == 0.003
    for _ in range(5):  # a slow CPU: the code itself used the time
        s.act(Obs())
        s.report_call(0.0009, 0.00085)
    assert s.overruns == 5 and s.degrade_level == 1


def test_a_real_stall_through_the_adapter_counts_for_nothing():
    bot = ship.make_bot(seed=1)
    a = Slow(bot)
    a.start(3, 8)

    def stalled(o):
        time.sleep(0.002)
        return KitBAdapter.to_observation(a, o)

    a.to_observation = stalled
    for i in range(8):
        a.decide(_native(hand=i + 1))
    assert bot.safe.worst > 0.002 and bot.safe.overruns == 0 and bot.safe.degrade_level == 0
    assert a._e_call < 0.001 and not a._floored


def test_the_gate_dilates_the_thread_clock_too():
    for tool in ("gate_host.py", "zip_host.py"):
        assert "time.thread_time = lambda" in (ROOT / "tools" / tool).read_text()
