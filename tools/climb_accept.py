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

Sets: `screen` 10000-10199; `H1` 20000-20399, `H2` 21000-21399, ... (+1000 each); `judge` 30000-30399; or `lo:hi`.
Stages (comma-separated; default confirm,guards,variants):
- confirm: night;
- guards: night_hard, realistic, top, night under payouts 10/7/5/4/3/2/1/0 and 50/25/12/6/3/2/1/1, night under a
  doubling blind schedule;
- variants: the catalogued entries on realistic, the set's first 200 seeds (`--variants NAME,...` and
  `--variant-seeds N` for some; a lone variant cell down prints REPLICATE: addendum 7 re-runs it on the next set);
- elite: the tuning fields elite (elite1, elite2 and the strong tunable bots) and elite_night (the two in a night room);
- judges: judge, judge2, judge2_night, judge_top, outside, outside_strong, elite_judge (run these on `--set judge`).
- aware: the three likeliest twists against variant-aware opponents, each field under its variant
  (toss_or_holdem_aware, bounty_aware, short_deck_aware; hyperion/sim/aware.py); `--aware NAME,...` for some.
- exploit: the S2 exploiter (`exploiter1`, docs/drills/exploiter/) at 8-max (`exploit`, payouts 10/7/5/4/3/2/1/0),
  heads-up (`exploit_hu`, rules hu.json: 10/7) and three-handed (`exploit_3`, three.json: 10/7/5); its own points are
  printed too. Part of the rule only with `--aim exploit` (addendum 6: an exploit field up, night not down);
  `--aim strong` is addendum 8 (elite, elite_night or mirror up, night not down).
- timing: tools/latency.py p99 for both specs (20,000 calls).
- window: night alone, the check a window needs (prompt 06): the candidate not beyond noise down. With --rules (the
  night's rules JSON: payouts, blinds, antes ...) and --variant (a catalog entry's hooks) it plays tonight's game;
  both also apply to confirm, guards and elite cells (a guard's own payouts or schedule still wins there).

Every run is model mode at fixed speed, eight rotations per seed, the same deals for both specs, with panic, soft
deadlines and `late_us` off (tools/swap.py's setup_process), so it replays exactly. The unit is one table seed; the
interval is the 95% interval of the per-seed paired difference. UP / DOWN = beyond noise.

Results are cached per (spec, code version, field, rules, variant, seed chunk) under --out, so the base of a batch runs
once. The code version is the tree of hyperion/ at HEAD plus a hash of uncommitted changes under hyperion/ and tools/.
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

RULES_DIR = os.path.join(ROOT, "docs", "drills", "climb", "rules")
CONFIRM = [("night", "lin", None)]
GUARDS = [("night_hard", "lin", None), ("realistic", "lin", None), ("top", "lin", None), ("night", "brief", None),
          ("night", "th", None), ("night", "lin", "double")]
JUDGES = [("judge", "lin", None), ("judge2", "lin", None), ("judge2_night", "lin", None), ("judge_top", "lin", None),
          ("outside", "lin", None), ("outside_strong", "lin", None), ("elite_judge", "lin", None)]
ELITE = [("elite", "lin", None), ("elite_night", "lin", None)]
EXPLOIT = [("exploit", "brief", None), ("exploit_hu", "lin", "hu"), ("exploit_3", "lin", "three")]
EXPLOIT_BOT = "exploiter1"
VARIANT_FIELD = "realistic"
VARIANT_SEEDS = 200
CHUNK = 25


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
    h = hashlib.md5(diff + untracked.encode()).hexdigest()[:8]
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
    key, name, spec, field, pay, rules_name, variant, off, n = args
    SW.setup_process("model")
    from hyperion.compose import bot as CB
    from hyperion.drills import variants as V
    from hyperion.sim import bestiary as B
    from hyperion.sim.runner import run_tournament

    CB.COUNTS.clear()
    nm = SW._spec_bot(name, spec)
    rules = _rules(pay, rules_name)
    v = V.get(variant, seed=SW.SEED) if variant else None
    t0 = time.time()
    l0 = os.getloadavg()[0]
    rep = run_tournament(B.field_names(f"{field}@{nm}"), n, seed=SW.SEED, rotate=True, mode="model", rules=rules,
                         hero_config=B.HERO_CONFIG, table_offset=off, variant=v)
    b = rep.bots[nm]
    st = b.stats
    ex = rep.bots.get(EXPLOIT_BOT)
    return key, (field, pay, rules_name, variant, off), {
        "samples": b.samples, "opp_samples": ex.samples if ex is not None else None, "tmo": st.over_budget,
        "exc": st.exceptions, "ill": st.illegal,
        "safe_err": st.safe_err, "calls": st.calls, "p50": st.percentile_us(0.5), "p99": st.percentile_us(0.99),
        "max_us": st.max_ns / 1000, "secs": time.time() - t0, "load": (l0, os.getloadavg()[0])}


def cell_path(out: str, key: str, cell) -> str:
    field, pay, rules_name, variant, off = cell
    return os.path.join(out, key, f"{field}.{pay}.{_rules_tag(rules_name)}.{variant or '-'}.{off}.json")


def run_cells(out: str, specs: dict, cells: list, lo: int, hi: int, workers: int) -> None:
    """Run every (spec, cell, chunk) not yet cached."""
    jobs, seen = [], set()
    for name, (key, spec) in specs.items():
        for field, pay, rules_name, variant in cells:
            for off in range(lo, hi, CHUNK):
                p = cell_path(out, key, (field, pay, rules_name, variant, off))
                if not os.path.exists(p) and p not in seen:  # base == cand (warming the cache) runs once
                    seen.add(p)
                    jobs.append((key, name, spec, field, pay, rules_name, variant, off, min(CHUNK, hi - off)))
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
            path = cell_path(out, key, cell)
            with open(path + ".tmp", "w") as fh:
                json.dump(res, fh)
            os.replace(path + ".tmp", path)


def gather(out: str, key: str, cell4, lo: int, hi: int) -> dict:
    field, pay, rules_name, variant = cell4
    samples, opp, agg = [], [], {"tmo": 0, "exc": 0, "ill": 0, "safe_err": 0, "calls": 0, "p99": 0.0, "max_us": 0.0}
    for off in range(lo, hi, CHUNK):
        with open(cell_path(out, key, (field, pay, rules_name, variant, off))) as fh:
            r = json.load(fh)
        samples += r["samples"]
        opp += r.get("opp_samples") or []
        for k in ("tmo", "exc", "ill", "safe_err", "calls"):
            agg[k] += r[k]
        agg["p99"] = max(agg["p99"], r["p99"])
        agg["max_us"] = max(agg["max_us"], r["max_us"])
    agg["samples"] = samples
    agg["mean"] = sum(samples) / len(samples)
    agg["opp_mean"] = sum(opp) / len(opp) if opp else None
    return agg


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
    p.add_argument("--aware", default=None, help="the aware stage's fields (default: all three)")
    p.add_argument("--variants", default=None, help="the variants stage's entries (default: the whole catalog)")
    p.add_argument("--variant-seeds", type=int, default=VARIANT_SEEDS,
                   help="seeds per variant cell, from the set's first (addendum 7's replication: 400)")
    p.add_argument("--rules", default=None, help="a Rules JSON (the night's rules_tonight.json) for the window, "
                                                 "confirm, guards and elite cells")
    p.add_argument("--variant", default=None, help="a catalog variant's hooks for the same cells")
    p.add_argument("--aim", choices=("night", "exploit", "strong"), default="night",
                   help="what the change is for: night (confirm beyond noise up), exploit (addendum 6: an exploit "
                        "field up, night not down) or strong (addendum 8: elite, elite_night or mirror up, night "
                        "not down)")
    a = p.parse_args(argv)
    version = code_version()
    base_raw, cand_raw = load_spec(a.base), load_spec(a.cand)
    base, cand = resolve(base_raw), resolve(cand_raw)
    specs = {"base": (spec_key(base, version), base), "cand": (spec_key(cand, version), cand)}
    stages = [s.strip() for s in a.stages.split(",") if s.strip()]
    a.set = a.set or ("screen" if stages == ["window"] else "H1")
    lo, hi = seed_range(a.set)
    rows, verdict = [], {"version": version, "set": a.set, "seeds": [lo, hi], "base": base, "cand": cand,
                         "stages": {}}
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
        plan.append(("aware", [(f, "lin", None, AW.AWARE_VARIANT[f]) for f in names], lo, hi))
    if "exploit" in stages:
        plan.append(("exploit", EXPLOIT, lo, hi))
    if "variants" in stages:
        names = a.variants.split(",") if a.variants else V.catalog_names()
        plan.append(("variants", [(VARIANT_FIELD, "lin", None, v) for v in names], lo,
                     min(hi, lo + a.variant_seeds)))
    for stage, cells, s_lo, s_hi in plan:
        cells4 = [c if len(c) == 4 else (*c, None) for c in cells]
        run_cells(a.out, specs, cells4, s_lo, s_hi, a.workers)
        out = []
        for c in cells4:
            gb = gather(a.out, specs["base"][0], c, s_lo, s_hi)
            gc_ = gather(a.out, specs["cand"][0], c, s_lo, s_hi)
            m, h = paired(gb["samples"], gc_["samples"])
            out.append({"cell": label(c), "base": gb["mean"], "cand": gc_["mean"], "delta": m, "ci": h,
                        "flag": flag(m, h), "n": len(gb["samples"]), "tmo": (gb["tmo"], gc_["tmo"]),
                        "exc": (gb["exc"] + gb["ill"] + gb["safe_err"], gc_["exc"] + gc_["ill"] + gc_["safe_err"]),
                        "p99": (gb["p99"], gc_["p99"]), "opp": (gb["opp_mean"], gc_["opp_mean"])})
        verdict["stages"][stage] = out
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
    for s in ("guards", "elite", "variants", "judges", "aware"):
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
        print(f"\n## exploit (diagnostic)\n\n| cell | base | cand | cand - base | | n | {EXPLOIT_BOT} b/c | p99 b/c |")
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
    if "timing" in st:
        print(f"\n## timing\n- base: {st['timing']['base']['raw']}\n- cand: {st['timing']['cand']['raw']}")
    print("\n## verdict")
    for txt, ok in checks:
        print(f"- [{'x' if ok else ' '}] {txt}")
    if verdict["replicate"]:
        print(f"\n**REPLICATE** {verdict['replicate']}: one variant cell down; addendum 7 re-runs it on the next "
              f"held-out set with --variants NAME --variant-seeds 400")
    else:
        print(f"\n**{'ACCEPT' if verdict['accept'] else 'REJECT'}**" if checks else "")
    if a.json:
        with open(a.json, "w") as fh:
            json.dump(verdict, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
