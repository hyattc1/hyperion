"""The public export of this repo carries no denylisted term, drops the private material, and the
tool catches a planted term and squashes history. Strict on purpose: a hit here means the public
surface regressed and must be scrubbed, not waived."""
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "export_public.py"


def _load():
    spec = importlib.util.spec_from_file_location("export_public", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(TOOL), *args], capture_output=True, text=True, timeout=300)


def test_export_of_this_repo_is_clean(tmp_path):
    out = tmp_path / "public"
    r = run("--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    for rel in ("README.md", "pyproject.toml", ".gitignore", "hyperion/core/types.py", "hyperion/strategy",
                "tables/README.md", "tables/preflop_rank.json", "tools/gen_tables.py", "tests/test_eval.py",
                "docs/specs/2026-10-31-hyperion-design.md"):
        assert (out / rel).exists(), rel
    for rel in (".git", ".venv", ".pytest_cache", "__pycache__", "docs/research", "docs/drills", "docs/packet",
                "docs/prompts", "docs/night-of.md", "docs/decisions.md", "PLAYBOOK.md", "drills/log",
                "drills/scratch", "scratch", ".publicignore", "tools/export_public.py",
                "tests/test_export_public.py"):
        assert not (out / rel).exists(), rel
    assert not list(out.rglob("__pycache__")) and not list(out.rglob("*.pyc"))


def test_planted_term_fails_the_export(tmp_path):
    mod = _load()
    src = tmp_path / "src"
    (src / "pkg").mkdir(parents=True)
    (src / "README.md").write_text("# a clean readme\n")
    (src / "pkg" / "a.py").write_text("x = 1\n# built for " + mod.DENYLIST_PHRASES[0].title() + "'s event\n")
    (src / "pkg" / "b.bin").write_bytes(b"\0\0" + mod.DENYLIST_PHRASES[0].encode())  # binary: copied, not scanned
    r = run("--source", str(src), "--out", str(tmp_path / "out"))
    assert r.returncode == 1, r.stdout + r.stderr
    assert "pkg/a.py:2:" in r.stdout
    assert "b.bin" not in r.stdout
    assert (tmp_path / "out" / "pkg" / "a.py").exists()  # left in place for inspection


def test_denylisted_path_is_a_hit(tmp_path):
    mod = _load()
    src = tmp_path / "src"
    d = src / ("notes " + mod.DENYLIST_PHRASES[0])
    d.mkdir(parents=True)
    (d / "x.md").write_text("nothing here\n")
    r = run("--source", str(src), "--out", str(tmp_path / "out"))
    assert r.returncode == 1 and "(path)" in r.stdout


def test_publicignore_and_builtin_excludes_apply(tmp_path):
    src = tmp_path / "src"
    for rel in ("docs/research/r.md", "docs/packet/c.md", "PLAYBOOK.md", "NIGHT1.md", "drills/log/a.json",
                "private/secret.md", "keep/ok.md", "deep/__pycache__/x.pyc", "top.md"):
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("fine\n")
    (src / ".publicignore").write_text("# comment\nprivate/\n__pycache__/\n")
    out = tmp_path / "out"
    r = run("--source", str(src), "--out", str(out))
    assert r.returncode == 0, r.stdout + r.stderr
    assert sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()) == ["keep/ok.md", "top.md"]


def test_pattern_semantics():
    m = _load().matches
    assert m("docs/research/x.md", "docs/research/")
    assert not m("docs/research.md", "docs/research/")
    assert m("a/b/__pycache__/c.pyc", "__pycache__/")
    assert m("a/b/c.pyc", "*.pyc")
    assert m("NIGHT2.md", "NIGHT*.md") and not m("docs/NIGHT2.md", "/NIGHT*.md")
    assert m("docs/NIGHT2.md", "NIGHT*.md")
    assert m("PLAYBOOK.md", "PLAYBOOK.md") and not m("docs/PLAYBOOK.md", "/PLAYBOOK.md")


def test_denylist_shapes():
    rx = _load().DENYLIST
    for s in ("Nov 6", "nov. 12", "November 15", "NOV 9", "mitpokerbots/engine", "MIT-Pokerbots", "the Finals"):
        assert rx.search(s), s
    for s in ("November 2026", "nov 16", "2026-11-12", "sit-and-go", "ICM at the cap", "hold'em", "a tournament"):
        assert not rx.search(s), s


def test_init_git_squashes_to_one_commit(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "README.md").write_text("# clean\n")
    out = tmp_path / "out"
    r = run("--source", str(src), "--out", str(out), "--init-git")
    assert r.returncode == 0, r.stdout + r.stderr
    n = subprocess.run(["git", "-C", str(out), "rev-list", "--count", "HEAD"], capture_output=True, text=True, check=True)
    assert n.stdout.strip() == "1"
    msg = subprocess.run(["git", "-C", str(out), "log", "-1", "--format=%B"], capture_output=True, text=True, check=True)
    assert not _load().DENYLIST.search(msg.stdout)


def test_refuses_nonempty_output_without_force(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.md").write_text("x\n")
    out = tmp_path / "out"
    out.mkdir()
    (out / "stale").write_text("old\n")
    assert run("--source", str(src), "--out", str(out)).returncode == 2
    r = run("--source", str(src), "--out", str(out), "--force")
    assert r.returncode == 0 and not (out / "stale").exists() and (out / "a.md").exists()
