#!/usr/bin/env python
"""Child side of tools/gate.py: one packaged bot in a fresh `python -I -B` process, imported the way the
organisers would import it. Standard library only, and it never imports this repo.

sys.path is the package directory first, then the interpreter's own paths, then the kit directory, so
`import hyperion` resolves inside the package and `import kit` finds the kit module (the rules promise it
is importable). The working directory is a scratch directory, not the package.

    gate_host.py serve  <kind> <package_dir> <entry.py> <kit_dir> [<seat_file.py>]
        kind a | b      the fake kits' in-process interfaces (class Agent / module-level decide)
        kind seat       a seat file for tonight's kit (class Seat, same five methods as KitA below)
        kind direct     the package's own bot with no adapter: hyperion.ship.make_bot() (the bot and dials the
                        package records), or hyperion.strategy.hero.make_bot() in a package without ship.py
        One JSON object per line on the saved stdout, requests on stdin. The bot's own prints go to stderr.
    gate_host.py launch <package_dir> <entry.py> <kit_dir> [args...]
        subprocess kits (c, d): run the entry as __main__ with argv = [entry, *args]; stdin and stdout stay
        the kit protocol's.

The state each request carries is the fake kits' dealer dict (hyperion/drills/fakekits/_table.py): hole,
board, street, seat, button, stacks, bets, in_hand, pot (previous streets), to_call, min_raise and
max_raise (raise-to totals), legal (lowercase names), hand_no, blinds, history [[seat, kind, total]],
discards {seat: card}. Cards are ints, rank * 4 + suit. A seat file's state (kind seat) has more, for a kit whose log
is per street or counts chips: each history row is [seat, kind, total, street, put] (the street it was on, the chips
it put in) and `posts` lists the hand's forced bets [[seat, "ante" | "sb" | "bb" | "straddle", chips]];
hyperion/drills/gate_seat_template.py's `by_street(rows, posts)` groups them by street, posts first.

Writing a seat file for tonight's kit (in-process kits only): copy class KitA, rename it Seat, and change
`native` (dealer dict -> the kit's state object, using the kit's own classes), `parse` (the bot's reply ->
(kind, raise-to total), kind in fold/check/call/raise/discard) and the lifecycle calls. Only `call` is timed.
Build the kit's log in its own shape (per street, chips added, the blinds posted) from the tagged rows and posts:
a seat that sends one street's log never tests the adapter's per-street parsing (drills 8 and 9 did).
A seat's `end(hand_no, delta, result)` gets the hand's `result` dict (deltas of every seat, board, showdown
{seat: cards}, the tagged history rows, posts): pass on what the kit's own hand end carries, never more. An
event-driven kit (no state snapshot): hyperion/drills/gate_seat_template.py. A process kit (the bot is its own process on
JSON lines, drill 10's kit H): hyperion/drills/process_gate_seat_template.py, whose module-level `PROCESS = True` makes
this host hand the seat the entry's path instead of importing it; the seat launches the entry and plays the real stdin
loop through a pipe, and its `close()` (called at the gate's close) ends the bot process. A module-function kit (plain
module-level functions, one module a session, drill 11's kit I): hyperion/drills/module_gate_seat_template.py, whose
`load_entry(path)` this host calls instead of its own import, so the entry is loaded as the kit's loader loads it (the
folder off sys.path and its modules out of sys.modules right after); a seat's `gate_counts` dict goes back with the
close and the gate prints the sums.
"""
from __future__ import annotations

import importlib.util
import json
import os
import runpy
import sys
import time
import types


def _setup_path(pkg: str, kit_dir: str) -> None:
    sys.path.insert(0, pkg)
    if kit_dir and kit_dir != "-":
        sys.path.append(kit_dir)


def _load_file(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _fix_state(st: dict) -> dict:
    """JSON turned tuples into lists and int keys into strings; give the kit code the dealer's types back."""
    st["hole"] = tuple(st["hole"])
    st["board"] = tuple(st["board"])
    st["legal"] = set(st["legal"])
    st["blinds"] = tuple(st["blinds"])
    st["history"] = [tuple(h) for h in st.get("history", ())]
    if "posts" in st:
        st["posts"] = [tuple(p) for p in st["posts"]]
    st["discards"] = {int(k): v for k, v in (st.get("discards") or {}).items()}
    return st


# ------------------------------------------------------------------ seats: one per in-process interface

class KitA:
    """Fake kit A: submission.py defines class Agent; act(GameState) -> "FOLD" | "CHECK" | "CALL" |
    "RAISE:<total>" | "DISCARD:<i>". One Agent per table, as the kit's runner does."""

    def __init__(self, module, kit):
        self.mod, self.kit, self.agent = module, kit, None

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        self.agent = self.mod.Agent()
        self.agent.new_game(seat, n, stack)

    def native(self, st: dict):
        return self.kit.to_state(st)

    def call(self, native):
        return self.agent.act(native)

    def parse(self, reply, st: dict):
        return self.kit.parse_action(reply)

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        self.agent.hand_over(hand_no, delta)


class KitB:
    """Fake kit B: module-level decide(observation dict) -> dict, optional on_table_start / on_hand_end."""

    def __init__(self, module, kit):
        self.mod, self.kit = module, kit

    def start(self, seat: int, n: int, stack: int, blinds) -> None:
        fn = getattr(self.mod, "on_table_start", None)
        if fn is not None:
            fn({"seat": seat, "players": n, "stack": stack, "blinds": {"sb": blinds[0], "bb": blinds[1]}})

    def native(self, st: dict):
        return self.kit.to_observation(st)

    def call(self, native):
        return self.mod.decide(native)

    def parse(self, reply, st: dict):
        return self.kit.parse_decision(reply, st)

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        fn = getattr(self.mod, "on_hand_end", None)
        if fn is not None:
            fn({"hand_id": hand_no, "delta": delta})


class Direct:
    """No kit: the package's own ship bot (hyperion.ship.make_bot(): the bot and dials it records; Hero with the
    default Config in a package from before ship.py) fed the engine's Observation, full history included. The
    baseline that isolates the kit path from code drift between the package and this repo."""

    def __init__(self, module, kit):
        from hyperion.core import types as T  # the package's hyperion: its directory is first on sys.path

        try:
            from hyperion.ship import make_bot
        except ImportError:
            from hyperion.strategy.hero import make_bot

        self.T, self.bot = T, make_bot()
        self.kinds = {k.value: k for k in T.ActionKind}

    def _rules(self, d: dict):
        import dataclasses

        names = {f.name for f in dataclasses.fields(self.T.Rules)}
        raw = {k: v for k, v in d.items() if k in names}
        for k in ("board_sizes", "rank_order", "payouts", "blind_levels", "ante_per_level"):
            if k in raw:
                raw[k] = tuple(tuple(x) if isinstance(x, list) else x for x in raw[k])
        return self.T.Rules(**raw)

    def start(self, seat: int, n: int, stack: int, blinds, rules: dict | None = None) -> None:
        self.bot.new_table(self._rules(rules or {}), seat, n)

    def _hist(self, rows):
        A = self.T.Action
        return [(int(s), A(self.kinds[k], int(t))) for s, k, t in rows if k in self.kinds]

    def native(self, st: dict):
        ex = dict(st.get("extras") or {})
        if "discards" in ex:
            ex["discards"] = {int(k): v for k, v in ex["discards"].items()}
        return self.T.Observation(
            hole=tuple(st["hole"]), board=tuple(st["board"]), street=st["street"], seat=st["seat"],
            button=st["button"], stacks=list(st["stacks"]), bets=list(st["bets"]), in_hand=list(st["in_hand"]),
            pot=st["pot"], to_call=st["to_call"], min_raise=st["min_raise"], max_raise=st["max_raise"],
            legal=frozenset(self.kinds[k] for k in st["legal"]), hand_no=st["hand_no"], blinds=tuple(st["blinds"]),
            history=self._hist(st.get("history", ())), extras=ex)

    def call(self, obs):
        return self.bot.act(obs)

    def parse(self, a, st: dict):
        return a.kind.value, int(a.amount)

    def variant(self, prompt: dict):
        fn = getattr(self.bot, "variant_decide", None)
        if fn is None:
            return None
        p = dict(prompt)
        p["hole"], p["board"] = tuple(p.get("hole", ())), tuple(p.get("board", ()))
        return fn(p)

    def end(self, hand_no: int, delta: int, result: dict) -> None:
        r = result or {}
        self.bot.hand_end(self.T.HandResult(
            hand_no=hand_no, deltas=list(r.get("deltas", [])),
            showdown={int(k): tuple(v) for k, v in (r.get("showdown") or {}).items()},
            board=tuple(r.get("board", ())), history=self._hist(r.get("history", ()))))


# ------------------------------------------------------------------ serve: JSON lines

def _dilate(k: float) -> None:
    """tools/gate.py --slow K: every clock here reads K x this thread's CPU time, from before the package is imported, so its
    deadlines, its governor and the host's own timer are all on the slow box's clock (batch 2's method, tools/slowbox.py)."""
    src = time.thread_time_ns
    s0, p0, pn0 = src(), time.perf_counter(), time.perf_counter_ns()
    m0, mn0 = time.monotonic(), time.monotonic_ns()
    time.perf_counter = lambda: p0 + (src() - s0) * k * 1e-9
    time.perf_counter_ns = lambda: pn0 + int((src() - s0) * k)
    time.monotonic = lambda: m0 + (src() - s0) * k * 1e-9
    time.monotonic_ns = lambda: mn0 + int((src() - s0) * k)


def governor_report() -> dict | None:
    """What the package's SafeBots did in this process (hyperion/strategy/safe.py life_stats; a package from before G1:
    its stats()), found by type name, so a kit loader's purge of sys.modules does not hide them. None when there is none: the
    bot runs in another process (kits C, D, a process kit: GATE_GOV_REPORT), or it has no SafeBot."""
    import gc

    out = None
    gc.unfreeze()  # a frozen object is not listed, and the bot's build may freeze (the elite members' modules do); nothing is timed now
    for o in gc.get_objects():
        if type(o).__name__ != "SafeBot":
            continue
        try:
            fn = getattr(o, "life_stats", None)
            if fn is not None:
                r = fn()
                if not (r.get("acts") or r.get("reports")):
                    continue  # a bot the entry built and never played (a warm spare)
                r = {"capable": True, **r}
            else:
                st = o.stats()
                if not st.get("calls"):
                    continue
                r = {"capable": False, "acts": st["calls"], "reports": 0, "overruns": st["overruns"], "tables": 1,
                     "level_tables": int(st["level_max"] > 0), "panic_tables": int(bool(st["panic_mode"])),
                     "level_max": st["level_max"], "lvl_calls": {}, "whole_on": False, "whole": False}
                inner = getattr(o, "inner", None)
                for k, v in (getattr(inner, "counts", None) or {}).items():
                    if isinstance(k, str) and k.startswith("level:"):
                        r["lvl_calls"][k[6:]] = v
        except Exception:  # noqa: BLE001 - a report: never in the way
            continue
        if out is None:
            out = r
        else:
            for k in ("acts", "reports", "overruns", "tables", "level_tables", "panic_tables"):
                out[k] = out.get(k, 0) + r.get(k, 0)
            out["level_max"] = max(out.get("level_max", 0), r.get("level_max", 0))
            out["whole_on"] = out.get("whole_on") or r.get("whole_on")
            out["whole"] = out.get("whole") or r.get("whole")
            for k, v in r.get("lvl_calls", {}).items():
                out["lvl_calls"][k] = out["lvl_calls"].get(k, 0) + v
    return out


def serve(kind: str, pkg: str, entry: str, kit_dir: str, seat_file: str | None) -> int:
    if os.environ.get("GATE_SLOW_K"):
        _dilate(float(os.environ["GATE_SLOW_K"]))
    proto = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)  # anything the bot prints goes to stderr, never into the protocol

    def send(obj) -> None:
        proto.write(json.dumps(obj) + "\n")
        proto.flush()

    _setup_path(pkg, kit_dir)
    errors, notes = 0, []

    def note(text: str) -> None:
        if len(notes) < 8:
            notes.append(text[:300])

    t0 = time.perf_counter()
    try:
        kit = None
        if kit_dir and kit_dir != "-" and os.path.exists(os.path.join(kit_dir, "kit.py")):
            import kit  # noqa: F401 - the kit module, importable as the rules promise
        if kind == "direct":
            seat = Direct(None, kit)
        else:
            seat_mod = _load_file(seat_file, "gate_seat") if kind == "seat" else None
            if seat_mod is not None and getattr(seat_mod, "PROCESS", False):
                # a process kit's seat (hyperion/drills/process_gate_seat_template.py) launches the entry itself, as
                # the kit does: it gets the entry's path, never an in-process import
                module = types.SimpleNamespace(__file__=os.path.join(pkg, entry), __name__="submission")
            elif seat_mod is not None and callable(getattr(seat_mod, "load_entry", None)):
                # a module-function kit's seat (hyperion/drills/module_gate_seat_template.py) loads the entry as the
                # kit's loader does: the folder on sys.path for the import only, its modules out of sys.modules after
                module = seat_mod.load_entry(os.path.join(pkg, entry))
            else:
                module = _load_file(os.path.join(pkg, entry), "submission")
            if kind == "a":
                seat = KitA(module, kit)
            elif kind == "b":
                seat = KitB(module, kit)
            elif kind == "seat":
                seat = seat_mod.Seat(module, kit)
            else:
                raise ValueError(f"unknown kind {kind!r}")
    except BaseException as e:  # noqa: BLE001 - the import failing is the finding
        send({"fatal": f"{type(e).__name__}: {e}"[:500]})
        return 1
    send({"ready": True, "import_s": round(time.perf_counter() - t0, 3)})

    pc = time.perf_counter_ns
    for line in sys.stdin:
        msg = json.loads(line)
        op = msg["op"]
        if op == "act":
            st = _fix_state(msg["st"])
            try:
                native = seat.native(st)
            except Exception as e:  # noqa: BLE001 - our translation failed, not the bot
                send({"gate_err": f"{type(e).__name__}: {e}"[:300]})
                continue
            t = pc()
            try:
                reply = seat.call(native)
                ns = pc() - t
            except Exception as e:  # noqa: BLE001
                send({"err": f"{type(e).__name__}: {e}"[:300], "ns": pc() - t})
                continue
            try:
                kind_, total = seat.parse(reply, st)
                send({"k": kind_, "t": int(total), "ns": ns})
            except Exception:  # noqa: BLE001 - an unreadable reply is an illegal action
                send({"bad": repr(reply)[:200], "ns": ns})
        elif op == "variant":
            t = pc()
            try:
                ans = seat.variant(msg["prompt"])
                send({"v": ans if isinstance(ans, (int, float, str, bool)) or ans is None else repr(ans), "ns": pc() - t})
            except Exception as e:  # noqa: BLE001
                send({"err": f"{type(e).__name__}: {e}"[:300], "ns": pc() - t})
        elif op == "start":
            try:
                if kind == "direct":
                    seat.start(msg["seat"], msg["n"], msg["stack"], msg["blinds"], msg.get("rules"))
                else:
                    seat.start(msg["seat"], msg["n"], msg["stack"], msg["blinds"])
            except Exception as e:  # noqa: BLE001
                errors += 1
                note(f"start raised {type(e).__name__}: {e}")
        elif op == "end":
            try:
                seat.end(msg["hand_no"], msg["delta"], msg.get("result"))
            except Exception as e:  # noqa: BLE001
                errors += 1
                note(f"hand end raised {type(e).__name__}: {e}")
        elif op == "close":
            fn = getattr(seat, "close", None)  # a process seat ends the table and its bot process
            if fn is not None:
                try:
                    fn()
                except Exception as e:  # noqa: BLE001
                    errors += 1
                    note(f"close raised {type(e).__name__}: {e}")
            counts = getattr(seat, "gate_counts", None)  # a seat's own tallies (the module seat's Overtimes)
            send({"errors": errors, "notes": notes, "counts": dict(counts) if counts else {}, "gov": governor_report()})
            break
    return 0


def launch(pkg: str, entry: str, kit_dir: str, args: list[str]) -> None:
    _setup_path(pkg, kit_dir)
    path = os.path.join(pkg, entry)
    sys.argv = [path, *args]
    runpy.run_path(path, run_name="__main__")


if __name__ == "__main__":
    if sys.argv[1] == "serve":
        sys.exit(serve(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6] if len(sys.argv) > 6 else None))
    if sys.argv[1] == "launch":
        launch(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5:])
        sys.exit(0)
    sys.exit(f"usage: {sys.argv[0]} serve|launch ...")
