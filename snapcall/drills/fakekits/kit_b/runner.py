"""Kit B runner: imports your module, calls decide(observation) for every decision, 1 ms budget.

    python -m snapcall.drills.fakekits.kit_b.runner path/to/submission.py [--hands 30] [--seed 1]
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from .. import _table
from .kit import parse_decision, to_observation

N_PLAYERS = 4
STACK = 2000


def load_module(path: str):
    spec = importlib.util.spec_from_file_location("submission_b", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def run(module, hands: int = 30, seed: int = 1, budget_ms: float = 1.0, hole_cards: int = 2,
        n_players: int = N_PLAYERS) -> _table.Report:
    report = _table.Report()
    hero_seat = 0
    decide = module.decide
    start = getattr(module, "on_table_start", None)
    end = getattr(module, "on_hand_end", None)
    if start is not None:
        try:
            start({"seat": hero_seat, "players": n_players, "stack": STACK, "blinds": {"sb": 10, "bb": 20}})
        except Exception as e:  # noqa: BLE001
            report.exceptions += 1
            report.notes.append(f"on_table_start raised: {e!r}")

    def call(st: dict) -> tuple[str, int]:
        return parse_decision(decide(to_observation(st)), st)

    def hand_end(hand_no: int, deltas: list[int]) -> None:
        report.hands += 1
        if end is not None:
            try:
                end({"hand_id": hand_no, "delta": deltas[hero_seat]})
            except Exception as e:  # noqa: BLE001
                report.exceptions += 1
                if len(report.notes) < 5:
                    report.notes.append(f"on_hand_end raised: {e!r}")

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
    report = run(load_module(a.submission), a.hands, a.seed, a.budget_ms, a.hole_cards)
    print(report.summary())
    for n in report.notes:
        print("  ", n)
    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
