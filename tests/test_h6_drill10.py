"""H6, the drill 10 fixes (docs/drills/prompt-drill-10.md, "H6"): one test or more per item that changed code."""
import hashlib
import importlib.util

import pytest

from hyperion.compose import bot as CB
from hyperion.compose import register
from hyperion.drills import variants as V
from hyperion.sim import bestiary as B
from hyperion.sim.runner import run_tournament
from hyperion.strategy import hero as H

HC = {"panic_after": 10 ** 9}  # nothing reads the wall clock in these tests
HYB = {"panic_after": 10 ** 9, "soft_us": 1e6}


@pytest.fixture
def sim():
    saved = (B.HYBRID_CONFIG, dict(B.REGISTRY), dict(B._BY_CLASS), B.HERO_CONFIG)
    B.HYBRID_CONFIG = dict(HYB)
    yield
    B.HYBRID_CONFIG, B.HERO_CONFIG = saved[0], saved[3]
    B.REGISTRY.clear()
    B.REGISTRY.update(saved[1])
    B._BY_CLASS.clear()
    B._BY_CLASS.update(saved[2])


# ---------------------------------------------------------------------------------------------- item 2
def _play_f(variant, seats: list, seeds: int = 1):
    """(sha1 of every decision and variant answer F made in Hero's seat of `realistic`, every bot's per-seed points)."""
    h = hashlib.sha1()
    cls = register("_h6_f", dials={**CB.SHIP_DIALS, "light": True})

    class T(cls):
        def __init__(self, seed=None):
            super().__init__(seed)
            seats.append(self.impl)

        def act(self, o):
            a = super().act(o)
            h.update(repr((o.hand_no, o.street, a.kind.value, a.amount)).encode())
            return a

        def variant_decide(self, prompt):
            ans = super().variant_decide(prompt)
            h.update(repr(("v", prompt.get("decision"), ans)).encode())
            return ans

    B.REGISTRY["_h6_t"] = T
    rep = run_tournament(B.field_names("realistic@_h6_t"), seeds, seed=7, rotate=False, mode="model", hero_config=HC,
                         variant=variant)
    return h.hexdigest(), {k: v.samples for k, v in rep.bots.items()}


def _hero_whole() -> list:
    """The catalog entries the base's core cannot play (13 at H6: short deck, lowball, the three-card games ...)."""
    from hyperion.hybrid.bot import HybridConfig, table_reason

    cfg = HybridConfig(hero_on_bounty=False)  # as F's base (SHIP_DIALS base.hero_on_bounty)
    return [n for n in V.catalog_names() if table_reason(V.get(n).rules, cfg) is not None]


@pytest.mark.parametrize("name", _hero_whole())
def test_hero_whole_table_plays_as_before_without_the_second_hand_end(sim, monkeypatch, name):
    """On a table the base's core cannot play, the hero member plays the base's sections and the base's fallback Hero
    sleeps (no decision, no shadow, no hand end): every decision, variant answer and point is what the old routing (the
    base's Hero deciding its sections, both Heros' hand ends) gives on the same deals."""
    v = V.get(name)
    calls = {}
    real_he = H.HeroCore.hand_end

    def counting(self, result):
        calls[id(self)] = calls.get(id(self), 0) + 1
        return real_he(self, result)

    monkeypatch.setattr(H.HeroCore, "hand_end", counting)
    new_seats: list = []
    new = _play_f(v, new_seats)
    core = new_seats[-1].core
    assert core._whole and core.base.asleep
    assert calls.get(id(core.base.hero), 0) == 0 and calls[id(core.members[core._hero_idx])] > 20
    assert not any(k.endswith(":base") for k in core.counts), core.counts

    real_init = CB.CompositeCore.__init__

    def old_routing(self, config=None):
        real_init(self, config)
        self._same_hero = False  # as before H6: the base's Hero decides the base's sections and pays its hand end

    monkeypatch.setattr(CB.CompositeCore, "__init__", old_routing)
    old_seats: list = []
    old = _play_f(v, old_seats)
    oc = old_seats[-1].core
    assert not oc._whole and calls[id(oc.base.hero)] > 20 and any(k.endswith(":base") for k in oc.counts)
    assert new == old


def test_plain_holdem_keeps_the_base(sim):
    """Plain hold'em: the base's core plays its sections and its Hero stays awake, as before."""
    seats: list = []
    _play_f(None, seats)
    core = seats[-1].core
    assert not core._whole and not core.base.asleep
    assert any(k.endswith(":base") for k in core.counts)


# ---------------------------------------------------------------------------------------------- item 3
from hyperion.core.types import Action, ActionKind  # noqa: E402
from hyperion.drills.adapter import make_observation  # noqa: E402
from hyperion.strategy.postflop import Postflop, PostflopParams  # noqa: E402

SOLO = "hyperion/drills/solo_example.py:variant"
_R, _S = "23456789TJQKA", "cdhs"


def _c(text: str) -> list:
    return [_R.index(x[0]) * 4 + _S.index(x[1]) for x in text.split()]


@pytest.mark.parametrize("hole,board,tier,outs", [
    ("Ah Kd", "Ac 9h 4d", 5, 0),  # top pair (the drill 10 player's printed spot)
    ("9s 2c", "Ac 9h 4d", 4, 0),  # middle pair
    ("4s 2c", "Ac 9h 4d", 2, 0),  # bottom pair
    ("Qs Jc", "Ac 9h 4d", 0, 0),  # nothing: no overcard to the ace
    ("As 2c", "Ac Ah 4d", 7, 0),  # trips: our card on the board's pair
    ("4s 2c", "Ac Ah 4d", 4, 0),  # two pair under the board's pair
    ("Kd 2c", "Ac Ah 4d", 2, 0),  # the board's pair is everyone's: a king kicker
    ("Ad 2c", "Ac Ah As", 8, 0),  # quads
    ("2h 3c", "Ah 9h 4h", 1, 9),  # a flush draw: one heart of ours, the board one short of the four it must supply
    ("Th 3c", "Jc Qd 9h", 1, 8),  # an open-ender with one card
    ("3c 3d", "Jc Qd 9h", 0, 0),  # a pocket pair is one card
])
def test_short_board_read_tiers_solo_flops(hole, board, tier, outs):
    t, o, _ = Postflop(PostflopParams()).read_short(_c(hole), _c(board), 1)
    assert (t, o) == (tier, outs)


def test_short_board_read_is_the_must_use_read_of_a_short_board_only():
    """_read sends must-use-k to read_short only while the board has fewer than the 5 - k cards it must supply: Solo's
    flop, never its turn or river, never Omaha's flop (three, the three it needs)."""
    pf = Postflop(PostflopParams())
    seen = []
    pf.read_short = lambda *a, **k: seen.append(len(a[1])) or (0, 0, False)
    pf._read(_c("Ah Kd"), _c("Ac 9h 4d"), 1, ())
    pf._read(_c("Ah Kd"), _c("Ac 9h 4d 2s"), 1, ())
    pf._read(_c("Ah Kd 7c 7d"), _c("Ac 9h 4d"), 2, ())
    assert seen == [3]


def _solo_flop_obs(to_call: int):
    """Hand 1 of Solo at 10/20: seat 3 (us) opened to 60, the big blind (seat 2) called; the flop A-9-4, the big blind
    bets 40 into 130 (`to_call` 40) or checks (0). Our A-K: top pair."""
    hist = [(3, Action(ActionKind.RAISE, 60))] + [(s, Action(ActionKind.FOLD)) for s in (4, 5, 6, 7, 0, 1)] + \
        [(2, Action(ActionKind.CALL))]
    bets = [0] * 8
    stacks = [2000, 1990, 1940, 1940, 2000, 2000, 2000, 2000]
    if to_call:
        hist.append((2, Action(ActionKind.RAISE, 40)))
        bets[2], stacks[2] = 40, 1900
    in_hand = [s in (2, 3) for s in range(8)]
    legal = ["fold", "call", "raise"] if to_call else ["check", "raise"]
    return make_observation(hole=_c("Ah Kd"), board=_c("Ac 9h 4d"), street=1, seat=3, button=0, stacks=stacks,
                            bets=bets, in_hand=in_hand, pot=130, legal=legal, hand_no=0, blinds=(10, 20), history=hist)


@pytest.mark.parametrize("on", [True, False])
def test_f_plays_the_solo_flop(on):
    """F (the composite; Hero plays a must-use table whole) with top pair on Solo's flop: before H6 it folded to a bet
    and checked when checked to; with the short-board read it calls or raises the bet and bets when checked to."""
    from hyperion import ship

    v = V.get(SOLO)
    for to_call in (40, 0):
        bot = ship.make_bot(dials={"hero.mu_short_board": on}, seed=1)
        bot.new_table(v.rules, 3, 8)
        a = bot.act(_solo_flop_obs(to_call))
        hero = bot.core.members[bot.core._hero_idx]
        if on:
            assert hero.last_path.startswith(("postflop", "exploit"))
            assert a.kind in ((ActionKind.CALL, ActionKind.RAISE) if to_call else (ActionKind.RAISE,)), a
        else:
            assert hero.last_path == "safe"
            assert a.kind is (ActionKind.FOLD if to_call else ActionKind.CHECK)


def test_omaha_plays_the_same_with_the_short_board_read_off(sim):
    """The one catalog entry with a must-use rule (omaha_four: must use two, so the flop is the three it needs) never
    reaches the short-board read: F plays it decision for decision with `mu_short_board` on or off."""
    assert [n for n in V.catalog_names() if V.get(n).rules.must_use_hole] == ["omaha_four"]
    v = V.get("omaha_four")
    runs = []
    for on in (True, False):
        h = hashlib.sha1()
        cls = register("_h6_mu", dials={**CB.SHIP_DIALS, "light": True, "hero.mu_short_board": on})

        class T(cls):
            def act(self, o):
                a = super().act(o)
                h.update(repr((o.hand_no, o.street, a.kind.value, a.amount)).encode())
                return a

        B.REGISTRY["_h6_mu_t"] = T
        rep = run_tournament(B.field_names("realistic@_h6_mu_t"), 1, seed=7, rotate=False, mode="model",
                             hero_config=HC, variant=v)
        runs.append((h.hexdigest(), {k: r.samples for k, r in rep.bots.items()}))
    assert runs[0] == runs[1]


def test_solo_variant_file_and_its_tables():
    """The Solo variant file registers, validates, and Hero finds its committed tables (tables/variants/solo/)."""
    from hyperion.strategy import tables as T

    v = V.get(SOLO)
    assert v.name == "solo" and v.rules.must_use_hole == 1 and not V.validate(v)
    t = T.tables_for(v.rules)
    assert t.source == "disk" and len(t.equity) == 169
    assert t.equity["AKo"][0] > t.equity["AA"][0] > t.equity["22"][0]  # a pocket pair is one card


# ---------------------------------------------------------------------------------------------- item 1
import json  # noqa: E402
import os  # noqa: E402
import select  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402
import sys  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
DRILLS = ROOT / "hyperion" / "drills"


def _process_entry(tmp_path: Path) -> Path:
    """The process template as tonight's bot.py, beside the drill 10 player's kit-H adapter, Solo's rules and the
    local-check marker (the kit's fixed environment never carries HYPERION_CHECK)."""
    from hyperion.tablegen import rules_to_dict

    d = tmp_path / "sub"
    d.mkdir()
    shutil.copy(DRILLS / "process_entry_template.py", d / "bot.py")
    shutil.copy(ROOT / "docs" / "drills" / "drill10" / "adapter.py", d / "adapter.py")
    (d / "rules_tonight.json").write_text(json.dumps(rules_to_dict(V.get(SOLO).rules)))
    (d / "check.on").write_text("")
    return d


class FakeEngine:
    """Kit H's engine side, cut down (its engine/botproc.py): the bot as its own process, JSON lines, the kit's fixed
    environment (plus PYTHONPATH: this repo, since the folder has no vendored package), replies matched by id."""

    def __init__(self, folder: Path):
        env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "PYTHONUNBUFFERED": "1", "LANG": "C.UTF-8",
               "PYTHONPATH": str(ROOT)}
        self.err = open(folder / "stderr.log", "wb")
        self.p = subprocess.Popen([sys.executable, "-u", "bot.py"], cwd=folder, stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=self.err, bufsize=0, env=env)
        self.buf, self.next_id = b"", 0

    def send(self, *msgs) -> list:
        """Write every message in one go (a burst: none waits for its reply); returns their ids."""
        ids, data = [], b""
        for m in msgs:
            ids.append(self.next_id)
            data += (json.dumps(dict(m, id=self.next_id)) + "\n").encode()
            self.next_id += 1
        os.write(self.p.stdin.fileno(), data)
        return ids

    def replies(self, k: int, timeout: float = 120.0) -> list:
        out, end = [], time.monotonic() + timeout
        fd = self.p.stdout.fileno()
        while len(out) < k:
            i = self.buf.find(b"\n")
            if i >= 0:
                out.append(json.loads(self.buf[:i]))
                self.buf = self.buf[i + 1:]
                continue
            r, _, _ = select.select([fd], [], [], max(0.0, end - time.monotonic()))
            assert r, f"no reply after {len(out)} of {k}"
            chunk = os.read(fd, 65536)
            assert chunk, "the bot closed stdout"
            self.buf += chunk
        return out

    def close(self) -> str:
        self.p.stdin.close()
        self.p.wait(timeout=60)
        self.err.close()
        return (Path(self.err.name)).read_text()


def _hand(hand: int, street: int, to_call: int):
    """A kit H act for us ("me", the button of three: a small blind, b big blind): preflop first to act; on a later
    street after a and b checked through, with b's bet of `to_call` (0: checked to us). Chips add up to 6,000."""
    board = [8, 22, 37, 40, 5][:(0, 3, 4, 5)[street]]
    if not street:
        pl = [{"h": "a", "stack": 1990, "bet": 10, "total": 10, "state": "live"},
              {"h": "b", "stack": 1980, "bet": 20, "total": 20, "state": "live"},
              {"h": "me", "stack": 2000, "bet": 0, "total": 0, "state": "live"}]
        return {"t": "act", "table": 1, "hand": hand, "sb": 10, "bb": 20, "you": "me", "button": "me",
                "cards": [48, 45], "board": [], "pot": 30, "to_call": 20, "min_r": 20, "max_r": 1980, "players": pl,
                "log": ""}
    pl = [{"h": "a", "stack": 1980, "bet": 0, "total": 20, "state": "live"},
          {"h": "b", "stack": 1980 - to_call, "bet": to_call, "total": 20 + to_call, "state": "live"},
          {"h": "me", "stack": 1980, "bet": 0, "total": 20, "state": "live"}]
    log = "me:c a:c b:k" + "/a:k b:k me:k" * (street - 1) + "/a:k b:" + ("r%d" % to_call if to_call else "k")
    return {"t": "act", "table": 1, "hand": hand, "sb": 10, "bb": 20, "you": "me", "button": "me", "cards": [48, 45],
            "board": board, "pot": 60 + to_call, "to_call": to_call, "min_r": max(20, to_call),
            "max_r": 1980 - to_call, "players": pl, "log": log}


def _end(hand: int) -> dict:
    return {"t": "end", "table": 1, "hand": hand, "board": [8, 22, 37, 40, 5], "log": "me:c a:c b:k/a:k b:k/a:k b:k",
            "shown": {"a": [0, 1], "b": [2, 3], "me": [48, 45]}, "best": {}, "won": {"me": 60},
            "stacks": {"a": 1980, "b": 1980, "me": 2040}, "out": []}


def _ok_action(a) -> bool:
    return a in ("f", "c") or (isinstance(a, str) and a[:1] == "r" and a[1:].isdigit())


def test_process_entry_round_trips_and_keeps_order_under_a_burst(tmp_path):
    """The template as its own process: one reply per request, in order, each echoing its id, the decisions legal;
    then a burst written at once (hand ends, decisions, a table end and the next table start, none waiting for its
    reply): every reply still in order, and the hand ends that found a message waiting were skipped, not run late."""
    eng = FakeEngine(_process_entry(tmp_path))
    try:
        seq = [{"t": "hello", "proto": 1, "you": "me", "seats": 3, "stack": 2000},
               {"t": "table", "table": 1, "seats": ["a", "b", "me"], "button": "me", "stack": 2000, "max_hands": 200}]
        seq += [_hand(1, st, 0) for st in range(4)] + [_end(1)]
        for m in seq:  # one at a time, as the kit sends them: one message in flight
            (mid,) = eng.send(m)
            (r,) = eng.replies(1)
            assert r["id"] == mid and (("a" in r) == (m["t"] == "act"))
            if m["t"] == "act":
                assert _ok_action(r["a"]), r
        burst = [_hand(2, 0, 0), _end(2), _hand(3, 0, 0), _hand(3, 1, 40), _end(3), _end(4),
                 {"t": "over", "table": 1, "hands": 4, "results": []},
                 {"t": "table", "table": 2, "seats": ["me", "a", "b"], "button": "a", "stack": 2000, "max_hands": 200},
                 dict(_hand(1, 0, 0), table=2)]
        ids = eng.send(*burst)
        got = eng.replies(len(burst))
        assert [r["id"] for r in got] == ids
        for m, r in zip(burst, got):
            assert ("a" in r) == (m["t"] == "act") and (m["t"] != "act" or _ok_action(r["a"])), (m["t"], r)
    finally:
        err = eng.close()
    assert eng.p.returncode == 0, err
    assert "swallowed errors 0;" in err, err  # check.on: the exit line, under the kit's fixed environment
    assert " 0 violations" in err, err  # ... and the conformance report (HYPERION_CHECK set from the marker)
    skipped = int(err.split("skipped with a message waiting")[1].split("hand_end")[1].split(",")[0].split()[0])
    assert skipped >= 1, err


def test_process_entry_imports_quietly(tmp_path):
    """Imported (tools/pack.py's probe prints its timing on stdout after importing the entry), the template leaves
    stdout alone; run as the kit's process it writes only replies there."""
    d = _process_entry(tmp_path)
    probe = "import sys; sys.path.insert(0, sys.argv[1]); import bot; print('probe-line')"
    r = subprocess.run([sys.executable, "-c", probe, str(d)], capture_output=True, text=True, timeout=300,
                       env={**os.environ, "PYTHONPATH": str(ROOT)})
    assert r.returncode == 0 and r.stdout.strip().splitlines()[-1] == "probe-line", (r.stdout, r.stderr)


def test_the_gate_drives_the_process_loop_through_a_pipe(tmp_path):
    """tools/gate.py with the process gate seat: the package's bot is launched as its own process and every decision,
    hand end and table start goes through its stdin loop; one table plays clean (no exception, no illegal answer)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("h6_gate", ROOT / "tools" / "gate.py")
    gate = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = gate
    spec.loader.exec_module(gate)
    spec = importlib.util.spec_from_file_location("h6_pack", ROOT / "tools" / "pack.py")
    pack = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = pack
    spec.loader.exec_module(pack)

    d = _process_entry(tmp_path)
    (d / "check.on").unlink()  # never shipped
    dest = tmp_path / "pkg"
    pack.build(dest, d / "bot.py", [d / "adapter.py", d / "rules_tonight.json"], True, None)
    shutil.copy(DRILLS / "process_gate_seat_template.py", tmp_path / "gate_seat.py")
    scratch = tmp_path / "cwd"
    scratch.mkdir()
    v = V.get(SOLO)
    cfg = gate.Config(pkg=dest, entry="bot.py", kit="seat", kit_dir=Path("-"), scratch=str(scratch),
                      seat_file=tmp_path / "gate_seat.py")
    pkg, _ = gate.play(cfg, B.field_names("realistic"), 1, 3, v.rules, v, "measure", "sim")
    assert pkg.fatal is None, pkg.notes
    assert pkg.decisions > 10 and pkg.stats.exceptions == 0 and pkg.stats.illegal == 0, (pkg.stats.last_error, pkg.notes)
    assert pkg.lifecycle == 0, pkg.notes


# ---------------------------------------------------------------------------------------------- item 4
GEN = ROOT / "tools" / "gen_tables.py"
TINY = ["--samples", "60", "--matrix-samples", "20", "--flops-per-bucket", "1", "--max-holdings", "300"]


def _gen(out: Path, *args: str) -> str:
    r = subprocess.run([sys.executable, str(GEN), "--out", str(out), "--workers", "2", *args], capture_output=True,
                       text=True, timeout=600, check=True)
    return r.stdout


def test_gen_tables_loaded_preset_accuracy_and_unbuffered_progress(tmp_path):
    """`--preset loaded` sets drill 10's numbers (3,000 / 50 / 2 flops / 300 holdings), prints the 95% interval they
    buy before the run and records it; an explicit flag wins over the preset (here the tiny test sizes). Progress is
    flushed as it goes, a line a tenth of each long stage, so a backgrounded run redirected to a file shows where it
    is (drill 10's generator printed nothing until it ended)."""
    spec = importlib.util.spec_from_file_location("h6_gen", GEN)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    assert g.PRESETS["loaded"] == {"samples": 3000, "matrix_samples": 50, "flops_per_bucket": 2, "max_holdings": 300}
    acc = g.accuracy(3000, 50, 169)
    assert acc["preflop_cell"] == pytest.approx(1.96 * 0.5 / 3000 ** 0.5, abs=1e-4)
    assert acc["matrix_cell"] == pytest.approx(0.1386, abs=1e-3) and acc["matrix_range20"] < 0.025
    p = subprocess.Popen([sys.executable, str(GEN), "--out", str(tmp_path), "--workers", "2", "--preset", "loaded",
                          *TINY], stdout=subprocess.PIPE, text=True)
    first = p.stdout.readline()  # arrives while the run is going, not at its end
    still_running = p.poll() is None
    rest = p.stdout.read()
    assert p.wait(timeout=600) == 0
    assert still_running and first.startswith("accuracy (95%, worst case): preflop cell +-0.127"), first
    assert "[preset loaded]" in first
    assert sum(1 for ln in rest.splitlines() if ln.strip().startswith("preflop:")) >= 9, rest
    assert sum(1 for ln in rest.splitlines() if ln.strip().startswith("hu_matrix:")) >= 9, rest
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["samples"] == 60 and meta["matrix_samples"] == 20 and meta["preset"] == "loaded"
    assert meta["accuracy_95"]["matrix_cell"] == pytest.approx(0.2191, abs=1e-3)


def test_gen_tables_resume_keeps_the_finished_stages(tmp_path):
    """A run stopped after its preflop stage (drill 10 killed its generator in the matrix stage and wrote gen_rest.py):
    `--resume` keeps the preflop files byte for byte, runs the matrix, the push/fold re-solve and the flops, and the
    meta says what was kept. Other card rules keep nothing."""
    _gen(tmp_path, *TINY)
    pre = (tmp_path / "preflop_equity.json").read_bytes()
    for f in ("hu_matrix.json", "pushfold_hu.json", "flop_strength.json"):
        (tmp_path / f).unlink()
    meta = json.loads((tmp_path / "meta.json").read_text())
    (tmp_path / "meta.json").write_text(json.dumps({"rules": meta["rules"], "samples": 60, "seed": 2026,
                                                     "partial": True, "done": ["preflop"], "used": {"preflop": 60}}))
    out = _gen(tmp_path, "--resume", "--samples", "999", "--matrix-samples", "20", "--flops-per-bucket", "1",
               "--max-holdings", "300")
    assert "resume: kept preflop" in out and "preflop:" not in out, out
    assert (tmp_path / "preflop_equity.json").read_bytes() == pre
    assert all((tmp_path / f).exists() for f in ("hu_matrix.json", "pushfold_hu.json", "flop_strength.json"))
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["samples"] == 60 and meta["resumed"]["kept"] == ["preflop"] and "partial" not in meta
    # a run from before `done` existed: the files say what finished
    (tmp_path / "flop_strength.json").unlink()
    (tmp_path / "meta.json").write_text(json.dumps({"rules": meta["rules"], "samples": 60, "partial": True}))
    out = _gen(tmp_path, "--resume", *TINY)
    assert "resume: kept preflop, hu_matrix, pushfold" in out, out
    # other card rules: nothing kept
    (tmp_path / "rules.json").write_text(json.dumps({"must_use_hole": 1}))
    out = _gen(tmp_path, "--resume", "--rules", str(tmp_path / "rules.json"), "--skip-matrix", *TINY)
    assert "resume: kept nothing" in out, out


# ---------------------------------------------------------------------------------------------- item 5
PACK = ROOT / "tools" / "pack.py"


def test_pack_checks_the_zipped_and_the_unzipped_cap_apart(tmp_path):
    """Kit H's caps are 5 MB zipped and 20 MB unzipped: drill 10's `--max-mb 5` checked the unzipped package against
    the zipped cap. --max-mb is the unzipped cap, --max-zip-mb the zipped one, and the zip line prints both."""
    (tmp_path / "agent.py").write_text("from hyperion.strategy.hero import make_bot\nBOT = make_bot()\n")

    def run(*caps):
        return subprocess.run([sys.executable, str(PACK), "--entry", "agent.py", "--out", "dist", "--slim",
                               "--import-budget", "60", *caps], cwd=tmp_path, capture_output=True, text=True,
                              timeout=600)

    r = run("--max-mb", "20", "--max-zip-mb", "5")  # kit H's caps: the slim package passes both
    assert r.returncode == 0, r.stdout + r.stderr
    assert "zipped of 5 MB" in r.stdout and "unzipped of 20 MB" in r.stdout and "budget 60 s" in r.stdout, r.stdout
    r = run("--max-mb", "20", "--max-zip-mb", "0.5")
    assert r.returncode == 1 and "FAIL zip is" in r.stdout and "(--max-zip-mb)" in r.stdout, r.stdout
    r = run("--max-mb", "1", "--max-zip-mb", "5")
    assert r.returncode == 1 and "unzipped, limit 1 MB" in r.stdout, r.stdout


# ---------------------------------------------------------------------------------------------- found on the way
def test_climb_accept_names_a_short_chunk_by_its_length():
    """A set's last chunk shorter than CHUNK (10025-10039 of 10000:10040) has a file of its own: before H6 a 200-seed
    run read a 40-seed run's 15-sample chunk as its 25 and played 190 seeds. Full chunks keep their names."""
    spec = importlib.util.spec_from_file_location("h6_ca", ROOT / "tools" / "climb_accept.py")
    ca = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ca)
    cell = ("realistic", "lin", None, "omaha_four", 10025)
    full, short = ca.cell_path("o", "k", cell), ca.cell_path("o", "k", cell, 15)
    assert full.endswith("realistic.lin.-.omaha_four.10025.json") and full == ca.cell_path("o", "k", cell, ca.CHUNK)
    assert short.endswith("realistic.lin.-.omaha_four.10025.n15.json") and short != full
