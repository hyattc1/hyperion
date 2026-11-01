"""Rebuild the action log on a kit that has none, or only part of one, from what every kit shows.

Our bots read the hand's actions from `obs.history`: Hero's raise counts and opener reads, its profiler, the exploit
layer's fold streaks and dead or timing-out seats, rival 3's seat reads. A kit with no log hides all of it, which cost
Hero 0.6 and hybrid3_x 0.75-0.9 points a table in the base-switch rehearsal. Every kit does show, at each of our
decisions, each seat's in-hand flag, its chips behind, its chips in this street and the pot. Between two of our
decisions in a hand each other seat acts at most once a street, so the change in those numbers says what it did:

    went out of the hand           fold
    put in more, to a new high     raise to that total (all-in when its stack is now 0)
    put in more, to the high       call (a short all-in call when it is all-in below it)
    put in nothing, still in       check, where the betting order says it was asked and owed nothing

`HistoryInference` replays the engine's own betting procedure (who still has to act, in order from the button,
blinds and straddle posted, full and short raises) with those actions as the unknowns, and checks every observation
against the state it predicts. Across a street change the old street's last bets are in the pot, so each seat's
chips behind give what it put in. An action that the states do not settle is a gap, and the history stops there for
the rest of the hand: every entry it emits happened, in the order it happened. One example of a gap: a seat that
owed nothing, put nothing in and is out by our next turn could have folded at once or checked and then folded
on the next street before us.

Our own reply is read back from the next state like any other seat's. Nothing after our last decision shows in a
state, so at hand end the history carries our last reply as sent, and the seats after it only if the kit shows how the
hand ended (`final_stacks`, `deltas` or `shown`; `hand_end`). Otherwise they stay unknown and are never invented.

Merging with a kit's own entries (`kit` on observe): a complete log wins; a partial one (this street only, the
last few actions) is spliced in where it agrees with the rebuilt prefix and extends it.

Cost: one pass over the seats that acted since the last decision, about 10-25 µs a decision.

    inf = HistoryInference(rules)
    obs = inf.observe(obs)      # each decision: obs with history rebuilt, extras["history_inferred"] = True
    inf.acted(action)           # what we sent back
    hist = inf.hand_end(final_stacks=..., shown=...)   # the HandResult's history; arguments when the kit gives them

A kit whose hand end says nothing still shows every seat's stack in the next hand's first state, so the adapter holds
the hand end until then (`finals_from_next`): the folds after our last reply and every seat's chip change, delivered
just before the next decision. `InferSeat(bot)` is the simulator seat a kit with no log gives through such an adapter
(tools/gate.py's in-sim baseline for `--kit-log no`, and the measurement in hyperion/drills/infer_eval.py).
"""
from __future__ import annotations

import dataclasses

from hyperion.core.types import Action, ActionKind, HandResult, Observation, Rules

_RAISE = ActionKind.RAISE
_FOLD, _CHECK, _CALL = Action.fold(), Action.check(), Action.call()


class HistoryInference:
    """One seat's rebuilt action log for the hand in play. Never raises: a state it cannot explain is a gap."""

    def __init__(self, rules: Rules | None = None):
        self.rules = rules or Rules()
        self.hand_no = None
        self.hist: list[tuple[int, Action]] = []
        self.live = False  # the walk below is valid (no gap yet this hand)
        self.gap = False
        self.sent: Action | None = None  # our reply at the last decision
        self.paused = False  # the walk stands at our turn, our reply not yet read back
        # counters for reports and tests
        self.hands = self.gaps = 0
        self.merged = self.conflicts = 0

    # ------------------------------------------------------------------ public
    def new_table(self, rules: Rules | None = None) -> None:
        if rules is not None:
            self.rules = rules
        self.hand_no = None
        self.live = self.gap = self.paused = False
        self.hist = []
        self.sent = None

    def history(self, obs: Observation) -> list[tuple[int, Action]]:
        """The rebuilt history at this decision (the longest certain prefix of the hand's actions)."""
        try:
            if obs.hand_no != self.hand_no:
                self._start(obs)
            elif self.live:
                self._advance(obs)
        except Exception:  # noqa: BLE001 - a bug here costs the hand's history, never the decision
            self._fail()
        return self.hist

    def observe(self, obs: Observation, kit=None) -> Observation:
        """obs with history = the rebuilt log, merged with `kit` (the kit's own entries, if it shows any; None or []
        when it has no log). extras gain history_inferred (and history_gap after a gap); history_from_bets is
        dropped, since this history holds real folds, calls and checks."""
        hist = self.history(obs)
        if kit:
            hist = self.merge(hist, list(kit))
        extras = dict(obs.extras) if obs.extras else {}
        extras.pop("history_from_bets", None)
        extras["history_inferred"] = True
        if self.gap:
            extras["history_gap"] = True
        return dataclasses.replace(obs, history=list(hist), extras=extras)

    def acted(self, action: Action) -> None:
        """Our reply at this decision, as sent (read back from the next state; used as is only at hand end)."""
        self.sent = action

    def hand_end(self, final_stacks=None, deltas=None, shown=None, hand_no=None) -> list[tuple[int, Action]]:
        """The hand's history for the HandResult: the rebuilt prefix, our last reply, and the seats after it when the
        kit shows how the hand ended. `final_stacks` (every seat's chips after the hand) or `deltas` (every seat's
        chip change over the hand; antes come from Rules) say who put more in; `shown` (seats at showdown, {} when
        there was none) says who was still in at the end. Without them the tail stays unknown. `hand_no`: the hand
        the kit says ended; a hand we never acted in (all-in from a blind) has no history here."""
        if hand_no is not None and hand_no != self.hand_no:
            self.live = self.paused = False
            self.sent = None
            return []
        out = list(self.hist)
        try:
            if self.live and self.paused and self.sent is not None:
                out.extend(self._tail(final_stacks, deltas, shown))
        except Exception:  # noqa: BLE001
            pass
        self.live = self.paused = False
        self.sent = None
        return out

    def merge(self, mine: list, kit: list) -> list:
        """The kit's own entries with the rebuilt ones: the kit's log when the rebuilt prefix starts it; the rebuilt
        prefix extended by the kit's entries where they overlap its end (a log of this street, or the last few
        actions); the rebuilt prefix when they disagree (a translation bug: counted in `conflicts`)."""
        if not kit:
            return mine
        n, k = len(mine), len(kit)
        if k >= n and _same(kit[:n], mine):
            if k > n:
                self.merged += 1
            return kit
        if _same(mine[:k], kit):
            return mine
        for off in range(1, n + 1):  # kit = a suffix of the true log, overlapping the end of ours or just after it
            tail = mine[off:]
            if len(tail) <= k and _same(kit[:len(tail)], tail):
                if k > len(tail):
                    self.merged += 1
                    return mine[:off] + kit
                return mine
        self.conflicts += 1
        return mine

    # ------------------------------------------------------------------ the walk
    def _fail(self) -> None:
        if self.live:
            self.gaps += 1
        self.live = False
        self.gap = True
        self.paused = False

    def _start(self, obs: Observation) -> None:
        """A new hand: post the blinds (and a straddle) on the totals behind, then walk to our first turn."""
        self.hand_no = obs.hand_no
        self.hands += 1
        self.hist = []
        self.sent = None
        self.gap = False
        self.paused = False
        self.live = False
        n = len(obs.stacks)
        if n < 2 or obs.street != 0:
            self._fail()
            return
        stacks0 = [obs.stacks[s] + obs.bets[s] for s in range(n)]
        dealt = [bool(obs.in_hand[s]) or stacks0[s] > 0 for s in range(n)]
        button = obs.button
        order = [(button + i) % n for i in range(1, n + 1)]
        alive = [s for s in order if dealt[s]]
        if len(alive) < 2:
            self._fail()
            return
        if len(alive) == 2:
            sbs = button if dealt[button] else alive[0]
            bbs = alive[1] if alive[0] == sbs else alive[0]
        else:
            sbs, bbs = alive[0], alive[1]
        sb, bb = obs.blinds
        stacks, bets = stacks0[:], [0] * n
        for seat, amt in ((sbs, sb), (bbs, bb)):
            put = amt if amt < stacks[seat] else stacks[seat]
            stacks[seat] -= put
            bets[seat] += put
        last_inc, last_blind = bb, bbs
        straddle = getattr(self.rules, "straddle", 0)
        if straddle and len(alive) >= 3:
            st = alive[2 % len(alive)]
            amt = straddle * bb
            put = amt if amt < stacks[st] else stacks[st]
            stacks[st] -= put
            bets[st] += put
            if put == amt:
                last_inc = amt
            last_blind = st
        self.n, self.me, self.button, self.bb = n, obs.seat, button, bb
        self.stacks0 = stacks0
        self.pot0 = obs.pot
        self.stacks, self.bets, self.inh = stacks, bets, dealt[:]
        self.need = [dealt[s] and stacks[s] > 0 for s in range(n)]
        self.street, self.pot = 0, obs.pot
        self.cur, self.last_inc = max(bets), last_inc
        self.pos = (last_blind + 1) % n
        self.live = True
        self._advance(obs)

    def _advance(self, T: Observation) -> None:
        """Walk the betting from where it stands to our turn in T, emitting each seat's action as T settles it."""
        n, me = self.n, self.me
        if T.street < self.street or len(T.stacks) != n or T.seat != me:
            self._fail()
            return
        stacks, bets, inh, need, hist = self.stacks, self.bets, self.inh, self.need, self.hist
        Tst, Tbets, Tin = T.stacks, T.bets, T.in_hand
        first = self.paused  # our own reply comes first, read back from T like any other seat's
        if first and T.street == self.street and T.pot == self.pot and list(Tbets) == bets and list(Tst) == stacks:
            return  # the same decision asked again (a kit that re-asks after a bad reply): nothing has happened
        self.paused = False
        steps = 0
        while True:
            steps += 1
            if steps > 8 * n:
                self._fail()
                return
            if not any(need):  # the round is over
                if self.street >= T.street or sum(inh) < 2:
                    self._fail()
                    return
                self.pot += sum(bets)
                for i in range(n):
                    bets[i] = 0
                    need[i] = inh[i] and stacks[i] > 0
                self.street += 1
                self.cur, self.last_inc = 0, self.bb
                self.pos = (self.button + 1) % n
                continue
            s = self.pos
            if not need[s]:
                self.pos = (s + 1) % n
                continue
            cur = self.cur
            owe = cur - bets[s]
            if s == me and not first:
                if self.street != T.street:
                    self._fail()
                    return
                # our turn in T: everything the walk predicts must be what T shows
                if bets != list(Tbets) or stacks != list(Tst) or inh != [bool(x) for x in Tin] or self.pot != T.pot:
                    self._fail()
                    return
                self.paused = True
                return
            first = False
            responders = False
            for o in range(n):
                if o != s and inh[o] and stacks[o] > 0:
                    responders = True
                    break
            need[s] = False
            if owe <= 0 and not responders:  # the engine skips a seat with nothing to call and nobody to bet into
                self.pos = (s + 1) % n
                continue
            a = self._settle(s, owe, T)
            if a is None:
                self._fail()
                return
            self._apply(s, a)
            hist.append((s, a))
            if a is _FOLD and sum(inh) < 2:
                self._fail()  # the hand ended, yet T asks us to act
                return
            self.pos = (s + 1) % n

    def _settle(self, s: int, owe: int, T: Observation) -> Action | None:
        """Seat s's action at its turn now, from T; None when T does not settle it."""
        stacks, bets = self.stacks, self.bets
        if self.street == T.street:  # T is on this street: s acts once before our turn
            x = T.bets[s] - bets[s]
            if x < 0 or T.stacks[s] != stacks[s] - x:
                return None
            if not T.in_hand[s]:
                return _FOLD if x == 0 else None
            if x == 0:
                return _CHECK if owe <= 0 else None
            total = T.bets[s]
            if total > self.cur:
                return Action(_RAISE, total)
            if total == self.cur or T.stacks[s] == 0:
                return _CALL
            return None
        if self.street + 1 != T.street:
            return None
        # T is on the next street: what s put in for the rest of this one is what left its stack, less T's bet
        x = stacks[s] - T.stacks[s] - T.bets[s]
        if x < 0:
            return None
        if x == 0:
            if owe > 0:
                return None if T.in_hand[s] else _FOLD
            if T.in_hand[s]:
                return _CHECK
            # out by T, owing nothing now: a fold now, or a check now and a fold before us on T's street. Only a seat
            # acting after us on T's street cannot have folded there yet
            n, b = self.n, self.button
            return _FOLD if (s - b - 1) % n > (self.me - b - 1) % n else None
        total = bets[s] + x
        if total > self.cur:
            # a raise after our reply would have given us another turn on this street
            return Action(_RAISE, total) if s == self.me else None
        if total == self.cur or x == stacks[s]:
            return _CALL
        return None

    def _apply(self, s: int, a: Action) -> None:
        """The engine's bookkeeping for one action (hyperion/sim/engine.py _betting_round)."""
        stacks, bets, inh, need = self.stacks, self.bets, self.inh, self.need
        k = a.kind
        if a is _FOLD or k is ActionKind.FOLD:
            inh[s] = False
        elif k is ActionKind.CALL:
            owe = self.cur - bets[s]
            put = owe if owe < stacks[s] else stacks[s]
            stacks[s] -= put
            bets[s] += put
        elif k is _RAISE:
            total = a.amount
            put = total - bets[s]
            stacks[s] -= put
            bets[s] = total
            inc = total - self.cur
            full = inc >= self.last_inc
            if full:
                self.last_inc = inc
            self.cur = total
            for o in range(self.n):
                if o != s and inh[o] and stacks[o] > 0:
                    need[o] = True  # a short raise re-opens only the seats that had acted (they may call or fold)

    # ------------------------------------------------------------------ hand end
    def _tail(self, final_stacks, deltas, shown) -> list[tuple[int, Action]]:
        """Our last reply as sent, then each seat after it on this street while how the hand ended settles its action:
        a seat that owed chips, put nothing more in and won nothing folded at its turn. "Won nothing" is certain when
        the kit shows who was at showdown (`shown`; a seat not shown folded). With chip counts alone the folds are
        kept only when the rest of the hand is everyone folding to one seat, nobody all-in, and the chips show
        exactly that. Stops at the first seat whose action is not settled."""
        n, me, sent = self.n, self.me, self.sent
        owe = self.cur - self.bets[me]
        k = sent.kind
        if ((k is _RAISE and not self.cur < sent.amount <= self.bets[me] + self.stacks[me])
                or (k is ActionKind.CHECK and owe > 0) or (k is ActionKind.CALL and owe <= 0)):
            return []  # not a legal reply here: the kit must have changed it
        out = [(me, sent)]
        self.need[me] = False
        self._apply(me, sent)
        final = self._finals(final_stacks, deltas)
        if final is None:
            return out
        stacks, bets, inh, need = self.stacks, self.bets, self.inh, self.need
        allin = any(inh[s] and stacks[s] == 0 for s in range(n))
        pot = self.pot + sum(bets)
        folds: list[tuple[int, Action]] = []
        pos = (me + 1) % n
        for _ in range(n):
            if sum(inh) < 2 or not any(need):
                break
            s, pos = pos, (pos + 1) % n
            if not need[s]:
                continue
            need[s] = False
            responders = any(o != s and inh[o] and stacks[o] > 0 for o in range(n))
            if self.cur - bets[s] <= 0 and not responders:
                continue
            if self.cur - bets[s] <= 0 or final[s] != stacks[s] or (shown is not None and s in shown):
                break
            folds.append((s, _FOLD))
            inh[s] = False
        if shown is not None:
            return out + folds
        left = [s for s in range(n) if inh[s]]
        if (folds and not allin and len(left) == 1 and final[left[0]] == stacks[left[0]] + pot
                and all(final[s] == stacks[s] for s in range(n) if s != left[0])):
            return out + folds
        return out

    def start_stacks(self) -> list[int] | None:
        """Every seat's chips at the start of the hand in play, antes included (None when the antes do not add up)."""
        if self.hand_no is None or not hasattr(self, "stacks0"):
            return None
        paid = _antes(self.stacks0, self.pot0, self.rules, self.hand_no)
        return None if paid is None else [self.stacks0[s] + paid[s] for s in range(len(self.stacks0))]

    def _finals(self, final_stacks, deltas):
        if final_stacks is not None and len(final_stacks) == self.n:
            return [int(x) for x in final_stacks]
        if deltas is not None and len(deltas) == self.n:
            start = self.start_stacks()
            return None if start is None else [start[s] + int(deltas[s]) for s in range(self.n)]
        return None


def _antes(totals, pot: int, rules, hand_no: int) -> list[int] | None:
    """Each seat's ante, from the preflop pot before any bet goes in (it holds the antes only): None when they
    cannot be told apart (a seat all-in by its ante, or a pot that is not antes)."""
    n = len(totals)
    if pot == 0:
        return [0] * n
    payers = [s for s in range(n) if totals[s] > 0]
    ante = rules.ante_at(hand_no) if hasattr(rules, "ante_at") else 0
    if not ante or ante * len(payers) != pot:
        ante = pot // len(payers) if payers and pot % len(payers) == 0 else 0
    if not ante:
        return None
    return [ante if totals[s] > 0 else 0 for s in range(n)]


def finals_from_next(obs: Observation, rules: Rules | None = None) -> list[int] | None:
    """Every seat's chips after the last hand, from this hand's first state (preflop, before our first reply): what
    each seat has behind and in front now, plus the ante it posted. The tail of a hand on a kit whose hand end says
    nothing (`HistoryInference.hand_end(final_stacks=...)`). None when this is not a preflop state or the antes do
    not add up."""
    if obs.street != 0:
        return None
    totals = [obs.stacks[s] + obs.bets[s] for s in range(len(obs.stacks))]
    paid = _antes(totals, obs.pot, rules or Rules(), obs.hand_no)
    return None if paid is None else [totals[s] + paid[s] for s in range(len(totals))]


def _same(a: list, b: list) -> bool:
    if len(a) != len(b):
        return False
    for (s1, x), (s2, y) in zip(a, b):
        if s1 != s2 or x.kind is not y.kind or (x.kind is _RAISE and x.amount != y.amount):
            return False
    return True


class InferSeat:
    """A bot fed what a kit with no action log gives it through an adapter that infers the log: each decision's history
    rebuilt by HistoryInference from the bare state; each hand end with only its own chip change, and the rebuilt
    history (our last reply included). The in-sim counterpart of NoLogSeat, for tools/gate.py --kit-log no and the
    measurement (hyperion/drills/infer_eval.py).

    `final` is what the seat sees of how each hand ended:
      "next"    nothing at hand end; the hand end waits for the next hand's first state, whose stacks settle the folds
                after our last reply and give every seat's chip change (what Adapter does on such a kit; default)
      "none"    nothing: the hand end goes at once with our own chip change and the log up to our reply
      "stacks"  every seat's chip change at hand end (a kit whose hand end lists them)
      "shown"   that and the hands at showdown"""

    def __init__(self, bot, final: str = "next"):
        self.bot = bot
        self.final = final
        self.inf = HistoryInference()
        self.rules = Rules()
        self.seat = 0
        self.pending: tuple[int, int] | None = None  # (hand_no, our chip change) of a hand end not yet delivered

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.seat, self.rules, self.pending = seat, rules, None
        self.inf.new_table(rules)
        self.bot.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        bare = dataclasses.replace(obs, history=[], extras=dict(obs.extras) if obs.extras else {})
        if self.pending is not None:
            self._deliver(bare)
        a = self.bot.act(self.inf.observe(bare))
        self.inf.acted(a.clamp(obs) if isinstance(a, Action) else a)
        return a

    def hand_end(self, result: HandResult) -> None:
        if self.final == "next":
            if self.pending is not None:
                self._deliver(None)
            self.pending = (result.hand_no, result.deltas[self.seat])
            return
        if self.final == "none":
            self._end(result.hand_no, result.deltas[self.seat], self.inf.hand_end(hand_no=result.hand_no))
            return
        shown = dict(result.showdown) if self.final == "shown" else None
        hist = self.inf.hand_end(deltas=result.deltas, shown=shown, hand_no=result.hand_no)
        self.bot.hand_end(HandResult(hand_no=result.hand_no, deltas=list(result.deltas), showdown=shown or {},
                                     board=tuple(result.board) if self.final == "shown" else (), history=hist))

    def _deliver(self, obs: Observation | None) -> None:
        """The waiting hand end, settled by this hand's first state when it follows it."""
        hand_no, delta = self.pending
        self.pending = None
        finals = finals_from_next(obs, self.rules) if obs is not None and obs.hand_no == hand_no + 1 else None
        start = self.inf.start_stacks() if finals is not None and self.inf.hand_no == hand_no else None
        hist = self.inf.hand_end(final_stacks=finals if start is not None else None, hand_no=hand_no)
        if start is not None:
            self.bot.hand_end(HandResult(hand_no=hand_no, deltas=[f - b for f, b in zip(finals, start)], showdown={},
                                         board=(), history=hist))
        else:
            self._end(hand_no, delta, hist)

    def _end(self, hand_no: int, delta: int, hist) -> None:
        n = getattr(self.inf, "n", 0) or (self.seat + 1)
        deltas = [0] * n
        if 0 <= self.seat < n:
            deltas[self.seat] = delta
        self.bot.hand_end(HandResult(hand_no=hand_no, deltas=deltas, showdown={}, board=(), history=hist))

    def variant_decide(self, prompt: dict):
        return self.bot.variant_decide(prompt)
