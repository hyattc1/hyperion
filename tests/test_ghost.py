"""Ghost Hold'em as a variant file (hyperion/drills/ghost_example.py): chips kept, the Haunt paid to the next hand's
main-pot winner, the Ghost never ending a table, and chip-count places at the hand cap."""
from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.drills.ghost_example import GhostHooks, ghost_rules
from hyperion.sim.bestiary import RandomBot
from hyperion.sim.engine import Table
from tests.sim_helpers import Auditor, Scripted

FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE


class RiggedGhost(GhostHooks):
    """Fixed holes, Ghost and board per hand (a list of (holes, ghost, board) strings)."""

    def __init__(self, script):
        super().__init__()
        self.script = script
        self.k = -1

    def on_deal(self, holes, deck, rng):
        super().on_deal(holes, deck, rng)
        self.k += 1
        hs, gh, _ = self.script[min(self.k, len(self.script) - 1)]
        self.ghost = tuple(parse_cards(gh))
        return [tuple(parse_cards(h)) if holes[s] else () for s, h in enumerate(hs)]

    def on_street(self, street, board, holes, deck, rng, ask=None):
        full = tuple(parse_cards(self.script[min(self.k, len(self.script) - 1)][2]))
        return full[:len(board)], holes


class Plan:
    """Per hand number, a list of actions to play in order; then check, else fold. Records observations."""

    def __init__(self, plan):
        self.plan = {k: list(v) for k, v in plan.items()}
        self.obs = []

    def new_table(self, rules, seat, n):
        pass

    def act(self, obs):
        self.obs.append(obs)
        todo = self.plan.get(obs.hand_no)
        a = todo.pop(0) if todo else (Action.check() if CHECK in obs.legal else Action.fold())
        if a.kind is CHECK and CHECK not in obs.legal:
            a = Action.call()
        if a.kind is RAISE and RAISE not in obs.legal:
            a = Action.call()
        return a

    def hand_end(self, result):
        pass


def test_file_variant_registers_and_keeps_every_chip():
    v = V.get("hyperion/drills/ghost_example.py:variant")
    assert v.name == "ghost" and V.get("ghost").rules.extras["cap_places"] == "chips"
    total = 8 * 2000
    haunts = 0
    for seed in range(4):
        hooks = v.new_hooks()
        bots = [Auditor(RandomBot(seed * 10 + s), total) for s in range(8)]  # obs: stacks + bets + pot (Haunt in it)
        t = Table(bots, v.rules, seed=seed, variant=hooks)
        while not t.done:
            t.play_hand()
            assert sum(t.stacks) + hooks.carry == total  # the Haunt is held for the next hand, never lost or made
            assert min(t.stacks) >= 0
        haunts += hooks.stats["haunts"]
    assert haunts > 0


def test_a_haunted_pot_goes_to_the_next_main_pot_winner_by_fold():
    # hand 0 (kit F's example): AK v QJ checked down, the Ghost's trip deuces beat ace high: the 40-chip pot haunts.
    # hand 1: seat 1 raises, seat 0 folds: seat 1 takes the blinds and the Haunt.
    script = [(["AhKd", "QcJs"], "2c2d", "2h7s9dTc3s"), (["7c2s", "AsAd"], "KhKs", "4c5c6dJhQh")]
    hooks = RiggedGhost(script)
    b0 = Plan({0: [Action.call(), Action.check(), Action.check(), Action.check()], 1: [Action.fold()]})
    b1 = Plan({0: [Action.check()] * 4, 1: [Action.raise_to(60)]})
    t = Table([b0, b1], ghost_rules(), seed=3, variant=hooks)
    t.play_hand()
    assert t.stacks == [1980, 1980] and hooks.carry == 40
    assert hooks.last["pots"] == [(40, ())] and hooks.last["haunted"] == 40
    hs = t.play_hand()
    first = (b0.obs + b1.obs)[-1]
    assert first.hand_no == 1 and first.pot == 40 and first.extras["haunt"] == 40  # the Haunt is in obs.pot
    assert t.stacks == [1980 - 20, 1980 + 20 + 40] and hooks.carry == 0  # seat 0 was the big blind
    assert hs.deltas == [-20, 60]


def test_the_haunt_rides_in_the_main_pot_at_a_showdown_and_can_haunt_again():
    script = [(["AhKd", "QcJs"], "2c2d", "2h7s9dTc3s"),  # trip deuces beat ace high: 40 haunts
              (["AhKd", "QcJs"], "3c3d", "2h7s9dTc4s"),  # a pair of threes beats ace high: 40 + the Haunt's 40
              (["AhAd", "QcJs"], "3c4d", "2h7s9dTc5s")]  # aces beat the Ghost's ten high: 40 + 80 to seat 0
    hooks = RiggedGhost(script)
    sb_down = [Action.call(), Action.check(), Action.check(), Action.check()]
    b0 = Plan({0: list(sb_down), 1: [Action.check()] * 4, 2: list(sb_down)})
    b1 = Plan({0: [Action.check()] * 4, 1: list(sb_down), 2: [Action.check()] * 4})
    t = Table([b0, b1], ghost_rules(), seed=3, variant=hooks)
    t.play_hand()
    t.play_hand()
    assert hooks.carry == 80 and t.stacks == [1960, 1960]
    t.play_hand()
    assert hooks.last["pots"] == [(120, (0,))] and hooks.carry == 0
    assert t.stacks == [1960 - 20 + 120, 1960 - 20]


def test_the_ghost_never_ends_a_table():
    # both all-in for the same stack and the Ghost's quad aces beat both: haunting would leave nobody with chips, so
    # the pot is paid as normal (seat 1's aces and kings)
    script = [(["7c2s", "Kh3h"], "AsAd", "AhAcKdQs9h")]
    hooks = RiggedGhost(script)
    t = Table([Scripted([Action.raise_to(1000)]), Scripted([Action.call()])], ghost_rules(), seed=1, variant=hooks,
              stacks=[1000, 1000])
    t.play_hand()
    assert hooks.carry == 0 and t.stacks == [0, 2000] and t.done
    assert t.points == [11.0, 16.0]


def test_each_side_pot_meets_the_ghost_on_its_own():
    # seat 2 (all-in for 100) holds a set and beats the Ghost's aces: it wins the main pot; seats 0 and 1 (kings,
    # queens) lose the side pot to the Ghost
    script = [(["KcKs", "QcQd", "5c5s"], "AhAs", "8h2s5dJc3h")]
    hooks = RiggedGhost(script)
    b0 = Plan({0: [Action.raise_to(500), Action.check(), Action.check(), Action.check()]})
    b1 = Plan({0: [Action.call(), Action.check(), Action.check(), Action.check()]})
    b2 = Plan({0: [Action.call()]})
    t = Table([b0, b1, b2], ghost_rules(), seed=2, variant=hooks, stacks=[2000, 2000, 100])
    t.play_hand()
    assert hooks.last["pots"] == [(300, (2,)), (800, ())]
    assert t.stacks == [1500, 1500, 300] and hooks.carry == 800


def test_cap_places_by_chips_share_ties():
    rules = Rules(payouts=(16, 11, 8, 6, 4, 2, 1, 0), extras={"cap_places": "chips"})
    t = Table([Scripted([]) for _ in range(4)], rules, seed=0, stacks=[500, 300, 300, 100])
    t._place_by_chips([0, 1, 2, 3])
    assert t.points == [16.0, 9.5, 9.5, 6.0] and t.places == [0, 1, 1, 3]
