"""Finish tables/variants/solo after the preflop stage: matrix (low samples), push/fold re-solve, flops, meta."""
import json, sys, time
from multiprocessing import Pool
from pathlib import Path
sys.path.insert(0, sys.argv[1]); sys.path.insert(0, sys.argv[1] + "/tools")
import gen_tables as G
from hyperion import tablegen as tg
rules = tg.rules_from_dict(json.load(open(sys.argv[1] + "/submission/rules_tonight.json")))
out = Path(sys.argv[1] + "/tables/variants/solo")
ms, workers = int(sys.argv[2]), int(sys.argv[3])
classes = tg.class_table(rules)
times = {}
with Pool(workers, initializer=tg._init_worker, initargs=(tg.rules_to_dict(rules), classes)) as pool:
    t = time.perf_counter(); G.gen_matrix(pool, classes, ms, 2026, out); times["hu_matrix"] = time.perf_counter() - t
    print("hu_matrix", round(times["hu_matrix"], 1), flush=True)
    t = time.perf_counter()
    from hyperion.strategy import tables as _tables
    from hyperion.strategy.pushfold import build_pushfold_tables
    _tables._CACHE.clear()
    tl = _tables.load(str(out), need_hu=True, strict=True)
    sol = build_pushfold_tables(tl, str(out))
    times["pushfold_hu"] = time.perf_counter() - t
    print("pushfold", round(times["pushfold_hu"], 1), max(v[1] for v in sol["converged"].values()), flush=True)
    t = time.perf_counter()
    doc = G.gen_flops(pool, rules, 2026, out, int(sys.argv[4]), int(sys.argv[5]))
    times["flop_strength"] = time.perf_counter() - t
    print("flops", len(doc["buckets"]), round(times["flop_strength"], 1), flush=True)
meta = {"rules": tg.rules_to_dict(rules), "samples": 3000, "matrix_samples": ms, "seed": 2026, "workers": workers,
        "seconds": {k: round(v, 1) for k, v in times.items()}, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "python": sys.version.split()[0]}
G._dump(out / "meta.json", meta)
print("done", flush=True)
