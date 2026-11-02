"""Per-seat opponent model. Resets in new_table (state is wiped per table in the real event anyway).

Counters are plain int lists indexed by seat. Rates are Beta-smoothed with a weak prior worth
`prior_n` observations (default 2, per Hoehn et al. 2005: weak priors beat strong ones in short
matches). Flags fire after small fixed sample sizes because the field is deterministic bots.

Street attribution: Observation.history is a flat (seat, Action) list for the hand with no street
markers, so a small betting-round tracker replays it: a round closes when every seat that still
owes an action has acted, and a seat acting again while it owes nothing means a new street began
(covers all-in seats that never act again). Mis-tagging under odd kit behaviour costs one hand of
stats, never an exception: everything here is best effort and bounded by the length of history.
"""
from __future__ import annotations

from ..core.types import ActionKind, HandResult, Observation

_FOLD = ActionKind.FOLD
_CHECK = ActionKind.CHECK
_CALL = ActionKind.CALL
_RAISE = ActionKind.RAISE

NEUTRAL_DIALS = {"bluff_mult": 1.0, "value_threshold_shift": 0.0, "steal_mult": 1.0, "call_down_mult": 1.0}


def _rate(k: int, n: int, prior_mean: float, prior_n: float) -> float:
    return (k + prior_mean * prior_n) / (n + prior_n)


class Profiler:
    # prior means for the Beta-smoothed rates
    P_VPIP, P_PFR, P_FTB, P_SHOVE, P_CALL_SHOVE, P_WTSD, P_AGG = 0.25, 0.15, 0.5, 0.05, 0.25, 0.3, 0.4
    SHOVE_BUCKETS_BB = (12.0, 25.0, 50.0)  # depth buckets (bb at its first preflop action) for shove_counts
    LATE_BEHIND = 3  # an open with at most this many players behind (cutoff, button, small blind) is a late open

    def __init__(
        self,
        n_players: int = 8,
        prior_n: float = 2.0,
        dead_after: int = 5,
        station_after: int = 10,
        nit_after: int = 20,
        maniac_after: int = 10,
        random_after: int = 15,
        blend_n: float = 8.0,
        dial_strength: float = 1.0,
        calldown_slope: float = -0.8,
    ):
        self.prior_n = prior_n
        self.dial_strength = dial_strength  # scales every dial's distance from neutral (0 = no exploits)
        self.calldown_slope = calldown_slope  # unknown archetype: call_down_mult = 1.4 + slope * aggression
        self.dead_after = dead_after
        self.station_after = station_after
        self.nit_after = nit_after
        self.maniac_after = maniac_after
        self.random_after = random_after
        self.blend_n = blend_n
        # optional f(depth in bb) -> a solved caller's probability of calling a shove that deep (Hero installs it
        # from the multiway table); with it, call_looseness compares a seat's calls with what Nash would have called
        self.call_prior = None
        self.reset(n_players)

    # ------------------------------------------------------------------ lifecycle
    def reset(self, n_players: int, my_seat: int = -1) -> None:
        n = self.n = n_players
        self.me = my_seat
        z = lambda: [0] * n  # noqa: E731
        self.hands = z()  # hands dealt
        self.vpip = z()
        self.pfr = z()
        self.pre_faced = z()  # faced a raise preflop (opportunities to fold to a raise)
        self.pre_folded = z()
        self.post_faced = z()  # faced a bet postflop
        self.post_folded = z()
        self.post_actions = z()  # postflop actions taken
        self.post_aggr = z()  # postflop bets/raises
        self.actions = z()  # all actions
        self.raises = z()
        self.calls = z()
        self.folds = z()
        self.checks_free = z()  # checked when nothing to call
        self.shoves = z()
        self.shove_opps = z()  # actions where a shove was possible (any action counts)
        self.faced_shove = z()
        self.called_shove = z()
        self.faced_shove_exp = [0.0] * n  # sum over the shoves faced of a solved caller's call probability (call_prior)
        self.showdowns = z()
        # preflop shove frequency by the seat's own depth when it first acted: hands it acted in / hands it shoved,
        # per bucket of SHOVE_BUCKETS_BB (a short stack's shove range is wide, a deep one's is not)
        nb = len(self.SHOVE_BUCKETS_BB) + 1
        self.pre_hands_b = [[0] * nb for _ in range(n)]
        self.pre_shoves_b = [[0] * nb for _ in range(n)]
        # ... and per opportunity: first in (nobody has raised) and facing exactly one open (a raise, not all-in),
        # counted at the seat's first preflop action; a re-shove range is read from the second, not per hand
        self.fi_opp_b = [[0] * nb for _ in range(n)]
        self.fi_shove_b = [[0] * nb for _ in range(n)]
        self.vo_opp_b = [[0] * nb for _ in range(n)]
        self.vo_shove_b = [[0] * nb for _ in range(n)]
        # first-in opens per opportunity (nobody raised or limped before the seat's first preflop action, the seat
        # deeper than 12 bb), split by its position then: late (at most LATE_BEHIND players to act after it), early.
        # A seat's open rate is its range width when it opens (the solved re-shove table's w).
        self.open_opp = [[0, 0] for _ in range(n)]  # [late, early]
        self.opens = [[0, 0] for _ in range(n)]
        # heads-up flops after a preflop raise: the raiser's first flop action with no bet in front (a c-bet chance)
        # and the other player's answer to that c-bet
        # the preflop opener facing a re-raise (3-bet or re-shove), its first answer: how often it folds its open
        self.oft_opp = z()
        self.oft_fold = z()
        self.cb_opp = z()
        self.cbets = z()
        self.fcb_opp = z()
        self.fcb_fold = z()
        self._dials = [dict(NEUTRAL_DIALS) for _ in range(n)]
        self._stale = False
        self._fresh = 0
        self.last_bb = 20
        self.hand_no = -1
        self._finished = True
        self._start_blank()

    def _start_blank(self) -> None:
        n = self.n
        self.consumed = 0
        self.tstreet = 0
        self.cur_bet = 0
        self.committed = [0] * n
        self.chips = [0] * n
        self.need = 0
        self.inhand = 0
        self.dealt = 0
        self.vpip_mask = 0
        self.pfr_mask = 0
        self.shove_pending = False
        self.pre_raiser = -1
        self.pre_raises = 0
        self.seen_obs = False
        self.pre_acted_mask = 0
        self.pre_shoved_mask = 0
        self.pre_bucket = [0] * n
        self.pre_limped = False
        self.pre_behind = [0] * n  # players dealt in who act after each seat preflop
        self.pre_order_known = False  # False in the degraded hand_end pass (no observation, no button)
        self.pre_opener = -1
        self.oft_done = False
        self.counted = 0
        self.cb_state = 0  # this hand's flop: 0 nothing yet, 1 the raiser c-bet, 2 answered or not a c-bet spot

    def _start_hand(self, obs: Observation) -> None:
        self._start_blank()
        self.hand_no = obs.hand_no
        self._finished = False
        self.seen_obs = True
        n = self.n
        stacks, bets, in_hand = obs.stacks, obs.bets, obs.in_hand
        dealt = 0
        for s in range(n):
            if in_hand[s] or stacks[s] + bets[s] > 0:
                dealt |= 1 << s
                self.hands[s] += 1
        self.dealt = dealt
        self.counted = dealt  # hands[] already counts these seats; undone at hand_end if no action was ever seen
        self.inhand = dealt
        self.need = dealt
        bb = obs.blinds[1] or self.last_bb
        self.last_bb = bb
        self.cur_bet = bb
        # blinds: first two dealt seats after the button (button itself posts SB heads-up)
        alive = [s for s in range(n) if dealt >> s & 1]
        if len(alive) >= 2:
            order = sorted(alive, key=lambda s: (s - obs.button - 1) % n)
            if len(alive) == 2:
                sb, bb_seat = obs.button, order[0] if order[0] != obs.button else order[1]
            else:
                sb, bb_seat = order[0], order[1]
            self.committed[sb] = obs.blinds[0]
            self.committed[bb_seat] = bb
            if len(alive) == 2:
                pre = [obs.button, bb_seat]
            else:
                pre = order[2:] + order[:2]  # UTG ... button, then the blinds
            k = len(pre)
            for i, s in enumerate(pre):
                self.pre_behind[s] = k - 1 - i
            self.pre_order_known = True

    # ------------------------------------------------------------------ updates
    def observe(self, obs: Observation) -> None:
        """Consume the new tail of obs.history. Call once per act(); cost is O(new actions)."""
        if self._stale:
            self._settle()
        hist = obs.history
        if self._finished or obs.hand_no != self.hand_no or len(hist) < self.consumed:
            self._start_hand(obs)
        stacks, bets, chips = obs.stacks, obs.bets, self.chips
        for s in range(self.n):
            chips[s] = stacks[s] + bets[s]
        if len(hist) > self.consumed:
            self._consume(hist, obs.street)
        # resync money and membership with what the kit says; rebuild `need` only if the street slipped
        lost = self.tstreet != obs.street
        self.cur_bet = cur = max(bets) if bets else 0
        committed = self.committed
        inhand = 0
        need = self.need
        me = obs.seat
        n = self.n
        if lost:
            self.tstreet = obs.street
            self.shove_pending = False
            need = 0
            my_pos = (me - obs.button - 1) % n
        for s in range(n):
            committed[s] = bets[s]
            if obs.in_hand[s]:
                inhand |= 1 << s
                if lost and (bets[s] < cur or (s - obs.button - 1) % n > my_pos):
                    need |= 1 << s
        self.inhand = inhand
        self.need = (need & inhand) | (1 << me)

    # `lazy`: hand_end leaves the dials stale instead of computing every seat's; exploit_dials computes a seat's on
    # first read and the next observe() settles the rest before it changes a counter, so every read sees the dials of
    # the counters at the hand end, as computed eagerly. The next hand_end recomputes them all, so stale dials nobody
    # read are skipped. Same reads, less work for a profiler read rarely (the hybrids' fallback Hero).
    lazy = False

    def _settle(self) -> None:
        fresh = self._fresh
        for s in range(self.n):
            if not fresh >> s & 1:
                self._dials[s] = self._compute_dials(s)
        self._stale = False

    def hand_end(self, result: HandResult) -> None:
        self._stale = False  # recomputed below from this hand's counters; nothing reads them in between
        hist = result.history
        if self._finished or result.hand_no != self.hand_no:
            # never observed this hand (we were out or all-in): degraded pass without blind info
            self._start_blank()
            self.hand_no = result.hand_no
            self._finished = False
            dealt = 0
            for s, _ in hist:
                dealt |= 1 << s
            for s in result.showdown:
                dealt |= 1 << s
            self.dealt = self.inhand = self.need = dealt
            self.cur_bet = self.last_bb
            for s in range(self.n):
                if dealt >> s & 1:
                    self.hands[s] += 1
        if len(hist) > self.consumed:
            self._consume(hist, 99)
        if self.consumed == 0 and self.counted:
            # no action history reached us this hand (an adapter that passes none): do not count the hand as dealt,
            # or every seat's VPIP drifts to 0 and the nit flag fires on the whole table
            for s in range(self.n):
                if self.counted >> s & 1:
                    self.hands[s] -= 1
        self.counted = 0
        for s in result.showdown:
            if 0 <= s < self.n:
                self.showdowns[s] += 1
        self._finished = True
        if self.lazy:
            self._fresh = 0
            self._stale = True
        else:
            for s in range(self.n):
                self._dials[s] = self._compute_dials(s)

    def _advance(self) -> None:
        if self.tstreet < 3:
            self.tstreet += 1
        self.cur_bet = 0
        c = self.committed
        for s in range(self.n):
            c[s] = 0
        self.need = self.inhand
        self.shove_pending = False

    def _consume(self, hist, street_hint: int) -> None:
        n = self.n
        for i in range(self.consumed, len(hist)):
            seat, act = hist[i]
            if not 0 <= seat < n:
                continue
            bit = 1 << seat
            if self.tstreet < street_hint and not (self.need & bit) and (self.inhand & bit):
                self._advance()
            kind = act.kind
            pre = self.tstreet == 0
            facing = self.cur_bet > self.committed[seat]
            facing_raise = facing and (not pre or self.cur_bet > self.last_bb)
            self.actions[seat] += 1
            self.shove_opps[seat] += 1
            if facing_raise:
                if pre:
                    self.pre_faced[seat] += 1
                else:
                    self.post_faced[seat] += 1
                if self.shove_pending:
                    self.faced_shove[seat] += 1
                    cp = self.call_prior
                    if cp is not None:
                        ch = self.chips[seat]
                        depth = (self.cur_bet if self.cur_bet < ch else ch) / (self.last_bb or 1)
                        self.faced_shove_exp[seat] += cp(depth)
            first_ctx = 0
            if pre and seat == self.pre_opener and self.pre_raises >= 2 and facing_raise and not self.oft_done:
                self.oft_done = True
                self.oft_opp[seat] += 1
                if kind is _FOLD:
                    self.oft_fold[seat] += 1
            if self.tstreet == 1 and self.cb_state < 2:
                self._cbet_obs(seat, kind)
            if not pre:
                self.post_actions[seat] += 1
            elif not (self.pre_acted_mask & bit):
                self.pre_acted_mask |= bit
                b = self._bucket(self.chips[seat])
                self.pre_bucket[seat] = b
                self.pre_hands_b[seat][b] += 1
                ctx = 1 if self.pre_raises == 0 else 2 if (self.pre_raises == 1 and not self.shove_pending) else 0
                first_ctx = ctx
                if ctx == 1 and b >= 1 and not self.pre_limped and self.pre_order_known:
                    late = 0 if self.pre_behind[seat] <= self.LATE_BEHIND else 1
                    self.open_opp[seat][late] += 1
                    if kind is _RAISE:
                        self.opens[seat][late] += 1
                if ctx == 1:
                    self.fi_opp_b[seat][b] += 1
                elif ctx == 2:
                    self.vo_opp_b[seat][b] += 1
            if kind is _FOLD:
                self.folds[seat] += 1
                if facing_raise:
                    if pre:
                        self.pre_folded[seat] += 1
                    else:
                        self.post_folded[seat] += 1
                self.inhand &= ~bit
                self.need &= ~bit
            elif kind is _CHECK:
                if not facing:
                    self.checks_free[seat] += 1
                self.need &= ~bit
            elif kind is _CALL:
                self.calls[seat] += 1
                if pre and self.pre_raises == 0:
                    self.pre_limped = True
                if pre and not (self.vpip_mask & bit):
                    self.vpip_mask |= bit
                    self.vpip[seat] += 1
                if facing_raise and self.shove_pending:
                    self.called_shove[seat] += 1
                self.committed[seat] = self.cur_bet
                self.need &= ~bit
            elif kind is _RAISE:
                amt = act.amount
                self.raises[seat] += 1
                if pre:
                    if not (self.vpip_mask & bit):
                        self.vpip_mask |= bit
                        self.vpip[seat] += 1
                    if not (self.pfr_mask & bit):
                        self.pfr_mask |= bit
                        self.pfr[seat] += 1
                    self.pre_raiser = seat
                    if self.pre_raises == 0:
                        self.pre_opener = seat
                    self.pre_raises += 1
                else:
                    self.post_aggr[seat] += 1
                ch = self.chips[seat]
                if ch > 0 and amt >= ch * 0.95:
                    self.shoves[seat] += 1
                    self.shove_pending = True
                    if pre and not (self.pre_shoved_mask & bit):
                        self.pre_shoved_mask |= bit
                        b = self.pre_bucket[seat]
                        self.pre_shoves_b[seat][b] += 1
                        if first_ctx == 1:  # the shove was the seat's first preflop action: first in
                            self.fi_shove_b[seat][b] += 1
                        elif first_ctx == 2:  # ... facing exactly one open
                            self.vo_shove_b[seat][b] += 1
                elif amt > self.cur_bet:
                    self.shove_pending = False
                if amt > self.cur_bet:
                    self.cur_bet = amt
                self.committed[seat] = amt
                self.need = self.inhand & ~bit
            else:
                self.need &= ~bit
            if self.need == 0 and self.inhand:
                self._advance()
        self.consumed = len(hist)

    def _cbet_obs(self, seat: int, kind) -> None:
        """Count c-bet chances and answers on a heads-up flop after a single preflop raiser (before the action
        is applied: cur_bet is what the seat faces)."""
        r = self.pre_raiser
        if r < 0 or bin(self.inhand).count("1") != 2 or not (self.inhand >> r & 1):
            self.cb_state = 2
            return
        if self.cb_state == 0:
            if self.cur_bet > 0:  # someone bet into the raiser first: no c-bet chance this hand
                self.cb_state = 2
            elif seat == r:
                self.cb_opp[r] += 1
                if kind is _RAISE:
                    self.cbets[r] += 1
                    self.cb_state = 1
                else:
                    self.cb_state = 2
        elif seat != r:  # answering the c-bet
            self.fcb_opp[seat] += 1
            if kind is _FOLD:
                self.fcb_fold[seat] += 1
            self.cb_state = 2

    # ------------------------------------------------------------------ rates
    def cbet_rate(self, s: int, prior: float = 0.65, n0: float = 4.0) -> float:
        return (self.cbets[s] + prior * n0) / (self.cb_opp[s] + n0)

    def open_fold_to_reraise(self, s: int, prior: float = 0.75, n0: float = 5.0) -> float:
        """How often seat s folds its open to a re-raise, smoothed toward `prior` with n0 answers."""
        return (self.oft_fold[s] + prior * n0) / (self.oft_opp[s] + n0)

    def fold_to_cbet(self, s: int, prior: float = 0.5, n0: float = 4.0) -> float:
        return (self.fcb_fold[s] + prior * n0) / (self.fcb_opp[s] + n0)

    def vpip_rate(self, s: int) -> float:
        return _rate(self.vpip[s], self.hands[s], self.P_VPIP, self.prior_n)

    def pfr_rate(self, s: int) -> float:
        return _rate(self.pfr[s], self.hands[s], self.P_PFR, self.prior_n)

    def fold_to_bet_pre(self, s: int) -> float:
        return _rate(self.pre_folded[s], self.pre_faced[s], self.P_FTB, self.prior_n)

    def fold_to_bet_post(self, s: int) -> float:
        return _rate(self.post_folded[s], self.post_faced[s], self.P_FTB, self.prior_n)

    def fold_to_bet(self, s: int) -> float:
        return _rate(self.pre_folded[s] + self.post_folded[s], self.pre_faced[s] + self.post_faced[s], self.P_FTB, self.prior_n)

    def shove_rate(self, s: int) -> float:
        return _rate(self.shoves[s], self.shove_opps[s], self.P_SHOVE, self.prior_n)

    def _bucket(self, chips: int) -> int:
        bb = self.last_bb or 1
        d = chips / bb
        for i, top in enumerate(self.SHOVE_BUCKETS_BB):
            if d <= top:
                return i
        return len(self.SHOVE_BUCKETS_BB)

    def shove_counts(self, s: int, chips: int) -> tuple[int, int]:
        """(preflop shoves, hands acted preflop) for seat s in the depth bucket of `chips` (its stack at the shove)."""
        b = self._bucket(chips)
        return self.pre_shoves_b[s][b], self.pre_hands_b[s][b]

    def shove_counts_ctx(self, s: int, chips: int, ctx: int) -> tuple[int, int]:
        """(shoves, opportunities) for seat s in the depth bucket of `chips`: ctx 1 = first in, 2 = facing one open."""
        b = self._bucket(chips)
        if ctx == 1:
            return self.fi_shove_b[s][b], self.fi_opp_b[s][b]
        return self.vo_shove_b[s][b], self.vo_opp_b[s][b]

    def open_rate(self, s: int, late: bool, prior: float, n0: float) -> float:
        """Seat s's first-in open rate from late (or early) position, Beta-smoothed toward `prior` with n0 spots."""
        i = 0 if late else 1
        return (self.opens[s][i] + prior * n0) / (self.open_opp[s][i] + n0)

    def call_looseness(self, s: int, n0: float = 4.0) -> float:
        """Calls of shoves over the calls a solved caller would have made in the same spots (1 = Nash-like),
        smoothed with n0 pseudo-shoves at the seat's own average expected rate. Needs call_prior."""
        faced = self.faced_shove[s]
        exp = self.faced_shove_exp[s]
        q = exp / faced if faced else 0.12
        return (self.called_shove[s] + n0 * q) / (exp + n0 * q)

    def call_vs_shove(self, s: int) -> float:
        return _rate(self.called_shove[s], self.faced_shove[s], self.P_CALL_SHOVE, self.prior_n)

    def wtsd(self, s: int) -> float:
        return _rate(self.showdowns[s], self.vpip[s], self.P_WTSD, self.prior_n)

    def aggression(self, s: int) -> float:
        return _rate(self.post_aggr[s], self.post_actions[s], self.P_AGG, self.prior_n)

    def raise_freq(self, s: int) -> float:
        return _rate(self.raises[s], self.actions[s], 0.2, self.prior_n)

    # ------------------------------------------------------------------ flags
    def faced_total(self, s: int) -> int:
        return self.pre_faced[s] + self.post_faced[s]

    def dead_seat(self, s: int) -> bool:
        """Never voluntarily put a chip in, yet has faced >= dead_after bets. A crashed/timing-out bot."""
        return self.faced_total(s) >= self.dead_after and self.calls[s] + self.raises[s] == 0

    def station(self, s: int) -> bool:
        return self.faced_total(s) >= self.station_after and self.fold_to_bet(s) < 0.2 and not self.maniac(s)

    def maniac(self, s: int) -> bool:
        return self.actions[s] >= self.maniac_after and self.raise_freq(s) > 0.5

    def nit(self, s: int) -> bool:
        return self.hands[s] >= self.nit_after and self.vpip_rate(s) < 0.12

    def random_like(self, s: int) -> bool:
        """Fold / call / raise each used at least a fifth of the time when facing a bet, with enough data."""
        faced = self.faced_total(s)
        if faced < self.random_after:
            return False
        folds = self.pre_folded[s] + self.post_folded[s]
        # calls and raises while facing a bet are everything that was not a fold
        rest = faced - folds
        if rest <= 0:
            return False
        acted = self.actions[s]
        r = self.raises[s] / acted if acted else 0.0
        f = folds / faced
        c = rest / faced - r
        return f >= 0.2 and r >= 0.2 and c >= 0.15 and 0.2 <= self.checks_free[s] / max(1, acted) + f <= 0.9

    def archetype(self, s: int) -> str:
        if self.dead_seat(s):
            return "dead"
        if self.maniac(s):
            return "maniac"
        if self.station(s):
            return "station"
        if self.random_like(s):
            return "random"
        if self.nit(s):
            return "nit"
        return "unknown"

    # ------------------------------------------------------------------ dials
    def exploit_dials(self, s: int) -> dict:
        """Cached per seat; recomputed at hand_end (or on first read after it: `lazy`). Keys: bluff_mult,
        value_threshold_shift, steal_mult, call_down_mult."""
        if self._stale and not self._fresh >> s & 1:
            self._dials[s] = self._compute_dials(s)
            self._fresh |= 1 << s
        return self._dials[s]

    def _compute_dials(self, s: int) -> dict:
        n_obs = self.actions[s]
        w = n_obs / (n_obs + self.blend_n) * self.dial_strength  # 0 with no data, ->1 with many actions
        if w > 1.0:
            w = 1.0
        kind = self.archetype(s)
        if kind == "dead":
            target = (3.0, 0.0, 2.0, 1.0)
            w = 1.0 if self.dial_strength > 0.0 else 0.0
        elif kind == "station":
            target = (0.0, -1.0, 0.7, 0.8)
        elif kind == "maniac":
            target = (0.3, -1.0, 0.8, 1.4)
        elif kind == "random":
            target = (0.5, -1.0, 1.2, 1.3)
        elif kind == "nit":
            target = (1.5, 1.0, 1.5, 0.6)
        else:
            ftb = self.fold_to_bet(s)
            target = (0.5 + ftb, 0.0, 0.5 + self.fold_to_bet_pre(s), 1.4 + self.calldown_slope * self.aggression(s))
        return {
            "bluff_mult": 1.0 + w * (target[0] - 1.0),
            "value_threshold_shift": w * target[1],
            "steal_mult": 1.0 + w * (target[2] - 1.0),
            "call_down_mult": 1.0 + w * (target[3] - 1.0),
        }

    def summary(self, s: int) -> dict:
        return {
            "hands": self.hands[s], "vpip": round(self.vpip_rate(s), 2), "pfr": round(self.pfr_rate(s), 2),
            "ftb_pre": round(self.fold_to_bet_pre(s), 2), "ftb_post": round(self.fold_to_bet_post(s), 2),
            "shove": round(self.shove_rate(s), 2), "call_shove": round(self.call_vs_shove(s), 2),
            "wtsd": round(self.wtsd(s), 2), "agg": round(self.aggression(s), 2), "type": self.archetype(s),
        }
