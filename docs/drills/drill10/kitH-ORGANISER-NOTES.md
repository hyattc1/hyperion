# Organiser notes (not for teams)

Hand teams everything except this file and `organiser/` (the analysis script, its outputs, and
the logs of the soak runs quoted in TESTS.md).

## The event in one paragraph

Solo Hold'em: no-limit hold'em where your showdown hand is exactly one hole card plus exactly four
board cards. Points 13/8/5/3/2/1/0/-2. Bots are separate processes speaking JSON lines; players
are session-stable handles, cards are integers 0-51, raises are raise-by strings (`"r60"`), legal
actions are implied by `to_call`/`min_r`/`max_r`, history is a compact string log, and one
process plays a whole session of tables with an explicit `table` call and a 50 ms setup budget.

## Why this twist

It looks like a footnote and it overturns preflop. A team that ports a hold'em bot plays
backwards; a team that spends ten minutes computing equities finds a different game.

Numbers from `organiser/solo_analysis.py` (2,000 to 8,000 random boards per line; tables in
`organiser/solo_table.txt`, `solo_matchups.txt`, `solo_showdown.txt`):

| all-in, heads-up | hold'em | Solo |
|---|---|---|
| AA v KQo | 86% | 59% |
| AA v 72o | 88% | 56% |
| AA v KK | 83% | 82% |
| AKo v 22 | 48% | 87% |
| TT v A2o | 71% | 18% |
| 72o v 66 | 28% | 83% |
| KQs v K7o | 75% | 51% |
| 98s v A2o | 47% | 37% |

Starting-hand ranks by equity against a random hand (of 169 classes):

| hand | hold'em rank | Solo rank | Solo equity |
|---|---|---|---|
| AKo | 12 | 1 | 68.4% |
| A9o | 22 | 2 | 68.4% |
| A8o | 42 | 10 | 65.9% |
| AA | 1 | 55 | 56.7% |
| KK | 2 | 84 | 50.2% |
| QQ | 4 | 109 | 45.6% |
| TT | 5 | 149 | 34.8% |
| 88 | 7 | 163 | 27.9% |
| 72o | 165 | 137 | 38.5% |
| 22 | 77 | 169 (last) | 12.0% |

The ideas a strong team should find:

1. **A pocket pair is one card.** You can only play one of them, so a pair is a single card with
   no second chance to pair the board. Pairs average 30% against a random hand; 22-99 are eight
   of the nine worst starting hands (JJ is 133rd). AA still blocks the other aces and dominates any lone ace, which
   is why it beats KK as before but loses most of its edge against two different cards.
2. **Two different cards are two lottery tickets.** Your hand is your better card with the
   board, so what matters is the chance that either card pairs the board, plus high-card value
   when nobody does. Big unpaired cards are best; any ace is good (A2o is 35th, ahead of KK).
3. **Suited is worth nothing, connected little.** A flush needs four board cards of your suit, so
   two suited cards cover one suit where two offsuit cards cover two. Across all 78 pairs of
   ranks, suited averages 0.6 points of equity *worse* than offsuit (hold'em: 2.6 points better).
   KQs < KQo, JTs < JTo, 76s < 76o. Straights need four board cards in a window plus one of yours.
4. **The board is shared far more.** Everyone uses four of the same five cards. A paired board
   gives every live player that pair; two pair needs a board pair plus a paired hole card; kickers
   mostly come from the board, so ties are common (6.6% of heads-up showdowns split against 4.2% in
   hold'em; AKs against AKo ties 97% of the time). Heads-up the winning hand is a pair 49% of the
   time (hold'em 37%), flushes and full houses are half as frequent.
5. **Postflop equity is cheap if you see the trick.** Any hand's Solo value is the better of its
   two cards' single-card values. Score each unseen card once on this board (13 ranks, plus the
   suit cards when four of a suit are on board) and the probability that a random opponent's two
   cards both score below yours is about q^2 per opponent. That fits in well under 1 ms in Python;
   enumerating opponent hands does not. `bots/solo_aware.py` does exactly this.
6. **All-in charts and ICM need Solo equities.** Push/fold and calling ranges from hold'em are
   wrong both ways: shoving 55 or calling a shove with TT is a disaster; shoving A2o is fine.
   With 13/8/5 at the top and -2 for the first out, ICM pressure is real at every bubble.

What a naive bot gets wrong, in order of cost: it reads its hand with a seven-card evaluator (an
"overpair" on a dry board is ace or king high; "top two pair" with K9 on K-9-x-x-x is just a pair
of kings), it raises and calls all-ins with pocket pairs, it values suited connectors and flush
draws with two suited cards, and it assumes the board can play for it.

Measured with the sample bots (400 tables, 8 seats, two copies each; TESTS.md section 8): the
Solo-aware bot scores 8.6 and 9.5 points per table, the unadapted hold'em bot 4.6 and 4.8, random
1.3-1.4, the calling station about 0. A careful team should beat `solo_aware.py`: it uses a
heads-up equity table for every position, ignores opponents' tendencies, ICM, and stack depth
beyond a 12-big-blind shove rule.

## What teams must not miss (say it at minute 0)

* The rule is "exactly one hole card and exactly four board cards". Repeat the AA-loses-to-72
  example out loud.
* Raises are **raise-by**, not raise-to. `"r60"` facing a 40 bet puts in 100.
* Every message needs a reply that echoes `id`, on stdout, one line, flushed. Logging goes to
  stderr. The template does all this; teams that write their own loop break it most often.
* One message in flight: a stalled bot is auto-played for the whole stall, not just one
  decision. Python GC pauses are the usual cause (`gc.freeze()` after setup helps).
* `bot.py` at the zip root, standard library only, 5 MB.
* The local simulator's timeouts depend on the laptop; the machine-floor line says how much.

## Interface choices, and why

| choice | instead of | why |
|---|---|---|
| bot is its own process, JSON lines on stdin/stdout, timed by the engine | in-process `Agent.act()` | real isolation, any import cost paid once, timing the engine can enforce; a crash cannot take the table down |
| one process per session, explicit `table` message with a 50 ms setup budget, `hello` with 2 s | a fresh agent per table | lets bots learn opponents across tables and precompute once; the budgets are timed like everything else |
| players are session-stable handles | seats 0-7 | identity for opponent modelling; seats change every table; position comes from list order |
| cards are ints 0-51 (`rank = c >> 2`, `suit = c & 3`) | `"Ah"` strings | fast arithmetic in a 1 ms budget; no parsing |
| actions are strings `f` / `c` / `r<N>`, raise **by** N, clamped | action objects, raise-to totals | minimal JSON; raise-by makes "pot-sized raise" one expression; clamping means a sizing bug costs value, not the hand |
| legal actions implied by `to_call`, `min_r`, `max_r` | a listed set of legal actions | three integers say it all; no list to build every decision |
| compact action log string | a list of event objects | history in one short field, cheap to send and parse |
| callbacks for `end` and `over` | none | showdown cards and results for learning, each with its own 1 ms limit |

## Running the real event

* Run each table's engine and its eight bots on dedicated cores, with nothing else scheduled
  there. The rule is wall-clock on the engine side; it is only fair on a quiet machine. On the
  shared development box a do-nothing bot missed 1 ms on 0.3-1.7% of round trips, which the
  busy rule turns into 2-12% auto-played decisions (TESTS.md section 8). Before the event, run
  `python3 engine/sim.py --calibrate` on the event hardware: it should report 0 misses in 3,000.
* Sessions: one process per bot per session; tables in a session run one after another. Seat
  tables randomly from the field. The per-table standard deviation of points is 3-4, so a team
  needs about 6,000 tables for a 95% interval of ±0.1 points.
* The engine's own work is tens of microseconds per message; a table of 8 Python bots took
  0.28 s on the busy development box, so a quiet core plays over 10,000 tables an hour.
* The local simulator caps memory with `RLIMIT_AS` but does not block the network or the file
  system; the event sandbox must (no network, read-only except the bot's directory, 1 core).
* Restarts: a crashed bot is relaunched before its next table, up to 3 times a session.
* Disputes to expect: "my r60 put in 100 chips" (raise-by, as documented); "I folded and it
  checked" (no free folds); "my bot timed out once and lost 20 decisions" (the busy rule; the
  README warns about it); split pots with odd chips (left of the button).

## Known limits of the kit

* No real sandbox locally (see above).
* `solo_aware.py`'s preflop table is heads-up equity against a random hand; it is a baseline,
  not a solution.
* ICM ignores the 200-hand cap. Near hand 200, chip count decides places directly.
