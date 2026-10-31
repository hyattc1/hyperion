# CHALLENGE: what this tournament is, in one page

Read alongside the organizers' handout. Where the handout disagrees with this page, the handout
wins; write the difference into the rule sheet.

## The event

Sequoia Capital's "No Limit: A Bot Building Tournament," hosted with OpenAI and Citadel Securities.
Regionals: Menlo Park Nov 6, Cambridge MA Nov 9, Pittsburgh Nov 12, 6:00 to 9:00 PM local. Finals:
San Francisco Nov 15, a different variant. Top 5 teams per regional win $5,000 and a Finals seat;
Finals pay $100K / $50K / $25K. Teams of 1 or 2, students or classes of 2025 and 2026 at US and
Canadian universities. Source: the official rules at pokerbot.sequoiacap.com/rules.html (section
numbers below are from it).

## The build (§3)

- 60 minutes, a Python bot implementing the provided `Agent` interface (§3.3).
- Starter kit: agent template, local simulator, ICM calculator, payout structure, blind schedule (§3.3).
- The poker variant is confidential until the build phase starts (§3.2). Finals use another (§5.2).
- Astra and Codex may be used; OpenAI tools are optional (§3.4, §7.3). Other tools are not addressed.
- One submission per five minutes (§3.5). First tournament at the end of the build, then every 20
  minutes, six in total (§4.1, §4.2).

## The sandbox (§3.6, §3.7)

- No network. Cannot call any outside service for decisions.
- **One millisecond per decision.** Error or timeout = automatic fold, or check if available.
- Submission under 100 MB.
- Allowed packages: not addressed. Assume standard library only.

## The game (§3.8, §4)

- Eight bots per table, random seating; empty seats filled with copies of submitted bots (§4.6).
- 2,000 starting chips. Blinds 10/20, rising every 25 hands (§4.4). Schedule in the kit.
- Table ends at bust-out or 200 hands; survivors split remaining points by ICM (§4.3).
- Points by finishing position; distribution announced at build start, may vary by variant (§4.5).
- Bot state resets per table; opponents anonymized (§3.8).
- Each tournament is 10,000 tables; score = average points per table (§4.3, §4.7).
- Final = T1×1 + T2×2 + T3×3 + T4×4 + T5×5 + T6×6. T1 is 4.8% of the score; T5+T6 are 52%.

## What wins

Scores are relative and low-variance. Against a field of one-hour student bots the edge comes from:
never crashing or timing out (most students will write Monte Carlo equity, which is 10 to 100 ms in
Python and therefore an auto-fold); surviving the early game, since finish-position scoring punishes
busting more than it rewards winning; correct short-stack push/fold with ICM, because 16,000 chips
at 200/400 blinds means every table ends in push/fold; and attacking seats that are dead or timing
out. Deep-stack postflop skill is worth little. See `PLAYBOOK.md` section 0.

## Our assumptions (the list the rule sheet diffs against)

| Assumption | Our default | If the handout differs |
|---|---|---|
| Hole cards | 2 | Stage 3 regenerates tables with a new class scheme; preflop falls back to best-two-card class |
| Board | 3 / 1 / 1, one board | Stage 5 information patch |
| Hand ranking | standard | Stage 3 regenerates with `rank_order` / removed ranks; evaluator remaps |
| Betting | no-limit, raise amounts as raise-TO totals | adapter converts increments; pot-limit via `Rules.betting` |
| Antes | none | `Rules.ante`, `ante_from_level` (engine support landing); loosen opens one step |
| Blinds | 10/20 rising every 25 hands, 8 levels | paste the kit's schedule into `Rules.blind_levels` |
| Stacks / table | 2,000 chips, 8 seats | `Rules.starting_stack`, `n_players` |
| Hand cap | 200, ICM at cap | `Rules.max_hands` |
| Payouts | linear placeholder 8..1 | paste the real table into `Rules.payouts`; Hero reads it |
| Decision budget | 1 ms wall clock per call, no grace | `Config.deadline_ms` soft budget stays at 0.5 |
| Lifecycle | per-table init exists outside the budget | if not, move table loading to module import |
| State | resets per table, opponents anonymous | profiler already assumes this |

## Timeline we expect on the night (confirm against the handout)

| Clock | Event |
|---|---|
| 5:30 PM | check-in |
| 6:00 | variant revealed, kit distributed, build starts |
| 7:00 | build ends, T1 |
| 7:20 / 7:40 / 8:00 / 8:20 / 8:40 | T2 to T6 |
| 9:00 | results |
