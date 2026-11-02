"""The fake kits are self-contained: each kit (a, b, c, d, e_style) imports and plays with `hyperion` absent, so a
drill can copy one verbatim into a blank directory (drill 3, repo finding 1). The vendored evaluator orders
hands exactly as hyperion.core.eval does, so the dealer's showdowns are unchanged."""
import os
import random
import shutil
import subprocess
import sys
import textwrap
from itertools import combinations
from pathlib import Path

import pytest

from hyperion.core import eval as real_eval
from hyperion.drills.fakekits import _eval

ROOT = Path(__file__).resolve().parents[1]
FAKEKITS = ROOT / "hyperion" / "drills" / "fakekits"

# A legal do-nothing bot per kit, written against the kit's own interface only.
BOTS = {
    "a": """
        class Agent:
            def new_game(self, my_index, n_players, starting_stack): pass
            def act(self, state): return "CHECK" if "CHECK" in state.legal_moves else "FOLD"
            def hand_over(self, hand_number, chip_change): pass
        """,
    "b": """
        def decide(observation):
            return {"action": "check" if "check" in observation["actions"] else "fold"}
        """,
    "c": """
        import sys
        for line in sys.stdin:
            clauses = line.split()
            if not clauses or clauses[0] == "Q":
                break
            if clauses[0].startswith("T"):
                print("OK", flush=True)
            elif any(c.startswith("L") for c in clauses):
                legal = [c for c in clauses if c.startswith("L")][0][1:].split(",")
                print("K" if "K" in legal else "F", flush=True)
        """,
    "d": """
        from fakekits.kit_d.kit import Bot, CheckAction, FoldAction, parse_args, run_bot

        class Player(Bot):
            def handle_new_round(self, game_state, round_state, active): pass
            def get_action(self, game_state, round_state, active):
                return CheckAction() if CheckAction in round_state.legal_actions() else FoldAction()
            def handle_round_over(self, game_state, terminal_state, active): pass

        if __name__ == "__main__":
            run_bot(Player(), parse_args())
        """,
    "e_style": """
        class Agent:
            def on_table(self, info): pass
            def decide(self, req): return {"move": "check"} if "check" in req["moves"] else {"move": "fold"}
        """,
}

# Runs inside `python -I -S` (no site-packages, no PYTHON* env, no cwd on sys.path): hyperion must be
# unimportable, the kit must import and play five hands, and nothing named hyperion may have been loaded.
DRIVER = """
import sys
sys.path.insert(0, {copy!r})
try:
    import hyperion
except ImportError:
    pass
else:
    raise SystemExit("hyperion is importable here; the test is not isolating")
import fakekits.kit_{kit}.kit as kit
import fakekits.kit_{kit}.runner as runner
{run}
leaked = sorted(m for m in sys.modules if m == "hyperion" or m.startswith("hyperion."))
if leaked:
    raise SystemExit("hyperion modules loaded: " + ", ".join(leaked))
print("SUMMARY", report.summary())
"""

RUN = {
    "a": "report = runner.run(runner.load_agent_class({bot!r}), hands=5, seed=3)",
    "b": "report = runner.run(runner.load_module({bot!r}), hands=5, seed=3)",
    "c": "report = runner.run([sys.executable, {bot!r}], hands=5, seed=3)",
    "d": "report = runner.run([sys.executable, {bot!r}], hands=5, seed=3)",
    "e_style": ("rep = runner.run({bot!r}, tables=1, hands=5, seed=3, interrupt=False)\n"
                "class _Summary:\n"
                "    def summary(self):\n"
                "        return f\"{{rep['hands']}} hands, {{sum(rep['errors'].values())}} exceptions, "
                "{{rep['illegal']}} illegal\"\n"
                "report = _Summary()"),
}


@pytest.fixture(scope="module")
def copy(tmp_path_factory) -> Path:
    base = tmp_path_factory.mktemp("blank")
    shutil.copytree(FAKEKITS, base / "fakekits", ignore=shutil.ignore_patterns("__pycache__"))
    for kit, src in BOTS.items():
        (base / f"bot_{kit}.py").write_text(textwrap.dedent(src).lstrip())
    return base


@pytest.mark.parametrize("kit", ["a", "b", "c", "d", "e_style"])
def test_kit_imports_and_plays_without_hyperion(copy: Path, kit: str):
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env["PYTHONPATH"] = str(copy)  # ignored by the isolated runner (-I); lets the kit C/D bot subprocess find the kit
    code = DRIVER.format(copy=str(copy), kit=kit, run=RUN[kit].format(bot=str(copy / f"bot_{kit}.py")))
    r = subprocess.run([sys.executable, "-I", "-S", "-c", code], cwd=str(copy), env=env,
                       capture_output=True, text=True, timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    summary = [ln for ln in r.stdout.splitlines() if ln.startswith("SUMMARY ")]
    assert summary and "5 hands" in summary[0] and "0 exceptions, 0 illegal" in summary[0], r.stdout + r.stderr


def test_no_fakekit_source_imports_hyperion():
    for path in FAKEKITS.rglob("*.py"):
        for line in path.read_text().splitlines():
            stripped = line.strip()
            assert not (stripped.startswith(("import hyperion", "from hyperion"))), f"{path}: {line}"


def test_vendored_evaluator_orders_hands_like_the_real_one():
    rng = random.Random(7)
    deck = list(range(52))
    for n in (5, 6, 7, 8):  # 8 = three hole cards on a full board
        for _ in range(400):
            rng.shuffle(deck)
            a, b = tuple(deck[:n]), tuple(deck[n:2 * n])
            va, vb = _eval.evaluate(a), _eval.evaluate(b)
            ra, rb = real_eval.evaluate(a), real_eval.evaluate(b)
            assert (va > vb) == (ra > rb) and (va == vb) == (ra == rb), (a, b)
            assert va[0] == real_eval.category(ra)


def test_vendored_evaluator_knows_the_wheel_and_straight_flush():
    from hyperion.core.types import parse_cards

    wheel, six = _eval.evaluate(parse_cards("5c 4d 3h 2s Ac")), _eval.evaluate(parse_cards("6c 5d 4h 3s 2c"))
    assert wheel[0] == 4 and six[0] == 4 and wheel < six
    assert _eval.evaluate(parse_cards("As Ks Qs Js Ts 2c 3d"))[0] == 8
    assert _eval.card_str(51) == "As" and _eval.card_str(0) == "2c" and len(_eval.FULL_DECK) == 52
    assert len(list(combinations(range(7), 5))) == 21
