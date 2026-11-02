"""V-e's dials for twists against opponents that play them (Hero Config / PostflopParams, `hero.<key>` on F): each is
off by default, and each does what it says when on. twin_preflop (two-card twists: the hold'em twin from the variant's
own prepared table), postflop.split_call_margin (two boards), variant_preflop_ex (must-use, fixed limit, lowball)."""
import json

from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_cards as P
from hyperion.drills import variants as V
from hyperion.strategy.hero import Config, HeroCore, config_from_dict, mirror_map, wild_map
from hyperion.strategy.postflop import Postflop, PostflopParams
from hyperion.strategy.spot import Spot
from hyperion.strategy.tables import generic_doc, load, twin_classes, twin_shift

from .strategy_helpers import street_obs

R, C = Action.raise_to, Action.call()
HU = [False, True, False, False, False, False, False, True]
PRE = [(7, R(50)), (1, C)]


def test_every_new_dial_is_off_by_default():
    c = Config()
    assert (c.twin_preflop, c.twin_force, c.twin_multi, c.variant_preflop_ex, c.call_shift_ex, c.multi_call_shift,
            c.mu_call_shift, c.multi_value_shift, c.mu_value_shift, c.postflop.split_call_margin,
            c.postflop.split_tier_eq) == (0.0, False, 0.0, {}, {}, 0, 0, 0, 0, -1.0, False)


def test_twins_come_from_the_variants_own_table():
    base = load(need_hu=True)
    low = twin_classes(generic_doc(V.get("lowball").rules), base)
    wild = twin_classes(generic_doc(V.get("wild_deuces").rules), base)
    assert low["32o"] in ("AA", "KK", "QQ") and base.rank[low["AA"]] < 0.05  # 2-7: the wheel-ish hands lead, AA is trash
    assert wild["22"] == "AA" and base.rank[wild["AA"]] < base.rank["AA"] - 0.1  # two wilds lead; AA is not a premium
    assert twin_shift(low, base) > 0.3 and twin_shift(wild, base) > 0.1
    holdem = twin_classes(generic_doc(V.get("fixed_raise").rules), base)  # hold'em cards: the classes themselves
    assert holdem is not None and all(k == v for k, v in holdem.items())
    assert generic_doc(Rules()) is None  # plain hold'em names no variant


def _cls_map(dials, name):
    h = HeroCore(config_from_dict(dials))
    h.new_table(V.get(name).rules, 0, 8)
    return h._cls_map


def test_twin_preflop_replaces_the_hand_written_maps_only_when_on():
    base = load(need_hu=True)
    assert _cls_map({}, "lowball") == mirror_map(base.rank)
    assert _cls_map({}, "wild_deuces") == wild_map(0)
    assert _cls_map({}, "hi_lo") is None
    on = {"twin_preflop": 0.05}
    assert _cls_map(on, "wild_deuces")["AA"] != "AA" and _cls_map(on, "lowball") != mirror_map(base.rank)
    assert _cls_map(on, "hi_lo") is not None
    # under the threshold (a twist with hold'em's showdown: sampling noise), with a variant table set, or a rank
    # remap: unchanged
    for name in ("two_boards", "bounty", "short_deck", "permuted_ranks", "omaha_four"):
        assert _cls_map(on, name) == _cls_map({}, name), name
    h = HeroCore(config_from_dict(on))
    h.new_table(Rules(), 0, 8)
    assert h._cls_map is None
    # twin_force: the short deck's twins in place of its variant set (the hold'em tables read through the twins)
    h = HeroCore(config_from_dict({**on, "twin_force": True}))
    h.new_table(V.get("short_deck").rules, 0, 8)
    assert h.active is h.tables and h._cls_map["AA"] != "AA"


def _two_board_call(margin):
    pf = Postflop(PostflopParams(call_margin=0.2, split_call_margin=margin, vs_cbet_margin=-1.0))
    obs = street_obs("Ah 8d", "Ac 7s 2h", seat=1, button=7, pot=100, bets=[0] * 7 + [50],
                     in_hand=HU, history=PRE)
    spot = Spot(obs, P("Ah 8d"), None)
    # top pair on board 1, nothing on board 2: about half the pot back, at a price of a third
    return pf.act(spot, P("Ah 8d"), None, False, board=P("Ac 7s 2h"), board2=P("Kd 9c 4s")).kind


def test_split_call_margin_moves_two_board_calls_only():
    assert _two_board_call(-1.0) is ActionKind.FOLD
    assert _two_board_call(0.0) is ActionKind.CALL
    pf = Postflop(PostflopParams(call_margin=0.2, split_call_margin=0.0, vs_cbet_margin=-1.0))
    obs = street_obs("Kh 8d", "Ac 7s 2h", seat=1, button=7, pot=100, bets=[0] * 7 + [50],
                     in_hand=HU, history=PRE)
    spot = Spot(obs, P("Kh 8d"), None)
    assert pf.act(spot, P("Kh 8d"), None, False, board=P("Ac 7s 2h")).kind is ActionKind.FOLD  # one board: as before


def test_variant_preflop_ex_reaches_the_tables_variant_preflop_leaves_out():
    vp = {"call_raise_frac": 0.15, "three_bet_frac": 0.05}
    ex = {"must_use": {"call_raise_frac": 0.2}, "lowball": {"call_raise_frac": 0.25}, "fixedlimit": {"call_raise_frac": 0.3}}
    got = {}
    for name in ("omaha_four", "lowball", "fixed_raise", "short_deck", "hi_lo"):
        h = HeroCore(config_from_dict({"variant_preflop": vp, "variant_preflop_ex": ex}))
        h.new_table(V.get(name).rules, 0, 8)
        got[name] = h.preflop.p.call_raise_frac
    assert got == {"omaha_four": 0.2, "lowball": 0.25, "fixed_raise": 0.3, "short_deck": 0.15, "hi_lo": 0.15}
    for name, gate in (("short_deck", "deck"), ("two_boards", "boards"), ("wild_deuces", "wild")):
        h = HeroCore(config_from_dict({"variant_preflop": vp, "variant_preflop_ex": {gate: {"open_frac_mult": 0.5}}}))
        h.new_table(V.get(name).rules, 0, 8)
        assert (h.preflop.p.open_frac_mult, h.preflop.p.call_raise_frac) == (0.5, 0.15), name  # on top of vp
    h = HeroCore(config_from_dict({"variant_preflop_ex": ex}))
    h.new_table(Rules(), 0, 8)
    assert h.preflop.p.call_raise_frac == Config().preflop.call_raise_frac  # plain hold'em untouched


def test_split_tier_eq_bets_a_locked_board_with_a_pair_on_the_other():
    def act(flag):
        pf = Postflop(PostflopParams(split_tier_eq=flag, cbet_freq_ip_dry=0.0, semibluff_freq=0.0), seed=1)
        obs = street_obs("Kh Qh", "Ah 7h 2h", seat=1, button=7, pot=100, in_hand=HU, history=PRE)
        spot = Spot(obs, P("Kh Qh"), None)
        # a king-high flush on board 1, middle pair on board 2
        return pf.act(spot, P("Kh Qh"), None, False, board=P("Ah 7h 2h"), board2=P("Ac Qd 4s")).kind
    assert act(False) is ActionKind.CHECK
    assert act(True) is ActionKind.RAISE


def _captured_shift(dials, name, hole, board):
    h = HeroCore(config_from_dict(dials))
    h.new_table(V.get(name).rules, 0, 8)
    got = {}
    real = h.postflop.act

    def spy(*a, **kw):
        got.update(kw)
        return real(*a, **kw)

    h.postflop.act = spy
    obs = street_obs(hole, board, seat=1, button=7, pot=100, in_hand=HU, history=PRE)
    h.act(obs)
    return got.get("call_shift")


def test_multi_and_mu_value_shifts_reach_their_tables_only():
    def vs(dials, name, hole, board):
        h = HeroCore(config_from_dict(dials))
        h.new_table(V.get(name).rules, 0, 8)
        got = {}
        real = h.postflop.act

        def spy(*a, **kw):
            got.update(kw)
            return real(*a, **kw)

        h.postflop.act = spy
        h.act(street_obs(hole, board, seat=1, button=7, pot=100, in_hand=HU, history=PRE))
        return got.get("value_shift")
    d = {"multi_value_shift": 1, "mu_value_shift": 2}
    assert vs({}, "omaha_four", "Ah Kd 7c 7s", "As 9d 2h") == 0
    assert vs(d, "three_card_keep", "Ah Kd 7c", "As 9d 2h") == 1
    assert vs(d, "omaha_four", "Ah Kd 7c 7s", "As 9d 2h") == 2
    assert vs(d, "short_deck", "Ah Kd", "As 9d 7h") == 0


def test_multi_and_mu_call_shifts_reach_their_tables_only():
    d = {"multi_call_shift": 1, "mu_call_shift": 2}
    assert _captured_shift({}, "three_card_keep", "Ah Kd 7c", "As 9d 2h") == 0
    assert _captured_shift(d, "three_card_keep", "Ah Kd 7c", "As 9d 2h") == 1
    assert _captured_shift(d, "omaha_four", "Ah Kd 7c 7s", "As 9d 2h") == 2
    assert _captured_shift(d, "short_deck", "Ah Kd", "As 9d 7h") == 0
    assert _captured_shift(d, "bonus_card", "Ah Kd 7c", "As 9d 2h") == 0  # a bought third card: not dealt
    assert _captured_shift({"call_shift_ex": {"deck": 1, "wild": 2}}, "short_deck", "Ah Kd", "As 9d 7h") == 1
    assert _captured_shift({"call_shift_ex": {"deck": 1, "wild": 2}}, "wild_deuces", "Ah Kd", "As 9d 7h") == 2
    assert _captured_shift({"call_shift_ex": {"deck": 1, "wild": 2}}, "lowball", "Ah Kd", "As 9d 7h") == 0
    h = HeroCore(config_from_dict(d))
    h.new_table(Rules(), 0, 8)
    assert _captured_shift(d, "fixed_raise", "Ah Kd", "As 9d 2h") == 0


def test_twin_multi_recuts_omaha_labels_from_the_prepared_table():
    from hyperion.strategy.tables import recut_label_tables, tables_for

    base = load(need_hu=True)
    r = V.get("omaha_four").rules
    t = tables_for(r, base)
    t2, shift = recut_label_tables(generic_doc(r), t)
    assert shift > 0.1 and t2.source.endswith("+recut") and t2.scheme == t.scheme
    # the catalog set (300 hands a label) has quad deuces at equity 0.05 and AQs+hh above most aces; the re-cut has
    # every equity column monotone in rank, and AA+ss above AQs+hh
    assert t2.rank["AA+ss"] > t2.rank["AQs+hh"] and t2.equity["22+pp"][0] > 0.2
    doc = generic_doc(r)["labels"]
    labs = sorted((lb for lb in t2.rank if lb in doc), key=t2.rank.get)
    for k in range(7):
        pairs = [(t2.rank[lb], t2.equity[lb][k]) for lb in labs]
        assert all(e0 <= e1 + 1e-3 for (r0, e0), (r1, e1) in zip(pairs, pairs[1:]) if r0 < r1), k
    h = HeroCore(config_from_dict({"twin_multi": 0.05}))
    h.new_table(r, 0, 8)
    assert h.active.source.endswith("+recut")
    h = HeroCore(config_from_dict({"twin_multi": 0.5}))  # above the shift: the set as is
    h.new_table(r, 0, 8)
    assert h.active is t or not h.active.source.endswith("+recut")
    h = HeroCore(Config())
    h.new_table(r, 0, 8)
    assert not h.active.source.endswith("+recut")
