"""Sections of the game (hyperion/compose/sections.py): each hand-built spot lands in its section, every real decision
lands in exactly one, the partition is cheap, and routes parse."""
from time import perf_counter_ns

import pytest

from hyperion.compose import sections as S
from hyperion.core.types import ActionKind, Observation
from hyperion.sim import bestiary as B
from hyperion.sim.runner import run_tournament

F, K, C, R = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


def obs(stacks, bets, in_hand=None, street=0, seat=0, to_call=None, legal=None, bb=20, pot=0):
    n = len(stacks)
    in_hand = in_hand if in_hand is not None else [s + b > 0 for s, b in zip(stacks, bets)]
    cur = max(bets)
    tc = min(cur - bets[seat], stacks[seat]) if to_call is None else to_call
    if legal is None:
        legal = frozenset({F, C, R}) if tc > 0 else frozenset({F, K, R})
    return Observation(hole=(0, 5), board=() if street == 0 else (8, 12, 16), street=street, seat=seat, button=n - 1,
                       stacks=list(stacks), bets=list(bets), in_hand=list(in_hand), pot=pot, to_call=tc,
                       min_raise=cur + bb, max_raise=stacks[seat] + bets[seat], legal=legal, hand_no=3,
                       blinds=(bb // 2, bb))


def name(o):
    return S.section_name(o)


def test_unopened_bands_by_effective_stack():
    eight = [2000] * 8
    assert name(obs(eight, [0, 0, 0, 0, 0, 0, 10, 20])) == "pre_open_40"
    assert name(obs([600] + [2000] * 7, [0, 0, 0, 0, 0, 0, 10, 20])) == "pre_open_20"  # 30 bb
    assert name(obs([300] + [2000] * 7, [0, 0, 0, 0, 0, 0, 10, 20])) == "pre_open_10"  # 15 bb
    assert name(obs([150] + [2000] * 7, [0, 0, 0, 0, 0, 0, 10, 20])) == "pre_open_short"  # 7.5 bb
    # effective = the other side's chips when they are shorter than mine, among seats still in the hand
    assert name(obs([4000, 250, 250, 250, 0, 0, 0, 0], [0, 0, 10, 20, 0, 0, 0, 0])) == "pre_open_10"
    # limps keep the pot unopened
    assert name(obs(eight, [0, 0, 0, 0, 20, 20, 10, 20])) == "pre_open_40"


def test_facing_a_raise_and_an_all_in():
    eight = [2000] * 8
    assert name(obs(eight, [0, 0, 0, 0, 60, 0, 10, 20])) == "pre_raised_deep"
    assert name(obs([300] + [2000] * 7, [0, 0, 0, 0, 60, 0, 10, 20])) == "pre_raised_short"
    # the raiser is all-in
    assert name(obs([2000, 2000, 2000, 2000, 0, 2000, 2000, 2000], [0, 0, 0, 0, 400, 0, 10, 20])) == "pre_allin"
    # calling costs my whole stack
    assert name(obs([300] + [2000] * 7, [0, 0, 0, 0, 500, 0, 10, 20])) == "pre_allin"
    # no raise is legal: call or fold
    assert name(obs(eight, [0, 0, 0, 0, 60, 0, 10, 20], legal=frozenset({F, C}))) == "pre_allin"
    # three-handed all-ins are pre_allin too; heads-up ones are pre_hu
    three = [2000, 0, 2000, 0, 0, 0, 0, 0]
    assert name(obs([2000, 0, 2000, 0, 0, 0, 0, 0], [0, 400, 20, 0, 0, 0, 0, 0],
                    in_hand=[True, True, True] + [False] * 5)) == "pre_allin"
    assert name(obs(three, [0, 0, 20, 0, 0, 0, 0, 0], in_hand=[True, False, True] + [False] * 5)) == "pre_hu"


def test_short_handed_preflop():
    three = [2000, 2000, 2000, 0, 0, 0, 0, 0]
    ih = [True, True, True] + [False] * 5
    assert name(obs(three, [0, 10, 20, 0, 0, 0, 0, 0], in_hand=ih)) == "pre_3way"
    assert name(obs(three, [0, 60, 20, 0, 0, 0, 0, 0], in_hand=ih)) == "pre_3way"
    two = [2000, 2000, 0, 0, 0, 0, 0, 0]
    assert name(obs(two, [10, 20, 0, 0, 0, 0, 0, 0], in_hand=[True, True] + [False] * 6)) == "pre_hu"


def test_postflop():
    st = [2000] * 8
    hu = [True, True] + [False] * 6
    assert name(obs(st, [0] * 8, in_hand=hu, street=1, pot=120)) == "post_hu_chk"
    assert name(obs(st, [0, 60] + [0] * 6, in_hand=hu, street=2, pot=120)) == "post_hu_bet"
    mw = [True, True, True] + [False] * 5
    assert name(obs(st, [0] * 8, in_hand=mw, street=1, pot=180)) == "post_mw"
    assert name(obs(st, [0, 90, 0] + [0] * 5, in_hand=mw, street=3, pot=180)) == "post_mw"


class _Rec(B.Hybrid3XBot):
    LOG: list = []

    def act(self, o):
        _Rec.LOG.append(o)
        return super().act(o)


def test_every_real_decision_lands_in_one_section_and_it_is_cheap():
    B.REGISTRY["_sec_rec"] = _Rec
    _Rec.LOG.clear()
    saved = B.HYBRID_CONFIG
    B.HYBRID_CONFIG = {"panic_after": 10 ** 9, "soft_us": 1e6}
    try:
        run_tournament(B.field_names("realistic@_sec_rec"), 3, seed=7, rotate=True, mode="model",
                       hero_config={"panic_after": 10 ** 9})
    finally:
        B.HYBRID_CONFIG = saved
        del B.REGISTRY["_sec_rec"]
    log = _Rec.LOG
    assert len(log) > 1000
    seen = set()
    for o in log:
        i = S.section(o)
        assert 0 <= i < len(S.SECTIONS)
        seen.add(i)
        f = S.features(o)
        assert f["section"] == S.SECTIONS[i]
        assert (o.street == 0) == S.SECTIONS[i].startswith("pre_")
    assert len(seen) >= 10  # three tables x 8 rotations reach nearly every section
    best = min(_time(log) for _ in range(3))
    assert best < 10_000, best  # ns per call; ~1-2 us on this box


def _time(log):
    t = perf_counter_ns()
    for o in log:
        S.section(o)
    return (perf_counter_ns() - t) / len(log)


def test_parse_route():
    r = S.parse_route("*=base,pre_hu=hero,post=rival1")
    assert r["pre_hu"] == "hero" and r["post_mw"] == "rival1" and r["pre_open_40"] == "base"
    assert set(r) == set(S.SECTIONS)
    assert S.parse_route({"pre": "x"}) == {n: "x" for n in S.SECTIONS if n.startswith("pre_")}
    assert S.parse_route("") == {}
    with pytest.raises(KeyError):
        S.parse_route("preflop=hero")
