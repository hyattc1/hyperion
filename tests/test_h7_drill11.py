"""H7, the drill 11 fixes (docs/drills/prompt-drill-11.md, "H7"): one test or more per item that changed code or prompts.
The fake kit I below is written from the kit's handout (docs/drills/drill11/kitI-README.md), cut down: module-level
start/table/act/done, one module a session, the loader that drops the bot folder from sys.path and its modules from
sys.modules right after the import, an Overtime BaseException at the limit, chips-now ints, seats relative to us, no
legal list, the full big blind after a short blind post, uncalled chips returned (`u`), and a hand end whose `won` is
chips collected. It settles one ordinary pot (the tranches are V-j's, in the engine)."""
from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from hyperion import ship

ROOT = Path(__file__).resolve().parents[1]
DRILLS = ROOT / "hyperion" / "drills"


# ---------------------------------------------------------------------------------------------- item 9
@pytest.mark.night
def test_ship_set_touches_only_the_value_it_sets(tmp_path):
    """`--set` rewrites the DIALS value only, `--bot` the SHIP string only, each in place: quotes, annotation and
    comments stay, and setting a value back gives the file back byte for byte (drill 11: --set dropped SHIP's comment)."""
    src = (ROOT / "hyperion" / "ship.py").read_text()
    copy = tmp_path / "ship.py"
    copy.write_text(src)
    ship.main(["--set", "survival"], path=copy)
    diff = [x for x in difflib.unified_diff(src.splitlines(), copy.read_text().splitlines(), lineterm="", n=0)
            if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    assert len(diff) == 2 and diff[0].startswith("-DIALS: dict = ") and diff[1].startswith("+DIALS: dict = {'r3."), diff
    assert ship.read_record(copy) == (ship.SHIP, ship.recipe("survival", ship.SHIP))
    ship.main(["--set", ""], path=copy)
    assert copy.read_text() == src
    ship.main(["--bot", "hero"], path=copy)
    line = [x for x in copy.read_text().splitlines() if x.startswith("SHIP")][0]
    assert line.startswith('SHIP = "hero"  # the composite (decisions entry "Composite bot")'), line
    assert ship.read_record(copy) == ("hero", ship.DIALS)
    ship.main(["--bot", ship.SHIP], path=copy)
    assert copy.read_text() == src
    ship.write_record(copy, ship.SHIP, dict(ship.DIALS))  # tools/pack.py's call with nothing new: nothing written
    assert copy.read_text() == src


# ---------------------------------------------------------------------------------------------- item 5
def _short_bb_obs(to_call: int):
    """Hand 1 at 10/20, three seats: seat 1 posted the small blind, seat 2 is all-in for a big blind of 10, we (seat
    0, the button) face `to_call`."""
    from hyperion.drills.adapter import make_observation

    return make_observation(hole=(48, 45), board=(), street=0, seat=0, button=0, stacks=[2000, 1990, 0],
                            bets=[0, 10, 10], in_hand=[True, True, True], pot=0, to_call=to_call, min_raise=40,
                            max_raise=2000, legal=["fold", "call", "raise"], hand_no=0, blinds=(10, 20))


@pytest.mark.night
def test_full_big_blind_rule_after_a_short_blind_is_not_a_violation():
    """Kit I: a big blind posted short (10 of 20, all-in) still has the others call the full 20. The conformance check
    knows it from `extras.full_bb_call`; without the flag it reports to_call_bets and names the flag."""
    from hyperion.core.types import Rules
    from hyperion.drills.conformance import check_observation

    plain = check_observation(_short_bb_obs(20), Rules(n_players=3))
    assert [x.split(":")[0] for x in plain] == ["to_call_bets"] and "full_bb_call" in plain[0], plain
    flagged = Rules(n_players=3, extras={"full_bb_call": True})
    assert check_observation(_short_bb_obs(20), flagged) == []
    assert [x.split(":")[0] for x in check_observation(_short_bb_obs(10), flagged)] == ["to_call_bets"]
    assert check_observation(_short_bb_obs(10), Rules(n_players=3)) == []  # the usual rule: call what was posted
    from hyperion.tablegen import rules_from_dict

    assert rules_from_dict({"extras": {"full_bb_call": True}}).extras["full_bb_call"] is True


# ---------------------------------------------------------------------------------------------- the fake kit I
import importlib.util  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import random  # noqa: E402
import shutil  # noqa: E402
import signal  # noqa: E402
import sys  # noqa: E402
from types import SimpleNamespace  # noqa: E402

KIT_SCHEDULE = ((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500))
KIT_POINTS = (16, 10, 6, 3, 1, 0, -1, -3)
KIT_RULES = {"starting_stack": 2000, "blind_levels": [list(b) for b in KIT_SCHEDULE], "hands_per_level": 25,
             "max_hands": 200, "n_players": 8, "payouts": list(KIT_POINTS), "extras": {"cap_places": "chips",
                                                                                       "full_bb_call": True}}
BOARD_AT = (0, 3, 4, 5)


class Overtime(BaseException):
    """Kit I's: raised inside the bot at a limit."""


def kit_load(folder: Path, name: str = "bot"):
    """Kit I's loader, cut down: bot.py imported with its folder first on sys.path, then the folder off sys.path and
    every module loaded from it out of sys.modules. A fresh module object each call (one per seat)."""
    folder = os.path.realpath(folder)
    sys.path.insert(0, folder)
    try:
        spec = importlib.util.spec_from_file_location(name, os.path.join(folder, "bot.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path[:] = [p for p in sys.path if os.path.realpath(p or ".") != folder]
        for k, m in list(sys.modules.items()):
            f = getattr(m, "__file__", None)
            if f and os.path.realpath(f).startswith(folder + os.sep):
                del sys.modules[k]
    return mod


def rank2(hole) -> tuple:
    """Kit I's two-card hand: a pair over any non-pair, then the higher card, then the lower; suits never count."""
    a, b = hole[0] >> 2, hole[1] >> 2
    return (1, a, a) if a == b else (0, max(a, b), min(a, b))


class FakeKitI:
    """Kit I's dealer, cut down from its handout: 8 seats, blinds 10/20 rising every 25 hands, no-limit with the min
    raise of the largest full raise and short all-ins that do not reopen, the full big blind after a short blind post,
    the top bet's unmatched part back at a street's end (`u`), no cards after the betting is over, and ONE pot (side
    pots by what each paid) to the best hand on the cards out (the tranches are the engine's, V-j). Seats are modules
    (start/table/act/done, timed with setitimer and an Overtime at the limit) or plain functions v -> int."""

    def __init__(self, seats, stacks=None, seed=1, limits=None):
        self.seats = list(seats)
        self.n = len(self.seats)
        self.stacks = list(stacks or [2000] * self.n)
        self.rng = random.Random(seed)
        self.limits = {"start": 20000, "table": 5000, "act": 2000, "done": 2000, **(limits or {})}
        self.counts = {"act": 0, "done": 0, "act_overtime": 0, "done_overtime": 0, "errors": 0, "sit": 0, "short_bb": 0}
        self.answers: list = []
        self.trap: dict = {}  # ("act" | "done", the call's index) -> line at which an Overtime is raised in it
        self.calls = {"act": 0, "done": 0}
        self.trapped = 0
        self.out = set()  # seats sitting the table out (table() failed)
        self.button = self.rng.randrange(self.n)
        self.chips = sum(self.stacks)

    # ---------------------------------------------------------------- the clock
    def _call(self, kind, fn, arg):
        """(cut, result): fn(arg) with an Overtime at the limit, or at the trapped line of this call."""
        idx = self.calls.get(kind, 0)
        self.calls[kind] = idx + 1
        line = self.trap.get((kind, idx))
        old = signal.signal(signal.SIGALRM, self._ring)
        try:
            try:
                signal.setitimer(signal.ITIMER_REAL, self.limits[kind] / 1000.0)
                if line:
                    count = [0]

                    def tr(frame, event, a):
                        if event == "line":
                            count[0] += 1
                            if count[0] == line:
                                self.trapped += 1
                                raise Overtime()
                        return tr

                    sys.settrace(tr)
                try:
                    return False, fn(arg)
                finally:
                    sys.settrace(None)
                    signal.setitimer(signal.ITIMER_REAL, 0)
            except Overtime:
                return True, None
        finally:
            signal.signal(signal.SIGALRM, old)

    @staticmethod
    def _ring(signum, frame):
        raise Overtime()

    # ---------------------------------------------------------------- views
    def _rel(self, xs, me):
        return tuple(xs[(me + r) % self.n] for r in range(self.n))

    def _log(self, events, me, upto):
        parts = [[] for _ in range(upto + 1)]
        for k, s, code, chips, allin in events:
            if k <= upto:
                parts[k].append(f"{(s - me) % self.n}{code}{chips if code in 'sbcru' else ''}{'!' if allin else ''}")
        return "/".join(" ".join(p) for p in parts)

    def _seatcodes(self, me):
        return "".join(("p" if self.stacks[s] > 0 else "a") if self.in_hand[s] else ("f" if self.dealt[s] else "x")
                       for s in self._rel(list(range(self.n)), me))

    # ---------------------------------------------------------------- a session
    def start(self):
        for s, b in enumerate(self.seats):
            if callable(getattr(b, "start", None)):
                cut, _ = self._call("start", b.start, SimpleNamespace(
                    data_dir=".", limits_ms=dict(self.limits), seats=self.n, starting_stack=2000, blinds=KIT_SCHEDULE,
                    hands_per_level=25, max_hands=200, points=KIT_POINTS, tables=1))
                if cut:
                    self.out.add(s)
        for s, b in enumerate(self.seats):
            if callable(getattr(b, "table", None)) and s not in self.out:
                cut, _ = self._call("table", b.table, SimpleNamespace(
                    table=0, seats=self.n, stacks=self._rel(self.stacks, s), button=(self.button - s) % self.n,
                    blinds=KIT_SCHEDULE, hands_per_level=25, max_hands=200, points=KIT_POINTS))
                if cut:
                    self.out.add(s)

    def play(self, hands: int, first_table: bool = True):
        if first_table:
            self.start()
        else:
            self.out.clear()
            for s, b in enumerate(self.seats):
                if callable(getattr(b, "table", None)):
                    cut, _ = self._call("table", b.table, SimpleNamespace(
                        table=1, seats=self.n, stacks=self._rel(self.stacks, s), button=(self.button - s) % self.n,
                        blinds=KIT_SCHEDULE, hands_per_level=25, max_hands=200, points=KIT_POINTS))
                    if cut:
                        self.out.add(s)
        for hand in range(1, hands + 1):
            live = [s for s in range(self.n) if self.stacks[s] > 0]
            if len(live) < 2:
                break
            if hand > 1:
                self.button = self._next(self.button, live)
            elif self.stacks[self.button] <= 0:
                self.button = self._next(self.button, live)
            self.hand(hand, *KIT_SCHEDULE[min((hand - 1) // 25, len(KIT_SCHEDULE) - 1)])
            assert sum(self.stacks) == self.chips

    def _next(self, s, seats):
        for d in range(1, self.n + 1):
            if (s + d) % self.n in seats:
                return (s + d) % self.n
        return s

    def _ask(self, s, v):
        b = self.seats[s]
        if not callable(getattr(b, "act", None)):
            return int(b(v))
        if s in self.out:
            self.counts["sit"] += 1
            return 0
        self.counts["act"] += 1
        if v.street == 0 and v.to_call and max(p[0] for p in v.paid) < v.bb:
            self.counts["short_bb"] += 1  # a blind posted short: the others still call the full big blind
        cut, out = self._call("act", b.act, v)
        if cut:
            self.counts["act_overtime"] += 1
            return 0
        self.answers.append(out)
        if type(out) is not int:
            self.counts["errors"] += 1
            return 0
        return out

    def hand(self, hand, sb, bb):
        n, rng = self.n, self.rng
        deck = list(range(52))
        rng.shuffle(deck)
        self.dealt = [self.stacks[s] > 0 for s in range(n)]
        self.in_hand = list(self.dealt)
        live = [s for s in range(n) if self.dealt[s]]
        hole = {s: (deck.pop(), deck.pop()) for s in live}
        cards = [deck.pop() for _ in range(5)]
        paid = [[0] * 4 for _ in range(n)]
        events = []
        start = list(self.stacks)

        def put(s, k, chips, code):
            chips = min(chips, self.stacks[s])
            self.stacks[s] -= chips
            paid[s][k] += chips
            events.append((k, s, code, chips, self.stacks[s] == 0 and code != "u"))

        bt = self.button
        sbs = bt if len(live) == 2 else self._next(bt, live)
        bbs = self._next(sbs, live)
        put(sbs, 0, sb, "s")
        put(bbs, 0, bb, "b")
        board: list = []
        street = 0
        for street in range(4):
            board = cards[:BOARD_AT[street]]
            if street == 0 or sum(1 for s in live if self.in_hand[s] and self.stacks[s] > 0) >= 2:
                first = self._next(bbs, live) if street == 0 else self._next(bt, live)
                self._round(hand, street, first, board, hole, paid, events, put, sb, bb)
            got = sorted(((paid[s][street], s) for s in range(n)), reverse=True)
            if got[0][0] > got[1][0]:  # the top bet's unmatched part goes back
                back, s = got[0][0] - got[1][0], got[0][1]
                self.stacks[s] += back
                paid[s][street] -= back
                events.append((street, s, "u", back, False))
            if sum(self.in_hand) == 1 or sum(1 for s in live if self.in_hand[s] and self.stacks[s] > 0) <= 1:
                break
        won = [0] * n
        alive = [s for s in range(n) if self.in_hand[s]]
        total = [sum(p) for p in paid]
        if len(alive) == 1:
            won[alive[0]] = sum(total)
        else:
            def strength(s):
                return rank2(hole[s]) if not board else (2, E.evaluate(list(hole[s]) + list(board)))

            from hyperion.core import eval as E

            prev, given = 0, 0
            levels = sorted({total[s] for s in alive})
            for i, lv in enumerate(levels):
                layer = sum(min(t, lv) - min(t, prev) for t in total)
                if i == len(levels) - 1:
                    layer = sum(total) - given  # folded chips above every live seat's join the top layer
                elig = [s for s in alive if total[s] >= lv]
                best = max(strength(s) for s in elig)
                win = [s for s in sorted(elig, key=lambda x: (x - bt - 1) % n) if strength(s) == best]
                for j, s in enumerate(win):
                    won[s] += layer // len(win) + (1 if j < layer % len(win) else 0)
                given += layer
                prev = lv
        for s in range(n):
            self.stacks[s] += won[s]
        assert sum(won) == sum(total)
        shown = {s: hole[s] for s in alive} if len(alive) > 1 else {}
        for s, b in enumerate(self.seats):
            if not self.dealt[s] or not callable(getattr(b, "done", None)) or s in self.out:
                continue
            sh = [shown.get(x) for x in range(n)]
            sh[s] = hole[s]
            awards = [[0] * n for _ in range(4)]
            for x in range(n):
                awards[street][x] = won[x]
            self.counts["done"] += 1
            cut, _ = self._call("done", b.done, SimpleNamespace(
                hand=hand, board=tuple(board), shown=self._rel(sh, s), paid=self._rel([tuple(p) for p in paid], s),
                awards=tuple(self._rel(a, s) for a in awards), won=self._rel(won, s), stacks=self._rel(self.stacks, s),
                log=self._log(events, s, street)))
            self.counts["done_overtime"] += cut
        self.last = SimpleNamespace(start=start, won=won, paid=paid, events=events)

    def _round(self, hand, k, first, board, hole, paid, events, put, sb, bb):
        n = self.n
        top = bb if k == 0 else 0  # preflop the full big blind is the bet, even after a short post
        full = bb  # the largest full bet or raise on this street (preflop the big blind)
        acted: set = set()  # seats that acted since the last full raise: they may call or fold, not raise
        s = first
        for _ in range(10 * n * n):
            need = [x for x in range(n) if self.in_hand[x] and self.stacks[x] > 0 and (x not in acted or paid[x][k] < top)]
            if not need or sum(self.in_hand) == 1:
                return
            while s not in need:
                s = (s + 1) % n
            to_call = max(0, min(top - paid[s][k], self.stacks[s]))
            others = any(self.in_hand[x] and self.stacks[x] > 0 for x in range(n) if x != s)
            if s in acted or not others or self.stacks[s] <= to_call:
                mr = 0
            else:
                mr = min(top + full - paid[s][k], self.stacks[s])
            v = SimpleNamespace(
                hole=hole[s], board=tuple(board), street=k, to_call=to_call, min_raise=mr, stack=self.stacks[s],
                stacks=self._rel(self.stacks, s), seats=self._seatcodes(s), paid=self._rel([tuple(p) for p in paid], s),
                tranches=tuple(sum(p[j] for p in paid) for j in range(4)), button=(self.button - s) % n, sb=sb, bb=bb,
                hand=hand, level=(hand - 1) // 25 + 1, log=self._log(events, s, k))
            a = self._ask(s, v)
            if a < to_call:
                if to_call > 0:
                    self.in_hand[s] = False
                    events.append((k, s, "f", 0, False))
                else:
                    events.append((k, s, "k", 0, False))
                acted.add(s)
            elif mr == 0 or a < mr:
                if to_call:
                    put(s, k, to_call, "c")
                else:
                    events.append((k, s, "k", 0, False))
                acted.add(s)
            else:
                put(s, k, a, "r")
                inc = paid[s][k] - top
                if inc >= full:
                    full, acted = inc, {s}
                else:
                    acted.add(s)  # a short all-in: no reopening
                top = paid[s][k]
            s = (s + 1) % n
        raise AssertionError("betting round did not end")


def station(v):
    return v.to_call


def make_raiser(seed):
    rng = random.Random(seed)

    def raiser(v):
        x = rng.random()
        if v.min_raise and x < 0.2:
            y = rng.random()
            return v.min_raise if y < 0.8 else v.stack if y > 0.95 else max(v.min_raise, sum(v.tranches))
        if v.to_call and x > 0.8:
            return -1
        return v.to_call

    return raiser


def _module_entry(tmp_path: Path, adapter: Path | None = None) -> Path:
    """submission/ for kit I: the module template as bot.py, the drill 11 player's adapter, kit I's rules."""
    d = tmp_path / "sub"
    d.mkdir()
    shutil.copy(DRILLS / "module_entry_template.py", d / "bot.py")
    shutil.copy(adapter or ROOT / "docs" / "drills" / "drill11" / "adapter.py", d / "adapter.py")
    (d / "rules_tonight.json").write_text(json.dumps(KIT_RULES))
    return d


@pytest.fixture
def clean_path(monkeypatch):
    """The entry pins its folder onto sys.path and its modules into hyperion.drills.adapter's lists: undone after."""
    from hyperion.drills import adapter as A

    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.setattr(A, "_KEEP", list(A._KEEP))
    monkeypatch.setattr(A, "_PINNED", dict(A._PINNED))
    yield


def _checked(mod):
    from hyperion.drills.conformance import checked

    return checked(mod.AD).conformance


# ---------------------------------------------------------------------------------------------- item 1
def folder(v):
    return -1


def _kit_table(mods, seed=5):
    """Our copies in seats 0 and 4, each right after a seat that starts with 15 chips and folds everything (it posts a
    big blind short within the first hands, and we are first to act after it); random raisers and a station."""
    seats = [mods[0], make_raiser(1), make_raiser(2), folder, mods[1] if len(mods) > 1 else make_raiser(4),
             make_raiser(5), station, folder]
    stacks = [2000, 2000, 2000, 15, 2000, 2000, 2000, 15]
    return FakeKitI(seats, stacks=stacks, seed=seed)


@pytest.mark.night
def test_module_entry_plays_the_fake_kit_i_clean(tmp_path, clean_path):
    """The template as kit I's bot.py, two copies in one table as the kit's simulator seats them (each its own module
    and start()), loaded by the kit's loader: right after the import the folder is off sys.path and `adapter` out of
    sys.modules, and every later call still works (all built at import, the package pinned). Two tables in one
    session: every answer an int, 0 errors on the entry's line, 0 conformance violations (the full big blind after a
    short blind among them, with extras.full_bb_call), folds, calls and raises; the hand ends' deltas sum to 0
    (won read as chips collected)."""
    d = _module_entry(tmp_path)
    mods, reps = [], []
    for i in range(2):
        m = kit_load(d, name=f"bot{i}")
        assert os.path.realpath(d) not in [os.path.realpath(p or ".") for p in sys.path]
        assert "adapter" not in sys.modules and m.ERRORS == {}, m.ERRORS
        mods.append(m)
        reps.append(_checked(m))
    eng = _kit_table(mods)
    eng.play(40)
    eng2 = FakeKitI(eng.seats, stacks=[2000] * 8, seed=6)
    eng2.calls = eng.calls
    eng2.play(30, first_table=False)
    for m, rep in zip(mods, reps):
        assert m.ERRORS == {}, m.ERRORS
        assert rep.clean, rep.summary()
        assert rep.actions["fold"] and rep.actions["raise"] and (rep.actions["call"] or rep.actions["check"])
        assert m.AD.fallbacks == 0
    for e in (eng, eng2):
        assert e.counts["errors"] == 0 and e.counts["sit"] == 0 and all(type(a) is int for a in e.answers)
        assert e.counts["done"] > 20
    assert eng.counts["short_bb"] >= 1, eng.counts  # the full-big-blind rule was played, and conformance knew it


@pytest.mark.night
def test_module_entry_counts_a_won_read_as_net(tmp_path, clean_path):
    """TODO 3a read the wrong way round (kit G's line, deltas = won, on kit I's chips collected) shows on the error line
    as `deltas_sum`, hand after hand, instead of feeding the bot wrong stacks in silence."""
    d = _module_entry(tmp_path)
    src = (d / "bot.py").read_text()
    line = "    deltas = [int(w) - int(sum(p)) for w, p in zip(h.won, h.paid)]  # collected (kit I)\n"
    assert line in src and "net change" in src and "chips collected or net change?" in src
    (d / "bot.py").write_text(src.replace(line, "    deltas = [int(w) for w in h.won]\n"))
    m = kit_load(d, name="bot_net")
    assert m.ERRORS == {}  # the warm-up's own count is dropped
    eng = _kit_table([m])
    eng.play(25)
    assert m.ERRORS["deltas_sum"] >= 10, m.ERRORS


@pytest.mark.night
def test_every_template_asks_how_to_read_won():
    """Every entry, adapter and gate seat template's hand end asks "won: chips collected or net change?"; the entry
    templates give both formulas."""
    names = sorted(p.name for p in DRILLS.glob("*template*.py"))
    assert len(names) == 10, names
    for name in names:
        text = (DRILLS / name).read_text()
        assert "chips collected or net change?" in text, name
    for name in ("entry_template.py", "module_entry_template.py"):
        text = (DRILLS / name).read_text()
        assert "deltas = [int(w) for w in" in text and "deltas = [int(w) - int(sum(p)) for w, p in zip(" in text, name


def _tiny_bot(folder: Path, lazy: bool) -> None:
    folder.mkdir()
    (folder / "helper.py").write_text("def answer(v):\n    return v.to_call\n")
    if lazy:
        (folder / "bot.py").write_text("def act(v):\n    import helper\n    return helper.answer(v)\n")
    else:
        (folder / "bot.py").write_text("import helper\n\n\ndef act(v):\n    return helper.answer(v)\n")


@pytest.mark.night
@pytest.mark.parametrize("loader", ["kit", "seat"])
def test_the_loader_drops_the_folder_and_its_modules(tmp_path, clean_path, loader):
    """Kit I's loader (and the gate seat's copy of it): after the import the bot folder is off sys.path and its helper
    out of sys.modules, so an import inside act() fails while one at the top of bot.py keeps working."""
    spec = importlib.util.spec_from_file_location("h7_mseat", DRILLS / "module_gate_seat_template.py")
    seat_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seat_mod)
    v = SimpleNamespace(to_call=20)
    for lazy in (False, True):
        f = tmp_path / ("lazy" if lazy else "eager")
        _tiny_bot(f, lazy)
        mod = kit_load(f) if loader == "kit" else seat_mod.load_entry(str(f / "bot.py"))
        assert "helper" not in sys.modules
        assert os.path.realpath(f) not in [os.path.realpath(p or ".") for p in sys.path]
        if lazy:
            with pytest.raises(ModuleNotFoundError):
                mod.act(v)
        else:
            assert mod.act(v) == 20


def test_an_overtime_anywhere_in_act_or_done_leaves_the_next_call_clean(tmp_path, clean_path):
    """Kit I raises Overtime (a BaseException) inside the bot at the limit. Raised at a spread of lines inside 14 act()
    and 8 done() calls of one table (sys.settrace, so it lands where the line count says, whatever the box's load): the
    template never swallows it (the call ends), and every later call answers an int with nothing swallowed, no
    adapter fallback and no bot error."""
    d = _module_entry(tmp_path)
    m = kit_load(d, name="bot_ot")
    eng = _kit_table([m], seed=9)
    ks = [2, 5, 13, 40, 120, 400, 1500, 6000]
    eng.trap = {("act", 3 + 4 * i): ks[i % len(ks)] for i in range(14)}
    eng.trap.update({("done", 2 + 3 * i): ks[(i + 3) % len(ks)] for i in range(8)})
    eng.play(45)
    assert eng.trapped >= 12, eng.trapped
    assert eng.counts["act_overtime"] + eng.counts["done_overtime"] == eng.trapped
    assert eng.counts["errors"] == 0 and all(type(a) is int for a in eng.answers)
    assert m.ERRORS == {}, m.ERRORS
    assert m.AD.fallbacks == 0 and m.AD.bot.safe.errors == 0
    assert eng.calls["act"] > 3 + 4 * 13 + 10  # decisions after the last trap


# ---------------------------------------------------------------------------------------------- item 2
def _seat_module():
    spec = importlib.util.spec_from_file_location("h7_mseat2", DRILLS / "module_gate_seat_template.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def alarm():
    old = signal.getsignal(signal.SIGALRM)
    yield
    signal.setitimer(signal.ITIMER_REAL, 0)
    signal.signal(signal.SIGALRM, old)


POSTS = [[1, "sb", 10], [2, "bb", 20]]
ROWS = [[3, "raise", 60, 0, 60], [4, "fold", 0, 0, 0], [5, "fold", 0, 0, 0], [6, "fold", 0, 0, 0], [7, "fold", 0, 0, 0],
        [0, "call", 0, 0, 60], [1, "fold", 0, 0, 0], [2, "call", 0, 0, 40],
        [2, "check", 0, 1, 0], [3, "raise", 100, 1, 100], [0, "raise", 300, 1, 300], [2, "fold", 0, 1, 0]]


def _flop_state() -> dict:
    """The gate's dealer state: we are seat 3, the button 0; we opened to 60, the button and the big blind called; on
    the flop the big blind checked, we bet 100, the button raised to 300, the big blind folded."""
    return {"hole": (48, 45), "board": (12, 30, 7), "street": 1, "seat": 3, "button": 0,
            "stacks": [1640, 1990, 1940, 1840, 2000, 2000, 2000, 2000], "bets": [300, 0, 0, 100, 0, 0, 0, 0],
            "in_hand": [True, False, False, True, False, False, False, False], "pot": 190, "to_call": 200,
            "min_raise": 500, "max_raise": 1940, "legal": {"fold", "call", "raise"}, "hand_no": 0, "blinds": (10, 20),
            "history": [tuple(r) for r in ROWS], "posts": [tuple(p) for p in POSTS], "discards": {}}


@pytest.mark.night
def test_module_seat_builds_kit_i_state_answer_and_hand_end(alarm):
    """The seat's `v` is kit I's (seats relative to us, chips per street, the log with the posts and chips added), the
    drill 11 adapter reads it with 0 conformance violations, the int answer maps to the gate's (kind, raise-to total),
    and the hand end's `won` is chips collected, with the bet nobody called given back as `u`."""
    from hyperion.drills.cheapbot import CheapBot
    from hyperion.drills.conformance import check_observation
    from hyperion.tablegen import rules_from_dict

    S = _seat_module()
    got = []
    bot = SimpleNamespace(act=lambda v: 0, done=got.append, __file__=str(DRILLS / "x.py"))
    seat = S.Seat(bot, None)
    seat.start(3, 8, 2000, (10, 20))
    st = _flop_state()
    v = seat.native(st)
    assert v.log == "6s10 7b20 0r60 1f 2f 3f 4f 5c60 6f 7c40/7k 0r100 5r300 7f"
    assert v.seats == "pffffpff" and v.button == 5 and v.hand == 1 and v.level == 1
    assert v.paid[0] == (60, 100, 0, 0) and v.paid[5] == (60, 300, 0, 0) and v.paid[6] == (10, 0, 0, 0)
    assert v.tranches == (190, 400, 0, 0) and v.to_call == 200 and v.min_raise == 400 and v.stack == 1840
    assert v.stacks[0] == 1840 and v.stacks[5] == 1640
    spec = importlib.util.spec_from_file_location("h7_ad11", ROOT / "docs" / "drills" / "drill11" / "adapter.py")
    ad11 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ad11)
    rules = rules_from_dict(KIT_RULES)
    obs = ad11.TonightAdapter(CheapBot(), rules).to_observation(v)
    assert check_observation(obs, rules) == [] and obs.pot == 190 and obs.min_raise == 500
    assert [seat.parse(x, st) for x in (0, 199, 200, 399, 400, 5000)] == [
        ("fold", 0), ("fold", 0), ("call", 300), ("call", 300), ("raise", 500), ("raise", 1940)]
    for bad in (True, "200", 200.0, None):
        with pytest.raises(ValueError):
            seat.parse(bad, st)
    rows = ROWS + [[3, "call", 0, 1, 200], [0, "raise", 500, 2, 500], [3, "fold", 0, 2, 0]]
    seat.end(0, -360, {"deltas": [430, -10, -60, -360, 0, 0, 0, 0], "board": [12, 30, 7, 40], "showdown": {},
                       "history": rows, "posts": POSTS})
    (h,) = got
    assert h.log.endswith("/7k 0r100 5r300 7f 0c200/5r500 0f 5u500"), h.log
    assert h.won[0] == 0 and h.won[5] == 790 and sum(h.won) == 790
    assert h.paid[5] == (60, 300, 0, 0) and h.paid[0] == (60, 300, 0, 0)
    assert [w - sum(p) for w, p in zip(h.won, h.paid)] == [-360, 0, 0, 0, 0, 430, -10, -60]  # the gate's deltas
    assert h.shown[0] == (48, 45) and h.stacks[0] == 1640 and h.stacks[5] == 2430 and h.hand == 1


def _busy(ms):
    import time

    t = time.perf_counter()
    while time.perf_counter() - t < ms / 1000.0:
        pass


@pytest.mark.night
def test_module_seat_raises_the_kits_overtime_and_catches_a_bot_that_swallows_it(alarm):
    """At the act limit the seat raises Overtime inside the bot: a bot that lets it end the call answers the kit's 0 and
    is counted; one that catches it (except BaseException) and runs on is an error the gate fails on. done() the same,
    counted. A 1 ms limit against a 40 ms loop: the timer fires whatever the load."""
    S = _seat_module()

    def honest(v):
        _busy(40)
        return 999

    def swallow(v):
        try:
            _busy(40)
        except BaseException:  # noqa: BLE001 - the bug under test
            pass
        return 999

    st = _flop_state()
    seat = S.Seat(SimpleNamespace(act=honest, done=lambda h: _busy(40), __file__=str(DRILLS / "x.py")), None)
    seat.start(3, 8, 2000, (10, 20))
    assert seat.call(seat.native(st)) == S.SAFE and seat.counts["act_overtime"] == 1
    seat.end(0, 0, {"deltas": [0] * 8, "board": [], "showdown": {}, "history": [], "posts": []})
    assert seat.counts["done_overtime"] == 1 and seat.gate_counts == {"act_overtime": 1, "done_overtime": 1}
    bad = S.Seat(SimpleNamespace(act=swallow, __file__=str(DRILLS / "x.py")), None)
    bad.start(3, 8, 2000, (10, 20))
    with pytest.raises(RuntimeError, match="Overtime"):
        bad.call(bad.native(st))


def _gate_and_pack():
    spec = importlib.util.spec_from_file_location("h7_gate", ROOT / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)
    spec = importlib.util.spec_from_file_location("h7_pack", ROOT / "tools" / "pack.py")
    pack = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pack
    spec.loader.exec_module(pack)
    return gate, pack


def _gate_cfg(gate, tmp_path, pkg):
    shutil.copy(DRILLS / "module_gate_seat_template.py", tmp_path / "gate_seat.py")
    scratch = tmp_path / "cwd"
    scratch.mkdir(exist_ok=True)
    return gate.Config(pkg=pkg, entry="bot.py", kit="seat", kit_dir=Path("-"), scratch=str(scratch),
                       seat_file=tmp_path / "gate_seat.py")


def test_the_gate_plays_the_packed_module_entry_as_the_kit_loads_it(tmp_path):
    """tools/gate.py with the module seat on the packed template: gate_host loads bot.py through the seat's load_entry
    (the folder off sys.path and the vendored hyperion out of sys.modules right after the import), every call runs
    under the kit's Overtime; one table plays clean."""
    from hyperion.sim import bestiary as B
    from hyperion.tablegen import rules_from_dict

    gate, pack = _gate_and_pack()
    d = _module_entry(tmp_path)
    dest = tmp_path / "pkg"
    pack.build(dest, d / "bot.py", [d / "adapter.py", d / "rules_tonight.json"], True, None)
    pack.keep_built_modules(dest, *pack.record_bot(dest, None, None))  # as pack's main does after a --slim build
    assert not (dest / "hyperion" / "drills" / "module_entry_template.py").exists()
    cfg = _gate_cfg(gate, tmp_path, dest)
    pkg, _ = gate.play(cfg, B.field_names("realistic"), 1, 3, rules_from_dict(KIT_RULES), None, "measure", "sim")
    assert pkg.fatal is None, pkg.notes
    assert pkg.decisions > 10 and pkg.stats.exceptions == 0 and pkg.stats.illegal == 0, (pkg.stats.last_error, pkg.notes)
    assert pkg.lifecycle == 0, pkg.notes


def test_the_gate_module_seat_fails_a_lazy_import(tmp_path):
    """The same seat on a package whose act() imports a helper lazily: the kit's loader took the folder away, so every
    decision raises (the gate counts the exceptions: GATE FAIL); with the import at the top, none."""
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B

    gate, _ = _gate_and_pack()
    for lazy in (False, True):
        f = tmp_path / ("lazy" if lazy else "eager")
        _tiny_bot(f, lazy)
        cfg = _gate_cfg(gate, tmp_path, f)
        pkg, _ = gate.play(cfg, B.field_names("realistic"), 1, 3, Rules(), None, "measure", "sim")
        assert pkg.fatal is None and pkg.decisions > 5, pkg.notes
        if lazy:
            cut = pkg.counts.get("act_overtime", 0)  # a module search slower than 1 ms on this box: the kit's cut
            assert pkg.stats.exceptions + cut == pkg.decisions and "helper" in (pkg.stats.last_error or ""), (
                pkg.stats.last_error, pkg.counts)
        else:
            assert pkg.stats.exceptions == 0 and pkg.stats.illegal == 0, (pkg.stats.last_error, pkg.notes)


# ---------------------------------------------------------------------------------------------- the docs: 3, 4, 6, 7, 8, 10
def _read(rel: str) -> str:
    return (ROOT / rel).read_text()


def _flat(text: str) -> str:
    return " ".join(text.split())


@pytest.mark.night
def test_the_checker_rule_on_a_loaded_box_is_stated():
    """Item 3: the organisers' checker passes on its CPU clock with 0 errors and timeouts no worse than the kit's own
    sample bots in the same run, the load noted; with no CPU clock, the same rule on the wall clock."""
    p02, p04 = _flat(_read("docs/prompts/02-adapter-and-cheap-bot.md")), _flat(_read("docs/prompts/04-wire-hero.md"))
    stage2 = _flat(_read("PLAYBOOK.md").split("### Stage 2: ADAPT", 1)[1].split("### Stage 3", 1)[0])
    for text in (p02, stage2):
        assert "CPU clock" in text and "0 errors" in text and "no CPU clock" in text
        assert "no worse than the worst of the kit's sample bots in the same run" in text
    assert "prompt 02 step 6's rule" in p04 and "--clock cpu" in p02


def test_the_night_subset_is_marked_and_has_no_timing_test():
    """Item 4: `pytest -m night` collects the adapter, conformance, pack, switch and template tests (about a minute at
    load 18: 153 tests, 25-52 s at load 15-20 on this box) and no wall-clock test; prompts 00 and 02 run it."""
    import subprocess

    def collect(expr: str) -> list[str]:
        r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--collect-only", "-m",
                            expr], cwd=ROOT, capture_output=True, text=True, timeout=600)
        return [x for x in r.stdout.splitlines() if "::" in x]

    ids = collect("night")
    assert 100 <= len(ids) <= 220, len(ids)
    for part in ("test_nightof_conformance.py::", "test_nightof_history.py::", "test_kit_shapes.py::",
                 "test_nightof_pack.py::test_pack_builds_verifies_zips_and_logs",
                 "test_h5_drill9.py::test_the_entry_template_survives", "test_h6_drill10.py::test_process_entry_round",
                 "test_h7_drill11.py::test_module_entry_plays", "test_ship.py::test_recipes_resolve"):
        assert any(part in x for x in ids), part
    assert collect("night and timing") == []
    assert '"night: ' in _read("pyproject.toml")
    for rel in ("docs/prompts/00-briefing.md", "docs/prompts/02-adapter-and-cheap-bot.md"):
        assert "-m night" in _read(rel), rel


@pytest.mark.night
def test_a_latency_recipe_is_kept_by_the_kits_simulator():
    """Item 6: prompt 04 step 4 and prompt 06 keep a latency recipe only by the kit's own simulator, paired."""
    p04, p06 = _flat(_read("docs/prompts/04-wire-hero.md")), _flat(_read("docs/prompts/06-windows.md"))
    assert "only when the kit's own simulator shows it" in p04 and "tools/latency.py alone is not the check" in p04
    assert "verified in the kit's own simulator" in p06 and "not by tools/latency.py alone" in p06


@pytest.mark.night
def test_one_keep_rule_written_once_and_pointed_at():
    """Item 7: prompt 05 states the keep rule (paired on the same tables, our sim with --variant else the kit's, the
    estimate above zero, nothing down beyond its 95% interval, 600 paired tables or more); the three phrasings that
    disagreed are gone, and PLAYBOOK Stage 5, hard rule 6, the stage table, prompt 00 and the prompts README point
    at it."""
    p05 = _flat(_read("docs/prompts/05-variant-patch.md"))
    rule = p05.split("**The keep rule**", 1)[1].split("Dials, in our simulator", 1)[0]
    for words in ("paired", "`--variant`", "the kit's own simulator", "600 paired tables", "above zero",
                  "beyond its 95% interval"):
        assert words in rule, words
    docs = {rel: _flat(_read(rel)) for rel in ("PLAYBOOK.md", "docs/prompts/00-briefing.md", "docs/prompts/README.md",
                                               *(f"docs/prompts/{p.name}" for p in (ROOT / "docs" / "prompts").glob("0*.md")))}
    for rel, text in docs.items():
        for old in ("rise by more than half", "did not drop beyond the confidence interval", "points did not drop beyond CI",
                    "the score did not drop", "When the sim cannot see what a patch does"):
            assert old not in text, (rel, old)
    assert p05.count("**The keep rule**") == 1
    pb = docs["PLAYBOOK.md"]
    stage5 = pb.split("### Stage 5: PATCH", 1)[1].split("### Submit and freeze", 1)[0]
    rules = pb.split("## 7. Hard rules", 1)[1].split("## 8.", 1)[0]
    assert "the keep rule** in `05-variant-patch.md`" in stage5 and "keep rule (`05-variant-patch.md`)" in rules
    assert "The keep rule in `05-variant-patch.md`" in pb
    assert "keep rule" in docs["docs/prompts/00-briefing.md"] and "keep rule" in docs["docs/prompts/README.md"]


@pytest.mark.night
def test_the_stage_0_clause_is_skipped_on_a_solo_night():
    """Item 8: with no Stage 0 number under tonight's rules, prompt 04 skips the clause and notes it."""
    p04 = _flat(_read("docs/prompts/04-wire-hero.md"))
    assert "No Stage 0 number under tonight's rules" in p04 and "Stage 0 clause skipped" in p04
    assert "skipped, and noted, when nobody re-measured Stage 0 under tonight's rules" in _flat(_read("PLAYBOOK.md"))
    assert "prompt 04 skips its Stage 0 clause" in _flat(_read("docs/prompts/01-rule-sheet.md"))


@pytest.mark.night
def test_prompt_05_has_a_street_settled_pots_section():
    """Item 10: prompt 05's payoff section names street-settled pots, points at the catalog, and gives drill 11's twin
    (the adapter's twin_hole) as the first move, measured by the keep rule."""
    p05 = _flat(_read("docs/prompts/05-variant-patch.md"))
    sec = p05.split("Pots settled by street", 1)[1].split("- Point tables", 1)[0]
    assert "--variant" in sec and "twin_hole" in sec and "keep rule" in sec and "kit's simulator" in sec
    assert "def twin_hole(" in _read("docs/drills/drill11/adapter.py")
