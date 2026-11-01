"""The composite bot: a base plus, per section of the game, the member bot whose decision is used there.

    from hyperion.compose import make_bot
    bot = make_bot(route={"pre_hu": "hero"})       # SafeBot around CompositeCore; every other section is the base's
    bot.core.counts                                # decisions by section and donor, layer fires, fallbacks

**Donors and members.** A donor is what a section is routed to: a member bot and whether the exploit layer may act on its
decisions there. Members are built once per bot and play every table:
  base     rival 3's core behind Hero's shell (hyperion.hybrid, core "rival3"), the layer taken out to the front.
           Donor `base` (the layer on) is hybrid3_x; donor `hybrid3` (the layer off) is hybrid3.
  hero     Hero's HeroCore, its own layer off. Donor `hero` (the layer on) is Hero as it ships; `hero_nl` without it.
  r2       rival 2's core behind the same shell (core "rival2"). Donor `r2x` is hybrid_x; `r2` is hybrid.
  rival1   red-team rival 1 as built, through the kit adapter the bestiary uses. Donor `rival1`; `rival1x` with the layer.
  rival3   red-team rival 3 as built (brief's payouts in its ICM, no shell). Donor `rival3`; `rival3x` with the layer.
More can be registered at run time (`register_member`); scratch runners use that for black-box opponents.

**Every member sees everything.** Each member in the route acts on every observation and gets every hand_end, so its
reads stay its own: the members not chosen compute their decision too ("shadow" calls) and it is discarded. Only the
members named by the route run (plus the base, which also answers variant prompts and plays the tables a raw rival
cannot), so the shipped form pays only for what it uses; `shadow_all` runs every member (tests, timing). Rival 3 keeps
one fact about its own past actions, "I raised preflop" (it raises its flop bluff rate); when its decision was not the
one taken, that flag is set from the action that was (`_resync_r3`).

**The exploit layer** sits in front of the whole composite, one instance (hyperion/strategy/exploit.py): it observes
every decision, and replaces the chosen member's passive action where the donor has the layer on. One read of the
table, not one per member: the layer reads only the table, so copies would read the same and cost ~6 us each.

**Raw rivals play plain hold'em only.** On a table the base's core cannot play (Hero's 14 variant tables), a permuted
rank order, or a straddle, a section routed to rival1 or rival3 is played by the base instead (counted
`fallback:plain`). Hero and the hybrid members play every table.

**Errors.** A chosen member that raises or answers None: the base's answer, else check or fold (`fallback:error`). A
shadow that raises is counted and ignored. `late_us`: if the chosen member has already used this long, the shadows skip
this decision (counted `shadow:late`); 10^9 in deterministic runs.

Routes: a dict or "section=donor,..." (sections.parse_route: section names, "pre", "post", "*"). Unrouted sections go
to the base's donor (`base`).
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from time import perf_counter
from typing import Callable

from ..core.cards import is_identity_order
from ..core.types import Action, ActionKind, HandResult, Observation, Rules
from ..strategy.safe import SafeBot, safe_action
from .sections import SECTIONS, parse_route, section

_RAISE = ActionKind.RAISE
COUNTS: Counter = Counter()  # summed over every CompositeCore in the process (measurement scripts read it)


# ---------------------------------------------------------------------------------------------- members
class KitMember:
    """A red-team rival's Bot behind the kit interface it was built against (as bestiary.RivalBot passes it): legal as
    strings, history as (seat, (kind, amount)), 1-based hand_no, rules as a dict; its answer clamped to the
    observation, an unreadable one a check or fold. `history_at_end`: hand_end carries the hand's history (rival 3)."""

    plain_only = True

    def __init__(self, impl, history_at_end: bool = False):
        from ..hybrid.kit import KitView

        self.impl = impl
        self.kit = KitView()
        self.history_at_end = history_at_end

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.kit.reset()
        self.impl.new_table({"starting_stack": rules.starting_stack, "hand_cap": rules.max_hands,
                             "n_players": n_players, "blinds": rules.blind_levels}, seat, n_players)

    def act(self, obs: Observation) -> Action:
        from ..hybrid.kit import from_kit

        a = from_kit(self.impl.act(self.kit(obs, obs.hole, obs.board)), obs)
        return a if a is not None else (Action.check() if ActionKind.CHECK in obs.legal else Action.fold())

    def hand_end(self, result: HandResult) -> None:
        r = {"hand_no": result.hand_no + 1, "deltas": result.deltas}
        if self.history_at_end:
            r["history"] = [(s, (a.kind.value, a.amount)) for s, a in result.history]
        self.impl.hand_end(r)


def _r3_state(bot):
    return bot.hand, bot.my_pf_raise


def _resync_r3(bot, before, obs: Observation, taken: Action) -> None:
    """Rival 3 sets `my_pf_raise` from its own preflop answer; when another member's answer was taken, set it from the
    action that was: it raised preflop this hand if it had before this decision or the action taken is a raise."""
    if obs.street != 0:
        return
    h0, p0 = before
    prev = p0 if bot.hand == h0 else False  # its _act reset the flag when this decision opened a new hand
    bot.my_pf_raise = bool(prev or taken.kind is _RAISE)


def _hybrid_member(core: str, cfg: "ComposeConfig", seed):
    from ..hybrid.bot import HybridCore, hybrid_config
    from ..strategy.exploit import ExploitParams

    over = {"core": core, **cfg.hybrid_overrides}
    if core == "rival3":
        over.update(cfg.base_overrides)
    over["exploit"] = None
    hc = hybrid_config(over, cfg.hero_overrides, seed)
    hc.hero.exploit = ExploitParams()  # one layer, in front of the composite
    m = HybridCore(hc)
    m.plain_only = False
    return m


def _hero_member(cfg: "ComposeConfig", seed):
    from ..strategy.exploit import ExploitParams
    from ..strategy.hero import HeroCore, config_from_dict

    c = config_from_dict(cfg.hero_overrides, seed=seed)
    c.exploit = ExploitParams()
    m = HeroCore(c)
    m.plain_only = False
    return m


def _rival_member(module: str, history_at_end: bool):
    def build(cfg, seed):
        import importlib

        mod = importlib.import_module(f"..sim.rivals.{module}", __package__)
        return KitMember(mod.Bot(), history_at_end)
    return build


# name -> factory(cfg, seed) -> member (new_table / act / hand_end, optional set_panic and variant_decide; plain_only)
MEMBERS: dict[str, Callable] = {
    "base": lambda cfg, seed: _hybrid_member("rival3", cfg, seed),
    "hero": _hero_member,
    "r2": lambda cfg, seed: _hybrid_member("rival2", cfg, seed),
    "rival1": _rival_member("rival1", False),
    "rival3": _rival_member("rival3", True),
}
# member name -> (state(member) captured before act, resync(member, state, obs, taken) when its answer was not taken)
RESYNC: dict[str, tuple] = {
    "base": (lambda m: _r3_state(m.core), lambda m, st, obs, a: _resync_r3(m.core, st, obs, a)),
    "rival3": (lambda m: _r3_state(m.impl), lambda m, st, obs, a: _resync_r3(m.impl, st, obs, a)),
}
# donor name -> (member, the exploit layer acts on its decisions)
DONORS: dict[str, tuple[str, bool]] = {
    "base": ("base", True), "hybrid3": ("base", False),
    "hero": ("hero", True), "hero_nl": ("hero", False),
    "r2x": ("r2", True), "r2": ("r2", False),
    "rival1": ("rival1", False), "rival1x": ("rival1", True),
    "rival3": ("rival3", False), "rival3x": ("rival3", True),
}


def register_member(name: str, factory: Callable, layer_donor: bool = True) -> None:
    """Add a member (and donors `name`, and `name`x with the layer) for this process only: scratch runners and tests."""
    MEMBERS[name] = factory
    DONORS[name] = (name, False)
    if layer_donor:
        DONORS[name + "x"] = (name, True)


# ---------------------------------------------------------------------------------------------- config
@dataclass
class ComposeConfig:
    route: dict = field(default_factory=dict)  # section -> donor; unrouted sections go to `base_donor`
    base_donor: str = "base"
    # the layer's params: "hero" = what Hero's Config ships, a dict of ExploitParams fields on top of those, an
    # ExploitParams, or None (no layer anywhere)
    exploit: object = "hero"
    hero_overrides: dict = field(default_factory=dict)  # Hero's dotted Config overrides (hero member and every fallback Hero)
    hybrid_overrides: dict = field(default_factory=dict)  # flat HybridConfig overrides for the hybrid members (soft_us ...)
    base_overrides: dict = field(default_factory=dict)  # ... for the base only (rival 3 core knobs, once exposed)
    shadow_all: bool = False  # run every registered member, not only the route's (tests, timing)
    late_us: float = 700.0  # the chosen member already used this much: shadows skip this decision
    deadline_ms: float = 0.5  # SafeBot, as Hero sets it
    panic_after: int = 5
    panic_rate: float = 0.02
    seed: int | None = None


def compose_config(route=None, seed=None, **kw) -> ComposeConfig:
    cfg = ComposeConfig(seed=seed, **kw)
    cfg.route = parse_route(route)
    for sec, d in cfg.route.items():
        if sec not in SECTIONS:
            raise KeyError(f"unknown section {sec!r}")
        if d not in DONORS:
            raise KeyError(f"unknown donor {d!r} for {sec}; known: {', '.join(DONORS)}")
    if cfg.base_donor not in DONORS or DONORS[cfg.base_donor][0] != "base":
        raise KeyError(f"base_donor must be a donor of the base member, got {cfg.base_donor!r}")
    return cfg


# ---------------------------------------------------------------------------------------------- the core
class CompositeCore:
    """Routes each decision to its section's member (module doc). Not guarded: Composite wraps it in SafeBot."""

    def __init__(self, config: ComposeConfig | None = None):
        self.cfg = cfg = config or ComposeConfig()
        donors = [cfg.route.get(s, cfg.base_donor) for s in SECTIONS]
        names = ["base"]  # index 0 is always the base
        for d in donors:
            m = DONORS[d][0]
            if m not in names:
                names.append(m)
        if cfg.shadow_all:
            names += [m for m in MEMBERS if m not in names]
        self.names = names
        self.members = [MEMBERS[n](cfg, cfg.seed) for n in names]
        self.base = self.members[0]
        idx = {n: i for i, n in enumerate(names)}
        self.route = [(idx[DONORS[d][0]], DONORS[d][1]) for d in donors]  # per section: (member index, layer on)
        self.donors = donors
        self.plain_only = [bool(getattr(m, "plain_only", False)) for m in self.members]
        self.resync = [RESYNC.get(n) for n in names]
        self._rs_idx = [j for j, r in enumerate(self.resync) if r is not None]
        self._states: list = [None] * len(names)
        self._props: list = [None] * len(names)
        # tap(core, obs, section, chosen index, chosen member's answer, action taken, every member's answer, layer):
        # called after each decision whose shadows all ran (tools/swap.py records disagreements with it)
        self.tap = None
        from ..hybrid.bot import exploit_params

        params = exploit_params(cfg.exploit)
        self.ex = None
        if params is not None:
            from ..strategy.exploit import Exploit

            self.ex = Exploit(params)
        self.counts: Counter = Counter()
        self.panic = False
        self.plain = True
        self.late = cfg.late_us * 1e-6
        self.last_section = -1

    # ------------------------------------------------------------------ Bot protocol
    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.panic = False
        for m in self.members:
            m.new_table(rules, seat, n_players)
        b = self.base
        self.plain = getattr(b, "_table_why", None) is None and not getattr(b, "_straddle", False) \
            and is_identity_order(rules)
        if self.ex is not None:
            self.ex.new_table(n_players, seat)

    def set_panic(self, on: bool) -> None:
        self.panic = on
        for m in self.members:
            sp = getattr(m, "set_panic", None)
            if sp is not None:
                sp(on)

    def act(self, obs: Observation) -> Action:
        t0 = perf_counter()
        ex = self.ex
        if ex is not None:
            try:
                ex.observe(obs)
            except Exception:  # noqa: BLE001 - a slip in the layer keeps the members' decision
                ex = None
        sec = section(obs)
        self.last_section = sec
        mi, layer = self.route[sec]
        counts = self.counts
        if self.panic:  # SafeBot saw repeated overruns: the base alone (Hero's cheap path) for the rest of the table
            mi, layer = 0, True
        elif mi and self.plain_only[mi] and not self.plain:
            counts["fallback:plain"] += 1
            mi = 0
        members, resync = self.members, self.resync
        nm = len(members)
        states = self._states
        for j in self._rs_idx:
            if j != mi:
                try:
                    states[j] = resync[j][0](members[j])
                except Exception:  # noqa: BLE001
                    states[j] = None
        props = self._props
        failed = -1
        try:
            a = members[mi].act(obs)
        except Exception:  # noqa: BLE001
            a = None
        if a is None or a.__class__ is not Action:
            counts["fallback:error"] += 1
            a = None
            if mi:
                try:
                    a = self.base.act(obs)
                except Exception:  # noqa: BLE001
                    a = None
                failed = mi
                mi = 0
            if a is None or a.__class__ is not Action:
                a = safe_action(obs)
        props[mi] = a
        shadowed = False
        if not self.panic and nm > 1:
            if perf_counter() - t0 > self.late:
                counts["shadow:late"] += 1
            else:
                shadowed = True
                for j in range(nm):
                    if j != mi and j != failed:
                        try:
                            props[j] = members[j].act(obs)
                        except Exception:  # noqa: BLE001 - a shadow's failure costs nothing
                            props[j] = None
                            counts["shadow:error:" + self.names[j]] += 1
        own = a
        if layer and ex is not None:
            try:
                b = ex.override(obs, a)
            except Exception:  # noqa: BLE001
                b = None
            if b is not None:
                why = "exploit:" + (ex.last or "override")
                counts[why] += 1
                COUNTS[why] += 1
                a = b
        if shadowed:
            for j in self._rs_idx:
                # a member whose answer was not the action taken: its record of its own actions follows the one taken
                pj = props[j]
                if j != mi and states[j] is not None and pj is not None and pj != a:
                    try:
                        resync[j][1](members[j], states[j], obs, a)
                    except Exception:  # noqa: BLE001
                        pass
            tap = self.tap
            if tap is not None:
                tap(self, obs, sec, mi, own, a, props, ex)
        for j in range(nm):
            props[j] = None
        key = SECTIONS[sec] + ":" + self.names[mi]
        counts[key] += 1
        COUNTS[key] += 1
        return a

    def hand_end(self, result: HandResult) -> None:
        if self.ex is not None:
            try:
                self.ex.hand_end(result)
            except Exception:  # noqa: BLE001
                pass
        err = None
        for m in self.members:
            try:
                m.hand_end(result)
            except Exception as e:  # noqa: BLE001 - every member still gets the hand
                err = err or e
        if err is not None:
            raise err

    def variant_decide(self, prompt: dict):
        return self.base.variant_decide(prompt)

    def stats(self) -> dict:
        return dict(self.counts)


class Composite:
    """SafeBot around CompositeCore, as Hero and the hybrids are built."""

    def __init__(self, config: ComposeConfig | None = None):
        self.core = CompositeCore(config)
        cfg = self.core.cfg
        self.safe = SafeBot(self.core, cfg.deadline_ms, cfg.panic_after, cfg.panic_rate)

    @property
    def config(self) -> ComposeConfig:
        return self.core.cfg

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.safe.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.safe.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.safe.hand_end(result)

    def variant_decide(self, prompt: dict):
        try:
            return self.core.variant_decide(prompt)
        except Exception:  # noqa: BLE001
            self.safe.errors += 1
            return None


def make_bot(route=None, seed: int | None = None, config: ComposeConfig | None = None, **kw) -> Composite:
    return Composite(config or compose_config(route, seed=seed, **kw))


# ---------------------------------------------------------------------------------------------- the simulator
def register(name: str, route=None, **kw) -> type:
    """Seat a composite in the simulator under `name` (this process only): `<field>@<name>` puts it in Hero's seat.
    It reads the bestiary's HERO_CONFIG (Hero's dotted overrides) and HYBRID_CONFIG (panic_after, soft_us, ...) when
    built, as `hero` and the hybrids do, so a model-mode run's settings reach it."""
    from ..sim import bestiary as B

    fixed = dict(kw)

    class _Seat(B._Base):
        ROUTE = route
        KW = fixed

        def __init__(self, seed=None):
            super().__init__(seed)
            kw2 = dict(self.KW)
            hyb = dict(B.HYBRID_CONFIG or {})
            panic = hyb.pop("panic_after", None)
            if panic is not None:
                kw2.setdefault("panic_after", panic)
            if hyb.get("soft_us", 0) >= 1e5:
                kw2.setdefault("late_us", 1e9)  # deterministic runs: nothing reads the wall clock
            kw2["hybrid_overrides"] = {**hyb, **kw2.get("hybrid_overrides", {})}
            kw2["hero_overrides"] = {**(B.HERO_CONFIG or {}), **kw2.get("hero_overrides", {})}
            self.impl = make_bot(self.ROUTE, seed=seed, **kw2)

        def new_table(self, rules, seat, n_players):
            self.impl.new_table(rules, seat, n_players)

        def act(self, obs):
            return self.impl.act(obs)

        def hand_end(self, result):
            self.impl.hand_end(result)

        def variant_decide(self, prompt):
            return self.impl.variant_decide(prompt)

    _Seat.__name__ = _Seat.__qualname__ = "Composite_" + name
    B.REGISTRY[name] = _Seat
    B._BY_CLASS[_Seat.__name__.lower()] = _Seat
    return _Seat


__all__ = ["COUNTS", "Composite", "CompositeCore", "ComposeConfig", "DONORS", "KitMember", "MEMBERS", "compose_config",
           "make_bot", "register", "register_member"]
