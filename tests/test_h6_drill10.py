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
