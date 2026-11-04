"""S13: the short-handed specialist (hyperion/strategy/short.py) behind the composite's `short_route`, off by default
(tests/test_ship.py and tests/test_compose.py replay F at the defaults; here the route and the tables)."""
import os

import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.strategy import short as SH
from hyperion.strategy.tables import CLASS_INDEX, TABLES_DIR

from hyperion.compose.bot import BATCH7_OFF

from .test_s2_dials import _digest

HU = ["hero", "exploiter2"]
THREE = ["hero", "exploiter2", "loose_aggro"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
ROUTE = "pre_hu=short,pre_3way=short,pre_allin=short,post_hu_bet=short,post_hu_chk=short"
ON = {**BATCH7_OFF, "short_route": ROUTE, "short.three": True}  # on batch 6 (batch 7 ships S7's gated route)


def _freq(node, cls, act):
    a = node["a"]
    return (ord(node["s"][CLASS_INDEX[cls] * len(a) + a.index(act)]) - 48) / 40.0


def test_the_heads_up_table_loads_and_reads_sensibly():
    t = SH._load("hu")
    assert t is not None and t["keys"][0] == 5.0 and t["keys"][-1] == 100.0
    for d in t["keys"]:
        nodes = t["solve"][d]["nodes"]
        root = nodes[""]
        assert root["p"] == 0 and set(root["a"]) <= set("fcrj")
        for n in nodes.values():  # every class sums to 1
            na = len(n["a"])
            assert all(sum(ord(c) - 48 for c in n["s"][i * na:(i + 1) * na]) == 40 for i in range(169))
        assert _freq(root, "AA", "f") == 0.0
        assert _freq(nodes["j"], "AA", "c") == 1.0  # the big blind calls a jam with aces at every depth
    shallow = t["solve"][5.0]["nodes"]
    assert _freq(shallow["j"], "72o", "f") == 1.0  # ... and folds 72o to a 5 bb jam


def test_the_three_handed_table_loads_when_present():
    if not os.path.exists(os.path.join(TABLES_DIR, "extra", "short_3.json")):
        pytest.skip("no three-handed table")
    t = SH._load("3")
    assert t is not None and len(t["solve"]) == len(t["grid"]) ** 3
    any_cfg = next(iter(t["solve"].values()))["nodes"]
    assert any_cfg[""]["p"] == 0 and "f" in any_cfg and "r" in any_cfg[""]["a"] + "r"


def test_ship_routes_only_s7s_heads_up_sections_and_batch7_off_builds_no_specialist():
    from hyperion import ship
    from hyperion.compose.sections import SECTIONS

    bot = ship.make_bot("composite", {})
    on = {s for s, x in zip(SECTIONS, bot.core.short) if x is not None}
    assert on == {"pre_hu", "post_hu_bet", "post_hu_chk"} and "short" in bot.core.names
    sh = bot.core.members[bot.core.names.index("short")]
    assert sh.p.like_vpip_min == 0.5 and sh.p.like_vpip_max == 0.88 and sh.p.pre_roles == "bb"
    off = ship.make_bot("composite", BATCH7_OFF)
    assert off.core.short is None and "short" not in off.core.names


def _obs(hist, bets, stacks, to_call, seat=1, button=0, hole=(48, 49), street=0, board=(), pot=0, hand_no=3):
    return Observation(hole=hole, board=board, street=street, seat=seat, button=button, stacks=list(stacks),
                       bets=list(bets), in_hand=[True, True], pot=pot, to_call=to_call, min_raise=max(bets) * 2,
                       max_raise=stacks[seat] + bets[seat], legal=frozenset(ActionKind), hand_no=hand_no,
                       blinds=(10, 20), history=list(hist))


def test_the_member_maps_a_heads_up_preflop_line_and_answers_from_the_table():
    m = SH.ShortMember()
    m.new_table(R2, 1, 2)
    # seat 0 (button, small blind) opens to 50 with 2000 behind: we are the big blind with aces
    o = _obs([(0, Action.raise_to(50))], bets=(50, 20), stacks=(1950, 1980), to_call=30)
    assert m.wants(o, None)
    a = m.act(o)
    assert a.kind in (ActionKind.CALL, ActionKind.RAISE)  # never folds aces
    # a limp-raise (not a line of the tree): not ours, F plays it
    o2 = _obs([(0, Action.call()), (1, Action.raise_to(60)), (0, Action.raise_to(150))], bets=(150, 60),
              stacks=(1850, 1940), to_call=90)
    assert not m.wants(o2, None)


def test_the_member_defends_by_minimum_defence_postflop():
    m = SH.ShortMember()
    m.new_table(R2, 1, 2)
    pre = [(0, Action.raise_to(40)), (1, Action.call())]
    m.light_observe(_obs([], bets=(10, 20), stacks=(1990, 1980), to_call=10, hand_no=5))
    # flop: we (big blind, out of position) check, it bets half the pot
    board = (0, 21, 46)  # 2c 7d Qh
    hist = pre + [(1, Action.check()), (0, Action.raise_to(40))]
    o = _obs(hist, bets=(40, 0), stacks=(1920, 1960), to_call=40, street=1, board=board, pot=80, hand_no=5,
             hole=(44, 45))  # QcQd: a set
    assert m.wants(o, None)
    assert m.act(o).kind in (ActionKind.CALL, ActionKind.RAISE)


@pytest.mark.parametrize("names,rules", [(HU, R2), (THREE, R3)])
def test_the_short_route_plays_and_replays_exactly(names, rules):
    d1, bot = _digest(ON, 1, names, rules)
    assert d1 == _digest(ON, 1, names, rules)[0]
    assert bot.core.counts["short"] > 0
    assert not any(k.startswith("fallback:error") or k == "short:error" for k in bot.core.counts)
    assert d1 != _digest(BATCH7_OFF, 1, names, rules)[0]


def test_the_short_route_defers_to_f_against_a_dead_seat():
    names = ["hero", "crasher"]
    _, bot = _digest(ON, 0, names, R2)
    c = bot.core.counts
    assert c["pre_hu:base"] > c.get("pre_hu:short", 0)  # dead reads within a few hands: F's steals play


def test_the_short_route_never_plays_a_twist_table():
    from hyperion.drills import variants as V

    rules = V.get("short_deck").rules
    _, bot = _digest(ON, 0, HU, rules)
    assert bot.core.counts.get("short", 0) == 0


def test_the_solver_matches_push_fold_on_the_cut_tree(capsys):
    import importlib.util

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location("solve_short", os.path.join(root, "tools", "solve_short.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class A:
        depth, iters = "10", 120

    mod.cmd_check(A())
    out = capsys.readouterr().out
    ours = float(out.split("push freq ours ")[1].split()[0])
    ref = float(out.split("push freq ours ")[1].split()[2])
    assert abs(ours - ref) < 0.02


class _Prof:
    """A stand-in for F's profiler: every seat opens `rate` of its small blinds."""

    def __init__(self, rate):
        self.rate = rate

    def archetype(self, s):
        return "unknown"

    def open_rate(self, s, late, prior, n0):
        return self.rate


def _sb_vs_3bet(m, member, hole, hand_no):
    """We are the button (seat 0) at 50 bb, opened to 2.25 bb (45 chips); the big blind 3-bets to m times that."""
    to = int(45 * m)
    member.light_observe(_obs([], bets=(10, 20), stacks=(990, 980), to_call=10, seat=0, hand_no=hand_no))
    o = _obs([(0, Action.raise_to(45)), (1, Action.raise_to(to))], bets=(45, to), stacks=(955, 1000 - to),
             to_call=to - 45, seat=0, hole=hole, hand_no=hand_no)
    assert member.wants(o, None)
    return member.act(o)


@pytest.mark.skipif(not os.path.exists(os.path.join(TABLES_DIR, "short_hu_t3.json")), reason="no 3-bet size table")
def test_a_small_3bet_is_answered_from_its_own_table():
    m = SH.ShortMember()
    m.new_table(R2, 0, 2)
    folds = {2.2: 0, 3.5: 0}
    hands = [(r * 4, ((r + 5) % 13) * 4 + 1) for r in range(13)]  # assorted offsuit hands
    for mult in folds:
        for i, h in enumerate(hands):
            if _sb_vs_3bet(mult, m, h, 100 + i).kind is ActionKind.FOLD:
                folds[mult] += 1
    assert m.counts.get("t3:2.2", 0) > 0
    assert folds[2.2] < folds[3.5]


@pytest.mark.skipif(not os.path.exists(os.path.join(TABLES_DIR, "short_hu_lock.json")), reason="no lock table")
def test_a_wide_opener_meets_the_locked_counter():
    m = SH.ShortMember(SH.ShortParams(wide_open=0.72))
    m.new_table(R2, 1, 2)
    m.light_observe(_obs([], bets=(10, 20), stacks=(990, 980), to_call=10, hand_no=7))
    o = _obs([(0, Action.raise_to(45))], bets=(45, 20), stacks=(955, 980), to_call=25, hand_no=7, hole=(0, 21))
    assert m.wants(o, _Prof(0.97))
    m.act(o)
    assert m.counts.get("wide", 0) == 1
    assert m.wants(o, _Prof(0.5)) and not m._wide  # a normal opener: the equilibrium tables


def test_postflop_only_against_a_seat_that_bets_into_us():
    class P(_Prof):
        def __init__(self, bets, chances):
            super().__init__(0.5)
            self.pb_bet, self.ab_bet, self.pb_opp, self.ab_opp = [bets] * 2, [0] * 2, [chances] * 2, [0] * 2

    m = SH.ShortMember(SH.ShortParams(post_aggr=0.5))
    m.new_table(R2, 1, 2)
    pre = [(0, Action.raise_to(40)), (1, Action.call())]
    m.light_observe(_obs([], bets=(10, 20), stacks=(1990, 1980), to_call=10, hand_no=5))
    hist = pre + [(1, Action.check()), (0, Action.raise_to(40))]
    o = _obs(hist, bets=(40, 0), stacks=(1920, 1960), to_call=40, street=1, board=(0, 21, 46), pot=80, hand_no=5,
             hole=(44, 45))
    assert m.wants(o, P(9, 10))  # it bets 9 chances in 10: ours
    assert not m.wants(o, P(1, 10))  # a passive seat: F plays


def test_no_preflop_with_antes_and_the_big_blind_only_against_a_wide_opener():
    m = SH.ShortMember(SH.ShortParams(pre_open_min=0.65))
    m.new_table(R2, 1, 2)
    o = _obs([(0, Action.raise_to(50))], bets=(50, 20), stacks=(1950, 1980), to_call=30)
    assert m.wants(o, _Prof(0.9)) and not m.wants(o, _Prof(0.4))
    o.pot = 10  # antes in the pot
    assert not m.wants(o, _Prof(0.9))


def test_the_exploiter_gate_needs_every_read():
    class P(_Prof):
        def __init__(self, probe, bet, pfr):
            super().__init__(0.9)
            self.pb_bet, self.pb_opp = [probe * 100] * 2, [100] * 2
            self.ab_bet, self.ab_opp = [bet * 100 * 2 - probe * 100] * 2, [100] * 2
            self._pfr = pfr

        def pfr_rate(self, s):
            return self._pfr

    m = SH.ShortMember(SH.ShortParams(like_probe=0.75, like_bet=0.6, like_pfr=0.15))
    m.new_table(R2, 1, 2)
    o = _obs([(0, Action.raise_to(50))], bets=(50, 20), stacks=(1950, 1980), to_call=30)
    assert m.wants(o, P(0.9, 0.75, 0.5))  # exploiter 2's shape
    assert not m.wants(o, P(0.45, 0.7, 0.6))  # exploiter 1 / an ordinary bettor: probes rarely
    assert not m.wants(o, P(0.8, 0.7, 0.07))  # leads a lot but never raises preflop (naive)
    assert not m.wants(o, P(0.9, 0.4, 0.5))  # probes, but bets little overall


def test_the_looseness_bounds_of_the_exploiter_gate():
    class P(_Prof):
        def __init__(self, vpip, pfr):
            super().__init__(0.9)
            self.pb_bet, self.pb_opp, self.ab_bet, self.ab_opp = [90] * 2, [100] * 2, [60] * 2, [100] * 2
            self._v, self._p = vpip, pfr

        def pfr_rate(self, s):
            return self._p

        def vpip_rate(self, s):
            return self._v

    m = SH.ShortMember(SH.ShortParams(like_probe=0.75, like_bet=0.6, like_pfr=0.3, like_vpip_min=0.5,
                                      like_vpip_max=0.88))
    m.new_table(R2, 1, 2)
    o = _obs([(0, Action.raise_to(50))], bets=(50, 20), stacks=(1950, 1980), to_call=30)
    assert m.wants(o, P(0.76, 0.54))  # exploiter 2 heads-up
    assert not m.wants(o, P(0.33, 0.25))  # an elite build at an 8-max table's end
    assert not m.wants(o, P(0.91, 0.65))  # a maniac: F's reads
    assert not m.wants(o, P(0.6, 0.2))  # loose but passive preflop
