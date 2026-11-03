# S16b: reading how each seat answers our own opens (running log)

Branch climb/s16b-open-answer, from main 64b466a (S16 merged, its dials off). Brief (coordinator, 2026-11-03): S16's
next step. A per-seat read of how each seat answers F's own first-in raises (fold, call, re-raise), in place of the
pooled fold-to-a-raise in rival 3's steal price, and in the layer's steal read if it has the same bias; a fold prior
near 0.70-0.75 fixed from a survey of the pooled fields before screening, with the trust floor on small samples; hold'em
tables only plus whatever gate the survey supports; screen `--aim strong` (elite, confirm, guards, all 12 exploit
cells, variants). The target: S16's `prior` arm (+0.14 to +0.21 at strong tables, but it lost on realistic and
top_heavy when gated) without the losses.

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
