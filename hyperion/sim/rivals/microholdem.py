"""MicroAgent from the public repo ryankkhalil19/microholdem (MIT), played as a sparring opponent.

Unlike rival1, this is an adapter, not a drop-in. Nothing from that repository is copied here: their
package is imported at run time from a clone named by an environment variable. The adapter is disabled
when that variable is unset or the clone is incomplete. `available()` then says why, and constructing the
bot raises RuntimeError, so nothing that does not ask for it ever needs the clone. Measured in
docs/drills/public-repos-sparring.md: level with Hero, and the strongest public bot by 0.9 points.

Setup, from outside the clone, without running their setup.py:

    git clone --depth 1 https://github.com/ryankkhalil19/microholdem /path/mh
    pip install numpy pybind11                       # their package imports numpy
    c++ -O3 -shared -fPIC -std=c++17 $(python -m pybind11 --includes) \
        /path/mh/src/microholdem/_core.cpp -o /path/build/_core$(python3-config --extension-suffix)
    export HYPERION_MICROHOLDEM=/path/mh HYPERION_MICROHOLDEM_CORE=/path/build/_core<suffix>.so

HYPERION_MICROHOLDEM_CORE may be omitted if the extension was built in place under src/microholdem/.
Run with `python -B` to keep bytecode out of their tree. Register it where wanted, e.g.
`bestiary.REGISTRY["micro"] = MicroholdemBot` in a sweep script (the bestiary is left alone).

Their interface wants per-street history, per-hand contributions and payouts. Our Observation carries
none of those directly, so the adapter replays the hand from `obs.history` with our engine's no-limit
betting rules (no straddle). Seat stacks at hand start come from `hand_end` deltas. In the scratch
drill the replay matched our engine on every decision. A mismatch increments `replay_mismatches` and
the bot still acts. The engine times the adapter and MicroAgent together.
"""
from __future__ import annotations

import glob
import importlib.util
import os
import sys
from typing import Optional

from ...core.types import Action, ActionKind

ENV_REPO = "HYPERION_MICROHOLDEM"
ENV_CORE = "HYPERION_MICROHOLDEM_CORE"
_KIND = {"fold": 0, "check": 1, "call": 2, "raise": 3}
_MOD = None  # (engine module, MicroAgent class) once loaded
_WHY = ""


def _core_path(repo: str) -> Optional[str]:
    core = os.environ.get(ENV_CORE)
    if core:
        return core if os.path.isfile(core) else None
    hits = glob.glob(os.path.join(repo, "src", "microholdem", "_core*.so"))
    return hits[0] if hits else None


def _load():
    """Import their engine and agent once. Returns None (and sets _WHY) when disabled."""
    global _MOD, _WHY
    if _MOD is not None:
        return _MOD
    repo = os.environ.get(ENV_REPO, "")
    if not repo:
        _WHY = f"{ENV_REPO} is not set"
        return None
    src = os.path.join(repo, "src")
    if not os.path.isfile(os.path.join(src, "microholdem", "agent.py")):
        _WHY = f"{ENV_REPO}={repo!r} has no src/microholdem/agent.py"
        return None
    core = _core_path(repo)
    if core is None:
        _WHY = f"no compiled _core: set {ENV_CORE} or build it under src/microholdem/"
        return None
    try:
        if "microholdem._core" not in sys.modules:
            spec = importlib.util.spec_from_file_location("microholdem._core", core)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            sys.modules["microholdem._core"] = mod
        if src not in sys.path:
            sys.path.append(src)
        from microholdem import engine as E  # type: ignore[import-not-found]
        from microholdem.agent import MicroAgent  # type: ignore[import-not-found]
    except Exception as e:  # noqa: BLE001 - optional dependency; report, never crash an import
        _WHY = f"import failed: {e!r}"
        return None
    _MOD = (E, MicroAgent)
    return _MOD


def available() -> tuple[bool, str]:
    """(True, '') when the clone and extension load; otherwise (False, reason)."""
    ok = _load() is not None
    return ok, "" if ok else _WHY


def _after(s: int, n: int, alive: list) -> int:
    for _ in range(n):
        s = (s + 1) % n
        if alive[s]:
            return s
    return s


class MicroholdemBot:
    """Our Bot protocol around their MicroAgent (reset(seat, n_seats, seed), act(obs) -> Action)."""

    def __init__(self, seed: Optional[int] = None):
        mod = _load()
        if mod is None:
            raise RuntimeError(f"microholdem rival disabled: {_WHY}")
        self.E, cls = mod
        self.seed = (seed or 0) & 0x7FFFFFFF
        self.impl = cls(seed=self.seed)
        self.replay_mismatches = 0

    # ----- Bot protocol ---------------------------------------------------------------------------
    def new_table(self, rules, seat: int, n_players: int) -> None:
        self.rules, self.n = rules, n_players
        self.stacks = [rules.starting_stack] * n_players  # at the start of the next hand
        self.impl.reset(seat, n_players, self.seed)

    def hand_end(self, result) -> None:
        for i, d in enumerate(result.deltas):
            self.stacks[i] = max(0, self.stacks[i] + d)

    def act(self, obs) -> Action:
        hist, contrib_ok = self._replay(obs)
        if not contrib_ok:
            self.replay_mismatches += 1
        E = self.E
        can_raise = ActionKind.RAISE in obs.legal
        in_hand = tuple(obs.in_hand)
        alive = sum(1 for x in self.stacks if x > 0)
        mo = E.Observation(
            seat=obs.seat, hole=tuple(obs.hole), board=tuple(obs.board), street=obs.street,
            pot=obs.pot + sum(obs.bets), to_call=obs.to_call,
            min_raise_to=obs.min_raise if can_raise else 0, max_raise_to=obs.max_raise if can_raise else 0,
            can_raise=can_raise, stacks=tuple(obs.stacks), bets=tuple(obs.bets), in_hand=in_hand,
            button=obs.button, small_blind=obs.blinds[0], big_blind=obs.blinds[1],
            ante=self.rules.ante_at(obs.hand_no), n_in_hand=sum(in_hand), hand_number=obs.hand_no,
            history=hist, payouts=tuple(float(x) for x in self.rules.payouts[:alive]),
        )
        a = self.impl.act(mo)
        k = int(a.kind)
        if k == 0:
            return Action.fold()
        if k == 1:
            return Action.check()
        if k == 2:
            return Action.call()
        return Action.raise_to(int(a.amount))

    # ----- history replay -------------------------------------------------------------------------
    def _replay(self, obs) -> tuple[tuple, bool]:
        """Their history tuples (street, seat, kind, amount: chips for a call, raise-to for a raise) for
        this hand so far, and whether the replay landed exactly on this decision."""
        n, rules = self.n, self.rules
        stacks = self.stacks[:]
        alive = [x > 0 for x in stacks]
        in_hand = alive[:]
        bets = [0] * n
        b = obs.button
        if sum(alive) == 2:
            sb, bb = b, _after(b, n, alive)
        else:
            sb = _after(b, n, alive)
            bb = _after(sb, n, alive)
        ante = rules.ante_at(obs.hand_no)
        if ante:
            for s in range(n):
                if alive[s]:
                    stacks[s] -= min(ante, stacks[s])
        for seat, amt in ((sb, obs.blinds[0]), (bb, obs.blinds[1])):
            put = min(amt, stacks[seat])
            stacks[seat] -= put
            bets[seat] += put
        cur, last_inc = max(bets), obs.blinds[1]
        history, hi, out = obs.history, 0, []
        first = _after(bb, n, alive)
        for street in range(rules.streets):
            if street:
                bets = [0] * n
                cur, last_inc = 0, obs.blinds[1]
                first = _after(b, n, in_hand)
            chips = sum(1 for s in range(n) if in_hand[s] and stacks[s] > 0)
            owes = any(in_hand[s] and stacks[s] > 0 and bets[s] < cur for s in range(n))
            if not (chips >= 2 or (chips == 1 and owes)):
                if sum(in_hand) == 1:
                    break
                continue
            need = [in_hand[s] and stacks[s] > 0 for s in range(n)]
            pending, s = sum(need), first
            while pending:
                if need[s]:
                    need[s] = False
                    pending -= 1
                    owe = cur - bets[s]
                    responders = any(o != s and in_hand[o] and stacks[o] > 0 for o in range(n))
                    if owe > 0 or responders:
                        if hi >= len(history):
                            ok = s == obs.seat and street == obs.street and bets == list(obs.bets)
                            return tuple(out), ok
                        hs, a = history[hi]
                        hi += 1
                        if hs != s:
                            return tuple(out), False
                        k = a.kind.value
                        if k == "fold":
                            in_hand[s] = False
                            out.append((street, s, 0, 0))
                        elif k == "check":
                            out.append((street, s, 1, 0))
                        elif k == "call":
                            put = min(owe, stacks[s])
                            stacks[s] -= put
                            bets[s] += put
                            out.append((street, s, 2, put))
                        else:
                            total = a.amount
                            stacks[s] -= total - bets[s]
                            bets[s] = total
                            inc = total - cur
                            if inc >= last_inc:
                                last_inc = inc
                            cur = total
                            for o in range(n):
                                if o != s and in_hand[o] and stacks[o] > 0 and not need[o]:
                                    need[o] = True
                                    pending += 1
                            out.append((street, s, 3, total))
                s = (s + 1) % n
            if sum(in_hand) == 1:
                break
        return tuple(out), False
