import random

import pytest

from hyperion.core.icm import icm_equity
from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.sim.bestiary import RandomBot
from hyperion.sim.engine import Table, Variant, play_table
from tests.sim_helpers import Auditor, Recorder, Scripted

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


class Spy(Variant):
    """Records who got which cards and where the button was, hand by hand."""

    def __init__(self):
        self.deals = []  # (hand_no, button, holes)

    def on_deal(self, hand, rng):
        self.deals.append((hand.hand_no, hand.button, list(hand.holes)))


class Rig(Variant):
    """Deals fixed hole cards and board, for exact settlement tests."""

    def __init__(self, holes, board):
        self.holes = [parse_cards(h) if h else () for h in holes]
        self.board = list(parse_cards(board))

    def on_deal(self, hand, rng):
        for s, h in enumerate(self.holes):
            if hand.in_hand[s]:
                hand.holes[s] = h
        hand.runout[:] = self.board
        hand.board = tuple(hand.runout[: len(hand.board)])


# ----- fuzz ------------------------------------------------------------------------------------


def test_fuzz_random_bots_keep_the_rules():
    rules = Rules()
    total = rules.starting_stack * rules.n_players
    hands = 0
    seed = 0
    while hands < 2000:
        bots = [Auditor(RandomBot(seed * 10 + s), total) for s in range(8)]
        t = Table(bots, rules, seed=seed)
        while not t.done:
            before = t.stacks[:]
            hs = t.play_hand()
            hands += 1
            assert sum(t.stacks) == total
            assert min(t.stacks) >= 0
            assert sum(hs.deltas) == 0
            assert sum(hs.contrib) == sum(before) - sum(t.stacks) + sum(hs.contrib)  # contrib is what left stacks
            for s in range(8):
                assert hs.contrib[s] <= before[s]
                if hs.deltas[s] > 0:
                    # a winner can take at most what each other player matched of their own stake
                    ceiling = sum(min(hs.contrib[o], hs.contrib[s]) for o in range(8) if o != s)
                    assert hs.deltas[s] <= ceiling, (s, hs.deltas, hs.contrib)
            assert hs.blinds == rules.blinds_at(hs.hand_no)
            if hs.showdown:
                assert len(hs.showdown) >= 2
                assert all(len(h) == rules.hole_cards for h in hs.showdown.values())
        res = t.result()
        assert sum(res.points) == pytest.approx(sum(rules.payouts))
        assert sorted(res.places) == list(range(8))
        assert res.hands <= rules.max_hands
        seed += 1


def test_blind_levels_advance_every_25_hands():
    bots = [Recorder() for _ in range(8)]
    res = play_table(bots, Rules(), seed=5)
    seen = {}
    for b in bots:
        for o in b.obs:
            seen[o.hand_no] = o.blinds
    assert seen[0] == (10, 20) and seen[24] == (10, 20)
    assert seen[25] == (15, 30) and seen[49] == (15, 30)
    assert seen[50] == (25, 50)
    assert seen[175] == (200, 400)
    assert res.hands == 200


# ----- dealing ---------------------------------------------------------------------------------


def test_same_seed_reproduces_the_table():
    def run():
        spy = Spy()
        res = play_table([RandomBot(s) for s in range(8)], Rules(), seed=42, variant=spy)
        return res, spy.deals

    r1, d1 = run()
    r2, d2 = run()
    assert (r1.points, r1.places, r1.stacks, r1.hands) == (r2.points, r2.places, r2.stacks, r2.hands)
    assert d1 == d2


def test_different_seeds_deal_differently():
    s1, s2 = Spy(), Spy()
    play_table([Recorder() for _ in range(8)], Rules(max_hands=3), seed=1, variant=s1)
    play_table([Recorder() for _ in range(8)], Rules(max_hands=3), seed=2, variant=s2)
    assert s1.deals[0][2] != s2.deals[0][2]


@pytest.mark.parametrize("k", [1, 3, 7])
def test_rotation_deals_same_cards_to_shifted_seats(k):
    n = 8
    base, rot = Spy(), Spy()
    play_table([Recorder() for _ in range(n)], Rules(), seed=9, rotation=0, variant=base)
    play_table([Recorder() for _ in range(n)], Rules(), seed=9, rotation=k, variant=rot)
    assert len(base.deals) == len(rot.deals) == 200
    for (h0, b0, holes0), (hk, bk, holesk) in zip(base.deals, rot.deals):
        assert h0 == hk
        assert bk == (b0 + k) % n
        for s in range(n):
            assert holesk[s] == holes0[(s - k) % n]


def test_rotation_is_a_relabelling_of_results_for_identical_bots():
    r0 = play_table([RandomBot(7) for _ in range(8)], Rules(), seed=11, rotation=0)
    r3 = play_table([RandomBot(7) for _ in range(8)], Rules(), seed=11, rotation=3)
    # identical bots with identical private seeds: the whole table is the same up to seat labels
    assert r3.points == [r0.points[(s - 3) % 8] for s in range(8)]
    assert r3.hands == r0.hands


# ----- settlement ------------------------------------------------------------------------------


def three_seat_rules(**kw):
    return Rules(n_players=3, payouts=(3, 2, 1), **kw)


def test_side_pots_pay_each_pot_to_its_best_eligible_hand():
    # button 0 (100 chips), sb 1 (300), bb 2 (1000). Everyone all-in or calling.
    bots = [Scripted([Action.raise_to(100)]), Scripted([Action.raise_to(300)]), Scripted([Action.call()])]
    rig = Rig(["AsAh", "KsKh", "QsQh"], "2c 3d 7h 8s Tc")
    t = Table(bots, three_seat_rules(), seed=0, variant=rig, stacks=[100, 300, 1000])
    hs = t.play_hand()
    assert hs.deltas == [200, 100, -300]
    assert t.stacks == [300, 400, 700]
    assert set(hs.showdown) == {0, 1, 2}


def test_uncalled_bet_returns_to_the_bettor():
    bots = [Scripted([Action.raise_to(500)]), Scripted([Action.fold()]), Scripted([Action.fold()])]
    t = Table(bots, three_seat_rules(), seed=0)
    hs = t.play_hand()
    assert hs.deltas == [30, -10, -20]
    assert not hs.showdown


def test_tie_splits_pot_and_odd_chip_goes_clockwise_from_button():
    # 4 seats: button 0, sb 1 (folds after posting 10), bb 2, utg 3. Board plays: 3-way tie of 70.
    bots = [Scripted([Action.call()]), Scripted([Action.fold()]), Scripted([]), Scripted([Action.call()])]
    rig = Rig(["2c3c", "2d3d", "2h3h", "4c5c"], "As Ks Qs Js Ts")
    t = Table(bots, Rules(n_players=4, payouts=(4, 3, 2, 1)), seed=0, variant=rig)
    hs = t.play_hand()
    assert hs.deltas == [3, -10, 4, 3]  # 70 = 23 + 23 + 23 + 1 odd chip to seat 2, first after the button


def test_short_all_in_does_not_reopen_action_for_players_who_acted():
    # button 0 raises to 100, sb 1 calls, bb 2 shoves 130 (an increment of 30 < 80: not a full raise)
    bots = [Scripted([Action.raise_to(100), Action.call()]), Scripted([Action.call(), Action.call()]),
            Scripted([Action.raise_to(130)])]
    t = Table(bots, three_seat_rules(), seed=0, stacks=[1000, 1000, 130])
    t.play_hand()
    assert bots[0].obs[1].to_call == 30 and bots[0].obs[1].legal == frozenset({FOLD, CALL})
    assert bots[1].obs[1].to_call == 30 and bots[1].obs[1].legal == frozenset({FOLD, CALL})


def test_full_raise_reopens_action_with_correct_min_raise():
    bots = [Scripted([Action.raise_to(100), Action.call()]), Scripted([Action.call(), Action.call()]),
            Scripted([Action.raise_to(200)])]
    t = Table(bots, three_seat_rules(), seed=0, stacks=[1000, 1000, 1000])
    t.play_hand()
    o = bots[0].obs[1]
    assert RAISE in o.legal and o.min_raise == 300 and o.to_call == 100
    # the big blind's option: a min-raise preflop is twice the blind
    assert bots[0].obs[0].min_raise == 40


def test_heads_up_button_posts_small_blind_and_acts_first_preflop():
    bots = [Scripted([Action.call()]), Scripted([])]
    t = Table(bots, Rules(n_players=2, payouts=(2, 1)), seed=0)
    hs = t.play_hand()
    assert hs.button == 0
    first = bots[0].obs[0]
    assert first.street == 0 and first.bets == [10, 20] and first.to_call == 10
    # postflop the big blind acts first; then the button
    assert bots[1].obs[1].street == 1 and bots[1].obs[1].seat == 1
    assert bots[0].obs[1].street == 1
    hs2 = t.play_hand()
    assert hs2.button == 1


def test_button_skips_busted_seats_and_table_ends_with_one_player():
    bots = [Scripted([Action.raise_to(100)]), Scripted([Action.raise_to(200)]), Scripted([Action.call()])]
    rig = Rig(["2c3d", "4c5d", "AsAh"], "Kc Qd 7h 8s Tc")
    t = Table(bots, three_seat_rules(), seed=0, variant=rig, stacks=[100, 200, 1000])
    t.play_hand()
    assert t.done
    res = t.result()
    assert res.places == [2, 1, 0]  # both busted the same hand: more chips at hand start finishes higher
    assert res.points == [1.0, 2.0, 3.0]
    assert res.survived == [False, False, True]


def test_bust_order_by_chips_at_hand_start_among_eight():
    # everyone shoves, the aces win; the seven losers are ranked by their starting stacks
    bots = [Scripted([Action.raise_to(10 ** 6)] * 1) for _ in range(8)]
    rig = Rig(["AsAh", "2c3c", "2d3d", "2h3h", "4c5c", "4d5d", "4h5h", "7c8c"], "Kc Qd 9h Ts Jc")
    stacks = [2000, 100, 200, 300, 400, 500, 600, 700]
    res = play_table(bots, Rules(), seed=0, variant=rig, stacks=stacks)
    assert res.places == [0, 7, 6, 5, 4, 3, 2, 1]
    assert res.points == [8.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]


def test_survivors_at_the_cap_split_remaining_points_by_icm():
    rules = Rules(max_hands=6)
    bots = [Recorder() for _ in range(8)]
    res = play_table(bots, rules, seed=3)
    assert res.hands == 6 and all(res.survived)
    assert res.points == pytest.approx(icm_equity(res.stacks, rules.payouts))
    assert sum(res.points) == pytest.approx(sum(rules.payouts))
    by_stack = sorted(range(8), key=lambda s: (-res.stacks[s], s))
    assert [res.places[s] for s in by_stack] == list(range(8))


def test_cap_after_some_busts_uses_only_the_remaining_payouts():
    # seat 0 busts on hand 0; the other two survive to a 2-hand cap and share payouts (3, 2) by ICM
    bots = [Scripted([Action.raise_to(100)]), Scripted([Action.raise_to(200)]), Scripted([Action.call()])]
    rig = Rig(["2c3d", "KsKh", "AsAh"], "Jc Qd 7h 8s Tc")
    res = play_table(bots, three_seat_rules(max_hands=2), seed=0, variant=rig, stacks=[100, 1000, 1000])
    assert res.places[0] == 2 and res.points[0] == 1.0
    assert sum(res.points) == pytest.approx(6.0)
    assert res.points[1] + res.points[2] == pytest.approx(5.0)
    assert res.points[2] > res.points[1]  # aces won the first hand


# ----- variants --------------------------------------------------------------------------------


def test_rank_order_is_applied_at_showdown():
    # deuces are the top rank: displayed 2222 beats displayed AAAA
    order = (12,) + tuple(range(12))
    rules = Rules(n_players=2, payouts=(2, 1), rank_order=order)
    bots = [Scripted([Action.raise_to(2000)]), Scripted([Action.call()])]
    rig = Rig(["2c2d", "AcAd"], "2h 2s Ah 7c 9d")
    t = Table(bots, rules, seed=0, variant=rig)
    hs = t.play_hand()
    assert hs.deltas == [2000, -2000]


def test_variant_hooks_can_change_hole_cards_and_board_sizes():
    class Discard(Variant):
        def on_deal(self, hand, rng):
            for s in range(len(hand.holes)):
                if hand.holes[s]:
                    hand.holes[s] = hand.holes[s][:2]

    rules = Rules(hole_cards=3, board_sizes=(0, 3, 4, 5))
    bots = [Scripted([Action.raise_to(2000)] + [Action.call()] * 3) for _ in range(8)]
    t = Table(bots, rules, seed=1, variant=Discard())
    hs = t.play_hand()
    assert all(len(h) == 2 for h in hs.showdown.values())
    assert len(hs.board) == 5


def test_generic_board_sizes_and_hole_counts():
    rules = Rules(hole_cards=3, board_sizes=(0, 2, 4, 5), n_players=6, payouts=(6, 5, 4, 3, 2, 1))
    seen_streets = set()

    class Watch(Variant):
        def on_street(self, hand, street, rng):
            seen_streets.add((street, len(hand.board)))

    bots = [Scripted([Action.call()] * 8) for _ in range(6)]
    t = Table(bots, rules, seed=1, variant=Watch())
    hs = t.play_hand()
    assert seen_streets == {(1, 2), (2, 4), (3, 5)}
    assert all(len(h) == 3 for h in hs.showdown.values())


def test_requires_two_seats_and_a_known_mode():
    with pytest.raises(ValueError):
        Table([Recorder()], Rules())
    with pytest.raises(ValueError):
        Table([Recorder(), Recorder()], Rules(), mode="fast")
