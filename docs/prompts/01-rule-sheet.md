# Prompt 01: rule sheet (minute 2; paste the rules text and attach or path the kit)

Here are the official rules for tonight's variant and the starter kit files. Produce a RULE SHEET
in `NIGHT.md` and nothing else. Do not write bot code yet.

<paste the variant rules verbatim here>

Kit location: <path>

Fill in every line below. Where the rules are silent, write "UNSPECIFIED" and your conservative
assumption. Quote the rule text for anything that differs from standard no-limit hold'em.

RULE SHEET
- Hole cards dealt per player: N. Any discards, swaps, exposures, auctions? When, and who chooses?
- Board: cards per street, number of boards, any community cards that change.
- Hand ranking: standard? Any rank permutation, removed ranks, added categories, must-use-two rule?
- Betting: no-limit / pot-limit / fixed. Min raise rule. Are raise amounts given as raise-to totals
  or increments? Antes? Straddles?
- Blind schedule: levels and hands per level. Starting stack. Table size. Hand cap.
- Scoring: points by finish position (table), ICM at the cap, any bounty or side payoff.
- Agent interface: class or function name, method signature, the state object's fields (list every
  attribute and its type), the action format (type, string, dict), legal-action discovery, per-decision
  time limit, how a table start and a hand end are signalled, whether the agent is one instance per
  table or per tournament, whether state persists.
- Tooling: how the local simulator runs, how to submit, what the submission file layout must be,
  allowed imports the kit itself uses.

AXIS CLASSIFICATION (pick every axis that moved; most variants move one)
- Hand strength ordering moved? (permuted ranks, short deck, new categories) -> Y/N, how.
- Information moved? (extra/fewer hole cards, swaps, exposed cards, extra boards) -> Y/N, how.
- Payoff moved? (bounties, auctions, non-standard points) -> Y/N, how.
- Betting structure moved? (limits, sizes, schedule, antes) -> Y/N, how.

ASSUMPTION DIFF against our prepared code (our defaults: 2 hole cards, 3/1/1 board, standard
rankings, no-limit with raise-to totals, 10/20 rising every 25 hands, linear placeholder payouts):
list each default that is now wrong and which of our tables or settings it invalidates.

End with: the single most dangerous thing in these rules for a bot that must answer in 1 ms.
