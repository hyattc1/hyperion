"""Held-out variants: five twists nobody tunes on.

HELD OUT. These entries are a test set, not a catalog to prepare against. They measure how the shipped bot, and a
bot adapted in a rehearsal, cope with a twist we did not prepare for, which is the likeliest case on the night (the
organisers announce the variant at build start and our 23 catalogued entries are our guesses). A bot, a dial or a
table tuned on any of these stops measuring that, so:

  - they are NOT in hyperion.drills.variants.CATALOG / catalog_names() / PRESETS, so no screen, matrix default,
    drill or climb loop picks them up; they are reachable by name only (`variants.get(NAME)` falls back here,
    `python -m hyperion.sim --variant NAME`, `tools/variant_matrix.py --unseen`);
  - no entry carries a Config patch, and nothing in hyperion/strategy, hybrid or compose may read their extras keys;
  - the climb's protocol (docs/drills/goal-plan.md) measures them only on the judge seeds 30000-30399, once per batch.

The five were written by a fresh agent that knew only the names of our 23 entries (the spec, with handout text and
exact engine rules, is copied into docs/drills/unseen-variants-log.md with what each entry implements):

  river_of_blood  a red river deals another card and another betting round, until a black card (MIT 2023)
  showtime        a folded hand is turned face up for the rest of the hand (PokerStars 2018)
  high_chicago    half of every showdown pot goes to the highest spade in the hole
  bomb_pot        every fifth hand: no blinds, a 2 bb ante from everyone, no preflop betting
  unfold          a side pot for preflop folders, who may buy back in after the flop (PokerStars 2018)

The engine side is the optional hand-shape hooks in hyperion/sim/engine.py (forced_bets, after_forced, next_card,
on_fold, free_fold_checks, settle, result_extras); each is off for every other variant, and default play is
bit-identical with them in (the log records the check). Bots see a variant only through Rules.extras, the
Observation (extras included) and HandResult.extras; unfold's buy-back decision is an `ask` (variant_decide), the
decision channel the catalog already uses. Where an entry is not exactly the spec, its docstring says how it differs.

CLI:  python -m hyperion.drills.variants_unseen --list | --show NAME
"""
from __future__ import annotations

import argparse
import sys
from typing import Callable, Sequence

from hyperion.core import eval as _eval
from hyperion.core.cards import is_identity_order, remap
from hyperion.core.eval import FLUSH5, PRIMES, UNSUITED5, evaluate, evaluate_displayed
from hyperion.core.types import ActionKind, Rules

from .variants import Variant, VariantHooks

RED_SUITS = (1, 2)  # cards are rank*4 + suit, suits c d h s = 0..3: diamonds and hearts are red
SPADE = 3


# ------------------------------------------------------------------------------- a best-five of any number of cards

# the ten straights as rank bitmasks, ace-high first, the wheel (A-2-3-4-5) last
_STRAIGHTS_DESC = tuple(0b1111100000000 >> i for i in range(9)) + (0b1000000001111,)


def _mask_ranks(mask: int) -> list[int]:
    return [r for r in range(13) if mask >> r & 1]


def _best_unsuited_ranks(counts: Sequence[int]) -> list[int]:
    """The five ranks of the best non-flush hand in a rank multiset (any size >= 5)."""
    desc = [r for r in range(12, -1, -1) if counts[r]]
    for r in desc:
        if counts[r] >= 4:
            return [r] * 4 + [next(k for k in desc if k != r)]
    trips = [r for r in desc if counts[r] >= 3]
    if trips:
        t = trips[0]
        pair = next((r for r in desc if r != t and counts[r] >= 2), None)
        if pair is not None:
            return [t] * 3 + [pair] * 2
    mask = 0
    for r in desc:
        mask |= 1 << r
    for sm in _STRAIGHTS_DESC:
        if mask & sm == sm:
            return _mask_ranks(sm)
    if trips:
        t = trips[0]
        return [t] * 3 + [r for r in desc if r != t][:2]
    pairs = [r for r in desc if counts[r] >= 2]
    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        return [p1, p1, p2, p2, next(r for r in desc if r != p1 and r != p2)]
    if pairs:
        p = pairs[0]
        return [p, p] + [r for r in desc if r != p][:3]
    return desc[:5]


def evaluate_many(cards: Sequence[int]) -> int:
    """Best five-card strength of any number (>= 5) of canonical cards, on the same scale as core.eval.evaluate.

    Up to 8 cards it is core.eval.evaluate itself. Past 8 that evaluator builds a lookup table per hand size (3 s at
    9 cards, about x3 per extra card, gigabytes by 14), so River of Blood's showdown, with a board of up to 30
    cards, uses this direct path instead: the best flush or straight flush per suit from its rank mask, the best
    non-flush hand from the rank counts, each looked up in the five-card tables. tests compare it with
    core.eval.evaluate_slow."""
    n = len(cards)
    if n <= 8:
        return evaluate(cards)
    counts = [0] * 13
    suit_mask = [0, 0, 0, 0]
    suit_n = [0, 0, 0, 0]
    for c in cards:
        r, s = c >> 2, c & 3
        counts[r] += 1
        suit_mask[s] |= 1 << r
        suit_n[s] += 1
    best = 0
    for s in range(4):
        if suit_n[s] >= 5:
            m = suit_mask[s]
            f = 0
            for sm in _STRAIGHTS_DESC:
                if m & sm == sm:
                    f = FLUSH5[sm]
                    break
            if not f:
                top, k = 0, 0
                for r in range(12, -1, -1):
                    if m >> r & 1:
                        top |= 1 << r
                        k += 1
                        if k == 5:
                            break
                f = FLUSH5[top]
            if f > best:
                best = f
    p = 1
    for r in _best_unsuited_ranks(counts):
        p *= PRIMES[r]
    u = UNSUITED5[p]
    return best if best > u else u


# ------------------------------------------------------------------------------- the bots' evaluator past 8 cards

class EvaluatorLimit(RuntimeError):
    """core.eval.evaluate asked for more than 8 cards while River of Blood's guard is on (see install_eval_guard)."""


_ORIGINAL_BUILD: Callable | None = None
_PARKED: dict = {}  # 9+ card tables some earlier caller built in this process, set aside while the guard is on


def install_eval_guard() -> None:
    """Make core.eval.evaluate raise EvaluatorLimit on 9+ cards instead of building a lookup table for that size.

    Why: the bots evaluate hole + board with core.eval.evaluate, which builds its table for a new hand size lazily,
    inside the call: 3 s at 9 cards, about x3 per extra card, hours and gigabytes by 14 or 15 (River of Blood boards
    reach 12+ cards a few times per thousand river hands). At the tournament's 1 ms per decision that decision is a
    timeout: a check if checking is legal, otherwise a fold. Raising does the same thing here (SafeBot or the engine
    turns the exception into a check or fold, and counts it), and keeps a run from stalling for hours. It is the
    1 ms rule applied to every such decision, a slightly pessimistic model: a bot whose process survived the first
    build would be fast at that size afterwards. Process-wide and idempotent; remove_eval_guard() undoes it.
    Tables for 9+ cards already built in the process are set aside meanwhile, so the guard does not depend on what
    ran before it. The engine's own showdown never needs it (RiverOfBloodHooks.score_hand uses evaluate_many)."""
    global _ORIGINAL_BUILD
    if _ORIGINAL_BUILD is not None:
        return
    _ORIGINAL_BUILD = _eval._build_unsuited
    for k in [k for k in _eval._UNSUITED_N if k > 8]:
        _PARKED[k] = _eval._UNSUITED_N.pop(k)

    def guarded(n: int, _orig=_ORIGINAL_BUILD):
        if n > 8:
            raise EvaluatorLimit(f"core.eval.evaluate on {n} cards: its {n}-card table would be built inside a "
                                 "1 ms decision (seconds to hours): played as a timeout")
        return _orig(n)

    _eval._build_unsuited = guarded


def remove_eval_guard() -> None:
    global _ORIGINAL_BUILD
    if _ORIGINAL_BUILD is not None:
        _eval._build_unsuited = _ORIGINAL_BUILD
        _ORIGINAL_BUILD = None
        _eval._UNSUITED_N.update(_PARKED)
        _PARKED.clear()


def eval_guard_on() -> bool:
    return _ORIGINAL_BUILD is not None


# ------------------------------------------------------------------------------- 1. river_of_blood

class RiverOfBloodHooks(VariantHooks):
    """A red river (diamond or heart) deals one more board card and one more betting round; repeat until a black card.

    Dealing: every hand the undealt cards (`deck`, the hand's own copy) are shuffled with the table's variant rng at
    the deal, and the run is popped from it, so the run depends only on the table seed and the hand (duplicate
    rotations see the same run) and never on how many cards a fold left undealt. Folds end the hand at once
    (the engine stops asking for cards). An all-in hand deals the whole run, with no betting, then shows down.

    Streets: Observation.street is our betting-round index, 0 preflop, 1 flop, 2 turn, 3 river, then 4, 5, ... for
    run cards (the spec's MIT numbering is the board length: street 6 there is street 4 here; len(obs.board) is that
    number). Each run street is a full no-limit round: bets reset, min bet one big blind, first to act the first
    live seat left of the button. Nothing says a street is final (Rules.board_sizes stays (0, 3, 4, 5)).

    Showdown: the best five of the two hole cards plus every board card, by evaluate_many.

    Differs from the spec only in what the bots' own evaluator does past 8 cards (install_eval_guard): with
    guard_bot_eval=False the bots are left to build those tables, which stalls a run for hours."""

    def __init__(self, guard_bot_eval: bool = True) -> None:
        if guard_bot_eval:
            install_eval_guard()
        self.run_cards = 0  # cards dealt past the river this hand

    def on_deal(self, holes, deck, rng):
        rng.shuffle(deck)
        self.run_cards = 0
        return holes

    def next_card(self, street: int, board: tuple[int, ...], deck: list[int], rng) -> int | None:
        if len(board) < 5 or (board[-1] & 3) not in RED_SUITS:
            return None
        if not deck:
            raise RuntimeError("river_of_blood: the deck ran out during a run")
        self.run_cards += 1
        return deck.pop()

    def score_hand(self, hole, board, rules):
        cards = tuple(hole) + tuple(board)
        if not is_identity_order(rules):
            cards = remap(cards, rules)
        return evaluate_many(cards)


def river_of_blood() -> Variant:
    rules = Rules(extras={"variant": "river_of_blood", "run_until_black": True})
    return Variant(
        name="river_of_blood",
        summary="River of Blood Hold'em (MIT 2023): standard no-limit through the river. If the river card is red "
                "(a heart or a diamond) another community card is dealt, followed by another betting round; this "
                "repeats until a black card is dealt, and the black card gets its own betting round too. Showdown: "
                "the best five of your two hole cards plus every board card.",
        rules=rules,
        breaks=(
            "Street 3 is not the last street: on a red river at least one more card and round come, so draws still "
            "have outs (a spade flush draw completes about 42% of the time in the run, a heart one 27%), thin "
            "river value bets and bluffs are early, and geometric sizing over three postflop streets over-commits. "
            "Code indexed by street 0-3 meets 4, 5, ...; an evaluator built for 5-7 (or 8) cards meets 9 to 30. "
            "About half of all boards reaching the river grow, hands inflate, chops are more common."
        ),
        checklist=(
            "Bot: read len(obs.board) and the last card's suit; street >= 3 with a black last card is the last round.",
            "Bot: an evaluator for 7+ board cards (best five from rank counts and suit masks).",
            "Bot: equity sampling deals the run (until black), not a fixed river.",
        ),
        hooks_factory=RiverOfBloodHooks,
        needs_engine=True,
        axis="betting", tables="unsupported",
        tables_note="the generator deals five board cards; no table knows the run",
        playable_note="the bots' core.eval past 8 cards is played as a 1 ms timeout (install_eval_guard)",
    )


# ------------------------------------------------------------------------------- 2. showtime

class ShowtimeHooks(VariantHooks):
    """A fold turns the folder's two hole cards face up for the rest of the hand.

    obs.extras["revealed"] is {seat: hole} of every fold so far this hand and obs.extras["dead_cards"] the sorted
    tuple of those cards; each observation after a fold carries the new map (a fresh dict, so earlier observations
    keep theirs). HandResult.extras["revealed"] has the hand's folded hands; HandResult.showdown the showdown hands,
    as always. A fold with nothing to call is played as a check and reveals nothing (free_fold_checks). The winner
    of an uncontested pot shows nothing. A timeout or an illegal action facing a bet is a fold, so it reveals.

    Differs from the spec: the spec delivers each fold as an event to every bot in the hand, those that already
    folded included. This engine has no events; a bot sees the reveals in its next observation and, if it has
    folded, in HandResult.extras at the hand's end."""

    free_fold_checks = True

    def __init__(self) -> None:
        self.revealed: dict[int, tuple[int, ...]] = {}

    def on_deal(self, holes, deck, rng):
        self.revealed = {}
        return holes

    def on_fold(self, seat: int, hole: tuple[int, ...], board_len: int) -> None:
        self.revealed[seat] = tuple(hole)

    def extras(self, hand) -> dict:
        return {"revealed": dict(self.revealed),
                "dead_cards": tuple(sorted(c for h in self.revealed.values() for c in h))}

    def result_extras(self, hand) -> dict:
        return {"revealed": dict(self.revealed)}


def showtime() -> Variant:
    rules = Rules(extras={"variant": "showtime", "folds_shown": True})
    return Variant(
        name="showtime",
        summary="Showtime Hold'em (PokerStars 2018): whenever a player folds, their two hole cards are turned face "
                "up for everyone and stay visible for the rest of the hand (obs.extras['revealed'], "
                "obs.extras['dead_cards']). A player who wins because everyone else folded does not show.",
        rules=rules,
        breaks=(
            "Dead cards: a late seat can see up to twelve folded cards before acting preflop; equity that samples "
            "from the full deck, and ranges that ignore removed cards, are wrong. Free opponent data: every fold "
            "shows what that seat folds. Our own folds leak our thresholds."
        ),
        checklist=(
            "Bot: remove extras['dead_cards'] from every sampled deck and range.",
            "Bot: per-seat fold thresholds from the revealed hands.",
        ),
        hooks_factory=ShowtimeHooks,
        needs_engine=True,
        axis="information",
        playable_note="fold events reach a bot in its next observation, or at hand end once it has folded",
    )


# ------------------------------------------------------------------------------- 3. high_chicago

def hole_spade(hole: Sequence[int]):
    """Rank of the highest spade among the hole cards (12 = ace), None without one."""
    best = None
    for c in hole:
        if c & 3 == SPADE and (best is None or c >> 2 > best):
            best = c >> 2
    return best


class HighChicagoHooks(VariantHooks):
    """At showdown each pot is split: the high half (P - floor(P/2)) to the best hand, the spade half (floor(P/2))
    to the highest spade in the hole among that pot's eligible players.

    It runs on the engine's split-pot path (score_splits): column 0 is the hand, column 1 the hole spade's rank;
    each pot (main and side) is settled among its own eligible players; the odd chip of the halving goes to the
    high half; a pot where nobody eligible has a hole spade goes whole to the best hand; one player can win both;
    an uncontested pot is never split. HandResult.extras["pots"] reports each pot: its amount, the high winners and
    their share, the spade winner (or None) and its share."""

    def __init__(self) -> None:
        self.rules = Rules()

    def score_splits(self, hole, board, rules) -> list:
        self.rules = rules  # for the per-pot report
        return [evaluate_displayed(tuple(hole) + tuple(board), rules), hole_spade(hole)]

    def score_hand(self, hole, board, rules):
        return evaluate_displayed(tuple(hole) + tuple(board), rules)

    def result_extras(self, hand) -> dict:
        n = len(hand.contrib)
        contrib = hand.contrib
        contenders = [s for s in range(n) if hand.in_hand[s]]
        if len(contenders) == 1:
            return {"pots": [{"amount": sum(contrib), "high_winners": contenders, "high_amount": sum(contrib),
                              "spade_winner": None, "spade_amount": 0, "uncontested": True}]}
        rules = self.rules
        hi = {s: evaluate_displayed(tuple(hand.holes[s]) + tuple(hand.board), rules) for s in contenders}
        sp = {s: hole_spade(hand.holes[s]) for s in contenders}
        pots, prev = [], 0
        for lvl in sorted({contrib[s] for s in contenders}):
            amount = sum((c if c < lvl else lvl) - prev for c in contrib if c > prev)
            eligible = [s for s in contenders if contrib[s] >= lvl]
            best = max(hi[s] for s in eligible)
            spades = [(sp[s], s) for s in eligible if sp[s] is not None]
            spade_winner = max(spades)[1] if spades else None
            spade_amount = amount // 2 if spade_winner is not None else 0
            pots.append({"amount": amount, "high_winners": [s for s in eligible if hi[s] == best],
                         "high_amount": amount - spade_amount, "spade_winner": spade_winner,
                         "spade_amount": spade_amount, "uncontested": False})
            prev = lvl
        return {"pots": [p for p in pots if p["amount"]]}


def high_chicago() -> Variant:
    rules = Rules(extras={"variant": "high_chicago", "split": "high_spade"})
    return Variant(
        name="high_chicago",
        summary="High Chicago Hold'em: at showdown every pot is split in two. Half goes to the best poker hand, the "
                "other half to the player holding the highest spade among their two hole cards (board spades do not "
                "count, the ace of spades is highest). Nobody at showdown with a hole spade: the best hand takes it "
                "all. A pot won because everyone else folded is not split.",
        rules=rules,
        breaks=(
            "The ace of spades in the hole is a lock on half of every pot it reaches showdown in, so every call and "
            "shove with it is chip-positive; a normal bot folds A-spades-7 preflop. K and Q of spades become locks "
            "as the higher spades show up dead. A hand without a spade is capped near half the pot: equity is "
            "0.5 P(win high) + 0.5 P(win spade), and bluffing into a likely spade lock is futile."
        ),
        checklist=(
            "Bot: P(my spade is highest) = C(U-h, 2k) / C(U, 2k) with h unseen higher spades, U unseen cards, k opponents.",
            "Bot: equity = half the high equity plus half the spade race.",
        ),
        hooks_factory=HighChicagoHooks,
        needs_engine=True,
        axis="payoff", tables="unsupported",
        tables_note="the generator scores the high hand only",
    )


# ------------------------------------------------------------------------------- 4. bomb_pot

class BombPotHooks(VariantHooks):
    """Every fifth hand (1-based hand numbers 5, 10, ..., 200: hand_no % 5 == 4 here) is a bomb pot: no blinds,
    every player dealt in antes two big blinds of the current level, no preflop round; the flop comes at once and
    betting from the flop on is normal no-limit, first to act the first live seat left of the button.

    A stack at or under the ante posts all of it and is all-in; the ante is a contribution, so side pots form from
    it. The button moves as on any hand, and the next normal hand's blinds follow the button (no missed blinds).
    Bomb pots count toward the blind levels and the 200-hand cap and run at any table size. With betting closed
    from the start the board is dealt out. Bots are told through obs.extras: {"bomb_pot": True, "ante": chips,
    "blinds_posted": False} on a bomb pot's every decision (the first one on street 1, with an empty history),
    {"bomb_pot": False} otherwise; obs.pot holds the antes; obs.blinds stays the level's (the minimum bet).
    The schedule is public in Rules.extras (bomb_every, bomb_ante_bb)."""

    def __init__(self, every: int = 5, ante_bb: int = 2) -> None:
        self.every = every
        self.ante_bb = ante_bb

    def is_bomb(self, hand_no: int) -> bool:
        return (hand_no + 1) % self.every == 0

    def forced_bets(self, hand_no: int, blinds: tuple[int, int], n_in_hand: int):
        if not self.is_bomb(hand_no):
            return None
        return {"ante": self.ante_bb * blinds[1], "blinds": False, "preflop": False}

    def extras(self, hand) -> dict:
        if self.is_bomb(hand.hand_no):
            return {"bomb_pot": True, "ante": self.ante_bb * hand.blinds[1], "blinds_posted": False}
        return {"bomb_pot": False}


def bomb_pot() -> Variant:
    rules = Rules(extras={"variant": "bomb_pot", "bomb_every": 5, "bomb_ante_bb": 2})
    return Variant(
        name="bomb_pot",
        summary="Bomb pots: every fifth hand (5, 10, ..., 200) has no blinds; everyone posts an ante of two big "
                "blinds and there is no preflop betting. The flop is dealt straight away with everyone in, and "
                "betting from the flop on is normal no-limit. obs.extras['bomb_pot'] says which hands.",
        rules=rules,
        breaks=(
            "A hand that starts on the flop: per-hand state reset on street 0 never resets, preflop ranges and "
            "the preflop aggressor do not exist, and up to eight random hands see the flop for a 16 bb pot, so "
            "top pair is often beaten. The ante puts short stacks all-in every fifth hand on a public schedule."
        ),
        checklist=(
            "Bot: detect a new hand by hand_no, never by street 0.",
            "Bot: on extras['bomb_pot'], flop thresholds against N random hands; no c-bet logic.",
        ),
        hooks_factory=BombPotHooks,
        needs_engine=True,
        axis="betting",
    )


# ------------------------------------------------------------------------------- 5. unfold

def _says_unfold(ans) -> bool:
    return ans is True or (isinstance(ans, str) and ans.strip().lower() == "unfold")


class UnfoldHooks(VariantHooks):
    """A second game for the players who fold preflop, on hands with at least four players dealt in.

    Antes: after the blinds every player dealt in posts ceil(bb / 4) (5 at 10/20) into a separate unfold pot held
    here, outside the main pot (never a bet, a call or a side-pot contribution); a stack smaller than the ante after
    its blind posts nothing and cannot unfold. Main pot won preflop: every ante is refunded, no unfold phase.
    Unfold phase, right after the flop is dealt and before flop betting: each preflop folder who posted the ante and
    has at least the cost behind (cost = the total of antes posted, fixed first) is asked once through `ask`
    (the bot's variant_decide) with {"decision": "unfold", "hole", "board" (the flop), "cost", "unfold_pot",
    "eligible" (how many are asked)}; True or "unfold" unfolds, anything else (None, no method, an error, a strict
    timeout) passes. Nobody's answer is shown to another before all have answered. Fewer than two unfold: the
    game ends for the hand and every ante is refunded, paid back at hand end (see _refund). Two or more: they pay
    the cost into the unfold pot and the unfolded seats are announced (obs.extras["unfolders"]) before flop
    betting. Unfolded players never act again in the main hand (they folded). At hand end the board is run to five
    if the main hand stopped early, and the best hand among the unfolders takes the whole unfold pot (ties split,
    odd chips clockwise from the button). Unfold money comes from stacks, so a player can bust in the unfold game.

    Told to bots: obs.extras {"unfold_active", "unfold_ante", "unfold_pot", "unfold_cost", "unfold_status"
    ("pending", "running", "refunded", "off"), "unfolders"}; HandResult.extras["unfold"] the phase and its showdown
    (unfolders' hands, winners, amounts). obs.pot and the main pot never include unfold money.

    Differs from the spec: the spec's new decision type (UnfoldAction / PassAction delivered to a folded seat) is
    the engine's existing variant decision (`ask` -> variant_decide), outside the betting loop; a bot without
    variant_decide passes, as the spec's timeout does. The decisions are asked one seat at a time, but none sees
    another's answer, so they are simultaneous in effect. A refund is paid at hand end rather than at the flop
    (the final chips are the same; a stack all-in preflop stays all-in instead of getting its ante back to bet)."""

    MIN_PLAYERS = 4

    def __init__(self, min_players: int = MIN_PLAYERS) -> None:
        self.min_players = min_players
        self._reset(())

    def _reset(self, holes) -> None:
        self.table = None
        self.hand = None
        self.active = sum(1 for h in holes if h) >= self.min_players
        self.ante = 0
        self.antes: dict[int, int] = {}
        self.cost = 0
        self.pot = 0
        self.status = "pending" if self.active else "off"
        self.eligible: list[int] = []
        self.unfolders: list[int] = []
        self.result: dict = {}
        self.refund_due = False

    def on_deal(self, holes, deck, rng):
        self._reset(holes)
        return holes

    def after_forced(self, table, hand) -> None:
        self.table, self.hand = table, hand
        if not self.active:
            return
        self.ante = ante = -(-hand.blinds[1] // 4)
        stacks = table.stacks
        for s in range(len(stacks)):
            if hand.in_hand[s] and stacks[s] >= ante:
                stacks[s] -= ante
                self.antes[s] = ante
        self.pot = sum(self.antes.values())

    def _refund(self) -> None:
        """The antes go back at hand end (settle), not mid-hand: an ante returned at the flop would give a player
        who was all-in preflop chips to bet again, and a raiser whose excess nobody covered could then fold it away."""
        self.status = "refunded"
        self.refund_due = True

    def on_street(self, street, board, holes, deck, rng, ask=None):
        if street != 1 or self.status != "pending" or self.table is None:
            return board, holes
        hand, stacks = self.hand, self.table.stacks
        self.cost = cost = sum(self.antes.values())
        folded = {s for s, a in hand.history if a.kind is ActionKind.FOLD}  # only preflop has been played
        self.eligible = [s for s in sorted(folded) if s in self.antes and stacks[s] >= cost]
        chosen = []
        for s in self.eligible:
            ans = None
            if ask is not None:
                try:
                    ans = ask(s, {"decision": "unfold", "hole": tuple(hand.holes[s]), "board": tuple(board),
                                  "cost": cost, "unfold_pot": self.pot, "eligible": len(self.eligible)})
                except Exception:  # noqa: BLE001 - a broken answer is a pass
                    ans = None
            if _says_unfold(ans):
                chosen.append(s)
        if len(chosen) < 2:
            self._refund()
            return board, holes
        for s in chosen:
            stacks[s] -= cost
        self.pot += cost * len(chosen)
        self.unfolders = chosen
        self.status = "running"
        return board, holes

    def settle(self, table, hand) -> None:
        if self.status == "pending":  # the main pot was won preflop: no unfold phase
            self._refund()
        if self.refund_due:
            for s, a in self.antes.items():
                table.stacks[s] += a
            self.pot = 0
            self.refund_due = False
            return
        if self.status != "running":
            return
        board = tuple(hand.runout[:5])
        hand.board = board  # the board is run to five for the unfold showdown even if the main hand stopped early
        rules = table.rules
        scores = {s: evaluate_displayed(tuple(hand.holes[s]) + board, rules) for s in self.unfolders}
        best = max(scores.values())
        winners = [s for s in self.unfolders if scores[s] == best]
        n = len(table.stacks)
        share, odd = divmod(self.pot, len(winners))
        paid = {s: share for s in winners}
        for s in ((hand.button + 1 + i) % n for i in range(n)):
            if odd and s in paid:
                paid[s] += 1
                odd -= 1
        for s, amt in paid.items():
            table.stacks[s] += amt
        self.result = {"hands": {s: tuple(hand.holes[s]) for s in self.unfolders}, "winners": winners,
                       "paid": paid, "board": board}
        self.pot = 0

    def extras(self, hand) -> dict:
        return {"unfold_active": self.active, "unfold_ante": self.ante, "unfold_pot": self.pot,
                "unfold_cost": self.cost, "unfold_status": self.status, "unfolders": list(self.unfolders)}

    def result_extras(self, hand) -> dict:
        out = {"active": self.active, "status": self.status, "ante": self.ante, "antes": dict(self.antes),
               "cost": self.cost, "eligible": list(self.eligible), "unfolders": list(self.unfolders)}
        out.update(self.result)
        return {"unfold": out}


def unfold() -> Variant:
    rules = Rules(extras={"variant": "unfold", "unfold_ante_bb": 0.25, "unfold_min_players": 4})
    return Variant(
        name="unfold",
        summary="Unfold Hold'em (PokerStars 2018): before each hand everyone posts a quarter-big-blind unfold ante "
                "into a separate pot. After the flop every player who folded preflop decides, without seeing the "
                "others, whether to unfold by paying the size of the unfold pot (variant_decide, decision "
                "'unfold'). The main hand plays on as normal; the unfold pot goes to the best hand among the "
                "unfolded players on the five-card board. Fewer than two unfold, or the main pot is won preflop: "
                "all unfold money is refunded. Off with fewer than four players dealt in.",
        rules=rules,
        breaks=(
            "A decision after folding: most bots are never asked (no variant_decide) and pass, which is safe but "
            "bleeds the ante whenever two others unfold. The unfold pot holds every ante, so with k unfolders and "
            "equal equity unfolding returns C/k on a cost of C; the other unfolders are folders who liked the "
            "flop. Main-pot players can read the announced unfolders as holding flop-connected cards."
        ),
        checklist=(
            "Bot: variant_decide for {'decision': 'unfold'}: unfold above a flop-strength threshold against folders' ranges.",
            "Bot: remove likely unfolder cards from main-pot equity.",
        ),
        hooks_factory=UnfoldHooks,
        needs_engine=True,
        axis="payoff",
        playable_note="the buy-back is a variant_decide ask, not a new action kind",
    )


# ------------------------------------------------------------------------------- the held-out catalog

HELD_OUT: dict[str, Callable[[], Variant]] = {
    "river_of_blood": river_of_blood,
    "showtime": showtime,
    "high_chicago": high_chicago,
    "bomb_pot": bomb_pot,
    "unfold": unfold,
}


def names() -> list[str]:
    return list(HELD_OUT)


def get(name: str, seed: int = 0) -> Variant:
    if name not in HELD_OUT:
        raise KeyError(f"unknown held-out variant {name!r}; known: {', '.join(HELD_OUT)}")
    return HELD_OUT[name]()


def catalog() -> list[Variant]:
    return [get(n) for n in HELD_OUT]


def main(argv: Sequence[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.drills.variants_unseen",
                                description="Held-out variants (a test set: never tune on them).")
    p.add_argument("--list", action="store_true")
    p.add_argument("--show", metavar="NAME")
    a = p.parse_args(argv)
    if a.list:
        for v in catalog():
            print(f"{v.name:<16} {v.axis:<12} {v.summary.split('. ')[0]}")
        return 0
    if a.show:
        v = get(a.show)
        print(f"{v.name}  [{v.axis}]  HELD OUT\n\n{v.summary}\n\nWhat breaks: {v.breaks}")
        if v.playable_note:
            print(f"\nNote: {v.playable_note}")
        return 0
    p.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
