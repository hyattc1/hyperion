import time

from hyperion.core.types import Action, ActionKind, HandResult, Rules
from hyperion.strategy.safe import SafeBot, safe_action

from .strategy_helpers import make_obs


class Boom:
    def new_table(self, rules, seat, n):
        raise RuntimeError("new_table boom")

    def act(self, obs):
        raise ValueError("act boom")

    def hand_end(self, result):
        raise RuntimeError("hand_end boom")


class Returns:
    def __init__(self, value):
        self.value = value

    def new_table(self, *a):
        pass

    def act(self, obs):
        return self.value

    def hand_end(self, r):
        pass


class Slow:
    def __init__(self):
        self.panic = None

    def new_table(self, *a):
        pass

    def set_panic(self, on):
        self.panic = on

    def act(self, obs):
        time.sleep(0.002)
        return Action.check()

    def hand_end(self, r):
        pass


def test_exception_returns_check_else_fold():
    bot = SafeBot(Boom())
    bot.new_table(Rules(), 0, 8)
    obs = make_obs(bets=[0] * 8, street=1, board="Ah Kd 2c")
    assert bot.act(obs) == Action.check()
    obs = make_obs(seat=2, bets=[10, 20, 0, 0, 0, 0, 0, 0])
    assert bot.act(obs) == Action.fold()
    bot.hand_end(HandResult(0, [0] * 8, {}, (), []))
    assert bot.errors >= 3


def test_illegal_raise_is_clamped_and_garbage_is_replaced():
    obs = make_obs(seat=2, bets=[10, 20, 0, 0, 0, 0, 0, 0])
    huge = SafeBot(Returns(Action.raise_to(10**9)))
    assert huge.act(obs) == Action.raise_to(obs.max_raise)
    tiny = SafeBot(Returns(Action.raise_to(1)))
    assert tiny.act(obs) == Action.raise_to(obs.min_raise)
    assert SafeBot(Returns("fold")).act(obs) == Action.fold()
    assert SafeBot(Returns(None)).act(obs) == Action.fold()
    # a check when a call is required becomes a call, never an illegal check
    assert SafeBot(Returns(Action.check())).act(obs) == Action.call()


def test_overruns_counted_and_panic_switches_inner_bot():
    inner = Slow()
    bot = SafeBot(inner, deadline_ms=0.5, panic_after=2)
    obs = make_obs(street=1, board="Ah Kd 2c")
    bot.act(obs)
    assert bot.overruns == 1 and not bot.panic_mode and inner.panic is None
    bot.act(obs)
    assert bot.overruns == 2 and bot.panic_mode and inner.panic is True
    assert bot.worst >= 0.002
    bot.new_table(Rules(), 0, 8)
    assert not bot.panic_mode and inner.panic is False and bot.overruns == 0


def test_safe_action_on_broken_observation():
    class NoLegal:
        pass

    assert safe_action(NoLegal()) == Action.fold()
    obs = make_obs(legal=frozenset({ActionKind.CALL}))
    assert safe_action(obs) == Action.call()


class Timed:
    """Each act() reports `cost` seconds on SafeBot's clock (patched), and records the levels it is told."""

    levels = 2

    def __init__(self):
        self.cost = 0.0
        self.panic = False
        self.level = 0
        self.seen = []

    def new_table(self, *a):
        pass

    def set_panic(self, on):
        self.panic = on

    def set_level(self, n):
        self.level = n
        self.seen.append(n)

    def act(self, obs):
        _CLOCK[0] += self.cost
        return Action.check()

    def hand_end(self, r):
        pass


_CLOCK = [0.0]


def _gov_bot(monkeypatch, **kw):
    from hyperion.strategy import safe as S

    monkeypatch.setattr(S, "perf_counter", lambda: _CLOCK[0])
    inner = Timed()
    return inner, SafeBot(inner, 0.5, 5, 0.02, S.governor(**kw))


def test_default_governor_is_none_and_the_cliff_is_unchanged():
    from hyperion.strategy.safe import Governor, governor

    assert governor() is None and not Governor().active
    assert SafeBot(Returns(Action.check())).gov is None


def test_ladder_steps_one_level_per_trigger_then_panics(monkeypatch):
    inner, bot = _gov_bot(monkeypatch, ladder=True)
    obs = make_obs(street=1, board="Ah Kd 2c")
    inner.cost = 0.0006  # over the 0.5 ms soft deadline every call
    for _ in range(5):
        bot.act(obs)
    assert bot.degrade_level == 1 and inner.level == 1 and not bot.panic_mode
    for _ in range(5):
        bot.act(obs)
    assert bot.degrade_level == 2 and inner.level == 2 and not inner.panic
    for _ in range(5):
        bot.act(obs)
    assert bot.panic_mode and inner.panic and bot.degrade_level == 3 and bot.level_max == 3


def test_window_ignores_scattered_overruns(monkeypatch):
    inner, bot = _gov_bot(monkeypatch, window=50)
    obs = make_obs(street=1, board="Ah Kd 2c")
    for i in range(400):  # one overrun every 20 calls: never five in fifty
        inner.cost = 0.0006 if i % 20 == 0 else 0.0001
        bot.act(obs)
    assert bot.overruns == 20 and not bot.panic_mode
    for _ in range(5):  # a burst of five
        inner.cost = 0.0006
        bot.act(obs)
    assert bot.panic_mode


def test_recover_steps_back_up_with_backoff(monkeypatch):
    inner, bot = _gov_bot(monkeypatch, recover=30, backoff=2.0)
    obs = make_obs(street=1, board="Ah Kd 2c")
    inner.cost = 0.0006
    for _ in range(5):
        bot.act(obs)
    assert bot.panic_mode
    inner.cost = 0.0001
    for _ in range(29):
        bot.act(obs)
    assert bot.panic_mode
    bot.act(obs)
    assert not bot.panic_mode and not inner.panic and bot.degrade_level == 0
    inner.cost = 0.0006
    for _ in range(5):
        bot.act(obs)
    assert bot.panic_mode
    inner.cost = 0.0001
    for _ in range(59):
        bot.act(obs)
    assert bot.panic_mode  # the second recovery needs 60 quiet calls
    bot.act(obs)
    assert not bot.panic_mode
    bot.new_table(Rules(), 0, 8)
    assert bot.degrade_level == 0 and bot._need == 30 and inner.level == 0
