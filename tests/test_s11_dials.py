"""S11's fixes against the second exploiter (docs/drills/climb/s11-log.md): each behind a dial that defaults to the
shipped play (tests/test_ship.py replays rival 3 as built at the defaults; tests/test_compose.py the composite); here
each one reaches the decisions it names, and the new reads count what they say."""
import pytest

from hyperion.core.types import Action, ActionKind, Observation, Rules
from hyperion.strategy.exploit import Exploit, ExploitParams
from hyperion.strategy.profiler import Profiler

from .test_s2_dials import _digest

HU = ["hero", "exploiter2"]
THREE = ["hero", "exploiter2", "loose_aggro"]
R2, R3 = Rules(n_players=2, payouts=(10, 7)), Rules(n_players=3, payouts=(10, 7, 5))
FIN = {"r3.v3_defend": True, "hero.postflop.cbet_size_dry": 0.5}


def _obs(street, seat, hist, bets=(0, 0), stacks=(1000, 1000), to_call=0, button=0, pot=100):
    return Observation(hole=(0, 1), board=(8, 20, 33)[:3 if street else 0], street=street, seat=seat, button=button,
                       stacks=list(stacks), bets=list(bets), in_hand=[True, True], pot=pot, to_call=to_call,
                       min_raise=40, max_raise=1000, legal=frozenset(ActionKind), hand_no=0, blinds=(10, 20),
                       history=list(hist))


def _hu_hand(prof, flop):
    """A heads-up hand, me seat 0 on the button (small blind): I open, seat 1 calls; then the flop actions."""
    pre = [(0, Action.raise_to(50)), (1, Action.call())]
    prof.observe(_obs(0, 0, [], bets=(10, 20), to_call=10))
    prof.observe(_obs(1, 0, pre + flop[:-1]))
    from hyperion.core.types import HandResult
    prof.hand_end(HandResult(hand_no=0, deltas=[0, 0], history=pre + flop, showdown={}, board=()))


def test_the_probe_read_counts_leads_into_me_and_not_my_cbets():
    prof = Profiler(2)
    prof.reset(2, 0)
    _hu_hand(prof, [(1, Action.raise_to(40)), (0, Action.fold())])  # it leads into my open: a probe, a bet
    assert (prof.pb_opp[1], prof.pb_bet[1], prof.ab_opp[0]) == (1, 1, 0)
    _hu_hand(prof, [(1, Action.check()), (0, Action.raise_to(50)), (1, Action.raise_to(200)), (0, Action.fold())])
    assert (prof.pb_opp[1], prof.pb_bet[1]) == (2, 1)  # it checked to me: a probe chance it did not take
    assert (prof.rb_opp[1], prof.rb_raise[1]) == (1, 1)  # ... and raised my c-bet
    assert prof.probe_rate(1, 0.5, 2.0) == pytest.approx((1 + 1.0) / (2 + 2.0))


def test_the_raise_guard_reads_raises_of_my_postflop_bets():
    ex = Exploit(ExploitParams(bet_checked=True, raise_guard=0.3))
    ex.new_table(2, 0)
    for _ in range(3):
        ex.hand_no = None
        ex.observe(_obs(0, 0, [], bets=(10, 20), to_call=10))
        hist = [(0, Action.raise_to(50)), (1, Action.call()), (1, Action.check()), (0, Action.raise_to(40)),
                (1, Action.raise_to(160))]
        ex.observe(_obs(1, 0, hist, bets=(40, 160), to_call=120))
        from hyperion.core.types import HandResult
        ex.hand_end(HandResult(hand_no=0, deltas=[0, 0], history=hist + [(0, Action.fold())], showdown={}, board=()))
    assert ex.xr_faced[1] == 3 and ex.xr_raised[1] == 3 and ex.raise_rate(1) > 0.3


@pytest.mark.parametrize("dials", [{"r3.v3_bvb_prior": 0.15}, {"hero.postflop.probe_from": 0.6},
                                   {"hero.postflop.cbet_from": 0.7}, {"hero.postflop.balance_sizes": True},
                                   {"hero.postflop.wide_from": 0.65},
                                   {"exploit.raise_guard": 0.3},
                                   {"hero.postflop.probe_from": 0.6, "hero.postflop.probe_trap": 1.0}])
def test_each_s11_dial_reaches_the_decisions(dials):
    names, rules = (HU, R2)
    assert any(_digest({**FIN, **dials}, t, names, rules)[0] != _digest(FIN, t, names, rules)[0]
               for t in range(10)), dials


def test_three_handed_with_every_s11_dial_replays_exactly():
    d = {**FIN, "r3.v3_bvb_prior": 0.15, "r3.v3_bvb_f4_cap": 0.45, "hero.postflop.probe_from": 0.6,
         "hero.postflop.cbet_from": 0.7, "hero.postflop.probe_raise_tier": 5, "hero.postflop.probe_trap": 0.5,
         "hero.postflop.probe_margin": 0.03, "hero.postflop.balance_from": 0.3, "hero.postflop.probe_bluff": 0.5,
         "hero.postflop.wide_from": 0.65,
         "hero.postflop.raiser_from": 0.3, "hero.postflop.balance_sizes": True, "exploit.raise_guard": 0.3}
    assert _digest(d, 1, THREE, R3)[0] == _digest(d, 1, THREE, R3)[0]
