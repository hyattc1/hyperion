"""Known cards (V-h, hyperion/strategy/known.py): cards an opponent is known to hold, ours included, priced as his.
The extras shapes, the suit-invariant key, the prepared heads-up equities, Hero's class and shared-card reads behind
Config.known_cards, and the dial off playing as before."""
import dataclasses
import itertools
import random

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_cards as P
from hyperion.sim import generic as G
from hyperion.strategy import known as K
from hyperion.strategy.hero import Config, HeroCore
from hyperion.strategy.postflop import Postflop, PostflopParams

from .strategy_helpers import preflop_obs, street_obs

THREE = Rules(hole_cards=3, extras={"variant": "three_card_keep"})


def test_parse_joins_exposed_and_known_and_reads_the_viewer_entry():
    flat = {"known": {1: P("As Kd"), "2": P("2c")[0]}, "exposed": {0: 9, 1: 40}}
    assert K.parse(flat, me=0) == {1: tuple(sorted({*P("As Kd"), 40})), 2: (P("2c")[0],)}
    viewer = {"known": {0: {3: P("Qh")}, 3: {0: P("Qh")}}}
    assert K.parse(viewer, me=0) == {3: (P("Qh")[0],)}
    assert K.parse(viewer, me=5) == {}  # keyed by viewer, nothing for seat 5
    assert K.parse({"known": {0: (1, 2)}}, me=0) == {}  # only our own seat listed: nothing about the others
    perm = tuple(range(12, -1, -1))  # a reversed rank order remaps the cards as Hero remaps its own
    assert K.parse({"known": {1: (P("As")[0],)}}, me=0, rank_order=perm) == {1: (P("2s")[0],)}


def test_key_is_suit_invariant_and_complete():
    rng = random.Random(5)
    perms = list(itertools.permutations(range(4)))
    for _ in range(200):
        cards = rng.sample(range(52), 4)
        mine, shared, exposed = cards[:1], cards[1:3], cards[3:]
        k = K.key(mine, shared, exposed)
        pm = perms[rng.randrange(24)]
        f = lambda cs: [(c & ~3) | pm[c & 3] for c in cs]  # noqa: E731
        assert K.key(f(mine), f(shared), f(exposed)) == k
    # a different suit pattern is another key: As+(Ks Qs) suited links vs As+(Kh Qs)
    assert K.key(P("As"), P("Ks Qs"), ()) != K.key(P("As"), P("Kh Qs"), ())
    assert K.key(P("As"), P("Ks"), ()) != K.key(P("As"), (), P("Ks"))  # the group matters


def test_split_cuts_shared_from_exposed():
    hole = P("2c As Ah")
    assert K.split(hole, P("As Ah")) == (P("2c"), P("As Ah"), ())
    assert K.split(hole, P("As 9d")) == (P("2c Ah"), P("As"), P("9d"))


@pytest.mark.parametrize("shape", [(1, 2, 0, 1), (2, 1, 0, 2), (2, 0, 1, 1)])
def test_prepared_tables_cover_every_hand_of_their_shape(shape):
    t = K.table(shape)
    assert t is not None and len(t) == len(K.representatives(shape))
    assert all(0.0 < e < 1.0 for e in t.values())


def test_prepared_equities_point_the_right_way():
    # Chain heads-up: both links shared, only the private cards separate us
    hi = K.equity(P("Ac"), P("Ks Qh"), (), 1)
    lo = K.equity(P("2c"), P("Ks Qh"), (), 1)
    assert hi > 0.65 and lo < 0.40
    # a pair of links is his pair too: the third card decides
    assert K.equity(P("2c"), P("As Ah"), (), 1) < 0.40 < 0.55 < K.equity(P("Ad"), P("As Ah"), (), 1)
    # exposed_card heads-up: 77 against a face-up ace is behind its plain equity, ahead against a face-up deuce
    assert K.equity(P("7c 7d"), (), P("As"), 1) < 0.62 < K.equity(P("7c 7d"), (), P("2s"), 1)


def test_class_at_reads_the_nearest_equity():
    lad = ([0.3, 0.5, 0.7], ["a", "b", "c"])
    assert [K.class_at(lad, e) for e in (0.0, 0.39, 0.41, 0.66, 0.99)] == ["a", "a", "b", "c", "c"]


def _hero(kc: str, rules: Rules = THREE) -> HeroCore:
    h = HeroCore(Config(known_cards=kc, seed=1))
    h.new_table(rules, 0, 8)
    return h


def _hu_pre(hole: str, links: str):
    obs = preflop_obs(hole, 0, button=0, stacks=[2000, 2000] + [0] * 6, hand_no=150)
    return dataclasses.replace(obs, extras={"known": {0: {1: tuple(P(links))}, 1: {0: tuple(P(links))}}})


def test_known_cards_off_reads_nothing_new():
    h = _hero("")
    assert not h._known_pre and not h._known_post
    obs = _hu_pre("2c As Ah", "As Ah")
    plain = dataclasses.replace(obs, extras={})
    assert h.act(obs) == _hero("").act(plain)
    assert h.known_pre_n == 0


def test_heads_up_class_prices_the_shared_links_as_his():
    h = _hero("pre")
    assert h._known_pre and not h._known_post and len(h._known_ladder[0]) >= 300
    # AAx with both aces shared and a deuce: a kicker battle we mostly lose; the dealt class calls it a premium
    a = h.act(_hu_pre("2c As Ah", "As Ah"))
    assert h.known_pre_n == 1 and a.kind is ActionKind.FOLD
    assert _hero("").act(_hu_pre("2c As Ah", "As Ah")).kind is ActionKind.RAISE
    assert h.act(_hu_pre("Ac As Ah", "As Ah")).kind is ActionKind.RAISE  # trips against his pair


def test_unsupported_showdowns_keep_the_dealt_class():
    for rules in (Rules(hole_cards=3, must_use_hole=2, extras={"variant": "omaha_three"}),
                  Rules(extras={"variant": "lowball", "lowball": True})):
        h = _hero("pre,post", rules)
        assert not h._known_pre and not h._known_post


def test_shared_read_moves_the_shared_cards_to_the_board():
    pp = Postflop(PostflopParams(), seed=1)
    hole, board = P("7c Ks 8d"), P("Kh 9c 4d 2s Jh")
    assert pp.read_multi(hole, board)[0] >= 2  # a pair of kings, read as ours alone
    assert pp.read_shared(hole, board, P("Ks 8d"))[0] == 0  # his kings too: our seven decides, and loses
    assert pp.read_shared(P("Kc Ks 8d"), board, P("Ks 8d"))[0] >= 5  # our private king: trips against his pair
    # one link shared: a pair made with it is a pair on the board against him
    t, _, _ = pp.read_shared(P("4c As 9d"), P("Ah 7h 2s"), P("As"), more=True)
    assert t <= 1
    assert pp.read_shared(P("4c As 9d"), P("Ah 7h 2s"), P("9d"), more=True)[0] >= 3
    assert pp.read_shared(P("4c"), board, P("4c")) is None  # nothing separates us


def test_shared_reads_reach_postflop_for_opponents_in_the_hand():
    h = _hero("post")
    obs = street_obs("7c Ks 8d", "Kh 9c 4d 2s Jh", 0, button=0, stacks=[1800, 1800] + [0] * 6, pot=400,
                     in_hand=[True, True] + [False] * 6, hand_no=150)
    obs = dataclasses.replace(obs, extras={"known": {0: {1: tuple(P("Ks 8d"))}}})
    h.act(obs)
    assert h.known_post_n == 1
    # the sharing seat folded: nobody in the hand holds our cards, the plain read
    obs3 = street_obs("7c Ks 8d", "Kh 9c 4d 2s Jh", 0, button=0, stacks=[1800, 1800, 1800] + [0] * 5, pot=400,
                      in_hand=[True, False, True] + [False] * 5, hand_no=150)
    h.act(dataclasses.replace(obs3, extras={"known": {0: {1: tuple(P("Ks 8d"))}}}))
    assert h.known_post_n == 1


def test_generic_bots_hold_known_cards_in_the_seats_hand():
    ex = {"known": {0: {1: tuple(P("As"))}, 1: {0: tuple(P("As")), 2: tuple(P("Kd"))}}}
    dead, held = G.public_cards(ex, me=0, in_hand=[True, True, True])
    assert dead == set() and held == {1: tuple(P("As"))}
    dead, held = G.public_cards(ex, me=1, in_hand=[True, True, False])  # seat 2 folded: no read of his card
    assert held == {0: tuple(P("As"))}
