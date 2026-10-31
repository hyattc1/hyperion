"""Rival bots behind the bestiary adapter: red-team drills 1 and 2 (`rival1`, `rival2`) and the fields they sit in."""
from time import perf_counter_ns

import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_cards
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Auditor


@pytest.fixture
def rival_debug():
    """Make the rival re-raise what its own act() would swallow, so an exception inside it reaches
    the engine's counters instead of becoming a quiet check/fold. Restored afterwards."""
    from hyperion.sim.rivals import rival1

    old = rival1.Bot.debug
    rival1.Bot.debug = True
    try:
        yield
    finally:
        rival1.Bot.debug = old


def test_rival1_plays_300_hands_in_measure_mode_with_zero_exceptions(rival_debug):
    rules = Rules(max_hands=300, starting_stack=16000)  # deep enough that busts do not end it early
    hands = decisions = 0
    seed = 0
    while hands < 300:
        bots = [Auditor(B.make_bot("rival1", seed=seed * 8 + s), 8 * 16000) for s in range(8)]
        t = Table(bots, rules, seed=seed, mode="measure")
        while not t.done:
            t.play_hand()
            hands += 1
        for s in range(8):
            st = t.stats[s]
            assert st.exceptions == 0, st.last_error
            assert st.illegal == 0
        decisions += sum(len(b.decisions) for b in bots)
        seed += 1
    assert hands >= 300 and decisions > 300


def test_rival1_timeout_rate_in_strict_mode_is_under_one_percent():
    names = ["rival1", "hero", "tag", "pushfold", "loose_aggro", "nit", "station", "random"]
    calls = over = 0
    for seed in range(6):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(names)]
        res = play_table(bots, Rules(), seed=seed, mode="strict")
        st = res.stats[0]
        assert st.exceptions == 0, st.last_error
        assert st.illegal == 0
        calls += st.calls + st.first_calls
        over += st.over_budget
    assert calls >= 300
    assert over / calls < 0.01, (over, calls)


def _obs(hole, legal, to_call=0, bets=None, history=()):
    n = 8
    stacks = [2000] * n
    bets = list(bets) if bets else [0] * n
    return Observation(hole=hole, board=(), street=0, seat=2, button=7, stacks=stacks, bets=bets,
                       in_hand=[True] * n, pot=0, to_call=to_call, min_raise=40, max_raise=2000,
                       legal=frozenset(legal), hand_no=4, blinds=(10, 20), history=list(history))


def test_adapter_presents_the_kit_interface_and_converts_history_incrementally():
    bot = B.make_bot("rival1", seed=1)
    bot.new_table(Rules(), 2, 8)
    assert bot.impl.cap == 200  # hand_cap reached the rival through the rules dict
    hist = [(0, Action.raise_to(60)), (1, Action.call())]
    o = _obs(parse_cards("AsKs"), {ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE}, to_call=60, history=hist)
    k = bot.to_kit(o)
    assert k.legal == {"fold", "call", "raise"} and isinstance(k.legal, set)
    assert k.history == [(0, ("raise", 60)), (1, ("call", 0))]
    assert k.hand_no == 5 and k.blinds == (10, 20) and k.stacks is o.stacks
    first = k.history
    hist.append((3, Action.fold()))
    k2 = bot.to_kit(_obs(parse_cards("AsKs"), {ActionKind.FOLD, ActionKind.CALL}, to_call=60, history=hist))
    assert k2.history is first and k2.history[-1] == (3, ("fold", 0))  # extended, not rebuilt
    o3 = _obs(parse_cards("7c2d"), {ActionKind.FOLD, ActionKind.CHECK}, history=[(5, Action.check())])
    o3.hand_no = 5
    k3 = bot.to_kit(o3)
    assert k3.history == [(5, ("check", 0))] and k3.history is not first  # a new hand starts the list over


def test_adapter_clamps_the_rivals_answer():
    o = _obs(parse_cards("AsKs"), {ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE}, to_call=20)
    assert B.RivalBot.from_kit(("raise", 10 ** 6), o) == Action.raise_to(2000)
    assert B.RivalBot.from_kit(("raise", 1), o) == Action.raise_to(40)
    assert B.RivalBot.from_kit(("call", 0), o) == Action.call()
    assert B.RivalBot.from_kit(("check", 0), o) == Action.call()  # check is not legal facing a bet
    no_raise = _obs(parse_cards("AsKs"), {ActionKind.FOLD, ActionKind.CALL}, to_call=20)
    assert B.RivalBot.from_kit(("raise", 500), no_raise) == Action.call()
    free = _obs(parse_cards("7c2d"), {ActionKind.FOLD, ActionKind.CHECK})
    assert B.RivalBot.from_kit(None, free) == Action.check()
    assert B.RivalBot.from_kit(("jump", 0), free) == Action.check()
    assert B.RivalBot.from_kit(("raise", "x"), free) == Action.check()


def test_rival1_shoves_premiums_short_and_folds_junk_through_the_adapter():
    bot = B.make_bot("rival1", seed=1)
    bot.new_table(Rules(), 2, 8)
    n = 8
    stacks, bets = [2000] * n, [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0], stacks[1] = 1990, 1980
    stacks[2] = 140  # 8 bb UTG
    legal = frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE})
    mk = lambda hole: Observation(hole=hole, board=(), street=0, seat=2, button=7, stacks=stacks, bets=bets,  # noqa: E731
                                  in_hand=[True] * n, pot=0, to_call=20, min_raise=40, max_raise=140,
                                  legal=legal, hand_no=0, blinds=(10, 20))
    a = bot.act(mk(parse_cards("AsAd")))
    assert a.kind is ActionKind.RAISE and a.amount == 140
    assert bot.act(mk(parse_cards("7c2d"))).kind is ActionKind.FOLD


def test_rival_fields_resolve_to_eight_bots_and_naive_stays_registered():
    for name in ("realistic", "top", "top2"):
        members = B.field_names(name)
        assert len(members) == 8, name
        for nm in members:
            assert isinstance(B.make_bot(nm, seed=1), object)
    assert "rival1" in B.FIELDS["realistic"] and "naive" not in B.FIELDS["realistic"]
    assert "rival2" not in B.FIELDS["realistic"]  # realistic is unchanged by rival 2
    assert B.FIELDS["top"].count("rival1") == 2 and B.FIELDS["top"][0] == "hero"
    assert "rival2" in B.FIELDS["top"] and "montecarlo30" not in B.FIELDS["top"]
    assert isinstance(B.make_bot("naive"), B.NaiveEquityBot)
    assert isinstance(B.make_bot("rival1"), B.RivalBot)
    r2 = B.make_bot("rival2")
    assert isinstance(r2, B.Rival2Bot) and type(r2.impl).__module__ == "hyperion.sim.rivals.rival2"


def test_top_field_runs_twenty_tables_end_to_end():
    rep = run_tournament(B.field_names("top"), tables=20, seed=1, mode="strict")
    assert rep.tables == 20 and rep.hands >= 20
    assert set(rep.bots) == set(B.FIELDS["top"])
    assert rep.bots["rival1"].seats == 40 and rep.bots["hero"].seats == 20
    for name, b in rep.bots.items():
        assert len(b.samples) == 20, name
        assert b.stats.exceptions == 0, (name, b.stats.last_error)
        assert b.stats.illegal == 0, name
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 20 - sum(Rules().payouts)) < 1e-6


# ----- rival 2 (red-team drill 2: the computation-first bot) -----------------------------------


@pytest.fixture
def rival2_debug():
    """Rival 2's own switch for re-raising what its act() would swallow (it is `DEBUG`, not `debug`)."""
    from hyperion.sim.rivals import rival2

    old = rival2.Bot.DEBUG
    rival2.Bot.DEBUG = True
    try:
        yield
    finally:
        rival2.Bot.DEBUG = old


def test_rival2_plays_300_hands_in_measure_mode_with_zero_exceptions(rival2_debug):
    rules = Rules(max_hands=300, starting_stack=16000)
    hands = decisions = 0
    seed = 0
    while hands < 300:
        bots = [Auditor(B.make_bot("rival2", seed=seed * 8 + s), 8 * 16000) for s in range(8)]
        t = Table(bots, rules, seed=seed, mode="measure")
        while not t.done:
            t.play_hand()
            hands += 1
        for s in range(8):
            st = t.stats[s]
            assert st.exceptions == 0, st.last_error
            assert st.illegal == 0
        decisions += sum(len(b.decisions) for b in bots)
        seed += 1
    assert hands >= 300 and decisions > 300


def _host_overrun_rate(us: int = 200, n: int = 2000) -> float:
    """Fraction of fixed `us`-microsecond busy loops that take over 1 ms of wall time in this process:
    what the host's scheduler does to any bot that spends that long per decision."""
    over = 0
    for _ in range(n):
        t0 = perf_counter_ns()
        end = t0 + us * 1000
        while perf_counter_ns() < end:
            pass
        over += perf_counter_ns() - t0 > 1_000_000
    return over / n


def test_rival2_timeout_rate_in_strict_mode_is_under_two_percent():
    # Its postflop sampler spends ~150-280 us by design (hard cap 520 us), so it is preempted past 1 ms
    # about 8x as often as a 20 us bot: ~0.01-0.05% on a quiet host, 2-3% when the 8-core box runs a
    # dozen sims. Over 2%, a fixed 200 us busy loop decides whose fault it is: if the loop overruns too,
    # the host is oversubscribed and the rate is not measurable here (skip); if it does not, rival 2 or
    # the adapter got slower (fail).
    names = ["rival2", "hero", "tag", "pushfold", "loose_aggro", "nit", "station", "random"]
    calls = over = 0
    for seed in range(6):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(names)]
        res = play_table(bots, Rules(), seed=seed, mode="strict")
        st = res.stats[0]
        assert st.exceptions == 0, st.last_error
        assert st.illegal == 0
        calls += st.calls + st.first_calls
        over += st.over_budget
    assert calls >= 300
    rate = over / calls
    if rate >= 0.02:
        host = _host_overrun_rate()
        if host >= 0.005:
            pytest.skip(f"host oversubscribed: rival2 {rate:.2%} over 1 ms, a fixed 200 us loop {host:.2%}")
    assert rate < 0.02, (over, calls)


def test_rival2_shoves_premiums_short_and_folds_junk_through_the_adapter():
    bot = B.make_bot("rival2", seed=1)
    bot.new_table(Rules(), 2, 8)
    n = 8
    stacks, bets = [2000] * n, [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0], stacks[1] = 1990, 1980
    stacks[2] = 140  # 7 bb UTG
    legal = frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE})
    mk = lambda hole: Observation(hole=hole, board=(), street=0, seat=2, button=7, stacks=stacks, bets=bets,  # noqa: E731
                                  in_hand=[True] * n, pot=0, to_call=20, min_raise=40, max_raise=140,
                                  legal=legal, hand_no=0, blinds=(10, 20))
    a = bot.act(mk(parse_cards("AsAd")))
    assert a.kind is ActionKind.RAISE and a.amount == 140
    assert bot.act(mk(parse_cards("7c2d"))).kind is ActionKind.FOLD


def test_top2_field_resolves_to_eight_bots_and_runs_twenty_tables():
    members = B.field_names("top2")
    assert members == ["hero", "rival1", "rival2", "rival2", "pushfold", "tag", "hero_tight", "loose_aggro"]
    rep = run_tournament(members, tables=20, seed=1, mode="strict")
    assert rep.tables == 20 and rep.hands >= 20
    assert set(rep.bots) == set(members)
    assert rep.bots["rival2"].seats == 40 and rep.bots["rival1"].seats == 20 and rep.bots["hero"].seats == 20
    for name, b in rep.bots.items():
        assert len(b.samples) == 20, name
        assert b.stats.exceptions == 0, (name, b.stats.last_error)
        assert b.stats.illegal == 0, name
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 20 - sum(Rules().payouts)) < 1e-6


# ----- micro (public repo ryankkhalil19/microholdem, MIT): optional, behind HYPERION_MICROHOLDEM -------------


def test_micro_and_the_public_field_are_disabled_without_the_env_var():
    # a fresh interpreter: the registry is decided at import from the environment
    import os
    import subprocess
    import sys

    env = {k: v for k, v in os.environ.items() if k != "HYPERION_MICROHOLDEM"}
    code = (
        "from hyperion.sim import bestiary as B\n"
        "assert 'micro' not in B.REGISTRY and 'public' not in B.FIELDS\n"
        "for f in (lambda: B.make_bot('micro'), lambda: B.field_names('public')):\n"
        "    try:\n"
        "        f()\n"
        "    except B.BotUnavailable as e:\n"
        "        assert 'HYPERION_MICROHOLDEM is not set' in str(e), str(e)\n"
        "    else:\n"
        "        raise AssertionError('expected BotUnavailable')\n"
        "print('ok')\n"
    )
    r = subprocess.run([sys.executable, "-c", code], env=env, capture_output=True, text=True, timeout=120)
    assert r.returncode == 0 and r.stdout.strip() == "ok", r.stdout + r.stderr


@pytest.mark.skipif(not __import__("os").environ.get("HYPERION_MICROHOLDEM"),
                    reason="HYPERION_MICROHOLDEM is not set (micro is an optional opponent)")
def test_micro_plays_the_public_field_when_configured():
    from hyperion.sim.rivals import microholdem

    ok, why = microholdem.available()
    assert ok, f"HYPERION_MICROHOLDEM is set but the bot cannot load: {why}"
    members = B.field_names("public")
    assert members == ["hero", "micro", "micro", "rival1", "rival2", "tag", "pushfold", "loose_aggro"]
    for seed in range(4):
        bots = [B.make_bot(n, seed=seed * 8 + s) for s, n in enumerate(members)]
        res = play_table(bots, Rules(), seed=seed, mode="strict")
        for s, nm in enumerate(members):
            st = res.stats[s]
            assert st.exceptions == 0, (nm, st.last_error)
            assert st.illegal == 0, nm
            if nm == "micro":
                assert st.calls > 0 and bots[s].replay_mismatches == 0
