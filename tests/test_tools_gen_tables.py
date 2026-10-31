import json
import subprocess
import sys
from pathlib import Path

import pytest

from snapcall import tablegen as tg
from snapcall.core.cards import all_hole_classes, hole_class
from snapcall.core.types import Rules, parse_cards as P

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "tools" / "gen_tables.py"


def gen(out: Path, *args: str) -> None:
    cmd = [sys.executable, str(GEN), "--out", str(out), "--workers", "2", *args]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, timeout=300)


def test_default_tiny_generation_shapes(tmp_path):
    gen(tmp_path, "--samples", "60", "--flops-per-bucket", "1")
    eq = json.loads((tmp_path / "preflop_equity.json").read_text())
    assert set(eq) == set(all_hole_classes()) and len(eq) == 169
    assert all(len(v) == 7 and all(0.0 <= x <= 1.0 for x in v) for v in eq.values())
    rank = json.loads((tmp_path / "preflop_rank.json").read_text())
    assert len(rank) == 169 and max(rank, key=rank.get) == "AA"
    assert 0 < rank["72o"] < 0.2
    m = json.loads((tmp_path / "hu_matrix.json").read_text())
    assert len(m["classes"]) == 169 and len(m["equity"]) == 169 and all(len(r) == 169 for r in m["equity"])
    i, j = m["classes"].index("AA"), m["classes"].index("22")
    assert m["equity"][i][j] + m["equity"][j][i] == pytest.approx(1.0, abs=1e-6)
    assert m["equity"][i][j] > 0.6
    fs = json.loads((tmp_path / "flop_strength.json").read_text())
    assert len(fs["buckets"]) > 100
    for key, b in fs["buckets"].items():
        q = [b["hs_quantiles"][f"p{p}"] for p in range(10, 100, 10)]
        assert q == sorted(q) and 0.0 <= q[0] and q[-1] <= 1.0, key
        assert b["n_flops"] > 0 and "example" in b
        assert abs(sum(c["share"] for c in b["categories"].values()) - 1.0) < 0.01
    meta = json.loads((tmp_path / "meta.json").read_text())
    assert meta["samples"] == 60 and meta["rules"]["hole_cards"] == 2
    assert not (tmp_path / "hole_classes.json").exists()


def test_three_card_permuted_rules_emit_hole_classes(tmp_path):
    perm = list(range(13))[::-1]
    rules = {"hole_cards": 3, "rank_order": perm, "extras": {"variant": "t", "keep": 2}}
    (tmp_path / "rules.json").write_text(json.dumps(rules))
    out = tmp_path / "out"
    gen(out, "--rules", str(tmp_path / "rules.json"), "--samples", "60", "--skip-matrix",
        "--flops-per-bucket", "1", "--max-holdings", "300")
    hc = json.loads((out / "hole_classes.json").read_text())
    assert hc["scheme"] == "best2+tags" and hc["hole_cards"] == 3
    eq = json.loads((out / "preflop_equity.json").read_text())
    assert set(eq) == set(hc["classes"]) and len(eq) > 169
    assert all("+" in k for k in eq)
    assert sum(hc["classes"].values()) == 22100  # C(52, 3)
    assert not (out / "hu_matrix.json").exists()
    meta = json.loads((out / "meta.json").read_text())
    assert meta["rules"]["rank_order"] == perm and meta["rules"]["extras"]["variant"] == "t"


def test_short_deck_extras_shrink_the_deck():
    rules = tg.rules_from_dict({"extras": {"removed_ranks": [0, 1, 2, 3]}})
    assert len(tg.live_deck(rules)) == 36
    classes = tg.class_table(rules)
    assert "22" not in classes and "AA" in classes and sum(len(v) for v in classes.values()) == 630


def test_hole_label_matches_169_for_two_cards():
    for cls in ("AKs", "AKo", "TT", "72o"):
        combo = tg.class_table(Rules())[cls][0]
        assert tg.hole_label(combo) == hole_class(combo) == cls


def test_hole_label_three_cards_tags():
    assert tg.hole_label(P("Ah Kh 2c")) == "AKs+l"
    assert tg.hole_label(P("Ah Kh Kd")) == "KK+s" or tg.hole_label(P("Ah Kh Kd")) == "AKs+p"
    assert tg.hole_label(P("Qc Qd Qh")) == "QQ+p"
    assert tg.hole_label(P("9c 8c Ad")).endswith("+h") or tg.hole_label(P("9c 8c Ad")).startswith("A")


def test_texture_key_and_canonical_flops():
    assert tg.texture_key(P("Ah Kh Qh")) == "unpaired-mono-connected-A"
    assert tg.texture_key(P("Kc Kh 7h")) == "paired-twotone-dry-K"
    assert tg.texture_key(P("5c 5d 5h")) == "trips-rainbow-none-5"
    assert tg.texture_key(P("Jc 8d 2s")) == "unpaired-rainbow-dry-J"
    flops = tg.canonical_flops(tuple(range(52)))
    assert len(flops) == 1755 and sum(w for _, w in flops) == 22100


def test_rules_round_trip():
    r = Rules(hole_cards=3, rank_order=tuple(range(13))[::-1], extras={"x": 1})
    d = tg.rules_to_dict(r)
    assert json.loads(json.dumps(d)) == d
    assert tg.rules_from_dict(d) == r and tg.rules_from_dict(d).extras == {"x": 1}
