"""Fake event kit runner: one Agent seat among the shared dealer's opponents, every call timed and interrupted.

    python -m hyperion.drills.fakekits.kit_e_style.runner path/to/agent.py [--tables 4] [--hands 60] [--seed 1]
                                                          [--players 6] [--budget-ms 1.0] [--no-interrupt]

Per table: a fresh copy of the module (its own name), Agent(), on_table: that is the setup, 1 s. Then every hand:
on_hand, on_board when cards come, on_action for every action (the Agent's own too), on_reveal at a showdown of two
or more, on_result; decide() at each of its turns. Each call is timed alone; over 1 ms is a timeout, and on Linux
and macOS the call is interrupted at 1.05 ms (SIGALRM raises KitInterrupt, a BaseException). A decide() that
times out, raises or answers garbage is played as check-else-fold; an event that does is skipped.
"""
from __future__ import annotations

import argparse
import importlib.util
import random
import signal
import sys
import time
from collections import Counter

from .. import _table
from .._table import BOARD_SIZES, legalize
from .kit import BUDGET_MS, SETUP_MS, card, parse_reply, request


class KitInterrupt(BaseException):
    """Raised inside a call that ran past its budget."""


_INSIDE = [False]  # the alarm interrupts the Agent's call only, never the runner's own code around it


def _alarm(signum, frame):
    if _INSIDE[0]:
        _INSIDE[0] = False
        raise KitInterrupt()


class Clock:
    """Times each call into the Agent; counts timeouts, exceptions and interrupts per method."""

    def __init__(self, budget_ms: float, interrupt: bool):
        self.budget = budget_ms / 1000.0
        self.interrupt = interrupt and hasattr(signal, "setitimer")
        self.calls, self.timeouts, self.errors, self.cut = Counter(), Counter(), Counter(), Counter()
        self.worst: dict[str, float] = {}
        self.notes: list[str] = []
        if self.interrupt:
            signal.signal(signal.SIGALRM, _alarm)

    def call(self, name: str, fn, *args):
        """(ok, result): ok False when the call raised, was interrupted or ran past the budget."""
        self.calls[name] += 1
        if self.interrupt:
            signal.setitimer(signal.ITIMER_REAL, self.budget * 1.05)
        t0 = time.perf_counter()
        try:
            _INSIDE[0] = True
            out = fn(*args)
            _INSIDE[0] = False
            ok = True
        except KitInterrupt:
            out, ok = None, False
            self.cut[name] += 1
        except Exception as e:  # noqa: BLE001 - the bot's exception is a timeout-like fault
            out, ok = None, False
            self.errors[name] += 1
            if len(self.notes) < 8:
                self.notes.append(f"{name} raised {type(e).__name__}: {e}")
        finally:
            _INSIDE[0] = False
            dt = time.perf_counter() - t0
            if self.interrupt:
                signal.setitimer(signal.ITIMER_REAL, 0)
        if dt > self.worst.get(name, 0.0):
            self.worst[name] = dt
        if dt > self.budget:
            self.timeouts[name] += 1
            ok = False
        return ok, out


class EventTable(_table.Table):
    """The shared dealer, telling one seat what happens as it happens."""

    def __init__(self, seat: int, tell, **kw):
        super().__init__(**kw)
        self.agent_seat = seat
        self.tell = tell  # tell(event name, payload)
        self.kit_hand = 0

    def play_hand(self, policies):
        alive = self.alive()
        if len(alive) < 2:
            return [0] * self.n
        self.kit_hand += 1
        start = list(self.stacks)
        deck = list(self.deck_template)
        self.rng.shuffle(deck)
        self.in_hand = [self.stacks[s] > 0 for s in range(self.n)]
        self.bets = [0] * self.n
        self.committed = [0] * self.n
        self.pot = 0
        self.board = ()
        self.history = []
        self.discards = {}
        self.button = self.next_alive(self.button)
        sb_seat = self.next_alive(self.button) if len(alive) > 2 else self.button
        bb_seat = self.next_alive(sb_seat)
        sb, bb = self.blinds()
        posted = []
        for seat, amt in ((sb_seat, sb), (bb_seat, bb)):
            before = self.stacks[seat]
            self._post(seat, amt)
            posted.append({"seat": seat, "paid": before - self.stacks[seat], "ante": False})
        self.holes = {s: tuple(deck.pop() for _ in range(self.hole_cards)) for s in range(self.n) if self.in_hand[s]}
        me = self.agent_seat
        if self.in_hand[me]:
            self.tell("on_hand", {"hand": self.kit_hand, "button": self.button, "blinds": [sb, bb],
                                  "chips": {str(s): start[s] for s in range(self.n)}, "posted": posted,
                                  "cards": [card(c) for c in self.holes[me]]})
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
                self.tell("on_board", {"board": [card(c) for c in self.board]})
                first = self.next_alive(self.button)
            if sum(self.in_hand) > 1 and self._can_bet() > 1:
                self._betting_round(street, first, policies, bb)
            if sum(self.in_hand) == 1:
                break
        self.pot += sum(self.bets)
        self.bets = [0] * self.n
        live = [s for s in range(self.n) if self.in_hand[s]]
        if len(live) > 1:
            self.tell("on_reveal", {"hands": {str(s): [card(c) for c in self.holes[s]] for s in live}})
        self._showdown()
        self.hand_no += 1
        net = [self.stacks[s] - start[s] for s in range(self.n)]
        self.tell("on_result", {"hand": self.kit_hand, "net": {str(s): net[s] for s in range(self.n)},
                                "chips": {str(s): self.stacks[s] for s in range(self.n)}})
        return net

    def _betting_round(self, street, first, policies, bb):
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
            before = self.stacks[seat]
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
            self.tell("on_action", {"seat": seat, "move": kind, "to": self.bets[seat], "paid": before - self.stacks[seat]})


def load_agent_module(path: str, k: int):
    spec = importlib.util.spec_from_file_location(f"_kit_e_agent{k}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run(path: str, tables: int = 4, hands: int = 60, seed: int = 1, n_players: int = 6, budget_ms: float = BUDGET_MS,
        interrupt: bool = True, watch=None) -> dict:
    """Play `tables` tables of `hands` hands with the Agent in seat 0. `watch(state, req)` sees the dealer's true
    state at every Agent decision (tests compare the Agent's own view with it). Returns the report dict."""
    rng = random.Random(seed)
    clock = Clock(budget_ms, interrupt)
    rep = {"tables": 0, "hands": 0, "decisions": 0, "illegal": 0, "delta": 0, "setup_s": [], "setup_over": 0}
    for t in range(tables):
        seat = 0
        t0 = time.perf_counter()
        agent, ok = None, False
        try:
            mod = load_agent_module(path, t)
            agent = mod.Agent()
            ok, _ = clock.call("on_table", agent.on_table, {"seat": seat, "players": n_players, "stack": 2000,
                                                            "hands": hands, "budget_ms": budget_ms,
                                                            "setup_ms": SETUP_MS, "payouts": [50, 30, 20]})
        except Exception as e:  # noqa: BLE001
            clock.notes.append(f"setup raised {type(e).__name__}: {e}")
        setup = time.perf_counter() - t0
        rep["setup_s"].append(round(setup, 3))
        dead = agent is None or setup > SETUP_MS / 1000.0
        rep["setup_over"] += dead and agent is not None

        def tell(name, payload, _a=agent, _dead=dead):
            if not _dead:
                fn = getattr(_a, name, None)
                if fn is not None:
                    clock.call(name, fn, payload)

        table = EventTable(seat, tell, n_players=n_players, seed=rng.randrange(1 << 30))
        opps = _table.opponents(n_players, random.Random(rng.randrange(1 << 30)))

        def me(st, _a=agent, _dead=dead, _table_=table):
            rep["decisions"] += 1
            req = request(st, _table_.kit_hand)
            if watch is not None:
                watch(st, req)
            if _dead:
                return ("check", 0) if "check" in st["legal"] else ("fold", 0)
            ok, reply = clock.call("decide", _a.decide, req)
            if ok:
                try:
                    return parse_reply(reply, st)
                except ValueError as e:
                    rep["illegal"] += 1
                    if len(clock.notes) < 8:
                        clock.notes.append(f"illegal: {e}")
            return ("check", 0) if "check" in st["legal"] else ("fold", 0)

        policies = [me if s == seat else opps[s] for s in range(n_players)]
        for _ in range(hands):
            if len(table.alive()) < 2 or table.stacks[seat] == 0:
                break
            rep["delta"] += table.play_hand(policies)[seat]
            rep["hands"] += 1
        rep["tables"] += 1
    rep.update(calls=dict(clock.calls), timeouts=dict(clock.timeouts), errors=dict(clock.errors),
               interrupted=dict(clock.cut), worst_us={k: round(v * 1e6) for k, v in clock.worst.items()},
               notes=clock.notes)
    return rep


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("agent")
    p.add_argument("--tables", type=int, default=4)
    p.add_argument("--hands", type=int, default=60)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--players", type=int, default=6)
    p.add_argument("--budget-ms", type=float, default=BUDGET_MS)
    p.add_argument("--no-interrupt", action="store_true")
    a = p.parse_args(argv)
    rep = run(a.agent, a.tables, a.hands, a.seed, a.players, a.budget_ms, not a.no_interrupt)
    for k in ("tables", "hands", "decisions", "illegal", "delta", "setup_s", "setup_over", "calls", "timeouts",
              "errors", "interrupted", "worst_us"):
        print(f"{k:12s} {rep[k]}")
    for n in rep["notes"]:
        print("note", n)
    bad = rep["illegal"] or sum(rep["errors"].values()) or rep["setup_over"]
    print("FAIL" if bad else "PASS")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
