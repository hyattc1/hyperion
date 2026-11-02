# The climb: plan and frozen protocol (2026-11-01, written before any bot code changes)

The brief is `docs/prompts/goal.md`. Our regional is Pittsburgh, Nov 12 (6:00 PM ET). The climb stops at the
latest on **Nov 11, 18:00 ET**, or earlier when the stop rule fires. Base at the start: the composite F
(`SHIP = "composite"`, `DIALS = {}`, commit 49c3f82), fallbacks hybrid3_x and Hero.

## 1. The night score, broken into parts

| part | what it is | how we measure it | where it can fail on the night |
|---|---|---|---|
| A. Strength | points against the real room on plain hold'em | paired 400 x 8 runs on held-out seeds: `night` (primary), `night_hard`, `realistic`, `top`; the judges and the outside field once per batch | opponents we never imagined; a payout table unlike ours |
| B. Variant strength | points under tonight's twist | `tools/variant_matrix.py`-style runs over the 23 catalogued entries, paired against the previous ship; variant-aware opponents where we have them; the 5 unseen variants | the generic patch is wrong for an unseen twist; a Hero-table variant plays weaker |
| C. Adapting in the hour | how good the gated upload is at minute 50, and when the first valid upload lands | full rehearsals: a fresh agent, a new fake kit with an unseen variant and an unfamiliar interface, 60 minutes; score the final zip on the held-out field; minutes to the first valid upload | the adapter takes too long; a tool or prompt breaks on an unfamiliar kit; the agent ships a bug |
| D. Robustness | the upload runs as built whatever the kit does | `tools/gate.py` on kits A-D and new kits; partial and missing logs (`--kit-log`); raise-to vs increment; one instance per table vs per tournament (10,000 tables in one object); memory; import time | state leaks over 10,000 tables; a kit shape we never saw; import over budget |
| E. Never time out or crash | zero auto-folds | strict-mode runs on a quiet host; `tools/latency.py` p50 / p99 / max; strict runs on a deliberately slowed machine (CPU contention, pinned cores) | the organisers' sandbox is 2-3x slower than this box: today's max 629 us becomes a timeout |
| F. The windows | the five 20-minute windows after T1 (T5 + T6 are 52% of the score) | prompt 06 rehearsed on recorded standings; each recipe moves play the stated way and costs nothing beyond noise | a recipe hurts; a window ships an unverified change |

Parts C, D and E are where a failure costs whole points a table (a crash or a timeout is a fold, a broken upload
is the cheap bot). Parts A and B are where the climb buys tenths. The backlog is ordered with that in mind.

## 2. The frozen protocol

Changing anything in this section needs a `docs/decisions.md` entry saying why.

**Mode and pairing.** Model mode (fixed speed), `--rotate` (8 rotations), every candidate paired against the
current ship on the same deals with `tools/swap.py paired` (the first spec is the reference). The sample unit is one
table seed (its rotations averaged). The interval is the 95% interval of the per-seed paired difference.
- *Beyond noise up*: the lower bound is above 0. *Beyond noise down*: the upper bound is below 0.

**Seeds.** Seeds used before this climb (0-199, 1000-1399, 4000-4199, 5000-5399, 6000-6399, 7000-7399) are not
used for decisions.
- *Screen seeds:* 10000-10199 (200 x 8). Screens may be reused; they decide nothing on their own.
- *Held-out sets* of 400 seeds: H1 = 20000-20399, H2 = 21000-21399, H3 = 22000-22399, and so on (+1000 each).
  A set is retired after it has confirmed three accepted changes, and the next set is drawn. `docs/drills/goal-log.md`
  records which set is live.
- *Judge seeds:* 30000-30399, fixed for the judges, the outside field and the unseen variants, used only for the
  once-per-batch measurement.

**Fields.**
- *Primary:* `night`.
- *Guards:* `night_hard`, `realistic`, `top`, and `night` under two other payout tables (`--payouts brief`,
  10/7/5/4/3/2/1/0, and `--payouts th`, 50/25/12/6/3/2/1/1).
- *Judges (never tuned on, measured once per accepted batch):* `judge`, `judge2`, `judge2_night`, `judge_top`, and
  the outside field built in this climb (fresh agents' bots, no repo access).

**Acceptance rule.** A change is accepted only if every line holds:
1. Screen: night on the screen seeds, point estimate above 0 (a cheap filter, not evidence).
2. Confirm: night on the live held-out set, beyond noise up.
3. Guards on the same held-out set: no guard beyond noise down.
4. Variants: none of the 23 catalogued entries beyond noise down against the previous ship (200 x 8 each).
5. Timing: `tools/latency.py` p99 at most 200 us at a table and the gate's p99 at most 400 us; strict timeouts no
   higher than the previous ship on the same seeds; max reported.
6. Rehearsal: for a change to the adapter, the prompts, the packet or the tools, the next rehearsal is not worse.

**After every accepted batch:**
- update `SHIP` / `DIALS` (or the defaults);
- pack a frozen known-good zip, record its sha256 and commit in `docs/drills/goal-leaderboard.md`, and keep it in
  `frozen/` (git-ignored) so there is always a safe fallback;
- measure the judges and the outside field once, paired against the previous frozen ship. A judge beyond noise down
  sends the batch back: take its changes out one at a time until the judge is level;
- update the leaderboard: rank, bot, points, margin, in plain words.

**Rounds and the stop rule.** A round tests at least five ideas from at least three tracks. The climb stops when
three rounds in a row accept nothing on fresh held-out seeds. Then it runs one round of structural ideas (a new
composite member, a new solver, a rewritten section), and stops only if that round also fails, or at Nov 11 18:00
ET, whichever comes first. Being first on our leaderboard is never a reason to stop.

**Compute.** This host has 8 cores. At most 6 simulator workers at once across every agent, and none while a strict
timing run is measuring. Builders of outside bots run one process each under `nice`.

## 3. Test sets (built first)

- **Outside field.** Four fresh agents, no repo access, each building a bot in 60 minutes against the red-team
  brief and kit, as four kinds of real team: prepared veterans (ICM and push/fold first), a solo student who lets an
  agent self-play-tune for the hour, aggressive grinders (loose-aggressive, re-shoves), and quants (import-time
  push/fold equilibria, exact ICM). Wired in as frozen copies like the persona bots, in a field `outside`, never in
  any tuning field. One more outside bot every few rounds.
- **Unseen variants.** A fresh agent with only the names of our 23 entries writes 5 variants we have not
  catalogued (handout text plus exact rules). They are implemented as a held-out catalog that no screen uses.
- **The exploiter.** A fresh agent given only the packaged zip, played as a black box through an arena script, builds
  a bot to beat it. Its findings go into the backlog as Strength items.
- **Payout and weight robustness.** The two extra payout tables above. The night pool weights are a guess
  (decisions entry "Night field and skill profile"), so `night_hard` is a guard. Re-weigh the pool on Nov 7 and Nov
  10 if the regionals before ours publish anything about the field.

## 4. Fixed-date items

- **Nov 7 (after Menlo Park, Nov 6) and Nov 10 (after Boston, Nov 9):** re-run the competition research. The kit
  interface, the payout table, the field and possibly the variant may be public. Our variant can differ (and the
  rules ask teams not to share it), but the kit and the payout table are likely the same. Each finding becomes a
  fake kit, a payout guard, or a pool re-weighting, the same day.

## 5. The backlog, ranked by expected gain on the night per hour of work

Tracks: **S** strength, **V** variants, **H** the hour, **R** robustness.

| rank | id | idea | why it is worth the hour |
|---|---|---|---|
| 1 | R1 | Slow-machine timing: strict runs with the host deliberately slowed (contention, pinned cores) and a 2x / 3x budget squeeze; check SafeBot's panic path holds every decision under 1 ms | the sandbox's speed is unknown; a 2x slower box turns our 629 us max into folds |
| 2 | S1 | Payout-table robustness: F under the `brief` and `th` tables against hybrid3_x and Hero; check every member reads `Rules.payouts` (rival 3's core was built for 10/7/5/4/3/2/1/0) | the real table is announced at build start; a top-heavy table changes every all-in |
| 3 | R2 | Instance lifetime: one object for thousands of tables (memory growth, per-table reset, profiler state) | if the kit builds one Agent per tournament, a leak is 10,000 tables deep |
| 4 | H1 | Full rehearsal on a new fake kit with an unseen variant, fresh agent, 60 minutes | the only measure of part C; it has not been run on the composite |
| 5 | S2 | The exploiter's findings | a black-box attacker finds what our own fields cannot |
| 6 | S3 | The weakest section of F by `tools/skill_profile.py` on night and the outside field; fix that section, not dials | the last climb's 54 one-dial trials were noise |
| 7 | S4 | Short-stack push/fold and call-off ranges against ICM at the payout table (`tools/hrc_check.py`) | every table ends in push/fold |
| 8 | S5 | Faster reads of dead, timing-out and maniac seats (about two broken seats a table) | the weak and broken group is 30% of night |
| 9 | V1 | Rank the 23 variants by likelihood; for the top five, go from READY to strong against variant-aware opponents; fix lowball (-0.07) | strength under the variant is half the night |
| 10 | H2 | Composite vs hybrid3_x in the hour: does the composite's complexity cost adaptation time or bugs? | if it costs more than +0.28, ship hybrid3_x |
| 11 | V2 | The generic patch path for the unseen five: time and correctness | an uncatalogued twist is the likeliest case |
| 12 | R3 | Kit shapes: raise-to vs increment, partial logs, blind posts in or out of the history, swapped min/max | each was a drill failure once |
| 13 | S6 | Short-handed and heads-up endgame play | the last three seats decide 1st vs 3rd |
| 14 | S7 | Bust avoidance in the first two levels (a bust penalty in all-in decisions) | rival 5's largest gain was this term |
| 15 | F1 | Rehearse the five windows on recorded standings; check each recipe still moves play on F | 52% of the score is decided in T5 and T6 |
| 16 | R4 | Memory and import time with every table loaded; the 100 MB cap | cheap to check |

The order changes as results come in; every change of order is a line in `docs/drills/goal-log.md`.

## 6. Files

- `docs/drills/goal-log.md`: the running log (every run, its seeds, its numbers).
- `docs/drills/goal-leaderboard.md`: one page, rank, bot, points, margin, in plain words.
- `docs/decisions.md`: one entry per accepted batch, and one for any protocol change.
