"""G1: the binary form of R6's solved tree (tables/extra/short_3b.bin, hyperion/strategy/short.py) holds exactly the JSON's
values, on every Python we can find; it is smaller, it is what the loader reads first, and the JSON still plays."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zlib

import pytest

from hyperion.strategy import short as S

JSON = os.path.join(S.TABLES_DIR, "extra", "short_3b.json")
BIN = os.path.join(S.TABLES_DIR, "extra", "short_3b.bin")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def from_json() -> dict:
    with open(JSON) as fh:
        raw = json.load(fh)
    nodes = json.loads(zlib.decompress(base64.b85decode(raw["z"])))
    return {"q": raw["q"], "grid": raw["grid"], "rho": raw.get("rho", [0.4]),
            "solve": {k: {"meta": raw["meta"][k]["meta"], "nodes": v} for k, v in nodes.items()}}


def digest(t: dict) -> str:
    return hashlib.sha256(json.dumps(t, sort_keys=True).encode()).hexdigest()


def test_the_same_values_every_node_every_class():
    with open(BIN, "rb") as fh:
        got = S.decode_bin(fh.read())
    want = from_json()
    assert got == want  # dict equality: every configuration, line, action string, size and strategy character
    assert sum(len(v["nodes"]) for v in got["solve"].values()) > 20000  # not vacuous


def test_the_file_is_what_the_encoder_makes_and_smaller():
    with open(JSON) as fh:
        raw = json.load(fh)
    with open(BIN, "rb") as fh:
        data = fh.read()
    assert S.encode_bin(raw) == data  # the committed file is the JSON's, byte for byte
    assert len(data) < 0.6 * os.path.getsize(JSON)


def test_the_loader_reads_the_binary_first_and_the_tables_are_equal(monkeypatch):
    monkeypatch.setattr(S, "_TABLES", {})
    got = S._load("3b")
    assert got == from_json() and "3b" not in S.MISSING


def test_the_json_still_plays_and_a_broken_binary_falls_back_to_it(tmp_path, monkeypatch):
    extra = tmp_path / "extra"
    extra.mkdir()
    shutil.copy2(JSON, extra / "short_3b.json")
    monkeypatch.setattr(S, "TABLES_DIR", str(tmp_path))
    monkeypatch.setattr(S, "_TABLES", {})
    want = from_json()
    assert S._load("3b") == want  # no binary at all: a package from before G1
    (extra / "short_3b.bin").write_bytes(b"HYPERION-SHORT-1\nnot a table")
    monkeypatch.setattr(S, "_TABLES", {})
    assert S._load("3b") == want  # a broken binary: the JSON
    os.unlink(extra / "short_3b.json")
    monkeypatch.setattr(S, "_TABLES", {})
    monkeypatch.setattr(S, "MISSING", {})
    assert S._load("3b") is None and "3b" in S.MISSING  # neither: on record, as ever (the pack and the gate fail on it)


def test_a_node_that_does_not_sum_to_q_cannot_be_encoded():
    raw = {"q": 40, "grid": [5], "rho": [0.4], "meta": {"5,5,5": {"meta": {}}},
           "z": base64.b85encode(zlib.compress(json.dumps(
               {"5,5,5": {"": {"p": 0, "a": "fc", "s": "0Y"}}}).encode())).decode()}
    with pytest.raises(ValueError):
        S.encode_bin(raw)


CHECK = """
import hashlib, json, sys
sys.path.insert(0, sys.argv[1])
from hyperion.strategy import short as S
print(hashlib.sha256(json.dumps(S._load("3b"), sort_keys=True).encode()).hexdigest())
"""


@pytest.mark.parametrize("python", ["python3.10", "python3.11", "python3.13", "python3.14"])
def test_another_python_reads_the_same_values(python):
    """The sandbox's Python may not be ours: stdlib zlib, json and bytes only, no marshal, no pickle."""
    exe = shutil.which(python)
    if exe is None:
        pytest.skip(f"no {python} on this box")
    r = subprocess.run([exe, "-I", "-B", "-c", CHECK, ROOT], capture_output=True, text=True, timeout=120)
    if r.returncode != 0 and "SyntaxError" in r.stderr:
        pytest.skip(f"the package does not import on {python}")
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == digest(from_json())
