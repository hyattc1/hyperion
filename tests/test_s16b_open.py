"""S16b's open-answer read (docs/drills/climb/s16b-log.md): rival 3's core counts how each seat answers my first-in
raises (r3.oa_read: its steal price; exploit.open_read: the layer's steal_min_fold), against a per-table rate by
position shrunk to the survey's priors."""
from dataclasses import replace

from hyperion import ship
from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.core.types import parse_cards as parse
from hyperion.hybrid.core3 import Rival3Core, oa_scan
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table
from hyperion.strategy.exploit import Exploit, ExploitParams

from .test_ship import QUIET, _Recorder

R, C, F = ActionKind.RAISE, ActionKind.CALL, ActionKind.FOLD
ON = {"r3.oa_read": True, "exploit.open_read": True}
STRONG = ["hero", "elite1", "elite2", "rival1", "rival2", "rival3", "agent_pushfold", "agent_default"]


def test_oa_scan_reads_answers_to_my_first_in_raise_only():
    h = [(0, ('fold', 0)), (1, ('raise', 50)), (2, ('fold', 0)), (3, ('call', 0)), (4, ('raise', 150)),
         (5, ('fold', 0)), (1, ('fold', 0))]
    assert oa_scan(h, 1, 2000, 6, 7) == [(2, 0, True, False), (3, 0, False, False), (4, 0, False, True)]
    assert oa_scan([(0, ('call', 0)), (1, ('raise', 60))], 1, 2000, 6, 7) == []  # a limp first: not first in
    assert oa_scan([(1, ('raise', 2000)), (2, ('fold', 0))], 1, 2000, 6, 7) == []  # all-in: not an open
    assert oa_scan([(5, ('raise', 50)), (6, ('fold', 0)), (7, ('call', 0))], 5, 2000, 6, 7) == [
        (6, 1, True, False), (7, 2, False, False)]  # the blinds by position


def test_oa_fold_is_the_table_rate_by_position_plus_the_seat_excess():
    c = Rival3Core()
    c.k = replace(c.k, oa_read=True)
    c._v3_reset()
    k = c.k
    assert abs(c.oa_fold(3, 2) - k.oa_mu_bb) < 1e-12 and abs(c.oa_fold(3, 0) - k.oa_mu_other) < 1e-12
    c.oa_tn[2], c.oa_tf[2] = 20.0, 8.0  # this table's big blinds folded 8 of 20
    t = (8.0 + k.oa_mu_bb * k.oa_st) / (20.0 + k.oa_st)
    assert abs(c.oa_fold(3, 2) - t) < 1e-12
    c.oan[3], c.oax[3] = 10.0, 2.0  # seat 3 folded two more than the table's rates said
    assert abs(c.oa_fold(3, 2) - (t + 2.0 / (10.0 + k.oa_s))) < 1e-12
    c.k = replace(k, oa_min_n=11.0)
    assert abs(c.oa_fold(3, 2) - t) < 1e-12


def test_layer_steal_reads_the_open_answer_read():
    ex = Exploit(ExploitParams(steal_min_fold=0.7, open_read=True))
    ex.new_table(8, 7)
    obs = Observation(hole=parse("7c 2d"), board=(), street=0, seat=7, button=7, stacks=[2000] * 8,
                      bets=[10, 20, 0, 0, 0, 0, 0, 0], in_hand=[True] * 8, pot=0, to_call=20, min_raise=40,
                      max_raise=2000, legal=frozenset({F, C, R}), hand_no=0, blinds=(10, 20), history=[])
    ex.observe(obs)
    for s in (0, 1):
        ex.fold[s][0], ex.faced[s][0] = 0.95 * 6.0, 6.0
    assert ex.open_fold is None and ex.override(obs, Action.fold()) is not None  # no reader: fold_rate (0.9 > 0.7)
    seen = []
    ex.open_fold = lambda s, pos: seen.append((s, pos)) or 0.8
    assert ex.override(obs, Action.fold()) is None  # 0.8 x 0.8 < 0.7: no steal
    assert seen == [(0, 1), (1, 2)]
    ex.open_fold = lambda s, pos: 0.9
    assert ex.override(obs, Action.fold()) is not None


def _digest(dials, table, names=STRONG, rules=None):
    seed = 13 * 1_000_003 + table
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    for b in bots:
        if hasattr(b, "use_cost_model"):
            b.use_cost_model(True)
    bot = ship.make_bot("composite", {**QUIET, "late_us": 1e9, **dials}, seed=seed * 64)
    rec = bots[0] = _Recorder(bot)
    play_table(bots, rules or Rules(), seed=seed, mode="model")
    return rec.h.hexdigest(), bot


def test_off_by_default_nothing_is_counted():
    _, bot = _digest({}, 0)
    core = bot.core.base.core
    assert sum(core.oan) == 0 and sum(core.oa_tn) == 0 and bot.core.ex.open_fold is None


def test_the_read_reaches_decisions_counts_and_replays_exactly():
    h, bot = _digest(ON, 0)
    core = bot.core.base.core
    assert sum(core.oa_tn) > 0 and bot.core.ex.open_fold is not None
    assert any(_digest(ON, t)[0] != _digest({}, t)[0] for t in range(3))
    assert h == _digest(ON, 0)[0]


def test_twist_tables_play_as_f():
    from hyperion.drills import variants as V

    bounty = V.get("bounty", seed=7).rules
    for t in range(2):
        h, bot = _digest(ON, t, rules=bounty)
        assert h == _digest({}, t, rules=bounty)[0]
        assert bot.core.ex.open_fold is None


def test_the_cap_only_lowers_the_fold_read():
    c = Rival3Core()
    c.k = replace(c.k, oa_read=True, oa_cap=True)
    c._v3_reset()
    S = c.st[3]
    S.hands, S.vpip, S.fr, S.fr_f = 40, 2, 30, 29  # folds 29 of 30 raises: the read (0.92) is above the prior
    assert c._fold_prob(3, False) > c.oa_fold(3, 0)
    ex = Exploit(ExploitParams(steal_min_fold=0.7, open_read=True, open_cap=True))
    ex.new_table(8, 7)
    obs = Observation(hole=parse("7c 2d"), board=(), street=0, seat=7, button=7, stacks=[2000] * 8,
                      bets=[10, 20, 0, 0, 0, 0, 0, 0], in_hand=[True] * 8, pot=0, to_call=20, min_raise=40,
                      max_raise=2000, legal=frozenset({F, C, R}), hand_no=0, blinds=(10, 20), history=[])
    ex.observe(obs)
    for s in (0, 1):
        ex.fold[s][0], ex.faced[s][0] = 0.80 * 6.0, 6.0  # fold rate (4.8 + 1.95) / 9 = 0.75
    ex.open_fold = lambda s, pos: 0.95  # higher than the seat's own rate: the cap keeps 0.75 (0.56 < 0.7)
    assert ex.override(obs, Action.fold()) is None
    ex.p.open_cap = False
    assert ex.override(obs, Action.fold()) is not None  # uncapped: 0.95 x 0.95 >= 0.7


def test_min_alive_keeps_short_handed_steals_as_built():
    d = {**ON, "r3.oa_cap": True, "exploit.open_cap": True}
    gated = {**d, "r3.oa_min_alive": 4, "exploit.open_min_alive": 4}
    r = Rules(n_players=3, payouts=(10, 7, 5))
    names = ["hero", "rival1", "rival2"]
    assert _digest(gated, 1, names, r)[0] == _digest({}, 1, names, r)[0]  # never four alive: F's own play
    assert any(_digest(gated, t)[0] != _digest({}, t)[0] for t in range(3))  # eight-handed it still reads
