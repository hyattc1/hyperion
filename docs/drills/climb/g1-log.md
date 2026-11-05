# G1: the governor counts the whole timed call

Branch climb/g1-governor. The finding was docs/drills/climb/b8-timing.md: through kit B's adapter batch 8 timed out on 12% of its
decisions at 3x, while its governor, timing `act` alone, never stepped down. The owner decided the governor must count the whole
call. Reference for identity: batch 8's F, goal/idchk39.md. Raw runs: goal/g1/runs/ (earlier code in old/, old2/, old3/). The box:
Ryzen 7 9850X3D, 16 threads, WSL2, shared; never quiet (load 9-23 through this work), so every timing row carries its load.

## Where the time went (batch 8's zip, kit B, 40 tables, us; docs/drills/climb/g1_profile_entry.py)

| segment of a call, 1x, load about 15 | mean | p50 | p99 | share of all calls |
|---|---|---|---|---|
| whole call | 236 | 249 | 469 | 100% |
| `act` | 117 | 110 | 242 | 49% |
| deferred hand end, the bot's part (on 55% of calls: 112 mean, p99 218) | 61 | 86 | 179 | 26% |
| deferred hand end, the adapter's part (settling the tail from the next state) | 14 | 21 | 45 | 6% |
| history inference | 22 | 20 | 50 | 9% |
| translation (`to_observation`) | 20 | 19 | 43 | 8% |
| reply, repin, the rest | 2 | | | 1% |
| garbage collection | 0 | 0 | 0 | 0%: none ran inside a call in 7,658 (Hero freezes at table start) |

The same at 3x: the same shares, whole call p50 787, p99 1585. First decision of a table (this branch's profile): 636 us at 2x, 986 at 3x,
cold, 0.5% of calls, and the one a kit's warm-up helps. A call with a held hand end cost 297 against 168 for a later one in the hand. The
hand end, about 100-112 (in-process, by member): the hero member 52 (its ICM curve 26, its profiler 23), the base 41 (rival 3's replay 23,
its fallback Hero 14), the rest under 7. Kit J (drill 12, the recap inside the timed decide), 1x: whole call 219, `act` 106, the recap 74 (its bot part 52), translation
18, a log kit's history 11; 2.5x `act` on a call with a recap, H8's number, and that is where it goes.

## What changed

**Cut, no decision changes** (kit B, 1x: p50 about 250 to 220, -12%; the rest of the fall is the budget): `dataclasses.replace` out
of the inference's `observe`; make_observation's stand-in log not built where the rebuilt one replaces it; `legal_kinds` cached;
the tail's generators gone; the bot's hand end lazy behind an adapter (curve and dials wait for the member that reads them, and run at
the kit's callback when it is untimed); a log kit's hand end does not rebuild what the kit's log already says.

**The clock.** `Adapter.decide` reads it on its first line (or takes the entry's first read, `decide(native, t0)`) and reports the whole
call to the bot's SafeBot on every way out (`report_call`). The overruns are counted there, on the same 0.8 ms line and 5-in-60
window, and `act`'s own time no longer counts. Nothing to wire: the constructor does it. All the templates (entry, module, process,
event, closure) pass their first read. `tools/gate.py` FAILS a package with the dial on and under 99% of decisions reported, warns on
one with the dial off or from before G1, and prints a `governor:` line. Dials: `whole_call`, `hand_end_ms` in SHIP_DIALS and `slow_box`;
`G1_OFF` (with the old ladder) plays batch 8's clock.

**A stall is not a slow box.** The first real-clock runs fired at 1x (level 1 on up to 3% of tables at load 16-18, every gate run): stalls.
Two rules fix it, each found by a real-clock run after the one before it: an overrun needs this thread's CPU time over 0.6 of
the line, and the box's slow mean of CPU time per call (an average to the 64th call, 1/64 after, clipped at 1 ms) over 0.26 ms, since
the thread's clock counts a hypervisor's stall as running. Stepping down answers neither.

**The ladder.** `noshadow` saves nothing on the shipped routes, `lean` nothing under 8..1. Whole tables at each level, model mode, 200 x 8,
night 8..1 unless named (act's p50 / p99 us against F's 108 / 233):

| level | points against F | p50 / p99 |
|---|---|---|
| `bare` (no shadows) | +0.017 ± 0.054; realistic -0.016 ± 0.051; elite **-0.114 ± 0.074**; th -0.61 ± 0.68 of 100 | 75 / 158 |
| `hero` (batch 8's third rung) | **-0.165 ± 0.122** | 82 / 192 |
| `bare` and `hero` | **-0.235 ± 0.117**; th **-2.01 ± 1.30** | 58 / 126 |
| the cheap path (panic; R1's numbers) | -1.58 ± 0.14; th -13.2 ± 1.1 | about as fast as the row above |

So the ladder is `bare,lean,hero` and panic is no rung of it (`no_panic`, with `whole_call`). An adapter that has measured the box at
over 0.3 ms a decision holds the first rung without waiting for a cluster (`set_floor`; back under 0.19).

**The deferred hand end.** Lazy always, as above. Past `hand_end_ms` (a typical decision with one over 0.75 ms) it runs at the kit's
callback without its tail; the bound: one hand in `tail_every` (2) still waits for its tail, whatever the budget, and the gate prints both
counts. A kit with no untimed moment (kit J's recap, entry_template's "store") keeps the chip chain and drops the bot's hand end, at most
one in a row, counted as `dropped`.

**The first design lost points, and the reads are why.** It left the timed call at half the budget, with one tail in eight kept. Timeouts fell
further and points fell with them, on kit B against batch 8, realistic:

| tails kept | 2x | 3x |
|---|---|---|
| 1 in 8 (150 tables) | -0.383 ± 0.280 | -0.476 ± 0.334 |
| 1 in 2 (400 tables) | -0.044 ± 0.145 | -0.239 ± 0.184 |
| all (400 tables) | -0.165 ± 0.120 | +0.014 ± 0.175 |

A timeout is usually a check or fold of a hand we would fold anyway; a fold after our last reply is a read rival 3 and the profiler have
nowhere else to get, and losing it biases them (seats that fold to our raises stop showing it). Worth knowing beyond this branch:
batch 8 at 12% timeouts plays level with this branch at 2% on night under 8..1. The tail now goes only when the budget is truly gone.

**Setup.** tables/extra/short_3b.bin (tools/solve_short.py binary): zlib, json and bytes only, no marshal, no pickle; the last action of
each class is rebuilt from q, base85 (200 ms of pure Python) is gone. The same values: tests/test_g1_table.py compares every node, and
the digest is the same on Python 3.10, 3.11 and 3.12 (no 3.13 here to try). 1.72 MB against 3.19; 58 ms to decode against 260-370. The JSON
stays in the repo as the solver's output and the fallback; pack ships the binary, zipped at level 9.

## The timing table (zip against batch 8, interleaved table by table, the same seeds; realistic, 150 tables)

A = this branch at 742377d, B = batch 8. One telemetry line differs at the head. Over 1 ms is a timeout, strict. Levels: decisions at level
1 / 2 / 3 as a share of A's.

| kit | clock | load | tmo % A | tmo % B | p50 A / B | p99 A / B | max A / B | A's levels 1 / 2 / 3 |
|---|---|---|---|---|---|---|---|---|
| B | 1x | 22.7 | 0.32 | 0.22 | 225 / 249 | 501 / 490 | 11181 / 11181 | none |
| B | 1.5x | 22.6 | 0.33 | 0.50 | 317 / 380 | 707 / 772 | 8089 / 5794 | 25% / 0 / 0 |
| B | 2x | 19.2 | 0.62 | 1.18 | 373 / 509 | 865 / 1057 | 5392 / 7168 | 83% / 0 / 0 |
| B | 3x | 18.8 | 2.71 | 13.37 | 533 / 786 | 1276 / 1599 | 9573 / 9763 | 68% / 11% / 3% |
| J | 1x | 22.5 | 0.28 | 0.32 | 266 / 283 | 563 / 593 | 15368 / 8840 | none |
| J | 1.5x | 20.0 | 0.46 | 0.74 | 350 / 429 | 786 / 904 | 6623 / 4954 | 55% / 0 / 0 |
| J | 2x | 19.6 | 1.15 | 1.81 | 435 / 573 | 1045 / 1138 | 6988 / 8432 | 81% / 1% / 0 |
| J | 3x | 15.9 | 6.13 | 24.72 | 625 / 866 | 1376 / 1624 | 9534 / 6631 | 29% / 27% / 25% |

And on a box less busy (the points runs below, 1600 tables, night):

| kit | clock | load | tmo % A | tmo % B | p50 A / B | p99 A / B | max A / B | A's levels 1 / 2 / 3 |
|---|---|---|---|---|---|---|---|---|
| B | 2x | 9.9 | 0.072 | 0.243 | 345 / 439 | 684 / 821 | 1725 / 2079 | 81% / 0 / 0 |
| B | 3x | 12.6 | 1.21 | 6.80 | 511 / 703 | 1031 / 1249 | 8029 / 3515 | 81% / 1% / 0 |
| J | 2x | 12.8 | 0.206 | 0.513 | 419 / 544 | 822 / 926 | 7683 / 5170 | 81% / 0 / 0 |
| J | 3x | 12.6 | 4.10 | 17.40 | 610 / 830 | 1217 / 1411 | 3976 / 3599 | 43% / 24% / 14% |

**The target, plainly.** 0.3% at 2x: **met at load 10-13 (kit B 0.07%, kit J 0.21%), not met at load 19 (0.62%, 1.15%), about half of batch 8
in either case.** At load 19 the box is oversubscribed, the dilated clock counts what a sibling thread and the hypervisor take, and
the gate's own load clause applies; batch 8's bot with no adapter at all reads 0.25% at load 15-17 (b8-timing.md). A large cut at 3x: **met**,
about five times on kit B (13.4 to 2.7, 6.8 to 1.2), four on kit J (24.7 to 6.1, 17.4 to 4.1). Kit J's 3x stays the weak one: the recap has no
untimed moment.

## Points (paired, dilated clock, screen seeds 10000-10199 x 8, night, 1600 tables a cell; A - B)

| kit | clock | rules | A - B | tmo % A / B | load |
|---|---|---|---|---|---|
| B | 2x | 8..1 | +0.039 ± 0.084 | 0.072 / 0.243 | 9.9 |
| B | 3x | 8..1 | +0.032 ± 0.094 | 1.21 / 6.80 | 12.6 |
| J | 2x | 8..1 | +0.005 ± 0.079 | 0.206 / 0.513 | 12.8 |
| J | 3x | 8..1 | +0.077 ± 0.108 | 4.10 / 17.40 | 12.6 |
| B | 3x | 50/25/12/6/3/2/1/1 | **+4.057 ± 1.144** of 100 | 5.01 / 48.85 | 11.8 |

Level everywhere under 8..1, up by 4 points of 100 under top-heavy payouts, where exact ICM makes the slow box far slower and batch 8 timed out
on half its decisions. Only night and the one top-heavy cell were screened here, on the kit path; `bare` costs -0.11 at elite tables in
model mode, and the kit path at elite tables at 2x-3x was not run. The held-out seeds were not touched.

## The normal box (1x, real wall clock, level 0 is the requirement)

At 742377d, load 15-22: kit B and kit J, 300 tables each on night and 150 each on realistic: **0 overruns counted, level_max 0, 0 tables left level
0, 0 hand ends without their tail, in 900 tables and about 165,000 decisions**. The gate runs likewise, plain and two twists. Timeouts at 1x
are level with batch 8's (0.16% and 0.16% at load 18, on night). The paired points at 1x: +0.092 ± 0.142, +0.046 ± 0.154, +0.020 ± 0.144,
-0.037 ± 0.108.

## Identity

- `climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards`: all seven rows' points, timeouts and errors as goal/idchk39.md
  (only the p99 column moves, a clock's).
- The kit path, which climb_accept never plays: tools/kit_compare.py --det, model mode, reply for reply against batch 8's zip: kit B 80 of 80
  tables (13,469 decisions), kit J 80 of 80 (13,634).
- tests/test_g1_governor.py: the kit path in model mode with G1 on and G1_OFF, reply for reply.

## Setup and the zip

Import, build and first table, cold, no bytecode cache, tools/zip_timing.py, the same hour for both, ms (p50 / max):

| condition | this branch | batch 8 |
|---|---|---|
| 1x, load 15 | 428 / 443 | 659 / 695 |
| 1x, load 22 | 588 / 880 | 918 / 2109 |
| 3x, load 15 | 1266 / 1313 | 1937 / 2043 |
| 3x, load 22 | 1299 / 1347 | 1997 / 2080 |

Kit H's 2 s start, at 3x: was over at the worst table, now 1.35 s. The zip: 2,966,703 bytes against 3,692,371; 7.1 MB unzipped against 8.5. The bot alone
(no adapter, zip_timing): p50 and p99 level with batch 8, as they should be; the bot's `act` did not change.

## The final state (e370fb3; the timing, points and normal-box runs above are 742377d, one telemetry line behind)

- Zip (kit B entry, `--slim`): sha256 941360774ad1801a8b5afe771f2006ea53d50eb3b703fd2cf6cd5dce4cd4040f.
- tools/zip_parity.py: PARITY PASS, 112,522 decisions and 1,779 variant decisions over 730 tables; strong 1105, heads-up 1533, R6 226.
- tools/gate.py, 40 tables strict, load about 10: plain PASS +0.350 ± 0.596, 0.00% timeouts; auction PASS -0.495 ± 0.711, 0.00%; bonus_card PASS -0.031 ±
  0.559, 0.00%; kit J's seat (closure entry, zip 778e3aab...) PASS +0.281 ± 0.620, 0.01%. All four: every decision reported, 0 overruns, level_max 0.
- Identity at the head, kit B reply for reply: 40 of 40 tables, 6,599 decisions.
- Suite, `-m "not timing"`: 1556 passed, 7 skipped, 0 failed.

## Not verified

- **A really slower CPU.** Every slow row is the dilated clock: K times this thread's CPU time. It scales memory-bound work as much as CPU work, and at
  high load it counts what a sibling thread and the hypervisor take.
- **A CPU-share sandbox.** By design the governor now ignores time our thread did not run: on a quota that stalls a bot in slices it will not step down,
  and the box's mean will not read slow. b8-timing.md found no bot code answers those stalls either, but that was measured on the bot alone, not on this clock.
- **The real kit**, its adapter's cost, and whether its hand end is timed. Kit B and kit J are fakes; kit J's numbers are through the gate's closure seat. Its own simulator ran
  the zip at 120 tables with 0 errors at limits of 1000 and 500 us (46 timeouts of 33,903 against batch 8's 63 of 31,459 at 500 us), which does not dilate.
- **A quiet box**: load never fell under 9. **Elite tables on the kit path at 2x-3x**: not run; `bare` costs -0.11 ± 0.07 there in model mode.
- **Twists at 2x-3x**: only plain hold'em and one top-heavy table. **Python 3.13+**: not on this box; the table's test skips them.
- **The first 32 decisions of a table on a slow box**: the box must read slow first, so the governor and the floor wait for that; the table's first decision (986 us at 3x
  through a kit with no warm-up) times out about 40% of the time at 3x, as before.

## Commands

    python tools/kit_compare.py NEW.zip OLD.zip --slow K --tables 150 --seed 11                         # timing, kit B
    python tools/kit_compare.py NEW.zip OLD.zip --kit gate_seat.py --entry bot.py --slow K ...          # kit J
    python tools/kit_compare.py NEW.zip OLD.zip --slow K --tables 200 --t0 10000 --rotations 8 --field night@hero   # points
    python tools/kit_compare.py NEW.zip OLD.zip --det --tables 80 --t0 300                              # identity, reply for reply
    PROF_OUT=x.jsonl python tools/gate.py DIR --kit b --entry g1_profile_entry.py --baseline package --slow K   # the profile
