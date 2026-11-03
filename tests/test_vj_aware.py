"""V-j: the tranche reads (hyperion/strategy/tranche.py), tranche_holdem's aware opponents (hyperion/sim/aware.py) and
the generic opponents' read of payoff by street (hyperion/sim/generic.py)."""
from __future__ import annotations

import dataclasses
import random

import pytest

from hyperion.core.types import Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim import aware as AW
from hyperion.sim import bestiary as B
from hyperion.sim import generic as G
from hyperion.sim.engine import Table
from hyperion.strategy import tranche as T
from tests.strategy_helpers import make_obs


def test_two_card_shares_match_the_organisers_table():
    # kit I's organiser notes (beats one random hand; theirs count a tie as no win, ours half: within 0.005)
    for hand, want in (("As Ah", 0.999), ("Jc Jd", 0.984), ("7c 7d", 0.965), ("2c 2d", 0.940), ("Ac Kd", 0.934),
                       ("Ac 2d", 0.826), ("Kc Qd", 0.784), ("8s 7s", 0.229)):
        assert T.beat_share(T.two_card_key(parse_cards(hand))) == pytest.approx(want, abs=0.005), hand
    assert len(T.TWO_CARD_KEYS) == 91 and T.TWO_CARD_KEYS[-1] == (12, 12) and T.TWO_CARD_KEYS[0] == (1, 0)


def test_the_twin_of_a_two_card_rank_is_the_holdem_class_at_its_percentile():
    from hyperion.strategy import tables

    tm = T.twin_map(tables.load().rank)
    assert tm[(0, 0)] == "ATs"  # 22 beats every non-pair: a strong hold'em class
    assert tm[(12, 12)] == "AA" and tm[(12, 11)] == "AKo"
    assert tm[(11, 10)] in ("A3s", "A4s", "A2s")  # K-Q is below every pair and every ace
    assert tm[(5, 0)] in ("54o", "64o", "53o")
    assert T.twin_cards("ATs") == (12 * 4 + 3, 8 * 4 + 3) and T.twin_cards("77") == (5 * 4 + 3, 5 * 4 + 2)
    a, b = T.twin_cards("AKo")
    assert (a >> 2, b >> 2) == (12, 11) and a & 3 != b & 3


def test_now_share_scores_the_board_as_it_stands():
    rng = random.Random(4)
    fd = T.now_share(parse_cards("Ah 5h"), parse_cards("Kh 9h 2c"), 1, rng, 400)
    nut = T.now_share(parse_cards("Ah Kd"), parse_cards("Kh 9h 2c"), 1, rng, 400)
    assert 0.4 < fd < 0.75 and nut > 0.9  # a flush draw is its ace high now, top pair top kicker nearly always ahead
    assert T.now_share(parse_cards("2c 2d"), (), 3, rng) == pytest.approx(T.beat_share((0, 0)) ** 3)


def test_the_aware_field_is_wired_for_the_entry():
    assert AW.AWARE_VARIANT["tranche_holdem_aware"] == "tranche_holdem"
    names = AW.AWARE_FIELDS["tranche_holdem_aware"]
    assert names[0] == "hero" and {"tranche_tag", "tranche_pushfold", "tranche_mc"} <= set(names)
    assert {"tranche_tag", "tranche_pushfold", "tranche_mc"} <= set(B.REGISTRY)
    assert AW.tranche_class(parse_cards("2c 2d")) in B.ChartTAG.MIDDLE  # 22 beats every non-pair: opened early
    assert AW.tranche_class(parse_cards("8s 7s")) not in B.ChartTAG.LATE  # suited connectors are weak two-card hands


def test_the_claim_counts_only_where_a_call_ends_the_betting():
    # river, heads-up, our pocket deuces took a 600-chip preflop tranche; a 300 bet with nothing made on the river
    obs = make_obs(hole="2c 2d", board="Ks Qh Jd 9c 5s", street=3, seat=0, stacks=[1500, 1200] + [0] * 6,
                   bets=[0, 300] + [0] * 6, in_hand=[True, True] + [False] * 6, pot=600)
    obs.extras = {"tranches": (600, 0, 0)}
    bot = AW.TrancheTAG(seed=1)
    bot.new_table(V.get("tranche_holdem").rules, 0, 8)
    assert AW.closes_betting(obs) and bot.claim_call(obs)  # 0.15 x 600 + ~0.94 x 600 >= 300
    obs.street, obs.board = 2, obs.board[:4]
    assert not AW.closes_betting(obs) and not bot.claim_call(obs)  # a turn call keeps it only by paying the river too


@pytest.mark.parametrize("field", ["tranche_holdem_aware", "generic_aware"])
def test_the_aware_fields_play_the_entry_clean(field):
    v = V.get("tranche_holdem")
    rules = dataclasses.replace(v.rules, max_hands=60)
    names = [nm if nm != "hero" else "tag" for nm in B.field_names(field)]
    for seed in (3, 4):
        bots = [B.make_bot(nm, seed=seed * 8 + s) for s, nm in enumerate(names)]
        t = Table(bots, rules, seed=seed, variant=v.new_hooks(), mode="model")
        while not t.done:
            t.play_hand()
            assert sum(t.stacks) == 8 * rules.starting_stack
        for s, st in enumerate(t.stats):
            assert st.exceptions == 0 and st.illegal == 0, (names[s], st.last_error)


def test_the_generic_read_settles_this_streets_chips_on_the_board_as_it_stands():
    v = V.get("tranche_holdem")
    sim = G.Sim(v.rules, v)
    assert not sim.holdem_cards()  # its own table, not hold'em's
    sim.sync({}, ())
    rng = random.Random(2)
    assert sim.rollout(parse_cards("2c 2d"), (), 0, [1], 600, rng, street=0) > 0.9  # two cards alone preflop
    assert sim.rollout(parse_cards("8s 7s"), (), 0, [1], 600, rng, street=0) < 0.35
    assert sim.rollout(parse_cards("Ah 5h"), parse_cards("Kh 9h 2c"), 0, [1], 600, rng, street=1) < 0.75  # no draw
    hold = G.Sim(Rules(), None)
    hold.sync({}, ())
    assert hold.rollout(parse_cards("8s 7s"), (), 0, [1], 600, rng, street=0) > 0.35  # hold'em's runout: unchanged
    t = G.load_table("tranche_holdem", v.rules, sim, build_if_missing=False)
    assert t.eq["22"] > t.eq["AQs"] > t.eq["KQs"] > t.eq["87s"]
