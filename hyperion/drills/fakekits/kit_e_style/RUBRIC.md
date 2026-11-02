# Fake event kit (kit_e_style) rubric: events in, a move out, no state snapshot

| Kit | Ours | Trap |
|---|---|---|
| `on_hand` `chips` = every seat's chips **before** the posts; `posted` = the blinds (and antes, `ante: true`) | `EventTracker.hand_start(..., chips)` then `post()` each | posting twice (chips after + posts), or antes as bets (they are dead money in the pot) |
| `on_hand` `hand` counts from 1 | `obs.hand_no` from 0 | pass `hand - 1` everywhere (the hand end too) |
| `on_board` = the whole board so far | `EventTracker.board(cards)` | a new street resets every bet to 0 |
| `on_action` for every action, yours included; `to` = street total after it, `paid` = chips that left the stack | `EventTracker.action(seat, move, total=to, paid=paid)` | a call's `to` is the bet it matched, capped by the stack (a short all-in) |
| `on_reveal` only when two or more hands reach a showdown | `showdown={seat: cards}` at the hand end, `{}` when none | - |
| `on_result` `net` / `chips` maps keyed by **string** seats | `deltas=[...]` by seat | `int(seat)` |
| `decide` request: `moves` lists exactly the legal ones, `raise` `min`/`max` are raise-to totals, `call` `cost` | `obs.legal`, `min_raise`, `max_raise`, `to_call` | fold is not offered when check is |
| reply `{"move": "raise", "to": int}` | `Action.raise_to(total)` | `to` must be an int inside [min, max]: 300.0 and True are illegal, not clamped |
| every call, events included, 1 ms; interrupted at 1.05 ms (a BaseException inside your code) | the hand end too: `defer_hand_end(True)` and `idle()` at the next hand start | an interrupted event leaves bookkeeping half done: the next decision must notice (`request_keys`) |
| setup = import + `Agent()` + `on_table`, 1 s per table, a fresh module per table | warm at import | the bot's table start (evaluator tables) counts here |

Reference entry: `hyperion/drills/event_example.py` (EventTracker + EventAdapter + the ship bot). Gate seat:
`hyperion/drills/gate_seat_template.py`.

Run: `python -m hyperion.drills.fakekits.kit_e_style.runner hyperion/drills/event_example.py`
