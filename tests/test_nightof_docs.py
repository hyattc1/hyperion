"""The night-of templates and prompt edits: the adapter template imports and only raises NotImplementedError,
NIGHT-template carries prompt 01's rule sheet verbatim, the example sheet is short and labelled, and the
prompts point at the tools instead of the manual steps they replaced."""
import atexit
import re
from pathlib import Path

import pytest

from hyperion.drills import conformance
from hyperion.drills.cheapbot import CheapBot

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "docs" / "prompts"
PACKET = ROOT / "docs" / "packet"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


# --- adapter template ------------------------------------------------------------------------------

def test_adapter_template_imports_instantiates_and_defers_everything():
    from hyperion.drills.adapter_template import TonightAdapter, card, make_adapter

    a = TonightAdapter(CheapBot())
    for call in (lambda: a.to_observation({}), lambda: a.from_action(None, None, {}), lambda: a.native_safe({}),
                 lambda: card("Th")):
        with pytest.raises(NotImplementedError):
            call()
    assert isinstance(make_adapter(CheapBot()), TonightAdapter)


def test_adapter_template_make_adapter_honours_the_check_switch(monkeypatch):
    from hyperion.drills.adapter_template import make_adapter

    monkeypatch.setenv("HYPERION_CHECK", "1")
    a = make_adapter(CheapBot())
    atexit.unregister(conformance._print_report)
    assert a.conformance is not None and a.conformance.observations == 0


def test_adapter_template_todos_are_in_gotcha_order_with_a_test_each():
    src = read(ROOT / "hyperion" / "drills" / "adapter_template.py")
    order = ["CARD ENCODING", "STREET", "POT", "RAISE", "LEGAL ACTIONS", "SEATS", "BLINDS", "PER-TABLE INIT",
             "native_safe"]
    positions = [src.index(f"TODO {i}  {name}") for i, name in enumerate(order, 1)]
    assert positions == sorted(positions)
    assert src.count("Test:") >= 9 and '"10" vs "T"' in src and "suit case" in src
    for field in ("obs.hole", "obs.street", "obs.pot", "obs.min_raise", "obs.legal", "obs.seat", "obs.blinds"):
        assert field in src


# --- NIGHT template and the example --------------------------------------------------------------

def rule_sheet_bullets(text: str) -> list[str]:
    block = text.split("RULE SHEET", 1)[1].split("AXIS CLASSIFICATION", 1)[0]
    bullets, cur = [], None
    for line in block.splitlines():
        if line.startswith("- "):
            if cur:
                bullets.append(cur)
            cur = line
        elif line.startswith("  ") and cur:
            cur += " " + line.strip()
    if cur:
        bullets.append(cur)
    return [norm(b) for b in bullets]


def test_night_template_carries_prompt_01_fields_verbatim():
    prompt, template = read(PROMPTS / "01-rule-sheet.md"), read(PACKET / "NIGHT-template.md")
    bullets = rule_sheet_bullets(prompt)
    assert len(bullets) == 8
    flat = norm(template)
    for b in bullets:
        assert b in flat, b
    for axis in ("Hand strength ordering moved?", "Information moved?", "Payoff moved?", "Betting structure moved?"):
        assert axis in template
    for heading in ("## FIT VERDICT", "## ASSUMPTION DIFF", "## Submissions", "## Windows", "## sha256"):
        assert heading in template
    assert "| minute | file | sha256 | size / import | what changed | verified by |" in template
    assert "sha256sum dist/submission.zip" in template and "shasum -a 256 dist/submission.zip" in template
    assert re.search(r"^T0: ", template, re.M), "pack.py reads the T0 line to stamp the minute"
    for layer in ("evaluator", "preflop tables", "push/fold solution", "postflop rule layer", "opponent profiler",
                  "ICM curve"):
        assert layer in template and layer in prompt


def test_example_rule_sheet_is_short_and_labelled_as_a_rehearsal():
    text = read(PACKET / "EXAMPLE-rule-sheet.md")
    first = text.splitlines()[0]
    assert "EXAMPLE" in first and "NOT tonight" in first and "rehearsal" in first
    assert len(text.split()) < 400, len(text.split())
    for section in ("## RULE SHEET", "## AXIS CLASSIFICATION", "## FIT VERDICT", "## ASSUMPTION DIFF",
                    "## MOST DANGEROUS THING"):
        assert section in text
    assert "UNSPECIFIED" in text and "ENGINE CANNOT REPRESENT" in text


# --- prompts and playbook --------------------------------------------------------------------------

def test_prompt_01_has_fit_verdict_and_always_writes_rules_tonight():
    p = read(PROMPTS / "01-rule-sheet.md")
    assert "FIT VERDICT" in p and "KEEP / REGENERATE / DROP" in p and "both DROP" in p
    assert "rules_tonight.json" in p and "even when nothing moved" in p
    assert "ENGINE CANNOT REPRESENT" in p and "NIGHT-template.md" in p


def test_prompt_02_uses_the_tools_and_the_upload_cadence():
    p = read(PROMPTS / "02-adapter-and-cheap-bot.md")
    assert "adapter_template.py" in p and "HYPERION_CHECK=1" in p and "tools/pack.py" in p
    assert "five minutes" in p and "17 earliest" in p
    assert "0.3% of decisions over 1 ms" in p and "under 0.5 ms" not in p
    assert "rules_tonight.json" in p


def test_prompt_04_gates_and_tools():
    p = read(PROMPTS / "04-wire-hero.md")
    assert "--field realistic@ship --rules rules_tonight.json" in p and "omit `--rules`" not in p
    assert "--out\n   /tmp/load" in p or "--out /tmp/load" in p
    assert "Ship vs tag is not the gate" in p and "tag's minus" not in p
    assert "hyperion.ship.make_bot()" in p and "--bot hero" in p and "--bot cheap" in p
    assert "Hero.cheap()`\npackage unchanged" in p or "Hero.cheap()` package unchanged" in p
    assert "dead-seat and station" not in p
    assert "tools/latency.py" in p and "tools/pack.py" in p and "HYPERION_CHECK=1" in p
    assert "0.3% of decisions over 1 ms" in p and "under 0.5 ms" not in p


def test_prompt_05_names_only_real_config_keys():
    p = read(PROMPTS / "05-variant-patch.md")
    contracts = read(PACKET / "CONTRACTS.md")
    assert "ICM risk premium" not in p and "No ICM-premium key exists" in p
    keys = set(re.findall(r"`((?:preflop|pushfold|postflop)\.[a-z_]+)`", p))
    assert keys and all(f"`{k}`" in contracts for k in keys), keys


def _dial_keys(text: str) -> set[str]:
    """Every dial a doc names: bare Hero keys, r3.* and exploit.* keys, and hero.<key> (checked as <key>)."""
    found = set(re.findall(r'"?((?:r3|exploit|hero\.(?:preflop|pushfold|postflop)|preflop|pushfold|postflop)'
                           r'\.[a-z_]+)"?', text))
    return {k[len("hero."):] if k.startswith("hero.") else k for k in found}


def test_every_dial_the_night_docs_name_exists():
    """The window and variant dials (prompts 05 and 06, PLAYBOOK section 5) are keys the shipped bot or Hero has."""
    contracts = read(PACKET / "CONTRACTS.md")
    section5 = read(ROOT / "PLAYBOOK.md").split("## 5. The signal table", 1)[1].split("## 6.", 1)[0]
    for name, text in (("05", read(PROMPTS / "05-variant-patch.md")), ("06", read(PROMPTS / "06-windows.md")),
                       ("PLAYBOOK 5", section5)):
        keys = _dial_keys(text)
        missing = {k for k in keys if f"`{k}`" not in contracts}
        assert not missing, (name, missing)
    assert any(k.startswith("r3.") for k in _dial_keys(section5))
    from hyperion import ship

    p06 = read(PROMPTS / "06-windows.md")
    for name in ship.HERO_RECIPES:  # the windows name recipes, which resolve for whichever bot the switch names
        assert f"`{name}`" in p06 and f"`{name}`" in section5 and f"`{name}`" in contracts, name
    assert "--dials" in p06 and "python -m hyperion.ship --set" in p06
    for text in (p06, section5, read(PROMPTS / "04-wire-hero.md"), read(PROMPTS / "05-variant-patch.md")):
        assert "hybrid3_x ships" not in text and "shipped bot" not in text


def test_playbook_stage_0_prepared_list():
    pb = read(ROOT / "PLAYBOOK.md")
    assert "network off" in pb and "second machine" in pb.lower() and "never `git add -A`" in pb
    assert "night-of tooling pass" in pb
