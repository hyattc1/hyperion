# S16b: reading how each seat answers our own opens (running log)

Branch climb/s16b-open-answer, from main 64b466a (S16 merged, its dials off). Brief (coordinator, 2026-11-03): S16's
next step. A per-seat read of how each seat answers F's own first-in raises (fold, call, re-raise), in place of the
pooled fold-to-a-raise in rival 3's steal price, and in the layer's steal read if it has the same bias; a fold prior
near 0.70-0.75 fixed from a survey of the pooled fields before screening, with the trust floor on small samples; hold'em
tables only plus whatever gate the survey supports; screen `--aim strong` (elite, confirm, guards, all 12 exploit
cells, variants). The target: S16's `prior` arm (+0.14 to +0.21 at strong tables, but it lost on realistic and
top_heavy when gated) without the losses.

**Findings.**
1. **The survey.** 228,397 answers to F's first-in raises on nine fields: strong seats fold 0.67-0.75 to F's opens
   (4-9 points under their pooled fold-to-a-raise), but **position matters more than the seat**: the big blind folds
   0.57-0.60 at strong tables (0.80 on realistic), the small blind 0.77-0.79, the others 0.85-0.87. Priors fixed from
   the nine fields pooled: 0.866 / 0.815 / 0.668 (all answers 0.774, strong fields 0.748). The estimator chosen offline
   (no points), the only one better than F's read on every field: this table's fold rate by position (prior worth 20
   answers) plus the seat's excess (worth 23). The floor at 10 made every estimator a little worse (a seat answers 7-15
   opens a table), so the trust weight is the shrinkage itself, with no floor. The layer's steal read has the same bias.
2. **O1 (the read replaces F's): rejected** (top -0.096, elite_night -0.120 down; strong cells negative). A truer fold
   rate raises the early positions' fold equity as well as lowering the blinds', and rival 3's open clause (pf x pot -
   (1 - pf) x raise x 0.55) then opens more junk early.
3. **O2 (the read only lowers F's read, S16's one-sided cap): the gain the brief asked for**, mirror +0.137 and mirror_b
   +0.202 (the `prior` arm's +0.147 / +0.210), elite +0.052, elite_b +0.071, night_hard up, realistic and top level;
   **rejected** for exploiter 1 heads-up (-0.165) and three-handed (-0.205), antes_from_level_3 (-0.062) and straddle
   (-0.127).
4. **O3 = O2 with four or more alive and off on straddle tables** (both added after O2's screen): mirror +0.105 and
   mirror_b +0.197 UP, elite_b +0.075, elite +0.030, elite_night +0.026; night -0.031, guards level, night_hard up;
   12 exploit cells level or up (exploit3 +0.131), 8 of them and straddle exactly F's; **antes_from_level_3 -0.060 ±
   0.051 down**, the one cell against it (realistic-based cells all lean negative, -0.03 to -0.06). Latency p99: act
   110-111 µs, hand end 140-147 µs. Spec: `{"r3.oa_read": true, "exploit.open_read": true, "r3.oa_cap": true,
   "exploit.open_cap": true, "r3.oa_min_alive": 4, "exploit.open_min_alive": 4}` at aafe5b9 or later.
5. **Next:** the realistic lean comes from the big blind's pooled prior (0.668 against realistic's 0.80) moving slowly.
   A table gate would hide it but leaked on realistic for T3; a faster table-rate prior (oa_st under 20) or a prior
   from the table's own non-blind answers are cheaper to try. Not run.

Rules kept: screen seeds 10000-10199 only for points; the survey on 8850-8899 (fresh, under 10000). No held-out set,
judge seed, judge bot, judge field or held-out variant was run, read or profiled. Model mode, eight rotations per seed.
At most three worker processes, nice 5. F's cells come from main's code (detached worktree `goal/wt_s16m`), copied to
the branch's version after an identity check. Scratch tools in `goal/s16/` (`survey16b.py`, `survey16b_report.py`,
`survey16b_table.py`, `patch_oa.py`; never shipped).

## 05:05-05:40: the survey (survey16b.py, 8850-8899 x 8, F at main in the hero seat, nine fields, no points)

Every answer to F's first-in raise (all folded to F, F not all-in): each seat's first action until someone re-raises,
with what F's reads said at the moment of the open. 228,397 answers.

| field | answers | fold | call | re-raise | fold: small blind | big blind | not a blind | rival 3's read at the open (fr >= 10) | layer's read |
|---|---|---|---|---|---|---|---|---|---|
| night | 31,710 | 0.797 | 0.139 | 0.063 | 0.864 | 0.692 | 0.886 | 0.827 | 0.765 |
| realistic | 31,456 | 0.825 | 0.117 | 0.058 | 0.849 | 0.799 | 0.846 | 0.807 | 0.765 |
| night_hard | 30,184 | 0.783 | 0.144 | 0.073 | 0.845 | 0.659 | 0.876 | 0.828 | 0.762 |
| top | 27,221 | 0.784 | 0.129 | 0.086 | 0.806 | 0.703 | 0.862 | 0.809 | 0.758 |
| elite | 22,495 | 0.751 | 0.153 | 0.096 | 0.785 | 0.600 | 0.872 | 0.800 | 0.747 |
| elite_night | 23,919 | 0.750 | 0.168 | 0.082 | 0.791 | 0.636 | 0.867 | 0.796 | 0.738 |
| elite_b | 21,355 | 0.742 | 0.149 | 0.109 | 0.766 | 0.594 | 0.863 | 0.787 | 0.741 |
| mirror | 19,929 | 0.745 | 0.151 | 0.104 | 0.781 | 0.570 | 0.861 | 0.785 | 0.741 |
| mirror_b | 20,128 | 0.751 | 0.145 | 0.104 | 0.785 | 0.595 | 0.853 | 0.787 | 0.745 |

Pooled over all nine fields: fold 0.774 (strong fields 0.748); small blind 0.815, big blind 0.668, the others 0.866
(strong fields 0.782 / 0.602 / 0.863; guard fields 0.842 / 0.718 / 0.869). By identity (all fields pooled): the
strong seats fold 0.67-0.75 to F's opens and re-raise 10-14% (elite2 0.672, rival1 0.690, rival3 0.698, elite1 0.729,
rival2 0.732, elite4 0.742, f_copy 0.747), 4-9 points under their pooled read; the agent builds and Track B 0.77-0.88;
tag 0.936, nit 0.963; a few weak seats fold more to our opens than their read says (timeout_then_recover +0.13,
montecarlo +0.05). A seat answers 7-15 of F's opens a table (f_copy's three seats 22 together). Between-identity sd of
the fold rate 0.085, so a Beta prior is worth about 23 answers.

What this says:
- **Position is the larger effect.** The big blind folds 0.57-0.80 to our open, the others 0.85-0.89: a spread of 0.2
  inside a seat, against 0.085 between seats. Rival 3's read (and the layer's) is one number per seat, so it
  overstates the big blind's fold by 0.1-0.2 at strong tables and understates the early seats'. A button or cutoff
  steal (one or two seats behind, the blinds) is where the clause opens 85% of hands and where the read is most wrong.
- **The layer has the same bias** where it fires: its steal_min_fold needs a product of 0.7, which in practice means
  one or two seats behind (the blinds), read at 0.74-0.77 against the big blind's 0.57-0.64 at strong tables.
- **The field level moves the blinds most** (big blind 0.80 on realistic, 0.57 on mirror), so a fixed prior must be
  wrong somewhere; a table's own answers by position say which table it is.

## 05:40-05:50: the estimator, chosen offline (survey16b_report.py, survey16b_table.py; no points)

Each estimator predicts each answer from what F had seen before that hand at that table; Brier score (and mean bias,
predicted - actual fold) per field:

| estimator | night | realistic | night_hard | top | elite | elite_night | elite_b | mirror | mirror_b |
|---|---|---|---|---|---|---|---|---|---|
| E0 rival 3's read (F) | 0.1571 | 0.1433 / -0.046 | 0.1680 | 0.1668 | 0.1894 / +0.013 | 0.1784 | 0.1946 | 0.1942 / +0.005 | 0.1909 |
| E2 seat's own answers, one prior 0.775 (s 23) | 0.1558 | 0.1411 | 0.1657 | 0.1654 | 0.1845 | 0.1786 | 0.1895 | 0.1883 | 0.1857 |
| E2f the same with the floor (nothing below 10, s 10) | 0.1565 | 0.1411 | 0.1665 | 0.1661 | 0.1845 | 0.1790 | 0.1896 | 0.1879 | 0.1851 |
| P1 prior by position + seat excess (s 23) | 0.1495 | 0.1456 / -0.047 | 0.1575 | 0.1622 | 0.1730 | 0.1706 | 0.1785 | 0.1760 | 0.1755 |
| P2 the same with the floor (nothing below 10, s 10) | 0.1502 | 0.1458 | 0.1585 | 0.1632 | 0.1731 | 0.1712 | 0.1788 | 0.1756 | 0.1752 |
| P3 the strong fields' position priors + seat excess | 0.1531 | 0.1549 / -0.089 | 0.1594 | 0.1656 | 0.1715 / -0.007 | 0.1707 | 0.1766 | 0.1735 | 0.1740 |
| P4 position prior + rival 3's read debiased as the seat's level | 0.1489 | 0.1468 | 0.1580 | 0.1625 | 0.1753 | 0.1679 | 0.1814 | 0.1799 | 0.1794 |
| **T5b this table's rate by position (prior worth 20) + seat excess (s 23)** | **0.1490** | **0.1430 / -0.024** | 0.1582 | 0.1631 | 0.1738 / +0.022 | 0.1700 | 0.1789 | 0.1757 | 0.1756 |
| T5d the same, the floor on the seat excess (nothing below 10, s 10) | 0.1505 | 0.1438 | 0.1601 | 0.1652 | 0.1753 | 0.1715 | 0.1804 | 0.1765 | 0.1764 |

- A prior by position is worth more than anything about the seat (P1 against E2); the strong fields' priors (P3) are
  best at strong tables and worst on the guards; the pooled read adds little once position is in (P4).
- T5b is the only estimator better than F's read on every field, realistic included (0.1430 against 0.1433), and
  within 0.002 of the best at each strong field: the table's own answers by position move its prior to the field
  (realistic's big blind 0.80, mirror's 0.57), which is the gate a fixed prior lacks. At the strong fields it is
  within 0.0025 of the best estimator there (P3, built on the strong fields' own priors).
- **The floor does not help**: with 7-15 answers a seat a table, nothing below 10 throws away half of each table's
  evidence (T5d, P2, E2f are each a little worse than their versions without it). The trust weight is kept as the
  shrinkage itself (a seat's excess counts n / (n + 23), a table position's rate n / (n + 20)); the floor is off.

## Pre-registered before any screen (05:55)

**O1** = `{"r3.oa_read": true, "exploit.open_read": true}` on top of SHIP_DIALS, with the dials' defaults fixed from the
survey: priors fold 0.866 (not a blind), 0.815 (small blind), 0.668 (big blind), the nine fields pooled (0.774 over
all answers, 0.748 at the strong fields); a table position's weight `oa_st` 20; a seat's `oa_s` 23; `oa_min_n` 0.
- Rival 3's core: in an unopened pot with no limper, deeper than short_bb (10 bb), every seat behind is read as this
  table's fold rate from its position plus its own excess; this replaces the fold-to-any-raise read in `pf` there
  (the steal price `ev_steal` and both open clauses). Dead seats still fold (1.0). Not touched: the short shove's
  price (the survey left out all-in opens), the iso-raise over limpers, facing a raise, the 3-bet defence, postflop.
- The layer: steal_min_fold reads the same (`Exploit.open_fold`, wired by the composite to the base's core).
- Counted at each hand end from the history (my first-in raise not all-in, every earlier action a fold; each other
  seat's first action until someone re-raises), per table.
- Gate: hold'em tables only (hero.holdem_table: the 22 twist variants play exactly as F, tested). No strong-table
  gate: the survey supports none, because the table's own position rates adapt the read to the field.
- One candidate; no other value is screened.

## 05:43-06:06: identity (idcheck3.py)

`climb_accept --cand '{"dials": {}}' --set 10000:10040 --stages confirm,guards` and `--set 10000:10025 --stages
elite,exploit` (now 12 exploit cells), in the detached main worktree (64b466a) and on the branch (bc8f723), separate
caches: **all 31 cells identical sample for sample**, and the 28 that existed then identical to F at 724cc7f too. With
the dials off nothing is counted (the scan runs only with `r3.oa_read` or the layer's `open_read`) and the deep branch
keeps its `pf`. F's cells at main's version were copied to the branch's (7dd316b7d4, key 6c18820fd9c6). (A first
launch of the queue died at 05:53 with this session's command; relaunched under setsid.)

**Added at 06:25, after O1's partial screen (not pre-registered with O1).** With 7 of O1's 28 cells complete, top was
beyond noise down (-0.096 ± 0.094) and elite at -0.084 ± 0.109 after 150 seeds. A likely reason, before the rest is
in: rival 3's open clause prices a steal as pf x pot - (1 - pf) x raise x 0.55, a crude model tuned with the biased
read; an accurate read raises pf for early-position opens (seats that are not blinds fold 0.87, above the old 0.8)
as well as lowering it for late ones, and the `prior` arm's gain came from steals given up, not from accuracy. **O2**
= O1 + `{"r3.oa_cap": true, "exploit.open_cap": true}`: the open-answer read only lowers a seat's fold read (min of
the two), S16's one-sided rule, which kept T2's guards level. Code da609e3; O1 plays identically under it. Screened
after O1's table, the same stages; the held-out set decides, not this screen.

## 06:06-06:39: O1's screen (code bc8f723, version 7dd316b7d4; screen 10000-10199 x 8), stopped part-way

`climb_accept --cand '{"dials": {"r3.oa_read": true, "exploit.open_read": true}}' --set screen --stages
confirm,guards,elite,exploit,variants --variants top_heavy,antes_from_level_3,fast_schedule,straddle --variant-seeds 200
--aim strong`. The run was killed from outside between 06:16 and 06:39 (the host's OOM killer fired at that time on
another process; this queue's shell went with it), after 12 of its 28 cells. Its cached chunks, O1 - F paired:

| cell | O1 - F | |
|---|---|---|
| night | -0.001 ± 0.083 | level |
| night_hard | +0.074 ± 0.097 | level |
| realistic | +0.034 ± 0.074 | level |
| **top** | **-0.096 ± 0.094** | DOWN |
| night @10/7/5..., @50/25/12..., doubling | +0.054 ± 0.134, +0.458 ± 0.912, +0.011 ± 0.073 | level |
| elite | -0.090 ± 0.095 | level |
| **elite_night** | **-0.120 ± 0.085** | DOWN |
| mirror | -0.048 ± 0.097 | level |
| elite_b | -0.029 ± 0.101 | level |
| mirror_b (50 seeds) | +0.140 ± 0.219 | level |
| exploit, variants | not reached | |

**O1: REJECT** (top and elite_night beyond noise down; the strong fields' point estimates negative). Not re-run: two
cells are already down at 200 seeds. The more accurate read makes F worse at strong tables, where the brief wanted the
gain. The intervals (± 0.08-0.10, against T2's ± 0.04-0.05) show it changes many decisions.

O1's latency (`tools/latency.py --hand-end --reps 3 --tables 20`, per-call minimum, bc8f723, load 16-24): act p99
107.1 / 121.9 µs (realistic / elite; F 115.6 / 113.0), hand end p99 148.6 / 141.0 (F 143.3 / 140.6); mean +0.4 to +2
µs. The targeted suites at bc8f723 (the S16 and S16b tests, s11-s15, ship, compose x4, hybrid3, exploit x2, profiler,
API card, mirror, adapt, climb_accept): 244 passed.

## 06:55-07:18: O2's code (the cap, cherry-picked as the branch's next commit) and identity again

Identity at the new code (idcheck3.py, the same 31 cells): **all 31 identical** to main 64b466a and to 724cc7f; F's
cells copied to version 409c5ced04 (key 044e841c99e0). O2's screen follows (from 07:18; same stages).

**O3, added at 08:20 after O2's exploit cells (not pre-registered).** O2's exploiter 1 heads-up (-0.165 ± 0.102) and
three-handed (-0.205 ± 0.131) cells came in beyond noise down while its strong cells were up (below). O3 = O2 +
`{"r3.oa_min_alive": 4, "exploit.open_min_alive": 4}`: the read only while four or more players have chips, so the
heads-up and three-handed steal prices stay F's (S12's C6 did the same for the size read). Code 7959538, cherry-picked
after O2's run. Exploit stage first, then elite, confirm and guards, variants (host at load 45: 2 workers from here).

## 07:18-08:30: O2's full screen (code e54c827, version 409c5ced04; screen 10000-10199 x 8)

`climb_accept --cand '{"dials": {"r3.oa_read": true, "exploit.open_read": true, "r3.oa_cap": true, "exploit.open_cap":
true}}' --set screen --stages confirm,guards,elite,exploit,variants --variants
top_heavy,antes_from_level_3,fast_schedule,straddle --variant-seeds 200 --aim strong --workers 3`. O2 - F, paired;
0 errors, 0 timeouts (the candidate's p99 column, 8-10 ms, is the host at load 30-45; F's cells were played earlier).

| stage | cell | F | O2 | O2 - F | |
|---|---|---|---|---|---|
| confirm | night | 5.972 | 5.929 | -0.043 ± 0.072 | level |
| guards | night_hard | 5.499 | 5.591 | **+0.093 ± 0.084** | UP |
| | realistic | 6.370 | 6.334 | -0.036 ± 0.048 | level |
| | top | 5.058 | 5.039 | -0.019 ± 0.075 | level |
| | night @10/7/5..., @50/25/12..., doubling | | | -0.034 ± 0.130, -0.140 ± 0.886, -0.006 ± 0.075 | level |
| elite | elite | 4.865 | 4.918 | +0.052 ± 0.090 | level |
| | elite_night | 5.422 | 5.456 | +0.034 ± 0.074 | level |
| | **mirror** | 4.498 | 4.634 | **+0.137 ± 0.082** | UP |
| | elite_b | 4.638 | 4.709 | +0.071 ± 0.084 | level |
| | **mirror_b** | 4.466 | 4.669 | **+0.202 ± 0.091** | UP |
| exploit | exploit / exploit2 | 5.839 / 5.844 | 5.781 / 5.882 | -0.058 ± 0.133 / +0.038 ± 0.132 | level |
| | **exploit_hu** | 9.227 | 9.062 | **-0.165 ± 0.102** | DOWN |
| | **exploit_3** | 8.458 | 8.253 | **-0.205 ± 0.131** | DOWN |
| | exploit2_hu / exploit2_3 | 7.848 / 7.378 | 7.840 / 7.327 | -0.007 ± 0.064 / -0.052 ± 0.091 | level |
| | **exploit3** | 5.471 | 5.607 | **+0.136 ± 0.127** | UP |
| | exploit3_hu / exploit3_3 | 8.268 / 7.528 | 8.252 / 7.583 | -0.015 ± 0.059 / +0.055 ± 0.111 | level |
| | adapt / adapt_hu / adapt_3 | 5.889 / 8.605 / 8.007 | 5.878 / 8.545 / 7.948 | -0.010 ± 0.125 / -0.060 ± 0.080 / -0.058 ± 0.114 | level |
| variants | top_heavy (of 100) | 28.654 | 28.365 | -0.289 ± 0.640 | level |
| | **antes_from_level_3** | 6.496 | 6.434 | **-0.062 ± 0.052** | DOWN |
| | fast_schedule | 6.122 | 6.074 | -0.048 ± 0.051 | level |
| | **straddle** | 6.412 | 6.285 | **-0.127 ± 0.053** | DOWN |

**O2: REJECT** (exploit_hu, exploit_3, antes_from_level_3, straddle down). It does what the brief asked at strong
tables: mirror +0.137 and mirror_b +0.202 (the `prior` arm's +0.147 and +0.210), every strong point estimate positive,
night_hard up, realistic and top level, where the `prior` arm and T3 lost. The losses are elsewhere:
- Exploiter 1 heads-up and three-handed: there the blinds are most of the table and the button's raise-first-in is the
  hand's main source of chips; a capped read gives some of it up to a bot that defends.
- straddle: the straddle is posted outside the history, so the scan sees no first-in raise there and the layer (the
  only part that plays a straddle table's preflop; Hero plays the rest) reads every seat at the priors.
- antes_from_level_3: antes make a steal worth more, so the same drop in fold equity costs more.

Latency (per-call minimum, e54c827): act p99 108.6 / 113.6 µs (realistic / elite), hand end p99 143.8 / 143.4, mean
+1 to +2 µs over F. Targeted tests (s16b, API card, ship): 33 passed.

**O3 amended before it ran (08:35):** O2 + four or more alive + the read off on straddle tables (code aafe5b9: the
first two by construction leave the heads-up and three-handed cells and straddle exactly F's; a test each). Screened
at 2 workers, in this order: elite; the four 8-max exploit cells; antes_from_level_3, fast_schedule, top_heavy;
confirm and guards; then one 25-seed chunk of each cell that should be F's exactly (the eight short-handed exploit
cells and straddle), compared sample for sample.

## 08:35-08:50: O3's code (cc3a491 the four-alive gate, aafe5b9 straddle off), identity, latency

Identity (idcheck5.py: the branch with the dials off against main 64b466a's 31 cells from 06:06): **all 31
identical**; F's cells copied to version 9549c8efee (key 9ea319a2ced4). Latency (per-call minimum, aafe5b9): act p99
109.6 / 111.0 µs (realistic / elite), hand end p99 147.0 / 139.7, first act max 141.5. Tests (s16b including the
four-alive and straddle tests, API card, ship, compose): 56 passed. (The first launch of O3's screen failed at once:
the stage wrapper's module was not importable by the pool's workers; fixed, relaunched 08:52 at 2 workers.)

## 08:52-09:23: O3's elite stage (version 9549c8efee, screen 10000-10199 x 8, 2 workers)

| cell | F | O3 | O3 - F | | O2 |
|---|---|---|---|---|---|
| elite | 4.865 | 4.896 | +0.030 ± 0.087 | level | +0.052 |
| elite_night | 5.422 | 5.447 | +0.026 ± 0.073 | level | +0.034 |
| **mirror** | 4.498 | 4.602 | **+0.105 ± 0.083** | UP | +0.137 |
| elite_b | 4.638 | 4.713 | +0.075 ± 0.082 | level | +0.071 |
| **mirror_b** | 4.466 | 4.663 | **+0.197 ± 0.092** | UP | +0.202 |

The four-alive gate keeps nearly all of O2's strong-table gain: it was made at four or more alive.

O3's 8-max exploit cells (`EXPLOIT_CELLS=exploit,exploit2,exploit3,adapt oaccept.py --stages exploit`):

| cell | F | O3 | O3 - F | | exploiter's points F / O3 |
|---|---|---|---|---|---|
| exploit (exploiter 1) | 5.839 | 5.757 | -0.082 ± 0.125 | level | 4.608 / 4.707 |
| exploit2 | 5.844 | 5.891 | +0.047 ± 0.131 | level | 5.086 / 5.001 |
| **exploit3** | 5.471 | 5.602 | **+0.131 ± 0.126** | UP | 5.306 / 5.173 |
| adapt (adapt1) | 5.889 | 5.864 | -0.024 ± 0.123 | level | 5.106 / 5.083 |

O3's structural variants (realistic, 200 seeds; straddle is F's by construction, checked below):

| cell | F | O3 | O3 - F | | O2 |
|---|---|---|---|---|---|
| **antes_from_level_3** | 6.496 | 6.436 | **-0.060 ± 0.051** | DOWN | -0.062 ± 0.052 |
| fast_schedule | 6.122 | 6.077 | -0.045 ± 0.052 | level | -0.048 |
| top_heavy (of 100) | 28.654 | 28.274 | -0.380 ± 0.634 | level | -0.289 |

O3's confirm and guards:

| cell | F | O3 | O3 - F | | O2 |
|---|---|---|---|---|---|
| night | 5.972 | 5.941 | -0.031 ± 0.070 | level | -0.043 |
| **night_hard** | 5.499 | 5.584 | **+0.085 ± 0.084** | UP | +0.093 |
| realistic | 6.370 | 6.336 | -0.034 ± 0.048 | level | -0.036 |
| top | 5.058 | 5.037 | -0.021 ± 0.074 | level | -0.019 |
| night @10/7/5..., @50/25/12..., doubling | | | -0.011 ± 0.130, -0.229 ± 0.854, +0.001 ± 0.075 | level | |

The cells O3 plays exactly as F by construction, one 25-seed chunk each against F's cached chunk (`idchunk.py`):
exploit_hu, exploit_3, exploit2_hu, exploit2_3, exploit3_hu, exploit3_3, adapt_hu, adapt_3 and straddle: **all
identical sample for sample**.

**O3's verdict:** every strong point estimate positive (mirror and mirror_b beyond noise up), night and every guard
level or up, the 12 exploit cells level or up (8 of them F's exactly), and **one cell down: antes_from_level_3
-0.060 ± 0.051**. By the brief's rule (nothing beyond noise down) O3 is not kept; under addendum 7 a lone variant cell
down is a REPLICATE on the next held-out set at 400 seeds, not a reject. The realistic room leans the same way in
every cell that uses it (realistic -0.034, fast_schedule -0.045, antes -0.060, top_heavy -0.38 of 100), so a
replication may well confirm the loss: F's steals against realistic's folders pay, and the big blind's prior (0.668,
pooled) sits far under realistic's 0.80 until 20 or so answers move the table rate.

# S16c: O4, a faster table rate (branch climb/s16c-o4 from main cbaaab6)

The coordinator (10:00): screen O4 = O3 + `"r3.oa_st": 10` (the one value, fixed in advance), every stage at full
seeds, from a fresh worktree of main, 2 workers. The question: does the realistic room's lean (antes_from_level_3
-0.060 down; realistic, fast_schedule and top_heavy negative) go while the strong-table gains stay? The layer has no
table rate of its own: `exploit.open_read` reads rival 3's core's `oa_fold`, so `r3.oa_st` sets both. With the big
blind's prior worth 10 answers instead of 20, realistic's big blind (0.80 against the prior's 0.668) is read at about
0.73 after 10 answers instead of 0.71.

Spec: `{"r3.oa_read": true, "exploit.open_read": true, "r3.oa_cap": true, "exploit.open_cap": true,
"r3.oa_min_alive": 4, "exploit.open_min_alive": 4, "r3.oa_st": 10.0}`. No code change (main 0ed102a6ef carries O3's
code and other merges since: S18's tooling, H6, V-i); F's identity at main against the cached F checked first.

Identity (10:05-10:25; idcheck6.py, main 0ed102a6ef against the cells of 64b466a): **all 31 identical** sample for
sample. (Main's climb_accept now names a short last chunk `*.n15.json`; the script first flagged the seven 15-seed
chunks as missing and they were compared by hand: identical.) F's cells copied to main's key 2ff4eef35075. O4's
screen from 10:27, 2 workers: elite, the four variants, confirm and guards, the 12 exploit cells, then one call that
prints the whole table from the cache.

O4's elite stage (O4 - F; O3 beside it): elite +0.030 ± 0.086 (O3 +0.030), elite_night +0.062 ± 0.072 (+0.026),
**mirror +0.095 ± 0.080 UP** (+0.105), elite_b +0.075 ± 0.080 (+0.075), **mirror_b +0.177 ± 0.089 UP** (+0.197).

O4's variants (realistic, 200 seeds): **antes_from_level_3 -0.056 ± 0.050 DOWN** (O3 -0.060), **fast_schedule -0.060
± 0.047 DOWN** (O3 -0.045, level), top_heavy -0.040 ± 0.668 of 100 (O3 -0.380), straddle +0.000 ± 0.000 (identical
by construction). The faster table rate does not remove the realistic lean.

O4's confirm and guards: night -0.032 ± 0.068 (O3 -0.031), night_hard +0.064 ± 0.081 (O3 +0.085 UP), realistic
-0.026 ± 0.051 (-0.034), top +0.004 ± 0.076 (-0.021), night @10/7/5... -0.000 ± 0.121, @50/25/12... -0.560 ± 0.822 (of
100), doubling +0.002 ± 0.074: all level.
