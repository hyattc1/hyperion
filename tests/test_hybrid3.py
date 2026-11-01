"""The second hybrid candidate (`hybrid3`): rival 3's decision core behind the same shell as `hybrid`. Legality, every
catalogue entry without an error, the rank-remap round trip, payouts in its all-in prices, the hand_end history, the
fallbacks, and timing."""
import dataclasses
import random
from time import perf_counter_ns

import pytest

from hyperion.core.types import ActionKind, HandResult, Observation, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.hybrid import make_bot
from hyperion.hybrid.bot import table_reason
from hyperion.hybrid.core3 import Rival3Core, icm_points
from hyperion.sim import bestiary as B
from hyperion.sim.engine import BotStats, Table, play_table
from hyperion.sim.rivals import rival3 as R3
from hyperion.strategy.hero import icm_me
from tests.sim_helpers import Auditor

FAST_FIELD = ["hybrid3", "tag", "pushfold", "loose_aggro", "nit", "station", "maniac", "random"]
NO_PANIC = {"core": "rival3", "panic_after": 10 ** 9, "soft_us": 1e6}  # these tests must not read the wall clock
HERO_ONLY = {"short_deck", "lowball", "wild_deuces", "flush_over_full_house", "omaha_four", "exposed_card",
             "two_boards", "bounty", "knockout_bounty", "hi_lo", "fixed_raise", "toss_or_holdem",
             "three_card_blind_discard", "three_card_keep"}


def _routes(bot) -> dict:
    return dict(bot.impl.core.counts) if hasattr(bot, "impl") else dict(bot.core.counts)


def _core3(bot) -> Rival3Core:
    return (bot.impl if hasattr(bot, "impl") else bot).core.core


def test_hybrid3_is_registered_and_its_fields_seat_it_where_hero_sits():
    assert "hybrid3" in B.REGISTRY
    assert isinstance(_core3(B.make_bot("hybrid3", seed=1)), Rival3Core)
    for f in ("realistic", "top", "top2"):
        plain, hyb = B.field_names(f), B.field_names(f + "_h3")
        assert plain[0] == "hero" and hyb[0] == "hybrid3" and plain[1:] == hyb[1:]


def test_hybrid3_plays_300_hands_legally_with_no_error_swallowed(monkeypatch):
    monkeypatch.setattr(B, "HYBRID_CONFIG", {"panic_after": 10 ** 9})
    rules = Rules(max_hands=300, starting_stack=16000)
    names = ["hybrid3", "hybrid3", "rival3", "rival1", "tag", "pushfold", "loose_aggro", "station"]
    hands = seed = core_decisions = 0
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
            assert _core3(inner).replay_errors == 0  # rival 3 swallows these; the subclass counts them first
            routes = _routes(inner)
            assert routes.get("hero:core_error", 0) == 0, routes
            core_decisions += routes.get("core", 0)
        seed += 1
    assert core_decisions > 300


@pytest.mark.parametrize("name", V.catalog_names())
def test_hybrid3_plays_every_catalogue_entry_without_an_error(name):
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


def _to_displayed(cards, rules: Rules):
    inv = [0] * 13
    for d, c in enumerate(rules.rank_order):
        inv[c] = d
    return tuple(inv[c >> 2] * 4 + (c & 3) for c in cards)


def test_rank_remap_round_trip_the_permuted_game_plays_exactly_as_the_canonical_one():
    """A plain table recorded at seat 0, then replayed to a fresh hybrid3 under a rank permutation with every card in
    displayed ranks (hole, board, showdowns): every decision must be the same."""
    plain = Rules(starting_stack=16000, max_hands=200)
    perm = dataclasses.replace(V.get("permuted_ranks", seed=5).rules, starting_stack=16000, max_hands=200)

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

    a_bot = Rec(make_bot(seed=3, overrides=NO_PANIC))
    others = [B.make_bot(n, seed=90 + s) for s, n in enumerate(FAST_FIELD[1:])]
    play_table([a_bot] + others, plain, seed=21, mode="measure")
    acts = [x for x in a_bot.log if x[0] == "act"]
    assert len(acts) > 100 and any(o.street > 0 for _, o, _ in acts)
    b_bot = make_bot(seed=3, overrides=NO_PANIC)
    b_bot.new_table(perm, 0, 8)
    for kind, x, a in a_bot.log:
        if kind == "act":
            o = Observation(**{**x.__dict__, "hole": _to_displayed(x.hole, perm), "board": _to_displayed(x.board, perm)})
            assert b_bot.act(o) == a, (x.hand_no, x.street, x.hole, x.board)
        else:
            b_bot.hand_end(HandResult(x.hand_no, x.deltas, {s: _to_displayed(h, perm) for s, h in x.showdown.items()},
                                      _to_displayed(x.board, perm), x.history))
    assert _routes(b_bot) == _routes(a_bot.inner)


def test_icm_points_is_rival3s_closed_form_on_its_table_and_exact_on_others():
    rng = random.Random(1)
    for _ in range(500):
        st = [rng.choice([0, rng.randint(1, 6000)]) for _ in range(8)]
        st[0] = rng.randint(1, 6000)
        assert icm_points(st, 0, (10, 7, 5, 4, 3, 2, 1, 0)) == pytest.approx(R3._icm1(st, 0), abs=1e-9)
        for pays in ((8, 7, 6, 5, 4, 3, 2, 1), (50, 25, 12, 6, 3, 2, 1, 1), (3, 2, 1, 0, 0, 0, 0, 0)):
            assert icm_points(st, 0, pays) == pytest.approx(icm_me(st, 0, pays), abs=1e-9)
    assert icm_points([0, 100, 100], 0, (8, 7, 6)) == 0.0


def test_the_all_in_prices_use_the_tables_payouts_and_leave_rival3s_globals_alone():
    pts_before = tuple(R3._PTS)
    stacks, bets, inh = [1000, 3000, 2000, 2000, 2000, 2000, 2000, 2000], [0] * 8, [True] * 8
    for pays in ((10, 7, 5, 4, 3, 2, 1, 0), (8, 7, 6, 5, 4, 3, 2, 1), (50, 25, 12, 6, 3, 2, 1, 1)):
        hb = make_bot(seed=1, overrides=NO_PANIC)
        hb.new_table(Rules(payouts=pays), 0, 8)
        evf, evs, evw, evl = hb.core.core._allin(stacks, bets, inh, 0, 1, 300, 8)
        assert evf == pytest.approx(icm_me([1000, 3300, 2000, 2000, 2000, 2000, 2000, 2000], 0, pays))
        assert evl == pytest.approx(pays[7])  # I bust: last of eight
        assert evw > evf > evl
    r3 = R3.Bot()
    assert r3._allin(stacks, bets, inh, 0, 1, 300, 8)[3] == pytest.approx(0.0)  # as built: the brief's last place
    assert tuple(R3._PTS) == pts_before


def test_hand_end_passes_the_hands_history_in_the_kits_shape():
    seen = []
    orig = R3.Bot.hand_end

    def spy(self, result):
        if isinstance(self, Rival3Core):
            seen.append(result)
        return orig(self, result)

    R3.Bot.hand_end = spy
    try:
        bots = [B.make_bot(n, seed=50 + s) for s, n in enumerate(FAST_FIELD)]
        play_table(bots, Rules(max_hands=30), seed=2, mode="measure")
    finally:
        R3.Bot.hand_end = orig
    assert seen and all(isinstance(r.get("history"), list) for r in seen)
    kinds = {kind for r in seen for _, (kind, _) in r["history"]}
    assert kinds <= {"fold", "check", "call", "raise"} and "fold" in kinds
    assert all(isinstance(s, int) and isinstance(amt, int) for r in seen for s, (_, amt) in r["history"])


def _preflop_obs(hole, stack=140, legal=None, to_call=20, max_raise=None):
    n = 8
    stacks, bets = [2000] * n, [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0], stacks[1] = 1990, 1980
    stacks[2] = stack
    return Observation(hole=hole, board=(), street=0, seat=2, button=7, stacks=stacks, bets=bets, in_hand=[True] * n,
                       pot=0, to_call=to_call, min_raise=40, max_raise=max_raise or stack,
                       legal=legal or frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE}),
                       hand_no=0, blinds=(10, 20))


def test_permuted_aces_shove_and_permuted_seven_deuce_folds():
    perm = V.get("permuted_ranks", seed=5).rules
    for rules, conv in ((Rules(), lambda c: c), (perm, lambda c: _to_displayed(c, perm))):
        bot = make_bot(seed=1, overrides=NO_PANIC)
        bot.new_table(rules, 2, 8)
        a = bot.act(_preflop_obs(conv(parse_cards("AsAd"))))
        assert a.kind is ActionKind.RAISE and a.amount == 140
        bot = make_bot(seed=1, overrides=NO_PANIC)
        bot.new_table(rules, 2, 8)
        assert bot.act(_preflop_obs(conv(parse_cards("7c2d")))).kind is ActionKind.FOLD


def test_a_declined_core_decision_is_heros():
    """Rival 3 returns nothing when it wants to shove and only call or fold is legal (as built it would then fold)."""
    hb = make_bot(seed=2, overrides=NO_PANIC)
    hb.new_table(Rules(), 2, 8)
    obs = _preflop_obs(parse_cards("AsKs"), stack=15, legal=frozenset({ActionKind.FOLD, ActionKind.CALL}), to_call=15)
    a = hb.act(obs)
    assert a.kind in (ActionKind.CALL, ActionKind.FOLD)
    assert _routes(hb) in ({"hero:core_none": 1}, {"core": 1})


def test_soft_deadline_answers_with_heros_cheap_path():
    bots = [B.make_bot(n, seed=70 + s) for s, n in enumerate(FAST_FIELD)]
    hb = bots[0].impl
    hb.core.cfg.soft_us = 0.0  # applied in new_table: every decision is already late
    res = play_table(bots, Rules(max_hands=40), seed=8, mode="measure")
    assert res.stats[0].exceptions == 0 and res.stats[0].illegal == 0
    routes = _routes(bots[0])
    assert routes.get("hero:soft_deadline", 0) > 0 and routes.get("core", 0) == 0, routes
    assert not hb.core.hero.panic


def _best_of_replay(over: dict, seeds=range(3), n: int = 3) -> list[int]:
    """Each decision's cost as the minimum over `n` replays of the same recorded table (ns): what the bot itself
    costs, with the host's preemptions and cache misses taken out."""
    names = ["rival2", "rival1", "tag", "pushfold", "loose_aggro", "hero", "station"]
    out: list[int] = []
    for seed in seeds:
        log = []
        bot = make_bot(seed=seed, overrides=over)

        class Rec:
            def new_table(self, r, s, k):
                bot.new_table(r, s, k)

            def act(self, o):
                log.append(("a", o))
                return bot.act(o)

            def hand_end(self, r):
                log.append(("e", r))
                bot.hand_end(r)

        play_table([Rec()] + [B.make_bot(nm, seed=seed * 8 + i) for i, nm in enumerate(names, 1)], Rules(), seed=seed,
                   mode="measure")
        best = None
        for _ in range(n):
            b = make_bot(seed=seed, overrides=over)
            b.new_table(Rules(), 0, 8)
            ts = []
            for kind, x in log:
                if kind == "a":
                    t0 = perf_counter_ns()
                    b.act(x)
                    ts.append(perf_counter_ns() - t0)
                else:
                    b.hand_end(x)
            best = ts if best is None else [min(u, v) for u, v in zip(best, ts)]
        out += best
    return out


def test_hybrid3_decision_cost_best_of_replay_is_heros_order():
    # Rival 3 has no sampler: a history replay and table lookups. On this box, best of 5: mean 23 us, p99 42 us
    # (Hero 21 / 38). Wall-clock percentiles on a loaded host measure the host (a strict-mode p99 test failed half
    # the time at load 30+), so the cost is read from the best of three replays of the same recorded tables.
    xs = sorted(_best_of_replay({"core": "rival3", "soft_us": 1e6, "panic_after": 10 ** 9}))
    n = len(xs)
    assert n > 300
    assert sum(xs) / n < 60_000, sum(xs) / n
    assert xs[int(0.99 * n)] < 150_000, xs[int(0.99 * n)]


def test_hybrid3_strict_timeouts_are_heros_order_at_the_same_load():
    # Strict mode, hybrid3 and Hero at the same tables, so they share whatever load the host has: hybrid3's share of
    # decisions over 1 ms must stay within 3x Hero's (plus 0.2 points of slack for small counts), or under 1%.
    names = ["hybrid3", "rival2", "rival1", "tag", "pushfold", "loose_aggro", "hero", "station"]
    stats = [BotStats(n) for n in names]
    for seed in range(4):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(names)]
        play_table(bots, Rules(), seed=seed, mode="strict", stats=stats)
    st, hero = stats[0], stats[6]
    assert st.exceptions == 0, st.last_error
    assert st.illegal == 0
    calls = st.calls + st.first_calls
    assert calls >= 300
    rate = st.over_budget / calls
    hero_rate = hero.over_budget / (hero.calls + hero.first_calls)
    assert rate < 0.01 or rate <= 3 * hero_rate + 0.002, (rate, hero_rate)


def test_the_exploit_layer_composes_in_front_of_every_decision_and_only_once():
    from hyperion.strategy.exploit import ExploitParams

    over = {**NO_PANIC, "exploit": {"bet_checked": True, "post_streak": 1, "bet_min_fold": 0.5, "steal": True}}
    hb = make_bot(seed=4, overrides=over)
    assert hb.core.ex is not None and hb.core.ex.p.bet_checked
    if hasattr(hb.core.hero.cfg, "exploit"):
        assert not hb.core.hero.cfg.exploit.active  # the fallback Hero's own copy is off: no decision is seen twice
    names = ["hybrid3", "station", "montecarlo30", "timeout_then_recover", "tag", "pushfold", "nit", "loose_aggro"]
    bots = [hb] + [B.make_bot(n, seed=60 + s) for s, n in enumerate(names[1:])]
    # the deterministic timeout model: the timeout bots fold when their modelled cost is over budget, as on the night
    res = play_table(bots, Rules(starting_stack=8000), seed=3, mode="model")
    assert res.stats[0].exceptions == 0 and res.stats[0].illegal == 0 and hb.safe.errors == 0
    routes = _routes(hb)
    fired = sum(v for k, v in routes.items() if k.startswith("exploit:"))
    assert fired == sum(hb.core.ex.fired.values()) and fired > 0, routes
    # {} = Hero's shipped exploit params unchanged: a layer exactly when Hero ships one (ExploitParams() itself is off)
    from hyperion.strategy.hero import Config

    assert (make_bot(seed=4, overrides={**NO_PANIC, "exploit": {}}).core.ex is not None) == Config().exploit.active
    assert B.make_bot("hybrid3_x", seed=1).impl.config.core == "rival3"


def test_a_rival3_hybrid_never_imports_rival2s_core():
    """Rival 2's module runs a Monte Carlo and gc.freeze() at import (1.2-6 s): a hybrid3 package must not pay it."""
    import subprocess
    import sys
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    probe = ("import sys; sys.path.insert(0, sys.argv[1]); from hyperion.hybrid import make_bot; "
             "make_bot(overrides={'core': 'rival3', 'exploit': 'hero'}); "
             "print('hyperion.sim.rivals.rival2' in sys.modules, 'hyperion.sim.rivals.rival3' in sys.modules)")
    out = subprocess.run([sys.executable, "-I", "-B", "-c", probe, str(root)], capture_output=True, text=True,
                         cwd=str(root.parent), timeout=120)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["False", "True"], out.stdout
