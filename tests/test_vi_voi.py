"""V-i (docs/drills/climb/vi-log.md): twist decisions priced as value of information (Config.voi, voi_parts) and the
showdown tax read (Config.sd_tax). The option tables, each decision's rule, the composite handing the base's Hero its
observation, the tax gate, and both dials off playing as before."""
import random

import pytest

from hyperion.core.types import Rules, parse_cards as P
from hyperion.drills import variants as V
from hyperion.drills.ghost_example import ghost_rules
from hyperion.strategy import hero as H
from hyperion.strategy.hero import Config, HeroCore
from hyperion.strategy.postflop import TIER_EQUITY
from hyperion.strategy.tables import generic_doc

from .strategy_helpers import make_obs


def _core(rules: Rules, **kw) -> HeroCore:
    core = HeroCore(Config(**kw))
    core.new_table(rules, 0, 8)
    return core


def test_the_option_tables_cover_every_column_and_point_the_right_way():
    t = H.voi_table()
    assert set(t) == {"flop2", "flop3", "flop5", "turn", "buy"}
    for name in t:
        assert set(t[name]) == {1, 2, 3, 4}
    f2 = t["flop2"]
    # more opponents, less of the pot; a set is worth more than air; the bonus card adds more to air than to a set
    assert f2[1][(0, 0)] > f2[3][(0, 0)] and f2[1][(6, 0)] > f2[1][(0, 0)]
    e3, e2 = t["buy"][1][(0, 0)]
    s3, s2 = t["buy"][1][(6, 0)]
    assert e3 > e2 and e3 - e2 > s3 - s2
    # opponents who kept their best two of five are stronger: my middle pair is worth less there than in hold'em
    assert t["flop5"][1][(2, 0)] < t["flop3"][1][(2, 0)] < f2[1][(2, 0)]
    # the plain flop table is the auction table's two-card column (the same simulation, other seeds)
    a = H.auction_table()
    assert abs(f2[1][(0, 0)] - 0.3288) < 0.02 and 0.3 < a[1][(0, 0)] < 0.45


def test_voi_parts_reject_unknown_names():
    assert H.voi_parts("bid, keep") == {"bid", "keep"}
    with pytest.raises(KeyError):
        H.voi_parts("bid,auction")


def test_dials_off_make_the_decisions_as_before():
    off, on = _core(V.get("swap_one_turn").rules), _core(V.get("swap_one_turn").rules, voi=1.0, voi_parts="bid")
    assert off._voi == frozenset() and off._tax is None
    rng = random.Random(3)
    for _ in range(200):
        c = rng.sample(range(52), 6)
        p = {"decision": "swap", "hole": tuple(c[:2]), "board": tuple(c[2:])}
        assert off.variant_decide(p) == off._swap(p["hole"], p["board"]) == on.variant_decide(p)


def test_the_bid_at_multiplier_one_is_the_indifference_price_and_scales_with_it():
    rules = V.get("auction").rules
    p = {"decision": "bid", "hole": P("Ah 7d"), "board": P("Kd 9s 4c"), "pot": 120, "stack": 1900, "max_bid": 1900,
         "n_bidders": 2, "seat": 0, "big_blind": 20}
    plain = _core(rules).variant_decide(p)
    assert _core(rules, voi=1.0).variant_decide(p) == plain
    low, high = _core(rules, voi=0.67).variant_decide(p), _core(rules, voi=1.5).variant_decide(p)
    assert low < plain <= high <= int(0.75 * 120)  # the caps stay: a share of the pot and of the stack
    made = {**p, "hole": P("Kh Ks")}
    assert _core(rules, voi=1.5).variant_decide(made) > _core(rules).variant_decide(made)


def test_the_bonus_card_is_bought_when_its_worth_covers_the_price():
    rules = V.get("bonus_card").rules
    core = _core(rules, voi=1.0)
    stacks = [2000] * 8
    last = make_obs(hole="Ah 7d", seat=0, stacks=stacks, pot=0, hand_no=5)  # nothing in the middle yet
    base = {"decision": "buy_card", "price": 20, "hole": P("Ah 7d"), "board": P("Kd 9s 4c"), "seat": 0,
            "hand_no": 5, "last_obs": last}
    # a raised pot (two players put in 200): air buys; a limped pot of 40: a set keeps its blind
    big = {**base, "stacks": [1800, 1800] + [2000] * 6}
    small = {**base, "stacks": [1980, 1980] + [2000] * 6, "hole": P("9h 9d")}
    assert core.variant_decide(big) is True
    assert core.variant_decide(small) is False
    assert core._pot_now(big) == 400 and core._pot_now(small) == 40
    # no observation of this hand (another hand's, or none): the plain rule (a tenth of the stack)
    assert core.variant_decide({**small, "hand_no": 6}) is True
    assert _core(rules).variant_decide(small) is True


def _swap_full(core, hole, board, tab):
    """The swap's values over every replacement card, read one by one (what _swap_voi's grouping must equal)."""
    read = core.postflop._read
    tier, outs, _ = read(hole, board, 0, ())
    best, bv = -1, tab.get((tier, H.outs_bucket(outs)), TIER_EQUITY[tier])
    unseen = [c for c in range(52) if c not in set(hole) | set(board)]
    for i in (0, 1):
        acc = 0.0
        for r in unseen:
            t2, o2, _ = read((hole[1 - i], r), board, 0, (hole[i],))
            acc += tab.get((t2, H.outs_bucket(o2)), TIER_EQUITY[t2])
        if acc / len(unseen) > bv + 1e-9:
            best, bv = i, acc / len(unseen)
    return best


def test_the_swap_prices_every_replacement_card():
    core = _core(V.get("swap_one_turn").rules, voi=1.0)
    rng = random.Random(11)
    for _ in range(300):
        c = rng.sample(range(52), 6)
        hole, board = tuple(c[:2]), tuple(c[2:])
        assert core.variant_decide({"decision": "swap", "hole": hole, "board": board}) == \
            _swap_full(core, hole, board, H.voi_table()["turn"][1])
    # a made straight keeps; a dead kicker with nothing goes
    assert core.variant_decide({"decision": "swap", "hole": P("Th 9c"), "board": P("8d 7s 6h 2c")}) == -1
    assert core.variant_decide({"decision": "swap", "hole": P("Ah 2c"), "board": P("Ks Qd 9h 5s")}) == 1


def test_keep_and_discard_take_the_option_worth_most():
    core = _core(V.get("deal5_keep2").rules, voi=1.0)
    p = {"decision": "keep", "hole": P("7c 2d As 9s Ah"), "board": P("Ad Kh 6c"), "revealed": {}}
    assert sorted(core.variant_decide(p)) == [2, 4]  # trip aces
    p = {"decision": "keep", "hole": P("Qh Jh 4c 4s 2c"), "board": P("Th 9h 4d"), "revealed": {}}
    assert sorted(core.variant_decide(p)) == [2, 3]  # the set
    toss = _core(V.get("toss_or_holdem").rules, voi=1.0)
    assert toss.variant_decide({"decision": "discard", "hole": P("Kh Kd 2c"), "board": P("Ks 7d 3c"),
                                "discards": {}}) == 2
    blind = _core(V.get("three_card_blind_discard").rules, voi=1.0)
    assert blind.variant_decide({"decision": "discard", "hole": P("Ah Ad 7c"), "board": (), "discards": {}}) == 2


def test_the_composite_hands_the_base_hero_its_last_observation():
    from hyperion.ship import make_bot

    bot = make_bot(None, {"hero.voi": 1.0})
    bot.new_table(V.get("bonus_card").rules, 0, 8)
    seen = {}
    hero = bot.core.base.hero  # the base (the hybrid core) -> its fallback HeroCore
    orig = hero.variant_decide

    def spy(prompt):
        seen.update(prompt)
        return orig(prompt)

    hero.variant_decide = spy
    obs = make_obs(hole="Ah 7d", seat=0, hand_no=4)
    bot.core._obs = obs
    bot.variant_decide({"decision": "buy_card", "price": 20, "hole": P("Ah 7d"), "board": P("Kd 9s 4c"),
                        "seat": 0, "hand_no": 4, "stacks": [2000] * 8})
    assert seen.get("last_obs") is obs


def test_mean_share_and_the_tax_tiers():
    import json
    import os

    from hyperion.strategy.tables import GENERIC_DIR

    with open(os.path.join(GENERIC_DIR, "holdem-3eb02749.json")) as fh:  # hold'em's own (no variant name)
        assert abs(H.mean_share(json.load(fh)) - H.SD_SHARE_HOLDEM) < 0.0001
    ghost = H.mean_share(generic_doc(ghost_rules()))
    assert 0.33 < ghost < 0.35
    assert H.tax_tiers(ghost / H.SD_SHARE_HOLDEM, 4) == 2
    assert H.tax_tiers(1.0, 4) == 0 and H.tax_tiers(0.95, 4) == 0
    assert H.tax_tiers(1.6, 4) < 0  # a showdown that pays more than the pot: thinner value


def test_the_tax_gate_opens_on_the_ghost_only():
    assert _core(ghost_rules(), sd_tax=True)._tax is not None
    f, n = _core(ghost_rules(), sd_tax=True)._tax
    assert 0.66 < f < 0.70 and n == 2
    assert _core(ghost_rules(), sd_tax=False)._tax is None
    assert _core(ghost_rules(named=False), sd_tax=True)._tax is None  # not told the twist: no table to read
    for name in V.catalog_names():  # every catalog twist pays hold'em's showdown, or Hero prices it (bounty)
        assert _core(V.get(name).rules, sd_tax=True)._tax is None, name


def test_the_tax_reads_calls_lower_and_thin_value_higher():
    from hyperion.strategy.postflop import Postflop, PostflopParams
    from hyperion.strategy.spot import Spot

    pf = Postflop(PostflopParams(), 1)
    # top pair good kicker on the river, a pot-sized bet to call: calls in hold'em, folds at f 0.68
    obs = make_obs(hole="Ah Kd", board="Ks 9c 4d 2h 7s", street=3, seat=0, stacks=[1500] * 8, bets=[0, 200] + [0] * 6,
                   in_hand=[True, True] + [False] * 6, pot=200)
    spot = Spot(obs, obs.hole, None)
    assert pf.act(spot, obs.hole, None, False).kind.name == "CALL"
    assert pf.act(spot, obs.hole, None, False, call_scale=0.68).kind.name == "FOLD"
    # checked to with top pair good kicker: a value bet in hold'em, a check two tiers up
    obs2 = make_obs(hole="Ah Kd", board="Ks 9c 4d 2h 7s", street=3, seat=0, stacks=[1500] * 8,
                    in_hand=[True, True] + [False] * 6, pot=200)
    spot2 = Spot(obs2, obs2.hole, None)
    assert pf.act(spot2, obs2.hole, None, False).kind.name == "RAISE"
    assert pf.act(spot2, obs2.hole, None, False, thin_shift=2).kind.name == "CHECK"


def test_f_plays_the_decision_twists_and_the_ghost_with_both_dials_on():
    from hyperion.ship import register_sim
    from hyperion.sim.bestiary import field_names
    from hyperion.sim.runner import run_tournament
    from hyperion.drills.ghost_example import variant as ghost

    register_sim({"hero.voi": 1.5, "hero.sd_tax": True})
    try:
        for v in [V.get(n) for n in ("auction", "bonus_card", "swap_one_turn", "toss_or_holdem", "deal5_keep2")] + \
                [ghost()]:
            rep = run_tournament(field_names("realistic@ship"), 1, seed=4, variant=v, mode="model")
            st = rep.bots["ship"].stats
            assert st.exceptions == 0 and st.illegal == 0 and st.safe_err == 0 and rep.hands > 0, v.name
    finally:
        register_sim()  # the registry's `ship` as shipped, for the tests after this one
