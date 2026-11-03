"""H7, the drill 11 fixes (docs/drills/prompt-drill-11.md, "H7"): one test or more per item that changed code or prompts.
The fake kit I below is written from the kit's handout (docs/drills/drill11/kitI-README.md), cut down: module-level
start/table/act/done, one module a session, the loader that drops the bot folder from sys.path and its modules from
sys.modules right after the import, an Overtime BaseException at the limit, chips-now ints, seats relative to us, no
legal list, the full big blind after a short blind post, uncalled chips returned (`u`), and a hand end whose `won` is
chips collected. It settles one ordinary pot (the tranches are V-j's, in the engine)."""
from __future__ import annotations

import difflib
from pathlib import Path

import pytest

from hyperion import ship

ROOT = Path(__file__).resolve().parents[1]
DRILLS = ROOT / "hyperion" / "drills"


# ---------------------------------------------------------------------------------------------- item 9
@pytest.mark.night
def test_ship_set_touches_only_the_value_it_sets(tmp_path):
    """`--set` rewrites the DIALS value only, `--bot` the SHIP string only, each in place: quotes, annotation and
    comments stay, and setting a value back gives the file back byte for byte (drill 11: --set dropped SHIP's comment)."""
    src = (ROOT / "hyperion" / "ship.py").read_text()
    copy = tmp_path / "ship.py"
    copy.write_text(src)
    ship.main(["--set", "survival"], path=copy)
    diff = [x for x in difflib.unified_diff(src.splitlines(), copy.read_text().splitlines(), lineterm="", n=0)
            if x[:1] in "+-" and not x.startswith(("+++", "---"))]
    assert len(diff) == 2 and diff[0].startswith("-DIALS: dict = ") and diff[1].startswith("+DIALS: dict = {'r3."), diff
    assert ship.read_record(copy) == (ship.SHIP, ship.recipe("survival", ship.SHIP))
    ship.main(["--set", ""], path=copy)
    assert copy.read_text() == src
    ship.main(["--bot", "hero"], path=copy)
    line = [x for x in copy.read_text().splitlines() if x.startswith("SHIP")][0]
    assert line.startswith('SHIP = "hero"  # the composite (decisions entry "Composite bot")'), line
    assert ship.read_record(copy) == ("hero", ship.DIALS)
    ship.main(["--bot", ship.SHIP], path=copy)
    assert copy.read_text() == src
    ship.write_record(copy, ship.SHIP, dict(ship.DIALS))  # tools/pack.py's call with nothing new: nothing written
    assert copy.read_text() == src
