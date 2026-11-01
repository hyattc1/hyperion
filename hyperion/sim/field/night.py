"""The `night` fields: seven opponents drawn per table from a weighted pool that is our guess at the real room.

Why a drawn field. The real room is whatever the student teams build in the hour, seated 8 at a time at random, so no
fixed 8-bot field looks like it. Here each table seats Hero's seat plus seven distinct opponents drawn from the pool
with the table seed alone. Seat seven slots, `night.1` .. `night.7`, each a PoolSeat that builds the k-th drawn bot.

**The weights are a guess, stated here so they can be argued with** (decisions entry "Night field and skill
profile"). Share of the seven opponent seats, and why:

| group | night | night_hard | members |
|---|---|---|---|
| one-hour agent builds | 40% | 45% | the four persona bots (agent_*) and the two Track B bots (trackb3, trackb5) |
| weak or broken | 30% | 10% | Monte Carlo bots that time out, bots that break mid-table, placeholders, crashers |
| decent archetypes | 15% | 15% | tag, pushfold, loose_aggro |
| strong teams | 15% | 30% | rival1, rival2, rival3 |

- *One-hour agent builds are the room.* Nearly every team has a coding agent and one hour. Most ship what the agent
  builds by default, or what the team tells it to build (Monte Carlo equity, charts, push/fold): 2.8 seats a table.
- *Weak or broken is the 1 ms clock and the hour.* Pure-Python Monte Carlo overruns 1 ms postflop, state that grows
  breaks a bot mid-table, and a team that ran out of time ships a placeholder. Monte Carlo bots weigh most: they are
  what most students write. About 2.1 seats a table.
- *Decent* (a chart TAG, a push/fold chart, a loose student) and *strong* (teams with poker knowledge, our red-team
  rivals 1 to 3, each built blind in 35-41 minutes) are about one seat each.
- `night_hard` is the room we would hate: strong teams twice as heavy (two of three rivals at most tables), the
  persona bots twice as heavy as the Track B bots inside their group, and few broken bots to feed on.

Not in any pool: Hero and its presets (self-play), the hybrids and composites (candidates), rival 4 and rival 5 (the
judges), and anything optional (`micro`).

**Drawing.** For each of the seven seats: pick a group with probability proportional to its weight among the groups
that still have an undrawn member, then a member of it proportional to its weight; no bot is drawn twice. A group that
runs out passes its share to the others pro rata. The generator is seeded with "<pool>:<table seed>" (string seeds are
hashed with SHA-512, so the draw is the same in every process and Python build). A member that is not registered is
skipped, so the persona bots join `night` and `night_hard` on the commit that registers them; `night0` never has them
(the stand-in version shipped before they froze, kept so runs made on it can be repeated).

**Pairing.** A PoolSeat reads the table seed from the seat seed the runner gives every bot (table_seed * 64 +
rotation * 8 + seat; tools/gate.py uses table_seed * 64 + seat), so all rotations of a deal and every `night@<bot>`
swap see the same seven opponents with the same seeds, in the same seats: `night@X - night@Y` is paired seed for seed,
as `judge@X - judge` is. A caller that seeds bots another way gets a deterministic draw, not the runner's.

**Reports.** The runner aggregates by seat name, so `night.3` mixes whatever sat in slot 3. Read the Hero seat; for
the opponents use `opponents()` here or tools/profile.py.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional

AGENT, WEAK, DECENT, STRONG = "one-hour agent builds", "weak or broken", "decent", "strong teams"

PERSONAS = ("agent_default", "agent_montecarlo", "agent_charts", "agent_pushfold")
TRACK_B = ("trackb3", "trackb5")
_WEAK_MEMBERS = (
    ("montecarlo", 3.0),  # honest 200 rollouts: times out on most postflop decisions
    ("montecarlo30", 3.0),  # Monte Carlo that times out on 30% of postflop decisions
    ("naive", 2.0),  # the 40-minute equity bot
    ("timeout_then_recover", 2.0),  # breaks for good at hand 30..120
    ("timeout_burst", 1.0),  # breaks in outages and recovers
    ("station", 1.0),
    ("random", 1.0),
    ("maniac", 1.0),
    ("nit", 1.0),
    ("allin", 0.5),
    ("timeout", 0.5),  # every decision over the clock: a dead seat
    ("crasher", 0.5),  # every decision raises: a dead seat
)
_DECENT_MEMBERS = (("tag", 1.0), ("pushfold", 1.0), ("loose_aggro", 1.0))
_STRONG_MEMBERS = (("rival1", 1.0), ("rival2", 1.0), ("rival3", 1.0))


@dataclass(frozen=True)
class Pool:
    """`groups`: (group, weight, ((bot, weight), ...)) in a fixed order; `seats`: how many distinct bots one table
    draws; `exclude`: members never drawn from this pool."""

    name: str
    groups: tuple
    seats: int = 7
    exclude: tuple = ()


def _night_groups(agent: float, weak: float, decent: float, strong: float, persona_w: float = 1.0) -> tuple:
    return (
        (AGENT, agent, tuple((p, persona_w) for p in PERSONAS) + tuple((t, 1.0) for t in TRACK_B)),
        (WEAK, weak, _WEAK_MEMBERS),
        (DECENT, decent, _DECENT_MEMBERS),
        (STRONG, strong, _STRONG_MEMBERS),
    )


POOLS: dict[str, Pool] = {
    "night": Pool("night", _night_groups(0.40, 0.30, 0.15, 0.15)),
    "night_hard": Pool("night_hard", _night_groups(0.45, 0.10, 0.15, 0.30, persona_w=2.0)),
    # the stand-in version committed before the persona bots froze: the same weights with no persona bot
    "night0": Pool("night0", _night_groups(0.40, 0.30, 0.15, 0.15), exclude=PERSONAS),
    # judge2_night: rival 5 sits in one seat (listed in the field itself) and these six are drawn around it
    "judge2_night": Pool("judge2_night", _night_groups(0.40, 0.30, 0.15, 0.15), seats=6),
}


def seat_names(pool: str) -> tuple[str, ...]:
    """The field entries for a pool's drawn seats: ('night.1', ..., 'night.7')."""
    return tuple(f"{pool}.{k}" for k in range(1, POOLS[pool].seats + 1))


def parse_seat(name: str) -> Optional[tuple[str, int]]:
    """'night.3' -> ('night', 3); None for anything that is not a pool seat."""
    pool, dot, slot = name.rpartition(".")
    if not dot or pool not in POOLS or not slot.isdigit():
        return None
    k = int(slot)
    return (pool, k) if 1 <= k <= POOLS[pool].seats else None


def _registered() -> set:
    from ..bestiary import REGISTRY

    return set(REGISTRY)


def members(pool: str) -> tuple:
    """The pool's groups with only the members that can be built now: ((group, weight, ((bot, w), ...)), ...)."""
    p = POOLS[pool]
    reg = _registered()
    return tuple((g, w, tuple((b, bw) for b, bw in ms if b in reg and b not in p.exclude)) for g, w, ms in p.groups)


_CACHE: dict = {}


def _pick(rng: random.Random, weights: list) -> int:
    x = rng.random() * sum(weights)
    for i, w in enumerate(weights):
        x -= w
        if x < 0:
            return i
    return len(weights) - 1


def draw(pool: str, table_seed: int) -> tuple[str, ...]:
    """The distinct bots one table of `pool` seats, in slot order, from the table seed alone."""
    groups = members(pool)
    key = (pool, table_seed, groups)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    rng = random.Random(f"{pool}:{table_seed}")
    left = [[g, w, list(ms)] for g, w, ms in groups]
    out = []
    for _ in range(POOLS[pool].seats):
        live = [e for e in left if e[2] and e[1] > 0]
        if not live:
            raise ValueError(f"pool {pool!r} has fewer than {POOLS[pool].seats} buildable members")
        grp = live[_pick(rng, [e[1] for e in live])]
        ms = grp[2]
        out.append(ms.pop(_pick(rng, [bw for _, bw in ms]))[0])
    res = tuple(out)
    if len(_CACHE) > 50_000:
        _CACHE.clear()
    _CACHE[key] = res
    return res


def table_seed_of(seat_seed: Optional[int]) -> int:
    """The runner seeds seat s of rotation r with table_seed * 64 + r * 8 + s; None (a probe build) is table 0."""
    return 0 if seat_seed is None else seat_seed // 64


def opponents(field: list, table_seed: int) -> list:
    """The field's entries with each pool seat replaced by the bot it draws at this table (others unchanged)."""
    out = []
    for nm in field:
        ps = parse_seat(nm)
        out.append(draw(ps[0], table_seed)[ps[1] - 1] if ps else nm)
    return out


def composition(pool: str, tables: int = 20_000) -> dict:
    """Mean seats per table by group and by bot over `tables` draws (table seeds 0..tables-1)."""
    groups = members(pool)
    group_of = {b: g for g, _, ms in groups for b, _ in ms}
    by_group: dict = {g: 0 for g, _, _ in groups}
    by_bot: dict = {}
    for t in range(tables):
        for b in draw(pool, t):
            by_group[group_of[b]] += 1
            by_bot[b] = by_bot.get(b, 0) + 1
    return {"group": {g: n / tables for g, n in by_group.items()},
            "bot": {b: n / tables for b, n in sorted(by_bot.items(), key=lambda kv: -kv[1])}}


class PoolSeat:
    """One drawn seat: builds the bot its slot draws at this table, with the seed the runner gave the seat, and hands
    every call to it. `act` and `hand_end` are the inner bot's own bound methods, so the engine's clock times the
    inner bot with no extra frame; `inner` lets the engine find its variant_decide and SafeBot."""

    def __init__(self, pool: str, slot: int, seed: Optional[int] = None):
        from ..bestiary import make_bot

        self.pool, self.slot = pool, slot
        self.name = f"{pool}.{slot}"
        self.table_seed = table_seed_of(seed)
        self.drawn = draw(pool, self.table_seed)[slot - 1]
        self.inner = make_bot(self.drawn, seed)
        self.act = self.inner.act
        self.hand_end = self.inner.hand_end

    def use_cost_model(self, on: bool) -> None:
        hook = getattr(self.inner, "use_cost_model", None)
        if callable(hook):
            hook(on)

    @property
    def last_cost_ns(self):
        return getattr(self.inner, "last_cost_ns", None)

    def new_table(self, rules, seat: int, n_players: int) -> None:
        self.inner.new_table(rules, seat, n_players)

    def act(self, obs):  # replaced per instance by the inner bot's own act
        return self.inner.act(obs)

    def hand_end(self, result) -> None:  # replaced per instance
        self.inner.hand_end(result)
