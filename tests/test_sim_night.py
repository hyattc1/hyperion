"""The `night` fields (hyperion/sim/field/night.py) and the Track B bots in their pool: the draw is a function of the
table seed alone, seven distinct opponents, the same for every rotation and every `night@<bot>` swap; the frozen
sources match their archives; the kit A and kit B adapters play legal poker. No number from a run here is read as a
measurement."""
import hashlib
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.field import night as N
from hyperion.sim.engine import play_table
from hyperion.sim.runner import run_tournament

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {  # registry name -> (archived original, copy in the package, header lines, md5 of the original)
    "trackb3": ("docs/drills/field/trackb3_bot.py", "hyperion/sim/field/trackb3.py", 7,
                "b40150c0551b423454c6e9c9e927bea4"),
    "trackb5": ("docs/drills/field/trackb5_bot.py", "hyperion/sim/field/trackb5.py", 7,
                "aeb14d3b9bbc64a7db86450a66d1c4d0"),
    "agent_charts": ("docs/drills/field/agent_charts_bot.py", "hyperion/sim/field/agent_charts.py", 6,
                     "8d684a439cabe518f86a1c471e343d2b"),
    "agent_default": ("docs/drills/field/agent_default_bot.py", "hyperion/sim/field/agent_default.py", 6,
                      "cd47da88b88071e7e1e7665aea06db41"),
    "agent_montecarlo": ("docs/drills/field/agent_montecarlo_bot.py", "hyperion/sim/field/agent_montecarlo.py", 6,
                         "653c9c29fe77708d6318d237ca88e17c"),
    "agent_pushfold": ("docs/drills/field/agent_pushfold_bot.py", "hyperion/sim/field/agent_pushfold.py", 6,
                       "d221bdd6e5ae76aa6c152fb2fa614490"),
}
SCRUBBED = {"trackb3", "trackb5"}  # the event's name dropped from the first docstring line for the public export
# how to let each persona bot's exceptions through to the engine (each wraps its own act() in a try)
PERSONA_UNWRAP = {
    "agent_charts": lambda cls, mp: mp.setattr(cls, "DEBUG", True),
    "agent_default": lambda cls, mp: mp.setattr(cls, "act", lambda self, obs: self._safe(obs, self._act(obs))),
    "agent_montecarlo": lambda cls, mp: mp.setattr(
        cls, "act", lambda self, obs: self._sanitize(self._act(obs, time.perf_counter()), obs)),
    "agent_pushfold": lambda cls, mp: mp.setattr(cls, "DEBUG", True),
}
JUDGES = {"rival4", "rival5"}
NOT_IN_POOLS = JUDGES | {"hero", "hero_tight", "hero_loose", "hybrid", "hybrid3", "hybrid_x", "hybrid3_x", "micro"}


@pytest.mark.parametrize("name", sorted(FROZEN))
def test_frozen_source_matches_its_archive_and_md5(name):
    archive, copy, header, md5 = FROZEN[name]
    raw = (ROOT / archive).read_bytes()
    assert hashlib.md5(raw).hexdigest() == md5
    lines = (ROOT / copy).read_bytes().splitlines(keepends=True)
    assert all(ln.startswith(b"#") for ln in lines[:header])
    assert md5.encode() in b"".join(lines[:header])
    if name not in SCRUBBED:
        assert b"".join(lines[header:]) == raw  # unchanged apart from the header
        return
    # unchanged apart from the header and the event's one-word name, dropped from the docstring's first line so the
    # public export carries no event identifier (the archive keeps it; docs/drills/ is never exported)
    body = b"".join(lines[header:])
    a_first, a_rest = raw.split(b"\n", 1)
    c_first, c_rest = body.split(b"\n", 1)
    assert c_rest == a_rest
    assert c_first.startswith(b'"""Bot night, ') and a_first.lower().endswith(c_first[3:].lower())
    assert len(a_first) - len(c_first) == 8 and b" " not in a_first[3:10]  # one word and its space


def test_night_fields_are_hero_plus_seven_pool_seats():
    for pool in ("night", "night_hard", "night0"):
        f = B.field_names(pool)
        assert f == ["hero"] + [f"{pool}.{k}" for k in range(1, 8)]
        assert B.field_names(f"{pool}@hybrid3_x") == ["hybrid3_x"] + f[1:]
    assert "night@hybrid3_x" in B.FIELDS and "night_hard@rival3" in B.FIELDS
    assert N.parse_seat("night.3") == ("night", 3)
    assert N.parse_seat("night.8") is None and N.parse_seat("tag") is None and N.parse_seat("nope.1") is None


def test_pools_hold_no_judge_and_no_candidate():
    for name, pool in N.POOLS.items():
        drawn = {b for _, _, ms in pool.groups for b, _ in ms}
        assert not drawn & NOT_IN_POOLS, name
        assert abs(sum(w for _, w, _ in pool.groups) - 1.0) < 1e-9, name
    assert N.POOLS["night"].groups[0][1] == 0.40 and N.POOLS["night_hard"].groups[3][1] == 0.30


def test_draw_is_seven_distinct_registered_bots_and_a_function_of_the_table_seed():
    for pool in ("night", "night_hard", "night0"):
        for t in range(300):
            d = N.draw(pool, t)
            assert len(d) == 7 and len(set(d)) == 7, (pool, t, d)
            assert all(b in B.REGISTRY for b in d)
            N._CACHE.clear()
            assert N.draw(pool, t) == d  # not the cache: recomputed
    assert N.draw("night", 1) != N.draw("night", 2) or N.draw("night", 1) != N.draw("night", 3)
    assert not set().union(*(N.draw("night0", t) for t in range(200))) & set(N.PERSONAS)


def test_draw_is_the_same_in_another_process_with_another_hash_seed():
    code = "from hyperion.sim.field import night as N; print([N.draw('night', t) for t in (0, 7, 7000021)])"
    outs = set()
    for hs in ("0", "12345"):
        env = {**os.environ, "PYTHONHASHSEED": hs}
        outs.add(subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True,
                                check=True).stdout)
    assert len(outs) == 1
    assert outs.pop().strip() == str([N.draw("night", t) for t in (0, 7, 7000021)])


def test_composition_follows_the_weights_where_groups_do_not_run_out():
    c = N.composition("night", 4000)["group"]
    assert abs(sum(c.values()) - 7) < 1e-9
    agent_members = [b for b, _ in N.members("night")[0][2]]
    assert set(agent_members) == set(N.PERSONAS) | set(N.TRACK_B)
    for g, share in ((N.AGENT, 0.40), (N.WEAK, 0.30), (N.DECENT, 0.15), (N.STRONG, 0.15)):
        assert abs(c[g] / 7 - share) < 0.02, (g, c[g])  # no group runs out: 40/30/15/15 of the seven seats
    hard = N.composition("night_hard", 4000)["group"]
    assert hard[N.STRONG] > 1.6 * c[N.STRONG] and hard[N.WEAK] < 0.5 * c[N.WEAK]
    by_bot = N.composition("night_hard", 4000)["bot"]
    assert by_bot["agent_default"] > 1.3 * by_bot["trackb3"]  # persona bots twice the Track B bots' weight
    # night0 keeps the stand-in version: the agent group is the two Track B bots and runs out at two seats
    c0 = N.composition("night0", 4000)["group"]
    assert c0[N.AGENT] <= 2 + 1e-9 and 1.6 < c0[N.WEAK] / c0[N.DECENT] < 2.4


def test_pool_seat_reads_the_table_seed_from_the_runner_seat_seed(monkeypatch):
    built = []

    class Dummy:
        def __init__(self, name, seed):
            self.name, self.seed, self.last_cost_ns, self.model = name, seed, 123, None

        def use_cost_model(self, on):
            self.model = on

        def act(self, obs):
            return "act:" + self.name

        def hand_end(self, result):
            built.append(("end", self.name))

        def new_table(self, rules, seat, n):
            pass

    monkeypatch.setattr(B, "make_bot", lambda name, seed=None: built.append((name, seed)) or Dummy(name, seed))
    table_seed = 7 * 1_000_003 + 5
    want = N.draw("night", table_seed)
    for rot in range(8):
        for s in range(8):
            seat = N.PoolSeat("night", 1 + (s % 7), seed=table_seed * 64 + rot * 8 + s)
            assert seat.drawn == want[s % 7] and seat.inner.seed == table_seed * 64 + rot * 8 + s
    seat.use_cost_model(True)
    assert seat.inner.model is True and seat.last_cost_ns == 123  # the engine's mode "model" sees the inner bot
    assert seat.act(None) == "act:" + seat.drawn  # the inner bot's own bound method
    assert N.PoolSeat("night", 2, seed=None).drawn == N.draw("night", 0)[1]


class _Spy:
    """Records which bot each pool seat built, with its seed, through the real runner."""

    def __init__(self, monkeypatch):
        self.log = []
        orig = N.PoolSeat.__init__

        def init(seat, pool, slot, seed=None):
            orig(seat, pool, slot, seed)
            self.log.append((seat.table_seed, seed, seat.name, seat.drawn))

        monkeypatch.setattr(N.PoolSeat, "__init__", init)


def test_every_rotation_and_every_hero_swap_sees_the_same_opponents_and_seeds(monkeypatch):
    spy = _Spy(monkeypatch)
    runs = {}
    for hero in ("tag", "nit"):
        spy.log.clear()
        rep = run_tournament(B.field_names(f"night@{hero}"), tables=1, seed=7, rotate=True, mode="model",
                             table_offset=3)
        runs[hero] = [e for e in spy.log if e[1] is not None]  # drop the runner's seedless probe builds
        assert rep.bots[hero].seats == 8
    assert runs["tag"] == runs["nit"]
    log = runs["tag"]
    assert len(log) == 7 * 8  # seven pool seats, eight rotations
    table_seed = 7 * 1_000_003 + 3
    assert {e[0] for e in log} == {table_seed}
    by_slot = {}
    for _, seed, name, drawn in log:
        by_slot.setdefault(name, set()).add(drawn)
        assert seed // 64 == table_seed
    assert all(len(v) == 1 for v in by_slot.values())  # a slot keeps its bot across the rotations
    assert sorted(v.pop() for v in by_slot.values()) == sorted(N.draw("night", table_seed))
    assert N.opponents(B.field_names("night"), table_seed)[1:] == list(N.draw("night", table_seed))


@pytest.fixture
def trackb_unwrapped(monkeypatch):
    """Both Track B bots swallow every exception into a check or fold; unwrap them so an adapter bug reaches the
    engine's counters."""
    from hyperion.sim.field import trackb3, trackb5

    monkeypatch.setattr(trackb3.Agent, "act", trackb3.Agent.decide)

    def decide(obs):
        kind, by = trackb5._decide(obs)
        out = trackb5._legalize(kind, by, obs)
        if out["action"] == "raise":
            trackb5.H["cur"] += out["by"]
        return out

    monkeypatch.setattr(trackb5, "decide", decide)


def test_track_b_bots_play_legal_poker_through_their_kit_adapters(trackb_unwrapped):
    names = ["trackb3", "trackb5", "tag", "pushfold", "loose_aggro", "maniac", "station", "nit"]
    rep = run_tournament(names, tables=6, seed=11, mode="measure")
    for nm in ("trackb3", "trackb5"):
        st = rep.bots[nm].stats
        assert st.calls > 300, nm
        assert st.exceptions == 0 and st.illegal == 0, (nm, st.last_error)
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 6 - sum(Rules().payouts)) < 1e-6


def test_trackb5_keeps_its_profile_per_seat_and_reads_the_rank_order_from_the_rules(trackb_unwrapped):
    from hyperion.sim.field import trackb5

    a, b = B.make_bot("trackb5", 1), B.make_bot("trackb5", 2)
    a.new_table(Rules(), 0, 8)
    b.new_table(Rules(rank_order=(1, 10, 9, 5, 11, 2, 3, 7, 8, 4, 0, 12, 6)), 1, 8)
    assert a._state[0] is not b._state[0] and a._state[1] is not b._state[1]
    a._bind()
    assert trackb5.REMAP == list(range(13)) and trackb5.S["seat"] == 0
    b._bind()
    assert trackb5.REMAP == [1, 10, 9, 5, 11, 2, 3, 7, 8, 4, 0, 12, 6] and trackb5.S["seat"] == 1
    rep = run_tournament(["trackb5", "trackb5", "tag", "pushfold", "nit", "station", "maniac", "naive"], tables=3,
                         seed=5, mode="measure")
    assert rep.bots["trackb5"].stats.exceptions == 0 and rep.bots["trackb5"].stats.illegal == 0


def test_trackb3_plays_without_its_bounty_patch():
    from hyperion.sim.field import trackb3

    B.make_bot("trackb3")
    assert trackb3.BOUNTY_CHIPS == 0  # plain hold'em pays no bounty


def test_night_field_smoke_runs_in_model_mode():
    # conservation and legality only; the hero seat is a cheap bot so the run is quick
    members = B.field_names("night@tag")
    rep = run_tournament(members, tables=3, seed=2, rotate=False, mode="model")
    assert set(rep.bots) == set(members)
    for name, b in rep.bots.items():
        assert b.stats.illegal == 0, name
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 3 - sum(Rules().payouts)) < 1e-6


@pytest.mark.parametrize("name", sorted(PERSONA_UNWRAP))
def test_persona_bots_play_legal_poker_with_their_exceptions_let_through(name, monkeypatch):
    bot = B.make_bot(name)
    assert isinstance(bot, B.PersonaBot) and type(bot.impl).__module__ == f"hyperion.sim.field.{name}"
    assert "kit" not in sys.modules  # the brief's kit is importable only while a persona bot loads
    PERSONA_UNWRAP[name](type(bot.impl), monkeypatch)
    names = [name, "tag", "pushfold", "loose_aggro", "maniac", "station", "nit", "trackb5"]
    rep = run_tournament(names, tables=6, seed=13, mode="measure")
    st = rep.bots[name].stats
    assert st.calls > 300 and st.exceptions == 0 and st.illegal == 0, st.last_error
    bot.new_table(Rules(), 3, 8)  # the adapter passes payouts and history, which the brief allows
    assert bot.kit_rules(Rules(), 8)["payouts"] == list(Rules().payouts)


def test_agent_montecarlo_leaves_the_collector_on_samples_from_its_own_seat_rng_and_replays_in_model_mode():
    import gc

    from hyperion.sim.field import agent_montecarlo as m

    bot = B.make_bot("agent_montecarlo", 5)
    assert gc.isenabled()  # it disables the collector at import; field.load turns it back on
    names = ["agent_montecarlo", "agent_pushfold", "tag", "station", "maniac", "nit", "naive", "random"]

    def once():
        bots = [B.make_bot(n, seed=s) for s, n in enumerate(names)]
        r = play_table(bots, Rules(), seed=11, mode="model")
        return r.points, r.hands, r.stacks

    assert once() == once()  # mode "model": its clock advances 3.5 us a read, sample counts no longer follow the host
    bot.use_cost_model(True)  # what the engine does at table start in mode "model"
    bot.new_table(Rules(), 0, 8)
    bot.act(_flop_obs())
    assert m._rand == bot._rand and m._perf == bot._clock  # bound into the module before its decision
    bot.use_cost_model(False)  # strict and measure: the wall clock, as built
    bot.act(_flop_obs())
    assert m._perf is time.perf_counter


def _flop_obs():
    from hyperion.core.types import ActionKind, Observation, parse_cards

    n = 8
    return Observation(hole=parse_cards("AsKd"), board=parse_cards("Ah7c2d"), street=1, seat=0, button=7,
                       stacks=[1900] * n, bets=[0] * n, in_hand=[True, True] + [False] * 6, pot=200, to_call=0,
                       min_raise=20, max_raise=1900, legal=frozenset({ActionKind.FOLD, ActionKind.CHECK,
                                                                      ActionKind.RAISE}), hand_no=3,
                       blinds=(10, 20), history=[])


def test_agent_pushfold_skips_its_wall_clock_guard_in_model_mode_only():
    bot = B.make_bot("agent_pushfold", 1)
    bot.use_cost_model(True)
    assert bot.impl._el() == 0.0
    bot.use_cost_model(False)
    bot.impl._t0 = time.perf_counter() - 1.0
    assert bot.impl._el() > 1e5  # as built: microseconds since its act() began


def test_rival2_plays_a_fixed_sampler_in_model_mode_and_as_built_otherwise():
    from hyperion.sim.rivals import rival2 as R2

    bot = B.make_bot("rival2", 1)
    assert R2.MC_N == R2.MC_BOARDS  # imported with its clock held still: complete tables at any load
    bot.use_cost_model(True)
    assert (bot.impl.MC_BUDGET_US, bot.impl.MC_MAX) == (1e9, B.Rival2Bot.MODEL_SAMPLES)
    bot.use_cost_model(False)
    assert (bot.impl.MC_BUDGET_US, bot.impl.MC_MAX) == (R2.Bot.MC_BUDGET_US, R2.Bot.MC_MAX)
    assert "equity_mc" not in bot.impl.__dict__


@pytest.mark.parametrize("field", ["night", "night_hard"])
def test_night_fields_replay_exactly_in_model_mode(field):
    # every seat, every rotation: two runs of the same seeds give the same points, places and hands
    def once():
        rep = run_tournament(B.field_names(f"{field}@hero"), tables=2, seed=7, rotate=True, mode="model",
                             hero_config={"panic_after": 10 ** 9}, table_offset=11)
        return rep.hands, {nm: (b.samples, b.places, b.busts) for nm, b in rep.bots.items()}

    assert once() == once()
