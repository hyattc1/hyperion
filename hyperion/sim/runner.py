"""Tournament runner: many tables, aggregated per bot name, with confidence intervals.

`python -m hyperion.sim --tables 1000 --seed 1 --bots tag,nit,station,maniac --rotate`

Seats: the named bots are placed in a seeded random order per table; names beyond the table size
are dropped, fewer are filled with random copies of the names given (the tournament fills with
copies of submitted bots). Copies count toward their name's statistics here, since they run the
same code; the real tournament ignores filler points only to keep one score per team.

Sample unit for the CI: one (table seed, bot name) pair, averaging that bot's seats and, with
--rotate, its eight rotations. Rotations of one seed share cards and are not independent.
"""
from __future__ import annotations

import argparse
import cProfile
import json
import math
import pstats
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Optional, Sequence

from ..core.types import Rules
from .bestiary import REGISTRY, make_bot
from .engine import BotStats, play_table


@dataclass
class BotReport:
    name: str
    samples: list[float] = field(default_factory=list)  # mean points per table-seed
    places: list[int] = field(default_factory=list)  # histogram, index 0 = winner
    seats: int = 0
    busts: int = 0
    stats: BotStats = field(default_factory=BotStats)

    @property
    def mean(self) -> float:
        return sum(self.samples) / len(self.samples) if self.samples else 0.0

    @property
    def ci95(self) -> float:
        n = len(self.samples)
        if n < 2:
            return 0.0
        m = self.mean
        var = sum((x - m) ** 2 for x in self.samples) / (n - 1)
        return 1.96 * math.sqrt(var / n)

    @property
    def bust_rate(self) -> float:
        return self.busts / self.seats if self.seats else 0.0


@dataclass
class Report:
    bots: dict[str, BotReport]
    tables: int
    hands: int
    seconds: float

    @property
    def hands_per_second(self) -> float:
        return self.hands / self.seconds if self.seconds > 0 else 0.0

    def format(self) -> str:
        n_places = max((len(b.places) for b in self.bots.values()), default=8)
        head = (f"{'bot':<10} {'n':>5} {'pts':>6} {'±95%':>5}  "
                + " ".join(f"{'p' + str(i + 1):>4}" for i in range(n_places))
                + f"  {'bust%':>5} {'tmo':>5} {'exc':>5} {'ill':>5} "
                f"{'p50us':>6} {'p99us':>6} {'maxus':>6} {'1st_us':>7}")
        lines = [head]
        for name, b in sorted(self.bots.items(), key=lambda kv: -kv[1].mean):
            dist = " ".join(f"{100 * c / b.seats:4.0f}" if b.seats else "   -" for c in b.places)
            st = b.stats
            lines.append(
                f"{name:<10} {len(b.samples):>5} {b.mean:>6.3f} {b.ci95:>5.3f}  {dist}  "
                f"{100 * b.bust_rate:>5.1f} {st.over_budget:>5} {st.exceptions:>5} {st.illegal:>5} "
                f"{st.percentile_us(0.5):>6.0f} {st.percentile_us(0.99):>6.0f} {st.max_ns / 1000:>6.0f} "
                f"{st.first_max_ns / 1000:>7.0f}"
            )
        lines.append(
            f"{self.tables} tables, {self.hands} hands in {self.seconds:.1f}s: "
            f"{self.hands_per_second:,.0f} hands/s. p1..pN are finish-position percentages; "
            f"1st_us is the slowest first call of a table."
        )
        return "\n".join(lines)


def load_rules(spec: str) -> Rules:
    """'default' or a path to a json object whose keys are Rules fields."""
    if spec == "default":
        return Rules()
    with open(spec) as f:
        raw = json.load(f)
    tup = lambda v: tuple(tuple(x) if isinstance(x, list) else x for x in v)  # noqa: E731
    for k in ("board_sizes", "rank_order", "payouts", "blind_levels"):
        if k in raw:
            raw[k] = tup(raw[k])
    return Rules(**raw)


def run_tournament(
    names: Sequence[str],
    tables: int,
    seed: int = 1,
    rotate: bool = False,
    mode: str = "strict",
    rules: Optional[Rules] = None,
    stacks: Optional[Sequence[int]] = None,
) -> Report:
    rules = rules if rules is not None else Rules()
    n = rules.n_players
    names = [nm.strip().lower() for nm in names if nm.strip()]
    if not names:
        raise ValueError("need at least one bot name")
    for nm in names:
        make_bot(nm)  # fail early on a typo
    reports = {nm: BotReport(nm, places=[0] * n, stats=BotStats(nm)) for nm in names}
    rotations = range(n) if rotate else (0,)
    hands = 0
    t0 = time.perf_counter()
    for t in range(tables):
        table_seed = seed * 1_000_003 + t
        rng = random.Random(table_seed)
        seating = list(names[:n])
        while len(seating) < n:
            seating.append(rng.choice(names))
        rng.shuffle(seating)
        per_name_points: dict[str, list[float]] = {nm: [] for nm in names}
        for rot in rotations:
            bots = [make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
            stats = [reports[nm].stats for nm in seating]
            res = play_table(bots, rules, seed=table_seed, rotation=rot, mode=mode, stats=stats, stacks=stacks)
            hands += res.hands
            for s, nm in enumerate(seating):
                r = reports[nm]
                r.seats += 1
                r.places[res.places[s]] += 1
                r.busts += not res.survived[s]
                per_name_points[nm].append(res.points[s])
        for nm, pts in per_name_points.items():
            if pts:
                reports[nm].samples.append(sum(pts) / len(pts))
    return Report(reports, tables * len(rotations), hands, time.perf_counter() - t0)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.sim", description="Run 8-max sit-and-gos.")
    p.add_argument("--tables", type=int, default=100, help="table seeds to play (default 100)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--bots", default="hero,tag,nit,station,maniac,naive,random,allin",
                   help="comma-separated names from the registry; fewer than seats fills with copies")
    p.add_argument("--rotate", action="store_true", help="play all rotations of each deal (duplicate)")
    p.add_argument("--mode", choices=("strict", "measure"), default="strict")
    p.add_argument("--rules", default="default", help="'default' or a json file of Rules fields")
    p.add_argument("--profile", action="store_true", help="print the hottest functions afterwards")
    p.add_argument("--list", action="store_true", help="list bot names and exit")
    a = p.parse_args(argv)
    if a.list:
        for nm, cls in REGISTRY.items():
            print(f"{nm:<10} {cls.__name__:<16} {(cls.__doc__ or '').strip().splitlines()[0]}")
        return 0
    rules = load_rules(a.rules)
    names = a.bots.split(",")
    prof = cProfile.Profile() if a.profile else None
    if prof:
        prof.enable()
    report = run_tournament(names, a.tables, a.seed, a.rotate, a.mode, rules)
    if prof:
        prof.disable()
    print(report.format())
    if prof:
        pstats.Stats(prof, stream=sys.stdout).sort_stats("tottime").print_stats(15)
    return 0
