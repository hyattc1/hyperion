"""tools/profile.py: the Hero-seat tracer books every decision by section, its chip attribution sums to the bot's net
chips, a job plays exactly the runner's tables, and the report ranks bots per section."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table
from hyperion.sim.runner import run_tournament

_PATH = Path(__file__).resolve().parents[1] / "tools" / "profile.py"
_spec = importlib.util.spec_from_file_location("skill_profile", _PATH)  # not `profile`: that is the stdlib's
P = importlib.util.module_from_spec(_spec)
sys.modules["skill_profile"] = P
_spec.loader.exec_module(P)

NAMES = ["tag", "pushfold", "maniac", "station", "nit", "naive", "loose_aggro", "random"]


@pytest.fixture(autouse=True)
def _registry_restored():
    """seat_name registers `<bot>_seat` aliases; keep them out of the other tests' registry."""
    saved, saved_hybrid = dict(B.REGISTRY), B.HYBRID_CONFIG
    yield
    B.REGISTRY.clear()
    B.REGISTRY.update(saved)
    B.HYBRID_CONFIG = saved_hybrid


def test_chips_booked_by_section_sum_to_the_net_chips_and_busts_are_counted():
    rules = Rules(blind_levels=((10, 20),))  # one level, so chips_bb * 20 is chips
    counts = P._new_counts()
    net = busts = 0
    for t in range(5):
        bots = [B.make_bot(n, seed=t * 64 + s) for s, n in enumerate(NAMES)]
        bots[0] = P.Tracer(bots[0], counts)
        res = play_table(bots, rules, seed=t, mode="model")
        net += res.stacks[0] - rules.starting_stack
        busts += not res.survived[0]
    assert abs(sum(counts["chips_bb"]) * 20 - net) < 1e-6
    assert sum(counts["busts"]) == busts
    d = counts["dec"]
    assert sum(d) > 100 and d[P.BLINDS] == 0
    for i in range(len(P.ROWS)):  # every decision is one of fold, check, call, raise
        assert counts["fold"][i] + counts["check"][i] + counts["call"][i] + counts["raise"][i] == d[i]
        assert counts["vpip"][i] == counts["call"][i] + counts["raise"][i]
        assert counts["sd_won"][i] <= counts["sd"][i]


def test_a_job_plays_the_runner_tables_exactly():
    res = P.run_job(("realistic", "tag", 3, 5, "model", None, 7))
    B.HYBRID_CONFIG = None
    rep = run_tournament(B.field_names("realistic@tag_seat"), 2, seed=7, rotate=True, mode="model",
                         hero_config=P.MODEL_HERO_CONFIG, table_offset=3)
    assert res["samples"] == rep.bots["tag_seat"].samples  # realistic seats tag already: the profiled copy is an alias
    assert res["seats"] == 16 and sum(res["counts"]["dec"]) > 0


def test_seat_name_aliases_a_bot_the_field_already_seats():
    assert P.seat_name("realistic", "hero") == "hero"
    assert P.seat_name("realistic", "rival1") == "rival1_seat"
    assert issubclass(B.REGISTRY["rival1_seat"], B.RivalBot)
    assert P.seat_name("night", "rival1") == "rival1"  # pool seats are not the bot's name


def test_merge_refuses_overlapping_seeds_and_the_report_ranks_bots_per_section(tmp_path):
    for bot in ("tag", "nit"):
        r = P.run_job(("strong", bot, 0, 1, "model", None, 7))
        d = tmp_path / "strong"
        d.mkdir(exist_ok=True)
        (d / f"{bot}.json").write_text(json.dumps(P._merge(None, r)))
        with pytest.raises(ValueError):
            P._merge(P._merge(None, r), r)
    text = P.report([tmp_path])
    assert "## `strong`" in text and "short-stack play" in text and "facing an all-in" in text
    assert "1. **" in text and "| bot | 1 | 2 |" in text
