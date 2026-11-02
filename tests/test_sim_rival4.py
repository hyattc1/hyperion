"""Red-team rival 4 (`rival4`, drill 4's bot, built with no assigned philosophy) behind the bestiary adapter, the two
judge fields it sits in, and the `<field>@<bot>` swap that seats a candidate core in Hero's seat. Rival 4 is the
judge: no candidate is measured against it or tuned on it before the one final comparison, so these tests check that
it plays and that the fields are wired, never how well anything does. The smoke runs are not measurements: they
assert conservation and legality only."""
import random
from time import perf_counter_ns

import pytest

from hyperion.core.icm import icm_equity
from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules, parse_cards
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Auditor

BRIEF = (10, 7, 5, 4, 3, 2, 1, 0)


@pytest.fixture
def rival4_debug():
    """Rival 4 has no debug switch: act() swallows every exception into a legal action, and new_table() and
    hand_end() swallow theirs. Unwrap act() so an exception reaches the engine's counters, and record every exception
    in the hand-end model update and the payout read even where the rival swallows it. Restored afterwards."""
    from hyperion.sim.rivals import rival4

    errors: list[str] = []
    old_act, old_fin, old_pay = rival4.Bot.act, rival4.Bot._finalize, rival4.Bot._set_pay

    def act(self, obs):
        legal = set(obs.legal)
        return self._legalize(self._act(obs, legal), obs, legal)

    def recorded(fn):
        def w(self, *a):
            try:
                return fn(self, *a)
            except Exception as e:  # noqa: BLE001 - recorded, then re-raised into the rival's own handler
                errors.append(repr(e))
                raise
        return w

    rival4.Bot.act, rival4.Bot._finalize, rival4.Bot._set_pay = act, recorded(old_fin), recorded(old_pay)
    try:
        yield errors
    finally:
        rival4.Bot.act, rival4.Bot._finalize, rival4.Bot._set_pay = old_act, old_fin, old_pay


def test_rival4_plays_300_hands_in_measure_mode_with_zero_exceptions(rival4_debug):
    rules = Rules(max_hands=300, starting_stack=16000)  # deep enough that busts do not end it early
    hands = decisions = 0
    seed = 0
    while hands < 300:
        bots = [Auditor(B.make_bot("rival4", seed=seed * 8 + s), 8 * 16000) for s in range(8)]
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
    assert rival4_debug == [], rival4_debug[:3]  # no model update or payout read failed, swallowed or not


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


def test_rival4_timeout_rate_in_strict_mode_is_under_one_percent():
    # Median ~20 us per decision (table lookups and a few 1.3-us ICM calls, no sampler, no replay), so its overruns
    # are the host's: they track a fixed 30 us loop's (redteam-4.md section 4). Over 1%, that loop decides whose fault
    # it is: skip if it overruns too, fail if it does not.
    names = ["rival4", "tag", "pushfold", "loose_aggro", "nit", "station", "random", "rival1"]
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
            pytest.skip(f"host oversubscribed: rival4 {rate:.2%} over 1 ms, a fixed 30 us loop {host:.2%}")
    assert rate < 0.01, (over, calls)


def test_rival4_has_no_cost_model_so_mode_model_never_folds_it_for_time():
    # The deterministic timeout model folds only bots that report `last_cost_ns`; rival 4 reports none, so in mode
    # "model" its timeout count is zero by construction while its wall-clock latency is still recorded.
    bot = B.make_bot("rival4", seed=1)
    assert not hasattr(bot, "use_cost_model") and getattr(bot, "last_cost_ns", None) is None
    names = ["rival4", "tag", "pushfold", "loose_aggro", "nit", "station", "random", "montecarlo"]
    res = play_table([B.make_bot(n, seed=s) for s, n in enumerate(names)], Rules(), seed=3, mode="model")
    st = res.stats[0]
    assert st.over_budget == 0 and st.calls + st.first_calls > 0 and st.sum_ns > 0


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


def test_adapter_passes_the_payouts_so_its_icm_prices_the_table_that_scores_it():
    bot = B.make_bot("rival4", seed=1)
    assert isinstance(bot, B.Rival4Bot) and type(bot.impl).__module__ == "hyperion.sim.rivals.rival4"
    assert bot.impl.pay == list(BRIEF)  # before new_table: the brief's table, its fallback
    bot.new_table(Rules(), 2, 8)
    assert bot.impl.pay == list(Rules().payouts) and bot.impl.cap == Rules().max_hands
    assert (bot.impl.base, bot.impl.d1x, bot.impl.d2x) == (1.0, 0, 0)  # 8..1: points = 1 + players outlasted
    # its O(n^2) ICM equals the engine's exact ICM up to a constant per alive count, so every comparison it makes
    # between branches is priced on our table
    rng = random.Random(4)
    for _ in range(60):
        k = rng.randint(2, 8)
        st = [rng.randint(1, 9000) for _ in range(k)] + [0] * (8 - k)
        ours = icm_equity(st, Rules().payouts)
        gaps = [ours[i] - bot.impl.icm(st, i) for i in range(k)]
        assert max(gaps) - min(gaps) < 1e-9, (st, gaps)
    # a variant's table reaches it the same way; the brief's table gives the rival's own decomposition
    bot.new_table(Rules(payouts=BRIEF), 0, 8)
    assert bot.impl.pay == list(BRIEF) and (bot.impl.base, bot.impl.d1x, bot.impl.d2x) == (1.0, 2, 1)
    # the shared rival 1/2/3 dict carries no payouts: through it rival 4 would price the brief's table
    shared = B.RivalBot.kit_rules(bot, Rules(), 8)
    assert "payouts" not in shared and B.make_bot("rival1").kit_rules(Rules(), 8) == shared
    bare = B.make_bot("rival4", seed=1)
    bare.impl.new_table(shared, 2, 8)
    assert bare.impl.pay == list(BRIEF)


def test_adapter_round_trip_and_hand_end_passes_the_history_in_kit_shape():
    bot = B.make_bot("rival4", seed=1)
    bot.new_table(Rules(), 2, 8)

    # our Observation -> the kit's -> the rival's answer -> a legal Action
    o = _preflop(parse_cards("7c2d"))
    k = bot.to_kit(o)
    assert k.legal == {"fold", "call", "raise"} and k.hand_no == 5 and k.history == []
    a = bot.act(o)
    assert a == Action.fold()  # 72o first in at 100 bb
    assert bot.impl.cur_hand == 5  # it opened its hand on the kit's hand_no

    # everything happens after its only decision; only hand_end can show it. Seat 6 shoves over seat 3's open
    rest = [(3, Action.raise_to(60)), (4, Action.fold()), (5, Action.fold()), (6, Action.raise_to(2000)),
            (7, Action.fold()), (0, Action.fold()), (1, Action.fold()), (3, Action.call())]
    assert bot.impl.seen == {}
    seen = {}
    real_hand_end = bot.impl.hand_end
    bot.impl.hand_end = lambda r: (seen.setdefault("result", r), real_hand_end(r))
    bot.hand_end(HandResult(4, [0] * 8, {}, (), [(2, a)] + rest))
    r = seen["result"]
    assert r["hand_no"] == 5 and r["history"][:3] == [(2, ("fold", 0)), (3, ("raise", 60)), (4, ("fold", 0))]
    im = bot.impl
    assert all(im.seen[s] == 1 for s in range(8))  # every seat that acted was seen once
    assert (im.vpip[3], im.raised[3], im.shoves[3]) == (1, 1, 0)  # opened 3 bb, then called the shove
    assert (im.vpip[6], im.raised[6], im.shoves[6]) == (1, 1, 1)  # a raise of 8 bb or more counts as a shove
    assert (im.vpip[4], im.raised[4]) == (0, 0) and im.cur_hist is None  # folded; the hand is closed

    # the shared rival 1/2 adapter passes no history; rival 4 would then never see a hand it folded first in
    bare = B.make_bot("rival4", seed=1)
    bare.new_table(Rules(), 2, 8)
    bare.act(_preflop(parse_cards("7c2d")))
    B.RivalBot.hand_end(bare, HandResult(4, [0] * 8, {}, (), [(2, a)] + rest))
    assert bare.impl.seen == {}


def test_rival4_reads_six_passive_hands_as_a_folder_and_one_call_clears_it():
    bot = B.make_bot("rival4", seed=1)
    bot.new_table(Rules(), 2, 8)
    folds = [(s, Action.fold()) for s in (2, 3, 4, 5, 6, 7, 0)]
    for h in range(6):
        bot.hand_end(HandResult(h, [0] * 8, {}, (), folds))
    assert bot.impl.is_folder(5) and not bot.impl.is_folder(1)  # seat 1 (the big blind) never acted
    bot.hand_end(HandResult(6, [0] * 8, {}, (), [(5, Action.call())]))
    assert not bot.impl.is_folder(5)


def test_rival4_shoves_premiums_short_and_folds_junk_through_the_adapter():
    bot = B.make_bot("rival4", seed=1)
    bot.new_table(Rules(), 2, 8)
    o = _preflop(parse_cards("AsAd"))
    o.stacks[2], o.max_raise = 140, 140  # 7 bb UTG: its push/fold zone (8 bb or less)
    a = bot.act(o)
    assert a.kind is ActionKind.RAISE and a.amount == 140
    o.hole = parse_cards("7c2d")
    assert bot.act(o).kind is ActionKind.FOLD


def test_rival4_play_is_reproducible_run_to_run():
    # no wall-clock time box and one RNG seeded at construction: the same seed plays the same table
    names = ["rival4", "tag", "pushfold", "loose_aggro", "nit", "station", "random", "rival1"]

    def once():
        bots = [B.make_bot(n, seed=s) for s, n in enumerate(names)]
        r = play_table(bots, Rules(), seed=11, mode="measure")
        return r.points, r.places, r.hands, r.stacks

    assert once() == once()


def test_judge_fields_have_the_agreed_seats():
    judge = B.field_names("judge")
    assert judge == ["hero", "rival4", "montecarlo30", "montecarlo", "pushfold", "loose_aggro", "tag",
                     "timeout_then_recover"]
    assert sorted(judge) == sorted("rival4" if m == "rival1" else m for m in B.FIELDS["realistic"])  # rival 1's seat
    assert judge == ["rival4" if m == "rival3" else m for m in B.FIELDS["holdout"]]  # holdout's order, seat for seat
    assert B.field_names("judge_top") == ["hero", "rival1", "rival2", "rival3", "rival4", "pushfold", "tag",
                                          "loose_aggro"]
    for name, members in B.FIELDS.items():
        if not name.startswith(("judge", "outside")):  # outside*: the climb's judge-like fields
            assert "rival4" not in members, name  # every earlier field is unchanged


def test_hero_seat_swap_seats_a_candidate_with_every_other_seat_unchanged(monkeypatch):
    for field in ("judge", "judge_top"):
        base = B.field_names(field)
        for cand in B.JUDGE_CANDIDATES:
            swapped = B.field_names(f"{field}@{cand}")
            assert swapped == [cand] + base[1:], (field, cand)  # Hero's seat, so the same deals seat for seat
            assert f"{field}@{cand}" in B.FIELDS  # pre-registered: `python -m hyperion.sim --field` accepts it
    assert set(B.JUDGE_CANDIDATES) >= {"hybrid", "hybrid3"} and all(c in B.REGISTRY for c in B.JUDGE_CANDIDATES)
    # generic: any field with one `hero` seat and any registered bot not already seated, from code
    assert B.field_names("Holdout@Hero_Loose") == ["hero_loose"] + B.field_names("holdout")[1:]
    assert B.field_names("judge@hero") == B.field_names("judge")
    with pytest.raises(KeyError):
        B.field_names("judge@nope")
    with pytest.raises(KeyError):
        B.field_names("judge_top@rival2")  # already seated: the report would merge the two seats
    monkeypatch.setitem(B.FIELDS, "no_hero", ("tag",) * 8)
    with pytest.raises(KeyError):
        B.field_names("no_hero@hybrid")  # no Hero seat to swap


@pytest.mark.parametrize("field", ["judge", "judge_top"])
def test_judge_field_with_hero_runs_twelve_strict_tables_without_exceptions(field):
    # a smoke run, not a measurement: conservation, seats and legality only; no number from it is read
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
    assert abs(sum(b.mean * b.seats for b in rep.bots.values()) / 12 - sum(Rules().payouts)) < 1e-6
