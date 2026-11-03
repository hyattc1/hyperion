"""Gate seat for an EVENT-DRIVEN kit: copy to `submission/gate_seat.py`, fill the TODOs, and run
`python tools/gate.py dist/submission.zip --kit submission/gate_seat.py --entry player.py --tables 100 --rules
rules_tonight.json` (tools/gate_host.py loads class Seat; only `call` is timed).

The gate sends the simulator's state at each of our decisions (a dealer dict: hole, board, street, seat, button,
stacks, bets, in_hand, pot of the previous streets, to_call, min_raise / max_raise as raise-to totals, legal,
hand_no, blinds, history rows [seat, kind, total, street, put], posts [[seat, "ante" | "sb" | "bb" | "straddle",
chips]]) and at each hand end the result (every seat's deltas, the board, the showdown, the history, the posts).
A STATE kit's seat (class Seat from tools/gate_host.KitA) builds the kit's own log from those: `by_street` below groups
them by street, the posts first, with the chips each action put in and the seat's street total after it, so the log
can be per street, in chips added or in totals, blinds included, as the kit writes it (drills 8 and 9 sent one
street's log, and the gate never tested the adapter's per-street parsing; `kit_g_log` is drill 9's kit's shape, worked
and tested in tests/test_h5_drill9.py). An event kit never sends a state, so this seat writes the state into the entry's
EventTracker as the kit's events would have left it (`native`), and the kit's own simulator, not the gate, is what
exercises the entry's event bookkeeping. The rest goes through the entry's real methods: the table start, the
decision (timed), and the hand end with what the kit's hand end carries, OUTSIDE the timed call, as the kit runs it.
Drill 7's first seat deferred the bot's hand end into the next timed decision (2.1% timeouts, GATE FAIL) and its
second skipped every other seat's chips (wrong stacks): this template does neither.

The defaults fit hyperion/drills/event_player_template.py's Player (and the fake event kit's request and reply);
the worked example's seat is in tests/test_drills_events.py.
"""
from __future__ import annotations

from hyperion.core.types import Action, ActionKind

_KIND = {"fold": ActionKind.FOLD, "check": ActionKind.CHECK, "call": ActionKind.CALL, "raise": ActionKind.RAISE}


class Seat:
    # TODO 1  the entry's class and method names (the kit's), and where it keeps its EventAdapter
    ENTRY_CLASS = "Player"
    TABLE_START = "table_start"
    HAND_END = "hand_end"
    DECIDE = "decide"
    ADAPTER = "a"
    KIT_HAND_BASE = 1  # TODO 2  the kit's first hand number (ours is 0)

    def __init__(self, module, kit):
        self.mod, self.kit, self.p = module, kit, None
        self.n = 8

    def _adapter(self):
        return getattr(self.p, self.ADAPTER)

    # ---------------------------------------------------------------- lifecycle
    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.n = n
        self.p = getattr(self.mod, self.ENTRY_CLASS)()
        getattr(self.p, self.TABLE_START)(self.table_payload(seat, n, stack, blinds))

    def table_payload(self, seat: int, n: int, stack: int, blinds) -> dict:
        # TODO 3  what the kit's table start carries
        return {"seat": seat, "players": n, "stack": stack, "blinds": list(blinds)}

    # ---------------------------------------------------------------- a decision
    def native(self, st: dict):
        """The tracker as the kit's events would have left it at this decision, the bot's deferred hand-end work done
        (the kit's next event would have run it), and the kit's request. Untimed."""
        a = self._adapter()
        a.t.load(hand_no=st["hand_no"], button=st["button"], blinds=st["blinds"], hole=st["hole"], board=st["board"],
                 stacks=st["stacks"], bets=st["bets"], in_hand=st["in_hand"], pot_prev=st["pot"],
                 history=_history(st.get("history", ())), seat=st["seat"])
        a.idle()
        return self.request(st)

    def request(self, st: dict):
        # TODO 4  the kit's decision request for this state (the fake event kit's: moves with call cost, raise-to
        #   min / max, the hand number and board size the entry's request_keys checks)
        legal = st["legal"]
        moves: dict = {}
        for k in ("fold", "check"):
            if k in legal:
                moves[k] = {}
        if "call" in legal:
            moves["call"] = {"cost": int(st["to_call"])}
        if "raise" in legal:
            moves["raise"] = {"min": int(st["min_raise"]), "max": int(st["max_raise"])}
        return {"hand": int(st["hand_no"]) + self.KIT_HAND_BASE, "board_size": len(st["board"]), "moves": moves}

    def call(self, native):
        return getattr(self.p, self.DECIDE)(native)

    def parse(self, reply, st: dict):
        # TODO 5  the kit's reply -> (kind, raise-to total); anything else raises (the gate counts it illegal)
        mv = reply["move"]
        if mv == "raise":
            to = reply["to"]
            if type(to) is not int:
                raise ValueError("raise amount not an int")
            return "raise", to
        if mv == "call":
            return "call", int(st["bets"][st["seat"]]) + int(st["to_call"])
        if mv in ("check", "fold"):
            return mv, 0
        raise ValueError(f"unknown move {mv!r}")

    # ---------------------------------------------------------------- the hand end, untimed
    def end(self, hand_no: int, delta: int, result: dict | None) -> None:
        """The rest of the hand (actions after our last decision, the final board, the showdown) into the tracker,
        then the entry's own hand-end method with what the kit's hand end carries."""
        a = self._adapter()
        t = a.t
        r = result or {}
        if t.hand_no != hand_no:  # a hand with no decision of ours (a walk): the kit's hand start would have come
            t.hand_no, t.shown, t.log = hand_no, {}, []
        if r.get("history") is not None:
            t.log = _history(r["history"])
        if r.get("board") is not None:
            t.cards = tuple(r["board"])
        t.showdown({int(s): tuple(h) for s, h in (r.get("showdown") or {}).items()})
        getattr(self.p, self.HAND_END)(self.end_payload(hand_no, delta, r))

    def end_payload(self, hand_no: int, delta: int, r: dict) -> dict:
        # TODO 6  what the kit's hand end carries, from the gate's result: here every seat's net (a kit with only
        #   our own: {seat: delta} for ours alone; a kit whose `won` is chips collected, as kit I's: delta + what the
        #   seat paid this hand, module_gate_seat_template.py's end)
        deltas = r.get("deltas") or []
        return {"hand": hand_no + self.KIT_HAND_BASE, "net": {str(s): int(d) for s, d in enumerate(deltas)}}


def by_street(rows, posts=(), upto: int | None = None) -> list[list[tuple]]:
    """The gate's tagged history rows [seat, kind, total, street, put] and the hand's posts [seat, kind, chips] -> one
    list per street (at least `upto` + 1 of them: pass the state's street, as a kit's log has a segment for the street
    in play before anyone acts on it), street 0 opening with the posts. Each entry is (seat, kind, to, put): `put` the
    chips it added, `to` the seat's chips in on that street after it (a raise's raise-to total; an ante's 0, antes are
    dead money). Seats are the gate's (absolute); a kit that numbers from us takes (seat - me) % n."""
    streets: list[list[tuple]] = [[]]
    have: dict = {}
    for seat, kind, chips in posts or ():
        seat, chips = int(seat), int(chips)
        if kind != "ante":
            have[seat] = have.get(seat, 0) + chips
        streets[0].append((seat, str(kind), have.get(seat, 0) if kind != "ante" else 0, chips))
    for row in rows or ():
        seat, kind, street, put = int(row[0]), str(row[1]), int(row[3]), int(row[4])
        while len(streets) <= street:
            streets.append([])
            have = {}
        have[seat] = have.get(seat, 0) + put
        streets[street].append((seat, kind, have[seat], put))
    while upto is not None and len(streets) <= upto:
        streets.append([])
    return streets


KIT_G_CODE = {"sb": "s", "bb": "b", "fold": "f", "check": "k", "call": "c", "raise": "r"}


def kit_g_log(rows, posts, me: int, n: int, upto: int | None = None) -> str:
    """Drill 9's kit G log, the worked example: seats as offsets from us, one segment per street joined by "/", each
    action "<offset><code><chips added>" (s, b, c, r carry chips; f, k none), the blinds posted first."""
    out = []
    for street in by_street(rows, posts, upto):
        toks = []
        for seat, kind, _to, put in street:
            code = KIT_G_CODE.get(kind)
            if code is not None:
                toks.append(f"{(seat - me) % n}{code}{put if code in 'sbcr' else ''}")
        out.append(",".join(toks))
    return "/".join(out)


def _history(rows) -> list:
    """The gate's history rows [seat, kind, total, ...] -> [(seat, Action)] (raise totals; discards skipped)."""
    out = []
    for row in rows:
        seat, kind, total = row[0], row[1], row[2]
        k = _KIND.get(kind)
        if k is not None:
            out.append((int(seat), Action(k, int(total) if k is ActionKind.RAISE else 0)))
    return out
