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


def test_the_one_size_can_wait_for_a_short_table_and_ask_for_more_folds():
    ex = Exploit(ExploitParams(bet_checked=True, stab_size=True, stab_alive=2))
    ex.size_from(_post(True))
    a = _stab(ex)  # three players have chips: the old size
    assert a.kind is RAISE and a.amount == int(0.33 * 180)
    ex = Exploit(ExploitParams(bet_checked=True, stab_size=True, stab_alive=3))
    ex.size_from(_post(True))
    assert _stab(ex).amount == int(0.5 * 180)
    # both seats fold 6 of 6: each reads 0.95, the product 0.91; asking 0.7 stabs, 0.95 does not
    for need, fires in ((0.7, True), (0.95, False)):
        ex = Exploit(ExploitParams(bet_checked=True, stab_size=True, stab_min_fold=need))
        ex.size_from(_post(True))
        assert (_stab(ex) is not None) is fires
    ex = Exploit(ExploitParams(bet_checked=True, stab_min_fold=0.95))  # no one size: bet_min_fold as before
    assert _stab(ex).amount == int(0.33 * 180)


def test_the_hold_em_gate_keeps_bet_frac_on_every_twist_table():
    """C3h: batch 6 carries Hero's one size to the buy family (bonus_card, auction) and others (postflop.s11_twists), so
    the ungated stab_size changed play there (C3 lost on bonus_card, H22 and H27). With stab_holdem_only the stab takes
    the one size on plain hold'em only."""
    from hyperion.drills import variants as V

    on = {"exploit.stab_size": True, "exploit.stab_alive": 3}
    gated = ship.make_bot("composite", {**on, "exploit.stab_holdem_only": True})
    ungated = ship.make_bot("composite", on)
    bonus = V.get("bonus_card").rules
    ungated.new_table(bonus, 0, 8)
    assert ungated.core.ex.stab_frac == 0.5  # the leak C3 had
    from hyperion.strategy.hero import holdem_table

    twists = 0
    for name in V.catalog_names():
        rules = V.get(name).rules
        gated.new_table(rules, 0, 8)
        if holdem_table(rules):  # a hold'em table with its own points or schedule (top_heavy, straddle ...)
            assert gated.core.ex.stab_frac == 0.5, name
        else:
            twists += 1
            assert gated.core.ex.stab_frac is None, name
    assert twists >= 18
    gated.new_table(Rules(), 0, 8)
    assert gated.core.ex.stab_frac == 0.5
    from hyperion.strategy.hero import HeroCore, config_from_dict

    h = HeroCore(config_from_dict({"exploit.stab_size": True, "exploit.stab_holdem_only": True,
                                   "postflop.balance_sizes": True}, seed=1))
    h.new_table(bonus, 0, 8)
    assert h.exploit.stab_frac is None
    h.new_table(Rules(), 0, 8)
    assert h.exploit.stab_frac == 0.5
