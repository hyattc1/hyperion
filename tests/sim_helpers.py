"""Bots and checks shared by the simulator tests."""
from hyperion.core.types import Action, ActionKind, Observation

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


def check_observation(obs: Observation, total_chips: int) -> None:
    """Invariants every Observation the engine hands out must satisfy."""
    assert sum(obs.stacks) + sum(obs.bets) + obs.pot == total_chips
    assert all(s >= 0 for s in obs.stacks) and all(b >= 0 for b in obs.bets)
    assert obs.in_hand[obs.seat]
    assert obs.stacks[obs.seat] > 0
    assert FOLD in obs.legal
    assert (CHECK in obs.legal) == (obs.to_call == 0)
    assert (CALL in obs.legal) == (obs.to_call > 0)
    assert 0 <= obs.to_call <= obs.stacks[obs.seat]
    assert obs.max_raise == obs.stacks[obs.seat] + obs.bets[obs.seat]
    if RAISE in obs.legal:
        assert obs.min_raise <= obs.max_raise
        assert obs.min_raise > max(obs.bets)
        others_with_chips = [s for s in range(obs.n_players) if s != obs.seat and obs.in_hand[s] and obs.stacks[s] > 0]
        assert others_with_chips
    assert len(obs.board) >= 0 and len(obs.hole) > 0
    assert obs.street >= 0


class Auditor:
    """Wraps a bot: checks every observation, records what was returned and all legal sets."""

    def __init__(self, inner, total_chips):
        self.inner = inner
        self.total = total_chips
        self.decisions = []  # (obs, action)
        self.holes = {}  # hand_no -> hole

    def new_table(self, rules, seat, n):
        self.seat = seat
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        check_observation(obs, self.total)
        a = self.inner.act(obs)
        assert a.kind in obs.legal, (a, obs.legal)
        if a.kind is RAISE:
            assert obs.min_raise <= a.amount <= obs.max_raise
        self.decisions.append((obs, a))
        self.holes[obs.hand_no] = obs.hole
        return a

    def hand_end(self, result):
        self.inner.hand_end(result)


class Recorder:
    """Checks or folds; keeps every observation so tests can look at cards and buttons."""

    def __init__(self):
        self.obs = []
        self.results = []

    def new_table(self, rules, seat, n):
        self.seat = seat

    def act(self, obs):
        self.obs.append(obs)
        return Action.check() if CHECK in obs.legal else Action.fold()

    def hand_end(self, result):
        self.results.append(result)


class Scripted:
    """Plays a fixed list of actions, then checks/calls. Records observations."""

    def __init__(self, actions):
        self.actions = list(actions)
        self.obs = []

    def new_table(self, rules, seat, n):
        self.seat = seat

    def act(self, obs):
        self.obs.append(obs)
        if self.actions:
            return self.actions.pop(0)
        return Action.check() if CHECK in obs.legal else Action.call()

    def hand_end(self, result):
        pass
