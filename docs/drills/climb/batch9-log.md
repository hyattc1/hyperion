# Batch 9: staging (S22 + H1 + B18 + S24's shove read; O8's and the c-bettor's code merged off)

climb/batch9, worktree goal/wt_b9, from main at 92b8e45 (batch 8 + H8's night tooling + G1's whole-call governor). Nothing here is in `SHIP_DIALS`; no held-out
set was started. The combined check and the freeze are the main session's. Main has moved since (to 7526c3e), with docs only: nothing under hyperion/, tools/ or tests/.

## The merges, in order

| # | commit | branch | conflicts | how |
|---|---|---|---|---|
| 1 | c292669 | climb/b8-s22 (S22) | none | |
| 2 | 16a1adb | climb/s20-h1 (H1) | tools/solve_short.py, 2 blocks | G1's `cmd_binary` and H1's `hu2` solver are both additions; the command map names both |
| 3 | 08cd74f | climb/s23-firsts (B18) | hyperion/compose/bot.py 1, hyperion/strategy/short.py 2 | H1's `strong_open` and B18's `strong_now` come from one read (`strong_table` is pure, computed once); dials and methods are additions |
| 4 | ffab72f | climb/s24-overfold (S24) | hyperion/strategy/postflop.py 2, docs/packet/CONTRACTS.md 1 | dials and reads both kept, S22's first; order written at the reads; card regenerated |
| 5 | 97f7345 | climb/b8-o8 (O8) | hyperion/hybrid/core3.py 3, hyperion/hybrid/dials.py 1, docs/packet/CONTRACTS.md 1 | additions at the same place; each count keeps its own guard; card regenerated |

The S24 worker's 13 conflict blocks were against an older base: on this order there were 3. O8 went through as its conflicts are additions at the same place and its dials are inert
(identity below ran with it merged); it is one merge commit if the main session prefers it out. Its own effect was not compared against climb/b8-o8's chunks; tests/test_s21_o8.py passes.

**The order of S22's and S24's reads** (written at the code too): S22 acts on the river alone, S24's c-bettor read on the flop and turn alone, so at most one moves a decision, and each is inert unless its
`*_from` is under 1.0. Neither reads the other's weight. Against the stab read, S22's weight replaces it where larger (equity and margin); S24's equity is the higher of its own and what the stab or wide read left,
and its margin moves after theirs.

## Candidate

docs/drills/climb/batch9-candidate.json: S22 (8 dials) + H1 (6) + B18 (2) + S24's shove read (4, `r3.sr_*`; H41). `hero.postflop.cbr_*` stay out, rejected on H40; their code stays merged, off.
batch9-candidate-s24.json, the earlier union, is deleted.

## Identity

- **All new dials off plays batch 8's F:** 7 of 7 rows equal to goal/idchk39.md, 14 of 14 chunks equal per seed (samples, tmo, errors, calls; goal/idchk40). Effective dials differ only by G1's `whole_call`,
  `degrade`, `hand_end_ms`, which main already carries.
- **Each part plays as on its own branch**, 10000:10040 with the runout term, chunk for chunk (a 15-seed chunk against the first 15 seeds of the 25-seed one where the screen's chunks are longer):

| part | stage | against | equal | prefix-equal | differ |
|---|---|---|---|---|---|
| S22 | exploit | climb/b8-s22 f42a6d2, re-run detached | 30 | 0 | 0 (exploit5's 6 chunks: not on its branch) |
| H1 | elite | goal/s20/h1screen | 5 | 5 | 0 |
| B18 | elite | goal/s23/accept | 5 | 5 | 0 |
| S24, both reads | exploit | goal/s24/screen | 18 | 18 | 0 |
| S24's shove read | exploit | goal/accept_s24 (H41's chunks; 82000:82040, a used set, identity only) | 18 | 18 | 0 |

Effective dials differ only by G1's three in each. Each part's effect shows: S22 exploit4_hu +0.148 ± 0.122, H1 elite +0.012 ± 0.010 (40 seeds).

## Interactions

Corrected diagnostics in the scratchpad's dg/ (candidate on `SHIP_DIALS`, 40 seeds x rotations, plays the climb_accept cells, source-patched counters, branch untouched). **The first set, dg_bad/, is void:** it left out
`SHIP_DIALS`, so no S7, R6, H1 or ladder played.

Who gets a decision:
- **Heads-up preflop:** S7's gates first. H1 only where they refuse and only while the `like_*` read refuses (a seat S7's read admits is S7's or F's, never H1's); then the strong read, 3 probe chances, the 3-bet defer, 10-40 bb
  (button to 22). Exclusive. Across the cells H1 was never followed by S7's postflop in a hand: every decision after H1's preflop went to Hero (elite 262, exploit4_hu 308).
- **Three-handed preflop:** R6 alone (`alive == 3`; H1 needs 2). B18 opens the composite's gate at or under 18 bb, and then the member's either-or decides: per-seat re-raises, or the strong read. Same depth formula on both sides. Deeper, both as R6.
- **Heads-up postflop:** S7, where its route wants the decision, else Hero, where S22 reads. S22's read in a Hero shadow changes nothing played (exploit_hu 4, exploit2_3 2). Against exploiter 2 S7 plays 79% of those decisions and S22 played no bet.
- **Shove read:** in the core, so only where the core decides. Heads-up facing a shove the section is `pre_hu`: S7 and H1 go first. It was fully in a shadow 42 of 1,382 times at elite. After R6's open and a re-shove, keep-defence returns the decision to the core and the read
  acts: 20 hands at elite, 10 at night (R6 then the read, same hand, different decisions).
- **Same hand:** H1 then S22, 10 hands at exploit4_hu, 1 at elite_b, 1 at adapt_hu.
- **One way through the strong read:** R6's and B18's opens feed the table's `_rr` counts, which later gate H1 once two are left. Designed, not measured apart.

Whole candidate on the 40 screen seeds, a first look, not a verdict: nothing beyond noise down; exploit4_hu +0.136 ± 0.150 (S22 alone +0.148 ± 0.122), so H1 does not visibly take S22's gain; elite +0.038 ± 0.046, elite_b +0.057 ± 0.050 UP, mirror +0.060 ± 0.058 UP.

## G1's ladder: what each level drops

`degrade` = "bare,lean,hero"; level n has the first n rungs. Whole tables pinned at each level, model mode, 40 seeds:

| level | S7, R6, H1, B18 | S22 | shove read | notes |
|---|---|---|---|---|
| 1 `bare` | route, but see below | runs (exploit4_hu 96 -> 106 fires) | runs (elite 1,340 -> 1,264) | no shadows |
| 2 + `lean` | as 1 | runs | as 1, except a decision given to Hero under exact ICM | under 8..1 no change at all (decisions equal to level 1); under top-heavy payouts it moves some |
| 3 + `hero` | **all gone** (0 decisions) | runs (exploit4_hu 127) | **gone** (0) | every section Hero |

Panic is no rung with this ladder (`no_panic`); if it did fire, all of them are off, as they need `not cheap`.

**Found at `bare`, already on main, not caused by a merge:** Hero's profiler misses preflop without its light shadow, and two gates that read it starve.
- `rr_by` (R6's per-seat gate): elite 1,672 -> 43 on F, 1,648 -> 41 on the candidate. **F's R6 falls from 254 hands to 0.** On the candidate it falls 458 -> 236; since F's reads alone give 0 there, nearly all of those come through B18's either-or.
- S7 against exploiter 2: preflop decisions 1,307 -> 312 on F, 1,313 -> 467 on the candidate; postflop 3,306 -> 1,635 on F. H1 picks up what the gate now refuses: 13 -> 131 hands.
- Points, raw, 40 seeds, no interval: elite F 4.826 -> 4.641, candidate 4.900 -> 4.722; exploit2_hu F 8.312 -> 8.088, candidate 8.312 -> 8.125.
The likely cause of `rr_by`, read from the code and not tested: a hand the profiler catches up at hand end has blank `chips`, so `amt < chips * 0.95` never opens the count. S7's drop is not root-caused. It may be part of G1's
measured `bare` cost at elite (-0.11 ± 0.07), and G1's log has `bare` held for about 80% of decisions at 2x. Left unfixed: a change here moves play at that level and needs its own check.

## S24's shove read in exploit5_hu (raw DOWN on H41, corrected level)

- H41: raw -0.015 ± 0.015 DOWN, corrected -0.005 ± 0.007 level. Only **4 of 400 seeds** finish differently raw, each -1.5; corrected, 13 differ, 9 down and 4 up.
- Screen seeds 10000-10399, the candidate with and without the read: 889 shoves faced in 800 tables, 52 widened, 17 tables diverge, **all fold -> call**, opponent 10-15 bb, hands 52-104. 5 seeds finish differently: 3 at -1.5, 2 at +1.5; mean -0.004.
- So this is a handful of flipped tables; the two sets disagree on direction and neither is enough to read one. 9 of the 17 flips came with 2 or 3 chances seen before this hand, on the thin end of `sr_min` 3. Worth watching in the combined check; nothing here argues for changing a dial.

## Suite

`pytest -q -m "not timing"` at ded60ba: **1 failed, 1607 passed, 7 skipped, 115 deselected** (16:40, at load about 9-11). The one failure:
tests/test_h5_drill9.py::test_the_entry_template_survives_a_loader_that_unloads_before_the_agent_and_defers_a_timed_hand_end[defer], `hand_over_us` 1231 against a 1000 limit, a CPU-time assert with no timing mark. Alone it passes 5 of 5; 12 repeats read median 180 µs here and 178 on main.
Read as a load flake, not proven. Only the candidate JSON changed after ded60ba, so the suite was not re-run. tests/test_climb_accept.py's adapter weights came with exploiter 5 (a sixth each) and pass; docs/packet/CONTRACTS.md through tools/apicard.py, `--check` clean.
tools/zip_parity.py and tools/zip_host.py now require H1's route to fire when the recorded dials ask for it (ded60ba).

## Package, parity, timing (the candidate at 7e42384, dials recorded)

goal/b9_stage/final/submission.zip, sha256 de59ff6c9092e3bfc13435b59539b0e29fb9c8730d53cbfb7ca57580c3f3d0e7, a trial pack, not a freeze. **3.0 MB zipped, 7.2 MB unzipped**, 121 files, 12 tables at the build, all in the package; passes kit H's caps (2 s, 20 MB, 5 MB).
**Parity PASS:** 112,128 decisions and 1,780 variant decisions identical over 730 tables; strong 1,029, specialist 1,525, H1 358, R6 505.

H1's log's 12.5 MB does not apply here. Its head re-packed today with `--slim` gives 8.6 MB, 3.7 MB zipped, so the figure was not reproduced (why not is not established). It would pass either way: the tightest kit seen allows 20 MB.

| | F (batch 8 + G1) | candidate |
|---|---|---|
| latency.py act p99, 20,000 calls, two runs, load 4-5 | 294.0, 253.7 µs | 249.0, 285.6 µs |
| act max | 961, 3071 µs | 856, 868 µs |
| hand end p99, per-call minimum of 3 | 193.1, 187.5 µs | 188.1, 186.2 µs |
| hand end p99, first pass | 335, 374 µs | 301, 312 µs |
| table start p99, 4 copies, budget 25 ms | 0.55 ms | 0.58 ms |

Level. Zip against zip, zip_timing once each at the box's load (frozen/B8G-e370fb3): setup p50 484 ms, max 550 against 497, 558; p99 524 against 563 µs; timeouts 7 of 14,779 against 4 of 15,174. The load differed (5-8 against 8-9.5) and the counts are small, so no difference is claimed;
exploit2_hu read 3 against 0, p99 619 against 507, one run. Not run: `--k 3`, the kit path through `tools/gate.py --slow`, or the gate itself: those belong to the freeze.
Climb_accept's p99 column is not paired in the first look (candidate at load 11-14, up to 1.5 ms, 0 timeouts; F's cached run at load 8-9).

## For the main session

S24's proposed addendum 17 stays in docs/drills/climb/s24-log.md, "Addendum 17, proposed", now on this branch; docs/decisions.md is untouched. It describes exploiter 5's wiring, which is merged here; S24's reads were not part of it.

## Process notes

- goal/b9_stage/run.sh was written but never started until the coordinator's message: my miss, about three hours lost.
- The first trial pack failed: `tools/pack.py --dials` takes the dials object, not climb_accept's `{"dials": ...}`.
- Part dials and run outputs sit in goal/b9/, an older batch's folder; nothing there was overwritten (checked against the backup). Diagnostics: my session's scratchpad. The detached reference worktrees are removed.
