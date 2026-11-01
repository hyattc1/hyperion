"""Short-stack engine: push / fold / call-a-shove from precomputed heads-up Nash ranges, tightened
multiway by a one-line rule, gated by ICM.

Offline (tools or the fallback at load):
  solve_hu_pushfold(matrix, depths)  fictitious play on the 169x169 all-in equity matrix for the
  SB-pushes / BB-calls game at each stack depth S (blinds 0.5/1, no antes):
      push EV(h)  = sum_h' w(h'|h) [ c(h') * S(2e - 1) + (1 - c(h')) * 1 ]   vs  fold = -0.5
      call EV(h') = sum_h  w(h|h') p(h) * S(2e' - 1)                          vs  fold = -1
  with card-removal weights w. Each side best-responds to the other's *average* strategy and the
  averages converge to the mixed Nash equilibrium (the game is two-player zero-sum); a depth starts
  from the previous depth's solution and stops when neither side can gain more than `tol` big
  blinds per hand by deviating. The 2026-10-31 HRC cross-check traced the 21-25 bb zig-zag to the
  old damped loop ending on alternate sides of the boundary at successive depths; the averaged,
  converged solution has no such oscillation. Output per depth: push set and call set (the mixed
  strategy thresholded at 0.5), their combo frequencies (of the mixed strategy), and each hand's
  equity against the opposing mixed range. Cached to tables/pushfold_hu.json. A live-class mask
  (short deck: 81 of the 169) keeps dead classes out of both ranges and out of the frequencies.

Multiway rule (plainly): rank every hand by the deepest stack at which heads-up Nash still pushes
it (ties by heads-up equity). With k opponents able to call, push the top
      f = p_push_HU(S) / (1 + c * (k - 1)),  c = 0.3 by default,
of hands by that order: k = 1 is the heads-up range, the button (k = 2) pushes 77% of it (about
39% of hands at 10 bb), UTG eight-handed (k = 7) 36% of it (about 18%), close to published
multiway Nash tables. Dead seats do not count toward k. Calls use the same shape
with the call order and p_call_HU. Opponent dials stretch f, clamped.

Hands that are not one of the 169 classes (3- and 4-card variants label hands 'AKs+l'; see
tablegen.hole_label) go through the same rule with the label's own percentile from the variant's
preflop_rank table and its equity vs one random hand discounted by the average gap, at that depth,
between "vs random" and "vs the Nash calling range" measured on the 169 solution.

ICM gate: a candidate push or call must have positive ICM-weighted EV against folding, using the
Nash caller frequency and the hand's equity against the calling range. ICM comes from a value
curve V(my stack) that Hero precomputes once per hand (exact ICM is ~0.5 ms for eight seats, too
slow for the decision path); without it V is chip-proportional and the gate is plain chip EV. A
bounty's expected chips (Spot.bounty_bonus) sit in every pot we win; a knockout bounty's points
(Spot.ko_points, times the share of opponents we cover) are added to the winning branch when the
curve is in points.
"""
from __future__ import annotations

import os
from dataclasses import dataclass

from ..core.cards import class_combos
from ..core.types import Action, ActionKind
from .profiler import Profiler
from .spot import Spot
from .tables import CLASSES, CLASS_INDEX, COMBO_COUNT, TABLES_DIR, TOTAL_COMBOS, Tables, read_json, write_json

_FOLD = Action(ActionKind.FOLD)
_CHECK = Action(ActionKind.CHECK)
_CALL = Action(ActionKind.CALL)
_BB_OPEN_PRIOR = (0.45, 0.45, 0.40, 0.28, 0.22, 0.18, 0.15, 0.13)  # PreflopParams.bb_open_prior's default
_mw = None  # hyperion.strategy.multiway, imported on first use (it imports from this module)
DEFAULT_DEPTHS = tuple(range(1, 26))


@dataclass
class PushFoldParams:
    threshold_bb: float = 10.0  # effective stack at or below this: push or fold preflop (swept: 12 -> 10 is +0.14 on the strong field, 15 is -0.11)
    tighten_per_player: float = 0.3  # the c in the multiway rule
    multiway_equity_penalty: float = 0.02  # per extra caller, off the equity vs the HU calling range
    reshove_raiser_call_prob: float = 0.6
    bb_flat_max_frac: float = 0.12  # BB closing the action may flat this share of stack with a decent hand
    bb_flat_min_rank: float = 0.5
    dial_min: float = 0.6
    dial_max: float = 2.0
    icm_epsilon: float = 1e-6
    call_equity_margin: float = 0.0  # off the equity when calling a shove (the solver's caller is exact; the field is not)
    # callers who call shoves wider than the prior (profiler call_vs_shove / P_CALL_SHOVE = looseness L):
    loose_caller_tighten: float = 0.0  # push slice f /= 1 + this * (mean L - 1)+ : fewer light shoves into loose callers
    loose_caller_equity_blend: float = 0.0  # equity moves from "vs Nash calling range" toward "vs random" by this * (max L - 1)+
    push_equity_margin: float = 0.0  # off the equity when pushing
    cheap_push_frac_mult: float = 0.8  # Hero.cheap(): a bit tighter than the rule, no dials
    # the solved multiway tables (tables/pushfold_multi.json, multiway.py): first-in shoves against k behind, and
    # re-shoves over one open, from the chip-EV equilibrium; the solve's no-call probability and equity-when-called
    # feed the ICM gate. Off, or no table for this matrix: the heuristic rule above (tighten_per_player).
    use_multiway: bool = True
    use_reshove_table: bool = True
    # exploitative first-in shoves: instead of the top p_push of hands, shove any hand whose ICM EV beats folding
    # when each caller calls the top c_j of hands, c_j = its seat type's solved call frequency times its observed
    # call-vs-shove rate over the prior (smoothed with exploit_prior_n shoves faced, clamped to [exploit_l_min,
    # exploit_l_max]). Against Nash callers this is the solved set; against seats that over-fold it shoves wider.
    exploit_push: bool = False
    exploit_prior_n: float = 4.0
    exploit_l_min: float = 0.3
    exploit_l_max: float = 3.0
    exploit_expected_norm: bool = True  # looseness = calls / a solved caller's calls in the same spots (profiler.call_prior)
    # the opener's width w for the re-shove table (and for reading a re-shove when calling): its observed first-in
    # open rate at > 12 bb from its position class (late = cutoff, button, small blind; early), smoothed toward
    # bb_open_prior[its seat] with reshove_w_n0 spots. Off = bb_open_prior times its PFR over the prior.
    reshove_w_observed: bool = False
    reshove_w_n0: float = 6.0
    # the first-in shove zone: an unopened pot above threshold_bb is still push/fold (the solved first-in table
    # with its ICM gate) up to fi_threshold_bb effective, and up to fi_late_threshold_bb with at most fi_late_behind
    # players behind. Hands the table does not shove fold, or with fi_rest_open fall through to the preflop chart's
    # open-raise. 0 = off (the chart opens everything above threshold_bb).
    fi_threshold_bb: float = 0.0
    fi_late_threshold_bb: float = 0.0
    fi_late_behind: int = 2
    fi_rest_open: bool = False


# ---------------------------------------------------------------- offline solver

def removal_weights(live=None) -> list[list[int]]:
    """w[i][j] = combos of class j that share no card with a representative combo of class i.
    `live` (169 bools) zeroes the columns of classes the deck cannot make."""
    reps = [class_combos(c)[0] for c in CLASSES]
    combos = [class_combos(c) for c in CLASSES]
    n = len(CLASSES)
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        a, b = reps[i]
        row = w[i]
        for j in range(n):
            if live is not None and not live[j]:
                continue
            cnt = 0
            for x, y in combos[j]:
                if x != a and x != b and y != a and y != b:
                    cnt += 1
            row[j] = cnt
    return w


def _caller_br(push: list[float], e: list[list[float]], w: list[list[int]], S: float) -> list[float]:
    n = len(push)
    out = [0.0] * n
    for j in range(n):
        wj, ej = w[j], e[j]
        tot = 0.0
        for i in range(n):
            p = push[i]
            if p:
                tot += wj[i] * p * (S * (2.0 * ej[i] - 1.0) + 1.0)
        out[j] = 1.0 if tot > 0.0 else 0.0
    return out


def _pusher_br(call: list[float], e: list[list[float]], w: list[list[int]], S: float) -> list[float]:
    n = len(call)
    out = [0.0] * n
    for i in range(n):
        wi, ei = w[i], e[i]
        tot = 0.0
        den = 0
        for j in range(n):
            wij = wi[j]
            if wij:
                den += wij
                c = call[j]
                tot += wij * (c * S * (2.0 * ei[j] - 1.0) + (1.0 - c))
        out[i] = 1.0 if den and tot / den > -0.5 else 0.0
    return out


def _gains(push, call, br_push, br_call, e, w, S, counts, total) -> tuple[float, float]:
    """How much (bb per hand) each side gains by best-responding instead of playing its average."""
    n = len(push)
    g_push = 0.0
    for i in range(n):
        if not counts[i]:
            continue
        wi, ei = w[i], e[i]
        tot = 0.0
        den = 0
        for j in range(n):
            wij = wi[j]
            if wij:
                den += wij
                c = call[j]
                tot += wij * (c * S * (2.0 * ei[j] - 1.0) + (1.0 - c))
        ev_push = tot / den if den else -0.5
        g_push += counts[i] * (br_push[i] - push[i]) * (ev_push + 0.5)
    g_call = 0.0
    for j in range(n):
        if not counts[j]:
            continue
        wj, ej = w[j], e[j]
        tot = 0.0
        den = 0
        for i in range(n):
            p = push[i]
            if p:
                x = wj[i] * p
                den += x
                tot += x * (S * (2.0 * ej[i] - 1.0) + 1.0)
        ev_call = tot / den if den else -1.0  # relative to folding (-1): calling gains ev_call
        g_call += counts[j] * (br_call[j] - call[j]) * ev_call
    return g_push / total, g_call / total


def _eq_vs_range(rng: list[float], e: list[list[float]], w: list[list[int]]) -> list[float]:
    n = len(rng)
    out = [0.5] * n
    for i in range(n):
        wi, ei = w[i], e[i]
        num = den = 0.0
        for j in range(n):
            x = wi[j] * rng[j]
            if x:
                num += x * ei[j]
                den += x
        if den:
            out[i] = num / den
    return out


def _freq(rng: list[float], counts=COMBO_COUNT, total: int = TOTAL_COMBOS) -> float:
    return sum(counts[i] * rng[i] for i in range(len(rng))) / total


def solve_hu_pushfold(matrix: list[list[float]], depths=DEFAULT_DEPTHS, iters: int = 600, live=None,
                      tol: float = 1e-4) -> dict:
    """Heads-up push/fold per depth by fictitious play (see the module doc). `iters` caps the iterations
    per depth; a depth stops early once both sides' best-response gains are under `tol`. Returns the
    JSON-able table described in the module doc plus `converged` {depth: [iterations, gain]}."""
    n = len(CLASSES)
    counts = [COMBO_COUNT[i] if (live is None or live[i]) else 0 for i in range(n)]
    total = sum(counts) or TOTAL_COMBOS
    w = removal_weights(live)
    out = {"classes": list(CLASSES), "depths": list(depths), "push": {}, "call": {}, "p_push": {}, "p_call": {},
           "eq_vs_call": {}, "eq_vs_push": {}, "converged": {}}
    push = call = None
    for S in sorted(float(d) for d in depths):
        if push is None:
            # cold start: a short damped best-response run lands near the equilibrium (averaging from
            # "push everything" would take hundreds of iterations to forget it); the averages do the rest
            push = [1.0 if counts[i] else 0.0 for i in range(n)]
            call = [c if counts[i] else 0.0 for i, c in enumerate(_caller_br(push, matrix, w, S))]
            for _ in range(min(40, iters)):
                br_call = _caller_br(push, matrix, w, S)
                br_push = _pusher_br(call, matrix, w, S)
                for i in range(n):
                    if counts[i]:
                        push[i] += 0.5 * (br_push[i] - push[i])
                        call[i] += 0.5 * (br_call[i] - call[i])
        gain = (1.0, 1.0)
        t = 0
        for t in range(1, iters + 1):
            br_call = _caller_br(push, matrix, w, S)
            br_push = _pusher_br(call, matrix, w, S)
            if t % 10 == 0 or t == iters:
                gain = _gains(push, call, br_push, br_call, matrix, w, S, counts, total)
                if gain[0] + gain[1] < tol:
                    break
            a = 1.0 / (t + 1)
            for i in range(n):
                if counts[i]:
                    push[i] += a * (br_push[i] - push[i])
                    call[i] += a * (br_call[i] - call[i])
        key = str(int(S)) if S == int(S) else str(S)
        out["push"][key] = [1 if (x >= 0.5 and counts[i]) else 0 for i, x in enumerate(push)]
        out["call"][key] = [1 if (x >= 0.5 and counts[i]) else 0 for i, x in enumerate(call)]
        out["p_push"][key] = round(_freq(push, counts, total), 4)
        out["p_call"][key] = round(_freq(call, counts, total), 4)
        out["eq_vs_call"][key] = [round(x, 4) for x in _eq_vs_range(call, matrix, w)]
        out["eq_vs_push"][key] = [round(x, 4) for x in _eq_vs_range(push, matrix, w)]
        out["converged"][key] = [t, round(gain[0] + gain[1], 6)]
        push, call = push[:], call[:]  # warm start for the next depth
    return out


def matrix_fingerprint(hu) -> str:
    """Cheap identity of a heads-up matrix, so a push/fold cache solved from an older matrix is detected."""
    import hashlib
    h = hashlib.sha1()
    for row in hu:
        h.update(("%.4f," * len(row) % tuple(row)).encode())
    return h.hexdigest()[:16]


def build_pushfold_tables(tables: Tables, tables_dir: str = TABLES_DIR, depths=DEFAULT_DEPTHS, write: bool = True,
                          iters: int = 600) -> dict:
    """Solve from tables.hu (over tables.live) and (optionally) write tables/pushfold_hu.json. For tools/gen_tables.py."""
    sol = solve_hu_pushfold(tables.hu, depths, iters=iters, live=tables.live)
    sol["matrix_fp"] = matrix_fingerprint(tables.hu)
    sol["n_classes"] = sum(1 for x in (tables.live or []) if x) or len(CLASSES)
    if write:
        write_json("pushfold_hu.json", sol, tables_dir)
    return sol


_SOLUTIONS: dict[str, dict] = {}


def load_pushfold(tables: Tables, tables_dir: str | None = None) -> dict:
    """The solution for `tables` (from its own directory by default), re-solved when the cached file was
    solved from a different matrix. Memoised per directory so new_table does not re-read 75 KB of JSON."""
    tables_dir = tables_dir or tables.dir or TABLES_DIR
    fp = matrix_fingerprint(tables.hu)
    sol = _SOLUTIONS.get(tables_dir)
    if sol is not None and sol.get("matrix_fp") == fp:
        return sol
    raw = read_json("pushfold_hu.json", tables_dir)
    if raw and raw.get("classes") == list(CLASSES) and raw.get("depths") and raw.get("matrix_fp") == fp:
        _SOLUTIONS[tables_dir] = raw
        return raw
    # stale or missing: solved from a different matrix (tables were regenerated for a variant). Re-solve.
    sol = build_pushfold_tables(tables, tables_dir, write=os.access(tables_dir, os.W_OK) if os.path.isdir(tables_dir) else False)
    _SOLUTIONS[tables_dir] = sol
    return sol


# ---------------------------------------------------------------- the engine

class _Linear:
    """Chip-proportional value curve: the fallback when no ICM curve is set."""
    __slots__ = ()
    points = False  # values are chips, not tournament points: knockout points cannot be added to them

    def value(self, x: float) -> float:
        return x


class PushFold:
    def __init__(self, params: PushFoldParams, tables: Tables, solution: dict | None = None):
        self.p = params
        self.tables = tables
        self.rank = tables.rank
        self.equity = tables.equity
        self.counts = tables.combo_count
        self.total = tables.total_combos or TOTAL_COMBOS
        sol = solution or load_pushfold(tables)
        self.depths = [int(d) for d in sol["depths"]]
        self.max_depth = max(self.depths)
        self.min_depth = min(self.depths)
        self.push_set = {int(k): v for k, v in sol["push"].items()}
        self.call_set = {int(k): v for k, v in sol["call"].items()}
        self.p_push = {int(k): v for k, v in sol["p_push"].items()}
        self.p_call = {int(k): v for k, v in sol["p_call"].items()}
        self.eq_vs_call = {int(k): v for k, v in sol["eq_vs_call"].items()}
        self.eq_vs_push = {int(k): v for k, v in sol["eq_vs_push"].items()}
        self.push_pct = self._order_pct(self.push_set)
        self.call_pct = self._order_pct(self.call_set)
        self.call_disc = {D: self._discount(self.push_set[D], self.eq_vs_call[D]) for D in self.depths}
        self.push_disc = {D: self._discount(self.call_set[D], self.eq_vs_push[D]) for D in self.depths}
        self.curve = _Linear()
        self.last = ""  # the sub-decision taken last (diagnostics: the runner's bust tracer reads it)
        self.pre = None  # Hero's Preflop module (installed by HeroCore): its shover-range read is shared
        try:
            global _mw
            if _mw is None:
                from . import multiway as _m  # multiway imports this module's solver helpers: import it late

                _mw = _m
            self.mw = _mw.load_multiway(tables) if (params.use_multiway and tables.scheme == "169") else None
        except Exception:  # noqa: BLE001 - a broken table file means the heuristic rule, never a crash
            self.mw = None

    def with_tables(self, tables: Tables) -> "PushFold":
        """The same solution and dials, looking hands up in another rank / equity table (a 3- or 4-card
        variant's labels). Cheap: shares every solved array."""
        import copy

        other = copy.copy(self)
        other.tables = tables
        other.rank = tables.rank
        other.equity = tables.equity
        return other

    def _order_pct(self, sets: dict[int, list[int]]) -> dict[str, float]:
        """cls -> combo-weighted share of live hands strictly ahead of it in (max depth, HU rank) order."""
        depth_of = []
        for i, c in enumerate(CLASSES):
            d = 0
            for D in self.depths:
                if sets[D][i]:
                    d = D
            depth_of.append((-d, -self.rank[c], i))
        depth_of.sort()
        out = {}
        before = 0
        for _, _, i in depth_of:
            out[CLASSES[i]] = before / self.total
            before += self.counts.get(CLASSES[i], 0)
        return out

    def _discount(self, members: list[int], eq_vs: list[float]) -> float:
        """Combo-weighted mean gap between a member's equity vs one random hand and vs the opposing range."""
        num = den = 0.0
        for i, c in enumerate(CLASSES):
            k = self.counts.get(c, 0)
            if members[i] and k:
                num += k * (self.equity[c][0] - eq_vs[i])
                den += k
        return num / den if den else 0.0

    # ------------------------------------------------------------ class keys: 169 labels or variant labels
    @staticmethod
    def _idx(cls: str) -> int:
        return CLASS_INDEX.get(cls, -1)

    def _ppct(self, cls: str, i: int) -> float:
        return self.push_pct[cls] if i >= 0 else 1.0 - self.rank[cls]

    def _cpct(self, cls: str, i: int) -> float:
        return self.call_pct[cls] if i >= 0 else 1.0 - self.rank[cls]

    def _e_call(self, D: int, cls: str, i: int) -> float:
        return self.eq_vs_call[D][i] if i >= 0 else self.equity[cls][0] - self.call_disc[D]

    def _e_push(self, D: int, cls: str, i: int) -> float:
        return self.eq_vs_push[D][i] if i >= 0 else self.equity[cls][0] - self.push_disc[D]

    def depth(self, eff_bb: float) -> int:
        d = int(eff_bb + 0.5)
        return self.min_depth if d < self.min_depth else self.max_depth if d > self.max_depth else d

    def applies(self, spot: Spot) -> bool:
        return spot.cls is not None and (spot.eff_bb <= self.p.threshold_bb or self.fi_zone(spot))

    def fi_zone(self, spot: Spot) -> bool:
        """An unopened pot above threshold_bb that the first-in shove zone covers."""
        p = self.p
        if spot.n_raises or spot.eff_bb <= p.threshold_bb:
            return False
        top = p.fi_threshold_bb
        if spot.behind <= p.fi_late_behind and p.fi_late_threshold_bb > top:
            top = p.fi_late_threshold_bb
        return spot.eff_bb <= top

    def _clamp(self, m: float) -> float:
        return self.p.dial_min if m < self.p.dial_min else self.p.dial_max if m > self.p.dial_max else m

    # ------------------------------------------------------------ decisions
    def act(self, spot: Spot, prof: Profiler | None, cheap: bool = False) -> Action:
        if spot.facing_shove:
            self.last = "call_shove"
            return self._call_shove(spot, prof, cheap)
        if spot.n_raises == 0:
            self.last = "push"
            return self._push_or_fold(spot, prof, cheap)
        self.last = "reshove"
        return self._reshove(spot, prof, cheap)

    def _callers(self, spot: Spot, prof: Profiler | None):
        """Opponents who could still call a shove: not folded, not already all-in, not dead."""
        obs = spot.obs
        seats = []
        for s in spot.opps:
            if obs.stacks[s] <= 0:
                continue
            if prof is not None and prof.dead_seat(s):
                continue
            seats.append(s)
        return seats

    def _push_or_fold(self, spot: Spot, prof: Profiler | None, cheap: bool) -> Action:
        p = self.p
        obs = spot.obs
        cls = spot.cls
        i = self._idx(cls)
        D = self.depth(spot.eff_bb)
        callers = self._callers(spot, prof)
        k = len(callers)
        free = _CHECK if ActionKind.CHECK in obs.legal else _FOLD
        if k == 0:
            # nobody live can call: any shove takes the pot (dead seats fold to a bet)
            self.last = "push_free"
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else free
        mw = self.mw
        if mw is not None and i >= 0:
            return self._push_table(spot, prof, cheap, mw, cls, i, callers, free)
        f = self.p_push[D] / (1.0 + p.tighten_per_player * (k - 1))
        loose_sum = 0.0
        loose_max = 1.0
        if cheap:
            f *= p.cheap_push_frac_mult
        elif prof is not None:
            m = 0.0
            for s in callers:
                m += prof.exploit_dials(s)["steal_mult"]
                L = self._clamp(prof.call_vs_shove(s) / Profiler.P_CALL_SHOVE)
                loose_sum += L
                if L > loose_max:
                    loose_max = L
            f *= self._clamp(m / k)
            if p.loose_caller_tighten > 0.0 and loose_sum > k:
                f /= 1.0 + p.loose_caller_tighten * (loose_sum / k - 1.0)
        if self._ppct(cls, i) >= f:
            return free
        # ICM gate
        pc_none = 1.0
        base_pc = self.p_call[D] / (1.0 + p.tighten_per_player * (k - 1))
        for s in callers:
            pc = base_pc
            if prof is not None and not cheap:
                pc *= self._clamp(prof.call_vs_shove(s) / Profiler.P_CALL_SHOVE)
            pc_none *= 1.0 - (0.98 if pc > 0.98 else pc)
        pc_any = 1.0 - pc_none
        e = self._e_call(D, cls, i)
        if p.loose_caller_equity_blend > 0.0 and loose_max > 1.0:
            # a wide caller's range is nearer random than the Nash calling range: junk gains little, value hands gain
            w = p.loose_caller_equity_blend * (loose_max - 1.0)
            if w > 1.0:
                w = 1.0
            e += w * (self.equity[cls][0] - e)
        e -= p.multiway_equity_penalty * (k - 1) + p.push_equity_margin
        if self._push_ev_ok(spot, pc_any, e, spot.cover_frac):
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        return free

    def _looseness(self, prof: Profiler | None, seats) -> float:
        """Mean of the callers' call-vs-shove rate over the prior, clamped (1 = as the solve assumes)."""
        if prof is None or not seats:
            return 1.0
        m = 0.0
        for s in seats:
            m += self._clamp(prof.call_vs_shove(s) / Profiler.P_CALL_SHOVE)
        return m / len(seats)

    def _push_table(self, spot: Spot, prof: Profiler | None, cheap: bool, mw: dict, cls: str, i: int, callers,
                    free: Action) -> Action:
        """First-in shove from the solved table: the top p_push[k][S] by the solve's order (stretched by the
        callers' steal dials), then the ICM gate with the solve's no-call probability and equity when called."""
        p = self.p
        obs = spot.obs
        k = len(callers)
        if k > mw["k_max"]:
            k = mw["k_max"]
        S = _mw.depth(mw, spot.eff_bb)
        pre = self.pre
        if p.exploit_push and not cheap and pre is not None and pre.req is not None:
            return self._push_exploit(spot, prof, mw, cls, k, S, callers, free)
        f = mw["p_push"][k][S]
        loose = 1.0
        if cheap:
            f *= p.cheap_push_frac_mult
        elif prof is not None:
            m = 0.0
            for s in callers:
                m += prof.exploit_dials(s)["steal_mult"]
            f *= self._clamp(m / len(callers))
            loose = self._looseness(prof, callers)
        if mw["push_order"][k][i] >= f:
            return free
        pc_any = 1.0 - mw["pnc"][k][S][i]
        if loose != 1.0:
            pc_any *= loose
            if pc_any > 0.98:
                pc_any = 0.98
        e = mw["eqc"][k][S][i] - p.push_equity_margin
        if self._push_ev_ok(spot, pc_any, e, spot.cover_frac):
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        return free

    def call_prior(self, depth_bb: float) -> float:
        """A solved caller's probability of calling a shove `depth_bb` deep (types and seats averaged at k = 3;
        beyond the table's 25 bb it falls as 25 / depth)."""
        mw = self.mw
        if mw is None:
            return 0.12
        D = _mw.depth(mw, depth_bb)
        q = 0.0
        n = 0
        for t in ("n", "sb", "bb"):
            row = mw["p_call"][t][3]
            if row is not None and row[D] is not None:
                q += row[D]
                n += 1
        q = q / n if n else 0.12
        if depth_bb > mw["S_max"]:
            q *= mw["S_max"] / depth_bb
        return q

    def reshove_freq(self, spot: Spot, opener: int, shover: int, prof: Profiler | None = None):
        """The solved re-shove frequency for `shover` over `opener`'s open (None without the table): the opener's
        range is my own open fraction when I opened, else bb_open_prior by its seat (its observed open rate with
        reshove_w_observed); m = players behind the shover."""
        mw = self.mw
        if mw is None or opener < 0:
            return None
        rs = mw["reshove"]
        pre = self.pre
        kb = self.behind_seat(spot, opener)
        if opener == spot.me and pre is not None:
            pp = pre.p
            w = pp.open_frac.get(kb + pp.open_step, pp.open_frac_default) * pp.open_frac_mult
        elif self.p.reshove_w_observed and prof is not None:
            w = self.opener_width(spot, prof, opener)
        else:
            pri = pre.p.bb_open_prior if pre is not None else _BB_OPEN_PRIOR
            w = pri[kb] if kb < len(pri) else pri[-1]
        m = self.behind_seat(spot, shover)
        if m > rs["m_max"]:
            m = rs["m_max"]
        obs = spot.obs
        S = _mw.depth(rs, min(spot.my_total, obs.stacks[shover] + obs.bets[shover]) / spot.bb)
        return rs["p_push"][_mw.nearest_w(mw, w if w > 0 else 0.1)][m][S]

    def caller_width(self, spot: Spot, prof: Profiler | None, mw: dict, seat: int, k: int, S: int) -> float:
        """Estimated share of hands `seat` calls a shove with: its seat type's solved frequency at (k, S), times
        how often it has really called shoves against the prior."""
        t = "bb" if seat == spot.bb_seat else "sb" if seat == spot.sb_seat else "n"
        pc = mw["p_call"]
        row = pc[t][k] if pc[t][k] is not None else (pc["n"][k] or pc["bb"][k])
        q = row[S] if row is not None and row[S] is not None else 0.2
        if prof is not None:
            p = self.p
            n0 = p.exploit_prior_n
            if p.exploit_expected_norm and prof.call_prior is not None:
                L = prof.call_looseness(seat, n0)
            else:
                P = Profiler.P_CALL_SHOVE
                L = (prof.called_shove[seat] + P * n0) / (prof.faced_shove[seat] + n0) / P
            q *= p.exploit_l_min if L < p.exploit_l_min else p.exploit_l_max if L > p.exploit_l_max else L
        return 0.01 if q < 0.01 else 1.0 if q > 1.0 else q

    def _push_exploit(self, spot: Spot, prof: Profiler | None, mw: dict, cls: str, k: int, S: int, callers,
                      free: Action) -> Action:
        """Shove when the ICM EV against the callers' estimated ranges beats folding: the first caller j (each
        calls the top c_j, the ones before it folded) brings equity eq(cls vs top c_j); nobody calling takes the pot."""
        obs = spot.obs
        req = self.pre.req
        v = self.curve.value
        behind = obs.stacks[spot.me]
        pot = spot.pot_total + spot.bounty_bonus
        v_fold = v(behind)
        reach = 1.0
        ev = 0.0
        ko = spot.ko_points if (spot.ko_points and self.curve.points) else 0.0
        margin = self.p.push_equity_margin
        my_total = spot.my_total
        for s in callers:
            c = self.caller_width(spot, prof, mw, s, k, S)
            e = req.eq(cls, c)
            if e is None:
                return free
            e -= margin
            tot = obs.stacks[s] + obs.bets[s]
            risk = behind if behind < tot else tot
            v_win = v(behind + pot + risk) + (ko if tot <= my_total else 0.0)
            ev += reach * c * (e * v_win + (1.0 - e) * v(behind - risk))
            reach *= 1.0 - c
        ev += reach * v(behind + pot)
        if ev > v_fold + self.p.icm_epsilon:
            self.last = "push_exploit"
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        return free

    def _reshove_table(self, spot: Spot, prof: Profiler | None, mw: dict, cls: str, i: int, callers):
        """Re-shove over one open from the solved re-shove family: the opener's range is estimated like the
        big blind's defence (bb_open_prior by its seat, scaled by its PFR), m = players who could still call
        behind me. None = this spot is not one the table describes."""
        rs = mw["reshove"]
        obs = spot.obs
        raiser = spot.raiser
        if raiser < 0 or raiser == spot.me or obs.stacks[raiser] <= 0:
            return None
        wi = _mw.nearest_w(mw, self.opener_width(spot, prof, raiser))
        m = len(callers) - 1  # the opener is one of the callers
        if m < 0:
            m = 0
        if m > rs["m_max"]:
            m = rs["m_max"]
        S = _mw.depth(rs, spot.eff_bb)
        for c in rs["p_bcall"][wi][m][S] or ():
            if c is not None and c > 0.5:
                return None  # a short-stack cell on the no-overcall model's gamble branch (see multiway.py): not used
        f = rs["p_push"][wi][m][S]
        if prof is not None:
            f *= self._clamp(prof.fold_to_bet_pre(raiser) / Profiler.P_FTB)
        if rs["order"][wi][m][i] >= f:
            return False
        pc_any = 1.0 - rs["pnc"][wi][m][S][i]
        if prof is not None:
            pc_any *= self._looseness(prof, callers)
            if pc_any > 0.98:
                pc_any = 0.98
        e = rs["eqc"][wi][m][S][i] - self.p.push_equity_margin
        return self._push_ev_ok(spot, pc_any, e, spot.cover_frac)

    def opener_width(self, spot: Spot, prof: Profiler | None, opener: int) -> float:
        """Estimated share of hands `opener` opens from its seat: bb_open_prior by the players behind it, then either
        its observed first-in open rate from that position class (reshove_w_observed) or the prior times its PFR
        over the prior, clamped to [0.5, 2.5] of the prior."""
        pre = self.pre
        pri = pre.p.bb_open_prior if pre is not None else _BB_OPEN_PRIOR
        kb = self.behind_seat(spot, opener)
        w = pri[kb] if kb < len(pri) else pri[-1]
        if prof is None:
            return w
        if self.p.reshove_w_observed:
            return prof.open_rate(opener, kb <= Profiler.LATE_BEHIND, w, self.p.reshove_w_n0)
        r = prof.pfr_rate(opener) / Profiler.P_PFR
        return w * (0.5 if r < 0.5 else 2.5 if r > 2.5 else r)

    def reshove_mid(self, spot: Spot, prof: Profiler | None):
        """Above push/fold depth: shove over one open from the solved re-shove family (4-25 bb), True / False, or
        None when the table does not describe the spot."""
        mw = self.mw
        cls = spot.cls
        i = self._idx(cls) if cls is not None else -1
        if mw is None or i < 0 or not self.p.use_reshove_table:
            return None
        return self._reshove_table(spot, prof, mw, cls, i, self._callers(spot, prof))

    def _push_ev_ok(self, spot: Spot, pc_any: float, e: float, cover: float = 0.0) -> bool:
        obs = spot.obs
        v = self.curve.value
        behind = obs.stacks[spot.me]
        pot = spot.pot_total + spot.bounty_bonus
        risk = min(behind, spot.max_opp_total)
        v_fold = v(behind)
        v_steal = v(behind + pot)
        v_win = v(behind + pot + risk)
        v_lose = v(behind - risk)
        if spot.ko_points and self.curve.points:
            v_win += spot.ko_points * cover
        ev = pc_any * (e * v_win + (1.0 - e) * v_lose) + (1.0 - pc_any) * v_steal
        return ev > v_fold + self.p.icm_epsilon

    def _reshove(self, spot: Spot, prof: Profiler | None, cheap: bool) -> Action:
        """Facing a raise (not a shove) while short: shove over it, flat only in the big blind, else fold."""
        p = self.p
        obs = spot.obs
        cls = spot.cls
        i = self._idx(cls)
        D = self.depth(spot.eff_bb)
        callers = self._callers(spot, prof)
        k = len(callers)
        mw = self.mw
        if mw is not None and i >= 0 and p.use_reshove_table and spot.n_raises == 1 and not cheap:
            ok = self._reshove_table(spot, prof, mw, cls, i, callers)
            if ok:
                return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
            if ok is not None:
                if spot.behind == 0 and spot.to_call <= p.bb_flat_max_frac * spot.my_total and self.rank[cls] >= p.bb_flat_min_rank:
                    self.last = "bb_flat"
                    return _CALL
                return _CHECK if ActionKind.CHECK in obs.legal else _FOLD
        f = self.p_call[D] / (1.0 + p.tighten_per_player * max(0, k - 1))
        pc_raiser = p.reshove_raiser_call_prob
        if prof is not None and not cheap and spot.raiser >= 0:
            f *= self._clamp(prof.pfr_rate(spot.raiser) / Profiler.P_PFR)
            pc_raiser = min(0.95, pc_raiser * self._clamp(prof.call_vs_shove(spot.raiser) / Profiler.P_CALL_SHOVE))
        if cheap:
            f *= p.cheap_push_frac_mult
        if self._cpct(cls, i) < f:
            e = self._e_call(D, cls, i) - p.multiway_equity_penalty * max(0, k - 1) - p.push_equity_margin
            if self._push_ev_ok(spot, pc_raiser, e, spot.cover_frac):
                return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        if spot.behind == 0 and spot.to_call <= p.bb_flat_max_frac * spot.my_total and self.rank[cls] >= p.bb_flat_min_rank:
            self.last = "bb_flat"
            return _CALL
        return _CHECK if ActionKind.CHECK in obs.legal else _FOLD

    def nash_push_freq(self, k: int, D: int) -> float:
        """First-in push frequency with k players behind at depth D: the solved multiway table, else the
        heuristic multiway rule on the heads-up solution."""
        if k < 1:
            k = 1
        mw = self.mw
        if mw is not None:
            return mw["p_push"][k if k <= mw["k_max"] else mw["k_max"]][_mw.depth(mw, D)]
        return self.p_push[D] / (1.0 + self.p.tighten_per_player * (k - 1))

    @staticmethod
    def behind_seat(spot: Spot, seat: int) -> int:
        """Players dealt into this hand who act after `seat` preflop (who were still to act when it shoved)."""
        obs = spot.obs
        n = spot.n
        alive = 0
        for s in range(n):
            if obs.stacks[s] + obs.bets[s] > 0 or obs.in_hand[s]:
                alive += 1
        mine = Spot._pre_order(seat, obs.button, n, alive)
        k = 0
        for s in range(n):
            if s != seat and (obs.stacks[s] + obs.bets[s] > 0 or obs.in_hand[s]) and \
                    Spot._pre_order(s, obs.button, n, alive) > mine:
                k += 1
        return k

    def _call_shove(self, spot: Spot, prof: Profiler | None, cheap: bool) -> Action:
        p = self.p
        obs = spot.obs
        cls = spot.cls
        i = self._idx(cls)
        shover = spot.shover
        shover_total = obs.stacks[shover] + obs.bets[shover] if shover >= 0 else spot.max_opp_total
        D = self.depth(min(spot.my_total, shover_total) / spot.bb)
        k_behind = 0
        for s in spot.opps:
            if obs.bets[s] < spot.cur_bet and obs.stacks[s] > 0:
                k_behind += 1
        pre = self.pre
        if pre is not None and pre.p.shove_range_model and pre.req is not None and not cheap and shover >= 0:
            # the shover's range from its seat's Nash push frequency, scaled by how often this seat really shoves
            base = self.nash_push_freq(self.behind_seat(spot, shover), D)
            x = pre.shover_range(spot, prof, base)
            margin = p.call_equity_margin + p.multiway_equity_penalty * k_behind
            ok = pre.range_call_ok(spot, cls, x, margin, max(0, spot.n_in - 1))
            if ok is not None:
                return _CALL if ok else _FOLD
        f = self.p_call[D] / (1.0 + p.tighten_per_player * k_behind)
        if spot.n_in >= 2:
            f *= 0.5  # a shove and a call already: need a premium
        if prof is not None and not cheap and shover >= 0:
            f *= self._clamp(prof.exploit_dials(shover)["call_down_mult"])
            f *= self._clamp(prof.shove_rate(shover) / Profiler.P_SHOVE)
        if self._cpct(cls, i) >= f:
            return _FOLD
        e = self._e_push(D, cls, i) - p.multiway_equity_penalty * (k_behind + max(0, spot.n_in - 1)) \
            - p.call_equity_margin
        v = self.curve.value
        behind = obs.stacks[spot.me]
        v_fold = v(behind)
        v_win = v(behind + spot.pot_total + spot.bounty_bonus)
        v_lose = v(behind - spot.to_call)
        if spot.ko_points and spot.shover_covered and self.curve.points:
            v_win += spot.ko_points
        if e * v_win + (1.0 - e) * v_lose > v_fold + p.icm_epsilon:
            return _CALL
        return _FOLD
