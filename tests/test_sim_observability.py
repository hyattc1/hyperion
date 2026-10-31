"""SafeBot-swallowed errors and overruns reach the engine's columns, and the bust tracer names the
module and sub-decision that acted (a silent KeyError once ran at one hand in 25 for hours)."""
from hyperion.core.types import Action, ActionKind, Rules
from hyperion.sim.bestiary import CallingStation, make_bot
from hyperion.sim.engine import find_safe, play_table
from hyperion.sim.runner import BustTracer, format_busts, run_tournament
from hyperion.strategy.safe import SafeBot


class Flaky:
    """Checks or calls (so it stays in the table), but raises a KeyError on every fifth decision."""

    def __init__(self):
        self.n = 0

    def new_table(self, rules, seat, n):
        pass

    def act(self, obs):
        self.n += 1
        if self.n % 5 == 0:
            raise KeyError("missing label")
        return Action.check() if ActionKind.CHECK in obs.legal else Action.call()

    def hand_end(self, result):
        pass


class Wrapped:
    """A bestiary-style wrapper: the SafeBot sits two levels down (wrapper.impl.safe)."""

    def __init__(self, impl):
        self.impl = impl

    def new_table(self, rules, seat, n):
        self.impl.new_table(rules, seat, n)

    def act(self, obs):
        return self.impl.act(obs)

    def hand_end(self, result):
        self.impl.hand_end(result)


def test_safebot_errors_and_overruns_are_engine_columns_not_exceptions():
    inner = Flaky()
    bot = SafeBot(inner, deadline_ms=0.0)  # a zero deadline: every call overruns
    bots = [bot] + [CallingStation() for _ in range(7)]
    res = play_table(bots, Rules(max_hands=30), seed=3, mode="measure")
    st = res.stats[0]
    assert st.exceptions == 0, "SafeBot hides the KeyError from the engine"
    assert st.safe_err == inner.n // 5 > 0
    assert st.safe_over == bot.calls > 0
    assert all(o.safe_err == 0 and o.safe_over == 0 for o in res.stats[1:])


def test_find_safe_walks_impl_and_inner_chains():
    hero = make_bot("hero", seed=1)  # bestiary.Hero -> strategy.Hero (.safe)
    assert find_safe(hero) is hero.impl.safe
    assert find_safe(Wrapped(hero.impl)) is hero.impl.safe
    tracer = BustTracer(hero, "hero", ["hero"] * 8, [])
    assert find_safe(tracer) is hero.impl.safe
    direct = SafeBot(Flaky())
    assert find_safe(direct) is direct
    assert find_safe(CallingStation()) is None


def test_runner_report_has_the_columns_and_a_clean_hero():
    rep = run_tournament(["hero", "station"], tables=2, seed=4, mode="strict")
    text = rep.format()
    assert "safe_err" in text and "safe_over" in text
    assert rep.bots["hero"].stats.safe_err == 0
    assert "WARNING" not in text


def test_bust_tracer_attributes_module_and_sub_decision():
    rep = run_tournament(["hero", "allin", "allin", "maniac"], tables=6, seed=5, mode="measure", trace_busts="hero")
    assert rep.busts, "hero must bust somewhere against three all-in bots over six tables"
    paths = {b["path"] for b in rep.busts}
    assert any("." in p for p in paths), paths  # module.sub, e.g. pushfold.call_shove or preflop.call_shove
    assert all(p.split(":")[-1].split(".")[0] in ("preflop", "pushfold", "postflop", "safe", "act", "none") for p in paths), paths
    assert all("inner_error" in b and "overran" in b for b in rep.busts)
    assert not any(b["inner_error"] for b in rep.busts)
    text = format_busts(rep.busts, rep.bots["hero"].seats)
    assert "inner error" in text and "module / street / kind" in text
