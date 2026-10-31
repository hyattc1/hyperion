"""A push/fold cache solved from an older heads-up matrix must be detected and re-solved."""
import json
import os

from hyperion.strategy import tables as T
from hyperion.strategy.pushfold import build_pushfold_tables, load_pushfold, matrix_fingerprint


def _tiny_tables():
    t = T.load(need_hu=True)
    return t


def test_fingerprint_changes_when_matrix_changes():
    t = _tiny_tables()
    fp = matrix_fingerprint(t.hu)
    mutated = [row[:] for row in t.hu]
    mutated[0][1] = round(1.0 - mutated[0][1], 4)
    assert matrix_fingerprint(mutated) != fp


def test_stale_cache_is_resolved(tmp_path):
    t = _tiny_tables()
    sol = build_pushfold_tables(t, str(tmp_path), depths=(5, 10), write=True)
    assert sol["matrix_fp"] == matrix_fingerprint(t.hu)
    # pretend the matrix was regenerated: corrupt the stored fingerprint
    p = tmp_path / "pushfold_hu.json"
    raw = json.loads(p.read_text())
    raw["matrix_fp"] = "deadbeef"
    p.write_text(json.dumps(raw))
    fresh = load_pushfold(t, str(tmp_path))
    assert fresh["matrix_fp"] == matrix_fingerprint(t.hu)
    assert json.loads(p.read_text())["matrix_fp"] == matrix_fingerprint(t.hu)
