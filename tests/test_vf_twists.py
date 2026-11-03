"""V-f (docs/drills/climb/vf-log.md): the hold'em-gated gains carried to the one-step twist families by dials that list
them (postflop.size_read_twists, postflop.s11_twists, r3.v3_bvb_twists, the composite's strong_route_twists). Off by
default: every gate stays as it was (hold'em only), so F plays as before."""
import pytest

from hyperion.core.types import ActionKind, Observation, Rules
from hyperion.drills import variants as V
from hyperion.strategy.hero import TWIST_FAMILIES, twist_families, twist_family
from hyperion.strategy.postflop import Postflop, PostflopParams
from hyperion.strategy.spot import Spot

FAMILY = {"toss_or_holdem": "discard", "three_card_blind_discard": "discard", "bounty": "bounty",
          "knockout_bounty": "knockout", "bonus_card": "buy", "auction": "buy", "swap_holdem": "swap",
          "swap_one_turn": "swap", "exposed_card": "exposed"}
D3 = {"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0, "hero.postflop.size_read_min_alive": 4,
      "hero.postflop.size_read_holdem_only": True, "hero.postflop.size_read_min_bets": 2,
      "hero.postflop.size_read_min_share": 0.15, "hero.postflop.size_read_min_buckets": 2,
      "hero.postflop.size_read_skip_weak": True, "hero.postflop.size_read_streets": 3,
      "hero.postflop.size_read_min_cbet": 0.55}
Z3 = {"r3.v3_bvb_prior": 0.15, "hero.postflop.probe_from": 0.75, "hero.postflop.probe_n": 2,
      "hero.postflop.probe_margin": 0.03, "hero.postflop.probe_raise_tier": 5, "hero.postflop.probe_bluff": 0.4,
      "hero.postflop.balance_sizes": True, "hero.postflop.s11_holdem_only": True, "r3.v3_bvb_holdem_only": True}
SR = {"strong_route": "pre_open_10=elite1x", "strong_rr": 0.2}
ALL = "discard,bounty,knockout,buy,swap,exposed"


def test_the_family_of_every_catalog_entry():
    for name in V.catalog_names():
        assert twist_family(V.get(name).rules) == FAMILY.get(name), name
    assert twist_family(Rules()) is None
    # two twists at once, or a key the family does not know: no family (the gate stays shut)
    assert twist_family(Rules(extras={"variant": "bounty", "bounty_ratio": 1.5, "swap_street": 2})) is None
    assert twist_family(Rules(extras={"variant": "swap_holdem", "swap_p_flop": 0.1, "wild_rank": 0})) is None
    assert twist_family(Rules(extras={"variant": "exposed_card", "exposed_index": 0}, n_suits=3)) is None
    # tonight's own name for a twist of a known shape is that family; another family's catalog name is not
    assert twist_family(Rules(hole_cards=3, extras={"variant": "pineapple_tonight", "discard_street": 1,
                                                    "discard_face_up": True, "keep": 2})) == "discard"
    assert twist_family(Rules(extras={"variant": "auction", "swap_p_flop": 0.1})) is None
    assert twist_family(Rules(extras={"variant": "short_deck", "removed_ranks": [0, 1, 2, 3]})) is None
    assert set(FAMILY.values()) == set(TWIST_FAMILIES)


def test_an_unknown_family_name_fails():
    assert twist_families(ALL) == frozenset(TWIST_FAMILIES)
    with pytest.raises(KeyError):
        twist_families("discard,bounties")
    with pytest.raises(KeyError):
        Postflop(PostflopParams(size_read_twists="toss"))


def _hero(bot):
    m = bot.core.members[bot.core.names.index("hero")]
    return m


def test_the_dials_off_keep_every_gain_on_hold_em_only():
    from hyperion import ship

    bot = ship.make_bot("composite", {**D3, **Z3})
    hero = _hero(bot)
    for name in FAMILY:
        hero.new_table(V.get(name).rules, 0, 8)
        pf = hero.postflop
        assert pf._sr_on is False and pf._tw is None and pf.p.balance_sizes is False, name
    hero.new_table(Rules(), 0, 8)
    assert hero.postflop._sr_on is True and hero.postflop.p.balance_sizes is True


def test_each_dial_reaches_only_its_families():
    from hyperion import ship

    bot = ship.make_bot("composite", {**D3, **Z3, "hero.postflop.size_read_twists": "discard,swap",
                                      "hero.postflop.s11_twists": "bounty"})
    hero = _hero(bot)
    pf = hero.postflop
    for name, fam in FAMILY.items():
        hero.new_table(V.get(name).rules, 0, 8)
        assert pf._sr_on is (fam in ("discard", "swap")), name
        assert pf.p.balance_sizes is (fam == "bounty") and (pf.p.probe_from == 0.75) is (fam == "bounty"), name
        assert pf._tw == (fam if fam in ("discard", "swap", "bounty") else None), name
    hero.new_table(V.get("short_deck").rules, 0, 8)
    assert pf._sr_on is False and pf.p.balance_sizes is False and pf._tw is None
    # the fallback Hero of the base (the tables Hero plays whole: toss, exposed) carries the same dials
    base_hero = bot.core.members[0].hero
    base_hero.new_table(V.get("toss_or_holdem").rules, 0, 8)
    assert base_hero.postflop._sr_on is True


def test_the_bvb_prior_dial_reaches_rival_3s_core_on_its_families():
    from hyperion import ship

    for tw, want in (("", False), ("bounty,swap", True)):
        bot = ship.make_bot("composite", {**Z3, "r3.v3_bvb_twists": tw})
        base = bot.core.members[0]
        base.new_table(V.get("bounty").rules, 0, 8)
        assert base.core.holdem is want
        base.new_table(V.get("auction").rules, 0, 8)
        assert base.core.holdem is False
        base.new_table(Rules(), 0, 8)
        assert base.core.holdem is True


def test_the_strong_route_dial_lets_elite1_play_only_where_the_core_plays_the_table():
    from hyperion import ship

    off = ship.make_bot("composite", SR)
    on = ship.make_bot("composite", {**SR, "strong_route_twists": ALL})
    e = on.core.names.index("elite1")
    for name, fam in FAMILY.items():
        rules = V.get(name).rules
        off.core.new_table(rules, 0, 8)
        on.core.new_table(rules, 0, 8)
        assert off.core._no_h[e] is True, name
        assert on.core._no_h[e] is False, name
        # the base's core plays the table (elite1 may play its sections) except where Hero plays it whole
        assert on.core.plain is (fam not in ("discard", "exposed")), name
    with pytest.raises(KeyError):
        ship.make_bot("composite", {**SR, "strong_route_twists": "toss"})


def _spot(extras, board=(8, 20, 33), stacks=(1000, 1000), bets=(0, 100), to_call=100):
    obs = Observation(hole=(0, 1), board=board, street=1, seat=0, button=0, stacks=list(stacks), bets=list(bets),
                      in_hand=[True, True], pot=200, to_call=to_call, min_raise=200, max_raise=1000,
                      legal=frozenset(ActionKind), hand_no=3, blinds=(10, 20), history=[], extras=extras)
    return Spot(obs, (0, 1))


def test_the_twist_read_skips_a_bettor_the_twist_explains():
    pf = Postflop(PostflopParams(size_read_twists=ALL))
    pf.holdem = False
    pf.family = "buy"
    assert pf._twist_read_off(_spot({"bought": {1: True, 0: False}}), 1)
    assert not pf._twist_read_off(_spot({"bought": {1: False, 0: True}}), 1)
    assert pf._twist_read_off(_spot({"auction_winners": (1,), "bids": {0: 5, 1: 9}}), 1)
    assert not pf._twist_read_off(_spot({"auction_winners": (0,)}), 1)
    pf.family = "bounty"  # board ranks 2, 5, 8 (cards 8, 20, 33)
    assert pf._twist_read_off(_spot({"bounties": {0: 12, 1: 5}}), 1)
    assert not pf._twist_read_off(_spot({"bounties": {0: 5, 1: 11}}), 1)
    assert not pf._twist_read_off(_spot({}), 1)  # private bounties: no test
    pf.family = "knockout"
    assert pf._twist_read_off(_spot({}, stacks=(400, 1000), bets=(0, 500), to_call=500), 1)
    assert not pf._twist_read_off(_spot({}), 1)
    for fam in ("discard", "swap", "exposed"):
        pf.family = fam
        assert not pf._twist_read_off(_spot({"bought": {1: True}, "bounties": {1: 5}}), 1)
    pf.holdem = True  # a hold'em table: no twist to respect
    pf.family = None
    assert pf._tw is None and not pf._twist_read_off(_spot({"bought": {1: True}}), 1)


def _vdigest(dials, name, table=0):
    from hyperion import ship
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table

    from .test_ship import QUIET, _Recorder

    seed = 11 * 1_000_003 + table
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    for b in bots:
        if hasattr(b, "use_cost_model"):
            b.use_cost_model(True)
    bot = ship.make_bot("composite", {**QUIET, "late_us": 1e9, **dials}, seed=seed * 64)
    rec = bots[0] = _Recorder(bot)
    v = V.get(name, seed=seed)
    play_table(bots, v.rules, seed=seed, mode="model", variant=v.new_hooks())
    return rec.h.hexdigest()


@pytest.mark.parametrize("name", sorted(FAMILY))
def test_each_gain_gated_to_hold_em_plays_every_family_exactly_as_f(name):
    # so one F run is the base of all three twist extensions on these tables (docs/drills/climb/vf-log.md)
    f = _vdigest({}, name)
    for gain in (D3, Z3, SR):
        assert _vdigest(gain, name) == f, (name, gain)
