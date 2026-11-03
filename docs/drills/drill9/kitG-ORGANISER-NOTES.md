# Organiser notes (not for teams)

## The twist in one paragraph

Chain Hold'em: each player is dealt one private card, and one link card is
dealt between every two neighbours in the ring; both neighbours hold and see
it. A hand is private + left link + right link + board, best five of eight.
Heads-up both links are shared with the one opponent. Nothing else changes:
no-limit betting (from a pot-fraction menu), standard ranks, split pots.

## Why it is strategically interesting

It changes three things at once, and a bot that ignores any of them leaks.

1. **Hand values.** Three hole cards instead of two. 17.2% of starting hands
   contain a pair (5.9% in hold'em), trips are 0.24%, and the average showdown
   hand is stronger. A hold'em chart applied to "the best two of my three"
   misranks hands: the third card matters, suits and connectivity across three
   cards matter, and a pair is no longer a premium. `bots/make_chain_table.py`
   shows the honest fix (offline equities for the 1,755 three-card classes).

2. **Shared cards and known cards.** You know one card of each neighbour, and
   each neighbour knows one of yours. Consequences a strong team can use:
   - Against a neighbour, the shared card cannot win you the pot. Top pair made
     with a shared ace against that neighbour is a kicker battle or a chop.
     Measured over random 8-handed deals, two neighbours finish with exactly
     the same hand 7.4% of the time, against 2.6% for two non-neighbours.
     Equity has to be computed against *who is in the pot*, not in general.
   - Range reading is sharper. In three-card space one known card moves a range
     a lot: a neighbour who raises while holding your deuce has made the raise
     with his other two cards. Your own raise is equally readable by your
     neighbours.
   - Blockers are certain. The two cards you share are not available to anyone
     else; Monte Carlo that deals neighbours fresh random cards (instead of
     putting your links in their hands) is simply wrong.
   - Position interacts with the ring: the small and big blind always share a
     link (every blind battle is played with one card face-up between them),
     the big blind also sees one card of the first player to act, and the
     button sees one card of the small blind.

3. **Heads-up is nearly open-card.** With two left you see two of the
   opponent's three cards; only the private card is hidden, so river equity
   is an exact sum over about 44 cards and preflop equities are far more
   lopsided than in hold'em (in 18% of random heads-up deals one player is a
   75/25 favourite or better preflop, against 8% in plain hold'em). The bot
   that computes this and value-bets relentlessly wins heads-up; bluffing
   barely works. The points table puts 18 points on 1st versus 2nd, the
   largest gap, so heads-up skill is worth a lot.

## What a naive bot gets wrong

- Plays its three cards as if all three were private (`bots/tight.py` does
  this on purpose) and overvalues hands built on a link shared with the raiser.
- Estimates equity against random hands that ignore the chain structure.
- Plays heads-up like hold'em heads-up: folds hands it knows are ahead, calls
  when it knows it is behind, bluffs a player who can see most of its hand.
- Uses ICM to the end. The table stops at hand 200 and survivors are ranked by
  chips, so in the last few hands chip *rank* is what matters, not ICM (a
  narrow chip lead can be locked up by folding; a player just behind must
  gamble). About 5% of tables in a field of the sample bots reach the cap; a
  field of careful bots will reach it far more often.
- Interface traps: seat numbers are offsets from you (assuming absolute seats
  breaks everything); one Agent instance plays many tables, so per-table state
  must be reset in `begin_table`; `R..` tokens are raise-*by* a fraction of the
  pot after the call, not raise-to; any token that is not exactly one of the
  nine is an error; and 1 ms in pure Python is perhaps 300-700 hand
  evaluations, so anything heavy must be precomputed or shipped as data.

## Anything a team must not miss (repeat these at minute 0)

1. Your links are in your neighbours' hands. Heads-up, both are.
2. Offsets, not seats. 0 is you; `left_nb`/`right_nb` tell you who shares what.
3. Raise tokens: `R33 R50 R75 R100 R150 R250` raise **by** that % of the pot
   after your call; `s.cost(token)` tells you the chips.
4. 1 ms per decision; a late answer is thrown away and you check/fold.
   `hand_over` is timed too: if it is late, your *next* decision is check/fold.
5. The hand-200 cap ranks by chips.

## How the sample bots do (this machine, loaded, nice 5)

| field | result (points per table, 95% CI, pooled over seats) |
|---|---|
| 2x each of random, station, tight, chain; 500 tables | chain 29.4 [28.4, 30.4], tight 23.7 [22.8, 24.6], random 8.5 [7.9, 9.1], station 4.9 [4.5, 5.3] |
| 4x chain, 4x tight; 300 tables | chain 18.9 [17.9, 19.9], tight 14.3 [13.5, 15.2] |

`chain.py` is meant to be "reasonable", not strong: it uses chain-consistent
Monte Carlo, the offline preflop table, a raiser-range weighting and a
shared-link discount, and nothing about the cap or opponent modelling. A good
team should beat it clearly; a team that does not beat `tight.py` has missed
the twist.

## What the kit does not do (the production harness must)

- **Isolation.** The simulator runs all eight bots in one process (each seat
  imports its own copy of its module and helpers). The tournament must run each
  bot in its own sandbox process, one core each, 1 GB, no network, read-only
  files, and kill bots that start threads or subprocesses. Decision time must
  be measured inside the sandbox around the `decide` call, so IPC is not
  charged, with the same garbage-collector policy (`gc.freeze()` after setup,
  automatic collection off during a table, `gc.collect()` between tables).
- **Load.** Timing on a loaded machine is noisy: here a fixed 0.3 ms busy loop
  overran 1 ms in 0.23% of 40,000 trials (max 10 ms) because of preemption.
  Run the tournament on idle, pinned cores, or every bot collects random
  check/folds.
- **Budget planning.** About 600 decisions per table. Eight bots that each use
  their full 1 ms make a table cost up to 0.6 s of bot time; 10,000 tables is
  under two hours of one core, so a few dozen cores finish an event in minutes.
- **Simplifications to announce if asked** (all in the README): no dead button
  (the button simply moves to the next player with chips), no burn cards, a
  short big blind still makes the call amount the full big blind (unmatched
  chips are returned), and several short all-ins add up to reopen the betting.

## Running it

```
python -m engine.sim bots/random_bot.py bots/station.py bots/tight.py bots/chain.py -t 500 --jobs 2
python -m engine.sim team.zip --fill bots/chain.py -t 1000 --jobs 4
python -m unittest discover -s tests -t .
```
