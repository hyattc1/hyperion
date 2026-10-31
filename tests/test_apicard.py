"""The API card the agent reads on the night must match the code."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "docs" / "packet" / "CONTRACTS.md"


def test_contracts_md_is_current():
    if not CARD.exists():
        pytest.skip("docs/packet is not part of this tree")
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "apicard.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
