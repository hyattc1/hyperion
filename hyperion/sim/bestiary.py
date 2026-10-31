"""Opponent archetypes: what one-hour student bots turn out to be, each a few lines with knobs.

Every bot here implements the Bot protocol and decides in well under 1 ms. They see displayed
cards and most of them evaluate those directly, which is wrong under a rank-permuting variant,
exactly like a naive bot would be. Helpers tolerate any hole-card count so variants do not crash
them; their poker sense is only meant for two cards.
"""
from __future__ import annotations

import random
import time
from typing import Optional

from ..core.cards import hole_class
from ..core.eval import category, evaluate
from ..core.types import RANKS, Action, ActionKind, HandResult, Observation, Rules

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
_KIND_ORDER = (FOLD, CHECK, CALL, RAISE)  # frozenset iteration order is not stable across processes


# ----- helpers ---------------------------------------------------------------------------------


def two_card_class(hole: tuple[int, ...]) -> str:
    """169-class label for the best two cards of any hole (pair if present, else top two)."""
    if len(hole) == 2:
        return hole_class(hole)
    if len(hole) < 2:
        return "72o"
    by_rank = sorted(hole, key=lambda c: -(c >> 2))
    for i in range(len(by_rank) - 1):
        if by_rank[i] >> 2 == by_rank[i + 1] >> 2:
            return hole_class((by_rank[i], by_rank[i + 1]))
    return hole_class((by_rank[0], by_rank[1]))


def made_category(hole: tuple[int, ...], board: tuple[int, ...]) -> int:
    """core.eval category of hole+board, or -1 when there are not 5..8 cards to evaluate."""
    cards = hole + board
    if 5 <= len(cards) <= 8:
        return category(evaluate(cards))
    return -1


def top_pair_or_better(hole: tuple[int, ...], board: tuple[int, ...]) -> bool:
    cat = made_category(hole, board)
    if cat >= 2:
        return True
    if cat != 1 or not board:
        return False
    top = max(c >> 2 for c in board)
    hole_ranks = [c >> 2 for c in hole]
    if top in hole_ranks:
        return True
    pairs = {r for r in hole_ranks if hole_ranks.count(r) > 1}
    return bool(pairs) and min(pairs) > top


def expand_range(spec: str) -> frozenset[str]:
    """'77+ AJs+ KQo T9s' -> set of class labels. '+' walks pairs up, or the kicker up to the gap."""
    out = set()
    for tok in spec.split():
        plus = tok.endswith("+")
        tok = tok.rstrip("+")
        hi, lo = RANKS.index(tok[0]), RANKS.index(tok[1])
        suffix = tok[2:] if len(tok) > 2 else ""
        if hi == lo:
            for r in range(hi, 13 if plus else hi + 1):
                out.add(RANKS[r] * 2)
        else:
            for r in range(lo, hi if plus else lo + 1):
                out.add(RANKS[hi] + RANKS[r] + suffix)
    return frozenset(out)


def chen_score(hole: tuple[int, ...]) -> float:
    """Bill Chen's preflop formula on the best two cards."""
    cls = two_card_class(hole)
    hi, lo = RANKS.index(cls[0]), RANKS.index(cls[1])
    pts = {12: 10.0, 11: 8.0, 10: 7.0, 9: 6.0}.get(hi, (hi + 2) / 2)
    if hi == lo:
        return max(5.0, pts * 2)
    if cls[2] == "s":
        pts += 2
    gap = hi - lo - 1
    pts -= (0, 1, 2, 4)[gap] if gap < 4 else 5
    if gap <= 1 and hi < 10:
        pts += 1
    return pts


def preflop_order(obs: Observation) -> list[int]:
    """Seats in preflop acting order among live players (UTG first, big blind last)."""
    n = obs.n_players
    live = [s for s in range(n) if obs.stacks[s] + obs.bets[s] > 0]
    ring = sorted(live, key=lambda s: (s - obs.button) % n)  # button first
    if len(ring) == 2:
        return ring
    return ring[3:] + ring[:3]


def players_behind(obs: Observation) -> int:
    order = preflop_order(obs)
    return len(order) - 1 - order.index(obs.seat) if obs.seat in order else 0


def _check_or_fold(obs: Observation) -> Action:
    return Action.check() if CHECK in obs.legal else Action.fold()


def _check_or_call(obs: Observation) -> Action:
    return Action.check() if CHECK in obs.legal else Action.call()


def _raise_or_call(obs: Observation, total: int) -> Action:
    if RAISE in obs.legal:
        return Action.raise_to(max(obs.min_raise, min(obs.max_raise, int(total))))
    return _check_or_call(obs)


class _Base:
    """Stores the table parameters; subclasses override act()."""

    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.seat = 0
        self.rules = Rules()

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.rules, self.seat, self.n_players = rules, seat, n_players

    def act(self, obs: Observation) -> Action:
        return _check_or_fold(obs)

    def hand_end(self, result: HandResult) -> None:
        pass


# ----- the archetypes --------------------------------------------------------------------------


class Crasher(_Base):
    """Raises on every decision. The engine should fold it and keep going."""

    def act(self, obs: Observation) -> Action:
        raise RuntimeError("Crasher always crashes")


class TimeoutBot(_Base):
    """Sleeps past the budget, then shoves. In strict mode its shove never lands."""

    def __init__(self, seed: Optional[int] = None, sleep_s: float = 0.002):
        super().__init__(seed)
        self.sleep_s = sleep_s

    def act(self, obs: Observation) -> Action:
        time.sleep(self.sleep_s)
        return _raise_or_call(obs, obs.max_raise)


class RandomBot(_Base):
    """Uniform over legal kinds; a raise picks a uniform raise-to in [min_raise, max_raise]."""

    def act(self, obs: Observation) -> Action:
        legal = obs.legal
        kinds = [k for k in _KIND_ORDER if k in legal]
        k = kinds[self.rng.randrange(len(kinds))]
        if k is RAISE:
            return Action.raise_to(self.rng.randint(obs.min_raise, obs.max_raise))
        return Action(k)


class CallingStation(_Base):
    """Never folds, never raises."""

    def act(self, obs: Observation) -> Action:
        return _check_or_call(obs)


class Nit(_Base):
    """Plays a tiny premium list preflop; postflop needs top pair or better to put chips in."""

    PREMIUM = frozenset({"AA", "KK", "QQ", "JJ", "TT", "AKs", "AKo", "AQs"})

    def __init__(self, seed: Optional[int] = None, open_bb: float = 3.0, shove_below_bb: float = 12.0):
        super().__init__(seed)
        self.open_bb, self.shove_below_bb = open_bb, shove_below_bb

    def act(self, obs: Observation) -> Action:
        if obs.street == 0:
            if two_card_class(obs.hole) in self.PREMIUM:
                if obs.stack_bb <= self.shove_below_bb:
                    return _raise_or_call(obs, obs.max_raise)
                return _raise_or_call(obs, self.open_bb * obs.big_blind)
            return _check_or_fold(obs)
        if top_pair_or_better(obs.hole, obs.board):
            if made_category(obs.hole, obs.board) >= 2 or obs.to_call == 0:
                return _raise_or_call(obs, obs.total_pot)
            return Action.call()
        return _check_or_fold(obs)


class Maniac(_Base):
    """Raises or shoves most of the time, calls the rest, never folds."""

    def __init__(self, seed: Optional[int] = None, p_raise: float = 0.7, p_shove: float = 0.3):
        super().__init__(seed)
        self.p_raise, self.p_shove = p_raise, p_shove

    def act(self, obs: Observation) -> Action:
        if RAISE in obs.legal and self.rng.random() < self.p_raise:
            if self.rng.random() < self.p_shove:
                return Action.raise_to(obs.max_raise)
            return _raise_or_call(obs, max(obs.min_raise, obs.total_pot + obs.to_call))
        return _check_or_call(obs)


class AllInBot(_Base):
    """Shoves every hand."""

    def act(self, obs: Observation) -> Action:
        return _raise_or_call(obs, obs.max_raise)


class NaiveEquityBot(_Base):
    """What a student writes in 40 minutes: Chen preflop, made-hand category vs pot odds after."""

    CATEGORY_EQUITY = (0.20, 0.45, 0.65, 0.80, 0.88, 0.92, 0.96, 0.99, 1.0)

    def __init__(self, seed: Optional[int] = None, raise_score: float = 9.0, call_score: float = 6.0):
        super().__init__(seed)
        self.raise_score, self.call_score = raise_score, call_score

    def act(self, obs: Observation) -> Action:
        bb = obs.big_blind
        if obs.street == 0:
            score = chen_score(obs.hole)
            if score >= self.raise_score:
                return _raise_or_call(obs, 3 * bb if obs.to_call <= bb else 3 * (obs.to_call + obs.bets[obs.seat]))
            if score >= self.call_score or obs.to_call <= bb and score >= 4:
                return _check_or_call(obs)
            return _check_or_fold(obs)
        cat = made_category(obs.hole, obs.board)
        eq = self.CATEGORY_EQUITY[max(cat, 0)]
        if obs.to_call == 0:
            if cat >= 1:
                return _raise_or_call(obs, obs.bets[obs.seat] + max(bb, obs.total_pot // 2))
            return Action.check()
        odds = obs.to_call / (obs.total_pot + obs.to_call)
        if cat >= 2 and RAISE in obs.legal:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
        if eq >= odds:
            return Action.call()
        return Action.fold()


class ChartTAG(_Base):
    """Tight-aggressive baseline: position charts, c-bets, folds to resistance without top pair."""

    EARLY = expand_range("77+ AJs+ AQo+ KQs")
    MIDDLE = EARLY | expand_range("55+ ATs+ AJo+ KJs+ KQo QJs JTs")
    LATE = MIDDLE | expand_range("22+ A2s+ A8o+ K9s+ KTo+ Q9s+ QTo+ J9s+ JTo T9s 98s 87s 76s")
    THREE_BET = expand_range("QQ+ AKs AKo")
    CALL_RAISE = expand_range("JJ TT 99 AQs AJs KQs AQo")

    def __init__(self, seed: Optional[int] = None, open_bb: float = 3.0, push_below_bb: float = 12.0,
                 cbet_frac: float = 0.5):
        super().__init__(seed)
        self.open_bb, self.push_below_bb, self.cbet_frac = open_bb, push_below_bb, cbet_frac
        self.aggressor_hand = -1
        self.cbet_done_hand = -1

    def act(self, obs: Observation) -> Action:
        bb = obs.big_blind
        cls = two_card_class(obs.hole)
        if obs.street == 0:
            behind = players_behind(obs)
            rng_ = self.EARLY if behind >= 5 else self.MIDDLE if behind >= 3 else self.LATE
            facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
            if obs.stack_bb <= self.push_below_bb:
                if cls in (self.MIDDLE if facing_raise else rng_):
                    return _raise_or_call(obs, obs.max_raise)
                return _check_or_fold(obs)
            if facing_raise:
                if cls in self.THREE_BET:
                    self.aggressor_hand = obs.hand_no
                    target = obs.bets[obs.seat] + obs.to_call * 3
                    return _raise_or_call(obs, target if target < obs.my_stack // 2 else obs.max_raise)
                if cls in self.CALL_RAISE and obs.to_call <= obs.my_stack // 8 and self.aggressor_hand != obs.hand_no:
                    return Action.call()
                return _check_or_fold(obs)
            if cls in rng_ and RAISE in obs.legal:
                self.aggressor_hand = obs.hand_no
                limpers = sum(1 for s in range(obs.n_players) if obs.in_hand[s] and obs.bets[s] >= bb) - 1
                return _raise_or_call(obs, self.open_bb * bb + max(0, limpers) * bb)
            return _check_or_fold(obs)
        strong = top_pair_or_better(obs.hole, obs.board)
        if obs.to_call == 0:
            if strong:
                return _raise_or_call(obs, max(bb, obs.total_pot // 2))
            if obs.street == 1 and self.aggressor_hand == obs.hand_no and self.cbet_done_hand != obs.hand_no:
                self.cbet_done_hand = obs.hand_no
                return _raise_or_call(obs, max(bb, int(obs.total_pot * self.cbet_frac)))
            return Action.check()
        if strong:
            if made_category(obs.hole, obs.board) >= 2:
                return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
            return Action.call()
        return Action.fold()


HERO_CONFIG: Optional[dict] = None  # dotted Config overrides for every Hero built here (runner --hero-config, sweeps)


class Hero(_Base):
    """The bot under development: hyperion.strategy.hero.Hero if it exists, else ChartTAG."""

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.impl = None
        try:
            from ..strategy.hero import Hero as _Hero, config_from_dict  # type: ignore[import-not-found]

            self.impl = _Hero(config_from_dict(HERO_CONFIG, seed=seed))
        except Exception:  # noqa: BLE001 - strategy may not exist yet or may need arguments
            self.impl = ChartTAG(seed)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.impl.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.impl.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end(result)


REGISTRY: dict[str, type] = {
    "crasher": Crasher,
    "timeout": TimeoutBot,
    "random": RandomBot,
    "station": CallingStation,
    "nit": Nit,
    "maniac": Maniac,
    "allin": AllInBot,
    "naive": NaiveEquityBot,
    "tag": ChartTAG,
    "hero": Hero,
}
_BY_CLASS = {cls.__name__.lower(): cls for cls in REGISTRY.values()}


def make_bot(name: str, seed: Optional[int] = None):
    key = name.strip().lower()
    cls = REGISTRY.get(key) or _BY_CLASS.get(key)
    if cls is None:
        raise KeyError(f"unknown bot {name!r}; known: {', '.join(REGISTRY)}")
    return cls(seed)
