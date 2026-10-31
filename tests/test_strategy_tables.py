import os

import pytest

from hyperion.strategy import tables as T


def test_disk_tables_cover_all_classes():
    t = T.load(need_hu=True)
    assert t.source == "disk", "tables/ should be committed; load() fell back to building"
    assert set(t.equity) == set(T.CLASSES) and len(T.CLASSES) == 169
    assert all(len(v) == 7 for v in t.equity.values())
    aa = t.equity["AA"]
    assert 0.82 < aa[0] < 0.88 and all(aa[i] > aa[i + 1] for i in range(6))
    assert t.rank["AA"] > 0.99 and t.rank["32o"] < 0.02 and t.rank["AKs"] > t.rank["T9s"] > t.rank["72o"]


def test_hu_matrix_is_antisymmetric_and_in_our_order():
    t = T.load(need_hu=True)
    i, j = T.CLASS_INDEX["AA"], T.CLASS_INDEX["72o"]
    assert t.hu[i][j] > 0.85 and t.hu[j][i] == pytest.approx(1.0 - t.hu[i][j], abs=1e-6)
    assert t.hu[T.CLASS_INDEX["AKs"]][T.CLASS_INDEX["22"]] == pytest.approx(0.5, abs=0.06)
    assert all(abs(t.hu[k][k] - 0.5) < 0.06 for k in range(169))  # the generator samples the diagonal too


def test_fallback_generator_builds_everything_small():
    eq, rank = T.build_default_tables(samples=24, seed=3)
    assert set(eq) == set(T.CLASSES) and all(len(v) == 7 for v in eq.values())
    assert eq["AA"][0] > eq["72o"][0]
    assert rank["AA"] > 0.95 and set(rank) == set(T.CLASSES)
    m = T.build_hu_matrix(samples=4, seed=1)
    assert len(m) == 169 and m[0][1] == pytest.approx(1 - m[1][0])


def test_rank_from_equity_is_combo_weighted_midpoint():
    eq = {c: [0.0] * 7 for c in T.CLASSES}
    for k, c in enumerate(T.CLASSES):
        eq[c][0] = k / 169.0
    rank = T.rank_from_equity(eq)
    worst = T.CLASSES[0]
    assert rank[worst] == pytest.approx(0.5 * T.combos_of(worst) / 1326, abs=1e-4)
    assert max(rank.values()) < 1.0 and min(rank.values()) > 0.0


def test_load_from_empty_dir_builds(tmp_path):
    t = T.load(str(tmp_path), fallback_samples=8)
    assert t.source == "built" and len(t.equity) == 169
    assert not os.path.exists(tmp_path / "preflop_equity.json")  # loader never writes
