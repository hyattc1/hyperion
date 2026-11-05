"""S20 H1: the second heads-up tree (tools/solve_short.py hu2) and the specialist's second heads-up path behind
`short.hu2` (off by default), which never takes a decision S7's own path wants (batch 7's heads-up routes behind the
`like_*` gates) and plays only while the composite's strong-table read is open. tables/extra/short_hu2_dev.json is a
development fixture (two depths, 15 and 40 bb, 400 iterations), not a table to play from."""
import importlib.util
import json
import os

import pytest

from hyperion.compose import bot as CB
from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.strategy import short as SH
from hyperion.strategy.tables import TABLES_DIR

from .test_s2_dials import _digest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R2 = Rules(n_players=2, payouts=(10, 7))
DEV = os.path.join(TABLES_DIR, "extra", "short_hu2_dev.json")
has_dev = pytest.mark.skipif(not os.path.exists(DEV), reason="no development heads-up table")
H1 = {"short.hu2": True, "short.hu2_file": "hu2_dev"}


def _solver():
    spec = importlib.util.spec_from_file_location("solve_short_h1", os.path.join(ROOT, "tools", "solve_short.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _keys(root, mod):
    return {n.key: n for n in mod.nodes_of(root)}


def test_the_second_heads_up_tree():
    mod = _solver()
    t15 = _keys(mod.hu2_tree(15)[0], mod)
    assert t15[""].acts == ["f", "r", "j"]  # no limp under 25 bb
    assert t15["r"].acts == ["f", "c", "s", "j"]  # the big blind: fold / call / the small 3-bet / the re-shove
    t20 = _keys(mod.hu2_tree(20)[0], mod)
    assert t20["r"].sizes == {"s": 2.3, "t": 3.3} and "t" in t20["r"].acts  # two 3-bet sizes
    t30 = _keys(mod.hu2_tree(30)[0], mod)
    assert t30[""].acts == ["f", "c", "r", "j"] and t30["c"].sizes == {"r": 3.0}  # the limp from 25 bb on
    assert t30["rs"].acts == ["f", "c", "r", "j"] and t30["rs"].sizes == {"r": 2.2}  # the button 4-bets


def test_the_default_realization_is_the_old_model():
    mod = _solver()
    for spr in (0.5, 3.0, 7.0, 12.0):
        ref_ip, ref_oop = mod.realize_mats(spr)
        for mode in ("hero_ip", "hero_oop"):
            ip, oop = mod.realize_h2(mod.REAL_H2_DEFAULT, spr, mode, "default")
            for i in (0, 40, 168):
                for j in (3, 90, 167):
                    assert abs(ip[i][j] - ref_ip[i][j]) < 1e-12 and abs(oop[j][i] - ref_oop[j][i]) < 1e-12


def test_the_fit_moves_our_share():
    mod = _solver()
    with open(os.path.join(ROOT, "docs", "drills", "climb", "s20-h1-real.json")) as fh:
        real = json.load(fh)
    g = mod._globals()
    E, W = g["E"], g["W"]
    ip, _ = mod.realize_h2(real, 2.0, "hero_ip", "fit")
    ref, _ = mod.realize_mats(2.0)
    i, j = 80, 81  # two middling classes
    assert ip[i][j] / W[i][j] > ref[i][j] / W[i][j] + 0.05  # our button realizes more than the old model at SPR 2


def test_push_fold_sanity_at_ten_big_blinds(capsys):
    """The second tree cut to fold / jam at 10 bb plays tables/pushfold_hu.json's push / fold game."""
    mod = _solver()
    root = mod.cut_push_fold(mod.hu2_tree(10)[0])
    mod.solve(root, 2, 150, mod._norm2())
    s = mod._avg_strategy(root)
    call = mod._avg_strategy(root.kids[1])[1]
    tot = sum(mod.COMBO_COUNT)
    push = sum(mod.COMBO_COUNT[i] * s[1][i] for i in range(mod.N)) / tot
    calls = sum(mod.COMBO_COUNT[i] * call[i] for i in range(mod.N)) / tot
    pf = mod.read_json(os.path.join(TABLES_DIR, "pushfold_hu.json"))
    assert abs(push - pf["p_push"]["10"]) < 0.02 and abs(calls - pf["p_call"]["10"]) < 0.02


def test_a_small_solve_converges():
    mod = _solver()
    root, _ = mod.hu2_tree(12, None, 0)
    hist = mod.solve(root, 2, 120, mod._norm2(), check_every=40)
    gains = [sum(g) for _, g in hist]
    assert gains[-1] < gains[0] and gains[-1] < 0.004  # under 4 mbb a hand after 120 iterations


def _obs(hist, bets, stacks, to_call, seat, hole=(48, 49), hand_no=3):
    return Observation(hole=hole, board=(), street=0, seat=seat, button=0, stacks=list(stacks), bets=list(bets),
                       in_hand=[True, True], pot=0, to_call=to_call, min_raise=max(bets) * 2,
                       max_raise=stacks[seat] + bets[seat], legal=frozenset(ActionKind), hand_no=hand_no,
                       blinds=(10, 20), history=list(hist))


@has_dev
def test_the_second_path_needs_the_strong_read_and_maps_the_line():
    m = SH.ShortMember(SH.ShortParams(hu2=True, hu2_file="hu2_dev", pre_roles="bb"))
    m.new_table(R2, 0, 2)
    # we are the button at 15 bb (300 chips at 20), first in
    o = _obs([], bets=(10, 20), stacks=(290, 280), to_call=10, seat=0)
    assert not m.wants(o, None)  # the strong read is shut: F plays
    m.strong_open = True
    assert m.wants(o, None) and m._hu2_mode
    a = m.act(o)
    assert any(k.startswith("hu2:") for k in m.counts) and a.kind in (ActionKind.FOLD, ActionKind.RAISE)
    # we opened 2 bb, the big blind 3-bet to 2.3x: the node after the small 3-bet
    o2 = _obs([(0, Action.raise_to(40)), (1, Action.raise_to(92))], bets=(40, 92), stacks=(260, 208), to_call=52,
              seat=0, hand_no=4)
    m.light_observe(_obs([], bets=(10, 20), stacks=(290, 280), to_call=10, seat=0, hand_no=4))
    got = m._hu2_node(o2)
    assert got is not None and got[1] == "rs"


def test_f_is_unchanged_and_the_dials_are_off():
    p = SH.ShortParams()
    assert p.hu2 is False and not any(k.startswith("short.hu2") for k in CB.SHIP_DIALS)
    m = SH.ShortMember()
    assert m.hu2 is None and m.needs_strong is False


@has_dev
def test_with_the_strong_read_shut_f_plays_exactly_as_batch_7():
    names = ["hero", "exploiter2"]
    d_f, _ = _digest({}, 1, names, R2)
    d_h, bot = _digest({**H1, "strong_rr": 0.99}, 1, names, R2)
    sh = next(m for m in bot.core.members if isinstance(m, SH.ShortMember))
    assert d_h == d_f and not any(k.startswith("hu2:") for k in sh.counts)


@has_dev
def test_s7s_decisions_stay_s7s(monkeypatch):
    """With the second path on and the strong read always open, every decision S7's own path wants is still S7's and
    gets S7's action (a twin member without hu2 replays each one)."""
    checked = []
    orig_wants = SH.ShortMember.wants

    def wants(self, obs, prof, base=None):
        r = orig_wants(self, obs, prof, base)
        if self.hu2 is not None:
            tw = getattr(self, "_twin", None)
            if tw is None:
                kw = {k: v for k, v in vars(self.p).items() if not k.startswith("hu2")}
                tw = self._twin = SH.ShortMember(SH.ShortParams(**kw), self.seed)
                tw.new_table(R2, self.seat, self.n)
            if tw.wants(obs, prof, base):
                assert r and not self._hu2_mode
                assert tw.act(obs) == SH.ShortMember.act(self, obs)
                checked.append(1)
        return r

    monkeypatch.setattr(SH.ShortMember, "wants", wants)
    for table in (0, 1):  # S7 plays about 50 decisions at each against exploiter 2 heads-up
        d_h, bot = _digest(H1, table, ["hero", "exploiter2"], R2)  # the shipped strong threshold (0.2)
        assert bot.core.counts.get("short:error", 0) == 0
    assert len(checked) > 50
    monkeypatch.setattr(SH.ShortMember, "wants", orig_wants)
    for table in (0, 1):  # ... and there the read stays under 0.2, so the tables play exactly as batch 7
        assert _digest(H1, table, ["hero", "exploiter2"], R2)[0] == _digest({}, table, ["hero", "exploiter2"], R2)[0]


@has_dev
def test_the_second_path_plays_where_s7_does_not():
    _, bot = _digest({**H1, "strong_rr": 0.01}, 2, ["hero", "elite1"], R2)
    sh = next(m for m in bot.core.members if isinstance(m, SH.ShortMember))
    assert any(k.startswith("hu2:") for k in sh.counts) and bot.core.counts.get("short:error", 0) == 0


class _Prof:
    """A read of one opponent as `_like_ok` and the hold ask for it."""

    def __init__(self, pb_opp, pb_bet, opp=1):
        n = 2
        self.pb_opp, self.pb_bet = [0] * n, [0] * n
        self.ab_opp, self.ab_bet = [0] * n, [0] * n
        self.pb_opp[opp], self.pb_bet[opp] = pb_opp, pb_bet

    def pfr_rate(self, j):
        return 0.5

    def vpip_rate(self, j):
        return 0.7

    def archetype(self, j):
        return "unknown"


@has_dev
def test_the_hold_waits_for_s7s_gate():
    """`hu2_like_opp`: S7's probe read cannot admit a seat under 3 chances, so H1 holds until then; a seat the gate has
    refused with its chances is H1's, a seat it admits is not."""
    m = SH.ShortMember(SH.ShortParams(hu2=True, hu2_file="hu2_dev", pre_roles="bb", hu2_like_opp=3, like_probe=0.75,
                                      like_bet=0.6, like_pfr=0.3, like_vpip_min=0.5, like_vpip_max=0.88))
    m.new_table(R2, 0, 2)
    m.strong_open = True
    o = _obs([], bets=(10, 20), stacks=(290, 280), to_call=10, seat=0)
    assert not m.wants(o, _Prof(0, 0))  # no chances yet
    assert not m.wants(o, _Prof(2, 0))  # two chances, refused so far: the gate could not have admitted yet
    assert m.wants(o, _Prof(3, 1)) and m._hu2_mode  # three chances, refused
    assert not m.wants(o, _Prof(4, 4))  # admitted: never H1's (and S7 takes only the big blind)
