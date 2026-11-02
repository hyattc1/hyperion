# Prompt 01: rule sheet (minute 2; paste the rules text and attach or path the kit)

Tonight's rules and starter kit. Fill the RULE SHEET in `NIGHT.md` (from `docs/packet/NIGHT-template.md`)
and write `rules_tonight.json`. No bot code yet. The header's Stage 0 line is the Verifier's, re-measured
with `--rules` (and `--variant` if the catalog has hooks) while Stage 2 runs.

<paste the variant rules verbatim here>

Kit location: <path>

Fill every line; silent rules get UNSPECIFIED and the conservative assumption; quote the rule text for
anything non-standard.

RULE SHEET
- Hole cards dealt per player: N. Any discards, swaps, exposures, auctions? When, and who chooses?
- Board: cards per street, number of boards, any community cards that change.
- Hand ranking: standard? Any rank permutation, removed ranks, added categories, must-use-two rule?
- Betting: no-limit / pot-limit / fixed. Min raise rule. Raise amounts as raise-to totals or
  increments? Antes? Straddles? Any non-standard rule with no `Rules` field in CONTRACTS.md: write
  ENGINE CANNOT REPRESENT and what the sim will play instead.
- Blind schedule: levels and hands per level. Starting stack. Table size. Hand cap.
- Scoring: points by finish position (table), ICM at the cap, any bounty or side payoff.
- Agent interface: class or function name, method signature, every state field and its type, the
  action format (type, string, dict), legal-action discovery, per-decision time limit, how a table
  start and a hand end are signalled, one instance per table or per tournament, whether state persists.
- Setup budget per table (import + construction + table start) and whether each table gets a fresh module, a
  fresh instance, or one object for the tournament (kit E: 1 s, a fresh module per table).
- Event callbacks (table or hand start, cards, actions, showdown, hand end): timed or not, and what an overrun
  does (skipped, interrupted mid-call, counted as a timeout).
- Submission size cap, zipped and unzipped (kit E's was 10 MB zipped, not 100 MB): tools/pack.py `--max-mb`.
- Tooling: how the local simulator runs, how to submit, what the submission file layout must be,
  allowed imports the kit itself uses.

AXIS CLASSIFICATION (every axis that moved; usually one)
- Hand strength ordering moved? (permuted ranks, short deck, new categories) -> Y/N, how.
- Information moved? (extra/fewer hole cards, swaps, exposed cards, extra boards) -> Y/N, how.
- Payoff moved? (bounties, auctions) -> Y/N, how. A point table unlike ours is not a moved axis:
  ASSUMPTION DIFF and `Rules.payouts`.
- Betting structure moved? (limits, sizes, schedule, antes) -> Y/N, how.

FIT VERDICT (one line each: KEEP / REGENERATE / DROP and why; the Verifier holds it all hour unless you
missed a rule)
- evaluator (best hand from 5 to 8 cards, rank remap through `Rules.rank_order`):
- preflop tables (169-class equity and ranks; fewer ranks = REGENERATE; prompt 03 then checks
  `tables.load().source`):
- push/fold solution:
- postflop rule layer:
- opponent profiler:
- ICM curve (reads `Rules.payouts`):
Path: evaluator AND preflop tables both DROP -> skip Stages 3 to 5, Track B cheap bot behind the adapter
(plus the profiler if KEEP). Any REGENERATE -> Stage 3. Otherwise Stage 4.

ASSUMPTION DIFF against the `Rules` table in CONTRACTS.md: each default now wrong and what it
invalidates. Then `rules_tonight.json` with every `Rules` field that differs; it exists
even when nothing moved, and prompts 02 to 06 pass it as `--rules rules_tonight.json`.

End with the single most dangerous thing in these rules for a bot that must answer in 1 ms.
