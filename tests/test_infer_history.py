"""The action log rebuilt from the states (hyperion/drills/infer_history.py): every entry it emits happened, in order.

Checked against the engine's own log: on real sim tables (precision 100%, recall 100% at decisions), over random
hands that stress the betting rules (any stacks, antes, straddles, heads-up, three betting structures, folds with
a free check, short all-ins) from every seat, in hand-built spots, and end to end through kit B's adapter.
"""
from __future__ import annotations

import dataclasses
import random
from collections import Counter

from hyperion.core.types import Action, ActionKind, Rules
from hyperion.drills import infer_eval as E
from hyperion.drills.adapter import KitBAdapter, dealer_state
from hyperion.drills.conformance import checked
from hyperion.drills.fakekits.kit_b import kit as kit_b
from hyperion.drills.infer_history import HistoryInference, InferSeat, finals_from_next
from hyperion.sim.engine import Table

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


def rows(hist):
    return [(s, a.kind.value, a.amount if a.kind is RAISE else 0) for s, a in hist]


class RandomBot:
    """Any legal action: folds even when a check is free, min raises, odd sizes and all-ins."""

    def __init__(self, seed: int):
        self.rng = random.Random(seed)

    def new_table(self, *a):
        pass

    def act(self, obs):
        r, legal = self.rng.random(), obs.legal
        if r < 0.12:
            return Action.fold()
        if r < 0.55 or RAISE not in legal:
            return Action.check() if CHECK in legal else Action.call()
        if r < 0.75:
            return Action.raise_to(obs.min_raise)
        if r < 0.9:
            return Action.raise_to(self.rng.randint(obs.min_raise, obs.max_raise))
        return Action.raise_to(obs.max_raise)

    def hand_end(self, result):
        pass


class Script:
    """Plays a fixed list of actions, in order, then checks or folds."""

    def __init__(self, actions):
        self.todo = list(actions)

    def new_table(self, *a):
        pass

    def act(self, obs):
        if self.todo:
            return self.todo.pop(0)
        return Action.check() if CHECK in obs.legal else Action.fold()

    def hand_end(self, result):
        pass


def random_table(rng: random.Random, finals: str):
    n = rng.randint(2, 8)
    level = rng.choice(((10, 20), (25, 50), (100, 200)))
    rules = Rules(n_players=n, blind_levels=(level,), ante=rng.choice((0, 0, 5, level[1] // 4)), ante_from_level=0,
                  straddle=rng.choice((0, 0, 0, 2)), betting=rng.choice(("nolimit", "nolimit", "potlimit", "fixedlimit")))
    stacks = [rng.choice((rng.randint(1, 3 * level[1]), rng.randint(200, 4000))) for _ in range(n)]
    book: dict = {}
    st: Counter = Counter()
    st["ns"], st["bad"] = [], []
    bots = [E._Checker(E._Streets(RandomBot(rng.randrange(1 << 30)), book), st, book, finals, rules) for _ in range(n)]
    return Table(bots, rules, seed=rng.randrange(1 << 30), stacks=stacks, mode="measure"), st


def test_random_hands_from_every_seat_never_emit_a_false_entry():
    rng = random.Random(20261101)
    total: Counter = Counter()
    for i in range(160):
        table, st = random_table(rng, ("next", "none", "stacks", "shown")[i % 4])
        for _ in range(6):
            if table.done:
                break
            table.play_hand()
        assert st["decision", "wrong"] == 0 and st["hand_end", "wrong"] == 0, st["bad"]
        for k, v in st.items():
            if isinstance(k, tuple):
                total[k] += v
    got = sum(total["decision", "got", k] for k in range(4))
    true = sum(total["decision", "true", k] for k in range(4))
    assert true > 3000 and got / true > 0.9, (got, true)  # gaps: folds with a free check before our next turn
    assert total["hand_end", "emitted"] > 1000


def test_real_tables_precision_and_recall():
    for field, bot, final in (("realistic", "hybrid3_x", "next"), ("night", "hero", "shown")):
        st = E.check(field, bot, 2, 7, final)
        assert st["decision", "wrong"] == 0 and st["hand_end", "wrong"] == 0, E.check_report(st)
        for k in range(4):
            if st["decision", "true", k]:
                assert st["decision", "got", k] == st["decision", "true", k], E.check_report(st)
        pre = st["hand_end", "got", 0] / st["hand_end", "true", 0]
        assert pre > 0.6, E.check_report(st)


def _play(scripts, me, hands=1, final="none", rules=None, stacks=None):
    """A table of scripted seats; seat `me` keeps the rebuilt log beside the true one. Returns what it saw."""
    rules = rules or Rules(n_players=len(scripts))
    seen = []

    class Watch:
        def __init__(self, inner):
            self.inner, self.inf, self.pending = inner, HistoryInference(rules), None

        def new_table(self, r, s, n):
            self.inf.new_table(r)

        def act(self, obs):
            bare = dataclasses.replace(obs, history=[], extras={})
            if self.pending is not None:
                res, self.pending = self.pending, None
                seen.append(("end", rows(self.inf.hand_end(final_stacks=finals_from_next(bare, rules),
                                                           hand_no=res.hand_no)), rows(res.history)))
            got = self.inf.observe(bare)
            seen.append(("act", rows(got.history), rows(obs.history), bool(got.extras.get("history_gap"))))
            a = self.inner.act(obs).clamp(obs)
            self.inf.acted(a)
            return a

        def hand_end(self, res):
            if final == "next":
                self.pending = res
                return
            kw = {} if final == "none" else {"deltas": res.deltas, "shown": dict(res.showdown)}
            seen.append(("end", rows(self.inf.hand_end(hand_no=res.hand_no, **kw)), rows(res.history)))

    bots = [Watch(Script(a)) if s == me else Script(a) for s, a in enumerate(scripts)]
    t = Table(bots, rules, seed=1, stacks=stacks, mode="measure")
    for _ in range(hands):
        t.play_hand()
    return seen


def test_preflop_raise_fold_call_then_the_flop():
    # 4 seats, button 0, blinds 1 and 2, UTG 3. UTG raises to 60, we (button) call, SB folds, BB calls; flop: BB
    # checks, UTG bets 100, our turn
    seen = _play([[Action.call()], [Action.fold()], [Action.call(), Action.check()],
                  [Action.raise_to(60), Action.raise_to(100)]], me=0)
    pre, flop = seen[0], seen[1]
    assert pre[1] == pre[2] == [(3, "raise", 60)]
    assert flop[1] == flop[2] == [(3, "raise", 60), (0, "call", 0), (1, "fold", 0), (2, "call", 0), (2, "check", 0),
                                  (3, "raise", 100)]
    assert not flop[3]


def test_a_free_option_out_by_our_next_turn_is_a_gap():
    # UTG limps, we limp, SB completes, BB folds its free option (or checks and folds to the flop bet: the states are
    # the same); flop: SB bets 40, UTG calls, our turn. The log stops before the big blind's action.
    for bb in ([Action.fold()], [Action.check(), Action.fold()]):
        seen = _play([[Action.call()], [Action.call(), Action.raise_to(40)], bb, [Action.call(), Action.call()]], me=0)
        flop = seen[1]
        assert flop[1] == [(3, "call", 0), (0, "call", 0), (1, "call", 0)] and flop[3]
        assert flop[2][:3] == flop[1]


def test_hand_end_folds_after_our_raise_only_when_the_kit_shows_them():
    # we raise on the button, both blinds fold
    scripts = [[Action.raise_to(60)], [Action.fold()], [Action.fold()], [Action.fold()]]
    truth = [(3, "fold", 0), (0, "raise", 60), (1, "fold", 0), (2, "fold", 0)]
    none = _play(scripts, me=0, final="none")
    assert none[-1][1] == truth[:2] and none[-1][2] == truth
    shown = _play(scripts, me=0, final="shown")
    assert shown[-1][1] == truth
    nxt = _play(scripts + [], me=0, final="next", hands=2)
    ends = [x for x in nxt if x[0] == "end"]
    assert ends and ends[0][1] == truth


def test_hand_end_stops_at_a_seat_that_put_more_in():
    # we fold UTG+1; the button raises and the blinds fold: our fold, then the cutoff's... (3 seats after us)
    scripts = [[Action.raise_to(60)], [Action.fold()], [Action.fold()], [Action.call(), Action.fold()]]
    # 4 seats: button 0, SB 1, BB 2, UTG 3 (us): we call 20, button raises, blinds fold, we fold
    seen = _play(scripts, me=3, final="shown")
    end = seen[-1]
    assert end[2] == [(3, "call", 0), (0, "raise", 60), (1, "fold", 0), (2, "fold", 0), (3, "fold", 0)]
    assert end[1] == end[2]  # our fold ends the hand: every action is ours or before it
    scripts = [[Action.raise_to(60), Action.raise_to(100)], [Action.fold()], [Action.call(), Action.fold()],
               [Action.fold()]]
    seen = _play(scripts, me=3, final="shown")
    end = seen[-1]
    assert end[1] == [(3, "fold", 0)] and end[2][0] == (3, "fold", 0)  # the button's raise is not settled: stop


def test_merge_takes_a_kit_log_of_this_street():
    inf = HistoryInference()
    mine = [(3, Action.raise_to(60)), (0, Action.call())]
    street = [(0, Action.call()), (1, Action.fold())]
    assert rows(inf.merge(mine, street)) == [(3, "raise", 60), (0, "call", 0), (1, "fold", 0)]
    assert rows(inf.merge(mine, mine + [(1, Action.fold())])) == rows(mine) + [(1, "fold", 0)]
    assert inf.merge(mine, [(5, Action.fold())]) == mine and inf.conflicts == 1


class Record:
    def __init__(self):
        self.acts, self.ends = [], []

    def new_table(self, *a):
        pass

    def act(self, obs):
        self.acts.append(obs)
        return Action.check() if CHECK in obs.legal else (Action.call() if obs.to_call <= 40 else Action.fold())

    def hand_end(self, result):
        self.ends.append(result)


def test_kit_b_adapter_end_to_end_against_the_engine_log():
    """Engine -> kit B's dict -> KitBAdapter (with only our chip change at hand end) -> the bot: what the bot reads
    is the engine's log, a prefix of it, at every decision; the hand ends arrive one state late with every seat's
    chip change and the folds after our reply."""
    from hyperion.sim import bestiary as B

    names = B.field_names("realistic")
    acts = ends = full = 0
    for t in range(3):
        rec = Record()
        ad = checked(KitBAdapter(rec))
        truth: dict = {}
        me = t % 8

        class Seat:
            def new_table(self, rules, seat, n):
                ad.start(seat, n, rules)

            def act(self, obs):
                st = dealer_state(obs)
                st["legal"] = set(st["legal"])
                reply = ad.decide(kit_b.to_observation(st))
                kind, total = kit_b.parse_decision(reply, st)
                return Action.raise_to(total) if kind == "raise" else Action(ActionKind(kind))

            def hand_end(self, res):
                truth[res.hand_no] = (rows(res.history), list(res.deltas))
                ad.hand_end(res.hand_no, res.deltas[me])

        seen = {}

        class Engine(Table):
            def _ask(self, s, obs):
                if s == me:
                    seen[len(rec.acts)] = rows(obs.history)
                return super()._ask(s, obs)

        bots = [B.make_bot(nm, seed=t * 64 + s) for s, nm in enumerate(names)]
        bots[me] = Seat()
        Engine(bots, Rules(), seed=100 + t, mode="model").play()
        for i, obs in enumerate(rec.acts):
            assert obs.extras.get("history_inferred") and not obs.extras.get("history_from_bets")
            assert rows(obs.history) == seen[i], (i, rows(obs.history), seen[i])
        for res in rec.ends:
            hist, deltas = truth[res.hand_no]
            assert rows(res.history) == hist[: len(res.history)], (rows(res.history), hist)
            full += res.deltas == deltas
        acts, ends = acts + len(rec.acts), ends + len(rec.ends)
        assert ad.conformance.clean, ad.conformance.summary()
        assert ad.inference.gaps == 0
    assert acts > 100 and ends > 100
    assert full > 0.8 * ends  # every seat's chips, one state late (not the hand that ends the table)


def test_conformance_flags_a_state_the_betting_cannot_explain():
    import types

    from hyperion.drills.cheapbot import CheapBot
    from hyperion.drills.fakekits.kit_b import runner as run_b

    class PotIncludesBets(KitBAdapter):
        def to_observation(self, o):
            obs = super().to_observation(o)
            obs.pot += sum(obs.bets)
            return obs

    for adapter, bad in ((KitBAdapter(CheapBot()), False), (PotIncludesBets(CheapBot()), True)):
        a = checked(adapter)
        mod = types.SimpleNamespace(decide=a.decide, on_table_start=lambda i, a=a: a.start(i["seat"], i["players"]),
                                    on_hand_end=lambda i, a=a: a.hand_end(i["hand_id"], i["delta"]))
        run_b.run(mod, hands=60, seed=3)
        summary = a.conformance.summary()
        assert ("history_gap" in a.conformance.counts) is bad, summary
        assert "rebuilt from the states" in summary


def test_infer_seat_matches_the_adapter_path_and_costs_little():
    """InferSeat (the gate's in-sim baseline for --kit-log no) feeds the bot a rebuilt log and a deferred hand end."""
    rec = Record()
    seat = InferSeat(rec)
    from hyperion.sim import bestiary as B

    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=s) for s, nm in enumerate(names)]
    bots[2] = seat
    Table(bots, Rules(), seed=5, mode="model").play()
    assert rec.acts and all(o.extras.get("history_inferred") for o in rec.acts)
    assert sum(len(set(r.deltas) - {0}) > 1 for r in rec.ends) > 0.5 * len(rec.ends)
    st = E.check("realistic", "hero", 1, 3, "next")
    ns = sorted(st["ns"])
    assert ns[len(ns) // 2] < 100_000, ns[len(ns) // 2]  # ~10 us on a quiet host; generous under load


def test_finals_from_next_adds_the_antes_back():
    from tests.strategy_helpers import make_obs

    o = make_obs(seat=3, bets=[10, 20, 0, 0], stacks=[1980, 1970, 1990, 1990], pot=40, hand_no=7)
    assert finals_from_next(o, Rules(n_players=4, ante=10, ante_from_level=0)) == [2000] * 4
    assert finals_from_next(o, Rules(n_players=4)) == [2000] * 4  # the pot alone, split evenly
    flop = dataclasses.replace(o, street=1)
    assert finals_from_next(flop) is None
