#!/usr/bin/env python
"""Hero's readiness on every catalog entry, as one markdown table for docs/decisions.md and the playbook.

    .venv/bin/python tools/variant_matrix.py --tables 300 --seed 7 --field realistic --workers 4
    .venv/bin/python tools/variant_matrix.py --only toss_or_holdem,omaha_four --tables 100
    .venv/bin/python tools/variant_matrix.py --unseen --seed 30000 --tables 50     (the held-out five: measure, never tune)
    .venv/bin/python tools/variant_matrix.py --bot ship --mode model --only auction,deal5_keep2 --tables 200

`--bot ship` seats the shipped bot (F: the composite with SHIP_DIALS, as hyperion.ship builds it) in Hero's seat of the
same tables (`<field>@ship`), with the same VPIP count; `--mode model` is the climb's replayable setup (tools/swap.py's
setup_process: panic, soft deadlines and late_us off; the engine's timeout model), so a rerun gives the same numbers.

Per entry (one `python -m hyperion.sim --variant NAME --field F --tables N --seed S` in strict mode, in a
worker process): Hero's points with the 95% interval, its rank among the field's bot names, engine
exceptions plus SafeBot's inner errors (the engine never sees those: SafeBot turns them into a check or
fold, so `exc` alone would under-report), illegal actions, timeouts, bust rate, VPIP (hands Hero
voluntarily put preflop chips in over hands it acted in), p99 latency, and a verdict:

    READY   Hero plays (VPIP >= 10%) and ranks top 2        PLAYS   ranks 3-4
    WEAK    ranks 5+ or VPIP < 10%                           BROKEN  any exception or inner error

The reason column names the leader when Hero is not first, the VPIP when it is low, and the error count.
"""
from __future__ import annotations

import argparse
import sys
import time
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from hyperion.core.types import ActionKind  # noqa: E402

_STATE = {"hands": 0, "vpip": 0, "heroes": []}


def _counting(base):
    """`base` (a bestiary seat class) counting VPIP and keeping itself reachable for SafeBot's error count."""

    class Counting(base):
        def new_table(self, rules, seat, n_players):
            self._hand, self._in = -1, False
            _STATE["heroes"].append(self)
            super().new_table(rules, seat, n_players)

        def act(self, obs):
            if obs.hand_no != self._hand:
                self._hand, self._in = obs.hand_no, False
                _STATE["hands"] += 1
            a = super().act(obs)
            if obs.street == 0 and not self._in and (a.kind is ActionKind.CALL or a.kind is ActionKind.RAISE):
                self._in = True
                _STATE["vpip"] += 1
            return a

    Counting.__name__ = Counting.__qualname__ = "Counting" + base.__name__
    return Counting


def _install_counting_ship() -> str:
    """F in Hero's seat: the composite with the shipped dials (hyperion.compose.bot.ship's set, light shadows on),
    registered through compose.register so a model-mode run's HYBRID_CONFIG / HERO_CONFIG reach it."""
    from hyperion.compose import bot as CB
    from hyperion.sim import bestiary as B

    seat = CB.register("ship", dials={**CB.SHIP_DIALS, "light": True})
    B.REGISTRY["ship"] = _counting(seat)
    return "ship"


def _install_counting_hero():
    from hyperion.sim import bestiary as B

    B.REGISTRY["hero"] = _counting(B.Hero)


def _job(args):
    name, field, tables, seed = args[:4]
    bot, mode = (args[4], args[5]) if len(args) > 5 else ("hero", "strict")
    from hyperion.drills import variants as V
    from hyperion.sim import bestiary as B
    from hyperion.sim.bestiary import field_names
    from hyperion.sim.runner import run_tournament

    hero_config = None
    if mode == "model":
        import importlib.util

        spec = importlib.util.spec_from_file_location("vm_swap_tool", str(ROOT / "tools" / "swap.py"))
        sw = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sw)
        sw.setup_process("model")
        hero_config = B.HERO_CONFIG
    _install_counting_hero()
    me = "hero"
    if bot == "ship":
        me = _install_counting_ship()
        field = f"{field}@{me}"
    elif bot != "hero":
        raise KeyError(f"--bot is hero or ship, got {bot!r}")
    _STATE.update(hands=0, vpip=0, heroes=[])
    v = V.get(name, seed=seed)
    t0 = time.perf_counter()
    rep = run_tournament(field_names(field), tables, seed, variant=v, mode=mode, hero_config=hero_config)
    secs = time.perf_counter() - t0
    order = sorted(rep.bots.values(), key=lambda b: -b.mean)
    hero = rep.bots[me]
    rank = [b.name for b in order].index(me) + 1
    leader = order[0]
    st = hero.stats
    if bot == "hero":
        inner = sum(getattr(getattr(h, "impl", None), "safe", None).errors if getattr(getattr(h, "impl", None), "safe", None) else 0
                    for h in _STATE["heroes"])
    else:  # the engine harvests every SafeBot's inner errors once per table (BotStats.safe_err)
        inner = st.safe_err
    return {
        "variant": name, "axis": v.axis, "pts": hero.mean, "ci": hero.ci95, "rank": rank, "n_bots": len(order),
        "leader": leader.name, "leader_pts": leader.mean, "second": order[1].name if len(order) > 1 else "",
        "second_pts": order[1].mean if len(order) > 1 else 0.0,
        "bust": 100 * hero.bust_rate, "exc": st.exceptions, "inner": inner, "ill": st.illegal, "tmo": st.over_budget,
        "p99": st.percentile_us(0.99), "vpip": 100 * _STATE["vpip"] / _STATE["hands"] if _STATE["hands"] else 0.0,
        "hands": rep.hands, "secs": secs,
    }


def verdict(r: dict) -> tuple[str, str]:
    if r["exc"] or r["inner"]:
        return "BROKEN", f"{r['exc']} engine exceptions, {r['inner']} inner errors"
    if r["vpip"] < 10.0:
        return "WEAK", f"VPIP {r['vpip']:.0f}%: Hero is not playing"
    if r["rank"] >= 5:
        return "WEAK", f"rank {r['rank']}; {r['leader']} leads with {r['leader_pts']:.2f}"
    if r["rank"] >= 3:
        return "PLAYS", f"rank {r['rank']}; {r['leader']} {r['leader_pts']:.2f}, {r['second']} {r['second_pts']:.2f}"
    if r["rank"] == 2:
        return "READY", f"second to {r['leader']} {r['leader_pts']:.2f}"
    return "READY", f"next {r['second']} {r['second_pts']:.2f}"


def render(rows: list[dict], field: str, tables: int, seed: int, bot: str = "hero", mode: str = "strict") -> str:
    who = "Hero" if bot == "hero" else "F (the ship bot, in Hero's seat)"
    lines = [f"Bot {who}; field `{field}`, {tables} tables, seed {seed}, {mode} mode; rank is its place among the field's "
             f"bot names by points; exc = engine exceptions + SafeBot inner errors; VPIP over hands Hero acted in preflop.",
             "",
             "| variant | axis | hero pts (±95%) | rank | exc | ill | VPIP % | bust % | p99 us | verdict | reason |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        v, why = verdict(r)
        lines.append(f"| {r['variant']} | {r['axis']} | {r['pts']:.2f} ± {r['ci']:.2f} | {r['rank']} / {r['n_bots']} | "
                     f"{r['exc'] + r['inner']} | {r['ill']} | {r['vpip']:.0f} | {r['bust']:.0f} | {r['p99']:.0f} | "
                     f"**{v}** | {why if v != 'READY' or r['rank'] == 2 else why} |")
    counts = {}
    for r in rows:
        counts[verdict(r)[0]] = counts.get(verdict(r)[0], 0) + 1
    lines.append("")
    lines.append("Verdicts: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())) + ".")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--tables", type=int, default=300)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--field", default="realistic")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--only", default=None, help="comma-separated entry names (default: the whole catalog); held-out "
                                                "names resolve too")
    p.add_argument("--unseen", action="store_true", help="the held-out catalog (hyperion/drills/variants_unseen.py) "
                                                         "instead of the 23 entries: a test set, never tuning input")
    p.add_argument("--bot", default="hero", help="hero (bestiary Hero, the default) | ship (F, hyperion/ship.py's "
                                                  "composite with its shipped dials, in Hero's seat)")
    p.add_argument("--mode", default="strict", choices=("strict", "model"),
                   help="strict (as before) | model (replayable: the climb's fixed-speed setup)")
    p.add_argument("--out", default=None, help="also write the markdown here")
    a = p.parse_args(argv)
    from hyperion.drills import variants as V

    if a.only:
        names = a.only.split(",")
    elif a.unseen:
        from hyperion.drills import variants_unseen as U

        names = U.names()
    else:
        names = V.catalog_names()
    jobs = [(n, a.field, a.tables, a.seed, a.bot, a.mode) for n in names]
    t0 = time.perf_counter()
    with Pool(a.workers) as pool:
        rows = pool.map(_job, jobs, chunksize=1)
    by_name = {r["variant"]: r for r in rows}
    rows = [by_name[n] for n in names]
    text = render(rows, a.field, a.tables, a.seed, a.bot, a.mode)
    print(text)
    print(f"\n{len(rows)} entries in {time.perf_counter() - t0:.0f}s on {a.workers} workers")
    if a.out:
        Path(a.out).write_text(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
