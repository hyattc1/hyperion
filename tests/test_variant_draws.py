"""Where a hook's extra cards come from, and where every chip goes.

1. The deal shuffles only the slots it deals (a partial Fisher-Yates), so the undealt tail is in near-deck order. Hooks
   that pop extra cards from it (swap_holdem, swap_one_turn, two_boards, bonus_card) drew the ace of spades as their
   first extra card in 60% of seeds on hand 0. The engine now shuffles the undealt cards before the hooks see them
   (Table.srng), so every extra card is uniform over the cards nobody holds, and never one that was dealt.
2. The pot award paid side pots by the contenders' levels only: whatever a folded player put in above every
   contender was lost. No default hand reaches it (the top contributor never faces a bet, so never folds); a variant
   that hands chips back does. That excess now goes into the top pot.
"""
from collections import Counter

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim.engine import Table, Variant
from tests.sim_helpers import Scripted

CHECK = ActionKind.CHECK
DRAWING = ("swap_holdem", "swap_one_turn", "two_boards", "bonus_card")


class CheckCall:
    def new_table(self, rules, seat, n):
        pass

    def act(self, obs):
        return Action.check() if CHECK in obs.legal else Action.call()

    def hand_end(self, result):
        pass


def _recording(hooks, out):
    """The hooks with every card popped from the deck recorded per street, in pop order."""
    inner = hooks.on_street

    def on_street(street, board, holes, deck, rng, ask=None):
        before = list(deck)
        res = inner(street, board, holes, deck, rng, ask)
        k = len(before) - len(deck)
        assert before[: len(deck)] == deck  # hooks only pop from the end
        out.extend(reversed(before[len(deck):]) if k else ())
        return res

    hooks.on_street = on_street
    return hooks


def _draws(name: str, seeds: range, hands: int = 1):
    """(first extra card per hand, every extra card, collisions with a card already dealt or drawn this hand)."""
    firsts, every, bad = Counter(), Counter(), 0
    for seed in seeds:
        v = V.get(name)
        out: list = []
        t = Table([CheckCall() for _ in range(8)], v.rules, seed=seed, variant=_recording(v.new_hooks(), out))
        for _ in range(hands):
            n0 = len(out)
            t.play_hand()
            dealt = set(t.deck[: t.cards_per_hand])  # every hole slot and the whole runout of this hand
            got = out[n0:]
            bad += sum(1 for c in got if c in dealt) + len(got) - len(set(got))
            if got:
                firsts[got[0]] += 1
            every.update(got)
    return firsts, every, bad


def _chi2(counts: Counter) -> float:
    n = sum(counts.values())
    exp = n / 52
    return sum((counts.get(c, 0) - exp) ** 2 / exp for c in range(52))


@pytest.mark.parametrize("name", DRAWING)
def test_extra_cards_are_uniform_over_the_undealt_cards_and_never_collide(name):
    firsts, every, bad = _draws(name, range(1500))
    n = sum(firsts.values())
    assert n > 1200, n  # swap_holdem draws on ~92% of hands
    # before the fix: the ace of spades (51) was 60% of first draws, chi-square ~34,000 on 51 degrees of freedom
    assert max(firsts.values()) / n < 0.04, firsts.most_common(3)
    assert _chi2(firsts) < 100, _chi2(firsts)  # p ~ 5e-5 under uniform; the seeds are fixed, so this is exact
    assert _chi2(every) < 100, _chi2(every)
    assert bad == 0


def test_later_hands_draw_uniformly_too():
    firsts, every, bad = _draws("two_boards", range(200), hands=15)
    assert bad == 0
    assert max(firsts.values()) / sum(firsts.values()) < 0.04 and _chi2(every) < 100


def test_the_spare_deck_is_the_undealt_cards_shuffled_and_rotation_independent():
    seen = []
    for rot in (0, 3):
        hooks = V.TwoBoardsHooks()
        t = Table([CheckCall() for _ in range(8)], V.two_boards().rules, seed=11, rotation=rot, variant=hooks)
        boards = []
        for _ in range(6):
            hs = t.play_hand()
            undealt = sorted(t.deck[t.cards_per_hand:])
            assert sorted(hs.spare + list(hooks.board2)) == undealt
            boards.append(hooks.board2)
        seen.append(boards)
    assert seen[0] == seen[1]  # duplicate dealing: a rotation relabels seats, the second board is the same


def test_default_play_draws_nothing_from_the_spare_rng():
    t = Table([CheckCall() for _ in range(8)], Rules(), seed=2)
    state = t.srng.getstate()
    for _ in range(5):
        t.play_hand()
    assert t.srng.getstate() == state


# ----- chips --------------------------------------------------------------------------------------


class Rebate(Variant):
    """On the flop every player still in gets back all but `keep` of what they put in: a variant that hands chips
    back. Folded players get nothing back, so one of them can have put in more than anyone still in the hand.
    Fixed cards, as tests/test_sim_engine.py's Rig deals them."""

    def __init__(self, keep: int, holes, board):
        self.keep = keep
        self.holes = [parse_cards(h) for h in holes]
        self.board = list(parse_cards(board))
        self.stacks = None  # the table's stacks, set once the table exists

    def on_deal(self, hand, rng):
        for s, h in enumerate(self.holes):
            hand.holes[s] = h
        hand.runout[:] = self.board
        hand.board = tuple(hand.runout[: len(hand.board)])

    def on_street(self, hand, street, rng):
        if street != 1:
            return
        for s in range(len(hand.contrib)):
            if hand.in_hand[s] and hand.contrib[s] > self.keep:
                back = hand.contrib[s] - self.keep
                hand.contrib[s] -= back
                hand.pot -= back
                self.stacks[s] += back


def test_a_folded_players_excess_goes_to_the_top_pot():
    # four seats, button 0, sb 1, bb 2, utg 3. utg raises to 200, the button re-raises to 600, sb and bb call,
    # utg folds with 200 in. On the flop the three still in get back all but 50: utg's 200 is above all of them.
    bots = [Scripted([Action.raise_to(600)]), Scripted([Action.call()]), Scripted([Action.call()]),
            Scripted([Action.raise_to(200), Action.fold()])]
    rig = Rebate(50, ["2c3d", "KsKh", "7c8d", "AsAh"], "Kd 9s 4c 5h Jd")  # the sb's kings win
    t = Table(bots, Rules(n_players=4, payouts=(4, 3, 2, 1)), seed=0, variant=rig)
    rig.stacks = t.stacks
    total = sum(t.stacks)
    hs = t.play_hand()
    assert hs.contrib == [50, 50, 50, 200]
    assert sum(t.stacks) == total and sum(hs.deltas) == 0  # before the fix: 150 chips vanished
    # the main pot 4 x 50 = 200 and utg's 150 above every contender: all to the sb's kings
    assert hs.deltas == [-50, 300, -50, -200]


def test_default_play_never_has_a_folded_player_above_every_contender():
    """The excess rule is unreachable without a variant: over random play nothing moves into the top pot."""
    from hyperion.sim.bestiary import RandomBot

    hits = 0
    orig = Table._award

    def award(self, hs):
        nonlocal hits
        top = max(hs.contrib[s] for s in range(self.n) if hs.in_hand[s])
        hits += any(c > top for c in hs.contrib)
        orig(self, hs)

    Table._award = award
    try:
        for seed in range(30):
            t = Table([RandomBot(seed * 8 + s) for s in range(8)], Rules(ante=5, ante_from_level=1), seed=seed)
            total = sum(t.stacks)
            while not t.done:
                t.play_hand()
                assert sum(t.stacks) == total
    finally:
        Table._award = orig
    assert hits == 0
