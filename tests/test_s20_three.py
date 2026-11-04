"""S20: the second three-handed tree (tools/solve_short.py three2, tables/extra/short_3b.json) and the specialist's
walker for it (short.three2, hyperion/strategy/short.py), routed by `short_route` and gated by `short_strong`; all
off by default (F plays exactly as before: tests/test_ship.py, test_compose.py and the digests here)."""
import importlib.util
import os

import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.strategy import short as SH
from hyperion.strategy.tables import CLASS_INDEX, TABLES_DIR

from .test_s2_dials import _digest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R3 = Rules(n_players=3, payouts=(10, 7, 5))
THREE = ["hero", "exploiter2", "loose_aggro"]
T3B = os.path.join(TABLES_DIR, "extra", "short_3b.json")
ROUTE = "pre_3way=short,pre_allin=short"
ON = {"short_route": ROUTE, "short.three2": True, "short.defer_3bet": 1.0}
has_table = pytest.mark.skipif(not os.path.exists(T3B), reason="no second three-handed table")


def _solver():
    spec = importlib.util.spec_from_file_location("solve_short_s20", os.path.join(ROOT, "tools", "solve_short.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _keys(root, mod):
    return {n.key: n for n in mod._all_nodes(root) if n.term is None}


def test_the_second_tree_has_the_new_lines():
    pytest.importorskip("numpy")  # the tree's flop terminals carry numpy matrices (the solver is offline only)
    mod = _solver()
    nodes = _keys(mod.three_tree2([40, 40, 40], 0.4)[0], mod)
    assert nodes[""].acts == ["f", "r", "j"] and nodes[""].sizes == {"r": 2.25}  # the button: no limp
    assert "c" in nodes["r"].acts  # the small blind flats the open ...
    assert set(nodes["r"].sizes) == {"s", "t"}  # ... or 3-bets small or big
    assert "rc" in nodes and nodes["rc"].player == 2 and "r" in nodes["rc"].acts  # the big blind squeezes
    assert nodes["rs"].acts == ["f", "r", "j"]  # the big blind's cold 4-bet over the small blind's 3-bet (no cold call)
    assert "r" in nodes["rfs"].acts and "c" in nodes["rfs"].acts  # the opener 4-bets or calls a 3-bet
    assert nodes["rsr"].acts == ["f", "j"]  # facing a 3-bet and a 4-bet: fold or jam
    assert nodes["fc"].acts == ["c", "r", "j"]  # the big blind's option over the small blind's limp
    short = _keys(mod.three_tree2([8, 8, 8], 0.4)[0], mod)
    assert all(set(n.acts) <= set("fcrj") for n in short.values())  # 8 bb: no 3-bet size short of the jam


def test_a_small_solve_converges_and_every_class_sums_to_one():
    pytest.importorskip("numpy")
    mod = _solver()
    root, _ = mod.three_tree2([18, 18, 18], 0.4)
    hist = mod.solve3(root, 60, 20)
    gains = [sum(g) for _, g in hist]
    assert gains[-1] < gains[0] and gains[-1] < 0.002  # milli-prizes ... under 2 per hand after 60 iterations
    import numpy as np

    enc = mod.encode_np2(root, np)
    for rec in enc.values():
        na = len(rec["a"])
        assert all(sum(ord(c) - 48 for c in rec["s"][i * na:(i + 1) * na]) == 40 for i in range(169))


def test_push_fold_sanity_at_eight_big_blinds():
    """Both trees cut to push / fold (the button's first action and the small blind's after its fold: fold or jam)
    play the same all-in game: the second tree's jams and calls match the first tree's (S13, itself checked against
    the heads-up push/fold solution)."""
    pytest.importorskip("numpy")
    import numpy as np

    mod = _solver()
    w = np.array([float(x) for x in mod.COMBO_COUNT]) / 1326.0

    def cut(root):
        nodes = _keys(root, mod)
        for key in ("", "f"):
            n = nodes[key]
            keep = [i for i, a in enumerate(n.acts) if a in ("f", "j")]
            n.acts = [n.acts[i] for i in keep]
            n.kids = [n.kids[i] for i in keep]
        return root

    trees = []
    for build in (mod.three_tree2, mod.three_tree):
        root = cut(build([8, 8, 8], 0.4)[0])
        mod.solve3(root, 300, 0)
        trees.append(_keys(root, mod))

    def freq(nodes, key, act):
        n = nodes[key]
        s = mod._avg_np(n, np)
        return float((s[n.acts.index(act)] * w).sum())

    for key, act in (("", "j"), ("f", "j"), ("j", "c"), ("jf", "c"), ("fj", "c")):
        assert abs(freq(trees[0], key, act) - freq(trees[1], key, act)) < 0.02, (key, act)


def test_the_fitted_realization_moves_the_flop_share():
    pytest.importorskip("numpy")
    mod = _solver()
    real = {"spr": [0.0, 40.0], "sym": {"k": [0.0, 0.0], "s": [0.0, 0.0], "c": [0.0, 0.0]},
            "hero_ip": {"k": [0.0, 0.0], "s": [0.0, 0.0], "c": [0.1, 0.1]},
            "hero_oop": {"k": [0.0, 0.0], "s": [0.0, 0.0], "c": [-0.1, -0.1]}, "w3": [0.0, 0.0, 0.0]}
    E = mod._globals()["E"]
    W = mod._np_globals()["W"]
    ip, _ = mod.realize_fit(real, 5.0, "hero_ip", "t")
    assert abs(ip[0][1] / W[0][1] - (E[0][1] + 0.1)) < 1e-9  # the hero in position: E + c
    ip2, oop2 = mod.realize_fit(real, 5.0, "hero_oop", "t")
    assert abs(oop2[1][0] / W[1][0] - ((1 - E[0][1]) - 0.1)) < 1e-9  # the hero out of position: its own E + c
    ip3, _ = mod.realize_fit(real, 5.0, "sym", "t")
    assert abs(ip3[0][1] / W[0][1] - E[0][1]) < 1e-9
    for spr in (0.5, 3.0, 7.0, 12.0):  # the default coefficients are the first tree's fixed model, exactly
        a, b = mod.realize_fit(mod.REAL_DEFAULT, spr, "sym", "d")
        c, d = mod.realize_mats_np(spr)
        assert float(abs(a - c).max()) < 1e-12 and float(abs(b - d).max()) < 1e-12


def _obs(hist, bets, stacks, to_call, seat, button=0, hole=(48, 49), hand_no=3, in_hand=(True, True, True)):
    return Observation(hole=hole, board=(), street=0, seat=seat, button=button, stacks=list(stacks), bets=list(bets),
                       in_hand=list(in_hand), pot=0, to_call=to_call, min_raise=max(bets) * 2,
                       max_raise=stacks[seat] + bets[seat], legal=frozenset(ActionKind), hand_no=hand_no,
                       blinds=(10, 20), history=list(hist))


def _member():
    m = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0))
    m.new_table(R3, 1, 3)
    return m


@has_table
def test_the_walker_maps_a_flat_and_a_squeeze():
    m = _member()
    # seats: 0 button, 1 small blind (us), 2 big blind; 40 bb each (800 chips at 20)
    m.light_observe(_obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=10, seat=1))
    o = _obs([(0, Action.raise_to(45))], bets=(45, 10, 20), stacks=(755, 790, 780), to_call=35, seat=1)
    assert m.wants(o, None)
    assert m._three_node2(o)[1] == "r"
    m.act(o)  # answers from the node: fold, flat or one of the two 3-bets
    # we flatted; the big blind squeezes to 4x: our node is "rcr" (button to act first, then us)
    o2 = _obs([(0, Action.raise_to(45)), (1, Action.call()), (2, Action.raise_to(180)), (0, Action.fold())],
              bets=(45, 45, 180), stacks=(755, 755, 620), to_call=135, seat=1, in_hand=(False, True, True))
    got = m._three_node2(o2)
    assert got is not None and got[1] == "rcrf"


@has_table
def test_a_3bet_maps_onto_the_nearer_size_on_a_log_scale():
    m = _member()
    m.light_observe(_obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=10, seat=0))
    seen = set()
    for h in range(40):
        # we opened 45 on the button, the small blind 3-bets to 3x (between 2.5x and 3.5x)
        o = _obs([(0, Action.raise_to(45)), (1, Action.raise_to(135)), (2, Action.fold())], bets=(45, 135, 20),
                 stacks=(755, 665, 780), to_call=90, seat=0, hand_no=10 + h, in_hand=(True, True, False))
        m.light_observe(o)
        got = m._three_node2(o)
        assert got is not None
        seen.add(got[1])
    assert seen == {"rsf", "rtf"}
    # a 3-bet under the small size maps onto it; one far above the big size (70% of the stack) is the jam or the big
    o = _obs([(0, Action.raise_to(45)), (1, Action.raise_to(90)), (2, Action.fold())], bets=(45, 90, 20),
             stacks=(755, 710, 780), to_call=45, seat=0, hand_no=99, in_hand=(True, True, False))
    m.light_observe(o)
    assert m._three_node2(o)[1] == "rsf"


@has_table
def test_the_route_plays_three_handed_and_replays_exactly():
    d1, bot = _digest(ON, 1, THREE, R3)
    assert d1 == _digest(ON, 1, THREE, R3)[0]
    c = bot.core.counts
    assert c["short"] > 0 and c.get("short:error", 0) == 0
    assert not any(k.startswith("fallback:error") for k in c)
    assert d1 != _digest({}, 1, THREE, R3)[0]
    sh = next(m for m in bot.core.members if isinstance(m, SH.ShortMember))
    assert any(k.startswith("3b:") for k in sh.counts)


@has_table
def test_the_strong_gate_shuts_the_route_while_the_table_reads_weak():
    # a read that can never reach the threshold: the route never opens, and F plays every decision
    shut = {**ON, "short_strong": True, "strong_rr": 0.99}
    d_shut, bot = _digest(shut, 1, THREE, R3)
    assert bot.core.counts.get("short", 0) == 0
    d_f, _ = _digest({"strong_rr": 0.99}, 1, THREE, R3)
    assert d_shut == d_f
    _, open_ = _digest({**ON, "short_strong": True, "strong_rr": 0.01}, 1, THREE, R3)
    assert open_.core.counts["short"] > 0


def test_f_builds_no_specialist_and_the_new_dials_are_off():
    from hyperion import ship
    from hyperion.compose import bot as CB

    bot = ship.make_bot("composite", {})
    assert bot.core.short is None and "short" not in bot.core.names
    assert not any(k.startswith("short") for k in CB.SHIP_DIALS)
    assert SH.ShortParams().three2 is False and CB.ComposeConfig().short_strong is False
    # the gate alone (no route) changes nothing
    assert _digest({"short_strong": True}, 2, THREE, R3)[0] == _digest({}, 2, THREE, R3)[0]


@has_table
def test_keep_the_defence_and_the_roles():
    m = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0, three2_keep_defence=True, three2_roles="btn,sb"))
    m.new_table(R3, 0, 3)
    m.light_observe(_obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=0, seat=0))
    first = _obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=20, seat=0)
    assert m.wants(first, None)  # the button's first decision: the tables'
    # we opened, the small blind 3-bet: once our raise is re-raised, F's defence plays
    o = _obs([(0, Action.raise_to(45)), (1, Action.raise_to(110)), (2, Action.fold())], bets=(45, 110, 20),
             stacks=(755, 690, 780), to_call=65, seat=0, in_hand=(True, True, False))
    assert m._three_node2(o) is not None and not m.wants(o, None)
    # the big blind's seat is not in three2_roles: F plays it
    m2 = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0, three2_roles="btn,sb"))
    m2.new_table(R3, 2, 3)
    m2.light_observe(_obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=0, seat=2))
    o2 = _obs([(0, Action.raise_to(45)), (1, Action.fold())], bets=(45, 10, 20), stacks=(755, 790, 780),
              to_call=25, seat=2, in_hand=(True, False, True))
    assert m2._three_node2(o2) is not None and not m2.wants(o2, None)


@has_table
def test_the_per_seat_reraise_gate():
    class P:
        def __init__(self, rr):
            self.rr_by = rr

        def archetype(self, s):
            return "unknown"

    m = SH.ShortMember(SH.ShortParams(three2=True, defer_3bet=1.0, three2_seat_rr=1))
    m.new_table(R3, 0, 3)
    m.light_observe(_obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=20, seat=0))
    first = _obs([], bets=(0, 10, 20), stacks=(800, 790, 780), to_call=20, seat=0)
    assert m.wants(first, P([0, 2, 1]))  # both opponents have re-raised us
    assert not m.wants(first, P([0, 2, 0]))  # the big blind never has: F plays
    assert not m.wants(first, None)  # no read: F plays


@has_table
def test_the_button_only_route_plays_no_blind(monkeypatch):
    """R6 (`three2_roles` btn): the tables make only button decisions; F plays every small-blind and big-blind one."""
    import json

    spec = json.load(open(os.path.join(ROOT, "docs", "drills", "climb", "s20-r6-candidate.json")))["dials"]
    roles = []
    orig = SH.ShortMember.act

    def act(self, obs):
        got = self._three_node2(obs) if obs.street == 0 else None
        if got is not None:
            roles.append(got[3])
        return orig(self, obs)

    monkeypatch.setattr(SH.ShortMember, "act", act)
    _, bot = _digest({**spec, "short_strong": False}, 1, THREE, R3)
    assert bot.core.counts["short"] > 0 and roles and set(roles) == {0}
