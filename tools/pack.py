#!/usr/bin/env python
"""One-command submission packager (stdlib only).

    python tools/pack.py --entry submission/agent.py --out dist/ [--extra submission/adapter.py ...]
                         [--bot hybrid3_x|hero|cheap] [--dials JSON]
                         [--slim] [--rules rules_tonight.json] [--tables-dir DIR] [--note "what changed"]
                         [--night NIGHT.md]

The bot the package plays is hyperion/ship.py's SHIP with its DIALS (the shipped base, hybrid3_x, unless the file
says otherwise); --bot and --dials replace them, and pack writes the pair it packed into the package's copy of
that file, so the zip records what it plays and tools/gate.py pairs it against the same bot. `--bot cheap` is
Stage 2's Hero.cheap(); `--bot hero` restores Hero. The entry builds it with `hyperion.ship.make_bot()`.

Builds <out>/submission/: hyperion/ (never tests, docs or caches; with --slim also without
drills/fakekits, the sim bestiary and the simulator's opponents: sim/field, sim/aware.py and every rival but
rival 3), tables/ (the default tables, plus tables/variants/<name>/ when the rules name a variant; --tables-dir DIR
packages all of DIR instead), the entry file and any --extra files or directories beside it. The rules are --rules, else the first --extra JSON with Rules keys, else
rules_tonight.json beside the entry; their extras["variant"] is the active variant (drill 6 shipped
without its variant set because --tables-dir was not passed). Then, from a fresh Python started in another
directory with PYTHONPATH cleared, imports the entry module with <out>/submission first on sys.path,
checks that `hyperion` resolved from there, and times the import (fail over --import-budget seconds), then
builds the recorded bot there once if the entry imports hyperion (`hyperion.ship.make_bot()`; fail if it raises).
Checks the size against --max-mb, zips to <out>/submission.zip with the entry at the top level, prints
sha256, size and import time, and appends the same as a row under "## Submissions" in NIGHT.md if that
file exists (the minute is computed from a `T0: HH:MM` line in NIGHT.md when there is one).
Exit 1 if any check fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_NAMES = {"__pycache__", "tests", "docs", ".benchmarks", ".pytest_cache", ".git"}
SLIM_SKIPS = {ROOT / "hyperion" / "drills": {"fakekits"}, ROOT / "hyperion" / "sim": {"bestiary.py", "aware.py", "field"}}
# --slim leaves the simulator's opponents out: every field bot, judge and test opponent (hyperion/sim/field), the
# variant-aware opponents (sim/aware.py) and every rival but rival 3, whose core hybrid3_x and the composite's base
# run on. Measured by playing each ship bot (the composite with every recipe, hybrid3_x, hero, cheap) under the default
# rules and every catalog variant: hyperion.sim.rivals and its rival3 are the only simulator modules any imports
# (docs/drills/climb/r2-log.md, R4). A recorded route that names another rival's donor brings that rival back.
SLIM_RIVALS = ROOT / "hyperion" / "sim" / "rivals"
SLIM_RIVALS_KEEP = {"__init__.py", "rival3.py"}
DONOR_RIVALS = {"rival1": "rival1.py", "rival1x": "rival1.py", "r2": "rival2.py", "r2x": "rival2.py",
                "rival3": "rival3.py", "rival3x": "rival3.py"}  # hyperion/compose/bot.py DONORS that load a rival

_IMPORT_PROBE = """
import importlib, os, sys, time
dest, name = sys.argv[1], sys.argv[2]
sys.path.insert(0, dest)
t0 = time.perf_counter()
importlib.import_module(name)
dt = time.perf_counter() - t0
build = -1.0
if "hyperion" in sys.modules and os.path.isfile(os.path.join(dest, "hyperion", "ship.py")):
    t1 = time.perf_counter()
    importlib.import_module("hyperion.ship").make_bot()
    build = time.perf_counter() - t1
hyp = sys.modules.get("hyperion")
print("%.3f %.3f %s" % (dt, build, getattr(hyp, "__file__", "-") if hyp else "-"))
"""


def ship_module():
    """This repo's hyperion/ship.py loaded by path (only its stdlib record helpers and BUILDERS are used here)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_ship_record", ROOT / "hyperion" / "ship.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def record_bot(dest: Path, bot: str | None, dials: str | None) -> tuple[str, dict]:
    """Write --bot / --dials (JSON inline or a file, or recipe names resolved for that bot) into the package's
    hyperion/ship.py; returns the (bot, dials) it now records."""
    ship = ship_module()
    path = dest / "hyperion" / "ship.py"
    name, have = ship.read_record(path)
    name = bot or name
    try:
        dials = have if dials is None else ship.parse_dials(dials, name)
    except (KeyError, ValueError) as e:
        raise SystemExit(f"FAIL --dials: {e}")
    if name not in ship.BUILDERS:
        raise SystemExit(f"FAIL --bot {name!r} is not in hyperion/ship.py BUILDERS ({', '.join(ship.BUILDERS)})")
    ship.write_record(path, name, dials)
    return name, dials


def _ignore(slim: bool):
    def ignore(d: str, names: list[str]) -> set[str]:
        skip = {n for n in names if n in SKIP_NAMES or n.endswith(".pyc")}
        if slim:
            here = Path(d).resolve()
            skip |= SLIM_SKIPS.get(here, set()) & set(names)
            if here == SLIM_RIVALS.resolve():
                skip |= {n for n in names if n.endswith(".py") and n not in SLIM_RIVALS_KEEP}
        return skip
    return ignore


def route_rivals(dest: Path, dials: dict) -> list[str]:
    """A slim package whose recorded route names a rival's donor (rival1, r2, ...): copy that rival back in. Returns
    the files copied."""
    import re

    rivals = dest / "hyperion" / "sim" / "rivals"
    if not rivals.is_dir():
        return []
    route = str((dials or {}).get("route", ""))
    want = {DONOR_RIVALS[d] for d in re.findall(r"=\s*(\w+)", route) if d in DONOR_RIVALS}
    out = []
    for f in sorted(want):
        if not (rivals / f).exists():
            shutil.copy2(SLIM_RIVALS / f, rivals / f)
            out.append(f)
    return out


RULES_KEYS = {"hole_cards", "board_sizes", "rank_order", "payouts", "blind_levels", "extras", "n_players"}


def find_rules(entry: Path, extras: list[Path], explicit: Path | None) -> Path | None:
    """The rules JSON the package plays: --rules, else the first --extra JSON with Rules keys, else
    rules_tonight.json beside the entry."""
    if explicit is not None:
        return explicit
    for x in extras:
        if x.is_file() and x.suffix == ".json":
            try:
                raw = json.loads(x.read_text())
            except (OSError, ValueError):
                continue
            if isinstance(raw, dict) and RULES_KEYS & set(raw):
                return x
    beside = entry.parent / "rules_tonight.json"
    return beside if beside.is_file() else None


def active_variant(rules_path: Path | None) -> tuple[str | None, bool]:
    """(extras["variant"], whether the card rules need a variant table set: more hole cards, removed ranks or
    must-use, the cases hyperion.strategy.tables.needs_variant_tables names)."""
    if rules_path is None:
        return None, False
    try:
        raw = json.loads(rules_path.read_text())
    except (OSError, ValueError) as e:
        raise SystemExit(f"FAIL rules {rules_path} unreadable: {e}")
    if not isinstance(raw, dict):
        return None, False
    ex = raw.get("extras") or {}
    needs = int(raw.get("hole_cards", 2) or 2) != 2 or bool(ex.get("removed_ranks")) or bool(raw.get("must_use_hole"))
    return (str(ex["variant"]) if ex.get("variant") else None), needs


def build(dest: Path, entry: Path, extras: list[Path], slim: bool, tables_dir: Path | None,
          variant: str | None = None, tables_root: Path | None = None, needs_variant: bool = False) -> str:
    """Write the package; returns a one-line description of the tables it carries."""
    tables_root = tables_root or ROOT / "tables"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ROOT / "hyperion", dest / "hyperion", ignore=_ignore(slim))
    if tables_dir is not None:
        shutil.copytree(tables_dir, dest / "tables", ignore=shutil.ignore_patterns("__pycache__"))
        what = f"all of {tables_dir} (--tables-dir)"
    else:
        (dest / "tables").mkdir()
        files = sorted(tables_root.glob("*.json"))
        if not files:
            raise SystemExit(f"no tables in {tables_root}; run tools/gen_tables.py first")
        for f in files:
            shutil.copy2(f, dest / "tables" / f.name)
        what = "default"
        if variant:
            vdir = tables_root / "variants" / variant
            if vdir.is_dir():
                shutil.copytree(vdir, dest / "tables" / "variants" / variant,
                                ignore=shutil.ignore_patterns("__pycache__"))
                what += f" + variants/{variant}"
            elif needs_variant:
                what += (f"; WARN the rules name variant {variant!r} and change the cards, but {vdir} does not "
                         f"exist: Hero plays label tables (Stage 3 writes tables/variants/<name>/)")
    shutil.copy2(entry, dest / entry.name)
    for x in extras:
        if x.is_dir():
            shutil.copytree(x, dest / x.name, ignore=_ignore(slim))
        else:
            shutil.copy2(x, dest / x.name)
    return what


def verify_import(dest: Path, module: str, budget_s: float, python: str = sys.executable) -> tuple[bool, str, float]:
    """(ok, detail, import seconds). Fresh interpreter, other cwd, no PYTHONPATH, dest first on sys.path; the
    recorded bot is built once after the import (its seconds are in the detail)."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    with tempfile.TemporaryDirectory() as elsewhere:
        t0 = time.perf_counter()
        try:
            proc = subprocess.run([python, "-I", "-B", "-c", _IMPORT_PROBE, str(dest), module], cwd=elsewhere, env=env,
                                  capture_output=True, text=True, timeout=max(30.0, budget_s * 4))
        except subprocess.TimeoutExpired:
            return False, f"import did not finish in {max(30.0, budget_s * 4):.0f} s", float("inf")
        wall = time.perf_counter() - t0
    if proc.returncode != 0:
        tail = (proc.stderr or proc.stdout).strip().splitlines()[-3:]
        return False, "import failed: " + " | ".join(tail), wall
    secs, build, where = proc.stdout.strip().splitlines()[-1].split(" ", 2)
    secs, build = float(secs), float(build)
    if where != "-" and not Path(where).resolve().is_relative_to(dest.resolve()):
        return False, f"hyperion resolved outside the package: {where}", secs
    if secs + max(0.0, build) > budget_s:
        return False, (f"import took {secs:.2f} s and the bot build {max(0.0, build):.2f} s, budget {budget_s:g} s "
                       f"(move work to the table-start hook)"), secs
    built = f"; bot built in {build:.2f} s" if build >= 0 else ""
    return True, (f"hyperion from {where}" if where != "-" else "entry does not import hyperion") + built, secs


def package_files(root: Path) -> list[Path]:
    """Every file to ship: no bytecode, even if a probe or an editor left some behind after the copy."""
    return sorted(p for p in root.rglob("*")
                  if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")


def tree_size(root: Path) -> tuple[int, int]:
    files = package_files(root)
    return sum(p.stat().st_size for p in files), len(files)


def make_zip(dest: Path, zip_path: Path) -> str:
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in package_files(dest):
            zf.write(p, p.relative_to(dest).as_posix())
    h = hashlib.sha256()
    with open(zip_path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def human(n: int) -> str:
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{n / 1e3:.0f} KB"


def minute_since_t0(text: str, now: datetime | None = None) -> str:
    """'T0: 18:00' (or 'T0 18:00:12') in NIGHT.md -> minutes since then; else the wall clock HH:MM."""
    now = now or datetime.now()
    m = re.search(r"\bT0\b[:\s]+(\d{1,2}):(\d{2})", text)
    if not m:
        return now.strftime("%H:%M")
    t0 = now.replace(hour=int(m.group(1)), minute=int(m.group(2)), second=0, microsecond=0)
    return str(int(((now - t0).total_seconds() % 86400) // 60))


SUBMISSIONS_HEADER = ["| minute | file | sha256 | size / import | what changed | verified by |",
                      "|---|---|---|---|---|---|"]


def append_night_row(night: Path, row: str) -> None:
    """Insert `row` at the end of the table under '## Submissions', creating heading and table if absent."""
    lines = night.read_text().splitlines()
    heads = [i for i, line in enumerate(lines) if line.strip().lower().startswith("## submissions")]
    if not heads:
        lines += ["", "## Submissions", "", *SUBMISSIONS_HEADER, row]
    else:
        start = heads[0] + 1
        end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
        table = [i for i in range(start, end) if lines[i].lstrip().startswith("|")]
        if table:
            lines.insert(table[-1] + 1, row)
        else:
            lines[start:start] = ["", *SUBMISSIONS_HEADER, row]
    night.write_text("\n".join(lines) + "\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--entry", required=True, help="the kit's entry file; copied to the top of the package")
    p.add_argument("--out", default="dist", help="output directory (default dist/)")
    p.add_argument("--extra", nargs="*", default=[], help="files or directories to copy beside the entry")
    p.add_argument("--bot", help="the bot to record in the package (default hyperion/ship.py's SHIP): hybrid3_x, "
                                 "hero, cheap (Stage 2's Hero.cheap()) or any BUILDERS name")
    p.add_argument("--dials", help="dials to record: a JSON object (inline or a file) or recipe names such as "
                                   "survival (default hyperion/ship.py's DIALS)")
    p.add_argument("--slim", action="store_true", help="drop drills/fakekits, the sim bestiary and the simulator's "
                                                        "opponents (sim/field, sim/aware.py, every rival but rival 3)")
    p.add_argument("--rules", help="the rules JSON whose extras.variant picks tables/variants/<name>/ (default: "
                                   "the first --extra JSON with Rules keys, else rules_tonight.json beside the entry)")
    p.add_argument("--tables-dir", help="override: package this whole directory as tables/ (default: tables/*.json "
                                        "plus the active variant's set)")
    p.add_argument("--name", default="submission", help="package directory and zip base name")
    p.add_argument("--note", default="", help="'what changed' for the NIGHT.md row")
    p.add_argument("--night", default="NIGHT.md", help="log file; a row is appended only if it exists")
    p.add_argument("--import-budget", type=float, default=5.0, help="seconds (default 5)")
    p.add_argument("--max-mb", type=float, default=100.0)
    a = p.parse_args(argv)

    entry = Path(a.entry).resolve()
    if not entry.is_file():
        print(f"FAIL entry not found: {entry}")
        return 1
    extras = [Path(x).resolve() for x in a.extra]
    missing = [x for x in extras if not x.exists()]
    if missing:
        print(f"FAIL --extra not found: {missing}")
        return 1
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    dest = out / a.name
    tables_dir = Path(a.tables_dir).resolve() if a.tables_dir else None
    rules_path = find_rules(entry, extras, Path(a.rules).resolve() if a.rules else None)
    variant, needs = active_variant(rules_path)
    tables = build(dest, entry, extras, a.slim, tables_dir, variant, needs_variant=needs)
    bot, dials = record_bot(dest, a.bot, a.dials)
    if a.slim:
        back = route_rivals(dest, dials)
        if back:
            print(f"slim     the route names {', '.join(back)}: kept")

    ok, detail, secs = verify_import(dest, entry.stem, a.import_budget)
    size, count = tree_size(dest)
    print(f"package  {dest}  ({count} files, {human(size)})")
    print(f"bot      {bot}  dials {dials}  (recorded in the package's hyperion/ship.py; the gate pairs against it)")
    print(f"tables   {tables}  (rules {rules_path or 'none found'})")
    print(f"import   {'ok' if ok else 'FAIL'} {secs:.2f} s  {detail}")
    if not ok:
        return 1
    if size > a.max_mb * 1e6:
        print(f"FAIL package is {human(size)}, limit {a.max_mb:g} MB")
        return 1
    zip_path = out / f"{a.name}.zip"
    sha = make_zip(dest, zip_path)
    zsize = zip_path.stat().st_size
    if zsize > a.max_mb * 1e6:
        print(f"FAIL zip is {human(zsize)}, limit {a.max_mb:g} MB")
        return 1
    print(f"zip      {zip_path}  {human(zsize)}")
    print(f"sha256   {sha}")
    night = Path(a.night)
    if night.is_file():
        minute = minute_since_t0(night.read_text())
        what = f"{bot}{' ' + json.dumps(dials) if dials else ''}: {a.note}" if a.note else f"{bot}{' ' + json.dumps(dials) if dials else ''}"
        row = f"| {minute} | {zip_path.name} | {sha} | {human(zsize)} / import {secs:.2f} s | {what} | |"
        append_night_row(night, row)
        print(f"NIGHT.md row appended under Submissions (minute {minute})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
