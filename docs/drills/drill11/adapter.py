"""Tonight's adapter: Tranche Hold'em kit (module-level act(v) -> int chips added now).

Native state `v`: hole/board ints (4*rank+suit, rank 0 = deuce, suits c d h s = 0..3: ours exactly), street 0..3,
relative seats (0 = me), stacks behind, seats 'p'/'a'/'f'/'x', paid[s][k] chips per tranche, tranches[k], to_call
(capped at stack), min_raise = smallest return that raises (chips added now; 0 = may not raise), full log string.
Answer: an int, the chips to put in now (n < to_call folds / checks, to_call <= n < min_raise calls).
"""
from __future__ import annotations

from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules  # noqa: F401
from hyperion.drills.adapter import Adapter, make_observation
from hyperion.drills.conformance import maybe_checked

N_SEATS = 8

# ---- Stage 5 patch: the two-card twin (Tranche Hold'em). A preflop all-in is settled on the two hole cards alone
# (pair > non-pair, then high card, then kicker, suits never count), so where a preflop decision is an all-in one the
# bot is shown the hold'em class at the same combo percentile as our hand's two-card rank. 0 = off.
TWIN_BB = 1000
TWIN_CALL_FRAC = 0.4
_RANKS = "23456789TJQKA"
_TWIN: dict = {}


def _build_twin() -> None:
    try:
        from hyperion.strategy import tables as _tables

        rank = _tables.load().rank  # hold'em class -> midpoint combo percentile from the bottom
        items = sorted(rank.items(), key=lambda kv: kv[1])
        keys = []  # two-card classes, weakest first: non-pairs by (high, low), then pairs
        for hi in range(1, 13):
            for lo in range(0, hi):
                keys.append((hi, lo, 16))
        for r in range(13):
            keys.append((r, r, 6))
        total = float(sum(k[2] for k in keys))
        below = 0
        for hi, lo, n in keys:
            pct = (below + n / 2.0) / total
            below += n
            best = min(items, key=lambda kv: abs(kv[1] - pct))[0]
            a, b = _RANKS.index(best[0]), _RANKS.index(best[1])
            if a == b:
                cards = (a * 4, a * 4 + 1)
            elif best.endswith("s"):
                cards = (a * 4 + 3, b * 4 + 3)
            else:
                cards = (a * 4 + 3, b * 4 + 2)
            _TWIN[(hi, lo)] = cards
    except Exception:  # noqa: BLE001 - no twin: the bot sees its real cards
        _TWIN.clear()


def twin_hole(hole, street, stacks, bets, in_hand, to_call, bb):
    """The hole cards the bot is shown: the twin preflop when the decision is an all-in one, else the real ones."""
    if not TWIN_BB or street != 0 or not _TWIN or len(hole) != 2:
        return hole
    try:
        mine = stacks[0] + bets[0]
        other = max((stacks[s] + bets[s] for s in range(1, len(stacks)) if in_hand[s]), default=0)
        eff = min(mine, other)
        if eff > TWIN_BB * bb and not (stacks[0] > 0 and to_call >= TWIN_CALL_FRAC * stacks[0]):
            return hole
        r1, r2 = hole[0] >> 2, hole[1] >> 2
        hi, lo = (r1, r2) if r1 >= r2 else (r2, r1)
        tw = _TWIN.get((hi, lo))
        return list(tw) if tw else hole
    except Exception:  # noqa: BLE001
        return hole


def card(native_card: Any) -> int:
    """TODO 1: kit cards are already rank*4 + suit with our rank and suit order."""
    return int(native_card)


_KINDS = {"f": ActionKind.FOLD, "k": ActionKind.CHECK, "c": ActionKind.CALL, "r": ActionKind.RAISE}


def history(log: Any) -> list[tuple[int, Action]]:
    """TODO 7b: the kit's log string -> [(relative seat, Action)], raises as raise-TO totals for the street.
    Blind posts (s, b) and uncalled returns (u) are not decisions: they only move the street contributions."""
    out: list[tuple[int, Action]] = []
    if not log:
        return out
    try:
        streets = str(log).split("/")
    except Exception:  # noqa: BLE001
        return out
    for part in streets:
        contrib = [0] * N_SEATS
        for tok in part.split():
            try:
                t = tok.rstrip("!")
                seat = int(t[0])
                code = t[1]
                chips = int(t[2:]) if len(t) > 2 else 0
                if code in ("s", "b"):
                    contrib[seat] += chips
                    continue
                if code == "u":
                    contrib[seat] -= chips
                    continue
                kind = _KINDS.get(code)
                if kind is None:
                    continue
                if kind is ActionKind.RAISE:
                    contrib[seat] += chips
                    out.append((seat, Action(kind, contrib[seat])))
                else:
                    if kind is ActionKind.CALL:
                        contrib[seat] += chips
                    out.append((seat, Action(kind, 0)))
            except Exception:  # noqa: BLE001 - a malformed token costs one history line, not the decision
                continue
    return out


class TonightAdapter(Adapter):
    """Tranche Hold'em kit: v (relative seats, paid per tranche, log string) -> Observation; Action -> int chips."""

    history_source = "log"

    def to_observation(self, v: Any) -> Observation:
        street = int(v.street)
        paid = v.paid
        bets = [int(paid[s][street]) for s in range(N_SEATS)]  # TODO 3: this street's chips per seat
        pot = int(sum(v.tranches)) - sum(bets)  # previous streets only
        stacks = [int(x) for x in v.stacks]  # chips behind
        in_hand = [c in "pa" for c in v.seats]  # TODO 6: relative seats, 0 = me
        to_call = int(v.to_call)
        mr = int(v.min_raise)
        legal = []
        if to_call > 0:
            legal += ["fold", "call"]
        else:
            legal.append("check")
        if mr > 0:
            legal.append("raise")
        my_bet = bets[0]
        hole = twin_hole([card(c) for c in v.hole], street, stacks, bets, in_hand, to_call, int(v.bb))
        return make_observation(
            hole=hole, board=[card(c) for c in v.board], street=street, seat=0,
            button=int(v.button), stacks=stacks, bets=bets, in_hand=in_hand, pot=pot, to_call=to_call,
            min_raise=(my_bet + mr) if mr > 0 else None, max_raise=(my_bet + stacks[0]) if mr > 0 else None,
            legal=legal, hand_no=int(v.hand), blinds=(int(v.sb), int(v.bb)), history=history(v.log),
        )

    def from_action(self, action: Action, obs: Observation, v: Any) -> Any:
        to_call = int(v.to_call)
        kind = action.kind
        if kind is ActionKind.FOLD:
            return 0 if to_call == 0 else -1
        if kind is ActionKind.CHECK:
            return 0
        if kind is ActionKind.CALL:
            return to_call
        # RAISE: our raise-TO total -> chips added now
        mr = int(v.min_raise)
        stack = int(v.stack)
        if mr <= 0:
            return to_call
        add = int(action.amount) - int(obs.bets[0])
        if add < mr:
            add = mr
        if add > stack:
            add = stack
        return int(add)

    def native_safe(self, v: Any) -> Any:
        return 0  # the kit's check-if-possible-else-fold


def make_adapter(bot: Any, rules: Rules | None = None) -> TonightAdapter:
    if TWIN_BB and not _TWIN:
        _build_twin()
    return maybe_checked(TonightAdapter(bot, rules))
