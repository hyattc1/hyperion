"""The dials of rival 3's decision core: the night's window and variant dials for the shipped base (`hybrid3_x`).

On plain hold'em rival 3's core makes ~97% of hybrid3_x's decisions, so Hero's `Config` keys (`preflop.open_frac` and
the rest) only reach the 14 tables Hero plays whole and the ~0.1 decision a table the core declines. These dials say
the same things to the core. Each is a named copy of one literal in rival 3's own code; the defaults are those
literals, so with no dial set every decision is bit-identical to rival 3 as built (tests/test_ship.py).

Set them as `r3.<name>` in a dials dict (hyperion/ship.py, `--dials` on the tools):

    {"r3.open_late_scale": 1.3, "r3.bluff_scale": 1.3}       # too passive for this field
    {"r3.push_margin": 0.03, "r3.call_margin": 0.03, "r3.raise_shift": 0.05, "r3.three_bet_scale": 0.7}   # survival

Directions were checked with paired runs in model mode (docs/decisions.md, "Ship hybrid3_x as the base").
"""
from __future__ import annotations

from dataclasses import dataclass, field


def _dial(default, doc: str):
    return field(default=default, metadata={"doc": doc})


@dataclass
class Rival3Knobs:
    # preflop, unopened, deeper than short_bb: rival 3 raises first in (or isolates limpers) when the hand's percentile
    # is inside the position's threshold: 0.48 with one seat behind, 0.36 with two ... 0.12 with seven
    open_scale: float = _dial(1.0, "multiplies every position's raise-first-in threshold: above 1 opens wider, below 1 "
                                   "tighter")
    open_late_scale: float = _dial(1.0, "multiplies it again for the cutoff and the button (two or three seats behind)")
    open_vs3b_scale: float = _dial(0.75, "multiplies it again when a seat behind re-raises more than 20% of the raises "
                                         "it faces (1 = no narrowing)")
    # push or fold
    short_bb: float = _dial(10.0, "effective stack in big blinds at or under which an unopened pot is shove or fold")
    push_margin: float = _dial(0.002, "points (ICM on the table's payouts) a shove must beat folding by, open or "
                                      "re-shove: higher = fewer shoves, lower or negative = more")
    # facing a raise
    commit_bb: float = _dial(18.0, "at or under this effective depth, a call or re-shove facing a raise is priced as "
                                   "all-in by ICM")
    call_margin: float = _dial(0.002, "points a committing call must beat folding by: higher = fewer stack-off calls")
    three_bet_scale: float = _dial(1.0, "multiplies the deep value 3-bet range: below 1 tighter")
    # bounty tables (MIT 2025), where the core plays only with `base.hero_on_bounty` off: as built it is blind to them
    bounty: float = _dial(0.0, "share of my bounty's expected chips (the house pays (ratio - 1) x the net win + constant "
                               "when my bounty rank is in my hand or on the board) added to the winning branches of "
                               "every all-in price: 1 = all of it, 0 = rival 3 as built")
    # postflop
    bluff_scale: float = _dial(1.0, "multiplies the chance of every bluff and semi-bluff, the flop continuation bet "
                                    "included")
    call_edge: float = _dial(0.12, "strength over the price a postflop call needs: higher folds more")
    raise_shift: float = _dial(0.0, "added to the strength rival 3 raises a bet with (0.8; 0.7 when shallow): higher = "
                                    "fewer stack-offs")
    # opponent reads
    prior_scale: float = _dial(1.0, "weight of the prior in every seat read (about four actions' worth): below 1 the "
                                    "reads move sooner")
    dead_hands: int = _dial(22, "hands with no voluntary chip before a seat reads as dead (folds to everything): lower "
                                "catches folding and timing-out seats sooner")
    # facing a 3-bet after we opened (S2, docs/drills/s2-exploit-fixes-log.md). Off: rival 3 as built, which prices
    # every 3-bet as an all-in against the top ~9% and so folds ~90% of its opens whatever the 3-bet's size
    v3_defend: bool = _dial(False, "facing one 3-bet of our open, deep and not committed by the price: fold, call, "
                                   "4-bet or jam by ICM against the 3-bettor's observed 3-bet rate (a prior, then "
                                   "its 3-bets per chance) and its observed folds to 4-bets; off = as built")
    v3_min_rate: float = _dial(0.2, "the 3-bettor's estimated 3-bet rate from which the defence plays; under it, as "
                                    "built (tight: most seats rarely 3-bet)")
    v3_prior: float = _dial(0.08, "prior 3-bet rate of a seat facing an open")
    v3_prior_n: float = _dial(20.0, "weight of that prior, in chances: lower moves sooner (8 fired on two 3-bets of a "
                                    "nit and lost on night)")
    v3_others_w: float = _dial(0.5, "weight of a chance to 3-bet another seat's open (one against our open counts 1)")
    v3_cont: float = _dial(0.04, "share of all hands a 3-bettor continues with against a 4-bet (about QQ+ and AK): "
                                 "its fold rate to a 4-bet is modelled as 1 - this / its 3-bet rate")
    v3_f4_n: float = _dial(4.0, "weight of that model against the 3-bettor's observed folds to 4-bets")
    v3_f4_cap: float = _dial(0.6, "the model's fold rate to a 4-bet is at most this before folds are observed (a "
                                  "4-bet to 2.2x breaks even near 0.5: lower = no bluff 4-bets until it is seen "
                                  "folding)")
    v3_min_n: float = _dial(0.0, "chances to 3-bet (weighted) the 3-bettor must have shown in completed hands")
    v3_real_ip: float = _dial(0.85, "share of our equity a call of the 3-bet realises in position")
    v3_real_oop: float = _dial(0.7, "... out of position")
    v3_size: float = _dial(2.2, "4-bet to this multiple of the 3-bet (a 4-bet committing 40% of the stack is a jam)")
    v3_min_bb: float = _dial(12.0, "effective depth in big blinds from which the defence plays")
    v3_margin: float = _dial(0.002, "points a call, 4-bet or jam must beat folding by")
    # blind against blind (S11, docs/drills/climb/s11-log.md): a big blind's 3-bet of our small-blind open (heads-up:
    # the button's) comes from a wide range against a wide open, so the defence there reads it from its own prior
    v3_bvb_prior: float = _dial(-1.0, "the prior 3-bet rate (weight v3_prior_n) when the big blind 3-bets our small-blind "
                                      "open with nobody else in; -1 = the v3_prior and v3_min_rate as everywhere")
    v3_bvb_min_rate: float = _dial(0.12, "... and the estimated rate from which the defence plays there")
    v3_bvb_holdem_only: bool = _dial(False, "... and only on hold'em tables (hero.holdem_table): on twist tables it lost "
                                            "a little on six variants and two aware fields (held-out H9)")
    v3_bvb_twists: str = _dial("", "... and on these one-step twist families as well (hero.TWIST_FAMILIES, comma-"
                                   "separated: discard, bounty, knockout, buy, swap, exposed; V-f); '' = hold'em only")
    v3_bvb_f4_cap: float = _dial(-1.0, "... and the cap on its modelled fold rate to a 4-bet there (a wide 3-bettor "
                                       "need not fold its wide range to a 4-bet: 0.45 = no bluff 4-bets until it is "
                                       "seen folding to one); -1 = v3_f4_cap")
    v3_bvb_cont: float = _dial(-1.0, "... and the share of all hands it continues with against a 4-bet there (blind against "
                                     "blind a 3-bettor defends wider than QQ+ / AK: 0.08 means a seat that 3-bets 18% "
                                     "folds 56% in the model); -1 = v3_cont")
    # the big blind facing one raise and no callers, deep (S2): call when the equity it realises beats the price
    bb_defend: bool = _dial(False, "big blind facing one raise and no caller, not committed: also call when equity "
                                   "against the opener's range times bb_real beats the price (so the range widens "
                                   "against a small open); off = as built (bottom half folds at any price)")
    bb_real: float = _dial(0.75, "share of its equity the big blind realises out of position")
    bb_margin: float = _dial(0.0, "equity over the price a big-blind call needs")
    # a light 3-bet against an opener that folds to 3-bets (S12, docs/drills/climb/s12-log.md). Off: rival 3 as built,
    # which 3-bets only its value range (top 2.5-6%) whoever opened
    l3_on: bool = _dial(False, "facing one open and no caller, deep: also 3-bet a hand inside l3_max_pct when the "
                               "opener's read fold-to-3-bet (a prior, then its folds per 3-bet faced in completed "
                               "hands) times the folds of the seats still behind pays for the raise")
    l3_prior: float = _dial(0.6, "prior fold-to-3-bet of an opener (the tuning fields' openers fold 0.43-0.9; a low "
                                 "prior waits for evidence)")
    l3_prior_n: float = _dial(6.0, "weight of that prior, in 3-bets faced")
    l3_min_n: float = _dial(0.0, "3-bets the opener must have been seen facing before a light 3-bet")
    l3_min_fold: float = _dial(0.65, "the opener's read fold-to-3-bet from which a light 3-bet is considered")
    l3_max_pct: float = _dial(0.35, "light 3-bets only with hands inside this share of rival 3's preflop ranking")
    l3_lose: float = _dial(0.75, "share of the raise lost when the light 3-bet is not folded to (called or 4-bet)")
    l3_min_bb: float = _dial(25.0, "effective depth in big blinds from which a light 3-bet is considered")
    # a trust weight on the fold read that prices steals at strong tables (S16, docs/drills/climb/s16-log.md). Off: the
    # read as built, (folds + 2.4) / (raises faced + 4). The composite says per seat when the weight applies (while the
    # table reads strong: hero member's Profiler.strong_table at the strong route's threshold; hold'em tables only)
    read_trust: float = _dial(0.0, "unopened pots (the steal price, the open clauses, a short shove's fold equity): a "
                                   "seat's fold-to-a-raise read is at most prior + (observed - prior) x n / (n + this), "
                                   "n its raises faced, prior 0.6; 0 = off")
    read_trust_min_n: float = _dial(10.0, "... and only the prior (0.6) below this many raises faced")
