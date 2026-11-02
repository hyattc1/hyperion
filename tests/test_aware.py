"""The variant-aware opponents of the three likeliest twists (hyperion/sim/aware.py) and their fields, and the toss
prompt they read (TossHooks: the acting order and the discards so far)."""
import dataclasses

import pytest

from hyperion.core.types import ActionKind, Observation, parse_cards
from hyperion.drills import variants as V
from hyperion.sim import aware as A
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table
from hyperion.sim.field import night
from hyperion.sim.runner import run_tournament
from tests.test_variant_auction_keep2 import Decider, _rigged


def test_aware_fields_seat_hero_and_the_aware_bots_and_no_night_pool_has_them():
    for name, variant in A.AWARE_VARIANT.items():
        members = B.field_names(name)
        assert len(members) == 8 and members.count("hero") == 1
        assert variant in V.catalog_names()
        aware = [m for m in members if m in A.AWARE]
        assert len(aware) >= 3 and all(m in B.REGISTRY for m in aware)
        assert B.field_names(f"{name}@hybrid3_x")[members.index("hero")] == "hybrid3_x"
    for pool in ("night", "night_hard", "night0"):
        assert not set(night.members(pool)) & set(A.AWARE)
        for seed in range(100):
            assert not set(night.draw(pool, seed)) & set(A.AWARE)
    for field in ("realistic", "top", "judge", "judge2", "outside", "outside_strong"):
        assert not set(B.field_names(field)) & set(A.AWARE)


def test_toss_prompt_asks_in_postflop_order_with_the_discards_so_far():
    holes = ("As Ah 7c", "Kc Kd 3s", "Qh Jh Th")
    bots = [Decider(2), Decider(2), Decider(0)]
    hooks = _rigged(V.TossHooks, holes, "Ad Kh 6c 8h 2s")
    rules = dataclasses.replace(V.toss_or_holdem().rules, n_players=3, payouts=(3, 2, 1))
    t = Table(bots, rules, seed=1, variant=hooks)
    t.play_hand()
    # button 0: the flop's order is 1, 2, 0, and each prompt carries the discards made before it
    assert bots[1].prompts[0]["discards"] == {}
    assert bots[2].prompts[0]["discards"] == {1: parse_cards("3s")[0]}
    assert bots[0].prompts[0]["discards"] == {1: parse_cards("3s")[0], 2: parse_cards("Qh")[0]}
    assert list(hooks.discards) == [1, 2, 0]
    flop = [o for o in bots[0].obs if o.street == 1]
    assert flop and len(flop[0].hole) == 2 and flop[0].extras["discards"] == hooks.discards


def test_the_aware_toss_keeps_the_made_hand_then_live_draws():
    # a set beats two overcards
    assert A.toss_index(parse_cards("Ah 7c 7d"), parse_cards("Kh 7h 2c")) == 0
    # Ah 7h on 2h 9h Qc: the nut flush draw, not the king
    assert A.toss_index(parse_cards("Ah 7h Kd"), parse_cards("2h 9h Qc")) == 2
    # live outs: a spade draw has nine, four when five more spades are dead
    hole, board = parse_cards("8s 7d Kc"), parse_cards("2s 9s 3d")
    gone = set(hole) | set(board)
    assert A.live_draw_outs(parse_cards("8s 7d"), parse_cards("2s 9s 3s"), gone | set(parse_cards("3s"))) == 9
    dead = set(parse_cards("As Ks Qs Js Ts"))
    assert A.live_draw_outs(parse_cards("8s 7d"), parse_cards("2s 9s 3s"), gone | set(parse_cards("3s")) | dead) == 4


def test_short_deck_ranking_flush_over_full_house_and_the_ace_six_straight():
    sd = V.ShortDeckHooks()
    rules = V.short_deck().rules
    cases = [("Ah Kh", "7h 9h Jh 7c 7d"), ("9c 9d", "9h 7c 7d Ah Kh"), ("Ac 6d", "7h 8s 9c Kd Kh"),
             ("Kc Qd", "Kh Ks 7c 6d 8h"), ("Ac Ad", "6h 7s 8c 9d Ks")]
    for hole, board in cases:
        h, b = parse_cards(hole), parse_cards(board)
        assert A.sd_score(h + b) == sd.score_hand(h, b, rules)
    assert A.sd_category(parse_cards("Ah Kh"), parse_cards("7h 9h Jh 7c 7d")) == 6  # flush, above ...
    assert A.sd_category(parse_cards("9c 9d"), parse_cards("9h 7c 7d Ah Kh")) == 5  # ... the full house
    assert A.sd_category(parse_cards("Ac 6d"), parse_cards("7h 8s 9c Kd Kh")) == 4  # A-6-7-8-9
    r = A.sd_range(B.ChartTAG.EARLY)
    assert "AA" in r and all(c[0] not in "2345" and c[1] not in "2345" for c in r)


def _obs(hole, board, bounty=None, to_call=0, street=1, active=2):
    return Observation(hole=parse_cards(hole), board=parse_cards(board), street=street, seat=0, button=1,
                       stacks=[1900] * 8, bets=[0] * 8, in_hand=[True] * active + [False] * (8 - active), pot=100,
                       to_call=to_call, min_raise=20, max_raise=1900,
                       legal=frozenset({ActionKind.CHECK, ActionKind.RAISE, ActionKind.FOLD, ActionKind.CALL}),
                       hand_no=3, blinds=(10, 20), extras={"bounties": {0: bounty}} if bounty is not None else {})


def test_bounty_bots_bet_a_hit_bounty_when_checked_to():
    tag = B.make_bot("bounty_tag", seed=1)
    tag.new_table(V.bounty().rules, 0, 8)
    # 7c 2d on Kh 9s 4c: nothing, and the TAG checks without the bounty; the 7 is its bounty: it bets
    assert tag.act(_obs("7c 2d", "Kh 9s 4c")).kind is ActionKind.CHECK
    a = tag.act(_obs("7c 2d", "Kh 9s 4c", bounty=5))
    assert a.kind is ActionKind.RAISE and a.amount == 50
    # four players: no bet
    assert tag.act(_obs("7c 2d", "Kh 9s 4c", bounty=5, active=4)).kind is ActionKind.CHECK
    # a bounty on the board counts too
    assert B.make_bot("bounty_pushfold", seed=1).act(_obs("7c 2d", "Kh 9s 4c", bounty=11)).kind is ActionKind.RAISE


@pytest.mark.parametrize("field", sorted(A.AWARE_VARIANT))
def test_aware_fields_play_their_variant_cleanly(field):
    v = V.get(A.AWARE_VARIANT[field], seed=3)
    rep = run_tournament(B.field_names(field), 3, seed=5, mode="model", variant=v)
    for name in A.AWARE:
        if name in rep.bots:
            st = rep.bots[name].stats
            assert st.exceptions == 0 and st.illegal == 0, (name, st.last_error)
            assert st.calls > 0


def test_aware_bots_are_deterministic_for_a_seed():
    v = V.get("short_deck", seed=3)
    a = run_tournament(B.field_names("short_deck_aware"), 2, seed=9, mode="model", variant=v)
    b = run_tournament(B.field_names("short_deck_aware"), 2, seed=9, mode="model", variant=V.get("short_deck", seed=3))
    assert {k: x.samples for k, x in a.bots.items()} == {k: x.samples for k, x in b.bots.items()}
