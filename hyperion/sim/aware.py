"""Variant-aware opponents for the three likeliest twists: what a decent one-hour team ships after reading the handout.

On the night every team's bot knows the variant, so a field of bots that ignore the twist overstates us. Each entry
gets three bots, built on the bestiary's archetypes (same ranges, sizes and postflop rules) plus the one thing a team
that read the rule would add. They sit in the `<variant>_aware` fields (bestiary FIELDS), never in a night pool:

  toss_or_holdem   three hole cards, one tossed face up after the flop (dead, not community)
    toss_tag       ChartTAG on the Chen-best two of three, a range wider when the third card adds a pair, a suit or a
                   connector to them; tosses the card whose removal leaves the best made hand on the flop, then the
                   most live outs (every face-up toss so far and its own are dead), then high cards
    toss_pushfold  PushFoldBot on the same best two, the same toss
    toss_mc        Monte Carlo equity after the toss against two-card opponents with every face-up toss dead
    toss_rival1    red-team rival 1 (unchanged) with the same toss: the strong team that read the rule
  bounty           MIT 2025: win a pot holding your bounty rank (in hand or on the board) and the house pays 1.5x + 10
    bounty_tag     ChartTAG opening one range wider holding its bounty rank, and with the bounty hit (in hand or on
                   the board) betting half the pot when checked to in a pot of three or fewer: the bounty pays for
                   winning pots, so the lever is fold equity
    bounty_pushfold  PushFoldBot opening one position wider and shoving one depth wider holding its bounty rank, and
                   the same bet when the bounty is hit
    bounty_mc      the Monte Carlo bot 2 Chen points looser holding the rank, and the same bet when it is hit
                   Measured against each bot without its bounty play (paired seat swaps on `realistic` under bounty,
                   seeds 10000-10099 x 8, scratch): calling raises and shoves wider holding the rank cost the push/fold
                   bot -0.06 +- 0.03, continuing with any pair when hit -0.16; the bets +0.04 to +0.09, opens level
  short_deck       36 cards (6 to ace), a flush beats a full house, A-6-7-8-9 is a straight
    short_tag      ChartTAG's ranges re-cut for the 36-card deck (the same share of combos by short-deck preflop
                   equity, opens a fifth wider), hands read with short-deck rankings
    short_pushfold PushFoldBot's ranges re-cut the same way, short-deck rankings postflop
    short_mc       Monte Carlo equity from the 36-card deck with short-deck rankings

The Monte Carlo bots sample 48 runouts against at most three opponents (rng.sample), so they decide in time; they have
no cost model and are never folded for time in model mode. All of them are deterministic for a seed.
"""
from __future__ import annotations

import json
import os
from typing import Optional

from ..core.cards import hole_class
from ..core.eval import category, evaluate
from ..core.types import Action, Observation, Rules
from . import bestiary as _B
from .bestiary import (
    RAISE, ChartTAG, PushFoldBot, RivalBot, _Base, _check_or_fold, _raise_or_call, chen_score, expand_range,
    facing_shove, players_behind, top_pair_or_better, two_card_class,
)

_TABLES = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "tables")


# ----- shared reads ----------------------------------------------------------------------------------------------------


def best_two(hole: tuple[int, ...]) -> tuple[int, int]:
    """Indices of the two cards with the best Chen score (ties: the higher ranks)."""
    best, key = (0, 1), None
    n = len(hole)
    for i in range(n):
        for j in range(i + 1, n):
            pair = (hole[i], hole[j])
            k = (chen_score(pair), max(hole[i] >> 2, hole[j] >> 2), min(hole[i] >> 2, hole[j] >> 2))
            if key is None or k > key:
                best, key = (i, j), k
    return best


def third_bonus(hole: tuple[int, ...], i: int, j: int) -> int:
    """What the cards outside the best two add to them: one each for pairing one, sharing a suit, or connecting
    (within two ranks) with one."""
    a, b = hole[i], hole[j]
    out = 0
    for m, c in enumerate(hole):
        if m in (i, j):
            continue
        r = c >> 2
        if r in (a >> 2, b >> 2):
            out += 1
        if (c & 3) in (a & 3, b & 3):
            out += 1
        if any(0 < abs(r - (x >> 2)) <= 2 for x in (a, b)):
            out += 1
    return out


def live_draw_outs(keep: tuple[int, int], board: tuple[int, ...], gone: set, ranks_live=None) -> int:
    """Live outs to a flush or a straight that uses a kept card: cards not in `gone` (seen or dead). `ranks_live`:
    the ranks in the deck (short deck), else all 13; A-6-7-8-9 counts when the deck has no 2-5."""
    if len(board) < 3 or len(board) >= 5:
        return 0
    live = ranks_live if ranks_live is not None else range(13)
    live_set = set(live)
    cards = keep + board
    draw = 0
    for suit in range(4):
        mine = sum(1 for c in cards if c & 3 == suit)
        if mine == 4 and (keep[0] & 3 == suit or keep[1] & 3 == suit):
            draw = max(draw, sum(1 for r in live if r * 4 + suit not in gone))
    ranks = {c >> 2 for c in cards}
    windows = [set(range(lo, lo + 5)) for lo in range(0, 9)] + [{12, 0, 1, 2, 3}]
    if ranks_live is not None and 0 not in live_set:
        windows = [w for w in windows if w <= live_set] + [{12, 4, 5, 6, 7}]
    kr = {keep[0] >> 2, keep[1] >> 2}
    outs = set()
    for w in windows:
        if len(w & ranks) == 4 and (kr & w):
            outs |= w - ranks
    if outs:
        draw = max(draw, sum(1 for r in outs for su in range(4) if r * 4 + su not in gone))
    return draw


def toss_index(hole: tuple[int, ...], board: tuple[int, ...], dead=()) -> int:
    """toss_or_holdem: index of the card to toss. Keep the two that make the best made hand with the flop (category,
    then strength), then the most live outs (dead = every face-up toss so far plus the card tossed), then high cards."""
    best, key = None, None
    n = len(hole)
    for t in range(n):
        keep = tuple(hole[m] for m in range(n) if m != t)
        if len(keep) != 2:
            continue
        if len(board) >= 3:
            s = evaluate(keep + board)
            cat = category(s)
            gone = set(dead) | set(hole) | set(board)
            draw = live_draw_outs(keep, board, gone)
            k = (cat, s if cat >= 1 else 0, draw, max(c >> 2 for c in keep), min(c >> 2 for c in keep))
        else:
            k = (chen_score(keep), 0, 0, max(c >> 2 for c in keep), min(c >> 2 for c in keep))
        if key is None or k > key:
            best, key = t, k
    return 0 if best is None else best


def _discards(obs_or_prompt_extras: dict, me: int) -> tuple:
    d = (obs_or_prompt_extras or {}).get("discards") or {}
    return tuple(int(c) for s, c in d.items() if c is not None and int(s) != me)


# ----- the TAG and push/fold preflop with a range shift ------------------------------------------------------------


def tag_preflop(bot: ChartTAG, obs: Observation, cls: str, notch: int = 0, early=None, middle=None, late=None,
                wide=None, three_bet=None, call_raise=None, call_notch: int | None = None) -> Action:
    """ChartTAG's preflop for hand class `cls`, its position range shifted `notch` steps wider (negative: tighter) and
    its ranges facing a raise `call_notch` steps (default `notch`); the ranges default to ChartTAG's (`wide` is one
    step past LATE)."""
    cn = notch if call_notch is None else call_notch
    E, M, L = early or bot.EARLY, middle or bot.MIDDLE, late or bot.LATE
    W = wide or (L | _WIDE_EXTRA)
    tiers = (E, M, L, W)
    bb = obs.big_blind
    behind = players_behind(obs)
    t = (0 if behind >= 5 else 1 if behind >= 3 else 2) + notch
    rng_ = tiers[max(0, min(3, t))]
    facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
    tb = three_bet or bot.THREE_BET
    cr = call_raise or bot.CALL_RAISE
    if cn > 0:
        tb = tb | expand_range("JJ AQs")
        cr = cr | M
    if obs.stack_bb <= bot.push_below_bb:
        if cls in (tiers[max(0, min(3, 1 + cn))] if facing_raise else rng_):
            return _raise_or_call(obs, obs.max_raise)
        return _check_or_fold(obs)
    if facing_raise:
        if cls in tb:
            bot.aggressor_hand = obs.hand_no
            target = obs.bets[obs.seat] + obs.to_call * 3
            return _raise_or_call(obs, target if target < obs.my_stack // 2 else obs.max_raise)
        if cls in cr and obs.to_call <= obs.my_stack // 8 and bot.aggressor_hand != obs.hand_no:
            return Action.call()
        return _check_or_fold(obs)
    if cls in rng_ and RAISE in obs.legal:
        bot.aggressor_hand = obs.hand_no
        limpers = sum(1 for s in range(obs.n_players) if obs.in_hand[s] and obs.bets[s] >= bb) - 1
        return _raise_or_call(obs, bot.open_bb * bb + max(0, limpers) * bb)
    return _check_or_fold(obs)


_WIDE_EXTRA = expand_range("A2o+ K5s+ K8o+ Q8s+ Q9o+ J8s+ J9o+ T8s+ T9o 97s+ 86s+ 75s+ 65s 54s")


def pushfold_preflop(bot: PushFoldBot, obs: Observation, cls: str, notch: int = 0, ranges=None,
                     call_notch: int | None = None) -> Action:
    """PushFoldBot's preflop for hand class `cls`; `notch` > 0 opens one position wider and shoves from the next
    shallower depth's (wider) range; `call_notch` > 0 (default `notch`) calls shoves with the short range and 3-bets /
    flats one range wider. `ranges` replaces the class ranges (short deck): a dict with OPEN, THREE_BET, CALL_RAISE,
    PUSH, CALL_SHOVE, CALL_SHOVE_SHORT."""
    cn = notch if call_notch is None else call_notch
    R = ranges or {"OPEN": bot.OPEN, "THREE_BET": bot.THREE_BET, "CALL_RAISE": bot.CALL_RAISE, "PUSH": bot.PUSH,
                   "CALL_SHOVE": bot.CALL_SHOVE, "CALL_SHOVE_SHORT": bot.CALL_SHOVE_SHORT}
    bb = obs.big_blind
    pos = bot._position(obs)
    facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
    shove = facing_shove(obs) or obs.to_call >= obs.my_stack / 3
    if shove and obs.to_call > 0:
        short = obs.stack_bb <= 8 or obs.to_call <= obs.my_stack / 4 or cn > 0
        rng_ = R["CALL_SHOVE_SHORT"] if short else R["CALL_SHOVE"]
        return Action.call() if cls in rng_ else _check_or_fold(obs)
    if obs.stack_bb <= bot.pushfold_bb:
        if facing_raise:
            rng_ = R["CALL_SHOVE_SHORT"] if cn > 0 else R["CALL_SHOVE"]
            return _raise_or_call(obs, obs.max_raise) if cls in rng_ else _check_or_fold(obs)
        caps = (5, 10, 15)
        k = next((i for i, cap in enumerate(caps) if obs.stack_bb <= cap), 2)
        k = max(0, k - notch)
        if cls in R["PUSH"][(caps[k], pos)]:
            bot.aggressor_hand = obs.hand_no
            return _raise_or_call(obs, obs.max_raise)
        return _check_or_fold(obs)
    if facing_raise:
        tb = R["THREE_BET"] | (R["CALL_SHOVE"] if cn > 0 else frozenset())
        if cls in tb:
            bot.aggressor_hand = obs.hand_no
            target = obs.bets[obs.seat] + obs.to_call * 3
            return _raise_or_call(obs, target if target < obs.my_stack // 2 else obs.max_raise)
        cr = R["CALL_RAISE"] | (R["OPEN"]["middle"] if cn > 0 else frozenset())
        if cls in cr and obs.to_call <= obs.my_stack // 10:
            return Action.call()
        return _check_or_fold(obs)
    order = ("early", "middle", "late")
    p = order[min(2, order.index(pos) + max(0, notch))]
    if cls in R["OPEN"][p] and RAISE in obs.legal:
        bot.aggressor_hand = obs.hand_no
        limpers = sum(1 for s in range(obs.n_players) if obs.in_hand[s] and obs.bets[s] >= bb) - 1
        return _raise_or_call(obs, bot.open_bb * bb + max(0, limpers) * bb)
    return _check_or_fold(obs)


def tag_postflop(bot, obs: Observation, strong: bool, big: bool, cbet: bool = True) -> Action:
    """ChartTAG's postflop with the reads given: `strong` continues (top pair or better), `big` raises."""
    bb = obs.big_blind
    if obs.to_call == 0:
        if strong:
            return _raise_or_call(obs, max(bb, obs.total_pot // 2))
        if cbet and obs.street == 1 and bot.aggressor_hand == obs.hand_no and bot.cbet_done_hand != obs.hand_no:
            bot.cbet_done_hand = obs.hand_no
            return _raise_or_call(obs, max(bb, int(obs.total_pot * bot.cbet_frac)))
        return Action.check()
    if strong:
        if big:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
        return Action.call()
    return Action.fold()


def pushfold_postflop(bot: PushFoldBot, obs: Observation, strong: bool, big: bool) -> Action:
    """PushFoldBot's postflop with the reads given."""
    bb = obs.big_blind
    if obs.stack_bb <= bot.pushfold_bb:
        return _raise_or_call(obs, obs.max_raise) if strong else _check_or_fold(obs)
    if obs.to_call == 0:
        if strong:
            return _raise_or_call(obs, obs.bets[obs.seat] + max(bb, (2 * obs.total_pot) // 3))
        if (obs.street == 1 and bot.aggressor_hand == obs.hand_no and bot.cbet_done_hand != obs.hand_no
                and obs.active == 2):
            bot.cbet_done_hand = obs.hand_no
            return _raise_or_call(obs, max(bb, obs.total_pot // 2))
        return Action.check()
    if big:
        return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + obs.total_pot)
    if strong:
        return Action.call()
    return Action.fold()


# ----- toss_or_holdem ----------------------------------------------------------------------------------------------


class _TossMixin:
    def variant_decide(self, prompt: dict):
        if prompt.get("decision") != "discard":
            return None
        hole, board = tuple(prompt.get("hole") or ()), tuple(prompt.get("board") or ())
        if len(hole) != 3:
            return None
        return toss_index(hole, board, _discards(prompt, -1))

    def _pre_class(self, obs: Observation) -> tuple[str, int]:
        if len(obs.hole) < 3:
            return hole_class(obs.hole[:2]), 0
        i, j = best_two(obs.hole)
        return hole_class((obs.hole[i], obs.hole[j])), (1 if third_bonus(obs.hole, i, j) >= 2 else 0)


class TossTAG(_TossMixin, ChartTAG):
    """toss_or_holdem's aware TAG (module doc)."""

    def act(self, obs: Observation) -> Action:
        if obs.street == 0:
            cls, notch = self._pre_class(obs)
            return tag_preflop(self, obs, cls, notch)
        return super().act(obs)


class TossPushFold(_TossMixin, PushFoldBot):
    """toss_or_holdem's aware push/fold bot (module doc)."""

    def act(self, obs: Observation) -> Action:
        if obs.street == 0:
            cls, notch = self._pre_class(obs)
            return pushfold_preflop(self, obs, cls, notch)
        return super().act(obs)


class TossRival1(_TossMixin, RivalBot):
    """toss_or_holdem's aware strong team: red-team rival 1, unchanged, through the kit adapter, with the TAG's toss.
    Its preflop stays as built (it reads the first two of its three cards): handing it the Chen-best two measured
    worse (-0.47, scratch, 150 seeds): its hold'em ranges then play too many hands at a table where every hand is
    stronger."""


# ----- the aware Monte Carlo bot -------------------------------------------------------------------------------------


class AwareMC(_Base):
    """MonteCarloBot's play (bet at 0.6 equity, raise at 0.75, call when equity beats the price by 0.05, plus up to 0.15
    more as the bet grows to the pot: a bettor's range beats random) on a read that knows the variant: the deck it
    samples from, the rankings, dead cards and the bounty (subclasses). Preflop by Chen score: open-raise 3 bb with 9
    (five or more behind), 8 (three or four), 7 (late), no limps; facing a raise call with 9 up to an eighth of the
    stack, 3-bet with 11; at or under 12 bb shove with 8 (9 facing a raise)."""

    SAMPLES = 48
    MAX_OPP = 3

    def __init__(self, seed: Optional[int] = None, margin: float = 0.05, bet_eq: float = 0.6, raise_eq: float = 0.75):
        super().__init__(seed)
        self.margin, self.bet_eq, self.raise_eq = margin, bet_eq, raise_eq
        self.deck = list(range(52))

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        removed = set((rules.extras or {}).get("removed_ranks") or ())
        self.deck = [c for c in range(52) if (c >> 2) not in removed and (c & 3) < rules.n_suits]

    # hooks for the variants
    def score(self, cards) -> int:
        return evaluate(cards)

    def dead(self, obs: Observation) -> tuple:
        return ()

    def pre_score(self, obs: Observation) -> float:
        return chen_score(obs.hole)

    def bounty_chips(self, obs: Observation, win: int) -> float:
        return 0.0

    def equity(self, hole, board, dead, n_opp: int) -> float:
        gone = set(hole) | set(board) | set(dead)
        stub = [c for c in self.deck if c not in gone]
        need = 5 - len(board)
        n_opp = max(1, min(self.MAX_OPP, n_opp))
        take = 2 * n_opp + need
        if take > len(stub):
            return 0.5
        sample, score = self.rng.sample, self.score
        acc = 0.0
        for _ in range(self.SAMPLES):
            pick = sample(stub, take)
            full = board + tuple(pick[2 * n_opp:])
            mine = score(hole + full)
            best, ties = 0, 1
            for i in range(n_opp):
                s = score((pick[2 * i], pick[2 * i + 1]) + full)
                if s > best:
                    best, ties = s, 1
                elif s == best:
                    ties += 1
            acc += 1.0 if mine > best else (1.0 / ties if mine == best else 0.0)
        return acc / self.SAMPLES

    _start = (-1, 0)  # (hand, my chips when it was dealt)

    def act(self, obs: Observation) -> Action:
        bb = obs.big_blind
        if obs.hand_no != self._start[0]:
            self._start = (obs.hand_no, obs.stacks[obs.seat] + obs.bets[obs.seat])  # first seen preflop: as dealt
        if obs.street == 0:
            score = self.pre_score(obs)
            facing_raise = obs.to_call > bb or (obs.to_call > 0 and obs.bets[obs.seat] >= bb)
            if obs.stack_bb <= 12:
                return _raise_or_call(obs, obs.max_raise) if score >= (9.0 if facing_raise else 8.0) \
                    else _check_or_fold(obs)
            if facing_raise:
                if score >= 11.0:
                    return _raise_or_call(obs, 3 * (obs.to_call + obs.bets[obs.seat]))
                if score >= 9.0 and obs.to_call <= obs.my_stack // 8:
                    return Action.call()
                return _check_or_fold(obs)
            behind = players_behind(obs)
            if score >= (9.0 if behind >= 5 else 8.0 if behind >= 3 else 7.0) and RAISE in obs.legal:
                return _raise_or_call(obs, 3 * bb)
            return _check_or_fold(obs)
        if len(obs.hole) != 2:
            return _check_or_fold(obs)
        eq = self.equity(obs.hole, obs.board, self.dead(obs), obs.active - 1)
        pot = obs.total_pot
        win = pot - (self._start[1] - obs.stacks[obs.seat])  # the net win if the pot were ours now: the others' chips in it
        pot_eff = pot + self.bounty_chips(obs, win)
        if obs.to_call == 0:
            if eq >= self.bet_eq and RAISE in obs.legal:
                return _raise_or_call(obs, obs.bets[obs.seat] + max(bb, (2 * pot) // 3))
            return Action.check()
        odds = obs.to_call / (pot_eff + obs.to_call)
        if eq >= self.raise_eq and RAISE in obs.legal:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + pot)
        # a bet means a range better than random: the margin grows with the bet (up to 0.15 more for a pot-sized one)
        if eq >= odds + self.margin + 0.15 * min(1.0, obs.to_call / max(1, pot - obs.to_call)):
            return Action.call()
        return Action.fold()


class TossMC(_TossMixin, AwareMC):
    """toss_or_holdem's aware Monte Carlo bot: the Chen score of its best two preflop (+1 for a helping third card),
    two-card opponents after the toss, every face-up toss dead."""

    def pre_score(self, obs: Observation) -> float:
        if len(obs.hole) < 3:
            return chen_score(obs.hole)
        i, j = best_two(obs.hole)
        return chen_score((obs.hole[i], obs.hole[j])) + (1.0 if third_bonus(obs.hole, i, j) >= 2 else 0.0)

    def dead(self, obs: Observation) -> tuple:
        return _discards(obs.extras, obs.seat)


# ----- bounty --------------------------------------------------------------------------------------------------------


def my_bounty(obs: Observation):
    b = (obs.extras or {}).get("bounties") or {}
    r = b.get(obs.seat)
    if r is None:
        r = b.get(str(obs.seat))
    return r


def bounty_live(obs: Observation) -> tuple[bool, bool]:
    """(holding the bounty rank, the bounty is hit now: in the hand or on the board)."""
    r = my_bounty(obs)
    if r is None:
        return False, False
    held = any((c >> 2) == r for c in obs.hole)
    return held, held or any((c >> 2) == r for c in obs.board)


def bounty_bet(bot, obs: Observation) -> Action | None:
    """With the bounty hit and nothing to call in a pot of at most three players: bet half the pot (winning it now pays
    1.5x + 10). None otherwise."""
    if obs.to_call == 0 and obs.active <= 3 and RAISE in obs.legal:
        return _raise_or_call(obs, obs.bets[obs.seat] + max(obs.big_blind, obs.total_pot // 2))
    return None


class BountyTAG(ChartTAG):
    """bounty's aware TAG (module doc)."""

    OPEN_NOTCH, CALL_NOTCH, POST = 1, 0, True

    def act(self, obs: Observation) -> Action:
        held, hit = bounty_live(obs)
        if obs.street == 0:
            return tag_preflop(self, obs, two_card_class(obs.hole), self.OPEN_NOTCH if held else 0,
                               call_notch=self.CALL_NOTCH if held else 0)
        if hit and self.POST:
            a = bounty_bet(self, obs)
            if a is not None:
                return a
        return super().act(obs)


class BountyPushFold(PushFoldBot):
    """bounty's aware push/fold bot (module doc)."""

    OPEN_NOTCH, CALL_NOTCH, POST = 1, 0, True

    def act(self, obs: Observation) -> Action:
        held, hit = bounty_live(obs)
        if obs.street == 0:
            return pushfold_preflop(self, obs, two_card_class(obs.hole), self.OPEN_NOTCH if held else 0,
                                    call_notch=self.CALL_NOTCH if held else 0)
        if hit and self.POST and obs.stack_bb > self.pushfold_bb:
            a = bounty_bet(self, obs)
            if a is not None:
                return a
        return super().act(obs)


class BountyMC(AwareMC):
    """bounty's aware Monte Carlo bot: preflop 2 Chen points looser holding its bounty rank; postflop, with the bounty
    hit, it bets half the pot when checked to in a pot of three or fewer. (Pricing the bounty's chips into its calls
    measured worse than ignoring them: -0.07 against the plain bot, the same bot betting +0.07; scratch, 100 seeds.)"""

    def pre_score(self, obs: Observation) -> float:
        held, _ = bounty_live(obs)
        return chen_score(obs.hole) + (2.0 if held else 0.0)

    def act(self, obs: Observation) -> Action:
        if obs.street > 0:
            _, hit = bounty_live(obs)
            if hit:
                if obs.hand_no != self._start[0]:
                    self._start = (obs.hand_no, obs.stacks[obs.seat] + obs.bets[obs.seat])
                a = bounty_bet(self, obs)
                if a is not None:
                    return a
        return super().act(obs)


# ----- short deck ----------------------------------------------------------------------------------------------------

_SD_ORDER = (0, 1, 2, 3, 4, 6, 5, 7, 8)  # flush above full house
_LOW_STRAIGHT = frozenset({12, 4, 5, 6, 7})


def sd_score(cards) -> int:
    """Short-deck strength of 5..8 canonical cards (ShortDeckHooks.score_hand's ranking): flush over full house,
    A-6-7-8-9 the lowest straight."""
    s = evaluate(cards)
    cat = category(s)
    if cat < 4 or cat == 5:
        ranks = set()
        by_suit: dict = {}
        for c in cards:
            ranks.add(c >> 2)
            by_suit.setdefault(c & 3, set()).add(c >> 2)
        if any(_LOW_STRAIGHT <= rs for rs in by_suit.values()):
            return _SD_ORDER[8] * 10000 + 1
        if cat < 4 and _LOW_STRAIGHT <= ranks:
            return _SD_ORDER[4] * 10000 + 1
    return _SD_ORDER[cat] * 10000 + s


def sd_category(hole, board) -> int:
    """Short-deck category (0 high card .. 4 straight, 5 full house, 6 flush, 7 quads, 8 straight flush), -1 when
    there are not 5..8 cards."""
    cards = tuple(hole) + tuple(board)
    if not 5 <= len(cards) <= 8:
        return -1
    return sd_score(cards) // 10000


def sd_strong(hole, board) -> bool:
    """Top pair or better, read with short-deck rankings."""
    cat = sd_category(hole, board)
    if cat >= 2:
        return True
    return cat == 1 and top_pair_or_better(hole, board)


_SD_RANKED: Optional[list] = None
_SD_LIVE = tuple(range(4, 13))


def _sd_ranked() -> list:
    """Short-deck classes, strongest first (tables/variants/short_deck/preflop_rank.json, heads-up equity)."""
    global _SD_RANKED
    if _SD_RANKED is None:
        with open(os.path.join(_TABLES, "variants", "short_deck", "preflop_rank.json")) as f:
            rank = json.load(f)
        _SD_RANKED = sorted(rank, key=lambda c: -rank[c])
    return _SD_RANKED


def _combos(cls: str) -> int:
    return 6 if len(cls) == 2 else 4 if cls[2] == "s" else 12


def sd_range(holdem: frozenset, scale: float = 1.0) -> frozenset:
    """A hold'em range re-cut for the 36-card deck: the strongest short-deck classes holding the same share of combos
    (times `scale`)."""
    share = sum(_combos(c) for c in holdem) / 1326.0 * scale
    out, acc = set(), 0
    for c in _sd_ranked():
        if acc >= share * 630:
            break
        out.add(c)
        acc += _combos(c)
    return frozenset(out)


class ShortTAG(ChartTAG):
    """short_deck's aware TAG (module doc)."""

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        if not hasattr(ShortTAG, "_R"):
            ShortTAG._R = {"early": sd_range(ChartTAG.EARLY, 1.2), "middle": sd_range(ChartTAG.MIDDLE, 1.2),
                           "late": sd_range(ChartTAG.LATE, 1.2), "wide": sd_range(ChartTAG.LATE | _WIDE_EXTRA, 1.2),
                           "three_bet": sd_range(ChartTAG.THREE_BET), "call_raise": sd_range(ChartTAG.CALL_RAISE)}

    def act(self, obs: Observation) -> Action:
        R = ShortTAG._R
        if obs.street == 0:
            return tag_preflop(self, obs, two_card_class(obs.hole), 0, R["early"], R["middle"], R["late"], R["wide"],
                               R["three_bet"], R["call_raise"])
        cat = sd_category(obs.hole, obs.board)
        return tag_postflop(self, obs, sd_strong(obs.hole, obs.board), cat >= 3)


class ShortPushFold(PushFoldBot):
    """short_deck's aware push/fold bot (module doc)."""

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        super().new_table(rules, seat, n_players)
        if not hasattr(ShortPushFold, "_R"):
            P = PushFoldBot
            ShortPushFold._R = {
                "OPEN": {k: sd_range(v, 1.2) for k, v in P.OPEN.items()}, "THREE_BET": sd_range(P.THREE_BET),
                "CALL_RAISE": sd_range(P.CALL_RAISE), "PUSH": {k: sd_range(v) for k, v in P.PUSH.items()},
                "CALL_SHOVE": sd_range(P.CALL_SHOVE), "CALL_SHOVE_SHORT": sd_range(P.CALL_SHOVE_SHORT)}

    def act(self, obs: Observation) -> Action:
        if obs.street == 0:
            return pushfold_preflop(self, obs, two_card_class(obs.hole), 0, ShortPushFold._R)
        cat = sd_category(obs.hole, obs.board)
        return pushfold_postflop(self, obs, sd_strong(obs.hole, obs.board), cat >= 3)


class ShortMC(AwareMC):
    """short_deck's aware Monte Carlo bot: the 36-card deck, short-deck rankings; preflop the Chen score of the class's
    hold'em twin at the same short-deck percentile."""

    def score(self, cards) -> int:
        return sd_score(cards)

    def pre_score(self, obs: Observation) -> float:
        cls = two_card_class(obs.hole)
        sd = _SD_TWIN.get(cls)
        if sd is None:
            _build_twins()
            sd = _SD_TWIN.get(cls)
        return sd if sd is not None else chen_score(obs.hole)


_SD_TWIN: dict = {}


def _build_twins() -> None:
    """Short-deck class -> the Chen score of the hold'em class at the same combo percentile."""
    from ..core.types import RANKS

    hold = []
    for i in range(13):
        for j in range(i, 13):
            if i == j:
                hold.append(RANKS[i] * 2)
            else:
                hold.append(RANKS[j] + RANKS[i] + "s")
                hold.append(RANKS[j] + RANKS[i] + "o")
    def _chen(c):
        a, b = RANKS.index(c[0]), RANKS.index(c[1])
        if len(c) == 2:
            return chen_score((a * 4, a * 4 + 1))
        return chen_score((a * 4, b * 4 + (0 if c[2] == "s" else 1)))
    hold.sort(key=lambda c: -_chen(c))
    cum, acc = [], 0
    for c in hold:
        acc += _combos(c)
        cum.append((acc / 1326.0, _chen(c)))
    acc = 0
    for c in _sd_ranked():
        acc += _combos(c)
        q = acc / 630.0
        _SD_TWIN[c] = next((ch for p, ch in cum if p >= q), cum[-1][1])


AWARE = {
    "toss_tag": TossTAG, "toss_pushfold": TossPushFold, "toss_mc": TossMC, "toss_rival1": TossRival1,
    "bounty_tag": BountyTAG, "bounty_pushfold": BountyPushFold, "bounty_mc": BountyMC,
    "short_tag": ShortTAG, "short_pushfold": ShortPushFold, "short_mc": ShortMC,
}
# the `<variant>_aware` fields: Hero's seat, the entry's three aware bots in the seats of the honest Monte Carlo bot,
# the push/fold bot and the TAG, and the rest of `realistic` (montecarlo30, loose_aggro, rival1, timeout_then_recover);
# toss_or_holdem's rival 1 is toss_rival1 (rival 1 with the aware toss: it reads three cards, so it has a toss to make)
AWARE_FIELDS = {
    "toss_or_holdem_aware": ("hero", "montecarlo30", "toss_mc", "toss_pushfold", "loose_aggro", "toss_rival1",
                             "toss_tag", "timeout_then_recover"),
    "bounty_aware": ("hero", "montecarlo30", "bounty_mc", "bounty_pushfold", "loose_aggro", "rival1", "bounty_tag",
                     "timeout_then_recover"),
    "short_deck_aware": ("hero", "montecarlo30", "short_mc", "short_pushfold", "loose_aggro", "rival1", "short_tag",
                         "timeout_then_recover"),
}
# the variant each aware field is for (tools/climb_accept.py's `aware` stage, tools/variant_matrix.py --aware)
AWARE_VARIANT = {"toss_or_holdem_aware": "toss_or_holdem", "bounty_aware": "bounty", "short_deck_aware": "short_deck"}

_B.REGISTRY.update(AWARE)
_B._BY_CLASS.update({cls.__name__.lower(): cls for cls in AWARE.values()})
_B.FIELDS.update(AWARE_FIELDS)
