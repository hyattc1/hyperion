"""river_of_blood (MIT 2023): a red river deals another card and betting round until a black card. Held out until drill 7
(hyperion/drills/variants_unseen.py), promoted to the catalog 2026-11-02: the engine's run streets, the spec's numbers,
the any-size evaluator (core.eval.evaluate_many) and the bots' evaluator guard."""
import random

import pytest

from hyperion.core.eval import evaluate, evaluate_many, evaluate_slow
from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.drills import variants_unseen as U
from hyperion.sim.bestiary import ChartTAG, RandomBot
from hyperion.sim.engine import Table

P = parse_cards
RAISE = ActionKind.RAISE


@pytest.fixture(autouse=True)
def _no_guard_leak():
    """RiverOfBloodHooks() installs a process-wide guard on core.eval; take it off after every test."""
    yield
    V.remove_eval_guard()


class Bot:
    """Plays a script, then checks or calls; records observations and results."""

    def __init__(self, actions=()):
        self.actions = list(actions)
        self.obs, self.results = [], []

    def new_table(self, rules, seat, n):
        self.seat = seat

    def act(self, obs):
        self.obs.append(obs)
        if self.actions:
            return self.actions.pop(0)
        return Action.check() if ActionKind.CHECK in obs.legal else Action.call()

    def hand_end(self, result):
        self.results.append(result)


def rules_n(n, **kw):
    return Rules(n_players=n, payouts=tuple(range(n, 0, -1)), **kw)


def test_river_of_blood_is_in_the_catalog_and_no_longer_held_out():
    assert "river_of_blood" in V.catalog_names() and "river_of_blood" not in U.names()
    v = V.get("river_of_blood")
    assert v.name == "river_of_blood" and v.axis == "betting" and V.validate(v) == []
    assert v.rules.extras["run_until_black"] and v.config_patch == {}
    # the old import paths still resolve to the same objects
    assert U.RiverOfBloodHooks is V.RiverOfBloodHooks and U.evaluate_many is evaluate_many
    assert U.install_eval_guard is V.install_eval_guard


def test_river_of_blood_keeps_the_rules_and_conserves_chips():
    v = V.get("river_of_blood")
    total = v.rules.starting_stack * v.rules.n_players
    long_boards = 0
    for seed in range(4):
        bots = [RandomBot(seed * 10 + s) if s % 2 else ChartTAG(seed * 10 + s) for s in range(8)]
        t = Table(bots, v.rules, seed=seed, variant=v.new_hooks())
        while not t.done:
            hs = t.play_hand()
            assert sum(t.stacks) == total and min(t.stacks) >= 0 and sum(hs.deltas) == 0
            long_boards += len(hs.board) > 5
        assert all(st.illegal == 0 for st in t.stats)
    assert long_boards > 0


def test_evaluate_many_never_builds_a_table():
    from hyperion.core import eval as E

    before = set(E._UNSUITED_N)
    rng = random.Random(4)
    for n in range(9, 20):
        evaluate_many(rng.sample(range(52), n))
    assert set(E._UNSUITED_N) == before

def test_evaluate_many_matches_brute_force_on_any_number_of_cards():
    rng = random.Random(11)
    for n in list(range(5, 9)) * 50 + list(range(9, 15)) * 150:
        cards = rng.sample(range(52), n)
        assert evaluate_many(cards) == evaluate_slow(cards), cards
    # every category is reached past 8 cards, straight flushes and wheels included
    assert evaluate_many(P("Ah 2h 3h 4h 5h Kc Kd Ks 9c")) == evaluate_slow(P("Ah 2h 3h 4h 5h Kc Kd Ks 9c"))
    assert evaluate_many(P("As 2d 3c 4h 5s 9c 9d Jh Qc")) == evaluate_slow(P("As 2d 3c 4h 5s 9c 9d Jh Qc"))
    assert evaluate_many(P("7c 7d 7h 7s 2c 2d 2h 3c 3d 4c")) == evaluate_slow(P("7c 7d 7h 7s 2c 2d 2h 3c 3d 4c"))


def test_eval_guard_makes_the_bots_nine_card_evaluation_fail_and_comes_off():
    cards = P("Ah Kd 7c 7d 2s 3h 9c Jd Qs")
    V.RiverOfBloodHooks()
    assert V.eval_guard_on()
    assert evaluate(cards[:8]) == evaluate_slow(cards[:8])
    with pytest.raises(V.EvaluatorLimit):
        evaluate(cards)
    V.remove_eval_guard()
    assert not V.eval_guard_on()
    V.RiverOfBloodHooks(guard_bot_eval=False)
    assert not V.eval_guard_on()


class RobRig(V.RiverOfBloodHooks):
    """Fixed holes, a fixed five-card board and a fixed run (dealt in order while the last card is red)."""

    def __init__(self, holes, board, run):
        super().__init__(guard_bot_eval=False)
        self.holes, self.board, self.run = [P(h) for h in holes], list(P(board)), list(P(run))

    def on_deal(self, holes, deck, rng):
        deck[:] = self.run[::-1]
        return [self.holes[s] if holes[s] else () for s in range(len(holes))]

    def on_street(self, street, board, holes, deck, rng, ask=None):
        return tuple(self.board[: len(board)]), holes


def test_a_red_river_deals_run_streets_each_with_a_betting_round_and_the_whole_board_plays():
    # seat 0's flush needs the run's Qh; without it seat 1's trip kings win
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qh 8c 2c")
    bots = [Bot(), Bot()]
    t = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig)
    hs = t.play_hand()
    assert hs.board == P("Kc 7d 3s 9h 4h Qh 8c")  # stops at the black 8c; 2c is never dealt
    assert rig.run_cards == 2
    streets = sorted({o.street for o in bots[1].obs})
    assert streets == [0, 1, 2, 3, 4, 5]
    run_obs = [o for o in bots[1].obs if o.street >= 4]
    assert all(len(o.board) == o.street + 2 and o.bets == [0, 0] and o.min_raise == 20 for o in run_obs)
    assert all(o.seat == 1 for o in run_obs)  # first to act on a run street: the first live seat left of the button
    assert hs.deltas == [20, -20]  # the flush made on street 4 wins


def test_a_black_river_ends_the_board_and_a_fold_stops_the_run():
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4c", "Qh 8c")
    t = Table([Bot(), Bot()], rules_n(2, max_hands=1), seed=0, variant=rig)
    assert len(t.play_hand().board) == 5 and rig.run_cards == 0
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qh 8c")
    bots = [Bot([Action.call(), Action.check(), Action.check(), Action.fold()]),
            Bot([Action.check(), Action.check(), Action.check(), Action.raise_to(40)])]
    hs = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig).play_hand()
    assert len(hs.board) == 5 and rig.run_cards == 0 and hs.deltas == [-20, 20]


def test_all_in_deals_the_whole_run_without_betting():
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qd 2h 8s")  # the run's 2h makes seat 0's flush
    bots = [Bot([Action.raise_to(2000)]), Bot([Action.call()])]
    hs = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig).play_hand()
    assert hs.board == P("Kc 7d 3s 9h 4h Qd 2h 8s") and len(bots[0].obs) == 1 and len(bots[1].obs) == 1
    assert hs.deltas == [2000, -2000]


def test_extra_street_rate_and_board_length_match_the_spec():
    """Spec: P(extra) ~ 0.48-0.52, E[board] ~ 5.9-6.0, a run adds ~1.9 cards. Every hand here reaches the river."""
    lengths = []
    for seed in range(12):
        bots = [Bot() for _ in range(8)]
        t = Table(bots, V.river_of_blood().rules, seed=seed, variant=V.RiverOfBloodHooks(guard_bot_eval=False),
                  stacks=[10 ** 9] * 8)
        while not t.done:
            lengths.append(len(t.play_hand().board))
    n = len(lengths)
    assert n == 12 * 200
    p_extra = sum(1 for x in lengths if x > 5) / n
    mean_len = sum(lengths) / n
    run = [x - 5 for x in lengths if x > 5]
    assert 0.45 < p_extra < 0.55, p_extra
    assert 5.8 < mean_len < 6.1, mean_len
    assert 1.75 < sum(run) / len(run) < 2.1, sum(run) / len(run)


def _completion(hero, suit, trials=8000, seed=5):
    """Spec setup: hero's two suited cards against 7 opponents, a board with exactly two of hero's suit and a red
    river, then the run as the hook deals it. P(five of the suit by the end of the run)."""
    rng = random.Random(seed)
    hook = V.RiverOfBloodHooks(guard_bot_eval=False)
    rest = [c for c in range(52) if c not in hero]
    hits = tot = 0
    while tot < trials:
        d = rest[:]
        rng.shuffle(d)
        board = d[14:19]
        if board[4] & 3 not in V.RED_SUITS or sum(1 for c in board if c & 3 == suit) != 2:
            continue
        tot += 1
        spare = d[19:]
        hook.on_deal([], spare, rng)
        b = tuple(board)
        while (c := hook.next_card(4, b, spare, rng)) is not None:
            b += (c,)
        hits += sum(1 for c in tuple(hero) + b if c & 3 == suit) >= 5
    return hits / tot


def test_flush_draws_on_a_red_river_complete_at_the_spec_rates():
    assert abs(_completion(P("As Ks"), 3) - 0.42) < 0.025  # spade draw: the final run card is black
    assert abs(_completion(P("Ah Kh"), 2) - 0.27) < 0.025  # heart draw


def test_duplicate_rotations_see_the_same_run():
    boards = []
    for rot in (0, 3):
        t = Table([Bot() for _ in range(8)], V.river_of_blood().rules, seed=4, rotation=rot,
                  variant=V.RiverOfBloodHooks(guard_bot_eval=False), stacks=[10 ** 9] * 8)
        boards.append([t.play_hand().board for _ in range(40)])
    assert boards[0] == boards[1] and any(len(b) > 6 for b in boards[0])


# ----- Hero's long-board read (Config long_board) ------------------------------------------------------------------


def _obs(hole, board, to_call=0):
    from hyperion.core.types import Observation

    b = P(board)
    bets = [0] * 8
    if to_call:
        bets[1] = to_call
    legal = {ActionKind.FOLD, ActionKind.CALL, RAISE} if to_call else {ActionKind.CHECK, RAISE, ActionKind.FOLD}
    return Observation(hole=P(hole), board=b, street=len(b) - 2, seat=0, button=1,
                       stacks=[1500, 1500 - to_call] + [1500] * 6, bets=bets, in_hand=[True, True] + [False] * 6,
                       pot=200, to_call=to_call, min_raise=max(20, 2 * to_call), max_raise=1500, legal=frozenset(legal),
                       hand_no=3, blinds=(10, 20), history=[(1, Action.raise_to(to_call))] if to_call else [],
                       extras={})


def _hero(**dials):
    from hyperion.strategy.hero import HeroCore, config_from_dict

    h = HeroCore(config_from_dict({"use_profiler": False, **dials}, seed=1))
    h.new_table(V.river_of_blood().rules, 0, 8)
    return h


def test_hero_folds_a_flush_past_eight_cards_without_the_dial_and_raises_it_with():
    from hyperion.core import eval as E

    # the unseen log's probe: Ah Jh on Kc 7d 3s 9h 4h Qh 8c facing a bet
    o = _obs("Ah Jh", "Kc 7d 3s 9h 4h Qh 8c", to_call=100)
    off = _hero()
    assert off.act(o).kind is ActionKind.FOLD and off.last_path == "safe"
    on = _hero(long_board=True)
    assert on.act(o).kind is RAISE and on.last_path == "postflop.long"
    # twelve board cards: still read, and no evaluator table past 8 cards is built inside the decision
    assert on.act(_obs("Ah Jh", "Kc 7d 3s 9h 4h Qh 8c 2d 5c Td 6s", to_call=100)).kind is RAISE
    assert max(E._UNSUITED_N) <= 8


def test_long_read_plays_the_board_and_counts_draws_while_a_card_can_come():
    from hyperion.strategy.postflop import Postflop

    # the board's own straight on seven cards: playing the board
    tier, _, _ = Postflop.read(P("2c 2d"), P("5h 6s 7c 8d 9s Kh Kc"), long=True)
    assert tier <= 2
    # a heart draw on a red river: outs count only when another card can come
    _, outs_last, _ = Postflop.read(P("Ah Jh"), P("Kc 7h 3s 9h 4d"), long=True, more=False)
    _, outs_more, _ = Postflop.read(P("Ah Jh"), P("Kc 7h 3s 9h 4d"), long=True, more=True)
    assert outs_last == 0 and outs_more >= 9


def test_a_red_last_card_plays_as_a_turn_and_a_black_one_as_the_river():
    h = _hero(long_board=True, long_to_come=1)
    seen = []
    orig = h.postflop.act

    def spy(*a, **kw):
        seen.append((kw.get("street"), kw.get("to_come"), kw.get("more")))
        return orig(*a, **kw)

    h.postflop.act = spy
    h.act(_obs("Ah Jh", "Kc 7h 3s 9h 4d"))  # a red river: another card comes
    h.act(_obs("Ah Jh", "Kc 7h 3s 9h 4d 8c"))  # black: the last street
    assert seen == [(2, 1, True), (3, 0, False)]


def test_long_board_dials_change_nothing_on_plain_holdem_boards():
    from hyperion.core.types import Rules
    from hyperion.strategy.hero import HeroCore, config_from_dict

    for hole, board, to_call in (("Ah Jh", "Kc 7h 3s 9h 4d", 100), ("Qs Qd", "Kc 7h 3s", 0), ("9c 8c", "Tc 7h 2s 3c", 60)):
        acts = []
        for dials in ({}, {"long_board": True, "long_value_per_card": 2, "long_call_per_card": 2}):
            h = HeroCore(config_from_dict({"use_profiler": False, **dials}, seed=1))
            h.new_table(Rules(), 0, 8)
            acts.append(h.act(_obs(hole, board, to_call)))
        assert acts[0] == acts[1]


def test_hybrid_routes_long_boards_to_hero_only_with_its_dial():
    from hyperion.hybrid import HybridCore, hybrid_config

    for on in (False, True):
        hc = HybridCore(hybrid_config({"core": "rival3", "hero_on_long_board": on, "hero.long_board": True}))
        hc.new_table(V.river_of_blood().rules, 0, 8)
        hc.act(_obs("Ah Jh", "Kc 7d 3s 9h 4h Qh 8c", to_call=100))
        assert (hc.counts.get("hero:long_board", 0) == 1) == on
