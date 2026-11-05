"""S26's heads-up re-jam read (docs/drills/climb/s26-log.md; hyperion/compose/bot.py ComposeConfig.hu_rejam_*): behind dials that
default to the shipped play. It sees the opener's fold rate before it widens, keeps to heads-up plain hold'em, and off it does not
exist."""
from hyperion.compose.bot import ComposeConfig, CompositeCore
from hyperion.core.types import Action, ActionKind, Observation, Rules

from .test_s2_dials import _digest

HU = ["hero", "f_copy"]
THREE = ["hero", "elite1", "elite2"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
S26 = {"hu_rejam_t": 0.7}


class _Prof:
    def __init__(self, n, f):
        self.oft_opp, self.oft_fold = [0, n], [0, f]
        self.ofj_opp, self.ofj_fold = [0, 0], [0, 0]

    def open_fold_to_reraise(self, s, prior, n0):
        return (self.oft_fold[s] + prior * n0) / (self.oft_opp[s] + n0)


def _core(n, f, **kw):
    c = CompositeCore.__new__(CompositeCore)
    c.cfg = ComposeConfig(hu_rejam_t=0.7, **kw)
    c._rj_prof = _Prof(n, f)
    c._rj_n, c._rj_f = [0, 0], [0, 0]
    from hyperion.sim.rivals.rival3 import PCT, _cls, _eqvs

    from hyperion.hybrid.core3 import icm_points

    c._rj_r3 = (PCT, _cls, _eqvs, icm_points)
    c._rj_pay = (10, 7, 5)
    return c


def _obs(stack_me=1500, stack_opp=1500, amount=200, hole=(0, 5), hist=None):
    """Heads-up, our big blind (seat 0) facing the button's (seat 1) first-in raise to `amount`; blinds 50/100."""
    return Observation.__new__(Observation), dict(
        seat=0, stacks=[stack_me - 100, stack_opp - amount], bets=[100, amount], in_hand=[True, True], blinds=(50, 100),
        pot=0, street=0, hole=hole, to_call=amount - 100, max_raise=stack_me, min_raise=2 * amount - 100,
        legal=(ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE),
        history=hist if hist is not None else [(1, Action(ActionKind.RAISE, amount))])


def _o(**kw):
    o, d = _obs(**kw)
    for k, v in d.items():
        object.__setattr__(o, k, v)
    return o


FOLD = Action(ActionKind.FOLD)


def test_it_needs_answers_and_a_high_fold_rate_before_it_widens():
    assert not _core(2, 2)._hu_rejam(_o(), FOLD)  # too few answers seen
    assert _core(9, 9)._hu_rejam(_o(), FOLD)  # 72o-grade hand against an opener folding everything
    assert not _core(9, 2)._hu_rejam(_o(), FOLD)  # this opener calls


def test_our_own_jams_answers_count_for_more_than_the_table():
    c = _core(9, 9)
    c._rj_n[1], c._rj_f[1] = 6, 1
    assert not c._hu_rejam(_o(), FOLD)  # it folded 9 of 9 at the table, then called five of our six


def test_all_in_answers_count_before_the_any_reraise_read():
    assert not _core(9, 3)._hu_rejam(_o(), FOLD)  # calls most re-raises
    c = _core(9, 3, hu_rejam_jk=2.0)
    c._rj_prof.ofj_opp[1], c._rj_prof.ofj_fold[1] = 4, 4
    assert c._hu_rejam(_o(), FOLD)  # ... and folded all four all-in ones
    c._rj_prof.ofj_fold[1] = 1
    assert not c._hu_rejam(_o(), FOLD)


def test_the_lines_it_leaves_alone():
    c = _core(9, 9)
    assert not c._hu_rejam(_o(stack_me=800), FOLD)  # under the depth floor
    assert not c._hu_rejam(_o(stack_me=2500, stack_opp=2500), FOLD)  # over the depth cap
    assert not c._hu_rejam(_o(amount=700), FOLD)  # a raise committing it
    assert not c._hu_rejam(_o(), Action(ActionKind.RAISE, 600))  # the members already raise
    assert not c._hu_rejam(_o(hist=[(1, Action(ActionKind.RAISE, 200)), (0, Action(ActionKind.RAISE, 500))]), FOLD)
    assert not _core(9, 9, hu_rejam_cap=0.1)._hu_rejam(_o(), FOLD)  # outside the top share of hands


def _o3(hole=(0, 5), hist=None, stacks=(1500, 1500, 1500), amount=200, in_hand=(True, True, False)):
    """Three alive: our big blind (seat 0), the button (seat 1) raised to `amount`, the small blind (seat 2) folded its 50."""
    o, d = _obs(hole=hole)
    d.update(stacks=[stacks[0] - 100, stacks[1] - amount, stacks[2] - 50], bets=[100, amount, 50], in_hand=list(in_hand), to_call=amount - 100,
             history=hist if hist is not None else [(1, Action(ActionKind.RAISE, amount)), (2, Action(ActionKind.FOLD))])
    for k, v in d.items():
        object.__setattr__(o, k, v)
    return o


def _core3(n, f, **kw):
    c = _core(n, f, **kw)
    c._rj_prof.oft_opp, c._rj_prof.oft_fold = [0, n, 0], [0, f, 0]
    c._rj_prof.ofj_opp, c._rj_prof.ofj_fold = [0, 0, 0], [0, 0, 0]
    c._rj_n, c._rj_f = [0, 0, 0], [0, 0, 0]
    return c


def test_three_alive_needs_the_dial_the_fold_behind_and_prices_in_icm():
    assert not _core3(9, 9)._hu_rejam(_o3(), FOLD)  # hu_rejam_alive 2: heads-up only
    c = _core3(9, 9, hu_rejam_alive=3)
    assert c._hu_rejam(_o3(), FOLD)
    assert c.hu_rejam_would[0] > 0.7 and abs(c.hu_rejam_would[3]) < 3.0  # the gain is in points, not big blinds
    # the small blind still to act: not ours
    assert not c._hu_rejam(_o3(hist=[(1, Action(ActionKind.RAISE, 200))], in_hand=(True, True, True)), FOLD)
    # a call before us: not ours
    assert not c._hu_rejam(_o3(hist=[(1, Action(ActionKind.RAISE, 200)), (2, Action(ActionKind.CALL))], in_hand=(True, True, True)), FOLD)
    assert not _core3(9, 2, hu_rejam_alive=3)._hu_rejam(_o3(), FOLD)  # an opener that calls
    assert not _core3(9, 9, hu_rejam_alive=3, hu_rejam_margin3=5.0)._hu_rejam(_o3(), FOLD)  # the margin is in points


def test_absent_it_does_not_exist():
    assert ComposeConfig().hu_rejam_t == 0.0
    from hyperion.compose.bot import SHIP_DIALS

    assert not any(k.startswith("hu_rejam") for k in SHIP_DIALS)
    _, bot = _digest({}, 0, HU, R2)
    assert bot.core._rj_prof is None and not any("hu_rejam" in k for k in bot.core.counts)


def test_it_reaches_heads_up_decisions_and_replays():
    # f_copy does not replay in this harness with or without the read; rival 3 does
    assert any(_digest(S26, t, HU, R2)[1].core.counts.get("hu_rejam", 0) for t in range(12))
    for t in range(6):
        assert _digest(S26, t, ["hero", "rival3"], R2)[0] == _digest(S26, t, ["hero", "rival3"], R2)[0]


def test_three_handed_tables_play_as_f_until_two_are_left():
    # no decision with three alive consults the read: the read's counts move only heads-up
    _, bot = _digest({"hu_rejam_t": 0.01, "hu_rejam_min": 0, "hu_rejam_max_bb": 0.0}, 3, THREE, R3)
    assert not any("hu_rejam" in k for k in bot.core.counts)
    assert _digest({"hu_rejam_t": 0.01, "hu_rejam_max_bb": 0.0}, 3, THREE, R3)[0] == _digest({}, 3, THREE, R3)[0]


def test_twist_tables_stay_off():
    r = Rules(n_players=2, payouts=(10, 7), hole_cards=3)
    c = CompositeCore(ComposeConfig(hu_rejam_t=0.7))
    c.new_table(r, 0, 2)
    assert c._rj_prof is None


def test_hu2_free_opens_h1_with_the_strong_read_shut_and_off_it_stays_shut():
    from hyperion.strategy.short import ShortParams

    assert ShortParams().hu2_free is False
    base = {"short.hu2": True, "short.hu2_like_opp": 0, "short.hu2_min": 10, "short.hu2_max": 40, "strong_rr": 0.99}
    off = sum(_digest(base, t, ["hero", "rival3"], R2)[1].core.counts.get("short", 0) for t in range(3))
    on = sum(_digest({**base, "short.hu2_free": True}, t, ["hero", "rival3"], R2)[1].core.counts.get("short", 0) for t in range(3))
    assert on > off
