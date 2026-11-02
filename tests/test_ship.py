"""The ship switch (hyperion/ship.py) and the dials of the shipped base: one name builds the bot every tool uses, the
dials route to the part of the bot that makes the decision, and rival 3's core with its dials at the defaults plays
bit for bit as rival 3's own methods."""
import hashlib
from pathlib import Path

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
    from hyperion.compose import Composite

    assert ship.SHIP in ship.BUILDERS and ship.DIALS == {}
    bot = ship.make_bot()  # the composite as measured (decisions entry "Composite bot")
    assert isinstance(bot, Composite) and ship.SHIP == "composite"
    assert bot.core.names == ["base", "hero"]
    cfg = bot.core.members[0].cfg  # its base: rival 3's core at its defaults, the layer in front of the composite
    assert cfg.core == "rival3" and cfg.exploit is None and cfg.r3 == Rival3Knobs() and bot.core.ex is not None
    bot = ship.make_bot("hybrid3_x")
    assert isinstance(bot, Hybrid)
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
    bot = ship.make_bot("hybrid3_x", dials={**QUIET, "cheap": True}, seed=3)  # the composite: tests/test_compose.py
    assert bot.core.ex is None and bot.core.hero.cfg.cheap
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=s) for s, nm in enumerate(names)]
    bots[0] = bot
    play_table(bots, Rules(), seed=5, mode="model")
    routes = dict(bot.core.counts)
    assert routes and set(routes) == {"hero:cheap"}, routes


def test_ship_seats_in_the_simulator_with_its_dials():
    try:
        assert ship.register_sim({"r3.open_scale": 1.1}, "hybrid3_x") == "hybrid3_x dials {'r3.open_scale': 1.1}"
        names = B.field_names("realistic@ship")
        assert names[0] == "ship" and names[1:] == B.field_names("realistic")[1:]
        seat = B.make_bot("ship", seed=1)
        assert seat.impl.core.cfg.r3.open_scale == 1.1
    finally:
        B.REGISTRY.pop("ship", None)


def test_adapter_hand_end_passes_the_kits_history_and_deltas():
    """A kit whose hand-end signal carries the actions gives them to the bot (rival 3 replays them at hand end)."""
    from hyperion.core.types import Action
    from hyperion.drills.adapter import Adapter

    got = []

    class Bot:
        def new_table(self, *a):
            pass

        def hand_end(self, result):
            got.append(result)

    ad = Adapter(Bot())
    ad.start(1, 3)
    ad.hand_end(4, 30)
    hist = [(0, Action.raise_to(60)), (1, Action.call())]
    ad.hand_end(5, -60, history=hist, deltas=[60, -60, 0])
    assert got[0].deltas == [0, 30, 0] and got[0].history == []  # one per seat of the table start()ed
    assert got[1].deltas == [60, -60, 0] and got[1].history == hist and got[1].hand_no == 5


def test_a_history_rebuilt_from_the_bets_reaches_the_core_as_none():
    """A kit with no action log: make_observation rebuilds the street's raises for Hero and flags it; rival 3's core
    reads no history then (a replay of raises alone books every raiser as a seat that raises every hand)."""
    from hyperion.drills.adapter import make_observation
    from hyperion.hybrid.kit import KitView

    kw = dict(hole=[48, 44], board=[], street=0, seat=3, button=0, stacks=[1990, 1980, 1940] + [2000] * 5,
              bets=[0, 10, 20, 60, 0, 0, 0, 0], in_hand=[True] * 8, pot=0, to_call=0, min_raise=100, max_raise=2000,
              legal=["fold", "call", "raise"], hand_no=4, blinds=(10, 20))
    rebuilt = make_observation(**kw)
    assert rebuilt.extras == {"history_from_bets": True} and len(rebuilt.history) == 1
    assert KitView()(rebuilt, rebuilt.hole, rebuilt.board).history == []
    from hyperion.core.types import Action
    logged = make_observation(**kw, history=[(3, Action.raise_to(60))])
    assert logged.extras == {} and KitView()(logged, logged.hole, logged.board).history == [(3, ("raise", 60))]


def test_no_log_seat_feeds_a_bot_what_a_kit_without_a_log_gives():
    """tools/gate.py's baseline on kits with no action log: the raises rebuilt from the bets, a bare hand end."""
    from hyperion.core.types import Action, HandResult
    from hyperion.drills.adapter import NoLogSeat
    from tests.strategy_helpers import preflop_obs

    seen = []

    class Bot:
        def new_table(self, *a):
            pass

        def act(self, obs):
            seen.append(obs)
            return Action.fold()

        def hand_end(self, result):
            seen.append(result)


    seat = NoLogSeat(Bot())
    seat.new_table(Rules(), 2, 4)
    log = [(3, Action.raise_to(60)), (4, Action.call()), (5, Action.fold())]
    obs = preflop_obs("AsKd", seat=6, actions=log)
    seat.act(obs)
    assert seen[0].extras.get("history_from_bets") and [a.amount for _, a in seen[0].history] == [60]
    assert obs.history[-3:] == log and not obs.extras, "the engine's own observation is untouched"
    seat.hand_end(HandResult(hand_no=0, deltas=[5, -5, 30, -30], showdown={1: (0, 1)}, board=(), history=[(0, Action.call())]))
    assert seen[1].deltas == [0, 0, 30, 0] and seen[1].history == [] and seen[1].showdown == {}


def test_every_registered_ship_bot_builds_with_no_dials():
    for name in ship.BUILDERS:
        bot = ship.make_bot(name, {})
        assert all(hasattr(bot, m) for m in ("new_table", "act", "hand_end", "variant_decide")), name


def test_recipes_resolve_for_whichever_bot_ships(tmp_path, capsys):
    """The window dials are named recipes: the same name gives each bot the dials with that meaning."""
    for name in ship.HERO_RECIPES:
        for bot in ("hybrid3_x", "hero", "composite"):
            ship.make_bot(bot, {**ship.recipe(name, bot)})
    core, hero = ship.recipe("survival", "hybrid3_x"), ship.recipe("survival", "hero")
    assert core["r3.call_margin"] == 0.03 and core["hero.preflop.patience_deep"] == hero["preflop.patience_deep"]
    assert not any(k.startswith("r3.") for k in hero)
    assert ship.recipe("timeouts", "hybrid3_x") == ship.recipe("timeouts", "hero") == {"cheap": True}
    assert ship.recipe("survival+passive", "hero") == {**ship.HERO_RECIPES["survival"], **ship.HERO_RECIPES["passive"]}
    assert ship.parse_dials('{"r3.open_scale": 1.1}') == {"r3.open_scale": 1.1} and ship.parse_dials(None) is None
    assert ship.parse_dials("dead_seats", "hero") == ship.HERO_RECIPES["dead_seats"]
    with pytest.raises(KeyError):
        ship.recipe("bolder")
    copy = tmp_path / "ship.py"
    copy.write_text((Path(ship.__file__)).read_text())
    ship.main(["--set", "passive", "--bot", "hero"], path=copy)
    assert ship.read_record(copy) == ("hero", ship.HERO_RECIPES["passive"])
    ship.main(["--set", ""], path=copy)
    assert ship.read_record(copy) == ("hero", {})
    assert "SHIP = 'hero'" in capsys.readouterr().out


def test_slow_box_recipe_turns_the_governor_on_for_each_bot():
    """R1: `slow_box` resolves per bot; the composite gets its ladder levels (and has them by default since batch 2)."""
    comp = ship.make_bot("composite", ship.recipe("slow_box", "composite"))
    assert comp.safe.gov is not None and comp.safe.gov.ladder and comp.core.levels == 3 and comp.safe.deadline == 0.0008
    hyb = ship.make_bot("hybrid3_x", ship.recipe("slow_box", "hybrid3_x"))
    assert hyb.safe.gov is not None and hyb.core.levels == 1
    hero = ship.make_bot("hero", ship.recipe("slow_box", "hero"))
    assert hero.safe.gov is not None and not hero.safe.gov.ladder
    both = ship.recipe("slow_box+survival", "composite")
    assert both["r3.call_margin"] == 0.03 and both["panic_window"] == 60
    # since the climb's batch 2 the composite ships with the governor on (SHIP_DIALS); hybrid3_x and Hero do not
    assert ship.make_bot("composite", {}).safe.gov is not None and ship.make_bot("composite", {}).core.levels == 3
    assert ship.make_bot("hybrid3_x", {}).safe.gov is None and ship.make_bot("hero", {}).safe.gov is None
