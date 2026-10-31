"""A tiny no-limit hold'em dealer shared by the three fake kits.

This is NOT hyperion.sim. It is just enough poker to make an adapter's output legal or illegal
and to move chips: blinds, four streets, side pots, a few dumb opponents. The kits differ in
*interface*, not in the game, so they share this and each wraps the decision state its own way.

Decision state is a plain dict so kit code cannot lean on hyperion.core.types by accident:
  hole, board, street (0..3), seat, button, stacks, bets, in_hand, pot (previous streets only),
  to_call, min_raise (raise-to total), max_raise (all-in total), legal {'fold','check','call','raise'},
  hand_no, blinds, history [(seat, kind, total)]
A policy is a callable(state) -> (kind, total) with kind in legal and total the raise-to amount.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Callable

from hyperion.core.cards import deck_for
from hyperion.core.eval import evaluate
from hyperion.core.types import Rules

Policy = Callable[[dict], tuple[str, int]]
BOARD_SIZES = (0, 3, 4, 5)


@dataclass
class Report:
    hands: int = 0
    decisions: int = 0
    timeouts: int = 0
    exceptions: int = 0
    illegal: int = 0
    delta: int = 0
    times_ms: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    @property
    def max_ms(self) -> float:
        return max(self.times_ms) if self.times_ms else 0.0

    @property
    def mean_ms(self) -> float:
        return sum(self.times_ms) / len(self.times_ms) if self.times_ms else 0.0

    @property
    def passed(self) -> bool:
        """No crashes, no illegal actions, timeouts within OS jitter (1% of decisions, at least 1)."""
        return (
            self.exceptions == 0 and self.illegal == 0 and self.decisions > 0
            and self.timeouts <= max(1, self.decisions // 100)
        )

    def summary(self) -> str:
        return (
            f"{'PASS' if self.passed else 'FAIL'}: {self.hands} hands, {self.decisions} decisions, "
            f"{self.timeouts} timeouts, {self.exceptions} exceptions, {self.illegal} illegal, "
            f"delta {self.delta:+d}, mean {self.mean_ms:.3f} ms, max {self.max_ms:.3f} ms"
        )


class Table:
    def __init__(self, n_players: int = 4, seed: int = 0, stack: int = 2000, blinds=(10, 20),
                 hole_cards: int = 2, hands_per_level: int = 25,
                 levels=((10, 20), (15, 30), (25, 50), (50, 100), (75, 150), (100, 200))):
        self.n = n_players
        self.rng = random.Random(seed)
        self.stacks = [stack] * n_players
        self.hole_cards = hole_cards
        self.levels = levels if blinds == (10, 20) else (blinds,)
        self.hands_per_level = hands_per_level
        self.button = n_players - 1
        self.hand_no = 0
        self.deck_template = list(deck_for(Rules()))

    # -- helpers
    def alive(self) -> list[int]:
        return [s for s in range(self.n) if self.stacks[s] > 0]

    def next_alive(self, seat: int) -> int:
        for i in range(1, self.n + 1):
            s = (seat + i) % self.n
            if self.stacks[s] > 0 or self.in_hand[s]:
                return s
        return seat

    def blinds(self) -> tuple[int, int]:
        return self.levels[min(self.hand_no // self.hands_per_level, len(self.levels) - 1)]

    # -- one hand
    def play_hand(self, policies: list[Policy]) -> list[int]:
        """Play one hand; returns chip delta per seat. policies[seat] decides for that seat."""
        alive = self.alive()
        if len(alive) < 2:
            return [0] * self.n
        start = list(self.stacks)
        deck = list(self.deck_template)
        self.rng.shuffle(deck)
        self.in_hand = [self.stacks[s] > 0 for s in range(self.n)]
        self.bets = [0] * self.n
        self.committed = [0] * self.n  # whole hand, for side pots
        self.pot = 0
        self.board: tuple[int, ...] = ()
        self.history: list[tuple[int, str, int]] = []
        self.button = self.next_alive(self.button)
        sb_seat = self.next_alive(self.button) if len(alive) > 2 else self.button
        bb_seat = self.next_alive(sb_seat)
        sb, bb = self.blinds()
        self._post(sb_seat, sb)
        self._post(bb_seat, bb)
        self.holes = {}
        for s in range(self.n):
            if self.in_hand[s]:
                self.holes[s] = tuple(deck.pop() for _ in range(self.hole_cards))
        self.last_raise = bb
        self.current_bet = bb
        first = self.next_alive(bb_seat)
        for street in range(4):
            if street > 0:
                self.pot += sum(self.bets)
                self.bets = [0] * self.n
                self.current_bet = 0
                self.last_raise = bb
                self.board = self.board + tuple(deck.pop() for _ in range(BOARD_SIZES[street] - len(self.board)))
                first = self.next_alive(self.button)
            if sum(self.in_hand) > 1 and self._can_bet() > 1:
                self._betting_round(street, first, policies, bb)
            if sum(self.in_hand) == 1:
                break
        self.pot += sum(self.bets)
        self.bets = [0] * self.n
        self._showdown()
        self.hand_no += 1
        return [self.stacks[s] - start[s] for s in range(self.n)]

    def _post(self, seat: int, amount: int) -> None:
        amt = min(amount, self.stacks[seat])
        self.stacks[seat] -= amt
        self.bets[seat] += amt
        self.committed[seat] += amt

    def _can_bet(self) -> int:
        return sum(1 for s in range(self.n) if self.in_hand[s] and self.stacks[s] > 0)

    def state_for(self, seat: int, street: int) -> dict:
        to_call = min(self.current_bet - self.bets[seat], self.stacks[seat])
        max_raise = self.stacks[seat] + self.bets[seat]
        min_raise = min(max_raise, self.current_bet + max(self.last_raise, self.blinds()[1]))
        legal = {"fold"}
        if to_call == 0:
            legal.add("check")
        else:
            legal.add("call")
        if max_raise > self.current_bet and self._can_bet() > 1 or (max_raise > self.current_bet and to_call == 0):
            legal.add("raise")
        return {
            "hole": self.holes[seat], "board": self.board, "street": street, "seat": seat,
            "button": self.button, "stacks": list(self.stacks), "bets": list(self.bets),
            "in_hand": list(self.in_hand), "pot": self.pot, "to_call": to_call,
            "min_raise": min_raise, "max_raise": max_raise, "legal": legal,
            "hand_no": self.hand_no, "blinds": self.blinds(), "history": list(self.history),
        }

    def _betting_round(self, street: int, first: int, policies: list[Policy], bb: int) -> None:
        order = [(first + i) % self.n for i in range(self.n)]
        pending = [s for s in order if self.in_hand[s] and self.stacks[s] > 0]
        while pending:
            seat = pending.pop(0)
            if not self.in_hand[seat] or self.stacks[seat] == 0:
                continue
            if sum(self.in_hand) == 1:
                return
            st = self.state_for(seat, street)
            kind, total = policies[seat](st)
            kind, total = legalize(kind, total, st)
            self.history.append((seat, kind, total))
            if kind == "fold":
                self.in_hand[seat] = False
            elif kind == "call":
                self._post(seat, st["to_call"])
            elif kind == "raise":
                prev = self.current_bet
                self._post(seat, total - self.bets[seat])
                self.current_bet = self.bets[seat]
                self.last_raise = max(self.last_raise, self.current_bet - prev)
                after = [(seat + i) % self.n for i in range(1, self.n)]
                pending = [s for s in after if self.in_hand[s] and self.stacks[s] > 0]

    def _showdown(self) -> None:
        live = [s for s in range(self.n) if self.in_hand[s]]
        if len(live) == 1:
            self.stacks[live[0]] += self.pot
            return
        strength = {s: evaluate(self.holes[s] + self.board) for s in live}
        # side pots by contribution level
        levels = sorted({self.committed[s] for s in range(self.n) if self.committed[s] > 0})
        paid = 0
        prev = 0
        for lvl in levels:
            contributors = [s for s in range(self.n) if self.committed[s] >= lvl]
            size = (lvl - prev) * len(contributors)
            prev = lvl
            eligible = [s for s in contributors if self.in_hand[s]]
            if not eligible:
                continue
            best = max(strength[s] for s in eligible)
            winners = [s for s in eligible if strength[s] == best]
            share, rem = divmod(size, len(winners))
            for i, w in enumerate(winners):
                self.stacks[w] += share + (1 if i < rem else 0)
            paid += size
        # chips not covered above (should be zero) go to the strongest live hand
        if paid < self.pot:
            self.stacks[max(live, key=lambda s: strength[s])] += self.pot - paid


def legalize(kind: str, total: int, st: dict) -> tuple[str, int]:
    """Clamp a (kind, total) to something legal in st; returns a check/fold if the kind is not legal."""
    legal = st["legal"]
    if kind == "raise" and "raise" in legal:
        return "raise", max(st["min_raise"], min(st["max_raise"], int(total)))
    if kind in legal:
        return kind, 0
    if kind == "raise" and "call" in legal:
        return "call", 0
    return ("check", 0) if "check" in legal else ("fold", 0)


def is_legal(kind: str, total: int, st: dict) -> bool:
    if kind not in st["legal"]:
        return False
    if kind == "raise":
        return st["min_raise"] <= int(total) <= st["max_raise"]
    return True


# ------------------------------------------------------------------ dumb opponents

def station(st: dict) -> tuple[str, int]:
    return ("check", 0) if "check" in st["legal"] else ("call", 0)


def maniac(rng: random.Random) -> Policy:
    def act(st: dict) -> tuple[str, int]:
        if "raise" in st["legal"] and rng.random() < 0.4:
            return "raise", min(st["max_raise"], max(st["min_raise"], st["pot"] + sum(st["bets"])))
        return station(st)
    return act


def rock(st: dict) -> tuple[str, int]:
    ranks = sorted((c >> 2 for c in st["hole"]), reverse=True)
    strong = ranks[0] == ranks[1] or ranks[0] >= 11 and ranks[1] >= 9
    if strong and "raise" in st["legal"]:
        return "raise", st["min_raise"]
    if strong:
        return station(st)
    return ("check", 0) if "check" in st["legal"] else ("fold", 0)


def opponents(n: int, rng: random.Random) -> list[Policy]:
    kinds = [station, maniac(rng), rock]
    return [kinds[i % len(kinds)] for i in range(n)]


# ------------------------------------------------------------------ the timed hero wrapper

class TimedSeat:
    """Wraps a kit-native agent call: times it, catches exceptions, legalizes, keeps a Report."""

    def __init__(self, call: Callable[[dict], tuple[str, int]], budget_ms: float, report: Report):
        self.call = call  # kit-native round trip: state dict -> (kind, total), raising on bad output
        self.budget = budget_ms / 1000.0
        self.report = report

    def __call__(self, st: dict) -> tuple[str, int]:
        r = self.report
        r.decisions += 1
        t0 = time.perf_counter()
        try:
            kind, total = self.call(st)
        except Exception as e:  # noqa: BLE001 - the kit folds on any exception
            dt = time.perf_counter() - t0
            r.times_ms.append(dt * 1000)
            r.exceptions += 1
            if len(r.notes) < 5:
                r.notes.append(f"exception: {type(e).__name__}: {e}")
            return _safe(st)
        dt = time.perf_counter() - t0
        r.times_ms.append(dt * 1000)
        if dt > self.budget:
            r.timeouts += 1
            return _safe(st)
        if not is_legal(kind, total, st):
            r.illegal += 1
            if len(r.notes) < 5:
                r.notes.append(f"illegal: {kind} {total} with legal={sorted(st['legal'])} "
                               f"min={st['min_raise']} max={st['max_raise']}")
            return _safe(st)
        return kind, total


def _safe(st: dict) -> tuple[str, int]:
    return ("check", 0) if "check" in st["legal"] else ("fold", 0)


def play(hero: Policy, hands: int, seed: int, n_players: int = 4, hole_cards: int = 2,
         on_hand_end: Callable[[int, list[int]], None] | None = None, hero_seat: int = 0) -> int:
    """Play `hands` hands with hero in seat hero_seat and dumb opponents elsewhere; returns hero's delta.

    When the table ends (hero busted or everyone else did) a fresh table starts, so the hand count
    is always met and hand numbers keep climbing."""
    rng = random.Random(seed)
    opps = opponents(n_players, rng)
    policies = [hero if s == hero_seat else opps[s] for s in range(n_players)]
    delta = 0
    hand_no = 0
    table = None
    for _ in range(hands):
        if table is None or len(table.alive()) < 2 or table.stacks[hero_seat] == 0:
            table = Table(n_players=n_players, seed=rng.randrange(1 << 30), hole_cards=hole_cards)
            table.hand_no = hand_no
        d = table.play_hand(policies)
        hand_no = table.hand_no
        delta += d[hero_seat]
        if on_hand_end is not None:
            on_hand_end(hand_no - 1, d)
    return delta
