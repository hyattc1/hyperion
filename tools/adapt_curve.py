#!/usr/bin/env python
"""Does an adaptive test opponent learn? Its chips per hand by hand window, against the bot in the hero seat, with the
same deals for the bot and its counters-off twin (R6, decisions "The climb: addendum 9").

    .venv/bin/python tools/adapt_curve.py --field adapt_hu --set screen            (F in the hero seat, adapt1 and twin)
    .venv/bin/python tools/adapt_curve.py --field adapt --hero rival2 --set 10000:10100   (a field without F)

The hero seat plays `--hero`: a spec as tools/climb_accept.py takes it ({"dials": {}} or '' is F, the default; a bare
registry name is that bot). The adaptive seat plays `--bot` (default adapt1) and, on the same seeds, `--twin` (default
adapt1_off). Each cell plays as climb_accept's exploit stage does: model mode, eight rotations per seed, payouts
10/7/5/4/3/2/1/0 at 8-max, rules hu.json / three.json short-handed.

Per hand the adaptive seat's chip delta is read at hand end, and the chips that flowed between it and the hero seat:
each loser's chips are split over the winners in proportion to what each won, so flow(hero -> adaptive) is exact
heads-up and a proportional share at more seats. Windows are hands 1-30, 31-100 and 101-200 (the counters cannot be
on before hand 31). Printed per window, for the bot and its twin: chips per hand and bb per hand (all hands the
adaptive seat was alive for), the flow from the hero seat per hand, and the paired per-table difference bot - twin in
window chips (95% interval over seeds). Points per table for both seats close the table.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location("climb_accept_tool", os.path.join(_HERE, "climb_accept.py"))
CA = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(CA)
SW = CA.SW

WINDOWS = ((0, 30), (30, 100), (100, 200))
CELLS = {"adapt": ("brief", None), "adapt_hu": ("lin", "hu"), "adapt_3": ("lin", "three")}
CHUNK = 10


def _hero_spec(s: str) -> dict:
    t = s.strip()
    if t and not t.startswith("{") and not os.path.exists(t) and "+" not in t:
        from hyperion.sim import bestiary as B

        if t in B.REGISTRY:
            return {"bot": t}
    return CA.resolve(CA.load_spec(t))


def _job(args):
    field, hero_spec, bots, off, n = args
    SW.setup_process("model")
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table

    pay, rules_name = CELLS[field]
    rules = CA._rules(pay, rules_name)
    from hyperion.core.types import Rules

    rules = rules if rules is not None else Rules()
    hero = SW._spec_bot("hero_x", hero_spec)
    sink = []
    orig = B.Adapt1Bot.hand_end

    def rec(self, result):
        sink.append((self.seat, result.hand_no, list(result.deltas)))
        orig(self, result)

    B.Adapt1Bot.hand_end = rec
    out = {}
    try:
        for bot in bots:
            names = [hero if x == "hero" else (bot if x == "adapt1" else x) for x in B.field_names(field)]
            per_seed = []
            for t in range(off, off + n):
                table_seed = SW.SEED * 1_000_003 + t
                rng = random.Random(table_seed)
                seating = list(names[:rules.n_players])
                while len(seating) < rules.n_players:
                    seating.append(rng.choice(names))
                rng.shuffle(seating)
                a_seat, h_seat = seating.index(bot), seating.index(hero)
                tabs = []
                for rot in range(rules.n_players):
                    built = [B.make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
                    del sink[:]
                    res = play_table(built, rules, seed=table_seed, rotation=rot, mode="model")
                    win = [[0, 0.0, 0.0, 0.0] for _ in WINDOWS]  # hands, chips, bb, flow from hero
                    for seat, hand, d in sink:
                        if seat != a_seat:
                            continue
                        bb = rules.blinds_at(hand)[1]
                        pos = sum(x for x in d if x > 0)
                        flow = 0.0
                        if pos:
                            if d[h_seat] < 0 < d[a_seat]:
                                flow = -d[h_seat] * d[a_seat] / pos
                            elif d[a_seat] < 0 < d[h_seat]:
                                flow = d[a_seat] * d[h_seat] / pos
                        for w, (lo, hi) in enumerate(WINDOWS):
                            if lo <= hand < hi:
                                x = win[w]
                                x[0] += 1
                                x[1] += d[a_seat]
                                x[2] += d[a_seat] / bb
                                x[3] += flow
                    tabs.append({"win": win, "pts": res.points[a_seat], "hero_pts": res.points[h_seat],
                                 "hands": res.hands})
                per_seed.append(tabs)
            out[bot] = per_seed
    finally:
        B.Adapt1Bot.hand_end = orig
    return off, out


def summarize(data: dict, bots: list) -> str:
    lines = []
    n_seeds = len(next(iter(data.values())))
    for bot in bots:
        seeds = data[bot]
        lines.append(f"\n### {bot} ({n_seeds} seeds x {len(seeds[0])} rotations)\n")
        lines.append("| hands | n hands | chips/hand | bb/hand | flow from hero/hand |")
        lines.append("|---|---|---|---|---|")
        for w, (lo, hi) in enumerate(WINDOWS):
            h = sum(t["win"][w][0] for s in seeds for t in s)
            c = sum(t["win"][w][1] for s in seeds for t in s)
            b = sum(t["win"][w][2] for s in seeds for t in s)
            f = sum(t["win"][w][3] for s in seeds for t in s)
            lines.append(f"| {lo + 1}-{hi} | {h} | {c / max(h, 1):+.2f} | {b / max(h, 1):+.4f} | "
                         f"{f / max(h, 1):+.2f} |")
        pts = [sum(t["pts"] for t in s) / len(s) for s in seeds]
        hp = [sum(t["hero_pts"] for t in s) / len(s) for s in seeds]
        lines.append(f"\npoints: {bot} {sum(pts) / len(pts):.3f}, hero seat {sum(hp) / len(hp):.3f}")
    if len(bots) == 2:
        a, b = bots
        lines.append(f"\n### paired: {a} - {b}, per table, window sums (95% over seeds)\n")
        lines.append("| hands | chips | flow from hero | bb |")
        lines.append("|---|---|---|---|")
        for w, (lo, hi) in enumerate(WINDOWS):
            row = []
            for k in (1, 3, 2):
                d = [sum(t["win"][w][k] for t in sa) / len(sa) - sum(t["win"][w][k] for t in sb) / len(sb)
                     for sa, sb in zip(data[a], data[b])]
                m = sum(d) / len(d)
                v = sum((x - m) ** 2 for x in d) / (len(d) - 1) if len(d) > 1 else 0.0
                row.append(f"{m:+.1f} ± {1.96 * math.sqrt(v / len(d)):.1f}")
            lines.append(f"| {lo + 1}-{hi} | " + " | ".join(row) + " |")
        for nm, key in ((a, "pts"), ("hero seat", "hero_pts")):
            d = [sum(t[key] for t in sa) / len(sa) - sum(t[key] for t in sb) / len(sb)
                 for sa, sb in zip(data[a], data[b])]
            m = sum(d) / len(d)
            v = sum((x - m) ** 2 for x in d) / (len(d) - 1) if len(d) > 1 else 0.0
            lines.append(f"\npoints, {nm}: with {a} - with {b} = {m:+.3f} ± {1.96 * math.sqrt(v / len(d)):.3f}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--field", choices=sorted(CELLS), default="adapt_hu")
    p.add_argument("--hero", default='{"dials": {}}', help="the hero seat: a climb_accept spec (default F) or a bot name")
    p.add_argument("--bot", default="adapt1")
    p.add_argument("--twin", default="adapt1_off", help="'' for none")
    p.add_argument("--set", default="screen")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--json", default=None, help="write the per-seed data here")
    a = p.parse_args(argv)
    lo, hi = CA.seed_range(a.set)
    hero = _hero_spec(a.hero)
    bots = [a.bot] + ([a.twin] if a.twin else [])
    jobs = [(a.field, hero, bots, off, min(CHUNK, hi - off)) for off in range(lo, hi, CHUNK)]
    t0 = time.time()
    res = {}
    with Pool(a.workers, maxtasksperchild=4) as pool:
        for off, out in pool.imap_unordered(_job, jobs):
            res[off] = out
    data = {b: [s for off in sorted(res) for s in res[off][b]] for b in bots}
    print(f"# adapt_curve: field {a.field}, hero {json.dumps(hero, sort_keys=True)}, set {a.set} ({lo}-{hi - 1}), "
          f"{(time.time() - t0) / 60:.1f} min")
    print(summarize(data, bots))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump({"field": a.field, "hero": hero, "set": [lo, hi], "data": data}, fh)
    return 0


if __name__ == "__main__":
    sys.exit(main())
