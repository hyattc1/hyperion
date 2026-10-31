# The prompt pack

The hour is not for research or tuning. It is for translation and verification, done by firing a
fixed sequence of prompts at a coding agent. The prompts are the carried-in knowledge. They are plain
text, tool-agnostic (the rules name Astra and Codex; whether Claude Code is allowed is unconfirmed),
and each one has a time box, the exact things to paste in, and a pass/fail check.

Two tracks, decided by the organizers' answer on pre-written code:

- **Track A (repo allowed).** The agent works inside this repo. The prompts mostly ask it to write one
  adapter, run one generator, and run the sim. Hero is submitted by minute 45.
- **Track B (blank directory).** The agent rebuilds the core from `track-b-from-scratch.md`, which is
  the compressed specification of this repo: evaluator, safe wrapper, push/fold rule, profiler. It is
  written so a competent agent regenerates a legal tight bot in 15 minutes and a profiling push/fold
  bot in 40. Rehearse it; it is slower and more fragile than Track A.

## Why the order is variant-agnostic

Every hold'em twist in the MIT archive changes one of four things, and only one of them at a time:

| Axis | Examples | What it breaks | Fix |
|---|---|---|---|
| **Hand strength ordering** | permuted ranks, short deck, new hand categories | every equity table, the evaluator's rank map | regenerate tables with a rules JSON; remap ranks; never touch strategy |
| **Information** | 3 hole cards with discard, card swaps on flop/turn, two boards, exposed cards | preflop class scheme, how much a made hand is worth by the river | widen the class scheme or fall back to made-hand heuristics; reduce value thresholds on streets where cards can change |
| **Payoff** | bounties, auctions for a card, ICM point tables, side pots for a target rank | what a chip is worth; shove/call thresholds | adjust the EV gate: add the side payoff to the pot when it applies; keep everything else |
| **Betting structure** | pot limit, fixed sizes, different blind schedule, antes | legal action set, open sizes, push depth | the adapter clamps; the Config sizes change; push/fold recomputed with the real schedule |

So the first prompt classifies the variant onto these axes, and the fifth prompt applies the fix for
that axis. Everything in between is identical regardless of the game.

## Timeline

| Clock | Prompt | Pass check | If it fails |
|---|---|---|---|
| 0:00 | `00-briefing` pasted as the agent's first message | agent restates the constraints in one paragraph | re-paste; do not proceed without it |
| 0:02 | `01-rule-sheet` with the rules PDF/page and kit files | a filled rule sheet and the axis classification | answer its questions from the rules, re-run |
| 0:07 | `02-adapter-and-cheap-bot` | kit's local simulator plays 50 hands, zero errors, legal every time, submission accepted | submit the kit's own example bot first; then fix |
| 0:15 | **SUBMIT cheap bot** | portal confirms | nothing else matters until this is green |
| 0:17 | `03-tables` only if the rule sheet says the strength or information axis moved | generator finishes, spot check prints sane equities | ship Hero with old tables plus the axis fallback |
| 0:25 | `04-wire-hero` | 300 strict-mode tables vs bestiary through the adapter: zero exceptions, zero illegal, p99 under 0.3 ms, Hero not last | revert to cheap bot plus profiler only |
| 0:40 | `05-variant-patch` for the axis the rule sheet named | re-run the 300 tables, Hero score did not drop | ship without the patch |
| 0:50 | **SUBMIT Hero** | portal confirms | re-submit the cheap bot |
| 0:55 | freeze; read `06-windows` | known-good bot recorded with its hash | |
| T1 + each 20 min | `06-windows` loop | one dial change per window at most, verified in sim before submit | keep the frozen bot |

## Testing the prompts

The prompts are what we tune this week, not the bot. A prompt drill is: fresh agent, blank context,
a scratch directory with one fake kit (`hyperion/drills/fakekits/kit_{a,b,c}`) and one hidden variant
from `hyperion/drills/variants.py`, the prompts fired in order with a wall clock. Score:

1. Minutes to a legal submission (target 15, hard fail at 20).
2. Minutes to Hero wired and clean in strict mode (target 40).
3. Hero points vs the bestiary at the end (compare against the untouched Hero on the same seed).
4. Count of agent questions that needed a human answer (target 0 after the rule sheet).
5. Anything the agent did that we had to undo.

Run it at least once per kit and once per axis. Every failure becomes a sentence in the prompt
that caused it, never a new prompt. `hyperion/drills/run.py` keeps the clock and the scratch dir;
the log goes to `drills/log/`.
