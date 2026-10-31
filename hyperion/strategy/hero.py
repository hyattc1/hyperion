"""Hero: the bot. Composes profiler + preflop charts + push/fold + postflop rules behind SafeBot.

    Hero()            full bot, SafeBot inside (Hero.safe holds the telemetry)
    Hero.cheap()      the 15-minute fallback: push/fold + tight preflop, no reads, no ICM
    make_bot()        for the simulator registry

Every tunable number lives in Config (and the per-module *Params it holds). Decision-time work is
one Spot, one profiler update, and one module call. ICM is a per-hand value curve computed in
hand_end / new_table where exact ICM's ~0.5 ms does not count against the decision budget.
"""
from __future__ import annotations

import gc
from dataclasses import dataclass, field, replace
from functools import lru_cache

from ..core.cards import is_identity_order, remap
from ..core.types import Action, ActionKind, HandResult, Observation, Rules
from .postflop import Postflop, PostflopParams
from .preflop import Preflop, PreflopParams
from .profiler import Profiler
from .pushfold import PushFold, PushFoldParams
from .safe import SafeBot, safe_action
from .spot import Spot
from .tables import Tables, load as load_tables

_CHECK = Action(ActionKind.CHECK)
_FOLD = Action(ActionKind.FOLD)

try:  # the ICM module is another builder's; chip-proportional if it is missing or broken
    from ..core.icm import icm_equity as _icm_equity
except Exception:  # noqa: BLE001
    _icm_equity = None

ICM_BUCKETS = 100  # opponents' stacks are rounded to 1/100 of the chips in play before the (memoised) exact ICM call
ICM_ME_SUBDIV = 4  # my own units are chosen so my *share* of the chips is kept, to 1/4 of an opponent unit


@lru_cache(maxsize=1 << 15)
def _icm_bucketed(key: tuple, me: int, payouts: tuple) -> float:
    return _icm_equity(list(key), payouts)[me]


def icm_value(stacks, me: int, payouts) -> float:
    """My exact ICM points for `stacks`, memoised on a rounded key. Opponents are rounded to 1% of the
    chips in play (their mutual proportions barely move my equity); my own entry is then set so that
    my share of the rounded total equals my true share, because that share is what the curve reads."""
    total = 0.0
    for s in stacks:
        if s > 0:
            total += s
    unit = total / ICM_BUCKETS if total > 0 else 1.0
    sub = ICM_ME_SUBDIV
    key = [0] * len(stacks)
    others = 0
    for i, s in enumerate(stacks):
        if i != me and s > 0:
            u = sub * max(1, int(s / unit + 0.5))
            key[i] = u
            others += u
    mine = stacks[me]
    if mine > 0:
        rest = total - mine
        key[me] = max(1, int(mine / rest * others + 0.5)) if rest > 0 and others > 0 else sub * ICM_BUCKETS
    return _icm_bucketed(tuple(key), me, tuple(float(p) for p in payouts))


@dataclass
class Config:
    preflop: PreflopParams = field(default_factory=PreflopParams)
    pushfold: PushFoldParams = field(default_factory=PushFoldParams)
    postflop: PostflopParams = field(default_factory=PostflopParams)
    profiler_prior_n: float = 2.0
    profiler_blend_n: float = 8.0  # dials reach half strength after this many observed actions
    profiler_dial_strength: float = 1.0  # 0 = read opponents but never act on it
    profiler_calldown_slope: float = -0.8  # unknown archetype: call_down_mult = 1.4 + slope * aggression
    use_profiler: bool = True
    use_icm: bool = True
    # my-stack multiples the ICM curve samples. Dense around 1x: with samples only at 0.5/1/1.5 the piecewise-linear
    # curve had a kink at my stack that priced a +-7% flip at 57% equity where exact ICM says 47%.
    icm_ratios: tuple = (0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0)
    cheap: bool = False  # cheapest paths everywhere (also what panic mode switches on)
    deadline_ms: float = 0.5
    panic_after: int = 5
    panic_rate: float = 0.02  # ... and at least this share of calls overran
    seed: int | None = None  # postflop frequency RNG; None = nondeterministic

    @staticmethod
    def cheap_config() -> "Config":
        return Config(cheap=True, use_profiler=False, use_icm=False)


def config_from_dict(overrides: dict | None, seed: int | None = None) -> Config:
    """A Config with dotted overrides applied: {"preflop.three_bet_frac": 0.06, "postflop.value_tier": 5,
    "pushfold.threshold_bb": 10, "use_profiler": false}. Dict-valued fields (open_frac) are merged by key.
    This is how the runner and tools/sweep.py reach the levers without touching code."""
    cfg = Config(seed=seed)
    for key, val in (overrides or {}).items():
        parts = key.split(".")
        target = cfg
        for part in parts[:-1]:
            target = getattr(target, part)
        leaf = parts[-1]
        cur = getattr(target, leaf)
        if isinstance(cur, dict) and isinstance(val, dict):
            cur = dict(cur)
            cur.update({int(k) if str(k).lstrip("-").isdigit() else k: v for k, v in val.items()})
            val = cur
        elif isinstance(cur, tuple) and isinstance(val, list):
            val = tuple(tuple(x) if isinstance(x, list) else x for x in val)
        setattr(target, leaf, val)
    return cfg


class IcmCurve:
    """V(x): my expected points as a function of my stack x, chips moving to/from the field pro rata.
    Sampled at a few multiples of my current stack; linear between samples. V(0) is the payout for
    busting right now (the ICM function reports 0 for a busted seat because its points are fixed)."""

    __slots__ = ("xs", "vs", "n")

    def __init__(self):
        self.xs = [0.0, 1.0]
        self.vs = [0.0, 1.0]
        self.n = 2

    def compute(self, stacks, me: int, payouts, ratios) -> None:
        total = float(sum(s for s in stacks if s > 0))
        base = float(stacks[me])
        alive = sum(1 for s in stacks if s > 0)
        pays = list(payouts) + [0.0] * max(0, alive - len(payouts))
        bust_value = float(pays[alive - 1]) if alive >= 1 else 0.0
        if total <= 0 or base <= 0:
            self.xs, self.vs, self.n = [0.0, 1.0], [bust_value, bust_value], 2
            return
        others = total - base
        xs, vs = [], []
        for r in ratios:
            x = base * r
            if x > total:
                x = total
            if x <= 0:
                v = bust_value
            elif _icm_equity is None:
                v = bust_value + (float(pays[0]) - bust_value) * x / total
            else:
                if others > 0:
                    scale = (total - x) / others
                    st = [x if s == me else (stacks[s] * scale if stacks[s] > 0 else 0) for s in range(len(stacks))]
                else:
                    st = [x if s == me else 0 for s in range(len(stacks))]
                v = icm_value(st, me, pays)
            if xs and x <= xs[-1]:
                break
            xs.append(x)
            vs.append(v)
        if xs[-1] < total:  # holding every chip is first place exactly: the curve's ceiling
            xs.append(total)
            vs.append(float(pays[0]))
        if len(xs) < 2:
            xs.append(xs[-1] + 1.0)
            vs.append(vs[-1])
        self.xs, self.vs, self.n = xs, vs, len(xs)

    def linear(self, stacks, me: int, payouts) -> None:
        """Chip-proportional between busting now and holding every chip: the deep-stack stand-in."""
        total = float(sum(s for s in stacks if s > 0))
        alive = sum(1 for s in stacks if s > 0)
        pays = list(payouts) + [0.0] * max(0, alive - len(payouts))
        bust = float(pays[alive - 1]) if alive >= 1 else 0.0
        top = float(pays[0]) if pays else 0.0
        self.xs, self.vs, self.n = [0.0, max(total, 1.0)], [bust, top], 2

    def value(self, x: float) -> float:
        xs, vs = self.xs, self.vs
        if x <= xs[0]:
            return vs[0]
        n = self.n
        i = 1
        while i < n - 1 and xs[i] < x:
            i += 1
        x0, x1 = xs[i - 1], xs[i]
        v0, v1 = vs[i - 1], vs[i]
        if x > x1:  # beyond the last sample (all the chips): nothing more to win
            return v1
        return v0 + (v1 - v0) * (x - x0) / (x1 - x0)


class HeroCore:
    """The unguarded strategy. Hero wraps it in SafeBot; tests may poke it directly."""

    def __init__(self, config: Config | None = None, tables: Tables | None = None):
        self.cfg = cfg = config or Config()
        self.tables = tables or load_tables(need_hu=True)
        self.prof = Profiler(8, prior_n=cfg.profiler_prior_n, blend_n=cfg.profiler_blend_n,
                             dial_strength=cfg.profiler_dial_strength,
                             calldown_slope=cfg.profiler_calldown_slope) if cfg.use_profiler else None
        self.preflop = Preflop(cfg.preflop, self.tables)
        self.pushfold = PushFold(cfg.pushfold, self.tables)
        self.postflop = Postflop(cfg.postflop, cfg.seed)
        self.curve = IcmCurve()
        if cfg.use_icm:
            self.pushfold.curve = self.curve
            self.preflop.curve = self.curve
            self.postflop.curve = self.curve
        self.panic = False
        self.rules = Rules()
        self.seat = 0
        self.n = 8
        self._remap = None
        self.hand_no = -1
        self.hand_start = None  # chips per seat at the start of the current hand
        self.last_stacks = None
        self.payouts = self.rules.payouts
        self.last_path = ""  # which module made the last decision (diagnostics only)

    # ------------------------------------------------------------------ Bot protocol
    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.rules = rules
        self.seat = seat
        self.n = n_players
        self.payouts = rules.payouts
        self._remap = None if is_identity_order(rules) else rules
        self.hand_no = -1
        self.hand_start = None
        self.last_stacks = [rules.starting_stack] * n_players
        self.panic = False
        if self.prof is not None:
            self.prof.reset(n_players, seat)
        if self.cfg.use_icm:
            self.curve.compute(self.last_stacks, seat, self.payouts, self.cfg.icm_ratios)
        gc.freeze()  # tables and evaluator dicts leave the collector's reach: no gen-2 pause mid-decision

    def set_panic(self, on: bool) -> None:
        self.panic = on

    def act(self, obs: Observation) -> Action:
        hole = obs.hole
        board = obs.board
        if self._remap is not None:
            hole = remap(hole, self._remap)
            board = remap(board, self._remap)
        if obs.hand_no != self.hand_no:
            self.hand_no = obs.hand_no
            stacks, bets = obs.stacks, obs.bets
            self.hand_start = [stacks[s] + bets[s] for s in range(len(stacks))]
        prof = self.prof
        if prof is not None:
            try:
                prof.observe(obs)
            except Exception:  # noqa: BLE001 - a profiler slip must not cost the decision
                prof = None
        spot = Spot(obs, hole)
        cheap = self.cfg.cheap or self.panic
        if obs.street == 0:
            if self.pushfold.applies(spot):
                self.last_path = "pushfold"
                return self.pushfold.act(spot, prof, cheap)
            self.last_path = "preflop"
            return self.preflop.act(spot, prof, cheap)
        if len(hole) != 2 or len(board) < 3:
            self.last_path = "safe"
            return safe_action(obs)
        aggressor = prof is not None and prof.pre_raiser == obs.seat
        self.last_path = "postflop"
        return self.postflop.act(spot, hole, prof, aggressor, cheap, board)

    def hand_end(self, result: HandResult) -> None:
        if self.prof is not None:
            self.prof.hand_end(result)
        base = self.hand_start if (self.hand_start is not None and result.hand_no == self.hand_no) else self.last_stacks
        if base is not None and len(result.deltas) == len(base):
            after = [max(0, base[s] + result.deltas[s]) for s in range(len(base))]
            self.last_stacks = after
            if self.cfg.use_icm and after[self.seat] > 0:
                self.curve.compute(after, self.seat, self.payouts, self.cfg.icm_ratios)
        self.hand_start = None


class Hero:
    """SafeBot around HeroCore. `hero.safe.stats()` has errors / overruns / worst latency."""

    def __init__(self, config: Config | None = None, tables: Tables | None = None):
        self.core = HeroCore(config, tables)
        self.safe = SafeBot(self.core, self.core.cfg.deadline_ms, self.core.cfg.panic_after, self.core.cfg.panic_rate)

    @classmethod
    def cheap(cls, tables: Tables | None = None) -> "Hero":
        return cls(Config.cheap_config(), tables)

    @property
    def config(self) -> Config:
        return self.core.cfg

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.safe.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.safe.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.safe.hand_end(result)


def make_bot(config: Config | None = None) -> Hero:
    return Hero(config)


gc.freeze()  # whatever was built at import (evaluator tables, straight-draw table) is permanent

__all__ = ["Config", "Hero", "HeroCore", "IcmCurve", "config_from_dict", "icm_value", "make_bot", "replace"]
