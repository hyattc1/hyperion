# S26: a heads-up re-jam read, H1's reach, chips on arrival (running log)

Branch climb/s26, worktree goal/wt_s26, from climb/s25-hu 05dbdef. F here = SHIP_DIALS + goal/b42/cand.json (batch 9 + S24's shove read +
S25). Order from the coordinator: (b) a heads-up re-jam read from the big blind, (c) H1 without the strong read, (a) chips on arrival only if
a clean idea is left. Each priced first with the coin, in ICM points, on separate fit and check seeds. Diagnostic seeds 20000-20999. Judges
(out_reads, elite5, out_cfr, out_press, out_charts, out_o9/o10/o11, rival4, rival5, adapt2, elite6/7) are never run or read here.
Scratch: `goal/s26/`.

## (b) The heads-up re-jam read

### What the recordings already say (S25's rec_*_brief, F = batch 9, seeds 19000-19199; `a26.py scan`, `a26.py cf`)

Every opener over-folds to a heads-up re-jam, in every room, at every depth: f_copy 0.91, elite1 0.91, rival3 0.91, rival2 0.88, rival1 0.87,
elite2 0.80, F 0.81, elite4 0.76 (strong rooms); the ordinary rooms' F 0.88, rival1 0.83, loose_aggro 0.87, tag 0.89, pushfold 0.83, the night
pool 0.77, hero_tight 0.71; montecarlo30 0.00 (22 answers). The equilibrium opener folds 0.55-0.74 (S25's H1 widths). F's big blind against a
non-jam open at 15-22 bb re-jams 24% (elite1 66%, elite2 53%, rival2 35%), at 10-15 bb 56%.

First-order value of re-jamming instead of F's fold or call (the opener answers at the fold rate measured for that bot and depth, calling with
its top hands by rank, against its actual hand; 8-30 bb; milli-points a table-rotation under 10/7/5): strong rooms +82 (5,631 spots), q0 +25, q1
+20, q2 +19, q3 +11, q4 +8; replacing folds +38, calls +44. Night +53, top +46, realistic +5 (montecarlo30's seats -11, the rest +16). So the
prize looks large, four times S25's, and it is a first-order number: it holds the openers' answers fixed as the jam widens. The coin is what
counts.

### The rule (hyperion/compose/bot.py `_hu_rejam`, ComposeConfig.hu_rejam_*; off by default, tests/test_s26_rejam.py)

Plain hold'em (not a straddle), heads-up, our big blind facing the button's first-in raise (not all-in, under 40% of the effective stack), at 10 to 22
bb effective, the members not already raising. Read of the opener's fold: the profiler's `open_fold_to_reraise` (answers to any re-raise this table, shrunk
to prior 0.5 with weight 5, at least 3 answers seen), then our own heads-up re-jams' answers on top with that read counting as 4 of them, so a seat that
starts calling our jams shuts the rule fast. The rule needs the read at 0.70 or more (`hu_rejam_t`). Then the chip gain over folding must be positive:
read x pot + (1 - read) x ((2 eq - 1) x effective + our blind), eq = rival 3's equity table against the top (1 - read) x 0.7 of hands. It overrides the
members (S7, H1, the base) after the exploit layer, once they answer fold or call.

Pre-registered before any coin result: v1 = the values above (t 0.70, any hand the sum allows, 10-22 bb, over folds and calls). Fallbacks, in order, one
fixed rule each, no sweep: (i) if the weakest hands or the realistic room lose, `hu_rejam_cap` 0.66 (no hand outside the top 66%, the widest an elite re-jams
at this depth); (ii) if the rule's overrides of F's calls lose while its overrides of F's folds gain, folds only. If neither pays, the idea stops.

### Coin v1, fit seeds 20000-20119 (120 x 8 a room, 10/7/5; `A_<room>_brief.jsonl.gz`; read - F, points a table-rotation, 95%)

| room | eligible hands | read's arm: opener folds | read - F |
|---|---|---|---|
| four strong rooms pooled | 812 of 17,631 heads-up hands | 0.89 | **+0.0195 ± 0.0104 UP** |
| realistic | 101 | 0.80 | +0.0164 ± 0.0166 |
| night | 190 | 0.89 | **+0.0287 ± 0.0193 UP** |
| top | 141 | 0.75 | +0.0092 ± 0.0205 |

Nothing negative in any room on the fit. By rank (strong) q0 +0.0072, q1 +0.0001, q2 +0.0064, q3 +0.0062, q4 -0.0004; by who decided base +0.0102, H1 +0.0093; by opener f_copy +0.0112 of the 0.0195,
the rest spread. Fallback (i) is not triggered: the weakest hands gain and realistic is not down. The check seeds run next, unchanged.

### Coin v1, check seeds 20120-20239 (`B_*`), and the heads-up exploit cells on 20000-20119 (`X_*`)

| room | eligible hands | read's arm: opener folds | read - F, points a table-rotation |
|---|---|---|---|
| four strong rooms pooled | 732 of 17,697 | 0.89 | **+0.0233 ± 0.0093 UP** |
| realistic | 127 | 0.86 | **+0.0178 ± 0.0153 UP** |
| night | 155 | 0.89 | +0.0118 ± 0.0182 |
| top | 161 | 0.83 | +0.0091 ± 0.0224 |

By rank (strong) q0 +0.0056, q1 +0.0071, q2 +0.0069, q3 +0.0032, q4 +0.0007; base +0.0129, H1 +0.0105; depth 10-15 +0.0092, 15-20 +0.0133, 20+ +0.0009. Openers: f_copy +0.0104, the other nine +0.0129 together,
elite1 +0.0020, elite2 +0.0007, elite4 -0.0010 (few hands each).

Heads-up exploit cells, 10/7 (a chip is worth about as much as under 10/7/5), 120 x 2 seats: exploit_hu +0.056 ± 0.103 (the opener folds only 0.40, F still gains: it was folding those hands), exploit2_hu +0.055 ± 0.086, exploit3_hu +0.044 ± 0.041 UP, exploit4_hu +0.056 ± 0.058,
exploit5_hu +0.110 ± 0.109 UP, adapt_hu +0.076 ± 0.060 UP. None down.

**Fit and check agree: about +0.02 a table under 10/7/5 at the strong rooms, nothing down anywhere.** A per-hand coin holds the opponent's reads of F at their half-dose, so a table-for-table check is still owed; the screen does that.

### Why the read reaches 28% of the spots, and a second read (pre-registered)

`reach.py`, strong rooms, 2,918 spots at the fit seeds (big blind, facing a non-jam open, 10-22 bb): the read fires 28%, the members already raise 32%, the read is under 0.70 33%, fewer than 3 answers seen 6%. Under 0.70 on 62% of elite2's spots, 54% of elite1's, 47% of elite4's, though
these fold 76-91% to a heads-up re-jam: `open_fold_to_reraise` counts sized 3-bets, which they call far more often. **v2**: the seat's answers this table to re-raises that were all-in (new profiler counts `ofj_*`) come first, with the any-re-raise read counting as 2 of them (`hu_rejam_jk` 2); our own heads-up jams on top as in v1.
So an elite's first all-in answers open the rule, and our premium re-jams, which F makes anyway, show the fold rate before the rule widens. Fixed before its coin: same threshold, depth, everything. Coin on the old fit seeds (`C_*`, to compare with v1 directly) and fresh check seeds 20240-20359 (`D_*`). v2 replaces v1 only if it gains over v1 at
the strong rooms on the fit and holds on the check with no room down; otherwise v1 goes to the screen.

(c)'s dial `short.hu2_free` went in at the same commit, off.

### Coin v2 (t 0.70, 10-22 bb, `hu_rejam_jk` 2): fit 20000-20119 (`C_*`, the same seeds as v1) and check 20240-20359 (`D_*`); points a table-rotation under 10/7/5

| room | v1 on the fit | **v2 on the fit** | **v2 on the check** |
|---|---|---|---|
| four strong rooms pooled | +0.0195 ± 0.0104 | **+0.0273 ± 0.0112 UP** (1,019 eligible) | **+0.0261 ± 0.0105 UP** (1,070 eligible, opener folds 0.91) |
| realistic | +0.0164 ± 0.0166 | +0.0133 ± 0.0209 | +0.0061 ± 0.0153 |
| night | +0.0287 ± 0.0193 | **+0.0320 ± 0.0235 UP** | +0.0161 ± 0.0220 |
| top | +0.0092 ± 0.0205 | +0.0155 ± 0.0213 | **+0.0266 ± 0.0230 UP** |

v2 reaches 35% of the spots (v1 28%); elite1's 29% (7%), elite2's 19% (13%). Against the elites on the check: elite1 +0.0027, elite2 +0.0011, elite4 +0.0031, about +0.007 together; opener folds 0.88-0.97. By rank (check): q0 +0.0119, q1 +0.0094, q2 +0.0006, q3 +0.0051, q4 -0.0009: the premium hands level, as on every set so far.
Its pre-registered test is met (gains over v1 on the fit, holds on the check, no room down). **v2 replaces v1.**

- Identity at 8cc4738 (dials absent, 10000:10040 confirm,guards, against climb/s25-hu at 05dbdef in wt_s26ref; `goal/s26/idcmp2.py` pairs the chunk dirs by spec): **14 of 14 identical for each of F and the b42 candidate.** To be re-run at the code frozen for the screen.

## (c) H1's reach: H1 without the strong read

`short.hu2_free` (off): with the strong read shut, the H1 path plays wherever its other gates (`hu2_like_opp`, `hu2_defer_3bet`, `hu2_min`, `hu2_max`, `hu2_btn_max`) admit it. Coin (`d26h.py`, `ipsh.py`): a fair coin per heads-up hand; eligible = a decision went, or would go, to H1 through the dial alone. Base: F + v2. Fit 20000-20119 (`H_*`), check 20480-20599 (`I_*`) if the fit pays. Heads-up exploit cells on the fit seeds, since exploiter 1 was H1's old loss. Pre-registered: no further split; if the fit is not up at the strong rooms, or any room or exploit cell is down, (c) stops.

## (a) Chips on arriving heads-up: the same read three-handed

Not in the set-aside list or s23b's log: those tried the small blind's first-in tables, calls of jams, and reads of the big blind. **What's untried is F's own re-jam.** `a26t.py` on S25's recordings: three alive, the first answer to a non-jam open: openers fold to a re-jam 0.85-0.96 (F 0.92-0.93, f_copy 0.92-0.93, elite1 0.92 at 15-22 bb and 0.65 at 10-15, elite2 0.81-0.87, rival1-3 0.89-0.96, realistic's and night's openers 0.77-0.96), while F re-jams 8% at 15-22 bb and 28% at 10-15, elite1 24% and 43%, elite2 16% and 33%, rival2 34% and 22%. S23's leak was F being re-jammed; this is F not re-jamming.

The rule, `hu_rejam_alive` 3 (off at 2; tested): with three alive, the raiser our only opponent left and nobody behind us (the small blind folded, or the button did and the small blind opened), the same read and depth window, the gain in ICM points (rival 3's `icm_points` and the bust place: the three-handed risk premium is in it), opens' width 0.5 (`hu_rejam_open_w3`). Pre-registered: as it stands on the fit (20000-20119, `T_*`, `d26t.py`; heads-up as v2 in both arms; `pts` = the hand's change in F's ICM points) and the check (20600-20719, `U_*`). If the weakest hands lose or a room is down: `hu_rejam_cap` 0.66, one fixed fallback. If that does not pay, it stops.
