# Origin: the climb's R6 adaptive test opponent, the tuning copy (docs/decisions.md, "The climb: addendum 9"). Written
# from scratch by the R6 worker, who had repo access (docs/drills/climb/r6-log.md); nothing in it is taken from F,
# Hero, the rivals or the exploiters. Played through hyperion.sim.bestiary.Adapt1Bot (registry name `adapt1`, and
# `adapt1_off`, the same bot with its counters off): a test opponent, never in a night pool. Its held-out twin is a
# separate build by a fresh agent with no repo access; this file is the one we may tune.
"""Adaptive red-team bot: a sound, general bot that learns each seat inside one table and switches on fixed counters.

Kit shape (the brief's kit.Agent): new_table(rules, seat, n_players), act(obs) -> (kind, raise-to total),
hand_end(result). It reads only the public table: the observation, each hand's action history and, at hand end,
the cards shown at showdown. It never sees who sits where; every count below is per seat number, for this table only.

**Baseline.** Preflop: a hand-score ranking of the 169 classes (percentile of all 1,326 combos), position-scaled open
ranges, 3-bets for value with a few bluffs, calls scaled by the opener's position, a 3-bet defence scaled to the range
it opened, push/fold at 15 bb or less, and calls of all-ins priced by pot odds against the jammer's likely range.
Postflop: a rule-based strength in [0, 1] (made hand against the board, kicker, texture) plus a draw bonus; value
bets, c-bets, stabs and semi-bluffs at fixed frequencies; calls by pot odds plus a street margin; raises with the
nuts-ish.

**What it counts, per seat, from each hand's history** (replayed at hand end, with blinds, all-ins and street ends as
the engine plays them): fold to a single bet by street; check-then-fold (it checked, then faced a bet); fold to a
raise after betting, split by the size of its bet; fold to a 3-bet as the opener, and its 4-bets; fold to an open;
c-bet rate as the preflop raiser; calls of all-ins (anyone's, and ours); and, from showdowns, the strength each of its
bet sizes turned out to hold. Rates are shrunk toward a prior; postflop folds are pooled over streets, and each
street's, check-then-fold and the like are shrunk toward the pooled rate, so a seat is readable after a few spots.

**Counters**, on from hand WARMUP + 1 for a seat whose counts pass the threshold (`COUNTERS = False` is the twin):
1. bluff where seats fold too much: bet half pot with any hand when the chance every live opponent folds (each at its
   estimate) is BLUFF_MARGIN over the break-even; open 1.6x wider when every seat behind folds to opens 80%;
2. value-bet thinner where seats call too much (every live opponent folds to bets at most STATION), and stop bluffing;
3. 3-bet lighter (LIGHT_3 of hands, LIGHT_3_MORE at 80% folds, a jam with LIGHT_JAM at 22 bb or less) against an
   opener that folds to 3-bets at least F3_LIGHT, 4-bets at most 1 in 8, and has not 4-bet in its last six answers;
4. bet sizes against strength: raise a small bet (SMALL of the pot or less) heads-up on the flop or turn with any hand
   when that seat folds to raises after small bets, or its small bets showed weak at showdown and its large ones
   stronger; call large bets tighter when they showed strong; raise its larger bets when it folds 70% to raises there;
5. jams by all-in calls: a 0.7x jam range when a seat behind calls all-ins 55% or more; any hand whose jam beats
   folding when every seat behind has called at most 20% of our own jams.
Counter 3 stops itself against an opener that starts 4-betting (F does heads-up), and counter 5 reads only calls of
our own jams, because a seat that reads our range calls wider as we jam wider.
"""
import random

try:
    from kit import Agent
except Exception:  # run outside the kit
    class Agent(object):
        def new_table(self, rules, seat, n_players):
            pass

        def act(self, obs):
            raise NotImplementedError

        def hand_end(self, result):
            pass


# ------------------------------------------------------------------------------------------------ cards and hands
_POP = [bin(m).count("1") for m in range(8192)]
_STRAIGHT = [-1] * 8192  # 13-bit rank mask -> high rank of the best straight in it, -1 if none (wheel: 3)
for _m in range(8192):
    for _hi in range(12, 3, -1):
        _w = 0x1F << (_hi - 4)
        if _m & _w == _w:
            _STRAIGHT[_m] = _hi
            break
    else:
        if _m & 0x100F == 0x100F:
            _STRAIGHT[_m] = 3


def _top(mask, k):
    out = []
    r = 12
    while r >= 0 and len(out) < k:
        if mask >> r & 1:
            out.append(r)
        r -= 1
    return out


def evaluate(cards):
    """Best hand among the cards as one comparable int: category << 20 | ranks (8 straight flush .. 0 high card)."""
    rc = [0] * 13
    sm = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        rc[r] += 1
        sm[c & 3] |= 1 << r
    fl = -1
    for m in sm:
        if _POP[m] >= 5:
            fl = m
            sf = _STRAIGHT[m]
            if sf >= 0:
                return 8 << 20 | sf << 16
    quads, trips, pairs, mask = [], [], [], 0
    for r in range(12, -1, -1):
        k = rc[r]
        if k:
            mask |= 1 << r
            if k == 4:
                quads.append(r)
            elif k == 3:
                trips.append(r)
            elif k == 2:
                pairs.append(r)
    if quads:
        q = quads[0]
        kick = _top(mask & ~(1 << q), 1)
        return 7 << 20 | q << 16 | (kick[0] if kick else 0) << 12
    if trips and (len(trips) > 1 or pairs):
        p = max(trips[1] if len(trips) > 1 else -1, pairs[0] if pairs else -1)
        return 6 << 20 | trips[0] << 16 | p << 12
    if fl >= 0:
        v = 5 << 20
        for i, r in enumerate(_top(fl, 5)):
            v |= r << (16 - 4 * i)
        return v
    st = _STRAIGHT[mask]
    if st >= 0:
        return 4 << 20 | st << 16
    if trips:
        t = trips[0]
        v = 3 << 20 | t << 16
        for i, r in enumerate(_top(mask & ~(1 << t), 2)):
            v |= r << (12 - 4 * i)
        return v
    if len(pairs) >= 2:
        a, b = pairs[0], pairs[1]
        kick = _top(mask & ~(1 << a) & ~(1 << b), 1)
        return 2 << 20 | a << 16 | b << 12 | (kick[0] if kick else 0) << 8
    if pairs:
        p = pairs[0]
        v = 1 << 20 | p << 16
        for i, r in enumerate(_top(mask & ~(1 << p), 3)):
            v |= r << (12 - 4 * i)
        return v
    v = 0
    for i, r in enumerate(_top(mask, 5)):
        v |= r << (16 - 4 * i)
    return v


def strength(hole, board):
    """(made, draw) for two hole cards on a 3-5 card board. `made` is a rough equity of the made hand against a
    sensible continuing range, in [0, 1]; `draw` is the extra equity of a flush or straight draw (0 on the river)."""
    h1, h2 = hole[0] >> 2, hole[1] >> 2
    nb = len(board)
    br = [c >> 2 for c in board]
    bc = [0] * 13
    bs = [0, 0, 0, 0]
    bmask = 0
    for c in board:
        bc[c >> 2] += 1
        bs[c & 3] += 1
        bmask |= 1 << (c >> 2)
    ub = _top(bmask, 5)  # distinct board ranks, high to low
    top = ub[0]
    second = ub[1] if len(ub) > 1 else -1
    flushy = max(bs) >= 3
    straighty = False
    for hi in range(12, 3, -1):
        if _POP[bmask & (0x1F << (hi - 4))] >= 3:
            straighty = True
            break
    if not straighty and _POP[bmask & 0x100F] >= 3:
        straighty = True
    bpair = max(bc) >= 2
    val = evaluate(list(hole) + list(board))
    cat = val >> 20
    if nb == 5 and evaluate(board) >= val:
        return 0.2, 0.0  # we play the board
    made = 0.0
    if cat == 8:
        made = 0.99
    elif cat == 7:
        made = 0.6 if max(bc) == 4 else 0.99
    elif cat == 6:
        made = 0.86 if max(bc) == 3 else (0.9 if sum(1 for x in bc if x >= 2) >= 2 else 0.96)
    elif cat == 5:
        suit = next(s for s in range(4) if bs[s] + (hole[0] & 3 == s) + (hole[1] & 3 == s) >= 5)
        mine = [c >> 2 for c in hole if c & 3 == suit]
        if not mine:
            made = 0.22
        else:
            hi = max(mine)
            on_board = 0
            for c in board:
                if c & 3 == suit:
                    on_board |= 1 << (c >> 2)
            higher = sum(1 for r in range(hi + 1, 13) if not on_board >> r & 1)
            made = max(0.7, 0.95 - 0.04 * higher)
            if bpair:
                made -= 0.1
            if bs[suit] >= 4 and len(mine) == 1:
                made -= 0.05
    elif cat == 4:
        made = 0.86 - (0.14 if flushy else 0.0) - (0.08 if bpair else 0.0)
        if nb >= 4 and _STRAIGHT[bmask] < 0:
            # a straight that needs only one of our cards on a four-straight board is weaker
            if _STRAIGHT[bmask | 1 << h1] >= 0 or _STRAIGHT[bmask | 1 << h2] >= 0:
                made -= 0.06
    elif cat == 3:
        t = (val >> 16) & 15
        if h1 == h2 == t:
            made = 0.93 - (0.1 if flushy else 0.0) - (0.06 if straighty else 0.0)
        elif bc[t] == 3:
            made = 0.18 + 0.01 * max(h1, h2)
        else:
            k = h2 if h1 == t else h1
            made = 0.78 + 0.008 * k - (0.08 if flushy else 0.0)
    elif cat == 2:
        if h1 != h2 and bc[h1] >= 1 and bc[h2] >= 1:
            made = (0.86 if {h1, h2} == {top, second} else 0.8) - (0.1 if flushy else 0.0) - (0.05 if straighty else 0.0)
        elif h1 == h2:
            made = 0.72 if h1 > top else (0.5 if h1 > second else 0.35)
        elif bc[h1] >= 1 or bc[h2] >= 1:
            r = h1 if bc[h1] >= 1 else h2
            k = h2 if r == h1 else h1
            made = (0.6 + 0.01 * k if r == top else (0.44 if r == second else 0.34)) - 0.06
        else:
            made = 0.14 + 0.01 * max(h1, h2)
    elif cat == 1:
        if h1 == h2:
            made = 0.7 + 0.012 * h1 if h1 > top else (0.52 if h1 > second else 0.36)
        elif bc[h1] >= 1 or bc[h2] >= 1:
            r = h1 if bc[h1] >= 1 else h2
            k = h2 if r == h1 else h1
            if r == top:
                made = 0.6 + 0.012 * k
            elif r == second:
                made = 0.46 + 0.006 * k
            else:
                made = 0.36 + 0.004 * k
        else:
            cat = 0
    if cat == 0:
        overs = (h1 > top) + (h2 > top)
        made = (0.06 + 0.01 * max(h1, h2) + 0.04 * overs) if nb < 5 else (0.04 + 0.012 * max(h1, h2))
    if made < 0.85:
        made -= 0.03 if nb == 4 else (0.05 if nb == 5 else 0.0)
    draw = 0.0
    if nb < 5 and cat < 4:
        fd = False
        for s in range(4):
            mine = (hole[0] & 3 == s) + (hole[1] & 3 == s)
            if mine and bs[s] + mine == 4:
                fd = True
        allmask = bmask | 1 << h1 | 1 << h2
        outs = 0
        for r in range(13):
            bit = 1 << r
            if not allmask & bit and _STRAIGHT[allmask | bit] >= 0 and _STRAIGHT[bmask | bit] < 0:
                outs += 1
        flop = nb == 3
        if fd:
            draw += 0.18 if flop else 0.1
        if outs >= 2:
            draw += 0.15 if flop else 0.085
        elif outs == 1:
            draw += 0.07 if flop else 0.04
        if draw > 0.27:
            draw = 0.27
        if made >= 0.45:
            draw *= 0.5
    return made, draw


# preflop: a hand score per class, ranked into the share of all 1,326 combos at least as strong (lower = better)
def _pre_score(hi, lo, suited):
    if hi == lo:
        return 13.0 + 2.0 * hi
    gap = hi - lo - 1
    s = 1.6 * hi + 0.9 * lo + (3.0 if suited else 0.0) - ((0.0, 1.0, 2.5, 4.0)[gap] if gap < 4 else 5.5)
    if gap <= 1 and 2 <= lo and hi <= 9:
        s += 0.8
    return s


_CLASSES = [(hi, lo, su) for hi in range(13) for lo in range(hi + 1) for su in ((False,) if hi == lo else (True, False))]
_CLASSES.sort(key=lambda c: -_pre_score(*c))
PCT = {}
_cum = 0
for _c in _CLASSES:
    _w = 6 if _c[0] == _c[1] else (4 if _c[2] else 12)
    PCT[_c] = (_cum + _w / 2.0) / 1326.0
    _cum += _w


def pre_pct(hole):
    r1, r2 = hole[0] >> 2, hole[1] >> 2
    if r1 < r2:
        r1, r2 = r2, r1
    return PCT[(r1, r2, r1 != r2 and (hole[0] & 3) == (hole[1] & 3))]


OPEN_PCT = {1: 0.5, 2: 0.42, 3: 0.3, 4: 0.22, 5: 0.18, 6: 0.15, 7: 0.13}  # players behind -> first-in raise range
PUSH_PCT = {1: 0.6, 2: 0.42, 3: 0.32, 4: 0.25, 5: 0.2, 6: 0.17, 7: 0.15}  # the same for a first-in jam at 15 bb


# ------------------------------------------------------------------------------------------------ history replay
def replay(start, button, blinds, ante, history):
    """The hand's actions with their context, as the engine plays them. Yields dicts with: street, seat, kind, amt
    (raise-to total), facing (chips to call before acting), nr (raises this street before it), pot (chips in before
    it: earlier streets plus this street's bets), cur (the bet to match), stack (chips behind before it), allin_raiser
    (the seat it faces went all-in), checked (it had checked this street), raised (it had bet or raised this street),
    last_bet_frac (the size of its own last bet this street, share of the pot before it), first_bet (a bet into no bet:
    its size, share of the pot), aggressor (the last raiser this street before it), frac (a raise's increment over
    the bet it faced, share of the pot before it)."""
    n = len(start)
    alive = [s for s in range(n) if start[s] > 0]
    if len(alive) < 2:
        return []
    rem = list(start)
    pot = 0
    if ante:
        for s in alive:
            a = min(ante, rem[s])
            rem[s] -= a
            pot += a

    def after(s):
        for i in range(1, n + 1):
            t = (s + i) % n
            if start[t] > 0:
                return t
        return s

    if len(alive) == 2:
        sbs = button if start[button] > 0 else after(button)
        bbs = after(sbs)
    else:
        sbs = after(button)
        bbs = after(sbs)
    bet = [0] * n
    for s, b in ((sbs, blinds[0]), (bbs, blinds[1])):
        a = min(b, rem[s])
        rem[s] -= a
        bet[s] += a
    inh = [start[s] > 0 for s in range(n)]
    cur = max(bet)
    street = 0
    nr = 0
    need = set(s for s in alive if rem[s] > 0)
    checked, raised, lastfrac = set(), set(), {}
    aggr = None
    out = []

    def responders(s):
        return any(o != s and inh[o] and rem[o] > 0 for o in range(n))

    def prune():
        for s in list(need):
            if not inh[s] or rem[s] == 0 or (cur - bet[s] <= 0 and not responders(s)):
                need.discard(s)

    for seat, act in history:
        kind = act[0]
        if kind not in ("fold", "check", "call", "raise"):
            continue
        amt = act[1] if len(act) > 1 else 0
        facing = max(0, cur - bet[seat])
        ar = aggr is not None and rem[aggr] == 0 and facing > 0
        ev = {"street": street, "seat": seat, "kind": kind, "amt": amt, "facing": facing, "nr": nr,
              "pot": pot + sum(bet), "cur": cur, "stack": rem[seat], "allin_raiser": ar, "checked": seat in checked,
              "raised": seat in raised, "last_bet_frac": lastfrac.get(seat), "first_bet": None, "aggressor": aggr,
              "frac": None}
        need.discard(seat)
        if kind == "fold":
            inh[seat] = False
        elif kind == "call":
            a = min(facing, rem[seat])
            rem[seat] -= a
            bet[seat] += a
        elif kind == "check":
            checked.add(seat)
        else:
            put = min(max(0, amt - bet[seat]), rem[seat])
            before = pot + sum(bet)
            rem[seat] -= put
            bet[seat] += put
            if bet[seat] > cur:
                if cur == 0 and street > 0:
                    ev["first_bet"] = put / before if before > 0 else 1.0
                lastfrac[seat] = ev["frac"] = (bet[seat] - cur) / before if before > 0 else 1.0
                cur = bet[seat]
                nr += 1
                aggr = seat
                raised.add(seat)
                for o in range(n):
                    if o != seat and inh[o] and rem[o] > 0:
                        need.add(o)
        out.append(ev)
        live = [s for s in range(n) if inh[s]]
        if len(live) <= 1:
            break
        prune()
        while not need:
            pot += sum(bet)
            bet = [0] * n
            cur = 0
            nr = 0
            aggr = None
            checked, raised, lastfrac = set(), set(), {}
            street += 1
            if street > 3:
                return out
            need = set(s for s in live if rem[s] > 0)
            if len(need) < 2:
                need = set()  # nobody left to bet against: no more actions this hand
                if street >= 3:
                    return out
                continue
            prune()
    return out


# ------------------------------------------------------------------------------------------------ the bot
_KEYS = ("fb1n", "fb1f", "fb2n", "fb2f", "fb3n", "fb3f", "xfn", "xff", "frn", "frf", "frsn", "frsf", "frln", "frlf",
         "f3n", "f3f", "f34", "fon", "fof", "cbn", "cby", "jcn", "jcc", "jmn", "jmc")


class Bot(Agent):
    COUNTERS = True  # False: the twin, the same bot with every counter off
    WARMUP = 30  # hands played at this table before any counter may switch on
    MIN_N = 4  # postflop single bets faced (all streets) before its fold rates are trusted
    MIN_N_RARE = 2  # 3-bets faced as the opener before its fold-to-3-bet rate is
    BLUFF_MARGIN = 0.12  # a counter bluff needs the fold estimate this far above the bet's break-even
    STATION = 0.3  # a seat folding to bets at or below this rate gets thin value and no bluffs
    F3_LIGHT = 0.7  # an opener folding to 3-bets at or above this rate (4-betting at most 1 in 8) gets 3-bet light:
    LIGHT_3, LIGHT_3_MORE, LIGHT_JAM = 0.3, 0.45, 0.3  # with this share of hands (at 80%+ folds; as a jam at 22 bb)
    HU_FLOP_DEFEND = 0.06
    SMALL = 0.45  # a bet at or below this share of the pot is "small"
    LARGE = 0.6

    def __init__(self):
        self.rng = random.Random(0xAD)
        self.new_table({}, 0, 8)

    # ----- table state -----
    def new_table(self, rules, seat, n_players):
        self.n = n_players or 8
        self.me = seat or 0
        self.st = [dict.fromkeys(_KEYS, 0) for _ in range(self.n)]
        self.sd = [([], []) for _ in range(self.n)]  # per seat: showdown strengths behind its small / large bets
        self.f3_recent = [[] for _ in range(self.n)]  # per seat: its answers to 3-bets as opener ("f", "c", "r")
        self.hand = None
        self.start = None
        self.button = 0
        self.blinds = (10, 20)
        self.ante = 0
        self.played = 0  # hands seen at this table
        self.on = False
        self.trace = None  # a diagnostic may set a list: (hand_no, counter tag) per counter that acted

    def _tag(self, name):
        if self.trace is not None:
            self.trace.append((self.hand, name))

    # ----- estimates (None = not enough evidence, or counters off) -----
    def _rate(self, s, num, den, prior, m=4.0, min_n=None):
        if not self.on or s == self.me:
            return None
        d = self.st[s]
        if d[den] < (self.MIN_N if min_n is None else min_n):
            return None
        return (d[num] + prior * m) / (d[den] + m)

    def pooled_fold(self, s):
        """Its fold rate to a single postflop bet, all streets pooled (None below MIN_N observations)."""
        if not self.on or s == self.me:
            return None
        d = self.st[s]
        n = d["fb1n"] + d["fb2n"] + d["fb3n"]
        if n < self.MIN_N:
            return None
        return (d["fb1f"] + d["fb2f"] + d["fb3f"] + 0.45 * 4.0) / (n + 4.0)

    def _toward(self, s, num, den, m=3.0):
        """A sparse rate shrunk toward the seat's pooled fold-to-bet rate (None when that is not known yet)."""
        base = self.pooled_fold(s)
        if base is None:
            return None
        d = self.st[s]
        return (d[num] + base * m) / (d[den] + m)

    def fold_to_bet(self, s, street, checked):
        """Its fold rate to our bet on this street: the street's own count shrunk toward the pooled rate, or the
        check-then-fold count if it checked to us."""
        if checked:
            return self._toward(s, "xff", "xfn")
        return self._toward(s, "fb%df" % street, "fb%dn" % street)

    # ----- acting -----
    def act(self, obs):
        try:
            a = self._act(obs)
        except Exception:
            a = None
        return self._legal(a, obs)

    def _legal(self, a, obs):
        legal = obs.legal
        if a is not None and a[0] == "raise" and "raise" in legal:
            amt = int(a[1])
            lo, hi = obs.min_raise, obs.max_raise
            amt = lo if amt < lo else (hi if amt > hi else amt)
            if hi - amt < 0.3 * amt:  # do not leave a sliver behind
                amt = hi
            return ("raise", amt)
        if a is not None and a[0] == "raise":
            a = ("call", 0)
        if a is not None and a[0] in legal:
            return (a[0], 0)
        if "check" in legal:
            return ("check", 0)
        return ("fold", 0)

    def _act(self, obs):
        n = len(obs.stacks)
        if obs.hand_no != self.hand:
            self.hand = obs.hand_no
            self.button = obs.button
            self.blinds = tuple(obs.blinds)
            alive = [s for s in range(n) if obs.stacks[s] + obs.bets[s] > 0 or obs.in_hand[s]]
            self.ante = obs.pot // len(alive) if obs.street == 0 and obs.pot and alive else 0
            self.start = [obs.stacks[s] + obs.bets[s] + (self.ante if s in alive else 0) for s in range(n)] \
                if obs.street == 0 else None
        self.on = self.COUNTERS and self.played >= self.WARMUP
        evs = replay(self.start, self.button, self.blinds, self.ante, obs.history) if self.start else []
        if obs.street == 0:
            return self._preflop(obs, evs)
        return self._postflop(obs, evs)

    # ----- preflop -----
    def _order(self, obs):
        """Seats dealt in, in preflop order (the big blind last)."""
        n = len(obs.stacks)
        start = self.start or [obs.stacks[s] + obs.bets[s] for s in range(n)]
        alive = [s for s in range(n) if start[s] > 0]
        b = obs.button

        def after(s):
            for i in range(1, n + 1):
                t = (s + i) % n
                if start[t] > 0:
                    return t
            return s

        if len(alive) == 2:
            sbs = b if start[b] > 0 else after(b)
            return [sbs, after(sbs)]
        sbs = after(b)
        bbs = after(sbs)
        first = after(bbs)
        order = [first]
        while len(order) < len(alive):
            order.append(after(order[-1]))
        return order

    def _jam_call(self, obs, pct, jam_range, need):
        k = 1.6 - 2.6 * need
        k = 0.15 if k < 0.15 else (1.5 if k > 1.5 else k)
        alive = sum(1 for s in range(len(obs.stacks)) if obs.stacks[s] + obs.bets[s] > 0)
        if alive >= 5:
            k *= 0.8
        return pct <= jam_range * k

    def _preflop(self, obs, evs):
        me = obs.seat
        bb = obs.blinds[1] or 1
        pct = pre_pct(obs.hole)
        n = len(obs.stacks)
        mine = obs.stacks[me] + obs.bets[me]
        opps = [s for s in range(n) if s != me and obs.in_hand[s]]
        eff = min(mine, max(obs.stacks[s] + obs.bets[s] for s in opps)) / bb if opps else 0
        raises = [e for e in evs if e["kind"] == "raise"]
        nraise = len(raises)
        order = self._order(obs)
        idx = order.index(me) if me in order else 0
        behind = [s for s in order[idx + 1:] if obs.in_hand[s]]
        C = obs.to_call
        pot = obs.pot + sum(obs.bets)
        alive_n = len(order)
        rng = self.rng.random()
        if nraise == 0:
            if C == 0:  # the big blind's option after limps
                return ("raise", int(obs.bets[me] + 3 * bb + pot)) if pct <= 0.1 else ("check", 0)
            k = len(behind)
            limped = any(e["kind"] == "call" for e in evs)
            if eff <= 15:
                p = PUSH_PCT.get(k, 0.13) * (15.0 / max(eff, 2.0)) ** 0.6
                if alive_n == 2:
                    p = max(p, 0.7)
                p = self._jam_adjust(obs, behind, p, pct)
                return ("raise", obs.max_raise) if pct <= min(p, 1.0) else ("fold", 0)
            p = OPEN_PCT.get(k, 0.13) if alive_n > 2 else 0.8
            if limped:
                return ("raise", int(4 * bb + pot)) if pct <= 0.6 * p else (("call", 0) if pct <= 0.08 else ("fold", 0))
            if self.on and behind:
                fo = [self._rate(s, "fof", "fon", 0.6) for s in behind]
                if all(f is not None and f >= 0.8 for f in fo):  # every seat behind folds to opens
                    if pct > p:
                        self._tag("open_wide")
                    p = min(1.0, p * 1.6)
            size = 2.5 if alive_n >= 5 else 2.2
            return ("raise", int(size * bb)) if pct <= p else ("fold", 0)
        opener = raises[0]["seat"]
        if nraise == 1:
            ev0 = raises[0]
            o_order = order.index(opener) if opener in order else 0
            o_k = len(order) - 1 - o_order
            o_jam = obs.stacks[opener] == 0
            o_range = (PUSH_PCT if o_jam else OPEN_PCT).get(o_k, 0.13) if alive_n > 2 else 0.8
            need = C / float(pot + C)
            if o_jam or C >= 0.45 * obs.stacks[me]:
                return ("call", 0) if self._jam_call(obs, pct, o_range, need) else ("fold", 0)
            callers = sum(1 for e in evs if e["kind"] == "call" and e["nr"] == 1)
            f3 = self._rate(opener, "f3f", "f3n", 0.5, m=2.0, min_n=self.MIN_N_RARE) if not callers else None
            d = self.st[opener]
            recent = self.f3_recent[opener][-6:]
            light = (f3 is not None and f3 >= self.F3_LIGHT and d["f34"] * 8 <= d["f3n"]  # it seldom 4-bets,
                     and "r" not in recent and recent[-4:].count("f") >= 0.75 * len(recent[-4:]))  # nor lately
            if eff <= 22:
                jam = o_range * 0.35
                if light:
                    if o_range * 0.35 < pct <= max(jam, self.LIGHT_JAM):
                        self._tag("3bet_light")
                    jam = max(jam, self.LIGHT_JAM)
                return ("raise", obs.max_raise) if pct <= jam else (
                    ("call", 0) if obs.bets[me] * 2 >= C and pct <= o_range * 0.5 and eff > 12 else ("fold", 0))
            value3 = max(0.03, o_range * 0.08)
            bb_seat = order[-1] == me
            call_pct = min(0.6, o_range * (0.9 if bb_seat else 0.5) + (0.08 if bb_seat else 0.0))
            if ev0["amt"] > 4 * bb:
                call_pct *= 0.6
            ip = me != order[-1] and me != order[-2] if alive_n > 2 else me == order[0]
            to3 = int(ev0["amt"] * (3.0 if ip else 3.6) + callers * ev0["amt"])
            if pct <= value3:
                return ("raise", to3)
            if light and pct <= (self.LIGHT_3 if f3 < 0.8 else self.LIGHT_3_MORE):
                self._tag("3bet_light")
                return ("raise", to3)
            if call_pct < pct <= call_pct + 0.06 and rng < 0.3 and not callers:
                return ("raise", to3)
            return ("call", 0) if pct <= call_pct else ("fold", 0)
        need = C / float(pot + C)
        last = raises[-1]
        if obs.stacks[last["seat"]] == 0 or C >= 0.45 * obs.stacks[me]:
            depth = (obs.stacks[last["seat"]] + obs.bets[last["seat"]]) / float(bb)
            jr = 0.25 if depth <= 15 else (0.12 if depth <= 25 else (0.06 if nraise == 2 else 0.035))
            return ("call", 0) if self._jam_call(obs, pct, jr, need) else ("fold", 0)
        if nraise == 2 and opener == me:  # our open was 3-bet: defend in proportion to the range we opened
            mine = len(order) - 1 - order.index(me) if me in order else 1
            r = OPEN_PCT.get(mine, 0.13) if alive_n > 2 else 0.8
            if pct <= max(0.03, 0.1 * r) or (eff <= 35 and pct <= max(0.06, 0.15 * r)):
                return ("raise", obs.max_raise)
            if pct <= max(0.1, 0.35 * r) and eff >= 25:
                return ("call", 0)
            return ("fold", 0)
        if pct <= 0.025:
            return ("raise", obs.max_raise)
        return ("fold", 0)

    def _jam_adjust(self, obs, behind, p, pct):
        """Counter 5: a first-in jam against the seats left to act, by how often they call all-ins. Tighter (0.7x the
        range) if one calls them often; wider when all are known: jam any hand whose jam beats folding, with q the
        chance someone calls (each at its own all-in call rate) and our equity against a calling range of the top q
        put at 0.5 + 0.3 (q - pct) / (q + pct)."""
        if not self.on or not behind:
            return p
        rates = [self._rate(s, "jcc", "jcn", 0.35, m=3.0, min_n=3) for s in behind]
        known = [r for r in rates if r is not None]
        if known and max(known) >= 0.55:
            self._tag("jam_tight")
            return p * 0.7
        # wider only on calls of our own jams: a seat that reads our range calls wider as we jam wider
        mine = [self._rate(s, "jmc", "jmn", 0.35, m=3.0, min_n=3) for s in behind]
        if all(r is not None and r <= 0.2 for r in mine) and pct > p:
            rates = mine
            q = 1.0
            for r in rates:
                q *= 1.0 - r
            q = 1.0 - q
            me = obs.seat
            risk = obs.stacks[me] + obs.bets[me]
            pot = obs.pot + sum(obs.bets)
            eq = 0.5 + 0.3 * (q - pct) / (q + pct)
            ev = (1.0 - q) * pot + q * (eq * (2 * risk + pot - obs.bets[me]) - risk) - obs.bets[me] * (1.0 - q)
            if ev > 0:
                self._tag("jam_wide")
                return 1.0
        return p

    # ----- postflop -----
    def _postflop(self, obs, evs):
        me = obs.seat
        n = len(obs.stacks)
        street = obs.street
        made, draw = strength(obs.hole, obs.board)
        e = made + draw
        opps = [s for s in range(n) if s != me and obs.in_hand[s]]
        live = [s for s in opps if obs.stacks[s] > 0]
        nopp = len(opps)
        pot = obs.pot + sum(obs.bets)
        C = obs.to_call
        rng = self.rng.random()
        pre = [x for x in evs if x["street"] == 0 and x["kind"] == "raise"]
        pfa = pre[-1]["seat"] if pre else None
        cur_evs = [x for x in evs if x["street"] == street]
        if nopp > 1:
            e -= 0.05 * (nopp - 1) if made < 0.85 else 0.0
        order = [(obs.button + i) % n for i in range(1, n + 1)]
        in_order = [s for s in order if obs.in_hand[s]]
        ip = in_order and in_order[-1] == me
        my_stack = obs.stacks[me]
        if C == 0:
            vt = {1: 0.66, 2: 0.7, 3: 0.72}.get(street, 0.72) + 0.04 * (nopp - 1)
            bluff_ok = True
            folds = None
            if self.on and live:
                checked = set(x["seat"] for x in cur_evs if x["kind"] == "check")
                fs = [self.fold_to_bet(s, min(street, 3), s in checked) for s in live]
                if all(f is not None for f in fs):
                    folds = 1.0
                    for f in fs:
                        folds *= f
                    if max(fs) <= self.STATION:  # counter 2: they call too much
                        vt = {1: 0.5, 2: 0.54, 3: 0.58}.get(street, 0.58)
                        bluff_ok = False
            if e >= vt or made >= vt:
                if not bluff_ok and max(e, made) < {1: 0.66, 2: 0.7, 3: 0.72}.get(street, 0.72) + 0.04 * (nopp - 1):
                    self._tag("thin_value")
                size = 0.75 if (made >= 0.85 and street == 3) or not bluff_ok and made >= 0.75 else 0.6
                return self._bet(obs, size, pot)
            if folds is not None and bluff_ok and folds >= 0.5 / 1.5 + self.BLUFF_MARGIN:  # counter 1
                self._tag("bluff_bet")
                return self._bet(obs, 0.5, pot)
            if not bluff_ok:
                self._tag("no_bluff")
                return ("check", 0)
            if street == 1 and pfa == me and nopp == 1:
                if draw >= 0.07 or made < 0.3:
                    return self._bet(obs, 0.5, pot) if rng < 0.55 else ("check", 0)
                return ("check", 0)
            if nopp == 1 and draw >= 0.12 and street < 3:
                return self._bet(obs, 0.55, pot) if rng < 0.5 else ("check", 0)
            if nopp == 1 and ip and made < 0.3 and street < 3 and all(x["kind"] == "check" for x in cur_evs):
                return self._bet(obs, 0.5, pot) if rng < 0.3 else ("check", 0)
            if street == 3 and nopp == 1 and made < 0.2 and ip and rng < 0.12:
                return self._bet(obs, 0.6, pot)
            return ("check", 0)
        # facing a bet or a raise
        raises = [x for x in cur_evs if x["kind"] == "raise"]
        bettor = raises[-1]["seat"] if raises else None
        nr = len(raises)
        if raises and raises[-1]["frac"] is not None:
            bet_frac = raises[-1]["frac"]
        else:
            bet_frac = C / float(max(1, pot - C))
        need = C / float(pot + C)
        thr = 0.3 + 0.7 * need + {1: 0.0, 2: 0.04, 3: 0.07}.get(street, 0.07) + (0.12 if nr >= 2 else 0.0)
        if C >= 0.5 * my_stack:
            thr += 0.05
        if nopp == 1 and street == 1 and nr == 1:
            thr -= self.HU_FLOP_DEFEND  # a single flop bet heads-up: defend a little wider (a c-bet range is wide)
        raise_thr = {1: 0.86, 2: 0.88, 3: 0.9}.get(street, 0.9) + (0.05 if nr >= 2 else 0.0)
        small_weak = False
        frr = None
        if self.on and bettor is not None and bettor != me:
            small, large = self.sd[bettor]
            if nr == 1:
                if bet_frac <= self.SMALL:
                    sw = self._rate(bettor, "frsf", "frsn", 0.45, m=3.0, min_n=3)
                    sd_weak = len(small) >= 3 and sum(small) / len(small) <= 0.5 and (
                        len(large) < 2 or sum(large) / len(large) - sum(small) / len(small) >= 0.15)
                    small_weak = (sw is not None and sw >= 0.6) or sd_weak
                elif bet_frac >= self.LARGE and len(large) >= 3 and sum(large) / len(large) >= 0.68:
                    thr += 0.08  # counter 4: its large bets are strong
                if bet_frac > self.SMALL:
                    frr = self._rate(bettor, "frlf", "frln", 0.4, m=3.0, min_n=3)
        to = 3 * max(obs.bets)
        if made >= raise_thr:
            return ("raise", to)
        heads_up = nopp == 1
        if heads_up and nr == 1 and street < 3 and (small_weak or (frr is not None and frr >= 0.7)) and e < raise_thr:
            self._tag("raise_small" if small_weak else "raise_folder")
            return ("raise", to)  # counters 1 and 4: raise what reads weak or folds to raises
        if heads_up and nr == 1 and street == 1 and draw >= 0.15 and rng < 0.25:
            return ("raise", to)
        if e >= thr:
            return ("call", 0)
        if street == 1 and draw >= 0.15 and need <= 0.34:
            return ("call", 0)
        if street == 2 and draw >= 0.08 and need <= 0.22:
            return ("call", 0)
        return ("fold", 0)

    def _bet(self, obs, frac, pot):
        amt = int(obs.bets[obs.seat] + max(obs.blinds[1], frac * pot))
        if amt >= 0.7 * obs.max_raise:
            amt = obs.max_raise
        return ("raise", amt)

    # ----- learning -----
    def hand_end(self, result):
        try:
            self._learn(result)
        except Exception:
            pass

    def _learn(self, result):
        if not result:
            return
        hn = result.get("hand_no")
        if hn is not None and hn != self.hand:
            self.played += 1  # a hand we never acted in (folded to our big blind): counted, not replayed
            return
        self.played += 1
        if not self.start:
            return
        evs = replay(self.start, self.button, self.blinds, self.ante, result.get("history") or [])
        if not evs:
            return
        me = self.me
        bb = self.blinds[1] or 1
        pfa = None
        opener = None
        cb_seen = False
        bets_by = {}
        for e in evs:
            s, k, st = e["seat"], e["kind"], e["street"]
            d = self.st[s]
            if st == 0:
                if e["nr"] == 1 and s != opener and e["facing"] > 0 and not e["allin_raiser"]:
                    d["fon"] += 1
                    d["fof"] += k == "fold"
                if e["nr"] == 2 and s == opener and e["facing"] > 0 and not e["allin_raiser"]:
                    d["f3n"] += 1
                    d["f3f"] += k == "fold"
                    d["f34"] += k == "raise"
                    self.f3_recent[s].append(k[0])
                if k == "raise":
                    if e["nr"] == 0:
                        opener = s
                    pfa = s
            else:
                if st == 1 and s == pfa and not cb_seen and e["nr"] == 0:
                    cb_seen = True
                    d["cbn"] += 1
                    d["cby"] += k == "raise"
                elif st == 1 and e["nr"] > 0:
                    cb_seen = True
                if e["facing"] > 0 and not e["allin_raiser"]:
                    if e["raised"]:
                        d["frn"] += 1
                        d["frf"] += k == "fold"
                        lf = e["last_bet_frac"]
                        if lf is not None and lf <= self.SMALL:
                            d["frsn"] += 1
                            d["frsf"] += k == "fold"
                        else:
                            d["frln"] += 1
                            d["frlf"] += k == "fold"
                    elif e["nr"] == 1:
                        key = min(st, 3)
                        d["fb%dn" % key] += 1
                        d["fb%df" % key] += k == "fold"
                        if e["checked"]:
                            d["xfn"] += 1
                            d["xff"] += k == "fold"
                if e["first_bet"] is not None:
                    bets_by.setdefault(s, []).append((st, e["first_bet"]))
            if e["allin_raiser"] and e["facing"] >= 0.35 * max(1, e["stack"]) and e["facing"] >= 3 * bb:
                d["jcn"] += 1
                d["jcc"] += k != "fold"
                if e["aggressor"] == me:
                    d["jmn"] += 1
                    d["jmc"] += k != "fold"
        shown = result.get("showdown") or {}
        board = result.get("board") or ()
        for s, hole in shown.items():
            s = int(s)
            if s == me or s not in bets_by or len(hole) != 2:
                continue
            for st, frac in bets_by[s]:
                b = tuple(board[:{1: 3, 2: 4, 3: 5}.get(st, 5)])
                if len(b) < 3:
                    continue
                m, dr = strength(tuple(hole), b)
                small, large = self.sd[s]
                if frac <= self.SMALL:
                    small.append(m + dr)
                elif frac >= self.LARGE:
                    large.append(m + dr)
