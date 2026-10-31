"""hyperion.strategy.multiway: the multiway push/fold solver, the shipped table and its loader."""
import json
import os
import shutil
import time

import pytest

from hyperion.strategy import multiway as MW
from hyperion.strategy.tables import CLASS_INDEX, CLASSES, COMBO_COUNT, TABLES_DIR, Tables, load, read_json

I = CLASS_INDEX


@pytest.fixture(scope="module")
def tables():
    return load(need_hu=True)


@pytest.fixture(scope="module")
def ctx(tables):
    return MW.Ctx(tables.hu, tables.live, [tables.rank[c] for c in CLASSES])


@pytest.fixture(scope="module")
def mw(tables):
    got = MW.load_multiway(tables)
    if got is None:
        pytest.skip("tables/pushfold_multi.json missing or stale: run tools/gen_multiway.py")
    return got


def _diff(a, b) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


# ---------------------------------------------------------------- (i) k = 1 is the heads-up game

def test_k1_matches_the_heads_up_table_at_every_depth(mw):
    hu = read_json("pushfold_hu.json", TABLES_DIR)
    for S in range(2, 26):
        assert _diff(mw["push"][1][S], hu["push"][str(S)]) <= 2, S
        assert _diff(mw["call"]["bb"][1][S], hu["call"][str(S)]) <= 2, S
        assert abs(mw["p_push"][1][S] - hu["p_push"][str(S)]) < 0.01
        assert abs(mw["p_call"]["bb"][1][S] - hu["p_call"][str(S)]) < 0.01


def test_fresh_k1_solve_matches_the_heads_up_table(ctx):
    hu = read_json("pushfold_hu.json", TABLES_DIR)
    r = MW.solve_first_in(ctx, 1, depths=(3, 6, 10, 15, 20))
    for i, S in enumerate(r["S"]):
        assert _diff(r["push"][i], hu["push"][str(S)]) <= 2, S
        assert _diff(r["call"]["bb"][i], hu["call"][str(S)]) <= 2, S


# ---------------------------------------------------------------- (ii) shape of the solution

def test_push_frequency_falls_with_players_behind_and_with_depth(mw):
    # tolerance 0.005 (combo share). S = 2 is excluded on purpose: there k >= 3 shoves a little wider than
    # k = 2 (a non-blind caller leaves both blinds dead), as RangeMyHand's 2 bb rows do (BTN 0.814, CO 0.826).
    for S in range(3, 26):
        for k in range(1, 7):
            assert mw["p_push"][k + 1][S] <= mw["p_push"][k][S] + 0.005, (k, S)
    for k in range(1, 8):
        for S in range(2, 25):
            assert mw["p_push"][k][S + 1] <= mw["p_push"][k][S] + 0.005, (k, S)
    assert mw["p_push"][7][10] < 0.15 < mw["p_push"][2][10] < 0.4 < mw["p_push"][1][10]


def test_aa_always_shoves_and_72o_folds_at_10bb_with_three_or_more_behind(mw):
    assert all(mw["push"][k][S][I["AA"]] for k in range(1, 8) for S in range(2, 26))
    assert all(mw["call"][t][k][S][I["AA"]] for k in range(1, 8) for t in mw["types"][k] for S in range(2, 26))
    for k in range(3, 8):
        assert mw["push"][k][10][I["72o"]] == 0
    assert mw["push_order"][7][I["AA"]] == 0.0 and mw["push_order"][7][I["72o"]] > 0.9


# ---------------------------------------------------------------- (iii) pnc and eqc

def test_pnc_and_eqc_are_probabilities(mw):
    for k in range(1, 8):
        for S in range(2, 26):
            for key in ("pnc", "eqc", "eq_vs_push"):
                v = mw[key][k][S]
                assert len(v) == 169 and all(0.0 <= x <= 1.0 for x in v), (key, k, S)
    # AA is called less often when it blocks the callers' aces, and is a favourite when called
    assert mw["pnc"][7][10][I["AA"]] > mw["pnc"][7][10][I["KK"]] > mw["pnc"][7][10][I["76s"]]
    assert mw["eqc"][7][10][I["AA"]] > 0.8 and mw["eqc"][7][10][I["72o"]] < 0.35


def test_pnc_falls_as_callers_are_added_with_their_strategies_fixed(ctx, mw):
    # The structural property. Across equilibria pnc does NOT fall with k: with more players behind the
    # shover tightens, so each caller tightens too, and the fold-through chance stays roughly flat
    # (S = 10: 0.63, 0.61, 0.61, 0.62, 0.64, 0.65, 0.65 for k = 1..7). Holding the k = 7 call sets fixed
    # and adding callers in front, pnc must fall for every class.
    S = 10
    c = {t: [float(x) for x in mw["call"][t][7][S]] for t in MW.TYPES}
    p = [float(x) for x in mw["push"][7][S]]
    prev = None
    for k in range(2, 8):
        seq, posted, steal, sup = MW.first_in_spec(ctx, k)(S)
        keys, _, _ = MW._prep(ctx, seq, sup)
        _, _, pnc, _ = MW._shover_eval(ctx, S, seq, posted, steal, keys, p, {t: c[t] for t in keys})
        if prev is not None:
            assert all(pnc[i] <= prev[i] + 1e-12 for i in ctx.live_idx), k
        prev = pnc
    # and the equilibrium drift across k is small: combo-mean pnc within 0.03 of k = 1 at 10 bb
    def mean(k):
        return sum(COMBO_COUNT[i] * mw["pnc"][k][S][i] for i in range(169)) / 1326
    assert all(abs(mean(k) - mean(1)) < 0.03 for k in range(2, 8))


def test_pot_accounting_at_the_extremes(ctx):
    # nobody ever calls: shoving wins the 1.5 blinds (shove minus fold = 1.5 for a non-blind shover)
    S = 10.0
    n = ctx.n
    for k in (1, 4):
        seq, posted, steal, sup = MW.first_in_spec(ctx, k)(S)
        keys, by_key, sup_idx = MW._prep(ctx, seq, sup)
        p = [1.0] * n
        none = {t: [0.0] * n for t in keys}
        br, _, pnc, _ = MW._shover_eval(ctx, S, seq, posted, steal, keys, p, none)
        assert all(x == 1.0 for x in pnc) and steal + posted == 1.5
        # the first responder always calls: shove minus fold = e_vs_random (2S + dead_first) - S + posted
        everyone = {t: [1.0] * n for t in keys}
        dead = 1.5 - posted - MW.POSTED[seq[0].key]
        br, g, pnc, eqc = MW._shover_eval(ctx, S, seq, posted, steal, keys, p, everyone)
        for cls in ("AA", "T9s", "72o"):
            i = I[cls]
            G = ctx.eq_rand[i] * (2 * S + dead) - S + posted
            assert pnc[i] == 0.0 and eqc[i] == pytest.approx(ctx.eq_rand[i])
            assert br[i] == (1.0 if G > 0 else 0.0)
        # a responder facing "shove everything" calls with e_vs_random > (S - posted) / (2S + dead)
        br_c, T_c, Wp, _ = MW._resp_eval(ctx, S, by_key, sup_idx, p)
        r = by_key[seq[-1].key]
        i = I["Q7o"]
        assert br_c[r.key][i] == (1.0 if ctx.eq_rand[i] > (S - r.posted) / (2 * S + r.dead) else 0.0)
    # re-shove, BB (m = 0), opener never calls: R takes the opener's 2.3 and the SB's 0.5 (+1 vs folding the BB)
    seq_fn, op = MW.reshove_spec(ctx, 0.25, 0)
    seq, posted, steal, sup = seq_fn(S)
    keys, _, _ = MW._prep(ctx, seq, sup)
    br, _, pnc, _ = MW._shover_eval(ctx, S, seq, posted, steal, keys, [1.0] * n, {"o": [0.0] * n})
    assert posted == 1.0 and steal == pytest.approx(2.8) and all(x == 1.0 for x in pnc)


# ---------------------------------------------------------------- re-shove sanity

def test_reshove_widens_with_the_openers_range_and_the_opener_calls_inside_it(tables, mw):
    rs = mw["reshove"]
    ws = rs["w"]
    for m in range(rs["m_max"] + 1):
        for S in range(rs["S_min"], rs["S_max"] + 1):
            for wi in range(len(ws) - 1):
                assert rs["p_push"][wi + 1][m][S] >= rs["p_push"][wi][m][S] - 0.005, (m, S, wi)
            for wi, w in enumerate(ws):
                oc = rs["ocall"][wi][m][S]
                assert all(not oc[i] or tables.rank[c] >= 1 - w - 1e-9 for i, c in enumerate(CLASSES))
                assert all(0.0 <= x <= 1.0 for x in rs["pnc"][wi][m][S] + rs["eqc"][wi][m][S])
                assert rs["push"][wi][m][S][I["AA"]] == 1
    # the BB against a 25% opener at 15 bb: a plausible re-shove range; deep-stack branch at 8 bb with 4 behind
    wi = MW.nearest_w(mw, 0.25)
    assert 0.12 < rs["p_push"][wi][0][15] < 0.3
    assert max(x for x in rs["p_bcall"][wi][4][8] if x is not None) < 0.5


# ---------------------------------------------------------------- (iv) a tiny solve end to end

def test_tiny_grid_solve_round_trips_through_the_loader(tables, tmp_path):
    t0 = time.time()
    sol = MW.solve_all(tables, workers=1, k_grid=(1, 3), s_grid=(5, 10), w_grid=(0.25,), m_grid=(0, 2),
                       rs_s_grid=(10, 12), max_iters=300)
    assert time.time() - t0 < 15
    assert sol["matrix_fp"] and sol["classes"] == list(CLASSES) and sol["model"]
    assert sol["first_in"]["k"] == [1, 3] and len(sol["first_in"]["push"][1][1]) == 169
    assert all(it <= 300 for row in sol["first_in"]["converged"] for it, _ in row)
    (tmp_path / MW.FILE).write_text(json.dumps(sol))
    shaped = MW.load_multiway(tables, str(tmp_path))
    assert shaped is not None and shaped["k_max"] == 3 and shaped["S_min"] == 5
    assert shaped["push"][3][10] == sol["first_in"]["push"][1][1] and shaped["push"][2] is None
    assert shaped["call"]["n"][1] is None and len(shaped["call"]["n"][3][5]) == 169
    rs = shaped["reshove"]
    assert rs["w"] == (0.25,) and len(rs["push"][0][2][12]) == 169 and rs["p_bcall"][0][0][10] == [None, None, None]
    assert MW.depth(shaped, 3) == 5 and MW.depth(shaped, 40) == 10 and MW.depth(rs, 11.4) == 11


# ---------------------------------------------------------------- (v) the loader refuses stale files

def test_loader_returns_none_on_a_fingerprint_mismatch_or_a_missing_file(tables, tmp_path):
    src = os.path.join(TABLES_DIR, MW.FILE)
    if not os.path.exists(src):
        pytest.skip("no shipped table")
    stale = tmp_path / "stale"
    stale.mkdir()
    with open(src) as f:
        raw = json.load(f)
    raw["matrix_fp"] = "0000000000000000"
    (stale / MW.FILE).write_text(json.dumps(raw))
    assert MW.load_multiway(tables, str(stale)) is None
    assert MW.load_multiway(tables, str(tmp_path / "nowhere")) is None
    broken = tmp_path / "broken"
    broken.mkdir()
    (broken / MW.FILE).write_text('{"version": 1, "matrix_fp": "x"')  # truncated
    assert MW.load_multiway(tables, str(broken)) is None
    # a matching copy loads; a different matrix with the same file does not
    good = tmp_path / "good"
    good.mkdir()
    shutil.copy(src, good / MW.FILE)
    assert MW.load_multiway(tables, str(good)) is not None
    other_hu = [row[:] for row in tables.hu]
    other_hu[0][1] = round(other_hu[0][1] + 0.01, 4)
    other = Tables(tables.equity, tables.rank, other_hu, "disk", str(good))
    assert MW.load_multiway(other, str(good)) is None
    assert MW.load_multiway(Tables(tables.equity, tables.rank, None, "disk", str(good))) is None


def test_loader_is_memoised(tables, mw):
    assert MW.load_multiway(tables) is mw
