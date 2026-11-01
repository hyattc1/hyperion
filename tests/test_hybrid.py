"""The hybrid candidate (hyperion.hybrid): rival 2's decision core behind Hero's shell. Legality, every catalogue entry
without an error, the rank-remap round trip, payouts reaching the core, the fallbacks, and timing."""
from time import perf_counter_ns

import pytest

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.hybrid import COUNTS, HybridCore, hybrid_config, make_bot
from hyperion.hybrid.bot import table_reason
from hyperion.hybrid.core import build_curve
from hyperion.sim import bestiary as B
from hyperion.sim.engine import BotStats, Table, play_table
from hyperion.sim.rivals import rival2 as R2
from hyperion.strategy.hero import icm_value
from tests.sim_helpers import Auditor

FAST_FIELD = ["hybrid", "tag", "pushfold", "loose_aggro", "nit", "station", "maniac", "random"]
# deterministic sampler (count only, no wall budget): the same inputs give the same decisions
COUNT_ONLY = {"mc_budget_us": 1e6, "mc_hard_us": 1e6, "soft_us": 1e6}


def _routes(bot) -> dict:
    return dict(bot.impl.core.counts) if hasattr(bot, "impl") else dict(bot.core.counts)


def test_hybrid_is_registered_and_its_fields_seat_it_where_hero_sits():
    assert "hybrid" in B.REGISTRY
    for f in ("realistic", "top", "top2", "holdout"):
        plain, hyb = B.field_names(f), B.field_names(f + "_h")
        assert plain[0] == "hero" and hyb[0] == "hybrid" and plain[1:] == hyb[1:]


def test_hybrid_plays_300_hands_legally_with_no_error_swallowed():
    rules = Rules(max_hands=300, starting_stack=16000)  # deep enough that busts do not end it early
    names = ["hybrid", "hybrid", "rival2", "rival1", "tag", "pushfold", "loose_aggro", "station"]
    hands = 0
    seed = 0
    core_decisions = 0
    while hands < 300:
        bots = [Auditor(B.make_bot(n, seed=seed * 8 + s), 8 * 16000) for s, n in enumerate(names)]
        t = Table(bots, rules, seed=seed, mode="measure")
        while not t.done:
            t.play_hand()
            hands += 1
        for s in (0, 1):
            st, inner = t.stats[s], bots[s].inner
            assert st.exceptions == 0, st.last_error
            assert st.illegal == 0
            assert inner.impl.safe.errors == 0
            routes = _routes(inner)
            assert routes.get("hero:core_error", 0) == 0, routes
            core_decisions += routes.get("core", 0)
        seed += 1
    assert core_decisions > 300


HERO_ONLY = {"short_deck", "lowball", "wild_deuces", "flush_over_full_house", "omaha_four", "exposed_card",
             "two_boards", "bounty", "knockout_bounty", "hi_lo", "fixed_raise", "toss_or_holdem",
             "three_card_blind_discard", "three_card_keep"}


@pytest.mark.parametrize("name", V.catalog_names())
def test_hybrid_plays_every_catalogue_entry_without_an_error(name):
    v = V.get(name, seed=3)
    bots = [B.make_bot(n, seed=40 + s) for s, n in enumerate(FAST_FIELD)]
    res = play_table(bots, v.rules, seed=11, mode="measure", variant=v.new_hooks())
    st = res.stats[0]
    assert st.exceptions == 0, st.last_error
    assert st.illegal == 0
    assert bots[0].impl.safe.errors == 0
    routes = _routes(bots[0])
    assert routes.get("hero:core_error", 0) == 0, routes
    core = sum(c for k, c in routes.items() if k.startswith("core"))
    if name in HERO_ONLY:
        assert core == 0 and any(k.startswith("hero:table:") for k in routes), routes
    else:
        assert core > 0, routes
    assert (table_reason(v.rules, bots[0].impl.config) is None) == (name not in HERO_ONLY)


def _perm_rules(seed: int = 5) -> Rules:
    return V.get("permuted_ranks", seed=seed).rules


def _to_displayed(cards, rules: Rules):
    inv = [0] * 13
    for d, c in enumerate(rules.rank_order):
        inv[c] = d
    return tuple(inv[c >> 2] * 4 + (c & 3) for c in cards)


def test_rank_remap_round_trip_the_permuted_game_plays_exactly_as_the_canonical_one():
    """A table of the plain game, recorded at seat 0, then replayed to a fresh hybrid under a rank permutation with
    every card (hole, board, showdowns) written in displayed ranks: every decision must be the same."""
    plain = Rules()
    perm = _perm_rules()
    assert tuple(perm.rank_order) != tuple(range(13))

    class Rec:
        def __init__(self, inner):
            self.inner, self.log = inner, []

        def new_table(self, rules, seat, n):
            self.inner.new_table(rules, seat, n)

        def act(self, obs):
            a = self.inner.act(obs)
            self.log.append(("act", obs, a))
            return a

        def hand_end(self, result):
            self.log.append(("end", result, None))
            self.inner.hand_end(result)

    a_bot = Rec(make_bot(seed=3, overrides=COUNT_ONLY))
    others = [B.make_bot(n, seed=90 + s) for s, n in enumerate(FAST_FIELD[1:])]
    play_table([a_bot] + others, plain, seed=21, mode="measure")
    acts = [x for x in a_bot.log if x[0] == "act"]
    assert len(acts) > 100 and any(o.street > 0 for _, o, _ in acts)

    b_bot = make_bot(seed=3, overrides=COUNT_ONLY)
    b_bot.new_table(perm, 0, 8)
    same = 0
    for kind, x, a in a_bot.log:
        if kind == "act":
            o = Observation(**{**x.__dict__, "hole": _to_displayed(x.hole, perm), "board": _to_displayed(x.board, perm)})
            assert b_bot.act(o) == a, (x.hand_no, x.street, x.hole, x.board)
            same += 1
        else:
            b_bot.hand_end(HandResult(x.hand_no, x.deltas, {s: _to_displayed(h, perm) for s, h in x.showdown.items()},
                                      _to_displayed(x.board, perm), x.history))
    assert same == len(acts)
    assert _routes(b_bot) == _routes(a_bot.inner)


def _preflop_obs(hole, stack=140, legal=None):
    n = 8
    stacks, bets = [2000] * n, [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0], stacks[1] = 1990, 1980
    stacks[2] = stack
    return Observation(hole=hole, board=(), street=0, seat=2, button=7, stacks=stacks, bets=bets, in_hand=[True] * n,
                       pot=0, to_call=20, min_raise=40, max_raise=stack,
                       legal=legal or frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE}),
                       hand_no=0, blinds=(10, 20))


def test_permuted_aces_shove_and_permuted_seven_deuce_folds():
    perm = _perm_rules()
    for rules, conv in ((Rules(), lambda c: c), (perm, lambda c: _to_displayed(c, perm))):
        bot = make_bot(seed=1)
        bot.new_table(rules, 2, 8)
        a = bot.act(_preflop_obs(conv(parse_cards("AsAd"))))
        assert a.kind is ActionKind.RAISE and a.amount == 140
        bot = make_bot(seed=1)
        bot.new_table(rules, 2, 8)
        assert bot.act(_preflop_obs(conv(parse_cards("7c2d")))).kind is ActionKind.FOLD


def test_the_core_curve_uses_the_tables_payouts_and_leaves_rival2_globals_alone():
    pts_before = list(R2.PTS)
    stacks = [2000] * 8
    for pays in ((8, 7, 6, 5, 4, 3, 2, 1), (10, 7, 5, 4, 3, 2, 1, 0), (50, 25, 12, 6, 3, 2, 1, 1)):
        c = build_curve(stacks, 0, pays)
        assert c.u(16000) == pytest.approx(pays[0])
        assert c.u(0) == pytest.approx(pays[-1])
        assert c.u(2000) == pytest.approx(sum(pays) / 8, rel=1e-6)  # equal stacks: the average payout
        assert c.u(1000) == pytest.approx(icm_value([1000] + [2000 * 15000 / 14000] * 7, 0, pays), rel=1e-6)
    hb = make_bot(seed=1)
    hb.new_table(Rules(payouts=(50, 25, 12, 6, 3, 2, 1, 1)), 0, 8)
    curve = hb.core.core._pending[2]
    assert curve.u(2000) == pytest.approx(12.5, rel=1e-6)
    assert list(R2.PTS) == pts_before  # an opponent rival 2 in the same process still prices its own table
    r2 = B.make_bot("rival2", seed=1)
    r2.new_table(Rules(payouts=(50, 25, 12, 6, 3, 2, 1, 1)), 0, 8)
    assert R2.build_curve(stacks, 0)[0].u(2000) == pytest.approx(sum(R2.PTS) / 8, rel=1e-6)


def test_the_curve_is_built_in_hand_end_never_inside_a_decision():
    bots = [B.make_bot(n, seed=60 + s) for s, n in enumerate(FAST_FIELD)]
    play_table(bots, Rules(), seed=5, mode="measure")
    core = bots[0].impl.core.core
    assert core.hands_seen > 20
    assert core.inline_curves == 0


def test_soft_deadline_answers_with_heros_cheap_path():
    bots = [B.make_bot(n, seed=70 + s) for s, n in enumerate(FAST_FIELD)]
    hb = bots[0].impl
    hb.core.cfg.soft_us = 0.0  # applied to the core in new_table: every postflop sample run is already late
    res = play_table(bots, Rules(), seed=8, mode="measure")
    assert res.stats[0].exceptions == 0 and res.stats[0].illegal == 0
    routes = _routes(bots[0])
    assert routes.get("hero:soft_deadline", 0) > 0, routes
    assert not hb.core.hero.panic  # the cheap path is per decision, not left switched on


def test_a_core_failure_is_heros_decision_not_a_forced_fold():
    hb = make_bot(seed=2)
    hb.new_table(Rules(), 2, 8)

    def boom(kit, t0):
        raise RuntimeError("core broke")

    hb.core.core.decide = boom
    a = hb.act(_preflop_obs(parse_cards("AsAd")))
    assert a.kind is ActionKind.RAISE  # Hero shoves aces at 7 bb too
    assert _routes(hb) == {"hero:core_error": 1}
    assert hb.safe.errors == 0


def test_three_card_games_with_the_core_use_its_best_two_preflop_and_heros_discard():
    v = V.get("toss_or_holdem")
    bots = [B.make_bot(n, seed=80 + s) for s, n in enumerate(FAST_FIELD)]
    asked = []
    hb = bots[0].impl
    hb.core.cfg.hero_on_three_cards = False  # the default gives Hero the whole table
    orig = hb.core.variant_decide

    def spy(prompt):
        ans = orig(prompt)
        asked.append(ans)
        return ans

    hb.core.variant_decide = spy
    res = play_table(bots, v.rules, seed=4, mode="measure", variant=v.new_hooks())
    assert res.stats[0].exceptions == 0
    routes = _routes(bots[0])
    assert routes.get("core:best_two", 0) > 0 and routes.get("core", 0) > 0, routes
    assert asked and all(a in (0, 1, 2) for a in asked)


def test_panic_routes_everything_to_hero():
    hb = make_bot(seed=2)
    hb.new_table(Rules(), 2, 8)
    hb.core.set_panic(True)
    hb.act(_preflop_obs(parse_cards("KsKd")))
    assert _routes(hb) == {"hero:panic": 1}
    hb.new_table(Rules(), 2, 8)  # SafeBot clears panic per table
    assert not hb.core.panic


def _host_overrun_rate(us: int = 60, n: int = 3000) -> float:
    """Fraction of fixed `us`-microsecond busy loops that take over 1 ms of wall time in this process."""
    over = 0
    for _ in range(n):
        t0 = perf_counter_ns()
        end = t0 + us * 1000
        while perf_counter_ns() < end:
            pass
        over += perf_counter_ns() - t0 > 1_000_000
    return over / n


def _host_p99_overhead(us: int = 200, n: int = 2000) -> float:
    """p99 of a fixed `us`-microsecond busy loop's wall time, in microseconds: the host's share of a p99."""
    xs = []
    for _ in range(n):
        t0 = perf_counter_ns()
        end = t0 + us * 1000
        while perf_counter_ns() < end:
            pass
        xs.append((perf_counter_ns() - t0) / 1000)
    xs.sort()
    return xs[int(0.99 * n)]


def test_hybrid_decision_p99_is_under_300_us_and_strict_timeouts_under_one_percent():
    # Preflop is rival 2's lookups (~25 us p50; its ICM curve moved to hand_end); postflop is its sampler at
    # mc_max samples inside a 200 us budget. On a loaded host both numbers follow the host: then a fixed busy loop
    # decides whose fault it is (skip with both numbers), as the rival tests do.
    names = ["hybrid", "rival2", "rival1", "tag", "pushfold", "loose_aggro", "hero", "station"]
    stats = [BotStats(n) for n in names]  # accumulated over the tables
    for seed in range(4):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(names)]
        play_table(bots, Rules(), seed=seed, mode="strict", stats=stats)
    st = stats[0]
    assert st.exceptions == 0, st.last_error
    assert st.illegal == 0
    calls, over = st.calls + st.first_calls, st.over_budget
    assert calls >= 300
    rate = over / calls
    if rate >= 0.01:
        host = _host_overrun_rate()
        if host >= 0.002:
            pytest.skip(f"host oversubscribed: hybrid {rate:.2%} over 1 ms, a fixed 60 us loop {host:.2%}")
    assert rate < 0.01, (over, calls)
    p99 = st.percentile_us(0.99)
    if p99 >= 300:
        host = _host_p99_overhead()
        if host >= 260:
            pytest.skip(f"host oversubscribed: hybrid p99 {p99:.0f} us, a fixed 200 us loop's p99 {host:.0f} us")
    assert p99 < 300, p99


def test_variant_decide_is_heros_and_guarded():
    hb = make_bot(seed=2)
    hb.new_table(V.get("toss_or_holdem").rules, 0, 8)
    idx = hb.variant_decide({"decision": "discard", "hole": parse_cards("AsAd7c"), "board": ()})
    assert idx == 2
    hb.core.hero.variant_decide = lambda p: 1 / 0
    assert hb.variant_decide({"decision": "discard", "hole": (0, 1, 2), "board": ()}) is None
    assert hb.safe.errors == 1


def test_counts_add_up_in_the_module_counter():
    before = sum(COUNTS.values())
    hb = make_bot(seed=2)
    hb.new_table(Rules(), 2, 8)
    hb.act(_preflop_obs(parse_cards("QsQd")))
    assert sum(COUNTS.values()) == before + 1
    assert isinstance(hb.core, HybridCore)
    assert hybrid_config({"mc_max": 32}).mc_max == 32
    with pytest.raises(KeyError):
        hybrid_config({"no_such_knob": 1})
    assert Action.fold() is not None
