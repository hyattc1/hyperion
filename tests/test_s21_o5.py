"""O5 and O6 (docs/drills/climb/s21-log.md): the big blind's fold read from its answers as the big blind to a first-in raise
by any seat this table, with its fold-to-any-raise read as the prior (r3.bb_read, r3.bb_k), for the big blind only
(r3.oa_bb_only, exploit.open_bb_only), in rival 3's core and in the layer."""
from dataclasses import replace

from hyperion import ship
from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.core.types import parse_cards as parse
from hyperion.hybrid.core3 import Rival3Core, bb_scan
from hyperion.strategy.exploit import Exploit, ExploitParams

from .test_s16b_open import _digest

R, C, F = ActionKind.RAISE, ActionKind.CALL, ActionKind.FOLD
O5 = {"r3.oa_read": True, "r3.bb_read": True, "r3.oa_bb_only": True, "r3.oa_min_alive": 4,
      "exploit.open_read": True, "exploit.open_bb_only": True, "exploit.open_min_alive": 4}
ST = [2000] * 8


def test_bb_scan_reads_the_big_blind_answer_to_anyones_open():
    assert bb_scan([(3, ('fold', 0)), (4, ('raise', 50)), (5, ('call', 0)), (6, ('fold', 0)), (7, ('fold', 0))],
                   7, ST) == 1
    assert bb_scan([(4, ('raise', 50)), (5, ('fold', 0)), (6, ('fold', 0)), (7, ('call', 0))], 7, ST) == 0
    assert bb_scan([(6, ('raise', 60)), (7, ('raise', 180))], 7, ST) == 0  # small blind's open, re-raised: answered
    assert bb_scan([(4, ('raise', 50)), (5, ('raise', 150)), (7, ('fold', 0))], 7, ST) is None  # a 3-bet came first
    assert bb_scan([(4, ('call', 0)), (5, ('raise', 80)), (7, ('fold', 0))], 7, ST) is None  # a limp first
    assert bb_scan([(4, ('raise', 1990)), (7, ('fold', 0))], 7, ST) is None  # all-in: not an open
    assert bb_scan([(0, ('fold', 0)), (6, ('fold', 0))], 7, ST) is None  # a walk


def test_the_read_starts_at_the_fold_to_any_raise_read_and_moves_with_answers():
    c = Rival3Core()
    c.k = replace(c.k, oa_read=True, bb_read=True)
    c._v3_reset()
    g = c._fold_prob(3, False)
    assert abs(c.oa_fold(3, 2) - g) < 1e-12  # no answers: F's own read
    c.bbn[3], c.bbf[3] = 10.0, 9.0
    assert abs(c.oa_fold(3, 2) - (9.0 + g * c.k.bb_k) / (10.0 + c.k.bb_k)) < 1e-12
    assert c.oa_fold(3, 0) != c.oa_fold(3, 2)  # other positions keep O3's estimator (unused with oa_bb_only)
    c.k = replace(c.k, bb_read=False)
    assert abs(c.oa_fold(3, 2) - c._oa_table(2)) < 1e-12  # off: O3's estimator (no answers of its own yet)


def test_the_layer_reads_the_big_blind_only():
    ex = Exploit(ExploitParams(steal_min_fold=0.7, open_read=True, open_bb_only=True))
    ex.new_table(8, 5)
    obs = Observation(hole=parse("7c 2d"), board=(), street=0, seat=5, button=5, stacks=[2000] * 8,
                      bets=[0, 0, 0, 0, 0, 0, 10, 20], in_hand=[False] * 5 + [True] * 3, pot=0, to_call=20,
                      min_raise=40, max_raise=2000, legal=frozenset({F, C, R}), hand_no=0, blinds=(10, 20),
                      history=[(s, Action.fold()) for s in range(5)])
    ex.observe(obs)
    for s in (6, 7):
        ex.fold[s][0], ex.faced[s][0] = 0.95 * 6.0, 6.0
    seen = []
    ex.open_fold = lambda s, pos: seen.append((s, pos)) or 0.95
    ex.override(obs, Action.fold())
    assert seen == [(7, 2)]


def test_off_by_default_nothing_is_counted_and_on_it_counts_and_replays():
    _, bot = _digest({}, 0)
    assert sum(bot.core.base.core.bbn) == 0
    h, bot = _digest(O5, 0)
    core = bot.core.base.core
    assert sum(core.bbn) > 0 and sum(core.bbf) <= sum(core.bbn)
    assert h == _digest(O5, 0)[0]
    assert any(_digest(O5, t)[0] != _digest({}, t)[0] for t in range(3))


def test_twist_and_straddle_tables_play_as_f():
    from hyperion.drills import variants as V

    for rules in (V.get("bounty", seed=7).rules, Rules(straddle=2)):
        assert _digest(O5, 0, rules=rules)[0] == _digest({}, 0, rules=rules)[0]


def test_ship_dials_leave_o5_off():
    bot = ship.make_bot("composite", {})
    k = bot.core.base.core.k
    assert not k.bb_read and not k.oa_bb_only and not bot.core.ex.p.open_bb_only


# O6 (docs/drills/climb/s21-log.md, "O6"): O5 + the seats that are not a blind on O3's own read, uncapped
O6 = {**O5, "r3.oa_other": True, "exploit.open_other": True}


def test_o6_the_layer_reads_the_big_blind_and_the_seats_that_are_not_a_blind():
    ex = Exploit(ExploitParams(steal_min_fold=0.7, open_read=True, open_bb_only=True, open_other=True))
    ex.new_table(8, 3)
    obs = Observation(hole=parse("7c 2d"), board=(), street=0, seat=3, button=5, stacks=[2000] * 8,
                      bets=[0, 0, 0, 0, 0, 0, 10, 20], in_hand=[False] * 3 + [True] * 5, pot=0, to_call=20,
                      min_raise=40, max_raise=2000, legal=frozenset({F, C, R}), hand_no=0, blinds=(10, 20),
                      history=[(s, Action.fold()) for s in range(3)])
    ex.observe(obs)
    for s in range(8):
        ex.fold[s][0], ex.faced[s][0] = 0.95 * 6.0, 6.0
    seen = []
    ex.open_fold = lambda s, pos: seen.append((s, pos)) or 0.95
    ex.override(obs, Action.fold())
    assert seen == [(4, 0), (5, 0), (7, 2)]  # not the small blind (seat 6)


def test_o6_off_is_o5_and_on_it_moves_more_opens():
    assert _digest({**O5, "r3.oa_other": False, "exploit.open_other": False}, 0)[0] == _digest(O5, 0)[0]
    h = _digest(O6, 0)[0]
    assert h == _digest(O6, 0)[0]
    assert any(_digest(O6, t)[0] != _digest(O5, t)[0] for t in range(3))


def test_o6_twist_and_straddle_tables_play_as_f():
    from hyperion.drills import variants as V

    for rules in (V.get("bounty", seed=7).rules, Rules(straddle=2)):
        assert _digest(O6, 0, rules=rules)[0] == _digest({}, 0, rules=rules)[0]


def test_ship_dials_leave_o6_off():
    bot = ship.make_bot("composite", {})
    assert not bot.core.base.core.k.oa_other and not bot.core.ex.p.open_other
