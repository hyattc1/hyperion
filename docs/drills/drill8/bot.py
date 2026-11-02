"""Ghost Hold'em entry: class Agent around hyperion.ship.make_bot() behind the adapter."""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from hyperion.core.types import Rules  # noqa: E402
from hyperion.ship import make_bot  # noqa: E402

from adapter import history as _hist  # adapter.py beside bot.py  # noqa: E402
from adapter import make_adapter  # noqa: E402


def _rules() -> Rules:
    for p in (os.path.join(_HERE, "rules_tonight.json"), os.path.join(_HERE, "submission", "rules_tonight.json")):
        try:
            with open(p) as f:
                d = json.load(f)
            d = {k: (tuple(tuple(x) if isinstance(x, list) else x for x in v) if isinstance(v, list) else v)
                 for k, v in d.items()}
            return Rules(**d)
        except Exception:  # noqa: BLE001
            continue
    return Rules()


RULES = _rules()

# warm everything at import: one throwaway adapter started for a table
try:
    _warm = make_adapter(make_bot(), RULES)
    _warm.start(0, 8, RULES)
except Exception:  # noqa: BLE001
    _warm = None


class Agent:
    """hand_over only stores the result (the kit fails a submission on any hand_over over 1 ms, and this box's load
    spikes past that); the stored hand ends go to the bot at the top of the next act or new_table."""

    def __init__(self):
        bot = make_bot()
        try:
            bot.defer_hand_end(True)  # hand_end leaves the ICM curves and dials to idle() / the next decision
        except Exception:  # noqa: BLE001
            pass
        self.bot = bot
        self.ad = make_adapter(bot, RULES)
        self.pending = []

    def _flush(self):
        pend, self.pending = self.pending, []
        for r in pend:
            try:
                self.ad.hand_end(int(r.hand_no), int(r.delta[0]), 8, history=_hist(r.log), deltas=list(r.delta),
                                 showdown=dict(r.shown or {}), board=tuple(r.board or ()))
            except Exception:  # noqa: BLE001
                pass

    def new_table(self, t):
        try:
            self._flush()
            self.ad.start(0, 8, RULES)
            self.bot.idle()
        except Exception:  # noqa: BLE001
            pass

    def act(self, s):
        try:
            if self.pending:
                self._flush()
            n = self.ad.decide(s)
            return int(n) if isinstance(n, int) and not isinstance(n, bool) else 0
        except Exception:  # noqa: BLE001
            return 0

    def hand_over(self, r):
        try:
            if r.table_over or r.place:
                self.pending = []  # nothing more to play at this table
            else:
                self.pending.append(r)
        except Exception:  # noqa: BLE001
            pass
