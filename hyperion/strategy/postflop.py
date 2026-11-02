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

Variants (Hero sets them from Rules / Observation.extras; every default is the plain game):
  read_multi   three or four hole cards, kept whole (8 cards at the river) or Omaha-style must-use-two:
               the same tiers from the same board-relative reading, one tier lower for made pairs and
               two pairs because every hand at the table is stronger
  read_low     2-7 lowball: the lowest five of my cards; tiers by the high card of a pairless low
  read_wild    wild cards: each wild becomes the card that makes my best hand (greedy), then the
               normal read on the result, one tier lower when the wild sits on the shared board
  dead cards   exposed cards of other seats come off flush and straight outs
  two boards   both boards are read; value needs both, the equity proxy is the mean (a split pot
               is half a pot), bet sizes are halved
  flush over full house, flush/straight tier shifts and the draw-outs multiplier are Config keys
  (drill 4 found prompt 05's short-deck bullets had no knobs)

Profiler dials: bluff_mult (0 vs stations/maniacs, high vs folders and dead seats),
value_threshold_shift (negative = value bet thinner), call_down_mult (>1 vs maniacs).
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import combinations

from ..core.eval import category, evaluate, evaluate_many, warm
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
# short deck (6 to ace, A-6-7-8-9 the lowest straight): the straights that exist, and their completers
_SD_STRAIGHTS = tuple((0b11111 << i) for i in range(4, 9)) + ((1 << 12) | (0b1111 << 4),)
_SD_LOW = (1 << 12) | (0b1111 << 4)


def _build_sd_completers() -> list[int]:
    table = [0] * 8192
    for s in _SD_STRAIGHTS:
        comp = [b for b in range(4, 13) if not (s >> b & 1)]
        subsets = [0]
        for b in comp:
            subsets += [x | (1 << b) for x in subsets]
        for r in range(13):
            if s >> r & 1:
                base = s ^ (1 << r)
                for m in subsets:
                    table[base | m] |= 1 << r
    return table


SD_COMPLETERS = _build_sd_completers()
SD_OUT_SCALE = 1.45  # an out is worth this much more than hold'em's rule of 4 and 2: 31 unseen cards, not 47
warm(7)  # hold'em's 6/7-card lookups (about 25 ms): pay at import, never in act()
TIER_EQUITY = (0.10, 0.20, 0.32, 0.42, 0.58, 0.72, 0.84, 0.92, 0.98)
# size_read (S12): a tier race, a higher tier wins this often on the flop / turn / river (an equal tier splits)
SIZE_WIN = (0.78, 0.86, 0.97)
# size_read_rank: the population's betting range per street (tier shares of every bet, sizes pooled) and its share of
# bets by size bucket (the same survey)
POP_BET = (
    (0.144, 0.166, 0.166, 0.141, 0.265, 0.061, 0.045, 0.011, 0.001),
    (0.033, 0.082, 0.173, 0.136, 0.351, 0.105, 0.068, 0.051, 0.001),
    (0.047, 0.085, 0.222, 0.078, 0.270, 0.079, 0.088, 0.126, 0.005),
)
POP_BKT = ((0.033, 0.629, 0.320, 0.012, 0.006), (0.037, 0.499, 0.398, 0.026, 0.040), (0.083, 0.410, 0.413, 0.029, 0.065))
# size_read's prior: the bettor's tier histogram for a bet of each size bucket (Profiler.SZ_EDGES; 5 = a raise) on
# each street, the tuning fields' opponents pooled (S12 survey: seeds 8000-8024, night, realistic, night_hard, top,
# elite, every seat but ours, from the simulator's cards). [street][bucket] -> 9 tier shares
SIZE_PRIOR = (
    (  # flop
        (0.240, 0.228, 0.203, 0.115, 0.196, 0.008, 0.007, 0.002, 0.001),
        (0.204, 0.228, 0.217, 0.123, 0.183, 0.025, 0.015, 0.005, 0.000),
        (0.017, 0.045, 0.068, 0.183, 0.428, 0.133, 0.101, 0.024, 0.000),
        (0.084, 0.039, 0.053, 0.062, 0.368, 0.202, 0.154, 0.034, 0.003),
        (0.141, 0.082, 0.135, 0.100, 0.306, 0.100, 0.129, 0.006, 0.000),
        (0.009, 0.026, 0.155, 0.064, 0.264, 0.229, 0.187, 0.065, 0.000),
    ),
    (  # turn
        (0.053, 0.074, 0.303, 0.106, 0.350, 0.046, 0.037, 0.030, 0.000),
        (0.057, 0.138, 0.229, 0.166, 0.305, 0.047, 0.031, 0.026, 0.001),
        (0.005, 0.026, 0.114, 0.114, 0.402, 0.162, 0.100, 0.075, 0.002),
        (0.013, 0.010, 0.026, 0.023, 0.261, 0.248, 0.257, 0.160, 0.003),
        (0.011, 0.013, 0.046, 0.073, 0.471, 0.209, 0.106, 0.068, 0.002),
        (0.003, 0.046, 0.142, 0.067, 0.250, 0.206, 0.146, 0.132, 0.008),
    ),
    (  # river
        (0.028, 0.070, 0.288, 0.137, 0.293, 0.054, 0.049, 0.072, 0.009),
        (0.069, 0.113, 0.298, 0.083, 0.259, 0.052, 0.046, 0.080, 0.001),
        (0.038, 0.077, 0.167, 0.069, 0.269, 0.095, 0.125, 0.155, 0.005),
        (0.010, 0.005, 0.054, 0.034, 0.192, 0.138, 0.251, 0.310, 0.005),
        (0.009, 0.018, 0.083, 0.056, 0.357, 0.148, 0.101, 0.224, 0.004),
        (0.003, 0.091, 0.173, 0.048, 0.268, 0.072, 0.095, 0.250, 0.001),
    ),
)
_LOW_TIER = {0: 8, 1: 8, 2: 8, 3: 8, 4: 8, 5: 8, 6: 7, 7: 6, 8: 5, 9: 4, 10: 3, 11: 2, 12: 1}  # pairless low by its top card


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
    # turn and river calls against a tight-aggressive bettor (VPIP under tight_vpip, postflop aggression over
    # tight_agg): its late bets are value, so the margin grows by tight_aggro_margin (0 = off)
    tight_aggro_margin: float = 0.0
    tight_vpip: float = 0.22
    tight_agg: float = 0.40
    # an unknown bettor's call-down dial is capped at this on the turn and river (a low aggression stat made the
    # dial > 1, i.e. lighter calls, against passive bettors whose late bets are value); 9 = off
    late_calldown_cap: float = 1.0  # swept: +0.13 vs seven rival1, rival1 among seven Heroes -0.17; neutral on the fields
    river_min_tier: int = 0  # never call a river bet below this tier (0 = off)
    # heads-up raised pots. Facing the preflop raiser's flop c-bet (heads-up, the first bet of the street, at most
    # vs_cbet_max_pot of the pot) from a seat whose smoothed c-bet rate is at least vs_cbet_min_rate, the call margin
    # is vs_cbet_margin instead of call_margin (-1 = off): a c-bet range is wide, and a third-pot bet folded middle
    # pair. With cbet_ftc_read my heads-up c-bet bluffs scale by the caller's smoothed fold-to-c-bet over
    # cbet_ftc_prior (capped at cbet_ftc_max) instead of the general bluff dial.
    vs_cbet_margin: float = 0.05  # aggression pass: shipped with reshove_mid_bb 25 (see docs/decisions.md)
    vs_cbet_max_pot: float = 0.75
    vs_cbet_min_rate: float = 0.0
    cbet_ftc_read: bool = False
    cbet_ftc_prior: float = 0.5
    cbet_ftc_max: float = 1.8
    # a wide bettor (S2, docs/drills/s2-exploit-fixes-log.md): facing a bet heads-up from a seat that bets this often
    # or more when nothing is to call postflop (its smoothed free-bet rate: prior wide_bettor_prior worth
    # wide_bettor_n chances), the call-down dial is at least 1 + wide_bettor_slope * (rate - wide_bettor_from), past
    # the late cap: a seat that bets most of its chances bets most of its hands. 1.0 = off
    wide_bettor_from: float = 1.0
    wide_bettor_slope: float = 1.5
    wide_bettor_prior: float = 0.4
    wide_bettor_n: float = 4.0
    # S12 reads (docs/drills/climb/s12-log.md); every one off by default.
    # size_read: facing a single bet heads-up (or a raise of my bet), the bettor's range for a bet of that size (bucket
    # of the pot before the bet, Profiler.SZ_EDGES; a raise is its own bucket) is a tier histogram: the population's
    # (SIZE_PRIOR) worth size_read_n0 bets, plus the bettor's own bets of that size whose cards were shown. My equity
    # against it is a tier race (SIZE_WIN: a higher tier wins this often by street). The call decision blends the
    # usual one (equity proxy - margin) with this one (read equity - size_read_margin) at weight size_read
    # (size_read_evid: times n / (n + size_read_n0), so the read only counts with the seat's own evidence).
    size_read: float = 0.0
    size_read_n0: float = 8.0
    size_read_margin: float = 0.03
    size_read_evid: bool = False
    size_read_raise: float = 2.0  # raise for value when the read equity is at least this (2 = never)
    size_read_pool: bool = False  # the seat's shown bets of this size on every street count (not only this street's)
    # size_read_rank > 0: the prior for a seat's bet of size bucket b is the slice of the population's betting range
    # (POP_BET, weakest first) that its bets of smaller sizes leave below, as wide as its share of bets of size b:
    # bigger bets are stronger, so a seat with two sizes bets its weaker hands small. Its size shares are its bets seen
    # (every street) shrunk toward the population's shares (POP_BKT) with this many bets; a seat with one size reads
    # as the population's whole betting range. 0 = the population's histogram per size (SIZE_PRIOR)
    size_read_rank: float = 0.0
    size_read_rank_streets: int = 7  # bit mask of the streets the rank prior is used on (1 flop, 2 turn, 4 river)
    size_read_rank_by_street: bool = False  # the seat's size shares on this street only (not pooled over streets)
    size_read_rank_mix: float = 1.0  # the prior is this share of the rank slice plus the rest of SIZE_PRIOR's map
    # xr_shift: heads-up, nothing to call, the opponent checked to me on this street and its check-raise rate (prior
    # xr_prior worth xr_n0 chances) is at most xr_max: value-bet this many tiers thinner (a checked range with no
    # check-raises holds few strong hands)
    xr_shift: int = 0
    xr_max: float = 0.04
    xr_prior: float = 0.02
    xr_n0: float = 10.0
    xr_streets: int = 7  # bit mask of the streets it applies on: 1 flop, 2 turn, 4 river
    # strength-axis knobs (prompt 05's short-deck patch): a made flush / straight lands this many tiers away from
    # its hold'em tier, and draw outs are scaled (short deck: an open-ender is worth about 1.2x its hold'em outs)
    flush_tier_shift: int = 0
    straight_tier_shift: int = 0
    draw_outs_mult: float = 1.0
    # information-axis knobs
    multi_tier_penalty: int = 1  # three or four hole cards: made pairs and two pairs (tiers 3..5) drop this much
    two_boards_size_mult: float = 0.5  # every bet size when the pot splits over two boards
    wild_board_penalty: int = 1  # a wild on the shared board helps everyone: one tier off my read
    low_draw_outs_cap: int = 12  # lowball: at most this many outs to a better low are counted


class _Linear:
    __slots__ = ()
    points = False

    def value(self, x: float) -> float:
        return x


def _must_use_strength(hole, board, k: int) -> int:
    """Best hand using exactly k hole cards and 5 - k board cards (k = 2 is Omaha). Canonical cards."""
    best = 0
    nb = 5 - k
    for hs in combinations(hole, k):
        for bs in combinations(board, nb):
            s = evaluate(hs + bs)
            if s > best:
                best = s
    return best


class Postflop:
    def __init__(self, params: PostflopParams, seed: int | None = None):
        self.p = params
        self.rng = random.Random(seed)
        self.curve = _Linear()  # Hero installs its ICM curve; chip EV otherwise
        self.low = False
        self.wild_rank = -1  # canonical rank index of the wild card, -1 = none
        self.flush_over_full = False
        self.short = False  # short deck: A-6-7-8-9 a straight, its straights' outs, five flush outs, outs x SD_OUT_SCALE
        self._mult = 1.0  # bet-size multiplier for the current decision (two boards: 0.5)
        self.last = ""  # the sub-decision taken last (diagnostics: the runner's bust tracer reads it)

    def set_mode(self, low: bool = False, wild_rank: int = -1, flush_over_full: bool = False,
                 short: bool = False) -> None:
        """Ranking-axis switches Hero sets per table from Rules.extras (`short`: the short-deck read, a dial)."""
        self.low = low
        self.wild_rank = wild_rank
        self.flush_over_full = flush_over_full
        self.short = short

    def _commit_ok(self, spot: Spot, eq: float, risk: int) -> bool:
        """Risking `risk` chips with equity `eq` (opponent never folds) beats keeping them, in ICM points.
        `spot.ror` (the risk-of-ruin margin while deep and early) adds to the margin."""
        e = eq - self.p.icm_margin - spot.ror
        if e <= 0.0:
            return False
        v = self.curve.value
        behind = spot.obs.stacks[spot.me]
        v_win = v(behind + spot.pot_total + spot.bounty_bonus + risk)
        if spot.ko_points and self.curve.points:
            v_win += spot.ko_points * spot.cover_frac
        return e * v_win + (1.0 - e) * v(behind - risk) > v(behind)

    # ------------------------------------------------------------------ hand reading
    @staticmethod
    def read(hole, board, dead=(), flush_shift: int = 0, straight_shift: int = 0, flush_over_full: bool = False,
             short: bool = False, long: bool = False, more: bool = False) -> tuple[int, int, bool]:
        """(tier, outs, wet_board) for two hole cards. Pure arithmetic over ranks and suits plus one evaluate().
        `dead` cards (exposed elsewhere) come off the draw outs; the shifts move a made flush / straight. `short`: the
        36-card deck's straights (A-6-7-8-9 made and drawn to, no wheel) and flush draws (five outs, not nine).
        `long`: the board may be longer than five (any count, core.eval.evaluate_many past 8 cards; playing the board
        is read against the board's own best five at any length). `more`: another board card may still come on a board
        of five or more (river_of_blood's red last card), so draws and their outs count there too."""
        cards = tuple(hole) + tuple(board)
        strength = evaluate(cards) if len(cards) <= 8 else evaluate_many(cards)
        cat = category(strength)
        comp = COMPLETERS
        if short:
            comp = SD_COMPLETERS
            if cat < 8:
                m = 0
                sm = [0, 0, 0, 0]
                for c in cards:
                    m |= 1 << (c >> 2)
                    sm[c & 3] |= 1 << (c >> 2)
                if any(x & _SD_LOW == _SD_LOW for x in sm):
                    cat = 8
                elif cat < 4 and m & _SD_LOW == _SD_LOW:
                    cat = 4
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
        fsuit = s1
        if s1 == s2:
            my_flush_cards = suit_cnt[s1] + 2
        else:
            a, b = suit_cnt[s1] + 1, suit_cnt[s2] + 1
            if a >= b:
                my_flush_cards = a
            else:
                my_flush_cards, fsuit = b, s2
        drawing = n_board < 5 or more
        flush_draw = my_flush_cards == 4 and drawing
        # straight draw: completing ranks beyond what the board alone offers
        mine = comp[full_mask] & ~comp[board_mask] if drawing else 0
        n_str_outs = mine.bit_count()
        oesd = n_str_outs >= 2
        gutshot = n_str_outs == 1
        pocket = r1 == r2
        # connectedness of the board for texture: any straight possible with 1 or 2 cards
        connected = comp[board_mask] != 0 or board_mask.bit_count() >= 3 and _span3(board_mask) <= 4
        wet = flush_possible or connected
        # made-hand tier relative to the board
        if cat >= 4:
            if cat == 4:
                tier = 6 + straight_shift
            elif cat == 5:
                tier = 7 + flush_shift
            elif cat == 6:
                tier = 6 if (flush_over_full and flush_possible) else 7
            else:
                tier = 8
            if n_board == 5 or (long and n_board > 5):
                bstr = evaluate(board) if n_board <= 8 else evaluate_many(board)
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
            if flush_draw or oesd or gutshot:
                outs = _draw_outs(flush_draw, fsuit, oesd, gutshot, mine, dead, cards, 5 if short else 9)
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
        if tier < 0:
            tier = 0
        elif tier > 8:
            tier = 8
        return tier, outs, wet

    def read_multi(self, hole, board, must_use: int = 0, dead=()) -> tuple[int, int, bool]:
        """(tier, outs, wet) for three or four hole cards: kept whole (best five of all, 8 cards at most)
        or must-use-k (Omaha when k = 2). The same board-relative tiers as `read`, then
        `multi_tier_penalty` off made pairs and two pairs because everyone holds more cards."""
        p = self.p
        hole = tuple(hole)
        board = tuple(board)
        nh = len(hole)
        if must_use:
            strength = _must_use_strength(hole, board, must_use)
        else:
            strength = evaluate(hole + board)
        cat = category(strength)
        hr = [c >> 2 for c in hole]
        hs = [c & 3 for c in hole]
        board_mask = 0
        suit_cnt = [0, 0, 0, 0]
        top = -1
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
        hits = [0] * nh
        for i in range(nh):
            for c in board:
                if (c >> 2) == hr[i]:
                    hits[i] += 1
        pocket = -1  # highest rank paired within the hole
        for i in range(nh):
            for j in range(i + 1, nh):
                if hr[i] == hr[j] and hr[i] > pocket:
                    pocket = hr[i]
        hit_ranks = {hr[i] for i in range(nh) if hits[i]}
        full_mask = board_mask
        for r in hr:
            full_mask |= 1 << r
        bsm = max(suit_cnt)
        flush_possible = bsm >= 3
        four_flush = bsm >= 4
        n_board = len(board)
        need_hole = 2 if must_use == 2 else 1
        # flush draw / one-card flush: per suit, how many of mine
        my_suit = [0, 0, 0, 0]
        for s in hs:
            my_suit[s] += 1
        flush_draw = False
        fsuit = 0
        one_card_flush = False
        for s in range(4):
            if my_suit[s] >= need_hole:
                tot = my_suit[s] + suit_cnt[s]
                if must_use == 2:
                    if my_suit[s] >= 2 and suit_cnt[s] == 2 and n_board < 5:  # Omaha: two in hand, two on board
                        flush_draw, fsuit = True, s
                elif tot == 4 and n_board < 5:
                    flush_draw, fsuit = True, s
                if tot >= 5 and my_suit[s] == 1 and suit_cnt[s] >= 4:
                    one_card_flush = True
        mine = COMPLETERS[full_mask] & ~COMPLETERS[board_mask] if n_board < 5 else 0
        n_str_outs = mine.bit_count()
        oesd = n_str_outs >= 2
        gutshot = n_str_outs == 1
        connected = COMPLETERS[board_mask] != 0 or board_mask.bit_count() >= 3 and _span3(board_mask) <= 4
        wet = flush_possible or connected
        kicker = max(hr)
        if cat >= 4:
            if cat == 4:
                tier = 6 + p.straight_tier_shift
            elif cat == 5:
                tier = 7 + p.flush_tier_shift
                if one_card_flush and not must_use:
                    tier = 4
            elif cat == 6:
                tier = 6 if (self.flush_over_full and flush_possible) else 7
            else:
                tier = 8
            if n_board == 5 and not must_use and evaluate(board) == strength:
                tier = 1  # playing the board
            if cat == 4 and four_flush:
                tier = 4
        elif cat == 3:
            if pocket >= 0 and pocket in hit_ranks:
                tier = 6  # set
            elif any(h == 2 for h in hits):
                tier = 5  # trips with a board pair
            elif hr.count(pocket) >= 3:
                tier = 5  # trips in the hand
            else:
                tier = 1
        elif cat == 2:
            if len(hit_ranks) >= 2:
                tier = 5 if not paired_board else 4
            elif pocket >= 0 and hit_ranks:
                tier = 5
            elif pocket >= 0:
                tier = 4 if pocket > top else 2
            elif hit_ranks:
                r = max(hit_ranks)
                tier = _pair_tier(r, max([x for x in hr if x != r] or [0]), top)
            else:
                tier = 1 if paired_board else 0
        elif cat == 1:
            if pocket >= 0:
                tier = 4 if pocket > top else 3 if pocket >= top - 1 and pocket > 7 else 2
            elif hit_ranks:
                r = max(hit_ranks)
                tier = _pair_tier(r, max([x for x in hr if x != r] or [0]), top)
            else:
                tier = 1 if paired_board and kicker > top else 0
        else:
            tier = 1 if sum(1 for r in hr if r > top) >= 2 else 0
        if 3 <= tier <= 5 and nh > 2:
            tier -= p.multi_tier_penalty  # made pairs and two pairs only: a draw's outs are what they are
        outs = 0
        if tier < 6:
            if flush_draw or oesd or gutshot:
                outs = _draw_outs(flush_draw, fsuit, oesd, gutshot, mine, dead, hole + board)
            if flush_draw or oesd:
                if tier >= 2:
                    tier = 4 if tier < 4 else tier
                else:
                    tier = 4 if (flush_draw and oesd) else 3
            elif gutshot and tier < 1:
                tier = 1
            if tier <= 1 and kicker > top:
                outs += 3 if sum(1 for r in hr if r > top) >= 2 else 0
        if cat < 5:
            if four_flush:
                tier = min(tier, 2)
            elif flush_possible and n_board >= 4 and tier < 7:
                tier = min(tier, 4)
        if tier < 0:
            tier = 0
        elif tier > 8:
            tier = 8
        return tier, outs, wet

    def read_low(self, hole, board) -> tuple[int, int, bool]:
        """2-7 lowball: the weakest five of my cards is my hand. Tier by the top card of a pairless, non-straight,
        non-flush low (7-high is the nuts); a pair as the best low is nearly nothing. Outs: cards below my top
        card that pair nothing in the low (capped), since every street can only improve a low."""
        cards = tuple(hole) + tuple(board)
        best = None
        best_s = 1 << 30
        for five in combinations(cards, 5):
            s = evaluate(five)
            if s < best_s:
                best_s, best = s, five
        cat = category(best_s)
        ranks = sorted((c >> 2 for c in best), reverse=True)
        if cat == 0:
            tier = _LOW_TIER[ranks[0]]
        elif cat == 1:
            tier = 1 if ranks[0] <= 5 else 0
        else:
            tier = 0
        outs = 0
        if len(cards) < 7 and cat <= 1:
            have = set(ranks)
            seen = {}
            for c in cards:
                seen[c >> 2] = seen.get(c >> 2, 0) + 1
            cap = self.p.low_draw_outs_cap
            for r in range(ranks[0]):
                if r not in have:
                    outs += 4 - seen.get(r, 0)
            if outs > cap:
                outs = cap
        return tier, outs, False

    def read_wild(self, hole, board, must_use: int = 0, dead=()) -> tuple[int, int, bool]:
        """Each wild (canonical rank self.wild_rank) becomes, greedily, the card that makes my best hand; then
        the normal read on the substituted cards, `wild_board_penalty` lower when a wild was on the board."""
        w = self.wild_rank
        cards = list(hole) + list(board)
        nh = len(hole)
        wild_pos = [k for k, c in enumerate(cards) if (c >> 2) == w]
        if not wild_pos:
            if nh == 2 and not must_use:
                return self.read(hole, board, dead, self.p.flush_tier_shift, self.p.straight_tier_shift, self.flush_over_full)
            return self.read_multi(hole, board, must_use, dead)
        present = {c for c in cards if (c >> 2) != w}
        on_board = any(k >= nh for k in wild_pos)
        for k in wild_pos:
            best, best_s = cards[k], -1
            for cand in range(52):
                if (cand >> 2) == w or cand in present:
                    continue
                cards[k] = cand
                s = evaluate(cards) if not must_use else _must_use_strength(cards[:nh], cards[nh:], must_use)
                if s > best_s:
                    best_s, best = s, cand
            cards[k] = best
            present.add(best)
        h2, b2 = tuple(cards[:nh]), tuple(cards[nh:])
        if nh == 2 and not must_use:
            tier, outs, wet = self.read(h2, b2, dead, self.p.flush_tier_shift, self.p.straight_tier_shift, self.flush_over_full)
        else:
            tier, outs, wet = self.read_multi(h2, b2, must_use, dead)
        if on_board and tier > 0:
            tier = max(0, tier - self.p.wild_board_penalty)
        return tier, outs, wet

    def _read(self, hole, board, must_use: int, dead, long: bool = False, more: bool = False) -> tuple[int, int, bool]:
        if self.low:
            return self.read_low(hole, board)
        if self.wild_rank >= 0:
            return self.read_wild(hole, board, must_use, dead)
        if len(hole) == 2 and not must_use:
            p = self.p
            if long:
                return self.read(hole, board, dead, p.flush_tier_shift, p.straight_tier_shift, self.flush_over_full,
                                 self.short, True, more)
            return self.read(hole, board, dead, p.flush_tier_shift, p.straight_tier_shift, self.flush_over_full,
                             self.short)
        return self.read_multi(hole, board, must_use, dead)

    def _equity(self, tier: int, outs: int, cards_to_come: int, n_opp: int) -> float:
        p = self.p
        draw_eq = outs * p.draw_outs_mult * (4 if cards_to_come == 2 else 2) / 100.0 if cards_to_come else 0.0
        if self.short:
            draw_eq *= SD_OUT_SCALE
        eq = TIER_EQUITY[tier]
        if draw_eq > eq:
            eq = draw_eq
        if tier >= 4:
            eq -= p.multiway_call_penalty * (n_opp - 1)
        return eq

    # ------------------------------------------------------------------ sizing
    def _bet(self, spot: Spot, frac: float, bluff: bool = False, eq: float = 1.0) -> Action:
        obs = spot.obs
        if ActionKind.RAISE not in obs.legal:
            return _CALL if spot.to_call > 0 and ActionKind.CALL in obs.legal else _CHECK
        frac *= self._mult
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
            board=None, board2=None, must_use: int = 0, dead=(), value_shift: int = 0, call_shift: int = 0,
            street: int | None = None, to_come: int | None = None, long: bool = False, more: bool = False) -> Action:
        """`hole` and `board` are canonical cards (Hero remaps under a permuted rank order); the
        displayed obs.board is only the fallback when no board is passed. `board2` is the second board of
        a two-board game, `must_use` the Omaha rule, `dead` the exposed cards, `value_shift` raises the
        value thresholds (streets before a swap), `call_shift` reads a made hand this many tiers lower when
        facing a bet. `street` / `to_come` replace the observation's street and the cards still to come (a long
        board: Hero plays a street that may not be the last as a turn); `long` / `more`: see `read`."""
        p = self.p
        obs = spot.obs
        if board is None:
            board = obs.board
        tier, outs, wet = self._read(hole, board, must_use, dead, long, more)
        if street is None:
            street = obs.street
        if to_come is None:
            cards_to_come = 2 if street == 1 else 1 if street == 2 else 0
        else:
            cards_to_come = to_come
        n_opp = spot.n_opps
        ip = spot.behind == 0
        self._mult = 1.0
        t_eq = tier - call_shift if call_shift and spot.to_call > 0 else tier
        eq = self._equity(t_eq if t_eq > 0 else 0, outs, cards_to_come, n_opp)
        if board2 is not None:
            t2, o2, w2 = self._read(hole, board2, must_use, dead)
            t2e = t2 - call_shift if call_shift and spot.to_call > 0 else t2
            eq = 0.5 * (eq + self._equity(t2e if t2e > 0 else 0, o2, cards_to_come, n_opp))
            if t2 < tier:
                tier, outs = t2, o2
            wet = wet or w2
            self._mult = p.two_boards_size_mult
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
        value_tier = p.value_tier + int(shift) + value_shift
        big_value_tier = p.big_value_tier + value_shift
        if p.xr_shift and spot.to_call == 0 and n_opp == 1 and prof is not None and not cheap \
                and 1 <= street <= 3 and p.xr_streets >> (street - 1) & 1:
            o = spot.opps[0]
            if prof.chk_mask >> o & 1 and prof.xr_rate(o, p.xr_prior, p.xr_n0) <= p.xr_max:
                value_tier -= p.xr_shift
        self.last = ""
        if cheap:
            self.last = "cheap"
            return self._cheap(spot, tier, eq, wet)

        if spot.to_call == 0:
            # ---- nobody has bet: value, c-bet, semi-bluff, or check
            if all_dead:
                self.last = "dead_bet"
                return self._bet(spot, p.dead_bet_size)
            if any_station:
                if street == 3:
                    if tier >= p.station_river_tier + value_shift:
                        self.last = "station_river"
                        return self._bet(spot, p.station_river_size, eq=eq)
                    return _CHECK
                if tier >= p.station_early_tier + value_shift:
                    self.last = "station_value"
                    return self._bet(spot, p.value_size_wet, eq=eq)
                return _CHECK
            if tier >= big_value_tier:
                self.last = "big_value"
                return self._bet(spot, p.big_value_size, eq=eq)
            if tier >= value_tier:
                self.last = "value"
                return self._bet(spot, p.value_size_wet if wet else p.value_size_dry, eq=eq)
            if bluff_mult <= 0.0 or spot.my_total <= 0:
                return _CHECK
            if street == 1 and i_was_aggressor:
                freq = p.cbet_freq_ip_dry * bluff_mult
                if p.cbet_ftc_read and n_opp == 1 and prof is not None:
                    r = prof.fold_to_cbet(spot.opps[0], p.cbet_ftc_prior) / p.cbet_ftc_prior
                    freq = p.cbet_freq_ip_dry * (r if r < p.cbet_ftc_max else p.cbet_ftc_max)
                if not ip:
                    freq *= p.cbet_oop_mult
                if wet:
                    freq *= p.cbet_wet_mult
                if n_opp > 1:
                    freq *= p.cbet_multiway_mult ** (n_opp - 1)
                if self.rng.random() < freq:
                    size = p.cbet_size_wet if wet else p.cbet_size_dry
                    if size * spot.pot_total <= p.bluff_max_stack_frac * spot.my_total:
                        self.last = "cbet"
                        return self._bet(spot, size, bluff=True)
                return _CHECK
            if tier == 3 and cards_to_come and self.rng.random() < p.semibluff_freq * bluff_mult:
                if p.bluff_size * spot.pot_total <= p.bluff_max_stack_frac * spot.my_total:
                    self.last = "semibluff"
                    return self._bet(spot, p.bluff_size, bluff=True)
            return _CHECK

        # ---- facing a bet
        pot_odds = spot.pot_odds
        if street >= 2 and bettor >= 0 and prof is not None and not cheap:
            if call_down > p.late_calldown_cap and not (prof.maniac(bettor) or prof.random_like(bettor)):
                call_down = p.late_calldown_cap
        if p.wide_bettor_from < 1.0 and n_opp == 1 and bettor >= 0 and prof is not None:
            r = prof.free_bet_rate(bettor, p.wide_bettor_prior, p.wide_bettor_n)
            if r > p.wide_bettor_from:
                cd = 1.0 + p.wide_bettor_slope * (r - p.wide_bettor_from)
                if cd > call_down:
                    call_down = cd
        base_margin = p.call_margin
        if p.vs_cbet_margin >= 0.0 and street == 1 and n_opp == 1 and bettor >= 0 and prof is not None \
                and prof.pre_raiser == bettor and obs.bets[spot.me] == 0 and obs.pot > 0 \
                and spot.to_call <= p.vs_cbet_max_pot * obs.pot and prof.cbet_rate(bettor) >= p.vs_cbet_min_rate:
            base_margin = p.vs_cbet_margin
        margin = base_margin / call_down if call_down > 0 else base_margin
        if p.tight_aggro_margin > 0.0 and street >= 2 and bettor >= 0 and prof is not None and not cheap \
                and prof.vpip_rate(bettor) < p.tight_vpip and prof.aggression(bettor) > p.tight_agg:
            margin += p.tight_aggro_margin
        if street == 3:
            margin += p.river_call_margin
            if tier < p.river_min_tier and tier < p.raise_tier:
                return _FOLD
        eq += (call_down - 1.0) * p.call_down_equity_bonus
        if any_station and bettor >= 0 and prof is not None and prof.station(bettor):
            margin += p.passive_bettor_extra_margin
        if tier >= p.raise_tier + value_shift:
            self.last = "raise"
            return self._bet(spot, p.raise_size, eq=eq)
        if p.size_read > 0.0 and n_opp == 1 and bettor >= 0 and prof is not None and not cheap and 1 <= street <= 3 \
                and board2 is None and not must_use and self.wild_rank < 0 and not self.low:
            sr = self._size_eq(spot, prof, bettor, street, tier)
            if sr is not None:
                eq_r, w = sr
                if eq_r >= p.size_read_raise and tier >= 2:
                    self.last = "size_raise"
                    return self._bet(spot, p.raise_size, eq=eq_r)
                gap = (1.0 - w) * (pot_odds + margin - eq) + w * (pot_odds + p.size_read_margin - eq_r)
                if gap <= 0.0:
                    eq_g = (1.0 - w) * eq + w * eq_r
                    self.last = "size_call"
                    if spot.to_call >= p.icm_gate_frac * obs.stacks[spot.me] and \
                            not self._commit_ok(spot, eq_g, spot.to_call):
                        return _FOLD
                    return _CALL
                return _FOLD
        if eq >= pot_odds + margin:
            self.last = "call"
            if spot.to_call >= p.icm_gate_frac * obs.stacks[spot.me] and not self._commit_ok(spot, eq, spot.to_call):
                return _FOLD
            return _CALL
        return _FOLD

    @staticmethod
    def _rank_prior(prof: Profiler, s: int, st: int, b: int, k: float, by_street: bool = False):
        """Seat s's bet of size b as a slice of the population's betting range (size_read_rank), or None."""
        if by_street:
            c = prof.szc[s][st]
            n = sum(c)
        else:
            c, n = prof.size_shares(s)
        pb = POP_BKT[st]
        lo = 0.0
        for j in range(b):
            lo += (c[j] + k * pb[j]) / (n + k)
        hi = lo + (c[b] + k * pb[b]) / (n + k)
        if hi - lo < 1e-6:
            return None
        out = [0.0] * 9
        c0 = 0.0
        for t, q in enumerate(POP_BET[st]):
            c1 = c0 + q
            ov = (c1 if c1 < hi else hi) - (c0 if c0 > lo else lo)
            if ov > 0.0:
                out[t] = ov / (hi - lo)
            c0 = c1
        return out

    def _size_eq(self, spot: Spot, prof: Profiler, bettor: int, street: int, tier: int):
        """(equity against the bettor's read range for a bet of this size, weight) or None (size_read, S12)."""
        p = self.p
        obs = spot.obs
        mine = obs.bets[spot.me]
        bet = obs.bets[bettor]
        if mine > 0:
            b = 5  # a raise of my bet
        else:
            before = spot.pot_total - bet
            b = prof.size_bucket(bet / before if before > 0 else 9.0)
        st = street - 1
        h, n = prof.size_hist(bettor, st, b)
        if p.size_read_pool and n is not None:
            h = [0] * 9
            n = 0
            for st2 in range(3):
                h2, n2 = prof.size_hist(bettor, st2, b)
                if n2:
                    n += n2
                    for t in range(9):
                        h[t] += h2[t]
        prior = SIZE_PRIOR[st][b]
        if p.size_read_rank > 0.0 and b < 5 and n is not None and p.size_read_rank_streets >> st & 1:
            rk = self._rank_prior(prof, bettor, st, b, p.size_read_rank, p.size_read_rank_by_street)
            if rk is not None:
                m = p.size_read_rank_mix
                prior = rk if m >= 1.0 else [m * x + (1.0 - m) * y for x, y in zip(rk, prior)]
        win = SIZE_WIN[st]
        lose = 1.0 - win
        if n is None:  # an oracle's weights
            tot = 0.0
            acc = 0.0
            for t in range(9):
                q = h[t]
                tot += q
                acc += q * (0.5 if t == tier else win if tier > t else lose)
            if tot <= 0.0:
                return None
            return acc / tot, p.size_read
        n0 = p.size_read_n0
        acc = 0.0
        for t in range(9):
            q = h[t] + n0 * prior[t]
            acc += q * (0.5 if t == tier else win if tier > t else lose)
        w = p.size_read
        if p.size_read_evid:
            w *= n / (n + n0)
            if w <= 0.0:
                return None
        return acc / (n + n0), w

    def _cheap(self, spot: Spot, tier: int, eq: float, wet: bool) -> Action:
        p = self.p
        if spot.to_call == 0:
            if tier >= p.cheap_value_tier:
                return self._bet(spot, p.value_size_wet if wet else p.value_size_dry)
            return _CHECK
        if tier >= p.value_tier and eq >= spot.pot_odds:
            return _CALL
        return _FOLD


def _draw_outs(flush_draw: bool, fsuit: int, oesd: bool, gutshot: bool, completers: int, dead, visible,
               flush_outs: int = 9) -> int:
    """Rule-of-thumb outs (9 flush, 8 open-ender, 4 gutshot, overlaps removed) minus the dead cards among them;
    `flush_outs` 5 on a short deck."""
    outs = 0
    if flush_draw:
        fd = flush_outs
        if dead:
            for c in dead:
                if (c & 3) == fsuit and c not in visible:
                    fd -= 1
        outs += fd if fd > 0 else 0
    if oesd or gutshot:
        sd = (8 if oesd else 4) - (2 if (flush_draw and oesd) else 1 if flush_draw else 0)
        if dead:
            for c in dead:
                if completers >> (c >> 2) & 1 and c not in visible:
                    sd -= 1
        outs += sd if sd > 0 else 0
    return outs


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
