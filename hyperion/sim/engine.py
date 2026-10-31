"""No-limit hold'em sit-and-go engine for 2..8 fixed seats, driven by Rules.

What it does: moving button, blinds from Rules.blinds_at (hand_no is 0-based, so hand 25 is
level 1), no antes, min-raise and short-all-in rules, side pots, ties with odd chips, bust-outs,
finishing points with ICM at the hand cap, reproducible and duplicate dealing, and enforcement
around every bot call (exceptions, time budget, illegal actions).

Conventions, also recorded in docs/decisions.md:
- Button: moves to the next live seat each hand. Small blind is the next live seat after it, big
  blind the next after that; heads-up the button posts the small blind. No dead button, so a seat
  can skip a blind after a bust-out. The real engine's choice is unknown.
- A blind shorter than the full post is posted for less; the amount to call is the largest actual
  bet on the street.
- A raise is full when its increment is at least the last full increment this street (the big
  blind to start). A short all-in raise does not reopen action for players who already acted:
  they may call or fold. Several short all-ins adding up to a full raise do not reopen either.
- Raising is illegal when no opponent left in the hand has chips to respond.
- Observation.to_call is capped at the player's stack (what a call actually costs them).
- History holds decisions only; blind posts show up in bets and contributions.
- Illegal actions from a bot are clamped with Action.clamp and counted in BotStats.illegal.
- Duplicate dealing: the deck for hand h depends only on (seed, h). Deal slot j holds a fixed run
  of cards; seat s receives slot (s - rotation) mod n, and the first button is seat `rotation`, so
  rotation k is rotation 0 with every seat relabelled by +k.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from time import perf_counter_ns
from typing import Optional, Sequence

from ..core.cards import deck_for, is_identity_order, remap
from ..core.eval import evaluate, warm
from ..core.icm import icm_equity
from ..core.types import Action, ActionKind, Bot, HandResult, Observation, Rules

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
A_FOLD, A_CHECK, A_CALL = Action.fold(), Action.check(), Action.call()
LEGAL_CHECK = frozenset((FOLD, CHECK))
LEGAL_CHECK_RAISE = frozenset((FOLD, CHECK, RAISE))
LEGAL_CALL = frozenset((FOLD, CALL))
LEGAL_CALL_RAISE = frozenset((FOLD, CALL, RAISE))

BUDGET_NS = 1_000_000  # the tournament's 1 ms per decision
_HIST_BUCKETS = 10_000  # 1 us buckets up to 10 ms, then one overflow bucket


class BotStats:
    """Latency and enforcement counters for one bot, accumulated across tables.

    The first act() of each table is kept apart (first_*) because imports and table warm-up land
    there; it still counts toward over_budget, as it would in the real engine.
    """

    __slots__ = (
        "name", "calls", "sum_ns", "max_ns", "hist", "over_budget", "exceptions", "illegal",
        "first_calls", "first_sum_ns", "first_max_ns", "last_error", "_fresh",
    )

    def __init__(self, name: str = "bot"):
        self.name = name
        self.calls = 0
        self.sum_ns = 0
        self.max_ns = 0
        self.hist = [0] * (_HIST_BUCKETS + 1)
        self.over_budget = 0
        self.exceptions = 0
        self.illegal = 0
        self.first_calls = 0
        self.first_sum_ns = 0
        self.first_max_ns = 0
        self.last_error = ""
        self._fresh = True

    def new_table(self) -> None:
        self._fresh = True

    def record(self, ns: int) -> None:
        if ns > BUDGET_NS:
            self.over_budget += 1
        if self._fresh:
            self._fresh = False
            self.first_calls += 1
            self.first_sum_ns += ns
            if ns > self.first_max_ns:
                self.first_max_ns = ns
            return
        self.calls += 1
        self.sum_ns += ns
        if ns > self.max_ns:
            self.max_ns = ns
        i = ns // 1000
        self.hist[i if i < _HIST_BUCKETS else _HIST_BUCKETS] += 1

    def merge(self, other: "BotStats") -> None:
        self.calls += other.calls
        self.sum_ns += other.sum_ns
        self.max_ns = max(self.max_ns, other.max_ns)
        h, oh = self.hist, other.hist
        for i in range(len(h)):
            h[i] += oh[i]
        self.over_budget += other.over_budget
        self.exceptions += other.exceptions
        self.illegal += other.illegal
        self.first_calls += other.first_calls
        self.first_sum_ns += other.first_sum_ns
        self.first_max_ns = max(self.first_max_ns, other.first_max_ns)
        self.last_error = self.last_error or other.last_error

    def percentile_us(self, q: float) -> float:
        """q in [0, 1]; resolution 1 us; values beyond 10 ms report as 10000."""
        if self.calls == 0:
            return 0.0
        target = q * self.calls
        seen = 0
        for i, c in enumerate(self.hist):
            seen += c
            if seen >= target:
                return float(i)
        return float(_HIST_BUCKETS)

    @property
    def mean_us(self) -> float:
        return self.sum_ns / self.calls / 1000 if self.calls else 0.0

    @property
    def first_mean_us(self) -> float:
        return self.first_sum_ns / self.first_calls / 1000 if self.first_calls else 0.0


class HandState:
    """Everything about the hand in play. Variants mutate holes/runout/board; tests read contrib."""

    __slots__ = (
        "hand_no", "button", "blinds", "holes", "runout", "board", "stacks_start", "in_hand",
        "n_in_hand", "bets", "contrib", "pot", "current_bet", "last_inc", "history", "showdown",
        "deltas",
    )


class Variant:
    """Hooks for drills. Subclass and override; the default is plain hold'em under Rules."""

    def on_deal(self, hand: HandState, rng: random.Random) -> None:
        """After hole cards and the street-0 board are set, before any action."""

    def on_street(self, hand: HandState, street: int, rng: random.Random) -> None:
        """After hand.board is set for street >= 1, before action."""

    def evaluate(self, hole: Sequence[int], board: Sequence[int], rules: Rules) -> int:
        cards = tuple(hole) + tuple(board)
        if not 5 <= len(cards) <= 8:
            raise ValueError(f"evaluator takes 5..8 cards, got {len(cards)}; override Variant.evaluate")
        if not is_identity_order(rules):
            cards = remap(cards, rules)
        return evaluate(cards)


@dataclass
class TableResult:
    points: list[float]  # per seat
    places: list[int]  # per seat, 0 = winner; survivors at the cap are ordered by chips
    hands: int
    stacks: list[int]
    survived: list[bool]
    stats: list[BotStats]


class Table:
    """One sit-and-go. Call play_hand() until done, or use play_table()."""

    def __init__(
        self,
        bots: Sequence[Bot],
        rules: Optional[Rules] = None,
        seed: int = 0,
        rotation: int = 0,
        mode: str = "strict",
        variant: Optional[Variant] = None,
        stats: Optional[Sequence[BotStats]] = None,
        stacks: Optional[Sequence[int]] = None,
    ):
        if mode not in ("strict", "measure"):
            raise ValueError(f"mode must be strict or measure, got {mode!r}")
        self.bots = list(bots)
        self.n = n = len(self.bots)
        if n < 2:
            raise ValueError("a table needs at least two seats")
        self.rules = rules = rules if rules is not None else Rules()
        self.rotation = rotation % n
        self.strict = mode == "strict"
        self.variant = variant if variant is not None else Variant()
        self.stats = list(stats) if stats is not None else [BotStats(type(b).__name__) for b in self.bots]
        if len(self.stats) != n:
            raise ValueError("one BotStats per seat")
        for st in self.stats:
            st.new_table()
        self.rng = random.Random(seed)  # used for deals only, so hand h's deck depends on (seed, h)
        self.vrng = random.Random(seed * 1_000_003 + 7)  # for variant hooks
        self.deck = list(deck_for(rules))
        self.cards_per_hand = rules.hole_cards * n + rules.board_sizes[-1]
        if self.cards_per_hand > len(self.deck):
            raise ValueError("deck too small for this many seats under these rules")
        warm(min(8, rules.hole_cards + rules.board_sizes[-1]))  # so no bot pays for the lazy tables
        self.stacks = list(stacks) if stacks is not None else [rules.starting_stack] * n
        self.button = (self.rotation - 1) % n  # hand 0's button is seat `rotation`
        self.hand_no = 0
        self.places: list[int] = [-1] * n
        self.points = [0.0] * n
        self.alive_count = sum(1 for s in self.stacks if s > 0)
        self.done = self.alive_count <= 1
        for s, bot in enumerate(self.bots):
            try:
                bot.new_table(rules, s, n)
            except Exception as e:  # noqa: BLE001 - enforcement boundary
                self.stats[s].exceptions += 1
                self.stats[s].last_error = repr(e)

    # ----- driving -----------------------------------------------------------------------------

    def play(self) -> TableResult:
        while not self.done:
            self.play_hand()
        return self.result()

    def result(self) -> TableResult:
        return TableResult(
            points=list(self.points), places=list(self.places), hands=self.hand_no,
            stacks=list(self.stacks), survived=[s > 0 for s in self.stacks], stats=list(self.stats),
        )

    def _after(self, s: int, in_hand: list[bool]) -> int:
        n = self.n
        for _ in range(n):
            s = (s + 1) % n
            if in_hand[s]:
                return s
        raise RuntimeError("no live seat")

    def play_hand(self) -> HandState:
        if self.done:
            raise RuntimeError("table is finished")
        n, rules, stacks = self.n, self.rules, self.stacks
        hs = HandState()
        hs.hand_no = self.hand_no
        hs.blinds = blinds = rules.blinds_at(self.hand_no)
        in_hand = [st > 0 for st in stacks]
        hs.in_hand = in_hand
        hs.n_in_hand = n_in = sum(in_hand)
        b = self._after(self.button, in_hand)
        self.button = hs.button = b
        if n_in == 2:
            sb, bb = b, self._after(b, in_hand)
        else:
            sb = self._after(b, in_hand)
            bb = self._after(sb, in_hand)

        # deal by slots so rotations relabel seats without changing the cards. Partial
        # Fisher-Yates: only the cards actually dealt are shuffled (a quarter of shuffle()'s cost).
        deck = self.deck
        rnd = self.rng.random
        size = len(deck)
        for i in range(self.cards_per_hand):
            j = i + int(rnd() * (size - i))
            deck[i], deck[j] = deck[j], deck[i]
        h, rot = rules.hole_cards, self.rotation
        holes: list[tuple[int, ...]] = [()] * n
        for s in range(n):
            if in_hand[s]:
                j = ((s - rot) % n) * h
                holes[s] = tuple(deck[j : j + h])
        base = n * h
        hs.holes = holes
        hs.runout = deck[base : base + rules.board_sizes[-1]]
        hs.board = tuple(hs.runout[: rules.board_sizes[0]])
        hs.stacks_start = stacks[:]
        hs.bets = bets = [0] * n
        hs.contrib = contrib = [0] * n
        hs.pot = 0
        hs.history = []
        hs.showdown = {}
        self.variant.on_deal(hs, self.vrng)

        for seat, amt in ((sb, blinds[0]), (bb, blinds[1])):
            put = amt if amt < stacks[seat] else stacks[seat]
            stacks[seat] -= put
            bets[seat] += put
            contrib[seat] += put
        hs.current_bet = max(bets)
        hs.last_inc = blinds[1]

        first = self._after(bb, in_hand)
        for street in range(rules.streets):
            if street:
                hs.pot += sum(bets)
                for i in range(n):
                    bets[i] = 0
                hs.current_bet = 0
                hs.last_inc = blinds[1]
                hs.board = tuple(hs.runout[: rules.board_sizes[street]])
                self.variant.on_street(hs, street, self.vrng)
                first = self._after(b, in_hand)
            if self._needs_betting(hs):
                self._betting_round(hs, street, first)
            if hs.n_in_hand == 1:
                break
        self._award(hs)
        self._finish_hand(hs)
        return hs

    # ----- betting -----------------------------------------------------------------------------

    def _needs_betting(self, hs: HandState) -> bool:
        stacks, in_hand, bets = self.stacks, hs.in_hand, hs.bets
        with_chips = 0
        owes = False
        for s in range(self.n):
            if in_hand[s] and stacks[s] > 0:
                with_chips += 1
                if bets[s] < hs.current_bet:
                    owes = True
        return with_chips >= 2 or (with_chips == 1 and owes)

    def _betting_round(self, hs: HandState, street: int, first: int) -> None:
        n, stacks, bets, contrib, in_hand = self.n, self.stacks, hs.bets, hs.contrib, hs.in_hand
        history = hs.history
        need = [in_hand[s] and stacks[s] > 0 for s in range(n)]
        can_raise = [True] * n
        pending = sum(need)
        s = first
        while pending:
            if need[s]:
                need[s] = False
                pending -= 1
                cur = hs.current_bet
                owe = cur - bets[s]
                st = stacks[s]
                responders = False
                for o in range(n):
                    if o != s and in_hand[o] and stacks[o] > 0:
                        responders = True
                        break
                if owe > 0 or responders:
                    max_total = bets[s] + st
                    to_call = owe if owe < st else st
                    raise_ok = responders and can_raise[s] and max_total > cur
                    min_total = cur + hs.last_inc
                    if min_total > max_total:
                        min_total = max_total
                    if owe == 0:
                        legal = LEGAL_CHECK_RAISE if raise_ok else LEGAL_CHECK
                    else:
                        legal = LEGAL_CALL_RAISE if raise_ok else LEGAL_CALL
                    obs = Observation(
                        hole=hs.holes[s], board=hs.board, street=street, seat=s, button=hs.button,
                        stacks=stacks[:], bets=bets[:], in_hand=in_hand[:], pot=hs.pot,
                        to_call=to_call, min_raise=min_total, max_raise=max_total, legal=legal,
                        hand_no=hs.hand_no, blinds=hs.blinds, history=history[:],
                    )
                    a = self._ask(s, obs)
                    k = a.kind
                    if k is FOLD:
                        in_hand[s] = False
                        hs.n_in_hand -= 1
                        history.append((s, a))
                        if hs.n_in_hand == 1:
                            return
                    elif k is CALL:
                        stacks[s] -= to_call
                        bets[s] += to_call
                        contrib[s] += to_call
                        history.append((s, a))
                    elif k is RAISE:
                        total = a.amount
                        put = total - bets[s]
                        stacks[s] -= put
                        bets[s] = total
                        contrib[s] += put
                        inc = total - cur
                        full = inc >= hs.last_inc
                        if full:
                            hs.last_inc = inc
                        hs.current_bet = total
                        for o in range(n):
                            if o != s and in_hand[o] and stacks[o] > 0:
                                if full:
                                    if not need[o]:
                                        need[o] = True
                                        pending += 1
                                    can_raise[o] = True
                                elif not need[o]:
                                    need[o] = True
                                    pending += 1
                                    can_raise[o] = False
                        history.append((s, a))
                    else:
                        history.append((s, a))
            s = (s + 1) % n

    def _ask(self, s: int, obs: Observation) -> Action:
        """Call the bot with enforcement. Always returns a legal Action."""
        st = self.stats[s]
        t0 = perf_counter_ns()
        try:
            a = self.bots[s].act(obs)
            failed = False
        except Exception as e:  # noqa: BLE001 - enforcement boundary
            a = None
            failed = True
            st.exceptions += 1
            st.last_error = repr(e)
        dt = perf_counter_ns() - t0
        st.record(dt)
        if failed or (self.strict and dt > BUDGET_NS):
            return A_CHECK if CHECK in obs.legal else A_FOLD
        if type(a) is not Action:
            st.illegal += 1
            return A_CHECK if CHECK in obs.legal else A_FOLD
        k = a.kind
        if k is RAISE:
            amt = a.amount
            if type(amt) is not int or k not in obs.legal or not obs.min_raise <= amt <= obs.max_raise:
                st.illegal += 1
                if type(amt) is not int:
                    a = Action(RAISE, int(amt))
                a = a.clamp(obs)
            return a
        if k not in obs.legal:
            st.illegal += 1
            return a.clamp(obs)
        return a

    # ----- settlement --------------------------------------------------------------------------

    def _award(self, hs: HandState) -> None:
        n, stacks, contrib, in_hand = self.n, self.stacks, hs.contrib, hs.in_hand
        contenders = [s for s in range(n) if in_hand[s]]
        if len(contenders) == 1:
            stacks[contenders[0]] += sum(contrib)
            return
        rules, board, ev = self.rules, hs.board, self.variant.evaluate
        strength = {s: ev(hs.holes[s], board, rules) for s in contenders}
        hs.showdown = {s: hs.holes[s] for s in contenders}
        levels = sorted({contrib[s] for s in contenders})
        b = hs.button
        order = [(b + 1 + i) % n for i in range(n)]  # odd chips go clockwise from the button
        prev = 0
        for lvl in levels:
            pot = 0
            for s in range(n):
                c = contrib[s]
                if c > prev:
                    pot += (c if c < lvl else lvl) - prev
            eligible = [s for s in contenders if contrib[s] >= lvl]
            best = max(strength[s] for s in eligible)
            winners = [s for s in eligible if strength[s] == best]
            share, odd = divmod(pot, len(winners))
            for s in winners:
                stacks[s] += share
            if odd:
                for s in order:
                    if s in winners:
                        stacks[s] += 1
                        odd -= 1
                        if not odd:
                            break
            prev = lvl

    def _finish_hand(self, hs: HandState) -> None:
        n, stacks, rules = self.n, self.stacks, self.rules
        start = hs.stacks_start
        hs.deltas = deltas = [stacks[s] - start[s] for s in range(n)]
        result = HandResult(hs.hand_no, deltas, hs.showdown, hs.board, hs.history)
        alive_before = [s for s in range(n) if start[s] > 0]
        for s in alive_before:
            try:
                self.bots[s].hand_end(result)
            except Exception as e:  # noqa: BLE001 - enforcement boundary
                self.stats[s].exceptions += 1
                self.stats[s].last_error = repr(e)
        busted = [s for s in alive_before if stacks[s] == 0]
        if busted:
            busted.sort(key=lambda s: (-start[s], s))  # more chips at hand start = better finish
            remaining = self.alive_count - len(busted)
            for i, s in enumerate(busted):
                self._place(s, remaining + i)
            self.alive_count = remaining
        self.hand_no += 1
        if self.alive_count <= 1:
            for s in range(n):
                if stacks[s] > 0:
                    self._place(s, 0)
            self.done = True
        elif self.hand_no >= rules.max_hands:
            eq = icm_equity(stacks, rules.payouts)
            survivors = sorted((s for s in range(n) if stacks[s] > 0), key=lambda s: (-stacks[s], s))
            for place, s in enumerate(survivors):
                self.places[s] = place
                self.points[s] = eq[s]
            self.done = True

    def _place(self, seat: int, place: int) -> None:
        payouts = self.rules.payouts
        self.places[seat] = place
        self.points[seat] = float(payouts[place]) if place < len(payouts) else 0.0


def play_table(
    bots: Sequence[Bot],
    rules: Optional[Rules] = None,
    seed: int = 0,
    rotation: int = 0,
    mode: str = "strict",
    variant: Optional[Variant] = None,
    stats: Optional[Sequence[BotStats]] = None,
    stacks: Optional[Sequence[int]] = None,
) -> TableResult:
    """Play one table to the end. rotation=k deals rotation 0's cards to seats shifted by k."""
    return Table(bots, rules, seed, rotation, mode, variant, stats, stacks).play()
