"""Preflop decisions for stacks above push/fold depth, driven by the 169-class tables.

Position is "players still to act after me" (`behind`), which generalises across table sizes as
seats bust: UTG eight-handed has 7 behind, the button 2 (the blinds), the small blind 1, the big
blind 0. Every range is "open the top X of hands by heads-up equity rank" where X is a number in
PreflopParams, so the whole street retunes by editing a dict.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from ..core.types import Action, ActionKind
from .profiler import Profiler
from .spot import Spot
from .tables import Tables

_FOLD = Action(ActionKind.FOLD)
_CHECK = Action(ActionKind.CHECK)
_CALL = Action(ActionKind.CALL)


def _default_open_frac() -> dict:
    # fraction of hands to open-raise, keyed by players still to act after me (unopened pot)
    return {0: 0.0, 1: 0.40, 2: 0.42, 3: 0.28, 4: 0.20, 5: 0.16, 6: 0.13, 7: 0.11}


@dataclass
class PreflopParams:
    open_frac: dict = field(default_factory=_default_open_frac)
    open_frac_default: float = 0.10  # more than 7 behind
    steal_positions: int = 2  # `behind` <= this and nobody in: steal_mult applies
    iso_frac: float = 0.14  # raise over limpers
    overlimp_frac: float = 0.35  # limp behind in position
    bb_raise_over_limps_frac: float = 0.12
    sb_complete_frac: float = 0.45
    three_bet_frac: float = 0.05
    four_bet_frac: float = 0.03
    five_bet_frac: float = 0.02
    call_raise_frac: float = 0.45  # never flat a raise outside this rank slice
    call_3bet_frac: float = 0.07
    call_margin_ip: float = 0.06  # equity must beat pot odds by this
    call_margin_oop: float = 0.10
    call_max_stack_frac: float = 0.15  # flat calls cost at most this share of my stack
    crowd_behind: int = 3  # this many still to act counts as one extra opponent when flatting
    setmine_ratio: float = 15.0  # pairs call when effective stack >= ratio x the call
    shove_call_margin: float = 0.10  # a shover's range beats random: equity vs random is discounted by this
    shove_call_risk: float = 0.05  # extra margin per unit of (to_call / my stack)
    raise_or_fold_bb: float = 25.0  # below this depth, no speculative flats
    short_flat_frac: float = 0.12
    open_size_bb: tuple = ((50, 2.5), (150, 2.3), (10**9, 2.2))  # (bb at most, size in bb)
    limper_add_bb: float = 1.0
    three_bet_mult_ip: float = 3.0
    three_bet_mult_oop: float = 3.5
    four_bet_mult: float = 2.3
    shove_instead_frac: float = 0.4  # a raise this large relative to my stack becomes a shove
    cheap_open_frac: float = 0.12  # Hero.cheap(): one open fraction everywhere


class _Linear:
    __slots__ = ()

    def value(self, x: float) -> float:
        return x


class Preflop:
    def __init__(self, params: PreflopParams, tables: Tables):
        self.p = params
        self.rank = tables.rank
        self.equity = tables.equity
        self.curve = _Linear()  # Hero installs its ICM curve; chip EV otherwise

    # ------------------------------------------------------------------ sizing
    def open_size(self, spot: Spot) -> int:
        bb = spot.bb
        for cap, size in self.p.open_size_bb:
            if bb <= cap:
                return int(bb * (size + self.p.limper_add_bb * spot.limpers))
        return int(bb * 2.2)

    def _raise_to(self, spot: Spot, amount: int) -> Action:
        obs = spot.obs
        if amount >= self.p.shove_instead_frac * spot.my_total:
            amount = obs.max_raise
        amount = max(obs.min_raise, min(obs.max_raise, int(amount)))
        return Action(ActionKind.RAISE, amount)

    # ------------------------------------------------------------------ decisions
    def act(self, spot: Spot, prof: Profiler | None, cheap: bool = False) -> Action:
        cls = spot.cls
        obs = spot.obs
        if cls is None:
            return _CHECK if ActionKind.CHECK in obs.legal else _FOLD
        rank = self.rank[cls]
        p = self.p
        if cheap:
            return self._cheap(spot, rank)
        if spot.n_raises == 0:
            return self._unopened(spot, rank, prof)
        if spot.facing_shove:
            return self._facing_shove(spot, cls, rank)
        if spot.n_raises == 1:
            return self._facing_open(spot, cls, rank, prof)
        if spot.n_raises == 2:
            frac = p.four_bet_frac
            if rank >= 1.0 - frac:
                return self._raise_to(spot, spot.cur_bet * p.four_bet_mult)
            if spot.raiser != spot.me and self._opened(spot):
                if rank >= 1.0 - p.call_3bet_frac and spot.to_call <= p.call_max_stack_frac * spot.my_total \
                        and spot.my_bb >= p.raise_or_fold_bb and spot.behind == 0:
                    return _CALL
            return _FOLD
        if rank >= 1.0 - p.five_bet_frac:
            return Action(ActionKind.RAISE, obs.max_raise)
        return _FOLD

    def _opened(self, spot: Spot) -> bool:
        """Did I make the first raise this hand?"""
        me = spot.me
        for seat, act in spot.obs.history:
            if act.kind is ActionKind.RAISE:
                return seat == me
        return False

    def _unopened(self, spot: Spot, rank: float, prof: Profiler | None) -> Action:
        p = self.p
        obs = spot.obs
        me = spot.me
        legal = obs.legal
        can_check = ActionKind.CHECK in legal
        if spot.limpers == 0:
            if me == spot.bb_seat and can_check:
                return _CHECK  # everyone folded to the big blind: free flop (or walk)
            frac = p.open_frac.get(spot.behind, p.open_frac_default)
            if spot.behind <= p.steal_positions and prof is not None:
                frac *= self._steal_mult(spot, prof)
            if rank >= 1.0 - frac:
                return self._raise_to(spot, self.open_size(spot))
            if me == spot.sb_seat and rank >= 1.0 - p.sb_complete_frac and spot.to_call <= spot.bb and spot.my_bb >= p.raise_or_fold_bb:
                return _CALL
            return _CHECK if can_check else _FOLD
        # limpers ahead
        iso = p.iso_frac
        if prof is not None:
            iso *= self._steal_mult(spot, prof)
        if me == spot.bb_seat:
            if rank >= 1.0 - p.bb_raise_over_limps_frac:
                return self._raise_to(spot, self.open_size(spot))
            return _CHECK if can_check else _CALL
        if rank >= 1.0 - iso:
            return self._raise_to(spot, self.open_size(spot))
        if spot.behind <= p.steal_positions and rank >= 1.0 - p.overlimp_frac and spot.to_call <= spot.bb \
                and spot.my_bb >= p.raise_or_fold_bb:
            return _CALL
        return _CHECK if can_check else _FOLD

    def _steal_mult(self, spot: Spot, prof: Profiler) -> float:
        """Average steal dial of the opponents still to act, clamped so a dial cannot make us open any two."""
        obs = spot.obs
        total = 0.0
        k = 0
        for s in spot.opps:
            if obs.bets[s] <= spot.bb:
                total += prof.exploit_dials(s)["steal_mult"]
                k += 1
        if k == 0:
            return 1.0
        m = total / k
        return 0.6 if m < 0.6 else 2.0 if m > 2.0 else m

    def _facing_open(self, spot: Spot, cls: str, rank: float, prof: Profiler | None) -> Action:
        p = self.p
        three = p.three_bet_frac
        if prof is not None and spot.raiser >= 0:
            # a wide raiser gets 3-bet for value more often
            pfr = prof.pfr_rate(spot.raiser)
            three *= max(0.6, min(2.0, 1.0 + (pfr - 0.15) * 3.0))
        if rank >= 1.0 - three:
            mult = p.three_bet_mult_ip if spot.behind == 0 else p.three_bet_mult_oop
            return self._raise_to(spot, spot.cur_bet * mult)
        to_call, my_total = spot.to_call, spot.my_total
        if to_call > p.call_max_stack_frac * my_total:
            # a big raise: it is shove-or-fold territory, and only premiums continue
            if rank >= 1.0 - p.short_flat_frac and self._icm_call_ok(spot, cls, p.shove_call_margin, 0):
                return Action(ActionKind.RAISE, spot.obs.max_raise) if to_call >= 0.4 * my_total else _CALL
            return _FOLD
        pair = cls[0] == cls[1]
        if pair and spot.eff >= p.setmine_ratio * to_call:
            return _CALL
        if spot.my_bb < p.raise_or_fold_bb:
            return _CALL if rank >= 1.0 - p.short_flat_frac else _FOLD
        if rank < 1.0 - p.call_raise_frac:
            return _FOLD
        margin = p.call_margin_ip if spot.behind == 0 else p.call_margin_oop
        return _CALL if self._equity_ok(spot, cls, margin, 1 if spot.behind >= p.crowd_behind else 0) else _FOLD

    def _facing_shove(self, spot: Spot, cls: str, rank: float) -> Action:
        p = self.p
        margin = p.shove_call_margin + p.shove_call_risk * (spot.to_call / spot.my_total)
        if spot.n_in >= 2:
            margin += 0.08
        return _CALL if self._icm_call_ok(spot, cls, margin, 0) else _FOLD

    def _icm_call_ok(self, spot: Spot, cls: str, margin: float, extra: int) -> bool:
        """Calling for a large share of the stack: ICM-weighted EV must beat folding, with the equity
        discounted by `margin` for the shover's range not being random."""
        n_opp = spot.n_in + extra
        n_opp = 1 if n_opp < 1 else 7 if n_opp > 7 else n_opp
        e = self.equity[cls][n_opp - 1] - margin
        if e <= 0.0:
            return False
        obs = spot.obs
        v = self.curve.value
        behind = obs.stacks[spot.me]
        return e * v(behind + spot.pot_total) + (1.0 - e) * v(behind - spot.to_call) > v(behind)

    def _equity_ok(self, spot: Spot, cls: str, margin: float, extra: int) -> bool:
        """Equity vs (players already in + extra) random hands beats the pot odds by margin."""
        n_opp = spot.n_in + extra
        n_opp = 1 if n_opp < 1 else 7 if n_opp > 7 else n_opp
        eq = self.equity[cls][n_opp - 1]
        return eq >= spot.pot_odds + margin

    def _cheap(self, spot: Spot, rank: float) -> Action:
        """Hero.cheap(): raise the top slice, call shoves with the top slice, otherwise check or fold."""
        p = self.p
        obs = spot.obs
        if rank >= 1.0 - p.cheap_open_frac:
            if spot.n_raises >= 2 or spot.facing_shove:
                return _CALL if spot.facing_shove else Action(ActionKind.RAISE, obs.max_raise)
            return self._raise_to(spot, max(self.open_size(spot), spot.cur_bet * 3))
        return _CHECK if ActionKind.CHECK in obs.legal else _FOLD
