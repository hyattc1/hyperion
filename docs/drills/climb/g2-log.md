# G2: Hero's profiler at `bare`

Branch climb/g2-bare from climb/batch9 6db96fe. Raw runs: goal/g2/. Seeds 21000-21999 only; no held-out set, no judge.

## Root cause (forced `bare`, model mode, seeds 21000 x rotations, 40 tables)

A ghost profiler beside the hero member's (goal/g2/ghost.py; nothing on the branch changes), fed every decision and hand end as level 0's light shadow feeds the real one, on the same hands. At level 0 the two match on
every counter (the control). At level 1, F, against the ghost:

| counter | elite real / ghost | exploit2_hu real / ghost |
|---|---|---|
| `rr_by` | 42 / 1,646 | 17 / 304 |
| `rr_n` (my first-in raises) | 2,283 / 6,975 | 509 / 1,325 |
| `open_opp` / `opens` | 20,111 / 118,507; 7,755 / 35,624 | 998 / 3,982; 996 / 3,319 |
| `shoves` | 992 / 9,199 | 18 / 347 |
| `faced_shove` | 1,530 / 19,593 | 18 / 347 |
| `fi_shove_b` | 1 / 4,991 | 0 / 99 |
| `hands` | 260,430 / 262,113 | 7,451 / 8,140 |

With no shadow Hero's profiler is fed only when Hero itself is chosen, so on a hand Hero never decides it meets the hand only at `hand_end`, in the blank pass written for hands we were not in: `chips` all zero, no blinds, no button, `pre_order_known` False, and `hands` counted only for seats in the history.
- `amt < chips * 0.95` is never true, so `rr_n` and `rr_open` never start: **`rr_by` starves. The staging worker's reading was right.** The same zero chips end `shoves`, `faced_shove`, the shove buckets.
- `ctx == 1 and b >= 1 and pre_order_known` is never true, so `open_opp` and `opens` starve.
- **S7's drop is the same pass, by two routes.** Asked at each `wants` where the real read and the ghost's differ (exploit2_hu, F): `like_vpip` refuses in 809 preflop and 1,361 postflop decisions the ghost admits, `pre_open_min` in 617. A seat's walks (we fold the button) are not in the history, so `hands` falls, its VPIP reads over `like_vpip_max` 0.88 and the gate shuts. The opens that do count come from hands that reached a flop, 996 of 998, and `open_rate` sits at its prior 0.5 under `pre_open_min` 0.65 until enough have.
- R6 at elite, F: all 217 refusals the ghost would have passed are `seat_rr`.

## The fix

`bare_reads`, a composite dial, off. At a level with no shadows where Hero is not every section's donor (levels 1 and 2 of `bare,lean,hero`), `CompositeCore.act` appends the observation to `Profiler.pend_obs`, one list append. The profiler feeds them at Hero's next decision or at the hand's end, before anything else there.
The reads then equal level 0's on every counter at every hand end, one hand later inside a hand. A first version kept only the hand's first observation (cheaper by about 4 us a hand end at 1x, in process) but its shove counts ran 8% off level 0's: closer to the truth, but not what anything was tuned on. Not kept.
