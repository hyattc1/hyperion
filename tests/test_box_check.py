"""tools/box_check.py: the night's one line says which case the box is."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("box_check", ROOT / "tools" / "box_check.py")
BC = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BC)


def test_the_three_cases():
    assert BC.verdict({"work_ms": 6.2, "share": 1.0, "stalls_per_s": 0.0, "worst_ms": 0.3}).startswith("NORMAL")
    slow = BC.verdict({"work_ms": 12.4, "share": 0.99, "stalls_per_s": 1.0, "worst_ms": 2.0})
    assert slow.startswith("SLOW CPU, about 2.0x") and "--slow 2.0" in slow
    assert BC.verdict({"work_ms": 6.1, "share": 0.33, "stalls_per_s": 83.0, "worst_ms": 8.0}).startswith("CPU SHARE")
    assert BC.verdict({"work_ms": 18.0, "share": 0.5, "stalls_per_s": 40.0, "worst_ms": 8.0}).startswith("CPU SHARE")


def test_it_measures_with_the_standard_library_alone():
    m = BC.measure(0.05)
    assert m["work_ms"] > 0 and 0 < m["share"] <= 1.2 and m["stalls_per_s"] >= 0
