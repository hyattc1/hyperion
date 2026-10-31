import random
import time

import pytest

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules
from hyperion.strategy.hero import Config, Hero, HeroCore, IcmCurve, make_bot
from hyperion.strategy.profiler import Profiler

from .strategy_helpers import make_obs, preflop_obs, random_obs, street_obs

R, C, F, K = Action.raise_to, Action.call(), Action.fold(), Action.check()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731


@pytest.fixture(scope="module")
def hero():
    h = Hero(Config(seed=3))
    h.new_table(Rules(), 2, 8)
    return h


def test_make_bot_is_a_safe_hero():
    bot = make_bot()
    assert isinstance(bot, Hero) and bot.safe.inner is bot.core
    bot.new_table(Rules(), 0, 8)
    assert bot.act(make_obs(seat=0, bets=[10, 20, 0, 0, 0, 0, 0, 0], hole="Ah Ad")).kind is ActionKind.RAISE


def test_latency_two_thousand_random_decisions(hero):
    """Mean < 0.15 ms and p99 < 0.5 ms over 2,000 self-consistent random decision points.

    Each observation is timed on three passes and the minimum kept: this machine runs other jobs,
    and a preempted call reports the scheduler, not the bot. The raw single pass is printed too."""
    rng = random.Random(2026)
    obs = [random_obs(rng) for _ in range(2000)]
    for o in obs[:200]:  # warm caches, then measure
        hero.act(o)
    before = dict(hero.safe.stats())
    best = [float("inf")] * len(obs)
    raw = []
    for rep in range(3):
        for i, o in enumerate(obs):
            t = time.perf_counter()
            hero.act(o)
            dt = time.perf_counter() - t
            if rep == 0:
                raw.append(dt)
            if dt < best[i]:
                best[i] = dt
    best.sort()
    raw.sort()
    mean = sum(best) / len(best)
    p99 = best[int(0.99 * len(best))]
    after = hero.safe.stats()
    print(f"\nhero.act min-of-3: mean {mean*1e6:.1f} us, p99 {p99*1e6:.1f} us, max {best[-1]*1e6:.1f} us"
          f" | single pass: mean {sum(raw)/len(raw)*1e6:.1f} us, p99 {raw[int(0.99*len(raw))]*1e6:.1f} us,"
          f" max {raw[-1]*1e6:.1f} us, overruns {after['overruns'] - before['overruns']} of {3 * len(obs)}")
    assert after["errors"] == before["errors"], "inner exceptions on self-consistent random observations"
    assert mean < 0.15e-3, f"mean {mean*1e6:.1f} us"
    assert p99 < 0.5e-3, f"p99 {p99*1e6:.1f} us"


def test_garbage_observations_never_raise_and_stay_legal():
    h = Hero()
    h.new_table(Rules(), 0, 8)
    rng = random.Random(5)
    for _ in range(300):
        n = rng.randint(1, 9)
        stacks = [rng.choice((0, 0, 5, 100, 2000, -3)) for _ in range(n)]
        bets = [rng.choice((0, 0, 7, 20, 10**6)) for _ in range(n)]
        legal = frozenset(k for k in ActionKind if rng.random() < 0.6)
        obs = Observation(
            hole=tuple(rng.sample(range(52), rng.choice((0, 1, 2, 3)))),
            board=tuple(rng.sample(range(52), rng.choice((0, 2, 3, 4, 5, 6)))),
            street=rng.randint(-1, 5), seat=rng.randint(0, n - 1), button=rng.randint(-2, 10), stacks=stacks,
            bets=bets, in_hand=[rng.random() < 0.5 for _ in range(n)], pot=rng.choice((0, -5, 300)),
            to_call=rng.choice((0, 20, 10**7)), min_raise=rng.choice((0, 40, -1)), max_raise=rng.choice((0, 2000)),
            legal=legal, hand_no=rng.randint(-1, 3), blinds=rng.choice(((10, 20), (0, 0), (20, 10))),
            history=[(rng.randint(-1, 9), rng.choice((F, C, K, R(rng.randint(-5, 5000))))) for _ in range(rng.randint(0, 6))],
        )
        a = h.act(obs)
        assert isinstance(a, Action)
        if legal:
            assert a.kind in legal or (a.kind is ActionKind.FOLD)
        if a.kind is ActionKind.RAISE:
            assert obs.min_raise <= a.amount <= obs.max_raise or obs.min_raise > obs.max_raise
        h.hand_end(HandResult(obs.hand_no, [rng.randint(-100, 100) for _ in range(n)], {}, (), obs.history))
    h.new_table(Rules(), 0, 8)


def test_aa_opens_and_four_bets(hero):
    a = hero.act(preflop_obs("Ah Ad", 2))
    assert a.kind is ActionKind.RAISE
    obs = preflop_obs("Ah Ad", 2, actions=[(2, R(50))] + FOLDS(3, 4) + [(5, R(160))] + FOLDS(6, 7, 0, 1))
    a = hero.act(obs)
    assert a.kind is ActionKind.RAISE and a.amount >= 320


def test_72o_folds_from_early_position(hero):
    assert hero.act(preflop_obs("7h 2d", 2)) == F


def test_six_bb_button_shoves_a9o_and_folds_83o():
    h = Hero()
    h.new_table(Rules(), 7, 8)
    st = [2000] * 8
    st[7] = 120
    folded = FOLDS(2, 3, 4, 5, 6)
    assert h.act(preflop_obs("Ah 9d", 7, stacks=st, actions=folded)) == R(120)
    assert h.act(preflop_obs("8h 3d", 7, stacks=st, actions=folded)) == F


def test_dead_seat_gets_shoved_into():
    h = Hero()
    h.new_table(Rules(), 7, 8)
    prof: Profiler = h.core.prof
    for s in (0, 1):  # both blinds have folded to every bet they faced
        prof.pre_faced[s] = prof.pre_folded[s] = prof.actions[s] = 6
    for s in range(8):
        prof._dials[s] = prof._compute_dials(s)
    st = [2000] * 8
    st[7] = 160
    obs = preflop_obs("7h 2d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))
    assert h.act(obs) == R(obs.max_raise)
    # postflop too: a dead seat only reaches a flop when it was checked to (here: hero limped, BB checked);
    # facing a bet it folds, so bet anything
    flop = street_obs("7c 2d", "Ks 9d 2h", 7, pot=50, in_hand=[False, True, False, False, False, False, False, True],
                      history=[(7, C), (0, F), (1, K), (1, K)])
    assert h.act(flop).kind is ActionKind.RAISE


def test_cheap_variant_is_minimal_but_sound():
    h = Hero.cheap()
    assert h.config.cheap and h.core.prof is None
    h.new_table(Rules(), 2, 8)
    assert h.act(preflop_obs("Ah Ad", 2)).kind is ActionKind.RAISE
    assert h.act(preflop_obs("Kh 9d", 7, actions=FOLDS(2, 3, 4, 5, 6))) == F
    st = [2000] * 8
    st[7] = 120
    h.new_table(Rules(), 7, 8)
    assert h.act(preflop_obs("Ah 9d", 7, stacks=st, actions=FOLDS(2, 3, 4, 5, 6))) == R(120)
    flop = street_obs("7c 6d", "Ks 9d 2h", 7, pot=120, in_hand=[False, True, False, False, False, False, False, True],
                      history=[(7, R(50)), (1, C), (1, K)])
    assert h.act(flop) == K


def test_panic_mode_switches_to_cheap_paths():
    h = Hero(Config(panic_after=1, panic_rate=0.0, deadline_ms=0.0))  # every call overruns a zero budget
    h.new_table(Rules(), 7, 8)
    h.act(preflop_obs("7h 2d", 7))
    assert h.safe.panic_mode and h.core.panic
    h.new_table(Rules(), 7, 8)
    assert not h.core.panic


def test_icm_curve_is_concave_and_updates_at_hand_end():
    h = Hero()
    h.new_table(Rules(), 0, 8)
    c = h.core.curve
    assert c.xs[0] == 0 and c.vs[0] == 1.0  # busting 8th now is worth the 8th-place point
    slopes = [(c.vs[i + 1] - c.vs[i]) / (c.xs[i + 1] - c.xs[i]) for i in range(len(c.vs) - 1)]
    assert all(g > 0 for g in slopes) and all(slopes[i] >= slopes[i + 1] - 2e-5 for i in range(len(slopes) - 1))
    assert c.xs[-1] == 16000 and c.vs[-1] == 8.0 and c.value(50000) == 8.0  # every chip = first place, and no more
    assert c.value(2000) == pytest.approx(36 / 8)  # equal stacks: average of all payouts
    h.act(preflop_obs("Ah Ad", 0, hand_no=0))
    h.hand_end(HandResult(0, [1000, -1000, 0, 0, 0, 0, 0, 0], {}, (), []))
    assert h.core.last_stacks[0] == 3000 and c.xs[2] == 3000
    assert c.value(3000) > 36 / 8
    # the eight-handed risk premium: AK (65%) doubling up is worth less than the stack it risks
    v = c.value
    assert 0.65 * v(6000) + 0.35 * v(0) < v(3000) < 0.82 * v(6000) + 0.18 * v(0)


def test_icm_curve_handles_degenerate_stacks():
    c = IcmCurve()
    c.compute([0, 0, 500, 0], 2, (8, 7, 6, 5), (0.0, 1.0, 2.0))
    assert c.value(500) == pytest.approx(8.0)
    c.compute([0, 0, 0, 0], 1, (8, 7), (0.0, 1.0))
    assert c.value(10) == 0.0


def test_core_routes_streets_and_remaps_variants():
    core = HeroCore(Config(seed=1))
    order = (12,) + tuple(range(12))  # deuces are the top rank
    core.new_table(Rules(rank_order=order), 2, 8)
    # displayed 22 is really AA: it must open under the gun
    assert core.act(preflop_obs("2h 2d", 2)).kind is ActionKind.RAISE
    # displayed AA is really KK: still opens
    assert core.act(preflop_obs("Ah Ad", 2)).kind is ActionKind.RAISE
    core.new_table(Rules(), 2, 8)
    assert core.act(preflop_obs("2h 2d", 2)) == F


def test_permuted_ranks_fifty_strict_tables_no_exceptions():
    """Under a permuted rank order hero remaps hole and board; every module must see canonical cards
    (postflop once read the displayed board next to the canonical hole: duplicate cards, KeyError in
    the evaluator). SafeBot hides such errors from the engine, so the check is on hero.safe.errors."""
    from hyperion.sim.bestiary import make_bot as make_opp
    from hyperion.sim.engine import play_table

    order = (12, 0, 11, 1, 10, 2, 9, 3, 8, 4, 7, 5, 6)  # deuces on top, threes at the bottom, ...
    rules = Rules(rank_order=order)
    heroes = []
    for t in range(50):
        h = Hero(Config(seed=t))
        heroes.append(h)
        bots = [h] + [make_opp(nm, seed=t * 8 + i) for i, nm in enumerate(("tag", "naive", "station", "random", "maniac", "nit", "allin"))]
        res = play_table(bots, rules, seed=1000 + t, mode="strict")
        assert res.stats[0].exceptions == 0 and res.stats[0].illegal == 0
    errors = sum(h.safe.errors for h in heroes)
    assert errors == 0, f"{errors} inner exceptions under a permuted rank order"
