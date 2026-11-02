# River of Blood Hold'em: bot kit

You have 60 minutes to build a poker bot. This page is everything you need: the rules,
tonight's variant, the bot interface, how to submit, and how to test locally.
Python 3 standard library only. Nothing in the kit needs installing.

```bash
cp -r bots/template mybot                      # 1. start from the template
$EDITOR mybot/player.py                        # 2. write your strategy in choose()
python3 simulate.py mybot bots/random_legal bots/call_station -n 50   # 3. play 50 tables
cd mybot && zip -r ../mybot.zip player.py && cd ..                     # 4. submit mybot.zip
```

`python3 selftest.py` checks the kit itself (a few seconds).

---

## 1. The tournament

| | |
|---|---|
| Game | No-limit hold'em with the River of Blood variant (section 2) |
| Table | 8-bot sit-and-go, 2,000 chips each, seats drawn at random |
| Blinds | rise every 25 hands, schedule below (`data/blinds.json`) |
| Length | until one bot has every chip, or 200 hands; survivors at the cap are paid by ICM |
| Scoring | points by finishing place (`data/payouts.json`), summed over all your tables |
| Time | 1 ms wall clock per call into your bot (section 5) |
| Opponents | anonymous: you see seat numbers only, and seating is reshuffled every table |
| Instances | one fresh bot instance per table; nothing carries over between tables |

### Blind schedule

Every player dealt in posts the ante before the blinds. Antes are dead money: they are in
the pot, but they do not count toward the bet you must call.

| Level | Hands | Small blind | Big blind | Ante |
|---|---|---|---|---|
| 1 | 1-25 | 10 | 20 | 0 |
| 2 | 26-50 | 15 | 30 | 0 |
| 3 | 51-75 | 25 | 50 | 0 |
| 4 | 76-100 | 40 | 80 | 10 |
| 5 | 101-125 | 60 | 120 | 15 |
| 6 | 126-150 | 100 | 200 | 25 |
| 7 | 151-175 | 150 | 300 | 40 |
| 8 | 176-200 | 200 | 400 | 50 |

### Points by finishing place

| Place | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| Points | 50 | 25 | 15 | 10 | 0 | 0 | 0 | 0 |

Top half paid; each table hands out 100 points. Your score is the sum over all your tables.

- **Busting.** A bot with no chips after a hand is out at once and receives no more calls.
- **Several busts in one hand.** The bot that started the hand with more chips finishes
  higher. Equal starting stacks share the places, and each gets the average of the shared
  places' points (two bots tied for 4th-5th get 5 points each).
- **The 200-hand cap.** If two or more bots remain after hand 200, they split the places
  still open by ICM (Malmuth-Harville) on their chip stacks over those places' points.
  Three survivors with 8,000 / 5,000 / 3,000 chips get 35.9 / 29.8 / 24.3 points
  (`python3 -m kit.icm 8000 5000 3000`).

### House rules

Everything not listed is standard no-limit hold'em tournament play.

- **Button and blinds.** The button moves one seat clockwise (to higher seat numbers,
  wrapping 7 -> 0) every hand, skipping busted seats. The small blind is the next seat in
  after the button, the big blind the one after. There is no dead button or dead blind.
- **Heads-up.** The button posts the small blind and acts first preflop; the other bot
  posts the big blind and acts first on every later street.
- **Action order.** Preflop: the first seat after the big blind. Every later street,
  run streets included: the first seat clockwise from the button still able to bet.
- **Bet to call preflop** is the full big blind, even when the big blind is all-in for
  less. (The extra goes into a side pot, or back to you if nobody else matches it.)
- **Never more than can be matched.** When every other bot still in is all-in, the bet you
  must match is capped at the largest of their street totals; if you already have that
  much in, you are not asked to act. (Heads-up against a big blind all-in for 15, the
  small blind is offered fold or call 15; against one all-in for 5, it is not asked at all
  and gets its extra 5 back.)
- **Minimum bet** on any street is the big blind. **Minimum raise**: the raise increment
  must be at least the last full raise increment on this street (the big blind if none).
  An all-in may be for less.
- **Short all-ins do not reopen betting.** If you have already acted, you may raise again
  only if the bet has gone up by at least one full raise increment since your last action.
  One short all-in never reopens; several short all-ins that together add up to a full
  raise do (the TDA rule). A bot that has not yet acted on this street may raise (if it
  has chips beyond the call and an opponent can respond).
- **No raise without an opponent.** If every other bot still in is all-in, you can only
  call or fold.
- **Checking is free.** When you owe nothing, `fold` is not offered (and is illegal).
- **Uncalled chips** go back to the bettor at the end of the hand.
- **Side pots** are built from each bot's total contribution. Each pot goes to the best hand
  among the bots eligible for it; ties split it, and odd chips go one at a time to the
  winners in clockwise order starting from the seat after the button.
- **Showdown.** Every bot still holding cards shows. All-in bots are not shown early.
- **Errors.** A timeout, an exception, or an illegal response is played for you as a check
  if checking is free, otherwise a fold. The hand goes on.
- **Dealing.** A new shuffle every hand, no burn cards.

---

## 2. Tonight's variant: River of Blood

### Handout

> This year's variant is River of Blood Hold'em. Everything is standard no-limit hold'em up to
> and including the river. If the river card is red (a heart or a diamond), another community
> card is dealt, followed by another betting round. This repeats until a black card (a club or a
> spade) is dealt. The black card that ends the run gets its own betting round too. At showdown
> you make your best five-card hand from your two hole cards plus every community card on the
> board. The colors of the flop and turn cards don't matter; only the river and the cards after
> it do.

### What it means for your bot

- **Streets are numbered by board length**: 0 preflop, 3 flop, 4 turn, 5 river, then 6, 7, 8
  ... for each run card. Every run street is a full no-limit betting round (minimum bet =
  big blind, first to act = first seat clockwise from the button still able to bet).
- **The engine never says whether a street is the last one.** You work it out from the
  board you were sent: on street 5 or later, a black last card (`c` or `s`) means this is
  the final betting round; a red last card (`h` or `d`) means at least one more card is
  coming. Before the river you cannot know. The template has `last_round()` for this.
- **How often.** With the river dealt and the hand still contested, another card comes
  50% of the time, a second run card 24.5% of the time, a third 11.8%, a fourth (a
  9-card board) 5.5%; on average 0.96 run cards per river if nobody folds. A card from the
  river on is red with probability (26 - j) / (52 - j), where j is the number of red cards
  dealt before it from the river on.
- **Showdown** uses your two hole cards plus every board card: best five of 2 + N. With a
  long board, the board itself often plays and pots are chopped more often. `kit/cards.py`
  has an evaluator that takes any number of cards; you may copy it into your bot.
- **All-in.** If at most one bot can still bet and nothing is owed, the rest of the board,
  run included, is dealt with no betting (you still get a `see_cards` call per street).
- **Folds.** If everyone but one folds, the hand ends at once, even after a red card.
- `take_seat` tells you the variant: `{"name": "river_of_blood", "extends_on": ["h", "d"],
  "first_extending_street": 5}`.

---

## 3. The bot interface

Your bot is a class named `Player` in `player.py`. The engine builds it with no arguments
at the start of each table and then calls its methods as things happen: it tells you
about every event, one call per event, and asks you for a move when it is your turn.
**There is no state snapshot.** The decision request holds only your legal moves; the pot,
stacks and bets are yours to track from the events (the template does this already).

```python
class Player:
    def take_seat(self, table): ...        # once per table, before hand 1
    def start_hand(self, hand): ...        # hand starts: your hole cards, stacks, posts
    def see_cards(self, cards): ...        # new street: flop, turn, river, or a run card
    def see_action(self, action): ...      # any bot acted (you included), as it happens
    def see_showdown(self, showdown): ...  # cards shown at showdown
    def end_hand(self, result): ...        # pots, winners, new stacks, busts
    def choose(self, request):             # your turn: return a move
        return {"move": "call"}
```

Only `choose` is required. Leave out any event method you don't need; the engine skips
it. Calls for one hand arrive in this order:

```
start_hand
  see_action ...  (choose when it's your turn, then see_action for your own move)
see_cards street 3      see_action ... choose ...
see_cards street 4      see_action ... choose ...
see_cards street 5      see_action ... choose ...
see_cards street 6, 7 ...                       (River of Blood: while the last card is red)
see_showdown                                    (only if two or more bots reach showdown)
end_hand
```

### Conventions

- **Seats** are ints 0-7. Clockwise means increasing seat number, wrapping 7 -> 0. Dicts
  keyed by seat use int keys. You learn your own seat in `take_seat` (`table["seat"]`).
- **Cards** are two-character strings: rank `23456789TJQKA`, suit `c d h s`. `"Ah"`, `"Td"`.
  Hearts and diamonds are red; clubs and spades are black.
- **Streets**: 0 preflop, 3 flop, 4 turn, 5 river, 6+ run cards. Street = board length.
- **Amounts are street totals (raise-to).** Every `amount` in this API (in your response,
  in the options, in `see_action`) is the total a bot has put in *on this street* after the
  move, not the chips added. Facing a 60 bet with 20 already in, `{"move": "raise",
  "amount": 200}` makes your street total 200 and costs you 180 more. `paid` (in events) and
  `cost` (in options) are the chips that actually leave the stack. Antes are never part of
  a street total.
- **Payloads are yours.** Each call gets a fresh copy; keep it or change it as you like.

### `take_seat(table)`

Once per table, before hand 1. Shares the 1 s setup budget with importing `player.py` and
`Player()`; the place to build lookup tables.

| Field | Meaning |
|---|---|
| `seat` | your seat (int) |
| `seats` | all seats at the table, sorted |
| `starting_stack` | 2000 |
| `hand_cap` | 200 |
| `budget_ms` | time per call, 1.0 |
| `setup_ms` | setup budget, 1000.0 |
| `blinds` | the schedule: list of `{level, first_hand, last_hand, sb, bb, ante}` |
| `payouts` | points by place, best first: `[50, 25, 15, 10, 0, 0, 0, 0]` |
| `variant` | `{"name": "river_of_blood", "extends_on": ["h", "d"], "first_extending_street": 5}` |

```python
{'seat': 3, 'seats': [0, 1, 2, 3, 4, 5, 6, 7], 'starting_stack': 2000, 'hand_cap': 200,
 'budget_ms': 1.0, 'setup_ms': 1000.0,
 'blinds': [{'level': 1, 'first_hand': 1, 'last_hand': 25, 'sb': 10, 'bb': 20, 'ante': 0}, ...],
 'payouts': [50, 25, 15, 10, 0, 0, 0, 0],
 'variant': {'name': 'river_of_blood', 'extends_on': ['h', 'd'], 'first_extending_street': 5}}
```

### `start_hand(hand)`

The blinds and antes have already been posted when this arrives.

| Field | Meaning |
|---|---|
| `hand` | hand number at this table, from 1 |
| `level`, `sb`, `bb`, `ante` | this hand's blind level |
| `button`, `sb_seat`, `bb_seat` | seats (heads-up, `sb_seat == button`) |
| `order` | seats dealt in, clockwise from the seat after the button; the button is last |
| `stacks` | seat -> chips *before* posting |
| `posts` | list of `{seat, kind: "ante"/"sb"/"bb", paid, all_in}`, in posting order |
| `seat` | your seat |
| `hole` | your two cards |

```python
{'hand': 1, 'level': 1, 'sb': 10, 'bb': 20, 'ante': 0, 'button': 4, 'sb_seat': 5,
 'bb_seat': 6, 'order': [5, 6, 7, 0, 1, 2, 3, 4],
 'stacks': {5: 2000, 6: 2000, 7: 2000, 0: 2000, 1: 2000, 2: 2000, 3: 2000, 4: 2000},
 'posts': [{'seat': 5, 'kind': 'sb', 'paid': 10, 'all_in': False},
           {'seat': 6, 'kind': 'bb', 'paid': 20, 'all_in': False}],
 'seat': 3, 'hole': ['As', 'Kc']}
```

A blind post can be short (`paid` less than the blind, `all_in: True`); a bot can even be
all-in from the ante. The bet to match preflop is still the full big blind.

### `see_cards(cards)`

A new street. The street's bets start at 0.

| Field | Meaning |
|---|---|
| `street` | 3, 4, 5, then 6, 7, ... (= board length) |
| `cards` | the new cards (3 on the flop, else 1) |
| `board` | the whole board so far |

```python
{'street': 6, 'cards': ['8d'], 'board': ['3h', 'Ah', '9c', '8c', 'Qh', '8d']}
```

Here the river `Qh` was red, so street 6 came; `8d` is red too, so street 7 will come.

### `see_action(action)`

Every move at the table, in order, including your own (sent right after your `choose`
returns, showing what was actually played). Not sent for blinds and antes; those are in
`start_hand["posts"]`.

| Field | Meaning |
|---|---|
| `seat` | who moved |
| `street` | the street |
| `move` | `"fold"`, `"check"`, `"call"` or `"raise"` (a raise with no bet in front is an opening bet) |
| `amount` | that bot's street total after the move |
| `paid` | chips that left its stack with this move |
| `all_in` | true if that bot has no chips left |
| `auto` | `None` normally; `"timeout"`, `"exception"`, `"illegal"` or `"dead"` if the engine played the move for that bot |

```python
{'seat': 5, 'street': 0, 'move': 'raise', 'amount': 93, 'paid': 83, 'all_in': False, 'auto': None}
{'seat': 6, 'street': 0, 'move': 'call',  'amount': 93, 'paid': 73, 'all_in': False, 'auto': None}
{'seat': 7, 'street': 0, 'move': 'fold',  'amount': 20, 'paid': 0,  'all_in': False, 'auto': None}
```

(Seat 5 was the small blind: 10 in, raised to 93, paid 83. Seat 7 had limped for 20.)

### `see_showdown(showdown)`

Only when two or more bots still hold cards at the end. Sent before `end_hand`.

| Field | Meaning |
|---|---|
| `board` | the final board |
| `hands` | list of `{seat, hole, rank, best}`: hole cards, hand category, the five cards played |

```python
{'board': ['3h', 'Ah', '9c', '8c', 'Qh', '8d', '2h', 'Ad', '4c'],
 'hands': [{'seat': 1, 'hole': ['Jh', 'Qs'], 'rank': 'flush', 'best': ['Ah', 'Qh', 'Jh', '3h', '2h']},
           {'seat': 3, 'hole': ['As', 'Kc'], 'rank': 'full house', 'best': ['As', 'Ah', 'Ad', '8c', '8d']}]}
```

`rank` is one of: high card, pair, two pair, three of a kind, straight, flush, full house,
four of a kind, straight flush.

### `end_hand(result)`

| Field | Meaning |
|---|---|
| `hand` | hand number |
| `board` | the final board (shorter than 5 if the hand ended early) |
| `returned` | seat -> uncalled chips given back |
| `pots` | main pot first, then side pots: `{amount, eligible, winners, won: {seat: chips}}` |
| `stacks` | seat -> chips after the hand, for every bot that played it |
| `net` | seat -> chips won or lost this hand |
| `busted` | list of `{seat, places}`: bots out this hand and their place(s) (two places = a shared tie) |

```python
{'hand': 1, 'board': ['3h', 'Ah', '9c', '8c', 'Qh', '8d', '2h', 'Ad', '4c'], 'returned': {},
 'pots': [{'amount': 4198, 'eligible': [5, 1, 2, 3, 4], 'winners': [3], 'won': {3: 4198}}],
 'stacks': {5: 1187, 6: 1907, 7: 1980, 0: 1980, 1: 1187, 2: 1187, 3: 5385, 4: 1187},
 'net': {5: -813, 6: -93, 7: -20, 0: -20, 1: -813, 2: -813, 3: 3385, 4: -813},
 'busted': []}
```

If you are in `busted`, this is your last call at this table.

### `choose(request)` and your response

```python
{'hand': 1, 'street': 7, 'budget_ms': 1.0,
 'options': [{'move': 'fold'},
             {'move': 'call', 'amount': 509, 'cost': 509},
             {'move': 'raise', 'min': 1018, 'max': 1760}]}
```

| Field | Meaning |
|---|---|
| `hand`, `street` | where you are |
| `budget_ms` | your time for this call |
| `options` | exactly the legal moves, in this order when present: fold, check, call, raise |

The option dicts:

| Option | Offered when | Fields |
|---|---|---|
| `{"move": "fold"}` | you owe chips | |
| `{"move": "check"}` | you owe nothing | |
| `{"move": "call", "amount": A, "cost": C}` | you owe chips | `amount`: your street total after calling; `cost`: chips it takes. If you can't cover the bet, this is an all-in call for less. |
| `{"move": "raise", "min": L, "max": H}` | you may raise (or open-bet) | `min`, `max`: the legal street totals; `max` is all-in. If `min == max` the only raise is all-in. |

Return a dict:

```python
{"move": "fold"}
{"move": "check"}
{"move": "call"}                    # any "amount" you add is ignored
{"move": "raise", "amount": 300}    # street total, an int with min <= amount <= max
```

Returning one of the offered option dicts as-is works for fold, check and call.

**Legality is exact; nothing is rounded or clamped.** These are illegal and are played as
a check (if offered) or a fold: a `move` not in `options` (so `fold` when `check` is
offered, `check` when you owe chips, `raise` when no raise is offered); a raise `amount`
that is missing, not an `int` (`300.0` and `True` are illegal), or outside `[min, max]`;
anything that is not a dict. Every illegal response is counted, and the simulator prints
the first few with the reason.

### Tracking the hand

From the events alone:

- **pot** = sum of `paid` in `posts` and in every `see_action` since `start_hand`.
- **bet to match on this street** = the largest `amount` in this street's `see_action`s;
  preflop it starts at the big blind, after `see_cards` at 0 (capped as in the house rules
  when everyone else still in is all-in).
- **your cost to call** = that minus your own street total (also given as `cost` in the
  call option).
- **stacks** = `start_hand["stacks"]` minus each bot's `paid`; reset from `end_hand`.
- **last betting round?** `street >= 5 and board[-1][1] in "cs"`.

`bots/template/player.py` implements all of these.

---

## 4. Submission

- One `.zip` with `player.py` **at the top level** (not inside a folder) defining a class
  `Player` whose constructor takes no arguments.
- Python 3.10+, standard library only. Single file is simplest. Extra modules in the zip are
  imported relatively (`from . import tables`); data files are opened via
  `os.path.join(os.path.dirname(__file__), "tables.bin")`.
- At most 10 MB zipped.
- Your code may not use the network, start threads or processes, write files, or read
  anything outside its own folder. Use your own `random.Random()`; don't reseed the shared
  `random` module.
- A fresh copy of your module and a fresh `Player()` are made for every table. Nothing
  persists between tables.
- Test your exact zip before submitting: `python3 simulate.py mybot.zip bots/call_station`.
  A zip is unpacked into `.unpacked/` inside the kit.

---

## 5. Limits

| What | Limit | When over |
|---|---|---|
| `choose` | 1 ms wall clock per call | interrupted; the move becomes check (if free) or fold |
| each event method | 1 ms wall clock per call | interrupted; counted as a timeout; the hand goes on |
| setup: import + `Player()` + `take_seat` | 1 s per table | the seat check/folds for the whole table |
| memory | 256 MB per bot | official runner: the bot is stopped and check/folds (not enforced locally) |
| exceptions | n/a | as a timeout: the move becomes check/fold, an event is skipped |

- **How the clock works.** The engine reads `time.perf_counter()` immediately before and
  after each call. More than 1.000 ms is a timeout. On Linux and macOS the engine also
  interrupts your code at 1.05 ms (a `BaseException` raised inside it), so a slow bot loses
  that turn but never stalls the table. Catching that exception does not save you.
- **Garbage collection** runs between hands, never during your call.
- **Wall clock means wall clock.** If the operating system pauses the process during your
  call, that time counts. On a busy laptop this happens roughly once in tens of thousands of
  calls even to a bot that does nothing, so a rare timeout locally is not necessarily your
  code. The official runner uses idle dedicated cores. Leave headroom: aim for well under
  0.3 ms, watch the simulator's `max us` column, do heavy precomputation in setup, and
  import modules at the top of the file, not inside methods.
- An interrupted event method leaves your bookkeeping half-updated. Make it cheap, and
  robust to a missed event (the template is).

---

## 6. Running the simulator

```bash
python3 simulate.py [options] BOT [BOT ...]
```

Each `BOT` is a `player.py`, a folder containing `player.py`, or a submission `.zip`. Give 1
to 8; the list is repeated to fill the 8 seats (`simulate.py mybot bots/call_station` seats
four of each; `simulate.py mybot` plays eight copies of your bot).

| Option | Default | |
|---|---|---|
| `-n`, `--tables N` | 20 | tables (sit-and-gos) to play |
| `--seed S` | 1 | seeds seating, buttons and decks, so runs repeat (bots' own randomness aside) |
| `--budget-ms MS` | 1.0 | time per call; keep 1.0 to match the event |
| `--log FILE` | | every engine event as JSON lines, with all hole cards |
| `-q`, `--quiet` | | no progress line |

Example (`python3 simulate.py bots/template bots/random_legal bots/call_station -n 20 --seed 7`):

```
River of Blood: 20 tables, seed 7, 1 ms per call, interrupts on, 0.6 s
points by place: 50 / 25 / 15 / 10 / 0 / 0 / 0 / 0

bot              points     avg   1st  2nd  3rd  4th  5-8  cap  timeouts exceptions  illegal   mean us   max us
---------------------------------------------------------------------------------------------------------------
template#3        505.0   25.25     7    5    0    3    5    0         0          0        0       3.1    489.9
template#1        427.0   21.35     5    3    6    2    4    0         0          0        0       2.9    100.9
template#2        317.0   15.85     3    4    3    3    7    0         0          0        0       2.9    121.6
random_legal#1    175.0    8.75     1    3    2    2   12    0         0          0        0       3.0    497.9
call_station#2    172.0    8.60     1    3    3    1   12    0         0          0        0       1.4     74.0
random_legal#3    162.0    8.10     1    1    3    5   10    0         0          0        0       2.5     70.7
call_station#1    145.0    7.25     2    1    0    2   15    0         0          0        0       1.5     96.8
random_legal#2     97.0    4.85     0    0    3    6   11    0         0          0        0       2.5    137.9
...
hands 1753 (87.7 per table, 0 tables reached the cap), decisions 15463
River of Blood: 930 rivers dealt, 49.5% red (spec 50%); 0.832 run cards per river; longest board 12; 644 betting rounds on run streets
  another card after a contested river: 49.1% of 851 (spec 50.0%); 6th card: 47.5% of 404 (spec 49.0%); 7th card: 51.6% of 184 (spec 48.0%)
conservation: 1753 hands, 1822 pots, 2169656 chips through pots; run-rule violations 0
engine errors: 0
```

- `points` total over your tables, `avg` per table; `1st`..`5-8` finishing places; `cap`
  tables where you survived to hand 200 and were paid by ICM.
- `timeouts`, `exceptions` include event methods; `illegal` counts responses only. Below the
  table, each bot with problems gets its first three messages (which call, how long, the
  exception text, or why a response was illegal).
- `mean us`, `max us`: your `choose` time in microseconds. Watch `max`.
- Exit status is 1 if the engine itself failed (it should never).

---

## 7. ICM calculator

```bash
python3 -m kit.icm 8000 5000 3000                  # equities over the published points
python3 -m kit.icm 6000 4000 --payouts 50 25       # any payout list
```

```python
from kit.icm import icm_equity, finish_probabilities
icm_equity([8000, 5000, 3000], [50, 25, 15])   # -> [35.93, 29.78, 24.29]  (expected points)
finish_probabilities([8000, 5000, 3000])       # P[i][k]: player i finishes in place k+1
```

Malmuth-Harville: a player wins with probability stack / total; given who has taken the
places above, each remaining player takes the next place in proportion to their stack.
Exact over subsets; fine up to a dozen players. Copy it into your bot if you want ICM-aware
play near the bubble (4th of 8 pays, 5th does not).

---

## 8. Self-test

```bash
python3 selftest.py
```

Checks the evaluator against brute force on boards of up to 12 cards, ICM against brute
force, the exact legality rules on scripted hands (short all-ins, full and cumulative
raises, the full big blind, heads-up order, side pots, odd chips, two busts in one hand,
River of Blood runs, all-in run-outs, substituted moves), the sandbox (timeouts, runaway
loops, exceptions, setup failures, a chaos bot), an oracle bot that rebuilds every legal
option from the events alone using this README's rules and must agree with the engine on
every decision of 60 tables, and then plays 20 tables of the example bots: zero engine errors, every hand's chips conserved (re-added from the event stream),
and run streets at the rate the spec predicts. Ends with `SELF-TEST PASSED`.

---

## 9. What's in the kit

```
README.md              this handout
simulate.py            the local simulator (section 6)
selftest.py            the kit's self-test (section 8)
data/blinds.json       the blind schedule
data/payouts.json      points by finishing place
kit/engine.py          the dealer: one hand, betting, the red run, side pots, showdown
kit/tournament.py      sit-and-go tables, busts, the cap, ICM payout, many-table runs
kit/sandbox.py         loading bots, the 1 ms clock and interrupts, fault counting
kit/cards.py           cards and a best-five-of-any-number evaluator (copy it freely)
kit/icm.py             Malmuth-Harville ICM
kit/rules.py           constants and data-file loading
bots/template/         a legal, naive bot that tracks the hand: start here
bots/random_legal/     example: random legal moves
bots/call_station/     example: always check or call
tests/chaos/           a rule-breaking bot used by the self-test
tests/oracle/          a bot that re-derives the legal options from events (self-test)
```

## 10. What the local simulator does not do

- **Isolation.** Bots run in one Python process, not one process each, so a malicious bot
  could reach into the engine. The official runner uses one process per bot with the same
  timing rules.
- **Memory.** The 256 MB limit is not enforced locally.
- **Windows.** Without `SIGALRM` the clock is still measured and timeouts still count, but
  a bot that loops forever hangs the simulator. Use WSL, Linux or macOS.
- **C-level stalls.** A single long-running C call (a huge `sort`, big-integer arithmetic)
  cannot be interrupted until it returns; it still counts as a timeout.
