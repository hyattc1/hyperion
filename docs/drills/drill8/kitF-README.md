# Ghost Hold'em: starter kit

This is the handout for the build phase. You have **60 minutes** to write a Python bot that
plays **Ghost Hold'em**: no-limit hold'em with one extra hand at every table that never bets.
Read the twist section twice. The interface is not the one you may have practised against,
so read that section too.

Contents

1. [The event](#1-the-event)
2. [The twist: the Ghost](#2-the-twist-the-ghost)
3. [Table rules](#3-table-rules)
4. [Points](#4-points)
5. [Your bot: the interface](#5-your-bot-the-interface)
6. [Time limits](#6-time-limits)
7. [Sandbox](#7-sandbox)
8. [Submitting](#8-submitting)
9. [The local simulator](#9-the-local-simulator)
10. [What is in the kit](#10-what-is-in-the-kit)
11. [Common mistakes](#11-common-mistakes)

---

## 1. The event

- Each team submits one bot by **minute 60**.
- Bots play **8-player sit-and-go tables**. Everyone starts with **2,000 chips**. Blinds start
  at **10/20** and go up every **25 hands**. A table stops when one player has every chip, or
  after **200 hands**, whichever comes first.
- We play many thousands of tables. Seats and opponents are drawn at random for every table.
- Your score is your **mean points per table**. Points depend only on your finishing place
  (section 4).
- Every decision must come back within **1 millisecond**. If it doesn't, or your code raises,
  the dealer **checks for you if checking is free, and otherwise folds**.
- Bots run in sandboxes with **no network access** and only the **Python 3.10 standard library**.

## 2. The twist: the Ghost

Every hand, after the players get their hole cards, the dealer deals **one more two-card hand
face down: the Ghost**. The Ghost's cards come from the same deck, so they are not on the board
and not in anyone's hand. The Ghost never bets, never folds and never wins chips. It matters
in one place only: **the showdown**.

**The rule.** When a pot reaches a showdown with two or more players still in it, the dealer
compares the Ghost's best five-card hand (its two cards plus the board) with the best hand
among the players in that pot.

- If the Ghost's hand is **strictly better**, nobody wins that pot. The pot **haunts**.
- If the Ghost's hand is worse or **equal**, the pot is paid out as normal. Ties with the Ghost
  go to the players.

**Where a haunted pot goes.** Haunted chips are moved into the **next hand's main pot** before
any cards are dealt. They are dead money, and they go to whoever wins that main pot,
**whether by showdown or because everyone else folded**. We call it **the Haunt**. You see it as
`s.haunt` (it is already included in `s.pot`). If the next hand also haunts, the Haunt carries on
and grows.

More detail:

- **Pots won without a showdown never haunt.** If everyone else folds, you win the pot, the
  Haunt included, and the Ghost is never looked at.
- **Every pot is checked separately.** With side pots, the Ghost is compared with the best hand
  among the players eligible for *that* pot. A short stack can win the main pot while the side
  pot haunts, or the other way round.
- **Chips you put in a haunted pot are gone.** If that leaves you with 0 chips, you are
  eliminated. The player who covered you keeps only the chips they had behind.
- **The Ghost never ends a table.** If haunting would leave no player at the table with any
  chips (for example two players all-in for exactly the same amount), the Ghost is ignored for
  that hand and the pots are paid out as normal.
- **A Haunt still on the table when the table ends is discarded.** It belongs to no one, and it
  does not count toward anyone's chips at the end of hand 200.
- The Ghost's cards are revealed after every showdown (`r.ghost` in `hand_over`). When there is
  no showdown, they stay hidden.

**Example.** Heads-up, you hold A♥ K♦, your opponent Q♣ J♠. The board is 2♥ 7♠ 9♦ T♣ 3♠ and
you both check it down. Your ace-high beats their queen-high, but the Ghost holds 2♣ 2♦: trip
deuces. The 40-chip pot haunts. Next hand, the pot starts at 40 plus the blinds. Your
opponent opens, you fold, and they collect the blinds and the 40.

## 3. Table rules

- **Seating.** 8 seats, 2,000 chips each. Seats never change during a table.
- **Button.** For hand 1 the button goes to a random seat. After every hand it moves clockwise
  to the next player who still has chips (there is no dead button).
- **Blinds.** The small blind is the next player with chips clockwise from the button, the big
  blind the next one after that. **Heads-up, the button posts the small blind.** A player who
  cannot cover a blind posts everything they have and is all-in. There are **no antes**.
  The schedule is in [PAYOUTS.md](PAYOUTS.md) and `engine/blinds.py`.
- **Dealing.** Each hand uses a fresh shuffled deck. Hole cards are dealt one at a time
  starting with the small blind, then the Ghost's two cards, then burn, flop, burn, turn,
  burn, river.
- **Betting order.** Before the flop, the first player to act is the one after the big blind
  (heads-up: the button/small blind). After the flop, the first player with chips after the
  button acts first (heads-up: the big blind).
- **No-limit betting.**
  - Before the flop the amount to call is the full big blind, even if the big blind player is
    all-in for less. Chips nobody matches are returned at the end of the hand.
  - A bet or raise must be at least the big blind, and at least as large as the last full bet
    or raise on this street. There is no limit on the number of raises.
  - You may always go all-in. An all-in that is smaller than a full raise is allowed, but it
    does **not** reopen raising for players who have already acted on this street. Those players
    can only call or fold, unless someone later makes a full raise.
  - If every other player still in the hand is all-in, you cannot raise; you can call or fold.
  - Folding when you could check counts as a check.
- **Showdown.** If two or more players reach the end of the river, or are all-in earlier and
  the board is run out, every remaining player shows. Then each pot is settled, main pot first,
  following section 2. Best five of seven cards; suits never rank; split pots are split
  equally. Odd chips go to the winners closest to the button's left.
- **Eliminations and places.** See section 4.

## 4. Points

| Place  | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|--------|----:|----:|----:|----:|----:|----:|----:|----:|
| Points |  16 |  11 |   8 |   6 |   4 |   2 |   1 |   0 |

- A player who ends a hand with 0 chips is out and takes the worst place still open. A
  knockout by the Ghost counts the same as any other.
- If several players go out in the same hand, the one who **started that hand with more chips**
  takes the better place. Players who started with exactly the same stack share the places
  involved and each gets the average of those points.
- The last player with chips is 1st.
- If a table reaches the end of hand 200 with two or more players left, they are placed by chip
  count. Exactly equal counts share places and average the points. A Haunt still on the table
  is discarded first.
- Your event score is your mean points per table over every table you play. The full
  structure, with the blind schedule, is in [PAYOUTS.md](PAYOUTS.md).

`engine/icm.py` is an ICM (Malmuth-Harville) calculator for this point table. You may copy it
into your bot.

## 5. Your bot: the interface

Your entry file is `bot.py`, and it defines a class named `Agent`:

```python
class Agent:
    def __init__(self):          # once per session          (import + __init__: 2 s)
        ...
    def new_table(self, t):      # once per table, optional  (50 ms)
        ...
    def act(self, s):            # every decision            (1 ms) -> int
        ...
    def hand_over(self, r):      # after every hand, optional (1 ms)
        ...
```

**One Agent plays a whole session.** We construct your `Agent` once, and that instance then plays
table after table (hundreds of them) one at a time. Anything you store on `self` survives from
table to table. `new_table` is called before each table's first hand. The official run uses
many sessions in parallel, each one a separate process with its own `Agent`, so do not count on
any state shared between instances.

`new_table` and `hand_over` are optional. If you leave either one out, it is simply never called.

### Four conventions to get right

1. **Cards are integers 0-51.** `card = 4 * rank + suit`, so `rank = card >> 2`
   (0 = deuce, 1 = trey, ..., 8 = ten, 9 = jack, 10 = queen, 11 = king, 12 = ace) and
   `suit = card & 3` (0 clubs, 1 diamonds, 2 hearts, 3 spades). The ace of spades is 51 and the
   two of clubs is 0. `engine/cards.py` converts to and from `"As"` strings for debugging.
2. **Seats are relative to you.** In everything you receive, **seat 0 is you**. Seat 1 is the
   next seat clockwise (it acts after you), and so on up to seat 7 on your right. Players who
   are out keep their seat numbers. Opponents are identified across tables by `t.ids`.
3. **Your action is a single int: the chips you put in now.** You never send a "raise to"
   total, and there is no action object and no list of legal actions. Section 5.3 shows how
   the int is read.
4. **The hand's history is a compact string**, `s.log` (section 5.4).

### 5.1 `new_table(t)`: once per table

| field | type | meaning |
|---|---|---|
| `t.table_id` | `str` | unique id of this table within the session |
| `t.ids` | `tuple[str] * 8` | player id for each **relative** seat; `t.ids[0]` is yours. Ids are opaque and stay the same for a given opponent for the whole session, so you can keep statistics on them. Locally they look like `"tight#3"`. |
| `t.stack` | `int` | your starting stack (2000) |
| `t.blinds` | `tuple[(int, int)]` | (small, big) blind per level, level 1 first |
| `t.level_hands` | `int` | hands per level (25) |
| `t.max_hands` | `int` | hand limit (200) |
| `t.points` | `tuple[int] * 8` | points by place, 1st first |
| `t.limits_ns` | `dict` | `{"act": 1000000, "hand_over": 1000000, "new_table": 50000000}` in nanoseconds |

### 5.2 `act(s)`: every decision, return an `int`

You are only asked when you have a real decision: you are in the hand, not all-in, and either
action has come to you or you owe chips.

| field | type | meaning |
|---|---|---|
| `s.hand_no` | `int` | hand number at this table, 1-200 (the level is `(hand_no - 1) // 25`) |
| `s.street` | `int` | 0 preflop, 1 flop, 2 turn, 3 river |
| `s.hole` | `(int, int)` | your two cards |
| `s.board` | `tuple[int]` | 0, 3, 4 or 5 community cards |
| `s.stack` | `int` | your chips behind (not counting what you have bet this street) |
| `s.owe` | `int` | chips you must put in to call. 0 means you can check. If you cannot cover a bet, `s.owe == s.stack` and calling puts you all-in. |
| `s.min_raise` | `int` | the fewest chips you can put in **now** that count as a raise (call plus the minimum raise). It equals `s.stack` when going all-in is your only raise, and it is **0 if you cannot raise** at all. |
| `s.pot` | `int` | all chips in the middle: every bet so far, this street's included, plus the Haunt |
| `s.haunt` | `int` | Haunt carried into this hand (already part of `s.pot`; 0 if none) |
| `s.sb`, `s.bb` | `int` | current blinds |
| `s.button` | `int` | relative seat of the button |
| `s.stacks` | `tuple[int] * 8` | chips behind for each relative seat (`s.stacks[0] == s.stack`) |
| `s.bets` | `tuple[int] * 8` | chips each relative seat has put in **on this street** (blinds count) |
| `s.status` | `str`, length 8 | one char per relative seat: `A` in the hand with chips, `X` all-in, `F` folded, `-` not in this hand (out of the table). `s.status[0]` is always `A`. |
| `s.log` | `str` | everything that has happened in this hand so far (5.4) |

**The action.** `act` returns an `int` *n*: the number of chips you move from your stack into
the pot with this action. The dealer reads it like this:

| you return | the dealer does |
|---|---|
| `n < s.owe` (including any negative *n*, and 0 when you owe chips) | **fold**; a **check** if `s.owe == 0` |
| `s.owe <= n < s.min_raise`, or any `n >= s.owe` when `s.min_raise == 0` | **call** (a check if `s.owe == 0`) |
| `s.min_raise <= n < s.stack` | **raise**, putting in exactly *n* chips |
| `n >= s.stack` (with `s.min_raise > 0`) | **all-in** |

So: `return 0` means check, or fold if you owe chips. `return s.owe` means check or call.
`return s.stack` means all-in. To raise to a total of *T* chips on this street, return
`T - s.bets[0]`. A `float` is rounded down. Any other type, including `bool`, `None` and
strings, counts as an **error** and gets the default action.

### 5.3 Examples

Preflop, blinds 10/20, you are the button and two players have folded to you.
`s.owe = 20`, `s.min_raise = 40`, `s.stack = 2000`:

| return | result |
|---|---|
| `-1` or `0` or `15` | fold |
| `20` or `39` | call 20 |
| `60` | raise: you put in 60 (a total bet of 60) |
| `5000` | all-in for 2000 |

Big blind, everyone limped: `s.owe = 0`, `s.min_raise = 20`. `0` checks, `-1` also checks,
and `20` raises by 20 to a total of 40.

### 5.4 The log

`s.log` is a space-separated list of tokens covering the current hand from the blinds on.
Seat numbers are **relative to you**, as everywhere else.

```
token := "/"                 the next street was dealt (flop, turn, river)
       | SEAT "s" N ["!"]    posted the small blind of N
       | SEAT "b" N ["!"]    posted the big blind of N
       | SEAT "f"            folded
       | SEAT "k"            checked
       | SEAT "c" N ["!"]    called, putting in N chips
       | SEAT "r" N ["!"]    bet or raised, putting in N chips (the chips for this action, not a total)
SEAT  := "0" .. "7"          relative seat, 0 is you
"!"   = this put the player all-in
```

Example, seen from seat 0:

```
1s10 2b20 3f 4c20 5r60 6f 7f 0c60 1f 2c40 4c40 / 2k 4r90 5f 0c90 2f / 4k 0k / 4r200
```

You are on the button. Seat 1 posted the small blind and seat 2 the big blind. Seat 4 limped,
seat 5 raised to 60, you called, and seats 2 and 4 called too. On the flop seat 4 bet 90,
seat 5 folded, you called and seat 2 folded. On the turn seat 4 and you both checked. On the
river seat 4 has bet 200, and it is your turn: `s.owe == 200`. Timeouts appear in the log as
the default action (`k` or `f`).

### 5.5 `hand_over(r)`: after every hand you were dealt into

| field | type | meaning |
|---|---|---|
| `r.hand_no` | `int` | |
| `r.board` | `tuple[int]` | all 5 cards if there was a showdown, otherwise the cards dealt before the hand ended |
| `r.shown` | `dict[int, (int, int)]` | relative seat -> hole cards, for every player at the showdown (empty if none) |
| `r.ghost` | `(int, int)` or `None` | the Ghost's cards if there was a showdown, else `None` |
| `r.pots` | `list[(int, tuple[int])]` | each pot as (amount, winning relative seats), main pot first. **An empty winners tuple means that pot haunted.** Uncalled chips returned to a bettor are not a pot. |
| `r.haunted` | `int` | chips haunted this hand, which become the next hand's Haunt |
| `r.delta` | `tuple[int] * 8` | chip change this hand per relative seat |
| `r.stacks` | `tuple[int] * 8` | chips after the hand per relative seat |
| `r.log` | `str` | the full log of the hand |
| `r.busted` | `tuple[int]` | relative seats eliminated this hand |
| `r.place` | `int` | your final place if you were eliminated this hand or the table is over, else 0 |
| `r.table_over` | `bool` | True after the table's last hand |
| `r.places` | `tuple[int] * 8` or `None` | final places per relative seat when the table is over (tied players show the better place) |

Once you are eliminated you get no more calls for that table. The next call is `new_table`
for your next table.

## 6. Time limits

| call | budget | if you go over, or raise an exception |
|---|---|---|
| import of `bot.py` + `Agent()` | **2 s**, once per session | you sit out the whole session: the default action every time |
| `new_table(t)` | **50 ms** per table | you sit out **that table**: the default action every time, and no callbacks |
| `act(s)` | **1 ms** per decision | that decision gets the **default action**: check if `s.owe == 0`, otherwise fold |
| `hand_over(r)` | **1 ms** per hand | your **next** `act()` is skipped and gets the default action |

- Time is **wall-clock**, measured by the dealer with `time.perf_counter_ns()` from the moment it
  calls your method until the method returns. The local simulator measures it exactly the same
  way, in the same process as the dealer.
- Python's cyclic garbage collector is switched off while a table is running and run between
  tables, so a collection pause never lands on your clock. Memory you leak is still yours, so
  don't build up cycles.
- A call that is still running after 1 s is interrupted. Officially your process is killed and
  you sit out the rest of that session.
- Tournament machines are quiet, dedicated cores of about laptop speed. A busy laptop is not:
  aim for a **p99 under 500 us** in the simulator, and use `--limit-us 500` to test your headroom.
  The table of results shows p50, p99 and max for every bot.

## 7. Sandbox

- CPython **3.10**, standard library only. No numpy, no compiled extensions, no `pip`.
- No network. The filesystem is read-only apart from a private temp directory. Read any data
  files from your own folder, using `os.path.dirname(__file__)`.
- Single-threaded: do not start threads or processes. 1 GB of memory per process.
- Anything you print to stdout or stderr is thrown away. Printing costs time.
- Do all your imports at the top of your modules, not inside `act`.

## 8. Submitting

Submit **one zip** named after your team, for example `team-name.zip`:

```
team-name.zip
├── bot.py          <- required, at the ROOT of the zip, defines class Agent
├── anything.py     <- optional helper modules (e.g. a copy of engine/handeval.py)
└── tables.txt      <- optional data files
```

- `bot.py` must be at the **root** of the zip, not inside a folder. Zip the *contents* of your
  folder: `cd mybot && zip -r ../team-name.zip .`
- Caps: **5 MB** zipped and **25 MB** unzipped. Only `.py` and data files are allowed: no `.so`,
  `.pyd`, `.dll` or `.exe`.
- You may copy any file from this kit into your zip (`handeval.py`, `icm.py`, `cards.py`).
- Upload it on the event page **before minute 60**. You may upload as often as you like; your
  last upload before the deadline counts.
- **Check it first.** This runs the same layout, import and timing checks as the organisers, then
  plays 20 tables against the sample bots:

  ```
  python3 -m engine.check team-name.zip
  ```

## 9. The local simulator

Run these from the kit folder (or use `python3 path/to/kit/engine/sim.py ...`):

```
# your bot against the sample field (8 seats filled by repeating the list), 300 tables
python3 -m engine.sim mybot/ bots/ghostwise bots/tight.py bots/station.py -t 300

# a .py file, a folder holding bot.py, or your submission zip all work
python3 -m engine.sim team-name.zip bots/ghostwise -t 200

# less luck: every deal is played 8 times with the entries rotated through the seats
python3 -m engine.sim mybot/ bots/tight.py --duplicate -t 400

# watch what happens: print the first 10 hands of table 1 (with the Ghost and every pot)
python3 -m engine.sim mybot/ bots/tight.py -t 1 --show 10

# stricter time limit to test headroom; use 4 processes
python3 -m engine.sim mybot/ bots/ghostwise -t 600 --limit-us 500 -j 4
```

You can seat 1 to 8 bots. If you give fewer than 8, the list is repeated to fill the table.
Every seat gets its **own fresh instance** of its bot. Seats are shuffled every table, and each
seat's `Agent` plays the whole run as one session.

The output has one row per seat:

```
slot  entry   points  +-95%  1st%  place  decisions  p50us  p99us  maxus  tmout  error  cbfail  auto
```

- **points**: mean points per table. **±95%**: 1.96 standard errors over tables.
- **1st%**: share of tables won. **place**: mean finishing place.
- **p50us, p99us, maxus**: `act()` time. **tmout**: `act()` calls over the limit.
  **error**: `act()` raised or returned a non-number. **cbfail**: `new_table`/`hand_over` over
  budget or raised. **auto**: decisions the dealer made for you because of a penalty.
- Below the table you get table statistics, how often the Ghost haunted, and the first error
  for each seat.

Options: `-t/--tables N` (default 100), `--seed N`, `--duplicate`, `--no-shuffle`,
`--limit-us US` (default 1000), `--setup-ms MS` (default 50), `--show N`, `-j/--jobs N`,
`--clock {wall,cpu}`. The default `wall` clock is the official one. `cpu` counts only your own
thread's CPU time, which helps when other programs are fighting your laptop for the CPU.

The engine's own tests (50 of them, about 10 seconds) run with
`python3 -m unittest discover -s tests`.

## 10. What is in the kit

```
README.md            this handout
PAYOUTS.md           points, places and the blind schedule
TESTS.md             how the engine was checked
agent_template.py    a minimal legal bot in this interface: copy it to bot.py and start here
engine/
  dealer.py          the table engine, with the Ghost; this is the dealer we run
  sim.py             the local simulator (python3 -m engine.sim)
  check.py           submission checker (python3 -m engine.check)
  loader.py          loads bots from .py / folder / zip
  handeval.py        fast 5-7 card evaluator (about 1 us per hand); copy it freely
  icm.py             ICM calculator for the point table; copy it freely
  cards.py           card int <-> "As" helpers
  blinds.py          blind schedule, stack, hand limit
  payouts.py         point table and place rules
bots/
  random_bot.py      random actions
  station.py         calls everything
  tight.py           tight, straightforward hold'em; does not know about the Ghost
  ghostwise/         a folder bot (bot.py + handeval.py + icm.py) that plays around the Ghost
tests/               the engine's unit tests and stress test
```

## 11. Common mistakes

- Returning a raise-to total. `act` returns the chips you put in **now**. To make the total bet
  *T*, return `T - s.bets[0]`.
- Returning `0` when you mean "call". `0` folds when you owe chips; use `s.owe`.
- Treating seat 0 as the first seat at the table. Seat 0 is **you**.
- Reading cards as strings. They are ints: `rank = c >> 2`, `suit = c & 3`.
- Zipping the folder instead of its contents, so `bot.py` ends up in `team-name/bot.py`.
- Doing slow work in `hand_over`. It has a 1 ms budget too.
- Forgetting that the Ghost exists.
