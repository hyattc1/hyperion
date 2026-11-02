import random
import time

import pytest

from hyperion.core import eval as ev
from hyperion.core.cards import remap
from hyperion.core.types import Rules, parse_cards


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


# ----- table builds (R6: the setup budget) -----------------------------------------------------------

def test_grown_tables_equal_the_brute_force_ones():
    for n in (6, 7):
        assert ev.unsuited_table(n) == ev._build_unsuited_slow(n), n
    assert ev._grow(ev.unsuited_table(7)) == ev._build_unsuited_slow(8)


def test_grown_flush_masks_equal_the_brute_force_ones():
    from itertools import combinations

    for k in (6, 7, 8):
        for bits in combinations(range(13), k):
            m = sum(1 << r for r in bits)
            assert ev._FLUSH_N[m] == ev._best_flush_for_mask(m)
    assert len(ev._FLUSH_N) == 1287 + 1716 + 1716 + 1287


def test_a_missing_table_is_exact_and_never_built_inside_evaluate(monkeypatch):
    """An 8-card evaluate before warm(8): the best of its 7-card subsets, no build; the next warm() builds it."""
    monkeypatch.setattr(ev, "_UNSUITED_N", {k: v for k, v in ev._UNSUITED_N.items() if k <= 7})
    monkeypatch.setattr(ev, "WANTED", set())
    rng = random.Random(8)
    deck = list(range(52))
    for _ in range(1500):
        rng.shuffle(deck)
        hand = deck[:8]
        assert ev.evaluate(hand) == ev.evaluate_slow(hand), hand
    assert 8 not in ev._UNSUITED_N and ev.WANTED == {8}
    ev.warm(7)
    assert 8 in ev._UNSUITED_N and not ev.WANTED


def test_max_cards_follows_the_rules():
    from hyperion.drills import variants as V

    assert ev.max_cards(Rules()) == 7
    assert ev.max_cards(V.get("toss_or_holdem").rules) == 7  # 3 + 3 before the flop discard, 2 + 5 after
    assert ev.max_cards(V.get("three_card_keep").rules) == 8
    assert ev.max_cards(V.get("bonus_card").rules) == 8  # a third hole card bought on the flop
    assert ev.max_cards(V.get("omaha_four").rules) == 5  # two hole plus three board, always
    assert ev.max_cards(Rules(board_sizes=(0, 3, 4))) == 6
    for name in V.catalog_names():
        assert 5 <= ev.max_cards(V.get(name).rules) <= 8
