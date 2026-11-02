"""The held-out catalog (hyperion/drills/variants_unseen.py): kept out of the catalog, legal and chip-conserving
under every entry, each entry's own rule, and default play unchanged by the engine hooks it needs."""
import hashlib
import random
import subprocess
import sys
from itertools import combinations
from pathlib import Path

import pytest

from hyperion.core import eval as E
from hyperion.core.eval import evaluate, evaluate_displayed, evaluate_slow
from hyperion.core.types import Action, ActionKind, Rules, parse_cards
from hyperion.drills import variants as V
from hyperion.drills import variants_unseen as U
from hyperion.sim.bestiary import ChartTAG, RandomBot
from hyperion.sim.engine import Table, play_table

ROOT = Path(__file__).resolve().parents[1]
FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
P = parse_cards


@pytest.fixture(autouse=True)
def _no_guard_leak():
    """RiverOfBloodHooks() installs a process-wide guard on core.eval; take it off after every test."""
    yield
    U.remove_eval_guard()


class Bot:
    """Plays a script, then checks or calls; records observations, results and variant prompts."""

    def __init__(self, actions=(), answer=None):
        self.actions = list(actions)
        self.answer = answer
        self.obs, self.results, self.prompts = [], [], []

    def new_table(self, rules, seat, n):
        self.seat = seat

    def act(self, obs):
        self.obs.append(obs)
        if self.actions:
            return self.actions.pop(0)
        return Action.check() if CHECK in obs.legal else Action.call()

    def hand_end(self, result):
        self.results.append(result)

    def variant_decide(self, prompt):
        self.prompts.append(prompt)
        return self.answer


def rules_n(n, **kw):
    return Rules(n_players=n, payouts=tuple(range(n, 0, -1)), **kw)


# ----- held out ---------------------------------------------------------------------------------


def test_held_out_entries_are_reachable_by_name_but_never_in_the_catalog():
    held = set(U.names())
    assert held == {"river_of_blood", "showtime", "high_chicago", "bomb_pot", "unfold"}
    assert not held & set(V.CATALOG) and not held & set(V.PRESETS) and not held & set(V.catalog_names())
    assert not held & {v.name for v in V.catalog()}
    for name in held:
        v = V.get(name)
        assert v.name == name and V.validate(v) == [], V.validate(v)
        assert v.config_patch == {}  # nothing to tune with
        from hyperion.tablegen import rules_from_dict
        assert rules_from_dict(v.rules_json()) == v.rules
        h1, h2 = v.new_hooks(), v.new_hooks()
        assert h1 is not h2 and isinstance(h1, V.VariantHooks)
    assert "HELD OUT" in U.__doc__
    with pytest.raises(KeyError):
        V.get("not_a_variant")


@pytest.mark.parametrize("name", U.names())
def test_runner_plays_each_held_out_entry(name):
    from hyperion.sim.runner import run_tournament

    rep = run_tournament(["tag", "random"], tables=1, seed=3, variant=V.get(name))
    assert rep.hands > 0 and all(b.stats.exceptions == 0 for b in rep.bots.values())


def test_sim_cli_and_matrix_reach_the_held_out_entries():
    out = subprocess.run([sys.executable, "-m", "hyperion.sim", "--variant", "bomb_pot", "--bots", "tag,random",
                          "--tables", "1", "--seed", "2", "--mode", "model"], cwd=ROOT, capture_output=True, text=True,
                         timeout=120, check=True).stdout
    assert "tag" in out and "random" in out
    listing = subprocess.run([sys.executable, "-m", "hyperion.drills.variants_unseen", "--list"], cwd=ROOT,
                             capture_output=True, text=True, timeout=60, check=True).stdout
    assert all(n in listing for n in U.names())
    help_text = subprocess.run([sys.executable, str(ROOT / "tools" / "variant_matrix.py"), "--help"], cwd=ROOT,
                               capture_output=True, text=True, timeout=60, check=True).stdout
    assert "--unseen" in help_text


# ----- legality and conservation under every entry ----------------------------------------------


class Observer:
    """Checks every observation's invariants (unfold money counted) and every returned action's legality."""

    def __init__(self, inner, total):
        self.inner, self.total, self.n_obs = inner, total, 0

    def new_table(self, rules, seat, n):
        self.inner.new_table(rules, seat, n)

    def act(self, obs):
        side = obs.extras.get("unfold_pot", 0) if obs.extras else 0
        assert sum(obs.stacks) + sum(obs.bets) + obs.pot + side == self.total
        assert 0 <= obs.to_call <= obs.stacks[obs.seat] and obs.in_hand[obs.seat] and obs.stacks[obs.seat] > 0
        assert obs.max_raise <= obs.stacks[obs.seat] + obs.bets[obs.seat]
        if RAISE in obs.legal:
            assert max(obs.bets) < obs.min_raise <= obs.max_raise
        assert len(obs.board) == (0 if obs.street == 0 else obs.street + 2)
        self.n_obs += 1
        a = self.inner.act(obs)
        assert a.kind in obs.legal and (a.kind is not RAISE or obs.min_raise <= a.amount <= obs.max_raise)
        return a

    def hand_end(self, result):
        self.inner.hand_end(result)


@pytest.mark.parametrize("name", U.names())
def test_every_entry_keeps_the_rules_and_conserves_chips(name):
    v = U.get(name)
    total = v.rules.starting_stack * v.rules.n_players
    for seed in range(4):
        bots = [Observer(RandomBot(seed * 10 + s) if s % 2 else ChartTAG(seed * 10 + s), total) for s in range(8)]
        t = Table(bots, v.rules, seed=seed, variant=v.new_hooks())
        while not t.done:
            hs = t.play_hand()
            assert sum(t.stacks) == total and min(t.stacks) >= 0 and sum(hs.deltas) == 0
        assert all(st.exceptions == 0 and st.illegal == 0 for st in t.stats)
        assert all(b.n_obs for b in bots) and sorted(t.places) == sorted(set(t.places))


# ----- default play is unchanged ----------------------------------------------------------------

# sha256 of every hand's deltas, board and actions, and the final points. The first digest covers default Rules, a
# straddle, antes, fixed limit and hi_lo (a hook that draws no card): computed on 519dce1, before the hand-shape hooks
# went into the engine, and again on 27e0cff, before the v-catalog fixes; both engines agree, and every change since must
# keep it. (Until the v-catalog fixes one digest also covered bonus_card and two_boards: 4359fed2...)
DEFAULT_FINGERPRINT = "8253b28f64e88545383eae53c204225f6cde980b3a86b7e9daf4a162fa6f5031"
# bonus_card and two_boards draw extra cards, which now come from the shuffled undealt cards (tests/test_variant_draws.py;
# before, from the near-deck-order tail), and bonus_card's price is dead money (before, a contribution only buyers
# could win back): this digest pins them after both fixes (65125a35... after the first), so later changes are deliberate.
DRAWING_FINGERPRINT = "bfd7c3925ffbe24c159f56401cfe68bbdf11f590c875066da724896a07dc3306"


def _play_digest(cases) -> str:
    h = hashlib.sha256()
    for rules, vname in cases:
        for seed in range(3):
            for rot in (0, 3):
                bots = [RandomBot(seed * 10 + s) if s % 2 else ChartTAG(seed * 10 + s) for s in range(8)]
                hooks = V.get(vname).new_hooks() if vname else None
                t = Table(bots, rules, seed=seed, rotation=rot, mode="model", variant=hooks)
                while not t.done:
                    hs = t.play_hand()
                    h.update(repr((hs.hand_no, hs.deltas, hs.board,
                                   [(s, a.kind.value, a.amount) for s, a in hs.history])).encode())
                h.update(repr((t.points, t.places)).encode())
    return h.hexdigest()


def test_default_play_is_bit_identical_to_the_engine_before_the_hooks():
    cases = [(Rules(), None), (Rules(straddle=2), None), (Rules(ante=5, ante_from_level=1), None),
             (Rules(betting="fixedlimit"), None), (V.get("hi_lo").rules, "hi_lo")]
    assert _play_digest(cases) == DEFAULT_FINGERPRINT


def test_drawing_hooks_play_is_pinned():
    cases = [(V.get("bonus_card").rules, "bonus_card"), (V.get("two_boards").rules, "two_boards")]
    assert _play_digest(cases) == DRAWING_FINGERPRINT


def test_default_hand_results_carry_empty_extras():
    bots = [Bot() for _ in range(3)]
    play_table(bots, rules_n(3, max_hands=3), seed=1)
    assert bots[0].results and all(r.extras == {} for r in bots[0].results)


# ----- river_of_blood ---------------------------------------------------------------------------


def test_evaluate_many_matches_brute_force_on_any_number_of_cards():
    rng = random.Random(11)
    for n in list(range(5, 9)) * 50 + list(range(9, 15)) * 150:
        cards = rng.sample(range(52), n)
        assert U.evaluate_many(cards) == evaluate_slow(cards), cards
    # every category is reached past 8 cards, straight flushes and wheels included
    assert U.evaluate_many(P("Ah 2h 3h 4h 5h Kc Kd Ks 9c")) == evaluate_slow(P("Ah 2h 3h 4h 5h Kc Kd Ks 9c"))
    assert U.evaluate_many(P("As 2d 3c 4h 5s 9c 9d Jh Qc")) == evaluate_slow(P("As 2d 3c 4h 5s 9c 9d Jh Qc"))
    assert U.evaluate_many(P("7c 7d 7h 7s 2c 2d 2h 3c 3d 4c")) == evaluate_slow(P("7c 7d 7h 7s 2c 2d 2h 3c 3d 4c"))


def test_eval_guard_makes_the_bots_nine_card_evaluation_fail_and_comes_off():
    cards = P("Ah Kd 7c 7d 2s 3h 9c Jd Qs")
    U.RiverOfBloodHooks()
    assert U.eval_guard_on()
    assert evaluate(cards[:8]) == evaluate_slow(cards[:8])
    with pytest.raises(U.EvaluatorLimit):
        evaluate(cards)
    U.remove_eval_guard()
    assert not U.eval_guard_on()
    U.RiverOfBloodHooks(guard_bot_eval=False)
    assert not U.eval_guard_on()


class RobRig(U.RiverOfBloodHooks):
    """Fixed holes, a fixed five-card board and a fixed run (dealt in order while the last card is red)."""

    def __init__(self, holes, board, run):
        super().__init__(guard_bot_eval=False)
        self.holes, self.board, self.run = [P(h) for h in holes], list(P(board)), list(P(run))

    def on_deal(self, holes, deck, rng):
        deck[:] = self.run[::-1]
        return [self.holes[s] if holes[s] else () for s in range(len(holes))]

    def on_street(self, street, board, holes, deck, rng, ask=None):
        return tuple(self.board[: len(board)]), holes


def test_a_red_river_deals_run_streets_each_with_a_betting_round_and_the_whole_board_plays():
    # seat 0's flush needs the run's Qh; without it seat 1's trip kings win
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qh 8c 2c")
    bots = [Bot(), Bot()]
    t = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig)
    hs = t.play_hand()
    assert hs.board == P("Kc 7d 3s 9h 4h Qh 8c")  # stops at the black 8c; 2c is never dealt
    assert rig.run_cards == 2
    streets = sorted({o.street for o in bots[1].obs})
    assert streets == [0, 1, 2, 3, 4, 5]
    run_obs = [o for o in bots[1].obs if o.street >= 4]
    assert all(len(o.board) == o.street + 2 and o.bets == [0, 0] and o.min_raise == 20 for o in run_obs)
    assert all(o.seat == 1 for o in run_obs)  # first to act on a run street: the first live seat left of the button
    assert hs.deltas == [20, -20]  # the flush made on street 4 wins


def test_a_black_river_ends_the_board_and_a_fold_stops_the_run():
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4c", "Qh 8c")
    t = Table([Bot(), Bot()], rules_n(2, max_hands=1), seed=0, variant=rig)
    assert len(t.play_hand().board) == 5 and rig.run_cards == 0
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qh 8c")
    bots = [Bot([Action.call(), Action.check(), Action.check(), Action.fold()]),
            Bot([Action.check(), Action.check(), Action.check(), Action.raise_to(40)])]
    hs = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig).play_hand()
    assert len(hs.board) == 5 and rig.run_cards == 0 and hs.deltas == [-20, 20]


def test_all_in_deals_the_whole_run_without_betting():
    rig = RobRig(["Ah Jh", "Kd Ks"], "Kc 7d 3s 9h 4h", "Qd 2h 8s")  # the run's 2h makes seat 0's flush
    bots = [Bot([Action.raise_to(2000)]), Bot([Action.call()])]
    hs = Table(bots, rules_n(2, max_hands=1), seed=0, variant=rig).play_hand()
    assert hs.board == P("Kc 7d 3s 9h 4h Qd 2h 8s") and len(bots[0].obs) == 1 and len(bots[1].obs) == 1
    assert hs.deltas == [2000, -2000]


def test_extra_street_rate_and_board_length_match_the_spec():
    """Spec: P(extra) ~ 0.48-0.52, E[board] ~ 5.9-6.0, a run adds ~1.9 cards. Every hand here reaches the river."""
    lengths = []
    for seed in range(12):
        bots = [Bot() for _ in range(8)]
        t = Table(bots, U.river_of_blood().rules, seed=seed, variant=U.RiverOfBloodHooks(guard_bot_eval=False),
                  stacks=[10 ** 9] * 8)
        while not t.done:
            lengths.append(len(t.play_hand().board))
    n = len(lengths)
    assert n == 12 * 200
    p_extra = sum(1 for x in lengths if x > 5) / n
    mean_len = sum(lengths) / n
    run = [x - 5 for x in lengths if x > 5]
    assert 0.45 < p_extra < 0.55, p_extra
    assert 5.8 < mean_len < 6.1, mean_len
    assert 1.75 < sum(run) / len(run) < 2.1, sum(run) / len(run)


def _completion(hero, suit, trials=8000, seed=5):
    """Spec setup: hero's two suited cards against 7 opponents, a board with exactly two of hero's suit and a red
    river, then the run as the hook deals it. P(five of the suit by the end of the run)."""
    rng = random.Random(seed)
    hook = U.RiverOfBloodHooks(guard_bot_eval=False)
    rest = [c for c in range(52) if c not in hero]
    hits = tot = 0
    while tot < trials:
        d = rest[:]
        rng.shuffle(d)
        board = d[14:19]
        if board[4] & 3 not in U.RED_SUITS or sum(1 for c in board if c & 3 == suit) != 2:
            continue
        tot += 1
        spare = d[19:]
        hook.on_deal([], spare, rng)
        b = tuple(board)
        while (c := hook.next_card(4, b, spare, rng)) is not None:
            b += (c,)
        hits += sum(1 for c in tuple(hero) + b if c & 3 == suit) >= 5
    return hits / tot


def test_flush_draws_on_a_red_river_complete_at_the_spec_rates():
    assert abs(_completion(P("As Ks"), 3) - 0.42) < 0.025  # spade draw: the final run card is black
    assert abs(_completion(P("Ah Kh"), 2) - 0.27) < 0.025  # heart draw


def test_duplicate_rotations_see_the_same_run():
    boards = []
    for rot in (0, 3):
        t = Table([Bot() for _ in range(8)], U.river_of_blood().rules, seed=4, rotation=rot,
                  variant=U.RiverOfBloodHooks(guard_bot_eval=False), stacks=[10 ** 9] * 8)
        boards.append([t.play_hand().board for _ in range(40)])
    assert boards[0] == boards[1] and any(len(b) > 6 for b in boards[0])


# ----- showtime ---------------------------------------------------------------------------------


def test_a_fold_shows_the_folders_cards_to_everyone_after_it_and_at_hand_end():
    bots = [Bot([Action.raise_to(60), Action.raise_to(40)]), Bot([Action.fold()]),
            Bot([Action.call(), Action.check(), Action.fold()])]
    t = Table(bots, rules_n(3, max_hands=1), seed=2, variant=U.ShowtimeHooks())
    hs = t.play_hand()
    h1, h2 = hs.holes[1], hs.holes[2]
    assert bots[0].obs[0].extras == {"revealed": {}, "dead_cards": ()}  # earlier observations keep their snapshot
    first2 = bots[2].obs[0]
    assert first2.street == 0 and first2.extras["revealed"] == {1: h1}
    assert first2.extras["dead_cards"] == tuple(sorted(h1))
    flop0 = [o for o in bots[0].obs if o.street == 1][0]
    assert flop0.extras["revealed"] == {1: h1}
    res = bots[0].results[0]
    assert res.extras["revealed"] == {1: h1, 2: h2} and res.showdown == {}  # the winner of an uncontested pot shows nothing


def test_a_free_fold_is_a_check_and_reveals_nothing():
    bots = [Bot([Action.call()]), Bot([Action.fold()])]  # heads-up: the big blind folds with nothing to call
    hs = Table(bots, rules_n(2, max_hands=1), seed=1, variant=U.ShowtimeHooks()).play_hand()
    assert (1, Action.check()) in hs.history and all(a.kind is not FOLD for _, a in hs.history)
    assert len(hs.board) == 5 and bots[0].results[0].extras["revealed"] == {}


def test_folds_to_the_big_blind_show_seven_hands_and_errors_fold_face_up():
    bots = [Bot([Action.fold()]) for _ in range(8)]
    hs = Table(bots, Rules(max_hands=1), seed=3, variant=U.ShowtimeHooks()).play_hand()
    revealed = bots[2].results[0].extras["revealed"]
    assert sorted(revealed) == [0, 1, 3, 4, 5, 6, 7] and all(revealed[s] == hs.holes[s] for s in revealed)

    class Broken(Bot):
        def act(self, obs):
            raise RuntimeError("boom")

    bots = [Bot([Action.raise_to(60)]), Broken(), Bot([Action.fold()])]
    t = Table(bots, rules_n(3, max_hands=1), seed=3, variant=U.ShowtimeHooks())
    hs = t.play_hand()
    assert t.stats[1].exceptions == 1 and bots[0].results[0].extras["revealed"][1] == hs.holes[1]


# ----- high_chicago -----------------------------------------------------------------------------


class Rig(V.VariantHooks):
    def __init__(self, base, holes, board):
        self.base, self.holes, self.board = base, [P(h) for h in holes], list(P(board))

    def on_deal(self, holes, deck, rng):
        return [self.holes[s] if holes[s] else () for s in range(len(holes))]

    def on_street(self, street, board, holes, deck, rng, ask=None):
        return tuple(self.board[: len(board)]), holes

    def score_splits(self, hole, board, rules):
        return self.base.score_splits(hole, board, rules)

    def score_hand(self, hole, board, rules):
        return self.base.score_hand(hole, board, rules)

    def result_extras(self, hand):
        return self.base.result_extras(hand)


def chicago(holes, board, stacks=None, scripts=(), blinds=((5, 11),)):
    rules = rules_n(len(holes), max_hands=1, blind_levels=blinds)
    bots = [Bot(scripts[s] if s < len(scripts) else ()) for s in range(len(holes))]
    t = Table(bots, rules, seed=0, variant=Rig(U.HighChicagoHooks(), holes, board), stacks=stacks)
    return t.play_hand(), bots


def test_spade_half_floor_and_the_odd_chip_to_the_high_half():
    hs, bots = chicago(["As 2c", "Kd Kh", "7c 8d"], "Qh 9c 5d 3h Jd")  # pot 33: 16 to A-spades, 17 to the kings
    assert hs.deltas == [16 - 11, 17 - 11, -11]
    pots = bots[0].results[0].extras["pots"]
    assert pots == [{"amount": 33, "high_winners": [1], "high_amount": 17, "spade_winner": 0, "spade_amount": 16,
                     "uncontested": False}]


def test_no_hole_spade_scoops_board_spades_never_count_and_a_scoop_with_a_tie():
    hs, _ = chicago(["Ac 2c", "Kd Kh", "7c 8d"], "Qs 9s 5d 3h Js")
    assert hs.deltas == [-11, 22, -11]
    # the board plays a broadway straight for all three: the high half (17) splits 5/5/5 plus two odd chips
    # clockwise from the button (seats 1, 2); the spade half (16) goes to the 2 of spades
    hs, _ = chicago(["2s 3c", "4c 5d", "6c 7d"], "Ah Kd Qc Jd Th")
    assert hs.deltas == [16 + 5 - 11, 6 - 11, 6 - 11]


def test_each_side_pot_has_its_own_spade_winner():
    # seat 0 all-in for 100 with As: half the main pot; the side pot's spade half goes to seat 1's Ks
    hs, bots = chicago(["As 2c", "Ks 3c", "Qd Qh"], "Jh 9c 5d 4h 7d", stacks=[100, 1000, 1000],
                       scripts=[[Action.raise_to(100)], [Action.call(), Action.raise_to(200)], [Action.call()]],
                       blinds=((10, 20),))
    assert [hs.stacks_start[s] + hs.deltas[s] for s in range(3)] == [150, 900, 1050]
    pots = bots[0].results[0].extras["pots"]
    assert [(p["amount"], p["spade_winner"], p["spade_amount"], p["high_winners"]) for p in pots] == [
        (300, 0, 150, [2]), (400, 1, 200, [2])]


def test_an_uncontested_pot_is_not_split():
    hs, bots = chicago(["As 2c", "Kd Kh", "7c 8d"], "Qh 9c 5d 3h Jd",
                       scripts=[[Action.raise_to(60)], [Action.fold()], [Action.fold()]])
    assert hs.deltas == [16, -5, -11] and bots[0].results[0].extras["pots"][0]["uncontested"]


# ----- bomb_pot ---------------------------------------------------------------------------------


def test_every_fifth_hand_is_a_bomb_pot_that_starts_on_the_flop():
    bots = [Bot() for _ in range(8)]
    t = Table(bots, Rules(max_hands=10), seed=1, variant=U.BombPotHooks())
    buttons = [t.play_hand().button for _ in range(10)]
    assert buttons == [(b + i) % 8 for i, b in zip(range(10), [buttons[0]] * 10)]  # the button moves every hand
    by_hand = {}
    for b in bots:
        for o in b.obs:
            by_hand.setdefault(o.hand_no, []).append(o)
    for h in (4, 9):
        first = min(by_hand[h], key=lambda o: (o.street, len(o.history)))
        assert {o.street for o in by_hand[h]} >= {1} and all(o.street >= 1 for o in by_hand[h])
        assert first.history == [] and first.pot == 8 * 40 and first.bets == [0] * 8
        assert first.extras == {"bomb_pot": True, "ante": 40, "blinds_posted": False}
        assert first.seat == (buttons[h] + 1) % 8 and first.min_raise == 20
    for h in (3, 5):
        pre = min((o for o in by_hand[h] if o.street == 0), key=lambda o: len(o.history))
        assert pre.history == [] and pre.extras == {"bomb_pot": False} and sum(pre.bets) == 30
        sb, bb = (buttons[h] + 1) % 8, (buttons[h] + 2) % 8  # the blinds follow the button after a bomb pot
        assert pre.bets[sb] == 10 and pre.bets[bb] == 20


def test_a_short_stack_is_all_in_for_the_ante_and_side_pots_form():
    total = 30 + 1000 + 1000
    for seed in range(6):
        t = Table([Bot() for _ in range(3)], rules_n(3, max_hands=1), seed=seed, variant=U.BombPotHooks(every=1),
                  stacks=[30, 1000, 1000])
        hs = t.play_hand()
        assert hs.contrib[0] == 30 and sum(t.stacks) == total and t.stacks[0] in (0, 90, 45, 30)
    t = Table([Bot() for _ in range(3)], rules_n(3, max_hands=1), seed=0, variant=U.BombPotHooks(every=1),
              stacks=[30, 30, 30])
    hs = t.play_hand()
    assert len(hs.board) == 5 and all(not b.obs for b in t.bots) and sum(t.stacks) == 90


def test_heads_up_bomb_pot():
    bots = [Bot(), Bot()]
    t = Table(bots, rules_n(2, max_hands=2), seed=0, variant=U.BombPotHooks(every=1))
    hs = t.play_hand()
    first = min((o for b in bots for o in b.obs if o.hand_no == 0), key=lambda o: len(o.history))
    assert first.street == 1 and first.pot == 80 and first.seat == (hs.button + 1) % 2


# ----- unfold -----------------------------------------------------------------------------------


def unfold_table(scripts, answers, stacks=None, seed=0, n=6):
    bots = [Bot(scripts[s], answers[s]) for s in range(n)]
    hooks = U.UnfoldHooks()
    t = Table(bots, rules_n(n, max_hands=1), seed=seed, variant=hooks, stacks=stacks)
    return t, t.play_hand(), bots, hooks


# six seats, hand 0: button 0, blinds 1 and 2; preflop order 3, 4, 5, 0, 1, 2
FOLD3 = [[], [], [], [Action.fold()], [Action.fold()], [Action.fold()]]


def test_two_unfolders_play_for_the_unfold_pot_on_the_five_card_board():
    t, hs, bots, hooks = unfold_table(FOLD3, [None, None, None, "unfold", True, None])
    assert sum(t.stacks) == 6 * 2000
    for s in (3, 4, 5):
        assert len(bots[s].prompts) == 1
        p = bots[s].prompts[0]
        assert p["decision"] == "unfold" and p["cost"] == 30 and p["unfold_pot"] == 30 and p["eligible"] == 3
        assert len(p["board"]) == 3 and p["hole"] == hs.holes[s]
    assert not any(bots[s].prompts for s in (0, 1, 2))
    flop = [o for o in bots[0].obs if o.street == 1][0]
    assert flop.extras["unfolders"] == [3, 4] and flop.extras["unfold_status"] == "running"
    assert flop.extras["unfold_pot"] == 90 and flop.stacks[0] == 2000 - 5 - 20
    res = bots[0].results[0].extras["unfold"]
    scores = {s: evaluate_displayed(hs.holes[s] + tuple(hs.runout[:5]), Rules()) for s in (3, 4)}
    best = max(scores.values())
    assert res["winners"] == [s for s in (3, 4) if scores[s] == best] and res["hands"] == {3: hs.holes[3], 4: hs.holes[4]}
    assert hs.deltas[5] == -5 and hs.deltas[3] + hs.deltas[4] == 90 - 70
    assert sorted((hs.deltas[3], hs.deltas[4])) in ([-35, 55], [10, 10])


def test_fewer_than_two_unfolders_or_a_preflop_win_refund_everything():
    t, hs, bots, hooks = unfold_table(FOLD3, [None, None, None, "unfold", None, False])
    assert hooks.status == "refunded" and hs.deltas[3:] == [0, 0, 0] and sum(t.stacks) == 12000
    flop = [o for o in bots[0].obs if o.street == 1][0]
    assert flop.extras["unfold_status"] == "refunded" and flop.extras["unfolders"] == []
    everyone_folds = [[Action.fold()]] * 6
    t, hs, bots, hooks = unfold_table(everyone_folds, [True] * 6)
    assert hooks.status == "refunded" and not any(b.prompts for b in bots)
    assert hs.deltas == [0, -10, 10, 0, 0, 0]


def test_the_unfold_game_is_off_below_four_players_and_a_short_blind_posts_no_ante():
    t, hs, bots, hooks = unfold_table([[Action.fold()], [], []], [True] * 3, n=3)
    assert hooks.status == "off" and bots[0].obs[0].stacks[0] == 2000 and not any(b.prompts for b in bots)
    t, hs, bots, hooks = unfold_table(FOLD3, [None] * 6, stacks=[2000, 2000, 22, 2000, 2000, 2000])
    assert 2 not in hooks.antes and hooks.cost == 25 and sum(t.stacks) == 2000 * 5 + 22


def test_the_board_runs_to_five_when_the_main_hand_ends_on_the_flop_and_unfolders_can_bust():
    scripts = [[], [], [], [Action.fold()], [Action.fold()], [Action.fold()]]
    scripts[0] = [Action.call(), Action.raise_to(100)]
    scripts[1] = [Action.call(), Action.fold()]
    scripts[2] = [Action.check(), Action.fold()]
    t, hs, bots, hooks = unfold_table(scripts, [None, None, None, True, True, None],
                                      stacks=[2000, 2000, 2000, 35, 35, 2000])
    assert hooks.cost == 30 and hooks.unfolders == [3, 4]
    assert len(hs.board) == 5 and bots[0].results[0].board == hs.board  # the main hand stopped on the flop
    assert sum(t.stacks) == 2000 * 4 + 70
    if len(hooks.result["winners"]) == 1:
        loser = 7 - hooks.result["winners"][0]
        assert t.stacks[loser] == 0 and t.places[loser] >= 0  # busted in the unfold game
