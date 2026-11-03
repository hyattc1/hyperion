# Organiser notes (not for teams)

## The twist in two sentences

Tranche Hold'em: each betting round's chips are their own pot (a tranche), and at showdown each
tranche goes to the best hand *as it stood on that street*: two-card hands for the preflop
tranche, hole cards + flop for the flop tranche, and so on to ordinary seven-card hold'em for
the river tranche. Folding forfeits every tranche you paid into, and when the betting is over
no more cards are dealt, so an all-in is settled on the cards that were out when the chips
went in.

## Why this twist

* **It moves an axis the last three events did not.** Those moved the pot (a hidden hand with a
  carried pot), information (cards shared with neighbours) and hand strength (one hole card).
  This one moves **the payoff of a hand**: the cards, the betting structure and the information
  are plain no-limit hold'em; only the rule that turns chips-in into chips-out changes.
* **It is small in the dealer.** The settlement is about forty lines (`Table._settle`): side
  pots are layered per street instead of per hand, and each street is judged with its own
  evaluator (`rank2` for two cards, `best5` for five to seven). Everything else is the ordinary
  engine. The "no more cards once betting is over" rule is a consequence, not extra machinery:
  later tranches are empty, so later cards cannot matter.
* **It is substantial.** It changes the value of nearly every decision, on every street. A
  standard hold'em bot plays it and loses about 2.6 points a table to a bot of similar
  sophistication that knows the rule (measured below).
* **It rewards thinking, not just preparation.** The key quantities (P(best two-card hand
  against a range), P(ahead *now*), the forfeit value of earlier tranches) are all derivable in
  the first ten minutes by a team that reads the rule carefully, and all computable within 1 ms
  if precomputed sensibly.

## What changes, and what a strong team exploits

1. **The preflop tranche is a deterministic two-card contest.** Any pair beats any non-pair;
   suits and connectedness are worth nothing in it. Exact numbers (vs random hands):

   | Hand | beats 1 random | best of 4 | best of 8 |
   |---|---|---|---|
   | AA | 0.999 | 0.999 | 0.997 |
   | JJ | 0.984 | 0.956 | 0.898 |
   | 77 | 0.965 | 0.901 | 0.779 |
   | 22 | 0.940 | 0.829 | 0.648 |
   | AK | 0.934 | 0.822 | 0.641 |
   | A2 | 0.826 | 0.557 | 0.241 |
   | KQ | 0.784 | 0.478 | 0.157 |
   | 87s | 0.229 | 0.009 | 0.000 |

   22 against AK all-in preflop wins 100% (about 50% in hold'em). A2 beats KQ. 87 suited is
   the worst kind of hand to put preflop money in with.
2. **No card luck in an all-in.** Once betting is over, no more cards come. "Equity" is just the
   probability you are ahead *now* given what the opponent might hold. A flop shove with a set
   against a flush draw wins the flop tranche every time. Draws have no all-in value at all.
3. **Every later tranche starts at zero.** A flop bet of B into an empty flop tranche is an
   even-money side bet on the current five-card hand, plus fold pressure. Ordinary pot odds
   ("call 100 to win 400, need 20%") are wrong: the call wins the current tranche (2B), so it
   needs about 50% to be ahead now, minus the forfeit value below.
4. **Forfeit value ("hostage chips").** Folding gives up the earlier tranches too. The right
   call test is roughly `q_s * (T_s + c) - c + sum_{k<s} q_k * T_k > 0`, where `q_k` is the chance
   of winning tranche k and `T_k` its size. A pocket pair that took a big preflop tranche should
   call down light; its opponent's river bluff mostly buys nothing. Conversely, a bot with no
   earlier claim (unpaired high cards that missed) folds cheaply. Big bets on later streets are
   a lever against a player whose earlier claim is small and current hand is weak.
5. **Bet the street you are ahead on; do not slow-play; do not pay to draw.** Money goes into
   the tranche of the street it is bet on and is judged there. A draw is worth something only in
   tranches that do not exist yet and will only exist if someone bets then.
6. **Preflop sizing tells.** With chips locked to two-card strength, preflop raise size leaks
   whether a bot holds a pair. Within a table seats are stable, and `done()` shows every
   showdown hand, so opponent modelling by seat pays.
7. **The 200-hand cap decides most tables.** With this schedule, 61-98% of tables reached
   hand 200 in the sample fields we ran (86-92% in the fields measured below), with two or
   three bots left on average. So the finish is mostly
   *chip rank at hand 200*, not who busts. ICM (which assumes play to the end) overstates the
   value of survival late; near hand 200 chips map almost directly onto places. A team that
   notices this plays big pots differently from hand ~150 on. (A field of strong bots may bust
   more often; check this on the real field after the event.)
8. **Points 16/10/6/3/1/0/-1/-3.** Steep at the top, a small penalty for 7th and 8th. With few
   busts and the cap, 1st and 2nd are where the points are: chip accumulation beats survival.
9. **1 ms in Python.** A five-card evaluation costs about 4 µs here, so a bot gets about 100 per
   decision with room to spare. Teams that precompute
   two-card tables in `start()` and sample postflop under a `perf_counter` budget win; teams
   that run Monte Carlo naively time out and fold.

## What a naive bot gets wrong

* Hold'em preflop charts: plays suited connectors and calls shoves with AK/AQs. Under the
  twist AK loses the preflop tranche to every pair.
* Thinks an all-in has run-out equity (it has none: no more cards).
* Uses whole-pot odds instead of per-tranche odds; calls flop and turn bets with draws.
* Folds a strong earlier claim on the river.
* Slow-plays monsters (the flop money is judged on the flop).
* Interface slips: returns a raise-to total instead of chips to add (returning `3 * bb` from the
  big blind puts in 60 *more*, not "raise to 60"); treats seat 0 as a fixed physical seat or as
  the button; parses cards as strings; uses a bare `except:` (swallows `Overtime`); imports a
  helper inside `act()` (not on `sys.path` after import).

## Measured with the sample bots

All runs on the shared build machine (8 cores, load average about 16 from other jobs), with
`nice -n 5` and two workers.

| Field | Tables | Clock | Result (points per table, 95% CI) |
|---|---|---|---|
| tranche_bot, tight, station, random (x2 each) | 300 | wall | tranche +10.38 ±0.38, tight +6.73 ±0.38, random -0.15 ±0.14, station -0.96 ±0.13 |
| tranche_bot x4 vs tight x4 | 300 | cpu | tranche +5.31 ±0.37, tight +2.69 ±0.29 |
| tranche x2, tight x2, random x2, station, template | 400 | wall | tranche +8.98 ±0.39, tight +6.67 ±0.36, template +4.30 ±0.39, random -1.01 ±0.09, station -1.58 ±0.13 |
| pair-shover x2, tranche x2, tight x2, station x2 | 200 | cpu | tranche +9.10 ±0.60, tight about +4.9, pair-shover +3.90 ±0.40, station about -1.9 |

`tight.py` is a reasonable hold'em TAG; `tranche_bot.py` is not more sophisticated, it just uses
the rule (two-card ranking preflop, current-street strength postflop, forfeit value on calls).
The 2.6-point gap in the 4v4 is the value of reading the rule. The pair-shover ("shove every
pair, fold everything else") probe scores about average: the twist does not collapse into a
trivial strategy.

## Running the event: things not to miss

* **Timing must run on idle cores.** On the loaded build machine, wall-clock timeouts were
  about 0.8% of decisions for a bot averaging 90 µs, and even a bot averaging 3 µs logged some.
  They cluster at about 4.0 ms (a 250 Hz scheduler tick: the process was descheduled mid-call).
  With `--clock cpu` the rate fell to about 0.12%; the rest is presumably the host preempting
  the VM (CPU time measured inside a VM still counts it). For
  the event: one table per core, workers at most cores minus one, nothing else running. If the
  hardware must be shared, announce `--clock cpu` before the build starts, not after.
* **Sandboxing.** The local simulator runs every bot in one process. For the event, run each bot
  in its own sandboxed process and call `engine.seat.timed_call` *inside* that process, so the
  measured time is the bot's call only, exactly as documented. The dealer protocol
  (`on_table`, `on_act`, `on_done`) is what crosses the process boundary.
* **Draw tables** with eight different teams, balanced so every team plays the same number of
  tables; break score ties on first places (as announced).
* **Simplifications we announced** (README 2.1/2.3): moving button rather than dead button;
  short all-ins never reopen betting, even cumulatively; no burn cards. Do not change them
  mid-event.
* **Questions to expect**, and the answers the handout gives: suits never count in the preflop
  tranche; the flop tranche uses exactly five cards; an all-in bot has no stake in later
  tranches; folded bots' chips stay in their tranche as dead money; if everyone is all-in on the
  turn, the river is never dealt; `to_call` is capped at your stack.
* **If a dealer bug is reported** during the build, fix it, rerun `python3 -m unittest discover
  -s tests`, and push the fix to every team at once.
