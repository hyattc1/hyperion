"""Hero on the variant axes: table resolution and the loader fixes from drill 4, 3/4-card preflop, multi-card
postflop reads, lowball / wild / flush-over-full modes, variant decisions, extras (bounty, knockout, exposed
cards, two boards), the push/fold solver's convergence, and the Config keys the windows loop reaches."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind, Rules, parse_cards as P
from hyperion.drills import variants as V
from hyperion.sim.bestiary import make_bot as make_opp
from hyperion.sim.engine import play_table
from hyperion.strategy import tables as T
from hyperion.strategy.hero import Config, Hero, HeroCore, config_from_dict, mirror_map, wild_map
from hyperion.strategy.postflop import Postflop, PostflopParams
from hyperion.strategy.preflop import Preflop, PreflopParams
from hyperion.strategy.pushfold import PushFold, PushFoldParams, solve_hu_pushfold
from hyperion.strategy.spot import Spot
from hyperion.tablegen import hole_label

from .strategy_helpers import preflop_obs, street_obs

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "gen_tables.py"
R, C, F, K = Action.raise_to, Action.call(), Action.fold(), Action.check()
FOLDS = lambda *seats: [(s, F) for s in seats]  # noqa: E731
CALL, RAISE = ActionKind.CALL, ActionKind.RAISE


# ----- loader: the class scheme the files declare --------------------------------------------------


def test_short_deck_regeneration_loads_from_disk_with_81_classes(tmp_path):
    """Drill 4 repo finding 1: a regenerated short-deck set was rejected for not having 169 classes and
    Hero silently played from built hold'em tables; the push/fold solve went through the same loader."""
    rules_path = tmp_path / "rules.json"
    rules_path.write_text(json.dumps(V.short_deck().rules_json()))
    out = tmp_path / "sd"
    subprocess.run([sys.executable, str(GEN), "--rules", str(rules_path), "--out", str(out), "--samples", "60",
                    "--matrix-samples", "20", "--flops-per-bucket", "1", "--workers", "2"],
                   check=True, stdout=subprocess.DEVNULL, timeout=300)
    t = T.load(str(out), need_hu=True, strict=True)
    assert t.source == "disk" and len(t.classes) == 81 and "22" not in t.classes and "AA" in t.classes
    assert t.total_combos == 630 and sum(t.live) == 81
    assert len(t.equity) == 169 and t.equity["22"] == [0.0] * 7 and t.rank["22"] == 0.0  # dead classes filled
    assert 0.0 < t.rank["66"] < 1.0 and t.rank["AA"] > 0.95  # 60 samples: the top pairs can swap places
    i, j, d = T.CLASS_INDEX["AA"], T.CLASS_INDEX["66"], T.CLASS_INDEX["22"]
    assert len(t.hu) == 169 and t.hu[i][j] > 0.6 and t.hu[i][d] == 0.5  # embedded in the 169 order
    sol = json.loads((out / "pushfold_hu.json").read_text())
    assert sol["n_classes"] == 81 and sol["push"]["10"][d] == 0 and sol["call"]["2"][d] == 0
    pf = PushFold(PushFoldParams(), t)
    assert pf.total == 630 and pf.push_pct["AA"] <= 0.02 and 0.9 < pf.push_pct["76o"] <= 1.0  # percentiles over 630 combos


def test_strict_load_raises_and_the_default_warns_loudly(tmp_path):
    with pytest.raises(T.TablesError):
        T.load(str(tmp_path / "empty"), strict=True)
    with pytest.warns(RuntimeWarning, match="built"):
        t = T.load(str(tmp_path / "other"), fallback_samples=8)
    assert t.source == "built"


def test_tables_for_resolves_catalog_sets_and_falls_back_to_a_label_view():
    base = T.load(need_hu=True)
    toss = T.tables_for(V.get("toss_or_holdem").rules, base)
    assert toss.scheme == "best2+tags" and toss.source == "disk" and len(toss.classes) == 338
    assert toss.rank["AA+s"] > toss.rank["AKs+l"] > toss.rank["32s+l"]  # 72o is never the Chen-best two of three
    omaha = T.tables_for(V.get("omaha_four").rules, base)
    assert omaha.hole_cards == 4 and len(omaha.classes) == 550
    assert T.tables_for(V.get("permuted_ranks").rules, base) is base  # a rank remap keeps the default tables
    assert T.tables_for(V.get("bounty").rules, base) is base
    view = T.tables_for(Rules(hole_cards=3, extras={"variant": "nobody_generated_this"}), base)
    assert view.scheme == "best2+tags" and view.source.endswith("+labelview")
    assert view.rank["AKs+p"] > view.rank["AKs+l"] > view.rank["72o+l"]
    assert len(view.equity["QJs+s"]) == 7 and view.equity["QJs+s"][0] >= view.equity["QJs+l"][0]
    assert "AKs+l" in view.rank and "ZZ+l" not in view.rank


# ----- Hero plays every information-axis entry ------------------------------------------------------


class Vpip:
    """Counts hands Hero acted in preflop and hands it voluntarily put chips in."""

    def __init__(self, inner):
        self.inner, self.hands, self.vpip, self._hand, self._in = inner, 0, 0, -1, False

    def new_table(self, rules, seat, n):
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        if obs.hand_no != self._hand:
            self._hand, self._in = obs.hand_no, False
            self.hands += 1
        a = self.inner.act(obs)
        if obs.street == 0 and not self._in and a.kind in (CALL, RAISE):
            self._in = True
            self.vpip += 1
        return a

    def hand_end(self, result):
        self.inner.hand_end(result)

    def variant_decide(self, prompt):
        return self.inner.variant_decide(prompt)


@pytest.mark.parametrize("name", ["toss_or_holdem", "three_card_blind_discard", "three_card_keep", "omaha_four",
                                  "bonus_card", "lowball", "wild_deuces", "two_boards", "exposed_card", "bounty",
                                  "knockout_bounty", "swap_one_turn", "short_deck"])
def test_hero_plays_the_variant_without_errors(name):
    v = V.get(name, seed=3)
    hands = vpip = 0
    for t in range(4):
        h = Hero(Config(seed=t))
        w = Vpip(h)
        bots = [w] + [make_opp(nm, seed=t * 8 + i) for i, nm in
                      enumerate(("tag", "naive", "station", "random", "maniac", "nit", "pushfold"))]
        res = play_table(bots, v.rules, seed=700 + t, mode="strict", variant=v.new_hooks())
        assert res.stats[0].exceptions == 0 and res.stats[0].illegal == 0, res.stats[0].last_error
        assert h.safe.errors == 0, f"{name}: {h.safe.errors} inner exceptions"
        hands += w.hands
        vpip += w.vpip
    assert hands > 50 and vpip / hands > 0.10, f"{name}: VPIP {vpip}/{hands}"


def test_hero_switches_modules_per_table_and_back():
    core = HeroCore(Config(seed=1))
    base_pre = core.preflop
    core.new_table(V.get("toss_or_holdem").rules, 2, 8)
    assert core.active.scheme == "best2+tags" and core.preflop is not base_pre and core.preflop.curve is core.curve
    assert core.act(preflop_obs("Ah Ad 7c", 2)).kind is RAISE
    assert core.act(preflop_obs("7h 2d 3c", 2)) == F
    core.new_table(Rules(), 2, 8)
    assert core.preflop is base_pre and core.active is core.tables
    core.new_table(V.get("lowball").rules, 2, 8)
    assert core.act(preflop_obs("Ah Ad", 2)) == F  # aces are the worst lowball hand
    assert core.act(preflop_obs("7h 2d", 2)).kind is RAISE  # 72o is the nuts


# ----- variant decisions ------------------------------------------------------------------------------


def test_variant_decide_discard_swap_and_buy():
    core = HeroCore(Config(seed=1))
    core.new_table(V.get("toss_or_holdem").rules, 0, 8)
    assert core.variant_decide({"decision": "discard", "hole": P("Ah Ad 7c"), "board": ()}) == 2
    assert core.variant_decide({"decision": "discard", "hole": P("7c Ah Ad"), "board": ()}) == 0
    assert core.variant_decide({"decision": "discard", "hole": P("Kc 9d 2h"), "board": P("9s 9c 4d")}) == 2
    assert core.variant_decide({"decision": "discard", "hole": P("Ah 2h 9c"), "board": P("Kh Qh 3d")}) == 2
    assert core.variant_decide({"decision": "discard", "hole": P("As Qd 8c"), "board": P("8h 8d 2s")}) == 1
    core.new_table(V.get("swap_one_turn").rules, 0, 8)
    assert core.variant_decide({"decision": "swap", "hole": P("Ah Kd"), "board": P("As 7c 2d 9h")}) == -1
    assert core.variant_decide({"decision": "swap", "hole": P("7c 2d"), "board": P("Ks Qd 9h Jc")}) == 1
    assert core.variant_decide({"decision": "swap", "hole": P("Ah 3h"), "board": P("Kh 7h 2c 9d")}) == -1  # flush draw
    core.new_table(V.get("bonus_card").rules, 0, 8)
    assert core.variant_decide({"decision": "buy_card", "price": 20, "seat": 0, "stacks": [2000] * 8}) is True
    assert core.variant_decide({"decision": "buy_card", "price": 20, "seat": 0, "stacks": [100] * 8}) is False
    assert core.variant_decide({"decision": "auction", "hole": P("Ah Kd")}) is None
    h = Hero(Config(seed=1))
    h.new_table(V.get("toss_or_holdem").rules, 0, 8)
    assert h.variant_decide({"decision": "discard", "hole": P("Ah Ad 7c"), "board": ()}) == 2
    assert h.variant_decide({"decision": "discard", "hole": (5, "x", 9), "board": None}) is None and h.safe.errors == 1


# ----- postflop reads ---------------------------------------------------------------------------------


def test_multi_card_reads_keep_all_and_must_use_two():
    pp = Postflop(PostflopParams(), seed=1)
    assert pp.read_multi(P("Ah Kh 2c 3d"), P("Qh Jh 9h"), must_use=2)[0] == 7  # a real Omaha flush
    assert pp.read_multi(P("Ah 2c 3d 4s"), P("Kh Qh Jh 9h 2d"), must_use=2)[0] <= 2  # one heart: no flush
    assert pp.read_multi(P("Ah Ad 7c"), P("As 9d 2c"))[0] == 6  # set, no penalty above tier 5
    assert pp.read_multi(P("Kc Qd 7c"), P("Kd 9s 2h"))[0] == 3  # top pair good kicker, one tier off for the third card
    tier, outs, _ = pp.read_multi(P("Ah 2h 9c"), P("Kh 7h 3d"))
    assert tier >= 3 and outs >= 9  # flush draw with three cards
    tier, outs, _ = pp.read_multi(P("Ah Kh Qh Jh"), P("Th 9h 2c"), must_use=2)
    assert tier >= 3 and outs >= 12  # no made hand yet (two hearts on board), but a flush draw and a wrap
    assert pp.read_multi(P("Ah Kh 2c 3d"), P("Qh 7h 2s"), must_use=2)[1] >= 9  # two in hand + two on board draws
    assert pp.read_multi(P("Ah 2c 3d 4s"), P("Qh 7h 2s"), must_use=2)[1] < 9  # one heart in hand draws to nothing


def test_lowball_read_ranks_lows_and_counts_outs():
    pp = Postflop(PostflopParams(), seed=1)
    pp.set_mode(low=True)
    assert pp.read_low(P("7d 5c"), P("4h 3s 2d"))[0] == 8
    assert pp.read_low(P("8d 5c"), P("4h 3s 2d 9c Tc"))[0] == 7
    assert pp.read_low(P("Ad Ac"), P("4h 3s 2d 9c Tc"))[0] == 5  # the low is T-9-4-3-2: aces are high in 2-7
    assert pp.read_low(P("Kd Kc"), P("Kh 3s 2d"))[0] == 0  # trips: nothing
    tier, outs, _ = pp.read_low(P("Kd 9c"), P("8h 3s 2d"))
    assert tier == 2 and outs > 0
    assert pp.read_low(P("6d 5c"), P("4h 3s 2d"))[0] == 0  # a straight is a disaster
    assert pp._read(P("7d 5c"), P("4h 3s 2d"), 0, ())[0] == 8


def test_wild_read_substitutes_the_best_card():
    pp = Postflop(PostflopParams(), seed=1)
    pp.set_mode(wild_rank=0)
    assert pp.read_wild(P("2d 2c"), P("Kh Ks 7d"))[0] == 8  # two wilds: quad kings
    assert pp.read_wild(P("Ad Qc"), P("Kh 7s 4d")) == Postflop.read(P("Ad Qc"), P("Kh 7s 4d"))
    with_board_wild = pp.read_wild(P("Kd 9c"), P("2h 7s 4d"))[0]
    assert 2 <= with_board_wild <= 3  # top pair kings through the shared wild, one tier off


def test_flush_over_full_house_demotes_a_boat_on_a_flush_board_and_shifts_are_keys():
    hole, board = P("8s 8h"), P("Kh 7h 6h 8c 6d")
    assert Postflop.read(hole, board)[0] == 7
    assert Postflop.read(hole, board, flush_over_full=True)[0] == 6
    assert Postflop.read(P("Ah 9h"), P("Kh 7h 6h 8c 8d"), flush_shift=1)[0] == 8
    assert Postflop.read(P("8c 9d"), P("Ts Jh Qc 2d 3h"), straight_shift=-1)[0] == 5
    pp = Postflop(PostflopParams(draw_outs_mult=1.5), seed=1)
    assert pp._equity(3, 8, 2, 1) == pytest.approx(0.48)


def test_exposed_cards_come_off_the_outs_and_shrink_steals():
    hole, board = P("Ah 2h"), P("Kh 7h 9c")
    assert Postflop.read(hole, board)[1] == 9
    assert Postflop.read(hole, board, dead=P("Qh Jh 9d"))[1] == 7
    assert Postflop.read(P("8c 9d"), P("Ts Jh 2c"), dead=P("7s Qd"))[1] == 6
    pf = Preflop(PreflopParams(), T.load())
    obs = preflop_obs("Jh 7d", 7, actions=FOLDS(2, 3, 4, 5, 6))
    spot = Spot(obs, obs.hole, exposed={0: P("Ah")[0], 1: P("Kd")[0]})
    assert pf._exposed_steal_mult(spot) == pytest.approx(0.85 ** 2)
    assert pf._exposed_steal_mult(Spot(obs, obs.hole, exposed={0: P("4h")[0]})) == 1.0


def test_two_boards_value_needs_both_boards():
    pp = Postflop(PostflopParams(), seed=1)
    strong = street_obs("8s 8d", "8c 9d 2c", 7, pot=200, in_hand=[False, True, False, False, False, False, False, True],
                        history=[(7, R(50)), (1, C), (1, K)])
    spot = Spot(strong, strong.hole)
    assert pp.act(spot, strong.hole, None, True, board=strong.board).kind is RAISE
    dead_board = P("Kh Qh Jh")  # an underpair there, and no heart in hand to draw with
    a = pp.act(spot, strong.hole, None, False, board=strong.board, board2=dead_board)
    assert a == K  # a set on one board and nothing on the other: a split, check it (no c-bet: not the aggressor)
    both = pp.act(spot, strong.hole, None, False, board=strong.board, board2=P("8c 5d 7s"))
    assert both.kind is RAISE and both.amount < pp.act(spot, strong.hole, None, False, board=strong.board).amount


# ----- payoff terms -------------------------------------------------------------------------------------


def test_bounty_bonus_enters_pot_odds_and_the_gates():
    obs = preflop_obs("Ah Kd", 1, actions=[(5, R(160))] + FOLDS(6, 7, 0))
    assert Spot(obs, obs.hole, bounty_bonus=100.0).pot_odds < Spot(obs, obs.hole).pot_odds
    core = HeroCore(Config(seed=1))
    core.new_table(V.get("bounty").rules, 1, 8)
    assert core._bounty is not None
    ex = {"bounties": {s: 12 for s in range(8)}}  # everyone's bounty rank is the ace
    hit = core._bounty_bonus(obs, ex)
    win = obs.pot + sum(obs.bets) - obs.bets[1]
    assert hit == pytest.approx(0.5 * win + 10)
    ex2 = {"bounties": {s: 3 for s in range(8)}}  # a five: must come on the board
    miss = core._bounty_bonus(obs, ex2)
    assert 0.0 < miss < hit
    assert core._bounty_bonus(obs, {"bounties": {}}) == 0.0


def test_knockout_points_make_hero_call_a_covered_shove_wider():
    tables = T.load(need_hu=True)
    pf = PushFold(PushFoldParams(), tables)

    class Curve:  # points: ICM so punishing that chips won are worth nothing, so only the knockout point can pay
        points = True

        def __init__(self, now):
            self.now = now

        def value(self, x):
            return 1.0 if x >= self.now else 0.0

    st = [2000] * 8
    st[5] = 160
    shove = FOLDS(2, 3, 4) + [(5, R(160))] + FOLDS(6, 7, 0)
    obs = preflop_obs("Ah Jd", 1, stacks=st, actions=shove)
    pf.curve = Curve(obs.stacks[1])
    plain = Spot(obs, obs.hole)
    ko = Spot(obs, obs.hole, ko_points=1.0)
    assert ko.shover_covered and ko.cover_frac == 1.0
    assert pf.act(plain, None) == F and pf.act(ko, None) == C


# ----- solver -------------------------------------------------------------------------------------------


def test_fictitious_play_converges_and_push_frequency_is_monotone():
    t = T.load(need_hu=True)
    sol = solve_hu_pushfold(t.hu, depths=range(18, 26), iters=400, tol=1e-4)
    p = [sol["p_push"][str(d)] for d in range(19, 26)]  # 18 absorbs the cold start; the rest warm-start
    assert all(a >= b - 0.003 for a, b in zip(p, p[1:])), p  # no 21-25 bb zig-zag
    assert all(v[1] < 2e-3 for d, v in sol["converged"].items() if int(d) >= 19), sol["converged"]
    assert sol["push"]["20"][T.CLASS_INDEX["K2o"]] == 0 and sol["push"]["20"][T.CLASS_INDEX["22"]] == 1


def test_pushfold_label_path_pushes_premiums_and_folds_junk_with_three_cards():
    base = T.load(need_hu=True)
    rules = V.get("toss_or_holdem").rules
    pf = PushFold(PushFoldParams(), base).with_tables(T.tables_for(rules, base))
    assert pf.call_disc[10] > 0.02 and pf.push_disc[10] > 0.0
    st = [2000] * 8
    st[7] = 120
    folded = FOLDS(2, 3, 4, 5, 6)
    obs = preflop_obs("Ah Ad 9c", 7, stacks=st, actions=folded)
    a = pf.act(Spot(obs, obs.hole, hole_label(obs.hole, rules)), None)
    assert a.kind is RAISE and a.amount == 120
    obs = preflop_obs("8h 3d 2c", 7, stacks=st, actions=folded)
    assert pf.act(Spot(obs, obs.hole, hole_label(obs.hole, rules)), None) == F


# ----- class maps and Config keys ---------------------------------------------------------------------------


def test_class_maps_for_lowball_and_wild_cards():
    rank = T.load().rank
    m = mirror_map(rank)
    assert rank[m["AA"]] < 0.05 and rank[m["72o"]] > 0.95 and rank[m["32o"]] > 0.99
    w = wild_map(0)
    assert w["A2o"] == "AA" and w["A2s"] == "AA" and w["22"] == "AA" and w["72s"] == "77" and w["AKs"] == "AKs"


def test_config_exposes_profiler_strength_and_open_knobs():
    cfg = config_from_dict({"profiler_dead_after": 3, "profiler_nit_after": 9, "postflop.flush_tier_shift": -1,
                            "postflop.straight_tier_shift": 1, "postflop.draw_outs_mult": 1.2,
                            "preflop.open_frac_mult": 1.2, "preflop.open_step": 1, "icm_buckets": 50,
                            "label_bonus_pair": 0.05})
    core = HeroCore(cfg)
    assert core.prof.dead_after == 3 and core.prof.nit_after == 9
    assert core.postflop.p.flush_tier_shift == -1 and core.preflop.p.open_frac_mult == 1.2
    core.new_table(Rules(), 0, 8)
    assert core.curve.n >= 2
    # open_step: one position tighter turns a button open into a fold at the margin
    wide = Preflop(PreflopParams(), T.load())
    tight = Preflop(PreflopParams(open_step=2), T.load())
    obs = preflop_obs("Jh 7d", 7, actions=FOLDS(2, 3, 4, 5, 6))
    assert wide.act(Spot(obs, obs.hole), None).kind is RAISE and tight.act(Spot(obs, obs.hole), None) == F
    half = Preflop(PreflopParams(open_frac_mult=0.5), T.load())
    assert half.act(Spot(obs, obs.hole), None) == F
