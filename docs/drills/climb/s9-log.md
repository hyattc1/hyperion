# S9 + S10: F at strong tables (mirror field, first-place conversion)

Branch climb/s9-strong-tables, from main 77d8932. Protocol: docs/drills/goal-plan.md section 2 and addendum 8 (a
strong-table change is accepted on a held-out set when it is beyond noise up on at least one of elite, elite_night or
mirror and beyond noise down on nothing else). This worker screens only: seeds 10000-10199 (`--set screen`) and fresh
seeds under 10000 for diagnostics; the coordinator runs the held-out confirmation. No judge bot, judge field or held-out
variant is run, read or tuned on here.

## 1. The mirror field

- `f_copy` (hyperion/sim/bestiary.py, ShipCopy): a copy of F as it ships (SHIP_DIALS, light shadows, the bestiary's
  model-mode settings through compose.bot.sim_kwargs, the same helper tools/swap.py's registered seats now use). It
  follows SHIP_DIALS, so when the ship changes the copies change with it.
- `mirror` = hero, f_copy x3, rival2, elite1, elite2, hybrid3_x (the strongest general bots we may tune on, F's own
  base among them).
- `mirror_night` = hero, f_copy x2, elite1, elite2 and elite_night's first three drawn night seats (diagnostic).
- climb_accept's elite stage now measures elite, elite_night and mirror.
- Copies of one bot at one table: the runner builds every seat its own instance with its own seed
  (table_seed * 64 + rotation * 8 + seat). tests/test_sim_mirror.py replays each of three copies alone, in a fresh
  instance with its seed and the observations it saw at the table, and every decision matches, so no copy's play
  depends on another's state; the field replays exactly in model mode; points sum to 36 a table.
- Cost: about 2.3 s per seed (8 rotations) in one process, about twice elite.
