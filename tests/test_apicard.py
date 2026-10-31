"""The API card the agent reads on the night must match the code."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_contracts_md_is_current():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "apicard.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
