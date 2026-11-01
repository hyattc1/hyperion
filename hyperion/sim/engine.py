"""No-limit hold'em sit-and-go engine for 2..8 fixed seats, driven by Rules.

What it does: moving button, blinds from Rules.blinds_at (hand_no is 0-based, so hand 25 is
level 1), antes from Rules.ante_at, an optional straddle, no-limit / pot-limit / fixed-limit
raise caps from Rules.betting, min-raise and short-all-in rules, side pots (split per board or
hi/lo when a variant asks), ties with odd chips, bust-outs, finishing points with ICM at the hand
cap, reproducible and duplicate dealing, and enforcement around every bot call (exceptions, time
budget, illegal actions).

Variants: `variant=` takes either an engine `Variant` (mutate HandState directly) or a
`hyperion.drills.variants.VariantHooks` object, which the engine wraps in `HooksVariant`:
on_deal / on_street / score_hand / on_payout are called at the points the contract names, with an
`ask(seat, prompt)` callback that lets a bot answer a variant decision through an optional
`variant_decide(prompt) -> object` method (looked up on the bot, then bot.impl, then
bot.impl.core so wrapped heroes are reached). A hook may also expose `score_splits` (split
pots), `on_bust` (bonus points), `extras(hand)` (per-street Observation.extras) and `charges`
(chips a hook moves into the pot, e.g. buying a card). With variant=None every hook is a no-op.

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
- Antes go straight into the pot (Observation.pot), never into bets; a seat that cannot cover the
  ante is all-in for what it has. Antes are posted before the blinds.
- Straddle (Rules.straddle = k big blinds): with three or more in the hand the seat after the big
  blind posts k bb as a live bet, action starts after it, and the min re-raise increment is the
  straddle. Heads-up there is no straddle.
- Pot-limit: max raise-to = current bet + (pot + bets on the street + the call). Fixed-limit: the
  only raise-to is current bet + 1 bb preflop and on the flop, + 2 bb after; no cap on the number
  of raises. In both, a stack shorter than the cap caps it.
- must_use_hole = 2: showdown is the best 2 of the hole with 3 of the board (Omaha); other values
  of must_use_hole evaluate every k-subset of the hole with (5 - k) of the board.
- Rules.extras["removed_ranks"] (displayed ranks) are left out of the deck (short deck).
- Modes: "strict" folds (or checks) a call over the 1 ms budget on the wall clock; "measure" times it and lets it
  through; "model" is the deterministic timeout model: no bot is timed out on the wall clock, and a bot that
  reports a modelled cost for the decision in `last_cost_ns` (the bestiary's Monte Carlo and timeout bots, told by
  `use_cost_model(True)` at table start) is folded or checked when that cost is over the budget. Default off
  (strict), so earlier numbers stay comparable; with it on, a screen's timeouts no longer drift with host load.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations
from time import perf_counter_ns
from typing import Callable, Optional, Sequence

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
        "first_calls", "first_sum_ns", "first_max_ns", "last_error", "_fresh", "safe_err", "safe_over",
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
        # what a SafeBot wrapper (hyperion.strategy.safe) swallowed: inner exceptions turned into a check or
        # fold, and inner calls over its own deadline. The engine never sees either, so `exceptions` stays 0;
        # a silent KeyError once ran at one hand in 25 for hours. Harvested once per table (Table._harvest_safe).
        self.safe_err = 0
        self.safe_over = 0
        self._fresh = True

    def new_table(self) -> None:
        self._fresh = True

    def record(self, ns: int, over: Optional[bool] = None) -> None:
        """`over`: whether the call counts as over budget (the timeout model decides it); None = ns > budget."""
        if (ns > BUDGET_NS) if over is None else over:
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
        self.safe_err += other.safe_err
        self.safe_over += other.safe_over

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
        "deltas", "ante", "spare", "extras",
    )


_NO_EXTRAS: dict = {}


def evaluate_must_use(hole: Sequence[int], board: Sequence[int], rules: Rules, k: int) -> int:
    """Best hand using exactly k hole cards and 5 - k board cards (k = 2 is Omaha)."""
    if not is_identity_order(rules):
        hole = remap(hole, rules)
        board = remap(board, rules)
    best = 0
    nb = 5 - k
    if len(hole) < k or len(board) < nb:
        raise ValueError(f"must_use_hole={k} needs {k} hole and {nb} board cards")
    for hs in combinations(hole, k):
        for bs in combinations(board, nb):
            s = evaluate(hs + bs)
            if s > best:
                best = s
    return best


class Variant:
    """Hooks for drills. Subclass and override; the default is plain hold'em under Rules.

    `splits`, `payout` and `bust` are None on the base class so the engine's fast path does not
    pay for them; HooksVariant fills them in from the drills contract when the hook has them.
    """

    splits: Optional[Callable] = None  # (hole, board, rules) -> list[int | None], one score per pot share
    payout: Optional[Callable] = None  # (deltas, holes, board, hand_no, rules, rng) -> deltas
    bust: Optional[Callable] = None  # (busted_seats, deltas, hand_no, rules) -> {seat: bonus points}

    def on_deal(self, hand: HandState, rng: random.Random) -> None:
        """After hole cards and the street-0 board are set, before any action."""

    def on_street(self, hand: HandState, street: int, rng: random.Random) -> None:
        """After hand.board is set for street >= 1, before action."""

    def extras(self, hand: HandState) -> dict:
        """Observation.extras for the current street (shared dict; bots must not mutate it)."""
        return _NO_EXTRAS

    def evaluate(self, hole: Sequence[int], board: Sequence[int], rules: Rules) -> int:
        if rules.must_use_hole:
            return evaluate_must_use(hole, board, rules, rules.must_use_hole)
        cards = tuple(hole) + tuple(board)
        if not 5 <= len(cards) <= 8:
            raise ValueError(f"evaluator takes 5..8 cards, got {len(cards)}; override Variant.evaluate")
        if not is_identity_order(rules):
            cards = remap(cards, rules)
        return evaluate(cards)


class HooksVariant(Variant):
    """Bridges a `hyperion.drills.variants.VariantHooks` object to the engine's hand loop.

    The hook sees *displayed* cards, holes as a per-seat list with () for seats not in the hand,
    and a `spare` list: the undealt cards of this hand it may pop from. Anything it returns is
    written back; a changed board is also written into the runout so later streets keep it.
    """

    def __init__(self, hooks, table: "Table"):
        self.hooks = hooks
        self.table = table
        h = hooks
        self.splits = getattr(h, "score_splits", None)
        self.payout = h.on_payout if type(h).on_payout is not _hooks_base_method(h, "on_payout") else None
        self.bust = getattr(h, "on_bust", None)
        self._extras = getattr(h, "extras", None)
        self._score = h.score_hand

    def on_deal(self, hand: HandState, rng: random.Random) -> None:
        t = self.table
        hand.spare = t.deck[t.cards_per_hand:]
        in_hand = hand.in_hand
        holes = [hand.holes[s] if in_hand[s] else () for s in range(t.n)]
        out = self.hooks.on_deal(holes, hand.spare, rng)
        if out is not holes:
            hand.holes = [tuple(out[s]) if in_hand[s] else hand.holes[s] for s in range(t.n)]
        else:
            hand.holes = holes
        self._apply_charges(hand)
        hand.extras = self._extras(hand) if self._extras else _NO_EXTRAS

    def on_street(self, hand: HandState, street: int, rng: random.Random) -> None:
        t = self.table
        in_hand = hand.in_hand
        holes = [hand.holes[s] if in_hand[s] else () for s in range(t.n)]
        board, out = self.hooks.on_street(street, hand.board, holes, hand.spare, rng, ask=t._ask_variant)
        board = tuple(board)
        if board != hand.board:
            hand.runout[: len(board)] = list(board)
            hand.board = board
        if out is not holes:
            hand.holes = [tuple(out[s]) if in_hand[s] else hand.holes[s] for s in range(t.n)]
        self._apply_charges(hand)
        hand.extras = self._extras(hand) if self._extras else _NO_EXTRAS

    def _apply_charges(self, hand: HandState) -> None:
        """Chips a hook asked to move into the pot (hooks.charges = {seat: chips}), capped at the stack."""
        charges = getattr(self.hooks, "charges", None)
        if not charges:
            return
        stacks = self.table.stacks
        for s, amt in charges.items():
            if hand.in_hand[s] and amt > 0:
                put = amt if amt < stacks[s] else stacks[s]
                stacks[s] -= put
                hand.contrib[s] += put
                hand.pot += put
        charges.clear()

    def extras(self, hand: HandState) -> dict:
        return hand.extras

    def evaluate(self, hole, board, rules):
        return self._score(hole, board, rules)


def _hooks_base_method(h, name: str):
    """The contract's identity implementation of `name`, so unoverridden hooks stay no-ops."""
    for klass in type(h).__mro__:
        if klass.__name__ == "VariantHooks" and name in klass.__dict__:
            return klass.__dict__[name]
    return None


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
        if mode not in ("strict", "measure", "model"):
            raise ValueError(f"mode must be strict, measure or model, got {mode!r}")
        self.bots = list(bots)
        self.n = n = len(self.bots)
        if n < 2:
            raise ValueError("a table needs at least two seats")
        self.rules = rules = rules if rules is not None else Rules()
        self.rotation = rotation % n
        self.strict = mode == "strict"
        self.model = mode == "model"  # the deterministic timeout model (see the module docstring)
        if rules.betting not in ("nolimit", "potlimit", "fixedlimit"):
            raise ValueError(f"Rules.betting must be nolimit, potlimit or fixedlimit, got {rules.betting!r}")
        self.betting = ("nolimit", "potlimit", "fixedlimit").index(rules.betting)
        if variant is None:
            self.variant = Variant()
        elif isinstance(variant, Variant):
            self.variant = variant
        else:
            self.variant = HooksVariant(variant, self)
        self._deciders: list = [None] * n  # resolved variant_decide callables, filled lazily
        self.stats = list(stats) if stats is not None else [BotStats(type(b).__name__) for b in self.bots]
        if len(self.stats) != n:
            raise ValueError("one BotStats per seat")
        for st in self.stats:
            st.new_table()
        self.rng = random.Random(seed)  # used for deals only, so hand h's deck depends on (seed, h)
        self.vrng = random.Random(seed * 1_000_003 + 7)  # for variant hooks
        removed = set(rules.extras.get("removed_ranks", ()) or ())
        self.deck = [c for c in deck_for(rules) if (c >> 2) not in removed]
        self.cards_per_hand = rules.hole_cards * n + rules.board_sizes[-1]
        if self.cards_per_hand > len(self.deck):
            raise ValueError("deck too small for this many seats under these rules")
        warm(5 if rules.must_use_hole else min(8, rules.hole_cards + rules.board_sizes[-1]))  # no bot pays for the lazy tables
        self.stacks = list(stacks) if stacks is not None else [rules.starting_stack] * n
        self.button = (self.rotation - 1) % n  # hand 0's button is seat `rotation`
        self.hand_no = 0
        self.places: list[int] = [-1] * n
        self.points = [0.0] * n
        self.bonus = [0.0] * n  # points added by a variant's on_bust (knockout bounties)
        self.alive_count = sum(1 for s in self.stacks if s > 0)
        self.done = self.alive_count <= 1
        self._harvested = False
        for s, bot in enumerate(self.bots):
            hook = getattr(bot, "use_cost_model", None)
            if callable(hook):
                hook(self.model)
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
        hs.extras = _NO_EXTRAS
        hs.ante = ante = rules.ante_at(self.hand_no)
        self.variant.on_deal(hs, self.vrng)

        if ante:
            for s in range(n):
                if in_hand[s]:
                    put = ante if ante < stacks[s] else stacks[s]
                    stacks[s] -= put
                    contrib[s] += put
                    hs.pot += put
        for seat, amt in ((sb, blinds[0]), (bb, blinds[1])):
            put = amt if amt < stacks[seat] else stacks[seat]
            stacks[seat] -= put
            bets[seat] += put
            contrib[seat] += put
        hs.current_bet = max(bets)
        hs.last_inc = blinds[1]
        last_blind = bb
        if rules.straddle and n_in >= 3:
            st_seat = self._after(bb, in_hand)
            amt = rules.straddle * blinds[1]
            put = amt if amt < stacks[st_seat] else stacks[st_seat]
            stacks[st_seat] -= put
            bets[st_seat] += put
            contrib[st_seat] += put
            if put == amt:  # a full straddle is a blind raise: the min re-raise is twice the straddle
                hs.last_inc = amt
            hs.current_bet = max(bets)
            last_blind = st_seat
        if self.betting == 2:
            hs.last_inc = blinds[1]

        first = self._after(last_blind, in_hand)
        for street in range(rules.streets):
            if street:
                hs.pot += sum(bets)
                for i in range(n):
                    bets[i] = 0
                hs.current_bet = 0
                hs.last_inc = blinds[1] * (2 if (self.betting == 2 and street >= 2) else 1)
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
        betting = self.betting
        fixed_inc = hs.blinds[1] * (2 if street >= 2 else 1)
        extras = hs.extras
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
                    if betting:
                        if betting == 1:
                            cap = cur + hs.pot + sum(bets) + to_call
                        else:
                            cap = cur + fixed_inc
                        if cap < max_total:
                            max_total = cap
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
                        hand_no=hs.hand_no, blinds=hs.blinds, history=history[:], extras=extras,
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
                        if full and betting != 2:
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
        if self.model:
            cost = None if failed else getattr(self.bots[s], "last_cost_ns", None)
            over = cost is not None and cost > BUDGET_NS
            st.record(dt, over)
        else:
            over = self.strict and dt > BUDGET_NS
            st.record(dt)
        if failed or over:
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

    def _ask_variant(self, s: int, prompt: dict):
        """The hooks' `ask` callback: the bot's variant_decide(prompt) under the same enforcement as
        act(); None when the bot has no such method, raised, or overran the budget in strict mode."""
        fn = self._deciders[s]
        if fn is None:
            fn = False
            bot = self.bots[s]
            for obj in (bot, getattr(bot, "impl", None), getattr(getattr(bot, "impl", None), "core", None),
                        getattr(bot, "inner", None)):
                cand = getattr(obj, "variant_decide", None) if obj is not None else None
                if callable(cand):
                    fn = cand
                    break
            self._deciders[s] = fn
        if fn is False:
            return None
        prompt = dict(prompt)
        prompt.setdefault("seat", s)
        prompt.setdefault("hand_no", self.hand_no)
        prompt.setdefault("stacks", self.stacks[:])
        st = self.stats[s]
        t0 = perf_counter_ns()
        try:
            ans = fn(prompt)
        except Exception as e:  # noqa: BLE001 - enforcement boundary
            ans = None
            st.exceptions += 1
            st.last_error = repr(e)
        dt = perf_counter_ns() - t0
        st.record(dt, False if self.model else None)  # no bot models a variant decision's cost
        if self.strict and dt > BUDGET_NS:
            return None
        return ans

    # ----- settlement --------------------------------------------------------------------------

    def _award(self, hs: HandState) -> None:
        n, stacks, contrib, in_hand = self.n, self.stacks, hs.contrib, hs.in_hand
        contenders = [s for s in range(n) if in_hand[s]]
        if len(contenders) == 1:
            stacks[contenders[0]] += sum(contrib)
            return
        rules, board, variant = self.rules, hs.board, self.variant
        hs.showdown = {s: hs.holes[s] for s in contenders}
        levels = sorted({contrib[s] for s in contenders})
        b = hs.button
        order = [(b + 1 + i) % n for i in range(n)]  # odd chips go clockwise from the button
        splits = variant.splits
        if splits is None:
            ev = variant.evaluate
            scores = {s: (ev(hs.holes[s], board, rules),) for s in contenders}
            k = 1
        else:
            scores = {s: tuple(splits(hs.holes[s], board, rules)) for s in contenders}
            k = len(next(iter(scores.values())))
        prev = 0
        for lvl in levels:
            pot = 0
            for s in range(n):
                c = contrib[s]
                if c > prev:
                    pot += (c if c < lvl else lvl) - prev
            eligible = [s for s in contenders if contrib[s] >= lvl]
            if k == 1:
                best = max(scores[s][0] for s in eligible)
                self._pay(pot, [s for s in eligible if scores[s][0] == best], order)
            else:
                # one share per score column; a column nobody qualifies for (all None) goes to column 0
                base, rem = divmod(pot, k)
                winners0 = None
                for col in range(k):
                    part = base + (rem if col == 0 else 0)
                    vals = [scores[s][col] for s in eligible if scores[s][col] is not None]
                    if vals:
                        best = max(vals)
                        winners = [s for s in eligible if scores[s][col] == best]
                    else:
                        winners = winners0
                    if col == 0:
                        winners0 = winners
                    if part and winners:
                        self._pay(part, winners, order)
            prev = lvl

    def _pay(self, pot: int, winners: list, order: list) -> None:
        stacks = self.stacks
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

    def _finish_hand(self, hs: HandState) -> None:
        n, stacks, rules = self.n, self.stacks, self.rules
        start = hs.stacks_start
        payout = self.variant.payout
        if payout is not None:
            deltas = [stacks[s] - start[s] for s in range(n)]
            new = payout(deltas, hs.holes, hs.board, hs.hand_no, rules, self.vrng)
            for s in range(n):
                d = int(new[s])
                stacks[s] = start[s] + d if start[s] + d > 0 else 0
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
            bust = self.variant.bust
            if bust is not None:
                for s, bonus in bust(busted, deltas, hs.hand_no, rules).items():
                    self.points[s] += float(bonus)
                    self.bonus[s] += float(bonus)
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
                self.points[s] = eq[s] + self.bonus[s]
            self.done = True
        if self.done:
            self._harvest_safe()

    def _harvest_safe(self) -> None:
        """Observability only. A SafeBot (hyperion.strategy.safe) turns its inner bot's exceptions and
        deadline overruns into legal actions, so `BotStats.exceptions` never sees them. Once per table, read
        its counters (it resets them in new_table) into safe_err / safe_over."""
        if self._harvested:
            return
        self._harvested = True
        for s, bot in enumerate(self.bots):
            safe = find_safe(bot)
            if safe is not None:
                st = self.stats[s]
                st.safe_err += int(getattr(safe, "errors", 0) or 0)
                st.safe_over += int(getattr(safe, "overruns", 0) or 0)

    def _place(self, seat: int, place: int) -> None:
        payouts = self.rules.payouts
        self.places[seat] = place
        self.points[seat] = (float(payouts[place]) if place < len(payouts) else 0.0) + self.bonus[seat]


def find_safe(bot, depth: int = 5):
    """The SafeBot inside a possibly wrapped bot: `bot.safe`, or the same through the .impl / .inner chain
    (BustTracer -> bestiary.Hero -> strategy.Hero.safe), or the object itself when it is the SafeBot."""
    obj = bot
    for _ in range(depth):
        if obj is None:
            return None
        safe = getattr(obj, "safe", None)
        if safe is not None and hasattr(safe, "errors") and hasattr(safe, "overruns"):
            return safe
        if hasattr(obj, "errors") and hasattr(obj, "overruns") and hasattr(obj, "panic_mode"):
            return obj
        nxt = getattr(obj, "impl", None)
        obj = nxt if nxt is not None else getattr(obj, "inner", None)
    return None


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
