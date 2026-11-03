"""V-j: payoff by street in the engine (Rules.extras settle="street", no_runout) and the tranche_holdem entry.

Every number here is worked by hand from kit I's handout (docs/drills/drill11/kitI-README.md, section 3), not from the
kit's code: the deal and the per-street awards, side pots within a tranche, ties and the odd chip, folds forfeiting
the tranches paid into, a preflop all-in with no board ranked on two cards.
"""
from __future__ import annotations

import pytest

from hyperion.core.eval import evaluate_short
from hyperion.core.types import Action, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim.engine import HandState, Table, Variant

TRANCHE = Rules(extras={"variant": "tranche_holdem", "settle": "street", "no_runout": True})


def c(s):
    return parse_cards(s)


# ----------------------------------------------------------------------------------------------- two-card hands

def test_two_card_ranking_pair_over_non_pair_then_high_then_kicker_suits_never_count():
    e = lambda s: evaluate_short(c(s))
    assert e("2c 2d") > e("As Ks")  # any pair over any non-pair (README: 2-2 beats A-K)
    assert e("3c 3d") > e("2h 2s")  # a higher pair over a lower one
    assert e("Ac 2d") > e("Ks Qh")  # the high card first (README: A-2 beats K-Q)
    assert e("Ac Kd") > e("As Qs")  # then the kicker
    assert e("Ac Kd") == e("As Ks")  # suits never count: A-K suited and offsuit are equal
    assert e("Kd Ac") == e("Ac Kd")  # order never counts
    assert e("7s 2c") < e("7d 3c") < e("8c 2d")
    assert max(e(x) for x in ("Ac Kd", "Qs Qh", "2c 2s")) == e("Qs Qh")
    # fewer than five cards of any size: trips over two pair over a pair
    assert evaluate_short(c("5c 5d 5h 2s")) > evaluate_short(c("Ac Ad Kc Kd")) > evaluate_short(c("Ac Ad Kc Qd"))


# ----------------------------------------------------------------------------------------------- the settlement alone

def _settle(holes, boards, paid, in_hand=None, button=0, rules=TRANCHE):
    """Each seat's chips back from the engine's award: `paid[t][s]` chips seat s put into street t's round, `boards[t]`
    the board that round was bet on (the hand's board is the last)."""
    n = len(holes)
    t = Table.__new__(Table)
    t.n, t.rules, t.variant = n, rules, Variant()
    t.by_street = (rules.extras or {}).get("settle") == "street"
    t.no_runout = bool((rules.extras or {}).get("no_runout"))
    hs = HandState()
    hs.hand_no, hs.button, hs.history, hs.showdown, hs.extras, hs.dead = 0, button, [], {}, {}, None
    hs.holes = [c(h) for h in holes]
    hs.boards = [c(b) for b in boards]
    hs.board = hs.boards[-1]
    hs.in_hand = list(in_hand) if in_hand is not None else [True] * n
    hs.n_in_hand = sum(hs.in_hand)
    cum = [0] * n
    marks = []
    for t_, row in enumerate(paid):
        if t_:
            marks.append(cum[:])
        cum = [cum[s] + row[s] for s in range(n)]
    hs.marks, hs.contrib = marks, cum
    t.stacks = [0] * n
    t._award(hs)
    return t.stacks, hs


def test_the_handouts_worked_example():
    # heads-up, 2c2d against AhKh: raise to 100 and called (tranche 0 = 200), flop Kd 7s 3c bet 50 called (100), turn
    # 9h checked through (0), river Qh bet 100 called (200)
    got, hs = _settle(["2c 2d", "Ah Kh"], ["", "Kd 7s 3c", "Kd 7s 3c 9h", "Kd 7s 3c 9h Qh"],
                      [[100, 100], [50, 50], [0, 0], [100, 100]])
    assert got == [200, 300]  # our twos take tranche 0; their kings tranches 1 and 3
    assert hs.awards == [[200, 0], [0, 100], [0, 0], [0, 200]]
    # the same money all-in preflop: no board, the twos win everything
    got, _ = _settle(["2c 2d", "Ah Kh"], [""], [[2000, 2000]])
    assert got == [4000, 0]


def test_side_pots_inside_a_tranche_and_an_all_in_seat_has_no_stake_later():
    # three seats. Preflop 20 each (60). Flop: A bets 500, B calls all-in for 280, C calls 500: layer 280 x 3 = 840 for
    # A, B, C; layer 220 x 2 = 440 for A and C. Turn: A bets 200, C calls (400, A and C). River checked through.
    holes = ["Ad Kd", "7c 7h", "Qs Jd"]  # A, B, C
    boards = ["", "7d 2s 3h", "7d 2s 3h Qc", "7d 2s 3h Qc 4s"]
    paid = [[20, 20, 20], [500, 280, 500], [200, 0, 200], [0, 0, 0]]
    got, hs = _settle(holes, boards, paid)
    # preflop B's pair of sevens beats both unpaired hands: B 60. Flop: B's set takes the 840 layer, then A's ace high
    # beats C's queen high for the 440 layer. Turn: C's pair of queens beats A's ace high (B is not eligible): C 400.
    assert hs.awards[0] == [0, 60, 0]
    assert hs.awards[1] == [440, 840, 0]
    assert hs.awards[2] == [0, 0, 400]
    assert got == [440, 900, 400] and sum(got) == sum(map(sum, paid))


def test_ties_split_and_the_odd_chip_goes_clockwise_from_the_button():
    # A-K suited and offsuit tie on two cards; 25 + 25 + 15 folded = 65: 32 each and the odd chip to the first tied
    # seat clockwise from the button (button seat 1: seat 2 first, then 0)
    got, _ = _settle(["Ac Kc", "9d 8d", "As Kd"], [""], [[25, 15, 25]], in_hand=[True, False, True], button=1)
    assert got == [32, 0, 33]
    got, _ = _settle(["Ac Kc", "9d 8d", "As Kd"], [""], [[25, 15, 25]], in_hand=[True, False, True], button=2)
    assert got == [33, 0, 32]
    # each tranche to its own street's winner: A-2 over K-3 preflop, the aces on the flop, their straight on the river
    got, hs = _settle(["Ac 2d", "Kc 3h"], ["", "Ah Td 9s", "Ah Td 9s Js", "Ah Td 9s Js Qc"],
                      [[20, 20], [40, 40], [0, 0], [100, 100]])
    assert hs.awards == [[40, 0], [80, 0], [0, 0], [0, 200]]  # river: their king makes K-Q-J-T-9
    # a tie on the river board: both play the board's straight, the river tranche splits, the flop tranche does not
    got, hs = _settle(["Ac 2d", "Kc 3h"], ["", "4c 5d 6s", "4c 5d 6s 7h", "4c 5d 6s 7h 8c"],
                      [[20, 20], [40, 40], [0, 0], [100, 100]])
    assert hs.awards[1] == [80, 0] and hs.awards[3] == [100, 100]


def test_folded_chips_are_dead_money_and_a_layer_nobody_still_in_reached_joins_the_one_below():
    # seat 1 folded after putting 300 into the flop round; the contenders put in 100 and 200. Layers: 100 x 3 for both
    # contenders; 100 (seat 1) + 100 (seat 2) for seat 2 alone; seat 1's last 100 has no contender at its level: it
    # joins the layer below, seat 2's.
    got, hs = _settle(["Ah Ad", "Kc Kd", "Qh Qd"], ["", "2c 7d 9s"], [[20, 20, 20], [100, 300, 200]],
                      in_hand=[True, False, True])
    assert hs.awards[0] == [60, 0, 0]
    assert hs.awards[1] == [300, 0, 300]  # aces win the first layer; queens are alone in the rest
    assert sum(got) == 660


def test_a_fold_forfeits_every_tranche_paid_into():
    # through the engine: the worked example with the river bet folded. The other seat takes all 400, our preflop
    # tranche included (we paid 150).
    t, _obs = _play(["2c 2d", "Ah Kh"], "Kd 7s 3c 9h Qh",
                    {0: [("r", 100), ("c",), ("k",), ("f",)], 1: [("c",), ("r", 50), ("k",), ("r", 100)]})
    assert t.stacks == [1850, 2150]


# ----------------------------------------------------------------------------------------------- the engine end to end

class _Rig(Variant):
    def __init__(self, holes, board):
        self.h, self.b = [c(x) for x in holes], list(c(board))

    def on_deal(self, hand, rng):
        hand.holes = list(self.h)
        hand.runout = list(self.b)
        hand.board = ()


class _Script:
    def __init__(self, moves):
        self.moves, self.seen = list(moves), []

    def new_table(self, rules, seat, n):
        pass

    def act(self, obs):
        self.seen.append(obs)
        m = self.moves.pop(0)
        if m[0] == "r":
            return Action.raise_to(m[1])
        return {"c": Action.call(), "k": Action.check(), "f": Action.fold()}[m[0]]

    def hand_end(self, result):
        self.result = result


def _play(holes, board, script, rules=TRANCHE, stacks=None):
    bots = [_Script(script[s]) for s in range(len(holes))]
    t = Table(bots, rules, seed=1, variant=_Rig(holes, board), stacks=stacks)
    t.play_hand()
    return t, bots


def test_the_worked_example_through_the_engine_with_the_tranches_in_the_observation():
    # heads-up: seat 0 is the button and the small blind, acts first preflop and last after
    t, bots = _play(["2c 2d", "Ah Kh"], "Kd 7s 3c 9h Qh",
                    {0: [("r", 100), ("c",), ("k",), ("c",)], 1: [("c",), ("r", 50), ("k",), ("r", 100)]})
    assert t.stacks == [1950, 2050]  # we put in 250 and get 200 back
    seen = bots[0].seen
    assert [o.extras["tranches"] for o in seen] == [(), (200,), (200, 100), (200, 100, 0)]
    r = bots[0].result
    assert r.extras["tranches"] == (200, 100, 0, 200)
    assert r.extras["awards"] == ((200, 0), (0, 100), (0, 0), (0, 200))


def test_no_runout_a_preflop_all_in_deals_no_board():
    t, bots = _play(["2c 2d", "Ah Kh"], "Kd 7s 3c 9h Qh", {0: [("r", 2000)], 1: [("c",)]})
    assert t.stacks == [4000, 0]
    assert bots[0].result.board == () and bots[0].result.showdown


def test_no_runout_stops_after_the_round_that_ends_the_betting():
    # all-in on the flop: the turn and river never come; the flop tranche is judged on the flop
    t, bots = _play(["Qc Qd", "Ah 5h"], "Qs 7h 3h 9h Ah",
                    {0: [("r", 60), ("r", 1940)], 1: [("c",), ("k",), ("c",)]})
    assert bots[0].result.board == c("Qs 7h 3h")  # the flush and the ace never came
    assert t.stacks == [4000, 0]


def test_no_runout_alone_settles_hold_em_on_the_cards_out():
    # one pot as in hold'em, but a preflop all-in is two cards against two: 2-2 beats A-K with no board
    rules = Rules(extras={"no_runout": True})
    t, bots = _play(["2c 2d", "Ah Kh"], "Kd Ks Kc 9h Qh", {0: [("r", 2000)], 1: [("c",)]}, rules=rules)
    assert t.stacks == [4000, 0] and bots[0].result.board == ()
    # with a runout (the default) the same all-in goes to the kings on the board
    t, _ = _play(["2c 2d", "Ah Kh"], "Kd Ks Kc 9h Qh", {0: [("r", 2000)], 1: [("c",)]}, rules=Rules())
    assert t.stacks == [0, 4000]


def test_settle_by_street_alone_still_deals_the_runout():
    # street settlement without no_runout: the board runs out after a preflop all-in, but only tranche 0 has chips, so
    # the two-card hands decide it all
    rules = Rules(extras={"settle": "street"})
    t, bots = _play(["2c 2d", "Ah Kh"], "Kd Ks Kc 9h Qh", {0: [("r", 2000)], 1: [("c",)]}, rules=rules)
    assert len(bots[0].result.board) == 5 and t.stacks == [4000, 0]


def test_an_unknown_settle_rule_fails_at_the_table():
    with pytest.raises(ValueError):
        Table([_Script([]), _Script([])], Rules(extras={"settle": "pot"}))


def test_the_catalog_entry():
    v = V.get("tranche_holdem")
    assert v.name in V.catalog_names() and v.axis == "payoff" and not V.validate(v)
    assert v.rules.extras["settle"] == "street" and v.rules.extras["no_runout"] is True
    assert v.rules.payouts == Rules().payouts and v.hooks is None  # the catalog's default points, no hooks


def test_several_hundred_tables_play_clean_and_keep_every_chip():
    from hyperion.sim import bestiary as B

    v = V.get("tranche_holdem")
    names = ["tag", "loose_aggro", "pushfold", "maniac", "nit", "random", "montecarlo30", "tag"]
    hands = shown = bare = 0
    for seed in range(200):
        bots = [B.make_bot(nm, seed=seed * 8 + i) for i, nm in enumerate(names)]
        t = Table(bots, v.rules, seed=seed, mode="model", variant=v.new_hooks())
        while not t.done:
            hs = t.play_hand()
            hands += 1
            assert sum(t.stacks) == 8 * v.rules.starting_stack
            shown += bool(hs.showdown)
            bare += bool(hs.showdown) and not hs.board
        assert all(st.exceptions == 0 and st.illegal == 0 for st in t.stats)
    assert hands > 10000 and shown > 500 and bare > 100
