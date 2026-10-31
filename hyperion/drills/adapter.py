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
    """Base class. Subclasses implement the three translation hooks; decide() does the rest safely."""

    def __init__(self, bot: Bot, rules: Rules | None = None):
        self.bot = bot
        self.rules = rules or Rules()
        self.seat = 0
        self.started = False

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
        self.started = True
        try:
            self.bot.new_table(self.rules, seat, n_players)
        except Exception:  # noqa: BLE001 - never let a bot bug reach the kit
            pass

    def decide(self, native: Any) -> Any:
        try:
            obs = self.to_observation(native)
            if not self.started:
                self.start(obs.seat, obs.n_players)
            action = self.bot.act(obs).clamp(obs)
            return self.from_action(action, obs, native)
        except Exception:  # noqa: BLE001
            return self.native_safe(native)

    def hand_end(self, hand_no: int, delta: int, n_players: int | None = None) -> None:
        try:
            deltas = [0] * (n_players or max(1, self.seat + 1))
            deltas[self.seat] = delta
            self.bot.hand_end(HandResult(hand_no=hand_no, deltas=deltas, showdown={}, board=(), history=[]))
        except Exception:  # noqa: BLE001
            pass


def make_observation(*, hole, board, street, seat, button, stacks, bets, in_hand, pot, to_call, min_raise,
                     max_raise, legal: Iterable[str], hand_no, blinds, history=None) -> Observation:
    """Assemble an Observation from already-translated pieces; `legal` are lowercase kind names."""
    return Observation(
        hole=tuple(hole), board=tuple(board), street=int(street), seat=int(seat), button=int(button),
        stacks=list(stacks), bets=list(bets), in_hand=list(in_hand), pot=int(pot), to_call=int(to_call),
        min_raise=int(min_raise), max_raise=int(max_raise),
        legal=frozenset(KIND_BY_NAME[k.lower()] for k in legal), hand_no=int(hand_no),
        blinds=(int(blinds[0]), int(blinds[1])), history=list(history or []),
    )


# ------------------------------------------------------------------ kit A: class-based, strings

_A_STREETS = {"preflop": 0, "flop": 1, "turn": 2, "river": 3}


def _a_card(s: str) -> int:
    return parse_card(s.replace("10", "T"))


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
    """Hero if the strategy builder has shipped it, else the cheap stand-in. HYPERION_DRILL_BOT=cheap forces
    the stand-in (adapter tests measure translation, not hero)."""
    if os.environ.get("HYPERION_DRILL_BOT") == "cheap":
        from hyperion.drills.cheapbot import CheapBot

        return CheapBot()
    try:
        from hyperion.strategy.hero import make_bot  # type: ignore

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
        try:
            last = terminal_state.previous_state
            shown = {s: tuple(parse_card(c) for c in h) for s, h in enumerate(last.hands) if h and s != active}
            self.bot.hand_end(HandResult(hand_no=int(game_state.round_num) - 1, deltas=list(terminal_state.deltas),
                                         showdown=shown, board=tuple(parse_card(c) for c in last.board), history=[]))
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
