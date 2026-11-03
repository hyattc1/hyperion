"""Tonight's twist as a hooks file: Chain Hold'em. Each dealt-in seat keeps one private card; between every two
ring neighbours one link card both hold. Hole = (private, left link, right link); best five of eight, standard
ranks (the default score). Ring order = seat order over the dealt-in seats (left = next seat that acts after)."""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks


class ChainHooks(VariantHooks):
    def on_deal(self, holes, deck, rng):
        ring = [i for i, h in enumerate(holes) if h]
        n = len(ring)
        if n < 2:
            return holes
        priv = {s: holes[s][0] for s in ring}
        link = {s: holes[s][1] for s in ring}  # link(s, next(s))
        spare = [holes[s][2] for s in ring]
        for c in spare:  # unused third cards go back to the undealt deck at random places
            deck.insert(rng.randrange(len(deck) + 1), c)
        out = list(holes)
        for k, s in enumerate(ring):
            prev = ring[k - 1]
            out[s] = (priv[s], link[s], link[prev])
        return out


def variant() -> Variant:
    rules = Rules(hole_cards=3,
                  blind_levels=((10, 20), (15, 30), (25, 50), (40, 80), (60, 120), (100, 200), (150, 300), (250, 500)),
                  payouts=(50, 32, 21, 14, 9, 5, 2, 0),
                  extras={"variant": "chain_holdem"})
    return Variant(
        name="chain_holdem",
        summary="Chain Hold'em: one private card plus two link cards shared with the ring neighbours; best five of eight.",
        rules=rules,
        breaks="Three-card tables (three_card_keep) price independent third cards; links are shared with neighbours.",
        checklist=("No regeneration: three_card_keep tables by card rules.",),
        hooks_factory=ChainHooks,
        needs_engine=True,
        axis="information",
    )
