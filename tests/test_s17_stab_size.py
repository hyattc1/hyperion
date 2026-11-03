"""S17 (docs/drills/climb/s17-log.md): one size for the exploit layer's stab. With `exploit.stab_size` the layer's
bet_checked bets the host's one balanced size (Hero's hero.postflop.balance_sizes, on hold'em tables) instead of
bet_frac; off (the default) it plays as before."""
from types import SimpleNamespace

from hyperion import ship
from hyperion.core.types import Action, ActionKind, Rules
from hyperion.strategy.exploit import POST_MW, Exploit, ExploitParams

from .test_s2_dials import _digest
from .test_strategy_exploit_layer import _flop_checked_to

K, RAISE = Action.check(), ActionKind.RAISE
HU = ["hero", "exploiter2"]
R2 = Rules(n_players=2, payouts=(10, 7))


def _stab(ex: Exploit) -> Action:
    """Checked to on a three-way flop by two seats that check and fold: the layer's stab (pot 180)."""
    obs = _flop_checked_to(ex)
    for s in (0, 1):
        ex.streak[s][POST_MW] = 4
        ex.fold[s][POST_MW], ex.faced[s][POST_MW] = 6.0, 6.0
    return ex.override(obs, K)


def _post(balance: bool, size: float = 0.5):
    return SimpleNamespace(p=SimpleNamespace(balance_sizes=balance, balance_size=size))


def test_the_stab_takes_the_hosts_one_size():
    ex = Exploit(ExploitParams(bet_checked=True, stab_size=True))
    ex.size_from(_post(True))
    a = _stab(ex)
    assert a.kind is RAISE and a.amount == int(0.5 * 180) and ex.last == "bet_checked"


def test_without_one_size_or_with_the_dial_off_the_stab_keeps_bet_frac():
    for params, post in ((ExploitParams(bet_checked=True, stab_size=True), _post(False)),
                         (ExploitParams(bet_checked=True), _post(True)),
                         (ExploitParams(bet_checked=True, stab_size=True), None)):
        ex = Exploit(params)
        ex.size_from(post)
        assert ex.stab_frac is None
        a = _stab(ex)
        assert a.kind is RAISE and a.amount == int(0.33 * 180)


def test_the_composite_reads_its_postflop_members_size_per_table():
    bot = ship.make_bot("composite", {"exploit.stab_size": True})
    bot.new_table(Rules(), 0, 8)
    assert bot.core.ex.p.stab_size and bot.core.ex.stab_frac == 0.5  # hold'em: Hero bets one size (batch 5)
    bot.new_table(Rules(extras={"variant": "bounty", "bounty_ratio": 1.5}), 0, 8)
    assert bot.core.ex.stab_frac is None  # a twist table: Hero's one size is hold'em only, so the stab keeps 0.33
    bot.new_table(Rules(), 0, 8)
    assert bot.core.ex.stab_frac == 0.5
    off = ship.make_bot("composite", {})
    off.new_table(Rules(), 0, 8)
    assert not off.core.ex.p.stab_size and off.core.ex.stab_frac is None
    no_bal = ship.make_bot("composite", {"exploit.stab_size": True, "hero.postflop.balance_sizes": False})
    no_bal.new_table(Rules(), 0, 8)
    assert no_bal.core.ex.stab_frac is None


def test_hero_with_its_own_layer_takes_its_size_too():
    from hyperion.strategy.hero import HeroCore, config_from_dict

    h = HeroCore(config_from_dict({"exploit.stab_size": True, "postflop.balance_sizes": True}, seed=1))
    h.new_table(Rules(), 0, 8)
    assert h.exploit.stab_frac == 0.5


def test_the_dial_reaches_the_decisions_heads_up_against_exploiter2():
    on = {"exploit.stab_size": True}
    assert any(_digest(on, t, HU, R2)[0] != _digest({}, t, HU, R2)[0] for t in range(6))
    assert _digest(on, 1, HU, R2)[0] == _digest(on, 1, HU, R2)[0]  # and replays exactly
