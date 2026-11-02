"""R2, instance lifetime: one ship-bot object for many tables, a fresh one per table in one process, and a fresh import
of the package per table in one process (tools/lifetime.py runs the 10,000-table version; docs/drills/climb/r2-log.md).
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(f"{name}_under_test", ROOT / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


lifetime = load_tool("lifetime")


def test_one_object_plays_each_table_as_a_fresh_one_and_keeps_nothing():
    """Model mode, two night tables: the one object's points equal a fresh object's on each, and after new_table its
    attribute graph equals a fresh object's (HeroCore._pre_aggr carried over before the fix; harmless, now reset)."""
    from hyperion.sim import bestiary as B

    saved = (B.HYBRID_CONFIG, B.HERO_CONFIG)
    try:
        assert lifetime.main(["--tables", "2", "--every", "2", "--mode", "model", "--fresh-every", "1"]) == 0
    finally:
        B.HYBRID_CONFIG, B.HERO_CONFIG = saved


def test_new_table_resets_panic_levels_and_reads():
    from hyperion import ship
    from hyperion.core.types import Rules
    from hyperion.sim import bestiary as B
    from hyperion.sim.engine import play_table

    one = ship.make_bot(seed=3)
    names = [n for n in B.field_names("realistic") if n != "hero"][:7]
    play_table([one] + [B.make_bot(nm, seed=s) for s, nm in enumerate(names)], Rules(max_hands=60), seed=4,
               mode="model")
    one.safe._enter_panic()
    one.core.set_level(2)
    one.new_table(Rules(), 2, 8)
    fresh = ship.make_bot(seed=3)
    fresh.new_table(Rules(), 2, 8)
    assert not one.safe.panic_mode and one.core.level == 0 and not one.core.panic
    assert lifetime.state_diff(one, fresh) == []


PROBE = r'''
import gc, importlib, os, sys
sys.path.insert(0, sys.argv[1])
mode, n = sys.argv[2], int(sys.argv[3])
def rss():
    return int(open("/proc/self/statm").read().split()[1]) * os.sysconf("SC_PAGE_SIZE") / 1e6
for i in range(n):
    if mode == "purge":  # a sandbox that loads the bot's modules afresh for each table
        for m in [m for m in sys.modules if m.split(".")[0] == "hyperion"]:
            del sys.modules[m]
    ship = importlib.import_module("hyperion.ship")
    T = importlib.import_module("hyperion.core.types")
    b = ship.make_bot()
    b.new_table(T.Rules(), i % 8, 8)
    del b, ship, T
    if i == 1:
        r0, f0 = rss(), gc.get_freeze_count()
print(rss() - r0, gc.get_freeze_count() - f0)
'''


def _probe(mode: str, n: int) -> tuple[float, int]:
    out = subprocess.run([sys.executable, "-I", "-c", PROBE, str(ROOT), mode, str(n)], capture_output=True, text=True,
                         timeout=300)
    assert out.returncode == 0, out.stderr[-2000:]
    mb, frozen = out.stdout.split()
    return float(mb), int(frozen)


def test_a_fresh_import_per_table_frees_the_earlier_copy():
    """Before the fix each import's gc.freeze() pinned the earlier copy for good: +28 MB a table (256 MB, kit E's cap,
    by the eighth table). Now the import collects first."""
    mb, frozen = _probe("purge", 5)
    assert mb < 20 and frozen < 2000, (mb, frozen)  # before: +84 MB and +46,000 frozen objects over these 3 tables


def test_a_fresh_object_per_table_in_one_process_frees_the_old_one():
    """Kit E's own runner: a fresh Player per table, the package cached. Before the fix every old bot object stayed
    frozen (+70 KB and ~26 tracked objects a table, 1,000 tables 70 MB); now one table start in 32 collects."""
    mb, frozen = _probe("cached", 66)
    assert frozen < 26 * 32, frozen
