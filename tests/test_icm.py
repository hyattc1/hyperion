from itertools import permutations

import pytest

from hyperion.core.icm import icm_cached, icm_equity


def reference_icm(stacks, payouts):
    """Independent brute force: sum over every finishing order, Harville-weighted."""
    n = len(stacks)
    alive = [i for i in range(n) if stacks[i] > 0]
    eq = [0.0] * n
    for order in permutations(alive):
        p = 1.0
        remaining = sum(stacks[i] for i in alive)
        for i in order:
            p *= stacks[i] / remaining
            remaining -= stacks[i]
        for place, i in enumerate(order):
            if place < len(payouts):
                eq[i] += p * payouts[place]
    return eq


def test_two_player_by_hand():
    # P(A first) = .75 -> A: .75*10 + .25*6 = 9, B: 7
    assert icm_equity([3000, 1000], (10, 6)) == pytest.approx([9.0, 7.0])


def test_known_three_player_example():
    # 5000/3000/2000 for 50/30/20: the standard worked example
    eq = icm_equity([5000, 3000, 2000], (50, 30, 20))
    assert eq == pytest.approx([38.392857, 32.75, 28.857143], abs=1e-5)


@pytest.mark.parametrize("stacks", [
    [2000] * 8,
    [100, 200, 300, 400, 500, 600, 700, 13200],
    [1, 1, 1, 1, 1, 1, 1, 15993],
    [4000, 0, 3000, 0, 9000, 0, 0, 0],
    [16000, 0, 0, 0, 0, 0, 0, 0],
])
def test_matches_bruteforce_up_to_eight(stacks):
    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    assert icm_equity(stacks, payouts) == pytest.approx(reference_icm(stacks, payouts), abs=1e-9)


def test_sum_is_top_k_payouts_and_busted_get_zero():
    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    stacks = [0, 5000, 0, 7000, 4000, 0, 0, 0]
    eq = icm_equity(stacks, payouts)
    assert sum(eq) == pytest.approx(8 + 7 + 6)
    assert all(eq[i] == 0 for i in range(8) if stacks[i] == 0)
    assert all(eq[i] > 0 for i in range(8) if stacks[i] > 0)


def test_monotone_in_stack_and_bounded_by_payouts():
    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    stacks = [500, 1500, 2500, 3500, 4500, 5500, 6500, 7500]
    eq = icm_equity(stacks, payouts)
    assert eq == sorted(eq)
    assert all(payouts[-1] <= e <= payouts[0] for e in eq)
    # equal stacks share equally
    assert icm_equity([100] * 4, payouts) == pytest.approx([(8 + 7 + 6 + 5) / 4] * 4)


def test_payouts_shorter_than_players():
    eq = icm_equity([1000, 1000, 1000, 1000], (10, 5))
    assert sum(eq) == pytest.approx(15)
    assert eq == pytest.approx([3.75] * 4)


def test_cached_rounds_to_big_blind_and_keeps_short_stacks_alive():
    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    a = icm_cached([2004, 1996, 3, 0], payouts, big_blind=20)
    b = icm_cached([2000, 2000, 20, 0], payouts, big_blind=20)
    assert a == b
    assert a[2] > 0 and a[3] == 0
    assert sum(a) == pytest.approx(8 + 7 + 6)
    assert icm_cached([3000, 1000], (10, 6), 20) == pytest.approx((9.0, 7.0))
