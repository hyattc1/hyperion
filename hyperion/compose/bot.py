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
  elite1, elite2   the climb's elite builds as built (PersonaMember: payouts and history as the bestiary passes them,
           the generator seeded per table). Donors `elite1`, `elite2`; `elite1x`, `elite2x` with the layer (S9).
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

**Degradation levels** (backlog R1, `degrade`, off by default). SafeBot's governor (hyperion/strategy/safe.py) can step
the composite down through the levels `degrade` names, one per trigger, before the cheap path (panic) and back up when
the box turns out fine; each level adds its saving to the ones above it:
  noshadow   no full shadows (a member not chosen that would decide in full skips the decision; its record of its own
             actions follows the one taken, as after a light shadow); light shadows stay, they keep the members' state
  bare       no shadows at all
  base       every section to the base's donor (hybrid3_x: rival 3's core + the layer), no full shadows (light ones
             stay)
  hero       every section to Hero (the hero member, the layer on), no full shadows (light ones stay)
  lean       under payouts with no closed form (top-heavy), a decision the base would price with exact ICM (~50 us a
             call, four an all-in) is Hero's (the base's own Hero, its ICM precomputed at hand_end: `hero:lean`)
Counted `level:<n>` once per decision played at level n > 0.

Routes: a dict or "section=donor,..." (sections.parse_route: section names, "pre", "post", "*"). Unrouted sections go
to the base's donor (`base`).

**The strong-table route** (backlog S9, `strong_route`, off by default): sections played by other donors only while the
table reads strong. The read is the share of our first-in, not all-in preflop raises this table that faced a re-raise
before the flop, smoothed toward `strong_prior` with the weight of `strong_prior_n` raises; the table reads strong
while it is at least `strong_rr` (0: always). At night's tables about 14% of F's opens are re-raised, at tables of
strong general bots and copies of F 24-26% (docs/drills/climb/s9-log.md). Never in a blind-vs-blind unopened pot unless
`strong_bvb`. Its donors' members run (and shadow) on every decision, like any routed member's.
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


def _hero_state(m):
    return m.hand_no, m._pre_aggr


def _resync_hero(m, before, obs: Observation, taken: Action) -> None:
    """Hero keeps "I was the last preflop raiser" (`_pre_aggr`, its postflop aggressor when the kit passes no history)
    from its own answers; when another member's answer was taken, set it as Hero's own act would from the one taken."""
    if obs.street != 0:
        return
    h0, p0 = before
    prev = p0 if h0 == obs.hand_no else False
    if taken.kind is _RAISE:
        m._pre_aggr = True
        return
    if obs.to_call > 0:
        hist = obs.history
        raised = any(a.kind is _RAISE for _, a in hist) if hist else max(obs.bets) > obs.blinds[1]
        if raised:
            m._pre_aggr = False
            return
    m._pre_aggr = prev


# Light shadows (ComposeConfig.light): a member not chosen keeps its state from the observation without deciding, where
# its decision changes nothing it keeps. Hero preflop: its modules keep no state, so the hand's chips and the profiler's
# read are all; postflop it draws from its RNG, so it decides in full. Rival 3's core postflop: its decision draws from
# its RNG (and nothing else it keeps), and preflop it draws nothing, so its read of the hand (the history replay) is
# all; preflop it decides in full (its own preflop raise is part of its state).
def _hero_light_ok(m, obs: Observation) -> bool:
    return obs.street == 0 and not m.panic


def _hero_light(m, obs: Observation) -> None:
    if obs.hand_no != m.hand_no:
        m.hand_no = obs.hand_no
        m.hand_start = [s + b for s, b in zip(obs.stacks, obs.bets)]
        m._pre_aggr = False
    prof = m.prof
    if prof is not None:
        try:
            prof.observe(obs)
        except Exception:  # noqa: BLE001 - as in HeroCore.act
            pass


def _none(*args, **kw):
    return None


def _base_light_ok(m, obs: Observation) -> bool:
    return obs.street > 0 and not m.panic and m._table_why is None and len(obs.hole) == 2


def _base_light(m, obs: Observation) -> None:
    hole, board = obs.hole, obs.board
    rm = m._remap
    if rm is not None:
        from ..core.cards import remap

        hole, board = remap(hole, rm), remap(board, rm)
    m._core_hand = obs.hand_no
    kit = m.kit(obs, hole, board)
    core = m.core
    core._t0 = perf_counter()
    core._post = _none  # the instance attribute hides the method: the history replay runs, the decision does not
    try:
        core._act(kit)
    finally:
        del core._post


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

    c = config_from_dict({**cfg.hero_overrides, **cfg.hero_member}, seed=seed)
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


class PersonaMember(KitMember):
    """An elite build from hyperion.sim.field (elite1, elite2: our own agents' prepared top-team bots) as a member,
    through the adapter the bestiary's PersonaBot plays it with: the payouts in the rules dict, the hand's history at
    hand_end, and its generator (each was written with an unseeded random.Random()) reseeded from the member's seed at
    every table start, as the bestiary's _EliteBot does, so a table replays exactly. Plain hold'em only, like every raw
    rival. Backlog S9: a section of F can be routed to one of them (donors `elite1`, `elite2`; `...x` with the layer)."""

    def __init__(self, impl, seed):
        super().__init__(impl, history_at_end=True)
        self._seed = 0 if seed is None else int(seed)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.kit.reset()
        self.impl.new_table({"starting_stack": rules.starting_stack, "hand_cap": rules.max_hands,
                             "n_players": n_players, "blinds": rules.blind_levels, "payouts": list(rules.payouts)},
                            seat, n_players)

    def act(self, obs: Observation) -> Action:
        # the generator is seeded per decision (from the hand, the street and the history's length), so a decision's
        # draws never depend on which earlier decisions it made in full: a light shadow (below) plays the same
        rng = getattr(self.impl, "rng", None)
        if rng is not None:
            rng.seed(((self._seed * 1_000_003 + obs.hand_no) * 4 + obs.street) * 1024 + len(obs.history))
        return super().act(obs)


def _persona_member(module: str):
    def build(cfg, seed):
        from ..sim.field import load

        return PersonaMember(load(module).Bot(), seed)
    return build


# elite1 keeps its reads from the history it scans at each decision (`_scan`) and one fact from its own last answer:
# `pend`, the seats that still owe a response to its raise (settled from the stacks at its next hand). Its light shadow
# scans without deciding; its record follows the action taken (a raise taken sets `pend`, anything else clears it), as
# its own act would have set it, so a light shadow and a full one play the same.
def _elite1_light(m, obs: Observation) -> None:
    m.impl._scan(m.kit(obs, obs.hole, obs.board))


def _elite1_resync(m, before, obs: Observation, taken: Action) -> None:
    b = m.impl
    if taken.kind is _RAISE:
        me = obs.seat
        b.pend = {i: obs.stacks[i] for i in range(len(obs.stacks)) if i != me and obs.in_hand[i] and obs.stacks[i] > 0}
        b.pend_jam = taken.amount >= obs.max_raise
        b.pend_hand = obs.hand_no + 1  # the kit's 1-based hand number, as elite1 reads it
        b.pend_st = obs.street
    else:
        b.pend = None


# name -> factory(cfg, seed) -> member (new_table / act / hand_end, optional set_panic and variant_decide; plain_only)
MEMBERS: dict[str, Callable] = {
    "base": lambda cfg, seed: _hybrid_member("rival3", cfg, seed),
    "hero": _hero_member,
    "r2": lambda cfg, seed: _hybrid_member("rival2", cfg, seed),
    "rival1": _rival_member("rival1", False),
    "rival3": _rival_member("rival3", True),
    "elite1": _persona_member("elite1"),
    "elite2": _persona_member("elite2"),
}
# member name -> (state(member) captured before act, resync(member, state, obs, taken) when its answer was not taken)
RESYNC: dict[str, tuple] = {
    "base": (lambda m: _r3_state(m.core), lambda m, st, obs, a: _resync_r3(m.core, st, obs, a)),
    "rival3": (lambda m: _r3_state(m.impl), lambda m, st, obs, a: _resync_r3(m.impl, st, obs, a)),
    "hero": (_hero_state, _resync_hero),
    "elite1": (lambda m: True, _elite1_resync),
}
# member name -> (can a light shadow stand in for its decision on this observation, the light shadow)
LIGHT: dict[str, tuple] = {
    "hero": (_hero_light_ok, _hero_light),
    "base": (_base_light_ok, _base_light),
    "elite1": (lambda m, obs: True, _elite1_light),
}
# donor name -> (member, the exploit layer acts on its decisions)
DONORS: dict[str, tuple[str, bool]] = {
    "base": ("base", True), "hybrid3": ("base", False),
    "hero": ("hero", True), "hero_nl": ("hero", False),
    "r2x": ("r2", True), "r2": ("r2", False),
    "rival1": ("rival1", False), "rival1x": ("rival1", True),
    "rival3": ("rival3", False), "rival3x": ("rival3", True),
    "elite1": ("elite1", False), "elite1x": ("elite1", True),
    "elite2": ("elite2", False), "elite2x": ("elite2", True),
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
    base_overrides: dict = field(default_factory=dict)  # dials for the base only: r3.* (rival 3's core), hero.* (its
    #                                                     fallback Hero), flat HybridConfig fields
    hero_member: dict = field(default_factory=dict)  # Hero's dotted Config keys for the hero member only
    shadow_all: bool = False  # run every registered member, not only the route's (tests, timing)
    shadow: tuple = ()  # ... or these members as well as the route's (tools/swap.py: the donors it records)
    late_us: float = 700.0  # the chosen member already used this much: shadows skip this decision
    light: bool = False  # light shadows where a member allows them (LIGHT): the same play, about half the cost;
    #                      off where every member's answer is needed (tools/swap.py records them)
    deadline_ms: float = 0.5  # SafeBot, as Hero sets it
    panic_after: int = 5
    panic_rate: float = 0.02
    # SafeBot's governor (hyperion/strategy/safe.py; all off = the single cliff) and the levels it steps through
    panic_window: int = 0
    panic_ladder: bool = False
    panic_recover: int = 0
    panic_backoff: float = 2.0
    degrade: str = ""  # "noshadow,base": the intermediate levels, in order (module doc)
    start_level: int = 0  # measurement: play every table at this level from its first decision (a level's strength)
    # the strong-table route (backlog S9, module doc): these sections go to these donors while the table reads strong,
    # i.e. while the share of our first-in preflop raises that were re-raised, smoothed toward `strong_prior` with the
    # weight of `strong_prior_n` raises, is at least `strong_rr`. Empty (the default): every section as `route` says
    strong_route: dict = field(default_factory=dict)
    strong_rr: float = 0.0  # 0 = always strong (the strong route always on, when it is set)
    strong_prior: float = 0.15
    strong_prior_n: float = 10.0
    # ... and in an unopened pot with one opponent left in the hand (the small blind against the big, or folded round to
    # the button with the small blind out): off = never there (blind-vs-blind play is S11's, climb/s11-exploiter2-fixes)
    strong_bvb: bool = False
    seed: int | None = None


def compose_config(route=None, seed=None, **kw) -> ComposeConfig:
    cfg = ComposeConfig(seed=seed, **kw)
    cfg.route = parse_route(route)
    cfg.strong_route = parse_route(cfg.strong_route)
    for r in (cfg.route, cfg.strong_route):
        for sec, d in r.items():
            if sec not in SECTIONS:
                raise KeyError(f"unknown section {sec!r}")
            if d not in DONORS:
                raise KeyError(f"unknown donor {d!r} for {sec}; known: {', '.join(DONORS)}")
    if cfg.base_donor not in DONORS or DONORS[cfg.base_donor][0] != "base":
        raise KeyError(f"base_donor must be a donor of the base member, got {cfg.base_donor!r}")
    for lv in degrade_levels(cfg.degrade):
        if lv not in LEVEL_KINDS:
            raise KeyError(f"unknown degrade level {lv!r}; known: {', '.join(LEVEL_KINDS)}")
    return cfg


LEVEL_KINDS = ("noshadow", "bare", "base", "hero", "lean")


def degrade_levels(spec) -> list:
    if not spec:
        return []
    if isinstance(spec, (list, tuple)):
        return [str(x).strip() for x in spec if str(x).strip()]
    return [x.strip() for x in str(spec).split(",") if x.strip()]


def _bvb(obs: Observation) -> bool:
    """Preflop, unopened, and one opponent left in the hand (blind against blind)."""
    if max(obs.bets) > obs.blinds[1]:
        return False
    n = 0
    for j, x in enumerate(obs.in_hand):
        if x and j != obs.seat:
            n += 1
    return n == 1


# ---------------------------------------------------------------------------------------------- the core
class CompositeCore:
    """Routes each decision to its section's member (module doc). Not guarded: Composite wraps it in SafeBot."""

    def __init__(self, config: ComposeConfig | None = None):
        self.cfg = cfg = config or ComposeConfig()
        donors = [cfg.route.get(s, cfg.base_donor) for s in SECTIONS]
        names = ["base"]  # index 0 is always the base
        for d in donors + [cfg.strong_route[s] for s in SECTIONS if s in cfg.strong_route]:
            m = DONORS[d][0]
            if m not in names:
                names.append(m)
        extra = list(MEMBERS) if cfg.shadow_all else list(cfg.shadow)
        names += [m for m in extra if m not in names]
        self.names = names
        self.members = [MEMBERS[n](cfg, cfg.seed) for n in names]
        self.base = self.members[0]
        idx = {n: i for i, n in enumerate(names)}
        self.route = [(idx[DONORS[d][0]], DONORS[d][1]) for d in donors]  # per section: (member index, layer on)
        sr = cfg.strong_route
        self.strong = [(idx[DONORS[sr[s]][0]], DONORS[sr[s]][1]) if s in sr else None for s in SECTIONS] if sr else None
        self._rr_reset()
        self.donors = donors
        self.plain_only = [bool(getattr(m, "plain_only", False)) for m in self.members]
        self.resync = [RESYNC.get(n) for n in names]
        self._rs_idx = [j for j, r in enumerate(self.resync) if r is not None]
        self.light = [LIGHT.get(n) if cfg.light else None for n in names]
        self._lit = [False] * len(names)
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
        # degradation levels (module doc): what each level n = 1 .. levels turns on, cumulatively
        self._degrade = degrade_levels(cfg.degrade)
        self.levels = len(self._degrade)
        self.level = 0
        self._full_shadows = True
        self._shadows = True
        self._force = None  # (member index, layer) every section goes to at a base / hero level
        self._hero_idx = names.index("hero") if "hero" in names else -1

    # ------------------------------------------------------------------ Bot protocol
    def _rr_reset(self) -> None:
        self._rr_n = 0  # our first-in preflop raises (not all-in) this table
        self._rr_k = 0  # ... that faced a re-raise before the flop
        self._rr_hand = -1
        self._rr_open = False  # our first-in raise this hand, not yet re-raised

    def strong_table(self) -> bool:
        """The strong-table read: the share of our first-in raises re-raised (smoothed) is at least strong_rr."""
        c = self.cfg
        if c.strong_rr <= 0.0:
            return True
        return (self._rr_k + c.strong_prior * c.strong_prior_n) / (self._rr_n + c.strong_prior_n) >= c.strong_rr

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.panic = False
        self._rr_reset()
        for m in self.members:
            m.new_table(rules, seat, n_players)
        if self.cfg.start_level or self.level:
            self.set_level(self.cfg.start_level)
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

    def set_level(self, n: int) -> None:
        """Play at degradation level n (0 = full strength; module doc). SafeBot's governor calls it; panic is separate."""
        n = max(0, min(int(n), self.levels))
        self.level = n
        on = set(self._degrade[:n])
        self._shadows = "bare" not in on
        self._force = None
        if "hero" in on and self._hero_idx >= 0:
            self._force = (self._hero_idx, True)
        elif "base" in on:
            self._force = (0, DONORS[self.cfg.base_donor][1])
        # a forced level saves the full shadows too (the point of it); light ones keep the members' state
        self._full_shadows = self._shadows and "noshadow" not in on and self._force is None
        lean = "lean" in on
        for m in self.members:
            sl = getattr(m, "set_lean", None)
            if sl is not None:
                sl(lean)

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
        strong = self.strong
        if strong is not None:
            if obs.hand_no != self._rr_hand:
                self._rr_hand, self._rr_open = obs.hand_no, False
            elif self._rr_open and (obs.street or obs.to_call > 0):
                if not obs.street:
                    self._rr_k += 1  # we act again before the flop, facing a bet: our raise was re-raised
                self._rr_open = False
            sr = strong[sec]
            if sr is not None and self.strong_table() and (self.cfg.strong_bvb or obs.street or not _bvb(obs)):
                mi, layer = sr
                counts["strong"] += 1
        if self.level:
            counts["level:%d" % self.level] += 1
            if self._force is not None and not self.panic:
                mi, layer = self._force
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
        if not self.panic and nm > 1 and self._shadows:
            if perf_counter() - t0 > self.late:
                counts["shadow:late"] += 1
            else:
                shadowed = True
                light, lit = self.light, self._lit
                full = self._full_shadows
                for j in range(nm):
                    if j != mi and j != failed:
                        lt = light[j]
                        try:
                            if lt is not None and lt[0](members[j], obs):
                                lt[1](members[j], obs)
                                lit[j] = True
                            elif full:
                                props[j] = members[j].act(obs)
                            else:  # a degraded level: no full shadow; its record follows the action taken
                                lit[j] = True
                                counts["shadow:skip"] += 1
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
            lit = self._lit
            for j in self._rs_idx:
                # a member whose answer was not the action taken (or that did not answer: a light shadow): its record
                # of its own actions follows the one taken
                pj = props[j]
                if j != mi and states[j] is not None and (lit[j] or (pj is not None and pj != a)):
                    try:
                        resync[j][1](members[j], states[j], obs, a)
                    except Exception:  # noqa: BLE001
                        pass
            for j in range(nm):
                lit[j] = False
            tap = self.tap
            if tap is not None:
                tap(self, obs, sec, mi, own, a, props, ex)
        for j in range(nm):
            props[j] = None
        if strong is not None and not obs.street and a.kind is _RAISE and max(obs.bets) <= obs.blinds[1] \
                and a.amount < obs.max_raise:
            self._rr_n += 1  # a first-in raise that is not all-in: will it be re-raised?
            self._rr_open = True
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

    def defer_hand_end(self, on: bool = True) -> None:
        """Every member that can (HeroCore.defer_hand_end): hand_end leaves the ICM curves and dials to idle()."""
        for m in self.members:
            fn = getattr(m, "defer_hand_end", None)
            if fn is not None:
                fn(on)

    def idle(self) -> None:
        for m in self.members:
            fn = getattr(m, "idle", None)
            if fn is not None:
                try:
                    fn()
                except Exception:  # noqa: BLE001 - the next decision computes whatever is still pending
                    pass

    def stats(self) -> dict:
        return dict(self.counts)


class Composite:
    """SafeBot around CompositeCore, as Hero and the hybrids are built."""

    def __init__(self, config: ComposeConfig | None = None):
        from ..strategy.safe import governor

        self.core = CompositeCore(config)
        cfg = self.core.cfg
        self.safe = SafeBot(self.core, cfg.deadline_ms, cfg.panic_after, cfg.panic_rate,
                            governor(cfg.panic_window, cfg.panic_ladder, cfg.panic_recover, cfg.panic_backoff))

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

    def defer_hand_end(self, on: bool = True) -> None:
        """For a kit that times the hand end (CompositeCore.defer_hand_end); call idle() when there is time."""
        self.core.defer_hand_end(on)

    def idle(self) -> None:
        try:
            self.core.idle()
        except Exception:  # noqa: BLE001
            self.safe.errors += 1


def make_bot(route=None, seed: int | None = None, config: ComposeConfig | None = None, **kw) -> Composite:
    return Composite(config or compose_config(route, seed=seed, **kw))


# ---------------------------------------------------------------------------------------------- shipping
SHIP_ROUTE = "post=hero,pre_raised_short=hero"  # the route the composite ships with when the dials name none
# ... and its other dials: the guarded climb's accepted step (docs/drills/compose-log.md, "climb round 2"). ship() puts the
# dials it is given on top of these, so `hyperion.ship.make_bot("composite", {})` is the composite as measured ("F")
# The shipped dials. The SafeBot governor and degradation ladder (hyperion/ship.py's `slow_box` recipe, backlog R1) are on
# by default since the climb's batch 2: bit-identical on a normal box, +3.6 points of 100 (payouts 50/25/12/6/3/2/1/1)
# and +0.14 (8..1) on a 3x slower box, held-out seeds 20000-20199 (docs/drills/goal-log.md; decisions "The climb").
SHIP_DIALS: dict = {"route": SHIP_ROUTE, "exploit.bet_min_fold": 0.4, "hero.postflop.call_margin": 0.2,
                    "deadline_ms": 0.8, "panic_window": 60, "panic_ladder": True, "panic_recover": 40,
                    "degrade": "noshadow,lean,hero"}


def parse_dials(dials: dict | None) -> tuple:
    """One flat dials dict -> (route, make_bot keywords). The keys:
      route          "section=donor,..." (default SHIP_ROUTE)
      r3.<name>      rival 3's core in the base (hyperion/hybrid/dials.py)
      exploit.<f>    the layer's params on top of Hero's shipped set; "exploit": None for no layer
      hero.<key>     Hero's Config wherever Hero plays: the hero member (sections routed to `hero`) and the base's
                     fallback Hero (the tables it plays whole), as `hero.<key>` reaches hybrid3_x's fallback Hero
      base.<key>     any other dial for the base (`base.hero.<key>`: its fallback Hero; flat HybridConfig fields)
      cheap          every decision the base's cheap path (Hero's), no other member
      late_us, deadline_ms, panic_after, panic_rate   the shell's clocks
      panic_window, panic_ladder, panic_recover, panic_backoff, degrade   SafeBot's governor and the composite's
                     degradation levels (module doc; off by default)
      light          light shadows (ship() turns them on)
      soft_us, mc_max, ...   any flat HybridConfig field: every hybrid member (the base's soft deadline ...)"""
    d = dict(dials or {})
    route = d.pop("route", SHIP_ROUTE)
    exploit = d.pop("exploit", "hero")
    layer, base, hero = {}, {}, {}
    for k in list(d):
        head, dot, rest = k.partition(".")
        if not dot:
            continue
        v = d.pop(k)
        if head == "r3":
            base[k] = v
        elif head == "exploit":
            layer[rest] = v
        elif head == "hero":  # Hero wherever it plays: the hero member and the base's fallback Hero (variant tables)
            hero[rest] = v
            base[k] = v
        elif head == "base":
            base[rest] = v
        else:
            raise KeyError(f"unknown composite dial {k!r}")
    if d.pop("cheap", False):  # as on hybrid3_x: every decision Hero's cheap path, no reads, no layer
        base["cheap"] = True
        route = ""
        exploit, layer = None, {}
    if layer:
        if exploit is None:
            raise KeyError("exploit.* dials with the layer off")
        from ..hybrid.bot import _layer_with

        exploit = _layer_with(exploit, layer)
    from ..hybrid.bot import HybridConfig

    hyb = {}
    for k in list(d):
        if k in ComposeConfig.__dataclass_fields__ and k not in ("route", "exploit", "base_overrides", "hero_member",
                                                                 "hybrid_overrides", "hero_overrides"):
            continue
        if k in HybridConfig.__dataclass_fields__ and k not in ("hero", "r3", "exploit", "core", "seed"):
            hyb[k] = d.pop(k)  # a flat hybrid field (soft_us, mc_max ...): every hybrid member, as on hybrid3_x
            continue
        raise KeyError(f"unknown composite dial {k!r}")
    return route, {"exploit": exploit, "base_overrides": base, "hero_member": hero, "hybrid_overrides": hyb, **d}


def ship(dials: dict, seed: int | None = None) -> Composite:
    """hyperion/ship.py's builder: the composite from one flat dials dict (parse_dials) on top of SHIP_DIALS, with light
    shadows unless the dials say {"light": false} (the same play; tests/test_compose.py)."""
    dials = dict(dials or {})
    base = dict(SHIP_DIALS)
    if "exploit" in dials and dials["exploit"] is None:  # the layer off: its default params go with it
        base = {k: v for k, v in base.items() if not k.startswith("exploit.")}
    route, kw = parse_dials({**base, **dials})
    kw.setdefault("light", True)
    return make_bot(route, seed=seed, **kw)


def variant_member(parent: str, base_overrides: dict | None = None, hero_member: dict | None = None) -> str:
    """Register (this process only) a copy of member `parent` built with extra dials, as a member that can shadow:
    tools/swap.py records where a dial would change a decision this way. Returns its member name."""
    from dataclasses import replace as _replace
    import json as _json

    name = f"{parent}@" + _json.dumps({"b": base_overrides or {}, "h": hero_member or {}}, sort_keys=True)
    if name not in MEMBERS:
        build = MEMBERS[parent]
        bo, hm = dict(base_overrides or {}), dict(hero_member or {})

        def factory(cfg, seed):
            return build(_replace(cfg, base_overrides={**cfg.base_overrides, **bo}, hero_member={**cfg.hero_member, **hm}),
                         seed)

        MEMBERS[name] = factory
        if parent in RESYNC:
            RESYNC[name] = RESYNC[parent]
    return name


# ---------------------------------------------------------------------------------------------- the simulator
def sim_kwargs(kw: dict) -> dict:
    """make_bot keywords for a composite seated in the simulator: `kw` with the bestiary's HYBRID_CONFIG (panic_after,
    soft_us, ...) and HERO_CONFIG (Hero's dotted overrides) under them, as `hero` and the hybrids read them when built,
    so a model-mode run's settings reach it (register's seats and the bestiary's `f_copy`)."""
    from ..sim import bestiary as B

    kw2 = dict(kw)
    hyb = dict(B.HYBRID_CONFIG or {})
    panic = hyb.pop("panic_after", None)
    if panic is not None:
        kw2.setdefault("panic_after", panic)
    if hyb.get("soft_us", 0) >= 1e5:
        kw2.setdefault("late_us", 1e9)  # deterministic runs: nothing reads the wall clock
    kw2["hybrid_overrides"] = {**hyb, **kw2.get("hybrid_overrides", {})}
    kw2["hero_overrides"] = {**(B.HERO_CONFIG or {}), **kw2.get("hero_overrides", {})}
    return kw2


def register(name: str, route=None, dials: dict | None = None, **kw) -> type:
    """Seat a composite in the simulator under `name` (this process only): `<field>@<name>` puts it in Hero's seat.
    Give a route and make_bot keywords, or one flat `dials` dict (parse_dials). It reads the bestiary's HERO_CONFIG
    (Hero's dotted overrides) and HYBRID_CONFIG (panic_after, soft_us, ...) when built, as `hero` and the hybrids do, so
    a model-mode run's settings reach it."""
    from ..sim import bestiary as B

    if dials is not None:
        route, dkw = parse_dials(dials)
        kw = {**dkw, **kw}
    fixed = dict(kw)

    class _Seat(B._Base):
        ROUTE = route
        KW = fixed

        def __init__(self, seed=None):
            super().__init__(seed)
            self.impl = make_bot(self.ROUTE, seed=seed, **sim_kwargs(self.KW))

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


__all__ = ["COUNTS", "Composite", "CompositeCore", "ComposeConfig", "DONORS", "KitMember", "MEMBERS", "SHIP_DIALS", "SHIP_ROUTE",
           "compose_config", "make_bot", "parse_dials", "register", "register_member", "ship", "sim_kwargs",
           "variant_member"]
