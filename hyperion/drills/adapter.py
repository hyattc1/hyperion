"""Adapter pattern: kit-native state -> Observation, our Action -> kit-native action.

Strategy code never sees a kit. On event night you write one Adapter subclass for the real kit
(pattern below, worked examples for the three fake kits) and the bot behind it stays untouched.
Nothing here imports a fake kit; the reference adapters are pure translation.
"""
from __future__ import annotations

import os
import sys
from typing import Any, Callable, Iterable

from hyperion.core.types import Action, ActionKind, Bot, HandResult, Observation, Rules, parse_card

KIND_BY_NAME = {"fold": ActionKind.FOLD, "check": ActionKind.CHECK, "call": ActionKind.CALL, "raise": ActionKind.RAISE}


class Adapter:
    """Base class. Subclasses implement the three translation hooks; decide() does the rest safely.

    `history_source` says where obs.history comes from, and conformance holds the adapter to it:
      "log"      the kit's action log, the whole hand so far, so within a hand every decision's history extends the
                 last one. It is used as it is.
      "partial"  the kit shows some actions (this street only, the last few, ...): the rebuilt log below, extended
                 by the kit's entries where they agree with it.
      "bets"     the kit has no log (make_observation's raises-from-bets stand-in is dropped).
    For "partial" and "bets", decide() rebuilds the hand's log from the states the kit shows
    (hyperion/drills/infer_history.py: each seat's in-hand flag, stack and bet between our decisions; every entry
    true, a gap ends it). For every source, hand_end() adds our last reply and, when the kit shows how the hand
    ended (every seat's chips or deltas, the hands at showdown), the folds after it.
    """

    history_source = "log"

    def __init__(self, bot: Bot, rules: Rules | None = None):
        from hyperion.drills.infer_history import HistoryInference

        self.bot = bot
        self.rules = rules or Rules()
        self.seat = 0
        self.started = False
        self.inference = HistoryInference(self.rules)
        self._last_hist: list = []
        self._last_hand = None
        self._pending = None  # a hand end waiting for the next hand's first state (defer_hand_end)

    # -- translation hooks ------------------------------------------------------------
    def to_observation(self, native: Any) -> Observation:
        raise NotImplementedError

    def from_action(self, action: Action, obs: Observation, native: Any) -> Any:
        raise NotImplementedError

    def native_safe(self, native: Any) -> Any:
        """The kit's own check-if-possible-else-fold, used when translation itself blows up."""
        raise NotImplementedError

    # -- lifecycle ---------------------------------------------------------------------
    def start(self, seat: int, n_players: int, rules: Rules | None = None) -> None:
        if rules is not None:
            self.rules = rules
        self.seat = seat
        self.n_players = n_players
        self.started = True
        self._pending = None
        self.inference.new_table(self.rules)
        try:
            self.bot.new_table(self.rules, seat, n_players)
        except Exception:  # noqa: BLE001 - never let a bot bug reach the kit
            pass

    def with_history(self, obs: Observation) -> Observation:
        """obs with the history the bot reads: the kit's log, or the one rebuilt from the states (history_source).

        The inference runs on every decision, so its walk is in step for the hand end whatever the source; on a log
        kit it only watches."""
        kit = [] if (obs.extras and obs.extras.get("history_from_bets")) else obs.history
        if self.history_source == "log" and kit:
            self.inference.history(obs)
            out = obs
        else:
            out = self.inference.observe(obs, kit if self.history_source == "partial" else None)
        self._last_hist, self._last_hand = out.history, obs.hand_no
        return out

    def decide(self, native: Any) -> Any:
        try:
            obs = self.to_observation(native)
            if not self.started:
                self.start(obs.seat, obs.n_players)
            if self._pending is not None:
                self._deliver(obs)
            try:
                obs = self.with_history(obs)
            except Exception:  # noqa: BLE001 - the bot still decides, on the history make_observation gave
                pass
            action = self.bot.act(obs).clamp(obs)
            self.inference.acted(action)
            return self.from_action(action, obs, native)
        except Exception:  # noqa: BLE001
            return self.native_safe(native)

    def hand_end(self, hand_no: int, delta: int, n_players: int | None = None, history=None, deltas=None,
                 final_stacks=None, showdown=None, board=()) -> None:
        """The hand is over; pass whatever the kit's hand-end signal has.

        `history` the kit's [(seat, Action)] for the hand; `deltas` every seat's chip change (or `final_stacks`,
        every seat's chips after it); `showdown` {seat: hole cards} for every hand still in at showdown ({} when
        there was none; leave it None when the kit does not say). Without a history the rebuilt one goes to the bot:
        the hand's log up to our last decision, our reply, and the folds after it that the deltas and showdown
        settle. When the signal has none of deltas, final_stacks or showdown (`defer_hand_end`) and some seat had to
        act after our reply owing chips, the bot's hand end waits for the next hand's first state, whose stacks give
        every seat's chips after this hand: it is delivered at the top of that decision (50-200 us of the bot's own
        hand end inside it; `defer_hand_end = False` keeps it at the kit's hand end, untimed, without those
        folds). Rival 3's core (hybrid3_x, the composite) replays the hand's history here, as
        the simulator gives it."""
        try:
            if self._pending is not None:  # two hand ends with no decision between them (a walk in our big blind)
                self._deliver(None)
            if (deltas is None and final_stacks is None and showdown is None and self.defer_hand_end
                    and self.inference.hand_no == hand_no and (self.hold_all or self.inference.tail_open())):
                self._pending = (hand_no, delta, n_players, history, board)
                return
            self._end(hand_no, delta, n_players, history, deltas, final_stacks, showdown, board)
        except Exception:  # noqa: BLE001
            pass

    defer_hand_end = True
    hold_all = False  # hold every hand end we acted in: every seat's chip change for the bot's stacks (Hero's ICM
    #                  curve), at the cost of the bot's hand end inside the next decision on every hand

    def _deliver(self, obs: Observation | None) -> None:
        """The waiting hand end, settled by `obs` when it is the next hand's first state."""
        from hyperion.drills.infer_history import chips_after_hand

        hand_no, delta, n_players, history, board = self._pending
        self._pending = None
        after = deltas = None
        if obs is not None and obs.hand_no == hand_no + 1 and self.inference.hand_no == hand_no:
            after = chips_after_hand(obs, self.rules)
            start = self.inference.start_stacks() if after is not None else None
            if start is not None and len(start) == len(after):
                deltas = [f - b for f, b in zip(after, start)]
            else:
                after = None
        self._end(hand_no, delta, n_players, history, deltas, after, None, board)

    def _end(self, hand_no, delta, n_players, history, deltas, final_stacks, showdown, board) -> None:
        try:
            n = n_players or getattr(self, "n_players", 0) or max(1, self.seat + 1)
            shown = None if showdown is None else dict(showdown)
            hist = self.inference.hand_end(final_stacks=final_stacks, deltas=deltas, shown=shown, hand_no=hand_no)
            seen = self._last_hist if self._last_hand == hand_no else []
            hist = self.inference.merge(hist, list(seen))
            kit = list(history or [])
            if kit:
                hist = kit if self.history_source == "log" else self.inference.merge(hist, kit)
            if deltas is None:
                deltas = [0] * n
                deltas[self.seat] = delta
            self.bot.hand_end(HandResult(hand_no=hand_no, deltas=list(deltas), showdown=dict(showdown or {}),
                                         board=tuple(board or ()), history=hist))
        except Exception:  # noqa: BLE001
            pass
        self._last_hist, self._last_hand = [], None


def history_from_bets(street: int, button: int, stacks, bets, big_blind: int) -> list[tuple[int, Action]]:
    """This street's raises, rebuilt from the bets when the kit gives no action history.

    Hero reads who raised (Spot.n_raises, Spot.raiser, the opener and shove reads) from obs.history only; an
    empty history makes every raised pot look unopened, which cost Hero 2.5 points a table in drill 6 (5.9 to
    3.3 on the realistic field). One RAISE per distinct bet level above the street's base (the big blind
    preflop, 0 after), credited to the first seat in acting order at that level; a short all-in below the
    top level is a call, not a raise. Earlier streets' raises and the exact count of re-raises are lost."""
    n = len(bets)
    base = big_blind if street == 0 else 0
    top = max(bets) if n else 0
    first = 3 if street == 0 else 1  # UTG preflop, the first seat left of the button after
    order = sorted(range(n), key=lambda x: (x - button - first) % n)
    out: list[tuple[int, Action]] = []
    for level in sorted({b for b in bets if b > base}):
        seats = [x for x in order if bets[x] == level]
        if level < top and all(stacks[x] == 0 for x in seats):
            continue
        out.append((seats[0], Action(ActionKind.RAISE, int(level))))
    return out


class NoLogSeat:
    """A bot fed what a kit with no action log gives it through an adapter that infers nothing: each decision's history
    is this street's raises rebuilt from the bets (make_observation's rule, flagged in extras), and each hand end
    carries only its own chip change. What the reference adapters gave before the inference
    (hyperion/drills/infer_history.py InferSeat is the seat with it); tools/gate.py --kit-log bets seats the in-sim
    baseline this way, for a package whose adapter predates the inference."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.seat = 0
        self.n = 0

    def new_table(self, rules: Rules, seat: int, n_players: int) -> None:
        self.seat, self.n = seat, n_players
        self.bot.new_table(rules, seat, n_players)

    def act(self, obs: Observation) -> Action:
        import dataclasses

        hist = history_from_bets(obs.street, obs.button, obs.stacks, obs.bets, obs.blinds[1])
        return self.bot.act(dataclasses.replace(obs, history=hist, extras={**obs.extras, "history_from_bets": True}))

    def hand_end(self, result: HandResult) -> None:
        deltas = [0] * len(result.deltas)
        if 0 <= self.seat < len(deltas):
            deltas[self.seat] = result.deltas[self.seat]
        self.bot.hand_end(HandResult(hand_no=result.hand_no, deltas=deltas, showdown={}, board=(), history=[]))

    def variant_decide(self, prompt: dict):
        return self.bot.variant_decide(prompt)


def history_rows(history, discards: dict | None = None, at: int | None = None) -> list[list]:
    """obs.history -> the fake dealer's rows [seat, kind, total] (total only for a raise). `discards`
    {seat: card}, in toss order, go in as [seat, "discard", card] at history index `at` (the flop's first
    action), as the dealer logs them; without `at` they go last."""
    rows = [[int(s), a.kind.value, int(a.amount) if a.kind is ActionKind.RAISE else 0] for s, a in history]
    if discards:
        pos = len(rows) if at is None else min(at, len(rows))
        rows[pos:pos] = [[int(s), "discard", int(c)] for s, c in discards.items()]
    return rows


def dealer_state(obs: Observation, discards_at: int | None = None) -> dict:
    """The fake kits' dealer state (hyperion/drills/fakekits/_table.py) for an Observation: the inverse of
    make_observation, history and face-up discards included. Lists and ints only, so
    tools/gate.py can send it to another process (json turns the int keys of `discards` into strings;
    tools/gate_host.py turns them back). `kit.to_state(...)` and its peers accept it as it is."""
    discards = (obs.extras or {}).get("discards") or {}
    return {
        "hole": list(obs.hole), "board": list(obs.board), "street": obs.street, "seat": obs.seat,
        "button": obs.button, "stacks": list(obs.stacks), "bets": list(obs.bets), "in_hand": list(obs.in_hand),
        "pot": obs.pot, "to_call": obs.to_call, "min_raise": obs.min_raise, "max_raise": obs.max_raise,
        "legal": sorted(k.value for k in obs.legal), "hand_no": obs.hand_no, "blinds": list(obs.blinds),
        "history": history_rows(obs.history, discards, discards_at),
        "discards": {int(s): int(c) for s, c in discards.items()},
    }


def make_observation(*, hole, board, street, seat, button, stacks, bets, in_hand, pot, to_call, min_raise,
                     max_raise, legal: Iterable[str], hand_no, blinds, history=None) -> Observation:
    """Assemble an Observation from already-translated pieces; `legal` are lowercase kind names.
    No `history` (or an empty one) while somebody has bet above the blind: raises are rebuilt from the bets, and
    `extras["history_from_bets"]` says so (the shipped bot's core then reads no history: a replay of raises alone
    would book every raiser as a seat that raises every hand)."""
    hist = list(history or [])
    extras = {}
    if not hist:
        hist = history_from_bets(int(street), int(button), stacks, bets, int(blinds[1]))
        extras["history_from_bets"] = True
    return Observation(
        hole=tuple(hole), board=tuple(board), street=int(street), seat=int(seat), button=int(button),
        stacks=list(stacks), bets=list(bets), in_hand=list(in_hand), pot=int(pot), to_call=int(to_call),
        min_raise=int(min_raise), max_raise=int(max_raise),
        legal=frozenset(KIND_BY_NAME[k.lower()] for k in legal), hand_no=int(hand_no),
        blinds=(int(blinds[0]), int(blinds[1])), history=hist, extras=extras,
    )


# ------------------------------------------------------------------ kit A: class-based, strings

_A_STREETS = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}


def _a_card(s: str) -> int:
    return parse_card(s.replace("10", "T"))


def _a_history(log) -> list[tuple[int, Action]]:
    """kit A action_log [(index, "FOLD" | "CHECK" | "CALL" | "RAISE:120" | "DISCARD:Ah")] -> obs.history.
    Discards are not betting actions and are skipped; anything unreadable is skipped, never raised."""
    out: list[tuple[int, Action]] = []
    for item in log or ():
        try:
            seat, text = item
            word, _, amount = str(text).partition(":")
            kind = KIND_BY_NAME.get(word.lower())
            if kind is None:
                continue
            out.append((int(seat), Action(kind, int(amount) if kind is ActionKind.RAISE else 0)))
        except Exception:  # noqa: BLE001 - a malformed entry costs one history line, not the decision
            continue
    return out


class KitAAdapter(Adapter):
    """state attributes: hand, community, street, my_index, dealer_index, players[].stack/.bet/.folded,
    pot_size (includes current bets), current_bet, my_bet, legal_moves, min_raise, max_raise (totals)."""

    def to_observation(self, s: Any) -> Observation:
        stacks = [p.stack for p in s.players]
        bets = [p.bet for p in s.players]
        return make_observation(
            hole=[_a_card(c) for c in s.hand], board=[_a_card(c) for c in s.community],
            street=_A_STREETS[s.street], seat=s.my_index, button=s.dealer_index,
            stacks=stacks, bets=bets, in_hand=[not p.folded for p in s.players],
            pot=s.pot_size - sum(bets), to_call=min(s.current_bet - s.my_bet, s.my_stack),
            min_raise=s.min_raise, max_raise=s.max_raise, legal=s.legal_moves,
            hand_no=s.hand_number, blinds=(s.small_blind, s.big_blind),
            history=_a_history(getattr(s, "action_log", None)),
        )

    def from_action(self, a: Action, obs: Observation, s: Any) -> str:
        if a.kind is ActionKind.RAISE:
            return f"RAISE:{a.amount}"
        return a.kind.value.upper()

    def native_safe(self, s: Any) -> str:
        return "CHECK" if "CHECK" in getattr(s, "legal_moves", ()) else "FOLD"


class KitAAgent:
    """Drop-in `Agent` for kit A around any of our bots. Duck-types kit_a.kit.Agent."""

    def __init__(self, bot: Bot | None = None):
        self.adapter = KitAAdapter(bot or _default_bot())

    def new_game(self, my_index: int, n_players: int, starting_stack: int) -> None:
        self.adapter.start(my_index, n_players)

    def act(self, state: Any) -> str:
        return self.adapter.decide(state)

    def hand_over(self, hand_number: int, chip_change: int) -> None:
        self.adapter.hand_end(hand_number, chip_change)


# ------------------------------------------------------------------ kit B: dict in, dict out, increments

def _b_card(d: dict) -> int:
    return (int(d["rank"]) - 2) * 4 + "cdhs".index(str(d["suit"]).lower())


_B_STREETS = {0: 0, 3: 1, 4: 2, 5: 3}


class KitBAdapter(Adapter):
    """observation dict: hand.cards[{rank,suit}], table.{board,pot,button,players[{seat,chips,committed,
    active}]}, you.{seat,to_call,min_raise_by,max_raise_by}, actions, street = board count."""

    history_source = "bets"  # the kit has no action log

    def to_observation(self, o: dict) -> Observation:
        players = sorted(o["table"]["players"], key=lambda p: p["seat"])
        bets = [p["committed"] for p in players]
        current = max(bets)
        return make_observation(
            hole=[_b_card(c) for c in o["hand"]["cards"]], board=[_b_card(c) for c in o["table"]["board"]],
            street=_B_STREETS[int(o["street"])], seat=o["you"]["seat"], button=o["table"]["button"],
            stacks=[p["chips"] for p in players], bets=bets, in_hand=[bool(p["active"]) for p in players],
            pot=o["table"]["pot"], to_call=o["you"]["to_call"],
            min_raise=current + o["you"]["min_raise_by"], max_raise=current + o["you"]["max_raise_by"],
            legal=o["actions"], hand_no=o["hand_id"], blinds=(o["blinds"]["sb"], o["blinds"]["bb"]),
        )

    def from_action(self, a: Action, obs: Observation, o: dict) -> dict:
        if a.kind is ActionKind.RAISE:
            return {"action": "raise", "by": a.amount - max(obs.bets)}
        return {"action": a.kind.value}

    def native_safe(self, o: Any) -> dict:
        try:
            return {"action": "check" if "check" in o["actions"] else "fold"}
        except Exception:  # noqa: BLE001
            return {"action": "fold"}


def make_kit_b_module(bot: Bot | None = None) -> tuple[Callable, Callable, Callable]:
    """(decide, on_table_start, on_hand_end) closures to expose at module level in a kit B submission."""
    adapter = KitBAdapter(bot or _default_bot())

    def decide(observation: dict) -> dict:
        return adapter.decide(observation)

    def on_table_start(info: dict) -> None:
        adapter.start(info["seat"], info["players"])

    def on_hand_end(info: dict) -> None:
        adapter.hand_end(info["hand_id"], info["delta"])

    return decide, on_table_start, on_hand_end


# ------------------------------------------------------------------ kit C: line protocol

class KitCAdapter(Adapter):
    """Decision line clauses: H D S K B C E I O L V T (see kit_c/kit.py). Replies F/K/C/R<total>."""

    history_source = "bets"  # the kit has no action log

    @staticmethod
    def clauses(line: str) -> dict[str, str]:
        return {tok[0]: tok[1:] for tok in line.split() if tok}

    def to_observation(self, line: str) -> Observation:
        c = self.clauses(line)
        stacks = [int(x) for x in c["C"].split(",")]
        bets = [int(x) for x in c["E"].split(",")]
        seat = self.seat
        legal, lo, hi = [], 0, 0
        for tok in c["L"].split(","):
            if tok == "F":
                legal.append("fold")
            elif tok == "K":
                legal.append("check")
            elif tok == "C":
                legal.append("call")
            elif tok.startswith("R"):
                legal.append("raise")
                lo, hi = (int(x) for x in tok[1:].split("-"))
        sb, bb = (int(x) for x in c["V"].split("/"))
        return make_observation(
            hole=[parse_card(x) for x in c["K"].split(",")],
            board=[] if c["B"] == "-" else [parse_card(x) for x in c["B"].split(",")],
            street=int(c["S"]), seat=seat, button=int(c["D"]), stacks=stacks, bets=bets,
            in_hand=[ch == "1" for ch in c["I"]], pot=int(c["O"]),
            to_call=min(max(bets) - bets[seat], stacks[seat]), min_raise=lo, max_raise=hi,
            legal=legal, hand_no=int(c["H"]), blinds=(sb, bb),
        )

    def from_action(self, a: Action, obs: Observation, line: str) -> str:
        if a.kind is ActionKind.RAISE:
            return f"R{a.amount}"
        return {"fold": "F", "check": "K", "call": "C"}[a.kind.value]

    def native_safe(self, line: str) -> str:
        try:
            return "K" if "K" in self.clauses(line)["L"].split(",") else "F"
        except Exception:  # noqa: BLE001
            return "F"

    def serve(self, inp=None, out=None) -> None:
        """Run the stdin/stdout loop until Q or EOF. The T line gets OK; L lines get an action."""
        inp = inp or sys.stdin
        out = out or sys.stdout
        for line in inp:
            line = line.strip()
            if not line:
                continue
            if line.startswith("Q"):
                break
            c = self.clauses(line)
            if line.startswith("T") and "P" in c:
                self.start(int(c["P"]), int(c["T"]))
                out.write("OK\n")
                out.flush()
            elif "X" in c and "W" in c:
                self.hand_end(int(c["X"]), int(c["W"]))
            elif "L" in c:
                out.write(self.decide(line) + "\n")
                out.flush()


def _default_bot() -> Bot:
    """The bot hyperion/ship.py ships (`ship.make_bot()`: SHIP with its DIALS, which a package records), else the
    cheap stand-in. HYPERION_DRILL_BOT=cheap forces the stand-in (adapter tests measure translation, not the bot)."""
    if os.environ.get("HYPERION_DRILL_BOT") == "cheap":
        from hyperion.drills.cheapbot import CheapBot

        return CheapBot()
    try:
        from hyperion.ship import make_bot  # type: ignore

        return make_bot()
    except Exception:  # noqa: BLE001 - not there yet, or broken: the drill must still run
        from hyperion.drills.cheapbot import CheapBot

        return CheapBot()


# ------------------------------------------------------------------ kit D: MIT-style Bot, namedtuple states

_D_STREETS = {0: 0, 3: 1, 4: 2, 5: 3}
_D_KIND_BY_CLASS = {"FoldAction": "fold", "CallAction": "call", "CheckAction": "check", "RaiseAction": "raise"}
_D_CLASS_BY_KIND = {v: k for k, v in _D_KIND_BY_CLASS.items()}


def _d_round_total(round_state: Any) -> int:
    """Chips at the table at round start: walk previous_state to the root, where pips are just the blinds."""
    rs = round_state
    while getattr(rs, "previous_state", None) is not None:
        rs = rs.previous_state
    return sum(rs.stacks) + sum(rs.pips)


class KitDAdapter(Adapter):
    """native = (game_state, round_state, active). RoundState fields: button, street (0/3/4/5), pips, stacks,
    hands (card strings, ours filled), board, acting, in_hand, blinds, last_raise, previous_state;
    legal_actions() is a set of action classes (no FoldAction when a check is free); raise_bounds() are
    raise-to totals. Replies are instances of the classes found in the legal set, so no kit import."""

    history_source = "bets"  # previous_state holds the hand, but this adapter does not walk it: the inference does

    def __init__(self, bot: Bot, rules: Rules | None = None):
        super().__init__(bot, rules)
        self.round_total: int | None = None
        self._classes: dict[str, Any] = {}

    def new_round(self, game_state: Any, round_state: Any, active: int) -> None:
        self.round_total = sum(round_state.stacks) + sum(round_state.pips)
        if not self.started:
            self.start(active, len(round_state.stacks))

    def to_observation(self, native: Any) -> Observation:
        game_state, rs, seat = native
        stacks, pips = list(rs.stacks), list(rs.pips)
        self._classes = {cls.__name__: cls for cls in rs.legal_actions()}
        legal = [_D_KIND_BY_CLASS[name] for name in self._classes]
        lo, hi = rs.raise_bounds() if "raise" in legal else (0, 0)
        total = self.round_total if self.round_total is not None else _d_round_total(rs)
        return make_observation(
            hole=[parse_card(c) for c in rs.hands[seat]], board=[parse_card(c) for c in rs.board],
            street=_D_STREETS[int(rs.street)], seat=seat, button=rs.button, stacks=stacks, bets=pips,
            in_hand=list(rs.in_hand), pot=max(0, total - sum(stacks) - sum(pips)),
            to_call=min(max(pips) - pips[seat], stacks[seat]), min_raise=lo, max_raise=hi, legal=legal,
            hand_no=int(game_state.round_num) - 1, blinds=rs.blinds,
        )

    def from_action(self, a: Action, obs: Observation, native: Any) -> Any:
        classes = self._classes
        if a.kind is ActionKind.RAISE:
            return classes["RaiseAction"](a.amount)
        cls = classes.get(_D_CLASS_BY_KIND[a.kind.value]) or classes.get("CheckAction") or classes.get("FoldAction")
        return cls()

    def native_safe(self, native: Any) -> Any:
        try:
            classes = {cls.__name__: cls for cls in native[1].legal_actions()}
        except Exception:  # noqa: BLE001 - native is not even a state; use the classes seen last time
            classes = self._classes
        cls = classes.get("CheckAction") or classes.get("FoldAction")
        return cls() if cls is not None else None

    def round_over(self, game_state: Any, terminal_state: Any, active: int) -> None:
        """Every seat's delta and the hands shown at showdown: the inference settles the folds after our last reply."""
        try:
            last = terminal_state.previous_state
            shown = {s: tuple(parse_card(c) for c in h) for s, h in enumerate(last.hands) if h and s != active}
            deltas = list(terminal_state.deltas)
            self.hand_end(int(game_state.round_num) - 1, deltas[active], len(deltas), deltas=deltas, showdown=shown,
                          board=tuple(parse_card(c) for c in last.board))
        except Exception:  # noqa: BLE001
            pass


class KitDBot:
    """Drop-in MIT-style Bot around any of our bots. Duck-types kit_d.kit.Bot (three hooks)."""

    def __init__(self, bot: Bot | None = None):
        self.adapter = KitDAdapter(bot or _default_bot())

    def handle_new_round(self, game_state: Any, round_state: Any, active: int) -> None:
        self.adapter.new_round(game_state, round_state, active)

    def get_action(self, game_state: Any, round_state: Any, active: int) -> Any:
        return self.adapter.decide((game_state, round_state, active))

    def handle_round_over(self, game_state: Any, terminal_state: Any, active: int) -> None:
        self.adapter.round_over(game_state, terminal_state, active)
