from snapcall.core.equity import hand_strength, monte_carlo_equity, preflop_equity
from snapcall.core.types import parse_cards as P


def test_aces_dominate_heads_up():
    aa = preflop_equity("AA", 1, 4000, seed=1)
    seven_two = preflop_equity("72o", 1, 4000, seed=1)
    assert 0.82 < aa < 0.88
    assert 0.30 < seven_two < 0.38


def test_equity_falls_with_more_opponents():
    one = preflop_equity("AKs", 1, 3000, seed=2)
    seven = preflop_equity("AKs", 7, 3000, seed=2)
    assert one > 0.6 > seven > 0.2


def test_hand_strength_nuts_is_one():
    assert hand_strength(P("Ah Kh"), P("Qh Jh Th")) == 1.0


def test_hand_strength_middling():
    hs = hand_strength(P("9c 9d"), P("Ks 7h 2c"))
    assert 0.6 < hs < 0.9


def test_monte_carlo_with_board():
    eq = monte_carlo_equity(P("Ah Kh"), P("Qh Jh 2c"), 1, 3000, seed=3)
    assert 0.65 < eq < 0.85  # royal draw plus overcards vs random
