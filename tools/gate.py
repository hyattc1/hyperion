#!/usr/bin/env python
"""Gate what you upload: play the submission zip itself in our simulator, paired against the same bot in-sim.

    python tools/gate.py dist/submission.zip --kit a|b|c|d|seat.py [--entry submission.py]
                         [--tables 100] [--seed 11] [--field realistic | --bots a,b,...] [--mode strict]
                         [--rules rules_tonight.json] [--variant NAME] [--bot NAME] [--dials JSON]
                         [--hero-config JSON|cheap] [--baseline sim|package] [--kit-module path/to/kit.py]

Every Stage 4 number before drill 6 measured the simulator's own Hero, which the engine feeds its full
history. The bot we upload sees only what its adapter passes, and in drill 6 that was 2.5 points a table
less. This gate measures the upload.

The zip (or its directory) is unpacked into a temp dir and imported there the way the organisers would:
a fresh `python -I -B` (tools/gate_host.py), the package directory first on sys.path, the kit module
importable as `kit`, a scratch working directory, no PYTHON* or HYPERION_* variables. One process per
table ("imported once per table"). A reverse adapter turns each engine Observation into the kit's state
(hyperion.drills.adapter.dealer_state, then the kit's own constructor) and the kit's reply back into an
Action:
  a, b   in-process (class Agent / module decide); the host times the bot call alone against 1 ms.
  c, d   the entry runs as a subprocess speaking the kit's line or socket protocol, as their runners do;
         each round trip is charged to the kit's pooled clock (1 ms x max_hands x 3), and once it runs
         out every action is a check or fold.
  seat.py  tonight's in-process kit: a class Seat modelled on gate_host.KitA, with --kit-module the
         organisers' kit.py. Its state's history rows carry the street and the chips each action put in
         ([seat, kind, total, street, put]) and `posts` the hand's forced bets, so the seat can send the kit's own
         per-street log (hyperion/drills/gate_seat_template.py by_street) and the gate tests the adapter's parser.
         A process kit's seat: process_gate_seat_template.py; a module-function kit's (drill 11's kit I):
         module_gate_seat_template.py, which loads the entry as the kit's loader does (the folder off sys.path and
         its modules out of sys.modules after the import) and raises the kit's Overtime inside it at each limit.
Illegal replies and exceptions are a check or fold, as the rules score them. One exception: kit D's legal set
lets a seat re-raise after a short all-in, which our engine does not reopen; that raise is played as a call
and reported as a rule mismatch, since the bot followed its kit.

Each table seed is played twice: the package in the `hero` seat of the field, then the same deal with the
baseline in that seat and every other bot identical. The baseline (`--baseline sim`) is the bot the package
records in its hyperion/ship.py (tools/pack.py writes SHIP and DIALS there: hybrid3_x, the shipped base, unless
packed with --bot), built by this repo's hyperion.ship.make_bot with those dials; a package with no record is
paired against Hero. `--bot` / `--dials` replace the record; `--hero-config JSON|cheap` is the older form, Hero
(or Hero.cheap()) with those Config keys, also given to every other Hero seat. `--baseline package` plays the
package's own ship bot behind no adapter instead, for a package built from older code (it reads the package's
tables too, so a missing variant set hides from it).

A kit with no action log (`--kit-log no`; the default `auto` says no for fake kits b, c and d and yes for a and a
seat file) gives the baseline what the kit gives the package, through the same inference the adapters run
(hyperion.drills.infer_history.InferSeat): each decision's log rebuilt from the bare states, and a hand end that
waits for the next hand's first state (kit d: one with every seat's chip change and the hands at showdown). Fed
the full log, the in-sim bot is a bar no package on such a kit can reach (kit B before the inference: Hero
-0.83 +- 0.46, hybrid3_x -1.23 +- 0.71 at 60 tables); fed the bets alone (`--kit-log bets`, NoLogSeat, the
baseline before the inference) it no longer catches an adapter that drops the inference (worth 0.4-0.8 points).

FAIL (exit 1) when the package lacks a table its recorded bot needs (tools/table_probe.py, before any table is played: the
loader that returns None plays on, so no table would show it) or trails the baseline by more than the paired 95% interval, raises, sends
an illegal action, never imports, or times out on more than --max-tmo-pct of its decisions (a warning
instead when the load average exceeds the core count, the playbook's load clause). Otherwise PASS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import select
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Run as a script, tools/ is sys.path[0], and a tools/*.py named like a stdlib module shadows it (tools/profile.py
# broke `import cProfile` in the runner): modules come from the repo root and the standard library only.
sys.path[:] = [p for p in sys.path if Path(p or ".").resolve() != ROOT / "tools"]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hyperion import ship  # noqa: E402
from hyperion.core.types import Action, ActionKind, Observation, Rules  # noqa: E402
from hyperion.drills.adapter import NoLogSeat, dealer_state, history_rows  # noqa: E402
from hyperion.drills.infer_history import InferSeat  # noqa: E402
from hyperion.sim import bestiary  # noqa: E402
from hyperion.sim.engine import BUDGET_NS, BotStats, Table  # noqa: E402

HOST = ROOT / "tools" / "gate_host.py"
FAKEKITS = ROOT / "hyperion" / "drills" / "fakekits"
KINDS = {k.value: k for k in ActionKind}
FOLD, CHECK, CALL, RAISE = ActionKind.FOLD, ActionKind.CHECK, ActionKind.CALL, ActionKind.RAISE
READY_TIMEOUT_S = 60.0  # import on a loaded box; the organisers' own limit is unknown
HARD_TIMEOUT_S = 2.0  # a reply slower than this marks a subprocess bot dead, as kits C and D do
CHEAP = ship.CHEAP  # Hero.cheap()'s Config


@dataclass
class Reply:
    """What the gate seat answered: kind and raise-to total, or why there is no usable answer."""
    kind: str | None = None
    total: int = 0
    ns: int | None = None  # the bot's time (in-process kits) or the round trip (subprocess kits)
    error: str | None = None  # the bot raised, died, or never imported
    bad: str | None = None  # a reply the kit cannot parse
    late: bool = False  # over the 1 ms budget, or the pooled clock ran out
    value: object = None  # a variant decision's answer


def _env() -> dict:
    return {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "HYPERION_"))}


# ------------------------------------------------------------------ the gate seat: one proxy per kit

class Proxy:
    """The engine Bot interface for a packaged bot in another process. The GateTable asks it through
    decide() and variant() so the time charged is the bot's, never this process's IPC."""

    kit = "?"

    def __init__(self, cfg: "Config"):
        self.cfg = cfg
        self.table: "GateTable | None" = None
        self.seat = 0
        self.n = 0
        self.rules = Rules()
        self.fatal: str | None = None
        self.notes: list[str] = []
        self.late = 0
        self.unasked = 0  # decisions after a pooled clock ran out: folded without asking, as kits C and D do
        self.unsupported = 0  # variant decisions this kit cannot carry: the dealer's default plays
        self.lifecycle_errors = 0  # exceptions in table start or hand end, counted by the host
        self.rule_mismatch = 0  # kit D raises its rules allow and ours do not (short all-in, no reopen)
        self.import_s: float | None = None
        self.counts: dict = {}  # a seat file's own tallies (gate_counts: the module seat's Overtimes)

    def note(self, text: str) -> None:
        if len(self.notes) < 12:
            self.notes.append(text[:400])

    # engine interface
    def new_table(self, rules: Rules, seat: int, n: int) -> None:
        self.rules, self.seat, self.n = rules, seat, n
        self.open()

    def act(self, obs: Observation) -> Action:  # pragma: no cover - GateTable never calls it
        raise RuntimeError("the gate table asks a proxy through decide()")

    def hand_end(self, result) -> None:
        pass

    # gate interface
    def open(self) -> None:
        raise NotImplementedError

    def decide(self, obs: Observation) -> Reply:
        raise NotImplementedError

    def variant(self, prompt: dict) -> Reply:
        self.unsupported += 1
        return Reply()

    def close(self) -> None:
        pass


class HostProxy(Proxy):
    """Kits a, b, a seat file, or `direct`: tools/gate_host.py serves the bot over JSON lines."""

    def __init__(self, cfg: "Config", kind: str):
        super().__init__(cfg)
        self.kind = kind
        self.kit = kind
        self.proc: subprocess.Popen | None = None
        self.log = None

    def open(self) -> None:
        c = self.cfg
        self.log = tempfile.TemporaryFile(mode="w+")
        args = [sys.executable, "-I", "-B", str(HOST), "serve", self.kind, str(c.pkg), c.entry, str(c.kit_dir)]
        if self.kind == "seat":
            args.append(str(c.seat_file))
        self.proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
                                     text=True, bufsize=1, cwd=c.scratch, env=_env())
        msg = self._read(READY_TIMEOUT_S)
        if msg is None or "fatal" in msg:
            self.fatal = (msg or {}).get("fatal") or "no ready line: " + self._stderr_tail()
            self.note(f"import failed: {self.fatal}")
            return
        self.import_s = msg.get("import_s")
        blinds = self.rules.blinds_at(0)
        start = {"op": "start", "seat": self.seat, "n": self.n, "stack": self.rules.starting_stack,
                 "blinds": list(blinds)}
        if self.kind == "direct":
            from hyperion.tablegen import rules_to_dict
            start["rules"] = rules_to_dict(self.rules)
        self._send(start)

    def _send(self, obj) -> bool:
        try:
            self.proc.stdin.write(json.dumps(obj) + "\n")
            self.proc.stdin.flush()
            return True
        except (BrokenPipeError, OSError, ValueError):
            self.fatal = self.fatal or "bot process died: " + self._stderr_tail()
            return False

    def _read(self, timeout: float) -> dict | None:
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            return None
        line = self.proc.stdout.readline()
        return json.loads(line) if line else None

    def _stderr_tail(self) -> str:
        try:
            self.log.seek(0)
            return " | ".join(self.log.read().strip().splitlines()[-4:])[-400:]
        except Exception:  # noqa: BLE001
            return ""

    def _ask(self, obj) -> Reply:
        if self.fatal:
            return Reply(error=self.fatal)
        if not self._send(obj):
            return Reply(error=self.fatal)
        msg = self._read(READY_TIMEOUT_S)
        if msg is None:
            self.fatal = "bot process stopped answering: " + self._stderr_tail()
            return Reply(error=self.fatal)
        if "gate_err" in msg:  # our reverse adapter failed: a gate bug, reported, never blamed on the bot
            self.note(f"gate translation error: {msg['gate_err']}")
            return Reply(error="gate: " + msg["gate_err"])
        ns = msg.get("ns")
        late = ns is not None and ns > self.cfg.budget_ns
        if "err" in msg:
            return Reply(error=msg["err"], ns=ns)
        if "bad" in msg:
            return Reply(bad=msg["bad"], ns=ns, late=late)
        if "v" in msg:
            return Reply(value=msg["v"], ns=ns, late=late)
        return Reply(kind=msg["k"], total=msg["t"], ns=ns, late=late)

    def state(self, obs: Observation) -> dict:
        """The dealer state the host's seat gets; a seat file (tonight's kit) also gets each row's street and chips
        and the posts, for the kit's own log."""
        t = self.table
        if self.kind == "seat" and t is not None:
            return dealer_state(obs, t.street_start(1), tags=t.history_tags(obs.history), posts=t.posts)
        st = dealer_state(obs, t.street_start(1) if t else None)
        if self.kind == "direct":
            st["extras"] = _json_extras(obs.extras)
        return st

    def decide(self, obs: Observation) -> Reply:
        return self._ask({"op": "act", "st": self.state(obs)})

    def variant(self, prompt: dict) -> Reply:
        if self.kind == "direct":
            p = {k: (list(v) if isinstance(v, tuple) else v) for k, v in prompt.items()}
            return self._ask({"op": "variant", "prompt": p})
        if prompt.get("decision") != "discard" or self.kind == "b":
            self.unsupported += 1
            return Reply()
        st = self.table.discard_state(self.seat, prompt, tagged=self.kind == "seat")  # kit A, a seat: DISCARD only
        r = self._ask({"op": "act", "st": st})
        if r.kind is not None:
            if r.kind != "discard" or not 0 <= r.total < len(prompt["hole"]):
                return Reply(bad=f"{r.kind}:{r.total} on a discard", ns=r.ns, late=r.late)
            r.value = r.total
        return r

    def hand_end(self, result) -> None:
        if self.fatal or self.proc is None:
            return
        res = None
        if self.kind in ("direct", "seat"):  # a seat file passes on what tonight's kit's hand end would carry
            t = self.table if self.kind == "seat" else None
            res = {"deltas": list(result.deltas), "board": list(result.board),
                   "showdown": {str(s): list(h) for s, h in (result.showdown or {}).items()},
                   "history": history_rows(result.history, tags=t.history_tags(result.history) if t else None)}
            if t is not None:
                res["posts"] = [list(p) for p in t.posts]
        self._send({"op": "end", "hand_no": result.hand_no, "delta": result.deltas[self.seat], "result": res})

    def close(self) -> None:
        if self.proc is None:
            return
        if not self.fatal and self._send({"op": "close"}):
            msg = self._read(10.0) or {}
            if msg.get("errors"):
                self.lifecycle_errors = msg["errors"]
                for n in msg.get("notes", []):
                    self.note(n)
            self.counts = dict(msg.get("counts") or {})
        try:
            self.proc.stdin.close()
        except OSError:
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()


def _json_extras(extras: dict) -> dict:
    out = {}
    for k, v in (extras or {}).items():
        try:
            json.dumps(v)
            out[k] = v
        except TypeError:
            if isinstance(v, dict):
                out[k] = {str(a): (list(b) if isinstance(b, tuple) else b) for a, b in v.items()}
    return out


class PooledProxy(Proxy):
    """Subprocess kits share the pooled game clock: budget x max_hands x 3, charged by each round trip."""

    def __init__(self, cfg: "Config"):
        super().__init__(cfg)
        self.clock_s = 0.0
        self.dead = False

    def reset_clock(self) -> None:
        self.clock_s = self.cfg.budget_ns / 1e9 * self.rules.max_hands * 3

    def _launch(self, extra: list[str], **kw) -> subprocess.Popen:
        c = self.cfg
        self.log = tempfile.TemporaryFile(mode="w+")
        if kw.get("stdout") == "log":  # kit D bots print their logs; the protocol is the socket
            kw["stdout"] = self.log
        return subprocess.Popen([sys.executable, "-I", "-B", str(HOST), "launch", str(c.pkg), c.entry, str(c.kit_dir),
                                 *extra], stderr=self.log, cwd=c.scratch, env=_env(), **kw)

    def _stderr_tail(self) -> str:
        try:
            self.log.seek(0)
            return " | ".join(self.log.read().strip().splitlines()[-4:])[-400:]
        except Exception:  # noqa: BLE001
            return ""

    def _die(self, why: str) -> None:
        if not self.dead:
            self.dead = True
            self.fatal = self.fatal or why
            self.note(f"{why}; stderr: {self._stderr_tail()}")


class KitCProxy(PooledProxy):
    """Kit C: `python submission.py`, one line per message on stdin/stdout (hyperion/drills/fakekits/kit_c)."""

    kit = "c"

    def open(self) -> None:
        from hyperion.drills.fakekits.kit_c import kit as kc

        self.kc = kc
        self.reset_clock()
        self.proc = self._launch([], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, bufsize=1)
        sb, bb = self.rules.blinds_at(0)
        ack = self._ask_line(kc.encode_table_start(self.n, self.seat, self.rules.starting_stack, (sb, bb)),
                             READY_TIMEOUT_S)
        if ack is None:
            self._die("no OK after the table-start line")
        elif ack.strip() != "OK":
            self.note(f"expected OK after table start, got {ack.strip()!r}")

    def _ask_line(self, line: str, timeout: float) -> str | None:
        if self.dead:
            return None
        try:
            self.proc.stdin.write(line + "\n")
            self.proc.stdin.flush()
        except (BrokenPipeError, OSError):
            self._die("bot process died")
            return None
        ready, _, _ = select.select([self.proc.stdout], [], [], timeout)
        if not ready:
            self._die(f"no reply within {timeout:g} s")
            return None
        reply = self.proc.stdout.readline()
        if not reply:
            self._die("bot closed stdout")
            return None
        return reply

    def decide(self, obs: Observation) -> Reply:
        if self.dead:
            return Reply(error=self.fatal)
        if self.clock_s <= 0:
            return Reply(late=True)
        t0 = time.perf_counter_ns()
        reply = self._ask_line(self.kc.encode_decision(dealer_state(obs), self.clock_s * 1000), HARD_TIMEOUT_S)
        ns = time.perf_counter_ns() - t0
        if reply is None:
            return Reply(error=self.fatal, ns=ns)
        self.clock_s -= ns / 1e9
        if self.clock_s <= 0:
            return Reply(late=True, ns=ns)
        try:
            kind, total = self.kc.parse_reply(reply)
        except ValueError:
            return Reply(bad=reply.strip()[:80], ns=ns)
        return Reply(kind=kind, total=total, ns=ns)

    def hand_end(self, result) -> None:
        if not self.dead:
            try:
                self.proc.stdin.write(self.kc.encode_hand_end(result.hand_no, result.deltas[self.seat]) + "\n")
                self.proc.stdin.flush()
            except (BrokenPipeError, OSError):
                self._die("bot process died")

    def close(self) -> None:
        try:
            self.proc.stdin.write("Q\n")
            self.proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()


_D_ACTION = {"fold": "F", "call": "C", "check": "K"}


class KitDProxy(PooledProxy):
    """Kit D: `python submission.py <port>`, the MIT-style socket skeleton. The bot replays every action at
    the table, so each packet carries the actions since the last one, with B<board> where a street begins
    (hyperion/drills/fakekits/kit_d)."""

    kit = "d"

    def open(self) -> None:
        self.reset_clock()
        self.hand = -1
        lst = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lst.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        lst.bind(("localhost", 0))
        lst.listen(1)
        lst.settimeout(READY_TIMEOUT_S)
        self.proc = self._launch([str(lst.getsockname()[1])], stdin=subprocess.DEVNULL, stdout="log")
        try:
            conn, _ = lst.accept()
        except OSError:
            self._die("bot did not connect")
            return
        finally:
            lst.close()
        conn.settimeout(HARD_TIMEOUT_S)
        self.conn, self.rfile, self.wfile = conn, conn.makefile("r"), conn.makefile("w")

    def _query(self, clauses: list[str]) -> tuple[str | None, int]:
        line = " ".join([f"T{max(self.clock_s, 0.0):.6f}", f"P{self.seat}", *clauses])
        t0 = time.perf_counter_ns()
        try:
            self.wfile.write(line + "\n")
            self.wfile.flush()
            reply = self.rfile.readline()
        except (socket.timeout, OSError) as e:
            self._die(f"socket: {type(e).__name__}")
            return None, time.perf_counter_ns() - t0
        ns = time.perf_counter_ns() - t0
        self.clock_s -= ns / 1e9
        if not reply:
            self._die("bot closed the connection")
            return None, ns
        return reply, ns

    def _open_round(self) -> None:
        """The round-start packet from the stacks and pips right after the blinds."""
        from hyperion.core.types import card_str

        t = self.table
        stacks, pips, holes, button, blinds = t.pre
        self.hand, self.sent, self.board_sent = t.cur.hand_no, 0, 0
        self._query([f"S{','.join(map(str, stacks))}", f"I{','.join(map(str, pips))}", f"L{blinds[0]},{blinds[1]}",
                     "H" + ",".join(card_str(c) for c in holes[self.seat]), f"G{button}"])

    def _pending(self, history) -> list[str]:
        from hyperion.core.types import card_str

        out = []
        marks = self.table.marks
        for i in range(self.sent, len(history) + 1):
            for board, at in marks:
                if at == i and len(board) > self.board_sent:
                    out.append("B" + ",".join(card_str(c) for c in board))
                    self.board_sent = len(board)
            if i < len(history):
                a = history[i][1]
                out.append(f"R{a.amount}" if a.kind is RAISE else _D_ACTION[a.kind.value])
        self.sent = len(history)
        return out

    def decide(self, obs: Observation) -> Reply:
        if self.dead:
            return Reply(error=self.fatal)
        if self.clock_s <= 0:
            return Reply(late=True)
        if self.hand != obs.hand_no:
            self._open_round()
        reply, ns = self._query(self._pending(obs.history))
        if reply is None:
            return Reply(error=self.fatal, ns=ns)
        if self.clock_s <= 0:
            return Reply(late=True, ns=ns)
        s = reply.strip()
        if s in ("F", "K", "C"):
            return Reply(kind={"F": "fold", "K": "check", "C": "call"}[s], ns=ns)
        if s.startswith("R") and s[1:].isdigit():
            return Reply(kind="raise", total=int(s[1:]), ns=ns)
        return Reply(bad=s[:80], ns=ns)

    def hand_end(self, result) -> None:
        if self.dead or self.clock_s <= 0:
            return
        from hyperion.core.types import card_str

        if self.hand != result.hand_no:
            self._open_round()
        clauses = self._pending(result.history)
        if len(result.board) > self.board_sent:
            clauses.append("B" + ",".join(card_str(c) for c in result.board))
        if len(result.showdown or {}) > 1:
            clauses += [f"O{s}:" + ",".join(card_str(c) for c in h) for s, h in result.showdown.items() if s != self.seat]
        clauses.append("A" + ",".join(str(int(d)) for d in result.deltas))
        self._query(clauses)

    def close(self) -> None:
        try:
            if not self.dead:
                self.wfile.write("Q\n")
                self.wfile.flush()
            for f in (self.rfile, self.wfile, self.conn):
                f.close()
        except (OSError, AttributeError):
            pass
        try:
            self.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.log.close()


# ------------------------------------------------------------------ the table

class GateTable(Table):
    """A sim Table whose `gate_seat` is a Proxy: it is asked through the proxy, timed by the proxy, and held
    to the rules' scoring (an exception, an illegal or late reply is a check or fold). Every other seat, and
    the whole table when gate_seat is None, is the engine's own code. Records what the reverse adapters need:
    the hand in play, the stacks and pips right after the blinds, where each street's history begins, and the forced
    bets, from which each history entry's street and chips follow (history_tags, posts)."""

    def __init__(self, bots, rules, seed, mode, variant, stats, gate_seat=None, proxy=None):
        self.gate_seat, self.proxy = gate_seat, proxy
        self.cur = None
        self.pre = None
        self.marks: list[tuple[tuple, int]] = []
        self.starts: list[tuple[int, int]] = []  # (street, history index) where each betting round began
        self.posts: list[list] = []  # this hand's forced bets [seat, "ante" | "sb" | "bb" | "straddle", chips]
        if proxy is not None:
            proxy.table = self
        super().__init__(bots, rules, seed, 0, mode, variant, stats)

    def _needs_betting(self, hs) -> bool:
        if hs is not self.cur:  # street 0 of a new hand: the blinds (and a straddle) are in, nobody has acted
            self.cur, self.marks, self.starts = hs, [], []
            self.pre = (self.stacks[:], hs.bets[:], list(hs.holes), hs.button, hs.blinds)
            self.posts = self._forced(hs)
        self.marks.append((tuple(hs.board), len(hs.history)))
        return super()._needs_betting(hs)

    def _betting_round(self, hs, street: int, first: int) -> None:
        self.starts.append((street, len(hs.history)))
        return super()._betting_round(hs, street, first)

    def _forced(self, hs) -> list[list]:
        """The hand's forced bets as the engine posted them: every ante (dead money, out of the bets), then the small
        blind, the big blind and a straddle (Table.play_hand's order; heads-up the button posts the small blind)."""
        out = [[s, "ante", hs.contrib[s] - hs.bets[s]] for s in range(self.n) if hs.contrib[s] > hs.bets[s]]
        in_hand = hs.in_hand
        sb = hs.button if hs.n_in_hand == 2 else self._after(hs.button, in_hand)
        bb = self._after(sb, in_hand)
        seats = [(sb, "sb"), (bb, "bb")]
        if self.rules.straddle and hs.n_in_hand >= 3:
            seats.append((self._after(bb, in_hand), "straddle"))
        out += [[s, name, hs.bets[s]] for s, name in seats if hs.bets[s] > 0]
        return out

    def history_tags(self, history) -> list[tuple[int, int]]:
        """(street, chips put in) for each entry of this hand's `history`: the street from where each betting round
        began, the chips replayed from the stacks and bets right after the posts (a call puts in what it owes, capped by
        the stack; a raise its total less the seat's bet on the street)."""
        if self.pre is None:
            return [(0, 0)] * len(history)
        stacks, bets = list(self.pre[0]), list(self.pre[1])
        starts = self.starts
        k, street = 0, starts[0][0] if starts else 0
        out = []
        for i, (s, a) in enumerate(history):
            while k + 1 < len(starts) and starts[k + 1][1] <= i:
                k += 1
                street = starts[k][0]
                bets = [0] * len(bets)
            kind = a.kind
            if kind is CALL:
                put = min(max(bets) - bets[s], stacks[s])
            elif kind is RAISE:
                put = min(int(a.amount) - bets[s], stacks[s])
            else:
                put = 0
            bets[s] += put
            stacks[s] -= put
            out.append((street, put))
        return out

    def street_start(self, street: int) -> int | None:
        return self.marks[street][1] if street < len(self.marks) else None

    def discard_state(self, seat: int, prompt: dict, tagged: bool = False) -> dict:
        """The dealer's DISCARD-only state for a toss (fakekits/_table.py _toss_round); `tagged` for a seat file."""
        hs = self.cur
        discards = dict(getattr(getattr(self.variant, "hooks", None), "discards", {}) or {})
        st = {
            "hole": list(prompt["hole"]), "board": list(prompt.get("board") or hs.board), "street": 1, "seat": seat,
            "button": hs.button, "stacks": self.stacks[:], "bets": list(hs.bets), "in_hand": list(hs.in_hand),
            "pot": hs.pot, "to_call": 0, "min_raise": 0, "max_raise": 0, "legal": ["discard"],
            "hand_no": hs.hand_no, "blinds": list(hs.blinds),
            "history": history_rows(hs.history, discards, tags=self.history_tags(hs.history) if tagged else None),
            "discards": {int(s): int(c) for s, c in discards.items()},
        }
        if tagged:
            st["posts"] = [list(p) for p in self.posts]
        return st

    def _fallback(self, obs: Observation) -> Action:
        return Action.check() if CHECK in obs.legal else Action.fold()

    def _ask(self, s: int, obs: Observation) -> Action:
        if s != self.gate_seat:
            return super()._ask(s, obs)
        st, p = self.stats[s], self.proxy
        r = p.decide(obs)
        if r.ns is not None:
            st.record(r.ns)
        if r.error:
            st.exceptions += 1
            st.last_error = r.error
            return self._fallback(obs)
        if r.late:
            p.late += 1
            if r.ns is None:  # the pooled clock had run out: the kit never asked the bot
                p.unasked += 1
                return self._fallback(obs)
            if self.strict:
                return self._fallback(obs)
        if r.bad is not None:
            st.illegal += 1
            p.note(f"unreadable reply {r.bad!r}")
            return self._fallback(obs)
        kind = KINDS.get(r.kind)
        if (p.kit == "d" and kind is RAISE and RAISE not in obs.legal and CALL in obs.legal
                and obs.stacks[s] > obs.to_call):
            # kit D's skeleton lets a seat re-raise after a short all-in; our engine does not reopen the action.
            # The bot followed its kit's rules, so this is a rule mismatch played as a call, not an illegal action.
            p.rule_mismatch += 1
            return Action.call()
        if kind is None or kind not in obs.legal or (kind is RAISE and not obs.min_raise <= r.total <= obs.max_raise):
            st.illegal += 1
            p.note(f"illegal {r.kind} {r.total} with legal {sorted(k.value for k in obs.legal)} "
                   f"min {obs.min_raise} max {obs.max_raise} (hand {obs.hand_no}, street {obs.street})")
            return self._fallback(obs)
        return Action(kind, int(r.total)) if kind is RAISE else Action(kind)

    def _ask_variant(self, s: int, prompt: dict):
        if s != self.gate_seat:
            return super()._ask_variant(s, prompt)
        prompt = dict(prompt)
        prompt.setdefault("seat", s)
        prompt.setdefault("hand_no", self.hand_no)
        prompt.setdefault("stacks", self.stacks[:])
        st, p = self.stats[s], self.proxy
        r = p.variant(prompt)
        if r.ns is not None:
            st.record(r.ns)
        if r.error:
            st.exceptions += 1
            st.last_error = r.error
            return None
        if r.late:
            p.late += 1
            if self.strict:
                return None
        if r.bad is not None:
            st.illegal += 1
            p.note(f"illegal variant answer {r.bad!r}")
            return None
        return r.value


# ------------------------------------------------------------------ runs

@dataclass
class Config:
    pkg: Path
    entry: str
    kit: str
    kit_dir: Path
    scratch: str
    seat_file: Path | None = None
    budget_ns: int = BUDGET_NS


@dataclass
class Side:
    """One seat's results across the run: the package, or the baseline in the same seat on the same deal."""
    label: str
    points: list[float] = field(default_factory=list)
    places: list[int] = field(default_factory=list)
    busts: int = 0
    stats: BotStats = field(default_factory=BotStats)
    late: int = 0
    unasked: int = 0
    unsupported: int = 0
    rule_mismatch: int = 0
    counts: dict = field(default_factory=dict)  # the seat file's tallies, summed over the tables
    lifecycle: int = 0
    notes: list[str] = field(default_factory=list)
    import_s: list[float] = field(default_factory=list)
    fatal: str | None = None
    proxied: bool = False

    @property
    def decisions(self) -> int:
        return self.stats.calls + self.stats.first_calls + self.unasked

    @property
    def tmo(self) -> int:
        """Decisions the time rule turned into a check or fold (counted in measure mode too, not enforced)."""
        return self.late if self.proxied else self.stats.over_budget


def mean_ci(xs: list[float]) -> tuple[float, float]:
    n = len(xs)
    if n == 0:
        return 0.0, 0.0
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, 1.96 * math.sqrt(var / n)


def make_proxy(cfg: Config, kind: str) -> Proxy:
    if kind in ("a", "b", "seat", "direct"):
        return HostProxy(cfg, kind)
    if kind == "c":
        return KitCProxy(cfg)
    if kind == "d":
        return KitDProxy(cfg)
    raise ValueError(kind)


def seating_for(names: list[str], n: int, table_seed: int) -> list[str]:
    """The runner's seating rule (hyperion/sim/runner.py), so a gate table and a sim table seat alike."""
    rng = random.Random(table_seed)
    seating = list(names[:n])
    while len(seating) < n:
        seating.append(rng.choice(names))
    rng.shuffle(seating)
    return seating


def play(cfg: Config, names: list[str], tables: int, seed: int, rules: Rules, variant, mode: str,
         baseline: str, progress=None, base: Side | None = None,
         bot: tuple[str, dict] | None = None, no_log: bool | str = False) -> tuple[Side, Side]:
    """Each table seed with the package in the hero seat, then with the baseline there. A `base` from an
    earlier call with the same field, seeds and rules is reused instead of replayed. `bot` = (name, dials) for
    hyperion.ship.make_bot in the baseline seat; None = the bestiary's `hero` (with bestiary.HERO_CONFIG).
    `no_log`: the in-sim baseline sees what a kit with no action log gives: "next" (or True) through an adapter that
    infers the log (InferSeat; its hand end waits for the next hand's first state), "shown" the same with a hand end
    that lists every seat's chip change and the hands at showdown (kit D), "bets" through one that infers nothing
    (NoLogSeat, for packages from before the inference)."""
    pkg = Side("package")
    sides = [(pkg, cfg.kit)]
    label = bot[0] if bot is not None else "hero"
    if base is None:
        base = Side(f"{label} (sim)" if baseline == "sim" else f"{label} (package, no adapter)")
        sides.append((base, None if baseline == "sim" else "direct"))
    n = rules.n_players
    for t in range(tables):
        table_seed = seed * 1_000_003 + t
        seating = seating_for(names, n, table_seed)
        g = seating.index("hero")
        for side, kind in sides:
            bots = [bestiary.make_bot(nm, seed=table_seed * 64 + s) for s, nm in enumerate(seating)]
            proxy = make_proxy(cfg, kind) if kind else None
            if proxy is not None:
                bots[g] = proxy
            elif bot is not None:
                bots[g] = ship.make_bot(bot[0], bot[1], seed=table_seed * 64 + g)
            if proxy is None and no_log and baseline == "sim":
                mode_ = "next" if no_log is True else no_log
                bots[g] = NoLogSeat(bots[g]) if mode_ == "bets" else InferSeat(bots[g], final=mode_)
            stats = [BotStats(nm) for nm in seating]
            stats[g] = side.stats
            hooks = variant.new_hooks() if variant is not None else None
            try:
                tbl = GateTable(bots, rules, table_seed, mode, hooks, stats, g if proxy else None, proxy)
                res = tbl.play()
            finally:
                if proxy is not None:
                    proxy.close()
            side.points.append(res.points[g])
            side.places.append(res.places[g])
            side.busts += not res.survived[g]
            if proxy is not None:
                side.proxied = True
                side.late += proxy.late
                side.unasked += proxy.unasked
                side.rule_mismatch += proxy.rule_mismatch
                side.unsupported += proxy.unsupported
                side.lifecycle += proxy.lifecycle_errors
                for k, c in proxy.counts.items():
                    side.counts[k] = side.counts.get(k, 0) + int(c)
                if proxy.import_s is not None:
                    side.import_s.append(proxy.import_s)
                side.fatal = side.fatal or proxy.fatal
                for x in proxy.notes:
                    if len(side.notes) < 12 and x not in side.notes:
                        side.notes.append(x)
        if progress is not None and ((t + 1) % 10 == 0 or t + 1 == tables):
            progress(t + 1, pkg, base)
    return pkg, base


# ------------------------------------------------------------------ report and verdict

def row(side: Side, n_places: int) -> str:
    m, ci = mean_ci(side.points)
    st = side.stats
    d = side.decisions or 1
    dist = " ".join(f"{100 * side.places.count(i) / max(1, len(side.places)):3.0f}" for i in range(n_places))
    return (f"{side.label:<27} {len(side.points):>4} {m:6.3f} {ci:5.3f}  {dist}  "
            f"{100 * side.busts / max(1, len(side.points)):5.1f} {st.exceptions:>4} {st.illegal:>4} {side.tmo:>5} "
            f"{100 * side.tmo / d:5.2f} {side.decisions:>6} {st.percentile_us(0.5):>6.0f} {st.percentile_us(0.99):>6.0f} "
            f"{st.max_ns / 1000:>7.0f}")


def verdict(pkg: Side, base: Side, max_tmo_pct: float, load_clause: bool) -> tuple[bool, list[str], list[str]]:
    deltas = [a - b for a, b in zip(pkg.points, base.points)]
    dm, dci = mean_ci(deltas)
    fails, warns = [], []
    if pkg.fatal and not pkg.decisions:
        fails.append(f"the package never played: {pkg.fatal}")
    if pkg.stats.exceptions:
        fails.append(f"{pkg.stats.exceptions} exceptions ({pkg.stats.last_error})")
    if pkg.lifecycle:
        fails.append(f"{pkg.lifecycle} exceptions in table start or hand end")
    if pkg.stats.illegal:
        fails.append(f"{pkg.stats.illegal} illegal actions")
    rate = 100 * pkg.tmo / max(1, pkg.decisions)
    if rate > max_tmo_pct:
        msg = f"timeouts {rate:.2f}% of decisions > {max_tmo_pct:g}%"
        (warns if load_clause else fails).append(msg + (" (load average over the core count: load clause, re-run"
                                                        " on a quiet box before failing)" if load_clause else ""))
    if dm + dci < 0:
        fails.append(f"the package trails {base.label} by {-dm:.3f} points a table, beyond the paired 95% interval "
                     f"(±{dci:.3f}): the upload is not the bot the sim measured (drill 6: an adapter that dropped "
                     f"history cost 2.5)")
    return not fails, fails, warns


def unpack(src: Path, into: Path) -> Path:
    if src.is_dir():
        return src.resolve()
    if not zipfile.is_zipfile(src):
        raise SystemExit(f"FAIL {src} is neither a directory nor a zip")
    dest = into / "pkg"
    with zipfile.ZipFile(src) as zf:
        for name in zf.namelist():
            p = Path(name)
            if p.is_absolute() or ".." in p.parts:
                raise SystemExit(f"FAIL unsafe path in the zip: {name}")
        zf.extractall(dest)
    return dest


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def baseline_bot(pkg: Path, bot: str | None, dials: str | None, hero_spec: str | None,
                 hero_config: dict | None) -> tuple[tuple[str, dict], str]:
    """((name, dials) for the baseline seat, where they came from): --bot / --dials, else --hero-config, else the
    package's hyperion/ship.py record, else Hero."""
    if hero_spec and not bot:
        name = "cheap" if hero_spec.strip() == "cheap" else "hero"
        rec, where = (name, {} if name == "cheap" else dict(hero_config or {})), "--hero-config"
    else:
        record = pkg / "hyperion" / "ship.py"
        try:
            rec, where = ship.read_record(record), "the package's hyperion/ship.py"
        except (OSError, ValueError, SyntaxError):
            rec, where = ("hero", {}), "no record in the package: Hero"
    if bot or dials:
        name = bot or rec[0]
        rec = (name, ship.parse_dials(dials, name) if dials else rec[1])
        where = "--bot / --dials" if bot else where + ", --dials"
    if rec[0] not in ship.BUILDERS:
        raise SystemExit(f"FAIL baseline bot {rec[0]!r} is not in hyperion/ship.py BUILDERS ({', '.join(ship.BUILDERS)})")
    return rec, where


def check_kit(kit: str, rules: Rules, variant) -> None:
    """Refuse what a kit cannot carry rather than gate a game the bot never saw."""
    if kit == "d" and rules.straddle:
        raise SystemExit("FAIL kit d cannot carry a straddle (its first actor is the seat after the big blind)")
    if kit == "d" and variant is not None and variant.hooks is not None:
        from hyperion.drills.variants import VariantHooks

        h = type(variant.hooks)
        if h.on_street is not VariantHooks.on_street or h.on_deal is not VariantHooks.on_deal:
            raise SystemExit(f"FAIL kit d cannot carry {variant.name}: the bot replays its round from the "
                             f"round-start hole cards, and this variant changes cards mid-hand")


def find_entry(pkg: Path, entry: str | None) -> tuple:
    """(the entry's file name, None), or (None, why not). tools/pack.py copies the entry to the top of the package under
    its own name (prompt 04: `--entry submission/<entry>.py`), so with no --entry: submission.py, else the only .py
    there (a rehearsal's agent.py failed the gate on the old default)."""
    if entry is not None:
        return (entry, None) if (pkg / entry).is_file() else (None, f"no {entry}")
    if (pkg / "submission.py").is_file():
        return "submission.py", None
    tops = sorted(x.name for x in pkg.glob("*.py"))
    if len(tops) == 1:
        return tops[0], None
    return None, (f"several .py files ({', '.join(tops)}): pass --entry <the kit's entry>" if tops else "no .py file")


def lacking_tables(pkg: Path, scratch: Path) -> list[str]:
    """The tables the package's recorded bot needs and the package does not hold, by name (tools/table_probe.py in a fresh
    `python -I -B`). A package with no ship.py records no bot to check. A bot that does not build is the gate's to report
    when it plays, so it is not a table failure here."""
    if not (pkg / "hyperion" / "ship.py").is_file():
        return []
    proc = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tools" / "table_probe.py"), str(pkg)], cwd=scratch,
                          env=_env(), capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        return []
    rep = json.loads(proc.stdout.strip().splitlines()[-1])
    return [f"tables/{t}" for t in rep["lacking"]] + [f"the specialist's short_{k}: {why}"
                                                      for k, why in sorted(rep["specialist_missing"].items())]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("package", help="the submission zip, or the directory it was zipped from")
    p.add_argument("--kit", required=True, help="a | b | c | d (the fake kits) or a seat file for tonight's kit")
    p.add_argument("--kit-module", help="the kit's kit.py, importable as `kit` (default: the fake kit's)")
    p.add_argument("--entry", default=None, help="the entry file at the top of the package (default: submission.py, "
                                                 "else the package's only top-level .py)")
    p.add_argument("--tables", type=int, default=100)
    p.add_argument("--seed", type=int, default=11)
    p.add_argument("--field", default="realistic", help="a bestiary field; its `hero` seat is the one gated")
    p.add_argument("--bots", help="comma-separated bot names instead of --field (must include hero)")
    p.add_argument("--mode", choices=("strict", "measure"), default="strict")
    p.add_argument("--rules", default="default", help="'default' or a Rules JSON (rules_tonight.json)")
    p.add_argument("--variant", help="a catalog variant: its hooks, and its Rules unless --rules is a file")
    p.add_argument("--variant-seed", type=int, default=None)
    p.add_argument("--bot", help="the baseline bot (hyperion/ship.py BUILDERS name; default: the one the package "
                                 "records in its hyperion/ship.py, else hero)")
    p.add_argument("--dials", help="the baseline's dials: JSON inline or a file, or recipe names (default: the "
                                   "package's record)")
    p.add_argument("--hero-config", help="older form: Hero with these dotted Config overrides as the baseline (and in "
                                         "every other Hero seat), JSON or file, or `cheap` for Hero.cheap()")
    p.add_argument("--baseline", choices=("sim", "package"), default="sim")
    p.add_argument("--max-tmo-pct", type=float, default=0.3, help="timeouts as a share of decisions (default 0.3)")
    p.add_argument("--kit-log", choices=("auto", "yes", "no", "bets"), default="auto",
                   help="does the kit give an action log? no = the in-sim baseline sees the bare states with the log "
                        "inferred from them, as the package's adapter does (hyperion/drills/infer_history.py); bets = "
                        "the raises rebuilt from the bets only, for a package from before the inference (auto: no for "
                        "fake kits b, c, d; yes for a and a seat file)")
    a = p.parse_args(argv)

    from hyperion.sim.runner import load_hero_config, load_rules

    rules = load_rules(a.rules)
    variant = None
    if a.variant:
        from hyperion.drills import variants as _variants

        variant = _variants.get(a.variant, seed=a.seed if a.variant_seed is None else a.variant_seed)
        if a.rules == "default":
            rules = variant.rules
    names = [x.strip().lower() for x in a.bots.split(",")] if a.bots else bestiary.field_names(a.field)
    if "hero" not in names:
        raise SystemExit("FAIL the field needs a `hero` seat: the package and the baseline take turns in it")
    hero_config = CHEAP if (a.hero_config or "").strip() == "cheap" else load_hero_config(a.hero_config)
    if a.hero_config:
        bestiary.HERO_CONFIG = hero_config
    kit = a.kit.lower() if a.kit.lower() in ("a", "b", "c", "d") else "seat"
    check_kit(kit, rules, variant)

    src = Path(a.package)
    with tempfile.TemporaryDirectory(prefix="gate_") as tmp:
        tmp = Path(tmp)
        pkg = unpack(src, tmp)
        a.entry, why = find_entry(pkg, a.entry)
        if a.entry is None:
            print(f"GATE FAIL: {why} at the top of {src}")
            return 1
        kit_dir = tmp / "kit"
        kit_dir.mkdir()
        kit_src = Path(a.kit_module) if a.kit_module else (FAKEKITS / f"kit_{kit}" / "kit.py" if kit != "seat" else None)
        if kit_src is not None:
            shutil.copy2(kit_src, kit_dir / "kit.py")
        scratch = tmp / "cwd"
        scratch.mkdir()
        lacking = lacking_tables(pkg, scratch)
        if lacking:
            print(f"GATE FAIL: {src} lacks tables its recorded bot needs, and would play without them, silently: "
                  + "; ".join(lacking))
            return 1
        cfg = Config(pkg=pkg, entry=a.entry, kit=kit, kit_dir=kit_dir, scratch=str(scratch),
                     seat_file=Path(a.kit).resolve() if kit == "seat" else None)
        bot, where = baseline_bot(pkg, a.bot, a.dials, a.hero_config, hero_config)
        digest = sha256(src) if src.is_file() else "(directory)"
        field_label = f"--bots {a.bots}" if a.bots else f"field {a.field}"
        print(f"gate  {src}  sha256 {digest}")
        print(f"      kit {a.kit}, {field_label}, {a.tables} tables {a.mode}, seed {a.seed}, rules {a.rules}"
              f"{', variant ' + a.variant if a.variant else ''}, baseline {a.baseline}"
              f"{', hero-config ' + a.hero_config if a.hero_config else ''}")
        no_log: bool | str = False
        if a.kit_log == "bets":
            no_log = "bets"
        elif a.kit_log == "no" or (a.kit_log == "auto" and kit in ("b", "c", "d")):
            no_log = "shown" if kit == "d" else "next"
        seen = {"bets": "; it sees what a kit with no log gives an adapter that infers nothing (--kit-log bets)",
                "next": "; it sees what a kit with no log gives, the log inferred from the states (--kit-log no)",
                "shown": "; it sees what a kit with no log gives, the log inferred from the states and the hand "
                         "ends' deltas and showdowns (--kit-log no, kit d)"}
        print(f"      baseline bot {bot[0]} dials {bot[1]} ({where}){seen.get(no_log, '') if no_log else ''}")
        t0 = time.perf_counter()

        def progress(done, pk, bs):
            m1, _ = mean_ci(pk.points)
            m2, _ = mean_ci(bs.points)
            print(f"      {done}/{a.tables} tables  package {m1:.2f}  baseline {m2:.2f}  "
                  f"({time.perf_counter() - t0:.0f} s)", file=sys.stderr, flush=True)

        pkg_side, base_side = play(cfg, names, a.tables, a.seed, rules, variant, a.mode, a.baseline, progress,
                                   bot=bot, no_log=no_log)

    n_places = rules.n_players
    print(f"{'seat':<27} {'n':>4} {'pts':>6} {'±95%':>5}  " + " ".join(f"{'p' + str(i + 1):>3}" for i in range(n_places))
          + f"  {'bust%':>5} {'exc':>4} {'ill':>4} {'tmo':>5} {'tmo%':>5} {'calls':>6} {'p50us':>6} {'p99us':>6} {'maxus':>7}")
    print(row(pkg_side, n_places))
    print(row(base_side, n_places))
    deltas = [x - y for x, y in zip(pkg_side.points, base_side.points)]
    dm, dci = mean_ci(deltas)
    print(f"paired delta package - {base_side.label}: {dm:+.3f} ± {dci:.3f} over {len(deltas)} tables "
          f"({time.perf_counter() - t0:.0f} s)")
    if pkg_side.import_s:
        print(f"package import {max(pkg_side.import_s):.2f} s at worst over {len(pkg_side.import_s)} fresh processes")
    if kit in ("c", "d"):
        print(f"tmo for kit {kit} counts decisions after the pooled clock ran out; p50/p99/max are round trips")
    if pkg_side.rule_mismatch:
        print(f"note: {pkg_side.rule_mismatch} raises kit d's rules allow after a short all-in and ours do not; "
              f"played as calls, not counted illegal")
    if pkg_side.unsupported:
        print(f"note: {pkg_side.unsupported} variant decisions kit {a.kit} cannot carry; the dealer's default played them")
    if pkg_side.counts:
        print("note: seat counts (the kit's clock in the seat file): "
              + ", ".join(f"{k} {v}" for k, v in sorted(pkg_side.counts.items())))
    for x in pkg_side.notes:
        print(f"note: {x}")
    load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
    ok, fails, warns = verdict(pkg_side, base_side, a.max_tmo_pct, load > (os.cpu_count() or 1))
    for w in warns:
        print(f"WARN {w}")
    if ok:
        print(f"GATE PASS: the package plays like {base_side.label} ({dm:+.3f} ± {dci:.3f}), 0 exceptions, "
              f"0 illegal; sha256 {digest}")
        return 0
    print("GATE FAIL: " + "; ".join(fails))
    return 1


if __name__ == "__main__":
    sys.exit(main())
