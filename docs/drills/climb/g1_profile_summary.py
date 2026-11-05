"""Where the timed call's time goes: g1_profile_entry.py's records, by segment (us). python g1_profile_summary.py x.jsonl ..."""
import json
import sys

KEYS = ("total", "xlate", "deliver", "bot_end", "hist", "act", "settle", "back", "gc")


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] / 1000


def block(name, rs, n):
    if not rs:
        return
    tot = sum(r["total"] for r in rs)
    print(f" {name}: n {len(rs)} ({100 * len(rs) / n:.1f}%), over 1 ms {100 * sum(r['total'] > 1e6 for r in rs) / len(rs):.2f}%, "
          f"over 0.8 ms {100 * sum(r['total'] > 8e5 for r in rs) / len(rs):.2f}%")
    for k in KEYS:
        xs = [r.get(k, 0) for r in rs]
        print(f"   {k:8} mean {sum(xs) / len(xs) / 1000:7.1f} p50 {q(xs, .5):7.1f} p90 {q(xs, .9):7.1f} p99 {q(xs, .99):8.1f} "
              f"max {q(xs, 1):9.1f} share {100 * sum(xs) / max(1, tot):5.1f}%")


for path in sys.argv[1:]:
    rows, ends, tables = [], [], 0
    for line in open(path):
        d = json.loads(line)
        rows += d["rec"]
        ends += d["ends"]
        tables += 1
    n = len(rows)
    print(path, "tables", tables, "calls", n)
    block("all", rows, n)
    block("first of the table", [r for r in rows if r["first"]], n)
    block("with a held hand end", [r for r in rows if r.get("bot_end")], n)
    block("preflop, no hand end", [r for r in rows if not r.get("bot_end") and r["street"] == 0], n)
    block("postflop", [r for r in rows if r["street"]], n)
    block("over 0.8 ms", [r for r in rows if r["total"] > 8e5], n)
    if ends:
        print(f" the kit's hand-end callback (untimed): p50 {q(ends, .5):.1f} p99 {q(ends, .99):.1f} max {q(ends, 1):.1f}")
