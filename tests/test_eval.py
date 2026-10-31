import random
import time

import pytest

from snapcall.core import eval as ev
from snapcall.core.cards import remap
from snapcall.core.types import Rules, parse_cards


def S(s):
    return parse_cards(s)


def test_category_ordering():
    hands = [
        ("As Ks Qs Js Ts", 8),
        ("9c 9d 9h 9s 2c", 7),
        ("Kc Kd Kh 3s 3c", 6),
        ("Ah 9h 7h 4h 2h", 5),
        ("5c 4d 3h 2s Ac", 4),
        ("Qc Qd Qh 7s 2c", 3),
        ("Jc Jd 4h 4s 9c", 2),
        ("8c 8d Ah 4s 2c", 1),
        ("Kc 9d 7h 4s 2c", 0),
    ]
    prev = 10**9
    for text, cat in hands:
        s = ev.evaluate(S(text))
        assert ev.category(s) == cat, text
        assert s < prev, text
        prev = s


def test_wheel_is_lowest_straight():
    wheel = ev.evaluate(S("5c 4d 3h 2s Ac"))
    six = ev.evaluate(S("6c 5d 4h 3s 2c"))
    assert ev.category(wheel) == 4 and wheel < six


def test_kickers_matter():
    assert ev.evaluate(S("Ac Ad Kh 7s 2c")) > ev.evaluate(S("Ac Ad Qh 7s 2c"))
    assert ev.evaluate(S("Ah 9h 7h 4h 2h")) > ev.evaluate(S("Kh 9h 7h 4h 2h"))


def test_royal_is_max_and_worst_high_card_is_min():
    assert ev.evaluate(S("As Ks Qs Js Ts")) == ev.MAX_STRENGTH
    assert ev.evaluate(S("7c 5d 4h 3s 2c")) == 1


@pytest.mark.parametrize("n", [5, 6, 7, 8])
def test_matches_bruteforce(n):
    rng = random.Random(n)
    deck = list(range(52))
    for _ in range(3000):
        rng.shuffle(deck)
        hand = deck[:n]
        assert ev.evaluate(hand) == ev.evaluate_slow(hand), hand


def test_seven_card_flush_with_more_than_five_suited():
    # 6 hearts, best flush is A K Q 9 7 (drops the 2)
    s = ev.evaluate(S("Ah Kh Qh 9h 7h 2h 3c"))
    assert s == ev.evaluate(S("Ah Kh Qh 9h 7h"))


def test_rank_permutation_variant():
    # deuces are now the highest rank, aces the lowest
    order = (12,) + tuple(range(0, 12))  # displayed 2 -> canonical A, displayed 3 -> canonical 2, ...
    rules = Rules(rank_order=order)
    quad_deuces = ev.evaluate_displayed(S("2c 2d 2h 2s 3c"), rules)
    quad_aces = ev.evaluate_displayed(S("Ac Ad Ah As 3c"), rules)
    assert quad_deuces > quad_aces
    assert remap(S("2c"), rules) == S("Ac")


def test_speed_seven_card():
    ev.warm(7)
    rng = random.Random(1)
    deck = list(range(52))
    hands = []
    for _ in range(20000):
        rng.shuffle(deck)
        hands.append(tuple(deck[:7]))
    t = time.perf_counter()
    for h in hands:
        ev.evaluate(h)
    per = (time.perf_counter() - t) / len(hands)
    # 1 ms budget; we want two orders of magnitude of headroom
    assert per < 20e-6, f"{per*1e6:.1f} us per 7-card eval"
