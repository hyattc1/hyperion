"""Opponent archetypes: what one-hour student bots turn out to be, each a few lines with knobs.

Every bot here implements the Bot protocol and decides in well under 1 ms. They see displayed
cards and most of them evaluate those directly, which is wrong under a rank-permuting variant,
exactly like a naive bot would be. tag, nit and pushfold read `Rules.rank_order` first
(`strength_view`), like a student who read the rule sheet, so they stay honest yardsticks under
permuted ranks. Helpers tolerate any hole-card count so variants do not crash them; their poker
sense is only meant for two cards.
"""
from __future__ import annotations

import dataclasses
import os
import random
import sys
import time
import types
from typing import Optional

from ..core.cards import deck_for, hole_class, remap
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


_IDENTITY_ORDER = tuple(range(13))


def strength_view(obs: Observation, rules: Rules) -> Observation:
    """`obs` with hole and board mapped to canonical strength under `rules.rank_order`; `obs` itself when the
    order is the identity. A copy, so the engine's observation is never mutated."""
    if tuple(rules.rank_order) == _IDENTITY_ORDER:
        return obs
    return dataclasses.replace(obs, hole=remap(obs.hole, rules), board=remap(obs.board, rules))


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


def chen_preflop(obs: Observation, raise_score: float = 9.0, call_score: float = 6.0) -> Action:
    """The preflop most students ship: Chen score thresholds, 3x opens, limp-along when it is cheap."""
    bb = obs.big_blind
    score = chen_score(obs.hole)
    if score >= raise_score:
        return _raise_or_call(obs, 3 * bb if obs.to_call <= bb else 3 * (obs.to_call + obs.bets[obs.seat]))
    if score >= call_score or obs.to_call <= bb and score >= 4:
        return _check_or_call(obs)
    return _check_or_fold(obs)


def facing_shove(obs: Observation) -> bool:
    """Someone still in the hand is all-in for at least the current bet."""
    top = max(obs.bets)
    return any(obs.in_hand[s] and obs.stacks[s] == 0 and obs.bets[s] >= top > 0
               for s in range(obs.n_players) if s != obs.seat)


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


# ----- the deterministic timeout model (engine mode "model") -----------------------------------
# In strict mode the engine times each call on the wall clock, so how often the Monte Carlo and timeout bots overrun
# follows the host's load, and a strict screen's timeouts drift with whatever else the box runs. In mode "model" the
# engine calls use_cost_model(True) on each bot that has it, and folds (or checks) a bot only when the decision's
# modelled cost, `last_cost_ns`, is over the 1 ms budget; a bot with no model is never folded for time. Modelled bots
# skip their sleeps but do the same work and draw the same random numbers as in strict mode, so the two modes differ
# only where a timeout differs. Per-rollout costs of MonteCarloBot.equity, medians on the dev box at load ~2.7 of 8
# cores (scratch calibration, docs/drills/exploit-pass-log.md); 200 honest rollouts heads-up land at ~1.0 ms, so with
# the spread below half of them time out, as they did there, and with two or more opponents all of them do.
MC_SHUFFLE_NS = (4_000, 500)  # deck.shuffle rollouts: 4.0 us + 0.5 us per hand evaluated (opponents + 1)
MC_SAMPLE_NS = (1_040, 790)  # rng.sample rollouts: 1.04 us + 0.79 us per opponent
MC_ACT_NS = 5_000  # the rest of a postflop act()
COST_SIGMA = 0.05  # per-decision lognormal spread (the sd of log time of 200 honest rollouts there)


class _CostModel:
    """Mixin for bots that can say what a decision costs. `last_cost_ns` is set on every act() while the model is
    on (None = no cost worth modelling); `_sleep` sleeps only while it is off."""

    cost_model = False
    last_cost_ns: Optional[int] = None
    cost_rng: Optional[random.Random] = None

    def use_cost_model(self, on: bool) -> None:
        self.cost_model = bool(on)
        if on and self.cost_rng is None:
            # its own stream: the noise never moves the bot's decision RNG
            self.cost_rng = random.Random((getattr(self, "seed", None) or 0) * 2_654_435_761 + 97)

    def _sleep(self, seconds: float) -> None:
        if not self.cost_model:
            time.sleep(seconds)

    def _noisy(self, ns: float) -> int:
        return int(ns * self.cost_rng.lognormvariate(0.0, COST_SIGMA)) if COST_SIGMA > 0 else int(ns)


class _FixedSpeedInModel:
    """For bots whose play follows the wall clock (a sampler that stops on a time budget, a guard that skips work when
    late): in engine mode "model" they play at a fixed speed, so every model-mode run replays exactly, whatever the
    host's load; in strict and measure modes they play as built. The engine calls use_cost_model(True) on each bot that
    has it at table start (mode "model" only, False otherwise); `last_cost_ns` stays None, so the timeout model never
    folds them. FIXED_SPEED, when True, forces the fixed speed in every mode. Subclasses implement _set_speed(fixed)."""

    FIXED_SPEED = False
    fixed_speed = False
    last_cost_ns = None

    def use_cost_model(self, on: bool) -> None:
        self.fixed_speed = bool(on) or self.FIXED_SPEED
        self._set_speed(self.fixed_speed)

    def _set_speed(self, fixed: bool) -> None:
        raise NotImplementedError


# ----- the archetypes --------------------------------------------------------------------------


class Crasher(_Base):
    """Raises on every decision. The engine should fold it and keep going."""

    def act(self, obs: Observation) -> Action:
        raise RuntimeError("Crasher always crashes")


class TimeoutBot(_CostModel, _Base):
    """Sleeps past the budget, then shoves. In strict mode its shove never lands."""

    def __init__(self, seed: Optional[int] = None, sleep_s: float = 0.002):
        super().__init__(seed)
        self.sleep_s = sleep_s

    def act(self, obs: Observation) -> Action:
        self._sleep(self.sleep_s)
        if self.cost_model:
            self.last_cost_ns = int(self.sleep_s * 1e9)
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
        obs = strength_view(obs, self.rules)
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
            return chen_preflop(obs, self.raise_score, self.call_score)
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
        obs = strength_view(obs, self.rules)
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


class AuctionTAG(ChartTAG):
    """The auction entry's variant-aware opponent: what a team that read the auction rule ships in an hour. ChartTAG
    preflop and postflop (its reads take three hole cards), plus:
      bid    a share of the pot by how much a card should help: 0.45 heads-up, 0.30 three-way, 0.20 beyond, for a
             hand that is at most one pair; half that with two pair or better; +-20% jitter so bids do not tie; never
             more than a quarter of the stack.
      reads  when someone else won a card and it did not, it continues only with two pair or better."""

    def variant_decide(self, prompt: dict):
        if prompt.get("decision") != "bid":
            return None
        pot = int(prompt.get("pot", 0) or 0)
        stack = int(prompt.get("max_bid", 0) or 0)
        k = int(prompt.get("n_bidders", 2) or 2)
        share = 0.45 if k <= 2 else 0.30 if k == 3 else 0.20
        hole, board = tuple(prompt.get("hole") or ()), tuple(prompt.get("board") or ())
        if tuple(self.rules.rank_order) != tuple(range(13)):
            hole, board = remap(hole, self.rules), remap(board, self.rules)
        if len(hole) + len(board) >= 5 and made_category(hole, board) >= 2:
            share *= 0.5
        bid = int(pot * share * (0.8 + 0.4 * self.rng.random()))
        return max(0, min(bid, stack // 4))

    def act(self, obs: Observation) -> Action:
        if obs.street >= 1 and obs.to_call > 0 and obs.extras:
            won = obs.extras.get("auction_winners") or ()
            if won and obs.seat not in won and any(obs.in_hand[s] for s in won if s != obs.seat):
                v = strength_view(obs, self.rules)
                if made_category(v.hole, v.board) < 2:
                    return _check_or_fold(obs)
        return super().act(obs)


class Keep2TAG(ChartTAG):
    """deal5_keep2's variant-aware opponent: a team that read 'five cards, keep two after the flop'. Preflop it plays
    the best two of its five from ranges a notch tighter than ChartTAG's (everyone's best two of five is strong),
    one notch wider with a second pair or a suited ace among the five; postflop ChartTAG on the kept two. Keep: the
    pair with the best made hand on the flop, then live draws (flush and open-ended outs not among the revealed
    discards, its own discards included), then high cards."""

    EARLY5 = expand_range("JJ+ AKs")
    MIDDLE5 = EARLY5 | expand_range("99+ AQs+ AKo")
    LATE5 = MIDDLE5 | expand_range("66+ ATs+ AQo+ KQs KJs QJs JTs")
    WIDE5 = LATE5 | expand_range("22+ A2s+ A9o+ KTs+ QTs+ JTs T9s 98s")

    def act(self, obs: Observation) -> Action:
        if obs.street == 0 and len(obs.hole) > 2:
            v = strength_view(obs, self.rules)
            cls = two_card_class(v.hole)
            ranks = [c >> 2 for c in v.hole]
            pairs = len({r for r in ranks if ranks.count(r) >= 2})
            suited_ace = any((a >> 2) == 12 and (a & 3) == (b & 3) and a != b for a in v.hole for b in v.hole)
            bonus = (pairs >= 2) + suited_ace
            behind = players_behind(obs)
            tiers = (self.EARLY5, self.MIDDLE5, self.LATE5)
            t = (0 if behind >= 5 else 1 if behind >= 3 else 2) + bonus
            rng_ = tiers[t] if t < 3 else self.WIDE5
            bb = obs.big_blind
            facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
            if obs.stack_bb <= self.push_below_bb:
                return _raise_or_call(obs, obs.max_raise) if cls in (self.MIDDLE5 if facing_raise else rng_) \
                    else _check_or_fold(obs)
            if facing_raise:
                if cls in self.EARLY5:
                    return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call * 3)
                if cls in self.MIDDLE5 and obs.to_call <= obs.my_stack // 8:
                    return Action.call()
                return _check_or_fold(obs)
            if cls in rng_ and RAISE in obs.legal:
                self.aggressor_hand = obs.hand_no
                return _raise_or_call(obs, self.open_bb * bb)
            return _check_or_fold(obs)
        return super().act(obs)

    def variant_decide(self, prompt: dict):
        if prompt.get("decision") != "keep":
            return None
        hole, board = tuple(prompt.get("hole") or ()), tuple(prompt.get("board") or ())
        rv = prompt.get("revealed") or {}
        dead = [c for cards in rv.values() for c in cards]
        if tuple(self.rules.rank_order) != tuple(range(13)):
            hole, board, dead = remap(hole, self.rules), remap(board, self.rules), remap(tuple(dead), self.rules)
        best, best_key = None, None
        for i in range(len(hole)):
            for j in range(i + 1, len(hole)):
                a, b = hole[i], hole[j]
                gone = set(dead) | {hole[m] for m in range(len(hole)) if m not in (i, j)} | set(board) | {a, b}
                cat = made_category((a, b), board) if len(board) >= 3 else (1 if a >> 2 == b >> 2 else 0)
                draw = 0
                if len(board) >= 3:
                    for suit in range(4):
                        mine = sum(1 for c in (a, b) + board if c & 3 == suit)
                        if mine == 4 and (a & 3 == suit or b & 3 == suit):
                            draw = max(draw, sum(1 for r in range(13) if r * 4 + suit not in gone))
                    ranks = {c >> 2 for c in (a, b) + board}
                    for lo in range(-1, 9):
                        window = {(r if r >= 0 else 12) for r in range(lo, lo + 5)}
                        if len(window & ranks) == 4 and ({a >> 2, b >> 2} & window):
                            need = (window - ranks).pop()
                            draw = max(draw, sum(1 for su in range(4) if need * 4 + su not in gone))
                key = (cat, draw, max(a >> 2, b >> 2), min(a >> 2, b >> 2))
                if best_key is None or key > best_key:
                    best, best_key = (i, j), key
        return best


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


# ----- the field: one-hour agent-assisted builds under a 1 ms clock ------------------------------


class MonteCarloBot(_CostModel, _Base):
    """What most students actually write: Chen preflop, Monte Carlo equity postflop, bet when
    equity beats pot odds by a margin. The rollouts genuinely take the time (200 of them cost
    1-3 ms in pure Python), so in strict mode almost every postflop decision is auto-folded and
    in measure mode the bot plays.

    Two ways to put it in a field:
      samples=200, timeout_frac=None   the honest bot: use it to see what really happens to it.
      timeout_frac=0.3                 cheap model of "times out 30% of the time": that share of
                                       postflop decisions sleeps past the budget; the rest run
                                       `fast_samples` rollouts via rng.sample so they land in time.
                                       Use this for large fields (10x faster) and when the question
                                       is how Hero does against a partially broken opponent.
    """

    def __init__(self, seed: Optional[int] = None, samples: int = 200, timeout_frac: Optional[float] = None,
                 fast_samples: int = 30, margin: float = 0.05, bet_eq: float = 0.6, raise_eq: float = 0.75,
                 sleep_s: float = 0.002):
        super().__init__(seed)
        self.seed = seed
        self.samples, self.timeout_frac, self.fast_samples = samples, timeout_frac, fast_samples
        self.margin, self.bet_eq, self.raise_eq, self.sleep_s = margin, bet_eq, raise_eq, sleep_s
        self.deck = list(deck_for(self.rules))

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self.deck = list(deck_for(rules))

    def equity(self, hole: tuple[int, ...], board: tuple[int, ...], n_opp: int, samples: int, fast: bool) -> float:
        """Equity vs n_opp random hands run out to the river, displayed cards evaluated as is."""
        dead = set(hole) | set(board)
        stub = [c for c in self.deck if c not in dead]
        k = self.rules.hole_cards
        if k + self.rules.board_sizes[-1] > 8:  # deal5_keep2: opponents hold the two they kept (else a 10-card evaluation)
            k = int(self.rules.extras.get("keep", 2) or 2)
        need = self.rules.board_sizes[-1] - len(board)
        n_opp = max(1, n_opp)
        take = n_opp * k + need
        if take > len(stub) or len(hole) + self.rules.board_sizes[-1] > 8:
            return 0.5
        rng, shuffle, sample = self.rng, self.rng.shuffle, self.rng.sample
        acc = 0.0
        for _ in range(samples):
            if fast:
                pick = sample(stub, take)
            else:
                shuffle(stub)  # the student's deck.shuffle(); deal from the top
                pick = stub
            full = board + tuple(pick[n_opp * k : take])
            mine = evaluate(hole + full)
            best, ties = 0, 1
            for i in range(n_opp):
                s = evaluate(tuple(pick[i * k : i * k + k]) + full)
                if s > best:
                    best, ties = s, 1
                elif s == best:
                    ties += 1
            acc += 1.0 if mine > best else (1.0 / ties if mine == best else 0.0)
        return acc / samples

    def model_cost_ns(self, samples: int, n_opp: int, fast: bool) -> float:
        """What `samples` rollouts against n_opp opponents cost on the calibration host, before the spread."""
        n_opp = max(1, n_opp)
        a, b = MC_SAMPLE_NS if fast else MC_SHUFFLE_NS
        per = a + b * (n_opp if fast else n_opp + 1)
        return MC_ACT_NS + samples * per

    def act(self, obs: Observation) -> Action:
        if obs.street == 0:
            self.last_cost_ns = None
            return chen_preflop(obs)
        n_opp = obs.active - 1
        if self.timeout_frac is not None:
            slept = self.rng.random() < self.timeout_frac
            if slept:
                self._sleep(self.sleep_s)
            samples, fast = min(self.samples, self.fast_samples), True
        else:
            slept, samples, fast = False, self.samples, False
        if self.cost_model:
            cost = self._noisy(self.model_cost_ns(samples, n_opp, fast))
            self.last_cost_ns = cost + (int(self.sleep_s * 1e9) if slept else 0)
        eq = self.equity(obs.hole, obs.board, n_opp, samples, fast)
        pot = obs.total_pot
        if obs.to_call == 0:
            if eq >= self.bet_eq and RAISE in obs.legal:
                return _raise_or_call(obs, obs.bets[obs.seat] + max(obs.big_blind, (2 * pot) // 3))
            return Action.check()
        odds = obs.to_call / (pot + obs.to_call)
        if eq >= self.raise_eq and RAISE in obs.legal:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + pot)
        if eq >= odds + self.margin:
            return Action.call()
        return Action.fold()


class MonteCarloTimeout30(MonteCarloBot):
    """MonteCarloBot that times out on 30% of postflop decisions (timeout_frac=0.3, see there)."""

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed, timeout_frac=0.3)


class PushFoldBot(_Base):
    """The good-student baseline: tight-aggressive above 15 bb from hardcoded position ranges,
    pure push/fold below from a chart by stack depth, tight shove calls. No ICM, no reads."""

    OPEN = {
        "early": expand_range("77+ ATs+ AJo+ KQs"),
        "middle": expand_range("55+ A8s+ ATo+ KTs+ KQo QJs JTs"),
        "late": expand_range("22+ A2s+ A5o+ K7s+ K9o+ Q8s+ QTo+ J8s+ JTo T8s+ 97s+ 86s+ 75s+ 65s"),
    }
    THREE_BET = expand_range("JJ+ AQs+ AKo")
    CALL_RAISE = expand_range("22+ ATs+ AJo+ KQs KQo QJs JTs T9s")
    # push chart: (max stack in bb, position) -> range. Depth buckets are tried shallowest first.
    PUSH = {
        (5, "early"): expand_range("22+ A2s+ A7o+ KTs+ KQo"),
        (5, "middle"): expand_range("22+ A2s+ A2o+ K9s+ KTo+ QJs"),
        (5, "late"): expand_range("22+ A2s+ A2o+ K2s+ K5o+ Q2s+ Q7o+ J6s+ J9o+ T7s+ T9o 97s+ 87s"),
        (10, "early"): expand_range("55+ ATs+ AJo+ KQs"),
        (10, "middle"): expand_range("22+ A2s+ A8o+ KJs+ KQo"),
        (10, "late"): expand_range("22+ A2s+ A2o+ K2s+ K9o+ Q8s+ Q9o+ J8s+ JTo T8s+ 98s"),
        (15, "early"): expand_range("77+ AJs+ AQo+"),
        (15, "middle"): expand_range("55+ A9s+ ATo+ KQs"),
        (15, "late"): expand_range("22+ A2s+ A7o+ K9s+ KTo+ QTs+ JTs"),
    }
    CALL_SHOVE = expand_range("99+ AQs+ AKo")
    CALL_SHOVE_SHORT = expand_range("77+ ATs+ AJo+ KQs")  # at or below 8 bb, or when the shove is small

    def __init__(self, seed: Optional[int] = None, pushfold_bb: float = 15.0, open_bb: float = 2.5):
        super().__init__(seed)
        self.pushfold_bb, self.open_bb = pushfold_bb, open_bb
        self.aggressor_hand = -1
        self.cbet_done_hand = -1

    @staticmethod
    def _position(obs: Observation) -> str:
        behind = players_behind(obs)
        return "late" if behind <= 2 else "middle" if behind <= 4 else "early"

    def _push_range(self, obs: Observation) -> frozenset[str]:
        pos = self._position(obs)
        for cap in (5, 10, 15):
            if obs.stack_bb <= cap:
                return self.PUSH[(cap, pos)]
        return self.PUSH[(15, pos)]

    def act(self, obs: Observation) -> Action:
        obs = strength_view(obs, self.rules)
        bb = obs.big_blind
        cls = two_card_class(obs.hole)
        if obs.street == 0:
            facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
            shove = facing_shove(obs) or obs.to_call >= obs.my_stack / 3
            if shove and obs.to_call > 0:
                rng_ = self.CALL_SHOVE_SHORT if obs.stack_bb <= 8 or obs.to_call <= obs.my_stack / 4 else self.CALL_SHOVE
                return Action.call() if cls in rng_ else _check_or_fold(obs)
            if obs.stack_bb <= self.pushfold_bb:
                if facing_raise:
                    return _raise_or_call(obs, obs.max_raise) if cls in self.CALL_SHOVE else _check_or_fold(obs)
                if cls in self._push_range(obs):
                    self.aggressor_hand = obs.hand_no
                    return _raise_or_call(obs, obs.max_raise)
                return _check_or_fold(obs)
            if facing_raise:
                if cls in self.THREE_BET:
                    self.aggressor_hand = obs.hand_no
                    target = obs.bets[obs.seat] + obs.to_call * 3
                    return _raise_or_call(obs, target if target < obs.my_stack // 2 else obs.max_raise)
                if cls in self.CALL_RAISE and obs.to_call <= obs.my_stack // 10:
                    return Action.call()
                return _check_or_fold(obs)
            if cls in self.OPEN[self._position(obs)] and RAISE in obs.legal:
                self.aggressor_hand = obs.hand_no
                limpers = sum(1 for s in range(obs.n_players) if obs.in_hand[s] and obs.bets[s] >= bb) - 1
                return _raise_or_call(obs, self.open_bb * bb + max(0, limpers) * bb)
            return _check_or_fold(obs)
        strong = top_pair_or_better(obs.hole, obs.board)
        big = made_category(obs.hole, obs.board) >= 2
        if obs.stack_bb <= self.pushfold_bb:  # saw a flop short (big blind, mostly): shove or give up
            if strong:
                return _raise_or_call(obs, obs.max_raise)
            return _check_or_fold(obs)
        if obs.to_call == 0:
            if strong:
                return _raise_or_call(obs, obs.bets[obs.seat] + max(bb, (2 * obs.total_pot) // 3))
            if (obs.street == 1 and self.aggressor_hand == obs.hand_no and self.cbet_done_hand != obs.hand_no
                    and obs.active == 2):
                self.cbet_done_hand = obs.hand_no
                return _raise_or_call(obs, max(bb, obs.total_pot // 2))
            return Action.check()
        if big:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
        if strong:
            return Action.call()
        return Action.fold()


class LooseAggroStudent(_Base):
    """Opens wide, c-bets every flop with one size, barrels half the turns, folds to a raise
    without top pair. Common and exploitable, but not a maniac: it does fold."""

    def __init__(self, seed: Optional[int] = None, open_score: float = 5.0, call_score: float = 6.0,
                 three_bet_score: float = 10.0, open_bb: float = 2.5, bet_frac: float = 0.5,
                 barrel_frac: float = 0.5, shove_below_bb: float = 10.0, shove_score: float = 7.0):
        super().__init__(seed)
        self.open_score, self.call_score, self.three_bet_score = open_score, call_score, three_bet_score
        self.open_bb, self.bet_frac, self.barrel_frac = open_bb, bet_frac, barrel_frac
        self.shove_below_bb, self.shove_score = shove_below_bb, shove_score
        self.aggressor_hand = -1
        self.bet_street = (-1, -1)  # (hand, street) of the last bet, so each street fires once
        self.barrel_hand = (-1, False)

    def _bet(self, obs: Observation) -> Action:
        self.bet_street = (obs.hand_no, obs.street)
        return _raise_or_call(obs, obs.bets[obs.seat] + max(obs.big_blind, int(obs.total_pot * self.bet_frac)))

    def act(self, obs: Observation) -> Action:
        bb = obs.big_blind
        if obs.street == 0:
            score = chen_score(obs.hole)
            facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
            if obs.stack_bb <= self.shove_below_bb:
                if score >= self.shove_score:
                    self.aggressor_hand = obs.hand_no
                    return _raise_or_call(obs, obs.max_raise)
                return _check_or_fold(obs)
            if facing_raise:
                if score >= self.three_bet_score:
                    self.aggressor_hand = obs.hand_no
                    return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call * 3)
                if score >= self.call_score and obs.to_call <= obs.my_stack // 6:
                    return Action.call()
                return _check_or_fold(obs)
            if score >= self.open_score and RAISE in obs.legal:
                self.aggressor_hand = obs.hand_no
                limpers = sum(1 for s in range(obs.n_players) if obs.in_hand[s] and obs.bets[s] >= bb) - 1
                return _raise_or_call(obs, self.open_bb * bb + max(0, limpers) * bb)
            return _check_or_fold(obs)
        strong = top_pair_or_better(obs.hole, obs.board)
        aggressor = self.aggressor_hand == obs.hand_no
        if obs.to_call == 0:
            if strong and RAISE in obs.legal:
                return self._bet(obs)
            if aggressor and RAISE in obs.legal and self.bet_street != (obs.hand_no, obs.street):
                if obs.street == 1:
                    return self._bet(obs)
                if obs.street == 2:
                    if self.barrel_hand[0] != obs.hand_no:
                        self.barrel_hand = (obs.hand_no, self.rng.random() < self.barrel_frac)
                    if self.barrel_hand[1]:
                        return self._bet(obs)
            return Action.check()
        if not strong:
            return Action.fold()
        if made_category(obs.hole, obs.board) >= 2 and RAISE in obs.legal:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
        return Action.call()


class TimeoutThenRecover(_CostModel, _Base):
    """Plays an inner bot (naive by default) for the first N hands, then sleeps past the budget on
    every decision: state that grows, a cache that fills, a leak. N is drawn per table from
    [first_fail_lo, first_fail_hi] (30..120). Recovery is not modeled; the name is the archetype's
    slot in the field, and the knob to add if a real bot shows one is an outage length."""

    def __init__(self, seed: Optional[int] = None, inner: str = "naive", first_fail_lo: int = 30,
                 first_fail_hi: int = 120, sleep_s: float = 0.002):
        super().__init__(seed)
        self.inner = make_bot(inner, seed)
        self.lo, self.hi, self.sleep_s = first_fail_lo, first_fail_hi, sleep_s
        self.fail_from = self.rng.randint(self.lo, self.hi)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self.fail_from = self.rng.randint(self.lo, self.hi)
        self.inner.new_table(rules, seat, n_players)

    def failing(self, hand_no: int) -> bool:
        return hand_no >= self.fail_from

    def act(self, obs: Observation) -> Action:
        fail = self.failing(obs.hand_no)
        if fail:
            self._sleep(self.sleep_s)
        a = self.inner.act(obs)
        if self.cost_model:
            self.last_cost_ns = int(self.sleep_s * 1e9) if fail else getattr(self.inner, "last_cost_ns", None)
        return a

    def hand_end(self, result: HandResult) -> None:
        self.inner.hand_end(result)


class TimeoutBurst(TimeoutThenRecover):
    """TimeoutThenRecover with recovery: from hand N (30..120) it times out for an outage of `outage` hands (10..30),
    plays normally for `uptime` hands (20..50), and repeats; every length is drawn per table. A cache rebuilt now and
    then, a leak that a restart clears. It is the field's check that a read lets go of a seat that came back."""

    def __init__(self, seed: Optional[int] = None, inner: str = "naive", first_fail_lo: int = 30,
                 first_fail_hi: int = 120, sleep_s: float = 0.002, outage: tuple = (10, 30), uptime: tuple = (20, 50)):
        self.outage, self.uptime = outage, uptime
        super().__init__(seed, inner, first_fail_lo, first_fail_hi, sleep_s)
        self._windows = self._draw_windows()

    def _draw_windows(self) -> list:
        out, h = [], self.fail_from
        while h < 1000:
            n = self.rng.randint(*self.outage)
            out.append((h, h + n))
            h += n + self.rng.randint(*self.uptime)
        return out

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self._windows = self._draw_windows()

    def failing(self, hand_no: int) -> bool:
        for lo, hi in self._windows:
            if hand_no < lo:
                return False
            if hand_no < hi:
                return True
        return False


class HeroClone(_Base):
    """Hero built with a dict of dotted Config overrides (hero.config_from_dict), on top of
    HERO_CONFIG. Subclasses set OVERRIDES for named presets. Falls back to ChartTAG like Hero
    when the strategy package is missing."""

    OVERRIDES: dict = {}

    def __init__(self, seed: Optional[int] = None, overrides: Optional[dict] = None):
        super().__init__(seed)
        self.overrides = dict(HERO_CONFIG or {})
        self.overrides.update(self.OVERRIDES)
        self.overrides.update(overrides or {})
        try:
            from ..strategy.hero import config_from_dict, make_bot as _make_hero  # type: ignore[import-not-found]

            self.impl = _make_hero(config_from_dict(self.overrides, seed=seed))
        except Exception:  # noqa: BLE001 - strategy may not exist yet
            self.impl = ChartTAG(seed)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.impl.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.impl.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end(result)


class HeroTight(HeroClone):
    """Hero preset: opens and defends less, 3-bets a narrower slice, needs a stronger tier to value bet."""

    OVERRIDES = {
        "preflop.open_frac": {1: 0.30, 2: 0.32, 3: 0.20, 4: 0.14, 5: 0.11, 6: 0.09, 7: 0.08},
        "preflop.open_frac_default": 0.07,
        "preflop.three_bet_frac": 0.035,
        "preflop.call_raise_frac": 0.30,
        "pushfold.threshold_bb": 10.0,
        "postflop.cbet_freq_ip_dry": 0.45,
        "postflop.value_tier": 5,
        "postflop.semibluff_freq": 0.3,
    }


class HeroLoose(HeroClone):
    """Hero preset: opens and defends more, 3-bets wider, c-bets and semi-bluffs more often."""

    OVERRIDES = {
        "preflop.open_frac": {1: 0.50, 2: 0.55, 3: 0.38, 4: 0.28, 5: 0.22, 6: 0.18, 7: 0.15},
        "preflop.open_frac_default": 0.14,
        "preflop.three_bet_frac": 0.08,
        "preflop.call_raise_frac": 0.60,
        "pushfold.threshold_bb": 15.0,
        "postflop.cbet_freq_ip_dry": 0.8,
        "postflop.semibluff_freq": 0.7,
    }


# ----- rivals: other teams' bots behind an adapter to the interface they were built against ------


class _KitObs:
    """The observation shape the red-team brief promised (docs/drills/redteam/redteam-1.md, kit.py):
    the same fields as our Observation, with `legal` a set of strings, `history` a list of
    (seat, (kind, amount)) tuples and `hand_no` 1-based."""

    __slots__ = ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot",
                 "to_call", "min_raise", "max_raise", "legal", "hand_no", "blinds", "history")


_KIT_ACTIONS = {"fold": Action.fold(), "check": Action.check(), "call": Action.call()}
_KIT_LEGAL: dict[frozenset, set] = {}  # our frozenset[ActionKind] -> the kit's set of strings, memoized


class RivalBot(_Base):
    """Red-team rival 1 (hyperion.sim.rivals.rival1), unchanged, behind the kit interface it was built
    against: `legal` as strings, history as (seat, (kind, amount)), 1-based hand_no, rules as a dict.
    The rival's answer ('kind', amount_total) becomes an Action clamped to the observation, and the
    engine times the adapter and the rival together. The rival seeds itself per table; `seed` is unused."""

    MODULE = "rival1"
    PACKAGE = ".rivals"  # the field's persona bots live in .field

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        import importlib

        self.impl = importlib.import_module(f"{self.PACKAGE}.{self.MODULE}", __package__).Bot()
        self._hist: list = []  # converted history for the current hand, extended as it grows
        self._hist_n = 0
        self._hist_hand = -1

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self._hist, self._hist_n, self._hist_hand = [], 0, -1
        self.impl.new_table(self.kit_rules(rules, n_players), seat, n_players)

    def kit_rules(self, rules: Rules, n_players: int) -> dict:
        """The rules dict the kit passes to new_table ("may be partial")."""
        return {"starting_stack": rules.starting_stack, "hand_cap": rules.max_hands, "n_players": n_players,
                "blinds": rules.blind_levels}

    def to_kit(self, obs: Observation) -> _KitObs:
        """Our Observation as the kit's. History is converted incrementally: the engine hands out a
        fresh copy each decision but the prefix never changes within a hand."""
        k = _KitObs()
        k.hole, k.board, k.street, k.seat, k.button = obs.hole, obs.board, obs.street, obs.seat, obs.button
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

    @staticmethod
    def from_kit(answer, obs: Observation) -> Action:
        """('kind', amount_total) -> Action, clamped to what is legal. Anything unreadable is a check or fold."""
        try:
            kind, amount = answer
        except (TypeError, ValueError):
            return _check_or_fold(obs)
        if kind == "raise":
            try:
                return Action.raise_to(int(amount)).clamp(obs)
            except (TypeError, ValueError):
                return _check_or_fold(obs)
        a = _KIT_ACTIONS.get(kind)
        return a.clamp(obs) if a is not None else _check_or_fold(obs)

    def act(self, obs: Observation) -> Action:
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas})


class Rival2Bot(_FixedSpeedInModel, RivalBot):
    """Red-team rival 2 (hyperion.sim.rivals.rival2), unchanged, behind the same kit adapter as rival 1.
    Built blind against the same brief, so it reads the same fields (hole, board, street, seat, button,
    stacks, bets, in_hand, pot, to_call, min/max_raise, legal as strings, 1-based hand_no, blinds,
    history as (seat, (kind, amount))) and only `hand_no` from hand_end; it ignores the rules dict.
    Importing it costs ~1.2 s (import-time Monte Carlo, push/fold solve) and ends in gc.freeze(),
    which applies to the whole process. Its import-time equity tables stop at 1500 boards or after 2.4 s; the adapter
    imports it with its clock held still, so every process builds all 1500 (what a quiet host does) at any load. Its
    postflop sampler stops on the wall clock (260 us, a hard stop at 520 us), so as built its play follows the host.
    In mode "model" it plays at a fixed speed (_FixedSpeedInModel): no time budget, no hard stop, a fixed
    MODEL_SAMPLES (110: what it draws heads-up here on a quiet host, as tools/swap.py's R2_SAMPLES), so model-mode
    runs replay exactly; strict and measure play it as built."""

    MODULE = "rival2"
    MODEL_SAMPLES = 110

    def __init__(self, seed: Optional[int] = None):
        if "hyperion.sim.rivals.rival2" not in sys.modules:
            real = time.perf_counter
            time.perf_counter = lambda: 0.0  # its import-time tables then always build all 1500 boards
            try:
                from .rivals import rival2  # noqa: F401
            finally:
                time.perf_counter = real
        super().__init__(seed)

    def _set_speed(self, fixed: bool) -> None:
        im = self.impl
        if fixed:
            wall = type(im).equity_mc
            im.MC_BUDGET_US, im.MC_MAX = 1e9, self.MODEL_SAMPLES
            im.equity_mc = lambda hole, board, cuts, deadline, fits=None, hard=None: wall(
                im, hole, board, cuts, deadline, fits, deadline + 1.0)
        else:
            for k in ("MC_BUDGET_US", "MC_MAX", "equity_mc"):
                im.__dict__.pop(k, None)


class Rival3Bot(RivalBot):
    """Red-team rival 3 (hyperion.sim.rivals.rival3), unchanged, behind the same kit adapter; the holdout,
    never tuned against. Built blind against the same brief, it reads the same act() fields as rivals 1 and 2
    and only `n_players` from new_table. Unlike them it learns in hand_end: it replays `history` there, in the
    kit's (seat, (kind, amount)) shape, to count the actions that came after its last decision, so this
    adapter passes the hand's history as the rival's own engine did (without it the rival scored ~0.3 lower
    there; docs/drills/redteam/redteam-3.md section 5). It imports in ~20 ms, has no wall-clock time box and
    seeds its one RNG at construction, so its play is bit-reproducible."""

    MODULE = "rival3"

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas,
                            "history": [(s, (a.kind.value, a.amount)) for s, a in result.history]})


class Rival4Bot(RivalBot):
    """Red-team rival 4 (hyperion.sim.rivals.rival4), unchanged, behind the same kit adapter; the judge: no candidate
    core is measured against it or tuned on it before the one final comparison. Built blind against the same brief
    with no assigned philosophy, it reads the same act() fields as rivals 1 to 3. Two differences, both things the
    brief's kit may pass: new_table's rules dict carries `payouts` (Rules.payouts), which the rival reads, so its exact
    ICM prices every all-in on the table that scores it rather than the brief's 10/7/5/4/3/2/1/0 (exact for any table
    whose places from third down are equal steps, 8..1 included; docs/drills/redteam/redteam-4.md section 3); and
    hand_end passes the hand's history in the kit's (seat, (kind, amount)) shape, as rival 3's does, from which it
    counts each seat's VPIP, raises and shoves. Its own engine passed neither. It imports in ~15 ms, has no wall-clock
    time box and seeds its one RNG at construction, so its play is bit-reproducible. It has no cost model, so the
    engine's mode "model" never folds it for time."""

    MODULE = "rival4"

    def kit_rules(self, rules: Rules, n_players: int) -> dict:
        return {**super().kit_rules(rules, n_players), "payouts": list(rules.payouts)}

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas,
                            "history": [(s, (a.kind.value, a.amount)) for s, a in result.history]})


class Rival5Bot(_FixedSpeedInModel, Rival4Bot):
    """Red-team rival 5 (hyperion.sim.rivals.rival5), unchanged, behind the same kit adapter as rival 4: payouts with
    the rules, the hand's history at hand_end. The second judge: built blind by a fresh team against the same brief and
    kit (docs/drills/redteam/rival5_bot.py), never tuned on; the compose agent measures the candidates on it once, at
    the end, in `judge2` and `judge2_night`. Smoke tests check only that it plays legally and in time. It reads
    `hand_cap` from the rules and builds its per-seat counts from the history it sees in act(); its ICM is the brief's
    table, hard-coded.
    Its postflop sampler stops on the wall clock (130 us, checked every four trials), so its play follows the host,
    as rival 2's does. In mode "model" it plays at a fixed speed (_FixedSpeedInModel): its clock advances STEP_US per
    read, so it samples a fixed amount and replays exactly; 4.0 us is the CPU time of four trials against two opponents
    on this box (2.9 heads-up, 6.8 against three). Strict and measure modes play the judge as built."""

    MODULE = "rival5"
    STEP_US = 4.0

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.mod = sys.modules[type(self.impl).__module__]
        self._now = 0.0
        self._clock_ns = types.SimpleNamespace(perf_counter=self._clock)

    def _clock(self) -> float:
        self._now += self.STEP_US * 1e-6
        return self._now

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        self.mod.time = self._clock_ns if self.fixed_speed else time
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


# ----- the night field: other agents' one-hour builds behind the kit each was built against (hyperion/sim/field/) ----


class _KitAPlayer:
    __slots__ = ("name", "stack", "bet", "folded", "all_in")

    def __init__(self, name, stack, bet, folded, all_in):
        self.name, self.stack, self.bet, self.folded, self.all_in = name, stack, bet, folded, all_in


class _KitAState:
    """Fake kit A's GameState (hyperion/drills/fakekits/kit_a/kit.py) with the fields its bots read."""

    __slots__ = ("hand", "community", "street", "my_index", "dealer_index", "players", "my_stack", "pot_size",
                 "current_bet", "my_bet", "legal_moves", "min_raise", "max_raise", "hand_number", "small_blind",
                 "big_blind", "action_log", "discards")


_KIT_A_CARD = tuple(("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")[c >> 2] + "cdhs"[c & 3]
                    for c in range(52))
_KIT_A_STREET = ("preflop", "flop", "turn", "river")
_KIT_A_LEGAL: dict[frozenset, list] = {}
_KIT_A_ACTIONS = {"FOLD": Action.fold(), "CHECK": Action.check(), "CALL": Action.call()}


class TrackBKitABot(_Base):
    """Drill 3's Track B bot (hyperion.sim.field.trackb3), unchanged, behind fake kit A's interface: an Agent with
    new_game(my_index, n_players, starting_stack), act(GameState) -> "FOLD" | "CHECK" | "CALL" | "RAISE:<total>" and
    hand_over(hand_number, chip_change), cards as strings ("10d"), pot_size including this street's bets, and the
    hand's action log as (seat, "RAISE:120"). One adaptation: the bot was built for a bounty twist (a showdown won
    holding a Seven pays 50 chips) and reads the module constant BOUNTY_CHIPS at every decision; it is set to 0, as
    plain hold'em pays none. The rest plays as built, including the brief's 10/7/5/4/3/2/1/0 table in its ICM.
    Imports in ~2.7 s (its 7-card evaluator and 169-class equity tables); lookups and arithmetic after."""

    MODULE = "trackb3"

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        import importlib

        mod = importlib.import_module(f".field.{self.MODULE}", __package__)
        mod.BOUNTY_CHIPS = 0
        self.impl = mod.Agent()
        self._log: list = []
        self._log_n = 0
        self._log_hand = -1

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self._log, self._log_n, self._log_hand = [], 0, -1
        self.impl.new_game(seat, n_players, rules.starting_stack)

    def to_kit(self, obs: Observation) -> _KitAState:
        st = _KitAState()
        bets, stacks, in_hand = obs.bets, obs.stacks, obs.in_hand
        st.hand = [_KIT_A_CARD[c] for c in obs.hole]
        st.community = [_KIT_A_CARD[c] for c in obs.board]
        st.street = _KIT_A_STREET[obs.street] if obs.street < 4 else "river"
        st.my_index, st.dealer_index = obs.seat, obs.button
        st.players = [_KitAPlayer("player%d" % i, stacks[i], bets[i], not in_hand[i], in_hand[i] and stacks[i] == 0)
                      for i in range(len(stacks))]
        st.my_stack = stacks[obs.seat]
        st.pot_size = obs.pot + sum(bets)
        st.current_bet = max(bets)
        st.my_bet = bets[obs.seat]
        legal = _KIT_A_LEGAL.get(obs.legal)
        if legal is None:
            legal = _KIT_A_LEGAL[obs.legal] = [m for m in ("FOLD", "CHECK", "CALL", "RAISE")
                                               if ActionKind(m.lower()) in obs.legal]
        st.legal_moves = legal
        st.min_raise, st.max_raise = obs.min_raise, obs.max_raise
        st.hand_number = obs.hand_no + 1
        st.small_blind, st.big_blind = obs.blinds
        src = obs.history
        n = len(src)
        if obs.hand_no != self._log_hand or n < self._log_n:
            self._log, self._log_n, self._log_hand = [], 0, obs.hand_no
        if n > self._log_n:
            self._log.extend((s, "RAISE:%d" % a.amount if a.kind is RAISE else a.kind.value.upper())
                             for s, a in src[self._log_n:])
            self._log_n = n
        st.action_log = self._log
        st.discards = {}
        return st

    @staticmethod
    def from_kit(answer, obs: Observation) -> Action:
        if isinstance(answer, str):
            if answer.startswith("RAISE:"):
                try:
                    return Action.raise_to(int(answer[6:])).clamp(obs)
                except ValueError:
                    return _check_or_fold(obs)
            a = _KIT_A_ACTIONS.get(answer)
            if a is not None:
                return a.clamp(obs)
        return _check_or_fold(obs)

    def act(self, obs: Observation) -> Action:
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_over(result.hand_no + 1, result.deltas[self.seat])


_KIT_B_SUITS = "CDHS"
_KIT_B_CARD = tuple({"rank": (c >> 2) + 2, "suit": _KIT_B_SUITS[c & 3]} for c in range(52))
_KIT_B_LEGAL: dict[frozenset, list] = {}


class TrackBKitBBot(_Base):
    """Drill 5's Track B bot (hyperion.sim.field.trackb5), unchanged, behind fake kit B's interface: module functions
    decide(observation: dict) -> {"action": ..., "by": <increment over the highest bet>}, on_table_start(info) and
    on_hand_end(info), cards as {"rank": 2..14, "suit": "H"}, no action history. Two adaptations:
    - its state lives in module globals (P, H, S, C), so each instance keeps its own dicts and binds them into the
      module before every call: two seats of it at one table (`night@trackb5` drawing it too) never share a profile;
    - it was built for permuted_ranks (seed 0) and maps printed ranks to strength through the module list REMAP at
      every parse; REMAP is set from Rules.rank_order at each table, so it is the identity on plain hold'em and right
      under any permutation the rules sheet gives.
    Imports in ~1.4 s (evaluator and equity tables); lookups and arithmetic after."""

    MODULE = "trackb5"

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        import importlib

        self.mod = importlib.import_module(f".field.{self.MODULE}", __package__)
        self._state = None

    def _bind(self) -> None:
        m, st = self.mod, self._state
        m.P, m.H, m.S, m.C, m.REMAP = st

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self._state = ({}, {"hand": None, "street": -1, "snap": {}, "cur": 0, "seen": set(), "flags": {}},
                       {"seat": None, "n": 0, "stack0": 2000, "total": 16000, "est": [], "hand_start": None,
                        "hand_start_id": None},
                       {"pts": None}, list(rules.rank_order))
        self._bind()
        self.mod.on_table_start({"seat": seat, "players": n_players, "stack": rules.starting_stack,
                                 "blinds": {"sb": rules.small_blind, "bb": rules.big_blind}})

    @staticmethod
    def to_kit(obs: Observation) -> dict:
        bets, stacks, in_hand = obs.bets, obs.stacks, obs.in_hand
        current = max(bets)
        legal = _KIT_B_LEGAL.get(obs.legal)
        if legal is None:
            legal = _KIT_B_LEGAL[obs.legal] = [k.value for k in _KIND_ORDER if k in obs.legal]
        return {
            "hand_id": obs.hand_no,
            "street": len(obs.board),
            "blinds": {"sb": obs.blinds[0], "bb": obs.blinds[1]},
            "hand": {"cards": [_KIT_B_CARD[c] for c in obs.hole]},
            "table": {"board": [_KIT_B_CARD[c] for c in obs.board], "pot": obs.pot, "button": obs.button,
                      "players": [{"seat": i, "chips": stacks[i], "committed": bets[i], "active": bool(in_hand[i])}
                                  for i in range(len(stacks))]},
            "you": {"seat": obs.seat, "to_call": obs.to_call, "min_raise_by": obs.min_raise - current,
                    "max_raise_by": obs.max_raise - current},
            "actions": list(legal),
        }

    @staticmethod
    def from_kit(d, obs: Observation) -> Action:
        try:
            kind = d["action"]
            if kind == "raise":
                return Action.raise_to(max(obs.bets) + int(d["by"])).clamp(obs)
            a = _KIT_ACTIONS.get(kind)
        except (TypeError, KeyError, ValueError):
            return _check_or_fold(obs)
        return a.clamp(obs) if a is not None else _check_or_fold(obs)

    def act(self, obs: Observation) -> Action:
        self._bind()
        return self.from_kit(self.mod.decide(self.to_kit(obs)), obs)

    def hand_end(self, result: HandResult) -> None:
        self._bind()
        self.mod.on_hand_end({"hand_id": result.hand_no, "delta": result.deltas[self.seat]})


class PersonaBot(RivalBot):
    """A persona bot of the night field (hyperion.sim.field.agent_*), unchanged, behind the red-team kit adapter it was
    built against (the same brief and kit as rivals 1 to 5: legal as strings, history as (seat, (kind, amount)),
    1-based hand_no). Each was built by an agent in one hour playing one kind of student team, with no access to this
    repository (docs/drills/field/agent_*.md, the builders' logs). The brief says new_table's rules and hand_end's
    result "may be partial", so this passes what a kit may: the payouts (Rules.payouts) with the rules, the hand's
    history with the result, as rival 4's adapter does. A bot that ignores them is unaffected."""

    PACKAGE = ".field"
    MODULE = "agent_charts"

    def __init__(self, seed: Optional[int] = None):
        _Base.__init__(self, seed)
        from .field import load

        self.impl = load(self.MODULE).Bot()  # with the brief's kit importable as `kit` while it loads
        self._hist: list = []
        self._hist_n = 0
        self._hist_hand = -1

    def kit_rules(self, rules: Rules, n_players: int) -> dict:
        return {**super().kit_rules(rules, n_players), "payouts": list(rules.payouts)}

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas,
                            "history": [(s, (a.kind.value, a.amount)) for s, a in result.history]})


class AgentChartsBot(PersonaBot):
    """Persona `agent_charts`: a strong live cash player's team. Positional open and 3-bet charts typed from memory,
    standard c-bets, value-heavy TAG postflop with pot-odds calls, Chen-percentile shove/fold under 15 bb; no ICM, no
    opponent model. Frozen at minute 17. Reads no rules and nothing at hand_end; one RNG with a fixed seed."""

    MODULE = "agent_charts"


class AgentMonteCarloBot(_FixedSpeedInModel, PersonaBot):
    """Persona `agent_montecarlo`: a three-person team that insisted on Monte Carlo equity against the players still in
    the hand, compared with pot odds, as fast as pure Python allows. Preflop from equity tables simulated at import
    (seeded); postflop a sampler with a 0.18 ms wall-clock budget and an early stop; no charts, no ICM, no bluffs.
    Frozen at minute 46. Three adaptations, all about running in one process with every other bot:
    - it calls gc.disable() at import, process-wide; hyperion.sim.field.load turns the collector back on (in the
      tournament it runs alone in its process);
    - its sampler draws from the global `random.random`, shared here with everything else in the process; each seat
      gets its own generator seeded from the seat seed, bound into the module before each decision;
    - its clock is the wall clock as built (strict and measure modes). In mode "model" it plays at a fixed speed
      (_FixedSpeedInModel): its clock advances STEP_US per read, so its sample counts no longer follow the host;
      3.5 us is the CPU time of one four-trial block between its clock checks on this box (0.8-1.1 us a trial, 1-3
      opponents), so it samples as on a quiet host and replays exactly."""

    MODULE = "agent_montecarlo"
    STEP_US = 3.5

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)  # hyperion.sim.field.load turns the garbage collector back on after the import
        self.mod = sys.modules[type(self.impl).__module__]
        self._rand = random.Random((seed or 0) * 1_000_003 + 0xF2).random
        self._now = 0.0

    def _clock(self) -> float:
        self._now += self.STEP_US * 1e-6
        return self._now

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        m = self.mod
        m._rand = self._rand
        m._perf = self._clock if self.fixed_speed else time.perf_counter
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


class AgentPushFoldBot(_FixedSpeedInModel, PersonaBot):
    """Persona `agent_pushfold`: an ICM push/fold quant team. Exact Malmuth-Harville ICM (the brief's 10/7/5/4/3/2/1/0,
    hard-coded), push charts typed from memory of Nash charts with a bubble-factor adjustment, ICM-required equity to
    call shoves from an embedded 169-class equity table, tiered postflop. Frozen at minute 46. Reads no rules and
    nothing at hand_end; one RNG with a fixed seed. A 260 us wall-clock guard (its _el()) skips its heaviest jam EV
    when late, so as built its play follows the host; in mode "model" it plays at a fixed speed (_FixedSpeedInModel):
    _el() reads 0, the guard never fires and model-mode runs replay exactly."""

    MODULE = "agent_pushfold"

    def _set_speed(self, fixed: bool) -> None:
        if fixed:
            self.impl._el = lambda: 0.0
        else:
            self.impl.__dict__.pop("_el", None)


class AgentDefaultBot(PersonaBot):
    """Persona `agent_default`: a coding agent told only "build us the strongest bot you can". Rule-based TAG: Chen
    preflop by position, made-hand and draw classes postflop with pot-odds calls, short-stack push/fold, light per-seat
    VPIP and raise counts from the history. Frozen at minute 45. Reads `starting_stack` from the rules; imports
    `kit.Agent` with no fallback, so it loads with the brief's kit present."""

    MODULE = "agent_default"


# ----- the outside field: fresh one-hour builds for the climb (docs/drills/goal-plan.md), never tuned on ---------


class OutsideVeteransBot(PersonaBot):
    """Outside `out_veterans`: two former university pokerbots finalists who prepared for two weeks. ICM push/fold at
    13 bb or less with seat-adjusted call chances, ICM all-in calls with a 0.15-point margin, re-shoves over one open
    at 25 bb or less, wide positional opens, steals when the seats behind time out or fold, tight value postflop.
    Frozen at minute 38 (md5 bffa539c). No clock, no RNG beyond its own; plays the same in every mode."""

    MODULE = "outside_veterans"


class OutsideSelfPlayBot(_FixedSpeedInModel, PersonaBot):
    """Outside `out_selfplay`: a solo student whose agent self-play-tuned the bot in its own simulator for the hour.
    Monte Carlo tables at import, percentile push/fold at 13 bb or less, very tight committed calls (equity over pot
    odds + 0.35), a range-narrowed postflop Monte Carlo capped at 140 us of wall time (one clock read per sample) or
    150 samples. Pauses the garbage collector inside act(). Frozen at minute 45 (md5 5e739fa4). In mode "model" it
    plays at a fixed speed: its clock advances STEP_US per read. 4.5 us is the wall time per sample measured here (5.5 at
    load 5-6, less the load), so it draws about 31 samples in its 140 us, as a quiet host would."""

    MODULE = "outside_selfplay"
    STEP_US = 4.5

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.mod = sys.modules[type(self.impl).__module__]
        self._ns = 0
        self._clock_ns = types.SimpleNamespace(perf_counter_ns=self._clock)

    def _clock(self) -> int:
        self._ns += int(self.STEP_US * 1000)
        return self._ns

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        self.mod.time = self._clock_ns if self.fixed_speed else time
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


class OutsideLagBot(PersonaBot):
    """Outside `out_lag`: three online grinders playing loose-aggressive. Percentile opens by position (about 20% UTG
    to 85% SB), wide re-shoves over opens at 13-28 bb, push/fold at 13 bb or less, all-in calls with a margin up to
    0.40, endgame pressure when covering, barrels when checked to. Frozen at minute 39 (md5 7f2cf887). Own seeded RNG,
    no clock; plays the same in every mode."""

    MODULE = "outside_lag"


class OutsideQuantsBot(_FixedSpeedInModel, PersonaBot):
    """Outside `out_quants`: two quant interns. An embedded 169x169 all-in equity table and fictitious-play push/fold
    equilibria for 1-7 players behind and 1-30 bb, exact ICM for 10/7/5/4/3/2/1/0 (hard-coded), push/fold at 16 bb or
    less, a range-narrowed postflop Monte Carlo with a 250 us wall-clock budget (one clock read per iteration after
    the fourth). gc.freeze() at import, process-wide. Frozen at minute 36 (md5 27d9b2cb). In mode "model" it plays at
    a fixed speed: its clock advances STEP_US per read. 5.5 us is the wall time per iteration measured here (6.9 at load
    5-6, less the load), so it runs about 4 + 45 iterations in its 250 us, as a quiet host would."""

    MODULE = "outside_quants"
    STEP_US = 5.5

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.mod = sys.modules[type(self.impl).__module__]
        self._now = 0.0

    def _clock(self) -> float:
        self._now += self.STEP_US * 1e-6
        return self._now

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        self.mod.perf_counter = self._clock if self.fixed_speed else time.perf_counter
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


# ----- the elite field: prepared top-team builds for the climb (owner's direction, 2026-11-01) --------------------


class _EliteBot(PersonaBot):
    """An elite build, behind the red-team adapter. Each was written with an unseeded `random.Random()` (elite 2 also
    reseeds from the time of day at every table start), so here the bot's generator is reseeded from the seat seed after
    every table start: every rotation and every swap replays exactly, as for the other field bots."""

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self._seed = 0 if seed is None else int(seed)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self.impl.rng.seed(self._seed * 1_000_003 + 0xE11)


class Elite1Bot(_EliteBot):
    """Elite `elite1`: decisions in points (ICM) for every all-in-sized spot, short-stack shove/fold by expected points
    with per-seat call rates, ranges from measured frequencies with depth and position priors, settles unseen folds
    from the next stacks, a 5 us postflop classifier against continuing/betting ranges, heads-up opens 85%. No clock.
    Frozen at about minute 107 (md5 9bf36037). In the tuning fields `elite` and `elite_night`."""

    MODULE = "elite1"


class Elite2Bot(_EliteBot):
    """Elite `elite2`: exact fast ICM for 10/7/5/4/3/2/1/0 (hard-coded), push/fold at 14 bb or less with blended call
    rates, equity-against-range preflop from 169x169 tables, postflop exact enumeration over a range narrowed by the
    bettor's aggression and size, EV-sized bets (0.4-1.1 pot). Reads the clock only into an unused field. Frozen at
    minute 104 (md5 70c29e17). In the tuning fields `elite` and `elite_night`."""

    MODULE = "elite2"


class Elite3Bot(_FixedSpeedInModel, _EliteBot):
    """Elite `elite3`: every big decision in tournament points (exact ICM with dead money), push/fold at about 13 bb
    with per-seat call rates, a postflop Monte Carlo capped at 85 us of wall time (module-level `_pc`, read every
    iteration multiway and every fourth heads-up) over ranges narrowed by bet size and barrels, adaptive opens. Frozen at
    minute 104 (md5 c5e956bd). The held-out elite judge (`elite_judge`): never tuned on. In mode "model" it plays at a
    fixed speed: its clock advances STEP_NS per read (measured wall time per read here, less the load)."""

    MODULE = "elite3"
    STEP_NS = 8000  # 9.9 us wall per read measured at load 5-13 (2026-11-02), less the load

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.mod = sys.modules[type(self.impl).__module__]
        self._ns = 0

    def _clock(self) -> int:
        self._ns += self.STEP_NS
        return self._ns

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        self.mod._pc = self._clock if self.fixed_speed else time.perf_counter_ns
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


# ----- the exploiter: a black-box attacker of the ship bot (S2), a test opponent, never in a night pool -------------


class Exploiter1Bot(_FixedSpeedInModel, PersonaBot):
    """Test opponent `exploiter1`: the climb's red-team exploiter (docs/drills/exploiter/FINDINGS.md), built in ~80
    minutes by a fresh agent that played the packed F (d3a7ca5) only as a black box. It finds F's seat from its bet-size
    fingerprint, then 3-bets F's opens at the minimum, opens 90% heads-up, reads F's bet sizes and barrels it; against
    the rest it is a push/fold and equity-chart bot with a Monte Carlo postflop. Reads `payouts` from the rules.
    Frozen at md5 183c150c. Its postflop Monte Carlo stops on `time.perf_counter` (a 200 us budget, one clock read per
    sample after the tenth), so as built its play follows the host; in mode "model" it plays at a fixed speed: its clock
    advances STEP_US per read (calibration in docs/drills/s2-exploit-fixes-log.md), so it replays exactly. Never in a
    night pool (fields `exploit`, `exploit_hu`, `exploit_3`)."""

    MODULE = "exploiter1"
    STEP_US = 5.5  # wall time per clock read over a whole Monte Carlo decision: 5.8 heads-up, 6.6 at 8-max at load 5

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.mod = sys.modules[type(self.impl).__module__]
        self._now = 0.0
        self._clock_ns = types.SimpleNamespace(perf_counter=self._clock)

    def _clock(self) -> float:
        self._now += self.STEP_US * 1e-6
        return self._now

    def _set_speed(self, fixed: bool) -> None:
        pass  # read at every act()

    def act(self, obs: Observation) -> Action:
        self.mod.time = self._clock_ns if self.fixed_speed else time
        return self.from_kit(self.impl.act(self.to_kit(obs)), obs)


class Exploiter2Bot(PersonaBot):
    """Test opponent `exploiter2`: the climb's second red-team exploiter (docs/drills/exploiter2/FINDINGS.md), built in
    ~2 hours by a fresh agent that played F with FIN (r3.v3_defend, half-pot dry c-bet) only as a black box. Against
    F's blind opens it 3-bets the top 18% to 3x and flat-calls to 80%; it raises F's small postflop bets and folds to
    its big ones (F's bet size names its hand), stabs 0.6 pot when checked to and leads 0.4 pot into the preflop
    raiser; heads-up its small blind min-raises every hand. Per-seat fold counts gate its bluffs. Against the rest it is
    a percentile-range and push/fold bot with rule-based postflop. Frozen at md5 d77551bc (exploit_bot.py; five modules
    beside it in hyperion/sim/field/exploiter2/, loaded by field.load_flat). No clock. Its one RNG (base.py) seeds
    itself from the seat number at new_table; here it is reseeded from the seat seed at every table, so each table
    draws its own stream and runs replay exactly. Never in a night pool (fields `exploit2`, `exploit2_hu`,
    `exploit2_3`)."""

    PARTS = ("ev", "pre_table", "mat_table", "base", "trk")

    def __init__(self, seed: Optional[int] = None):
        _Base.__init__(self, seed)
        from .field import load_flat

        self.impl = load_flat("exploiter2", self.PARTS, "exploit_bot", scrub_env=("EXPP",)).Bot()
        self._seed = seed or 0
        self._hist, self._hist_n, self._hist_hand = [], 0, -1

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        self.impl.rng = random.Random(self._seed * 1_000_003 + 0xE2)


# ----- the hybrid candidate: rival 2's decision core behind Hero's shell ---------------------------------------


HYBRID_CONFIG: Optional[dict] = None  # flat HybridConfig overrides for every hybrid built here ({"mc_max": 48})


class HybridBot(_Base):
    """The hybrid candidate (hyperion.hybrid): rival 2's decision core on plain hold'em behind Hero's shell (Rules,
    rank remap, variant decisions, SafeBot, Hero for what the core cannot represent). Its fallback Hero takes the
    same dotted overrides as `hero` (HERO_CONFIG). A candidate measured against Hero, not a replacement."""

    CORE = "rival2"
    EXPLOIT = None  # the exploit layer in front of it: None = off, "hero" = the params Hero's Config ships

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        from ..hybrid import make_bot as _make_hybrid

        over = {**(HYBRID_CONFIG or {}), "core": self.CORE}
        if self.EXPLOIT is not None:
            over.setdefault("exploit", self.EXPLOIT)
        self.impl = _make_hybrid(seed=seed, overrides=over, hero_overrides=HERO_CONFIG)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.impl.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.impl.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.impl.hand_end(result)

    def variant_decide(self, prompt: dict):
        return self.impl.variant_decide(prompt)


class Hybrid3Bot(HybridBot):
    """The second hybrid candidate: rival 3's decision core (hyperion.hybrid.core3) behind the same shell as `hybrid`:
    payouts from Rules in its all-in prices, the hand's history at hand_end, Hero for what it cannot represent."""

    CORE = "rival3"


class HybridXBot(HybridBot):
    """`hybrid` with the exploit layer (hyperion/strategy/exploit.py) in front of every decision, with the params Hero's
    Config ships at this commit (identical to `hybrid` while Hero ships every spot off)."""

    EXPLOIT = "hero"


class Hybrid3XBot(Hybrid3Bot):
    """`hybrid3` with the exploit layer in front of every decision, with the params Hero's Config ships at this commit."""

    EXPLOIT = "hero"


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
    "montecarlo": MonteCarloBot,  # honest 200 rollouts: times out postflop in strict mode
    "montecarlo30": MonteCarloTimeout30,  # modeled: 30% of postflop decisions time out
    "pushfold": PushFoldBot,
    "loose_aggro": LooseAggroStudent,
    "timeout_then_recover": TimeoutThenRecover,
    "timeout_burst": TimeoutBurst,  # times out in outages of 10..30 hands, recovering in between
    "hero_tight": HeroTight,
    "hero_loose": HeroLoose,
    "rival1": RivalBot,  # red-team drill 1's bot through the kit adapter; `naive` stays available by name
    "rival2": Rival2Bot,  # red-team drill 2's computation-first bot through the same adapter
    "rival3": Rival3Bot,  # red-team drill 3's exploitation-first bot: the holdout, never tuned against
    "rival4": Rival4Bot,  # red-team drill 4's bot (no assigned philosophy): the judge of the final comparison
    "rival5": Rival5Bot,  # red-team drill 5's bot, built blind by a fresh team: the second judge (judge2, judge2_night)
    "trackb3": TrackBKitABot,  # drill 3's Track B one-hour build (kit A), in the night pool
    "trackb5": TrackBKitBBot,  # drill 5's Track B one-hour build (kit B), in the night pool
    "agent_charts": AgentChartsBot,  # persona: live-poker chart player's team (one-hour agent build), night pool
    "agent_default": AgentDefaultBot,  # persona: an agent told "build the strongest bot you can", night pool
    "agent_montecarlo": AgentMonteCarloBot,  # persona: a Monte Carlo equity team, night pool
    "agent_pushfold": AgentPushFoldBot,  # persona: an ICM push/fold quant team, night pool
    "out_veterans": OutsideVeteransBot,  # outside field (the climb): prepared veterans, never tuned on
    "out_selfplay": OutsideSelfPlayBot,  # outside field: an agent self-play-tuned for the hour, never tuned on
    "out_lag": OutsideLagBot,  # outside field: loose-aggressive grinders, never tuned on
    "out_quants": OutsideQuantsBot,  # outside field: import-time equilibria and exact ICM, never tuned on
    "elite1": Elite1Bot,  # elite field (prepared top-team build): tuning fields elite, elite_night
    "elite2": Elite2Bot,  # elite field: tuning fields elite, elite_night
    "elite3": Elite3Bot,  # elite field: the held-out elite judge (elite_judge), never tuned on
    "exploiter1": Exploiter1Bot,  # the S2 exploiter of F (black-box attacker): a test opponent, never in a night pool
    "exploiter2": Exploiter2Bot,  # the second exploiter (S11), of F with FIN: a test opponent, never in a night pool
    "hybrid": HybridBot,  # candidate: rival 2's decision core behind Hero's shell (hyperion.hybrid)
    "hybrid3": Hybrid3Bot,  # candidate: rival 3's decision core behind the same shell
    "hybrid_x": HybridXBot,  # `hybrid` with the exploit layer as Hero ships it
    "hybrid3_x": Hybrid3XBot,  # `hybrid3` with the exploit layer as Hero ships it
    "auction_tag": AuctionTAG,  # the auction entry's variant-aware opponent (bids by hand, reads others' cards)
    "keep2_tag": Keep2TAG,  # deal5_keep2's variant-aware opponent (five-card preflop, keeps by made hand and live draws)
}

# Opponents that need something from outside this repo. Each is registered only when its environment
# variable is set; otherwise asking for it raises BotUnavailable naming the variable. They are opponents
# only: nothing from them goes into Hero.
from .rivals import microholdem as _microholdem  # noqa: E402 - stdlib-only module; loads nothing until a bot is built

OPTIONAL_BOTS: dict[str, tuple[str, str]] = {
    # name -> (environment variable, what it must point at)
    "micro": (_microholdem.ENV_REPO, "a clone of github.com/ryankkhalil19/microholdem (MIT) with its _core "
              "compiled, and numpy importable; setup in hyperion/sim/rivals/microholdem.py"),
}
if os.environ.get(_microholdem.ENV_REPO):
    REGISTRY["micro"] = _microholdem.MicroholdemBot  # public-repo MicroAgent through our adapter (sparring)
_BY_CLASS = {cls.__name__.lower(): cls for cls in REGISTRY.values()}


class BotUnavailable(KeyError):
    """An optional bot (or a field that seats one) was asked for while its environment variable is unset."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


def _unavailable(name: str) -> BotUnavailable:
    var, what = OPTIONAL_BOTS[name]
    return BotUnavailable(f"bot {name!r} is disabled: {var} is not set (it must point at {what})")

# Named 8-bot fields for the runner (`--field`). Duplicated names take two seats.
FIELDS: dict[str, tuple[str, ...]] = {
    # the room as we expect it: one competent short-stacker, Monte Carlo bots in both flavours,
    # a loose-aggressive student, the red-team rival (in the seat the 40-minute bot `naive` had
    # until 2026-10-31), a TAG, and one bot that breaks mid-table
    "realistic": ("hero", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "rival1", "tag",
                  "timeout_then_recover"),
    # realistic with the twist read: the honest Monte Carlo seat and the TAG replaced by the entry's variant-aware bot
    "realistic_auction": ("hero", "montecarlo30", "auction_tag", "pushfold", "loose_aggro", "rival1", "auction_tag",
                          "timeout_then_recover"),
    "realistic_keep2": ("hero", "montecarlo30", "keep2_tag", "pushfold", "loose_aggro", "rival1", "keep2_tag",
                        "timeout_then_recover"),
    # `toss_or_holdem_aware`, `bounty_aware`, `short_deck_aware`: added by hyperion/sim/aware.py (end of this file)
    # the table where everybody did their homework, plus two Hero copies with other settings
    "strong": ("hero", "pushfold", "pushfold", "tag", "hero_tight", "hero_loose", "nit", "loose_aggro"),
    # the strong room with both rivals: rival 1 twice, rival 2 (in the seat montecarlo30 had until
    # 2026-10-31), the short-stacker, a TAG, a tight Hero and the loose student
    "top": ("hero", "rival1", "rival1", "pushfold", "tag", "hero_tight", "loose_aggro", "rival2"),
    # the same room weighted the other way: rival 2 twice, rival 1 once
    "top2": ("hero", "rival1", "rival2", "rival2", "pushfold", "tag", "hero_tight", "loose_aggro"),
    # the strong room with each of the three rivals once
    "top3": ("hero", "rival1", "rival2", "rival3", "pushfold", "tag", "hero_tight", "loose_aggro"),
    # the holdout: `realistic` with rival 3 in rival 1's seat. Hero is never tuned on rival 3 or on this field;
    # it is where a gain measured against rivals 1 and 2 shows whether it generalises
    "holdout": ("hero", "rival3", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag",
                "timeout_then_recover"),
    # the judge: `holdout` with rival 4 in rival 3's seat (so `realistic`'s bots with rival 4 for rival 1), and the
    # strong room with each of the four rivals once.
    # Rival 4 decides between the candidate cores in one final comparison: until then no candidate sits here beyond
    # smoke tests, and nobody tunes on it. `judge@hybrid3` etc. (below, and field_names) seat a candidate in Hero's seat
    "judge": ("hero", "rival4", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag", "timeout_then_recover"),
    "judge_top": ("hero", "rival1", "rival2", "rival3", "rival4", "pushfold", "tag", "loose_aggro"),
    # the hybrid candidate in Hero's seat, everything else as in realistic, top, top2 and holdout: the same seating
    # and the same duplicate deals seed for seed, so hybrid(X_h) - hero(X) is a paired comparison
    "realistic_h": ("hybrid", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "rival1", "tag",
                    "timeout_then_recover"),
    "top_h": ("hybrid", "rival1", "rival1", "pushfold", "tag", "hero_tight", "loose_aggro", "rival2"),
    "top2_h": ("hybrid", "rival1", "rival2", "rival2", "pushfold", "tag", "hero_tight", "loose_aggro"),
    "holdout_h": ("hybrid", "rival3", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag",
                  "timeout_then_recover"),
    # the same three rooms with the rival 3 hybrid in Hero's seat
    "realistic_h3": ("hybrid3", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "rival1", "tag",
                     "timeout_then_recover"),
    "top_h3": ("hybrid3", "rival1", "rival1", "pushfold", "tag", "hero_tight", "loose_aggro", "rival2"),
    "top2_h3": ("hybrid3", "rival1", "rival2", "rival2", "pushfold", "tag", "hero_tight", "loose_aggro"),
    # timeout-heavy: the four timeout-prone bots (honest Monte Carlo, Monte Carlo timing out 30% postflop, one that
    # breaks for good, one that breaks in outages and recovers) with the three competent students. Screened with the
    # deterministic timeout model (mode "model") so its timeouts do not follow the host
    "timeouts": ("hero", "montecarlo", "montecarlo30", "timeout_then_recover", "timeout_burst", "tag", "pushfold",
                 "loose_aggro"),
    # the table that busts itself: Hero's job is to survive it and be there at the end
    "chaos": ("hero", "crasher", "random", "allin", "station", "montecarlo", "maniac", "timeout_then_recover"),
}
# The night: Hero's seat and seven opponents drawn per table, with the table seed alone, from a weighted pool that is
# our guess at the real room (one-hour agent builds 40%, weak or broken 30%, decent 15%, strong teams 15%;
# night_hard: strong teams and the persona bots heavier). Each `night.k` entry is a seat that builds the bot its slot
# draws (hyperion/sim/field/night.py, where the weights and the reasoning are). Every rotation and every `night@<bot>`
# swap sees the same seven opponents with the same seeds. `night0` is the version without the persona bots.
from .field import night as _night  # noqa: E402 - imports nothing from here at module level

for _pool in ("night", "night_hard", "night0"):
    FIELDS[_pool] = ("hero",) + _night.seat_names(_pool)
# the second judge: `judge` with rival 5 in rival 4's seat (realistic-shaped, rival 5 in the holdout seat), and the
# night pool with rival 5 in one seat and six drawn around it. Never tuned on; measured once, by the compose agent
FIELDS["judge2"] = ("hero", "rival5", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag",
                    "timeout_then_recover")
FIELDS["judge2_night"] = ("hero", "rival5") + _night.seat_names("judge2_night")
# the climb's outside field (docs/drills/goal-plan.md): four fresh one-hour builds by agents with no repo access, plus
# three seats drawn from the night pool; and a strong room (Pittsburgh's field is expected to be stronger): the four,
# both judges and agent_pushfold. Judge-like: measured once per accepted batch, never tuned on.
OUTSIDE = ("out_veterans", "out_selfplay", "out_lag", "out_quants")
FIELDS["outside"] = ("hero",) + OUTSIDE + _night.seat_names("outside_rest")
FIELDS["outside_strong"] = ("hero",) + OUTSIDE + ("rival4", "rival5", "agent_pushfold")
# the elite field (owner's direction): three prepared top-team builds. elite1 and elite2 are a tuning field, alone with
# the strong tunable bots (`elite`, a top table) or in a night room (`elite_night`); elite3 is held out with both judges
# and two outside builds (`elite_judge`, the strongest room we have): measured once per batch, never tuned on.
FIELDS["elite"] = ("hero", "elite1", "elite2", "rival1", "rival2", "rival3", "agent_pushfold", "agent_default")
FIELDS["elite_night"] = ("hero", "elite1", "elite2") + _night.seat_names("elite_rest")
FIELDS["elite_judge"] = ("hero", "elite3", "elite1", "elite2", "rival4", "rival5", "out_veterans", "out_quants")
# the exploiter's fields (S2, docs/drills/exploiter/): as its arena seated it, the hero seat and exploiter1 with six
# night-pool seats at 8-max, alone heads-up, and with the first night-pool seat three-handed (play them with Rules of
# n_players 2 / 3: docs/drills/climb/rules/hu.json, three.json). A test opponent, never in a night pool.
EXPLOITERS = ("exploiter1", "exploiter2")
FIELDS["exploit"] = ("hero", "exploiter1") + _night.seat_names("night")[:6]
FIELDS["exploit_hu"] = ("hero", "exploiter1")
FIELDS["exploit_3"] = ("hero", "exploiter1") + _night.seat_names("night")[:1]
# the second exploiter's (S11, docs/drills/exploiter2/), seated the same way: its arena put F, itself and the first six
# night-pool seats at 8-max (payouts 10/7/5/4/3/2/1/0), and played heads-up and three-handed with the same seating
FIELDS["exploit2"] = ("hero", "exploiter2") + _night.seat_names("night")[:6]
FIELDS["exploit2_hu"] = ("hero", "exploiter2")
FIELDS["exploit2_3"] = ("hero", "exploiter2") + _night.seat_names("night")[:1]
# fields of fewer than eight seats, with the player count their Rules must carry (every other field seats eight)
FIELD_PLAYERS: dict[str, int] = {"exploit_hu": 2, "exploit_3": 3, "exploit2_hu": 2, "exploit2_3": 3}

# fields that seat an optional bot: present in FIELDS only when every bot in them is registered
OPTIONAL_FIELDS: dict[str, tuple[str, ...]] = {
    # the best public prep bot twice, both red-team rivals, and the competent baselines
    "public": ("hero", "micro", "micro", "rival1", "rival2", "tag", "pushfold", "loose_aggro"),
}
for _name, _members in OPTIONAL_FIELDS.items():
    if all(m in REGISTRY for m in _members):
        FIELDS[_name] = _members

# `<field>@<bot>`: the field with <bot> in Hero's seat and every other seat as it is. The runner shuffles a field's
# seating with the table seed alone, so the bot sits where Hero sat, with the same deals and the same opponents' seeds:
# `judge@hybrid3` - `judge` is paired seed for seed. Any field with one `hero` and any registered bot not already
# seated works through field_names(); the candidate cores' judge swaps are also listed in FIELDS so that
# `python -m hyperion.sim --field judge@hybrid3` accepts them. Hero with and without the exploit layer stays `hero` in
# Hero's own seat: it ships with the layer; `--hero-config '{"exploit.bet_checked": false, "exploit.steal": false,
# "exploit.steal_min_fold": 0}'` turns it off. Not on a hybrid run: the hybrids' fallback Hero takes HERO_CONFIG too.
JUDGE_CANDIDATES = tuple(c for c in ("hybrid", "hybrid_x", "hybrid3", "hybrid3_x") if c in REGISTRY)


def _hero_swap(base: str, bot: str) -> list[str]:
    members = field_names(base)
    if bot == "hero":
        return members
    if bot not in REGISTRY and bot not in _BY_CLASS:
        if bot in OPTIONAL_BOTS:
            raise _unavailable(bot)
        raise KeyError(f"unknown bot {bot!r} for {base}@{bot}; known: {', '.join(REGISTRY)}")
    if members.count("hero") != 1:
        raise KeyError(f"field {base!r} has {members.count('hero')} hero seats; {base}@{bot} needs exactly one")
    if bot in members:
        raise KeyError(f"{bot!r} already sits in {base!r}: its two seats would merge in the report")
    members[members.index("hero")] = bot
    return members


def field_names(name: str) -> list[str]:
    key = name.strip().lower()
    if key not in FIELDS and "@" in key:
        base, _, bot = key.partition("@")
        return _hero_swap(base.strip(), bot.strip())
    if key not in FIELDS:
        if key in OPTIONAL_FIELDS:
            missing = [m for m in OPTIONAL_FIELDS[key] if m not in REGISTRY]
            raise BotUnavailable(f"field {name!r} is disabled: {_unavailable(missing[0])}")
        raise KeyError(f"unknown field {name!r}; known: {', '.join(FIELDS)}")
    return list(FIELDS[key])


for _name in ("judge", "judge_top", "judge2", "judge2_night"):
    for _cand in JUDGE_CANDIDATES:
        FIELDS[f"{_name}@{_cand}"] = tuple(_hero_swap(_name, _cand))
for _name in ("night", "night_hard"):  # so `--field night@hybrid3_x` parses; field_names() takes any registered bot
    for _cand in JUDGE_CANDIDATES + ("rival3",):
        FIELDS[f"{_name}@{_cand}"] = tuple(_hero_swap(_name, _cand))


def make_bot(name: str, seed: Optional[int] = None):
    key = name.strip().lower()
    cls = REGISTRY.get(key) or _BY_CLASS.get(key)
    if cls is None:
        seat = _night.parse_seat(key)
        if seat is not None:  # `night.3`: the bot slot 3 of the night pool draws at this seed's table
            return _night.PoolSeat(seat[0], seat[1], seed)
        if key in OPTIONAL_BOTS:
            raise _unavailable(key)
        raise KeyError(f"unknown bot {name!r}; known: {', '.join(REGISTRY)}")
    return cls(seed)


# the variant-aware opponents of the three likeliest twists (toss_or_holdem, bounty, short_deck: a TAG, a push/fold bot and
# a Monte Carlo bot each) and their `<variant>_aware` fields: the entry's three aware bots in the seats of the honest Monte
# Carlo bot, the push/fold bot and the TAG, the rest as in `realistic`; play them with the variant (`--variant
# toss_or_holdem --field toss_or_holdem_aware`, tools/climb_accept.py's `aware` stage). Never in a night pool. The module
# registers them here when it finishes loading (whichever of the two is imported first).
from . import aware as _aware  # noqa: E402,F401
