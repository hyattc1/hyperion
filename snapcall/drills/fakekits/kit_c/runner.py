"""Kit C runner: spawns your bot as a subprocess and talks the line protocol over its stdin/stdout.

    python -m snapcall.drills.fakekits.kit_c.runner path/to/submission.py [--hands 30] [--seed 1]

Your submission is run as `python submission.py` with the repo root on PYTHONPATH. A pooled game
clock of 1 ms per expected decision (hands x 3) is enforced; wall time of each round trip counts.
A reply that takes more than 2 s is treated as a dead bot and every later action folds.
"""
from __future__ import annotations

import argparse
import os
import select
import subprocess
import sys
import time
from pathlib import Path

from .. import _table
from .kit import encode_decision, encode_hand_end, encode_table_start, parse_reply

N_PLAYERS = 4
STACK = 2000
HARD_TIMEOUT_S = 2.0
BUILD_TIMEOUT_S = 10.0
DECISIONS_PER_HAND = 3
ROOT = Path(__file__).resolve().parents[4]


class LineBot:
    def __init__(self, cmd: list[str], cwd: str | None = None):
        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
        self.proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, cwd=cwd, env=env,
        )
        self.dead = False

    def send(self, line: str) -> None:
        if self.dead:
            return
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self.dead = True

    def ask(self, line: str, timeout_s: float = HARD_TIMEOUT_S) -> str:
        """Send a line and wait for one reply line; raises TimeoutError if the bot hangs."""
        self.send(line)
        if self.dead:
            raise RuntimeError("bot process is dead")
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout_s)
        if not ready:
            self.dead = True
            raise TimeoutError("no reply within hard timeout")
        reply = self.proc.stdout.readline()
        if reply == "":
            self.dead = True
            raise RuntimeError("bot closed stdout")
        return reply

    def close(self) -> str:
        self.send("Q")
        try:
            _, err = self.proc.communicate(timeout=HARD_TIMEOUT_S)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            _, err = self.proc.communicate()
        return err or ""


def run(cmd: list[str], hands: int = 30, seed: int = 1, budget_ms: float = 1.0, hole_cards: int = 2,
        n_players: int = N_PLAYERS, cwd: str | None = None) -> _table.Report:
    report = _table.Report()
    hero_seat = 0
    bot = LineBot(cmd, cwd)
    clock = [budget_ms * hands * DECISIONS_PER_HAND]  # pooled, in ms
    # startup handshake: imports and warm-up are not charged to the clock, but must finish in 10 s
    try:
        ack = bot.ask(encode_table_start(n_players, hero_seat, STACK, (10, 20)), timeout_s=BUILD_TIMEOUT_S)
        if ack.strip() != "OK":
            report.illegal += 1
            report.notes.append(f"expected OK after table start, got {ack.strip()!r}")
    except (TimeoutError, RuntimeError) as e:
        report.exceptions += 1
        report.notes.append(f"no OK after table start: {e}")

    def policy(st: dict) -> tuple[str, int]:
        report.decisions += 1
        if clock[0] <= 0 or bot.dead:
            report.timeouts += 1
            return _table._safe(st)
        t0 = time.perf_counter()
        try:
            reply = bot.ask(encode_decision(st, clock[0]))
        except (TimeoutError, RuntimeError) as e:
            report.exceptions += 1
            if len(report.notes) < 5:
                report.notes.append(str(e))
            return _table._safe(st)
        dt_ms = (time.perf_counter() - t0) * 1000
        report.times_ms.append(dt_ms)
        clock[0] -= dt_ms
        if clock[0] <= 0:
            report.timeouts += 1
            if len(report.notes) < 5:
                report.notes.append(f"clock exhausted at decision {report.decisions}")
            return _table._safe(st)
        try:
            kind, total = parse_reply(reply)
        except ValueError as e:
            report.illegal += 1
            if len(report.notes) < 5:
                report.notes.append(str(e))
            return _table._safe(st)
        if not _table.is_legal(kind, total, st):
            report.illegal += 1
            if len(report.notes) < 5:
                report.notes.append(f"illegal: {kind} {total} legal={sorted(st['legal'])} "
                                    f"min={st['min_raise']} max={st['max_raise']}")
            return _table._safe(st)
        return kind, total

    def hand_end(hand_no: int, deltas: list[int]) -> None:
        report.hands += 1
        bot.send(encode_hand_end(hand_no, deltas[hero_seat]))

    report.delta = _table.play(policy, hands, seed, n_players=n_players, hole_cards=hole_cards,
                               on_hand_end=hand_end, hero_seat=hero_seat)
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
    report = run([sys.executable, a.submission], a.hands, a.seed, a.budget_ms, a.hole_cards)
    print(report.summary())
    for n in report.notes:
        print("  ", n)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
