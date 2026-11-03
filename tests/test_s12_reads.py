"""S12's reads (docs/drills/climb/s12-log.md): each behind a dial that defaults to the shipped play; here each one reaches
the decisions it names, its counters count what they say, and with every dial off the profiler counts nothing new."""
import pytest

from hyperion import ship
from hyperion.compose.bot import BATCH5_OFF
from hyperion.core.types import parse_cards as parse
from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules
from hyperion.hybrid.core3 import o3_scan
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table
from hyperion.strategy.postflop import SIZE_PRIOR
from hyperion.strategy.profiler import Profiler

from .test_ship import QUIET, _Recorder

ROOM = ["hero", "rival1", "loose_aggro", "tag", "pushfold", "rival2", "agent_charts", "nit"]
R, C, F, K = ActionKind.RAISE, ActionKind.CALL, ActionKind.FOLD, ActionKind.CHECK


def _o3(hist):
    o, f = [0.0] * 8, [0.0] * 8
    o3_scan(hist, o, f)
    return o, f


def test_o3_scan_counts_the_openers_reply_to_the_first_3bet():
    o, f = _o3([(0, ("fold", 0)), (1, ("raise", 50)), (2, ("fold", 0)), (3, ("raise", 150)), (4, ("fold", 0)),
                (1, ("fold", 0))])
    assert o[1] == 1 and f[1] == 1 and sum(o) == 1
    o, f = _o3([(1, ("raise", 50)), (3, ("raise", 150)), (1, ("call", 0))])
    assert o[1] == 1 and f[1] == 0
    o, f = _o3([(1, ("raise", 50)), (3, ("call", 0)), (1, ("raise", 40))])  # no 3-bet: the flop came
    assert sum(o) == 0
    o, f = _o3([(0, ("call", 0)), (1, ("check", 0)), (0, ("raise", 40))])  # limped: the first raise is a flop bet
    assert sum(o) == 0


def _act(seat, kind, amount=0):
    return (seat, Action(kind, amount))


def test_profiler_counts_sizes_shown_tiers_and_check_raises_only_when_tracking():
    for track in (False, True):
        p = Profiler(3)
        p.track_s12 = track
        p.reset(3, 0)
        hist = [_act(0, C, 20), _act(1, C, 20), _act(2, K),  # preflop: limps, the big blind checks (pot 60)
                _act(1, K), _act(2, R, 30), _act(0, F), _act(1, R, 90), _act(2, C, 90),  # flop: bet 0.5 pot, a check-raise
                _act(1, K), _act(2, R, 200), _act(1, C, 200)]  # turn: 240 pot, a bet of 200 (0.83)
        res = HandResult(0, [0, 0, 0], {1: parse("Ah Kd"), 2: parse("7c 7d")}, parse("7h 2c 9s Qd Jc"), hist)
        obs = Observation(hole=parse("3c 4d"), board=(), street=0, seat=0, button=2, stacks=[2000] * 3, bets=[0, 10, 20],
                          in_hand=[True] * 3, pot=0, to_call=20, min_raise=40, max_raise=2000, legal=frozenset({F, C, R}),
                          hand_no=0, blinds=(10, 20), history=[])
        p.observe(obs)
        p.hand_end(res)
        if not track:
            assert sum(map(sum, p.sz_n[2])) == 0 and sum(p.xr_opp) == 0
            continue
        assert p.xr_opp[1] == 2 and p.xr[1] == 1  # flop: checked then raised; turn: checked then called
        assert p.sz_n[2][0][1] == 1 and p.sz_hist[2][0][1][6] == 1  # seat 2's half-pot flop bet with a set
        assert p.sz_n[1][0][5] == 1  # seat 1's raise over the bet (an unpaired ace-king: tier 1)
        assert p.sz_n[2][1][2] == 1  # the turn bet, 200 into 240


def test_size_prior_is_a_distribution_per_street_and_bucket():
    assert len(SIZE_PRIOR) == 3 and all(len(r) == 6 for r in SIZE_PRIOR)
    for row in SIZE_PRIOR:
        for h in row:
            assert len(h) == 9 and abs(sum(h) - 1.0) < 0.01


def _digest(dials, table, names=ROOM, rules=None):
    seed = 7 * 1_000_003 + table
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    for b in bots:
        if hasattr(b, "use_cost_model"):
            b.use_cost_model(True)
    # from batch 4's F (these tests were written against it; batch 5 ships D3's size read and S11's dials)
    bot = ship.make_bot("composite", {**QUIET, "late_us": 1e9, **BATCH5_OFF, **dials}, seed=seed * 64)
    rec = bots[0] = _Recorder(bot)
    play_table(bots, rules or Rules(), seed=seed, mode="model")
    return rec.h.hexdigest(), bot


@pytest.mark.parametrize("dials", [{"hero.postflop.size_read": 1.0}, {"hero.postflop.xr_shift": 1}, {"r3.l3_on": True}])
def test_each_s12_dial_reaches_the_decisions(dials):
    assert any(_digest(dials, t)[0] != _digest({}, t)[0] for t in range(4)), dials


def test_off_by_default_nothing_new_is_counted():
    _, bot = _digest({}, 0)
    hero = bot.core.members[1]
    assert not hero.prof.track_s12 and sum(hero.prof.xr_opp) == 0
    assert sum(bot.core.members[0].core.o3n) == 0


def test_with_the_reads_on_the_counters_fill_and_a_table_replays_exactly():
    d = {"hero.postflop.size_read": 1.0, "hero.postflop.xr_shift": 1, "r3.l3_on": True}
    h1, bot = _digest(d, 2)
    assert h1 == _digest(d, 2)[0]
    prof = bot.core.members[1].prof
    assert prof.track_s12 and sum(prof.xr_opp) > 0
    assert sum(bot.core.members[0].core.o3n) > 0


def test_rank_prior_reads_a_two_size_bettor_as_polarised_and_a_one_size_bettor_as_the_population():
    from hyperion.strategy.postflop import POP_BET, Postflop
    p = Profiler(8)
    p.reset(8, 0)
    p.szc[1][0][1], p.szc[1][0][2] = 8, 12  # two sizes: half pot 40%, 0.6-0.85 pot 60%
    small = Postflop._rank_prior(p, 1, 0, 1, 5.0)
    big = Postflop._rank_prior(p, 1, 0, 2, 5.0)
    mean = lambda h: sum(t * x for t, x in enumerate(h))  # noqa: E731
    assert abs(sum(small) - 1) < 1e-9 and abs(sum(big) - 1) < 1e-9
    assert mean(small) < 1.5 < 3.5 < mean(big)
    p.szc[2][0][1] = 200  # one size: its bets are its whole betting range
    whole = Postflop._rank_prior(p, 2, 0, 1, 5.0)
    assert max(abs(a - b / sum(POP_BET[0])) for a, b in zip(whole, POP_BET[0])) < 0.05


def test_short_handed_gate_turns_the_size_read_off_heads_up():
    d = {"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0, "hero.postflop.size_read_min_alive": 4}
    r = Rules(n_players=2, payouts=(10, 7))
    names = ["hero", "rival1"]
    assert _digest(d, 1, names, r)[0] == _digest({}, 1, names, r)[0]  # never three or more alive: F's own play


def test_holdem_table_keeps_structure_variants_and_drops_every_twist():
    import json
    import os
    from hyperion.drills import variants as V
    from hyperion.strategy.hero import holdem_table
    structure = {"top_heavy", "antes_from_level_3", "fast_schedule", "straddle"}
    for name in V.catalog_names():
        assert holdem_table(V.get(name, seed=7).rules) == (name in structure), name
    assert holdem_table(Rules()) and holdem_table(Rules(payouts=(50, 25, 12, 6, 3, 2, 1, 1)))
    path = os.path.join(os.path.dirname(__file__), "..", "docs", "drills", "climb", "rules", "double.json")
    with open(path) as fh:
        raw = json.load(fh)
    assert holdem_table(Rules(**{k: tuple(tuple(x) if isinstance(x, list) else x for x in v) if isinstance(v, list)
                                 else v for k, v in raw.items()}))
    assert not holdem_table(Rules(extras={"something_new": 1}))  # an unseen twist: the read stays off


def test_holdem_only_plays_a_twist_table_as_f_and_holdem_as_without_the_gate():
    from hyperion.drills import variants as V
    base = {"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0, "hero.postflop.size_read_min_alive": 4}
    gated = {**base, "hero.postflop.size_read_holdem_only": True}
    assert _digest(gated, 0)[0] == _digest(base, 0)[0]  # hold'em: the gate changes nothing
    bounty = V.get("bounty", seed=7).rules
    assert any(_digest(base, t, rules=bounty)[0] != _digest({}, t, rules=bounty)[0] for t in range(3))
    assert all(_digest(gated, t, rules=bounty)[0] == _digest({}, t, rules=bounty)[0] for t in range(3))


def test_size_evidence_needs_two_informative_buckets():
    p = Profiler(8)
    p.reset(8, 0)
    p.szc[1][0][1], p.szc[1][1][2] = 4, 5  # two sizes, four and five bets
    p.szc[2][0][1], p.szc[2][1][2] = 30, 2  # one size and a stray bet of another
    p.szc[3][0][1], p.szc[3][0][2] = 2, 2  # two sizes, too few bets
    assert p.size_evidence(1, 3, 0.15, 2)
    assert not p.size_evidence(2, 3, 0.15, 2)
    assert not p.size_evidence(3, 3, 0.15, 2)


def test_strong_table_counts_my_first_in_raises_reraised():
    for reraised in (False, True):
        p = Profiler(3)
        p.track_s12 = True
        p.reset(3, 0)
        hist = [_act(0, R, 60), _act(1, F)] + ([_act(2, R, 180), _act(0, F)] if reraised else [_act(2, F)])
        res = HandResult(0, [0, 0, 0], {}, (), hist)
        obs = Observation(hole=parse("3c 4d"), board=(), street=0, seat=0, button=2, stacks=[2000] * 3, bets=[0, 10, 20],
                          in_hand=[True] * 3, pot=0, to_call=20, min_raise=40, max_raise=2000, legal=frozenset({F, C, R}),
                          hand_no=0, blinds=(10, 20), history=[])
        p.observe(obs)
        p.hand_end(res)
        assert (p.rr_n, p.rr_k) == (1, int(reraised))
        assert p.strong_table(0.2, 0.15, 10.0) == (reraised and (1 + 1.5) / 11 >= 0.2)


def test_the_evidence_gates_reach_decisions_and_change_nothing_off():
    c7 = {"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0, "hero.postflop.size_read_min_alive": 4,
          "hero.postflop.size_read_holdem_only": True}
    d1 = {**c7, "hero.postflop.size_read_min_bets": 2, "hero.postflop.size_read_skip_weak": True}
    assert any(_digest(d1, t)[0] != _digest(c7, t)[0] for t in range(6))
    assert any(_digest(d1, t)[0] != _digest({}, t)[0] for t in range(6))
    off = {**c7, "hero.postflop.size_read_min_bets": 0, "hero.postflop.size_read_strong_rr": 0.0}
    assert _digest(off, 1)[0] == _digest(c7, 1)[0]


def test_night_rule_reaches_decisions_and_reads_only_seats_that_cbet():
    c7 = {"hero.postflop.size_read": 1.0, "hero.postflop.size_read_rank": 5.0, "hero.postflop.size_read_min_alive": 4,
          "hero.postflop.size_read_holdem_only": True}
    d1 = {**c7, "hero.postflop.size_read_min_bets": 2, "hero.postflop.size_read_skip_weak": True}
    d3 = {**d1, "hero.postflop.size_read_streets": 3, "hero.postflop.size_read_min_cbet": 0.55}
    assert any(_digest(d3, t)[0] != _digest(d1, t)[0] for t in range(6))
    p = Profiler(8)
    p.reset(8, 0)
    p.cb_opp[1], p.cbets[1] = 3, 1  # c-bets a third of its chances: (1 + 2) / 7 < 0.55
    p.cb_opp[2], p.cbets[2] = 3, 3  # (3 + 2) / 7 >= 0.55
    assert p.cbet_rate(1, 0.5, 4.0) < 0.55 <= p.cbet_rate(2, 0.5, 4.0)
    assert p.cbet_rate(3, 0.5, 4.0) < 0.55  # no evidence: not read
