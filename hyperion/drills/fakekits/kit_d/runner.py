"""Kit D runner (the engine side): listens on a localhost port, starts your bot with that port as its
argument, and plays N hands of 8-max against the shared dumb opponents over the kit's line protocol.

    python -m hyperion.drills.fakekits.kit_d.runner path/to/submission.py [--hands 30] [--seed 1]
    python -m hyperion.drills.fakekits.kit_d.runner path/to/botdir            # a dir with commands.json

Your submission is run as `python submission.py <port>` (or the commands.json "run" list + port) with the
repo root on PYTHONPATH and must connect within 10 s. A pooled game clock of 1 ms per expected decision
(hands x 3) is charged by the wall time of EVERY round trip, the two acks per round included; once it is
negative every later action is a fold and the bot is not spoken to again. A reply slower than 2 s marks
the bot dead. Exceptions, illegal replies (a fold when a check is free is illegal here, as in MIT) and
latency are reported.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable

from hyperion.core.types import card_str

from .. import _table

N_PLAYERS = 8
STACK = 2000
HARD_TIMEOUT_S = 2.0
CONNECT_TIMEOUT_S = 10.0
DECISIONS_PER_HAND = 3
ROOT = Path(__file__).resolve().parents[4]

_HIST = {"fold": "F", "call": "C", "check": "K"}


def parse_reply(line: str) -> tuple[str, int]:
    """'F' | 'K' | 'C' | 'R<total>' -> (kind, total). Raises ValueError on garbage."""
    s = line.strip()
    if s == "F":
        return "fold", 0
    if s == "K":
        return "check", 0
    if s == "C":
        return "call", 0
    if s.startswith("R") and s[1:].isdigit():
        return "raise", int(s[1:])
    raise ValueError(f"bad reply {line!r}")


def _cards(cs) -> str:
    return ",".join(card_str(c) for c in cs)


def _csv(xs) -> str:
    return ",".join(str(int(x)) for x in xs)


class SocketBot:
    """Spawns the bot process and accepts its connection, MIT style."""

    def __init__(self, cmd: list[str], cwd: str | None = None):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("localhost", 0))
        self.listener.listen(1)
        port = self.listener.getsockname()[1]
        self.proc = subprocess.Popen(
            cmd + [str(port)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, cwd=cwd, env=env,
        )
        self.listener.settimeout(0.05)
        deadline = time.perf_counter() + CONNECT_TIMEOUT_S
        conn = None
        while conn is None:
            try:
                conn, _ = self.listener.accept()
            except socket.timeout:
                if self.proc.poll() is not None:
                    out = self._drain()
                    raise RuntimeError(f"bot exited with {self.proc.returncode} before connecting: {out[-300:]}")
                if time.perf_counter() > deadline:
                    self.proc.kill()
                    raise TimeoutError(f"bot did not connect within {CONNECT_TIMEOUT_S:.0f} s")
        conn.settimeout(HARD_TIMEOUT_S)
        self.conn = conn
        self.rfile = conn.makefile("r")
        self.wfile = conn.makefile("w")
        self.dead = False

    def ask(self, line: str) -> str:
        """Send one packet, wait for one reply line."""
        if self.dead:
            raise RuntimeError("bot connection is dead")
        try:
            self.wfile.write(line + "\n")
            self.wfile.flush()
            reply = self.rfile.readline()
        except socket.timeout:
            self.dead = True
            raise TimeoutError("no reply within hard timeout") from None
        except OSError as e:
            self.dead = True
            raise RuntimeError(f"socket error: {e}") from None
        if reply == "":
            self.dead = True
            raise RuntimeError("bot closed the connection")
        return reply

    def _drain(self) -> str:
        try:
            out, _ = self.proc.communicate(timeout=HARD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            out, _ = self.proc.communicate()
        return out or ""

    def close(self) -> str:
        if not self.dead:
            try:
                self.wfile.write("Q\n")
                self.wfile.flush()
            except OSError:
                pass
        for f in (self.rfile, self.wfile, self.conn, self.listener):
            try:
                f.close()
            except OSError:
                pass
        return self._drain()


class Engine:
    """Drives the shared dealer and talks the kit D protocol through `ask` (one packet in, one line out)."""

    def __init__(self, ask: Callable[[str], str] | None, hands: int, seed: int, budget_ms: float,
                 hole_cards: int, n_players: int, report: _table.Report, hero_seat: int = 0):
        self.ask = ask
        self.alive = ask is not None
        self.hands, self.seed, self.hole_cards, self.n = hands, seed, hole_cards, n_players
        self.hero_seat = hero_seat
        self.report = report
        self.clock = budget_ms * hands * DECISIONS_PER_HAND / 1000.0  # seconds, pooled for the game
        self.table: _table.Table | None = None
        self.pre_stacks: list[int] = []
        self.round_open = False
        self.sent = 0
        self.board_sent = 0
        self.board_at: dict[int, tuple] = {}
        self.last_state: dict | None = None  # the dealer's view at the hero's current decision (for tests)

    # -- transport
    def _query(self, clauses: list[str]):
        """One packet, one reply, wall time charged to the clock. None when the bot cannot be used."""
        if not self.alive or self.clock <= 0:
            return None
        line = " ".join([f"T{self.clock:.6f}", f"P{self.hero_seat}", *clauses])
        t0 = time.perf_counter()
        try:
            reply = self.ask(line)
        except (TimeoutError, RuntimeError) as e:
            self.alive = False
            self.report.exceptions += 1
            if len(self.report.notes) < 5:
                self.report.notes.append(str(e))
            return None
        dt = time.perf_counter() - t0
        self.clock -= dt
        return reply, dt

    # -- packets
    def _open_round(self, stacks, pips) -> None:
        t = self.table
        sb, bb = t.blinds()
        self.round_open = True
        self.sent = 0
        self.board_sent = 0
        self.board_at = {}
        self._query(["S" + _csv(stacks), "I" + _csv(pips), f"L{sb},{bb}", "H" + _cards(t.holes[self.hero_seat]),
                     f"G{t.button}"])

    def _pending(self) -> list[str]:
        """History since the last packet, with a B clause wherever the street changed."""
        out = []
        hist = self.table.history
        for i in range(self.sent, len(hist) + 1):  # + 1: the street may have changed for the decision being asked
            board = self.board_at.get(i)
            if board is not None and len(board) > self.board_sent:
                out.append("B" + _cards(board))
                self.board_sent = len(board)
            if i < len(hist):
                seat, kind, total = hist[i]
                out.append(_HIST.get(kind) or f"R{total}")
        self.sent = len(hist)
        return out

    def _wrap(self, policy: _table.Policy) -> _table.Policy:
        def wrapped(st: dict):
            if not self.round_open:
                self._open_round(self.table.stacks, self.table.bets)
            self.board_at[len(st["history"])] = tuple(st["board"])
            return policy(st)
        return wrapped

    def hero(self, st: dict) -> tuple[str, int]:
        r = self.report
        r.decisions += 1
        self.last_state = st
        if not self.alive or self.clock <= 0:
            r.timeouts += 1
            return _table._safe(st)
        res = self._query(self._pending())
        if res is None:
            return _table._safe(st)
        reply, dt = res
        r.times_ms.append(dt * 1000)
        if self.clock <= 0:
            r.timeouts += 1
            if len(r.notes) < 5:
                r.notes.append(f"clock exhausted at decision {r.decisions}")
            return _table._safe(st)
        try:
            kind, total = parse_reply(reply)
        except ValueError as e:
            r.illegal += 1
            if len(r.notes) < 5:
                r.notes.append(str(e))
            return _table._safe(st)
        if kind == "fold" and "check" in st["legal"]:
            r.illegal += 1
            if len(r.notes) < 5:
                r.notes.append("illegal: fold when a check is free (FoldAction is not in legal_actions() there)")
            return _table._safe(st)
        if not _table.is_legal(kind, total, st):
            r.illegal += 1
            if len(r.notes) < 5:
                r.notes.append(f"illegal: {kind} {total} legal={sorted(st['legal'])} "
                               f"min={st['min_raise']} max={st['max_raise']}")
            return _table._safe(st)
        return kind, total

    def _after_hand(self, deltas: list[int]) -> None:
        t = self.table
        if not self.round_open:  # nobody could act (all-in from the blinds): the round still happened
            pips = list(t.committed)
            self._open_round([a - b for a, b in zip(self.pre_stacks, pips)], pips)
        clauses = self._pending()
        if len(t.board) > self.board_sent:
            clauses.append("B" + _cards(t.board))
            self.board_sent = len(t.board)
        live = [s for s in range(self.n) if t.in_hand[s]]
        if len(live) > 1:
            clauses.extend(f"O{s}:" + _cards(t.holes[s]) for s in live if s != self.hero_seat)
        clauses.append("A" + _csv(deltas))
        self._query(clauses)
        self.report.hands += 1
        self.round_open = False

    # -- the game
    def play(self) -> None:
        rng = random.Random(self.seed)
        opps = _table.opponents(self.n, rng)
        policies = [self._wrap(self.hero if s == self.hero_seat else opps[s]) for s in range(self.n)]
        hand_no = 0
        delta = 0
        table = None
        for _ in range(self.hands):
            if table is None or len(table.alive()) < 2 or table.stacks[self.hero_seat] == 0:
                table = _table.Table(n_players=self.n, seed=rng.randrange(1 << 30), hole_cards=self.hole_cards)
                table.hand_no = hand_no
            self.table = table
            self.pre_stacks = list(table.stacks)
            d = table.play_hand(policies)
            hand_no = table.hand_no
            delta += d[self.hero_seat]
            self._after_hand(d)
        self.report.delta = delta


def command_for(submission: str) -> tuple[list[str], str | None]:
    """A .py file runs as `python file.py`; a directory runs its commands.json "run" list (MIT layout)."""
    p = Path(submission)
    if p.is_dir():
        spec = json.loads((p / "commands.json").read_text())
        return list(spec["run"]), str(p)
    return [sys.executable, str(p)], None


def run(cmd: list[str], hands: int = 30, seed: int = 1, budget_ms: float = 1.0, hole_cards: int = 2,
        n_players: int = N_PLAYERS, cwd: str | None = None) -> _table.Report:
    report = _table.Report()
    bot = None
    try:
        bot = SocketBot(cmd, cwd)
    except (TimeoutError, RuntimeError) as e:
        report.exceptions += 1
        report.notes.append(f"startup: {e}")
    Engine(bot.ask if bot else None, hands, seed, budget_ms, hole_cards, n_players, report).play()
    if bot is not None:
        err = bot.close().strip()
        if err:
            report.notes.append("stderr: " + err[-400:])
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("submission")
    p.add_argument("--hands", type=int, default=30)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--budget-ms", type=float, default=1.0)
    p.add_argument("--hole-cards", type=int, default=2)
    a = p.parse_args(argv)
    cmd, cwd = command_for(a.submission)
    report = run(cmd, a.hands, a.seed, a.budget_ms, a.hole_cards, cwd=cwd)
    print(report.summary())
    for n in report.notes:
        print("  ", n)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
