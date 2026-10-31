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
