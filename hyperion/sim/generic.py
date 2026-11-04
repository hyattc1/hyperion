"""Generic variant-aware opponents: archetypes that read the table's Rules and the variant's own hooks; no per-twist
code.

hyperion/sim/aware.py hand-builds aware opponents for four twists. On the night every team's bot knows the twist, and it
may be one we never catalogued, so a field that adapts only where we wrote code overstates us. These three adapt to any
variant the engine can play, because they decide through the same code the engine uses for it:

  gen_mc        the Monte Carlo archetype (AwareMC's play: bet at 0.6, raise at 0.75, call when the value beats the
                price by 0.05 plus up to 0.15 more as the bet grows to the pot) on a VALUE SHARE: the share of the pot
                (after the call) the hand gets back, averaged over runouts dealt and scored by the variant's hooks:
                on_street (discards, swaps, bought cards, a second board), next_card (boards of any length), the
                showdown (score_hand or score_splits: rank orders, short decks, wild cards, lowball, must-use, split
                pots), on_payout (bounties: winning can pay more than the pot) and settle (a payoff the engine applies
                after its award, priced on a probe hand through the engine's own award and the hook: a showdown pot
                that goes to nobody, as in Ghost Hold'em). Against min(opponents, 3) random
                holdings, a bounded number of runouts (the variant's measured cost, below). Preflop: AwareMC's Chen
                thresholds on the Chen score of the hold'em class at the same percentile of the variant's own preflop
                table, two points looser when winning the pot now pays more than the pot, one when antes make the
                forced bets two big blinds or more; a live straddle is its big blind preflop.
  gen_tag       ChartTAG: its charts applied to the hand's hold'em twin (the class at the same combo percentile of the
                variant's table, so it opens the same share of hands, the variant's best ones); postflop its reads
                "top pair or better" and "two pair or better" become MADE SHARES (the share of random holdings the hand
                beats on this board under the variant's showdown) at the thresholds that agree best with those reads
                in hold'em (H_STRONG, H_BIG). One notch wider preflop, and a half-pot bet when checked to in a pot of
                three or fewer, while winning the pot now pays at least 1.1 times the pot (the payoff hook says so).
                From the Rules: one notch wider when antes (and blinds) reach two big blinds before anyone acts, and a
                live straddle read as the big blind preflop (sizes, facing a raise, stack depth).
  gen_pushfold  PushFoldBot the same way (re-cut ranges, made-share reads, the same payoff lever).

All three answer the engine's variant decisions by type, whatever the twist: discard (an index), keep (indices), swap
(an index or -1), buy_card (yes or no), bid (chips), each option priced by the same value share; any other decision
gets None (the hook's default).

How they find the variant: Rules.extras["variant"] through hyperion.drills.variants.get (the catalog, the held-out
set, or a file registered with `variants.get("path/to/file.py:factory")`), a private hooks object per table. Public
per-hand state comes back from Observation.extras: hooks.restore(extras, board) when the hooks define it, else every
extras key that names one of the hooks' attributes is copied in (bounties, discards, revealed, exposed). Cards in
extras are known: keys about discards, reveals, boards, shown or folded cards are dead; keys about exposed or face-up
cards stay in that seat's hand (`public_cards`).

The variant's table: `prepare(name)` (`python -m hyperion.sim.generic --prepare NAME|all`) writes
tables/generic/<name>-<hash>.json once: the preflop value share of every hole class against one random hand, dealt
and scored through the hooks from the deal (169 classes stratified, or best2+tags labels sampled for 3+ hole cards),
the measured cost of a showdown score and of a runout (which fixes each bot's sample counts, so play is deterministic
once the file exists), and score quantiles per board length (the fallback read for a showdown too slow to sample).
Hold'em-shaped card rules with no card hooks reuse tables/preflop_equity.json, so on hold'em the twins are the
classes themselves. Missing at table start, the table is built in-process with a smaller budget and cached under
scratch/generic/ (not committed).

Never in a night pool; the `generic_aware` field (hero, montecarlo30, gen_mc, gen_pushfold, loose_aggro, rival1,
gen_tag, timeout_then_recover: the aware fields' shape) plays under any `--variant` (tools/climb_accept.py
`--aware generic:NAME` or `generic:all`).
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import math
import os
import random
import sys
import time
from bisect import bisect_left, bisect_right
from itertools import combinations
from typing import Optional

from ..core.cards import deck_for, hole_class, is_identity_order
from ..core.eval import evaluate, evaluate_many, warm
from ..core.types import RANKS, Action, Observation, Rules
from . import bestiary as _B
from .aware import AwareMC, pushfold_postflop, pushfold_preflop, tag_postflop, tag_preflop
from .bestiary import RAISE, ChartTAG, PushFoldBot, _check_or_fold, _raise_or_call, chen_score, players_behind

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TABLE_DIR = os.path.join(_ROOT, "tables", "generic")  # prepared tables (committed for the catalog)
CACHE_DIR = os.path.join(_ROOT, "scratch", "generic")  # tables a bot built for itself at table start (not committed)
_REFERENCE = os.path.join(_ROOT, "tables", "preflop_equity.json")

# Per-decision budgets in nanoseconds of the variant's measured cost (the table file's "cost"). gen_mc's runouts, the
# reads' made shares and a variant decision's options each get one; a bot that cannot afford MIN samples of its read
# falls back to the next cheaper one (runouts against every opponent -> heads-up runouts to the power of the opponents
# -> made share -> the score's quantile at this board length).
B_MC = 240_000
B_HS = 80_000
B_DEC = 120_000
MAX_MC, MAX_HS, MIN_SAMPLES = 64, 48, 10
# The made-share thresholds that agree best with ChartTAG's / PushFoldBot's reads in hold'em, by board length 3 / 4 /
# 5+ (random two-card hands and boards, 10,000 spots each, made share against every opponent holding; scratch script
# in docs/drills/climb/vd-log.md): "top pair or better" (strong) and "two pair or better" (big).
H_STRONG = {3: 0.850, 4: 0.815, 5: 0.550}
H_BIG = {3: 0.970, 4: 0.925, 5: 0.560}
PAYOFF_HIT = 1.1  # winning the pot now pays at least this many times the pot: the payoff lever
_MISSING = object()


# ----- the variant ---------------------------------------------------------------------------------------------------


def variant_of(rules: Rules):
    """The catalog (or registered) Variant Rules.extras["variant"] names; None for plain hold'em or an unknown name."""
    from ..drills import variants as V

    name = (rules.extras or {}).get("variant")
    if not name:
        return None
    try:
        return V.get(str(name), seed=int((rules.extras or {}).get("seed", 0) or 0))
    except (KeyError, ValueError, TypeError):
        return None


def _overrides(h, name: str) -> bool:
    from ..drills.variants import VariantHooks

    return getattr(type(h), name, None) is not getattr(VariantHooks, name, None)


def _seatify(v):
    """Extras as the hooks keep them: dicts keyed by seat number (JSON-ish string keys back to ints)."""
    if isinstance(v, dict):
        return {(int(k) if isinstance(k, str) and k.lstrip("-").isdigit() else k): _seatify(x) for k, x in v.items()}
    return v


def _copy(v):
    if isinstance(v, dict):
        return dict(v)
    if isinstance(v, list):
        return list(v)
    if isinstance(v, set):
        return set(v)
    return v


_DEAD_WORDS = ("discard", "reveal", "board", "shown", "show", "fold", "dead", "muck", "burn", "toss")
_HELD_WORDS = ("expos", "face_up", "faceup", "upcard")
_NOT_CARDS = ("price", "bought", "bid", "winner", "count", "bount", "rank", "swapped", "order", "street", "pot", "chip")


def _cards_in(v, out: set) -> None:
    if isinstance(v, bool):
        return
    if isinstance(v, int):
        if 0 <= v < 52:
            out.add(v)
    elif isinstance(v, dict):
        for x in v.values():
            _cards_in(x, out)
    elif isinstance(v, (list, tuple, set, frozenset)):
        for x in v:
            _cards_in(x, out)


def public_cards(extras: dict, me: int, in_hand=None) -> tuple[set, dict]:
    """(dead cards, {seat: cards known to be in that seat's hand}) from a variant's public extras (or a decision
    prompt). Exposed / face-up cards of a seat still in the hand stay in its hand; everything else card-like is dead.
    `known` ({seat: cards} from where `me` sits, or {viewer: {seat: cards}}: hyperion/strategy/known.py) is cards a
    seat holds, ours included (a card two players share is in both hands): held while that seat is in the hand."""
    dead: set = set()
    held: dict = {}
    for key, val in (extras or {}).items():
        k = str(key).lower()
        if k == "known":
            if isinstance(val, dict):
                from ..strategy.known import parse

                for s, cards in parse({"known": val}, me).items():
                    if in_hand is None or (0 <= s < len(in_hand) and in_hand[s]):
                        held[s] = tuple(sorted(set(held.get(s, ())) | set(cards)))
            continue
        if any(w in k for w in _NOT_CARDS):
            continue
        if any(w in k for w in _HELD_WORDS) and isinstance(val, dict):
            for s, cards in _seatify(val).items():
                got: set = set()
                _cards_in(cards, got)
                if s == me:
                    continue
                if isinstance(s, int) and (in_hand is None or (0 <= s < len(in_hand) and in_hand[s])):
                    held[s] = tuple(sorted(got | set(held.get(s, ()))))
                else:
                    dead |= got
        elif any(w in k for w in _DEAD_WORDS):
            _cards_in(val, dead)
    return dead, held


# ----- the simulator: the hand's remainder through the variant's own hooks -------------------------------------------


class Sim:
    """Rolls a hand out from a known state through one private hooks object (see the module doc)."""

    MAX_OPP = 3
    SLACK = 8  # random spare cards on top of the deck hooks pop from (swaps, bought cards, a run of extra boards);
    # below them the rest of the deck in a per-call shuffled order
    RUN_MAX = 30

    def __init__(self, rules: Rules, variant=None):
        from ..drills.variants import VariantHooks

        self.rules = rules
        hooks = variant.new_hooks() if variant is not None else None
        self.hooks = h = hooks if hooks is not None else VariantHooks()
        removed = set((rules.extras or {}).get("removed_ranks") or ())
        self.deck = tuple(c for c in deck_for(rules) if (c >> 2) not in removed)
        self.k = rules.hole_cards
        self.sizes = tuple(rules.board_sizes)
        self.final = self.sizes[-1]
        self.n_seats = rules.n_players
        self.on_deal = h.on_deal if _overrides(h, "on_deal") else None
        self.on_street = h.on_street if _overrides(h, "on_street") else None
        nc = getattr(h, "next_card", None)
        self.next_card = nc if callable(nc) else None
        sp = getattr(h, "score_splits", None)
        self.splits = sp if callable(sp) else None
        self.payout = h.on_payout if _overrides(h, "on_payout") else None
        self.view = bool(getattr(h, "wants_view", False))
        st = getattr(h, "settle", None)
        self.settle = st if callable(st) else None  # a payoff the engine applies after its award: priced by _probe
        self.fast = (not _overrides(h, "score_hand")) and not rules.must_use_hole and is_identity_order(rules)
        sh = h.score_hand
        self._score = None if self.fast else (lambda hole, board, _sh=sh, _r=rules: _sh(hole, board, _r))
        # payoff by street (Rules.extras settle="street", the engine's rule: V-j): this street's chips are won by the
        # hand as it is now, so the showdown is scored on the board as it stands, with no runout (two cards alone
        # preflop: evaluate_short below five cards); the earlier streets' chips are not priced apart
        self.now = (rules.extras or {}).get("settle") == "street"
        if self.now:
            self.fast = False
            self._score = (lambda hole, board, _sh=sh, _r=rules: _sh(hole, board, _r)
                           if len(hole) + len(board) >= 5 else _short(hole, board, _r))
        # settle keeps state (and may deal from the unseen cards), so it runs on the dynamic path: hooks reset and
        # spare cards per runout
        self.dynamic = self.on_street is not None or self.next_card is not None or self.settle is not None
        self._stub = None  # (Table, HooksVariant) for _probe, built on first use
        self._fresh = {k: _copy(v) for k, v in vars(h).items()}
        self._snap: Optional[dict] = None
        self._restore = getattr(h, "restore", None)
        warm(5 if rules.must_use_hole else min(8, rules.hole_cards + self.final))

    def holdem_cards(self) -> bool:
        """The hand is hold'em's: default card rules and no hook that deals, scores or pays differently."""
        d, r = Rules(), self.rules
        ex = r.extras or {}
        return ((r.hole_cards, tuple(r.board_sizes), tuple(r.rank_order), r.n_suits, r.must_use_hole)
                == (d.hole_cards, tuple(d.board_sizes), tuple(d.rank_order), d.n_suits, d.must_use_hole)
                and not ex.get("removed_ranks") and not ex.get("keep") and self.fast
                and self.on_deal is None and self.dynamic is False and self.splits is None and self.payout is None
                and self.settle is None and not self.now)

    # -- scores
    def score(self, hole, board):
        if self.fast:
            cards = tuple(hole) + tuple(board)
            return evaluate(cards) if len(cards) <= 8 else evaluate_many(cards)
        return self._score(tuple(hole), tuple(board))

    def scores(self, hole, board) -> tuple:
        """One score per pot share (a tuple; None = does not qualify)."""
        if self.splits is not None:
            return tuple(self.splits(tuple(hole), tuple(board), self.rules))
        return (self.score(hole, board),)

    # -- state
    def sync(self, extras: dict, board=()) -> None:
        """Reset the hooks to their fresh state, then restore the hand's public state from extras."""
        h = self.hooks
        for k, v in self._fresh.items():
            setattr(h, k, _copy(v))
        ex = extras or {}
        if callable(self._restore):
            self._restore(ex, tuple(board))
        else:
            for key, val in ex.items():
                if not isinstance(key, str):
                    continue
                cur = getattr(h, key, _MISSING)
                if cur is _MISSING or callable(cur):
                    continue
                setattr(h, key, _seatify(val))
        self._snap = {k: _copy(v) for k, v in vars(h).items()} if self.dynamic or self.on_deal is not None else None

    def _reset(self) -> None:
        if self._snap is not None:
            h = self.hooks
            for k, v in self._snap.items():
                setattr(h, k, _copy(v))

    # -- the runout
    def rollout(self, hole, board, seat: int, opps, n: int, rng: random.Random, *, street: int = -1, dead=(),
                held=None, pot: int = 0, contrib: int = 0, hand_no: int = 0, view: Optional[dict] = None,
                from_deal: bool = False, my_extra: int = 0, opp_extra: int = 0, opp_k: Optional[int] = None,
                rest: Optional[list] = None):
        """Mean value share of `hole` over n runouts against random holdings in `opps` (seats): the share of the pot it
        wins at showdown (split columns and ties shared), after the payoff hook when there is one (pot / contrib: the
        pot and our chips in it, as at showdown). `street`: the betting round we are in (the hooks act from the next
        one); `from_deal` runs on_deal first (the preflop table). `my_extra` / `opp_extra`: random cards added to our
        hand / the first opponent's (a card swapped in, bought, or won at auction). `rest`: a shuffled deck to draw the
        hooks' spare cards from, shared by the calls of one decision (known cards are left out here). None when the
        deck is too small."""
        held = held or {}
        hole, board = tuple(hole), tuple(board)
        known = set(hole) | set(board) | set(dead)
        for s in opps:
            known.update(held.get(s, ()))
        stub = [c for c in self.deck if c not in known]
        if opp_k is None:
            opp_k = min(len(hole) + my_extra, self.k)
        needs = [max(0, opp_k - len(held.get(s, ()))) + (opp_extra if i == 0 else 0) for i, s in enumerate(opps)]
        board_need = 0 if self.now else max(0, self.final - len(board))
        base = my_extra + sum(needs) + board_need
        if base > len(stub) or n <= 0:
            return None
        dyn = self.dynamic or from_deal
        take = base + (min(self.SLACK, len(stub) - base) if dyn else 0)
        if dyn and rest is None:
            rest = list(stub)
            rng.shuffle(rest)
        if street < 0:
            street = max(i for i, sz in enumerate(self.sizes) if sz <= len(board))
        sizes, final, rules, h = self.sizes, self.final, self.rules, self.hooks
        on_street, next_card, splits, payout = self.on_street, self.next_card, self.splits, self.payout
        on_deal = self.on_deal if from_deal else None
        score = self.score
        nseat = max(self.n_seats, seat + 1, max(opps, default=0) + 1)
        contenders = [seat] + list(opps)
        sample = rng.sample
        acc, got = 0.0, 0
        for _ in range(n):
            pick = sample(stub, take)
            holes = [()] * nseat
            holes[seat] = hole + tuple(pick[:my_extra]) if my_extra else hole
            i = my_extra
            for s, need in zip(opps, needs):
                holes[s] = held.get(s, ()) + tuple(pick[i:i + need])
                i += need
            runout = pick[i:i + board_need]
            if not dyn:
                b = board + tuple(runout)
            else:
                used = known.union(pick)
                spare = [c for c in rest if c not in used] + pick[i + board_need:]  # hooks pop from the end
                self._reset()
                try:
                    if on_deal is not None:
                        holes = list(on_deal(holes, spare, rng))
                    full = list(board) + runout
                    if on_street is not None:
                        for st in range(street + 1, len(sizes)):
                            cur = tuple(full[:sizes[st]])
                            if self.view and view is not None:
                                h.view = view
                            nb, holes = on_street(st, cur, holes, spare, rng, None)
                            nb = tuple(nb)
                            if nb != cur:
                                full[:len(nb)] = list(nb)
                            ch = getattr(h, "charges", None)
                            if ch:
                                ch.clear()
                    b = tuple(full[:max(final, len(board))])
                    if next_card is not None:
                        st = len(sizes)
                        for _r in range(self.RUN_MAX):
                            c = next_card(st, b, spare, rng)
                            if c is None:
                                break
                            b = b + (c,)
                            st += 1
                except Exception:  # noqa: BLE001 - a hook that cannot play this sample: skip it
                    continue
            # showdown
            if self.settle is not None:
                share = self._probe(holes, b, seat, opps, pot, contrib, spare)
                if share is None:
                    continue
            elif splits is None:
                mine = score(holes[seat], b)
                best, ties = mine, 1
                lost = False
                for s in opps:
                    v = score(holes[s], b)
                    if v > best:
                        lost = True
                        break
                    if v == best:
                        ties += 1
                share = 0.0 if lost else 1.0 / ties
            else:
                cols = {s: splits(holes[s], b, rules) for s in contenders}
                kk = len(cols[seat])
                share = 0.0
                win0 = None
                for col in range(kk):
                    vals = [(cols[s][col], s) for s in contenders if cols[s][col] is not None]
                    if vals:
                        top = max(v for v, _ in vals)
                        w = [s for v, s in vals if v == top]
                    else:
                        w = win0
                    if col == 0:
                        win0 = w
                    if w and seat in w:
                        share += 1.0 / (kk * len(w))
            if payout is not None and pot > 0:
                deltas = [0] * nseat
                deltas[seat] = int(share * pot) - contrib
                others = pot - contrib
                for s in opps:
                    deltas[s] = -(others // max(1, len(opps)))
                try:
                    out = payout(deltas, holes, b, hand_no, rules, rng)
                    share = (out[seat] + contrib) / pot
                except Exception:  # noqa: BLE001
                    pass
            acc += share
            got += 1
        return acc / got if got else None

    PROBE_STACK = 1_000_000  # chips behind every contender in a probe: no stack ever binds

    def _probe(self, holes, board, seat: int, opps, pot: int, contrib: int, spare) -> Optional[float]:
        """The share of `pot` that `seat` takes at this showdown through the engine's own award and the hooks' settle
        (hyperion.sim.engine.Table._award, then HooksVariant settle): a payoff that moves chips after the award (a pot
        that goes to nobody, a side game) is priced as the table would pay it. The contenders are `seat` and `opps`; I
        put in `contrib`, each opponent as much (capped by what the pot leaves them), and the rest of `pot` is dead
        money every contender is eligible for (folded players' chips, money carried in). `spare`: unseen cards a hook
        may deal from. None when the hooks cannot settle this spot."""
        from .engine import HandState, HooksVariant, Table

        if self._stub is None:
            t = Table.__new__(Table)
            t.rules = self.rules
            t.variant = HooksVariant(self.hooks, t)
            self._stub = t
        t = self._stub
        n = len(holes)
        t.n = n
        k = len(opps)
        if pot <= 0:
            pot, contrib = 100 * (1 + k), 100
        mine = max(0, min(contrib, pot))
        each = min(mine, (pot - mine) // k) if k else 0
        dead = pot - mine - each * k
        big = self.PROBE_STACK
        hs = HandState()
        hs.hand_no, hs.button, hs.history, hs.showdown, hs.extras = 0, n - 1, [], {}, {}
        hs.holes = list(holes)
        hs.board = tuple(board)
        hs.runout = list(board)
        hs.in_hand = [False] * n
        hs.contrib = [0] * n
        for s in [seat] + list(opps):
            hs.in_hand[s] = True
            hs.contrib[s] = mine if s == seat else each
        hs.n_in_hand = k + 1
        hs.stacks_start = [big + c if hs.in_hand[s] else 0 for s, c in enumerate(hs.contrib)]
        hs.pot = pot
        hs.dead = [(frozenset(s for s in range(n) if hs.in_hand[s]), dead)] if dead > 0 else None
        hs.spare = spare if spare is not None else []
        t.stacks = [big if hs.in_hand[s] else 0 for s in range(n)]
        try:
            t._award(hs)
            t.variant.settle(hs)
        except Exception:  # noqa: BLE001 - a hook that cannot settle this sample: skip it
            return None
        return (t.stacks[seat] - big) / pot

    def made_share(self, hole, board, n: int, rng: random.Random, dead=(), opp_k: Optional[int] = None):
        """The share of random holdings (opp_k cards) the hand beats on this board as it stands, under the variant's
        showdown (ties half, split columns averaged). None with fewer than five cards to score or no deck left."""
        hole, board = tuple(hole), tuple(board)
        if len(hole) + len(board) < 5 or n <= 0:
            return None
        opp_k = opp_k or min(len(hole), self.k)
        known = set(hole) | set(board) | set(dead)
        stub = [c for c in self.deck if c not in known]
        if opp_k > len(stub):
            return None
        try:
            mine = self.scores(hole, board)
        except Exception:  # noqa: BLE001
            return None
        kk = len(mine)
        sample = rng.sample
        acc = 0.0
        for _ in range(n):
            theirs = self.scores(tuple(sample(stub, opp_k)), board)
            for c in range(kk):
                a, t = mine[c], theirs[c]
                if a is None:
                    continue
                if t is None or a > t:
                    acc += 1.0
                elif a == t:
                    acc += 0.5
        return acc / (n * kk)

    def win_now_ratio(self, hole, board, seat: int, opps, pot: int, contrib: int, hand_no: int, rng) -> float:
        """What winning the pot uncontested now pays, over the pot (1.0 without a payoff hook)."""
        if self.payout is None or pot <= 0:
            return 1.0
        nseat = max(self.n_seats, seat + 1, max(opps, default=0) + 1)
        holes = [()] * nseat
        holes[seat] = tuple(hole)
        deltas = [0] * nseat
        deltas[seat] = pot - contrib
        for s in opps:
            deltas[s] = -((pot - contrib) // max(1, len(opps)))
        try:
            out = self.payout(deltas, holes, tuple(board), hand_no, self.rules, rng)
        except Exception:  # noqa: BLE001
            return 1.0
        return (out[seat] + contrib) / pot


# ----- the variant's table -------------------------------------------------------------------------------------------


def _combos(cls: str) -> int:
    return 6 if len(cls) == 2 else 4 if cls[2] == "s" else 12


def _short(hole, board, rules: Rules) -> int:
    """A hand under five cards (payoff by street before the flop): core.eval.evaluate_short on canonical cards."""
    from ..core.cards import remap
    from ..core.eval import evaluate_short

    cards = tuple(hole) + tuple(board)
    return evaluate_short(cards if is_identity_order(rules) else remap(cards, rules))


_REF: Optional[list] = None  # hold'em classes, best first by heads-up equity: [(class, share, cumulative share)]


def _reference() -> list:
    global _REF
    if _REF is None:
        with open(_REFERENCE) as fh:
            eq = json.load(fh)
        order = sorted(eq, key=lambda c: (-eq[c][0], c))  # ties by name, as Table orders them
        out, acc = [], 0.0
        for c in order:
            sh = _combos(c) / 1326.0
            acc += sh
            out.append((c, sh, acc, eq[c][0]))
        _REF = out
    return _REF


def _chen_class(cls: str) -> float:
    a, b = RANKS.index(cls[0]), RANKS.index(cls[1])
    if len(cls) == 2:
        return chen_score((a * 4, a * 4 + 1))
    return chen_score((a * 4, b * 4 + (0 if cls[2] == "s" else 1)))


def _hooks_id(hooks) -> str:
    """The hooks class by module and name. A variant file (variants.get("path.py:factory")) is loaded under a module
    name made from its absolute path, so it is named by its path inside the repo instead (else its file name): the
    same file keys the same table wherever the repo is checked out."""
    mod = type(hooks).__module__
    if mod.startswith("hyperion_variant_"):
        f = os.path.abspath(getattr(sys.modules.get(mod), "__file__", "") or "")
        rel = os.path.relpath(f, _ROOT) if f.startswith(_ROOT + os.sep) else os.path.basename(f)
        mod = "file:" + rel.replace(os.sep, "/")
    return mod + "." + type(hooks).__qualname__


def table_key(name: str, rules: Rules, hooks) -> str:
    from ..tablegen import rules_to_dict

    blob = json.dumps({"rules": rules_to_dict(rules), "hooks": _hooks_id(hooks),
                       "hook_state": sorted((k, repr(v)) for k, v in vars(hooks).items()
                                            if isinstance(v, (int, float, str, bool)))}, sort_keys=True, default=str)
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in str(name or "holdem"))[:40]
    return f"{safe}-{hashlib.md5(blob.encode()).hexdigest()[:8]}"


def table_path(key: str, cache: bool = False) -> str:
    return os.path.join(CACHE_DIR if cache else TABLE_DIR, key + ".json")


class Table:
    """A variant's preflop classes (label -> value share, combo share), their hold'em twins and percentiles, the
    measured costs, and the score quantiles per board length."""

    def __init__(self, doc: dict, rules: Rules):
        self.doc, self.rules = doc, rules
        self.k = int(doc.get("k", rules.hole_cards))
        labels = doc["labels"]  # label -> [value share, combo share, samples]
        self.eq = {lb: v[0] for lb, v in labels.items()}
        order = sorted(labels, key=lambda lb: (-labels[lb][0], lb))
        total = sum(labels[lb][1] for lb in order) or 1.0
        ref = _reference()
        cums = [r[2] for r in ref]
        self.twin: dict = {}
        self.pct: dict = {}
        acc = 0.0
        for lb in order:
            sh = labels[lb][1] / total
            q = acc + sh / 2
            acc += sh
            self.pct[lb] = 1.0 - q
            j = min(len(ref) - 1, bisect_left(cums, q))
            self.twin[lb] = ref[j][0]
        self.cost = doc.get("cost", {})
        self.quant = {int(k): v for k, v in (doc.get("quantiles") or {}).items()}
        self._cmap = tuple(rules.rank_order[c >> 2] * 4 + (c & 3) for c in range(52))

    def label(self, hole) -> str:
        if len(hole) == 2:
            return hole_class(tuple(hole))
        from ..tablegen import hole_label

        return hole_label(tuple(hole), self.rules, self._cmap)

    def twin_of(self, hole) -> str:
        """The hold'em class at the same combo percentile as this hand's class in the variant's table."""
        lb = self.label(hole)
        t = self.twin.get(lb)
        if t is None and "+" in lb:
            t = self.twin.get(lb.split("+")[0])
            if t is None:
                t = lb.split("+")[0]
        return t or _B.two_card_class(tuple(hole))

    def chen_of(self, hole) -> float:
        return _chen_class(self.twin_of(hole))

    def quantile(self, length: int, scores: tuple) -> Optional[float]:
        """The share of random hands at this board length whose score the given scores beat (split columns averaged);
        None when the table has none for it."""
        q = self.quant.get(min(length, max(self.quant) if self.quant else length))
        if not q:
            return None
        tot = 0.0
        for c, s in enumerate(scores):
            col = q[c] if c < len(q) else None
            if not col or s is None:
                continue
            lo, hi = bisect_left(col, s), bisect_right(col, s)
            tot += (lo + hi) / 2 / len(col)
        return tot / len(scores)


_TABLES: dict = {}
_SIMS: dict = {}


def load_table(name: str, rules: Rules, sim: Sim, build_if_missing: bool = True,
               vspec: Optional[str] = None) -> Table:
    key = table_key(name, rules, sim.hooks)
    t = _TABLES.get(key)
    if t is not None:
        return t
    path = table_path(key)
    if not os.path.exists(path):
        path = table_path(key, cache=True)
    if not os.path.exists(path):
        if not build_if_missing:
            raise FileNotFoundError(path)
        doc = build_table(name, rules, workers=1, budget_s=4.0, vspec=vspec or "")  # quick, cached for the next process
        _write(path, doc)
    else:
        with open(path) as fh:
            doc = json.load(fh)
    t = Table(doc, rules)
    _TABLES[key] = t
    return t


def _write(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    with open(tmp, "w") as fh:
        json.dump(doc, fh, separators=(",", ":"), sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def _worker_sim(vspec: Optional[str], rules_d: dict) -> Sim:
    from ..tablegen import rules_from_dict

    key = (vspec, json.dumps(rules_d, sort_keys=True))
    sim = _SIMS.get(key)
    if sim is None:
        rules = rules_from_dict(rules_d)
        v = None
        if vspec:
            from ..drills import variants as V

            v = V.get(vspec, seed=int((rules.extras or {}).get("seed", 0) or 0))
        sim = Sim(rules, v)
        _SIMS[key] = sim
    return sim


_DEAL_POT = 120  # the preflop table's pot: two players in for 3 big blinds at 10/20 (bounty constants are in chips)


def _deal_value(sim: Sim, hole: tuple, rng: random.Random, n: int = 1) -> Optional[float]:
    """n hands from the deal: `hole` against one random holding, through on_deal, every street and the payoff."""
    sim.sync({}, ())
    return sim.rollout(hole, (), 0, [1], n, rng, street=0, pot=_DEAL_POT, contrib=_DEAL_POT // 2, from_deal=True,
                       opp_k=sim.k, view={"stacks": [2000] * sim.n_seats, "pot": _DEAL_POT, "button": sim.n_seats - 1,
                                          "blinds": (10, 20), "contrib": [0] * sim.n_seats, "hand_no": 0})


def _job_classes(args):
    """Stratified: rounds over the job's classes, 8 hands from the deal per class per round, until the time budget is
    spent and every class has `n_min` (at most `n_max`)."""
    vspec, rules_d, classes, n_min, n_max, budget_s, seed = args
    sim = _worker_sim(vspec, rules_d)
    rng = random.Random(seed)
    out = {lb: [0.0, 0] for lb, _ in classes}
    t_end = time.perf_counter() + budget_s
    per = 8
    while True:
        for lb, combos in classes:
            v = _deal_value(sim, combos[rng.randrange(len(combos))], rng, per)
            if v is not None:
                out[lb][0] += v * per
                out[lb][1] += per
        least = min(g for _, g in out.values())
        if least >= n_max or (least >= n_min and time.perf_counter() >= t_end):
            break
    return {lb: tuple(v) for lb, v in out.items()}


def _job_sampled(args):
    """Natural frequency: random hands until the time budget is spent (at least n_min, at most n_max), summed by
    label."""
    vspec, rules_d, n_min, n_max, budget_s, seed = args
    sim = _worker_sim(vspec, rules_d)
    from ..tablegen import canon_map, hole_label

    cmap = canon_map(sim.rules)
    rng = random.Random(seed)
    out: dict = {}
    t_end = time.perf_counter() + budget_s
    done = 0
    while done < n_max and (done < n_min or time.perf_counter() < t_end):
        for _ in range(200):
            hole = tuple(rng.sample(sim.deck, sim.k))
            lb = hole_label(hole, sim.rules, cmap)
            v = _deal_value(sim, hole, rng)
            done += 1
            if v is None:
                continue
            a = out.setdefault(lb, [0.0, 0])
            a[0] += v
            a[1] += 1
    return out


def calibrate(sim: Sim, rng: random.Random, reps: int = 40, batches: int = 5) -> dict:
    """Measured costs (ns, CPU time of this thread, so a busy host moves them little; the mean of `batches` batches):
    one showdown score at the final board size, one runout from the flop against 1 and 3 opponents, one hand from the
    deal. These fix the bots' sample counts."""
    deck = list(sim.deck)
    flop = sim.sizes[1] if len(sim.sizes) > 1 else 3
    showk = int((sim.rules.extras or {}).get("keep", 0) or 0) or sim.k
    view = {"stacks": [2000] * sim.n_seats, "pot": 120, "button": sim.n_seats - 1, "blinds": (10, 20),
            "contrib": [0] * sim.n_seats, "hand_no": 0}
    clock = time.thread_time_ns
    runs: dict = {"score_ns": [], "roll1_ns": [], "roll3_ns": [], "deal_ns": []}
    for _b in range(batches):
        spots = []
        for _ in range(reps):
            cards = rng.sample(deck, sim.k + sim.final)
            spots.append((tuple(cards[:showk]), tuple(cards[sim.k:sim.k + sim.final]), tuple(cards[:sim.k]),
                          tuple(cards[sim.k:sim.k + flop])))
        sim.sync({}, ())
        t = clock()
        for hole, board, _h, _f in spots:
            try:
                sim.scores(hole, board)
            except Exception:  # noqa: BLE001
                pass
        runs["score_ns"].append((clock() - t) / reps)
        per = 20  # runouts per call, as a decision makes them (the per-call shuffle amortized)
        for n_opp in (1, 3):
            t = clock()
            for _s, _b2, hole, fl in spots[: reps // 4]:
                sim.rollout(hole[:showk] if showk < sim.k else hole, fl, 0, list(range(1, 1 + n_opp)), per, rng,
                            street=1, view=view, pot=120, contrib=60)
            runs[f"roll{n_opp}_ns"].append((clock() - t) / (per * (reps // 4)))
        t = clock()
        for _s, _b2, hole, _f in spots[:5]:
            _deal_value(sim, hole, rng, 8)
        runs["deal_ns"].append((clock() - t) / 40)
    return {k: int(sum(v) / len(v)) for k, v in runs.items()}  # the mean: a showdown with a heavy tail (wild cards)
    # costs what its average costs, which a median would hide


def _quantiles(sim: Sim, rng: random.Random, n: int) -> dict:
    """Score quantiles per board length (3, 4, 5 cards ... the final size) for random two-card hands (or the hole size
    at showdown): the fallback read. Split columns kept apart; None (does not qualify) left out."""
    out = {}
    showk = int((sim.rules.extras or {}).get("keep", 0) or 0) or sim.k
    lengths = sorted({sz for sz in sim.sizes if sz >= 3} | {sim.final})
    for L in lengths:
        cols: list = []
        for _ in range(n):
            cards = rng.sample(sim.deck, showk + L)
            try:
                sc = sim.scores(tuple(cards[:showk]), tuple(cards[showk:]))
            except Exception:  # noqa: BLE001
                continue
            while len(cols) < len(sc):
                cols.append([])
            for c, s in enumerate(sc):
                if s is not None:
                    cols[c].append(s)
        out[str(L)] = [sorted(c)[:: max(1, len(c) // 200)] for c in cols]
    return out


def build_table(name: Optional[str], rules: Rules, workers: int = 2, budget_s: float = 45.0, seed: int = 1,
                vspec: Optional[str] = None) -> dict:
    """The variant's table document (module doc): preflop value shares by class through the hooks, costs, quantiles."""
    from ..drills import variants as V
    from ..tablegen import rules_to_dict

    t0 = time.time()
    vspec = vspec if vspec is not None else name  # "" = no variant: the rules alone
    v = V.get(vspec, seed=int((rules.extras or {}).get("seed", 0) or 0)) if vspec else None
    sim = Sim(rules, v)
    key = table_key(name or "holdem", rules, sim.hooks)
    rng = random.Random(seed)
    cost = calibrate(sim, rng)
    rules_d = rules_to_dict(rules)
    labels: dict = {}
    how = ""
    if sim.holdem_cards():
        with open(_REFERENCE) as fh:
            eq = json.load(fh)
        labels = {c: [eq[c][0], _combos(c) / 1326.0, 20000] for c in eq}
        how = "hold'em cards and no card hooks: tables/preflop_equity.json (heads-up)"
    elif sim.k == 2:
        classes: dict = {}
        for a, b in combinations(sim.deck, 2):
            classes.setdefault(hole_class((a, b)), []).append((a, b))
        items = sorted(classes.items())
        nj = 4 * max(1, workers)
        jobs = [(vspec, rules_d, items[i::nj], 160, 4000, budget_s / 4, seed * 7919 + i) for i in range(nj)]
        res = _map(_job_classes, jobs, workers)
        for part in res:
            for lb, (acc, got) in part.items():
                labels[lb] = [acc / got if got else 0.0, len(classes[lb]) / math.comb(len(sim.deck), 2), got]
        per = sorted(v[2] for v in labels.values())
        how = (f"169-class stratified, {per[0]}-{per[-1]} hands per class from the deal through the hooks vs one "
               f"random hand")
    else:
        nj = 4 * max(1, workers)
        jobs = [(vspec, rules_d, 5000, 150000, budget_s / 4, seed * 104729 + j) for j in range(nj)]
        res = _map(_job_sampled, jobs, workers)
        sums: dict = {}
        for part in res:
            for lb, (acc, got) in part.items():
                a = sums.setdefault(lb, [0.0, 0])
                a[0] += acc
                a[1] += got
        n_all = sum(g for _, g in sums.values()) or 1
        mean = sum(a for a, _ in sums.values()) / n_all
        heads: dict = {}
        for lb, (acc, got) in sums.items():
            hb = heads.setdefault(lb.split("+")[0], [0.0, 0])
            hb[0] += acc
            hb[1] += got
        m = 20.0  # shrinkage: a label with few hands leans on its best-two class, that on the overall mean
        head_eq = {hb: (a + m * mean) / (g + m) for hb, (a, g) in heads.items()}
        for lb, (acc, got) in sums.items():
            labels[lb] = [(acc + m * head_eq[lb.split("+")[0]]) / (got + m), got / n_all, got]
        for hb, e in head_eq.items():  # best-two fallbacks for labels never sampled (share 0: no weight in the order)
            labels.setdefault(hb, [e, 0.0, 0])
        how = f"best2+tags labels, {n_all} random hands from the deal through the hooks vs one random hand, shrunk"
    quant = _quantiles(sim, rng, 600)
    return {"key": key, "variant": name, "vspec": vspec, "rules": rules_d,
            "hooks": type(sim.hooks).__name__, "k": sim.k, "labels": labels, "cost": cost, "quantiles": quant,
            "how": how, "secs": round(time.time() - t0, 1), "workers": workers}


def _map(fn, jobs, workers):
    if workers <= 1 or len(jobs) <= 1:
        return [fn(j) for j in jobs]
    from multiprocessing import get_context

    with get_context("fork").Pool(workers, maxtasksperchild=8) as p:
        return list(p.imap_unordered(fn, jobs))


def prepare(vspec: Optional[str], rules: Optional[Rules] = None, workers: int = 2, force: bool = False,
            budget_s: float = 45.0) -> tuple[str, dict]:
    """Make sure the variant's table exists (build it if missing, or with force); returns (path, doc)."""
    from ..drills import variants as V

    v = V.get(vspec) if vspec else None
    rules = rules or (v.rules if v is not None else Rules())
    name = (rules.extras or {}).get("variant") or (v.name if v is not None else None) or vspec
    sim = Sim(rules, v)
    path = table_path(table_key(name or "holdem", rules, sim.hooks))
    if os.path.exists(path) and not force:
        with open(path) as fh:
            return path, json.load(fh)
    doc = build_table(name, rules, workers=workers, budget_s=budget_s, vspec=vspec)
    _write(path, doc)
    _TABLES.pop(doc["key"], None)
    return path, doc


# ----- the bots ------------------------------------------------------------------------------------------------------


def _blen(board) -> int:
    return 3 if len(board) <= 3 else 4 if len(board) == 4 else 5


class _Generic:
    """What the three share: the variant, its table, the reads and the variant decisions."""

    def _gen_table(self, rules: Rules) -> None:
        v = variant_of(rules)
        name = str((rules.extras or {}).get("variant") or "holdem")
        try:
            self.gsim = Sim(rules, v)
            self.gtab = load_table(name, rules, self.gsim, vspec=name if v is not None else None)
        except Exception:  # noqa: BLE001 - never fail a table start: play the rules without the variant's hooks
            self.gsim = Sim(rules, None)
            self.gtab = load_table("holdem", rules, self.gsim)
        c = self.gtab.cost
        self._score_ns = max(1, int(c.get("score_ns", 2000)))
        r1, r3 = int(c.get("roll1_ns", 8000)), int(c.get("roll3_ns", 16000))
        self._roll = (max(1, r1 - (r3 - r1) // 2), max(0, (r3 - r1) // 2))  # base + per opponent
        self._hand0 = (-1, 0)
        self._last_obs: Optional[Observation] = None
        self.grng = random.Random(((getattr(self, "gseed", None) or 0) * 2_654_435_761 + 4099) & 0xFFFFFFFF)

    def _roll_ns(self, n_opp: int) -> int:
        return self._roll[0] + self._roll[1] * n_opp

    def _track(self, obs: Observation) -> None:
        if obs.hand_no != self._hand0[0]:
            self._hand0 = (obs.hand_no, obs.stacks[obs.seat] + obs.bets[obs.seat])
        self._last_obs = obs

    def _contrib(self, obs: Observation) -> int:
        return max(0, self._hand0[1] - obs.stacks[obs.seat])

    def _opps(self, obs: Observation) -> list:
        n = obs.n_players
        out = [(obs.seat + i) % n for i in range(1, n) if obs.in_hand[(obs.seat + i) % n]]
        return out[: Sim.MAX_OPP]

    def _ctx(self, obs: Observation):
        sim = self.gsim
        sim.sync(obs.extras, obs.board)
        dead, held = public_cards(obs.extras, obs.seat, obs.in_hand)
        return dead, held

    def _view(self, obs: Observation) -> dict:
        return {"stacks": list(obs.stacks), "pot": obs.total_pot, "button": obs.button, "blinds": obs.blinds,
                "contrib": [0] * obs.n_players, "hand_no": obs.hand_no}

    def _pre_obs(self, obs: Observation) -> tuple[Observation, int]:
        """Preflop as a team that read the Rules: a live straddle is the big blind (for facing a raise, sizes and stack
        depth), and one notch wider when the forced bets before anyone acts reach two of those big blinds (antes),
        when the steal is worth more. Plain hold'em: (obs, 0)."""
        r = self.rules
        bb = obs.big_blind
        alive = obs.players_left
        eff = r.straddle * bb if r.straddle and alive >= 3 else bb
        if eff > bb:
            obs = dataclasses.replace(obs, blinds=(obs.blinds[0], eff))
        dead = obs.blinds[0] + bb + r.ante_at(obs.hand_no) * alive + (eff if eff > bb else 0)
        return obs, (1 if dead >= 2 * eff else 0)

    def _payoff_hit(self, obs: Observation) -> bool:
        sim = self.gsim
        if sim.payout is None:
            return False
        sim.sync(obs.extras, obs.board)
        pot = max(obs.total_pot, 3 * obs.big_blind)
        r = sim.win_now_ratio(obs.hole, obs.board, obs.seat, self._opps(obs), pot, min(self._contrib(obs), pot // 2),
                              obs.hand_no, self.grng)
        return r >= PAYOFF_HIT

    def _strength(self, obs: Observation, dead, held) -> Optional[float]:
        """The made share now (reads), or the score's quantile when the showdown is too slow to sample."""
        n = min(MAX_HS, B_HS // self._score_ns)
        if n >= MIN_SAMPLES:
            return self.gsim.made_share(obs.hole, obs.board, n, self.grng, dead=dead | _flat(held))
        try:
            sc = self.gsim.scores(obs.hole, obs.board)
        except Exception:  # noqa: BLE001
            return None
        return self.gtab.quantile(len(obs.board), sc)

    def _value(self, obs: Observation, dead, held) -> Optional[float]:
        """gen_mc's value share after a call: runouts, else the made share (or quantile) to the power of opponents."""
        opps = self._opps(obs)
        n_opp = max(1, len(opps))
        pot = obs.total_pot + obs.to_call
        for who in ((opps, 1), (opps[:1], n_opp)) if n_opp > 1 else ((opps, 1),):
            n = min(MAX_MC, B_MC // max(1, self._roll_ns(len(who[0]) or 1)))
            if n >= MIN_SAMPLES:
                e = self.gsim.rollout(obs.hole, obs.board, obs.seat, who[0], n, self.grng, street=obs.street,
                                      dead=dead, held=held, pot=pot, contrib=self._contrib(obs) + obs.to_call,
                                      hand_no=obs.hand_no, view=self._view(obs))
                return None if e is None else (e if who[1] == 1 else min(1.0, e) ** who[1])
        hs = self._strength(obs, dead, held)
        return None if hs is None else hs ** n_opp

    # -- variant decisions, by type (any twist that asks one of these)
    def variant_decide(self, prompt: dict):
        fn = {"discard": self._dec_discard, "keep": self._dec_keep, "swap": self._dec_swap,
              "buy_card": self._dec_buy, "bid": self._dec_bid}.get(prompt.get("decision"))
        if fn is None or not hasattr(self, "gsim"):
            return None
        try:
            return fn(prompt)
        except Exception:  # noqa: BLE001 - the hook's default is always legal
            return None

    def _dec_setup(self, prompt: dict):
        hole, board = tuple(prompt.get("hole") or ()), tuple(prompt.get("board") or ())
        seat = int(prompt.get("seat", getattr(self, "seat", 0)))
        sim = self.gsim
        sim.sync(prompt, board)
        o = self._last_obs
        in_hand = o.in_hand if o is not None else None
        dead, held = public_cards(prompt, seat, in_hand)
        n = sim.n_seats
        if in_hand is not None:
            opps = [(seat + i) % n for i in range(1, n) if in_hand[(seat + i) % n]][: Sim.MAX_OPP] or [(seat + 1) % n]
        else:
            opps = [(seat + 1) % n]
        street = max(1, max(i for i, sz in enumerate(sim.sizes) if sz <= len(board)))
        pot = int(prompt.get("pot") or (o.total_pot if o is not None else 0) or 0)
        return hole, board, seat, dead, held, opps, street, pot

    def _options(self, hole, board, seat, dead, held, opps, street, pot, options, **kw):
        """Value share of each option (a dict: option -> (hole, extra dead, my_extra)), common random numbers."""
        sim = self.gsim
        n = max(4, min(24, B_DEC // max(1, len(options) * self._roll_ns(len(opps)))))
        seed = self.grng.getrandbits(32)
        rest = self._rest(hole, board, dead, held)
        out = {}
        for key, (h, extra_dead, my_extra) in options.items():
            v = sim.rollout(h, board, seat, opps, n, random.Random(seed), street=street, dead=dead | extra_dead,
                            held=held, pot=max(pot, 1), contrib=0, my_extra=my_extra, rest=rest, **kw)
            out[key] = -1.0 if v is None else v
        return out

    def _rest(self, hole, board, dead, held) -> Optional[list]:
        """One shuffled deck for the hooks' spare cards, shared by every option of a decision."""
        if not self.gsim.dynamic:
            return None
        known = set(hole) | set(board) | set(dead) | _flat(held)
        rest = [c for c in self.gsim.deck if c not in known]
        self.grng.shuffle(rest)
        return rest

    def _dec_discard(self, prompt: dict):
        hole, board, seat, dead, held, opps, street, pot = self._dec_setup(prompt)
        if len(hole) < 2:
            return None
        opts = {i: (hole[:i] + hole[i + 1:], {hole[i]}, 0) for i in range(len(hole))}
        val = self._options(hole, board, seat, dead, held, opps, street, pot, opts)
        return max(val, key=lambda i: (val[i], -i))

    def _dec_keep(self, prompt: dict):
        hole, board, seat, dead, held, opps, street, pot = self._dec_setup(prompt)
        keep = int(prompt.get("keep", 2) or 2)
        sim = self.gsim
        pairs = list(combinations(range(len(hole)), keep))
        if len(pairs) > 3 and len(board) + keep >= 5:  # screen by the made hand now, then price the best three
            def made(ix):
                try:
                    return sim.scores(tuple(hole[i] for i in ix), board)[0] or 0
                except Exception:  # noqa: BLE001
                    return 0
            pairs = sorted(pairs, key=lambda ix: (made(ix), sum(hole[i] >> 2 for i in ix)), reverse=True)[:3]
        opts = {ix: (tuple(hole[i] for i in ix), {hole[i] for i in range(len(hole)) if i not in ix}, 0) for ix in pairs}
        val = self._options(hole, board, seat, dead, held, opps, street, pot, opts)
        return list(max(val, key=lambda ix: val[ix]))

    def _dec_swap(self, prompt: dict):
        hole, board, seat, dead, held, opps, street, pot = self._dec_setup(prompt)
        opts = {-1: (hole, set(), 0)}
        for i in range(len(hole)):
            opts[i] = (hole[:i] + hole[i + 1:], {hole[i]}, 1)
        val = self._options(hole, board, seat, dead, held, opps, street, pot, opts, opp_k=len(hole))
        best = max(val, key=lambda i: (val[i], i == -1))
        return best if val[best] > val[-1] + 0.01 else -1

    def _dec_buy(self, prompt: dict):
        hole, board, seat, dead, held, opps, street, pot = self._dec_setup(prompt)
        price = int(prompt.get("price", 0) or 0)
        opts = {True: (hole, set(), 1), False: (hole, set(), 0)}
        val = self._options(hole, board, seat, dead, held, opps, street, pot, opts, opp_k=len(hole))
        return (val[True] - val[False]) * max(pot, 1) >= price

    def _dec_bid(self, prompt: dict):
        hole, board, seat, dead, held, opps, street, pot = self._dec_setup(prompt)
        cap = int(prompt.get("max_bid", prompt.get("stack", 0)) or 0)
        sim = self.gsim
        n = max(4, min(24, B_DEC // max(1, 2 * self._roll_ns(len(opps)))))
        seed = self.grng.getrandbits(32)
        common = dict(street=street, dead=dead, held=held, pot=max(pot, 1), contrib=0, opp_k=len(hole),
                      rest=self._rest(hole, board, dead, held))
        mine = sim.rollout(hole, board, seat, opps, n, random.Random(seed), my_extra=1, **common)
        theirs = sim.rollout(hole, board, seat, opps, n, random.Random(seed), opp_extra=1, **common)
        if mine is None or theirs is None:
            return None
        d = max(0.0, mine - theirs)
        return max(0, min(int(d * pot * 0.75), cap // 4))


def _flat(held: dict) -> set:
    out: set = set()
    for v in held.values():
        out.update(v)
    return out


class GenMC(_Generic, AwareMC):
    """gen_mc (module doc)."""

    _notch = 0

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.gseed = seed

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        AwareMC.new_table(self, rules, seat, n_players)
        self._gen_table(rules)

    def pre_score(self, obs: Observation) -> float:
        return self.gtab.chen_of(obs.hole) + (2.0 if self._payoff_hit(obs) else 0.0) + self._notch

    def act(self, obs: Observation) -> Action:
        self._track(obs)
        if obs.street == 0:
            obs, self._notch = self._pre_obs(obs)
            return AwareMC.act(self, obs)
        dead, held = self._ctx(obs)
        e = self._value(obs, dead, held)
        if e is None:
            return _check_or_fold(obs)
        bb, pot = obs.big_blind, obs.total_pot
        if obs.to_call == 0:
            if e >= self.bet_eq and RAISE in obs.legal:
                return _raise_or_call(obs, obs.bets[obs.seat] + max(bb, (2 * pot) // 3))
            return Action.check()
        odds = obs.to_call / (pot + obs.to_call)
        if e >= self.raise_eq and RAISE in obs.legal:
            return _raise_or_call(obs, obs.bets[obs.seat] + obs.to_call + pot)
        if e >= odds + self.margin + 0.15 * min(1.0, obs.to_call / max(1, pot - obs.to_call)):
            return Action.call()
        return Action.fold()


class GenTAG(_Generic, ChartTAG):
    """gen_tag (module doc)."""

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.gseed = seed

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        ChartTAG.new_table(self, rules, seat, n_players)
        self._gen_table(rules)

    def act(self, obs: Observation) -> Action:
        self._track(obs)
        if obs.street == 0:
            pre, notch = self._pre_obs(obs)
            return tag_preflop(self, pre, self.gtab.twin_of(obs.hole), notch + (1 if self._payoff_hit(obs) else 0))
        dead, held = self._ctx(obs)
        hs = self._strength(obs, dead, held)
        if hs is None:
            return _check_or_fold(obs)
        L = _blen(obs.board)
        strong, big = hs >= H_STRONG[L], hs >= H_BIG[L]
        if (not strong and obs.to_call == 0 and obs.active <= 3 and RAISE in obs.legal and self._payoff_hit(obs)):
            return _raise_or_call(obs, obs.bets[obs.seat] + max(obs.big_blind, obs.total_pot // 2))
        return tag_postflop(self, obs, strong, big)


class GenPushFold(_Generic, PushFoldBot):
    """gen_pushfold (module doc)."""

    def __init__(self, seed: Optional[int] = None):
        super().__init__(seed)
        self.gseed = seed

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        PushFoldBot.new_table(self, rules, seat, n_players)
        self._gen_table(rules)

    def act(self, obs: Observation) -> Action:
        self._track(obs)
        if obs.street == 0:
            pre, notch = self._pre_obs(obs)
            notch += 1 if self._payoff_hit(obs) else 0
            return pushfold_preflop(self, pre, self.gtab.twin_of(obs.hole), notch)
        dead, held = self._ctx(obs)
        hs = self._strength(obs, dead, held)
        if hs is None:
            return _check_or_fold(obs)
        L = _blen(obs.board)
        strong, big = hs >= H_STRONG[L], hs >= H_BIG[L]
        if (not strong and obs.to_call == 0 and obs.active <= 3 and RAISE in obs.legal
                and obs.stack_bb > self.pushfold_bb and self._payoff_hit(obs)):
            return _raise_or_call(obs, obs.bets[obs.seat] + max(obs.big_blind, obs.total_pot // 2))
        return pushfold_postflop(self, obs, strong, big)


GENERIC = {"gen_mc": GenMC, "gen_tag": GenTAG, "gen_pushfold": GenPushFold, "aware_mc": AwareMC}
# the generic aware field: the aware fields' shape (hyperion/sim/aware.py), the three generic bots in the seats of the
# honest Monte Carlo bot, the push/fold bot and the TAG; the realistic seats stay twist-blind. Plays under any variant.
GENERIC_FIELDS = {
    "generic_aware": ("hero", "montecarlo30", "gen_mc", "gen_pushfold", "loose_aggro", "rival1", "gen_tag",
                      "timeout_then_recover"),
    # validation (docs/drills/climb/vd-log.md): each generic bot at the table with the bot it should match, the
    # hand-built aware bot of the twist (play under that variant) or the plain archetype (hold'em; aware_mc is AwareMC
    # with no twist, the Monte Carlo archetype the aware fields use)
    "generic_vs_holdem": ("hero", "gen_mc", "aware_mc", "gen_tag", "tag", "gen_pushfold", "pushfold", "loose_aggro"),
    "generic_vs_toss": ("hero", "gen_mc", "toss_mc", "gen_tag", "toss_tag", "gen_pushfold", "toss_pushfold",
                        "loose_aggro"),
    "generic_vs_bounty": ("hero", "gen_mc", "bounty_mc", "gen_tag", "bounty_tag", "gen_pushfold", "bounty_pushfold",
                          "loose_aggro"),
    "generic_vs_short": ("hero", "gen_mc", "short_mc", "gen_tag", "short_tag", "gen_pushfold", "short_pushfold",
                         "loose_aggro"),
    "generic_vs_rob": ("hero", "gen_mc", "rob_mc", "gen_tag", "rob_tag", "gen_pushfold", "rob_pushfold", "loose_aggro"),
}

_B.REGISTRY.update(GENERIC)
_B._BY_CLASS.update({cls.__name__.lower(): cls for cls in GENERIC.values()})
_B.FIELDS.update(GENERIC_FIELDS)


# ----- CLI -----------------------------------------------------------------------------------------------------------


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="python -m hyperion.sim.generic", description=__doc__.split("\n\n")[0])
    p.add_argument("--prepare", required=True, help="a catalog variant, a registered file spec (path.py:factory), "
                                                    "'holdem', or 'all' (every catalog entry)")
    p.add_argument("--rules", default=None, help="a Rules JSON for the table (default: the variant's own Rules)")
    p.add_argument("--workers", type=int, default=2)
    p.add_argument("--budget", type=float, default=45.0, help="seconds of sampling per worker (about)")
    p.add_argument("--force", action="store_true", help="rebuild even when the table exists")
    a = p.parse_args(argv)
    from ..drills import variants as V
    from ..sim.runner import load_rules

    names = V.catalog_names() if a.prepare == "all" else [None if a.prepare == "holdem" else a.prepare]
    for nm in names:
        t = time.time()
        rules = load_rules(a.rules) if a.rules else None
        path, doc = prepare(nm, rules, workers=a.workers, force=a.force, budget_s=a.budget)
        c = doc["cost"]
        print(f"{nm or 'holdem':26s} {time.time() - t:6.1f}s  labels {len(doc['labels']):5d}  "
              f"score {c['score_ns'] / 1000:6.1f}us  runout 1/3 opp {c['roll1_ns'] / 1000:6.1f}/"
              f"{c['roll3_ns'] / 1000:6.1f}us  deal {c['deal_ns'] / 1000:6.1f}us  {os.path.relpath(path, _ROOT)}",
              flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
