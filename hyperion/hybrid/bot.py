"""HybridCore routes each decision to a rival's core or to Hero; Hybrid is the SafeBot shell around it.

The core is `HybridConfig.core`: "rival2" (`hybrid`, core.py) or "rival3" (`hybrid3`, core3.py). Each exposes the same
adapter (setup, start_hand, decide, legalize, end), and the routing below is the same for both.

Routing, per table from Rules and per decision from the observation:
  core   plain hold'em as the rivals model it: two hole cards (three before a discard only with hero_on_three_cards
         off: the core then sees its best two), a 52-card deck, board 3/4/5, best five of seven, no-limit or pot
         limit (the core's all-in is `max_raise`, the pot-limit cap), antes (they are in `pot`, which the cores read
         as dead money), any blind schedule (they read the current blinds each decision; neither has a place for
         future levels), any payout table (built into rival 2's curve and rival 3's all-in prices from
         `Rules.payouts`), any rank order (cards are remapped first).
  hero   what the core cannot represent, named by a counter: `hero:table:<why>` for a whole table (short deck,
         lowball, wild cards, category order, hi/lo, two boards, must-use-two, three hole cards, fixed limit,
         bounties, knockout points, exposed cards); `hero:straddle` (preflop with a straddle: the cores read it as
         an open raise); `hero:extra_hole` (postflop with more than two hole cards); `hero:soft_deadline` (already
         late when the core's expensive part would start: Hero's cheap path); `hero:core_none` (the core declined:
         rival 3 returns nothing when the move it wants is not legal, e.g. a shove with only call or fold offered, and
         would then fold); `hero:core_error` (the core raised or its answer was unreadable); `hero:panic` (SafeBot saw repeated overruns: Hero's cheap path for the rest of the
         table).
Variant decisions (discard, swap, buy a card) are always Hero's `variant_decide`.

Exploit layer (`HybridConfig.exploit`, off by default): hyperion/strategy/exploit.py observes every decision and may
replace a passive action (counted as `exploit:<spot>`); the fallback Hero's own copy is then off.

Counters: `HybridCore.counts` per bot, and the module-level `COUNTS` summed over every HybridCore in the process
(measurement scripts read it).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from time import perf_counter

from ..core.cards import is_identity_order, remap
from ..core.types import Action, HandResult, Observation, Rules
from ..strategy.hero import Config, HeroCore, config_from_dict
from ..strategy.safe import SafeBot
from .core import KitView, Rival2Core, SoftDeadline, best_two, from_kit
from .core3 import Rival3Core

CORES = {"rival2": Rival2Core, "rival3": Rival3Core}  # HybridConfig.core -> the decision core behind the shell

COUNTS: Counter = Counter()  # every HybridCore in this process adds its routes here

_SHOWDOWN_KEYS = ("lowball", "wild_rank", "category_order", "hi_lo")


@dataclass
class HybridConfig:
    hero: Config = field(default_factory=Config)  # the Hero that takes every decision the core does not
    core: str = "rival2"  # the decision core: "rival2" (`hybrid`) or "rival3" (`hybrid3`)
    # the core's postflop sampler (rival 2 as built: 160 / 48 / 260 us budget / 520 us hard stop)
    mc_max: int = 32  # samples (heads-up: one runout per two samples); 32 v 64 v as built: no measurable difference
    mc_min: int = 16  # samples before the wall budget may stop it (rival 2 divides this by the opponents sampled)
    mc_budget_us: float = 200.0  # wall budget from the start of the decision
    mc_hard_us: float = 450.0  # stop regardless (only binds when the process was preempted mid-sample)
    soft_us: float = 350.0  # already this late when the sampler would start: Hero's cheap path instead
    # SafeBot, as Hero sets it: overruns of deadline_ms are counted; after panic_after of them (and panic_rate of
    # calls) the rest of the table is Hero's cheap path
    deadline_ms: float = 0.5
    panic_after: int = 5
    panic_rate: float = 0.02
    # payoff and information terms the core has no place for: Hero plays those tables
    hero_on_bounty: bool = True
    hero_on_exposed: bool = True
    # three hole cards: Hero plays the table from its 3-card variant tables. False = the core plays preflop from its
    # best two (and postflop once a discard leaves two): measured 0.35-0.63 worse than Hero on the three 3-card games
    hero_on_three_cards: bool = True
    # the exploit layer for dead and timing-out seats (hyperion/strategy/exploit.py) in front of every decision, core or
    # Hero: None = off; an ExploitParams; or "hero" = the params Hero's Config ships by default at this commit. When it
    # is on, the fallback Hero's own copy is switched off, so one layer sees every decision and none is counted twice.
    exploit: object = None
    seed: int | None = None


def hybrid_config(overrides: dict | None = None, hero_overrides: dict | None = None,
                  seed: int | None = None) -> HybridConfig:
    """A HybridConfig with flat overrides ({"mc_max": 48}) and Hero's dotted Config overrides for the fallback."""
    cfg = HybridConfig(hero=config_from_dict(hero_overrides, seed=seed), seed=seed)
    for k, v in (overrides or {}).items():
        if not hasattr(cfg, k) or k == "hero":
            raise KeyError(f"unknown HybridConfig field {k!r}")
        setattr(cfg, k, v)
    cfg.exploit = exploit_params(cfg.exploit)
    return cfg


def exploit_params(spec):
    """HybridConfig.exploit as ExploitParams or None: "hero" (Hero's shipped defaults), a dict of ExploitParams fields
    (on top of those defaults), an ExploitParams, or None / False (off). A layer with no spot on is None."""
    if spec is None or spec is False:
        return None
    from ..strategy.exploit import ExploitParams  # imported here: a Hero without the layer still builds a hybrid

    if spec == "hero" or spec is True:
        base = getattr(Config(), "exploit", None)
        params = base if isinstance(base, ExploitParams) else ExploitParams()
    elif isinstance(spec, dict):
        base = getattr(Config(), "exploit", None)
        params = replace(base if isinstance(base, ExploitParams) else ExploitParams(), **spec)
    elif isinstance(spec, ExploitParams):
        params = spec
    else:
        raise TypeError(f"HybridConfig.exploit: {spec!r}")
    return params if params.active else None


def table_reason(rules: Rules, cfg: HybridConfig) -> str | None:
    """Why the core cannot play this table at all, or None when it can."""
    ex = rules.extras or {}
    if rules.n_suits != 4 or tuple(rules.board_sizes) != (0, 3, 4, 5) or ex.get("removed_ranks"):
        return "deck"
    if rules.must_use_hole:
        return "must_use"
    if rules.hole_cards > 3:
        return "hole_cards"
    if rules.hole_cards == 3 and cfg.hero_on_three_cards:
        return "three_cards"
    for k in _SHOWDOWN_KEYS:
        if k in ex:
            return "showdown"
    if int(ex.get("n_boards", 1) or 1) > 1:
        return "showdown"
    if rules.betting == "fixedlimit":
        return "fixed_limit"
    if rules.betting not in ("nolimit", "potlimit"):
        return "betting"
    if cfg.hero_on_bounty and ("bounty_ratio" in ex or "bounty_funding" in ex or ex.get("variant") == "bounty"
                               or float(ex.get("ko_points", 0.0) or 0.0) > 0.0):
        return "bounty"
    if cfg.hero_on_exposed and ("exposed_index" in ex or ex.get("variant") == "exposed_card"):
        return "exposed"
    return None


class HybridCore:
    """A rival's core for what it can represent, Hero for the rest (module doc). Not guarded: Hybrid wraps it."""

    def __init__(self, config: HybridConfig | None = None):
        self.cfg = cfg = config or HybridConfig()
        cfg.exploit = exploit_params(cfg.exploit)
        self.ex = None
        if cfg.exploit is not None:
            from ..strategy.exploit import Exploit, ExploitParams

            self.ex = Exploit(cfg.exploit)
            if hasattr(cfg.hero, "exploit"):  # one layer in front of every decision: Hero's own copy stays off
                cfg.hero.exploit = ExploitParams()
        self.hero = HeroCore(cfg.hero)
        if cfg.core not in CORES:
            raise KeyError(f"unknown hybrid core {cfg.core!r}; known: {', '.join(CORES)}")
        self.core = CORES[cfg.core]()
        self.kit = KitView()
        self.counts: Counter = Counter()
        self.panic = False
        self.rules = Rules()
        self.seat = 0
        self.n = 8
        self._remap = None
        self._table_why: str | None = None
        self._straddle = False
        self._start: list = []  # exact chips per seat at the start of the current hand
        self._start_hand = 0  # 0-based hand number `_start` belongs to
        self._core_hand = -1  # hand number of the core's last decision

    # ------------------------------------------------------------------ Bot protocol
    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        cfg = self.cfg
        self.rules, self.seat, self.n = rules, seat, n_players
        self.panic = False
        self._remap = None if is_identity_order(rules) else rules
        self._table_why = table_reason(rules, cfg)
        self._straddle = bool(rules.straddle)
        self.hero.new_table(rules, seat, n_players)
        if self.ex is not None:
            self.ex.new_table(n_players, seat)
        self.kit.reset()
        core = self.core
        core.setup(rules, seat, n_players, cfg)
        self._start = [rules.starting_stack] * n_players
        self._start_hand = 0
        self._core_hand = -1
        if self._table_why is None:
            core.start_hand(1, self._start)

    def set_panic(self, on: bool) -> None:
        self.panic = on
        self.hero.set_panic(on)

    def act(self, obs: Observation) -> Action:
        ex = self.ex
        if ex is None:
            return self._decide(obs)
        try:
            ex.observe(obs)
        except Exception:  # noqa: BLE001 - a slip in the layer keeps the decision the core or Hero makes
            ex = None
        a = self._decide(obs)
        if ex is not None:
            try:
                b = ex.override(obs, a)
            except Exception:  # noqa: BLE001
                b = None
            if b is not None:
                why = "exploit:" + (ex.last or "override")
                self.counts[why] += 1
                COUNTS[why] += 1
                return b
        return a

    def _decide(self, obs: Observation) -> Action:
        t0 = perf_counter()
        if self.panic:
            return self._hero(obs, "hero:panic")
        if self._table_why is not None:
            return self._hero(obs, "hero:table:" + self._table_why)
        street = obs.street
        if street == 0 and self._straddle:
            return self._hero(obs, "hero:straddle")
        hole, board = obs.hole, obs.board
        rm = self._remap
        if rm is not None:
            hole, board = remap(hole, rm), remap(board, rm)
        route = "core"
        if len(hole) != 2:
            if street > 0 or len(hole) < 2:
                return self._hero(obs, "hero:extra_hole")
            hole = best_two(hole)
            route = "core:best_two"
        self._core_hand = obs.hand_no
        try:
            kit = self.kit(obs, hole, board)
            ans = self.core.decide(kit, t0)
            if ans is None:  # the core declined (rival 3 does when the move it wants is not legal): Hero decides
                return self._hero(obs, "hero:core_none")
            a = from_kit(self.core.legalize(ans, kit), obs)
        except SoftDeadline:
            return self._hero(obs, "hero:soft_deadline", cheap=True)
        except Exception:  # noqa: BLE001 - the core's failure is Hero's decision, never a forced fold
            a = None
        if a is None:
            return self._hero(obs, "hero:core_error")
        self.counts[route] += 1
        COUNTS[route] += 1
        return a

    def _hero(self, obs: Observation, why: str, cheap: bool = False) -> Action:
        self.counts[why] += 1
        COUNTS[why] += 1
        h = self.hero
        if h.hand_no != obs.hand_no and self._core_hand == obs.hand_no and self._start_hand == obs.hand_no \
                and len(self._start) == len(obs.stacks):
            # Hero meets this hand after the core acted in it: its own read of the hand-start chips (stacks + bets at
            # its first decision) would be off by whatever moved since, and its hand_end chip chain with it
            h.hand_no = obs.hand_no
            h.hand_start = list(self._start)
        if cheap and not h.panic:
            h.panic = True
            try:
                return h.act(obs)
            finally:
                h.panic = False
        return h.act(obs)

    def hand_end(self, result: HandResult) -> None:
        if self.ex is not None:
            try:
                self.ex.hand_end(result)
            except Exception:  # noqa: BLE001
                pass
        try:
            self.hero.hand_end(result)
        finally:
            self.core.end(result)
            start = self._start
            if len(result.deltas) == len(start) and result.hand_no == self._start_hand:
                self._start = [max(0, start[s] + result.deltas[s]) for s in range(len(start))]
                self._start_hand = result.hand_no + 1
                if self._table_why is None and self._start[self.seat] > 0:
                    self.core.start_hand(result.hand_no + 2, self._start)

    # ------------------------------------------------------------------ variant decisions
    def variant_decide(self, prompt: dict):
        return self.hero.variant_decide(prompt)

    def stats(self) -> dict:
        return dict(self.counts)


class Hybrid:
    """SafeBot around HybridCore, as Hero is SafeBot around HeroCore. `hybrid.safe.stats()` has errors / overruns /
    worst latency; `hybrid.core.counts` has the decisions by route."""

    def __init__(self, config: HybridConfig | None = None):
        self.core = HybridCore(config)
        cfg = self.core.cfg
        self.safe = SafeBot(self.core, cfg.deadline_ms, cfg.panic_after, cfg.panic_rate)

    @property
    def config(self) -> HybridConfig:
        return self.core.cfg

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.safe.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.safe.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.safe.hand_end(result)

    def variant_decide(self, prompt: dict):
        """Guarded like act(): an error is counted and means the hook's default decision."""
        try:
            return self.core.variant_decide(prompt)
        except Exception:  # noqa: BLE001
            self.safe.errors += 1
            return None


def make_bot(config: HybridConfig | None = None, seed: int | None = None, overrides: dict | None = None,
             hero_overrides: dict | None = None) -> Hybrid:
    if config is None:
        config = hybrid_config(overrides, hero_overrides, seed)
    return Hybrid(config)
