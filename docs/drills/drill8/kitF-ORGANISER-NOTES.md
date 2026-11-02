# Organiser notes (do NOT ship to teams)

`organiser/build_handout.py` builds the team zip without this file or `organiser/`.

## The twist in one line

Every hand has a ninth, silent hand, **the Ghost**. A pot that goes to showdown is only paid out
if the best hand in it beats or ties the Ghost. Otherwise it **haunts**: it becomes dead money in
the next hand's main pot, and whoever wins that pot takes it, by showdown or by fold.

Why it suits a quant event: the rule is one sentence, and the dealer needs about 20 lines for it.
But it changes the value of every showdown, adds a conditional-probability problem (beat the
field *and* a random hand), and creates a recurring dead-money spot that rewards anyone who
reads `s.haunt`. None of the excluded twists touch the showdown payout itself.

## Numbers (from `organiser/ghost_stats.py`, 400k river samples; and the simulator)

P(the Ghost beats your 7-card hand), by your hand's category on the river:

| your hand | Ghost beats it | share of hands |
|---|---:|---:|
| high card | 81.6% | 17.5% |
| one pair | **56.3%** | 43.9% |
| two pair | **30.5%** | 23.4% |
| trips | 23.9% | 4.8% |
| straight | 6.9% | 4.6% |
| flush | 11.3% | 3.0% |
| full house | 6.1% | 2.6% |
| quads | 4.2% | 0.2% |

Random hands at showdown haunt 31.9% of the time heads-up, 23.5% three-way and 18.7% four-way.
In simulated play with the sample bots, 23-30% of showdowns haunt, and the average haunted pot
is 600-2,400 chips depending on the field.

Preflop heads-up equity against a random hand, plain hold'em versus Ghost Hold'em (a haunted pot
counts 0): AA 85.1 -> 73.8, 22 drops 23 places in the ranking, 33 drops 19, 44 drops 15. Suited
connectors rise: 87s +22, 98s +21, 65s +21, 76s +19. Small pairs make one pair, and the Ghost
beats one pair more often than not. Connected, suited cards make the straights and flushes that
clear the Ghost.

## What makes it strategically interesting

1. **Showdown is taxed; fold equity is not.** A pot you take uncontested is never haunted. Every
   bet that makes everyone fold dodges the Ghost. Thin value bets lose value, because a one-pair
   hand that gets called is behind the Ghost 56% of the time. Bluffs and semi-bluffs gain value.
2. **The Haunt hand.** After a haunt, the next hand starts with dead money, often several big
   blinds and sometimes more than a stack. The right response is to open, steal and defend
   much wider, and to size up. Tight bots fold these pots away to whoever is aggressive. This is
   the single biggest, most visible edge, and `s.haunt` hands it to every team on a plate.
3. **A haunted pot is not a total loss.** The chips go to the next hand's winner, so roughly
   1/(players left) of a haunted pot comes back to you on average, more if you win Haunt hands
   more than your share. Correct showdown EV is
   `P(win) * pot + P(haunt) * pot * share - cost`.
4. **Multiway pots haunt less.** The best of three hands beats a random hand more often than the
   best of two. That nudges you toward multiway pots with drawing hands and away from
   heads-up pots with one pair.
5. **ICM interaction.** In an all-in, a haunt eliminates the short stack without enriching the
   big stack, and survivors move up a place for free. When you are covered, calling is
   worse than plain-poker ICM says, because even winning against your opponent can still lose to
   the Ghost. Laddering is real: 2nd to 3rd is 3 points, and 6th to 7th is 1.
6. **The end of the table.** A Haunt still on the table after hand 200 is discarded. Late in a
   table, a leader can protect a lead by avoiding showdowns, and a trailer has less reason to
   pass on a Haunt hand.
7. **Opponent modelling across tables.** `t.ids` stays the same for the whole session, so fold
   rates and showdown ranges can be learned. The sample `ghostwise` bot does this.

## What a naive bot gets wrong

- It uses plain hold'em equity, so it calls down and value-bets with one pair as if it were
  ahead. In the sample runs, `tight` and `ghostwise` lose most of their showdown chips with
  one pair and two pair.
- It ignores `s.haunt`. It folds marginal hands into a pot that already holds 20+ big blinds of
  dead money.
- It never bluffs, so it never collects the showdown-free pots that the Ghost cannot touch.
- It treats preflop all-ins as plain coin flips. With AA versus a random hand, about 11% of the
  pot goes to the Ghost.
- Interface traps: returning a raise-to total (it is chips put in now), returning 0 to call (0
  folds when owing), treating seat 0 as the first seat (it is *you*), parsing cards as
  strings.

## Things a team must not miss (we will see these in the logs)

- `return 0` folds when you owe chips. The timeout default is check-or-fold, so a slow bot
  folds a lot.
- `s.min_raise == 0` means you cannot raise. Any amount at or above the call is then a call.
- The Ghost only plays when a pot has 2+ eligible players at showdown. A pot with one eligible
  player (for example, uncalled chips in a side pot) is paid without it.
- `hand_over` has a 1 ms budget too. Going over costs the next decision.
- `new_table` going over 50 ms costs the whole table. Precompute in `__init__`, which has 2 s.

## Sample bots: what they show (400-table runs, one process, see TESTS.md)

| bot | mixed field, shuffled seats | mixed field, duplicate | 4 ghostwise v 4 tight |
|---|---:|---:|---:|
| ghostwise | 9.54 | 9.91 | 6.07 |
| tight | 9.15 | 8.87 | 5.93 |
| random_bot | 3.41 | 3.41 | - |
| station | 1.91 | 1.81 | - |

(The mixed field is 2 of each bot, mean of both slots. 6.0 is average.) `ghostwise` beats the
mixed field mostly through Haunt-hand aggression and stabbing at small pots. Against a field of
only `tight` bots it is roughly even: it wins far more tables, but it also busts early more
often. Strong teams should beat both clearly, and the headroom is real: better ranges, using
ICM at 6-8 players, and Haunt-hand sizing.

## Operational notes

- **Timing noise.** The local simulator measures wall-clock time in-process. On a heavily loaded
  machine (the test machine had load average 11-13 on 8 cores from unrelated jobs), even a
  10-microsecond bot sees a few timeouts per 50,000 decisions. Tournament hosts must give each
  bot process a dedicated, quiet core. Consider re-running any table where a bot's timeout rate
  jumps above its own baseline.
- **Hang guard.** Locally a SIGALRM interrupts any call after 1 s. CPython 3.10 cannot interrupt
  a loop whose body is only a `try:` around plain arithmetic, so the official harness must also
  kill a bot process on a hard wall-clock timeout.
- **Determinism.** The deck for hand *h* depends only on (table seed, *h*), which is what makes
  `--duplicate` work. Bots that use `random` without a seed make reruns differ; that is
  expected.
- **Haunt discard volume.** About 1,300 chips per table are discarded at table end in the sample
  fields, mostly at the hand-200 limit, where the last few haunted pots are large. That is
  intended and it is announced, but expect questions about it.
