import random

import pytest

from hyperion.core.types import ActionKind, Observation, Rules
from hyperion.core.types import parse_cards as P
from hyperion.drills import variants as V
from hyperion.tablegen import rules_from_dict


@pytest.mark.parametrize("name", V.names())
def test_every_preset_is_valid(name):
    v = V.get(name, seed=5)
    assert isinstance(v.rules, Rules)
    assert V.validate(v) == []
    assert v.breaks and len(v.checklist) >= 1 and v.summary
    assert rules_from_dict(v.rules_json()) == v.rules
    if v.needs_engine and v.hooks is not None:
        h = v.hooks
        holes = [P("Ah Kh"), P("2c 3d")]
        deck = list(range(10, 50))
        rng = random.Random(1)
        out = h.on_deal(holes, deck, rng)
        assert len(out) == 2
        board, holes2 = h.on_street(1, P("Qh Jh Tc"), holes, deck, rng)
        assert isinstance(board, tuple) and len(holes2) == 2
        assert isinstance(h.score_hand(P("Ah Kh"), P("Qh Jh Tc 2d 3s"), v.rules), int)
        assert h.on_payout([50, -50], holes, P("Qh Jh Tc 2d 3s"), 3, v.rules, rng) is not None


def test_permuted_ranks_is_a_seeded_permutation():
    a, b = V.permuted_ranks(3), V.permuted_ranks(3)
    assert a.rules.rank_order == b.rules.rank_order and sorted(a.rules.rank_order) == list(range(13))
    assert V.permuted_ranks(4).rules.rank_order != a.rules.rank_order


def test_toss_default_discards_lowest_card_face_up():
    h = V.TossHooks()
    holes = [P("Ah Kh 2c"), P("7d 7s 9c"), ()]
    board, new = h.on_street(1, P("Qh Jh 4d"), holes, [], random.Random(0))
    assert new[0] == P("Ah Kh") and new[1] == P("7d 7s") and new[2] == ()
    assert board == P("Qh Jh 4d") and h.discards == {0: P("2c")[0], 1: P("9c")[0]}
    board2, new2 = h.on_street(1, P("Qh Jh 4d"), holes, [], random.Random(0), ask=lambda seat, prompt: 0)
    assert new2[0] == P("Kh 2c")
    assert h.on_street(2, board, new, [], random.Random(0)) == (board, new)


def test_swap_replaces_cards_with_probability():
    h = V.SwapHooks(p_flop=1.0, p_turn=0.0)
    deck = [40, 41, 42, 43]
    board, new = h.on_street(1, (), [P("Ah Kh"), P("2c 3d")], deck, random.Random(0))
    assert sorted(new[0] + new[1]) == [40, 41, 42, 43] and deck == []
    _, same = h.on_street(2, (), [P("Ah Kh")], [1, 2], random.Random(0))
    assert same[0] == P("Ah Kh")


def test_short_deck_scoring():
    h = V.ShortDeckHooks()
    r = V.short_deck().rules
    flush = h.score_hand(P("Ah 9h"), P("Kh 7h 6h 8c 8d"), r)
    full = h.score_hand(P("8s 8h"), P("Kc 7h 6h 8c 6d"), r)
    assert flush > full
    low_straight = h.score_hand(P("Ac 6d"), P("7h 8c 9s Kd Qd"), r)
    trips = h.score_hand(P("Kc Kd"), P("7h 8c Ks 2d Qd"), r)
    assert low_straight > trips
    assert h.score_hand(P("Ac 6c"), P("7c 8c 9c Kd Qd"), r) > h.score_hand(P("Kc Kd"), P("Kh Ks 6d 7d 8d"), r)


def test_bounty_payout_scales_only_hits():
    h = V.BountyHooks(ratio=1.5, constant=10, rounds_per_bounty=25)
    rng = random.Random(0)
    holes = [P("Ah Kh"), P("2c 3d")]
    out = h.on_payout([100, -100], holes, P("Qh Jh Tc 2d 3s"), 0, Rules(), rng)
    assert out[1] == -100 and out[0] in (100, 160)
    h.bounties = {0: 12, 1: 0}  # ace for seat 0
    assert h.on_payout([100, -100], holes, P("Qh Jh Tc 2d 3s"), 1, Rules(), rng)[0] == 160


def test_two_boards_hook_keeps_a_second_board():
    h = V.TwoBoardsHooks()
    deck = list(range(0, 32))  # no overlap with the hole or board
    h.on_deal([P("Ah Kh")], deck, random.Random(0))
    board = P("Qh Jh Tc")
    h.on_street(1, board, [P("Ah Kh")], deck, random.Random(0))
    assert len(h.board2) == 3 and len(deck) == 29
    h.on_street(2, board + P("2d"), [P("Ah Kh")], deck, random.Random(0))
    assert len(h.board2) == 4 and len(h.score_boards(P("Ah Kh"), board + P("2d") + P("3s"), Rules())) == 2


def test_pot_limit_cap():
    obs = Observation(hole=P("Ah Kh"), board=(), street=0, seat=2, button=0, stacks=[2000, 1990, 1980],
                      bets=[0, 10, 20], in_hand=[True] * 3, pot=0, to_call=0, min_raise=40, max_raise=2000,
                      legal=frozenset({ActionKind.CHECK, ActionKind.RAISE}), hand_no=0, blinds=(10, 20))
    assert V.pot_limit_max_raise(obs) == 50  # 20 current + 30 pot after (zero) call
    obs.seat, obs.to_call = 0, 20
    assert V.pot_limit_max_raise(obs) == 20 + (30 + 20)
