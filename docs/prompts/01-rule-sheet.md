# Prompt 01: rule sheet (minute 2; paste the rules text and attach or path the kit)

Here are the official rules for tonight's variant and the starter kit files. Fill the RULE SHEET in
`NIGHT.md` (copied from `docs/packet/NIGHT-template.md`) and write `rules_tonight.json`. No bot code yet.

<paste the variant rules verbatim here>

Kit location: <path>

Fill every line; where the rules are silent write UNSPECIFIED and your conservative assumption; quote
the rule text for anything non-standard.

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
- Tooling: how the local simulator runs, how to submit, what the submission file layout must be,
  allowed imports the kit itself uses.

AXIS CLASSIFICATION (every axis that moved; most variants move one)
- Hand strength ordering moved? (permuted ranks, short deck, new categories) -> Y/N, how.
- Information moved? (extra/fewer hole cards, swaps, exposed cards, extra boards) -> Y/N, how.
- Payoff moved? (bounties, auctions, non-standard points) -> Y/N, how.
- Betting structure moved? (limits, sizes, schedule, antes) -> Y/N, how.

FIT VERDICT (one line each: KEEP / REGENERATE / DROP and the reason; the Verifier holds this for the rest
of the hour and you may not reopen it without a rule you missed)
- evaluator (best hand from 5 to 8 cards, rank remap through `Rules.rank_order`):
- preflop tables (169-class equity and ranks):
- push/fold solution:
- postflop rule layer:
- opponent profiler:
- ICM curve (reads `Rules.payouts`):
Path, mechanically: evaluator AND preflop tables both DROP -> not hold'em underneath: skip Stages 3 to 5,
Track B cheap bot (tight hand-written rules, push/fold by stack depth, no bluffs) behind the adapter, plus
the profiler if it is KEEP. Any REGENERATE -> Stage 3 runs. Otherwise Stage 4 as normal.

ASSUMPTION DIFF against our defaults (the `Rules` table in CONTRACTS.md): each default now wrong and
what it invalidates. Then write `rules_tonight.json` with every `Rules` field that differs; it exists
even when nothing moved, and prompts 02 to 06 pass it as `--rules rules_tonight.json`.

End with: the single most dangerous thing in these rules for a bot that must answer in 1 ms.
