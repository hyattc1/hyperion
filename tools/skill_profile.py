"""Skill profile: what each bot is good at, section by section of the game, not just one score.

    python tools/skill_profile.py run --field night --bots hybrid3_x,hero,rival3 --seeds 0:200 --out DIR [--workers 3]
    python tools/skill_profile.py report DIR [DIR ...] --out docs/drills/skill-profile.md [--fields night,realistic]

`run` seats each bot in Hero's seat of the field (`<field>@<bot>`, so every bot plays the same deals against the same
opponents), plays duplicate tables (seed 7, all eight rotations) and records every decision the Hero seat makes, by the
section of the game it falls in (hyperion/compose/sections.py: twelve sections, from deep opens to heads-up rivers).
Results accumulate in DIR/<field>/<bot>.json, one file per bot, merged chunk by chunk, so a run can be extended.
`report` reads them and writes ranked leaderboards per section.

Per bot and section:
- **share**: the section's share of the bot's decisions;
- **vpip**: share of decisions that put chips in voluntarily (call or raise); **pfr** (raise): share that raise;
- **agg**: raises per call (the aggression factor);
- **allin**: share of decisions that put the whole stack in;
- **bb/dec**: chips won per decision, in big blinds of the hand. A hand's net result is split over the decisions that
  put chips into it, in proportion to the chips each put in: the bot takes W chips from the pot and put in T (blinds
  included), so a decision that put in c gets W * c / T - c, and the posted blinds get the rest (the `blinds` row,
  with the hands where the bot never acted: walks and all-ins by posting). Folds and checks put in nothing and get 0.
  The rows sum to the bot's net chips exactly;
- **sd win**: share of the showdowns the bot won (net chips > 0), by the section of its last decision in the hand;
- **busts**: the section of the last decision that put chips in on the hand the bot busted.
Per bot: points, 1st %, bust %, the finish distribution.

**Descriptive, not causal.** Each bot reaches different spots (a tight opener sees fewer flops, a short stack lives in
the push-or-fold sections), so a section's numbers mix skill with how the bot got there. "Best at short-stack play"
means its decisions there won the most chips per decision in the spots it reached. The causal measure is the compose
agent's swap test: the same bot with one section's decisions replaced, paired on the same deals.

Mode `model` (the default) is the deterministic timeout model; as in the final comparison, Hero's SafeBot panic and the
hybrids' soft deadline are off there (`panic_after` 10^9, `soft_us` 10^6), so nothing reads the wall clock but rival 2's
sampler. Rival 2 is imported with its clock held still, so its import-time tables are complete at any load
(steady_rival2). `--mode strict` plays everything as shipped. At most `--workers` processes (default 3).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from multiprocessing import Pool
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperion.compose.sections import SECTIONS  # noqa: E402
from hyperion.compose.sections import section as _section  # noqa: E402
from hyperion.core.types import Action, ActionKind, Rules  # noqa: E402
from hyperion.sim import bestiary as B  # noqa: E402
from hyperion.sim import runner as R  # noqa: E402
from hyperion.sim.engine import BotStats  # noqa: E402

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
ROWS = SECTIONS + ("blinds",)  # the last row: posted blinds, walks, all-ins by posting
BLINDS = len(SECTIONS)
# counters per row
KEYS = ("dec", "vpip", "raise", "call", "fold", "check", "allin", "chips_bb", "sd", "sd_won", "busts")
LABEL = {
    "pre_open_40": "opening deep (unopened pot, 40+ bb)",
    "pre_open_20": "opening at 20-40 bb",
    "pre_open_10": "opening at 10-20 bb",
    "pre_open_short": "push or fold (unopened, under 10 bb)",
    "pre_raised_deep": "facing a raise, 20+ bb",
    "pre_raised_short": "facing a raise under 20 bb (re-shove or fold)",
    "pre_allin": "facing an all-in",
    "pre_3way": "three-handed preflop",
    "pre_hu": "heads-up preflop",
    "post_hu_bet": "heads-up pot after the flop, facing a bet",
    "post_hu_chk": "heads-up pot after the flop, nothing to call",
    "post_mw": "multiway pot after the flop",
    "blinds": "posted blinds (no decision)",
}
GROUPS = (  # plain-language groups of sections for the summary leaderboards
    ("deep preflop play", ("pre_open_40", "pre_open_20", "pre_raised_deep")),
    ("short-stack play", ("pre_open_10", "pre_open_short", "pre_raised_short", "pre_allin")),
    ("endgame (three-handed and heads-up preflop)", ("pre_3way", "pre_hu")),
    ("play after the flop", ("post_hu_bet", "post_hu_chk", "post_mw")),
)
MODEL_HERO_CONFIG = {"panic_after": 10 ** 9}
MODEL_HYBRID_CONFIG = {"panic_after": 10 ** 9, "soft_us": 1e6}


def _new_counts() -> dict:
    return {k: [0.0] * len(ROWS) for k in KEYS}


class Tracer:
    """Wraps the Hero seat's bot and books each decision by section. Passes every call through unchanged; mirrors the
    engine's enforcement (a non-Action or an exception is a check or fold, an illegal action is clamped) so the
    booked action is the one the table played. The engine finds the inner bot's SafeBot and variant_decide through
    `inner`, and its modelled cost through `last_cost_ns`."""

    def __init__(self, inner, counts: dict):
        self.inner = inner
        self.c = counts
        self.seat = 0
        self.rules = Rules()
        self._hand = -1
        self._dec: list = []  # (row, chips put in) this hand
        self._forced = 0
        self._bb = 1

    def use_cost_model(self, on: bool) -> None:
        hook = getattr(self.inner, "use_cost_model", None)
        if callable(hook):
            hook(on)

    @property
    def last_cost_ns(self):
        return getattr(self.inner, "last_cost_ns", None)

    def new_table(self, rules, seat: int, n_players: int) -> None:
        self.rules, self.seat = rules, seat
        self._hand, self._dec, self._forced = -1, [], 0
        self._chips = rules.starting_stack  # chips at the start of the next hand, kept from the deltas
        self.inner.new_table(rules, seat, n_players)

    def act(self, obs):
        if obs.hand_no != self._hand:
            self._hand, self._dec = obs.hand_no, []
            self._forced = obs.bets[obs.seat] if obs.street == 0 else 0
            self._bb = obs.blinds[1] or 1
        try:
            a = self.inner.act(obs)
        except Exception:
            self._book(obs, Action.check() if CHECK in obs.legal else Action.fold())
            raise
        played = a
        if type(a) is not Action:
            played = Action.check() if CHECK in obs.legal else Action.fold()
        elif a.kind not in obs.legal or (a.kind is RAISE and not obs.min_raise <= a.amount <= obs.max_raise):
            played = a.clamp(obs)
        self._book(obs, played)
        return a

    def _book(self, obs, a) -> None:
        row = _section(obs)
        c = self.c
        c["dec"][row] += 1
        k = a.kind
        me = obs.seat
        put = 0
        if k is CALL:
            put = min(obs.to_call, obs.stacks[me])
            c["call"][row] += 1
            c["vpip"][row] += 1
        elif k is RAISE:
            put = a.amount - obs.bets[me]
            c["raise"][row] += 1
            c["vpip"][row] += 1
        elif k is FOLD:
            c["fold"][row] += 1
        else:
            c["check"][row] += 1
        if put > 0 and put >= obs.stacks[me]:
            c["allin"][row] += 1
        self._dec.append((row, put))

    def hand_end(self, result) -> None:
        try:
            self._settle(result)
        finally:
            self.inner.hand_end(result)

    def _settle(self, result) -> None:
        c = self.c
        delta = result.deltas[self.seat]
        before = self._chips
        self._chips = before + delta
        acted = result.hand_no == self._hand
        dec = self._dec if acted else []
        if acted:
            bb = self._bb
            total = self._forced + sum(p for _, p in dec)
        else:  # no decision this hand: a walk, or all-in by posting a blind
            bb = self.rules.blinds_at(result.hand_no)[1] or 1
            total = 0
        if total > 0:
            won = delta + total  # chips taken from the pot, uncalled chips returned included
            for row, p in dec:
                if p:
                    c["chips_bb"][row] += (won * p / total - p) / bb
            if self._forced:
                c["chips_bb"][BLINDS] += (won * self._forced / total - self._forced) / bb
        elif delta:
            c["chips_bb"][BLINDS] += delta / bb
        last = dec[-1][0] if dec else BLINDS
        if self.seat in result.showdown:
            c["sd"][last] += 1
            c["sd_won"][last] += delta > 0
        if before > 0 >= self._chips:  # busted on this hand: the last decision that put chips in did it
            put_rows = [r for r, p in dec if p > 0]
            c["busts"][put_rows[-1] if put_rows else BLINDS] += 1
        self._hand = -1  # the next hand starts fresh even if its number repeats (it never does)


# ----- one job: one bot in Hero's seat for a chunk of seeds ----------------------------------------------------------


def seat_name(field: str, bot: str) -> str:
    """The name the bot sits under: itself, or `<bot>_seat` (a second registration of the same class) when the field
    already seats it, so the two seats stay apart in the report."""
    base = B.field_names(field)
    if bot != "hero" and bot in base:
        alias = f"{bot}_seat"
        if alias not in B.REGISTRY:
            cls = B.REGISTRY[bot]
            B.REGISTRY[alias] = type(cls.__name__ + "Seat", (cls,), {})
        return alias
    return bot


def run_job(args) -> dict:
    """Seeds lo..hi one at a time (each with its eight rotations), keeping each seed's section totals for the
    intervals."""
    field, bot, lo, hi, mode, payouts, seed = args
    name = seat_name(field, bot)
    names = B.field_names(f"{field}@{name}")
    counts = _new_counts()
    cur = {"c": counts}
    orig = B.make_bot

    def build(nm, seed=None):
        b = orig(nm, seed=seed)
        return Tracer(b, cur["c"]) if nm == name and seed is not None else b

    if mode == "model":
        B.HYBRID_CONFIG = dict(MODEL_HYBRID_CONFIG)
        hero_config = dict(MODEL_HERO_CONFIG)
    else:
        B.HYBRID_CONFIG, hero_config = None, None
    rules = Rules(payouts=tuple(payouts)) if payouts else None
    t0 = time.time()
    load0 = os.getloadavg()[0]
    samples, places, seats, busts, hands, per_seed_rows = [], None, 0, 0, 0, {}
    st = BotStats(name)
    R.make_bot = build
    try:
        for t in range(lo, hi):
            cur["c"] = one = _new_counts()
            rep = R.run_tournament(names, 1, seed=seed, rotate=True, mode=mode, rules=rules, hero_config=hero_config,
                                   table_offset=t)
            br = rep.bots[name]
            samples.extend(br.samples)
            places = br.places if places is None else [a + b for a, b in zip(places, br.places)]
            seats += br.seats
            busts += br.busts
            hands += rep.hands
            st.merge(br.stats)
            for k in KEYS:
                counts[k] = [a + b for a, b in zip(counts[k], one[k])]
            per_seed_rows[str(t)] = [one["chips_bb"], one["dec"]]
    finally:
        R.make_bot = orig
    return {
        "field": field, "bot": bot, "seeds": [lo, hi], "mode": mode, "seed": seed, "payouts": payouts,
        "samples": samples, "places": places, "seats": seats, "busts": busts, "per_seed_rows": per_seed_rows,
        "counts": counts, "hands": hands, "secs": time.time() - t0, "load": [load0, os.getloadavg()[0]],
        "engine": {"calls": st.calls + st.first_calls, "over_budget": st.over_budget, "exceptions": st.exceptions,
                   "illegal": st.illegal, "safe_err": st.safe_err, "p50_us": st.percentile_us(0.5),
                   "p99_us": st.percentile_us(0.99), "last_error": st.last_error},
    }


def _merge(old: Optional[dict], new: dict) -> dict:
    if old is None:
        out = {k: new[k] for k in ("field", "bot", "mode", "seed", "payouts")}
        out.update({"chunks": [], "per_seed": {}, "places": [0] * len(new["places"]), "seats": 0, "busts": 0,
                    "counts": _new_counts(), "hands": 0, "secs": 0.0, "engine": {}})
        old = out
    assert (old["mode"], old["seed"], old["payouts"]) == (new["mode"], new["seed"], new["payouts"]), "mixed settings"
    lo, hi = new["seeds"]
    if any(lo < h and l < hi for l, h in old["chunks"]):
        raise ValueError(f"{new['bot']} on {new['field']}: seeds {lo}:{hi} overlap {old['chunks']}")
    old["chunks"] = sorted(old["chunks"] + [[lo, hi]])
    for i, x in enumerate(new["samples"]):
        old["per_seed"][str(lo + i)] = x
    old.setdefault("per_seed_rows", {}).update(new.get("per_seed_rows", {}))
    old["places"] = [a + b for a, b in zip(old["places"], new["places"])]
    old["seats"] += new["seats"]
    old["busts"] += new["busts"]
    old["hands"] += new["hands"]
    old["secs"] += new["secs"]
    for k in KEYS:
        old["counts"][k] = [a + b for a, b in zip(old["counts"][k], new["counts"][k])]
    e, n = old["engine"], new["engine"]
    for k in ("calls", "over_budget", "exceptions", "illegal", "safe_err"):
        e[k] = e.get(k, 0) + n[k]
    e["p50_us"], e["p99_us"] = n["p50_us"], max(e.get("p99_us", 0.0), n["p99_us"])
    if n["last_error"]:
        e["last_error"] = n["last_error"]
    old.setdefault("loads", []).append(new["load"])
    return old


def steady_rival2() -> None:
    """Import rival 2 with its clock held still. Its import-time equity tables stop at 1500 boards or after 2.4 s,
    whichever comes first, so on a loaded host each process would build different tables; held still, every process
    builds all 1500, as a quiet host does (the compose agent's tools/swap.py does the same). Its sampler at decision
    time keeps its wall-clock budget, as built and as the final comparison played it. Called once before the workers
    fork, so they share the module."""
    import sys as _sys

    if "hyperion.sim.rivals.rival2" in _sys.modules:
        return
    real = time.perf_counter
    time.perf_counter = lambda: 0.0
    try:
        from hyperion.sim.rivals import rival2  # noqa: F401
    finally:
        time.perf_counter = real


def run(field: str, bots: list, lo: int, hi: int, out: Path, workers: int = 3, mode: str = "model",
        chunk: int = 25, payouts=None, seed: int = 7) -> None:
    """Each bot in Hero's seat for seeds lo..hi, chunks of `chunk` seeds interleaved across bots so all bots of a run
    play at the same host load. Results merge into out/<field>/<bot>.json as chunks finish."""
    if mode == "model":
        steady_rival2()
    d = out / field
    d.mkdir(parents=True, exist_ok=True)
    jobs = [(field, b, s, min(s + chunk, hi), mode, list(payouts) if payouts else None, seed)
            for s in range(lo, hi, chunk) for b in bots]
    with Pool(workers) as pool:
        for res in pool.imap_unordered(run_job, jobs):
            path = d / f"{res['bot']}.json"
            old = json.loads(path.read_text()) if path.exists() else None
            merged = _merge(old, res)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(json.dumps(merged))
            os.replace(tmp, path)
            pts = sum(res["samples"]) / len(res["samples"])
            print(f"[{field}] {res['bot']:<16} seeds {res['seeds'][0]}:{res['seeds'][1]} pts {pts:.3f} "
                  f"({res['secs']:.0f}s, load {res['load'][0]:.0f}-{res['load'][1]:.0f})", flush=True)


# ----- report ---------------------------------------------------------------------------------------------------------


def load(dirs: list, fields: Optional[list] = None) -> dict:
    """{field: {bot: merged result}} from every DIR/<field>/<bot>.json."""
    out: dict = {}
    for d in dirs:
        for f in sorted(Path(d).glob("*/*.json")):
            field = f.parent.name
            if fields and field not in fields:
                continue
            out.setdefault(field, {})[f.stem] = json.loads(f.read_text())
    return out


def mean_ci(xs: list) -> tuple:
    n = len(xs)
    if n < 2:
        return (xs[0] if xs else 0.0), 0.0
    m = sum(xs) / n
    return m, 1.96 * math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def summarize(res: dict) -> dict:
    """Per-row rates and the bot's totals from one merged result."""
    c = res["counts"]
    total_dec = sum(c["dec"][:BLINDS]) or 1
    rows = {}
    for i, nm in enumerate(ROWS):
        d = c["dec"][i]
        rows[nm] = {
            "dec": d, "share": d / total_dec if i < BLINDS else None,
            "vpip": c["vpip"][i] / d if d else None, "pfr": c["raise"][i] / d if d else None,
            "agg": (c["raise"][i] / c["call"][i]) if c["call"][i] else (math.inf if c["raise"][i] else None),
            "allin": c["allin"][i] / d if d else None,
            "chips_bb": c["chips_bb"][i], "bb_dec": c["chips_bb"][i] / d if d else None,
            "sd": c["sd"][i], "sd_win": c["sd_won"][i] / c["sd"][i] if c["sd"][i] else None,
            "busts": c["busts"][i],
        }
    samples = [res["per_seed"][k] for k in sorted(res["per_seed"], key=int)]
    pts, ci = mean_ci(samples)
    seats = res["seats"] or 1
    psr = res.get("per_seed_rows", {})
    return {"rows": rows, "pts": pts, "ci": ci, "n": len(samples), "first": res["places"][0] / seats,
            "per_seed_rows": [psr[k] for k in sorted(psr, key=int)],
            "bust": res["busts"] / seats, "places": [p / seats for p in res["places"]], "decisions": total_dec,
            "net_bb": sum(c["chips_bb"]), "engine": res.get("engine", {}), "chunks": res["chunks"]}


def _fmt(x, pct=False, digits=2) -> str:
    if x is None:
        return "-"
    if x == math.inf:
        return "inf"
    return f"{100 * x:.0f}%" if pct else f"{x:+.{digits}f}" if digits == 3 else f"{x:.{digits}f}"


def ratio_ci(per_seed: list) -> float:
    """95% half-width of sum(chips) / sum(decisions) over seeds (the ratio estimator's linearised standard error;
    the seed is the unit, its eight rotations inside it)."""
    n = len(per_seed)
    tot_d = sum(d for _, d in per_seed)
    if n < 2 or not tot_d:
        return 0.0
    r = sum(c for c, _ in per_seed) / tot_d
    ss = sum((c - r * d) ** 2 for c, d in per_seed)
    return 1.96 * math.sqrt(ss * n / (n - 1)) / tot_d


def leaderboard(field_res: dict, rows: tuple, min_dec: int = 200) -> list:
    """Bots ranked by chips won per decision over `rows` (one section or a group); bots with fewer than `min_dec`
    decisions there are left out. -> [(bot, bb/dec, decisions, share, ±95%)]"""
    out = []
    for bot, s in field_res.items():
        d = sum(s["rows"][r]["dec"] for r in rows)
        if d < min_dec:
            continue
        chips = sum(s["rows"][r]["chips_bb"] for r in rows)
        idx = [ROWS.index(r) for r in rows]
        per = [(sum(c[i] for i in idx), sum(dd[i] for i in idx)) for c, dd in s.get("per_seed_rows", [])]
        out.append((bot, chips / d, d, d / s["decisions"], ratio_ci(per)))
    return sorted(out, key=lambda t: -t[1])


def report(dirs: list, fields: Optional[list] = None, names: Optional[dict] = None, top: int = 99) -> str:
    """Markdown: per field, the bots by points, then per group and per section a ranked list by bb per decision, then
    each bot's table. `names` maps a bot's file name to the name shown (e.g. a private bot's alias)."""
    names = names or {}
    data = load(dirs, fields)
    order = fields or sorted(data)
    lines = []
    for field in order:
        if field not in data:
            continue
        summ = {names.get(b, b): summarize(r) for b, r in data[field].items()}
        any_res = next(iter(data[field].values()))
        n_seeds = {s["n"] for s in summ.values()}
        lines.append(f"## `{field}`: {', '.join(str(n) for n in sorted(n_seeds))} seeds x 8 rotations, mode "
                     f"{any_res['mode']}, seed {any_res['seed']}")
        lines.append("")
        lines.append("Overall, by points (uniform 4.50):")
        lines.append("")
        ranked = sorted(summ.items(), key=lambda kv: -kv[1]["pts"])
        for i, (b, s) in enumerate(ranked, 1):
            lines.append(f"{i}. **{b}** {s['pts']:.2f} ± {s['ci']:.2f} (1st {100 * s['first']:.0f}%, bust "
                         f"{100 * s['bust']:.0f}%)")
        lines.append("")
        lines.append("Best at, by chips won per decision (bb) in the spots each bot reached, ± 95% (the seed is the "
                     "unit):")
        lines.append("")
        for title, rows in GROUPS:
            lb = leaderboard(summ, rows)[:top]
            lines.append(f"- **{title}**: " + ", ".join(f"{i}. {b} {v:+.3f} ± {ci:.3f}"
                                                       for i, (b, v, _, _, ci) in enumerate(lb, 1)))
        lines.append("")
        lines.append("Per section (bb per decision ± 95%; the bot's share of its decisions in brackets):")
        lines.append("")
        for nm in SECTIONS:
            lb = leaderboard(summ, (nm,))[:top]
            lines.append(f"- *{LABEL[nm]}* (`{nm}`): "
                         + ", ".join(f"{i}. {b} {v:+.3f} ± {ci:.3f} ({100 * sh:.0f}%)"
                                     for i, (b, v, _, sh, ci) in enumerate(lb, 1)))
        lines.append("")
        bust_rows = {}
        for b, s in summ.items():
            tot = sum(s["rows"][r]["busts"] for r in ROWS) or 1
            top3 = sorted(ROWS, key=lambda r: -s["rows"][r]["busts"])[:3]
            bust_rows[b] = ", ".join(f"{r} {100 * s['rows'][r]['busts'] / tot:.0f}%" for r in top3
                                     if s["rows"][r]["busts"])
        lines.append("Where the busts come from (the section of the last decision that put chips in, top three):")
        lines.append("")
        for b, _ in ranked:
            lines.append(f"- {b}: {bust_rows[b] or '-'}")
        lines.append("")
        lines.append("Finish distribution (% of seats, 1st .. 8th):")
        lines.append("")
        lines.append("| bot | " + " | ".join(str(i) for i in range(1, 9)) + " | bust |")
        lines.append("|---|" + "---|" * 9)
        for b, s in ranked:
            dist = " | ".join(f"{100 * p:.0f}" for p in s["places"])
            lines.append(f"| {b} | {dist} | {100 * s['bust']:.0f} |")
        lines.append("")
        for b, s in ranked:
            lines.append(f"<details><summary>{b}: per-section table</summary>")
            lines.append("")
            lines.append("| section | share | vpip | raise | agg | all-in | bb/dec | sd win | busts |")
            lines.append("|---|---|---|---|---|---|---|---|---|")
            for nm in ROWS:
                r = s["rows"][nm]
                if not r["dec"] and not r["chips_bb"]:
                    continue
                lines.append(f"| {nm} | {_fmt(r['share'], True)} | {_fmt(r['vpip'], True)} | {_fmt(r['pfr'], True)} | "
                             f"{_fmt(r['agg'])} | {_fmt(r['allin'], True)} | "
                             f"{_fmt(r['bb_dec'], digits=3) if nm != 'blinds' else f'{r['chips_bb']:+.0f} total'} | "
                             f"{_fmt(r['sd_win'], True)} | {r['busts']:.0f} |")
            e = s["engine"]
            lines.append("")
            lines.append(f"{s['decisions']:.0f} decisions; net {s['net_bb']:+.0f} bb over the run; engine: "
                         f"{e.get('exceptions', 0)} exceptions, {e.get('illegal', 0)} illegal, "
                         f"{e.get('over_budget', 0)} timeouts, p99 {e.get('p99_us', 0):.0f} us.")
            lines.append("</details>")
            lines.append("")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python tools/skill_profile.py", description=__doc__.split("\n\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="play the bots in Hero's seat and record their decisions by section")
    r.add_argument("--field", required=True)
    r.add_argument("--bots", required=True, help="comma-separated registry names")
    r.add_argument("--seeds", default="0:100", help="lo:hi table seeds (default 0:100)")
    r.add_argument("--out", required=True)
    r.add_argument("--workers", type=int, default=3)
    r.add_argument("--mode", default="model", choices=("model", "strict", "measure"))
    r.add_argument("--chunk", type=int, default=25)
    r.add_argument("--seed", type=int, default=7)
    r.add_argument("--payouts", default=None, help="comma-separated payout table (default: Rules().payouts)")
    q = sub.add_parser("report", help="ranked leaderboards per section from saved runs")
    q.add_argument("dirs", nargs="+")
    q.add_argument("--fields", default=None)
    q.add_argument("--out", default=None)
    a = p.parse_args(argv)
    if a.cmd == "run":
        lo, hi = (int(x) for x in a.seeds.split(":"))
        bots = [b.strip() for b in a.bots.split(",") if b.strip()]
        for b in bots:
            B.field_names(f"{a.field}@{seat_name(a.field, b)}")  # fail early on a typo
        pay = [float(x) for x in a.payouts.split(",")] if a.payouts else None
        run(a.field, bots, lo, hi, Path(a.out), a.workers, a.mode, a.chunk, pay, a.seed)
        return 0
    text = report(a.dirs, a.fields.split(",") if a.fields else None)
    if a.out:
        Path(a.out).write_text(text + "\n")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
