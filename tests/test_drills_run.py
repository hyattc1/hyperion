import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def drill(tmp_path: Path, *args: str) -> tuple[int, dict, str]:
    cmd = [sys.executable, "-m", "hyperion.drills.run", "--auto", "--scratch", str(tmp_path / "scratch"),
           "--log-dir", str(tmp_path / "log"), "--hands", "8", "--auto-samples", "50", *args]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=300)
    logs = list((tmp_path / "log").glob("*.json"))
    assert len(logs) == 1, proc.stdout + proc.stderr
    return proc.returncode, json.loads(logs[0].read_text()), proc.stdout


@pytest.mark.parametrize("variant,kit", [("swap_holdem", "a"), ("toss_or_holdem", "c"), ("short_deck", "b")])
def test_auto_drill_hits_every_checkpoint(tmp_path, variant, kit):
    code, log, out = drill(tmp_path, "--variant", variant, "--kit", kit, "--seed", "11")
    assert code == 0, out
    assert log["variant"] == variant and log["kit"] == kit
    names = [c["name"] for c in log["checkpoints"]]
    assert names == ["legal_bot", "tables", "hero_in_sim", "final"]
    by = {c["name"]: c for c in log["checkpoints"]}
    assert by["legal_bot"]["status"] == "pass", by["legal_bot"]["detail"]
    assert by["tables"]["status"] == "pass", by["tables"]["detail"]
    assert by["hero_in_sim"]["status"] in ("pass", "degraded", "skipped")
    assert by["final"]["status"] == "pass", by["final"]["detail"]
    assert all(c["on_time"] for c in log["checkpoints"])
    scratch = Path(log["scratch"])
    assert (scratch / "kit" / "RUBRIC.md").exists() and (scratch / "variant.json").exists()
    assert (scratch / "BRIEF.md").exists() and (scratch / "tables" / "meta.json").exists()
    if variant == "toss_or_holdem":
        assert (scratch / "tables" / "hole_classes.json").exists()
    assert "twist" in out and variant in out


def test_random_pick_is_seeded(tmp_path):
    code, log, _ = drill(tmp_path, "--seed", "4")
    assert code == 0 and log["seed"] == 4 and log["variant"] in {
        "permuted_ranks", "toss_or_holdem", "swap_holdem", "bounty", "short_deck", "two_boards", "pot_limit"}
