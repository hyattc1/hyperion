"""Kit A runner: plays a few hands of your Agent against built-in dumb opponents with a 1 ms budget.

    python -m snapcall.drills.fakekits.kit_a.runner path/to/submission.py [--hands 30] [--seed 1]

submission.py must define `class Agent` (subclass of kit.Agent or duck-typed) with act(state) -> str.
Over budget, exceptions and illegal actions all become an auto-fold (check if possible).
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from .. import _table
from .kit import parse_action, to_state

N_PLAYERS = 4
STACK = 2000


def load_agent_class(path: str):
    spec = importlib.util.spec_from_file_location("submission_a", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod.Agent


def run(agent_cls, hands: int = 30, seed: int = 1, budget_ms: float = 1.0, hole_cards: int = 2,
        n_players: int = N_PLAYERS) -> _table.Report:
    report = _table.Report()
    agent = agent_cls()
    hero_seat = 0
    try:
        agent.new_game(hero_seat, n_players, STACK)
    except Exception as e:  # noqa: BLE001
        report.exceptions += 1
        report.notes.append(f"new_game raised: {e!r}")

    def call(st: dict) -> tuple[str, int]:
        return parse_action(agent.act(to_state(st)))

    def hand_end(hand_no: int, deltas: list[int]) -> None:
        report.hands += 1
        try:
            agent.hand_over(hand_no, deltas[hero_seat])
        except Exception as e:  # noqa: BLE001
            report.exceptions += 1
            if len(report.notes) < 5:
                report.notes.append(f"hand_over raised: {e!r}")

    hero = _table.TimedSeat(call, budget_ms, report)
    report.delta = _table.play(hero, hands, seed, n_players=n_players, hole_cards=hole_cards,
                               on_hand_end=hand_end, hero_seat=hero_seat)
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("submission")
    p.add_argument("--hands", type=int, default=30)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--budget-ms", type=float, default=1.0)
    p.add_argument("--hole-cards", type=int, default=2)
    a = p.parse_args(argv)
    sys.path.insert(0, str(Path(a.submission).resolve().parent))
    report = run(load_agent_class(a.submission), a.hands, a.seed, a.budget_ms, a.hole_cards)
    print(report.summary())
    for n in report.notes:
        print("  ", n)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
