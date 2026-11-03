"""S18's horizon-aware ICM (docs/drills/climb/s18-log.md, section 0), behind `icm.horizon` (off: F as shipped, which
tests/test_compose.py replays): the blinds each seat still owes, the half-stack floor, Hero's curve and rival 3's all-in
prices on the effective stacks, the dial reaching both, and the late-table records (the play unchanged)."""
import importlib.util
import os

import pytest

from hyperion.compose import bot as CB
from hyperion.core.types import HandResult, Rules
from hyperion.hybrid import make_bot as make_hybrid
from hyperion.hybrid.core3 import icm_points
from hyperion.sim.runner import run_tournament
from hyperion.strategy.hero import IcmCurve, blinds_owed, horizon_stack, icm_me, next_live

NO_PANIC = {"core": "rival3", "panic_after": 10 ** 9, "soft_us": 1e6}


def test_each_seat_owes_its_blinds_before_its_next_button():
    r = Rules()  # 10/20, 15/30 ... 25 hands a level, cap 200
    # hand 0's button is seat 0, so hand 1's is seat 1: it owes nothing; seat 2 posts the small blind at hand 1, seat 3
    # the big blind at 1 and the small blind at 2; every later seat both blinds before its button
    assert blinds_owed([True] * 8, 0, 0, r) == [30.0, 0.0, 10.0, 30.0, 30.0, 30.0, 30.0, 30.0]
    # busted seats are skipped: live 0, 2, 3, 5; hand 11's button is seat 2
    live = [True, False, True, True, False, True, False, False]
    assert blinds_owed(live, 0, 10, r) == [30.0, 0.0, 0.0, 10.0, 0.0, 30.0, 0.0, 0.0]
    # a level change on the way: the blinds of the hands they are posted in
    assert blinds_owed([True] * 8, 0, 23, r)[2:5] == [10.0, 20.0 + 15.0, 30.0 + 15.0]
    # near the cap only the hands before it: 198 and 199 are left after hand 197
    assert blinds_owed(live, 0, 197, r) == [400.0, 0.0, 0.0, 200.0, 0.0, 400.0 + 200.0, 0.0, 0.0]
    assert blinds_owed(live, 0, 199, r) == [0.0] * 8  # the last hand: ICM is the cap's payoff
    assert blinds_owed(live, 0, 99, Rules(max_hands=100)) == [0.0] * 8
    # heads-up: the button posts the small blind on its own button hand; the other seat owes the big blind
    assert blinds_owed([True, False, True, False], 0, 30, r) == [30.0, 0.0, 0.0, 0.0]
    assert blinds_owed([True, False, False, False], 0, 30, r) == [0.0] * 4
    assert next_live(live, 0) == 2 and next_live(live, 5) == 0


def test_a_stack_keeps_at_least_half_of_itself():
    assert horizon_stack(1000, 300) == 700
    assert horizon_stack(1000, 600) == 500 and horizon_stack(1000, 5000) == 500
    assert horizon_stack(0, 300) == 0
    assert horizon_stack(1234.5, 0.0) == 1234.5


@pytest.mark.parametrize("pays", [(8, 7, 6, 5, 4, 3, 2, 1), (50, 25, 12, 6, 3, 2, 1, 1)])
def test_the_curve_prices_the_effective_stacks(pays):
    stacks = [3000, 600, 2000, 0, 1500, 4000, 2500, 2400]
    ratios = (0.0, 0.5, 1.0, 1.5, 2.0)
    plain, zero, hz = IcmCurve(), IcmCurve(), IcmCurve()
    plain.compute(stacks, 1, pays, ratios)
    zero.compute(stacks, 1, pays, ratios, owed=[0.0] * 8)
    assert (zero.xs, zero.vs) == (plain.xs, plain.vs)  # nothing owed: plain ICM, bit for bit
    owed = blinds_owed([c > 0 for c in stacks], 5, 120, Rules())  # hand 121: seat 6 on the button, seat 1 owes both
    hz.compute(stacks, 1, pays, ratios, buckets=10 ** 6, subdiv=1, owed=owed)
    assert hz.xs == plain.xs and hz.vs[0] == plain.vs[0]  # the axis is my stack after the hand; busting is busting
    total, others = sum(stacks), sum(stacks) - stacks[1]
    for x, v in zip(hz.xs[1:-1], hz.vs[1:-1]):
        scale = (total - x) / others
        st = [x if s == 1 else c * scale for s, c in enumerate(stacks)]
        eff = [horizon_stack(c, o) for c, o in zip(st, owed)]
        assert v == pytest.approx(icm_me(eff, 1, pays), rel=1e-3)
    # the short stack (600, owing a blind or two) is worth less than plain ICM says, the leader more
    assert hz.value(600) < plain.value(600)
    lead = IcmCurve()
    lead.compute(stacks, 5, pays, ratios, owed=owed)
    plain.compute(stacks, 5, pays, ratios)
    assert lead.value(4000) > plain.value(4000)


def test_the_dial_reaches_heros_curve_and_rival3s_prices():
    off = CB.ship({})
    assert not off.core.members[0].cfg.r3.icm_horizon and not off.core.members[1].cfg.icm_horizon
    on = CB.ship({"icm.horizon": True})
    base, hero = on.core.members[0], on.core.members[1]
    assert base.cfg.r3.icm_horizon and base.cfg.hero.icm_horizon and hero.cfg.icm_horizon
    with pytest.raises(KeyError):
        CB.ship({"icm.other": True})


def test_rival3s_all_in_prices_use_the_effective_stacks():
    stacks, bets, inh = [1000, 3000, 2000, 2000, 2000, 2000, 2000, 2000], [0] * 8, [True] * 8
    pays = (10, 7, 5, 4, 3, 2, 1, 0)
    hb = make_hybrid(seed=1, overrides={**NO_PANIC, "r3.icm_horizon": True})
    hb.new_table(Rules(payouts=pays), 0, 8)
    core = hb.core.core
    core.hand, core.button = 61, 6  # kit hand 61 = hand 60 (level 2: 25/50); hand 61's button is seat 7
    owed = blinds_owed([True] * 8, 6, 60, core.rules)
    assert owed[7] == 0.0 and owed[0] == 25.0 and owed[1] == 75.0
    evf, evs, evw, evl = core._allin(stacks, bets, inh, 0, 1, 300, 8)
    f = [1000, 3300, 2000, 2000, 2000, 2000, 2000, 2000]
    assert evf == pytest.approx(icm_points([horizon_stack(c, o) for c, o in zip(f, owed)], 0, pays))
    assert evf != pytest.approx(icm_points(f, 0, pays))
    assert evl == pytest.approx(pays[7])  # busting is busting
    core.hand = 200  # the last hand: nothing owed
    assert core._allin(stacks, bets, inh, 0, 1, 300, 8)[0] == pytest.approx(icm_points(f, 0, pays))


def test_heros_curve_follows_the_button_it_saw():
    from hyperion.strategy.hero import Config, HeroCore

    h = HeroCore(Config(icm_horizon=True, seed=1))
    h.new_table(Rules(), 0, 8)
    plain = (list(h.curve.xs), list(h.curve.vs))  # the table's first curve: no button seen yet, plain ICM
    h.hand_no, h.hand_start, h.btn_seen = 40, [2000] * 8, (40, 3)
    h.hand_end(HandResult(hand_no=40, deltas=[-1500, 1500, 0, 0, 0, 0, 0, 0], showdown={}, board=(), history=[]))
    stacks = [500, 3500] + [2000] * 6
    owed = blinds_owed([True] * 8, 4, 41, Rules())  # hand 41's button: the next live seat after 3
    ref = IcmCurve()
    ref.compute(stacks, 0, Rules().payouts, h.cfg.icm_ratios, owed=owed)
    assert (h.curve.xs, h.curve.vs) == (ref.xs, ref.vs) and h.curve.vs != plain[1]


def test_late_records_leave_the_play_alone():
    names = ["hero", "tag", "nit", "station", "maniac", "loose_aggro", "pushfold", "random"]
    a = run_tournament(names, 2, seed=5, rotate=False, mode="model")
    b = run_tournament(names, 2, seed=5, rotate=False, mode="model", late_at=60)
    assert {k: v.samples for k, v in a.bots.items()} == {k: v.samples for k, v in b.bots.items()}
    assert len(b.late) == 2 and not a.late
    for t, rot, alive, per in b.late:
        assert 0 <= alive <= 8 and sum(len(v) for v in per.values()) == 8
        assert all(alive_at or not surv for pts, alive_at, surv in per["hero"])  # out by hand 60: no survivor


def _ca():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("climb_accept_s18", os.path.join(root, "tools", "climb_accept.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_the_late_report_counts_tables_with_three_alive():
    CA = _ca()
    base = {(0, 0): (3, [[5.0, True, True]]), (0, 1): (2, [[7.0, True, True]]), (1, 0): (4, [[1.0, True, False]]),
            (1, 1): (5, [[2.0, False, False]])}
    cand = {(0, 0): (3, [[6.0, True, True]]), (0, 1): (3, [[7.0, True, True]]), (1, 0): (4, [[2.0, True, False]]),
            (1, 1): (2, [[2.0, False, False]])}
    rb = CA.late_rows(base)
    assert rb["tables"] == 4 and rb["late"] == 3
    assert rb["pts"][0] == pytest.approx((5 + 1 + 2) / 3) and rb["bust"] == pytest.approx(2 / 3)
    assert rb["alive"] == pytest.approx(2 / 3) and rb["bust_after"] == pytest.approx(1 / 2)
    rc = CA.late_rows(cand, base)
    assert rc["late"] == 3 and rc["paired"][0] == pytest.approx((1 + 1 + 0) / 3) and rc["paired"][2] == 3


def test_rival3_precomputes_the_next_hands_blinds_at_hand_end():
    hb = make_hybrid(seed=1, overrides={**NO_PANIC, "r3.icm_horizon": True})
    hb.new_table(Rules(), 0, 8)
    core = hb.core.core
    core.button = 2
    totals = [2000, 0, 1500, 2500, 2000, 2000, 2000, 2000]
    core.start_hand(41, totals)  # kit hand 41 = hand 40; its button the next live seat after 2
    live = [c > 0 for c in totals]
    assert core._owed_key == (41, 3) and core._owed_v == blinds_owed(live, 3, 40, core.rules)
    core.hand, core.button = 41, 3  # as predicted: the decision reads the cached list
    cached = core._owed_v
    assert core._owed(totals, [0] * 8, live) is cached
    core.button = 4  # the button was elsewhere: recomputed from the decision's own state
    assert core._owed(totals, [0] * 8, live) == blinds_owed(live, 4, 40, core.rules)
