"""The mirror fields (backlog S9): copies of F (`f_copy`, the composite at SHIP_DIALS) at a table of strong general bots.
Several copies of one bot must play as independent players: each its own instance, its own seat seed, no state shared
through a module, so one copy's play is what it would be alone with the same observations."""
import copy

from hyperion.compose import bot as CB
from hyperion.core.types import Action
from hyperion.sim import bestiary as B
from hyperion.sim import runner as R
from hyperion.sim.field import night as N

MODEL_HYBRID = {"panic_after": 10 ** 9, "soft_us": 1e6, "mc_budget_us": 1e9, "mc_hard_us": 1e9}
MODEL_HERO = {"panic_after": 10 ** 9}


def _model(monkeypatch):
    monkeypatch.setattr(B, "HYBRID_CONFIG", dict(MODEL_HYBRID))


def test_mirror_fields_seat_copies_of_f_with_the_strong_bots():
    assert B.REGISTRY["f_copy"] is B.ShipCopy
    assert B.field_names("mirror") == ["hero", "f_copy", "f_copy", "f_copy", "rival2", "elite1", "elite2", "hybrid3_x"]
    assert B.field_names("mirror_night")[:5] == ["hero", "f_copy", "f_copy", "elite1", "elite2"]
    assert B.field_names("mirror_night")[5:] == ["elite_rest.1", "elite_rest.2", "elite_rest.3"]
    assert B.field_names("mirror@hybrid_x")[0] == "hybrid_x"
    for name, pool in N.POOLS.items():
        assert "f_copy" not in {b for _, _, ms in pool.groups for b, _ in ms}, name
    for members in B.FIELDS.values():  # never beside a judge
        if "f_copy" in members:
            assert not {"rival4", "rival5", "elite3"} & set(members)


def test_a_copy_is_f_as_it_ships(monkeypatch):
    _model(monkeypatch)
    b = B.make_bot("f_copy", seed=11)
    route, kw = CB.parse_dials(dict(CB.SHIP_DIALS))
    f = CB.make_bot(route, seed=11, **CB.sim_kwargs(kw))
    assert b.impl.core.cfg.route == f.core.cfg.route
    assert b.impl.core.cfg.light and b.impl.core.cfg.late_us == 1e9 and b.impl.core.cfg.panic_after == 10 ** 9


def test_mirror_plays_legally_and_replays_exactly_in_model_mode(monkeypatch):
    _model(monkeypatch)
    names = B.field_names("mirror")
    a = R.run_tournament(names, 1, seed=1, rotate=True, mode="model", hero_config=dict(MODEL_HERO), table_offset=9100)
    b = R.run_tournament(names, 1, seed=1, rotate=True, mode="model", hero_config=dict(MODEL_HERO), table_offset=9100)
    for nm, rep in a.bots.items():
        assert rep.stats.exceptions == 0 and rep.stats.illegal == 0 and rep.stats.safe_err == 0, nm
        assert rep.samples == b.bots[nm].samples, nm
    assert a.bots["f_copy"].seats == 3 * 8
    # the copies' seats merge in the report (their mean); points still sum to 36 a table seat by seat
    total = sum(sum(r.samples) / len(r.samples) * r.seats / 8 for r in a.bots.values())
    assert abs(total - 36.0) < 1e-6


class _Tape:
    """Records one seat's calls (with its seed) and passes them through."""

    def __init__(self, inner, seed, tapes):
        self.inner, self.seed, self.ev = inner, seed, []
        tapes.append(self)

    def new_table(self, rules, seat, n_players):
        self.ev.append(("table", (rules, seat, n_players)))
        self.inner.new_table(rules, seat, n_players)

    def act(self, obs):
        o = copy.deepcopy(obs)
        a = self.inner.act(obs)
        self.ev.append(("act", o, (a.kind, a.amount)))
        return a

    def hand_end(self, result):
        self.ev.append(("end", copy.deepcopy(result)))
        self.inner.hand_end(result)


def test_copies_are_independent_players(monkeypatch):
    """Three copies at one table: each replayed alone, in a fresh instance with its seed and the observations it saw,
    plays every decision as it did at the table, so no copy's play depended on another's state."""
    _model(monkeypatch)
    tapes: list = []
    orig = R.make_bot

    def build(nm, seed=None):
        b = orig(nm, seed=seed)
        return _Tape(b, seed, tapes) if nm == "f_copy" and seed is not None else b

    monkeypatch.setattr(R, "make_bot", build)
    R.run_tournament(B.field_names("mirror"), 1, seed=3, rotate=False, mode="model", hero_config=dict(MODEL_HERO),
                     table_offset=9200)
    monkeypatch.setattr(R, "make_bot", orig)
    assert len(tapes) == 3 and len({t.seed for t in tapes}) == 3
    assert all(sum(e[0] == "act" for e in t.ev) > 20 for t in tapes)
    for t in reversed(tapes):  # in another order than they were built
        b = B.make_bot("f_copy", seed=t.seed)
        for e in t.ev:
            if e[0] == "table":
                b.new_table(*e[1])
            elif e[0] == "act":
                a = b.act(copy.deepcopy(e[1]))
                assert isinstance(a, Action) and (a.kind, a.amount) == e[2]
            else:
                b.hand_end(copy.deepcopy(e[1]))
