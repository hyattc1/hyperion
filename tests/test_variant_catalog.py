"""Antes, pot-limit and fixed-limit legality, straddle, must-use showdown, split pots, the hooks
bridge (ask / variant_decide, payout, bust, extras, charges), and the catalog itself."""
import dataclasses
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim.bestiary import ChartTAG, RandomBot
from hyperion.sim.engine import Table, evaluate_must_use, play_table
from tests.sim_helpers import Recorder, Scripted

ROOT = Path(__file__).resolve().parents[1]
FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


class Rig(V.VariantHooks):
    """Deals fixed displayed hole cards and board through the drills contract."""

    def __init__(self, holes, board):
        self.holes = [parse_cards(h) if h else () for h in holes]
        self.board = list(parse_cards(board))

    def on_deal(self, holes, deck, rng):
        return [self.holes[s] if holes[s] else () for s in range(len(holes))]

    def on_street(self, street, board, holes, deck, rng, ask=None):
        return tuple(self.board[: len(board)]), holes


class Observer:
    """Checks the invariants that hold under every betting structure and keeps observations."""

    def __init__(self, inner, total):
        self.inner, self.total, self.obs = inner, total, []

    def new_table(self, rules, seat, n):
        self.rules = rules
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        assert sum(obs.stacks) + sum(obs.bets) + obs.pot == self.total
        assert 0 <= obs.to_call <= obs.stacks[obs.seat]
        assert obs.max_raise <= obs.stacks[obs.seat] + obs.bets[obs.seat]
        if RAISE in obs.legal:
            assert max(obs.bets) < obs.min_raise <= obs.max_raise
            if self.rules.betting == "potlimit":
                assert obs.max_raise <= V.pot_limit_max_raise(obs)
            if self.rules.betting == "fixedlimit":
                inc = obs.big_blind * (2 if obs.street >= 2 else 1)
                assert obs.max_raise <= max(obs.bets) + inc
                assert obs.min_raise == obs.max_raise
        self.obs.append(obs)
        a = self.inner.act(obs)
        assert a.kind in obs.legal and (a.kind is not RAISE or obs.min_raise <= a.amount <= obs.max_raise)
        return a

    def hand_end(self, result):
        self.inner.hand_end(result)


def fuzz(rules, seeds=range(6), variant=None, hooks=None):
    total = rules.starting_stack * rules.n_players
    observers = []
    for seed in seeds:
        bots = [Observer(RandomBot(seed * 10 + s), total) for s in range(rules.n_players)]
        v = hooks() if hooks else variant
        t = Table(bots, rules, seed=seed, variant=v)
        while not t.done:
            hs = t.play_hand()
            assert sum(t.stacks) == total and min(t.stacks) >= 0
            assert sum(hs.deltas) == 0
        observers.extend(bots)
    return observers


# ----- antes -----------------------------------------------------------------------------------


def test_antes_go_to_the_pot_from_their_level_and_chips_are_conserved():
    fuzz(Rules(ante=5, ante_from_level=0), seeds=range(4))  # conservation under random play
    rules = Rules(ante=5, ante_from_level=2, hands_per_level=5, max_hands=30)
    bots = [Recorder() for _ in range(8)]
    play_table(bots, rules, seed=1)
    first_pre = {}
    for b in bots:
        for o in b.obs:
            if o.street == 0 and o.hand_no not in first_pre:
                first_pre[o.hand_no] = o
    assert all(o.pot == 0 for h, o in first_pre.items() if h < 10)
    late = [o for h, o in first_pre.items() if h >= 10]
    assert late and all(o.pot == 5 * 8 for o in late)  # eight antes in the pot, none in bets
    assert all(sum(o.bets) == sum(o.blinds) for o in late if len(o.history) == 0)


def test_ante_schedule_and_short_stack_all_in_for_the_ante():
    rules = Rules(n_players=3, payouts=(3, 2, 1), ante_per_level=(0, 7), ante_from_level=1, hands_per_level=1,
                  blind_levels=((10, 20), (10, 20)))
    assert rules.ante_at(0) == 0 and rules.ante_at(1) == 7 and rules.ante_at(9) == 7
    bots = [Scripted([]), Scripted([]), Scripted([])]
    t = Table(bots, rules, seed=0, stacks=[3, 500, 500])
    t.play_hand()  # level 0: no ante
    assert sum(t.stacks) == 1003
    hs = t.play_hand()  # level 1: seat 0 can only post 3
    assert hs.ante == 7 and hs.contrib[0] <= 3 and sum(t.stacks) == 1003
    assert all(st.illegal == 0 for st in t.stats)


# ----- pot limit / fixed limit / straddle -------------------------------------------------------


def test_pot_limit_caps_every_raise_and_conserves_chips():
    bots = fuzz(Rules(betting="potlimit"))
    raises = [o for b in bots for o in b.obs if RAISE in o.legal]
    assert raises
    # preflop UTG: current 20, pot after call 50 -> cap 70; the big blind is never reachable all-in in one move
    utg = [o for o in raises if o.street == 0 and o.pot == 0 and sum(o.bets) == 30 and o.to_call == 20]
    assert utg and all(o.max_raise == min(70, o.stacks[o.seat] + o.bets[o.seat]) for o in utg)
    assert any(o.max_raise == 70 for o in utg)


def test_pot_limit_exact_cap_after_a_raise():
    # 3 seats: button 0 raises pot (to 70), sb 1 folds, bb 2 may re-raise to 20 + ... cap
    bots = [Scripted([Action.raise_to(70)]), Scripted([Action.fold()]), Scripted([Action.call()])]
    t = Table(bots, Rules(n_players=3, payouts=(3, 2, 1), betting="potlimit"), seed=0)
    t.play_hand()
    o = bots[2].obs[0]
    # bb faces 70: pot after call = 10 (sb) + 70 + 70 = 150; cap = 70 + 150 = 220
    assert o.to_call == 50 and o.max_raise == 220 and o.min_raise == 120


def test_fixed_limit_single_raise_size_and_turn_doubles():
    bots = fuzz(Rules(betting="fixedlimit"), seeds=range(4))
    allin = lambda o: o.stacks[o.seat] + o.bets[o.seat]  # noqa: E731
    pre = [o for b in bots for o in b.obs if RAISE in o.legal and o.street == 0]
    assert pre and all(o.max_raise == min(max(o.bets) + o.big_blind, allin(o)) for o in pre)
    assert any(o.max_raise == max(o.bets) + o.big_blind for o in pre)
    turn = [o for b in bots for o in b.obs if RAISE in o.legal and o.street >= 2]
    assert turn and all(o.max_raise == min(max(o.bets) + 2 * o.big_blind, allin(o)) for o in turn)
    assert any(o.max_raise == max(o.bets) + 2 * o.big_blind for o in turn)


def test_straddle_is_posted_live_and_acts_last_preflop():
    rules = Rules(n_players=4, payouts=(4, 3, 2, 1), straddle=2)
    bots = [Recorder() for _ in range(4)]
    t = Table(bots, rules, seed=0)
    hs = t.play_hand()
    # button 0, sb 1, bb 2, straddle 3: first to act preflop is the button
    first = min((o for b in bots for o in b.obs if o.street == 0), key=lambda o: len(o.history))
    assert first.seat == 0 and first.bets == [0, 10, 20, 40] and first.to_call == 40
    assert first.min_raise == 80  # twice the straddle
    assert hs.contrib[3] >= 40 and sum(t.stacks) == 8000
    fuzz(Rules(straddle=2), seeds=range(3))


def test_heads_up_has_no_straddle():
    bots = [Scripted([Action.call()]), Scripted([])]
    t = Table(bots, Rules(n_players=2, payouts=(2, 1), straddle=2), seed=0)
    t.play_hand()
    assert bots[0].obs[0].bets == [10, 20]


def test_unknown_betting_mode_is_rejected():
    with pytest.raises(ValueError):
        Table([Recorder(), Recorder()], Rules(betting="spread"))


# ----- showdown rules ---------------------------------------------------------------------------


def test_must_use_two_is_omaha():
    P = parse_cards
    rules = Rules(hole_cards=4, must_use_hole=2)
    # four hearts on the board, one in hand: not a flush under Omaha
    s_omaha = evaluate_must_use(P("Ah 2c 3d 4s"), P("Kh Qh Jh 9h 2d"), rules, 2)
    s_any = V.VariantHooks().score_hand(P("Ah 2c"), P("Kh Qh Jh 9h 2d"), Rules())
    assert s_omaha < s_any
    bots = [Scripted([Action.raise_to(2000)]), Scripted([Action.call()])]
    rig = Rig(["Ah 2c 3d 4s", "Kc Kd 7s 8s"], "Kh Qh Jh 9h 2d")
    t = Table(bots, Rules(n_players=2, payouts=(2, 1), hole_cards=4, must_use_hole=2), seed=0, variant=rig)
    hs = t.play_hand()
    assert hs.deltas == [-2000, 2000]  # trip kings beat a pair of deuces with one heart


def test_two_boards_split_each_half_by_its_own_board():
    class Boards(V.TwoBoardsHooks):
        def on_deal(self, holes, deck, rng):
            self.board2 = ()
            return [parse_cards("As Ad"), parse_cards("7c 8c")]

        def on_street(self, street, board, holes, deck, rng, ask=None):
            b1 = parse_cards("Ac Kd 2h 3s 9d")
            self.board2 = parse_cards("5c 6c 9c Ts Jd")[: len(board)]
            return b1[: len(board)], holes

    bots = [Scripted([Action.raise_to(2000)]), Scripted([Action.call()])]
    t = Table(bots, Rules(n_players=2, payouts=(2, 1)), seed=0, variant=Boards())
    hs = t.play_hand()
    assert hs.deltas == [0, 0]  # aces take board 1, the flush takes board 2


def test_hi_lo_splits_with_a_qualifying_low_and_scoops_without():
    P = parse_cards
    h = V.HiLoHooks()
    hi, lo = h.score_splits(P("Ad 2d"), P("3c 4h 8s Kd Kc"), Rules())
    assert lo is not None and V.low_score(P("Kd Kc Ad 2d 3c 4h 9s"), Rules()) is None
    assert V.low_score(P("Ad 2d 3c 4h 5s"), Rules()) > V.low_score(P("Ad 2d 3c 4h 8s"), Rules())
    bots = [Scripted([Action.raise_to(2000)]), Scripted([Action.call()])]
    rig_board = "3c 4h 8s Kd Kc"
    t = Table(bots, Rules(n_players=2, payouts=(2, 1)), seed=0, variant=_hilo_rig(["Ad 2d", "Ks Qs"], rig_board))
    hs = t.play_hand()
    assert hs.deltas == [0, 0]  # kings full takes the high half, A2 the low half
    t = Table([Scripted([Action.raise_to(2000)]), Scripted([Action.call()])], Rules(n_players=2, payouts=(2, 1)),
              seed=0, variant=_hilo_rig(["9d Td", "Ks Qs"], rig_board))
    assert t.play_hand().deltas == [-2000, 2000]  # no low: the high hand scoops


def _hilo_rig(holes, board):
    class R(V.HiLoHooks):
        def on_deal(self, hs_, deck, rng):
            return [parse_cards(x) for x in holes]

        def on_street(self, street, b, hs_, deck, rng, ask=None):
            return tuple(parse_cards(board)[: len(b)]), hs_
    return R()


def test_lowball_and_wild_and_flush_over_full_scores():
    P = parse_cards
    low = V.LowballHooks()
    assert low.score_hand(P("7d 5c"), P("4h 3s 2d Kc Qc"), Rules()) > low.score_hand(P("Ad Ac"), P("4h 3s 2d Kc Qc"), Rules())
    assert low.score_hand(P("8d 5c"), P("4h 3s 2d 9c Tc"), Rules()) > low.score_hand(P("6d 5c"), P("4h 3s 2d 9c Tc"), Rules())  # 65432 is a straight
    wild = V.WildRankHooks(0)
    quads = wild.score_hand(P("2d 2c"), P("Kh Ks 7d 8c 9c"), Rules())
    assert quads > V.VariantHooks().score_hand(P("Kd Kc"), P("Kh 7s 7d 8c 9c"), Rules())  # two wild kings: quads beat a boat
    assert wild.score_hand(P("Ad Qc"), P("Kh 7s 4d 8c 9c"), Rules()) == V.VariantHooks().score_hand(P("Ad Qc"), P("Kh 7s 4d 8c 9c"), Rules())
    fof = V.FlushOverFullHooks()
    assert fof.score_hand(P("Ah 9h"), P("Kh 7h 6h 8c 8d"), Rules()) > fof.score_hand(P("8s 8h"), P("Kc 7h 6h 8c 6d"), Rules())


# ----- hooks bridge -----------------------------------------------------------------------------


class Decider(Scripted):
    """Answers every variant decision with a fixed value and remembers the prompts."""

    def __init__(self, actions, answer):
        super().__init__(actions)
        self.answer, self.prompts = answer, []

    def variant_decide(self, prompt):
        self.prompts.append(prompt)
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def test_ask_reaches_variant_decide_and_falls_back_on_exceptions():
    rules = Rules(n_players=3, payouts=(3, 2, 1), hole_cards=3)
    bots = [Decider([Action.call()] * 4, 0), Decider([Action.call()] * 4, RuntimeError("boom")), Scripted([Action.call()] * 4)]
    hooks = V.TossHooks()
    t = Table(bots, rules, seed=1, variant=hooks)
    hs = t.play_hand()
    assert bots[0].prompts and bots[0].prompts[0]["decision"] == "discard" and bots[0].prompts[0]["seat"] == 0
    holes0 = bots[0].obs[0].hole
    assert hooks.discards[0] == holes0[0]  # seat 0 tossed index 0 as asked
    assert t.stats[1].exceptions == 1  # seat 1's decider raised: counted, default discard used
    assert hooks.discards[1] == bots[1].obs[0].hole[V.default_discard(bots[1].obs[0].hole)]
    assert all(len(h) == 2 for h in hs.showdown.values()) and len(hs.board) == 5
    post = [o for o in bots[2].obs if o.street >= 1]
    assert post and post[0].extras["discards"] == hooks.discards


def test_variant_decide_is_found_through_impl_and_core():
    class Core:
        def __init__(self):
            self.prompts = []

        def variant_decide(self, prompt):
            self.prompts.append(prompt)
            return -1

    class Wrapped(Scripted):
        def __init__(self):
            super().__init__([])
            self.impl = type("Impl", (), {})()
            self.impl.core = Core()

    bots = [Wrapped(), Wrapped(), Scripted([])]
    t = Table(bots, Rules(n_players=3, payouts=(3, 2, 1)), seed=2, variant=V.SwapOneHooks())
    for _ in range(5):
        t.play_hand()
    assert any(b.impl.core.prompts for b in bots[:2])


def test_payout_hook_house_funding_and_loser_funding():
    rules_house = Rules(n_players=2, payouts=(2, 1), extras={"bounty_funding": "house"})
    hooks = V.BountyHooks(ratio=2.0, constant=10)
    hooks.bounties = {0: 12, 1: 12}
    bots = [Scripted([Action.raise_to(2000)]), Scripted([Action.call()])]
    t = Table(bots, rules_house, seed=0, variant=_bounty_rig(hooks, ["Ad Ac", "Kd Kc"], "2c 3d 7h 8s Tc"))
    hs = t.play_hand()
    assert hs.deltas[0] == 2000 * 2 + 10 and hs.deltas[1] == -2000 and sum(t.stacks) == 6010
    rules_losers = Rules(n_players=2, payouts=(2, 1), extras={"bounty_funding": "losers"})
    hooks2 = V.BountyHooks(ratio=1.5, constant=10)
    hooks2.bounties = {0: 12, 1: 12}
    bots = [Scripted([Action.raise_to(500)]), Scripted([Action.call()])]
    t = Table(bots, rules_losers, seed=0, variant=_bounty_rig(hooks2, ["Ad Ac", "Kd Kc"], "2c 3d 7h 8s Tc"))
    hs = t.play_hand()
    assert hs.deltas == [760, -760] and sum(t.stacks) == 4000


def _bounty_rig(hooks, holes, board):
    rig = Rig(holes, board)
    hooks.on_deal = rig.on_deal
    hooks.on_street = rig.on_street
    return hooks


def test_knockout_bounty_adds_points_to_the_biggest_winner():
    bots = [Scripted([Action.raise_to(100)]), Scripted([Action.raise_to(200)]), Scripted([Action.call()])]
    rig = Rig(["2c3d", "4c5d", "AsAh"], "Kc Qd 7h 8s Tc")
    hooks = V.KnockoutHooks(points=1.0)
    hooks.on_deal, hooks.on_street = rig.on_deal, rig.on_street
    res = play_table(bots, Rules(n_players=3, payouts=(3, 2, 1)), seed=0, variant=hooks, stacks=[100, 200, 1000])
    assert res.places == [2, 1, 0]
    assert res.points == [1.0, 2.0, 3.0 + 2.0]  # two knockouts on one hand


def test_bonus_card_charges_the_price_and_deals_a_third_card():
    bots = [Decider([Action.call()] * 4, True), Decider([Action.call()] * 4, False), Scripted([Action.call()] * 4)]
    rules = Rules(n_players=3, payouts=(3, 2, 1))
    hooks = V.BonusCardHooks(price_bb=1.0)
    t = Table(bots, rules, seed=3, variant=hooks)
    hs = t.play_hand()
    assert len(hs.holes[0]) == 3 and len(hs.holes[1]) == 2 and len(hs.holes[2]) == 3
    assert hs.contrib[0] - hs.contrib[1] == 20 and sum(t.stacks) == 6000
    flop = [o for o in bots[1].obs if o.street == 1]
    assert flop and flop[0].extras["bought"] == {0: True, 1: False, 2: True}


def test_exposed_cards_and_boards_in_extras():
    bots = [Recorder() for _ in range(3)]
    play_table(bots, Rules(n_players=3, payouts=(3, 2, 1), max_hands=2), seed=0, variant=V.ExposedCardHooks())
    o = bots[0].obs[0]
    assert set(o.extras["exposed"]) == {0, 1, 2} and o.extras["exposed"][o.seat] == o.hole[0]
    bots = [Scripted([]) for _ in range(3)]
    play_table(bots, Rules(n_players=3, payouts=(3, 2, 1), max_hands=2), seed=0, variant=V.TwoBoardsHooks())
    post = [o for o in bots[0].obs if o.street >= 1]
    assert post and len(post[0].extras["boards"]) == 2 and len(post[0].extras["boards"][1]) == len(post[0].board)


def test_no_variant_means_no_extras_and_identical_results():
    r1 = play_table([RandomBot(s) for s in range(8)], Rules(), seed=4)
    r2 = play_table([RandomBot(s) for s in range(8)], Rules(), seed=4, variant=V.VariantHooks())
    assert (r1.points, r1.stacks, r1.hands) == (r2.points, r2.stacks, r2.hands)


# ----- the catalog ------------------------------------------------------------------------------


def test_catalog_has_four_axes_and_about_twenty_entries():
    cat = V.catalog()
    assert 20 <= len(cat) <= 30
    assert {v.axis for v in cat} == set(V.AXES)
    assert len({v.name for v in cat}) == len(cat)
    assert set(V.names()) <= set(V.catalog_names())


@pytest.mark.parametrize("name", V.catalog_names())
def test_catalog_entry_is_valid_and_round_trips(name):
    v = V.get(name, seed=3)
    assert V.validate(v) == [], V.validate(v)
    assert v.summary and v.breaks and v.checklist and isinstance(v.config_patch, dict)
    from hyperion.tablegen import rules_from_dict
    from hyperion.sim.runner import load_rules
    assert rules_from_dict(v.rules_json()) == v.rules
    d = json.loads(json.dumps(v.rules_json()))
    assert rules_from_dict(d) == v.rules
    h1, h2 = v.new_hooks(), v.new_hooks()
    assert (h1 is None) == (v.hooks is None) and (h1 is None or h1 is not h2)


@pytest.mark.parametrize("name", [n for n in V.catalog_names() if V.get(n).playable])
def test_playable_entry_runs_100_hands_without_error(name):
    v = V.get(name, seed=3)
    rules = dataclasses.replace(v.rules, max_hands=100)
    bots = [RandomBot(s) if s % 2 else ChartTAG(s) for s in range(rules.n_players)]
    res = play_table(bots, rules, seed=5, variant=v.new_hooks())
    assert res.hands <= 100 and all(st.exceptions == 0 for st in res.stats)
    assert all(0 <= p for p in res.points)
    if rules.extras.get("bounty_funding", "losers") != "house":
        assert sum(res.stacks) == rules.starting_stack * rules.n_players


def test_catalog_cli_writes_rules_the_generator_and_sim_accept(tmp_path):
    out = tmp_path / "rules_short_deck.json"
    cmd = [sys.executable, "-m", "hyperion.drills.variants", "--rules", "short_deck", "--out", str(out)]
    subprocess.run(cmd, check=True, cwd=ROOT, stdout=subprocess.DEVNULL, timeout=60)
    sys.path.insert(0, str(ROOT / "tools"))
    import gen_tables
    from hyperion import tablegen as tg
    from hyperion.sim.runner import load_rules

    rules = gen_tables.load_rules(str(out))
    assert rules == V.short_deck().rules and len(tg.live_deck(rules)) == 36
    assert load_rules(str(out)) == rules
    out2 = tmp_path / "rules_omaha.json"
    subprocess.run([sys.executable, "-m", "hyperion.drills.variants", "--rules", "omaha_four", "--out", str(out2)],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL, timeout=60)
    r2 = gen_tables.load_rules(str(out2))
    assert r2.must_use_hole == 2 and r2.hole_cards == 4
    listing = subprocess.run([sys.executable, "-m", "hyperion.drills.variants", "--list"], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, check=True).stdout
    assert all(n in listing for n in V.catalog_names())


def test_runner_variant_selects_rules_and_hooks():
    from hyperion.sim.runner import run_tournament

    rep = run_tournament(["tag", "random"], tables=2, seed=1, variant=V.get("two_boards"))
    assert rep.hands > 0 and all(b.stats.exceptions == 0 for b in rep.bots.values())
    rep = run_tournament(["tag", "random"], tables=1, seed=1, variant=V.get("top_heavy"))
    assert sum(b.mean * b.seats / len(b.samples) for b in rep.bots.values()) == pytest.approx(100.0)
