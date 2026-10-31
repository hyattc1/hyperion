"""The Track B spec is pasted into a context window on the night: it stays short, keeps its minute-ordered
checkpoints, and carries the drill-3 fixes that would otherwise regress silently."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "prompts" / "track-b-from-scratch.md"
PROMPT_02 = ROOT / "docs" / "prompts" / "02-adapter-and-cheap-bot.md"

CHECKPOINTS = [
    "## Step 0 (minutes 0–2)",
    "## Step 1 (by minute 15)",
    "## Step 2 (by minute 30)",
    "## Step 2b (minutes 30–33)",
    "## Step 3 (by minute 45)",
    "## Step 3b (minutes 45–50)",
    "## Step 4 (if time remains)",
    "## The gate",
]


def spec() -> str:
    return SPEC.read_text(encoding="utf-8")


def flat() -> str:
    """The spec with line wraps collapsed, for phrase checks that must survive a reflow."""
    return re.sub(r"\s+", " ", spec())


def test_spec_stays_under_1600_words():
    n = len(spec().split())
    assert n < 1600, n


def test_spec_has_the_checkpoint_headings_in_minute_order():
    text = spec()
    positions = [text.index(h) for h in CHECKPOINTS]
    assert positions == sorted(positions)
    assert text.count("\n## ") == len(CHECKPOINTS)
    assert "by minute 15" in text.split("## Step 2 (")[0], "the cheap bot by 15 is the first checkpoint"


def test_spec_defines_the_terms_drill_3_found_undefined():
    text = flat()
    for term in ("Effective stack", "Shove =", "Top pair =", "Outs:", "Pot =", "Percent of hands =", "1,326",
                 "button 0, cutoff 1, hijack 2"):
        assert term in text, term


def test_spec_keeps_icm_off_the_decision_path_and_gates_only_calls():
    text = flat()
    assert "never run it inside `act`" in text
    assert "interpolate" in text and "hand-end callback" in text
    assert "never before an open shove" in text
    assert "REMAP[displayed] = strength" in text and "before anything else" in text


def test_spec_uses_rate_and_p99_not_max():
    text = flat()
    assert "0.3 percent of calls over 1 ms" in text and "p99 under 500 µs" in text
    assert not re.search(r"max (must be )?under \d+ µs", text)
    assert "2,000 samples" in text and "QQ above JJ" in text and "A3o outside the top 12 percent" in text
    assert "points did not drop" not in text


def test_prompt_02_track_b_paragraph_matches_v2_step_1():
    p = PROMPT_02.read_text(encoding="utf-8")
    block = re.sub(r"\s+", " ", p.split("Track B (blank directory):", 1)[1])
    for phrase in ("one file, no vendoring", "test_bot.py", "bench.py", "a call is not required", "p99 under 500 µs",
                   "rank map at parse time", "0.3% of calls over 1 ms"):
        assert phrase in block, phrase
