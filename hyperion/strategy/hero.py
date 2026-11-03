"""Hero: the bot. Composes profiler + preflop charts + push/fold + postflop rules behind SafeBot.

    Hero()            full bot, SafeBot inside (Hero.safe holds the telemetry)
    Hero.cheap()      the 15-minute fallback: push/fold + tight preflop, no reads, no ICM
    make_bot()        for the simulator registry

Every tunable number lives in Config (and the per-module *Params it holds). Decision-time work is
one Spot, one profiler update, and one module call. ICM is a per-hand value curve computed in
hand_end / new_table from `icm_me` (my Malmuth-Harville points only: O(n) and exact for linear payouts,
a 2^(n-1) forward pass otherwise), ~30 us per curve on the default payouts.

Variants are configured once per table from Rules (new_table) and read per decision from
Observation.extras; every default is the plain game:
  tables       `tables.tables_for(rules)`: tables/variants/<name>/ when the hole-card count, the deck or
               the showdown rule differ from hold'em and the catalog has a matching set; a rank remap
               (permuted ranks) keeps the default tables; a 3/4-card game without a set plays from the
               best-two class plus tag bonuses, one position tighter
  hand class   two cards: the 169 label (mirrored for lowball, a wild + x reads as the pair of x);
               three or four cards: `tablegen.hole_label` ('AKs+l'), the key of the variant tables
  postflop     keep-all and must-use-two reads for extra hole cards, lowball and wild reads, dead cards
               from exposed_card, both boards of two_boards, value thresholds up before a swap street
  payoff       bounty: expected extra chips in every pot we win (Spot.bounty_bonus); knockout bounty:
               the house points for busting a covered opponent in every all-in EV (Spot.ko_points)
  decisions    variant_decide: discard (keep the best two by the flop read, or by preflop rank before
               the flop), swap (keep made hands and draws, replace the lowest dead card), buy_card
               (when the price is at most a tenth of the stack), bid (the auction: the price at which winning
               and losing the third card come out level, from tables/auction_bid.json), keep (deal 5 keep 2:
               the best pair by the flop read, every revealed discard and our own as dead cards)
  dead cards   deal5_keep2's revealed discards (obs.extras['revealed']) come off the postflop draw outs
"""
from __future__ import annotations

import gc
from dataclasses import dataclass, field, replace
from functools import lru_cache
from math import erf, sqrt

from ..core.cards import hole_class, is_identity_order, remap
from ..core.eval import max_cards, warm
from ..core.types import RANKS, Action, ActionKind, HandResult, Observation, Rules
from ..tablegen import hole_label
from .exploit import Exploit, ExploitParams, ShippedExploitParams
from . import known as _known
from .known import ladder as known_ladder
from .postflop import TIER_EQUITY, Postflop, PostflopParams
from .preflop import Preflop, PreflopParams
from .profiler import Profiler
from .pushfold import PushFold, PushFoldParams
from .safe import SafeBot, safe_action
from .spot import Spot, history_explains_bets, history_from_bets
from .tables import CLASSES, Tables, load as load_tables, tables_for

_CHECK = Action(ActionKind.CHECK)
_FOLD = Action(ActionKind.FOLD)
PLAIN_NAMES = ("", "holdem", "hold'em", "plain", "nlhe", "default")  # rules.extras["variant"] values that are no twist

ICM_BUCKETS = 100  # default Config.icm_buckets: opponents' stacks are rounded to 1/100 of the chips in play before the (memoised) exact ICM call
ICM_ME_SUBDIV = 4  # default Config.icm_me_subdiv: my own units are chosen so my *share* of the chips is kept, to 1/4 of an opponent unit


# The collector and the tables (backlog R2, docs/drills/climb/r2-log.md). gc.freeze() takes every object the collector
# tracks out of its reach, so no full collection over the tables lands inside a timed act(). A frozen object is never
# collected, though: one that dies later in a reference cycle stays in memory for good. One bot object for many tables,
# a fresh one per table in one process (an earlier table's bot), or a sandbox that imports this package afresh per table
# (the whole earlier copy, 31 MB a table) all leave such objects behind. So the freezes first unfreeze and collect: at
# import always (setup time, ~10-20 ms), at a table start one time in REFREEZE_TABLES (a full collection is ~10-20 ms,
# which a kit with no table-start hook pays inside the table's first decision); the other table starts only freeze.
REFREEZE_TABLES = 32  # Hero table starts between full collections (16 tables of the composite, which holds two Heroes)
_table_starts = 0


def refreeze(collect: bool = True) -> None:
    """gc.freeze(), after gc.unfreeze() and a full gc.collect() when `collect` (the block above)."""
    if collect:
        gc.unfreeze()
        gc.collect()
    gc.freeze()


def table_freeze() -> None:
    """HeroCore.new_table's freeze: a full collection first one time in REFREEZE_TABLES."""
    global _table_starts
    _table_starts += 1
    refreeze(_table_starts % REFREEZE_TABLES == 0)


def _linear_step(pays) -> float | None:
    """The constant drop per place when the payouts in play are linear (8, 7, ..., 1 is), else None."""
    if len(pays) < 2:
        return 0.0
    d = pays[0] - pays[1]
    for p in range(1, len(pays) - 1):
        if abs(pays[p] - pays[p + 1] - d) > 1e-9:
            return None
    return d


def icm_me(stacks, me: int, payouts) -> float:
    """My Malmuth-Harville points, exact, without computing anyone else's.

    Linear payouts (the default 8..1): under Malmuth-Harville (a Plackett-Luce ranking) the chance that j
    finishes above me is s_j / (s_me + s_j), so E[place] = 1 + sum_j s_j / (s_me + s_j) and my points are
    pay_1 - step * sum_j s_j / (s_me + s_j): O(n), about 2 us for eight seats.
    Other payouts: a forward pass over the sets of opponents who can finish above me (2^(n-1) sets, each
    reached with the probability that exactly those players took the top places), adding my chance to take
    the next place times its payout: ~900 steps for eight seats instead of the full recursion's ~16,000."""
    mine = stacks[me]
    if mine <= 0:
        return 0.0
    opp = [s for i, s in enumerate(stacks) if i != me and s > 0]
    k = len(opp) + 1
    pays = [float(x) for x in payouts[:k]] + [0.0] * max(0, k - len(payouts))
    if k == 1:
        return pays[0]
    step = _linear_step(pays)
    if step is not None:
        acc = 0.0
        for s in opp:
            acc += s / (mine + s)
        return pays[0] - step * acc
    m = len(opp)
    total = float(mine + sum(opp))
    size, low, prev, cnt, succ = _icm_plan(m)
    dp = [0.0] * size
    held = [0.0] * size
    dp[0] = 1.0
    out = 0.0
    for mask in range(size):
        if mask:
            held[mask] = held[prev[mask]] + opp[low[mask]]
        pr = dp[mask]
        if pr == 0.0:
            continue
        rem = total - held[mask]
        out += pr * mine / rem * pays[cnt[mask]]
        q = pr / rem
        for nb, j in succ[mask]:
            dp[nb] += q * opp[j]
    return out


# The forward pass's bookkeeping depends only on the number of opponents m, so it is built once per m (here, at import:
# never inside a timed act()): for each subset mask, its lowest member, the mask without it, its size, and the masks it
# extends to with their new member, in the order the pass adds them. Same float operations in the same order as the
# loop it replaced (`_icm_me_ref`, kept for the test that they agree exactly), about half the time (R1: 49 -> 25 us at
# eight seats; docs/drills/r1-timing-log.md).
_ICM_PLANS: dict = {}


def _icm_plan(m: int):
    p = _ICM_PLANS.get(m)
    if p is None:
        size = 1 << m
        low, prev, cnt, succ = [0] * size, [0] * size, [0] * size, [()] * size
        for mask in range(size):
            if mask:
                lb = mask & -mask
                low[mask] = lb.bit_length() - 1
                prev[mask] = mask ^ lb
                cnt[mask] = cnt[mask ^ lb] + 1
            succ[mask] = tuple((mask | (1 << j), j) for j in range(m) if not mask & (1 << j))
        p = _ICM_PLANS[m] = (size, low, prev, cnt, succ)
    return p


for _m in range(1, 12):  # up to twelve seats
    _icm_plan(_m)


def _icm_me_ref(stacks, me: int, payouts) -> float:
    """icm_me's forward pass as first written (one bit test per opponent per subset): the reference the tests hold
    icm_me to, bit for bit."""
    mine = stacks[me]
    if mine <= 0:
        return 0.0
    opp = [s for i, s in enumerate(stacks) if i != me and s > 0]
    k = len(opp) + 1
    pays = [float(x) for x in payouts[:k]] + [0.0] * max(0, k - len(payouts))
    if k == 1:
        return pays[0]
    step = _linear_step(pays)
    if step is not None:
        acc = 0.0
        for s in opp:
            acc += s / (mine + s)
        return pays[0] - step * acc
    m = len(opp)
    total = float(mine + sum(opp))
    size = 1 << m
    dp = [0.0] * size
    held = [0.0] * size
    dp[0] = 1.0
    out = 0.0
    for mask, (j, prev, cnt, succ) in enumerate(_subset_plan(m)):
        if mask:
            held[mask] = held[prev] + opp[j]
        pr = dp[mask]
        if pr == 0.0:
            continue
        rem = total - held[mask]
        out += pr * mine / rem * pays[cnt]
        q = pr / rem
        for t, k in succ:
            dp[t] += q * opp[k]
    return out


_PLANS: dict = {}


def _subset_plan(m: int) -> list:
    """For each mask of m opponents: (its lowest seat index, the mask without it, its size, and the (mask | 1 << k, k)
    for every k outside it, k ascending). icm_me walks this instead of testing bits: the same additions in the same
    order, so the same floats, about 1.6x faster (built once per m, at import for m <= 9)."""
    plan = _PLANS.get(m)
    if plan is None:
        plan = []
        for mask in range(1 << m):
            low = mask & -mask
            plan.append((low.bit_length() - 1 if mask else -1, mask ^ low, bin(mask).count("1"),
                         tuple((mask | 1 << k, k) for k in range(m) if not mask >> k & 1)))
        _PLANS[m] = plan
    return plan


for _m in range(1, 10):  # up to ten seats
    _subset_plan(_m)


def _cap_value(stacks, me: int, pays, cap) -> float:
    """Linear payouts near the hand cap: pay_1 - step * sum_j [lam * s_j / (s + s_j) + (1 - lam) * Phi((s_j - s) / sigma)]."""
    lam, sigma = cap
    mine = stacks[me]
    step = pays[0] - pays[1] if len(pays) > 1 else 0.0
    acc = 0.0
    inv = 1.0 / (sigma * 1.4142135623730951) if sigma > 0 else 0.0
    for i, sj in enumerate(stacks):
        if i != me and sj > 0:
            if inv:
                above = 0.5 * (1.0 + erf((sj - mine) * inv))
            else:  # the last hand: the cap's ranking is the chip ranking
                above = 1.0 if sj > mine else 0.5 if sj == mine else 0.0
            acc += lam * sj / (mine + sj) + (1.0 - lam) * above
    return pays[0] - step * acc


@lru_cache(maxsize=1 << 15)
def _icm_bucketed(key: tuple, me: int, payouts: tuple) -> float:
    return icm_me(key, me, payouts)


def icm_value(stacks, me: int, payouts, buckets: int = ICM_BUCKETS, subdiv: int = ICM_ME_SUBDIV) -> float:
    """My exact ICM points for `stacks`. Linear payouts are exact and O(n) (icm_me), so no rounding; otherwise
    memoised on a rounded key: opponents are rounded to 1/buckets of the chips in play (their mutual proportions
    barely move my equity), and my own entry is set so that my share of the rounded total equals my true share,
    because that share is what the curve reads."""
    k = 0
    for s in stacks:
        if s > 0:
            k += 1
    if _linear_step([float(x) for x in payouts[:k]]) is not None and len(payouts) >= k:
        return icm_me(stacks, me, payouts)
    return _icm_rounded(stacks, me, tuple(float(p) for p in payouts), buckets, subdiv)


def _icm_rounded(stacks, me: int, pays_t: tuple, buckets: int, subdiv: int) -> float:
    """icm_value's non-linear case: the memoised exact value on the rounded key (`pays_t` the payouts as floats)."""
    total = 0.0
    for s in stacks:
        if s > 0:
            total += s
    unit = total / buckets if total > 0 else 1.0
    sub = subdiv
    key = [0] * len(stacks)
    others = 0
    for i, s in enumerate(stacks):
        if i != me and s > 0:
            u = sub * max(1, int(s / unit + 0.5))
            key[i] = u
            others += u
    mine = stacks[me]
    if mine > 0:
        rest = total - mine
        key[me] = max(1, int(mine / rest * others + 0.5)) if rest > 0 and others > 0 else sub * buckets
    return _icm_bucketed(tuple(key), me, pays_t)


@dataclass
class Config:
    preflop: PreflopParams = field(default_factory=PreflopParams)
    pushfold: PushFoldParams = field(default_factory=PushFoldParams)
    postflop: PostflopParams = field(default_factory=PostflopParams)
    # dead and timing-out seats (hyperion/strategy/exploit.py): its own reads, and overrides of the modules' action in
    # a few spots. Shipped on: bet when checked to by folders, the dead-seat steal, the steal by fold reads (exploit
    # pass, docs/decisions.md); exploit.bet_checked / steal false and steal_min_fold 0 give the behaviour of 7e51197
    exploit: ExploitParams = field(default_factory=ShippedExploitParams)
    profiler_prior_n: float = 2.0
    profiler_blend_n: float = 8.0  # dials reach half strength after this many observed actions
    profiler_dial_strength: float = 1.0  # 0 = read opponents but never act on it
    profiler_calldown_slope: float = -0.8  # unknown archetype: call_down_mult = 1.4 + slope * aggression
    # archetype flags fire after these sample sizes (the profiler's constructor knobs, exposed for the windows loop)
    profiler_dead_after: int = 5  # faced this many bets without ever calling or raising: a dead seat
    profiler_station_after: int = 10
    profiler_nit_after: int = 20
    profiler_maniac_after: int = 10
    profiler_random_after: int = 15
    use_profiler: bool = True
    use_icm: bool = True
    # early-game risk-of-ruin cap: while my stack is deep (linear from ror_from_bb to full at ror_full_bb) and the
    # hand number is at most ror_hands, any stack-off (a call or commitment of half my stack or more, preflop or
    # postflop) needs ror_margin more equity. The option to wait for a better spot is worth most early. 0 = off.
    ror_margin: float = 0.0
    ror_from_bb: float = 30.0
    ror_full_bb: float = 80.0
    ror_hands: int = 75
    # the hand cap: survivors are ranked by chips at the last hand, so near it chips matter by rank more than by
    # share. With linear payouts my points are pay_1 - step * sum_j P(j finishes above me); the curve blends
    # Malmuth-Harville's s_j / (s_me + s_j) with the cap's Phi((s_j - s_me) / sigma), where sigma^2 is twice the sum
    # over the remaining hands of (cap_vol_bb * big blind)^2 (a pair of stacks' variance to the cap) and the weight
    # on Malmuth-Harville is sigma^2 / (sigma^2 + average stack^2). Early on it is ~1; it falls in the last levels.
    # 0 = off (pure Malmuth-Harville).
    cap_vol_bb: float = 0.0
    # my-stack multiples the ICM curve samples. Dense around 1x: with samples only at 0.5/1/1.5 the piecewise-linear
    # curve had a kink at my stack that priced a +-7% flip at 57% equity where exact ICM says 47%.
    icm_ratios: tuple = (0.0, 0.25, 0.5, 0.75, 0.9, 1.0, 1.1, 1.25, 1.5, 2.0, 3.0, 4.0, 6.0)
    # non-linear payouts with this many players alive: the exact forward pass costs ~50 us per point at eight seats,
    # so the curve samples the thinner set below (linear payouts, the default, are O(n) and always use icm_ratios)
    icm_many_alive: int = 7
    icm_ratios_many: tuple = (0.0, 0.5, 0.9, 1.0, 1.1, 1.5, 2.0, 3.0, 6.0)
    icm_buckets: int = ICM_BUCKETS  # opponents' stacks rounded to 1/this of the chips in play before exact ICM
    icm_me_subdiv: int = ICM_ME_SUBDIV  # my own rounding, in fractions of an opponent unit
    # 3/4-card games without a variant table set: best-two class plus these bonuses per pairing / suited extra card
    label_bonus_pair: float = 0.04
    label_bonus_suited: float = 0.02
    label_open_step: int = 1  # ... and this many positions tighter on opens
    # the auction entry's bid (variant_decide 'bid'): d x pot_eff / (1 - d), d from tables/auction_bid.json by flop read
    # and bidders; pot_eff = pot x (1 + auction_implied x min(stack / pot, auction_spr_cap)) for the betting still to
    # come; capped at auction_stack_frac of the stack and auction_pot_frac of the pot
    auction_implied: float = 0.05
    auction_spr_cap: float = 4.0
    auction_stack_frac: float = 0.33
    auction_pot_frac: float = 0.75
    # deal5_keep2: everyone kept their best two of five on this flop, so a made hand is worth less than its board-relative
    # tier says: postflop value thresholds this many tiers up (as before a swap street)
    keep_value_shift: int = 1
    # toss_or_holdem (and the blind discard): three hole cards, one tossed face up on the flop (obs.extras['discards'],
    # {seat: card}). toss_dead: every face-up toss, ours included, is a dead card: off the postflop draw outs, and the
    # toss itself (variant_decide 'discard') reads the tosses made before ours (the prompt's 'discards') and the card it
    # throws as dead. toss_value_shift: everyone kept their best two of three on this flop, so postflop value
    # thresholds this many tiers up (keep_value_shift's reason, a third as strong). Both off: the play before 2026-11-01
    toss_dead: bool = False
    toss_value_shift: int = 0
    # ... and toss_call_shift: facing a bet on those tables, the made hand's equity read this many tiers lower (the
    # call side of toss_value_shift, as keep_call_shift is of keep_value_shift on deal5_keep2). 0 = off
    toss_call_shift: int = 0
    # bounty (MIT 2025: win a pot holding the bounty rank, in hand or on the board, and the house pays (ratio - 1) x the
    # net win + constant more). bounty_exact: the net win is the others' chips in the pot (not ours from earlier
    # streets), and every all-in EV also prices the bounty on the chips a caller adds (Spot.bounty_k).
    # bounty_call_scale: the bounty's share in the pot odds of a call (1 = as before; 0 = calls priced without it).
    # bounty_bet_frac: with the bounty hit, nothing to call and at most three players in, bet this share of the pot
    # where the postflop rules would check (0 = off): the bounty pays for winning the pot, so fold equity is worth 1.5x
    bounty_exact: bool = False
    bounty_call_scale: float = 1.0
    bounty_bet_frac: float = 0.0
    # short deck (6 to ace): the postflop read knows the 36-card deck: A-6-7-8-9 is a straight (made and drawn to),
    # no wheel, a flush draw has five outs, and an out is worth 1.45x the rule of 4 and 2 (31 unseen cards). Off: the
    # hold'em read with the flush-over-full-house tier (the play before 2026-11-01)
    short_deck_read: bool = False
    # the variant table set by directory name under tables/variants/ (its meta.json card rules must match the table's
    # rules, else the usual set): "short_deck_v2" is the short deck regenerated with its own showdown (A-6-7-8-9, flush
    # over full house), more samples and a multiway push/fold solve. "" = the set extras["variant"] names
    variant_tables: str = ""
    # PreflopParams overrides for a catalogued twist's tables only (rules.extras["variant"] names one, not plain
    # hold'em; not fixed limit or must-use-k, where they measured worse): e.g. {"call_raise_frac": 0.15}. On F, Hero
    # plays every preflop decision of the 14 Hero tables (short deck, three hole cards ...) and few elsewhere; this
    # reaches the first and none of the second. {} = off
    variant_preflop: dict = field(default_factory=dict)
    # PushFoldParams overrides on the same tables (the same gate): the push/fold zone's decisions, e.g. calling a
    # shove at 10 bb or less ({"call_equity_margin": 0.05}); deeper shove calls are the preflop module's
    # (variant_preflop's shove_eq_margin, shove_range_mult). Decision-time fields only: the solved tables and the
    # multiway switch are the table set's. {} = off
    variant_pushfold: dict = field(default_factory=dict)
    # PreflopParams overrides by the table's rule, for the twist tables variant_preflop leaves out ("must_use":
    # Omaha-style must-use-k, "fixedlimit", "lowball": in place of the hold'em params) and, on top of variant_preflop,
    # for a short deck ("deck": ranks removed), two boards ("boards"), wild cards ("wild"); the first that applies, in
    # that order. E.g. {"must_use": {"call_raise_frac": 0.15}}. Measured against opponents that play the twist (the
    # generic aware field), where variant_preflop was measured against twist-blind ones. {} = off
    variant_preflop_ex: dict = field(default_factory=dict)
    # boards longer than five cards (river_of_blood's run streets, or any rule that deals past the river). long_board:
    # read them (core.eval.evaluate_many for any number of cards, never a table built in a decision; "playing the
    # board" against the board's own best five; draws and outs while another card may come), and play a street that
    # may not be the last as a turn (`long_to_come` cards to come, rule of 2 per out per card) and the last one as a
    # river. Under `run_until_black` (rules.extras) a red last card on a board of five or more means another card
    # comes. long_value_per_card: postflop value and raise thresholds this many tiers up per board card past five
    # (every hand at the table uses the extra cards); long_call_per_card: facing a bet, the made hand's equity is read
    # this many tiers lower per board card past five. Off: past 8 cards check or fold, a sixth board card is read as
    # a river with no draws, a red river as the last street (the play before 2026-11-02)
    long_board: bool = False
    long_to_come: int = 1
    long_value_per_card: int = 0
    long_call_per_card: int = 0
    # deal5_keep2: facing a bet, the made hand's equity read this many tiers lower (everyone kept their best two of
    # five on this flop: keep_value_shift's reason, applied to calls; keep_value_shift moves only bets and raises). 0 = off
    keep_call_shift: int = 0
    # three or more hole cards dealt and still held after the flop (three_card_keep: all kept; Omaha: must use two; not a
    # third card bought, as in bonus_card and auction, where it measured +0.12 and -0.07 apart): facing a bet,
    # the made hand's equity read this many tiers lower (every hand at the table is stronger; read_multi already takes
    # multi_tier_penalty off pairs and two pairs for bets and calls alike). multi_call_shift for hands kept whole,
    # mu_call_shift for must-use-k. 0 = off
    multi_call_shift: int = 0
    mu_call_shift: int = 0
    # ... and the bet / raise side there: value, big-value and raise thresholds this many tiers up. 0 = off
    multi_value_shift: int = 0
    mu_value_shift: int = 0
    # ... and by the table's rule (variant_preflop_ex's gates: "must_use", "fixedlimit", "lowball", "deck", "boards",
    # "wild"), added to the above, e.g. {"deck": 1}. {} = off
    call_shift_ex: dict = field(default_factory=dict)
    # two-card twists with no variant table set (lowball, wild cards, hi-lo, any new showdown): read each hand as its
    # hold'em twin from the variant's own preflop table (tables/generic/, hyperion/sim/generic.py's prepare: the value
    # share of every class dealt and scored through the variant's hooks), the hold'em class at the same combo
    # percentile, in place of the hand-written lowball mirror and wild map; used when the twins move hands by at least
    # this mean percentile (tables.twin_shift: a prepared table of a twist with hold'em's showdown moves them 0.015-0.03
    # by sampling noise alone). 0 = off
    twin_preflop: float = 0.0
    # ... also on a two-card twist that has a variant table set (short deck): its twins from the prepared table in place
    # of the set (the hold'em tables, read through the twins). False = the set, as before
    twin_force: bool = False
    # three or four hole cards (Omaha, the three-card games): the variant's label tables re-cut from its own prepared
    # table (tables.recut_label_tables: rank by the doc's value share, equity the set's distribution at that rank),
    # used when the re-cut moves labels by at least this mean percentile (Omaha's catalog set, 300 samples a label,
    # 0.17; the three-card sets 0.06-0.08). 0 = off
    twin_multi: float = 0.0
    # known cards (V-h, hyperion/strategy/known.py): cards an opponent is known to hold, from obs.extras["known"]
    # ({seat: cards}; a card may be ours too, as Chain Hold'em's shared links are) and obs.extras["exposed"]. A comma
    # list of the parts on, "" = off (the play before 2026-11-02: exposed cards only, as dead cards and range reads):
    #   pre   heads-up before the flop (one opponent left in the hand, known to hold cards): the hand is read as the
    #         class whose heads-up equity is ours against him (known.equity: a shared card counts for both hands, his
    #         exposed cards are his), and the exposed-card range reads stand down for that decision
    #   post  after the flop: against each opponent in the hand who shares cards with us, the hand is read with the
    #         shared cards on the board (they make his hand as much as ours); the lowest read over the opponents (the
    #         plain read for those who share nothing) is the hand's
    # With it on, every known card that is not ours comes off the draw outs (as exposed cards always did)
    known_cards: str = ""
    cheap: bool = False  # cheapest paths everywhere (also what panic mode switches on)
    deadline_ms: float = 0.5
    panic_after: int = 5
    panic_rate: float = 0.02  # ... and at least this share of calls overran
    # SafeBot's governor (hyperion/strategy/safe.py, backlog R1; all off = the single cliff): Hero has no intermediate
    # levels, so a ladder is the cliff; window and recover still apply
    panic_window: int = 0
    panic_ladder: bool = False
    panic_recover: int = 0
    panic_backoff: float = 2.0
    seed: int | None = None  # postflop frequency RNG; None = nondeterministic

    @staticmethod
    def cheap_config() -> "Config":
        return Config(cheap=True, use_profiler=False, use_icm=False)


def config_from_dict(overrides: dict | None, seed: int | None = None) -> Config:
    """A Config with dotted overrides applied: {"preflop.three_bet_frac": 0.06, "postflop.value_tier": 5,
    "pushfold.threshold_bb": 10, "use_profiler": false}. Dict-valued fields (open_frac) are merged by key.
    This is how the runner and tools/sweep.py reach the levers without touching code."""
    cfg = Config(seed=seed)
    for key, val in (overrides or {}).items():
        parts = key.split(".")
        target = cfg
        for part in parts[:-1]:
            target = getattr(target, part)
        leaf = parts[-1]
        cur = getattr(target, leaf)
        if isinstance(cur, dict) and isinstance(val, dict):
            cur = dict(cur)
            cur.update({int(k) if str(k).lstrip("-").isdigit() else k: v for k, v in val.items()})
            val = cur
        elif isinstance(cur, tuple) and isinstance(val, list):
            val = tuple(tuple(x) if isinstance(x, list) else x for x in val)
        setattr(target, leaf, val)
    return cfg


class IcmCurve:
    """V(x): my expected points as a function of my stack x, chips moving to/from the field pro rata.
    Sampled at a few multiples of my current stack; linear between samples. V(0) is the payout for
    busting right now (the ICM function reports 0 for a busted seat because its points are fixed)."""

    __slots__ = ("xs", "vs", "n")
    points = True  # values are tournament points: knockout points add to them directly

    def __init__(self):
        self.xs = [0.0, 1.0]
        self.vs = [0.0, 1.0]
        self.n = 2

    def compute(self, stacks, me: int, payouts, ratios, buckets: int = ICM_BUCKETS, subdiv: int = ICM_ME_SUBDIV,
                cap=None) -> None:
        """`cap` = (weight on Malmuth-Harville, sigma of a stack pair to the hand cap), linear payouts only."""
        total = float(sum(s for s in stacks if s > 0))
        base = float(stacks[me])
        alive = sum(1 for s in stacks if s > 0)
        pays = list(payouts) + [0.0] * max(0, alive - len(payouts))
        bust_value = float(pays[alive - 1]) if alive >= 1 else 0.0
        if total <= 0 or base <= 0:
            self.xs, self.vs, self.n = [0.0, 1.0], [bust_value, bust_value], 2
            return
        others = total - base
        xs, vs = [], []
        points = [base * r for r in ratios]
        if cap is not None and others > 0:
            # near the cap my points step where I pass a stack (others scale pro rata): sample both sides of each step
            d = max(1.0, 0.25 * cap[1])
            for s in range(len(stacks)):
                if s != me and stacks[s] > 0:
                    t = stacks[s] * total / (others + stacks[s])
                    points.append(t - d)
                    points.append(t + d)
            points = sorted({x for x in points if x >= 0.0})
        lin: dict = {}  # players with chips -> (their payouts as floats, the linear step) or None: icm_value's test
        pays_t = None
        for x in points:
            if x > total:
                x = total
            if xs and x <= xs[-1]:  # a repeat (several multiples past every chip): dropped before it is priced
                continue
            if x <= 0:
                v = bust_value
            else:
                if others > 0:
                    scale = (total - x) / others
                    st = [x if s == me else (stacks[s] * scale if stacks[s] > 0 else 0) for s in range(len(stacks))]
                else:
                    st = [x if s == me else 0 for s in range(len(stacks))]
                if cap is not None:
                    v = _cap_value(st, me, pays, cap)
                else:
                    # icm_value(st, me, pays, buckets, subdiv), with its per-call payout tests done once per k
                    opp = [c for i, c in enumerate(st) if i != me and c > 0]
                    k = len(opp) + 1
                    lk = lin.get(k, False)
                    if lk is False:
                        pk = [float(p) for p in pays[:k]]
                        step = _linear_step(pk)
                        lk = lin[k] = (pk, step) if step is not None and len(pays) >= k else None
                    if lk is not None:  # icm_me's linear branch: the same sum in the same order
                        pk, step = lk
                        if k == 1:
                            v = pk[0]
                        else:
                            acc = 0.0
                            for c in opp:
                                acc += c / (x + c)
                            v = pk[0] - step * acc
                    else:
                        if pays_t is None:
                            pays_t = tuple(float(p) for p in pays)
                        v = _icm_rounded(st, me, pays_t, buckets, subdiv)
            xs.append(x)
            vs.append(v)
        if xs[-1] < total:  # holding every chip is first place exactly: the curve's ceiling
            xs.append(total)
            vs.append(float(pays[0]))
        if len(xs) < 2:
            xs.append(xs[-1] + 1.0)
            vs.append(vs[-1])
        self.xs, self.vs, self.n = xs, vs, len(xs)

    def linear(self, stacks, me: int, payouts) -> None:
        """Chip-proportional between busting now and holding every chip: the deep-stack stand-in."""
        total = float(sum(s for s in stacks if s > 0))
        alive = sum(1 for s in stacks if s > 0)
        pays = list(payouts) + [0.0] * max(0, alive - len(payouts))
        bust = float(pays[alive - 1]) if alive >= 1 else 0.0
        top = float(pays[0]) if pays else 0.0
        self.xs, self.vs, self.n = [0.0, max(total, 1.0)], [bust, top], 2

    def value(self, x: float) -> float:
        xs, vs = self.xs, self.vs
        if x <= xs[0]:
            return vs[0]
        n = self.n
        i = 1
        while i < n - 1 and xs[i] < x:
            i += 1
        x0, x1 = xs[i - 1], xs[i]
        v0, v1 = vs[i - 1], vs[i]
        if x > x1:  # beyond the last sample (all the chips): nothing more to win
            return v1
        return v0 + (v1 - v0) * (x - x0) / (x1 - x0)


# ---------------------------------------------------------------- class maps for the ranking axis

def mirror_map(rank: dict) -> dict[str, str]:
    """Lowball: the class at the mirrored position of the hold'em order (72o reads as AA, AA as 72o)."""
    order = sorted(CLASSES, key=lambda c: rank[c])
    n = len(order)
    return {order[i]: order[n - 1 - i] for i in range(n)}


def wild_map(wild_rank: int) -> dict[str, str]:
    """Wild cards: a wild with x is at least a pair of x, two wilds are the best pair there is."""
    w = RANKS[wild_rank]
    out = {}
    for c in CLASSES:
        a, b = c[0], c[1]
        if a == w and b == w:
            out[c] = "AA"
        elif a == w:
            out[c] = b + b
        elif b == w:
            out[c] = a + a
        else:
            out[c] = c
    return out


# S12's size read (postflop.size_read_holdem_only): a table is hold'em when only its structure differs (payouts,
# blinds, antes, a straddle, chip-count places at the hand cap); an unknown key in Rules.extras or any other variant
# entry turns the read off
_HOLDEM_EXTRAS = frozenset({"variant", "ante_rule", "cap_places"})
_HOLDEM_VARIANTS = frozenset({None, "top_heavy", "antes_from_level_3", "fast_schedule", "straddle"})


def holdem_table(rules: Rules) -> bool:
    ex = rules.extras or {}
    return (rules.hole_cards == 2 and tuple(rules.board_sizes) == (0, 3, 4, 5) and rules.n_suits == 4
            and not rules.must_use_hole and rules.betting == "nolimit" and is_identity_order(rules)
            and set(ex) <= _HOLDEM_EXTRAS and ex.get("variant") in _HOLDEM_VARIANTS)


# V-f: the one-step twist families that still play ordinary hold'em after the twist (docs/drills/climb/vf-log.md). The
# hold'em-gated gains (S12's size read, S11's probe read and one size, S9's strong-table route) can be carried to a
# family by a dial that lists it (postflop.size_read_twists, postflop.s11_twists, the composite's strong_route_twists).
# A table is in a family when its structure is hold'em (52 cards, board 3/4/5, no-limit, rank order as dealt; two hole
# cards, three only for a face-up discard down to two) and its extras hold that family's keys and nothing else; the
# variant name may be any (tonight's own file names its twist its own way) but not another family's catalog entry.
# Anything else is no family: the gate stays shut
TWIST_FAMILIES: dict = {
    "discard": ({"toss_or_holdem", "three_card_blind_discard"},
                {"discard_street", "discard_face_up", "keep", "blind_discard"}),
    "bounty": ({"bounty"}, {"bounty_ratio", "bounty_constant", "rounds_per_bounty", "bounty_funding"}),
    "knockout": ({"knockout_bounty"}, {"ko_points", "ko_funding"}),
    "buy": ({"bonus_card", "auction"}, {"price_bb", "street", "auction_street", "auction_price", "auction_ties"}),
    "swap": ({"swap_holdem", "swap_one_turn"}, {"swap_p_flop", "swap_p_turn", "swap_street", "swap_count"}),
    "exposed": ({"exposed_card"}, {"exposed_index"}),
}


def twist_families(spec) -> frozenset:
    """A dial's family list ("discard,swap" or a list) as a set; an unknown name is an error, not a silent no-op."""
    if not spec:
        return frozenset()
    names = [x.strip() for x in (spec.split(",") if isinstance(spec, str) else spec) if str(x).strip()]
    bad = [x for x in names if x not in TWIST_FAMILIES]
    if bad:
        raise KeyError(f"unknown twist family {bad[0]!r}; known: {', '.join(TWIST_FAMILIES)}")
    return frozenset(names)


def twist_family(rules: Rules) -> str | None:
    """The one-step twist family of a table that is hold'em but for that twist (TWIST_FAMILIES), or None (hold'em
    itself, or any other table)."""
    ex = rules.extras or {}
    if not (tuple(rules.board_sizes) == (0, 3, 4, 5) and rules.n_suits == 4 and not rules.must_use_hole
            and rules.betting == "nolimit" and is_identity_order(rules)):
        return None
    if "discard_face_up" in ex:
        fam = "discard"
    elif "bounty_ratio" in ex or "bounty_funding" in ex or ex.get("variant") == "bounty":
        fam = "bounty"
    elif "ko_points" in ex:
        fam = "knockout"
    elif "price_bb" in ex or "auction_price" in ex or ex.get("variant") in ("bonus_card", "auction"):
        fam = "buy"
    elif "swap_p_flop" in ex or "swap_p_turn" in ex or "swap_street" in ex:
        fam = "swap"
    elif "exposed_index" in ex or ex.get("variant") == "exposed_card":
        fam = "exposed"
    else:
        return None
    names, keys = TWIST_FAMILIES[fam]
    v = ex.get("variant")
    if v is not None and v not in names and any(v in n for f, (n, _) in TWIST_FAMILIES.items() if f != fam):
        return None
    if not set(ex) <= keys | _HOLDEM_EXTRAS:
        return None
    if fam == "discard":
        ok = rules.hole_cards == 3 and bool(ex.get("discard_face_up")) and int(ex.get("keep", 2) or 2) == 2
    elif fam == "knockout":
        ok = rules.hole_cards == 2 and float(ex.get("ko_points", 0.0) or 0.0) > 0.0
    else:
        ok = rules.hole_cards == 2
    return fam if ok else None


_TWINS: dict = {}  # HeroCore._twins' cache: (variant, extras, hole cards, threshold, tables) -> twin map or None


class HeroCore:
    """The unguarded strategy. Hero wraps it in SafeBot; tests may poke it directly."""

    def __init__(self, config: Config | None = None, tables: Tables | None = None):
        self.cfg = cfg = config or Config()
        self.tables = tables or load_tables(need_hu=True)
        self.prof = Profiler(8, prior_n=cfg.profiler_prior_n, blend_n=cfg.profiler_blend_n,
                             dial_strength=cfg.profiler_dial_strength, calldown_slope=cfg.profiler_calldown_slope,
                             dead_after=cfg.profiler_dead_after, station_after=cfg.profiler_station_after,
                             nit_after=cfg.profiler_nit_after, maniac_after=cfg.profiler_maniac_after,
                             random_after=cfg.profiler_random_after) if cfg.use_profiler else None
        self.preflop = Preflop(cfg.preflop, self.tables)
        self.pushfold = PushFold(cfg.pushfold, self.tables)
        self.postflop = Postflop(cfg.postflop, cfg.seed)
        self.pushfold.pre = self.preflop
        self.preflop.pf = self.pushfold
        self.exploit = Exploit(cfg.exploit) if cfg.exploit.active and not cfg.cheap else None  # cheap: no reads
        if self.prof is not None and self.pushfold.mw is not None:
            self.prof.call_prior = self.pushfold.call_prior  # shove calls are read against a solved caller's
        if self.prof is not None and (cfg.postflop.size_read > 0.0 or cfg.postflop.xr_shift):
            self.prof.track_s12 = True  # S12 reads: count bet sizes, shown tiers and check-raises (off: no cost)
        self._base = (self.preflop, self.pushfold)
        self._modules: dict = {}  # (tables dir, scheme) -> (Preflop, PushFold) built for a variant set
        self.curve = IcmCurve()
        if cfg.use_icm:
            self.pushfold.curve = self.curve
            self.preflop.curve = self.curve
            self.postflop.curve = self.curve
        self.panic = False
        self.rules = Rules()
        self.seat = 0
        self.n = 8
        self._remap = None
        self.hand_no = -1
        self.hand_start = None  # chips per seat at the start of the current hand
        self.last_stacks = None
        self.payouts = self.rules.payouts
        self.last_path = ""  # which module made the last decision (diagnostics only)
        self.active = self.tables  # the table set in play
        self._label = False  # hands are labelled by tablegen.hole_label (3 or 4 hole cards)
        self._cls_map = None  # 169 -> 169 remap (lowball mirror, wild cards)
        self._must_use = 0
        self._bounty = None  # (ratio, constant) when a bounty variant is on
        self._ko = 0.0  # knockout points per bust
        self._swap_street = 0
        self._auction = None  # the auction entry's bid table (tables/auction_bid.json), loaded when the rules name it
        # deal5_keep2 (rules.extras discard_count): obs.extras["revealed"] discards are dead cards. Scoped to the rule:
        # the held-out showtime uses the same key for folded hands, and the held-out set is not tuned on
        self._revealed_dead = False
        self._toss = False  # three hole cards and a face-up toss (toss_or_holdem, three_card_blind_discard)
        self._gate = None  # the twist table's rule for the *_ex dials (_configure)
        self._run = False  # rules.extras["run_until_black"] (river_of_blood): a red last card deals another street
        self._pre_aggr = False  # my last preflop action this hand was a raise nobody re-raised (when history is absent)
        self.inferred = 0  # decisions whose betting state came from the bets because the history could not explain it
        # known cards (Config.known_cards): which parts are on, and the class ladder the heads-up equity is read
        # through (equities ascending, their classes), built per table set in _configure
        self._known_pre = self._known_post = False
        self._known_ladder = None
        self.known_pre_n = self.known_post_n = 0  # decisions the known cards reached (diagnostics)

    # ------------------------------------------------------------------ Bot protocol
    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.rules = rules
        self.seat = seat
        self.n = n_players
        self.payouts = rules.payouts
        self._remap = None if is_identity_order(rules) else rules
        self.hand_no = -1
        self.hand_start = None
        self.last_stacks = [rules.starting_stack] * n_players
        self.panic = False
        self._pre_aggr = False  # (the first act of the table resets it too: hand_no -1 above)
        self._cap_var = None
        if self.cfg.cap_vol_bb > 0.0 and rules.max_hands > 0:
            # suffix sums of big blind^2 over the hands still to play: var[h] = sum_{t >= h} bb_t^2
            var = [0.0] * (rules.max_hands + 1)
            for t in range(rules.max_hands - 1, -1, -1):
                var[t] = var[t + 1] + float(rules.blinds_at(t)[1]) ** 2
            self._cap_var = var
        # the evaluator tables these rules need (8 cards only for three kept hole cards or a bought card: 60 ms), here
        # and never inside a timed act(); a count they miss is still exact (eval.max_cards)
        warm(max_cards(rules))
        self._configure(rules)
        if self.prof is not None:
            self.prof.reset(n_players, seat)
        if self.exploit is not None:
            self.exploit.new_table(n_players, seat)
        self._curve_todo = None
        if self.cfg.use_icm:
            self._curve(self.last_stacks, 0)
        table_freeze()  # tables and evaluator dicts leave the collector's reach: no gen-2 pause mid-decision

    def _configure(self, rules: Rules) -> None:
        """Per-table variant wiring from Rules: table set, class map, postflop mode, payoff terms."""
        cfg = self.cfg
        ex = rules.extras or {}
        self._must_use = int(rules.must_use_hole or 0)
        self._bounty = None
        if "bounty_ratio" in ex or "bounty_funding" in ex or ex.get("variant") == "bounty":
            self._bounty = (float(ex.get("bounty_ratio", 1.5)), float(ex.get("bounty_constant", 10)))
        self._ko = float(ex.get("ko_points", 0.0) or 0.0)
        self._swap_street = int(ex.get("swap_street", 0) or 0)
        if self._auction is None and (ex.get("variant") == "auction" or "auction_price" in ex):
            self._auction = auction_table()
        self._revealed_dead = bool(ex.get("discard_count"))
        self._toss = bool(ex.get("discard_face_up")) and not ex.get("discard_count") and rules.hole_cards == 3
        self._run = bool(ex.get("run_until_black"))
        low = bool(ex.get("lowball"))
        wild = ex.get("wild_rank", None)
        wild_c = int(rules.rank_order[int(wild)]) if wild is not None else -1
        fof = ex.get("category_order") == "flush_over_full_house"
        short = cfg.short_deck_read and set(ex.get("removed_ranks") or ()) == {0, 1, 2, 3}
        self.postflop.set_mode(low=low, wild_rank=wild_c, flush_over_full=fof, short=short)
        self.postflop.family = twist_family(rules)  # (before holdem: the setter picks the params from both)
        self.postflop.holdem = holdem_table(rules)
        self._cls_map = mirror_map(self.tables.rank) if low else wild_map(wild_c) if wild_c >= 0 else None
        t = tables_for(rules, self.tables, name=cfg.variant_tables or None)
        if cfg.twin_preflop > 0.0 and rules.hole_cards == 2 and self._remap is None \
                and (t is self.tables or (cfg.twin_force and t.scheme == "169")):
            tm = self._twins(rules)
            if tm is not None:
                self._cls_map = tm
                t = self.tables
        if t is self.tables:
            pre, pf = self._base
            self._label = False
        else:
            key = (t.dir, t.scheme, t.source)
            mods = self._modules.get(key)
            if mods is None:
                if t.scheme == "169":
                    pre, pf = Preflop(cfg.preflop, t), PushFold(cfg.pushfold, t)
                else:
                    params = cfg.preflop
                    if t.source.endswith("+labelview"):  # no variant set: best-two class, one position tighter
                        t.rank.bonus_p = t.equity.bonus_p = cfg.label_bonus_pair
                        t.rank.bonus_s = t.equity.bonus_s = cfg.label_bonus_suited
                        params = replace(params, open_step=params.open_step + cfg.label_open_step)
                    pre, pf = Preflop(params, t), self._base[1].with_tables(t)
                mods = self._modules[key] = (pre, pf, t)
            pre, pf, t = mods  # the set the cached modules were built on (a label view is rebuilt per call)
            self._label = t.scheme != "169"
            if cfg.twin_multi > 0.0 and self._label:
                rc = self._recut(rules, t)
                if rc is not None:
                    pre, pf, t = rc
        vp = cfg.variant_preflop
        vpf = cfg.variant_pushfold
        twist = (vp or vpf) and ex.get("variant") and str(ex.get("variant")).lower() not in PLAIN_NAMES \
            and rules.betting != "fixedlimit" and not rules.must_use_hole and not ex.get("lowball")
        if vp and twist:
            # a catalogued twist (rules.extras["variant"]): this table's preflop module with variant_preflop on top.
            # Not fixed limit (a flat costs one bet, so the wide flat range pays), must-use (Omaha: four-card hands
            # run close) or lowball (mirrored classes): there the tighter flats measured -0.108 +- 0.073,
            # -0.065 +- 0.051 and -0.062 +- 0.047 (held-out H1)
            vkey = ("variant_preflop", id(pre))
            vpre = self._modules.get(vkey)
            if vpre is None:
                vpre = self._modules[vkey] = Preflop(replace(pre.p, **vp), t)
            pre = vpre
        gate = None  # the table's rule for the *_ex dials: the first that applies
        if ex.get("variant") and str(ex.get("variant")).lower() not in PLAIN_NAMES:
            gate = "must_use" if rules.must_use_hole else "fixedlimit" if rules.betting == "fixedlimit" else \
                "lowball" if ex.get("lowball") else "deck" if ex.get("removed_ranks") else \
                "boards" if int(ex.get("n_boards", 1) or 1) > 1 else "wild" if ex.get("wild_rank") is not None else None
        self._gate = gate
        vx = cfg.variant_preflop_ex
        if vx and gate:
            over = vx.get(gate)
            if over:
                vkey = ("variant_preflop_ex", gate, id(pre))
                vpre = self._modules.get(vkey)
                if vpre is None:
                    vpre = self._modules[vkey] = Preflop(replace(pre.p, **over), t)
                pre = vpre
        if vpf and twist:
            vkey = ("variant_pushfold", id(pf))
            vpf_mod = self._modules.get(vkey)
            if vpf_mod is None:
                import copy

                vpf_mod = copy.copy(pf)  # the same solved arrays and tables, other decision-time params
                vpf_mod.p = replace(pf.p, **vpf)
                self._modules[vkey] = vpf_mod
            pf = vpf_mod
        self.active = t
        self.preflop, self.pushfold = pre, pf
        pf.pre = pre  # push/fold reads the shover's range through the preflop module
        pre.pf = pf
        if cfg.use_icm:
            pre.curve = pf.curve = self.curve
        self._known_pre = self._known_post = False
        self._known_ladder = None
        if cfg.known_cards:
            parts = {x.strip() for x in str(cfg.known_cards).split(",") if x.strip()}
            bad = parts - {"pre", "post"}
            if bad:
                raise KeyError(f"unknown known_cards part {sorted(bad)[0]!r}; known: pre, post")
            # the prepared equities are hold'em's showdown (52 cards, five on the board, best five of all, no must-use):
            # any other showdown keeps the dealt class and the plain read
            std = (tuple(rules.board_sizes)[-1:] == (5,) and rules.n_suits == 4 and not rules.must_use_hole
                   and not ex.get("removed_ranks") and not low and wild_c < 0 and not fof
                   and int(ex.get("n_boards", 1) or 1) == 1)
            self._known_post = "post" in parts and std
            if "pre" in parts and std and self._cls_map is None:
                self._known_ladder = known_ladder(t, pre)
                self._known_pre = self._known_ladder is not None

    def _twins(self, rules: Rules) -> dict | None:
        """The variant's twin map (Config.twin_preflop), read once per variant and rules; None when the variant has
        no prepared table or its twins stay within the threshold."""
        import json as _json

        from .tables import generic_doc, twin_classes, twin_shift

        key = (str((rules.extras or {}).get("variant")), _json.dumps(rules.extras or {}, sort_keys=True, default=str),
               rules.hole_cards, self.cfg.twin_preflop, self.tables.dir, self.tables.source)
        cache = _TWINS  # once per process: reading the table is ~1.5 ms, at a table start
        if key not in cache:
            tm = twin_classes(generic_doc(rules), self.tables)
            cache[key] = tm if tm is not None and twin_shift(tm, self.tables) >= self.cfg.twin_preflop else None
        return cache[key]

    def _recut(self, rules: Rules, t):
        """(Preflop, PushFold, Tables) on the re-cut label tables (Config.twin_multi), built once per set and process;
        None when the variant has no prepared table or the re-cut moves labels less than the threshold."""
        from .tables import generic_doc, recut_label_tables

        key = ("recut", t.dir, t.source, str((rules.extras or {}).get("variant")), self.cfg.twin_multi)
        if key not in _TWINS:
            res = recut_label_tables(generic_doc(rules), t)
            _TWINS[key] = res[0] if res is not None and res[1] >= self.cfg.twin_multi else None
        t2 = _TWINS[key]
        if t2 is None:
            return None
        mkey = ("recut", id(t2))
        mods = self._modules.get(mkey)
        if mods is None:
            mods = self._modules[mkey] = (Preflop(self.cfg.preflop, t2), self._base[1].with_tables(t2), t2)
        return mods

    def set_panic(self, on: bool) -> None:
        self.panic = on

    # A kit that times the hand end (drill 7's kit E: 1 ms per event, interrupted at 1.05 ms): `defer_hand_end(True)`
    # leaves the ICM curve and the profiler's dials pending at hand end, and `idle()` (an event callback with time to
    # spare, the next hand's start) computes them; a decision that comes first computes them itself. Either way every
    # read sees the values the eager hand end would have computed. `lazy`: the owner's standing choice (the hybrids'
    # fallback Hero is lazy and idle() leaves it so; it computes when it decides).
    lazy = False
    deferred = False

    def defer_hand_end(self, on: bool) -> None:
        self.deferred = bool(on)
        self._lazy_now()

    def set_lazy(self, on: bool) -> None:
        self.lazy = bool(on)
        self._lazy_now()

    def _lazy_now(self) -> None:
        on = self.lazy or self.deferred
        self.lazy_curve = on
        if self.prof is not None:
            self.prof.lazy = on

    def idle(self) -> None:
        """Pending hand-end work, now (outside any decision). A lazy Hero keeps its own pending until it decides."""
        if self.lazy:
            return
        self.settle()
        prof = self.prof
        if prof is not None and prof._stale:
            prof._settle()

    def act(self, obs: Observation) -> Action:
        self.last_path = "act"  # until a module is chosen: an error before that point is attributed here
        if self._curve_todo is not None:
            self.settle()
        hole = obs.hole
        board = obs.board
        rm = self._remap
        if rm is not None:
            hole = remap(hole, rm)
            board = remap(board, rm)
        if obs.hand_no != self.hand_no:
            self.hand_no = obs.hand_no
            stacks, bets = obs.stacks, obs.bets
            self.hand_start = [stacks[s] + bets[s] for s in range(len(stacks))]
            self._pre_aggr = False
        prof = self.prof
        if prof is not None:
            try:
                prof.observe(obs)  # the kit's own history: the profiler counts only what it can see
            except Exception:  # noqa: BLE001 - a profiler slip must not cost the decision
                prof = None
        xl = self.exploit  # (not `ex`: that name holds the exposed cards below)
        raw = obs  # the kit's own observation: the exploit layer replays only what it saw
        if xl is not None:
            try:
                xl.observe(obs)
            except Exception:  # noqa: BLE001
                xl = None
        no_history = not obs.history
        if obs.street == 0 or no_history:
            bb = obs.blinds[1] or 1
            base = (max(bb, self.rules.straddle * bb) if self.rules.straddle else bb) if obs.street == 0 else 0
            if not history_explains_bets(obs, base):
                # an adapter that passes no action history: rebuild this street's raises from the bets so a raised
                # pot does not read as unopened (drill 6: 5.9 -> 3.2 points without this)
                obs = replace(obs, history=history_from_bets(obs, base))
                self.inferred += 1
        nh = len(hole)
        cls = None
        if nh == 2:
            cls = hole_class(hole)
            cm = self._cls_map
            if cm is not None:
                cls = cm.get(cls, cls)
        elif self._label and nh >= 3:
            cls = hole_label(obs.hole, self.rules)  # the variant tables are keyed by displayed labels
        extras = obs.extras
        bounty = 0.0
        dead = ()
        exposed = None
        board2 = None
        bounty_k = 0.0
        shared = None
        if extras:
            if self._bounty is not None:
                if self.cfg.bounty_exact:
                    bounty, bounty_k = self._bounty_exact(obs, extras)
                else:
                    bounty = self._bounty_bonus(obs, extras)
            if self._known_pre or self._known_post:
                known = _known.parse(extras, obs.seat, rm.rank_order if rm is not None else None)
                if known:
                    exposed, dead, shared = self._known(known, hole)
                    if obs.street == 0 and self._known_pre and nh == self.rules.hole_cards:
                        k = self._known_class(known, hole, obs)
                        if k is not None:
                            cls = k
                            exposed = None  # the class prices his cards: no exposed-card range reads on top
            else:
                ex = extras.get("exposed")
                if ex:
                    exposed, dead = self._exposed(ex, obs.seat)
            if self._revealed_dead:
                rv = extras.get("revealed")
                if rv:  # deal5_keep2: every face-up discard, our own included, is out of the deck
                    dead = dead + self._revealed(rv)
            elif self._toss and self.cfg.toss_dead:
                dc = extras.get("discards")
                if dc:  # toss_or_holdem: every face-up toss, our own included, is out of the deck
                    dead = dead + self._tossed(dc)
            if obs.street > 0:
                bs = extras.get("boards")
                if bs and len(bs) > 1 and len(bs[1]) == len(board):
                    board2 = tuple(bs[1])
                    if rm is not None:
                        board2 = remap(board2, rm)
        spot = Spot(obs, hole, cls, bounty, self._ko, dead, exposed)
        cfg = self.cfg
        if bounty:
            spot.bounty_k = bounty_k
            if cfg.bounty_call_scale != 1.0 and spot.to_call > 0:
                spot.pot_odds = spot.to_call / (spot.pot_total + spot.to_call + bounty * cfg.bounty_call_scale)
        if cfg.ror_margin > 0.0:
            spot.ror = self.ror_for(spot.my_bb, obs.hand_no)
        cheap = cfg.cheap or self.panic
        if obs.street == 0:
            if xl is not None and not cheap and xl.p.dead_shift and spot.n_raises == 0 and spot.n_in == 0 \
                    and spot.behind > 1:
                try:
                    k = xl.dead_behind(raw)
                except Exception:  # noqa: BLE001
                    k = 0
                if k:
                    spot.behind = max(1, spot.behind - k)  # dead seats behind fold: open for the seats that are left
            pf = self.pushfold
            a = None
            if pf.applies(spot):
                self.last_path = "pushfold"
                a = pf.act(spot, prof, cheap)
                if not (a.kind is ActionKind.RAISE or not pf.p.fi_rest_open or not pf.fi_zone(spot)):
                    a = None
            if a is None:
                self.last_path = "preflop"
                a = self.preflop.act(spot, prof, cheap)
            if xl is not None and not cheap:
                a = self._exploit(xl, raw, a)
            if a.kind is ActionKind.RAISE:
                self._pre_aggr = True
            elif spot.to_call > 0 and spot.n_raises > 0:
                self._pre_aggr = False  # facing a raise and not re-raising: someone else is the aggressor
            return a
        if nh < 2 or len(board) < 3:
            self.last_path = "safe"
            return safe_action(obs)
        mu = self._must_use
        if mu:
            if nh < mu or len(board) < 5 - mu:
                self.last_path = "safe"
                return safe_action(obs)
        elif nh + len(board) > 8 and not (cfg.long_board and nh == 2):
            self.last_path = "safe"
            return safe_action(obs)
        if no_history:
            aggressor = self._pre_aggr
        else:
            aggressor = prof is not None and prof.pre_raiser == obs.seat
        value_shift = 1 if (self._swap_street and obs.street < self._swap_street) else 0
        call_shift = 0
        if self._revealed_dead:
            value_shift += cfg.keep_value_shift
            call_shift += cfg.keep_call_shift
        elif self._toss:
            value_shift += cfg.toss_value_shift
            call_shift += cfg.toss_call_shift
        elif nh >= 3 and self.rules.hole_cards >= 3:  # dealt, not bought (bonus_card, auction: measured apart)
            call_shift += cfg.mu_call_shift if mu else cfg.multi_call_shift
            value_shift += cfg.mu_value_shift if mu else cfg.multi_value_shift
        if cfg.call_shift_ex and self._gate:
            call_shift += int(cfg.call_shift_ex.get(self._gate, 0) or 0)
        self.last_path = "postflop"
        nb = len(board)
        if cfg.long_board and (nb > 5 or (self._run and nb >= 5)) and nh == 2 and not mu:
            # a long board, or the last size with a run still possible (river_of_blood): one more card comes after a
            # red last card under run_until_black; a board past five plays as a turn while one may come, a river when not
            pf = self.postflop
            if not pf.low and pf.wild_rank < 0:
                more = self._run and (board[-1] & 3) in (1, 2)
                extra = nb - 5 if nb > 5 else 0
                self.last_path = "postflop.long"
                a = pf.act(spot, hole, prof, aggressor, cheap, board, board2=board2, must_use=mu, dead=dead,
                           value_shift=value_shift + cfg.long_value_per_card * extra,
                           call_shift=call_shift + cfg.long_call_per_card * extra,
                           street=2 if more else 3, to_come=cfg.long_to_come if more else 0, long=True, more=more)
                if xl is not None and not cheap:
                    a = self._exploit(xl, raw, a)
                return a
            if nh + nb > 8:
                self.last_path = "safe"
                return safe_action(obs)
        sh, sh_all = (), False
        if shared and self._known_post:
            sh, sh_all = self._shared_sets(shared, spot)
        if sh:
            # the shared reads are pairwise (his hand on the same board as ours): the multi-card call shift, there
            # because every three-card hand is stronger, does not apply to them
            cs2 = call_shift - (cfg.multi_call_shift if (nh >= 3 and self.rules.hole_cards >= 3 and not mu
                                                         and not self._revealed_dead and not self._toss) else 0)
            a = self.postflop.act(spot, hole, prof, aggressor, cheap, board, board2=board2, must_use=mu, dead=dead,
                                  value_shift=value_shift, call_shift=call_shift, shared=sh, shared_call_shift=cs2,
                                  shared_all=sh_all)
            self.known_post_n += 1
        else:
            a = self.postflop.act(spot, hole, prof, aggressor, cheap, board, board2=board2, must_use=mu, dead=dead,
                                  value_shift=value_shift, call_shift=call_shift)
        if cfg.bounty_bet_frac > 0.0 and bounty and a.kind is ActionKind.CHECK and spot.to_call == 0 \
                and spot.n_opps <= 2 and not cheap and ActionKind.RAISE in obs.legal and self._bounty_hit(obs):
            a = self.postflop._bet(spot, cfg.bounty_bet_frac, bluff=True)
            self.last_path = "postflop.bounty_bet"
        if xl is not None and not cheap:
            a = self._exploit(xl, raw, a)
        return a

    def _exploit(self, ex: Exploit, obs: Observation, a: Action) -> Action:
        """The exploit layer's override of the module's action, if it has one; a slip there keeps `a`."""
        try:
            b = ex.override(obs, a)
        except Exception:  # noqa: BLE001
            return a
        if b is None:
            return a
        self.last_path = "exploit." + ex.last
        return b

    def ror_for(self, my_bb: float, hand_no: int) -> float:
        """The risk-of-ruin margin on stack-offs: Config.ror_margin while deep and early, else 0."""
        cfg = self.cfg
        if cfg.ror_margin <= 0.0 or hand_no > cfg.ror_hands:
            return 0.0
        t = (my_bb - cfg.ror_from_bb) / (cfg.ror_full_bb - cfg.ror_from_bb)
        return 0.0 if t <= 0.0 else cfg.ror_margin * (1.0 if t > 1.0 else t)

    def hand_end(self, result: HandResult) -> None:
        """The chips after the hand first (a few assignments: an interrupted hand end leaves the chain whole), then the
        reads, then the ICM curve for the next hand. `lazy_curve`: the curve waits until a decision needs it (settle(),
        at the top of act and variant_decide): the same curve from the same chips, paid only on hands this Hero
        plays (the hybrids' fallback Hero). An interrupted curve stays pending and is computed at the next settle()."""
        base = self.hand_start if (self.hand_start is not None and result.hand_no == self.hand_no) else self.last_stacks
        after = None
        if base is not None and len(result.deltas) == len(base):
            after = [max(0, base[s] + result.deltas[s]) for s in range(len(base))]
            self.last_stacks = after
        self.hand_start = None
        if self.prof is not None:
            self.prof.hand_end(result)
        if self.exploit is not None:
            try:
                self.exploit.hand_end(result)
            except Exception:  # noqa: BLE001
                pass
        if after is not None and self.cfg.use_icm and after[self.seat] > 0:
            self._curve_todo = (after, result.hand_no + 1)
            if not self.lazy_curve:
                self.settle()

    lazy_curve = False
    _curve_todo = None  # (chips after the last hand, its next hand number): the curve still to compute

    def settle(self) -> None:
        """Compute the ICM curve the last hand end left pending, if any (cleared only once it is done)."""
        todo = self._curve_todo
        if todo is not None:
            self._curve(todo[0], todo[1])
            self._curve_todo = None

    def _curve(self, stacks, next_hand: int) -> None:
        """Recompute the ICM value curve for `stacks` (once per hand, outside the decision budget)."""
        cfg = self.cfg
        ratios = cfg.icm_ratios
        alive = 0
        total = 0
        for s in stacks:
            if s > 0:
                alive += 1
                total += s
        linear = len(self.payouts) >= alive and _linear_step([float(x) for x in self.payouts[:alive]]) is not None
        if alive >= cfg.icm_many_alive and not linear:
            ratios = cfg.icm_ratios_many
        cap = None
        var = self._cap_var
        if var is not None and linear and alive >= 2 and 0 <= next_hand < len(var) - 1:
            # the variance still to come once the next hand (the one this curve prices) is over
            s2 = 2.0 * cfg.cap_vol_bb ** 2 * var[next_hand + 1]
            avg = total / alive
            lam = s2 / (s2 + avg * avg)
            if lam < 0.999:
                cap = (lam, sqrt(s2))
        self.curve.compute(stacks, self.seat, self.payouts, ratios, cfg.icm_buckets, cfg.icm_me_subdiv, cap)

    # ------------------------------------------------------------------ extras
    def _bounty_bonus(self, obs: Observation, extras: dict) -> float:
        """Expected extra chips if we win this pot: the bounty pays (ratio - 1) x the net win + constant when
        my bounty rank is in my hand or lands on the board (displayed ranks, as the hook draws them)."""
        b = extras.get("bounties")
        if not b:
            return 0.0
        r = b.get(obs.seat)
        if r is None:
            r = b.get(str(obs.seat))
            if r is None:
                return 0.0
        ratio, const = self._bounty
        hit = False
        for c in obs.hole:
            if (c >> 2) == r:
                hit = True
                break
        if not hit:
            for c in obs.board:
                if (c >> 2) == r:
                    hit = True
                    break
        if hit:
            p = 1.0
        else:
            rules = self.rules
            to_come = rules.board_sizes[-1] - len(obs.board)
            if to_come <= 0:
                return 0.0
            unseen = rules.deck_size - len(obs.hole) - len(obs.board)
            outs = rules.n_suits
            p_none = 1.0
            for k in range(to_come):
                p_none *= (unseen - outs - k) / (unseen - k)
            p = 1.0 - p_none
        win = obs.pot + sum(obs.bets) - obs.bets[obs.seat]
        return p * ((ratio - 1.0) * (win if win > 0 else 0) + const)

    def _bounty_rank(self, obs: Observation, extras: dict):
        b = extras.get("bounties")
        if not b:
            return None
        r = b.get(obs.seat)
        return b.get(str(obs.seat)) if r is None else r

    def _bounty_hit(self, obs: Observation) -> bool:
        """My bounty rank is in my hand or on the board (displayed ranks, as the hook reads them)."""
        r = self._bounty_rank(obs, obs.extras or {})
        if r is None:
            return False
        return any((c >> 2) == r for c in obs.hole) or any((c >> 2) == r for c in obs.board)

    def _bounty_exact(self, obs: Observation, extras: dict) -> tuple[float, float]:
        """(expected extra chips if we win this pot now, extra chips per chip a caller adds): p x ((ratio - 1) x the
        net win + constant) and p x (ratio - 1), the net win being the other players' chips in the pot (the pot less
        everything we put in this hand), p the chance the bounty rank is in my hand or on the board at the end."""
        r = self._bounty_rank(obs, extras)
        if r is None:
            return 0.0, 0.0
        ratio, const = self._bounty
        if any((c >> 2) == r for c in obs.hole) or any((c >> 2) == r for c in obs.board):
            p = 1.0
        else:
            rules = self.rules
            to_come = rules.board_sizes[-1] - len(obs.board)
            if to_come <= 0:
                return 0.0, 0.0
            unseen = rules.deck_size - len(obs.hole) - len(obs.board)
            outs = rules.n_suits
            p_none = 1.0
            for k in range(to_come):
                p_none *= (unseen - outs - k) / (unseen - k)
            p = 1.0 - p_none
        me = obs.seat
        start = self.hand_start[me] if self.hand_start is not None else obs.stacks[me] + obs.bets[me]
        win = obs.pot + sum(obs.bets) - (start - obs.stacks[me])
        return p * ((ratio - 1.0) * (win if win > 0 else 0) + const), p * (ratio - 1.0)

    def _tossed(self, dc: dict) -> tuple:
        """toss_or_holdem's face-up tosses ({seat: card}), every seat's, as canonical cards."""
        rm = self._remap
        out = []
        for c in dc.values():
            if c is None:
                continue
            c = int(c)
            out.append(rm.rank_order[c >> 2] * 4 + (c & 3) if rm is not None else c)
        return tuple(out)

    def _revealed(self, rv: dict) -> tuple:
        """deal5_keep2's face-up discards ({seat: cards}), every seat's, as canonical cards."""
        rm = self._remap
        out = []
        for cards in rv.values():
            for c in cards:
                c = int(c)
                out.append(rm.rank_order[c >> 2] * 4 + (c & 3) if rm is not None else c)
        return tuple(out)

    def _known(self, known: dict, hole):
        """Known cards ({seat: canonical cards}, known.parse) as (exposed {seat: his highest card that is not ours},
        dead cards for the draw outs (every known card that is not ours, once), shared {seat: our cards he holds too})."""
        mine = set(hole)
        exposed = {}
        dead = set()
        shared = {}
        for s, cards in known.items():
            sh = []
            top = -1
            for c in cards:
                if c in mine:
                    sh.append(c)
                else:
                    dead.add(c)
                    if c > top:
                        top = c
            if top >= 0:
                exposed[s] = top
            if sh:
                shared[s] = tuple(sh)
        return exposed or None, tuple(sorted(dead)), shared

    def _known_class(self, known: dict, hole, obs: Observation):
        """Heads-up before the flop against a seat known to hold cards: the class whose heads-up equity is ours
        against him (Config.known_cards "pre"), or None (more than one opponent, nothing known, or no table)."""
        in_hand = obs.in_hand
        me = obs.seat
        opp = -1
        for s in range(len(in_hand)):
            if s != me and in_hand[s]:
                if opp >= 0:
                    return None
                opp = s
        cards = known.get(opp) if opp >= 0 else None
        if not cards:
            return None
        mine, sh, xp = _known.split(hole, cards)
        u = self.rules.hole_cards - len(sh) - len(xp)
        if u < 0 or not mine:
            return None
        e = _known.equity(mine, sh, xp, u)
        if e is None:
            return None
        self.known_pre_n += 1
        return _known.class_at(self._known_ladder, e)

    @staticmethod
    def _shared_sets(shared: dict, spot: Spot) -> tuple[tuple, bool]:
        """Our cards each opponent still in the hand holds too, one tuple per distinct set, and whether every
        opponent in the hand holds some."""
        out = []
        every = True
        for s in spot.opps:
            cs = shared.get(s)
            if not cs:
                every = False
            elif cs not in out:
                out.append(cs)
        return tuple(out), every and bool(out)

    def _exposed(self, ex: dict, me: int):
        """Other seats' face-up cards: {seat: canonical card} and the dead tuple for draw reads."""
        rm = self._remap
        out = {}
        dead = []
        for s, c in ex.items():
            s = int(s)
            if s == me or c is None:
                continue
            c = int(c)
            if rm is not None:
                c = rm.rank_order[c >> 2] * 4 + (c & 3)
            out[s] = c
            dead.append(c)
        return out, tuple(dead)

    # ------------------------------------------------------------------ variant decisions
    def variant_decide(self, prompt: dict):
        """The engine's ask(): discard / swap / buy_card. None means the hook's default."""
        if self._curve_todo is not None:
            self.settle()
        kind = prompt.get("decision")
        hole = tuple(prompt.get("hole") or ())
        board = tuple(prompt.get("board") or ())
        rm = self._remap
        if rm is not None:
            hole, board = remap(hole, rm), remap(board, rm)
        if kind == "discard":
            dead = ()
            if self._toss and self.cfg.toss_dead:
                dc = prompt.get("discards")
                dead = self._tossed(dc) if dc else ()
            return self._discard(hole, board, dead)
        if kind == "swap":
            return self._swap(hole, board)
        if kind == "buy_card":
            price = int(prompt.get("price", 0) or 0)
            stacks = prompt.get("stacks")
            seat = int(prompt.get("seat", self.seat))
            mine = stacks[seat] if stacks and 0 <= seat < len(stacks) else 0
            return price <= 0.1 * mine
        if kind == "bid":
            return self._bid(hole, board, prompt)
        if kind == "keep":
            rv = prompt.get("revealed") or {}
            return self._keep(hole, board, self._revealed(rv) if rv else ())
        return None

    def _bid(self, hole, board, prompt: dict) -> int:
        """The auction (MIT 2024's second-price sealed bid for a third card): bid the price at which winning and losing
        come out level. Winning at price x is worth e_win (pot + x) - x, losing (a rival pays x) e_lose (pot + x), so
        x = d pot / (1 - d) with d = e_win - e_lose, the pot share winning the card is worth (tables/auction_bid.json,
        by flop read and the number of other bidders). The pot is grown by the stack still to bet (`auction_implied`),
        and the bid is capped at a share of the stack and of the pot. A tie pays the bid too."""
        cfg = self.cfg
        stack = int(prompt.get("max_bid", prompt.get("stack", 0)) or 0)
        pot = int(prompt.get("pot", 0) or 0)
        if stack <= 0 or pot <= 0 or len(hole) < 2 or len(board) < 3:
            return 0
        t = self._auction
        if t is None:
            t = self._auction = auction_table()
        k = int(prompt.get("n_bidders", 2) or 2) - 1
        k = 1 if k < 1 else 4 if k > 4 else k
        tier, outs, _ = self.postflop._read(hole[:2], board, 0, ())
        cells = t.get(k) or {}
        d = cells.get((tier, 0 if outs <= 0 else 1 if outs <= 4 else 2 if outs <= 8 else 3))
        if d is None:
            d = cells.get("mean", 0.25)
        if d <= 0.0:
            return 0
        spr = stack / pot
        pot_eff = pot * (1.0 + cfg.auction_implied * (spr if spr < cfg.auction_spr_cap else cfg.auction_spr_cap))
        x = d * pot_eff / (1.0 - d) if d < 0.95 else pot_eff * 19.0
        cap = min(cfg.auction_stack_frac * stack, cfg.auction_pot_frac * pot)
        b = int(x if x < cap else cap)
        return b if b < stack else stack

    def _keep(self, hole, board, dead: tuple = ()):
        """deal 5 keep 2: indices of the two to keep, the best by the flop read (made tier, draws) with every revealed
        discard and the three we throw as dead cards, the preflop rank breaking ties. None (the hook's default) when
        there is nothing to choose."""
        n = len(hole)
        if n <= 2:
            return None
        rank = self.tables.rank
        best, best_s = None, -1.0
        read = self.postflop._read
        flop = len(board) >= 3
        for i in range(n):
            for j in range(i + 1, n):
                keep = (hole[i], hole[j])
                if flop:
                    own = tuple(hole[m] for m in range(n) if m != i and m != j)
                    tier, outs, _ = read(keep, board, 0, dead + own)
                    s = max(TIER_EQUITY[tier], outs * 0.04) + 0.01 * rank[hole_class(keep)]
                else:
                    s = rank[hole_class(keep)]
                if s > best_s:
                    best_s, best = s, (i, j)
        return best

    def _keep_score(self, keep, board, dead: tuple = ()) -> float:
        """How good the two kept cards are: the flop read when a board is shown (`dead` cards off the outs), else the
        preflop rank."""
        rank = self.tables.rank[hole_class(keep)]
        if len(board) >= 3:
            tier, outs, _ = self.postflop._read(keep, board, 0, dead)
            draw = outs * 0.04
            return max(TIER_EQUITY[tier], draw) + 0.01 * rank
        return rank

    def _discard(self, hole, board, dead: tuple = ()):
        """Index of the card whose removal leaves the best two. With `dead` (toss_dead: the tosses made before ours)
        those and the card thrown come off the kept two's outs."""
        n = len(hole)
        if n < 3:
            return None
        best_k, best = 0, -1.0
        for k in range(n):
            keep = hole[:k] + hole[k + 1:]
            if len(keep) != 2:
                continue
            s = self._keep_score(keep, board, dead + (hole[k],) if dead else ())
            if s > best:
                best, best_k = s, k
        return best_k

    def _swap(self, hole, board):
        """-1 to keep: a made hand or a draw. Otherwise replace the lowest card that pairs nothing on the board
        and is not part of a flush draw."""
        if len(hole) != 2 or len(board) < 3:
            return -1
        tier, outs, _ = self.postflop._read(hole, board, 0, ())
        if tier >= 3 or outs >= 8:
            return -1
        board_ranks = {c >> 2 for c in board}
        suits = [0, 0, 0, 0]
        for c in board:
            suits[c & 3] += 1
        cands = []
        for i, c in enumerate(hole):
            if (c >> 2) in board_ranks or (c >> 2) == (hole[1 - i] >> 2):
                continue
            if suits[c & 3] + sum(1 for h in hole if (h & 3) == (c & 3)) >= 4:
                continue
            cands.append(i)
        if not cands:
            return -1
        return min(cands, key=lambda i: hole[i] >> 2)


_AUCTION: dict | None = None


def auction_table(path=None) -> dict:
    """tables/auction_bid.json as {bidders - 1 (1..4): {(tier, outs bucket): d, "mean": d}}, read once per process."""
    global _AUCTION
    if _AUCTION is not None and path is None:
        return _AUCTION
    import json
    from pathlib import Path

    from .tables import TABLES_DIR

    with open(Path(path) if path else Path(TABLES_DIR) / "auction_bid.json") as f:
        raw = json.load(f)["d"]
    out: dict = {}
    for k, cells in raw.items():
        m: dict = {}
        tot = acc = 0.0
        for key, c in cells.items():
            tier, ob = (int(x) for x in key.split(","))
            m[(tier, ob)] = float(c["d"])
            tot += c["n"]
            acc += c["n"] * c["d"]
        m["mean"] = acc / tot if tot else 0.25
        out[int(k)] = m
    if path is None:
        _AUCTION = out
    return out


class Hero:
    """SafeBot around HeroCore. `hero.safe.stats()` has errors / overruns / worst latency."""

    def __init__(self, config: Config | None = None, tables: Tables | None = None):
        from .safe import governor

        self.core = HeroCore(config, tables)
        c = self.core.cfg
        self.safe = SafeBot(self.core, c.deadline_ms, c.panic_after, c.panic_rate,
                            governor(c.panic_window, c.panic_ladder, c.panic_recover, c.panic_backoff))

    @classmethod
    def cheap(cls, tables: Tables | None = None) -> "Hero":
        return cls(Config.cheap_config(), tables)

    @property
    def config(self) -> Config:
        return self.core.cfg

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.safe.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        return self.safe.act(obs)

    def hand_end(self, result: HandResult) -> None:
        self.safe.hand_end(result)

    def variant_decide(self, prompt: dict):
        """Guarded like act(): an error is counted and means the hook's default decision."""
        try:
            return self.core.variant_decide(prompt)
        except Exception:  # noqa: BLE001
            self.safe.errors += 1
            return None

    def defer_hand_end(self, on: bool = True) -> None:
        """HeroCore.defer_hand_end: for a kit that times the hand end; call idle() from a callback with time to spare."""
        self.core.defer_hand_end(on)

    def idle(self) -> None:
        try:
            self.core.idle()
        except Exception:  # noqa: BLE001
            self.safe.errors += 1


def make_bot(config: Config | None = None) -> Hero:
    return Hero(config)


refreeze()  # whatever was built at import (evaluator tables, straight-draw table) is permanent; an earlier copy is freed

__all__ = ["Config", "Exploit", "ExploitParams", "Hero", "HeroCore", "IcmCurve", "config_from_dict", "icm_value", "make_bot", "mirror_map",
           "replace", "wild_map"]
