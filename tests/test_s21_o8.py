"""O8 (docs/drills/climb/s21-log.md, "O8"): rival 3's first-in clause does not open a hand the measured price says
loses when called (hyperion/hybrid/open_ev.py) where the seats behind fold less than veto_t to everyone's opens this
table (r3.veto_read, r3.open_veto, r3.veto_t / veto_prior / veto_prior_n)."""
import json
from dataclasses import replace
from pathlib import Path

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.hybrid.core3 import Rival3Core, any_scan
from hyperion.hybrid.open_ev import TABLE, open_ev

from .test_s16b_open import _digest
from .test_s21_o5 import O5

O8 = {"r3.veto_read": True, "r3.open_veto": True}
ST = [2000] * 8


def test_the_lookup_is_the_measured_table():
    d = json.loads((Path(__file__).resolve().parents[1] / "docs/drills/climb/s21-o7-table.json").read_text())
    for pb in range(10):
        p = 0.1 * pb + 0.05
        for nb in range(1, 8):
            for di, eff in enumerate((15.0, 30.0, 60.0)):
                assert abs(open_ev(p, nb, eff) - d["table"][pb][min(nb, 5) - 1][di]) < 1e-9
    assert open_ev(0.0, 1, 10.5) == TABLE[0][0][0] and open_ev(0.999, 9, 400) == TABLE[9][4][2]
    assert open_ev(0.1, 2, 20.0) == TABLE[1][1][0] and open_ev(0.0999, 2, 20.01) == TABLE[0][1][1]  # band edges


def test_any_scan_reads_every_answer_to_the_first_in_raise():
    h = [(3, ('fold', 0)), (4, ('raise', 50)), (5, ('call', 0)), (6, ('fold', 0)), (7, ('raise', 150)), (4, ('fold', 0))]
    assert any_scan(h, 7, ST) == [(5, 0), (6, 1), (7, 0)]
    assert any_scan([(4, ('call', 0)), (5, ('raise', 60))], 7, ST) == []  # a limp first
    assert any_scan([(4, ('raise', 1990)), (5, ('fold', 0))], 7, ST) == []  # all-in: not an open
    assert any_scan([(6, ('raise', 60)), (7, ('fold', 0))], 7, ST) == [(7, 1)]  # the small blind's open


def _core(**kw):
    c = Rival3Core()
    c.k = replace(c.k, veto_read=True, open_veto=True, **kw)
    c._v3_reset()
    return c


def test_the_switch_and_the_price():
    c = _core()
    behind = [5, 6, 7]
    assert abs(c.veto_rate(behind) - 0.80) < 1e-12  # no answers: the prior, not under 0.80: closed
    assert not c.open_vetoed(behind, 0.2, 1.5, 0.95, 60.0)
    for s in behind:
        c.anyn[s], c.anyf[s] = 10.0, 6.0  # they fold 0.6 to everyone's opens
    assert abs(c.veto_rate(behind) - (18.0 + 8.0) / 40.0) < 1e-12
    assert c.open_vetoed(behind, 0.2, 1.5, 0.95, 60.0)  # 0.2 x 1.5 + 0.8 x price < 0: no open
    assert not c.open_vetoed(behind, 0.9, 1.5, 0.95, 60.0)  # the blinds come in often enough
    assert not c.open_vetoed([], 0.2, 1.5, 0.95, 60.0)
    c.k = replace(c.k, veto_t=0.6)  # 0.65 is not under 0.6: closed
    assert not c.open_vetoed(behind, 0.2, 1.5, 0.95, 60.0)


def test_off_by_default_nothing_counted_and_on_it_counts_replays_and_moves_play():
    _, bot = _digest({}, 0)
    assert sum(bot.core.base.core.anyn) == 0
    h, bot = _digest({**O5, **O8}, 0)
    core = bot.core.base.core
    assert sum(core.anyn) > 0 and sum(core.anyf) <= sum(core.anyn)
    assert h == _digest({**O5, **O8}, 0)[0]
    assert any(_digest({**O5, **O8}, t)[0] != _digest(O5, t)[0] for t in range(4))


def test_switch_never_on_plays_as_o5():
    for t in range(2):
        assert _digest({**O5, **O8, "r3.veto_t": 0.0}, t)[0] == _digest(O5, t)[0]


def test_twist_and_straddle_tables_play_as_f():
    from hyperion.drills import variants as V

    for rules in (V.get("bounty", seed=7).rules, Rules(straddle=2)):
        assert _digest({**O5, **O8}, 0, rules=rules)[0] == _digest({}, 0, rules=rules)[0]


def test_ship_dials_leave_o8_off():
    k = ship.make_bot("composite", {}).core.base.core.k
    assert not k.veto_read and not k.open_veto
