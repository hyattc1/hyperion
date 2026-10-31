# EXAMPLE rule sheet — from a rehearsal, NOT tonight's rules

Drill 2 (2026-10-31, fake kit C, "Top Heavy / Turbo"; `docs/drills/prompt-drill-2-kitC-payoff.md`),
condensed from the agent's NIGHT.md. Nothing below applies to the event.

## RULE SHEET
- Hole cards: 2; no discards, swaps, exposures or auctions ("no card exchanges").
- Board: 3/1/1.
- Hand ranking: standard ("standard hand rankings"); best five of seven; no must-use rule.
- Betting: no-limit; min raise = last raise or one bb; raise-TO totals ("the TOTAL you are raising to").
  Antes "from Level 3 ... 5% of the big blind": at drill time ENGINE CANNOT REPRESENT (no `Rules` field;
  the sim played the variant minus the ante). Straddles: UNSPECIFIED, assume none.
- Blind schedule: 10/20 to 320/640 in six levels every 20 hands (last held); stack 1,500; eight seats;
  cap 150 hands.
- Scoring: 50/25/12/6/3/2/1/1 by finish; ICM over unfilled positions at the cap. No bounties.
- Agent interface: one process per table (`python submission.py`): `T<n> P<seat> Z<stack>
  V<sb>/<bb>` -> `OK` within 10 s; decision clauses H D S K B C E I O L V T -> `F|K|C|R<total>`, flushed;
  `X`/`Q` get no reply. to_call not given: `max(E) - E[seat]` capped by stack. Pooled clock 1 ms x 3 x
  hands by wall-clock round trip; one reply over 2 s = dead.
- Tooling: `python -m hyperion.drills.fakekits.kit_c.runner submission.py`. One zip under 100 MB,
  `submission.py` at top level; stdlib plus the kit's imports.

## AXIS CLASSIFICATION
- Strength ordering: N. Information: N.
- Payoff: Y. 50/25/12/6/3/2/1/1 (first = 50% of the pool) against our linear 8..1.
- Betting structure: Y. Six levels every 20 hands, 1,500 chips, 150-hand cap; 5% antes from level 3.

## FIT VERDICT
All six KEEP: standard cards, push/fold is per big blind, postflop and profiler untouched by payoffs,
ICM curve reads the pasted payouts. Path: Stage 4.

## ASSUMPTION DIFF
- payouts 8..1 -> 50/25/12/6/3/2/1/1: Hero's ICM curve and sim scoring (`Rules.payouts`).
- 2,000 chips, 8 x 25 hands, cap 200 -> 1,500, 6 x 20, cap 150: sim schedule only; push/fold is per bb.
- no antes -> 5% bb from level 3: unrepresentable then; now `ante_from_level`, `ante_per_level`.

## MOST DANGEROUS THING
The pooled clock charged by pipe round trip: warm-up leaking past the `OK`, or an unflushed stdout (2 s = dead). Second: answering an `X` or `Q` line desynchronises every later reply.
