"""R3, kit shapes: every quirk of fake kit S (hyperion/drills/fakekits/kit_s) through the reference adapter (KitSAdapter,
written the way the template asks) and the ship bot, at real tables; then the helpers that put each quirk right.

The bot is the climb's deterministic F (model mode), so two shapes that carry the same information must make the same
decisions: the shapes that lose nothing are held to the plain shape's decisions exactly; the ones that lose something
(a partial or no log, derived raise bounds) to legal moves, no exceptions and no fallback to the kit's check/fold.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules, parse_card
from hyperion.drills.adapter import (KitSAgent, dealer_state, drop_blind_posts, legal_kinds, make_observation,
                                     raise_bounds)
from hyperion.drills.conformance import check_observation, checked
from hyperion.drills.fakekits.kit_s import kit as ks
from hyperion.sim import bestiary as B
from hyperion.sim.engine import BotStats, play_table

pytestmark = pytest.mark.night  # the night's one-minute subset (pyproject.toml markers)

ROOT = Path(__file__).resolve().parents[1]
RAISE, CALL, CHECK, FOLD = ActionKind.RAISE, ActionKind.CALL, ActionKind.CHECK, ActionKind.FOLD
LOSSY = {"log_own", "log_last3", "log_none", "bounds_missing"}  # what the bot reads differs from the plain shape


def _swap():
    spec = importlib.util.spec_from_file_location("_swap_shapes", ROOT / "tools" / "swap.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def model_f():
    """The composite on SHIP_DIALS, deterministic (tools/swap.py's model setup), restored after."""
    saved = (B.HYBRID_CONFIG, B.HERO_CONFIG)
    _swap().setup_process("model")
    from hyperion.compose import bot as CB

    CB.register("shapes_f", dials={})
    yield lambda seed: B.make_bot("shapes_f", seed=seed)
    B.HYBRID_CONFIG, B.HERO_CONFIG = saved
    B.REGISTRY.pop("shapes_f", None)  # the runner's --list reads every registered class's docstring
    B._BY_CLASS.pop("composite_shapes_f", None)


class ShapeSeat:
    """Our seat: each engine Observation -> the dealer dict -> kit S's native dict for `shape` -> the agent -> the
    kit's parse of the reply -> an Action, every decision recorded."""

    def __init__(self, agent, shape):
        self.agent, self.shape, self.log, self.bad = agent, shape, [], 0

    def new_table(self, rules, seat, n):
        self.seat = seat
        label = {"seats_from_1": seat + 1, "seats_me": 0}.get(self.shape, seat)
        self.agent.new_table({"seat": label, "players": n, "stack": rules.starting_stack})

    def act(self, obs):
        st = dealer_state(obs)
        st["legal"] = set(st["legal"])
        reply = self.agent.act(ks.to_native(st, self.shape))
        try:
            kind, total = ks.parse_reply(reply, st, self.shape)
        except Exception:  # noqa: BLE001 - the kit would not read it: illegal
            self.bad += 1
            kind, total = "fold", 0
        self.log.append((obs.hand_no, obs.street, kind, total))
        return Action(ActionKind(kind), total)

    def hand_end(self, result):
        self.agent.hand_over(result.hand_no, result.deltas[self.seat])


def play_shape(shape, build, tables=2, hook=True, agent=None):
    names = [n for n in B.field_names("realistic") if n != "hero"]
    agent = agent or KitSAgent(build(77), hook=hook)
    seat = ShapeSeat(agent, shape)
    stats_all = []
    for t in range(tables):
        others = [B.make_bot(nm, seed=1000 * t + s) for s, nm in enumerate(names[:7])]
        bots = [seat] + others
        stats = [BotStats(type(b).__name__) for b in bots]
        play_table(bots, Rules(max_hands=80), seed=500 + t, rotation=t % 8, mode="model", stats=stats)
        stats_all.append(stats[0])
    return seat, agent, stats_all


@pytest.fixture(scope="module")
def base_log(model_f):
    seat, agent, stats = play_shape("base", model_f)
    assert agent.adapter.fallbacks == 0 and seat.bad == 0
    return seat.log


@pytest.mark.parametrize("shape", [s for s in ks.SHAPES if s != "base"])
def test_every_shape_plays_legal_without_fallbacks(shape, model_f, base_log):
    seat, agent, stats = play_shape(shape, model_f)
    a = agent.adapter
    assert seat.bad == 0, f"{shape}: {seat.bad} replies the kit could not read"
    assert a.fallbacks == 0, f"{shape}: {a.fallbacks} decisions fell back to the kit's check/fold"
    assert sum(s.illegal for s in stats) == 0 and sum(s.exceptions for s in stats) == 0, shape
    if shape not in LOSSY:
        assert seat.log == base_log, f"{shape}: decisions differ from the plain shape"
    assert len(seat.log) > 50


def test_shapes_report_their_quirk_and_no_violation(model_f):
    """Conformance on the shapes make_observation puts right: clean, and the quirk counted as a kit fix."""
    for shape, fix in (("bounds_swapped", "raise_bounds_swapped"), ("bounds_missing", "min_raise_derived"),
                       ("posts", "blind_posts_dropped")):
        agent = KitSAgent(model_f(5))
        checked(agent.adapter)
        play_shape(shape, model_f, tables=1, agent=agent)
        rep = agent.adapter.conformance
        assert not rep.counts, (shape, rep.summary())
        assert rep.fixes[fix] > 0, (shape, rep.summary())


def test_one_object_for_every_table_without_a_hook_restarts_the_bot(model_f):
    """R2 through the adapter: a kit that keeps one Agent for every table and never calls its table start. Before the
    fix the bot's new_table ran once (lazily), so the next tables played on the first table's state: SafeBot's panic
    (the cheap path for the rest of the table), the reads, the seat."""
    agent = KitSAgent(model_f(9), hook=False)
    bot = agent.adapter.bot
    safe = bot.impl.safe
    calls = []
    inner = bot.new_table

    def spy(r, s, n):
        inner(r, s, n)
        calls.append((s, safe.panic_mode))

    bot.new_table = spy
    seat = ShapeSeat(agent, "base")
    names = [n for n in B.field_names("realistic") if n != "hero"]
    for t in range(3):
        bots = [B.make_bot(nm, seed=t * 10 + s) for s, nm in enumerate(names[:7])]
        bots.insert(t, seat)  # our seat moves: 0, 1, 2
        safe._enter_panic()  # what a slow table leaves behind
        play_table(bots, Rules(max_hands=40), seed=900 + t, mode="model")
        assert calls and calls[-1] == (t, False), calls
    assert len(calls) == 3 and agent.adapter.tables_seen == 2


def test_a_hook_that_names_the_seat_from_1_is_corrected_at_the_first_decision(model_f):
    seat, agent, _ = play_shape("seats_from_1", model_f, tables=1)
    assert agent.adapter.seat_fixes == 1 and agent.adapter.seat == 0


# ------------------------------------------------------------------------------------------------- the helpers

@pytest.mark.parametrize("text,card", [
    ("Th", 34), ("th", 34), ("TH", 34), ("10h", 34), ("10H", 34), ("T♥", 34), ("♥T", 34), ("hT", 34),
    ("h10", 34), ("10 of hearts", 34), ("Ten of Hearts", 34), ("2c", 0), ("2♣", 0), ("Ac", 48), ("1c", 48),
    ("A♠", 51), ("A♠️", 51), ("♠A", 51), (" Kd ", 45), (("T", "h"), 34), ((10, "h"), 34),
    ((14, "s"), 51), ((1, "s"), 51), ({"rank": 10, "suit": "H"}, 34), ({"rank": "A", "suit": "spades"}, 51)])
def test_parse_card_reads_every_format(text, card):
    assert parse_card(text) == card


@pytest.mark.parametrize("bad", [34, "Xh", "", None, "T", "11x", {"rank": 3}, True])
def test_parse_card_rejects_what_it_cannot_know(bad):
    with pytest.raises(ValueError):
        parse_card(bad)


def test_legal_kinds_takes_the_kits_words():
    def k(x, to_call=20, stack=500):
        return {a.value for a in legal_kinds(x, to_call, stack)}

    assert k(["fold", "call", "raise"]) == k(["FOLD", "CALL", "RAISE"]) == k("fold,call,raise") == {"fold", "call", "raise"}
    assert k("F C R") == k([{"type": "fold"}, {"action": "Call"}, {"kind": "bet"}]) == {"fold", "call", "raise"}
    assert k(["check", "bet"], 0) == {"check", "raise"}
    assert k(["fold", "all-in"], 600, 500) == {"fold", "call"}  # the call takes every chip
    assert k(["fold", "call", "all in"], 20, 500) == {"fold", "call", "raise"}
    assert k("check/call", 0) == {"check"} and k("check/call", 20) == {"call"}
    assert k("f,c,r", 0) == {"fold", "check", "raise"} and k("f,c,r", 20) == {"fold", "call", "raise"}

    class CheckAction:
        pass

    assert k([CheckAction, ActionKind.RAISE], 0) == {"check", "raise"}
    with pytest.raises(KeyError):
        legal_kinds(["fold", "surrender"], 20, 500)


@pytest.mark.parametrize("given,want,fix", [
    ((40, 2000), (40, 2000), None),
    ((2000, 40), (40, 2000), "raise_bounds_swapped"),
    ((None, None), (40, 2000), "min_raise_derived"),
    ((40, 10 ** 9), (40, 2000), "max_raise_capped"),
])
def test_raise_bounds(given, want, fix):
    lo, hi, fixed = raise_bounds(*given, [1980, 1990], [20, 10], 0, 20, True)
    assert (lo, hi) == want and (fix in fixed if fix else not fixed)


def test_raise_bounds_short_all_in_and_a_raised_pot():
    assert raise_bounds(80, 60, [50, 1990], [10, 40], 0, 20, True)[:2] == (60, 60)  # all-in below the min raise
    assert raise_bounds(None, None, [500, 400, 300], [0, 60, 20], 0, 20, True)[:2] == (100, 500)  # 60 after 20: +40


def test_drop_blind_posts_only_at_the_start():
    R = lambda s, t: (s, Action(RAISE, t))  # noqa: E731
    posts = [R(1, 10), R(2, 20), R(3, 60)]
    assert drop_blind_posts(posts, 20, 0) == ([R(3, 60)], 2)
    assert drop_blind_posts(posts, 20, 2) == ([R(3, 60)], 2)  # the full log on the turn
    assert drop_blind_posts([R(3, 20)], 20, 1) == ([R(3, 20)], 0)  # a flop log of this street: a min bet
    assert drop_blind_posts([R(3, 60), R(1, 10)], 20, 0) == ([R(3, 60), R(1, 10)], 0)


def test_make_observation_is_unchanged_on_a_clean_kit():
    obs = make_observation(hole=[parse_card("Ah"), parse_card("Kd")], board=[], street=0, seat=3, button=0,
                           stacks=[2000, 1990, 1980, 2000], bets=[0, 10, 20, 0], in_hand=[True] * 4, pot=0, to_call=20,
                           min_raise=40, max_raise=2000, legal=["fold", "call", "raise"], hand_no=0, blinds=(10, 20),
                           history=[])
    assert (obs.min_raise, obs.max_raise, obs.to_call) == (40, 2000, 20) and "kit_fixes" not in obs.extras
    assert not check_observation(obs)


def test_conformance_flags_blind_posts_and_seats_from_one():
    obs = Observation(hole=(48, 45), board=(), street=0, seat=3, button=0, stacks=[2000, 1990, 1980, 2000],
                      bets=[0, 10, 20, 0], in_hand=[True] * 4, pot=0, to_call=20, min_raise=40, max_raise=2000,
                      legal=frozenset((FOLD, CALL, RAISE)), hand_no=0, blinds=(10, 20),
                      history=[(1, Action(RAISE, 10)), (2, Action(RAISE, 20))])
    assert any(v.startswith("history_blind") for v in check_observation(obs))
    obs.seat = 4
    assert any("numbered from 1" in v for v in check_observation(obs))
