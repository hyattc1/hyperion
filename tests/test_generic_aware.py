"""The generic variant-aware opponents (hyperion/sim/generic.py): they read any variant through its own hooks, play
like their archetypes on hold'em, answer every catalogued variant decision legally, and stay out of the night pools."""
import dataclasses
import os
import random
import textwrap

import pytest

from hyperion.core.cards import hole_class
from hyperion.core.types import Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.sim import bestiary as B
from hyperion.sim import generic as G
from hyperion.sim.engine import Table
from hyperion.sim.field import night
from hyperion.sim.runner import run_tournament

GEN = ("gen_mc", "gen_tag", "gen_pushfold")


def test_generic_field_seats_the_three_and_no_night_pool_has_them():
    members = B.field_names("generic_aware")
    assert len(members) == 8 and members.count("hero") == 1 and all(g in members for g in GEN)
    for pool in ("night", "night_hard", "night0"):
        assert not set(night.members(pool)) & set(G.GENERIC)
        for seed in range(50):
            assert not set(night.draw(pool, seed)) & set(G.GENERIC)
    for field in ("realistic", "top", "judge", "judge2", "outside", "outside_strong", "elite", "mirror"):
        assert not set(B.field_names(field)) & set(G.GENERIC)


def test_every_catalog_entry_has_a_prepared_table():
    for name in V.catalog_names():
        v = V.get(name)
        sim = G.Sim(v.rules, v)
        assert os.path.exists(G.table_path(G.table_key(name, v.rules, sim.hooks))), name


def test_holdem_twins_are_the_classes_themselves_and_preflop_matches_the_archetypes():
    rules = Rules()
    sim = G.Sim(rules, None)
    assert sim.holdem_cards()
    t = G.load_table("holdem", rules, sim, build_if_missing=False)
    rng = random.Random(3)
    for _ in range(300):
        hole = tuple(rng.sample(range(52), 2))
        assert t.twin_of(hole) == hole_class(hole)
    # a card-identical variant (antes) reuses the hold'em reference too
    v = V.get("antes_from_level_3")
    assert G.Sim(v.rules, v).holdem_cards()


def test_the_rollout_prices_the_variant_not_holdem():
    rng = random.Random(1)
    aa, seven_deuce = parse_cards("As Ah"), parse_cards("7c 2d")
    hold = G.Sim(Rules(), None)
    hold.sync({}, ())
    assert 0.80 < hold.rollout(aa, (), 0, [1], 600, rng, street=0) < 0.90
    low = V.get("lowball")
    ls = G.Sim(low.rules, low)
    ls.sync({}, ())
    # under 2-7 lowball 7-2 offsuit is a strong hand and aces a weak one
    assert ls.rollout(seven_deuce, (), 0, [1], 600, rng, street=0) > ls.rollout(aa, (), 0, [1], 600, rng, street=0)
    wild = V.get("wild_deuces")
    ws = G.Sim(wild.rules, wild)
    ws.sync({}, ())
    assert ws.made_share(parse_cards("2c 2d"), parse_cards("Ks 9h 4c"), 40, rng) > 0.95  # trips with two wilds and K


def test_bounty_payoff_and_restored_state():
    v = V.get("bounty")
    sim = G.Sim(v.rules, v)
    hole = parse_cards("Ks 7d")
    sim.sync({"bounties": {"0": 11, "1": 3}}, ())  # seat 0's bounty is a king (rank 11): held
    assert sim.hooks.bounties == {0: 11, 1: 3}
    assert sim.win_now_ratio(hole, (), 0, [1], 120, 40, 0, random.Random(1)) > 1.3
    sim.sync({"bounties": {"0": 2, "1": 3}}, ())
    assert sim.win_now_ratio(hole, (), 0, [1], 120, 40, 0, random.Random(1)) == pytest.approx(1.0)


def test_public_cards_dead_or_held():
    dead, held = G.public_cards({"discards": {1: 5, 2: 9}, "bounties": {1: 3}, "bonus_card_price": 20}, me=0)
    assert dead == {5, 9} and held == {}
    dead, held = G.public_cards({"exposed": {0: 4, 1: 50, 2: 7}}, me=0, in_hand=[True, True, False])
    assert held == {1: (50,)} and dead == {7}
    boards = {"boards": [tuple(parse_cards("As Kd 2c")), tuple(parse_cards("Qh Jh 3s"))]}
    tb = V.get("two_boards")
    sim = G.Sim(tb.rules, tb)
    sim.sync(boards, boards["boards"][0])
    assert sim.hooks.board2 == tuple(parse_cards("Qh Jh 3s"))


@pytest.mark.parametrize("name", ["toss_or_holdem", "three_card_blind_discard", "deal5_keep2", "swap_one_turn",
                                  "bonus_card", "auction"])
def test_variant_decisions_are_legal(name):
    v = V.get(name)
    bots = [B.make_bot(g, seed=s) for s, g in enumerate(GEN)]
    for s, b in enumerate(bots):
        b.new_table(v.rules, s, 8)
    rng = random.Random(7)
    deck = list(range(52))
    for _ in range(20):
        cards = rng.sample(deck, v.rules.hole_cards + 3 + 1)
        hole = tuple(cards[:v.rules.hole_cards])
        flop = tuple(cards[v.rules.hole_cards:v.rules.hole_cards + 3])
        for b in bots:
            if name in ("toss_or_holdem", "three_card_blind_discard"):
                ans = b.variant_decide({"decision": "discard", "hole": hole, "board": flop if name == "toss_or_holdem"
                                        else (), "discards": {}, "seat": b.seat})
                assert ans in range(3)
            elif name == "deal5_keep2":
                ans = b.variant_decide({"decision": "keep", "hole": hole, "board": flop, "revealed": {}, "keep": 2,
                                        "seat": b.seat})
                assert V.legal_keep(ans, 5) is not None
            elif name == "swap_one_turn":
                ans = b.variant_decide({"decision": "swap", "hole": hole, "board": flop + tuple(cards[-1:]), "seat": b.seat})
                assert ans in (-1, 0, 1)
            elif name == "bonus_card":
                ans = b.variant_decide({"decision": "buy_card", "price": 20, "hole": hole, "board": flop,
                                        "seat": b.seat})
                assert isinstance(ans, bool)
            else:
                ans = b.variant_decide({"decision": "bid", "hole": hole, "board": flop, "pot": 300, "stack": 1800,
                                        "max_bid": 1800, "n_bidders": 3, "big_blind": 20, "seat": b.seat})
                assert isinstance(ans, int) and 0 <= ans <= 1800 // 4
    # an unknown decision gets None: the hook's default
    assert bots[0].variant_decide({"decision": "something_new", "hole": hole}) is None


@pytest.mark.parametrize("name", V.catalog_names())
def test_every_catalog_entry_plays_clean(name):
    v = V.get(name)
    rules = dataclasses.replace(v.rules, max_hands=40)
    names = list(B.field_names("generic_aware"))
    # the engine counts exceptions and illegal actions itself (an Auditor's chip count would trip on house bounties)
    bots = [B.make_bot(nm, seed=s) for s, nm in enumerate(names)]
    t = Table(bots, rules, seed=11, variant=v.new_hooks(), mode="model")
    while not t.done:
        t.play_hand()
    for s, nm in enumerate(names):
        if nm in GEN:
            st = t.stats[s]
            assert st.exceptions == 0, (name, nm, st.last_error)
            assert st.illegal == 0, (name, nm)


def test_a_variant_from_a_file_registers_and_the_generic_bots_find_its_hooks(tmp_path):
    src = tmp_path / "tonight.py"
    src.write_text(textwrap.dedent('''
        from hyperion.core.types import Rules
        from hyperion.drills.variants import FlushOverFullHooks, Variant

        def variant():
            return Variant(name="tonight_test", summary="a flush beats a full house", breaks="", checklist=(),
                           rules=Rules(extras={"variant": "tonight_test"}), hooks_factory=FlushOverFullHooks)
    '''))
    v = V.get(f"{src}:variant")
    assert v.name == "tonight_test" and V.get("tonight_test").name == "tonight_test"
    assert isinstance(G.variant_of(v.rules), V.Variant)
    sim = G.Sim(v.rules, G.variant_of(v.rules))
    assert isinstance(sim.hooks, V.FlushOverFullHooks) and not sim.fast
    rep = run_tournament(B.field_names("generic_aware"), 1, seed=3, mode="model",
                         rules=dataclasses.replace(v.rules, max_hands=30), variant=v)
    for g in GEN:
        assert rep.bots[g].stats.exceptions == 0 and rep.bots[g].stats.illegal == 0


@pytest.mark.parametrize("first", ["hyperion.sim.aware", "hyperion.sim.generic", "hyperion.sim.bestiary"])
def test_any_import_order_registers_everything(first):
    # climb_accept's aware stage imports aware before the bestiary: a cycle once made that an ImportError
    import subprocess
    import sys

    code = (f"import {first}\nfrom hyperion.sim import bestiary as B\n"
            "assert 'gen_mc' in B.REGISTRY and 'generic_aware' in B.FIELDS and 'toss_tag' in B.REGISTRY")
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run([sys.executable, "-c", code], check=True, cwd=root)
