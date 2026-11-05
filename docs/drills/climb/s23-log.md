# S23: where F's first places go at strong tables (running log)

Branch climb/s23-firsts, worktree goal/wt_s23, from main 8d03ba0 (batch 8 is F). Brief (coordinator, 2026-11-04 late):
at the strongest held-out room F is third of eight on points, takes 1st 12.3% (an even share is 12.5%) against 18-22%
for the two best bots, busts more, and the gap doubles under 10/7/5/4/3/2/1/0 against 8..1. Decompose finish position
at the strong tuning rooms, price each leak in points, build the top one or two behind dials off by default, screen.

Rules kept here: held-out judges (out_reads, elite5, out_cfr, out_press, out_charts, out_o9/o10/o11, rival4, rival5,
adapt2) are never run, read or looked at. Diagnosis on tuning rooms only (elite, elite_b, mirror, mirror_b, top,
night, realistic; checked in hyperion/sim/bestiary.py: none seats a held-out bot). Diagnostic seeds 16000-16999;
screens 10000-10199. Any change sits behind dials off by default; identity with them off against batch 8
(goal/idchk39's rows). Plain hold'em only unless shown to help a twist. Last bot change Nov 10 18:00 ET; anything to
ship must pass its screen by Nov 9 12:00 ET.

Scratch: `goal/s23/` (recorder `d23.py`, analysis `a23.py`, recordings `rec_<field>_<pay>.jsonl.gz`, `run_d23.sh`).

## Runs (appended as each finishes)

- 2026-11-05 00:00 Step 1 recordings started (`run_d23.sh`, 3 workers, nice 5): d23.py plays each field as
  climb_accept seats it (seed 7, 8 rotations, model mode, F = SHIP_DIALS in the hero seat) hand by hand and records,
  per table-rotation, places, points, hands, the cap, the stacks when the alive count first reaches 4 / 3 / 2, every
  seat's bust (hand, alive count, blinds, its last action: street, kind, facing a bet or first in, players in hand)
  and F's compact action string (to compare F's play across payout tables on the same deals). Cells: elite, mirror,
  elite_b, mirror_b under 8..1, 10/7/5/4/3/2/1/0 and 50/25/12/6/3/2/1/1; top and night under 8..1 and
  50/25/12/6/3/2/1/1. Seeds 16000-16199 (200 x 8). About 0.36 s a table-rotation: about an hour in all.

## Step 1: the decomposition (diagnostic seeds 16000-16199, F = batch 8)

Tools: `goal/s23/d23.py` (the recorder), `a23.py` (finish decomposition; `--pay X` revalues 8..1 play under table X),
`flow.py` (points by stage: each seat's ICM value when the alive count first reaches 4 / 3 / 2, so the stage gains sum
to points over the mean), `diverge.py` (F's action strings across payout tables on the same deals).

**Finish decomposition, 8..1** (200 seeds x 8; "share@k" the seat's chip share when k are alive; "1st|k" its first
places given it was there; per-seed 95% intervals):

| room | bot | points | 1st % | 3rd % | bust % | reach 4 / 3 / 2 % | share @4 / @3 / @2 | 1st given 3 alive | 1st given 2 alive |
|---|---|---|---|---|---|---|---|---|---|
| elite | F | 4.810 ± 0.095 | 13.1 ± 1.4 | 14.8 | 83.2 | 56.1 / 42.2 / 26.9 | .243 / .323 / .480 | 33.9 ± 3.9 | 53.3 ± 5.3 |
| elite | elite1 | 4.401 ± 0.116 | 18.4 ± 1.7 | 6.8 | 79.4 | 45.6 / 34.0 / 27.0 | .284 / .388 / .576 | 56.6 ± 4.6 | 70.1 ± 4.9 |
| elite | elite2 | 4.613 ± 0.113 | 17.1 ± 1.9 | 11.8 | 80.6 | 50.1 / 38.9 / 26.9 | .261 / .365 / .561 | 42.1 ± 4.2 | 60.9 ± 5.3 |
| elite | rival2 | 4.955 ± 0.093 | 15.2 ± 1.6 | 15.8 | 79.7 | 59.1 / 47.1 / 30.4 | .247 / .314 / .477 | 33.5 ± 3.7 | 49.2 ± 4.9 |
| mirror | F | 4.511 ± 0.101 | 10.7 ± 1.6 | 13.7 | 85.9 | 49.2 / 36.2 / 22.2 | .240 / .317 / .484 | 29.8 ± 4.4 | 44.4 ± 5.9 |
| mirror | elite1 | 4.314 ± 0.108 | 20.0 ± 1.8 | 7.4 | 78.4 | 44.3 / 35.6 / 27.1 | .304 / .407 / .623 | 57.5 ± 4.7 | 70.0 ± 5.0 |
| mirror | elite2 | 4.416 ± 0.106 | 16.2 ± 1.8 | 10.6 | 82.2 | 47.1 / 35.9 / 24.8 | .287 / .394 / .573 | 45.2 ± 4.6 | 64.5 ± 5.4 |
| elite_b | F | 4.749 ± 0.092 | 11.9 ± 1.5 | 14.4 | 84.2 | 55.4 / 40.2 / 25.1 | .241 / .319 / .466 | 31.3 ± 4.1 | 45.2 ± 5.5 |
| elite_b | elite1 | 4.326 ± 0.113 | 17.3 ± 1.7 | 9.4 | 81.0 | 45.4 / 34.9 / 24.8 | .283 / .388 / .568 | 50.1 ± 4.4 | 69.5 ± 4.9 |
| elite_b | elite2 | 4.535 ± 0.115 | 17.8 ± 1.9 | 10.2 | 80.8 | 47.7 / 36.4 / 25.4 | .290 / .387 / .591 | 48.0 ± 4.5 | 67.9 ± 5.2 |
| mirror_b | F | 4.535 ± 0.100 | 10.8 ± 1.6 | 15.0 | 86.0 | 50.7 / 37.6 / 22.4 | .236 / .314 / .484 | 28.5 ± 4.0 | 45.5 ± 5.9 |
| mirror_b | elite1 | 4.309 ± 0.110 | 19.0 ± 1.8 | 7.2 | 79.8 | 44.9 / 35.6 / 27.7 | .314 / .423 / .607 | 52.4 ± 4.3 | 67.3 ± 4.8 |
| mirror_b | elite2 | 4.416 ± 0.118 | 18.6 ± 1.9 | 9.2 | 80.0 | 46.8 / 35.9 / 26.6 | .285 / .393 / .579 | 53.2 ± 4.8 | 71.3 ± 4.9 |

Hands to reach 4 / 3 / 2 alive: 112-128 / 131-144 / 148-162 for every bot (no difference). The cap: 20-27% of
tables (nearly all with two alive, 10% with three); F's first-place share on cap tables equals its share elsewhere
(elite 14.4 vs 12.6, mirror 10.3 vs 10.8), the elites' is lower on cap tables than off (elite1 11.1 vs 21.3): the cap
takes first places from the bots that would win heads-up, not from F. Every chip leader at the cap is placed first.

**Reading.** F reaches four and three alive as often as anyone (more than the elites) but arrives short: 0.24 of the
chips at four alive (an even share is 0.25), 0.32 at three (0.33), 0.48 heads-up; elite1 arrives with 0.28-0.31 /
0.39-0.42 / 0.57-0.62. From three alive F converts to first at its chip share (29.8-33.9% on 0.31-0.32 of the chips)
and busts third 35% of the time; elite1 converts at 50-57% on 0.39-0.42 (+13 to +18 points over its chips) and busts
third 21%. Heads-up F wins about its chip share (44-53% on 0.47-0.48), elite1 +8 to +12 over its chips. So F's first
places go to **conversion, not to reaching the endgame**: about a third of the conversion gap is chips on arrival
(F is the survivor that arrives short) and two thirds is play with three or two left, relative to the chips held.
F's bust anatomy is the mirror image of the elites': 53-58% of F's busts come with 5-8 alive against 65-68% of
elite1's; F busts with 2-4 alive 47% of the time, elite1 32%. 86% of F's busts are preflop all-ins (72% as the
raiser or re-raiser, 24% calling); the elites' are similar (73-74% / 19%), so nothing in how F busts stands out.

**Points by stage** (`flow.py`; each seat's gain in ICM value from the start to four alive, through four alive, three
alive and heads-up, per seat, per-seed intervals; the sum is points over the table mean):

| room, payouts | bot | start to 4 alive | 4 alive | 3 alive | heads-up | total | 3 alive per arrival | heads-up per arrival |
|---|---|---|---|---|---|---|---|---|
| elite 8..1 | F | +0.307 ± 0.091 | +0.010 ± 0.026 | -0.004 ± 0.019 | -0.004 ± 0.009 | +0.310 | -0.008 | -0.013 |
| elite 8..1 | elite1 | -0.155 ± 0.111 | -0.019 ± 0.025 | +0.050 ± 0.017 | +0.025 ± 0.010 | -0.099 | +0.146 | +0.094 |
| elite 8..1 | elite2 | +0.045 | +0.038 | +0.012 ± 0.020 | +0.018 ± 0.010 | +0.113 | +0.030 | +0.067 |
| elite 10/7/5 | F | +0.360 ± 0.117 | +0.047 ± 0.049 | +0.020 ± 0.047 | +0.017 ± 0.030 | +0.443 | +0.047 | +0.057 |
| elite 10/7/5 | elite1 | -0.175 | +0.006 | +0.071 ± 0.046 | +0.055 ± 0.029 | -0.043 | +0.205 | +0.216 |
| elite 10/7/5 | elite2 | +0.053 | +0.071 | +0.024 ± 0.049 | +0.056 ± 0.028 | +0.204 | +0.063 | +0.211 |
| elite 50/25/12 | F | +1.96 ± 0.57 | +0.45 ± 0.33 | +0.54 ± 0.34 | +0.21 ± 0.26 | +3.17 | +1.22 | +0.66 |
| elite 50/25/12 | elite1 | -0.03 | +0.04 | +0.32 ± 0.35 | +0.40 ± 0.22 | +0.74 | +0.89 | +1.60 |
| mirror 8..1 | F | +0.025 ± 0.097 | -0.002 ± 0.025 | -0.008 ± 0.018 | -0.004 ± 0.008 | +0.011 | -0.022 | -0.018 |
| mirror 8..1 | elite1 | -0.264 | +0.015 | +0.049 ± 0.018 | +0.014 ± 0.011 | -0.186 | +0.138 | +0.050 |
| mirror 10/7/5 | F | +0.114 ± 0.120 | +0.004 ± 0.047 | -0.038 ± 0.043 | -0.018 ± 0.030 | +0.063 | -0.099 | -0.075 |
| mirror 10/7/5 | elite1 | -0.325 | +0.024 | +0.072 ± 0.041 | +0.068 ± 0.029 | -0.161 | +0.215 | +0.273 |
| mirror 10/7/5 | elite2 | -0.174 | +0.025 | +0.098 ± 0.041 | +0.042 ± 0.031 | -0.009 | +0.283 | +0.159 |
| elite_b 8..1 | F | +0.270 ± 0.089 | -0.011 | -0.005 ± 0.019 | -0.004 ± 0.009 | +0.249 | -0.014 | -0.014 |
| elite_b 8..1 | elite1 | -0.206 | -0.003 | +0.012 ± 0.017 | +0.024 ± 0.009 | -0.174 | +0.033 | +0.095 |
| elite_b 10/7/5 | F | +0.313 ± 0.117 | +0.009 | -0.022 ± 0.043 | +0.023 ± 0.031 | +0.324 | -0.052 | +0.086 |
| elite_b 10/7/5 | elite1 | -0.253 | -0.005 | +0.025 ± 0.041 | +0.060 ± 0.029 | -0.172 | +0.075 | +0.255 |
| mirror_b 8..1 | F | +0.048 ± 0.096 | +0.011 | -0.019 ± 0.019 | -0.005 ± 0.009 | +0.035 | -0.050 | -0.023 |
| mirror_b 8..1 | elite1 | -0.240 | +0.005 | +0.033 ± 0.016 | +0.011 ± 0.010 | -0.191 | +0.093 | +0.039 |
| mirror_b 10/7/5 | F | +0.092 ± 0.124 | +0.024 | -0.076 ± 0.044 | -0.019 ± 0.028 | +0.021 | -0.195 | -0.080 |
| mirror_b 10/7/5 | elite1 | -0.225 | +0.016 | +0.066 ± 0.042 | +0.048 ± 0.030 | -0.096 | +0.187 | +0.184 |
| mirror_b 10/7/5 | elite2 | -0.172 | +0.014 | +0.014 ± 0.044 | +0.060 ± 0.028 | -0.084 | +0.040 | +0.253 |

**Where the points are.** All of F's gain at a strong table is made from the start to four alive (+0.25 to +0.31 at
elite and elite_b under either table; the elites lose 0.16-0.33 there). With four, three or two left F is level under
8..1 (-0.00 to -0.02 a stage) and **loses under 10/7/5/4/3/2/1/0: three alive -0.04 to -0.08 a seat (-0.05 to -0.20
per arrival), heads-up -0.02** (mirror, mirror_b, elite_b; elite +0.02). The elites gain +0.05 to +0.10 three-handed
and +0.04 to +0.07 heads-up under that table. Under 50/25/12/... F's three-handed play is the best in the room
(+0.54; elite2 prices that table as 10/7/5, its ICM is hard-coded).

**Points on the table per leak** (F's seat, a strong table, F to elite1's level in that stage):
1. Three alive: 8..1 +0.05 to +0.06; 10/7/5 **+0.11 to +0.14**; 50/25/12 nothing (F ahead). The biggest.
2. Heads-up: 8..1 +0.02 to +0.03; 10/7/5 **+0.07 to +0.09**; 50/25/12 +0.2 on that scale (about +0.07 on 8..1's).
   H1 (climb/s20-h1, solved heads-up per seat) is the line already open on this; its screen never ran to the end
   (the old session died with H1_screen.md empty).
3. Four alive: F level, elite2 and rival2 +0.04 to +0.08 under 10/7/5: at most +0.05.
4. Chips on arrival (accumulation 8 to 4 alive): F is already the best bot in the room at this stage (+0.3); making
   it arrive with more chips means risking the stage that carries its whole margin. Not a leak to fix; a trade.

**Does F play differently under a top-heavy table, and should it?** Yes and yes. Same deals, F's actions diverge from
its 8..1 play on 79% of table-rotations under 50/25/12 (first difference at hand 77 median, 8 alive on a third of them)
and 50% under 10/7/5 (hand 105 median, mostly 4-6 alive). Revaluing F's 8..1 play under the other tables: elite 4.342
against 4.443 played under 10/7/5 (+0.10 from adapting), 13.53 against 15.67 under 50/25/12 (+2.1). Its first places
rise with the table: 13.1% (8..1), 15.8% (10/7/5), 19.0% (50/25/12) at elite, where under 50/25/12 it leads the
room (15.67; rival2 14.85, elite1 13.24).

**So the gap at 10/7/5 the coordinator saw at the held-out room reproduces in kind at the tuning rooms**: F's whole
margin is the 8-to-4-alive stage; with three left it gives ICM value back under a 10/7/5-shaped table, where the
elites take it. Next: the three-handed hands themselves (step 2, `d3b.py` on 16200-16319 under 8..1 and 10/7/5),
booked by spot in ICM points, to find which seat and decision loses.
