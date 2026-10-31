"""The event-field archetypes and the named fields."""
import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_cards
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from hyperion.sim.runner import run_tournament
from tests.sim_helpers import Auditor

NEW = ["montecarlo", "montecarlo30", "pushfold", "loose_aggro", "timeout_then_recover", "hero_tight", "hero_loose"]


class Counter:
    """Wraps a bot and counts decisions by street."""

    def __init__(self, inner):
        self.inner = inner
        self.by_street = {}

    def new_table(self, rules, seat, n):
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        self.by_street[obs.street] = self.by_street.get(obs.street, 0) + 1
        return self.inner.act(obs)

    def hand_end(self, result):
        self.inner.hand_end(result)


@pytest.mark.parametrize("name", NEW)
def test_each_new_bot_plays_200_hands_in_measure_mode(name):
    bots = [Auditor(B.make_bot(name, seed=s), 16000) for s in range(8)]
    t = Table(bots, Rules(), seed=11, mode="measure")
    hands = 0
    while not t.done:
        t.play_hand()
        hands += 1
    assert hands <= 200
    for s in range(8):
        st = t.stats[s]
        assert st.exceptions == 0, st.last_error
        assert st.illegal == 0
    assert sum(len(b.decisions) for b in bots) > 0


def test_montecarlo_times_out_postflop_in_strict_mode():
    mc = Counter(B.MonteCarloBot(seed=1))
    bots = [mc] + [B.CallingStation(seed=s) for s in range(7)]
    res = play_table(bots, Rules(max_hands=60), seed=2, mode="strict")
    st = res.stats[0]
    postflop = sum(v for k, v in mc.by_street.items() if k > 0)
    assert postflop >= 20
    assert st.over_budget >= 0.5 * postflop, (st.over_budget, postflop)
    assert st.exceptions == 0


def test_montecarlo_timeout_frac_models_the_rate():
    mc = Counter(B.MonteCarloBot(seed=3, timeout_frac=0.3))
    bots = [mc] + [B.CallingStation(seed=s) for s in range(7)]
    res = play_table(bots, Rules(max_hands=150, starting_stack=20000), seed=4, mode="measure")
    st = res.stats[0]
    postflop = sum(v for k, v in mc.by_street.items() if k > 0)
    assert postflop >= 60
    rate = st.over_budget / postflop
    assert 0.15 <= rate <= 0.5, rate  # 30% plus whatever the machine adds


def test_montecarlo_equity_is_sane():
    mc = B.MonteCarloBot(seed=5)
    mc.new_table(Rules(), 0, 8)
    nuts = mc.equity(parse_cards("AsAd"), parse_cards("Ac Ah 2d 7c 9s"), 1, 100, False)
    air = mc.equity(parse_cards("7c2d"), parse_cards("As Kd Qh Js 9s"), 3, 100, True)
    assert nuts == 1.0
    assert air < 0.1


def test_timeout_then_recover_breaks_after_n_hands():
    bot = B.TimeoutThenRecover(seed=9)
    bots = [bot] + [B.CallingStation(seed=s) for s in range(7)]
    res = play_table(bots, Rules(), seed=6, mode="measure")
    assert 30 <= bot.fail_from <= 120
    if res.hands > bot.fail_from + 5:
        assert res.stats[0].over_budget > 0
    assert res.stats[0].exceptions == 0


def _obs(hole, stack_bb, seat=2, bb=20):
    """Unopened preflop pot, eight seats, button at 7 (SB 0, BB 1, UTG 2): seat 2 has 7 behind."""
    n = 8
    stacks = [2000] * n
    bets = [0] * n
    bets[0], bets[1] = 10, 20
    stacks[0] -= 10
    stacks[1] -= 20
    stacks[seat] = int(stack_bb * bb) - bets[seat]
    legal = frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE})
    return Observation(hole=hole, board=(), street=0, seat=seat, button=7, stacks=stacks, bets=bets,
                       in_hand=[True] * n, pot=0, to_call=20 - bets[seat], min_raise=40,
                       max_raise=stacks[seat] + bets[seat], legal=legal, hand_no=0, blinds=(10, bb))


def test_pushfold_pushes_premiums_short_and_folds_junk():
    bot = B.PushFoldBot(seed=1)
    bot.new_table(Rules(), 0, 8)
    o = _obs(parse_cards("AsAd"), 8)
    a = bot.act(o)
    assert a.kind is ActionKind.RAISE and a.amount == o.max_raise
    o = _obs(parse_cards("7c2d"), 8)
    assert bot.act(o).kind is ActionKind.FOLD
    assert bot.act(_obs(parse_cards("As5d"), 8)).kind is ActionKind.FOLD  # A5o: button yes, UTG no
    assert bot.act(_obs(parse_cards("As5d"), 8, seat=7)).kind is ActionKind.RAISE
    o = _obs(parse_cards("AsKs"), 40)
    a = bot.act(o)
    assert a.kind is ActionKind.RAISE and a.amount < o.max_raise  # a normal open above 15 bb


def test_loose_aggro_opens_wide_and_folds_junk():
    bot = B.LooseAggroStudent(seed=1)
    bot.new_table(Rules(), 0, 8)
    assert bot.act(_obs(parse_cards("Ts9s"), 60)).kind is ActionKind.RAISE
    assert bot.act(_obs(parse_cards("7c2d"), 60)).kind is ActionKind.FOLD


def test_hero_presets_apply_overrides():
    pytest.importorskip("hyperion.strategy.hero")
    tight = B.make_bot("hero_tight", seed=1)
    loose = B.make_bot("hero_loose", seed=1)
    assert tight.impl.config.preflop.three_bet_frac < loose.impl.config.preflop.three_bet_frac
    assert tight.impl.config.pushfold.threshold_bb == 10.0
    assert tight.impl.config.preflop.open_frac[7] < loose.impl.config.preflop.open_frac[7]
    custom = B.HeroClone(seed=1, overrides={"use_profiler": False})
    assert custom.impl.config.use_profiler is False


def test_fields_resolve_to_eight_registered_bots():
    for name, members in B.FIELDS.items():
        assert len(members) == 8, name
        for nm in members:
            B.make_bot(nm, seed=1)
    assert B.field_names("Strong") == list(B.FIELDS["strong"])
    with pytest.raises(KeyError):
        B.field_names("nope")


def test_runner_field_flag_and_duplicate_names():
    from hyperion.sim.runner import main
    assert main(["--tables", "1", "--seed", "1", "--field", "strong", "--mode", "measure"]) == 0
    rep = run_tournament(B.field_names("strong"), tables=1, seed=1, mode="measure")
    assert rep.bots["pushfold"].seats == 2  # listed twice, two seats, one line in the report
