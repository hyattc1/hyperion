# O8s: why O8's veto lost fast_schedule, and whether a scope exists (branch climb/o8s from climb/b8-o8)

**Result: no sound scope; O8 stays rejected. No rule built, no screen run, nothing for H38.** `hyperion/` and `tools/` are
unchanged from climb/b8-o8, so no identity run was needed. Scripts and raw output: goal/o8s/.

Brief: O8 rejected on fast_schedule (realistic), -0.055 ± 0.043 on H35, -0.039 ± 0.032 on H37. The coordinator's guess: the
veto is wrong at shallow depth, so a depth gate would be general and would also protect the night if its unpublished
schedule is faster. Test the guess; scope only if the diagnosis supports it. Diagnostic seeds 17000-17999 only.

## The two instruments

1. **The randomised veto** (goal/o8s/o8s_rct.py). Batch 8 + O8 plays; wherever the veto would fire, a fair coin (its own
   stream) applies it or lets the open stand. Value = veto arm - open arm, hand-end ICM points against the fold state,
   times firings a table, bootstrapped over seeds. Tight, but it stops at the end of the hand and plays a half-veto policy.
2. **The veto by arm, table for table** (goal/o8s/o8s_paired.py). The screen's own measure (corrected points, paired by
   seed) with the veto allowed only inside a filter, applied as a monkeypatch for the diagnosis. Sees everything after
   the hand too, with wider intervals.

The first collection was wrong and was thrown away: arms of 4,785 against 2,463, not 50/50, showed my collector dropped
every open that was called (it cleared the row at F's next action). Values of -0.05 a firing with tiny intervals were that
bug. Every table below is from the fixed collector; arms 4,877 / 4,908 and 4,408 / 4,407.

## The guess: depth

The veto's value in points, by effective depth (veto arm - open arm, per table, 17000-17999):

| depth | realistic, default | realistic, fast | night, default | night, fast | elite_night | mirror_b |
|---|---|---|---|---|---|---|
| 10-15 bb | -0.0042 ± 0.0078 | -0.0035 ± 0.0127 | -0.0023 ± 0.0121 | +0.0041 ± 0.0145 | +0.0129 ± 0.0155 | +0.0100 ± 0.0291 |
| 15-20 bb | -0.0031 ± 0.0075 | +0.0008 ± 0.0077 | +0.0068 ± 0.0092 | -0.0015 ± 0.0071 | +0.0119 ± 0.0116 | +0.0055 ± 0.0146 |
| 20-30 bb | -0.0005 ± 0.0054 | -0.0034 ± 0.0035 | -0.0026 ± 0.0031 | +0.0043 ± 0.0056 | +0.0023 ± 0.0063 | +0.0078 ± 0.0098 |
| 30-40 bb | +0.0011 ± 0.0054 | -0.0035 ± 0.0031 | +0.0025 ± 0.0052 | -0.0008 ± 0.0033 | +0.0014 ± 0.0054 | +0.0020 ± 0.0056 |
| 40-60 bb | -0.0045 ± 0.0034 | -0.0007 ± 0.0014 | -0.0007 ± 0.0017 | +0.0001 ± 0.0014 | +0.0006 ± 0.0043 | +0.0000 ± 0.0031 |
| over 60 bb | +0.0014 ± 0.0044 | +0.0017 ± 0.0032 | -0.0029 ± 0.0038 | -0.0034 ± 0.0036 | -0.0009 ± 0.0054 | +0.0072 ± 0.0066 |
| **all** | **-0.0098 ± 0.0148** | **-0.0091 ± 0.0152** | +0.0005 ± 0.0171 | +0.0030 ± 0.0189 | **+0.0281 ± 0.0211 UP** | +0.0336 ± 0.0352 |
| firings a table | 1.22 | 1.10 | 1.01 | 0.83 | 1.73 | 3.21 |

No depth gradient in the soft rooms at either schedule, and the same total at both. Where shallow does stand out, it is the
gain: most of elite_night's value is at 20 bb and under (+0.0248 of +0.0281).

The same split in table points (corrected; realistic 1,000 seeds, the rest 500):

| veto allowed | realistic | realistic, fast | night | night, fast | elite_night | strong family (5 cells) |
|---|---|---|---|---|---|---|
| everywhere | -0.0087 ± 0.0190 | **-0.0212 ± 0.0179 DOWN** | -0.0033 ± 0.0226 | **-0.0316 ± 0.0219 DOWN** | +0.0231 ± 0.0296 | **+0.0345 ± 0.0186 UP** |
| 20 bb and under | -0.0093 ± 0.0102 | **-0.0127 ± 0.0119 DOWN** | -0.0078 ± 0.0112 | -0.0043 ± 0.0123 | **+0.0236 ± 0.0151 UP** | **+0.0126 ± 0.0100 UP** |
| over 20 bb | (below) | (below) | +0.0061 ± 0.0213 | **-0.0266 ± 0.0201 DOWN** | +0.0164 ± 0.0286 | **+0.0347 ± 0.0181 UP** |
| 20-40 bb | -0.0016 ± 0.0112 | -0.0078 ± 0.0119 | | | | |
| over 40 bb | -0.0008 ± 0.0145 | -0.0066 ± 0.0122 | | | | |

**The guess does not hold.**
- On the rejected cell the loss per firing is flat across depth: -0.025 at 20 bb and under (0.50 firings a table), -0.021 at
  20-40 (0.37), -0.029 over 40 (0.23), using firing rates from instrument 1. Under 20 bb is 45% of the firings and 47% of the
  loss, so a depth gate removes loss only by removing firings.
- What the fast schedule adds over the default does not sit at shallow depth: realistic -0.003 / -0.006 / -0.006 at 20 and
  under / 20-40 / over 40 (each ± 0.015-0.018); night +0.003 ± 0.016 at 20 and under, -0.033 ± 0.028 over 20.
- So a depth gate would not protect the night under faster blinds: over 20 bb, fast night is still DOWN.
- It would cost elite_night, the strong cell closest to the night's room, about a third of its table points and most of its
  hand-end value, while the strong family as a whole holds.

## Is it the schedule at all?

The veto against batch 8 by blind pace, table for table:

| ladder | realistic (1,000 seeds; double 500) | night (500) |
|---|---|---|
| 25 hands a level (default) | -0.0087 ± 0.0190 | -0.0033 ± 0.0226 |
| 20 | -0.0227 ± 0.0190 DOWN | |
| 15 (fast_schedule) | -0.0212 ± 0.0179 DOWN | -0.0316 ± 0.0219 DOWN |
| 10 | -0.0059 ± 0.0183 | -0.0106 ± 0.0218 |
| doubling ladder, 25 a level (as fast as fast_schedule) | -0.0065 ± 0.0257 | +0.0022 ± 0.0214 |
| pooled | **-0.0137 ± 0.0087** | -0.0108 ± 0.0110 |
| homogeneity chi-square | 2.80 on 4 df | 5.29 on 3 df |

There is no dose response: the fastest ladder and the doubling ladder lose least. So a gate on pace (hands per level, read
from Rules or from the blinds seen) has no support either. It would make the fast_schedule cell identical by construction
while the leak stays in the room; that hides the loss from the test without removing it.

**Diagnosis.** O8 has a real, small leak in ordinary rooms, about -0.014 a table in realistic at every ladder, roughly in
proportion to how often it fires. fast_schedule failed twice because that leak sat near the edge of the cell's interval;
H35's -0.055 and H37's -0.039 are larger than the 1,000 fresh seeds' -0.021. Not excluded: a fast-specific extra cost.
Fast minus default, paired by seed, is -0.0125 ± 0.0249 in realistic and -0.0283 ± 0.0301 at night (about -0.019 ± 0.019
pooled), and hand-end ICM sees none of it (table points fall short of it at fast, -0.021 against -0.009 and -0.032 against
+0.003, and agree at the default). That is the coordinator's "blinds bite" in another form: a cost after the hand. But it
does not sit at shallow depth and does not grow with pace, so I have no gate for it.

## Other gates looked at

- **Alive count:** flat in the soft rooms at both schedules; the one flagged row (5 alive, realistic fast, -0.0101 ± 0.0093)
  is not repeated at night. The strong gain leans to 4-5 alive at elite_night. Nothing separates the rooms. Hand-end only:
  the filter cannot see alive, and I did not run a table arm.
- **The switch's rate and answers:** no separation by rate between rooms. Answers (read maturity): 30-60 answers is -0.0150 on
  realistic fast but +0.0068 on night fast, so not a mechanism.
- **Hand band:** the one cut that repeated on both halves of the seeds. p 0.1-0.3 in realistic: -0.0072 / -0.0049 default,
  -0.0181 / -0.0133 fast (not in night or the strong rooms). It came from about 45 cuts, so I tested it table for table before
  believing it: veto everywhere except p 0.1-0.3:

  | realistic | realistic, fast | night | night, fast | elite_night | elite | elite_b | mirror | mirror_b |
  |---|---|---|---|---|---|---|---|---|
  | -0.0093 ± 0.0129 | -0.0099 ± 0.0129 | -0.0158 ± 0.0159 | **-0.0170 ± 0.0153 DOWN** | +0.0112 ± 0.0195 | -0.0137 ± 0.0254 | -0.0065 ± 0.0297 | -0.0051 ± 0.0325 | +0.0051 ± 0.0310 |

  It keeps the leak and loses the strong gain. Rejected. Its complement (veto only at p 0.1-0.3) looks better by subtraction,
  but that is a further post-hoc look against the hand-end reading, and with the leak in proportion to firings it would only
  scale it. Not tried: that would be the sweep the brief rules out.

## The closest thing to a scope, not built

Veto only over 20 bb. On these seeds it looks better than O8 in most cells: realistic about -0.002 (sum of arms), realistic
fast about -0.014, night +0.006, strong family +0.035 ± 0.018. I do not count it as supported: its gain is fewer firings
rather than a cause removed, fast night stays DOWN, elite_night falls from +0.023 to +0.016, and instrument 1 shows no depth
effect to justify it. It would also probably pass the fast_schedule cell on size alone. The rule was to fix one from the
diagnosis, and the diagnosis does not point here.

## Left for the coordinator

Rejected stays rejected. What remains is a weighing rather than a scope: O8 gives about +0.03 at strong tables for about -0.014
in the ordinary room (H35 W +0.0048 ± 0.0087). Nothing here changes that trade or addendum 7's verdict.
