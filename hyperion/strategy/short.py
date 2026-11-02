"""The short-handed specialist (S13): a composite member for tables with three or fewer players alive.

Close to unexploitable by default, so a counter-strategy bot finds no big leak, and played only where the composite's
`short_route` sends it (hyperion/compose/bot.py; off by default). It deviates by handing the decision back: while any
opponent still alive reads as a clear leak to F's profiler (dead or station by default), the composite
plays F's normal route there, F's reads and the exploit layer included.

**Preflop** is a lookup in tables solved offline by tools/solve_short.py (CFR+ on an abstracted tree, the module doc
there): heads-up by effective stack (5 to 100 bb, tables/short_hu.json, chip EV), three-handed by the three stacks at
ICM (tables/short_3.json). The hand's preflop history is mapped onto the tree's lines (f fold, c call, r the tree's raise,
j all-in; a raise between the tree's size and all-in maps to either by a log-scale split drawn once per hand); a line
the tree does not have (a limp-raise, a flat in a three-way pot) is not ours: `wants` says no and F plays. The tree's
raise sizes follow the actual bet: the 3-bet is 3.5 times the open, the 4-bet 2.2 times the 3-bet.

**Postflop, heads-up pots** (two in the hand, at most `post_alive` alive): one size per street (flop 0.5 pot, turn 0.66,
river 0.75) for value and bluffs alike, so a size names nothing. The hand's place in its range is read from Hero's
tier read (postflop.read: tier, draw outs) as a percentile of random holdings on this kind of board, ordered inside a
tier by kicker and outs, and moved up by what the range has already shown (each bet we called keeps the top
minimum-defence share). Facing a bet of b into a pot P we continue with the top P / (P + b) of the range (minimum
defence), raise the top part of that with value and strong draws, and add a few bluff raises from the folding part;
with nothing to call the aggressor bets its top share and draws or bottom air in a ratio that the size makes
balanced; the defender stabs a little less when checked to.

Every random choice is drawn from a hash of (seed, hand, street, hole cards), so a decision replays exactly and a
hand's mix is stable across calls. The member keeps no state that depends on its own answers (it reads the hand from
the observation's history), so its light shadow (light_observe) only records the hand's starting chips.
"""
from __future__ import annotations

import json
import math
import os
from zlib import crc32

from ..core.cards import hole_class
from ..core.types import Action, ActionKind, Observation
from .tables import CLASS_INDEX, TABLES_DIR

_FOLD = Action(ActionKind.FOLD)
_CHECK = Action(ActionKind.CHECK)
_CALL = Action(ActionKind.CALL)
_RAISE = ActionKind.RAISE
_CALLK = ActionKind.CALL
_CHECKK = ActionKind.CHECK
_FOLDK = ActionKind.FOLD

# random holdings' tier shares (postflop.read) by street (flop, turn, river) and wet board: 120,000 samples each
TIER_P = {
    (1, 0): (0.4422, 0.159, 0.2061, 0.0981, 0.0517, 0.0346, 0.0063, 0.0017, 0.0003),
    (1, 1): (0.2084, 0.2409, 0.1995, 0.1865, 0.1075, 0.0215, 0.0254, 0.0103, 0.0001),
    (2, 0): (0.3023, 0.2104, 0.2406, 0.1141, 0.0547, 0.0559, 0.0066, 0.0141, 0.0013),
    (2, 1): (0.1576, 0.1851, 0.24, 0.1811, 0.1486, 0.033, 0.0325, 0.0218, 0.0003),
    (3, 0): (0.3188, 0.2243, 0.2455, 0.0439, 0.0463, 0.0547, 0.0038, 0.0574, 0.0052),
    (3, 1): (0.3034, 0.1041, 0.3184, 0.046, 0.096, 0.0408, 0.0383, 0.0517, 0.0013),
}
TIER_CDF = {k: tuple(sum(v[:i]) for i in range(10)) for k, v in TIER_P.items()}

_TABLES: dict = {}


def _load(kind: str):
    """tables/short_<kind>.json, decoded once per process (None when missing)."""
    if kind in _TABLES:
        return _TABLES[kind]
    path = os.path.join(TABLES_DIR, f"short_{kind}.json")
    t = None
    try:
        with open(path) as fh:
            raw = json.load(fh)
        t = {"q": raw["q"], "keys": sorted(float(k) for k in raw["solve"]), "solve": {}}
        for k, v in raw["solve"].items():
            t["solve"][float(k)] = {"meta": v["meta"], "nodes": v["nodes"]}
        if kind == "3":
            t["grid"] = raw["grid"]
            t["rho"] = raw.get("rho", [0.4])
    except (OSError, ValueError, KeyError):
        t = None
    _TABLES[kind] = t
    return t


def _u(*parts) -> float:
    """A uniform draw in [0, 1) from a hash of the parts (replays exactly)."""
    return (crc32(repr(parts).encode()) & 0xFFFFFF) / 16777216.0


class ShortParams:
    """Dials (the composite's `short.<name>` keys)."""

    def __init__(self, **kw):
        self.defer = "dead,station"  # opponent archetypes that hand the decision back to F (maniac and random fire on
        #                              both exploiters short-handed: not clear leaks there)
        self.post = True  # play heads-up pots postflop
        self.post_alive = 2  # ... only with at most this many alive
        self.three = True  # play three-handed preflop (tables/short_3.json)
        self.flop_size = 0.5
        self.turn_size = 0.66
        self.river_size = 0.75
        self.raise_mult = 3.0  # a raise of a bet: to this times the bet
        self.value_raise = (0.30, 0.25, 0.20)  # the share of the defending range that raises for value, by street
        self.bluff_raise = (0.5, 0.35, 0.15)  # bluff raises as a share of the value raises, by street
        self.bet_value = {"agg_ip": (0.42, 0.40, 0.36), "agg_oop": (0.34, 0.38, 0.34),
                          "stab": (0.36, 0.34, 0.30), "lead": (0.0, 0.0, 0.0)}
        self.bet_bluff = {"agg_ip": (0.26, 0.20, 0.15), "agg_oop": (0.18, 0.16, 0.13),
                          "stab": (0.22, 0.16, 0.12), "lead": (0.0, 0.0, 0.0)}
        self.mdf_slack = 0.0  # defend this much less than minimum defence (0 = exactly MDF)
        for k, v in kw.items():
            if not hasattr(self, k):
                raise KeyError(f"unknown short dial {k!r}")
            setattr(self, k, v)


class ShortMember:
    """The composite member (module doc)."""

    plain_only = True  # permuted ranks, straddles: the base plays
    holdem_only = True  # any twist: the base plays

    def __init__(self, params: ShortParams | None = None, seed: int | None = None):
        self.p = params or ShortParams()
        self.seed = 0 if seed is None else int(seed)
        self.defer = frozenset(x.strip() for x in str(self.p.defer).split(",") if x.strip())
        self.hu = _load("hu")
        self.t3 = _load("3") if self.p.three else None
        self.payouts = (1.0, 0.0)
        self.rho = 0.4
        self.n = 0
        self.seat = 0
        self._hand = -1
        self._start: list = []
        self.counts: dict = {}

    # ------------------------------------------------------------------ member protocol
    def new_table(self, rules, seat: int, n_players: int) -> None:
        self.n = n_players
        self.seat = seat
        pay = tuple(rules.payouts) if rules.payouts else ()
        if len(pay) >= 3 and pay[0] > pay[2]:
            self.rho = (pay[1] - pay[2]) / (pay[0] - pay[2])
        self._hand = -1

    def hand_end(self, result) -> None:
        pass

    def light_observe(self, obs: Observation) -> None:
        if obs.hand_no != self._hand:
            self._hand = obs.hand_no
            if obs.street == 0:
                n_alive = sum(1 for s, b in zip(obs.stacks, obs.bets) if s + b > 0) or 1
                ante = obs.pot / n_alive if obs.pot else 0.0
                self._start = [s + b + (ante if s + b > 0 else 0.0) for s, b in zip(obs.stacks, obs.bets)]
            else:
                self._start = []

    def act(self, obs: Observation) -> Action:
        self.light_observe(obs)
        if obs.street == 0:
            a = self._preflop(obs)
        else:
            a = self._postflop(obs)
        if a is None:
            raise ValueError("short: not a spot of ours")  # the composite plays the base's answer
        return a

    # ------------------------------------------------------------------ routing
    def wants(self, obs: Observation, prof) -> bool:
        """This decision is ours: the hand maps onto our tables / heads-up postflop, and no opponent alive reads as a
        clear leak (module doc)."""
        self.light_observe(obs)
        stacks, bets, in_hand = obs.stacks, obs.bets, obs.in_hand
        alive = [j for j in range(len(stacks)) if stacks[j] + bets[j] > 0 or in_hand[j]]
        if prof is not None and self.defer:
            for j in alive:
                if j != obs.seat:
                    try:
                        if prof.archetype(j) in self.defer:
                            return False
                    except Exception:  # noqa: BLE001
                        return False
        if obs.street == 0:
            if len(alive) == 2:
                return self._hu_node(obs) is not None
            if len(alive) == 3 and self.t3 is not None:
                return self._three_node(obs) is not None
            return False
        if not self.p.post or len(alive) > self.p.post_alive:
            return False
        if sum(1 for x in in_hand if x) != 2 or len(obs.hole) != 2:
            return False
        return bool(self._start) and self._replay(obs) is not None

    # ------------------------------------------------------------------ preflop: heads-up
    def _depth(self, table, S: float, hand_no: int, salt: str) -> float:
        keys = table["keys"]
        if S <= keys[0]:
            return keys[0]
        if S >= keys[-1]:
            return keys[-1]
        for i in range(1, len(keys)):
            if keys[i] >= S:
                lo, hi = keys[i - 1], keys[i]
                w = (math.log(S) - math.log(lo)) / (math.log(hi) - math.log(lo))
                return hi if _u(self.seed, hand_no, salt) < w else lo
        return keys[-1]

    def _map_raise(self, acts: str, amount: float, r_to: float, jam_to: float, hand_no: int, k: int) -> str:
        has_r, has_j = "r" in acts, "j" in acts
        if amount >= jam_to - 1e-9:
            return "j" if has_j else ("r" if has_r else "")
        if has_j and not has_r and amount < 0.45 * jam_to:
            return ""  # a small raise where the tree only jams: not a line of ours
        if has_r and has_j:
            if amount <= r_to:
                return "r"
            w = (math.log(jam_to) - math.log(amount)) / (math.log(jam_to) - math.log(r_to))
            return "r" if _u(self.seed, hand_no, "map", k) < w else "j"
        return "r" if has_r else ("j" if has_j else "")

    def _hu_node(self, obs: Observation):
        """(depth solve, node key, node, my role, eff chips) for a heads-up preflop decision, or None."""
        t = self.hu
        if t is None or not self._start:
            return None
        n = len(obs.stacks)
        alive = [j for j in range(n) if self._start[j] > 0]
        if len(alive) != 2:
            return None
        sb = obs.button
        if sb not in alive:
            return None
        bbs = alive[0] if alive[1] == sb else alive[1]
        bb = obs.blinds[1] or 1
        eff = min(self._start[sb], self._start[bbs])
        S = eff / bb
        d = self._depth(t, S, obs.hand_no, "d2")
        sol = t["solve"][d]
        nodes = sol["nodes"]
        role = {sb: 0, bbs: 1}
        key = ""
        cur = float(obs.blinds[1])  # the bet to match
        k = 0
        for seat, a in obs.history:
            node = nodes.get(key)
            if node is None or role.get(seat) != node["p"]:
                return None
            acts = node["a"]
            kind = a.kind
            if kind is _FOLDK:
                return None
            if kind is _CALLK or kind is _CHECKK:
                ch = "c"
            else:
                r_to = self._raise_to(key, sol["meta"], cur, bb) if "r" in acts else cur * 3
                ch = self._map_raise(acts, float(a.amount), r_to, float(eff), obs.hand_no, k)
                cur = float(a.amount)
            if not ch or ch not in acts:
                return None
            k += 1
            nxt = "l" if (key == "" and ch == "c") else key + ch
            if ch == "c" and key != "":
                return None  # a call that closes preflop: no decision of ours follows
            key = nxt
        node = nodes.get(key)
        if node is None or role.get(obs.seat) != node["p"]:
            return None
        return sol, key, node, role[obs.seat], eff

    @staticmethod
    def _raise_to(key: str, meta: dict, cur: float, bb: float) -> float:
        """The tree's raise at this node, in chips, sized from the actual bet faced."""
        if key == "":
            return meta["r1"] * bb
        if key == "l":
            return meta["iso"] * bb
        if key in ("r", "b", "o"):
            return 3.5 * cur
        return 2.2 * cur  # 4-bets (and the three-handed tree's re-raises)

    def _pick(self, node, cls: int, obs: Observation, q: int, salt: str) -> str:
        acts = node["a"]
        na = len(acts)
        s = node["s"]
        u = _u(self.seed, obs.hand_no, salt, obs.hole) * q
        acc = 0
        for x in range(na):
            acc += ord(s[cls * na + x]) - 48
            if u < acc:
                return acts[x]
        return acts[-1]

    def _to_action(self, ch: str, key: str, meta: dict, obs: Observation, eff: float) -> Action:
        legal = obs.legal
        if ch == "f":
            return _CHECK if obs.to_call == 0 and _CHECKK in legal else _FOLD
        if ch == "c":
            if obs.to_call == 0:
                return _CHECK
            return _CALL if _CALLK in legal else _FOLD
        if _RAISE not in legal:
            return _CALL if _CALLK in legal else _CHECK
        bb = obs.blinds[1] or 1
        if ch == "j":
            return Action(_RAISE, obs.max_raise)
        cur = float(max(obs.bets))
        amt = self._raise_to(key, meta, cur, bb)
        if amt > 0.4 * eff:
            return Action(_RAISE, obs.max_raise)
        amt = int(round(amt))
        amt = max(obs.min_raise, min(obs.max_raise, amt))
        return Action(_RAISE, amt)

    def _preflop(self, obs: Observation):
        alive = sum(1 for s, b, h in zip(obs.stacks, obs.bets, obs.in_hand) if s + b > 0 or h)
        if alive == 2:
            got = self._hu_node(obs)
            if got is None:
                return None
            sol, key, node, role, eff = got
            cls = CLASS_INDEX.get(hole_class(obs.hole))
            if cls is None:
                return None
            ch = self._pick(node, cls, obs, self.hu["q"], "pre" + key)
            self.counts["hu:" + key + ch] = self.counts.get("hu:" + key + ch, 0) + 1
            return self._to_action(ch, key, sol["meta"], obs, eff)
        if alive == 3 and self.t3 is not None:
            got = self._three_node(obs)
            if got is None:
                return None
            sol, key, node, role, eff = got
            cls = CLASS_INDEX.get(hole_class(obs.hole))
            if cls is None:
                return None
            ch = self._pick(node, cls, obs, self.t3["q"], "p3" + key)
            self.counts["3:" + key + ch] = self.counts.get("3:" + key + ch, 0) + 1
            return self._to_action3(ch, key, sol["meta"], obs, eff)
        return None

    # ------------------------------------------------------------------ preflop: three-handed
    def _three_node(self, obs: Observation):
        t = self.t3
        if t is None or not self._start:
            return None
        n = len(obs.stacks)
        alive = [j for j in range(n) if self._start[j] > 0]
        if len(alive) != 3:
            return None
        btn = obs.button
        if btn not in alive:
            return None
        i = alive.index(btn)
        sb, bbs = alive[(i + 1) % 3], alive[(i + 2) % 3]
        bb = obs.blinds[1] or 1
        st = [self._start[btn] / bb, self._start[sb] / bb, self._start[bbs] / bb]
        grid = t["grid"]
        cfg = []
        for x in st:
            cfg.append(self._grid_pick(grid, x, obs.hand_no, len(cfg)))
        key3 = "%g,%g,%g" % tuple(cfg)
        sol = t["solve"].get(key3)
        if sol is None:
            return None
        nodes = sol["nodes"]
        role = {btn: 0, sb: 1, bbs: 2}
        key = ""
        cur = float(obs.blinds[1])
        k = 0
        for seat, a in obs.history:
            node = nodes.get(key)
            if node is None or role.get(seat) != node["p"]:
                return None
            acts = node["a"]
            kind = a.kind
            if kind is _FOLDK:
                ch = "f"
            elif kind is _CALLK or kind is _CHECKK:
                ch = "c"
            else:
                jam_to = self._start[seat]
                r_to = self._raise_to3(key, sol["meta"], cur, bb) if "r" in acts else cur * 3
                ch = self._map_raise(acts, float(a.amount), r_to, float(jam_to), obs.hand_no, k)
                cur = float(a.amount)
            if not ch or ch not in acts:
                return None
            k += 1
            key = key + ch
        node = nodes.get(key)
        if node is None or role.get(obs.seat) != node["p"]:
            return None
        me = obs.seat
        others = [self._start[j] for j in alive if j != me]
        eff = min(self._start[me], max(others))
        return sol, key, node, role[me], eff

    def _grid_pick(self, grid, x: float, hand_no: int, salt) -> float:
        if x <= grid[0]:
            return grid[0]
        if x >= grid[-1]:
            return grid[-1]
        for i in range(1, len(grid)):
            if grid[i] >= x:
                lo, hi = grid[i - 1], grid[i]
                w = (math.log(x) - math.log(lo)) / (math.log(hi) - math.log(lo))
                return hi if _u(self.seed, hand_no, "g3", salt) < w else lo
        return grid[-1]

    @staticmethod
    def _raise_to3(key: str, meta: dict, cur: float, bb: float) -> float:
        """The three-handed tree's raise: the open (button, or the small blind after the button folds), the raise
        over a limp, then 3.5 times the open and 2.2 times a 3-bet."""
        n_raises = key.count("r") + key.count("j")
        if n_raises == 0:
            return (meta["iso"] if key.endswith("c") else meta["r1"]) * bb
        return (3.5 if n_raises == 1 else 2.2) * cur

    def _to_action3(self, ch: str, key: str, meta: dict, obs: Observation, eff: float) -> Action:
        legal = obs.legal
        if ch in ("f", "c", "j"):
            return self._to_action(ch, key, meta, obs, eff)
        if _RAISE not in legal:
            return _CALL if _CALLK in legal else _CHECK
        bb = obs.blinds[1] or 1
        cur = float(max(obs.bets))
        amt = self._raise_to3(key, meta, cur, bb)
        if amt > 0.4 * eff:
            return Action(_RAISE, obs.max_raise)
        amt = int(round(amt))
        return Action(_RAISE, max(obs.min_raise, min(obs.max_raise, amt)))

    # ------------------------------------------------------------------ postflop
    def _replay(self, obs: Observation):
        """Split the hand's history into streets (a heads-up pot at the end). Returns a dict with the preflop
        aggressor, each street's actions as (seat, kind, to, pot_before, bet_before) and per street the last
        aggressor, or None when the history does not replay."""
        start = self._start
        n = len(obs.stacks)
        if len(start) != n:
            return None
        bb_amt = obs.blinds[1] or 1
        alive = [j for j in range(n) if start[j] > 0]
        if len(alive) < 2:
            return None
        btn = obs.button
        if len(alive) == 2:
            sb = btn
            bbs = alive[0] if alive[1] == btn else alive[1]
        else:
            if btn not in alive:
                return None
            i = alive.index(btn)
            sb, bbs = alive[(i + 1) % len(alive)], alive[(i + 2) % len(alive)]
        chips = list(start)
        bets = [0.0] * n
        inh = [start[j] > 0 for j in range(n)]
        for seat, amt in ((sb, obs.blinds[0]), (bbs, obs.blinds[1])):
            put = min(float(amt), chips[seat])
            chips[seat] -= put
            bets[seat] += put
        cur = float(max(bets))
        pot = 0.0
        need = {j for j in range(n) if inh[j] and chips[j] > 0}
        street = 0
        streets = [[]]
        aggr = [-1]
        for seat, a in obs.history:
            if street > 3:
                return None
            if seat not in need and not (inh[seat] and chips[seat] > 0):
                return None
            kind = a.kind
            pb = pot + sum(bets)
            if kind is _FOLDK:
                inh[seat] = False
                need.discard(seat)
                streets[street].append((seat, "f", 0.0, pb, cur))
            elif kind is _CHECKK:
                need.discard(seat)
                streets[street].append((seat, "k", bets[seat], pb, cur))
            elif kind is _CALLK:
                put = min(cur - bets[seat], chips[seat])
                chips[seat] -= put
                bets[seat] += put
                need.discard(seat)
                streets[street].append((seat, "c", bets[seat], pb, cur))
            else:
                to = float(a.amount)
                put = min(to - bets[seat], chips[seat])
                chips[seat] -= put
                bets[seat] += put
                streets[street].append((seat, "r", bets[seat], pb, cur))
                if bets[seat] > cur:
                    cur = bets[seat]
                    aggr[street] = seat
                    need = {j for j in range(n) if inh[j] and chips[j] > 0 and j != seat}
                else:
                    need.discard(seat)
            live = [j for j in range(n) if inh[j]]
            if len(live) <= 1:
                return None
            if not need:  # the street closes
                pot += sum(bets)
                bets = [0.0] * n
                cur = 0.0
                street += 1
                streets.append([])
                aggr.append(-1)
                need = {j for j in range(n) if inh[j] and chips[j] > 0}
                if len(need) < 2:
                    return None
        if street != obs.street:
            return None
        return {"streets": streets, "aggr": aggr, "btn": btn}

    def _strength(self, obs: Observation):
        from .postflop import Postflop

        tier, outs, wet = Postflop.read(obs.hole, obs.board)
        st = min(obs.street, 3)
        key = (st, 1 if wet else 0)
        cdf, pr = TIER_CDF[key], TIER_P[key]
        r1, r2 = obs.hole[0] >> 2, obs.hole[1] >> 2
        hi, lo = (r1, r2) if r1 >= r2 else (r2, r1)
        if tier <= 1:
            sub = (hi * 13 + lo) / 169.0 * 0.6 + min(outs, 12) / 12.0 * 0.4
        elif tier <= 5:
            sub = 0.5 * hi / 12.0 + 0.3 * lo / 12.0 + 0.2 * min(outs, 9) / 9.0
        else:
            sub = 0.6 * hi / 12.0 + 0.4 * lo / 12.0
        sub = min(sub, 0.999)
        p = cdf[tier] + sub * pr[tier]
        return p, tier, outs

    def _postflop(self, obs: Observation):
        rp = self._replay(obs)
        if rp is None:
            return None
        p = self.p
        me = obs.seat
        st = min(obs.street, 3)
        si = st - 1
        streets, aggr = rp["streets"], rp["aggr"]
        opp = next((j for j in range(len(obs.in_hand)) if obs.in_hand[j] and j != me), -1)
        if opp < 0:
            return None
        # position: the player first to act postflop is the first in the hand after the button
        n = len(obs.stacks)
        first = None
        for d in range(1, n + 1):
            j = (rp["btn"] + d) % n
            if obs.in_hand[j]:
                first = j
                break
        ip = first != me
        # the range so far: each bet we called on an earlier street keeps the top MDF share
        floor = 0.0
        for s in range(1, st):
            mine = 0.0
            for (seat, k, to, pb, cur) in streets[s]:
                if seat != me:
                    continue
                if k == "c" and pb > 0:
                    call = cur - mine
                    m = (pb - call) / pb  # the pot before the bet over the pot with it: minimum defence
                    floor = floor + (1.0 - floor) * (1.0 - m)
                mine = to
        floor = min(floor, 0.85)
        pct, tier, outs = self._strength(obs)
        q = (pct - floor) / (1.0 - floor)
        q = 0.0 if q < 0.0 else 1.0 if q > 1.0 else q
        u = _u(self.seed, obs.hand_no, obs.street, obs.hole, len(obs.history))
        legal = obs.legal
        total = obs.pot + sum(obs.bets)
        to_call = obs.to_call
        my_behind = obs.stacks[me]
        opp_behind = obs.stacks[opp]
        if to_call > 0:
            # facing a bet (or a raise of ours)
            m = (total - to_call) / total if total > 0 else 1.0
            m = max(0.0, m - p.mdf_slack)
            n_raises = sum(1 for (seat, k, to, pb, cur) in streets[st] if k == "r")
            defend = q >= 1.0 - m
            vr = p.value_raise[si]
            value_raise = q >= 1.0 - m * vr
            can_raise = _RAISE in legal and opp_behind > 0 and n_raises <= 2
            if can_raise:
                if value_raise and (n_raises <= 1 or q >= 0.93):
                    return self._raise(obs, total, to_call)
                if n_raises <= 1 and st < 3 and outs >= 8 and u < p.bluff_raise[si]:
                    return self._raise(obs, total, to_call)
                if n_raises <= 1 and not defend:
                    # a few bluff raises from the folding part: bluffs = ratio x value raises
                    fold_share = 1.0 - m
                    want = p.bluff_raise[si] * m * vr * 0.5
                    if fold_share > 0 and u < want / fold_share and q > 0.15:
                        return self._raise(obs, total, to_call)
            if defend:
                return _CALL if _CALLK in legal else _FOLD
            return _FOLD
        # nothing to call: bet or check
        prev = aggr[st - 1] if st - 1 < len(aggr) else -1
        if prev == me:
            role = "agg_ip" if ip else "agg_oop"
        elif ip:
            role = "stab"
        else:
            role = "lead"
        v = p.bet_value[role][si]
        bl = p.bet_bluff[role][si]
        if _RAISE not in legal or opp_behind <= 0:
            return _CHECK
        if q >= 1.0 - v:
            return self._bet(obs, total, st)
        if bl > 0 and q < 1.0 - v:
            # bluffs: strong draws first, then the bottom of the range
            if st < 3 and outs >= 8:
                return self._bet(obs, total, st)
            draw_share = 0.08 if st == 1 else 0.05 if st == 2 else 0.0
            rest = max(0.0, bl - draw_share)
            bottom = 0.45
            if q < bottom and u < rest / bottom:
                return self._bet(obs, total, st)
        return _CHECK

    def _bet(self, obs: Observation, total: float, st: int) -> Action:
        p = self.p
        frac = p.flop_size if st == 1 else p.turn_size if st == 2 else p.river_size
        amt = obs.bets[obs.seat] + frac * total
        behind = obs.stacks[obs.seat]
        if amt - obs.bets[obs.seat] >= 0.6 * behind:
            amt = obs.max_raise
        amt = int(round(amt))
        return Action(_RAISE, max(obs.min_raise, min(obs.max_raise, amt)))

    def _raise(self, obs: Observation, total: float, to_call: float) -> Action:
        cur = max(obs.bets)
        amt = self.p.raise_mult * cur
        mine = obs.bets[obs.seat]
        behind = obs.stacks[obs.seat]
        if amt - mine >= 0.5 * behind:
            amt = obs.max_raise
        amt = int(round(amt))
        return Action(_RAISE, max(obs.min_raise, min(obs.max_raise, amt)))


def short_member(cfg, seed):
    """hyperion.compose.bot's factory: the member with the composite's `short_params` dials."""
    return ShortMember(ShortParams(**dict(getattr(cfg, "short_params", {}) or {})), seed)
