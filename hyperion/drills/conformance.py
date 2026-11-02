"""Observation conformance: the invariants every adapter's `to_observation` must satisfy, checked on
the night without editing adapter.py.

    HYPERION_CHECK=1 python -m hyperion.drills.fakekits.kit_b.runner submission.py
    python -m hyperion.drills.conformance          # demo: reference adapters clean, a buggy one caught

`check_observation(obs, rules)` returns human-readable violations, one per broken rule, prefixed by a
short rule name (`raise_total: ...`). `checked(adapter)` wraps one Adapter *instance* so every `decide`
call checks the Observation it produced (and, for a kit with no or a partial log, the history the inference rebuilt
for the bot) and records violations (count and the first five examples per
rule) in `adapter.conformance`; it also counts translation errors, which `Adapter.decide` otherwise
turns silently into the kit's check/fold, and the action kinds sent back, which is the "folds, calls
and raises at least once" check. `maybe_checked(adapter)` does that only when `HYPERION_CHECK=1` and
prints the report to stderr at exit, so an entry point can call it unconditionally and the shipped
bot is unchanged (the variable is not set in the sandbox).

The checks cost tens of microseconds per decision and allocate: a drill tool, never a submission path.
"""
from __future__ import annotations

import atexit
import os
import sys
from collections import Counter
from typing import Any

from hyperion.core.types import Action, ActionKind, Observation, Rules

CHECK, CALL, RAISE = ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
EXAMPLES_PER_RULE = 5


def check_observation(obs: Observation, rules: Rules | None = None) -> list[str]:
    """Invariants of a single Observation. Empty list = clean. Never raises on a malformed obs."""
    try:
        return _check(obs, rules or Rules())
    except Exception as e:  # noqa: BLE001 - a field of the wrong type is itself the finding
        return [f"malformed: {type(e).__name__}: {e}"]


def _check(obs: Observation, rules: Rules) -> list[str]:
    v: list[str] = []
    n = len(obs.stacks)
    if n == 0:
        return ["seats: stacks is empty"]
    seat, button = obs.seat, obs.button
    # cards: hole count, board count per street, encoding range, duplicates
    want = rules.hole_cards
    ex = rules.extras or {}
    if "discard_street" in ex and obs.street >= int(ex["discard_street"]):
        want = int(ex.get("keep", want - 1))  # toss or hold'em: the discard leaves `keep` cards
    if len(obs.hole) != want:
        v.append(f"hole_len: {len(obs.hole)} hole cards, rules say {want} on street {obs.street}")
    streets = len(rules.board_sizes)
    if not 0 <= obs.street < streets:
        v.append(f"street_range: street {obs.street} outside 0..{streets - 1} (board count passed as the index?)")
    elif len(obs.board) != rules.board_sizes[obs.street]:
        v.append(f"board_len: {len(obs.board)} board cards on street {obs.street}, rules say "
                 f"{rules.board_sizes[obs.street]}")
    cards = tuple(obs.hole) + tuple(obs.board)
    bad = [c for c in cards if type(c) is not int or not 0 <= c < rules.deck_size]
    if bad:
        v.append(f"card_range: {bad} outside 0..{rules.deck_size - 1} (rank*4+suit, 2=0 ... A=12, cdhs=0..3)")
    if len(set(cards)) != len(cards):
        v.append(f"card_dup: duplicate card in hole+board {cards} (displayed and canonical mixed?)")
    # seats
    one = " (seats numbered from 1? subtract 1: TODO 6)"
    if not 0 <= seat < n:
        v.append(f"seat_range: seat {seat} outside 0..{n - 1}{one if seat == n else ''}")
    if not 0 <= button < n:
        v.append(f"button_range: button {button} outside 0..{n - 1}{one if button == n else ''}")
    if len(obs.bets) != n or len(obs.in_hand) != n:
        v.append(f"lengths: stacks {n}, bets {len(obs.bets)}, in_hand {len(obs.in_hand)} differ")
        return v  # per-seat checks below would index out of range
    if any(s < 0 for s in obs.stacks):
        v.append(f"stacks_nonneg: negative stack in {obs.stacks}")
    if any(b < 0 for b in obs.bets):
        v.append(f"bets_nonneg: negative bet in {obs.bets}")
    me_ok = 0 <= seat < n
    if me_ok and not obs.in_hand[seat]:
        v.append(f"in_hand_self: in_hand[{seat}] is False while we are asked to act")
    # chips
    if obs.pot < 0:
        v.append(f"pot_nonneg: pot {obs.pot} < 0 (subtracting this street's bets from a pot that excludes them?)")
    if obs.to_call < 0:
        v.append(f"to_call_nonneg: to_call {obs.to_call} < 0")
    my_stack = obs.stacks[seat] if me_ok else 0
    my_bet = obs.bets[seat] if me_ok else 0
    cur = max(obs.bets)
    if me_ok:
        expect = max(0, min(cur - my_bet, my_stack))
        if obs.to_call != expect:
            v.append(f"to_call_bets: to_call {obs.to_call}, but max(bets) {cur} - my bet {my_bet} capped by my stack "
                     f"{my_stack} is {expect}")
    # legal set
    legal = obs.legal
    if not legal:
        v.append("legal_empty: no legal action")
    foreign = [k for k in legal if not isinstance(k, ActionKind)]
    if foreign:
        v.append(f"legal_kinds: {foreign} are not ActionKind (use make_observation / KIND_BY_NAME)")
    if obs.to_call > 0:
        if CHECK in legal:
            v.append(f"check_vs_call: to_call {obs.to_call} > 0 but CHECK is legal")
        if CALL not in legal and my_stack > 0:
            v.append(f"check_vs_call: to_call {obs.to_call} > 0 but CALL is not legal")
    else:
        if CALL in legal:
            v.append("check_vs_call: to_call is 0 but CALL is legal (to_call read from the wrong seat?)")
        if legal and CHECK not in legal:
            v.append("check_vs_call: to_call is 0 but CHECK is not legal")
    if RAISE in legal:
        if obs.min_raise > obs.max_raise:
            v.append(f"raise_bounds: min_raise {obs.min_raise} > max_raise {obs.max_raise}")
        if obs.max_raise > my_stack + my_bet:
            v.append(f"raise_max_stack: max_raise {obs.max_raise} > my stack {my_stack} + my bet {my_bet} "
                     f"(raise-to totals are capped by what I can put in)")
        if obs.min_raise <= cur:
            v.append(f"raise_total: min_raise {obs.min_raise} is not above the current highest bet {cur}: raise-to "
                     f"totals expected (increment passed as a total?)")
    # blinds, hand number, history
    sb, bb = obs.blinds
    if sb <= 0 or bb <= 0:
        v.append(f"blinds_positive: blinds {obs.blinds} must both be positive")
    elif sb > bb:
        v.append(f"blinds_order: small blind {sb} > big blind {bb} (swapped?)")
    if obs.hand_no < 0:
        v.append(f"hand_no: {obs.hand_no} < 0")
    for item in obs.history:
        s, a = item
        if not 0 <= s < n:
            v.append(f"history_seat: seat {s} in history outside 0..{n - 1}{one if s == n else ''}")
            return v
        if not isinstance(a, Action):
            v.append(f"history_action: {a!r} in history is not an Action")
            return v
    if obs.history:
        a0 = obs.history[0][1]
        if a0.kind is RAISE and bb > 0 and (a0.amount < bb or (a0.amount == bb and obs.street == 0)):
            v.append(f"history_blind: the history starts with a RAISE to {a0.amount}, the big blind or less: the forced "
                     f"bets logged as raises? Skip blind posts and antes (TODO 7b; make_observation drops them)")
    v += _check_raise_in_history(obs, rules)
    return v


def _check_raise_in_history(obs: Observation, rules: Rules) -> list[str]:
    """A bet above the street's base (the big blind, or the straddle, preflop; nothing after) means somebody
    raised: the history must hold a RAISE to that total. Hero reads who raised from history (drill 6: an empty
    one cost 2.5 points a table)."""
    bb = obs.blinds[1]
    base = bb * max(1, int(rules.straddle or 0)) if obs.street == 0 else 0
    top = max(obs.bets)
    if top <= base:
        return []
    raises = [a.amount for _, a in obs.history if a.kind is RAISE]
    fix = ("pass the kit's action log as history= to make_observation, or, when the kit has none, leave history "
           "out so make_observation rebuilds this street's raises from the bets (TODO 7b)")
    if not raises:
        return [f"history_raise: a bet of {top} is above the street's base {base} but obs.history holds no RAISE; "
                f"Hero reads raises from history (an empty one cost 2.5 points a table in drill 6): {fix}"]
    if top not in raises:
        return [f"history_raise: the top bet is {top} but no RAISE in obs.history reaches it (raises {raises[-3:]}); "
                f"history amounts must be raise-to totals: {fix}"]
    return []


class ConformanceReport:
    """Counts per rule with the first few examples, plus the cross-call checks a single obs cannot make:
    the table's chip total is constant within a hand, the button is constant within a hand, our seat is
    constant for the table, and (for an adapter whose history_source is "log") each decision's history
    extends the previous decision's in the same hand, so a raise seen once is never dropped later."""

    def __init__(self, examples: int = EXAMPLES_PER_RULE, history_source: str = "log"):
        self.observations = 0
        self.counts: Counter = Counter()
        self.fixes: Counter = Counter()  # what make_observation put right (extras["kit_fixes"]): the kit's quirks, not bugs
        self.examples: dict[str, list[str]] = {}
        self.actions: Counter = Counter()
        self.keep = examples
        self.history_source = history_source  # "log", "partial" or "bets", as the adapter declares
        self.inference = None  # the adapter's HistoryInference (hyperion/drills/infer_history.py), for the summary
        self._inf_hist: tuple[int, list] | None = None  # hand_no, the last rebuilt history
        self._seat: int | None = None
        self._last: tuple[int, int, int] | None = None  # hand_no, chip total, button
        self._hist: tuple[int, list] | None = None  # hand_no, the last observation's history as (seat, kind, amount)

    @property
    def total(self) -> int:
        return sum(self.counts.values())

    @property
    def clean(self) -> bool:
        return self.total == 0

    def record(self, violations: list[str]) -> None:
        for text in violations:
            rule = text.split(":", 1)[0]
            self.counts[rule] += 1
            ex = self.examples.setdefault(rule, [])
            if len(ex) < self.keep:
                ex.append(text)

    def check(self, obs: Observation, rules: Rules | None = None) -> list[str]:
        self.observations += 1
        for f in (obs.extras or {}).get("kit_fixes", ()):
            self.fixes[f] += 1
        v = check_observation(obs, rules)
        try:
            v += self._across_calls(obs)
        except Exception as e:  # noqa: BLE001
            v.append(f"checker: {type(e).__name__}: {e}")
        self.record(v)
        return v

    def _across_calls(self, obs: Observation) -> list[str]:
        out: list[str] = []
        if self._seat is None:
            self._seat = obs.seat
        elif obs.seat != self._seat:
            out.append(f"seat_changed: seat {obs.seat} after {self._seat} at the same table")
        total = obs.pot + sum(obs.bets) + sum(obs.stacks)
        if self._last is not None and self._last[0] == obs.hand_no:
            _, t, b = self._last
            if total != t:
                out.append(f"chips: table total went {t} -> {total} within hand {obs.hand_no} "
                           f"(pot includes this street's bets, or stacks already exclude them?)")
            if obs.button != b:
                out.append(f"button_changed: button {b} -> {obs.button} within hand {obs.hand_no}")
        self._last = (obs.hand_no, total, obs.button)
        hist = [(s, a.kind.value, a.amount) for s, a in obs.history]
        if self.history_source == "log" and self._hist is not None and self._hist[0] == obs.hand_no:
            prev = self._hist[1]
            if hist[: len(prev)] != prev:
                out.append(f"history_prefix: hand {obs.hand_no}: this decision's history does not extend the last one "
                           f"({len(prev)} entries then {len(hist)}); a kit log only grows. If the kit has no log and the "
                           f"history is rebuilt from the bets each decision, declare history_source = \"bets\" on the "
                           f"adapter (earlier streets' raises are then lost, and the report says so)")
        self._hist = (obs.hand_no, hist)
        return out

    GAP_RATE = 0.05  # more of the hands than this with a gap: the state the adapter builds disagrees with the betting

    def check_history(self, obs: Observation, rules: Rules | None = None) -> list[str]:
        """The history the bot reads on a kit with no or a partial log (Adapter.with_history): the inference's log must
        explain the bets unless it stopped at a gap, and must only grow within a hand."""
        if self.history_source == "log":
            return []
        v: list[str] = []
        try:
            gap = bool(obs.extras and obs.extras.get("history_gap"))
            if not gap:
                miss = _check_raise_in_history(obs, rules or Rules())
                v += [x.replace("history_raise:", "history_infer:", 1) for x in miss]
            hist = [(s, a.kind.value, a.amount) for s, a in obs.history]
            prev = self._inf_hist
            if prev is not None and prev[0] == obs.hand_no and hist[: len(prev[1])] != prev[1]:
                v.append(f"history_infer: hand {obs.hand_no}: the rebuilt history does not extend the last decision's")
            self._inf_hist = (obs.hand_no, hist)
        except Exception as e:  # noqa: BLE001
            v.append(f"checker: {type(e).__name__}: {e}")
        self.record(v)
        return v

    def gap_finding(self) -> str | None:
        """A violation line when the inference stopped at a gap in too many hands (it should almost never)."""
        inf = self.inference
        if inf is None or self.history_source == "log" or inf.hands < 20 or inf.gaps <= self.GAP_RATE * inf.hands:
            return None
        return (f"history_gap: the rebuilt log stopped at a gap in {inf.gaps} of {inf.hands} hands: the stacks, bets, "
                f"in-hand flags or pot this adapter builds disagree with the betting (pot with this street's bets "
                f"in it? a folded seat still in hand? blinds posted by other seats than the engine's?)")

    def summary(self) -> str:
        lines = []
        gap = self.gap_finding()
        if gap is not None and "history_gap" not in self.counts:
            self.record([gap])
        for rule, count in self.counts.most_common():
            lines.append(f"  {rule} x{count}")
            lines.extend(f"    {ex}" for ex in self.examples[rule])
        if self.fixes:
            lines.append("  kit quirks make_observation put right (not violations; check the rule sheet agrees): "
                         + ", ".join(f"{k} x{c}" for k, c in self.fixes.most_common()))
        acts = " ".join(f"{k} {self.actions[k]}" for k in ("fold", "check", "call", "raise"))
        lines.append(f"conformance: {self.observations} observations checked, {self.total} violations"
                     f"{' in ' + str(len(self.counts)) + ' rules' if self.counts else ''}; actions {acts}")
        inf = self.inference
        rebuilt = (f"; rebuilt from the states (hyperion/drills/infer_history.py): {inf.gaps} of {inf.hands} hands "
                   f"stopped at a gap" if inf is not None else
                   "; rebuilt from the bets each decision (no inference attached): this street's raises only, "
                   "earlier streets' are lost")
        lines.append({"log": "history: the kit's action log; hand end adds our last reply",
                      "partial": "history: the kit's entries merged into the log" + rebuilt,
                      "bets": "history: the kit has no log" + rebuilt}.get(self.history_source,
                                                                           "history: " + str(self.history_source)))
        return "\n".join(lines)


def checked(adapter: Any, rules: Rules | None = None, report: ConformanceReport | None = None) -> Any:
    """Wrap the instance's to_observation and from_action; returns the same adapter with `.conformance`.
    `rules` defaults to the adapter's own Rules at each call (so a later `start(rules=...)` is honoured)."""
    if getattr(adapter, "conformance", None) is not None:
        return adapter
    report = report or ConformanceReport(history_source=getattr(adapter, "history_source", "log"))
    to_obs, from_act = adapter.to_observation, adapter.from_action
    with_hist = getattr(adapter, "with_history", None)
    report.inference = getattr(adapter, "inference", None)

    def to_observation(native: Any) -> Observation:
        try:
            obs = to_obs(native)
        except Exception as e:
            report.record([f"translate_error: {type(e).__name__}: {e}"])
            raise
        report.check(obs, rules if rules is not None else adapter.rules)
        return obs

    def from_action(action: Action, obs: Observation, native: Any) -> Any:
        try:
            out = from_act(action, obs, native)
        except Exception as e:
            report.record([f"from_action_error: {type(e).__name__}: {e} for {action}"])
            raise
        report.actions[action.kind.value] += 1
        return out

    def with_history(obs: Observation) -> Observation:
        out = with_hist(obs)
        report.check_history(out, rules if rules is not None else adapter.rules)
        return out

    adapter.to_observation = to_observation
    adapter.from_action = from_action
    if with_hist is not None:
        adapter.with_history = with_history
    adapter.conformance = report
    return adapter


def maybe_checked(adapter: Any) -> Any:
    """`checked(adapter)` when HYPERION_CHECK=1, with the report printed to stderr at exit; else unchanged."""
    if os.environ.get("HYPERION_CHECK") != "1":
        return adapter
    checked(adapter)
    atexit.register(_print_report, adapter)
    return adapter


def _print_report(adapter: Any) -> None:
    try:
        sys.stderr.write(f"conformance report for {type(adapter).__name__}:\n{adapter.conformance.summary()}\n")
        sys.stderr.flush()
    except Exception:  # noqa: BLE001 - stderr may be gone at exit
        pass


# ------------------------------------------------------------------ demo: a buggy adapter the check catches

def _demo(hands: int = 50, seed: int = 3) -> int:
    """Kit B and kit C reference adapters (clean), then two deliberately wrong kit B adapters."""
    import tempfile
    import types
    from pathlib import Path

    from hyperion.drills.adapter import KitBAdapter, make_observation
    from hyperion.drills.cheapbot import CheapBot
    from hyperion.drills.fakekits.kit_b import runner as run_b
    from hyperion.drills.fakekits.kit_c import runner as run_c

    class IncrementAsTotal(KitBAdapter):
        """The increment-vs-total bug: min/max_raise_by passed straight through as raise-to totals."""

        def to_observation(self, o: dict) -> Observation:
            obs = super().to_observation(o)
            obs.min_raise, obs.max_raise = o["you"]["min_raise_by"], o["you"]["max_raise_by"]
            return obs

    class PotIncludesBets(KitBAdapter):
        """The pot bug: this street's bets added to a pot that already excludes them."""

        def to_observation(self, o: dict) -> Observation:
            obs = super().to_observation(o)
            obs.pot += sum(obs.bets)
            return obs

    def kit_b(adapter) -> str:
        checked(adapter)
        mod = types.SimpleNamespace(decide=adapter.decide,
                                    on_table_start=lambda info: adapter.start(info["seat"], info["players"]),
                                    on_hand_end=lambda info: adapter.hand_end(info["hand_id"], info["delta"]))
        r = run_b.run(mod, hands=hands, seed=seed)
        return r.summary() + "\n" + adapter.conformance.summary()

    print(f"== kit B reference adapter, {hands} hands\n" + kit_b(KitBAdapter(CheapBot())))
    with tempfile.TemporaryDirectory() as d:
        sub = Path(d) / "submission.py"
        sub.write_text("import sys\nfrom hyperion.drills.adapter import KitCAdapter\nfrom hyperion.drills.cheapbot import CheapBot\n"
                       "from hyperion.drills.conformance import maybe_checked\n"
                       "maybe_checked(KitCAdapter(CheapBot())).serve(sys.stdin, sys.stdout)\n")
        os.environ["HYPERION_CHECK"] = "1"
        r = run_c.run([sys.executable, str(sub)], hands=hands, seed=seed)
        print(f"\n== kit C reference adapter via HYPERION_CHECK=1, {hands} hands\n" + r.summary())
        print("\n".join("  " + n for n in r.notes))
    print(f"\n== WRONG kit B adapter: increments passed as totals\n" + kit_b(IncrementAsTotal(CheapBot())))
    print(f"\n== WRONG kit B adapter: pot includes this street's bets\n" + kit_b(PotIncludesBets(CheapBot())))
    _ = make_observation  # noqa: F841 - imported so a broken adapter.py fails here, not mid-demo
    return 0


_demo.__test__ = False  # not a pytest target

if __name__ == "__main__":
    sys.exit(_demo())
