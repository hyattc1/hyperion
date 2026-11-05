"""G2: `bare_reads`, Hero's profiler at a level with no shadows (docs/drills/climb/g2-log.md). Off, or at a level where a shadow or Hero's own decisions feed it,
nothing changes; on, at `bare`, its counters at each hand's end are the ones a profiler fed at every decision holds, on the same hands."""
import copy
import hashlib
import random

import pytest

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.sim.bestiary import make_bot
from hyperion.sim.engine import BotStats, play_table

DET = {"panic_after": 10 ** 9, "late_us": 1e9, "soft_us": 1e6}
FIELD = ("rival3", "tag", "pushfold", "loose_aggro", "rival1", "station", "maniac")
COUNTERS = ("hands", "vpip", "pfr", "pre_faced", "pre_folded", "post_faced", "post_folded", "post_actions", "post_aggr", "actions", "raises", "calls",
            "folds", "checks_free", "post_free", "post_free_bets", "shoves", "shove_opps", "faced_shove", "called_shove", "faced_shove_exp", "showdowns",
            "pre_hands_b", "pre_shoves_b", "fi_opp_b", "fi_shove_b", "vo_opp_b", "vo_shove_b", "open_opp", "opens", "oft_opp", "oft_fold", "cb_opp", "cbets",
            "fcb_opp", "fcb_fold", "pb_opp", "pb_bet", "ab_opp", "ab_bet", "rb_opp", "rb_raise", "st_opp", "st_bet", "rv_opp", "rv_bet", "sz_hist", "sz_n", "szc",
            "xr_opp", "xr", "rr_n", "rr_k", "rr_by")


class _Seat:
    """Plays the composite and feeds a ghost profiler every decision and hand end, as level 0's light shadow feeds the real one, from the same observations."""

    def __init__(self, bot, level=None, hop=False, check=True):
        self.bot, self.level, self.hop, self.check = bot, level, hop, check
        self.h = hashlib.sha1()
        self.rng = random.Random(9)
        self.hands = 0
        self.diffs = []

    @property
    def prof(self):
        c = self.bot.core
        return c.members[c._hero_idx].prof

    def new_table(self, rules, seat, n):
        self.bot.new_table(rules, seat, n)
        if self.level is not None:  # (SafeBot.new_table puts level 0 back)
            self.bot.core.set_level(self.level)
        self.ghost = copy.copy(self.prof)
        self.ghost.reset(n, seat)

    def act(self, obs):
        if self.hop:
            self.bot.core.set_level(self.rng.randrange(4))
        a = self.bot.act(obs)
        self.ghost.observe(obs)
        self.h.update(repr((obs.hand_no, obs.street, a.kind.value, a.amount)).encode())
        return a

    def hand_end(self, r):
        self.bot.hand_end(r)
        self.ghost.hand_end(r)
        self.hands += 1
        if self.check:
            self.diffs += [(r.hand_no, k) for k in COUNTERS if getattr(self.prof, k) != getattr(self.ghost, k)]


def _table(dials, seed=3, level=None, hop=False, rules=None):
    seat = _Seat(ship.make_bot("composite", {**DET, **dials}, seed=5), level, hop)
    bots = [seat] + [make_bot(nm, seed=seed * 64 + i) for i, nm in enumerate(FIELD, 1)]
    res = play_table(bots, rules or Rules(), seed=seed, mode="model", stats=[BotStats(str(i)) for i in range(8)])
    return seat, seat.h.hexdigest(), res.points[0]


def test_off_the_blank_pass_starves_the_reads():
    """The bug: at `bare` with the dial off the profiler holds less than one fed at every decision."""
    seat, _, _ = _table({}, level=1)
    assert seat.diffs
    p, g = seat.prof, seat.ghost
    assert sum(map(sum, p.open_opp)) < sum(map(sum, g.open_opp))
    assert sum(p.rr_by) <= sum(g.rr_by) and sum(p.shoves) < sum(g.shoves) and sum(p.hands) < sum(g.hands)


@pytest.mark.parametrize("seed", [3, 4])
def test_on_every_counter_at_every_hand_end_as_fed_at_every_decision(seed):
    seat, _, _ = _table({"bare_reads": True}, seed=seed, level=1)
    assert seat.hands > 20 and not seat.diffs
    assert seat.prof.pend_obs == []


def test_on_the_counters_hold_through_any_change_of_level():
    """The governor moves levels between decisions, mid-hand too: levels 0-3 at random at each decision."""
    seat, _, _ = _table({"bare_reads": True}, hop=True)
    assert seat.hands > 20 and not seat.diffs


@pytest.mark.parametrize("seed", [3, 4])
def test_on_at_level_zero_and_at_the_hero_rung_plays_the_same(seed):
    """The dial moves no decision at level 0, where a shadow feeds the profiler, nor at `hero`, where Hero's own decisions do."""
    for level in (None, 3):
        off = _table({}, seed=seed, level=level)[1:]
        on = _table({"bare_reads": True}, seed=seed, level=level)[1:]
        assert off == on


def test_off_at_bare_plays_as_before_and_nothing_waits():
    seat, h, pts = _table({}, level=1)
    assert seat.prof.pend_obs == [] and seat.bot.core._late_prof is None
    assert (h, pts) == _table({"bare_reads": False}, level=1)[1:]


def test_on_only_the_levels_with_no_shadows_and_not_hero_take_observations():
    b = ship.make_bot("composite", {**DET, "bare_reads": True}, seed=5)
    b.new_table(Rules(), 0, 8)
    want = {0: False, 1: True, 2: True, 3: False}
    for lv, on in want.items():
        b.core.set_level(lv)
        assert (b.core._late_prof is not None) == on
