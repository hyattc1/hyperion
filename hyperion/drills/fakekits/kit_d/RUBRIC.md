# Kit D rubric: MIT Pokerbots style Bot, 8 seats, socket

| Kit D | Ours | Trap |
|---|---|---|
| `class Player(Bot)` with `handle_new_round`, `get_action`, `handle_round_over`, each `(game_state, state, active)` | `new_table`, `act`, `hand_end` | `active` is your seat and is passed every call; there is no separate start hook, so start the bot lazily on the first call |
| `GameState(bankroll, game_clock, round_num)` | `hand_no` | `round_num` is 1-based: `hand_no = round_num - 1`. `game_clock` is seconds left for the whole game |
| `RoundState.street` in `{0, 3, 4, 5}` | `street` 0..3 | it is the board size, not an index |
| `pips`, `stacks` (8 each) | `bets`, `stacks` | same meaning; `to_call = min(max(pips) - pips[active], stacks[active])` is yours to compute |
| `in_hand` (8 bools), `button` (dealer seat), `acting` (whose turn), `blinds` | `in_hand`, `button`, `blinds` | the real MIT `button` is a turn counter, not a seat; here it is the seat, read the kit |
| no pot field | `pot` | `pot = total_at_round_start - sum(stacks) - sum(pips)`; record `sum(stacks) + sum(pips)` in `handle_new_round` (or walk `previous_state` to the root). The MIT idiom is `STARTING_STACK - my_stack`, which is wrong here because stacks carry over |
| `hands[active]` is a list of card strings `['As', 'Td']`; other slots are `[]` until shown | `hole` via `parse_card` | at `handle_round_over`, `terminal_state.previous_state.hands` holds the shown hands |
| `legal_actions()` returns a **set of classes** `{FoldAction, CallAction, RaiseAction}` | `legal` | **`FoldAction` is absent when a check is free**; a fold there is illegal and becomes a check. `'fold' in legal` is always False (they are classes, not strings) |
| `raise_bounds()` -> `(min_raise_to, max_raise_to)` | `min_raise`, `max_raise` | raise-TO totals for the street; only meaningful when `RaiseAction` is legal; max is your all-in (the real MIT caps at the effective stack; follow the kit's bounds, never your own) |
| return an **instance**: `RaiseAction(total)`, `CallAction()`, `CheckAction()`, `FoldAction()` | `Action` | returning the class (`CheckAction`) or a string is illegal. The classes are in the legal set, so you never need to import them |
| your own action comes back in the next packet as history | - | the skeleton replays every action, yours included; do not apply it yourself |
| `TerminalState(deltas, previous_state)`, 8 deltas | `HandResult` | `deltas[active]` is yours; `bankroll` already includes it |
| socket: `python submission.py <port> [--host localhost]`, connect within 10 s | - | imports and warm-up before `run_bot`; the game clock starts at the first packet |
| one line per packet, one reply per packet, `K` acks `G` and `A` packets | - | a second reply desyncs the whole game; print logs to stderr only |
| unknown clause keys | - | ignore them; the real kit will have some |

Budget: pooled game clock of 1 ms x hands x 3 for the whole game, charged by wall-clock round trip
(about 100 us of socket overhead per packet, two acks per round included). A reply slower than 2 s
marks the bot dead; a negative clock makes every later action a fold and the engine stops talking.

Run: `python -m hyperion.drills.fakekits.kit_d.runner submission.py` (or a directory with
`commands.json` `{"run": ["python3", "player.py"]}`, MIT layout; the port is appended).

Adding kit D to `hyperion/drills/run.py` takes two edits: `KITS = ("a", "b", "c", "d")` and a branch in
`Drill.run_kit` before the kit C fallthrough:

```python
if self.kit == "d":
    mod = importlib.import_module("hyperion.drills.fakekits.kit_d.runner")
    return mod.run([sys.executable, str(sub)], hands, seed, budget_ms, hole_cards, cwd=str(self.scratch))
```
