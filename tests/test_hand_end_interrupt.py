"""The ship bot's hand end, interrupted anywhere, leaves nothing that breaks the next hand (R5; drill 7's kit E raises
a BaseException inside an event method at 1.05 ms), and defer_hand_end + idle() play exactly as the eager hand end.

Method: record a table of the bot in the simulator; replay it on a fresh bot, and at one hand end raise an exception
at the k-th line the hand end executes (sys.settrace), for k spread over the whole call; then replay the rest. Every
later call must run clean (SafeBot counts no error), the chip chain must follow the table again by the next hand end,
and nothing may stay pending."""
import copy
import sys

import pytest

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table


class Interrupt(BaseException):
    """What kit E raises in a callback past its budget (a BaseException: `except Exception` does not stop it)."""


class _Rec:
    def __init__(self, impl):
        self.impl, self.log = impl, []

    def new_table(self, rules, seat, n):
        self.log.append(("nt", rules, seat, n))
        self.impl.new_table(rules, seat, n)

    def act(self, obs):
        self.log.append(("act", copy.deepcopy(obs)))
        return self.impl.act(obs)

    def hand_end(self, result):
        self.log.append(("he", copy.deepcopy(result)))
        self.impl.hand_end(result)

    def variant_decide(self, prompt):
        return self.impl.variant_decide(prompt)


def _record(bot_name, rules, seed=97, hands=60):
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    rec = _Rec(ship.make_bot(bot_name, seed=seed))
    bots[0] = rec
    play_table(bots, Rules(**{**rules.__dict__, "max_hands": hands}), seed=seed, mode="model")
    return rec.log


def _lines(fn) -> int:
    n = 0

    def tr(frame, event, arg):
        nonlocal n
        if event == "line":
            n += 1
        return tr

    sys.settrace(tr)
    try:
        fn()
    finally:
        sys.settrace(None)
    return n


def _interrupted(fn, k: int) -> bool:
    n = 0

    def tr(frame, event, arg):
        nonlocal n
        if event == "line":
            n += 1
            if n == k:
                raise Interrupt()
        return tr

    sys.settrace(tr)
    try:
        fn()
        return False
    except Interrupt:
        return True
    finally:
        sys.settrace(None)


def _run(bot_name, log, at=None, k=0, defer=None):
    """Replay `log` on a fresh bot; hand end number `at` is interrupted at its k-th line."""
    bot = ship.make_bot(bot_name, seed=97)
    if defer:
        bot.defer_hand_end(True)
    he = 0
    hit = False
    for ev in log:
        if ev[0] == "nt":
            bot.new_table(ev[1], ev[2], ev[3])
        elif ev[0] == "act":
            bot.act(ev[1])
        else:
            if he == at:
                hit = _interrupted(lambda: bot.hand_end(ev[1]), k)
            else:
                bot.hand_end(ev[1])
            if defer == "idle":
                bot.idle()
            he += 1
    return bot, hit


def _heroes(bot):
    """Every HeroCore inside the bot (the composite's hero member and the base's fallback; hybrid3_x's; Hero's)."""
    core = bot.core
    out = []
    for m in getattr(core, "members", [core]):
        h = getattr(m, "hero", m)
        if hasattr(h, "_curve_todo"):
            out.append(h)
    return out


def _bases(bot):
    core = bot.core
    return [m for m in getattr(core, "members", [core]) if hasattr(m, "_start_hand")]


@pytest.mark.parametrize("bot_name,payouts", [("composite", (8, 7, 6, 5, 4, 3, 2, 1)),
                                              ("composite", (50, 25, 15, 10, 0, 0, 0, 0)),
                                              ("hybrid3_x", (50, 25, 15, 10, 0, 0, 0, 0))])
def test_an_interrupted_hand_end_breaks_nothing(bot_name, payouts):
    log = _record(bot_name, Rules(payouts=payouts))
    ends = [i for i, ev in enumerate(log) if ev[0] == "he"]
    at = len(ends) // 2
    ref, _ = _run(bot_name, log)
    # the hand end's length in lines, on a bot in the same state
    probe = ship.make_bot(bot_name, seed=97)
    he = 0
    total = None
    for ev in log:
        if ev[0] == "nt":
            probe.new_table(ev[1], ev[2], ev[3])
        elif ev[0] == "act":
            probe.act(ev[1])
        else:
            if he == at:
                total = _lines(lambda: probe.hand_end(ev[1]))
                break
            probe.hand_end(ev[1])
            he += 1
    assert total and total > 50
    hits = 0
    for k in sorted({1, 2, 3, 5, 8, 13, 21, 34, total // 4, total // 2, 3 * total // 4, total - 2, total - 1}):
        bot, hit = _run(bot_name, log, at, k)
        hits += hit
        assert bot.safe.errors == 0, k
        for b, r in zip(_bases(bot), _bases(ref)):
            assert b._start_hand == r._start_hand, k  # the chain follows the table again, never stuck
        for h in _heroes(bot):
            assert h._curve_todo is None or h.lazy, k  # nothing an eager Hero still owes
    assert hits >= 10


@pytest.mark.parametrize("defer", ["idle", "act"])
def test_defer_hand_end_plays_as_the_eager_hand_end(defer):
    """defer_hand_end(True): the curve and dials wait for idle() (or the next decision); every decision the same."""
    log = _record("composite", Rules(payouts=(50, 25, 15, 10, 0, 0, 0, 0)), hands=80)
    acts = [ev[1] for ev in log if ev[0] == "act"]

    def answers(mode):
        bot = ship.make_bot("composite", seed=97)
        if mode:
            bot.defer_hand_end(True)
        out = []
        for ev in log:
            if ev[0] == "nt":
                bot.new_table(ev[1], ev[2], ev[3])
            elif ev[0] == "act":
                out.append(bot.act(ev[1]))
            else:
                bot.hand_end(ev[1])
                if mode == "idle":
                    bot.idle()
        return out

    assert len(acts) > 20
    assert answers(defer) == answers(None)
