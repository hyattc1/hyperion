"""V-j: F's dials for payoff by street, off by default: the composite's tranche_twin and Hero's tranche parts."""
from __future__ import annotations

import pytest

from hyperion.compose import bot as CB
from hyperion.core.types import ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.strategy.hero import HeroCore, config_from_dict
from hyperion.strategy.postflop import Postflop
from tests.strategy_helpers import make_obs

TR = V.get("tranche_holdem").rules
OTHERS = [n for n in V.catalog_names() if n != "tranche_holdem"]


def test_the_dials_ship_in_batch_7_and_are_off_by_default():
    assert CB.SHIP_DIALS["tranche_twin"] == "all" and CB.SHIP_DIALS["hero.tranche"] == "now,sunk"  # c6 (H29)
    assert CB.BATCH7_OFF["tranche_twin"] == "" and CB.BATCH7_OFF["hero.tranche"] == ""
    assert CB.ComposeConfig().tranche_twin == ""
    assert config_from_dict({}).tranche == ""
    with pytest.raises(KeyError):
        CB.compose_config(tranche_twin="every")


def _core(dials: dict, rules: Rules):
    bot = CB.ship(dials, seed=1)
    bot.new_table(rules, 0, 8)
    return bot.core


def test_the_twin_reaches_only_street_settled_or_no_runout_tables():
    core = _core({"tranche_twin": "all"}, TR)
    obs = make_obs(hole="2c 2d", street=0, seat=3, button=0, bets=[0, 10, 20, 0, 0, 0, 0, 0])
    o = core._twin_obs(obs)
    assert o is not obs and o.hole == parse_cards("As Ts")  # 22 beats every non-pair: shown as A-T suited
    assert obs.hole == parse_cards("2c 2d")  # the engine's observation is untouched
    assert core._twin_obs(make_obs(hole="8s 7s", street=0, seat=3)).hole[0] >> 2 < 8  # a weak two-card hand
    assert _core(CB.BATCH7_OFF, TR)._twin is None
    for name in OTHERS:
        assert _core({"tranche_twin": "all"}, V.get(name, seed=3).rules)._twin is None, name
    assert _core({"tranche_twin": "all"}, Rules())._twin is None
    # no runout alone: the all-in decisions only (20 bb deep here: 2000 chips at 10/20 is 100 bb, so deep stays real)
    nr = _core({"tranche_twin": "all"}, Rules(extras={"no_runout": True}))
    assert nr._twin is not None and nr._twin_obs(obs) is None
    short = make_obs(hole="2c 2d", street=0, seat=3, stacks=[300] * 8, bets=[0, 10, 20, 0, 0, 0, 0, 0])
    assert nr._twin_obs(short).hole == parse_cards("As Ts")


def test_heros_tranche_parts_switch_on_only_where_the_rule_is():
    for name in OTHERS:
        h = HeroCore(config_from_dict({"tranche": "now,sunk,allin"}))
        h.new_table(V.get(name, seed=3).rules, 0, 8)
        assert not (h._tr_now or h._tr_sunk or h._tr_allin), name
    h = HeroCore(config_from_dict({"tranche": "now,sunk,allin"}))
    h.new_table(TR, 0, 8)
    assert h._tr_now and h._tr_sunk and h._tr_allin
    h.new_table(Rules(extras={"no_runout": True}), 0, 8)
    assert h._tr_allin and not (h._tr_now or h._tr_sunk)
    with pytest.raises(KeyError):
        HeroCore(config_from_dict({"tranche": "draws"})).new_table(TR, 0, 8)


def test_the_now_read_gives_a_draw_nothing():
    hole, board = parse_cards("Ah 5h"), parse_cards("Kh 9h 2c")
    tier, outs, _ = Postflop.read(hole, board)
    assert tier >= 3 and outs >= 9  # hold'em: a nut flush draw
    tier, outs, _ = Postflop.read(hole, board, now=True)
    assert tier <= 1 and outs == 0  # as it is now: ace high
    assert Postflop.read(parse_cards("Kc Qd"), board, now=True)[0] == Postflop.read(parse_cards("Kc Qd"), board)[0]


def _hero(parts: str, early: float = 0.5) -> HeroCore:
    h = HeroCore(config_from_dict({"tranche": parts, "tranche_claim_early": early, "use_profiler": False}, seed=1))
    h.new_table(TR, 0, 8)
    return h


def test_a_flush_draw_folds_to_a_flop_bet_it_calls_in_holdem():
    # heads-up flop, 200 in the preflop tranche, a half-pot bet: hold'em calls the nut flush draw, the tranche read
    # (ace high now, the call against this street's 200 less half the preflop claim) folds it
    obs = make_obs(hole="Ah 5h", board="Kh 9h 2c", street=1, seat=0, button=1, stacks=[1800, 1700] + [0] * 6,
                   bets=[0, 100] + [0] * 6, in_hand=[True, True] + [False] * 6, pot=200, history=[])
    obs.extras = {"tranches": (200,)}
    plain = HeroCore(config_from_dict({"use_profiler": False}, seed=1))
    plain.new_table(TR, 0, 8)
    assert plain.act(obs).kind in (ActionKind.CALL, ActionKind.RAISE)
    assert _hero("now,sunk").act(obs).kind is ActionKind.FOLD


def test_a_big_preflop_claim_calls_a_river_bet_it_would_fold():
    # pocket deuces took a 1000-chip preflop tranche; the river bet of 300 with nothing made: whole-pot hold'em folds a
    # pair of deuces on an A-K-Q-J-9 board, the claim (0.94 x 1000) pays for the call
    obs = make_obs(hole="2c 2d", board="As Kh Qd Jc 9s", street=3, seat=0, button=1, stacks=[1000, 1000] + [0] * 6,
                   bets=[0, 300] + [0] * 6, in_hand=[True, True] + [False] * 6, pot=1000, history=[])
    obs.extras = {"tranches": (1000, 0, 0)}
    assert _hero("now").act(obs).kind is ActionKind.FOLD
    assert _hero("now,sunk").act(obs).kind is ActionKind.CALL
    # on the turn the claim counts at tranche_claim_early: 0 drops it, so the same spot folds
    turn = make_obs(hole="2c 2d", board="As Kh Qd Jc", street=2, seat=0, button=1, stacks=[1000, 1000] + [0] * 6,
                    bets=[0, 300] + [0] * 6, in_hand=[True, True] + [False] * 6, pot=1000, history=[])
    turn.extras = {"tranches": (1000, 0)}
    assert _hero("now,sunk", early=1.0).act(turn).kind is ActionKind.CALL
    assert _hero("now,sunk", early=0.0).act(turn).kind is ActionKind.FOLD
