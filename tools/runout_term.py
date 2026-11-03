"""The all-in runout term: climb_accept's --runout-term (docs/research/Edges against strong opponents.md, item 6).

What it removes. When a hand's last decision is made with board cards still to come and two or more players still in (an
all-in before the river), the rest of the board is pure chance, and every seat's points carry that chance. For each such
hand the term is, per seat,

    V(the post-hand stacks of the actual runout) - mean of V over every runout the unseen cards could have made

and a seat's corrected points for the table are its points minus the sum of its terms over the table's hands. Every
seat alive at the hand gets a term, not only the two in the pot: a bust moves everyone up the ladder.

V, fixed before any data: each seat's ICM points on the post-hand stacks over the cell's points table (Rules.payouts),
a seat busted in the hand placed as the engine places it (more chips at hand start = the better place) and given that
place's points. Why the corrected mean is unbiased: given everything before the event (all hole cards dealt, the board
so far, every decision), the cards still to come are uniform over the cards nobody has seen, so each term has mean zero
whatever V is; V only decides how much noise the term removes.

The runouts: every combination of the cards to come when there are at most MAX_ENUM (the turn, 1 card, and the flop, 2
cards), else SAMPLES draws without replacement (preflop, 5 cards) from a generator seeded by (table seed, rotation,
hand) alone: never the table's streams. Outcomes are grouped by who beats whom, so V (ICM) runs once per distinct
outcome.

How it records. RunoutTable is the engine's Table with three read-only overrides: `_ask` notes the board at the hand's
last decision, `_award` keeps the stacks before the pots are paid, and `_finish_hand` computes the term after the
engine has finished the hand. Nothing is drawn from the table's generators and nothing a bot sees changes, so play is
the engine's exactly (tests/test_runout_term.py; climb_accept also checks every term cell's raw samples against the plain
cell of the same key when it is cached). It lives outside hyperion/ so the code version, and every cache, stays as is.

Where it applies: hold'em under any Rules, and twists whose hooks leave the hand alone after the last decision (no
on_street, on_payout, next_card or settle: score_hand, score_splits, on_deal, extras, on_bust and the deal's charges are
fine). Elsewhere the term is zero and the corrected sample is the raw one; of the catalog, toss_or_holdem,
three_card_blind_discard, swap_holdem, swap_one_turn, two_boards, bonus_card, auction, deal5_keep2, bounty and
river_of_blood.
"""
from __future__ import annotations

import hashlib
import os
import random
from itertools import combinations
from math import comb

from hyperion.core.icm import icm_equity
from hyperion.sim.engine import HandState, Table
from hyperion.sim.engine import Variant as EngineVariant

MAX_ENUM = 1100  # enumerate when the runouts number at most this (every turn and flop all-in), else sample
SAMPLES = 50  # runouts drawn for a preflop all-in
_HERE = os.path.abspath(__file__)


def version() -> str:
    """This file's content: the term's own cache tag (climb_accept's code version reads hyperion/ and swap.py only)."""
    with open(_HERE, "rb") as fh:
        return hashlib.md5(fh.read()).hexdigest()[:8]


def neutral(hooks) -> bool:
    """Whether the hand after its last decision is the engine's own: the runout and the award alone decide it."""
    if hooks is None:
        return True
    if isinstance(hooks, EngineVariant):  # an engine Variant passed directly: only the base class is known
        return type(hooks) is EngineVariant
    from hyperion.drills.variants import VariantHooks

    t = type(hooks)
    if any(getattr(t, m, None) is not getattr(VariantHooks, m) for m in ("on_street", "on_payout")):
        return False
    return not any(callable(getattr(hooks, m, None)) for m in ("next_card", "settle"))


def _ranks(vals) -> tuple:
    """Dense ranks of a column of scores (0 = best; None stays None): the award depends on these alone."""
    order = sorted({v for v in vals if v is not None}, reverse=True)
    idx = {v: i for i, v in enumerate(order)}
    return tuple(None if v is None else idx[v] for v in vals)


class RunoutTable(Table):
    """Table, plus the runout term per seat in `rt_corr` (summed over the table's events) and `rt_log`, one
    (hand, cards to come, runouts, term per seat) per event."""

    def __init__(self, bots, rules=None, seed=0, rotation=0, mode="strict", variant=None, stats=None, stacks=None):
        super().__init__(bots, rules, seed, rotation, mode, variant, stats, stacks)
        self.rt_on = neutral(variant)
        self.rt_seed = seed
        self.rt_corr = [0.0] * self.n
        self.rt_log: list = []
        self._rt_hand = -1  # the hand of the last decision seen ...
        self._rt_seen = 0  # ... and the board cards at it
        self._rt_pre = None  # stacks before this hand's award

    def _ask(self, s, obs):
        self._rt_hand = obs.hand_no
        self._rt_seen = len(obs.board)
        return super()._ask(s, obs)

    def _award(self, hs):
        if self.rt_on:
            self._rt_pre = self.stacks[:]
        super()._award(hs)

    def _finish_hand(self, hs):
        pre, self._rt_pre = self._rt_pre, None
        start = hs.stacks_start
        super()._finish_hand(hs)
        if pre is None or hs.n_in_hand < 2:
            return
        seen = self._rt_seen if self._rt_hand == hs.hand_no else self.rules.board_sizes[0]
        if len(hs.board) > seen:
            self._rt_event(hs, pre, start, seen)

    # ----- the term
    def _rt_post(self, hs, pre, board) -> list:
        """The stacks after the award had the board been `board`: the engine's own award on a copy of the hand."""
        sh = HandState()
        sh.hand_no, sh.button, sh.holes, sh.board = hs.hand_no, hs.button, hs.holes, board
        sh.contrib, sh.in_hand, sh.dead, sh.showdown = hs.contrib, hs.in_hand, hs.dead, {}
        saved = self.stacks
        self.stacks = list(pre)
        try:
            Table._award(self, sh)
            return self.stacks
        finally:
            self.stacks = saved

    def _rt_value(self, post, start) -> list:
        """V per seat: ICM points on the post-hand stacks; a seat busted in the hand gets its place's points."""
        pay = self.rules.payouts
        alive = sum(1 for x in start if x > 0)
        busted = sorted((s for s in range(self.n) if start[s] > 0 and post[s] == 0), key=lambda s: (-start[s], s))
        remaining = alive - len(busted)
        v = icm_equity(post, pay)
        for i, s in enumerate(busted):
            v[s] = float(pay[remaining + i]) if remaining + i < len(pay) else 0.0
        return v

    def _rt_event(self, hs, pre, start, seen) -> None:
        n, rules, board = self.n, self.rules, hs.board
        known, m = board[:seen], len(board) - seen
        dealt = set(known)
        for s in range(n):
            if start[s] > 0:
                dealt.update(hs.holes[s])
        unseen = sorted(c for c in self.deck if c not in dealt)
        contenders = [s for s in range(n) if hs.in_hand[s]]
        holes = hs.holes
        splits, ev = self.variant.splits, self.variant.evaluate
        cache: dict = {}

        def value(b):
            if splits is None:
                sig = _ranks([ev(holes[s], b, rules) for s in contenders])
            else:
                sig = tuple(_ranks(col) for col in zip(*(tuple(splits(holes[s], b, rules)) for s in contenders)))
            v = cache.get(sig)
            if v is None:
                v = cache[sig] = self._rt_value(self._rt_post(hs, pre, b), start)
            return v

        actual = value(board)
        if self._rt_post(hs, pre, board) != self.stacks:  # the model of the hand's end must be the engine's
            raise RuntimeError(f"runout term: the award model missed the engine's stacks (hand {hs.hand_no})")
        total = comb(len(unseen), m)
        if total <= MAX_ENUM:
            runouts, count = combinations(unseen, m), total
        else:
            rng = random.Random(f"runout/{self.rt_seed}/{self.rotation}/{hs.hand_no}")
            runouts, count = (rng.sample(unseen, m) for _ in range(SAMPLES)), SAMPLES
        acc = [0.0] * n
        for r in runouts:
            v = value(known + tuple(r))
            for s in range(n):
                acc[s] += v[s]
        corr = [actual[s] - acc[s] / count for s in range(n)]
        for s in range(n):
            self.rt_corr[s] += corr[s]
        self.rt_log.append((hs.hand_no, m, count, tuple(corr)))


def run_tournament_rt(names, tables, **kw):
    """hyperion.sim.runner.run_tournament with every table a RunoutTable: (report, corrected samples per name, events
    per name). The report is run_tournament's own; a name's corrected sample for a table seed is the mean over its seats
    and rotations of points minus the seat's term, in the report's order (its raw samples are checked against it)."""
    from hyperion.sim import runner

    log = []

    def play_table(bots, rules=None, seed=0, rotation=0, mode="strict", variant=None, stats=None, stacks=None):
        t = RunoutTable(bots, rules, seed, rotation, mode, variant, stats, stacks)
        res = t.play()
        log.append((seed, [st.name for st in stats], res.points, t.rt_corr, t.rt_log))
        return res

    orig = runner.play_table
    runner.play_table = play_table
    try:
        rep = runner.run_tournament(names, tables, **kw)
    finally:
        runner.play_table = orig
    corrected = {nm: [] for nm in rep.bots}
    events = {nm: [] for nm in rep.bots}
    raw = {nm: [] for nm in rep.bots}
    i = 0
    while i < len(log):
        seed = log[i][0]
        j = i
        while j < len(log) and log[j][0] == seed:
            j += 1
        pts = {nm: [] for nm in rep.bots}
        cor = {nm: [] for nm in rep.bots}
        nev = {nm: 0 for nm in rep.bots}
        for _, seats, points, corr, elog in log[i:j]:
            for s, nm in enumerate(seats):
                pts[nm].append(points[s])
                cor[nm].append(points[s] - corr[s])
                nev[nm] += sum(1 for e in elog if e[3][s] != 0.0)
        for nm in rep.bots:
            if pts[nm]:
                raw[nm].append(sum(pts[nm]) / len(pts[nm]))
                corrected[nm].append(sum(cor[nm]) / len(cor[nm]))
                events[nm].append(nev[nm])
        i = j
    for nm, b in rep.bots.items():
        if raw[nm] != b.samples:
            raise RuntimeError(f"runout term: {nm}'s raw samples differ from the report's")
    return rep, corrected, events
