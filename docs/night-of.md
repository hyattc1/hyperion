# Night of: operational checklist

Plain language, in order. The bot that wins is the one that never crashes, never times out, and is
submitted every window. Everything below serves that.

## Before 6 PM (setup, done at home)

- Laptop: plugged in, power mode "performance", sleep and screen lock off, notifications off, Wi-Fi
  hotspot on the phone as backup. Close everything but the terminal, the editor and one browser tab.
- Repo: `git pull`, `.venv/bin/python -m pytest -q` green, `git status` clean. Note the commit hash.
- Tables warmed: `ls -la tables/` shows today's `meta.json`; `python tools/gen_tables.py --rules default
  --variant-check` reports under 3 minutes projected. If the laptop has 4 cores, note the number.
- Drills passed: at least one full `python -m hyperion.drills.run --variant random --kit random` this week
  with all four checkpoints on time, and `drills/log/` has the JSON to prove it. Read the last log.
- Hero known-good: `python -m hyperion.sim` (or the runner's strict mode) vs the bestiary, result written
  down: mean points, CI, max decision latency. This is the number to beat tonight.
- A timer app on the phone with alarms at T+12, T+28, T+40, T+55 (the "stop improving, submit" alarms).
- Paper: this checklist printed, the kit rubrics (`hyperion/drills/fakekits/*/RUBRIC.md`) as a reminder
  of the gotcha classes, and the email answer from the organizers if we got one (see bottom).

## T+0 to T+15: read, diff, adapt, submit the cheap bot

1. Read the rules sheet once, slowly. Write the variant into `variant.json` as Rules fields before writing
   any code: `hole_cards`, `board_sizes`, `rank_order`, blinds, hands per level, payouts, and anything odd
   into `extras`. If it matches a preset in `hyperion/drills/variants.py`, start from that file's checklist.
2. Diff the kit against our assumptions, in this order, because each one has sunk a drill: card encoding
   (is ten `T` or `10`? suits upper or lower? dicts? ints?), street encoding (index or board count?),
   whether pot includes the current street's bets, whether raise amounts are totals or increments,
   legal-action names and case, how the kit says "check", what seat numbering is, where the blinds are,
   and whether the kit calls a per-table init we can use for warm-up. Mark each on the rubric table.
3. Write `Adapter` subclass (copy the closest of `KitAAdapter`, `KitBAdapter`, `KitCAdapter`), wrap it in
   whatever class or function the kit wants. Behind it put `CheapBot` first, not hero.
4. Run the kit's own local simulator with the cheap bot. No exceptions, no illegal actions, no timeouts.
   If the kit prints decision times, note the max. If it does not, time 1000 `act` calls ourselves.
5. Submit at T+12 at the latest. A legal, boring bot on the board is worth more than anything else you
   can do in the next three minutes. Note the submission time and the file hash.

## T+15 to T+40: tables, hero, sim

6. Does the variant change any table? Permuted ranks, short deck, a different hole-card count or board:
   yes, run `python tools/gen_tables.py --rules variant.json --out tables/` now in a second terminal and
   keep working. Swap, bounty, pot-limit, two boards: no regeneration, go to step 8.
7. While tables build, update the parts of hero the variant's checklist names (discard choice, bounty
   bonus, pot-limit clamp, second board in `obs.extras`). Do not touch anything the checklist does not name.
8. Swap `CheapBot` for `make_bot()` behind the adapter. Run the kit simulator again: same three zeros.
9. Run our sim vs the bestiary in strict mode (the mode that auto-folds at 1 ms and counts it) with the
   variant's Rules and, if the variant has hooks, the `Variant.hooks` object. Compare with the number from
   home. If it is within the CI, fine. If hero is worse than the cheap bot, submit the cheap bot and debug
   with the remaining time, not the other way around.
10. Latency: max decision time under the strict run must be under 0.5 ms on this laptop. If not, cut
    whatever is slow (usually a table lookup that became a loop); do not optimize, remove.

## T+40 to T+60: dials, latency, submit

11. Tune only dials that exist: open-range width, shove threshold, call-down threshold, bluff frequency.
    One change, one sim run, keep or revert. Stop at T+55 whatever the state.
12. Final latency check on the submission file itself (not the dev copy): 2000 random decisions, p99 and
    max. Submit at T+55. Freeze: `cp submission.py frozen/T1.py`, write the hash down.
13. T+55 to T+60: nothing clever. Re-read the submission rules once more: file size under 100 MB, no
    network, no reading from disk at decision time if the kit forbids it, the entry point named exactly
    as the kit wants.

## The five 20-minute windows after T1 (T2..T6)

Each window is the same loop. Tournaments are weighted 1..6, so the last one matters six times the first:
be conservative early, and never let a late submission be the first run of new code.

- Minute 0-5: look at the standings. Our rank, our mean points, and the spread. Then look at *why*: if the
  kit shows hand histories or per-table results, sample ten tables we finished last in. Timeouts or
  crashes are the only thing that justify a hurried change. Early busts with marginal hands: tighten the
  shove range one notch. Blinding out: loosen it one notch. Being outlasted by stations: value-bet thinner.
- Minute 5-15: one change, run the strict sim, compare with the previous number. Keep if better and not
  slower; revert otherwise. Change at most two dials per window.
- Minute 15-18: freeze the known-good bot before the next tournament: `cp submission.py frozen/T<n>.py`.
  Then submit. One submission per 5 minutes is the rule we hold ourselves to; the last one before the
  tournament starts is the one that plays, so make it the frozen one when in doubt.
- Minute 18-20: write three lines in the log: what changed, what the sim said, what the standings said.
- If anything crashes in a window: resubmit the previous frozen file first, then investigate.
- Finals use a different variant: the whole T+0..T+60 loop repeats. The adapter should not need to
  change; the Rules and the tables do.

## The email to pokerbot@sequoiacap.com (send this week)

Subject: No Limit tournament: four questions about the build environment

1. May teams bring pre-written code and precomputed tables (for example preflop equity tables as JSON)
   into the 60-minute build, provided the bot itself follows the sandbox rules? The rules constrain the
   bot (offline, 1 ms, 100 MB) but say "from scratch" in the announcement; we want to prepare correctly.
2. Which Python version runs the sandbox, and which third-party packages, if any, are importable
   (numpy? none?). We are building stdlib-only and would like to know whether that is required.
3. Is the `Agent` interface a class with a single decision method, and is there a per-table
   initialization call outside the 1 ms budget where a bot may load tables and warm caches? How is the
   1 ms measured (wall clock or CPU, per call, any grace)?
4. What CPU (model, clock, shared or dedicated core) does the sandbox run on, so we can set our own
   margin? Our target is 0.3 ms on a laptop; if the sandbox is much slower we will budget differently.

Whatever the answers, the adapter pattern stands; the answers change the margin and whether tables
ship as files or as literals inside the submission.
