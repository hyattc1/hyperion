"""Batch 7's scoping dials: S7 (the specialist's heads-up routes behind its looseness gate) and S20's R5 (its
three-handed route behind the strong-table read) share one member, so each one's settings are scoped to its own
decisions: `short_strong` names sections, `short.like_max_alive` keeps the like gates heads-up, and
`short.defer_three` / `short.defer_3bet_three` carry R5's defer settings on three-handed decisions only. Each part
alone, with the scoping on, plays exactly as it was accepted (the digests here); all off by default."""
import os

import pytest

from hyperion.core.types import Rules
from hyperion.strategy import short as SH
from hyperion.strategy.tables import TABLES_DIR

from hyperion.compose.bot import BATCH7_OFF

from .test_s2_dials import _digest

R3 = Rules(n_players=3, payouts=(10, 7, 5))
THREE = ["hero", "exploiter2", "loose_aggro"]
has_table = pytest.mark.skipif(not os.path.exists(os.path.join(TABLES_DIR, "extra", "short_3b.json")),
                               reason="no second three-handed table")
ON3 = {**BATCH7_OFF, "short_route": "pre_3way=short", "short.three2": True, "short.defer_3bet": 1.0}
S7 = {**BATCH7_OFF, "short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
      "short.pre_open_min": 0.65, "short.like_probe": 0.75, "short.like_bet": 0.6, "short.like_pfr": 0.3,
      "short.like_vpip_min": 0.5, "short.like_vpip_max": 0.88}
SCOPE = {"short.like_max_alive": 2, "short.defer_three": "dead,station,maniac,random,nit",
         "short.defer_3bet_three": 0.25}


def test_the_scoping_dials_are_off_by_default():
    from hyperion.compose import bot as CB

    p = SH.ShortParams()
    assert p.like_max_alive == 0 and p.defer_three is None and p.defer_3bet_three is None
    assert CB.ComposeConfig().short_strong is False


@has_table
def test_short_strong_by_section_name():
    for rr in (0.99, 0.01):
        on = _digest({**ON3, "short_strong": True, "strong_rr": rr}, 1, THREE, R3)[0]
        assert _digest({**ON3, "short_strong": "pre_3way", "strong_rr": rr}, 1, THREE, R3)[0] == on
    # a gate on another section leaves this route open while the table reads weak
    d, bot = _digest({**ON3, "short_strong": "pre_hu", "strong_rr": 0.99}, 1, THREE, R3)
    assert bot.core.counts["short"] > 0 and d == _digest({**ON3, "strong_rr": 0.99}, 1, THREE, R3)[0]


@has_table
def test_the_like_gates_stay_heads_up_with_like_max_alive():
    _, shut = _digest({**ON3, "short.like_vpip_min": 0.99}, 1, THREE, R3)
    assert shut.core.counts.get("short", 0) == 0  # no seat plays that loose: the gate shuts the three-handed route
    d = _digest({**ON3, "short.like_vpip_min": 0.99, "short.like_max_alive": 2}, 1, THREE, R3)[0]
    assert d == _digest(ON3, 1, THREE, R3)[0]


@has_table
def test_the_three_handed_defer_settings():
    _, shut = _digest({**ON3, "short.defer_3bet": 0.0}, 1, THREE, R3)  # every seat reads as a 3-bettor: F plays
    assert shut.core.counts.get("short", 0) == 0
    assert _digest({**ON3, "short.defer_3bet": 0.0, "short.defer_3bet_three": 1.0}, 1, THREE, R3)[0] == \
        _digest(ON3, 1, THREE, R3)[0]
    base = {**ON3, "short.defer": ""}
    assert _digest({**ON3, "short.defer": "dead,station,maniac,random,nit,tag,lag", "short.defer_three": ""}, 1,
                   THREE, R3)[0] == _digest(base, 1, THREE, R3)[0]


@pytest.mark.parametrize("table", [0, 1, 2])
def test_s7_alone_plays_as_accepted_with_the_scoping_on(table):
    d7, bot = _digest(S7, table, THREE, R3)
    assert table != 0 or bot.core.counts["short"] > 0  # table 0 reaches heads-up with exploiter 2: S7 plays
    assert _digest({**S7, **SCOPE, "short_strong": "pre_3way"}, table, THREE, R3)[0] == d7


@has_table
@pytest.mark.parametrize("table", [0, 1, 2])
def test_r5_alone_plays_as_accepted_with_the_scoping_on(table):
    r5 = {**BATCH7_OFF, "short_route": "pre_3way=short", "short.three2": True, "short.three2_file": "3b", "short.defer_3bet": 0.25,
          "short_strong": True, "short.three2_keep_defence": True, "short.three2_roles": "btn,sb",
          "short.defer": "dead,station,maniac,random,nit", "short.three2_seat_rr": 1, "strong_rr": 0.01}
    scoped = {**r5, "short.defer_3bet": 0.4, "short.defer": "dead,station", "short_strong": "pre_3way",
              "short.defer_3bet_three": 0.25, "short.defer_three": "dead,station,maniac,random,nit",
              "short.like_max_alive": 2}
    d5, bot = _digest(r5, table, THREE, R3)
    assert table != 1 or bot.core.counts["short"] > 0  # table 1: the three-handed route plays
    assert _digest(scoped, table, THREE, R3)[0] == d5
