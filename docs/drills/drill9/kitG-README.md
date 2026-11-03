# Pokerbot build: Chain Hold'em

You have 60 minutes to write a Python bot that plays **Chain Hold'em**, an
8-player no-limit hold'em sit-and-go with one twist: some of your cards are
shared with the players next to you. This handout is the whole rulebook. If
something you need is missing, ask an organiser; the answer goes to every team.

Contents of the kit:

| path | what it is |
|---|---|
| `README.md` | this handout |
| `agent_template.py` | the smallest legal bot; copy it to `bot.py` and start there |
| `engine/table.py` | the dealer and table engine the tournament runs |
| `engine/sim.py` | the local simulator (`python -m engine.sim ...`) |
| `engine/harness.py` | the clock, the budgets and the submission checks, as the tournament applies them |
| `engine/cards.py` | card encoding and a fast hand evaluator (5 to 8 cards); copy it into your bot if you like |
| `engine/icm.py` | ICM calculator for the points table (`python -m engine.icm 5000 3000 2000`) |
| `engine/payouts.py` | the points table and how places are decided |
| `engine/blinds.py` | the blind schedule (`python -m engine.blinds`) |
| `bots/` | four sample opponents: `random_bot.py`, `station.py`, `tight.py`, `chain.py` |
| `bots/make_chain_table.py` | how `chain.py`'s preflop table was built offline |
| `tests/` | the engine's tests (`python -m unittest discover -s tests -t .`) |
| `TESTS.md` | how the engine was checked |

Python 3.10, standard library only. Run every command from the kit's top folder.

---

## 1. The twist: Chain Hold'em

Seat the players who are dealt in (everyone with chips) in a ring, clockwise.

- Each player gets **one private card**. Only you see it.
- Between every two neighbours in the ring the dealer places **one link card**,
  face down. Both neighbours see it and both hold it.
- Your hand is **your private card, your left link and your right link**, plus the
  five-card board: the best five cards out of those eight. You may use any
  five; you do not have to use any hole card.

```
            P1            P1 holds: own private card, link(P0,P1), link(P1,P2)
      L01        L12
   P0                P2   With n players dealt in there are n private cards and
      L40        L23      n links: 8 + 8 = 16 hole cards at a full table.
         P4     P3
            L34
```

Your **left** neighbour is the next dealt-in player clockwise (the one who acts
after you); your **right** neighbour is the previous one. So:

- You know one of your left neighbour's three cards (your left link) and one of
  your right neighbour's (your right link). You know nothing about anyone else.
- Your left neighbour holds your left link too. Against that player the card
  does not separate you; against everyone else it is as good as private.
- **Heads-up** (two players dealt in) the ring has two links and both are shared
  with your one opponent. You see two of their three cards; only their private
  card is hidden.
- Folding gives up the pot, not the cards: a folded player's links stay in the
  neighbours' hands and still play for them at showdown.
- The ring is fixed when the hand is dealt (busted players are skipped) and
  does not change during the hand.

Everything else is no-limit hold'em: standard hand ranks (straight flush, four
of a kind, full house, flush, straight, three of a kind, two pair, pair, high
card; ace plays high or in A-2-3-4-5), suits never break ties, and ties split
the pot. Ties are common in this game: two neighbours who both play their
shared card often hold the same five.

## 2. A table

- 8 players, 2,000 chips each, no antes, no rebuys. Seats are shuffled for every
  table. Opponents are anonymous: you get no names or ids.
- Blinds rise every 25 hands; the table stops after hand 200 at the latest.

  | level | hands | blinds |
  |---|---|---|
  | 1 | 1-25 | 10/20 |
  | 2 | 26-50 | 15/30 |
  | 3 | 51-75 | 25/50 |
  | 4 | 76-100 | 40/80 |
  | 5 | 101-125 | 60/120 |
  | 6 | 126-150 | 100/200 |
  | 7 | 151-175 | 150/300 |
  | 8 | 176-200 | 250/500 |

- **Button and blinds.** The first button is random. Each hand the button moves
  clockwise to the next player with chips (no dead button). The next two
  players with chips post the small and big blind. Heads-up, the button posts the
  small blind. A player who cannot cover a blind posts what they have and is
  all-in; the amount to call is still the full big blind (anything the short
  blind cannot match comes back to whoever put it in).
- **Order of play.** Preflop the player left of the big blind acts first
  (heads-up: the button). After the flop, the first player still in left of the
  button acts first. Four betting rounds: preflop, flop (3 cards), turn, river.
  No burn cards (a shuffled deck makes them irrelevant).
- **Betting.** No limit, but you choose sizes from a fixed menu (section 4.3).
  The smallest bet is the big blind; the smallest raise increment is the last
  full raise increment on this street (at least the big blind). An all-in for
  less than a full raise does not reopen the betting: a player who has already
  acted may raise again only if the bet has gone up by at least one full raise
  increment since they last acted (several short all-ins can add up to that).
- **All-in and side pots.** Standard: each pot is contested by the players who
  put in enough to be in it; chips nobody matched go back to their owner. When
  no more than one player can still bet, the rest of the board is dealt out.
- **Showdown.** Everyone left in shows all three hole cards. A pot shared by
  several winners is split equally; odd chips go one at a time to the winners
  in clockwise order starting left of the button. Folded hands are never shown,
  and a player who wins uncontested shows nothing.
- **Knocked out** at 0 chips, after the hand.

## 3. Scoring

A table is scored by finish position:

| place | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| points | 50 | 32 | 21 | 14 | 9 | 5 | 2 | 0 |

- Players knocked out in the same hand take the places just below the
  survivors, ordered by their stacks at the **start** of that hand.
- If hand 200 ends with several players left, they are ranked by **chips at that
  moment**: 4,001 chips beats 4,000. ICM does not apply at the cap.
- Players tied on that number share the points of the places they cover
  equally (two players tied for 2nd and 3rd get 26.5 each).
- Your event score is your **average points per table** over every table you
  play. There are many thousands of tables, so the ranking is decided by small
  edges, played consistently, without timeouts.

`engine/payouts.py` holds the table; `engine/icm.py` converts stacks to
expected points (Malmuth-Harville ICM, with `cap_points` for what stacks are
worth if the table stopped now).

## 4. The interface

Submit a file `bot.py` that defines a class `Agent`:

```python
class Agent:
    def __init__(self): ...                  # once per session
    def begin_table(self, info): ...         # optional; once per table
    def decide(self, s) -> str: ...          # required; every decision
    def hand_over(self, r): ...              # optional; after every hand you were dealt into
```

**One Agent instance plays a whole session**: a long sequence of tables, one at
a time. `begin_table` tells you a new table has started; reset your per-table
state there. Your last `hand_over` at a table has `r.table_over == True` (you
were knocked out or the table ended). The tournament runs many sessions of your
bot in parallel, in separate sandboxes; they share nothing, so do not rely on
anything carrying over between sessions.

### 4.1 Cards and seats

**Cards are integers 0-51**: `card = rank * 4 + suit`, so `rank = card >> 2`
(0 = deuce, 1 = trey, ..., 8 = ten, 9 = jack, 10 = queen, 11 = king, 12 = ace)
and `suit = card & 3` (0 clubs, 1 diamonds, 2 hearts, 3 spades).
The ace of spades is 51; the deuce of clubs is 0. `engine/cards.py` has
`card_str(51) == "As"` and `parse_card("As") == 51`.

**Seats are offsets from you**, clockwise: offset 0 is you, 1 is the seat to
your left (acts after you), ..., 7 is the seat to your right. Every per-seat
field is a tuple of 8 indexed by offset, and every seat number you are given
(neighbours, button, the log) is an offset. Seats of players who are out stay
in the tuples with stack 0 and status `O`, so offsets are stable for the whole
table.

### 4.2 `decide(s)`: what you see

`s` is a fresh object for every decision (changing it does nothing):

| field | type | meaning |
|---|---|---|
| `hand` | int | hand number at this table, 1-200 |
| `street` | int | 0 preflop, 1 flop, 2 turn, 3 river |
| `card` | int | your private card |
| `left` | int | your left link: the card you share with `left_nb` |
| `right` | int | your right link: the card you share with `right_nb` |
| `left_nb` | int | offset of your left neighbour (next dealt-in player clockwise) |
| `right_nb` | int | offset of your right neighbour. Heads-up, `left_nb == right_nb` |
| `board` | tuple of int | community cards so far: 0, 3, 4 or 5 |
| `pot` | int | every chip put in this hand so far, this street's bets included |
| `to_call` | int | chips you must add to call, already capped at your stack. 0 means you can check |
| `min_raise_by` | int | the smallest raise increment the dealer accepts now |
| `can_raise` | bool | False when you cannot raise: calling already puts you all-in, nobody left could answer a raise, or you have acted and no full raise has come since |
| `stacks` | tuple of 8 int | chips behind (not yet in the pot), by offset; `stacks[0]` is yours |
| `bets` | tuple of 8 int | chips put in on this street, by offset |
| `in_pot` | tuple of 8 int | chips put in this hand, by offset |
| `status` | str, 8 chars | by offset: `A` in the hand and able to act, `L` all-in, `F` folded, `O` not dealt in (out of the table) |
| `button` | int | offset of the button |
| `sb`, `bb` | int | this hand's blinds |
| `level` | int | blind level, 1-8 |
| `hands_left` | int | `200 - hand`: hands that can still be played after this one |
| `log` | str | this hand's actions so far (4.4) |
| `cost(token)` | method -> int | the chips `token` would put in now, by the dealer's exact rule (KeyError for anything that is not a token) |

Legal actions are not listed: everything you need to work them out is above,
and every token in 4.3 is always accepted.

### 4.3 What you return: an action token

`decide` returns one of these strings:

| token | action |
|---|---|
| `"F"` | fold. If `to_call == 0` it is played as a check |
| `"C"` | check if `to_call == 0`, otherwise call |
| `"R33"` `"R50"` `"R75"` `"R100"` `"R150"` `"R250"` | raise **by** that percentage of the pot |
| `"A"` | all-in |

**Sizing.** A raise token adds an increment on top of the current bet:

```
increment = (pot + to_call) * pct // 100      # pct of the pot after you call
increment = max(increment, min_raise_by)      # never below a legal raise
put_in    = min(to_call + increment, stacks[0])   # more than you have -> all-in
```

With no bet yet (`to_call == 0`) that is a bet of `pct`% of the pot, at least
the big blind. Example, first to act at 10/20: pot 30, to call 20, pot after
your call 50; `R50` raises by 25 (puts in 45, total bet 45), `R100` by 50 (70),
`R33` would be 16 so it is lifted to the 20 minimum (40), `R250` by 125 (145).
`s.cost("R75")` returns the chips a token puts in, so you never need to
re-derive this.

- When `can_raise` is False, `R..` and `A` are played as `C`.
- Anything else (another string, lower case, `None`, a number, a tuple) is an
  **error**: the dealer checks for you if it can, otherwise folds.

### 4.4 The log

`s.log` is this hand's history as one compact string, written from your seat:

- Streets are separated by `/`. A `/` is added when the next street is dealt,
  so `s.log.count("/") == s.street`.
- Inside a street, actions are separated by `,`. Each action is the actor's
  **offset** (one digit, 0 = you), a code letter, and for codes that move chips
  the number of chips that action **added**:

  | code | meaning |
  |---|---|
  | `s<n>` | posted the small blind (n chips) |
  | `b<n>` | posted the big blind |
  | `f` | fold |
  | `k` | check |
  | `c<n>` | call, adding n chips (n may be less than the bet if all-in) |
  | `r<n>` | bet or raise, adding n chips (n is what was added, not the new total) |

Example, seen by the player in offset 0 on the flop:
`5s10,6b20,7f,0r45,1f,2f,3c45,4f,5f,6c25/6k,0r47,3c47,6f`
(offset 5 small blind, 6 big blind, the button is offset 4; you raised to 45
preflop with `R50` and were called by 3 and the big blind; on the flop, pot 145,
you bet 47 with `R33`, 3 called, the big blind folded).
Actions the dealer plays for a late or failed bot look like any other `k`/`f`.

### 4.5 `hand_over(r)` and `begin_table(info)`

`hand_over(r)` is called after every hand you were dealt into, folded or not:

| field | type | meaning |
|---|---|---|
| `hand` | int | hand number |
| `board` | tuple of int | the board as far as it was dealt |
| `log` | str | the whole hand's log |
| `shown` | tuple of 8 | by offset: `(card, left, right)` for each player who reached showdown, else `None` (all `None` if nobody showed) |
| `won` | tuple of 8 int | by offset: net chips won (+) or lost (-) in this hand |
| `stacks` | tuple of 8 int | stacks after the hand |
| `place` | int | your finish place once your table is over for you, else 0 |
| `points` | float or None | your points for this table once `place` is set |
| `table_over` | bool | True on your last `hand_over` at this table |

`begin_table(info)` is called once before hand 1 of every table:

| field | type | meaning |
|---|---|---|
| `table` | int | index of this table in your session: 0, 1, 2, ... |
| `button` | int | offset of the button for hand 1 |
| `stacks` | tuple of 8 int | starting stacks by offset (all 2,000) |
| `levels` | tuple of (sb, bb) | the blind schedule |
| `hands_per_level`, `max_hands` | int | 25 and 200 |
| `points` | tuple of 8 int | the points table, 1st first |
| `menu` | tuple of str | the raise tokens |
| `decision_ms`, `callback_ms`, `table_setup_ms` | float | the budgets below |

## 5. Time limits

Each budget is wall-clock time from the moment the harness calls your method
to the moment it returns, measured around the call in your sandbox.

| what | budget | if you go over, or raise an exception |
|---|---|---|
| session setup: importing `bot.py` plus `Agent()` | 3,000 ms | you sit out the **whole session** |
| `begin_table(info)` | 20 ms | you sit out **that table** |
| `decide(s)` | **1 ms** | that decision is played as check if possible, otherwise fold; a late answer is discarded even if it arrives |
| `hand_over(r)` | 1 ms | your **next** decision at this table is played as check/fold |

- Sitting out means you are not called at all: the dealer checks or folds for
  you every time (you still post blinds and can still bust).
- A call that runs away is interrupted after 25 ms (500 ms for `begin_table`,
  30 s for setup) and counted as over the limit.
- The 1 ms includes everything you do in `decide`. Precompute in `__init__`
  (or ship data in your zip and load it there) and keep per-decision work
  bounded. Pure-Python Monte Carlo fits a few dozen to a few hundred
  evaluations; `bots/chain.py` stops its Monte Carlo at 0.3 ms.
- The harness disables Python's cyclic garbage collector while a table is being
  played (after `gc.freeze()` once your setup is done) and collects between
  tables, outside your clock, so a collection never lands inside your 1 ms.
  Garbage made of reference cycles is only freed between tables.
- Tournament machines give each bot its own idle core. A busy laptop is
  sometimes late by a few ms for reasons that have nothing to do with your bot:
  a few lates per 10,000 decisions with a p99 well under 1 ms is your machine.
  A p99 near 1 ms is your bot. If in doubt, rerun with `--decision-ms 5`: lates
  that vanish were the machine; the tournament limit stays 1 ms.

## 6. Sandbox and submission

- Python 3.10, standard library only, one core, 1 GB of memory, no network.
- Your files are read-only. Read your own data files relative to `bot.py`:
  `os.path.join(os.path.dirname(os.path.abspath(__file__)), "table.bin")`.
- Do not start threads or processes; bots that do are disqualified. Anything you
  print is discarded.
- Import helper modules at the top of `bot.py`, not inside functions.
- The kit's `engine` package is not in the sandbox. If you want the evaluator,
  copy `engine/cards.py` into your zip (it is self-contained). The simulator
  rejects a bot that imports the kit's `engine`, as the sandbox would.

**Submission:** one `.zip` per team, `bot.py` at the root of the zip (not inside
a folder), class `Agent` in it. Caps: 10 MB zipped, 50 MB unzipped, 500 files.
The last upload before the end of the build phase counts.

```
zip -r mybot.zip bot.py helpers.py data/      # bot.py at the root
python -m engine.sim mybot.zip --fill bots/chain.py -t 50   # same checks as the upload server
```

## 7. The local simulator

```
python -m engine.sim BOT [BOT ...] [-t TABLES] [--seed S] [--jobs J] [--fill BOT]
```

- `BOT` is a `.py` file with an `Agent` class, a folder containing `bot.py`, or a
  submission `.zip` (checked exactly as the upload server checks it).
- Up to 8 bots. With fewer, the list is repeated to fill 8 seats, or `--fill BOT`
  fills the rest. Each seat is its own `Agent` instance, i.e. its own session,
  and plays every table. Seats are shuffled around the table for every table.
- Same `--seed`, same deals and seatings. The simulator also seeds Python's
  global `random` at the start of each table, so bots that only use `random`
  and depend neither on timing nor on earlier tables replay exactly.
- `--jobs J` splits the tables over J processes (each runs its own sessions).

Examples:

```
python -m engine.sim bot.py bots/chain.py bots/tight.py bots/station.py -t 300
python -m engine.sim bot.py --fill bots/chain.py -t 500 --jobs 2
python -m engine.sim bot.py bots/chain.py -t 5 --history hands.txt   # readable hands
python -m engine.sim bot.py bots/tight.py -t 50 --bot-output         # let your prints through
python -m engine.sim bot.py bots/tight.py --no-time-limit            # debugging only
```

Other options: `--decision-ms`, `--callback-ms`, `--table-ms`, `--session-ms`
change the budgets; `--progress N` prints progress every N tables.

What it prints:

- **pts/table** with a 95% confidence interval, and the share of tables finished
  in each place, for every seat; then the same pooled by bot when a bot has
  several seats.
- **late**: decisions over 1 ms (played as check/fold). **errors**: exceptions
  and bad tokens. **forced**: decisions played as check/fold because the
  previous `hand_over` was late or raised. **sat-out**: decisions played for a
  bot sitting out after a failed setup. **p50/p99/max** decision time,
  `hand_over` lates/errors, the slowest `begin_table`, and session setup time.
- The first problems per seat, with tracebacks.

Speed: with the sample bots, 10 to 15 tables a second per core. A table has
roughly 600-700 decisions in all, about 100 per seat, so a bot that spends its
whole 1 ms on every decision adds about 0.1 s per table for each seat it
occupies. Use `--jobs` for long runs.

## 8. Clarifications

- `decide` is only called when you have a choice: never while you are all-in,
  and not when everyone else is all-in and you have nothing to call.
- `hand_over` comes after every hand you were dealt into, including hands you
  folded early; it does not come for tables you sit out.
- `to_call` is capped at your stack; when you cannot cover the bet, `"C"` puts
  you all-in and `can_raise` is False.
- Folding when you could check is never played; it is a check.
- Your links are dealt from the same deck as everything else: there are no
  duplicate cards anywhere in a hand.
- `bets`, `in_pot` and `stacks` always add up: `stacks[i] + in_pot[i]` is what
  player i started the hand with.
- `hands_left` counts hands after this one, ignoring knockouts; a table that is
  down to one player ends early.
- The sample bots are opponents to test against, not a hint about the field.
