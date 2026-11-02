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


# ----- R5: the cheaper hand end computes the same numbers -------------------------------------------------------

def _icm_me_reference(stacks, me, payouts):
    """icm_me as it was before the subset plan (bit tests in the inner loop), for the exact-equality check."""
    from hyperion.strategy.hero import _linear_step

    mine = stacks[me]
    if mine <= 0:
        return 0.0
    opp = [s for i, s in enumerate(stacks) if i != me and s > 0]
    k = len(opp) + 1
    pays = [float(x) for x in payouts[:k]] + [0.0] * max(0, k - len(payouts))
    if k == 1:
        return pays[0]
    step = _linear_step(pays)
    if step is not None:
        acc = 0.0
        for s in opp:
            acc += s / (mine + s)
        return pays[0] - step * acc
    m = len(opp)
    total = float(mine + sum(opp))
    size = 1 << m
    dp, held, cnt = [0.0] * size, [0.0] * size, [0] * size
    dp[0] = 1.0
    out = 0.0
    for mask in range(size):
        if mask:
            low = mask & -mask
            j = low.bit_length() - 1
            prev = mask ^ low
            held[mask] = held[prev] + opp[j]
            cnt[mask] = cnt[prev] + 1
        pr = dp[mask]
        if pr == 0.0:
            continue
        rem = total - held[mask]
        out += pr * mine / rem * pays[cnt[mask]]
        q = pr / rem
        for j in range(m):
            b = 1 << j
            if not mask & b:
                dp[mask | b] += q * opp[j]
    return out


PAYS = ([8, 7, 6, 5, 4, 3, 2, 1], [50, 25, 15, 10, 0, 0, 0, 0], [10, 7, 5, 4, 3, 2, 1, 0], [50, 25, 12, 6, 3, 2, 1, 1],
        [20, 10, 6, 4, 3, 2, 1, 0], [50, 30, 20])


def test_icm_me_is_bit_identical_to_the_bit_test_loop():
    rng = random.Random(5)
    for _ in range(2000):
        n = rng.randint(2, 9)
        st = [rng.randint(1, 6000) if rng.random() > 0.2 else 0 for _ in range(n)]
        me = rng.randrange(n)
        p = rng.choice(PAYS)
        assert icm_me(st, me, p) == _icm_me_reference(st, me, p)


def test_curve_is_bit_identical_to_pricing_every_point_with_icm_value():
    from hyperion.strategy.hero import Config, IcmCurve, icm_value

    cfg = Config()

    def reference(stacks, me, payouts, ratios):
        total = float(sum(s for s in stacks if s > 0))
        base = float(stacks[me])
        alive = sum(1 for s in stacks if s > 0)
        pays = list(payouts) + [0.0] * max(0, alive - len(payouts))
        bust = float(pays[alive - 1])
        others = total - base
        xs, vs = [], []
        for x in [base * r for r in ratios]:
            x = min(x, total)
            if x <= 0:
                v = bust
            else:
                scale = (total - x) / others if others > 0 else 0.0
                st = [x if s == me else (stacks[s] * scale if stacks[s] > 0 else 0) for s in range(len(stacks))]
                v = icm_value(st, me, pays, cfg.icm_buckets, cfg.icm_me_subdiv)
            if xs and x <= xs[-1]:
                continue
            xs.append(x)
            vs.append(v)
        if xs[-1] < total:
            xs.append(total)
            vs.append(float(pays[0]))
        return xs, vs

    rng = random.Random(9)
    c = IcmCurve()
    for _ in range(400):
        n = rng.randint(2, 8)
        st = [rng.randint(1, 8000) if rng.random() > 0.2 else 0 for _ in range(n)]
        me = rng.randrange(n)
        if st[me] == 0 or sum(1 for s in st if s > 0) < 2:
            continue
        p = rng.choice(PAYS)
        ratios = rng.choice((cfg.icm_ratios, cfg.icm_ratios_many))
        c.compute(st, me, p, ratios, cfg.icm_buckets, cfg.icm_me_subdiv)
        assert (c.xs, c.vs) == reference(st, me, p, ratios)


def test_lazy_dials_read_as_the_eager_ones():
    """Profiler.lazy: a seat's dials computed on first read, the rest settled before the next observe changes a
    counter: every read equals the eager profiler's (two profilers fed one recorded table)."""
    from hyperion.strategy.profiler import Profiler

    recs = [_Rec(s) for s in range(8)]
    play_table(recs, Rules(max_hands=80), seed=3, mode="model")
    log = recs[0].log
    eager, lazy = Profiler(8), Profiler(8)
    lazy.lazy = True
    rng = random.Random(1)
    reads = 0
    for ev in log:
        if ev[0] == "nt":
            eager.reset(ev[3], ev[2])
            lazy.reset(ev[3], ev[2])
        elif ev[0] == "act":
            eager.observe(ev[1])
            lazy.observe(ev[1])
            for s in rng.sample(range(8), 3):
                assert lazy.exploit_dials(s) == eager.exploit_dials(s)
                reads += 1
        else:
            eager.hand_end(ev[1])
            lazy.hand_end(ev[1])
            s = rng.randrange(8)
            assert lazy.exploit_dials(s) == eager.exploit_dials(s)
    assert reads > 50
