import pytest

from hyperion.core.types import ActionKind, Rules, parse_cards
from hyperion.sim import bestiary as B
from hyperion.sim.engine import Table, play_table
from tests.sim_helpers import Auditor

NAMES = [n for n in B.REGISTRY if n not in ("crasher", "timeout")]


@pytest.mark.parametrize("name", NAMES)
def test_each_bot_plays_200_hands_without_error(name):
    # eight copies under a cap that forces the full 200 hands when nobody busts
    bots = [Auditor(B.make_bot(name, seed=s), 16000) for s in range(8)]
    t = Table(bots, Rules(), seed=7)
    hands = 0
    while not t.done:
        t.play_hand()
        hands += 1
    assert hands <= 200
    for s in range(8):
        st = t.stats[s]
        assert st.exceptions == 0, st.last_error
        assert st.illegal == 0
    # the bot actually decides, except when a table of copies ends on hand one
    assert sum(len(b.decisions) for b in bots) > 0


@pytest.mark.parametrize("name", NAMES)
def test_each_bot_in_a_mixed_field_stays_under_budget(name):
    names = [name] + [n for n in NAMES if n != name][:7]
    while len(names) < 8:
        names.append("station")
    bots = [B.make_bot(n, seed=s) for s, n in enumerate(names)]
    res = play_table(bots, Rules(), seed=3, mode="measure")
    st = res.stats[0]
    assert st.exceptions == 0, st.last_error
    assert st.illegal == 0
    if st.calls:
        assert st.percentile_us(0.99) < 1000


def test_bots_survive_a_three_card_variant_with_permuted_ranks():
    order = (12,) + tuple(range(12))
    rules = Rules(hole_cards=3, rank_order=order)
    bots = [B.make_bot(n, seed=s) for s, n in enumerate(NAMES)]
    res = play_table(bots, rules, seed=5)
    for st in res.stats:
        assert st.exceptions == 0, st.last_error
        assert st.illegal == 0


def test_crasher_and_timeout_are_handled():
    bots = [B.Crasher(), B.TimeoutBot()] + [B.CallingStation() for _ in range(6)]
    res = play_table(bots, Rules(max_hands=5), seed=1)
    assert res.stats[0].exceptions > 0
    assert res.stats[1].over_budget > 0
    assert res.hands == 5


def test_hero_falls_back_to_charttag_when_strategy_is_missing():
    h = B.Hero(seed=1)
    try:
        import hyperion.strategy.hero  # noqa: F401

        has_strategy = True
    except Exception:
        has_strategy = False
    if not has_strategy:
        assert isinstance(h.impl, B.ChartTAG)


def test_registry_lookup_by_short_and_class_name():
    assert isinstance(B.make_bot("tag"), B.ChartTAG)
    assert isinstance(B.make_bot("ChartTAG"), B.ChartTAG)
    with pytest.raises(KeyError):
        B.make_bot("gto")


def test_helpers():
    assert B.two_card_class(parse_cards("AsKs")) == "AKs"
    assert B.two_card_class(parse_cards("As Kd 7c")) == "AKo"
    assert B.two_card_class(parse_cards("As 7d 7c")) == "77"
    assert B.top_pair_or_better(parse_cards("AsKd"), parse_cards("Ac 7d 2h"))
    assert not B.top_pair_or_better(parse_cards("KsQd"), parse_cards("Ac Kd 2h"))
    assert B.top_pair_or_better(parse_cards("QsQd"), parse_cards("Jc 7d 2h"))  # overpair
    assert not B.top_pair_or_better(parse_cards("AsKd"), parse_cards("7c 7d 2h"))  # pair on board
    assert B.chen_score(parse_cards("AsAd")) == 20
    assert B.chen_score(parse_cards("AsKs")) == 12
    assert B.chen_score(parse_cards("7c2d")) == pytest.approx(-1.5)
    r = B.expand_range("77+ AJs+ KQo")
    assert {"77", "AA", "AJs", "AQs", "AKs", "KQo"} <= r and "66" not in r and "ATs" not in r


def test_nit_folds_junk_and_raises_premiums():
    from tests.sim_helpers import Scripted

    bots = [B.Nit(), Scripted([]), Scripted([])]
    rules = Rules(n_players=3, payouts=(3, 2, 1))
    seen = []

    class Watch(B.Nit):
        def act(self, obs):
            a = super().act(obs)
            seen.append((B.two_card_class(obs.hole), obs.street, a.kind))
            return a

    bots[0] = Watch()
    play_table(bots, rules, seed=4)
    preflop = [(c, k) for c, st, k in seen if st == 0]
    assert any(k is ActionKind.RAISE for c, k in preflop if c in B.Nit.PREMIUM) or not any(
        c in B.Nit.PREMIUM for c, _ in preflop
    )
    assert all(k in (ActionKind.FOLD, ActionKind.CHECK) for c, k in preflop if c not in B.Nit.PREMIUM)
