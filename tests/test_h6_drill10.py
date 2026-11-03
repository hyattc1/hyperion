"""H6, the drill 10 fixes (docs/drills/prompt-drill-10.md, "H6"): one test or more per item that changed code."""
import hashlib

import pytest

from hyperion.compose import bot as CB
from hyperion.compose import register
from hyperion.drills import variants as V
from hyperion.sim import bestiary as B
from hyperion.sim.runner import run_tournament
from hyperion.strategy import hero as H

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


# ---------------------------------------------------------------------------------------------- item 2
def _play_f(variant, seats: list, seeds: int = 1):
    """(sha1 of every decision and variant answer F made in Hero's seat of `realistic`, every bot's per-seed points)."""
    h = hashlib.sha1()
    cls = register("_h6_f", dials={**CB.SHIP_DIALS, "light": True})

    class T(cls):
        def __init__(self, seed=None):
            super().__init__(seed)
            seats.append(self.impl)

        def act(self, o):
            a = super().act(o)
            h.update(repr((o.hand_no, o.street, a.kind.value, a.amount)).encode())
            return a

        def variant_decide(self, prompt):
            ans = super().variant_decide(prompt)
            h.update(repr(("v", prompt.get("decision"), ans)).encode())
            return ans

    B.REGISTRY["_h6_t"] = T
    rep = run_tournament(B.field_names("realistic@_h6_t"), seeds, seed=7, rotate=False, mode="model", hero_config=HC,
                         variant=variant)
    return h.hexdigest(), {k: v.samples for k, v in rep.bots.items()}


def _hero_whole() -> list:
    """The catalog entries the base's core cannot play (13 at H6: short deck, lowball, the three-card games ...)."""
    from hyperion.hybrid.bot import HybridConfig, table_reason

    cfg = HybridConfig(hero_on_bounty=False)  # as F's base (SHIP_DIALS base.hero_on_bounty)
    return [n for n in V.catalog_names() if table_reason(V.get(n).rules, cfg) is not None]


@pytest.mark.parametrize("name", _hero_whole())
def test_hero_whole_table_plays_as_before_without_the_second_hand_end(sim, monkeypatch, name):
    """On a table the base's core cannot play, the hero member plays the base's sections and the base's fallback Hero
    sleeps (no decision, no shadow, no hand end): every decision, variant answer and point is what the old routing (the
    base's Hero deciding its sections, both Heros' hand ends) gives on the same deals."""
    v = V.get(name)
    calls = {}
    real_he = H.HeroCore.hand_end

    def counting(self, result):
        calls[id(self)] = calls.get(id(self), 0) + 1
        return real_he(self, result)

    monkeypatch.setattr(H.HeroCore, "hand_end", counting)
    new_seats: list = []
    new = _play_f(v, new_seats)
    core = new_seats[-1].core
    assert core._whole and core.base.asleep
    assert calls.get(id(core.base.hero), 0) == 0 and calls[id(core.members[core._hero_idx])] > 20
    assert not any(k.endswith(":base") for k in core.counts), core.counts

    real_init = CB.CompositeCore.__init__

    def old_routing(self, config=None):
        real_init(self, config)
        self._same_hero = False  # as before H6: the base's Hero decides the base's sections and pays its hand end

    monkeypatch.setattr(CB.CompositeCore, "__init__", old_routing)
    old_seats: list = []
    old = _play_f(v, old_seats)
    oc = old_seats[-1].core
    assert not oc._whole and calls[id(oc.base.hero)] > 20 and any(k.endswith(":base") for k in oc.counts)
    assert new == old


def test_plain_holdem_keeps_the_base(sim):
    """Plain hold'em: the base's core plays its sections and its Hero stays awake, as before."""
    seats: list = []
    _play_f(None, seats)
    core = seats[-1].core
    assert not core._whole and not core.base.asleep
    assert any(k.endswith(":base") for k in core.counts)


# ---------------------------------------------------------------------------------------------- item 3
from hyperion.core.types import Action, ActionKind  # noqa: E402
from hyperion.drills.adapter import make_observation  # noqa: E402
from hyperion.strategy.postflop import Postflop, PostflopParams  # noqa: E402

SOLO = "hyperion/drills/solo_example.py:variant"
_R, _S = "23456789TJQKA", "cdhs"


def _c(text: str) -> list:
    return [_R.index(x[0]) * 4 + _S.index(x[1]) for x in text.split()]


@pytest.mark.parametrize("hole,board,tier,outs", [
    ("Ah Kd", "Ac 9h 4d", 5, 0),  # top pair (the drill 10 player's printed spot)
    ("9s 2c", "Ac 9h 4d", 4, 0),  # middle pair
    ("4s 2c", "Ac 9h 4d", 2, 0),  # bottom pair
    ("Qs Jc", "Ac 9h 4d", 0, 0),  # nothing: no overcard to the ace
    ("As 2c", "Ac Ah 4d", 7, 0),  # trips: our card on the board's pair
    ("4s 2c", "Ac Ah 4d", 4, 0),  # two pair under the board's pair
    ("Kd 2c", "Ac Ah 4d", 2, 0),  # the board's pair is everyone's: a king kicker
    ("Ad 2c", "Ac Ah As", 8, 0),  # quads
    ("2h 3c", "Ah 9h 4h", 1, 9),  # a flush draw: one heart of ours, the board one short of the four it must supply
    ("Th 3c", "Jc Qd 9h", 1, 8),  # an open-ender with one card
    ("3c 3d", "Jc Qd 9h", 0, 0),  # a pocket pair is one card
])
def test_short_board_read_tiers_solo_flops(hole, board, tier, outs):
    t, o, _ = Postflop(PostflopParams()).read_short(_c(hole), _c(board), 1)
    assert (t, o) == (tier, outs)


def test_short_board_read_is_the_must_use_read_of_a_short_board_only():
    """_read sends must-use-k to read_short only while the board has fewer than the 5 - k cards it must supply: Solo's
    flop, never its turn or river, never Omaha's flop (three, the three it needs)."""
    pf = Postflop(PostflopParams())
    seen = []
    pf.read_short = lambda *a, **k: seen.append(len(a[1])) or (0, 0, False)
    pf._read(_c("Ah Kd"), _c("Ac 9h 4d"), 1, ())
    pf._read(_c("Ah Kd"), _c("Ac 9h 4d 2s"), 1, ())
    pf._read(_c("Ah Kd 7c 7d"), _c("Ac 9h 4d"), 2, ())
    assert seen == [3]


def _solo_flop_obs(to_call: int):
    """Hand 1 of Solo at 10/20: seat 3 (us) opened to 60, the big blind (seat 2) called; the flop A-9-4, the big blind
    bets 40 into 130 (`to_call` 40) or checks (0). Our A-K: top pair."""
    hist = [(3, Action(ActionKind.RAISE, 60))] + [(s, Action(ActionKind.FOLD)) for s in (4, 5, 6, 7, 0, 1)] + \
        [(2, Action(ActionKind.CALL))]
    bets = [0] * 8
    stacks = [2000, 1990, 1940, 1940, 2000, 2000, 2000, 2000]
    if to_call:
        hist.append((2, Action(ActionKind.RAISE, 40)))
        bets[2], stacks[2] = 40, 1900
    in_hand = [s in (2, 3) for s in range(8)]
    legal = ["fold", "call", "raise"] if to_call else ["check", "raise"]
    return make_observation(hole=_c("Ah Kd"), board=_c("Ac 9h 4d"), street=1, seat=3, button=0, stacks=stacks,
                            bets=bets, in_hand=in_hand, pot=130, legal=legal, hand_no=0, blinds=(10, 20), history=hist)


@pytest.mark.parametrize("on", [True, False])
def test_f_plays_the_solo_flop(on):
    """F (the composite; Hero plays a must-use table whole) with top pair on Solo's flop: before H6 it folded to a bet
    and checked when checked to; with the short-board read it calls or raises the bet and bets when checked to."""
    from hyperion import ship

    v = V.get(SOLO)
    for to_call in (40, 0):
        bot = ship.make_bot(dials={"hero.mu_short_board": on}, seed=1)
        bot.new_table(v.rules, 3, 8)
        a = bot.act(_solo_flop_obs(to_call))
        hero = bot.core.members[bot.core._hero_idx]
        if on:
            assert hero.last_path.startswith(("postflop", "exploit"))
            assert a.kind in ((ActionKind.CALL, ActionKind.RAISE) if to_call else (ActionKind.RAISE,)), a
        else:
            assert hero.last_path == "safe"
            assert a.kind is (ActionKind.FOLD if to_call else ActionKind.CHECK)


def test_omaha_plays_the_same_with_the_short_board_read_off(sim):
    """The one catalog entry with a must-use rule (omaha_four: must use two, so the flop is the three it needs) never
    reaches the short-board read: F plays it decision for decision with `mu_short_board` on or off."""
    assert [n for n in V.catalog_names() if V.get(n).rules.must_use_hole] == ["omaha_four"]
    v = V.get("omaha_four")
    runs = []
    for on in (True, False):
        h = hashlib.sha1()
        cls = register("_h6_mu", dials={**CB.SHIP_DIALS, "light": True, "hero.mu_short_board": on})

        class T(cls):
            def act(self, o):
                a = super().act(o)
                h.update(repr((o.hand_no, o.street, a.kind.value, a.amount)).encode())
                return a

        B.REGISTRY["_h6_mu_t"] = T
        rep = run_tournament(B.field_names("realistic@_h6_mu_t"), 1, seed=7, rotate=False, mode="model",
                             hero_config=HC, variant=v)
        runs.append((h.hexdigest(), {k: r.samples for k, r in rep.bots.items()}))
    assert runs[0] == runs[1]


def test_solo_variant_file_and_its_tables():
    """The Solo variant file registers, validates, and Hero finds its committed tables (tables/variants/solo/)."""
    from hyperion.strategy import tables as T

    v = V.get(SOLO)
    assert v.name == "solo" and v.rules.must_use_hole == 1 and not V.validate(v)
    t = T.tables_for(v.rules)
    assert t.source == "disk" and len(t.equity) == 169
    assert t.equity["AKo"][0] > t.equity["AA"][0] > t.equity["22"][0]  # a pocket pair is one card
