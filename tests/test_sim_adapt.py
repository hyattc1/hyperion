"""The adaptive test opponent (R6, decisions "The climb: addendum 9"): `adapt1` (tuning copy) and `adapt1_off` (the same
bot with its counters off), played through the red-team kit adapter, its RNG reseeded per table from the seat seed;
fields `adapt`, `adapt_hu`, `adapt_3`, never in a pool."""
import json
import random
from pathlib import Path

import pytest

from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.field import adapt1 as A
from hyperion.sim.field import night as N
from hyperion.sim.runner import run_tournament

ROOT = Path(__file__).resolve().parents[1]


def _rules(name):
    return Rules(**json.loads((ROOT / "docs/drills/climb/rules" / f"{name}.json").read_text()))


def test_registered_seated_and_in_no_pool():
    assert B.ADAPTERS == ("adapt1", "adapt1_off") and set(B.ADAPTERS) <= set(B.REGISTRY)
    for name, pool in N.POOLS.items():
        drawn = {b for _, _, ms in pool.groups for b, _ in ms}
        assert not drawn & set(B.ADAPTERS), name
    assert B.field_names("adapt") == ["hero", "adapt1"] + [f"night.{k}" for k in range(1, 7)]
    assert B.field_names("adapt_hu@hybrid3_x") == ["hybrid3_x", "adapt1"]
    assert B.field_names("adapt_3") == ["hero", "adapt1", "night.1"]
    assert B.FIELD_PLAYERS["adapt_hu"] == 2 and B.FIELD_PLAYERS["adapt_3"] == 3
    assert B.make_bot("adapt1", seed=1).impl.COUNTERS is True
    assert B.make_bot("adapt1_off", seed=1).impl.COUNTERS is False


def test_the_exploit_stage_has_the_three_cells():
    import importlib.util

    spec = importlib.util.spec_from_file_location("climb_accept", ROOT / "tools" / "climb_accept.py")
    CA = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(CA)
    assert [c for c in CA.EXPLOIT if c[0].startswith("adapt")] == [
        ("adapt", "brief", None), ("adapt_hu", "lin", "hu"), ("adapt_3", "lin", "three")]
    assert "adapt1" in CA.EXPLOIT_BOTS


def test_reseeds_per_table_from_the_seat_seed():
    draws = []
    for seed in (7, 7, 8):
        b = B.REGISTRY["adapt1"](seed=seed)
        b.new_table(Rules(), 3, 8)
        draws.append(b.impl.rng.random())
    assert draws[0] == draws[1] != draws[2]


@pytest.mark.parametrize("field,rules,total", [("adapt", None, 36.0), ("adapt_hu", "hu", 17.0),
                                               ("adapt_3", "three", 22.0)])
def test_adapt_fields_play_legally_and_replay_exactly_in_model_mode(field, rules, total, monkeypatch):
    # Hero's panic mode reads the wall clock; climb_accept turns it off (tools/swap.py HERO_CONFIG), so does this
    monkeypatch.setattr(B, "HERO_CONFIG", B.HERO_CONFIG)
    r = _rules(rules) if rules else None
    kw = dict(seed=1, rotate=True, mode="model", table_offset=10000, rules=r, hero_config={"panic_after": 10 ** 9})
    a = run_tournament(B.field_names(field), 2, **kw)
    b = run_tournament(B.field_names(field), 2, **kw)
    for nm, rep in a.bots.items():
        assert rep.stats.exceptions == 0 and rep.stats.illegal == 0, nm
        assert rep.samples == b.bots[nm].samples, nm
    assert abs(sum(sum(x.samples) for x in a.bots.values()) / len(a.bots["hero"].samples) - total) < 1e-6


def test_the_twin_plays_the_same_until_the_counters_may_switch_on():
    """Same deals, same seeds: adapt1 and adapt1_off take the same actions through hand 30."""
    from hyperion.sim.engine import Table

    logs = {}
    for name in ("adapt1", "adapt1_off"):
        bots = [B.make_bot("hero", seed=5), B.make_bot(name, seed=6)]
        t = Table(bots, _rules("hu"), seed=11)
        while not t.done and t.hand_no < 30:
            t.play_hand()
        logs[name] = (t.hand_no, list(t.stacks))
    assert logs["adapt1"] == logs["adapt1_off"]


def test_replay_follows_streets_blinds_and_all_ins():
    # three-handed, button seat 0: seat 1 posts 10, seat 2 posts 20; seat 0 opens, seat 1 folds, seat 2 calls;
    # flop: seat 2 checks, seat 0 bets 30 into 50, seat 2 folds
    hist = [(0, ("raise", 50)), (1, ("fold", 0)), (2, ("call", 0)), (2, ("check", 0)), (0, ("raise", 30)),
            (2, ("fold", 0))]
    evs = A.replay([2000, 2000, 2000], 0, (10, 20), 0, hist)
    assert [e["street"] for e in evs] == [0, 0, 0, 1, 1, 1]
    assert evs[1]["facing"] == 40 and evs[1]["nr"] == 1
    assert evs[4]["first_bet"] == pytest.approx(30 / 110) and evs[4]["pot"] == 110
    assert evs[5]["facing"] == 30 and evs[5]["checked"] and evs[5]["nr"] == 1
    # heads-up, the button is the small blind; a jam and a call end the betting
    evs = A.replay([400, 2000], 0, (10, 20), 0, [(0, ("raise", 400)), (1, ("call", 0))])
    assert evs[1]["allin_raiser"] and evs[1]["facing"] == 380


def test_learns_fold_rates_and_switches_counters_on_only_after_the_warmup():
    bot = A.Bot()
    bot.new_table({}, 0, 2)
    bot.COUNTERS = True
    bot.st[1].update(fb1n=6, fb1f=5, xfn=3, xff=3)
    bot.played, bot.on = 10, False
    assert bot.pooled_fold(1) is None  # counters off: no estimate
    bot.on = True
    assert bot.pooled_fold(1) == pytest.approx((5 + 0.45 * 4) / 10)
    assert bot.fold_to_bet(1, 1, checked=True) > bot.fold_to_bet(1, 2, checked=False) > 0.45


def test_evaluator_orders_hands():
    def cards(s):
        from hyperion.core.types import parse_cards

        return list(parse_cards(s))

    order = ["2c7d9hJsKd", "2c2d9hJsKd", "2c2d9h9sKd", "2c2d2h9sKd", "3c4d5h6s7d", "2h7h9hJhKh", "2c2d2h9s9d",
             "2c2d2h2s9d", "3h4h5h6h7h"]
    vals = [A.evaluate(cards(s)) for s in order]
    assert vals == sorted(vals) and len(set(vals)) == len(vals)
    assert A.evaluate(cards("Ac2d3h4s5d")) < A.evaluate(cards("2c3d4h5s6d"))  # the wheel is the lowest straight
    made, draw = A.strength(tuple(cards("AhAd")), tuple(cards("2c7dTs")))
    assert made > 0.8 and draw == 0
    made, draw = A.strength(tuple(cards("9h8h")), tuple(cards("2h7hTs")))
    assert made < 0.3 and draw > 0.25  # a flush draw and an open-ended straight draw


def test_preflop_ranking_puts_aces_first_and_spans_all_combos():
    assert A.pre_pct((48, 49)) < A.pre_pct((44, 45)) < A.pre_pct((48, 44)) < 0.03
    assert A.pre_pct((20, 1)) > 0.9  # seven-deuce offsuit is near the bottom
    assert max(A.PCT.values()) < 1.0 and len(A.PCT) == 169


def test_acts_legally_on_random_observations():
    from hyperion.sim.field import Obs

    rng = random.Random(3)
    bot = A.Bot()
    bot.new_table({"payouts": [10, 7, 5]}, 1, 3)
    for i in range(300):
        deck = rng.sample(range(52), 7)
        street = rng.choice((0, 1, 2, 3))
        board = tuple(deck[2:2 + (0, 3, 4, 5)[street]])
        stacks = [rng.randint(0, 3000) for _ in range(3)]
        bets = [rng.choice((0, 10, 20, 60)) for _ in range(3)]
        to_call = max(0, max(bets) - bets[1])
        legal = {"fold", "call", "raise"} if to_call else {"check", "raise"}
        obs = Obs(hole=tuple(deck[:2]), board=board, street=street, seat=1, button=0, stacks=stacks, bets=bets,
                  in_hand=[True, True, rng.random() < 0.5], pot=rng.randint(0, 400), to_call=to_call,
                  min_raise=max(bets) + 20, max_raise=max(max(bets) + 20, bets[1] + stacks[1]), legal=legal,
                  hand_no=i + 1, blinds=(10, 20), history=[])
        kind, amt = bot.act(obs)
        assert kind in legal
        if kind == "raise":
            assert obs.min_raise <= amt <= obs.max_raise
