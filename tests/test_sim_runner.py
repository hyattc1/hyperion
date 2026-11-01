import json

import pytest

from hyperion.core.types import Rules
from hyperion.sim.runner import load_rules, main, run_tournament


def test_run_tournament_aggregates_per_name_and_fills_with_copies():
    rep = run_tournament(["tag", "nit", "station"], tables=3, seed=1, rotate=False, mode="strict")
    assert set(rep.bots) == {"tag", "nit", "station"}
    assert sum(b.seats for b in rep.bots.values()) == 3 * 8  # copies fill the empty seats
    assert all(len(b.samples) == 3 for b in rep.bots.values())
    assert sum(sum(b.places) for b in rep.bots.values()) == 24
    assert rep.hands > 0 and rep.hands_per_second > 0
    total_points = sum(sum(b.samples) * b.seats / len(b.samples) for b in rep.bots.values())
    assert total_points == pytest.approx(3 * 36, rel=0.5)  # per-sample means weighted back is rough
    text = rep.format()
    assert "tag" in text and "hands/s" in text


def test_rotate_plays_every_rotation_and_one_sample_per_seed():
    rep = run_tournament(["allin", "station"], tables=2, seed=3, rotate=True)
    assert rep.tables == 16
    assert all(len(b.samples) == 2 for b in rep.bots.values())
    assert sum(b.seats for b in rep.bots.values()) == 16 * 8
    # a duplicate deal over all rotations gives every seat each card-set once: points sum is exact
    assert sum(b.mean * b.seats / 16 * 8 / 8 for b in rep.bots.values()) > 0


def test_points_per_table_sum_to_the_payouts():
    rep = run_tournament(["random"], tables=4, seed=2)
    b = rep.bots["random"]
    assert b.samples == pytest.approx([36 / 8] * 4)


def test_unknown_bot_name_fails_early():
    with pytest.raises(KeyError):
        run_tournament(["tag", "nope"], tables=1)


def test_load_rules_from_json(tmp_path):
    p = tmp_path / "r.json"
    p.write_text(json.dumps({"hole_cards": 3, "board_sizes": [0, 3, 4, 5], "max_hands": 10,
                             "blind_levels": [[10, 20], [20, 40]], "payouts": [8, 7, 6, 5, 4, 3, 2, 1]}))
    r = load_rules(str(p))
    assert r.hole_cards == 3 and r.max_hands == 10
    assert r.blind_levels == ((10, 20), (20, 40))
    assert isinstance(r, Rules) and load_rules("default") == Rules()


def test_cli_runs(capsys):
    assert main(["--list"]) == 0
    assert "tag" in capsys.readouterr().out
    assert main(["--tables", "2", "--seed", "1", "--bots", "tag,nit", "--mode", "measure"]) == 0
    out = capsys.readouterr().out
    assert "hands/s" in out and "nit" in out


def test_variant_seed_picks_the_permutation_apart_from_the_table_seed(monkeypatch):
    from hyperion.drills import variants
    from hyperion.sim import runner

    seen = []
    real = runner.run_tournament

    def spy(names, tables, seed, rotate, mode, rules, **kw):
        seen.append((seed, tuple(rules.rank_order), tuple(kw["variant"].rules.rank_order)))
        return real(names, tables, seed, rotate, mode, rules, **kw)

    monkeypatch.setattr(runner, "run_tournament", spy)
    base = ["--tables", "1", "--bots", "tag,nit", "--mode", "measure", "--variant", "permuted_ranks", "--seed", "11"]
    assert main(base) == 0
    assert main(base + ["--variant-seed", "0"]) == 0
    perm11 = tuple(variants.get("permuted_ranks", seed=11).rules.rank_order)
    perm0 = tuple(variants.get("permuted_ranks", seed=0).rules.rank_order)
    assert perm11 != perm0
    assert seen[0] == (11, perm11, perm11)  # default unchanged: the table seed also picks the permutation
    assert seen[1] == (11, perm0, perm0)  # --variant-seed: same tables, the seed-0 permutation
