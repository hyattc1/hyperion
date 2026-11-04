# Tranche Hold'em: pokerbot build, starter kit

You have **60 minutes** to write a Python bot. At minute 60 you upload one zip. After the
build, every bot plays many thousands of 8-player sit-and-go tables, and your score is your
mean points per table.

This handout has every rule. If the code and this handout disagree, tell an organiser: the
handout is what we intend, and we fix the code.

**First five minutes:** read "The twist" and "Your bot", then run

```
python3 -m engine.sim agent_template.py bots/tight.py bots/tranche_bot.py bots/station.py -t 50
```

from this folder. You need Python 3.10 or later and nothing else.

---

## 1. The event at a glance

| | |
|---|---|
| Game | **Tranche Hold'em**: no-limit hold'em in which each street's chips are a separate pot, settled on the cards as they stood on that street (section 3) |
| Table | 8 bots, 2,000 chips each, no antes |
| Blinds | 10/20, rising every 25 hands (section 2.2) |
| Length | until one bot has every chip, or 200 hands |
| Scoring | points by finish position: **+16, +10, +6, +3, +1, 0, -1, -3** (section 4) |
| Decision limit | **1 ms** per decision, or you check if you can and otherwise fold. Errors count the same way |
| Your code | one module, `bot.py`, with module-level functions, no class (section 5) |
| Sandbox | Python 3.10, standard library only, no network, one core (section 7) |
| Submission | a zip with `bot.py` at its root, at most 5 MB (section 8) |

## 2. The table

### 2.1 Seats, button, blinds

* Eight seats. Every bot starts with 2,000 chips.
* The button starts on a random seat and moves one seat clockwise every hand, skipping seats
  whose bot is out. The small blind is the next live seat clockwise from the button and the big
  blind the next after that.
* **Heads-up** (two left): the button posts the small blind and acts first before the flop;
  the big blind acts first on every later street.
* A bot that cannot cover a blind posts what it has and is all-in. The others must still call
  the full big blind.
* There are no antes and no straddles.

### 2.2 Blind schedule

| Level | Hands | Small | Big |
|---|---|---|---|
| 1 | 1-25 | 10 | 20 |
| 2 | 26-50 | 15 | 30 |
| 3 | 51-75 | 25 | 50 |
| 4 | 76-100 | 40 | 80 |
| 5 | 101-125 | 60 | 120 |
| 6 | 126-150 | 100 | 200 |
| 7 | 151-175 | 150 | 300 |
| 8 | 176-200 | 250 | 500 |

The schedule is also in `engine/blinds.py` and in what `start()` and `table()` receive.

### 2.3 Dealing and betting

* Each hand uses a freshly shuffled 52-card deck. Two hole cards each, then a three-card flop,
  a turn card and a river card. There are no burn cards (they change nothing).
* There are four betting rounds: preflop, flop, turn, river. Preflop, action starts left of the
  big blind; after that, with the first bot still in the hand left of the button.
* No limit. The minimum bet is one big blind. A raise must add at least as much as the largest
  full bet or raise already made on this street (preflop the big blind counts as that bet).
  There is no cap on the number of raises.
* You may always go all-in. An all-in that adds less than a full raise does not reopen the
  betting: a bot that has already acted on this street and faces only that short all-in may
  call or fold, but not raise. (Two short all-ins that add up to a full raise do not reopen it
  either. This is simpler than the casino rule.)
* At the end of each betting round, any part of the top bet that nobody matched goes back to
  whoever bet it. The log records this (`u`, section 5.6).
* If everyone folds to one bot, it takes every chip put in this hand. Nothing is shown.

### 2.4 When the table ends

A bot whose stack is 0 after a hand is out. The table ends when one bot holds every chip, or
after hand 200. Finish order is in section 4.

## 3. The twist: Tranche Hold'em

**Each betting round's chips form their own pot, called a tranche. At showdown, each tranche
goes to the best hand as it stood on that street.**

| Tranche | Holds | Won by the best hand made from |
|---|---|---|
| 0 | the blinds and every preflop bet | your **two hole cards only** |
| 1 | every flop bet | your two hole cards + the **3 flop cards** (all five used) |
| 2 | every turn bet | the best five of your two + the **4 board cards** |
| 3 | every river bet | the best five of your two + all **5 board cards** (ordinary hold'em) |

The rules that go with it:

1. **Two-card hands (tranche 0).** A pair beats any non-pair; a higher pair beats a lower pair.
   Non-pairs compare the higher card, then the lower card. Suits never count, so A-K suited and
   A-K offsuit are equal. `2-2` beats `A-K`. `A-2` beats `K-Q`.
2. **Five-card hands (tranches 1-3)** are ordinary poker hands: straight flush, four of a kind,
   full house, flush, straight, three of a kind, two pair, pair, high card. The ace plays high,
   or low in A-2-3-4-5. Suits never break a tie.
3. **Side pots inside each tranche.** Within a tranche, chips are layered by what each bot paid
   *on that street*, exactly as in ordinary side pots. Each layer goes to the best hand among
   the bots still in the hand that paid up to that layer. A bot that went all-in on the flop
   has a stake in tranches 0 and 1 only: it paid nothing into tranches 2 and 3. Chips that
   folded bots put into a tranche stay in it as dead money. (If a layer has no bot still in the
   hand that paid up to it, its chips join the layer below.)
4. **Folding gives up every tranche**, including those of earlier streets you paid into.
   To collect anything you must be in the hand at the showdown (or be the last bot left).
5. **No cards after the betting is over.** If, after a betting round, at most one bot in the
   hand still has chips behind (everyone else is all-in or folded), no more cards are dealt.
   The later tranches are empty, so later cards could not change a thing. A preflop all-in is
   settled on two-card hands with no board at all.
6. **Ties** split the tranche (or layer). An odd chip goes to the first tied bot clockwise from
   the button.
7. **Showdown.** When two or more bots are still in at the end, every one of their hole cards
   is shown to the whole table (in `done()`, section 5.9).

**Worked example** (heads-up, blinds 10/20). You hold 2♣2♦, the other bot A♥K♥.
You raise to 100 and are called: **tranche 0 = 200**. Flop K♦ 7♠ 3♣: they bet 50, you call:
**tranche 1 = 100**. Turn 9♥: both check, **tranche 2 = 0**. River Q♥: they bet 100, you call:
**tranche 3 = 200**. Showdown:

* tranche 0 (two-card hands): your pair of twos beats ace-king. You get 200.
* tranche 1 (hole cards + K 7 3): their pair of kings. They get 100.
* tranche 3 (all seven cards): their kings. They get 200.

You put in 250 and get 200 back; they put in 250 and get 300. Had you folded to the river bet,
they would have taken all 400, your preflop tranche included. Had you both gone all-in
preflop, no board would have been dealt and your twos would have won everything.

The dealer's code for this is `Table._settle` in `engine/dealer.py`; the hand evaluators are
`rank2` and `best5` in `engine/cards.py` (you may copy that file into your zip).

## 4. Points

| Finish | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| Points | **+16** | **+10** | **+6** | **+3** | **+1** | **0** | **-1** | **-3** |

* Bots knocked out earlier finish lower. Bots knocked out on the same hand finish in order of
  the stacks they started that hand with (more chips finishes higher).
* If the table reaches hand 200, the bots still in are ranked by stack.
* Bots that tie (same hand and same starting stack, or the same stack at hand 200) share the
  places they span and split those points evenly: two bots tied for 7th and 8th get -2 each.
* Chips are worth nothing once the table ends; only the finish counts.
* **Your score** is your mean points per table over all your tables. Eight bots share 32 points
  a table, so the field averages +4. Ties on score are broken by the number of first places.

`engine/payouts.py` holds the table and these rules. `engine/icm.py` turns stacks into
expected points (Malmuth-Harville ICM): `python3 -m engine.icm 4000 3000 2000 1000`.

## 5. Your bot

### 5.1 The module

Your bot is one Python module, `bot.py`, with **module-level functions**. There is no class to
subclass and nothing to import from us.

```python
def start(session): ...   # optional: once per session, before any table      3000 ms
def table(info): ...      # optional: at the start of every table                50 ms
def act(v): ...           # required: every decision; returns an int              1 ms
def done(h): ...          # optional: after every hand you were dealt into        1 ms
```

**One module plays a whole session.** Your module is imported once per session and plays many
tables one after another, never two at once. Module globals survive from table to table, so
you can learn across tables; reset per-table notes in `table()`. A session is a few hundred
tables; each new session is a fresh process that imports your module and calls `start()` again.

`agent_template.py` is a complete, legal bot. Start from it.

### 5.2 Cards are integers

```
card = 4 * rank + suit         0..51
rank = card >> 2               0 = two, 1 = three, ..., 8 = ten, 9 = jack, 10 = queen, 11 = king, 12 = ace
suit = card & 3                0 = clubs, 1 = diamonds, 2 = hearts, 3 = spades
```

So `0` is 2♣, `51` is A♠, and two cards pair when `a >> 2 == b >> 2`. `engine/cards.py` has
`card_str`, `parse_card`, `rank2` and a fast `best5`.

### 5.3 Seats are relative to you

Every per-seat field is a tuple of 8 indexed by **relative seat**: **0 is you**, 1 is the seat
to your left (it acts after you), 2 the next, and so on round to 7, the seat to your right. A
seat keeps its relative number for the whole table, including after it is knocked out. You are
never told which team sits where, and seats are drawn afresh for every table.

### 5.4 `act(v)`: what you see

`v` has these attributes (all plain ints, strings and tuples):

| Field | Type | Meaning |
|---|---|---|
| `hole` | `(int, int)` | your two cards |
| `board` | tuple of 0, 3, 4 or 5 ints | the board so far |
| `street` | int | 0 preflop, 1 flop, 2 turn, 3 river; also the tranche now being bet |
| `to_call` | int | chips you must put in to call. 0 means you can check. Never more than `stack` (if you cannot cover the bet, calling puts you all-in) |
| `min_raise` | int | the smallest return value that bets or raises (section 5.5). **0 when you may not raise**: nobody else could call, betting was not reopened to you, or your stack is no more than `to_call`. If a full raise needs more chips than you have, it is your stack |
| `stack` | int | your chips behind, not counting what you have put in this hand |
| `stacks` | 8 ints | chips behind for each relative seat (`stacks[0] == stack`); 0 for a seat that is out |
| `seats` | str of 8 chars | each relative seat: `p` in the hand with chips behind, `a` in the hand and all-in, `f` folded this hand, `x` out of the table |
| `paid` | 8 tuples of 4 ints | `paid[s][k]`: chips relative seat `s` has put into tranche `k` this hand (after any uncalled chips came back) |
| `tranches` | 4 ints | chips in each tranche so far (`tranches[k] == sum(p[k] for p in paid)`) |
| `button` | int | relative seat of the button |
| `sb`, `bb` | int | this hand's blinds |
| `hand` | int | hand number at this table, 1..200 |
| `level` | int | blind level, 1..8 |
| `log` | str | everything that has happened this hand (section 5.6) |

There is no list of legal actions: `to_call` and `min_raise` tell you everything.

### 5.5 `act(v)`: what you return

**Return one int: the number of chips to put in now.**

| You return `n` | It means |
|---|---|
| `n < to_call` (for example 0, or -1) | **fold**; or **check** if `to_call == 0` |
| `to_call <= n < min_raise`, or `n >= to_call` when `min_raise == 0` | **call** `to_call` chips (a check when `to_call == 0`) |
| `n >= min_raise > 0` | **bet or raise**, putting in `n` chips; `n >= stack` puts you all-in |

So `return 0` is check-or-fold, `return v.to_call` is check-or-call, and `return v.stack`
is all-in. The amount is what you add now, not a total: facing a bet of 60 when you have
put in 20 on this street, `to_call` is 40, and returning 140 raises by 100 (to a total of 160).

A float is truncated to an int (`int(n)`). Anything else (None, a string, a bool, NaN) is an
error, which counts as returning 0.

### 5.6 The log

`v.log` is the hand so far as text, seats relative to you:

```
log    = street ("/" street)*      one part per street reached; the number of "/" is v.street
street = token (" " token)*        or empty, if nobody has acted yet on this street
token  = seat code [chips] ["!"]
seat   = 0..7                      relative seat
code   = s   posts the small blind      b   posts the big blind
         f   folds                      k   checks
         c   calls                      r   bets or raises
         u   gets uncalled chips back at the end of the street
chips  = chips put in by this action (s, b, c, r) or given back (u)
!      = that bot is now all-in
```

Example, seen by the bot on the button three-handed (you are 0, the blinds are 1 and 2):

```
1s10 2b20 0r60 1c50 2f/1k 0r80 1c80/1r200 0c200/1k
```

You raised to 60, the small blind called, the big blind folded; on the flop the small blind
checked, you bet 80 and were called; on the turn it bet 200 and you called; on the river it
has checked, and it is your turn. A timeout or error shows as the check or fold it produced.

### 5.7 `table(info)`

Called once at the start of each table, before its first hand. Fields:

| Field | Type | Meaning |
|---|---|---|
| `table` | int | table id within this session |
| `seats` | int | 8 |
| `stacks` | 8 ints | starting stacks by relative seat (all 2000) |
| `button` | int | relative seat of the first hand's button |
| `blinds` | tuple of 8 `(small, big)` | the schedule, level 1 first |
| `hands_per_level` | int | 25 |
| `max_hands` | int | 200 |
| `points` | 8 ints | points for 1st..8th |

### 5.8 `start(session)`

Called once per session, before the first table. Load anything you shipped in your zip here.

| Field | Type | Meaning |
|---|---|---|
| `data_dir` | str | the folder your zip was unpacked into: open your data files from here |
| `limits_ms` | dict | `{"start": 3000, "table": 50, "act": 1, "done": 1}` |
| `seats`, `starting_stack`, `blinds`, `hands_per_level`, `max_hands`, `points` | | as in `table()` |
| `tables` | int or None | how many tables this session will play, if known |

### 5.9 `done(h)`

Called after every hand you were dealt into, including the one that knocks you out. Fields
(per-seat tuples are relative, as always):

| Field | Type | Meaning |
|---|---|---|
| `hand` | int | hand number |
| `board` | tuple of ints | the cards dealt (fewer than 5 if the hand ended early, or if betting ended early: section 3, rule 5) |
| `shown` | 8 entries | `(int, int)` hole cards for every seat that reached a showdown, and always for you; `None` otherwise |
| `paid` | 8 tuples of 4 ints | final chips each seat put into each tranche |
| `awards` | 4 tuples of 8 ints | `awards[k][s]`: chips seat `s` won from tranche `k` |
| `won` | 8 ints | chips each seat collected in total (`sum(paid[s])` was its cost) |
| `stacks` | 8 ints | stacks after the hand; 0 means knocked out |
| `log` | str | the complete log |

## 6. Time limits

| Call | Limit | If it runs over the limit or raises |
|---|---|---|
| `start(session)` | 3000 ms, once per session | you sit out the whole session: every decision checks if it can, otherwise folds |
| `table(info)` | 50 ms, once per table | you sit out that table (same), and `done()` is not called for it |
| `act(v)` | **1 ms, every decision** | treated as returning 0: **you check if you can, otherwise fold** |
| `done(h)` | 1 ms, every hand | nothing happens to your play; the event log counts it |

How the limits are enforced, in the event and in the local simulator alike:

* The time is the **wall-clock time of the call itself**, measured with `time.perf_counter()`
  just before your function is called and just after it returns. Building `v` is not charged
  to you.
* When a call starts, a timer is set for its limit (`signal.setitimer`). If your code is still
  running when it fires, an `Overtime` exception is raised inside your code. `Overtime`
  derives from `BaseException`, so `except Exception:` does not catch it. **Do not use a bare
  `except:`**, or you will swallow it and run on.
* A call that returns after its limit (for example because it was stuck inside one long C call
  such as a huge `sorted()` when the timer fired) is treated exactly as if it had been stopped.
* The garbage collector is off while tables are played and runs between tables, so a
  collection never lands inside your call.
* Your code can be stopped at any line. Keep state updates that must not be half-done short.
* In the event each table runs on its own otherwise idle core. Python is slow: 1 ms is about 200
  `best5` evaluations and nothing else. Precompute in `start()`, and if
  you sample, watch `time.perf_counter()` and stop at about 0.3 ms.

On a busy laptop the operating system sometimes pauses the whole simulator for a few
milliseconds, and wall-clock time then charges your bot for it. `--clock cpu` (section 9)
measures CPU time instead, so you can tell your own slowness from your laptop's.

## 7. The sandbox

* CPython 3.10 with the standard library only. No third-party packages; compiled extension
  files in your zip will not load.
* One CPU core, 1 GB of memory, no network.
* Do not start threads or processes; the sandbox does not allow it.
* Your zip is unpacked into `session.data_dir` and that folder is on `sys.path` while
  `bot.py` is imported, so `import helper` works for a `helper.py` next to `bot.py`.
  **Put your imports at the top of `bot.py`**: the folder is not on `sys.path` afterwards.
* Files are read-only. Anything you want to keep, keep in memory.
* In the event your stdout and stderr are discarded. Locally, printing is slow enough to
  cost you timeouts.

## 8. Submission

* **One zip per team, uploaded on the submission page before minute 60.** The last upload
  before the deadline counts.
* **`bot.py` at the root of the zip** (not inside a folder). It may sit next to other `.py`
  modules and data files.
* **Size cap: 5 MB zipped, 25 MB unpacked.**
* Name the zip after your team, for example `team-17.zip`.
* Check it before you upload: `python3 -m engine.check team-17.zip`. It checks the layout and
  the caps, loads your bot the way the event does, plays 20 tables against the sample bots and
  lists any timeout or error.

To build the zip from a folder holding `bot.py`:

```
cd mybot && python3 -c "import zipfile,os; z=zipfile.ZipFile('../team-17.zip','w',zipfile.ZIP_DEFLATED); [z.write(f) for f in os.listdir('.') if os.path.isfile(f)]"
```

(or `zip -r ../team-17.zip .` inside the folder, if you have `zip`).

**How the event runs.** Each table seats 8 different teams, drawn at random. Every team plays
the same number of tables, several thousand. A bot that fails to load scores as a bot that
always checks or folds.

## 9. The local simulator

Run everything from this folder.

```
python3 -m engine.sim BOT [BOT ...] [-t TABLES] [--seed S] [--workers 1|2] [--clock wall|cpu]
                      [--limit-ms X] [--no-limits] [--history FILE] [--quiet]
```

* `BOT` is a `.py` file, a folder holding `bot.py`, or your submission `.zip`. Give one to
  eight; with fewer than eight the list repeats to fill the seats (`a.py b.py` gives four of
  each). Every seat is its own copy of the module with its own globals and its own `start()`.
* Physical seats are shuffled every table, so no bot keeps the same neighbours.
* `-t` tables (default 200); `--seed` fixes the deck (same seed, same cards).
* `--workers 2` uses two processes; each is its own session.
* `--clock cpu` measures your calls in CPU time instead of wall-clock time (section 6).
* `--limit-ms` loosens the act/done limit for a slow laptop; `--no-limits` switches every limit
  off so you can use a debugger. The event uses 1 ms on the wall clock.
* `--history FILE` writes the first table's full hand history, readable, with every hole card.

Example (on the organisers' shared build machine, which was heavily loaded; hence the
timeouts, see section 6):

```
$ python3 -m engine.sim bots/tranche_bot.py bots/tight.py bots/station.py bots/random_bot.py -t 300 --workers 2 --quiet
Tranche Hold'em: 300 tables, 58505 hands, 11.5s (26.17 tables/s), 2 workers; limits act 1.000 ms, done 1.000 ms, table 50 ms, start 3000 ms (wall clock)
points +16/+10/+6/+3/+1/+0/-1/-3; 195.0 hands per table; 86% of tables reached hand 200, with 2.3 bots left on average

seat bot                              pts   ±95%  place  1st% out1% decisions   t/o  err   sit mean_us  p99_us  max_us
S0   bots/tranche_bot.py          +10.590  0.527   2.07  36.0   0.0    55964   449    0     0    88.2     630   19657
S1   bots/tight.py                 +6.750  0.548   3.09  14.7   2.0    48042    34    0     0     8.7      30    8395
S2   bots/station.py               -0.867  0.184   6.61   0.0  48.7    11611     2    0     0     3.0      10    8773
...
by bot file
x2   bots/tranche_bot.py          +10.382  0.384   2.13  35.8   0.2   110410   884    0     0    88.7     640   26136
...
```

Columns: `pts` mean points per table and its 95% confidence interval; `place` mean finish;
`1st%` how often the seat won; `out1%` how often it was first out; `decisions`, `t/o`
(act timeouts), `err` (act errors), `sit` (decisions made for a seat that was sitting out); and
`act()` time: mean, 99th percentile and maximum, in microseconds. A second block sums the seats
that run the same file. Notes at the end show the first few timeouts and errors with their
messages, and any failed `start()` or `table()`.

Other tools:

```
python3 -m engine.check team-17.zip          # check a submission
python3 -m engine.icm 4000 3000 2000 1000    # ICM: expected points for these stacks
python3 -m engine.blinds                     # print the blind schedule
python3 -m engine.payouts                    # print the points and finish rules
python3 -m unittest discover -s tests        # the engine's own tests
```

## 10. What is in the kit

```
README.md               this handout
agent_template.py       a minimal legal bot in this interface
engine/dealer.py        the table: dealing, betting, tranches, settlement, finish order
engine/cards.py         card encoding, rank2 (two-card hands), best5 (5-7 cards); copy it freely
engine/seat.py          loading bots, the time limits
engine/sim.py           the local simulator
engine/check.py         the submission checker
engine/icm.py           ICM calculator
engine/payouts.py       the points table and finish rules
engine/blinds.py        the blind schedule
bots/random_bot.py      random legal actions
bots/station.py         calls everything
bots/tight.py           a tight-aggressive bot that plays ordinary hold'em
bots/tranche_bot.py     a bot that plays the twist reasonably
bots/handeval.py        evaluator used by the sample bots (a copy of engine/cards.py)
tests/test_engine.py    the engine's tests
TESTS.md                how the engine was checked
```

## 11. Small print

* No cards are ever shown except at a showdown; the log never tells you who timed out.
* Your relative seat numbers say nothing about which team is which, and the event never tells
  you who your opponents are.
* `v` is a fresh object every call; changing it changes nothing.
* The deal is uniform: `random.Random` seeded per table, `shuffle` of 52 cards.
* If you find a bug in the dealer, tell an organiser at once. A bug that is reported is fixed
  for everyone; exploiting one gets the team removed.
