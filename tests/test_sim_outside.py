"""The climb's outside field (docs/drills/goal-plan.md): four one-hour builds by fresh agents with no repo access, frozen
copies below an origin header, played through the red-team adapter; never in a night pool, never tuned on."""
import hashlib
from pathlib import Path

import pytest

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
    assert set(FROZEN) <= set(B.REGISTRY) and set(B.OUTSIDE) | set(B.OUTSIDE_B) == set(FROZEN) - ELITE
    for name, members in B.FIELDS.items():  # the second wave is held out: judge fields only
        if set(B.OUTSIDE_B) & set(members):
            assert name.startswith("outside"), name
    for name, pool in N.POOLS.items():
        drawn = {b for _, _, ms in pool.groups for b, _ in ms}
        assert not drawn & set(FROZEN), name
    assert B.field_names("outside")[:5] == ["hero", *B.OUTSIDE]
    assert B.field_names("outside_strong@hybrid3_x")[0] == "hybrid3_x"


def test_elite3_is_held_out_of_every_tuning_field():
    for name, members in B.FIELDS.items():
        if "elite3" in members or "elite5" in members:
            assert name.startswith("elite_judge") or name == "outside_b", name  # judge fields only


@pytest.mark.parametrize("field", ["outside", "outside_strong", "elite", "elite_night", "elite_judge", "elite_b",
                                   "elite_judge_b", "outside_b"])
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
