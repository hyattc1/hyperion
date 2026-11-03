"""Payoff by street (drill 11's Tranche Hold'em; V-j): the reads a bot needs on a table that settles each street's chips
on the hand as it stood on that street (Rules.extras["settle"] == "street"), or settles an all-in on the cards already
out (Rules.extras["no_runout"]). The engine's side is hyperion/sim/engine.py's module doc. Stdlib and core only, every
table built once per process from the rule (never from a kit).

  street_settled(rules), no_runout(rules)   the two rules
  two_card_key(hole)    (high rank, low rank) of two canonical cards; suits never count
  TWO_CARD_KEYS         the 91 keys, weakest first: non-pairs by (high, low), then the pairs (evaluate_short's order)
  beat_share(key)       the chance the two-card hand beats one random two-card hand (ties half), exact with removal
  twin_map(rank)        key -> the hold'em class at the same combo percentile (a pair is 6 combos, a non-pair 16:
                        suits never count), given a hold'em class -> percentile map such as Tables.rank
  twin_cards(cls)       two cards for a hold'em class label (spades and hearts; the suits say suited or not)
  now_share(...)        the chance the hand as it is now beats n random holdings on this board (sampled; two cards by
                        beat_share, exact), the read of the street's own tranche: no card to come counts
"""
from __future__ import annotations

from ..core.eval import evaluate, evaluate_short
from ..core.types import RANKS, Rules


def street_settled(rules: Rules) -> bool:
    return (rules.extras or {}).get("settle") == "street"


def no_runout(rules: Rules) -> bool:
    return bool((rules.extras or {}).get("no_runout"))


def two_card_key(hole) -> tuple[int, int]:
    a, b = hole[0] >> 2, hole[1] >> 2
    return (a, b) if a >= b else (b, a)


TWO_CARD_KEYS: tuple = tuple([(hi, lo) for hi in range(1, 13) for lo in range(hi)] + [(r, r) for r in range(13)])
_ORDER = {k: i for i, k in enumerate(TWO_CARD_KEYS)}  # strength index, weakest 0
_BEAT: dict = {}


def _build_beat() -> None:
    for key in TWO_CARD_KEYS:
        left = [4] * 13
        left[key[0]] -= 1
        left[key[1]] -= 1
        mine = _ORDER[key]
        win = tie = 0.0
        total = 0.0
        for k2 in TWO_CARD_KEYS:
            h, lo = k2
            n = left[h] * (left[h] - 1) / 2 if h == lo else left[h] * left[lo]
            if n <= 0:
                continue
            total += n
            o = _ORDER[k2]
            if o < mine:
                win += n
            elif o == mine:
                tie += n
        _BEAT[key] = (win + 0.5 * tie) / total


def beat_share(key) -> float:
    """P(this two-card hand beats one random two-card hand from the other 50 cards), ties counted half."""
    if not _BEAT:
        _build_beat()
    return _BEAT[key]


def twin_map(rank: dict) -> dict:
    """Two-card key -> the hold'em class (a key of `rank`) whose percentile in `rank` (class -> midpoint combo
    percentile from the bottom, as Tables.rank) is nearest the key's own midpoint percentile in the two-card order."""
    items = sorted(rank.items(), key=lambda kv: kv[1])
    vals = [v for _, v in items]
    combos = [6 if hi == lo else 16 for hi, lo in TWO_CARD_KEYS]
    total = float(sum(combos))
    out, below = {}, 0
    from bisect import bisect_left

    for key, n in zip(TWO_CARD_KEYS, combos):
        pct = (below + n / 2.0) / total
        below += n
        j = bisect_left(vals, pct)
        if j >= len(vals) or (j > 0 and pct - vals[j - 1] <= vals[j] - pct):
            j -= 1
        out[key] = items[max(0, j)][0]
    return out


def twin_cards(cls: str) -> tuple[int, int]:
    a, b = RANKS.index(cls[0]), RANKS.index(cls[1])
    if a == b:
        return (a * 4 + 3, a * 4 + 2)
    if cls.endswith("s"):
        return (a * 4 + 3, b * 4 + 3)
    return (a * 4 + 3, b * 4 + 2)


_TWIN_CACHE: dict = {}


def twin_cards_map(rank: dict) -> dict:
    """key -> twin_cards(twin_map(rank)[key]), once per `rank` object."""
    k = id(rank)
    m = _TWIN_CACHE.get(k)
    if m is None or m[0] is not rank:
        tm = twin_map(rank)
        m = _TWIN_CACHE[k] = (rank, {key: twin_cards(c) for key, c in tm.items()}, tm)
    return m[1]


def score_now(hole, board) -> int:
    """The hand as it is now: core.eval from five cards on, evaluate_short below."""
    cards = tuple(hole) + tuple(board)
    return evaluate(cards) if len(cards) >= 5 else evaluate_short(cards)


def now_share(hole, board, n_opp: int, rng, samples: int = 32, dead=()) -> float:
    """P(the hand as it is now beats each of `n_opp` random holdings on this board; ties shared), the read a street's
    own tranche is settled on (and an all-in with no runout). Two cards and no board: beat_share ** n_opp, exact
    against independent hands. Otherwise `samples` deals of the opponents' cards from the unseen deck."""
    hole, board = tuple(hole), tuple(board)
    n_opp = max(1, n_opp)
    if not board and len(hole) == 2:
        return beat_share(two_card_key(hole)) ** n_opp
    gone = set(hole) | set(board) | set(dead)
    stub = [c for c in range(52) if c not in gone]
    k = len(hole)
    if k * n_opp > len(stub):
        return 0.5
    mine = score_now(hole, board)
    acc = 0.0
    sample = rng.sample
    for _ in range(samples):
        pick = sample(stub, k * n_opp)
        ties = 1
        lost = False
        for i in range(n_opp):
            s = score_now(pick[k * i:k * i + k], board)
            if s > mine:
                lost = True
                break
            if s == mine:
                ties += 1
        if not lost:
            acc += 1.0 / ties
    return acc / samples
