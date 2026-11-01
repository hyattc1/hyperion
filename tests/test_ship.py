"""The ship switch (hyperion/ship.py) and the dials of the shipped base: one name builds the bot every tool uses, the
dials route to the part of the bot that makes the decision, and rival 3's core with its dials at the defaults plays
bit for bit as rival 3's own methods."""
import hashlib

import pytest

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.hybrid import Hybrid, hybrid_config
from hyperion.hybrid.core3 import Rival3Core
from hyperion.hybrid.dials import Rival3Knobs
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table
from hyperion.sim.rivals import rival3 as R3
from hyperion.strategy.hero import Hero

QUIET = {"panic_after": 10 ** 9, "soft_us": 1e6}  # nothing reads the wall clock


class _Rival3AsBuilt(Rival3Core):
    """The shell's rival 3 core with rival 3's own decision methods instead of the dial copies."""
    _pre_body = R3.Bot._pre
    _post_body = R3.Bot._post
    _rates = R3.Bot._rates


class _Recorder:
    def __init__(self, bot):
        self.bot, self.h = bot, hashlib.sha256()

    def new_table(self, rules, seat, n):
        self.bot.new_table(rules, seat, n)

    def act(self, obs):
        a = self.bot.act(obs)
        self.h.update(f"{obs.hand_no}.{a.kind.value}.{a.amount};".encode())
        return a

    def hand_end(self, result):
        self.bot.hand_end(result)

    def variant_decide(self, prompt):
        return self.bot.variant_decide(prompt)


DEAD_ROOM = ["hero", "timeout", "nit", "tag", "timeout", "pushfold", "loose_aggro", "timeout"]


def _digest(dials: dict, table: int, as_built: bool = False, names: list | None = None) -> tuple[str, float]:
    seed = 7 * 1_000_003 + table
    names = names or B.field_names("realistic")
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    bot = ship.make_bot("hybrid3_x", {**QUIET, **dials}, seed=seed * 64)
    if as_built:
        bot.core.core = _Rival3AsBuilt()
    rec = bots[0] = _Recorder(bot)
    res = play_table(bots, Rules(), seed=seed, mode="model")
    return rec.h.hexdigest(), res.points[0]


def test_ship_names_one_bot_and_make_bot_builds_it():
    assert ship.SHIP in ship.BUILDERS and ship.DIALS == {}
    bot = ship.make_bot()
    assert isinstance(bot, Hybrid) and ship.SHIP == "hybrid3_x"
    cfg = bot.core.cfg
    assert cfg.core == "rival3" and cfg.exploit is not None and cfg.r3 == Rival3Knobs()
    assert isinstance(ship.make_bot("hero"), Hero) and ship.make_bot("cheap").config.cheap
    assert ship.make_bot("hybrid3").core.cfg.exploit is None
    with pytest.raises(KeyError):
        ship.make_bot("nobody")


def test_dials_at_defaults_play_rival_3_as_built_bit_for_bit():
    for t in range(6):
        assert _digest({}, t) == _digest({}, t, as_built=True), t


@pytest.mark.parametrize("dial,value", [
    ("r3.open_scale", 1.6), ("r3.open_late_scale", 1.8), ("r3.short_bb", 16.0), ("r3.push_margin", 0.2),
    ("r3.commit_bb", 30.0), ("r3.call_margin", 0.2), ("r3.three_bet_scale", 3.0), ("r3.bluff_scale", 0.0),
    ("r3.call_edge", 0.3), ("r3.raise_shift", 0.1), ("r3.prior_scale", 0.25), ("r3.dead_hands", 6),
])
def test_every_rival3_dial_reaches_the_core(dial, value):
    room = DEAD_ROOM if dial == "r3.dead_hands" else None  # dead reads need seats that never put a chip in
    assert any(_digest({dial: value}, t, names=room)[0] != _digest({}, t, names=room)[0] for t in range(4)), dial


def test_dials_route_to_the_part_that_decides():
    cfg = hybrid_config({"core": "rival3", "exploit": "hero", "r3.open_scale": 1.2, "exploit.steal": False,
                         "hero.preflop.three_bet_frac": 0.05, "mc_max": 48})
    assert cfg.r3.open_scale == 1.2 and cfg.exploit.steal is False and cfg.exploit.bet_checked is True
    assert cfg.hero.preflop.three_bet_frac == 0.05 and cfg.mc_max == 48
    off = hybrid_config({"core": "rival3", "exploit.steal": True})  # no layer named: neutral params plus this spot
    assert off.exploit.steal is True and off.exploit.bet_checked is False
    assert hybrid_config({"core": "rival3", "exploit": "hero", "exploit": None}).exploit is None
    for bad in ({"preflop.open_frac": 0.2}, {"r3.open_wide": 1.0}, {"exploit.nothing": 1}, {"nothing": 1}):
        with pytest.raises(KeyError):
            hybrid_config({"core": "rival3", **bad})


def test_cheap_dial_sends_every_decision_to_heros_cheap_path():
    bot = ship.make_bot(dials={**QUIET, "cheap": True}, seed=3)
    assert bot.core.ex is None and bot.core.hero.cfg.cheap
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=s) for s, nm in enumerate(names)]
    bots[0] = bot
    play_table(bots, Rules(), seed=5, mode="model")
    routes = dict(bot.core.counts)
    assert routes and set(routes) == {"hero:cheap"}, routes


def test_ship_seats_in_the_simulator_with_its_dials():
    try:
        assert ship.register_sim({"r3.open_scale": 1.1}) == "hybrid3_x dials {'r3.open_scale': 1.1}"
        names = B.field_names("realistic@ship")
        assert names[0] == "ship" and names[1:] == B.field_names("realistic")[1:]
        seat = B.make_bot("ship", seed=1)
        assert seat.impl.core.cfg.r3.open_scale == 1.1
    finally:
        B.REGISTRY.pop("ship", None)
