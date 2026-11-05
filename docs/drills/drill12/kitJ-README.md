# Trailing Stop Hold'em: team handout

You have 60 minutes to build a Python bot. It plays 8-player sit-and-go tables of no-limit hold'em with one twist: **every player has a trailing stop, and closing a hand below it eliminates you, however many chips you still hold.**

Read the twist and the interface sections carefully. Both differ from what you may have prepared for.

## 1. The event

- 8 bots at a table, 2,000 chips each, up to 200 hands, many thousands of tables.
- Blinds start at 10/20 and rise every 25 hands.
- You score points by finish position at each table.
- Each decision must come back within 1 ms. If it does not, or if your code raises an error or returns something invalid, your bot checks if it can and otherwise folds.
- Bots run in isolated sandboxes with no network access.

## 2. The twist: the trailing stop

Every player has a **peak** and a **stop**.

- Your **peak** is the highest stack you have closed a hand on. It starts at 2,000 and never falls.
- Your **stop** is 60% of your peak, rounded up to a whole chip. It starts at 1,200 and never falls.

At the close of every hand, after all pots are paid:

1. **The mark.** Every player's stack is compared with their stop, all at the same moment. A player below their stop is **stopped out** and leaves the table. A player exactly on their stop survives.
2. **The liquidation.** A stopped-out player's remaining chips are split equally among the survivors. Any odd chips go one each to the survivors in clockwise order, starting from the first survivor left of the button.
3. **The new peaks.** Each survivor whose stack is now above their peak has a new peak, and a new stop to match. A dividend can raise a peak, the same as a pot can.

A dividend never saves anyone in the hand that paid it, because the mark comes first. Running out of chips is the same thing as being stopped out with 0 chips.

**Example.** You win pots up to 3,500, so your peak is 3,500 and your stop is 2,100. You then call a 1,500 shove and lose. You close the hand on 2,000, which is below 2,100. You are eliminated, and your 2,000 chips go to the survivors. If 6 players survive, they get 333 each, and the first 2 left of the button get 1 more.

The stop is checked only at the close of a hand. During a hand, your chips behind can be below your stop, and winning the pot can bring you back above it. If your chips behind are below your stop and you fold, you are out.

Everyone's stack, peak and stop are public. The `decide` call gives you all three for every player at the table.

## 3. The rest of the rules

Apart from the stop, this is standard no-limit hold'em table stakes.

**Blind schedule.** The level depends only on the hand number.

| Level | Hands | Small blind | Big blind |
|---|---|---|---|
| 1 | 1-25 | 10 | 20 |
| 2 | 26-50 | 15 | 30 |
| 3 | 51-75 | 25 | 50 |
| 4 | 76-100 | 40 | 80 |
| 5 | 101-125 | 60 | 120 |
| 6 | 126-150 | 100 | 200 |
| 7 | 151-175 | 150 | 300 |
| 8 | 176-200 | 250 | 500 |

There are no antes.

**Seats and button.** Seating and the first button are random. The button moves to the next remaining player each hand. The next two remaining players post the small and big blinds. Heads-up, the button posts the small blind.

**Dealing.** One standard 52-card deck, freshly shuffled each hand. Two hole cards each, then flop, turn and river, with a betting round after the deal and after each street.

**Order of action.** Before the flop, the first player after the big blind acts first. After the flop, the first remaining player left of the button acts first. Heads-up, the button acts first before the flop and the big blind acts first after it.

**Betting.**

- A short blind still sets the full price. If the big blind has 7 chips left, the price to call is still one full big blind.
- The smallest raise is the size of the last full raise on this street, and at least one big blind.
- You can always go all-in for less than a full raise. An all-in raise that is short of a full raise does not reopen betting: a player who has already acted on this street may only call or fold when it comes back to them. Players who have not yet acted may still raise. Short raises do not add together.
- You may fold when you could check. The fold stands.
- You are not asked to act if nobody could respond and you owe nothing.

**Showdown and pots.** Best five of seven cards wins. All-ins make main and side pots in the usual way. Chips from folded players stay in the pots. An uncalled bet comes back to the bettor. When a pot is split, odd chips go one each to the winners in clockwise order from the first player left of the button. Cards of everyone still in at a showdown are shown to all, in the recap.

**How a table ends.** When one player remains, or after hand 200, whichever comes first.

## 4. Finish positions and points

| Place | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
|---|---|---|---|---|---|---|---|---|
| Points | 14 | 9 | 6 | 4 | 3 | 2 | 1 | 0 |

- The later you are eliminated, the better you place.
- Players eliminated in the same hand rank among themselves by the chips they held at the mark (more is better), then by their stack at the start of the hand.
- If a table reaches the end of hand 200, the survivors rank by stack after the mark and the liquidation of that hand. Peaks and stops do not matter for this ranking.
- Players still equal share their places: each gets the average of the points for those places.

Your score is your mean points per table. See `engine/PAYOUTS.md` for the same rules in brief.

## 5. The interface

Your submission is a module with one function. Read this section closely. The shape is unusual on purpose.

```python
def sit_down(table):
    # called once per table: you have 25 ms
    def decide(v):
        # called for each of your decisions: you have 1 ms
        return "c"
    return decide
```

`sit_down(table)` is a plain module-level function, called once for each table you are seated at. It returns the function that makes your decisions at that table. Keep per-table state in that closure. There are no other callbacks: everything else you need reaches you through `decide`.

**Module globals** survive from table to table in one process, which is good for lookup tables. Do not depend on it: the event's runner may start a new process at any time.

**Players have no fixed identity.** At each table every player gets a new random 2-letter tag, such as `"qx"`. Tags are fair within a table and mean nothing across tables. There are no seat numbers.

**All amounts are floats in big blinds of the current level, not chips.** Your 2,000 chips are 100.0 at level 1 and 66.67 at level 2. When the level rises, every number shrinks, including your stop. To get chips back, multiply by `v.bb`.

### Cards

A set of cards is one Python `int` used as a bit mask. A card is one bit:

```
bit = 13 * suit + (rank - 2)      rank: 2..14, ace = 14
                                  suit: 0 clubs, 1 diamonds, 2 hearts, 3 spades
```

So the ace of hearts is bit 38, `1 << 38`. Each suit is a 13-bit block, and `(mask >> 13 * suit) & 0x1FFF` gives that suit's ranks with the deuce as the lowest bit. `agent_template.py` has a short decoder, and `engine/hand_eval.py` scores any 5 to 7 card mask.

### `table`, passed to `sit_down`

| Field | Type | Meaning |
|---|---|---|
| `me` | str | Your tag at this table |
| `tags` | tuple of str | All 8 tags, in clockwise seat order |
| `start_chips` | int | 2000 |
| `blinds` | tuple of (int, int) | (small, big) in chips for levels 1 to 8 |
| `hands_per_level` | int | 25 |
| `hand_cap` | int | 200 |
| `stop_fraction` | float | 0.6 |
| `points` | tuple of int | Points for places 1 to 8 |
| `decision_limit_ms` | float | 1.0 |
| `setup_limit_ms` | float | 25.0 |
| `seed` | int | A number for seeding your own random generator |

### `v`, passed to `decide`

| Field | Type | Meaning |
|---|---|---|
| `hand` | int | Hand number, from 1 |
| `level` | int | Blind level, 1 to 8 |
| `bb` | int | Chips in one big blind at this level |
| `next_level_in` | int | Hands left at this level, counting this one |
| `street` | int | 0 preflop, 1 flop, 2 turn, 3 river |
| `hole` | int | Your two cards, as a mask |
| `board` | int | The board so far, as a mask |
| `pot` | float | All chips put in this hand so far, including uncalled ones |
| `owe` | float | What calling costs you now, 0.0 if you can check. Never more than your stack |
| `min_raise` | float | The smallest raise-by you can make. If you can only raise all-in for less than a full raise, this equals `max_raise`. 0.0 if you cannot raise |
| `max_raise` | float | The largest raise-by you can make: your stack minus `owe`. 0.0 if you cannot raise |
| `me` | int | Your index in `players` |
| `button` | int | The button's index in `players` |
| `players` | tuple of Player | Everyone left at the table, clockwise from the small blind. Index 0 posted the small blind and index 1 the big blind. Eliminated players are not listed |
| `log` | str | This hand's actions so far, see below |
| `recap` | tuple of Recap | Every hand finished since your last decision, oldest first. Usually one, and empty for later decisions in the same hand |

Legal actions are not listed. They follow from `owe`, `min_raise` and `max_raise`.

**Player**

| Field | Type | Meaning |
|---|---|---|
| `tag` | str | Their tag |
| `stack` | float | Chips behind, not counting what they have put in this hand |
| `peak` | float | Their peak |
| `floor` | float | Their stop. A player with `stack < floor` is past their stop: if they do not win chips in this hand, they are out |
| `bet` | float | Put in on this street |
| `in_pot` | float | Put in this hand, including this street |
| `state` | str | `"L"` in the hand and able to act, `"A"` all-in, `"F"` folded |

**Recap**

| Field | Type | Meaning |
|---|---|---|
| `hand` | int | The hand's number |
| `bb` | int | Chips in one big blind in that hand. The other amounts are in these units |
| `log` | str | The hand's full log |
| `board` | int | The board as far as it was dealt |
| `shown` | tuple of (str, int) | (tag, hole mask) for each player at a showdown. Empty if there was none |
| `net` | tuple of (str, float) | (tag, stack change over the hand). A survivor's figure includes the dividend. An eliminated player's figure does not count the chips they forfeited |
| `out` | tuple of str | Tags eliminated in that hand, best place first |
| `dividend` | float | The dividend per survivor, before odd chips. 0.0 if nobody was out |

### The log

The log is a string of tokens separated by spaces. A `/` token marks each new street, and appears even when an all-in leaves no one to act.

```
qxS0.5 mvB1 tkF abC1 cdR2 qxF mvC2 / mvK cdR1.5! mvF
```

Each token is a 2-letter tag, one verb, then the amount where there is one:

| Verb | Meaning | Amount |
|---|---|---|
| `S` | Posted the small blind | Paid |
| `B` | Posted the big blind | Paid |
| `F` | Folded | None |
| `K` | Checked | None |
| `C` | Called | Paid, which may be less than the price if all-in |
| `R` | Raised | The raise-by on top of the price |

A trailing `!` means that action put the player all-in. Amounts are in big blinds, printed by Python's `%g`: short decimals such as `0.5`, `1.33333`, and possibly exponents such as `1e+06`. Automatic check/folds after a timeout or an error look like any other `K` or `F`.

### Your answer

`decide` returns a string.

| Answer | Meaning |
|---|---|
| `"f"` | Fold |
| `"c"` | Check if you owe nothing, otherwise call |
| `"r<x>"` | Raise by `x` big blinds **on top of the call**. You pay `owe + x` |

So facing a price of `owe = 2`, the answer `"r3"` pays 5 big blinds, and raises the price by 3. This is a raise-by, not a raise-to.

`x` is read with Python's `float()` and must be positive and finite. It is multiplied by the current big blind and rounded to the nearest chip, halves up. Then:

- Below `min_raise`, it is lifted to `min_raise`.
- Above `max_raise`, it is cut to `max_raise`, which is all-in. `"r1000000"` is a safe way to shove.
- If you cannot raise (`max_raise` is 0.0), it is treated as `"c"`.

None of those three cases counts as an error. Anything else is an error: any other string, `"r0"`, `"r-3"`, `"rnan"`, `"rinf"`, or any value that is not a string.

### What happens on a failure

| Failure | Consequence |
|---|---|
| `decide` is over 1 ms, raises, or returns an invalid answer | That decision becomes check if you owe nothing, otherwise fold. The late answer is thrown away. Your bot keeps playing |
| `sit_down` is over 25 ms, raises, or returns something not callable | You play that whole table on check/fold autopilot |
| The bot fails to import, or takes over 5 s to import, or has no `sit_down` | You play every table on check/fold autopilot |

The autopilot makes no exception for your stop. A check/fold bot past its stop folds and is out.

## 6. Time limits

| Call | Limit | Hard stop | How often |
|---|---|---|---|
| Importing your bot | 5 s | 15 s | Once per process, per seat |
| `sit_down(table)` | 25 ms | 500 ms | Once per table |
| `decide(v)` | 1 ms | 50 ms | Once per decision |

There are no timed callbacks other than these, and there is no shared time bank. Unused time does not carry over.

**How the limit is enforced.** The harness reads the clock immediately before and immediately after your call, and discards the answer if the gap is over the limit. Building `v` happens before the first reading and is not charged to you. Python cannot stop a function from outside at an exact moment, so your code keeps running until it returns. Past the hard stop, a 20 ms tick raises an exception inside your code to interrupt it. It derives from `BaseException`, so do not catch `BaseException` or use a bare `except:`. A call stuck inside a long C function cannot be interrupted until that function returns.

**The clock is the wall clock** (`time.perf_counter_ns`), both in the event and by default in the simulator. A busy laptop will show stray timeouts, so `--clock cpu` is there for checking your own code.

**Garbage collection.** The harness turns off automatic garbage collection during a table and collects between tables, on its own time. If you call `gc.collect()` yourself, that is your time.

Do your slow work at import: tables, caches, and warming up anything that runs slowly the first time.

## 7. Submitting

Submit one zip file.

```
team.zip
├── bot.py        required, at the root of the zip, with sit_down(table)
├── helper.py     optional: your other modules
└── table.bin     optional: your data files
```

- **Size:** at most 5 MiB zipped, 25 MiB unzipped, 2,000 files.
- **No top-level folder.** `team/bot.py` is refused. Symlinks and paths with `..` are refused too.
- **Python:** CPython 3.10, standard library only.
- **Imports go at the top of your files.** Your folder is on the import path only while your bot is being imported, so an import inside `decide` of your own helper module fails.
- **The kit is not in the sandbox.** Your bot cannot import `engine`. To use `hand_eval.py` or `icm.py`, copy them into your zip. Loaded alone, `icm.equities` needs its payouts passed in, such as `table.points`.
- **Data files:** find them with `os.path.dirname(__file__)`. They are read-only in the event.
- **Output:** stdout and stderr are discarded in the event. The simulator discards stdout.
- **Randomness:** use your own generator: `random.Random(table.seed)`. The simulator runs all bots in one process, so the shared `random` module's sequence depends on what other bots draw.

Make the zip with:

```
cd my_bot && python3 -m zipfile -c ../team.zip bot.py helper.py
```

## 8. The local simulator

Run it from the root of the kit. It needs only Python, and it was tested on CPython 3.10 on Linux. On Windows, `--workers` above 1 and the hard stops are not available.

```
python3 -m engine.sim bots/random_legal.py bots/station.py bots/tight.py bots/deskhand.py --tables 300
python3 -m engine.sim my_bot.py bots/tight.py bots/deskhand.py --tables 1000 --seed 7 --workers 2
python3 -m engine.sim team.zip bots/tight.py --tables 200 --trace hands.txt --trace-tables 2
```

Pass 1 to 8 bots, as `.py` files or submission zips. A shorter list is repeated until all 8 seats are filled, and each seat loads its own copy of the bot. Every table reshuffles who sits where and renames everyone.

A `.py` file is loaded directly, under any name. A zip goes through the same checks as a real submission.

| Option | Default | Meaning |
|---|---|---|
| `--tables`, `-T` | 200 | Tables to play |
| `--seed` | 1 | The same seed and bots give the same cards and seating, whatever `--workers` is. Results can still differ between runs if a timeout lands differently, or if a bot keeps state between tables |
| `--workers` | 1 | Processes to use, counting the main one |
| `--clock` | `wall` | `wall` is the event's clock. `cpu` counts only your thread's CPU time |
| `--limit-us` | 1000 | The decision limit in microseconds |
| `--trace FILE` | off | Write hand logs with everyone's hole cards. The stacks shown are after the hand |
| `--trace-tables` | 3 | How many tables to trace. With `--workers` above 1, only those played by the main process are written |

The output has one row for each of the 8 seats. "Seat" here means a place in your list of 8 bots, not a physical seat. A second block totals the rows for any bot that appears more than once.

| Column | Meaning |
|---|---|
| `points`, `+/-95%` | Mean points per table and its 95% confidence half-width |
| `1st%`, `top3%`, `last%` | How often it finished there |
| `decisions` | Calls to `decide` |
| `timeouts` | Answers discarded for being late |
| `errors` | Exceptions and invalid answers |
| `setup` | Tables lost to a failed `sit_down`, or tables where the bot failed to load |
| `auto` | Decisions made by the autopilot |
| `mean_us`, `p99_us`, `max_us` | Time spent in `decide`. `p99_us` is rounded up to the next 10 us |

The simulator also prints average hands per table, how many tables reached the cap, and how many eliminations there were. If a bot fails to load, a `WARNING` line says why.

The local simulator runs all bots in one process and does not block the network or the file system. The event's sandbox does both.

To print the structure, or to use the ICM calculator:

```
python3 -m engine.structure
python3 -m engine.icm 5000 3000 2000 1500
python3 -m engine.icm --payouts 50,30,20 500 300 200
```

`engine/icm.py` is plain Malmuth-Harville ICM on the stacks you give it. It knows nothing about stops. With 8 stacks, a call takes about 0.4 ms, a large share of your decision time.

## 9. What is in the kit

| Path | What it is |
|---|---|
| `agent_template.py` | A minimal legal bot. Copy it to `bot.py` |
| `engine/table.py` | The dealer and the table engine |
| `engine/sim.py` | The simulator |
| `engine/loader.py` | The submission checks and bot loading |
| `engine/hand_eval.py` | The hand evaluator. You may copy it |
| `engine/icm.py` | The ICM calculator. You may copy it |
| `engine/structure.py` | Blinds, points, the stop and the limits, as constants |
| `engine/PAYOUTS.md` | The points note |
| `bots/random_legal.py` | Random legal actions |
| `bots/station.py` | Checks and calls everything |
| `bots/tight.py` | A tight hold'em bot that ignores the stop |
| `bots/deskhand.py` | A bot that plays around the stop reasonably well |
| `tests/` and `TESTS.md` | How the engine was checked |

Good luck.
