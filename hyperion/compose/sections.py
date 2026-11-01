"""Sections of the game: every decision falls in exactly one of twelve, read from the Observation alone.

The composite bot (hyperion/compose/bot.py) routes each section to the member bot whose decisions there are best; the
skill profile (tools/profile.py) scores each bot per section. Both need the same small partition, cheap enough to run on
every decision (about 1 us), and coarse enough that each section holds a few percent of the decisions of a 200-hand,
8-seat turbo with 100 bb stacks and blinds every 25 hands.

    from hyperion.compose.sections import SECTIONS, section, section_name
    i = section(obs)          # 0 .. len(SECTIONS) - 1
    SECTIONS[i]               # e.g. "pre_open_20"

The axes, in the order they are read:
  street      preflop or postflop. ~78% of decisions are preflop, and in this format most of the points are won or lost
              there (opens, steals, re-shoves, calling all-ins under ICM).
  postflop    by players in the hand: 2 (heads-up pot) or 3+ (multiway, ~4%: one section); a heads-up pot splits on
              whether we face a bet (fold / call / raise) or not (bet / check, where the exploit layer's
              bet-when-checked-to acts).
  alive       seats with chips (stack + bets this street, or still in the hand). Heads-up (2) and three-handed (3)
              preflop are their own sections: ICM and ranges change most there, and every stack depth reads differently.
  what we face, preflop: unopened (nobody has raised: blinds and limps only), a raise we can re-raise, or an all-in
              (the raiser is all-in, or calling costs my whole stack, or no raise is legal): a call-or-fold decision.
  effective stack in big blinds: min(my chips, the most chips of any other seat still in the hand), counting this
              street's bets. Bands < 10 (push or fold), 10-20 (re-shove range), 20-40, 40+ for unopened pots; < 20 and
              20+ when facing a raise (fewer decisions there).

| # | name | what it is | share of hybrid3_x's decisions, % (realistic / top / strong) |
|---|---|---|---|
| 0 | pre_open_40 | preflop, 4+ alive, unopened, effective 40+ bb | 23.4 / 19.2 / 20.0 |
| 1 | pre_open_20 | ... 20-40 bb | 8.8 / 8.8 / 9.6 |
| 2 | pre_open_10 | ... 10-20 bb | 4.4 / 6.8 / 8.2 |
| 3 | pre_open_short | ... under 10 bb (push or fold) | 1.3 / 3.1 / 3.6 |
| 4 | pre_raised_deep | preflop, 4+ alive, facing a raise I can re-raise, effective 20+ bb | 18.5 / 23.6 / 22.6 |
| 5 | pre_raised_short | ... under 20 bb (re-shove or fold) | 2.8 / 6.2 / 6.5 |
| 6 | pre_allin | preflop, 3+ alive, facing an all-in or a call for my stack | 3.1 / 6.6 / 5.4 |
| 7 | pre_3way | preflop, 3 alive, not facing an all-in | 8.7 / 4.8 / 4.6 |
| 8 | pre_hu | preflop, 2 alive (any depth, anything faced) | 6.9 / 3.2 / 3.5 |
| 9 | post_hu_bet | postflop, 2 in the hand, facing a bet | 6.2 / 4.9 / 5.2 |
| 10 | post_hu_chk | postflop, 2 in the hand, nothing to call | 12.1 / 9.7 / 9.1 |
| 11 | post_mw | postflop, 3+ in the hand | 3.7 / 2.9 / 1.8 |

Notes: a straddle reads as a raise (the composite plays straddle tables as its base does); "unopened" counts limps as
unopened; a preflop all-in for less than a big blind does not open the pot. Variant tables use the same partition
(the composite decides there which member may play; see bot.py).
"""
from __future__ import annotations

from ..core.types import ActionKind, Observation

SECTIONS: tuple[str, ...] = (
    "pre_open_40", "pre_open_20", "pre_open_10", "pre_open_short",
    "pre_raised_deep", "pre_raised_short", "pre_allin",
    "pre_3way", "pre_hu",
    "post_hu_bet", "post_hu_chk", "post_mw",
)
INDEX: dict[str, int] = {n: i for i, n in enumerate(SECTIONS)}
PREFLOP: frozenset[str] = frozenset(n for n in SECTIONS if n.startswith("pre_"))
POSTFLOP: frozenset[str] = frozenset(n for n in SECTIONS if n.startswith("post_"))

(PRE_OPEN_40, PRE_OPEN_20, PRE_OPEN_10, PRE_OPEN_SHORT, PRE_RAISED_DEEP, PRE_RAISED_SHORT, PRE_ALLIN, PRE_3WAY, PRE_HU,
 POST_HU_BET, POST_HU_CHK, POST_MW) = range(len(SECTIONS))

# share of decisions per section for hybrid3_x in Hero's seat, model mode, 50 seeds x 8 (docs/drills/compose-log.md)
SHARES: dict[str, dict[str, float]] = {
    'realistic': {'pre_open_40': 23.43, 'pre_open_20': 8.75, 'pre_open_10': 4.41, 'pre_open_short': 1.31, 'pre_raised_deep': 18.52, 'pre_raised_short': 2.83, 'pre_allin': 3.15, 'pre_3way': 8.74, 'pre_hu': 6.87, 'post_hu_bet': 6.17, 'post_hu_chk': 12.14, 'post_mw': 3.68},
    'top': {'pre_open_40': 19.21, 'pre_open_20': 8.83, 'pre_open_10': 6.82, 'pre_open_short': 3.11, 'pre_raised_deep': 23.62, 'pre_raised_short': 6.22, 'pre_allin': 6.58, 'pre_3way': 4.77, 'pre_hu': 3.23, 'post_hu_bet': 4.94, 'post_hu_chk': 9.73, 'post_mw': 2.92},
    'strong': {'pre_open_40': 20.03, 'pre_open_20': 9.63, 'pre_open_10': 8.16, 'pre_open_short': 3.58, 'pre_raised_deep': 22.55, 'pre_raised_short': 6.52, 'pre_allin': 5.4, 'pre_3way': 4.64, 'pre_hu': 3.49, 'post_hu_bet': 5.18, 'post_hu_chk': 9.07, 'post_mw': 1.76},
}

_RAISE = ActionKind.RAISE


def section(obs: Observation) -> int:
    """The section index of this decision (module doc). Never raises on a well-formed Observation."""
    stacks, bets, in_hand = obs.stacks, obs.bets, obs.in_hand
    if obs.street:
        n_in = 0
        for x in in_hand:
            if x:
                n_in += 1
        if n_in >= 3:
            return POST_MW
        return POST_HU_BET if obs.to_call > 0 else POST_HU_CHK
    me = obs.seat
    bb = obs.blinds[1] or 1
    alive = 0
    cur = 0
    opp = 0  # the most chips of another seat still in the hand
    raiser_allin = False
    for j in range(len(stacks)):
        s = stacks[j]
        b = bets[j]
        t = s + b
        if t > 0 or in_hand[j]:
            alive += 1
        if b > cur:
            cur = b
        if j != me and in_hand[j] and t > opp:
            opp = t
    if alive <= 2:
        return PRE_HU
    raised = cur > bb
    to_call = obs.to_call
    if raised and to_call > 0:
        my_stack = stacks[me]
        if to_call >= my_stack or _RAISE not in obs.legal:
            return PRE_ALLIN
        for j in range(len(stacks)):
            if j != me and bets[j] == cur and stacks[j] == 0:
                raiser_allin = True
                break
        if raiser_allin:
            return PRE_ALLIN
    if alive == 3:
        return PRE_3WAY
    mine = stacks[me] + bets[me]
    eff = (mine if mine < opp else opp) / bb
    if raised and to_call > 0:
        return PRE_RAISED_DEEP if eff >= 20.0 else PRE_RAISED_SHORT
    if eff >= 40.0:
        return PRE_OPEN_40
    if eff >= 20.0:
        return PRE_OPEN_20
    if eff >= 10.0:
        return PRE_OPEN_10
    return PRE_OPEN_SHORT


def section_name(obs: Observation) -> str:
    return SECTIONS[section(obs)]


def features(obs: Observation) -> dict:
    """The raw axes behind section(obs), for profiles and logs (not used on the decision path)."""
    stacks, bets, in_hand = obs.stacks, obs.bets, obs.in_hand
    bb = obs.blinds[1] or 1
    me = obs.seat
    tot = [s + b for s, b in zip(stacks, bets)]
    opp = max((tot[j] for j in range(len(tot)) if j != me and in_hand[j]), default=0)
    return {
        "street": obs.street,
        "alive": sum(1 for j in range(len(tot)) if tot[j] > 0 or in_hand[j]),
        "in_hand": sum(1 for x in in_hand if x),
        "eff_bb": min(tot[me], opp) / bb,
        "to_call_bb": obs.to_call / bb,
        "raised": max(bets) > bb if obs.street == 0 else obs.to_call > 0,
        "section": SECTIONS[section(obs)],
    }


def parse_route(spec) -> dict[str, str]:
    """A route as {section: value}. Accepts a dict, or "name=value,name=value"; a key may be a section name, "pre" /
    "post" (every preflop / postflop section) or "*" (all). Later keys override earlier ones."""
    if not spec:
        return {}
    items = spec.items() if isinstance(spec, dict) else (kv.split("=", 1) for kv in str(spec).split(",") if kv.strip())
    out: dict[str, str] = {}
    for k, v in items:
        k = k.strip()
        v = v.strip() if isinstance(v, str) else v
        if k == "*":
            keys = SECTIONS
        elif k == "pre":
            keys = tuple(n for n in SECTIONS if n in PREFLOP)
        elif k == "post":
            keys = tuple(n for n in SECTIONS if n in POSTFLOP)
        elif k in INDEX:
            keys = (k,)
        else:
            raise KeyError(f"unknown section {k!r}; known: {', '.join(SECTIONS)}, pre, post, *")
        for key in keys:
            out[key] = v
    return out


__all__ = ["SECTIONS", "INDEX", "PREFLOP", "POSTFLOP", "SHARES", "section", "section_name", "features", "parse_route"]
