"""Tonight's twist as a hooks file: Chain Hold'em. Each dealt-in seat keeps one private card; between every two
ring neighbours one link card both hold. Hole = (private, left link, right link); best five of eight, standard
ranks (the default score). Ring order = seat order over the dealt-in seats (left = next seat that acts after).

V-h (2026-11-02): `extras` reports what each seat knows of the others, `{"known": {viewer: {seat: (cards,)}}}`: a
seat's two links are in its neighbours' hands (heads-up both are the one opponent's). Keyed by the viewer because the
engine's extras are one dict for every seat; a bot reads its own entry (Hero's Config.known_cards,
hyperion/strategy/known.py; the generic aware bots' public_cards)."""
from __future__ import annotations

from hyperion.core.types import Rules
from hyperion.drills.variants import Variant, VariantHooks


class ChainHooks(VariantHooks):
    def __init__(self) -> None:
        self.known: dict = {}

    def on_deal(self, holes, deck, rng):
        ring = [i for i, h in enumerate(holes) if h]
        n = len(ring)
        self.known = {}
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
        known: dict = {s: {} for s in ring}
        for k, s in enumerate(ring):  # link[s] sits between s and the next seat: each knows the other holds it
            nxt = ring[(k + 1) % n]
            known[s][nxt] = known[s].get(nxt, ()) + (link[s],)
            known[nxt][s] = known[nxt].get(s, ()) + (link[s],)
        self.known = known
        return out

    def extras(self, hand) -> dict:
        return {"known": self.known}


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
