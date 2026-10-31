# Kit B rubric: function-based `decide(observation: dict) -> dict`

| Kit B | Ours | Trap |
|---|---|---|
| `hand.cards[i]` = `{"rank": 2..14, "suit": "C"/"D"/"H"/"S"}` | int `(rank-2)*4 + "cdhs".index(suit.lower())` | rank is a number with ace = 14; suits are uppercase |
| `street` = number of board cards: 0, 3, 4, 5 | `street` index 0..3 | MIT-style; `street == 3` is the flop, not the river |
| `table.pot` | `pot` | previous streets only, same as ours; the current street lives in `players[].committed` |
| `table.players[i].chips` / `.committed` / `.active` | `stacks[i]` / `bets[i]` / `in_hand[i]` | `players` is ordered by seat but trust `player["seat"]`, not the list index |
| `table.button`, `you.seat` | `button`, `seat` | - |
| `you.to_call` | `to_call` | already capped by your stack |
| `you.min_raise_by`, `you.max_raise_by` | `min_raise`, `max_raise` | **increments** above the current highest bet: `min_raise = max(committed) + min_raise_by` |
| `actions` lowercase `["fold","check","call","raise"]` | `legal` | lowercase here, uppercase in kit A |
| return `{"action": "raise", "by": n}` | `Action.raise_to(total)` | convert back: `by = total - max(committed)`; `by` below `min_raise_by` is illegal, not clamped |
| return `{"action": "check"}` | `Action.check()` | returning `"check"` as a bare string is garbage |
| `on_table_start(info)` with `seat`, `players`, `stack`, `blinds` | `Bot.new_table(rules, seat, n)` | optional hook; the module is imported once per table |
| `on_hand_end({"hand_id", "delta"})` | `Bot.hand_end(HandResult)` | optional; no showdown info |

Budget: 1 ms wall-clock per `decide` call. Exceptions, slow calls and illegal results auto-fold.
Pass = no exceptions, no illegal actions, timeouts within 1% of decisions.

Run: `python -m snapcall.drills.fakekits.kit_b.runner submission.py`
