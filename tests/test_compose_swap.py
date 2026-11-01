"""tools/swap.py's shortcut is exact: replaying only the rotations where a donor disagrees gives the same points as
replaying every rotation, and the base run is hybrid3_x's own game."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _swap():
    spec = importlib.util.spec_from_file_location("swap_tool", ROOT / "tools" / "swap.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["swap_tool"] = m  # the pool's workers find its job functions by module name
    spec.loader.exec_module(m)
    return m


def test_shortcut_matches_full_replay(tmp_path):
    sw = _swap()
    cells = "pre_hu:hero,post_mw:rival1,pre_allin:hybrid3"
    for sub in ("short", "full"):
        out = tmp_path / sub
        sw.main(["base", "--field", "realistic", "--seeds", "0:2", "--out", str(out), "--workers", "2", "--chunk", "4",
                 "--donors", "hero,hybrid3,rival1"])
        sw.main(["cells", "--field", "realistic", "--seeds", "0:2", "--out", str(out), "--workers", "2", "--chunk", "4",
                 "--cells", cells] + (["--full"] if sub == "full" else []))
    d = {sub: tmp_path / sub / "realistic.lin.0-2" / "base" for sub in ("short", "full")}
    base = json.loads((d["short"] / "base.json").read_text())
    pts = {(r[0], r[1]): r[2] for r in base["rows"]}
    # the base run is hybrid3_x's own game
    from hyperion.sim import bestiary as B
    from hyperion.sim.runner import run_tournament

    sw.setup_process()
    rep = run_tournament(B.field_names("realistic@hybrid3_x"), 2, seed=7, rotate=True, mode="model",
                         hero_config=sw.HERO_CONFIG)
    assert rep.bots["hybrid3_x"].samples == sw.per_seed(pts, range(2))
    for c in cells.split(","):
        s, dn = c.split(":")
        short = json.loads((d["short"] / f"cell.{s}.{dn}.json").read_text())
        full = json.loads((d["full"] / f"cell.{s}.{dn}.json").read_text())
        merged = dict(pts)
        merged.update({(r[0], r[1]): r[2] for r in short["rows"]})
        assert full["replayed"] == 16 and short["replayed"] <= 16
        assert {(r[0], r[1]): r[2] for r in full["rows"]} == merged


def test_dial_variants_shortcut_matches_full_replay(tmp_path):
    """A dial change recorded in the base run (a copy of the base member, the layer's read-time params, a read param
    replayed in full) gives the same points shortcut or full, on top of a route."""
    sw = _swap()
    var = '{"open": {"r3.open_scale": 1.2}, "bf": {"exploit.bet_frac": 0.5}, "decay": {"exploit.decay": 0.9}}'
    cells = "var:open,var:bf,var:decay"
    for sub in ("short", "full"):
        out = tmp_path / sub
        sw.main(["base", "--field", "realistic", "--seeds", "0:1", "--out", str(out), "--workers", "2", "--chunk", "4",
                 "--donors", "hero", "--route", "post_hu_bet=hero", "--variants", var])
        sw.main(["cells", "--field", "realistic", "--seeds", "0:1", "--out", str(out), "--workers", "2", "--chunk", "4",
                 "--route", "post_hu_bet=hero", "--cells", cells] + (["--full"] if sub == "full" else []))
    d = {sub: tmp_path / sub / "realistic.lin.0-1" / "post_hu_bet~hero" for sub in ("short", "full")}
    pts = {(r[0], r[1]): r[2] for r in json.loads((d["short"] / "base.json").read_text())["rows"]}
    for n in ("open", "bf", "decay"):
        short = json.loads((d["short"] / f"cell.var.{n}.json").read_text())
        full = json.loads((d["full"] / f"cell.var.{n}.json").read_text())
        merged = dict(pts)
        merged.update({(r[0], r[1]): r[2] for r in short["rows"]})
        assert {(r[0], r[1]): r[2] for r in full["rows"]} == merged
    assert json.loads((d["short"] / "cell.var.decay.json").read_text())["replayed"] == 8  # a read param: in full
