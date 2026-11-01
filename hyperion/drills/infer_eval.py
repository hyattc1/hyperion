"""How much of the missing action log the inference wins back, and whether every entry it emits is true.

    python -m hyperion.drills.infer_eval --fields realistic,night --bots hero,hybrid3_x --seeds 200 --rotate \
        --workers 2 --out infer.json          # points: the three cases, paired on the same deals
    python -m hyperion.drills.infer_eval --check 40 --fields realistic --bots hybrid3_x   # precision and recall

Cases, each the bot in Hero's seat of the field, model mode, the same table seeds and rotations:
  nolog         what a kit with no action log gives through a reference adapter, as tools/gate.py --kit-log no did
                before the inference (hyperion.drills.adapter.NoLogSeat): this street's raises rebuilt from the bets,
                a hand end with only our own chip change
  infer         the same bare states through the inference as the adapters run it (hyperion.drills.infer_history
                InferSeat): the log rebuilt from the states; when a seat owed chips after our last reply, the hand
                end waits for the next hand's first state, whose stacks settle the folds and every seat's chip change
  infer_all     infer, holding every hand end we acted in (Adapter.hold_all): every seat's chip change every hand
  infer_none    the same, with the hand end at once: our own chip change and the log up to our last reply
  infer_stacks  the hand end lists every seat's chip change (a kit that says so)
  infer_shown   infer_stacks, and the kit shows the hands at showdown
  full          the engine's own log at every decision and hand end
The bot plays with panic_after 1e9 (and soft_us 1e6 on the hybrids), so its play does not follow the host's clock.

--check plays the full-log table and, at each of our decisions and hand ends, rebuilds the log from the bare state
and compares: precision over emitted entries (any false entry is a bug), recall by street.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import random
import sys
import time
from collections import Counter

QUIET = {"panic_after": 10 ** 9, "soft_us": 1e6}
CASES = ("nolog", "infer_none", "infer", "infer_all", "infer_stacks", "infer_shown", "full")


def _name(bot: str) -> str:
    """`ship` is the bot hyperion/ship.py names."""
    if bot == "ship":
        from hyperion import ship

        return ship.SHIP
    return bot


def _dials(bot: str) -> dict:
    return dict(QUIET) if _name(bot) not in ("hero", "cheap") else {"panic_after": 10 ** 9}


def seating_for(names, n, table_seed):
    rng = random.Random(table_seed)
    seating = list(names[:n])
    while len(seating) < n:
        seating.append(rng.choice(names))
    rng.shuffle(seating)
    return seating


def wrap(case: str, bot):
    from hyperion.drills.adapter import NoLogSeat
    from hyperion.drills.infer_history import InferSeat

    if case == "full":
        return bot
    if case == "nolog":
        return NoLogSeat(bot)
    if case == "infer_all":
        return InferSeat(bot, final="next", hold_all=True)
    return InferSeat(bot, final={"infer": "next", "infer_none": "none", "infer_stacks": "stacks",
                                 "infer_shown": "shown"}[case])


def job(args):
    """One (field, bot, case) over a chunk of seeds: {seed: mean points over its rotations}."""
    field, bot, case, seeds, base_seed, rotate = args
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table

    rules = Rules()
    names = B.field_names(field)
    out = {}
    for t in seeds:
        ts = base_seed * 1_000_003 + t
        seating = seating_for(names, rules.n_players, ts)
        g = seating.index("hero")
        pts = []
        for rot in (range(rules.n_players) if rotate else (0,)):
            bots = [B.make_bot(nm, seed=ts * 64 + rot * 8 + s) for s, nm in enumerate(seating)]
            bots[g] = wrap(case, ship.make_bot(_name(bot), _dials(bot), seed=ts * 64 + rot * 8 + g))
            res = play_table(bots, rules, seed=ts, rotation=rot, mode="model")
            pts.append(res.points[g])
        out[t] = sum(pts) / len(pts)
    return field, bot, case, out


def mean_ci(xs):
    n = len(xs)
    if n < 2:
        return (xs[0] if xs else 0.0), 0.0
    m = sum(xs) / n
    return m, 1.96 * math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1) / n)


def report(res: dict, cases) -> str:
    lines = []
    for key in sorted(res):
        field, bot = key.split("|")
        per = res[key]
        have = [c for c in cases if c in per]
        seeds = sorted(set.intersection(*(set(per[c]) for c in have))) if have else []
        if not seeds:
            continue
        lines.append(f"{field} / {bot}: {len(seeds)} seeds")
        for c in have:
            m, ci = mean_ci([per[c][s] for s in seeds])
            lines.append(f"  {c:<13} {m:6.3f} ± {ci:.3f}")
        if "nolog" in per and "full" in per:
            gap = [per["full"][s] - per["nolog"][s] for s in seeds]
            gm, gci = mean_ci(gap)
            lines.append(f"  full - nolog  {gm:+.3f} ± {gci:.3f}   (what the missing log costs)")
            for c in have:
                if c.startswith("infer"):
                    d = [per[c][s] - per["nolog"][s] for s in seeds]
                    dm, dci = mean_ci(d)
                    left = [per["full"][s] - per[c][s] for s in seeds]
                    lm, lci = mean_ci(left)
                    share = f", {100 * dm / gm:.0f}% of the gap" if abs(gm) > 1e-9 else ""
                    lines.append(f"  {c} - nolog {dm:+.3f} ± {dci:.3f} recovered{share}; "
                                 f"full - {c} {lm:+.3f} ± {lci:.3f}")
    return "\n".join(lines)


# ------------------------------------------------------------------ --check: precision and recall on real tables

def _same(x, y) -> bool:
    from hyperion.core.types import ActionKind

    return x.kind is y.kind and (x.kind is not ActionKind.RAISE or x.amount == y.amount)


class _Streets:
    """Wraps every seat to note the street of each history index (the entry a seat's act appends)."""

    def __init__(self, bot, book):
        self.bot, self.book = bot, book

    def new_table(self, r, s, n):
        self.bot.new_table(r, s, n)

    def act(self, obs):
        self.book.setdefault(obs.hand_no, {})[len(obs.history)] = obs.street
        return self.bot.act(obs)

    def hand_end(self, r):
        self.bot.hand_end(r)

    def variant_decide(self, p):
        return self.bot.variant_decide(p)


class _Checker:
    """Our seat on a full-log table: rebuilds the log from the bare state alongside and scores it."""

    def __init__(self, bot, st: Counter, book: dict, final: str, rules):
        from hyperion.drills.infer_history import HistoryInference

        self.bot, self.st, self.book, self.final = bot, st, book, final
        self.inf = HistoryInference(rules)
        self.rules = rules
        self.pending = None

    def new_table(self, r, s, n):
        self.inf.new_table(r)
        self.bot.new_table(r, s, n)

    def act(self, obs):
        from hyperion.drills.infer_history import finals_from_next

        bare = dataclasses.replace(obs, history=[], extras={})
        if self.pending is not None:  # final "next": the hand end settled by this state's stacks
            res, self.pending = self.pending, None
            finals = finals_from_next(bare, self.rules) if obs.hand_no == res.hand_no + 1 else None
            got = self.inf.hand_end(final_stacks=finals, hand_no=res.hand_no)
            self._score(got, res.history, res.hand_no, "hand_end")
        t0 = time.perf_counter_ns()
        o2 = self.inf.observe(bare)
        self.st["ns"].append(time.perf_counter_ns() - t0)
        self._score(o2.history, obs.history, obs.hand_no, "decision")
        a = self.bot.act(obs)
        self.inf.acted(a.clamp(obs))
        return a

    def hand_end(self, res):
        if self.final == "next":
            if self.pending is not None:
                old, self.pending = self.pending, None
                self._score(self.inf.hand_end(hand_no=old.hand_no), old.history, old.hand_no, "hand_end")
            self.pending = res
            self.bot.hand_end(res)
            return
        kw = {"hand_no": res.hand_no}
        if self.final in ("stacks", "shown"):
            kw["deltas"] = res.deltas
        if self.final == "shown":
            kw["shown"] = dict(res.showdown)
        self._score(self.inf.hand_end(**kw), res.history, res.hand_no, "hand_end")
        self.bot.hand_end(res)

    def _score(self, got, true, hand, where):
        st = self.st
        for i, (s, a) in enumerate(got):
            st[where, "emitted"] += 1
            if not (i < len(true) and true[i][0] == s and _same(true[i][1], a)):
                st[where, "wrong"] += 1
                if len(st["bad"]) < 5:
                    st["bad"].append((where, hand, i, [(x, y.kind.value, y.amount) for x, y in got],
                                      [(x, y.kind.value, y.amount) for x, y in true]))
        streets = self.book.get(hand, {})
        for i in range(len(true)):
            k = streets.get(i, -1)
            st[where, "true", k] += 1
            st[where, "got", k] += i < len(got)

    def variant_decide(self, p):
        return self.bot.variant_decide(p)


def check(field: str, bot: str, tables: int, seed: int, final: str, variant: str | None = None) -> Counter:
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table

    var = None
    rules = Rules()
    if variant:
        from hyperion.drills import variants

        var = variants.get(variant, seed=seed)
        rules = var.rules
    st: Counter = Counter()
    st["ns"], st["bad"] = [], []
    names = B.field_names(field)
    for t in range(tables):
        ts = seed * 1_000_003 + t
        seating = seating_for(names, rules.n_players, ts)
        g = seating.index("hero")
        book: dict = {}
        bots = [B.make_bot(nm, seed=ts * 64 + s) for s, nm in enumerate(seating)]
        bots[g] = ship.make_bot(_name(bot), _dials(bot), seed=ts * 64 + g)
        bots = [_Streets(b, book) for b in bots]
        bots[g] = _Checker(bots[g], st, book, final, rules)
        play_table(bots, rules, seed=ts, mode="model", variant=var.new_hooks() if var else None)
    return st


def check_report(st: Counter) -> str:
    ns = sorted(st["ns"]) or [0]
    lines = []
    for where in ("decision", "hand_end"):
        e, w = st[where, "emitted"], st[where, "wrong"]
        rec = []
        for k, name in ((0, "preflop"), (1, "flop"), (2, "turn"), (3, "river")):
            tt = st[where, "true", k]
            if tt:
                rec.append(f"{name} {100 * st[where, 'got', k] / tt:.1f}%")
        lines.append(f"{where:<9} emitted {e:>7}, false {w}, precision {100 * (1 - w / max(1, e)):.2f}%; "
                     f"recall {', '.join(rec)}")
    p50, p99 = ns[len(ns) // 2] / 1000, ns[int(0.99 * (len(ns) - 1))] / 1000
    lines.append(f"cost a decision: p50 {p50:.1f} us, p99 {p99:.1f} us")
    for b in st["bad"]:
        lines.append(f"FALSE ENTRY {b}")
    return "\n".join(lines)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fields", default="realistic,night")
    p.add_argument("--bots", default="hero,hybrid3_x", help="hyperion/ship.py BUILDERS names; ship = the switch's")
    p.add_argument("--cases", default="nolog,infer,full")
    p.add_argument("--seeds", type=int, default=200)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--rotate", action="store_true", help="all eight rotations of each deal")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--chunk", type=int, default=10)
    p.add_argument("--out", help="results JSON (resumed if it exists)")
    p.add_argument("--check", type=int, metavar="TABLES", help="precision and recall over this many tables instead")
    p.add_argument("--final", default="next", choices=("next", "none", "stacks", "shown"),
                   help="--check: what the hand end shows (next: nothing, settled by the next hand's first state)")
    p.add_argument("--variant")
    a = p.parse_args(argv)
    fields, bots = a.fields.split(","), a.bots.split(",")
    if a.check:
        for f in fields:
            for b in bots:
                print(f"{f} / {b}, {a.check} tables, hand end shows {a.final}")
                print(check_report(check(f, b, a.check, a.seed, a.final, a.variant)))
        return 0
    cases = a.cases.split(",")
    res: dict = {}
    if a.out and os.path.exists(a.out):
        with open(a.out) as fh:
            raw = json.load(fh)
        res = {k: {c: {int(s): v for s, v in d.items()} for c, d in per.items()} for k, per in raw.items()}
    jobs = []
    for f in fields:
        for b in bots:
            for c in cases:
                done = res.get(f"{f}|{b}", {}).get(c, {})
                for lo in range(0, a.seeds, a.chunk):
                    seeds = [s for s in range(lo, min(a.seeds, lo + a.chunk)) if s not in done]
                    if seeds:
                        jobs.append((f, b, c, seeds, a.seed, a.rotate))
    t0 = time.time()
    from multiprocessing import Pool

    with Pool(a.workers) as pool:
        for i, (f, b, c, out) in enumerate(pool.imap_unordered(job, jobs)):
            res.setdefault(f"{f}|{b}", {}).setdefault(c, {}).update(out)
            if a.out:
                with open(a.out + ".tmp", "w") as fh:
                    json.dump(res, fh)
                os.replace(a.out + ".tmp", a.out)
            print(f"{i + 1}/{len(jobs)} {f} {b} {c} ({time.time() - t0:.0f} s)", file=sys.stderr, flush=True)
    print(report(res, [c for c in CASES if any(c in per for per in res.values())]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
