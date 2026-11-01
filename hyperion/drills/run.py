"""The timed 60-minute build drill.

    python -m hyperion.drills.run --variant random --kit random --seed 7
    python -m hyperion.drills.run --variant toss_or_holdem --kit c --seed 1 --auto   # machinery smoke test

Reveals the twist and the kit only when started, starts a wall clock, makes a scratch directory with
the kit and the variant's rules JSON, then waits for you to hit four checkpoints:
  T+15  legal bot: scratch/submission.py passes the kit's runner
  T+30  tables regenerated for the variant into scratch/tables (gen_tables meta matches the rules)
  T+45  hero wired and playing in the sim (degrades to the fake table, or skips, if sim/hero are missing)
  T+60  final: longer run of the kit's runner, latency report
Each checkpoint time goes to drills/log/<timestamp>.json. --auto runs every checkpoint immediately
with the reference adapter and tiny tables, to prove the drill itself works.
"""
from __future__ import annotations

import argparse
import importlib
import json
import random
import shutil
import subprocess
import sys
import time
from pathlib import Path

from hyperion.drills import variants
from hyperion.drills.fakekits import _table

ROOT = Path(__file__).resolve().parents[2]
KITS = ("a", "b", "c", "d")
CHECKPOINTS = (("legal_bot", 15), ("tables", 30), ("hero_in_sim", 45), ("final", 60))
REFERENCE = {k: ROOT / "hyperion" / "drills" / "reference" / f"kit_{k}_submission.py" for k in KITS}


class Drill:
    def __init__(self, variant: variants.Variant, kit: str, seed: int, scratch: Path, log_dir: Path, hands: int):
        self.variant, self.kit, self.seed, self.hands = variant, kit, seed, hands
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.scratch = scratch / f"{self.stamp}-{variant.name}-kit{kit}"
        self.log_dir = log_dir
        self.t0 = time.perf_counter()
        self.results: list[dict] = []

    # -- time
    def elapsed_min(self) -> float:
        return (time.perf_counter() - self.t0) / 60.0

    def clock(self) -> str:
        s = int(time.perf_counter() - self.t0)
        return f"T+{s // 60:02d}:{s % 60:02d}"

    # -- setup
    def setup(self) -> None:
        self.scratch.mkdir(parents=True, exist_ok=True)
        kit_dir = ROOT / "hyperion" / "drills" / "fakekits" / f"kit_{self.kit}"
        shutil.copytree(kit_dir, self.scratch / "kit", ignore=shutil.ignore_patterns("__pycache__"))
        (self.scratch / "variant.json").write_text(json.dumps(self.variant.rules_json(), indent=1) + "\n")
        brief = [
            f"# Drill {self.stamp}: {self.variant.name} on kit {self.kit}", "",
            self.variant.summary, "", "## Checkpoints", "",
            f"- T+15 write `{self.scratch}/submission.py` for kit {self.kit} (read kit/RUBRIC.md) and press Enter in the drill",
            f"- T+30 `python tools/gen_tables.py --rules {self.scratch}/variant.json --out {self.scratch}/tables`",
            "- T+45 the ship bot wired: hyperion.ship.make_bot() behind the adapter, playing in the sim",
            "- T+60 final run", "", "## What breaks", "", self.variant.breaks, "", "## Checklist", "",
        ] + [f"- {c}" for c in self.variant.checklist]
        (self.scratch / "BRIEF.md").write_text("\n".join(brief) + "\n")

    def banner(self) -> None:
        v = self.variant
        print("=" * 78)
        print(f"DRILL START {time.strftime('%H:%M:%S')}   seed {self.seed}")
        print(f"  twist : {v.name} - {v.summary}")
        print(f"  kit   : {self.kit}  (read {self.scratch / 'kit' / 'RUBRIC.md'})")
        print(f"  rules : {self.scratch / 'variant.json'}")
        print(f"  brief : {self.scratch / 'BRIEF.md'}")
        print(f"  submit: {self.scratch / 'submission.py'}")
        print("  checkpoints: T+15 legal bot, T+30 tables, T+45 hero in sim, T+60 final")
        print("=" * 78)

    # -- checks
    def run_kit(self, hands: int, seed: int, budget_ms: float = 1.0) -> _table.Report:
        sub = self.scratch / "submission.py"
        if not sub.exists():
            r = _table.Report()
            r.notes.append(f"missing {sub}")
            r.exceptions = 1
            return r
        hole_cards = self.variant.rules.hole_cards
        sys.path.insert(0, str(self.scratch))
        try:
            if self.kit == "a":
                mod = importlib.import_module("hyperion.drills.fakekits.kit_a.runner")
                return mod.run(mod.load_agent_class(str(sub)), hands, seed, budget_ms, hole_cards)
            if self.kit == "b":
                mod = importlib.import_module("hyperion.drills.fakekits.kit_b.runner")
                return mod.run(mod.load_module(str(sub)), hands, seed, budget_ms, hole_cards)
            if self.kit == "d":
                mod = importlib.import_module("hyperion.drills.fakekits.kit_d.runner")
                return mod.run([sys.executable, str(sub)], hands, seed, budget_ms, hole_cards, cwd=str(self.scratch))
            mod = importlib.import_module("hyperion.drills.fakekits.kit_c.runner")
            return mod.run([sys.executable, str(sub)], hands, seed, budget_ms, hole_cards, cwd=str(self.scratch))
        finally:
            sys.path.remove(str(self.scratch))

    def check_legal_bot(self) -> tuple[str, str]:
        r = self.run_kit(self.hands, self.seed)
        return ("pass" if r.passed else "fail"), r.summary() + ("; " + "; ".join(r.notes) if r.notes else "")

    def check_tables(self) -> tuple[str, str]:
        tdir = self.scratch / "tables"
        meta_p = tdir / "meta.json"
        if not meta_p.exists():
            return "fail", f"no {meta_p}"
        meta = json.loads(meta_p.read_text())
        want = self.variant.rules_json()
        got = meta.get("rules", {})
        diffs = [k for k in ("hole_cards", "board_sizes", "rank_order", "n_suits")
                 if json.dumps(got.get(k)) != json.dumps(want.get(k))]
        if got.get("extras", {}).get("removed_ranks") != want.get("extras", {}).get("removed_ranks"):
            diffs.append("extras.removed_ranks")
        need = ["preflop_equity.json", "preflop_rank.json", "flop_strength.json"]
        if want["hole_cards"] != 2:
            need.append("hole_classes.json")
        missing = [n for n in need if not (tdir / n).exists()]
        if diffs or missing:
            return "fail", f"rules differ in {diffs}; missing {missing}"
        secs = meta.get("seconds", {}).get("total")
        return "pass", f"{', '.join(need)} match variant.json; generated in {secs}s at samples={meta.get('samples')}"

    def check_hero_in_sim(self) -> tuple[str, str]:
        hero = None
        try:
            hero_mod = importlib.import_module("hyperion.ship")  # the bot we ship (hyperion/ship.py)
            hero = hero_mod.make_bot()
        except Exception as e:  # noqa: BLE001
            hero_err = f"{type(e).__name__}: {e}"
        play_table = None
        try:
            sim = importlib.import_module("hyperion.sim")
            play_table = getattr(sim, "play_table", None)
            if play_table is None:
                play_table = importlib.import_module("hyperion.sim.engine").play_table
        except Exception as e:  # noqa: BLE001
            sim_err = f"{type(e).__name__}: {e}"
        if hero is None:
            return "skipped", f"hero missing ({hero_err}); the cheap bot stands in for the kit checks"
        if play_table is None:
            # degrade: hero plays the fake table through the kit A adapter
            from hyperion.drills.adapter import KitAAdapter
            from hyperion.drills.fakekits.kit_a.kit import parse_action, to_state

            report = _table.Report()
            ad = KitAAdapter(hero)
            ad.start(0, 4)
            seat = _table.TimedSeat(lambda st: parse_action(ad.decide(to_state(st))), 1.0, report)
            report.delta = _table.play(seat, self.hands, self.seed, hole_cards=self.variant.rules.hole_cards)
            return ("degraded" if report.passed else "fail"), f"sim missing ({sim_err}); fake table: {report.summary()}"
        from hyperion.drills.cheapbot import CheapBot

        bots = [hero] + [CheapBot() for _ in range(self.variant.rules.n_players - 1)]
        try:
            t = time.perf_counter()
            out = play_table(bots, self.variant.rules, self.seed, 0)
            return "pass", f"play_table ran in {time.perf_counter() - t:.1f}s -> {str(out)[:120]}"
        except Exception as e:  # noqa: BLE001
            return "fail", f"play_table raised {type(e).__name__}: {e}"

    def check_final(self) -> tuple[str, str]:
        r = self.run_kit(max(self.hands, 3 * self.hands), self.seed + 1)
        status = "pass" if r.passed else "fail"
        return status, r.summary() + (f"; p-max latency {r.max_ms:.3f} ms" if r.times_ms else "")

    def checkpoint(self, name: str, target: int) -> dict:
        fn = {"legal_bot": self.check_legal_bot, "tables": self.check_tables,
              "hero_in_sim": self.check_hero_in_sim, "final": self.check_final}[name]
        try:
            status, detail = fn()
        except Exception as e:  # noqa: BLE001
            status, detail = "fail", f"check raised {type(e).__name__}: {e}"
        at = self.elapsed_min()
        rec = {"name": name, "target_min": target, "at_min": round(at, 2), "on_time": at <= target,
               "status": status, "detail": detail}
        self.results.append(rec)
        flag = "on time" if rec["on_time"] else "LATE"
        print(f"[{self.clock()}] {name:12s} {status.upper():8s} ({flag}, target T+{target})  {detail}")
        return rec

    def skip(self, name: str, target: int) -> None:
        self.results.append({"name": name, "target_min": target, "at_min": round(self.elapsed_min(), 2),
                             "on_time": False, "status": "skipped", "detail": "skipped by user"})

    # -- log
    def write_log(self) -> Path:
        self.log_dir.mkdir(parents=True, exist_ok=True)
        path = self.log_dir / f"{self.stamp}.json"
        doc = {
            "stamp": self.stamp, "variant": self.variant.name, "kit": self.kit, "seed": self.seed,
            "scratch": str(self.scratch), "total_min": round(self.elapsed_min(), 2),
            "checkpoints": self.results,
            "passed": all(r["status"] in ("pass", "degraded", "skipped") for r in self.results),
        }
        path.write_text(json.dumps(doc, indent=1) + "\n")
        return path

    def summary(self) -> None:
        print("-" * 78)
        for r in self.results:
            print(f"  {r['name']:12s} target T+{r['target_min']:2d}  hit T+{r['at_min']:5.1f}  {r['status']}")
        print(f"  total {self.elapsed_min():.1f} min; log {self.write_log()}")


def auto_prepare(d: Drill, samples: int) -> None:
    """--auto: reference submission + tiny tables, so every checkpoint has something to check."""
    shutil.copy(REFERENCE[d.kit], d.scratch / "submission.py")
    cmd = [sys.executable, str(ROOT / "tools" / "gen_tables.py"), "--rules", str(d.scratch / "variant.json"),
           "--out", str(d.scratch / "tables"), "--samples", str(samples), "--skip-matrix",
           "--flops-per-bucket", "1", "--workers", "2"]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--variant", default="random", help="random or one of: " + ", ".join(variants.names()))
    p.add_argument("--kit", default="random", choices=("random",) + KITS)
    p.add_argument("--seed", type=int, default=int(time.time()) % 100000)
    p.add_argument("--scratch", default=str(ROOT / "drills" / "scratch"))
    p.add_argument("--log-dir", default=str(ROOT / "drills" / "log"))
    p.add_argument("--hands", type=int, default=30, help="hands per kit-runner check")
    p.add_argument("--auto", action="store_true", help="no prompts: reference adapter, tiny tables, all checks now")
    p.add_argument("--auto-samples", type=int, default=100)
    a = p.parse_args(argv)

    rng = random.Random(a.seed)
    vname = rng.choice(variants.names()) if a.variant == "random" else a.variant
    kit = rng.choice(KITS) if a.kit == "random" else a.kit
    variant = variants.get(vname, seed=a.seed)
    d = Drill(variant, kit, a.seed, Path(a.scratch), Path(a.log_dir), a.hands)
    d.setup()
    d.banner()

    if a.auto:
        auto_prepare(d, a.auto_samples)
        for name, target in CHECKPOINTS:
            d.checkpoint(name, target)
    else:
        if not sys.stdin.isatty():
            print("stdin is not a terminal; use --auto for a non-interactive run")
            return 2
        for name, target in CHECKPOINTS:
            ans = input(f"[{d.clock()}] Enter when '{name}' is ready (target T+{target}), s to skip, q to quit: ")
            if ans.strip().lower() == "q":
                break
            if ans.strip().lower() == "s":
                d.skip(name, target)
                continue
            d.checkpoint(name, target)
    d.summary()
    return 0 if all(r["status"] in ("pass", "degraded", "skipped") for r in d.results) else 1


if __name__ == "__main__":
    sys.exit(main())
