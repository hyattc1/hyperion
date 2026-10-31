# hyperion

A millisecond poker bot and training ground for Sequoia's **No Limit: A Bot Building Tournament**
(pokerbot.sequoiacap.com). Python, stdlib only on the decision path, built to never time out.

Why it exists, what the rules force, and what wins: `docs/research/Sequoia poker bot competition prep.md`.
Build contract: `docs/specs/2026-10-31-hyperion-design.md`.

```
uv venv .venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```
