#!/usr/bin/env python
"""Does the zip play as the source does? Every number we trust measures the repo; what we upload is the zip.

    python tools/zip_parity.py dist/submission.zip [--scale 1.0] [--workers 3] [--json OUT] [--max-bad 3]

The zip is extracted to a temp dir and its bot built there, from the zip's own hyperion package, in a fresh `python -I -B`
(tools/zip_host.py: PYTHONPATH cleared, cwd elsewhere), with the bot and dials the zip records. The source bot is the
same record built from this repo, in a process of the same shape. Both sit in one seat of the same deterministic tables
(model mode: opponents at fixed speed, the table's seeds, the bot's seed; panic, soft deadlines and late_us off:
tools/slowbox.py's DET, the settings tools/swap.py's model mode plays), get the same observations, and must give the same
action, decision for decision, variant decisions and each table's route counters included. Play follows the source; the
first mismatch of a table is reported and the table abandoned.

PASS needs all of:
  - no mismatch, on any decision;
  - the static check (tools/table_probe.py on the unpacked zip) finds no table the recorded bot needs and lacks;
  - no table file the play itself opened, on either side, is absent from the zip (a lazily loaded table the probe's map
    forgot);
  - every route the recorded bot carries fired, on both sides: the strong-table route, the heads-up specialist and R6's
    three-handed table. Its decisions are counted and printed; a count of zero fails, so this cannot pass vacuously.

CELLS are the tables, sized (1.0) to about 5 minutes at 3 workers on a loaded box; 8-max rooms (night, the strong tables
where the strong route and R6 fire), the heads-up and three-handed formats (the specialist behind its looseness gate),
and three twists (the lazily loaded tables). Part of the freeze: PLAYBOOK "Freezing a batch", after tools/pack.py and before
tools/gate.py. It does not time anything and does not go through a kit's adapter: tools/gate.py does that. Exit 1 on FAIL.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import pickle
import random
import struct
import subprocess
import sys
import tempfile
import time
import zipfile
from multiprocessing import Pool
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_HERE = str(ROOT / "tools")
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]  # a tools/*.py never shadows the stdlib
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

HOST = ROOT / "tools" / "zip_host.py"
PROBE = ROOT / "tools" / "table_probe.py"
RULES_DIR = ROOT / "docs" / "drills" / "climb" / "rules"
SEAT = "zip_parity_seat"
ROUTES = {"strong": "the strong-table route", "hu": "the heads-up specialist", "3b": "R6's three-handed table"}
# (field, rules file, variant, table seeds, seed offset). A table seed is every rotation of it.
CELLS = (("night", None, None, 20, 500),
         ("elite", None, None, 16, 520),
         ("mirror", None, None, 8, 540),
         ("elite_night", None, None, 8, 550),
         ("exploit2_hu", "hu", None, 40, 560),
         ("exploit2_3", "three", None, 30, 600),
         ("realistic", None, "auction", 6, 640),
         ("realistic", None, "bonus_card", 6, 650),
         ("realistic", None, "tranche_holdem", 6, 660))
QUICK = (("elite", None, None, 3, 520), ("exploit2_hu", "hu", None, 4, 560))
CHUNK = 4


def load_tool(name: str):
    """A tools/ module by path (they keep tools/ off sys.path, so one cannot simply import the next)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def clean_env() -> dict:
    return {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "HYPERION_"))}


class Host:
    """A bot's process (tools/zip_host.py)."""

    def __init__(self, root: Path, bot: str, dials: dict, cwd: str, extra=(), preexec=None):
        self.proc = subprocess.Popen([sys.executable, "-I", "-B", str(HOST), str(root), bot, json.dumps(dials), *extra],
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, cwd=cwd, env=clean_env(),
                                     preexec_fn=preexec)
        self.hello = self.get()[1]

    def put(self, *msg) -> None:
        data = pickle.dumps(msg, protocol=4)
        self.proc.stdin.write(struct.pack("<I", len(data)) + data)
        self.proc.stdin.flush()

    def get(self):
        head = self.proc.stdout.read(4)
        if len(head) < 4:
            raise RuntimeError(f"the bot's process died (exit {self.proc.poll()})")
        return pickle.loads(self.proc.stdout.read(struct.unpack("<I", head)[0]))

    def call(self, *msg):
        self.put(*msg)
        return self.get()

    def close(self) -> None:
        try:
            self.put("bye")
            self.proc.stdin.close()
            self.proc.wait(timeout=10)
        except Exception:  # noqa: BLE001
            self.proc.kill()


class DuelSeat:
    """One seat, two bots: each call goes to both and the answers must match. Plays the source's."""

    hosts: tuple = ()  # (source, zip), set per job
    tally: dict = {}
    first_bad: str | None = None  # the table's first mismatch (play goes on with the source's answers)

    def __init__(self, seed=None):
        self.seed = seed
        self.where = ""

    def new_table(self, rules, seat, n_players) -> None:
        self.where = f"seed {self.seed} seat {seat}"
        for h in self.hosts:
            h.put("table", self.seed, rules, seat, n_players)
        for h in self.hosts:
            h.get()
        self.tally["tables"] += 1

    def _both(self, *msg):
        for h in self.hosts:
            h.put(*msg)
        return [h.get()[0] for h in self.hosts]

    def _same(self, kind, a, b, obs=None) -> None:
        self.tally[kind] += 1
        if a != b and DuelSeat.first_bad is None:
            at = "" if obs is None else (f" hand {obs.hand_no} street {obs.street} hole {obs.hole} board {obs.board} "
                                         f"stacks {obs.stacks} to_call {obs.to_call}")
            DuelSeat.first_bad = f"{self.where}{at}: source {a!r}, zip {b!r}"

    def act(self, obs):
        a, b = self._both("act", obs)
        self._same("decisions", a, b, obs)
        return a

    def hand_end(self, result) -> None:
        self._both("end", result)

    def variant_decide(self, prompt):
        a, b = self._both("variant", prompt)
        self._same("variant_decisions", a, b)
        return a


def _rules_of(rules_name):
    from hyperion.core.types import Rules

    if not rules_name:
        return None
    with open(RULES_DIR / f"{rules_name}.json") as fh:
        extra = json.load(fh)
    return Rules(**{k: tuple(tuple(x) if isinstance(x, list) else x for x in v) if isinstance(v, list) else v
                    for k, v in extra.items()})


def _job(args):
    """One chunk of one cell: (cell label, tally, the source's state, mismatches)."""
    field, rules_name, variant, offset, n, pkg, bot, dials = args
    SW = load_tool("swap")  # tools/swap.py's model-mode settings for the opponents
    DET = load_tool("slowbox").DET

    SW.setup_process("model")
    from hyperion.drills import variants as V
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import BotStats, play_table

    # slowbox's DET, and Hero's own SafeBot too (it plays whole twist tables): two processes at load must not panic apart
    det = {**DET.get(bot, {}), **({"hero.panic_after": 10 ** 9} if bot == "composite" else {}), **dials}
    label = field + (f"+{rules_name}" if rules_name else "") + (f"+{variant}" if variant else "")
    tally = {"tables": 0, "decisions": 0, "variant_decisions": 0}
    seen = {"strong": 0, "hu": 0, "3b": 0, "short": 0}
    routes: set = set()
    opened: set = set()
    bad: list = []
    B.REGISTRY[SEAT] = DuelSeat
    rules = _rules_of(rules_name)
    v = V.get(variant, seed=SW.SEED) if variant else None
    rules = rules if rules is not None else v.rules if v is not None else None
    from hyperion.core.types import Rules

    rules = rules or Rules()
    names = [nm.strip().lower() for nm in B.field_names(f"{field}@{SEAT}") if nm.strip()]
    with tempfile.TemporaryDirectory(prefix="zip_parity_cwd_") as cwd:
        hosts = (Host(ROOT, bot, det, cwd), Host(Path(pkg), bot, det, cwd))  # one process per chunk: a bot per table
        DuelSeat.hosts, DuelSeat.tally = hosts, tally
        if not Path(hosts[1].hello["hyperion"]).resolve().is_relative_to(Path(pkg).resolve()):
            raise SystemExit(f"FAIL the zip's bot imported {hosts[1].hello['hyperion']}, outside the zip")
        try:
            for t in range(offset, offset + n):
                table_seed = SW.SEED * 1_000_003 + t
                rng = random.Random(table_seed)
                seats = list(names[:rules.n_players])
                while len(seats) < rules.n_players:
                    seats.append(rng.choice(names))
                rng.shuffle(seats)
                for rot in range(rules.n_players):
                    DuelSeat.first_bad = None
                    bots = [B.make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seats)]
                    stats = [BotStats(nm) for nm in seats]
                    hooks = v.new_hooks() if v is not None else None
                    play_table(bots, rules, seed=table_seed, rotation=rot, mode="model", stats=stats, variant=hooks)
                    me = seats.index(SEAT)
                    if stats[me].exceptions:  # the engine catches a call that raised: here, a bot's process that died
                        bad.append(f"{label} table {t} rotation {rot}: {stats[me].last_error}")
                        return label, tally, seen, sorted(routes), sorted(opened), bad
                    a, b = hosts[0].call("state")[0], hosts[1].call("state")[0]
                    if DuelSeat.first_bad is not None:
                        bad.append(f"{label} table {t} rotation {rot}: {DuelSeat.first_bad}")
                    elif {k: a[k] for k in seen} != {k: b[k] for k in seen}:
                        bad.append(f"{label} table {t} rotation {rot}: route counters differ: source "
                                   f"{ {k: a[k] for k in seen} }, zip { {k: b[k] for k in seen} }")
                    for k in seen:
                        seen[k] += a[k]
                    routes.update(a["routes"])
                    opened.update(a["opened"])  # the source's: what the bot we measured reads, which a zip that lacks
                    opened.update(b["opened"])  # it may never try to open (a directory listed, nothing found)
        finally:
            for h in hosts:
                h.close()
    return label, tally, seen, sorted(routes), sorted(opened), bad


def probe_zip(pkg: Path, cwd: str) -> dict:
    proc = subprocess.run([sys.executable, "-I", "-B", str(PROBE), str(pkg)], cwd=cwd, env=clean_env(), capture_output=True,
                          text=True, timeout=300)
    if proc.returncode != 0:
        raise SystemExit("FAIL the zip's recorded bot does not build: " + " | ".join(proc.stderr.strip().splitlines()[-3:]))
    return json.loads(proc.stdout.strip().splitlines()[-1])


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("zip", help="the packed submission.zip")
    p.add_argument("--scale", type=float, default=1.0, help="table seeds per cell x this (at least one)")
    p.add_argument("--workers", type=int, default=3)
    p.add_argument("--quick", action="store_true", help="the tests' cells: few tables, still firing every route")
    p.add_argument("--only", help="only the cells of these fields (comma-separated)")
    p.add_argument("--json", help="write the report here")
    p.add_argument("--max-bad", type=int, default=3, help="stop after this many mismatching tables")
    a = p.parse_args(argv)
    src = Path(a.zip).resolve()
    if not src.is_file():
        print(f"FAIL no such zip: {src}")
        return 1
    t0 = time.perf_counter()
    report: dict = {"zip": str(src), "cells": {}, "fails": []}
    with tempfile.TemporaryDirectory(prefix="zip_parity_") as tmp:
        pkg = Path(tmp) / "package"
        pkg.mkdir()
        with zipfile.ZipFile(src) as zf:
            zf.extractall(pkg)
        static = probe_zip(pkg, tmp)
        bot, dials = static["bot"], static["dials"]
        print(f"zip      {src}\nbot      {bot} dials {dials} (the zip's record)\nhyperion {static['hyperion']}")
        print(f"tables   opened at the build {len(static['opened'])}, declared {len(static['declared'])}, lacking "
              f"{static['lacking'] or 'none'}")
        fails = []
        if static["lacking"]:
            fails.append("the zip lacks tables its recorded bot needs: " + ", ".join(static["lacking"]))
        if static["specialist_missing"]:
            fails.append(f"the specialist's loader returned None: {static['specialist_missing']}")
        cells = QUICK if a.quick else CELLS
        if a.only:
            cells = tuple(c for c in cells if c[0] in a.only.split(","))
        jobs = []
        for field, rules_name, variant, n, off in cells:
            n = max(1, round(n * a.scale))
            for i in range(0, n, CHUNK):
                jobs.append((field, rules_name, variant, off + i, min(CHUNK, n - i), str(pkg), bot, dials))
        total = {"tables": 0, "decisions": 0, "variant_decisions": 0}
        seen = {"strong": 0, "hu": 0, "3b": 0, "short": 0}
        routes: set = set()
        opened: set = set()
        bad: list = []
        with Pool(a.workers) as pool:
            for label, tally, s, r, o, b in pool.imap_unordered(_job, jobs):
                cell = report["cells"].setdefault(label, {"tables": 0, "decisions": 0, "variant_decisions": 0,
                                                          "strong": 0, "hu": 0, "3b": 0, "short": 0})
                for k, v in {**tally, **s}.items():
                    cell[k] += v
                for k in total:
                    total[k] += tally[k]
                for k in seen:
                    seen[k] += s[k]
                routes.update(r)
                opened.update(o)
                bad.extend(b)
                if len(bad) >= a.max_bad:
                    pool.terminate()
                    print(f"stopped after {len(bad)} mismatches")
                    break
        for label, c in sorted(report["cells"].items()):
            print(f"{label:<28} tables {c['tables']:>4}  decisions {c['decisions']:>7}  variant {c['variant_decisions']:>5}  "
                  f"strong {c['strong']:>5}  specialist heads-up {c['hu']:>5}  R6 {c['3b']:>5}")
        print(f"{'all':<28} tables {total['tables']:>4}  decisions {total['decisions']:>7}  variant "
              f"{total['variant_decisions']:>5}  strong {seen['strong']:>5}  specialist heads-up {seen['hu']:>5}  R6 "
              f"{seen['3b']:>5}")
        lacking = sorted(t for t in opened if not (pkg / "tables" / t).is_file())
        if lacking:
            fails.append("the play opened tables the zip lacks: " + ", ".join(lacking))
        if bad:
            fails.append(f"{len(bad)} tables differ; first: {bad[0]}")
        if not bad:
            for r in sorted(routes):
                if seen[r] == 0:
                    fails.append(f"{ROUTES[r]} ({r}) never fired: this run proves nothing about it")
        report.update(total=total, fired=seen, routes=sorted(routes), opened=sorted(opened), mismatches=bad[:20], fails=fails,
                      secs=round(time.perf_counter() - t0, 1))
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1) + "\n")
    print(f"opened   {len(opened)} table files in play; {report['secs']} s")
    for x in bad[:5]:
        print(f"MISMATCH {x}")
    if fails:
        print("PARITY FAIL: " + "; ".join(fails))
        return 1
    print(f"PARITY PASS: {total['decisions']} decisions and {total['variant_decisions']} variant decisions identical over "
          f"{total['tables']} tables; strong {seen['strong']}, specialist heads-up {seen['hu']}, R6 {seen['3b']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
