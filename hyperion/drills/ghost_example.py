"""Ghost Hold'em (drill 8, kit F) as a variant file: a payoff twist that moves a pot into the next hand.

Kit F's rule (docs/drills/drill8/kitF-README.md, section 2): every hand deals a ninth, face-down two-card hand, the
Ghost. When a pot reaches a showdown with two or more players eligible for it, the Ghost's best hand is compared with
the best hand among them. If the Ghost's is strictly better, nobody wins that pot: it haunts. Haunted chips go into the
next hand's main pot as dead money (the Haunt), won by whoever wins that pot, by showdown or by fold. Ties go to the
players. Each side pot is checked on its own. Pots won without a showdown never haunt. The Ghost never ends a table:
if haunting would leave nobody with chips, it is ignored for that hand. A Haunt left when the table ends is discarded.

The hooks (hyperion/sim/engine.py's header; hyperion/drills/variants.py's contract):
  on_deal        deals the Ghost from the undealt cards (never on the board or in a hand).
  after_forced   puts the Haunt into this hand's pot (obs.pot shows it, as kit F's `s.pot` does) and publishes it as
                 obs.extras["haunt"] (kit F's `s.haunt`).
  settle         replaces the engine's award with kit F's: the pots built from the contributions (a layer only one
                 player paid is returned), the Haunt in the main pot, each pot with two or more eligible players
                 checked against the Ghost, the haunted chips kept for the next hand.
  result_extras  HandResult.extras["ghost"]: the Ghost's cards (at a showdown), each pot and its winners (empty =
                 haunted), the chips haunted and the Haunt this hand started with.
The hooks object lives for one table (runner and climb build one per table), so the Haunt carries from hand to hand and
is dropped with the hooks at the table's end.

Kit F's other rules are Rules, not hooks: its blind schedule (10/20 ... 250/500, 25 hands a level), points
16/11/8/6/4/2/1/0, and survivors at the 200-hand cap placed by chip count (Rules.extras["cap_places"] = "chips", the
engine's option). The same rules without the variant's name are docs/drills/drill8/rules_ghost.json: there Hero is not
told a twist is on, as kit F's packed bot was not (its rules_tonight.json has no extras).

    .venv/bin/python -m hyperion.sim --field realistic@ship --variant hyperion/drills/ghost_example.py:variant
    .venv/bin/python -m hyperion.sim.generic --prepare hyperion/drills/ghost_example.py:variant
    .venv/bin/python tools/climb_accept.py --stages aware --aware generic:hyperion/drills/ghost_example.py:variant \
        --base '' --cand '' --set screen --workers 2

Differs from kit F, all minor: the first button is seat `rotation` (kit F: a random seat); busting players who started
the hand with exactly the same stack get the seat order (kit F: they share the places); preflop the call is the largest
actual bet (kit F: the full big blind when the big blind is all-in short).
"""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks

KIT_F_BLINDS = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
KIT_F_POINTS = (16, 11, 8, 6, 4, 2, 1, 0)


class GhostHooks(VariantHooks):
    """The Ghost and the Haunt for one table (module doc). `haunt`: dead money in this hand's main pot; `carry`: the
    chips haunted this hand, the next hand's Haunt."""

    def __init__(self) -> None:
        self.haunt = 0
        self.carry = 0
        self.ghost = None
        self.last: dict = {}
        # the kit simulator's table statistics, for validation (hyperion/sim/runner does not read them)
        self.stats = {"hands": 0, "showdowns": 0, "haunts": 0, "haunted_chips": 0, "ghost_kos": 0}

    # -- the deal and the Haunt
    def on_deal(self, holes, deck, rng):
        self.ghost = (deck.pop(), deck.pop()) if len(deck) >= 2 else None
        self.last = {}
        return holes

    def after_forced(self, table, hand) -> None:
        self.haunt, self.carry = self.carry, 0
        if self.haunt:
            hand.pot += self.haunt  # dead money: in the pot, in no one's contribution; settle pays it

    def extras(self, hand) -> dict:
        return {"haunt": self.haunt}

    def restore(self, extras: dict, board) -> None:
        """A rollout from a known state (hyperion/sim/generic.py) prices the pot it is given: the Haunt is already in
        that pot, so nothing is carried, and the Ghost is dealt afresh from the unseen cards."""
        self.haunt = self.carry = 0
        self.ghost = None
        self.last = {}

    # -- the showdown
    def settle(self, table, hand) -> None:
        """Kit F's settlement, replacing the engine's award. The chips behind before any award are the hand's start
        stacks less the contributions (this variant charges nothing else); dead money in hand.dead (none in play; a
        rollout's probe may put a pot's excess there) joins the main pot as the Haunt does."""
        n = table.n
        stacks, contrib, in_hand = table.stacks, hand.contrib, hand.in_hand
        behind = [hand.stacks_start[s] - contrib[s] for s in range(n)]
        dead_in = self.haunt + (sum(c for _, c in hand.dead) if hand.dead else 0)
        contenders = [s for s in range(n) if in_hand[s]]
        showdown = len(contenders) >= 2
        scores: dict = {}
        g_score = -1
        board = tuple(hand.board)
        if showdown:
            ev, rules = table.variant.evaluate, table.rules
            if self.ghost is None:
                spare = getattr(hand, "spare", None) or []
                self.ghost = (spare.pop(), spare.pop()) if len(spare) >= 2 else None
            scores = {s: ev(hand.holes[s], board, rules) for s in contenders}
            if self.ghost is not None:
                g_score = ev(self.ghost, board, rules)
        # the pots, main first: one layer per contribution level; a layer only one player paid goes back to them
        refund = [0] * n
        pots: list = []
        prev = carry = 0
        for lvl in sorted({c for c in contrib if c > 0}):
            payers = [s for s in range(n) if contrib[s] >= lvl]
            amt = (lvl - prev) * len(payers) + carry
            carry, prev = 0, lvl
            if len(payers) == 1:
                refund[payers[0]] += amt
                continue
            elig = [s for s in payers if in_hand[s]]
            if not elig:
                if pots:
                    pots[-1][0] += amt
                else:
                    carry = amt
                continue
            if pots and pots[-1][1] == elig:
                pots[-1][0] += amt
            else:
                pots.append([amt, elig])
        if dead_in or carry:
            if pots:
                pots[0][0] += dead_in + carry
            else:
                pots.append([dead_in + carry, contenders])
        b = hand.button

        def resolve(use_ghost: bool):
            won = list(refund)
            recs, haunted, h_elig = [], 0, set()
            for amt, elig in pots:
                if len(elig) == 1:
                    won[elig[0]] += amt
                    recs.append((amt, (elig[0],)))
                    continue
                best = max(scores[s] for s in elig)
                if use_ghost and g_score > best:
                    haunted += amt
                    h_elig.update(elig)
                    recs.append((amt, ()))
                    continue
                winners = sorted((s for s in elig if scores[s] == best), key=lambda s: (s - b - 1) % n)
                share, rem = divmod(amt, len(winners))
                for i, s in enumerate(winners):
                    won[s] += share + (1 if i < rem else 0)
                recs.append((amt, tuple(winners)))
            return won, recs, haunted, h_elig

        won, recs, haunted, h_elig = resolve(True)
        if haunted and not any(behind[s] + won[s] > 0 for s in range(n)):
            won, recs, haunted, h_elig = resolve(False)  # the Ghost never ends a table
        for s in range(n):
            stacks[s] = behind[s] + won[s]
        self.carry = haunted
        st = self.stats
        st["hands"] += 1
        if showdown:
            st["showdowns"] += 1
        if haunted:
            st["haunts"] += 1
            st["haunted_chips"] += haunted
            st["ghost_kos"] += sum(1 for s in h_elig if hand.stacks_start[s] > 0 and stacks[s] == 0)
        self.last = {"ghost": self.ghost if showdown else None, "pots": recs, "haunted": haunted,
                     "haunt_in": self.haunt, "showdown": showdown}

    def result_extras(self, hand) -> dict:
        return {"ghost": dict(self.last)}


def ghost_rules(named: bool = True) -> Rules:
    """Kit F's table rules; `named` adds Rules.extras["variant"] (the generic bots and Hero's twin tables find the
    hooks by it; Hero also reads any named twist as one, which kit F's packed bot did not)."""
    extras = {"cap_places": "chips"}
    if named:
        extras = {"variant": "ghost", **extras}
    return Rules(blind_levels=KIT_F_BLINDS, payouts=KIT_F_POINTS, extras=extras)


def variant() -> Variant:
    return Variant(
        name="ghost",
        summary="Ghost Hold'em (kit F): a ninth face-down hand at every showdown. A showdown pot whose best hand the "
                "Ghost strictly beats goes to nobody and becomes dead money in the next hand's main pot, won by "
                "whoever wins that pot, by showdown or by fold. Side pots are checked one by one; ties go to the "
                "players; the Ghost never ends a table; a Haunt left at the table's end is discarded.",
        rules=ghost_rules(named=True),
        breaks="Every showdown is taxed: one pair loses to the Ghost 56% of the time, two pair 31%. Plain equity "
               "overprices thin value and calls with one pair; a pot won by a bet that makes everyone fold is never "
               "haunted. The hand after a haunt carries dead money in obs.pot (and obs.extras['haunt']).",
        checklist=("python -m hyperion.sim.generic --prepare hyperion/drills/ghost_example.py:variant",),
        hooks_factory=GhostHooks,
        needs_engine=True,
        axis="payoff",
        playable_note="settle replaces the engine's award with kit F's; the Haunt is dead money in hand.pot",
    )
