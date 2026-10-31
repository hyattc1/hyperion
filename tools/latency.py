#!/usr/bin/env python
"""Decision latency of a bot, and of the adapter round trip, on random self-consistent Observations.

    python tools/latency.py --bot hero|cheap|module:attr --n 2000
                            [--adapter module:Class --native kit_a|kit_b|kit_c|module:func]
                            [--rules rules_tonight.json] [--seed 2026] [--p99-us 500]

Prints mean, p50, p99 and max in µs, the count over 1 ms, wall versus process CPU time for the run,
garbage collections during it, and the timer floor. Exit 1 if p99 exceeds --p99-us (default 500) for
the bot or for the round trip. The observations (and the kit-native states for the round trip) are
built before the clock starts and every call is timed alone into a preallocated list, so the harness
adds only the timer read, which is printed as the floor. `--native` is what turns an Observation back
into the kit's state: the three fake kits are built in; for the real kit write a 10-line
`build(obs) -> native` and pass `module:build`. Stdlib only, plus tests/strategy_helpers.py's generator.
"""
from __future__ import annotations

import argparse
import gc
import importlib
import json
import random
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperion.core.types import Observation, Rules  # noqa: E402


def load_attr(spec: str):
    mod, sep, attr = spec.partition(":")
    if not sep:
        raise SystemExit(f"expected module:attr, got {spec!r}")
    return getattr(importlib.import_module(mod), attr)


def load_bot(spec: str):
    if spec == "hero":
        from hyperion.strategy.hero import make_bot
        return make_bot()
    if spec == "cheap":
        from hyperion.strategy.hero import Hero
        return Hero.cheap()
    obj = load_attr(spec)
    return obj() if callable(obj) else obj


def load_rules(path: str | None) -> Rules:
    if not path:
        return Rules()
    from hyperion.tablegen import rules_from_dict
    with open(path) as f:
        return rules_from_dict(json.load(f))


def observations(n: int, seed: int, n_players: int, seat: int) -> list[Observation]:
    """n random decision points for `seat` (the adapter's fixed seat), from tests/strategy_helpers."""
    try:
        from tests.strategy_helpers import random_obs
    except ImportError as e:  # pragma: no cover - the repo layout guarantees it
        raise SystemExit(f"generator tests/strategy_helpers.random_obs not importable from {ROOT}: {e}")
    rng = random.Random(seed)
    out: list[Observation] = []
    while len(out) < n:
        o = random_obs(rng, n_players)
        if o.seat == seat:
            out.append(o)
    return out


def obs_to_state(obs: Observation) -> dict:
    """The fake kits' dealer state dict (hyperion/drills/fakekits/_table.py) for an Observation."""
    return {
        "hole": tuple(obs.hole), "board": tuple(obs.board), "street": obs.street, "seat": obs.seat,
        "button": obs.button, "stacks": list(obs.stacks), "bets": list(obs.bets), "in_hand": list(obs.in_hand),
        "pot": obs.pot, "to_call": obs.to_call, "min_raise": obs.min_raise, "max_raise": obs.max_raise,
        "legal": {k.value for k in obs.legal}, "hand_no": obs.hand_no, "blinds": tuple(obs.blinds), "history": [],
    }


def native_builder(spec: str):
    if spec == "kit_a":
        from hyperion.drills.fakekits.kit_a.kit import to_state
        return lambda obs: to_state(obs_to_state(obs))
    if spec == "kit_b":
        from hyperion.drills.fakekits.kit_b.kit import to_observation
        return lambda obs: to_observation(obs_to_state(obs))
    if spec == "kit_c":
        from hyperion.drills.fakekits.kit_c.kit import encode_decision
        return lambda obs: encode_decision(obs_to_state(obs), 100.0)
    return load_attr(spec)


class GcCounter:
    def __init__(self):
        self.counts = [0, 0, 0]

    def __call__(self, phase, info):
        if phase == "start":
            self.counts[info["generation"]] += 1


def measure(fn, items: list) -> dict:
    """Time fn(item) for every item; nothing but the call sits between the two timer reads."""
    n = len(items)
    times = [0.0] * n
    pc = time.perf_counter
    gcc = GcCounter()
    gc.callbacks.append(gcc)
    wall0, cpu0 = pc(), time.process_time()
    for i in range(n):
        x = items[i]
        t0 = pc()
        fn(x)
        times[i] = pc() - t0
    wall, cpu = pc() - wall0, time.process_time() - cpu0
    gc.callbacks.remove(gcc)
    return {"times": times, "wall": wall, "cpu": cpu, "gc": gcc.counts}


def stats(times: list[float]) -> dict:
    s = sorted(times)
    n = len(s)
    return {
        "n": n, "mean": sum(s) / n, "p50": s[n // 2], "p99": s[min(n - 1, int(0.99 * n))], "max": s[-1],
        "over_1ms": sum(1 for t in s if t > 1e-3),
    }


def line(label: str, m: dict) -> str:
    st = stats(m["times"])
    us = 1e6
    return (f"{label:<15} n={st['n']}  mean {st['mean'] * us:7.1f} µs  p50 {st['p50'] * us:7.1f}  p99 {st['p99'] * us:7.1f}"
            f"  max {st['max'] * us:8.1f}  over 1 ms: {st['over_1ms']} ({100 * st['over_1ms'] / st['n']:.2f}%)"
            f"  wall {m['wall'] * 1e3:.0f} ms  cpu {m['cpu'] * 1e3:.0f} ms  gc gen0/1/2 {m['gc'][0]}/{m['gc'][1]}/{m['gc'][2]}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--bot", default="hero", help="hero | cheap | module:attr (a Bot, or a factory returning one)")
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--warm", type=int, default=200, help="untimed calls before the run (default 200)")
    p.add_argument("--adapter", help="module:Class, an Adapter subclass to time the round trip through")
    p.add_argument("--native", default="kit_b", help="kit_a | kit_b | kit_c | module:func building the kit state")
    p.add_argument("--rules", help="Rules JSON (default Rules())")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--seat", type=int, default=0, help="our seat in every observation (default 0)")
    p.add_argument("--p99-us", type=float, default=500.0, help="exit 1 above this p99 (default 500)")
    a = p.parse_args(argv)

    rules = load_rules(a.rules)
    bot = load_bot(a.bot)
    obs = observations(a.n, a.seed, rules.n_players, a.seat)
    warm = obs[: min(a.warm, len(obs))]
    bot.new_table(rules, a.seat, rules.n_players)
    for o in warm:
        bot.act(o)
    floor = measure(lambda x: None, obs)
    runs = [("bot.act", measure(bot.act, obs))]
    if a.adapter:
        adapter = load_attr(a.adapter)(bot, rules)
        adapter.start(a.seat, rules.n_players, rules)
        build = native_builder(a.native)
        natives = [build(o) for o in obs]
        for x in natives[: len(warm)]:
            adapter.decide(x)
        runs.append(("adapter.decide", measure(adapter.decide, natives)))

    print(f"bot {a.bot}  rules {a.rules or 'default'}  seed {a.seed}  seat {a.seat}  warm {len(warm)}")
    for label, m in runs:
        print(line(label, m))
    fl = stats(floor["times"])
    extra = f"timer floor p50 {fl['p50'] * 1e6:.2f} µs (already inside every number above)"
    safe = getattr(bot, "safe", None)
    if safe is not None and hasattr(safe, "stats"):
        s = safe.stats()
        extra += f"; SafeBot errors {s['errors']}, overruns {s['overruns']}, worst {s['worst_ms']:.3f} ms"
    print(extra)
    worst = max(stats(m["times"])["p99"] for _, m in runs)
    if worst * 1e6 > a.p99_us:
        print(f"FAIL p99 {worst * 1e6:.1f} µs > {a.p99_us:g} µs")
        return 1
    print(f"OK p99 {worst * 1e6:.1f} µs <= {a.p99_us:g} µs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
