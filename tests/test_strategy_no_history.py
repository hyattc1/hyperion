"""Hero behind an adapter that passes no action history (drill 6): the betting state comes from the bets, the
profiler counts nothing it cannot see, and the bot plays close to its full-history self."""
import random
from dataclasses import replace

import pytest

from hyperion.core.types import Action, ActionKind, HandResult, Rules
from hyperion.sim.bestiary import make_bot
from hyperion.sim.engine import play_table
from hyperion.strategy.hero import HeroCore, config_from_dict
from hyperion.strategy.profiler import Profiler
from hyperion.strategy.spot import Spot, history_explains_bets, history_from_bets
from hyperion.strategy.tables import load

from .strategy_helpers import preflop_obs

R, C, F = Action.raise_to, Action.call(), Action.fold()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731


@pytest.fixture(scope="module")
def tables():
    return load(need_hu=True)


def test_raises_are_rebuilt_from_the_bets():
    obs = preflop_obs("Ah 8c", 1, button=7, stacks=[2000] * 8,
                      actions=FOLDS(2, 3, 4) + [(5, R(50)), (6, C), (7, R(150)), (0, F)])
    bare = replace(obs, history=[])
    assert history_explains_bets(obs, 20) and not history_explains_bets(bare, 20)
    rebuilt = history_from_bets(bare, 20)
    assert [(s, a.amount) for s, a in rebuilt] == [(5, 50), (7, 150)]  # the opener and the 3-bettor; the caller is not
    full, inferred = Spot(obs, obs.hole), Spot(replace(obs, history=rebuilt), obs.hole)
    assert (inferred.n_raises, inferred.raiser) == (full.n_raises, full.raiser) == (2, 7)
    unopened = preflop_obs("Ah 8c", 4, button=7, actions=FOLDS(2, 3))
    assert history_explains_bets(replace(unopened, history=[]), 20)  # folded to me: nothing to explain


@pytest.mark.parametrize("hole", ["Ah 8c", "Kh 9c", "7h 2c", "Qh Qd"])
def test_hero_decides_the_same_with_and_without_history(tables, hole):
    """Big blind at 18 bb facing a button open: the inferred state gives the decision the full history gives (the
    profiler is off on both: with history it also reads this hand's raise, which a stripped profiler cannot)."""
    acts = FOLDS(2, 3, 4, 5, 6) + [(7, R(45)), (0, F)]
    obs = preflop_obs(hole, 1, button=7, stacks=[360] * 8, actions=acts)
    a = HeroCore(config_from_dict({"use_profiler": False}, seed=1), tables)
    b = HeroCore(config_from_dict({"use_profiler": False}, seed=1), tables)
    for core in (a, b):
        core.new_table(Rules(), 1, 8)
    assert a.act(obs) == b.act(replace(obs, history=[]))
    assert b.inferred == 1 and a.inferred == 0


def test_profiler_does_not_count_hands_it_never_saw():
    prof = Profiler(8)
    prof.reset(8, 0)
    for h in range(30):
        obs = preflop_obs("Ah Kh", 0, button=7, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(50))], hand_no=h)
        prof.observe(replace(obs, history=[]))
        prof.hand_end(HandResult(h, [0] * 8, {}, (), []))
    assert prof.hands[7] == 0 and not prof.nit(7)  # 30 unseen hands: no VPIP of 0 over 30, no nit flag
    obs = preflop_obs("Ah Kh", 0, button=7, actions=FOLDS(2, 3, 4, 5, 6) + [(7, R(50))], hand_no=40)
    prof.observe(obs)
    prof.hand_end(HandResult(40, [0] * 8, {}, (), obs.history + [(0, F), (1, F)]))
    assert prof.hands[7] == 1 and prof.pfr[7] == 1


class _Stripped:
    """The bestiary Hero behind an adapter that passes no history, neither to act() nor to hand_end()."""

    def __init__(self, inner):
        self.inner = inner

    def new_table(self, rules, seat, n):
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        return self.inner.act(replace(obs, history=[]))

    def hand_end(self, r):
        self.inner.hand_end(HandResult(r.hand_no, r.deltas, r.showdown, r.board, []))


def test_hero_without_history_plays_close_to_hero_with_it():
    """Same deals, Hero's seat with and without history (realistic minus the slow Monte Carlo seats). Drill 6
    measured 3.2 against 5.5 before the bets fallback; the gap must now be a fraction of a point."""
    field = ["hero", "rival1", "tag", "pushfold", "loose_aggro", "nit", "station", "maniac"]
    full, stripped = [], []
    # the modules' inference only: the exploit layer reads the kit's own history and is inert without it
    # (test_strategy_exploit_layer), so with it on the full-history Hero gains what the stripped one cannot
    from hyperion.sim import bestiary

    bestiary.HERO_CONFIG = {"exploit.bet_checked": False, "exploit.steal": False, "exploit.steal_min_fold": 0.0}
    try:
        _play(field, full, stripped)
    finally:
        bestiary.HERO_CONFIG = None
    m_full, m_strip = sum(full) / len(full), sum(stripped) / len(stripped)
    assert m_strip > m_full - 0.6, (m_full, m_strip)
    assert m_strip > 4.8, (m_full, m_strip)


def _play(field, full, stripped):
    for t in range(6):
        rng = random.Random(t)
        seating = field[:]
        rng.shuffle(seating)
        for rot in range(8):
            for out, strip in ((full, False), (stripped, True)):
                bots = [make_bot(nm, seed=t * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
                me = seating.index("hero")
                if strip:
                    bots[me] = _Stripped(bots[me])
                res = play_table(bots, Rules(), seed=5000 + t, rotation=rot, mode="measure")
                out.append(res.points[me])
