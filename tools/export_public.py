"""Build a clean public export of this repo at an output directory.

    python tools/export_public.py --out /tmp/hyperion-public [--init-git] [--force] [--source DIR]

Copies the current tree (tracked and untracked files, .gitignore respected when git is available)
minus a built-in exclusion set, minus every pattern in `.publicignore` at the repo root, and minus
the scrub tooling itself (this file, its test, `.publicignore`). Then every exported path and text
file is checked against a denylist of identifying terms; any hit is printed as file:line and the
exit code is 1, with the export left in place for inspection. `--init-git` runs `git init` in the
export and makes one squashed commit, so no history travels with it. Prints a summary.

The denylist is case-insensitive and deliberately broad; a false positive costs a look, a miss costs
more. Exit codes: 0 clean, 1 denylist hits, 2 usage or I/O error.
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# What a public reader must never see. Plain phrases, matched case-insensitively as substrings.
DENYLIST_PHRASES: tuple[str, ...] = (
    "sequoia",
    "sequoiacap",
    "pokerbot.sequoiacap.com",
    "no limit: a bot",
    "bot building tournament",
    "citadel",
    "openai",
    "astra",
    "codex",
    "menlo park",
    "regional",
    "finals",
    "mit pokerbots",
    "november 6/9/12/15",
)
# Regular expressions for the shapes a phrase list cannot spell: the event dates in any spelling, and
# the competition name with or without the space.
DENYLIST_REGEXES: tuple[str, ...] = (
    r"\bnov(?:ember)?\.? ?(?:6|9|12|15)\b",
    r"\bmit[ -]?pokerbots\b",
)
DENYLIST = re.compile(
    "|".join([re.escape(p) for p in DENYLIST_PHRASES] + list(DENYLIST_REGEXES)), re.IGNORECASE
)

# Always excluded, whether or not .publicignore exists.
BUILTIN_EXCLUDES: tuple[str, ...] = (
    ".git/",
    ".venv/",
    "docs/research/",
    "docs/drills/",
    "docs/packet/",
    "docs/prompts/",
    "PLAYBOOK.md",
    "docs/night-of.md",
    "drills/log/",
    "NIGHT*.md",
)
# The scrub tooling names the denylist, so it never ships.
SELF_EXCLUDES: tuple[str, ...] = (
    ".publicignore",
    "tools/export_public.py",
    "tests/test_export_public.py",
)
IGNORE_FILE = ".publicignore"


# ----------------------------------------------------------------------------- patterns


def load_patterns(source: Path) -> list[str]:
    """Built-in excludes, then `.publicignore` lines (comments and blanks dropped), then the tooling."""
    pats = list(BUILTIN_EXCLUDES)
    f = source / IGNORE_FILE
    if f.exists():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                pats.append(line)
    pats.extend(SELF_EXCLUDES)
    return pats


def matches(rel: str, pattern: str) -> bool:
    """gitignore-flavoured match of one posix relative file path against one pattern.

    Trailing slash: directories only (a file matches through an ancestor). A leading slash or a slash
    inside the pattern anchors it to the root and it is matched against the path and each ancestor
    path; otherwise it is matched against every single path segment. `*` and `?` are fnmatch globs.
    """
    dir_only = pattern.endswith("/")
    pat = pattern.rstrip("/")
    anchored = pat.startswith("/") or "/" in pat
    pat = pat.lstrip("/")
    parts = rel.split("/")
    if anchored:
        upto = len(parts) - 1 if dir_only else len(parts)
        candidates = ["/".join(parts[: i + 1]) for i in range(upto)]
    else:
        candidates = parts[:-1] if dir_only else parts
    return any(fnmatch.fnmatchcase(c, pat) for c in candidates)


def excluded(rel: str, patterns: list[str]) -> str | None:
    """The first pattern that excludes `rel`, or None."""
    for p in patterns:
        if matches(rel, p):
            return p
    return None


# ----------------------------------------------------------------------------- enumeration


def list_files(source: Path) -> list[str]:
    """Relative posix paths of every file in the tree. Uses git when the source is a repo (tracked
    plus untracked, .gitignore honoured, .git skipped), otherwise walks the directory."""
    try:
        r = subprocess.run(
            ["git", "-C", str(source), "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True, check=True,
        )
        rels = [p.decode("utf-8", "surrogateescape") for p in r.stdout.split(b"\0") if p]
        return sorted({p for p in rels if (source / p).is_file()})
    except (OSError, subprocess.CalledProcessError):
        pass
    out: list[str] = []
    for dirpath, dirnames, filenames in os.walk(source):
        dirnames[:] = sorted(d for d in dirnames if d != ".git")
        for name in sorted(filenames):
            p = Path(dirpath) / name
            if p.is_file():
                out.append(p.relative_to(source).as_posix())
    return out


# ----------------------------------------------------------------------------- scanning


def is_text(data: bytes) -> bool:
    return b"\0" not in data[:8192]


def scan_text(text: str) -> list[tuple[int, str]]:
    """(line number, line) for every line that contains a denylisted term."""
    hits = []
    for i, line in enumerate(text.splitlines(), 1):
        if DENYLIST.search(line):
            hits.append((i, line.strip()))
    return hits


def scan_export(out: Path, rels: list[str]) -> list[str]:
    """`file:line: text` for every hit in the exported paths and text files."""
    findings: list[str] = []
    for rel in rels:
        if DENYLIST.search(rel):
            findings.append(f"{rel}:0: (path) {rel}")
        data = (out / rel).read_bytes()
        if not is_text(data):
            continue
        for n, line in scan_text(data.decode("utf-8", "replace")):
            findings.append(f"{rel}:{n}: {line[:160]}")
    return findings


# ----------------------------------------------------------------------------- export


def _inside(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def export(source: Path, out: Path, force: bool = False) -> tuple[list[str], list[tuple[str, str]]]:
    """Copy the public set of `source` into `out`. Returns (copied rels, [(rel, pattern)] excluded)."""
    source = source.resolve()
    out = out.resolve()
    if out == source or _inside(source, out):
        raise SystemExit(f"refusing: output {out} contains the source tree")
    if out.exists() and any(out.iterdir()):
        if not force:
            raise SystemExit(f"refusing: {out} exists and is not empty (use --force to replace it)")
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    patterns = load_patterns(source)
    out_rel = out.relative_to(source).as_posix() + "/" if _inside(out, source) else None
    copied: list[str] = []
    skipped: list[tuple[str, str]] = []
    for rel in list_files(source):
        if out_rel and rel.startswith(out_rel):
            continue
        why = excluded(rel, patterns)
        if why:
            skipped.append((rel, why))
            continue
        dst = out / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / rel, dst)
        copied.append(rel)
    return copied, skipped


def init_git(out: Path) -> str:
    """`git init` plus one squashed commit of everything in `out`. Returns the short sha."""
    git = ["git", "-C", str(out)]
    subprocess.run(["git", "init", "-q", str(out)], check=True)
    subprocess.run(git + ["checkout", "-q", "-B", "main"], check=True)
    subprocess.run(git + ["add", "-A"], check=True)  # the export dir only; never run in the repo
    ident = []
    for key, fallback in (("user.name", "hyperion"), ("user.email", "hyperion@localhost")):
        r = subprocess.run(git + ["config", "--get", key], capture_output=True, text=True)
        if not r.stdout.strip():
            ident += ["-c", f"{key}={fallback}"]
    subprocess.run(["git", "-C", str(out), *ident, "commit", "-q", "-m", "Initial import"], check=True)
    r = subprocess.run(git + ["rev-parse", "--short", "HEAD"], capture_output=True, text=True, check=True)
    return r.stdout.strip()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="output directory for the export")
    ap.add_argument("--source", type=Path, default=ROOT, help="tree to export (default: this repo)")
    ap.add_argument("--init-git", action="store_true", help="git init the export with one squashed commit")
    ap.add_argument("--force", action="store_true", help="replace a non-empty output directory")
    args = ap.parse_args(argv)

    source: Path = args.source.resolve()
    if not source.is_dir():
        print(f"error: source {source} is not a directory", file=sys.stderr)
        return 2
    try:
        copied, skipped = export(source, args.out, force=args.force)
    except SystemExit as e:  # refusal with a message
        print(f"error: {e}", file=sys.stderr)
        return 2
    out = args.out.resolve()
    findings = scan_export(out, copied)
    nbytes = sum((out / r).stat().st_size for r in copied)

    print(f"export:   {out}")
    print(f"source:   {source}")
    print(f"copied:   {len(copied)} files, {nbytes:,} bytes")
    print(f"excluded: {len(skipped)} files")
    by_rule: dict[str, int] = {}
    for _, why in skipped:
        by_rule[why] = by_rule.get(why, 0) + 1
    for why, n in sorted(by_rule.items(), key=lambda kv: (-kv[1], kv[0])):
        print(f"          {n:5d}  {why}")
    if findings:
        print(f"denylist: {len(findings)} hit(s); the export is NOT publishable, left in place for inspection")
        for f in findings:
            print(f"  {f}")
        return 1
    print("denylist: 0 hits")
    if args.init_git:
        sha = init_git(out)
        print(f"git:      initialised, one commit {sha}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
