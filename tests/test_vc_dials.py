"""F's dials from climb/vc-long-boards (Hero Config, `hero.<key>` on F), each off by default and gated to its twist:
long_board and its tier dials (boards past five, river_of_blood; tests/test_river_of_blood.py has the reads),
keep_call_shift (deal5_keep2's calls), variant_pushfold (PushFoldParams on twist tables)."""
from hyperion.core.types import ActionKind, Observation, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.strategy.hero import Config, HeroCore, config_from_dict

LEGAL = frozenset({ActionKind.RAISE, ActionKind.FOLD, ActionKind.CALL})


def _facing_bet(hole, board, to_call=60, pot=120, extras=None):
    bets = [0] * 8
    bets[1] = to_call
    return Observation(hole=parse_cards(hole), board=parse_cards(board), street=len(parse_cards(board)) - 2, seat=0,
                       button=7, stacks=[1900, 1900 - to_call] + [1900] * 6, bets=bets,
                       in_hand=[True, True] + [False] * 6, pot=pot, to_call=to_call, min_raise=2 * to_call,
                       max_raise=1900, legal=LEGAL, hand_no=3, blinds=(10, 20), extras=extras or {})


def test_every_new_dial_is_off_by_default():
    c = Config()
    assert (c.long_board, c.long_to_come, c.long_value_per_card, c.long_call_per_card, c.keep_call_shift,
            c.variant_pushfold, c.toss_call_shift) == (False, 1, 0, 0, 0, {}, 0)


def _spy_calls(cfg, rules, obs):
    h = HeroCore(cfg)
    h.new_table(rules, 0, 8)
    got = {}
    real = h.postflop.act

    def spy(*a, **kw):
        got.update(kw)
        return real(*a, **kw)

    h.postflop.act = spy
    return h.act(obs), got


def test_keep_call_shift_reads_calls_lower_on_deal5_keep2_only():
    # top pair, good kicker, facing a half-pot bet after the keep (two hole cards left)
    o = _facing_bet("Ah Kd", "Ks 8c 3d", extras={"revealed": {}})
    a0, kw0 = _spy_calls(config_from_dict({"use_profiler": False}, seed=1), V.deal5_keep2().rules, o)
    a2, kw2 = _spy_calls(config_from_dict({"use_profiler": False, "keep_call_shift": 2}, seed=1), V.deal5_keep2().rules, o)
    assert kw0["call_shift"] == 0 and kw2["call_shift"] == 2
    assert a0.kind is ActionKind.CALL and a2.kind is ActionKind.FOLD
    # plain hold'em and another twist: no shift
    for rules in (Rules(), V.toss_or_holdem().rules):
        _, kw = _spy_calls(config_from_dict({"use_profiler": False, "keep_call_shift": 2}, seed=1), rules,
                           _facing_bet("Ah Kd", "Ks 8c 3d"))
        assert kw["call_shift"] == 0


def test_variant_pushfold_reaches_catalogued_twists_only_and_shares_the_solution():
    cfg = config_from_dict({"variant_pushfold": {"call_equity_margin": 0.07}})
    for name in ("short_deck", "bounty", "toss_or_holdem", "river_of_blood"):
        h = HeroCore(cfg)
        h.new_table(V.get(name).rules, 0, 8)
        assert h.pushfold.p.call_equity_margin == 0.07 and h.pushfold.pre is h.preflop
    plain = HeroCore(cfg)
    plain.new_table(Rules(), 0, 8)
    assert plain.pushfold.p.call_equity_margin == 0.0
    for name in ("fixed_raise", "omaha_four"):
        h = HeroCore(cfg)
        h.new_table(V.get(name).rules, 0, 8)
        assert h.pushfold.p.call_equity_margin == 0.0
    h = HeroCore(cfg)
    h.new_table(V.short_deck().rules, 0, 8)
    base = HeroCore(Config())
    base.new_table(V.short_deck().rules, 0, 8)
    assert h.pushfold.p_call == base.pushfold.p_call and h.pushfold.push_set == base.pushfold.push_set


def test_toss_call_shift_reads_calls_lower_on_toss_tables_only():
    o = _facing_bet("Ah Kd", "Ks 8c 3d", extras={"discards": {}})
    cfg = config_from_dict({"use_profiler": False, "toss_call_shift": 2}, seed=1)
    _, kw = _spy_calls(cfg, V.toss_or_holdem().rules, o)
    assert kw["call_shift"] == 2
    for rules in (Rules(), V.deal5_keep2().rules):
        _, kw = _spy_calls(cfg, rules, _facing_bet("Ah Kd", "Ks 8c 3d"))
        assert kw["call_shift"] == 0
