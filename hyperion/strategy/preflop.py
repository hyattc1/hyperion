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
from .ranges import range_equity
from .spot import Spot
from .tables import Tables

_FOLD = Action(ActionKind.FOLD)
_CHECK = Action(ActionKind.CHECK)
_CALL = Action(ActionKind.CALL)


def _default_open_frac() -> dict:
    # fraction of hands to open-raise, keyed by players still to act after me (unopened pot)
    # swept 2026-10-31: the field folds too much to be left alone; 0.3/0.32/... cost -0.17 on a tag/nit table,
    # 0.5/0.52/... gained +0.16 there, this set a further +0.05 everywhere (tools/sweep.py, docs/decisions.md)
    return {0: 0.0, 1: 0.60, 2: 0.60, 3: 0.42, 4: 0.30, 5: 0.24, 6: 0.20, 7: 0.17}


@dataclass
class PreflopParams:
    open_frac: dict = field(default_factory=_default_open_frac)
    open_frac_default: float = 0.10  # more than 7 behind
    steal_positions: int = 2  # `behind` <= this and nobody in: steal_mult applies
    iso_frac: float = 0.14  # raise over limpers
    overlimp_frac: float = 0.35  # limp behind in position
    bb_raise_over_limps_frac: float = 0.12
    sb_complete_frac: float = 0.45
    three_bet_frac: float = 0.03  # swept: 0.05 -0.07 and 0.08 -0.04 on the mixed field vs 0.03
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
    shove_call_multiway: float = 0.08  # extra margin once a shove has already been called
    # option value of waiting: a deep stack can decline a flip and wait for a better one, and a frequent
    # shover will offer the same spot again. Both are extra equity margin on calling off a stack.
    patience_deep: float = 0.2  # full extra margin at patience_deep_bb (linear from patience_from_bb); swept 0.1/0.2/0.3
    patience_from_bb: float = 20.0
    patience_deep_bb: float = 60.0
    patience_risk_scaled: bool = True  # the deep premium scales with to_call / my stack: a 10% call keeps my options
    patience_shover: float = 0.0  # times the shover's shove rate above the prior (0 .. ~1)
    # calling a shove against the shover's *observed* range: a seat that rarely shoves holds the top of its range
    # (a 4-bet shove from a tight seat is QQ+/AK), one that shoves every hand holds anything. The range is the top
    # x of hands, x = shove_range_mult * its preflop shove rate per hand in its depth bucket (profiler.shove_counts,
    # Beta-smoothed toward shove_prior[bucket] with weight shove_prior_n hands), clamped to [shove_range_min, 1];
    # equity against it comes from ranges.RangeEquity. Off = the older rule (equity vs random minus margins).
    shove_range_model: bool = True
    shove_prior: tuple = (0.20, 0.08, 0.035, 0.025)  # per-hand shove rate by the shover's depth: <=12, <=25, <=50, >50 bb
    shove_prior_n: float = 10.0
    shove_range_mult: float = 1.5  # per-hand rate -> range width (a seat is first in, or facing a raise, only part of the time)
    shove_range_min: float = 0.02
    shove_eq_margin: float = 0.02  # equity margin against the estimated range
    # big-blind defence against a single open (no callers): call when my equity against the opener's estimated range,
    # times what I realise out of position, beats the pot odds; 3-bet the value slice plus a small polarised set.
    # The opener's range is bb_open_prior[players behind it] scaled by its PFR against the prior, clamped.
    bb_defend: bool = False
    bb_open_prior: tuple = (0.45, 0.45, 0.40, 0.28, 0.22, 0.18, 0.15, 0.13)  # by players behind the opener at open
    bb_realize: float = 0.85
    bb_defend_margin: float = 0.0
    bb_defend_max_frac: float = 0.15  # the call costs at most this share of my stack
    bb_3bet_bluffs: tuple = ("A5s", "A4s")  # polarised 3-bets (blockers, playable when called)
    bb_3bet_bluff_min_bb: float = 15.0
    # the folder read: a seat that folded to at least folder_ftr of the >= folder_min_n preflop raises it faced
    # (within its first ~20 hands that is a handful of samples); steals widen by folder_steal_mult when every
    # player still to act is a folder (1.0 = off)
    folder_ftr: float = 0.75
    folder_min_n: int = 4
    folder_steal_mult: float = 1.0
    reraise_margin: float = 0.15  # 4-bet / 5-bet shoves: equity vs random is discounted by this (a 3-bettor is not random)
    reraise_tight_pfr: float = 0.0  # ... plus this much more when the re-raiser's PFR is below the prior (0 = off)
    raise_or_fold_bb: float = 25.0  # below this depth, no speculative flats
    short_flat_frac: float = 0.12
    open_size_bb: tuple = ((50, 2.5), (150, 2.3), (10**9, 2.2))  # (bb at most, size in bb)
    limper_add_bb: float = 1.0
    three_bet_mult_ip: float = 3.0
    three_bet_mult_oop: float = 3.5
    four_bet_mult: float = 2.3
    shove_instead_frac: float = 0.4  # a raise this large relative to my stack becomes a shove
    cheap_open_frac: float = 0.12  # Hero.cheap(): one open fraction everywhere
    # one knob each for "a step wider / tighter" (drill 4: open_frac_default only applies beyond 7 behind, which an
    # 8-max table never reaches, so it is inert there; these two are the levers)
    open_frac_mult: float = 1.0  # multiplies every open fraction
    open_step: int = 0  # read the open fraction for this many more players behind (1 = one position tighter)
    # exposed-card variants (Spot.exposed = {seat: card}): a high card showing behind me shrinks steals, and a
    # shover's exposed card moves the calling margin
    exposed_high_rank: int = 10  # canonical rank index: 10 = Q
    exposed_steal_mult: float = 0.85  # per high card exposed behind me in an unopened pot
    exposed_shove_margin: float = 0.03  # +this vs a shover showing a high card, -this vs one showing 9 or lower


class _Linear:
    __slots__ = ()
    points = False

    def value(self, x: float) -> float:
        return x


class Preflop:
    def __init__(self, params: PreflopParams, tables: Tables):
        self.p = params
        self.rank = tables.rank
        self.equity = tables.equity
        self.curve = _Linear()  # Hero installs its ICM curve; chip EV otherwise
        self.last = ""  # the sub-decision that put chips in last (diagnostics: the runner's bust tracer reads it)
        try:
            self.req = range_equity(tables) if tables.hu else None
        except Exception:  # noqa: BLE001 - a table set without a usable matrix keeps the older shove-call rule
            self.req = None

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
        self.last = ""
        if cheap:
            self.last = "cheap"
            return self._cheap(spot, rank)
        if spot.n_raises == 0:
            return self._unopened(spot, rank, prof)
        if spot.facing_shove:
            self.last = "call_shove"
            return self._facing_shove(spot, cls, rank, prof)
        if spot.n_raises == 1:
            return self._facing_open(spot, cls, rank, prof)
        if spot.n_raises == 2:
            frac = p.four_bet_frac
            if rank >= 1.0 - frac:
                amount = spot.cur_bet * p.four_bet_mult
                if amount >= p.shove_instead_frac * spot.my_total and not self._reraise_ok(spot, cls, prof):
                    self.last = "call_3bet_flat"
                    return _CALL if spot.to_call <= p.call_max_stack_frac * spot.my_total else _FOLD
                self.last = "4bet"
                return self._raise_to(spot, amount)
            if spot.raiser != spot.me and self._opened(spot):
                if rank >= 1.0 - p.call_3bet_frac and spot.to_call <= p.call_max_stack_frac * spot.my_total \
                        and spot.my_bb >= p.raise_or_fold_bb and spot.behind == 0:
                    self.last = "call_3bet"
                    return _CALL
            return _FOLD
        if rank >= 1.0 - p.five_bet_frac and self._reraise_ok(spot, cls, prof):
            self.last = "5bet"
            return Action(ActionKind.RAISE, obs.max_raise)
        return _FOLD

    def _reraise_ok(self, spot: Spot, cls: str, prof: Profiler | None) -> bool:
        """Shoving over a 3-bet or 4-bet: ICM-weighted EV against the re-raiser's (premium) range, taken as
        equity vs random minus reraise_margin, minus more when the profiler shows a tight raiser."""
        p = self.p
        margin = p.reraise_margin
        if p.reraise_tight_pfr > 0.0 and prof is not None and spot.raiser >= 0:
            pfr = prof.pfr_rate(spot.raiser)
            if pfr < Profiler.P_PFR:
                margin += p.reraise_tight_pfr * (Profiler.P_PFR - pfr) / Profiler.P_PFR
        if margin <= 0.0:
            return True
        return self._icm_call_ok(spot, cls, margin, 0)

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
            frac = p.open_frac.get(spot.behind + p.open_step, p.open_frac_default) * p.open_frac_mult
            if spot.behind <= p.steal_positions and prof is not None:
                frac *= self._steal_mult(spot, prof)
            if spot.exposed:
                frac *= self._exposed_steal_mult(spot)
            if rank >= 1.0 - frac:
                self.last = "open"
                return self._raise_to(spot, self.open_size(spot))
            if me == spot.sb_seat and rank >= 1.0 - p.sb_complete_frac and spot.to_call <= spot.bb and spot.my_bb >= p.raise_or_fold_bb:
                self.last = "complete"
                return _CALL
            return _CHECK if can_check else _FOLD
        # limpers ahead
        iso = p.iso_frac
        if prof is not None:
            iso *= self._steal_mult(spot, prof)
        if me == spot.bb_seat:
            if rank >= 1.0 - p.bb_raise_over_limps_frac:
                self.last = "raise_limps"
                return self._raise_to(spot, self.open_size(spot))
            return _CHECK if can_check else _CALL
        if rank >= 1.0 - iso:
            self.last = "iso"
            return self._raise_to(spot, self.open_size(spot))
        if spot.behind <= p.steal_positions and rank >= 1.0 - p.overlimp_frac and spot.to_call <= spot.bb \
                and spot.my_bb >= p.raise_or_fold_bb:
            self.last = "overlimp"
            return _CALL
        return _CHECK if can_check else _FOLD

    def _exposed_steal_mult(self, spot: Spot) -> float:
        """Every opponent still in an unopened pot acts after me; each one showing a high card shrinks the steal."""
        p = self.p
        m = 1.0
        for s in spot.opps:
            c = spot.exposed.get(s)
            if c is not None and (c >> 2) >= p.exposed_high_rank:
                m *= p.exposed_steal_mult
        return m

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
        if self.p.folder_steal_mult != 1.0:
            p = self.p
            folders = True
            for s in spot.opps:
                if obs.bets[s] <= spot.bb and not (prof.pre_faced[s] >= p.folder_min_n and
                                                   prof.fold_to_bet_pre(s) >= p.folder_ftr):
                    folders = False
                    break
            if folders:
                m *= p.folder_steal_mult
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
            self.last = "3bet"
            return self._raise_to(spot, spot.cur_bet * mult)
        if p.bb_defend and spot.me == spot.bb_seat and spot.n_in == 1 and spot.raiser >= 0 and self.req is not None \
                and spot.to_call <= p.bb_defend_max_frac * spot.my_total:
            act = self._bb_defend(spot, cls, prof)
            if act is not None:
                return act
        to_call, my_total = spot.to_call, spot.my_total
        if to_call > p.call_max_stack_frac * my_total:
            # a big raise: it is shove-or-fold territory, and only premiums continue
            margin = p.shove_call_margin + self._patience(spot, prof, spot.raiser)
            if rank >= 1.0 - p.short_flat_frac and self._icm_call_ok(spot, cls, margin, 0):
                self.last = "big_raise_call"
                return Action(ActionKind.RAISE, spot.obs.max_raise) if to_call >= 0.4 * my_total else _CALL
            return _FOLD
        pair = cls[0] == cls[1]
        if pair and spot.eff >= p.setmine_ratio * to_call:
            self.last = "setmine"
            return _CALL
        if spot.my_bb < p.raise_or_fold_bb:
            self.last = "short_flat"
            return _CALL if rank >= 1.0 - p.short_flat_frac else _FOLD
        if rank < 1.0 - p.call_raise_frac:
            return _FOLD
        margin = p.call_margin_ip if spot.behind == 0 else p.call_margin_oop
        self.last = "call_open"
        return _CALL if self._equity_ok(spot, cls, margin, 1 if spot.behind >= p.crowd_behind else 0) else _FOLD

    def shover_range(self, spot: Spot, prof: Profiler | None, base: float | None = None) -> float:
        """Estimated width (top x of hands) of the shover's range. `base` (push/fold: the Nash push frequency for
        the shover's seat and depth) is scaled by how much more or less often than the prior this seat shoves;
        without it the smoothed rate itself, times shove_range_mult, is the width."""
        p = self.p
        obs = spot.obs
        sh = spot.shover
        chips = obs.stacks[sh] + obs.bets[sh] if sh >= 0 else spot.max_opp_total
        d = chips / spot.bb
        pri = p.shove_prior
        b = 0 if d <= 12 else 1 if d <= 25 else 2 if d <= 50 else 3
        prior = pri[b] if b < len(pri) else pri[-1]
        k = n = 0
        if prof is not None and sh >= 0:
            k, n = prof.shove_counts(sh, chips)
        rate = (k + prior * p.shove_prior_n) / (n + p.shove_prior_n)
        x = base * rate / prior if base is not None else p.shove_range_mult * rate
        return p.shove_range_min if x < p.shove_range_min else 1.0 if x > 1.0 else x

    def range_call_ok(self, spot: Spot, cls: str, x: float, margin: float, n_callers: int = 0):
        """ICM-weighted EV of calling a shove against the top x of hands beats folding (None: class not covered).
        With n_callers already in, each is taken as the top x/2, and my share of the pot is the normalised product
        of my pairwise equities (p_me ~ e1 e2 / (e1 e2 + (1 - e1)/2 + (1 - e2)/2), exact for equal equities)."""
        req = self.req
        if req is None:
            return None
        e = req.eq(cls, x)
        if e is None:
            return None
        for _ in range(min(n_callers, 2)):
            e2 = req.eq(cls, 0.5 * x)
            e = e * e2 / (e * e2 + 0.5 * (1.0 - e) + 0.5 * (1.0 - e2))
        e -= margin
        if spot.ror and spot.to_call >= 0.5 * spot.my_total:
            e -= spot.ror
        if e <= 0.0:
            return False
        obs = spot.obs
        v = self.curve.value
        behind = obs.stacks[spot.me]
        v_win = v(behind + spot.pot_total + spot.bounty_bonus)
        if spot.ko_points and spot.shover_covered and self.curve.points:
            v_win += spot.ko_points
        return e * v_win + (1.0 - e) * v(behind - spot.to_call) > v(behind)

    def _bb_defend(self, spot: Spot, cls: str, prof: Profiler | None):
        """Pot-odds-correct defence of the big blind against one open; None = class not covered (older rule)."""
        from .pushfold import PushFold

        p = self.p
        k = PushFold.behind_seat(spot, spot.raiser)
        pri = p.bb_open_prior
        x = pri[k] if k < len(pri) else pri[-1]
        if prof is not None:
            m = prof.pfr_rate(spot.raiser) / Profiler.P_PFR
            x *= 0.5 if m < 0.5 else 2.5 if m > 2.5 else m
        x = 0.03 if x < 0.03 else 1.0 if x > 1.0 else x
        e = self.req.eq(cls, x)
        if e is None:
            return None
        if cls in p.bb_3bet_bluffs and spot.my_bb >= p.bb_3bet_bluff_min_bb:
            self.last = "bb_3bet_bluff"
            return self._raise_to(spot, spot.cur_bet * p.three_bet_mult_oop)
        if e * p.bb_realize >= spot.pot_odds + p.bb_defend_margin:
            self.last = "bb_defend"
            return _CALL
        return _FOLD

    def _facing_shove(self, spot: Spot, cls: str, rank: float, prof: Profiler | None) -> Action:
        p = self.p
        if p.shove_range_model and self.req is not None:
            margin = p.shove_eq_margin + self._patience(spot, prof, spot.shover) + self._exposed_margin(spot)
            ok = self.range_call_ok(spot, cls, self.shover_range(spot, prof), margin, max(0, spot.n_in - 1))
            if ok is not None:
                return _CALL if ok else _FOLD
        margin = p.shove_call_margin + p.shove_call_risk * (spot.to_call / spot.my_total)
        if spot.n_in >= 2:
            margin += p.shove_call_multiway
        margin += self._patience(spot, prof, spot.shover)
        if spot.exposed:
            c = spot.exposed.get(spot.shover)
            if c is not None:
                r = c >> 2
                if r >= p.exposed_high_rank:
                    margin += p.exposed_shove_margin
                elif r <= 7:
                    margin -= p.exposed_shove_margin
        return _CALL if self._icm_call_ok(spot, cls, margin, 0) else _FOLD

    def _exposed_margin(self, spot: Spot) -> float:
        p = self.p
        if spot.exposed:
            c = spot.exposed.get(spot.shover)
            if c is not None:
                r = c >> 2
                if r >= p.exposed_high_rank:
                    return p.exposed_shove_margin
                if r <= 7:
                    return -p.exposed_shove_margin
        return 0.0

    def _patience(self, spot: Spot, prof: Profiler | None, shover: int) -> float:
        """Extra equity margin for the option of waiting: deep stacks, and shovers who do it every hand."""
        p = self.p
        m = 0.0
        if p.patience_deep > 0.0:
            t = (spot.my_bb - p.patience_from_bb) / (p.patience_deep_bb - p.patience_from_bb)
            t = 0.0 if t < 0.0 else 1.0 if t > 1.0 else t
            if p.patience_risk_scaled and spot.my_total > 0:
                share = spot.to_call / spot.my_total
                t *= 1.0 if share > 1.0 else share
            m += p.patience_deep * t
        if p.patience_shover > 0.0 and prof is not None and shover >= 0:
            r = prof.shove_rate(shover) - Profiler.P_SHOVE
            if r > 0.0:
                m += p.patience_shover * r
        return m

    def _icm_call_ok(self, spot: Spot, cls: str, margin: float, extra: int) -> bool:
        """Calling for a large share of the stack: ICM-weighted EV must beat folding, with the equity
        discounted by `margin` for the shover's range not being random."""
        n_opp = spot.n_in + extra
        n_opp = 1 if n_opp < 1 else 7 if n_opp > 7 else n_opp
        e = self.equity[cls][n_opp - 1] - margin
        if spot.ror and spot.to_call >= 0.5 * spot.my_total:
            e -= spot.ror
        if e <= 0.0:
            return False
        obs = spot.obs
        v = self.curve.value
        behind = obs.stacks[spot.me]
        v_win = v(behind + spot.pot_total + spot.bounty_bonus)
        if spot.ko_points and spot.facing_shove and spot.shover_covered and self.curve.points:
            v_win += spot.ko_points  # the shover busts when we win: the house pays the knockout
        return e * v_win + (1.0 - e) * v(behind - spot.to_call) > v(behind)

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
