# Origin: drill 3 (docs/drills/prompt-drill-3-trackB-kitA-bounty.md), Track B: a from-scratch build by an agent that
# saw only our prompts and Track B spec v1, never this repository, on fake kit A (string cards, "RAISE:<total>"
# answers) with a bounty twist (a showdown won holding a Seven pays 50 chips). Spec exhausted at minute 20; frozen at
# md5 b40150c0551b423454c6e9c9e927bea4 (the minute-19 upload, submission_step4.zip) and copied here unchanged apart
# from this header and the event's name, dropped from the docstring's first line for the public export. The archived
# original is docs/drills/field/trackb3_bot.py. It is played through hyperion.sim.bestiary.TrackBKitABot (registry
# name `trackb3`), one of the `night` pool's one-hour builds. Do not edit; a new bot is a new file.
"""Bot night, Track B: steps 1-3 (cheap bot, evaluator, profiler, equity table, ICM gate).
Standard library only. Everything expensive runs at import; the decision path is lookups and arithmetic."""
import random
from itertools import combinations, combinations_with_replacement

RANKS = {"2": 0, "3": 1, "4": 2, "5": 3, "6": 4, "7": 5, "8": 6, "9": 7, "10": 8, "T": 8, "J": 9, "Q": 10, "K": 11, "A": 12}
SUITS = {"c": 0, "d": 1, "h": 2, "s": 3}
RSTR = "23456789TJQKA"
PRIMES = (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41)
PAYOUTS = (10, 7, 5, 4, 3, 2, 1, 0)  # tonight's points by finishing position (rules s.5)
BOUNTY_RANK, BOUNTY_CHIPS = 5, 50  # rules s.4: win a showdown holding a Seven, the house adds 50 chips


def parse_card(s):  # "10d" -> 33 ; rank*4 + suit, deuce = 0, ace = 12
    return RANKS[s[:-1]] * 4 + SUITS[s[-1]]


def fmt_card(c):
    return RSTR[c >> 2] + "cdhs"[c & 3]


# ----------------------------------------------------------------------------- evaluator (built at import)
def _class5(ranks, flush):
    """Five ranks -> sortable (category, tiebreak...). Categories 0 high .. 8 straight flush."""
    cnt = {}
    for r in ranks:
        cnt[r] = cnt.get(r, 0) + 1
    groups = sorted(cnt.items(), key=lambda kv: (kv[1], kv[0]), reverse=True)
    shape = tuple(n for _, n in groups)
    order = tuple(r for r, _ in groups)
    distinct = sorted(cnt, reverse=True)
    straight = -1
    if len(distinct) == 5:
        if distinct[0] - distinct[4] == 4:
            straight = distinct[0]
        elif distinct == [12, 3, 2, 1, 0]:
            straight = 3
    if flush:
        return (8, straight) if straight >= 0 else (5,) + tuple(distinct)
    if shape[0] == 4:
        return (7,) + order
    if shape == (3, 2):
        return (6,) + order
    if straight >= 0:
        return (4, straight)
    if shape[0] == 3:
        return (3,) + order
    if shape[:2] == (2, 2):
        return (2,) + order
    if shape[0] == 2:
        return (1,) + order
    return (0,) + tuple(distinct)


def _build():
    classes = []
    for rs in combinations_with_replacement(range(13), 5):
        if all(rs.count(r) <= 4 for r in set(rs)):
            classes.append((_class5(rs, False), 0, rs))
    for rs in combinations(range(13), 5):
        classes.append((_class5(rs, True), 1, rs))
    classes.sort()
    assert len(classes) == 7462, len(classes)
    nf, fl, cat_min = {}, {}, [1] * 9
    for strength, (cls, is_flush, rs) in enumerate(classes, 1):
        if strength == 1 or cls[0] != classes[strength - 2][0][0]:
            cat_min[cls[0]] = strength
        if is_flush:
            m = 0
            for r in rs:
                m |= 1 << r
            fl[m] = strength
        else:
            p = 1
            for r in rs:
                p *= PRIMES[r]
            nf[p] = strength
    for n in (6, 7):
        for rs in combinations_with_replacement(range(13), n):
            if any(rs.count(r) > 4 for r in set(rs)):
                continue
            p = 1
            for r in rs:
                p *= PRIMES[r]
            best = 0
            for drop in set(combinations(rs, n - 5)):
                q = p
                for r in drop:
                    q //= PRIMES[r]
                v = nf[q]
                if v > best:
                    best = v
            nf[p] = best
        for bits in combinations(range(13), n):
            m = 0
            for r in bits:
                m |= 1 << r
            best = 0
            for sub in combinations(bits, 5):
                sm = 0
                for r in sub:
                    sm |= 1 << r
                v = fl[sm]
                if v > best:
                    best = v
            fl[m] = best
    return nf, fl, cat_min


NF, FL, CAT_MIN = _build()  # strength 1..7462; CAT_MIN[c] = first strength of category c


def evaluate(cards):
    """Best five-card strength of 5..7 cards (ints). One suit count, one product, one dict lookup."""
    sc = [0, 0, 0, 0]
    sm = [0, 0, 0, 0]
    p = 1
    for c in cards:
        s = c & 3
        r = c >> 2
        sc[s] += 1
        sm[s] |= 1 << r
        p *= PRIMES[r]
    for s in range(4):
        if sc[s] >= 5:
            return FL[sm[s]]
    return NF[p]


def category(strength):
    c = 8
    while CAT_MIN[c] > strength:
        c -= 1
    return c


# ----------------------------------------------------------------------------- preflop classes and equity (step 3)
def hand_class(hole):  # (high rank, low rank, suited)
    a, b = sorted((c >> 2 for c in hole), reverse=True)
    return a, b, (hole[0] & 3) == (hole[1] & 3)


def _mc(n_opp, samples, rng):
    """Monte Carlo equity of each of the 169 classes versus n_opp random hands; ties split."""
    eq = {}
    need = 5 + 2 * n_opp
    for a in range(13):
        for b in range(a + 1):
            for s in (False, True):
                if a == b and s:
                    continue
                hero = [a * 4, b * 4 + (0 if s else 1)]
                deck = [c for c in range(52) if c not in hero]
                tot = 0.0
                for _ in range(samples):
                    d = rng.sample(deck, need)
                    board = d[:5]
                    hs = evaluate(hero + board)
                    best, ties = 0, 0
                    for i in range(5, need, 2):
                        o = evaluate(d[i:i + 2] + board)
                        if o > best:
                            best, ties = o, 1
                        elif o == best:
                            ties += 1
                    if hs > best:
                        tot += 1.0
                    elif hs == best:
                        tot += 1.0 / (ties + 1)
                eq[(a, b, s)] = tot / samples
    return eq


def _pct(eq):
    """Combo-weighted percentile of each class by equity: best class ~0.005, worst 1.0 (lower is better)."""
    pct, cum = {}, 0.0
    for k in sorted(eq, key=lambda k: -eq[k]):
        a, b, s = k
        cum += (6 if a == b else 4 if s else 12) / 1326.0
        pct[k] = cum
    return pct


_RNG = random.Random(2026)
EQ1 = _mc(1, 2000, _RNG)  # spec says 400 and "cut if slower than 5 s"; 400 ranked JJ over QQ, 2000 fits in ~3 s
EQ3 = _mc(3, 2000, _RNG)
PCT = _pct(EQ1)


# ----------------------------------------------------------------------------- ICM (Malmuth-Harville)
def icm_hero(hero, others, payouts):
    """Hero's expected points: hero stack, the other live stacks, payouts for the n live positions."""
    m = len(others)
    if hero <= 0:
        return float(payouts[m]) if m < len(payouts) else 0.0
    T = hero + sum(others)
    size = 1 << m
    ssum = [0] * size
    pc = [0] * size
    p = [0.0] * size
    p[0] = 1.0
    for mask in range(1, size):
        low = mask & -mask
        prev = mask ^ low
        ssum[mask] = ssum[prev] + others[low.bit_length() - 1]
        pc[mask] = pc[prev] + 1
    for mask in range(1, size):
        acc = 0.0
        rest = mask
        while rest:
            low = rest & -rest
            rest ^= low
            prev = mask ^ low
            acc += p[prev] * others[low.bit_length() - 1] / (T - ssum[prev])
        p[mask] = acc
    v = 0.0
    for mask in range(size):
        v += p[mask] * hero / (T - ssum[mask]) * payouts[pc[mask]]
    return v


# ----------------------------------------------------------------------------- step-1 hand lists still used
def three_bet(h):  # QQ+ and AK
    a, b, s = h
    return (a == b and a >= 10) or (a == 12 and b == 11)


def premium(h):  # 99+, AK, AQ, AJs, KQs
    a, b, s = h
    return (a == b and a >= 7) or (a == 12 and b >= 10) or (s and ((a == 12 and b == 9) or (a == 11 and b == 10)))


def outs(cards):  # flush draw 9, open-ended straight draw 8 (flop/turn only)
    suits = [0] * 4
    mask = 0
    for c in cards:
        suits[c & 3] += 1
        mask |= 1 << (c >> 2)
    n = 9 if 4 in suits else 0
    if any((mask >> i) & 15 == 15 for i in range(1, 9)):
        n += 8
    return n


def hand_grade(hole, board):
    """0 nothing, 1 top pair (or overpair), 2 top pair good kicker (T+), 3 two pair or better."""
    cat = category(evaluate(hole + board))
    if cat >= 2:
        return 3
    top = max(c >> 2 for c in board)
    r0, r1 = hole[0] >> 2, hole[1] >> 2
    if cat == 1 and r0 == r1 and r0 > top:
        return 3  # overpair plays as a strong made hand
    if cat == 1 and (r0 == top or r1 == top):
        return 2 if min(r0, r1) >= 8 or r0 == r1 else 1
    return 0


# ----------------------------------------------------------------------------- profiler (step 2)
class Profile:
    """Per-seat counters; Beta prior of 2 pseudo-observations at the population rate."""
    __slots__ = ("vpip", "pfr", "ftb", "shove", "acts", "raises", "faced", "faced_fold", "free_check")

    def __init__(self):
        self.vpip, self.pfr, self.ftb, self.shove = [0.6, 2.0], [0.3, 2.0], [1.0, 2.0], [0.1, 2.0]
        self.acts = self.raises = self.faced = self.faced_fold = self.free_check = 0

    def see(self, action, preflop, all_in):
        self.acts += 1
        kind = action[:5]
        if kind == "RAISE":
            self.raises += 1
            self.shove[0] += all_in
        self.shove[1] += 1
        if kind == "CHECK":
            self.free_check += 1
        elif kind == "FOLD" or kind == "CALL":
            self.faced += 1
            self.ftb[1] += 1
            if kind == "FOLD":
                self.faced_fold += 1
                self.ftb[0] += 1
        if preflop:
            self.vpip[1] += 1
            self.pfr[1] += 1
            if kind == "CALL" or kind == "RAISE":
                self.vpip[0] += 1
            if kind == "RAISE":
                self.pfr[0] += 1

    def flag(self):
        if self.faced >= 5 and self.faced_fold == self.faced and self.free_check and not self.raises:
            return "dead"
        if self.ftb[1] >= 12 and self.ftb[0] / self.ftb[1] < 0.15:
            return "station"
        if self.acts >= 10 and self.raises / self.acts > 0.5:
            return "maniac"
        if self.vpip[1] >= 22 and self.vpip[0] / self.vpip[1] < 0.12:
            return "nit"
        return ""


# ----------------------------------------------------------------------------- the agent
class Agent:
    def new_game(self, my_index, n_players, starting_stack):
        self.me = my_index
        self.prof = [Profile() for _ in range(max(n_players, 10))]
        self.shoves = [0] * max(n_players, 10)
        self.hand_no, self.seen = -1, 0
        self.v_fold = None

    def hand_over(self, hand_number, chip_change):
        pass

    def act(self, st):
        try:
            return self.decide(st)
        except Exception:
            return "CHECK" if "CHECK" in st.legal_moves else "FOLD"

    def observe(self, st):
        P = st.players
        if st.hand_number != self.hand_no:
            self.hand_no, self.seen = st.hand_number, 0
            self.hand_start(st)
        pre = st.street == "preflop"
        for i, a in st.action_log[self.seen:]:
            if i == self.me:
                continue
            all_in = a.startswith("RAISE") and P[i].stack == 0
            self.shoves[i] += all_in
            self.prof[i].see(a, pre, all_in)
        self.seen = len(st.action_log)

    def hand_start(self, st):
        """Once per hand: ICM value of folding, from the stacks as this hand started."""
        P, me = st.players, self.me
        self.stacks = {i: p.stack + p.bet for i, p in enumerate(P) if p.stack + p.bet > 0}
        self.pay = PAYOUTS[:len(self.stacks)]
        others = [v for i, v in self.stacks.items() if i != me]
        self.v_fold = icm_hero(self.stacks.get(me, 0), others, self.pay)

    def icm_gain(self, opp, amt, dead, eq):
        """eq-weighted ICM value of winning/losing `amt` against `opp` (plus `dead` chips when winning) minus fold."""
        me = self.me
        hero, o = self.stacks.get(me, 0), self.stacks.get(opp, 0)
        amt = min(amt, hero, o)
        if amt <= 0:
            return 0.0
        pay = self.pay

        def val(h, ov):
            return icm_hero(h, [ov if i == opp else v for i, v in self.stacks.items() if i != me], pay)

        return eq * val(hero + amt + dead, o - amt) + (1 - eq) * val(hero - amt, o + amt) - self.v_fold

    def decide(self, st):
        legal = st.legal_moves
        bb, me, btn, P = st.big_blind, st.my_index, st.dealer_index, st.players
        self.observe(st)
        hole = [parse_card(c) for c in st.hand]
        h = hand_class(hole)
        pct = PCT[h]
        bounty = BOUNTY_CHIPS if BOUNTY_RANK in (hole[0] >> 2, hole[1] >> 2) else 0  # paid only at showdown
        step = 0.01 if bounty and bb <= BOUNTY_CHIPS else 0.0  # chase at most one rank step, and only while 50 chips >= 1 bb
        to_call = min(st.current_bet - st.my_bet, st.my_stack)
        my_total = st.my_stack + st.my_bet
        live = [i for i, p in enumerate(P) if i != me and not p.folded]
        others = [P[i].stack + P[i].bet for i in live]
        eff_bb = min(my_total, max(others) if others else my_total) / bb
        flags = {i: self.prof[i].flag() for i in live}
        aggressor, n_raises = -1, 0
        for i, a in st.action_log:
            if a.startswith("RAISE") and i != me:
                aggressor, n_raises = i, n_raises + 1
        agg_flag = flags.get(aggressor, "")

        def raise_to(total):
            if "RAISE" not in legal:
                return "CALL" if "CALL" in legal else "CHECK" if "CHECK" in legal else "FOLD"
            return "RAISE:%d" % max(st.min_raise, min(st.max_raise, int(total)))

        def call():
            return "CALL" if "CALL" in legal else check_or_fold

        check_or_fold = "CHECK" if "CHECK" in legal else "FOLD"
        n = len(P)
        if st.street == "preflop":
            raised = st.current_bet > bb
            dealt = [i for i, p in enumerate(P) if p.stack > 0 or p.bet > 0 or not p.folded]
            k, s = 0, me
            while s != btn:  # dealt seats between me and the button, going forward
                s = (s + 1) % n
                k += s in dealt
            nd = len(dealt)
            is_sb, is_bb = k == nd - 1 and nd > 2, k == nd - 2 or (nd == 2 and k == 1)
            pos = 2 if k <= 1 else 1 if k <= 3 or is_sb else 0  # 2 button/cutoff, 1 middle, 0 early
            bettors = [i for i in live if P[i].bet == st.current_bet]
            shove = raised and (to_call >= st.my_stack or st.current_bet >= 10 * bb
                                or any(P[i].all_in for i in bettors))
            dead_money = st.pot_size - st.my_bet - sum(P[i].bet for i in bettors[:1]) + bounty  # an all-in goes to showdown
            if shove:  # all-in decision: percentile threshold, then the ICM gate
                wide = any(P[i].stack + P[i].bet < 12 * bb or self.shoves[i] >= 3 for i in bettors) or agg_flag == "maniac"
                if pct > (0.20 if wide else 0.12) + step:
                    return check_or_fold
                callers = [i for i in live if P[i].bet > bb]
                eq = (EQ3 if len(callers) >= 2 else EQ1)[h]
                return call() if self.icm_gain(bettors[0] if bettors else live[0], to_call, dead_money, eq) > 0 else check_or_fold
            if eff_bb < 12:
                if raised:
                    if agg_flag == "nit" and not three_bet(h):
                        return check_or_fold
                    if pct <= 0.12 + step and self.icm_gain(aggressor, st.my_stack, dead_money, EQ1[h]) > 0:
                        return raise_to(st.max_raise)
                    return check_or_fold
                thr = (0.60 if eff_bb < 5 else 0.40 if eff_bb < 8 else (0.25, 0.35, 0.45)[pos]) + step
                if pct <= thr:
                    return raise_to(st.max_raise)
                if live and all(flags[i] == "dead" for i in live):
                    return raise_to(st.max_raise)  # exploit: dead seats fold to any bet
                return check_or_fold
            if not raised:
                thr = ((0.15, 0.25, 0.40)[pos] if not is_bb else 0.15) + step
                if pct <= thr:
                    return raise_to(2.5 * bb)
                if live and all(flags[i] == "dead" for i in live):
                    return raise_to(st.max_raise)
                if pos == 2 and live and all(flags[i] == "nit" for i in live):
                    return raise_to(2.5 * bb)  # exploit: steal nits' blinds with any two
                return check_or_fold
            if agg_flag == "nit":
                return raise_to(3 * st.current_bet) if three_bet(h) else check_or_fold
            if three_bet(h):
                return raise_to(3 * st.current_bet)
            if is_bb and n_raises == 1 and pct <= 0.35 + step:
                return call()  # defend the big blind versus one raise
            return call() if premium(h) else check_or_fold
        board = [parse_card(c) for c in st.community]
        pot = st.pot_size - sum(p.bet for p in P)
        grade = hand_grade(hole, board)
        river = st.street == "river"
        if to_call == 0:
            if live and all(flags[i] == "dead" for i in live):
                return raise_to(0.6 * pot)  # exploit: always bet when a dead seat checks to us
            if any(flags[i] == "station" for i in live):
                if grade >= 2 or (river and grade >= 1):
                    return raise_to(0.75 * pot)  # exploit: bigger value bets, medium hands wait
                return check_or_fold
            return raise_to(0.6 * pot) if grade >= 1 and "RAISE" in legal else check_or_fold
        if grade >= 1 or (not river and outs(hole + board) >= 8 and to_call * 3 < st.pot_size + bounty):
            return call()
        return "FOLD"
