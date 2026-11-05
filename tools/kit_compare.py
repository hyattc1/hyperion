#!/usr/bin/env python
"""Two zips through a kit's adapter, the same tables, the same hour: the timing and the points of the kit path, paired.

    python tools/kit_compare.py A.zip B.zip [--kit SEAT.py --entry bot.py] [--slow K] [--tables 40] [--t0 0] [--seed 7]
                                [--rotations 1] [--field realistic] [--rules FILE] [--workers 3] [--json OUT] [--det]

tools/gate.py pairs a package against an in-sim baseline; this pairs two packages. Each (table, rotation) is played by A, then
by B, in the gate's own seat (tools/gate.py GateTable and HostProxy: one fresh `python -I -B` per table, the bot behind
the kit's adapter, 1 ms a decision, strict, K-times clock with --slow), with every other seat identical, on the same
seeds as tools/swap.py (table seed = seed * 1,000,003 + t, seats' seeds table_seed * 64 + rotation * 8 + seat). The bot's own
seed is fixed too, so two bots that decide alike play alike, and the pairs are as tight as they can be: on fake kit B (the default)
each package's copy gets `entry_compare.py`, make_kit_b_module around ship.make_bot(seed=...); with --kit, a seat file (drill 12's
kit J: closure_gate_seat_template.py), the package's --entry with its `ship.make_bot()` so seeded.

--det is the identity check: both packages' records get tools/slowbox.py's DET dials (panic, soft deadlines, late_us off), the
table runs in model mode (opponents at fixed speed, nothing enforced), and every reply must be the same, table by table: the
first difference is reported and the table abandoned. Exit 1 when one differs.

Printed for each side: decisions, timeouts, p50, p99, p99.9, max (us, the gate's clock around the kit's call), the governor's line
(tools/gate_host.py governor_report). Without --det, the points of each, and A - B paired over the tables with its 95% interval.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import math
import os
import shutil
import sys
import tempfile
import time
import zipfile
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_HERE = str(ROOT / "tools")
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ENTRY = "entry_compare.py"
ENTRY_TEXT = """import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperion import ship
from hyperion.drills.adapter import make_kit_b_module

decide, on_table_start, on_hand_end = make_kit_b_module(ship.make_bot(seed=int(os.environ["KIT_COMPARE_SEED"])))
"""
BOT_SEED_MUL = 97


def load_tool(name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def prepare(src: Path, into: Path, det: bool, entry: str | None = None) -> Path:
    """The package of `src` in `into`, with the entry that seeds the bot; --det: its record's dials with DET on top."""
    with zipfile.ZipFile(src) as zf:
        zf.extractall(into)
    if entry is None:
        (into / ENTRY).write_text(ENTRY_TEXT)
    else:
        text = (into / entry).read_text()
        if "ship.make_bot()" not in text or "import os" not in text:
            raise SystemExit(f"FAIL {entry}: no ship.make_bot() to seed")
        (into / ENTRY).write_text(text.replace("ship.make_bot()", 'ship.make_bot(seed=int(os.environ["KIT_COMPARE_SEED"]))'))
    if det:
        from hyperion import ship

        SB = load_tool("slowbox")
        name, dials = ship.read_record(into / "hyperion" / "ship.py")
        ship.write_record(into / "hyperion" / "ship.py", name, {**dials, **SB.DET[name]})
    return into


def play_chunk(job: dict) -> dict:
    gate = load_tool("gate")
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary
    from hyperion.sim.engine import BotStats
    from hyperion.sim.runner import load_rules

    class Traced(gate.HostProxy):
        """The gate's proxy, its replies recorded."""

        def __init__(self, cfg):
            super().__init__(cfg, "seat" if job["seat_file"] else "b")
            self.trace, self.ns = [], []

        def decide(self, obs):
            r = super().decide(obs)
            self.trace.append((obs.hand_no, obs.street, r.kind, r.total, r.error))
            if r.ns is not None:
                self.ns.append(r.ns)
            return r

    rules = load_rules(job["rules"])
    names = job["names"]
    n = rules.n_players
    out = {"pairs": [], "sides": [{"ns": [], "late": 0, "exc": 0, "ill": 0, "imports": [], "gov": {}, "notes": []} for _ in job["pkgs"]],
           "mismatch": []}
    with tempfile.TemporaryDirectory(prefix="kitcmp_") as tmp:
        kit_dir = Path(tmp) / "kit"
        kit_dir.mkdir()
        if not job["seat_file"]:
            shutil.copy2(gate.FAKEKITS / "kit_b" / "kit.py", kit_dir / "kit.py")
        scratch = Path(tmp) / "cwd"
        scratch.mkdir()
        mode = "model" if job["det"] else "strict"
        for t, rot in job["tables"]:
            table_seed = job["seed"] * 1_000_003 + t
            seating = gate.seating_for(names, n, table_seed)
            g = seating.index("hero")
            os.environ["KIT_COMPARE_SEED"] = str((table_seed * 64 + rot * 8 + g) * BOT_SEED_MUL % (2 ** 31))
            traces, points = [], []
            for i, pkg in enumerate(job["pkgs"]):
                seat_file = Path(job["seat_file"]) if job["seat_file"] else None
                cfg = gate.Config(pkg=Path(pkg), entry=ENTRY, kit="seat" if seat_file else "b", kit_dir=kit_dir,
                                  scratch=str(scratch), slow=job["slow"], seat_file=seat_file)
                bots = [bestiary.make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
                proxy = Traced(cfg)
                bots[g] = proxy
                stats = [BotStats(nm) for nm in seating]
                try:
                    res = gate.GateTable(bots, rules, table_seed, mode, None, stats, g, proxy, rotation=rot).play()
                finally:
                    proxy.close()
                side = out["sides"][i]
                side["ns"].extend(proxy.ns)
                side["late"] += proxy.late
                side["exc"] += stats[g].exceptions
                side["ill"] += stats[g].illegal
                if proxy.import_s is not None:
                    side["imports"].append(proxy.import_s)
                gate.add_gov(side["gov"], proxy.gov)
                for x in proxy.notes[:2]:
                    if len(side["notes"]) < 4:
                        side["notes"].append(x)
                traces.append(proxy.trace)
                points.append(res.points[g])
            out["pairs"].append((t, rot, points[0], points[1]))
            if job["det"] and traces[0] != traces[1]:
                i = next((k for k, (x, y) in enumerate(zip(*traces)) if x != y), min(map(len, traces)))
                out["mismatch"].append({"t": t, "rot": rot, "at": i, "a": traces[0][i:i + 1], "b": traces[1][i:i + 1]})
    return out


def pct(xs: list, q: float) -> float:
    return xs[min(len(xs) - 1, int(q * len(xs)))] if xs else 0.0


def merge_gov(gate, total: dict, one: dict) -> None:
    if not one:
        return
    if one.get("acts") or one.get("reports"):
        gate.add_gov(total, one)
    total["no_report"] = total.get("no_report", 0) + one.get("no_report", 0)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("a")
    p.add_argument("b")
    p.add_argument("--kit", default=None, help="a seat file for another kit (default: fake kit B)")
    p.add_argument("--entry", default=None, help="with --kit: the package's entry, its ship.make_bot() seeded here")
    p.add_argument("--slow", type=float, default=0.0)
    p.add_argument("--tables", type=int, default=40)
    p.add_argument("--t0", type=int, default=0, help="the first table's number (screen seeds: 10000-10199)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--rotations", type=int, default=1)
    p.add_argument("--field", default="realistic")
    p.add_argument("--rules", default="default")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--chunk", type=int, default=8)
    p.add_argument("--json")
    p.add_argument("--det", action="store_true")
    a = p.parse_args(argv)

    gate = load_tool("gate")
    from hyperion.sim import bestiary

    names = bestiary.field_names(a.field)
    if "hero" not in names:
        raise SystemExit("FAIL the field needs a `hero` seat (name it: --field night@hero)")
    tables = [(t, r) for t in range(a.t0, a.t0 + a.tables) for r in range(a.rotations)]
    t00 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="kitcmp_pk_") as tmp:
        pkgs = []
        for i, src in enumerate((a.a, a.b)):
            d = Path(tmp) / f"p{i}"
            d.mkdir()
            pkgs.append(str(prepare(Path(src), d, a.det, a.entry if a.kit else None)))
        jobs = [{"pkgs": pkgs, "tables": tables[i:i + a.chunk], "seed": a.seed, "slow": a.slow, "rules": a.rules, "names": names,
                 "det": a.det, "seat_file": str(Path(a.kit).resolve()) if a.kit else None} for i in range(0, len(tables), a.chunk)]
        sides = [{"ns": [], "late": 0, "exc": 0, "ill": 0, "imports": [], "gov": {}, "notes": []} for _ in pkgs]
        pairs, mismatch = [], []
        done = 0
        with Pool(a.workers) as pool:
            for r in pool.imap_unordered(play_chunk, jobs):
                pairs += r["pairs"]
                mismatch += r["mismatch"]
                for s, o in zip(sides, r["sides"]):
                    s["ns"] += o["ns"]
                    for k in ("late", "exc", "ill"):
                        s[k] += o[k]
                    s["imports"] += o["imports"]
                    merge_gov(gate, s["gov"], o["gov"])
                    for x in o["notes"]:
                        if len(s["notes"]) < 4 and x not in s["notes"]:
                            s["notes"].append(x)
                done += len(r["pairs"])
                print(f"   {done}/{len(tables)} tables ({time.perf_counter() - t00:.0f} s)", file=sys.stderr, flush=True)
    res = {"a": a.a, "b": a.b, "kit": a.kit or "b", "slow": a.slow, "field": a.field, "rules": a.rules, "t0": a.t0, "tables": a.tables,
           "rotations": a.rotations, "det": a.det, "secs": round(time.perf_counter() - t00, 1),
           "load": list(os.getloadavg()), "sides": []}
    print(f"kit path, {'kit ' + Path(a.kit).name if a.kit else 'fake kit B'}: k {a.slow or 1}, {len(tables)} tables (t {a.t0}.. x {a.rotations}), field {a.field}, rules {a.rules}, "
          f"{'model mode, DET' if a.det else 'strict'}; {res['secs']} s, load {os.getloadavg()[0]:.1f}")
    for label, s, idx in (("A", sides[0], 2), ("B", sides[1], 3)):
        ns = sorted(s["ns"])
        n = len(ns)
        pts = [x[idx] for x in pairs]
        mean = sum(pts) / max(1, len(pts))
        row = {"label": label, "decisions": n, "timeouts": s["late"], "tmo_pct": round(100 * s["late"] / max(1, n), 3),
               "p50": round(pct(ns, .5) / 1000), "p90": round(pct(ns, .9) / 1000), "p99": round(pct(ns, .99) / 1000),
               "p999": round(pct(ns, .999) / 1000), "max": round(ns[-1] / 1000) if ns else 0,
               "exc": s["exc"], "ill": s["ill"], "points": round(mean, 4), "gov": s["gov"],
               "import_max": round(max(s["imports"], default=0), 3)}
        res["sides"].append(row)
        print(f"  {label} {Path(a.a if label == 'A' else a.b).parent.name}/{Path(a.a if label == 'A' else a.b).name}: n {n}  tmo "
              f"{s['late']} ({row['tmo_pct']}%)  p50 {row['p50']}  p90 {row['p90']}  p99 {row['p99']}  p99.9 {row['p999']}  max {row['max']}"
              f"  pts {mean:.3f}  exc {s['exc']} ill {s['ill']}  import worst {row['import_max']} s")
        print("    " + gate.gov_line(s["gov"]))
        for x in s["notes"]:
            print(f"    note: {x}")
    d = [x[2] - x[3] for x in pairs]
    m = sum(d) / max(1, len(d))
    sd = math.sqrt(sum((x - m) ** 2 for x in d) / max(1, len(d) - 1))
    ci = 1.96 * sd / math.sqrt(max(1, len(d)))
    res["delta"], res["ci"] = round(m, 4), round(ci, 4)
    res["pairs"] = sorted(pairs)
    res["mismatch"] = mismatch[:20]
    res["mismatches"] = len(mismatch)
    if a.det:
        print(f"  identity: {len(tables) - len(mismatch)} of {len(tables)} tables reply for reply; decisions compared {len(sides[0]['ns'])}")
        for m_ in mismatch[:5]:
            print(f"    MISMATCH {m_}")
    else:
        print(f"  A - B {m:+.3f} ± {ci:.3f} over {len(d)} tables (paired)")
    if a.json:
        Path(a.json).write_text(json.dumps(res) + "\n")
    return 1 if (a.det and mismatch) else 0


if __name__ == "__main__":
    sys.exit(main())
