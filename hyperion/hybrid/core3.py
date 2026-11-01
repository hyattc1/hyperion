"""Rival 3's decision core, driven from outside: payouts from Rules, the hand's history at hand_end, a soft deadline.

Nothing in hyperion/sim/rivals/rival3.py is edited. `Rival3Core` subclasses its `Bot` and changes, from here:
  - payouts: rival 3 prices every all-in with `_icm1`, a closed form exact only for the brief's 10/7/5/4/3/2/1/0, and
    its bust value with the same table. Its one ICM method, `_allin` (20 lines), is re-implemented here line for
    line with `icm_points` and `Rules.payouts` in their place. `icm_points` keeps rival 3's O(n) closed form whenever
    the payouts are linear from the third place down (8..1 and the brief's table both are) and uses Hero's exact
    `icm_me` otherwise (top_heavy: ~50 us a call at eight seats, four calls per all-in). Its module globals are
    untouched, so a `rival3` opponent in the same process still plays as built.
  - history at hand_end, in the kit's (seat, (kind, amount)) shape, as its own engine passed it (worth +0.22 to it on
    `holdout`: docs/decisions.md, "Rival 3 in the pool").
  - a soft deadline: if the decision has already used `soft_us` when its preflop or postflop logic would start (the
    history replay ran long or the process was preempted), `SoftDeadline` is raised and Hero's cheap path answers.
  - replay errors, which rival 3 swallows, are counted (`replay_errors`) before its own handler sees them.
  - dials (`HybridConfig.r3`, hyperion/hybrid/dials.py): its preflop and postflop decisions and its seat reads
    (`_pre`, `_post`, `_rates`) are copied here from rival3.py with a dozen literals named as knobs. At the defaults
    every decision is bit-identical to rival 3's own methods (tests/test_ship.py replays whole tables against them).
Everything else (equity tables, push/fold by ICM, the opponent model and dead-seat detection, postflop rules) is rival 3
as frozen. It has no wall-clock time box and seeds its one RNG at construction, so it is bit-reproducible.
"""
from __future__ import annotations

from time import perf_counter

from ..core.types import HandResult, Rules
from ..sim.rivals import rival3 as R3
from ..sim.rivals.rival3 import CLASSES, PCT, _cls, _eqvs
from ..strategy.hero import icm_me
from .dials import Rival3Knobs
from .kit import SoftDeadline


def _linear_from(pays) -> tuple[float, float, int] | None:
    """(A, B, m): pays[p] == A - B * p for every place index p >= m (0 = first), with the smallest such m; None when
    fewer than two places are paid."""
    k = len(pays)
    if k < 2:
        return None
    B = pays[k - 2] - pays[k - 1]
    A = pays[k - 1] + B * (k - 1)
    m = k - 1
    while m > 0 and abs(pays[m - 1] - (A - B * (m - 1))) < 1e-9:
        m -= 1
    return A, B, m


def icm_points(st, i: int, payouts) -> float:
    """My Malmuth-Harville points for stacks `st` (busted seats hold 0). Payouts linear from the third place down:
    E = A - B * E[players ahead] + (pay_1 - A) P(1st) + (pay_2 - (A - B)) P(2nd), all O(n) (rival 3's `_icm1` is the
    brief's case: A 7, B 1, corrections 3 and 1). Otherwise Hero's exact forward pass, `icm_me`."""
    si = st[i]
    if si <= 0:
        return 0.0
    alive = 0
    T = 0.0
    for x in st:
        if x > 0:
            alive += 1
            T += x
    pays = [float(p) for p in payouts[:alive]] + [0.0] * max(0, alive - len(payouts))
    if alive == 1:
        return pays[0]
    lin = _linear_from(pays)
    if lin is None or lin[2] > 2:
        return icm_me(st, i, pays)
    A, B, m = lin
    ahead = 0.0
    p2 = 0.0
    for j, sj in enumerate(st):
        if j == i or sj <= 0:
            continue
        ahead += sj / (si + sj)
        p2 += (sj / T) * si / (T - sj)
    out = A - B * ahead
    if m >= 1:
        out += (pays[0] - A) * (si / T)
    if m >= 2:
        out += (pays[1] - (A - B)) * p2
    return out


class Rival3Core(R3.Bot):
    """Rival 3's `Bot` with payouts, hand_end history and a soft deadline set from outside (module doc). `decide` returns
    its raw ('kind', amount) answer, or None where it declines (as built it would then fold; the caller asks Hero)."""

    payouts = (8, 7, 6, 5, 4, 3, 2, 1)
    soft_us = 350.0
    _t0 = 0.0
    replay_errors = 0
    k = Rival3Knobs()  # the dials (hyperion/hybrid/dials.py); setup() takes HybridConfig.r3

    # ------------------------------------------------------------------ the adapter HybridCore drives
    def setup(self, rules: Rules, seat: int, n_players: int, cfg) -> None:
        self.new_table({"starting_stack": rules.starting_stack, "hand_cap": rules.max_hands,
                        "n_players": n_players, "blinds": rules.blind_levels}, seat, n_players)
        self.payouts = tuple(rules.payouts)
        self.soft_us = float(cfg.soft_us)
        self.k = getattr(cfg, "r3", None) or Rival3Knobs()
        self.replay_errors = 0

    def start_hand(self, kit_hand_no: int, totals) -> None:
        """Nothing to precompute: rival 3 prices each all-in from the stacks it sees."""

    def decide(self, kit, t0: float):
        self._t0 = t0
        return self._act(kit)

    def legalize(self, ans, kit):
        return self._legalize(ans, kit)

    @staticmethod
    def best_two(hole: tuple) -> tuple:
        """The two hole cards (canonical) rival 3's own preflop ranking values most (lowest `PCT` percentile)."""
        if len(hole) <= 2:
            return hole
        best, best_p = hole[:2], 2.0
        n = len(hole)
        for i in range(n):
            for j in range(i + 1, n):
                p = R3.PCT[R3._cls((hole[i], hole[j]))]
                if p < best_p:
                    best_p, best = p, (hole[i], hole[j])
        return best

    def end(self, result: HandResult) -> None:
        self.hand_end({"hand_no": result.hand_no + 1, "deltas": result.deltas,
                       "history": [(s, (a.kind.value, a.amount)) for s, a in result.history]})

    # ------------------------------------------------------------------ overrides
    def _soft(self) -> None:
        if perf_counter() - self._t0 > self.soft_us * 1e-6:
            raise SoftDeadline()

    def _pre(self, *args):
        self._soft()
        return self._pre_body(*args)

    def _post(self, *args):
        self._soft()
        return self._post_body(*args)

    # ------------------------------------------------------------------ rival 3's decisions, with the dials
    # Copied from hyperion/sim/rivals/rival3.py (Bot._rates, _pre, _post); the only changes are the `kn.` / `w0` /
    # `self.k.` terms, each replacing the literal that is its default, and one dropped unused call.
    def _rates(self, s):
        S = self.st[s]; h = S.hands
        w0 = self.k.prior_scale
        vp = (S.vpip + 1.0 * w0) / (h + 4.0 * w0)
        pfr = (S.pfr + 0.6 * w0) / (h + 4.0 * w0)
        f2r = (S.fr_f + 2.4 * w0) / (S.fr + 4.0 * w0)
        r3 = (S.fr_r + 0.3 * w0) / (S.fr + 4.0 * w0)
        shv = (S.shv + 0.2 * w0) / (S.rz + 2.0 * w0)
        fb = (S.fb_f + 1.8 * w0) / (S.fb + 4.0 * w0)
        agg = (S.nb_b + 1.2 * w0) / (S.nb + 4.0 * w0)
        dead = (S.dead >= 1 and S.vpip == 0 and h >= 3) or (h >= self.k.dead_hands and S.vpip == 0)
        return vp, pfr, f2r, r3, shv, fb, agg, dead

    def _pre_body(self, o, legal, hole, stacks, bets, inh, n, seat, sbv, bb, pot, to_call, button):
        kn = self.k
        ci = _cls(hole); p = PCT[ci]
        tot = [stacks[i] + bets[i] for i in range(n)]
        mytot = tot[seat]
        alive = [i for i in range(n) if tot[i] > 0 or inh[i]]
        n_alive = len(alive)
        opp_in = [i for i in range(n) if inh[i] and i != seat]
        if not opp_in: return self._call_or_check(legal)
        eff = min(mytot, max(tot[i] for i in opp_in))
        eff_bb = eff / float(bb)
        level = max(bets) if bets else 0
        pot_tot = pot + sum(min(b, mytot) for b in bets)  # chips I can actually win
        # players still to act behind me (in hand, not yet having put in level)
        order = []
        for k in range(1, n):
            s = (seat + k) % n
            order.append(s)
        # seats that act after me this round: those in hand who haven't matched/acted -> approximate by position
        sbs, bbs = self._blind_seats(alive, button, n)
        behind = []
        # positions: after me until the BB (inclusive)
        if bbs is not None and seat != bbs:
            for s in order:
                if inh[s] and stacks[s] > 0: behind.append(s)
                if s == bbs: break
        raisers = []
        for s in range(n):
            if s != seat and inh[s] and bets[s] > bb: raisers.append(s)
        n_raises = max(getattr(self, 'n_raises', 0), 1 if raisers else 0)
        if level <= bb:
            n_raises = 0
        short = eff_bb <= kn.short_bb
        # ---------------- unopened (maybe limpers)
        if n_raises == 0:
            limpers = [s for s in opp_in if bets[s] >= bb and s != bbs]
            # fold equity of everybody behind
            pf = 1.0
            for s in behind: pf *= self._fold_prob(s, short)
            for s in limpers: pf *= self._fold_prob(s, short) * 0.9
            n_beh = len(behind) + len(limpers)
            if short:
                cands = behind + limpers
                if not cands:
                    return self._raise(legal, o, o.max_raise) if p <= 0.5 else self._call_or_check(legal)
                # likely caller: the loosest seat behind; its calling range = 1 - fold prob
                fps = [(self._fold_prob(s, True), s) for s in cands]
                fmin, caller = min(fps)
                big = max(cands, key=lambda s: tot[s])
                opp = caller if tot[caller] >= mytot else big
                wc = min(1.0, max(0.03, 1.0 - fmin))
                eqc = _eqvs(ci, wc)
                ncall = sum(1 for f_, s_ in fps if f_ < 0.5)
                if ncall >= 2: eqc = eqc ** (1.0 + 0.5 * (ncall - 1))
                evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, opp, pot, n_alive)
                ev_sh = pf * evs + (1 - pf) * (eqc * evw + (1 - eqc) * evl)
                if ev_sh > evf + kn.push_margin:
                    return self._raise(legal, o, o.max_raise)
                return self._fold(legal) if to_call > 0 else self._call_or_check(legal)
            # deeper: raise-first-in / isolate
            base = {0: 1.0, 1: 0.48, 2: 0.36, 3: 0.27, 4: 0.21, 5: 0.17, 6: 0.14, 7: 0.12}.get(len(behind), 0.11)
            if limpers:
                base = 0.14 + 0.03 * sum(1 for s in limpers if self._rates(s)[0] > 0.5)
            if n_alive <= 4: base *= 1.2
            # re-shovers / 3bettors behind tighten
            r3max = max([self._rates(s)[3] for s in behind] or [0])
            if r3max > 0.2: base *= 0.75
            base *= kn.open_scale
            if len(behind) in (2, 3): base *= kn.open_late_scale  # the cutoff and the button
            size = bb * (2.5 if len(behind) > 1 else 2.2) + bb * len(limpers)
            if limpers and any(self._rates(s)[0] > 0.55 for s in limpers): size += bb * len(limpers)
            ev_steal = pf * pot_tot - (1 - pf) * (size - bets[seat]) * 0.55
            if p <= base or (n_beh and ev_steal > 0 and p <= 0.85) or (n_beh and pf > 0.9):
                return self._raise(legal, o, size)
            if 'check' in legal: return ('check', 0)
            if seat == sbs and to_call <= sbv and p <= 0.45 and len(limpers) == 0:
                return ('call', 0)
            if limpers and to_call <= bb and p <= 0.30 and eff_bb > 30:
                return ('call', 0)
            return ('fold', 0)
        # ---------------- facing raise(s)
        agg = max(raisers, key=lambda s: bets[s]) if raisers else (self.pf_aggr if self.pf_aggr is not None else None)
        if agg is None or not (0 <= agg < n): agg = opp_in[0]
        vp, pfr, f2r, r3, shv, fb, aggf, dead = self._rates(agg)
        agg_allin = stacks[agg] == 0 and inh[agg]
        if n_raises <= 1:
            w = min(1.0, max(0.04, pfr * 1.25))
            if bets[agg] >= 0.85 * tot[agg] or agg_allin:
                w = min(1.0, max(0.05, pfr * 1.1))
        else:
            w = min(0.6, max(0.03, r3 * 0.9 + 0.02))
        eq = _eqvs(ci, w)
        # multiway: every other opponent who put money in beyond the blind must also be beaten
        k = sum(1 for s in opp_in if bets[s] > bb)
        if k >= 2:
            eq = eq ** (1.0 + 0.75 * (k - 1))
        nb = len([s for s in behind if s not in raisers])
        if nb: eq *= (1.0 - 0.015 * nb)
        callamt = min(to_call, stacks[seat])
        req = callamt / float(pot_tot + callamt) if pot_tot + callamt > 0 else 1.0
        commit = callamt >= 0.4 * stacks[seat] or eff_bb <= kn.commit_bb or agg_allin or n_raises >= 2
        # (rival 3 computes self._icm_margin(...) here and never reads it: dropped)
        if commit:
            evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, agg, pot, n_alive)
            ev_call = eq * evw + (1 - eq) * evl
            can_shove = 'raise' in legal and not agg_allin
            if can_shove:
                # fold equity of the aggressor (and anyone behind) vs our shove
                fo = self._fold_prob(agg, True) * (0.5 if n_raises >= 2 else 0.8)
                for s in behind:
                    if s != agg: fo *= self._fold_prob(s, True)
                wc = min(1.0, max(0.03, w * 0.6))
                eqc = _eqvs(ci, wc)
                if k >= 2: eqc = eqc ** (1.0 + 0.75 * (k - 1))
                ev_sh = fo * evs + (1 - fo) * (eqc * evw + (1 - eqc) * evl)
                if ev_sh > evf + kn.push_margin and ev_sh >= ev_call:
                    return self._raise(legal, o, o.max_raise)
            if ev_call > evf + kn.call_margin:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            return self._fold(legal)
        # deep: 3bet value / call / fold
        if n_raises == 1:
            v3 = (min(0.06, w * 0.3) if pfr < 0.35 else min(0.18, w * 0.35)) * kn.three_bet_scale
            if p <= max(0.025, v3):
                size = bets[agg] * 3 + bb
                if size > 0.4 * mytot: size = o.max_raise
                return self._raise(legal, o, size)
            implied = 0.06 if eff_bb > 40 and callamt < 0.1 * stacks[seat] else 0.0
            if ci is not None and CLASSES[ci][0] == CLASSES[ci][1] and callamt <= 0.07 * stacks[seat]:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            if eq + implied >= req + 0.08 and p <= max(0.22, w * 0.7):
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            if seat == bbs and callamt <= 2 * bb and eq >= req and p <= 0.5:
                return ('call', 0) if 'call' in legal else self._call_or_check(legal)
            return self._fold(legal)
        # 3bet+ deep
        if p <= 0.025 or eq >= 0.6:
            return self._raise(legal, o, o.max_raise) if 'raise' in legal else self._call_or_check(legal)
        if p <= 0.05 and eq >= req + 0.05:
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        return self._fold(legal)

    def _post_body(self, o, legal, hole, board, stacks, bets, inh, n, seat, bb, pot, to_call, street):
        if len(board) < 3: return self._call_or_check(legal) if to_call == 0 else self._fold(legal)
        kn = self.k
        e, draw = self._strength(hole, board, street)
        opps = [i for i in range(n) if inh[i] and i != seat]
        if not opps: return self._call_or_check(legal)
        nop = len(opps)
        if nop > 1: e = e ** (1.0 + 0.45 * (nop - 1)) if e < 0.85 else e - 0.03 * (nop - 1)
        rates = [self._rates(s) for s in opps]
        stations = sum(1 for r in rates if r[0] > 0.5 and r[5] < 0.35)
        avg_fold = 1.0
        for r in rates: avg_fold *= (1.0 if r[7] else r[5])
        pot_tot = pot + sum(bets)
        mystack = stacks[seat]
        spr = mystack / float(max(1, pot_tot))
        if to_call <= 0:
            # value
            thr = 0.6 if stations == 0 else 0.52
            if e >= thr:
                frac = 0.65 if stations == 0 else 0.85
                if e >= 0.85: frac = 0.8 if stations == 0 else 1.0
                amt = bets[seat] + max(bb, int(pot_tot * frac))
                if spr < 1.3 and e >= 0.6: amt = o.max_raise
                return self._raise(legal, o, amt) or self._call_or_check(legal)
            # bluffs / semi-bluffs, never into stations
            if stations == 0 and nop <= 2:
                bluffp = 0.0
                if self.my_pf_raise and street == 1: bluffp = 0.55 if avg_fold > 0.45 else 0.3
                elif street >= 2 and avg_fold > 0.6 and nop == 1: bluffp = 0.4
                if draw: bluffp = max(bluffp, 0.5)
                if avg_fold > 0.85: bluffp = 0.9
                if self.rng.random() < bluffp * kn.bluff_scale:
                    amt = bets[seat] + max(bb, int(pot_tot * 0.5))
                    return self._raise(legal, o, amt) or self._call_or_check(legal)
            return self._call_or_check(legal)
        # facing a bet
        aggr = max(opps, key=lambda s: bets[s])
        vp, pfr, f2r, r3, shv, fb, ag, dead = self._rates(aggr)
        adj = 0.0
        raised_me = bets[seat] > 0
        if ag > 0.5 or pfr > 0.4: adj += (0.08 if not raised_me else 0.02)   # maniac: range is wide
        elif ag < 0.25 and vp < 0.3: adj -= 0.08    # nit bets: believe it
        if vp > 0.5 and ag < 0.3: adj -= 0.03       # station betting = real hand
        if raised_me and e < 0.85: adj -= 0.12      # a raise over my bet is stronger than a bet
        e2 = min(0.97, e + adj)
        callamt = min(to_call, mystack)
        req = callamt / float(pot_tot + callamt)
        if callamt > 0.35 * mystack and e2 < 0.6 and street < 3 and not draw:
            req = max(req, 0.5)
        if callamt >= 0.45 * mystack:
            try:
                n_alive = sum(1 for i in range(n) if stacks[i] + bets[i] > 0 or inh[i])
                evf, evs, evw, evl = self._allin(stacks, bets, inh, seat, aggr, pot, n_alive)
                if evw > evl: req = max(req, (evf - evl) / (evw - evl))
            except Exception:
                pass
        if e2 >= 0.8 + kn.raise_shift or (e2 >= 0.7 + kn.raise_shift and spr < 2):
            amt = bets[aggr] * 3 if spr > 2 else o.max_raise
            if stations or ag > 0.5: amt = max(amt, bets[seat] + int(pot_tot + callamt))
            r = self._raise(legal, o, amt)
            if r and self.rng.random() < 0.8: return r
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        implied = 0.05 if draw and spr > 3 and street < 3 else 0.0
        if e2 + implied >= req + kn.call_edge:
            return ('call', 0) if 'call' in legal else self._call_or_check(legal)
        return self._fold(legal)

    def _replay(self, hist, o, final=False):
        try:
            return R3.Bot._replay(self, hist, o, final)
        except Exception:
            self.replay_errors += 1
            raise

    def _allin(self, stacks, bets, inh, seat, opp, pot, n_alive):
        """Rival 3's `_allin` (ICM values of fold, steal, win, lose against `opp`) with this table's payouts."""
        pays = self.payouts
        n = len(stacks)
        tot = [stacks[j] + bets[j] for j in range(n)]
        mytot = tot[seat]
        pot_all = pot + sum(bets)
        dead_other = pot_all - bets[seat] - bets[opp]
        c = min(tot[opp], mytot)
        base = list(stacks)
        f = list(base)
        f[opp] += pot_all
        ev_fold = icm_points(f, seat, pays)
        st = list(base)
        st[seat] = mytot + pot_all - bets[seat]
        ev_steal = icm_points(st, seat, pays)
        w = list(base)
        w[seat] = mytot + c + dead_other
        w[opp] = tot[opp] - c
        ev_win = icm_points(w, seat, pays)
        lo = list(base)
        lo[seat] = mytot - c
        lo[opp] = tot[opp] + c + dead_other
        if lo[seat] <= 0:
            place = min(len(pays), max(1, n_alive)) - 1  # busting now: last of the n_alive places
            ev_lose = float(pays[place]) if 0 <= place < len(pays) else 0.0
        else:
            ev_lose = icm_points(lo, seat, pays)
        return ev_fold, ev_steal, ev_win, ev_lose
