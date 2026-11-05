"""S16's trust weight on the steal reads (docs/drills/climb/s16-log.md): r3.read_trust (rival 3's core's fold read in
an unopened pot) and exploit.read_trust (the layer's steal_min_fold), applied per seat while the table reads strong
(the hero member's Profiler.strong_table) or, with trust_seat_rr, to a seat that re-raised my first-in raises."""
from hyperion import ship
from hyperion.compose.bot import BATCH8_OFF
from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules
from hyperion.core.types import parse_cards as parse
from hyperion.hybrid.core3 import Rival3Core
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table
from hyperion.strategy.exploit import PRE, Exploit, ExploitParams
from hyperion.strategy.profiler import Profiler

from .test_ship import QUIET, _Recorder

R, C, F, K = ActionKind.RAISE, ActionKind.CALL, ActionKind.FOLD, ActionKind.CHECK
ON = {"r3.read_trust": 10.0, "exploit.read_trust": 10.0}
STRONG = ["hero", "elite1", "elite2", "rival1", "rival2", "rival3", "agent_pushfold", "agent_default"]


def _core(fr, fr_f, read_trust=10.0, trust=True):
    from dataclasses import replace

    c = Rival3Core()
    c.k = replace(c.k, read_trust=read_trust)
    S = c.st[1]
    S.hands, S.vpip, S.fr, S.fr_f = 40, 10, fr, fr_f
    c.trust = [False, trust] + [False] * 6
    return c


def test_fold_trust_shrinks_a_folding_seat_and_keeps_a_caller():
    c = _core(20, 18)
    assert abs(c._fold_prob(1, False) - 20.4 / 24) < 1e-9
    assert abs(c._fold_trust(1, False) - (0.6 + 0.3 * 20 / 30)) < 1e-9  # 0.8
    c = _core(6, 6)  # under ten raises faced: the prior alone
    assert abs(c._fold_trust(1, False) - 0.6) < 1e-9 and c._fold_prob(1, False) > 0.8
    c = _core(20, 4)  # a seat that calls: its read (0.27) narrows our risk and is kept
    assert c._fold_trust(1, False) == c._fold_prob(1, False) < 0.3
    c = _core(20, 18, trust=False)  # not marked: the read as built
    assert c._fold_trust(1, False) == c._fold_prob(1, False)
    c = _core(0, 0)
    c.st[1].dead, c.st[1].vpip, c.st[1].hands = 1, 0, 5  # a dead seat folds to anything
    assert c._fold_trust(1, True) == 1.0


def _ex_obs(seat=5, button=5):
    n = 8
    return Observation(hole=parse("7c 2d"), board=(), street=0, seat=seat, button=button, stacks=[2000] * n,
                       bets=[10, 20, 0, 0, 0, 0, 0, 0], in_hand=[True] * n, pot=0, to_call=20, min_raise=40,
                       max_raise=2000, legal=frozenset({F, C, R}), hand_no=0, blinds=(10, 20), history=[])


def test_layer_trusted_pre_counts_raises_faced_and_prices_the_steal_with_it():
    ex = Exploit(ExploitParams(steal_min_fold=0.7, read_trust=10.0))
    ex.new_table(8, 7)
    obs = _ex_obs(seat=7, button=7)  # the button, first in: only the blinds behind
    ex.observe(obs)
    for s in (0, 1):  # the blinds: decayed fold reads of 0.95, twelve raises faced
        ex.fold[s][PRE], ex.faced[s][PRE], ex.faced_n[s] = 0.95 * 6.0, 6.0, 12
    t = ex.trusted_pre(0)
    assert abs(t - (0.65 + (0.95 - 0.65) * 12 / 22)) < 1e-9
    assert ex.override(obs, Action.fold()) is not None  # untrusted: about 0.94 x 0.94 >= 0.7
    ex.trust = [True] * 8
    assert t * t < 0.7 and ex.override(obs, Action.fold()) is None
    ex.trust = [False] * 8
    assert ex.override(obs, Action.fold()) is not None
    ex.faced_n[0] = 9  # under ten: the prior
    assert ex.trusted_pre(0) == 0.65


def test_layer_counts_raises_faced_preflop_undecayed():
    ex = Exploit(ExploitParams())
    ex.new_table(3, 0)
    obs = Observation(hole=parse("3c 4d"), board=(), street=0, seat=0, button=2, stacks=[2000] * 3, bets=[0, 10, 20],
                      in_hand=[True] * 3, pot=0, to_call=20, min_raise=40, max_raise=2000, legal=frozenset({F, C, R}),
                      hand_no=0, blinds=(10, 20), history=[])
    ex.observe(obs)
    ex.hand_end(HandResult(0, [0, 0, 0], {}, (), [(0, Action(R, 60)), (1, Action(F)), (2, Action(C))]))
    assert ex.faced_n == [0, 1, 1]


def test_profiler_counts_reraises_of_my_open_by_seat():
    p = Profiler(3)
    p.track_s12 = True
    p.reset(3, 0)
    hist = [(0, Action(R, 60)), (1, Action(F)), (2, Action(R, 180)), (0, Action(F))]
    obs = Observation(hole=parse("3c 4d"), board=(), street=0, seat=0, button=2, stacks=[2000] * 3, bets=[0, 10, 20],
                      in_hand=[True] * 3, pot=0, to_call=20, min_raise=40, max_raise=2000, legal=frozenset({F, C, R}),
                      hand_no=0, blinds=(10, 20), history=[])
    p.observe(obs)
    p.hand_end(HandResult(0, [0, 0, 0], {}, (), hist))
    assert (p.rr_n, p.rr_k, p.rr_by) == (1, 1, [0, 0, 1])


def _digest(dials, table, names=STRONG, rules=None):
    seed = 11 * 1_000_003 + table
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    for b in bots:
        if hasattr(b, "use_cost_model"):
            b.use_cost_model(True)
    bot = ship.make_bot("composite", {**QUIET, "late_us": 1e9, **BATCH8_OFF, **dials}, seed=seed * 64)  # on batch 7's F
    rec = bots[0] = _Recorder(bot)
    play_table(bots, rules or Rules(), seed=seed, mode="model")
    return rec.h.hexdigest(), bot


def test_off_by_default_and_inert_when_the_table_never_reads_strong():
    h0, bot = _digest({}, 0)
    assert bot.core._trust_prof is None and bot.core.base.core.trust is None and bot.core.ex.trust is None
    never = {**ON, "strong_prior": 0.0, "strong_rr": 1.01}  # the gate never opens (the strong route never plays either)
    assert _digest(never, 0)[0] == _digest({"strong_prior": 0.0, "strong_rr": 1.01}, 0)[0]


def test_the_trust_weight_reaches_decisions_and_replays_exactly():
    assert _digest(ON, 5)[0] != _digest({}, 5)[0]  # a table that reads strong (the weight changes few decisions)
    assert _digest(ON, 5)[0] == _digest(ON, 5)[0]


def test_twist_tables_play_as_f():
    from hyperion.drills import variants as V

    bounty = V.get("bounty", seed=7).rules
    for t in range(2):
        h, bot = _digest({**ON, "trust_seat_rr": 1}, t, rules=bounty)
        assert h == _digest({}, t, rules=bounty)[0]
        assert bot.core.base.core.trust is None
