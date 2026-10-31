# Kit A rubric: class-based `Agent.act(state) -> str`

What a correct adapter must translate. Each line is a trap that has cost someone a drill.

| Kit A | Ours (`Observation` / `Action`) | Trap |
|---|---|---|
| `state.hand`, `state.community` are strings like `"Ah"`, `"10d"` | ints 0..51 via `parse_card` | ten is `"10"`, two characters of rank; `parse_card("10d")` is wrong, map `"10"` to `"T"` first |
| `state.street` is `"preflop"/"flop"/"turn"/"river"` | `street` 0..3 | string, not an int |
| `state.my_index`, `state.dealer_index` | `seat`, `button` | same numbering (0..n-1), but it is an index into `players`, not a position relative to the button |
| `state.players[i].stack` / `.bet` / `.folded` | `stacks[i]` / `bets[i]` / `in_hand[i]` | `folded` is the inverse of `in_hand`; a busted player (stack 0, no bet, folded) stays in the list |
| `state.pot_size` | `pot` | **includes this street's bets**; ours excludes them: `pot = pot_size - sum(bets)` |
| `state.current_bet`, `state.my_bet` | `to_call = min(current_bet - my_bet, my_stack)` | to_call is capped by your stack |
| `state.legal_moves` strings `"FOLD"/"CHECK"/"CALL"/"RAISE"` | `legal` frozenset of `ActionKind` | uppercase; `"RAISE"` is bare, the range lives in `min_raise`/`max_raise` |
| `state.min_raise`, `state.max_raise` | `min_raise`, `max_raise` | both are raise-to **totals**, same as ours (the one place this kit is kind) |
| `state.hand_number`, `state.small_blind`, `state.big_blind` | `hand_no`, `blinds` | - |
| `state.action_log` `(index, "CALL" / "RAISE:120")` | `history` `(seat, Action)` | optional; parse lazily or skip |
| return `"FOLD"`, `"CHECK"`, `"CALL"`, `"RAISE:<total>"` | `Action.kind`, `Action.amount` | the string must be exact; `"RAISE: 120"` with a space is garbage to this kit |
| `Agent.new_game(my_index, n_players, starting_stack)` | `Bot.new_table(rules, seat, n_players)` | build `Rules()` from the blinds you see; the kit tells you nothing about the variant |
| `Agent.hand_over(hand_number, chip_change)` | `Bot.hand_end(HandResult)` | no showdown info here; opponent modeling must come from `action_log` |

Budget: 1 ms wall-clock per `act` call measured around the call. Exceptions, slow calls and illegal
actions are auto-folded (checked when possible) and counted. The runner passes when there are no
exceptions, no illegal actions and timeouts within 1% of decisions.

Run: `python -m hyperion.drills.fakekits.kit_a.runner submission.py`
