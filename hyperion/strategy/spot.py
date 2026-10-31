"""Spot: the handful of numbers every strategy module wants, computed once per decision.

Only arithmetic over obs.stacks / obs.bets / obs.in_hand and one pass over the hand's history.

Variant terms (all neutral by default, set by Hero from Rules.extras / Observation.extras):
  cls           the table key for the hand: the 169 label, or a variant label such as 'AKs+l' for
                three or four hole cards, or a remapped label (lowball mirror, wild cards)
  bounty_bonus  expected extra chips added to any pot we win (bounty variants); it sits in the pot
                for pot odds and in the winning branch of every shove / call EV
  ko_points     points the house pays per knockout; cover_frac / shover_covered say how much of it a
                won all-in would earn (only opponents we cover can bust)
  dead          cards known to be out of play (exposed cards of other seats), for draw outs
  exposed       {seat: card} of the other seats' face-up cards, for range reads
"""
from __future__ import annotations

from ..core.cards import hole_class
from ..core.types import ActionKind, Observation

_RAISE = ActionKind.RAISE


class Spot:
    __slots__ = (
        "obs", "cls", "n", "me", "bb", "sb_seat", "bb_seat", "my_total", "my_bb", "cur_bet", "to_call",
        "pot_total", "opps", "n_opps", "behind", "limpers", "n_in", "n_raises", "raiser", "facing_shove",
        "shover", "max_opp_total", "eff", "eff_bb", "i_raised_last", "pot_odds",
        "bounty_bonus", "ko_points", "cover_frac", "shover_covered", "dead", "exposed", "ror",
    )

    def __init__(self, obs: Observation, hole: tuple[int, ...], cls: str | None = None, bounty_bonus: float = 0.0,
                 ko_points: float = 0.0, dead: tuple = (), exposed: dict | None = None):
        self.obs = obs
        self.cls = cls if cls is not None else (hole_class(hole) if len(hole) == 2 else None)
        self.bounty_bonus = bounty_bonus
        self.ko_points = ko_points
        self.dead = dead
        self.exposed = exposed
        self.ror = 0.0  # risk-of-ruin margin for stack-offs (Hero sets it from Config per decision)
        n = self.n = len(obs.stacks)
        me = self.me = obs.seat
        stacks, bets, in_hand, button = obs.stacks, obs.bets, obs.in_hand, obs.button
        bb = self.bb = obs.blinds[1] or 1
        my_total = self.my_total = stacks[me] + bets[me]
        self.my_bb = my_total / bb
        cur = 0
        for b in bets:
            if b > cur:
                cur = b
        self.cur_bet = cur
        self.to_call = obs.to_call
        self.pot_total = obs.pot + sum(bets)
        self.pot_odds = self.to_call / (self.pot_total + self.to_call + bounty_bonus) if self.to_call > 0 else 0.0
        # blinds: first two alive seats after the button; heads-up the button is the small blind
        sb_seat = bb_seat = -1
        alive = 0
        for k in range(1, n + 1):
            s = (button + k) % n
            if stacks[s] + bets[s] > 0 or in_hand[s]:
                alive += 1
                if sb_seat < 0:
                    sb_seat = s
                elif bb_seat < 0:
                    bb_seat = s
        if alive == 2:
            sb_seat, bb_seat = button, (sb_seat if sb_seat != button else bb_seat)
        self.sb_seat, self.bb_seat = sb_seat, bb_seat
        # opponents still in the hand, and preflop order position (0 = first to act preflop)
        opps = []
        max_opp = 0
        behind = 0
        limpers = 0
        n_in = 0
        shover = -1
        covered = 0
        my_order = self._pre_order(me, button, n, alive)
        for s in range(n):
            if s == me or not in_hand[s]:
                continue
            opps.append(s)
            tot = stacks[s] + bets[s]
            if tot > max_opp:
                max_opp = tot
            if tot <= my_total:
                covered += 1
            if obs.street == 0 and self._pre_order(s, button, n, alive) > my_order:
                behind += 1
            if bets[s] >= cur and cur > 0:
                if cur > bb or s != bb_seat:
                    n_in += 1
                if cur == bb and s != bb_seat:
                    limpers += 1
                if stacks[s] == 0 and cur > 0:
                    shover = s
        if obs.street > 0:
            # postflop: players after me in postflop order
            my_pos = (me - button - 1) % n
            for s in opps:
                if (s - button - 1) % n > my_pos:
                    behind += 1
        self.opps = opps
        self.n_opps = len(opps)
        self.cover_frac = covered / len(opps) if opps else 0.0
        self.behind = behind
        self.limpers = limpers
        self.n_in = n_in
        self.max_opp_total = max_opp
        self.eff = min(my_total, max_opp) if max_opp else my_total
        self.eff_bb = self.eff / bb
        self.shover = shover
        self.facing_shove = shover >= 0 and self.to_call > 0
        self.shover_covered = shover >= 0 and stacks[shover] + bets[shover] <= my_total
        n_raises = 0
        raiser = -1
        for seat, act in obs.history:
            if act.kind is _RAISE:
                n_raises += 1
                raiser = seat
        self.n_raises = n_raises
        self.raiser = raiser
        self.i_raised_last = raiser == me

    @staticmethod
    def _pre_order(seat: int, button: int, n: int, alive: int) -> int:
        """Preflop acting order index: UTG = 0 ... BB last. Heads-up the button acts first."""
        pos = (seat - button - 1) % n  # 0 = SB ... n-1 = button
        if alive == 2:
            return 0 if seat == button else 1
        return (pos - 2) % n
