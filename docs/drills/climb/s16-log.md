# S16: a trust weight on the risk-taking preflop reads at strong tables (running log)

Branch climb/s16-read-trust, from main 724cc7f (batch 5's F). Brief (coordinator, 2026-11-03): item 3 of
docs/research/Edges against strong opponents.md. First repeat S12's warm-store split on the strong fields at 200
seeds: does the loss at strong tables come from the preflop reads that widen F's risk (rival 3's core's fold reads in
its steal price and open clauses, the layer's steal read)? If yes, add `r3.read_trust` and `exploit.read_trust`
(prior + (observed - prior) x n / (n + 10), nothing below 10 chances, only while Profiler.strong_table reads strong at
batch 5's threshold; the defensive reads untouched), fix a per-seat fallback gate before screening, and screen with
`--aim strong`.

Rules kept: screen seeds 10000-10199 only for points; recordings and the firing diagnostic on 8800-8849 (fresh, under
10000; S13 used 8800-8803 for a diagnostic). No held-out set (H1-H18), judge seed, judge bot, judge field or held-out
variant was run, read or profiled. Model mode, eight rotations per seed. At most three worker processes, nice 5; the
host was at load 19-37 with other measurements running. Every measurement of F runs from a detached worktree at main's
code (`goal/wt_s16m`, 724cc7f); scratch tools in `goal/s16/` (never shipped).

## Tools (scratch, `goal/s16/`)

- `warmlib16.py`, `rec16.py`: S12's warm-read device (goal/s12/warmlib.py) ported to batch 5's composite (members by
  name: the base's rival 3 core, the hero member's profiler, the base's fallback Hero's profiler, the front layer).
  S12's stores and counters exactly (the size, probe and raise-guard counters added since stay cold in every arm).
- `warm16.py`: tools/climb_accept.py with four arms of F, `{"bot": "w16_<arm>"}`, F's own cells shared:
  - `all`: S12's warm full (every store at the long-run truth from hand 0);
  - `risk`: only the reads that widen preflop risk warm: rival 3's core's fold read in an unopened pot (`_fold_prob`
    while max(bets) <= bb: the steal price `ev_steal`, the open clauses `ev_steal > 0` and `pf > 0.9`, the short
    shove's fold equity and caller) and the layer's preflop cell (steal_min_fold's rates, a long-run-dead seat's
    streak);
  - `rest`: every other store S12 loaded warm, the risk reads cold (Hero's two profilers, the layer's postflop cells,
    rival 3's other reads and its 3-bet reads);
  - `prior`: cold F with the risk reads at their priors (rival 3's 0.6 and its VPIP prior, dead seats kept; the
    layer's 0.65, so steal_min_fold 0.7 never fires; the dead-seat steal kept). The limit s -> infinity of the
    trust weight, ungated: whether F's own cold fold reads pay or cost at strong tables.
  Patches are instance-gated: only F's seat reads differently (the mirror's f_copy seats play as shipped).
- Recordings: `rec16.py`, seeds 8800-8849 x 8, F in the hero seat, per field (elite, elite_b, mirror, mirror_b).
