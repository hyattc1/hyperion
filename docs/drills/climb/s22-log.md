# S22: the river over-fold exploiter 4 found (running log)

Branch climb/s22-river, from main 7a352ba (batch 7 is F). Brief (coordinator, 2026-11-04 11:40): exploiter 4
(docs/drills/exploiter4/NOTEBOOK.md, F9) finds that F folds 66-81% to a 0.7-pot river bet heads-up (break-even
about 41%) and does not adapt. Diagnose on seeds 15000-15999 only, fix behind dials that are off by default, screen
on 10000-10199 with `--aim exploit`. No held-out set, judge set, judge bot or judge field is run, read or tuned on
(20000-60799 untouched). Workers 2, nice 5, detached runs with done-files.

**Where I am / next:** diagnosis running (scratch `goal/s22/diag.py`, `ana.py`); next: the read's prior and gate
from it, then the code.

## Diagnosis (seeds 15000-15199 heads-up and three-handed, 15000-15079 x 8 at 8-max; F = batch 7, model mode)

Scratch `goal/s22/diag.py` records every postflop decision of every seat in hands F plays, with the simulator's
cards, F's route and its reads of the bettor; `ana.py` takes heads-up pots (two players in the hand) on a street.
"F wins" is F's share of the pot at showdown against the bettor's actual cards (river), or its equity over every
river card (turn), whether or not the hand went to showdown. "Price" is the call's share of the final pot.

### 1. Exploiter 4 heads-up and three-handed (river)

