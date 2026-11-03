"""The weighted score of addendum 11 (docs/decisions.md; docs/research/acceptance-rule-review.md, "The proposed rule"):
every cell in night points, five families with fixed weights, the family-block interval, W-min over the plausible
ranges, the cap, and route 2's test. The numbers are in tools/accept_weights.json; this is the arithmetic, the review's
own scripts (wrule.py, sens2.py) reused. tools/climb_accept.py prints it beside its verdict; it decides nothing there.

Input is a verdict's `stages` dict (climb_accept's --json), so a saved verdict scores the same as a live run."""
from __future__ import annotations

import itertools
import json
import math
import os

WEIGHTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "accept_weights.json")
FAMILIES = ("ordinary", "strong", "adapters", "twist_realistic", "twist_aware")
UNWEIGHTED_STAGES = ("judges", "window", "timing")


def load(path: str = WEIGHTS) -> dict:
    with open(path) as fh:
        return json.load(fh)


def parse_label(label: str) -> tuple[str, str, str | None, str | None]:
    """climb_accept.label() backwards: 'VARIANT (FIELD @PAYOUTS +RULES)' -> (field, payouts, rules, variant)."""
    s, variant = label, None
    if s.endswith(")") and " (" in s:
        variant, s = s[:-1].split(" (", 1)
    rules = None
    if " +" in s:
        s, rules = s.split(" +", 1)
    pay = "8..1"
    if " @" in s:
        s, pay = s.split(" @", 1)
    return s.strip(), pay, rules, variant


def _adapter_cell(W: dict, field: str):
    for bot, fmts in W["families"]["adapters"]["bots"].items():
        for fmt, f in fmts.items():
            if f == field:
                return bot, fmt
    return None


def classify(W: dict, stage: str, label: str) -> dict:
    """A cell's family, its key inside the family, and its factor to night points."""
    field, pay, rules, variant = parse_label(label)
    u = W["units"]
    if variant in u["variants"]:
        unit = u["variants"][variant]
    elif rules in u["rules"]:
        unit = u["rules"][rules]
    else:
        unit = u["payouts"].get(pay, 1.0)
    c = dict(stage=stage, label=label, field=field, pay=pay, rules=rules, variant=variant, unit=unit, key=label)
    F = W["families"]
    if stage == "judges" or (stage not in ("variants", "aware") and field in W["judges"]):
        c["family"] = "judges"
    elif stage in UNWEIGHTED_STAGES:
        c["family"] = stage
    elif stage == "variants":
        c.update(family="twist_realistic", key=variant)
    elif stage == "aware":
        c.update(family="twist_aware", key=variant)
    elif field in F["ordinary"]["fields"]:
        c["family"] = "ordinary"
    elif field in F["strong"]["fields"]:
        c["family"] = "strong"
    elif _adapter_cell(W, field):
        bot, fmt = _adapter_cell(W, field)
        c.update(family="adapters", key=(bot, fmt), bot=bot, fmt=fmt)
    else:
        c["family"] = "unmapped"
    return c


def cells_from(W: dict, stages: dict) -> list[dict]:
    out = []
    for stage, rows in stages.items():
        if stage == "timing":
            continue
        for r in rows:
            c = classify(W, stage, r["cell"])
            c.update(delta=r["delta"], ci=r["ci"], flag=r["flag"], n=r["n"], src="measured")
            out.append(c)
    return out


def _zero(W, stage, label):
    c = classify(W, stage, label)
    c.update(label=label + " [identical]", delta=0.0, ci=0.0, flag="level", n=0, src="identical")
    return c


def identical_twists(W: dict, identical) -> set:
    names = set()
    for t in identical or ():
        if t == "twists":
            names |= set(W["variant_probability"]["p"]) - set(W["holdem_tables"])
        elif t != "holdem":
            names.add(t)
    return names


def impute(W: dict, cells: list[dict], identical) -> tuple[list[dict], list[str]]:
    """Cells identical by construction count 0 +- 0 where no cell ran (the section's missing-cell rule). Returns the
    cells and the claims a measured cell contradicts (an identical cell plays exactly as the base: delta and ci 0)."""
    identical = list(identical or ())
    twists = identical_twists(W, identical)
    out = list(cells)
    contra = []
    have = {(c["family"], c["key"]) for c in cells}
    for c in cells:
        claimed = (c["family"] in ("twist_realistic", "twist_aware") and c["key"] in twists) or (
            "holdem" in identical and c["family"] in ("ordinary", "strong", "adapters"))
        if claimed and (c["delta"] != 0 or c["ci"] != 0):
            contra.append(c["label"])
    for v in sorted(twists):
        for fam, lab in (("twist_realistic", f"{v} (realistic)"), ("twist_aware", f"{v} (aware)")):
            if (fam, v) not in have:
                out.append(_zero(W, "variants" if fam == "twist_realistic" else "aware", lab))
    if "holdem" in identical:
        F = W["families"]
        for fam in ("ordinary", "strong", "adapters"):
            if any(c["family"] == fam for c in out):
                continue
            if fam == "adapters":
                labs = [("exploit", f + {"8max": " @10/7/5/4/3/2/1/0", "hu": " +hu", "three": " +three"}[fmt])
                        for fmts in F[fam]["bots"].values() for fmt, f in fmts.items()]
            else:
                labs = [("guards", lab) for lab in F[fam]["cells"]]
            out += [_zero(W, st, lab) for st, lab in labs]
    return out, contra


def shares(W: dict, cells: list[dict], adapters: str = "fixed") -> dict:
    """Each weighted cell's share of its family (index -> share). adapters='fixed' is the committed rule (a quarter per
    bot, a bot not run 0 +- 0); 'shared' is the review's first draft (the format's cells that ran share it), kept only
    to reproduce its W column."""
    F = W["families"]
    P = W["variant_probability"]["p"]
    unlisted = W["variant_probability"]["unlisted"]
    by = {}
    for i, c in enumerate(cells):
        if c["family"] in FAMILIES:
            by.setdefault(c["family"], []).append(i)
    out = {}
    for fam, idx in by.items():
        keys = {}
        for i in idx:
            keys.setdefault(cells[i]["key"], []).append(i)
        if fam in ("ordinary", "strong"):
            sh = F[fam]["cells"]
            unnamed = 0.05  # the review script's default for a cell its table does not name (accept_weights notes)
            tot = sum(sh.get(k, unnamed) for k in keys)
            for k, ii in keys.items():
                for i in ii:
                    out[i] = sh.get(k, unnamed) / tot / len(ii)
        elif fam == "adapters":
            fm = F[fam]["formats"]
            if adapters == "fixed":
                tot = sum(fm.values())
                for i in idx:
                    out[i] = fm[cells[i]["fmt"]] / tot * F[fam]["bot_share"]
            else:
                fmts = {}
                for i in idx:
                    fmts.setdefault(cells[i]["fmt"], []).append(i)
                tot = sum(fm[f] for f in fmts)
                for f, ii in fmts.items():
                    for i in ii:
                        out[i] = fm[f] / tot / len(ii)
        else:
            tot = sum(P.get(k, unlisted) for k in keys)
            for k, ii in keys.items():
                for i in ii:
                    out[i] = P.get(k, unlisted) / tot / len(ii)
    return out


def family_stats(cells: list[dict], sh: dict) -> dict:
    fs = {}
    for i, s in sh.items():
        c = cells[i]
        f = fs.setdefault(c["family"], {"mean": 0.0, "half": 0.0, "cells": 0, "measured": 0})
        f["mean"] += s * c["unit"] * c["delta"]
        f["half"] += s * c["unit"] * c["ci"]
        f["cells"] += 1
        f["measured"] += c["src"] == "measured"
    return fs


def bound(fs: dict, w: dict) -> tuple[float, float, float]:
    """Weighted mean, family-block half-width, lower bound."""
    m = sum(w[f] * fs[f]["mean"] for f in fs)
    h = math.sqrt(sum((w[f] * fs[f]["half"]) ** 2 for f in fs))
    return m, h, m - h


def corners(W: dict, fams: list[str]) -> list[dict]:
    """Corners of {lo <= w <= hi, sum w = 1} over the present families (ranges scaled when families are dropped and the
    ranges cannot sum to 1)."""
    F = W["families"]
    lo = {f: F[f]["range"][0] for f in fams}
    hi = {f: F[f]["range"][1] for f in fams}
    if sum(lo.values()) > 1 or sum(hi.values()) < 1:
        s = sum(F[f]["weight"] for f in fams)
        lo = {f: F[f]["range"][0] / s for f in fams}
        hi = {f: min(1.0, F[f]["range"][1] / s) for f in fams}
    out = []
    for free in fams:
        others = [f for f in fams if f != free]
        for combo in itertools.product((0, 1), repeat=len(others)):
            w = {f: (hi[f] if b else lo[f]) for f, b in zip(others, combo)}
            rest = 1 - sum(w.values())
            if lo[free] - 1e-9 <= rest <= hi[free] + 1e-9:
                w[free] = rest
                out.append(w)
    return out


def expected_missing(W: dict, cells: list[dict]) -> dict:
    """What a full run has that this one does not: per family, the cells not run (twist_aware: none expected beyond
    its own cells; its count of twists is reported instead)."""
    F = W["families"]
    have = {(c["family"], c["key"]) for c in cells}
    miss = {}
    for fam in ("ordinary", "strong"):
        m = [lab for lab in F[fam]["cells"] if (fam, lab) not in have]
        if m:
            miss[fam] = m
    m = [f for bot, fmts in F["adapters"]["bots"].items() for fmt, f in fmts.items()
         if ("adapters", (bot, fmt)) not in have]
    if m:
        miss["adapters"] = m
    m = [v for v in W["variant_probability"]["p"] if ("twist_realistic", v) not in have]
    if m:
        miss["twist_realistic"] = m
    return miss


def score(stages: dict, identical=(), W: dict | None = None, adapters: str = "fixed") -> dict:
    """The weighted block for a verdict's stages: base weights and W-min, the cap, what is missing."""
    W = W or load()
    measured = cells_from(W, stages)
    cells, contra = impute(W, measured, identical)
    sh = shares(W, cells, adapters)
    fs = family_stats(cells, sh)
    present = [f for f in FAMILIES if f in fs]
    F = W["families"]
    res = {"rule": "addendum 11 (tools/accept_weights.json)", "identical": list(identical or ()),
           "contradicted": contra, "families": {}, "dropped": [f for f in FAMILIES if f not in fs],
           "missing": expected_missing(W, cells),
           "aware_twists": sorted({c["key"] for c in measured if c["family"] == "twist_aware"}),
           "aware_identical": sorted({c["key"] for c in cells if c["family"] == "twist_aware"}
                                     - {c["key"] for c in measured if c["family"] == "twist_aware"}),
           "not_weighted": sorted({c["label"] for c in measured if c["family"] in ("unmapped", "window")}),
           "judges_down": [c["label"] for c in measured if c["family"] == "judges" and c["flag"] == "DOWN"],
           "judges": [c["label"] for c in measured if c["family"] == "judges"],
           "down": [c["label"] for c in measured if c["family"] in FAMILIES and c["flag"] == "DOWN"]}
    if not present:
        res.update(mean=None, half=None, lb=None, w_min=None, cap={"night_points": W["cap"]["night_points"],
                                                                   "broken": []})
        return res
    tot = sum(F[f]["weight"] for f in present)
    w0 = {f: F[f]["weight"] / tot for f in present}
    m, h, lb = bound({f: fs[f] for f in present}, w0)
    worst = min(((bound(fs, w)[2], w) for w in corners(W, present)), key=lambda t: t[0])
    wm, wh, _ = bound(fs, worst[1])
    cap = W["cap"]["night_points"]
    broken = []
    for c in cells:
        if c["family"] not in FAMILIES:
            continue
        ub = c["unit"] * (c["delta"] + c["ci"])
        if ub < -cap:
            broken.append({"cell": c["label"], "delta": c["delta"], "ci": c["ci"], "upper_night_points": ub})
    for f in present:
        res["families"][f] = {"weight": w0[f], "w_min": worst[1][f], **fs[f]}
    res.update(mean=m, half=h, lb=lb, w_min={"lb": worst[0], "mean": wm, "half": wh, "weights": worst[1]},
               cap={"night_points": cap, "broken": broken},
               cells=[[c["label"], c["family"], round(sh[i], 6), round(c["unit"], 6), c["delta"], c["ci"], c["src"]]
                      for i, c in enumerate(cells) if i in sh])
    return res


ROUTE2_STAGES = ("confirm", "guards", "elite", "exploit", "variants", "aware")


def route2_refusal(set_name: str, stages, variants=None, variant_seeds: int = 200, rules=None, variant=None) -> str:
    """Why --route2 cannot run here ('' when it can): route 2 needs a held-out set with every stage of the protocol."""
    why = []
    if not (set_name.upper().startswith("H") and set_name[1:].isdigit()):
        why.append(f"set {set_name!r} is not a held-out set (H1, H2, ...)")
    miss = [s for s in ROUTE2_STAGES if s not in stages]
    if miss:
        why.append(f"stages not run: {', '.join(miss)} (every stage: {','.join(ROUTE2_STAGES)})")
    if variants:
        why.append("--variants runs part of the catalogue")
    if variant_seeds < 200:
        why.append(f"--variant-seeds {variant_seeds} < 200")
    if rules or variant:
        why.append("--rules/--variant play the night's game, not the protocol's cells")
    return "; ".join(why)


def route2(ws: dict, main_accept, judges_rows=None) -> dict:
    """Route 2's test (addendum 11) on a weighted block. accept: True, False, or None while the judges are pending.
    Condition (d), a log entry per down cell, is the log's job: the cells are listed for it."""
    checks = []
    applies = not main_accept
    checks.append(("every family run (none dropped)", not ws["dropped"]))
    if ws["contradicted"]:
        checks.append((f"identical claims hold (contradicted by: {', '.join(ws['contradicted'])})", False))
    lbm = ws["w_min"]["lb"] if ws["w_min"] else None
    checks.append((f"(a) W-min lower bound above zero ({'-' if lbm is None else f'{lbm:+.4f}'} night points)",
                   lbm is not None and lbm > 0))
    br = ws["cap"]["broken"]
    checks.append(("(b) no cell breaks the cap" + (f" (broken: {', '.join(b['cell'] for b in br)})" if br else ""),
                   not br))
    if judges_rows is None:
        checks.append(("(c) no judge beyond noise down: pending (pass --judges-json, the judges stage on --set judge)",
                       None))
    else:
        jd = [r["cell"] for r in judges_rows if r["flag"] == "DOWN"]
        checks.append((f"(c) no judge beyond noise down ({len(judges_rows)} judges"
                       + (f"; down: {', '.join(jd)})" if jd else ")"), not jd and bool(judges_rows)))
    downs = ws["down"]
    oks = [ok for _, ok in checks]
    accept = False if any(ok is False for ok in oks) else (None if any(ok is None for ok in oks) else True)
    return {"applies": applies, "accept": accept if applies else None, "checks": checks, "log_down_cells": downs}


def _f(x, nd=4):
    return "-" if x is None else f"{x:+.{nd}f}"


def lines(ws: dict, W: dict | None = None) -> list[str]:
    """The printed block."""
    W = W or load()
    F = W["families"]
    out = ["", "## weighted (addendum 11: printed beside the verdict, decides nothing in it)", ""]
    if ws["mean"] is None:
        out.append("- no weighted cells in this run" + (f" (judges: {len(ws['judges'])})" if ws["judges"] else ""))
        return out
    out += ["| family | weight | W-min weight | cells (measured) | mean | ± block |", "|---|---|---|---|---|---|"]
    for f, d in ws["families"].items():
        out.append(f"| {F[f]['name']} | {d['weight']:.3f} | {d['w_min']:.3f} | {d['cells']} ({d['measured']}) | "
                   f"{_f(d['mean'])} | {d['half']:.4f} |")
    out.append("")
    out.append(f"- W, base weights: {_f(ws['mean'])} ± {ws['half']:.4f} night points (family block); lower bound "
               f"**{_f(ws['lb'])}**")
    wm = ws["w_min"]
    corner = ", ".join(f"{f.replace('_', ' ')} {wm['weights'][f]:.2f}" for f in FAMILIES if f in wm["weights"])
    out.append(f"- W-min, worst corner ({corner}): {_f(wm['mean'])} ± {wm['half']:.4f}; lower bound "
               f"**{_f(wm['lb'])}**")
    cap = ws["cap"]
    if cap["broken"]:
        out.append(f"- cap (no cell's upper bound below -{cap['night_points']} night points): **broken** by "
                   + "; ".join(f"{b['cell']} {b['delta']:+.3f} ± {b['ci']:.3f} (upper {b['upper_night_points']:+.4f} "
                               f"night points)" for b in cap["broken"]))
    else:
        out.append(f"- cap (no cell's upper bound below -{cap['night_points']} night points): holds")
    miss = []
    if ws["dropped"]:
        miss.append("families not run (dropped, the others reweighted; never under route 2): "
                    + ", ".join(F[f]["name"] for f in ws["dropped"]))
    for f, labs in ws["missing"].items():
        if f in ws["dropped"]:
            continue
        how = "0 ± 0 at their fixed quarter" if f == "adapters" else "the cells that ran share the family"
        shown = ", ".join(labs) if len(labs) <= 8 else f"{len(labs)} variants"
        miss.append(f"{F[f]['name']}: {shown} ({how})")
    if "twist_aware" in ws["families"]:
        n = len(W["variant_probability"]["p"])
        k, z = len(ws["aware_twists"]), len(ws["aware_identical"])
        if k + z < n:
            miss.append(f"twist-aware field: no cell on {n - k - z} of {n} twists (measured on {k}"
                        + (f", identical on {z}" if z else "") + "; the cells there share the family)")
    out.append("- missing: " + ("; ".join(miss) if miss else "none"))
    if ws["identical"]:
        out.append(f"- identical by construction (0 ± 0 where not run): {', '.join(ws['identical'])}"
                   + (f"; **contradicted** by {', '.join(ws['contradicted'])}" if ws["contradicted"] else ""))
    if ws["not_weighted"]:
        out.append(f"- not weighted: {', '.join(ws['not_weighted'])}")
    if ws["judges_down"]:
        out.append(f"- judges beyond noise down (route 2's condition c): {', '.join(ws['judges_down'])}")
    return out


def route2_lines(r2: dict) -> list[str]:
    out = ["", "## route 2 (addendum 11)", ""]
    if not r2["applies"]:
        out.append("- the main rule accepts: route 2 not needed")
    for txt, ok in r2["checks"]:
        out.append(f"- [{'x' if ok else ('?' if ok is None else ' ')}] {txt}")
    if r2["log_down_cells"]:
        out.append(f"- (d) write up each down cell in the log with its cause: {', '.join(r2['log_down_cells'])}")
    out.append("- the set must be fresh for this candidate: not checked here")
    if r2["applies"]:
        word = {True: "ACCEPT", False: "REJECT", None: "PENDING (judges)"}[r2["accept"]]
        out.append(f"\n**ROUTE 2: {word}**" + (" once each down cell is in the log with its cause"
                                                if r2["accept"] and r2["log_down_cells"] else ""))
    return out
