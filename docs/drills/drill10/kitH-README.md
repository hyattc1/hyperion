# Pokerbot Sprint: starter kit

You have **60 minutes** to build a Python bot. At the end of the build your bot plays many
thousands of 8-player sit-and-go tables against every other team's bot, and is scored on where it
finishes. This file is the whole rulebook: if something here disagrees with your memory of poker,
this file wins.

```
README.md            this handout
agent_template.py    a minimal legal bot: copy it to bot.py and start editing
engine/              the dealer, the local simulator, ICM, payouts, blind schedule (read it, copy from it)
bots/                four sample opponents
```

Quick start:

```
cp agent_template.py bot.py
python3 engine/sim.py bot.py bots/station.py bots/random_bot.py bots/tight.py bots/solo_aware.py \
    bots/station.py bots/random_bot.py bots/tight.py -t 100
```

---

## 1. The game: Solo Hold'em

This event's variant is **Solo Hold'em**. It is no-limit Texas hold'em with one change, at the
showdown:

> **Your hand is the best five-card poker hand made of exactly ONE of your two hole cards and
> exactly FOUR of the five board cards.**

You can never play both hole cards, and you can never play the board. Everything else is
standard no-limit hold'em: two hole cards each, flop, turn, river, four betting rounds, the usual
hand ranks (straight flush, quads, full house, flush, straight, trips, two pair, pair, high card),
ace high or low in straights (A-2-3-4-5), suits never rank.

Examples (board first):

| board | hole cards | the hand it plays |
|---|---|---|
| K♣ 9♠ 7♦ 4♥ 2♣ | A♥ A♦ | **ace high**: A K 9 7 4. A pocket pair is only one card. |
| K♣ 9♠ 7♦ 4♥ 3♣ | 7♣ 2♦ | pair of sevens, 7 7 K 9 4: it beats the aces above |
| A♥ K♥ Q♥ J♥ T♥ | 2♣ 3♦ | ace high (A K Q J 2). Nobody plays the royal flush on the board. |
| A♥ K♥ Q♥ J♥ T♥ | 9♥ 3♦ | straight flush, 9 high (9♥ K Q J T) |
| A♥ A♦ A♣ A♠ K♦ | Q♣ 2♥ | four aces with a **queen** kicker; the board's king cannot be your fifth card |
| 2♥ 5♥ 9♥ K♣ 3♣ | A♥ Q♥ | ace high. A flush needs four board cards of your suit. |
| 2♥ 5♥ 9♥ K♥ 3♣ | A♥ 7♣ | ace-high flush (A♥ + four board hearts) |
| K♣ 9♠ 9♦ 4♥ 2♣ | K♦ 3♣ | two pair, kings and nines. One hole card can pair only one rank. |

Ties split the pot. `engine/cards.py` has the dealer's evaluator: `evaluate_solo(hole, board)`
returns the score the dealer compares, and `best_solo(hole, board)` also returns the five cards.
You may copy it.

## 2. The table

| | |
|---|---|
| players | 8 per table, random seats |
| starting stack | 2,000 chips each (16,000 at the table) |
| blinds | 10/20 at hand 1, rising every 25 hands (schedule below); no antes |
| length | until one player has all the chips, or 200 hands, whichever comes first |
| button | random for hand 1, then one occupied seat clockwise each hand |
| blinds | the next two occupied seats after the button post small and big blind; heads-up, the button posts the small blind |
| action | preflop starts left of the big blind; later streets start with the first player still in left of the button. Heads-up: the button acts first preflop and last after the flop |

Blind schedule (`engine/blinds.py`):

| level | hands | small | big |
|---|---|---|---|
| 1 | 1-25 | 10 | 20 |
| 2 | 26-50 | 15 | 30 |
| 3 | 51-75 | 25 | 50 |
| 4 | 76-100 | 40 | 80 |
| 5 | 101-125 | 60 | 120 |
| 6 | 126-150 | 100 | 200 |
| 7 | 151-175 | 150 | 300 |
| 8 | 176-200 | 250 | 500 |

Betting is no-limit:

* A player who cannot cover a blind posts what they have and is all-in. The others still owe the
  full big blind.
* The minimum raise is the size of the last full raise on this street (at least the big blind).
  You may always go all-in for less than that.
* An all-in for less than a full raise does not reopen the betting: a player who has already
  acted on this street may then only call or fold, unless the raises since their last action add
  up to at least a full raise.
* You cannot raise when every other player still in is all-in.
* Side pots are standard. Chips nobody else could match are returned. Odd chips of a split pot
  go one at a time to the winners closest to the left of the button.
* You cannot fold when you could check: a fold with nothing to call is a check.
* There is no mucking at showdown: every hand still in is shown.

## 3. Points

Your score is the average of your points over all your tables. Points by finishing place
(`engine/payouts.py`, `engine/PAYOUTS.md`):

| place | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| points | 13 | 8 | 5 | 3 | 2 | 1 | 0 | -2 |

* A player is out when they finish a hand with no chips. Players out in the same hand are placed
  by their stack at the start of that hand: the bigger stack places higher.
* If the table reaches hand 200, the players left are placed by their chip count.
* Ties (equal starting stacks busting in the same hand, or equal chips at hand 200) share the tied
  places: each gets the average of those places' points.
* The first player out loses 2 points. A table pays 30 points in all, 3.75 per seat on average.

`engine/icm.py` turns stacks into expected points (Malmuth-Harville ICM), for example
`python3 engine/icm.py 6000 4000 3000 3000` for four players left.

## 4. Your bot

### 4.1 Process and protocol

Your bot is a program, `bot.py`, run by the engine as its own process:

```
python3 -u bot.py            # CPython 3.10, standard library only; working directory = your unzipped submission
```

It talks to the engine in **JSON lines**: the engine writes one JSON object per line to your
**stdin**, and you answer **every** line with exactly one JSON object on one line on your
**stdout**, flushed. Your reply must echo the message's `id`. Anything else you print to stdout
that is not that reply is ignored (and costs you time): log to **stderr**.

One process plays a whole **session**: a series of tables, one after another (expect a few
hundred). The engine sends:

```
hello                       once, when your process starts
table                       a table starts
  act / act / end ...       a decision for you (act); a hand finished (end)
over                        the table finished, with places and points
table ...                   the next table
                            stdin closes at the end of the session: exit
```

`act` is the only message that needs an action. Every other reply is just `{"id": 17}`.

### 4.2 Players, cards, amounts

* **Players are handles**, not seat numbers: short opaque strings (`"q7mz"` at the event; the
  local simulator names them after the bot files). A handle is the same for the whole session,
  so you can learn about an opponent across tables. Your own handle is in `hello` and in every
  `act` as `you`.
* **Cards are integers 0-51**: `card = 4 * rank + suit`, where `rank = card >> 2` is 0 (deuce)
  through 12 (ace) and `suit = card & 3` is 0-3 (clubs, diamonds, hearts, spades). Example: the
  ace of hearts is 50, the deuce of clubs is 0.
* **Chips are integers.** Raises are **raise-by** amounts (see 4.4).

### 4.3 Messages from the engine

Every message has `"id"` (int, increasing; echo it) and `"t"` (its type).

**`hello`** (once per process)

| field | type | meaning |
|---|---|---|
| `proto` | int | protocol version, 1 |
| `variant` | str | `"solo"` |
| `you` | str | your handle for this session |
| `seats` | int | players per table, 8 |
| `stack` | int | starting stack, 2000 |
| `blinds` | list of [int, int] | [small, big] for levels 1-8 |
| `hands_per_level` | int | 25 |
| `max_hands` | int | 200 |
| `points` | list of numbers | points for 1st, 2nd, ... |
| `limits_ms` | object | `{"hello": 2000, "table": 50, "act": 1, "end": 1, "over": 1}` |

**`table`** (a table starts)

| field | type | meaning |
|---|---|---|
| `table` | int | table number within this session: 1, 2, ... |
| `seats` | list of str | the handles at this table, clockwise |
| `button` | str | who has the button on hand 1 |
| `stack` | int | your starting stack, 2000 |
| `max_hands` | int | 200 |

**`act`** (your decision)

| field | type | meaning |
|---|---|---|
| `table` | int | table number |
| `hand` | int | hand number at this table, from 1 |
| `sb`, `bb` | int | blinds this hand |
| `you` | str | your handle |
| `button` | str | the button's handle |
| `cards` | [int, int] | your hole cards |
| `board` | list of int | board cards so far: 0, 3, 4 or 5 of them |
| `pot` | int | every chip put in this hand so far, including bets on this street |
| `to_call` | int | chips you must add to call (0 = you can check) |
| `min_r` | int | the smallest raise-by amount you may choose; 0 if you cannot raise |
| `max_r` | int | the largest raise-by amount (all-in); 0 if you cannot raise |
| `players` | list of objects | everyone dealt into this hand, in position order (below) |
| `log` | str | this hand's actions so far (below) |

Each entry of `players`:

| field | type | meaning |
|---|---|---|
| `h` | str | handle |
| `stack` | int | chips behind (not yet put in) |
| `bet` | int | chips put in on this street |
| `total` | int | chips put in this hand |
| `state` | str | `"live"`, `"folded"` or `"allin"` |

Position order: `players[0]` is the small blind, `players[1]` the big blind, then clockwise; the
button is last. Heads-up there are two entries and `players[0]` is the button and small blind.
Players already eliminated from the table are not listed.

**`log`**: streets are separated by `/`, actions by single spaces. Each action is
`handle:act` where `act` is `f` (fold), `k` (check), `c` (call; possibly all-in for less), or
`r<N>` (raised by N, after clamping). Blinds are not in the log; `players[0]` and `players[1]`
posted them (`total` shows how much, if they were short). The number of `/` is the number of
finished streets: 0 preflop, 1 on the flop, 2 on the turn, 3 on the river. Example on the flop:

```
"cc:f dd:r40 ee:f ff:f gg:c hh:f aa:f bb:c/bb:k dd:r55"
```

**`end`** (a hand you were dealt into is over)

| field | type | meaning |
|---|---|---|
| `table`, `hand` | int | which hand |
| `board` | list of int | every board card dealt (fewer than 5 if it ended early) |
| `log` | str | the whole hand |
| `shown` | {str: [int, int]} | hole cards of every player still in at a showdown; `{}` if everyone else folded |
| `best` | {str: [int x5]} | the five cards each shown hand played (one hole card + four board cards) |
| `won` | {str: int} | chips each winner collected (includes returned uncalled chips) |
| `stacks` | {str: int} | everyone's chips after the hand |
| `out` | list of str | handles eliminated this hand |

**`over`** (the table is finished)

| field | type | meaning |
|---|---|---|
| `table` | int | table number |
| `hands` | int | hands played |
| `results` | list of [str, int, number] | [handle, place, points], best place first; tied players share a place number and the average points |

You get `end` for every hand you were dealt into, and `over` for every table you sat at, even
after you were eliminated.

### 4.4 Your reply

```
{"id": 41}                      to hello, table, end, over
{"id": 42, "a": "c"}            to act
```

The action `a` is a string:

| `a` | meaning |
|---|---|
| `"f"` | fold (a check if `to_call` is 0) |
| `"c"` | check, or call `to_call` (all-in if you have less) |
| `"r<N>"` | **raise by N**: put in `to_call`, then N more. N is a positive integer in decimal, e.g. `"r60"` |

Raise-by, not raise-to. The bet you face is `to_call` above your `bet`; after `"r<N>"` the bet
to match is N higher than it was, and you have put in `to_call + N` more chips. Examples with
blinds 10/20:

* First in preflop, nothing in yet (`to_call` 20): `"r40"` puts in 60, raising to 60 in total.
* In the big blind facing a raise to 60 (`to_call` 40): `"r100"` puts in 140, making it 160.
* On the flop, checked to you (`to_call` 0): `"r50"` bets 50.

N is clamped into `[min_r, max_r]`: too small becomes `min_r`, too big becomes `max_r` (all-in),
so `"r999999"` is always all-in. If you cannot raise (`max_r` is 0), any `"r<N>"` is a call.

Anything else is an **error**: not JSON, no `a`, or `a` not one of the forms above (`"k"`,
`"raise 50"`, `"r-5"`, `"R50"`, `"r1.5"`, a number, ...). An error is played as the default
action: **check if `to_call` is 0, otherwise fold**. Extra keys in your reply are ignored.

### 4.5 Time limits

The clock runs **on the engine's side**, wall time: it starts when the engine writes the message
to your stdin and stops when the engine has read your reply line from your stdout. Your reading,
parsing, thinking, writing and flushing all count.

| message | limit | if you miss it |
|---|---|---|
| `hello` | 2000 ms from launch (imports, precomputation) | you are auto-played until your reply arrives |
| `table` | 50 ms (per-table setup budget) | you are auto-played until your reply arrives |
| `act` | **1 ms** | check if you can, otherwise fold |
| `end`, `over` | 1 ms | nothing is lost unless you are still busy at your next decision |

**One message in flight.** The engine never sends you a new message while you still owe a
reply. If you miss a limit, the engine plays on without you; your late reply is thrown away when
it arrives. Until it has arrived you are **busy**: every decision that comes up meanwhile is
auto-played (check or fold) and counts as a timeout, and `end` messages are skipped. Every `act`
is self-contained (cards, board, stacks, the whole log), so a busy bot loses information but
never gets out of sync. A table moves at tens of microseconds per message, so a 20 ms stall can
cost you dozens of decisions. Python's garbage collector can stall you; `gc.freeze()` or
`gc.disable()` after setup is allowed.

**Crashes.** If your process exits, every decision is auto-played until the end of that table.
The engine relaunches your bot (a fresh `hello`) before your next table, up to 3 times a session;
after that you are auto-played for the rest of the session.

**Sandbox.** Each bot runs in its own sandbox: no network, one CPU core, 1 GB of address space
(`RLIMIT_AS`), CPython 3.10 with the standard library only (no numpy). Your working directory is
your unzipped submission; you may read your own files and write scratch files there. Nothing
persists between sessions.

## 5. Submitting

* One **zip**, at most **5 MB** zipped and 20 MB unzipped.
* **`bot.py` at the zip root** is the entry file. Anything else in the zip (modules, data
  files, precomputed tables) is available next to it: `import mymodule` works for modules at the
  root.
* No absolute paths or `..` in the zip.
* Upload through the event portal before minute 60. Your last upload counts.
* Check your zip with the local simulator before you upload; it unpacks and runs zips exactly
  as the event does:

```
cd mybot && zip -r ../team.zip . && cd ..
python3 engine/sim.py team.zip bots/station.py bots/tight.py -t 20
```

## 6. The local simulator

```
python3 engine/sim.py [options] ENTRY ENTRY [ENTRY ...]
```

Each ENTRY is a `.py` file, a directory with `bot.py` in it, or a submission zip. Give 2 to 8
entries; repeat a path to seat several copies (each copy is its own process). Every entry is
one session for the whole run, and seats rotate so every entry sits in every seat equally often.
The event is always 8-handed; with fewer entries the simulator pays places 1..N with the first N
values of the point table.

| option | default | meaning |
|---|---|---|
| `-t, --tables T` | 200 | tables to play |
| `-s, --seed S` | 1 | card seed; the same seed deals the same cards |
| `--dup` | off | duplicate mode: each group of N tables replays the same cards with the seats rotated (less luck in the comparison; the interval is then over groups) |
| `--limit-ms MS` | 1.0 | decision limit (also used for `end`/`over`) |
| `--setup-ms MS` | 50 | table setup budget |
| `--hello-ms MS` | 2000 | startup budget |
| `--mem-mb MB` | 1024 | address-space cap per bot (0 = off) |
| `--stderr DIR` | off | save each entry's stderr to `DIR/<handle>.log` |
| `--history FILE` | off | write every hand (all hole cards, board, log, results) as JSON lines |
| `--json FILE` | off | write the summary as JSON |
| `--calibrate` | | only measure your machine's reply-time floor (see below) |

It prints one row per entry:

```
entry         points   ±95%  places 1..8   decisions timeouts errors  late crash  p50us  p99us   maxus
```

* `points ±95%`: mean points per table and the half-width of a 95% confidence interval.
* `places`: how often the entry finished 1st, 2nd, ...
* `timeouts`: decisions auto-played because no reply came in time, or because the bot was busy.
* `errors`: malformed replies, and decisions while the process was dead.
* `late`: `table`, `end` or `over` messages not answered in time.
* `crash`: times the process died.
* `p50us p99us maxus`: engine-side reply times of the decisions that came back in time.

**Your machine is not the event's.** The event runs each table on dedicated cores. On a busy
laptop the operating system sometimes pauses a process for several milliseconds, and that shows
up as timeouts that are not your bot's fault. Every run prints a "machine floor" line: how a bot
that does nothing fared on your machine just now. If your timeouts look like the sample bots',
it is your machine; `--limit-ms 5` shows results without that noise. Your bot's own `p99us` is
the number to keep well under 1000.

Tests for the engine: `cd engine/tests && python3 -m unittest discover -s .`

## 7. The sample bots

| file | what it does |
|---|---|
| `bots/random_bot.py` | random legal actions |
| `bots/station.py` | checks or calls everything |
| `bots/tight.py` | tight-aggressive hold'em bot that ignores the Solo rule |
| `bots/solo_aware.py` | a reasonable bot that plays the Solo rule |

They are single files that speak the protocol directly. Beat them all.
