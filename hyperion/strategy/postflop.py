"""Postflop rules: one evaluator call, a few masks, a strength tier, and a four-action menu
(fold / check-call / bet a pot fraction / all-in). No tables, no simulation.

Tier (0..8) is the strength proxy, built from the made-hand category *relative to the board*
(a paired board does not make our unpaired hole cards "two pair") plus draw flags:
  0 nothing            3 top pair weak kicker, or a strong draw (flush draw / open-ender)
  1 overcards/gutshot  4 top pair good kicker, overpair, pair + draw, combo draw
  2 under/middle pair  5 two pair, trips on a paired board          6 set, straight
                       7 flush, full house                          8 quads, straight flush
Scary boards demote: a possible flush or straight we do not hold caps the tier.
TIER_EQUITY is the equity proxy against one opponent; draws use the rule of 2 and 4 on outs.

Profiler dials: bluff_mult (0 vs stations/maniacs, high vs folders and dead seats),
value_threshold_shift (negative = value bet thinner), call_down_mult (>1 vs maniacs).
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from ..core.eval import category, evaluate, warm
from ..core.types import Action, ActionKind
from .profiler import Profiler
from .spot import Spot

_FOLD = Action(ActionKind.FOLD)
_CHECK = Action(ActionKind.CHECK)
_CALL = Action(ActionKind.CALL)
_STRAIGHTS = tuple((0b11111 << i) for i in range(9)) + (0b1000000001111,)


def _build_completers() -> list[int]:
    """mask -> bitmask of ranks that would complete a straight when added to mask."""
    table = [0] * 8192
    for s in _STRAIGHTS:
        comp = [b for b in range(13) if not (s >> b & 1)]
        subsets = [0]
        for b in comp:
            subsets += [x | (1 << b) for x in subsets]
        for r in range(13):
            if s >> r & 1:
                base = s ^ (1 << r)
                bit = 1 << r
                for m in subsets:
                    table[base | m] |= bit
    return table


COMPLETERS = _build_completers()
warm(7)  # eval builds its 6/7-card lookups lazily (~100 ms each): pay at import, never in act()
TIER_EQUITY = (0.10, 0.20, 0.32, 0.42, 0.58, 0.72, 0.84, 0.92, 0.98)


@dataclass
class PostflopParams:
    cbet_freq_ip_dry: float = 0.6
    cbet_oop_mult: float = 0.6
    cbet_multiway_mult: float = 0.5  # per extra opponent
    cbet_wet_mult: float = 0.7
    cbet_size_dry: float = 0.33
    cbet_size_wet: float = 0.5
    value_tier: int = 4  # bet this tier and above for value
    value_size_dry: float = 0.5
    value_size_wet: float = 0.7
    big_value_tier: int = 6
    big_value_size: float = 0.8
    semibluff_freq: float = 0.5  # strong draws bet this often when checked to
    bluff_size: float = 0.5
    station_early_tier: int = 5  # vs stations: flop/turn bet only this tier and up ...
    station_river_tier: int = 4  # ... then bet the river big with this and up
    station_river_size: float = 1.0
    dead_bet_size: float = 0.33
    call_margin: float = 0.15  # equity must beat pot odds by this to call (swept: 0.05 -> 0.15 is +0.07 vs tags, 0.20 costs the weak field)
    multiway_call_penalty: float = 0.07  # per extra opponent, made hands only
    raise_tier: int = 6
    raise_size: float = 1.0  # pot-sized raise
    commit_frac: float = 0.5  # a bet this large relative to my stack becomes all-in
    bluff_max_stack_frac: float = 0.33  # never bluff more than this share of stack
    passive_bettor_extra_margin: float = 0.08  # a station betting means strength
    call_down_equity_bonus: float = 0.25  # per unit of (call_down_mult - 1): a flagged maniac buys ~one tier
    cheap_value_tier: int = 5  # Hero.cheap(): bet this and up, call with value_tier, otherwise check/fold
    # ICM gate on commitments: a call or value bet that risks at least icm_gate_frac of my chips must have
    # ICM-weighted EV above folding/checking, with the equity proxy discounted by icm_margin.
    icm_gate_frac: float = 0.5  # 2.0 = never (the gate is off); 0.5 = any commitment of half my stack or more
    icm_margin: float = 0.10  # the single biggest lever found: +0.14/+0.15/+0.07 on mixed/strong/weak fields, busts 54% -> 50%
    river_call_margin: float = 0.0  # extra margin on river calls: a student who bets the river has it
    river_min_tier: int = 0  # never call a river bet below this tier (0 = off)


class _Linear:
    __slots__ = ()

    def value(self, x: float) -> float:
        return x


class Postflop:
    def __init__(self, params: PostflopParams, seed: int | None = None):
        self.p = params
        self.rng = random.Random(seed)
        self.curve = _Linear()  # Hero installs its ICM curve; chip EV otherwise

    def _commit_ok(self, spot: Spot, eq: float, risk: int) -> bool:
        """Risking `risk` chips with equity `eq` (opponent never folds) beats keeping them, in ICM points."""
        e = eq - self.p.icm_margin
        if e <= 0.0:
            return False
        v = self.curve.value
        behind = spot.obs.stacks[spot.me]
        return e * v(behind + spot.pot_total + risk) + (1.0 - e) * v(behind - risk) > v(behind)

    # ------------------------------------------------------------------ hand reading
    @staticmethod
    def read(hole, board) -> tuple[int, int, bool]:
        """(tier, outs, wet_board). Pure arithmetic over ranks and suits plus one evaluate()."""
        cards = tuple(hole) + tuple(board)
        strength = evaluate(cards)
        cat = category(strength)
        r1, r2 = hole[0] >> 2, hole[1] >> 2
        s1, s2 = hole[0] & 3, hole[1] & 3
        board_mask = 0
        suit_cnt = [0, 0, 0, 0]
        top = -1
        hit1 = hit2 = 0
        paired_board = False
        for c in board:
            r = c >> 2
            bit = 1 << r
            if board_mask & bit:
                paired_board = True
            board_mask |= bit
            suit_cnt[c & 3] += 1
            if r > top:
                top = r
            if r == r1:
                hit1 += 1
            if r == r2:
                hit2 += 1
        full_mask = board_mask | (1 << r1) | (1 << r2)
        bsm = max(suit_cnt)
        flush_possible = bsm >= 3
        four_flush = bsm >= 4
        n_board = len(board)
        # flush draw: four to a suit using at least one hole card
        my_flush_cards = 0
        if s1 == s2:
            my_flush_cards = suit_cnt[s1] + 2
        else:
            a, b = suit_cnt[s1] + 1, suit_cnt[s2] + 1
            my_flush_cards = a if a > b else b
        flush_draw = my_flush_cards == 4 and n_board < 5
        # straight draw: completing ranks beyond what the board alone offers
        mine = COMPLETERS[full_mask] & ~COMPLETERS[board_mask] if n_board < 5 else 0
        n_str_outs = mine.bit_count()
        oesd = n_str_outs >= 2
        gutshot = n_str_outs == 1
        pocket = r1 == r2
        # connectedness of the board for texture: any straight possible with 1 or 2 cards
        connected = COMPLETERS[board_mask] != 0 or board_mask.bit_count() >= 3 and _span3(board_mask) <= 4
        wet = flush_possible or connected
        # made-hand tier relative to the board
        if cat >= 4:
            if cat == 4:
                tier = 6
            elif cat == 5:
                tier = 7
            elif cat == 6:
                tier = 7
            else:
                tier = 8
            if n_board == 5:
                bstr = evaluate(board)
                if bstr == strength:
                    tier = 1  # playing the board
            # a flush we do not hold on a 4-flush board, or a straight on a one-liner board
            if cat == 4 and four_flush:
                tier = 4
        elif cat == 3:
            if pocket and hit1 == 1:
                tier = 6  # set
            elif hit1 == 2 or hit2 == 2:
                tier = 5  # trips with a board pair
            else:
                tier = 1  # board trips, we have nothing
        elif cat == 2:
            if hit1 and hit2 and not pocket:
                tier = 5 if not paired_board else 4
            elif pocket:
                tier = 4 if r1 > top else 2  # pocket pair + board pair
            elif hit1 or hit2:
                tier = _pair_tier(r1 if hit1 else r2, r2 if hit1 else r1, top)
            else:
                tier = 1 if paired_board else 0
        elif cat == 1:
            if pocket:
                tier = 4 if r1 > top else 3 if r1 >= top - 1 and r1 > 7 else 2
            elif hit1 or hit2:
                tier = _pair_tier(r1 if hit1 else r2, r2 if hit1 else r1, top)
            else:
                tier = 1 if paired_board and (r1 > top or r2 > top) else 0
        else:
            tier = 1 if (r1 > top and r2 > top) else 0
        outs = 0
        if tier < 6:
            if flush_draw:
                outs += 9
            if oesd:
                outs += 8 if not flush_draw else 6
            elif gutshot:
                outs += 4 if not flush_draw else 3
            if flush_draw or oesd:
                if tier >= 2:
                    tier = 4 if tier < 4 else tier
                else:
                    tier = 4 if (flush_draw and oesd) else 3
            elif gutshot and tier < 1:
                tier = 1
            if tier <= 1 and (r1 > top or r2 > top):
                outs += 3 if r1 > top and r2 > top else 0
        # demotions for scary boards we do not beat
        if cat < 5:
            if four_flush:
                tier = min(tier, 2)
            elif flush_possible and n_board >= 4 and tier < 7:
                tier = min(tier, 4)
        return tier, outs, wet

    # ------------------------------------------------------------------ sizing
    def _bet(self, spot: Spot, frac: float, bluff: bool = False, eq: float = 1.0) -> Action:
        obs = spot.obs
        if ActionKind.RAISE not in obs.legal:
            return _CALL if spot.to_call > 0 and ActionKind.CALL in obs.legal else _CHECK
        pot_after_call = spot.pot_total + spot.to_call
        amount = obs.bets[spot.me] + spot.to_call + frac * pot_after_call
        if amount >= self.p.commit_frac * spot.my_total and not bluff:
            amount = obs.max_raise
        p = self.p
        behind = obs.stacks[spot.me]
        put = int(amount) - obs.bets[spot.me]
        if put >= p.icm_gate_frac * behind and not bluff and eq < 1.0:
            risk = min(behind, spot.max_opp_total - obs.bets[spot.me]) if spot.max_opp_total > obs.bets[spot.me] else behind
            if risk > 0 and not self._commit_ok(spot, eq, min(risk, put)):
                if spot.to_call == 0:
                    return _CHECK
                if spot.to_call >= p.icm_gate_frac * behind and not self._commit_ok(spot, eq, spot.to_call):
                    return _FOLD
                return _CALL
        amount = int(amount)
        if amount < obs.min_raise:
            amount = obs.min_raise
        if amount > obs.max_raise:
            amount = obs.max_raise
        return Action(ActionKind.RAISE, amount)

    # ------------------------------------------------------------------ decision
    def act(self, spot: Spot, hole, prof: Profiler | None, i_was_aggressor: bool, cheap: bool = False,
            board=None) -> Action:
        """`hole` and `board` are canonical cards (Hero remaps under a permuted rank order); the
        displayed obs.board is only the fallback when no board is passed."""
        p = self.p
        obs = spot.obs
        tier, outs, wet = self.read(hole, obs.board if board is None else board)
        street = obs.street
        cards_to_come = 2 if street == 1 else 1 if street == 2 else 0
        n_opp = spot.n_opps
        ip = spot.behind == 0
        # opponent dials: the most cautious of the live opponents, call-down from the bettor
        bluff_mult = 1.0
        shift = 0.0
        call_down = 1.0
        all_dead = n_opp > 0
        any_station = False
        bettor = -1
        if prof is not None and not cheap:
            for s in spot.opps:
                if prof.dead_seat(s):
                    continue
                all_dead = False
                d = prof.exploit_dials(s)
                if d["bluff_mult"] < bluff_mult:
                    bluff_mult = d["bluff_mult"]
                if d["value_threshold_shift"] < shift:
                    shift = d["value_threshold_shift"]
                if prof.station(s):
                    any_station = True
                if obs.bets[s] == spot.cur_bet and spot.cur_bet > 0:
                    bettor = s
            if bettor >= 0:
                call_down = prof.exploit_dials(bettor)["call_down_mult"]
            if all_dead:
                bluff_mult = 3.0
        else:
            all_dead = False
        draw_eq = outs * (4 if cards_to_come == 2 else 2) / 100.0 if cards_to_come else 0.0
        eq = TIER_EQUITY[tier]
        if draw_eq > eq:
            eq = draw_eq
        if tier >= 4:
            eq -= p.multiway_call_penalty * (n_opp - 1)
        value_tier = p.value_tier + int(shift)
        if cheap:
            return self._cheap(spot, tier, eq, wet)

        if spot.to_call == 0:
            # ---- nobody has bet: value, c-bet, semi-bluff, or check
            if all_dead:
                return self._bet(spot, p.dead_bet_size)
            if any_station:
                if street == 3:
                    if tier >= p.station_river_tier:
                        return self._bet(spot, p.station_river_size, eq=eq)
                    return _CHECK
                if tier >= p.station_early_tier:
                    return self._bet(spot, p.value_size_wet, eq=eq)
                return _CHECK
            if tier >= p.big_value_tier:
                return self._bet(spot, p.big_value_size, eq=eq)
            if tier >= value_tier:
                return self._bet(spot, p.value_size_wet if wet else p.value_size_dry, eq=eq)
            if bluff_mult <= 0.0 or spot.my_total <= 0:
                return _CHECK
            if street == 1 and i_was_aggressor:
                freq = p.cbet_freq_ip_dry * bluff_mult
                if not ip:
                    freq *= p.cbet_oop_mult
                if wet:
                    freq *= p.cbet_wet_mult
                if n_opp > 1:
                    freq *= p.cbet_multiway_mult ** (n_opp - 1)
                if self.rng.random() < freq:
                    size = p.cbet_size_wet if wet else p.cbet_size_dry
                    if size * spot.pot_total <= p.bluff_max_stack_frac * spot.my_total:
                        return self._bet(spot, size, bluff=True)
                return _CHECK
            if tier == 3 and cards_to_come and self.rng.random() < p.semibluff_freq * bluff_mult:
                if p.bluff_size * spot.pot_total <= p.bluff_max_stack_frac * spot.my_total:
                    return self._bet(spot, p.bluff_size, bluff=True)
            return _CHECK

        # ---- facing a bet
        pot_odds = spot.pot_odds
        margin = p.call_margin / call_down if call_down > 0 else p.call_margin
        if street == 3:
            margin += p.river_call_margin
            if tier < p.river_min_tier and tier < p.raise_tier:
                return _FOLD
        eq += (call_down - 1.0) * p.call_down_equity_bonus
        if any_station and bettor >= 0 and prof is not None and prof.station(bettor):
            margin += p.passive_bettor_extra_margin
        if tier >= p.raise_tier:
            return self._bet(spot, p.raise_size, eq=eq)
        if eq >= pot_odds + margin:
            if spot.to_call >= p.icm_gate_frac * obs.stacks[spot.me] and not self._commit_ok(spot, eq, spot.to_call):
                return _FOLD
            return _CALL
        return _FOLD

    def _cheap(self, spot: Spot, tier: int, eq: float, wet: bool) -> Action:
        p = self.p
        if spot.to_call == 0:
            if tier >= p.cheap_value_tier:
                return self._bet(spot, p.value_size_wet if wet else p.value_size_dry)
            return _CHECK
        if tier >= p.value_tier and eq >= spot.pot_odds:
            return _CALL
        return _FOLD


def _pair_tier(pair_rank: int, kicker: int, top: int) -> int:
    if pair_rank == top:
        return 4 if kicker >= 8 else 3  # top pair, T+ kicker is "good"
    return 2


def _span3(mask: int) -> int:
    """Smallest span of any three distinct ranks in mask (13 = none)."""
    ranks = [r for r in range(13) if mask >> r & 1]
    best = 13
    for i in range(len(ranks) - 2):
        sp = ranks[i + 2] - ranks[i]
        if sp < best:
            best = sp
    return best
