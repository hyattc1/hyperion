#!/usr/bin/env python
"""Decision latency of a bot, and of the adapter round trip, on random self-consistent Observations.

    python tools/latency.py [--bot ship|hybrid3_x|hero|cheap|module:attr] [--dials JSON] --n 2000
                            [--adapter module:Class --native kit_a|kit_b|kit_c|kit_d|module:func]
                            [--rules rules_tonight.json] [--variant NAME] [--seed 2026] [--p99-us 500]

`--bot ship` (the default) is the bot hyperion/ship.py ships, with its DIALS or `--dials`; any other BUILDERS
name there (hybrid3_x, hero, cheap) builds that bot with the same dials. Prints mean, p50, p99 and max in µs, the count over 1 ms, wall versus process CPU time for the run,
garbage collections during it, and the timer floor. Exit 1 if p99 exceeds --p99-us (default 500) for
the bot or for the round trip. The observations (and the kit-native states for the round trip) are
built before the clock starts and every call is timed alone into a preallocated list, so the harness
adds only the timer read, which is printed as the floor. `--native` is what turns an Observation back
into the kit's state: the four fake kits are built in (`kit_d_native` is the template for a kit with
namedtuple states); for the real kit write a 10-line `build(obs) -> native` and pass `module:build`.
The cards follow the rules (--rules, else --variant's): the hole-card count (the kept count after a discard
street), the board sizes and the deck (removed ranks left out), so a three-card game is timed on three-card
decisions and its variant tables, not on hold'em hands its tables do not hold (drill 6: 468 SafeBot errors).
Stdlib only, plus tests/strategy_helpers.py's generator for the betting state.
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


def load_bot(spec: str, dials: dict | None = None):
    """ship (hyperion/ship.py's SHIP), a BUILDERS name, or module:attr (a Bot, or a factory returning one)."""
    from hyperion import ship

    if spec == "ship":
        return ship.make_bot(None, dials)
    if spec in ship.BUILDERS:
        return ship.make_bot(spec, {} if dials is None else dials)
    obj = load_attr(spec)
    return obj() if callable(obj) else obj


def load_rules(path: str | None, variant: str | None = None) -> Rules:
    """--rules wins; else the catalog variant's Rules; else the default game."""
    if path:
        from hyperion.tablegen import rules_from_dict
        with open(path) as f:
            return rules_from_dict(json.load(f))
    if variant:
        from hyperion.drills import variants
        return variants.get(variant).rules
    return Rules()


def deal_for(rules: Rules, street: int, rng: random.Random) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """(hole, board) for `street` under the rules: rules.hole_cards before a discard street and extras["keep"]
    from it on, rules.board_sizes[street] board cards, from the rules' deck without removed ranks."""
    from hyperion.core.cards import deck_for

    ex = rules.extras or {}
    removed = set(ex.get("removed_ranks") or ())
    deck = [c for c in deck_for(rules) if (c >> 2) not in removed]
    rng.shuffle(deck)
    holes = rules.hole_cards
    if "discard_street" in ex and street >= int(ex["discard_street"]):
        holes = int(ex.get("keep", holes - 1))
    board = rules.board_sizes[min(street, len(rules.board_sizes) - 1)]
    return tuple(deck[:holes]), tuple(deck[holes:holes + board])


def observations(n: int, seed: int, n_players: int, seat: int, rules: Rules | None = None) -> list[Observation]:
    """n random decision points for `seat` (the adapter's fixed seat): the betting state from
    tests/strategy_helpers, the cards dealt for `rules` (default hold'em keeps the generator's own)."""
    try:
        from tests.strategy_helpers import random_obs
    except ImportError as e:  # pragma: no cover - the repo layout guarantees it
        raise SystemExit(f"generator tests/strategy_helpers.random_obs not importable from {ROOT}: {e}")
    rng = random.Random(seed)
    redeal = rules is not None and not _holdem_cards(rules)
    out: list[Observation] = []
    while len(out) < n:
        o = random_obs(rng, n_players)
        if o.seat != seat:
            continue
        if redeal:
            street = min(o.street, len(rules.board_sizes) - 1)
            o.hole, o.board = deal_for(rules, street, rng)
            o.street = street
        out.append(o)
    return out


def _holdem_cards(rules: Rules) -> bool:
    """True when the card rules are hold'em's (another payout or schedule does not change the deal)."""
    ex = rules.extras or {}
    return (rules.hole_cards == 2 and tuple(rules.board_sizes) == (0, 3, 4, 5) and not ex.get("removed_ranks")
            and "discard_street" not in ex)


def obs_to_state(obs: Observation) -> dict:
    """The fake kits' dealer state dict (hyperion/drills/fakekits/_table.py) for an Observation, history
    included (hyperion.drills.adapter.dealer_state)."""
    from hyperion.drills.adapter import dealer_state
    return dealer_state(obs)


def kit_d_native(obs: Observation) -> tuple:
    """(game_state, round_state, active) as KitDAdapter expects. A lone RoundState carries no pot, so the
    state hangs off a round-start state holding the pot's chips: the adapter's previous_state walk then
    recovers obs.pot. last_raise is chosen so raise_bounds() reproduces obs.min_raise."""
    from hyperion.core.types import card_str
    from hyperion.drills.fakekits.kit_d.kit import GameState, RoundState

    hands = [[] for _ in obs.stacks]
    hands[obs.seat] = [card_str(c) for c in obs.hole]
    pips, stacks, blinds = list(obs.bets), list(obs.stacks), tuple(obs.blinds)
    root_stacks = list(stacks)
    root_stacks[obs.seat] += obs.pot  # the pot's chips were in somebody's stack at round start; whose is moot
    root = RoundState(obs.button, 0, list(pips), root_stacks, hands, [], obs.seat, list(obs.in_hand), blinds,
                      blinds[1], None)
    last_raise = max(blinds[1], obs.min_raise - max(pips))
    rs = RoundState(obs.button, len(obs.board), pips, stacks, hands, [card_str(c) for c in obs.board], obs.seat,
                    list(obs.in_hand), blinds, last_raise, root)
    return GameState(0, 0.5, obs.hand_no + 1), rs, obs.seat


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
    if spec == "kit_d":
        return kit_d_native
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
    p.add_argument("--bot", default="ship", help="ship (hyperion/ship.py's bot, the default) | hybrid3_x | hero | "
                                                 "cheap | module:attr (a Bot, or a factory returning one)")
    p.add_argument("--dials", help="dials for the bot, JSON inline or a file (default: hyperion/ship.py's DIALS for "
                                   "ship, none for a named bot)")
    p.add_argument("--n", type=int, default=2000)
    p.add_argument("--warm", type=int, default=200, help="untimed calls before the run (default 200)")
    p.add_argument("--adapter", help="module:Class, an Adapter subclass to time the round trip through")
    p.add_argument("--native", default="kit_b", help="kit_a | kit_b | kit_c | kit_d | module:func building the kit state")
    p.add_argument("--rules", help="Rules JSON (default Rules())")
    p.add_argument("--variant", help="a catalog variant whose Rules to use when --rules is not given")
    p.add_argument("--seed", type=int, default=2026)
    p.add_argument("--seat", type=int, default=0, help="our seat in every observation (default 0)")
    p.add_argument("--p99-us", type=float, default=500.0, help="exit 1 above this p99 (default 500)")
    a = p.parse_args(argv)

    rules = load_rules(a.rules, a.variant)
    dials = None
    if a.dials:
        dials = json.loads(a.dials) if a.dials.lstrip().startswith("{") else json.loads(Path(a.dials).read_text())
    bot = load_bot(a.bot, dials)
    obs = observations(a.n, a.seed, rules.n_players, a.seat, rules)
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

    from hyperion import ship

    label = ship.describe(None, dials) if a.bot == "ship" else (ship.describe(a.bot, dials or {})
                                                               if a.bot in ship.BUILDERS else a.bot)
    print(f"bot {label}  rules {a.rules or (a.variant and 'variant ' + a.variant) or 'default'}  "
          f"hole cards {rules.hole_cards}  seed {a.seed}  seat {a.seat}  warm {len(warm)}")
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
