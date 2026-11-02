"""S2's fixes against the exploiter (docs/drills/s2-exploit-fixes-log.md): each behind a dial that defaults to the
shipped play (tests/test_ship.py replays rival 3 as built at the defaults); here each one reaches the decisions it
names, and the 3-bet reads count what they say."""
import pytest

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.hybrid.core3 import v3_scan
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table

from .test_ship import QUIET, _Recorder

ROOM = ["hero", "exploiter1", "loose_aggro", "tag", "maniac", "pushfold", "station", "nit"]


def _scan(hist, me=2, others_w=0.5):
    o, n = [0.0] * 8, [0.0] * 8
    v3_scan(hist, me, others_w, o, n)
    return o, n


def test_v3_scan_counts_each_reply_to_the_open_until_the_first_reraise():
    o, n = _scan([(0, ("fold", 0)), (1, ("fold", 0)), (2, ("raise", 50)), (3, ("fold", 0)), (4, ("raise", 150)),
                  (5, ("fold", 0)), (2, ("call", 0)), (4, ("raise", 100))])
    assert o == [0, 0, 0, 1, 1, 0, 0, 0] and n == [0, 0, 0, 0, 1, 0, 0, 0]  # seats before the open, after the 3-bet: no
    o, n = _scan([(0, ("raise", 50)), (1, ("call", 0)), (2, ("call", 0)), (0, ("raise", 100))])
    assert o == [0, 0.5, 0.5, 0, 0, 0, 0, 0] and n == [0] * 8  # another seat's open weighs others_w; a flop bet is not
    o, n = _scan([(0, ("call", 0)), (1, ("fold", 0)), (2, ("check", 0)), (0, ("raise", 40))])
    assert o == [0] * 8 and n == [0] * 8  # limped preflop: the first raise is a flop bet


def _digest(dials, table, names=ROOM, rules=None):
    seed = 7 * 1_000_003 + table
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    for b in bots:
        if hasattr(b, "use_cost_model"):
            b.use_cost_model(True)
    bot = ship.make_bot("composite", {**QUIET, "late_us": 1e9, **dials}, seed=seed * 64)
    rec = bots[0] = _Recorder(bot)
    play_table(bots, rules or Rules(), seed=seed, mode="model")
    return rec.h.hexdigest(), bot


@pytest.mark.parametrize("dials", [{"r3.v3_defend": True}, {"r3.bb_defend": True}, {"r3.open_vs3b_scale": 1.0},
                                   {"hero.postflop.wide_bettor_from": 0.5}])
def test_each_s2_dial_reaches_the_decisions(dials):
    # against the dial switched off (r3.v3_defend ships on since the climb's batch 4, so {} is not "off" for it)
    off = {"r3.v3_defend": False} if "r3.v3_defend" in dials else {}
    assert any(_digest(dials, t)[0] != _digest(off, t)[0] for t in range(5)), dials


def test_the_3bet_defence_reads_the_exploiter_and_its_folds_to_our_4bets():
    _, bot = _digest({"r3.v3_defend": True}, 0)
    core = bot.core.members[0].core
    ex = ROOM.index("exploiter1")
    assert core.v3o[ex] > 0 and core.v3n[ex] / core.v3o[ex] > 0.3  # it 3-bets our opens far more than the prior
    assert core.v4o[ex] > 0 and core.v4f[ex] <= core.v4o[ex]


def test_heads_up_with_every_s2_dial_replays_exactly():
    d = {"r3.v3_defend": True, "r3.bb_defend": True, "hero.postflop.wide_bettor_from": 0.5}
    r = Rules(n_players=2, payouts=(10, 7))
    assert _digest(d, 1, ["hero", "exploiter1"], r)[0] == _digest(d, 1, ["hero", "exploiter1"], r)[0]
