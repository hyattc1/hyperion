"""Tournament runner: many tables, aggregated per bot name, with confidence intervals.

`python -m hyperion.sim --tables 1000 --seed 1 --bots tag,nit,station,maniac --rotate`
`python -m hyperion.sim --tables 125 --seed 7 --field realistic --rotate`   (named 8-bot fields)
`python -m hyperion.sim --tables 300 --field realistic --variant short_deck`  (catalog entry: its Rules + hooks)
`python -m hyperion.sim --tables 300 --seed 11 --variant permuted_ranks --variant-seed 0`  (seeded entry, own seed)

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

from ..core.cards import hole_class
from ..core.types import ActionKind, Rules
from . import bestiary
from .bestiary import FIELDS, OPTIONAL_FIELDS, REGISTRY, BotUnavailable, field_names, make_bot
from .engine import BUDGET_NS, BotStats, find_safe, play_table


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


class BustTracer:
    """Wraps one bot and remembers, per hand, its last decision that put chips in. When the bot
    busts, that decision is the one that did it: street, module and sub-decision (hero exposes
    `core.last_path` and each module's `last`, e.g. `pushfold.call_shove`), kind, how much of the stack
    it cost, stack in blinds, players alive, and who was in the pot. Two attribution flags: `inner_error`
    when the bot's SafeBot swallowed an exception during that act (the fallback acted, not the module),
    and `overran` when the call took longer than the engine's budget (in strict mode the engine then
    checked or folded, whatever the bot returned)."""

    def __init__(self, inner, name: str, seating: Sequence[str], sink: list):
        self.inner = inner
        self.name = name
        self.seating = list(seating)
        self.sink = sink
        self.seat = 0
        self.last = None
        self.start = None
        self.hand_no = -1
        self.safe = None

    def new_table(self, rules, seat, n):
        self.seat = seat
        self.inner.new_table(rules, seat, n)
        self.safe = find_safe(self.inner)

    def _path(self) -> str:
        impl = getattr(self.inner, "impl", None)
        core = getattr(impl, "core", None)
        path = getattr(core, "last_path", "") or type(impl or self.inner).__name__
        sub = getattr(getattr(core, path, None), "last", "") if core is not None else ""
        return f"{path}.{sub}" if sub else path

    def act(self, obs):
        me = self.seat
        if obs.hand_no != self.hand_no:
            self.hand_no = obs.hand_no
            self.start = obs.stacks[me] + obs.bets[me]
            self.last = None
        safe = self.safe
        err0 = safe.errors if safe is not None else 0
        t0 = time.perf_counter_ns()
        a = self.inner.act(obs)
        dt = time.perf_counter_ns() - t0
        k = a.kind
        if k is ActionKind.CALL or k is ActionKind.RAISE:
            total = obs.stacks[me] + obs.bets[me]
            put = (obs.to_call if k is ActionKind.CALL else a.amount - obs.bets[me])
            bb = obs.blinds[1] or 1
            shover = any(obs.in_hand[s] and obs.stacks[s] == 0 and obs.bets[s] >= max(obs.bets) > 0
                         for s in range(len(obs.stacks)) if s != me)
            inner_error = safe is not None and safe.errors > err0
            self.last = {
                "hand": obs.hand_no, "street": obs.street, "path": ("safe_error:" if inner_error else "") + self._path(),
                "kind": k.value, "inner_error": inner_error, "overran": dt > BUDGET_NS,
                "frac": put / obs.stacks[me] if obs.stacks[me] else 1.0, "bb": self.start / bb, "to_call_bb": obs.to_call / bb,
                "alive": obs.players_left, "cls": hole_class(obs.hole) if len(obs.hole) == 2 else "?",
                "n_opps": sum(obs.in_hand) - 1, "facing_shove": shover,
                "opps": tuple(sorted(self.seating[s] for s in range(len(obs.stacks)) if obs.in_hand[s] and s != me)),
            }
        return a

    def hand_end(self, result):
        self.inner.hand_end(result)
        if self.start is not None and result.hand_no == self.hand_no and result.deltas[self.seat] <= -self.start:
            rec = dict(self.last) if self.last else {"hand": result.hand_no, "street": -1, "path": "none", "kind": "blind",
                                                     "frac": 1.0, "bb": 0.0, "to_call_bb": 0.0, "alive": 0, "cls": "?",
                                                     "n_opps": 0, "facing_shove": False, "opps": (),
                                                     "inner_error": False, "overran": False}
            self.sink.append(rec)


def format_busts(busts: list, seats: int) -> str:
    """Aggregate the tracer's records: where and how the busts happened."""
    if not busts:
        return "no busts traced"
    from collections import Counter
    n = len(busts)
    out = [f"{n} busts in {seats} seats ({100 * n / seats:.1f}%)"]
    n_err = sum(1 for b in busts if b.get("inner_error"))
    n_over = sum(1 for b in busts if b.get("overran"))
    out.append(f"  fatal decisions attributed to the module that acted; {n_err} had an inner error swallowed by "
               f"SafeBot (its fallback acted), {n_over} ran over the 1 ms budget (strict mode: the engine acted)")

    def table(title, key, top=12):
        c = Counter(key(b) for b in busts)
        out.append(f"  by {title}:")
        for k, v in c.most_common(top):
            out.append(f"    {str(k):<42} {v:>5} {100 * v / n:5.1f}%")

    streets = {-1: "none", 0: "pre", 1: "flop", 2: "turn", 3: "river"}
    table("module / street / kind", lambda b: f"{b['path']}/{streets.get(b['street'], b['street'])}/{b['kind']}"
          + ("/vs-shove" if b["facing_shove"] else ""))
    table("stack in bb at hand start", lambda b: "<=5" if b["bb"] <= 5 else "<=12" if b["bb"] <= 12 else "<=25"
          if b["bb"] <= 25 else "<=50" if b["bb"] <= 50 else ">50")
    table("players alive", lambda b: b["alive"])
    table("share of stack put in by the fatal decision", lambda b: "<25%" if b["frac"] < 0.25 else "<50%"
          if b["frac"] < 0.5 else "<100%" if b["frac"] < 0.999 else "all-in")
    table("opponents in the pot", lambda b: ",".join(b["opps"]))
    table("hole class (preflop busts)", lambda b: b["cls"] if b["street"] == 0 else "(postflop)")
    bucket = lambda bb: "<=5" if bb <= 5 else "<=12" if bb <= 12 else "<=25" if bb <= 25 else "<=50" if bb <= 50 else ">50"  # noqa: E731
    table("module / kind x stack depth", lambda b: f"{b['path']}/{b['kind']} @{bucket(b['bb'])}bb")
    table("module x opponents in the pot", lambda b: f"{b['path']} vs {','.join(b['opps'])}")
    return "\n".join(out)


@dataclass
class Report:
    bots: dict[str, BotReport]
    tables: int
    hands: int
    seconds: float
    busts: list = field(default_factory=list)

    @property
    def hands_per_second(self) -> float:
        return self.hands / self.seconds if self.seconds > 0 else 0.0

    def format(self) -> str:
        n_places = max((len(b.places) for b in self.bots.values()), default=8)
        w = max(10, max((len(nm) for nm in self.bots), default=10))
        head = (f"{'bot':<{w}} {'n':>5} {'pts':>6} {'±95%':>5}  "
                + " ".join(f"{'p' + str(i + 1):>4}" for i in range(n_places))
                + f"  {'bust%':>5} {'tmo':>5} {'exc':>5} {'ill':>5} {'safe_err':>8} {'safe_over':>9} "
                f"{'p50us':>6} {'p99us':>6} {'maxus':>6} {'1st_us':>7}")
        lines = [head]
        swallowed = 0
        for name, b in sorted(self.bots.items(), key=lambda kv: -kv[1].mean):
            dist = " ".join(f"{100 * c / b.seats:4.0f}" if b.seats else "   -" for c in b.places)
            st = b.stats
            swallowed += st.safe_err
            lines.append(
                f"{name:<{w}} {len(b.samples):>5} {b.mean:>6.3f} {b.ci95:>5.3f}  {dist}  "
                f"{100 * b.bust_rate:>5.1f} {st.over_budget:>5} {st.exceptions:>5} {st.illegal:>5} "
                f"{st.safe_err:>8} {st.safe_over:>9} "
                f"{st.percentile_us(0.5):>6.0f} {st.percentile_us(0.99):>6.0f} {st.max_ns / 1000:>6.0f} "
                f"{st.first_max_ns / 1000:>7.0f}"
            )
        lines.append(
            f"{self.tables} tables, {self.hands} hands in {self.seconds:.1f}s: "
            f"{self.hands_per_second:,.0f} hands/s. p1..pN are finish-position percentages; "
            f"1st_us is the slowest first call of a table; safe_err / safe_over are exceptions and deadline "
            f"overruns a SafeBot swallowed inside the bot (the engine's exc column cannot see them)."
        )
        if swallowed:
            lines.append(f"WARNING: {swallowed} inner exceptions were swallowed by SafeBot and played as a check or "
                         f"fold; run with --trace-busts BOT or look at hero.safe.stats() before trusting the points.")
        return "\n".join(lines)


def load_rules(spec: str) -> Rules:
    """'default' or a path to a json object whose keys are Rules fields."""
    if spec == "default":
        return Rules()
    with open(spec) as f:
        raw = json.load(f)
    tup = lambda v: tuple(tuple(x) if isinstance(x, list) else x for x in v)  # noqa: E731
    for k in ("board_sizes", "rank_order", "payouts", "blind_levels", "ante_per_level"):
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
    hero_config: Optional[dict] = None,
    trace_busts: Optional[str] = None,
    table_offset: int = 0,
    variant=None,
) -> Report:
    """`variant` is a hyperion.drills.variants.Variant (catalog entry): a fresh hooks object is built per
    table because hooks keep per-hand state. Its Rules are used unless `rules` is given."""
    if variant is not None and rules is None:
        rules = variant.rules
    rules = rules if rules is not None else Rules()
    bestiary.HERO_CONFIG = hero_config
    n = rules.n_players
    names = [nm.strip().lower() for nm in names if nm.strip()]
    if not names:
        raise ValueError("need at least one bot name")
    for nm in names:
        make_bot(nm)  # fail early on a typo
    reports = {nm: BotReport(nm, places=[0] * n, stats=BotStats(nm)) for nm in names}
    rotations = range(n) if rotate else (0,)
    hands = 0
    busts: list = []
    t0 = time.perf_counter()
    for t in range(table_offset, table_offset + tables):
        table_seed = seed * 1_000_003 + t
        rng = random.Random(table_seed)
        seating = list(names[:n])
        while len(seating) < n:
            seating.append(rng.choice(names))
        rng.shuffle(seating)
        per_name_points: dict[str, list[float]] = {nm: [] for nm in names}
        for rot in rotations:
            bots = [make_bot(nm, seed=table_seed * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
            if trace_busts:
                bots = [BustTracer(b, nm, seating, busts) if nm == trace_busts else b for b, nm in zip(bots, seating)]
            stats = [reports[nm].stats for nm in seating]
            hooks = variant.new_hooks() if variant is not None else None
            res = play_table(bots, rules, seed=table_seed, rotation=rot, mode=mode, stats=stats, stacks=stacks,
                             variant=hooks)
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
    return Report(reports, tables * len(rotations), hands, time.perf_counter() - t0, busts)


def load_hero_config(spec: Optional[str]) -> Optional[dict]:
    """A JSON object of dotted Config overrides, inline or a path to a file; None for the defaults."""
    if not spec:
        return None
    if spec.lstrip().startswith("{"):
        return json.loads(spec)
    with open(spec) as f:
        return json.load(f)


def main(argv: Optional[Sequence[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.sim", description="Run 8-max sit-and-gos.")
    p.add_argument("--tables", type=int, default=100, help="table seeds to play (default 100)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--bots", default="hero,tag,nit,station,maniac,naive,random,allin",
                   help="comma-separated names from the registry; fewer than seats fills with copies")
    p.add_argument("--field", default=None,
                   help="a named 8-bot field from the bestiary; replaces --bots (optional fields such as `public` "
                        "need their bots enabled, e.g. HYPERION_MICROHOLDEM for `micro`); <field>@<bot> puts <bot> in "
                        "Hero's seat, and <field>@ship the bot hyperion/ship.py ships, with --dials")
    p.add_argument("--dials", default=None, help="dials for `ship`: JSON (inline or file) or recipe names such as "
                                                 "survival+passive (default hyperion/ship.py's DIALS)")
    p.add_argument("--rotate", action="store_true", help="play all rotations of each deal (duplicate)")
    p.add_argument("--mode", choices=("strict", "measure", "model"), default="strict",
                   help="strict: fold calls over 1 ms on the wall clock; measure: never; model: the deterministic timeout "
                        "model (bots that report a modelled cost are folded by it, nothing by the wall clock)")
    p.add_argument("--rules", default="default", help="'default' or a json file of Rules fields")
    p.add_argument("--variant", default=None, metavar="NAME",
                   help="a hyperion.drills.variants catalog entry: plays its Rules (unless --rules is a file) and hooks")
    p.add_argument("--variant-seed", type=int, default=None, metavar="N",
                   help="seed for a seeded variant (permuted_ranks' permutation); default --seed, so the table seed "
                        "also picks the permutation unless this is given")
    p.add_argument("--profile", action="store_true", help="print the hottest functions afterwards")
    p.add_argument("--list", action="store_true", help="list bot names and exit")
    p.add_argument("--hero-config", default=None, help="JSON (inline or file) of dotted hero Config overrides")
    p.add_argument("--trace-busts", default=None, metavar="BOT", help="report where this bot's busts happen")
    a = p.parse_args(argv)
    if a.list:
        for nm, cls in REGISTRY.items():
            print(f"{nm:<20} {cls.__name__:<20} {(cls.__doc__ or '').strip().splitlines()[0]}")
        print()
        for nm, members in FIELDS.items():
            print(f"field {nm:<14} {','.join(members)}")
        return 0
    rules = load_rules(a.rules)
    variant = None
    if a.variant:
        from ..drills import variants as _variants

        variant = _variants.get(a.variant, seed=a.seed if a.variant_seed is None else a.variant_seed)
        if a.rules == "default":
            rules = variant.rules
    if "ship" in (a.field or "").split("@")[-1:] or "ship" in [b.strip() for b in a.bots.split(",")] or a.dials:
        from ..ship import parse_dials, register_sim  # the night's bot as seat `ship`, built as the entry builds it

        print(f"ship = {register_sim(parse_dials(a.dials))}")
    try:
        names = field_names(a.field) if a.field else a.bots.split(",")
    except BotUnavailable as e:  # an optional field whose bot is not enabled: say which variable to set
        p.error(str(e).strip("'\""))
    except KeyError as e:
        p.error(str(e).strip("'\""))
    prof = cProfile.Profile() if a.profile else None
    if prof:
        prof.enable()
    report = run_tournament(names, a.tables, a.seed, a.rotate, a.mode, rules,
                            hero_config=load_hero_config(a.hero_config), trace_busts=a.trace_busts,
                            variant=variant)
    if prof:
        prof.disable()
    print(report.format())
    if a.trace_busts:
        print(format_busts(report.busts, report.bots[a.trace_busts].seats))
    if prof:
        pstats.Stats(prof, stream=sys.stdout).sort_stats("tottime").print_stats(15)
    return 0
