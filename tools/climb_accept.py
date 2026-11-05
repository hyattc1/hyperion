#!/usr/bin/env python
"""The climb's acceptance check (docs/drills/goal-plan.md, section 2): one command that measures a candidate against
the current ship on the frozen protocol's seeds and fields, and prints the verdict.

    .venv/bin/python tools/climb_accept.py --cand '{"dials": {"exploit.bet_min_fold": 0.35}}' --set H1
    .venv/bin/python tools/climb_accept.py --cand cand.json --base '{"bot": "hybrid3_x"}' --set screen --stages confirm
    .venv/bin/python tools/climb_accept.py --cand ... --set judge --stages judges
    .venv/bin/python tools/climb_accept.py --stages window --base dead_seats --cand dead_seats+survival \
        --rules submission/rules_tonight.json [--variant NAME] --workers 4          (a window, prompt 06)
    .venv/bin/python tools/climb_accept.py --stages window --base '' --cand '' --rules ... (at the freeze: F cached,
        so the first window plays only its candidate)

Specs are {"bot": NAME} for a registered bot, or {"dials": {...}}: the composite with these dials ON TOP OF the shipped
SHIP_DIALS, as hyperion.ship builds it, so {"dials": {}} is the shipped F (the default base). Note: tools/swap.py
paired takes a spec's dials alone, without SHIP_DIALS; there {"dials": {}} is not F. A spec may also be recipe names
(`survival`, `dead_seats+survival`; hyperion/ship.py resolves them for the composite) or '' (F as shipped).

Sets: `screen` 10000-10199; `H1` 20000-20399, `H2` 21000-21399, ... (+1000 each; H11 on skip the judge set: H11 is
31000-31399); `judge` 30000-30399; or `lo:hi`.
Stages (comma-separated; default confirm,guards,variants):
- confirm: night;
- guards: night_hard, realistic, top, night under payouts 10/7/5/4/3/2/1/0 and 50/25/12/6/3/2/1/1, night under a
  doubling blind schedule;
- variants: the catalogued entries (27 since tranche_holdem joined) on realistic, the set's first 200 seeds
  (`--variants NAME,...` and `--variant-seeds N` for some; a lone variant cell down prints REPLICATE: addendum 7
  re-runs it on the next set);
- elite: the tuning fields elite (elite1, elite2 and the strong tunable bots), elite_night (the two in a night room) and
  mirror (three copies of F, `f_copy`, with rival 2, elite1, elite2 and hybrid3_x: a table of near-equals, backlog S9);
  since the second wave also elite_b (elite's room with elite4 in agent_default's seat) and mirror_b (three copies of
  F with rival 2, elite4, elite1 and elite2);
- judges: judge, judge2, judge2_night, judge_top, outside, outside_strong, elite_judge, elite_judge_b (elite5, the
  second wave's held-out build; run these on `--set judge`).
- aware: the likeliest twists against variant-aware opponents, each field under its variant (toss_or_holdem_aware,
  bounty_aware, short_deck_aware, river_of_blood_aware, tranche_holdem_aware; hyperion/sim/aware.py); `--aware
  NAME,...` for some, and `--aware FIELD:VARIANT` for any field under any entry (realistic_keep2:deal5_keep2). `--aware generic:VARIANT` is
  the generic aware field (`generic_aware`: gen_mc, gen_tag, gen_pushfold, which read any variant's own hooks;
  hyperion/sim/generic.py) under that entry, `generic:all` under every catalog entry, and VARIANT may be a file
  (`generic:submission/tonight.py:variant`, a function returning a Variant). Each generic cell's table is built
  first if missing (about a minute for a new variant; tables/generic/).
- exploit: the S2 exploiter (`exploiter1`, docs/drills/exploiter/) at 8-max (`exploit`, payouts 10/7/5/4/3/2/1/0),
  heads-up (`exploit_hu`, rules hu.json: 10/7) and three-handed (`exploit_3`, three.json: 10/7/5), and the second
  exploiter (`exploiter2`, docs/drills/exploiter2/) in the same three formats (`exploit2`, `exploit2_hu`,
  `exploit2_3`), the third (`exploit3*`), and the adaptive opponent's tuning copy (`adapt1`, R6: `adapt`, `adapt_hu`,
  `adapt_3`; it learns each seat inside the table, tools/adapt_curve.py); the exploiter's own points are printed too. Part of the rule only with `--aim exploit` (addendum 6:
  an exploit field up, night not down); `--aim strong` is addendum 8 (elite, elite_night or mirror up, night not down).
- timing: tools/latency.py p99 for both specs (20,000 calls).
- window: night alone, the check a window needs (prompt 06): the candidate not beyond noise down. With --rules (the
  night's rules JSON: payouts, blinds, antes ...) and --variant (a catalog entry's hooks) it plays tonight's game;
  both also apply to confirm, guards and elite cells (a guard's own payouts or schedule still wins there).

After the verdict, every run prints addendum 11's weighted score (tools/accept_weights.json, tools/accept_weighted.py):
the weighted mean in night points, its family-block lower bound under the base weights and under W-min (the worst
corner of the plausible weights), the cap check and the cells missing; `--identical holdem|twists|NAME,...` counts
cells identical by construction as 0 +- 0. It decides nothing in the verdict. `--route2` adds route 2's own verdict
for a candidate the main rule rejects; it refuses unless the set is held out (H<k>) and every stage ran
(confirm,guards,elite,exploit,variants,aware), and reads the judges from `--judges-json` (the judge-set run).
`--json` holds both under "weighted" and "route2".
Late tables (`--late`, S18): every cell also records, per table played, who still had chips LATE (50) hands before
the cap (hand 150 of 200). `--late` prints, for the confirm, guards, elite and window cells, each spec's points and
bust rate on the tables that reached that hand with three or more players alive, and the paired difference on the
base's late tables (the same deals; 95% interval clustered by seed).

Every run is model mode at fixed speed, eight rotations per seed, the same deals for both specs, with panic, soft
deadlines and `late_us` off (tools/swap.py's setup_process), so it replays exactly. The unit is one table seed; the
interval is the 95% interval of the per-seed paired difference. UP / DOWN = beyond noise.

Results are cached per (spec, code version, field, rules, variant, seed chunk) under --out, so the base of a batch runs
once. The code version is the tree of hyperion/ at HEAD plus a hash of uncommitted changes under hyperion/ and tools/.

--runout-term (R7, docs/drills/climb/r7-log.md; off by default): every cell is also scored with the all-in runout term
subtracted (tools/runout_term.py: each seat's ICM points on the post-hand stacks of the actual runout, minus their mean
over every runout the unseen cards could have made, at each hand whose last decision left board cards to come). The
verdict is then read on the corrected paired delta; the raw delta, the term's mean per spec (zero within noise: the
check that it is unbiased) and the raw / corrected interval ratio print beside it. Its cells are cached apart
(`.rt-<term version>.json`, raw samples included) and a term cell's raw samples must equal the plain cell's when that
is cached: the term never changes play.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from multiprocessing import Pool

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [p for p in sys.path if os.path.abspath(p or os.curdir) != _HERE]
sys.path.insert(0, ROOT)

_spec = importlib.util.spec_from_file_location("climb_swap_tool", os.path.join(_HERE, "swap.py"))
SW = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(SW)
_wspec = importlib.util.spec_from_file_location("climb_weighted_score", os.path.join(_HERE, "accept_weighted.py"))
WS = importlib.util.module_from_spec(_wspec)  # addendum 11's weighted score (tools/accept_weights.json)
_wspec.loader.exec_module(WS)
_spec = importlib.util.spec_from_file_location("climb_runout_term", os.path.join(_HERE, "runout_term.py"))
RT = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(RT)

RULES_DIR = os.path.join(ROOT, "docs", "drills", "climb", "rules")
CONFIRM = [("night", "lin", None)]
GUARDS = [("night_hard", "lin", None), ("realistic", "lin", None), ("top", "lin", None), ("night", "brief", None),
          ("night", "th", None), ("night", "lin", "double")]
JUDGES = [("judge", "lin", None), ("judge2", "lin", None), ("judge2_night", "lin", None), ("judge_top", "lin", None),
          ("outside", "lin", None), ("outside_strong", "lin", None), ("elite_judge", "lin", None),
          ("elite_judge_b", "lin", None),  # elite5 held out (second wave, 2026-11-02)
          ("adapt_judge", "brief", None), ("adapt_judge_hu", "lin", "hu"), ("adapt_judge_3", "lin", "three"),  # adapt2
          ("outside_b", "lin", None),  # the outside judges' second wave (addendum 10)
          ("outside_c", "lin", None)]  # the third wave (addendum 14): out_reads
ELITE = [("elite", "lin", None), ("elite_night", "lin", None), ("mirror", "lin", None),
         ("elite_b", "lin", None), ("mirror_b", "lin", None)]  # elite4 joined 2026-11-02 (second wave)
EXPLOIT = [("exploit", "brief", None), ("exploit_hu", "lin", "hu"), ("exploit_3", "lin", "three"),
           ("exploit2", "brief", None), ("exploit2_hu", "lin", "hu"), ("exploit2_3", "lin", "three"),
           ("exploit3", "brief", None), ("exploit3_hu", "lin", "hu"), ("exploit3_3", "lin", "three"),  # of batch 5
           ("exploit4", "brief", None), ("exploit4_hu", "lin", "hu"), ("exploit4_3", "lin", "three"),  # of batch 7
           ("adapt", "brief", None), ("adapt_hu", "lin", "hu"), ("adapt_3", "lin", "three")]  # R6, addendum 9
EXPLOIT_BOTS = ("exploiter1", "exploiter2", "exploiter3", "exploiter4", "adapt1", "adapt2")  # the one seated in a cell is printed beside us
VARIANT_FIELD = "realistic"
VARIANT_SEEDS = 200
CHUNK = 25
LATE = 50  # the late-table report's checkpoint: this many hands before the cap (hand 150 of 200)


def seed_range(name: str) -> tuple[int, int]:
    if ":" in name:
        lo, hi = (int(x) for x in name.split(":"))
        return lo, hi
    if name == "screen":
        return 10000, 10200
    if name == "judge":
        return 30000, 30400
    if name.upper().startswith("H") and name[1:].isdigit():
        k = int(name[1:])
        lo = 20000 + 1000 * (k - 1)
        if lo >= 30000:  # H11 would be the judge set (30000-30399): held-out sets from H11 on start at 31000
            lo += 1000
        return lo, lo + 400
    raise SystemExit(f"unknown set {name!r}")


def _record_line(line: bytes) -> bool:
    """A changed line of hyperion/ship.py's record (SHIP = ..., DIALS: dict = ...), which `python -m hyperion.ship --set`
    rewrites in every window: specs here name their dials, so the record never changes what a cell plays."""
    return line[:1] in (b"+", b"-") and line[1:].startswith((b"SHIP = ", b"DIALS: dict = ", b"DIALS = "))


def code_version() -> str:
    """The tree hash of hyperion/ and the blob of tools/swap.py at HEAD (so a docs-only commit keeps the cache), plus a
    hash of any uncommitted change under hyperion/ and tools/ (changed lines only, the switch's record lines left out,
    so a window's `--set` keeps the cache of the windows before it)."""
    trees = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD:hyperion", "HEAD:tools/swap.py"], capture_output=True,
                           text=True).stdout.split()
    head = hashlib.md5(" ".join(trees).encode()).hexdigest()
    raw = subprocess.run(["git", "-C", ROOT, "diff", "-U0", "HEAD", "--", "hyperion", "tools"],
                         capture_output=True).stdout
    diff = b"\n".join(ln for ln in raw.splitlines()
                      if ln[:1] in (b"+", b"-") and not ln.startswith((b"+++", b"---")) and not _record_line(ln))
    untracked = subprocess.run(["git", "-C", ROOT, "ls-files", "--others", "--exclude-standard", "hyperion"],
                               capture_output=True, text=True).stdout
    blobs = hashlib.md5()  # an untracked module's content, not just its name (an edit to it must miss the cache)
    for name in untracked.split():
        try:
            with open(os.path.join(ROOT, name), "rb") as fh:
                blobs.update(name.encode() + b"\0" + fh.read())
        except OSError:
            pass
    h = hashlib.md5(diff + untracked.encode() + blobs.digest()).hexdigest()[:8]
    return f"{head[:10]}-{h}" if diff or untracked else head[:10]


def spec_key(spec: dict, version: str) -> str:
    return hashlib.md5((json.dumps(spec, sort_keys=True) + version).encode()).hexdigest()[:12]


def load_spec(s: str) -> dict:
    """A spec: JSON inline or in a file, or recipe names for the composite (`survival+passive`; '' = F as shipped)."""
    if os.path.exists(s):
        with open(s) as fh:
            return json.load(fh)
    t = s.strip()
    if t.startswith("{"):
        return json.loads(t)
    from hyperion import ship

    return {"dials": ship.recipe(t, "composite") if t else {}}


def resolve(spec: dict) -> dict:
    """A dials spec on top of the shipped dials, as hyperion.compose.bot.ship() builds it: {"dials": {}} is F. (tools/swap.py
    passes a spec's dials to parse_dials alone, so there {"dials": {}} is the composite without the shipped dials.)"""
    if "dials" not in spec:
        return dict(spec)
    from hyperion.compose import bot as CB

    dials = dict(spec["dials"])
    base = dict(CB.SHIP_DIALS)
    if "exploit" in dials and dials["exploit"] is None:
        base = {k: v for k, v in base.items() if not k.startswith("exploit.")}
    return {**{k: v for k, v in spec.items() if k != "dials"}, "dials": {**base, **dials}}


def _rules_file(rules_name: str) -> str:
    """A cell's rules: a name in docs/drills/climb/rules, or a path to a Rules JSON (--rules, the night's file)."""
    return rules_name if os.sep in rules_name or rules_name.endswith(".json") else os.path.join(RULES_DIR,
                                                                                                 rules_name + ".json")


def _rules(pay: str, rules_name):
    from hyperion.core.types import Rules

    kw = {}
    if rules_name:
        with open(_rules_file(rules_name)) as fh:
            extra = json.load(fh)
        kw.update({k: tuple(tuple(x) if isinstance(x, list) else x for x in v) if isinstance(v, list) else v
                   for k, v in extra.items()})
    if SW.PAYOUTS[pay]:  # a guard's payout table wins over a rules file's
        kw["payouts"] = SW.PAYOUTS[pay]
    return Rules(**kw) if kw else None


def _rules_tag(rules_name) -> str:
    if not rules_name:
        return "-"
    if os.sep in rules_name or rules_name.endswith(".json"):  # a file: its content names the cell
        with open(rules_name, "rb") as fh:
            return "f" + hashlib.md5(fh.read()).hexdigest()[:10]
    return rules_name


def _job(args):
    key, name, spec, field, pay, rules_name, variant, off, n = args[:9]
    rt = len(args) > 9 and args[9]
    SW.setup_process("model")
    from hyperion.compose import bot as CB
    from hyperion.drills import variants as V
    from hyperion.sim import bestiary as B
    from hyperion.sim.runner import run_tournament

    CB.COUNTS.clear()
    nm = SW._spec_bot(name, spec)
    rules = _rules(pay, rules_name)
    v = V.get(variant, seed=SW.SEED) if variant else None
    from hyperion.core.types import Rules

    cap = (rules if rules is not None else v.rules if v is not None else Rules()).max_hands
    t0 = time.time()
    l0 = os.getloadavg()[0]
    kw = dict(seed=SW.SEED, rotate=True, mode="model", rules=rules, hero_config=B.HERO_CONFIG, table_offset=off,
              variant=v)
    names = B.field_names(f"{field}@{nm}")
    if rt:  # addendum 13's runout term; the late-table records (S18) need the plain runner, so a term run keeps none
        rep, corrected, events = RT.run_tournament_rt(names, n, **kw)
    else:
        rep = run_tournament(names, n, late_at=max(0, cap - LATE), **kw)
    b = rep.bots[nm]
    st = b.stats
    ex = next((rep.bots[x] for x in EXPLOIT_BOTS if x in rep.bots), None)
    res = {"samples": b.samples, "opp_samples": ex.samples if ex is not None else None, "tmo": st.over_budget,
           "exc": st.exceptions, "ill": st.illegal,
           "safe_err": st.safe_err, "calls": st.calls, "p50": st.percentile_us(0.5), "p99": st.percentile_us(0.99),
           "max_us": st.max_ns / 1000, "secs": time.time() - t0, "load": (l0, os.getloadavg()[0])}
    if not rt:
        res["late"] = [[t, rot, alive, [list(x) for x in per.get(nm, [])]] for t, rot, alive, per in rep.late]
    if rt:  # the corrected samples, and the term's events touching our seats per table seed (8 rotations)
        res.update({"samples_rt": corrected[nm], "rt_events": events[nm], "rt_version": RT.version(),
                    "opp_samples_rt": corrected[ex.name] if ex is not None else None})
    return key, (field, pay, rules_name, variant, off), res


def _variant_tag(variant) -> str:
    """A cell's variant in a file name: a catalog name as is, a file spec (path.py:factory) by its content."""
    if not variant:
        return "-"
    if ".py" not in variant:
        return variant
    path, _, func = variant.rpartition(":") if ".py:" in variant else (variant, "", "")
    with open(path, "rb") as fh:
        return "v" + hashlib.md5(fh.read() + func.encode()).hexdigest()[:10]


def cell_path(out: str, key: str, cell, n: int = CHUNK, rt: bool = False) -> str:
    """A chunk's cache file. A chunk of fewer than CHUNK seeds (a set's last, e.g. 10025-10039 of 10000:10040) is named
    with its length: before H6 it shared the full chunk's name, and a later run over more seeds read its 15 samples
    as the chunk's 25 (drill 10's H6 found a 200-seed screen run that had played 190). With the runout term (addendum
    13) its own file, tagged by the term's version (tools/runout_term.py)."""
    field, pay, rules_name, variant, off = cell
    tail = ("" if n == CHUNK else f".n{n}") + (f".rt-{RT.version()}" if rt else "")
    return os.path.join(out, key, f"{field}.{pay}.{_rules_tag(rules_name)}.{_variant_tag(variant)}.{off}{tail}.json")


def _check_rt_raw(path: str, res: dict) -> None:
    """A term cell's raw samples against the plain cell of the same key, when cached: the term never changes play."""
    plain = path.rsplit(".rt-", 1)[0] + ".json"
    if os.path.exists(plain):
        with open(plain) as fh:
            if json.load(fh)["samples"] != res["samples"]:
                raise RuntimeError(f"runout term: raw samples differ from the plain cell {plain}")


def run_cells(out: str, specs: dict, cells: list, lo: int, hi: int, workers: int, rt: bool = False) -> None:
    """Run every (spec, cell, chunk) not yet cached."""
    jobs, seen = [], set()
    for name, (key, spec) in specs.items():
        for field, pay, rules_name, variant in cells:
            for off in range(lo, hi, CHUNK):
                n = min(CHUNK, hi - off)
                p = cell_path(out, key, (field, pay, rules_name, variant, off), n, rt)
                if not os.path.exists(p) and p not in seen:  # base == cand (warming the cache) runs once
                    seen.add(p)
                    jobs.append((key, name, spec, field, pay, rules_name, variant, off, n, rt))
    if not jobs:
        return
    for name, (key, spec) in specs.items():
        os.makedirs(os.path.join(out, key), exist_ok=True)
        with open(os.path.join(out, key, "spec.json"), "w") as fh:
            json.dump({"name": name, "spec": spec}, fh)
    # maxtasksperchild: a worker that played many variants holds every one's tables and evaluator caches (2.7 GB per
    # process was seen with 25 variants), so each worker is replaced after two jobs; finished chunks are cached anyway
    with Pool(workers, maxtasksperchild=2) as p:
        for key, cell, res in p.imap_unordered(_job, jobs):
            path = cell_path(out, key, cell, len(res["samples"]), rt)  # one sample a table seed: the chunk's length
            if rt:
                _check_rt_raw(path, res)
            with open(path + ".tmp", "w") as fh:
                json.dump(res, fh)
            os.replace(path + ".tmp", path)


def gather(out: str, key: str, cell4, lo: int, hi: int, rt: bool = False) -> dict:
    field, pay, rules_name, variant = cell4
    samples, opp, agg = [], [], {"tmo": 0, "exc": 0, "ill": 0, "safe_err": 0, "calls": 0, "p99": 0.0, "max_us": 0.0}
    srt, ev = [], []
    for off in range(lo, hi, CHUNK):
        with open(cell_path(out, key, (field, pay, rules_name, variant, off), min(CHUNK, hi - off), rt)) as fh:
            r = json.load(fh)
        samples += r["samples"]
        opp += r.get("opp_samples") or []
        if rt:
            srt += r["samples_rt"]
            ev += r["rt_events"]
        for k in ("tmo", "exc", "ill", "safe_err", "calls"):
            agg[k] += r[k]
        agg["p99"] = max(agg["p99"], r["p99"])
        agg["max_us"] = max(agg["max_us"], r["max_us"])
    agg["samples"] = samples
    agg["mean"] = sum(samples) / len(samples)
    agg["opp_mean"] = sum(opp) / len(opp) if opp else None
    if rt:
        agg["samples_raw"], agg["samples"] = samples, srt  # the verdict reads the corrected samples
        agg["mean_raw"], agg["mean"] = agg["mean"], sum(srt) / len(srt)
        agg["rt_events"] = sum(ev) / len(ev)
    return agg


def gather_late(out: str, key: str, cell4, lo: int, hi: int) -> dict | None:
    """The cell's late-table records, {(table, rotation): (alive at the checkpoint, [(points, alive then, survived)
    per seat of the spec])}; None if a chunk was cached before the records were kept."""
    field, pay, rules_name, variant = cell4
    recs = {}
    for off in range(lo, hi, CHUNK):
        path = cell_path(out, key, (field, pay, rules_name, variant, off), min(CHUNK, hi - off))
        if not os.path.exists(path):  # a runout-term run keeps no late records (addendum 13)
            return None
        with open(path) as fh:
            r = json.load(fh)
        if "late" not in r:
            return None
        for t, rot, alive, seats in r["late"]:
            recs[(t, rot)] = (alive, seats)
    return recs


def _cluster_mean(vals: list) -> tuple[float, float, int]:
    """(mean, 95% half-width, n) of [(cluster, x)]: the mean over every x, its interval clustered by seed."""
    n = len(vals)
    if n == 0:
        return float("nan"), float("nan"), 0
    m = sum(x for _, x in vals) / n
    by: dict = {}
    for c, x in vals:
        by[c] = by.get(c, 0.0) + (x - m)
    g = len(by)
    v = sum(e * e for e in by.values()) / (n * n) * (g / (g - 1)) if g > 1 else 0.0
    return m, 1.96 * math.sqrt(v), n


def late_rows(recs: dict, base_recs: dict | None = None) -> dict:
    """A spec's late-table numbers: tables that reached the checkpoint with three or more alive; on them the spec's
    points (mean over its seats), bust rate, share alive at the checkpoint and busts after it given alive; with
    `base_recs`, the paired difference on the base's late tables."""
    late = [(k, a, seats) for k, (a, seats) in recs.items() if a >= 3 and seats]
    pts = [(k[0], sum(x[0] for x in seats) / len(seats)) for k, a, seats in late]
    seat_rows = [x for _, _, seats in late for x in seats]
    alive = [x for x in seat_rows if x[1]]
    out = {"tables": len(recs), "late": len(late), "pts": _cluster_mean(pts),
           "bust": sum(1 for x in seat_rows if not x[2]) / len(seat_rows) if seat_rows else float("nan"),
           "alive": len(alive) / len(seat_rows) if seat_rows else float("nan"),
           "bust_after": sum(1 for x in alive if not x[2]) / len(alive) if alive else float("nan")}
    if base_recs is not None:
        d = []
        for k, (a, seats) in base_recs.items():
            if a >= 3 and seats and k in recs and recs[k][1]:
                mine = recs[k][1]
                d.append((k[0], sum(x[0] for x in mine) / len(mine) - sum(x[0] for x in seats) / len(seats)))
        out["paired"] = _cluster_mean(d)
    return out
def term_mean(g: dict) -> tuple[float, float]:
    """The runout term's mean per table seed for one spec (raw - corrected) and its 95% interval: zero within noise."""
    return paired(g["samples"], g["samples_raw"])


def paired(a: list, b: list) -> tuple[float, float]:
    d = [y - x for x, y in zip(a, b)]
    n = len(d)
    m = sum(d) / n
    v = sum((x - m) ** 2 for x in d) / (n - 1) if n > 1 else 0.0
    return m, 1.96 * math.sqrt(v / n)


def flag(m: float, h: float) -> str:
    return "UP" if m - h > 0 else ("DOWN" if m + h < 0 else "level")


def label(cell4) -> str:
    field, pay, rules_name, variant = cell4
    s = field
    if pay != "lin":
        s += f" @{ {'brief': '10/7/5/4/3/2/1/0', 'th': '50/25/12/6/3/2/1/1'}.get(pay, pay)}"
    if rules_name:
        s += f" +{os.path.basename(rules_name)}"
    if variant:
        s = f"{variant} ({s})"
    return s


def latency(spec: dict) -> dict:
    if "bot" in spec:
        args = ["--bot", spec["bot"]]
    else:  # latency.py's `composite` is ship(): its dials go on top of SHIP_DIALS, so pass the resolved set (the same)
        args = ["--bot", "composite", "--dials", json.dumps(spec.get("dials", {}))]
    cmd = [sys.executable, os.path.join(_HERE, "latency.py"), *args, "--n", "20000", "--p99-us", "100000"]
    out = subprocess.run(cmd, capture_output=True, text=True, cwd=ROOT).stdout
    res = {"raw": out.strip().splitlines()[1] if len(out.strip().splitlines()) > 1 else out.strip()}
    for tok in ("p50", "p99", "max"):
        try:
            res[tok] = float(out.split(tok, 1)[1].split()[0])
        except (IndexError, ValueError):
            res[tok] = None
    return res


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cand", required=True, help="the candidate spec: JSON inline or a file, or recipe names")
    p.add_argument("--base", default='{"dials": {}}', help="the reference spec (default: the shipped composite F), "
                                                           "or recipe names ('' = F)")
    p.add_argument("--set", default=None, help="screen, H1, H2 ..., judge or lo:hi (default H1; screen for --stages "
                                                "window)")
    p.add_argument("--stages", default="confirm,guards,variants")
    p.add_argument("--workers", type=int, default=4)
    p.add_argument("--out", default=os.path.join(ROOT, "scratch", "climb"))
    p.add_argument("--json", default=None, help="also write the verdict as JSON here")
    p.add_argument("--aware", default=None, help="the aware stage's fields (default: every aware field), each FIELD "
                                                 "or FIELD:VARIANT")
    p.add_argument("--variants", default=None, help="the variants stage's entries (default: the whole catalog)")
    p.add_argument("--variant-seeds", type=int, default=VARIANT_SEEDS,
                   help="seeds per variant cell, from the set's first (addendum 7's replication: 400)")
    p.add_argument("--rules", default=None, help="a Rules JSON (the night's rules_tonight.json) for the window, "
                                                 "confirm, guards and elite cells")
    p.add_argument("--variant", default=None, help="a catalog variant's hooks for the same cells")
    p.add_argument("--late", action="store_true", help=f"print the late-table report (tables alive {LATE} hands "
                                                       "before the cap with three or more players) for the confirm, "
                                                       "guards, elite and window cells")
    p.add_argument("--runout-term", action="store_true",
                   help="score every cell with the all-in runout term subtracted (tools/runout_term.py): the verdict "
                        "reads the corrected delta; the raw delta, the term's mean per spec and the interval ratio "
                        "print beside it")
    p.add_argument("--aim", choices=("night", "exploit", "strong"), default="night",
                   help="what the change is for: night (confirm beyond noise up), exploit (addendum 6: an exploit "
                        "field up, night not down) or strong (addendum 8: elite, elite_night or mirror up, night "
                        "not down)")
    p.add_argument("--identical", default="", help="cells identical by construction for the weighted score "
                                                   "(addendum 11, 0 +- 0 where not run), comma-separated: holdem (a "
                                                   "change to twist tables only), twists (a change gated to hold'em "
                                                   "tables: the 22 variants off them), or variant names")
    p.add_argument("--route2", action="store_true", help="also apply addendum 11's route 2 to a candidate the main "
                                                         "rule rejects: a held-out set with every stage run only")
    p.add_argument("--judges-json", default=None, help="route 2's condition (c): the candidate's climb_accept "
                                                       "--json on --set judge --stages judges (same base and cand)")
    a = p.parse_args(argv)
    version = code_version()
    base_raw, cand_raw = load_spec(a.base), load_spec(a.cand)
    base, cand = resolve(base_raw), resolve(cand_raw)
    specs = {"base": (spec_key(base, version), base), "cand": (spec_key(cand, version), cand)}
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    a.set = a.set or ("screen" if stages == ["window"] else "H1")
    lo, hi = seed_range(a.set)
    identical = [t.strip() for t in a.identical.split(",") if t.strip()]
    if WS.unknown_identical(WS.load(), identical):
        raise SystemExit(f"--identical: unknown {', '.join(WS.unknown_identical(WS.load(), identical))} (holdem, "
                         f"twists or a catalogue variant)")
    judges_rows = None
    if a.route2:  # addendum 11: route 2 only on a fresh held-out set with every stage run; refuse before any play
        why = WS.route2_refusal(a.set, stages, a.variants, a.variant_seeds, a.rules, a.variant)
        if a.judges_json:
            with open(a.judges_json) as fh:
                jv = json.load(fh)
            if "judges" not in jv.get("stages", {}):
                why = "; ".join(filter(None, [why, f"{a.judges_json} has no judges stage"]))
            elif [jv.get("base"), jv.get("cand")] != json.loads(json.dumps([base, cand])):
                why = "; ".join(filter(None, [why, f"{a.judges_json} is another base or candidate"]))
            else:
                judges_rows = jv["stages"]["judges"]
        if why:
            raise SystemExit(f"--route2 refuses: {why}")
    rt = a.runout_term
    rows, verdict = [], {"version": version, "set": a.set, "seeds": [lo, hi], "base": base, "cand": cand,
                         "stages": {}, "runout_term": RT.version() if rt else None}
    t0 = time.time()
    from hyperion.drills import variants as V

    rules_path = os.path.abspath(a.rules) if a.rules else None
    if a.variant:
        V.get(a.variant)  # an unknown name fails here, not in a worker

    def tonight(cells):  # the night's rules and variant on a stage's cells (a cell's own rules or variant wins)
        return [(f, pay, rn if rn else rules_path, *(c[3:] if len(c) > 3 else (a.variant,)))
                for c in cells for f, pay, rn in [c[:3]]]

    plan = []
    if "window" in stages:
        plan.append(("window", tonight(CONFIRM), lo, hi))
    if "confirm" in stages:
        plan.append(("confirm", tonight(CONFIRM), lo, hi))
    if "guards" in stages:
        plan.append(("guards", tonight(GUARDS), lo, hi))
    if "elite" in stages:
        plan.append(("elite", tonight(ELITE), lo, hi))
    if "judges" in stages:
        plan.append(("judges", JUDGES, lo, hi))
    if "aware" in stages:
        from hyperion.sim import aware as AW

        names = a.aware.split(",") if a.aware else list(AW.AWARE_FIELDS)
        # FIELD (an aware field, under its variant) or FIELD:VARIANT (any field under any catalog entry, e.g.
        # realistic_keep2:deal5_keep2); generic:VARIANT / generic:all is the generic aware field (module doc)
        pairs = []
        for n in names:
            f, v = n.split(":", 1) if ":" in n else (n, AW.AWARE_VARIANT[n])
            if f == "generic":
                f = "generic_aware"
            pairs += [(f, x) for x in (V.catalog_names() if v == "all" else [v])]
        if any(f == "generic_aware" for f, _ in pairs):
            from hyperion.sim import generic as GEN

            for f, v in pairs:
                if f == "generic_aware":
                    t1 = time.time()
                    path, _doc = GEN.prepare(v, workers=a.workers)
                    print(f"generic table for {v}: {os.path.relpath(path, ROOT)} ({time.time() - t1:.1f} s)",
                          flush=True)
        plan.append(("aware", [(f, "lin", None, v) for f, v in pairs], lo, hi))
    if "exploit" in stages:
        plan.append(("exploit", EXPLOIT, lo, hi))
    if "variants" in stages:
        names = a.variants.split(",") if a.variants else V.catalog_names()
        plan.append(("variants", [(VARIANT_FIELD, "lin", None, v) for v in names], lo,
                     min(hi, lo + a.variant_seeds)))
    for stage, cells, s_lo, s_hi in plan:
        cells4 = [c if len(c) == 4 else (*c, None) for c in cells]
        run_cells(a.out, specs, cells4, s_lo, s_hi, a.workers, rt)
        out = []
        for c in cells4:
            gb = gather(a.out, specs["base"][0], c, s_lo, s_hi, rt)
            gc_ = gather(a.out, specs["cand"][0], c, s_lo, s_hi, rt)
            m, h = paired(gb["samples"], gc_["samples"])
            row = {"cell": label(c), "base": gb["mean"], "cand": gc_["mean"], "delta": m, "ci": h,
                   "flag": flag(m, h), "n": len(gb["samples"]), "tmo": (gb["tmo"], gc_["tmo"]),
                   "exc": (gb["exc"] + gb["ill"] + gb["safe_err"], gc_["exc"] + gc_["ill"] + gc_["safe_err"]),
                   "p99": (gb["p99"], gc_["p99"]), "opp": (gb["opp_mean"], gc_["opp_mean"])}
            if rt:
                mr, hr = paired(gb["samples_raw"], gc_["samples_raw"])
                tb = [x - y for x, y in zip(gb["samples_raw"], gb["samples"])]
                tc = [x - y for x, y in zip(gc_["samples_raw"], gc_["samples"])]
                row.update({"raw_base": gb["mean_raw"], "raw_cand": gc_["mean_raw"], "raw_delta": mr, "raw_ci": hr,
                            "raw_flag": flag(mr, hr), "term_base": term_mean(gb), "term_cand": term_mean(gc_),
                            "term_delta": paired(tb, tc),
                            "ratio": hr / h if h > 0 else None,
                            "events": (gb["rt_events"], gc_["rt_events"])})
            out.append(row)
        verdict["stages"][stage] = out
        if a.late and stage in ("window", "confirm", "guards", "elite"):
            rows_l = []
            for c in cells4:
                rb = gather_late(a.out, specs["base"][0], c, s_lo, s_hi)
                rc = gather_late(a.out, specs["cand"][0], c, s_lo, s_hi)
                if rb is None or rc is None:
                    rows_l.append({"cell": label(c), "missing": True})
                    continue
                rows_l.append({"cell": label(c), "base": late_rows(rb), "cand": late_rows(rc, rb)})
            verdict.setdefault("late", {})[stage] = rows_l
    if "timing" in stages:
        verdict["stages"]["timing"] = {"base": latency(base), "cand": latency(cand)}
    # the protocol's rule
    st = verdict["stages"]
    checks = []
    if "window" in st:
        checks.append(("window: night not beyond noise down (a recipe answers the standings; it need not gain)",
                       all(r["flag"] != "DOWN" for r in st["window"])))
    if "confirm" in st:
        if a.aim == "night":
            checks.append(("confirm: night beyond noise up", all(r["flag"] == "UP" for r in st["confirm"])))
        else:
            checks.append(("confirm: night not beyond noise down", all(r["flag"] != "DOWN" for r in st["confirm"])))
    if a.aim == "exploit":  # addendum 6
        ups = [r["cell"] for r in st.get("exploit", []) if r["flag"] == "UP"]
        checks.append((f"exploit (addendum 6): an exploit field beyond noise up ({', '.join(ups) or 'none'})",
                       bool(ups)))
        downs = [r["cell"] for r in st.get("exploit", []) if r["flag"] == "DOWN"]
        checks.append((f"exploit: none beyond noise down" + (f" (down: {', '.join(downs)})" if downs else ""),
                       not downs))
    if a.aim == "strong":  # addendum 8
        ups = [r["cell"] for r in st.get("elite", []) if r["flag"] == "UP"]
        checks.append((f"elite (addendum 8): a strong field beyond noise up ({', '.join(ups) or 'none'})", bool(ups)))
    # the exploit stage counts under every aim when it runs: a loss to a bot built to beat F is a loss (S14 found
    # --aim strong printing ACCEPT with exploit cells down; no accepted batch had one)
    for s in ("guards", "elite", "variants", "judges", "aware") + (() if a.aim == "exploit" else ("exploit",)):
        if s in st:
            downs = [r["cell"] for r in st[s] if r["flag"] == "DOWN"]
            checks.append((f"{s}: none beyond noise down" + (f" (down: {', '.join(downs)})" if downs else ""),
                           not downs))
    if "timing" in st:
        p99 = st["timing"]["cand"].get("p99")
        checks.append((f"timing: latency.py p99 {p99} us <= 200", p99 is not None and p99 <= 200))
    verdict["checks"] = checks
    verdict["accept"] = all(ok for _, ok in checks) if checks else None
    # addendum 7: a lone variant cell down (with every other check passing) is not a reject yet: re-run that cell on
    # the next held-out set at 400 seeds; it rejects if the re-run, or both sets pooled, is beyond noise down
    vdowns = [r["cell"] for r in st.get("variants", []) if r["flag"] == "DOWN"]
    others_ok = all(ok for txt, ok in checks if not txt.startswith("variants:"))
    verdict["replicate"] = vdowns[0] if len(vdowns) == 1 and others_ok and not a.variants else None
    verdict["secs"] = time.time() - t0
    # print
    print(f"# climb_accept: set {a.set} ({lo}-{hi - 1}), code {version}, aim {a.aim}, {verdict['secs'] / 60:.1f} min")
    print(f"base {json.dumps(base_raw, sort_keys=True)} -> {json.dumps(base, sort_keys=True)}")
    print(f"cand {json.dumps(cand_raw, sort_keys=True)} -> {json.dumps(cand, sort_keys=True)}")
    if "exploit" in st:
        print("\n## exploit\n\n| cell | base | cand | cand - base | | n | exploiter b/c | p99 b/c |")
        print("|---|---|---|---|---|---|---|---|")
        for r in st["exploit"]:
            ob, oc = r["opp"]
            print(f"| {r['cell']} | {r['base']:.3f} | {r['cand']:.3f} | {r['delta']:+.3f} ± {r['ci']:.3f} | "
                  f"{r['flag']} | {r['n']} | {ob if ob is None else round(ob, 3)}/{oc if oc is None else round(oc, 3)} | "
                  f"{r['p99'][0]:.0f}/{r['p99'][1]:.0f} |")
    for s in ("window", "confirm", "guards", "elite", "judges", "variants", "aware"):
        if s not in st:
            continue
        print(f"\n## {s}\n\n| cell | base | cand | cand - base | | n | tmo b/c | err b/c | p99 b/c |")
        print("|---|---|---|---|---|---|---|---|---|")
        for r in st[s]:
            print(f"| {r['cell']} | {r['base']:.3f} | {r['cand']:.3f} | {r['delta']:+.3f} ± {r['ci']:.3f} | "
                  f"{r['flag']} | {r['n']} | {r['tmo'][0]}/{r['tmo'][1]} | {r['exc'][0]}/{r['exc'][1]} | "
                  f"{r['p99'][0]:.0f}/{r['p99'][1]:.0f} |")
    for s, rows_l in verdict.get("late", {}).items():
        print(f"\n## late tables: {s} (alive {LATE} hands before the cap with 3+ players)\n\n"
              "| cell | late tables b/c | pts on late tables b | c | bust b/c | alive then b/c | bust after b/c | "
              "c - b on base's late tables |")
        print("|---|---|---|---|---|---|---|---|")
        for r in rows_l:
            if r.get("missing"):
                print(f"| {r['cell']} | (chunks cached before the late records) | | | | | | |")
                continue
            b_, c_ = r["base"], r["cand"]
            pm, ph, _ = c_["paired"]
            print(f"| {r['cell']} | {b_['late']}/{c_['late']} of {b_['tables']} | {b_['pts'][0]:.3f} ± "
                  f"{b_['pts'][1]:.3f} | {c_['pts'][0]:.3f} ± {c_['pts'][1]:.3f} | {100 * b_['bust']:.1f}/"
                  f"{100 * c_['bust']:.1f}% | {100 * b_['alive']:.1f}/{100 * c_['alive']:.1f}% | "
                  f"{100 * b_['bust_after']:.1f}/{100 * c_['bust_after']:.1f}% | {pm:+.3f} ± {ph:.3f} "
                  f"{flag(pm, ph)} (n {c_['paired'][2]}) |")
    if rt:
        print("\n## runout term (the tables above are corrected)\n\n| cell | raw cand - base | | corrected | | ratio "
              "| term base | term cand | term c - b | events b/c |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for s in ("window", "confirm", "guards", "elite", "judges", "exploit", "variants", "aware"):
            for r in st.get(s, []):
                (tb, hb), (tc, hc), (td, hd) = r["term_base"], r["term_cand"], r["term_delta"]
                ratio = "-" if r["ratio"] is None else f"{r['ratio']:.2f}"
                print(f"| {r['cell']} | {r['raw_delta']:+.3f} ± {r['raw_ci']:.3f} | {r['raw_flag']} | "
                      f"{r['delta']:+.3f} ± {r['ci']:.3f} | {r['flag']} | {ratio} | {tb:+.3f} ± {hb:.3f} | "
                      f"{tc:+.3f} ± {hc:.3f} | {td:+.3f} ± {hd:.3f} | {r['events'][0]:.1f}/{r['events'][1]:.1f} |")
        print("\nterm = raw - corrected per table seed, each spec's and paired (term c - b = raw delta - corrected "
              "delta): zero within noise if unbiased; ratio = raw interval / corrected interval; events = term events "
              "touching our seats per table seed (8 rotations).")
    if "timing" in st:
        print(f"\n## timing\n- base: {st['timing']['base']['raw']}\n- cand: {st['timing']['cand']['raw']}")
    print("\n## verdict" + (" (on the corrected deltas)" if rt else ""))
    for txt, ok in checks:
        print(f"- [{'x' if ok else ' '}] {txt}")
    if verdict["replicate"]:
        print(f"\n**REPLICATE** {verdict['replicate']}: one variant cell down; addendum 7 re-runs it on the next "
              f"held-out set with --variants NAME --variant-seeds 400")
    else:
        print(f"\n**{'ACCEPT' if verdict['accept'] else 'REJECT'}**" if checks else "")
    # addendum 11: the weighted score beside the verdict; it decides nothing above (route 2 is its own verdict)
    ws = WS.score(st, identical)
    verdict["weighted"] = ws
    out_lines = WS.lines(ws)
    if a.rules or a.variant:
        out_lines.append("- note: cells under --rules/--variant are the night's game; the weights and units assume "
                         "the protocol's cells")
    print("\n".join(out_lines))
    if a.route2:
        verdict["route2"] = WS.route2(ws, verdict["accept"], judges_rows)
        print("\n".join(WS.route2_lines(verdict["route2"])))
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(verdict, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
