"""The climb's outside field (docs/drills/goal-plan.md): four one-hour builds by fresh agents with no repo access, frozen
copies below an origin header, played through the red-team adapter; never in a night pool, never tuned on."""
import hashlib
import sys
import time
from pathlib import Path

import pytest

from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.field import night as N
from hyperion.sim.runner import run_tournament

ROOT = Path(__file__).resolve().parents[1]
FROZEN = {  # registry name -> (archived original, copy in the package, header lines, md5 of the original)
    "out_veterans": ("docs/drills/field/outside_veterans_bot.py", "hyperion/sim/field/outside_veterans.py", 6,
                     "bffa539c16eabb4836c4518c5ba1a660"),
    "out_selfplay": ("docs/drills/field/outside_selfplay_bot.py", "hyperion/sim/field/outside_selfplay.py", 6,
                     "5e739fa4f8f1833d2ea7212a28ef9aef"),
    "out_lag": ("docs/drills/field/outside_lag_bot.py", "hyperion/sim/field/outside_lag.py", 6,
                "7f2cf88729b2db29a6d7d4c425843cce"),
    "out_quants": ("docs/drills/field/outside_quants_bot.py", "hyperion/sim/field/outside_quants.py", 6,
                   "27d9b2cb8a03c9e2ae65260b2a9c0b7b"),
    "elite1": ("docs/drills/field/elite1_bot.py", "hyperion/sim/field/elite1.py", 6, "9bf36037f33d9e836a33b9d29641488b"),
    "elite2": ("docs/drills/field/elite2_bot.py", "hyperion/sim/field/elite2.py", 6, "70c29e1754bbe6a555cea331468756f3"),
    "elite3": ("docs/drills/field/elite3_bot.py", "hyperion/sim/field/elite3.py", 6, "c5e956bd211896e22bafe0f2acfeeed4"),
    "elite4": ("docs/drills/field/elite4_bot.py", "hyperion/sim/field/elite4.py", 6, "063caf8cddf45881e1f125ea822943cc"),
    "elite5": ("docs/drills/field/elite5_bot.py", "hyperion/sim/field/elite5.py", 6, "3465ff11f8f85ab20d7856af86e5b97a"),
    "out_cfr": ("docs/drills/field/out_cfr_bot.py", "hyperion/sim/field/out_cfr.py", 6, "23e6881818195b0d110e2b79ecbaa861"),
    "out_press": ("docs/drills/field/out_press_bot.py", "hyperion/sim/field/out_press.py", 6, "1d724a694a88ab2b05df763801dddb99"),
    "out_charts": ("docs/drills/field/out_charts_bot.py", "hyperion/sim/field/out_charts.py", 6,
                   "7ada9e818fe730583053e7b0c6f7a18b"),
    "out_reads": ("docs/drills/field/out_reads_bot.py", "hyperion/sim/field/out_reads.py", 6,
                  "e51fb4390f9ed57c44c003a474151afc"),
    "out_o9": ("docs/drills/field/out_o9_bot.py", "hyperion/sim/field/out_o9.py", 6, "f85066a0bd7e92551dad61a0d559bc89"),
    "out_o10": ("docs/drills/field/out_o10_bot.py", "hyperion/sim/field/out_o10.py", 6,
                "bedcbd0c079f847c005af61f8807db10"),
    "out_o11": ("docs/drills/field/out_o11_bot.py", "hyperion/sim/field/out_o11.py", 6,
                "5f92fb3b1b7519f06b79234d41cfa5ba"),
}
ELITE = {"elite1", "elite2", "elite3", "elite4", "elite5"}


@pytest.mark.parametrize("name", sorted(FROZEN))
def test_frozen_source_matches_its_archive_and_md5(name):
    archive, copy, header, md5 = FROZEN[name]
    raw = (ROOT / archive).read_bytes()
    assert hashlib.md5(raw).hexdigest() == md5
    lines = (ROOT / copy).read_bytes().splitlines(keepends=True)
    assert all(ln.startswith(b"#") for ln in lines[:header])
    assert md5.encode() in b"".join(lines[:header])
    assert b"".join(lines[header:]) == raw


def test_outside_bots_are_registered_and_in_no_pool():
    assert set(FROZEN) <= set(B.REGISTRY)
    assert set(B.OUTSIDE) | set(B.OUTSIDE_B) | set(B.OUTSIDE_C) | set(B.OUTSIDE_D) == set(FROZEN) - ELITE
    for name, members in B.FIELDS.items():  # the second wave is held out: judge fields only
        if (set(B.OUTSIDE_B) | set(B.OUTSIDE_C) | set(B.OUTSIDE_D)) & set(members):
            assert name.startswith("outside"), name
    for name, pool in N.POOLS.items():
        drawn = {b for _, _, ms in pool.groups for b, _ in ms}
        assert not drawn & set(FROZEN), name
    assert B.field_names("outside")[:5] == ["hero", *B.OUTSIDE]
    assert B.field_names("outside_strong@hybrid3_x")[0] == "hybrid3_x"


def test_elite3_is_held_out_of_every_tuning_field():
    for name, members in B.FIELDS.items():
        if "elite3" in members or "elite5" in members:
            assert name.startswith("elite_judge") or name in ("outside_b", "outside_c", "outside_d_strong"), name  # judges


@pytest.mark.parametrize("field", ["outside", "outside_strong", "elite", "elite_night", "elite_judge", "elite_b",
                                   "elite_judge_b", "outside_b", "outside_c", "outside_d", "outside_d_strong"])
def test_outside_fields_play_legally_and_replay_exactly_in_model_mode(field):
    # Hero's panic mode reads the wall clock (under heavy load a replay can differ); climb_accept turns it off, so does
    # this
    kw = dict(seed=1, rotate=True, mode="model", table_offset=30000, hero_config={"panic_after": 10 ** 9})
    a = run_tournament(B.field_names(field), 2, **kw)
    b = run_tournament(B.field_names(field), 2, **kw)
    for nm, rep in a.bots.items():
        assert rep.stats.exceptions == 0 and rep.stats.illegal == 0, nm
        assert rep.samples == b.bots[nm].samples, nm
    assert abs(sum(sum(r.samples) for r in a.bots.values()) / len(a.bots["hero"].samples) - 36.0) < 1e-6


ROOM_D = ["out_o9", "out_o10", "out_o11"]


def test_the_fourth_waves_fields_are_seated_as_stated():
    assert B.field_names("outside_d") == ["hero", *ROOM_D, "night.1", "night.2", "night.3", "night.4"]
    assert B.field_names("outside_d_strong") == ["hero", *ROOM_D, "out_reads", "out_cfr", "elite5", "rival4"]
    for bot in ROOM_D:
        tag = bot[4:]
        assert B.field_names(f"outside_d_{tag}_hu") == ["hero", bot] and B.FIELD_PLAYERS[f"outside_d_{tag}_hu"] == 2
        assert B.field_names(f"outside_d_{tag}_3") == ["hero", bot, "night.1"] and B.FIELD_PLAYERS[f"outside_d_{tag}_3"] == 3


@pytest.mark.parametrize("bot", ROOM_D)
@pytest.mark.parametrize("fmt,players,payouts", [("hu", 2, (10, 7)), ("3", 3, (10, 7, 5))])
def test_the_fourth_waves_short_cells_play_legally_and_replay_exactly(bot, fmt, players, payouts):
    kw = dict(seed=1, rotate=True, mode="model", table_offset=30000, hero_config={"panic_after": 10 ** 9},
              rules=Rules(n_players=players, payouts=payouts))
    a = run_tournament(B.field_names(f"outside_d_{bot[4:]}_{fmt}"), 3, **kw)
    b = run_tournament(B.field_names(f"outside_d_{bot[4:]}_{fmt}"), 3, **kw)
    for nm, rep in a.bots.items():
        assert rep.stats.exceptions == 0 and rep.stats.illegal == 0, nm
        assert rep.samples == b.bots[nm].samples and rep.places == b.bots[nm].places, nm
    assert abs(sum(sum(r.samples) for r in a.bots.values()) / 3 - sum(payouts)) < 1e-6


@pytest.mark.parametrize("bot", ROOM_D)
def test_in_model_mode_the_wall_clock_never_reaches_a_time_guard(bot, monkeypatch):
    # a host so slow that every read of the real clock is a second late: as built each guard would cut its work
    def play():
        return run_tournament([bot, "tag"], 4, seed=2, rotate=True, mode="model", table_offset=30000,
                              rules=Rules(n_players=2, payouts=(10, 7))).bots[bot].samples

    quiet = play()
    now = [0.0]

    def slow():
        now[0] += 1.0
        return now[0]

    monkeypatch.setattr(time, "perf_counter", slow)
    assert play() == quiet


@pytest.mark.parametrize("bot", ROOM_D)
def test_the_modules_clock_is_fixed_in_model_mode_and_real_otherwise(bot):
    b = B.make_bot(bot, seed=5)
    b.use_cost_model(True)
    b.new_table(Rules(), 0, 8)
    assert b.fixed_speed
    t0 = b._clock()
    assert b._clock() - t0 == pytest.approx(b.STEP_US * 1e-6) and b.STEP_US > 0
    # bound at act(), after the module loaded: nothing an import or a reload does can lose it
    res = run_tournament([bot, "tag"], 1, seed=3, rotate=False, mode="model", table_offset=1,
                         rules=Rules(n_players=2, payouts=(10, 7)))
    assert res.bots[bot].stats.calls > 0 and sys.modules[type(b.impl).__module__].time is not time
    run_tournament([bot, "tag"], 1, seed=3, rotate=False, mode="measure", table_offset=1,
                   rules=Rules(n_players=2, payouts=(10, 7)))
    assert sys.modules[type(b.impl).__module__].time is time


@pytest.mark.parametrize("bot", ROOM_D)
def test_each_seat_draws_its_own_stream_at_every_table(bot):
    a, b, c = B.make_bot(bot, seed=11), B.make_bot(bot, seed=11), B.make_bot(bot, seed=12)
    for x in (a, b, c):
        x.new_table(Rules(), 0, 8)
    first = a.impl.rng.random()
    assert b.impl.rng.random() == first and c.impl.rng.random() != first
    a.new_table(Rules(), 0, 8)
    assert a.impl.rng.random() == first  # reseeded, not continued


def test_a_time_guard_that_trips_cuts_the_same_work_on_every_run():
    # the clock forced past out_o9's and out_o10's 500 us: the guard now trips at its fixed read, and replays
    class Fast(B.OutO9Bot):
        STEP_US = 400.0

    class Fast10(B.OutO10Bot):
        STEP_US = 400.0

    B.REGISTRY["out_o9_fast"] = Fast
    B.REGISTRY["out_o10_fast"] = Fast10
    try:
        kw = dict(seed=2, rotate=True, mode="model", table_offset=30000, rules=Rules(n_players=3, payouts=(10, 7, 5)))
        names = ["out_o9_fast", "out_o10_fast", "tag"]
        a, b = run_tournament(names, 3, **kw), run_tournament(names, 3, **kw)
        assert all(a.bots[n].samples == b.bots[n].samples for n in names)
    finally:
        del B.REGISTRY["out_o9_fast"], B.REGISTRY["out_o10_fast"]
