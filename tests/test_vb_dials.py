"""F's dials for the three likeliest twists (Hero Config, `hero.<key>` on F): each is off by default, and each does
what it says when on. toss_dead / toss_value_shift (toss_or_holdem), bounty_exact / bounty_call_scale /
bounty_bet_frac (bounty), short_deck_read / variant_tables (short deck), variant_preflop (any catalogued twist)."""
import random

from hyperion import tablegen as T
from hyperion.core.types import ActionKind, Observation, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.strategy.hero import Config, HeroCore, config_from_dict
from hyperion.strategy.postflop import Postflop
from hyperion.strategy.tables import tables_for

LEGAL = frozenset({ActionKind.CHECK, ActionKind.RAISE, ActionKind.FOLD, ActionKind.CALL})


def _obs(hole, board, street=1, extras=None, stacks=None, bets=None, pot=100, to_call=0, in_hand=None, seat=0):
    stacks = stacks or [1900] * 8
    return Observation(hole=parse_cards(hole), board=parse_cards(board), street=street, seat=seat, button=7,
                       stacks=stacks, bets=bets or [0] * 8, in_hand=in_hand or [True, True] + [False] * 6, pot=pot,
                       to_call=to_call, min_raise=20, max_raise=stacks[seat], legal=LEGAL, hand_no=3, blinds=(10, 20),
                       extras=extras or {})


def test_every_new_dial_is_off_by_default():
    c = Config()
    assert (c.toss_dead, c.toss_value_shift, c.bounty_exact, c.bounty_call_scale, c.bounty_bet_frac,
            c.short_deck_read, c.variant_tables, c.variant_preflop) == (False, 0, False, 1.0, 0.0, False, "", {})


def _captured_dead(cfg, extras):
    h = HeroCore(cfg)
    h.new_table(V.toss_or_holdem().rules, 0, 8)
    got = {}
    real = h.postflop.act

    def spy(*a, **kw):
        got.update(kw)
        return real(*a, **kw)

    h.postflop.act = spy
    h.act(_obs("8s 7s", "2s 9s 3d", extras=extras))
    return got


def test_toss_dead_takes_every_face_up_toss_off_the_outs():
    extras = {"discards": {1: parse_cards("As")[0], 0: parse_cards("Kd")[0]}}
    assert _captured_dead(Config(), extras)["dead"] == ()
    assert set(_captured_dead(config_from_dict({"toss_dead": True}), extras)["dead"]) == set(parse_cards("As Kd"))
    assert _captured_dead(config_from_dict({"toss_value_shift": 1}), extras)["value_shift"] == 1
    assert _captured_dead(Config(), extras)["value_shift"] == 0


def test_toss_dead_reads_the_earlier_tosses_in_the_toss_choice():
    h = HeroCore(config_from_dict({"toss_dead": True}))
    h.new_table(V.toss_or_holdem().rules, 0, 8)
    seen = []
    real = h.postflop._read

    def spy(hole, board, mu, dead):
        seen.append(tuple(dead))
        return real(hole, board, mu, dead)

    h.postflop._read = spy
    prompt = {"decision": "discard", "hole": parse_cards("8s 7s Kd"), "board": parse_cards("2s 9s 3d"),
              "discards": {3: parse_cards("As")[0]}}
    k = h.variant_decide(prompt)
    assert k in (0, 1, 2) and len(seen) == 3
    assert all(parse_cards("As")[0] in d for d in seen)  # the earlier toss, and the card each keep throws
    assert {d[-1] for d in seen} == set(parse_cards("8s 7s Kd"))
    off = HeroCore()
    off.new_table(V.toss_or_holdem().rules, 0, 8)
    seen.clear()
    off.postflop._read = spy
    off.variant_decide(prompt)
    assert seen == [(), (), ()]  # off: no dead cards in the toss choice


def test_short_deck_read_knows_the_ace_six_straight_and_five_flush_outs():
    R = Postflop.read
    assert R(parse_cards("Ac 6d"), parse_cards("7h 8s 9c"))[0] == 3  # hold'em: an open-ender
    assert R(parse_cards("Ac 6d"), parse_cards("7h 8s 9c"), short=True)[0] == 6  # short deck: a straight
    assert R(parse_cards("Th Jh"), parse_cards("6h 7h Kc"))[1] == 9
    assert R(parse_cards("Th Jh"), parse_cards("6h 7h Kc"), short=True)[1] == 5
    # A6 on 7 8 K: a gutshot to A-6-7-8-9 on the short deck, nothing in hold'em
    assert R(parse_cards("Ac 6d"), parse_cards("7h 8s Kc"), short=True)[:2] == (1, 4)
    h = HeroCore(config_from_dict({"short_deck_read": True}))
    h.new_table(V.short_deck().rules, 0, 8)
    assert h.postflop.short
    h.new_table(Rules(), 0, 8)
    assert not h.postflop.short
    off = HeroCore()
    off.new_table(V.short_deck().rules, 0, 8)
    assert not off.postflop.short


def _bounty_core(**dials):
    h = HeroCore(config_from_dict(dials))
    h.new_table(V.bounty().rules, 0, 8)
    return h


def test_bounty_exact_prices_the_net_win_and_a_callers_chips():
    h = _bounty_core(bounty_exact=True)
    # hand start: 2000 each; we put 100 in preflop (pot 200 of which 100 ours), now on the flop
    o = _obs("7c 2d", "Kh 9s 4c", extras={"bounties": {0: 5}}, stacks=[1900, 1900] + [2000] * 6, pot=200)
    h.hand_no, h.hand_start = 3, [2000] * 8
    bonus, k = h._bounty_exact(o, o.extras)
    assert k == 0.5 and bonus == 0.5 * 100 + 10  # the others' 100, not the whole 200
    old = HeroCore(Config())
    old.new_table(V.bounty().rules, 0, 8)
    assert old._bounty_bonus(o, o.extras) == 0.5 * 200 + 10  # before: our own 100 counted too
    miss = h._bounty_exact(_obs("Qc 2d", "Kh 9s 4c", extras={"bounties": {0: 5}}), {"bounties": {0: 5}})
    assert 0 < miss[1] < 0.5  # the 7 can still come


def test_bounty_bet_bets_a_hit_bounty_where_hero_would_check():
    o = _obs("7c 2d", "Kh 9s 4c", extras={"bounties": {0: 5}})
    off = _bounty_core()
    on = _bounty_core(bounty_bet_frac=0.5)
    a_off, a_on = off.act(o), on.act(o)
    assert a_off.kind is ActionKind.CHECK and a_on.kind is ActionKind.RAISE and a_on.amount == 50
    o2 = _obs("Qc 2d", "Kh 9s 4c", extras={"bounties": {0: 5}})  # no bounty in hand or on the board
    assert on.act(o2).kind == off.act(o2).kind


def test_variant_preflop_reaches_catalogued_twists_only():
    cfg = config_from_dict({"variant_preflop": {"call_raise_frac": 0.15}})
    for name in ("short_deck", "bounty", "toss_or_holdem"):
        h = HeroCore(cfg)
        h.new_table(V.get(name).rules, 0, 8)
        assert h.preflop.p.call_raise_frac == 0.15
    h = HeroCore(cfg)
    h.new_table(Rules(), 0, 8)
    assert h.preflop.p.call_raise_frac == 0.45
    h.new_table(Rules(extras={"variant": "holdem"}), 0, 8)
    assert h.preflop.p.call_raise_frac == 0.45


def test_variant_tables_by_name_must_match_the_card_rules():
    sd = V.short_deck().rules
    assert tables_for(sd, name="short_deck").dir == tables_for(sd).dir
    # a set for other card rules is ignored: the table's own set loads
    assert tables_for(sd, name="toss_or_holdem").dir == tables_for(sd).dir
    assert tables_for(sd, name="no_such_set").dir == tables_for(sd).dir


def test_the_generator_scores_the_short_deck_showdown():
    r = V.short_deck().rules
    T._init_worker(T.rules_to_dict(r))
    try:
        hk = V.ShortDeckHooks()
        deck = T.live_deck(r)
        rng = random.Random(3)
        for _ in range(3000):
            a = rng.sample(deck, 14)
            x, y = tuple(a[:7]), tuple(a[7:])
            s1, s2 = T._strength(x), T._strength(y)
            h1, h2 = hk.score_hand(x[:2], x[2:], r), hk.score_hand(y[:2], y[2:], r)
            assert (s1 > s2) == (h1 > h2) and (s1 == s2) == (h1 == h2)
            assert 0 <= T._category(s1) <= 8
    finally:
        T._init_worker(T.rules_to_dict(Rules()))
    assert not T._FOF and not T._LOW6


def test_r3_bounty_is_off_by_default_and_prices_the_bounty_in_the_cores_all_ins():
    from hyperion.hybrid.bot import HybridCore, hybrid_config

    off = HybridCore(hybrid_config({"core": "rival3", "hero_on_bounty": False}))
    off.new_table(V.bounty().rules, 0, 8)
    assert off._table_why is None and off._bounty is None
    on = HybridCore(hybrid_config({"core": "rival3", "hero_on_bounty": False, "r3.bounty": 1.0}))
    on.new_table(V.bounty().rules, 0, 8)
    assert on._bounty == (0.5, 10.0, 1.0)
    plain = HybridCore(hybrid_config({"core": "rival3", "r3.bounty": 1.0}))
    plain.new_table(Rules(), 0, 8)
    assert plain._bounty is None
    held = on._bounty_price(_obs("7c 2d", "", street=0, extras={"bounties": {0: 5}}))
    assert held == (1.0, True, 0.5, 10.0, 1.0)
    p, steal, *_ = on._bounty_price(_obs("Qc 2d", "", street=0, extras={"bounties": {0: 5}}))
    assert not steal and 0.3 < p < 0.4  # a 7 on a five-card board
    core = on.core
    stacks, bets, inh = [1000] * 8, [0] * 6 + [10, 20], [True] * 8
    stacks[6], stacks[7] = 990, 980
    core._bounty = None
    f0, s0, w0, l0 = core._allin(stacks, bets, inh, 0, 7, 0, 8)
    core._bounty = held
    f1, s1, w1, l1 = core._allin(stacks, bets, inh, 0, 7, 0, 8)
    assert (f1, l1) == (f0, l0) and s1 > s0 and w1 > w0


def test_bounty_hands_are_scored_with_the_bounties_their_players_were_shown():
    import dataclasses

    from hyperion.sim.bestiary import ChartTAG
    from hyperion.sim.engine import Table

    class Seer(ChartTAG):
        seen: dict = {}

        def act(self, obs):
            Seer.seen.setdefault(obs.hand_no, dict(obs.extras.get("bounties") or {}))
            return super().act(obs)

    v = V.bounty()
    hooks = v.new_hooks()
    scored = {}
    real = hooks.on_payout

    def spy(deltas, holes, board, hand_no, rules, rng):
        out = real(deltas, holes, board, hand_no, rules, rng)
        scored[hand_no] = dict(hooks.bounties)
        return out

    hooks.on_payout = spy
    Seer.seen = {}
    t = Table([Seer(s) for s in range(8)], dataclasses.replace(v.rules, max_hands=60), seed=3, variant=hooks)
    while not t.done:
        t.play_hand()
    assert 0 in Seer.seen and 25 in Seer.seen and 50 in Seer.seen  # hands 0, 25, 50 show the block's new bounties
    for h, b in Seer.seen.items():
        assert b == scored[h], h
    assert Seer.seen[0] != {} and Seer.seen[24] == Seer.seen[0]
