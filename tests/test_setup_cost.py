"""Setup and a table's first decision, cold, in a fresh process (R6; drill 7, kit E).

Kit E gave import + Player() + take_seat 1 s per table with a fresh module per table, and Hero's table start built
the 8-card evaluator table (0.62 s of it). And a decision that builds something lazily the first time it meets a
spot (a table, a curve, a profiler array) is a fold under a strict 1 ms clock, every table. Method: record one
table of the bot in the simulator, then replay its calls on a fresh bot in a fresh `python -I` process, where
nothing has been built yet: setup in CPU seconds, each decision's CPU time (a preempted call reports the scheduler,
not the bot), and which evaluator tables exist before and after the decisions."""
import copy
import json
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

from hyperion import ship
from hyperion.core.types import Rules
from hyperion.drills import variants as V
from hyperion.sim import bestiary as B
from hyperion.sim.engine import play_table

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.timing  # CPU-time budgets for setup and first decisions (drill 8: failed at load 11)

CHILD = r'''
import json, pickle, sys, time
root, path, bot_name = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, root)
cpu, thr = time.process_time, time.thread_time
c0 = cpu()
import hyperion.ship as ship
bot = ship.make_bot(bot_name)
with open(path, "rb") as f:
    log = pickle.load(f)
from hyperion.core import eval as E
c1 = cpu()
for ev in log:
    if ev[0] == "nt":
        bot.new_table(ev[1], ev[2], ev[3])
        break
c2 = cpu()
before = sorted(E._UNSUITED_N)
acts, first = [], None
for ev in log:
    if ev[0] == "act":
        t = thr()
        bot.act(ev[1])
        acts.append(thr() - t)
    elif ev[0] == "he":
        bot.hand_end(ev[1])
    elif ev[0] == "vd":
        bot.variant_decide(ev[1])
print(json.dumps({"setup_cpu": c2 - c0, "new_table_cpu": c2 - c1, "acts": acts, "tables_before": before,
                  "tables_after": sorted(E._UNSUITED_N), "wanted": sorted(E.WANTED)}))
'''


class _Rec:
    def __init__(self, impl):
        self.impl, self.log = impl, []

    def new_table(self, rules, seat, n):
        self.log.append(("nt", rules, seat, n))
        self.impl.new_table(rules, seat, n)

    def act(self, obs):
        self.log.append(("act", copy.deepcopy(obs)))
        return self.impl.act(obs)

    def hand_end(self, result):
        self.log.append(("he", copy.deepcopy(result)))
        self.impl.hand_end(result)

    def variant_decide(self, prompt):
        self.log.append(("vd", copy.deepcopy(prompt)))
        return self.impl.variant_decide(prompt)


def _record(bot_name: str, rules: Rules, variant, seed: int, hands: int) -> list:
    names = B.field_names("realistic")
    bots = [B.make_bot(nm, seed=seed * 64 + s) for s, nm in enumerate(names)]
    rec = _Rec(ship.make_bot(bot_name, seed=seed))
    bots[0] = rec
    play_table(bots, rules.__class__(**{**rules.__dict__, "max_hands": hands}), seed=seed, mode="model",
               variant=variant.new_hooks() if variant is not None else None)
    return rec.log


def _child(tmp_path, bot_name: str, log: list) -> dict:
    p = tmp_path / "log.pkl"
    p.write_bytes(pickle.dumps(log))
    script = tmp_path / "child.py"
    script.write_text(CHILD)
    out = subprocess.run([sys.executable, "-I", str(script), str(ROOT), str(p), bot_name], capture_output=True,
                         text=True, timeout=120, cwd=tmp_path)
    assert out.returncode == 0, out.stderr[-2000:]
    return json.loads(out.stdout.strip().splitlines()[-1])


CASES = [("default", Rules(), None, 7), ("toss_or_holdem", V.get("toss_or_holdem").rules, "toss_or_holdem", 7),
         ("three_card_keep", V.get("three_card_keep").rules, "three_card_keep", 8)]


@pytest.mark.parametrize("bot_name", ["composite", "hybrid3_x", "hero"])
@pytest.mark.parametrize("label,rules,vname,cards", CASES, ids=[c[0] for c in CASES])
def test_cold_setup_and_first_decisions(tmp_path, bot_name, label, rules, vname, cards):
    variant = V.get(vname) if vname else None
    log = _record(bot_name, rules, variant, seed=4242, hands=40)
    r = _child(tmp_path, bot_name, log)
    acts = r["acts"]
    assert len(acts) >= 10
    # import + make_bot + new_table: 0.9 s before R6 (warm(8) was 0.62 s of it); now about 0.14 s, 0.19 s with 8 cards
    assert r["setup_cpu"] < 0.45, r["setup_cpu"]
    # the table start built exactly the tables the rules need, and no decision built another
    assert r["tables_before"] == list(range(5, cards + 1)), r["tables_before"]
    assert r["tables_after"] == r["tables_before"] and r["wanted"] == [], (r["tables_after"], r["wanted"])
    # the first decision costs what any other does (48 ms first calls were reported under load; CPU time here)
    later = sorted(acts[1:])
    med = later[len(later) // 2]
    assert acts[0] < max(2e-3, 10 * med), (acts[0], med)
    assert max(acts) < 3e-3, max(acts)
