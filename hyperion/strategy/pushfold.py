"""Short-stack engine: push / fold / call-a-shove from precomputed heads-up Nash ranges, tightened
multiway by a one-line rule, gated by ICM.

Offline (tools or the fallback at load):
  solve_hu_pushfold(matrix, depths)  iterates damped best responses on the 169x169 all-in equity
  matrix for the SB-pushes / BB-calls game at each stack depth S (blinds 0.5/1, no antes):
      push EV(h)  = sum_h' w(h'|h) [ c(h') * S(2e - 1) + (1 - c(h')) * 1 ]   vs  fold = -0.5
      call EV(h') = sum_h  w(h|h') p(h) * S(2e' - 1)                          vs  fold = -1
  with card-removal weights w. Output per depth: push set, call set, their combo frequencies,
  and each hand's equity against the opposing range. Cached to tables/pushfold_hu.json.

Multiway rule (plainly): rank every hand by the deepest stack at which heads-up Nash still pushes
it (ties by heads-up equity). With k opponents able to call, push the top
      f = p_push_HU(S) / (1 + c * (k - 1)),  c = 0.3 by default,
of hands by that order: k = 1 is the heads-up range, the button (k = 2) pushes 77% of it (about
39% of hands at 10 bb), UTG eight-handed (k = 7) 36% of it (about 18%), close to published
multiway Nash tables. Dead seats do not count toward k. Calls use the same shape
with the call order and p_call_HU. Opponent dials stretch f, clamped.

ICM gate: a candidate push or call must have positive ICM-weighted EV against folding, using the
Nash caller frequency and the hand's equity against the calling range. ICM comes from a value
curve V(my stack) that Hero precomputes once per hand (exact ICM is ~0.5 ms for eight seats, too
slow for the decision path); without it V is chip-proportional and the gate is plain chip EV.
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
DEFAULT_DEPTHS = tuple(range(1, 26))


@dataclass
class PushFoldParams:
    threshold_bb: float = 12.0  # effective stack at or below this: push or fold preflop
    tighten_per_player: float = 0.3  # the c in the multiway rule
    multiway_equity_penalty: float = 0.02  # per extra caller, off the equity vs the HU calling range
    reshove_raiser_call_prob: float = 0.6
    bb_flat_max_frac: float = 0.12  # BB closing the action may flat this share of stack with a decent hand
    bb_flat_min_rank: float = 0.5
    dial_min: float = 0.6
    dial_max: float = 2.0
    icm_epsilon: float = 1e-6
    call_equity_margin: float = 0.0  # off the equity when calling a shove (the solver's caller is exact; the field is not)
    push_equity_margin: float = 0.0  # off the equity when pushing
    cheap_push_frac_mult: float = 0.8  # Hero.cheap(): a bit tighter than the rule, no dials


# ---------------------------------------------------------------- offline solver

def removal_weights() -> list[list[int]]:
    """w[i][j] = combos of class j that share no card with a representative combo of class i."""
    reps = [class_combos(c)[0] for c in CLASSES]
    combos = [class_combos(c) for c in CLASSES]
    n = len(CLASSES)
    w = [[0] * n for _ in range(n)]
    for i in range(n):
        a, b = reps[i]
        row = w[i]
        for j in range(n):
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
            den += wij
            c = call[j]
            tot += wij * (c * S * (2.0 * ei[j] - 1.0) + (1.0 - c))
        out[i] = 1.0 if tot / den > -0.5 else 0.0
    return out


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


def _freq(rng: list[float]) -> float:
    return sum(COMBO_COUNT[i] * rng[i] for i in range(len(rng))) / TOTAL_COMBOS


def solve_hu_pushfold(matrix: list[list[float]], depths=DEFAULT_DEPTHS, iters: int = 40, damping: float = 0.5) -> dict:
    """Heads-up push/fold approximation per depth. Returns the JSON-able table described in the module doc."""
    w = removal_weights()
    out = {"classes": list(CLASSES), "depths": list(depths), "push": {}, "call": {}, "p_push": {}, "p_call": {},
           "eq_vs_call": {}, "eq_vs_push": {}}
    for S in depths:
        S = float(S)
        push = [1.0] * len(CLASSES)
        call = _caller_br(push, matrix, w, S)
        for _ in range(iters):
            call_br = _caller_br(push, matrix, w, S)
            call = [damping * a + (1 - damping) * b for a, b in zip(call, call_br)]
            push_br = _pusher_br(call, matrix, w, S)
            push = [damping * a + (1 - damping) * b for a, b in zip(push, push_br)]
        call = _caller_br(push, matrix, w, S)
        push = _pusher_br(call, matrix, w, S)
        key = str(int(S)) if S == int(S) else str(S)
        out["push"][key] = [int(x) for x in push]
        out["call"][key] = [int(x) for x in call]
        out["p_push"][key] = round(_freq(push), 4)
        out["p_call"][key] = round(_freq(call), 4)
        out["eq_vs_call"][key] = [round(x, 4) for x in _eq_vs_range(call, matrix, w)]
        out["eq_vs_push"][key] = [round(x, 4) for x in _eq_vs_range(push, matrix, w)]
    return out


def matrix_fingerprint(hu) -> str:
    """Cheap identity of a heads-up matrix, so a push/fold cache solved from an older matrix is detected."""
    import hashlib
    h = hashlib.sha1()
    for row in hu:
        h.update(("%.4f," * len(row) % tuple(row)).encode())
    return h.hexdigest()[:16]


def build_pushfold_tables(tables: Tables, tables_dir: str = TABLES_DIR, depths=DEFAULT_DEPTHS, write: bool = True) -> dict:
    """Solve from tables.hu and (optionally) write tables/pushfold_hu.json. For tools/gen_tables.py."""
    sol = solve_hu_pushfold(tables.hu, depths)
    sol["matrix_fp"] = matrix_fingerprint(tables.hu)
    if write:
        write_json("pushfold_hu.json", sol, tables_dir)
    return sol


def load_pushfold(tables: Tables, tables_dir: str = TABLES_DIR) -> dict:
    raw = read_json("pushfold_hu.json", tables_dir)
    if raw and raw.get("classes") == list(CLASSES) and raw.get("depths"):
        if raw.get("matrix_fp") == matrix_fingerprint(tables.hu):
            return raw
        # stale: solved from a different matrix (tables were regenerated for a variant). Re-solve.
    return build_pushfold_tables(tables, tables_dir, write=os.access(tables_dir, os.W_OK) if os.path.isdir(tables_dir) else False)


# ---------------------------------------------------------------- the engine

class _Linear:
    """Chip-proportional value curve: the fallback when no ICM curve is set."""
    __slots__ = ()

    def value(self, x: float) -> float:
        return x


class PushFold:
    def __init__(self, params: PushFoldParams, tables: Tables, solution: dict | None = None):
        self.p = params
        self.rank = tables.rank
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
        self.curve = _Linear()

    def _order_pct(self, sets: dict[int, list[int]]) -> dict[str, float]:
        """cls -> combo-weighted share of hands strictly ahead of it in (max depth, HU rank) order."""
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
            out[CLASSES[i]] = before / TOTAL_COMBOS
            before += COMBO_COUNT[i]
        return out

    def depth(self, eff_bb: float) -> int:
        d = int(eff_bb + 0.5)
        return self.min_depth if d < self.min_depth else self.max_depth if d > self.max_depth else d

    def applies(self, spot: Spot) -> bool:
        return spot.cls is not None and spot.eff_bb <= self.p.threshold_bb

    def _clamp(self, m: float) -> float:
        return self.p.dial_min if m < self.p.dial_min else self.p.dial_max if m > self.p.dial_max else m

    # ------------------------------------------------------------ decisions
    def act(self, spot: Spot, prof: Profiler | None, cheap: bool = False) -> Action:
        obs = spot.obs
        if spot.facing_shove:
            return self._call_shove(spot, prof, cheap)
        if spot.n_raises == 0:
            return self._push_or_fold(spot, prof, cheap)
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
        D = self.depth(spot.eff_bb)
        callers = self._callers(spot, prof)
        k = len(callers)
        free = _CHECK if ActionKind.CHECK in obs.legal else _FOLD
        if k == 0:
            # nobody live can call: any shove takes the pot (dead seats fold to a bet)
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else free
        f = self.p_push[D] / (1.0 + p.tighten_per_player * (k - 1))
        if cheap:
            f *= p.cheap_push_frac_mult
        elif prof is not None:
            m = 0.0
            for s in callers:
                m += prof.exploit_dials(s)["steal_mult"]
            f *= self._clamp(m / k)
        if self.push_pct[cls] >= f:
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
        e = self.eq_vs_call[D][CLASS_INDEX[cls]] - p.multiway_equity_penalty * (k - 1) - p.push_equity_margin
        if self._push_ev_ok(spot, pc_any, e):
            return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        return free

    def _push_ev_ok(self, spot: Spot, pc_any: float, e: float) -> bool:
        obs = spot.obs
        v = self.curve.value
        behind = obs.stacks[spot.me]
        pot = spot.pot_total
        risk = min(behind, spot.max_opp_total)
        v_fold = v(behind)
        v_steal = v(behind + pot)
        v_win = v(behind + pot + risk)
        v_lose = v(behind - risk)
        ev = pc_any * (e * v_win + (1.0 - e) * v_lose) + (1.0 - pc_any) * v_steal
        return ev > v_fold + self.p.icm_epsilon

    def _reshove(self, spot: Spot, prof: Profiler | None, cheap: bool) -> Action:
        """Facing a raise (not a shove) while short: shove over it, flat only in the big blind, else fold."""
        p = self.p
        obs = spot.obs
        cls = spot.cls
        D = self.depth(spot.eff_bb)
        callers = self._callers(spot, prof)
        k = len(callers)
        f = self.p_call[D] / (1.0 + p.tighten_per_player * max(0, k - 1))
        pc_raiser = p.reshove_raiser_call_prob
        if prof is not None and not cheap and spot.raiser >= 0:
            f *= self._clamp(prof.pfr_rate(spot.raiser) / Profiler.P_PFR)
            pc_raiser = min(0.95, pc_raiser * self._clamp(prof.call_vs_shove(spot.raiser) / Profiler.P_CALL_SHOVE))
        if cheap:
            f *= p.cheap_push_frac_mult
        if self.call_pct[cls] < f:
            e = self.eq_vs_call[D][CLASS_INDEX[cls]] - p.multiway_equity_penalty * max(0, k - 1) - p.push_equity_margin
            if self._push_ev_ok(spot, pc_raiser, e):
                return Action(ActionKind.RAISE, obs.max_raise) if ActionKind.RAISE in obs.legal else _CALL
        if spot.behind == 0 and spot.to_call <= p.bb_flat_max_frac * spot.my_total and self.rank[cls] >= p.bb_flat_min_rank:
            return _CALL
        return _CHECK if ActionKind.CHECK in obs.legal else _FOLD

    def _call_shove(self, spot: Spot, prof: Profiler | None, cheap: bool) -> Action:
        p = self.p
        obs = spot.obs
        cls = spot.cls
        shover = spot.shover
        shover_total = obs.stacks[shover] + obs.bets[shover] if shover >= 0 else spot.max_opp_total
        D = self.depth(min(spot.my_total, shover_total) / spot.bb)
        k_behind = 0
        for s in spot.opps:
            if obs.bets[s] < spot.cur_bet and obs.stacks[s] > 0:
                k_behind += 1
        f = self.p_call[D] / (1.0 + p.tighten_per_player * k_behind)
        if spot.n_in >= 2:
            f *= 0.5  # a shove and a call already: need a premium
        if prof is not None and not cheap and shover >= 0:
            f *= self._clamp(prof.exploit_dials(shover)["call_down_mult"])
            f *= self._clamp(prof.shove_rate(shover) / Profiler.P_SHOVE)
        if self.call_pct[cls] >= f:
            return _FOLD
        e = self.eq_vs_push[D][CLASS_INDEX[cls]] - p.multiway_equity_penalty * (k_behind + max(0, spot.n_in - 1)) \
            - p.call_equity_margin
        v = self.curve.value
        behind = obs.stacks[spot.me]
        v_fold = v(behind)
        v_win = v(behind + spot.pot_total)
        v_lose = v(behind - spot.to_call)
        if e * v_win + (1.0 - e) * v_lose > v_fold + p.icm_epsilon:
            return _CALL
        return _FOLD
