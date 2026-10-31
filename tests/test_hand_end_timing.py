"""hand_end and new_table stay under 1 ms at p99 at a table of strong bots.

The per-hand ICM curve used to run exact eight-player Malmuth-Harville at every sample (6.4 ms per hand_end
at a table of seven Heroes). Now `icm_me` computes only my points: closed form for linear payouts (exact),
a forward pass over opponent subsets otherwise. Method: record a table of eight Heroes once, then replay each
seat's exact call sequence on three fresh Heroes and keep each call's minimum (this box runs other jobs; a
preempted call reports the scheduler, not the bot)."""
import copy
import random
import time

from hyperion.core.icm import icm_equity
from hyperion.core.types import Rules
from hyperion.sim.engine import play_table
from hyperion.strategy.hero import Config, Hero, _icm_bucketed, icm_me


class _Rec:
    def __init__(self, seed):
        self.bot = Hero(Config(seed=seed))
        self.log = []

    def new_table(self, rules, seat, n):
        self.log.append(("nt", rules, seat, n))
        self.bot.new_table(rules, seat, n)

    def act(self, obs):
        self.log.append(("act", copy.copy(obs)))
        return self.bot.act(obs)

    def hand_end(self, result):
        self.log.append(("he", copy.copy(result)))
        self.bot.hand_end(result)


def _replay(log, seed, reps=3):
    he_best, nt_best = None, None
    for _ in range(reps):
        _icm_bucketed.cache_clear()  # each replay starts cold: a warm memo would time cache hits, not the curve
        bot = Hero(Config(seed=seed))
        he, nt = [], []
        for ev in log:
            if ev[0] == "nt":
                t = time.perf_counter()
                bot.new_table(ev[1], ev[2], ev[3])
                nt.append(time.perf_counter() - t)
            elif ev[0] == "act":
                bot.act(ev[1])
            else:
                t = time.perf_counter()
                bot.hand_end(ev[1])
                he.append(time.perf_counter() - t)
        he_best = he if he_best is None else [min(a, b) for a, b in zip(he_best, he)]
        nt_best = nt if nt_best is None else [min(a, b) for a, b in zip(nt_best, nt)]
    return he_best, nt_best


def _p(xs, q):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(q * len(xs)))]


def _measure(rules, seed):
    recs = [_Rec(seed + s) for s in range(8)]
    play_table(recs, rules, seed=seed, mode="measure")
    he, nt = [], []
    for s, r in enumerate(recs):
        a, b = _replay(r.log, seed + s)
        he += a
        nt += b
    return he, nt


def test_hand_end_and_new_table_p99_under_one_ms():
    for rules, label in ((Rules(), "default 8..1"), (Rules(payouts=(20, 10, 6, 4, 3, 2, 1, 0)), "top-heavy")):
        he, nt = _measure(rules, 11)
        print(f"\n{label}: hand_end n={len(he)} mean {sum(he) / len(he) * 1e6:.0f} us p99 {_p(he, 0.99) * 1e6:.0f} us "
              f"max {max(he) * 1e6:.0f} us | new_table n={len(nt)} p99 {_p(nt, 0.99) * 1e6:.0f} us")
        assert _p(he, 0.99) < 1e-3, label
        assert _p(nt, 0.99) < 1e-3, label


def test_icm_me_matches_the_full_recursion():
    rng = random.Random(4)
    for _ in range(300):
        n = rng.randint(2, 8)
        st = [rng.randint(1, 5000) if rng.random() > 0.15 else 0 for _ in range(n)]
        if sum(1 for s in st if s > 0) < 2:
            continue
        pays = rng.choice(([8, 7, 6, 5, 4, 3, 2, 1], [50, 30, 20], [20, 10, 6, 4, 3, 2, 1, 0], [10, 7, 5, 3, 2, 1, 1, 1]))
        eq = icm_equity(st, pays)
        for i in range(n):
            if st[i] > 0:
                assert abs(icm_me(st, i, pays) - eq[i]) < 1e-9
