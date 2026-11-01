# Origin: the night field's persona builds (docs/drills/field/agent_default.md is the builder's log). A coding agent,
# told only what a two-person team of casual players would tell it ("build us the strongest bot you can"), built it in
# one hour from T0 against the red-team brief and kit, with no access to this repository; frozen at md5
# cd47da88b88071e7e1e7665aea06db41 (its FROZEN.md5, minute 45) and copied here unchanged apart from this header. The
# archived original is docs/drills/field/agent_default_bot.py. It is played through hyperion.sim.bestiary.AgentDefaultBot
# (registry name `agent_default`), one of the `night` pool's one-hour builds. Do not edit; a new bot is a new file.
"""Rule-based tight-aggressive NLHE bot: Chen-formula preflop, made-hand + draw classification postflop,
pot-odds calling, short-stack push/fold, light opponent tracking. Pure stdlib."""
import random
from kit import Agent

# ---------------------------------------------------------------- hand evaluation
STRAIGHT = [-1] * 8192          # mask of ranks -> high rank of best straight (or -1)
for _m in range(8192):
    _x = (_m << 1) | (_m >> 12)
    for _h in range(13, 3, -1):
        if (_x >> (_h - 4)) & 31 == 31:
            STRAIGHT[_m] = _h - 1
            break


def evaluate(cards):
    """Score of best 5-card hand among given cards (any count). Higher is better."""
    rc = [0] * 13
    sm = [0, 0, 0, 0]
    sc = [0, 0, 0, 0]
    for c in cards:
        r = c >> 2
        s = c & 3
        rc[r] += 1
        sm[s] |= 1 << r
        sc[s] += 1
    for s in range(4):
        if sc[s] >= 5:
            m = sm[s]
            sh = STRAIGHT[m]
            if sh >= 0:
                return (8 << 20) | (sh << 16)
            sc_ = 0
            k = 0
            for r in range(12, -1, -1):
                if m >> r & 1:
                    sc_ = (sc_ << 4) | r
                    k += 1
                    if k == 5:
                        break
            return (5 << 20) | sc_
    quads = []
    trips = []
    pairs = []
    singles = []
    mask = 0
    for r in range(12, -1, -1):
        n = rc[r]
        if n:
            mask |= 1 << r
            if n == 4:
                quads.append(r)
            elif n == 3:
                trips.append(r)
            elif n == 2:
                pairs.append(r)
            else:
                singles.append(r)
    if quads:
        q = quads[0]
        rest = [x for x in (trips + pairs + singles)]
        k = max(rest) if rest else 0
        return (7 << 20) | (q << 16) | (k << 12)
    if trips and (len(trips) > 1 or pairs):
        t = trips[0]
        p = trips[1] if len(trips) > 1 else pairs[0]
        if len(trips) > 1 and pairs and pairs[0] > p:
            p = pairs[0]
        return (6 << 20) | (t << 16) | (p << 12)
    sh = STRAIGHT[mask]
    if sh >= 0:
        return (4 << 20) | (sh << 16)
    if trips:
        ks = sorted(pairs + singles, reverse=True)[:2]
        v = (3 << 20) | (trips[0] << 16)
        sft = 12
        for k in ks:
            v |= k << sft
            sft -= 4
        return v
    if len(pairs) >= 2:
        rest = pairs[2:] + singles
        k = max(rest) if rest else 0
        return (2 << 20) | (pairs[0] << 16) | (pairs[1] << 12) | (k << 8)
    if pairs:
        ks = singles[:3]
        v = (1 << 20) | (pairs[0] << 16)
        sft = 12
        for k in ks:
            v |= k << sft
            sft -= 4
        return v
    v = 0
    for k in singles[:5]:
        v = (v << 4) | k
    return v


# ---------------------------------------------------------------- preflop strength (Chen formula)
def chen(c1, c2):
    r1, r2 = c1 >> 2, c2 >> 2
    s = (c1 & 3) == (c2 & 3)
    if r1 < r2:
        r1, r2 = r2, r1

    def pv(r):
        if r == 12: return 10.0
        if r == 11: return 8.0
        if r == 10: return 7.0
        if r == 9: return 6.0
        return (r + 2) / 2.0
    sc = pv(r1)
    if r1 == r2:
        sc = max(5.0, sc * 2)
        return sc
    if s:
        sc += 2
    gap = r1 - r2 - 1
    if gap == 1: sc -= 1
    elif gap == 2: sc -= 2
    elif gap == 3: sc -= 4
    elif gap >= 4: sc -= 5
    if gap <= 1 and r1 < 10:
        sc += 1
    return sc


def eq_from_chen(sc):
    """Rough equity vs ONE random hand (fit to the known table: 72o .35, 22 .50, AKo .65, AA .85)."""
    return 0.34 + 0.027 * max(0.0, sc)


def _num(x, d=0):
    try:
        return int(x)
    except Exception:
        return d


class Bot(Agent):
    def __init__(self):
        self.rng = random.Random(12345)
        self.new_table(None, None, None)

    # ------------------------------------------------------------ lifecycle
    def new_table(self, rules, seat, n_players):
        self.rng = random.Random(777)
        self.cur_hand = -1
        self.hist_n = 0
        self.pf_aggr = False       # I was the last preflop raiser
        self.pf_raiser = -1
        self.stats = {}            # seat -> [hands, vpip, raises]
        self.hand_seen = {}        # seat -> [vpip, raise] this hand
        self.start_stack = 2000
        try:
            if rules and rules.get('starting_stack'):
                self.start_stack = int(rules['starting_stack'])
        except Exception:
            pass

    def hand_end(self, result):
        self._flush_hand()

    def _flush_hand(self):
        for s, (v, r, na) in self.hand_seen.items():
            st = self.stats.setdefault(s, [0, 0, 0, 0])
            st[0] += 1
            st[1] += v
            st[2] += r
            st[3] += na
        self.hand_seen = {}

    def _new_hand(self, hn):
        self._flush_hand()
        self.cur_hand = hn
        self.hist_n = 0
        self.pf_aggr = False
        self.pf_raiser = -1

    def _scan_history(self, obs, me):
        hist = obs.history
        if not hist:
            return
        n = len(hist)
        if n < self.hist_n:
            self.hist_n = 0
        for i in range(self.hist_n, n):
            try:
                s, a = hist[i]
                k = a[0]
                if k == 'raise' and i < 2 and a[1] <= obs.blinds[1]:
                    continue          # blind post logged as a raise
            except Exception:
                continue
            if s != me:
                h = self.hand_seen.setdefault(s, [0, 0, 0])
                if k == 'raise':
                    h[2] += 1
                if obs.street == 0:
                    if k == 'call':
                        h[0] = 1
                    elif k == 'raise':
                        h[0] = 1
                        h[1] = 1
        self.hist_n = n

    def _aggr(self, s):
        """+1 loose-aggressive, -1 passive/tight, 0 unknown/normal (raises per hand, all streets)"""
        st = self.stats.get(s)
        if not st or st[0] < 15:
            return 0
        r = st[3] / st[0]
        if r > 0.75: return 1
        if r < 0.10: return -1
        return 0

    def _station(self, s):
        st = self.stats.get(s)
        if not st or st[0] < 12:
            return False
        return st[1] / float(st[0]) > 0.55 and st[2] / float(st[0]) < 0.12

    def _range_factor(self, s, to_call_bb=0.0):
        """Multiplier turning equity-vs-random into equity-vs-this-seat's-raising-range."""
        st = self.stats.get(s) if s >= 0 else None
        if st and st[0] >= 10:
            w = st[2] / float(st[0])
        elif to_call_bb >= 40:
            w = 0.07
        elif to_call_bb >= 15:
            w = 0.15
        else:
            w = 0.30
        w = max(0.04, min(0.5, w))
        return 0.62 + 0.38 * (w / 0.5) ** 0.7

    def _loose_raiser(self, s):
        st = self.stats.get(s)
        if not st or st[0] < 12:
            return 0
        rr = st[2] / st[0]
        if rr > 0.22: return 1
        if rr < 0.07: return -1
        return 0

    # ------------------------------------------------------------ main entry
    def act(self, obs):
        try:
            a = self._act(obs)
        except Exception:
            a = None
        return self._safe(obs, a)

    def _safe(self, obs, a):
        try:
            legal = set(obs.legal or ())
        except Exception:
            legal = set()
        try:
            kind, amt = a
        except Exception:
            kind, amt = None, 0
        if kind == 'raise' and 'raise' in legal:
            try:
                lo = min(int(obs.min_raise), int(obs.max_raise))
                hi = max(int(obs.min_raise), int(obs.max_raise))
                amt = int(amt)
                amt = max(lo, min(hi, amt))
                return ('raise', amt)
            except Exception:
                kind = 'call'
        if kind == 'raise':
            kind = 'call'
        if kind == 'fold' and 'check' in legal:
            kind = 'check'
        if kind == 'call' and 'call' not in legal:
            kind = 'check'
        if kind == 'check' and 'check' not in legal:
            kind = 'fold' if 'fold' in legal else ('call' if 'call' in legal else None)
        if kind in ('fold', 'check', 'call') and kind in legal:
            return (kind, 0)
        if 'check' in legal: return ('check', 0)
        if 'fold' in legal: return ('fold', 0)
        if 'call' in legal: return ('call', 0)
        return ('check', 0)

    def _act(self, obs):
        legal = set(obs.legal or ())
        stacks = list(obs.stacks)
        n = len(stacks)
        me = obs.seat
        bets = list(obs.bets) if obs.bets is not None else [0] * n
        if len(bets) < n: bets += [0] * (n - len(bets))
        in_hand = list(obs.in_hand) if obs.in_hand is not None else [True] * n
        if len(in_hand) < n: in_hand += [True] * (n - len(in_hand))
        hn = obs.hand_no if obs.hand_no is not None else 1
        if hn != self.cur_hand:
            self._new_hand(hn)
        try:
            self._scan_history(obs, me)
        except Exception:
            pass
        sb, bb = obs.blinds if obs.blinds else (10, 20)
        bb = max(1, bb); sb = max(1, sb)
        hole = tuple(obs.hole)
        board = tuple(obs.board or ())
        to_call = obs.to_call or 0
        my_stack = stacks[me]
        pot = obs.pot or 0
        total_pot = pot + sum(bets)
        lo = min(obs.min_raise, obs.max_raise)
        hi = max(obs.min_raise, obs.max_raise)
        can_raise = 'raise' in legal
        opps = [i for i in range(n) if i != me and in_hand[i]]
        n_opp = len(opps)
        live_opp = [i for i in opps if stacks[i] > 0]
        # effective stack: vs the biggest stack still in the hand
        big = max([stacks[i] + bets[i] for i in opps] or [0])
        eff = min(my_stack + bets[me], big) if big else my_stack + bets[me]
        eff_bb = eff / bb

        def raise_to(x):
            x = int(x)
            if x >= 0.5 * (my_stack + bets[me]):
                return ('raise', hi)
            return ('raise', max(lo, min(hi, x)))

        if obs.street == 0:
            return self._preflop(obs, locals_=dict(
                legal=legal, stacks=stacks, n=n, me=me, bets=bets, in_hand=in_hand, sb=sb, bb=bb, hole=hole,
                to_call=to_call, my_stack=my_stack, total_pot=total_pot, lo=lo, hi=hi, can_raise=can_raise,
                opps=opps, n_opp=n_opp, eff_bb=eff_bb, raise_to=raise_to))
        return self._postflop(obs, locals_=dict(
            legal=legal, stacks=stacks, n=n, me=me, bets=bets, in_hand=in_hand, sb=sb, bb=bb, hole=hole, board=board,
            to_call=to_call, my_stack=my_stack, total_pot=total_pot, lo=lo, hi=hi, can_raise=can_raise,
            opps=opps, n_opp=n_opp, eff_bb=eff_bb, raise_to=raise_to))

    # ------------------------------------------------------------ preflop
    def _preflop(self, obs, locals_):
        L = locals_
        legal = L['legal']; stacks = L['stacks']; n = L['n']; me = L['me']; bets = L['bets']
        in_hand = L['in_hand']; bb = L['bb']; hole = L['hole']; to_call = L['to_call']
        can_raise = L['can_raise']; eff_bb = L['eff_bb']; raise_to = L['raise_to']; hi = L['hi']
        total_pot = L['total_pot']; my_stack = L['my_stack']
        score = chen(hole[0], hole[1])
        r1, r2 = sorted((hole[0] >> 2, hole[1] >> 2), reverse=True)
        pair = r1 == r2
        premium = (pair and r1 >= 10) or (r1 == 12 and r2 == 11)
        maxbet = max(bets)
        raised = maxbet > bb
        # count raises this hand preflop and find last raiser from history
        nraise = 0
        last_raiser = -1
        cur = bb
        try:
            for s, a in (obs.history or ()):
                if a[0] == 'raise' and a[1] > cur:     # ignores blind posts if they are logged as raises
                    nraise += 1
                    last_raiser = s
                    cur = a[1]
        except Exception:
            pass
        if raised and nraise == 0:
            nraise = 1
        # position: live players yet to act after me
        order = [(me + k) % n for k in range(1, n)]
        active = [i for i in range(n) if in_hand[i] or stacks[i] > 0]
        btn = obs.button if obs.button is not None else 0
        # blind seats among active
        after_btn = [(btn + k) % n for k in range(1, n + 1)]
        act_after = [i for i in after_btn if i in active]
        if len(act_after) >= 3:
            sbseat, bbseat = act_after[0], act_after[1]
        elif len(act_after) == 2:
            sbseat, bbseat = btn, act_after[0]   # heads-up: button posts the small blind
        else:
            sbseat = bbseat = me
        # players yet to act (first-in decision): seats after me up to and including BB
        behind = 0
        # simple: seats between me and BB inclusive
        d_bb = (bbseat - me) % n
        for j in range(1, d_bb + 1):
            s = (me + j) % n
            if in_hand[s] and stacks[s] > 0:
                behind += 1
        if me == bbseat:
            behind = 0
        if len(act_after) == 2 and me == btn:
            behind = 1
        limpers = 0
        for i in range(n):
            if i != me and in_hand[i] and bets[i] >= bb and not raised and i != bbseat:
                limpers += 1
        ip_vs_raiser = False
        raiser_late = False
        loose = 0
        if last_raiser >= 0:
            loose = self._loose_raiser(last_raiser)
            d_r = (btn - last_raiser) % n   # 0 = button
            raiser_late = d_r <= 1
            ip_vs_raiser = ((me - btn) % n) < ((last_raiser - btn) % n) if me != btn else True
        pot_odds = to_call / float(total_pot + to_call) if (total_pot + to_call) > 0 else 0.0
        self.pf_raiser = last_raiser

        # ------------- not facing a raise
        if not raised:
            if to_call == 0 and not can_raise:
                return ('check', 0)
            # short-stack push/fold
            if eff_bb <= 10:
                thr = 2.0 + 0.5 * (eff_bb - 2) + 0.2 * (behind - 2)
                thr = max(2.0, min(11.0, thr))
                if me == bbseat:
                    thr = 99   # BB: take the free check, nothing to steal
                if score >= thr and can_raise:
                    self.pf_aggr = True
                    return ('raise', hi)
                if 'check' in legal:
                    return ('check', 0)
                if me == bbseat:
                    return ('check', 0) if 'check' in legal else ('fold', 0)
                # SB completing for half a blind is cheap
                if to_call <= bb * 0.5 and score >= 4:
                    return ('call', 0)
                return ('fold', 0)
            thr = {0: 9.5, 1: 6.0, 2: 5.5, 3: 6.5, 4: 7.0, 5: 7.5, 6: 8.0}.get(behind, 8.5)
            thr += 0.4 * limpers
            if me == bbseat and limpers == 0:
                thr = 99
            if len(act_after) == 2 and me != bbseat:
                thr = 3.5            # heads-up: the button/small blind opens very wide
            if score >= thr and can_raise:
                size = (2.5 if behind <= 2 else 3.0) * bb + limpers * bb
                if eff_bb < 18:
                    size = 2.2 * bb + limpers * bb
                self.pf_aggr = True
                return raise_to(size)
            if 'check' in legal:
                return ('check', 0)
            # cheap limp-behind with speculative hands in position / small blind
            if limpers >= 1 and to_call <= bb and behind <= 3 and (pair or (score >= 5.5)) and eff_bb >= 18:
                return ('call', 0)
            if me == sbseat and to_call <= bb * 0.5 and score >= 4.5:
                return ('call', 0)
            return ('fold', 0)

        # ------------- facing a raise
        # all-in shove from someone: need equity
        cost = to_call
        if to_call >= my_stack:
            need = pot_odds + 0.03
            ee = eq_from_chen(score) * self._range_factor(last_raiser, to_call / float(bb))
            if ee >= need or premium:
                return ('call', 0)
            return ('fold', 0)
        stack_frac = to_call / float(my_stack + bets[me]) if (my_stack + bets[me]) > 0 else 1.0
        if nraise >= 2:
            # 3-bet or higher
            if premium and can_raise:
                self.pf_aggr = True
                return ('raise', hi) if (stack_frac > 0.2 or eff_bb < 40) else raise_to(maxbet * 2.4)
            if score >= 11.5 and stack_frac < 0.3:
                return ('call', 0)
            if score >= 9 and stack_frac < 0.1:
                return ('call', 0)
            return ('fold', 0)
        # facing a single raise
        raise_bb = maxbet / float(bb)
        if eff_bb <= 12:
            # shove or fold range vs open
            thr = 9.5 - (0.8 if raiser_late else 0) - 0.8 * (1 if loose > 0 else 0)
            if score >= thr or premium:
                return ('raise', hi) if can_raise else ('call', 0)
            if score >= thr - 2.0 and pot_odds < 0.3:
                return ('call', 0)
            return ('fold', 0)
        hu = len(act_after) == 2
        three_thr = 12.0 - (1.5 if hu else 0.0)
        if loose > 0: three_thr -= 1.0
        if loose < 0: three_thr += 1.5
        if score >= three_thr and can_raise:
            self.pf_aggr = True
            mult = 3.0 if ip_vs_raiser else 3.7
            return raise_to(maxbet * mult)
        # occasional 3-bet bluff with suited wheel aces / connectors vs late-position opens
        if can_raise and raiser_late and (hole[0] & 3) == (hole[1] & 3) and 6.0 <= score <= 9.5 \
                and self.rng.random() < 0.10 and eff_bb >= 25 and loose >= 0:
            self.pf_aggr = True
            return raise_to(maxbet * 3.4)
        call_thr = 9.0 + 0.4 * max(-1.5, raise_bb - 3.0)
        if raiser_late: call_thr -= 0.8
        if me == bbseat: call_thr -= 1.5
        if ip_vs_raiser: call_thr -= 0.4
        if loose > 0: call_thr -= 1.3
        if loose < 0: call_thr += 1.3
        if hu: call_thr -= 2.0
        if pair and eff_bb >= 25 and stack_frac < 0.12:
            call_thr = min(call_thr, 5.0)   # set mining
        if stack_frac > 0.35:
            call_thr += 1.5
        if score >= call_thr:
            return ('call', 0)
        # suited speculative hands defend the big blind against late-position opens when deep
        if me == bbseat and raiser_late and (hole[0] & 3) == (hole[1] & 3) and score >= 5.5 \
                and eff_bb >= 30 and stack_frac < 0.1 and nraise <= 1:
            return ('call', 0)
        return ('fold', 0)

    # ------------------------------------------------------------ postflop
    def _analyze(self, hole, board):
        """Return (eq_vs_random, cat, outs, made_strength_kind)."""
        score = evaluate(hole + board)
        cat = score >> 20
        bcat = evaluate(board) >> 20 if len(board) >= 3 else 0
        bscore = evaluate(board)
        hr = [hole[0] >> 2, hole[1] >> 2]
        br = sorted([c >> 2 for c in board], reverse=True)
        h_hi = max(hr)
        eq = 0.15
        if cat == 0:
            eq = 0.10 + 0.012 * h_hi + (0.03 if hr[0] != hr[1] and min(hr) >= br[0] else 0)
            if h_hi < br[0]:
                eq -= 0.04
        elif cat == 1:
            pr = (score >> 16) & 15
            if pr in hr:
                if hr[0] == hr[1]:
                    if pr > br[0]: eq = 0.72 + 0.01 * (pr - 8 if pr > 8 else 0)
                    elif pr > br[1]: eq = 0.52
                    else: eq = 0.42
                else:
                    kick = hr[0] if hr[1] == pr else hr[1]
                    if pr == br[0]:
                        eq = 0.60 + (0.08 if kick >= 10 else 0.04 if kick >= 8 else 0.0)
                        if pr >= 10: eq += 0.03
                    elif len(br) > 1 and pr == br[1]:
                        eq = 0.48 + (0.03 if kick >= 10 else 0)
                    else:
                        eq = 0.38
            else:
                # board pair only: my kicker matters
                eq = 0.25 + 0.012 * h_hi - (0.05 if h_hi < br[0] else 0)
        elif cat == 2:
            p1 = (score >> 16) & 15
            p2 = (score >> 12) & 15
            used = (1 if p1 in hr else 0) + (1 if p2 in hr else 0)
            if hr[0] == hr[1] and hr[0] in (p1, p2):
                used = 2
            if used == 2: eq = 0.84
            elif used == 1: eq = 0.62 if (p1 in hr or p2 in hr) and max(p1, p2) in hr else 0.55
            else: eq = 0.28
        elif cat == 3:
            tr = (score >> 16) & 15
            nused = (1 if hr[0] == tr else 0) + (1 if hr[1] == tr else 0)
            eq = 0.93 if nused == 2 else 0.86 if nused == 1 else 0.38
        elif cat == 4:
            eq = 0.35 if score == bscore else 0.90
        elif cat == 5:
            eq = 0.88 if score != bscore else 0.4
            # nut-ish flush bonus
            if (score >> 16) & 15 == 12: eq = 0.94
        elif cat == 6:
            eq = 0.96 if bcat < 6 else 0.8
        else:
            eq = 0.99
        if len(board) >= 5:
            if cat < 4 and score == bscore:
                eq = min(eq, 0.3)
            return eq, cat, 0
        # draws
        outs = 0.0
        sm = [0, 0, 0, 0]
        sn = [0, 0, 0, 0]
        for c in hole + board:
            sn[c & 3] += 1
        hs = [hole[0] & 3, hole[1] & 3]
        for s in range(4):
            if sn[s] == 4 and s in hs and cat < 5:
                outs += 9
                break
        # straight draws
        if cat < 4:
            m = 0
            bm = 0
            for c in hole:
                m |= 1 << (c >> 2)
            for c in board:
                bm |= 1 << (c >> 2)
            m |= bm
            so = 0
            for r in range(13):
                bit = 1 << r
                if m & bit:
                    continue
                sh = STRAIGHT[m | bit]
                if sh >= 0 and sh > STRAIGHT[bm | bit]:
                    so += 1
            outs += so * 4 if so < 3 else 8
        # overcards
        if cat == 0 and min(hr) > br[0] and hr[0] != hr[1]:
            outs += 4.5
        elif cat == 1 and outs == 0 and pr_is_pair_low(score, hr, br):
            outs += 2.0
        if outs:
            rate = 0.04 if len(board) == 3 else 0.021
            o = min(outs, 15)
            eq = eq + (1 - eq) * o * rate * (0.9 if len(board) == 3 else 1.0)
        return eq, cat, outs

    def _postflop(self, obs, locals_):
        L = locals_
        legal = L['legal']; stacks = L['stacks']; n = L['n']; me = L['me']; bets = L['bets']
        in_hand = L['in_hand']; bb = L['bb']; hole = L['hole']; board = L['board']
        to_call = L['to_call']; can_raise = L['can_raise']; raise_to = L['raise_to']; hi = L['hi']; lo = L['lo']
        total_pot = L['total_pot']; my_stack = L['my_stack']; n_opp = L['n_opp']; opps = L['opps']
        street = obs.street
        eq, cat, outs = self._analyze(hole, board)
        raw_eq = eq
        # multiway: need to beat everyone
        if n_opp >= 2:
            eq = eq ** (1 + 0.45 * (n_opp - 1)) if eq < 0.9 else eq - 0.03 * (n_opp - 1)
        btn = obs.button if obs.button is not None else 0
        # in position: I act last among live opponents (approx: no live opp after me in order from btn)
        order_me = (me - btn - 1) % n
        in_pos = all(((o - btn - 1) % n) < order_me for o in opps) if opps else True
        rng = self.rng.random
        pot = max(total_pot, 1)
        aggressor = self.pf_aggr
        # opponent bet this street?
        facing = to_call > 0
        eff_stack = my_stack

        def bet(frac):
            amt = (bets[me] + max(to_call, 0)) + frac * pot
            return raise_to(max(lo, amt)) if can_raise else ('check', 0)

        # ---------------- not facing a bet
        if not facing:
            if not can_raise:
                return ('check', 0)
            if opps and all(self._station(o_) for o_ in opps):
                # calling stations never fold: value bet wider, never bluff
                if eq >= 0.5 and rng() < 0.75:
                    return bet(0.6 if eq < 0.8 else 0.75)
                if outs >= 8 and street < 3 and rng() < 0.3:
                    return bet(0.5)
                return ('check', 0)
            if eq >= 0.80:
                if street < 3 and n_opp == 1 and rng() < 0.12:
                    return ('check', 0)       # occasional slowplay
                return bet(0.70)
            if eq >= 0.64:
                p = 0.85 if n_opp == 1 else 0.6
                if rng() < p:
                    return bet(0.55)
                return ('check', 0)
            if outs >= 8 and street < 3:
                if rng() < (0.55 if in_pos or n_opp == 1 else 0.35):
                    return bet(0.6)
                return ('check', 0)
            if street == 1 and aggressor and n_opp <= 2 and rng() < (0.62 if n_opp == 1 else 0.35):
                return bet(0.5)
            if street == 2 and aggressor and n_opp == 1 and eq > 0.3 and rng() < 0.3:
                return bet(0.6)
            if street == 3 and n_opp == 1 and eq < 0.35 and rng() < 0.10:
                return bet(0.65)
            if in_pos and n_opp == 1 and street in (1, 2) and eq > 0.2 and rng() < 0.28:
                return bet(0.5)          # check-through: take the pot
            if eq >= 0.5 and street == 3 and n_opp == 1 and rng() < 0.35:
                return bet(0.4)
            return ('check', 0)

        # ---------------- facing a bet
        pot_before = max(total_pot - to_call, 1)
        frac = to_call / float(pot_before)
        odds = to_call / float(total_pot + to_call) if (total_pot + to_call) > 0 else 0.0
        adj = eq
        bettor = -1
        bm = 0
        for o_ in opps:
            if bets[o_] > bm:
                bm = bets[o_]; bettor = o_
        ag = self._aggr(bettor) if bettor >= 0 else 0
        if ag > 0: adj += 0.07
        elif ag < 0: adj -= 0.05
        if frac > 0.4:
            adj -= min(0.22, 0.13 * frac)
        # count raises on this street: more than one bet-sized raise from them is strong
        maxbet = max(bets)
        stack_frac = to_call / float(my_stack + bets[me]) if (my_stack + bets[me]) > 0 else 1.0
        if stack_frac > 0.4 and cat <= 1:
            adj -= 0.10
        if bets[me] > 0 and cat <= 1:
            adj -= 0.08       # they raised my bet: range is strong
        if street == 3:
            adj -= 0.02
        if cat <= 3 and frac >= 0.45:
            adj -= 0.035 * board_danger(board)
        # re-raise value
        if adj >= 0.85 and can_raise and rng() < 0.85:
            return raise_to(maxbet * 2.6 + 0.2 * pot)
        # draws: allow implied odds
        if outs >= 8 and street < 3 and can_raise and n_opp == 1 and frac < 0.8 and rng() < 0.12 \
                and my_stack > 3 * to_call:
            return raise_to(maxbet * 2.5 + 0.3 * pot)
        if to_call <= 0.06 * pot_before and raw_eq > 0.22:
            return ('call', 0)
        margin = 0.05 if street < 3 else 0.04
        if adj >= odds + margin:
            return ('call', 0)
        if outs >= 8 and street < 3 and raw_eq >= odds * 1.0 + 0.0 and stack_frac < 0.35:
            return ('call', 0)
        return ('fold', 0)


def pr_is_pair_low(score, hr, br):
    return False


def board_danger(board):
    """0 dry, 1 two-tone or connected, 2 flush-ish and connected / monotone."""
    sn = [0, 0, 0, 0]
    m = 0
    for c in board:
        sn[c & 3] += 1
        m |= 1 << (c >> 2)
    d = 0
    if max(sn) >= 3:
        d += 1
    if max(sn) >= 4:
        d += 1
    # connectedness: any 4-rank window containing 3 board ranks
    x = (m << 1) | (m >> 12)
    for lowbit in range(0, 10):
        if bin((x >> lowbit) & 31).count('1') >= 3:
            d += 1
            break
    return d
