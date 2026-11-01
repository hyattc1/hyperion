"""Red-team rival 3 (`rival3`, drill 3's exploitation-first bot) behind the bestiary adapter, and the two fields it
sits in: `top3` (each rival once) and `holdout` (`realistic` with rival 3 in rival 1's seat). Rival 3 is the
holdout: Hero is never tuned against it, so these tests check that it plays, not how well Hero does."""
from time import perf_counter_ns

import pytest

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules, parse_cards
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Auditor


@pytest.fixture
def rival3_debug():
    """Rival 3 has no debug switch: its act() swallows every exception into a legal check/fold, and act() and
    hand_end() swallow failures of the history replay. Unwrap act() so an exception reaches the engine's
    counters, and record every replay exception even where the rival swallows it. Restored afterwards."""
    from hyperion.sim.rivals import rival3

    errors: list[str] = []
    old_act, old_replay = rival3.Bot.act, rival3.Bot._replay

    def act(self, obs):
        return self._legalize(self._act(obs), obs)

    def replay(self, hist, o, final=False):
        try:
            return old_replay(self, hist, o, final)
        except Exception as e:  # noqa: BLE001 - recorded, then re-raised into the rival's own handler
            errors.append(repr(e))
            raise

    rival3.Bot.act, rival3.Bot._replay = act, replay
    try:
        yield errors
    finally:
        rival3.Bot.act, rival3.Bot._replay = old_act, old_replay


def test_rival3_plays_300_hands_in_measure_mode_with_zero_exceptions(rival3_debug):
    rules = Rules(max_hands=300, starting_stack=16000)  # deep enough that busts do not end it early
    hands = decisions = 0
    seed = 0
    while hands < 300:
        bots = [Auditor(B.make_bot("rival3", seed=seed * 8 + s), 8 * 16000) for s in range(8)]
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
    assert rival3_debug == [], rival3_debug[:3]  # no history replay failed, swallowed or not


def _host_overrun_rate(us: int = 30, n: int = 4000) -> float:
    """Fraction of fixed `us`-microsecond busy loops that take over 1 ms of wall time in this process."""
    over = 0
    for _ in range(n):
        t0 = perf_counter_ns()
        end = t0 + us * 1000
        while perf_counter_ns() < end:
            pass
        over += perf_counter_ns() - t0 > 1_000_000
    return over / n


def test_rival3_timeout_rate_in_strict_mode_is_under_one_percent():
    # Median ~25 us per decision (history replay, no sampler), so its overruns are the host's: on the loaded
    # 8-core box they track a fixed 30 us loop's (redteam-3.md section 4). Over 1%, that loop decides whose fault
    # it is: skip if it overruns too, fail if it does not.
    names = ["rival3", "hero", "tag", "pushfold", "loose_aggro", "nit", "station", "random"]
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
    if rate >= 0.01:
        host = _host_overrun_rate()
        if host >= 0.003:
            pytest.skip(f"host oversubscribed: rival3 {rate:.2%} over 1 ms, a fixed 30 us loop {host:.2%}")
    assert rate < 0.01, (over, calls)


def _preflop(hole, seat=2, history=()):
    """Hand 4 (kit hand 5), button 7, blinds posted by seats 0 and 1; seat 2 is first to act."""
    n = 8
    stacks, bets = [2000] * n, [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0], stacks[1] = 1990, 1980
    return Observation(hole=hole, board=(), street=0, seat=seat, button=7, stacks=stacks, bets=bets,
                       in_hand=[True] * n, pot=0, to_call=20, min_raise=40, max_raise=2000,
                       legal=frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE}), hand_no=4,
                       blinds=(10, 20), history=list(history))


def test_adapter_round_trip_and_hand_end_passes_the_history_in_kit_shape():
    bot = B.make_bot("rival3", seed=1)
    assert isinstance(bot, B.Rival3Bot) and type(bot.impl).__module__ == "hyperion.sim.rivals.rival3"
    bot.new_table(Rules(), 2, 8)
    assert bot.impl.n == 8  # n_players reached the rival; it ignores the rules dict

    # our Observation -> the kit's -> the rival's answer -> a legal Action
    o = _preflop(parse_cards("7c2d"))
    k = bot.to_kit(o)
    assert k.legal == {"fold", "call", "raise"} and k.hand_no == 5 and k.history == []
    a = bot.act(o)
    assert a == Action.fold()  # 72o first in at 100 bb
    assert bot.impl.hand == 5 and bot.impl.start is not None  # it opened its hand model on the kit's hand_no

    # the rest of the hand happens after its last decision; only hand_end can show it
    rest = [(3, Action.raise_to(60)), (4, Action.fold()), (5, Action.fold()), (6, Action.call()),
            (7, Action.fold()), (0, Action.fold()), (1, Action.fold()), (3, Action.raise_to(80)), (6, Action.fold())]
    assert bot.impl.st[3].hands == 0 and bot.impl.st[6].hands == 0
    seen = {}
    real_hand_end = bot.impl.hand_end
    bot.impl.hand_end = lambda r: (seen.setdefault("result", r), real_hand_end(r))
    bot.hand_end(HandResult(4, [0] * 8, {}, (), [(2, a)] + rest))
    r = seen["result"]
    assert r["hand_no"] == 5 and r["history"][:3] == [(2, ("fold", 0)), (3, ("raise", 60)), (4, ("fold", 0))]
    s3, s6, s4 = bot.impl.st[3], bot.impl.st[6], bot.impl.st[4]
    assert (s3.hands, s3.vpip, s3.pfr, s3.uo_r) == (1, 1, 1, 1)  # opened: counted from hand_end's history
    assert (s6.hands, s6.vpip, s6.fr_c) == (1, 1, 1)  # flatted the open
    assert (s6.fb, s6.fb_f) == (1, 1)  # then folded to the flop bet
    assert (s4.hands, s4.fr_f) == (1, 1)  # folded to the raise
    assert bot.impl.hand is None  # the hand is closed

    # the shared rival 1/2 adapter passes no history; rival 3 would then never see those actions
    bare = B.make_bot("rival3", seed=1)
    bare.new_table(Rules(), 2, 8)
    bare.act(_preflop(parse_cards("7c2d")))
    B.RivalBot.hand_end(bare, HandResult(4, [0] * 8, {}, (), [(2, a)] + rest))
    assert bare.impl.st[3].hands == 0


def test_rival3_shoves_premiums_short_and_folds_junk_through_the_adapter():
    bot = B.make_bot("rival3", seed=1)
    bot.new_table(Rules(), 2, 8)
    o = _preflop(parse_cards("AsAd"))
    o.stacks[2], o.max_raise = 140, 140  # 7 bb UTG
    a = bot.act(o)
    assert a.kind is ActionKind.RAISE and a.amount == 140
    o.hole = parse_cards("7c2d")
    assert bot.act(o).kind is ActionKind.FOLD


def test_rival3_play_is_reproducible_run_to_run():
    # no wall-clock time box and one RNG seeded at construction: the same seed plays the same table
    names = ["rival3", "tag", "pushfold", "loose_aggro", "nit", "station", "random", "rival1"]

    def once():
        bots = [B.make_bot(n, seed=s) for s, n in enumerate(names)]
        r = play_table(bots, Rules(), seed=11, mode="measure")
        return r.points, r.places, r.hands, r.stacks

    assert once() == once()


def test_top3_and_holdout_fields_have_the_agreed_seats():
    assert B.field_names("top3") == ["hero", "rival1", "rival2", "rival3", "pushfold", "tag", "hero_tight",
                                     "loose_aggro"]
    holdout = B.field_names("holdout")
    assert holdout == ["hero", "rival3", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag",
                       "timeout_then_recover"]
    swapped = ["rival3" if m == "rival1" else m for m in B.FIELDS["realistic"]]
    assert sorted(holdout) == sorted(swapped)  # realistic with rival 3 in rival 1's seat
    for name in ("realistic", "strong", "top", "top2", "chaos"):
        assert "rival3" not in B.FIELDS[name], name  # every earlier field is unchanged


@pytest.mark.parametrize("field", ["top3", "holdout"])
def test_field_with_rival3_runs_twelve_strict_tables_without_exceptions(field):
    members = B.field_names(field)
    rep = run_tournament(members, tables=12, seed=1, mode="strict")
    assert rep.tables == 12 and rep.hands >= 12
    assert set(rep.bots) == set(members)
    for name, b in rep.bots.items():
        assert b.seats == 12 * members.count(name), name
        assert len(b.samples) == 12, name
        assert b.stats.illegal == 0, name
        if name not in ("montecarlo", "montecarlo30", "timeout_then_recover"):
            assert b.stats.exceptions == 0, (name, b.stats.last_error)
    assert rep.bots["rival3"].stats.exceptions == 0, rep.bots["rival3"].stats.last_error
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 12 - sum(Rules().payouts)) < 1e-6
