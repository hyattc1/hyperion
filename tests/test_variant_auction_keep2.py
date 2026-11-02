"""The two entries added from the research's gaps: `auction` (MIT 2024's sealed-bid auction for a third hole card,
eight-handed) and `deal5_keep2` (CMU 2026: five hole cards, keep two, three discards face up). The rules as
implemented, one test per rule."""
import dataclasses

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim.bestiary import ChartTAG, RandomBot
from hyperion.sim.engine import Table, play_table
from tests.sim_helpers import Scripted

THREE = Rules(n_players=3, payouts=(3, 2, 1))


class Decider(Scripted):
    """Plays `actions`, then checks and calls; answers every variant prompt with `answer` and keeps the prompts."""

    def __init__(self, answer, actions=()):
        super().__init__(list(actions))
        self.answer, self.prompts = answer, []

    def variant_decide(self, prompt):
        self.prompts.append(prompt)
        return self.answer


def _rigged(cls, holes, board, extra="", **kw):
    """`cls` hooks dealing fixed hole cards and board; the fixed cards are taken out of the spare deck, and the cards
    in `extra` are the first ones popped from it, in that order."""
    fixed_holes = [parse_cards(h) for h in holes]
    fixed_board = list(parse_cards(board))
    pops = list(parse_cards(extra)) if extra else []
    used = {c for h in fixed_holes for c in h} | set(fixed_board) | set(pops)

    class Rigged(cls):
        def on_deal(self, holes_, deck, rng):
            deck[:] = [c for c in deck if c not in used] + pops[::-1]
            super().on_deal(holes_, deck, rng)
            return [fixed_holes[s] if holes_[s] else () for s in range(len(holes_))]

        def on_street(self, street, board_, holes_, deck, rng, ask=None):
            return super().on_street(street, tuple(fixed_board[: len(board_)]), holes_, deck, rng, ask)

    return Rigged(**kw)


# ----- auction ------------------------------------------------------------------------------------------------


def _auction_hand(answers, stacks=None, holes=("2c7d", "AsAh", "8c8d"), board="Kd 9s 4c 5h Jd", extra="2h 3c 4d",
                  actions=((), (), ())):
    bots = [Decider(a, act) if not isinstance(a, Scripted) else a for a, act in zip(answers, actions)]
    hooks = _rigged(V.AuctionHooks, holes, board, extra)
    t = Table(bots, THREE, seed=4, variant=hooks, stacks=stacks)
    total = sum(t.stacks)
    hs = t.play_hand()
    assert sum(t.stacks) == total and sum(hs.deltas) == 0
    return t, hs, hooks, bots


def test_auction_highest_bid_wins_a_card_and_pays_the_second_highest_into_the_pot():
    # three-handed: the button (0) calls, sb (1) calls, bb (2) checks: 60 in the pot at the flop
    t, hs, hooks, bots = _auction_hand([50, 30, 10])
    assert hooks.bids == {0: 50, 1: 30, 2: 10} and hooks.winners == (0,) and hooks.price == 30
    assert len(hs.holes[0]) == 3 and len(hs.holes[1]) == 2 and len(hs.holes[2]) == 2
    p = bots[1].prompts[0]
    assert p["decision"] == "bid" and p["pot"] == 60 and p["max_bid"] == p["stack"] == 1980 and p["n_bidders"] == 3
    # the price is dead money in the pot: the aces win it (MIT: the payment goes to the pot, won at showdown)
    assert hs.deltas == [-50, 70, -20]
    flop = [o for o in bots[2].obs if o.street == 1]
    assert flop[0].extras == {"bids": {0: 50, 1: 30, 2: 10}, "auction_winners": (0,), "auction_price": 30}
    assert flop[0].pot == 90  # the pot the flop betting sees includes the price


def test_auction_tied_top_bids_all_get_a_card_and_all_pay_the_bid():
    t, hs, hooks, _ = _auction_hand([40, 40, 10])
    assert hooks.winners == (0, 1) and hooks.price == 40
    assert len(hs.holes[0]) == 3 and len(hs.holes[1]) == 3 and len(hs.holes[2]) == 2
    assert hs.holes[0][2] == parse_cards("2h")[0] and hs.holes[1][2] == parse_cards("3c")[0]
    assert hs.deltas == [-60, 80, -20]  # the aces take 60 of bets and both prices


def test_auction_everyone_at_zero_is_a_tie_and_every_card_is_free():
    t, hs, hooks, _ = _auction_hand([0, 0, 0])
    assert hooks.winners == (0, 1, 2) and hooks.price == 0 and all(len(h) == 3 for h in hs.holes)


def test_auction_illegal_bids_are_zero_and_a_silent_bot_bids_a_quarter_of_the_pot():
    t, hs, hooks, _ = _auction_hand([5000, "x", Scripted([])])  # over the stack, not a number, no variant_decide
    assert hooks.bids == {0: 0, 1: 0, 2: 15}  # 60 // 4
    assert hooks.winners == (2,) and hooks.price == 0
    assert V.legal_bid(-1, 100) == 0 and V.legal_bid(True, 100) == 0 and V.legal_bid(7.9, 100) == 7
    assert V.default_bid(400, 50) == 50 and V.default_bid(400, 500) == 100


def test_auction_a_player_all_in_before_the_flop_bids_zero_unasked():
    # the bb (2) has 15 chips: all-in on the blind; the others call 20
    t, hs, hooks, bots = _auction_hand([25, 5, 99], stacks=[2000, 2000, 15])
    assert not bots[2].prompts and hooks.bids[2] == 0
    assert hooks.winners == (0,) and hooks.price == 5


def test_auction_dead_money_is_won_among_the_players_who_had_chips_when_it_was_paid():
    # the bb (2) is all-in for 15 before the flop, so only seats 0 and 1 bid: seat 0 wins at 25, pays 5 (gets the 2h)
    allin = [2000, 2000, 15]
    t, hs, hooks, _ = _auction_hand([25, 5, 0], stacks=allin)
    assert hs.deltas == [-20, 35, -15]  # the aces (seat 1) win the 45 and the 5
    # the bb's aces win the 45 they can win; the 5 goes to the best of seats 0 and 1 (seat 0's deuces)
    t, hs, hooks, _ = _auction_hand([25, 5, 0], stacks=allin, holes=("2c7d", "3h6s", "AsAh"))
    assert hs.deltas == [-15, -15, 30]
    # with a side pot: seat 1 bets 40 on the flop and seat 0 calls. Main 45 to the bb's eights; the side pot 80 and
    # the price 5 to seat 0's deuces (a price paid at the bb's level would have gone to the eights)
    t, hs, hooks, _ = _auction_hand([25, 5, 0], stacks=allin, holes=("2c7d", "3h6s", "8c8d"),
                                    actions=((), (Action.call(), Action.raise_to(40)), ()))
    assert hs.contrib == [55, 55, 15] and hs.deltas == [25, -55, 30]


@pytest.mark.parametrize("seed", range(4))
def test_auction_entry_plays_and_conserves_chips(seed):
    v = V.get("auction")
    rules = dataclasses.replace(v.rules, max_hands=60)
    total = rules.starting_stack * rules.n_players
    bots = [RandomBot(seed * 10 + s) if s % 2 else ChartTAG(seed * 10 + s) for s in range(8)]
    t = Table(bots, rules, seed=seed, variant=v.new_hooks())
    while not t.done:
        hs = t.play_hand()
        assert sum(t.stacks) == total and sum(hs.deltas) == 0
        held = [c for h in hs.holes if h for c in h] + list(hs.board)
        assert len(held) == len(set(held))  # the third cards never collide with anything dealt
    assert all(st.exceptions == 0 and st.illegal == 0 for st in t.stats)


# ----- deal5_keep2 --------------------------------------------------------------------------------------------


def test_keep2_discards_in_postflop_order_each_seeing_the_ones_before():
    holes = ("As Ah 7c 2d 9s", "Kc Kd 3s 4s 5d", "Qh Jh Th 2c 3c")
    bots = [Decider((0, 1)), Decider((0, 1)), Decider((0, 1))]
    hooks = _rigged(V.Keep2Hooks, holes, "Ad Kh 6c 8h 2s")
    t = Table(bots, dataclasses.replace(V.deal5_keep2().rules, n_players=3, payouts=(3, 2, 1)), seed=1, variant=hooks)
    hs = t.play_hand()
    # button 0: the flop's order is 1, 2, 0
    assert hooks.order == (1, 2, 0)
    assert bots[1].prompts[0]["revealed"] == {}
    assert set(bots[2].prompts[0]["revealed"]) == {1}
    assert set(bots[0].prompts[0]["revealed"]) == {1, 2}
    assert len(bots[0].prompts[0]["hole"]) == 5 and len(bots[0].prompts[0]["board"]) == 3
    assert hooks.revealed == {1: parse_cards("3s 4s 5d"), 2: parse_cards("Th 2c 3c"), 0: parse_cards("7c 2d 9s")}
    assert hs.showdown == {0: parse_cards("As Ah"), 1: parse_cards("Kc Kd"), 2: parse_cards("Qh Jh")}
    flop = [o for o in bots[0].obs if o.street == 1]
    assert flop and len(flop[0].hole) == 2 and flop[0].extras["revealed"] == hooks.revealed
    pre = [o for o in bots[0].obs if o.street == 0]
    assert pre and len(pre[0].hole) == 5
    assert hs.deltas[0] > 0  # trip aces


def test_keep2_invalid_or_missing_answers_keep_the_best_made_hand():
    holes = ("2d 9s As 7c Ah", "Kc 3s 4s 5d Kd", "Qh Jh Th 2c 3c")
    bots = [Decider((1, 1)), Decider("no"), Scripted([])]
    hooks = _rigged(V.Keep2Hooks, holes, "Ad Kh 6c 8h 2s")
    t = Table(bots, dataclasses.replace(V.deal5_keep2().rules, n_players=3, payouts=(3, 2, 1)), seed=1, variant=hooks)
    hs = t.play_hand()
    assert set(hs.showdown[0]) == set(parse_cards("As Ah"))  # trips
    assert set(hs.showdown[1]) == set(parse_cards("Kc Kd"))  # trips
    # nothing made: the best high-card hand with the flop, Qh Jh (A K Q J 6)
    assert V.default_keep(parse_cards("Qh Jh Th 2c 3c"), parse_cards("Ad Kh 6c")) == (0, 1)
    assert V.legal_keep((4, 0), 5) == (0, 4) and V.legal_keep((0, 0), 5) is None and V.legal_keep((0, 5), 5) is None
    assert V.legal_keep(None, 5) is None and V.legal_keep([1, 2, 3], 5) is None


@pytest.mark.parametrize("seed", range(4))
def test_keep2_entry_plays_and_conserves_chips(seed):
    v = V.get("deal5_keep2")
    assert V.validate(v) == []
    rules = dataclasses.replace(v.rules, max_hands=60)
    total = rules.starting_stack * rules.n_players
    bots = [RandomBot(seed * 10 + s) if s % 2 else ChartTAG(seed * 10 + s) for s in range(8)]
    t = Table(bots, rules, seed=seed, variant=v.new_hooks())
    while not t.done:
        hs = t.play_hand()
        assert sum(t.stacks) == total and sum(hs.deltas) == 0
        assert all(len(h) == 2 for h in hs.showdown.values())
        dead = [c for d in t.variant.hooks.revealed.values() for c in d]
        held = [c for h in hs.showdown.values() for c in h] + list(hs.board) + dead
        assert len(held) == len(set(held))
    assert all(st.exceptions == 0 and st.illegal == 0 for st in t.stats)


# ----- F's decisions (Hero's variant_decide, which the composite's base answers with) -------------------------


def _ship():
    from hyperion.ship import make_bot

    return make_bot()


@pytest.mark.parametrize("make", ["hero", "ship"])
def test_the_bid_is_the_cards_worth_capped_and_fast(make):
    import time

    from hyperion.strategy.hero import Hero

    bot = Hero() if make == "hero" else _ship()
    bot.new_table(V.get("auction").rules, 0, 8)
    base = {"decision": "bid", "hole": parse_cards("Ah 7d"), "board": parse_cards("Kd 9s 4c"), "pot": 120,
            "stack": 1900, "max_bid": 1900, "n_bidders": 2, "seat": 0, "big_blind": 20}
    air = bot.variant_decide(base)
    made = bot.variant_decide({**base, "hole": parse_cards("Kh Ks")})
    three_way = bot.variant_decide({**base, "n_bidders": 3})
    short = bot.variant_decide({**base, "stack": 40, "max_bid": 40})
    # a card is worth most to air heads-up (d ~ 0.38 of the pot) and little to a set; more bidders, less each
    assert isinstance(air, int) and 0.5 * 120 < air <= 0.75 * 120
    assert 0 <= made < air / 3 and three_way < air
    assert short <= 0.33 * 40 + 1
    assert bot.variant_decide({**base, "pot": 0}) == 0
    t0 = time.perf_counter()
    for _ in range(200):
        bot.variant_decide(base)
    assert (time.perf_counter() - t0) / 200 < 2e-4  # ~3 us; the budget is 1 ms


@pytest.mark.parametrize("make", ["hero", "ship"])
def test_the_keep_takes_the_best_flop_read_with_the_discards_dead(make):
    from hyperion.strategy.hero import Hero

    bot = Hero() if make == "hero" else _ship()
    bot.new_table(V.get("deal5_keep2").rules, 0, 8)
    p = {"decision": "keep", "hole": parse_cards("7c 2d As 9s Ah"), "board": parse_cards("Ad Kh 6c"), "revealed": {}}
    assert sorted(bot.variant_decide(p)) == [2, 4]  # trip aces
    # QJ of hearts is an open-ender and a flush draw on Th 9h 4d; the pocket fours (a set) still come first
    p = {"decision": "keep", "hole": parse_cards("Qh Jh 4c 4s 2c"), "board": parse_cards("Th 9h 4d"), "revealed": {}}
    assert sorted(bot.variant_decide(p)) == [2, 3]
    p = {"decision": "keep", "hole": parse_cards("Qh Jh 3c 5s 2c"), "board": parse_cards("Th 9h 4d"), "revealed": {}}
    assert sorted(bot.variant_decide(p)) == [0, 1]


def test_hero_takes_revealed_discards_off_its_outs():
    from hyperion.strategy.hero import HeroCore

    core = HeroCore()
    core.new_table(V.get("deal5_keep2").rules, 0, 8)
    assert core._revealed({3: parse_cards("8h 7h Ks"), 0: parse_cards("2c 2d 3s")}) == parse_cards("8h 7h Ks 2c 2d 3s")
    read = core.postflop._read
    hole, board = parse_cards("Qh Jh"), parse_cards("Th 9h 4d")
    live = read(hole, board, 0, ())[1]
    dead = read(hole, board, 0, parse_cards("8h 7h 2h 3h Kh Ks Kd 8s 8d"))[1]
    assert dead < live


@pytest.mark.parametrize("name,field", [("auction", "realistic_auction"), ("deal5_keep2", "realistic_keep2")])
def test_f_plays_the_new_entries_against_their_aware_field_without_errors(name, field):
    from hyperion.ship import register_sim
    from hyperion.sim.bestiary import field_names
    from hyperion.sim.runner import run_tournament

    register_sim()
    rep = run_tournament(field_names(f"{field}@ship"), 3, seed=2, variant=V.get(name), mode="model")
    st = rep.bots["ship"].stats
    assert st.exceptions == 0 and st.illegal == 0 and st.safe_err == 0 and rep.hands > 0
    assert all(b.stats.exceptions == 0 for nm, b in rep.bots.items() if nm in ("auction_tag", "keep2_tag"))
