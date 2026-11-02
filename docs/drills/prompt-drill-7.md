# Prompt drill 7: Track A on kit E (event-driven, no state snapshot), hidden variant river_of_blood

Date 2026-11-01, T0 21:25:46 EST, agent stopped 21:48:44 (minute 23). The climb's first rehearsal
(docs/drills/goal-plan.md, item H1).

**Set-up.**
- Kit E was built by a fresh agent with no repo access, as an organiser would ship it: an event-driven `Player`
  (take_seat, start_hand, see_cards, see_action, see_showdown, end_hand, choose) with no state snapshot; string
  cards; raise-to amounts; payouts 50/25/15/10/0/0/0/0; antes from level 4; a 1 s setup budget per table (fresh
  module per table); 1 ms for choose and for every event method; zip at most 10 MB. River of Blood in the dealer
  (red rivers deal more streets with betting until a black card). Handout: `docs/drills/drill7/kitE-README.md`.
- The variant came from the held-out set (a fresh writer's five, `docs/drills/goal-log.md` 20:42). The agent's repo
  copy was pinned at c1c18c7, before the held-out catalog was merged, so nothing in it knew the variant.
- The agent role was a fresh subagent (Opus 5.5) with the pinned copy, the kit and the prompts. It followed PLAYBOOK
  and prompts 00-05 itself, at most 3 processes, no docs/drills, decisions or HANDOFF. Load 6.5-8 on 8 cores.
- Its NIGHT.md and the files it wrote are in `docs/drills/drill7/`.

## Key numbers

| Checkpoint | Drill 7 | Drill 6 | Target |
|---|---|---|---|
| Rule sheet, axis, FIT VERDICT | minute 3 | 3 | 5 |
| First valid upload (cheap bot, gate PASS) | **minute 8** | 12 | 12 (hard 15) |
| Ship bot gated | minute 18 (PASS), final minute 20 | 29 | 40 |
| Stage 5 | no patch (the sim cannot see the run; the adapter maps run streets to a river view) | reverted | 50 |
| Questions needing a human | 0 | 0 | 0 |
| Stopped | minute 23 | 34 | 60 |

**The final zip in the real variant** (operator, after the drill: main's sim with the held-out river_of_blood
hooks, kit E's payouts and antes, night field, seeds 30000-30059, measure mode, the agent's own gate seat):
package **26.70 ± 5.45** points of 100 a table, composite F straight from the sim **23.30 ± 5.67**; paired
**+3.40 ± 6.49** (inside noise), 0 exceptions, 0 illegal, 1 timeout in 10,431 calls, import 0.27 s. The agent's
river view (a run street shown as a river: the best 5-card sub-board) beats raw F, which checks or folds every
decision on a board of 7+ cards.

## What slowed it down or broke (minutes lost first)

1. **Gate seat, about 5 minutes and two wasted packages.** The gate's hand end carries only our chip change; the first
   seat deferred the bot's hand end into the next timed `choose` (gate FAIL, 2.1% timeouts); the second skipped it
   (wrong stacks). Fixed by running the held hand end outside the timed call.
2. **Setup budget, about 3 minutes.** Hero's table start builds the 8-card evaluator table: 0.62 s of the kit's 1 s
   setup budget, per table (fresh module per table). The agent monkeypatched the entry to stop at 7 cards.
3. **History, about 1 minute.** The first run-street version dropped the earlier streets' log.
4. **Hand-end cost under a timed callback.** Kit E times `end_hand` too (1 ms, interrupted at 1.05 ms). Our hand end
   is p50 157 us, p99 658 us; 0.14% over 1 ms at load 6.5 (8-11 of 12-15 timeouts per seat in the kit sim). An
   interrupted hand end can leave the bot's state half-updated.

## Fixes that follow (backlog, track H and R)

- **H3** Event-driven kits: an adapter template that rebuilds the snapshot from events (drill 7's `player.py`
  generalised), and a gate-seat template that runs the hand end outside the timed call. Prompt 02/04 notes.
- **R5** Hand end: make the bot's hand end cheap (p99 well under 1 ms at load) and safe to interrupt.
- **R6** Setup: build evaluator tables only for the card counts the Rules imply (hole + largest board), lazily;
  measure import + setup cold in a fresh process per table against a 1 s budget.
- **V3** Boards longer than 5 cards: a generic river view in Hero's shell (river_of_blood is promoted to the main
  catalog after this drill).
- **Prompt 01**: the rule sheet asks for the setup budget per table, whether event callbacks are timed, and the zip
  cap (10 MB here, not 100).
