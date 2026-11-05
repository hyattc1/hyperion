"""A kit B entry with a stopwatch on every segment of the timed call (G1's profile; docs/drills/climb/g1-log.md). Copy it beside
hyperion/ in an unpacked zip and run: PROF_OUT=x.jsonl python tools/gate.py <dir> --kit b --entry g1_profile_entry.py
--baseline package --max-tmo-pct 100 [--slow K]; then python docs/drills/climb/g1_profile_summary.py x.jsonl. Timers wrap the
adapter's own methods, so it follows whatever Adapter.decide does; each timer costs about 0.2 us."""
import atexit
import gc
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hyperion.drills.adapter import KitBAdapter, _default_bot  # noqa: E402

pc = time.perf_counter_ns
REC, ENDS = [], []
SEG: dict = {}
GC = [0, 0]


def _cb(phase, info):
    if phase == "start":
        GC[1] = pc()
    else:
        GC[0] += pc() - GC[1]


gc.callbacks.append(_cb)


def wrap(obj, attr, key):
    f = getattr(obj, attr)

    def g(*a, **k):
        t = pc()
        try:
            return f(*a, **k)
        finally:
            SEG[key] = SEG.get(key, 0) + pc() - t
    setattr(obj, attr, g)


bot = _default_bot()
ad = KitBAdapter(bot)
wrap(ad, "to_observation", "xlate")
wrap(ad, "with_history", "hist")
wrap(ad, "_deliver", "deliver")
wrap(ad, "from_action", "back")
wrap(bot, "act", "act")
wrap(bot, "hand_end", "bot_end")
for m in bot.core.members:
    h = getattr(m, "hero", m)
    if hasattr(h, "settle"):
        wrap(h, "settle", "settle")
    if getattr(h, "prof", None) is not None:
        wrap(h.prof, "_settle", "settle")
FIRST = [True]


def decide(o):
    SEG.clear()
    g0 = GC[0]
    t = pc()
    r = ad.decide(o, t * 1e-9 if False else None)
    total = pc() - t
    REC.append({"total": total, **SEG, "gc": GC[0] - g0, "street": len(o["table"]["board"]), "hand": o["hand_id"],
                "level": bot.safe.degrade_level, "first": FIRST[0]})
    FIRST[0] = False
    return r


def on_table_start(i):
    ad.start(i["seat"], i["players"])


def on_hand_end(i):
    SEG.clear()
    t = pc()
    ad.hand_end(i["hand_id"], i["delta"])
    ENDS.append(pc() - t)


def _dump():
    out = os.environ.get("PROF_OUT")
    if out:
        with open(out, "a") as f:
            f.write(json.dumps({"rec": REC, "ends": ENDS, "stats": bot.safe.stats(), "gc": gc.get_stats()}) + "\n")


atexit.register(_dump)
