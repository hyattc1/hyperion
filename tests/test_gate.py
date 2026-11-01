"""tools/gate.py: the packaged bot, imported as the organisers would, played in our sim against in-sim Hero.

The proof the gate exists for: a package whose adapter drops history (drill 6) FAILS and the same package
with the reference adapter PASSES. Both packages vendor this tree but pin the Hero drill 6 shipped, which had
no inference from the bets (it landed in Hero afterwards and hides most of an adapter's loss), and both seed
Hero so the run is reproducible. The 100-table runs on drill 6's own upload are in docs/decisions.md ("Gate
the packaged bot"). Then each fake kit's path, the toss through kit A, and the parts.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

from hyperion.core.types import Action, Rules
from hyperion.drills.adapter import KitAAdapter, dealer_state
from hyperion.drills.cheapbot import CheapBot
from hyperion.drills.fakekits.kit_a.kit import to_state

from .strategy_helpers import preflop_obs, street_obs

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


gate = load_tool("gate")
pack = load_tool("pack")

PRELUDE = '''import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import hyperion.strategy.hero as _hero  # noqa: E402
from hyperion.drills.adapter import KitAAdapter, KitAAgent  # noqa: E402

if hasattr(_hero, "history_explains_bets"):  # Hero as drill 6 shipped it: nothing inferred from the bets
    _hero.history_explains_bets = lambda obs, base: True


def _bot():
    return _hero.make_bot(_hero.config_from_dict(None, seed=7))
'''
FIXED = PRELUDE + '''

class Agent(KitAAgent):
    def __init__(self):
        super().__init__(_bot())
'''
DROPS_HISTORY = PRELUDE + '''

class NoHistory(KitAAdapter):
    def to_observation(self, s):
        obs = super().to_observation(s)
        obs.history = []  # drill 6: no action log passed and nothing rebuilt
        return obs


class Agent(KitAAgent):
    def __init__(self):
        self.adapter = NoHistory(_bot())
'''
SETUP = "import os, sys\nsys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))\n"
CHEAP_ENTRIES = {
    "a": SETUP + "from hyperion.drills.adapter import KitAAgent\nfrom hyperion.strategy.hero import Hero\n\n\n"
                 "class Agent(KitAAgent):\n    def __init__(self):\n        super().__init__(Hero.cheap())\n\n"
                 "    def act(self, state):\n        if state.legal_moves == ['DISCARD']:\n            return 'DISCARD:0'\n"
                 "        return super().act(state)\n",
    "b": SETUP + "from hyperion.drills.adapter import make_kit_b_module\nfrom hyperion.strategy.hero import Hero\n\n"
                 "decide, on_table_start, on_hand_end = make_kit_b_module(Hero.cheap())\n",
    "c": SETUP + "from hyperion.drills.adapter import KitCAdapter\nfrom hyperion.strategy.hero import Hero\n\n"
                 "if __name__ == '__main__':\n    KitCAdapter(Hero.cheap()).serve()\n",
    "d": SETUP + "from kit import parse_args, run_bot  # the kit module, importable as the rules promise\n"
                 "from hyperion.drills.adapter import KitDBot\nfrom hyperion.strategy.hero import Hero\n\n"
                 "KitDBot(Hero.cheap()).adapter.start(0, 8)  # warm at import: kit D charges the round-start ack\n"
                 "if __name__ == '__main__':\n    run_bot(KitDBot(Hero.cheap()), parse_args())\n",
}


def build(tmp_path, name, source):
    src = tmp_path / f"{name}_src"
    src.mkdir()
    entry = src / "submission.py"
    entry.write_text(source)
    dest = tmp_path / name
    pack.build(dest, entry, [], False, None)
    return dest


def test_history_dropping_package_fails_and_the_fixed_one_passes(tmp_path):
    """32 tables, measure mode, the baseline seeded like the packages' Hero and played once for both. Measured
    at 48 tables: dropping history -1.71 +- 0.66, the fixed adapter +0.16 +- 0.43. Deterministic per tree."""
    from hyperion.sim import bestiary

    names = bestiary.field_names("realistic")
    bestiary.HERO_CONFIG = {"seed": 7}
    try:
        drops, base = play_pkg(tmp_path, "drops", DROPS_HISTORY, names, 32)
        fixed, _ = play_pkg(tmp_path, "fixed", FIXED, names, 32, base=base)
    finally:
        bestiary.HERO_CONFIG = None
    ok, fails, _ = gate.verdict(drops, base, 0.3, False)
    assert not ok and len(fails) == 1 and "trails hero (sim)" in fails[0] and "history" in fails[0], fails
    ok, fails, _ = gate.verdict(fixed, base, 0.3, False)
    assert ok, fails
    assert drops.stats.exceptions == fixed.stats.exceptions == 0 and drops.stats.illegal == fixed.stats.illegal == 0


def play_pkg(tmp_path, name, source, names, tables, base=None, kit="a", rules=None, variant=None):
    pkg = build(tmp_path, name, source)
    kit_dir = tmp_path / f"{name}_kit"
    kit_dir.mkdir()
    (kit_dir / "kit.py").write_bytes((gate.FAKEKITS / f"kit_{kit}" / "kit.py").read_bytes())
    scratch = tmp_path / f"{name}_cwd"
    scratch.mkdir()
    cfg = gate.Config(pkg=pkg, entry="submission.py", kit=kit, kit_dir=kit_dir, scratch=str(scratch))
    return gate.play(cfg, names, tables, 3, rules or Rules(), variant, "measure", "sim", base=base)


def play_kit(tmp_path, kit, tables=2, variant=None):
    import hyperion.drills.variants as variants
    from hyperion.sim import bestiary

    v = variants.get(variant) if variant else None
    bestiary.HERO_CONFIG = gate.CHEAP
    try:
        return play_pkg(tmp_path, f"kit_{kit}", CHEAP_ENTRIES[kit], bestiary.field_names("realistic"), tables,
                        kit=kit, rules=v.rules if v else None, variant=v)
    finally:
        bestiary.HERO_CONFIG = None


@pytest.mark.parametrize("kit", ["a", "b", "c", "d"])
def test_each_fake_kit_plays_clean(tmp_path, kit):
    pkg, base = play_kit(tmp_path, kit)
    assert len(pkg.points) == len(base.points) == 2
    assert pkg.fatal is None, pkg.notes
    assert pkg.decisions > 20 and pkg.stats.exceptions == 0 and pkg.stats.illegal == 0, (pkg.stats.last_error, pkg.notes)
    assert pkg.lifecycle == 0, pkg.notes
    if kit in ("a", "b"):
        assert pkg.import_s and max(pkg.import_s) < 30


def test_kit_a_carries_the_toss_and_the_other_kits_cannot(tmp_path):
    pkg, _ = play_kit(tmp_path, "a", tables=1, variant="toss_or_holdem")
    assert pkg.stats.illegal == 0 and pkg.stats.exceptions == 0 and pkg.unsupported == 0, pkg.notes
    with pytest.raises(SystemExit, match="kit d cannot carry toss_or_holdem"):
        import hyperion.drills.variants as variants

        v = variants.get("toss_or_holdem")
        gate.check_kit("d", v.rules, v)


def test_a_package_that_cannot_import_fails_loudly(tmp_path, capsys):
    pkg = build(tmp_path, "broken", SETUP + "import no_such_module_anywhere\n")
    assert gate.main([str(pkg), "--kit", "a", "--tables", "1", "--mode", "measure"]) == 1
    out = capsys.readouterr().out
    assert "GATE FAIL" in out and "no_such_module_anywhere" in out, out


def test_a_zip_is_unpacked_and_hashed(tmp_path, capsys):
    pkg = build(tmp_path, "zipme", CHEAP_ENTRIES["b"])
    sha = pack.make_zip(pkg, tmp_path / "submission.zip")
    assert gate.main([str(tmp_path / "submission.zip"), "--kit", "b", "--tables", "1", "--mode", "measure",
                      "--hero-config", "cheap", "--max-tmo-pct", "100"]) in (0, 1)
    out = capsys.readouterr().out
    assert f"sha256 {sha}" in out and "package import" in out, out


def test_dealer_state_round_trips_through_kit_a_with_history():
    obs = preflop_obs("Ah Kd", seat=5, button=7, actions=[(2, Action.raise_to(60)), (3, Action.fold()),
                                                          (4, Action.call())])
    back = KitAAdapter(CheapBot()).to_observation(to_state(dealer_state(obs)))
    for f in ("hole", "board", "street", "seat", "button", "stacks", "bets", "in_hand", "pot", "to_call",
              "min_raise", "max_raise", "legal", "hand_no", "blinds", "history"):
        assert getattr(back, f) == getattr(obs, f), f
    flop = street_obs("Ah Kd", "Kh 7d 2c", seat=5, pot=200, history=[(2, Action.raise_to(60)), (5, Action.call())])
    flop.extras = {"discards": {2: 51, 5: 0}}
    st = dealer_state(flop, discards_at=1)
    assert st["history"] == [[2, "raise", 60], [2, "discard", 51], [5, "discard", 0], [5, "call", 0]]
    assert to_state(st).discards == {2: "As", 5: "2c"}


def test_verdict_rules():
    def side(points, exc=0, ill=0, late=0, calls=1000):
        s = gate.Side("x", points=list(points), proxied=True, late=late)
        s.stats.exceptions, s.stats.illegal, s.stats.calls = exc, ill, calls
        return s

    base = side([5.0, 6.0, 4.0, 5.5] * 10)
    ok, fails, _ = gate.verdict(side([5.1, 5.9, 4.1, 5.4] * 10), base, 0.3, False)
    assert ok and not fails
    ok, fails, _ = gate.verdict(side([2.5, 3.5, 1.5, 3.0] * 10), base, 0.3, False)
    assert not ok and "trails" in fails[0]
    ok, fails, _ = gate.verdict(side([5.0, 6.0, 4.0, 5.5] * 10, exc=1, ill=2), base, 0.3, False)
    assert not ok and any("exceptions" in f for f in fails) and any("illegal" in f for f in fails)
    ok, fails, warns = gate.verdict(side([5.0, 6.0, 4.0, 5.5] * 10, late=50), base, 0.3, True)
    assert ok and warns and "load clause" in warns[0]
    ok, fails, _ = gate.verdict(side([5.0, 6.0, 4.0, 5.5] * 10, late=50), base, 0.3, False)
    assert not ok and "timeouts" in fails[0]


def test_a_gate_table_without_a_gate_seat_is_the_sim_table():
    """Same seating rule, same deal, same result as `python -m hyperion.sim` for one table (measure mode, so
    the clock cannot change a decision)."""
    from hyperion.sim import bestiary
    from hyperion.sim.engine import BotStats
    from hyperion.sim.runner import run_tournament

    names = bestiary.field_names("realistic")
    want = run_tournament(names, 1, seed=4, mode="measure").bots["hero"].samples[0]
    table_seed = 4 * 1_000_003
    seating = gate.seating_for(names, 8, table_seed)
    bots = [bestiary.make_bot(nm, seed=table_seed * 64 + s) for s, nm in enumerate(seating)]
    res = gate.GateTable(bots, Rules(), table_seed, "measure", None, [BotStats(nm) for nm in seating]).play()
    assert res.points[seating.index("hero")] == want


def test_playbook_and_prompts_gate_the_zip():
    read = lambda rel: (ROOT / rel).read_text()  # noqa: E731
    p02, p04 = read("docs/prompts/02-adapter-and-cheap-bot.md"), read("docs/prompts/04-wire-hero.md")
    assert "tools/gate.py dist/submission.zip" in p02 and "--hero-config cheap" in p02 and "GATE PASS" in p02
    assert "gate_seat.py" in p02 and "tools/gate_host.py" in p02
    assert "tools/gate.py dist/submission.zip" in p04 and "GATE PASS" in p04 and "every upload" in p04
    for text in (p02, p04):
        assert "--tables-dir tables" not in text  # pack.py vendors the variant set itself now
    pb = read("PLAYBOOK.md")
    stages = pb.split("## 3. The stages", 1)[1].split("## 4b.", 1)[0]
    rules = pb.split("## 7. Hard rules", 1)[1].split("## 8.", 1)[0]
    assert "`tools/gate.py` on the zip itself: GATE PASS" in stages and "tools/gate.py" in rules
    assert "Gate the packaged bot" in pb.split("## 9. Revision log", 1)[1]
    assert "tools/gate.py" in read("docs/prompts/05-variant-patch.md") and "tools/gate.py" in read(
        "docs/prompts/06-windows.md")


def test_the_baseline_is_the_bot_the_package_records(tmp_path):
    """pack.py records SHIP and DIALS in the package's hyperion/ship.py; the gate pairs against that bot in-sim."""
    from hyperion import ship

    pkg = build(tmp_path, "rec", "X = 1\n")
    assert gate.baseline_bot(pkg, None, None, None, None) == ((ship.SHIP, ship.DIALS), "the package's hyperion/ship.py")
    ship.write_record(pkg / "hyperion" / "ship.py", "hero", {"preflop.three_bet_frac": 0.05})
    assert gate.baseline_bot(pkg, None, None, None, None)[0] == ("hero", {"preflop.three_bet_frac": 0.05})
    assert gate.baseline_bot(pkg, None, None, "cheap", gate.CHEAP)[0] == ("cheap", {})
    assert gate.baseline_bot(pkg, "hybrid3_x", '{"r3.open_scale": 1.1}', None, None)[0] == \
        ("hybrid3_x", {"r3.open_scale": 1.1})
    (pkg / "hyperion" / "ship.py").unlink()
    assert gate.baseline_bot(pkg, None, None, None, None)[0] == ("hero", {})
    with pytest.raises(SystemExit):
        gate.baseline_bot(pkg, "nobody", None, None, None)


def test_a_ship_package_is_gated_against_the_ship_bot_in_sim(tmp_path):
    """The kit A reference entry builds hyperion.ship.make_bot(); 3 tables against in-sim hybrid3_x run clean."""
    from hyperion.sim import bestiary

    src = SETUP + "from hyperion.drills.adapter import KitAAgent as Agent  # noqa: F401\n"
    pkg_side, base_side = play_pkg(tmp_path, "shipped", src, bestiary.field_names("realistic"), 3)
    assert base_side.label == "hero (sim)"  # play() without bot= keeps the bestiary's Hero
    pkg = tmp_path / "shipped"
    kit_dir, scratch = tmp_path / "shipped_kit", tmp_path / "shipped_cwd"
    cfg = gate.Config(pkg=pkg, entry="submission.py", kit="a", kit_dir=kit_dir, scratch=str(scratch))
    bot, _ = gate.baseline_bot(pkg, None, None, None, None)
    pkg2, base2 = gate.play(cfg, bestiary.field_names("realistic"), 3, 3, Rules(), None, "measure", "sim", bot=bot)
    assert base2.label == "hybrid3_x (sim)" and base2.stats.calls > 0
    assert pkg2.stats.exceptions == pkg2.stats.illegal == 0 and pkg2.decisions > 0
