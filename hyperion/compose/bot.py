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
  r2s      rival 2's core for the strong-table route (S14): as r2, but its generator seeded per decision, a light
           shadow (no Monte Carlo when not chosen), its ICM curve built at its first read, plain hold'em only.
           Donors `r2s`, `r2sx` (the layer on).
  rival1   red-team rival 1 as built, through the kit adapter the bestiary uses. Donor `rival1`; `rival1x` with the layer.
  rival3   red-team rival 3 as built (brief's payouts in its ICM, no shell). Donor `rival3`; `rival3x` with the layer.
  elite1, elite2, elite4   the climb's elite builds as built (PersonaMember: payouts and history as the bestiary passes
           them, the generator seeded per decision). Donors `elite1`, `elite2`, `elite4`; `elite1x`, `elite2x`,
           `elite4x` with the layer (S9; elite4, the second wave's tuning build, S14). elite3 and elite5 are held-out
           judges and are never members.
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
`fallback:plain`). Hero and the hybrid members play every table (r2s, the strong route's rival 2, only plain hold'em).
A strong-route donor that cannot play the table hands the decision to the section's own donor (Hero in Hero's
sections), so the route never changes play on such a table.

**Tables Hero plays whole** (H6). On a table the base's core cannot play at all (HybridCore._table_why: short deck,
must-use, three hole cards, wild cards, two boards, fixed limit ...), every decision of the base's is its fallback
Hero's, a HeroCore with the hero member's Config (checked at build: `_same_hero`), the same seed, and the same
observations and hand ends. The hero member plays the base's sections there instead (counted under its own name, as
`<section>:hero`), and the base sleeps (`_whole`): it neither decides nor shadows, its Hero gets no hand end (the ICM
curve and the profiler's dials, computed twice before; drill 10's kit sim: about 280 us of CPU a hand, the next
message already waiting), and the variant prompts go to the hero member. Play is the same, seed for seed.

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
`strong_bvb` (True: every section; or the sections it names, S14). Its donors' members run (and shadow) on every
decision, like any routed member's.

**The second strong-table route** (S14, `strong2_route`, off by default): more sections on the same read, played while
it is in [`strong2_rr`, `strong2_rr_max`): a table where nearly every open of ours is re-raised holds an exploiter, and
F's own play (its 3-bet defence) is kept there. Blind-vs-blind as `strong_bvb` says.

**The steal reads' trust weight** (S16, `r3.read_trust` and `exploit.read_trust`, off by default). Before each preflop
decision on a hold'em table (hero.holdem_table) the composite marks the seats whose fold reads in an unopened pot take a
trust weight: every seat while the hero member's profiler reads the table strong (Profiler.strong_table at
`strong_rr` / `strong_prior` / `strong_prior_n`, the strong route's threshold), and with `trust_seat_rr` k > 0 also a
seat that re-raised at least k of my first-in raises this table. Rival 3's core then prices its steal and its open
clauses, and the layer its steal_min_fold, with each marked seat's fold read at most prior + (observed - prior) x
n / (n + read_trust) (n the raises it faced; the prior alone below `read_trust_min_n`). The defensive reads (the 3-bet
defence, the size and probe reads) are untouched (docs/drills/climb/s16-log.md).

**The open-answer read** (S16b, `r3.oa_read` and `exploit.open_read`, off by default). Rival 3's core counts, at each
hand end, how every seat answered my first-in raise (not all-in): folds against a prior by position (the small
blind, the big blind, the rest). With `r3.oa_read` its steal price and open clauses in an unopened pot with no limper
read each seat behind from that instead of its fold rate facing any raise; with `exploit.open_read` the layer's
steal_min_fold reads the same (`Exploit.open_fold`, wired here to the base's core). docs/drills/climb/s16b-log.md.
With `oa_strong` (S21, off by default) both act only while the table reads strong (strong_table(): the strong route's
read and threshold, `strong_rr`, `strong_prior`, `strong_prior_n`), set before each preflop decision; the core goes on
counting the answers all table long, so the read is warm when it opens (docs/drills/climb/s21-log.md).
O5 (`r3.bb_read`, `r3.oa_bb_only`, `exploit.open_bb_only`, off by default): the big blind's fold reads its answers as
the big blind to a first-in raise by any seat this table, with its fold-to-any-raise read as the prior (weight
`r3.bb_k`), in both places; the other seats keep their own reads (docs/drills/climb/s21-log.md, "O5").

**The short-handed route** (S13, `short_route`, off by default): sections played by another donor (the specialist
`short`, hyperion/strategy/short.py) while at most `short_alive` players have chips and that member `wants` the decision
(the hand maps onto its tables, no opponent alive reads as a clear leak); otherwise the section's donor as above. The
member's dials are `short.<name>` (short_params). Plain hold'em tables only (holdem_only, plain_only), like the elite
builds; its light shadow records only the hand's starting chips.
"""
from __future__ import annotations

from collections import Counter
from copy import copy
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
        m.btn_seen = (obs.hand_no, obs.button)
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
    """An elite build from hyperion.sim.field (elite1, elite2, elite4: our own agents' prepared top-team bots) as a member,
    through the adapter the bestiary's PersonaBot plays it with: the payouts in the rules dict, the hand's history at
    hand_end, and its generator (each was written with an unseeded random.Random()) reseeded from the member's seed at
    every table start, as the bestiary's _EliteBot does, so a table replays exactly. Plain hold'em only, like every raw
    rival. Backlog S9: a section of F can be routed to one of them (donors `elite1`, `elite2`; `...x` with the layer)."""

    # built for plain no-limit hold'em and blind to every twist: on a table that is not hold'em by Hero's test
    # (hero.holdem_table: only payouts, blinds, antes or a straddle may differ) the composite plays the base instead
    holdem_only = True

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


def _fold(*args, **kw):
    return ("fold", 0)


# elite2 keeps its reads in the hand's replay (`rp`, fed from the history at each decision and at hand_end) and the
# per-seat counters the replay updates; its decision writes only scratch values it sets again before reading them
# (`_fc`, `_raw`). Its light shadow runs its act with the decision taken out (preflop / postflop answer a fold, which
# its act then legalizes), so the replay is fed exactly as a full decision feeds it (S14).
def _elite2_light(m, obs: Observation) -> None:
    b = m.impl
    b.preflop = b.postflop = _fold  # instance attributes hide the methods: the replay runs, the decision does not
    try:
        b.act(m.kit(obs, obs.hole, obs.board))
    finally:
        del b.preflop, b.postflop


# elite4 keeps its reads from the history it ingests at each decision and at hand_end (`_ingest`: per-seat counters,
# the hand's street and raise state); its preflop and postflop decisions write nothing it keeps (they draw from its
# generator, which PersonaMember seeds per decision). Its light shadow runs `_act` with the decision taken out (S14).
def _elite4_light(m, obs: Observation) -> None:
    b = m.impl
    b._preflop = b._postflop = _none
    try:
        b._act(m.kit(obs, obs.hole, obs.board))
    finally:
        del b._preflop, b._postflop


# r2s (S14): rival 2's core behind the same shell as the `r2` member, for the strong-table route. Four changes from r2,
# none to rival 2's code: (1) its generator is seeded per decision (from the member's seed, the hand, the street and the
# history's length), as the elite members' are, so a decision's draws never depend on which earlier decisions it made
# in full; (2) a light shadow: its decision is not computed (preflop: nothing; postflop: its own code up to the Monte
# Carlo, about 260 us a decision as built, so its first-sight range cuts are set as a full decision sets them), while
# its read of the hand (the history replay, the per-seat counters) runs as in full; (3) what its own decision would
# have written ("we re-raised preflop", "we were the aggressor this street") always follows the action taken when it
# was not chosen (RESYNC_ALWAYS), so a light shadow and a full one leave the same state; (4) the hand's ICM curve
# (hybrid.core.build_curve, ~20 us at a hand end) is built from the same hand-start chips at the first decision that
# reads it, not at every hand end: the same values, paid only on hands where rival 2 decides. Plain hold'em only
# (plain_only, holdem_only), like the elite members.
_NO = object()


class _Stop(Exception):
    """Raised in place of rival 2's postflop Monte Carlo in a light shadow: the decision stops there."""


def _stop(*args, **kw):
    raise _Stop()


_LAZY_CURVE = None


def _lazy_curve_class():
    global _LAZY_CURVE
    if _LAZY_CURVE is None:
        from ..hybrid.core import R2, build_curve

        class LazyCurve(R2.Curve):
            """rival 2's Curve, built (hybrid.core.build_curve) at its first read: every read goes through u()."""
            __slots__ = ("_args",)

            def __init__(self, totals, me, payouts):  # noqa: D107 - the parent's slots are filled at the first read
                self._args = (totals, me, payouts)

            def u(self, x):
                a = self._args
                if a is not None:
                    c = build_curve(*a)
                    self.xs, self.us = c.xs, c.us
                    self._args = None
                return R2.Curve.u(self, x)

        _LAZY_CURVE = LazyCurve
    return _LAZY_CURVE


def _r2s_member(cfg, seed):
    m = _hybrid_member("rival2", cfg, seed)
    m.plain_only = True
    m.holdem_only = True
    core = m.core
    s0 = 0 if seed is None else int(seed)
    real_pf, real_post = core._preflop, core._postflop
    core._r2_pre = None  # (hand, street, we_raised_pre, street_aggr[street]) when its decision started
    core._r2_light = False

    def pf(obs, *rest):
        core._r2_pre = (core.cur, 0, core.we_raised_pre, core.street_aggr.get(0, _NO))
        return None if core._r2_light else real_pf(obs, *rest)

    def post(obs, *rest):
        st = obs.street
        core._r2_pre = (core.cur, st, core.we_raised_pre, core.street_aggr.get(st, _NO))
        if not core._r2_light:
            return real_post(obs, *rest)
        core.equity_mc = _stop  # the instance attribute hides the method: the decision stops at the Monte Carlo
        try:
            return real_post(obs, *rest)
        except _Stop:
            return None
        finally:
            del core.equity_mc

    lazy = _lazy_curve_class()

    def prime(kit_hand_no, totals):
        t = list(totals)
        core._pending = (kit_hand_no, t, lazy(t, core.me, core.payouts))

    core._preflop, core._postflop, core.prime = pf, post, prime
    act = m.act

    def seeded_act(obs):
        core.rng.seed(((s0 * 1_000_003 + obs.hand_no) * 4 + obs.street) * 1024 + len(obs.history))
        return act(obs)

    m.act = seeded_act
    return m


def _r2s_light_ok(m, obs: Observation) -> bool:
    """The shell would hand this decision to the core (HybridCore._decide), not to its fallback Hero."""
    return not m.panic and not m._cheap and m._table_why is None and len(obs.hole) == 2 \
        and not (obs.street == 0 and m._straddle) and len(obs.board) <= 5


def _r2s_light(m, obs: Observation) -> None:
    hole, board = obs.hole, obs.board
    rm = m._remap
    if rm is not None:
        from ..core.cards import remap

        hole, board = remap(hole, rm), remap(board, rm)
    m._core_hand = obs.hand_no
    core = m.core
    core._r2_light = True
    try:
        core.decide(m.kit(obs, hole, board), perf_counter())
    finally:
        core._r2_light = False


def _r2s_state(m):
    m.core._r2_pre = None
    return True


def _r2s_resync(m, before, obs: Observation, taken: Action) -> None:
    core = m.core
    p = core._r2_pre
    core._r2_pre = None
    if p is None or p[0] != core.cur:  # the core did not decide here (its shell's Hero did)
        return
    _, st, wrp, sa = p
    is_raise = taken.kind is _RAISE
    if st == 0:  # rival 2 marks its preflop re-raises (not its opens: those it reads from the history)
        core.we_raised_pre = bool(wrp or (is_raise and max(obs.bets) > obs.blinds[1]))
    elif is_raise and taken.amount < obs.max_raise:  # ... and its postflop bets and raises that are not all-in
        core.street_aggr[st] = core.me
    elif sa is _NO:
        core.street_aggr.pop(st, None)
    else:
        core.street_aggr[st] = sa


def _short_member(cfg, seed):
    from ..strategy.short import short_member

    return short_member(cfg, seed)


# name -> factory(cfg, seed) -> member (new_table / act / hand_end, optional set_panic and variant_decide; plain_only)
MEMBERS: dict[str, Callable] = {
    "base": lambda cfg, seed: _hybrid_member("rival3", cfg, seed),
    "hero": _hero_member,
    "r2": lambda cfg, seed: _hybrid_member("rival2", cfg, seed),
    "r2s": _r2s_member,  # S14: rival 2's core, seeded per decision, light shadow, plain hold'em only
    "rival1": _rival_member("rival1", False),
    "rival3": _rival_member("rival3", True),
    "elite1": _persona_member("elite1"),
    "elite2": _persona_member("elite2"),
    "elite4": _persona_member("elite4"),  # S14: the second wave's solver-minded build (a tuning bot; elite3/5 judge)
    "short": _short_member,
}
# member name -> (state(member) captured before act, resync(member, state, obs, taken) when its answer was not taken)
RESYNC: dict[str, tuple] = {
    "base": (lambda m: _r3_state(m.core), lambda m, st, obs, a: _resync_r3(m.core, st, obs, a)),
    "rival3": (lambda m: _r3_state(m.impl), lambda m, st, obs, a: _resync_r3(m.impl, st, obs, a)),
    "hero": (_hero_state, _resync_hero),
    "elite1": (lambda m: True, _elite1_resync),
    "r2s": (_r2s_state, _r2s_resync),
}
# members whose record of their own actions follows the action taken whenever they were not chosen, even when their own
# answer was the same (r2s: so that a full shadow and a light one leave the same state)
RESYNC_ALWAYS: set = {"r2s"}
# member name -> (can a light shadow stand in for its decision on this observation, the light shadow)
LIGHT: dict[str, tuple] = {
    "hero": (_hero_light_ok, _hero_light),
    "base": (_base_light_ok, _base_light),
    "elite1": (lambda m, obs: True, _elite1_light),
    "elite2": (lambda m, obs: True, _elite2_light),  # S14
    "elite4": (lambda m, obs: True, _elite4_light),  # S14
    "r2s": (_r2s_light_ok, _r2s_light),  # S14
    "short": (lambda m, obs: True, lambda m, obs: m.light_observe(obs)),  # S13: it keeps only the hand's start chips
}
# members whose light shadow is used even without `light` (the deterministic runs, tools/climb_accept.py's seats): it
# plays exactly as the full one (tests/test_sim_mirror.py), so a full shadow only adds cost, and the simulator's timing
# columns should show what the shipped bot pays. elite1's full shadow decided on every one of our decisions (about 30 us,
# a tail past 1 ms on a loaded host); its light one scans the history (about 6 us)
ALWAYS_LIGHT: set = {"elite1", "elite2", "elite4", "r2s", "short"}
# donor name -> (member, the exploit layer acts on its decisions)
DONORS: dict[str, tuple[str, bool]] = {
    "base": ("base", True), "hybrid3": ("base", False),
    "hero": ("hero", True), "hero_nl": ("hero", False),
    "r2x": ("r2", True), "r2": ("r2", False),
    "r2sx": ("r2s", True), "r2s": ("r2s", False),
    "rival1": ("rival1", False), "rival1x": ("rival1", True),
    "rival3": ("rival3", False), "rival3x": ("rival3", True),
    "elite1": ("elite1", False), "elite1x": ("elite1", True),
    "elite2": ("elite2", False), "elite2x": ("elite2", True),
    "elite4": ("elite4", False), "elite4x": ("elite4", True),
    "short": ("short", False), "shortx": ("short", True),
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
    strong_bvb: object = False  # True = every section; or section names ("pre_hu,pre_3way": those only; S14)
    # a second strong-table route (S14) on the same read with its own band: these sections go to these donors while the
    # read is at least `strong2_rr` and under `strong2_rr_max`. A table where our opens are re-raised nearly every time
    # holds an exploiter, not strong general bots, and F's own play (its 3-bet defence) is the one to keep there.
    # Blind-vs-blind unopened pots as `strong_bvb` says. Empty (the default): no second route
    strong2_route: dict = field(default_factory=dict)
    strong2_rr: float = 0.0
    strong2_rr_max: float = 1.01
    # ... and a preflop decision where our own raise this hand has been re-raised stays the section's own donor's (F's
    # 3-bet defence, batch 4): the second route's donor opens and answers others' raises only
    strong2_keep_defence: bool = False
    # the short-handed route (S13, module doc of hyperion/strategy/short.py): these sections go to these donors while at
    # most `short_alive` players have chips and the donor's member wants the decision (the hand maps onto its tables,
    # no opponent alive reads as a clear leak). Empty (the default): every section as `route` / `strong_route` say
    short_route: dict = field(default_factory=dict)
    short_alive: int = 3
    short_params: dict = field(default_factory=dict)  # the specialist's dials (strategy.short.ShortParams)
    # V-f: the hold'em-only members (the elite builds, twist-blind) may also play their sections on tables of these
    # one-step twist families (hero.TWIST_FAMILIES: "bounty,knockout,buy,swap"), where their play stays as right as the
    # base's: the base's core plays the table too (two hole cards; the families Hero plays whole, discard and exposed,
    # stay the base's whatever is listed) and is blind to the same twist. "" = hold'em tables only
    strong_route_twists: str = ""
    # S16 (module doc): the trust weight on the steal reads (r3.read_trust, exploit.read_trust) applies to every seat
    # while the hero member's profiler reads the table strong (strong_rr / strong_prior / strong_prior_n), and with
    # this > 0 also to a seat that re-raised at least this many of my first-in raises this table (the per-seat gate)
    trust_seat_rr: int = 0
    # S21 (module doc): the open-answer read (r3.oa_read, exploit.open_read) acts only while the table reads strong
    # (strong_table(): the strong route's read and threshold); off = wherever its own dials let it
    oa_strong: bool = False
    # V-j (docs/drills/climb/vj-log.md): payoff by street. On a table whose Rules settle each street's chips on the
    # hand as it stood then (extras settle="street"), every preflop decision is shown, to every member, the hold'em
    # class at the same combo percentile as our hand's two-card rank (a pair over any non-pair, then the high card,
    # then the kicker; suits never count): drill 11's adapter patch (twin_hole), keyed on the rule. "all": so on a
    # street-settled table; on a table that only settles all-ins on the cards out (extras no_runout), the all-in
    # decisions alone (effective stack 20 bb or less, or a call of 40% of our stack or more). "allin": the all-in
    # decisions alone on either. "" = off (the real cards everywhere)
    tranche_twin: str = ""
    seed: int | None = None


def compose_config(route=None, seed=None, **kw) -> ComposeConfig:
    cfg = ComposeConfig(seed=seed, **kw)
    cfg.route = parse_route(route)
    cfg.strong_route = parse_route(cfg.strong_route)
    cfg.strong2_route = parse_route(cfg.strong2_route)
    cfg.short_route = parse_route(cfg.short_route)
    for r in (cfg.route, cfg.strong_route, cfg.strong2_route, cfg.short_route):
        for sec, d in r.items():
            if sec not in SECTIONS:
                raise KeyError(f"unknown section {sec!r}")
            if d not in DONORS:
                raise KeyError(f"unknown donor {d!r} for {sec}; known: {', '.join(DONORS)}")
    if cfg.strong_route_twists:
        from ..strategy.hero import twist_families

        twist_families(cfg.strong_route_twists)  # an unknown family fails here, not at a table start
    if cfg.tranche_twin not in ("", "all", "allin"):
        raise KeyError(f"tranche_twin must be '', 'all' or 'allin', got {cfg.tranche_twin!r}")
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
        self._obs = None  # the last decision's observation (variant_decide passes it to the base's Hero)
        self._twin = None  # tranche_twin on this table: (two-card key -> twin cards, every preflop decision)
        self.cfg = cfg = config or ComposeConfig()
        donors = [cfg.route.get(s, cfg.base_donor) for s in SECTIONS]
        names = ["base"]  # index 0 is always the base
        for d in donors + [cfg.strong_route[s] for s in SECTIONS if s in cfg.strong_route] \
                + [cfg.strong2_route[s] for s in SECTIONS if s in cfg.strong2_route] \
                + [cfg.short_route[s] for s in SECTIONS if s in cfg.short_route]:
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
        s2 = cfg.strong2_route
        self.strong2 = [(idx[DONORS[s2[s]][0]], DONORS[s2[s]][1]) if s in s2 else None for s in SECTIONS] if s2 else None
        # keep the read (the strong routes, and S21's gate on the open-answer read)
        self._rr_on = self.strong is not None or self.strong2 is not None or cfg.oa_strong
        bvb = cfg.strong_bvb
        if isinstance(bvb, str):
            bvb = set(parse_route({k.strip(): "1" for k in bvb.split(",") if k.strip()}))
        self._sbvb = [bool(bvb is True or (isinstance(bvb, set) and s in bvb)) for s in SECTIONS]
        hr = cfg.short_route
        self.short = [(idx[DONORS[hr[s]][0]], DONORS[hr[s]][1]) if s in hr else None for s in SECTIONS] if hr else None
        self._rr_reset()
        self.donors = donors
        self.plain_only = [bool(getattr(m, "plain_only", False)) for m in self.members]
        # members built for plain hold'em only (the elite builds: twist-blind, and their jams would be clamped to a
        # pot-limit raise): on a twist table the base plays their sections
        self._h_only = [bool(getattr(m, "holdem_only", False)) for m in self.members]
        self._no_h = [False] * len(self.members)  # per member: plays the base here (this table is not hold'em)
        self.resync = [RESYNC.get(n) for n in names]
        self._rs_idx = [j for j, r in enumerate(self.resync) if r is not None]
        self._rs_always = [n in RESYNC_ALWAYS for n in names]
        self.light = [LIGHT.get(n) if cfg.light or n in ALWAYS_LIGHT else None for n in names]
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
        # H6 (module doc): the hero member plays the tables the base's core cannot, when its Config is the base's Hero's
        hm = self.members[self._hero_idx] if self._hero_idx >= 0 else None
        bh = getattr(self.base, "hero", None)
        self._same_hero = hm is not None and bh is not None and getattr(hm, "cfg", None) == getattr(bh, "cfg", 0) \
            and hasattr(self.base, "sleep")
        self._whole = False
        # S16: the steal reads' trust weight (module doc); off unless a read_trust dial is on
        core = getattr(self.base, "core", None)
        r3k = getattr(getattr(self.base, "cfg", None), "r3", None)
        self._trust_core = core if r3k is not None and getattr(r3k, "read_trust", 0.0) > 0.0 else None
        self._trust_ex = self.ex if self.ex is not None and self.ex.p.read_trust > 0.0 else None
        self._trust_prof = None
        if (self._trust_core is not None or self._trust_ex is not None) and self._hero_idx >= 0:
            self._trust_prof = getattr(self.members[self._hero_idx], "prof", None)
            if self._trust_prof is not None:
                self._trust_prof.track_s12 = True  # the strong-table counts (the shipped size read turns it on too)
        self._trust_h = False
        # S16b: the layer's steal read from rival 3's core's open-answer read (exploit.open_read; hold'em tables)
        self._oa_core = None
        if self.ex is not None and self.ex.p.open_read and core is not None and hasattr(core, "oa_fold"):
            core.oa_count = True
            self._oa_core = core
        self._oa_fn = None  # ... the layer's read on this table (None: not a hold'em table, or a straddle)
        # S21 (oa_strong): the core whose open-answer read waits while the table does not read strong
        self._oa_gcore = core if cfg.oa_strong and r3k is not None and getattr(r3k, "oa_read", False) \
            and hasattr(core, "oa_on") else None
        self._oa_gate = cfg.oa_strong and (self._oa_gcore is not None or self._oa_core is not None)

    # ------------------------------------------------------------------ Bot protocol
    def _rr_reset(self) -> None:
        self._raised_hand = -1  # the hand in which we last raised preflop (strong2_keep_defence)
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

    def rr_read(self) -> float:
        """The share of our first-in raises re-raised this table, smoothed toward strong_prior."""
        c = self.cfg
        return (self._rr_k + c.strong_prior * c.strong_prior_n) / (self._rr_n + c.strong_prior_n)

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.panic = False
        self._obs = None
        self._rr_reset()
        self._twin = None
        tw = self.cfg.tranche_twin
        if tw and rules.hole_cards == 2 and is_identity_order(rules):
            from ..strategy import tranche as _tr

            st = _tr.street_settled(rules)
            if st or _tr.no_runout(rules):
                from ..strategy.tables import load as _load

                self._twin = (_tr.twin_cards_map(_load().rank), tw == "all" and st)
        for m in self.members:
            m.new_table(rules, seat, n_players)
        if self.cfg.start_level or self.level:
            self.set_level(self.cfg.start_level)
        b = self.base
        self.plain = getattr(b, "_table_why", None) is None and not getattr(b, "_straddle", False) \
            and is_identity_order(rules)
        self._whole = self._same_hero and getattr(b, "_table_why", None) is not None and not getattr(b, "_cheap", False)
        if self._same_hero:
            b.sleep(self._whole)
        if any(self._h_only):
            from ..strategy.hero import holdem_table, twist_families, twist_family

            h = holdem_table(rules)
            if not h and self.cfg.strong_route_twists:
                h = twist_family(rules) in twist_families(self.cfg.strong_route_twists)
            self._no_h = [x and not h for x in self._h_only]
        if self.ex is not None:
            self.ex.new_table(n_players, seat)
            if self.ex.p.stab_size:  # S17: the stab takes the one size of the member that plays postflop (Hero)
                hi = self._hero_idx
                h = self.members[hi] if hi >= 0 else getattr(self.base, "hero", None)
                from ..strategy.hero import holdem_table

                self.ex.size_from(getattr(h, "postflop", None), holdem_table(rules))
        if self._trust_prof is not None:
            from ..strategy.hero import holdem_table

            self._trust_h = holdem_table(rules)
        if self._oa_core is not None:
            from ..strategy.hero import holdem_table

            self.ex.open_fold = self._oa_core.oa_fold if holdem_table(rules) and not rules.straddle else None
            self._oa_fn = self.ex.open_fold

    def _trust_gate(self, obs: Observation) -> None:
        """S16: mark, before a preflop decision, the seats whose steal reads take the trust weight (module doc)."""
        g = None
        if not obs.street and self._trust_h:
            prof, c = self._trust_prof, self.cfg
            n = len(obs.stacks)
            if prof.strong_table(c.strong_rr, c.strong_prior, c.strong_prior_n):
                g = [True] * n
            elif c.trust_seat_rr > 0:
                k = c.trust_seat_rr
                rb = prof.rr_by
                g = [s < len(rb) and rb[s] >= k for s in range(n)]
                if not any(g):
                    g = None
        if self._trust_core is not None:
            self._trust_core.trust = g
        if self._trust_ex is not None:
            self._trust_ex.trust = g

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

    def _twin_obs(self, obs: Observation):
        """tranche_twin: this preflop decision with the hold'em twin of our two-card rank in place of the hole cards,
        or None where it does not apply (an all-in-only table and a deep decision)."""
        cards, every = self._twin
        hole = obs.hole
        if len(hole) != 2:
            return None
        if not every:
            me, st, bt = obs.seat, obs.stacks, obs.bets
            other = max((st[s] + bt[s] for s in range(len(st)) if s != me and obs.in_hand[s]), default=0)
            if min(st[me] + bt[me], other) > 20 * obs.blinds[1] and not (st[me] > 0 and obs.to_call >= 0.4 * st[me]):
                return None
        a, b = hole[0] >> 2, hole[1] >> 2
        o = copy(obs)
        o.hole = cards[(a, b) if a >= b else (b, a)]
        return o

    def act(self, obs: Observation) -> Action:
        t0 = perf_counter()
        if self._twin is not None and not obs.street:
            o = self._twin_obs(obs)
            if o is not None:
                obs = o
        self._obs = obs  # the last decision's observation, for the variant decisions (variant_decide)
        ex = self.ex
        if ex is not None:
            try:
                ex.observe(obs)
            except Exception:  # noqa: BLE001 - a slip in the layer keeps the members' decision
                ex = None
        if self._trust_prof is not None:
            try:
                self._trust_gate(obs)
            except Exception:  # noqa: BLE001 - a slip in the gate leaves the reads as they are
                pass
        sec = section(obs)
        self.last_section = sec
        mi, layer = self.route[sec]
        counts = self.counts
        strong = self.strong
        rr_on = self._rr_on
        if rr_on:
            if obs.hand_no != self._rr_hand:
                self._rr_hand, self._rr_open = obs.hand_no, False
            elif self._rr_open and (obs.street or obs.to_call > 0):
                if not obs.street:
                    self._rr_k += 1  # we act again before the flop, facing a bet: our raise was re-raised
                self._rr_open = False
            if strong is not None:
                sr = strong[sec]
                if sr is not None and self.strong_table() and (self._sbvb[sec] or obs.street or not _bvb(obs)):
                    mi, layer = sr
                    counts["strong"] += 1
            strong2 = self.strong2
            if strong2 is not None:
                s2 = strong2[sec]
                if s2 is not None and (self._sbvb[sec] or obs.street or not _bvb(obs)) and not (
                        self.cfg.strong2_keep_defence and not obs.street and obs.to_call > 0
                        and self._raised_hand == obs.hand_no):
                    c2 = self.cfg
                    r = self.rr_read()
                    if (c2.strong2_rr <= 0.0 or r >= c2.strong2_rr) and r < c2.strong2_rr_max:
                        mi, layer = s2
                        counts["strong2"] += 1
        if self._oa_gate and not obs.street:  # S21: the open-answer read only while the table reads strong
            on = self.strong_table()
            if self._oa_gcore is not None:
                self._oa_gcore.oa_on = on
            if self._oa_core is not None:
                self.ex.open_fold = self._oa_fn if on else None
        short = self.short
        if short is not None and short[sec] is not None and not self.panic and self.plain:
            si, sl = short[sec]
            if not self._no_h[si]:
                alive = 0
                for s_, b_, h_ in zip(obs.stacks, obs.bets, obs.in_hand):
                    if s_ + b_ > 0 or h_:
                        alive += 1
                if alive <= self.cfg.short_alive:
                    hi = self._hero_idx
                    prof = getattr(self.members[hi], "prof", None) if hi >= 0 else None
                    try:
                        ok = self.members[si].wants(obs, prof, self.base)
                    except Exception:  # noqa: BLE001 - a slip in the read keeps F's route
                        ok = False
                        counts["short:error"] += 1
                    if ok:
                        mi, layer = si, sl
                        counts["short"] += 1
        if self.level:
            counts["level:%d" % self.level] += 1
            if self._force is not None and not self.panic:
                mi, layer = self._force
        if self.panic:  # SafeBot saw repeated overruns: the base alone (Hero's cheap path) for the rest of the table
            mi, layer = 0, True
        elif mi and self.plain_only[mi] and (not self.plain or self._no_h[mi]):
            counts["fallback:plain"] += 1
            ri, rl = self.route[sec]
            if ri and ri != mi and not (self.plain_only[ri] and (not self.plain or self._no_h[ri])):
                mi, layer = ri, rl  # a strong-route donor that cannot play this table: the section's own donor (S14)
            else:
                mi = 0
        whole = self._whole
        if whole and not mi:
            mi = self._hero_idx  # a table Hero plays whole: the base's Hero would play as the hero member does
        members, resync = self.members, self.resync
        nm = len(members)
        states = self._states
        for j in self._rs_idx:
            if j != mi:
                if whole and not j:  # the base sleeps: nothing of its own to follow
                    states[j] = None
                    continue
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
                    if j != mi and j != failed and not (whole and not j):
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
                if j != mi and states[j] is not None and (lit[j] or (pj is not None and pj != a) or self._rs_always[j]):
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
        if rr_on and not obs.street and a.kind is _RAISE:
            self._raised_hand = obs.hand_no
        if rr_on and not obs.street and a.kind is _RAISE and max(obs.bets) <= obs.blinds[1] \
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
        # the base's Hero makes it, and sees few of the hand's observations (the members decide): it gets ours, the
        # last decision's, for what the prompt does not carry (V-i's option prices: the pot, the opponents in)
        o = self._obs
        if o is not None and "last_obs" not in prompt:
            prompt = {**prompt, "last_obs": o}
        if self._whole:
            return self.members[self._hero_idx].variant_decide(prompt)
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
                    "degrade": "noshadow,lean,hero",
                    # batch 3 (V-b): twist tables only, plain hold'em identical (docs/decisions.md)
                    "hero.variant_preflop": {"call_raise_frac": 0.15, "three_bet_frac": 0.05},
                    "hero.toss_value_shift": 2, "hero.toss_dead": True, "base.hero_on_bounty": False,
                    # batch 4: the 3-bet defence (exploit resistance, addendum 6) and V-c's variant dials
                    "r3.v3_defend": True,
                    "hero.long_board": True, "hero.keep_call_shift": 2, "hero.toss_call_shift": 1,
                    # batch 5: strong tables (S9's route, S12c's size read), the second exploiter's fixes (S11, both
                    # gated to hold'em) and V-e's twist play (docs/decisions.md)
                    "strong_route": "pre_open_10=elite1x", "strong_rr": 0.2,
                    "hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0,
                    "hero.postflop.size_read_min_alive": 4, "hero.postflop.size_read_holdem_only": True,
                    "hero.postflop.size_read_min_bets": 2, "hero.postflop.size_read_min_share": 0.15,
                    "hero.postflop.size_read_min_buckets": 2, "hero.postflop.size_read_skip_weak": True,
                    "hero.postflop.size_read_streets": 3, "hero.postflop.size_read_min_cbet": 0.55,
                    "r3.v3_bvb_prior": 0.15, "r3.v3_bvb_holdem_only": True,
                    "hero.postflop.probe_from": 0.75, "hero.postflop.probe_n": 2, "hero.postflop.probe_margin": 0.03,
                    "hero.postflop.probe_raise_tier": 5, "hero.postflop.probe_bluff": 0.4,
                    "hero.postflop.balance_sizes": True, "hero.postflop.s11_holdem_only": True,
                    "hero.twin_preflop": 0.05, "hero.twin_multi": 0.07, "hero.multi_call_shift": 2,
                    "hero.mu_call_shift": 1, "hero.mu_value_shift": 1, "hero.call_shift_ex": {"wild": 2, "deck": 1},
                    # batch 6: twist tables only, plain hold'em identical (docs/decisions.md): V-f's per-family twist
                    # dials (H15) and V-h's known opponent cards (H18)
                    "hero.postflop.size_read_twists": "discard,bounty,knockout,swap,exposed",
                    "hero.postflop.s11_twists": "knockout,buy,swap,exposed", "strong_route_twists": "bounty,knockout,buy",
                    "hero.known_cards": "pre",
                    # batch 7 (docs/decisions.md): V-i's value of information on twist decisions (H23) and V-j's c6,
                    # the street-settled tables (H29), twist tables only; S7's heads-up specialist routes behind its
                    # looseness gate (H25) and S15e's gated stab read (H26), plain hold'em with three or fewer alive
                    "hero.voi": 1.5, "hero.sd_tax": True,
                    "tranche_twin": "all", "hero.tranche": "now,sunk", "hero.tranche_claim_early": 0.25,
                    "short_route": "pre_hu=short,post_hu_bet=short,post_hu_chk=short", "short.pre_roles": "bb",
                    "short.pre_open_min": 0.65, "short.like_probe": 0.75, "short.like_bet": 0.6, "short.like_pfr": 0.3,
                    "short.like_vpip_min": 0.5, "short.like_vpip_max": 0.88,
                    "hero.postflop.stab_from": 0.55, "hero.postflop.stab_full": 0.8, "hero.postflop.stab_prior": 0.4,
                    "hero.postflop.stab_min": 3, "hero.postflop.stab_pool": 7, "hero.postflop.stab_margin": 0.03,
                    "hero.postflop.stab_max_alive": 3, "hero.postflop.stab_pfr_min": 0.35,
                    "hero.postflop.stab_lead_max": 0.4, "hero.postflop.stab_free_max": 0.5,
                    "hero.postflop.stab_holdem_only": True}


# Batch 5's dials at their off values: on top of SHIP_DIALS they play batch 4's ship from this tree (the tests written
# against batch 4's F, and a paired check against the previous batch: --base '{"dials": BATCH5_OFF}').
BATCH5_OFF: dict = {"strong_route": "", "strong_rr": 0.0,
                    "hero.postflop.size_read": 0.0, "hero.postflop.size_read_rank": 0.0,
                    "hero.postflop.size_read_min_alive": 0, "hero.postflop.size_read_holdem_only": False,
                    "hero.postflop.size_read_min_bets": 0, "hero.postflop.size_read_min_share": 0.15,
                    "hero.postflop.size_read_min_buckets": 2, "hero.postflop.size_read_skip_weak": False,
                    "hero.postflop.size_read_streets": 7, "hero.postflop.size_read_min_cbet": 0.0,
                    "r3.v3_bvb_prior": -1.0, "r3.v3_bvb_holdem_only": False,
                    "hero.postflop.probe_from": 1.0, "hero.postflop.probe_n": 6.0, "hero.postflop.probe_margin": -1.0,
                    "hero.postflop.probe_raise_tier": 9, "hero.postflop.probe_bluff": 0.0,
                    "hero.postflop.balance_sizes": False, "hero.postflop.s11_holdem_only": False,
                    "hero.twin_preflop": 0.0, "hero.twin_multi": 0.0, "hero.multi_call_shift": 0,
                    "hero.mu_call_shift": 0, "hero.mu_value_shift": 0, "hero.call_shift_ex": {}}

# Batch 6's dials at their off values: on top of SHIP_DIALS they play batch 5's ship from this tree (tests written
# against batch 5's F; --base '{"dials": BATCH6_OFF}' for a paired check against the previous batch). With BATCH5_OFF
# as well, batch 4's.
BATCH6_OFF: dict = {"hero.postflop.size_read_twists": "", "hero.postflop.s11_twists": "", "strong_route_twists": "",
                    "hero.known_cards": ""}

# Batch 7's dials at their off values: on top of SHIP_DIALS they play batch 6's ship from this tree (tests written
# against batch 6's F; --base '{"dials": BATCH7_OFF}' for a paired check against the previous batch).
BATCH7_OFF: dict = {"hero.voi": 0.0, "hero.sd_tax": False,
                    "tranche_twin": "", "hero.tranche": "", "hero.tranche_claim_early": 0.5,
                    "short_route": "", "short.pre_roles": "sb,bb", "short.pre_open_min": 0.0, "short.like_probe": 0.0,
                    "short.like_bet": 0.0, "short.like_pfr": 0.0, "short.like_vpip_min": 0.0, "short.like_vpip_max": 0.0,
                    "hero.postflop.stab_from": 1.0, "hero.postflop.stab_full": 1.0, "hero.postflop.stab_prior": 0.5,
                    "hero.postflop.stab_min": 0, "hero.postflop.stab_pool": 0, "hero.postflop.stab_margin": -1.0,
                    "hero.postflop.stab_max_alive": 0, "hero.postflop.stab_pfr_min": 0.0,
                    "hero.postflop.stab_lead_max": 1.0, "hero.postflop.stab_free_max": 1.0,
                    "hero.postflop.stab_holdem_only": False}

def parse_dials(dials: dict | None) -> tuple:
    """One flat dials dict -> (route, make_bot keywords). The keys:
      route          "section=donor,..." (default SHIP_ROUTE)
      r3.<name>      rival 3's core in the base (hyperion/hybrid/dials.py)
      exploit.<f>    the layer's params on top of Hero's shipped set; "exploit": None for no layer
      hero.<key>     Hero's Config wherever Hero plays: the hero member (sections routed to `hero`) and the base's
                     fallback Hero (the tables it plays whole), as `hero.<key>` reaches hybrid3_x's fallback Hero
      base.<key>     any other dial for the base (`base.hero.<key>`: its fallback Hero; flat HybridConfig fields)
      icm.horizon    S18's horizon-aware ICM in both of F's ICM prices: Hero's curve wherever Hero plays
                     (`hero.icm_horizon`) and rival 3's all-in prices in the base (`r3.icm_horizon`)
      cheap          every decision the base's cheap path (Hero's), no other member
      late_us, deadline_ms, panic_after, panic_rate   the shell's clocks
      panic_window, panic_ladder, panic_recover, panic_backoff, degrade   SafeBot's governor and the composite's
                     degradation levels (module doc; off by default)
      light          light shadows (ship() turns them on)
      soft_us, mc_max, ...   any flat HybridConfig field: every hybrid member (the base's soft deadline ...)"""
    d = dict(dials or {})
    route = d.pop("route", SHIP_ROUTE)
    exploit = d.pop("exploit", "hero")
    layer, base, hero, short = {}, {}, {}, {}
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
        elif head == "short":  # the short-handed specialist's dials (S13)
            short[rest] = v
        elif head == "icm" and rest == "horizon":  # S18: both ICM prices, Hero's curve and rival 3's all-ins
            hero["icm_horizon"] = v
            base["hero.icm_horizon"] = v
            base["r3.icm_horizon"] = v
        else:
            raise KeyError(f"unknown composite dial {k!r}")
    if d.pop("cheap", False):  # as on hybrid3_x: every decision Hero's cheap path, no reads, no layer
        base["cheap"] = True
        route = ""
        d.pop("strong_route", None)  # no other member: batch 5's strong-table route (elite1) goes too
        d.pop("short_route", None)  # ... and batch 7's short-handed specialist (S7)
        short = {}
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
                                                                 "hybrid_overrides", "hero_overrides",
                                                                 "short_params"):
            continue
        if k in HybridConfig.__dataclass_fields__ and k not in ("hero", "r3", "exploit", "core", "seed"):
            hyb[k] = d.pop(k)  # a flat hybrid field (soft_us, mc_max ...): every hybrid member, as on hybrid3_x
            continue
        raise KeyError(f"unknown composite dial {k!r}")
    out = {"exploit": exploit, "base_overrides": base, "hero_member": hero, "hybrid_overrides": hyb, **d}
    if short:
        out["short_params"] = short
    return route, out


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
