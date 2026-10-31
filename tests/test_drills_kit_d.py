"""Kit D: the MIT-style skeleton, its engine, and the reference adapter."""
import random
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, ActionKind
from hyperion.drills.adapter import KitDAdapter, KitDBot
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills.fakekits import _table
from hyperion.drills.fakekits.kit_d import kit, runner as run_d

REF = Path(__file__).resolve().parents[1] / "hyperion" / "drills" / "reference"


@pytest.fixture(autouse=True)
def cheap_bot(monkeypatch):
    monkeypatch.setenv("HYPERION_DRILL_BOT", "cheap")  # these tests measure the adapter, not hero


def run_ref(submission: str, hands: int = 30, hole_cards: int = 2):
    return run_d.run([sys.executable, str(REF / submission)], hands=hands, seed=3, hole_cards=hole_cards)


# ------------------------------------------------------------------ the runner, end to end over a socket

def test_reference_adapter_passes_runner():
    r = run_ref("kit_d_submission.py")
    assert r.passed, r.summary() + " " + "; ".join(r.notes)
    assert r.hands == 30 and r.decisions >= 30
    assert r.exceptions == 0 and r.illegal == 0


def test_slow_adapter_is_auto_folded():
    r = run_ref("slow_kit_d.py", hands=8)
    assert not r.passed
    assert r.timeouts > 0 and r.exceptions == 0 and r.illegal == 0
    assert r.hands == 8  # the engine survives a slow bot and finishes the hands


def test_three_hole_cards_through_kit_d(tmp_path):
    """Three hole cards reach the bot through H and hands[active]. The 8-card evaluator table is built lazily
    (about 1.4 s on first use), which a pooled game clock cannot absorb: the submission warms it before
    run_bot, as the rubric says to."""
    sub = tmp_path / "sub3.py"
    sub.write_text(
        "from hyperion.core.eval import warm\n"
        "warm(8)  # three hole cards + five on the board: pay for the 8-card tables before the clock starts\n"
        "from hyperion.drills.adapter import KitDBot\n"
        "from hyperion.drills.fakekits.kit_d.kit import parse_args, run_bot\n"
        "if __name__ == '__main__':\n"
        "    run_bot(KitDBot(), parse_args())\n"
    )
    r = run_d.run([sys.executable, str(sub)], hands=10, seed=3, hole_cards=3)
    assert r.passed, r.summary() + " " + "; ".join(r.notes)


def test_bot_that_never_connects_is_reported(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("import sys\nsys.exit(3)\n")
    r = run_d.run([sys.executable, str(bad)], hands=3, seed=1)
    assert not r.passed and r.exceptions == 1 and r.hands == 3
    assert any("before connecting" in n for n in r.notes)


# ------------------------------------------------------------------ the skeleton's replay against the dealer

def _street_of(board_len: int) -> int:
    return {0: 0, 3: 1, 4: 2, 5: 3}[board_len]


class _Checker(kit.Bot):
    """Asserts the replayed RoundState equals the dealer's view at every decision, then acts at random."""

    def __init__(self, engine: run_d.Engine, rng: random.Random):
        self.engine, self.rng = engine, rng
        self.checked = 0
        self.round_total = None
        self.rounds = 0
        self.overs = 0

    def handle_new_round(self, game_state, round_state, active):
        self.rounds += 1
        self.round_total = sum(round_state.stacks) + sum(round_state.pips)
        assert round_state.street == 0 and round_state.board == []
        assert len(round_state.hands[active]) == self.engine.hole_cards
        assert all(h == [] for s, h in enumerate(round_state.hands) if s != active)

    def get_action(self, game_state, rs, active):
        st = self.engine.last_state
        assert st is not None and st["seat"] == active == rs.acting
        assert rs.pips == st["bets"], (rs.pips, st["bets"])
        assert rs.stacks == st["stacks"], (rs.stacks, st["stacks"])
        assert rs.in_hand == st["in_hand"]
        assert rs.button == st["button"] and tuple(rs.blinds) == tuple(st["blinds"])
        assert _street_of(len(rs.board)) == st["street"] and _street_of(rs.street) == st["street"]
        assert rs.board == [run_d.card_str(c) for c in st["board"]]
        assert self.round_total - sum(rs.stacks) - sum(rs.pips) == st["pot"]
        assert game_state.round_num - 1 == st["hand_no"]
        legal = {c.__name__ for c in rs.legal_actions()}
        want = {{"fold": "FoldAction", "check": "CheckAction", "call": "CallAction", "raise": "RaiseAction"}[k]
                for k in st["legal"]}
        if "CheckAction" in want:
            want.discard("FoldAction")
        assert legal == want, (legal, want)
        if "RaiseAction" in legal:
            assert rs.raise_bounds() == (st["min_raise"], st["max_raise"])
        self.checked += 1
        # act at random so raises, all-ins and side pots all happen
        classes = {c.__name__: c for c in rs.legal_actions()}
        if "RaiseAction" in classes and self.rng.random() < 0.35:
            lo, hi = rs.raise_bounds()
            return classes["RaiseAction"](self.rng.choice([lo, hi, self.rng.randint(lo, hi)]))
        if "CallAction" in classes and self.rng.random() < 0.7:
            return classes["CallAction"]()
        if "CheckAction" in classes:
            return classes["CheckAction"]()
        return classes["FoldAction"]()

    def handle_round_over(self, game_state, terminal_state, active):
        self.overs += 1
        assert len(terminal_state.deltas) == 8 and sum(terminal_state.deltas) == 0
        assert terminal_state.previous_state is not None


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_skeleton_replay_matches_dealer(seed):
    report = _table.Report()
    engine = run_d.Engine(None, hands=60, seed=seed, budget_ms=1000.0, hole_cards=2, n_players=8, report=report)
    checker = _Checker(engine, random.Random(seed))
    skeleton = kit.Runner(checker, socketfile=None)
    engine.ask = lambda line: skeleton.handle_packet(line.split(" ")) + "\n"
    engine.alive = True
    engine.play()
    assert report.exceptions == 0 and report.illegal == 0, report.summary() + " " + "; ".join(report.notes)
    assert report.hands == 60 and checker.rounds == 60 and checker.overs == 60
    assert checker.checked == report.decisions > 60


# ------------------------------------------------------------------ the adapter's translation

def _state(stacks, pips, button=7, hands=None, blinds=(10, 20)):
    hands = hands or [[] for _ in stacks]
    return kit.RoundState.start(button, stacks, pips, hands, blinds)


def test_round_state_start_follows_the_dead_button():
    # eight live seats, button 6: SB = 7, BB = 0, seat 1 opens
    stacks = [1980, 2000, 2000, 2000, 2000, 2000, 2000, 1990]
    pips = [20, 0, 0, 0, 0, 0, 0, 10]
    rs = _state(stacks, pips, button=6)
    assert rs.acting == 1 and rs.in_hand == [True] * 8
    # heads-up with dead seats: the button is the small blind and acts first preflop
    stacks = [0, 2990, 0, 0, 0, 0, 0, 980]
    pips = [0, 10, 0, 0, 0, 0, 0, 20]
    rs = _state(stacks, pips, button=1)
    assert rs.acting == 1 and rs.in_hand == [False, True, False, False, False, False, False, True]
    # after the button calls, the big blind acts; after a check the street is over and B resets the actor
    rs2 = rs.proceed(kit.CallAction())
    assert rs2.acting == 7 and rs2.pips[1] == 20 and rs2.stacks[1] == 2980
    rs3 = rs2.proceed(kit.CheckAction()).proceed_street(["Ah", "Kd", "2c"])
    assert rs3.street == 3 and rs3.pips == [0] * 8 and rs3.acting == 7 and rs3.previous_state.previous_state is rs2


def test_legal_actions_and_raise_bounds():
    stacks = [1980, 2000, 2000, 2000, 2000, 2000, 2000, 1990]
    pips = [20, 0, 0, 0, 0, 0, 0, 10]
    rs = _state(stacks, pips, button=6)  # seat 1 to act facing the big blind
    assert rs.legal_actions() == {kit.FoldAction, kit.CallAction, kit.RaiseAction}
    assert rs.raise_bounds() == (40, 2000)
    rs = rs.proceed(kit.RaiseAction(60))
    assert rs.pips[1] == 60 and rs.stacks[1] == 1940 and rs.last_raise == 40 and rs.acting == 2
    assert rs.raise_bounds() == (100, 2000)
    for _ in range(5):  # seats 2..6 fold
        rs = rs.proceed(kit.FoldAction())
    assert rs.acting == 7
    rs = rs.proceed(kit.FoldAction()).proceed(kit.CallAction())  # SB folds, BB calls
    rs = rs.proceed_street(["Ah", "Kd", "2c"])
    assert rs.acting == 0 and rs.legal_actions() == {kit.CheckAction, kit.RaiseAction}  # no FoldAction when free
    assert rs.raise_bounds() == (20, 1940)


def test_kit_d_adapter_translates_state():
    stacks = [1980, 2000, 2000, 2000, 2000, 2000, 2000, 1990]
    pips = [20, 0, 0, 0, 0, 0, 0, 10]
    hands = [[] for _ in range(8)]
    hands[1] = ["Ac", "Td"]
    rs = _state(stacks, pips, button=6, hands=hands)
    gs = kit.GameState(0, 0.5, 4)
    ad = KitDAdapter(CheapBot())
    ad.new_round(gs, rs, 1)
    assert ad.started and ad.round_total == 16000
    obs = ad.to_observation((gs, rs, 1))
    assert obs.hole == (48, 33) and obs.seat == 1 and obs.button == 6 and obs.hand_no == 3
    assert obs.street == 0 and obs.pot == 0 and obs.to_call == 20 and obs.bets == pips and obs.stacks == stacks
    assert obs.legal == frozenset({ActionKind.FOLD, ActionKind.CALL, ActionKind.RAISE})
    assert obs.min_raise == 40 and obs.max_raise == 2000 and obs.blinds == (10, 20) and obs.n_players == 8
    a = ad.from_action(Action.raise_to(60), obs, (gs, rs, 1))
    assert isinstance(a, kit.RaiseAction) and a.amount == 60
    assert isinstance(ad.from_action(Action.call(), obs, (gs, rs, 1)), kit.CallAction)
    assert isinstance(ad.native_safe((gs, rs, 1)), kit.FoldAction)
    # postflop, check is free: FOLD is not offered, and a bot that folds anyway is clamped to a check
    rs2 = rs.proceed(kit.CallAction())
    for _ in range(5):
        rs2 = rs2.proceed(kit.FoldAction())
    rs2 = rs2.proceed(kit.FoldAction()).proceed(kit.CheckAction()).proceed_street(["Ah", "Kd", "2c"])
    assert rs2.acting == 0  # the big blind acts first postflop
    rs2 = rs2.proceed(kit.CheckAction())
    assert rs2.acting == 1
    obs2 = ad.to_observation((gs, rs2, 1))
    assert obs2.street == 1 and obs2.pot == 50 and obs2.to_call == 0 and ActionKind.FOLD not in obs2.legal
    assert obs2.board == (50, 45, 0) and obs2.in_hand == [True, True, False, False, False, False, False, False]
    assert isinstance(ad.from_action(Action.fold().clamp(obs2), obs2, (gs, rs2, 1)), kit.CheckAction)
    assert isinstance(ad.native_safe((gs, rs2, 1)), kit.CheckAction)
    # without a new_round call the pot still comes out right, from the previous_state chain
    fresh = KitDAdapter(CheapBot())
    assert fresh.to_observation((gs, rs2, 1)).pot == 50


def test_kit_d_bot_through_the_skeleton_runner():
    """Packets in, replies out, with no socket: G and A are acked, action packets get an action."""
    player = KitDBot(CheapBot())
    sk = kit.Runner(player, socketfile=None)
    g = "T0.09 P1 S1980,2000,2000,2000,2000,2000,2000,1990 I20,0,0,0,0,0,0,10 L10,20 HAc,Ad G6 Zignored"
    assert sk.handle_packet(g.split(" ")) == "K"
    assert sk.round_state.acting == 1 and sk.game_state.round_num == 1
    reply = sk.handle_packet(["T0.089", "P1"])
    assert reply.startswith("R")  # aces: the cheap bot raises
    total = int(reply[1:])
    assert 40 <= total <= 2000
    # our raise comes back as history, everyone else folds, round over
    trail = [f"R{total}"] + ["F"] * 7 + ["A" + ",".join(["-20", "30", "0", "0", "0", "0", "0", "-10"])]
    assert sk.handle_packet(["T0.088", "P1", *trail]) == "K"
    assert sk.game_state.round_num == 2 and sk.game_state.bankroll == 30
    assert sk.handle_packet(["Q"]) is None


def test_encode_action_and_parse_reply():
    assert kit.encode_action(kit.RaiseAction(80)) == "R80" and kit.encode_action(kit.CheckAction()) == "K"
    assert kit.encode_action(kit.CheckAction) == "?"  # the class, not an instance
    assert run_d.parse_reply("R80\n") == ("raise", 80) and run_d.parse_reply("F") == ("fold", 0)
    with pytest.raises(ValueError):
        run_d.parse_reply("?")
    with pytest.raises(ValueError):
        run_d.parse_reply("R 80")


def test_kit_d_blind_schedule_matches_the_dealer():
    """The skeleton's constants are the dealer's first level; later levels arrive in the L clause."""
    t = _table.Table(n_players=8)
    assert (kit.SMALL_BLIND, kit.BIG_BLIND) == t.blinds() and kit.STARTING_STACK == run_d.STACK
