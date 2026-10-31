# Kit C rubric: line protocol over stdin/stdout

| Kit C | Ours | Trap |
|---|---|---|
| one message per line, clauses split on spaces, first char is the key | - | parse by key, not by position; unknown keys must be ignored (the real kit will add some) |
| reply `OK` to the `T` line, an action to `L` lines, nothing else | - | replying to `X` or `Q` desyncs the whole table: your next reply answers the wrong question |
| `K<cards>`, `B<cards>` with `B-` for no board; cards `As`, `Td` | `parse_card` works as-is | `K` is your hand on input but `K` means *check* on output |
| `S0..3` | `street` | same index as ours |
| `C<stacks>`, `E<bets>`, `I0110` | `stacks`, `bets`, `in_hand` | `I` is a string of 0/1 per seat, not comma separated |
| `O<pot>` | `pot` | previous streets only, same as ours |
| `L F,K,C,R80-1980` | `legal`, `min_raise`, `max_raise` | the raise range rides inside the `R` token; `to_call = max(bets) - bets[seat]` capped by stack is yours to compute |
| `V10/20` | `blinds` | - |
| `T<ms>` | - | the pooled clock left; a bot that is slow early starves itself later |
| reply `F`, `K`, `C`, `R<total>` | `Action` | newline-terminated, **flushed**; a buffered stdout looks exactly like a hung bot |
| `T4 P0 Z2000 V10/20` once, reply `OK` within 10 s | `new_table` | do imports and warm-up before the `OK`; after it, every microsecond is on the clock |
| `X<hand> W<delta>` | `hand_end` | no showdown info |
| `Q` | - | exit 0; lingering processes get killed and their stderr is reported |

Budget: pooled game clock of 1 ms x hands x 3 for the table, charged by wall-clock round trip
(so ~70 us of pipe overhead per decision is already yours). A reply slower than 2 s marks the bot
dead. Never print anything but replies to stdout; use stderr for logs.

Run: `python -m hyperion.drills.fakekits.kit_c.runner submission.py`
