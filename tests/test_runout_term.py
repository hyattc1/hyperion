"""tools/runout_term.py (R7, climb_accept --runout-term): the table with the term plays the engine's game exactly and draws
nothing from its generators, the term averages V over exactly the runouts the unseen cards allow, V places a hand's busts
as the engine does, twists that change the hand after its last decision get no term, and climb_accept refuses a term
cell whose raw samples differ from the plain cell's."""
import importlib.util
import json
import os

import pytest

from hyperion.core.cards import card_from_str as C
from hyperion.core.eval import evaluate
from hyperion.core.types import Rules
from hyperion.drills import variants as V
from hyperion.sim.bestiary import make_bot
from hyperion.sim.engine import HandState, Table

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, "tools", f"{name}.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


RT = _load("runout_term")
CHEAP = ["tag", "nit", "station", "maniac", "naive", "random", "allin", "tag"]


def _bots(names, seed, rot):
    return [make_bot(n, seed=seed * 64 + rot * 8 + s) for s, n in enumerate(names)]


@pytest.mark.parametrize("vname", [None, "hi_lo", "knockout_bounty", "short_deck", "omaha_four", "swap_holdem"])
def test_play_is_the_engines_exactly_and_the_term_sums_to_zero_over_the_seats(vname):
    v = V.get(vname) if vname else None
    rules = v.rules if v else None
    events = 0
    for seed in range(3):
        for rot in (0, 5):
            a = Table(_bots(CHEAP, seed, rot), rules, seed=seed, rotation=rot, mode="model",
                      variant=v.new_hooks() if v else None).play()
            t = RT.RunoutTable(_bots(CHEAP, seed, rot), rules, seed=seed, rotation=rot, mode="model",
                               variant=v.new_hooks() if v else None)
            b = t.play()
            assert (a.points, a.places, a.hands, a.stacks) == (b.points, b.places, b.hands, b.stacks)
            assert abs(sum(t.rt_corr)) < 1e-9  # V shares out a fixed total of points
            events += len(t.rt_log)
    if vname == "swap_holdem":  # its hooks redraw the board: no term
        assert not t.rt_on and events == 0
    else:
        assert t.rt_on and events > 0


def _turn_all_in(t):
    """Aces against kings, all in on the turn after the kings hit a set; the river is a blank, so the kings win."""
    holes = [(C("Ah"), C("Ad")), (C("Kh"), C("Kd"))]
    board = (C("2c"), C("7s"), C("9d"), C("Kc"), C("3h"))
    hs = HandState()
    hs.hand_no, hs.button, hs.holes, hs.board = 0, 0, holes, board
    hs.contrib, hs.in_hand, hs.dead, hs.n_in_hand, hs.stacks_start = [1000, 1000], [True, True], None, 2, [1000, 1000]
    t.stacks = [0, 2000]
    return hs, holes, board


def test_a_turn_all_in_averages_v_over_every_river_and_touches_no_table_stream():
    rules = Rules(n_players=2, payouts=(10, 7))
    t = RT.RunoutTable(_bots(["random", "random"], 0, 0), rules, seed=0)
    hs, holes, board = _turn_all_in(t)
    streams = (t.rng.getstate(), t.vrng.getstate(), t.srng.getstate())
    t._rt_event(hs, [0, 0], hs.stacks_start, seen=4)
    assert (t.rng.getstate(), t.vrng.getstate(), t.srng.getstate()) == streams
    rivers = [c for c in range(52) if c not in set(holes[0] + holes[1] + board[:4])]
    assert len(rivers) == 44 and t.rt_log[0][1:3] == (1, 44)
    a = [evaluate(holes[0] + board[:4] + (c,)) for c in rivers]
    k = [evaluate(holes[1] + board[:4] + (c,)) for c in rivers]
    wins, ties = sum(x > y for x, y in zip(a, k)), sum(x == y for x, y in zip(a, k))
    assert wins == 2 and ties == 0  # the last two aces
    mean_a = (10 * wins + 8.5 * ties + 7 * (44 - wins - ties)) / 44
    assert t.rt_corr[0] == pytest.approx(7 - mean_a) and t.rt_corr[1] == pytest.approx(10 - (17 - mean_a))


def test_a_preflop_all_in_samples_a_fixed_number_of_runouts_from_its_own_seed():
    rules = Rules(n_players=2, payouts=(10, 7))
    out = []
    for _ in range(2):
        t = RT.RunoutTable(_bots(["random", "random"], 0, 0), rules, seed=3)
        hs, _, _ = _turn_all_in(t)
        t._rt_event(hs, [0, 0], hs.stacks_start, seen=0)
        assert t.rt_log[0][1:3] == (5, RT.SAMPLES)
        out.append(t.rt_corr)
    assert out[0] == out[1]


def test_v_places_a_hands_busts_as_the_engine_does():
    rules = Rules(n_players=4, payouts=(10, 7, 5, 4))
    t = RT.RunoutTable(_bots(["random"] * 4, 0, 0), rules, seed=0)
    # seat 3 busted earlier; seats 1 and 2 bust in this hand, and 2 had more chips at its start: 2nd place for 2
    assert t._rt_value([700, 0, 0, 0], [300, 100, 300, 0]) == [10.0, 5.0, 7.0, 0.0]
    assert t._rt_value([600, 0, 0, 0], [200, 200, 200, 0]) == [10.0, 7.0, 5.0, 0.0]  # equal: the lower seat first
    v = t._rt_value([300, 300, 0, 0], [200, 200, 200, 0])
    assert v[2] == 5.0 and v[0] == v[1] == pytest.approx(8.5)


def test_the_term_applies_to_the_twists_that_leave_the_hand_alone_after_its_last_decision():
    off = {n for n in V.catalog_names() if not RT.neutral(V.get(n, seed=1).new_hooks())}
    assert off == {"toss_or_holdem", "three_card_blind_discard", "swap_holdem", "swap_one_turn", "two_boards",
                   "bonus_card", "auction", "deal5_keep2", "bounty", "river_of_blood"}


def test_climb_accept_refuses_a_term_cell_whose_raw_samples_differ_from_the_plain_cell(tmp_path):
    CA = _load("climb_accept")
    cell = ("night", "lin", None, None, 10000)
    plain, term = CA.cell_path(str(tmp_path), "k", cell), CA.cell_path(str(tmp_path), "k", cell, rt=True)
    assert term.endswith(f".10000.rt-{RT.version()}.json") and plain.endswith(".10000.json")
    os.makedirs(os.path.dirname(plain))
    with open(plain, "w") as fh:
        json.dump({"samples": [6.0, 5.5]}, fh)
    CA._check_rt_raw(term, {"samples": [6.0, 5.5]})
    with pytest.raises(RuntimeError):
        CA._check_rt_raw(term, {"samples": [6.0, 5.25]})
