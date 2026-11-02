"""The composite's degradation levels (backlog R1): off by default and bit-identical at level 0; `noshadow` skips exactly
the full shadows, `base` / `hero` force every section to one member, `lean` sends the base's exact-ICM decisions to
Hero under top-heavy payouts; and SafeBot's governor steps through them."""
import hashlib

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.sim.bestiary import make_bot
from hyperion.sim.engine import BotStats, play_table

DET = {"panic_after": 10 ** 9, "late_us": 1e9, "soft_us": 1e6}
FIELD = ("rival3", "tag", "pushfold", "loose_aggro", "rival1", "station", "maniac")
TH = (50, 25, 12, 6, 3, 2, 1, 1)


class _Hash:
    def __init__(self, bot, level=None):
        self.bot, self.h, self.level = bot, hashlib.sha1(), level

    def new_table(self, rules, seat, n):
        self.bot.new_table(rules, seat, n)
        if self.level is not None:  # (SafeBot.new_table puts level 0 back)
            self.bot.core.set_level(self.level)

    def act(self, obs):
        a = self.bot.act(obs)
        self.h.update(repr((obs.hand_no, obs.street, a.kind.value, a.amount)).encode())
        return a

    def hand_end(self, r):
        self.bot.hand_end(r)


def _table(bot, seed=3, rules=None, level=None):
    seat = _Hash(bot, level)
    bots = [seat] + [make_bot(nm, seed=seed * 64 + i) for i, nm in enumerate(FIELD, 1)]
    res = play_table(bots, rules or Rules(), seed=seed, mode="model", stats=[BotStats(str(i)) for i in range(8)])
    return seat.h.hexdigest(), res.points[0]


def test_defaults_have_no_levels_and_no_governor():
    b = ship.make_bot("composite", {})
    assert b.core.levels == 0 and b.safe.gov is None and b.core.level == 0


def test_level_zero_is_bit_identical():
    ref = _table(ship.make_bot("composite", dict(DET), seed=5))
    dials = {**DET, "degrade": "noshadow,base", "panic_ladder": True, "panic_window": 50, "panic_recover": 40}
    b = ship.make_bot("composite", dials, seed=5)
    assert b.core.levels == 2 and b.safe.gov is not None
    assert _table(b) == ref


def test_noshadow_skips_exactly_the_full_shadows():
    b = ship.make_bot("composite", {**DET, "degrade": "noshadow"}, seed=5)
    for seed in (3, 4, 5):
        _table(b, seed, level=1)
    c = b.core.counts
    assert c["pre_raised_short:hero"] > 0
    assert c["shadow:skip"] == c["pre_raised_short:hero"]  # the base's full preflop shadow; the light ones stay


def test_base_and_hero_levels_force_one_member():
    b = ship.make_bot("composite", {**DET, "degrade": "noshadow,base"}, seed=5)
    _table(b, level=2)
    assert not any(k.endswith(":hero") for k in b.core.counts)
    h = ship.make_bot("composite", {**DET, "degrade": "hero"}, seed=5)
    _table(h, level=1)
    assert not any(k.endswith(":base") for k in h.core.counts) and h.core.counts["level:1"] > 0


def test_lean_sends_exact_icm_decisions_to_hero_under_top_heavy_payouts():
    b = ship.make_bot("composite", {**DET, "degrade": "lean"}, seed=5)
    for seed in (3, 4):
        _table(b, seed, Rules(payouts=TH), level=1)
    assert b.core.base.counts["hero:lean"] > 0
    lin = ship.make_bot("composite", {**DET, "degrade": "lean"}, seed=5)
    for seed in (3, 4):
        _table(lin, seed, level=1)
    assert lin.core.base.counts["hero:lean"] == 0  # linear payouts: the closed form is cheap, nothing changes


def test_hybrid_lean_level():
    h = ship.make_bot("hybrid3_x", {"panic_after": 10 ** 9, "soft_us": 1e6, "panic_ladder": True})
    assert h.core.levels == 1 and h.safe.gov is not None
    h.core.set_level(1)
    assert h.core.core.lean
    h.core.set_level(0)
    assert not h.core.core.lean
