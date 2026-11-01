"""Rival 3's decision core, driven from outside: payouts from Rules, the hand's history at hand_end, a soft deadline.

Nothing in hyperion/sim/rivals/rival3.py is edited. `Rival3Core` subclasses its `Bot` and changes, from here:
  - payouts: rival 3 prices every all-in with `_icm1`, a closed form exact only for the brief's 10/7/5/4/3/2/1/0, and
    its bust value with the same table. Its one ICM method, `_allin` (20 lines), is re-implemented here line for
    line with `icm_points` and `Rules.payouts` in their place. `icm_points` keeps rival 3's O(n) closed form whenever
    the payouts are linear from the third place down (8..1 and the brief's table both are) and uses Hero's exact
    `icm_me` otherwise (top_heavy: ~50 us a call at eight seats, four calls per all-in). Its module globals are
    untouched, so a `rival3` opponent in the same process still plays as built.
  - history at hand_end, in the kit's (seat, (kind, amount)) shape, as its own engine passed it (worth +0.22 to it on
    `holdout`: docs/decisions.md, "Rival 3 in the pool").
  - a soft deadline: if the decision has already used `soft_us` when its preflop or postflop logic would start (the
    history replay ran long or the process was preempted), `SoftDeadline` is raised and Hero's cheap path answers.
  - replay errors, which rival 3 swallows, are counted (`replay_errors`) before its own handler sees them.
Everything else (equity tables, push/fold by ICM, the opponent model and dead-seat detection, postflop rules) is rival 3
as frozen. It has no wall-clock time box and seeds its one RNG at construction, so it is bit-reproducible.
"""
from __future__ import annotations

from time import perf_counter

from ..core.types import HandResult, Rules
from ..sim.rivals import rival3 as R3
from ..strategy.hero import icm_me
from .kit import SoftDeadline


def _linear_from(pays) -> tuple[float, float, int] | None:
    """(A, B, m): pays[p] == A - B * p for every place index p >= m (0 = first), with the smallest such m; None when
    fewer than two places are paid."""
    k = len(pays)
    if k < 2:
        return None
    B = pays[k - 2] - pays[k - 1]
    A = pays[k - 1] + B * (k - 1)
    m = k - 1
    while m > 0 and abs(pays[m - 1] - (A - B * (m - 1))) < 1e-9:
        m -= 1
    return A, B, m


def icm_points(st, i: int, payouts) -> float:
    """My Malmuth-Harville points for stacks `st` (busted seats hold 0). Payouts linear from the third place down:
    E = A - B * E[players ahead] + (pay_1 - A) P(1st) + (pay_2 - (A - B)) P(2nd), all O(n) (rival 3's `_icm1` is the
    brief's case: A 7, B 1, corrections 3 and 1). Otherwise Hero's exact forward pass, `icm_me`."""
    si = st[i]
    if si <= 0:
        return 0.0
    alive = 0
    T = 0.0
    for x in st:
        if x > 0:
            alive += 1
            T += x
    pays = [float(p) for p in payouts[:alive]] + [0.0] * max(0, alive - len(payouts))
    if alive == 1:
        return pays[0]
    lin = _linear_from(pays)
    if lin is None or lin[2] > 2:
        return icm_me(st, i, pays)
    A, B, m = lin
    ahead = 0.0
    p2 = 0.0
    for j, sj in enumerate(st):
        if j == i or sj <= 0:
            continue
        ahead += sj / (si + sj)
        p2 += (sj / T) * si / (T - sj)
    out = A - B * ahead
    if m >= 1:
        out += (pays[0] - A) * (si / T)
    if m >= 2:
        out += (pays[1] - (A - B)) * p2
    return out


class Rival3Core(R3.Bot):
    """Rival 3's `Bot` with payouts, hand_end history and a soft deadline set from outside (module doc). `decide` returns
    its raw ('kind', amount) answer, or None where it declines (as built it would then fold; the caller asks Hero)."""

    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    soft_us = 350.0
    _t0 = 0.0
    replay_errors = 0

    # ------------------------------------------------------------------ the adapter HybridCore drives
    def setup(self, rules: Rules, seat: int, n_players: int, cfg) -> None:
        self.new_table({"starting_stack": rules.starting_stack, "hand_cap": rules.max_hands,
                        "n_players": n_players, "blinds": rules.blind_levels}, seat, n_players)
        self.payouts = tuple(rules.payouts)
        self.soft_us = float(cfg.soft_us)
        self.replay_errors = 0

    def start_hand(self, kit_hand_no: int, totals) -> None:
        """Nothing to precompute: rival 3 prices each all-in from the stacks it sees."""

    def decide(self, kit, t0: float):
        self._t0 = t0
        return self._act(kit)

    def legalize(self, ans, kit):
        return self._legalize(ans, kit)

    @staticmethod
    def best_two(hole: tuple) -> tuple:
        """The two hole cards (canonical) rival 3's own preflop ranking values most (lowest `PCT` percentile)."""
        if len(hole) <= 2:
            return hole
        best, best_p = hole[:2], 2.0
        n = len(hole)
        for i in range(n):
            for j in range(i + 1, n):
                p = R3.PCT[R3._cls((hole[i], hole[j]))]
                if p < best_p:
                    best_p, best = p, (hole[i], hole[j])
        return best

    def end(self, result: HandResult) -> None:
        self.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas,
                       "history": [(s, (a.kind.value, a.amount)) for s, a in result.history]})

    # ------------------------------------------------------------------ overrides
    def _soft(self) -> None:
        if perf_counter() - self._t0 > self.soft_us * 1e-6:
            raise SoftDeadline()

    def _pre(self, *args):
        self._soft()
        return R3.Bot._pre(self, *args)

    def _post(self, *args):
        self._soft()
        return R3.Bot._post(self, *args)

    def _replay(self, hist, o, final=False):
        try:
            return R3.Bot._replay(self, hist, o, final)
        except Exception:
            self.replay_errors += 1
            raise

    def _allin(self, stacks, bets, inh, seat, opp, pot, n_alive):
        """Rival 3's `_allin` (ICM values of fold, steal, win, lose against `opp`) with this table's payouts."""
        pays = self.payouts
        n = len(stacks)
        tot = [stacks[j] + bets[j] for j in range(n)]
        mytot = tot[seat]
        pot_all = pot + sum(bets)
        dead_other = pot_all - bets[seat] - bets[opp]
        c = min(tot[opp], mytot)
        base = list(stacks)
        f = list(base)
        f[opp] += pot_all
        ev_fold = icm_points(f, seat, pays)
        st = list(base)
        st[seat] = mytot + pot_all - bets[seat]
        ev_steal = icm_points(st, seat, pays)
        w = list(base)
        w[seat] = mytot + c + dead_other
        w[opp] = tot[opp] - c
        ev_win = icm_points(w, seat, pays)
        lo = list(base)
        lo[seat] = mytot - c
        lo[opp] = tot[opp] + c + dead_other
        if lo[seat] <= 0:
            place = min(len(pays), max(1, n_alive)) - 1  # busting now: last of the n_alive places
            ev_lose = float(pays[place]) if 0 <= place < len(pays) else 0.0
        else:
            ev_lose = icm_points(lo, seat, pays)
        return ev_fold, ev_steal, ev_win, ev_lose
