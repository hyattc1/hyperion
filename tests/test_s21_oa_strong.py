"""S21's gate on the open-answer read (docs/drills/climb/s21-log.md): with `oa_strong`, O3 (S16b's read in rival 3's
core and in the layer) acts only while the composite's strong-table read is open (CompositeCore.strong_table());
the core keeps counting the answers while it waits."""
from hyperion import ship
from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.core.types import parse_cards as parse

from .test_s16b_open import _digest

R, C, F = ActionKind.RAISE, ActionKind.CALL, ActionKind.FOLD
O3 = {"r3.oa_read": True, "exploit.open_read": True, "r3.oa_cap": True, "exploit.open_cap": True,
      "r3.oa_min_alive": 4, "exploit.open_min_alive": 4}
GATED = {**O3, "oa_strong": True}
NEVER, ALWAYS = {"strong_rr": 1.01}, {"strong_rr": 0.0}  # the strong read never / always open (route and gate alike)


def _obs(hand_no):
    return Observation(hole=parse("7c 2d"), board=(), street=0, seat=5, button=5, stacks=[2000] * 8,
                       bets=[0, 0, 0, 0, 0, 0, 10, 20], in_hand=[True] * 8, pot=0, to_call=20, min_raise=40,
                       max_raise=2000, legal=frozenset({F, C, R}), hand_no=hand_no, blinds=(10, 20),
                       history=[(s, Action.fold()) for s in range(5)])


def test_off_by_default_and_off_is_o3():
    bot = ship.make_bot("composite", {**O3})
    assert bot.core.cfg.oa_strong is False and not bot.core._oa_gate
    assert _digest({**O3, "oa_strong": False}, 0)[0] == _digest(O3, 0)[0]


def test_the_gate_follows_the_strong_read_before_each_preflop_decision():
    bot = ship.make_bot("composite", GATED)
    cc = bot.core
    core = cc.base.core
    assert cc._oa_gate and cc._oa_gcore is core and cc._oa_core is core
    bot.new_table(Rules(), 5, 8)
    assert cc._oa_fn is not None
    cc._rr_n, cc._rr_k = 30, 0  # few of our opens re-raised: the read is closed
    assert not cc.strong_table()
    cc.act(_obs(1))
    assert core.oa_on is False and cc.ex.open_fold is None
    cc._rr_n, cc._rr_k = 30, 15  # half of them re-raised: open
    assert cc.strong_table()
    cc.act(_obs(2))
    assert core.oa_on is True and cc.ex.open_fold is not None and cc.ex.open_fold == core.oa_fold


def test_read_never_open_plays_as_f_and_still_counts():
    for t in range(2):
        h, bot = _digest({**GATED, **NEVER}, t)
        assert h == _digest(NEVER, t)[0]
        assert sum(bot.core.base.core.oa_tn) > 0  # the answers are counted while the read waits


def test_read_always_open_plays_as_o3():
    for t in range(2):
        assert _digest({**GATED, **ALWAYS}, t)[0] == _digest({**O3, **ALWAYS}, t)[0]


def test_as_shipped_the_gate_opens_at_some_strong_tables_only():
    # table 0: the read stays under 0.2 (3 of 18 opens re-raised): F's play where O3 would read; table 8: it opens
    # with four or more alive (4 of 12) and the gated read plays there as O3 does
    g0, g8 = _digest(GATED, 0)[0], _digest(GATED, 8)[0]
    assert g0 == _digest({}, 0)[0] and g0 != _digest(O3, 0)[0]
    assert g8 != _digest({}, 8)[0]
