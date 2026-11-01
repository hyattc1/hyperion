"""Rival 2's decision core, driven from outside: the kit-shaped observation it was built against, the ICM curve
from the table's payouts, and a postflop sampler with a tighter budget and a soft deadline.

Nothing in hyperion/sim/rivals/rival2.py is edited or copied. `Rival2Core` subclasses its `Bot` and changes
three things, all from here:
  - payouts: rival 2 hard-codes the brief's 10/7/5/4/3/2/1/0 (`PTS`) in its per-hand ICM curve. The curve is
    built here instead, at rival 2's own knots (0, 0.5, 0.9, 1, 1.1, 2 x my stack, all the chips), from
    `Rules.payouts` and the exact hand-start chips, with Hero's exact `icm_value`. It is built in hand_end
    (outside the decision clock: rival 2 built it inside the first decision of each hand, ~115 us p50 and
    ~500 us p99 at eight seats) and handed to the core when the next hand starts. Its module globals are
    untouched, so a `rival2` opponent in the same process still plays as built.
  - the sampler: `MC_MAX` samples (rival 2: 160, normally cut by its 260 us clock at ~110 heads-up), a wall
    budget from the start of the decision, and a hard stop; all three per instance.
  - a soft deadline: if the decision has already used `soft_us` when the sampler would start (the process was
    preempted), `SoftDeadline` is raised and the caller answers with Hero's cheap path instead.
Everything else (preflop, push/fold, re-shoves, opponent model, postflop thresholds) is rival 2 as frozen.
"""
from __future__ import annotations

from time import perf_counter

from ..core.types import Action, Observation
from ..sim.rivals import rival2 as R2
from ..strategy.hero import icm_value

_KIT_ACTIONS = {"fold": Action.fold(), "check": Action.check(), "call": Action.call()}
_KIT_LEGAL: dict = {}  # frozenset[ActionKind] -> set of strings, memoized
KNOTS = (0.5, 0.9, 1.0, 1.1, 2.0)  # rival 2's curve knots, multiples of my hand-start chips


class SoftDeadline(Exception):
    """The decision is already late when the core's sampler would start: answer with Hero's cheap path."""


class KitObs:
    """The observation shape rival 2 was built against (red-team brief, kit.py): our fields with `legal` a set of
    strings, `history` a list of (seat, (kind, amount)) and `hand_no` 1-based."""

    __slots__ = ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot",
                 "to_call", "min_raise", "max_raise", "legal", "hand_no", "blinds", "history")


class KitView:
    """Converts our Observation to KitObs. History is converted incrementally (the prefix never changes within a
    hand). `hole` and `board` are passed in already mapped to canonical strength."""

    __slots__ = ("_hist", "_hist_n", "_hist_hand")

    def __init__(self):
        self.reset()

    def reset(self) -> None:
        self._hist, self._hist_n, self._hist_hand = [], 0, -1

    def __call__(self, obs: Observation, hole: tuple, board: tuple) -> KitObs:
        k = KitObs()
        k.hole, k.board, k.street, k.seat, k.button = hole, board, obs.street, obs.seat, obs.button
        k.stacks, k.bets, k.in_hand, k.pot = obs.stacks, obs.bets, obs.in_hand, obs.pot
        k.to_call, k.min_raise, k.max_raise = obs.to_call, obs.min_raise, obs.max_raise
        k.hand_no, k.blinds = obs.hand_no + 1, obs.blinds
        legal = _KIT_LEGAL.get(obs.legal)
        if legal is None:
            legal = _KIT_LEGAL[obs.legal] = {kind.value for kind in obs.legal}
        k.legal = legal
        src = obs.history
        n = len(src)
        if obs.hand_no != self._hist_hand or n < self._hist_n:
            self._hist, self._hist_n, self._hist_hand = [], 0, obs.hand_no
        if n > self._hist_n:
            self._hist.extend((s, (a.kind.value, a.amount)) for s, a in src[self._hist_n:])
            self._hist_n = n
        k.history = self._hist
        return k


def from_kit(answer, obs: Observation) -> Action | None:
    """('kind', raise-to total) -> a legal Action; None when the answer is unreadable."""
    try:
        kind, amount = answer
    except (TypeError, ValueError):
        return None
    if kind == "raise":
        try:
            return Action.raise_to(int(amount)).clamp(obs)
        except (TypeError, ValueError):
            return None
    a = _KIT_ACTIONS.get(kind)
    return a.clamp(obs) if a is not None else None


def build_curve(totals, me: int, payouts) -> R2.Curve:
    """Rival 2's per-hand ICM curve (its `build_curve`, same knots and shape) with `payouts` in place of its
    hard-coded table: expected points of my chip count, the other stacks scaled pro rata, exact Malmuth-Harville."""
    alive = [i for i in range(len(totals)) if totals[i] > 0]
    n = len(alive)
    T = float(sum(totals[i] for i in alive))
    s0 = float(totals[me]) if 0 <= me < len(totals) else 0.0
    if n <= 1 or s0 <= 0:
        return R2.Curve([0.0, 1.0], [0.0, 0.0])
    pts = [float(p) for p in payouts[:n]] + [0.0] * max(0, n - len(payouts))
    u0, uT = pts[-1], pts[0]
    if n == 2:
        return R2.Curve([0.0, T], [u0, uT])
    idx = alive.index(me)
    others = [float(totals[i]) for i in alive if i != me]
    rest = T - s0
    xs, us = [0.0], [u0]
    for m in KNOTS:
        x = m * s0
        if x >= T - 1e-9:
            continue
        scale = (T - x) / rest if rest > 0 else 0.0
        st = [o * scale for o in others]
        st.insert(idx, x)
        xs.append(x)
        us.append(icm_value(st, idx, pts))
    xs.append(T)
    us.append(uT)
    for i in range(1, len(us)):  # monotone, as rival 2 enforces
        if us[i] < us[i - 1]:
            us[i] = us[i - 1]
    return R2.Curve(xs, us)


class Rival2Core(R2.Bot):
    """Rival 2's `Bot` with the payout curve, sampler budget and soft deadline set from outside (module doc).
    `decide(kit, t0)` returns its raw ('kind', amount) answer and lets exceptions through: the caller falls back to
    Hero instead of rival 2's own check-or-fold."""

    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    mc_max = 64
    mc_min = 16
    budget_us = 200.0
    hard_us = 450.0
    soft_us = 350.0
    _pending = None  # (kit hand_no, totals, curve) for the hand about to start
    _t0 = 0.0
    inline_curves = 0  # hands whose curve had to be built inside a decision (should stay 0)

    def configure(self, payouts, mc_max: int, mc_min: int, budget_us: float, hard_us: float, soft_us: float) -> None:
        self.payouts = tuple(payouts)
        self.mc_max, self.mc_min = int(mc_max), int(mc_min)
        self.budget_us, self.hard_us, self.soft_us = float(budget_us), float(hard_us), float(soft_us)
        self.MC_MAX = self.mc_max
        self.MC_MIN = self.mc_min
        self.MC_BUDGET_US = self.budget_us

    def prime(self, kit_hand_no: int, totals) -> None:
        """Build the curve for the hand that starts next from its exact starting chips (called outside the clock)."""
        self._pending = (kit_hand_no, list(totals), build_curve(totals, self.me, self.payouts))

    def decide(self, kit: KitObs, t0: float):
        self._t0 = t0
        hn = kit.hand_no
        if hn != self.cur:
            self._finish_hand()
            self._new_hand(hn)
            self.hands_seen += 1
            p = self._pending
            stacks, bets = kit.stacks, kit.bets
            chips = sum(stacks) + sum(bets) + (kit.pot or 0)
            if p is not None and p[0] == hn and abs(sum(p[1]) - chips) < 1.0:
                self.totals, self.curve = p[1], p[2]
            else:  # no primed curve (custom stacks, a missed hand_end): rival 2's own totals, our payouts
                n = len(stacks)
                nin = max(1, sum(1 for i in range(n) if kit.in_hand[i]))
                pot = kit.pot or 0
                self.totals = [stacks[i] + bets[i] + (pot / nin if kit.in_hand[i] else 0) for i in range(n)]
                self.curve = build_curve(self.totals, kit.seat, self.payouts)
                self.inline_curves += 1
            self._pending = None
        return self._act(kit)

    def equity_mc(self, hole, board, cuts, deadline, fits=None, hard=None):
        t0 = self._t0
        if perf_counter() - t0 > self.soft_us * 1e-6:
            raise SoftDeadline()
        return R2.Bot.equity_mc(self, hole, board, cuts, t0 + self.budget_us * 1e-6, fits, t0 + self.hard_us * 1e-6)


def best_two(hole: tuple) -> tuple:
    """The two cards (canonical) the core values most by its own preflop ranking (equity against one random hand)."""
    if len(hole) <= 2:
        return hole
    best, best_p = hole[:2], 2.0
    n = len(hole)
    for i in range(n):
        for j in range(i + 1, n):
            p = R2.P1[R2.CLS[hole[i] * 52 + hole[j]]]
            if p < best_p:
                best_p, best = p, (hole[i], hole[j])
    return best
