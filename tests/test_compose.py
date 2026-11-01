"""The composite bot (hyperion/compose/bot.py): with every section on one donor it plays that donor's game decision for
decision, shadows change nothing, members never touch the observation, rival 3's own-action flag follows the action
taken, raw rivals never play a variant table, and a failing member costs only its own decision."""
import copy
import hashlib

import pytest

from hyperion.compose import bot as CB
from hyperion.compose import compose_config, make_bot, register
from hyperion.compose.bot import _resync_r3
from hyperion.compose.sections import SECTIONS
from hyperion.core.types import Action, ActionKind
from hyperion.drills import variants as V
from hyperion.sim import bestiary as B
from hyperion.sim.runner import run_tournament

HC = {"panic_after": 10 ** 9}  # nothing reads the wall clock in these tests
HYB = {"panic_after": 10 ** 9, "soft_us": 1e6}


@pytest.fixture
def sim():
    saved = (B.HYBRID_CONFIG, dict(B.REGISTRY), dict(B._BY_CLASS), B.HERO_CONFIG)
    B.HYBRID_CONFIG = dict(HYB)
    yield
    B.HYBRID_CONFIG, B.HERO_CONFIG = saved[0], saved[3]
    B.REGISTRY.clear()
    B.REGISTRY.update(saved[1])
    B._BY_CLASS.clear()
    B._BY_CLASS.update(saved[2])


def _traced(cls, sink):
    class T(cls):
        def act(self, o):
            a = super().act(o)
            sink.update(repr((o.hand_no, o.street, o.seat, a.kind.value, a.amount)).encode())
            return a
    return T


def _play(name, field, seeds=1, variant=None):
    """(sha1 of every decision `name` made in Hero's seat, every bot's per-seed points)."""
    h = hashlib.sha1()
    B.REGISTRY["_traced"] = _traced(B.REGISTRY[name], h)
    rep = run_tournament(B.field_names(f"{field}@_traced"), seeds, seed=7, rotate=True, mode="model", hero_config=HC,
                         variant=variant)
    return h.hexdigest(), {k: v.samples for k, v in rep.bots.items()}


@pytest.mark.parametrize("route,alone,field,shadow", [
    ("*=base", "hybrid3_x", "realistic", False),
    ("*=base", "hybrid3_x", "realistic", True),
    ("*=hybrid3", "hybrid3", "realistic", False),
    ("*=hero", "hero", "realistic", True),
    ("*=rival3", "rival3", "realistic", False),
    ("*=rival1", "rival1", "strong", True),
])
def test_every_section_on_one_donor_plays_that_donor(sim, route, alone, field, shadow):
    register("_comp", route, shadow_all=shadow)
    B.REGISTRY["_alone"] = type("Alone", (B.REGISTRY[alone],), {})
    a = _play("_alone", field)
    c = _play("_comp", field)
    assert a[0] == c[0]  # every decision in Hero's seat
    assert a[1]["_traced"] == c[1]["_traced"] and len(a[1]) == len(c[1])
    assert all(a[1][k] == c[1][k] for k in a[1])  # and so every other seat's points


def test_only_the_route_members_are_built():
    assert make_bot().core.names == ["base"]
    assert make_bot(route="pre_hu=hero,post_mw=hybrid3").core.names == ["base", "hero"]
    assert make_bot(route="post=rival1,pre_hu=hero").core.names == ["base", "hero", "rival1"]
    c = make_bot(route="pre_hu=rival3", shadow_all=True).core
    assert c.names[:2] == ["base", "rival3"] and set(c.names) == set(CB.MEMBERS)
    with pytest.raises(KeyError):
        compose_config(route="pre_hu=nobody")
    with pytest.raises(KeyError):
        compose_config(route="preflop=hero")


def test_members_never_change_the_observation(sim):
    seen = []

    class Check(CB.CompositeCore):
        def act(self, obs):
            before = copy.deepcopy((obs.stacks, obs.bets, obs.in_hand, obs.history, obs.hole, obs.board, obs.pot,
                                    obs.to_call, obs.legal, obs.extras))
            a = super().act(obs)
            seen.append(before == (obs.stacks, obs.bets, obs.in_hand, obs.history, obs.hole, obs.board, obs.pot,
                                   obs.to_call, obs.legal, obs.extras))
            return a

    saved = CB.CompositeCore
    CB.CompositeCore = Check
    try:
        register("_comp", "pre=hero,post=rival1", shadow_all=True)
        run_tournament(B.field_names("realistic@_comp"), 1, seed=11, rotate=True, mode="model", hero_config=HC)
    finally:
        CB.CompositeCore = saved
    assert len(seen) > 300 and all(seen)


class _R3:
    def __init__(self, hand, flag):
        self.hand, self.my_pf_raise = hand, flag


def test_rival3_preflop_raise_flag_follows_the_action_taken():
    pre = type("O", (), {"street": 0})()
    post = type("O", (), {"street": 1})()
    b = _R3(5, True)  # it proposed a raise on hand 5 ...
    _resync_r3(b, (5, False), pre, Action.fold())  # ... and the composite folded
    assert b.my_pf_raise is False
    b = _R3(5, False)
    _resync_r3(b, (5, False), pre, Action.raise_to(60))  # it proposed a fold, the composite raised
    assert b.my_pf_raise is True
    b = _R3(5, True)
    _resync_r3(b, (5, True), pre, Action.call())  # it had raised earlier this hand: that stays
    assert b.my_pf_raise is True
    b = _R3(6, True)  # this decision opened hand 6 (its _act reset the flag), it proposed a raise, the action was a call
    _resync_r3(b, (5, True), pre, Action.call())
    assert b.my_pf_raise is False
    b = _R3(5, True)
    _resync_r3(b, (5, False), post, Action.fold())  # postflop decisions never touch it
    assert b.my_pf_raise is True


def test_rival3_flag_matches_our_preflop_raises_when_hero_plays_preflop(sim):
    """Base shadowing Hero preflop: after each preflop decision its 'I raised preflop' flag says whether this seat
    raised preflop this hand (allowing the few decisions its core never saw)."""
    checks = []

    def tap(core, obs, sec, mi, own, taken, props, ex):
        if obs.street == 0:
            raised = any(s == obs.seat and a.kind is ActionKind.RAISE for s, a in obs.history) \
                or taken.kind is ActionKind.RAISE
            checks.append(core.members[0].core.my_pf_raise == raised)

    cls = register("_comp", "pre=hero")

    class Tapped(cls):
        def __init__(self, seed=None):
            super().__init__(seed)
            self.impl.core.tap = tap

    B.REGISTRY["_comp_t"] = Tapped
    run_tournament(B.field_names("realistic@_comp_t"), 1, seed=13, rotate=True, mode="model", hero_config=HC)
    assert len(checks) > 300
    assert sum(checks) >= 0.99 * len(checks)


def test_raw_rivals_never_play_a_variant_table(sim):
    for name in ("short_deck", "permuted_ranks"):
        register("_comp", "*=rival1")
        bots = []
        cls = B.REGISTRY["_comp"]

        class Keep(cls):
            def __init__(self, seed=None):
                super().__init__(seed)
                bots.append(self)

        B.REGISTRY["_comp_k"] = Keep
        rep = run_tournament(B.field_names("realistic@_comp_k"), 1, seed=7, rotate=False, mode="model",
                             hero_config=HC, variant=V.get(name, seed=0))
        counts = {}
        for b in bots:
            for k, v in b.impl.core.counts.items():
                counts[k] = counts.get(k, 0) + v
        assert counts.get("fallback:plain", 0) > 20
        assert not any(k.endswith(":rival1") for k in counts), counts
        st = rep.bots["_comp_k"].stats
        assert st.exceptions == 0 and st.illegal == 0


def test_a_failing_member_costs_only_its_own_decision(sim):
    class Boom:
        plain_only = False

        def new_table(self, *a):
            pass

        def act(self, obs):
            raise RuntimeError("boom")

        def hand_end(self, r):
            pass

    CB.register_member("_boom", lambda cfg, seed: Boom(), layer_donor=False)
    try:
        bots = []
        cls = register("_comp", "pre_open_40=_boom,pre_raised_deep=_boom")

        class Keep(cls):
            def __init__(self, seed=None):
                super().__init__(seed)
                bots.append(self)

        B.REGISTRY["_comp_k"] = Keep
        rep = run_tournament(B.field_names("realistic@_comp_k"), 1, seed=7, rotate=False, mode="model", hero_config=HC)
        n = sum(b.impl.core.counts.get("fallback:error", 0) for b in bots)
        errs = sum(b.impl.core.counts.get("shadow:error:_boom", 0) for b in bots)
        assert n > 10 and errs > 10  # its own sections fall back to the base; elsewhere the shadow's raise is ignored
        st = rep.bots["_comp_k"].stats
        assert st.exceptions == 0 and st.illegal == 0
    finally:
        CB.MEMBERS.pop("_boom", None)
        CB.DONORS.pop("_boom", None)


def test_every_section_is_routable():
    c = make_bot(route={s: "hero" for s in SECTIONS}).core
    assert [d for d in c.donors] == ["hero"] * len(SECTIONS)
    assert all(mi == 1 and layer for mi, layer in c.route)


def test_ship_builder_reads_one_flat_dials_dict():
    from hyperion.compose import bot as CBm

    b = CBm.ship({"route": "pre_hu=hero", "exploit.bet_frac": 0.4, "r3.bluff_scale": 1.2,
                  "hero.preflop.three_bet_frac": 0.05})
    c = b.core
    assert c.names == ["base", "hero"] and c.donors[SECTIONS.index("pre_hu")] == "hero"
    assert c.ex.p.bet_frac == 0.4 and c.ex.p.bet_checked  # on top of Hero's shipped layer
    assert c.members[0].cfg.r3.bluff_scale == 1.2
    assert c.members[1].cfg.preflop.three_bet_frac == 0.05
    assert c.members[0].cfg.hero.preflop.three_bet_frac == 0.05  # and the base's fallback Hero, as on hybrid3_x
    assert CBm.ship({"cheap": True}).core.names == ["base"]
    assert CBm.ship({"exploit": None}).core.ex is None
    with pytest.raises(KeyError):
        CBm.ship({"preflop.open_frac": 0.2})


@pytest.mark.parametrize("field,variant", [("realistic", None), ("night", None), ("realistic", "permuted_ranks"),
                                           ("realistic", "short_deck")])
def test_light_shadows_play_the_same(sim, field, variant):
    """Light shadows (Hero preflop, the base postflop keep their state without deciding) change no decision."""
    route = "post=hero,pre_raised_short=hero"
    v = V.get(variant, seed=7) if variant else None
    got = []
    for light in (False, True):
        register("_comp", route, light=light)
        got.append(_play("_comp", field, seeds=1 if v is None else 1, variant=v))
    assert got[0] == got[1]


def test_hero_preflop_raise_flag_follows_the_action_taken():
    from hyperion.compose.bot import _resync_hero

    class H:
        hand_no, _pre_aggr = 4, False

    def o(to_call, bets, hist=()):
        return type("O", (), {"street": 0, "hand_no": 4, "to_call": to_call, "bets": bets, "blinds": (10, 20),
                              "history": list(hist)})()

    h = H()
    _resync_hero(h, (4, False), o(0, [10, 20]), Action.raise_to(60))  # the base opened: Hero is the aggressor
    assert h._pre_aggr is True
    _resync_hero(h, (4, True), o(120, [60, 180], [(1, Action.raise_to(180))]), Action.call())  # called a 3-bet
    assert h._pre_aggr is False
    h._pre_aggr = True
    _resync_hero(h, (3, True), o(0, [10, 20]), Action.check())  # a new hand starts unraised
    assert h._pre_aggr is False


def test_the_composite_ships_as_measured():
    """`composite` with no dials is the final composite F: P's route, the layer's fold read 0.4, Hero's call margin 0.2."""
    from hyperion import ship

    c = ship.make_bot("composite", {}).core
    assert c.names == ["base", "hero"]
    assert [c.donors[SECTIONS.index(s)] for s in ("pre_raised_short", "post_hu_bet", "post_hu_chk", "post_mw")] == \
        ["hero"] * 4
    assert all(c.donors[i] == "base" for i, s in enumerate(SECTIONS) if s not in
               ("pre_raised_short", "post_hu_bet", "post_hu_chk", "post_mw"))
    assert c.ex.p.bet_min_fold == 0.4 and c.ex.p.bet_checked and c.ex.p.steal
    assert c.members[1].cfg.postflop.call_margin == 0.2
    assert c.light[0] is not None  # light shadows as shipped
    assert ship.make_bot("composite", {"route": ""}).core.names == ["base"]  # dials on top of the defaults


def test_the_shipped_composite_takes_the_nights_cheap_dial_and_seats_in_the_simulator(sim):
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.sim.engine import play_table

    bot = ship.make_bot("composite", {"panic_after": 10 ** 9, "soft_us": 1e6, "cheap": True}, seed=3)
    assert bot.core.names == ["base"] and bot.core.ex is None and bot.core.members[0].hero.cfg.cheap
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=s) for s, nm in enumerate(names)]
    bots[0] = bot
    play_table(bots, Rules(), seed=5, mode="model")
    assert set(bot.core.members[0].counts) == {"hero:cheap"}
    try:
        assert ship.register_sim({"r3.open_scale": 1.1}) == "composite dials {'r3.open_scale': 1.1}"
        seat = B.make_bot("ship", seed=1)
        assert seat.impl.core.members[0].cfg.r3.open_scale == 1.1 and seat.impl.core.names == ["base", "hero"]
    finally:
        B.REGISTRY.pop("ship", None)
